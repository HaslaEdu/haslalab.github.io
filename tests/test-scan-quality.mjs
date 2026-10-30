import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { createRequire } from 'node:module';
import vm from 'node:vm';

const scannerSource = await fs.readFile(new URL('../sim/labscan/scanner.js', import.meta.url), 'utf8');
const scanner = await import('data:text/javascript;base64,' + Buffer.from(scannerSource).toString('base64'));
const require = createRequire(import.meta.url), Review = require('../sim/contest-review.js');

test('JPEG, PNG and WebP already under the upload limit keep their original bytes and MIME', async () => {
  for (const type of ['image/jpeg', 'image/png', 'image/webp']) {
    const original = new Blob(['original pencil strokes'], { type });
    assert.equal(await scanner.encodeUpload(original), original);
  }
});

function encodingFixture(width, height, sizeFor) {
  const saved = { document: globalThis.document, createImageBitmap: globalThis.createImageBitmap };
  const calls = [], bitmaps = [];
  globalThis.createImageBitmap = async (_blob, options) => {
    const bitmap = { width, height, options, closed: false, close() { this.closed = true; } };
    bitmaps.push(bitmap); return bitmap;
  };
  globalThis.document = { createElement() {
    const c = { width: 0, height: 0, getContext() { return { drawImage() {}, fillRect() {} }; },
      toBlob(resolve, type, quality) { calls.push({ width: c.width, height: c.height, type, quality }); resolve(new Blob([new Uint8Array(sizeFor(c, quality))], { type })); } };
    return c;
  } };
  return { calls, bitmaps, restore() { Object.assign(globalThis, saved); } };
}

test('oversized 200dpi A4 tries quality settings without reducing document resolution', async () => {
  const fixture = encodingFixture(1654, 2339, (_canvas, q) => q > .84 ? 2000000 : 1700000);
  try {
    const out = await scanner.encodeUpload(new Blob([new Uint8Array(2100000)], { type: 'image/png' }));
    assert.equal(out.type, 'image/jpeg'); assert.equal(out.size, 1700000);
    assert.deepEqual(fixture.calls.map(x => x.quality), [.92, .88, .84]);
    assert.ok(fixture.calls.every(x => x.width === 1654 && x.height === 2339));
    assert.equal(fixture.bitmaps[0].options.imageOrientation, 'from-image');
    assert.equal(fixture.bitmaps[0].closed, true);
  } finally { fixture.restore(); }
});

test('a difficult photo stops at 200dpi instead of silently making a smaller unreadable upload', async () => {
  const fixture = encodingFixture(4000, 6000, () => 2000000);
  try {
    await assert.rejects(scanner.encodeUpload(new Blob([new Uint8Array(2200000)], { type: 'image/jpeg' })), e => e.code === 'image_too_big');
    assert.deepEqual([...new Set(fixture.calls.map(x => Math.max(x.width, x.height)))], [2400, 2339]);
    assert.ok(fixture.calls.every(x => x.quality >= .76));
    assert.equal(fixture.bitmaps[0].closed, true);
  } finally { fixture.restore(); }
});

test('white paper with crisp writing is not mistaken for reflected glare', () => {
  const W = 160, H = 220, data = new Uint8ClampedArray(W * H * 4).fill(255);
  for (let y = 20; y < H - 20; y += 12) for (let x = 15; x < W - 15; x++) {
    if (x % 7 < 3) { const i = (y * W + x) * 4; data[i] = data[i + 1] = data[i + 2] = 30; }
  }
  const q = scanner.inspectDocumentPixels(data, W, H);
  assert.ok(q.glare > .3); assert.ok(q.focus >= 22); assert.equal(q.ok, true); assert.equal(q.hint, null);
  data.fill(230); for (let i = 3; i < data.length; i += 4) data[i] = 255;
  assert.equal(scanner.inspectDocumentPixels(data, W, H).ok, false);
});

