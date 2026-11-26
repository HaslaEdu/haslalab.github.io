/* Ink for the figure editor (#/workshop/draw): a pen or a finger on a tablet draws, and what it draws is cleaned up the
   way GoodNotes and Notability do it — hold the pen still at the end of a stroke (or lift it with "자동 보정 / Auto-shape"
   on) and a wobbly line becomes a straight one at 0/15/30/45/60/90°, a loop a circle or an ellipse, four corners a
   rectangle, a right triangle on a horizontal base an incline; physics glyphs too: a zigzag is a resistor or a spring, a
   coil a spring or an inductor, a wave a sine wave, two parallel bars a cell or a capacitor, three shrinking bars a ground,
   short dashes in a row a dashed line, a line with a head an arrow. Handwritten maths goes to the server as a small PNG
   (rasteriseStrokes → POST /api/workshop/ai/math, community/src/workshop-ai.js) and comes back as checked LaTeX.

   Everything here is geometry (fitting, residuals, corners by ShortStraw, closedness, turning, oscillation models):
   deterministic, offline, well under 10 ms a stroke. No DOM in the core: the browser and Node import the same file
   (tests/test-draw-ink.cjs). Coordinates are the editor's world (metres, y up); `unit` is world units per screen pixel
   (the editor's dview().w / W), so tolerances are in pixels the hand moved, whatever the zoom.

   Exports
     stroke model     normStroke(raw) → {points: [{x,y,t,pressure}], pointerType}; pathLength, bounds, resample
     smoothing        oneEuro(points, {unit}) · catmullRom(points, {samples, closed}) · smoothFreehand(points, {unit})
                      pressureWidths(points, {base, unit}) · strokeOutline(points, widths) · strokeLw(points)
     recognition      recognizeStroke(stroke, opts) → {type, params, confidence, alternatives: [{type, params, confidence}]}
                      recognizeGroup(items, opts) → a result made of the last k strokes ({…, strokes: k}) or null
                      types: line arrow dashed polyline polygon triangle incline rect square circle ellipse arc curve
                      zigzag (resistor | spring) coil (spring | inductor) wave cell capacitor ground freehand
     to the scene     toSceneObjects(result, {grid, existing, look, unit, idFor}) → objects of draw-scene.mjs types
                      candidatesFromScene(scene) → points a line can snap to
     the controller   createInkController({onShape, onFreehand, onMathRegion, onPreview, getCandidates, toWorld, options})
     maths            rasteriseStrokes(strokes, {maxSize, maxBytes}) → Promise<{dataUrl, width, height, bytes}>
                      strokesInLasso(strokes, lasso) · polyToStroke(obj) · mathRequestBody(dataUrl, hint) */
import {defaults, bodyPose, isBody, simplifyPath, ANCHOR_TYPES, BODY_TYPES} from './draw-scene.mjs?v=6e567e38776d';

export const INK_VERSION = 1;
export const MATH_PATH = '/api/workshop/ai/math';
export const INK_DEFAULTS = Object.freeze({
  autoShape: true, holdToSnap: true, fingerDraw: false, mouse: true,
  holdMs: 500, holdMovePx: 5, minConfidence: 0.6, snapPx: 14, angleTol: 6, axisTol: 8, snapStep: 15,
  groupMs: 1600, groupPx: 160, mathIdleMs: 0, palmArea: 2200, unit: 1
});
const PI = Math.PI, DEG = 180 / PI, hyp = Math.hypot;
const clamp = (v, a, b) => v < a ? a : v > b ? b : v;
const r4 = v => Math.round(v * 1e4) / 1e4;
const d2 = (a, b) => hyp(a.x - b.x, a.y - b.y);
const lerp = (a, b, t) => ({x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t});
const angOf = (a, b) => Math.atan2(b.y - a.y, b.x - a.x);
const normDeg = a => { a %= 360; if (a <= -180) a += 360; if (a > 180) a -= 360; return a + 0; };
/* the smaller angle between two directions, as undirected lines (0–90°) */
const lineDiff = (a, b) => { let d = Math.abs(normDeg((a - b) * DEG)) % 180; return d > 90 ? 180 - d : d; };
const dirDiff = (a, b) => Math.abs(normDeg((a - b) * DEG));
const now0 = () => (typeof performance !== 'undefined' && performance.now ? performance.now() : Date.now());

/* ── the stroke model ── */
/** a stroke from points as objects {x,y,t?,pressure?} or arrays [x,y,t?,p?]: non-finite points and repeats dropped */
export function normStroke(raw) {
  const src = Array.isArray(raw) ? raw : raw?.points || [];
  const out = [];
  for (const q of src) {
    const p = Array.isArray(q) ? {x: q[0], y: q[1], t: q[2], pressure: q[3]} : q;
    if (!p || !Number.isFinite(p.x) || !Number.isFinite(p.y)) continue;
    const t = Number.isFinite(p.t) ? p.t : (out.length ? out[out.length - 1].t + 8 : 0);
    const pr = Number.isFinite(p.pressure) && p.pressure > 0 ? clamp(p.pressure, 0, 1) : 0.5;
    const last = out[out.length - 1];
    if (last && last.x === p.x && last.y === p.y) continue;
    out.push({x: p.x, y: p.y, t, pressure: pr});
  }
  return {points: out, pointerType: raw?.pointerType || 'pen', id: raw?.id};
}
export const pathLength = pts => { let s = 0; for (let i = 1; i < pts.length; i++) s += d2(pts[i - 1], pts[i]); return s; };
export function bounds(pts) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const p of pts) { if (p.x < x0) x0 = p.x; if (p.x > x1) x1 = p.x; if (p.y < y0) y0 = p.y; if (p.y > y1) y1 = p.y; }
  const w = x1 - x0, h = y1 - y0;
  return {x0, y0, x1, y1, w, h, diag: hyp(w, h), cx: (x0 + x1) / 2, cy: (y0 + y1) / 2};
}
/** points every `step` along the path (the first and the last kept) */
export function resample(pts, step) {
  if (pts.length < 2 || !(step > 0)) return pts.map(p => ({x: p.x, y: p.y}));
  const out = [{x: pts[0].x, y: pts[0].y}];
  let acc = 0, prev = pts[0];
  for (let i = 1; i < pts.length; i++) {
    let cur = pts[i], d = d2(prev, cur);
    while (acc + d >= step && d > 0) {
      const t = (step - acc) / d, q = lerp(prev, cur, t);
      out.push(q); prev = q; d = d2(prev, cur); acc = 0;
      if (out.length > 4000) break;
    }
    acc += d; prev = cur;
  }
  const last = pts[pts.length - 1];
  if (d2(out[out.length - 1], last) > step * 0.25) out.push({x: last.x, y: last.y}); else out[out.length - 1] = {x: last.x, y: last.y};
  return out;
}
const smooth121 = (R, closed, passes = 2) => {
  let a = R;
  for (let k = 0; k < passes; k++) {
    const n = a.length, b = a.map(p => ({...p}));
    for (let i = 0; i < n; i++) {
      if (!closed && (i === 0 || i === n - 1)) continue;
      const p = a[(i - 1 + n) % n], q = a[(i + 1) % n];
      b[i] = {x: (p.x + 2 * a[i].x + q.x) / 4, y: (p.y + 2 * a[i].y + q.y) / 4};
    }
    a = b;
  }
  return a;
};

/* ── smoothing ── */
/** the one-euro filter (Casiez et al. 2012): little smoothing when the pen is fast, much when it is slow; speeds in px/s */
export function oneEuro(pts, {minCutoff = 1.2, beta = 0.008, dCutoff = 1, unit = 1} = {}) {
  if (pts.length < 3) return pts.map(p => ({...p}));
  const alpha = (cut, dt) => 1 / (1 + 1 / (2 * PI * cut * dt));
  let fx = pts[0].x, fy = pts[0].y, dx = 0, dy = 0;
  const out = [{...pts[0]}];
  for (let i = 1; i < pts.length; i++) {
    const p = pts[i], dt = clamp(((p.t ?? 0) - (pts[i - 1].t ?? 0)) / 1000, 1 / 480, 0.1) || 1 / 120;
    const ad = alpha(dCutoff, dt);
    dx += ad * ((p.x - fx) / dt / unit - dx); dy += ad * ((p.y - fy) / dt / unit - dy);
    const a = alpha(minCutoff + beta * hyp(dx, dy), dt);
    fx += a * (p.x - fx); fy += a * (p.y - fy);
    out.push({...p, x: fx, y: fy});
  }
  /* the filter lags: the end goes back to where the pen was lifted */
  out[out.length - 1] = {...pts[pts.length - 1]};
  return out;
}
/** a centripetal Catmull–Rom spline through the points, `samples` points a span */
export function catmullRom(pts, {samples = 6, closed = false} = {}) {
  const n = pts.length;
  if (n < 3) return pts.map(p => ({x: p.x, y: p.y}));
  const P = i => closed ? pts[(i + n) % n] : pts[clamp(i, 0, n - 1)], out = [];
  const spans = closed ? n : n - 1;
  for (let i = 0; i < spans; i++) {
    const p0 = P(i - 1), p1 = P(i), p2 = P(i + 1), p3 = P(i + 2);
    const tj = (a, b) => Math.sqrt(Math.max(d2(a, b), 1e-12));
    const t1 = tj(p0, p1), t2 = t1 + tj(p1, p2), t3 = t2 + tj(p2, p3);
    for (let s = 0; s < samples; s++) {
      const t = t1 + (t2 - t1) * s / samples;
      const L = (a, b, ta, tb) => { const k = (t - ta) / ((tb - ta) || 1e-9); return {x: a.x + (b.x - a.x) * k, y: a.y + (b.y - a.y) * k}; };
      const A1 = L(p0, p1, 0, t1), A2 = L(p1, p2, t1, t2), A3 = L(p2, p3, t2, t3);
      const B1 = L(A1, A2, 0, t2), B2 = L(A2, A3, t1, t3);
      out.push(L(B1, B2, t1, t2));
    }
  }
  if (!closed) out.push({x: pts[n - 1].x, y: pts[n - 1].y});
  return out;
}
/** a freehand stroke as the points of a smooth poly (draw it with smooth: true): filtered, then simplified */
export function smoothFreehand(pts, {unit = 1, max = 400} = {}) {
  if (pts.length < 3) return pts.map(p => ({x: p.x, y: p.y}));
  const f = oneEuro(pts, {unit});
  return simplifyPath(f, 0.8 * unit, max).map(p => ({x: p.x, y: p.y}));
}
/* the pressure the stroke had, or (a mouse, a pen without pressure) one made from its speed: fast is thin */
function pressures(pts, unit) {
  const flat = pts.every(p => Math.abs(p.pressure - pts[0].pressure) < 1e-6);
  if (!flat) return pts.map(p => p.pressure);
  let v = 0;
  return pts.map((p, i) => {
    if (i) { const dt = Math.max(1, (p.t - pts[i - 1].t)); v += 0.3 * (d2(p, pts[i - 1]) / unit / dt * 1000 - v); }
    return clamp(0.75 - v / 4000, 0.25, 0.75);
  });
}
/** a width at each point (world units), from the pressure: base at 0.5, thinner and thicker either side, tapered ends */
export function pressureWidths(pts, {base = 2, min = 0.35, max = 1.7, unit = 1, taper = 4} = {}) {
  const pr = pressures(pts, unit), n = pts.length;
  let ema = pr[0] ?? 0.5;
  return pr.map((p, i) => {
    ema += 0.4 * (p - ema);
    const k = min + (max - min) * ema, end = Math.min(1, (Math.min(i, n - 1 - i) + 1) / taper);
    return base * unit * k * (0.55 + 0.45 * end);
  });
}
/** the outline of a stroke of varying width, as one closed polygon (fill it) */
export function strokeOutline(pts, widths) {
  const n = pts.length; if (n < 2) return [];
  const left = [], right = [];
  for (let i = 0; i < n; i++) {
    const a = pts[Math.max(0, i - 1)], b = pts[Math.min(n - 1, i + 1)], L = d2(a, b) || 1, w = (widths[i] ?? widths[0]) / 2;
    const nx = -(b.y - a.y) / L, ny = (b.x - a.x) / L;
    left.push({x: pts[i].x + nx * w, y: pts[i].y + ny * w}); right.push({x: pts[i].x - nx * w, y: pts[i].y - ny * w});
  }
  return [...left, ...right.reverse()];
}
/** the line weight (draw-scene.mjs COMMON_FIELDS.lw, 0.2–5) a stroke's mean pressure gives */
export function strokeLw(pts) {
  if (!pts.length) return 1;
  const flat = pts.every(p => Math.abs(p.pressure - pts[0].pressure) < 1e-6);
  if (flat) return 1;
  const m = pts.reduce((s, p) => s + p.pressure, 0) / pts.length;
  return r4(clamp(0.5 + 1.4 * m, 0.4, 2.5));
}

