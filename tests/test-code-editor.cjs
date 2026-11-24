/* code-editor.js: highlighting escapes the text (the overlay is innerHTML), brackets in strings are not matched, and the
   AI panel's line diff turns one text into the other. */
const test=require('node:test'),assert=require('node:assert/strict');
const E=require('../code-editor.js');

test('the highlighted copy is escaped text, character for character', () => {
  const src='const s = "<img src=x onerror=alert(1)>"; // </pre><script>\nhl.circle(1, 2, 0.5) & 3 > 2';
  const html=E.highlight(src,'js');
  assert.doesNotMatch(html,/<img|<script|<\/pre>/);
  assert.equal(html.replace(/<[^>]+>/g,'').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&'),src);
  assert.match(html,/<span class="ce-h">hl<\/span>\.<span class="ce-f">circle<\/span>/);
  const py=E.highlight('def f(x):\n    return x**2  # square\ns = """a\nb"""','py');
  assert.match(py,/<span class="ce-k">def<\/span>/);assert.match(py,/<span class="ce-c"># square<\/span>/);assert.match(py,/<span class="ce-s">"""a\nb"""<\/span>/);
});

test('bracket matching skips brackets inside strings and comments', () => {
  const src='f(a, ")", [1, 2]) // (';
  assert.deepEqual(E.matchBracket(src,2,'js'),[1,16]);
  assert.deepEqual(E.matchBracket(src,17,'js'),[1,16]);
  assert.equal(E.matchBracket('(]',1,'js'),null);
});

test('the line diff rebuilds both texts', () => {
  const a='a\nb\nc\nd\ne',b='a\nB\nc\ne\nf';
  const d=E.diffLines(a,b);
  assert.equal(d.filter(x=>x.op!=='+').map(x=>x.text).join('\n'),a);
  assert.equal(d.filter(x=>x.op!=='-').map(x=>x.text).join('\n'),b);
  assert.equal(d.filter(x=>x.op===' ').length,3);
  assert.deepEqual(E.diffLines('same','same'),[{op:' ',text:'same'}]);
});
