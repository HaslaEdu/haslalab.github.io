/* The scene of the Workshop's figure and simulation editor (#/workshop/draw, draw.html). One plain JSON object is both
   the exam figure and the system the simulation runs, so a figure a teacher draws can be played and a photo read by
   the AI (community/src/workshop-scene.js) can be checked against the same rules. This file is shared: the browser
   imports it (draw.js, draw-render.mjs, draw-physics.mjs) and so does the community Worker. No DOM, no network.

   Scene, version 1 (all lengths in metres, masses in kg, forces in N, angles in degrees, y pointing up):
     {format:'haslalab-scene', version:1, title:'', g:9.8, grid:0.1, view:{x,y,w,h}, objects:[…]}
   view is the part of the world the figure shows (optional; the editor fits one). At most MAX_OBJECTS objects, each
   with an id (a letter, then letters, digits, _ or -, up to 24) unique in the scene and one of these types:
     bodies
       block    x,y (centre, when free) w,h mass label  on at  vx,vy showV vLabel
       ball     x,y r mass label  on at  vx,vy showV vLabel trail
                on: '' (free or hanging) or the id of a floor or an incline the body rests on; then at is the distance
                along that surface from its start to the body's foot, and x,y follow from it. vx,vy is the velocity at
                t = 0 (for a body on a surface, its part along the surface counts).
     surfaces and fixed points
       floor    x,y (left end of the top) w mu hatch        a horizontal surface, friction coefficient mu
       ceiling  x,y (left end of the underside) w hatch
       wall     x,y (bottom) h side ('left': solid to the left of x, 'right': to the right)
       incline  x,y (left end of the base) angle length (of the slope) mu flip angleLabel
                rises to the right from (x,y) unless flip, then it rises to the left and its slope ends at (x,y)
       pulley   x,y r mount ('' or a ceiling, incline, floor or wall it is fixed to)   fixed, massless, frictionless
       pivot    x,y                                                                  a fixed point
     connections
       string   a b over:[pulley ids] mode label    ends: bodies or a pivot; inextensible and massless; it can go slack.
                mode 'conical' (a pivot to one body, no pulleys): the body goes round a horizontal circle.
       rod      a (pivot) b (body) mode label       a rigid massless rod
       spring   a b k L0 coils label                ends: bodies, pivots, walls, ceilings, floors; L0 natural length
       force    on (body) F angle (from +x, anticlockwise) len (arrow length drawn) label   a constant applied force
     figure marks (drawn only)
       label    x,y text size     text: $…$ is maths; m_1, v^2, \theta, \mu … are understood
       dim      x1,y1,x2,y2 offset text            a dimension line
       arc      x,y r from to text                 an angle mark from `from` to `to` degrees, anticlockwise
       axes     x,y lx ly xlabel ylabel
       line     x1,y1,x2,y2 dash
   validateScene() checks every field (type, range, references) and returns the normalised scene. */

export const SCENE_FORMAT = 'haslalab-scene', SCENE_VERSION = 1, MAX_OBJECTS = 60;
export const BODY_TYPES = ['block', 'ball'];
export const SURFACE_TYPES = ['floor', 'incline'];
export const ANCHOR_TYPES = ['pivot', 'ceiling', 'wall', 'floor'];
export const MARK_TYPES = ['label', 'dim', 'arc', 'axes', 'line'];
const ID = /^[A-Za-z][A-Za-z0-9_-]{0,23}$/;
const COORD = 200, SPEED = 300;

