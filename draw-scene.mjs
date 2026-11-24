/* The scene of the Workshop's figure and simulation editor (#/workshop/draw, draw.html). One plain JSON object is both
   the exam figure and the system the simulation runs, so a figure a teacher draws can be played and a photo read by
   the AI (community/src/workshop-scene.js) can be checked against the same rules. This file is shared: the browser
   imports it (draw.js, draw-render.mjs, draw-physics.mjs) and so does the community Worker. No DOM, no network.

   Scene, version 2 (lengths in metres of the figure's world, masses in kg, forces in N, angles in degrees, y up):
     {format:'haslalab-scene', version:2, title:'', g:9.8, grid:0.1, style:'textbook', view:{x,y,w,h}, objects:[…]}
   style is the figure style ("그림체", draw-render.mjs STYLES): textbook | university | olympiad | jee | print.
   Version 1 (mechanics only, no style) is still read: it is migrated by migrateScene() (a line's dash:true|false
   becomes pattern:'dashed'|'solid'; style 'textbook'). view is the part of the world the figure shows (optional; the
   editor fits one). At most MAX_OBJECTS objects, each with an id (a letter, then letters, digits, _ or -, up to 24)
   unique in the scene and one of the types below. Every text field is a label: $…$ is maths, and outside $ a short
   label like m_1, \vec{F}, \hat{x}, \dot{x}, \frac{a}{b}, \sqrt{2gh}, \mathrm{kg}, \theta, \hbar, \ket{\psi} is
   maths too (draw-render.mjs texLayout lists the commands).

   mechanics (simulated by draw-physics.mjs buildSim)
       block    x,y (centre, when free) w,h mass label  on at  vx,vy showV vLabel
       ball     x,y r mass label  on at  vx,vy showV vLabel trail
                on: '' (free or hanging) or the id of a floor or an incline the body rests on; then at is the distance
                along that surface from its start to the body's foot, and x,y follow from it. vx,vy is the velocity at
                t = 0 (for a body on a surface, its part along the surface counts).
       floor    x,y (left end of the top) w mu hatch        a horizontal surface, friction coefficient mu
       ceiling  x,y (left end of the underside) w hatch
       wall     x,y (bottom) h side ('left': solid to the left of x, 'right': to the right)
       incline  x,y (left end of the base) angle length (of the slope) mu flip angleLabel
       pulley   x,y r mount ('' or a ceiling, incline, floor or wall it is fixed to)   fixed, massless, frictionless
       pivot    x,y
       string   a b over:[pulley ids] mode label   rod  a (pivot) b (body) mode label
       spring   a b k L0 coils label               force on (body) F angle len label
   electromagnetism
       element  x1,y1 → x2,y2 kind value r closed look route label     a two-terminal circuit element on the wire grid.
                kind: wire resistor battery cell dc ac capacitor inductor switch diode led bulb ammeter voltmeter
                galvanometer. value: Ω (resistor, bulb, galvanometer), V (emf of battery/cell/dc, amplitude of ac,
                forward drop of diode/led), μF (capacitor), H (inductor). r: internal resistance of a source (Ω).
                The (x2,y2) end is the + terminal of a source and the cathode of a diode or LED (it conducts from
                x1 to x2). closed: a switch.
                look: a resistor drawn 'zigzag' or as an IEC 'box' (auto: the style's). route: a wire 'straight',
                'hv' (horizontal first) or 'vh' (vertical first). Terminals that coincide (within 1/100 of the grid
                or 0.01) are one node, and an end lying on a wire joins it (draw-physics.mjs solveCircuit).
       ground   x,y label
       charge   x,y q (μC) r label  mass (mg) vx,vy showV vLabel trail    a point charge; with trail its path through
                the uniform field regions is drawn (Lorentz force, other charges ignored)
       plate    x1,y1 → x2,y2 q (μC, total) label marks                    a charged plate (a line of charge)
       fieldlines n levels equip arrows      the field lines of all charges and plates (and equipotentials)
       field    x,y (lower left) w,h kind ('B'|'E') dir ('in' ⊗ | 'out' ⊙ | 'arrow') angle mag (T or V/m) spacing
                pattern (border) label                                     a uniform field region
       cwire    x1,y1 → x2,y2 I label arrow    a current-carrying wire in the page
       current  x,y r dir ('out'|'in') I rings label   a wire through the page, with rings of B around it
       solenoid x,y (lower left) w,h turns core showB label       loop x,y r ccw tilt label
       magnet   x,y (lower left) w,h flip showB
   thermodynamics
       cylinder x,y (lower left) w,h piston (height of the piston, 0–1) gas weight heat ('none'|'in'|'out') label
       reservoir x,y w,h hot label        engine x,y (centre) size kind ('engine'|'fridge') th tc qh qc wl
       graph    x,y (lower left of the plot, world) w,h xmin xmax ymin ymax auto xlabel ylabel ticks grid origin
                a plot frame. auto: the ranges fit what is plotted on it (from 0).
       curve    graph kind x1 x2 y1 y2 gamma expr heads pattern label       a curve on a graph, in its data units.
                kind func: y = expr(x) for x from x1 to x2 (expr: + − * / ^, sin cos tan exp ln log sqrt abs …, pi, e).
                isotherm (P = y1·x1/V), adiabat (P V^γ = y1 x1^γ), isobar (P = y1): from V = x1 to x2;
                isochore: V = x1 from P = y1 to y2. heads: none | mid | end arrows along it.
       cycle    graph kind ('carnot'|'otto'|'stirling') v1 v2 t1 (hot) t2 (cold) gamma labels arrows shade
                an ideal-gas cycle with nR = 1 (P = T / V); see draw-physics.mjs gasCycle
   optics (thin elements are vertical; the optical axis is the line y of each element)
       lens     x,y (centre on the axis) h f (m; > 0 converging, < 0 diverging) showF label
       mirror   x,y h f (0 plane, > 0 concave, < 0 convex) face ('left'|'right': the side light comes from) showF label
       prism    x,y (middle of the base) size (base) apex (°) n label       slab x,y (lower left) w,h n label
       oarrow   x (on the axis) y (the axis) h (signed) label rays image imageLabel   an object for ray diagrams
       ray      x,y angle len arrow label          a ray traced through lenses, mirrors, prisms and slabs
       slits    x,y (centre) n d (mm) a (mm) L (m) lambda (nm) h screen (figure distance) pattern labels waves
       wavefront x,y kind ('plane'|'circular') n spacing angle h
   waves
       wave     x,y (start) len A lambda phase kind ('travel'|'standing') n ends ('none'|'fixed') showLambda showA
                envelope axis arrow label         standing: λ = 2 len / n
   modern physics
       well     x,y (lower left) w,h kind ('infinite'|'finite'|'harmonic'|'barrier'|'step') L (nm) V0 (eV; ħω for
                harmonic) mass (electron masses) levels psi ('none'|'psi'|'prob') E (eV, barrier/step) labels
       levels   x,y w,h kind ('hydrogen'|'custom') n values (eV, comma list) trans ("3-2,2-1") labels showLambda
       phototube x,y w,h label          a photoelectric setup
       spacetime x,y (origin) size units beta primed cone grid hyperbola xlabel ylabel   a Minkowski diagram
       worldline diagram (a spacetime) x0 (units) beta ticks tau label
       frames   x,y size gap label        frames S and S′ with the velocity of S′
   general marks (drawn only)
       label    x,y text size box          dim x1,y1,x2,y2 offset text      arc x,y r from to text arrow
       axes     x,y lx ly xlabel ylabel    line x1,y1,x2,y2 pattern heads   vector x1,y1,x2,y2 label width head
       region   x,y w,h shape fill pattern label                            point x,y label filled
   validateScene() checks every field (type, range, references) and returns the normalised version-2 scene. */

export const SCENE_FORMAT = 'haslalab-scene', SCENE_VERSION = 2, MAX_OBJECTS = 120;
export const BODY_TYPES = ['block', 'ball'];
export const SURFACE_TYPES = ['floor', 'incline'];
export const ANCHOR_TYPES = ['pivot', 'ceiling', 'wall', 'floor'];
export const MARK_TYPES = ['label', 'dim', 'arc', 'axes', 'line', 'vector', 'region', 'point'];
export const STYLE_KEYS = ['textbook', 'university', 'olympiad', 'jee', 'print'];
export const ELEMENT_KINDS = ['wire', 'resistor', 'battery', 'cell', 'dc', 'ac', 'capacitor', 'inductor', 'switch', 'diode', 'led', 'bulb', 'ammeter', 'voltmeter', 'galvanometer'];
export const PATTERNS = ['solid', 'dashed', 'dotted', 'dashdot', 'none'];
const ID = /^[A-Za-z][A-Za-z0-9_-]{0,23}$/;
const COORD = 200, SPEED = 300, DATA = 1e7;