/* ── fitting ── */
/* the total-least-squares line: centroid c, unit direction d, and the largest and the rms distance from it */
function fitLine(R) {
  const n = R.length; let cx = 0, cy = 0;
  for (const p of R) { cx += p.x; cy += p.y; } cx /= n; cy /= n;
  let sxx = 0, syy = 0, sxy = 0;
  for (const p of R) { const dx = p.x - cx, dy = p.y - cy; sxx += dx * dx; syy += dy * dy; sxy += dx * dy; }
  const th = 0.5 * Math.atan2(2 * sxy, sxx - syy), d = {x: Math.cos(th), y: Math.sin(th)};
  let max = 0, ss = 0;
  for (const p of R) { const e = Math.abs(-(p.x - cx) * d.y + (p.y - cy) * d.x); if (e > max) max = e; ss += e * e; }
  return {c: {x: cx, y: cy}, d, max, rms: Math.sqrt(ss / n)};
}
const project = (L, p) => { const t = (p.x - L.c.x) * L.d.x + (p.y - L.c.y) * L.d.y; return {x: L.c.x + L.d.x * t, y: L.c.y + L.d.y * t, t}; };
function intersect(L1, L2) {
  const det = L1.d.x * L2.d.y - L1.d.y * L2.d.x;
  if (Math.abs(det) < 1e-9) return null;
  const t = ((L2.c.x - L1.c.x) * L2.d.y - (L2.c.y - L1.c.y) * L2.d.x) / det;
  return {x: L1.c.x + L1.d.x * t, y: L1.c.y + L1.d.y * t};
}
/* a circle through points by algebraic least squares (Kåsa): centre and radius, the rms radial error over r */
function fitCircle(R) {
  let sx = 0, sy = 0, sxx = 0, syy = 0, sxy = 0, sz = 0, sxz = 0, syz = 0; const n = R.length;
  const mx = R.reduce((s, p) => s + p.x, 0) / n, my = R.reduce((s, p) => s + p.y, 0) / n;
  for (const p of R) { const x = p.x - mx, y = p.y - my, z = x * x + y * y; sx += x; sy += y; sxx += x * x; syy += y * y; sxy += x * y; sz += z; sxz += x * z; syz += y * z; }
  /* [sxx sxy sx; sxy syy sy; sx sy n] [D E F] = -[sxz syz sz] */
  const M = [[sxx, sxy, sx, -sxz], [sxy, syy, sy, -syz], [sx, sy, n, -sz]];
  for (let i = 0; i < 3; i++) {
    let piv = i; for (let k = i + 1; k < 3; k++) if (Math.abs(M[k][i]) > Math.abs(M[piv][i])) piv = k;
    [M[i], M[piv]] = [M[piv], M[i]];
    if (Math.abs(M[i][i]) < 1e-14) return null;
    for (let k = 0; k < 3; k++) if (k !== i) { const f = M[k][i] / M[i][i]; for (let j = i; j < 4; j++) M[k][j] -= f * M[i][j]; }
  }
  const D = M[0][3] / M[0][0], E = M[1][3] / M[1][1], F = M[2][3] / M[2][2];
  const cx = -D / 2, cy = -E / 2, r2 = cx * cx + cy * cy - F;
  if (!(r2 > 0)) return null;
  const r = Math.sqrt(r2), c = {x: cx + mx, y: cy + my};
  let ss = 0; for (const p of R) { const e = d2(p, c) - r; ss += e * e; }
  return {c, r, err: Math.sqrt(ss / n) / r};
}
/* an ellipse about the centroid along the principal axes: u²/a² + v²/b² = 1 by least squares; the mean radial error */
function fitEllipse(R) {
  const n = R.length; let cx = 0, cy = 0;
  for (const p of R) { cx += p.x; cy += p.y; } cx /= n; cy /= n;
  let sxx = 0, syy = 0, sxy = 0;
  for (const p of R) { const dx = p.x - cx, dy = p.y - cy; sxx += dx * dx; syy += dy * dy; sxy += dx * dy; }
  const th = 0.5 * Math.atan2(2 * sxy, sxx - syy), c = Math.cos(th), s = Math.sin(th);
  let s40 = 0, s04 = 0, s22 = 0, s20 = 0, s02 = 0;
  const uv = R.map(p => { const dx = p.x - cx, dy = p.y - cy; return [dx * c + dy * s, -dx * s + dy * c]; });
  for (const [u, v] of uv) { const u2 = u * u, v2 = v * v; s40 += u2 * u2; s04 += v2 * v2; s22 += u2 * v2; s20 += u2; s02 += v2; }
  const det = s40 * s04 - s22 * s22; if (Math.abs(det) < 1e-18) return null;
  const A = (s20 * s04 - s02 * s22) / det, B = (s02 * s40 - s20 * s22) / det;
  if (!(A > 0 && B > 0)) return null;
  let e = 0; for (const [u, v] of uv) e += Math.abs(Math.sqrt(A * u * u + B * v * v) - 1);
  return {c: {x: cx, y: cy}, a: 1 / Math.sqrt(A), b: 1 / Math.sqrt(B), th, err: e / n};
}
/* a cubic Bézier with the stroke's ends, its two inner control points by least squares (chord-length parameters) */
function fitBezier(R) {
  const n = R.length, P0 = R[0], P3 = R[n - 1];
  const ts = [0]; for (let i = 1; i < n; i++) ts.push(ts[i - 1] + d2(R[i - 1], R[i]));
  const T = ts[n - 1] || 1;
  let c11 = 0, c12 = 0, c22 = 0, x1 = 0, y1 = 0, x2 = 0, y2 = 0;
  for (let i = 0; i < n; i++) {
    const t = ts[i] / T, b0 = (1 - t) ** 3, b1 = 3 * t * (1 - t) ** 2, b2 = 3 * t * t * (1 - t), b3 = t ** 3;
    const rx = R[i].x - b0 * P0.x - b3 * P3.x, ry = R[i].y - b0 * P0.y - b3 * P3.y;
    c11 += b1 * b1; c12 += b1 * b2; c22 += b2 * b2; x1 += b1 * rx; y1 += b1 * ry; x2 += b2 * rx; y2 += b2 * ry;
  }
  const det = c11 * c22 - c12 * c12; if (Math.abs(det) < 1e-12) return null;
  const P1 = {x: (x1 * c22 - x2 * c12) / det, y: (y1 * c22 - y2 * c12) / det}, P2 = {x: (x2 * c11 - x1 * c12) / det, y: (y2 * c11 - y1 * c12) / det};
  let max = 0;
  for (let i = 0; i < n; i++) {
    const t = ts[i] / T, b0 = (1 - t) ** 3, b1 = 3 * t * (1 - t) ** 2, b2 = 3 * t * t * (1 - t), b3 = t ** 3;
    const q = {x: b0 * P0.x + b1 * P1.x + b2 * P2.x + b3 * P3.x, y: b0 * P0.y + b1 * P1.y + b2 * P2.y + b3 * P3.y};
    max = Math.max(max, d2(q, R[i]));
  }
  return {p0: {x: P0.x, y: P0.y}, p1: P1, p2: P2, p3: {x: P3.x, y: P3.y}, max};
}

/* ── corners (ShortStraw, Wolin et al. 2008), with a turning-angle check so a curve has none ── */
function corners(R, closed) {
  const n = R.length, W = 3;
  if (n < 2 * W + 3) return closed ? [] : [0, n - 1];
  const at = i => closed ? R[(i + n) % n] : R[clamp(i, 0, n - 1)];
  const straw = new Array(n).fill(Infinity);
  for (let i = closed ? 0 : W; i < (closed ? n : n - W); i++) straw[i] = d2(at(i - W), at(i + W));
  const vals = straw.filter(Number.isFinite).sort((a, b) => a - b), med = vals[vals.length >> 1], thr = med * 0.95;
  const turn = i => { const a = at(i - W), b = at(i), c = at(i + W); return dirDiff(angOf(a, b), angOf(b, c)); };
  let cand = [];
  for (let i = 0; i < n; i++) {
    if (!(straw[i] < thr)) continue;
    const s = straw[i], prev = straw[closed ? (i - 1 + n) % n : i - 1] ?? Infinity, next = straw[closed ? (i + 1) % n : i + 1] ?? Infinity;
    if (s <= prev && s < next && turn(i) > 38) cand.push(i);
  }
  /* corners that are one corner */
  const merged = [];
  for (const i of cand) { const last = merged[merged.length - 1]; if (last != null && i - last <= W) { if (straw[i] < straw[last]) merged[merged.length - 1] = i; } else merged.push(i); }
  if (closed && merged.length > 1 && merged[0] + n - merged[merged.length - 1] <= W) { if (straw[merged[0]] < straw[merged[merged.length - 1]]) merged.pop(); else merged.shift(); }
  let cs = closed ? merged : [0, ...merged.filter(i => i > W && i < n - 1 - W), n - 1];
  /* a corner between two segments that run on is not one */
  for (let changed = true; changed && cs.length > (closed ? 3 : 2);) {
    changed = false;
    const m = cs.length;
    for (let k = closed ? 0 : 1; k < (closed ? m : m - 1); k++) {
      const a = R[cs[(k - 1 + m) % m]], b = R[cs[k]], c = R[cs[(k + 1) % m]];
      if (dirDiff(angOf(a, b), angOf(b, c)) < 24) { cs.splice(k, 1); changed = true; break; }
    }
  }
  return cs;
}
/* the points of R from index i to j (going round when closed) */
const span = (R, i, j, closed) => { if (!closed || j >= i) return R.slice(i, j + 1); return [...R.slice(i), ...R.slice(0, j + 1)]; };
/* segments between corners as fitted lines; the vertices where neighbouring lines meet; the worst straightness */
function segmentsOf(R, cs, closed) {
  const m = cs.length, segs = [];
  for (let k = 0; k < (closed ? m : m - 1); k++) {
    const pts = span(R, cs[k], cs[(k + 1) % m], closed), len = d2(pts[0], pts[pts.length - 1]);
    /* the middle of the segment: the ends are rounded by the hand */
    const cut = Math.floor(pts.length * 0.15), mid = pts.length > 6 ? pts.slice(cut, pts.length - cut) : pts;
    const L = fitLine(mid.length >= 2 ? mid : pts), all = fitLine(pts);
    const P = pathLength(pts);
    segs.push({pts, L, len, path: P, straight: len / (P || 1), dev: Math.max(...pts.map(p => Math.abs(-(p.x - L.c.x) * L.d.y + (p.y - L.c.y) * L.d.x))) / (len || 1), all});
  }
  return segs;
}
function verticesOf(R, cs, segs, closed) {
  const m = segs.length, out = [];
  if (closed) {
    for (let k = 0; k < m; k++) { const a = segs[(k - 1 + m) % m].L, b = segs[k].L, x = intersect(a, b); const raw = R[cs[k]]; out.push(x && d2(x, raw) < 0.3 * Math.max(segs[k].len, 1e-9) ? x : {x: raw.x, y: raw.y}); }
  } else {
    out.push(project(segs[0].L, R[0]));
    for (let k = 1; k < m; k++) { const x = intersect(segs[k - 1].L, segs[k].L), raw = R[cs[k]]; out.push(x && d2(x, raw) < 0.3 * Math.min(segs[k - 1].len, segs[k].len) ? x : {x: raw.x, y: raw.y}); }
    out.push(project(segs[m - 1].L, R[R.length - 1]));
  }
  return out.map(p => ({x: p.x, y: p.y}));
}
const distToSeg = (p, a, b) => { const dx = b.x - a.x, dy = b.y - a.y, L2 = dx * dx + dy * dy || 1e-18, t = clamp(((p.x - a.x) * dx + (p.y - a.y) * dy) / L2, 0, 1); return hyp(p.x - a.x - t * dx, p.y - a.y - t * dy); };
const polyErr = (R, V, closed) => { let s = 0; for (const p of R) { let m = Infinity; for (let i = 0; i < V.length - (closed ? 0 : 1); i++) m = Math.min(m, distToSeg(p, V[i], V[(i + 1) % V.length])); s += m; } return s / R.length; };
const interior = V => V.map((b, i) => { const a = V[(i - 1 + V.length) % V.length], c = V[(i + 1) % V.length]; return 180 - dirDiff(angOf(a, b), angOf(b, c)); });

