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
import {isBody, surfaceFrame, bodyPose, attachPoint, anchorPoint, stringPath, bodyHalfHeight, bodyHalfWidth, vec} from './draw-scene.mjs?v=821b2b258cf0';

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

  /* ── chains: a string between two bodies ── */
  for (const s of strings) {
    if (s.type !== 'string') continue;
    const A = byId.get(s.a), B = byId.get(s.b);
    if (!isBody(A) || !isBody(B)) continue;
    const path = stringPath(scene, s);
    const ends = [[A, path.a, path.segs[0][1], -1], [B, path.b, path.segs[path.segs.length - 1][0], 1]].map(([b, att, next, eps]) => {
      const pose = bodyPose(scene, b), out = vec.unit(vec.sub(att, next));
      let d, frame = null;
      if (b.on) { frame = surfaceFrame(byId.get(b.on)); const sigma = sgn(vec.dot(out, frame.u)) || 1; d = vec.mul(frame.u, eps * sigma); }
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
      systems.push({kind: 'conical', id: s.id, ids: [b.id], q: Float64Array.from([0]), t: 0, mode: 0, done: null, omega: w, radius: R, centre: {x: P.x, y: P.y - L * Math.cos(alpha)}, side,
        prepare() {}, f() { return Float64Array.from([w]); }, events() { return []; },
        poses(q = this.q) { return new Map([[b.id, {x: P.x + side * R * Math.cos(q[0]), y: P.y - L * Math.cos(alpha), z: R * Math.sin(q[0]), angle: 0}]]); },
        velocities(q = this.q) { return new Map([[b.id, {x: -side * R * w * Math.sin(q[0]), y: 0, z: R * w * Math.cos(q[0])}]]); },
        accel(q = this.q) { return new Map([[b.id, {x: -side * R * w * w * Math.cos(q[0]), y: 0}]]); },
        tensions() { return {[s.id]: m * g / Math.cos(alpha)}; },
        forceList(q = this.q) { const p = this.poses(q).get(b.id), T = m * g / Math.cos(alpha), u = vec.unit(vec.sub(P, p));
          return new Map([[b.id, [{kind: 'gravity', v: vec.mul(G, m)}, {kind: 'tension', v: vec.mul(u, T)}].map(x => ({...x, at: {x: p.x, y: p.y}}))]]); },
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
    const items = list.map(b => { const fr = surfaceFrame(byId.get(b.on)); return {b, id: b.id, m: b.mass, fr, mu: fr.mu, angle: Math.atan2(fr.u.y, fr.u.x)}; });
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
        items.forEach((it, i) => { const v = qq[2 * i + 1]; out[2 * i] = v; out[2 * i + 1] = modes[i] === 0 && Math.abs(v) <= EPS_V ? 0 : r[i].a;
          out[2 * n] += -r[i].f * v * (modes[i] === 0 ? 0 : 1); out[2 * n + 1] += vec.dot(applied(it.id), vec.mul(it.fr.u, v)); });
        return out;
      },
      events(qq) {
        const r = this.eval(qq), out = [];
        items.forEach((it, i) => { const at = qq[2 * i], hw = bodyHalfWidth(it.b);
          out.push({code: 'end_of_surface', id: it.id, g: at - hw}, {code: 'end_of_surface', id: it.id, g: it.fr.length - at - hw}, {code: 'lift_off', id: it.id, g: r[i].N});
          if (it.mu > 0 && modes[i] !== 0) out.push({code: 'stick', i, g: modes[i] * qq[2 * i + 1], stop: false});
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
      energy(qq = this.q) { const p = posesAt(qq);
        return {K: items.reduce((k, it, i) => k + 0.5 * it.m * qq[2 * i + 1] ** 2, 0), Ug: items.reduce((u, it) => u + it.m * g * p.get(it.id).y, 0), Us: springEnergy(id => p.get(id)), heat: qq[2 * n], work: qq[2 * n + 1]}; }
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
    s.prepare();
    const f = q => s.f(q), q0 = s.q, q1 = rk4(f, q0, h);
    const before = s.events(q0), after = s.events(q1);
    let first = null, tau = 1;
    after.forEach((e, i) => {
      const g0 = before[i] ? before[i].g : NaN;
      if (!(g0 > 0 && e.g <= 0)) return;
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

  const sim = {
    scene, systems, unsupported, dt, t: 0,
    get done() { return systems.length > 0 && systems.every(s => s.done); },
    get events() { return systems.filter(s => s.done).map(s => s.done); },
    /* move every system on to time T */
    advanceTo(T) {
      for (const s of systems) {
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
        return p.at !== undefined ? {...o, at: p.at, x: p.x, y: p.y} : {...o, x: p.x, y: p.y, on: ''};
      })};
      return out;
    }
  };
  return sim;
}
