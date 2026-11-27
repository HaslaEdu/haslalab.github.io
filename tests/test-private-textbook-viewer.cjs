const test = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {resolve} = require('node:path');
const {createRequire} = require('node:module');
const {JSDOM} = createRequire(resolve(__dirname, '../community/package.json'))('jsdom');
const nav = require('../archive-navigation.js');

const exerciseData = readFileSync(resolve(__dirname, '../feynman-exercises.js'), 'utf8').replace(/^export /gm, '');
const code = exerciseData + '\n' + readFileSync(resolve(__dirname, '../archive-private-textbooks.js'), 'utf8')
  .replace(/^import .*;\r?\n/m, '').replace(/^export /gm, '');
const API = '/api/problem-bank/private-textbooks/books';
const PATH = '#/archive/books/phys?view=private-textbooks';
const BOOK = {id: 'goldstein', title: 'Private synthetic book', count: 1, korean_count: 1};
const FEYNMAN = {id: 'feynman', title: 'Sample lectures', kind: 'lectures', count: 3, korean_count: 0,
                 volumes: [1, 2, 3].map(number => ({number, title: 'Subject ' + number}))};
const problem = {ordinal: 1, number: '1.1', label: 'Sample', chapter: 'Chapter 1', has_korean: true};
const flush = () => new Promise(done => setImmediate(done));

