// Dedicated math-OCR services for a page, beside the LLM readers: Mathpix (v3/text) and SimpleTex (simpletex_ocr).
// Keys are Worker secrets found by name (any secret whose name says mathpix / simpletex and id / key / secret), so the
// admin's own names work; they are never returned or logged. Used by the admin model bench first.

const pick = (env, owner, kind) => {
  const name = Object.keys(env || {}).find(k => owner.test(k) && kind.test(k) && typeof env[k] === 'string' && env[k].trim());
  return name ? env[name].trim() : null;
};
const MATHPIX = /mathpix/i, SIMPLETEX = /simple_?tex/i;
const ID = /(app_?)?id$|_id_|appid/i, SECRET = /secret|key/i;
export const ocrEngineKeys = env => ({
  mathpix: !!(pick(env, MATHPIX, ID) && pick(env, MATHPIX, SECRET)),
  simpletex: !!(pick(env, SIMPLETEX, ID) && pick(env, SIMPLETEX, SECRET)),
});

const b64 = bytes => { let s = ''; for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000)); return btoa(s); };
class OcrEngineError extends Error { constructor(code, status, message) { super(code); this.code = code; this.status = status; Object.defineProperty(this, 'provider_message', { value: message, enumerable: false }); } }

/** Mathpix v3/text: the page as text with $…$ math */
export async function mathpixRead(env, bytes, mime, { signal, fetchImpl = fetch } = {}) {
  const id = pick(env, MATHPIX, ID), key = pick(env, MATHPIX, SECRET);
  if (!id || !key) throw new OcrEngineError('ocr_engine_unavailable');
  const res = await fetchImpl('https://api.mathpix.com/v3/text', { method: 'POST', signal,
    headers: { app_id: id, app_key: key, 'Content-Type': 'application/json' },
    body: JSON.stringify({ src: `data:${mime};base64,${b64(bytes)}`, formats: ['text'], math_inline_delimiters: ['$', '$'], rm_spaces: true,
      // candidates' pages are not kept by Mathpix to improve its models
      metadata: { improve_mathpix: false } }) });
  const body = await res.json().catch(() => null);
  if (!res.ok || !body || body.error) throw new OcrEngineError('ocr_engine_failed', res.status, String(body?.error || body?.error_info?.message || '').slice(0, 240));
  return { text: String(body.text || ''), confidence: Number.isFinite(body.confidence) ? body.confidence : null, handwritten: !!body.is_handwritten };
}

/** SimpleTex simpletex_ocr (general page with formulas), signed with the app id and secret */
export async function simpletexRead(env, bytes, mime, { signal, fetchImpl = fetch } = {}) {
  const id = pick(env, SIMPLETEX, ID), secret = pick(env, SIMPLETEX, SECRET);
  if (!id || !secret) throw new OcrEngineError('ocr_engine_unavailable');
  const random = Array.from(crypto.getRandomValues(new Uint8Array(16)), n => 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'[n % 62]).join('');
  const timestamp = String(Math.floor(Date.now() / 1000));
  const sign = md5(`app-id=${id}&random-str=${random}&timestamp=${timestamp}&secret=${secret}`);
  const form = new FormData(); form.append('file', new Blob([bytes], { type: mime }), mime === 'image/png' ? 'page.png' : 'page.jpg');
  const res = await fetchImpl('https://server.simpletex.cn/api/simpletex_ocr', { method: 'POST', signal, headers: { 'app-id': id, 'random-str': random, timestamp, sign }, body: form });
  const body = await res.json().catch(() => null);
  if (!res.ok || !body || body.status === false) throw new OcrEngineError('ocr_engine_failed', res.status, String(body?.err_info?.err_msg || body?.message || '').slice(0, 240));
  const info = body.res?.info;
  const text = typeof info === 'string' ? info : info && typeof info === 'object' ? String(info.markdown ?? info.text ?? JSON.stringify(info)) : '';
  return { text, confidence: Number.isFinite(body.res?.conf) ? body.res.conf : null };
}

/* MD5 (RFC 1321), for SimpleTex's request signature: Web Crypto has no MD5 */
export function md5(text) {
  const bytes = new TextEncoder().encode(text), n = (((bytes.length + 8) >>> 6) + 1) * 16, w = new Uint32Array(n);
  for (let i = 0; i < bytes.length; i++) w[i >> 2] |= bytes[i] << ((i % 4) * 8);
  w[bytes.length >> 2] |= 0x80 << ((bytes.length % 4) * 8);
  w[n - 2] = bytes.length * 8; w[n - 1] = Math.floor(bytes.length / 0x20000000);
  const K = Array.from({ length: 64 }, (_, i) => Math.floor(Math.abs(Math.sin(i + 1)) * 2 ** 32) >>> 0);
  const S = [7, 12, 17, 22, 5, 9, 14, 20, 4, 11, 16, 23, 6, 10, 15, 21];
  let a0 = 0x67452301, b0 = 0xefcdab89, c0 = 0x98badcfe, d0 = 0x10325476;
  for (let off = 0; off < n; off += 16) {
    let a = a0, b = b0, c = c0, d = d0;
    for (let i = 0; i < 64; i++) {
      const r = i >> 4; let f, g;
      if (r === 0) { f = (b & c) | (~b & d); g = i; }
      else if (r === 1) { f = (d & b) | (~d & c); g = (5 * i + 1) % 16; }
      else if (r === 2) { f = b ^ c ^ d; g = (3 * i + 5) % 16; }
      else { f = c ^ (b | ~d); g = (7 * i) % 16; }
      const t = d; d = c; c = b;
      const x = (a + f + K[i] + w[off + g]) >>> 0, s = S[r * 4 + (i % 4)];
      b = (b + ((x << s) | (x >>> (32 - s)))) >>> 0; a = t;
    }
    a0 = (a0 + a) >>> 0; b0 = (b0 + b) >>> 0; c0 = (c0 + c) >>> 0; d0 = (d0 + d) >>> 0;
  }
  return [a0, b0, c0, d0].map(v => [0, 8, 16, 24].map(sh => ((v >>> sh) & 255).toString(16).padStart(2, '0')).join('')).join('');
}
