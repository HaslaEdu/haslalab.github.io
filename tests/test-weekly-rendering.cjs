const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'arena.js'), 'utf8');
const esc = value => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[char]));
const context = {esc};
vm.createContext(context);
vm.runInContext(source, context);
const render = text => context.arPublishedText(text);

test('published text renders section headings and complete display equations without splitting their text nodes', () => {
  const html = render('## A. 운동방정식\n변위는 $x_j$이다.\n\n$$\n\\frac{d^2x}{dt^2}+\\omega^2 x=0\n$$\n\n### 조건\n$x(0)=0$');
  assert.match(html, /<h2>A\. 운동방정식<\/h2>/);
  assert.match(html, /<h3>조건<\/h3>/);
  assert.match(html, /<div class="arformula">\$\$\n\\frac/);
  assert.ok(!html.match(/arformula[^]*?<br>[^]*?<\/div>/));
  assert.match(html, /<p>변위는 \$x_j\$이다\.<\/p>/);
});

test('only local weekly SVG figure paths render; HTML, external URLs and traversal remain escaped text', () => {
  const good = render('![충돌 방향](weekly/figures/walls-targets.svg)');
  assert.match(good, /<figure class="arfigure"><img src="weekly\/figures\/walls-targets\.svg"/);
  for (const unsafe of ['<img src=x onerror=alert(1)>', '![x](https://example.com/a.svg)', '![x](javascript:alert(1))', '![x](weekly/figures/../secret.svg)', '![x](weekly/figures/a.svg?token=x)']) {
    const result = render(unsafe);
    assert.ok(!result.includes('<img'), unsafe);
    assert.ok(!result.includes('<script'), unsafe);
  }
  assert.ok(render('## <script>alert(1)</script>').includes('&lt;script&gt;'));
  assert.equal(context.arText('![x](weekly/figures/walls-targets.svg)'), '![x](weekly/figures/walls-targets.svg)', 'student preview stays plain escaped text');
});

test('every supplied formula parses in KaTeX and every published diagram exists', () => {
  const katex = require(path.join(root, 'vendor/katex/katex.min.js'));
  const content = {problems:['2026-W44.json','2026-11-greenhouse-part-d.json'].flatMap(name=>JSON.parse(fs.readFileSync(path.join(root,'community/weekly',name),'utf8')).problems)};
  let count = 0;
  for (const p of content.problems) for (const field of ['body_ko', 'body_en', 'model_ko', 'model_en']) {
    const text = p[field], equations = [...text.matchAll(/\$\$([\s\S]*?)\$\$|\$([^$\n]+)\$/g)];
    for (const eq of equations) {
      assert.doesNotThrow(() => katex.renderToString(eq[1] ?? eq[2], {displayMode:eq[1] !== undefined, throwOnError:true}), `${p.title_en}/${field}: ${eq[0]}`);
      count++;
    }
    for (const figure of text.matchAll(/!\[[^\]\n]+\]\(([^)]+)\)/g)) {
      assert.match(figure[1], /^weekly\/figures\/[a-z0-9][a-z0-9-]*\.svg$/);
      assert.ok(fs.existsSync(path.join(root, figure[1])), figure[1]);
    }
  }
  assert.ok(count > 500, 'full bilingual problems and solutions were checked');
});
