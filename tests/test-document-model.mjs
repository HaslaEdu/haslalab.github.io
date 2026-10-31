import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { DOCUMENT_ASSETS, decodeDocumentHeatmap, documentGeometry, refineDocumentEdges } from '../sim/labscan/document-model.mjs';
import { createDocumentDetector } from '../sim/labscan/document-detector.mjs';
const scannerSource=await readFile(new URL('../sim/labscan/scanner.js',import.meta.url),'utf8');
const scanner=await import('data:text/javascript;base64,'+Buffer.from(scannerSource).toString('base64'));

test('vendored model and CPU runtime match pinned upstream bytes and redistribution notices', async () => {
  for (const asset of [DOCUMENT_ASSETS.model, DOCUMENT_ASSETS.wasm]) {
    const data = await readFile(new URL(asset.path, new URL('../sim/labscan/document-model.mjs', import.meta.url)));
    assert.equal(data.byteLength, asset.bytes); assert.equal(createHash('sha256').update(data).digest('hex'), asset.sha256);
  }
  for (const key of ['runtime', 'runtimeModule']) {
    const data = await readFile(new URL(DOCUMENT_ASSETS[key], new URL('../sim/labscan/document-model.mjs', import.meta.url)));
    assert.equal(data.byteLength, DOCUMENT_ASSETS[key+'Bytes']);assert.equal(createHash('sha256').update(data).digest('hex'),DOCUMENT_ASSETS[key+'Sha256']);
  }
  assert.match(await readFile(new URL('../vendor/docaligner-lcnet/LICENSE', import.meta.url), 'utf8'), /Apache License/);
  assert.match(await readFile(new URL('../vendor/onnxruntime-web-1.20.1/LICENSE', import.meta.url), 'utf8'), /MIT License/);
});

test('four learned corner channels decode independently in source-image pixels and reject low confidence', () => {
  const heatmap = new Float32Array(4 * 128 * 128), points = [[16, 12], [110, 20], [20, 114], [105, 107]];
  points.forEach(([x, y], channel) => { heatmap[channel * 16384 + y * 128 + x] = .9; });
  const value = decodeDocumentHeatmap(heatmap, [1, 4, 128, 128], 1280, 960);
  points.forEach(([x, y], index) => assert.deepEqual(value.corners[index], { x: (x + .5) * 10, y: (y + .5) * 7.5 }));
  heatmap[3 * 16384 + 107 * 128 + 105] = .1;
  assert.equal(decodeDocumentHeatmap(heatmap, [1, 4, 128, 128], 1280, 960), null);
  assert.equal(decodeDocumentHeatmap(new Float32Array(10), [1, 4, 128, 128], 100, 100), null);
});

test('document geometry accepts real perspective and arbitrary document proportions without a physical A4 claim', () => {
  const trapezoid = [{ x: 170, y: 125 }, { x: 675, y: 210 }, { x: 110, y: 1040 }, { x: 730, y: 970 }];
  assert.ok(documentGeometry(trapezoid, 900, 1200));
  assert.ok(documentGeometry([{ x: 100, y: 100 }, { x: 400, y: 100 }, { x: 100, y: 400 }, { x: 400, y: 400 }], 600, 600));
  assert.equal(documentGeometry(Array(4).fill({ x: 100, y: 100 }), 600, 600), null);
  assert.equal(documentGeometry([{ x: 0, y: 0 }, ...trapezoid.slice(1)], 900, 1200), null);
});

test('auto crop preserves observed proportions while A4 is an explicit format choice', () => {
  const square=[{x:20,y:30},{x:220,y:30},{x:20,y:230},{x:220,y:230}];
  assert.deepEqual(scanner.documentOutputSize(square,100,'auto'),{width:100,height:100});
  assert.deepEqual(scanner.documentOutputSize(square,100,'a4'),{width:100,height:141});
  const landscape=[{x:20,y:30},{x:420,y:30},{x:20,y:230},{x:420,y:230}];
  assert.deepEqual(scanner.documentOutputSize(landscape,100,'auto'),{width:200,height:100});
  const m=scanner.MARKER_INSET,W=200,H=200*scanner.A4_RATIO;
  const markers=[{x:W*m.left,y:H*m.top},{x:W*m.right,y:H*m.top},{x:W*m.left,y:H*m.bottom},{x:W*m.right,y:H*m.bottom}];
  assert.deepEqual(scanner.documentOutputSize(markers,100,'auto',m),{width:100,height:141});
});