/* field kinds: [kind, default, min, max] for numbers; texts carry their length */
const num = (d, min, max) => ({k: 'num', d, min, max});
const txt = (d, max) => ({k: 'txt', d, max});
const bool = d => ({k: 'bool', d});
const ref = (types, d = '') => ({k: 'ref', d, types});
const pick = (d, list) => ({k: 'enum', d, list});
const expr = d => ({k: 'expr', d, max: 120});
const X = num(0, -COORD, COORD), Y = num(0, -COORD, COORD), X1 = X, Y1 = Y, X2 = num(1, -COORD, COORD), Y2 = Y;
const SEG = {x1: X1, y1: Y1, x2: X2, y2: Y2};
const MOTION = {vx: num(0, -SPEED, SPEED), vy: num(0, -SPEED, SPEED), showV: bool(false), vLabel: txt('v_0', 24)};
const BOX = (w, h) => ({x: X, y: Y, w: num(w, 0.05, 400), h: num(h, 0.05, 400)});
const L = (d = '') => txt(d, 40);
export const FIELDS = {
  /* mechanics */
  block: {x: X, y: Y, w: num(0.4, 0.02, 20), h: num(0.3, 0.02, 20), mass: num(1, 0.001, 10000), label: L(), on: ref(SURFACE_TYPES), at: num(0, -COORD, COORD), ...MOTION},
  ball: {x: X, y: Y, r: num(0.1, 0.01, 5), mass: num(1, 0.001, 10000), label: L(), on: ref(SURFACE_TYPES), at: num(0, -COORD, COORD), ...MOTION, trail: bool(false)},
  floor: {x: X, y: Y, w: num(3, 0.05, 400), mu: num(0, 0, 2), hatch: bool(true)},
  ceiling: {x: X, y: Y, w: num(2, 0.05, 400), hatch: bool(true)},
  wall: {x: X, y: Y, h: num(1, 0.05, 400), side: pick('left', ['left', 'right'])},
  incline: {x: X, y: Y, angle: num(30, 1, 89), length: num(2, 0.1, 200), mu: num(0, 0, 2), flip: bool(false), angleLabel: txt('', 24)},
  pulley: {x: X, y: Y, r: num(0.1, 0.01, 2), mount: ref(['ceiling', 'incline', 'floor', 'wall'])},
  pivot: {x: X, y: Y},
  string: {a: ref([...BODY_TYPES, 'pivot']), b: ref([...BODY_TYPES, 'pivot']), over: {k: 'refs', d: [], types: ['pulley'], max: 6}, mode: pick('normal', ['normal', 'conical']), label: txt('', 24)},
  rod: {a: ref(['pivot']), b: ref(BODY_TYPES), mode: pick('normal', ['normal', 'conical']), label: txt('', 24)},
  spring: {a: ref([...BODY_TYPES, ...ANCHOR_TYPES]), b: ref([...BODY_TYPES, ...ANCHOR_TYPES]), k: num(50, 0.01, 1e6), L0: num(1, 0.01, 100), coils: num(10, 3, 30), label: txt('', 24)},
  force: {on: ref(BODY_TYPES), F: num(10, 0, 1e6), angle: num(0, -360, 360), len: num(0.6, 0.05, 20), label: txt('F', 24)},
  /* electromagnetism */
  element: {...SEG, kind: pick('resistor', ELEMENT_KINDS), value: num(10, 0, 1e9), r: num(0, 0, 1e6), closed: bool(true), look: pick('auto', ['auto', 'zigzag', 'box']), route: pick('straight', ['straight', 'hv', 'vh']), label: L()},
  ground: {x: X, y: Y, label: L()},
  charge: {x: X, y: Y, q: num(1, -1e4, 1e4), r: num(0.12, 0.02, 5), label: L(), mass: num(1, 1e-6, 1e6), ...MOTION, trail: bool(false)},
  plate: {...SEG, q: num(10, -1e5, 1e5), label: L(), marks: bool(true)},
  fieldlines: {n: num(8, 2, 32), levels: num(6, 0, 16), equip: bool(false), arrows: bool(true)},
  field: {...BOX(2, 1.5), kind: pick('B', ['B', 'E']), dir: pick('in', ['in', 'out', 'arrow']), angle: num(0, -360, 360), mag: num(1, 0, 1e9), spacing: num(0.3, 0.05, 20), pattern: pick('dashed', PATTERNS), label: L()},
  cwire: {...SEG, I: num(1, -1e6, 1e6), label: L('I'), arrow: bool(true)},
  current: {x: X, y: Y, r: num(0.08, 0.02, 2), dir: pick('out', ['out', 'in']), I: num(1, -1e6, 1e6), rings: num(0, 0, 6), label: L('I')},
  solenoid: {...BOX(2.4, 0.8), turns: num(8, 2, 40), core: bool(false), showB: bool(false), label: L()},
  loop: {x: X, y: Y, r: num(0.5, 0.05, 50), ccw: bool(true), tilt: num(0.35, 0.05, 1), label: L('I')},
  magnet: {...BOX(1.6, 0.4), flip: bool(false), showB: bool(false)},
  /* thermodynamics */
  cylinder: {...BOX(1.2, 1.8), piston: num(0.6, 0.1, 0.95), gas: bool(true), weight: bool(false), heat: pick('none', ['none', 'in', 'out']), label: L()},
  reservoir: {...BOX(2, 0.5), hot: bool(true), label: L('T')},
  engine: {x: X, y: Y, size: num(1, 0.2, 40), kind: pick('engine', ['engine', 'fridge']), th: txt('T_H', 24), tc: txt('T_C', 24), qh: txt('Q_H', 24), qc: txt('Q_C', 24), wl: txt('W', 24)},
  graph: {...BOX(3, 2.2), xmin: num(0, -DATA, DATA), xmax: num(1, -DATA, DATA), ymin: num(0, -DATA, DATA), ymax: num(1, -DATA, DATA), auto: bool(true), xlabel: txt('x', 24), ylabel: txt('y', 24), ticks: bool(false), grid: bool(false), origin: txt('O', 8)},
  curve: {graph: ref(['graph']), kind: pick('func', ['func', 'isotherm', 'adiabat', 'isobar', 'isochore']), x1: num(0, -DATA, DATA), x2: num(1, -DATA, DATA), y1: num(1, -DATA, DATA), y2: num(0.5, -DATA, DATA), gamma: num(1.4, 1.01, 3), expr: expr('sin(x)'), heads: pick('none', ['none', 'mid', 'end']), pattern: pick('solid', PATTERNS), label: L()},
  cycle: {graph: ref(['graph']), kind: pick('carnot', ['carnot', 'otto', 'stirling']), v1: num(1, 1e-6, DATA), v2: num(2, 1e-6, DATA), t1: num(600, 1e-6, DATA), t2: num(400, 1e-6, DATA), gamma: num(1.4, 1.01, 3), labels: bool(true), arrows: bool(true), shade: bool(false)},
  /* optics */
  lens: {x: X, y: Y, h: num(1.4, 0.05, 100), f: num(1, -1000, 1000), showF: bool(true), label: L()},
  mirror: {x: X, y: Y, h: num(1.6, 0.05, 100), f: num(1, -1000, 1000), face: pick('left', ['left', 'right']), showF: bool(true), label: L()},
  prism: {x: X, y: Y, size: num(1.6, 0.05, 100), apex: num(60, 10, 150), n: num(1.5, 1, 4), label: L()},
  slab: {...BOX(2, 0.8), n: num(1.5, 1, 4), label: L()},
  oarrow: {x: X, y: Y, h: num(0.5, -100, 100), label: L('O'), rays: bool(true), image: bool(true), imageLabel: txt("I", 24)},
  ray: {x: X, y: Y, angle: num(0, -360, 360), len: num(8, 0.1, 400), arrow: bool(true), label: L()},
  slits: {x: X, y: Y, n: num(2, 1, 50), d: num(0.25, 1e-4, 100), a: num(0.05, 1e-4, 100), L: num(1, 1e-3, 1000), lambda: num(550, 10, 1e5), h: num(1.6, 0.1, 100), screen: num(2.4, 0.2, 200), pattern: bool(true), labels: bool(true), waves: bool(true)},
  wavefront: {x: X, y: Y, kind: pick('circular', ['plane', 'circular']), n: num(5, 1, 30), spacing: num(0.3, 0.02, 50), angle: num(0, -360, 360), h: num(1.4, 0.05, 200)},
  /* waves */
  wave: {x: X, y: Y, len: num(4, 0.1, 400), A: num(0.4, 0, 50), lambda: num(1.6, 0.02, 400), phase: num(0, -360, 360), kind: pick('travel', ['travel', 'standing']), n: num(3, 1, 20), ends: pick('none', ['none', 'fixed']),
    showLambda: bool(true), showA: bool(true), envelope: bool(true), axis: bool(true), arrow: bool(false), label: L()},
  /* modern physics */
  well: {...BOX(4, 3), kind: pick('infinite', ['infinite', 'finite', 'harmonic', 'barrier', 'step']), L: num(1, 1e-3, 1e4), V0: num(5, 0, 1e6), mass: num(1, 1e-3, 1e6), levels: num(3, 0, 8), psi: pick('psi', ['none', 'psi', 'prob']), E: num(2, 0, 1e6), labels: bool(true)},
  levels: {...BOX(2.6, 3), kind: pick('hydrogen', ['hydrogen', 'custom']), n: num(5, 2, 10), values: txt('-13.6,-3.4,-1.51,-0.85', 160), trans: txt('3-2,2-1', 80), labels: bool(true), showLambda: bool(true)},
  phototube: {...BOX(3, 2), label: L()},
  spacetime: {x: X, y: Y, size: num(3, 0.2, 400), units: num(4, 1, 20), beta: num(0.5, -0.99, 0.99), primed: bool(true), cone: bool(true), grid: bool(false), hyperbola: bool(false), xlabel: txt('x', 24), ylabel: txt('$ct$', 24)},
  worldline: {diagram: ref(['spacetime']), x0: num(0, -100, 100), beta: num(0.5, -0.99, 0.99), ticks: bool(true), tau: num(1, 0.05, 50), label: L()},
  frames: {x: X, y: Y, size: num(1.2, 0.1, 100), gap: num(1.8, 0, 200), label: L('v')},
  /* general marks */
  label: {x: X, y: Y, text: txt('', 80), size: num(16, 8, 48), box: bool(false)},
  dim: {x1: X, y1: Y, x2: X, y2: Y, offset: num(0.15, -10, 10), text: txt('', 40)},
  arc: {x: X, y: Y, r: num(0.3, 0.02, 20), from: num(0, -360, 360), to: num(30, -360, 360), text: txt('', 24), arrow: bool(false)},
  axes: {x: X, y: Y, lx: num(1, 0, 100), ly: num(1, 0, 100), xlabel: txt('x', 12), ylabel: txt('y', 12)},
  line: {x1: X, y1: Y, x2: X, y2: Y, pattern: pick('dashed', PATTERNS), heads: pick('none', ['none', 'end', 'start', 'both', 'mid'])},
  vector: {...SEG, label: L(), width: num(1.6, 0.3, 6), head: pick('auto', ['auto', 'filled', 'open', 'stealth', 'none'])},
  region: {...BOX(1, 0.8), shape: pick('rect', ['rect', 'ellipse']), fill: pick('gray', ['none', 'gray', 'hatch', 'dots']), pattern: pick('solid', PATTERNS), label: L()},
  point: {x: X, y: Y, label: L(), filled: bool(true)}
};
export const TYPES = Object.keys(FIELDS);
/* the palette's domains (draw.js tabs); every type is in one */
export const DOMAINS = {
  mech: ['block', 'ball', 'floor', 'ceiling', 'wall', 'incline', 'pulley', 'pivot', 'string', 'rod', 'spring', 'force'],
  em: ['element', 'ground', 'charge', 'plate', 'fieldlines', 'field', 'cwire', 'current', 'solenoid', 'loop', 'magnet'],
  thermo: ['cylinder', 'reservoir', 'engine', 'cycle', 'curve'],
  optics: ['lens', 'mirror', 'prism', 'slab', 'oarrow', 'ray', 'slits', 'wavefront'],
  waves: ['wave'],
  modern: ['well', 'levels', 'phototube', 'spacetime', 'worldline', 'frames'],
  general: ['label', 'dim', 'arc', 'axes', 'line', 'vector', 'region', 'point', 'graph']
};
export const TYPE_DOMAIN = Object.fromEntries(Object.entries(DOMAINS).flatMap(([d, list]) => list.map(t => [t, d])));
/* references that must name an existing object, and which must not be the same */
const REQUIRED_REFS = {string: ['a', 'b'], rod: ['a', 'b'], spring: ['a', 'b'], force: ['on'], curve: ['graph'], cycle: ['graph'], worldline: ['diagram']};
export const isBody = o => !!o && BODY_TYPES.includes(o.type);
export const isSeg = o => !!o && 'x1' in (FIELDS[o.type] || {});

