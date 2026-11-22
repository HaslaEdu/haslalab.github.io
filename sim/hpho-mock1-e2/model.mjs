// Photoelasticity bench for HPhO mock-1 E2. Pure functions and a small lab object; no DOM, no network.
// Units inside: lengths in mm unless named *_m, forces in N, stress fringe value fs in N/m.

export const G = 9.81;
export const LAMBDA = 546e-9;
export const NOMINAL = {t: 6.00, b1: 20.0, h: 25.0, b2: 30.0, d: 6.0};
export const PIECES = {50: 4, 100: 4, 500: 6};

export class Rng {
  constructor(seed) { this.s = seed >>> 0; }
  next() {
    this.s = (this.s + 0x6D2B79F5) >>> 0;
    let t = this.s;
    t = Math.imul(t ^ t >>> 15, t | 1);
    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  }
  uni(a, b) { return a + (b - a) * this.next(); }
  gauss() { let u = 0; while (u === 0) u = this.next(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * this.next()); }
}

// Hidden instrument parameters. defaultParams() is the centre of every range.
export function defaultParams() {
  return {v: 1, fs: 200, tT: 6.00, tB: 6.00, tH: 6.00, b1: 20.0, h: 25.0, b2: 30.0, d: 6.0,
    beamLen: 140.0, Lb: 130.0, E: 4.2e6, nu: 0.48, rho: 1100, hanger: 50.6, loop: 2.0,
    m50: 50.0, m100: 100.0, m500: 500.0, N0T: 0.14, N0H: 0.08, NaxB: 0.0, delta0: 0.5,
    Kt: 3.14, kappa: 0.025, tauC: 60, sMin: 0.095, rim: 0.045, rough: 0.07, noiseSeed: 12345};
}
export function drawParams(seed) {
  const r = new Rng(seed), u = (a, b) => r.uni(a, b);
  return {v: 1, fs: 200 * u(0.92, 1.08), tT: 6.00 + u(-0.04, 0.04), tB: 6.00 + u(-0.04, 0.04), tH: 6.00 + u(-0.04, 0.04),
    b1: 20.0 + u(-0.08, 0.08), h: 25.0 + u(-0.08, 0.08), b2: 30.0 + u(-0.08, 0.08), d: 6.0 + u(-0.05, 0.05),
    beamLen: 140 + u(-1, 1), Lb: 130 + u(-1, 1), E: u(3.5e6, 5.0e6), nu: 0.48, rho: u(1080, 1120),
    hanger: 50 + u(-0.8, 1.5), loop: u(1.5, 2.5), m50: 50 * (1 + u(-0.004, 0.004)), m100: 100 * (1 + u(-0.003, 0.003)), m500: 500 * (1 + u(-0.002, 0.002)),
    N0T: u(0.08, 0.20), N0H: u(0.03, 0.12), NaxB: u(-0.06, 0.06), delta0: u(-0.8, 0.8),
    Kt: 3.14 * u(0.985, 1.015), kappa: u(0.015, 0.035), tauC: u(40, 90), sMin: u(0.08, 0.11), rim: u(0.03, 0.06), rough: u(0.05, 0.09),
    noiseSeed: (seed * 2654435761) >>> 0};
}

// Fixed pattern noise for the rough machined hole surface (same every time at the same place).
function vnoise(seed, u) {
  const h = i => { let x = Math.imul((i | 0) ^ seed, 0x45d9f3b); x ^= x >>> 16; x = Math.imul(x, 0x45d9f3b); x ^= x >>> 16; return (x >>> 0) / 4294967296 * 2 - 1; };
  const i = Math.floor(u), f = u - i, s = f * f * (3 - 2 * f);
  return h(i) * (1 - s) + h(i + 1) * s;
}

export function weightSet(grams) {
  if (!Number.isFinite(grams) || grams < 0 || Math.round(grams) % 50 !== 0) return null;
  let g = Math.round(grams); const n = {500: 0, 100: 0, 50: 0};
  for (const p of [500, 100, 50]) { n[p] = Math.min(PIECES[p], Math.floor(g / p)); g -= n[p] * p; }
  return g === 0 ? n : null;
}
const pieceMass = (P, n) => n[500] * P.m500 + n[100] * P.m100 + n[50] * P.m50;

export function initialState(seed) {
  return {v: 1, rng: (seed ^ 0x9e3779b9) >>> 0, clock: 9 * 3600, spec: 'none', qwp: false, analyzer: 0, rotate: 0,
    hanger: false, weights: 0, creep: 0, watch: null, nextId: 1, records: [], pendingReset: false};
}

// Applied force (N) on the specimen from the hanging masses.
export function appliedForce(P, S) {
  if (S.spec === 'none') return 0;
  const n = weightSet(S.weights) || {500: 0, 100: 0, 50: 0};
  let m = pieceMass(P, n);
  if (S.hanger) m += P.hanger; else if (S.spec === 'beam' && S.weights > 0) m += P.loop;
  return m / 1000 * G;
}

// Kirsch perturbation (stress / remote stress) around a hole of radius a, load along x.
function kirschPert(x, y, a) {
  const r2 = x * x + y * y, th = Math.atan2(y, x), c2 = Math.cos(2 * th), s2 = Math.sin(2 * th);
  const q = a * a / r2, q2 = q * q;
  const srr = 0.5 * (1 - q) + 0.5 * (1 - 4 * q + 3 * q2) * c2 - 0.5 * (1 + c2);
  const stt = 0.5 * (1 + q) - 0.5 * (1 + 3 * q2) * c2 - 0.5 * (1 - c2);
  const srt = -0.5 * (1 + 2 * q - 3 * q2) * s2 + 0.5 * s2;
  const c = Math.cos(th), s = Math.sin(th);
  return {xx: srr * c * c + stt * s * s - 2 * srt * s * c, yy: srr * s * s + stt * c * c + 2 * srt * s * c, xy: (srr - stt) * s * c + srt * (c * c - s * s)};
}

