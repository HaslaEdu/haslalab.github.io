// The optical bench of sim/ipho2019_E1_web.html against the original Python
// (src/ipho2019_E1_sim_KO.py).  tests/fixtures/ipho2019-e1-python.json is the
// output of tests/fixtures/ipho2019-e1-oracle.py, which runs the original Lab
// and LabTab methods in CPython: the specimen of Lab(201901), ray traces of 26
// arrangements and the state after a sequence of handlers.
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const read = path => readFileSync(new URL('../' + path, import.meta.url), 'utf8');
const fixture = JSON.parse(read('tests/fixtures/ipho2019-e1-python.json'));
const html = read('sim/ipho2019_E1_web.html');
const block = html.slice(html.indexOf('/* ==== PHYSICS START'), html.indexOf('/* ==== PHYSICS END'));
const P = runInNewContext(block + ';({Lab, vis, TRAY_KEYS})', {Math, JSON});

const close = (actual, expected, path = 'value') => {
  if (typeof expected === 'number')
    return assert.ok(Math.abs(actual - expected) <= 1e-9 * Math.max(1, Math.abs(expected)), `${path}: ${actual} != ${expected}`);
  if (Array.isArray(expected)){
    assert.ok(Array.isArray(actual), path); assert.equal(actual.length, expected.length, path);
    return expected.forEach((entry, i) => close(actual[i], entry, `${path}[${i}]`));
  }
  if (expected && typeof expected === 'object') return Object.keys(expected).forEach(k => close(actual[k], expected[k], `${path}.${k}`));
  assert.equal(actual, expected, path);
};
/* a lab with the specimen the original drew for seed 201901 */
function lab(){
  const l = new P.Lab(7);
  Object.assign(l, structuredClone(fixture.specimen));
  return l;
}
const state = l => JSON.parse(JSON.stringify(Object.fromEntries(
  ['obj', 'order', 'slider', 'laser_fine', 'hold_rot', 'tape_on', 'tape_held', 'tape_a', 'tape_b', 'clock', 't', 'dark'].map(k => [k, l[k]]))));

test('the fixture is the output of the supplied original source', () => {
  assert.equal(createHash('sha256').update(readFileSync(new URL('../src/ipho2019_E1_sim_KO.py', import.meta.url))).digest('hex'), fixture.source_sha256);
  assert.equal(fixture.cases.length, 26);
});

test('the frozen fixture is still what the original prints', t => {
  const oracle = fileURLToPath(new URL('./fixtures/ipho2019-e1-oracle.py', import.meta.url));
  const run = ['python3', 'python'].map(py => spawnSync(py, [oracle], {encoding: 'utf8', maxBuffer: 1 << 26})).find(r => r.status === 0);
  if (!run) return t.skip('no Python on this machine');
  close(JSON.parse(run.stdout), fixture);
});

test('a new lab draws its specimen from the original ranges and starts with the tray full', () => {
  for (let seed = 1; seed < 60; seed++){
    const l = new P.Lab(seed);
    assert.ok(l.n_disk >= 1.505 && l.n_disk <= 1.524);
    assert.ok(l.n_prism >= 1.6395 && l.n_prism <= 1.6455);
    assert.ok(l.lam_over_d >= 0.3955 && l.lam_over_d <= 0.4045);
    assert.match(l.grating_id, /^#[1-9]\d\d$/);
    assert.ok(Math.abs(l.prism_eps.reduce((a, b) => a + b)) < 1e-12);
    assert.ok(Math.abs(l.prot_zero) <= 0.4);
    assert.ok(Object.values(l.obj).every(o => !o.on));
  }
  assert.deepEqual([...P.TRAY_KEYS], ['ruler', 'disk', 'holder', 'screen', 'tape6', 'tape', 'ruler8']);
});

for (const entry of fixture.cases) test(`ray trace matches the original: ${entry.input.name}`, () => {
  const l = lab(); l.laser_on = true;
  for (const [k, v] of Object.entries(entry.input.objects)) Object.assign(l.obj[k], structuredClone(v));
  for (const [k, v] of Object.entries(entry.input)) if (k !== 'name' && k !== 'objects') l[k] = v;
  l.clearPose();
  const t = l.trace();
  close({segs: t.segs, spots: t.spots, hits: t.hits, shots: t.shots}, entry.trace);
  assert.equal(t.shotSide.length, t.shots.length);
});

test('placing, dragging, turning, taping, the slider and the clock follow the original handlers', () => {
  const l = lab(), out = [];
  for (const [k, c] of [['ruler', [136, 170]], ['disk', [136, 150]], ['holder', [136, 96]], ['screen', [136, 100]], ['tape6', [40, 60]]]){
    l.toggle(k, c); out.push(state(l)); }
  l.side = l.screen_side('disk'); l.dragTo('disk', 142, 112); l.side = 0; out.push(state(l));
  l.turn('disk', true, false); out.push(state(l));
  l.turn('holder12b', false, true); out.push(state(l));
  l.turn('laser', true, true); out.push(state(l));
  l.tape_held = true;
  let [x, y] = l.pose('disk'); l.stick_tape(x - 5, y); out.push(state(l));
  [x, y] = l.pose('disk'); l.stick_tape(x + 5, y); out.push(state(l));
  assert.equal(l.turn('disk', true, false), false); out.push(state(l));
  [x, y] = l.pose('ruler'); l.stick_tape(x - 20, y); l.stick_tape(x + 20, y); l.stick_tape(x + l.slider + 2, y); out.push(state(l));
  l.dragSlider(x + 25, y); out.push(state(l));
  l.dragSlider(x - 25, y); out.push(state(l));
  l.tick(18.1, 10); out.push(state(l));
  l.tick(3.0, 10); out.push(state(l));
  close(out, fixture.handlers);
  assert.equal(l.dark, true);
});

test('visibility of a spot in the lit hall and in the dark is the original rule', () => {
  assert.equal(P.vis(1, false), 0.8); assert.equal(P.vis(0.019, false), 0);
  assert.equal(P.vis(0.00009, true), 0); assert.equal(P.vis(1, true), 1);
  assert.ok(Math.abs(P.vis(0.05, false) - 0.05 ** 0.42 * 0.8) < 1e-15);
});

test('the transparent ruler covers the path only when it lies on top of the disk', () => {
  const l = lab();
  Object.assign(l.obj.disk, {on: true, pos: [136, 96], ang: 270, tapes: [[-12, -2], [12, 2]]});
  Object.assign(l.obj.ruler8, {on: true, pos: [136, 96], ang: 90, tapes: [[-12, -1], [12, 1]]});
  l.order = l.order.filter(k => k !== 'ruler8').concat('ruler8'); l.clearPose();
  assert.equal(l.in_ruler8(136, 96), true);
  l.order = ['ruler8', ...l.order.filter(k => k !== 'ruler8')]; l.clearPose();
  assert.equal(l.in_ruler8(136, 96), false);
});
