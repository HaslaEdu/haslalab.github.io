const OFFICIAL_APIS = new Set([
  'https://haslalab-community-edge.haslalab.workers.dev',
  'https://haslalab-community.haslalab.workers.dev',
]);

// This entry point opens the same camera, live marker detection, perspective
// correction and preview used by IPhO. Only its monthly transport is different.
// Scan grants travel in a fragment and are never account bearer credentials.
export function monthlyScanTarget(href) {
  const entry = new URL(href), input = new URLSearchParams(entry.hash.slice(1));
  const code = input.get('c') || '';
  if (!/^[a-f0-9-]{36}\.[A-Za-z0-9_-]{43}$/.test(code)) return null;
  const target = new URL('scan.html',entry);
  target.search = '?monthly=1';
  const hash = new URLSearchParams({c:code,l:input.get('l') === 'en' ? 'en' : 'ko'});
  const requested = input.get('a');
  if (requested) {
    let api;
    try { api = new URL(requested); } catch { return null; }
    const local = /^(?:localhost|127\.0\.0\.1|\[::1\])$/.test(api.hostname) && ['http:','https:'].includes(api.protocol);
    if (api.username || api.password || api.search || api.hash || api.pathname !== '/' || !OFFICIAL_APIS.has(api.origin) && !local) return null;
    hash.set('a',api.origin);
  }
  target.hash = hash.toString();
  return target.href;
}

export async function monthlyScanPayload(shot,encodeUpload) {
  // One ID survives a lost response. Replacing the photo, page, kind or
  // corrected pixels clears it in the shared scanner's monthly branch.
  if (!shot.requestId) shot.requestId = monthlyUploadId();
  const scan = await encodeUpload(shot.blob,{maxBytes:4*1024*1024});
  const capture = shot.captureFile || shot.file;
  const original = capture === shot.blob ? scan : await encodeUpload(capture,{maxBytes:4*1024*1024});
  const form = new FormData();
  const extension = blob => ({'image/jpeg':'jpg','image/png':'png','image/webp':'webp'})[blob.type];
  const scanExt = extension(scan), originalExt = extension(original);
  if (!scanExt || !originalExt) throw {code:'bad_image'};
  form.append('image',scan,'scan.'+scanExt);
  form.append('original_image',original,'original.'+originalExt);
  form.append('request_id',shot.requestId);
  return form;
}

export function monthlyUploadId(random=globalThis.crypto) {
  if (random?.randomUUID) return random.randomUUID();
  if (!random?.getRandomValues) throw {code:'unsupported_browser'};
  return 'monthly-'+Array.from(random.getRandomValues(new Uint8Array(16)),byte=>byte.toString(16).padStart(2,'0')).join('');
}

if (typeof window !== 'undefined' && typeof document !== 'undefined' && /\/monthly-scan\.html$/.test(window.location.pathname)) {
  const input = new URLSearchParams(window.location.hash.slice(1)), en = input.get('l') === 'en';
  document.documentElement.lang = en ? 'en' : 'ko';
  if (en) {
    document.getElementById('title').textContent = 'Monthly answer scan';
    document.getElementById('message').textContent = 'Opening the same camera and page correction used by exam mode.';
    document.getElementById('back').textContent = 'Back to monthly problems';
  }
  const target = monthlyScanTarget(window.location.href);
  try { window.history.replaceState(null,'',window.location.pathname+window.location.search); } catch (_) {}
  if (target) window.location.replace(target);
  else document.getElementById('message').textContent = en
    ? 'This scan link is invalid. Open a new QR code from the monthly problem submission screen.'
    : '촬영 링크가 올바르지 않습니다. 월별 문제 제출 화면에서 새 QR 코드를 열어 주세요.';
}
