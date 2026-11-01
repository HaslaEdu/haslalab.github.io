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
