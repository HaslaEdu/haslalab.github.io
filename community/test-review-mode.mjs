// Real Worker routes against in-memory D1-compatible SQLite. No provider calls or production tokens.
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import test from 'node:test';
import worker from './src/index.js';

const sqlite = new DatabaseSync(':memory:');
for (const file of readdirSync(new URL('./migrations/', import.meta.url)).filter(n => /^00(?:0[1-9]|1[01])_.*\.sql$/.test(n)).sort()) sqlite.exec(readFileSync(new URL('./migrations/' + file, import.meta.url), 'utf8'));
const DB = {
  prepare(sql) {
    const st = sqlite.prepare(sql);
    const make = args => ({ bind: (...bound) => make(bound), async first() { return st.get(...args) || null; }, async all() { return { results: st.all(...args) }; }, async run() { return this.executeSync(); },
      executeSync() { if (st.columns().length) return { results: st.all(...args) }; const r = st.run(...args); return { success: true, meta: { changes: r.changes, last_row_id: Number(r.lastInsertRowid) } }; } });
    return make([]);
  },
  async batch(statements) { sqlite.exec('BEGIN'); try { const results = statements.map(s => s.executeSync()); sqlite.exec('COMMIT'); return results; } catch (error) { sqlite.exec('ROLLBACK'); throw error; } },
};
globalThis.caches = { default: { async match() {}, async put() {} } };
const timestamp = Math.floor(Date.now() / 1000), tokens = {};
for (let id = 1; id <= 20; id++) {
  sqlite.prepare('INSERT INTO users(id,username,nickname,pw,role,created_at,exam_tokens) VALUES(?,?,?,?,?,?,?)').run(id, 'review' + id, 'Review ' + id, 'unused', 'user', timestamp, 5);
  const token = String(id).padStart(48, 'a'); tokens[id] = token;
  const hash = Buffer.from(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(token))).toString('base64url');
  sqlite.prepare('INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)').run(hash, id, timestamp, timestamp + 3600);
}
const messages=[];
const env = { DB,LAB_JOBS:{async sendBatch(items){messages.push(...items.map(item=>item.body));}}, ALLOWED_ORIGINS: 'http://localhost:8765', LAB_KEEP_HOURS: 'off' };
const originalFetch = globalThis.fetch;
globalThis.fetch = () => { throw new Error('Unexpected external request'); };
test.after(() => { globalThis.fetch = originalFetch; sqlite.close(); });
async function request(path, body, id = 1, method = body === undefined ? 'GET' : 'POST', extra = {}) {
  const response = await worker.fetch(new Request('http://worker.local/api' + path, { method, headers: { ...(id ? { Authorization: 'Bearer ' + tokens[id] } : {}), ...(body === undefined ? {} : { 'Content-Type': 'application/json' }), ...extra }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) }), env);
  return { status: response.status, data: await response.json() };
}
async function drainQueue(){
  let safety=0;
  while(messages.length){assert.ok(++safety<100);const body=messages.shift();sqlite.prepare('UPDATE lab_jobs SET available_at=0 WHERE id=?').run(body.jobId);await worker.queue({messages:[{body,ack(){},retry(){messages.push(body);}}]},env);}
}
async function settled(path,body,id=1){
  const result=await request(path,body,id);
  if(result.status===200&&result.data.queued){
    assert.equal(result.data.session.status,'grading');
    await drainQueue();const done=await request('/lab/sessions/'+result.data.session.id,undefined,id);
    done.data.tokens=result.data.tokens;return done;
  }
  return result;
}
const exam = { comp: 'ipho', year: 2024, tasks: ['T1'], sources: { T1: { kind: 'theory', sol: 'IPhO_2024_T1S.pdf' } }, entry: '?c=ipho&y=2024&m=t&e=T1&review=1', review: true };
let first;
test('standalone review starts without an exam or upload timer and preserves the grading price', async () => {
  const r = await request('/lab/start', { ...exam, pair: true }); assert.equal(r.status, 200); first = r.data;
  assert.equal(first.session.status, 'scanning'); assert.equal(first.session.review_only, true);
  assert.equal(first.session.exam_sec, 0); assert.equal(first.session.scan_sec, null); assert.equal(first.session.scan_until, 0);
  assert.equal(first.session.started_at, first.session.ended_at); assert.equal(first.session.cost, 0.3); assert.equal(first.session.paid, false); assert.equal(first.tokens, 5);
  const saved = sqlite.prepare('SELECT sources FROM lab_sessions WHERE id=?').get(first.session.id);
  assert.equal(JSON.parse(saved.sources)._review, 1);
  const resume = await request('/lab/start', { ...exam, pair: true }); assert.equal(resume.data.session.id, first.session.id); assert.equal(resume.data.resumed, true);
});
test('review mode survives old timestamps and has a usable phone scan link without a deadline', async () => {
  const id = first.session.id;
  sqlite.prepare('UPDATE lab_sessions SET started_at=?,ended_at=? WHERE id=?').run(timestamp - 10 * 86400, timestamp - 10 * 86400, id);
  const r = await request('/lab/sessions/' + id); assert.equal(r.data.session.status, 'scanning'); assert.equal(r.data.session.paid, false);
  const phone = await request('/lab/up', undefined, null, 'GET', { 'X-Lab-Token': first.token });
  assert.equal(phone.status, 200); assert.equal(phone.data.open, true); assert.equal(phone.data.review_only, true); assert.equal(phone.data.scan_until, 0);
});
test('timed and standalone sessions of the same paper cannot resume each other', async () => {
  const r = await request('/lab/start', { ...exam, review: false });
  assert.equal(r.status, 409); assert.equal(r.data.error, 'other_active'); assert.equal(r.data.other.review_only, true);
});
test('typed work is validated, saved and replaced without spending tokens', async () => {
  const path = '/lab/sessions/' + first.session.id + '/text';
  assert.equal((await request(path, { answers: { T1: 'foreign' } }, 2)).status, 404);
  for (const answers of [[], { T2: 'wrong task' }, { T1: true }, { T1: 'x'.repeat(50001) }]) assert.equal((await request(path, { answers })).status, 400);
  let r = await request(path, { answers: { T1: 'Let x denote displacement. Then F = ma.' } });
  assert.equal(r.status, 200); assert.equal(r.data.tokens, 5); assert.equal(r.data.session.pages.length, 1); assert.equal(r.data.session.pages[0].source, 'typed');
  r = await request(path, { answers: { T1: 'Updated solution: F = ma.' } }); assert.equal(r.data.session.pages.length, 1); assert.equal(r.data.session.pages[0].text, 'Updated solution: F = ma.');
});
test('grading is charged once, closes the review, and never assigns a timed ranking', async () => {
  const id = first.session.id;
  let r = await settled('/lab/sessions/' + id + '/submit', { grade: true }); assert.equal(r.status, 200); assert.equal(r.data.tokens, 4.7); assert.equal(r.data.session.paid, true); assert.equal(r.data.session.status, 'pending');
  r = await settled('/lab/sessions/' + id + '/submit', { grade: true }); assert.equal(r.data.tokens, 4.7);
  assert.equal((await request('/lab/sessions/' + id + '/text', { answers: { T1: 'late edit' } })).status, 409);
  assert.equal((await request('/lab/up', undefined, null, 'GET', { 'X-Lab-Token': first.token })).status, 410);
  sqlite.prepare("UPDATE lab_sessions SET status='graded',score=9,points=10 WHERE id=?").run(id);
  r = await request('/lab/sessions/' + id); assert.equal(r.data.session.standing, null);
  r = await request('/lab/stats?comp=ipho'); assert.deepEqual(r.data.exams, {});
});
test('Physics Cup, Ortvay, OPhO and WOPHO enforce review-only even for old timed links', async () => {
  for (const [index, comp] of ['physcup', 'ortvay', 'opho', 'wopho'].entries()) {
    const r = await request('/lab/start', { ...exam, comp, review: false }, index + 3);
    assert.equal(r.status, 200); assert.equal(r.data.session.status, 'scanning'); assert.equal(r.data.session.review_only, true); assert.equal(r.data.session.exam_sec, 0);
    assert.equal(r.data.tokens, 5);
  }
});
test('empty reviews cannot spend tokens, but can close for free to release the active session', async () => {
  const r = await request('/lab/start', exam, 7), id = r.data.session.id;
  const empty = await settled('/lab/sessions/' + id + '/submit', { grade: true }, 7); assert.equal(empty.status, 400); assert.equal(empty.data.error, 'no_answers');
  assert.equal((await request('/lab/sessions/' + id + '/pay', {}, 7)).data.error, 'no_answers');
  const ended = await settled('/lab/sessions/' + id + '/submit', { grade: false }, 7); assert.equal(ended.status, 200); assert.equal(ended.data.session.status, 'ended'); assert.equal(ended.data.tokens, 5);
});
test('ordinary timed exams retain their duration, scan window and answer lock', async () => {
  const r = await request('/lab/start', { ...exam, review: false, entry: '?c=ipho&y=2024&m=t&e=T1' }, 8), s = r.data.session;
  assert.equal(r.status, 200); assert.equal(s.status, 'running'); assert.equal(s.review_only, false); assert.equal(s.exam_sec, 18000); assert.equal(s.scan_sec, 1800);
  assert.equal(s.ended_at - s.started_at, 18000); assert.equal(s.scan_until - s.ended_at, 1800);
  assert.equal((await request('/lab/sessions/' + s.id + '/text', { answers: { T1: 'bypass' } }, 8)).status, 409);
  sqlite.prepare("UPDATE lab_sessions SET status='graded',score=5,points=10 WHERE id=?").run(s.id);
  const stats = await request('/lab/stats?comp=ipho'); assert.equal(stats.data.exams['ipho2024:T1'].sat, 1); assert.equal(stats.data.exams['ipho2024:T1'].graded, 1); assert.equal(stats.data.exams['ipho2024:T1'].avg, 50);
});
test('typed numeric answers are indexed independently and fabricated grader values still score zero', async () => {
  const savedFetch = globalThis.fetch; env.GEMINI_API_KEY = 'test-provider'; const prompts = [];
  globalThis.fetch = async (url, options) => {
    assert.ok(String(url).includes(':generateContent'));
    const parts = JSON.parse(options.body).contents[0].parts, prompt = parts.map(p => p.text || '').join('\n'); prompts.push(prompt);
    let raw;
    if (prompt.includes('[TASK: index typed answer]')) {
      assert.ok(prompt.includes('A.1: F = 42 N')); assert.ok(!parts.some(p => p.inline_data));
      raw = { legible: 'good', items: [{ label: 'A.1', kind: 'value', text: 'F = 42 N', value: 42, unit: 'N', crossed_out: false }] };
    } else {
      assert.ok(prompt.includes('Original typed solution'));
      raw = { items: [{ id: 'A.1', found: true, page: 1, value: 42, unit_ok: true, score: 1, decision: 'met', rules: [], note: 'Explicit typed value.' },
        { id: 'A.2', found: true, page: 1, value: 999, unit_ok: true, score: 1, decision: 'met', rules: [], note: 'Unsupported claim.' }], feedback: [], review: { summary: 'One value is supported.', habits: [], handwriting: { rating: 'clear', notes: 'Typed.' } } };
    }
    return Response.json({ candidates: [{ content: { parts: [{ text: JSON.stringify(raw) }] } }] });
  };
  try {
    const scheme = { points: 2, items: [{ id: 'A.1', points: 1, type: 'value', sheet: 'answer', what: 'Force', unit: 'N', full_min: 42, full_max: 42 }, { id: 'A.2', points: 1, type: 'value', sheet: 'answer', what: 'Unwritten value', full_min: 999, full_max: 999 }] };
    sqlite.prepare('INSERT INTO lab_schemes(exam_key,task,source,scheme,model,created_at) VALUES(?,?,?,?,?,?)').run('ipho2025', 'T1', 'IPhO_2024_T1S.pdf', JSON.stringify(scheme), 'test', timestamp);
    const started = await request('/lab/start', { ...exam, year: 2025 }, 9), id = started.data.session.id;
    await request('/lab/sessions/' + id + '/text', { answers: { T1: 'A.1: F = 42 N' } }, 9);
    assert.equal(prompts.length, 0, 'saving a solution makes no provider request');
    const graded = await settled('/lab/sessions/' + id + '/submit', { grade: true }, 9), result = graded.data.session.detail.tasks.T1;
    assert.equal(graded.status, 200); assert.equal(result.status, 'graded'); assert.equal(result.score, 1); assert.equal(result.points, 2);
    assert.equal(result.items[0].got, 1); assert.equal(result.items[1].got, 0); assert.ok(result.items[1].rules.includes('R9')); assert.equal(prompts.length, 2);
    assert.equal(graded.data.session.pages[0].text, 'A.1: F = 42 N');
  } finally { delete env.GEMINI_API_KEY; globalThis.fetch = savedFetch; }
});
test('Ortvay receives grounded qualitative feedback from the official paper without invented points', async () => {
  const savedFetch = globalThis.fetch; env.GEMINI_API_KEY = 'test-provider'; let calls = 0;
  globalThis.fetch = async (url, options) => {
    if (String(url) === 'https://ortvay.elte.hu/2026/E26.pdf') return new Response('%PDF-1.7\nOfficial problem', { headers: { 'content-type': 'application/pdf' } });
    assert.ok(String(url).includes(':generateContent')); calls++;
    const parts = JSON.parse(options.body).contents[0].parts, prompt = parts.map(p => p.text || '').join('\n');
    assert.ok(prompt.includes('qualitative physics study review')); assert.ok(prompt.includes('No official solution or point scheme')); assert.ok(parts.some(p => p.inline_data?.mime_type === 'application/pdf'));
    return Response.json({ candidates: [{ content: { parts: [{ text: JSON.stringify({ summary: 'Newton’s second law is stated, but the assumptions need checking.', strengths: ['An explicit force law.'], gaps: ['Define the inertial reference frame.'], evidence: [{ page: 1, quote: 'F = ma', note: 'The stated force law.' }] }) }] } }] });
  };
  try {
    const started = await request('/lab/start', { comp: 'ortvay', year: 2026, tasks: ['T'], review: true, sources: { T: { kind: 'theory', paper: 'https://ortvay.elte.hu/2026/E26.pdf' } } }, 10), id = started.data.session.id;
    await request('/lab/sessions/' + id + '/text', { answers: { T: 'Problem 1. F = ma in an inertial frame.' } }, 10);
    const graded = await settled('/lab/sessions/' + id + '/submit', { grade: true }, 10), s = graded.data.session, result = s.detail.tasks.T;
    assert.equal(graded.status, 200); assert.equal(s.status, 'graded'); assert.equal(s.score, null); assert.equal(s.points, null); assert.equal(graded.data.tokens, 4.7); assert.equal(calls, 1);
    assert.equal(result.grading_mode, 'qualitative_review'); assert.equal(result.official, false); assert.equal(result.reference, 'published_problem_only'); assert.equal(result.score, null); assert.ok(result.review.summary); assert.equal(result.evidence[0].quote, 'F = ma');
    assert.equal((await request('/lab/sessions/' + id, undefined, 10)).data.session.standing, null);
  } finally { delete env.GEMINI_API_KEY; globalThis.fetch = savedFetch; }
});
test('qualitative scans preserve the original OCR once, include the image, and respect the D1 row budget', async () => {
  const savedFetch = globalThis.fetch; env.GEMINI_API_KEY = 'test-provider'; env.UPSTAGE_API_KEY = 'test-ocr';
  let oversized = false, reviewCalls = 0;
  const original = 'Problem 1: F = ma; x_i^2 = a/b. Original transcript.';
  globalThis.fetch = async (url, options) => {
    if (String(url) === 'https://ortvay.elte.hu/2026/E26.pdf') return new Response('%PDF-1.7\nOfficial problem');
    if (String(url).includes('upstage')) return Response.json({ content: { markdown: oversized ? original.repeat(10000) : original }, confidence: 0.94, usage: { pages: 1 } });
    assert.ok(String(url).includes(':generateContent'));
    const parts = JSON.parse(options.body).contents[0].parts, prompt = parts.map(p => p.text || '').join('\n'); let raw;
    if (prompt.includes('[TASK: read page]')) raw = { header: { task: 'T', sheet: 'answer' }, legible: 'good', items: [{ label: '1', kind: 'text', text: 'Short auxiliary index.' }] };
    else { reviewCalls++; assert.ok(parts.some(p => p.inline_data?.mime_type === 'image/png')); assert.ok(prompt.includes(original)); raw = { summary: 'The stated law is explicit.', strengths: ['A force law.'], gaps: [], evidence: [{ page: 1, quote: 'F = ma', note: 'Original transcript.' }] }; }
    return Response.json({ candidates: [{ content: { parts: [{ text: JSON.stringify(raw) }] } }] });
  };
  try {
    for (const user of [11, 12]) {
      oversized = user === 12;
      const started = await request('/lab/start', { comp: 'ortvay', year: 2026, tasks: ['T'], review: true, sources: { T: { kind: 'theory', paper: 'https://ortvay.elte.hu/2026/E26.pdf' } } }, user), id = started.data.session.id;
      const png = Buffer.from('89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4890000000D49444154789C6360000002000154A24F5D0000000049454E44AE426082', 'hex');
      const image = Buffer.concat([png, Buffer.alloc(oversized ? 1800000 : 200, 4)]);
      const page = sqlite.prepare("INSERT INTO lab_pages(session_id,no,task,kind,mime,data,ocr_status,created_at) VALUES(?,1,'T','answer','image/png',?,'unpaid',?)").run(id, image, timestamp);
      const graded = await settled('/lab/sessions/' + id + '/submit', { grade: true }, user), stored = sqlite.prepare('SELECT * FROM lab_pages WHERE id=?').get(Number(page.lastInsertRowid));
      assert.equal(graded.status, 200); assert.equal(stored.data.length, image.length);
      if (oversized) { assert.equal(graded.data.session.detail.tasks.T.why, 'ocr_storage_limit'); assert.equal(stored.ocr_status, 'failed'); assert.equal(stored.ocr, null); }
      else { assert.equal(graded.data.session.status, 'graded', JSON.stringify(graded.data.session.detail)); assert.equal(stored.ocr, original); assert.equal(stored.text, null); assert.equal(JSON.parse(stored.read).ocr.text, undefined); }
    }
    assert.equal(reviewCalls, 1, 'oversized OCR never reaches the feedback model');
  } finally { delete env.GEMINI_API_KEY; delete env.UPSTAGE_API_KEY; globalThis.fetch = savedFetch; }
});
const eotvosSources = JSON.parse(readFileSync(new URL('../tools/theory/eotvos.json', import.meta.url), 'utf8')).years
  .filter(y => [2014, 2015, 2016, 2020].includes(y.y)).sort((a, b) => a.y - b.y)
  .map(y => ({ year: y.y, solution: y.files.find(f => f.kind === 'solution').url }));
