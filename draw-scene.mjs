/* The scene of the Workshop's figure and simulation editor (#/workshop/draw, draw.html). One plain JSON object is both
   the exam figure and the system the simulation runs, so a figure a teacher draws can be played and a photo read by
   the AI (community/src/workshop-scene.js) can be checked against the same rules. This file is shared: the browser
   imports it (draw.js, draw-render.mjs, draw-physics.mjs) and so does the community Worker. No DOM, no network.

   Scene, version 2 (lengths in metres of the figure's world, masses in kg, forces in N, angles in degrees, y up):
     {format:'haslalab-scene', version:2, title:'', g:9.8, grid:0.1, style:'textbook', view:{x,y,w,h}, objects:[…]}
   style is the figure style ("그림체", draw-render.mjs STYLES): textbook | classic | modern | olympiad | jee | suneung |
   print. 'university' (대학 과제) was merged into textbook: a scene or an object written with it reads as textbook.
   Every object may carry its own style (one object drawn in another 그림체; '' follows the figure's).
   Optional top-level: gravityOn (false: the drawn rigid shapes float) and drag (air drag of the rigid shapes, 1/s).
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
       rough    on (a floor or an incline) from len mu look ('hatch'|'gray'|'dots') showMu label   a rough span of it
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
       label    x,y text size box font (math|serif|sans|mono|hand) italic bold underline align (left|center|right)
                                           dim x1,y1,x2,y2 offset text      arc x,y r from to text arrow
       axes     x,y lx ly xlabel ylabel    line x1,y1,x2,y2 pattern heads   vector x1,y1,x2,y2 label width head
       region   x,y w,h shape fill pattern label                            point x,y label filled
   drawing (the editor's tools; color: black gray lightgray blue red green orange; fill: none white lightgray gray dark
   hatch dots cross tint)
       rect x,y,w,h r (corner) color fill pattern rot     ellipse x,y,w,h color fill pattern rot
       poly pts [[x,y],…] (2–400) closed smooth color fill pattern heads     (polyline, polygon, the pen's strokes)
       bezier x1,y1 cx1,cy1 cx2,cy2 x2,y2 color pattern heads
       line, label and arc also take color (arc a pattern).
   a typed potential
       qpot x,y,w,h V (expr in x, nm → eV) params ("a=1 [0.2, 3], V0=5") xmin xmax mass showV levels psi E tplot Emax
            labels — its bound states and a scattering state, solved numerically (draw-physics.mjs qpotModel)
   A curve's expr can use its params too. A particle's velocity arrow is off unless arrow (a scene written before,
   without the field, keeps it).
   curve kinds param (x = expr(t), y = expr2(t) for t from x1 to x2), polar (r = expr(t), θ = t from x1 to x2, radians)
   and ineq (the part of the graph where y rel expr(x), rel lt le gt ge, shaded; a strict one has a dashed edge); a
   function curve can show tangent (at x = tx), area (from a1 to a2, its value written), roots and extrema (found
   numerically, draw-physics.mjs funcFeatures). graph xstep, ystep: the tick spacing (0: automatic).
   physics given to drawn shapes (rect, ellipse, poly, line: draw-physics.mjs rigidWorld): phys none | dynamic | static,
   pmass (kg), pvx, pvy (m/s), pw (rad/s), pmu (friction), pe (restitution), pfx, pfy (a constant applied force, N);
       joint    a b (drawn shapes; b '' = the fixed point bx,by) kind (spring | string | rod) ax,ay (the point on a, from its
                centre, in its own frame) bx,by k L0 (0: the distance at the start) damp coils label
   geometric construction (GeoGebra-like; every dependent object is computed from what it refers to, computeGeometry):
       gpoint   x,y kind (free | on: on the line, circle or polygon a, the nearest point to x,y | mid: of the points a, b
                or of the segment a | inter: the n-th intersection of a and b) label show
       gline    a b kind (segment | line | ray | perp | par: through a, perpendicular or parallel to the line base)
                measure (the length written) label color pattern
       gcircle  c (centre) p (a point on it, or '' and the radius r) measure color fill pattern label
       gpoly    pts [point ids] measure (the area written) color fill pattern label
       gangle   a b (the vertex) c r measure (the angle written) label
   validateScene() checks every field (type, range, references) and returns the normalised version-2 scene. */

export const SCENE_FORMAT = 'haslalab-scene', SCENE_VERSION = 2, MAX_OBJECTS = 120;
export const BODY_TYPES = ['block', 'ball', 'wheel'];
export const SURFACE_TYPES = ['floor', 'incline'];
export const ANCHOR_TYPES = ['pivot', 'ceiling', 'wall', 'floor'];
export const MARK_TYPES = ['label', 'dim', 'arc', 'axes', 'line', 'vector', 'region', 'point', 'panel', 'brace', 'callout', 'rect', 'ellipse', 'poly', 'bezier'];
/* the plain shapes the drawing tools make */
export const SHAPE_TYPES = ['line', 'rect', 'ellipse', 'poly', 'bezier', 'arc', 'label', 'dim'];
export const STYLE_KEYS = ['textbook', 'classic', 'modern', 'olympiad', 'jee', 'suneung', 'print'];
/* styles that were merged into another (a scene written with one reads as the other) */
export const LEGACY_STYLES = {university: 'textbook'};
export const legacyStyle = s => (typeof s === 'string' && LEGACY_STYLES[s]) || s;
/* the geometric construction's types and the drawn shapes that can be given physics */
export const GEO_TYPES = ['gpoint', 'gline', 'gcircle', 'gpoly', 'gangle'];
export const PHYS_SHAPES = ['rect', 'ellipse', 'poly', 'line'];
/* a conical pendulum's horizontal circle is drawn as an ellipse this many times as high as it is wide (an oblique view) */
export const CONE_TILT = 0.28;
export const ELEMENT_KINDS = ['wire', 'resistor', 'battery', 'cell', 'dc', 'ac', 'capacitor', 'inductor', 'switch', 'diode', 'led', 'bulb', 'ammeter', 'voltmeter', 'galvanometer', 'rheostat', 'dielectric'];
/* round bodies (a ball, a wheel) touch a surface at one point and are joined at their centre */
export const isRound = o => !!o && (o.type === 'ball' || o.type === 'wheel');
/* the moment of inertia of a body about its centre as a fraction of m r² (a wheel's kind; a ball or a block slides) */
export const INERTIA = {disk: 0.5, ring: 1, wheel: 0.75, sphere: 0.4, shell: 2 / 3};
export const PATTERNS = ['solid', 'dashed', 'dotted', 'dashdot', 'none'];
const ID = /^[A-Za-z][A-Za-z0-9_-]{0,23}$/;
const COORD = 200, SPEED = 300, DATA = 1e7;

/* field kinds: [kind, default, min, max] for numbers; texts carry their length */
const num = (d, min, max) => ({k: 'num', d, min, max});
const txt = (d, max) => ({k: 'txt', d, max});
const bool = d => ({k: 'bool', d});
const ref = (types, d = '') => ({k: 'ref', d, types});
const pick = (d, list) => ({k: 'enum', d, list});
const expr = d => ({k: 'expr', d, max: 160});
const params = d => ({k: 'params', d, max: 200});
/* stroke colours and fills of the drawing tools (draw-render.mjs COLOR_HEX): black and grays first, a few colours */
export const COLORS = ['black', 'gray', 'lightgray', 'blue', 'red', 'green', 'orange'];
export const FILLS = ['none', 'white', 'lightgray', 'gray', 'dark', 'hatch', 'dots', 'cross', 'tint'];
const COLOR = pick('black', COLORS), FILL = pick('none', FILLS);
const HEADS = pick('none', ['none', 'end', 'start', 'both']);
const X = num(0, -COORD, COORD), Y = num(0, -COORD, COORD), X1 = X, Y1 = Y, X2 = num(1, -COORD, COORD), Y2 = Y;
const SEG = {x1: X1, y1: Y1, x2: X2, y2: Y2};
const MOTION = {vx: num(0, -SPEED, SPEED), vy: num(0, -SPEED, SPEED), showV: bool(false), vLabel: txt('v_0', 24)};
const BOX = (w, h) => ({x: X, y: Y, w: num(w, 0.05, 400), h: num(h, 0.05, 400)});
const L = (d = '') => txt(d, 40);
const ROT = num(0, -360, 360);
const ON = ref([...SURFACE_TYPES, 'block']);
/* physics given to a drawn shape (draw-physics.mjs rigidWorld) */
export const PHYS_FIELDS = {phys: pick('none', ['none', 'dynamic', 'static']), pmass: num(1, 0.001, 1e4), pvx: num(0, -SPEED, SPEED), pvy: num(0, -SPEED, SPEED), pw: num(0, -200, 200),
  pmu: num(0.3, 0, 2), pe: num(0.2, 0, 1), pfx: num(0, -1e6, 1e6), pfy: num(0, -1e6, 1e6)};
const GP = ref(['gpoint']), GEO_LINE = ['gline'], GEO_PATH = ['gline', 'gcircle', 'gpoly'];
/* a label's or a text box's look, like a word processor's: the face (math: the figure style's face with italic
   variables, as before; serif, sans, mono, hand: plain text in that face, letters upright), italic, bold and underline
   for all of it, the alignment about x (a text box's text). Runs inside a label take \textit{} \textbf{} \mathrm{}
   \mathsf{} \mathtt{} \text{} (draw-render.mjs). A label written before these fields reads as math, plain, centred. */
