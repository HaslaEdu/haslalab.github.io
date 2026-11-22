// Drives lab.mjs like a student following the solution (E1.sol) and checks the results
// against the solution's accepted ranges. Run: node sim/hpho-mock1-e1/check.mjs
import { newState, exec, drawParams, C } from './lab.mjs';

const fit = (x, y) => { // least squares y = a + c x
  const n = x.length, mx = x.reduce((a, b) => a + b) / n, my = y.reduce((a, b) => a + b) / n;
  let sxx = 0, sxy = 0; for (let i = 0; i < n; i++) { sxx += (x[i] - mx) ** 2; sxy += (x[i] - mx) * (y[i] - my); }
  const c = sxy / sxx; return { c, a: my - c * mx };
};
const fit0 = (x, y) => { let sxy = 0, sxx = 0; for (let i = 0; i < x.length; i++) { sxy += x[i] * y[i]; sxx += x[i] * x[i]; } return sxy / sxx; };

function student(seed, nominal) {
  const s = newState(seed), p = drawParams(seed, nominal);
  const run = c => { const r = exec(s, c, 'en', p); if (!r.ok) throw Error(c + ': ' + r.text); return r; };
  const last = () => s.records.at(-1);
  const marks = [20, 35, 50, 65, 80, 95, 110, 125, 140, 150];
  // D first: open strip hung at the start, read every 5 min for 100 min (no lid)
  run('fill d2 water 40'); run('place d2 open'); run('dip d2');
  const D = [];
  for (let k = 0; k < 20; k++) { run('wait 5 min'); run('read d2'); D.push([last().t, last().value / 1000]); }
  // A: lidded container
  run('fill d1 water 30'); run('place d1 box'); run('dip d1');
  const A = marks.map(mk => { run('until d1 ' + mk); return [last().t, mk / 1000]; });
  run('lift d1');
  const nA = fit(A.map(a => Math.log(a[0])), A.map(a => Math.log(a[1]))).c;
  const K = fit0(A.map(a => a[0]), A.map(a => a[1] ** 2));
  const rd = 2 * C.mw * K / C.gw;
  // B: thickness by stacking, dry and wet mass at L = 12 cm
  run('caliper stack 10'); const th = last().value / 10 / 1000;
  run('caliper width'); const b = last().value / 1000;
  run('weigh strip'); const dry = +last().value;
  run('fill d1 water 30'); run('dip d1'); run('until d1 120'); run('lift d1'); run('weigh wet');
  const m = +last().value - dry, phi = m / 1000 / (C.rho * b * th * 0.120);
  // C: surfactant, same procedure
  run('fill d1 surf 30'); run('dip d1');
  const Cs = [20, 35, 50, 65, 80, 95, 110, 120].map(mk => { run('until d1 ' + mk); return [last().t, mk / 1000]; });
  run('lift d1');
  const Ks = fit0(Cs.map(a => a[0]), Cs.map(a => a[1] ** 2));
  const gs = C.gw * (C.ms / C.mw) * Ks / K * 1000;
  // D.1: d(L^2)/dt against L^2 using 10-min differences, x-intercept = Lmax^2
  const X = [], Y = [];
  for (let i = 0; i + 2 < D.length; i += 2) { const [t1, L1] = D[i], [t2, L2] = D[i + 2]; X.push((L1 * L1 + L2 * L2) / 2); Y.push((L2 * L2 - L1 * L1) / (t2 - t1)); }
  const f = fit(X, Y), Lmax = Math.sqrt(-f.a / f.c);
  const E = phi * C.rho * th * K / (4 * Lmax * Lmax);
  // D.3: mass loss of the open dish over 60 min
  run('lift d2'); run('caliper d2'); const Dd = last().value / 1000;
  run('weigh d2'); const m1 = +last().value, c1 = s.clock;
  run('wait 1 h'); run('weigh d2'); const m2 = +last().value, c2 = s.clock;
  const Ed = (m1 - m2) / 1000 / (Math.PI * Dd * Dd / 4) / (c2 - c1);
  return { n: nA, K, rd, t: th, m: m / 1000, phi, Ks, gs, Lmax, E, ratio: E / Ed, strips: s.next - 1, hours: s.clock / 3600 };
}

const ranges = { n: [0.44, 0.56], K: [1.4e-5, 2.8e-5], rd: [0.4e-6, 0.8e-6], t: [0.15e-3, 0.22e-3], m: [0.12e-3, 0.30e-3],
  phi: [0.45, 0.80], Ks: [6e-6, 12e-6], gs: [24, 42], Lmax: [0.16, 0.32], E: [0.4e-5, 2.5e-5], ratio: [1 / 3, 3] };
const ref = { n: 0.50, K: 2.0e-5, rd: 0.56e-6, t: 0.18e-3, m: 0.21e-3, phi: 0.65, Ks: 8.5e-6, gs: 32, Lmax: 0.24, E: 1.0e-5, ratio: 1 };
function batch(label, seeds, nominal) {
  const res = seeds.map(sd => student(sd, nominal));
  console.log(`\n${label}: ${seeds.length} runs`);
  console.log('qty     solution   mean        min         max         in range');
  let all = true;
  for (const k of Object.keys(ranges)) {
    const v = res.map(r => r[k]), [lo, hi] = ranges[k], ok = v.filter(x => x >= lo && x <= hi).length;
    if (ok < v.length) all = false;
    const g = x => x.toPrecision(3).padEnd(10);
    console.log(`${k.padEnd(7)} ${g(ref[k])} ${g(v.reduce((a, b) => a + b) / v.length)}  ${g(Math.min(...v))}  ${g(Math.max(...v))}  ${ok}/${v.length}`);
  }
  console.log(`strips used ${res[0].strips}, simulated clock ${res[0].hours.toFixed(2)} h`);
  return all;
}
{ // without the lid the log-log slope drops (solution: n about 0.47)
  const v = Array.from({ length: 30 }, (_, i) => { const s = newState(500 + i), p = drawParams(500 + i, true);
    for (const c of ['fill d1 water 30', 'place d1 open', 'dip d1']) exec(s, c, 'en', p);
    const A = [20, 35, 50, 65, 80, 95, 110, 125, 140, 150].map(mk => { exec(s, 'until d1 ' + mk, 'en', p); const r = s.records.at(-1); return [Math.log(r.t), Math.log(mk)]; });
    return fit(A.map(a => a[0]), A.map(a => a[1])).c; });
  console.log(`Open strip (no lid), part A procedure: n = ${(v.reduce((a, b) => a + b) / v.length).toFixed(3)} (range ${Math.min(...v).toFixed(3)}-${Math.max(...v).toFixed(3)}, 30 runs)`);
}
const okNom = batch('Paper values (nominal apparatus), different reading noise', Array.from({ length: 30 }, (_, i) => 1000 + i), true);
const okRnd = batch('Random apparatus per browser', Array.from({ length: 300 }, (_, i) => 7 + i * 7919), false);
console.log(okNom ? '\nPASS: nominal apparatus within all solution ranges' : '\nFAIL: nominal apparatus outside a range');
console.log(okRnd ? 'PASS: random apparatus within all solution ranges' : 'NOTE: some random apparatus outside a range (see table)');
process.exitCode = okNom ? 0 : 1;
