/* The figure editor's ink (draw-ink.mjs) on synthetic hand-drawn strokes (tests/helpers/ink-strokes.cjs): lines snap to
   15° steps and to nearby points, closed shapes come back with their sizes, arrows with their heads, a zigzag is a
   resistor or a spring by its teeth, cells, capacitors, grounds and dashed lines from several strokes, scribbles stay
   freehand; within the time budget; every result is a scene draw-scene.mjs validateScene accepts; the controller's pen,
   palm and finger rules, hold-to-snap and the maths mode; strokes rasterised to a PNG the maths route takes. */
const test = require('node:test'), assert = require('node:assert/strict');
const G = require('./helpers/ink-strokes.cjs');
const load = () => Promise.all([import('../draw-ink.mjs'), import('../draw-scene.mjs')]).then(([I, S]) => ({I, S}));
const O = {unit: G.U};
const near = (a, b, tol, msg) => assert.ok(Math.abs(a - b) <= tol, `${msg}: ${a} vs ${b}`);
const nearP = (p, q, tol, msg) => assert.ok(Math.hypot(p.x - q.x, p.y - q.y) <= tol, `${msg}: (${p.x.toFixed(3)},${p.y.toFixed(3)}) vs (${q.x},${q.y})`);
const angleOf = p => Math.atan2(p.b.y - p.a.y, p.b.x - p.a.x) * 180 / Math.PI;
const kindOf = r => r.type + (r.params.kind ? ':' + r.params.kind : '');
const SEEDS = [1, 2, 3, 4, 5, 6, 7, 8];

/* the synthetic set: name, what it must be read as, the ideal path */
const SET = [
  ...[0, 15, 30, 45, 60, 90, 135, 180, -30, -90, 7, 22].map(d => [`line ${d}°`, ['line'], G.line(0.5, 0.5, 2, d)]),
  ['circle', ['circle'], G.ellipse(2, 2, 0.8, 0.8)], ['small circle', ['circle'], G.ellipse(2, 2, 0.3, 0.3)],
  ['ellipse', ['ellipse'], G.ellipse(2, 2, 1.2, 0.6)], ['turned ellipse', ['ellipse'], G.ellipse(2, 2, 1.2, 0.5, 35)],
  ['rectangle', ['rect'], G.rect(2, 2, 2, 1)], ['square', ['square'], G.rect(2, 2, 1.2, 1.2)], ['turned rectangle', ['rect'], G.rect(2, 2, 2, 1, 30)],
  ['triangle', ['triangle'], G.tri({x: 0, y: 0}, {x: 2, y: 0.2}, {x: 0.8, y: 1.6})], ['right triangle', ['triangle', 'incline'], G.tri({x: 0, y: 0}, {x: 2, y: 0}, {x: 2, y: 1.15})],
  ['arrow, one barb', ['arrow'], G.chain({x: 0, y: 0}, {x: 2, y: 0.5}, {x: 1.75, y: 0.65})],
  ['arrow, two barbs', ['arrow'], G.chain({x: 0, y: 0}, {x: 2, y: 0}, {x: 1.75, y: 0.15}, {x: 2, y: 0}, {x: 1.75, y: -0.15})],
  ['polyline', ['polyline'], G.chain({x: 0, y: 0}, {x: 1.5, y: 0}, {x: 1.5, y: 1.2}, {x: 2.6, y: 1.2})],
  ['arc', ['arc'], G.arc(2, 2, 1, 10, 150)],
  ['resistor', ['zigzag:resistor'], G.zig({x: 0, y: 1}, {x: 2, y: 1}, 6, 0.15)], ['spring', ['zigzag:spring'], G.zig({x: 0, y: 1}, {x: 3, y: 1}, 14, 0.15)],
  ['coil', ['coil:spring'], G.coil({x: 0, y: 1}, {x: 3, y: 1}, 7, 0.2)], ['sine wave', ['wave'], G.sine(0, 1, 4, 0.3, 1.2)],
  ...[3, 5, 9, 11, 17].map(s => [`scribble ${s}`, ['freehand'], G.scribble(s)])
];

test('the synthetic set is read right (≥ 97 %), each stroke well inside the 10 ms budget', async () => {
  const {I} = await load();
  let ok = 0, n = 0;const miss = [], times = [];
  for (const [name, want, path] of SET) for (const seed of SEEDS) {
    const r = I.recognizeStroke(G.hand(path, {seed: seed * 7 + name.length}), O);
    n++; times.push(r.ms);
    if (want.includes(kindOf(r)) || want.includes(r.type)) ok++; else miss.push(`${name}#${seed}: ${kindOf(r)}`);
  }
  times.sort((a, b) => a - b);
  const mean = times.reduce((a, b) => a + b, 0) / times.length;
  console.log(`# ink: ${ok}/${n} read right (${(100 * ok / n).toFixed(1)} %), mean ${mean.toFixed(2)} ms, p95 ${times[Math.floor(times.length * 0.95)].toFixed(2)} ms, max ${times[times.length - 1].toFixed(2)} ms`);
  assert.ok(ok / n >= 0.97, miss.join('; '));
  assert.ok(mean < 10, `mean ${mean} ms`);
  /* with a shakier hand most still read right */
  let shaky = 0;
  for (const [name, want, path] of SET) for (const seed of SEEDS.slice(0, 3)) { const r = I.recognizeStroke(G.hand(path, {seed, wobble: 3, jitter: 1}), O); if (want.includes(kindOf(r)) || want.includes(r.type)) shaky++; }
  assert.ok(shaky / (SET.length * 3) >= 0.9, `shaky ${shaky}/${SET.length * 3}`);
});

