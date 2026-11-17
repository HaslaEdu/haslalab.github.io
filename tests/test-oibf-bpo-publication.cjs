const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const read = name => fs.readFileSync(path.join(root, name), 'utf8');
const published = JSON.parse(read('tools/oibf_bpo_publication.json')).files;
const assets = JSON.parse(read('pdf-assets.json'));
const context = {window: {}};
vm.runInNewContext(read('theory.js'), context);
const {THEORY, ARCHIVE_PRACTICAL} = context.window;
const PaperLanguages = require('../paper-languages.js');
const html = read('index.html');

test('every accepted OIbF/BPO PDF is reachable under its audited filename and byte count', () => {
  assert.equal(published.length, 156);
  assert.equal(new Set(published.map(file => file.file)).size, 156);
  assert.equal(published.filter(file => file.competition === 'oibf').length, 140);
  assert.equal(published.filter(file => file.competition === 'bpo').length, 16);
  const selected = new Set();
  for (const catalogue of [THEORY, ARCHIVE_PRACTICAL]) {
    for (const comp of ['oibf', 'bpo']) {
      for (const year of Object.values(catalogue[comp] || {})) {
        for (const slot of Object.values(year.f)) {
          for (const file of Object.values(PaperLanguages.files(slot))) selected.add(file);
          for (const file of [slot.sol, slot.ko?.sol]) if (file) selected.add(file);
        }
      }
    }
  }
  for (const file of published) {
    assert.ok(selected.has(file.file), `Unlinked accepted translation: ${file.file}`);
    assert.equal(assets[file.file], file.bytes, file.file);
    assert.match(file.sha256, /^[a-f0-9]{64}$/);
    assert.match(file.mapping_sha256, /^[a-f0-9]{64}$/);
    assert.ok(html.includes(`"${file.file}":"${file.sha256.slice(0, 16)}"`), file.file);
  }
});

test('translated theory and practical papers retain the original source-language choice', () => {
  for (const catalogue of [THEORY, ARCHIVE_PRACTICAL]) {
    for (const year of Object.values(catalogue.oibf)) {
      for (const slot of Object.values(year.f)) {
        const options = PaperLanguages.files(slot);
        assert.ok(options.en, 'English edition');
        assert.ok(options.ko, 'Korean edition');
        assert.ok(options.es || options.pt, 'Original source edition');
        assert.equal(slot.paper, options.en);
        assert.equal(slot.ko.paper, options.ko);
      }
    }
  }
  for (const year of Object.values(THEORY.bpo)) {
    assert.ok(year.f.T.papers.en.endsWith('_T_EN.pdf'));
    assert.ok(year.f.T.ko.paper.endsWith('_T_KO.pdf'));
    assert.ok(year.f.T.ko.sol.endsWith('_TS_KO.pdf'));
  }
});

test('embedded solutions remain disclosed for each translated language', () => {
  for (const catalogue of [THEORY, ARCHIVE_PRACTICAL]) {
    for (const year of Object.values(catalogue.oibf)) {
      for (const slot of Object.values(year.f)) {
        if (!slot.containsSolutions) continue;
        assert.equal(PaperLanguages.containsSolutions(slot, 'en'), true);
        assert.equal(PaperLanguages.containsSolutions(slot, 'ko'), true);
      }
    }
  }
});

test('the unavailable 2007 T1 solution stays a notice and cannot enable a graded exam', () => {
  const slot = THEORY.oibf['2007'].f.T1;
  assert.equal(slot.solutionNotice, true);
  assert.equal(slot.ko.solutionNotice, true);
  assert.equal(published.filter(file => file.document_type === 'solution_availability_notice').length, 2);
  const start = html.indexOf('function theoryGroups(');
  const end = html.indexOf('/* a shortlist (backup)', start);
  const scope = {
    thyOf: (comp, year) => THEORY[comp]?.[String(year)],
    compOf: () => ({}), THY_YEARLY: new Set(), THY_WHOLE: new Set(),
    EOTVOS_TIMED: new Set(),
  };
  vm.runInNewContext(html.slice(start, end) + '\nthis.groups=theoryGroups("oibf",{y:2007});', scope);
  assert.ok(!scope.groups.flat().includes('T1'));
});

test('OPhO round and component axes preserve the mixed invitational Part II', () => {
  const part = THEORY.opho['2025'].f.T2i;
  assert.equal(part.round, 'invitational');
  assert.equal(part.component, 'mixed');
  assert.deepEqual(Array.from(part.problemIds), ['Ti4']);
  assert.equal(THEORY.opho['2025'].f.T.round, 'open');
  assert.equal(THEORY.opho['2025'].f.T.component, 'theory');
  assert.match(html, /data-opho-round/);
  assert.match(html, /Part II contains both an experimental and a theoretical problem/);
});

test('the static experiment index links every translated practical source and its solutions', () => {
  for (const language of ['en', 'ko']) {
    const index = read(language === 'ko' ? 'problems.html' : 'problems-en.html');
    for (const file of published.filter(file => file.language === language && /^OIbF_\d{4}_E/.test(file.original))) {
      assert.ok(index.includes('/pdf/' + file.file), `Missing static experiment link: ${file.file}`);
    }
    assert.ok(index.includes(language === 'ko' ? '문제·해설 합본' : 'Problems &amp; solutions') || index.includes('Problems & solutions'));
  }
  assert.doesNotMatch(read('sitemap.xml'), /haslalab\.org\/https?:/);
});
