const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const Network=require('../sim/exam-network.js');
const Review=require('../sim/contest-review.js');

function app(lang='ko'){
  const context={lang,cm:{me:null},esc:s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),cmShort:()=> '10-30'};
  vm.createContext(context);vm.runInContext(fs.readFileSync(require.resolve('../arena.js'),'utf8'),context);
  return context;
}

test('ungraded reports show the server fee for single, bundled and discounted rounds in either language',()=>{
  for(const lang of ['ko','en']){
    const a=app(lang);
    for(const cost of [0.2,0.3,0.5])for(const review_only of [false,true]){
      const labels=a.arLabLabels({cost,review_only});
      assert.ok(labels.payBtn.includes(String(cost)));
      assert.ok(labels.payNote.includes(String(cost)));
      assert.doesNotMatch(labels.payNote,/one exam token|토큰 1개/);
    }
    assert.equal(vm.runInContext('arLabCost({kind:"mixed"})',a),0.5);
    assert.equal(vm.runInContext('arLabCost({kind:"theory"})',a),0.3);
  }
});

test('token history displays actual decimal charges and a readable set discount without internal pricing metadata',()=>{
  for(const lang of ['ko','en']){
    const a=app(lang),html=a.arLedgerHtml([
      {delta:-0.3,reason:'grade',note:JSON.stringify({pricing_version:2,cost:0.3,scope:'theory',units:3}),exam_key:'ipho2024',created_at:1},
      {delta:-0.2,reason:'grade',note:JSON.stringify({pricing_version:2,cost:0.2,scope:'lab',paired_with:12,discount:0.1}),created_at:1},
      {delta:1,reason:'grant',note:'<b>admin note</b>',created_at:1},
      {delta:0,reason:'grade',note:'half',created_at:1},
    ]);
    assert.match(html,/−0\.3/);assert.match(html,/−0\.2/);assert.match(html,/−0\.5/);assert.match(html,/\+1/);
    assert.match(html,/#\/lab\/12/);assert.match(html,/세트 할인|Set discount/);
    assert.match(html,/&lt;b>admin note&lt;\/b>/);
    assert.doesNotMatch(html,/pricing_version|paired_with|"units"|\[object Object\]/);
  }
});

test('exam fee copy uses the server quote and permits a complementary round with 0.2 token',()=>{
  const source=fs.readFileSync(require.resolve('../sim/exam.html'),'utf8');
  const begin=source.indexOf('const COST ='),end=source.indexOf('const R =',begin);
  const a=vm.createContext({Q:new URLSearchParams('h=1'),MIX:false,SES:null});
  vm.runInContext(source.slice(begin,end),a);
  assert.equal(vm.runInContext('COST()',a),0.3);
  a.SES={cost:0.2};assert.equal(vm.runInContext('COST()',a),0.2);
  assert.equal(vm.runInContext('costify("one exam token / 1 token / 토큰 1개")',a),'0.2 token / 0.2 token / 토큰 0.2개');
  a.SES=null;a.MIX=true;assert.equal(vm.runInContext('COST()',a),0.5);
  assert.match(source,/EX\.pair && !MIX \? 0\.2 : COST\(\)/);
  assert.doesNotMatch(source,/\$\{n - COST\(\)\}/);
});

test('grading transport sends the displayed maximum fee for both pay and submit',async()=>{
  const sent=[];
  const client=Review.createClient({getBase:()=> 'https://local.test',getToken:()=> 'local-test',fetch:async(url,options)=>{
    sent.push({url,body:JSON.parse(options.body)});return{ok:true,json:async()=>({})};
  }});
  await client.pay(12,0.2);await client.submit(12,0.3);
  assert.deepEqual(sent.map(x=>x.body),[{max_cost:0.2},{grade:true,max_cost:0.3}]);
});

test('a fee or discount-partner change refreshes the exam display even when no answer page changes',()=>{
  const a={id:1,status:'scanning',paid:false,cost:0.2,paired_with:12,pages:[]};
  const before=Network.sessionSignature(a);
  assert.notEqual(before,Network.sessionSignature({...a,cost:0.3}));
  assert.notEqual(before,Network.sessionSignature({...a,paired_with:13}));
  assert.equal(before,Network.sessionSignature({...a,now:999}),'a clock tick alone must not repaint the answer editor');
});
