// Drives the simulated bench the way the official solution does and checks the results against
// the solution's accepted ranges. Run: node sim/hpho-mock1-e2/check.mjs [draws]
import {Lab, defaultParams, drawParams, initialState, G, LAMBDA} from './model.mjs';

function student(params, seed) {
  const lab = new Lab(params, initialState(seed), 'en');
  const run = c => { const r = lab.exec(c); if (!r.ok) throw Error(c + ': ' + r.text); return r.text; };
  const bright = t => Number(/Brightness I = (\d+)/.exec(t)?.[1] ?? /\n\s*\S+\s+\S+\s+(\d+)/.exec(t)[1]);
  const watchTot = () => ({dark: lab.S.watch.dark, bright: lab.S.watch.bright});
  const order = (I, w) => { const f0 = Math.asin(Math.sqrt(Math.min(1, I / 100))) / Math.PI; return w.dark + (w.bright > w.dark ? 1 - f0 : f0); };
  const fit = (xs, ys) => { const n = xs.length, mx = xs.reduce((a, b) => a + b) / n, my = ys.reduce((a, b) => a + b) / n;
    let sxx = 0, sxy = 0; xs.forEach((x, i) => { sxx += (x - mx) ** 2; sxy += (x - mx) * (ys[i] - my); });
    const s = sxy / sxx, b = my - s * mx, res = ys.map((y, i) => y - s * xs[i] - b), se = Math.sqrt(res.reduce((a, r) => a + r * r, 0) / (n - 2) / sxx);
    return {s, b, se}; };
  const R = {};

  // A.1: rotate the analyzer, find the ends of the dark range, take the middle.
  run('mount none');
  const dark = [];
  for (let a = 70; a <= 110; a++) { run('analyzer ' + a); if (bright(run('look')) <= 2) dark.push(a); }
  R.A1 = (dark[0] + dark.at(-1)) / 2;
  run('analyzer ' + R.A1);

  // A.2: no-load order of the tension specimen from its brightness in the circular polariscope.
  run('mount tension'); run('qwp on');
  const I0 = bright(run('read 0 0'));
  R.N0 = Math.asin(Math.sqrt(I0 / 100)) / Math.PI;

  // B: count fringes passing the centre while loading, fraction from brightness.
  const b1 = Number(/= ([\d.]+)/.exec(run('measure width'))[1]);
  run('watch 0 0'); run('hanger on');
  const F = [], N = [];
  for (const g of [450, 950, 1450, 1950, 2450, 2950]) {
    run('load ' + g); run('wait 2 min');
    const I = bright(run('read 0 0'));
    F.push((g + 50) / 1000 * G); N.push(order(I, watchTot()));
  }
  const fb = fit(F, N);
  R.B_slope = fb.s; R.B_intercept = fb.b;
  R.fs_B = 1 / (b1 / 1000 * fb.s); R.dfs_B = R.fs_B * fb.se / fb.s; R.C = LAMBDA / R.fs_B;
  run('load 0'); run('hanger off');

  // C: cantilever, 100 g on a thread, section 60 mm from the loading notch.
  run('mount beam');
  const arm = Number(/= ([\d.]+)/.exec(run('measure arm'))[1]);
  const h = Number(/= ([\d.]+)/.exec(run('measure width'))[1]);
  const xs = Math.round(arm - 60);
  run('load 100'); run('wait 2 min');
  const pos = run('fringes x ' + xs).split('\n').slice(2).map(l => Number(l.trim().split(/\s+/)[1]));
  const mid = pos.reduce((k, p, i) => Math.abs(p - h / 2) < Math.abs(pos[k] - h / 2) ? i : k, 0);
  const ords = pos.map((_, i) => i - mid);
  const fc = fit(pos.map(p => p / 1000), ords);
  R.C_points = pos.length; R.y_NA = -fc.b / fc.s * 1000; R.y_NA_offset = R.y_NA - h / 2;
  const M = 0.100 * G * 0.060;
  R.fs_C = 12 * M / ((h / 1000) ** 3 * fc.s);
  run('load 0');

  // D: specimen with hole, 2.0 kg in total.
  run('mount hole');
  const d = Number(/= ([\d.]+)/.exec(run('measure hole'))[1]), a = d / 2;
  run('watch 50 0'); run('hanger on'); run('load 1950'); run('wait 2 min');
  R.Ninf = order(bright(run('read 50 0')), watchTot());
  // static count along x = 0 from the side edge inward: the outermost fringe is order floor(Ninf)+1
  const st = run(`fringes x 0 ${a} 15`).split('\n').slice(2).length;
  R.Nedge_static = Math.floor(R.Ninf) + st + 0.3; R.Kt_static = R.Nedge_static / R.Ninf;
  // counting while loading at a point just outside the machined surface, then a short extrapolation
  // to the edge with the local fringe spacing taken from the static fringe list
  const s0 = 0.15;
  run('load 0'); run('hanger off'); run('wait 5 min');
  run(`watch 0 ${(a + s0).toFixed(2)}`); run('hanger on'); run('load 1950'); run('wait 2 min');
  const t = run(`read 0 ${(a + s0).toFixed(2)}`), w = watchTot();
  R.N_near = /dense/.test(t) ? w.dark + (w.bright > w.dark ? 0.75 : 0.25) : order(bright(t), w);
  const near = run(`fringes x 0 ${a} ${a + 1}`).split('\n').slice(2).map(l => Number(l.trim().split(/\s+/)[1]));
  const spacing = near.length > 1 ? (near.at(-1) - near[0]) / (near.length - 1) : 0.12;
  R.Nedge_count = R.N_near + s0 / spacing; R.Kt_count = R.Nedge_count / R.Ninf;
  R.clock = lab.S.clock; R.records = lab.S.records.length;
  return R;
}

const ranges = {A1: [88, 92], fs_B: [150, 260], C: [2.1e-9, 3.6e-9], fs_C: [140, 280], y_NA_offset: [-1, 1], Kt_static: [2.4, 3.4], Kt_count: [2.4, 3.4]};
const inside = R => Object.fromEntries(Object.entries(ranges).map(([k, [lo, hi]]) => [k, R[k] >= lo && R[k] <= hi]));

const def = student(defaultParams(), 7);
console.log('Default parameters (fs = 200 N/m, Kt = 3.14):');
for (const [k, v] of Object.entries(def)) console.log('  ' + k.padEnd(14) + (typeof v === 'number' ? (Math.abs(v) < 1e-3 && v !== 0 ? v.toExponential(3) : v.toFixed(3)) : v) + (ranges[k] ? `   range ${ranges[k].join('..')}  ${inside(def)[k] ? 'OK' : 'OUT'}` : ''));
const draws = Number(process.argv[2] || 200), pass = Object.fromEntries(Object.keys(ranges).map(k => [k, 0]));
for (let i = 0; i < draws; i++) { const seed = (i * 7919 + 17) >>> 0, R = student(drawParams(seed), seed ^ 99), ok = inside(R); for (const k in ok) pass[k] += ok[k]; }
console.log(`Random apparatus draws: ${draws}`);
for (const k in pass) console.log('  ' + k.padEnd(14) + `${pass[k]}/${draws} inside`);
const fail = Object.values(inside(def)).some(v => !v);
process.exit(fail ? 1 : 0);
