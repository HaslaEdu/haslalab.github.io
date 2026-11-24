/* The figure editor's simulation (draw.js): a deterministic solver written for the systems the editor's scenes describe
   (draw-scene.mjs). Every body of a scene is put into one of four kinds of system, each moved with reduced
   coordinates by the classical fourth-order Runge–Kutta method at a fixed step (1 ms by default):
     chain     two bodies joined by a string, over any number of fixed ideal pulleys; each end hangs straight down or
               rests on a floor or an incline. One coordinate s: how far the string has moved from the first end
               towards the second. M s'' = Σ F·d (gravity, applied forces, springs to fixed points) minus friction.
     pendulum  a body on a string or a rod from a pivot: the angle θ from the downward vertical, mLθ'' = F·t̂.
               mode 'conical' turns at the constant rate ω = √(g / (L cos α)) that keeps the angle α.
     surface   bodies resting on floors or inclines and not on a string: one coordinate along the surface each,
               joined to each other or to fixed points by springs.
     free      bodies in the air (a projectile, a mass hanging from a spring): x, y each, gravity and springs.
   Friction is Coulomb friction with one coefficient μ for sticking and sliding (static and kinetic the same). While a
   body moves, friction is −μN in the direction of motion; when its speed reaches zero within a step the step is cut
   there, and the body stays at rest while the other forces along the surface are at most μN.
   Events end a system's motion and are found within the step by bisection, so a time like the projectile's landing is
   exact to well under a millisecond: a string going slack (tension below zero), a body reaching a pulley, the end of
   its surface or the body it is tied to, a body landing on a floor or an incline, a body leaving its surface
   (N below zero), two bodies on one surface touching. Systems outside these kinds are reported in `unsupported`
   with a code, and the figure stays a figure. */
import {isBody, surfaceFrame, bodyPose, attachPoint, anchorPoint, stringPath, bodyHalfHeight, bodyHalfWidth, vec, INERTIA, boundExpr, isPhysShape, CONE_TILT} from './draw-scene.mjs?v=0fa3728066f3';

export const SIM_DT = 1e-3;
const EPS_V = 1e-9;

/* one RK4 step of dq/dt = f(q) (no system here depends on t explicitly) */
function rk4(f, q, h) {
  const n = q.length, k1 = f(q), y = new Float64Array(n);
  for (let i = 0; i < n; i++) y[i] = q[i] + h / 2 * k1[i];
  const k2 = f(y);
  for (let i = 0; i < n; i++) y[i] = q[i] + h / 2 * k2[i];
  const k3 = f(y);
  for (let i = 0; i < n; i++) y[i] = q[i] + h * k3[i];
  const k4 = f(y), out = new Float64Array(n);
  for (let i = 0; i < n; i++) out[i] = q[i] + h / 6 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]);
  return out;
}
const sgn = v => v > 0 ? 1 : v < 0 ? -1 : 0;

/** the part of the figure a free body rests on or hangs from that the solver does not compute (a plank, a track, a
 *  line, a drawn shape's edge, a liquid it stands in), or null. Contact: a point of the part within a small tolerance
 *  of the body's outline. */
export function heldBy(scene, b) {
  const p = bodyPose(scene, b), round = b.type === 'ball' || b.type === 'wheel', hw = bodyHalfWidth(b), hh = bodyHalfHeight(b), tol = Math.max(0.004, 0.06 * Math.min(hw, hh));
  const touches = q => round ? Math.hypot(q.x - p.x, q.y - p.y) <= b.r + tol : Math.abs(q.x - p.x) <= hw + tol && Math.abs(q.y - p.y) <= hh + tol;
  const seg = (a, c, n = 48) => { for (let i = 0; i <= n; i++) if (touches({x: a.x + (c.x - a.x) * i / n, y: a.y + (c.y - a.y) * i / n})) return true; return false; };
  const ring = pts => pts.some((q, i) => i && seg(pts[i - 1], q));
  for (const o of scene.objects) {
    if (o === b) continue;
    const T = o.type;
    if (T === 'plank') { const a = o.rot * Math.PI / 180, u = {x: Math.cos(a), y: Math.sin(a)}, n = {x: -u.y, y: u.x}, c = (s1, t) => ({x: o.x + u.x * s1 + n.x * t, y: o.y + u.y * s1 + n.y * t}), L = o.len / 2, t2 = o.thick / 2;
      if (ring([c(-L, t2), c(L, t2), c(L, -t2), c(-L, -t2), c(-L, t2)])) return o.id; }
    else if (T === 'track') { const pts = []; for (let i = 0; i <= 120; i++) { const t = (o.from + (o.to - o.from) * i / 120) * Math.PI / 180; pts.push({x: o.x + o.r * Math.cos(t), y: o.y + o.r * Math.sin(t)}); } if (ring(pts)) return o.id; }
    else if (T === 'line' || T === 'vector' || T === 'cwire') { if (seg({x: o.x1, y: o.y1}, {x: o.x2, y: o.y2})) return o.id; }
    else if (T === 'poly') { const pts = o.pts.map(q => ({x: q[0], y: q[1]})); if (ring(o.closed ? [...pts, pts[0]] : pts)) return o.id; }
    else if (T === 'rect' || T === 'region' && o.shape === 'rect') { if (!o.rot && ring([{x: o.x, y: o.y}, {x: o.x + o.w, y: o.y}, {x: o.x + o.w, y: o.y + o.h}, {x: o.x, y: o.y + o.h}, {x: o.x, y: o.y}])) return o.id; }
    else if (T === 'container' || T === 'utube') { if (p.x > o.x && p.x < o.x + o.w && p.y - hh >= o.y - tol && p.y - hh < o.y + o.h) return o.id; }
  }
  return null;
}

