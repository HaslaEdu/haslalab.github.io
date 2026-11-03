// Upstage Document Parse as a page reader (admin bench only): the plain call, and a tuned reader built on it.
// One endpoint for Upstage's document APIs (api.upstage.ai/v1/document-digitization, multipart, the file in
// «document»). Math comes back as LaTeX in content.markdown / content.html, never in content.text (Upstage's own
// docs: the OCR model does not recognise equations, so text holds garbage for them). Prices per page, VAT aside:
// standard $0.01, enhanced $0.03 (2026-11).
import { pageStrips } from './page-tiles.js';

const UPSTAGE = 'https://api.upstage.ai/v1';
export const UPSTAGE_PAGE_USD = { standard: 0.01, enhanced: 0.03 };
const key = env => (typeof env.UPSTAGE_API_KEY === 'string' ? env.UPSTAGE_API_KEY.trim() : '') || null;

/** one Document Parse call on one image: { markdown, text, model, pages, ms, usd } */
export async function upstageParse(env, bytes, mime = 'image/jpeg', { mode = 'enhanced', model = 'document-parse', fetchImpl = globalThis.fetch, timeoutMs = 120000 } = {}) {
  const k = key(env); if (!k) { const e = new Error('provider_unavailable'); e.code = 'provider_unavailable'; throw e; }
  const form = new FormData();
  form.append('document', new Blob([bytes], { type: mime }), mime === 'image/png' ? 'page.png' : 'page.jpg');
  form.append('model', model);
  if (mode !== 'standard') form.append('mode', mode);                              // older models refuse the field; standard is the default
  form.append('ocr', 'force');                                                     // a photo has no text layer
  form.append('output_formats', '["markdown","text"]');
  const t0 = Date.now();
  for (let attempt = 0; ; attempt++) {
    const r = await fetchImpl(UPSTAGE + '/document-digitization', { method: 'POST', headers: { Authorization: 'Bearer ' + k }, body: form, signal: AbortSignal.timeout(timeoutMs) });
    if ((r.status === 429 || r.status >= 500) && attempt < 2) { await new Promise(done => setTimeout(done, 1500 * (attempt + 1))); continue; }
    if (!r.ok) { const e = new Error('upstage_' + r.status); e.code = r.status === 429 ? 'vision_provider_rate_limited' : 'vision_request_rejected'; e.provider_message = (await r.text().catch(() => '')).slice(0, 300); throw e; }
    const j = await r.json();
    const pages = +j?.usage?.pages || 1;
    return { markdown: String(j?.content?.markdown || ''), text: String(j?.content?.text || ''), model: String(j?.model || model), pages, ms: Date.now() - t0, usd: pages * (UPSTAGE_PAGE_USD[mode] ?? UPSTAGE_PAGE_USD.enhanced) };
  }
}

const norm = line => String(line).replace(/\s+/g, '').toLowerCase();
const lines = md => String(md || '').split('\n').map(l => l.trimEnd()).filter(l => l.trim());

/** the strips' readings, top to bottom, with the lines a strip shares with the one above (the overlap) left out */
export function joinStrips(readings) {
  const out = [];
  for (const md of readings) {
    const tail = new Set(out.slice(-12).map(norm));
    let skipping = true;
    for (const l of lines(md)) {
      if (skipping && tail.has(norm(l))) continue;                                  // the top of a strip repeats the bottom of the last
      skipping = false; out.push(l);
    }
  }
  return out.join('\n');
}

/* the lines two readings of a page disagree on, as pairs (a line of the strips and its nearest line of the whole page) */
function similarity(a, b) {
  const x = norm(a), y = norm(b); if (!x || !y) return 0;
  const grams = s => { const g = new Map(); for (let i = 0; i < s.length - 1; i++) g.set(s.slice(i, i + 2), (g.get(s.slice(i, i + 2)) || 0) + 1); return g; };
  const gx = grams(x), gy = grams(y); let hit = 0;
  for (const [k, n] of gx) hit += Math.min(n, gy.get(k) || 0);
  return 2 * hit / Math.max(1, x.length - 1 + y.length - 1);
}
export function disagreements(stripsText, wholeText) {
  const W = lines(wholeText), out = [];
  for (const [i, l] of lines(stripsText).entries()) {
    let best = null, score = 0;
    for (const w of W) { const s = similarity(l, w); if (s > score) { score = s; best = w; } }
    if (best && norm(best) !== norm(l) && score >= 0.55) out.push({ line: i, strips: l, whole: best });
  }
  return out;
}

