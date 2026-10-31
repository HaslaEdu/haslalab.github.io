import { DOCUMENT_ASSETS, decodeDocumentHeatmap, documentGeometry, refineDocumentEdges } from './document-model.mjs?v=6664c29c0e87';
import { toGray, detectDocumentQuadGray, findSheetMarkersGray, documentOutputSize, warpPixels, enhancePixels, inspectDocumentPixels } from './scanner.js?v=6664c29c0e87';

const CACHE = 'haslalab-document-assets-' + DOCUMENT_ASSETS.version;
let ort, session, initializing, modelFailure = null, modelRetryAt = 0, modelFailures = 0;
const digest = async bytes => [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(v => v.toString(16).padStart(2, '0')).join('');
async function asset(info, signal) {
  const url = new URL(info.path, import.meta.url), request = new Request(url, { credentials: 'omit' });
  let cache; try { cache = await caches.open(CACHE); } catch {}
  let response = await cache?.match(request), bytes;
  if (response) {
    bytes = await response.arrayBuffer();
    if (bytes.byteLength !== info.bytes || await digest(bytes) !== info.sha256) { await cache.delete(request); response = null; }
  }
  if (!response) {
    response = await fetch(request, { cache: 'force-cache', signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(30000)]) : AbortSignal.timeout(30000) });
    if (!response.ok || Number(response.headers.get('Content-Length') || 0) > info.bytes) throw new Error('document_asset_unavailable');
    const reader = response.body.getReader(), parts = []; let count = 0;
    for (;;) { const part = await reader.read(); if (part.done) break; count += part.value.byteLength; if (count > info.bytes) { await reader.cancel(); throw new Error('document_asset_size'); } parts.push(part.value); }
    bytes = new Uint8Array(count); let offset = 0; for (const part of parts) { bytes.set(part, offset); offset += part.byteLength; }
    if (count !== info.bytes || await digest(bytes) !== info.sha256) throw new Error('document_asset_integrity');
    try { await cache?.put(request, new Response(bytes, { headers: { 'Content-Type': 'application/octet-stream', 'Cache-Control': 'public,max-age=31536000,immutable' } })); } catch {}
  }
  return new Uint8Array(bytes);
}
async function initialize(retry = false) {
  if (session) return;
  if (initializing) return initializing;
  if (modelFailure && !retry && Date.now() < modelRetryAt) throw new Error(modelFailure);
  initializing = (async () => {
    self.postMessage({ type: 'progress', stage: 'download' });
    const assetsAbort = new AbortController(); let model, wasm;
    try { [model, wasm] = await Promise.all([asset(DOCUMENT_ASSETS.model, assetsAbort.signal), asset(DOCUMENT_ASSETS.wasm, assetsAbort.signal)]); }
    finally { assetsAbort.abort(); }
    ort = await import(new URL(DOCUMENT_ASSETS.runtime, import.meta.url).href);
    ort.env.wasm.numThreads = 1; ort.env.wasm.proxy = false;
    ort.env.wasm.wasmPaths = { mjs: new URL(DOCUMENT_ASSETS.runtimeModule, import.meta.url).href };
    ort.env.wasm.wasmBinary = wasm;
    self.postMessage({ type: 'progress', stage: 'compile' });
    session = await ort.InferenceSession.create(model, { executionProviders: ['wasm'], graphOptimizationLevel: 'all' });
    modelFailure = null; modelFailures = 0; modelRetryAt = 0;
  })().catch(error => {
    modelFailure = 'document_model_unavailable';
    modelRetryAt = Date.now() + Math.min(60000, 5000 * 2 ** Math.min(4, modelFailures++));
    throw error;
  }).finally(() => { initializing = null; });
  return initializing;
}
const tiny = new OffscreenCanvas(256, 256), tinyContext = tiny.getContext('2d', { willReadFrequently: true });
async function detect(message) {
  const bitmap = message.bitmap, width = bitmap.width, height = bitmap.height;
  const canvas = new OffscreenCanvas(width, height), context = canvas.getContext('2d', { willReadFrequently: true });
  context.drawImage(bitmap, 0, 0); bitmap.close();
  const rgba = context.getImageData(0, 0, width, height), gray = toGray(rgba.data, width, height);
  const printed = findSheetMarkersGray(gray, width, height);
  if (printed?.score >= .85) return { ...printed, paperStatus: 'document', engine: 'printed-markers', scanEligible: true,
    autoCaptureEligible: true, clipped: false };
  let modelReady = true;
  try { await initialize(message.retry === true); } catch { modelReady = false; }
  if (modelReady) {
    tinyContext.drawImage(canvas, 0, 0, 256, 256);
    const data = tinyContext.getImageData(0, 0, 256, 256).data, tensor = new Float32Array(3 * 256 * 256);
    for (let i = 0; i < 256 * 256; i++) { tensor[i] = data[i * 4] / 255; tensor[i + 65536] = data[i * 4 + 1] / 255; tensor[i + 131072] = data[i * 4 + 2] / 255; }
    const started = performance.now(), outputs = await session.run({ [session.inputNames[0]]: new ort.Tensor('float32', tensor, [1, 3, 256, 256]) });
    const output = outputs[session.outputNames[0]], decoded = decodeDocumentHeatmap(output.data, output.dims, width, height);
    const geometry = decoded && documentGeometry(decoded.corners, width, height);
    if (geometry) {
      const refined = refineDocumentEdges(gray, width, height, geometry.corners);
      const verified = refined && refined.edgeSupport >= .52 && refined.weakestEdge >= .28;
      if (verified) return { ...refined, score: Math.min(1, decoded.score), modelConfidence: decoded.confidence,
        corners: refined.corners, method: 'ml', engine: 'docaligner-lcnet', paperStatus: 'document', scanEligible: true,
        autoCaptureEligible: decoded.score >= .5 && refined.edgeSupport >= .72 && refined.weakestEdge >= .5,
        clipped: false, inferenceMs: performance.now() - started };
    }
  }
  const proposal = detectDocumentQuadGray(gray, width, height);
  return { ...proposal, engine: 'cv-fallback', scanEligible: false, autoCaptureEligible: false,
    reason: modelFailure || 'document_corners_uncertain' };
}
async function render(message) {
  const bitmap = message.bitmap, width = bitmap.width, height = bitmap.height;
  const source = new OffscreenCanvas(width, height), context = source.getContext('2d', { willReadFrequently: true });
  context.drawImage(bitmap, 0, 0); bitmap.close();
  const baseline = message.includeBaseline ? source.convertToBlob({ type: 'image/png' }) : null;
  const input = context.getImageData(0, 0, width, height), size = documentOutputSize(message.corners, message.outW, message.pageFormat, message.inset);
  const inset = message.inset, target = inset ? [
    { x: inset.left * size.width, y: inset.top * size.height }, { x: inset.right * size.width, y: inset.top * size.height },
    { x: inset.left * size.width, y: inset.bottom * size.height }, { x: inset.right * size.width, y: inset.bottom * size.height },
  ] : null;
  const output = warpPixels(input.data, width, height, message.corners, size.width, size.height, target);
  const quality = inspectDocumentPixels(output.data, size.width, size.height);
  const data = enhancePixels(output.data, size.width, size.height, message.mode || 'original');
  const canvas = new OffscreenCanvas(size.width, size.height);
  canvas.getContext('2d').putImageData(new ImageData(data, size.width, size.height), 0, 0);
  const blob = await canvas.convertToBlob({ type: message.mode === 'mono' ? 'image/png' : 'image/jpeg', quality: .94 });
  return { blob, quality, width: size.width, height: size.height, ...(baseline ? { baseBlob: await baseline } : {}) };
}
let chain = Promise.resolve();
const inbox = new Map();
self.onmessage = event => {
  const message = event.data;
  if (message.type === 'cancel') { try { inbox.get(message.id)?.bitmap?.close(); } catch {} inbox.delete(message.id); return; }
  if (inbox.size >= 3) { try { message.bitmap?.close(); } catch {} self.postMessage({ type: 'error', id: message.id, code: 'document_detector_busy' }); return; }
  inbox.set(message.id, message);
  chain = chain.then(async () => {
    if (!inbox.has(message.id)) return;
    try {
      if (message.type === 'warm') { await initialize(message.retry === true); self.postMessage({ type: 'ready', id: message.id }); }
      else if (message.type === 'detect') self.postMessage({ type: 'result', id: message.id, result: await detect(message) });
      else if (message.type === 'render') self.postMessage({ type: 'result', id: message.id, result: await render(message) });
    } catch { try { message.bitmap?.close(); } catch {} self.postMessage({ type: 'error', id: message.id, code: 'document_model_unavailable' }); }
    finally { inbox.delete(message.id); }
  });
};