async function setup(t, {initialToken = 'private-test-token', status = 200, withKorean = true, feynman = false,
                         exercises = false, multiChapter = false} = {}) {
  const dom = new JSDOM('<main></main>', {
    url: 'https://haslalab.org/' + PATH, runScripts: 'outside-only',
  });
  const w = dom.window;
  let token = initialToken;
  const calls = [], revoked = [], math = [];
  w.URL.createObjectURL = () => 'blob:private-source';
  w.URL.revokeObjectURL = url => revoked.push(url);
  w.HTMLElement.prototype.scrollIntoView = () => {};
  w.fetch = async (address, options) => {
    const url = new URL(address);
    calls.push({url, options});
    if (status !== 200) return {status, ok: false};
    if (url.pathname === API) return {ok: true, json: async () => ({books: [BOOK, FEYNMAN]})};
    if (url.pathname === API + '/feynman/workbook') return {ok: true, json: async () => ({
      count: 3, korean_count: 1, chapters: [{number: 1, title: 'Atoms', volume: 1, problems: [6, 8]},
        {number: 2, title: 'Heat', volume: 2, problems: [15]}],
      parts: [{start: 1, end: 10}, {start: 11, end: 25}], contents: 2, answers: 21,
    })};
    if (url.pathname === API + '/feynman/workbook/questions/2.1') return {ok: true, json: async () => ({
      number: '2.1', ko: {text: '온도 $T$를 구하라.', review_status: 'source_compared'},
    })};
    if (url.pathname === API + '/feynman/workbook/parts/2') return {
      ok: true, blob: async () => new w.Blob(['%PDF-'], {type: 'application/pdf'}),
    };
    const volume = /^\/([123])(\/pdf)?$/.exec(url.pathname.slice((API + '/feynman/volumes').length));
    if (url.pathname.startsWith(API + '/feynman/volumes') && volume) {
      const number = Number(volume[1]);
      if (volume[2]) return {ok: true, blob: async () => new w.Blob(['%PDF-'], {type: 'application/pdf'})};
      return {ok: true, json: async () => ({...FEYNMAN.volumes[number - 1],
        chapters: [{number: 1, title: 'Chapter in volume ' + number, page: 30 + number}]})};
    }
    if (url.pathname === API + '/goldstein') return {
      ok: true,
      json: async () => ({book: BOOK, total: multiChapter ? 2 : 1, page: 1, pages: 1,
        items: multiChapter ? [problem, {...problem, ordinal: 2, number: '2.1', chapter: 'Chapter 2'}] : [problem]}),
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
    params: new URLSearchParams(feynman ? 'book=feynman' + (exercises ? '&section=exercises' : '') : ''),
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

test('unsigned or denied sessions have no private text and only available languages are selectable', async t => {
  const guest = await setup(t, {initialToken: ''});
  assert.equal(guest.calls.length, 0);
  assert.match(guest.root.textContent, /로그인/);
  const denied = await setup(t, {status: 403});
  assert.match(denied.root.textContent, /열람 권한이 없습니다/);
  assert.doesNotMatch(denied.root.textContent, /Private synthetic book/);
  const pending = await setup(t, {withKorean: false});
  await pending.click(BOOK.title);
  await pending.click('1.1 · Sample');
  assert.equal(pending.root.querySelector('.al-private-prose').lang, 'en');
  assert.ok(![...pending.root.querySelectorAll('button')].some(button => button.textContent === '한국어'));
});

test('Feynman owner chooses a volume and jumps to its chapter in the authenticated PDF', async t => {
  const demo = await setup(t, {feynman: true});
  const nav = demo.root.querySelector('nav[aria-label="권 선택"]');
  assert.deepEqual([...nav.querySelectorAll('button')].map(button => button.textContent), ['Volume 1', 'Volume 2', 'Volume 3', '연습문제']);
  assert.equal(demo.calls.length, 1);
  await demo.click('Volume 2');
  assert.equal(demo.root.ownerDocument.activeElement.textContent, 'Volume 2');
  assert.match(demo.root.textContent, /Chapter in volume 2/);
  assert.doesNotMatch(demo.root.textContent, /Chapter in volume 1/);
  assert.ok(demo.root.querySelector('a[href="https://www.feynmanlectures.caltech.edu/II_toc.html"]'));
  await demo.click('1. Chapter in volume 2');
  assert.equal(demo.root.querySelector('iframe').getAttribute('src'), 'blob:private-source#page=32');
  assert.equal(demo.calls.at(-1).url.pathname, API + '/feynman/volumes/2/pdf');
  assert.equal(demo.calls.at(-1).options.headers.Authorization, 'Bearer private-test-token');
  await demo.click('Volume 3');
  assert.match(demo.root.textContent, /Chapter in volume 3/);
  assert.deepEqual(demo.revoked, ['blob:private-source']);
});

test('Feynman guests select the same three volumes and only see official reading links', async t => {
  const demo = await setup(t, {feynman: true, initialToken: ''});
  const roman = ['I', 'II', 'III'];
  for (const [offset, label] of roman.entries()) {
    await demo.click('Volume ' + (offset + 1));
    assert.ok(demo.root.querySelector('a[href="https://www.feynmanlectures.caltech.edu/' + label + '_toc.html"]'));
    assert.equal(demo.root.querySelector('iframe'), null);
  }
  assert.equal(demo.calls.length, 0);
});

test('Feynman’s public exercises show English by default and keep bilingual search', async t => {
  const path = PATH + '&book=feynman&section=exercises';
  assert.equal(nav.legacy(path), null);
  assert.equal(nav.parse(PATH + '&book=goldstein&section=exercises').params.get('section'), null);
  const demo = await setup(t, {feynman: true, exercises: true, initialToken: ''});
  const section = demo.root.querySelector('.al-feynman-exercises');
  const links = [...section.querySelectorAll('details a')];
  assert.equal(links.length, 47);
  assert.equal(new Set(links.map(a => a.href)).size, 47);
  assert.ok(links.every(a => a.href.startsWith('https://www.feynmanlectures.caltech.edu/info/exercises/')));
  const field = section.querySelector('input[type=search]');
  field.value = '강제 진동';
  field.dispatchEvent(new field.ownerDocument.defaultView.Event('input'));
  assert.equal(section.querySelectorAll('details').length, 1);
  const row = section.querySelector('details');
  assert.equal(row.lang, 'en');
  assert.equal(section.querySelector('nav[aria-label="목차"]').textContent.includes('Dynamics and oscillations'), true);
  assert.match(row.textContent, /Driven pendulum.*I · 23/);
  assert.equal(row.querySelector('a').href, 'https://www.feynmanlectures.caltech.edu/info/exercises/forced_pendulum.html');
  assert.equal(demo.calls.length, 0);
});

test('the private Feynman workbook searches by exercise number and opens its verified PDF part', async t => {
  const demo = await setup(t, {feynman: true, exercises: true});
  const workbook = demo.root.querySelector('.al-feynman-workbook');
  assert.match(workbook.textContent, /3 문제/);
  assert.equal(workbook.querySelector('iframe').hidden, true);
  const search = workbook.querySelector('input[type=search]');
  search.value = '2.1';
  search.dispatchEvent(new search.ownerDocument.defaultView.Event('input'));
  assert.match(workbook.querySelector('nav[aria-label="목차"] [aria-current=true]').textContent, /Heat/);
  await demo.click('2.1');
  assert.equal(workbook.querySelector('iframe').getAttribute('src'), 'blob:private-source#page=5');
  assert.equal(demo.calls.at(-1).url.pathname, API + '/feynman/workbook/parts/2');
  assert.equal(workbook.querySelector('button[aria-pressed=true]:last-child').textContent, 'English');
  assert.deepEqual(demo.math, []);
  await demo.click('한국어');
  assert.match(workbook.textContent, /온도 \$T\$를 구하라/);
  assert.deepEqual(demo.math, ['온도 $T$를 구하라.']);
});

test('private question lists can select a chapter from the same table-of-contents layout', async t => {
  const demo = await setup(t, {multiChapter: true});
  await demo.click(BOOK.title);
  const navigator = demo.root.querySelector('nav[aria-label="목차"]');
  const choose = [...navigator.querySelectorAll('button')].find(b => b.textContent.startsWith('Chapter 2'));
  choose.click();
  const results = demo.root.querySelector('.al-private-chapters .al-source-main');
  assert.match(results.textContent, /2\.1 · Sample/);
  assert.doesNotMatch(results.textContent, /1\.1 · Sample/);
});
