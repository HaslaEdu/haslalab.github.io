const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const data = JSON.parse(fs.readFileSync(path.join(root, 'tools/results/physics.json'), 'utf8'));
const get = (comp, year, scope) => data.competitions[comp].records.find(r => r.year === year && r.scope === scope);

test('physics distributions retain valid tied scores and distinguish full populations', () => {
  const ids = new Set();
  for (const comp of Object.values(data.competitions)) for (const r of comp.records) {
    assert.ok(!ids.has(r.id), r.id); ids.add(r.id);
    assert.equal(r.population, 'individual');
    assert.ok(r.sources.length && r.sources.every(s => /^https?:\/\//.test(s.url)));
    assert.ok(r.scores.every((s, i, a) => Number.isFinite(s) && s >= 0 && s <= r.max && (i === 0 || a[i - 1] <= s)), r.id);
    if (r.complete) assert.equal(r.scores.length, r.participants, r.id);
    if (r.medalCutoffs) {
      assert.equal(r.awardScope, true, r.id);
      assert.ok(['published', 'observed'].includes(r.cutoffKind));
    }
  }
});

test('public IPhO workbooks restore all anonymous scores without treating partial experiments as complete', () => {
  for (const [year, n] of [[2012, 378], [2022, 368]]) {
    for (const scope of ['theory', 'experiment', 'total']) {
      const r = get('ipho', year, scope);
      assert.equal(r.complete, true); assert.equal(r.scores.length, n);
      assert.ok(r.sources.some(s => /Results\.xlsx$/.test(s.url) && s.official === false), 'archive mirror must be labeled');
    }
  }
  const exp = get('ipho', 2024, 'experiment');
  assert.equal(exp.max, 20);
  assert.deepEqual(exp.taskSets, [['E1', 'E2']]);
  assert.equal(exp.awardScope, false);
  assert.equal(exp.medalCutoffs, undefined);
  assert.deepEqual(get('ipho', 2024, 'total').components[1].taskSets, [['E1', 'E2']]);
});

test('IPhO published total thresholds and incomplete-score limitations are preserved', () => {
  assert.deepEqual(get('ipho', 2012, 'total').medalCutoffs, {gold: 31, silver: 23.9, bronze: 17.2, hm: 12.4});
  const total = get('ipho', 2025, 'total');
  assert.deepEqual(total.medalCutoffs, {gold: 31.1, silver: 22.9, bronze: 15.3, hm: 11.3});
  assert.equal(total.rankFloor, 11.3);
  assert.equal(total.complete, false);
  assert.equal(total.participantCountUncertain, true);
  assert.equal(get('ipho', 2025, 'theory').rankFloor, undefined);
  assert.equal(get('ipho', 2015, 'total').scores.length, 263);
  assert.equal(get('ipho', 2015, 'theory').scores.length, 262, 'inconsistent source pair must not be silently repaired');
  assert.equal(get('ipho', 2018, 'total').cutoffKind, 'observed');
  assert.equal(get('ipho', 2018, 'total').medalCutoffs.hm, undefined);
});

test('EuPhO complete tables and ambiguous zero rows have different coverage', () => {
  assert.equal(get('eupho', 2026, 'theory').scores.length, 199);
  assert.deepEqual(get('eupho', 2026, 'experiment').taskSets, [['E1']]);
  assert.equal(get('eupho', 2026, 'experiment').max, 20);
  assert.deepEqual(get('eupho', 2026, 'total').medalCutoffs, {gold: 25.2, silver: 16.5, bronze: 11.4, hm: 7.5});
  assert.equal(get('eupho', 2020, 'theory').scores.length, 260);
  assert.equal(get('eupho', 2020, 'theory').complete, false);
  assert.equal(get('eupho', 2020, 'theory').participants, null);
  assert.equal(get('eupho', 2019, 'theory'), undefined);
  for (const year of [2020, 2021, 2022, 2025])
    assert.equal(get('eupho', year, 'total').medalCutoffs, undefined, 'color-only or special-prize labels must not become scalar medal cutoffs');
});

test('NBPhO full mixed sittings require both experiments and theory, with published maxima', () => {
  for (const year of [2022, 2023, 2024, 2025, 2026]) {
    const r = get('nbpho', year, 'round');
    assert.equal(r.max, 72);
    assert.deepEqual(r.taskSets, [['E1', 'E2', 'T']]);
  }
  assert.equal(get('nbpho', 2024, 'round').participants, 104);
  assert.equal(get('nbpho', 2025, 'round').scores.length, 105, 'a contestant named Max is not a maximum-score heading');
  assert.equal(get('nbpho', 2020, 'round').max, 36.5);
  assert.equal(Math.max(...get('nbpho', 2020, 'round').scores), 32.4, 'printed maximum heading is not a contestant');
  assert.equal(get('nbpho', 2021, 'round').max, 36);
  assert.equal(get('nbpho', 2021, 'round').medalCutoffs, undefined, 'out-of-ranking guest exceptions make scalar cutoffs unsafe');
  assert.equal(get('nbpho', 2026, 'round').complete, false);
  assert.equal(get('nbpho', 2026, 'theory').taskSets, undefined, 'the T skip-list changes its scope');
  assert.deepEqual(get('nbpho', 2026, 'experiment').taskSets, [['E1', 'E2']]);
});

test('APhO awardee tables cannot claim full-field component percentiles', () => {
  assert.equal(get('apho', 2017, 'total').scores.length, 167);
  assert.equal(get('apho', 2017, 'total').complete, true);
  for (const [year, count] of [[2025, 169], [2026, 161]]) {
    assert.equal(get('apho', year, 'total').scores.length, count);
    assert.equal(get('apho', year, 'total').complete, false);
    assert.equal(get('apho', year, 'total').cutoffKind, 'observed');
    assert.equal(get('apho', year, 'theory').medalCutoffs, undefined);
  }
});
