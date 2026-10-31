const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const figures = require('../monthly-figures.js');
const root = path.resolve(__dirname, '..');
const normalize = value => value.replace(/\r\n/g, '\n').trim();
const prefixed = (svg, prefix) => svg
  .replace(/id="([^"]+)"/g, (_, id) => `id="${prefix}-${id}"`)
  .replace(/url\(#([^)]+)\)/g, (_, id) => `url(#${prefix}-${id})`)
  .replace(/aria-labelledby="([^"]+)"/g, (_, ids) => `aria-labelledby="${ids.split(/\s+/).map(id => `${prefix}-${id}`).join(' ')}"`);

test('the inline diagram bundle exactly matches all reviewed transparent SVG sources', () => {
  assert.deepEqual(figures.paths, ['weekly/figures/pressure-wave-apparatus.svg','weekly/figures/proton-chain.svg', 'weekly/figures/walls-targets.svg', 'weekly/figures/optical-rutherford.svg','weekly/figures/greenhouse-precession.svg','weekly/figures/greenhouse-cycles.svg']);
  for (const source of figures.paths) {
    const svg = normalize(fs.readFileSync(path.join(root, source), 'utf8'));
    assert.equal(figures.render(source, 'proof'), prefixed(svg, 'proof'), source);
    assert.match(svg, /viewBox="[^"]+"/);
    assert.match(svg, /currentColor/);
    assert.ok(!/<(?:script|foreignObject|style|image|iframe|object|embed)\b/i.test(svg), source);
    assert.ok(!/\bon[a-z]+\s*=|(?:href|src)\s*=|https?:\/\//i.test(svg.replace('http://www.w3.org/2000/svg', '')), source);
    assert.ok(!/<rect\b/i.test(svg), 'no canvas rectangle separates the diagram from the page');
    assert.ok(!/fill="(?:#fff(?:fff)?|white)"/i.test(svg), 'no opaque white fill');
  }
});

test('only allowlisted paths inline; caller SVG, paths and prefixes cannot inject markup', () => {
  for (const unsafe of ['__proto__', 'constructor', '../weekly/figures/proton-chain.svg', 'https://example.com/a.svg', '<svg onload="alert(1)"></svg>', 'weekly/figures/proton-chain.svg?x=1']) {
    assert.equal(figures.render(unsafe), '', unsafe);
  }
  const clean = figures.render(figures.paths[0], 'bad" onload="alert(1)');
  assert.ok(!clean.includes('onload'));
  assert.match(clean, /id="hl-monthly-figure-\d+-title"/);
});

test('repeated diagrams retain unique accessible titles and correctly scoped marker references', () => {
  for (const source of figures.paths) {
    const first = figures.render(source), second = figures.render(source);
    const ids = html => [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
    const firstIds = ids(first), secondIds = ids(second);
    assert.equal(new Set([...firstIds, ...secondIds]).size, firstIds.length + secondIds.length);
    for (const html of [first, second]) {
      const own = new Set(ids(html));
      for (const ref of html.matchAll(/url\(#([^)]+)\)/g)) assert.ok(own.has(ref[1]), ref[1]);
      for (const ref of html.matchAll(/aria-labelledby="([^"]+)"/g)) for (const id of ref[1].split(/\s+/)) assert.ok(own.has(id), id);
    }
  }
});

test('classic browser loading exposes the same safe renderer without requiring a module system', () => {
  const context = {};
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(root, 'monthly-figures.js'), 'utf8'), context);
  assert.equal(context.HL_MONTHLY_FIGURES.render('weekly/figures/walls-targets.svg', 'browser'), figures.render('weekly/figures/walls-targets.svg', 'browser'));
});