/** Build the simulation of a validated scene. */
export function buildSim(scene, {dt = SIM_DT} = {}) {
  const g = scene.g, G = {x: 0, y: -g};
  const byId = new Map(scene.objects.map(o => [o.id, o]));
  const bodies = scene.objects.filter(isBody);
  const strings = scene.objects.filter(o => o.type === 'string' || o.type === 'rod');
  const springs = scene.objects.filter(o => o.type === 'spring');
  const forces = scene.objects.filter(o => o.type === 'force');
  const floors = scene.objects.filter(o => o.type === 'floor'), inclines = scene.objects.filter(o => o.type === 'incline');
  const applied = id => forces.filter(f => f.on === id).reduce((a, f) => ({x: a.x + f.F * Math.cos(f.angle * Math.PI / 180), y: a.y + f.F * Math.sin(f.angle * Math.PI / 180)}), {x: 0, y: 0});
  const unsupported = [], owner = new Map(), systems = [];
  const reject = (ids, code) => { unsupported.push({ids, code}); ids.forEach(id => owner.set(id, 'none')); };

  /* springs: their fixed ends are fixed where they are at t = 0 */
  const springEnds = s => [byId.get(s.a), byId.get(s.b)];
  const anchors = new Map();
  for (const s of springs) {
    const [A, B] = springEnds(s);
    for (const [me, other] of [[A, B], [B, A]]) if (!isBody(me)) {
      const from = isBody(other) ? bodyPose(scene, other) : {x: other.x, y: other.y};
      anchors.set(s.id + ':' + me.id, anchorPoint(me, from));
    }
  }
  /* the force of a spring on body `id` at the given centres (map id → pose) */
  const springForce = (s, id, poseOf) => {
    const [A, B] = springEnds(s), me = A.id === id ? A : B, other = me === A ? B : A;
    const pMe = poseOf(me.id), otherPt = isBody(other) ? poseOf(other.id) : anchors.get(s.id + ':' + other.id);
    const aMe = attachPoint(scene, me, otherPt, pMe), aOther = isBody(other) ? attachPoint(scene, other, aMe, poseOf(other.id)) : otherPt;
    const d = vec.sub(aMe, aOther), L = vec.len(d);
    return {F: vec.mul(vec.unit(d), -s.k * (L - s.L0)), L};
  };
  const springsOf = id => springs.filter(s => s.a === id || s.b === id);
  const springEnergy = poseOf => springs.reduce((E, s) => {
    const [A, B] = springEnds(s), body = isBody(A) ? A : B;
    if (!owner.has(body.id) || owner.get(body.id) === 'none') return E;
    const {L} = springForce(s, body.id, poseOf);
    return E + 0.5 * s.k * (L - s.L0) ** 2;
  }, 0);
  /* landing: for each floor and incline below a body, a value that goes through zero when the body touches it */
  /* (one entry per surface, always, so the lists before and after a step line up; far from it the value is large) */
  const FAR = 1e9;
  const landing = (b, p) => {
    const hh = bodyHalfHeight(b), hw = bodyHalfWidth(b);
    return [...floors.map(f => ({code: 'landed', id: b.id, on: f.id, g: p.x >= f.x - hw && p.x <= f.x + f.w + hw ? p.y - hh - f.y : FAR})),
      ...inclines.map(s => { const fr = surfaceFrame(s), along = vec.dot(vec.sub(p, fr.p0), fr.u);
        return {code: 'landed', id: b.id, on: s.id, g: along >= 0 && along <= fr.length ? vec.dot(vec.sub(p, fr.p0), fr.n) - hh : FAR}; })];
  };

  /* ── stacks: a body resting on a block that rests on a floor or an incline ──
     Coordinates along the lower surface's direction u: the lower block's place at₁ and velocity v₁, the upper body's
     place on the block's top face at₂ and its own velocity v₂. Friction: μ of the surface under the lower block, and μ
     of the block's top face (its field mu) between the two. Each contact either sticks or slides (Coulomb, one μ);
     the modes are found at the start of every step by trying "sticks" and turning to "slides" where the friction it
     needs is more than μN. */
  const tiedTo = id => strings.some(s => s.a === id || s.b === id) || springs.some(s => s.a === id || s.b === id);
  for (const top of bodies) {
    const bot = byId.get(top.on);
    if (!bot || bot.type !== 'block' || owner.has(top.id)) continue;
    const base = byId.get(bot.on);
    const ids = [bot.id, top.id];
    if (!base || base.type === 'block' || owner.has(bot.id) || bodies.some(b => b !== top && b.on === bot.id) || bodies.some(b => b.on === top.id) || tiedTo(top.id) || tiedTo(bot.id)) { reject(ids, 'stack_unsupported'); continue; }
    ids.forEach(id => owner.set(id, 'stack'));
    systems.push(stackSystem(bot, top, base));
  }
  function stackSystem(B, Tb, S) {
    const fr = surfaceFrame(S, scene), u = fr.u, n = fr.n, m1 = B.mass, m2 = Tb.mass, M = m1 + m2, mu1 = fr.mu, mu2 = B.mu;
    const ang = Math.atan2(u.y, u.x), hw1 = B.w / 2, hw2 = bodyHalfWidth(Tb), h2 = bodyHalfHeight(Tb);
    const q = Float64Array.from([B.at, vec.dot({x: B.vx, y: B.vy}, u), Tb.at, vec.dot({x: Tb.vx, y: Tb.vy}, u), 0, 0]);
    const F1 = vec.add(vec.mul(G, m1), applied(B.id)), F2 = vec.add(vec.mul(G, m2), applied(Tb.id));
    const Q1 = vec.dot(F1, u), Q2 = vec.dot(F2, u), N2 = Math.max(0, -vec.dot(F2, n)), N1 = Math.max(0, -vec.dot(F1, n) + N2);
    const modes = {m1: 0, m12: 0};
    const solve = (m1s, m12s) => {
      let a1, a2, f1, f2;
      if (m12s === 0) {
        if (m1s === 0) { a1 = a2 = 0; f1 = -(Q1 + Q2); f2 = -Q2; }
        else { f1 = -m1s * mu1 * N1; a1 = a2 = (Q1 + Q2 + f1) / M; f2 = m2 * a2 - Q2; }
      } else {
        f2 = -m12s * mu2 * N2; a2 = (Q2 + f2) / m2;
        const net = Q1 - f2;
        if (m1s === 0) { f1 = -net; a1 = 0; } else { f1 = -m1s * mu1 * N1; a1 = (net + f1) / m1; }
      }
      return {a1, a2, f1, f2};
    };
    const posesAt = qq => {
      const c1 = vec.add(vec.add(fr.p0, vec.mul(u, qq[0])), vec.mul(n, B.h / 2)), p0B = vec.add(vec.sub(c1, vec.mul(u, hw1)), vec.mul(n, B.h / 2));
      const c2 = vec.add(vec.add(p0B, vec.mul(u, qq[2])), vec.mul(n, h2));
      return new Map([[B.id, {x: c1.x, y: c1.y, angle: ang, at: qq[0]}], [Tb.id, {x: c2.x, y: c2.y, angle: Tb.type === 'block' ? ang : 0, at: qq[2]}]]);
    };
    return {kind: 'stack', id: B.id + '+' + Tb.id, ids: [B.id, Tb.id], q, t: 0, modes, done: null,
      prepare() {
        const v1 = this.q[1], rel = this.q[3] - this.q[1];
        modes.m1 = Math.abs(v1) > EPS_V ? sgn(v1) : 0; modes.m12 = Math.abs(rel) > EPS_V ? sgn(rel) : 0;
        for (let k = 0; k < 4; k++) {
          const r = solve(modes.m1, modes.m12); let changed = false;
          if (modes.m12 === 0 && Math.abs(r.f2) > mu2 * N2 + 1e-12) { modes.m12 = -sgn(r.f2); changed = true; }
          else if (modes.m1 === 0 && Math.abs(r.f1) > mu1 * N1 + 1e-12) { modes.m1 = -sgn(r.f1); changed = true; }
          if (!changed) break;
        }
      },
      f(qq) { const r = solve(modes.m1, modes.m12), out = new Float64Array(6);
        out[0] = qq[1]; out[1] = r.a1; out[2] = qq[3] - qq[1]; out[3] = r.a2;
        out[4] = (modes.m1 ? -r.f1 * qq[1] : 0) + (modes.m12 ? -r.f2 * (qq[3] - qq[1]) : 0);
        out[5] = vec.dot(applied(B.id), vec.mul(u, qq[1])) + vec.dot(applied(Tb.id), vec.mul(u, qq[3]));
        return out; },
      events(qq) {
        const out = [{code: 'end_of_surface', id: B.id, g: qq[0] - hw1}, {code: 'end_of_surface', id: B.id, g: fr.length - qq[0] - hw1},
          {code: 'end_of_surface', id: Tb.id, g: qq[2] - hw2}, {code: 'end_of_surface', id: Tb.id, g: B.w - qq[2] - hw2}, {code: 'lift_off', id: Tb.id, g: N2}, {code: 'lift_off', id: B.id, g: N1}];
        if (modes.m1 !== 0 && mu1 > 0) out.push({code: 'stick', which: 'm1', g: modes.m1 * qq[1], stop: false});
        if (modes.m12 !== 0 && mu2 > 0) out.push({code: 'stick', which: 'm12', g: modes.m12 * (qq[3] - qq[1]), stop: false});
        return out;
      },
      onStick(ev) { if (ev.which === 'm1') { const d = this.q[1]; this.q[1] = 0; if (modes.m12 === 0) this.q[3] -= d; modes.m1 = 0; } else { this.q[3] = this.q[1]; modes.m12 = 0; } },
      poses(qq = this.q) { return posesAt(qq); },
      velocities(qq = this.q) { return new Map([[B.id, vec.mul(u, qq[1])], [Tb.id, vec.mul(u, qq[3])]]); },
      accel() { const r = solve(modes.m1, modes.m12); return new Map([[B.id, vec.mul(u, r.a1)], [Tb.id, vec.mul(u, r.a2)]]); },
      tensions() { return {}; },
      friction() { const r = solve(modes.m1, modes.m12); return {floor: r.f1, between: r.f2, slipping: modes.m12 !== 0}; },
      forceList(qq = this.q) {
        const r = solve(modes.m1, modes.m12), p = posesAt(qq), l2 = [{kind: 'gravity', v: vec.mul(G, m2)}, {kind: 'normal', v: vec.mul(n, N2)}], l1 = [{kind: 'gravity', v: vec.mul(G, m1)}, {kind: 'normal', v: vec.mul(n, N1)}, {kind: 'normal', v: vec.mul(n, -N2)}];
        if (Math.abs(r.f2) > 1e-9) { l2.push({kind: 'friction', v: vec.mul(u, r.f2)}); l1.push({kind: 'friction', v: vec.mul(u, -r.f2)}); }
        if (Math.abs(r.f1) > 1e-9) l1.push({kind: 'friction', v: vec.mul(u, r.f1)});
        for (const [b, l] of [[B, l1], [Tb, l2]]) { const ap = applied(b.id); if (vec.len(ap) > 0) l.push({kind: 'applied', v: ap}); }
        return new Map([[B.id, l1.map(x => ({...x, at: p.get(B.id)}))], [Tb.id, l2.map(x => ({...x, at: p.get(Tb.id)}))]]);
      },
      energy(qq = this.q) { const p = posesAt(qq); return {K: 0.5 * m1 * qq[1] ** 2 + 0.5 * m2 * qq[3] ** 2, Ug: m1 * g * p.get(B.id).y + m2 * g * p.get(Tb.id).y, Us: 0, heat: qq[4], work: qq[5]}; }
    };
  }

  /* ── chains: a string between two bodies ── */
  for (const s of strings) {
    if (s.type !== 'string') continue;
    const A = byId.get(s.a), B = byId.get(s.b);
    if (!isBody(A) || !isBody(B) || owner.has(A.id) || owner.has(B.id)) continue;
    const path = stringPath(scene, s);
    const ends = [[A, path.a, path.segs[0][1], -1], [B, path.b, path.segs[path.segs.length - 1][0], 1]].map(([b, att, next, eps]) => {
      const pose = bodyPose(scene, b), out = vec.unit(vec.sub(att, next));
      let d, frame = null;
      if (b.on) { frame = surfaceFrame(byId.get(b.on), scene); const sigma = sgn(vec.dot(out, frame.u)) || 1; d = vec.mul(frame.u, eps * sigma); }
      else { if (Math.abs(out.y) < 0.985) return null; d = vec.mul(out, eps); }
      /* a hanging body stops where its top meets the rim of the pulley it hangs from, not at the string's tangent point */
      const w = path.wraps[eps < 0 ? 0 : path.wraps.length - 1];
      let room = 0.01;
      if (w && !frame) { const dx = Math.max(0, Math.abs(w.c.x - pose.x) - bodyHalfWidth(b)); if (dx < w.r) room += Math.sqrt(w.r * w.r - dx * dx); }
      return {b, id: b.id, m: b.mass, c0: {x: pose.x, y: pose.y}, at0: b.at, angle: pose.angle, d, frame, mu: frame ? frame.mu : 0, next, eps, out, att0: att, room};
    });
    const ids = [A.id, B.id];
    if (ends.some(e => !e)) { reject(ids, 'hanging_not_vertical'); continue; }
    const pulleyLess = !s.over.length;
    if (pulleyLess && !(A.on && B.on)) { reject(ids, 'tied_not_on_surface'); continue; }
    if ([A, B].some(b => springsOf(b.id).some(sp => { const o = byId.get(sp.a === b.id ? sp.b : sp.a); return isBody(o); }))) { reject(ids, 'spring_between_systems'); continue; }
    ids.forEach(id => owner.set(id, 'chain'));
    const M = ends[0].m + ends[1].m;
    const v0 = (ends.reduce((a, e) => a + e.m * vec.dot({x: e.b.vx, y: e.b.vy}, e.d), 0)) / M;
    const posesAt = q => new Map(ends.map(e => [e.id, {x: e.c0.x + q[0] * e.d.x, y: e.c0.y + q[0] * e.d.y, angle: e.angle}]));
    /* the forces on each end other than the string and friction, and the normal force on a surface */
    const ext = (e, poses) => {
      let F = vec.add(vec.mul(G, e.m), applied(e.id));
      for (const sp of springsOf(e.id)) F = vec.add(F, springForce(sp, e.id, id => poses.get(id)).F);
      const N = e.frame ? -vec.dot(F, e.frame.n) : 0;
      return {F, N, Q: vec.dot(F, e.d)};
    };
    const sys = {kind: 'chain', id: s.id, ids, q: Float64Array.from([0, v0, 0, 0]), t: 0, mode: 0, done: null, stickable: ends.some(e => e.mu > 0),
      eval(q) {
        const poses = posesAt(q), parts = ends.map(e => ext(e, poses));
        const Q = parts[0].Q + parts[1].Q, cap = ends.reduce((a, e, i) => a + e.mu * Math.max(0, parts[i].N), 0);
        let a, fr = [0, 0];
        if (this.mode === 0 && Math.abs(q[1]) <= EPS_V) { a = 0; fr = ends.map((e, i) => cap > 0 ? -Q * e.mu * Math.max(0, parts[i].N) / cap : 0); }
        else { const m = this.mode || sgn(q[1]); fr = ends.map((e, i) => -m * e.mu * Math.max(0, parts[i].N)); a = (Q + fr[0] + fr[1]) / M; }
        /* the string's pull on B is along −d_B: m_B a = F_B·d_B + f_B − T */
        const T = parts[1].Q + fr[1] - ends[1].m * a;
        return {poses, parts, Q, cap, a, fr, T};
      },
      prepare() {
        if (Math.abs(this.q[1]) > EPS_V) { this.mode = sgn(this.q[1]); return; }
        const {Q, cap} = (this.mode = 0, this.eval(this.q));
        this.mode = Math.abs(Q) <= cap + 1e-12 ? 0 : sgn(Q);
      },
      f(q) { const r = this.eval(q), heat = -(r.fr[0] + r.fr[1]) * Math.abs(q[1]) * (this.mode === 0 ? 0 : 1);
        const work = ends.reduce((w, e) => w + vec.dot(applied(e.id), e.d) * q[1], 0);
        return Float64Array.from([q[1], this.mode === 0 && Math.abs(q[1]) <= EPS_V ? 0 : r.a, heat, work]); },
      events(q) {
        const r = this.eval(q), out = [{code: 'slack', id: s.id, g: r.T}];
        for (const e of ends) {
          const p = r.poses.get(e.id), att = vec.add(e.att0, vec.mul(e.d, q[0]));
          if (!pulleyLess) out.push({code: 'reached_pulley', id: e.id, g: vec.dot(vec.sub(att, e.next), e.out) - e.room});
          if (e.frame) { const at = e.at0 + q[0] * vec.dot(e.d, e.frame.u), hw = bodyHalfWidth(e.b);
            out.push({code: 'end_of_surface', id: e.id, g: at - hw}, {code: 'end_of_surface', id: e.id, g: e.frame.length - at - hw}, {code: 'lift_off', id: e.id, g: r.parts[ends.indexOf(e)].N}); }
          else out.push(...landing(e.b, p));
        }
        if (this.stickable && this.mode !== 0) out.push({code: 'stick', g: this.mode * q[1], stop: false});
        return out;
      },
      onStick() { this.q[1] = 0; this.mode = 0; },
      poses(q = this.q) { const p = posesAt(q); for (const e of ends) if (e.frame) p.get(e.id).at = e.at0 + q[0] * vec.dot(e.d, e.frame.u); return p; },
      velocities(q = this.q) { return new Map(ends.map(e => [e.id, vec.mul(e.d, q[1])])); },
      accel(q = this.q) { const a = this.eval(q).a; return new Map(ends.map(e => [e.id, vec.mul(e.d, a)])); },
      tensions(q = this.q) { return {[s.id]: Math.max(0, this.eval(q).T)}; },
      forceList(q = this.q) {
        const r = this.eval(q), map = new Map();
        ends.forEach((e, i) => {
          const list = [{kind: 'gravity', v: vec.mul(G, e.m)}], pose = r.poses.get(e.id);
          if (e.frame) { list.push({kind: 'normal', v: vec.mul(e.frame.n, Math.max(0, r.parts[i].N))}); if (Math.abs(r.fr[i]) > 1e-9) list.push({kind: 'friction', v: vec.mul(e.d, r.fr[i])}); }
          const T = Math.max(0, r.T); if (T > 0) list.push({kind: 'tension', v: vec.mul(e.out, -T)});
          const ap = applied(e.id); if (vec.len(ap) > 0) list.push({kind: 'applied', v: ap});
          for (const sp of springsOf(e.id)) list.push({kind: 'spring', v: springForce(sp, e.id, id => r.poses.get(id)).F});
          map.set(e.id, list.map(x => ({...x, at: {x: pose.x, y: pose.y}})));
        });
        return map;
      },
      energy(q = this.q) {
        const p = this.poses(q), K = 0.5 * M * q[1] * q[1], Ug = ends.reduce((u, e) => u + e.m * g * p.get(e.id).y, 0);
        return {K, Ug, Us: springEnergy(id => p.get(id)), heat: q[2], work: q[3]};
      }
    };
    systems.push(sys);
  }

  /* ── pendulums: a body on a string or a rod from a pivot ── */
  for (const s of strings) {
    const A = byId.get(s.a), B = byId.get(s.b), P = [A, B].find(o => o?.type === 'pivot'), b = [A, B].find(isBody);
    if (!P || !b || owner.has(b.id)) continue;
    if (s.type === 'string' && s.over.length) { reject([b.id], 'pivot_over_pulley'); continue; }
    if (b.on) { reject([b.id], 'pendulum_on_surface'); continue; }
    if (springsOf(b.id).length) { reject([b.id], 'pendulum_with_spring'); continue; }
    owner.set(b.id, 'pendulum');
    const d = vec.sub(b, P), L = vec.len(d), m = b.mass, rigid = s.type === 'rod';
    if (L < 1e-6) { reject([b.id], 'zero_length'); continue; }
    if (s.mode === 'conical') {
      const alpha = Math.atan2(Math.abs(d.x), -d.y), side = sgn(d.x) || 1;
      if (!(alpha > 0.01 && alpha < 1.53)) { reject([b.id], 'conical_angle'); continue; }
      const w = Math.sqrt(g / (L * Math.cos(alpha))), R = L * Math.sin(alpha);
      /* the bob turns on a horizontal circle; the figure shows it in an oblique view (CONE_TILT: the circle as an ellipse
         whose height is that fraction of its width), so its drawn y moves with the depth z (z > 0: towards the viewer,
         lower on the page). φ = ω t from the side the figure put it on. */
      const C = {x: P.x, y: P.y - L * Math.cos(alpha)}, T = m * g / Math.cos(alpha);
      const at3 = q => ({x: C.x + side * R * Math.cos(q[0]), y: C.y, z: R * Math.sin(q[0])});
      systems.push({kind: 'conical', id: s.id, ids: [b.id], q: Float64Array.from([0]), t: 0, mode: 0, done: null, omega: w, radius: R, centre: C, side, alpha, length: L, pivot: {x: P.x, y: P.y},
        prepare() {}, f() { return Float64Array.from([w]); }, events() { return []; },
        poses(q = this.q) { const p = at3(q); return new Map([[b.id, {x: p.x, y: p.y - CONE_TILT * p.z, z: p.z, phi: q[0], angle: 0}]]); },
        velocities(q = this.q) { return new Map([[b.id, {x: -side * R * w * Math.sin(q[0]), y: 0, z: R * w * Math.cos(q[0])}]]); },
        accel(q = this.q) { return new Map([[b.id, {x: -side * R * w * w * Math.cos(q[0]), y: 0, z: -R * w * w * Math.sin(q[0])}]]); },
        tensions() { return {[s.id]: T}; },
        /* the forces in 3D, drawn in the same oblique view: gravity, the tension along the string, and their sum, the
           centripetal force m ω² r towards the axis */
        forceList(q = this.q) {
          const p3 = at3(q), p = {x: p3.x, y: p3.y - CONE_TILT * p3.z}, proj = v => ({x: v.x, y: v.y - CONE_TILT * v.z});
          const tv = {x: (P.x - p3.x) * T / L, y: (P.y - p3.y) * T / L, z: -p3.z * T / L}, cv = {x: (C.x - p3.x) * m * w * w, y: 0, z: -p3.z * m * w * w};
          return new Map([[b.id, [{kind: 'gravity', v: vec.mul(G, m)}, {kind: 'tension', v: proj(tv)}, {kind: 'centripetal', v: proj(cv)}].map(x => ({...x, at: p}))]]); },
        energy(q = this.q) { return {K: 0.5 * m * (R * w) ** 2, Ug: m * g * (P.y - L * Math.cos(alpha)), Us: 0, heat: 0, work: 0}; },
        period: 2 * Math.PI / w});
      continue;
    }
    const th0 = Math.atan2(d.x, -d.y), tan0 = {x: Math.cos(th0), y: Math.sin(th0)};
    const sys = {kind: 'pendulum', id: s.id, ids: [b.id], q: Float64Array.from([th0, vec.dot({x: b.vx, y: b.vy}, tan0) / L, 0]), t: 0, mode: 0, done: null, length: L,
      at(q) { return {x: P.x + L * Math.sin(q[0]), y: P.y - L * Math.cos(q[0])}; },
      parts(q) { const th = q[0], t = {x: Math.cos(th), y: Math.sin(th)}, rr = {x: Math.sin(th), y: -Math.cos(th)}, F = vec.add(vec.mul(G, m), applied(b.id));
        return {t, rr, F, T: m * L * q[1] * q[1] + vec.dot(F, rr)}; },
      prepare() {},
      f(q) { const r = this.parts(q); return Float64Array.from([q[1], vec.dot(r.F, r.t) / (m * L), vec.dot(applied(b.id), vec.mul(r.t, L * q[1]))]); },
      events(q) { const r = this.parts(q), p = this.at(q); return [...(rigid ? [] : [{code: 'slack', id: s.id, g: r.T}]), ...landing(b, p)]; },
      poses(q = this.q) { const p = this.at(q); return new Map([[b.id, {x: p.x, y: p.y, angle: 0}]]); },
      velocities(q = this.q) { return new Map([[b.id, vec.mul({x: Math.cos(q[0]), y: Math.sin(q[0])}, L * q[1])]]); },
      accel(q = this.q) { const r = this.parts(q), at = vec.dot(r.F, r.t) / m; return new Map([[b.id, vec.add(vec.mul(r.t, at), vec.mul(r.rr, -L * q[1] * q[1]))]]); },
      tensions(q = this.q) { const T = this.parts(q).T; return {[s.id]: rigid ? T : Math.max(0, T)}; },
      forceList(q = this.q) { const r = this.parts(q), p = this.at(q), list = [{kind: 'gravity', v: vec.mul(G, m)}];
        if (Math.abs(r.T) > 1e-9 && (rigid || r.T > 0)) list.push({kind: 'tension', v: vec.mul(r.rr, -r.T)});
        const ap = applied(b.id); if (vec.len(ap) > 0) list.push({kind: 'applied', v: ap});
        return new Map([[b.id, list.map(x => ({...x, at: p}))]]); },
      energy(q = this.q) { const p = this.at(q); return {K: 0.5 * m * (L * q[1]) ** 2, Ug: m * g * p.y, Us: 0, heat: 0, work: q[2]}; }
    };
    systems.push(sys);
  }

  /* a body at rest that is not on a floor, an incline or a block, nor on a string, but touches a part the solver does
     not compute (a plank, a curved track, a drawn line or shape) or stands in a liquid, is held there: it stays a
     figure, reported, instead of falling through what it rests on */
  for (const b of bodies) {
    if (owner.has(b.id) || b.on || Math.hypot(b.vx, b.vy) > 1e-9 || springsOf(b.id).length) continue;
    const by = heldBy(scene, b);
    if (by) reject([b.id], 'held_by_figure');
  }

  /* group the remaining bodies joined by springs */
  const rest = bodies.filter(b => !owner.has(b.id)), parent = new Map(rest.map(b => [b.id, b.id]));
  const root = id => { while (parent.get(id) !== id) id = parent.get(id); return id; };
  for (const s of springs) { const [A, B] = springEnds(s); if (isBody(A) && isBody(B) && parent.has(A.id) && parent.has(B.id)) parent.set(root(A.id), root(B.id)); }
  const groups = new Map();
  for (const b of rest) { const r = root(b.id); if (!groups.has(r)) groups.set(r, []); groups.get(r).push(b); }
  /* a spring from one of these to a body that is already in a chain or a pendulum joins two kinds of system */
  for (const [r, list] of [...groups]) if (list.some(b => springsOf(b.id).some(sp => { const o = byId.get(sp.a === b.id ? sp.b : sp.a); return isBody(o) && !parent.has(o.id); }))) {
    groups.delete(r); reject(list.map(b => b.id), 'spring_between_systems');
  }
  for (const list of groups.values()) {
    const onS = list.filter(b => b.on), free = list.filter(b => !b.on);
    if (onS.length && free.length) { reject(list.map(b => b.id), 'spring_surface_and_air'); continue; }
    list.forEach(b => owner.set(b.id, onS.length ? 'surface' : 'free'));
    systems.push(onS.length ? surfaceSystem(onS) : freeSystem(free));
  }

  /* ── bodies resting on surfaces ── */
  function surfaceSystem(list) {
    /* a wheel (k = I / m r² of its kind) on a surface with friction rolls without slipping while the friction that
       needs, k Q / (1 + k), is at most μN: a = Q / (m (1 + k)); otherwise it slides (its spin is not followed) */
    const items = list.map(b => { const fr = surfaceFrame(byId.get(b.on), scene); return {b, id: b.id, m: b.mass, fr, mu: fr.mu, angle: Math.atan2(fr.u.y, fr.u.x), k: b.type === 'wheel' && fr.mu > 0 ? INERTIA[b.kind] ?? 0.5 : 0}; });
    const n = items.length, q = new Float64Array(2 * n + 2);
    items.forEach((it, i) => { q[2 * i] = it.b.at; q[2 * i + 1] = vec.dot({x: it.b.vx, y: it.b.vy}, it.fr.u); });
    const centre = (it, at) => vec.add(vec.add(it.fr.p0, vec.mul(it.fr.u, at)), vec.mul(it.fr.n, bodyHalfHeight(it.b)));
    const posesAt = qq => new Map(items.map((it, i) => { const c = centre(it, qq[2 * i]); return [it.id, {x: c.x, y: c.y, angle: it.b.type === 'block' ? it.angle : 0, at: qq[2 * i]}]; }));
    const modes = new Array(n).fill(0);
    const sys = {kind: 'surface', id: items.map(x => x.id).join('+'), ids: items.map(x => x.id), q, t: 0, modes, done: null,
      eval(qq) {
        const poses = posesAt(qq);
        return items.map((it, i) => {
          let F = vec.add(vec.mul(G, it.m), applied(it.id));
          for (const sp of springsOf(it.id)) F = vec.add(F, springForce(sp, it.id, id => poses.get(id)).F);
          const N = -vec.dot(F, it.fr.n), Q = vec.dot(F, it.fr.u), cap = it.mu * Math.max(0, N), v = qq[2 * i + 1];
          let f, a;
          if (it.k > 0 && Math.abs(it.k * Q / (1 + it.k)) <= cap + 1e-12) return {F, N, Q, f: -it.k * Q / (1 + it.k), a: Q / (it.m * (1 + it.k)), pose: poses.get(it.id), rolling: true};
          if (modes[i] === 0 && Math.abs(v) <= EPS_V) { f = -Math.max(-cap, Math.min(cap, Q)); a = 0; }
          else { f = -(modes[i] || sgn(v)) * cap; a = (Q + f) / it.m; }
          return {F, N, Q, f, a, pose: poses.get(it.id)};
        });
      },
      prepare() {
        items.forEach((it, i) => { const v = this.q[2 * i + 1]; if (Math.abs(v) > EPS_V) modes[i] = sgn(v); else modes[i] = 0; });
        const r = this.eval(this.q);
        items.forEach((it, i) => { if (modes[i] === 0) { const cap = it.mu * Math.max(0, r[i].N); modes[i] = Math.abs(r[i].Q) <= cap + 1e-12 ? 0 : sgn(r[i].Q); } });
      },
      f(qq) {
        const r = this.eval(qq), out = new Float64Array(qq.length);
        items.forEach((it, i) => { const v = qq[2 * i + 1]; out[2 * i] = v; out[2 * i + 1] = r[i].rolling ? r[i].a : modes[i] === 0 && Math.abs(v) <= EPS_V ? 0 : r[i].a;
          out[2 * n] += r[i].rolling ? 0 : -r[i].f * v * (modes[i] === 0 ? 0 : 1); out[2 * n + 1] += vec.dot(applied(it.id), vec.mul(it.fr.u, v)); });
        return out;
      },
      events(qq) {
        const r = this.eval(qq), out = [];
        items.forEach((it, i) => { const at = qq[2 * i], hw = bodyHalfWidth(it.b);
          out.push({code: 'end_of_surface', id: it.id, g: at - hw}, {code: 'end_of_surface', id: it.id, g: it.fr.length - at - hw}, {code: 'lift_off', id: it.id, g: r[i].N});
          if (it.mu > 0 && modes[i] !== 0 && !r[i].rolling) out.push({code: 'stick', i, g: modes[i] * qq[2 * i + 1], stop: false});
          for (let j = i + 1; j < n; j++) if (items[j].b.on === it.b.on) out.push({code: 'touched', id: it.id, g: Math.abs(qq[2 * j] - at) - hw - bodyHalfWidth(items[j].b)});
        });
        return out;
      },
      onStick(ev) { this.q[2 * ev.i + 1] = 0; modes[ev.i] = 0; },
      poses(qq = this.q) { return posesAt(qq); },
      velocities(qq = this.q) { return new Map(items.map((it, i) => [it.id, vec.mul(it.fr.u, qq[2 * i + 1])])); },
      accel(qq = this.q) { const r = this.eval(qq); return new Map(items.map((it, i) => [it.id, vec.mul(it.fr.u, r[i].a)])); },
      tensions() { return {}; },
      forceList(qq = this.q) {
        const r = this.eval(qq), poses = posesAt(qq);
        return new Map(items.map((it, i) => {
          const list = [{kind: 'gravity', v: vec.mul(G, it.m)}, {kind: 'normal', v: vec.mul(it.fr.n, Math.max(0, r[i].N))}];
          if (Math.abs(r[i].f) > 1e-9) list.push({kind: 'friction', v: vec.mul(it.fr.u, r[i].f)});
          const ap = applied(it.id); if (vec.len(ap) > 0) list.push({kind: 'applied', v: ap});
          for (const sp of springsOf(it.id)) list.push({kind: 'spring', v: springForce(sp, it.id, id => poses.get(id)).F});
          return [it.id, list.map(x => ({...x, at: r[i].pose}))];
        }));
      },
      energy(qq = this.q) { const p = posesAt(qq), r = this.eval(qq);
        return {K: items.reduce((k, it, i) => k + 0.5 * it.m * qq[2 * i + 1] ** 2 * (r[i].rolling ? 1 + it.k : 1), 0), Ug: items.reduce((u, it) => u + it.m * g * p.get(it.id).y, 0), Us: springEnergy(id => p.get(id)), heat: qq[2 * n], work: qq[2 * n + 1]}; }
    };
    return sys;
  }

  /* ── bodies in the air ── */
  function freeSystem(list) {
    const n = list.length, q = new Float64Array(4 * n + 1);
    list.forEach((b, i) => { q[4 * i] = b.x; q[4 * i + 1] = b.y; q[4 * i + 2] = b.vx; q[4 * i + 3] = b.vy; });
    const posesAt = qq => new Map(list.map((b, i) => [b.id, {x: qq[4 * i], y: qq[4 * i + 1], angle: 0}]));
    const forceOn = (b, poses) => { let F = vec.add(vec.mul(G, b.mass), applied(b.id)); for (const sp of springsOf(b.id)) F = vec.add(F, springForce(sp, b.id, id => poses.get(id)).F); return F; };
    return {kind: 'free', id: list.map(b => b.id).join('+'), ids: list.map(b => b.id), q, t: 0, done: null,
      prepare() {},
      f(qq) {
        const poses = posesAt(qq), out = new Float64Array(qq.length);
        list.forEach((b, i) => { const F = forceOn(b, poses); out[4 * i] = qq[4 * i + 2]; out[4 * i + 1] = qq[4 * i + 3]; out[4 * i + 2] = F.x / b.mass; out[4 * i + 3] = F.y / b.mass;
          out[4 * n] += vec.dot(applied(b.id), {x: qq[4 * i + 2], y: qq[4 * i + 3]}); });
        return out;
      },
      events(qq) { const poses = posesAt(qq); return list.flatMap(b => landing(b, poses.get(b.id))); },
      poses(qq = this.q) { return posesAt(qq); },
      velocities(qq = this.q) { return new Map(list.map((b, i) => [b.id, {x: qq[4 * i + 2], y: qq[4 * i + 3]}])); },
      accel(qq = this.q) { const p = posesAt(qq); return new Map(list.map(b => [b.id, vec.mul(forceOn(b, p), 1 / b.mass)])); },
      tensions() { return {}; },
      forceList(qq = this.q) { const p = posesAt(qq);
        return new Map(list.map(b => { const l = [{kind: 'gravity', v: vec.mul(G, b.mass)}], ap = applied(b.id);
          if (vec.len(ap) > 0) l.push({kind: 'applied', v: ap});
          for (const sp of springsOf(b.id)) l.push({kind: 'spring', v: springForce(sp, b.id, id => p.get(id)).F});
          return [b.id, l.map(x => ({...x, at: p.get(b.id)}))]; })); },
      energy(qq = this.q) { const p = posesAt(qq);
        return {K: list.reduce((k, b, i) => k + 0.5 * b.mass * (qq[4 * i + 2] ** 2 + qq[4 * i + 3] ** 2), 0), Ug: list.reduce((u, b) => u + b.mass * g * p.get(b.id).y, 0), Us: springEnergy(id => p.get(id)), heat: 0, work: qq[4 * n]}; }
    };
  }

  /* every system's event values at its start: an event fires when its value goes from above zero to zero or below */
  for (const s of systems) s.prepare();

  /* one step of one system, cut at the first event inside it */
  function stepSystem(s, h) {
    /* a body that starts touching a surface (value 0) lands at once when it moves into it */
    s.prepare();
    const f = q => s.f(q), q0 = s.q, q1 = rk4(f, q0, h);
    const before = s.events(q0), after = s.events(q1);
    let first = null, tau = 1;
    after.forEach((e, i) => {
      const g0 = before[i] ? before[i].g : NaN;
      if (!((g0 > 0 && e.g <= 0) || (e.code === 'landed' && g0 >= -1e-9 && g0 <= 0 && e.g < g0 - 1e-12))) return;
      let lo = 0, hi = 1;
      for (let k = 0; k < 40; k++) { const mid = (lo + hi) / 2, gm = s.events(rk4(f, q0, h * mid))[i]?.g; if (gm > 0) lo = mid; else hi = mid; }
      if (!first || hi < tau) { tau = hi; first = e; }
    });
    if (first) {
      s.q = rk4(f, q0, h * tau); s.t += h * tau;
      if (first.stop === false) s.onStick?.(first);
      else s.done = {code: first.code, id: first.id, t: s.t};
    } else { s.q = q1; s.t += h; }
  }

  /* the drawn shapes given physics: their own rigid-body world (rigidWorld below) */
  const rw = rigidWorld(scene);
  if (rw) systems.push(rw);

  const sim = {
    scene, systems, unsupported, dt, t: 0,
    get done() { return systems.length > 0 && systems.every(s => s.done); },
    get events() { return systems.filter(s => s.done).map(s => s.done); },
    /* move every system on to time T */
    advanceTo(T) {
      for (const s of systems) {
        if (s.advance) { s.advance(T); continue; }
        let guard = 0;
        while (!s.done && s.t < T - 1e-12 && guard++ < 2e6) stepSystem(s, Math.min(dt, T - s.t));
      }
      this.t = T;
      return this;
    },
    run(seconds) { return this.advanceTo(this.t + seconds); },
    poses() { const m = new Map(); for (const s of systems) for (const [k, v] of s.poses()) m.set(k, v); return m; },
    velocities() { const m = new Map(); for (const s of systems) for (const [k, v] of s.velocities()) m.set(k, v); return m; },
    accelerations() { const m = new Map(); for (const s of systems) for (const [k, v] of s.accel()) m.set(k, v); return m; },
    tensions() { return Object.assign({}, ...systems.map(s => s.tensions())); },
    forces() { const m = new Map(); for (const s of systems) for (const [k, v] of s.forceList()) m.set(k, v); return m; },
    energy() {
      const e = {K: 0, Ug: 0, Us: 0, heat: 0, work: 0};
      for (const s of systems) { const x = s.energy(); for (const k in e) e[k] += x[k]; }
      e.E = e.K + e.Ug + e.Us;
      return e;
    },
    anchors,
    /** the scene with every body where the simulation has it now */
    applyTo(base = scene) {
      const poses = this.poses(), out = {...base, objects: base.objects.map(o => {
        const p = poses.get(o.id);
        if (!p) return o;
        if (p.rigid) return rw ? rw.place(o) : o;
        return p.at !== undefined ? {...o, at: p.at, x: p.x, y: p.y} : {...o, x: p.x, y: p.y, on: ''};
      })};
      return out;
    }
  };
  return sim;
}

