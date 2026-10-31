/* The scanner's worker: finds the page and renders the scan off the main thread. No model and no network: the page is
   found by printed markers or by findPage in scanner.js (v2), both plain arithmetic on the photo's pixels. */
import { toGray, detectDocumentQuadGray, documentOutputSize, warpPixels, enhancePixels, inspectDocumentPixels } from './scanner.js?v=8e31e6b73e0b';

function detect(message) {
  const bitmap = message.bitmap, width = bitmap.width, height = bitmap.height;
  const canvas = new OffscreenCanvas(width, height), context = canvas.getContext('2d', { willReadFrequently: true });
  context.drawImage(bitmap, 0, 0); bitmap.close();
  const rgba = context.getImageData(0, 0, width, height).data;
  return classify(detectDocumentQuadGray(toGray(rgba, width, height), width, height, rgba));
}
/* what the scan page needs to know: a usable quad (cropped and offered for a check), and whether its edges were measured */
export function classify(found) {
  const usable = !!found.corners && found.method !== 'frame';
  const verified = usable && (found.method === 'marker' || found.verified === true);
  return { ...found, engine: found.method === 'marker' ? 'printed-markers' : 'page-finder-v2', scanEligible: usable, verified,
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
      if (message.type === 'warm') self.postMessage({ type: 'ready', id: message.id });
      else if (message.type === 'detect') self.postMessage({ type: 'result', id: message.id, result: detect(message) });
      else if (message.type === 'render') self.postMessage({ type: 'result', id: message.id, result: await render(message) });
    } catch { try { message.bitmap?.close(); } catch {} self.postMessage({ type: 'error', id: message.id, code: 'document_worker_failed' }); }
    finally { inbox.delete(message.id); }
  });
};