/* ── a small, safe expression language for plotted functions: numbers, x, pi, e, + − * / ^, implicit products (2x,
   3sin(x)), and the functions below. Compiled to closures; nothing is ever evaluated as code. ── */
const FN = {sin: Math.sin, cos: Math.cos, tan: Math.tan, asin: Math.asin, acos: Math.acos, atan: Math.atan, sinh: Math.sinh, cosh: Math.cosh, tanh: Math.tanh,
  exp: Math.exp, ln: Math.log, log: Math.log10, sqrt: Math.sqrt, abs: Math.abs, sign: Math.sign, floor: Math.floor, ceil: Math.ceil, sec: x => 1 / Math.cos(x), csc: x => 1 / Math.sin(x), cot: x => 1 / Math.tan(x)};
export function compileExpr(src, vars = ['x']) {
  const s = String(src ?? '').replace(/π/g, 'pi').replace(/·|×/g, '*').replace(/−/g, '-').trim();
  if (!s || s.length > 120) return null;
  const toks = [], re = /\s*(?:(\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)|([A-Za-z]+)|(\*\*|[-+*/^(),]))/y;
  let m, k = 0;
  while (k < s.length) { re.lastIndex = k; m = re.exec(s); if (!m) return null; k = re.lastIndex; toks.push(m[1] !== undefined ? {n: +m[1]} : m[2] !== undefined ? {id: m[2]} : {op: m[3] === '**' ? '^' : m[3]}); if (/^\s*$/.test(s.slice(k))) break; }
  let i = 0, depth = 0;
  const peek = () => toks[i], op = c => toks[i] && toks[i].op === c;
  const fail = () => { throw new Error('expr'); };
  const exprP = () => { let a = term(); while (op('+') || op('-')) { const o = toks[i++].op, b = term(), A = a; a = o === '+' ? x => A(x) + b(x) : x => A(x) - b(x); } return a; };
  const startsAtom = t => t && (t.n !== undefined || t.id !== undefined || t.op === '(');
  const term = () => { let a = unary(); for (;;) { if (op('*') || op('/')) { const o = toks[i++].op, b = unary(), A = a; a = o === '*' ? x => A(x) * b(x) : x => A(x) / b(x); } else if (startsAtom(peek())) { const b = power(), A = a; a = x => A(x) * b(x); } else return a; } };
  const unary = () => { if (op('-')) { i++; const a = unary(); return x => -a(x); } if (op('+')) { i++; return unary(); } return power(); };
  const power = () => { const a = atom(); if (op('^')) { i++; const b = unary(); return x => Math.pow(a(x), b(x)); } return a; };
  const atom = () => {
    if (++depth > 40) fail();
    const t = toks[i++]; let r;
    if (!t) fail();
    if (t.n !== undefined) r = () => t.n;
    else if (t.op === '(') { const a = exprP(); if (!op(')')) fail(); i++; r = a; }
    else if (t.id !== undefined) {
      const id = t.id;
      if (FN[id]) { let a; if (op('(')) { i++; a = exprP(); if (!op(')')) fail(); i++; } else a = power(); const f = FN[id]; r = x => f(a(x)); }
      else if (id === 'pi') r = () => Math.PI;
      else if (id === 'e') r = () => Math.E;
      else if (vars.includes(id)) { const j = vars.indexOf(id); r = x => (Array.isArray(x) ? x[j] : x); }
      else fail();
    } else fail();
    depth--; return r;
  };
  try { const f = exprP(); if (i !== toks.length) return null; return f; } catch (e) { return null; }
}

/* text: no control characters, the length cut; for text the AI wrote, only what a physics label needs */
const AI_TEXT = /^[A-Za-z0-9 _^{}\\.,=+\-()/'°%·×|:!θμαβγδεζηικλνξπρστυφχψωΓΔΘΛΞΠΣΦΨΩϑϕϵϱςħℏÅ⊙⊗⊥∥∠△→⇒↔⇌ℰℒℋ∇∂∫∮∑√∞±∓≈≠≤≥∝∼≡⟨⟩′″가-힣ㄱ-ㅎ]*$/u;
function cleanText(v, max, ai) {
  let s = String(v).normalize('NFC').replace(/[\u0000-\u001f\u007f-\u009f\u2028\u2029]/g, ' ').replace(/\s+/g, ' ').trim();
  if (s.length > max) s = s.slice(0, max).trim();
  if (ai && (s.length > 40 || !AI_TEXT.test(s))) return null;
  return s;
}

/** A version-1 scene (or one with no version) as version 2, without checking it: a line's dash becomes its pattern. */
export function migrateScene(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) return input;
  const v1 = input.version === 1;
  if (!v1 && input.version !== undefined) return input;
  const out = {...input, version: SCENE_VERSION};
  if (Array.isArray(input.objects)) out.objects = input.objects.map(o => {
    if (!o || typeof o !== 'object' || o.type !== 'line' || o.pattern !== undefined) return o;
    const {dash, ...rest} = o; return {...rest, pattern: (dash === undefined ? v1 : dash === true) ? 'dashed' : 'solid', ...(typeof dash !== 'boolean' && dash !== undefined ? {dash} : {})};
  });
  return out;
}

/** Validate and normalise a scene. strict (default): every problem is an error. lenient: an object with a problem is
 *  dropped (and whatever refers to it), a number out of range is brought into range; each is reported. aiText: labels
 *  must look like physics labels (used for scenes the vision model wrote). Version 1 is migrated first.
 *  Returns {ok, scene, errors, notes}. */