export const TEXT_FONTS = ['math', 'serif', 'sans', 'mono', 'hand'];
const TEXT_STYLE = {font: pick('math', TEXT_FONTS), italic: bool(false), bold: bool(false), underline: bool(false), align: pick('center', ['left', 'center', 'right'])};
export const FIELDS = {
  /* mechanics */
  block: {x: X, y: Y, w: num(0.4, 0.02, 20), h: num(0.3, 0.02, 20), mass: num(1, 0.001, 10000), label: L(), on: ON, at: num(0, -COORD, COORD), ...MOTION, mu: num(0, 0, 2), look: pick('box', ['box', 'cart', 'car']), rot: ROT},
  ball: {x: X, y: Y, r: num(0.1, 0.01, 5), mass: num(1, 0.001, 10000), label: L(), on: ON, at: num(0, -COORD, COORD), ...MOTION, trail: bool(false)},
  wheel: {x: X, y: Y, r: num(0.2, 0.01, 20), mass: num(1, 0.001, 10000), kind: pick('disk', ['disk', 'ring', 'wheel', 'sphere', 'shell']), label: L(), on: ON, at: num(0, -COORD, COORD), ...MOTION, omega: pick('none', ['none', 'ccw', 'cw']), spokes: num(0, 0, 12), rot: ROT, trail: bool(false)},
  plank: {x: X, y: Y, len: num(2, 0.1, 200), thick: num(0.08, 0.01, 5), rot: ROT, support: pick('fulcrum', ['none', 'pivot', 'hinge', 'fulcrum', 'wall']), at: num(0.5, 0, 1), mass: num(1, 0, 10000), label: L()},
  track: {x: X, y: Y, r: num(1, 0.05, 100), from: num(180, -360, 360), to: num(360, -360, 360), side: pick('out', ['in', 'out']), hatch: bool(true), label: L()},
  floor: {x: X, y: Y, w: num(3, 0.05, 400), mu: num(0, 0, 2), hatch: bool(true)},
  ceiling: {x: X, y: Y, w: num(2, 0.05, 400), hatch: bool(true)},
  wall: {x: X, y: Y, h: num(1, 0.05, 400), side: pick('left', ['left', 'right'])},
  incline: {x: X, y: Y, angle: num(30, 1, 89), length: num(2, 0.1, 200), mu: num(0, 0, 2), flip: bool(false), angleLabel: txt('', 24)},
  pulley: {x: X, y: Y, r: num(0.1, 0.01, 2), mount: ref(['ceiling', 'incline', 'floor', 'wall'])},
  pivot: {x: X, y: Y},
  /* a rough part of a floor or an incline: from (m along the surface from its start) for len (m), with its own μ; the
     solver uses that μ for a body resting on (or tied along) the surface while its foot is on the span */
  rough: {on: ref(SURFACE_TYPES), from: num(0.5, 0, COORD), len: num(1, 0.02, COORD), mu: num(0.3, 0, 2), look: pick('hatch', ['hatch', 'gray', 'dots']), showMu: bool(true), label: txt('', 40)},
  string: {a: ref([...BODY_TYPES, 'pivot']), b: ref([...BODY_TYPES, 'pivot']), over: {k: 'refs', d: [], types: ['pulley'], max: 6}, mode: pick('normal', ['normal', 'conical']), label: txt('', 24)},
  rod: {a: ref(['pivot']), b: ref(BODY_TYPES), mode: pick('normal', ['normal', 'conical']), label: txt('', 24)},
  spring: {a: ref([...BODY_TYPES, ...ANCHOR_TYPES]), b: ref([...BODY_TYPES, ...ANCHOR_TYPES]), k: num(50, 0.01, 1e6), L0: num(1, 0.01, 100), coils: num(10, 3, 30), label: txt('', 24)},
  force: {on: ref(BODY_TYPES), F: num(10, 0, 1e6), angle: num(0, -360, 360), len: num(0.6, 0.05, 20), label: txt('F', 24)},
  /* electromagnetism */
  element: {...SEG, kind: pick('resistor', ELEMENT_KINDS), value: num(10, 0, 1e9), r: num(0, 0, 1e6), closed: bool(true), look: pick('auto', ['auto', 'zigzag', 'box']), route: pick('straight', ['straight', 'hv', 'vh']), label: L()},
  bridge: {...SEG, kind: pick('meter', ['meter', 'pot']), R: num(10, 0.001, 1e6), at: num(0.5, 0, 1), scale: bool(true), label: L()},
  transformer: {x: X, y: Y, h: num(1.2, 0.1, 50), np: num(6, 1, 40), ns: num(10, 1, 40), rot: ROT, label: L()},
  rails: {x: X, y: Y, w: num(3, 0.2, 200), h: num(1, 0.05, 100), at: num(1.8, 0, 200), v: num(2, -1000, 1000), B: num(0.5, 0, 100), R: num(2, 0, 1e6), field: pick('in', ['in', 'out', 'none']), label: L()},
  ground: {x: X, y: Y, label: L()},
  charge: {x: X, y: Y, q: num(1, -1e4, 1e4), r: num(0.12, 0.02, 5), label: L(), mass: num(1, 1e-6, 1e6), ...MOTION, trail: bool(false)},
  plate: {...SEG, q: num(10, -1e5, 1e5), label: L(), marks: bool(true)},
  fieldlines: {n: num(8, 2, 32), levels: num(6, 0, 16), equip: bool(false), arrows: bool(true)},
  field: {...BOX(2, 1.5), kind: pick('B', ['B', 'E']), dir: pick('in', ['in', 'out', 'arrow']), angle: num(0, -360, 360), mag: num(1, 0, 1e9), spacing: num(0.3, 0.05, 20), pattern: pick('dashed', PATTERNS), label: L()},
  cwire: {...SEG, I: num(1, -1e6, 1e6), label: L('I'), arrow: bool(true)},
  current: {x: X, y: Y, r: num(0.08, 0.02, 2), dir: pick('out', ['out', 'in']), I: num(1, -1e6, 1e6), rings: num(0, 0, 6), label: L('I')},
  solenoid: {...BOX(2.4, 0.8), turns: num(8, 2, 40), core: bool(false), showB: bool(false), label: L(), rot: ROT},
  loop: {x: X, y: Y, r: num(0.5, 0.05, 50), ccw: bool(true), tilt: num(0.35, 0.05, 1), label: L('I')},
  magnet: {...BOX(1.6, 0.4), flip: bool(false), showB: bool(false), rot: ROT},
  /* thermodynamics and fluids */
  cylinder: {...BOX(1.2, 1.8), piston: num(0.6, 0.1, 0.95), gas: bool(true), weight: bool(false), heat: pick('none', ['none', 'in', 'out']), label: L(), rot: ROT},
  container: {...BOX(2, 1.6), level: num(0.6, 0, 1), rho: num(1000, 1, 1e5), fill: pick('gray', ['gray', 'lines', 'none']), open: bool(true), label: L()},
  utube: {...BOX(1.6, 1.8), tube: num(0.24, 0.02, 10), left: num(0.45, 0, 1), right: num(0.65, 0, 1), fill: pick('gray', ['gray', 'lines', 'none']), label: L()},
  thermometer: {x: X, y: Y, h: num(1.2, 0.1, 50), level: num(0.5, 0, 1), label: L('T')},
  heater: {x: X, y: Y, w: num(0.8, 0.1, 50), kind: pick('flame', ['flame', 'coil', 'plate']), label: L()},
  gasbox: {...BOX(1.6, 1.2), n: num(18, 0, 200), arrows: bool(true), seed: num(1, 1, 999), label: L()},
  reservoir: {...BOX(2, 0.5), hot: bool(true), label: L('T')},
  engine: {x: X, y: Y, size: num(1, 0.2, 40), kind: pick('engine', ['engine', 'fridge']), th: txt('T_H', 24), tc: txt('T_C', 24), qh: txt('Q_H', 24), qc: txt('Q_C', 24), wl: txt('W', 24)},
  graph: {...BOX(3, 2.2), xmin: num(0, -DATA, DATA), xmax: num(1, -DATA, DATA), ymin: num(0, -DATA, DATA), ymax: num(1, -DATA, DATA), auto: bool(true), xlabel: txt('x', 24), ylabel: txt('y', 24), ticks: bool(false), grid: bool(false), origin: txt('O', 8),
    xt: txt('', 120), yt: txt('', 120), xstep: num(0, 0, DATA), ystep: num(0, 0, DATA)},
  curve: {graph: ref(['graph']), kind: pick('func', ['func', 'isotherm', 'adiabat', 'isobar', 'isochore', 'points', 'param', 'polar', 'ineq']), x1: num(0, -DATA, DATA), x2: num(1, -DATA, DATA), y1: num(1, -DATA, DATA), y2: num(0.5, -DATA, DATA), gamma: num(1.4, 1.01, 3), params: params(''), expr: expr('sin(x)'),
    expr2: expr('sin(t)'), rel: pick('lt', ['lt', 'le', 'gt', 'ge']),
    data: txt('0,0 1,2 3,2 4,0', 240), heads: pick('none', ['none', 'mid', 'end']), pattern: pick('solid', PATTERNS), shade: bool(false), label: L(),
    tangent: bool(false), tx: num(0.5, -DATA, DATA), area: bool(false), a1: num(0, -DATA, DATA), a2: num(1, -DATA, DATA), roots: bool(false), extrema: bool(false), color: COLOR},
  cycle: {graph: ref(['graph']), kind: pick('carnot', ['carnot', 'otto', 'stirling']), v1: num(1, 1e-6, DATA), v2: num(2, 1e-6, DATA), t1: num(600, 1e-6, DATA), t2: num(400, 1e-6, DATA), gamma: num(1.4, 1.01, 3), labels: bool(true), arrows: bool(true), shade: bool(false)},
  /* optics */
  lens: {x: X, y: Y, h: num(1.4, 0.05, 100), f: num(1, -1000, 1000), showF: bool(true), label: L(), rot: ROT},
  mirror: {x: X, y: Y, h: num(1.6, 0.05, 100), f: num(1, -1000, 1000), face: pick('left', ['left', 'right']), showF: bool(true), label: L(), rot: ROT, half: bool(false)},
  prism: {x: X, y: Y, size: num(1.6, 0.05, 100), apex: num(60, 10, 150), n: num(1.5, 1, 4), label: L()},
  slab: {...BOX(2, 0.8), n: num(1.5, 1, 4), label: L()},
  screen: {x: X, y: Y, h: num(1.6, 0.05, 100), rot: ROT, label: L()},
  eye: {x: X, y: Y, size: num(0.5, 0.05, 20), rot: ROT, label: L()},
  source: {x: X, y: Y, kind: pick('bulb', ['bulb', 'laser', 'point', 'sun']), size: num(0.4, 0.02, 50), rot: ROT, label: L()},
  fiber: {...SEG, r: num(0.15, 0.01, 10), angle: num(20, 0, 85), label: L()},
  oarrow: {x: X, y: Y, h: num(0.5, -100, 100), label: L('O'), rays: bool(true), image: bool(true), imageLabel: txt("I", 24)},
  ray: {x: X, y: Y, angle: num(0, -360, 360), len: num(8, 0.1, 400), arrow: bool(true), label: L()},
  slits: {x: X, y: Y, n: num(2, 1, 50), d: num(0.25, 1e-4, 100), a: num(0.05, 1e-4, 100), L: num(1, 1e-3, 1000), lambda: num(550, 10, 1e5), h: num(1.6, 0.1, 100), screen: num(2.4, 0.2, 200), pattern: bool(true), labels: bool(true), waves: bool(true)},
  wavefront: {x: X, y: Y, kind: pick('circular', ['plane', 'circular']), n: num(5, 1, 30), spacing: num(0.3, 0.02, 50), angle: num(0, -360, 360), h: num(1.4, 0.05, 200)},
  /* waves */
  wave: {x: X, y: Y, len: num(4, 0.1, 400), A: num(0.4, 0, 50), lambda: num(1.6, 0.02, 400), phase: num(0, -360, 360), kind: pick('travel', ['travel', 'standing']), n: num(3, 1, 20), ends: pick('none', ['none', 'fixed']),
    showLambda: bool(false), showA: bool(false), envelope: bool(true), axis: bool(true), arrow: bool(false), label: L()},
  pulse: {x: X, y: Y, len: num(4, 0.1, 400), A: num(0.4, -50, 50), width: num(0.6, 0.02, 100), pos: num(0.35, 0, 1), shape: pick('gauss', ['gauss', 'tri', 'square']), dir: pick('right', ['right', 'left', 'none']), axis: bool(true), label: L()},
  interference: {x: X, y: Y, d: num(1, 0.01, 100), lambda: num(0.4, 0.01, 100), n: num(5, 1, 30), nodal: bool(true), labels: bool(true), rot: ROT},
  /* modern physics */
  well: {...BOX(4, 3), kind: pick('infinite', ['infinite', 'finite', 'harmonic', 'barrier', 'step']), L: num(1, 1e-3, 1e4), V0: num(5, 0, 1e6), mass: num(1, 1e-3, 1e6), levels: num(3, 0, 8), psi: pick('psi', ['none', 'psi', 'prob']), E: num(2, 0, 1e6), labels: bool(true)},
  levels: {...BOX(2.6, 3), kind: pick('hydrogen', ['hydrogen', 'custom']), n: num(5, 2, 10), values: txt('-13.6,-3.4,-1.51,-0.85', 160), trans: txt('3-2,2-1', 80), labels: bool(true), showLambda: bool(false)},
  phototube: {...BOX(3, 2), label: L()},
  spacetime: {x: X, y: Y, size: num(3, 0.2, 400), units: num(4, 1, 20), beta: num(0.5, -0.99, 0.99), primed: bool(true), cone: bool(true), grid: bool(false), hyperbola: bool(false), xlabel: txt('x', 24), ylabel: txt('$ct$', 24)},
  worldline: {diagram: ref(['spacetime']), x0: num(0, -100, 100), beta: num(0.5, -0.99, 0.99), ticks: bool(true), tau: num(1, 0.05, 50), label: L()},
  frames: {x: X, y: Y, size: num(1.2, 0.1, 100), gap: num(1.8, 0, 200), label: L('v')},
  nucleus: {x: X, y: Y, r: num(0.3, 0.02, 20), np: num(6, 0, 60), nn: num(6, 0, 60), label: L()},
  particle: {x: X, y: Y, kind: pick('electron', ['electron', 'positron', 'proton', 'neutron', 'alpha', 'photon', 'neutrino']), arrow: bool(false), angle: num(0, -360, 360), len: num(0.8, 0, 50), label: L()},
  /* a potential typed as a function V(x) (eV, x in nm) with parameters: its bound states and a scattering state found
     numerically (draw-physics.mjs qpotModel) */
  qpot: {...BOX(4.4, 3), V: expr('abs(x) < a/2 ? 0 : V0'), params: params('a=1 [0.2, 3], V0=5 [0, 20]'), xmin: num(-1.5, -1e4, 1e4), xmax: num(1.5, -1e4, 1e4), mass: num(1, 1e-3, 1e6),
    showV: bool(true), levels: num(3, 0, 10), psi: pick('psi', ['none', 'psi', 'prob']), E: num(0, 0, 1e6), tplot: bool(false), Emax: num(0, 0, 1e6), labels: bool(true)},
  /* general marks */
  label: {x: X, y: Y, text: txt('', 240), size: num(16, 8, 48), box: bool(false), rot: ROT, color: COLOR, ...TEXT_STYLE},
  dim: {x1: X, y1: Y, x2: X, y2: Y, offset: num(0.15, -10, 10), text: txt('', 40)},
  arc: {x: X, y: Y, r: num(0.3, 0.02, 20), from: num(0, -360, 360), to: num(30, -360, 360), text: txt('', 24), arrow: bool(false), color: COLOR, pattern: pick('solid', PATTERNS)},
  axes: {x: X, y: Y, lx: num(1, 0, 100), ly: num(1, 0, 100), xlabel: txt('x', 12), ylabel: txt('y', 12)},
  line: {x1: X, y1: Y, x2: X, y2: Y, pattern: pick('dashed', PATTERNS), heads: pick('none', ['none', 'end', 'start', 'both', 'mid']), color: COLOR},
  vector: {...SEG, label: L(), width: num(1.6, 0.3, 6), head: pick('auto', ['auto', 'filled', 'open', 'stealth', 'none'])},
  region: {...BOX(1, 0.8), shape: pick('rect', ['rect', 'ellipse']), fill: pick('gray', ['none', 'gray', 'hatch', 'dots', 'cross', 'lines', 'dark']), pattern: pick('solid', PATTERNS), label: L(), rot: ROT},
  point: {x: X, y: Y, label: L(), filled: bool(true)},
  panel: {...BOX(2, 1.5), caption: txt('(가)', 24), frame: bool(false)},
  brace: {...SEG, kind: pick('brace', ['brace', 'bracket']), offset: num(0.12, -10, 10), text: txt('', 40)},
  callout: {x: X, y: Y, x2: num(1, -COORD, COORD), y2: num(0.6, -COORD, COORD), text: txt('', 60), end: pick('dot', ['dot', 'arrow', 'none'])},
  parrows: {...SEG, n: num(5, 1, 40), len: num(0.4, 0.02, 50), dir: pick('out', ['in', 'out']), label: L()},
  /* basic drawing (the editor's drawing tools): plain shapes with a stroke colour, a fill and a line pattern */
  rect: {...BOX(1, 0.6), r: num(0, 0, 100), color: COLOR, fill: FILL, pattern: pick('solid', PATTERNS), rot: ROT},
  ellipse: {...BOX(1, 0.6), color: COLOR, fill: FILL, pattern: pick('solid', PATTERNS), rot: ROT},
  poly: {pts: {k: 'pts', d: [[0, 0], [1, 0]], max: 400}, closed: bool(false), smooth: bool(false), color: COLOR, fill: FILL, pattern: pick('solid', PATTERNS), heads: HEADS},
  bezier: {x1: X, y1: Y, cx1: num(0.3, -COORD, COORD), cy1: num(0.5, -COORD, COORD), cx2: num(0.7, -COORD, COORD), cy2: num(0.5, -COORD, COORD), x2: X2, y2: Y, color: COLOR, pattern: pick('solid', PATTERNS), heads: HEADS},
  /* a spring, a string or a rod between drawn shapes given physics (or from one to a fixed point) */
  joint: {a: ref(PHYS_SHAPES), b: ref(PHYS_SHAPES), kind: pick('spring', ['spring', 'string', 'rod']), ax: num(0, -COORD, COORD), ay: num(0, -COORD, COORD), bx: num(0, -COORD, COORD), by: num(0, -COORD, COORD),
    k: num(50, 0.01, 1e6), L0: num(0, 0, 400), damp: num(0, 0, 1e4), coils: num(10, 3, 30), label: txt('', 24)},
  /* diagrams: a neural network (layers of nodes, every node joined to every node of the next layer; weights typed as
     matrices make the edges thicker or coloured, w_ij written on them), and block diagrams (boxes joined by arrows) */
  nnet: {...BOX(3.2, 2.2), layers: txt('2,3,1', 40), inLabels: txt('x_1,x_2', 120), outLabels: txt('\\hat{y}', 80), act: txt('\\sigma', 24), bias: bool(false), weights: txt('', 600),
    wstyle: pick('none', ['none', 'width', 'color']), wlabels: bool(false), nodeR: num(0.13, 0.02, 5), label: L()},
  fbox: {x: X, y: Y, w: num(1, 0.05, 100), h: num(0.6, 0.05, 100), shape: pick('rect', ['rect', 'round', 'circle', 'diamond', 'sum']), text: txt('', 80), fill: FILL},
  farrow: {a: ref(['fbox']), b: ref(['fbox']), route: pick('straight', ['straight', 'hv', 'vh']), label: L(), sign: txt('', 4), pattern: pick('solid', PATTERNS)},
  /* the geometric construction */
  gpoint: {x: X, y: Y, kind: pick('free', ['free', 'on', 'mid', 'inter']), a: ref(['gpoint', ...GEO_PATH]), b: ref(['gpoint', ...GEO_PATH]), n: num(0, 0, 1), label: L(), show: bool(true), color: COLOR},
  gline: {a: GP, b: GP, kind: pick('segment', ['segment', 'line', 'ray', 'perp', 'par']), base: ref(GEO_LINE), measure: bool(false), label: L(), color: COLOR, pattern: pick('solid', PATTERNS)},
  gcircle: {c: GP, p: GP, r: num(1, 0.001, 400), measure: bool(false), label: L(), color: COLOR, fill: FILL, pattern: pick('solid', PATTERNS)},
  gpoly: {pts: {k: 'refs', d: [], types: ['gpoint'], max: 24}, measure: bool(false), label: L(), color: COLOR, fill: pick('tint', FILLS), pattern: pick('solid', PATTERNS)},
  gangle: {a: GP, b: GP, c: GP, r: num(0.3, 0.02, 20), measure: bool(true), label: L()}
};
for (const t of PHYS_SHAPES) Object.assign(FIELDS[t], PHYS_FIELDS);
/* fields whose default became off (a particle's arrow, a wave's λ and A marks, the levels' wavelengths): an object
   written before, without the field, keeps what it showed */
