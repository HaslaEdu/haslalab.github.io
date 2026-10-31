/* DocAligner LCNet heatmap decoding follows the Apache-2.0 model pipeline.
 * The local-window decoder is adapted from quadscan (MIT); see vendor notices. */
export const DOCUMENT_ASSETS = Object.freeze({
  version: 'docaligner-lcnet-ort1201-v1',
  model: { path: '../../vendor/docaligner-lcnet/lcnet100-v1.onnx', bytes: 4767987, sha256: 'f4117b786e3a18470f3865c93f3c2bd69d9b998edd60f385574a5c665e79594e' },
  wasm: { path: '../../vendor/onnxruntime-web-1.20.1/ort-wasm-simd-threaded.wasm', bytes: 11246032, sha256: '207d02be4591c156b0a98f024f3d58005b5b04c92274d759fb390338c63559ea' },
  runtime: '../../vendor/onnxruntime-web-1.20.1/ort.wasm.min.mjs',
  runtimeBytes: 48904, runtimeSha256: 'f53ed4792e758e7232f779d479eb8931b97ff3ab2e3b9a33ee00d1251ffdaad6',
  runtimeModule: '../../vendor/onnxruntime-web-1.20.1/ort-wasm-simd-threaded.mjs',
  runtimeModuleBytes: 24618, runtimeModuleSha256: '745eb7c0ce6f18a6aa521971b2877babc7ffb27eecb58ab3bc6e5ef4692672e8',
});

export function decodeDocumentHeatmap(values, dims, width, height, threshold = .25) {
  const channels = dims.at(-3), rows = dims.at(-2), columns = dims.at(-1);
  if (channels !== 4 || !(rows > 0 && columns > 0) || values.length !== 4 * rows * columns) return null;
  const corners = [], confidence = [];
  for (let c = 0; c < 4; c++) {
    const base = c * rows * columns; let maximum = -Infinity, peak = 0;
    for (let i = 0; i < rows * columns; i++) if (values[base + i] > maximum) { maximum = values[base + i]; peak = i; }
    if (!Number.isFinite(maximum) || maximum < threshold) return null;
    const px = peak % columns, py = Math.floor(peak / columns);
    let weight = 0, x = 0, y = 0;
    for (let j = Math.max(0, py - 4); j <= Math.min(rows - 1, py + 4); j++) for (let i = Math.max(0, px - 4); i <= Math.min(columns - 1, px + 4); i++) {
      const v = values[base + j * columns + i];
      if (v >= maximum * .3) { weight += v; x += i * v; y += j * v; }
    }
    corners.push({ x: (weight ? x / weight + .5 : px + .5) * width / columns,
      y: (weight ? y / weight + .5 : py + .5) * height / rows });
    confidence.push(maximum);
  }
  return { corners, confidence, score: Math.min(...confidence) };
}

const cross = (a, b, c) => (b.x - a.x) * (c.y - b.y) - (b.y - a.y) * (c.x - b.x);
export function documentGeometry(corners, width, height) {
  if (!Array.isArray(corners) || corners.length !== 4 || corners.some(p => !p || !Number.isFinite(p.x + p.y))) return null;
  const cx = corners.reduce((s, p) => s + p.x, 0) / 4, cy = corners.reduce((s, p) => s + p.y, 0) / 4;
  const poly = [...corners].sort((a, b) => Math.atan2(a.y - cy, a.x - cx) - Math.atan2(b.y - cy, b.x - cx));
  let start = 0; for (let i = 1; i < 4; i++) if (poly[i].x + poly[i].y < poly[start].x + poly[start].y) start = i;
  const ordered = [...poly.slice(start), ...poly.slice(0, start)];
  const signs = ordered.map((p, i) => cross(p, ordered[(i + 1) % 4], ordered[(i + 2) % 4]));
  if (signs.some(v => Math.abs(v) < 1) || signs.some(v => Math.sign(v) !== Math.sign(signs[0]))) return null;
  const margin = Math.max(2, Math.min(width, height) * .006);
  if (ordered.some(p => p.x < margin || p.y < margin || p.x > width - margin || p.y > height - margin)) return null;
  const lengths = ordered.map((p, i) => Math.hypot(p.x - ordered[(i + 1) % 4].x, p.y - ordered[(i + 1) % 4].y));
  let area = 0; for (let i = 0; i < 4; i++) area += ordered[i].x * ordered[(i + 1) % 4].y - ordered[(i + 1) % 4].x * ordered[i].y;
  const coverage = Math.abs(area) / (2 * width * height);
  if (coverage < .075 || coverage > .95 || Math.min(...lengths) < Math.min(width, height) * .12 || Math.max(...lengths) / Math.min(...lengths) > 8) return null;
  return { corners: [ordered[0], ordered[1], ordered[3], ordered[2]], coverage, lengths };
}