function pixelFixture() {
  const saved = { document: globalThis.document, Image: globalThis.Image, ImageData: globalThis.ImageData, createImageBitmap: globalThis.createImageBitmap };
  const decode = url => JSON.parse(Buffer.from(url.split(',')[1], 'base64').toString());
  class Canvas {
    width = 0; height = 0; data = null;
    ensure() { if (!this.data || this.data.length !== this.width * this.height * 4) this.data = new Uint8ClampedArray(this.width * this.height * 4); }
    getContext() { const c = this; return {
      drawImage(image, _x, _y, width = image.width, height = image.height) {
        c.ensure(); const source = image.data;
        for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
          const s = (Math.min(image.height - 1, Math.floor(y / height * image.height)) * image.width + Math.min(image.width - 1, Math.floor(x / width * image.width))) * 4;
          c.data.set(source.slice(s, s + 4), (y * c.width + x) * 4);
        }
      },
      getImageData() { c.ensure(); return { data: c.data, width: c.width, height: c.height }; },
      putImageData(image) { c.data = new Uint8ClampedArray(image.data); },
    }; }
    payload() { this.ensure(); return { width: this.width, height: this.height, data: [...this.data] }; }
    toDataURL(type) { return 'data:' + type + ';base64,' + Buffer.from(JSON.stringify(this.payload())).toString('base64'); }
    toBlob(resolve, type) { resolve(new Blob([JSON.stringify(this.payload())], { type })); }
  }
  globalThis.document = { createElement: () => new Canvas() };
  globalThis.ImageData = class { constructor(data, width, height) { Object.assign(this, { data, width, height }); } };
  globalThis.Image = class { set src(url) { Object.assign(this, decode(url)); this.data = new Uint8ClampedArray(this.data); queueMicrotask(() => this.onload()); } };
  globalThis.createImageBitmap = async file => { const p = JSON.parse(await file.text()); return { ...p, data: new Uint8ClampedArray(p.data), close() {} }; };
  return { decode, restore() { Object.assign(globalThis, saved); } };
}

test('manual mode changes reuse a lossless captured baseline and produce stable original-colour output', async () => {
  const fixture = pixelFixture(), W = 100, H = 141;
  const pixels = new Uint8ClampedArray(W * H * 4).fill(255);
  const pencil = (60 * W + 45) * 4; pixels[pencil] = 177; pixels[pencil + 1] = 183; pixels[pencil + 2] = 191;
  const corners = [{ x: 0, y: 0 }, { x: W - 1, y: 0 }, { x: 0, y: H - 1 }, { x: W - 1, y: H - 1 }];
  try {
    const file = new Blob([JSON.stringify({ width: W, height: H, data: [...pixels] })], { type: 'image/png' });
    const first = await scanner.processShot(file, { corners, mode: 'original', dpi: 12 });
    assert.ok(first.baseUrl.startsWith('data:image/png;'));
    assert.deepEqual(fixture.decode(first.baseUrl).data.slice(pencil, pencil + 4), [177, 183, 191, 255]);
    const a = await scanner.reprocess(first.baseUrl, first.corners, 'original', 12);
    await scanner.reprocess(first.baseUrl, first.corners, 'mono', 12);
    const b = await scanner.reprocess(first.baseUrl, first.corners, 'original', 12);
    assert.deepEqual(new Uint8Array(await a.blob.arrayBuffer()), new Uint8Array(await b.blob.arrayBuffer()));
    assert.equal(a.width, 99); assert.equal(a.height, 140);
  } finally { fixture.restore(); }
});

test('manual marker coordinates preserve the paper margins outside the printed squares', async () => {
  const fixture = pixelFixture(), W = 100, H = 141, pixels = new Uint8ClampedArray(W * H * 4).fill(255);
  for (let y = 0; y < 4; y++) for (let x = 0; x < W; x++) { const i = (y * W + x) * 4; pixels[i] = 180; pixels[i + 1] = 20; pixels[i + 2] = 20; }
  const m = scanner.MARKER_INSET, points = [{ x: m.left * W, y: m.top * H }, { x: m.right * W, y: m.top * H }, { x: m.left * W, y: m.bottom * H }, { x: m.right * W, y: m.bottom * H }];
  const base = 'data:image/png;base64,' + Buffer.from(JSON.stringify({ width: W, height: H, data: [...pixels] })).toString('base64');
  try {
    const marker = await scanner.reprocess(base, points, 'original', 12, m);
    const page = await scanner.reprocess(base, points, 'original', 12, null);
    const a = JSON.parse(await marker.blob.text()), b = JSON.parse(await page.blob.text()), at = 49 * 4;
    assert.ok(a.data[at + 1] < 100, 'red top margin survives the marker inset');
    assert.ok(b.data[at + 1] > 240, 'the same points treated as paper edges would crop that margin');
  } finally { fixture.restore(); }
});

test('the desktop review sends PNG as PNG and retains the dedicated QR token header', async () => {
  const calls = [], body = new Blob(['lossless mono'], { type: 'image/png' });
  const client = Review.createClient({ fetch: async (url, options) => { calls.push({ url, ...options }); return { ok: true, json: async () => ({}) }; } });
  await client.upload('fixture-token', 'Q1', body);
  assert.equal(calls[0].headers['Content-Type'], 'image/png');
  assert.equal(calls[0].headers['X-Lab-Token'], 'fixture-token');
  assert.equal(calls[0].body, body); assert.ok(!calls[0].url.includes('fixture-token'));
});