const LEGACY_ON = {particle: {arrow: raw => (typeof raw.len === 'number' ? raw.len : 0.8) > 0}, wave: {showLambda: () => true, showA: () => true}, levels: {showLambda: () => true}};
/* every object also has a line weight and a label size (multiples of the style's), and can be locked against dragging */
export const COMMON_FIELDS = {lw: num(1, 0.2, 5), ls: num(1, 0.3, 4), lock: bool(false), style: pick('', ['', ...STYLE_KEYS])};
for (const t of Object.keys(FIELDS)) Object.assign(FIELDS[t], COMMON_FIELDS);
export const TYPES = Object.keys(FIELDS);
/* the types that turn by their field rot (degrees, anticlockwise) about their centre */
export const ROTATABLE = TYPES.filter(t => 'rot' in FIELDS[t]);
/* the palette's domains (draw.js tabs); every type is in one */
export const DOMAINS = {
  mech: ['block', 'ball', 'wheel', 'floor', 'ceiling', 'wall', 'incline', 'rough', 'track', 'pulley', 'pivot', 'plank', 'string', 'rod', 'spring', 'force'],
  em: ['element', 'bridge', 'transformer', 'rails', 'ground', 'charge', 'plate', 'fieldlines', 'field', 'cwire', 'current', 'solenoid', 'loop', 'magnet'],
  thermo: ['cylinder', 'container', 'utube', 'thermometer', 'heater', 'gasbox', 'reservoir', 'engine', 'cycle', 'curve'],
  optics: ['lens', 'mirror', 'prism', 'slab', 'oarrow', 'ray', 'slits', 'wavefront', 'screen', 'eye', 'source', 'fiber'],
  waves: ['wave', 'pulse', 'interference'],
  modern: ['well', 'qpot', 'levels', 'phototube', 'spacetime', 'worldline', 'frames', 'nucleus', 'particle'],
  general: ['label', 'dim', 'arc', 'axes', 'line', 'vector', 'region', 'point', 'graph', 'panel', 'brace', 'callout', 'parrows', 'rect', 'ellipse', 'poly', 'bezier', 'joint', 'nnet', 'fbox', 'farrow'],
  geo: GEO_TYPES
};
export const TYPE_DOMAIN = Object.fromEntries(Object.entries(DOMAINS).flatMap(([d, list]) => list.map(t => [t, d])));
/* references that must name an existing object, and which must not be the same */
const REQUIRED_REFS = {rough: ['on'], farrow: ['a', 'b'], string: ['a', 'b'], rod: ['a', 'b'], spring: ['a', 'b'], force: ['on'], curve: ['graph'], cycle: ['graph'], worldline: ['diagram'], joint: ['a'], gline: ['a'], gcircle: ['c'], gangle: ['a', 'b', 'c']};
/* references a geometric object needs as it is set */
const geoNeeds = o => o.type === 'gpoint' ? (o.kind === 'on' ? ['a'] : o.kind === 'mid' ? ['a'] : o.kind === 'inter' ? ['a', 'b'] : [])
  : o.type === 'gline' ? (o.kind === 'perp' || o.kind === 'par' ? ['a', 'base'] : ['a', 'b']) : [];
export const isBody = o => !!o && BODY_TYPES.includes(o.type);
/* a drawn shape given physics */
export const isPhysShape = o => !!o && PHYS_SHAPES.includes(o.type) && !!o.phys && o.phys !== 'none';
export const isSeg = o => !!o && 'x1' in (FIELDS[o.type] || {});

/* ── a small, safe expression language for plotted functions and potentials: numbers, x, pi, e, + − * / ^, implicit
   products (2x, 3sin(x), a x), the functions below, comparisons (< <= > >= == !=), && and ||, and the conditional
   c ? a : b (so a piecewise V(x) reads "x < 0 ? 0 : (x < a ? V0 : 0)"); a true comparison is 1, a false one 0. Names
   other than x are the parameters the caller lists (a curve's or a potential's params). Compiled to closures; nothing
   is ever evaluated as code. ── */
const FN = {sin: Math.sin, cos: Math.cos, tan: Math.tan, asin: Math.asin, acos: Math.acos, atan: Math.atan, sinh: Math.sinh, cosh: Math.cosh, tanh: Math.tanh,
  exp: Math.exp, ln: Math.log, log: Math.log10, sqrt: Math.sqrt, abs: Math.abs, sign: Math.sign, floor: Math.floor, ceil: Math.ceil, sec: x => 1 / Math.cos(x), csc: x => 1 / Math.sin(x), cot: x => 1 / Math.tan(x),
  step: x => x >= 0 ? 1 : 0};
export const EXPR_FUNCTIONS = Object.keys(FN);
const RESERVED = new Set(['x', 'pi', 'e', ...EXPR_FUNCTIONS]);
/* the variable of a curve's formula: t for a parametric or a polar curve, else x */
export const curveVar = kind => kind === 'param' || kind === 'polar' ? 't' : 'x';
/* an unknown run of letters split into known names, longest first ("ax" → a x, "kx" → k x); null if it does not split */
function splitName(id, known) {
  const out = []; let i = 0;
  while (i < id.length) { let hit = ''; for (const k of known) if (k.length > hit.length && id.startsWith(k, i)) hit = k; if (!hit) return null; out.push(hit); i += hit.length; }
  return out;
}
export function compileExpr(src, vars = ['x']) {
  const s = String(src ?? '').replace(/π/g, 'pi').replace(/·|×/g, '*').replace(/−/g, '-').replace(/≤/g, '<=').replace(/≥/g, '>=').replace(/≠/g, '!=').trim();
  if (!s || s.length > 160) return null;
  const known = [...vars, ...EXPR_FUNCTIONS, 'pi', 'e'];
  const toks = [], re = /\s*(?:(\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)|([A-Za-z][A-Za-z0-9_]*)|(\*\*|<=|>=|==|!=|&&|\|\||[-+*/^(),<>?:]))/y;
  let m, k = 0;
  while (k < s.length) {
    re.lastIndex = k; m = re.exec(s); if (!m) return null; k = re.lastIndex;
    if (m[1] !== undefined) toks.push({n: +m[1]});
    else if (m[2] !== undefined) {
      const id = m[2];
      if (known.includes(id)) toks.push({id});
      else { const letters = /^[A-Za-z]+/.exec(id)[0], parts = splitName(letters, known); if (!parts) return null; parts.forEach(p => toks.push({id: p})); k -= id.length - letters.length; }
    } else toks.push({op: m[3] === '**' ? '^' : m[3]});
    if (/^\s*$/.test(s.slice(k))) break;
  }
  let i = 0, depth = 0;
  const peek = () => toks[i], op = c => toks[i] && toks[i].op === c;
  const fail = () => { throw new Error('expr'); };
  const ternary = () => { const c = orP(); if (!op('?')) return c; i++; const a = ternary(); if (!op(':')) fail(); i++; const b = ternary(); return x => (c(x) ? a(x) : b(x)); };
  const orP = () => { let a = andP(); while (op('||')) { i++; const b = andP(), A = a; a = x => (A(x) || b(x)) ? 1 : 0; } return a; };
  const andP = () => { let a = cmpP(); while (op('&&')) { i++; const b = cmpP(), A = a; a = x => (A(x) && b(x)) ? 1 : 0; } return a; };
  const CMP = {'<': (a, b) => a < b, '<=': (a, b) => a <= b, '>': (a, b) => a > b, '>=': (a, b) => a >= b, '==': (a, b) => a === b, '!=': (a, b) => a !== b};
  const cmpP = () => { const a = exprP(); const t = peek(); if (t && CMP[t.op]) { i++; const b = exprP(), c = CMP[t.op]; return x => c(a(x), b(x)) ? 1 : 0; } return a; };
  const exprP = () => { let a = term(); while (op('+') || op('-')) { const o = toks[i++].op, b = term(), A = a; a = o === '+' ? x => A(x) + b(x) : x => A(x) - b(x); } return a; };
  const startsAtom = t => t && (t.n !== undefined || t.id !== undefined || t.op === '(');
  const term = () => { let a = unary(); for (;;) { if (op('*') || op('/')) { const o = toks[i++].op, b = unary(), A = a; a = o === '*' ? x => A(x) * b(x) : x => A(x) / b(x); } else if (startsAtom(peek())) { const b = power(), A = a; a = x => A(x) * b(x); } else return a; } };
  const unary = () => { if (op('-')) { i++; const a = unary(); return x => -a(x); } if (op('+')) { i++; return unary(); } return power(); };
  const power = () => { const a = atom(); if (op('^')) { i++; const b = unary(); return x => Math.pow(a(x), b(x)); } return a; };
  const atom = () => {
    if (++depth > 60) fail();
    const t = toks[i++]; let r;
    if (!t) fail();
    if (t.n !== undefined) r = () => t.n;
    else if (t.op === '(') { const a = ternary(); if (!op(')')) fail(); i++; r = a; }
    else if (t.id !== undefined) {
      const id = t.id;
      if (FN[id] && !vars.includes(id)) { let a; if (op('(')) { i++; a = ternary(); if (!op(')')) fail(); i++; } else a = power(); const f = FN[id]; r = x => f(a(x)); }
      else if (vars.includes(id)) { const j = vars.indexOf(id); r = x => (Array.isArray(x) ? x[j] : j === 0 ? x : NaN); }
      else if (id === 'pi') r = () => Math.PI;
      else if (id === 'e') r = () => Math.E;
      else fail();
    } else fail();
    depth--; return r;
  };
  try { const f = ternary(); if (i !== toks.length) return null; return f; } catch (e) { return null; }
}
/** Parameters of a function or a potential: "a = 1, V0 = 5 [0, 20]" — a name (a letter, then letters, digits or _,
 *  up to 8; not x, pi, e or a function), its value and an optional slider range [min, max] (else from the value).
 *  Returns the list (at most 8) or null when the text does not read. */
export function parseParams(text) {
  const s = String(text ?? '').trim(), out = [];
  if (!s) return out;
  const NUM = '[-+]?(?:\\d+\\.?\\d*|\\.\\d+)(?:[eE][-+]?\\d+)?';
  const re = new RegExp(`\\s*([A-Za-z][A-Za-z0-9_]{0,7})\\s*=\\s*(${NUM})(?:\\s*\\[\\s*(${NUM})\\s*[,~]\\s*(${NUM})\\s*\\])?\\s*(?:[,;]|$)`, 'y');
  let k = 0;
  while (k < s.length) {
    re.lastIndex = k; const m = re.exec(s); if (!m || re.lastIndex === k) return null; k = re.lastIndex;
    const name = m[1], value = +m[2];
    if (RESERVED.has(name) || out.some(p => p.name === name) || !Number.isFinite(value)) return null;
    let min = m[3] !== undefined ? +m[3] : value > 0 ? 0 : value < 0 ? 2 * value : -1, max = m[4] !== undefined ? +m[4] : value > 0 ? 2 * value : value < 0 ? 0 : 1;
    if (!(max > min)) return null;
    out.push({name, value, min, max});
    if (out.length > 8) return null;
  }
  return out;
}
/** the parameters as text again (what a slider writes back) */
export const paramsText = list => list.map(p => `${p.name}=${+p.value.toPrecision(6)} [${+p.min.toPrecision(6)}, ${+p.max.toPrecision(6)}]`).join(', ');
/** a function of x with an object's parameters bound (a curve's expr, a potential's V): null if it does not compile */
export function boundExpr(src, params, v = 'x') {
  const list = typeof params === 'string' ? parseParams(params) : params || [];
  if (!list) return null;
  const fn = compileExpr(src, [v, ...list.map(p => p.name)]); if (!fn) return null;
  const vals = list.map(p => p.value);
  return x => fn([x, ...vals]);
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
  /* optional: the values written on the figure (2 kg, 30°, 10 Ω …), and the printed width in mm (0: the style's) */
  if (input.values !== undefined) { if (typeof input.values === 'boolean') { if (input.values) scene.values = true; } else if (!lenient) err('bad_bool', null, 'values'); }
  if (input.printW !== undefined && input.printW !== 0) { const p = top('printW', 0, 20, 400); if (p) scene.printW = p; }
  if (input.style !== undefined) { const sk = legacyStyle(input.style); if (sk !== input.style) notes.push({code: 'style_merged', from: input.style, to: sk}); if (STYLE_KEYS.includes(sk)) scene.style = sk; else if (lenient) notes.push({code: 'style_dropped'}); else err('bad_enum', null, 'style'); }
  /* the drawn rigid shapes: gravity off, air drag */
  if (input.gravityOn !== undefined) { if (typeof input.gravityOn === 'boolean') { if (!input.gravityOn) scene.gravityOn = false; } else if (!lenient) err('bad_bool', null, 'gravityOn'); }
  if (input.drag !== undefined && input.drag !== 0) { const d = top('drag', 0, 0, 50); if (d) scene.drag = d; }
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
    /* fields whose default changed to off: a scene written before keeps what it showed */
    const legacy = LEGACY_ON[type];
    if (legacy) for (const [k, on] of Object.entries(legacy)) if (raw[k] === undefined) o[k] = on(raw);
    for (const [k, f] of Object.entries(F)) {
      const v = k === 'style' ? legacyStyle(raw[k]) : raw[k];
      if (v === undefined || v === null) { if (!(k in o)) o[k] = Array.isArray(f.d) ? [] : f.d; continue; }
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
      } else if (f.k === 'params') {
        const t = typeof v === 'string' ? cleanText(v, f.max, false) : null;
        if (t == null || !parseParams(t)) { if (lenient) { o[k] = f.d; notes.push({code: 'params_dropped', id, field: k}); continue; } err('bad_params', id, k); bad = true; continue; }
        o[k] = t;
      } else if (f.k === 'pts') {
        const ok = Array.isArray(v) && v.length >= 2 && v.length <= f.max && v.every(q => Array.isArray(q) && q.length === 2 && q.every(c => typeof c === 'number' && Number.isFinite(c) && Math.abs(c) <= COORD));
        if (!ok) { err('bad_points', id, k); bad = true; continue; }
        o[k] = v.map(q => [q[0], q[1]]);
      } else if (f.k === 'expr') {
        const t = typeof v === 'string' ? cleanText(v, f.max, false) : null;
        const pl = 'params' in F ? parseParams(typeof raw.params === 'string' ? raw.params : F.params.d) || [] : [];
        const v0 = type === 'curve' ? curveVar(raw.kind) : 'x';
        if (t == null || !compileExpr(t, [v0, ...pl.map(q => q.name)])) { if (lenient || (type === 'curve' && k === 'expr2' && v0 === 'x')) { o[k] = f.d; if (!(type === 'curve' && k === 'expr2' && v0 === 'x')) notes.push({code: 'expr_dropped', id, field: k}); continue; } err('bad_expr', id, k); bad = true; continue; }
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
      if ((o.type === 'string' || o.type === 'spring' || o.type === 'joint' || o.type === 'farrow') && o.a && o.a === o.b) { err('same_ends', o.id); bad = true; }
      if (!bad && o.type === 'nnet' && !nnLayers(o.layers)) { if (lenient) { o.layers = '2,3,1'; notes.push({code: 'clamped', id: o.id, field: 'layers'}); } else { err('bad_layers', o.id, 'layers'); bad = true; } }
      /* a geometric object names what it is built from */
      if (!bad && GEO_TYPES.includes(o.type)) {
        for (const k of geoNeeds(o)) if (!o[k]) { err('missing_ref', o.id, k); bad = true; }
        if (o.type === 'gpoint' && o.kind === 'mid' && !o.b && byId.get(o.a)?.type !== 'gline') { err('missing_ref', o.id, 'b'); bad = true; }
        if (o.type === 'gpoint' && o.kind === 'inter' && (byId.get(o.a)?.type === 'gpoint' || byId.get(o.b)?.type === 'gpoint')) { err('bad_ref', o.id, 'a'); bad = true; }
        if (o.type === 'gpoint' && o.kind === 'mid' && byId.get(o.a)?.type !== 'gpoint' && byId.get(o.a)?.type !== 'gline') { err('bad_ref', o.id, 'a'); bad = true; }
        if (o.type === 'gpoly' && o.pts.length < 3) { err('bad_points', o.id, 'pts'); bad = true; }
      }

      /* a body on a block: not on itself, and the blocks under it end on a floor or an incline (no loop) */
      if (isBody(o) && o.on && !bad && byId.get(o.on)?.type === 'block') {
        let cur = o, seen = new Set([o.id]), okStack = false;
        for (let k = 0; k < 8; k++) { const s = byId.get(cur.on); if (!s) break; if (s.type !== 'block') { okStack = true; break; } if (seen.has(s.id)) break; seen.add(s.id); if (!s.on) { okStack = true; break; } cur = s; }
        if (!okStack) { if (lenient) { o.on = ''; notes.push({code: 'ref_dropped', id: o.id, field: 'on'}); } else { err('bad_stack', o.id, 'on'); bad = true; } }
      }
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
  /* a construction that refers to itself (a point on a line through it) cannot be computed */
  const cyc = computeGeometry({objects: keep}).cyclic;
  if (cyc.size) { for (const id of cyc) err('geo_cycle', id); if (lenient) keep = keep.filter(o => !cyc.has(o.id)); }
  scene.objects = keep;
  /* bodies on bodies: the lower ones first */
  for (let pass = 0; pass < 3; pass++) for (const o of scene.objects) if (isBody(o) && o.on) placeOnSurface(scene, o);
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

/** The editor's undo history: states (JSON text of the scene) before each change, at most `limit` steps back.
 *  record(before) after a change that left `before` behind; undo(current) and redo(current) return the state to show
 *  (or null). A drag or a slider gesture records once, at its end, with the state from its start. */
export function createHistory(limit = 250) {
  const past = [], future = [];
  return {
    limit,
    record(before) { if (typeof before !== 'string') before = JSON.stringify(before); if (past[past.length - 1] === before) return; past.push(before); if (past.length > limit) past.shift(); future.length = 0; },
    undo(current) { if (!past.length) return null; future.push(typeof current === 'string' ? current : JSON.stringify(current)); return past.pop(); },
    redo(current) { if (!future.length) return null; past.push(typeof current === 'string' ? current : JSON.stringify(current)); return future.pop(); },
    get canUndo() { return past.length > 0; }, get canRedo() { return future.length > 0; },
    get size() { return past.length; }, clear() { past.length = 0; future.length = 0; }
  };
}

/* ── the editor's document (draw.js): which figure is open and what it is linked to ──
   Every figure the editor has open has an identity of its own (uid). The storage files it saves to (store: the JSON
   and SVG file ids, the updated_at last seen, the name and folder) and the shared project it updates (share) belong to
   that identity only. Whatever starts or loads another figure (모두 지우기, a template or a blank figure, JSON import,
   a figure saved in this browser, a photo, a new figure from AI, 복제, 다른 이름으로 저장) gets a new identity with no
   links; opening a storage file links the new identity to that file, opening a shared figure to that project.
   saved: the scene's signature when it was last saved or loaded; changes: edits since then. */
export function sceneSig(scene) {
  const s = JSON.stringify(scene ?? null); let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193); }
  return (h >>> 0).toString(36) + '.' + s.length.toString(36);
}
export const newUid = (rand = Math.random) => 'f' + Date.now().toString(36) + Math.floor(rand() * 2 ** 32).toString(36).padStart(7, '0');
/** the document for a figure that was just started or loaded: action 'new' (no links, clean), 'storage' ({store}),
 *  'share' ({share}), 'copy' (no links, not saved yet: 복제), 'saved-as' ({store}: a new identity on new files),
 *  'draft' (a recovery draft reopened: its own uid, store and share, unsaved) */
