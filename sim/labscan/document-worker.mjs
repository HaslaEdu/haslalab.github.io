/* The scanner's worker: finds the page and renders the scan off the main thread. The page is found by printed
   markers, by findPage in scanner.js (v2, plain arithmetic on the photo's pixels) and by the learned corner model
   DocCornerNet (scanic-ml, MIT, served from this site: vendor/scanic-ml-0.2.0), whose quad is fitted to the measured
   edges like any other before chooseDocument picks one. No photo leaves the device. */
import { toGray, detectDocumentQuadGray, findPageQuadGray, chooseDocument, documentOutputSize, warpPixels, enhancePixels, inspectDocumentPixels } from './scanner.js?v=08420579ed34';

const ML_ASSETS = new URL('../../vendor/scanic-ml-0.2.0/', import.meta.url).href;
let ml = null, mlFailedAt = 0;
const mlModule = () => ml || (ml = import(new URL('../../vendor/scanic-1.7.1/scanic-mlDetector.js', import.meta.url).href).catch(error => { ml = null; throw error; }));
const ML_OPTIONS = { assetBaseUrl: ML_ASSETS, numThreads: 1, minScore: 0 };
/* the model's corners for this canvas, or null while it is unavailable (retried a minute after a failure) */
async function learnedCorners(canvas) {
  if (Date.now() - mlFailedAt < 60000) return null;
  try {
    const { detectDocumentMl } = await mlModule(), r = await detectDocumentMl(canvas, ML_OPTIONS), c = r?.corners;
    const points = Array.isArray(c) ? c : c && ['topLeft', 'topRight', 'bottomRight', 'bottomLeft'].map(key => c[key]);
    if (!points || points.length !== 4 || points.some(p => !p || !Number.isFinite(p.x) || !Number.isFinite(p.y))) return null;
    return { points: [points[0], points[1], points[3], points[2]], score: Number(r.score ?? r.confidence) || 0 };
  } catch { mlFailedAt = Date.now(); return null; }
}
async function warm() {
  try { const { initializeMl } = await mlModule(); await initializeMl(ML_OPTIONS); } catch { mlFailedAt = Date.now(); }
}

async function detect(message) {
  const bitmap = message.bitmap, width = bitmap.width, height = bitmap.height;
  const canvas = new OffscreenCanvas(width, height), context = canvas.getContext('2d', { willReadFrequently: true });
  context.drawImage(bitmap, 0, 0); bitmap.close();
  const rgba = context.getImageData(0, 0, width, height).data, gray = toGray(rgba, width, height);
  const page = detectDocumentQuadGray(gray, width, height, rgba);
  if (page.method === 'marker' && page.score >= .75) return classify(page);
  const model = await learnedCorners(canvas);
  const learned = model && findPageQuadGray(gray, width, height, rgba, model.points);
  return classify(chooseDocument(page, learned, model?.score ?? 0));
}
/* what the scan page needs to know: a usable quad (cropped and offered for a check), and whether its edges were measured */
export function classify(found) {
  const usable = !!found.corners && found.method !== 'frame';
  const verified = usable && (found.method === 'marker' || found.verified === true);
  return { ...found, engine: found.method === 'marker' ? 'printed-markers' : found.engine || 'page-finder-v2', scanEligible: usable, verified,
    paperStatus: usable ? (found.paperStatus && found.paperStatus !== 'not_found' ? found.paperStatus : 'document') : 'not_found',
    autoCaptureEligible: verified && found.autoCaptureEligible === true, ...(verified || !usable ? {} : { reason: 'document_edges_weak' }) };
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
  const output = warpPixels(input.data, width, height, message.corners, size.width, size.height, target, { sharpen: message.mode === 'clean' });
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
      if (message.type === 'warm') { await warm(); self.postMessage({ type: 'ready', id: message.id }); }
      else if (message.type === 'detect') self.postMessage({ type: 'result', id: message.id, result: await detect(message) });
      else if (message.type === 'render') self.postMessage({ type: 'result', id: message.id, result: await render(message) });
    } catch { try { message.bitmap?.close(); } catch {} self.postMessage({ type: 'error', id: message.id, code: 'document_worker_failed' }); }
    finally { inbox.delete(message.id); }
  });
};
