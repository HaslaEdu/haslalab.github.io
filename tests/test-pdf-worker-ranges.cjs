const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../pdf-worker/src/index.js'), 'utf8');
const url = 'https://haslalab-pdf.haslalab.workers.dev/pdf/IZhO_2017_TS_KO.pdf?v=reviewed';
function setup({ match = async () => undefined, fetch = async () => { throw Error('Unexpected origin request'); } } = {}) {
  const writes = [], waits = [], lookups = [], upstream = [];
  const context = { Request, Response, Headers, URL, caches: { default: {
    match: async req => { lookups.push(req); return match(req); },
    put: async (req, res) => { writes.push({ request: req, status: res.status, body: await res.text() }); }
  } }, fetch: async (...args) => { upstream.push(args); return fetch(...args); } };
  vm.runInNewContext(source.replace('export default {', 'globalThis.pdfWorker = {'), context);
  return { lookups, writes, waits, upstream, run: req => context.pdfWorker.fetch(req, {}, { waitUntil: p => waits.push(p) }) };
}
test('a warm PDF serves requested bytes from cache with status and length intact', async () => {
  const h = setup({ match: async () => new Response('PDF!', { status: 206, headers: { 'Content-Type': 'application/pdf', 'Content-Length': '4', 'Content-Range': 'bytes 100-103/1000' } }) });
  const res = await h.run(new Request(url, { headers: { Range: 'bytes=100-103' } }));
  assert.equal(h.lookups[0].headers.get('Range'), 'bytes=100-103');
  assert.equal(h.lookups[0].method, 'GET');
  assert.equal(res.status, 206); assert.equal(await res.text(), 'PDF!');
  assert.equal(res.headers.get('Content-Length'), '4');
  assert.equal(res.headers.get('Content-Range'), 'bytes 100-103/1000');
  assert.equal(res.headers.get('Accept-Ranges'), 'bytes');
  assert.match(res.headers.get('Access-Control-Expose-Headers'), /Content-Range/);
  assert.equal(h.upstream.length, 0); assert.equal(h.writes.length, 0);
});
test('a cold range goes to the release asset without caching a partial PDF', async () => {
  const h = setup({ fetch: async () => new Response('tail', { status: 206, headers: { 'Content-Length': '4', 'Content-Range': 'bytes 996-999/1000' } }) });
  const res = await h.run(new Request(url, { headers: { Range: 'bytes=-4', Authorization: 'do-not-forward' } }));
  assert.equal(new Headers(h.upstream[0][1].headers).get('Range'), 'bytes=-4');
  assert.equal(new Headers(h.upstream[0][1].headers).get('Authorization'), null);
  assert.match(h.upstream[0][0], /^https:\/\/github\.com\/HaslaEdu\/haslalab\.github\.io\/releases\/download\/pdf-izho\//);
  assert.equal(res.status, 206); assert.equal(await res.text(), 'tail');
  assert.equal(res.headers.get('Content-Range'), 'bytes 996-999/1000');
  assert.equal(res.headers.get('Content-Type'), 'application/pdf');
  assert.equal(h.waits.length, 0); assert.equal(h.writes.length, 0);
});
test('a complete origin PDF is streamed unchanged and cached under a GET without Range', async () => {
  const h = setup({ fetch: async () => new Response('%PDF-complete', { headers: { 'Content-Length': '13' } }) });
  const res = await h.run(new Request(url));
  assert.equal(res.status, 200); assert.equal(await res.text(), '%PDF-complete');
  await Promise.all(h.waits); assert.equal(h.writes.length, 1);
  assert.equal(h.writes[0].body, '%PDF-complete'); assert.equal(h.writes[0].status, 200);
  assert.equal(h.writes[0].request.headers.get('Range'), null);
  assert.equal(h.writes[0].request.method, 'GET');
  assert.equal(res.headers.get('Content-Disposition'), 'inline; filename="IZhO_2017_TS_KO.pdf"');
  assert.equal(res.headers.get('Access-Control-Allow-Origin'), '*');
});
test('an origin ignoring Range may return a complete response, which remains complete in cache', async () => {
  const h = setup({ fetch: async () => new Response('complete', { headers: { 'Content-Length': '8' } }) });
  const res = await h.run(new Request(url, { headers: { Range: 'bytes=0-2' } }));
  assert.equal(res.status, 200); assert.equal(await res.text(), 'complete');
  await Promise.all(h.waits); assert.equal(h.writes[0].body, 'complete');
  assert.equal(h.writes[0].request.headers.get('Range'), null);
});
test('an unsatisfiable cold range stays 416 with the complete document length', async () => {
  const h = setup({ fetch: async () => new Response(null, { status: 416, headers: { 'Content-Range': 'bytes */1000' } }) });
  const res = await h.run(new Request(url, { headers: { Range: 'bytes=2000-' } }));
  assert.equal(res.status, 416); assert.equal(res.headers.get('Content-Range'), 'bytes */1000');
  assert.equal(await res.text(), ''); assert.equal(h.writes.length, 0); assert.equal(h.waits.length, 0);
});
test('an unsatisfiable cached range also preserves 416', async () => {
  const h = setup({ match: async () => new Response(null, { status: 416, headers: { 'Content-Range': 'bytes */1000' } }) });
  const res = await h.run(new Request(url, { headers: { Range: 'bytes=2000-' } }));
  assert.equal(res.status, 416); assert.equal(res.headers.get('Content-Range'), 'bytes */1000');
  assert.equal(h.upstream.length, 0);
});
test('HEAD ignores Range and returns full document headers with an empty body', async () => {
  const h = setup({ match: async () => new Response('%PDF-full', { headers: { 'Content-Length': '9', 'Content-Type': 'application/pdf' } }) });
  const res = await h.run(new Request(url, { method: 'HEAD', headers: { Range: 'bytes=0-2' } }));
  assert.equal(h.lookups[0].headers.get('Range'), null); assert.equal(res.status, 200);
  assert.equal(res.headers.get('Content-Length'), '9'); assert.equal(await res.text(), '');
});
test('If-Range falls back to the full PDF because this service publishes no validators', async () => {
  const h = setup({ fetch: async () => new Response('%PDF-full') });
  const res = await h.run(new Request(url, { headers: { Range: 'bytes=0-2', 'If-Range': '"old-edition"' } }));
  assert.equal(h.lookups[0].headers.get('Range'), null);
  assert.equal(new Headers(h.upstream[0][1].headers).get('Range'), null);
  assert.equal(res.status, 200); assert.equal(await res.text(), '%PDF-full'); await Promise.all(h.waits);
});
test('missing releases and invalid routes retain their existing error responses', async () => {
  const h = setup({ fetch: async () => new Response('missing', { status: 404 }) });
  assert.equal((await h.run(new Request(url))).status, 404);
  assert.equal((await h.run(new Request('https://example.com/pdf/../secret'))).status, 404);
  const denied = await h.run(new Request(url, { method: 'POST' }));
  assert.equal(denied.status, 405); assert.equal(denied.headers.get('Allow'), 'GET, HEAD');
  assert.equal(h.upstream.length, 1); assert.equal(h.writes.length, 0);
});
test('a site PDF is asked for by its own name and saved under it', async () => {
  const h = setup({ fetch: async () => new Response('%PDF', { status: 200, headers: { 'Content-Length': '4' } }) });
  const res = await h.run(new Request('https://haslalab-pdf.haslalab.workers.dev/pdf/l/ispho/ISPhO_2025_T1_KO.pdf'));
  assert.match(h.upstream[0][0], /\/releases\/download\/pdf-xispho\/Xispho_ISPhO_2025_T1_KO\.pdf\?/);
  assert.equal(res.status, 200);
  assert.equal(res.headers.get('Content-Disposition'), 'inline; filename="ISPhO_2025_T1_KO.pdf"');
  assert.match(h.lookups[0].url, /\/pdf\/Xispho_ISPhO_2025_T1_KO\.pdf\?v=/);
  const root = setup({ fetch: async () => new Response('%PDF', { status: 200 }) });
  await root.run(new Request('https://haslalab-pdf.haslalab.workers.dev/pdf/l/solution.pdf'));
  assert.match(root.upstream[0][0], /\/pdf-xroot\/Xroot_solution\.pdf\?/);
});
test('the old storage address still works and also saves under the real name', async () => {
  const h = setup({ fetch: async () => new Response('%PDF', { status: 200 }) });
  const res = await h.run(new Request('https://haslalab-pdf.haslalab.workers.dev/pdf/Xapho_APhO_2003_E1_KO.pdf'));
  assert.match(h.upstream[0][0], /\/pdf-xapho\/Xapho_APhO_2003_E1_KO\.pdf\?/);
  assert.equal(res.headers.get('Content-Disposition'), 'inline; filename="APhO_2003_E1_KO.pdf"');
});
test('the new route refuses paths outside a folder name', async () => {
  for (const p of ['/pdf/l/../x.pdf', '/pdf/l/ISPHO/a.pdf', '/pdf/l/ispho/sub/a.pdf']) {
    const res = await setup().run(new Request('https://haslalab-pdf.haslalab.workers.dev' + p));
    assert.equal(res.status, 404, p);
  }
});

test('a SHA-versioned link bypasses an older cached PDF at both cache layers', async () => {
  const digest='6c1452e22ac42726';
  const h=setup({
    match:async request=>new URL(request.url).searchParams.get('v').endsWith(digest)?undefined:new Response('old PDF'),
    fetch:async()=>new Response('new PDF')
  });
  const res=await h.run(new Request(`https://haslalab-pdf.haslalab.workers.dev/pdf/l/icho/IChO_2026_P_Q2_OriginalLayout_KO.pdf?v=${digest}&cv=2`));
  assert.equal(await res.text(),'new PDF');
  assert.equal(new URL(h.lookups[0].url).searchParams.get('v'),`106-${digest}`);
  assert.equal(new URL(h.upstream[0][0]).searchParams.get('v'),`106-${digest}`);
  await Promise.all(h.waits);
  assert.equal(h.writes[0].request.url,h.lookups[0].url);
});

test('local and storage aliases share a file version while different SHA versions stay separate', async () => {
  const h=setup({fetch:async()=>new Response('%PDF')});
  const base='https://haslalab-pdf.haslalab.workers.dev';
  const file='IChO_2026_P_Q2_OriginalLayout_KO.pdf';
  for(const path of [`/pdf/l/icho/${file}?v=6c1452e22ac42726`,`/pdf/Xicho_${file}?v=6c1452e22ac42726&cv=2`,`/pdf/l/icho/${file}?v=7d7f7157074b825e`]){
    await h.run(new Request(base+path));
  }
  assert.equal(h.lookups[0].url,h.lookups[1].url);
  assert.notEqual(h.lookups[1].url,h.lookups[2].url);
  await Promise.all(h.waits);
});