export function docFor(action, scene, {store = null, share = null, uid = '', changes = 1} = {}) {
  /* a recovery draft comes back as it was: its identity and links, with its changes not saved */
  if (action === 'draft') return {uid: uid || newUid(), store: store || null, share: share || null, saved: '', changes: Math.max(1, changes)};
  const clean = action !== 'copy';
  return {uid: newUid(), store: action === 'storage' || action === 'saved-as' ? store : null, share: action === 'share' ? share : null, saved: clean ? sceneSig(scene) : '', changes: clean ? 0 : 1};
}
/** after a change: one more edit */
export const docEdited = doc => ({...doc, changes: (doc.changes || 0) + 1});
/** after a save to the same identity: linked to the files, clean */
export const docSaved = (doc, scene, store) => ({...doc, store, saved: sceneSig(scene), changes: 0});
/** what the indicator shows: 'saved' (in storage, unchanged), 'unsaved' (changed since saved or loaded, or never
 *  saved after 복제), 'new' (not in storage, unchanged since it was started); changes: the edits counted */
export function docState(doc, scene) {
  const dirty = !doc || sceneSig(scene) !== doc.saved;
  return {dirty, state: dirty ? 'unsaved' : doc.store ? 'saved' : 'new', changes: dirty ? Math.max(1, doc?.changes || 0) : 0};
}
/** recovery drafts (localStorage): the newest unsaved figure of each identity, at most `max`, newest first */
export function keepDraft(list, doc, scene, t = Date.now(), max = 5) {
  const rest = (Array.isArray(list) ? list : []).filter(d => d && d.uid !== doc.uid);
  return [{uid: doc.uid, t, title: scene.title || '', scene, store: doc.store || null, share: doc.share || null, changes: doc.changes || 1}, ...rest].slice(0, max);
}
export const dropDraft = (list, uid) => (Array.isArray(list) ? list : []).filter(d => d && d.uid !== uid);

/** where a new object goes so it does not cover the others: the offset (whole steps, the nearest ring first, down and
 *  to the right before the other ways) at which its box overlaps none of `boxes` and stays inside `view`; when every
 *  place is taken, a cascade of `nth` steps down and to the right */
export function freeSpot(box, boxes, step, view, nth = 0, rings = 6) {
  const eps = 1e-9, hits = (dx, dy) => boxes.some(b => b && box.x + dx < b.x + b.w - eps && box.x + dx + box.w > b.x + eps && box.y + dy < b.y + b.h - eps && box.y + dy + box.h > b.y + eps);
  const inside = (dx, dy) => !view || (box.x + dx >= view.x - eps && box.x + dx + box.w <= view.x + view.w + eps && box.y + dy >= view.y - eps && box.y + dy + box.h <= view.y + view.h + eps);
  const cand = [];
  for (let i = -rings; i <= rings; i++) for (let j = -rings; j <= rings; j++) cand.push([i, j]);
  cand.sort((a, b) => Math.max(Math.abs(a[0]), Math.abs(a[1])) - Math.max(Math.abs(b[0]), Math.abs(b[1])) || (b[0] >= 0 && b[1] <= 0) - (a[0] >= 0 && a[1] <= 0) || Math.abs(a[0] - a[1] * -1) - Math.abs(b[0] - b[1] * -1) || Math.abs(a[0]) + Math.abs(a[1]) - Math.abs(b[0]) - Math.abs(b[1]));
  for (const [i, j] of cand) { const dx = i * step, dy = j * step; if (inside(dx, dy) && !hits(dx, dy)) return {dx, dy}; }
  return {dx: nth * step, dy: -nth * step};
}

/** a force added to a body after the ones it has: its weight first (mg, down), then the normal force (N, off the
 *  surface it rests on), the tension (T, along its string or rod), friction (f, against its motion or the way it
 *  would slide), then F; never on top of a force it already has (turned on by 30° until the angle is free) */