/* ════════════════════════════════════════════════════════════════════════════════════════════════════════════════
   Drawn shapes given physics ("물리 적용": a rect, an ellipse, a polygon or a line with phys 'dynamic' or 'static',
   joints between them): a small 2D rigid-body engine of its own, deterministic (a fixed step, a fixed order, no
   randomness), so the same figure plays the same way everywhere.
     bodies     a circle (an ellipse as wide as high) or a convex polygon (a rect; an ellipse as 24 sides; a polygon or a
                pen stroke as its convex hull; a line as a two-sided segment). Mass from pmass, the moment of inertia
                from the shape (uniform density). Static: infinite mass (a drawn floor, wall or ramp); a static open
                polyline is a chain of segments.
     step       semi-implicit (symplectic) Euler at RIGID_DT: v += (g + F/m − drag v) h, then the constraints on the
                velocities, then x += v h, θ += ω h, then the positions corrected (penetration and rod lengths).
     contacts   SAT for convex polygons (reference face and clipped incident face, up to two points), circle–polygon
                and circle–circle; a small margin makes resting contacts speculative (no jitter).
     impulses   sequential impulses with accumulated, clamped normal and friction impulses, warm-started from the step
                before (matched by the contact's features). Coulomb friction μ = √(μa μb) for sticking and sliding;
                restitution e = max(ea, eb) above a small closing speed (resting contacts do not bounce).
     joints     spring (a force k (ℓ − L0) along it, with damping), rod (ℓ = L0 both ways), string (ℓ ≤ L0, pulls only),
                solved with the contacts in the same iterations; L0 = 0 takes the length at the start.
     sleeping   a body slower than 3 cm/s and 0.05 rad/s for 0.6 s sleeps (stays put, acts as fixed) until a moving body
                touches it or pulls on it.
   Bodies of the analytic solver above (block, ball, wheel) are not part of this world. */
export const RIGID_DT = 1 / 480;
const R_ITER = 12, R_POS = 3, R_SLOP = 0.002, R_MARGIN = 0.004, R_BAUM = 0.6, R_MAXCORR = 0.04, R_BOUNCE = 0.4;
const rot = (a, v) => { const c = Math.cos(a), s = Math.sin(a); return {x: c * v.x - s * v.y, y: s * v.x + c * v.y}; };
const crs = (a, b) => a.x * b.y - a.y * b.x;
/* the convex hull of points (monotone chain), anticlockwise */
export function convexHull(pts) {
  const p = [...pts].sort((a, b) => a.x - b.x || a.y - b.y), out = [];
  if (p.length < 3) return p;
  const lo = [], hi = [];
  for (const q of p) { while (lo.length > 1 && crs(vec.sub(lo[lo.length - 1], lo[lo.length - 2]), vec.sub(q, lo[lo.length - 2])) <= 1e-12) lo.pop(); lo.push(q); }
  for (const q of p.slice().reverse()) { while (hi.length > 1 && crs(vec.sub(hi[hi.length - 1], hi[hi.length - 2]), vec.sub(q, hi[hi.length - 2])) <= 1e-12) hi.pop(); hi.push(q); }
  out.push(...lo.slice(0, -1), ...hi.slice(0, -1));
  return out;
}
/* area, centroid and the second moment (about the centroid, per unit density) of a polygon */
function polyMass(v) {
  let A = 0, cx = 0, cy = 0;
  for (let i = 0; i < v.length; i++) { const a = v[i], b = v[(i + 1) % v.length], c = crs(a, b); A += c / 2; cx += (a.x + b.x) * c / 6; cy += (a.y + b.y) * c / 6; }
  if (Math.abs(A) < 1e-14) return null;
  const c = {x: cx / A, y: cy / A}; let J = 0;
  for (let i = 0; i < v.length; i++) { const a = vec.sub(v[i], c), b = vec.sub(v[(i + 1) % v.length], c), k = crs(a, b); J += k * (vec.dot(a, a) + vec.dot(a, b) + vec.dot(b, b)) / 12; }
  return {A: Math.abs(A), c, J: Math.abs(J)};
}
/* a shape's outline in the world (unturned for rect and ellipse, whose rot is the start angle) */
function shapeBodies(o) {
  const out = [], deg = Math.PI / 180;
  if (o.type === 'rect') { const c = {x: o.x + o.w / 2, y: o.y + o.h / 2}, hw = o.w / 2, hh = o.h / 2; out.push({c, a: (o.rot || 0) * deg, verts: [{x: -hw, y: -hh}, {x: hw, y: -hh}, {x: hw, y: hh}, {x: -hw, y: hh}], I1: (o.w * o.w + o.h * o.h) / 12}); }
  else if (o.type === 'ellipse') {
    const c = {x: o.x + o.w / 2, y: o.y + o.h / 2};
    if (Math.abs(o.w - o.h) <= 1e-6 * Math.max(o.w, o.h)) out.push({c, a: (o.rot || 0) * deg, r: o.w / 2, I1: o.w * o.w / 8});
    else { const verts = []; for (let i = 0; i < 24; i++) { const t = 2 * Math.PI * i / 24; verts.push({x: o.w / 2 * Math.cos(t), y: o.h / 2 * Math.sin(t)}); } const pm = polyMass(verts); out.push({c, a: (o.rot || 0) * deg, verts, I1: pm.J / pm.A}); }
  } else if (o.type === 'line') { const a = {x: o.x1, y: o.y1}, b = {x: o.x2, y: o.y2}, c = vec.mul(vec.add(a, b), 0.5), L = vec.len(vec.sub(b, a)); if (L > 1e-9) out.push({c, a: 0, verts: [vec.sub(a, c), vec.sub(b, c)], I1: L * L / 12}); }
  else if (o.type === 'poly') {
    const pts = o.pts.map(q => ({x: q[0], y: q[1]}));
    if (o.phys === 'static' && !o.closed) { for (let i = 1; i < pts.length; i++) { const a = pts[i - 1], b = pts[i], c = vec.mul(vec.add(a, b), 0.5); if (vec.len(vec.sub(b, a)) > 1e-9) out.push({c, a: 0, verts: [vec.sub(a, c), vec.sub(b, c)], I1: 0, part: i}); } }
    else { const h = convexHull(pts), pm = h.length >= 3 ? polyMass(h) : null;
      if (pm) out.push({c: pm.c, a: 0, verts: h.map(q => vec.sub(q, pm.c)), I1: pm.J / pm.A});
      else if (h.length === 2) { const c = vec.mul(vec.add(h[0], h[1]), 0.5), L = vec.len(vec.sub(h[1], h[0])); out.push({c, a: 0, verts: [vec.sub(h[0], c), vec.sub(h[1], c)], I1: L * L / 12}); } }
  }
  return out;
}
/** the centre and the start angle a drawn shape has in the rigid world (where a joint's ax, ay are measured from) */
export function rigidFrame(o) { const b = shapeBodies({...o, phys: o.phys === 'static' && o.type === 'poly' && !o.closed ? 'dynamic' : o.phys})[0]; return b ? {c: b.c, a: b.a} : null; }
/** a joint's two ends in the world, the shapes as they are in the scene given (an end on no shape: the fixed point) */
export function jointEnds(scene, j) {
  const byId = new Map(scene.objects.map(o => [o.id, o])), A = byId.get(j.a), B = j.b ? byId.get(j.b) : null;
  const end = (o, x, y) => { const fr = o && rigidFrame(o); if (!fr) return null; const c = Math.cos(fr.a), s = Math.sin(fr.a); return {x: fr.c.x + c * x - s * y, y: fr.c.y + s * x + c * y}; };
  const a = end(A, j.ax, j.ay), b = j.b ? end(B, j.bx, j.by) : {x: j.bx, y: j.by};
  return a && b ? {a, b, fixed: !j.b} : null;
}
/* the outward normals of a polygon's edges (a two-point segment has two, opposite) */
function normalsOf(v) { return v.map((a, i) => { const b = v[(i + 1) % v.length], d = vec.sub(b, a), l = vec.len(d) || 1; return {x: d.y / l, y: -d.x / l}; }); }

