'use strict';
const test = require('node:test'), assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const read = f => fs.readFileSync(path.join(__dirname, '..', f), 'utf8');

test('the English site renders no ad banner; the Korean site keeps them', () => {
  const html = read('index.html'), code = html.slice(html.indexOf('function adFitBanner('), html.indexOf('/* ══', html.indexOf('function adFitBanner(')));
  for (const [lang, has] of [['en', false], ['ko', true]]) {
    const ctx = {lang}; vm.createContext(ctx); vm.runInContext(code, ctx);
    for (const placement of ['home', 'primary', 'secondary', 'about']) assert.equal(/adfit-banner/.test(ctx.adFitBanner(placement)), has, lang + ' ' + placement);
  }
});

test('the simulators hide the ad banner in English and fetch the ad only once Korean is chosen', () => {
  const js = read('sim/adfit.js');
  assert.match(js, /const ko = isKorean\(\);\s*banner\.style\.display = ko \? "" : "none";\s*if \(!ko\) return;/);
  /* the ad script is appended after that early return */
  assert.ok(js.indexOf('if (!ko) return;') < js.indexOf('ba.min.js'));
});
