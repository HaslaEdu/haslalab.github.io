const test = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {resolve} = require('node:path');
const {createRequire} = require('node:module');
const {JSDOM} = createRequire(resolve(__dirname, '../community/package.json'))('jsdom');
const nav = require('../archive-navigation.js');

const code = readFileSync(resolve(__dirname, '../archive-private-textbooks.js'), 'utf8').replace(/^export /gm, '');
const API = '/api/problem-bank/private-textbooks/books';
const PATH = '#/archive/books/phys?view=private-textbooks';
const BOOK = {id: 'goldstein', title: 'Private synthetic book', count: 1, korean_count: 1};
const problem = {ordinal: 1, number: '1.1', label: 'Sample', chapter: 'Chapter 1', has_korean: true};
const flush = () => new Promise(done => setImmediate(done));

async function setup(t, {initialToken = 'private-test-token', status = 200, withKorean = true} = {}) {
  const dom = new JSDOM('<main></main>', {
    url: 'https://haslalab.org/' + PATH, runScripts: 'outside-only',
  });
  const w = dom.window;
  let token = initialToken;
  const calls = [], revoked = [], math = [];
  w.URL.createObjectURL = () => 'blob:private-source';
  w.URL.revokeObjectURL = url => revoked.push(url);
  w.fetch = async (address, options) => {
    const url = new URL(address);
    calls.push({url, options});
    if (status !== 200) return {status, ok: false};
    if (url.pathname === API) return {ok: true, json: async () => ({books: [BOOK]})};
    if (url.pathname === API + '/goldstein') return {
      ok: true,
      json: async () => ({book: BOOK, total: 1, page: 1, pages: 1, items: [problem]}),
    };
    if (url.pathname === API + '/goldstein/questions/1') return {
      ok: true,
      json: async () => ({
        ...problem, book: BOOK,
        en: {text: 'A body with mass $m$ <img src=x onerror=alert(1)>', review_status: 'source_compared'},
        ko: withKorean ? {text: '질량이 $m$인 물체', review_status: 'model_source_reviewed'} : null,
        media: [{id: 1, page: 4, kind: 'source_page', url: API + '/goldstein/questions/1/media/1'}],
      }),
    };
    assert.equal(url.pathname, API + '/goldstein/questions/1/media/1');
    return {ok: true, blob: async () => new w.Blob(['webp'], {type: 'image/webp'})};
  };
  w.eval(code + '\nwindow.mountPrivateTextbooks = mountPrivateTextbooks;');
  const root = w.document.querySelector('main');
  const controller = w.mountPrivateTextbooks(root, {
    apiOrigin: 'https://worker.test', lang: 'ko', theme: 'light',
    getToken: () => token, renderMath: node => math.push(node.textContent), onLogin: () => {},
  });
  t.after(() => { controller.dispose(); w.close(); });
  await flush();
  const click = async value => {
    const button = [...root.querySelectorAll('button')].find(b => b.textContent === value);
    assert.ok(button, value);
    button.click();
    await flush();
  };
  return {root, calls, revoked, math, click, controller, setToken: v => { token = v; }};
}

test('private archive URL is scoped to physics books with no external parameters', () => {
  assert.equal(nav.parse(PATH).params.get('view'), 'private-textbooks');
  assert.equal(nav.legacy(PATH + '&q=external'), PATH);
  assert.equal(nav.parse('#/archive/books/astro?view=private-textbooks').params.get('view'), null);
  assert.equal(nav.parse('#/archive/open?view=private-textbooks').params.get('view'), null);
});

test('problem selection renders language versions and sources remain guarded and opt-in', async t => {
  const demo = await setup(t);
  await demo.click(BOOK.title);
  await demo.click('1.1 · Sample');
  const reader = demo.root.querySelector('.al-private-prose');
  assert.equal(reader.textContent, '질량이 $m$인 물체');
  assert.match(demo.root.textContent, /AI 원문 대조/);
  await demo.click('English');
  assert.equal(reader.lang, 'en');
  assert.match(reader.textContent, /A body with mass/);
  assert.equal(reader.querySelector('img'), null);
  const initialCalls = demo.calls.length;
  await demo.click('한국어');
  assert.equal(reader.lang, 'ko');
  assert.equal(demo.calls.length, initialCalls);
  assert.equal(demo.root.querySelector('img'), null);
  await demo.click('이미지 보기');
  assert.equal(demo.root.querySelector('img').src, 'blob:private-source');
  assert.equal(demo.math.length, 3);
  for (const call of demo.calls) {
    assert.equal(call.url.origin, 'https://worker.test');
    assert.equal(call.options.headers.Authorization, 'Bearer private-test-token');
    assert.equal(call.options.cache, 'no-store');
    assert.equal(call.options.redirect, 'error');
    assert.doesNotMatch(call.url.href, /private-test-token/);
  }
  demo.setToken('');
  demo.controller.update({});
  await flush();
  assert.equal(demo.root.querySelector('img'), null);
  assert.equal(demo.root.querySelector('.al-private-prose'), null);
  assert.deepEqual(demo.revoked, ['blob:private-source']);
});

test('unsigned or denied sessions have no private text and missing Korean is labelled', async t => {
  const guest = await setup(t, {initialToken: ''});
  assert.equal(guest.calls.length, 0);
  assert.match(guest.root.textContent, /로그인/);
  const denied = await setup(t, {status: 403});
  assert.match(denied.root.textContent, /열람 권한이 없습니다/);
  assert.doesNotMatch(denied.root.textContent, /Private synthetic book/);
  const pending = await setup(t, {withKorean: false});
  await pending.click(BOOK.title);
  await pending.click('1.1 · Sample');
  await pending.click('한국어');
  assert.match(pending.root.querySelector('.al-private-prose').textContent, /준비 중/);
});