/* collision: [{n (unit, from a to b), pts: [{p, sep, id}]}] or null */
function worldVerts(B) { if (B._wv && B._wt === B.stamp) return B._wv; const c = Math.cos(B.a), s = Math.sin(B.a); B._wv = B.verts.map(v => ({x: B.x + c * v.x - s * v.y, y: B.y + s * v.x + c * v.y})); B._wn = B.norms.map(n => ({x: c * n.x - s * n.y, y: s * n.x + c * n.y})); B._wt = B.stamp; return B._wv; }
function maxSep(A, B) { const va = worldVerts(A), na = A._wn, vb = worldVerts(B); let best = -Infinity, edge = 0; for (let i = 0; i < va.length; i++) { let m = Infinity; for (const q of vb) m = Math.min(m, na[i].x * (q.x - va[i].x) + na[i].y * (q.y - va[i].y)); if (m > best) { best = m; edge = i; } } return {sep: best, edge}; }
function collidePolys(A, B) {
  const sa = maxSep(A, B); if (sa.sep > R_MARGIN) return null;
  const sb = maxSep(B, A); if (sb.sep > R_MARGIN) return null;
  let ref = A, inc = B, e = sa.edge, flip = false;
  if (sb.sep > sa.sep + 1e-4) { ref = B; inc = A; e = sb.edge; flip = true; }
  const rv = worldVerts(ref), rn = ref._wn[e], v1 = rv[e], v2 = rv[(e + 1) % rv.length], iv = worldVerts(inc), inn = inc._wn;
  /* the incident edge: the one facing the reference face most */
  let ie = 0, md = Infinity; for (let i = 0; i < iv.length; i++) { const d = vec.dot(inn[i], rn); if (d < md) { md = d; ie = i; } }
  let cp = [{p: iv[ie], id: ie}, {p: iv[(ie + 1) % iv.length], id: (ie + 1) % iv.length}];
  const t = vec.unit(vec.sub(v2, v1));
  const clip = (pts, nrm, off, cid) => { const out = [], d0 = vec.dot(nrm, pts[0].p) - off, d1 = vec.dot(nrm, pts[1].p) - off; if (d0 <= 0) out.push(pts[0]); if (d1 <= 0) out.push(pts[1]); if (d0 * d1 < 0) { const k = d0 / (d0 - d1); out.push({p: vec.add(pts[0].p, vec.mul(vec.sub(pts[1].p, pts[0].p), k)), id: cid}); } return out; };
  cp = clip(cp, vec.mul(t, -1), -vec.dot(t, v1), 100 + e); if (cp.length < 2) { if (!cp.length) return null; }
  if (cp.length === 2) cp = clip(cp, t, vec.dot(t, v2), 200 + e);
  const pts = [];
  for (const q of cp) { const sep = vec.dot(rn, q.p) - vec.dot(rn, v1); if (sep <= R_MARGIN) pts.push({p: vec.sub(q.p, vec.mul(rn, sep / 2)), sep, id: (flip ? 1000 : 0) + e * 31 + q.id}); }
  if (!pts.length) return null;
  return {n: flip ? vec.mul(rn, -1) : rn, pts};
}
function collideCirclePoly(C, Pb, flip) {
  const v = worldVerts(Pb), n = Pb._wn, c = {x: C.x, y: C.y};
  let sep = -Infinity, e = 0;
  for (let i = 0; i < v.length; i++) { const s = vec.dot(n[i], vec.sub(c, v[i])); if (s > sep) { sep = s; e = i; } }
  if (sep > C.r + R_MARGIN) return null;
  const v1 = v[e], v2 = v[(e + 1) % v.length];
  let nrm, p, s;
  const u1 = vec.dot(vec.sub(c, v1), vec.sub(v2, v1)), u2 = vec.dot(vec.sub(c, v2), vec.sub(v1, v2));
  if (sep < 1e-9) { nrm = n[e]; s = sep - C.r; p = vec.sub(c, vec.mul(nrm, C.r + s / 2)); }
  else if (u1 <= 0 || u2 <= 0) { const q = u1 <= 0 ? v1 : v2, d = vec.sub(c, q), l = vec.len(d); if (l > C.r + R_MARGIN) return null; nrm = l > 1e-12 ? vec.mul(d, 1 / l) : n[e]; s = l - C.r; p = q; }
  else { nrm = n[e]; s = sep - C.r; p = vec.sub(c, vec.mul(nrm, C.r + s / 2)); }
  /* nrm points from the polygon to the circle */
  return {n: flip ? nrm : vec.mul(nrm, -1), pts: [{p, sep: s, id: e}]};
}
function collide(A, B) {
  if (A.r && B.r) { const d = {x: B.x - A.x, y: B.y - A.y}, l = vec.len(d), s = l - A.r - B.r; if (s > R_MARGIN) return null; const n = l > 1e-12 ? vec.mul(d, 1 / l) : {x: 0, y: 1}; return {n, pts: [{p: vec.add(A, vec.mul(n, A.r + s / 2)), sep: s, id: 0}]}; }
  if (A.r) return collideCirclePoly(A, B, false);
  if (B.r) return collideCirclePoly(B, A, true);
  return collidePolys(A, B);
}

/** the rigid-body world of a scene's drawn shapes given physics, as a system of buildSim (null if there is none) */
export function rigidWorld(scene, {dt = RIGID_DT} = {}) {
  const shapes = scene.objects.filter(isPhysShape);
  if (!shapes.some(o => o.phys === 'dynamic')) return null;
  const g = scene.gravityOn === false ? 0 : scene.g, drag = scene.drag || 0;
  const bodies = [], byObj = new Map();
  for (const o of shapes) for (const sb of shapeBodies(o)) {
    const dyn = o.phys === 'dynamic', m = dyn ? o.pmass : 0, I = dyn ? Math.max(1e-12, m * sb.I1) : 0;
    const B = {id: o.id, o, part: sb.part || 0, x: sb.c.x, y: sb.c.y, a: sb.a, c0: {...sb.c}, a0: sb.a, r: sb.r || 0, verts: sb.verts || null, norms: sb.verts ? normalsOf(sb.verts) : null,
      m, invM: dyn ? 1 / m : 0, I, invI: dyn ? 1 / I : 0, vx: dyn ? o.pvx : 0, vy: dyn ? o.pvy : 0, w: dyn ? o.pw : 0, mu: o.pmu, e: o.pe, fx: dyn ? o.pfx : 0, fy: dyn ? o.pfy : 0,
      dyn, asleep: false, sleepT: 0, stamp: 0, touch: new Map()};
    B.bound = B.r || Math.max(...B.verts.map(v => Math.hypot(v.x, v.y)));
    bodies.push(B); if (!byObj.has(o.id)) byObj.set(o.id, B);
  }
  /* joints: each end a body (by its shape) and a point on it in its own frame, or a fixed point */
  const joints = [];
  for (const j of scene.objects.filter(o => o.type === 'joint')) {
    const A = byObj.get(j.a), Bb = j.b ? byObj.get(j.b) : null; if (!A || (j.b && !Bb)) continue;
    const la = {x: j.ax, y: j.ay}, lb = Bb ? {x: j.bx, y: j.by} : null;
    const wa = vec.add(A, rot(A.a, la)), wb = Bb ? vec.add(Bb, rot(Bb.a, lb)) : {x: j.bx, y: j.by};
    joints.push({j, A, B: Bb, la, lb, fixed: Bb ? null : {x: j.bx, y: j.by}, L: j.L0 > 0 ? j.L0 : vec.len(vec.sub(wb, wa)), acc: 0, T: 0});
  }
  const anchor = (B, l) => { const r = rot(B.a, l); return {r, p: {x: B.x + r.x, y: B.y + r.y}}; };
  const jEnds = J => { const a = anchor(J.A, J.la), b = J.B ? anchor(J.B, J.lb) : {r: {x: 0, y: 0}, p: J.fixed}; return {a, b}; };
  const awake = B => B.dyn && !B.asleep;
  const iM = B => awake(B) ? B.invM : 0, iI = B => awake(B) ? B.invI : 0;
  const velAt = (B, r) => ({x: B.vx - B.w * r.y, y: B.vy + B.w * r.x});
  const impulse = (B, P, r) => { if (!awake(B)) return; B.vx += P.x * B.invM; B.vy += P.y * B.invM; B.w += crs(r, P) * B.invI; };
  const wake = B => { if (B.dyn && B.asleep) { B.asleep = false; B.sleepT = 0; } };
  let cache = new Map(), work = 0, E0 = null, lastContacts = [];
  const bump = () => { for (const B of bodies) B.stamp++; };
  const findContacts = () => {
    const out = [];
    for (let i = 0; i < bodies.length; i++) for (let k = i + 1; k < bodies.length; k++) {
      const A = bodies[i], B = bodies[k];
      if (!A.dyn && !B.dyn) continue; if (A.id === B.id) continue;
      if (!awake(A) && !awake(B)) continue;
      if (Math.abs(A.x - B.x) > A.bound + B.bound + R_MARGIN || Math.abs(A.y - B.y) > A.bound + B.bound + R_MARGIN) continue;
      const m = collide(A, B); if (m) out.push({A, B, ...m});
    }
    return out;
  };
  function step(h) {
    /* forces: gravity, the applied force, drag, springs */
    for (const B of bodies) if (awake(B)) {
      B.vx += h * (B.fx / B.m - drag * B.vx); B.vy += h * (-g + B.fy / B.m - drag * B.vy); B.w -= h * drag * B.w;
      work += h * (B.fx * B.vx + B.fy * B.vy);
    }
    for (const J of joints) if (J.j.kind === 'spring') {
      const {a, b} = jEnds(J), d = vec.sub(b.p, a.p), l = vec.len(d); if (l < 1e-12) continue;
      const u = vec.mul(d, 1 / l), vr = vec.sub(J.B ? velAt(J.B, b.r) : {x: 0, y: 0}, velAt(J.A, a.r)), F = J.j.k * (l - J.L) + J.j.damp * vec.dot(vr, u);
      J.T = F; if (Math.abs(F) > 1e-12) { wake(J.A); if (J.B) wake(J.B); }
      impulse(J.A, vec.mul(u, F * h), a.r); if (J.B) impulse(J.B, vec.mul(u, -F * h), b.r);
    }
    /* contacts: prepared once, then the iterations */
    bump();
    const contacts = findContacts(), next = new Map();
    for (const C of contacts) {
      const {A, B} = C, t = {x: -C.n.y, y: C.n.x}; C.mu = Math.sqrt(A.mu * B.mu); C.e = Math.max(A.e, B.e);
      /* a moving body wakes a sleeping one it touches */
      if (awake(A) !== awake(B)) { const M = awake(A) ? A : B; if (Math.hypot(M.vx, M.vy) > 0.05 || Math.abs(M.w) > 0.1) wake(awake(A) ? B : A); }
      for (const q of C.pts) {
        q.rA = vec.sub(q.p, A); q.rB = vec.sub(q.p, B);
        const rnA = crs(q.rA, C.n), rnB = crs(q.rB, C.n), rtA = crs(q.rA, t), rtB = crs(q.rB, t);
        q.mN = 1 / Math.max(1e-12, iM(A) + iM(B) + iI(A) * rnA * rnA + iI(B) * rnB * rnB);
        q.mT = 1 / Math.max(1e-12, iM(A) + iM(B) + iI(A) * rtA * rtA + iI(B) * rtB * rtB);
        const vn = vec.dot(vec.sub(velAt(B, q.rB), velAt(A, q.rA)), C.n);
        q.bias = vn < -R_BOUNCE ? -C.e * vn : 0;
        /* a contact not yet touching lets the bodies close the gap within the step (speculative) */
        q.spec = q.sep > 0 ? q.sep / h : 0;
        const key = A.id + '|' + A.part + '|' + B.id + '|' + B.part + '|' + q.id, old = cache.get(key);
        q.key = key; q.Pn = old ? old.Pn : 0; q.Pt = old ? old.Pt : 0;
        const P = vec.add(vec.mul(C.n, q.Pn), vec.mul(t, q.Pt)); impulse(A, vec.mul(P, -1), q.rA); impulse(B, P, q.rB);
      }
      C.t = t;
    }
    for (const J of joints) { J.acc = 0; if (J.j.kind !== 'spring' && (awake(J.A) || (J.B && awake(J.B)))) { wake(J.A); if (J.B) wake(J.B); } }
    for (let it = 0; it < R_ITER; it++) {
      for (const J of joints) {
        if (J.j.kind === 'spring') continue;
        const {a, b} = jEnds(J), d = vec.sub(b.p, a.p), l = vec.len(d); if (l < 1e-12) continue;
        if (J.j.kind === 'string' && l < J.L - R_SLOP) continue;
        const u = vec.mul(d, 1 / l), Bj = J.B, ra = crs(a.r, u), rb = Bj ? crs(b.r, u) : 0;
        const K = iM(J.A) + iI(J.A) * ra * ra + (Bj ? iM(Bj) + iI(Bj) * rb * rb : 0); if (K < 1e-12) continue;
        const cd = vec.dot(vec.sub(Bj ? velAt(Bj, b.r) : {x: 0, y: 0}, velAt(J.A, a.r)), u);
        let lam = -cd / K;
        if (J.j.kind === 'string') { const old = J.acc; J.acc = Math.min(0, old + lam); lam = J.acc - old; } else J.acc += lam;
        impulse(J.A, vec.mul(u, -lam), a.r); if (Bj) impulse(Bj, vec.mul(u, lam), b.r);
      }
      for (const C of contacts) {
        const {A, B, n, t} = C;
        for (const q of C.pts) {
          const dv = vec.sub(velAt(B, q.rB), velAt(A, q.rA));
          /* friction, within the cone of the normal impulse */
          const vt = vec.dot(dv, t), maxF = C.mu * q.Pn, oldT = q.Pt; q.Pt = Math.max(-maxF, Math.min(maxF, oldT - vt * q.mT));
          const dPt = q.Pt - oldT; impulse(A, vec.mul(t, -dPt), q.rA); impulse(B, vec.mul(t, dPt), q.rB);
          const dv2 = vec.sub(velAt(B, q.rB), velAt(A, q.rA)), vn = vec.dot(dv2, n);
          const oldN = q.Pn; q.Pn = Math.max(0, oldN - (vn - q.bias + q.spec) * q.mN);
          const dPn = q.Pn - oldN; impulse(A, vec.mul(n, -dPn), q.rA); impulse(B, vec.mul(n, dPn), q.rB);
        }
      }
    }
    /* the contact forces on each body, one normal force and one friction force for each body it touches */
    for (const B of bodies) B.touch = new Map();
    const addF = (B, other, N, F) => { const k = other.id, t = B.touch.get(k) || {N: {x: 0, y: 0}, F: {x: 0, y: 0}}; t.N = vec.add(t.N, N); t.F = vec.add(t.F, F); B.touch.set(k, t); };
    for (const C of contacts) for (const q of C.pts) {
      next.set(q.key, {Pn: q.Pn, Pt: q.Pt});
      const N = vec.mul(C.n, q.Pn / h), F = vec.mul(C.t, q.Pt / h);
      addF(C.B, C.A, N, F); addF(C.A, C.B, vec.mul(N, -1), vec.mul(F, -1));
    }
    for (const J of joints) if (J.j.kind !== 'spring') J.T = -J.acc / h;
    cache = next; lastContacts = contacts;
    /* positions */
    for (const B of bodies) if (awake(B)) { B.x += h * B.vx; B.y += h * B.vy; B.a += h * B.w; }
    /* position correction: what still overlaps is pushed apart, a rod or a taut string is brought to its length */
    for (let it = 0; it < R_POS; it++) {
      bump();
      for (const C of findContacts()) {
        const {A, B, n} = C;
        for (const q of C.pts) {
          const corr = Math.max(-R_MAXCORR, Math.min(0, R_BAUM * (q.sep + R_SLOP))); if (corr >= 0) continue;
          const rA = vec.sub(q.p, A), rB = vec.sub(q.p, B), rnA = crs(rA, n), rnB = crs(rB, n);
          const K = iM(A) + iM(B) + iI(A) * rnA * rnA + iI(B) * rnB * rnB; if (K < 1e-12) continue;
          const P = -corr / K / C.pts.length;
          if (awake(A)) { A.x -= n.x * P * A.invM; A.y -= n.y * P * A.invM; A.a -= crs(rA, n) * P * A.invI; }
          if (awake(B)) { B.x += n.x * P * B.invM; B.y += n.y * P * B.invM; B.a += crs(rB, n) * P * B.invI; }
          bump();
        }
      }
      for (const J of joints) {
        if (J.j.kind === 'spring') continue;
        const {a, b} = jEnds(J), d = vec.sub(b.p, a.p), l = vec.len(d); if (l < 1e-12) continue;
        const Cc = l - J.L; if (J.j.kind === 'string' && Cc < 0) continue;
        const u = vec.mul(d, 1 / l), Bj = J.B, ra = crs(a.r, u), rb = Bj ? crs(b.r, u) : 0;
        const K = iM(J.A) + iI(J.A) * ra * ra + (Bj ? iM(Bj) + iI(Bj) * rb * rb : 0); if (K < 1e-12) continue;
        const P = Cc / K;
        if (awake(J.A)) { J.A.x += u.x * P * J.A.invM; J.A.y += u.y * P * J.A.invM; J.A.a += ra * P * J.A.invI; }
        if (Bj && awake(Bj)) { Bj.x -= u.x * P * Bj.invM; Bj.y -= u.y * P * Bj.invM; Bj.a -= rb * P * Bj.invI; }
        bump();
      }
    }
    /* sleeping */
    const touched = new Set(); for (const C of contacts) { touched.add(C.A); touched.add(C.B); }
    for (const B of bodies) if (awake(B)) {
      if (Math.hypot(B.vx, B.vy) < 0.03 && Math.abs(B.w) < 0.05 && (touched.has(B) || g === 0)) B.sleepT += h; else B.sleepT = 0;
      if (B.sleepT > 0.6) { B.asleep = true; B.vx = B.vy = B.w = 0; }
    }
  }
  const energyNow = () => {
    let K = 0, Ug = 0, Us = 0;
    for (const B of bodies) if (B.dyn && !B.part) { K += 0.5 * B.m * (B.vx * B.vx + B.vy * B.vy) + 0.5 * B.I * B.w * B.w; Ug += B.m * g * B.y; }
    for (const J of joints) if (J.j.kind === 'spring') { const {a, b} = jEnds(J); Us += 0.5 * J.j.k * (vec.len(vec.sub(b.p, a.p)) - J.L) ** 2; }
    return {K, Ug, Us};
  };
  const dynBodies = bodies.filter(B => B.dyn);
  const sys = {kind: 'rigid', id: 'rigid', ids: dynBodies.map(B => B.id), t: 0, done: null, dt, bodies, joints,
    prepare() {},
    advance(T) { if (E0 === null) { const e = energyNow(); E0 = e.K + e.Ug + e.Us; } let guard = 0; while (this.t < T - 1e-12 && guard++ < 2e6) { step(dt); this.t += dt; } },
    poses() { return new Map(dynBodies.map(B => [B.id, {x: B.x, y: B.y, angle: B.a, rigid: true}])); },
    velocities() { return new Map(dynBodies.map(B => [B.id, {x: B.vx, y: B.vy, w: B.w}])); },
    accel() { return new Map(dynBodies.map(B => [B.id, {x: 0, y: 0}])); },
    tensions() { return Object.fromEntries(joints.map(J => [J.j.id, J.T])); },
    jointWorld() { return new Map(joints.map(J => { const {a, b} = jEnds(J); return [J.j.id, {a: a.p, b: b.p, fixed: !J.B}]; })); },
    contacts() { return lastContacts.flatMap(C => C.pts.map(q => ({a: C.A.id, b: C.B.id, p: q.p, n: C.n, sep: q.sep}))); },
    forceList() {
      return new Map(dynBodies.map(B => { const at = {x: B.x, y: B.y}, list = [];
        if (g) list.push({kind: 'gravity', v: {x: 0, y: -B.m * g}, at});
        if (B.fx || B.fy) list.push({kind: 'applied', v: {x: B.fx, y: B.fy}, at});
        for (const [, t] of B.touch || []) { if (vec.len(t.N) > 1e-9) list.push({kind: 'normal', v: t.N, at}); if (vec.len(t.F) > 1e-6) list.push({kind: 'friction', v: t.F, at}); }
        for (const J of joints) if ((J.A === B || J.B === B) && Math.abs(J.T) > 1e-9) { const {a, b} = jEnds(J), u = vec.unit(vec.sub(b.p, a.p)), s = J.A === B ? 1 : -1; list.push({kind: J.j.kind === 'spring' ? 'spring' : 'tension', v: vec.mul(u, s * J.T), at}); }
        return [B.id, list]; })); },
    energy() { const e = energyNow(), E = e.K + e.Ug + e.Us; return {...e, heat: Math.max(0, (E0 ?? E) + work - E), work}; },
    /** a drawn shape where the world has it now: rect and ellipse by their corner and rot, a polygon's and a line's points */
    place(o) {
      const B = byObj.get(o.id); if (!B || !B.dyn) return o;
      const da = B.a - B.a0, d = {x: B.x - B.c0.x, y: B.y - B.c0.y}, deg = da * 180 / Math.PI;
      const tp = (x, y) => { const q = rot(da, {x: x - B.c0.x, y: y - B.c0.y}); return [B.x + q.x, B.y + q.y]; };
      const wrap = r => { let v = ((r + 180) % 360 + 360) % 360 - 180; return v; };
      if (o.type === 'rect' || o.type === 'ellipse') return {...o, x: o.x + d.x, y: o.y + d.y, rot: wrap((o.rot || 0) + deg)};
      if (o.type === 'line') { const [x1, y1] = tp(o.x1, o.y1), [x2, y2] = tp(o.x2, o.y2); return {...o, x1, y1, x2, y2}; }
      if (o.type === 'poly') return {...o, pts: o.pts.map(q => tp(q[0], q[1]))};
      return o;
    }
  };
  return sys;
}