const eotvosSessions = [];
test('timed Eotvos preserves exactly the four verified journal source URLs for their matching year', async () => {
  for (const [index, source] of eotvosSources.entries()) {
    const user = 13 + index, r = await request('/lab/start', { comp: 'eotvos', year: source.year, tasks: ['T'], sources: { T: { kind: 'theory', sol: source.solution } } }, user);
    assert.equal(r.status, 200); assert.equal(r.data.session.status, 'running'); assert.equal(r.data.session.exam_sec, 18000); assert.equal(r.data.session.review_only, false);
    const stored = sqlite.prepare('SELECT sources FROM lab_sessions WHERE id=?').get(r.data.session.id);
    assert.equal(JSON.parse(stored.sources).T.sol, source.solution);
    eotvosSessions.push({ id: r.data.session.id, user, ...source });
  }
});
test('Eotvos journal source validation rejects wrong years, hosts and unrelated competitions', async () => {
  const cases = [
    { comp: 'eotvos', year: 2020, sol: eotvosSources[0].solution },
    { comp: 'eotvos', year: 2014, sol: eotvosSources[0].solution.replace('fizikaiszemle.elft.hu', 'fizikaiszemle.elft.hu.evil.invalid') },
    { comp: 'ipho', year: 2014, sol: eotvosSources[0].solution },
  ];
  for (const [index, value] of cases.entries()) {
    const r = await request('/lab/start', { ...value, tasks: ['T'], sources: { T: { kind: 'theory', sol: value.sol } } }, 17 + index);
    assert.equal(r.status, 200);
    const stored = sqlite.prepare('SELECT sources FROM lab_sessions WHERE id=?').get(r.data.session.id);
    assert.equal(JSON.parse(stored.sources).T.sol, undefined);
  }
});
test('a source journal without printed current-year point values remains unscored instead of inventing a rubric', async () => {
  const savedFetch = globalThis.fetch; env.GEMINI_API_KEY = 'test-provider'; let calls = 0;
  const sitting = eotvosSessions[0];
  globalThis.fetch = async (url, options) => {
    if (String(url) === sitting.solution) return new Response('%PDF-1.7\nOfficial Eotvos report with historical tasks');
    assert.ok(String(url).includes(':generateContent')); calls++;
    const request = JSON.parse(options.body), prompt = request.contents[0].parts.map(p => p.text || '').join('\n');
    assert.ok(prompt.includes('ONLY the exact 2014')); assert.ok(prompt.includes('exclude anniversary and historical problems')); assert.ok(prompt.includes('Never invent equal weights'));
    assert.ok(request.generationConfig.responseSchema.required.includes('points_verified'));
    return Response.json({ candidates: [{ content: { parts: [{ text: JSON.stringify({ points_verified: false, points: 0, items: [], notes: 'no_official_points' }) }] } }] });
  };
  try {
    await request('/lab/sessions/' + sitting.id + '/finish', {}, sitting.user);
    sqlite.prepare("INSERT INTO lab_pages(session_id,no,task,kind,mime,data,ocr,ocr_status,text,created_at) VALUES(?,1,'T','answer','text/plain',X'','F = ma','done','F = ma',?)").run(sitting.id, timestamp);
    const r = await settled('/lab/sessions/' + sitting.id + '/submit', { grade: true }, sitting.user);
    assert.equal(r.status, 200); assert.equal(r.data.session.status, 'pending'); assert.equal(r.data.session.detail.tasks.T.why, 'no_official_points'); assert.equal(r.data.session.points, null); assert.equal(r.data.session.score, null); assert.equal(calls, 1);
  } finally { delete env.GEMINI_API_KEY; globalThis.fetch = savedFetch; }
});
test('a verified Eotvos journal cannot redirect the Worker to an untrusted host', async () => {
  const savedFetch = globalThis.fetch; env.GEMINI_API_KEY = 'test-provider'; const sitting = eotvosSessions[1], fetched = [];
  globalThis.fetch = async url => { fetched.push(String(url)); assert.equal(String(url), sitting.solution); return new Response('', { status: 302, headers: { location: 'https://evil.invalid/paper.pdf' } }); };
  try {
    await request('/lab/sessions/' + sitting.id + '/finish', {}, sitting.user);
    sqlite.prepare("INSERT INTO lab_pages(session_id,no,task,kind,mime,data,ocr,ocr_status,text,created_at) VALUES(?,1,'T','answer','text/plain',X'','F = ma','done','F = ma',?)").run(sitting.id, timestamp);
    const r = await settled('/lab/sessions/' + sitting.id + '/submit', { grade: true }, sitting.user);
    assert.equal(r.status, 200); assert.equal(r.data.session.status, 'error'); assert.equal(r.data.session.detail.tasks.T.why, 'scheme_failed'); assert.ok(fetched.length>=1&&fetched.length<=4);assert.ok(fetched.every(url=>url===sitting.solution),'queue retries never follow an untrusted redirect');
  } finally { delete env.GEMINI_API_KEY; globalThis.fetch = savedFetch; }
});