/* ── snapping ── */
const snapStepAngle = (deg, {snapStep = 15, angleTol = 6, axisTol = 8} = {}) => {
  const k = Math.round(deg / snapStep) * snapStep, tol = k % 90 === 0 ? axisTol : k % 45 === 0 ? angleTol + 1 : angleTol;
  return Math.abs(deg - k) <= tol ? k : null;
};
const nearest = (p, cands, r) => { let best = null, bd = r; for (const c of cands || []) { const d = d2(p, c); if (d <= bd) { bd = d; best = c; } } return best; };
/** a line from a to b made clean: ends on nearby candidate points, the direction on 15° steps */
export function snapLine(a, b, opts = {}) {
  const unit = opts.unit ?? 1, r = (opts.snapPx ?? INK_DEFAULTS.snapPx) * unit, C = opts.candidates || [];
  const ca = nearest(a, C, r), cb = nearest(b, C.filter(c => c !== ca), r);
  let A = ca ? {x: ca.x, y: ca.y} : {...a}, B = cb ? {x: cb.x, y: cb.y} : {...b}, angle = null;
  if (!(ca && cb)) {
    const deg = angOf(A, B) * DEG, s = snapStepAngle(deg, opts);
    if (s != null) {
      angle = normDeg(s); const len = d2(A, B), u = {x: Math.cos(s / DEG), y: Math.sin(s / DEG)};
      if (cb && !ca) A = {x: B.x - u.x * len, y: B.y - u.y * len}; else B = {x: A.x + u.x * len, y: A.y + u.y * len};
    }
  }
  return {a: {x: A.x, y: A.y}, b: {x: B.x, y: B.y}, angle, snapA: ca?.id || (ca ? true : null), snapB: cb?.id || (cb ? true : null)};
}

/* ── one stroke ── */
const SHAPE_PRIORITY = ['line', 'arrow', 'rect', 'square', 'circle', 'ellipse', 'triangle', 'incline', 'polygon', 'polyline', 'arc', 'zigzag', 'coil', 'wave', 'curve'];
function analyse(stroke, opts) {
  const pts = stroke.points, unit = opts.unit ?? 1, L = pathLength(pts), bb = bounds(pts);
  const step = Math.max(Math.min(bb.diag / 48, L / 160), 0.6 * unit, L / 1500);
  let R = smooth121(resample(pts, step), false, 1);
  const chord = d2(pts[0], pts[pts.length - 1]);
  /* closed: the ends meet, or one end runs past the other (the loop is cut where it comes back) */
  let closed = false;
  if (L > 1.6 * bb.diag && R.length > 12) {
    const n = R.length, s0 = R[0], e0 = R[n - 1];
    let bj = -1, bd = Infinity; for (let j = Math.floor(n * 0.6); j < n; j++) { const d = d2(R[j], s0); if (d < bd) { bd = d; bj = j; } }
    let bi = -1, bd2 = Infinity; for (let i = 0; i < Math.floor(n * 0.4); i++) { const d = d2(R[i], e0); if (d < bd2) { bd2 = d; bi = i; } }
    const tol = Math.max(0.2 * bb.diag, 6 * unit);
    if (bd <= bd2 && bd < tol && (n - 1 - bj) < 0.3 * n) { R = R.slice(0, bj + 1); closed = true; }
    else if (bd2 < tol && bi < 0.3 * n) { R = R.slice(bi); closed = true; }
  }
  if (closed && d2(R[0], R[R.length - 1]) < step * 1.5 && R.length > 3) R = R.slice(0, -1);
  if (closed) R = smooth121(R, true, 1);
  return {pts, R, L, bb, chord, closed, unit, step};
}
const res = (type, params, confidence, extra = {}) => ({type, params, confidence: r4(clamp(confidence, 0, 1)), ...extra});

function closedCandidates(A, opts) {
  const out = [], {R, bb} = A;
  const E = fitEllipse(R);
  if (E) {
    const conf = 1 - E.err / 0.1;
    const ratio = Math.min(E.a, E.b) / Math.max(E.a, E.b);
    let rot = normDeg(E.th * DEG), rx = E.a, ry = E.b;
    /* axis-aligned when close: rot in (-90, 90], then 0 or 90 swaps the radii */
    const near = snapStepAngle(rot, {snapStep: 90, axisTol: 10, angleTol: 0});
    if (near != null) { if (Math.abs(near) === 90) [rx, ry] = [ry, rx]; rot = 0; }
    if (rot > 90) rot -= 180; if (rot <= -90) rot += 180;
    const circ = res('circle', {cx: E.c.x, cy: E.c.y, r: (E.a + E.b) / 2}, conf * (ratio > 0.8 ? 1 : 0.6 + 0.4 * ratio));
    const ell = res('ellipse', {cx: E.c.x, cy: E.c.y, rx, ry, rot}, conf * (ratio > 0.88 ? 0.9 : 1));
    out.push(circ, ell);
  }
  const cs = corners(R, true);
  if (cs.length >= 3 && cs.length <= 8) {
    const segs = segmentsOf(R, cs, true), V = verticesOf(R, cs, segs, true), err = polyErr(R, V, true) / bb.diag;
    const straight = Math.min(...segs.map(s => s.straight));
    const conf = (1 - err / 0.035) * clamp((straight - 0.8) / 0.12, 0, 1);
    const ang = interior(V);
    if (V.length === 4 && ang.every(a => Math.abs(a - 90) < 16)) {
      /* the box: its turn from the four sides (angles mod 90), its extent in that frame */
      let sx = 0, sy = 0; for (let i = 0; i < 4; i++) { const t = angOf(V[i], V[(i + 1) % 4]) * 4; sx += Math.cos(t); sy += Math.sin(t); }
      let th = Math.atan2(sy, sx) / 4 * DEG; if (Math.abs(th) < 8) th = 0; else { const s = snapStepAngle(th, opts); if (s != null) th = s; }
      const c = Math.cos(th / DEG), s = Math.sin(th / DEG), cx0 = V.reduce((a, p) => a + p.x, 0) / 4, cy0 = V.reduce((a, p) => a + p.y, 0) / 4;
      const loc = V.map(p => ({u: (p.x - cx0) * c + (p.y - cy0) * s, v: -(p.x - cx0) * s + (p.y - cy0) * c}));
      const us = loc.map(q => q.u).sort((a, b) => a - b), vs = loc.map(q => q.v).sort((a, b) => a - b);
      const u0 = (us[0] + us[1]) / 2, u1 = (us[2] + us[3]) / 2, v0 = (vs[0] + vs[1]) / 2, v1 = (vs[2] + vs[3]) / 2;
      const mu = (u0 + u1) / 2, mv = (v0 + v1) / 2, w = u1 - u0, h = v1 - v0;
      const cx = cx0 + mu * c - mv * s, cy = cy0 + mu * s + mv * c;
      const sq = Math.abs(w - h) / Math.max(w, h) < 0.12;
      const rect = res('rect', {cx, cy, w, h, rot: th}, conf), square = res('square', {cx, cy, w: (w + h) / 2, h: (w + h) / 2, rot: th}, conf * (sq ? 1.02 : 0.7));
      out.push(sq ? square : rect, sq ? {...rect, confidence: r4(rect.confidence * 0.95)} : square);
    } else if (V.length === 3) {
      const tri = triangleOf(V);
      out.push(res('triangle', {pts: tri.pts, right: tri.right}, conf));
      if (tri.incline) out.push(res('incline', tri.incline, conf * 0.97));
    }
    if (V.length >= 3) out.push(res('polygon', {pts: V}, conf * (V.length === 4 || V.length === 3 ? 0.9 : 1)));
  }
  return out;
}
/* a triangle: a side close to level made level; a right angle on a level base gives an incline (the slope's foot, the
   base's left end, the angle at the foot, the slope's length, flip when it rises to the left) */
function triangleOf(V0) {
  let V = V0.map(p => ({...p}));
  const ang = interior(V);
  let right = -1; ang.forEach((a, i) => { if (Math.abs(a - 90) < 12 && (right < 0 || Math.abs(a - 90) < Math.abs(ang[right] - 90))) right = i; });
  let incline = null;
  if (right >= 0) {
    const Rv = V[right], P = V[(right + 1) % 3], Q = V[(right + 2) % 3];
    const lvl = p => lineDiff(angOf(Rv, p), 0) < 10;
    const base = lvl(P) ? P : lvl(Q) ? Q : null, top = base === P ? Q : base === Q ? P : null;
    if (base && top && top.y > Rv.y - 1e-12 && Math.abs(top.y - Rv.y) > 1e-9) {
      const b = Math.abs(base.x - Rv.x), h = Math.abs(top.y - Rv.y);
      let angle = Math.atan2(h, b) * DEG; const s15 = Math.round(angle / 15) * 15; angle = Math.abs(angle - s15) < 2.5 ? s15 : Math.round(angle);
      angle = clamp(angle, 1, 89);
      const length = hyp(b, h), rises = base.x < Rv.x ? 'right' : 'left', baseLen = length * Math.cos(angle / DEG);
      const y = Rv.y, x = rises === 'right' ? Rv.x - baseLen : Rv.x;
      incline = {x, y, angle, length, flip: rises === 'left'};
      const foot = {x: rises === 'right' ? x : x + baseLen, y}, corner = {x: rises === 'right' ? x + baseLen : x, y}, apex = {x: corner.x, y: y + length * Math.sin(angle / DEG)};
      V = [foot, corner, apex];
    }
  }
  if (!incline) {
    for (let i = 0; i < 3; i++) { const a = V[i], b = V[(i + 1) % 3]; if (lineDiff(angOf(a, b), 0) < 3) { const y = (a.y + b.y) / 2; a.y = y; b.y = y; break; } }
  }
  return {pts: V, right: right >= 0, incline};
}