/* ════════════════════════════════════════════════════════════════════════════════════════════════════════════════
   The other domains. Everything here is a pure function of the scene, so the editor recomputes it on every redraw:
   field lines follow a charge while it is dragged, rays follow a lens, P–V curves and wave functions follow their
   parameters ("live" figures). Units are SI unless a field says otherwise (draw-scene.mjs).
   ════════════════════════════════════════════════════════════════════════════════════════════════════════════════ */
export const K_E = 8.9875517923e9, H_PLANCK = 6.62607015e-34, HBAR = H_PLANCK / (2 * Math.PI), M_E = 9.1093837015e-31, EV = 1.602176634e-19, C_LIGHT = 299792458;
const HC_EV_NM = H_PLANCK * C_LIGHT / EV * 1e9;   /* 1239.84 eV nm */

/* ── electrostatics: point charges (q in μC) and plates (a line of PLATE_PIECES equal charges) ── */
const PLATE_PIECES = 40;
export function chargesOf(scene) {
  const out = [];
  for (const o of scene.objects) {
    if (o.type === 'charge') out.push({x: o.x, y: o.y, q: o.q * 1e-6, r: o.r, id: o.id});
    else if (o.type === 'plate') for (let i = 0; i < PLATE_PIECES; i++) { const t = (i + 0.5) / PLATE_PIECES; out.push({x: o.x1 + (o.x2 - o.x1) * t, y: o.y1 + (o.y2 - o.y1) * t, q: o.q * 1e-6 / PLATE_PIECES, r: 0, id: o.id, plate: true}); }
  }
  return out;
}
/** E (V/m) at p of point charges [{x,y,q (C)}]: Σ k q r̂ / r² */
export function eField(charges, p) {
  let ex = 0, ey = 0;
  for (const c of charges) { const dx = p.x - c.x, dy = p.y - c.y, r2 = dx * dx + dy * dy; if (r2 < 1e-18) continue; const k = K_E * c.q / (r2 * Math.sqrt(r2)); ex += k * dx; ey += k * dy; }
  return {x: ex, y: ey};
}
export function potential(charges, p) { let V = 0; for (const c of charges) { const r = Math.hypot(p.x - c.x, p.y - c.y); if (r > 1e-9) V += K_E * c.q / r; } return V; }
const distSeg = (p, a, b) => { const ab = vec.sub(b, a), t = Math.max(0, Math.min(1, vec.dot(vec.sub(p, a), ab) / (vec.dot(ab, ab) || 1))); return vec.len(vec.sub(p, vec.add(a, vec.mul(ab, t)))); };
/** field lines of every charge and plate in the view: [{pts, arrow:{x,y,dx,dy}}], integrated (RK4 along Ê) from the
 *  positive charges (n lines for the largest |q|, fewer for smaller ones) until they reach a negative one or leave */
export function fieldLines(scene, view, {n = 8} = {}) {
  const ch = chargesOf(scene), pts = scene.objects.filter(o => o.type === 'charge'), plates = scene.objects.filter(o => o.type === 'plate');
  if (!ch.length) return [];
  const qmax = Math.max(...pts.map(o => Math.abs(o.q)), ...plates.map(o => Math.abs(o.q) / 4), 1e-12);
  const pos = ch.reduce((s, c) => s + Math.max(0, c.q), 0), sign = pos > 0 ? 1 : -1;
  const h = Math.hypot(view.w, view.h) / 420, pad = 0.15 * Math.max(view.w, view.h);
  const inView = p => p.x > view.x - pad && p.x < view.x + view.w + pad && p.y > view.y - pad && p.y < view.y + view.h + pad;
  const dir = p => { const E = eField(ch, p), m = Math.hypot(E.x, E.y); return m > 0 ? {x: sign * E.x / m, y: sign * E.y / m} : null; };
  const sinks = pts.filter(o => Math.sign(o.q) === -sign), sinkPlates = plates.filter(o => Math.sign(o.q) === -sign);
  const starts = [];
  for (const o of pts) if (Math.sign(o.q) === sign) {
    const k = Math.max(2, Math.round(n * Math.abs(o.q) / qmax)), r0 = Math.max(o.r, 2 * h);
    for (let i = 0; i < k; i++) { const a = 2 * Math.PI * (i + 0.5) / k; starts.push({x: o.x + r0 * Math.cos(a), y: o.y + r0 * Math.sin(a)}); }
  }
  for (const o of plates) if (Math.sign(o.q) === sign) {
    const k = Math.max(2, Math.round(n * Math.abs(o.q) / qmax / 2)), u = vec.unit({x: o.x2 - o.x1, y: o.y2 - o.y1}), nn = vec.perp(u), L = Math.hypot(o.x2 - o.x1, o.y2 - o.y1);
    for (let i = 0; i < k; i++) for (const s of [1, -1]) { const t = (i + 0.5) / k; starts.push({x: o.x1 + u.x * L * t + nn.x * s * 2 * h, y: o.y1 + u.y * L * t + nn.y * s * 2 * h}); }
  }
  const lines = [];
  for (const s0 of starts) {
    let p = s0; const line = [p];
    for (let i = 0; i < 1800; i++) {
      const k1 = dir(p); if (!k1) break;
      const k2 = dir(vec.add(p, vec.mul(k1, h / 2))); if (!k2) break;
      const k3 = dir(vec.add(p, vec.mul(k2, h / 2))); if (!k3) break;
      const k4 = dir(vec.add(p, vec.mul(k3, h))); if (!k4) break;
      p = vec.add(p, vec.mul({x: k1.x + 2 * k2.x + 2 * k3.x + k4.x, y: k1.y + 2 * k2.y + 2 * k3.y + k4.y}, h / 6));
      line.push(p);
      if (!inView(p) || sinks.some(o => Math.hypot(p.x - o.x, p.y - o.y) < Math.max(o.r * 0.9, 1.5 * h)) || sinkPlates.some(o => distSeg(p, {x: o.x1, y: o.y1}, {x: o.x2, y: o.y2}) < 1.2 * h)) break;
    }
    if (line.length < 3) continue;
    const sunk = inView(line[line.length - 1]);
    if (sign < 0) line.reverse();
    /* the arrow: half-way along a line that ends on a charge, else a fifth of the view from where it starts */
    let total = 0; for (let i = 1; i < line.length; i++) total += Math.hypot(line[i].x - line[i - 1].x, line[i].y - line[i - 1].y);
    const want = sunk ? total / 2 : Math.min(total / 2, 0.2 * Math.max(view.w, view.h)), at = sign < 0 ? 1 - want / total : want / total;
    if (!(total > 0) || line.some(q => !Number.isFinite(q.x) || !Number.isFinite(q.y))) continue;
    const arrow = {at: Math.min(1, Math.max(0, at))};
    lines.push({pts: line, arrow});
  }
  return lines;
}
/** equipotential lines in the view (marching squares on a grid, joined into polylines): [{V, pts}] */
export function equipotentials(scene, view, {levels = 6, nx = 110} = {}) {
  const ch = chargesOf(scene); if (!ch.length || !levels) return [];
  const qmax = Math.max(...ch.map(c => Math.abs(c.q) * (c.plate ? PLATE_PIECES / 4 : 1)));
  const ny = Math.max(10, Math.round(nx * view.h / view.w)), dx = view.w / nx, dy = view.h / ny;
  const V = new Float64Array((nx + 1) * (ny + 1)), near = new Uint8Array((nx + 1) * (ny + 1));
  const pc = scene.objects.filter(o => o.type === 'charge');
  for (let j = 0; j <= ny; j++) for (let i = 0; i <= nx; i++) { const p = {x: view.x + i * dx, y: view.y + j * dy}, k = j * (nx + 1) + i; V[k] = potential(ch, p); near[k] = pc.some(o => Math.hypot(p.x - o.x, p.y - o.y) < o.r * 1.2) ? 1 : 0; }
  const both = ch.some(c => c.q > 0) && ch.some(c => c.q < 0), half = Math.ceil(levels / 2), Ls = [];
  for (let k = 0; k < half; k++) { const d = view.w * 0.05 * Math.pow(1.75, k), v = K_E * qmax / d; Ls.push(v); if (both) Ls.push(-v); }
  if (!both) Ls.forEach((v, i) => { Ls[i] = Math.sign(ch.reduce((s, c) => s + c.q, 0)) * Math.abs(v); });
  if (both && levels % 2) Ls.push(0);
  const out = [];
  for (const lv of Ls.slice(0, levels)) {
    const segs = [], at = (i, j) => V[j * (nx + 1) + i] - lv;
    const pt = (i0, j0, i1, j1) => { const a = at(i0, j0), b = at(i1, j1), t = a / (a - b); return {x: view.x + (i0 + (i1 - i0) * t) * dx, y: view.y + (j0 + (j1 - j0) * t) * dy, key: `${i0},${j0},${i1},${j1}`}; };
    for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
      if (near[j * (nx + 1) + i] || near[j * (nx + 1) + i + 1] || near[(j + 1) * (nx + 1) + i] || near[(j + 1) * (nx + 1) + i + 1]) continue;
      const c = (at(i, j) > 0 ? 1 : 0) | (at(i + 1, j) > 0 ? 2 : 0) | (at(i + 1, j + 1) > 0 ? 4 : 0) | (at(i, j + 1) > 0 ? 8 : 0);
      if (c === 0 || c === 15) continue;
      const e = [() => pt(i, j, i + 1, j), () => pt(i + 1, j, i + 1, j + 1), () => pt(i, j + 1, i + 1, j + 1), () => pt(i, j, i, j + 1)];
      const T = {1: [[0, 3]], 2: [[0, 1]], 3: [[1, 3]], 4: [[1, 2]], 5: [[0, 1], [2, 3]], 6: [[0, 2]], 7: [[2, 3]], 8: [[2, 3]], 9: [[0, 2]], 10: [[0, 3], [1, 2]], 11: [[1, 2]], 12: [[1, 3]], 13: [[0, 1]], 14: [[0, 3]]}[c];
      for (const [a, b] of T) segs.push([e[a](), e[b]()]);
    }
    /* join the pieces that share an edge point */
    const ends = new Map(); segs.forEach((s, i) => { for (const p of s) { if (!ends.has(p.key)) ends.set(p.key, []); ends.get(p.key).push(i); } });
    const used = new Uint8Array(segs.length);
    for (let s = 0; s < segs.length; s++) {
      if (used[s]) continue; used[s] = 1;
      const line = [segs[s][0], segs[s][1]];
      for (const dirn of [1, 0]) {
        for (;;) {
          const tip = dirn ? line[line.length - 1] : line[0], nxt = (ends.get(tip.key) || []).find(i => !used[i]);
          if (nxt === undefined) break;
          used[nxt] = 1; const q = segs[nxt][0].key === tip.key ? segs[nxt][1] : segs[nxt][0];
          if (dirn) line.push(q); else line.unshift(q);
        }
      }
      if (line.length > 3) out.push({V: lv, pts: line.map(p => ({x: p.x, y: p.y}))});
    }
  }
  return out;
}
/** the path of a moving charge through the uniform field regions (q μC, mass mg, E V/m, B T): F = q(E + v × B) */
export function chargePath(scene, o, view, {maxSteps = 4000} = {}) {
  const regions = scene.objects.filter(r => r.type === 'field'), qm = o.q / o.mass;
  const plates = scene.objects.filter(p => p.type === 'plate');
  const acc = (p, v) => {
    let ax = 0, ay = 0;
    for (const r of regions) {
      if (p.x < r.x || p.x > r.x + r.w || p.y < r.y || p.y > r.y + r.h) continue;
      if (r.kind === 'E' && r.dir === 'arrow') { const a = r.angle * Math.PI / 180; ax += qm * r.mag * Math.cos(a); ay += qm * r.mag * Math.sin(a); }
      if (r.kind === 'B' && r.dir !== 'arrow') { const Bz = r.dir === 'out' ? r.mag : -r.mag; ax += qm * v.y * Bz; ay += -qm * v.x * Bz; }
    }
    return {x: ax, y: ay};
  };
  let p = {x: o.x, y: o.y}, v = {x: o.vx, y: o.vy}; const pts = [p];
  const ds = Math.max(view.w, view.h) / 500, pad = 0.1 * Math.max(view.w, view.h);
  for (let i = 0; i < maxSteps; i++) {
    const sp = Math.hypot(v.x, v.y); if (sp < 1e-9) break;
    const dt = ds / sp;
    const f = (pp, vv) => [vv, acc(pp, vv)];
    const [a1, b1] = f(p, v), [a2, b2] = f(vec.add(p, vec.mul(a1, dt / 2)), vec.add(v, vec.mul(b1, dt / 2)));
    const [a3, b3] = f(vec.add(p, vec.mul(a2, dt / 2)), vec.add(v, vec.mul(b2, dt / 2))), [a4, b4] = f(vec.add(p, vec.mul(a3, dt)), vec.add(v, vec.mul(b3, dt)));
    const np = {x: p.x + dt / 6 * (a1.x + 2 * a2.x + 2 * a3.x + a4.x), y: p.y + dt / 6 * (a1.y + 2 * a2.y + 2 * a3.y + a4.y)};
    v = {x: v.x + dt / 6 * (b1.x + 2 * b2.x + 2 * b3.x + b4.x), y: v.y + dt / 6 * (b1.y + 2 * b2.y + 2 * b3.y + b4.y)};
    if (plates.some(pl => segCross(p, np, {x: pl.x1, y: pl.y1}, {x: pl.x2, y: pl.y2}))) { pts.push(np); break; }
    p = np; pts.push(p);
    if (p.x < view.x - pad || p.x > view.x + view.w + pad || p.y < view.y - pad || p.y > view.y + view.h + pad) break;
  }
  return pts;
}
function segCross(a, b, c, d) {
  const r = vec.sub(b, a), s = vec.sub(d, c), den = vec.cross(r, s); if (Math.abs(den) < 1e-15) return false;
  const t = vec.cross(vec.sub(c, a), s) / den, u = vec.cross(vec.sub(c, a), r) / den; return t >= 0 && t <= 1 && u >= 0 && u <= 1;
}

