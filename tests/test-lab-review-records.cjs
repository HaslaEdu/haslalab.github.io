const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

function app(language='en'){
  let medalCalls=0;
  const context=vm.createContext({lang:language,cm:{me:{nickname:'Student'}},DATA:{},
    window:{labMedal:{load:async()=>{medalCalls++;return{}},estimate:()=>({}),html:()=>'<b>medal</b>'}},
    esc:x=>String(x??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),
    cmFull:()=> '2026-10-30 12:00',cmShort:()=> '10-30',URLSearchParams,encodeURIComponent});
  vm.runInContext(fs.readFileSync(require.resolve('../arena.js'),'utf8'),context);
  vm.runInContext('arMath=()=>{};arShopWire=()=>{}',context);
  return{context,medalCalls:()=>medalCalls,host:()=>({innerHTML:'',querySelector:()=>null,querySelectorAll:()=>[]})};
}
function qualitativeSession(){
  return{id:77,comp:'ortvay',year:2026,tasks:['T'],kind:'theory',review_only:true,status:'graded',score:null,points:null,
    started_at:1,pages:[],standing:{mine:99,rank:1,n:5,top_pct:1,avg:70,max:99,first:false},
    detail:{tasks:{T:{status:'graded',score:null,points:null,grading_mode:'qualitative_review',reference:'published_problem_only',official:false,items:[],
      evidence:[{page:1,quote:'F = ma',note:'State the force directions.'}],feedback:[{kind:'fix',note:'Define the coordinate axis.'}],
      review:{summary:'A promising argument with an unproved assumption.',strengths:['Clear free-body diagram.'],habits:[{habit:'Unstated assumptions',fix:'List assumptions before calculating.',pages:[1]}]}}}}};
}

test('qualitative review report shows grounded feedback without numerical score, ranking or medal',async()=>{
  const a=app(),s=qualitativeSession(),host=a.host();
  a.context.cmApi=async()=>({session:s});
  await a.context.arLabOne(host,()=>true,s.id);
  assert.ok(host.innerHTML.includes('Grading &amp; feedback')||host.innerHTML.includes('Grading & feedback'));
  assert.ok(host.innerHTML.includes('#/ortvay/review'));
  assert.ok(host.innerHTML.includes('Feedback complete · no score'));
  assert.ok(host.innerHTML.includes('No official solution or marking scheme'));
  assert.ok(host.innerHTML.includes('F = ma'));
  assert.ok(host.innerHTML.includes('State the force directions.'));
  assert.ok(host.innerHTML.includes('Define the coordinate axis.'));
  assert.ok(host.innerHTML.includes('A promising argument with an unproved assumption.'));
  assert.doesNotMatch(host.innerHTML,/null\s*\/|0\s*\/\s*0|99%|1 of 5|second sitting/);
  assert.equal(a.medalCalls(),0);
});

test('grading history distinguishes untimed submissions and retains a real zero score',async()=>{
  const a=app(),s=qualitativeSession(),host=a.host();
  const timed={id:78,comp:'ipho',year:2024,tasks:['E1'],review_only:false,status:'graded',score:0,points:20};
  a.context.cmApi=async(method,route)=>route==='/lab/active'?{active:null}:route==='/lab/tokens'?{tokens:2,ledger:[]}:route==='/lab/sessions'?{sessions:[s,timed]}:{};
  await a.context.arLabList(host,()=>true);
  assert.ok(host.innerHTML.includes('Feedback complete · no score'));
  assert.ok(host.innerHTML.includes('Grading & feedback'));
  assert.ok(host.innerHTML.includes('Timed attempt'));
  assert.ok(host.innerHTML.includes('0 / 20'));
  assert.doesNotMatch(host.innerHTML,/null\s*\/|0\s*\/\s*0/);
});

test('scored review-only reports keep the earned score but suppress timed standing',async()=>{
  const a=app('ko'),s=qualitativeSession(),host=a.host();
  s.comp='opho';s.score=0;s.points=10;s.detail={tasks:{}};
  a.context.cmApi=async()=>({session:s});
  await a.context.arLabOne(host,()=>true,s.id);
  assert.ok(host.innerHTML.includes('채점·첨삭'));
  assert.ok(host.innerHTML.includes('0 / 10'));
  assert.ok(host.innerHTML.includes('접수번호'));
  assert.ok(host.innerHTML.includes('#/opho/review'));
  assert.doesNotMatch(host.innerHTML,/99%|5명 중 1위|다시 응시한 시험/);
  assert.equal(a.medalCalls(),0);
});