function openCandidates(A, opts) {
  const out = [], {R, L, bb, chord, unit} = A;
  /* a line */
  const Lf = fitLine(R), straight = chord / (L || 1), e = Lf.max / Math.max(chord, 1e-9);
  if (straight > 0.85) {
    const conf = (1 - e / 0.08) * clamp((straight - 0.86) / 0.08, 0, 1);
    const a = project(Lf, R[0]), b = project(Lf, R[R.length - 1]);
    out.push(res('line', snapLine(a, b, opts), conf));
  }
  const cs = corners(R, false);
  const segs = cs.length >= 2 ? segmentsOf(R, cs, false) : [];
  /* an arrow drawn in one stroke: a straight shaft, then a head that turns back near its tip (or the head first) */
  for (const rev of [false, true]) {
    const RR = rev ? [...R].reverse() : R, cc = rev ? cs.map(i => R.length - 1 - i).reverse() : cs;
    const arr = arrowOne(RR, cc, opts);
    if (arr) { out.push(arr); break; }
  }
  /* a polyline: every part between corners straight */
  if (segs.length >= 2 && segs.length <= 8) {
    const V = verticesOf(R, cs, segs, false), err = polyErr(R, V, false) / bb.diag, worst = Math.min(...segs.map(s => s.straight));
    let conf = clamp(1 - err / 0.03, 0, 1) * clamp((worst - 0.86) / 0.08, 0, 1);
    /* short pieces that turn back sharply are an arrow's head, not corners of a path */
    if (out.some(c => c.type === 'arrow')) conf *= 0.6;
    out.push(res('polyline', {pts: snapPolyline(V, opts)}, conf));
  }
  /* oscillations: a zigzag (resistor, spring), a sine wave, a coil; a path that swings to and fro is one of them */
  const osc = oscillation(R, A, opts);
  if (osc) { out.push(...osc); if (osc.some(c => c.confidence > 0.45)) for (const c of out) if (c.type === 'polyline') c.confidence = r4(c.confidence * 0.6); }
  /* an arc */
  if (straight < 0.98) {
    const C = fitCircle(R);
    if (C && C.r < 4 * bb.diag) {
      let sw = 0; for (let i = 1; i < R.length; i++) sw += normDeg((angOf(C.c, R[i]) - angOf(C.c, R[i - 1])) * DEG);
      if (Math.abs(sw) > 25 && Math.abs(sw) < 345) {
        const a0 = angOf(C.c, R[0]) * DEG, a1 = a0 + sw;
        const from = sw > 0 ? a0 : a1, to = sw > 0 ? a1 : a0;
        const conf = (1 - C.err / 0.05) * clamp((Math.abs(sw) - 20) / 25, 0, 1) * (cs.length > 2 ? 0.6 : 1);
        out.push(res('arc', {cx: C.c.x, cy: C.c.y, r: C.r, from: normDeg(from), to: normDeg(from) + (to - from), sweep: sw}, conf));
      }
    }
  }
  /* any smooth curve as a Bézier */
  if (straight < 0.97 && cs.length <= 2) {
    const B = fitBezier(R);
    if (B) out.push(res('curve', {p0: B.p0, p1: B.p1, p2: B.p2, p3: B.p3}, Math.min(0.72, 1 - B.max / bb.diag / 0.05)));
  }
  return out;
}
function snapPolyline(V, opts) {
  const out = [{...V[0]}];
  for (let i = 1; i < V.length; i++) {
    const prev = out[i - 1], deg = angOf(V[i - 1], V[i]) * DEG, s = snapStepAngle(deg, opts), len = d2(V[i - 1], V[i]);
    out.push(s == null ? {...V[i]} : {x: prev.x + Math.cos(s / DEG) * len, y: prev.y + Math.sin(s / DEG) * len});
  }
  return out;
}
function arrowOne(R, cs, opts) {
  if (cs.length < 3) return null;
  const tipI = cs[1], shaft = R.slice(0, tipI + 1), head = R.slice(tipI);
  const sl = pathLength(shaft), hl = pathLength(head), tip = R[tipI], tail = R[0];
  const shaftLen = d2(tail, tip);
  if (shaftLen < 0.4 * pathLength(R) || shaftLen / (sl || 1) < 0.93 || hl > 1.1 * shaftLen || hl < 0.08 * shaftLen) return null;
  if (head.some(p => d2(p, tip) > 0.55 * shaftLen)) return null;
  const Lf = fitLine(shaft); if (Lf.max / shaftLen > 0.07) return null;
  const back = angOf(tip, tail), b1 = angOf(tip, R[cs[2]]);
  if (dirDiff(back, b1) > 70 || dirDiff(back, b1) < 8) return null;
  /* the head's barbs: one or two, either side of the shaft */
  const side = p => Math.sign((tip.x - tail.x) * (p.y - tail.y) - (tip.y - tail.y) * (p.x - tail.x));
  const sides = new Set(head.filter(p => d2(p, tip) > 0.08 * shaftLen).map(side));
  const s = snapLine(tail, tip, opts);
  return res('arrow', {a: s.a, b: s.b, angle: s.angle, heads: 'end', barbs: sides.size}, 0.9 - (sides.size > 1 ? 0 : 0.04));
}
/* a stroke that swings about a line: a zigzag (sharp turns), a sine wave (round turns) or a coil (loops) */
function oscillation(R, A, opts) {
  const {L, chord} = A; if (R.length < 16 || chord < 0.15 * L) return null;
  const a = R[0], b = R[R.length - 1], d = {x: (b.x - a.x) / chord, y: (b.y - a.y) / chord};
  /* v from the best line through the stroke (a wave's ends are rarely on its axis), u along the chord */
  const Lt = fitLine(R); let dt = Lt.d; if (dt.x * d.x + dt.y * d.y < 0) dt = {x: -dt.x, y: -dt.y};
  const tilt = lineDiff(Math.atan2(dt.y, dt.x), Math.atan2(d.y, d.x)) < 10;
  const uv = R.map(p => ({u: (p.x - a.x) * d.x + (p.y - a.y) * d.y, v: tilt ? -(p.x - Lt.c.x) * dt.y + (p.y - Lt.c.y) * dt.x : -(p.x - a.x) * d.y + (p.y - a.y) * d.x}));
  let fwd = 0, bwd = 0; for (let i = 1; i < uv.length; i++) { const du = uv[i].u - uv[i - 1].u; if (du > 0) fwd += du; else bwd -= du; }
  const vs = uv.map(q => q.v).sort((x, y) => x - y), amp = (vs[Math.floor(vs.length * 0.97)] - vs[Math.floor(vs.length * 0.03)]) / 2;
  if (amp < 0.03 * chord || amp > 0.7 * chord) return null;
  const back = bwd / (fwd + bwd), out = [];
  if (back > 0.07) {
    /* loops: runs backwards along the axis, evenly spaced, of similar height */
    const runs = []; let start = -1, acc = 0;
    for (let i = 1; i < uv.length; i++) {
      const du = uv[i].u - uv[i - 1].u;
      if (du < 0) { if (start < 0) { start = i; acc = 0; } acc -= du; }
      else if (start >= 0) { if (acc > 0.008 * chord) runs.push({i: start, j: i, u: uv[start].u, acc}); start = -1; }
    }
    const big = Math.max(0, ...runs.map(r => r.acc));
    runs.splice(0, runs.length, ...runs.filter(r => r.acc > 0.3 * big));
    if (runs.length >= 3) {
      const gaps = runs.slice(1).map((r, k) => r.u - runs[k].u), mg = gaps.reduce((s, x) => s + x, 0) / gaps.length;
      const cv = Math.sqrt(gaps.reduce((s, x) => s + (x - mg) ** 2, 0) / gaps.length) / (Math.abs(mg) || 1e-9);
      const mono = gaps.every(g => g > 0);
      if (mono && cv < 0.45) {
        const conf = 0.88 * clamp(1 - cv / 0.6, 0, 1) + 0.1;
        const P = {a: {...a}, b: {...b}, n: runs.length, amp, kind: 'spring'};
        out.push(res('coil', P, conf), res('coil', {...P, kind: 'inductor'}, conf * 0.9));
      }
    }
    if (out.length) return out;
  }
  if (back > 0.12) return null;
  /* excursions to either side with hysteresis */
  const h = 0.35 * amp, ex = [];
  let cur = null;
  for (let i = 0; i < uv.length; i++) {
    const v = uv[i].v, sg = v > h ? 1 : v < -h ? -1 : 0;
    if (sg && (!cur || cur.s !== sg)) { if (cur) ex.push(cur); cur = {s: sg, i, peak: i}; }
    else if (sg && cur && Math.abs(v) > Math.abs(uv[cur.peak].v)) cur.peak = i;
  }
  if (cur) ex.push(cur);
  if (ex.length < 4) return null;
  /* teeth and crests of about one height */
  const peaks = ex.map(e => Math.abs(uv[e.peak].v)), mp = peaks.reduce((x, y) => x + y, 0) / peaks.length;
  if (peaks.slice(1, -1).some(p => p < 0.45 * mp || p > 1.7 * mp)) return null;
  /* zero crossings between neighbouring excursions */
  const zc = [];
  for (let k = 1; k < ex.length; k++) {
    for (let i = ex[k - 1].peak; i < ex[k].peak; i++) {
      const v0 = uv[i].v, v1 = uv[i + 1].v;
      if (v0 === 0 || (v0 < 0) !== (v1 < 0)) { const t = v0 / ((v0 - v1) || 1e-12); zc.push(uv[i].u + (uv[i + 1].u - uv[i].u) * t); break; }
    }
  }
  if (zc.length !== ex.length - 1) return null;
  /* each inner half-wave against a triangle and a sine through the same crossings and peak */
  let eTri = 0, eSin = 0, nPts = 0;
  for (let k = 1; k < ex.length - 1; k++) {
    const ua = zc[k - 1], ub = zc[k], P = uv[ex[k].peak], up = clamp(P.u, ua + 1e-9, ub - 1e-9), Av = P.v;
    for (let i = ex[k - 1].peak; i <= ex[k + 1].peak; i++) {
      const q = uv[i]; if (q.u < ua || q.u > ub) continue;
      const s = q.u < up ? (q.u - ua) / (up - ua) : 1 + (q.u - up) / (ub - up);
      const tri = Av * (s < 1 ? s : 2 - s), sin = Av * Math.sin(PI / 2 * s);
      eTri += (q.v - tri) ** 2; eSin += (q.v - sin) ** 2; nPts++;
    }
  }
  if (!nPts) return null;
  eTri = Math.sqrt(eTri / nPts) / amp; eSin = Math.sqrt(eSin / nPts) / amp;
  const halfW = zc.length > 1 ? (zc[zc.length - 1] - zc[0]) / (zc.length - 1) : chord / ex.length;
  const widths = zc.slice(1).map((z, k) => z - zc[k]), mw = widths.length ? widths.reduce((s, x) => s + x, 0) / widths.length : halfW;
  const cv = widths.length ? Math.sqrt(widths.reduce((s, x) => s + (x - mw) ** 2, 0) / widths.length) / (mw || 1) : 0;
  const reg = clamp(1 - cv / 0.6, 0, 1);
  const zig = eTri < eSin * 0.85 || eTri < 0.12;
  const n = ex.length;
  if (zig || eTri < eSin * 1.4) {
    const conf = ((0.55 + 0.4 * reg) * clamp(1 - eTri / 0.35, 0, 1) + 0.05) * (zig ? 1 : 0.7);
    /* a resistor has a few teeth, a spring many; the editor's context (what the ends touch) may say otherwise */
    const P = {a: {...a}, b: {...b}, n, amp, start: ex[0].i, end: ex[n - 1].i};
    const many = n >= 9;
    out.push(res('zigzag', {...P, kind: many ? 'spring' : 'resistor'}, conf), res('zigzag', {...P, kind: many ? 'resistor' : 'spring'}, conf * 0.85));
  }
  /* a sine wave: the wavelength from the crossings, the phase from the first one */
  const lambda = 2 * halfW, Aw = ex.slice(1, -1).reduce((s, e) => s + Math.abs(uv[e.peak].v), 0) / Math.max(1, n - 2);
  const k = 2 * PI / lambda, rising = uv[ex[1].peak].v > 0;
  const phase = normDeg((rising ? -k * zc[0] : PI - k * zc[0]) * DEG);
  const sConf = (0.5 + 0.45 * reg) * clamp(1 - eSin / 0.3, 0, 1) * (zig ? 0.8 : 1) + 0.05;
  /* the wave's own axis: the best line through it (its ends are rarely on the axis) */
  const Lf = fitLine(R); let dw = Lf.d; if (dw.x * d.x + dw.y * d.y < 0) dw = {x: -dw.x, y: -dw.y};
  const pa = project(Lf, R[0]), pb = project(Lf, R[R.length - 1]), wlen = Math.abs(pb.t - pa.t);
  const off = (R[0].x - pa.x) * -dw.y + (R[0].y - pa.y) * dw.x, ph2 = Aw > 0 && Math.abs(off) < Aw ? Math.asin(clamp(off / Aw, -1, 1)) : null;
  const phaseW = ph2 == null ? phase : normDeg((ex[0].s > 0 ? ph2 : PI - ph2) * DEG);
  out.push(res('wave', {x: pa.x, y: pa.y, len: wlen, A: Aw, lambda, phase: phaseW, angle: Math.atan2(dw.y, dw.x) * DEG, n}, sConf));
  return out;
}

