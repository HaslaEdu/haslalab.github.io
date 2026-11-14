'use strict';
const test = require('node:test'), assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const read = f => fs.readFileSync(path.join(__dirname, '..', f), 'utf8');

test('the English site carries the same ad banners as the Korean site, labelled in its language', () => {
  const html = read('index.html'), code = html.slice(html.indexOf('function adFitBanner('), html.indexOf('/* ══', html.indexOf('function adFitBanner(')));
  for (const [lang, label] of [['en', 'Ad'], ['ko', '광고']]) {
    const ctx = {lang}; vm.createContext(ctx); vm.runInContext(code, ctx);
    for (const placement of ['home', 'primary', 'secondary', 'about']) {
      const b = ctx.adFitBanner(placement);
      assert.match(b, /adfit-banner/, lang + ' ' + placement);assert.ok(b.includes(`>${label}</span>`), lang + ' label');
    }
  }
  // the side cards too: no language gate, and the label follows the language
  assert.ok(!html.includes('English site (no ads)'));
  assert.match(html, /box\.innerHTML='<span class="adfit-banner-label">'\+\(lang==="ko"\?"광고":"Ad"\)\+'<\/span>'/);
});

test('the simulators show the ad in Korean and in English, labelled in the page language', () => {
  const js = read('sim/adfit.js');
  assert.ok(!js.includes('if (!ko) return;'));assert.ok(!/display = ko \? "" : "none"/.test(js));
  assert.match(js, /banner\.setAttribute\("aria-label", isKorean\(\) \? "광고" : "Advertisement"\);/);
  assert.match(js, /const label = \(\) => isKorean\(\) \? "광고" : "Ad";/);
});