test('PLANCKS uses its verified four-hour sitting and the 2021 sixteen-hour online exception on the server', async () => {
  for (const [year, hours] of [[2026, 4], [2021, 16]]) {
    const r = await request('/lab/start', { comp: 'plancks', year, tasks: ['T'], sources: { T: { kind: 'theory', sol: `PLANCKS_${year}_TS.pdf` } } }, 20);
    assert.equal(r.status, 200);
    assert.equal(r.data.session.exam_sec, hours * 3600);
    assert.equal(r.data.session.ended_at - r.data.session.started_at, hours * 3600);
    assert.equal(r.data.session.review_only, false);
    sqlite.prepare("UPDATE lab_sessions SET status='ended' WHERE id=?").run(r.data.session.id);
  }
});

test('a locally archived Eotvos report keeps the same current-year and printed-points safeguards as its publisher URL', async () => {
  const savedFetch = globalThis.fetch; env.GEMINI_API_KEY = 'test-provider'; let calls = 0;
  globalThis.fetch = async (url, options) => {
    if (String(url).startsWith('https://github.com/')) return new Response('', { status: 404 });
    if (String(url) === 'https://haslalab.org/pdfx/eotvos/Eotvos_2014_TS.pdf') return new Response('%PDF-1.7\nOriginal annual report');
    assert.ok(String(url).includes(':generateContent')); calls++;
    const prompt = JSON.parse(options.body).contents[0].parts.map(p => p.text || '').join('\n');
    assert.ok(prompt.includes('ONLY the exact 2014'));
    assert.ok(prompt.includes('exclude anniversary and historical problems'));
    return Response.json({ candidates: [{ content: { parts: [{ text: JSON.stringify({ points_verified: false, items: [], notes: 'no_official_points' }) }] } }] });
  };
  try {
    const started = await request('/lab/start', { comp: 'eotvos', year: 2014, tasks: ['T'], review: true, sources: { T: { kind: 'theory', sol: 'Eotvos_2014_TS.pdf' } } }, 20);
    assert.equal(started.status, 200);
    const id = started.data.session.id;
    await request('/lab/sessions/' + id + '/text', { answers: { T: 'A submitted derivation: F = ma.' } }, 20);
    const graded = await settled('/lab/sessions/' + id + '/submit', { grade: true }, 20);
    assert.equal(graded.status, 200);
    assert.equal(graded.data.session.detail.tasks.T.why, 'no_official_points');
    assert.equal(graded.data.session.score, null);
    assert.equal(graded.data.session.points, null);
    assert.equal(calls, 1);
  } finally { delete env.GEMINI_API_KEY; globalThis.fetch = savedFetch; }
});

