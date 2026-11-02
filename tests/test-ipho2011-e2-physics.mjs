// The tube of sim/ipho2011_E2_web.html (the official apparatus, seed 20110714),
// solved the way the official solution of IPhO 2011 Experimental Problem 2
// does: balance it for x_CM, time small swings on every hole, plot T^2 R
// against R^2 (method a), and get g, I_CM/(M+m), z and M/m.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

const html = readFileSync(new URL('../sim/ipho2011_E2_web.html', import.meta.url), 'utf8');
const block = html.slice(html.indexOf('/* ==== PHYSICS START'), html.indexOf('/* ==== PHYSICS END'));
const ctx = {Math, Number, String, Object, Array, T: {ko: new Proxy({}, {get: () => 'x'})}, lang: 'ko'};
runInNewContext(block + ';this.makeTruth = makeTruth; this.makeRig = makeRig; this.OFFICIAL_SEED = OFFICIAL_SEED;', ctx);
const truth = ctx.makeTruth(ctx.OFFICIAL_SEED);
const fit = (X, Y) => { const n = X.length, mx = X.reduce((a, b) => a + b) / n, my = Y.reduce((a, b) => a + b) / n;
  let sxy = 0, sxx = 0; X.forEach((x, i) => { sxy += (x - mx) * (Y[i] - my); sxx += (x - mx) ** 2; }); const k = sxy / sxx; return [k, my - k * mx]; };

test('the official tube: L = 30 cm, holes from 1.1 cm every 1 cm, x_CM = 17.8 cm', () => {
  assert.equal(truth.L, 0.30);
  assert.equal(truth.holes.length, 16);
  assert.ok(Math.abs(truth.holes[0] - 0.011) < 1e-9 && Math.abs(truth.holes[15] - 0.161) < 1e-9);
  assert.ok(Math.abs(truth.x_cm * 100 - 17.8) < 0.05);
});

test('in the thread loop the tube is level only at the centre of mass', () => {
  const rig = ctx.makeRig(truth); rig.enter_part_a();
  for (const [x, want] of [[truth.x_cm, 'level'], [truth.x_cm - 0.01, 'bottom_down'], [truth.x_cm + 0.01, 'top_down']]){
    rig.hold(true); rig.drag_loop_to(x); rig.hold(false);
    for (let i = 0; i < 400; i++) rig.step(0.004);
    assert.equal(rig.bench_readout().tilt_view, want, `loop at ${x}`);
  }
});

test('method (a): T^2 R against R^2 gives g, and with x_CM the official z and M/m', () => {
  const rig = ctx.makeRig(truth), X = [], Y = [];
  truth.holes.forEach((h, i) => {
    rig.resetAll(); rig.enter_part_b(); rig.mount_on_pin(i); rig.pull_aside(6); rig.release();
    let t = 0, prev = rig.theta; const cross = [];
    while (cross.length < 21 && t < 120){ rig.step(0.001); t += 0.001; if (prev < 0 && rig.theta >= 0) cross.push(t); prev = rig.theta; }
    const T = (cross[20] - cross[0]) / 20, R = (truth.x_cm - h) * 100;
    X.push(R * R); Y.push(T * T * R);
  });
  const [s, b] = fit(X, Y), g = 4 * Math.PI ** 2 / s, r = b / s;
  assert.ok(Math.abs(g - 978) < 6, `g ${g} cm/s^2`);
  assert.ok(Math.abs(r - 75.46) < 1.0, `I_CM/(M+m) ${r} cm^2`);
  const L = 30, xcm = 17.8, c = xcm - L / 2, Q = L * L / 12 + c * c;
  const u = (-(Q - r) / c + Math.sqrt(((Q - r) / c) ** 2 + 4 * r)) / 2;
  assert.ok(Math.abs(xcm + u - 25.3) < 0.4, `z ${xcm + u}`);
  assert.ok(Math.abs(u / c - 2.7) < 0.15, `M/m ${u / c}`);
});