const pixel = (gray, width, height, x, y) => {
  x = Math.max(0, Math.min(width - 1, x)); y = Math.max(0, Math.min(height - 1, y));
  const ix = Math.floor(x), iy = Math.floor(y), fx = x - ix, fy = y - iy;
  const right = Math.min(ix + 1, width - 1), down = Math.min(iy + 1, height - 1);
  return (gray[iy * width + ix] * (1 - fx) + gray[iy * width + right] * fx) * (1 - fy) +
    (gray[down * width + ix] * (1 - fx) + gray[down * width + right] * fx) * fy;
};
const median = values => [...values].sort((a, b) => a - b)[values.length >> 1];

/** Refine the learned coarse corners against native image pixels, not the
 * 256px network input. A weak/ambiguous boundary retains the model proposal. */
export function refineDocumentEdges(gray, width, height, corners) {
  const shape = documentGeometry(corners, width, height);
  if (!shape) return null;
  const q = shape.corners, poly = [q[0], q[1], q[3], q[2]], lines = [], supports = [];
  const cx = q.reduce((s, p) => s + p.x, 0) / 4, cy = q.reduce((s, p) => s + p.y, 0) / 4;
  for (let side = 0; side < 4; side++) {
    const a = poly[side], b = poly[(side + 1) % 4], length = shape.lengths[side];
    let nx = -(b.y - a.y) / length, ny = (b.x - a.x) / length;
    if ((cx - a.x) * nx + (cy - a.y) * ny < 0) { nx = -nx; ny = -ny; }
    const search = Math.min(28, Math.max(5, Math.max(width, height) / 80)), shifts = [];
    for (let sample = 0; sample < 48; sample++) {
      const t = .06 + .88 * (sample + .5) / 48, x = a.x + (b.x - a.x) * t, y = a.y + (b.y - a.y) * t;
      let best = 0, shift = 0;
      for (let offset = -search; offset <= search; offset += 1) {
        const px = x + nx * offset, py = y + ny * offset;
        const near = Math.abs(pixel(gray, width, height, px + nx * 2, py + ny * 2) - pixel(gray, width, height, px - nx * 2, py - ny * 2));
        const far = Math.abs(pixel(gray, width, height, px + nx * 7, py + ny * 7) - pixel(gray, width, height, px - nx * 7, py - ny * 7));
        if (near < 5 || far < 4 || near < far * .35) continue;
        const value = near - Math.abs(offset) * .18;
        if (value > best) { best = value; shift = offset; }
      }
      if (best >= 5) shifts.push(shift);
    }
    const support = shifts.length / 48;
    supports.push(support);
    lines.push({ nx, ny, r: nx * a.x + ny * a.y + (support >= .6 ? median(shifts) : 0) });
  }
  const fitted = lines.map((b, i) => {
    const a = lines[(i + 3) % 4], det = a.nx * b.ny - a.ny * b.nx;
    return Math.abs(det) < .08 ? null : { x: (a.r * b.ny - a.ny * b.r) / det, y: (a.nx * b.r - a.r * b.nx) / det };
  });
  const refined = documentGeometry(fitted, width, height);
  return { corners: refined?.corners || q, edgeSupport: supports.reduce((a, b) => a + b, 0) / 4, weakestEdge: Math.min(...supports) };
}