/** the recognised shape of one stroke: the best result, and the others it could be ("다른 모양으로"); a stroke that
 *  fits nothing well (confidence < minConfidence) is kept freehand, smoothed */
export function recognizeStroke(raw, opts = {}) {
  const t0 = now0();
  const o = {...INK_DEFAULTS, ...opts}, stroke = normStroke(raw);
  const pts = stroke.points, unit = o.unit;
  const free = () => res('freehand', {pts: smoothFreehand(pts, {unit}), lw: strokeLw(pts)}, 0.5);
  if (pts.length < 2) return {...res('dot', {x: pts[0]?.x ?? 0, y: pts[0]?.y ?? 0, len: 0}, 0.5), alternatives: [], ms: 0};
  const A = analyse(stroke, o);
  if (A.L < 7 * unit || A.bb.diag < 5 * unit) {
    const c = {x: A.bb.cx, y: A.bb.cy};
    return {...res('dot', {x: c.x, y: c.y, len: A.L, a: {...pts[0]}, b: {...pts[pts.length - 1]}}, 0.55), alternatives: [free()], ms: r4(now0() - t0)};
  }
  const cands = (A.closed ? closedCandidates(A, o) : openCandidates(A, o)).filter(c => c.confidence > 0.05);
  cands.sort((x, y) => y.confidence - x.confidence || SHAPE_PRIORITY.indexOf(x.type) - SHAPE_PRIORITY.indexOf(y.type));
  const uniq = []; for (const c of cands) if (!uniq.some(u => u.type === c.type && JSON.stringify(u.params.kind) === JSON.stringify(c.params.kind))) uniq.push(c);
  const fh = free();
  let best = uniq[0], alternatives;
  if (!best || best.confidence < o.minConfidence) { alternatives = uniq.slice(0, 4); best = fh; }
  else alternatives = [...uniq.slice(1, 5), fh];
  return {...best, closed: A.closed, alternatives, ms: r4(now0() - t0)};
}

/* ── several strokes ── */
const asLine = it => {
  const r = it.result; if (!r) return null;
  if (r.type === 'line' || r.type === 'arrow') return {a: r.params.a, b: r.params.b};
  const alt = (r.alternatives || []).find(x => x.type === 'line' && x.confidence > 0.45);
  if (alt) return {a: alt.params.a, b: alt.params.b};
  if (r.type === 'dot') return {a: r.params.a || {x: r.params.x, y: r.params.y}, b: r.params.b || {x: r.params.x, y: r.params.y}, dot: true};
  return null;
};
const segInfo = s => { const len = d2(s.a, s.b), m = lerp(s.a, s.b, 0.5), th = len > 0 ? angOf(s.a, s.b) : 0; return {...s, len, m, th}; };
/** a shape made of the last strokes (items: [{stroke, result}] oldest first): dashed line, ground, cell or capacitor,
 *  an arrow with a separate head. The result says how many of the last strokes it uses (strokes) */
export function recognizeGroup(items, opts = {}) {
  const o = {...INK_DEFAULTS, ...opts};
  if (!Array.isArray(items) || items.length < 2) return null;
  const segs = items.map(asLine).map(s => s && segInfo(s));
  const n = items.length;
  /* a dashed or dotted line: three or more short pieces in a row on one line */
  for (let k = Math.min(n, 40); k >= 3; k--) {
    const S = segs.slice(n - k); if (S.some(s => !s)) continue;
    const r = dashed(S, o); if (r) return {...r, strokes: k};
  }
  for (const k of [4, 3]) if (n >= k) { const S = segs.slice(n - k); if (S.every(Boolean)) { const r = ground(S, o); if (r) return {...r, strokes: k}; } }
  for (const k of [4, 3, 2]) if (n >= k) { const S = segs.slice(n - k); if (S.every(Boolean)) { const r = bars(S, o); if (r) return {...r, strokes: k}; } }
  for (const k of [3, 2]) if (n >= k) { const r = arrowGroup(items.slice(n - k), o); if (r) return {...r, strokes: k}; }
  return null;
}
function dashed(S, o) {
  const pts = S.map(s => s.m), L = fitLine(pts.length >= 2 ? pts : [S[0].a, S[0].b]);
  const lens = S.map(s => s.len), mean = lens.reduce((a, b) => a + b, 0) / S.length;
  const ext = S.flatMap(s => [project(L, s.a).t, project(L, s.b).t]), t0 = Math.min(...ext), t1 = Math.max(...ext), total = t1 - t0;
  if (total < 3 * mean || S.some(s => s.len > 0.4 * total)) return null;
  if (L.max > Math.max(0.35 * mean, 3 * (o.unit ?? 1))) return null;
  const dots = S.every(s => s.dot || s.len < 6 * (o.unit ?? 1));
  if (!dots && S.some(s => !s.dot && lineDiff(s.th, Math.atan2(L.d.y, L.d.x)) > 14)) return null;
  /* in order along the line, apart */
  const ord = S.map(s => ({lo: Math.min(project(L, s.a).t, project(L, s.b).t), hi: Math.max(project(L, s.a).t, project(L, s.b).t)})).sort((a, b) => a.lo - b.lo);
  for (let i = 1; i < ord.length; i++) if (ord[i].lo < ord[i - 1].hi - 0.25 * mean) return null;
  const a = {x: L.c.x + L.d.x * t0, y: L.c.y + L.d.y * t0}, b = {x: L.c.x + L.d.x * t1, y: L.c.y + L.d.y * t1};
  const first = S[0].m, fa = d2(first, a) < d2(first, b);
  const s = snapLine(fa ? a : b, fa ? b : a, o);
  return res('dashed', {a: s.a, b: s.b, angle: s.angle, pattern: dots ? 'dotted' : 'dashed'}, 0.9);
}
/* parallel bars, centred on one axis across them */
function stackOf(B) {
  const th = B[0].th;
  if (B.some(b => b.dot || lineDiff(b.th, th) > 14)) return null;
  const u = {x: Math.cos(th), y: Math.sin(th)}, nrm = {x: -u.y, y: u.x};
  const along = b => (b.m.x - B[0].m.x) * u.x + (b.m.y - B[0].m.y) * u.y, across = b => (b.m.x - B[0].m.x) * nrm.x + (b.m.y - B[0].m.y) * nrm.y;
  return {u, nrm, along, across};
}
function bars(S, o) {
  /* two bars and up to two leads: a lead is perpendicular to the bars and starts at one of them */
  for (let i = 0; i < S.length; i++) for (let j = i + 1; j < S.length; j++) {
    const B = [S[i], S[j]], st = stackOf(B); if (!st) continue;
    const gap = Math.abs(st.across(B[1])), long = Math.max(B[0].len, B[1].len), short = Math.min(B[0].len, B[1].len);
    if (gap < 0.08 * long || gap > 0.9 * long || Math.abs(st.along(B[1])) > 0.3 * long) continue;
    const rest = S.filter((_, k) => k !== i && k !== j), leads = [];
    let ok = true;
    for (const l of rest) {
      if (l.dot || lineDiff(l.th, st.u.x ? Math.atan2(st.nrm.y, st.nrm.x) : PI / 2) > 15) { ok = false; break; }
      const near = [l.a, l.b].map(p => Math.min(d2(p, B[0].m), d2(p, B[1].m))), k = near[0] < near[1] ? 0 : 1;
      if (near[k] > 0.35 * long) { ok = false; break; }
      leads.push({inner: k ? l.b : l.a, outer: k ? l.a : l.b});
    }
    if (!ok) continue;
    const ratio = short / long, cap = ratio > 0.72;
    const [neg, pos] = cap ? (st.across(B[1]) > 0 ? [B[0], B[1]] : [B[1], B[0]]) : (B[0].len < B[1].len ? [B[0], B[1]] : [B[1], B[0]]);
    const ax = {x: pos.m.x - neg.m.x, y: pos.m.y - neg.m.y}, al = hyp(ax.x, ax.y) || 1, n = {x: ax.x / al, y: ax.y / al};
    const m = lerp(neg.m, pos.m, 0.5), half = Math.max(1.1 * long, 1.6 * gap);
    let a = {x: m.x - n.x * half, y: m.y - n.y * half}, b = {x: m.x + n.x * half, y: m.y + n.y * half};
    for (const ld of leads) { if (d2(ld.outer, a) < d2(ld.outer, b)) a = {...ld.outer}; else b = {...ld.outer}; }
    const conf = 0.86 - (cap ? (1 - ratio) * 0.3 : Math.max(0, ratio - 0.5) * 0.3);
    const type = cap ? 'capacitor' : 'cell';
    return {...res(type, {a, b, gap, long, short}, conf), alternatives: [res(cap ? 'cell' : 'capacitor', {a, b, gap, long, short}, conf * 0.7)]};
  }
  return null;
}
function ground(S, o) {
  for (let skip = -1; skip < S.length; skip++) {
    const B = S.filter((_, k) => k !== skip), lead = skip >= 0 ? S[skip] : null;
    if (B.length !== 3 || (S.length === 4 && !lead) || (S.length === 3 && lead)) continue;
    const st = stackOf(B); if (!st) continue;
    const sorted = [...B].sort((a, b) => b.len - a.len);
    if (!(sorted[1].len < 0.92 * sorted[0].len && sorted[2].len < 0.92 * sorted[1].len)) continue;
    const ac = sorted.map(st.across), gap1 = ac[1] - ac[0], gap2 = ac[2] - ac[1];
    if (Math.sign(gap1) !== Math.sign(gap2) || Math.abs(gap1) < 0.05 * sorted[0].len || Math.abs(gap1) > 0.8 * sorted[0].len || Math.abs(gap2 - gap1) > 0.6 * Math.abs(gap1)) continue;
    if (sorted.some(b => Math.abs(st.along(b) - st.along(sorted[0])) > 0.25 * sorted[0].len)) continue;
    /* the side away from the short bars is up */
    const up = {x: -st.nrm.x * Math.sign(gap1), y: -st.nrm.y * Math.sign(gap1)};
    let top = {x: sorted[0].m.x + up.x * Math.abs(gap1) * 2.2, y: sorted[0].m.y + up.y * Math.abs(gap1) * 2.2};
    if (lead) {
      if (lineDiff(lead.th, Math.atan2(up.y, up.x)) > 15) continue;
      const k = d2(lead.a, sorted[0].m) < d2(lead.b, sorted[0].m) ? 0 : 1, inner = k ? lead.b : lead.a;
      if (d2(inner, sorted[0].m) > 0.4 * sorted[0].len) continue;
      top = {...(k ? lead.a : lead.b)};
    }
    return res('ground', {x: top.x, y: top.y, up: Math.atan2(up.y, up.x) * DEG}, lead ? 0.9 : 0.84);
  }
  return null;
}
function arrowGroup(items, o) {
  const shaftIt = items[0], sh = asLine(shaftIt); if (!sh || sh.dot || shaftIt.result.type === 'arrow') return null;
  const S = segInfo(sh); if (S.len < 10 * (o.unit ?? 1)) return null;
  const heads = {a: 0, b: 0};
  for (const it of items.slice(1)) {
    const r = it.result, pts = (r.type === 'polyline' ? r.params.pts : r.type === 'line' ? [r.params.a, r.params.b] : null);
    if (!pts) return null;
    if (pathLength(pts) > 1.2 * S.len) return null;
    let used = false;
    for (const end of ['a', 'b']) {
      const tip = S[end], other = end === 'a' ? S.b : S.a, back = angOf(tip, other);
      if (pts.length >= 3) {
        /* a V: its corner on the tip, both arms going back */
        const ci = pts.slice(1, -1).reduce((bi, p, i) => d2(p, tip) < d2(pts[bi], tip) ? i + 1 : bi, 1), c = pts[ci];
        if (d2(c, tip) > 0.25 * S.len) continue;
        const arms = [pts[0], pts[pts.length - 1]].map(p => dirDiff(angOf(c, p), back));
        if (arms.every(x => x > 10 && x < 70)) { heads[end]++; used = true; break; }
      } else {
        const [p, q] = d2(pts[0], tip) < d2(pts[1], tip) ? [pts[0], pts[1]] : [pts[1], pts[0]];
        if (d2(p, tip) > 0.2 * S.len || d2(p, q) > 0.6 * S.len) continue;
        const x = dirDiff(angOf(p, q), back);
        if (x > 10 && x < 70) { heads[end]++; used = true; break; }
      }
    }
    if (!used) return null;
  }
  if (!heads.a && !heads.b) return null;
  const toA = heads.a && !heads.b, s = snapLine(toA ? S.b : S.a, toA ? S.a : S.b, o);
  return res('arrow', {a: s.a, b: s.b, angle: s.angle, heads: heads.a && heads.b ? 'both' : 'end'}, 0.88);
}