export function validateScene(input0, {lenient = false, aiText = false} = {}) {
  const errors = [], notes = [];
  const err = (code, id, field) => { errors.push({code, ...(id ? {id} : {}), ...(field ? {field} : {})}); };
  if (!input0 || typeof input0 !== 'object' || Array.isArray(input0)) return {ok: false, scene: blankScene(), errors: [{code: 'not_object'}], notes};
  if (input0.format !== undefined && input0.format !== SCENE_FORMAT) err('bad_format');
  if (input0.version !== undefined && input0.version !== 1 && input0.version !== SCENE_VERSION) err('bad_version');
  const input = migrateScene(input0);
  if (input0.version === 1) notes.push({code: 'migrated', from: 1});
  const top = (k, d, min, max) => {
    const v = input[k];
    if (v === undefined || v === null) return d;
    if (typeof v !== 'number' || !Number.isFinite(v)) { err('bad_number', null, k); return d; }
    if (v < min || v > max) { if (lenient) { notes.push({code: 'clamped', field: k}); return Math.min(max, Math.max(min, v)); } err('out_of_range', null, k); return d; }
    return v;
  };
  const scene = {format: SCENE_FORMAT, version: SCENE_VERSION, title: '', g: top('g', 9.8, 0.1, 30), grid: top('grid', 0.1, 0.01, 1), style: 'textbook', objects: []};
  if (input.style !== undefined) { if (STYLE_KEYS.includes(input.style)) scene.style = input.style; else if (lenient) notes.push({code: 'style_dropped'}); else err('bad_enum', null, 'style'); }
  if (input.title !== undefined) { const t = typeof input.title === 'string' ? cleanText(input.title, 80, aiText) : null; if (t == null) err('bad_text', null, 'title'); else scene.title = t; }
  if (input.view !== undefined && input.view !== null) {
    const v = input.view, ok = v && typeof v === 'object' && ['x', 'y', 'w', 'h'].every(k => typeof v[k] === 'number' && Number.isFinite(v[k]))
      && Math.abs(v.x) <= COORD * 2 && Math.abs(v.y) <= COORD * 2 && v.w >= 0.1 && v.w <= 800 && v.h >= 0.1 && v.h <= 800;
    if (ok) scene.view = {x: v.x, y: v.y, w: v.w, h: v.h}; else if (!lenient) err('bad_view');
  }
  const list = Array.isArray(input.objects) ? input.objects : (err('no_objects'), []);
  if (list.length > MAX_OBJECTS) { if (lenient) notes.push({code: 'too_many'}); else err('too_many'); }
  const seen = new Set(), objs = [];
  for (const raw of list.slice(0, lenient ? MAX_OBJECTS : list.length)) {
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) { err('not_object'); continue; }
    const id = raw.id, type = raw.type;
    if (typeof id !== 'string' || !ID.test(id)) { err('bad_id', typeof id === 'string' ? id.slice(0, 24) : null); continue; }
    if (seen.has(id)) { err('dup_id', id); continue; }
    if (!Object.prototype.hasOwnProperty.call(FIELDS, type)) { err('bad_type', id); continue; }
    seen.add(id);
    const o = {id, type}, F = FIELDS[type];
    let bad = false;
    for (const [k, f] of Object.entries(F)) {
      const v = raw[k];
      if (v === undefined || v === null) { o[k] = Array.isArray(f.d) ? [] : f.d; continue; }
      if (f.k === 'num') {
        if (typeof v !== 'number' || !Number.isFinite(v)) { err('bad_number', id, k); bad = true; continue; }
        if (v < f.min || v > f.max) {
          if (lenient) { o[k] = Math.min(f.max, Math.max(f.min, v)); notes.push({code: 'clamped', id, field: k}); continue; }
          err('out_of_range', id, k); bad = true; continue;
        }
        o[k] = v;
      } else if (f.k === 'txt') {
        const t = typeof v === 'string' ? cleanText(v, f.max, aiText) : null;
        if (t == null) { if (lenient) { o[k] = ''; notes.push({code: 'text_dropped', id, field: k}); continue; } err('bad_text', id, k); bad = true; continue; }
        o[k] = t;
      } else if (f.k === 'expr') {
        const t = typeof v === 'string' ? cleanText(v, f.max, false) : null;
        if (t == null || !compileExpr(t)) { if (lenient) { o[k] = f.d; notes.push({code: 'expr_dropped', id, field: k}); continue; } err('bad_expr', id, k); bad = true; continue; }
        o[k] = t;
      } else if (f.k === 'bool') {
        if (typeof v !== 'boolean') { err('bad_bool', id, k); bad = true; continue; }
        o[k] = v;
      } else if (f.k === 'enum') {
        if (!f.list.includes(v)) { if (lenient && k !== 'kind') { o[k] = f.d; notes.push({code: 'enum_dropped', id, field: k}); continue; } err('bad_enum', id, k); bad = true; continue; }
        o[k] = v;
      } else if (f.k === 'ref') {
        if (typeof v !== 'string' || (v && !ID.test(v))) { err('bad_ref', id, k); bad = true; continue; }
        o[k] = v;
      } else if (f.k === 'refs') {
        if (!Array.isArray(v) || v.length > f.max || v.some(x => typeof x !== 'string' || !ID.test(x)) || new Set(v).size !== v.length) { err('bad_ref', id, k); bad = true; continue; }
        o[k] = [...v];
      }
    }
    /* checks across fields */
    if (!bad && (type === 'lens') && Math.abs(o.f) < 0.01) { if (lenient) { o.f = o.f < 0 ? -0.01 : 0.01; notes.push({code: 'clamped', id, field: 'f'}); } else { err('out_of_range', id, 'f'); bad = true; } }
    if (!bad && (type === 'mirror') && o.f !== 0 && Math.abs(o.f) < 0.01) { if (lenient) { o.f = 0; notes.push({code: 'clamped', id, field: 'f'}); } else { err('out_of_range', id, 'f'); bad = true; } }
    if (!bad && (type === 'element' || type === 'plate' || type === 'cwire' || type === 'vector') && Math.hypot(o.x2 - o.x1, o.y2 - o.y1) < 1e-6) { err('zero_length', id); bad = true; }
    if (!bad && type === 'graph' && !o.auto && (o.xmax <= o.xmin || o.ymax <= o.ymin)) { if (lenient) { o.auto = true; notes.push({code: 'clamped', id, field: 'xmax'}); } else { err('out_of_range', id, 'xmax'); bad = true; } }
    if (bad && lenient) continue;
    objs.push(o);
  }
  /* references: to objects that exist and are of the right type; a dropped object takes what refers to it along */
  let keep = objs;
  for (let pass = 0; pass < 4; pass++) {
    const byId = new Map(keep.map(o => [o.id, o])), next = [];
    for (const o of keep) {
      let bad = false;
      for (const [k, f] of Object.entries(FIELDS[o.type])) {
        if (f.k === 'ref') {
          const need = (REQUIRED_REFS[o.type] || []).includes(k);
          if (!o[k]) { if (need) { err('missing_ref', o.id, k); bad = true; } continue; }
          const t = byId.get(o[k]);
          if (!t || !f.types.includes(t.type)) { if (lenient && !need) { o[k] = ''; notes.push({code: 'ref_dropped', id: o.id, field: k}); continue; } err('bad_ref', o.id, k); bad = true; }
        } else if (f.k === 'refs') {
          if (o[k].some(x => !byId.has(x) || !f.types.includes(byId.get(x).type))) { err('bad_ref', o.id, k); bad = true; }
        }
      }
      if ((o.type === 'string' || o.type === 'spring') && o.a && o.a === o.b) { err('same_ends', o.id); bad = true; }
      if (o.type === 'string' && !bad && !isBody(byId.get(o.a)) && !isBody(byId.get(o.b))) { err('no_body', o.id); bad = true; }
      if (o.type === 'spring' && !bad && !isBody(byId.get(o.a)) && !isBody(byId.get(o.b))) { err('no_body', o.id); bad = true; }
      if ((o.type === 'string' || o.type === 'rod') && o.mode === 'conical' && !bad) {
        const ends = [byId.get(o.a), byId.get(o.b)];
        if ((o.over || []).length || !ends.some(e => e?.type === 'pivot') || !ends.some(isBody)) { err('bad_conical', o.id); bad = true; }
      }
      if (bad && lenient) continue;
      next.push(o);
    }
    if (next.length === keep.length) { keep = next; break; }
    keep = next;
  }
  /* a body joined to two strings or rods at once is outside what the editor and the solver handle */
  const byId = new Map(keep.map(o => [o.id, o])), used = new Set();
  keep = keep.filter(o => {
    if (o.type !== 'string' && o.type !== 'rod') return true;
    const ends = [o.a, o.b].filter(e => isBody(byId.get(e)));
    if (ends.some(e => used.has(e))) { err('two_strings', o.id); return !lenient; }
    ends.forEach(e => used.add(e));
    return true;
  });
  scene.objects = keep;
  for (const o of scene.objects) if (isBody(o) && o.on) placeOnSurface(scene, o);
  const dropped = list.length - keep.length;
  if (lenient && dropped > 0) notes.push({code: 'dropped', n: dropped});
  return {ok: lenient ? true : errors.length === 0, scene, errors, notes};
}
export const blankScene = () => ({format: SCENE_FORMAT, version: SCENE_VERSION, title: '', g: 9.8, grid: 0.1, style: 'textbook', objects: []});
/** a new object of a type with every field at its default */
export function defaults(type) {
  const o = {type};
  for (const [k, f] of Object.entries(FIELDS[type] || {})) o[k] = Array.isArray(f.d) ? [] : f.d;
  return o;
}

/* ── geometry shared by the drawing and the solver ── */
const rad = d => d * Math.PI / 180;
export const vec = {
  add: (a, b) => ({x: a.x + b.x, y: a.y + b.y}), sub: (a, b) => ({x: a.x - b.x, y: a.y - b.y}), mul: (a, k) => ({x: a.x * k, y: a.y * k}),
  dot: (a, b) => a.x * b.x + a.y * b.y, cross: (a, b) => a.x * b.y - a.y * b.x, len: a => Math.hypot(a.x, a.y),
  unit: a => { const l = Math.hypot(a.x, a.y); return l > 1e-12 ? {x: a.x / l, y: a.y / l} : {x: 0, y: 0}; },
  perp: a => ({x: -a.y, y: a.x})
};
/** a floor or an incline as a line: start p0, unit direction u along it, unit normal n out of it, and its length */
export function surfaceFrame(s) {
  if (s.type === 'floor') return {p0: {x: s.x, y: s.y}, u: {x: 1, y: 0}, n: {x: 0, y: 1}, length: s.w, mu: s.mu};
  const c = Math.cos(rad(s.angle)), sn = Math.sin(rad(s.angle)), base = s.length * c;
  return s.flip ? {p0: {x: s.x + base, y: s.y}, u: {x: -c, y: sn}, n: {x: sn, y: c}, length: s.length, mu: s.mu}
    : {p0: {x: s.x, y: s.y}, u: {x: c, y: sn}, n: {x: -sn, y: c}, length: s.length, mu: s.mu};
}
/** the incline's three corners: the slope's foot, its top, and the right angle under the top */
export function inclineCorners(s) {
  const f = surfaceFrame(s), top = vec.add(f.p0, vec.mul(f.u, s.length));
  return {foot: f.p0, top, right: {x: top.x, y: s.y}};
}
/* half the body's extent along the surface normal */
export const bodyHalfHeight = b => b.type === 'ball' ? b.r : b.h / 2;
export const bodyHalfWidth = b => b.type === 'ball' ? b.r : b.w / 2;
/** put a body that rests on a surface at its place on it (x, y from `at`) */
export function placeOnSurface(scene, b) {
  const s = scene.objects.find(o => o.id === b.on);
  if (!s) { b.on = ''; return b; }
  const f = surfaceFrame(s), c = vec.add(vec.add(f.p0, vec.mul(f.u, b.at)), vec.mul(f.n, bodyHalfHeight(b)));
  b.x = c.x; b.y = c.y;
  return b;
}
/** the body's centre and the angle of its base (radians) */
export function bodyPose(scene, b) {
  if (b.on) {
    const s = scene.objects.find(o => o.id === b.on);
    if (s) { const f = surfaceFrame(s), c = vec.add(vec.add(f.p0, vec.mul(f.u, b.at)), vec.mul(f.n, bodyHalfHeight(b))); return {x: c.x, y: c.y, angle: b.type === 'block' ? Math.atan2(f.u.y, f.u.x) : 0}; }
  }
  return {x: b.x, y: b.y, angle: 0};
}
/* the point where a string or a spring meets a body: the middle of the face looking towards `toward` (a block), or the
   centre (a ball) */
