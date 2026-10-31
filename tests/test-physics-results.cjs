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

test('component medal references use cumulative actual award counts on the same-round scores', () => {
  let references = 0;
  for (const comp of Object.values(data.competitions)) for (const r of comp.records) {
    const ref = r.medalReference;
    if (!ref) continue;
    references++;
    assert.ok(['theory', 'experiment'].includes(r.scope), r.id);
    assert.equal(r.awardScope, false);
    assert.equal(r.medalCutoffs, undefined, 'reference bands are separate from actual contest medals');
    assert.equal(ref.basis, 'round_rank');
    assert.equal(ref.population, r.complete ? 'complete' : 'published');
    assert.ok(ref.sources.length > 0 && ref.sources.every(s => /^https?:\/\//.test(s.url) && typeof s.official === 'boolean'));
    const descending = [...r.scores].sort((a, b) => b - a);
    let cumulative = 0;
    for (const tier of ['gold', 'silver', 'bronze']) {
      assert.ok(Number.isInteger(ref.counts[tier]) && ref.counts[tier] >= 0);
      cumulative += ref.counts[tier];
      assert.ok(cumulative <= r.scores.length);
      if (ref.counts[tier]) {
        assert.equal(ref.cuts[tier], descending[cumulative - 1], r.id + ':' + tier);
        assert.ok(descending.filter(s => s >= ref.cuts[tier]).length >= cumulative, 'ties remain on the boundary');
      } else assert.equal(ref.cuts[tier], undefined);
    }
    assert.ok(cumulative > 0);
    assert.equal(ref.counts.hm, undefined);
  }
  assert.equal(references, 36);
});

test('all nine scored IPhO editions keep reference and official total medal thresholds distinct', () => {
  const expected = {
    2012: [45, 71, 92], 2015: [38, 64, 93], 2016: [47, 74, 98],
    2018: [42, 69, 99], 2021: [45, 61, 94], 2022: [39, 71, 97],
    2023: [37, 74, 103], 2024: [18, 35, 53], 2025: [37, 81, 96],
  };
  for (const [yearText, values] of Object.entries(expected)) {
    const year = Number(yearText);
    for (const scope of ['theory', 'experiment']) {
      const r = get('ipho', year, scope);
      assert.deepEqual(r.medalReference.counts, Object.fromEntries(['gold', 'silver', 'bronze'].map((k, i) => [k, values[i]])));
      assert.equal(r.medalReference.population, [2012, 2022].includes(year) ? 'complete' : 'published');
    }
    assert.equal(get('ipho', year, 'total').medalReference, undefined);
  }
  assert.equal(get('ipho', 2025, 'theory').medalReference.cuts.gold, 20.8);
  assert.equal(get('ipho', 2025, 'experiment').medalReference.cuts.gold, 10.5);
  assert.equal(get('ipho', 2025, 'total').medalCutoffs.gold, 31.1);
});

test('source-specific medal labels supply counts only when all award categories are verified', () => {
  for (const scope of ['theory', 'experiment']) {
    assert.deepEqual(get('apho', 2025, scope).medalReference.counts, {gold: 28, silver: 37, bronze: 59}, 'official Bronz spelling must be recognized');
    assert.equal(get('apho', 2025, scope).medalReference.population, 'published');
    assert.deepEqual(get('eupho', 2020, scope).medalReference.counts, {gold: 27, silver: 49, bronze: 60}, '2020 has explicit medal-section headings');
    assert.equal(get('eupho', 2020, scope).medalReference.population, 'published');
    assert.deepEqual(get('eupho', 2026, scope).medalReference.counts, {gold: 23, silver: 37, bronze: 51});
    for (const year of [2021, 2022, 2025]) {
      assert.equal(get('eupho', year, scope).medalReference, undefined);
      assert.ok(data.competitions.eupho.coverage.medalReferenceOmitted[String(year)]);
    }
  }
  const receipts = JSON.parse(fs.readFileSync(path.join(root, 'tools/results/physics-receipts.json'), 'utf8'));
  assert.equal(receipts.medalReferences.length, 36);
  assert.ok(receipts.medalReferences.every(r => r.tieRule.includes('same reference band')));
});

test('IPhO rounds with a published award floor get exact full-field round ranks above that floor only', () => {
  const comparison = require('../sim/result-comparison.js');
  const ipho = JSON.parse(fs.readFileSync(path.join(root, 'sim/results/ipho.json'), 'utf8'));
  const round = (year, scope) => ipho.records.find(r => r.year === year && r.scope === scope);
  for (const year of [2025, 2024, 2023, 2021, 2016]) for (const scope of ['theory', 'experiment']) {
    const r = round(year, scope), coverage = comparison.componentFloor(ipho.records, r);
    const total = ipho.records.find(t => t.year === year && t.scope === 'total');
    assert.ok(coverage, `${year} ${scope}`);
    assert.equal(coverage.floor, total.rankFloor);
    assert.equal(r.scores.length, total.scores.length, 'the round scores belong to the same published contestants');
    const top = comparison.evaluate(r, r.max, false, coverage), low = comparison.evaluate(r, 0, false, coverage);
    assert.equal(top.bounded, true); assert.equal(top.rank, 1); assert.equal(top.fieldSize, r.participants);
    assert.equal(low.bounded, false);
  }
  // 2015 omits one inconsistent pair from its rounds; 2018 has no published award floor; 2012/2022 are complete.
  for (const year of [2015, 2018, 2012, 2022]) for (const scope of ['theory', 'experiment'])
    assert.equal(comparison.componentFloor(ipho.records, round(year, scope)), null, `${year} ${scope}`);
  const session = {id: 1, comp: 'ipho', year: 2025, status: 'graded', score: 22, points: 30, tasks: ['T1', 'T2', 'T3'], kind: 'theory'};
  const [e] = comparison.assess(ipho, session).comparisons;
  assert.equal(e.record.id, 'ipho-2025-theory');
  assert.equal(e.bounded, true); assert.equal(e.reference.medal, 'gold'); assert.equal(e.reference.fullField, true);
  assert.equal(e.top_pct, null, 'the disputed 2025 entrant count still suppresses a percentile');
  assert.match(comparison.resultHtml(e, 'ko'), /전체 참가자 기준/);
});