/* ── results on the scene ── */
const PREFIX = {line: 'n', rect: 'rc', ellipse: 'el', poly: 'pg', bezier: 'bz', arc: 'a', vector: 'v', element: 'e', ground: 'gnd', incline: 'i', spring: 'k', wave: 'wave', label: 'l'};
const KIND_PREFIX = {resistor: 'R', capacitor: 'C', inductor: 'L', cell: 'E', battery: 'E'};
const ELEMENT_LOOK = {resistor: {value: 100, label: 'R', look: 'zigzag'}, capacitor: {value: 100, label: 'C'}, inductor: {value: 0.1, label: 'L'}, cell: {value: 1.5, label: '\\mathcal{E}'}, battery: {value: 12, label: '\\mathcal{E}'}};
/** points objects in a scene offer for snapping: ends of lines, wires and elements, corners and centres of shapes,
 *  bodies and anchors (with their id and type, so a spring can join them) */
export function candidatesFromScene(scene) {
  const out = [], objs = scene?.objects || [];
  const add = (x, y, o, role) => { if (Number.isFinite(x) && Number.isFinite(y)) out.push({x, y, id: o.id, type: o.type, role}); };
  for (const o of objs) {
    if ('x1' in o && 'x2' in o) { add(o.x1, o.y1, o, 'end'); add(o.x2, o.y2, o, 'end'); }
    else if (o.type === 'rect') { add(o.x, o.y, o, 'corner'); add(o.x + o.w, o.y, o, 'corner'); add(o.x, o.y + o.h, o, 'corner'); add(o.x + o.w, o.y + o.h, o, 'corner'); add(o.x + o.w / 2, o.y + o.h / 2, o, 'centre'); }
    else if (o.type === 'ellipse') add(o.x + o.w / 2, o.y + o.h / 2, o, 'centre');
    else if (o.type === 'poly') for (const [x, y] of o.pts || []) add(x, y, o, 'vertex');
    else if (isBody(o)) { const p = bodyPose(scene, o); add(p.x, p.y, o, 'body'); }
    else if (['pivot', 'ground', 'point', 'gpoint', 'pulley', 'charge'].includes(o.type)) add(o.x, o.y, o, 'point');
    else if (o.type === 'floor' || o.type === 'ceiling') { add(o.x, o.y, o, 'anchor'); add(o.x + o.w, o.y, o, 'anchor'); }
    else if (o.type === 'wall') { add(o.x, o.y, o, 'anchor'); add(o.x, o.y + o.h, o, 'anchor'); }
  }
  return out;
}
/* what a spring's end touches: a body, or an anchor (floor, ceiling, wall: its surface; a pivot) */
function attachAt(p, existing, scene, r) {
  let best = null, bd = r;
  for (const o of existing) {
    let d = Infinity;
    if (isBody(o)) { const q = bodyPose(scene, o), half = o.type === 'block' ? Math.max(o.w, o.h) / 2 : o.r; d = Math.max(0, d2(p, q) - half); }
    else if (o.type === 'floor' || o.type === 'ceiling') d = distToSeg(p, {x: o.x, y: o.y}, {x: o.x + o.w, y: o.y});
    else if (o.type === 'wall') d = distToSeg(p, {x: o.x, y: o.y}, {x: o.x, y: o.y + o.h});
    else if (o.type === 'pivot') d = d2(p, o);
    else continue;
    if (d <= bd) { bd = d; best = o; }
  }
  return best;
}
const zigPoints = (a, b, n, amp, lead = 0.12) => {
  const L = d2(a, b), u = {x: (b.x - a.x) / L, y: (b.y - a.y) / L}, nv = {x: -u.y, y: u.x}, pts = [a];
  const l0 = L * lead, body = L - 2 * l0, teeth = Math.max(2, n);
  pts.push({x: a.x + u.x * l0, y: a.y + u.y * l0});
  for (let i = 0; i < teeth; i++) { const t = l0 + body * (i + 0.5) / teeth, s = i % 2 ? -1 : 1; pts.push({x: a.x + u.x * t + nv.x * amp * s, y: a.y + u.y * t + nv.y * amp * s}); }
  pts.push({x: b.x - u.x * l0, y: b.y - u.y * l0}, b);
  return pts;
};
const coilPoints = (a, b, n, amp) => {
  const L = d2(a, b), u = {x: (b.x - a.x) / L, y: (b.y - a.y) / L}, nv = {x: -u.y, y: u.x}, pts = [], N = Math.max(3, n) * 16;
  const pitch = L / (Math.max(3, n) + 0.6);
  for (let i = 0; i <= N; i++) {
    const s = i / N * Math.max(3, n) * 2 * PI, along = pitch * s / (2 * PI) + pitch * 0.3 * (1 - Math.cos(s)), across = amp * Math.sin(s);
    pts.push({x: a.x + u.x * along + nv.x * across, y: a.y + u.y * along + nv.y * across});
  }
  return pts;
};
const sinePoints = p => { const pts = [], N = Math.min(390, Math.max(24, Math.round(p.len / p.lambda * 24))), c = Math.cos(p.angle / DEG), s = Math.sin(p.angle / DEG), k = 2 * PI / p.lambda;
  for (let i = 0; i <= N; i++) { const x = p.len * i / N, y = p.A * Math.sin(k * x + p.phase / DEG); pts.push({x: p.x + x * c - y * s, y: p.y + x * s + y * c}); } return pts; };

/** a result as objects of the scene (draw-scene.mjs types, complete with defaults and ids free in `existing`):
 *  grid rounds circuit ends (default 0.1; elements join where their ends coincide), look is the drawing style
 *  ({color, lw, pattern, fill}), unit sets the snap radius for joining a spring to bodies */
export function toSceneObjects(result, {grid = 0.1, existing = [], look = {}, unit = 0.01, idFor, snapPx = INK_DEFAULTS.snapPx, scene} = {}) {
  if (!result || !result.type) return [];
  const sc = scene || {objects: existing}, taken = new Set(existing.map(o => o.id)), out = [];
  const idOf = (type, kind) => { if (idFor) { const id = idFor(type, kind, taken); if (id && !taken.has(id)) { taken.add(id); return id; } } const p = (type === 'element' && KIND_PREFIX[kind]) || PREFIX[type] || 'o'; let n = 1; while (taken.has(p + n)) n++; taken.add(p + n); return p + n; };
  const color = look.color || 'black', lw = clamp(look.lw ?? result.params?.lw ?? 1, 0.2, 5), pattern = look.pattern && look.pattern !== 'none' ? look.pattern : 'solid';
  const C = v => clamp(r4(v), -200, 200) + 0, P = q => [C(q.x), C(q.y)];
  const push = (type, o) => { const kind = o.kind; const obj = {...defaults(type), ...o, id: idOf(type, kind)}; out.push(obj); return obj; };
  const snapG = v => grid > 0 ? Math.round(v / grid) * grid : v;
  const element = (kind, a0, b0) => {
    const cand = candidatesFromScene(sc).filter(c => c.role === 'end' && (c.type === 'element' || c.type === 'cwire'));
    const r = snapPx * unit;
    let a = nearest(a0, cand, r) || {x: snapG(a0.x), y: snapG(a0.y)}, b = nearest(b0, cand, r) || {x: snapG(b0.x), y: snapG(b0.y)};
    a = {x: a.x, y: a.y}; b = {x: b.x, y: b.y};
    const th = lineDiff(angOf(a0, b0), 0);
    if (th < 15 && Math.abs(a.y - b.y) < 3 * grid) { const y = snapG((a.y + b.y) / 2); a.y = b.y = y; }
    else if (th > 75 && Math.abs(a.x - b.x) < 3 * grid) { const x = snapG((a.x + b.x) / 2); a.x = b.x = x; }
    if (d2(a, b) < 1e-6) b = {x: a.x + grid, y: a.y};
    const extra = ELEMENT_LOOK[kind] || {};
    return push('element', {kind, x1: C(a.x), y1: C(a.y), x2: C(b.x), y2: C(b.y), ...extra});
  };
  const p = result.params || {};
  switch (result.type) {
    case 'line': case 'dashed':
      if (d2(p.a, p.b) > 1e-6) push('line', {x1: C(p.a.x), y1: C(p.a.y), x2: C(p.b.x), y2: C(p.b.y), pattern: result.type === 'dashed' ? p.pattern || 'dashed' : pattern, heads: 'none', color, lw});
      break;
    case 'arrow':
      if (d2(p.a, p.b) > 1e-6) push('line', {x1: C(p.a.x), y1: C(p.a.y), x2: C(p.b.x), y2: C(p.b.y), pattern, heads: p.heads || 'end', color, lw});
      break;
    case 'vector':
      push('vector', {x1: C(p.a.x), y1: C(p.a.y), x2: C(p.b.x), y2: C(p.b.y), label: p.label || ''});
      break;
    case 'polyline': case 'polygon': case 'triangle': {
      const closed = result.type !== 'polyline';
      push('poly', {pts: p.pts.slice(0, 400).map(P), closed, smooth: false, color, lw, pattern, fill: closed ? (look.fill || 'none') : 'none', heads: 'none'});
      break;
    }
    case 'rect': case 'square':
      push('rect', {x: C(p.cx - p.w / 2), y: C(p.cy - p.h / 2), w: clamp(r4(p.w), 0.05, 400), h: clamp(r4(p.h), 0.05, 400), rot: r4(normDeg(p.rot || 0)), color, lw, pattern, fill: look.fill || 'none'});
      break;
    case 'circle': case 'ellipse': {
      const rx = result.type === 'circle' ? p.r : p.rx, ry = result.type === 'circle' ? p.r : p.ry;
      push('ellipse', {x: C(p.cx - rx), y: C(p.cy - ry), w: clamp(r4(2 * rx), 0.05, 400), h: clamp(r4(2 * ry), 0.05, 400), rot: r4(result.type === 'circle' ? 0 : normDeg(p.rot || 0)), color, lw, pattern, fill: look.fill || 'none'});
      break;
    }
    case 'arc': {
      let from = normDeg(p.from), to = from + Math.abs(p.to - p.from); if (to > 360) { from -= 360; to -= 360; }
      push('arc', {x: C(p.cx), y: C(p.cy), r: clamp(r4(p.r), 0.02, 20), from: r4(from), to: r4(to), text: '', arrow: false, color, pattern, lw});
      break;
    }
    case 'curve':
      push('bezier', {x1: C(p.p0.x), y1: C(p.p0.y), cx1: C(p.p1.x), cy1: C(p.p1.y), cx2: C(p.p2.x), cy2: C(p.p2.y), x2: C(p.p3.x), y2: C(p.p3.y), color, lw, pattern, heads: 'none'});
      break;
    case 'incline':
      push('incline', {x: C(p.x), y: C(p.y), angle: clamp(Math.round(p.angle), 1, 89), length: clamp(r4(p.length), 0.1, 200), flip: !!p.flip, mu: 0});
      break;
    case 'zigzag': case 'coil': {
      const kind = p.kind || 'resistor';
      if (kind === 'resistor' || kind === 'inductor') { element(kind, p.a, p.b); break; }
      /* a spring joins what its ends touch (a body and a body or an anchor); else it stays a drawn spring */
      const r = Math.max(snapPx * unit, 0.15 * d2(p.a, p.b));
      const A = attachAt(p.a, existing, sc, r), B = attachAt(p.b, existing.filter(x => x !== A), sc, r);
      if (A && B && (isBody(A) || isBody(B)) && [...BODY_TYPES, ...ANCHOR_TYPES].includes(A.type) && [...BODY_TYPES, ...ANCHOR_TYPES].includes(B.type)) {
        push('spring', {a: A.id, b: B.id, L0: clamp(r4(d2(p.a, p.b)), 0.01, 100), coils: clamp(Math.round(p.n || 10), 3, 30), k: 50});
      } else {
        const pts = result.type === 'coil' ? coilPoints(p.a, p.b, p.n, p.amp) : zigPoints(p.a, p.b, p.n, p.amp);
        push('poly', {pts: pts.slice(0, 400).map(P), closed: false, smooth: result.type === 'coil', color, lw, pattern: 'solid', fill: 'none', heads: 'none'});
      }
      break;
    }
    case 'cell': case 'battery': case 'capacitor':
      element(result.type, p.a, p.b); break;
    case 'ground':
      push('ground', {x: C(snapG(p.x)), y: C(snapG(p.y))}); break;
    case 'wave': {
      const level = lineDiff(p.angle / DEG, 0) < 8;
      if (level && Math.abs(normDeg(p.angle)) < 90) {
        push('wave', {x: C(p.x), y: C(p.y), len: clamp(r4(p.len), 0.1, 400), A: clamp(r4(p.A), 0, 50), lambda: clamp(r4(p.lambda), 0.02, 400), phase: r4(normDeg(p.phase)), kind: 'travel', axis: false, envelope: false, arrow: false, showLambda: false, showA: false});
      } else push('poly', {pts: sinePoints(p).map(P), closed: false, smooth: true, color, lw, pattern, fill: 'none', heads: 'none'});
      break;
    }
    case 'freehand': case 'dot': {
      const pts = p.pts || [p.a || {x: p.x, y: p.y}, p.b || {x: p.x + grid / 4, y: p.y}];
      if (pts.length >= 2) push('poly', {pts: pts.slice(0, 400).map(P), closed: false, smooth: pts.length > 2, color, lw, pattern, fill: 'none', heads: 'none'});
      break;
    }
    case 'latex':
      push('label', {x: C(p.x), y: C(p.y), text: ('$' + String(p.latex || '').slice(0, 236) + '$'), size: clamp(Math.round(p.size || 18), 8, 48), color}); break;
    default: break;
  }
  return out;
}

