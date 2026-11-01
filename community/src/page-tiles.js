// Zoomed strips of a photographed page for the page reader (image tiling): a vision model that scales a whole page
// down to a few thousand pixels reads small handwriting better from overlapping strips of it beside the full page.
// jpeg-js (BSD-3-Clause, pure JavaScript) decodes and encodes; a page that is not a JPEG, or is too large, gets none.
import jpeg from 'jpeg-js';

const MAX_PIXELS = 24e6;

/* jpeg-js's encoder ends with Buffer.from(bytes), and a Worker has no Buffer: a byte-array stand-in exists only for the
   (synchronous) call and is removed at once, so no other code ever sees a Buffer global */
function encode(image, quality) {
  if (typeof globalThis.Buffer !== 'undefined') return new Uint8Array(jpeg.encode(image, quality).data);
  globalThis.Buffer = { from: bytes => Uint8Array.from(bytes) };
  try { return jpeg.encode(image, quality).data; }
  finally { delete globalThis.Buffer; }
}

/** n horizontal strips (top to bottom) overlapping by `overlap` of the page height, as JPEG bytes */
export function pageStrips(bytes, n = 2, overlap = 0.1, quality = 85) {
  if (!(bytes instanceof Uint8Array) || bytes.length < 4 || bytes[0] !== 0xff || bytes[1] !== 0xd8 || !(n >= 2 && n <= 4)) return [];
  let image;
  try { image = jpeg.decode(bytes, { useTArray: true, formatAsRGBA: true, maxResolutionInMP: MAX_PIXELS / 1e6, maxMemoryUsageInMB: 160 }); }
  catch { return []; }
  const { width, height, data } = image;
  if (!(width > 0 && height > 0) || width * height > MAX_PIXELS) return [];
  const strips = [];
  for (let i = 0; i < n; i++) {
    const y0 = Math.max(0, Math.round((i / n - overlap / 2) * height)), y1 = Math.min(height, Math.round(((i + 1) / n + overlap / 2) * height));
    const rows = data.subarray(y0 * width * 4, y1 * width * 4);
    strips.push(encode({ width, height: y1 - y0, data: rows }, quality));
  }
  return strips;
}