/* ── circuits: DC steady state by modified nodal analysis (our own Gaussian elimination) ──
   Every element is a two-terminal branch from (x1,y1) to (x2,y2); its current I runs from x1 to x2 inside it.
     resistor, bulb, galvanometer (value Ω > 0): I = (V1 − V2)/R
     battery, cell, dc (emf value, internal r):    V2 − V1 = emf − r I     (x2 is +)
     wire: its ends are one node.  ammeter, inductor (DC), closed switch, R = 0: V2 = V1, I measured
     capacitor (DC), voltmeter, open switch: no current. diode, led: ideal with a forward drop (value V): on
       (V1 − V2 = drop, I ≥ 0) or off (I = 0, V1 − V2 ≤ drop), found by trying states until they agree.
     ac sources are not solved.
   A ground fixes its node at 0 V; without one, the − end of the first source is 0 V. Each node also has a leak of
   1e-12 S to ground so that a floating part does not make the system singular. */
const TOL = 1e-6;
const elementPath = e => e.kind === 'wire' && e.route !== 'straight' ? [{x: e.x1, y: e.y1}, e.route === 'hv' ? {x: e.x2, y: e.y1} : {x: e.x1, y: e.y2}, {x: e.x2, y: e.y2}] : [{x: e.x1, y: e.y1}, {x: e.x2, y: e.y2}];
export {elementPath};
/** the nodes of the circuit: terminals that coincide, wires joining their ends, ends lying on a wire */
/** the circuit's two-terminal branches: the elements, and each bridge wire (meter bridge, potentiometer) as two
 *  resistances on either side of its jockey J, R·at and R·(1 − at), so a lead ending at J joins the wire there */
export function bridgeJockey(b) { return {x: b.x1 + (b.x2 - b.x1) * b.at, y: b.y1 + (b.y2 - b.y1) * b.at}; }
export function circuitElements(scene) {
  const bridges = scene.objects.filter(o => o.type === 'bridge');
  /* a lead that ends on a bridge wire touches it at the jockey (the sliding contact), wherever it is drawn */
  const onWire = (p, b) => { const A = {x: b.x1, y: b.y1}, B = {x: b.x2, y: b.y2}, L = vec.len(vec.sub(B, A)), t = vec.dot(vec.sub(p, A), vec.sub(B, A)) / (L * L || 1); return t > 0.01 && t < 0.99 && distSeg(p, A, B) < Math.max(0.01, (scene.grid || 0.1) / 100) ? bridgeJockey(b) : null; };
  const out = scene.objects.filter(o => o.type === 'element').map(e => {
    let c = e;
    for (const b of bridges) for (const k of [1, 2]) { const J = onWire({x: c['x' + k], y: c['y' + k]}, b); if (J) c = {...c, ['x' + k]: J.x, ['y' + k]: J.y}; }
    return c;
  });
  for (const b of bridges) {
    const J = bridgeJockey(b);
    out.push({id: b.id + '.1', type: 'element', kind: 'resistor', x1: b.x1, y1: b.y1, x2: J.x, y2: J.y, value: Math.max(1e-9, b.R * b.at), r: 0, part: b.id},
      {id: b.id + '.2', type: 'element', kind: 'resistor', x1: J.x, y1: J.y, x2: b.x2, y2: b.y2, value: Math.max(1e-9, b.R * (1 - b.at)), r: 0, part: b.id});
  }
  return out;
}
/** the meter bridge's balance point: the jockey at l = L·R / (R + S) from the R end (galvanometer current zero) */
export const meterBridgeBalance = (R, S, L = 100) => L * R / (R + S);
export function circuitNodes(scene) {
  const els = circuitElements(scene), grounds = scene.objects.filter(o => o.type === 'ground');
  const tol = Math.max(0.01, (scene.grid || 0.1) / 100);
  const terms = [];
  els.forEach(e => { terms.push({p: {x: e.x1, y: e.y1}, el: e, end: 1}); terms.push({p: {x: e.x2, y: e.y2}, el: e, end: 2}); });
  grounds.forEach(g => terms.push({p: {x: g.x, y: g.y}, ground: g}));
  const parent = terms.map((_, i) => i), find = i => { while (parent[i] !== i) i = parent[i] = parent[parent[i]]; return i; }, join = (a, b) => { a = find(a); b = find(b); if (a !== b) parent[a] = b; };
  for (let i = 0; i < terms.length; i++) for (let j = i + 1; j < terms.length; j++) if (Math.hypot(terms[i].p.x - terms[j].p.x, terms[i].p.y - terms[j].p.y) < tol) join(i, j);
  terms.forEach((t, i) => { if (t.el?.kind === 'wire' && t.end === 1) join(i, i + 1); });
  /* an end on the middle of a wire */
  terms.forEach((t, i) => { for (let j = 0; j < terms.length; j += 2) { const w = terms[j].el; if (!w || w.kind !== 'wire' || t.el === w) continue; const P = elementPath(w); for (let s = 0; s + 1 < P.length; s++) if (distSeg(t.p, P[s], P[s + 1]) < tol) join(i, j); } });
  const ids = new Map(); terms.forEach((t, i) => { const r = find(i); if (!ids.has(r)) ids.set(r, ids.size); t.node = ids.get(r); });
  return {terms, count: ids.size, els, grounds};
}
function gauss(A, b) {
  const n = b.length;
  for (let c = 0; c < n; c++) {
    let p = c; for (let r = c + 1; r < n; r++) if (Math.abs(A[r][c]) > Math.abs(A[p][c])) p = r;
    if (Math.abs(A[p][c]) < 1e-14) return null;
    [A[c], A[p]] = [A[p], A[c]]; [b[c], b[p]] = [b[p], b[c]];
    for (let r = c + 1; r < n; r++) { const k = A[r][c] / A[c][c]; if (!k) continue; for (let j = c; j < n; j++) A[r][j] -= k * A[c][j]; b[r] -= k * b[c]; }
  }
  const x = new Array(n).fill(0);
  for (let r = n - 1; r >= 0; r--) { let s = b[r]; for (let j = r + 1; j < n; j++) s -= A[r][j] * x[j]; x[r] = s / A[r][r]; }
  return x;
}
const SOURCE = ['battery', 'cell', 'dc'], RESIST = ['resistor', 'bulb', 'galvanometer', 'rheostat'];
/* one linear solve with given diode states; replace: {id: 'short'|'open'|{current}} overrides for the transient;
   zeroSources: emfs and drops at 0 */
function mnaSolve(net, ref, diodeOn, replace = {}, zeroSources = false) {
  const {terms, count, els} = net, node = (e, end) => terms.find(t => t.el === e && t.end === end).node;
  const idx = k => k === ref ? -1 : k < ref ? k : k - 1, nv = count - 1;
  const vs = [];      /* branches with a current unknown: [el, emf, r] */
  const cur = [];     /* current sources: [el, I] */
  const res = [];
  for (const e of els) {
    const rep = replace[e.id];
    if (e.kind === 'wire') continue;
    if (rep === 'open') continue;
    if (rep === 'short') { vs.push([e, 0, 0]); continue; }
    if (rep && typeof rep === 'object') { cur.push([e, rep.current]); continue; }
    if (SOURCE.includes(e.kind)) vs.push([e, zeroSources ? 0 : e.value, e.r]);
    else if (RESIST.includes(e.kind)) { if (e.value > 0) res.push([e, e.value]); else vs.push([e, 0, 0]); }
    else if (e.kind === 'ammeter' || e.kind === 'inductor' || (e.kind === 'switch' && e.closed)) vs.push([e, 0, 0]);
    else if ((e.kind === 'diode' || e.kind === 'led') && diodeOn.has(e.id)) vs.push([e, zeroSources ? 0 : -e.value, 0]);
  }
  const n = nv + vs.length, A = Array.from({length: n}, () => new Array(n).fill(0)), b = new Array(n).fill(0);
  const addG = (a, c, g) => { const i = idx(a), j = idx(c); if (i >= 0) A[i][i] += g; if (j >= 0) A[j][j] += g; if (i >= 0 && j >= 0) { A[i][j] -= g; A[j][i] -= g; } };
  for (let k = 0; k < count; k++) if (k !== ref) A[idx(k)][idx(k)] += 1e-12;
  for (const [e, R] of res) addG(node(e, 1), node(e, 2), 1 / R);
  for (const [e, I] of cur) { const i = idx(node(e, 1)), j = idx(node(e, 2)); if (i >= 0) b[i] -= I; if (j >= 0) b[j] += I; }
  vs.forEach(([e, emf, r], m) => {
    const row = nv + m, i = idx(node(e, 1)), j = idx(node(e, 2));
    /* current I (x1 → x2 inside) leaves node 1 and enters node 2 */
    if (i >= 0) { A[i][row] += 1; A[row][i] -= 1; }
    if (j >= 0) { A[j][row] -= 1; A[row][j] += 1; }
    A[row][row] += r; b[row] = emf;      /* V2 − V1 + r I = emf */
  });
  const x = gauss(A, b);
  if (!x || x.some(v => !Number.isFinite(v))) return null;
  const V = k => k === ref ? 0 : x[idx(k)];
  const out = new Map();
  for (const e of els) {
    const V1 = V(node(e, 1)), V2 = V(node(e, 2)); let I = 0;
    const m = vs.findIndex(([x0]) => x0 === e);
    if (m >= 0) I = x[nv + m]; else { const rr = res.find(([x0]) => x0 === e); if (rr) I = (V1 - V2) / rr[1]; const cc = cur.find(([x0]) => x0 === e); if (cc) I = cc[1]; }
    out.set(e.id, {V1, V2, I});
  }
  return {out, V};
}
/** the DC steady state: {ok, code, nodes, el: Map id → {V1, V2, I (x1 → x2), drop V1 − V2}, transients} */
export function solveCircuit(scene) {
  const net = circuitNodes(scene), {els, terms} = net;
  if (!els.some(e => e.kind !== 'wire')) return {ok: false, code: 'empty', el: new Map(), transients: [], net};
  if (els.some(e => e.kind === 'ac')) return {ok: false, code: 'ac', el: new Map(), transients: [], net};
  const g = terms.find(t => t.ground), src = els.find(e => SOURCE.includes(e.kind));
  const ref = g ? g.node : src ? terms.find(t => t.el === src && t.end === 1).node : 0;
  const diodes = els.filter(e => e.kind === 'diode' || e.kind === 'led');
  let on = new Set(), sol = null;
  for (let it = 0; it < 2 * diodes.length + 2; it++) {
    sol = mnaSolve(net, ref, on); if (!sol) return {ok: false, code: 'short', el: new Map(), transients: [], net};
    const next = new Set();
    for (const d of diodes) { const r = sol.out.get(d.id); if (on.has(d.id) ? r.I >= -1e-12 : r.V1 - r.V2 > d.value + 1e-12) next.add(d.id); }
    if (next.size === on.size && [...next].every(id => on.has(id))) break;
    on = next;
  }
  const el = new Map([...sol.out].map(([id, r]) => [id, {...r, drop: r.V1 - r.V2}]));
  /* the transient of the one capacitor or inductor: its Thevenin resistance with the sources at zero */
  const dyn = els.filter(e => e.kind === 'capacitor' || e.kind === 'dielectric' || e.kind === 'inductor'), transients = [];
  if (dyn.length === 1) {
    const e = dyn[0], test = mnaSolve(net, ref, on, {[e.id]: {current: -1}}, true);
    if (test) {
      const r = test.out.get(e.id), Rth = r.V1 - r.V2;     /* the element drives 1 A out of its x1 end: V1 − V2 = R_th */
      if (Rth > 1e-9 && Rth < 1e12) {
        if (e.kind !== 'inductor') { const tau = Rth * e.value * 1e-6, Vf = el.get(e.id).V1 - el.get(e.id).V2; transients.push({id: e.id, kind: 'rc', tau, R: Rth, final: Vf, at: t => Vf * (1 - Math.exp(-t / tau)), current: t => Vf / Rth * Math.exp(-t / tau)}); }
        else { const tau = e.value / Rth, If = el.get(e.id).I; transients.push({id: e.id, kind: 'rl', tau, R: Rth, final: If, at: t => If * (1 - Math.exp(-t / tau))}); }
      }
    }
  }
  return {ok: true, el, transients, net, ref};
}
/** equivalent resistance between two terminals of a network of resistors (for tests and readouts) */
export const seriesR = (...r) => r.reduce((a, b) => a + b, 0), parallelR = (...r) => 1 / r.reduce((a, b) => a + 1 / b, 0);

/* ── thermodynamics: ideal-gas processes on a P–V graph (any consistent units; for a cycle nR = 1, P = T/V) ── */
/** points of a process in data units: isotherm P = y1 x1 / V, adiabat P = y1 (x1/V)^γ, isobar P = y1, isochore V = x1 */
export function processPoints(kind, {x1, x2, y1, y2, gamma = 1.4}, n = 160) {
  const pts = [];
  if (kind === 'isochore') { for (let i = 0; i <= 1; i++) pts.push({x: x1, y: i ? y2 : y1}); return pts; }
  const P = kind === 'isotherm' ? V => y1 * x1 / V : kind === 'adiabat' ? V => y1 * Math.pow(x1 / V, gamma) : () => y1;
  for (let i = 0; i <= n; i++) { const V = x1 + (x2 - x1) * i / n; pts.push({x: V, y: P(V)}); }
  return pts;
}
/** ∫ P dV along a process, by Simpson's rule on its own formula (2000 intervals) */
export function processWork(kind, o) {
  if (kind === 'isochore') return 0;
  const P = kind === 'isotherm' ? V => o.y1 * o.x1 / V : kind === 'adiabat' ? V => o.y1 * Math.pow(o.x1 / V, o.gamma) : () => o.y1;
  const N = 2000, h = (o.x2 - o.x1) / N; let s = P(o.x1) + P(o.x2);
  for (let i = 1; i < N; i++) s += (i % 2 ? 4 : 2) * P(o.x1 + i * h);
  return s * h / 3;
}
/** an ideal-gas cycle (nR = 1): its states A, B, C, D, its legs, the work W (from the integrals), the heat taken in
 *  Q_in (from the state functions: Q = W on an isotherm, C_V ΔT on an isochore, 0 on an adiabat) and η = W / Q_in */
export function gasCycle(o) {
  const g = o.gamma, cv = 1 / (g - 1), Th = Math.max(o.t1, o.t2), Tc = Math.min(o.t1, o.t2), Va = Math.min(o.v1, o.v2), Vb = Math.max(o.v1, o.v2);
  let S;
  if (o.kind === 'carnot') { const k = Math.pow(Th / Tc, cv); S = [[Va, Th], [Vb, Th], [Vb * k, Tc], [Va * k, Tc]]; }
  else if (o.kind === 'otto') { const T2 = Tc * Math.pow(Vb / Va, g - 1), T3 = Math.max(Th, T2 * 1.0001), T4 = T3 * Math.pow(Va / Vb, g - 1); S = [[Vb, Tc], [Va, T2], [Va, T3], [Vb, T4]]; }
  else S = [[Va, Th], [Vb, Th], [Vb, Tc], [Va, Tc]];
  const states = S.map(([V, T], i) => ({name: 'ABCD'[i], V, T, P: T / V}));
  const kinds = o.kind === 'carnot' ? ['isotherm', 'adiabat', 'isotherm', 'adiabat'] : o.kind === 'otto' ? ['adiabat', 'isochore', 'adiabat', 'isochore'] : ['isotherm', 'isochore', 'isotherm', 'isochore'];
  const legs = kinds.map((kind, i) => {
    const a = states[i], b = states[(i + 1) % 4], p = {x1: a.V, x2: b.V, y1: a.P, y2: b.P, gamma: g};
    const W = processWork(kind, p), Q = kind === 'isotherm' ? W : kind === 'adiabat' ? 0 : cv * (b.T - a.T);
    return {kind, from: a.name, to: b.name, pts: processPoints(kind, p), W, Q};
  });
  const W = legs.reduce((s, l) => s + l.W, 0), Qin = legs.reduce((s, l) => s + Math.max(0, l.Q), 0);
  return {states, legs, W, Qin, Qout: Qin - W, eta: W / Qin, Th, Tc};
}

/* ── optics ── sign convention ("real is positive"): an object distance u > 0 for a real object on the side the light
   comes from, an image distance v > 0 for a real image (beyond a lens, in front of a mirror), f > 0 for a converging
   lens or a concave mirror. Thin lens and mirror: 1/u + 1/v = 1/f, magnification m = −v/u. The ray tracer uses the
   thin-element (paraxial) map at a lens or a mirror, s' = s − y/f for the slope s along the direction of travel and
   the height y above its axis, which images every point exactly, and Snell's law (with total internal reflection) at
   the faces of prisms and slabs. */
export const lensImage = (u, f) => 1 / (1 / f - 1 / u);
export const mirrorImage = (u, f) => 1 / (1 / f - 1 / u);
export function prismCorners(o) { const ht = (o.size / 2) / Math.tan(o.apex * Math.PI / 360); return [{x: o.x - o.size / 2, y: o.y}, {x: o.x + o.size / 2, y: o.y}, {x: o.x, y: o.y + ht}]; }
const slabCorners = o => [{x: o.x, y: o.y}, {x: o.x + o.w, y: o.y}, {x: o.x + o.w, y: o.y + o.h}, {x: o.x, y: o.y + o.h}];
const inPoly = (p, P) => { let c = false; for (let i = 0, j = P.length - 1; i < P.length; j = i++) if ((P[i].y > p.y) !== (P[j].y > p.y) && p.x < (P[j].x - P[i].x) * (p.y - P[i].y) / (P[j].y - P[i].y) + P[i].x) c = !c; return c; };
/** a ray from p in direction d through the scene's optics: {pts, hits, d (the last direction), forks}. Lenses and
 *  mirrors may be turned (rot): the ray is followed in the element's own frame (its axis along x). A half-silvered
 *  mirror (half) lets the ray through and starts a reflected branch, traced on in forks [{pts, …}]; a screen stops it. */