test('noisy lines snap to 0/15/30/45/60/90° and keep their start and length; others keep their angle', async () => {
  const {I} = await load();
  for (const d of [0, 15, 30, 45, 60, 75, 90, 120, 150, 180, -45, -90]) for (const off of [-3, 2.5]) {
    const r = I.recognizeStroke(G.hand(G.line(0.5, 0.5, 2, d + off), {seed: d + 100}), O);
    assert.equal(r.type, 'line', `${d}+${off}`);
    const nd = a => { a = ((a % 360) + 360) % 360; return a > 180 ? a - 360 : a; }, want = nd(d);
    assert.equal(nd(r.params.angle), want, `${d}+${off}: snapped to ${r.params.angle}`);
    near(Math.abs(nd(angleOf(r.params) - want)), 0, 1e-6, 'drawn on the snapped angle');
    nearP(r.params.a, {x: 0.5, y: 0.5}, 0.04, 'start');
    near(Math.hypot(r.params.b.x - r.params.a.x, r.params.b.y - r.params.a.y), 2, 0.08, 'length');
  }
  const free = I.recognizeStroke(G.hand(G.line(0.5, 0.5, 2, 22), {seed: 4}), O);
  assert.equal(free.params.angle, null); near(angleOf(free.params), 22, 1.5, 'not snapped');
});

test('a line ends on a point nearby (getCandidates), then the angle snaps from there', async () => {
  const {I} = await load();
  const candidates = [{x: 0.48, y: 0.53, id: 'A'}, {x: 2.53, y: 0.47, id: 'B'}];
  const r = I.recognizeStroke(G.hand(G.line(0.5, 0.5, 2, 1), {seed: 9}), {...O, candidates});
  assert.equal(r.type, 'line');
  assert.deepEqual([r.params.snapA, r.params.snapB], ['A', 'B']);
  nearP(r.params.a, candidates[0], 1e-9, 'on A'); nearP(r.params.b, candidates[1], 1e-9, 'on B');
  const one = I.recognizeStroke(G.hand(G.line(0.5, 0.5, 2, 1), {seed: 9}), {...O, candidates: [candidates[0]]});
  nearP(one.params.a, candidates[0], 1e-9, 'start on A'); assert.equal(one.params.angle, 0);
});

test('circles, ellipses, rectangles and triangles come back with their sizes', async () => {
  const {I} = await load();
  for (const seed of SEEDS.slice(0, 4)) {
    const c = I.recognizeStroke(G.hand(G.ellipse(2, 1.5, 0.8, 0.8), {seed}), O);
    assert.equal(c.type, 'circle'); nearP({x: c.params.cx, y: c.params.cy}, {x: 2, y: 1.5}, 0.05, 'circle centre'); near(c.params.r, 0.8, 0.05, 'radius');
    assert.ok(c.alternatives.some(a => a.type === 'ellipse') && c.alternatives.at(-1).type === 'freehand', 'alternatives: the ellipse, then freehand');
    const e = I.recognizeStroke(G.hand(G.ellipse(2, 1.5, 1.2, 0.6), {seed}), O);
    assert.equal(e.type, 'ellipse'); near(e.params.rx, 1.2, 0.07, 'rx'); near(e.params.ry, 0.6, 0.06, 'ry'); assert.equal(e.params.rot, 0);
    const et = I.recognizeStroke(G.hand(G.ellipse(2, 1.5, 1.2, 0.5, 35), {seed}), O);
    near(et.params.rot, 35, 4, 'turned ellipse');
    const rc = I.recognizeStroke(G.hand(G.rect(2, 2, 2, 1), {seed}), O);
    assert.equal(rc.type, 'rect'); near(rc.params.w, 2, 0.06, 'w'); near(rc.params.h, 1, 0.06, 'h'); assert.equal(rc.params.rot, 0); nearP({x: rc.params.cx, y: rc.params.cy}, {x: 2, y: 2}, 0.05, 'centre');
    const rr = I.recognizeStroke(G.hand(G.rect(2, 2, 2, 1, 30), {seed}), O);
    assert.equal(rr.type, 'rect'); assert.equal(rr.params.rot, 30, 'snapped turn'); near(rr.params.w, 2, 0.08, 'turned w');
    const sq = I.recognizeStroke(G.hand(G.rect(2, 2, 1.2, 1.2), {seed}), O);
    assert.equal(sq.type, 'square'); assert.equal(sq.params.w, sq.params.h); assert.ok(sq.alternatives.some(a => a.type === 'rect'));
    const t = I.recognizeStroke(G.hand(G.tri({x: 0, y: 0}, {x: 2, y: 0.2}, {x: 0.8, y: 1.6}), {seed}), O);
    assert.equal(t.type, 'triangle'); assert.equal(t.params.pts.length, 3);
    for (const v of [{x: 0, y: 0}, {x: 2, y: 0.2}, {x: 0.8, y: 1.6}]) assert.ok(t.params.pts.some(p => Math.hypot(p.x - v.x, p.y - v.y) < 0.1), 'vertex ' + JSON.stringify(v));
  }
});