export function nextForce(scene, id) {
  const byId = new Map(scene.objects.map(o => [o.id, o])), b = byId.get(id);
  if (!isBody(b)) return null;
  const g = scene.g || 9.8, mg = b.mass * g, have = scene.objects.filter(o => o.type === 'force' && o.on === id);
  const used = new Set(have.map(o => String(o.label).replace(/^\$|\$$/g, '')));
  const ang = v => Math.round(Math.atan2(v.y, v.x) * 18000 / Math.PI) / 100, r3 = v => +(+v).toPrecision(3);
  const surf = b.on ? byId.get(b.on) : null, fr = surf ? surfaceFrame(surf, scene) : null;
  const link = scene.objects.find(o => (o.type === 'string' || o.type === 'rod') && (o.a === id || o.b === id));
  let tdir = null;
  if (link?.type === 'string') { const P = stringPath(scene, link); if (P) { const [p, q] = link.a === id ? P.segs[0] : [...P.segs[P.segs.length - 1]].reverse(); if (vec.len(vec.sub(q, p)) > 1e-9) tdir = vec.unit(vec.sub(q, p)); } }
  else if (link) { const far = byId.get(link.a === id ? link.b : link.a); if (far) { const d = vec.sub(isBody(far) ? bodyPose(scene, far) : far, bodyPose(scene, b)); if (vec.len(d) > 1e-9) tdir = vec.unit(d); } }
  const cands = [{label: 'mg', angle: -90, F: mg}];
  if (fr) cands.push({label: 'N', angle: ang(fr.n), F: mg * Math.max(0, fr.n.y)});
  if (tdir) cands.push({label: 'T', angle: ang(tdir), F: 10});
  if (fr) {
    const v = vec.dot({x: b.vx, y: b.vy}, fr.u);
    let s = v ? -Math.sign(v) : 0;
    if (!s && tdir) s = -Math.sign(vec.dot(tdir, fr.u));
    if (!s && Math.abs(fr.u.y) > 1e-9) s = Math.sign(fr.u.y);
    const dir = s ? vec.mul(fr.u, s) : vec.mul(fr.u, -1), N = mg * Math.max(0, fr.n.y);
    cands.push({label: 'f', angle: ang(dir), F: (fr.mu > 0 ? fr.mu : 0.2) * N || 1});
  }
  let pick = cands.find(c => !used.has(c.label));
  if (!pick) { let n = 1, L = 'F'; while (used.has(L)) L = `F_${++n}`; pick = {label: L, angle: 0, F: 10}; }
  let a = pick.angle;
  const clash = x => have.some(o => Math.abs((((o.angle - x) % 360) + 540) % 360 - 180) < 5);
  for (let k = 0; k < 12 && clash(a); k++) a = a + 30;
  a = ((a + 540) % 360) - 180;
  return {label: pick.label, angle: Math.round(a * 100) / 100, F: r3(Math.max(0, pick.F))};
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
export function surfaceFrame(s, scene, depth = 0) {
  if (s.type === 'floor') return {p0: {x: s.x, y: s.y}, u: {x: 1, y: 0}, n: {x: 0, y: 1}, length: s.w, mu: s.mu};
  if (s.type === 'block') {
    /* the top face of a block (a body stacked on it): from its upper left corner, μ of that face */
    const p = scene && depth < 8 ? bodyPose(scene, s, depth + 1) : {x: s.x, y: s.y, angle: (s.rot || 0) * Math.PI / 180};
    const u = {x: Math.cos(p.angle), y: Math.sin(p.angle)}, n = {x: -u.y, y: u.x};
    return {p0: {x: p.x - u.x * s.w / 2 + n.x * s.h / 2, y: p.y - u.y * s.w / 2 + n.y * s.h / 2}, u, n, length: s.w, mu: s.mu, block: s.id};
  }
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
export const bodyHalfHeight = b => isRound(b) ? b.r : b.h / 2;
export const bodyHalfWidth = b => isRound(b) ? b.r : b.w / 2;
/** put a body that rests on a surface at its place on it (x, y from `at`) */
export function placeOnSurface(scene, b) {
  const s = scene.objects.find(o => o.id === b.on);
  if (!s) { b.on = ''; return b; }
  const f = surfaceFrame(s, scene), c = vec.add(vec.add(f.p0, vec.mul(f.u, b.at)), vec.mul(f.n, bodyHalfHeight(b)));
  b.x = c.x; b.y = c.y;
  return b;
}
/** the body's centre and the angle of its base (radians) */
export function bodyPose(scene, b, depth = 0) {
  if (b.on) {
    const s = scene.objects.find(o => o.id === b.on);
    if (s) { const f = surfaceFrame(s, scene, depth), c = vec.add(vec.add(f.p0, vec.mul(f.u, b.at)), vec.mul(f.n, bodyHalfHeight(b))); return {x: c.x, y: c.y, angle: b.type === 'block' ? Math.atan2(f.u.y, f.u.x) : 0}; }
  }
  return {x: b.x, y: b.y, angle: b.type === 'block' ? (b.rot || 0) * Math.PI / 180 : 0};
}
/* the point where a string or a spring meets a body: the middle of the face looking towards `toward` (a block), or the
   centre (a ball, a wheel) */
export function attachPoint(scene, b, toward, pose = bodyPose(scene, b)) {
  if (isRound(b)) return {x: pose.x, y: pose.y};
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

/* ── the geometric construction: every object resolved from what it refers to, in dependency order ──
   computeGeometry(scene) → {get(id), cyclic: Set of ids that depend on themselves}; get gives
     point  {k:'pt', x, y}                      line {k:'line', p, d (direction, |d| = the segment's length), t0, t1}
     circle {k:'circ', c, r}                    poly {k:'poly', pts}        angle {k:'ang', a, b, c, deg}
   or null when it cannot be computed (two parallel lines do not meet, a point is missing). A segment runs t ∈ [0, 1],
   a ray [0, ∞), a line (−∞, ∞). */
const GEO_INF = 1e9;
export function geoLinePoint(L, t) { return {x: L.p.x + L.d.x * t, y: L.p.y + L.d.y * t}; }
/* the nearest point to q on a line, a circle or a polygon's edges */
export function geoProject(G, q) {
  if (!G) return null;
  if (G.k === 'line') { const dd = G.d.x * G.d.x + G.d.y * G.d.y; if (dd < 1e-18) return {...G.p}; const t = Math.max(G.t0, Math.min(G.t1, ((q.x - G.p.x) * G.d.x + (q.y - G.p.y) * G.d.y) / dd)); return geoLinePoint(G, t); }
  if (G.k === 'circ') { const dx = q.x - G.c.x, dy = q.y - G.c.y, l = Math.hypot(dx, dy) || 1; return {x: G.c.x + dx / l * G.r, y: G.c.y + dy / l * G.r}; }
  if (G.k === 'poly') { let best = null, bd = Infinity; G.pts.forEach((a, i) => { const b = G.pts[(i + 1) % G.pts.length], p = geoProject({k: 'line', p: a, d: {x: b.x - a.x, y: b.y - a.y}, t0: 0, t1: 1}, q), d = Math.hypot(p.x - q.x, p.y - q.y); if (d < bd) { bd = d; best = p; } }); return best; }
  return null;
}
/* the points where two lines, a line and a circle, or two circles meet (polygons: each edge) */
export function geoIntersect(A, B) {
  if (!A || !B) return [];
  if (A.k === 'poly' || B.k === 'poly') {
    const [P, Q] = A.k === 'poly' ? [A, B] : [B, A], out = [];
    P.pts.forEach((a, i) => { const b = P.pts[(i + 1) % P.pts.length]; out.push(...geoIntersect({k: 'line', p: a, d: {x: b.x - a.x, y: b.y - a.y}, t0: 0, t1: 1}, Q)); });
    return out;
  }
  const inL = (L, t) => t >= L.t0 - 1e-9 && t <= L.t1 + 1e-9;
  if (A.k === 'line' && B.k === 'line') {
    const den = A.d.x * B.d.y - A.d.y * B.d.x; if (Math.abs(den) < 1e-12) return [];
    const wx = B.p.x - A.p.x, wy = B.p.y - A.p.y, t = (wx * B.d.y - wy * B.d.x) / den, u = (wx * A.d.y - wy * A.d.x) / den;
    return inL(A, t) && inL(B, u) ? [geoLinePoint(A, t)] : [];
  }
  if (A.k === 'circ' && B.k === 'line') return geoIntersect(B, A);
  if (A.k === 'line' && B.k === 'circ') {
    const fx = A.p.x - B.c.x, fy = A.p.y - B.c.y, a = A.d.x * A.d.x + A.d.y * A.d.y, b = 2 * (fx * A.d.x + fy * A.d.y), c = fx * fx + fy * fy - B.r * B.r, disc = b * b - 4 * a * c;
    if (a < 1e-18 || disc < -1e-12) return [];
    const s = Math.sqrt(Math.max(0, disc)), ts = disc < 1e-12 ? [-b / (2 * a)] : [(-b - s) / (2 * a), (-b + s) / (2 * a)];
    return ts.filter(t => inL(A, t)).map(t => geoLinePoint(A, t));
  }
  if (A.k === 'circ' && B.k === 'circ') {
    const dx = B.c.x - A.c.x, dy = B.c.y - A.c.y, d = Math.hypot(dx, dy);
    if (d < 1e-12 || d > A.r + B.r + 1e-12 || d < Math.abs(A.r - B.r) - 1e-12) return [];
    const a = (A.r * A.r - B.r * B.r + d * d) / (2 * d), h = Math.sqrt(Math.max(0, A.r * A.r - a * a)), mx = A.c.x + dx * a / d, my = A.c.y + dy * a / d;
    return h < 1e-12 ? [{x: mx, y: my}] : [{x: mx - dy * h / d, y: my + dx * h / d}, {x: mx + dy * h / d, y: my - dx * h / d}];
  }
  return [];
}
export function computeGeometry(scene) {
  const byId = new Map((scene.objects || []).map(o => [o.id, o])), memo = new Map(), busy = new Set(), cyclic = new Set();
  const get = id => {
    if (!id) return null;
    if (memo.has(id)) return memo.get(id);
    const o = byId.get(id); if (!o || !GEO_TYPES.includes(o.type)) return null;
    if (busy.has(id)) { cyclic.add(id); return null; }
    busy.add(id);
    let r = null;
    const pt = k => { const g = get(o[k]); return g && g.k === 'pt' ? g : null; };
    if (o.type === 'gpoint') {
      if (o.kind === 'free') r = {k: 'pt', x: o.x, y: o.y};
      else if (o.kind === 'on') { const q = geoProject(get(o.a), o); r = q ? {k: 'pt', ...q} : null; }
      else if (o.kind === 'mid') {
        const A = get(o.a);
        if (A && A.k === 'line' && !o.b) r = {k: 'pt', ...geoLinePoint(A, 0.5)};
        else { const B = pt('b'); r = A && A.k === 'pt' && B ? {k: 'pt', x: (A.x + B.x) / 2, y: (A.y + B.y) / 2} : null; }
      } else if (o.kind === 'inter') {
        const list = geoIntersect(get(o.a), get(o.b));
        /* the same one of two crossings stays chosen while the figure moves: sorted by x, then y */
        list.sort((p, q) => Math.abs(p.x - q.x) > 1e-9 ? p.x - q.x : p.y - q.y);
        const q = list[Math.min(list.length - 1, Math.round(o.n))]; r = q ? {k: 'pt', x: q.x, y: q.y} : null;
      }
    } else if (o.type === 'gline') {
      const A = pt('a');
      if (A && (o.kind === 'perp' || o.kind === 'par')) { const B = get(o.base); if (B && B.k === 'line') { const l = Math.hypot(B.d.x, B.d.y) || 1, d = o.kind === 'par' ? {x: B.d.x / l, y: B.d.y / l} : {x: -B.d.y / l, y: B.d.x / l}; r = {k: 'line', p: {x: A.x, y: A.y}, d, t0: -GEO_INF, t1: GEO_INF}; } }
      else { const B = pt('b'); if (A && B && Math.hypot(B.x - A.x, B.y - A.y) > 1e-12) r = {k: 'line', p: {x: A.x, y: A.y}, d: {x: B.x - A.x, y: B.y - A.y}, t0: o.kind === 'line' ? -GEO_INF : 0, t1: o.kind === 'segment' ? 1 : GEO_INF}; }
    } else if (o.type === 'gcircle') {
      const C = pt('c'), P = o.p ? pt('p') : null;
      if (C && (!o.p || P)) r = {k: 'circ', c: {x: C.x, y: C.y}, r: P ? Math.hypot(P.x - C.x, P.y - C.y) : o.r};
    } else if (o.type === 'gpoly') {
      const pts = o.pts.map(id => get(id)); if (pts.length >= 3 && pts.every(g => g && g.k === 'pt')) r = {k: 'poly', pts: pts.map(g => ({x: g.x, y: g.y}))};
    } else if (o.type === 'gangle') {
      const A = pt('a'), B = pt('b'), C = pt('c');
      if (A && B && C) { let deg = (Math.atan2(C.y - B.y, C.x - B.x) - Math.atan2(A.y - B.y, A.x - B.x)) * 180 / Math.PI; deg = ((deg % 360) + 360) % 360; r = {k: 'ang', a: A, b: B, c: C, deg}; }
    }
    busy.delete(id); memo.set(id, r);
    return r;
  };
  for (const o of scene.objects || []) if (GEO_TYPES.includes(o.type)) get(o.id);
  /* everything that leans on a self-referring object is cyclic too */
  if (cyclic.size) for (let pass = 0; pass < 8; pass++) for (const o of scene.objects) if (GEO_TYPES.includes(o.type) && !cyclic.has(o.id) && (['a', 'b', 'c', 'p', 'base'].some(k => cyclic.has(o[k])) || (o.type === 'gpoly' && (o.pts || []).some(k => cyclic.has(k))))) cyclic.add(o.id);
  return {get, cyclic};
}
/** the world box of a geometric object (an infinite line: the box of the points it goes through) */
export function geoExtent(geo, o) {
  const G = geo.get(o.id); if (!G) return null;
  const box = pts => { const xs = pts.map(p => p.x), ys = pts.map(p => p.y), x = Math.min(...xs), y = Math.min(...ys); return {x: x - 0.05, y: y - 0.05, w: Math.max(...xs) - x + 0.1, h: Math.max(...ys) - y + 0.1}; };
  if (G.k === 'pt') return box([G]);
  if (G.k === 'line') return box([G.p, geoLinePoint(G, G.t1 > 1 ? 1 : G.t1)]);
  if (G.k === 'circ') return box([{x: G.c.x - G.r, y: G.c.y - G.r}, {x: G.c.x + G.r, y: G.c.y + G.r}]);
  if (G.k === 'poly') return box(G.pts);
  if (G.k === 'ang') return box([G.b, {x: G.b.x + o.r, y: G.b.y + o.r}, {x: G.b.x - o.r, y: G.b.y - o.r}]);
  return null;
}
/** a network's layer sizes from "2,3,1" (2 to 12 layers of 1 to 16 nodes), or null */
export function nnLayers(s) {
  const l = String(s ?? '').split(/[,\s]+/).filter(Boolean).map(Number);
  return l.length >= 2 && l.length <= 12 && l.every(n => Number.isInteger(n) && n >= 1 && n <= 16) ? l : null;
}
/** a network's weight matrices from "0.5 -1 0.2 / 1 0 -0.4 ; 0.7 / -1.2 / 0.3": one matrix a pair of layers (;), its rows
 *  the nodes of the earlier layer (/), its columns those of the later one; what does not fit is left out (null) */
export function nnWeights(s, layers) {
  const out = [], parts = String(s ?? '').split(';');
  for (let l = 0; l + 1 < layers.length; l++) {
    const rows = (parts[l] || '').split('/').map(r => r.split(/[,\s]+/).filter(Boolean).map(Number));
    out.push(Array.from({length: layers[l]}, (_, i) => Array.from({length: layers[l + 1]}, (_, j) => { const v = rows[i]?.[j]; return Number.isFinite(v) ? v : null; })));
  }
  return out;
}
/** the area of a polygon (shoelace, positive) */
export const polyArea = pts => Math.abs(pts.reduce((s, p, i) => { const q = pts[(i + 1) % pts.length]; return s + p.x * q.y - q.x * p.y; }, 0)) / 2;

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
    {id: 'd1', type: 'dim', x1: 1.35, y1: -0.22, x2: 1.6, y2: -0.22, offset: 0, text: 'A'}
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
  /* a conical pendulum: the string's conical mode draws the orbit as an ellipse in an oblique view, the vertical axis,
     the radius r and the angle θ itself (draw-render.mjs), and the solver turns the bob round it at ω = √(g / (L cos θ)) */
  if (key === 'conical') { const L = 1.6, a = rad(30); return T(name, [
    {id: 'ceil', type: 'ceiling', x: 0.9, y: 2.6, w: 1.2},
    {id: 'pv', type: 'pivot', x: 1.5, y: 2.6},
    {id: 'b1', type: 'ball', x: +(1.5 + L * Math.sin(a)).toFixed(4), y: +(2.6 - L * Math.cos(a)).toFixed(4), r: 0.08, mass: 0.5, label: 'm'},
    {id: 's1', type: 'string', a: 'pv', b: 'b1', mode: 'conical', label: 'L'}
  ], {x: 0.25, y: 0.75, w: 2.5, h: 2.1}); }
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
  custom_well: ['modern', '직접 입력한 퍼텐셜: 이중 우물 (ψ, 준위)', 'A typed potential: double well (ψ, levels)', 0.1, {x: -0.7, y: -0.5, w: 5.8, h: 3.9}, [
    {id: 'Q1', type: 'qpot', x: 0, y: 0, w: 4.6, h: 3.1, V: 'abs(x) > a + b/2 ? V0 : (abs(x) < b/2 ? Vb : 0)', params: 'a=0.5 [0.2, 1.5], b=0.12 [0, 0.8], V0=6 [0, 12], Vb=1.2 [0, 8]', xmin: -1.3, xmax: 1.3, levels: 3, psi: 'psi'}]],
  custom_barrier: ['modern', '직접 입력한 장벽의 투과 (ψ, T(E))', 'Transmission through a typed barrier (ψ, T(E))', 0.1, {x: -0.7, y: -0.5, w: 6.4, h: 3.6}, [
    {id: 'Q1', type: 'qpot', x: 0, y: 0, w: 5.2, h: 2.8, V: 'x < 0 ? 0 : (x < a ? V0 : 0)', params: 'a=0.4 [0.05, 1.5], V0=4 [0, 10]', xmin: -1.2, xmax: 1.6, levels: 0, psi: 'psi', E: 2.5, tplot: true}]],
  photoelectric: ['modern', '광전 효과 장치', 'Photoelectric effect setup', 0.1, {x: -0.4, y: -0.6, w: 3.8, h: 3.2}, [
    {id: 'pt', type: 'phototube', x: 0, y: 0, w: 3, h: 2.2, label: '$hf$'}]],
  /* general */
  function_graph: ['general', '함수 그래프', 'Graph of a function', 0.1, {x: -0.6, y: -1.6, w: 5.6, h: 3.4}, [
    {id: 'G1', type: 'graph', x: 0, y: -1.2, w: 4.4, h: 2.4, auto: false, xmin: 0, xmax: 7, ymin: -1.3, ymax: 1.3, xlabel: 't', ylabel: 'x', ticks: true, origin: 'O'},
    {id: 'c1', type: 'curve', graph: 'G1', kind: 'func', expr: 'exp(-x/3)*cos(3x)', x1: 0, x2: 7, label: ''},
    {id: 'c2', type: 'curve', graph: 'G1', kind: 'func', expr: 'exp(-x/3)', x1: 0, x2: 7, pattern: 'dashed', label: 'Ae^{-t/\\tau}'},
    {id: 'c3', type: 'curve', graph: 'G1', kind: 'func', expr: '-exp(-x/3)', x1: 0, x2: 7, pattern: 'dashed', label: ''}]],
  param_function: ['general', '값을 바꾸는 함수 그래프 (매개변수 슬라이더)', 'A function with parameters (sliders)', 0.1, {x: -0.6, y: -1.6, w: 5.6, h: 3.4}, [
    {id: 'G1', type: 'graph', x: 0, y: -1.2, w: 4.4, h: 2.4, auto: false, xmin: 0, xmax: 7, ymin: -1.3, ymax: 1.3, xlabel: 't', ylabel: 'x', ticks: true, origin: 'O'},
    {id: 'c1', type: 'curve', graph: 'G1', kind: 'func', params: 'A=1 [0, 1.2], tau=3 [0.5, 10], w=3 [0.5, 8]', expr: 'A exp(-x/tau) cos(w x)', x1: 0, x2: 7, label: ''}]],
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
    {id: 'tb', type: 'label', x: 3.3, y: 2.1, text: '\\rho = \\mathrm{const}', size: 14, box: true}]],
  /* ── added: mechanics ── */
  stacked_blocks: ['mech', '쌓인 두 물체와 마찰 (아래 물체를 당김)', 'Two stacked blocks with friction (pulling the lower one)', 0.1, {x: -0.3, y: -0.45, w: 4.6, h: 1.65}, [
    {id: 'gnd', type: 'floor', x: 0, y: 0, w: 4, mu: 0},
    {id: 'M', type: 'block', on: 'gnd', at: 1.6, w: 1.3, h: 0.36, mass: 3, mu: 0.4, label: 'M'},
    {id: 'm', type: 'block', on: 'M', at: 0.65, w: 0.5, h: 0.3, mass: 1, label: 'm'},
    {id: 'F1', type: 'force', on: 'M', F: 20, angle: 0, len: 0.9, label: 'F'},
    {id: 'lmu', type: 'label', x: 1.45, y: 0.5, text: '\\mu', size: 14}]],
  rolling_incline: ['mech', '빗면을 굴러 내려가는 원통 (미끄러지지 않음)', 'A cylinder rolling down an incline without slipping', 0.1, {x: -0.3, y: -0.35, w: 3.6, h: 2.0}, [
    {id: 'gnd', type: 'floor', x: -0.1, y: 0, w: 3.3},
    {id: 'inc', type: 'incline', x: 0.1, y: 0, angle: 28, length: 3, mu: 0.3, angleLabel: '\\theta'},
    {id: 'w1', type: 'wheel', on: 'inc', at: 2.3, r: 0.22, mass: 2, kind: 'disk', omega: 'ccw', label: ''},
    {id: 'lR', type: 'label', x: 2.45, y: 1.62, text: 'm, R', size: 14}]],
  seesaw: ['mech', '시소 (지레의 평형)', 'A seesaw (balance of a lever)', 0.1, {x: 0.1, y: 0, w: 3.8, h: 1.25}, [
    {id: 'pl', type: 'plank', x: 2, y: 0.6, len: 3.2, thick: 0.07, rot: 0, support: 'fulcrum', at: 0.5, mass: 0},
    {id: 'm1', type: 'block', x: 0.8, y: 0.785, w: 0.3, h: 0.3, mass: 3, label: 'm_1'},
    {id: 'm2', type: 'block', x: 3.2, y: 0.755, w: 0.24, h: 0.24, mass: 2, label: 'm_2'},
    {id: 'da', type: 'dim', x1: 0.8, y1: 1.05, x2: 2, y2: 1.05, offset: 0, text: 'a'},
    {id: 'db', type: 'dim', x1: 2, y1: 1.05, x2: 3.2, y2: 1.05, offset: 0, text: 'b'}]],
  hinged_beam: ['mech', '벽에 경첩으로 단 막대와 줄', 'A beam hinged to a wall, held by a cable', 0.1, {x: -0.2, y: 0.1, w: 3.0, h: 2.3}, [
    {id: 'wl', type: 'wall', x: 0.2, y: 0.3, h: 2, side: 'left'},
    {id: 'bm', type: 'plank', x: 1.2, y: 1, len: 2, thick: 0.07, rot: 0, support: 'wall', at: 0, mass: 2, label: 'L'},
    {id: 'cb', type: 'line', x1: 2.2, y1: 1, x2: 0.2, y2: 2, pattern: 'solid'},
    {id: 'hg', type: 'line', x1: 2.2, y1: 1, x2: 2.2, y2: 0.7, pattern: 'solid'},
    {id: 'm1', type: 'block', x: 2.2, y: 0.55, w: 0.3, h: 0.3, mass: 5, label: 'm'},
    {id: 'th', type: 'arc', x: 2.2, y: 1, r: 0.4, from: 153.43, to: 180, text: '\\theta'},
    {id: 'T1', type: 'callout', x: 1.2, y: 1.5, x2: 1.5, y2: 1.9, text: '\\vec{T}', end: 'none'}]],
  cart_ramp: ['mech', '경사면 위의 수레', 'A cart on a ramp', 0.1, {x: -0.3, y: -0.35, w: 3.8, h: 1.7}, [
    {id: 'gnd', type: 'floor', x: -0.1, y: 0, w: 3.5},
    {id: 'inc', type: 'incline', x: 0, y: 0, angle: 20, length: 3.2, angleLabel: '\\theta'},
    {id: 'c1', type: 'block', on: 'inc', at: 1.9, w: 0.7, h: 0.42, mass: 1.5, look: 'cart', label: 'm', showV: true, vx: -1, vy: -0.364, vLabel: 'v'}]],
  loop_track: ['mech', '곡면 경사로와 원형 궤도', 'A curved ramp and a vertical loop', 0.1, {x: -1.1, y: -0.45, w: 5.6, h: 2.6}, [
    {id: 'rp', type: 'track', x: 1, y: 1.6, r: 1.6, from: 180, to: 270, side: 'out'},
    {id: 'gnd', type: 'floor', x: 1, y: 0, w: 3.4},
    {id: 'lp', type: 'track', x: 3.2, y: 0.6, r: 0.6, from: -90, to: 270, side: 'out'},
    {id: 'b1', type: 'ball', x: -0.41, y: 1.09, r: 0.1, mass: 0.2, label: 'm'},
    {id: 'dh', type: 'dim', x1: -0.85, y1: 0, x2: -0.85, y2: 1.09, offset: 0, text: 'h'},
    {id: 'rr', type: 'line', x1: 3.2, y1: 0.6, x2: 3.2, y2: 1.2, pattern: 'solid', heads: 'end'},
    {id: 'lR', type: 'label', x: 3.32, y: 0.92, text: 'R', size: 15},
    {id: 'pc', type: 'point', x: 3.2, y: 0.6, label: '', filled: true}]],
  two_pulleys: ['mech', '두 도르래에 걸친 줄과 두 물체', 'One rope over two pulleys with two hanging masses', 0.1, {x: 0, y: 0.15, w: 3.2, h: 1.7}, [
    {id: 'tb', type: 'floor', x: 0.6, y: 1.4, w: 2},
    {id: 'p1', type: 'pulley', x: 0.55, y: 1.5, r: 0.1, mount: 'tb'},
    {id: 'p2', type: 'pulley', x: 2.65, y: 1.5, r: 0.1, mount: 'tb'},
    {id: 'm1', type: 'block', x: 0.45, y: 0.6, w: 0.24, h: 0.24, mass: 2, label: 'm_1'},
    {id: 'm2', type: 'block', x: 2.75, y: 0.85, w: 0.24, h: 0.24, mass: 3, label: 'm_2'},
    {id: 's1', type: 'string', a: 'm1', b: 'm2', over: ['p1', 'p2']}]],
  /* ── added: electromagnetism ── */
  meter_bridge: ['em', '미터 브리지 (평형점 찾기)', 'Meter bridge (finding the balance point)', 0.1, {x: -0.6, y: -1.5, w: 5.2, h: 3.4}, [
    {id: 'BR', type: 'bridge', x1: 0, y1: 0, x2: 4, y2: 0, kind: 'meter', R: 10, at: 0.4, label: 'J'},
    {id: 'R1', type: 'element', kind: 'resistor', x1: 0, y1: 1.5, x2: 1.6, y2: 1.5, value: 4, label: 'R'},
    {id: 'S1', type: 'element', kind: 'resistor', x1: 1.6, y1: 1.5, x2: 4, y2: 1.5, value: 6, label: 'S'},
    {id: 'G1', type: 'element', kind: 'galvanometer', x1: 1.6, y1: 1.5, x2: 1.6, y2: 0, value: 20},
    {id: 'W1', type: 'element', kind: 'wire', x1: 0, y1: 0, x2: 0, y2: 1.5},
    {id: 'W2', type: 'element', kind: 'wire', x1: 4, y1: 0, x2: 4, y2: 1.5},
    {id: 'W3', type: 'element', kind: 'wire', x1: 0, y1: 0, x2: 0, y2: -1},
    {id: 'E1', type: 'element', kind: 'cell', x1: 0, y1: -1, x2: 4, y2: -1, value: 2, label: '\\mathcal{E}'},
    {id: 'W4', type: 'element', kind: 'wire', x1: 4, y1: -1, x2: 4, y2: 0}]],
  rails_emf: ['em', '도체 레일 위를 움직이는 막대 (유도 기전력)', 'A rod sliding on rails (motional EMF)', 0.1, {x: -0.6, y: -0.6, w: 4.6, h: 2.3}, [
    {id: 'RL', type: 'rails', x: 0, y: 0, w: 3.4, h: 1.1, at: 2, v: 2, B: 0.5, R: 2, field: 'in'}]],
  transformer_ac: ['em', '변압기 (교류 전원과 전구)', 'A transformer with an AC source and a bulb', 0.05, {x: -0.3, y: -0.35, w: 4.4, h: 2.2}, [
    {id: 'TR', type: 'transformer', x: 2, y: 0.75, h: 1.4, np: 6, ns: 12},
    {id: 'E1', type: 'element', kind: 'ac', x1: 0.3, y1: 0.19, x2: 0.3, y2: 1.31, value: 10, label: 'V_1'},
    {id: 'W1', type: 'element', kind: 'wire', x1: 0.3, y1: 1.31, x2: 1.3, y2: 1.31},
    {id: 'W2', type: 'element', kind: 'wire', x1: 0.3, y1: 0.19, x2: 1.3, y2: 0.19},
    {id: 'B1', type: 'element', kind: 'bulb', x1: 3.7, y1: 1.31, x2: 3.7, y2: 0.19, value: 10},
    {id: 'W3', type: 'element', kind: 'wire', x1: 2.7, y1: 1.31, x2: 3.7, y2: 1.31},
    {id: 'W4', type: 'element', kind: 'wire', x1: 2.7, y1: 0.19, x2: 3.7, y2: 0.19}]],
  dielectric_rc: ['em', '유전체를 넣은 축전기와 가변 저항', 'A capacitor with a dielectric and a rheostat', 0.25, {x: -0.8, y: -0.6, w: 4.6, h: 3.1}, [
    {id: 'E1', type: 'element', kind: 'battery', x1: 0, y1: 0, x2: 0, y2: 2, value: 9, label: '\\mathcal{E}'},
    {id: 'S1', type: 'element', kind: 'switch', x1: 0, y1: 2, x2: 1, y2: 2, closed: true, label: 'S'},
    {id: 'R1', type: 'element', kind: 'rheostat', x1: 1, y1: 2, x2: 3, y2: 2, value: 1000, label: 'R'},
    {id: 'C1', type: 'element', kind: 'dielectric', x1: 3, y1: 2, x2: 3, y2: 0, value: 220, label: '\\kappa C'},
    {id: 'W1', type: 'element', kind: 'wire', x1: 3, y1: 0, x2: 0, y2: 0}]],
  force_on_wire: ['em', '자기장 속 전류가 받는 힘', 'Force on a current in a magnetic field', 0.1, {x: -0.4, y: -0.5, w: 4.4, h: 2.8}, [
    {id: 'B1', type: 'field', kind: 'B', dir: 'in', x: 0.3, y: 0, w: 3, h: 1.8, spacing: 0.4, pattern: 'dashed', label: '\\vec{B}'},
    {id: 'I1', type: 'cwire', x1: 0, y1: 0.9, x2: 3.6, y2: 0.9, I: 2, label: 'I'},
    {id: 'Fv', type: 'vector', x1: 1.8, y1: 0.9, x2: 1.8, y2: 1.75, label: '\\vec{F}'},
    {id: 'dl', type: 'brace', x1: 0.3, y1: 0.9, x2: 3.3, y2: 0.9, kind: 'brace', offset: -0.25, text: 'L'}]],
  /* ── added: heat and fluids ── */
  buoyancy: ['thermo', '물에 뜬 물체와 가라앉은 공 (부력)', 'A floating block and a sunken ball (buoyancy)', 0.1, {x: -0.4, y: -0.35, w: 3.6, h: 2.3}, [
    {id: 'ct', type: 'container', x: 0, y: 0, w: 2.4, h: 1.6, level: 0.6, rho: 1000, fill: 'gray'},
    {id: 'A', type: 'block', x: 1, y: 0.92, w: 0.5, h: 0.4, mass: 60, label: 'A'},
    {id: 'b1', type: 'ball', x: 1.9, y: 0.15, r: 0.15, mass: 40, label: 'B'},
    {id: 'cw', type: 'callout', x: 0.35, y: 0.5, x2: -0.1, y2: 1.35, text: '물', end: 'dot'},
    {id: 'Bu', type: 'parrows', x1: 1.2, y1: 0.72, x2: 0.8, y2: 0.72, n: 3, len: 0.2, dir: 'in', label: ''}]],
  u_tube: ['thermo', 'U자관 속 액체의 높이 차', 'Liquid levels in a U-tube', 0.1, {x: 0, y: -0.35, w: 2.6, h: 2.4}, [
    {id: 'ut', type: 'utube', x: 0.5, y: 0, w: 1.6, h: 1.8, tube: 0.24, left: 0.4, right: 0.7, fill: 'gray'},
    {id: 'pa', type: 'parrows', x1: 0.54, y1: 1.15, x2: 0.7, y2: 1.15, n: 2, len: 0.3, dir: 'in', label: 'P_0'}]],
  heated_gas: ['thermo', '가열되는 기체 (피스톤·온도계·열원)', 'Gas heated under a piston (thermometer, burner)', 0.1, {x: -0.3, y: -0.6, w: 3.4, h: 3.0}, [
    {id: 'cyl', type: 'cylinder', x: 0.3, y: 0.3, w: 1.4, h: 1.9, piston: 0.6, gas: true, weight: true, label: 'n, T'},
    {id: 'ht', type: 'heater', x: 1, y: -0.35, w: 0.9, kind: 'flame', label: '열원'},
    {id: 'tm', type: 'thermometer', x: 2.3, y: 0.3, h: 1.6, level: 0.55, label: 'T'}]],
  gas_box: ['thermo', '상자 속 기체 분자의 운동', 'Gas molecules moving in a box', 0.1, {x: -0.3, y: -0.4, w: 2.8, h: 2.1}, [
    {id: 'gb', type: 'gasbox', x: 0, y: 0, w: 2.2, h: 1.5, n: 22, arrows: true, seed: 3, label: 'N, V, T'}]],
  /* ── added: optics ── */
  michelson: ['optics', '마이클슨 간섭계', 'Michelson interferometer', 0.1, {x: -0.6, y: -1.8, w: 5, h: 3.8}, [
    {id: 'LS', type: 'source', x: 0, y: 0, kind: 'laser', size: 0.5, label: '레이저'},
    {id: 'BS', type: 'mirror', x: 2, y: 0, h: 0.9, f: 0, rot: -45, half: true, showF: false, label: ''},
    {id: 'M1', type: 'mirror', x: 2, y: 1.6, h: 0.9, f: 0, rot: 90, showF: false, label: ''},
    {id: 'M2', type: 'mirror', x: 3.8, y: 0, h: 0.9, f: 0, rot: 0, showF: false, label: 'M_2'},
    {id: 'SC', type: 'screen', x: 2, y: -1.4, h: 1, rot: 90, label: ''},
    {id: 'r1', type: 'ray', x: 0.02, y: 0, angle: 0, len: 14, arrow: true},
    {id: 'l1', type: 'label', x: 2.6, y: 1.75, text: 'M_1', size: 15},
    {id: 'l2', type: 'label', x: 2.45, y: 0.3, text: '\\mathrm{BS}', size: 13},
    {id: 'l3', type: 'label', x: 2.75, y: -1.5, text: '스크린', size: 14}]],
  magnifier: ['optics', '볼록 렌즈와 눈 (돋보기)', 'A converging lens and the eye (magnifier)', 0.1, {x: -0.3, y: -1.3, w: 5.4, h: 2.6}, [
    {id: 'ax', type: 'line', x1: -0.2, y1: 0, x2: 4.9, y2: 0, pattern: 'dashdot'},
    {id: 'L1', type: 'lens', x: 2.4, y: 0, h: 1.8, f: 1.2, label: 'L'},
    {id: 'O', type: 'oarrow', x: 1.6, y: 0, h: 0.4, label: 'O', rays: true, image: true, imageLabel: 'I'},
    {id: 'ey', type: 'eye', x: 4.4, y: 0, size: 0.5, rot: 180, label: '눈'}]],
  optical_fiber: ['optics', '광섬유 속 전반사', 'Total internal reflection in an optical fibre', 0.1, {x: -0.4, y: -0.8, w: 5.2, h: 1.6}, [
    {id: 'fb', type: 'fiber', x1: 0, y1: 0, x2: 4.4, y2: 0, r: 0.2, angle: 18, label: ''},
    {id: 'n1', type: 'label', x: 4.65, y: 0, text: 'n_1', size: 14}, {id: 'n2', type: 'label', x: 4.65, y: 0.3, text: 'n_2', size: 14}]],
  tilted_mirror: ['optics', '기울인 평면거울에서의 반사', 'Reflection from a tilted plane mirror', 0.1, {x: -0.3, y: -1.2, w: 4.2, h: 2.6}, [
    {id: 'M', type: 'mirror', x: 2.8, y: 0, h: 2, f: 0, rot: 20, showF: false, label: 'M'},
    {id: 'r1', type: 'ray', x: 0, y: 0.5, angle: 0, len: 6, arrow: true},
    {id: 'nl', type: 'line', x1: 2.618, y1: 0.5, x2: 1.49, y2: 0.09, pattern: 'dashed'},
    {id: 'th', type: 'arc', x: 2.8, y: 0, r: 0.6, from: 90, to: 110, text: '\\alpha'}]],
  /* ── added: waves and modern physics ── */
  pulses: ['waves', '줄 위에서 마주 오는 두 펄스', 'Two pulses approaching on a string', 0.1, {x: -0.3, y: -0.7, w: 5, h: 1.6}, [
    {id: 'p1', type: 'pulse', x: 0, y: 0, len: 4.4, A: 0.4, width: 0.8, pos: 0.25, shape: 'tri', dir: 'right', axis: true, label: 'v'},
    {id: 'p2', type: 'pulse', x: 0, y: 0, len: 4.4, A: -0.3, width: 0.8, pos: 0.75, shape: 'square', dir: 'left', axis: false, label: 'v'}]],
  two_sources: ['waves', '두 점파원의 간섭 (마디선)', 'Interference of two point sources (nodal lines)', 0.1, {x: -2.6, y: -2.2, w: 5.2, h: 4.4}, [
    {id: 'IF', type: 'interference', x: 0, y: 0, d: 1.2, lambda: 0.4, n: 4, nodal: true, labels: true}]],
  alpha_decay: ['modern', '알파 붕괴와 감마선', 'Alpha decay and a gamma ray', 0.1, {x: -0.4, y: -1.1, w: 4.4, h: 2.2}, [
    {id: 'nu', type: 'nucleus', x: 0.6, y: 0, r: 0.45, np: 12, nn: 14, label: '{}^{A}_{Z}\\mathrm{X}'},
    {id: 'al', type: 'particle', x: 1.4, y: 0.3, kind: 'alpha', arrow: true, angle: 20, len: 1.4, label: '\\alpha'},
    {id: 'ga', type: 'particle', x: 1.3, y: -0.35, kind: 'photon', angle: -15, len: 1.8, label: '\\gamma'}]],
  compton: ['modern', '광자와 전자의 충돌 (콤프턴 산란)', 'A photon scattering off an electron (Compton)', 0.1, {x: -0.3, y: -1.3, w: 4.6, h: 2.6}, [
    {id: 'ph', type: 'particle', x: 0, y: 0, kind: 'photon', angle: 0, len: 1.7, label: 'h\\nu'},
    {id: 'el', type: 'particle', x: 2, y: 0, kind: 'electron', arrow: true, angle: -35, len: 1.3, label: 'e^-'},
    {id: 'sc', type: 'particle', x: 2.15, y: 0.08, kind: 'photon', angle: 40, len: 1.6, label: "h\\nu'"},
    {id: 'ax', type: 'line', x1: 2, y1: 0, x2: 4, y2: 0, pattern: 'dashed'},
    {id: 'th', type: 'arc', x: 2, y: 0, r: 0.6, from: 0, to: 40, text: '\\theta'}]],
  /* ── added: graphs and multi-panel figures ── */
  vt_area: ['general', 'v–t 그래프와 이동 거리 (넓이)', 'A v–t graph and the distance (area)', 0.1, {x: -0.6, y: -0.55, w: 5.2, h: 3.0}, [
    {id: 'G1', type: 'graph', x: 0, y: 0, w: 4, h: 2, auto: false, xmin: 0, xmax: 6, ymin: 0, ymax: 3, xlabel: 't', ylabel: 'v', origin: '0', xt: '2:t_0, 4:2t_0, 5:3t_0', yt: '2:v_0'},
    {id: 'c1', type: 'curve', graph: 'G1', kind: 'points', data: '0,0 2,2 4,2 5,0', shade: true, label: ''}]],
  xt_vt_panels: ['general', '(가) x–t, (나) v–t 그래프', '(a) x–t and (b) v–t graphs', 0.1, {x: -0.5, y: -0.9, w: 7.6, h: 3.1}, [
    {id: 'G1', type: 'graph', x: 0, y: 0, w: 2.8, h: 1.8, auto: false, xmin: 0, xmax: 4, ymin: 0, ymax: 4, xlabel: 't', ylabel: 'x', origin: '0', xt: '2:t_0'},
    {id: 'c1', type: 'curve', graph: 'G1', kind: 'func', expr: '0.75x^2', x1: 0, x2: 2, label: ''},
    {id: 'c1b', type: 'curve', graph: 'G1', kind: 'points', data: '2,3 3.4,4', label: ''},
    {id: 'G2', type: 'graph', x: 3.9, y: 0, w: 2.8, h: 1.8, auto: false, xmin: 0, xmax: 4, ymin: 0, ymax: 4, xlabel: 't', ylabel: 'v', origin: '0', xt: '2:t_0', yt: '3:v_0'},
    {id: 'c2', type: 'curve', graph: 'G2', kind: 'points', data: '0,0 2,3 3.6,3', label: ''},
    {id: 'pa', type: 'panel', x: -0.3, y: -0.3, w: 3.4, h: 2.3, caption: '(가)'},
    {id: 'pb', type: 'panel', x: 3.6, y: -0.3, w: 3.4, h: 2.3, caption: '(나)'}]],
  /* ── added: 수능-style setups (style 수능: bare floor line, gray strips, (가)(나) captions) ── */
  ks_collision: ['mech', '수능형: 수평면 위 두 물체의 충돌 (가)(나)', 'CSAT style: two blocks colliding on a floor, (a) and (b)', 0.1, {x: -0.3, y: -0.75, w: 6.95, h: 1.9}, [
    {id: 'f1', type: 'floor', x: 0, y: 0, w: 2.9},
    {id: 'A', type: 'block', on: 'f1', at: 0.6, w: 0.45, h: 0.32, mass: 2, label: 'A'},
    {id: 'B', type: 'block', on: 'f1', at: 2.1, w: 0.45, h: 0.32, mass: 1, label: 'B'},
    {id: 'vA', type: 'vector', x1: 0.9, y1: 0.18, x2: 1.4, y2: 0.18, width: 1.2, label: ''},
    {id: 'lv', type: 'label', x: 1.15, y: 0.42, text: '2v', size: 14},
    {id: 'ls', type: 'label', x: 2.1, y: 0.55, text: '정지', size: 13},
    {id: 'lf', type: 'label', x: 0.35, y: -0.17, text: '수평면', size: 13},
    {id: 'f2', type: 'floor', x: 3.4, y: 0, w: 2.9},
    {id: 'A2', type: 'block', on: 'f2', at: 1.7, w: 0.45, h: 0.32, mass: 2, label: 'A'},
    {id: 'B2', type: 'block', on: 'f2', at: 2.25, w: 0.45, h: 0.32, mass: 1, label: 'B'},
    {id: 'vB', type: 'vector', x1: 5.95, y1: 0.18, x2: 6.3, y2: 0.18, width: 1.2, label: ''},
    {id: 'lv2', type: 'label', x: 6.1, y: 0.42, text: 'v_B', size: 14},
    {id: 'pa', type: 'panel', x: 0, y: -0.25, w: 2.9, h: 0.9, caption: '(가)'},
    {id: 'pb', type: 'panel', x: 3.4, y: -0.25, w: 2.9, h: 0.9, caption: '(나)'}], {style: 'suneung'}],
  ks_pulley: ['mech', '수능형: 실로 연결된 물체 A, B (도르래)', 'CSAT style: blocks A and B joined over a pulley', 0.1, {x: -0.2, y: -0.3, w: 3.1, h: 1.7}, [
    {id: 'tb', type: 'floor', x: 0, y: 1, w: 2.2, hatch: false},
    {id: 'A', type: 'block', on: 'tb', at: 1, w: 0.42, h: 0.3, mass: 2, label: 'A'},
    {id: 'p1', type: 'pulley', x: 2.3, y: 1.05, r: 0.1, mount: 'tb'},
    {id: 'B', type: 'block', x: 2.4, y: 0.45, w: 0.3, h: 0.3, mass: 1, label: 'B'},
    {id: 's1', type: 'string', a: 'A', b: 'B', over: ['p1']},
    {id: 'gd', type: 'floor', x: -0.1, y: 0, w: 3}, {id: 'lf', type: 'label', x: 0.3, y: -0.17, text: '수평면', size: 13},
    {id: 'pq', type: 'point', x: 0.3, y: 1, label: 'p'}, {id: 'pr', type: 'point', x: 1.9, y: 1, label: 'q'}], {style: 'suneung'}],
  ks_graph: ['general', '수능형: 속력–시간 그래프와 운동 (가)(나)', 'CSAT style: a speed–time graph with the motion, (a) and (b)', 0.1, {x: -0.3, y: -0.9, w: 7.0, h: 2.8}, [
    {id: 'f1', type: 'floor', x: 0, y: 0.4, w: 2.6},
    {id: 'A', type: 'block', on: 'f1', at: 0.5, w: 0.4, h: 0.3, mass: 1, label: 'A'},
    {id: 'v1', type: 'vector', x1: 0.8, y1: 0.55, x2: 1.25, y2: 0.55, width: 1.2, label: ''}, {id: 'lv', type: 'label', x: 1.02, y: 0.78, text: 'v_0', size: 14},
    {id: 'fz', type: 'region', x: 1.5, y: 0.34, w: 0.6, h: 0.06, fill: 'dark', pattern: 'none'},
    {id: 'cz', type: 'callout', x: 1.8, y: 0.34, x2: 2.2, y2: 0.05, text: '마찰 구간', end: 'none'},
    {id: 'G1', type: 'graph', x: 3.4, y: 0, w: 2.6, h: 1.6, auto: false, xmin: 0, xmax: 4, ymin: 0, ymax: 3, xlabel: '시간', ylabel: '속력', origin: '0', xt: '1:t_0, 2:2t_0', yt: '2:v_0'},
    {id: 'c1', type: 'curve', graph: 'G1', kind: 'points', data: '0,2 1,2 2,1 3.5,1', label: ''},
    {id: 'pa', type: 'panel', x: 0, y: -0.25, w: 2.6, h: 1.5, caption: '(가)'},
    {id: 'pb', type: 'panel', x: 3.3, y: -0.25, w: 2.9, h: 1.5, caption: '(나)'}], {style: 'suneung'}],
  /* diagrams: a 2-3-1 neural network with typed weights, a matrix equation, tensor notation, a feedback block diagram */
  nn_mlp: ['general', '신경망 (2-3-1 다층 퍼셉트론, 가중치)', 'Neural network (2-3-1 MLP, weights)', 0.1, {x: -0.8, y: -0.6, w: 5.4, h: 3.2}, [
    {id: 'N', type: 'nnet', x: 0, y: 0, w: 3.8, h: 2.2, layers: '2,3,1', inLabels: 'x_1,x_2', outLabels: '\\hat{y}', act: '\\sigma', bias: true, weights: '0.8 -0.5 0.3 / -1.2 0.9 0.6 ; 1.1 / -0.7 / 0.4', wstyle: 'color', wlabels: false},
    {id: 'l1', type: 'label', x: 0.25, y: -0.35, text: '입력층', size: 13}, {id: 'l2', type: 'label', x: 1.9, y: -0.35, text: '은닉층', size: 13}, {id: 'l3', type: 'label', x: 3.6, y: -0.35, text: '출력층', size: 13},
    {id: 'eq', type: 'label', x: 1.9, y: 2.4, text: '$h_j = \\sigma(\\sum_i w_{ij} x_i + b_j)$', size: 15}]],
  matrix_eq: ['general', '행렬 방정식 Ax = b (첨가 행렬)', 'Matrix equation Ax = b (augmented matrix)', 0.1, {x: -0.2, y: -0.2, w: 5.4, h: 2.6}, [
    {id: 'm1', type: 'label', x: 2.5, y: 1.75, text: '$\\pmatrix{2 & 1 & -1 \\\\ 1 & 3 & 2 \\\\ 0 & 1 & 4}\\pmatrix{x_1 \\\\ x_2 \\\\ x_3} = \\pmatrix{3 \\\\ 5 \\\\ 6}$', size: 17},
    {id: 'm2', type: 'label', x: 2.5, y: 0.5, text: '$\\amatrix{2 & 1 & -1 & 3 \\\\ 1 & 3 & 2 & 5 \\\\ 0 & 1 & 4 & 6}$', size: 17}]],
  tensor_sample: ['general', '텐서 표기 (위아래 첨자, 아인슈타인 합, ε, δ)', 'Tensor notation (indices, Einstein sum, ε, δ)', 0.1, {x: -0.2, y: -0.3, w: 5.6, h: 3.2}, [
    {id: 't1', type: 'label', x: 2.6, y: 2.5, text: '$F_{\\mu\\nu} = \\partial_\\mu A_\\nu - \\partial_\\nu A_\\mu$', size: 17},
    {id: 't2', type: 'label', x: 2.6, y: 1.8, text: '$(\\vec{a}\\times\\vec{b})_i = \\varepsilon_{ijk} a_j b_k$', size: 17},
    {id: 't3', type: 'label', x: 2.6, y: 1.0, text: '$\\delta_{ij} = \\cases{1 & i = j \\\\ 0 & i \\neq j}$', size: 17},
    {id: 't4', type: 'label', x: 2.6, y: 0.2, text: '$T^{\\mu\\nu} = (\\rho + p) u^\\mu u^\\nu + p\\, g^{\\mu\\nu}$', size: 17}]],
  block_flow: ['general', '블록 선도 (되먹임 제어)', 'Block diagram (feedback control)', 0.1, {x: -0.3, y: -0.9, w: 6.2, h: 2.4}, [
    {id: 'in', type: 'fbox', x: 0.2, y: 0.5, w: 0.1, h: 0.1, shape: 'circle', fill: 'dark'},
    {id: 'sum', type: 'fbox', x: 1.0, y: 0.5, w: 0.36, h: 0.36, shape: 'sum'},
    {id: 'C', type: 'fbox', x: 2.3, y: 0.5, w: 1.1, h: 0.6, text: '$C(s)$'}, {id: 'P', type: 'fbox', x: 3.9, y: 0.5, w: 1.1, h: 0.6, text: '$G(s)$'},
    {id: 'out', type: 'fbox', x: 5.4, y: 0.5, w: 0.1, h: 0.1, shape: 'circle', fill: 'dark'}, {id: 'Hs', type: 'fbox', x: 3.1, y: -0.45, w: 1.1, h: 0.55, text: '$H(s)$'},
    {id: 'a1', type: 'farrow', a: 'in', b: 'sum', label: 'R', sign: '+'}, {id: 'a2', type: 'farrow', a: 'sum', b: 'C', label: 'E'}, {id: 'a3', type: 'farrow', a: 'C', b: 'P', label: 'U'},
    {id: 'a4', type: 'farrow', a: 'P', b: 'out', label: 'Y'}, {id: 'a5', type: 'farrow', a: 'out', b: 'Hs', route: 'vh'}, {id: 'a6', type: 'farrow', a: 'Hs', b: 'sum', route: 'hv', sign: '-'}]],
  /* the geometric construction: drag A, B or C and everything built on them follows */
  geo_triangle: ['geo', '작도: 삼각형의 외심과 외접원', 'Construction: circumcentre and circumcircle of a triangle', 0.1, {x: -0.8, y: -0.85, w: 5.6, h: 4.0}, [
    {id: 'A', type: 'gpoint', x: 0.4, y: 0.4, label: 'A'}, {id: 'B', type: 'gpoint', x: 3.6, y: 0.6, label: 'B'}, {id: 'C', type: 'gpoint', x: 1.6, y: 2.8, label: 'C'},
    {id: 'ab', type: 'gline', a: 'A', b: 'B', measure: true}, {id: 'bc', type: 'gline', a: 'B', b: 'C'}, {id: 'ca', type: 'gline', a: 'C', b: 'A'},
    {id: 'M1', type: 'gpoint', kind: 'mid', a: 'ab', label: 'M'}, {id: 'M2', type: 'gpoint', kind: 'mid', a: 'bc', label: 'N'},
    {id: 'p1', type: 'gline', kind: 'perp', a: 'M1', base: 'ab', pattern: 'dashed', color: 'gray'}, {id: 'p2', type: 'gline', kind: 'perp', a: 'M2', base: 'bc', pattern: 'dashed', color: 'gray'},
    {id: 'O', type: 'gpoint', kind: 'inter', a: 'p1', b: 'p2', label: 'O'},
    {id: 'cc', type: 'gcircle', c: 'O', p: 'A', color: 'blue'},
    {id: 'ang', type: 'gangle', a: 'B', b: 'A', c: 'C', r: 0.45}]],
  /* functions like a graphing calculator: a parameter slider, the tangent, the area, roots and extrema */
  func_features: ['general', '함수 분석: 접선 · 넓이 · 근 · 극값', 'Function analysis: tangent, area, roots, extrema', 0.1, {x: -0.6, y: -0.5, w: 6.4, h: 4.4}, [
    {id: 'G', type: 'graph', x: 0, y: 0, w: 5.4, h: 3.4, auto: false, xmin: -3, xmax: 3, ymin: -3, ymax: 3, ticks: true, grid: true, xstep: 1, ystep: 1},
    {id: 'f', type: 'curve', graph: 'G', kind: 'func', expr: 'a x^3 - 2x', params: 'a=0.5 [0.1, 2]', x1: -3, x2: 3, label: 'y = f(x)', tangent: true, tx: 1.6, area: true, a1: 0, a2: 1.8, roots: true, extrema: true},
    {id: 'r', type: 'curve', graph: 'G', kind: 'polar', expr: '1 + 0.5 cos(3t)', x1: 0, x2: 6.2832, color: 'blue', pattern: 'dashed'},
    {id: 'q', type: 'curve', graph: 'G', kind: 'ineq', expr: '0.5 x - 2', rel: 'lt', color: 'green'}]],
  /* drawn shapes given physics: a ramp and a floor drawn as lines, boxes and a ball that fall, slide and roll */
  rigid_demo: ['mech', '그린 도형에 물리 적용 (경사면 · 상자 · 공)', 'Drawn shapes with physics (ramp, boxes, ball)', 0.1, {x: -0.3, y: -0.4, w: 5.6, h: 3.4}, [
    {id: 'fl', type: 'line', x1: 0, y1: 0, x2: 5, y2: 0, pattern: 'solid', phys: 'static', pmu: 0.4},
    {id: 'rp', type: 'line', x1: 0, y1: 1.8, x2: 2.2, y2: 0.4, pattern: 'solid', phys: 'static', pmu: 0.2},
    {id: 'wl', type: 'line', x1: 5, y1: 0, x2: 5, y2: 2.6, pattern: 'solid', phys: 'static'},
    {id: 'bx', type: 'rect', x: 0.28, y: 1.53, w: 0.4, h: 0.3, rot: -32.47, fill: 'lightgray', phys: 'dynamic', pmass: 1, pmu: 0.2},
    {id: 'b2', type: 'rect', x: 3.6, y: 0, w: 0.5, h: 0.5, fill: 'gray', phys: 'dynamic', pmass: 2},
    {id: 'b3', type: 'rect', x: 3.65, y: 0.5, w: 0.4, h: 0.4, fill: 'lightgray', phys: 'dynamic', pmass: 1},
    {id: 'bl', type: 'ellipse', x: 1.5, y: 2.2, w: 0.3, h: 0.3, fill: 'tint', color: 'red', phys: 'dynamic', pmass: 0.5, pvx: 1.2, pe: 0.6},
    {id: 'pd', type: 'ellipse', x: 4.35, y: 1.25, w: 0.2, h: 0.2, fill: 'dark', phys: 'dynamic', pmass: 0.3, pvx: -1.5},
    {id: 'jt', type: 'joint', a: 'pd', b: '', kind: 'rod', bx: 4.45, by: 2.5},
    {id: 'pv', type: 'point', x: 4.45, y: 2.5, filled: false}]]
};
export const TEMPLATE_KEYS = [...MECH_KEYS, ...Object.keys(NEW_TEMPLATES)];
export const TEMPLATE_NAMES = {...MECH_NAMES, ...Object.fromEntries(Object.entries(NEW_TEMPLATES).map(([k, t]) => [k, {ko: t[1], en: t[2]}]))};
export const TEMPLATE_DOMAIN = {...Object.fromEntries(MECH_KEYS.map(k => [k, 'mech'])), ...Object.fromEntries(Object.entries(NEW_TEMPLATES).map(([k, t]) => [k, t[0]]))};
export function template(key, lang = 'ko') {
  const name = (TEMPLATE_NAMES[key] || {})[lang === 'en' ? 'en' : 'ko'] || '';
  const t = NEW_TEMPLATES[key];
  if (t) return T(name, t[5], t[4], {grid: t[3], ...(t[6] || {})});
  return mechTemplate(key, name);
}