export function attachPoint(scene, b, toward, pose = bodyPose(scene, b)) {
  if (b.type === 'ball') return {x: pose.x, y: pose.y};
  const ca = Math.cos(pose.angle), sa = Math.sin(pose.angle);
  const ax = {x: ca, y: sa}, ay = {x: -sa, y: ca}, d = vec.sub(toward, pose);
  const faces = [[ax, b.w / 2], [vec.mul(ax, -1), b.w / 2], [ay, b.h / 2], [vec.mul(ay, -1), b.h / 2]];
  let best = faces[0], bv = -Infinity;
  for (const f of faces) { const v = vec.dot(vec.unit(d), f[0]); if (v > bv) { bv = v; best = f; } }
  return vec.add(pose, vec.mul(best[0], best[1]));
}
/* a fixed object as one point to hang or hook something on, seen from `from` */
export function anchorPoint(o, from) {
  if (o.type === 'pivot' || o.type === 'pulley') return {x: o.x, y: o.y};
  if (o.type === 'ceiling') return {x: Math.min(o.x + o.w, Math.max(o.x, from.x)), y: o.y};
  if (o.type === 'floor') return {x: Math.min(o.x + o.w, Math.max(o.x, from.x)), y: o.y};
  if (o.type === 'wall') return {x: o.x, y: Math.min(o.y + o.h, Math.max(o.y, from.y))};
  return {x: o.x, y: o.y};
}

/* the lines tangent to two circles (a point is a circle of radius 0) that run with the given turning senses
   (+1 anticlockwise, -1 clockwise, 0 a point): the tangent points on each */
export function tangentPoints(c1, r1, s1, c2, r2, s2) {
  const D = vec.sub(c2, c1), d = vec.len(D);
  if (d < 1e-9) return {t1: c1, t2: c2};
  const Dh = vec.mul(D, 1 / d), Dp = vec.perp(Dh);
  let best = null;
  for (const p1 of r1 > 0 ? [r1, -r1] : [0]) for (const p2 of r2 > 0 ? [r2, -r2] : [0]) {
    const cos = (p2 - p1) / d;
    if (Math.abs(cos) > 1) continue;
    const sin = Math.sqrt(1 - cos * cos);
    for (const sg of [1, -1]) {
      const n = vec.add(vec.mul(Dh, cos), vec.mul(Dp, sg * sin));
      const t1 = vec.sub(c1, vec.mul(n, p1)), t2 = vec.sub(c2, vec.mul(n, p2)), t = vec.sub(t2, t1);
      const ok1 = !s1 || Math.sign(vec.cross(t, vec.sub(c1, t1))) === s1, ok2 = !s2 || Math.sign(vec.cross(t, vec.sub(c2, t2))) === s2;
      if (ok1 && ok2 && vec.dot(t, D) > -1e-9) { best = {t1, t2}; break; }
    }
    if (best) break;
  }
  return best || {t1: c1, t2: c2};
}
/** the path of a string: its two end points, and for each pulley the turning sense and the points where the string
 *  meets and leaves it. poses: an optional map id → {x,y,angle} (the simulation's positions) */
export function stringPath(scene, str, poses) {
  const byId = new Map(scene.objects.map(o => [o.id, o]));
  const poseOf = o => poses?.get?.(o.id) || (isBody(o) ? bodyPose(scene, o) : {x: o.x, y: o.y, angle: 0});
  const A = byId.get(str.a), B = byId.get(str.b), pulleys = (str.over || []).map(id => byId.get(id)).filter(Boolean);
  if (!A || !B) return null;
  const centres = [poseOf(A), ...pulleys.map(p => ({x: p.x, y: p.y})), poseOf(B)];
  const end = (o, i, toward) => isBody(o) ? attachPoint(scene, o, toward, centres[i]) : {x: o.x, y: o.y};
  const pa = end(A, 0, centres[1]), pb = end(B, centres.length - 1, centres[centres.length - 2]);
  const nodes = [{c: pa, r: 0, s: 0}, ...pulleys.map((p, i) => {
    const prev = i === 0 ? pa : centres[i], next = i === pulleys.length - 1 ? pb : centres[i + 2];
    const s = Math.sign(vec.cross(vec.sub(p, prev), vec.sub(next, p))) || -1;
    return {c: {x: p.x, y: p.y}, r: p.r, s, id: p.id};
  }), {c: pb, r: 0, s: 0}];
  const segs = [];
  for (let i = 0; i + 1 < nodes.length; i++) { const {t1, t2} = tangentPoints(nodes[i].c, nodes[i].r, nodes[i].s, nodes[i + 1].c, nodes[i + 1].r, nodes[i + 1].s); segs.push([t1, t2]); }
  const wraps = pulleys.map((p, i) => ({id: p.id, c: nodes[i + 1].c, r: p.r, s: nodes[i + 1].s, from: segs[i][1], to: segs[i + 1][0]}));
  return {a: pa, b: pb, segs, wraps};
}

/* ── templates: the classic figures, ready to edit or run ── */
const T = (title, objects, view, extra = {}) => ({format: SCENE_FORMAT, version: SCENE_VERSION, title, g: 9.8, grid: 0.1, style: 'textbook', view, ...extra,
  objects: objects.map(o => ({...defaults(o.type), ...o}))});
const MECH_KEYS = ['atwood', 'incline_pulley', 'spring_block', 'pendulum', 'projectile', 'conical', 'vertical_circle'];
const MECH_NAMES = {
  atwood: {ko: '애트우드 기계', en: 'Atwood machine'}, incline_pulley: {ko: '빗면 · 도르래 · 매달린 물체', en: 'Incline, pulley and hanging mass'},
  spring_block: {ko: '용수철에 달린 물체', en: 'Block on a spring'}, pendulum: {ko: '단진자', en: 'Simple pendulum'},
  projectile: {ko: '포물선 운동', en: 'Projectile'}, conical: {ko: '원뿔 진자', en: 'Conical pendulum'}, vertical_circle: {ko: '연직면 원운동', en: 'Vertical circle'}
};
function mechTemplate(key, name) {
  if (key === 'atwood') return T(name, [
    {id: 'ceil', type: 'ceiling', x: 0.9, y: 2.6, w: 1.2},
    {id: 'p1', type: 'pulley', x: 1.5, y: 2.25, r: 0.2, mount: 'ceil'},
    {id: 'm1', type: 'block', x: 1.3, y: 1.55, w: 0.28, h: 0.28, mass: 3, label: 'm_1'},
    {id: 'm2', type: 'block', x: 1.7, y: 0.75, w: 0.24, h: 0.24, mass: 2, label: 'm_2'},
    {id: 's1', type: 'string', a: 'm1', b: 'm2', over: ['p1']},
    {id: 'gnd', type: 'floor', x: 0.6, y: 0, w: 1.8}
  ], {x: 0.3, y: -0.25, w: 2.4, h: 3.05});
  if (key === 'incline_pulley') {
    const inc = {id: 'inc', type: 'incline', x: 0.3, y: 0, angle: 30, length: 2.4, mu: 0.1, angleLabel: '\\theta'};
    const f = surfaceFrame({...defaults('incline'), ...inc}), top = vec.add(f.p0, vec.mul(f.u, inc.length)), r = 0.09, hA = 0.24;
    const c = vec.add(vec.add(top, vec.mul(f.n, hA / 2 - r)), vec.mul(f.u, 0.1));
    return T(name, [
      {id: 'gnd', type: 'floor', x: 0, y: 0, w: 3.1},
      inc,
      {id: 'm1', type: 'block', on: 'inc', at: 1.0, w: 0.34, h: hA, mass: 2, label: 'm_1'},
      {id: 'p1', type: 'pulley', x: +c.x.toFixed(4), y: +c.y.toFixed(4), r, mount: 'inc'},
      {id: 'm2', type: 'block', x: +(c.x + r).toFixed(4), y: 0.75, w: 0.24, h: 0.24, mass: 3, label: 'm_2'},
      {id: 's1', type: 'string', a: 'm1', b: 'm2', over: ['p1']},
      {id: 'lmu', type: 'label', x: 1.05, y: 0.28, text: '\\mu', size: 15}
    ], {x: -0.15, y: -0.3, w: 3.4, h: 1.95});
  }
  if (key === 'spring_block') return T(name, [
    {id: 'wl', type: 'wall', x: 0.2, y: 0, h: 0.7, side: 'left'},
    {id: 'gnd', type: 'floor', x: 0.2, y: 0, w: 2.6},
    {id: 'm1', type: 'block', on: 'gnd', at: 1.4, w: 0.3, h: 0.3, mass: 1, label: 'm'},
    {id: 'k1', type: 'spring', a: 'wl', b: 'm1', k: 40, L0: 1.0, coils: 10, label: 'k'},
    {id: 'd1', type: 'dim', x1: 1.6, y1: -0.12, x2: 1.35, y2: -0.12, offset: -0.12, text: 'A'}
  ], {x: -0.05, y: -0.45, w: 3.05, h: 1.3});
  if (key === 'pendulum') { const L = 1.5, a = rad(25); return T(name, [
    {id: 'ceil', type: 'ceiling', x: 1.0, y: 2.4, w: 1.0},
    {id: 'pv', type: 'pivot', x: 1.5, y: 2.4},
    {id: 'b1', type: 'ball', x: +(1.5 + L * Math.sin(a)).toFixed(4), y: +(2.4 - L * Math.cos(a)).toFixed(4), r: 0.08, mass: 0.5, label: 'm'},
    {id: 's1', type: 'string', a: 'pv', b: 'b1', label: 'L'},
    {id: 'ln', type: 'line', x1: 1.5, y1: 2.4, x2: 1.5, y2: 0.7, pattern: 'dashed'},
    {id: 'th', type: 'arc', x: 1.5, y: 2.4, r: 0.35, from: -90, to: -65, text: '\\theta'}
  ], {x: 0.6, y: 0.55, w: 1.8, h: 2.05}); }
  if (key === 'projectile') { const v = 10, a = rad(45); return T(name, [
    {id: 'gnd', type: 'floor', x: -0.2, y: 0, w: 11.6},
    {id: 'b1', type: 'ball', x: 0.3, y: 0.1, r: 0.1, mass: 0.2, vx: +(v * Math.cos(a)).toFixed(4), vy: +(v * Math.sin(a)).toFixed(4), showV: true, vLabel: 'v_0', trail: true},
    {id: 'th', type: 'arc', x: 0.3, y: 0.1, r: 0.55, from: 0, to: 45, text: '\\theta'},
    {id: 'ax', type: 'axes', x: 0.3, y: 0.1, lx: 10.8, ly: 3.2, xlabel: 'x', ylabel: 'y'}
  ], {x: -0.5, y: -0.6, w: 12, h: 4.2}); }
  if (key === 'conical') { const L = 1.6, a = rad(30); return T(name, [
    {id: 'ceil', type: 'ceiling', x: 0.9, y: 2.6, w: 1.2},
    {id: 'pv', type: 'pivot', x: 1.5, y: 2.6},
    {id: 'b1', type: 'ball', x: +(1.5 + L * Math.sin(a)).toFixed(4), y: +(2.6 - L * Math.cos(a)).toFixed(4), r: 0.08, mass: 0.5, label: 'm'},
    {id: 's1', type: 'string', a: 'pv', b: 'b1', mode: 'conical', label: 'L'},
    {id: 'ln', type: 'line', x1: 1.5, y1: 2.6, x2: 1.5, y2: 1.0, pattern: 'dashed'},
    {id: 'th', type: 'arc', x: 1.5, y: 2.6, r: 0.4, from: -90, to: -60, text: '\\theta'}
  ], {x: 0.35, y: 0.75, w: 2.3, h: 2.1}); }
  if (key === 'vertical_circle') return T(name, [
    {id: 'pv', type: 'pivot', x: 1.5, y: 1.5},
    {id: 'b1', type: 'ball', x: 1.5, y: 0.5, r: 0.08, mass: 0.3, label: 'm', vx: 6, showV: true, vLabel: 'v_0', trail: true},
    {id: 's1', type: 'string', a: 'pv', b: 'b1', label: 'r'}
  ], {x: 0.2, y: 0.15, w: 2.6, h: 2.7});
  return {...blankScene(), view: {x: -0.5, y: -0.5, w: 4, h: 3}};
}

