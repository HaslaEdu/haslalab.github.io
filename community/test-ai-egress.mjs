import test from 'node:test';
import assert from 'node:assert/strict';

const direct = [];
globalThis.fetch = async (input) => { direct.push(String(input instanceof Request ? input.url : input)); return new Response('direct'); };
const { useEgress, egressFetch } = await import('./src/ai-egress.js');
const egressWorker = (await import('../ai-egress/src/index.js')).default;

test('only the refusing AI hosts go through the egress binding, with method, body and target intact', async () => {
  const sent = [];
  useEgress({ AI_EGRESS: { fetch: async (url, init) => { sent.push({ url, init, target: init.headers.get('x-egress-url'), body: init.body ? await new Response(init.body).text() : null }); return new Response('egress'); } } });
  assert.equal(await (await egressFetch('https://generativelanguage.googleapis.com/v1beta/models/x:generateContent', { method: 'POST', body: '{"a":1}', headers: { 'x-goog-api-key': 'k' } })).text(), 'egress');
  assert.equal(await (await fetch('https://api.anthropic.com/v1/messages', { method: 'POST', body: 'b' })).text(), 'egress', 'the global fetch is the wrapper');
  assert.equal(await (await fetch('https://asia-northeast3-aiplatform.googleapis.com/v1/x')).text(), 'egress');
  assert.equal(await (await fetch('https://api.deepseek.com/chat/completions', { method: 'POST', body: 'x' })).text(), 'direct');
  assert.equal(await (await fetch('https://haslalab.org/pdfx/a.pdf')).text(), 'direct');
  assert.equal(sent.length, 3);
  assert.deepEqual([sent[0].init.method, sent[0].target, sent[0].body, sent[0].init.headers.get('x-goog-api-key')],
    ['POST', 'https://generativelanguage.googleapis.com/v1beta/models/x:generateContent', '{"a":1}', 'k']);
  assert.ok(direct.includes('https://api.deepseek.com/chat/completions'));
  useEgress({});
  assert.equal(await (await fetch('https://api.openai.com/v1/models')).text(), 'direct', 'no binding: straight out as before');
});

test('the egress Worker forwards only to its allowlisted hosts and drops its own headers', async () => {
  const seen = [];
  const saved = globalThis.fetch;
  globalThis.fetch = async (url, init) => { seen.push({ url: String(url), headers: init.headers }); return new Response('ok', { status: 200 }); };
  try {
    const call = (target, extra = {}) => egressWorker.fetch(new Request('https://ai-egress.internal/', { headers: { 'x-egress-url': target, 'authorization': 'Bearer k', 'cf-connecting-ip': '1.2.3.4', ...extra } }));
    assert.equal((await call('https://api.openai.com/v1/models')).status, 200);
    assert.equal(seen[0].url, 'https://api.openai.com/v1/models');
    assert.equal(seen[0].headers.get('authorization'), 'Bearer k');
    assert.equal(seen[0].headers.get('x-egress-url'), null); assert.equal(seen[0].headers.get('cf-connecting-ip'), null);
    for (const bad of ['https://evil.example/', 'http://api.openai.com/', 'https://api.openai.com:8443/', 'https://user:pw@api.openai.com/', 'not a url'])
      assert.ok([400, 403].includes((await call(bad)).status), bad);
    assert.equal(seen.length, 1);
  } finally { globalThis.fetch = saved; }
});
