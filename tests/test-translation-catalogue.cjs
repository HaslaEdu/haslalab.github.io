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
for (const year of ['2010', '2011', '2013', '2015', '2016', '2020']) {
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
for (const year of ['2005', '2006', '2007', '2013', '2022', '2023', '2024', '2025']) {
  const file = window.THEORY.cpho[year].f.T;
  assert.equal(file.paper, year === '2023' ? 'CPhO_2023_Combined_EN.pdf' : ['2005', '2006', '2007', '2013', '2022'].includes(year) ? `CPhO_${year}_T_EN.pdf` : `CPhO_${year}_T_BAUPC_EN.pdf`);
  assert.ok(assets[file.paper] > 0);
  assert.ok(assets[file.ko.paper] > 0);
  if (year === '2013' || year === '2024') {
    assert.equal(file.sol, `CPhO_${year}_TS_BAUPC_EN.pdf`);
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
console.log(JSON.stringify({statements, selectionPdfs, gphoSolutions: solutions, izhoKoreanEditions: 18, usapho, cphoBilingualYears: 8}));