test('native-pixel edge refinement corrects a shifted learned proposal without relying on a 256px crop', () => {
  const width = 500, height = 700, gray = new Uint8Array(width * height).fill(50);
  for (let y = 80; y < 620; y++) for (let x = 90; x < 410; x++) gray[y * width + x] = 230;
  const proposed = [{ x: 96, y: 84 }, { x: 416, y: 84 }, { x: 96, y: 624 }, { x: 416, y: 624 }];
  const refined = refineDocumentEdges(gray, width, height, proposed);
  assert.ok(refined.edgeSupport > .9);
  const truth = [{ x: 90, y: 80 }, { x: 410, y: 80 }, { x: 90, y: 620 }, { x: 410, y: 620 }];
  refined.corners.forEach((point, i) => assert.ok(Math.hypot(point.x - truth[i].x, point.y - truth[i].y) < 3));
});

function fixture(timeoutMs = 1000) {
  const calls = [], workers = [];
  const detector = createDocumentDetector({ timeoutMs, workerFactory(url) {
    assert.match(url.pathname, /document-worker\.mjs$/);
    const worker = { postMessage(message) { calls.push(message); }, terminate() { this.terminated = true; } };
    workers.push(worker); return worker;
  } });
  return { detector, calls, workers, reply(index, result) { workers.at(-1).onmessage({ data: { type: 'result', id: calls[index].id, result } }); } };
}
const tick = () => new Promise(resolve => setImmediate(resolve));

test('detector assets remain lazy and worker responses are isolated by request identity', async () => {
  const old = globalThis.createImageBitmap;
  globalThis.createImageBitmap = async () => ({ close() {} });
  const f = fixture();
  try {
    assert.equal(f.workers.length, 0);
    const first = f.detector.detect({}); await tick();
    assert.equal(f.workers.length, 1); assert.equal(f.calls[0].type, 'detect');
    f.reply(0, { corners: 'first-only' }); assert.deepEqual(await first, { corners: 'first-only' });
    const second = f.detector.detect({}); await tick();
    f.reply(0, { corners: 'stale' }); f.reply(1, { corners: 'second-only' });
    assert.deepEqual(await second, { corners: 'second-only' });
  } finally { f.detector.dispose(); globalThis.createImageBitmap = old; }
});

test('cancelled camera requests ignore late corners and keep the warm model available for a still photo', async () => {
  const old = globalThis.createImageBitmap; globalThis.createImageBitmap = async () => ({ close() {} });
  const f = fixture(), controller = new AbortController();
  try {
    const first = f.detector.detect({}, { signal: controller.signal }); await tick(); controller.abort();
    await assert.rejects(first, error => error.name === 'AbortError');
    const second = f.detector.detect({}); await tick();
    f.reply(0, { wrong: true }); f.reply(2, { correct: true });
    assert.deepEqual(await second, { correct: true }); assert.equal(f.workers.length, 1);
  } finally { f.detector.dispose(); globalThis.createImageBitmap = old; }
});

test('queued frames are bounded and a stuck worker is terminated instead of accumulating camera tasks', async () => {
  const old = globalThis.createImageBitmap; globalThis.createImageBitmap = async () => ({ close() {} });
  const f = fixture(15);
  try {
    const first = f.detector.detect({}), second = f.detector.detect({});
    const settled = Promise.allSettled([first, second]); await tick();
    await assert.rejects(f.detector.detect({}), /document_detector_busy/);
    assert.ok((await settled).every(row => row.status === 'rejected'));
    assert.equal(f.workers[0].terminated, true);
  } finally { f.detector.dispose(); globalThis.createImageBitmap = old; }
});