/* field kinds: [kind, default, min, max] for numbers; texts carry their length */
const num = (d, min, max) => ({k: 'num', d, min, max});
const txt = (d, max) => ({k: 'txt', d, max});
const bool = d => ({k: 'bool', d});
const ref = (types, d = '') => ({k: 'ref', d, types});
const pick = (d, list) => ({k: 'enum', d, list});
const X = num(0, -COORD, COORD), Y = num(0, -COORD, COORD);
const MOTION = {vx: num(0, -SPEED, SPEED), vy: num(0, -SPEED, SPEED), showV: bool(false), vLabel: txt('v_0', 24)};
export const FIELDS = {
  block: {x: X, y: Y, w: num(0.4, 0.02, 20), h: num(0.3, 0.02, 20), mass: num(1, 0.001, 10000), label: txt('', 40), on: ref(SURFACE_TYPES), at: num(0, -COORD, COORD), ...MOTION},
  ball: {x: X, y: Y, r: num(0.1, 0.01, 5), mass: num(1, 0.001, 10000), label: txt('', 40), on: ref(SURFACE_TYPES), at: num(0, -COORD, COORD), ...MOTION, trail: bool(false)},
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
  label: {x: X, y: Y, text: txt('', 80), size: num(16, 8, 48)},
  dim: {x1: X, y1: Y, x2: X, y2: Y, offset: num(0.15, -10, 10), text: txt('', 40)},
  arc: {x: X, y: Y, r: num(0.3, 0.02, 20), from: num(0, -360, 360), to: num(30, -360, 360), text: txt('', 24)},
  axes: {x: X, y: Y, lx: num(1, 0, 100), ly: num(1, 0, 100), xlabel: txt('x', 12), ylabel: txt('y', 12)},
  line: {x1: X, y1: Y, x2: X, y2: Y, dash: bool(true)}
};
export const TYPES = Object.keys(FIELDS);
/* references that must name an existing object, and which must not be the same */
const REQUIRED_REFS = {string: ['a', 'b'], rod: ['a', 'b'], spring: ['a', 'b'], force: ['on']};
export const isBody = o => !!o && BODY_TYPES.includes(o.type);

/* text: no control characters, the length cut; for text the AI wrote, only what a physics label needs */
const AI_TEXT = /^[A-Za-z0-9 _^{}\\.,=+\-()/'°%·×θμαβγωπφλρσΔ가-힣ㄱ-ㅎ]*$/u;
function cleanText(v, max, ai) {
  let s = String(v).normalize('NFC').replace(/[\u0000-\u001f\u007f-\u009f\u2028\u2029]/g, ' ').replace(/\s+/g, ' ').trim();
  if (s.length > max) s = s.slice(0, max).trim();
  if (ai && (s.length > 24 || !AI_TEXT.test(s))) return null;
  return s;
}

/** Validate and normalise a scene. strict (default): every problem is an error. lenient: an object with a problem is
 *  dropped (and whatever refers to it), a number out of range is brought into range; each is reported. aiText: labels
 *  must look like physics labels (used for scenes the vision model wrote). Returns {ok, scene, errors, notes}. */
export function validateScene(input, {lenient = false, aiText = false} = {}) {
  const errors = [], notes = [];
  const err = (code, id, field) => { errors.push({code, ...(id ? {id} : {}), ...(field ? {field} : {})}); };
  if (!input || typeof input !== 'object' || Array.isArray(input)) return {ok: false, scene: blankScene(), errors: [{code: 'not_object'}], notes};
  if (input.format !== undefined && input.format !== SCENE_FORMAT) err('bad_format');
  if (input.version !== undefined && input.version !== SCENE_VERSION) err('bad_version');
  const top = (k, d, min, max) => {
    const v = input[k];
    if (v === undefined || v === null) return d;
    if (typeof v !== 'number' || !Number.isFinite(v)) { err('bad_number', null, k); return d; }
    if (v < min || v > max) { if (lenient) { notes.push({code: 'clamped', field: k}); return Math.min(max, Math.max(min, v)); } err('out_of_range', null, k); return d; }
    return v;
  };
  const scene = {format: SCENE_FORMAT, version: SCENE_VERSION, title: '', g: top('g', 9.8, 0.1, 30), grid: top('grid', 0.1, 0.01, 1), objects: []};
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
    if (!FIELDS[type]) { err('bad_type', id); continue; }
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
      } else if (f.k === 'bool') {
        if (typeof v !== 'boolean') { err('bad_bool', id, k); bad = true; continue; }
        o[k] = v;
      } else if (f.k === 'enum') {
        if (!f.list.includes(v)) { err('bad_enum', id, k); bad = true; continue; }
        o[k] = v;
      } else if (f.k === 'ref') {
        if (typeof v !== 'string' || (v && !ID.test(v))) { err('bad_ref', id, k); bad = true; continue; }
        o[k] = v;
      } else if (f.k === 'refs') {
        if (!Array.isArray(v) || v.length > f.max || v.some(x => typeof x !== 'string' || !ID.test(x)) || new Set(v).size !== v.length) { err('bad_ref', id, k); bad = true; continue; }
        o[k] = [...v];
      }
    }
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
export const blankScene = () => ({format: SCENE_FORMAT, version: SCENE_VERSION, title: '', g: 9.8, grid: 0.1, objects: []});
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
const T = (title, objects, view, extra = {}) => ({format: SCENE_FORMAT, version: SCENE_VERSION, title, g: 9.8, grid: 0.1, view, ...extra,
  objects: objects.map(o => ({...defaults(o.type), ...o}))});