/* the other domains' templates: [domain, ko, en, grid, view, objects] */
const NEW_TEMPLATES = {
  /* electromagnetism */
  rc_circuit: ['em', 'RC 회로 (충전)', 'RC circuit (charging)', 0.25, {x: -0.9, y: -0.6, w: 4.8, h: 3.2}, [
    {id: 'E1', type: 'element', kind: 'battery', x1: 0, y1: 0, x2: 0, y2: 2, value: 12, label: '\\mathcal{E}'},
    {id: 'S1', type: 'element', kind: 'switch', x1: 0, y1: 2, x2: 1.25, y2: 2, closed: true, label: 'S'},
    {id: 'R1', type: 'element', kind: 'resistor', x1: 1.25, y1: 2, x2: 3, y2: 2, value: 10000, label: 'R'},
    {id: 'C1', type: 'element', kind: 'capacitor', x1: 3, y1: 2, x2: 3, y2: 0, value: 100, label: 'C'},
    {id: 'A1', type: 'element', kind: 'ammeter', x1: 3, y1: 0, x2: 1.5, y2: 0},
    {id: 'W1', type: 'element', kind: 'wire', x1: 1.5, y1: 0, x2: 0, y2: 0}]],
  wheatstone: ['em', '휘트스톤 브리지', 'Wheatstone bridge', 0.25, {x: -1, y: -1.7, w: 5, h: 5.2}, [
    {id: 'R1', type: 'element', kind: 'resistor', x1: 0, y1: 1.5, x2: 1.5, y2: 3, value: 100, label: 'R_1'},
    {id: 'R2', type: 'element', kind: 'resistor', x1: 1.5, y1: 3, x2: 3, y2: 1.5, value: 200, label: 'R_2'},
    {id: 'R3', type: 'element', kind: 'resistor', x1: 0, y1: 1.5, x2: 1.5, y2: 0, value: 150, label: 'R_3'},
    {id: 'R4', type: 'element', kind: 'resistor', x1: 1.5, y1: 0, x2: 3, y2: 1.5, value: 300, label: 'R_4'},
    {id: 'G1', type: 'element', kind: 'galvanometer', x1: 1.5, y1: 3, x2: 1.5, y2: 0, value: 50},
    {id: 'W1', type: 'element', kind: 'wire', x1: 0, y1: 1.5, x2: 0, y2: -1},
    {id: 'E1', type: 'element', kind: 'battery', x1: 0, y1: -1, x2: 3, y2: -1, value: 6, label: '\\mathcal{E}'},
    {id: 'W2', type: 'element', kind: 'wire', x1: 3, y1: -1, x2: 3, y2: 1.5},
    {id: 'lA', type: 'label', x: -0.3, y: 1.5, text: 'A', size: 15}, {id: 'lB', type: 'label', x: 1.5, y: 3.3, text: 'B', size: 15},
    {id: 'lC', type: 'label', x: 3.3, y: 1.5, text: 'C', size: 15}, {id: 'lD', type: 'label', x: 1.5, y: -0.3, text: 'D', size: 15}]],
  capacitor_charge: ['em', '평행판 축전기 속 대전 입자', 'A charge between capacitor plates', 0.1, {x: -1.1, y: -0.75, w: 5.2, h: 2.5}, [
    {id: 'P1', type: 'plate', x1: 0, y1: 1.2, x2: 3, y2: 1.2, q: 20, label: ''},
    {id: 'P2', type: 'plate', x1: 0, y1: 0, x2: 3, y2: 0, q: -20, label: ''},
    {id: 'F1', type: 'field', kind: 'E', dir: 'arrow', angle: -90, x: 0.05, y: 0.05, w: 2.9, h: 1.1, mag: 1, spacing: 0.5, pattern: 'none', label: '\\vec{E}'},
    {id: 'q1', type: 'charge', x: -0.7, y: 0.9, q: 1, r: 0.07, mass: 1, vx: 3, vy: 0, showV: true, vLabel: '\\vec{v}_0', trail: true, label: 'q'},
    {id: 'd1', type: 'dim', x1: 3.35, y1: 0, x2: 3.35, y2: 1.2, offset: 0, text: 'd'},
    {id: 'd2', type: 'dim', x1: 0, y1: -0.3, x2: 3, y2: -0.3, offset: 0, text: 'L'}]],
  dipole_field: ['em', '전기 쌍극자의 전기력선', 'Field lines of a dipole', 0.1, {x: -2.6, y: -1.8, w: 5.2, h: 3.6}, [
    {id: 'qa', type: 'charge', x: -1, y: 0, q: 2, r: 0.12, label: '+q'},
    {id: 'qb', type: 'charge', x: 1, y: 0, q: -2, r: 0.12, label: '-q'},
    {id: 'FL', type: 'fieldlines', n: 14, levels: 6, equip: true, arrows: true}]],
  particle_in_b: ['em', '자기장 속 대전 입자', 'A charged particle in a magnetic field', 0.1, {x: -1.4, y: -0.5, w: 5.4, h: 3.8}, [
    {id: 'B1', type: 'field', kind: 'B', dir: 'in', x: 0, y: 0, w: 3.6, h: 3, mag: 1, spacing: 0.4, pattern: 'dashed', label: '\\vec{B}'},
    {id: 'q1', type: 'charge', x: -0.8, y: 0.3, q: 1, r: 0.07, mass: 1, vx: 1.2, vy: 0, showV: true, vLabel: '\\vec{v}', trail: true, label: 'q, m'}]],
  magnetic_sources: ['em', '솔레노이드 · 막대자석 · 직선 전류', 'Solenoid, bar magnet and a straight current', 0.1, {x: -0.4, y: -1.9, w: 6.2, h: 3.2}, [
    {id: 'sol', type: 'solenoid', x: 0.2, y: 0, w: 2.6, h: 0.8, turns: 10, showB: true, label: 'I'},
    {id: 'mag', type: 'magnet', x: 0.5, y: -1.4, w: 2, h: 0.4},
    {id: 'cur', type: 'current', x: 4.4, y: -0.2, r: 0.08, dir: 'out', rings: 3, label: 'I'},
    {id: 'cw', type: 'cwire', x1: 3.4, y1: 0.95, x2: 5.6, y2: 0.95, I: 1, label: 'I'}]],
  /* thermodynamics */
  carnot: ['thermo', '카르노 순환 (P–V)', 'Carnot cycle (P–V)', 0.1, {x: -0.6, y: -0.55, w: 5.4, h: 4.1}, [
    {id: 'G1', type: 'graph', x: 0, y: 0, w: 4.2, h: 3, auto: true, xlabel: 'V', ylabel: 'P'},
    {id: 'C1', type: 'cycle', graph: 'G1', kind: 'carnot', v1: 1, v2: 2.2, t1: 600, t2: 350, gamma: 1.67, labels: true, arrows: true, shade: true},
    {id: 'eta', type: 'label', x: 3.1, y: 2.5, text: '\\eta = 1 - \\frac{T_C}{T_H}', size: 15}]],
  otto: ['thermo', '오토 순환 (P–V)', 'Otto cycle (P–V)', 0.1, {x: -0.6, y: -0.55, w: 5.4, h: 4.1}, [
    {id: 'G1', type: 'graph', x: 0, y: 0, w: 4.2, h: 3, auto: true, xlabel: 'V', ylabel: 'P'},
    {id: 'C1', type: 'cycle', graph: 'G1', kind: 'otto', v1: 1, v2: 4, t1: 1500, t2: 300, gamma: 1.4, labels: true, arrows: true, shade: true}]],
  pv_processes: ['thermo', '네 가지 과정 (등온·단열·등압·등적)', 'Four processes (isothermal, adiabatic, isobaric, isochoric)', 0.1, {x: -0.6, y: -0.55, w: 5.6, h: 4.1}, [
    {id: 'G1', type: 'graph', x: 0, y: 0, w: 4.4, h: 3, auto: false, xmin: 0, xmax: 4.6, ymin: 0, ymax: 4.6, xlabel: 'V', ylabel: 'P', ticks: false},
    {id: 'c1', type: 'curve', graph: 'G1', kind: 'isobar', x1: 1, x2: 4, y1: 4, heads: 'mid', label: 'P'},
    {id: 'c2', type: 'curve', graph: 'G1', kind: 'isotherm', x1: 1, x2: 4, y1: 4, heads: 'mid', label: 'T'},
    {id: 'c3', type: 'curve', graph: 'G1', kind: 'adiabat', x1: 1, x2: 4, y1: 4, gamma: 1.667, heads: 'mid', label: 'Q = 0'},
    {id: 'c4', type: 'curve', graph: 'G1', kind: 'isochore', x1: 1, y1: 4, y2: 0.6, heads: 'mid', label: 'V'},
    {id: 'pA', type: 'point', x: 0.957, y: 2.609, label: 'A'}]],
  piston_gas: ['thermo', '피스톤 실린더와 열원', 'Gas under a piston on a reservoir', 0.1, {x: -0.8, y: -0.4, w: 3.8, h: 3.4}, [
    {id: 'cyl', type: 'cylinder', x: 0.3, y: 0.5, w: 1.4, h: 1.9, piston: 0.6, gas: true, weight: true, label: 'n, T'},
    {id: 'res', type: 'reservoir', x: -0.1, y: 0, w: 2.2, h: 0.45, hot: true, label: 'T_H'},
    {id: 'Q', type: 'vector', x1: 2.4, y1: 0.25, x2: 2.4, y2: 1.0, label: 'Q'},
    {id: 'dh', type: 'dim', x1: 0.15, y1: 0.5, x2: 0.15, y2: 1.6, offset: 0, text: 'h'}]],
  heat_engine: ['thermo', '열기관 도식', 'Heat engine diagram', 0.1, {x: -0.2, y: -0.2, w: 3.6, h: 3.4}, [
    {id: 'eng', type: 'engine', x: 1.5, y: 1.5, size: 1, kind: 'engine'}]],
  /* optics */
  two_lens: ['optics', '두 렌즈 광선 추적', 'Two-lens ray tracing', 0.1, {x: -0.5, y: -1.8, w: 9.6, h: 3.6}, [
    {id: 'ax', type: 'line', x1: -0.3, y1: 0, x2: 9, y2: 0, pattern: 'dashdot'},
    {id: 'L1', type: 'lens', x: 2, y: 0, h: 2, f: 1, label: 'L_1'},
    {id: 'L2', type: 'lens', x: 5.5, y: 0, h: 2.8, f: 1, label: 'L_2'},
    {id: 'O', type: 'oarrow', x: 0, y: 0, h: 0.5, label: 'O', rays: true, image: true, imageLabel: "I"}]],
  concave_mirror: ['optics', '오목 거울의 상', 'Image in a concave mirror', 0.1, {x: -0.3, y: -1.4, w: 5, h: 2.8}, [
    {id: 'ax', type: 'line', x1: -0.1, y1: 0, x2: 4.4, y2: 0, pattern: 'dashdot'},
    {id: 'M', type: 'mirror', x: 4, y: 0, h: 2, f: 1, face: 'left', label: 'M'},
    {id: 'O', type: 'oarrow', x: 1.5, y: 0, h: 0.5, label: 'O', rays: true, image: true, imageLabel: "I"}]],
  diverging_lens: ['optics', '오목 렌즈의 허상', 'Virtual image of a diverging lens', 0.1, {x: -0.3, y: -1.3, w: 6, h: 2.6}, [
    {id: 'ax', type: 'line', x1: -0.1, y1: 0, x2: 5.5, y2: 0, pattern: 'dashdot'},
    {id: 'L1', type: 'lens', x: 3, y: 0, h: 1.8, f: -1.2, label: 'L'},
    {id: 'O', type: 'oarrow', x: 1, y: 0, h: 0.6, label: 'O', rays: true, image: true, imageLabel: "I"}]],
  prism: ['optics', '프리즘을 지나는 빛', 'A ray through a prism', 0.1, {x: -0.5, y: -0.6, w: 5, h: 2.8}, [
    {id: 'P', type: 'prism', x: 2, y: 0, size: 2, apex: 60, n: 1.5, label: 'n'},
    {id: 'r1', type: 'ray', x: -0.2, y: 0.35, angle: 15, len: 7, arrow: true}]],
  slab_shift: ['optics', '유리판의 굴절 (옆 밀림)', 'Refraction through a glass slab', 0.1, {x: -0.4, y: -1.2, w: 4.6, h: 3.6}, [
    {id: 'S', type: 'slab', x: 0.2, y: 0, w: 3.6, h: 1, n: 1.5, label: 'n'},
    {id: 'r1', type: 'ray', x: 0.5, y: 2.1, angle: -50, len: 5, arrow: true},
    {id: 'nl', type: 'line', x1: 1.42, y1: 1.6, x2: 1.42, y2: 0.4, pattern: 'dashed'},
    {id: 'th', type: 'arc', x: 1.42, y: 1, r: 0.35, from: 90, to: 140, text: '\\theta_1'}]],
  double_slit: ['optics', '영의 이중 슬릿', "Young's double slit", 0.1, {x: -0.6, y: -1.6, w: 5.6, h: 3.4}, [
    {id: 'S', type: 'slits', x: 1, y: 0, n: 2, d: 0.25, a: 0.04, L: 1.5, lambda: 600, h: 2.4, screen: 2.6, pattern: true, labels: true, waves: true}]],
  /* waves */
  travel_wave: ['waves', '진행파 (λ, A)', 'A travelling wave (λ, A)', 0.1, {x: -0.4, y: -0.9, w: 5, h: 1.9}, [
    {id: 'w1', type: 'wave', x: 0, y: 0, len: 4.2, A: 0.45, lambda: 1.6, kind: 'travel', showLambda: true, showA: true, axis: true, arrow: true, label: '\\vec{v}'}]],
  standing_string: ['waves', '양 끝이 고정된 줄의 정상파', 'Standing wave on a string with fixed ends', 0.1, {x: -0.5, y: -0.9, w: 5, h: 1.8}, [
    {id: 'w1', type: 'wave', x: 0, y: 0, len: 4, A: 0.45, kind: 'standing', n: 3, ends: 'fixed', envelope: true, showLambda: true, showA: false, axis: false, label: 'n = 3'}]],
  wavefronts: ['waves', '점파원과 평면파의 파면', 'Wavefronts of a point source and a plane wave', 0.1, {x: -1.6, y: -1.4, w: 6.4, h: 2.8}, [
    {id: 'wc', type: 'wavefront', x: 0, y: 0, kind: 'circular', n: 4, spacing: 0.3, h: 2.6},
    {id: 'pS', type: 'point', x: 0, y: 0, label: 'S'},
    {id: 'wp', type: 'wavefront', x: 2.6, y: 0, kind: 'plane', n: 5, spacing: 0.3, angle: 0, h: 2.2},
    {id: 'k', type: 'vector', x1: 3.2, y1: -0.9, x2: 4.4, y2: -0.9, label: '\\vec{k}'}]],
  /* modern physics */
  finite_well: ['modern', '유한 퍼텐셜 우물 (ψ)', 'Finite square well (ψ)', 0.1, {x: -0.6, y: -0.5, w: 5.4, h: 3.9}, [
    {id: 'Wl', type: 'well', x: 0, y: 0, w: 4.4, h: 3.2, kind: 'finite', L: 1, V0: 3, levels: 3, psi: 'psi'}]],
  infinite_well: ['modern', '무한 퍼텐셜 우물 (|ψ|²)', 'Infinite square well (|ψ|²)', 0.1, {x: -0.6, y: -0.5, w: 5.4, h: 3.9}, [
    {id: 'Wl', type: 'well', x: 0, y: 0, w: 4.4, h: 3.2, kind: 'infinite', L: 1, levels: 3, psi: 'prob'}]],
  barrier: ['modern', '퍼텐셜 장벽과 터널 효과', 'Potential barrier and tunnelling', 0.1, {x: -0.6, y: -0.5, w: 5.6, h: 3.2}, [
    {id: 'Wl', type: 'well', x: 0, y: 0, w: 4.6, h: 2.5, kind: 'barrier', L: 0.4, V0: 4, E: 2.5, psi: 'psi'}]],
  hydrogen: ['modern', '수소 원자 에너지 준위 (발머 계열)', 'Hydrogen energy levels (Balmer series)', 0.1, {x: -0.4, y: -0.4, w: 4.6, h: 3.8}, [
    {id: 'Lv', type: 'levels', x: 0.5, y: 0, w: 3, h: 3, kind: 'hydrogen', n: 6, trans: '3-2,4-2,5-2,6-2', labels: true, showLambda: true}]],
  minkowski: ['modern', '민코프스키 도표와 움직이는 시계', 'Minkowski diagram with a moving clock', 0.1, {x: -1.9, y: -0.5, w: 5.6, h: 3.9}, [
    {id: 'st', type: 'spacetime', x: 0, y: 0, size: 3, units: 4, beta: 0.5, primed: true, cone: true, hyperbola: true},
    {id: 'clk', type: 'worldline', diagram: 'st', x0: 1, beta: 0.5, ticks: true, tau: 1, label: '\\text{clock}'},
    {id: 'rest', type: 'worldline', diagram: 'st', x0: -1, beta: 0, ticks: true, tau: 1, label: ''}]],
  photoelectric: ['modern', '광전 효과 장치', 'Photoelectric effect setup', 0.1, {x: -0.4, y: -0.6, w: 3.8, h: 3.2}, [
    {id: 'pt', type: 'phototube', x: 0, y: 0, w: 3, h: 2.2, label: '$hf$'}]],
  /* general */
  function_graph: ['general', '함수 그래프', 'Graph of a function', 0.1, {x: -0.6, y: -1.6, w: 5.6, h: 3.4}, [
    {id: 'G1', type: 'graph', x: 0, y: -1.2, w: 4.4, h: 2.4, auto: false, xmin: 0, xmax: 7, ymin: -1.3, ymax: 1.3, xlabel: 't', ylabel: 'x', ticks: true, origin: 'O'},
    {id: 'c1', type: 'curve', graph: 'G1', kind: 'func', expr: 'exp(-x/3)*cos(3x)', x1: 0, x2: 7, label: ''},
    {id: 'c2', type: 'curve', graph: 'G1', kind: 'func', expr: 'exp(-x/3)', x1: 0, x2: 7, pattern: 'dashed', label: 'Ae^{-t/\\tau}'},
    {id: 'c3', type: 'curve', graph: 'G1', kind: 'func', expr: '-exp(-x/3)', x1: 0, x2: 7, pattern: 'dashed', label: ''}]],
  vectors: ['general', '벡터의 합과 각', 'Adding vectors, with angles', 0.1, {x: -0.5, y: -0.5, w: 4.2, h: 3}, [
    {id: 'va', type: 'vector', x1: 0, y1: 0, x2: 2.2, y2: 0.6, label: '\\vec{A}'},
    {id: 'vb', type: 'vector', x1: 2.2, y1: 0.6, x2: 3, y2: 2.1, label: '\\vec{B}'},
    {id: 'vs', type: 'vector', x1: 0, y1: 0, x2: 3, y2: 2.1, width: 2.2, label: '\\vec{A}+\\vec{B}'},
    {id: 'gl', type: 'line', x1: 0, y1: 0, x2: 3.2, y2: 0, pattern: 'dotted'},
    {id: 'th', type: 'arc', x: 0, y: 0, r: 0.6, from: 0, to: 15.3, text: '\\alpha'},
    {id: 'ph', type: 'arc', x: 0, y: 0, r: 0.95, from: 0, to: 35, text: '\\phi', arrow: true}]],
  annotated: ['general', '영역 · 점 · 치수 표시', 'Regions, points and dimensions', 0.1, {x: -0.4, y: -0.6, w: 4.6, h: 3}, [
    {id: 'rg', type: 'region', x: 0.2, y: 0.2, w: 2.2, h: 1.6, shape: 'ellipse', fill: 'gray', label: 'V'},
    {id: 'rh', type: 'region', x: 2.8, y: 0.3, w: 1, h: 1.4, shape: 'rect', fill: 'hatch', pattern: 'solid', label: ''},
    {id: 'P', type: 'point', x: 1.3, y: 1, label: 'P'},
    {id: 'd', type: 'dim', x1: 0.2, y1: -0.15, x2: 2.4, y2: -0.15, offset: 0, text: '2a'},
    {id: 'tb', type: 'label', x: 3.3, y: 2.1, text: '\\rho = \\mathrm{const}', size: 14, box: true}]]
};
export const TEMPLATE_KEYS = [...MECH_KEYS, ...Object.keys(NEW_TEMPLATES)];
export const TEMPLATE_NAMES = {...MECH_NAMES, ...Object.fromEntries(Object.entries(NEW_TEMPLATES).map(([k, t]) => [k, {ko: t[1], en: t[2]}]))};
export const TEMPLATE_DOMAIN = {...Object.fromEntries(MECH_KEYS.map(k => [k, 'mech'])), ...Object.fromEntries(Object.entries(NEW_TEMPLATES).map(([k, t]) => [k, t[0]]))};
export function template(key, lang = 'ko') {
  const name = (TEMPLATE_NAMES[key] || {})[lang === 'en' ? 'en' : 'ko'] || '';
  const t = NEW_TEMPLATES[key];
  if (t) return T(name, t[5], t[4], {grid: t[3]});
  return mechTemplate(key, name);
}

