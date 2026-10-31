import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { performance } from 'node:perf_hooks';

const source = await fs.readFile(new URL('../sim/labscan/scanner.js', import.meta.url), 'utf8');
const scanner = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
const polygon = q => [q[0], q[1], q[3], q[2]];
function rotated(degrees = 0, cx = 240, cy = 320, width = 260, height = 368) {
  const angle = degrees * Math.PI / 180, c = Math.cos(angle), s = Math.sin(angle);
  return [[-width / 2, -height / 2], [width / 2, -height / 2], [-width / 2, height / 2], [width / 2, height / 2]]
    .map(([x, y]) => ({ x: cx + x * c - y * s, y: cy + x * s + y * c }));
}
function inside(x, y, quad) {
  let sign = 0; const poly = polygon(quad);
  for (let i = 0; i < 4; i++) {
    const a = poly[i], b = poly[(i + 1) % 4], cross = Math.sign((b.x - a.x) * (y - a.y) - (b.y - a.y) * (x - a.x));
    if (cross && sign && cross !== sign) return false;
    if (cross) sign = cross;
  }
  return true;
}
const inset = (q, factor) => {
  const cx = q.reduce((s, p) => s + p.x, 0) / 4, cy = q.reduce((s, p) => s + p.y, 0) / 4;
  return q.map(p => ({ x: cx + (p.x - cx) * factor, y: cy + (p.y - cy) * factor }));
};
function distance(x, y, a, b) {
  const dx = b.x - a.x, dy = b.y - a.y, t = Math.max(0, Math.min(1, ((x - a.x) * dx + (y - a.y) * dy) / (dx * dx + dy * dy)));
  return Math.hypot(x - a.x - t * dx, y - a.y - t * dy);
}
function photo({ W = 480, H = 640, quad = rotated(), background = 90, paper = 235, shade = 0, inner = false, text = true, pattern } = {}) {
  const gray = new Uint8Array(W * H), innerQuad = quad && inset(quad, .85), textQuad = quad && inset(quad, .70);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    let value = typeof background === 'function' ? background(x, y) : background;
    if (quad && inside(x, y, quad)) {
      value = paper + shade * (x / W - .5);
      if (inner && polygon(innerQuad).some((a, i, points) => distance(x, y, a, points[(i + 1) % 4]) < 2)) value = 25;
      if (text && y % 20 < 2 && x % 11 < 6 && inside(x, y, textQuad)) value = 55;
    }
    if (pattern === 'checker') value = (Math.floor(x / 7) + Math.floor(y / 7)) % 2 ? 225 : 70;
    if (pattern === 'stripes') value = Math.floor(x / 19) % 2 ? 225 : 70;
    gray[y * W + x] = Math.max(0, Math.min(255, Math.round(value)));
  }
  return { gray, W, H, quad };
}
function error(actual, expected) {
  return Math.max(...expected.map(p => Math.min(...actual.map(q => Math.hypot(p.x - q.x, p.y - q.y)))));
}
function findsOuter(fixture, allowance = .028) {
  const result = scanner.findPageQuadGray(fixture.gray, fixture.W, fixture.H);
  assert.ok(result.corners, 'the complete paper should have a supported quadrilateral');
  assert.equal(result.method, 'page');
  const maximum = error(result.corners, fixture.quad);
  assert.ok(maximum < Math.max(fixture.W, fixture.H) * allowance, `outer corner error ${maximum.toFixed(2)} exceeds ${(Math.max(fixture.W, fixture.H) * allowance).toFixed(2)}`);
  assert.ok(result.edgeSupport >= .64); assert.equal(result.clipped, false);
  return result;
}

test('unmarked portrait, landscape and 35/45 degree rotations use four distinct real paper corners', () => {
  for (const quad of [rotated(), rotated(35), rotated(45), rotated(8, 240, 320, 360, 250)]) {
    const result = findsOuter(photo({ quad }));
    assert.equal(new Set(result.corners.map(p => `${p.x},${p.y}`)).size, 4);
    assert.ok(result.score >= .75); assert.equal(result.autoCaptureEligible, true);
  }
});

test('perspective and illumination gradients retain the complete page rather than a bright half', () => {
  findsOuter(photo({ quad: [{ x: 140, y: 70 }, { x: 397, y: 173 }, { x: 50, y: 490 }, { x: 343, y: 567 }], paper: 205, shade: -100 }));
  const crossing = photo({ quad: rotated(6), background: 145, paper: 165, shade: -230 });
  const result = scanner.findPageQuadGray(crossing.gray, crossing.W, crossing.H);
  // Returning a reviewable fallback is safe; a confident crop of one half is not.
  if (result.corners && result.autoCaptureEligible) assert.ok(error(result.corners, crossing.quad) < 20, 'a threshold inside a smooth shadow must not count as a page edge');
  else assert.equal(result.autoCaptureEligible, false);
});

test('paper can be darker than a bright desk and need not intersect any central seed', () => {
  findsOuter(photo({ quad: rotated(-16), background: 235, paper: 170 }));
  findsOuter(photo({ W: 800, H: 600, quad: rotated(-3, 140, 300, 235, 335), background: 120 }));
});

