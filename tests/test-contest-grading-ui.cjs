const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const Core=require('../sim/contest-core.js');
const source=fs.readFileSync(require.resolve('../sim/contest-exam.js'),'utf8');

function page(entry,{saved,query='grading=1'}={}){
  const nodes=new Map(),storage=new Map(),intervals=[],reviews=[];
  function element(){return{innerHTML:'',textContent:'',hidden:false,children:[],style:{},classList:{add(){},remove(){},toggle(){}},after(){},insertBefore(){},querySelector(){return element();},querySelectorAll(){return[];},setAttribute(){}};}
  const get=id=>{if(!nodes.has(id))nodes.set(id,element());return nodes.get(id);};
  get('root').querySelectorAll=selector=>selector==='.page>.card'?[element(),element()]:[];
  if(saved)storage.set('hlContestGrading:'+entry.id,JSON.stringify(saved));
  const context={URL,URLSearchParams,Date,Math,JSON,Number,String,Set,Array,Object,Infinity,
    location:{search:'?id='+entry.id+'&lang=en&'+query},
    document:{documentElement:{},title:'',visibilityState:'visible',getElementById:get,querySelector:()=>element(),querySelectorAll:()=>[],createElement:element},
    localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},
    window:{ContestCore:Core,CONTEST_EXAMS:{entries:[entry]},ContestReview:{mount:(host,e,options)=>{reviews.push({host,entry:e,options});return{dispose(){}};}}},
    addEventListener(){},clearInterval(){},setInterval(fn,ms){intervals.push({fn,ms});return intervals.length;},setTimeout(){}};
  vm.runInNewContext(source,context);
  return{nodes,storage,intervals,reviews,get};
}

test('reopened grading-only typed work renders without creating a countdown interval',()=>{
  const entry={id:'typed-proof',comp:'kmo',kind:'proof',questions:2,minutes:180,paperContainsAnswers:true};
  const saved=Core.create(entry,Date.now()-7*24*60*60*1000,'online',true);
  saved.marks={1:'A completed proof.'};
  const p=page(entry,{saved});
  assert.equal(p.get('clock').textContent,'No time limit');
  assert.equal(p.intervals.length,0);
  assert.ok(p.get('root').innerHTML.includes('Review and edit them without a time limit'));
  assert.equal(p.reviews.length,0);
});

test('completed paper proof goes straight from preparation to the existing token-review panel',()=>{
  const entry={id:'paper-proof',comp:'kmo',kind:'proof',questions:2,minutes:180,paperContainsAnswers:true};
  const p=page(entry);
  assert.ok(p.get('root').innerHTML.includes('Grading and feedback only'));
  p.get('start').onclick();
  assert.equal(p.intervals.length,0);
  assert.equal(p.reviews.length,1);
  assert.equal(p.reviews[0].options.mode,'paper');
  const saved=JSON.parse(p.storage.get('hlContestGrading:'+entry.id));
  assert.equal(saved.untimed,true);assert.equal(saved.deadline,null);
  assert.equal(saved.done.reason,'manual');
  assert.equal(p.storage.has('hlContest:'+entry.id),false);
});

test('numeric saved-review links keep opening the saved review instead of starting grading preparation',()=>{
  const entry={id:'saved-proof',comp:'kmo',kind:'proof',questions:2,minutes:180};
  const p=page(entry,{query:'review=42'});
  assert.equal(p.reviews.length,1);
  assert.equal(p.reviews[0].options.reviewId,42);
  assert.equal(p.intervals.length,0);
  assert.equal(p.storage.size,0);
});

test('completed objective paper enters scan review immediately without a timed sitting',()=>{
  const entry={id:'choice-paper',comp:'kmchc',kind:'choice',questions:2,minutes:120,answersVerified:true,answers:[1,2]};
  const p=page(entry);
  p.get('start').onclick();
  assert.equal(p.intervals.length,0);
  assert.ok(p.get('root').innerHTML.includes('Submit completed paper answers'));
  assert.equal(p.reviews.length,0);
  const saved=JSON.parse(p.storage.get('hlContestGrading:'+entry.id));
  assert.equal(saved.mode,'paper');assert.equal(saved.deadline,null);assert.ok(saved.done);
});