/** the world box of an object that is not a body or a connection (null for what is drawn inside another object) */
export function objectExtent(o) {
  const box = (x0, y0, x1, y1) => ({x: Math.min(x0, x1), y: Math.min(y0, y1), w: Math.abs(x1 - x0), h: Math.abs(y1 - y0)});
  switch (o.type) {
    case 'floor': return box(o.x, o.y - 0.15, o.x + o.w, o.y);
    case 'ceiling': return box(o.x, o.y, o.x + o.w, o.y + 0.15);
    case 'wall': return box(o.x + (o.side === 'left' ? -0.15 : 0.15), o.y, o.x, o.y + o.h);
    case 'incline': { const c = inclineCorners(o); return box(Math.min(c.foot.x, c.top.x), c.foot.y - 0.1, Math.max(c.foot.x, c.top.x), c.top.y); }
    case 'pulley': case 'charge': case 'current': return box(o.x - o.r, o.y - o.r, o.x + o.r, o.y + o.r);
    case 'loop': return box(o.x - o.r, o.y - o.r * o.tilt, o.x + o.r, o.y + o.r * o.tilt);
    case 'pivot': case 'label': case 'point': case 'ground': return box(o.x - 0.1, o.y - 0.1, o.x + 0.1, o.y + 0.1);
    case 'dim': case 'line': case 'element': case 'plate': case 'cwire': case 'vector': {
      const r = o.type === 'element' ? 0.18 : 0.05; return box(Math.min(o.x1, o.x2) - r, Math.min(o.y1, o.y2) - r, Math.max(o.x1, o.x2) + r, Math.max(o.y1, o.y2) + r);
    }
    case 'arc': return box(o.x - o.r, o.y - o.r, o.x + o.r, o.y + o.r);
    case 'axes': return box(o.x, o.y, o.x + o.lx, o.y + o.ly);
    case 'field': case 'solenoid': case 'magnet': case 'cylinder': case 'reservoir': case 'graph': case 'slab': case 'well': case 'levels': case 'phototube': case 'region':
      return box(o.x, o.y, o.x + o.w, o.y + o.h);
    case 'engine': return box(o.x - 1.4 * o.size, o.y - 1.45 * o.size, o.x + 1.4 * o.size, o.y + 1.45 * o.size);
    case 'lens': case 'mirror': return box(o.x - 0.15, o.y - o.h / 2, o.x + 0.15, o.y + o.h / 2);
    case 'prism': { const ht = (o.size / 2) / Math.tan(o.apex * Math.PI / 360); return box(o.x - o.size / 2, o.y, o.x + o.size / 2, o.y + ht); }
    case 'oarrow': return box(o.x - 0.1, Math.min(o.y, o.y + o.h), o.x + 0.1, Math.max(o.y, o.y + o.h));
    case 'ray': { const a = o.angle * Math.PI / 180; return box(o.x, o.y, o.x + Math.cos(a) * Math.min(o.len, 1), o.y + Math.sin(a) * Math.min(o.len, 1)); }
    case 'slits': return box(o.x - 1, o.y - o.h / 2, o.x + o.screen + 1, o.y + o.h / 2);
    case 'wavefront': return o.kind === 'circular' ? box(o.x - o.n * o.spacing, o.y - o.n * o.spacing, o.x + o.n * o.spacing, o.y + o.n * o.spacing) : box(o.x, o.y - o.h / 2, o.x + o.n * o.spacing, o.y + o.h / 2);
    case 'wave': return box(o.x, o.y - o.A - 0.3, o.x + o.len, o.y + o.A + 0.3);
    case 'spacetime': return box(o.x - o.size * 0.6, o.y - 0.1, o.x + o.size, o.y + o.size);
    case 'frames': return box(o.x - 0.1, o.y - 0.1, o.x + o.gap + o.size, o.y + o.size + 0.3);
  }
  return null;
}