// Horizontal shortening of the deflected cantilever between 0 and x (mm), tip load W (N) at Lb.
function shortening(P, W, x) {
  const L = P.Lb / 1000, X = Math.min(x, P.Lb) / 1000, I = P.tB / 1000 * (P.h / 1000) ** 3 / 12, k = W / (2 * P.E * I);
  const F = s => 4 * L * L * s ** 3 / 3 - L * s ** 4 + s ** 5 / 5;
  return 0.5 * k * k * F(X) * 1000;
}

// Fringe-order tensor at a point. Returns {kind, N, phi} with phi the principal direction relative to the specimen axis.
export function field(P, S, x, y, Feff = appliedForce(P, S) + S.creep) {
  const sp = S.spec;
  if (sp === 'none') return {kind: 'out'};
  let nxx = 0, nyy = 0, nxy = 0, extra = 0, kind = 'mat';
  if (sp === 'tension' || sp === 'hole') {
    const b = sp === 'tension' ? P.b1 : P.b2, t = sp === 'tension' ? P.tT : P.tH;
    if (Math.abs(y) > b / 2 || Math.abs(x) > 75) return {kind: 'out'};
    const sig = Feff / (b * t * 1e-6), Ninf = Feff / (b / 1000 * P.fs) * (1 + P.nu * sig / P.E);
    const grip = Math.exp(-(75 - Math.abs(x)) / 4), yy = y / (b / 2);
    let sxx = 1 + grip * 0.6 * (1 + 0.5 * Math.cos(Math.PI * yy)), syy = grip * 0.15, sxy = grip * 0.25 * yy * Math.sign(x);
    if (sp === 'hole') {
      const a = P.d / 2, r = Math.hypot(x, y);
      if (r < a) return {kind: 'hole'};
      if (r - a < P.rim) return {kind: 'rim'};
      const c = (P.Kt - 1) / 2, p = kirschPert(x, y, a);
      sxx += c * p.xx; syy += c * p.yy; sxy += c * p.xy;
      if (r - a < P.rim + P.rough) { kind = 'rough'; extra = 0.2 * vnoise(P.noiseSeed, Math.atan2(y, x) * 40 + (r - a) * 30) * (1 + Ninf / 6); }
    }
    const N0 = sp === 'tension' ? P.N0T : P.N0H, edge = 0.3 * Math.exp(-(b / 2 - Math.abs(y)) / 0.25);
    nxx = Ninf * sxx + N0 + edge; nyy = Ninf * syy; nxy = Ninf * sxy;
  } else if (sp === 'beam') {
    if (x < 0 || x > P.beamLen || y < 0 || y > P.h) return {kind: 'out'};
    const arm = Math.max(0, (P.Lb - x) - (shortening(P, Feff, P.Lb) - shortening(P, Feff, x))) / 1000;
    const q = P.rho * G * (P.tB / 1000) * (P.h / 1000), M = (x < P.Lb ? Feff * arm : 0) + q * ((P.beamLen - x) / 1000) ** 2 / 2;
    const clamp = 1 + 0.25 * Math.exp(-x / 5), h = P.h / 1000;
    nxx = 12 * M * ((y - P.h / 2) / 1000) / (h ** 3 * P.fs) * clamp + P.NaxB;
    nxy = 0.08 * M / (h * h * P.fs) * Math.exp(-x / 4) * (1 - (2 * y / P.h - 1) ** 2);
  }
  const dn = nxx - nyy, N = Math.hypot(dn, 2 * nxy) + extra;
  return {kind, N: Math.abs(N), phi: 0.5 * Math.atan2(2 * nxy, dn)};
}

// Jones calculus: polarizer at 0, optional QWP at 45, specimen retarder, optional QWP at analyzer+45, analyzer.
function retard(E, th, G2) {
  const c = Math.cos(th), s = Math.sin(th);
  const a = [c * E[0][0] + s * E[1][0], c * E[0][1] + s * E[1][1]], b = [-s * E[0][0] + c * E[1][0], -s * E[0][1] + c * E[1][1]];
  const ca = Math.cos(-G2 / 2), sa = Math.sin(-G2 / 2), cb = Math.cos(G2 / 2), sb = Math.sin(G2 / 2);
  const a2 = [a[0] * ca - a[1] * sa, a[0] * sa + a[1] * ca], b2 = [b[0] * cb - b[1] * sb, b[0] * sb + b[1] * cb];
  return [[c * a2[0] - s * b2[0], c * a2[1] - s * b2[1]], [s * a2[0] + c * b2[0], s * a2[1] + c * b2[1]]];
}
export function intensity(P, S, f) {
  const beta = (S.analyzer - P.delta0) * Math.PI / 180;
  let E = [[1, 0], [0, 0]];
  if (f.kind === 'rim') return 0.02;
  if (S.qwp) E = retard(E, Math.PI / 4, Math.PI / 2);
  if (f.kind === 'mat' || f.kind === 'rough') E = retard(E, f.phi + S.rotate * Math.PI / 180, 2 * Math.PI * f.N);
  if (S.qwp) E = retard(E, beta + Math.PI / 4, Math.PI / 2);
  const re = E[0][0] * Math.cos(beta) + E[1][0] * Math.sin(beta), im = E[0][1] * Math.cos(beta) + E[1][1] * Math.sin(beta);
  return Math.min(1, 0.001 + 0.999 * (re * re + im * im));
}