test('a saved photo with failed OCR reports storage/provider failure instead of claiming it was read', () => {
  const failed = { ocr_status: 'failed', ocr_error: 'ocr_storage_limit', legible: 'good' };
  assert.match(Review.uploadWarning(failed), /사진은 보관.*합계 용량/);
  assert.match(Review.uploadWarning(failed, 'en'), /photo was saved.*storage limit/i);
  assert.match(Review.uploadWarning({ ocr_status: 'failed', read: { ocr: { error: 'ocr_storage_limit' } } }), /합계 용량/);
  assert.match(Review.uploadWarning({ ocr_status: 'failed', ocr_error: 'provider_error' }), /글자를 읽지 못/);
  assert.equal(Review.uploadWarning({ ocr_status: 'done', legible: 'good' }), '');
  assert.equal(Review.uploadWarning({ ocr_status: 'unpaid' }), '');
});

test('a newer phone photo survives late progress, correction errors and rotation from older photos', async () => {
  const html = await fs.readFile(new URL('../sim/scan.html', import.meta.url), 'utf8');
  const script = html.match(/<script type="module">([\s\S]*?)<\/script>/)[1].replace(/^import .*?;\s*$/m, '');
  const nodes = new Map(), processed = [], rebuilt = [], rotated = [], revoked = [];
  const node = id => {
    if (!nodes.has(id)) nodes.set(id, { innerHTML: '', style: {}, classList: { toggle() {} }, querySelectorAll: () => [], querySelector: () => node('child'), remove() {}, click() {} });
    return nodes.get(id);
  };
  let nextURL = 0;
  class FixtureURL extends URL {
    static createObjectURL() { return 'blob:fixture/' + (++nextURL); }
    static revokeObjectURL(url) { revoked.push(url); }
  }
  const context = vm.createContext({
    URL: FixtureURL, URLSearchParams, Blob, console,
    document: { getElementById: node, querySelector: node, createElement: () => node('element'), body: { append() {} }, documentElement: {} },
    location: { hash: '', pathname: '/sim/scan.html' }, history: { replaceState() {} },
    navigator: { language: 'ko' }, window: { HLExamNetwork: require('../sim/exam-network.js') },
    sessionStorage: { getItem: () => null }, localStorage: { getItem: () => null },
    setInterval() {}, setTimeout() {}, clearTimeout() {},
    canProcess: () => true,
    processShot: (file, options) => new Promise((resolve, reject) => processed.push({ file, options, resolve, reject })),
    reprocess: (...args) => new Promise((resolve, reject) => rebuilt.push({ args, resolve, reject })),
    rotatePhoto: file => new Promise(resolve => rotated.push({ file, resolve })),
  });
  new vm.Script(script + '\nglobalThis.phone = { take, redo, releaseShot, getShot: () => shot, getMode: () => mode };').runInContext(context);
  const file = label => new Blob([label], { type: 'image/png' });
  const result = label => ({ blob: file(label), previewUrl: label, baseUrl: label, corners: [], method: 'page', autoScore: 1 });
  const a = file('a'), b = file('b'), c = file('c'), d = file('d');
  const takingA = context.phone.take(a), urlA = context.phone.getShot().originalUrl;
  const takingB = context.phone.take(b), urlB = context.phone.getShot().originalUrl;
  processed[0].options.onProgress(95);
  assert.equal(context.phone.getShot().pct, 0, 'old progress cannot update the new photo');
  processed[0].resolve(result('old-a')); await takingA;
  assert.equal(context.phone.getShot().file, b); assert.equal(context.phone.getShot().busy, true);
  processed[1].resolve(result('current-b')); await takingB;
  assert.equal(context.phone.getShot().previewUrl, 'current-b');

  const editingB = context.phone.redo([], 'mono'), takingC = context.phone.take(c);
  rebuilt[0].reject(new Error('older correction failed')); await editingB;
  assert.equal(context.phone.getShot().file, c); assert.equal(context.phone.getShot().busy, true);
  assert.equal(context.phone.getMode(), 'clean');
  processed[2].resolve(result('current-c')); await takingC;

  const rotatingC = node('rotate').onclick(), takingD = context.phone.take(d);
  rotated[0].resolve(file('rotated-old-c')); await rotatingC;
  assert.equal(processed.length, 4, 'an old rotation cannot start another take over the newest photo');
  assert.equal(context.phone.getShot().file, d);
  processed[3].resolve(result('current-d')); await takingD;
  assert.equal(context.phone.getShot().previewUrl, 'current-d');
  assert.ok(revoked.includes(urlA)); assert.ok(revoked.includes(urlB));
  context.phone.releaseShot(); assert.equal(context.phone.getShot(), null);
});
