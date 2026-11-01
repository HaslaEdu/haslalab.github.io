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