// Specimen geometry for lines and labels.
export function extent(P, sp) {
  if (sp === 'tension') return {x: [-75, 75], y: [-P.b1 / 2, P.b1 / 2]};
  if (sp === 'hole') return {x: [-75, 75], y: [-P.b2 / 2, P.b2 / 2]};
  if (sp === 'beam') return {x: [0, P.beamLen], y: [0, P.h]};
  return null;
}

// Dark fringes along a line, as an observer sees them: local minima of brightness that are dark enough,
// merged when closer than the eye can separate, and lost when they sit inside the dark rim of the hole.
export function darkFringes(P, S, axis, value, from, to) {
  const len = Math.abs(to - from), n = Math.max(200, Math.min(20000, Math.ceil(len / 0.002))), ds = (to - from) / n;
  const I = [], pos = [];
  for (let i = 0; i <= n; i++) {
    const s = from + i * ds, f = axis === 'x' ? field(P, S, value, s) : field(P, S, s, value);
    pos.push(s); I.push(f.kind === 'mat' || f.kind === 'rough' ? intensity(P, S, f) : null);
  }
  const out = [];
  let i = 0;
  while (i <= n) {
    if (I[i] === null) { i++; continue; }
    let j = i; while (j + 1 <= n && I[j + 1] !== null) j++;
    // segment [i, j]; ends next to a hole/rim are dark boundaries
    const darkLo = i > 0 && I[i - 1] === null, darkHi = j < n && I[j + 1] === null;
    const mins = [];
    for (let k = i + 1; k < j; k++) if (I[k] < I[k - 1] && I[k] <= I[k + 1] && I[k] < 0.06) mins.push(k);
    // merge minima that the eye cannot separate (closer than sMin or without bright gap between)
    const groups = [];
    for (const k of mins) {
      const g = groups.at(-1);
      if (g) {
        let peak = 0; for (let m = g.at(-1); m <= k; m++) peak = Math.max(peak, I[m]);
        if (Math.abs(pos[k] - pos[g.at(-1)]) < P.sMin || peak < 0.25) { g.push(k); continue; }
      }
      groups.push([k]);
    }
    for (const g of groups) {
      const c = pos[g[0]] + (pos[g.at(-1)] - pos[g[0]]) / 2;
      if (darkLo && Math.abs(c - pos[i]) < P.sMin / 2) continue;
      if (darkHi && Math.abs(pos[j] - c) < P.sMin / 2) continue;
      let a = g[0], b = g.at(-1);
      while (a > i && I[a - 1] < 0.1) a--;
      while (b < j && I[b + 1] < 0.1) b++;
      out.push({pos: c, width: Math.abs(pos[b] - pos[a]) + Math.abs(ds), merged: g.length});
    }
    i = j + 1;
  }
  return out;
}

// Local fringe gradient (orders per mm) for legibility checks.
function gradN(P, S, x, y) {
  const e = 0.01, f0 = field(P, S, x, y);
  if (f0.kind !== 'mat' && f0.kind !== 'rough') return 0;
  const fx = field(P, S, x + e, y), fy = field(P, S, x, y + e);
  const gx = fx.N === undefined ? 0 : (fx.N - f0.N) / e, gy = fy.N === undefined ? 0 : (fy.N - f0.N) / e;
  return Math.hypot(gx, gy);
}

