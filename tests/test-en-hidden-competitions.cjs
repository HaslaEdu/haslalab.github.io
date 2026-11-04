'use strict';
const test = require('node:test'), assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path');
const read = f => fs.readFileSync(path.join(__dirname, '..', f), 'utf8');

test('CPhO is kept off the English site: no card, no count, a direct link goes to the subject list', () => {
  const html = read('index.html');
  assert.match(html, /const EN_HIDDEN=new Set\(\["cpho"\]\);/);
  assert.match(html, /const compShown=key=>!\(lang==="en"&&EN_HIDDEN\.has\(key\)\);/);
  assert.match(html, /const list=cur\.comps\.filter\(k=>DATA\[k\]&&compShown\(k\)\)/);
  assert.match(html, /x\.comps\.filter\(k=>DATA\[k\]&&compShown\(k\)\)\.length/);
  assert.match(html, /else if\(first && DATA\[first\] && !compShown\(first\)\)\{ const to="#\/comps\/"\+subjOf\(first\);/);
  /* the update feed follows the same rule */
  const design = read('site-design.js');
  assert.match(design, /SITE_UPDATES\.filter\(updateShown\)\.slice\(0,4\)/);
  assert.match(design, /SITE_UPDATES\.forEach\(\(item,index\)=>updateShown\(item\)&&items\.push/);
});
