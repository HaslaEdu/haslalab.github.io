// arena.js in a VM with stand-ins only: no browser, no server, no real account.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const read = file => fs.readFileSync(path.join(__dirname, '..', file), 'utf8');
const arena = read('arena.js'), index = read('index.html');
const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));

function app({hash = '#/', token = '', lang = 'ko'} = {}) {
  const store = new Map(), calls = [], toks = [];
  const location = {origin: 'https://haslalab.org', pathname: '/', search: '', hash, href: 'https://haslalab.org/' + hash};
  const root = {innerHTML: '', querySelector: () => null, querySelectorAll: () => []};
  const context = {lang, esc, console, URLSearchParams, crypto: globalThis.crypto, btoa, location,
    cm: {me: null}, cmBase: () => 'https://community.example',
    cmApi: async (method, p, body) => { calls.push({method, path: p, body}); if (p === '/oauth/redeem') return {token: 'session-token', user: {id: 7, nickname: 'Fixture'}, fresh: false}; throw Object.assign(new Error('unexpected'), {status: 500}); },
    cmTok: v => { if (v === undefined) return token; toks.push(v); token = v || ''; },
    cmIdentityScope: () => token, cmBack: () => { location.hash = '#/'; }, cmToast: () => {}, arChip: () => {},
    cmHealth: async () => ({v: 5}), cmLoadMe: async () => null,
    history: {replaceState: (_s, _t, url) => { location.hash = url.slice(url.indexOf('#')); }},
    sessionStorage: {getItem: k => store.has(k) ? store.get(k) : null, setItem: (k, v) => store.set(k, String(v)), removeItem: k => store.delete(k)},
    document: {getElementById: id => id === 'arRoot' ? root : null, querySelector: () => null, querySelectorAll: () => []}};
  vm.createContext(context);
  vm.runInContext(arena, context);
  return {context, root, store, calls, toks, location};
}

test('starting a social sign-in keeps a fresh nonce in this tab and sends it to the start', () => {
  const a = app();
  a.context.arOauthStart('google');
  const url = new URL(a.location.href), n = url.searchParams.get('nonce');
  assert.equal(url.pathname, '/api/oauth/google/start');
  assert.match(n, /^[A-Za-z0-9_-]{32}$/);
  assert.equal(a.store.get('hlOauthNonce'), n);
  a.context.arOauthStart('kakao', 'TICKET');
  const again = new URL(a.location.href);
  assert.notEqual(again.searchParams.get('nonce'), n, 'every start has its own nonce');
  assert.equal(again.searchParams.get('ticket'), 'TICKET');
});

test('a code from a link someone else sent is not redeemed and the current session is untouched', async () => {
  for (const hash of ['#/oauth?c=attacker-code', '#/oauth?c=attacker-code&n=attacker-nonce']) for (const stored of [null, 'my-own-nonce']) {
    const a = app({hash, token: 'victim-session'});
    if (stored) a.store.set('hlOauthNonce', stored);
    await a.context.arOauthBack(a.root);
    assert.deepEqual(a.calls, [], 'no redeem request');
    assert.deepEqual(a.toks, [], 'the stored session is not replaced');
    assert.match(a.root.innerHTML, /로그인을 시작한 창에서만 완료할 수 있어요\. 다시 로그인해 주세요\./);
    assert.equal(a.location.hash, '#/oauth', 'the code leaves the address bar');
    assert.equal(a.store.get('hlOauthNonce') ?? null, stored, "this window's own pending sign-in still works");
  }
  const en = app({hash: '#/oauth?c=x&n=y', lang: 'en'});
  await en.context.arOauthBack(en.root);
  assert.match(en.root.innerHTML, /window that started it/);
});

test('the code this window asked for is redeemed once and its nonce is cleared', async () => {
  const a = app({hash: '#/oauth?c=my-code&n=my-nonce'});
  a.store.set('hlOauthNonce', 'my-nonce');
  await a.context.arOauthBack(a.root);
  assert.deepEqual(JSON.parse(JSON.stringify(a.calls)), [{method: 'POST', path: '/oauth/redeem', body: {code: 'my-code'}}]);
  assert.deepEqual([...a.toks], ['session-token']);
  assert.equal(a.store.has('hlOauthNonce'), false);
  // a provider error clears the pending nonce too and shows the reason
  const e = app({hash: '#/oauth?e=oauth_cancelled'});
  e.store.set('hlOauthNonce', 'pending');
  await e.context.arOauthBack(e.root);
  assert.equal(e.store.has('hlOauthNonce'), false);
  assert.deepEqual(e.calls, []);
  assert.match(e.root.innerHTML, /로그인을 취소했습니다/);
});
