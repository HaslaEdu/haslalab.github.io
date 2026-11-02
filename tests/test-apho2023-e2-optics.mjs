// The reflected pattern of sim/apho2023_E2_web.html against the official
// APhO 2023 Experimental Problem 2 solution.  The model computes the far
// field of the beam reflected from a Gaussian thermal bump; these checks
// read the pattern the way a student does (rings along a radius) and
// compare with the published tables.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

const html = readFileSync(new URL('../sim/apho2023_E2_web.html', import.meta.url), 'utf8');
const block = html.slice(html.indexOf('const LAMBDA'), html.indexOf('/* the deep red of a 650 nm diode'));
const M = runInNewContext(block + ';({ThermoModel, mulberry})', {Math, Map, Float64Array, Number, Object});

/* a plate with the nominal constants, in focus */
function plate(){
  const m = new M.ThermoModel(M.mulberry(5));
  Object.assign(m, {wb_spot: 1, slope: 0.4632, P_th: 280.5, P_yield: 363.6});
  m.waist = m.d_plate;
  return m;
}
const N = P => 0.4632 * (P - 280.5);
/* rings along a radius of the screen, L cm away */
function read(m, n, L){
  const ff = m.pattern(n), I = [];
  for (let R = 0; R <= 20; R += 0.01) I.push([R, m.intensity(Math.sin(Math.atan2(R, L)), ff)]);
  const maxs = [], mins = [];
  for (let i = 1; i < I.length - 1; i++){
    if (I[i][1] > I[i - 1][1] && I[i][1] >= I[i + 1][1] && I[i][1] > 0.05) maxs.push(I[i][0]);
    if (I[i][1] < I[i - 1][1] && I[i][1] <= I[i + 1][1]) mins.push(I[i][0]);
  }
  const out = maxs[maxs.length - 1];
  return {D: 2 * out, dark: mins.filter(R => R < out)};
}
const fit = (X, Y) => { const n = X.length, mx = X.reduce((a, b) => a + b) / n, my = Y.reduce((a, b) => a + b) / n;
  let sxy = 0, sxx = 0; X.forEach((x, i) => { sxy += (x - mx) * (Y[i] - my); sxx += (x - mx) ** 2; }); return sxy / sxx; };

test('A.2: at the yield power the outermost ring is 27.5 cm across on a screen 49.2 cm away', () => {
  const r = read(plate(), N(363.6), 49.2);
  assert.ok(Math.abs(r.D - 27.5) < 0.6, `D_out ${r.D}`);
});

test('B.1: the rings you can count follow the official table up to 327 mW', () => {
  const m = plate();
  for (const [P, n] of [[296.5, 4], [301.5, 5], [305.6, 9], [309.0, 11], [315.7, 13], [320.6, 15], [324.1, 16], [326.6, 19]]){
    const seen = read(m, N(P), 49.2).dark.length;
    assert.ok(Math.abs(seen - n) <= 2, `${P} mW: ${seen} dark rings, official ${n}`);
  }
});

test('B.2: the outer diameter grows linearly with power; its slope scales with the screen distance', () => {
  const m = plate(), Ps = [296.5, 301.5, 305.6, 306, 309, 310.5, 315.7, 320.6, 324.1, 326.6];
  const k49 = fit(Ps, Ps.map(P => read(m, N(P), 49.2).D)), k66 = fit(Ps, Ps.map(P => read(m, N(P), 66).D));
  assert.ok(k49 > 0.30 && k49 < 0.36, `slope at 49.2 cm ${k49}`);
  assert.ok(Math.abs(k66 - 0.4482) < 0.03, `slope at 66 cm ${k66}`);
});

test('C: the rings open out towards the edge, so alpha against m is not a straight line', () => {
  const r = read(plate(), N(320.6), 49.2), w = r.dark.slice(1).map((R, i) => R - r.dark[i]);
  assert.ok(w[w.length - 1] > 1.8 * w[0], `widths ${w.map(v => v.toFixed(2))}`);
});

test('out of focus the spot, the yield power and the bump grow and the pattern shrinks', () => {
  const m = plate(), n = N(320.6), D0 = read(m, n, 49.2).D;
  m.waist = m.d_plate + 4; m._ff = null;
  assert.ok(m.spot_scale() > 1.3);
  assert.ok(read(m, n, 49.2).D < 0.8 * D0);
  m.m_max(95);                                 /* ~355 mW: melts in focus, not here */
  assert.equal(m.melted, false);
});

test('the surface yields at the official power when the beam is in focus', () => {
  const m = plate();
  const cur = P => { let lo = 40, hi = 140; for (let i = 0; i < 60; i++){ const c = (lo + hi) / 2; if (m.power_true(c) < P) lo = c; else hi = c; } return lo; };
  m.m_max(cur(360)); assert.equal(m.melted, false);
  m.m_max(cur(366)); assert.equal(m.melted, true);
});