test('a right triangle on a level base is offered as an incline with its angle, rising either way', async () => {
  const {I} = await load();
  const r = I.recognizeStroke(G.hand(G.tri({x: 0, y: 0}, {x: 2, y: 0}, {x: 2, y: 1.15}), {seed: 3}), O);
  const inc = r.type === 'incline' ? r : r.alternatives.find(a => a.type === 'incline');
  assert.ok(inc, 'an incline candidate'); assert.equal(inc.params.angle, 30); assert.equal(inc.params.flip, false);
  near(inc.params.x, 0, 0.06, 'foot'); near(inc.params.y, 0, 0.05, 'base'); near(inc.params.length, Math.hypot(2, 1.15), 0.1, 'slope length');
  assert.ok(r.params.right || r.type === 'incline');
  const left = I.recognizeStroke(G.hand(G.tri({x: 2, y: 0}, {x: 0, y: 0}, {x: 0, y: 2}), {seed: 5}), O);
  const li = left.type === 'incline' ? left : left.alternatives.find(a => a.type === 'incline');
  assert.equal(li.params.angle, 45); assert.equal(li.params.flip, true); near(li.params.x, 0, 0.06, 'left end of the base');
});

test('arrows: a head drawn on in one stroke, at either end; a head drawn as separate strokes', async () => {
  const {I} = await load();
  const one = I.recognizeStroke(G.hand(G.chain({x: 0, y: 0}, {x: 2, y: 0}, {x: 1.75, y: 0.15}, {x: 2, y: 0}, {x: 1.75, y: -0.15}), {seed: 2}), O);
  assert.equal(one.type, 'arrow'); nearP(one.params.b, {x: 2, y: 0}, 0.06, 'tip'); assert.equal(one.params.angle, 0);
  /* the head first, then the shaft back: the arrow points where the stroke began */
  const rev = I.recognizeStroke(G.hand(G.chain({x: 1.75, y: 0.2}, {x: 2, y: 0}, {x: 0, y: 0}), {seed: 4}), O);
  assert.equal(rev.type, 'arrow'); nearP(rev.params.b, {x: 2, y: 0}, 0.06, 'tip at the start');
  let t = 0; const it = path => { const s = G.hand(path, {seed: ++t, t0: t * 400}); return {stroke: s, result: I.recognizeStroke(s, O)}; };
  const v = I.recognizeGroup([it(G.seg({x: 0, y: 0}, {x: 2, y: 0})), it(G.chain({x: 1.75, y: 0.18}, {x: 2, y: 0}, {x: 1.75, y: -0.18}))], O);
  assert.equal(v.type, 'arrow'); assert.equal(v.strokes, 2); nearP(v.params.b, {x: 2, y: 0}, 0.06, 'V head');
  const two = I.recognizeGroup([it(G.seg({x: 0, y: 0}, {x: 0, y: 2})), it(G.seg({x: 0, y: 0}, {x: 0.15, y: 0.25})), it(G.seg({x: 0, y: 0}, {x: -0.15, y: 0.25}))], O);
  assert.equal(two.type, 'arrow'); assert.equal(two.strokes, 3); nearP(two.params.b, {x: 0, y: 0}, 0.06, 'pointing down to the start'); assert.equal(two.params.angle, -90);
  assert.equal(I.recognizeGroup([it(G.seg({x: 0, y: 0}, {x: 2, y: 0})), it(G.seg({x: 0, y: 1}, {x: 2, y: 1.5}))], O), null, 'two lines are two lines');
});

test('a few teeth are a resistor, many a spring; a coil is a spring (or an inductor); a round wave is a sine', async () => {
  const {I} = await load();
  for (const seed of SEEDS.slice(0, 4)) {
    const r = I.recognizeStroke(G.hand(G.zig({x: 0, y: 1}, {x: 2, y: 1}, 6, 0.15), {seed}), O);
    assert.equal(kindOf(r), 'zigzag:resistor'); assert.ok(r.alternatives.some(a => kindOf(a) === 'zigzag:spring'), 'the spring as the other choice');
    const s = I.recognizeStroke(G.hand(G.zig({x: 0, y: 1}, {x: 3, y: 1}, 14, 0.15), {seed}), O);
    assert.equal(kindOf(s), 'zigzag:spring'); near(s.params.n, 14, 2, 'teeth');
    const c = I.recognizeStroke(G.hand(G.coil({x: 0, y: 1}, {x: 3, y: 1}, 7, 0.2), {seed}), O);
    assert.equal(kindOf(c), 'coil:spring'); near(c.params.n, 7, 1, 'loops'); assert.ok(c.alternatives.some(a => kindOf(a) === 'coil:inductor'));
    const w = I.recognizeStroke(G.hand(G.sine(0, 1, 4, 0.3, 1.2), {seed}), O);
    assert.equal(w.type, 'wave'); near(w.params.lambda, 1.2, 0.08, 'wavelength'); near(w.params.A, 0.3, 0.05, 'amplitude'); near(w.params.angle, 0, 2, 'level');
  }
});