/** the centre an object turns about (its field rot), in world units */
export function rotCentre(o) {
  if ('w' in o && 'h' in o && !isBody(o) && !['transformer'].includes(o.type)) return {x: o.x + o.w / 2, y: o.y + o.h / 2};
  return {x: o.x, y: o.y};
}
/** the world box of an object that is not a body or a connection (null for what is drawn inside another object);
 *  a turned object's box holds its turned corners */
export function objectExtent(o) {
  const b = baseExtent(o);
  if (!b || !o.rot || !ROTATABLE.includes(o.type) || isBody(o) || ['plank', 'interference', 'particle'].includes(o.type)) return b;
  const c = rotCentre(o), a = o.rot * Math.PI / 180, ca = Math.cos(a), sa = Math.sin(a);
  const pts = [[b.x, b.y], [b.x + b.w, b.y], [b.x, b.y + b.h], [b.x + b.w, b.y + b.h]].map(([x, y]) => ({x: c.x + (x - c.x) * ca - (y - c.y) * sa, y: c.y + (x - c.x) * sa + (y - c.y) * ca}));
  const xs = pts.map(p => p.x), ys = pts.map(p => p.y), x = Math.min(...xs), y = Math.min(...ys);
  return {x, y, w: Math.max(...xs) - x, h: Math.max(...ys) - y};
}
function baseExtent(o) {
  const box = (x0, y0, x1, y1) => ({x: Math.min(x0, x1), y: Math.min(y0, y1), w: Math.abs(x1 - x0), h: Math.abs(y1 - y0)});
  switch (o.type) {
    case 'plank': { const a = o.rot * Math.PI / 180, dx = Math.cos(a) * o.len / 2, dy = Math.sin(a) * o.len / 2, t = o.thick; return box(o.x - Math.abs(dx) - t, o.y - Math.abs(dy) - t - (o.support === 'fulcrum' ? 0.25 : 0.05), o.x + Math.abs(dx) + t, o.y + Math.abs(dy) + t); }
    case 'track': { const pts = []; for (let i = 0; i <= 24; i++) { const t = (o.from + (o.to - o.from) * i / 24) * Math.PI / 180; pts.push([o.x + o.r * Math.cos(t), o.y + o.r * Math.sin(t)]); } const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]); return box(Math.min(...xs) - 0.1, Math.min(...ys) - 0.1, Math.max(...xs) + 0.1, Math.max(...ys) + 0.1); }
    case 'bridge': case 'fiber': case 'parrows': case 'brace': { const r = o.type === 'fiber' ? o.r : o.type === 'parrows' ? o.len : 0.2; return box(Math.min(o.x1, o.x2) - r, Math.min(o.y1, o.y2) - r, Math.max(o.x1, o.x2) + r, Math.max(o.y1, o.y2) + r); }
    case 'callout': return box(Math.min(o.x, o.x2) - 0.1, Math.min(o.y, o.y2) - 0.1, Math.max(o.x, o.x2) + 0.1, Math.max(o.y, o.y2) + 0.1);
    case 'transformer': return box(o.x - o.h * 0.6, o.y - o.h / 2, o.x + o.h * 0.6, o.y + o.h / 2);
    case 'rails': return box(o.x - 0.25, o.y - 0.15, o.x + o.w + 0.1, o.y + o.h + 0.15);
    case 'container': case 'utube': case 'gasbox': case 'panel': return box(o.x, o.y, o.x + o.w, o.y + o.h);
    case 'thermometer': return box(o.x - 0.12, o.y - 0.12, o.x + 0.12, o.y + o.h);
    case 'heater': return box(o.x - o.w / 2, o.y - o.w * 0.3, o.x + o.w / 2, o.y + o.w * 0.4);
    case 'screen': return box(o.x - 0.08, o.y - o.h / 2, o.x + 0.08, o.y + o.h / 2);
    case 'eye': return box(o.x - o.size / 2, o.y - o.size / 2, o.x + o.size / 2, o.y + o.size / 2);
    case 'source': return box(o.x - o.size / 2, o.y - o.size / 2, o.x + o.size / 2, o.y + o.size / 2);
    case 'pulse': return box(o.x, o.y - Math.abs(o.A) - 0.3, o.x + o.len, o.y + Math.abs(o.A) + 0.3);
    case 'interference': { const R = o.n * o.lambda + o.d / 2; return box(o.x - R, o.y - R, o.x + R, o.y + R); }
    case 'nucleus': return box(o.x - o.r, o.y - o.r, o.x + o.r, o.y + o.r);
    case 'particle': { const a = o.angle * Math.PI / 180; return box(Math.min(o.x, o.x + Math.cos(a) * o.len) - 0.1, Math.min(o.y, o.y + Math.sin(a) * o.len) - 0.1, Math.max(o.x, o.x + Math.cos(a) * o.len) + 0.1, Math.max(o.y, o.y + Math.sin(a) * o.len) + 0.1); }
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
    case 'qpot': case 'rect': case 'ellipse': case 'nnet': return box(o.x, o.y, o.x + o.w, o.y + o.h);
    case 'fbox': return box(o.x - o.w / 2, o.y - o.h / 2, o.x + o.w / 2, o.y + o.h / 2);
    case 'poly': { const xs = o.pts.map(q => q[0]), ys = o.pts.map(q => q[1]); return box(Math.min(...xs) - 0.03, Math.min(...ys) - 0.03, Math.max(...xs) + 0.03, Math.max(...ys) + 0.03); }
    case 'bezier': { const pts = bezierPoints(o, 24); return box(Math.min(...pts.map(q => q.x)) - 0.03, Math.min(...pts.map(q => q.y)) - 0.03, Math.max(...pts.map(q => q.x)) + 0.03, Math.max(...pts.map(q => q.y)) + 0.03); }
  }
  return null;
}

