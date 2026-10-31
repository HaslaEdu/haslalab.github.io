import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {presentProtonText,PROTON_PART_LABELS} from './src/proton-presentation.js';
const require=createRequire(import.meta.url),katex=require('../vendor/katex/katex.min.js');
const original=JSON.parse(readFileSync(new URL('./weekly/2026-W44.json',import.meta.url),'utf8')).problems[0];

test('the ten legacy subquestions display in A and B while all original records remain unchanged',()=>{
  const copy=JSON.stringify(original);
  for(const lang of ['ko','en']){
    const body=presentProtonText(original['body_'+lang],'body_'+lang);
    const labels=[...body.matchAll(/^### ([AB]\.[1-5]) /gm)].map(m=>m[1]);
    assert.deepEqual(labels,PROTON_PART_LABELS);
    assert.equal((body.match(/^## Part A\./gm)||[]).length,1);
    assert.equal((body.match(/^## Part B\./gm)||[]).length,1);
    const scores=[...body.matchAll(/^### [AB]\.[1-5] [^\n]+\((\d+)(?:점| points)\)$/gm)].map(m=>Number(m[1]));
    assert.deepEqual(scores,[10,13,10,17,10,7,10,6,7,10]);
    assert.equal(scores.reduce((sum,n)=>sum+n,0),100);
    assert.doesNotMatch(body,/원문 \d|Original allocation|Original total/);
    assert.doesNotMatch(body,/\([a-j]\)/);
    assert.ok(body.indexOf('## Part B.')<body.indexOf('### B.1 '));
    assert.ok(body.indexOf('### A.5 ')<body.indexOf('## Part B.'));
    assert.equal(presentProtonText(body,'body_'+lang),body);
  }
  assert.equal(JSON.stringify(original),copy,'the persisted source, rubric and answer keys were not mutated');
});

test('the requested neighbour sum is an intact display equation with limits, not a collapsed inline symbol',()=>{
  for(const lang of ['ko','en']){
    const body=presentProtonText(original['body_'+lang],'body_'+lang);
    const part=body.split(/^### A\.2 /m)[1].split(/^### A\.3 /m)[0];
    assert.match(part,/\$\$\\displaystyle\\sum_\{k=1\}\^\{\\infty\}\(\\cdots\)\$\$/);
    assert.doesNotMatch(part,/(?<!\$)\$\\sum_\{k=1\}/);
    const html=katex.renderToString(String.raw`\displaystyle\sum_{k=1}^{\infty}(\cdots)`,{displayMode:true,throwOnError:true});
    assert.match(html,/munderover/,'lower and upper limits remain attached to the sum');
  }
});

test('worked solutions and prose references follow the new labels without changing mathematical expressions',()=>{
  for(const lang of ['ko','en']){
    const key='model_'+lang,raw=original[key],shown=presentProtonText(raw,key);
    assert.deepEqual([...shown.matchAll(/^### ([AB]\.[1-5]) /gm)].map(m=>m[1]),PROTON_PART_LABELS);
    assert.doesNotMatch(shown,/^## \([a-j]\)/m);
    assert.doesNotMatch(shown,/(?<!\$)\([edj]\)/);
    const formulae=text=>[...text.matchAll(/\$\$[\s\S]*?\$\$|\$[^$\n]+\$/g)].map(m=>m[0]);
    assert.deepEqual(formulae(shown),formulae(raw));
    assert.equal(presentProtonText(shown,key),shown);
  }
  const sample='## (a) Title\nUse (d), but keep $f(a)+x(d)$ unchanged.\n\n## (f) Other';
  assert.match(presentProtonText(sample,'model_en'),/Use A\.4, but keep \$f\(a\)\+x\(d\)\$ unchanged/);
  assert.equal(presentProtonText('Other text (a) without a legacy heading.'),'Other text (a) without a legacy heading.');
  assert.equal(presentProtonText(null),null);
});

test('the complete bilingual public problem and solution math parses in KaTeX',()=>{
  let equations=0;
  for(const field of ['body_ko','body_en','model_ko','model_en']){
    const shown=presentProtonText(original[field],field);
    for(const match of shown.matchAll(/\$\$([\s\S]*?)\$\$|\$([^$\n]+)\$/g)){
      assert.doesNotThrow(()=>katex.renderToString(match[1]??match[2],{displayMode:match[1]!==undefined,throwOnError:true}),field+': '+match[0]);
      equations++;
    }
  }
  assert.ok(equations>200);
});