test('several strokes: two bars are a cell (long bar +) or a capacitor, three shrinking bars a ground, dashes a dashed line', async () => {
  const {I} = await load();
  let t = 0; const it = path => { const s = G.hand(path, {seed: ++t, t0: t * 400}); return {stroke: s, result: I.recognizeStroke(s, O)}; };
  const cell = I.recognizeGroup([it(G.seg({x: 1, y: 0.5}, {x: 1, y: 1.5})), it(G.seg({x: 1.25, y: 0.8}, {x: 1.25, y: 1.2}))], O);
  assert.equal(cell.type, 'cell'); assert.ok(cell.params.b.x < cell.params.a.x, 'the + end (x2) is on the long bar side');
  assert.equal(cell.alternatives[0].type, 'capacitor');
  const cap = I.recognizeGroup([it(G.seg({x: 1, y: 0.5}, {x: 1, y: 1.5})), it(G.seg({x: 1.25, y: 0.52}, {x: 1.25, y: 1.48}))], O);
  assert.equal(cap.type, 'capacitor'); near(Math.abs(cap.params.a.y - cap.params.b.y), 0, 0.08, 'across the bars');
  const leads = I.recognizeGroup([it(G.seg({x: 0, y: 1}, {x: 1, y: 1})), it(G.seg({x: 1, y: 0.5}, {x: 1, y: 1.5})), it(G.seg({x: 1.25, y: 0.8}, {x: 1.25, y: 1.2})), it(G.seg({x: 1.25, y: 1}, {x: 2.3, y: 1}))], O);
  assert.equal(leads.type, 'cell'); assert.equal(leads.strokes, 4); near(Math.min(leads.params.a.x, leads.params.b.x), 0, 0.06, 'from the lead ends'); near(Math.max(leads.params.a.x, leads.params.b.x), 2.3, 0.06, 'to the lead ends');
  const gnd = I.recognizeGroup([it(G.seg({x: 1, y: 1.5}, {x: 1, y: 1})), it(G.seg({x: 0.6, y: 1}, {x: 1.4, y: 1})), it(G.seg({x: 0.75, y: 0.85}, {x: 1.25, y: 0.85})), it(G.seg({x: 0.9, y: 0.7}, {x: 1.1, y: 0.7}))], O);
  assert.equal(gnd.type, 'ground'); nearP(gnd.params, {x: 1, y: 1.5}, 0.06, 'the top of its lead');
  const dashes = [0, 1, 2, 3, 4].map(i => it(G.seg({x: i * 0.5, y: 1}, {x: i * 0.5 + 0.3, y: 1.02})));
  const d = I.recognizeGroup(dashes, O);
  assert.equal(d.type, 'dashed'); assert.equal(d.strokes, 5); assert.equal(d.params.angle, 0); near(d.params.b.x - d.params.a.x, 2.3, 0.08, 'from the first dash to the last');
  assert.equal(I.recognizeGroup(dashes.slice(0, 2), O), null, 'two dashes are not yet a dashed line');
});

test('scribbles and handwriting stay freehand, smoothed, with the shapes offered as alternatives', async () => {
  const {I} = await load();
  for (const s of [3, 5, 9, 11, 17, 23]) {
    const r = I.recognizeStroke(G.hand(G.scribble(s), {seed: s}), O);
    assert.equal(r.type, 'freehand', `scribble ${s}: ${kindOf(r)}`);
    assert.ok(r.params.pts.length >= 2 && r.params.pts.length <= 400);
  }
  const tiny = I.recognizeStroke({points: [{x: 1, y: 1, t: 0}, {x: 1.01, y: 1.005, t: 10}]}, O);
  assert.equal(tiny.type, 'dot');
});

test('smoothing: the one-euro filter takes out jitter, Catmull–Rom passes through its points, widths follow pressure', async () => {
  const {I} = await load();
  const st = G.hand(G.line(0, 0, 3, 0), {seed: 1, wobble: 0, jitter: 3});
  const dev = pts => Math.sqrt(pts.reduce((s, p) => s + p.y * p.y, 0) / pts.length);
  assert.ok(dev(I.oneEuro(st.points, O)) < 0.75 * dev(st.points), `less jitter: ${dev(I.oneEuro(st.points, O))} vs ${dev(st.points)}`);
  const ctrl = [{x: 0, y: 0}, {x: 1, y: 1}, {x: 2, y: 0}, {x: 3, y: 1}], cr = I.catmullRom(ctrl, {samples: 5});
  for (const p of ctrl) assert.ok(cr.some(q => Math.hypot(q.x - p.x, q.y - p.y) < 1e-9));
  const w = I.pressureWidths(st.points.map((p, i) => ({...p, pressure: i < st.points.length / 2 ? 0.2 : 0.9})), {base: 2, unit: G.U});
  assert.ok(w[Math.floor(w.length * 0.75)] > w[Math.floor(w.length * 0.25)] * 1.4, 'harder is wider');
  assert.equal(I.strokeOutline(st.points, w).length, st.points.length * 2);
  assert.ok(I.strokeLw(st.points) >= 0.4 && I.strokeLw(st.points) <= 2.5);
});

