const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const read = name => fs.readFileSync(path.join(root, name), 'utf8');
const window = {};
for (const name of ['iypt.js', 'theory.js', 'rupho-selection.js', 'rupho-archive.js']) {
  vm.runInNewContext(read(name), {window}, {filename: name});
}
const html = read('index.html');
for (const match of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)) {
  if (match[1].trim() && !match[0].includes('application/ld+json')) new vm.Script(match[1]);
}

const start = html.indexOf('if(window.IYPT) DATA.iypt=');
const end = html.indexOf('/* USACO', start);
assert.ok(start > 0 && end > start);
const DATA = {};
vm.runInNewContext(html.slice(start, end), {window, DATA});
assert.equal(DATA.iypt.years.length, 40);
let statements = 0;
for (const year of DATA.iypt.years) {
  assert.equal(year.problems.length, 17, year.y);
  year.problems.forEach((p, i) => {
    assert.equal(p.id, String(i + 1));
    assert.match(p.title.ko, /[가-힣]/, `${year.y}/${p.id} title`);
    assert.match(p.desc.ko, /[가-힣]/, `${year.y}/${p.id} statement`);
    assert.ok(!/<(?!br>)/.test(p.desc.ko), 'HTML in translated prose must be escaped');
    statements++;
  });
}

const assets = JSON.parse(read('pdf-assets.json'));
let selectionPdfs = 0;
for (const letter of 'wxy') {
  const key = `rupho${letter}`;
  assert.ok(window.RUPHO_ARCHIVE.stages.some(stage => stage.key === key));
  assert.ok(fs.existsSync(path.join(root, 'logo', `${key}.png`)));
  assert.ok(window.THEORY[key]);
  assert.ok(window.RUPHO_SELECTION[key]);
  const manifest = JSON.parse(read(`tools/theory/${key}.json`));
  assert.equal(manifest.classification, letter.toUpperCase());
  for (const year of manifest.years) {
    const numbers = year.problems.map(p => p.id);
    assert.equal(new Set(numbers).size, numbers.length);
    for (const file of year.files) {
      assert.match(file.url, new RegExp(`/rupho-${letter}/${year.y}/`));
      assert.ok(assets[file.file] > 0, `Unpublished PDF: ${file.file}`);
      selectionPdfs++;
    }
  }
}
assert.equal(selectionPdfs, 319);
assert.ok(!window.THEORY.ruphoz);

let solutions = 0;
for (const year of ['2016', '2017', '2019', '2022']) {
  for (const part of ['T1', 'T2', 'T3']) {
    const file = window.THEORY.gpho[year].f[part].ko;
    assert.ok(file.paper, 'Existing Korean problem must be preserved');
    assert.ok(assets[file.sol] > 0, `Unpublished solution: ${file.sol}`);
    solutions++;
  }
}
for (const year of ['2021', '2022', '2023', '2024', '2025', '2026']) {
  for (const kind of ['paper', 'sol']) {
    assert.ok(assets[window.THEORY.izho[year].f.T.ko[kind]] > 0);
  }
}
for (const year of ['2010', '2011', '2012', '2013', '2014', '2015', '2016', '2020']) {
  assert.ok(assets[window.THEORY.izho[year].f.T.ko.paper] > 0);
}
let usapho = 0;
for (let year = 1997; year <= 2026; year++) {
  const file = window.THEORY.usapho[String(year)].f.T;
  assert.ok(assets[file.paper] > 0);
  assert.ok(assets[file.sol] > 0);
  if (file.ko.paper.startsWith('pdfx/usapho/')) {
    const local = path.join(root, file.ko.paper);
    assert.ok(fs.statSync(local).size > 0, 'The local Korean print edition must be published');
    assert.equal(fs.readFileSync(local).subarray(0, 5).toString(), '%PDF-');
  } else assert.ok(assets[file.ko.paper] > 0);
  usapho++;
}
const cphoBilingualYears = ['2003', '2004', '2005', '2006', '2007', '2008', '2009', '2010', '2011', '2013', '2022', '2023', '2024', '2025'];
for (const year of cphoBilingualYears) {
  const file = window.THEORY.cpho[year].f.T;
  assert.equal(file.paper, year === '2023' ? 'CPhO_2023_Combined_EN.pdf' : ['2003', '2004', '2005', '2006', '2007', '2008', '2009', '2010', '2011', '2013', '2022', '2024'].includes(year) ? `CPhO_${year}_T_EN.pdf` : `CPhO_${year}_T_BAUPC_EN.pdf`);
  assert.ok(assets[file.paper] > 0);
  assert.ok(assets[file.ko.paper] > 0);
  if (['2003', '2004', '2008', '2009', '2010', '2013', '2024'].includes(year)) {
    assert.equal(file.sol, ['2003', '2004', '2008', '2009', '2010'].includes(year) ? `CPhO_${year}_TS_EN.pdf` : `CPhO_${year}_TS_BAUPC_EN.pdf`);
    assert.ok(assets[file.sol] > 0);
    assert.ok(assets[file.ko.sol] > 0);
  }
  if (year === '2023') {
    assert.equal(file.sol, file.paper);
    assert.equal(file.ko.sol, file.ko.paper);
  }
  const source = JSON.parse(read('tools/theory/cpho.json')).years.find(y => String(y.y) === year);
  if (Number(year) >= 2013) {
    const originalHost = {2022: '19216675.s21i.faiusr.com', 2023: 'wds-service-1258344699.file.myqcloud.com'}[year] || 'olimpicos.net';
    assert.equal(new URL(source.files[0].url).hostname, originalHost, 'Original source provenance must be preserved');
  }
}
for (const file of JSON.parse(read('tools/translation_font_validation.json')).files) {
  assert.equal(assets[file.file], file.bytes, `Published PDF size differs from audited version: ${file.file}`);
  assert.equal(file.missing_glyph_spans.length, 0, file.file);
}
// Every audited translation must be reachable from the site. The catalogue lives in several structures now:
// window.THEORY (theory.js, contest-exams.js and the per-competition chunks in catalogue/*.js), window.ARCHIVE_PRACTICAL
// (practical rounds), GENERAL, the RuPhO/IYPT/USACO datasets, and the problem archive in index.html. Links are stored as
// release names (CPhO_2004_T_KO.pdf), site paths (pdfx/ibo/x.pdf) or PDF Worker URLs; the Worker forms are mapped back
// to the file they serve (see pdf-worker/src/index.js and tools/pdfx_release.py):
//   https://haslalab-pdf.haslalab.workers.dev/pdf/l/<folder>/<name>?v=…  ->  pdfx/<folder>/<name>
//   …/pdf/l/<name>  ->  pdfx/<name>      …/pdf/X<folder>_<name>  ->  pdfx/<folder>/<name>      …/pdf/<NAME>  ->  <NAME>
const catalogueWindow = {};
const catalogueScope = {window: catalogueWindow, URL, URLSearchParams, localStorage: {getItem: () => null}, console};
vm.createContext(catalogueScope);
const catalogueSources = ['paper-languages.js', 'theory.js', 'contest-exams.js', 'iypt.js', 'usaco.js', 'rupho-selection.js', 'rupho-archive.js',
  ...fs.readdirSync(path.join(root, 'catalogue')).filter(name => name.endsWith('.js')).sort().map(name => 'catalogue/' + name)];
