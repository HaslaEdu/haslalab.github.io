/* Starting points for the Workshop's simulation editor (create.html): each is a whole program for the `hl` helpers that
   sim-sandbox.html defines. They are text here; the page only ever runs them inside the sandbox frame.
   tests/test-sim-helpers.cjs runs every one of them headless for a few seconds of simulated time. */
(function(root){
  'use strict';
  const T=[
{id:'blank',ko:'빈 시뮬레이션',en:'Blank simulation',code:`// 빈 시뮬레이션: 상태를 정하고(init), 한 단계씩 움직이고(step), 그립니다(draw).
// 좌표는 미터(m), y는 위쪽이 +입니다.
const v = hl.slider('v (m/s)', 0, 5, 1, 0.1);

hl.view(0, 10, 0);
hl.run({
  dt: 1 / 240,
  init: () => ({x: 1, y: 2}),
  step(s, dt) { s.x += v() * dt; if (s.x > 9) s.x = 1; },
  draw(s, t) {
    hl.clear(); hl.grid(1); hl.ground(0);
    hl.circle(s.x, s.y, 0.3);
    hl.arrow(s.x, s.y, v(), 0, {label: 'v'});
    hl.show('x', s.x, 'm');
  }
});
`},
{id:'projectile',ko:'공기 저항이 있는 포물선 운동',en:'Projectile with air drag',code:`// 공기 저항(F = k v²)이 있는 포물선 운동. 회색 선은 저항이 없을 때의 궤적입니다.
const v0 = hl.slider('v0 (m/s)', 5, 40, 20, 0.5);
const ang = hl.slider('angle (°)', 5, 85, 45, 1);
const m = hl.slider('m (kg)', 0.05, 2, 0.15, 0.05);
const k = hl.slider('k (kg/m)', 0, 0.02, 0.004, 0.0005);
const g = 9.8;

hl.view(-2, 45, -1);
const trail = hl.trail(3000);
const speed = hl.plot('|v| (m/s)', {xlabel: 's'});
// 상태 [x, y, vx, vy]의 시간 미분
const f = (t, [x, y, vx, vy]) => {
  const v = Math.hypot(vx, vy), c = k() / m();
  return [vx, vy, -c * v * vx, -g - c * v * vy];
};

hl.run({
  dt: 1 / 500, resetOnChange: true,
  init() {
    trail.clear();
    const a = ang() * Math.PI / 180;
    return {y: [0, 0, v0() * Math.cos(a), v0() * Math.sin(a)], landed: false, top: 0};
  },
  step(s, dt, t) {
    if (s.landed) return;
    s.y = hl.rk4(f, s.y, t, dt);
    s.top = Math.max(s.top, s.y[1]);
    if (s.y[1] < 0) s.landed = true;
  },
  draw(s, t) {
    const [x, y, vx, vy] = s.y, a = ang() * Math.PI / 180, ux = v0() * Math.cos(a), uy = v0() * Math.sin(a);
    hl.clear(); hl.grid(5); hl.ground(0);
    const T = 2 * uy / g;   // 진공에서의 비행 시간
    for (let i = 0; i < 60; i++) {
      const t1 = T * i / 60, t2 = T * (i + 1) / 60;
      hl.line(ux * t1, uy * t1 - g * t1 * t1 / 2, ux * t2, uy * t2 - g * t2 * t2 / 2, hl.colors.muted, 1);
    }
    trail.push(x, Math.max(0, y)); trail.draw();
    hl.circle(x, Math.max(0, y), 0.4);
    hl.arrow(x, Math.max(0, y), vx, vy, {scale: 0.25, label: 'v'});
    if (!s.landed) speed.add(t, Math.hypot(vx, vy));
    hl.show('x', x, 'm'); hl.show('최고 높이', s.top, 'm'); hl.show('진공 사거리', v0() ** 2 * Math.sin(2 * a) / g, 'm');
  }
});
`},
{id:'spring',ko:'용수철 진자 (감쇠 진동)',en:'Spring and mass (damped)',code:`// 벽에 붙은 용수철과 물체: m x'' = -k x - b v. 그래프는 운동 에너지 K, 퍼텐셜 에너지 U, 합 E.
const k = hl.slider('k (N/m)', 1, 100, 20, 1);
const m = hl.slider('m (kg)', 0.1, 5, 1, 0.1);
const b = hl.slider('b (kg/s)', 0, 2, 0, 0.05);
const x0 = hl.slider('x0 (m)', -0.8, 0.8, 0.5, 0.05);

hl.view(-1.6, 1.6, -0.6);
const energy = hl.plot('energy (J)', {xlabel: 's'});

hl.run({
  dt: 1 / 1000, resetOnChange: true,
  init: () => ({y: [x0(), 0]}),
  step(s, dt, t) { s.y = hl.rk4((t, [x, v]) => [v, (-k() * x - b() * v) / m()], s.y, t, dt); },
  draw(s, t) {
    const [x, v] = s.y, K = m() * v * v / 2, U = k() * x * x / 2;
    hl.clear(); hl.ground(0);
    hl.rect(-1.55, 0, 0.06, 0.7, hl.colors.muted);
    hl.spring(-1.49, 0.2, x - 0.15, 0.2, {coils: 12, width: 0.12});
    hl.rect(x - 0.15, 0, 0.3, 0.4, hl.colors.accent);
    hl.arrow(x, 0.55, -k() * x, 0, {scale: 0.02, label: 'F'});
    energy.add(t, K, 'K'); energy.add(t, U, 'U'); energy.add(t, K + U, 'E');
    hl.show('x', x, 'm'); hl.show('T = 2π√(m/k)', 2 * Math.PI * Math.sqrt(m() / k()), 's');
  }
});
`},
{id:'pendulum',ko:'단진자 (큰 진폭)',en:'Pendulum (large swings)',code:`// 단진자: θ'' = -(g/L) sin θ. 진폭이 크면 주기가 작은 진폭 공식 2π√(L/g)보다 길어집니다.
const L = hl.slider('L (m)', 0.2, 2, 1, 0.05);
const A = hl.slider('amplitude (°)', 5, 170, 30, 1);
const g = 9.8;

hl.view(-2.3, 2.3, -2.4, 0.4);
const angle = hl.plot('θ (°)', {xlabel: 's'});

hl.run({
  dt: 1 / 1000, resetOnChange: true,
  init: () => ({y: [A() * Math.PI / 180, 0], crossings: 0, last: 0, period: 0}),
  step(s, dt, t) {
    const prev = s.y[1];
    s.y = hl.rk4((t, [th, w]) => [w, -g / L() * Math.sin(th)], s.y, t, dt);
    // 각속도가 음에서 양으로 바뀌는 순간 = 한 주기
    if (prev < 0 && s.y[1] >= 0) { if (s.last) s.period = t - s.last; s.last = t; s.crossings++; }
  },
  draw(s, t) {
    const th = s.y[0], x = L() * Math.sin(th), y = -L() * Math.cos(th);
    hl.clear();
    hl.line(-0.5, 0, 0.5, 0, hl.colors.muted, 3);
    hl.line(0, 0, x, y);
    hl.circle(x, y, 0.08);
    hl.arrow(x, y, 0, -1, {scale: 0.3, label: 'mg', color: hl.colors.red});
    angle.add(t, th * 180 / Math.PI);
    hl.show('측정 주기', s.period, 's'); hl.show('2π√(L/g)', 2 * Math.PI * Math.sqrt(L() / g), 's');
  }
});
`},
{id:'orbit',ko:'행성 궤도 (만유인력)',en:'Orbit under gravity',code:`// 태양 둘레의 행성. 단위: 길이 AU, 시간 년(yr), GM = 4π² AU³/yr².
// 속도 Verlet 적분은 에너지를 오래 보존합니다. v0 = 2π이면 원 궤도입니다.
const v0 = hl.slider('v0 (AU/yr)', 2, 9, 5, 0.1);
const GM = 4 * Math.PI ** 2;

hl.view(-3, 3, -2.2, 2.2);
const trail = hl.trail(1500);
const energy = hl.plot('E / m (AU²/yr²)', {xlabel: 'yr'});
const acc = ([x, y]) => { const r3 = Math.hypot(x, y) ** 3; return [-GM * x / r3, -GM * y / r3]; };

hl.run({
  dt: 1 / 2000, speed: 0.25, resetOnChange: true,
  init() { trail.clear(); return {x: [1, 0], v: [0, v0()]}; },
  step(s, dt, t) { [s.x, s.v] = hl.verlet(acc, s.x, s.v, t, dt); },
  draw(s, t) {
    const [x, y] = s.x, [vx, vy] = s.v, r = Math.hypot(x, y);
    const E = (vx * vx + vy * vy) / 2 - GM / r, Lz = x * vy - y * vx;
    hl.clear(); hl.grid(1);
    hl.circle(0, 0, 0.12, hl.colors.orange);
    trail.push(x, y); trail.draw();
    hl.circle(x, y, 0.06, hl.colors.blue);
    hl.arrow(x, y, vx, vy, {scale: 0.08, label: 'v'});
    energy.add(t, E);
    hl.show('r', r, 'AU'); hl.show('E/m', E); hl.show('L/m', Lz);
    if (E < 0) hl.show('케플러 주기', Math.pow(-GM / (2 * E), 1.5), 'yr');
  }
});
`},
{id:'magnetic',ko:'자기장 속 대전 입자',en:'Charged particle in a magnetic field',code:`// 자기장 B (화면에서 나오는 방향)와 전기장 E (y 방향) 속의 대전 입자: m a = q (E + v × B).
// E가 0이 아니면 입자가 E×B 방향으로 표류합니다 (속도 E/B).
const qm = hl.slider('q/m (C/kg)', -2, 2, 1, 0.1);
const B = hl.slider('B (T)', 0.1, 3, 1, 0.1);
const E = hl.slider('E (V/m)', -2, 2, 0, 0.1);
const v0 = hl.slider('v0 (m/s)', 0.5, 5, 2, 0.1);

hl.view(-6, 6, -4, 4);
const trail = hl.trail(4000, hl.colors.red);
// [x, y, vx, vy]: v × B = (vy B, -vx B) for B along z
const f = (t, [x, y, vx, vy]) => [vx, vy, qm() * vy * B(), qm() * (E() - vx * B())];

hl.run({
  dt: 1 / 1000, resetOnChange: true,
  init() { trail.clear(); return {y: [0, 0, v0(), 0]}; },
  step(s, dt, t) { s.y = hl.rk4(f, s.y, t, dt); },
  draw(s, t) {
    const [x, y, vx, vy] = s.y;
    hl.clear();
    for (let gx = -5; gx <= 5; gx += 1) for (let gy = -3; gy <= 3; gy += 1) hl.dot(gx, gy, 1.5, hl.colors.muted);
    trail.push(x, y); trail.draw();
    hl.circle(x, y, 0.12, qm() >= 0 ? hl.colors.red : hl.colors.blue);
    hl.arrow(x, y, vx, vy, {scale: 0.4, label: 'v'});
    const w = Math.abs(qm() * B());
    hl.show('반지름 mv/(qB)', v0() / w, 'm'); hl.show('주기 2πm/(qB)', 2 * Math.PI / w, 's'); hl.show('표류 E/B', E() / B(), 'm/s');
  }
});
`},
{id:'wave',ko:'줄의 파동',en:'Wave on a string',code:`// 양 끝이 고정된 줄: ∂²y/∂t² = c² ∂²y/∂x², c = √(T/μ). 줄을 누르면(클릭) 그 자리에서 튕깁니다.
const T = hl.slider('T (N)', 1, 50, 10, 1);
const mu = hl.slider('μ (kg/m)', 0.01, 0.2, 0.05, 0.01);
const damp = hl.slider('damping', 0, 2, 0.2, 0.05);
const L = 2, N = 120, dx = L / N;

hl.view(-0.1, 2.1, -0.5, 0.5);
let y = new Array(N + 1).fill(0), yOld = y.slice();
function pluck(at) {
  for (let i = 1; i < N; i++) { const d = (i * dx - at) / 0.08; y[i] += 0.25 * Math.exp(-d * d); }
  yOld = y.slice();
}
hl.onClick(x => { if (x > 0 && x < L) pluck(x); });
hl.button('pluck', () => pluck(0.5));
hl.button('flat', () => { y.fill(0); yOld.fill(0); });

hl.run({
  dt: 1 / 4000,
  init() { y.fill(0); pluck(0.5); return {}; },
  step(s, dt) {
    const c = Math.sqrt(T() / mu()), r = (c * dt / dx) ** 2, k = damp() * dt;
    if (r > 1) throw new Error('불안정: c·dt/dx > 1. N이나 dt를 줄이세요.');
    const next = new Array(N + 1).fill(0);
    for (let i = 1; i < N; i++) next[i] = ((2 * y[i] - (1 - k) * yOld[i]) + r * (y[i + 1] - 2 * y[i] + y[i - 1])) / (1 + k);
    yOld = y; y = next;
  },
  draw() {
    hl.clear(); hl.axes('x (m)', 'y (m)');
    for (let i = 0; i < N; i++) hl.line(i * dx, y[i], (i + 1) * dx, y[i + 1], hl.colors.accent, 2);
    hl.dot(0, 0, 5, hl.colors.muted); hl.dot(L, 0, 5, hl.colors.muted);
    const c = Math.sqrt(T() / mu());
    hl.show('c = √(T/μ)', c, 'm/s'); hl.show('기본 진동수 c/2L', c / (2 * L), 'Hz');
  }
});
`},
{id:'gas',ko:'상자 속 이상 기체',en:'Ideal gas in a box',code:`// 2차원 상자 속 입자들. 벽이 받는 충격량으로 압력을 재고, 이상 기체 P A = N k T 와 비교합니다.
// (2차원: 평균 운동 에너지 = kT, 압력 = 벽 길이당 힘). 충돌은 띄엄띄엄 일어나므로 처음부터의 평균을 봅니다.
// 입자에 크기가 있어 실제 압력은 이상 기체보다 조금 큽니다 (반 데르 발스의 b 항).
const N = hl.slider('N', 10, 150, 60, 1);
const kT = hl.slider('kT (J)', 0.5, 5, 1, 0.1);
const collide = hl.toggle('입자끼리 충돌', true);
const Lx = 10, Ly = 6, m = 1, R = 0.12;

hl.view(-0.5, 10.5, -0.5, 6.5);
const plot = hl.plot('P (N/m)', {xlabel: 's'});

hl.run({
  dt: 1 / 500, resetOnChange: true,
  init() {
    const p = [];
    for (let i = 0; i < N(); i++) {
      const v = Math.sqrt(2 * kT() / m), a = Math.random() * 2 * Math.PI;
      p.push({x: R + Math.random() * (Lx - 2 * R), y: R + Math.random() * (Ly - 2 * R), vx: v * Math.cos(a), vy: v * Math.sin(a)});
    }
    return {p, impulse: 0, time: 0, since: 0, P: 0};
  },
  step(s, dt) {
    for (const q of s.p) {
      q.x += q.vx * dt; q.y += q.vy * dt;
      if (q.x < R && q.vx < 0 || q.x > Lx - R && q.vx > 0) { q.vx = -q.vx; s.impulse += 2 * m * Math.abs(q.vx); }
      if (q.y < R && q.vy < 0 || q.y > Ly - R && q.vy > 0) { q.vy = -q.vy; s.impulse += 2 * m * Math.abs(q.vy); }
    }
    if (collide()) for (let i = 0; i < s.p.length; i++) for (let j = i + 1; j < s.p.length; j++) {
      const a = s.p[i], b = s.p[j], dx = b.x - a.x, dy = b.y - a.y, d2 = dx * dx + dy * dy;
      if (d2 > 4 * R * R || d2 === 0) continue;
      const d = Math.sqrt(d2), nx = dx / d, ny = dy / d, vn = (b.vx - a.vx) * nx + (b.vy - a.vy) * ny;
      if (vn >= 0) continue;   // 이미 멀어지는 중
      a.vx += vn * nx; a.vy += vn * ny; b.vx -= vn * nx; b.vy -= vn * ny;   // 같은 질량의 탄성 충돌
    }
    s.time += dt; s.since += dt;
    s.P = s.impulse / s.time / (2 * (Lx + Ly));   // 지금까지 벽이 받은 평균 힘 / 벽 길이
    if (s.since >= 0.25) { s.since = 0; s.fresh = true; }
  },
  draw(s, t) {
    hl.clear();
    hl.rect(0, 0, Lx, Ly, hl.colors.muted, false);
    let K = 0;
    for (const q of s.p) { hl.circle(q.x, q.y, R, hl.colors.blue); K += m * (q.vx * q.vx + q.vy * q.vy) / 2; }
    const ideal = s.p.length * (K / s.p.length) / (Lx * Ly);
    if (s.fresh) { plot.add(t, s.P, '측정'); plot.add(t, ideal, 'NkT/A'); s.fresh = false; }
    hl.show('측정 P (평균)', s.P, 'N/m'); hl.show('NkT/A', ideal, 'N/m'); hl.show('평균 KE', K / s.p.length, 'J');
  }
});
`},
{id:'rc',ko:'RC 회로 충전·방전',en:'RC circuit',code:`// RC 회로: 스위치를 켜면 충전, 끄면 방전. dq/dt = (ε - q/C)/R, 시간 상수 τ = RC.
const eps = hl.slider('ε (V)', 1, 12, 9, 0.5);
const R = hl.slider('R (kΩ)', 1, 100, 10, 1);
const C = hl.slider('C (μF)', 10, 1000, 100, 10);
const on = hl.toggle('스위치 닫기 (충전)', true);

hl.view(0, 10, 0, 6);
const plot = hl.plot('V (V)', {xlabel: 's'});

hl.run({
  dt: 1 / 1000,
  init: () => ({q: 0}),
  step(s, dt, t) {
    const r = R() * 1e3, c = C() * 1e-6, e = on() ? eps() : 0;
    s.q = hl.rk4((t, [q]) => [(e - q / c) / r], [s.q], t, dt)[0];
  },
  draw(s, t) {
    const r = R() * 1e3, c = C() * 1e-6, Vc = s.q / c, I = ((on() ? eps() : 0) - Vc) / r;
    hl.clear();
    // 회로 그림: 전지 — 스위치 — 저항 — 축전기
    const ink = hl.colors.ink;
    hl.line(1, 1, 1, 5, ink, 2); hl.line(1, 5, 3.5, 5, ink, 2); hl.line(6.5, 5, 9, 5, ink, 2); hl.line(9, 5, 9, 3.3, ink, 2); hl.line(9, 2.7, 9, 1, ink, 2); hl.line(9, 1, 1, 1, ink, 2);
    hl.line(0.6, 3.2, 1.4, 3.2, ink, 3); hl.line(0.8, 2.8, 1.2, 2.8, ink, 3); hl.text('ε', 1.6, 2.9);
    hl.spring(3.5, 5, 6.5, 5, {coils: 6, width: 0.4, color: ink}); hl.text('R', 4.9, 5.5);
    hl.line(8.4, 3.3, 9.6, 3.3, ink, 3); hl.line(8.4, 2.7, 9.6, 2.7, ink, 3); hl.text('C', 9.8, 2.9);
    hl.line(2, 1, 2.8, on() ? 1 : 1.5, on() ? hl.colors.green : hl.colors.red, 3);
    hl.arrow(5, 4.4, Math.sign(I) * 1, 0, {label: 'I', color: hl.colors.orange});
    plot.add(t, Vc, 'V_C'); plot.add(t, I * r, 'V_R');
    hl.show('V_C', Vc, 'V'); hl.show('I', I * 1e3, 'mA'); hl.show('τ = RC', r * c, 's');
  }
});
`}
  ];
  const api={list:T,byId:id=>T.find(t=>t.id===id)||null};
  if(typeof module==='object'&&module.exports)module.exports=api;else root.HL_SIM_TEMPLATES=api;
})(typeof window!=='undefined'?window:this);