test('toSceneObjects: every result becomes objects that validateScene accepts as they are', async () => {
  const {I, S} = await load();
  const existing = [{...S.defaults('floor'), id: 'f1', x: 0, y: 0, w: 6}, {...S.defaults('block'), id: 'm1', x: 3.2, y: 1, w: 0.4, h: 0.4}, {...S.defaults('wall'), id: 'w1', x: 0, y: 0, h: 2}];
  const strokes = SET.filter(([n]) => !/scribble/.test(n)).map(([, , path], i) => G.hand(path, {seed: i + 1}));
  let t = 0; const it = path => { const s = G.hand(path, {seed: ++t, t0: t * 400}); return {stroke: s, result: I.recognizeStroke(s, O)}; };
  const groups = [
    I.recognizeGroup([it(G.seg({x: 1, y: 0.5}, {x: 1, y: 1.5})), it(G.seg({x: 1.25, y: 0.8}, {x: 1.25, y: 1.2}))], O),
    I.recognizeGroup([it(G.seg({x: 1, y: 0.5}, {x: 1, y: 1.5})), it(G.seg({x: 1.25, y: 0.52}, {x: 1.25, y: 1.48}))], O),
    I.recognizeGroup([it(G.seg({x: 0.6, y: 1}, {x: 1.4, y: 1})), it(G.seg({x: 0.75, y: 0.85}, {x: 1.25, y: 0.85})), it(G.seg({x: 0.9, y: 0.7}, {x: 1.1, y: 0.7}))], O),
    I.recognizeGroup([0, 1, 2, 3].map(i => it(G.seg({x: i * 0.5, y: 1}, {x: i * 0.5 + 0.3, y: 1}))), O)];
  const inc = I.recognizeStroke(G.hand(G.tri({x: 0, y: 0}, {x: 2, y: 0}, {x: 2, y: 1.15}), {seed: 3}), O);
  const results = [...strokes.map(s => I.recognizeStroke(s, O)), ...groups, inc, ...inc.alternatives, ...strokes.slice(0, 8).flatMap(s => I.recognizeStroke(s, O).alternatives)];
  const types = new Set();
  let objects = [...existing];
  for (const r of results) {
    const objs = I.toSceneObjects(r, {existing: objects, grid: 0.1, unit: G.U, look: {color: 'blue', lw: 1.2}});
    assert.ok(objs.length >= 1, 'something for ' + r.type);
    for (const o of objs) types.add(o.type);
    const v = S.validateScene({objects: [...objects, ...objs]});
    assert.ok(v.ok, r.type + ': ' + JSON.stringify(v.errors));
    objects = [...objects, ...objs].slice(-100);
  }
  for (const t of ['line', 'rect', 'ellipse', 'poly', 'arc', 'element', 'ground', 'wave', 'incline']) assert.ok(types.has(t), 'made ' + t);
  /* a spring drawn from the wall to the block joins them; drawn in the air it stays a drawn zigzag */
  const sp = I.recognizeStroke(G.hand(G.zig({x: 0.02, y: 1}, {x: 3.0, y: 1}, 14, 0.12), {seed: 3}), O);
  const joined = I.toSceneObjects(sp, {existing, unit: G.U});
  assert.equal(joined[0].type, 'spring'); assert.deepEqual([joined[0].a, joined[0].b].sort(), ['m1', 'w1']);
  assert.ok(S.validateScene({objects: [...existing, ...joined]}).ok);
  assert.equal(I.toSceneObjects(sp, {existing: [], unit: G.U})[0].type, 'poly');
  /* a resistor's ends on the grid, level, and on an element's end nearby */
  const R = I.recognizeStroke(G.hand(G.zig({x: 0.03, y: 1.02}, {x: 2.04, y: 0.99}, 6, 0.15), {seed: 2}), O);
  const el = I.toSceneObjects(R, {existing: [{...S.defaults('element'), id: 'W1', kind: 'wire', x1: -1, y1: 1, x2: 0, y2: 1}], unit: G.U, grid: 0.5})[0];
  assert.deepEqual([el.type, el.kind, el.x1, el.y1, el.x2, el.y2, el.label], ['element', 'resistor', 0, 1, 2, 1, 'R']);
  /* ids are free in the scene */
  const ln = I.toSceneObjects({type: 'line', params: {a: {x: 0, y: 0}, b: {x: 1, y: 0}}}, {existing: [{id: 'n1', type: 'line'}]});
  assert.equal(ln[0].id, 'n2'); assert.equal(ln[0].pattern, 'solid');
});