/* ── changing a result while the pen is still down (after a hold) ── */
/** the snapped shape following the pen: a line's end goes where the pen is (still on 15° steps); any other shape is
 *  scaled about its centre by how far the pen moved from where it snapped */
export function adjustResult(result, from, to, opts = {}) {
  const p = result.params, o = {...INK_DEFAULTS, ...opts};
  if (['line', 'arrow', 'dashed'].includes(result.type)) { const s = snapLine(p.a, to, o); return {...result, params: {...p, b: s.b, angle: s.angle}}; }
  const c = centreOf(result); if (!c) return result;
  const k = clamp(d2(c, to) / Math.max(d2(c, from), 1e-9), 0.2, 5);
  const S = q => ({x: c.x + (q.x - c.x) * k, y: c.y + (q.y - c.y) * k});
  const q = {...p};
  for (const key of ['a', 'b', 'p0', 'p1', 'p2', 'p3']) if (q[key]) q[key] = S(q[key]);
  if (q.pts) q.pts = q.pts.map(S);
  for (const key of ['w', 'h', 'r', 'rx', 'ry', 'length', 'len', 'A', 'lambda', 'amp']) if (Number.isFinite(q[key])) q[key] *= k;
  if (Number.isFinite(q.x) && Number.isFinite(q.y)) { const z = S({x: q.x, y: q.y}); q.x = z.x; q.y = z.y; }
  return {...result, params: q};
}
function centreOf(r) {
  const p = r.params;
  if (Number.isFinite(p.cx)) return {x: p.cx, y: p.cy};
  if (p.pts) { const b = bounds(p.pts); return {x: b.cx, y: b.cy}; }
  if (p.a && p.b) return lerp(p.a, p.b, 0.5);
  if (p.p0) return lerp(p.p0, p.p3, 0.5);
  if (Number.isFinite(p.x)) return {x: p.x, y: p.y};
  return null;
}

/* ── the controller ── */
/** Pointer handling for the editor's pen tool. Handlers return true when they took the event (the editor then does
 *  nothing more with it) and false otherwise (a palm, a finger when 손가락으로 그리기 is off, a second finger: the
 *  editor pans or pinches as before).
 *    onShape(result, {replaces, stroke, alternatives}) → the ids of the objects it inserted (kept to replace them when
 *      the next strokes complete a group: a dashed line, a cell, an arrow with its head)
 *    onFreehand(result, {stroke}) → ids, as onShape (a stroke kept freehand, smoothed)
 *    onPreview(result | null, {stroke}) — the snapped shape to draw while the pen is still down (null: none)
 *    onStroke(stroke, {live}) — the stroke being drawn, to paint (live: true while the pen is down)
 *    onMathRegion({strokes, bounds}) — 수식 쓰기: the strokes written, after mathIdleMs of rest or finishMath()
 *    getCandidates(bounds) → points to snap to ([{x, y, id?, type?}]; candidatesFromScene(scene) gives them)
 *    toWorld(ev) → {x, y} in the scene's world; unit() → world units per CSS pixel */
export function createInkController({onShape, onFreehand, onPreview, onStroke, onMathRegion, getCandidates, toWorld, unit, options = {}, timers} = {}) {
  const T = timers || {set: (f, ms) => setTimeout(f, ms), clear: id => clearTimeout(id), now: now0};
  const opt = {...INK_DEFAULTS, ...options};
  let mode = options.mode || 'draw', cur = null, penSeen = 0, pending = [], math = [], mathTimer = null, seq = 0;
  const U = () => (typeof unit === 'function' ? unit() : unit) || opt.unit || 1;
  const W = ev => toWorld ? toWorld(ev) : {x: ev.offsetX ?? ev.clientX, y: -(ev.offsetY ?? ev.clientY)};
  const ropts = () => ({...opt, unit: U(), candidates: cur && getCandidates ? (getCandidates(bounds(cur.points)) || []) : []});
  function accepts(ev) {
    const type = ev.pointerType || 'mouse';
    if (mode === 'off') return false;
    if (type === 'pen') return true;
    if (type === 'touch') {
      if (penSeen) return false; /* a pen is in use: touches are the palm */
      if (!opt.fingerDraw) return false;
      if ((ev.width || 0) * (ev.height || 0) > opt.palmArea) return false;
      return true;
    }
    return opt.mouse && (ev.button ?? 0) === 0;
  }
  const point = (ev, t) => { const w = W(ev); return {x: w.x, y: w.y, t, pressure: ev.pointerType === 'mouse' ? 0.5 : (ev.pressure > 0 ? ev.pressure : 0.5)}; };
  function armHold() {
    if (!cur) return; if (cur.timer) T.clear(cur.timer);
    if (!opt.holdToSnap || mode !== 'draw') return;
    cur.timer = T.set(() => {
      if (!cur || cur.snapped) return;
      if (pathLength(cur.points) < 10 * U()) return;
      const r = recognizeStroke(cur, ropts());
      if (r.type === 'freehand' || r.type === 'dot') return;
      cur.snapped = {result: r, from: {...cur.points[cur.points.length - 1]}, now: r};
      onPreview?.(r, {stroke: cur});
    }, opt.holdMs);
  }
  function cancel() {
    if (!cur) return;
    if (cur.timer) T.clear(cur.timer);
    if (cur.snapped) onPreview?.(null, {stroke: cur});
    cur = null; onStroke?.(null, {live: false});
  }
  function pointerdown(ev) {
    if (ev.pointerType === 'pen') { penSeen = T.now(); if (cur && cur.pointerType === 'touch') cancel(); }
    if (cur) { if (ev.pointerType === 'touch' && cur.pointerType === 'touch') { cancel(); } return false; }
    if (!accepts(ev)) return false;
    const t = T.now();
    cur = {id: 'ink' + (++seq), pointerId: ev.pointerId, pointerType: ev.pointerType || 'mouse', points: [point(ev, t)], screen: {x: ev.clientX, y: ev.clientY}, timer: null, snapped: null};
    if (mathTimer) { T.clear(mathTimer); mathTimer = null; }
    armHold(); onStroke?.(cur, {live: true});
    return true;
  }
  function pointermove(ev) {
    if (!cur || ev.pointerId !== cur.pointerId) return false;
    const evs = typeof ev.getCoalescedEvents === 'function' ? ev.getCoalescedEvents() : null, list = evs && evs.length ? evs : [ev];
    for (const e of list) {
      const t = Number.isFinite(e.timeStamp) && e.timeStamp > 0 && !timers ? e.timeStamp : T.now();
      const q = point(e, t), last = cur.points[cur.points.length - 1];
      if (d2(q, last) < 0.35 * U()) continue;
      cur.points.push(q);
    }
    if (hyp(ev.clientX - cur.screen.x, ev.clientY - cur.screen.y) > opt.holdMovePx) {
      cur.screen = {x: ev.clientX, y: ev.clientY};
      if (cur.snapped) { cur.snapped.now = adjustResult(cur.snapped.result, cur.snapped.from, cur.points[cur.points.length - 1], ropts()); onPreview?.(cur.snapped.now, {stroke: cur}); }
      else armHold();
    }
    if (!cur.snapped) onStroke?.(cur, {live: true});
    return true;
  }
  function emit(r, stroke) {
    const now = T.now();
    /* the strokes that may still join this one: drawn one after another, each soon after and near the one before */
    if (pending.length && now - pending[pending.length - 1].end > opt.groupMs) pending = [];
    const item = {stroke, result: r, end: now, ids: []};
    if (opt.autoShape || stroke.snapped) {
      const chain = [];
      let next = bounds(stroke.points);
      for (let i = pending.length - 1; i >= 0 && chain.length < 40; i--) {
        const b = bounds(pending[i].stroke.points);
        if (hyp(b.cx - next.cx, b.cy - next.cy) > opt.groupPx * U() + (b.diag + next.diag) / 2) break;
        chain.unshift(pending[i]); next = b;
      }
      const g = recognizeGroup([...chain, item], ropts());
      if (g) {
        const used = chain.slice(chain.length - (g.strokes - 1)), replaces = used.flatMap(it => it.ids || []);
        const ids = onShape?.(g, {replaces, stroke, alternatives: g.alternatives || [], group: true}) || [];
        for (const it of used) it.ids = [];
        item.ids = Array.isArray(ids) ? ids : []; item.group = g.type;
        /* a dashed line can still grow by another dash: its strokes stay; any other group is complete */
        if (g.type !== 'dashed') pending = pending.filter(it => !used.includes(it));
        pending.push(item);
        return g;
      }
    }
    const isShape = r.type !== 'freehand';
    const ids = (isShape ? onShape?.(r, {replaces: [], stroke, alternatives: r.alternatives || []}) : onFreehand?.(r, {stroke})) || [];
    item.ids = Array.isArray(ids) ? ids : [];
    pending.push(item); if (pending.length > 40) pending.shift();
    return r;
  }
  function pointerup(ev) {
    if (!cur || (ev && ev.pointerId !== undefined && ev.pointerId !== cur.pointerId)) return false;
    if (ev && ev.type !== 'pointercancel' && Number.isFinite(ev.clientX)) { const q = point(ev, T.now()), last = cur.points[cur.points.length - 1]; if (d2(q, last) > 0.35 * U()) cur.points.push(q); }
    const stroke = cur; if (stroke.timer) T.clear(stroke.timer); cur = null;
    onStroke?.(null, {live: false});
    if (ev?.type === 'pointercancel') { if (stroke.snapped) onPreview?.(null, {stroke}); return true; }
    if (mode === 'math') {
      math.push({points: stroke.points, pointerType: stroke.pointerType, id: stroke.id});
      if (opt.mathIdleMs > 0) mathTimer = T.set(() => { mathTimer = null; finishMath(); }, opt.mathIdleMs);
      onFreehand?.({type: 'freehand', params: {pts: smoothFreehand(stroke.points, {unit: U()}), lw: strokeLw(stroke.points)}, confidence: 1, math: true}, {stroke, math: true});
      return true;
    }
    let r;
    if (stroke.snapped) { r = stroke.snapped.now; onPreview?.(null, {stroke}); }
    else if (opt.autoShape) r = recognizeStroke(stroke, ropts());
    else r = {type: 'freehand', params: {pts: smoothFreehand(stroke.points, {unit: U()}), lw: strokeLw(stroke.points)}, confidence: 1, alternatives: []};
    if (r.type === 'dot' && !opt.autoShape) r = {type: 'freehand', params: {pts: stroke.points.map(p => ({x: p.x, y: p.y})), lw: 1}, confidence: 1, alternatives: []};
    emit(r.type === 'dot' ? {...r, type: 'freehand', params: {pts: stroke.points.length > 1 ? stroke.points.map(p => ({x: p.x, y: p.y})) : [stroke.points[0], {x: stroke.points[0].x + U(), y: stroke.points[0].y}], lw: 1, dot: r.params}} : r, stroke);
    return true;
  }
  function finishMath() {
    if (mathTimer) { T.clear(mathTimer); mathTimer = null; }
    if (!math.length) return null;
    const strokes = math; math = [];
    const all = strokes.flatMap(s => s.points), region = {strokes, bounds: bounds(all)};
    onMathRegion?.(region);
    return region;
  }
  return {
    pointerdown, pointermove, pointerup, pointercancel: ev => pointerup({...ev, type: 'pointercancel', pointerId: ev?.pointerId}),
    cancel, finishMath,
    clearMath() { math = []; if (mathTimer) { T.clear(mathTimer); mathTimer = null; } },
    get mathStrokes() { return math.slice(); },
    get mode() { return mode; }, set mode(m) { if (['draw', 'math', 'off'].includes(m)) { if (m !== 'math' && math.length) finishMath(); mode = m; cancel(); } },
    get options() { return {...opt}; }, set(o) { Object.assign(opt, o || {}); },
    get drawing() { return !!cur; }, get current() { return cur; }, get penSeen() { return !!penSeen; },
    resetPen() { penSeen = 0; }, forget() { pending = []; },
    /** tell the controller the ids an earlier result became (when onShape could not return them) */
    bind(strokeId, ids) { const it = pending.find(x => x.stroke.id === strokeId); if (it) it.ids = ids; }
  };
}