for (const name of catalogueSources) vm.runInContext(read(name), catalogueScope, {filename: name});
for (const key of ['THEORY', 'ARCHIVE_PRACTICAL']) assert.ok(catalogueWindow[key], `window.${key} must be defined by the catalogue`);
const PDF_WORKER = /^(?:https?:\/\/haslalab-pdf\.haslalab\.workers\.dev)?\/?pdf\//;
function catalogueFile(link) {
  let file = String(link).split(/[?#]/)[0];
  if (!PDF_WORKER.test(file)) return file;
  file = file.replace(PDF_WORKER, '');
  try { file = decodeURIComponent(file); } catch {}
  let m;
  if ((m = file.match(/^l\/(?:([a-z]+)\/)?([^/]+)$/))) return 'pdfx/' + (m[1] ? m[1] + '/' : '') + m[2];
  if ((m = file.match(/^X([a-z]+)_(.+)$/))) return 'pdfx/' + (m[1] === 'root' ? '' : m[1] + '/') + m[2];
  return file;
}
assert.equal(catalogueFile('https://haslalab-pdf.haslalab.workers.dev/pdf/l/ibo/IBO_2023_P3_OriginalLayout_KO.pdf?v=07571ca93bb89ef3&cv=2'), 'pdfx/ibo/IBO_2023_P3_OriginalLayout_KO.pdf');
assert.equal(catalogueFile('/pdf/l/root.pdf'), 'pdfx/root.pdf');
assert.equal(catalogueFile('https://haslalab-pdf.haslalab.workers.dev/pdf/Xicho_IChO_2008_P_KO.pdf'), 'pdfx/icho/IChO_2008_P_KO.pdf');
assert.equal(catalogueFile('https://haslalab-pdf.haslalab.workers.dev/pdf/CPhO_2004_T_KO.pdf#page=2'), 'CPhO_2004_T_KO.pdf');
assert.equal(catalogueFile('pdfx/ibo/x.pdf'), 'pdfx/ibo/x.pdf');
const catalogueFiles = new Set();
function collectFiles(value) {
  if (typeof value === 'string') catalogueFiles.add(catalogueFile(value));
  else if (value && typeof value === 'object') Object.values(value).forEach(collectFiles);
}
collectFiles(window.THEORY);
for (const value of Object.values(catalogueWindow)) collectFiles(value);
// experimental-round editions are linked from the problem archive in index.html (pdf/sol {ko, en|ru}), and the page
// script links some papers directly
for (const match of html.matchAll(/"pdf\/([^"\/]+\.pdf)"/g)) catalogueFiles.add(match[1]);
for (const match of html.matchAll(/["'`]([^"'`\s]+\.pdf(?:[?#][^"'`\s]*)?)["'`]/g)) catalogueFiles.add(catalogueFile(match[1]));
const unlinked = JSON.parse(read('tools/original_style_publication.json'))
  .filter(item => ![item.file, ...(item.aliases || [])].some(file => catalogueFiles.has(file)))
  .map(item => item.file);
assert.deepEqual(unlinked, [], `Audited translations not linked in the catalogue (${unlinked.length}):\n${unlinked.join('\n')}`);
// a site PDF the catalogue links must be in the repository: tools/pdfx_release.py publishes pdfx/ from there
const missingSiteFiles = [...catalogueFiles].filter(file => /^pdfx\/.+\.pdf$/.test(file) && !fs.existsSync(path.join(root, file)));
assert.deepEqual(missingSiteFiles, [], `Catalogue links to pdfx/ PDFs that are not in the repository:\n${missingSiteFiles.join('\n')}`);
const izhoKoreanEditions = new Set(Object.values(window.THEORY.izho)
  .flatMap(year => Object.values(year.f || {}).flatMap(part => Object.values(part.ko || {})))
  .filter(file => typeof file === 'string' && /_KO\.pdf$/.test(file))).size;
console.log(JSON.stringify({statements, selectionPdfs, gphoSolutions: solutions, izhoKoreanEditions, usapho, cphoBilingualYears: cphoBilingualYears.length}));