const pad = (v, n) => String(v).padStart(n);
const fmt = (v, d) => (Math.round(v * 10 ** d) / 10 ** d).toFixed(d);
const clockText = s => { s = Math.round(s); const h = Math.floor(s / 3600) % 24, m = Math.floor(s / 60) % 60, x = s % 60; return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(x).padStart(2, '0')}`; };
export {clockText};

const SPEC_NAMES = {ko: {none: '없음', tension: '인장 시편', beam: '굽힘 보', hole: '천공 시편'}, en: {none: 'none', tension: 'tension specimen', beam: 'bending beam', hole: 'specimen with hole'}};

export const HELP = {
  ko: [
    ['status', '현재 장치 상태와 시각', 'status'],
    ['analyzer <deg>', '두 번째 편광판(검광판)을 각도기 눈금 <deg>에 맞춘다', 'analyzer 85'],
    ['qwp on|off', '1/4 파장판 두 장을 45°로 넣거나 뺀다', 'qwp on'],
    ['mount none|tension|beam|hole', '시편을 바꿔 단다 (beam은 클램프에 물린 외팔보)', 'mount tension'],
    ['rotate <deg>', '편광계에 대해 시편을 면 안에서 돌린다', 'rotate 45'],
    ['hanger on|off', '추걸이를 건다 / 뗀다 (beam은 실 고리로도 걸 수 있다)', 'hanger on'],
    ['load <g>', '걸린 추의 합을 <g>로 바꾼다 (추걸이 제외, 천천히 하나씩)', 'load 1450'],
    ['look', '시편 전체를 보고 몇 곳의 밝기를 적는다', 'look'],
    ['read <x> <y>', '한 점의 밝기를 눈으로 읽는다 (mm)', 'read 0 0'],
    ['watch <x> <y> | off', '점에 표시하고, 하중이 바뀔 때 지나가는 줄을 센다', 'watch 0 0'],
    ['fringes x|y <값> [from to]', '선 위의 어두운 줄 위치를 캘리퍼스로 잰다', 'fringes x 70'],
    ['measure t|width|hole|arm|length', '자 또는 버니어 캘리퍼스로 치수를 잰다', 'measure width'],
    ['wait <n> [s|min]', '시각을 n만큼 넘긴다', 'wait 2 min'],
    ['log', '측정 기록 (최근 20개)', 'log'],
    ['csv', '측정 기록 전체를 CSV로 받는다', 'csv'],
    ['reset', '새 장치를 받는다 (확인 필요, 기록 삭제)', 'reset'],
    ['exit', '장치 프로그램을 끝낸다', 'exit'],
  ],
  en: [
    ['status', 'current set-up and clock', 'status'],
    ['analyzer <deg>', 'set the second polarizer (analyzer) to protractor reading <deg>', 'analyzer 85'],
    ['qwp on|off', 'insert or remove the two quarter-wave plates at 45°', 'qwp on'],
    ['mount none|tension|beam|hole', 'change the specimen (beam is clamped as a cantilever)', 'mount tension'],
    ['rotate <deg>', 'rotate the specimen in its plane relative to the polariscope', 'rotate 45'],
    ['hanger on|off', 'attach or remove the mass hanger (the beam can also take a thread loop)', 'hanger on'],
    ['load <g>', 'change the masses hung to <g> in total (hanger excluded, added one by one)', 'load 1450'],
    ['look', 'look at the whole specimen and note the brightness at a few places', 'look'],
    ['read <x> <y>', 'read the brightness at one point by eye (mm)', 'read 0 0'],
    ['watch <x> <y> | off', 'mark a point and count the fringes passing it as the load changes', 'watch 0 0'],
    ['fringes x|y <value> [from to]', 'measure the dark-fringe positions along a line with the caliper', 'fringes x 70'],
    ['measure t|width|hole|arm|length', 'measure a dimension with the ruler or vernier caliper', 'measure width'],
    ['wait <n> [s|min]', 'advance the clock by n', 'wait 2 min'],
    ['log', 'measurement records (last 20)', 'log'],
    ['csv', 'download all records as CSV', 'csv'],
    ['reset', 'get a new apparatus (asks for confirmation, deletes records)', 'reset'],
    ['exit', 'leave the apparatus program', 'exit'],
  ],
};

export const CSV_HEADER = 'id,time,specimen,polariscope,analyzer_deg,rotate_deg,hanger,weights_g,quantity,x_mm,y_mm,value,unit';

export class Lab {
  constructor(params, state, lang = 'ko') { this.P = params; this.S = state; this.lang = lang; }
  tr(ko, en) { return this.lang === 'en' ? en : ko; }
  rnd() { const r = new Rng(this.S.rng); const v = r.next(); this.S.rng = r.s; return v; }
  gauss() { const r = new Rng(this.S.rng); const v = r.gauss(); this.S.rng = r.s; return v; }
  eye(I) { return Math.max(0, Math.min(100, Math.round(100 * I + this.gauss() * (0.4 + 3 * I)))); }
  specName(sp = this.S.spec) { return SPEC_NAMES[this.lang][sp]; }
  record(quantity, value, unit, x = '', y = '') {
    const S = this.S, rec = {id: S.nextId++, time: clockText(S.clock), specimen: S.spec, polariscope: S.qwp ? 'circular' : 'plane',
      analyzer_deg: S.analyzer, rotate_deg: S.rotate, hanger: S.hanger ? 'on' : 'off', weights_g: S.weights, quantity, x_mm: x, y_mm: y, value, unit};
    S.records.push(rec); return rec;
  }
  csv() { return CSV_HEADER + '\n' + this.S.records.map(r => CSV_HEADER.split(',').map(k => r[k]).join(',')).join('\n') + '\n'; }

  // N at the watch point for a given effective load.
  watchN(Feff) { const w = this.S.watch; const f = field(this.P, this.S, w.tx, w.ty, Feff); return f.N === undefined ? null : f.N; }
  // Count dark (integer) and bright (half-integer) crossings along the path Feff a -> b.
  countPath(a, b) {
    const w = this.S.watch; if (!w || a === b) return;
    let prev = this.watchN(a); if (prev === null) return;
    let dark = 0, bright = 0;
    for (let i = 1; i <= 64; i++) {
      const cur = this.watchN(a + (b - a) * i / 64);
      dark += Math.floor(cur) - Math.floor(prev); bright += Math.floor(cur + 0.5) - Math.floor(prev + 0.5); prev = cur;
    }
    w.dDark += dark; w.dBright += bright;
  }
  advance(dt) {
    const S = this.S, P = this.P, F = appliedForce(P, S), c0 = S.creep;
    S.creep = P.kappa * F + (c0 - P.kappa * F) * Math.exp(-dt / P.tauC);
    if (S.watch) this.countPath(F + c0, F + S.creep);
    S.clock += dt;
  }
  setLoad(mutator, dt) {
    const S = this.S, F0 = appliedForce(this.P, S) + S.creep;
    mutator();
    const F1 = appliedForce(this.P, S) + S.creep;
    if (S.watch) this.countPath(F0, F1);
    this.advance(dt);
  }
  watchReport(out) {
    const w = this.S.watch; if (!w || (w.dDark === 0 && w.dBright === 0)) return;
    if (w.rough && (w.dDark || w.dBright)) {
      if (this.rnd() < 0.45) w.dDark += this.rnd() < 0.5 ? -1 : 1;
      out.push(this.tr('  가공면 근처라 줄이 일그러져 세기 어려웠다.', '  The fringes are distorted near the machined surface and were hard to count.'));
    }
    w.dark += w.dDark; w.bright += w.dBright;
    out.push(this.tr(`watch (${w.x}, ${w.y}): 지나간 어두운 줄 ${w.dDark >= 0 ? '+' : ''}${w.dDark}, 밝은 줄 ${w.dBright >= 0 ? '+' : ''}${w.dBright} | 표시 뒤 누적 어두운 ${w.dark}, 밝은 ${w.bright}`,
      `watch (${w.x}, ${w.y}): dark fringes passed ${w.dDark >= 0 ? '+' : ''}${w.dDark}, bright ${w.dBright >= 0 ? '+' : ''}${w.dBright} | since marked: dark ${w.dark}, bright ${w.bright}`));
    this.record('watch_dark_total', w.dark, 'count', w.x, w.y); this.record('watch_bright_total', w.bright, 'count', w.x, w.y);
    w.dDark = 0; w.dBright = 0;
  }

  exec(line) {
    const out = [], S = this.S, P = this.P, tr = (k, e) => this.tr(k, e);
    const words = line.trim().split(/\s+/), cmd = (words[0] || '').toLowerCase(), args = words.slice(1);
    const num = v => { const n = Number(String(v).replace(',', '.')); return Number.isFinite(n) ? n : null; };
    const err = text => ({ok: false, text});
    if (cmd !== 'reset') S.pendingReset = false;
    switch (cmd) {
      case 'help': {
        const rows = HELP[this.lang], w = Math.max(...rows.map(r => r[0].length));
        if (args[0]) { const r = rows.find(r => r[0].split(' ')[0] === args[0]); if (!r) return err(tr(`없는 명령: ${args[0]}`, `No such command: ${args[0]}`)); return {ok: true, text: `${r[0]}\n  ${r[1]}\n  ${tr('예', 'e.g.')}: ${r[2]}`}; }
        return {ok: true, text: rows.map(r => r[0].padEnd(w + 2) + r[1]).join('\n') + '\n\n' + tr('예: mount tension, qwp on, analyzer 90, hanger on, watch 0 0, load 450, read 0 0\n좌표와 자세한 사용법: help <명령>', 'e.g. mount tension, qwp on, analyzer 90, hanger on, watch 0 0, load 450, read 0 0\nDetails: help <command>')};
      }
      case 'status': {
        const F = appliedForce(P, S);
        const rows = [
          [tr('시각', 'clock'), clockText(S.clock)],
          [tr('편광계', 'polariscope'), S.qwp ? tr('원편광 (1/4 파장판 있음)', 'circular (quarter-wave plates in)') : tr('선편광 (1/4 파장판 없음)', 'plane (no quarter-wave plates)')],
          [tr('검광판 눈금', 'analyzer reading'), `${S.analyzer}°`],
          [tr('시편', 'specimen'), this.specName()],
          [tr('시편 회전', 'specimen rotation'), `${S.rotate}°`],
          [tr('추걸이', 'hanger'), S.hanger ? tr('걸림 (각인 50 g)', 'on (stamped 50 g)') : tr('없음', 'off')],
          [tr('걸린 추', 'masses hung'), `${S.weights} g` + (S.weights ? ` (${this.pieceText(weightSet(S.weights))})` : '')],
          ['watch', S.watch ? `(${S.watch.x}, ${S.watch.y}) ${tr('누적 어두운', 'dark')} ${S.watch.dark}, ${tr('밝은', 'bright')} ${S.watch.bright}` : tr('없음', 'none')],
        ];
        void F;
        return {ok: true, text: rows.map(([a, b]) => `${a}: ${b}`).join('\n')};
      }
      case 'analyzer': {
        const a = num(args[0]); if (a === null || a < -180 || a > 360) return err(tr('사용법: analyzer <deg>  예: analyzer 90', 'Usage: analyzer <deg>  e.g. analyzer 90'));
        S.analyzer = Math.round(a * 2) / 2; this.advance(10);
        return {ok: true, text: tr(`검광판 눈금 ${S.analyzer}°`, `Analyzer at ${S.analyzer}°`)};
      }
      case 'qwp': {
        if (!['on', 'off'].includes(args[0])) return err(tr('사용법: qwp on|off', 'Usage: qwp on|off'));
        S.qwp = args[0] === 'on'; this.advance(30);
        return {ok: true, text: S.qwp ? tr('1/4 파장판 두 장을 넣었다 (각 편광판 축에 45°).', 'Both quarter-wave plates inserted at 45° to the polarizer axes.') : tr('1/4 파장판을 뺐다.', 'Quarter-wave plates removed.')};
      }
      case 'mount': {
        const sp = args[0]; if (!['none', 'tension', 'beam', 'hole'].includes(sp)) return err(tr('사용법: mount none|tension|beam|hole', 'Usage: mount none|tension|beam|hole'));
        if (S.weights > 0 || S.hanger) return err(tr('먼저 추와 추걸이를 내려라 (load 0, hanger off).', 'Remove the masses and the hanger first (load 0, hanger off).'));
        S.spec = sp; S.watch = null; S.creep = 0; S.rotate = 0; this.advance(sp === 'none' ? 30 : 120);
        const note = {
          none: tr('편광판 사이에 시편이 없다.', 'No specimen between the polarizers.'),
          tension: tr('인장 시편을 위 클램프에 물렸다. 좌표: x는 하중 축 (중심 0, 물림부 끝 x = ±75 mm), y는 폭 방향 (중심선 0).', 'Tension specimen hung from the upper clamp. Coordinates: x along the load axis (centre 0, grip ends at x = ±75 mm), y across the width (centre line 0).'),
          beam: tr('굽힘 보를 클램프에 물려 수평 외팔보로 만들었다. 좌표: x는 클램프 끝에서 잰 거리, y는 아래 모서리에서 잰 높이. 추는 자유단 근처 홈에 건다.', 'Bending beam clamped as a horizontal cantilever. Coordinates: x from the clamp edge, y up from the lower edge. Masses hang from the notch near the free end.'),
          hole: tr('천공 시편을 위 클램프에 물렸다. 좌표: 원점은 구멍 중심, x는 하중 축 (물림부 끝 x = ±75 mm), y는 폭 방향.', 'Specimen with hole hung from the upper clamp. Coordinates: origin at the hole centre, x along the load axis (grip ends at x = ±75 mm), y across the width.'),
        }[sp];
        return {ok: true, text: note};
      }
      case 'rotate': {
        const a = num(args[0]); if (a === null || Math.abs(a) > 360) return err(tr('사용법: rotate <deg>  예: rotate 30', 'Usage: rotate <deg>  e.g. rotate 30'));
        if (S.spec === 'none') return err(tr('시편이 없다. mount 로 먼저 단다.', 'No specimen. Use mount first.'));
        S.rotate = Math.round(a * 2) / 2; this.advance(15);
        return {ok: true, text: tr(`시편 축이 첫 편광판 축과 ${S.rotate}°를 이룬다.`, `Specimen axis at ${S.rotate}° to the first polarizer axis.`)};
      }
      case 'hanger': {
        if (!['on', 'off'].includes(args[0])) return err(tr('사용법: hanger on|off', 'Usage: hanger on|off'));
        if (S.spec === 'none') return err(tr('시편이 없다.', 'No specimen.'));
        const on = args[0] === 'on';
        if (!on && S.weights > 0 && S.spec !== 'beam') return err(tr('추를 먼저 내려라 (load 0).', 'Remove the masses first (load 0).'));
        this.setLoad(() => { S.hanger = on; }, 20);
        out.push(on ? tr('추걸이를 걸었다 (각인 50 g).', 'Hanger attached (stamped 50 g).') : tr('추걸이를 뗐다.', 'Hanger removed.'));
        this.watchReport(out); return {ok: true, text: out.join('\n')};
      }
      case 'load': {
        const g = num(args[0]); const n = g === null ? null : weightSet(g);
        if (S.spec === 'none') return err(tr('시편이 없다.', 'No specimen.'));
        if (!n) return err(tr('추 세트(50 g×4, 100 g×4, 500 g×6)로 만들 수 있는 값을 g으로 적어라. 예: load 1450', 'Give a total in g that the set (50 g×4, 100 g×4, 500 g×6) can make. e.g. load 1450'));
        if (S.spec !== 'beam' && !S.hanger && g > 0) return err(tr('추걸이가 없다. hanger on 을 먼저 한다.', 'No hanger. Use hanger on first.'));
        if (S.spec === 'beam' && g > 300) return err(tr('보가 크게 처져 자유단이 받침에 닿는다. 300 g 이하로 건다.', 'The beam sags until the free end touches the base. Hang 300 g or less.'));
        const old = weightSet(S.weights), changed = Math.abs(n[50] - old[50]) + Math.abs(n[100] - old[100]) + Math.abs(n[500] - old[500]);
        this.setLoad(() => { S.weights = g; }, 10 + 8 * changed);
        out.push(tr(`걸린 추 ${g} g`, `Masses hung: ${g} g`) + (g ? ` (${this.pieceText(n)})` : '') + (S.spec === 'beam' && !S.hanger && g ? tr(', 실 고리', ', thread loop') : S.hanger ? tr(' + 추걸이', ' + hanger') : ''));
        this.watchReport(out); return {ok: true, text: out.join('\n')};
      }
      case 'wait': {
        let n = num(args[0]); const u = (args[1] || 's').toLowerCase();
        if (n === null || n <= 0) return err(tr('사용법: wait <n> [s|min]  예: wait 2 min', 'Usage: wait <n> [s|min]  e.g. wait 2 min'));
        if (u.startsWith('m')) n *= 60; if (n > 3 * 3600) return err(tr('한 번에 3시간까지 넘길 수 있다.', 'At most 3 hours at a time.'));
        this.advance(n); out.push(tr(`시각 ${clockText(S.clock)}`, `Clock ${clockText(S.clock)}`)); this.watchReport(out);
        return {ok: true, text: out.join('\n')};
      }
      case 'look': return this.look();
      case 'read': {
        const x = num(args[0]), y = num(args[1]);
        if (x === null || y === null) return err(tr('사용법: read <x> <y>  (mm)', 'Usage: read <x> <y>  (mm)'));
        this.advance(15);
        const tx = x + this.gauss() * 0.05, ty = y + this.gauss() * 0.05, f = field(P, S, tx, ty);
        let I, note = '';
        if (S.spec === 'none' || f.kind === 'out' || f.kind === 'hole') { I = this.eye(intensity(P, S, {kind: 'out'})); note = S.spec === 'none' ? '' : tr('  (시편 밖)', '  (outside the specimen)'); }
        else if (f.kind === 'rim') { I = this.eye(0.02); note = tr('  (구멍 가장자리의 어두운 테두리)', '  (dark rim at the hole edge)'); }
        else {
          const gr = gradN(P, S, tx, ty);
          if (gr > 1 / (1.5 * P.sMin)) { I = Math.round(50 + this.gauss() * 8); note = tr('  줄이 너무 촘촘해 밝기를 가늠할 수 없다', '  fringes too dense to judge the brightness'); }
          else I = this.eye(intensity(P, S, f));
          if (f.kind === 'rough') note += tr('  가공면 근처라 무늬가 일그러져 있다', '  pattern distorted near the machined surface');
        }
        this.record('brightness', I, '%', x, y);
        const t = `   x/mm    y/mm   I/%\n${pad(fmt(x, 2), 8)}${pad(fmt(y, 2), 8)}${pad(I, 6)}` + (note ? '\n' + note.trim() : '');
        out.push(t); this.watchReport(out); return {ok: true, text: out.join('\n')};
      }
      case 'watch': {
        if (args[0] === 'off') { S.watch = null; this.advance(5); return {ok: true, text: tr('watch 해제', 'Watch point cleared')}; }
        const x = num(args[0]), y = num(args[1]);
        if (x === null || y === null) return err(tr('사용법: watch <x> <y> | watch off', 'Usage: watch <x> <y> | watch off'));
        if (S.spec === 'none') return err(tr('시편이 없다.', 'No specimen.'));
        const tx = x + this.gauss() * 0.03, ty = y + this.gauss() * 0.03, f = field(P, S, tx, ty);
        if (f.kind !== 'mat' && f.kind !== 'rough') return err(tr('그 점은 시편 위가 아니다.', 'That point is not on the specimen.'));
        S.watch = {x, y, tx, ty, dark: 0, bright: 0, dDark: 0, dBright: 0, rough: f.kind === 'rough'};
        this.advance(20);
        return {ok: true, text: tr(`(${x}, ${y})에 유성펜으로 점을 찍었다. 이제 하중이나 시간이 바뀌면 이 점을 지나가는 줄을 센다.`, `Marked (${x}, ${y}) with the pen. Fringes passing this point are counted whenever the load or the time changes.`)};
      }
      case 'fringes': return this.fringes(args);
      case 'measure': return this.measure(args[0]);
      case 'log': {
        const rows = S.records.slice(-20);
        if (!rows.length) return {ok: true, text: tr('기록이 없다.', 'No records.')};
        const c = v => v === '' ? '' : Number(v).toFixed(2);
        return {ok: true, text: '  id  time      spec     load_g  quantity             x_mm    y_mm  value\n' + rows.map(r => `${pad(r.id, 4)}  ${r.time}  ${r.specimen.padEnd(7)}${pad(r.weights_g + (r.hanger === 'on' ? '+H' : ''), 8)}  ${String(r.quantity).padEnd(18)}${pad(c(r.x_mm), 7)} ${pad(c(r.y_mm), 7)}  ${r.value} ${r.unit}`).join('\n') + '\n' + this.tr('편광계, 검광판, 회전 각도는 csv에 있다.', 'Polariscope, analyzer and rotation are in the csv.')};
      }
      case 'reset': {
        if (args[0] === 'confirm' && S.pendingReset) return {ok: true, reset: true, text: tr('새 장치를 받았다. 기록을 지웠다.', 'New apparatus issued. Records deleted.')};
        S.pendingReset = true;
        return {ok: true, text: tr('새 장치(새 숨은 값)를 받고 지금까지의 기록을 모두 지운다. 계속하려면 reset confirm 을 입력하라.', 'This draws a new apparatus (new hidden values) and deletes all records. Type reset confirm to continue.')};
      }
      default: return err(tr(`${cmd}: 없는 명령. help 를 입력하라.`, `${cmd}: command not found. Type help.`));
    }
  }
  pieceText(n) { return [500, 100, 50].filter(p => n[p]).map(p => `${p} g×${n[p]}`).join(', '); }

  look() {
    const S = this.S, P = this.P, tr = (k, e) => this.tr(k, e); this.advance(20);
    const bg = this.eye(intensity(P, S, {kind: 'out'}));
    if (S.spec === 'none') { this.record('brightness', bg, '%'); return {ok: true, text: tr(`밝기 I = ${bg} %  (평행 편광판 = 100 %)`, `Brightness I = ${bg} %  (parallel polarizers = 100 %)`)}; }
    const pts = {
      tension: [[0, 0, tr('중앙', 'centre')], [0, P.b1 / 2 - 0.3, tr('옆 모서리 0.3 mm 안쪽', '0.3 mm inside the side edge')], [70, 0, tr('물림부 근처', 'near the grip')]],
      beam: [[60, P.h / 2, tr('중간 높이', 'mid-depth')], [60, P.h - 0.5, tr('위 모서리 근처', 'near the top edge')], [60, 0.5, tr('아래 모서리 근처', 'near the lower edge')]],
      hole: [[50, 0, tr('구멍에서 먼 곳', 'far from the hole')], [0, P.d / 2 + 2, tr('구멍 옆 2 mm', '2 mm beside the hole')], [P.d / 2 + 2, 0, tr('구멍 위 2 mm', '2 mm above the hole')]],
    }[S.spec];
    const lines = [`${pad('I/%', 5)}  ${tr('위치', 'place')}`, `${pad(bg, 5)}  ${tr('시편 밖', 'outside the specimen')}`];
    this.record('brightness_outside', bg, '%');
    for (const [x, y, name] of pts) {
      const f = field(P, S, x, y), I = this.eye(intensity(P, S, f));
      lines.push(`${pad(I, 5)}  ${name} (${fmt(x, 1)}, ${fmt(y, 1)})`); this.record('brightness', I, '%', fmt(x, 1), fmt(y, 1));
    }
    const line = {tension: ['y', 0, -75, 75], beam: ['x', 60, 0, P.h], hole: ['x', 0, P.d / 2, P.b2 / 2]}[S.spec];
    const fr = darkFringes(P, S, line[0], line[1], line[2], line[3]);
    const lineName = {tension: tr('중심선 y = 0 전체', 'the centre line y = 0'), beam: tr('단면 x = 60 mm', 'the section x = 60 mm'), hole: tr('구멍 옆 x = 0 (한쪽)', 'beside the hole along x = 0 (one side)')}[S.spec];
    lines.push(tr(`${lineName}에 보이는 어두운 줄: ${fr.length}개`, `Dark fringes visible on ${lineName}: ${fr.length}`));
    if (S.spec === 'tension' && fr.length) lines.push(tr('줄은 물림부 근처에 몰려 있다.', 'They are crowded near the grips.'));
    if (S.spec === 'hole' && fr.length > 3) lines.push(tr('구멍 가장자리로 갈수록 줄이 촘촘해진다.', 'The fringes crowd together towards the hole edge.'));
    const out = [lines.join('\n')]; this.watchReport(out);
    return {ok: true, text: out.join('\n')};
  }

  fringes(args) {
    const S = this.S, P = this.P, tr = (k, e) => this.tr(k, e);
    const usage = tr('사용법: fringes x <값> [from to]  (x = 값인 선 위에서 y 위치) | fringes y <값> [from to]', 'Usage: fringes x <value> [from to]  (y positions on the line x = value) | fringes y <value> [from to]');
    const axis = args[0], v = Number(args[1]);
    if (!['x', 'y'].includes(axis) || !Number.isFinite(v)) return {ok: false, text: usage};
    if (S.spec === 'none') return {ok: false, text: tr('시편이 없다.', 'No specimen.')};
    const ext = extent(P, S.spec), other = axis === 'x' ? ext.y : ext.x;
    let from = args[2] !== undefined ? Number(args[2]) : other[0], to = args[3] !== undefined ? Number(args[3]) : other[1];
    if (!Number.isFinite(from) || !Number.isFinite(to) || from === to) return {ok: false, text: usage};
    if (from > to) [from, to] = [to, from];
    from = Math.max(from, other[0] - 0.5); to = Math.min(to, other[1] + 0.5);
    const near = S.spec === 'hole' && Math.abs(v) < 10, place = near ? 0.03 : 0.2;
    const tv = v + this.gauss() * place;
    this.advance(90);
    const list = darkFringes(P, S, axis, tv, from, to);
    const out = [];
    const other_ = axis === 'x' ? 'y' : 'x';
    if (!list.length) out.push(tr(`${axis} = ${v} 선 위 ${from}–${to} mm: 어두운 줄이 보이지 않는다.`, `Line ${axis} = ${v}, ${from} to ${to} mm: no dark fringes visible.`));
    else {
      out.push(tr(`${axis} = ${v} mm 선 위의 어두운 줄 (${other_} 위치, 캘리퍼스 0.05 mm)`, `Dark fringes on the line ${axis} = ${v} mm (${other_} position, caliper 0.05 mm)`));
      out.push(`   #   ${other_}/mm   width/mm`);
      list.forEach((f, i) => {
        const p = Math.round((f.pos + this.gauss() * 0.04) * 20) / 20, w = Math.max(0.1, Math.round(f.width * 10) / 10);
        out.push(`${pad(i + 1, 4)}${pad(p.toFixed(2), 10)}${pad(w.toFixed(1), 11)}`);
        this.record('dark_fringe', p.toFixed(2), 'mm', axis === 'x' ? v : '', axis === 'y' ? v : '');
      });
    }
    this.watchReport(out);
    return {ok: true, text: out.join('\n')};
  }

  measure(what) {
    const S = this.S, P = this.P, tr = (k, e) => this.tr(k, e), sp = S.spec;
    const usage = tr('사용법: measure t|width|hole|arm|length', 'Usage: measure t|width|hole|arm|length');
    if (sp === 'none') return {ok: false, text: tr('시편이 없다.', 'No specimen.')};
    const F = appliedForce(P, S) + S.creep;
    const strain = sp === 'beam' ? 0 : F / ((sp === 'tension' ? P.b1 : P.b2) * (sp === 'tension' ? P.tT : P.tH) * 1e-6) / P.E;
    let true_, inst, res, sd, name;
    if (what === 't') { true_ = ({tension: P.tT, beam: P.tB, hole: P.tH})[sp] * (1 - P.nu * strain); inst = 'caliper'; name = 't'; }
    else if (what === 'width') { true_ = ({tension: P.b1, beam: P.h, hole: P.b2})[sp] * (1 - P.nu * strain); inst = 'caliper'; name = sp === 'beam' ? 'h' : sp === 'tension' ? 'b1' : 'b2'; }
    else if (what === 'hole') { if (sp !== 'hole') return {ok: false, text: tr('이 시편에는 구멍이 없다.', 'This specimen has no hole.')}; true_ = P.d; inst = 'caliper'; name = 'd'; }
    else if (what === 'arm') { if (sp !== 'beam') return {ok: false, text: tr('arm은 굽힘 보에서 클램프 끝부터 추를 건 홈까지의 수평 거리이다.', 'arm is the horizontal distance from the clamp edge to the loading notch on the beam.')}; true_ = P.Lb - shortening(P, F, P.Lb); inst = 'ruler'; name = 'arm'; }
    else if (what === 'length') { true_ = sp === 'beam' ? P.beamLen - shortening(P, F, P.beamLen) : 150 * (1 + strain); inst = 'ruler'; name = sp === 'beam' ? 'overhang' : 'grip_gap'; }
    else return {ok: false, text: usage};
    if (inst === 'caliper') { res = 0.02; sd = what === 'hole' ? 0.02 : 0.012; } else { res = 0.5; sd = 0.3; }
    this.advance(30);
    const v = Math.round((true_ + this.gauss() * sd) / res) * res, d = res < 0.1 ? 2 : 1;
    this.record(name, v.toFixed(d), 'mm');
    const instName = inst === 'caliper' ? tr('버니어 캘리퍼스, 눈금 0.02 mm', 'vernier caliper, 0.02 mm scale') : tr('300 mm 자, 0.5 mm까지 눈어림', '300 mm ruler, read to 0.5 mm');
    const out = [`${name} = ${v.toFixed(d)} mm  (${instName})`]; this.watchReport(out);
    return {ok: true, text: out.join('\n')};
  }
}