/* the controller with fake timers and pointer events */
function rig(I, options = {}) {
  let t = 1000; const timers = new Map(); let tid = 0;
  const T = {now: () => t, set: (f, ms) => { timers.set(++tid, {f, at: t + ms}); return tid; }, clear: id => timers.delete(id)};
  const advance = ms => { const end = t + ms; for (;;) { const due = [...timers.entries()].filter(([, x]) => x.at <= end).sort((a, b) => a[1].at - b[1].at)[0]; if (!due) break; t = due[1].at; timers.delete(due[0]); due[1].f(); } t = end; };
  const log = {shapes: [], free: [], previews: [], math: []}; let nid = 0;
  const c = I.createInkController({timers: T, unit: G.U, toWorld: e => ({x: e.wx, y: e.wy}), options,
    onShape: (r, ctx) => { const ids = ['s' + (++nid)]; log.shapes.push({r, ctx, ids}); return ids; },
    onFreehand: (r, ctx) => { const ids = ['f' + (++nid)]; log.free.push({r, ctx, ids}); return ids; },
    onPreview: r => log.previews.push(r), onMathRegion: m => log.math.push(m)});
  const ev = (p, type = 'pen', id = 1, extra = {}) => ({pointerId: id, pointerType: type, button: 0, clientX: p.x / G.U, clientY: -p.y / G.U, wx: p.x, wy: p.y, pressure: p.pressure ?? 0.5, ...extra});
  const draw = (path, {type = 'pen', id = 1, seed = 1, hold = 0} = {}) => {
    const s = G.hand(path, {seed}).points;
    const down = c.pointerdown(ev(s[0], type, id));
    for (const p of s.slice(1)) { advance(8); c.pointermove(ev(p, type, id)); }
    if (hold) advance(hold);
    advance(8); c.pointerup(ev(s[s.length - 1], type, id)); advance(200);
    return down;
  };
  return {c, log, draw, ev, advance};
}

test('the controller: a pen draws and is cleaned up; with a pen in use touches are the palm; a finger only when allowed', async () => {
  const {I} = await load();
  const {c, log, draw} = rig(I);
  assert.equal(draw(G.ellipse(2, 2, 0.8, 0.8)), true);
  assert.equal(log.shapes[0].r.type, 'circle');
  assert.equal(draw(G.line(0, 0, 2, 0), {type: 'touch', id: 5}), false, 'a palm after the pen');
  assert.equal(log.shapes.length, 1);
  const f = rig(I, {fingerDraw: true});
  assert.equal(f.draw(G.line(0, 0, 2, 1), {type: 'touch', id: 3}), true, 'a finger with 손가락으로 그리기');
  assert.equal(f.log.shapes[0].r.type, 'line');
  const off = rig(I);
  assert.equal(off.draw(G.line(0, 0, 2, 1), {type: 'touch'}), false, 'no finger drawing unless asked');
  /* a big contact is a palm even when fingers may draw */
  assert.equal(f.c.pointerdown(f.ev({x: 0, y: 0}, 'touch', 9, {width: 60, height: 60})), false);
  /* auto-shape off: freehand, smoothed */
  const fr = rig(I, {autoShape: false, holdToSnap: false});
  fr.draw(G.ellipse(2, 2, 0.8, 0.8));
  assert.equal(fr.log.shapes.length, 0); assert.equal(fr.log.free[0].r.type, 'freehand');
  c.mode = 'off'; assert.equal(draw(G.line(0, 0, 2, 0)), false);
});

test('hold to snap: a pause at the end shows the shape, which follows the pen until it is lifted', async () => {
  const {I} = await load();
  const {c, log, ev, advance} = rig(I, {autoShape: false});
  const s = G.hand(G.line(0, 0, 2, 45), {seed: 2}).points;
  c.pointerdown(ev(s[0])); for (const p of s.slice(1)) { advance(8); c.pointermove(ev(p)); }
  assert.equal(log.previews.length, 0);
  advance(520);
  assert.equal(log.previews.at(-1).type, 'line'); assert.equal(log.previews.at(-1).params.angle, 45);
  /* dragging on: the end follows, still on 15° steps */
  advance(8); c.pointermove(ev({x: 2.5, y: 0.05})); assert.equal(log.previews.at(-1).params.angle, 0);
  advance(8); c.pointerup(ev({x: 2.5, y: 0.05}));
  assert.equal(log.shapes.length, 1); assert.equal(log.shapes[0].r.params.angle, 0); assert.equal(log.previews.at(-1), null);
});

test('the controller groups strokes: the dashes inserted one by one are replaced by one dashed line', async () => {
  const {I} = await load();
  const {log, draw} = rig(I);
  for (let i = 0; i < 4; i++) draw(G.seg({x: i * 0.5, y: 1}, {x: i * 0.5 + 0.3, y: 1}), {seed: i + 1});
  const [d1, d2, d3, d4] = log.shapes;
  assert.deepEqual([d1.r.type, d2.r.type, d3.r.type, d4.r.type], ['line', 'line', 'dashed', 'dashed']);
  assert.deepEqual(d3.ctx.replaces, [...d1.ids, ...d2.ids], 'the third dash replaces the two lines');
  assert.deepEqual(d4.ctx.replaces, d3.ids, 'the fourth replaces the dashed line it grows');
  assert.ok(d4.ctx.group); near(d4.r.params.b.x - d4.r.params.a.x, 1.8, 0.08, 'all four dashes');
  /* a cell from two bars */
  const b = rig(I);
  b.draw(G.seg({x: 1, y: 0.5}, {x: 1, y: 1.5})); b.draw(G.seg({x: 1.25, y: 0.8}, {x: 1.25, y: 1.2}), {seed: 2});
  assert.equal(b.log.shapes.at(-1).r.type, 'cell'); assert.deepEqual(b.log.shapes.at(-1).ctx.replaces, b.log.shapes[0].ids);
});