/** the world rectangle every object fits in, with a margin */
export function sceneBounds(scene) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  const add = (x, y) => { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); };
  for (const o of scene.objects) {
    if (isBody(o)) { const p = bodyPose(scene, o), r = Math.max(bodyHalfWidth(o), bodyHalfHeight(o)) * 1.5; add(p.x - r, p.y - r); add(p.x + r, p.y + r); continue; }
    const b = objectExtent(o);
    if (b) { add(b.x, b.y); add(b.x + b.w, b.y + b.h); }
  }
  if (!Number.isFinite(x0)) return {x: -0.5, y: -0.5, w: 4, h: 3};
  const m = Math.max(0.25, 0.08 * Math.max(x1 - x0, y1 - y0));
  return {x: x0 - m, y: y0 - m, w: Math.max(0.5, x1 - x0 + 2 * m), h: Math.max(0.5, y1 - y0 + 2 * m)};
}

/* what the vision model is asked to write (community/src/workshop-scene.js); kept here so it follows the schema */
export const VISION_OBJECT_TYPES = ['block', 'ball', 'floor', 'ceiling', 'wall', 'incline', 'pulley', 'pivot', 'string', 'rod', 'spring', 'force',
  'element', 'ground', 'charge', 'plate', 'field', 'cwire', 'current', 'solenoid', 'magnet',
  'cylinder', 'reservoir', 'graph', 'curve',
  'lens', 'mirror', 'prism', 'slab', 'oarrow', 'ray',
  'wave', 'well', 'spacetime',
  'label', 'arc', 'dim', 'line', 'vector'];
export const UNSURE_FIELDS = ['object', 'position', 'mass', 'angle', 'mu', 'k', 'length', 'connection', 'velocity', 'force', 'label', 'value', 'charge', 'kind', 'focal'];
/** every field the vision model may write for VISION_OBJECT_TYPES, as one JSON-schema property each (enums merged) */
export function visionProperties() {
  const props = {};
  for (const t of VISION_OBJECT_TYPES) for (const [k, f] of Object.entries(FIELDS[t])) {
    const s = f.k === 'num' ? {type: 'number'} : f.k === 'bool' ? {type: 'boolean'} : f.k === 'refs' ? {type: 'array', items: {type: 'string'}} : f.k === 'enum' ? {type: 'string', enum: [...f.list]} : {type: 'string'};
    const old = props[k];
    if (!old) props[k] = s;
    else if (old.type !== s.type) throw new Error('vision field ' + k + ' has two kinds');
    else if (s.enum) props[k] = {type: 'string', enum: [...new Set([...(old.enum || []), ...s.enum])]};
  }
  return props;
}