export const TEMPLATE_KEYS = ['atwood', 'incline_pulley', 'spring_block', 'pendulum', 'projectile', 'conical', 'vertical_circle'];
export const TEMPLATE_NAMES = {
  atwood: {ko: '애트우드 기계', en: 'Atwood machine'}, incline_pulley: {ko: '빗면 · 도르래 · 매달린 물체', en: 'Incline, pulley and hanging mass'},
  spring_block: {ko: '용수철에 달린 물체', en: 'Block on a spring'}, pendulum: {ko: '단진자', en: 'Simple pendulum'},
  projectile: {ko: '포물선 운동', en: 'Projectile'}, conical: {ko: '원뿔 진자', en: 'Conical pendulum'}, vertical_circle: {ko: '연직면 원운동', en: 'Vertical circle'}
};
export function template(key, lang = 'ko') {
  const name = (TEMPLATE_NAMES[key] || {})[lang === 'en' ? 'en' : 'ko'] || '';
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
    {id: 'ln', type: 'line', x1: 1.5, y1: 2.4, x2: 1.5, y2: 0.7, dash: true},
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
    {id: 'ln', type: 'line', x1: 1.5, y1: 2.6, x2: 1.5, y2: 1.0, dash: true},
    {id: 'th', type: 'arc', x: 1.5, y: 2.6, r: 0.4, from: -90, to: -60, text: '\\theta'}
  ], {x: 0.35, y: 0.75, w: 2.3, h: 2.1}); }
  if (key === 'vertical_circle') return T(name, [
    {id: 'pv', type: 'pivot', x: 1.5, y: 1.5},
    {id: 'b1', type: 'ball', x: 1.5, y: 0.5, r: 0.08, mass: 0.3, label: 'm', vx: 6, showV: true, vLabel: 'v_0', trail: true},
    {id: 's1', type: 'string', a: 'pv', b: 'b1', label: 'r'}
  ], {x: 0.2, y: 0.15, w: 2.6, h: 2.7});
  return {...blankScene(), view: {x: -0.5, y: -0.5, w: 4, h: 3}};
}

/** the world rectangle every object fits in, with a margin */
export function sceneBounds(scene) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  const add = (x, y) => { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); };
  for (const o of scene.objects) {
    if (isBody(o)) { const p = bodyPose(scene, o), r = Math.max(bodyHalfWidth(o), bodyHalfHeight(o)) * 1.5; add(p.x - r, p.y - r); add(p.x + r, p.y + r); }
    else if (o.type === 'floor' || o.type === 'ceiling') { add(o.x, o.y); add(o.x + o.w, o.y + (o.type === 'floor' ? -0.15 : 0.15)); }
    else if (o.type === 'wall') { add(o.x, o.y); add(o.x + (o.side === 'left' ? -0.15 : 0.15), o.y + o.h); }
    else if (o.type === 'incline') { const c = inclineCorners(o); add(c.foot.x, c.foot.y - 0.1); add(c.top.x, c.top.y); add(c.right.x, c.right.y); }
    else if (o.type === 'pulley') { add(o.x - o.r, o.y - o.r); add(o.x + o.r, o.y + o.r); }
    else if (o.type === 'pivot' || o.type === 'label') add(o.x, o.y);
    else if (o.type === 'dim' || o.type === 'line') { add(o.x1, o.y1); add(o.x2, o.y2); }
    else if (o.type === 'arc') { add(o.x - o.r, o.y - o.r); add(o.x + o.r, o.y + o.r); }
    else if (o.type === 'axes') { add(o.x, o.y); add(o.x + o.lx, o.y + o.ly); }
  }
  if (!Number.isFinite(x0)) return {x: -0.5, y: -0.5, w: 4, h: 3};
  const m = Math.max(0.25, 0.08 * Math.max(x1 - x0, y1 - y0));
  return {x: x0 - m, y: y0 - m, w: Math.max(0.5, x1 - x0 + 2 * m), h: Math.max(0.5, y1 - y0 + 2 * m)};
}

/* what the vision model is asked to write (community/src/workshop-scene.js); kept here so it follows the schema */
export const VISION_OBJECT_TYPES = ['block', 'ball', 'floor', 'ceiling', 'wall', 'incline', 'pulley', 'pivot', 'string', 'rod', 'spring', 'force', 'label', 'arc'];
export const UNSURE_FIELDS = ['object', 'position', 'mass', 'angle', 'mu', 'k', 'length', 'connection', 'velocity', 'force', 'label', 'value'];