test('paying for an untimed review never submits it through GET, bootstrap or the minute recovery sweep',async()=>{
  const user=20,started=await request('/lab/start',exam,user),id=started.data.session.id;
  await request('/lab/sessions/'+id+'/text',{answers:{T1:'An unfinished review: F = ma.'}},user);
  const paid=await request('/lab/sessions/'+id+'/pay',{},user);assert.equal(paid.status,200);assert.equal(paid.data.session.paid,true);assert.equal(paid.data.session.status,'scanning');
  sqlite.prepare('UPDATE lab_sessions SET started_at=?,ended_at=?,scan_until=0 WHERE id=?').run(timestamp-30*86400,timestamp-30*86400,id);
  const savedFetch=globalThis.fetch;let calls=0;globalThis.fetch=()=>{calls++;throw Error('status reads and review sweep must not call AI');};
  try{
    assert.equal((await request('/lab/sessions/'+id,undefined,user)).data.session.status,'scanning');
    assert.equal((await request('/lab/bootstrap?id='+id,undefined,user)).data.session.status,'scanning');
    const work=[];await worker.scheduled({scheduledTime:Date.now()},env,{waitUntil:p=>work.push(p)});await Promise.all(work);
    const row=sqlite.prepare('SELECT status,submitted_at FROM lab_sessions WHERE id=?').get(id);
    assert.equal(row.status,'scanning');assert.equal(row.submitted_at,null);assert.equal(calls,0);
    assert.equal(sqlite.prepare('SELECT COUNT(*) n FROM lab_jobs WHERE session_id=?').get(id).n,0);
  }finally{globalThis.fetch=savedFetch;}
});
