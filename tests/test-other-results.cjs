const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const json = file => JSON.parse(fs.readFileSync(path.join(root, file), 'utf8'));
const data = json('tools/results/other.json');
const records = comp => data.competitions[comp].records;
const find = id => Object.values(data.competitions).flatMap(comp => comp.records).find(record => record.id === id);

test('IMO preserves all held editions, historical scoring maxima and duplicate and zero scores', () => {
  const editions = records('imo');
  const years = Array.from({length: 68}, (_, i) => 1959 + i).filter(year => year !== 1980);
  assert.deepEqual(editions.map(record => record.year).sort((a, b) => a - b), years);
  assert.equal(find('imo-1959-total').max, 40);
  assert.equal(find('imo-1960-total').max, 44);
  const recent = find('imo-2025-total');
  assert.equal(recent.max, 42);
  assert.deepEqual(recent.medalCutoffs, {gold: 35, silver: 28, bronze: 19});
  assert.equal(recent.participants, 630);
  assert.equal(recent.scores.filter(score => score === 42).length, 5);
  assert.ok(recent.scores.includes(0));
  for (const record of editions) {
    assert.equal(record.complete, true, String(record.year));
    assert.equal(record.scores.length, record.participants, String(record.year));
    assert.equal(record.medalCutoffs.hm, undefined, 'a total cannot determine an honourable mention');
  }
});

test('automatic historical comparisons name exact published complete papers', () => {
  for (const [key, competition] of Object.entries(data.competitions)) {
    const manifest = json(`tools/theory/${key}.json`);
    for (const record of competition.records) {
      for (const tasks of record.taskSets || []) {
        const annual = manifest.years.find(year => year.y === record.year);
        assert.ok(annual, record.id);
        const papers = new Set(annual.files.filter(file => file.kind === 'paper').map(file => file.part));
        assert.ok(tasks.every(task => papers.has(task)), record.id);
      }
    }
  }
  assert.deepEqual(find('imo-2025-total').taskSets, [['T']]);
  assert.deepEqual(find('ioaa-2025-theory').taskSets, [['T']]);
});

test('IOAA 2025 keeps theory, practical and medal totals separate and does not invent an HM threshold', () => {
  const theory = find('ioaa-2025-theory'), practical = find('ioaa-2025-practical'), total = find('ioaa-2025-total');
  assert.equal(theory.max, 300);
  assert.equal(practical.max, 300);
  assert.equal(total.max, 600);
  for (const record of [theory, practical, total]) {
    assert.equal(record.participants, 288);
    assert.equal(record.scores.length, 288);
    assert.equal(record.complete, true);
  }
  for (const component of [theory, practical]) {
    assert.equal(component.awardScope, false);
    assert.equal(component.medalCutoffs, undefined);
  }
  assert.equal(total.awardScope, true);
  assert.equal(total.cutoffKind, 'observed');
  assert.deepEqual(total.medalCutoffs, {gold: 279, silver: 223.5, bronze: 174});
  assert.deepEqual(total.components.map(component => component.max), [300, 300]);
  assert.equal(total.taskSets, undefined, 'theory alone must not auto-match the full competition');
});

test('IBO 2024 compares raw complete theory papers without applying standardized combined medals', () => {
  const theory = find('ibo-2024-theory'), a = find('ibo-2024-theory-a'), b = find('ibo-2024-theory-b');
  assert.deepEqual(theory.taskSets, [['T1', 'T2']]);
  assert.deepEqual(a.taskSets, [['T1']]);
  assert.deepEqual(b.taskSets, [['T2']]);
  assert.equal(theory.max, 100);
  assert.equal(a.max, 50);
  assert.equal(b.max, 50);
  for (const record of [theory, a, b]) {
    assert.equal(record.participants, 286);
    assert.equal(record.scores.length, 286);
    assert.equal(record.awardScope, false);
    assert.equal(record.medalCutoffs, undefined);
    assert.ok(record.sources.some(source => source.url.includes('amended%20version%20January%202025')));
  }
  const sum = record => record.scores.reduce((a, b) => a + b, 0);
  assert.ok(Math.abs(sum(a) + sum(b) - sum(theory)) < 1e-6, 'both raw components reconcile with the full theory population');
});

test('complete round reference bands use official overall award counts on the same-round score distribution', () => {
  const receipts = json('tools/results/other-receipts.json');
  for (const [id, counts] of [
    ['ioaa-2025-theory', {gold: 49, silver: 44, bronze: 49}],
    ['ioaa-2025-practical', {gold: 49, silver: 44, bronze: 49}],
    ['ibo-2024-theory', {gold: 31, silver: 57, bronze: 85}]
  ]) {
    const record = find(id), reference = record.medalReference;
    assert.equal(reference.basis, 'round_rank');
    assert.equal(reference.population, 'complete');
    assert.deepEqual(reference.counts, counts);
    assert.equal(record.complete, true);
    assert.equal(record.scores.length, record.participants);
    assert.equal(record.awardScope, false);
    assert.equal(record.medalCutoffs, undefined, 'a round reference is not an official award boundary');
    let cumulative = 0;
    const scores = [...record.scores].sort((a, b) => b - a);
    for (const award of ['gold', 'silver', 'bronze']) {
      cumulative += counts[award];
      assert.equal(reference.cuts[award], scores[cumulative - 1], `${id} ${award} uses this round's score boundary`);
    }
    assert.ok(reference.sources.every(source => source.official && source.url.startsWith('https://')));
    assert.ok(receipts.files.some(file => [file.theoryMedalReference, file.practicalMedalReference].some(value => value &&
      JSON.stringify(value) === JSON.stringify(reference))), 'the import receipt records the source-backed projection');
    assert.match(record.note.en, /reference.*not official|reference.*not.*official|not official.*reference/i);
  }
  assert.equal(find('ibo-2024-theory-a').medalReference, undefined, 'a half-paper is not the complete theory round');
  assert.equal(find('ibo-2024-theory-b').medalReference, undefined);
});

test('IESO preserves published raw totals only for explicit manual comparison and omits misleading medal minima', () => {
  const record = find('ieso-2026-total');
  assert.equal(record.manualOnly, true);
  assert.equal(record.max, null);
  assert.deepEqual(record.taskSets, []);
  assert.equal(record.components, undefined);
  assert.equal(record.participants, 151);
  assert.equal(record.complete, true);
  assert.equal(record.scores.length, 151);
  assert.equal(record.scores[0], 89.063);
  assert.equal(record.scores.filter(score => score === 85.58).length, 2);
  assert.equal(record.awardScope, false);
  assert.equal(record.medalCutoffs, undefined);
});

test('unavailable Junior score data stays explicit and every imported record has a unique anonymous identity', () => {
  assert.deepEqual(records('ioaajr'), []);
  assert.ok(data.competitions.ioaajr.coverage.sources.some(source => source.url === 'https://www.ioaajr2025.ro/results'));
  assert.match(data.competitions.ioaajr.coverage.limitations.en, /not numeric marklists/);
  const ids = new Set();
  for (const [comp, competition] of Object.entries(data.competitions)) {
    for (const record of competition.records) {
      assert.ok(record.id.startsWith(comp + '-'));
      assert.equal(ids.has(record.id), false, record.id);
      ids.add(record.id);
      assert.ok(record.scores.every(score => typeof score === 'number' && Number.isFinite(score)));
      assert.ok(!('names' in record) && !('countries' in record));
      assert.ok(record.sources.length > 0 && record.sources.every(source => source.official === true));
    }
  }
});