export function traceRay(scene, p0, d0, {len = 50, maxHits = 16, depth = 0} = {}) {
  const lenses = scene.objects.filter(o => o.type === 'lens'), mirrors = scene.objects.filter(o => o.type === 'mirror'), screens = scene.objects.filter(o => o.type === 'screen');
  const polys = scene.objects.filter(o => o.type === 'prism' || o.type === 'slab').map(o => ({o, P: o.type === 'prism' ? prismCorners(o) : slabCorners(o)}));
  const frame = E => { const a = (E.rot || 0) * Math.PI / 180; return {c: Math.cos(a), s: Math.sin(a)}; };
  const toL = (E, R, v) => ({x: R.c * v.x + R.s * v.y, y: -R.s * v.x + R.c * v.y}), toW = (R, v) => ({x: R.c * v.x - R.s * v.y, y: R.s * v.x + R.c * v.y});
  let p = p0, d = vec.unit(d0), left = len, hits = 0; const pts = [p], forks = [];
  while (left > 1e-9 && hits < maxHits) {
    let best = null;
    const consider = (t, what) => { if (t > 1e-7 && t <= left && (!best || t < best.t)) best = {t, ...what}; };
    for (const E of [...lenses, ...mirrors]) {
      const R = frame(E), lp = toL(E, R, vec.sub(p, E)), ld = toL(E, R, d);
      if (Math.abs(ld.x) < 1e-12) continue;
      const t = -lp.x / ld.x, y = lp.y + ld.y * t;
      if (E.type === 'lens' ? Math.abs(y) <= E.h * 1.5 : Math.abs(y) <= E.h / 2 * 1.02) consider(t, E.type === 'lens' ? {lens: E} : {mirror: E});
    }
    for (const Sc of screens) {
      const a = (Sc.rot || 0) * Math.PI / 180, e = {x: -Math.sin(a), y: Math.cos(a)}, A = vec.sub(Sc, vec.mul(e, Sc.h / 2)), s = vec.mul(e, Sc.h), den = vec.cross(d, s);
      if (Math.abs(den) < 1e-14) continue;
      const t = vec.cross(vec.sub(A, p), s) / den, u = vec.cross(vec.sub(A, p), d) / den;
      if (u >= 0 && u <= 1) consider(t, {screen: Sc});
    }
    for (const {o, P} of polys) for (let i = 0; i < P.length; i++) {
      const a = P[i], b = P[(i + 1) % P.length], s = vec.sub(b, a), den = vec.cross(d, s); if (Math.abs(den) < 1e-14) continue;
      const t = vec.cross(vec.sub(a, p), s) / den, u = vec.cross(vec.sub(a, p), d) / den;
      if (u >= 0 && u <= 1) consider(t, {poly: o, P, edge: vec.unit(s)});
    }
    if (!best) { p = vec.add(p, vec.mul(d, left)); pts.push(p); left = 0; break; }
    p = vec.add(p, vec.mul(d, best.t)); left -= best.t; pts.push(p); hits++;
    if (best.screen) { left = 0; break; }
    if (best.lens || best.mirror) {
      const E = best.lens || best.mirror, R = frame(E), ld = toL(E, R, d), lp = toL(E, R, vec.sub(p, E)), sx = Math.sign(ld.x), sl = ld.y / Math.abs(ld.x);
      let nd;
      if (best.lens) nd = {x: sx, y: sl - lp.y / E.f};
      else {
        const back = (E.face === 'left') !== (sx > 0);
        const refl = {x: -sx, y: E.f ? sl - lp.y / E.f : sl};
        if (E.half) { if (depth < 3) forks.push(traceRay(scene, vec.add(p, vec.mul(vec.unit(toW(R, refl)), 1e-9)), toW(R, refl), {len: left, maxHits, depth: depth + 1})); nd = ld; }
        else if (back) { left = 0; break; }      /* the back of a mirror */
        else nd = refl;
      }
      d = vec.unit(toW(R, nd));
      p = vec.add(p, vec.mul(d, 1e-9));
    } else {
      const N0 = vec.perp(best.edge), inside = inPoly(vec.add(p, vec.mul(d, -1e-6)), best.P);
      let N = vec.dot(N0, d) > 0 ? vec.mul(N0, -1) : N0;       /* against the ray */
      const n1 = inside ? best.poly.n : 1, n2 = inside ? 1 : best.poly.n, eta = n1 / n2, c1 = -vec.dot(d, N), k = 1 - eta * eta * (1 - c1 * c1);
      d = k < 0 ? vec.unit(vec.add(d, vec.mul(N, 2 * c1))) : vec.unit(vec.add(vec.mul(d, eta), vec.mul(N, eta * c1 - Math.sqrt(k))));
      p = vec.add(p, vec.mul(d, 1e-9));
    }
  }
  return {pts, hits, d, end: p, forks};
}
/** the image of an object arrow through the system, by tracing two rays from its tip and meeting their last lines:
 *  {x, y, h, real, m} (null if the rays leave parallel or there is no lens or mirror ahead) */
export function opticImage(scene, o, span = 200) {
  const rays = principalRays(scene, o, span); if (rays.length < 2) return null;
  const [a, b] = rays, pa = a.trace.pts[a.trace.pts.length - 2], pb = b.trace.pts[b.trace.pts.length - 2], da = a.trace.d, db = b.trace.d;
  const den = vec.cross(da, db); if (Math.abs(den) < 1e-12) return null;
  const t = vec.cross(vec.sub(pb, pa), db) / den, u = vec.cross(vec.sub(pb, pa), da) / den, I = vec.add(pa, vec.mul(da, t));
  return {x: I.x, y: o.y, h: I.y - o.y, top: I, real: t > 0 && u > 0, m: (I.y - o.y) / o.h, lastA: pa, lastB: pb};
}
/** the principal rays of an object arrow: parallel to the axis, through the centre (vertex) of the first lens or
 *  mirror, and through its front focal point */
export function principalRays(scene, o, span = 50) {
  const els = scene.objects.filter(e => (e.type === 'lens' || e.type === 'mirror') && e.x > o.x + 1e-6).sort((a, b) => a.x - b.x), E = els[0];
  if (!E) return [];
  const tip = {x: o.x, y: o.y + o.h}, out = [];
  const go = (d, kind) => out.push({kind, trace: traceRay(scene, tip, d, {len: span})});
  go({x: 1, y: 0}, 'parallel');
  go(vec.sub({x: E.x, y: E.y}, tip), 'centre');
  if (E.type === 'lens' || E.f) { let d = vec.sub({x: E.x - E.f, y: E.y}, tip); if (Math.abs(d.x) > 1e-6) { if (d.x < 0) d = vec.mul(d, -1); go(d, 'focal'); } }
  return out;
}

/* ── single slit, double slit, grating: I(θ)/I₀ = (sin β / β)² (sin Nα / N sin α)², β = π a sin θ / λ,
   α = π d sin θ / λ (a, d in mm, L in m, λ in nm); y = L tan θ on the screen ── */
export function slitIntensity(o, y) {
  const lam = o.lambda * 1e-9, th = Math.atan2(y, o.L), s = Math.sin(th), b = Math.PI * o.a * 1e-3 * s / lam, a = Math.PI * o.d * 1e-3 * s / lam;
  const env = Math.abs(b) < 1e-9 ? 1 : (Math.sin(b) / b) ** 2;
  if (o.n <= 1) return env;
  const N = Math.round(o.n), sa = Math.sin(a), inter = Math.abs(sa) < 1e-9 ? 1 : (Math.sin(N * a) / (N * sa)) ** 2;
  return env * inter;
}
export const fringeSpacing = o => o.lambda * 1e-9 * o.L / (o.d * 1e-3);
/** the half-height of the screen shown (m): three and a half fringes, or the single slit's second minimum */
export const slitRange = o => o.n <= 1 ? 2.6 * o.lambda * 1e-9 * o.L / (o.a * 1e-3) : 3.5 * fringeSpacing(o);
/** the bright fringes (principal maxima) on the screen within ±range (m), found numerically */
export function slitMaxima(o, range = slitRange(o)) {
  const N = 4000, out = []; let prev = slitIntensity(o, -range), cur = slitIntensity(o, -range + 2 * range / N);
  for (let i = 2; i <= N; i++) { const y = -range + 2 * range * i / N, next = slitIntensity(o, y); if (cur >= prev && cur > next && cur > (o.n > 2 ? 0.25 : 0.05)) {
    let lo = y - 4 * range / N, hi = y; for (let k = 0; k < 60; k++) { const m1 = lo + (hi - lo) / 3, m2 = hi - (hi - lo) / 3; if (slitIntensity(o, m1) < slitIntensity(o, m2)) lo = m1; else hi = m2; } out.push((lo + hi) / 2); }
    prev = cur; cur = next; }
  return out;
}

/* ── quantum wells (L in nm, V0 and E in eV, mass in electron masses) ── */
/** infinite well: E_n = n² h² / (8 m L²) in eV */
export const infiniteWellEnergy = (n, L, mass = 1) => n * n * H_PLANCK * H_PLANCK / (8 * mass * M_E * (L * 1e-9) ** 2) / EV;
/** finite well of depth V0 (V = 0 inside |x| < L/2): the bound energies, from z tan z = √(z0² − z²) (even) and
 *  −z cot z = √(z0² − z²) (odd), z = kL/2, z0 = (L/2)√(2 m V0)/ħ; E = 2ħ² z² / (m L²) */
export function finiteWellLevels(L, V0, mass = 1) {
  const m = mass * M_E, Lm = L * 1e-9, z0 = Lm / 2 * Math.sqrt(2 * m * V0 * EV) / HBAR, out = [];
  const root = (f, a, b) => { let fa = f(a); for (let k = 0; k < 200; k++) { const c = (a + b) / 2, fc = f(c); if ((fc > 0) === (fa > 0)) { a = c; fa = fc; } else b = c; } return (a + b) / 2; };
  for (let k = 0; k * Math.PI / 2 < z0; k++) {
    const a = k * Math.PI / 2 + 1e-12, b = Math.min((k + 1) * Math.PI / 2 - 1e-12, z0);
    const f = k % 2 === 0 ? z => z * Math.tan(z) - Math.sqrt(Math.max(0, z0 * z0 - z * z)) : z => -z / Math.tan(z) - Math.sqrt(Math.max(0, z0 * z0 - z * z));
    if (b <= a) continue;
    if ((f(a) > 0) === (f(b) > 0)) continue;
    const z = root(f, a, b);
    out.push({n: out.length + 1, E: 2 * HBAR * HBAR * z * z / (m * Lm * Lm) / EV, parity: k % 2 === 0 ? 'even' : 'odd', z});
  }
  return out;
}
const hermite = (n, x) => { let a = 1, b = 2 * x; if (n === 0) return a; for (let k = 1; k < n; k++) { const c = 2 * x * b - 2 * k * a; a = b; b = c; } return b; };
/** a well's potential, levels and wave functions: {V(x), xs: [x0, x1] (nm), Emax, levels: [{n, E, psi(x)}], T} */
export function wellModel(o) {
  const m = o.mass * M_E, L = o.L, k = E => Math.sqrt(2 * m * Math.max(0, E) * EV) / HBAR * 1e-9;   /* per nm */
  if (o.kind === 'infinite') {
    const levels = Array.from({length: o.levels}, (_, i) => { const n = i + 1; return {n, E: infiniteWellEnergy(n, L, o.mass), psi: x => Math.abs(x) > L / 2 ? 0 : n % 2 ? Math.cos(n * Math.PI * x / L) : Math.sin(n * Math.PI * x / L)}; });
    return {V: x => Math.abs(x) > L / 2 ? Infinity : 0, xs: [-0.8 * L, 0.8 * L], walls: [-L / 2, L / 2], Emax: (levels.at(-1)?.E || infiniteWellEnergy(1, L, o.mass)) * 1.3, levels};
  }
  if (o.kind === 'finite') {
    const levels = finiteWellLevels(L, o.V0, o.mass).slice(0, o.levels).map(l => {
      const kk = k(l.E), kap = Math.sqrt(2 * m * (o.V0 - l.E) * EV) / HBAR * 1e-9, even = l.parity === 'even';
      const edge = even ? Math.cos(kk * L / 2) : Math.sin(kk * L / 2);
      const raw = x => Math.abs(x) <= L / 2 ? (even ? Math.cos(kk * x) : Math.sin(kk * x)) : Math.sign(even ? 1 : x) * edge * Math.exp(-kap * (Math.abs(x) - L / 2));
      return {...l, psi: raw};
    });
    return {V: x => Math.abs(x) > L / 2 ? o.V0 : 0, xs: [-L, L], walls: [-L / 2, L / 2], Emax: o.V0 * 1.3, levels};
  }
  if (o.kind === 'harmonic') {
    const w = o.V0 * EV / HBAR, x0 = Math.sqrt(HBAR / (m * w)) * 1e9, N = Math.max(1, o.levels), xt = x0 * Math.sqrt(2 * N + 1) * 1.35;
    const levels = Array.from({length: o.levels}, (_, n) => ({n, E: (n + 0.5) * o.V0, psi: x => hermite(n, x / x0) * Math.exp(-((x / x0) ** 2) / 2)}));
    return {V: x => 0.5 * m * w * w * (x * 1e-9) ** 2 / EV, xs: [-xt, xt], Emax: (N + 0.5) * o.V0 * 1.25, levels, x0};
  }
  /* barrier (V0 for |x| < L/2) and step (V0 for x > 0): one incident energy E */
  const E = Math.max(1e-6, o.E), k1 = k(E), lam = 2 * Math.PI / k1, span = Math.max(2.5 * L, 1.8 * lam);
  if (o.kind === 'step') {
    const below = E < o.V0, kap = Math.sqrt(2 * m * Math.abs(o.V0 - E) * EV) / HBAR * 1e-9, t = below ? 0 : 2 * k1 / (k1 + kap);
    const T = below ? 0 : 4 * k1 * kap / (k1 + kap) ** 2;
    return {V: x => x > 0 ? o.V0 : 0, xs: [-span, span], walls: [0], Emax: Math.max(o.V0, E) * 1.3, T, levels: [{n: 0, E, psi: x => x <= 0 ? Math.cos(k1 * x) : below ? Math.exp(-kap * x) : t * Math.cos(kap * x)}]};
  }
  const below = E < o.V0, q = Math.sqrt(2 * m * Math.abs(o.V0 - E) * EV) / HBAR * 1e-9;
  const T = below ? 1 / (1 + o.V0 ** 2 * Math.sinh(q * L) ** 2 / (4 * E * (o.V0 - E))) : 1 / (1 + o.V0 ** 2 * Math.sin(q * L) ** 2 / (4 * E * Math.max(1e-12, E - o.V0)));
  const st = Math.sqrt(T);
  const psi = x => x < -L / 2 ? Math.cos(k1 * (x + L / 2)) : x > L / 2 ? st * Math.cos(k1 * (x - L / 2)) : below ? Math.exp(Math.log(st) * (x + L / 2) / L) : Math.cos(q * (x + L / 2)) * (1 + (st - 1) * (x + L / 2) / L);
  return {V: x => Math.abs(x) < L / 2 ? o.V0 : 0, xs: [-span, span], walls: [-L / 2, L / 2], Emax: Math.max(o.V0, E) * 1.35, T, levels: [{n: 0, E, psi}]};
}
/* ── a potential typed as V(x): the stationary Schrödinger equation −(ħ²/2m) ψ'' + V ψ = E ψ, solved numerically.
   Units: x in nm, V and E in eV, m in electron masses; C = ħ²/(2 m_e) = 0.0380998 eV nm².
   Bound states: the operator by central differences on a grid of N inner points over [x0, x1] with ψ = 0 at both ends
   (a symmetric tridiagonal matrix: 2C/h² + V_i on the diagonal, −C/h² beside it). Its eigenvalues are found one by
   one by bisection with the Sturm sequence count (how many eigenvalues lie below λ), each eigenvector by inverse
   iteration (the tridiagonal system solved by the Thomas algorithm). The error is O(h²) relative to the level.
   Scattering at energy E: V is cut into slabs where it is constant (cells of equal value merged), and (ψ, ψ') is
   carried through each slab by its exact 2×2 matrix (cos kd, sin kd / k; −k sin kd, cos kd), with k² = (E − V)/C
   (cosh and sinh where E < V). Starting on the right from the outgoing wave t e^{ik_R x} (t = 1) and going left, the
   wave on the left splits into incident A e^{ik_L x} and reflected B e^{−ik_L x}; T = (k_R/k_L)/|A|², R = |B/A|².
   For piecewise-constant V this is exact; a smooth V is sampled at the cells' midpoints. ── */