const ARBITRATE_SCHEMA = { type: 'object', properties: { choices: { type: 'array', items: { type: 'object', properties: {
  line: { type: 'integer' }, pick: { type: 'string', enum: ['strips', 'whole', 'uncertain'] } }, required: ['line', 'pick'] } } }, required: ['choices'] };

/**
 * The tuned reader: the page read whole and as overlapping strips (each strip at the full resolution a whole page
 * gets, so exponents and subscripts stay legible); the strips' reading is the transcript, and where it and the whole
 * page's disagree on a line a text model picks one of the two as written. It never writes a reading of its own
 * (an LLM «corrects» a student's mistakes otherwise), and «uncertain» keeps the strips' line with a mark.
 */
export async function upstageTunedRead(env, bytes, mime, { strips = 3, mode = 'enhanced', arbiter = 'solar-pro4', visionJSON, fetchImpl, log = [] } = {}) {
  const parse = (b, m) => upstageParse(env, b, m, { mode, fetchImpl }).then(r => { log.push({ step: 'ocr', provider: 'upstage', model: r.model, ms: r.ms, usd: r.usd, ok: 1 }); return r; });
  const cut = mime === 'image/jpeg' ? pageStrips(bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes), strips, 0.14, 92) : [];
  const [whole, ...parts] = await Promise.all([parse(bytes, mime), ...cut.map(b => parse(b, 'image/jpeg'))]);
  const stripsText = parts.length ? joinStrips(parts.map(p => p.markdown)) : whole.markdown;
  let final = lines(stripsText), picked = [];
  const diff = parts.length ? disagreements(stripsText, whole.markdown).slice(0, 60) : [];
  if (diff.length && arbiter && typeof visionJSON === 'function') {
    const t0 = Date.now();
    try {
      const r = await visionJSON(env, { provider: 'upstage', model: arbiter, stage: 'ocr', schema: ARBITRATE_SCHEMA, maxTokens: 4096, policy: 'Apply the policy in the first supplied text.', input: '',
        parts: [{ text: [
          'Two OCR readings of the same handwritten physics answer sheet disagree on some lines. For each listed line choose which reading is the more likely transcription of what the student wrote: "strips" (read from a zoomed strip of the page) or "whole" (read from the whole page). Choose by plausibility of the handwriting reading only (a digit or letter the OCR may confuse: 4/2, 0/d, phi/theta, omega/w, a dropped denominator or exponent), never by which one is physically right: a student\'s own mistake must stay as written. If neither is clearly more likely, answer "uncertain".',
          'Context: the full reading of the page (strips):', stripsText.slice(0, 12000),
          'Lines that disagree:', JSON.stringify(diff.map(d => ({ line: d.line, strips: d.strips, whole: d.whole })))].join('\n\n') }] });
      log.push({ step: 'arbiter', provider: 'upstage', model: arbiter, in: r.usage?.input_tokens ?? null, out: r.usage?.output_tokens ?? null, ms: Date.now() - t0, usd: r.usage ? ((r.usage.input_tokens || 0) * 0.3 + (r.usage.output_tokens || 0) * 1.2) / 1e6 : null, ok: 1 });
      for (const c of Array.isArray(r.raw?.choices) ? r.raw.choices : []) {
        const d = diff.find(x => x.line === c.line); if (!d) continue;
        picked.push({ line: d.line, pick: c.pick });
        if (c.pick === 'whole') final[d.line] = d.whole;
        else if (c.pick === 'uncertain') final[d.line] = d.strips + '   [? whole page read: ' + d.whole + ']';
      }
    } catch (e) { log.push({ step: 'arbiter', provider: 'upstage', model: arbiter, ms: Date.now() - t0, usd: 0, ok: 0, error: e?.code || e?.message || 'arbiter_failed' }); }
  }
  return { markdown: final.join('\n'), whole: whole.markdown, strips: stripsText, disagreements: diff.length, picked, pieces: 1 + parts.length };
}