test('a faint outer boundary wins over a strong printed inner frame and dense writing', () => {
  for (const background of [175, 220]) {
    const fixture = photo({ quad: rotated(-7), background, paper: 236, inner: true });
    const result = findsOuter(fixture, .035);
    const outerSpan = Math.hypot(fixture.quad[1].x - fixture.quad[0].x, fixture.quad[1].y - fixture.quad[0].y);
    const actualSpan = Math.hypot(result.corners[1].x - result.corners[0].x, result.corners[1].y - result.corners[0].y);
    assert.ok(actualSpan > outerSpan * .90, 'cropping to the 85% printed border loses real paper margins');
  }
});

test('uniform backgrounds, image-wide gradients, stripes and checkerboard never become an automatic page', () => {
  const options = [
    ...[0, 175, 255].map(background => ({ quad: null, background })),
    { quad: null, background: (x, y) => 80 + x / 480 * 100 + y / 640 * 20 },
    { quad: null, pattern: 'checker' }, { quad: null, pattern: 'stripes' },
  ];
  for (const option of options) {
    const f = photo(option), result = scanner.findPageQuadGray(f.gray, f.W, f.H);
    assert.equal(result.corners, null); assert.equal(result.autoCaptureEligible, false);
  }
});

test('printed frames on a full-frame sheet and solid dark diagrams do not supply outer paper corners', () => {
  const fixtures = [
    photo({ quad: [{ x: -20, y: -20 }, { x: 500, y: -20 }, { x: -20, y: 660 }, { x: 500, y: 660 }], background: 235, paper: 235, inner: true }),
    photo({ background: 235, paper: 20, text: false }),
  ];
  for (const f of fixtures) {
    const result = scanner.findPageQuadGray(f.gray, f.W, f.H);
    assert.equal(result.corners, null); assert.equal(result.autoCaptureEligible, false);
  }
});

test('clipped paper is left for manual review rather than inventing invisible corners', () => {
  const f = photo({ quad: rotated(15, 240, 215, 315, 490) });
  const result = scanner.findPageQuadGray(f.gray, f.W, f.H);
  assert.equal(result.corners, null); assert.equal(result.autoCaptureEligible, false);
});

test('shared detector prefers a real boundary to weak dark blobs and never applies marker insets to partial markers', () => {
  const f = photo();
  for (const [cx, cy] of [[175, 245], [305, 245], [175, 395], [305, 395]]) for (let y = cy - 2; y < cy + 2; y++) for (let x = cx - 2; x < cx + 2; x++) f.gray[y * f.W + x] = 10;
  const result = scanner.detectDocumentQuadGray(f.gray, f.W, f.H);
  assert.equal(result.method, 'page'); assert.ok(error(result.corners, f.quad) < 18);
  const plain = new Uint8Array(480 * 640).fill(235);
  for (const [cx, cy] of [[30, 30], [450, 30], [30, 610]]) for (let y = cy - 5; y <= cy + 5; y++) for (let x = cx - 5; x <= cx + 5; x++) plain[y * 480 + x] = 10;
  const partial = scanner.detectDocumentQuadGray(plain, 480, 640);
  assert.equal(partial.method, 'frame'); assert.equal(partial.autoCaptureEligible, false);
});

test('complete printed marker geometry keeps its marker centres and existing margin-preserving inset contract', () => {
  const f = photo({ text: false }), q = f.quad, inset = scanner.MARKER_INSET;
  const centers = [[inset.left, inset.top], [inset.right, inset.top], [inset.left, inset.bottom], [inset.right, inset.bottom]]
    .map(([u, v]) => ({ x: q[0].x + (q[1].x - q[0].x) * u, y: q[0].y + (q[2].y - q[0].y) * v }));
  for (const p of centers) for (let y = Math.round(p.y) - 4; y <= Math.round(p.y) + 4; y++) for (let x = Math.round(p.x) - 4; x <= Math.round(p.x) + 4; x++) f.gray[y * f.W + x] = 10;
  const result = scanner.detectDocumentQuadGray(f.gray, f.W, f.H);
  assert.equal(result.method, 'marker'); assert.equal(result.autoCaptureEligible, true);
  assert.ok(error(result.corners, centers) < 2); assert.deepEqual(scanner.MARKER_INSET, { left: .045, top: .035, right: .955, bottom: .965 });
});

test('720p work is bounded on detailed positive and noisy negative frames', t => {
  const positive = photo({ W: 1280, H: 720, quad: rotated(5, 640, 360, 365, 515) });
  const negative = photo({ W: 1280, H: 720, quad: null, pattern: 'checker' });
  for (const f of [positive, negative]) for (let i = 0; i < 2; i++) scanner.findPageQuadGray(f.gray, f.W, f.H);
  const times = [];
  for (let i = 0; i < 10; i++) { const f = i % 2 ? negative : positive, start = performance.now(); scanner.findPageQuadGray(f.gray, f.W, f.H); times.push(performance.now() - start); }
  times.sort((a, b) => a - b); t.diagnostic(`720p serial warm median=${times[5].toFixed(1)}ms p95=${times[9].toFixed(1)}ms`);
  assert.ok(times[9] < 3000, 'generous hang budget; shared CI contention is not a phone performance benchmark');
});
