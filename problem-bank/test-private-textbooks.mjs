import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash, webcrypto} from 'node:crypto';
import worker from './worker.mjs';

if (!globalThis.crypto) globalThis.crypto = webcrypto;
const ROOT = '/api/problem-bank/private-textbooks/books';
const PREFIX = 'textbook-intake/2026-11-21/viewer-v1';
const AUTH = 'a'.repeat(32);
const hash = input => createHash('sha256').update(input).digest('hex');
const bytes = value => Buffer.from(JSON.stringify(value));
const IMG = Buffer.from('RIFF0123WEBPsynthetic');
const OBJ = Buffer.concat([Buffer.from('lead'), IMG, Buffer.from('trail')]);
const PACK = hash(OBJ);
const item = {ordinal: 1, number: '1.1', label: 'Synthetic sample', chapter: 'Dynamics', has_korean: true};
const row = {
  ...item,
  en: {text: 'The question in English.', review_status: 'source_compared'},
  ko: {text: '한국어 문제 본문.', review_status: 'model_source_reviewed'},
  media: [{id: 1, page: 7, kind: 'source_page', pack_sha256: PACK, pack_size: OBJ.length,
           offset: 4, length: IMG.length, sha256: hash(IMG)}],
};
const directory = bytes([item]);
const batch = bytes([row]);
const manifest = bytes({
  schema: 'haslalab-private-textbook-viewer/v1',
  books: [{id: 'goldstein', title: 'Private source', count: 1, korean_count: 1,
           index_sha256: hash(directory), batches: [hash(batch)]}],
});
const RELEASE = hash(manifest);
const BASE = PREFIX + '/releases/' + RELEASE;

function setup(user = {id: 19, role: 'admin'}, overrides = {}) {
  const calls = [];
  const data = new Map([
    [BASE + '/manifest.json', manifest], [BASE + '/goldstein/index.json', directory],
    [BASE + '/goldstein/batches/0.json', batch], [PREFIX + '/media/' + PACK + '.bin', OBJ],
  ]);
  const env = {
    BANK_TEXTBOOK_OWNER_IDS: '19',
    BANK_TEXTBOOK_RELEASE: RELEASE,
    COMMUNITY: {fetch: async () => Response.json({user})},
    LIBRARY: {
      async get(key, options) {
        calls.push(key);
        const value = data.get(key);
        if (!value) return null;
        const range = options?.range;
        const payload = range ? value.subarray(range.offset, range.offset + range.length) : value;
        return {size: value.length, range, arrayBuffer: async () => Uint8Array.from(payload).buffer};
      },
    },
    ...overrides,
  };
  const call = (path, token = AUTH) => worker.fetch(new Request('https://example.test' + path, {
    headers: token ? {Authorization: 'Bearer ' + token} : {},
  }), env);
  return {call, calls, data};
}

test('private books, details and media all authenticate before any object reads', async () => {
  for (const path of [ROOT, ROOT + '/goldstein', ROOT + '/goldstein/questions/1',
                      ROOT + '/goldstein/questions/1/media/1', ROOT + '/feynman/volumes/1',
                      ROOT + '/feynman/volumes/1/pdf']) {
    const guest = setup();
    const noToken = await guest.call(path, null);
    assert.equal(noToken.status, 401);
    assert.equal(noToken.headers.get('cache-control'), 'private, no-store');
    assert.equal(guest.calls.length, 0);
    for (const account of [{id: 19, role: 'user'}, {id: 20, role: 'admin'}]) {
      const member = setup(account);
      assert.equal((await member.call(path)).status, 403);
      assert.equal(member.calls.length, 0);
    }
  }
});

test('Feynman is one catalogue entry with separate verified volumes and PDFs', async () => {
  const pdfs = [1, 2, 3].map(number => Buffer.from('%PDF-1.7 synthetic volume ' + number));
  const volumes = pdfs.map((pdf, offset) => ({
    number: offset + 1, title: 'Subject ' + (offset + 1), pages: 40,
    chapters: [{number: 1, title: 'Chapter in volume ' + (offset + 1), page: 12 + offset}],
    pdf_size: pdf.length, pdf_sha256: hash(pdf),
  }));
  const fixture = JSON.parse(manifest);
  fixture.books.push({id: 'feynman', kind: 'lectures', title: 'Feynman', count: 3, korean_count: 0, volumes});
  const raw = bytes(fixture), release = hash(raw);
  const state = setup(undefined, {BANK_TEXTBOOK_RELEASE: release});
  state.data.set(PREFIX + '/releases/' + release + '/manifest.json', raw);
  for (const [offset, volume] of volumes.entries()) {
    state.data.set(PREFIX + '/documents/' + volume.pdf_sha256 + '.pdf', pdfs[offset]);
  }
  const catalogue = await (await state.call(ROOT)).json();
  assert.deepEqual(catalogue.books.map(book => book.id), ['goldstein', 'feynman']);
  assert.deepEqual(catalogue.books[1].volumes, volumes.map(({number, title}) => ({number, title})));
  const detail = ROOT + '/feynman/volumes/2';
  const chapter = await (await state.call(detail)).json();
  assert.deepEqual(chapter.chapters, volumes[1].chapters);
  assert.equal(chapter.pdf_sha256, undefined);
  const original = await state.call(detail + '/pdf');
  assert.equal(original.headers.get('content-type'), 'application/pdf');
  assert.equal(original.headers.get('cache-control'), 'private, no-store');
  assert.deepEqual(Buffer.from(await original.arrayBuffer()), pdfs[1]);
  assert.equal((await state.call(detail + '/pdf?page=1')).status, 400);
  assert.equal((await state.call(ROOT + '/feynman/volumes/4')).status, 404);
  state.data.set(PREFIX + '/documents/' + volumes[1].pdf_sha256 + '.pdf', pdfs[2]);
  assert.equal((await state.call(detail + '/pdf')).status, 503);
});

