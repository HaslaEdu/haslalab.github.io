const test = require('node:test'), assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path');
const root = path.resolve(__dirname, '..');
const read = f => fs.readFileSync(path.join(root, f), 'utf8');

test('theory answer-sheet items are whole marking tables whose points add up to the problem total', () => {
  const data = JSON.parse(read('sim/theorysheets.json'));
  let n = 0;
  for (const [key, tasks] of Object.entries(data)) {
    assert.match(key, /^(ipho|apho|eupho)\d{4}$/);
    for (const [task, sheet] of Object.entries(tasks)) {
      assert.match(task, /^T\d+$/);
      assert.ok(sheet.items.length >= 2, key + task);
      const sum = sheet.items.reduce((s, [, p]) => s + p, 0);
      assert.ok(Math.abs(sum - sheet.points) < 1e-6, key + task);
      const total = sheet.total || 10;
      assert.ok(Math.abs(sum - total) <= 0.02 * total, `${key} ${task}: ${sum} vs ${total}`);
      assert.equal(new Set(sheet.items.map(([label]) => label)).size, sheet.items.length, 'labels are unique');
      n++;
    }
  }
  assert.ok(n >= 20);
});

test('every printed theory sheet and every stamped official sheet carries the scanner\'s corner squares', () => {
  const html = read('sim/sheets.html'), scanner = read('sim/labscan/scanner.js');
  const inset = JSON.parse(scanner.match(/export const MARKER_INSET = (\{[^}]+\})/)[1].replace(/(\w+):/g, '"$1":'));
  const stamp = JSON.parse(html.match(/const INSET = (\{[^}]+\})/)[1].replace(/(\w+):/g, '"$1":'));
  assert.deepEqual(stamp, inset, 'the stamped squares sit where the scanner looks for them');
  // HaslaLab's own pages: the theory header keeps the four squares and the sheet line the reader uses
  const thyHead = html.slice(html.indexOf('const thyHead'), html.indexOf('const head ='));
  assert.match(thyHead, /mk a.*mk b.*mk c.*mk d/s);
  assert.match(thyHead, /ANSWER SHEET.*WORKING SHEET/s);
  // official and translated theory sheets are offered with the markers added
  assert.match(html, /data-stamp="\$\{esc\(sheetUrl\(ANS\[i\]\)\)\}"/);
  assert.match(html, /data-stamp="\$\{esc\(sheetUrl\(WS\)\)\}"/);
  assert.match(html, /pdf-lib\/1\.17\.1\/pdf-lib\.min\.js/);
});

test('every exam and grading row offers its answer and working sheets to print before it starts', () => {
  const html = read('index.html');
  const src = html.slice(html.indexOf('function sheetsHref'), html.indexOf('/* a problem card on a year page'));
  const sheetsHref = new Function('lang', src + 'return sheetsHref;')('ko');
  const thy = new URLSearchParams(sheetsHref('sim/exam.html?m=t&c=ipho&y=2017&n=IPhO&e=T1%2CT2&t=a%7Cb&p=x&s=y&k=&a=pdfx%2Fipho%2FA1.pdf%7CA2.pdf&w=W.pdf&lang=ko&h=1&review=1').split('?')[1]);
  assert.deepEqual(Object.fromEntries(thy), { c: 'ipho', y: '2017', n: 'IPhO', e: 'T1,T2', t: 'a|b', lang: 'ko', m: 't', a: 'pdfx/ipho/A1.pdf|A2.pdf', w: 'W.pdf' });
  const mix = new URLSearchParams(sheetsHref('sim/exam.html?c=nbpho&y=2020&n=NBPhO&e=E1%2CT&f=a_web.html%2C-&t=x%7Cy&lang=ko').split('?')[1]);
  assert.equal(mix.get('tt'), 'T'); assert.equal(mix.get('m'), null);
  const exp = new URLSearchParams(sheetsHref('sim/exam.html?c=ipho&y=2017&n=IPhO&e=E1%2CE2&f=a_web.html%2Cb_web.html&t=x%7Cy&lang=ko').split('?')[1]);
  assert.equal(exp.get('tt'), null); assert.equal(exp.get('e'), 'E1,E2');
  const row = html.slice(html.indexOf('const row=(y,tasks,label,sub,sec,href)'), html.indexOf('const thyT='));
  assert.match(row, /href="\$\{sheetsHref\(href\)\}"/);
});

test('every problem card offers its answer and working sheets beside the problem and the solution', () => {
  const html = read('index.html'), sheets = read('sim/sheets.html');
  // the sheets page keeps one kind when a card asks for it
  assert.match(sheets, /const KIND = Q\.get\("k"\)/);
  assert.match(sheets, /want = \{ answer: KIND !== "working", working: KIND !== "answer" \}/);
  // theory cards: the official / Korean answer sheet and the Korean working sheet where the site has them, else the page
  const thy = html.slice(html.indexOf('const sheetDocs='), html.indexOf('const card=(code,probs,f,k,head,docs)'));
  assert.match(thy, /A\[0\]\?a\(A\[0\],ko\?"답안지":"Answer sheet"/);
  assert.match(thy, /ko&&t\.wk\?a\(t\.wk,"워킹시트"\)/);
  assert.match(html, /concat\(sheetDocs\(code,A,!omr\)\)/);
  // experiment cards: both, before the Python source
  assert.match(html, /if\(live&&!c\.open&&\/\^E\\d\*\$\/\.test\(p\.id\)\)\{ const h=expSheetsHref\(key,yr,p\);/);
  const sheetKind = new Function('return ' + html.match(/const sheetKind=([^;]+);/)[1])();
  assert.equal(sheetKind('sim/sheets.html?c=ipho', 'working'), 'sim/sheets.html?c=ipho&k=working');
});

test('ISPhO 2023–2026: every year has its answer sheets (and 2024–2026 their working sheets) in English and Korean, on the site', () => {
  const window = {};
  require('node:vm').runInNewContext(read('theory.js'), { window });
  const T = window.THEORY.ispho;
  for (const y of ['2023', '2024', '2025', '2026']) {
    for (const part of ['T', 'T1', 'T2', 'T3']) {
      const f = T[y].f[part];
      for (const file of [f.answer, f.ko.answer]) { assert.match(file, /^pdfx\/ispho\//, `${y} ${part}`); assert.ok(fs.existsSync(path.join(root, file)), file); }
    }
    if (y !== '2023') for (const file of [T[y].we, T[y].wk]) assert.ok(file && fs.existsSync(path.join(root, file)), `${y} working sheet`);
  }
  const index = JSON.parse(read('sim/sheets/index.json'));
  for (const y of ['2024', '2025', '2026']) for (const kind of ['answer', 'working']) {
    const langs = index['ispho' + y].E1[kind].map(e => { assert.ok(fs.existsSync(path.join(root, 'sim/sheets', e.file)), e.file); return e.lang; });
    assert.ok(langs.some(l => /^English/.test(l)) && langs.includes('Korean (Korea (Republic of))'), `${y} E1 ${kind}`);
  }
  // the T1 problems solved on the organisers' program are theory problems: no longer among the year's experiments
  const html = read('index.html'), block = html.slice(html.indexOf(' ispho:{'), html.indexOf(' opho:{'));
  assert.equal((block.match(/problems:\[[^\]]*id:"T1"/g) || []).length, 0);
  assert.equal((block.match(/sims:\[\s*\{id:"T1"/g) || []).length, 3);
});
