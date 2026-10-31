// The blackbox of sim/ipho2011_E1_web.html, solved the way the official
// solution of IPhO 2011 Experimental Problem 1 solves it: calibrate with the
// capacitors of Table 1, read f against the plate position, convert to C,
// and take the step of the peaks per node and the resolution at 5 kHz.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';

const html = readFileSync(new URL('../sim/ipho2011_E1_web.html', import.meta.url), 'utf8');
const block = html.slice(html.indexOf('/* ==== PHYSICS START'), html.indexOf('/* ==== PHYSICS END'));
const P = runInNewContext(block + ';({Kit, CAPS, C_blackbox})', {Math, Date, Set, Object});

/* the official C-x table, from f with alpha = 714 nF/s and Cs = 17.9 pF */
const OFFICIAL_F = [7.41, 8.09, 8.64, 9.30, 9.30, 8.21, 7.02, 6.40, 5.98, 5.91, 6.38, 6.96, 7.61, 8.40, 8.20, 7.13, 6.37, 5.96, 5.38, 5.33,
  5.72, 6.34, 6.85, 7.53, 7.23, 6.33, 5.56, 5.36, 4.73, 4.53, 4.94, 5.52, 6.19, 6.48, 6.64, 5.72, 5.08, 4.39, 4.06, 3.97, 4.32, 4.86,
  5.33, 6.05, 5.98, 5.14, 4.47, 3.93, 3.74, 3.64, 3.93, 4.30, 4.91, 5.46, 5.49, 4.64, 4.07, 3.62, 3.36];
const fit = (X, Y) => { const n = X.length, mx = X.reduce((a, b) => a + b) / n, my = Y.reduce((a, b) => a + b) / n;
  let sxy = 0, sxx = 0; X.forEach((x, i) => { sxy += (x - mx) * (Y[i] - my); sxx += (x - mx) ** 2; }); const k = sxy / sxx; return [k, my - k * mx]; };

function bench(){
  const k = new P.Kit(7);
  Object.assign(k, {battV: 9.3, sw: true, dial: 'hz', jit: 0});
  k.snap = {p: 'BINP', n: 'BINN'}; k.probe = {r: 'JR', b: 'JB'};
  return k;
}
const read = k => parseFloat(k.display());

test('the meter reads nothing until the oscillator is wired, switched on and the dial is on Hz', () => {
  const k = bench();
  k.sw = false; assert.equal(k.display(), '0.00'); k.sw = true;
  k.snap.n = null; assert.equal(k.display(), '0.00'); k.snap.n = 'BINN';
  k.probe.b = 'BATN'; assert.equal(k.display(), '0.00'); k.probe.b = 'JB';
  assert.ok(read(k) > 3 && read(k) < 10);
});

test('a flat battery reads below 9 V on the 20 V range and slows, then stops, the oscillator', () => {
  const k = bench(); k.probe = {r: 'BATP', b: 'BATN'}; k.dial = 'v20'; k.battV = 8.2;
  assert.equal(k.display(), '8.20');
  k.probe = {r: 'JR', b: 'JB'}; k.dial = 'hz'; const slow = read(k); k.battV = 9.3;
  assert.ok(slow < read(k)); k.battV = 7.0; assert.equal(k.display(), '0.00');
});

let alpha, Cs;
test('Part 1: 1/f against C of Table 1 (and parallel pairs) gives the official alpha and C_s', () => {
  const k = bench(), X = [], Y = [];
  for (const set of [[0], [1], [2], [3], [3, 2], [3, 1], [3, 0], [2, 0], [1, 0]]){
    k.caps = {}; k.stack = {};
    set.forEach((i, j) => { k.caps[i] = [0, 0]; if (j) k.stack[i] = set[0]; });
    k.clip = {r: 'A' + set[0], b: 'B' + set[0]};
    X.push(set.reduce((s, i) => s + P.CAPS[i][1], 0)); Y.push(1 / read(k));
  }
  const [s, b] = fit(X, Y); alpha = 1 / s; Cs = b / s;        /* pF kHz, pF */
  assert.ok(Math.abs(alpha - 714) < 15, `alpha ${alpha}`);
  assert.ok(Math.abs(Cs - 17.9) < 2, `Cs ${Cs}`);
});

test('Part 2: f against x follows the official table and the peaks of C step 19.9 pF per node (b = 60 mm)', () => {
  const k = bench(), f = [], C = [];
  for (let x = 0; x <= 58; x++){ k.slide = x; f.push(read(k)); C.push(alpha / f[x] - Cs); }
  const rms = Math.sqrt(f.reduce((s, v, i) => s + (v - OFFICIAL_F[i]) ** 2, 0) / f.length);
  assert.ok(rms < 0.45, `rms against the official f column ${rms}`);
  const peaks = []; for (let i = 1; i < C.length - 1; i++) if (C[i] > C[i - 1] && C[i] >= C[i + 1]) peaks.push([i, C[i]]);
  assert.deepEqual(peaks.map(p => p[0]), [9, 19, 29, 39, 49]);
  const step = fit(peaks.map((_, i) => i + 1), peaks.map(p => p[1]))[0];
  assert.ok(Math.abs(step - 19.9) < 0.6, `step ${step}`);
  const b = step * 1e-12 * 0.20e-3 / (1.5 * 8.85e-12 * 5e-3) * 1e3;
  assert.ok(Math.abs(b - 60) < 2, `b ${b} mm`);
});

test('Part 3: the resolution at 5 kHz is about 0.016 mm', () => {
  const k = bench(); let x0 = 0, best = 1e9;
  for (let x = 1; x < 58; x++){ k.slide = x; const d = Math.abs(read(k) - 5); if (d < best){ best = d; x0 = x; } }
  const C = x => { k.slide = x; return alpha / read(k) - Cs; };
  const m = Math.abs(C(x0 + 1) - C(x0 - 1)) / 2;            /* pF per mm */
  const dx = alpha / (m * 25) * 0.01;                         /* mm, for 0.01 kHz */
  assert.ok(dx > 0.012 && dx < 0.022, `dx ${dx}`);
});
