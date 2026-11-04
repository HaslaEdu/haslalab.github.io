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

/** a region of a photographed page, as JPEG bytes: box [ymin,xmin,ymax,xmax] in 0..1000 of the image (Gemini's
    box_2d), widened by padY / padX (in 0..1000 units) on each side and clipped to the page; null when it cannot be cut */
export function cropJpeg(bytes, box, padY = 20, padX = 40, quality = 90) {
  if (!(bytes instanceof Uint8Array) || bytes.length < 4 || bytes[0] !== 0xff || bytes[1] !== 0xd8) return null;
  if (!Array.isArray(box) || box.length !== 4 || !box.every(Number.isFinite)) return null;
  const [y0, x0, y1, x1] = box, top = Math.min(y0, y1) - padY, bottom = Math.max(y0, y1) + padY, left = Math.min(x0, x1) - padX, right = Math.max(x0, x1) + padX;
  let image;
  try { image = jpeg.decode(bytes, { useTArray: true, formatAsRGBA: true, maxResolutionInMP: MAX_PIXELS / 1e6, maxMemoryUsageInMB: 160 }); }
  catch { return null; }
  const { width, height, data } = image;
  if (!(width > 0 && height > 0) || width * height > MAX_PIXELS) return null;
  const r0 = Math.max(0, Math.floor(top / 1000 * height)), r1 = Math.min(height, Math.ceil(bottom / 1000 * height));
  const c0 = Math.max(0, Math.floor(left / 1000 * width)), c1 = Math.min(width, Math.ceil(right / 1000 * width));
  if (r1 - r0 < 8 || c1 - c0 < 8) return null;
  const w = c1 - c0, out = new Uint8Array(w * (r1 - r0) * 4);
  for (let r = r0; r < r1; r++) out.set(data.subarray((r * width + c0) * 4, (r * width + c1) * 4), (r - r0) * w * 4);
  return encode({ width: w, height: r1 - r0, data: out }, quality);
}

/** the same JPEG page encoded again at another quality (the admin bench: does a smaller upload read as well?); null for
    anything that is not a JPEG it can decode */
export function reencodeJpeg(bytes, quality) {
  if (!(bytes instanceof Uint8Array) || bytes.length < 4 || bytes[0] !== 0xff || bytes[1] !== 0xd8 || !(quality >= 30 && quality <= 100)) return null;
  let image;
  try { image = jpeg.decode(bytes, { useTArray: true, formatAsRGBA: true, maxResolutionInMP: MAX_PIXELS / 1e6, maxMemoryUsageInMB: 160 }); }
  catch { return null; }
  return image.width * image.height > MAX_PIXELS ? null : encode(image, quality);
}

/** a photo within `allowance` base64 bytes: as it is, or a JPEG encoded again at a lower quality; null if none fits
    (a grading request's image budget is shared by its pages: a long experiment's last pages were left out) */
export function fitPhoto(img, mime, allowance) {
  const b = img instanceof Uint8Array ? img : new Uint8Array(img);
  if (b.byteLength * 4 / 3 <= allowance) return b;
  if (mime !== 'image/jpeg') { console.warn(`[page-tiles] ${mime || 'non-JPEG'} page of ${b.byteLength} bytes is over its ${Math.round(allowance)}-byte share and cannot be made smaller here (no PNG/WebP decoder)`); return null; }
  for (const q of [60, 45, 32]) { const small = reencodeJpeg(b, q); if (small && small.byteLength * 4 / 3 <= allowance) return small; }
  return null;
}

/* The browser sends every answer page as JPEG (encodeUpload in sim/labscan/scanner.js). A PNG or WebP that still arrives
   (an old cached page, a browser that could not decode the file) is kept with its own MIME and graded from the whole
   photo, but it gets none of the above: no strips, no zoom crops, no size fitting. Said once per stored page, so a drop
   in reading accuracy can be traced to it. */
export function warnNotJpeg(where, mime, bytes) {
  if (mime === 'image/jpeg') return false;
  console.warn(`[${where}] stored ${mime || 'an unknown'} page of ${bytes} bytes as it is: no strips, zoom crops or size fitting (the Worker decodes JPEG only)`);
  return true;
}