test('the private release is disabled without an explicit owner and verified manifest digest', async () => {
  const owner = {id: 19, role: 'admin'};
  const absent = setup(owner, {BANK_TEXTBOOK_OWNER_IDS: ''});
  assert.equal((await absent.call(ROOT)).status, 403);
  assert.equal(absent.calls.length, 0);
  const disabled = setup(owner, {BANK_TEXTBOOK_RELEASE: '../../malformed'});
  assert.equal((await disabled.call(ROOT)).status, 503);
  assert.equal(disabled.calls.length, 0);
});

test('invalid object selectors and path traversal do not reach private storage', async () => {
  for (const suffix of ['/goldstein%2f..%2fsecret', '/goldstein/questions/../%2e%2e/private',
                        '/goldstein/questions/01', '/goldstein/questions/1/media/%2e%2e%2fsecret',
                        '/goldstein?page=1&page=2', '/goldstein?key=sources/secret']) {
    const state = setup();
    const result = await state.call(ROOT + suffix);
    assert.ok(result.status >= 400, suffix);
    assert.equal(state.calls.length, 0, suffix);
  }
});

test('owner can browse, filter and fetch privately selected bilingual text and verified image slices', async () => {
  const state = setup();
  const books = await state.call(ROOT);
  assert.equal(books.status, 200);
  assert.equal((await books.json()).books[0].count, 1);
  assert.equal(books.headers.get('x-robots-tag'), 'noindex, nofollow, noarchive');
  const list = await state.call(ROOT + '/goldstein?q=1.1&page=1');
  assert.equal((await list.json()).items[0].ordinal, 1);
  const detail = await state.call(ROOT + '/goldstein/questions/1');
  const payload = await detail.json();
  assert.deepEqual(payload.en, row.en);
  assert.deepEqual(payload.ko, row.ko);
  assert.deepEqual(payload.media, [
    {id: 1, page: 7, kind: 'source_page', label: '', url: ROOT + '/goldstein/questions/1/media/1'},
  ]);
  const asset = await state.call(payload.media[0].url);
  assert.equal(asset.headers.get('cache-control'), 'private, no-store');
  assert.equal(asset.headers.get('content-type'), 'image/webp');
  assert.deepEqual(Buffer.from(await asset.arrayBuffer()), IMG);
});

test('corrupt JSON and original media never produce viewer content', async () => {
  const metadata = setup();
  metadata.data.set(BASE + '/goldstein/batches/0.json', bytes([{...row, en: {text: 'different'}}]));
  assert.equal((await metadata.call(ROOT + '/goldstein/questions/1')).status, 503);
  const asset = setup();
  asset.data.set(PREFIX + '/media/' + PACK + '.bin', Buffer.alloc(OBJ.length, 1));
  assert.equal((await asset.call(ROOT + '/goldstein/questions/1/media/1')).status, 503);
});

test('a verified delta uses the base index and serves its revised problem batch', async () => {
  const adaptation = {text: '한국어 학습 문항.', review_status: 'study_adapted'};
  const revisedBatch = bytes([{...row, ko: adaptation}]);
  const book = {...JSON.parse(manifest).books[0], batches: [hash(revisedBatch)]};
  const delta = bytes({schema: JSON.parse(manifest).schema, inherit_from: RELEASE, books: [book]});
  const release = hash(delta);
  const base = PREFIX + '/releases/' + release;
  const state = setup(undefined, {BANK_TEXTBOOK_RELEASE: release});
  state.data.set(base + '/manifest.json', delta);
  state.data.set(base + '/goldstein/batches/0.json', revisedBatch);
  assert.equal((await state.call(ROOT + '/goldstein')).status, 200);
  assert.ok(state.calls.includes(BASE + '/goldstein/index.json'));
  const detail = await state.call(ROOT + '/goldstein/questions/1');
  assert.deepEqual((await detail.json()).ko, adaptation);
  assert.ok(!state.calls.includes(BASE + '/goldstein/batches/0.json'));
});