/* ── maths: strokes → a small PNG for the server ── */
/** the strokes whose points lie mostly inside the lasso polygon */
export function strokesInLasso(strokes, lasso) {
  const L = (lasso || []).map(p => Array.isArray(p) ? {x: p[0], y: p[1]} : p);
  if (L.length < 3) return [];
  const inside = p => { let c = false; for (let i = 0, j = L.length - 1; i < L.length; j = i++) { const a = L[i], b = L[j]; if ((a.y > p.y) !== (b.y > p.y) && p.x < (b.x - a.x) * (p.y - a.y) / (b.y - a.y) + a.x) c = !c; } return c; };
  return strokes.filter(s => { const pts = s.points || s; const k = pts.filter(inside).length; return pts.length && k / pts.length >= 0.6; });
}
/** a drawn poly of the scene (the pen's strokes) as a stroke */
export const polyToStroke = o => ({id: o.id, points: (o.pts || []).map(([x, y], i) => ({x, y, t: i * 8, pressure: 0.5}))});
export const mathRequestBody = (image, hint) => ({image, ...(hint ? {hint: String(hint).slice(0, 200)} : {})});

const CRC_TABLE = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
const crc32 = (buf, start = 0, end = buf.length) => { let c = 0xffffffff; for (let i = start; i < end; i++) c = CRC_TABLE[(c ^ buf[i]) & 0xff] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
/** a 1-bit greyscale PNG (black ink on white) of a bitmap (Uint8Array, 1 = ink), stored deflate: no compressor needed */
export function encodePNG1(bits, w, h) {
  const row = Math.ceil(w / 8) + 1, raw = new Uint8Array(row * h);
  for (let y = 0; y < h; y++) { raw[y * row] = 0; for (let x = 0; x < w; x++) if (!bits[y * w + x]) raw[y * row + 1 + (x >> 3)] |= 0x80 >> (x & 7); }
  /* zlib: header, stored blocks of ≤ 65535 bytes, adler32 */
  const blocks = Math.max(1, Math.ceil(raw.length / 65535)), z = new Uint8Array(2 + raw.length + blocks * 5 + 4);
  z[0] = 0x78; z[1] = 0x01; let o = 2;
  for (let b = 0; b < blocks; b++) {
    const s = b * 65535, n = Math.min(65535, raw.length - s);
    z[o++] = b === blocks - 1 ? 1 : 0; z[o++] = n & 255; z[o++] = n >> 8; z[o++] = ~n & 255; z[o++] = (~n >> 8) & 255;
    z.set(raw.subarray(s, s + n), o); o += n;
  }
  let a = 1, bb = 0; for (let i = 0; i < raw.length; i++) { a = (a + raw[i]) % 65521; bb = (bb + a) % 65521; }
  z[o++] = bb >> 8; z[o++] = bb & 255; z[o++] = a >> 8; z[o++] = a & 255;
  const chunk = (type, data) => { const c = new Uint8Array(12 + data.length), dv = new DataView(c.buffer); dv.setUint32(0, data.length); for (let i = 0; i < 4; i++) c[4 + i] = type.charCodeAt(i); c.set(data, 8); dv.setUint32(8 + data.length, crc32(c, 4, 8 + data.length)); return c; };
  const ihdr = new Uint8Array(13), dv = new DataView(ihdr.buffer); dv.setUint32(0, w); dv.setUint32(4, h); ihdr[8] = 1; ihdr[9] = 0;
  const parts = [new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]), chunk('IHDR', ihdr), chunk('IDAT', z.subarray(0, o)), chunk('IEND', new Uint8Array(0))];
  const out = new Uint8Array(parts.reduce((s, p) => s + p.length, 0)); let k = 0; for (const p of parts) { out.set(p, k); k += p.length; }
  return out;
}
const b64 = bytes => { if (typeof Buffer !== 'undefined') return Buffer.from(bytes).toString('base64'); let s = ''; for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000)); return btoa(s); };
/* the strokes in pixels of the picture: trimmed, scaled so the ink fits (and is at most `maxInk` px high), y down */
function layout(strokes, maxSize, pad, maxInk) {
  const all = strokes.flatMap(s => s.points || s), b = bounds(all);
  const w = Math.max(b.w, 1e-9), h = Math.max(b.h, 1e-9), room = maxSize - 2 * pad;
  let s = Math.min(room / w, room / h, maxInk / Math.max(h, w / 6));
  if (!Number.isFinite(s) || s <= 0) s = 1;
  const W = Math.max(8, Math.min(maxSize, Math.ceil(w * s + 2 * pad))), H = Math.max(8, Math.min(maxSize, Math.ceil(h * s + 2 * pad)));
  const map = p => ({x: pad + (p.x - b.x0) * s, y: pad + (b.y1 - p.y) * s, pressure: p.pressure ?? 0.5});
  return {W, H, s, lines: strokes.map(st => (st.points || st).map(map))};
}
/** strokes as a PNG data URL for the maths route: white, black ink, trimmed, at most maxSize px a side and maxBytes
 *  (300 KB). A canvas (OffscreenCanvas, or a <canvas>) draws it smooth when there is one; else (Node, a worker without
 *  OffscreenCanvas) it is drawn here as a 1-bit PNG */
export async function rasteriseStrokes(strokes, {maxSize = 1024, pad = 16, maxInk = 360, line = 3, maxBytes = 300 * 1024, canvas: useCanvas = true} = {}) {
  const list = (strokes || []).filter(s => (s.points || s).length);
  if (!list.length) return null;
  for (let size = maxSize, ink = maxInk; size >= 128; size = Math.floor(size * 0.75), ink = Math.floor(ink * 0.75)) {
    const Lyt = layout(list, size, pad, ink);
    let out = null;
    if (useCanvas) out = await canvasPNG(Lyt, line);
    if (!out) out = bitmapPNG(Lyt, line);
    if (out.bytes <= maxBytes) return {...out, width: Lyt.W, height: Lyt.H};
  }
  return null;
}
async function canvasPNG({W, H, lines}, line) {
  let cv = null;
  try {
    if (typeof OffscreenCanvas !== 'undefined') cv = new OffscreenCanvas(W, H);
    else if (typeof document !== 'undefined' && document.createElement) { cv = document.createElement('canvas'); cv.width = W; cv.height = H; }
  } catch { cv = null; }
  const g = cv?.getContext?.('2d'); if (!g) return null;
  g.fillStyle = '#fff'; g.fillRect(0, 0, W, H); g.strokeStyle = '#000'; g.fillStyle = '#000'; g.lineCap = 'round'; g.lineJoin = 'round';
  for (const pts of lines) {
    if (pts.length === 1) { g.beginPath(); g.arc(pts[0].x, pts[0].y, line / 2, 0, 2 * PI); g.fill(); continue; }
    for (let i = 1; i < pts.length; i++) { g.lineWidth = line * (0.75 + 0.5 * pts[i].pressure); g.beginPath(); g.moveTo(pts[i - 1].x, pts[i - 1].y); g.lineTo(pts[i].x, pts[i].y); g.stroke(); }
  }
  let bytes;
  if (cv.convertToBlob) { const blob = await cv.convertToBlob({type: 'image/png'}); bytes = new Uint8Array(await blob.arrayBuffer()); }
  else { const url = cv.toDataURL('image/png'); const s = atob(url.slice(url.indexOf(',') + 1)); bytes = Uint8Array.from(s, c => c.charCodeAt(0)); }
  return {dataUrl: 'data:image/png;base64,' + b64(bytes), bytes: bytes.length};
}
function bitmapPNG({W, H, lines}, line) {
  const bits = new Uint8Array(W * H), r = Math.max(1, line / 2), r2 = r * r;
  const dot = (cx, cy) => { for (let y = Math.max(0, Math.floor(cy - r)); y <= Math.min(H - 1, Math.ceil(cy + r)); y++) for (let x = Math.max(0, Math.floor(cx - r)); x <= Math.min(W - 1, Math.ceil(cx + r)); x++) if ((x - cx) ** 2 + (y - cy) ** 2 <= r2) bits[y * W + x] = 1; };
  for (const pts of lines) {
    dot(pts[0].x, pts[0].y);
    for (let i = 1; i < pts.length; i++) { const a = pts[i - 1], b = pts[i], n = Math.max(1, Math.ceil(d2(a, b) / 0.7)); for (let k = 1; k <= n; k++) dot(a.x + (b.x - a.x) * k / n, a.y + (b.y - a.y) * k / n); }
  }
  const png = encodePNG1(bits, W, H);
  return {dataUrl: 'data:image/png;base64,' + b64(png), bytes: png.length};
}
