const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const read = name => fs.readFileSync(path.join(root, name), 'utf8');
const json = name => JSON.parse(read(name));
const generated = {window: {}};
vm.runInNewContext(read('theory.js'), generated, {filename: 'theory.js'});
const catalogue = generated.window.THEORY;
const recentEotvos = Array.from({length: 33}, (_, i) => 1994 + i);
const historicalEotvos = [1949, 1962, 1963, 1964, 1965, 1966, 1970, 1987, 1988, 1989, 1990, 1991];
const finals = Array.from({length: 13}, (_, i) => 2014 + i);

test('generated Eotvos catalogue retains recovered physics years and Hungarian paper choices', () => {
  const manifest = json('tools/theory/eotvos.json');
  const expected = [...historicalEotvos, ...recentEotvos];
  assert.deepEqual(Object.keys(catalogue.eotvos).map(Number).sort((a, b) => a - b), expected);
  assert.deepEqual(json('tools/eotvos_archive_report.json').coverage.available_years, expected);
  for (const year of manifest.years) {
    const published = catalogue.eotvos[year.y];
    for (const file of year.files.filter(file => file.kind === 'paper')) {
      const slot = published.f[file.part];
      assert.equal(slot.papers[file.lang.toLowerCase()], file.local, `${year.y}/${file.lang}`);
    }
    assert.ok(published.f.T.papers.hu, `${year.y}: a Hungarian source remains selectable in the English UI`);
  }
  for (const year of [1894, 1916, 1992, 1993]) assert.equal(catalogue.eotvos[year], undefined);
  assert.equal(generated.window.THEORY_META.eotvos.since, 1916);
});

test('generated Eotvos papers disclose solutions by language and preserve historical document context', () => {
  for (const year of json('tools/theory/eotvos.json').years) {
    const published = catalogue.eotvos[year.y];
    for (const file of year.files.filter(file => file.kind === 'paper')) {
      const slot = published.f[file.part], language = file.lang.toLowerCase();
      assert.equal(Boolean(slot.paperContainsSolutions?.[language]), file.contains_solutions === true, `${year.y}/${language}`);
      if (slot.paper === file.local) assert.equal(Boolean(slot.containsSolutions), file.contains_solutions === true, `${year.y}: selected paper warning`);
    }
    if (year.source_type === 'historical_reprint') {
      assert.equal(published.sourceType, 'historical_reprint');
      assert.ok(published.note, `${year.y}: source report and page context must be disclosed`);
      assert.equal(published.f.T.sol, undefined, `${year.y}: the source report's newer solutions must not grade an older paper`);
    }
  }
});

test('PLANCKS archive contains every international final from 2014 through 2026 and no national preliminaries', () => {
  const manifest = json('tools/theory/plancks.json'), report = json('tools/plancks_archive_report.json');
  assert.equal(manifest.comp, 'plancks');
  assert.match(manifest.scope.en, /international/i);
  assert.match(report.scope, /international finals only.*no national preliminaries/i);
  assert.deepEqual(manifest.years.map(year => year.y).sort((a, b) => a - b), finals);
  assert.deepEqual(Object.keys(catalogue.plancks).map(Number).sort((a, b) => a - b), finals);
  const evidence = [...report.sources, ...(report.extractions || [])];
  for (const year of manifest.years) {
    assert.ok(year.files.some(file => file.kind === 'paper' && file.lang === 'EN'), `${year.y}: English final paper`);
    for (const file of year.files) {
      assert.match(file.local, /^pdfx\/plancks\/PLANCKS_\d{4}_(?:T_EN|TS)\.pdf$/);
      assert.match(file.url, /^https:\/\//);
      assert.ok(evidence.some(record => record.file === file.file && record.sha256 === file.sha256), `${file.file}: inspected source or extraction receipt`);
      assert.doesNotMatch(file.url, /prelim|preliminary|uk_ireland|national[_-]round/i);
      const slot = catalogue.plancks[year.y].f[file.part];
      if (file.kind === 'paper') {
        assert.equal(slot.papers.en, file.local, `${year.y}: published English final`);
        assert.equal(Boolean(slot.paperContainsSolutions?.en), false, `${year.y}: clean problem paper`);
      } else if (file.kind === 'solution') assert.equal(slot.sol, file.local, `${year.y}: published official solution`);
    }
  }
  assert.deepEqual(report.missing_solutions, [2017, 2018, 2019]);
  for (const year of report.missing_solutions) assert.equal(catalogue.plancks[year].f.T.sol, undefined, `${year}: unavailable solutions are not invented`);
  assert.match(report.sources.find(record => record.year === 2024 && record.kind === 'combined').url, /dublin_2024/);
});

test('PLANCKS local PDFs match inspection receipts and extracted problem pages retain their source provenance', () => {
  const manifest = json('tools/theory/plancks.json'), report = json('tools/plancks_archive_report.json');
  const checked = new Set();
  for (const file of manifest.years.flatMap(year => year.files)) {
    if (checked.has(file.local)) continue;
    const content = fs.readFileSync(path.join(root, file.local));
    assert.ok(content.subarray(0, 1024).includes(Buffer.from('%PDF-')), file.local);
    assert.equal(content.length, file.bytes, file.local);
    assert.equal(crypto.createHash('sha256').update(content).digest('hex'), file.sha256, file.local);
    assert.ok(Number.isInteger(file.pages) && file.pages > 0, file.local);
    checked.add(file.local);
  }
  for (const extraction of report.extractions || []) {
    const original = report.sources.find(record => record.file === extraction.source_file);
    assert.ok(original, extraction.file);
    assert.equal(extraction.source_sha256, original.sha256, extraction.file);
    assert.equal(extraction.source_pages.length, extraction.pages, extraction.file);
    assert.ok(extraction.source_pages.every((page, i, pages) => Number.isInteger(page) && page >= 1 && page <= original.pages && (!i || page > pages[i - 1])), extraction.file);
    const published = catalogue.plancks[extraction.year].f.T;
    assert.equal(published.paper, 'pdfx/plancks/' + extraction.file);
    assert.equal(Boolean(published.containsSolutions), false, `${extraction.year}: timed practice uses the inspected problems-only edition`);
  }
});

test('PLANCKS client and authoritative server preserve the 2021 sixteen-hour final and four-hour other finals', () => {
  const client = {window: {}};
  vm.runInNewContext(read('examdur.js'), client, {filename: 'examdur.js'});
  const worker = read('community/src/index.js');
  const start = worker.indexOf('const NBPHO_TIME =');
  const end = worker.indexOf('/* which kind of exam', start);
  assert.ok(start >= 0 && end > start);
  const server = {LAB: {}};
  vm.createContext(server);
  vm.runInContext(worker.slice(start, end), server);
  for (const year of json('tools/theory/plancks.json').years) {
    const minutes = year.y === 2021 ? 960 : 240, seconds = minutes * 60;
    assert.equal(year.minutes, minutes, `${year.y}: archive duration`);
    assert.equal(year.timing_evidence.minutes, minutes, `${year.y}: timing receipt`);
    assert.match(year.timing_evidence.source, /^https:\/\//);
    assert.ok(year.timing_evidence.basis, `${year.y}: duration basis`);
    assert.equal(client.window.HLexam.sec('plancks', year.y, 1, true), seconds, `${year.y}: client`);
    assert.equal(server.labExamSec('plancks', year.y, 1, true), seconds, `${year.y}: authoritative server`);
  }
});