export const HBAR2_2ME = HBAR * HBAR / (2 * M_E) / EV * 1e18;   /* eV nm² */
/** the lowest `count` eigenvalues and normalised eigenvectors (∫ψ² dx = 1) of −C ψ'' + V ψ on [x0, x1], ψ(x0) = ψ(x1) = 0 */
export function boundStates(V, x0, x1, {mass = 1, N = 600, count = 4} = {}) {
  const C = HBAR2_2ME / mass, h = (x1 - x0) / (N + 1), off = -C / (h * h);
  const xs = new Float64Array(N), d = new Float64Array(N);
  for (let i = 0; i < N; i++) { xs[i] = x0 + (i + 1) * h; const v = V(xs[i]); d[i] = 2 * C / (h * h) + (Number.isFinite(v) ? Math.max(-1e6, Math.min(1e6, v)) : 1e6); }
  /* eigenvalues below lam: the sign changes of the Sturm sequence */
  const below = lam => { let q = d[0] - lam, c = q < 0 ? 1 : 0; for (let i = 1; i < N; i++) { q = d[i] - lam - off * off / (q === 0 ? 1e-300 : q); if (q < 0) c++; } return c; };
  let lo = Infinity, hi = -Infinity; for (let i = 0; i < N; i++) { lo = Math.min(lo, d[i] - 2 * Math.abs(off)); hi = Math.max(hi, d[i] + 2 * Math.abs(off)); }
  const out = [];
  for (let k = 0; k < Math.min(count, N); k++) {
    let a = lo, b = hi;
    for (let it = 0; it < 200 && b - a > 1e-13 * Math.max(1, Math.abs(a) + Math.abs(b)); it++) { const m = (a + b) / 2; if (below(m) > k) b = m; else a = m; }
    const E = (a + b) / 2;
    /* inverse iteration: (H − (E + δ)) y = previous y */
    let y = new Float64Array(N).fill(1); y[0] = 0.5;
    const shift = E + 1e-10 * Math.max(1, Math.abs(E));
    for (let it = 0; it < 4; it++) {
      const cp = new Float64Array(N), dp = new Float64Array(N);
      let den = d[0] - shift; cp[0] = off / den; dp[0] = y[0] / den;
      for (let i = 1; i < N; i++) { den = d[i] - shift - off * cp[i - 1]; if (Math.abs(den) < 1e-300) den = 1e-300; cp[i] = off / den; dp[i] = (y[i] - off * dp[i - 1]) / den; }
      const z = new Float64Array(N); z[N - 1] = dp[N - 1];
      for (let i = N - 2; i >= 0; i--) z[i] = dp[i] - cp[i] * z[i + 1];
      let nrm = 0; for (let i = 0; i < N; i++) nrm += z[i] * z[i]; nrm = Math.sqrt(nrm * h) || 1;
      for (let i = 0; i < N; i++) z[i] /= nrm;
      y = z;
    }
    /* a fixed sign: the first lobe up */
    let first = 0; for (let i = 0; i < N; i++) if (Math.abs(y[i]) > 1e-3 * Math.sqrt(1 / (x1 - x0))) { first = y[i]; break; }
    if (first < 0) for (let i = 0; i < N; i++) y[i] = -y[i];
    out.push({n: k + 1, E, xs, psi: y});
  }
  return out;
}
/* complex numbers as [re, im] */
const cx = {add: (a, b) => [a[0] + b[0], a[1] + b[1]], mul: (a, b) => [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]], scale: (a, k) => [a[0] * k, a[1] * k],
  div: (a, b) => { const q = b[0] * b[0] + b[1] * b[1]; return [(a[0] * b[0] + a[1] * b[1]) / q, (a[1] * b[0] - a[0] * b[1]) / q]; }, abs2: a => a[0] * a[0] + a[1] * a[1]};
/* the slab matrix carrying (ψ, ψ') over a distance d where k² = q (q = (E − V)/C) */
function slabMatrix(q, d) {
  if (q > 1e-14) { const k = Math.sqrt(q), c = Math.cos(k * d), s = Math.sin(k * d); return [c, s / k, -k * s, c]; }
  if (q < -1e-14) { const k = Math.sqrt(-q), kd = Math.max(-700, Math.min(700, k * d)), c = Math.cosh(kd), s = Math.sinh(kd); return [c, s / k, k * s, c]; }
  return [1, d, 0, 1];
}
/** V cut into slabs [{a, b, V}] over [x0, x1] (N cells, sampled at their midpoints, equal neighbours merged) */
export function potentialSlabs(V, x0, x1, N = 1200) {
  const h = (x1 - x0) / N, out = [];
  for (let i = 0; i < N; i++) {
    let v = V(x0 + (i + 0.5) * h); if (!Number.isFinite(v)) v = 1e6;
    const last = out[out.length - 1];
    if (last && Math.abs(last.V - v) <= 1e-12 * Math.max(1, Math.abs(v))) last.b = x0 + (i + 1) * h; else out.push({a: x0 + i * h, b: x0 + (i + 1) * h, V: v});
  }
  return out;
}
/** a scattering state at energy E coming from the left: T, R and ψ(x) on the grid (complex), for V on [x0, x1] and
 *  V(x0), V(x1) continued outside */
export function scatterState(V, x0, x1, E, {mass = 1, N = 1200, samples = 400} = {}) {
  const C = HBAR2_2ME / mass, slabs = potentialSlabs(V, x0, x1, N), VL = slabs[0].V, VR = slabs[slabs.length - 1].V;
  if (!(E > VL)) return {T: 0, R: 1, kL: 0, kR: 0, xs: [], psi: [], ok: false};
  const kL = Math.sqrt((E - VL) / C), open = E > VR, kR = open ? Math.sqrt((E - VR) / C) : Math.sqrt((VR - E) / C);
  /* (ψ, ψ') at x1: outgoing e^{ik x}, or decaying e^{−κ x} */
  let psi = [1, 0], dpsi = open ? [0, kR] : [-kR, 0];
  const pts = [];
  const sampleAt = new Float64Array(samples + 1); for (let i = 0; i <= samples; i++) sampleAt[i] = x0 + (x1 - x0) * i / samples;
  let si = samples;
  pts[si] = {x: x1, re: psi[0], im: psi[1]};
  for (let j = slabs.length - 1; j >= 0; j--) {
    const sl = slabs[j], q = (E - sl.V) / C;
    /* inside the slab: the sample points, from its right end */
    while (si - 1 >= 0 && sampleAt[si - 1] >= sl.a - 1e-12) {
      si--; const M = slabMatrix(q, sampleAt[si] - sl.b);
      pts[si] = {x: sampleAt[si], re: M[0] * psi[0] + M[1] * dpsi[0], im: M[0] * psi[1] + M[1] * dpsi[1]};
    }
    const M = slabMatrix(q, sl.a - sl.b);
    const p2 = cx.add(cx.scale(psi, M[0]), cx.scale(dpsi, M[1])), d2 = cx.add(cx.scale(psi, M[2]), cx.scale(dpsi, M[3]));
    psi = p2; dpsi = d2;
  }
  /* at x0: ψ = A e^{ik x0} + B e^{−ik x0}, ψ' = ik(A e^{ik x0} − B e^{−ik x0}) (phases taken at x0) */
  const ik = [0, kL], A = cx.scale(cx.add(psi, cx.div(dpsi, ik)), 0.5), B = cx.scale(cx.add(psi, cx.scale(cx.div(dpsi, ik), -1)), 0.5);
  const a2 = cx.abs2(A), T = open ? (kR / kL) / a2 : 0, R = cx.abs2(B) / a2;
  const norm = 1 / Math.sqrt(a2);
  const phase = cx.div([1, 0], A);   /* ψ / A: incident amplitude 1 */
  const psiOut = pts.map(p => { const z = cx.mul([p.re, p.im], phase); return {x: p.x, re: z[0], im: z[1]}; });
  return {T, R, kL, kR, ok: true, open, xs: psiOut.map(p => p.x), psi: psiOut, norm};
}
/** T(E) over (Elo, Ehi] at n energies */
export function transmissionCurve(V, x0, x1, Ehi, {mass = 1, n = 160, N = 800} = {}) {
  const out = [];
  for (let i = 1; i <= n; i++) { const E = Ehi * i / n, r = scatterState(V, x0, x1, E, {mass, N, samples: 2}); out.push({E, T: r.T}); }
  return out;
}
/** everything a qpot object draws: V on its range, the bound states below both ends' V, a scattering state at E, T(E) */
export function qpotModel(o, {N = 500} = {}) {
  const V = boundExpr(o.V, o.params);
  if (!V) return {ok: false};
  const x0 = Math.min(o.xmin, o.xmax), x1 = Math.max(o.xmin, o.xmax);
  if (!(x1 - x0 > 1e-9)) return {ok: false};
  const vs = []; for (let i = 0; i <= 400; i++) { const x = x0 + (x1 - x0) * i / 400, v = V(x); vs.push({x, V: Number.isFinite(v) ? v : NaN}); }
  const finite = vs.filter(p => Number.isFinite(p.V)), Vmin = Math.min(...finite.map(p => p.V)), Vmax = Math.max(...finite.map(p => p.V));
  const edge = Math.min(Number.isFinite(V(x0)) ? V(x0) : Infinity, Number.isFinite(V(x1)) ? V(x1) : Infinity);
  /* bound: below what both ends reach (a state above it is only held by the box's walls) */
  const states = o.levels > 0 ? boundStates(V, x0, x1, {mass: o.mass, N, count: o.levels}).map(s => ({...s, bound: s.E < edge - 1e-9})) : [];
  const scatter = o.E > 0 ? scatterState(V, x0, x1, o.E, {mass: o.mass, samples: 400}) : null;
  const shown = states.filter(s => s.bound);
  const Etop = Math.max(Vmax > Vmin ? Vmax : Vmin + 1, ...shown.map(s => s.E), o.E || 0);
  const Emax = o.Emax > 0 ? o.Emax : Etop + 0.25 * (Etop - Math.min(0, Vmin));
  const curve = o.tplot ? transmissionCurve(V, x0, x1, Emax, {mass: o.mass}) : null;
  return {ok: true, V, x0, x1, vs, Vmin: Math.min(0, Vmin), Vmax, Emax, states, scatter, curve, edge};
}

/** energy levels (eV): hydrogen E_n = −13.6057/n², or the custom list; transitions "a-b" with λ = hc/|ΔE| */
export function levelModel(o) {
  const E = o.kind === 'hydrogen' ? Array.from({length: o.n}, (_, i) => ({n: i + 1, E: -13.605693 / (i + 1) ** 2})) : String(o.values).split(/[,;\s]+/).map(Number).filter(Number.isFinite).slice(0, 12).sort((a, b) => a - b).map((e, i) => ({n: i + 1, E: e}));
  const trans = String(o.trans).split(/[,;\s]+/).map(s => /^(\d+)\s*[-→>]+\s*(\d+)$/.exec(s)).filter(Boolean).map(m => ({from: +m[1], to: +m[2]})).filter(t => t.from !== t.to && E[t.from - 1] && E[t.to - 1])
    .map(t => { const dE = E[t.from - 1].E - E[t.to - 1].E; return {...t, dE, lambda: HC_EV_NM / Math.abs(dE)}; });
  return {levels: E, trans};
}
/** special relativity: γ, and the events of a clock's ticks on its worldline (x0 + β ct, every τ of proper time) */
/* ── a function's features, found numerically (a graphing calculator's: roots, extrema, the tangent, the area) ── */
/** f'(x) by a central difference */
export function derivative(fn, x, h = 1e-5 * Math.max(1, Math.abs(x))) { return (fn(x + h) - fn(x - h)) / (2 * h); }
/** ∫ f from a to b by Simpson's rule (n even); the parts where f is not finite count as 0 */
export function integrate(fn, a, b, n = 600) {
  const h = (b - a) / n, F = x => { const y = fn(x); return Number.isFinite(y) ? y : 0; };
  let s = F(a) + F(b);
  for (let i = 1; i < n; i++) s += F(a + i * h) * (i % 2 ? 4 : 2);
  return s * h / 3;
}
/** the roots and the local extrema of f on [x0, x1]: sign changes on n samples, refined by bisection (an extremum is a
 *  root of f′ where f′ changes sign; a jump of f, like tan's, is not counted) → {roots: [x], extrema: [{x, y, kind}]} */
export function funcFeatures(fn, x0, x1, n = 800) {
  const roots = [], extrema = [];
  if (!fn || !(x1 > x0)) return {roots, extrema};
  const xs = [], ys = [];
  for (let i = 0; i <= n; i++) { const x = x0 + (x1 - x0) * i / n; xs.push(x); ys.push(fn(x)); }
  const span = Math.max(1e-9, ...ys.filter(Number.isFinite).map(Math.abs));
  const bisect = (g, a, b) => { let ga = g(a); for (let k = 0; k < 60; k++) { const m = (a + b) / 2, gm = g(m); if (!Number.isFinite(gm)) return null; if ((gm > 0) === (ga > 0)) { a = m; ga = gm; } else b = m; } return (a + b) / 2; };
  for (let i = 0; i < n; i++) {
    const a = ys[i], b = ys[i + 1]; if (!Number.isFinite(a) || !Number.isFinite(b)) continue;
    if (a === 0) { roots.push(xs[i]); continue; }
    if (a * b < 0 && Math.abs(a - b) < 0.5 * span) { const r = bisect(fn, xs[i], xs[i + 1]); if (r != null) roots.push(r); }
  }
  if (ys[n] === 0) roots.push(xs[n]);
  const h = (x1 - x0) / n, d = x => derivative(fn, x, h * 1e-3);
  for (let i = 1; i < n; i++) {
    const a = ys[i - 1], b = ys[i], c = ys[i + 1]; if (![a, b, c].every(Number.isFinite)) continue;
    if ((b - a) * (c - b) < 0 && Math.abs(c - a) < 0.5 * span) {
      const x = bisect(d, xs[i - 1], xs[i + 1]); if (x == null) continue;
      const y = fn(x); if (Number.isFinite(y)) extrema.push({x, y, kind: b > a ? 'max' : 'min'});
    }
  }
  const uniq = list => list.filter((v, i) => !i || Math.abs((v.x ?? v) - (list[i - 1].x ?? list[i - 1])) > h * 0.5);
  return {roots: uniq(roots), extrema: uniq(extrema)};
}

export const lorentzGamma = beta => 1 / Math.sqrt(1 - beta * beta);
export const clockTicks = (o, max) => { const g = lorentzGamma(o.beta), out = []; for (let k = 1; g * k * o.tau <= max + 1e-9 && k < 200; k++) out.push({ct: g * k * o.tau, x: o.x0 + o.beta * g * k * o.tau, k}); return out; };

/* ── rails and a sliding rod: ε = B L v, I = ε / R, the magnetic force on the rod F = B I L (against v), P = ε I ── */
export function motionalEMF(o) { const emf = o.B * o.h * o.v, I = o.R > 0 ? emf / o.R : 0; return {emf, I, F: o.B * Math.abs(I) * o.h, P: emf * I}; }
/* ── fluids: buoyancy ρ g V_sub; a body of density ρ_b floats with the fraction ρ_b / ρ_f under the surface ── */
export const buoyancy = (rho, Vsub, g = 9.8) => rho * g * Vsub;
export const floatFraction = (rhoBody, rhoFluid) => Math.min(1, rhoBody / rhoFluid);
/** the liquid's surface height in a container, and each block standing in it: the submerged volume (a block's depth
 *  into the page is taken equal to its width), the buoyant force and the fraction it would float with */
export function containerInfo(scene, c, g = scene.g || 9.8) {
  const top = c.y + c.h * c.level, out = [];
  for (const b of scene.objects.filter(o => o.type === 'block' || o.type === 'ball')) {
    const p = bodyPose(scene, b), hw = bodyHalfWidth(b), hh = bodyHalfHeight(b);
    if (p.x - hw < c.x - 1e-9 || p.x + hw > c.x + c.w + 1e-9 || p.y - hh > top || p.y + hh < c.y) continue;
    const sub = Math.max(0, Math.min(2 * hh, top - (p.y - hh)));
    const V = b.type === 'ball' ? sphereCap(b.r, sub) : b.w * sub * b.w, Vb = b.type === 'ball' ? 4 / 3 * Math.PI * b.r ** 3 : b.w * b.h * b.w;
    out.push({id: b.id, Vsub: V, B: buoyancy(c.rho, V, g), weight: b.mass * g, rhoB: b.mass / Vb, floats: floatFraction(b.mass / Vb, c.rho)});
  }
  return {surface: top, bodies: out};
}
const sphereCap = (r, h) => Math.PI * h * h * (3 * r - h) / 3;
/** a wheel rolling without slipping down a slope θ: a = g sin θ / (1 + I / m r²) */
export const rollingAccel = (g, thetaDeg, k) => g * Math.sin(thetaDeg * Math.PI / 180) / (1 + k);

/** what the side panel shows for the figure's computed objects: [{id, type, ...values}] */
export function computedInfo(scene) {
  const out = [];
  for (const o of scene.objects) {
    if (o.type === 'rails') { const m = motionalEMF(o); out.push({id: o.id, type: o.type, emf: m.emf, I: m.I, F: m.F}); }
    else if (o.type === 'container') { const c = containerInfo(scene, o); for (const b of c.bodies) out.push({id: b.id, type: 'buoyancy', B: b.B, W: b.weight, floats: b.floats}); }
    else if (o.type === 'bridge' && o.kind === 'meter') out.push({id: o.id, type: o.type, l: o.at * 100});
    if (o.type === 'cycle') { const c = gasCycle(o); out.push({id: o.id, type: o.type, W: c.W, Qin: c.Qin, eta: c.eta, carnot: 1 - c.Tc / c.Th}); }
    else if (o.type === 'oarrow') { const im = opticImage(scene, o); if (im) out.push({id: o.id, type: o.type, x: im.x, h: im.h, m: im.m, real: im.real}); }
    else if (o.type === 'slits') out.push({id: o.id, type: o.type, dy: fringeSpacing(o), n: o.n});
    else if (o.type === 'well') { const w = wellModel(o); out.push({id: o.id, type: o.type, E: w.levels.map(l => l.E), T: w.T}); }
    else if (o.type === 'qpot') { const q = qpotModel(o); if (q.ok) out.push({id: o.id, type: o.type, E: q.states.filter(x => x.bound).map(x => x.E), T: q.scatter?.ok ? q.scatter.T : undefined}); }
    else if (o.type === 'levels') out.push({id: o.id, type: o.type, trans: levelModel(o).trans});
    else if (o.type === 'spacetime') out.push({id: o.id, type: o.type, gamma: lorentzGamma(o.beta)});
    else if (o.type === 'curve' && o.kind !== 'func' && o.kind !== 'isochore') out.push({id: o.id, type: o.type, W: processWork(o.kind, o)});
  }
  return out;
}