/** points along a cubic Bézier (x1,y1) → (cx1,cy1), (cx2,cy2) → (x2,y2) */
export function bezierPoints(o, n = 32) {
  const out = [];
  for (let i = 0; i <= n; i++) { const t = i / n, u = 1 - t, a = u * u * u, b = 3 * u * u * t, c = 3 * u * t * t, d = t * t * t; out.push({x: a * o.x1 + b * o.cx1 + c * o.cx2 + d * o.x2, y: a * o.y1 + b * o.cy1 + c * o.cy2 + d * o.y2}); }
  return out;
}
/** a freehand stroke made plain: Ramer–Douglas–Peucker with tolerance tol (world units), at most max points */
export function simplifyPath(pts, tol, max = 200) {
  if (pts.length < 3) return pts.slice();
  const keep = new Uint8Array(pts.length); keep[0] = keep[pts.length - 1] = 1;
  const stack = [[0, pts.length - 1]];
  while (stack.length) {
    const [a, b] = stack.pop(), A = pts[a], B = pts[b], dx = B.x - A.x, dy = B.y - A.y, L = Math.hypot(dx, dy) || 1e-12;
    let best = -1, bd = tol;
    for (let i = a + 1; i < b; i++) { const d = Math.abs((pts[i].x - A.x) * dy - (pts[i].y - A.y) * dx) / L; if (d > bd) { bd = d; best = i; } }
    if (best > 0) { keep[best] = 1; stack.push([a, best], [best, b]); }
  }
  let out = pts.filter((_, i) => keep[i]);
  if (out.length > max) out = simplifyPath(out, tol * 2, max);
  return out;
}

