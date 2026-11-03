const test=require('node:test'),assert=require('node:assert/strict');
const A=require('../archive-navigation.js');
const q='q_'+'a'.repeat(64),source='src_'+'b'.repeat(64);
test('archive categories carry fixed wire kinds and subject scope',()=>{
  for(const [category,kind] of Object.entries(A.categories)){
    for(const [sub,collection] of Object.entries(A.subjects)){
      const r=A.parse(A.href(category,sub));assert.equal(r.kind,kind);assert.equal(r.collection,collection);assert.equal(r.sub,sub);assert.equal(r.resolveLegacy,false);
    }
  }
  assert.equal(A.href('schools','astronomy'),'#/archive/schools/astro');
  assert.equal(A.href('books','cs'),'#/archive/books/info');
  assert.equal(A.parse('#/archive/books').collection,'physics');
});
test('old contest archive and Learn links remain useful without returning to the removed bank',()=>{
  assert.equal(A.legacy('#/comps/astro'),'#/archive/contests/astro');
  assert.equal(A.legacy('#/comps'),'#/archive/contests');
  assert.equal(A.legacy('#/archive/phys'),'#/archive/contests/phys');
  assert.equal(A.legacy('#/learn/astronomy/library'),'#/archive/books/astro');
  const target=A.legacy('#/learn/astronomy/library?problem='+q+'&source='+source);
  assert.equal(A.parse(target).resolveLegacy,true);assert.equal(A.parse(target).params.get('problem'),q);
  for(const hash of ['#/ipho/1967','#/ipho/exam','#/learn/physics/studio','#/community/post/1'])assert.equal(A.legacy(hash),null);
});
test('query state retains source/question and opaque browse cursors, never secrets or redirect destinations',()=>{
  const p=A.clean(new URLSearchParams({source,problem:q,topic:'general_relativity',q:'a & b / c',stars:'4',cursor:'sc_YWJj',token:'secret',redirect:'https://evil.invalid',collection:'astronomy',kind:'course'}));
  assert.deepEqual([...p.keys()].sort(),['cursor','problem','q','source','stars','topic']);
  const r=A.parse(A.href('books','phys',p));assert.equal(r.params.get('q'),'a & b / c');assert.equal(r.params.get('cursor'),'sc_YWJj');
  assert.equal(r.collection,'physics');assert.equal(r.kind,'book');
  assert.equal(A.clean('source='+source+'&source='+source).has('source'),false);
  assert.equal(A.clean('q=%00bad&stars=6&year=1799&cursor=https%3A%2F%2Fevil.invalid').toString(),'');
  assert.equal(A.clean('subject=special_relativity').get('topic'),'special_relativity');
  assert.equal(A.clean('cursor=o_20').get('cursor'),'o_20');
  assert.equal(A.parse(A.href('schools','math',{school:'kaist'})).params.get('school'),'kaist');
  assert.equal(A.clean({school:'https://evil.invalid'}).has('school'),false);
  assert.equal(A.clean('school=snu&school=kaist').has('school'),false);
  const longCursor='sc_'+'A'.repeat(2797);
  assert.equal(A.parse(A.href('books','phys',{cursor:longCursor})).params.get('cursor'),longCursor);
  assert.equal(A.clean({cursor:longCursor+'A'}).has('cursor'),false);
});
test('legacy resolver accepts only known safe hints and leaves the actual destination to source metadata',()=>{
  const r=A.parse('#/archive/open?problem='+q+'&kind=contest&collection=astronomy&lang=en&return=https://evil.invalid');
  assert.equal(r.resolveLegacy,true);assert.equal(r.params.get('kind'),'contest');assert.equal(r.params.get('collection'),'astronomy');assert.equal(r.params.get('lang'),'en');assert.equal(r.params.has('return'),false);
  assert.equal(A.legacy('#/archive/contests/phys'),null);
});