test('수식 쓰기: strokes are collected, then handed over as a region; rasterised to a PNG the maths route takes', async () => {
  const {I} = await load();
  const {c, log, draw, advance} = rig(I, {mathIdleMs: 1500});
  c.mode = 'math';
  draw(G.line(0, 0, 0.3, 90)); draw(G.chain({x: 0.2, y: 0.15}, {x: 0.5, y: 0.15}), {seed: 3});
  assert.equal(log.shapes.length, 0); assert.equal(c.mathStrokes.length, 2);
  advance(1600);
  assert.equal(log.math.length, 1); assert.equal(log.math[0].strokes.length, 2); assert.equal(c.mathStrokes.length, 0);
  const png = await I.rasteriseStrokes(log.math[0].strokes);
  assert.match(png.dataUrl, /^data:image\/png;base64,[A-Za-z0-9+/]+=*$/);
  const bytes = Buffer.from(png.dataUrl.split(',')[1], 'base64');
  assert.deepEqual([...bytes.subarray(0, 8)], [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  const w = bytes.readUInt32BE(16), h = bytes.readUInt32BE(20);
  assert.ok(w <= 1024 && h <= 1024 && w === png.width && h === png.height); assert.ok(bytes.length <= 300 * 1024 && png.bytes === bytes.length);
  /* a long line of writing still fits */
  const long = Array.from({length: 40}, (_, i) => G.hand(G.ellipse(i * 0.4, 0, 0.15, 0.2), {seed: i}));
  const big = await I.rasteriseStrokes(long);
  assert.ok(big.width <= 1024 && big.bytes <= 300 * 1024);
  /* lasso: the strokes inside */
  const inside = I.strokesInLasso(long, [[-0.5, -0.5], [2, -0.5], [2, 0.5], [-0.5, 0.5]]);
  assert.ok(inside.length >= 4 && inside.length <= 6, String(inside.length));
  assert.deepEqual(I.mathRequestBody('data:x', 'v = ...'), {image: 'data:x', hint: 'v = ...'});
});

test('the build stamps draw-ink.mjs and its import; the deploy runs this test', () => {
  const fs = require('node:fs'), path = require('node:path');
  const build = fs.readFileSync(path.join(__dirname, '../tools/build-site-catalogue.cjs'), 'utf8');
  assert.match(build, /draw-ink\.mjs/);
  assert.match(fs.readFileSync(path.join(__dirname, '../.github/workflows/deploy-worker.yml'), 'utf8'), /test-draw-ink\.cjs/);
  assert.doesNotMatch(fs.readFileSync(path.join(__dirname, '../draw-ink.mjs'), 'utf8'), /\b(document|window)\.(?!createElement)/, 'no DOM in the core');
});

/* ── pen and finger never confused (createPointerArbiter): sequences of pointer events → what each one does ── */
test('arbiter: mouse is the tool; before any pen a finger is the tool, a second finger cancels it into a pinch',async()=>{
  const {I}=await load();let t=0;const A=I.createPointerArbiter({now:()=>t});
  assert.deepEqual(A.down({pointerType:'mouse',pointerId:1,button:0,clientX:0,clientY:0}),{route:'tool'});assert.equal(A.move({pointerType:'mouse',pointerId:1}).route,'tool');A.up({pointerType:'mouse',pointerId:1});
  assert.equal(A.mode,'finger');
  assert.deepEqual(A.down({pointerType:'touch',pointerId:5,clientX:100,clientY:100}),{route:'tool'});
  assert.equal(A.move({pointerType:'touch',pointerId:5,clientX:120,clientY:100}).route,'tool');
  assert.deepEqual(A.down({pointerType:'touch',pointerId:6,clientX:200,clientY:100}),{route:'nav',cancel:'tool'},'the second finger: the stroke goes, a pinch starts');
  assert.equal(A.move({pointerType:'touch',pointerId:5,clientX:130,clientY:100}).route,'nav');assert.equal(A.points().length,2);
});
test('arbiter: once a pen is seen fingers only navigate; two- and three-finger taps undo and redo; 손가락으로 그리기 turns finger drawing back on',async()=>{
  const {I}=await load();let t=0;const A=I.createPointerArbiter({now:()=>t});
  assert.deepEqual(A.down({pointerType:'pen',pointerId:2,button:0,buttons:1,pressure:0.4,clientX:50,clientY:50}),{route:'tool'});
  assert.equal(A.move({pointerType:'pen',pointerId:2,clientX:60,clientY:50}).route,'tool');
  t=10;assert.equal(A.up({pointerType:'pen',pointerId:2}).route,'tool');assert.equal(A.mode,'pen');
  t=2000;assert.deepEqual(A.down({pointerType:'touch',pointerId:7,clientX:400,clientY:400}),{route:'nav'},'one finger pans');
  assert.equal(A.move({pointerType:'touch',pointerId:7,clientX:450,clientY:400}).route,'nav');A.up({pointerType:'touch',pointerId:7,type:'pointerup'});
  t=3000;A.down({pointerType:'touch',pointerId:8,clientX:400,clientY:400});A.down({pointerType:'touch',pointerId:9,clientX:480,clientY:400});
  t=3100;A.up({pointerType:'touch',pointerId:8,type:'pointerup'});assert.deepEqual(A.up({pointerType:'touch',pointerId:9,type:'pointerup'}),{route:'nav',tap:'undo'});
  t=4000;for(const id of [10,11,12])A.down({pointerType:'touch',pointerId:id,clientX:300+id*40,clientY:400});
  t=4100;A.up({pointerType:'touch',pointerId:10,type:'pointerup'});A.up({pointerType:'touch',pointerId:11,type:'pointerup'});assert.equal(A.up({pointerType:'touch',pointerId:12,type:'pointerup'}).tap,'redo');
  /* a moved two-finger gesture is a pinch, not a tap */
  t=5000;A.down({pointerType:'touch',pointerId:13,clientX:400,clientY:400});A.down({pointerType:'touch',pointerId:14,clientX:480,clientY:400});A.move({pointerType:'touch',pointerId:14,clientX:560,clientY:400});
  A.up({pointerType:'touch',pointerId:13,type:'pointerup'});assert.equal(A.up({pointerType:'touch',pointerId:14,type:'pointerup'}).tap,undefined);
  A.fingerMode='draw';assert.equal(A.mode,'finger');t=6000;assert.equal(A.down({pointerType:'touch',pointerId:15,clientX:10,clientY:10}).route,'tool');
});
test('arbiter: palm rejection — while the pen is down, 500 ms after it lifts, a large contact, near a hovering pen; a pen that starts during a finger gesture wins',async()=>{
  const {I}=await load();let t=0;const A=I.createPointerArbiter({now:()=>t});
  A.down({pointerType:'pen',pointerId:2,button:0,clientX:300,clientY:300});
  assert.equal(A.down({pointerType:'touch',pointerId:3,clientX:350,clientY:420}).route,'ignore','palm while the pen writes');
  assert.equal(A.move({pointerType:'touch',pointerId:3,clientX:360,clientY:430}).route,'ignore');assert.equal(A.up({pointerType:'touch',pointerId:3}).route,'ignore');
  t=100;A.up({pointerType:'pen',pointerId:2});t=400;assert.equal(A.down({pointerType:'touch',pointerId:4,clientX:350,clientY:420}).route,'ignore','within 500 ms');
  t=1200;assert.equal(A.down({pointerType:'touch',pointerId:5,clientX:100,clientY:100,width:48,height:60}).route,'ignore','a large contact');
  t=2000;A.hover({pointerType:'pen',pointerId:2,clientX:300,clientY:300,buttons:0,pressure:0});t=2100;
  assert.equal(A.down({pointerType:'touch',pointerId:6,clientX:380,clientY:420}).route,'ignore','near a hovering pen');
  t=3000;assert.equal(A.down({pointerType:'touch',pointerId:7,clientX:900,clientY:100}).route,'nav','an ordinary finger later: navigation');
  assert.deepEqual(A.down({pointerType:'pen',pointerId:2,button:0,clientX:300,clientY:300}),{route:'tool',cancel:'nav'},'the pen wins');
  assert.equal(A.move({pointerType:'touch',pointerId:7,clientX:950,clientY:100}).route,'ignore','the cancelled finger is done');
  /* in finger mode, a pen during a finger stroke cancels the stroke */
  const B=I.createPointerArbiter({now:()=>t,fingerMode:'draw'});B.down({pointerType:'touch',pointerId:1,clientX:0,clientY:0});
  assert.deepEqual(B.down({pointerType:'pen',pointerId:2,button:0}),{route:'tool',cancel:'tool'});
});
test('pen buttons: S Pen side / barrel button and the eraser end erase; the ink controller does not draw with them; tilt and pressure kept',async()=>{
  const {I}=await load();
  assert.equal(I.penButton({pointerType:'pen',button:2,buttons:2}),'barrel');assert.equal(I.penButton({pointerType:'pen',button:0,buttons:3}),'barrel');
  assert.equal(I.penButton({pointerType:'pen',button:5,buttons:32}),'eraser');assert.equal(I.penButton({pointerType:'pen',button:0,buttons:1}),null);assert.equal(I.penButton({pointerType:'mouse',button:2}),null);
  const A=I.createPointerArbiter();assert.equal(A.down({pointerType:'pen',pointerId:1,button:5,buttons:32}).route,'erase');
  const C=I.createInkController({toWorld:e=>({x:e.clientX/100,y:-e.clientY/100}),unit:0.01,options:{arbitrated:true}});
  assert.equal(C.pointerdown({pointerType:'pen',pointerId:1,button:2,buttons:2,clientX:0,clientY:0}),false);
  assert.equal(C.pointerdown({pointerType:'pen',pointerId:1,button:0,buttons:1,pressure:0.7,tiltX:30,tiltY:-10,clientX:0,clientY:0}),true);
  const p=C.current.points[0];assert.equal(p.pressure,0.7);assert.equal(p.tiltX,30);
  /* coalesced samples (Chrome / Samsung Internet on Android, Windows Ink) are all taken */
  C.pointermove({pointerType:'pen',pointerId:1,clientX:30,clientY:0,getCoalescedEvents:()=>[10,20,30].map(x=>({pointerType:'pen',pointerId:1,clientX:x,clientY:0,pressure:0.6}))});
  assert.equal(C.current.points.length,4);
});