/** the world rectangle every object fits in, with a margin */
export function sceneBounds(scene) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  const add = (x, y) => { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); };
  const geo = scene.objects.some(o => GEO_TYPES.includes(o.type)) ? computeGeometry(scene) : null;
  for (const o of scene.objects) {
    if (geo && GEO_TYPES.includes(o.type)) { const b = geoExtent(geo, o); if (b) { add(b.x, b.y); add(b.x + b.w, b.y + b.h); } continue; }
    if (isBody(o)) { const p = bodyPose(scene, o), r = Math.max(bodyHalfWidth(o), bodyHalfHeight(o)) * 1.5; add(p.x - r, p.y - r); add(p.x + r, p.y + r); continue; }
    const b = objectExtent(o);
    if (b) { add(b.x, b.y); add(b.x + b.w, b.y + b.h); }
  }
  if (!Number.isFinite(x0)) return {x: -0.5, y: -0.5, w: 4, h: 3};
  const m = Math.max(0.25, 0.08 * Math.max(x1 - x0, y1 - y0));
  return {x: x0 - m, y: y0 - m, w: Math.max(0.5, x1 - x0 + 2 * m), h: Math.max(0.5, y1 - y0 + 2 * m)};
}

/* what the vision model is asked to write (community/src/workshop-scene.js); kept here so it follows the schema */
export const VISION_OBJECT_TYPES = ['block', 'ball', 'wheel', 'floor', 'ceiling', 'wall', 'incline', 'pulley', 'pivot', 'plank', 'string', 'rod', 'spring', 'force',
  'element', 'ground', 'charge', 'plate', 'field', 'cwire', 'current', 'solenoid', 'magnet', 'rails',
  'cylinder', 'container', 'reservoir', 'graph', 'curve',
  'lens', 'mirror', 'prism', 'slab', 'oarrow', 'ray', 'screen',
  'wave', 'well', 'spacetime',
  'label', 'arc', 'dim', 'line', 'vector', 'panel', 'rect', 'ellipse'];
export const UNSURE_FIELDS = ['object', 'position', 'mass', 'angle', 'mu', 'k', 'length', 'connection', 'velocity', 'force', 'label', 'value', 'charge', 'kind', 'focal'];
/** every field the vision model may write for VISION_OBJECT_TYPES, as one JSON-schema property each (enums merged) */
export function visionProperties() {
  const props = {};
  for (const t of VISION_OBJECT_TYPES) for (const [k, f] of Object.entries(FIELDS[t])) {
    if (k in COMMON_FIELDS || k in PHYS_FIELDS) continue;
    const s = f.k === 'num' ? {type: 'number'} : f.k === 'bool' ? {type: 'boolean'} : f.k === 'refs' ? {type: 'array', items: {type: 'string'}} : f.k === 'enum' ? {type: 'string', enum: [...f.list]} : {type: 'string'};
    const old = props[k];
    if (!old) props[k] = s;
    else if (old.type !== s.type) throw new Error('vision field ' + k + ' has two kinds');
    else if (s.enum) props[k] = {type: 'string', enum: [...new Set([...(old.enum || []), ...s.enum])]};
  }
  return props;
}

/** The scene schema in a compact, machine-readable form, for a model asked to write or change a scene (the server's
 *  POST /api/workshop/ai/scene imports it for its prompt): every type with its domain, the references it needs and
 *  each field as [kind, default, …] — num: [min, max], enum: [values], txt: max length, ref/refs: the types it may
 *  name. The fields every object has (lw, ls, lock, style) are listed once under common. Plain JSON, no functions. */
export function sceneSchemaForAI() {
  const field = d => d.k === 'num' ? ['num', d.d, d.min, d.max] : d.k === 'enum' ? ['enum', d.d, [...d.list]] : d.k === 'bool' ? ['bool', d.d]
    : d.k === 'ref' ? ['ref', [...d.types]] : d.k === 'refs' ? ['refs', [...d.types], d.max] : d.k === 'pts' ? ['pts', d.max] : [d.k, d.d, d.max];
  const types = {};
  for (const [t, F] of Object.entries(FIELDS)) {
    const fields = {};
    for (const [k, d] of Object.entries(F)) if (!(k in COMMON_FIELDS)) fields[k] = field(d);
    types[t] = {domain: TYPE_DOMAIN[t], ...(REQUIRED_REFS[t] ? {needs: [...REQUIRED_REFS[t]]} : {}), fields};
  }
  const out = {format: SCENE_FORMAT, version: SCENE_VERSION, maxObjects: MAX_OBJECTS,
    units: 'lengths in metres of the drawing (y up), masses kg, forces N, angles degrees; keep the figure within about 0..6 m',
    top: {title: ['txt', '', 80], g: ['num', 9.8, 0.1, 30], grid: ['num', 0.1, 0.01, 1], style: ['enum', 'textbook', [...STYLE_KEYS]], view: 'optional {x,y,w,h}', values: ['bool', false], gravityOn: ['bool', true], drag: ['num', 0, 0, 50]},
    common: Object.fromEntries(Object.entries(COMMON_FIELDS).map(([k, d]) => [k, field(d)])),
    ids: 'a letter, then letters, digits, _ or - (at most 24), unique',
    labels: 'TeX-like: m_1, \\theta, \\vec{F}, $…$ for maths, \\ce{H2O} for chemistry',
    expressions: 'curve expr: + - * / ^, sin cos tan exp ln log sqrt abs …, pi, e, comparisons and c ? a : b; variable x (t for param and polar); params "a=1 [0, 2], k=3"',
    domains: Object.fromEntries(Object.entries(DOMAINS).map(([d, l]) => [d, [...l]])), types};
  /* the same as text for a prompt: one line a type, "type {field,…}" and then each field's kind, default and range */
  const one = ([k, d]) => d[0] === 'num' ? `${k}=${d[1]} [${d[2]},${d[3]}]` : d[0] === 'enum' ? `${k}:${d[2].join('|')}` : d[0] === 'bool' ? `${k}:bool` : d[0] === 'ref' ? `${k}→${d[1].join('|')}` : d[0] === 'refs' ? `${k}→[${d[1].join('|')}]` : d[0] === 'pts' ? `${k}:[[x,y],…]` : `${k}:${d[0]}≤${d[2]}`;
  out.text = [`Scene ${SCENE_FORMAT} v${SCENE_VERSION}: {title, g, grid, style (${STYLE_KEYS.join('|')}), view {x,y,w,h}, objects: [{id, type, …fields}]}, at most ${MAX_OBJECTS} objects.`,
    `Units: ${out.units}. ids: ${out.ids}. Labels: ${out.labels}. Formulas: ${out.expressions}.`,
    `Every object may also have: ${Object.entries(out.common).map(one).join(', ')}.`,
    ...Object.entries(types).map(([t, d]) => `${t} {${Object.keys(d.fields).join(',')}}${d.needs ? ' needs ' + d.needs.join(',') : ''} — ${Object.entries(d.fields).map(one).join('; ')}`)].join('\n');
  return out;
}
