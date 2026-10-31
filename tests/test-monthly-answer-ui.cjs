const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {pathToFileURL} = require('node:url');
const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'arena.js'), 'utf8');
const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));

function app(signed=true) {
  const storage = new Map(), context = {lang:'ko',esc,cm:{me:signed?{username:'student-A'}:null}, cmBase:()=> 'https://api.test',
    cmErr:error=>error?.code||'error',localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},
    setTimeout:()=>1,clearTimeout(){},crypto:{randomUUID:()=> 'e66f46d5-00ab-45df-a2ba-a8599bd3f18e'}};
  vm.createContext(context); vm.runInContext(source,context); context.arMath=()=>{};
  return {context,storage};
}
const sample = {id:4,attempts:{limit:3,used:0,remaining:3},answerSheet:{version:'2026-11-v1',limit:3,parts:[
  {id:'a',label_ko:'운동방정식',label_en:'Equation of motion',points:40},
  {id:'b',label_ko:'에너지',label_en:'Energy',points:60}
]}};
const plain=x=>JSON.parse(JSON.stringify(x));

test('every actual problem has labelled answer and working boxes, a printable form and authoritative remaining attempts', async()=>{
  const {getMonthlyAnswerSheet}=await import(pathToFileURL(path.join(root,'monthly-problems.mjs')).href);
  const {context}=app();
  for(const id of [4,5,6]) {
    const p={id,attempts:{limit:3,used:1,remaining:2},answerSheet:getMonthlyAnswerSheet(id)};
    const html=context.arMonthlyAnswerHtml(p,true);
    assert.equal([...html.matchAll(/data-sheet-answer="/g)].length,p.answerSheet.parts.length);
    assert.equal([...html.matchAll(/data-sheet-working="/g)].length,p.answerSheet.parts.length);
    assert.ok(p.answerSheet.parts.every(part=>html.includes(`data-sheet-part="${part.id}"`)));
    assert.match(html,/남은 제출 기회 2 \/ 3회/);
    assert.ok(html.includes(`sim/monthly-answer-sheet.html?id=${id}&lang=ko`));
    assert.match(html,/답안 제출 · 기회 1회 사용/);
    assert.match(html,/답안지 촬영/);assert.match(html,/QR/);assert.match(html,/네 모서리 보정/);
    assert.match(html,/LaTeX/);
  }
});

test('guests can inspect the answer-sheet format and exhausted accounts cannot submit again',()=>{
  const guest=app(false).context.arMonthlyAnswerHtml({...sample,attempts:null},true);
  assert.match(guest,/문제당 제출 기회 3회/);
  assert.match(guest,/id="arLogin"/);
  assert.equal([...guest.matchAll(/<fieldset[^>]* disabled/g)].length,2);
  assert.match(guest,/type="submit" disabled/);
  const exhausted=app().context.arMonthlyAnswerHtml({...sample,attempts:{limit:3,used:3,remaining:0}},true);
  assert.match(exhausted,/3회를 모두 사용/);
  assert.match(exhausted,/type="submit" disabled/);
});

test('parts must contain both answer and reasoning, may be left blank together, and remain canonical',()=>{
  const {context}=app(),values={'a':{answer:' \\omega^2=k/m ',working:' From Newton: $m\\ddot x=-kx$. '},'b':{answer:'',working:''}};
  const form={querySelector:selector=>{const [,kind,id]=/data-sheet-(answer|working)="([^"]+)"/.exec(selector);return{value:values[id][kind]};}};
  assert.deepEqual(plain(context.arSheetParts(sample,form)),[
    {id:'a',answer:'\\omega^2=k/m',working:'From Newton: $m\\ddot x=-kx$.'},{id:'b',answer:'',working:''}
  ]);
  values.a.working='';assert.throws(()=>context.arSheetParts(sample,form),e=>e.sheetMessage.includes('a:'));
  values.a.answer='';assert.throws(()=>context.arSheetParts(sample,form),e=>e.sheetMessage.includes('한 소문항'));
  values.a.answer='a'.repeat(4001);values.a.working='reason';assert.throws(()=>context.arSheetParts(sample,form),e=>e.sheetMessage.includes('4,000'));
});

test('LaTeX previews preserve complete display equations and escape arbitrary markup',()=>{
  const {context}=app();
  assert.equal(context.arSheetFinalPreview('No resonance'),'No resonance');
  assert.equal(context.arSheetFinalPreview('\\omega^2=k/m'),'<div>$$\\omega^2=k/m$$</div>');
  const display=context.arSheetWorkingPreview('Let\n$$\n\\frac{dE}{dt}=P\n$$\nthen continue.');
  assert.ok(display.includes('$$\n\\frac{dE}{dt}=P\n$$'));
  assert.ok(!display.includes('$$<br>'));
  assert.ok(!context.arSheetFinalPreview('<img src=x onerror=alert(1)>').includes('<img'));
  const saved=context.arMonthlySavedAnswer({answer_sheet:{parts:[{id:'<bad>',answer:'<script>x</script>',working:'$a+b$'}]}});
  assert.ok(!saved.includes('<script>'));assert.ok(saved.includes('&lt;bad&gt;'));
});

test('draft keys separate accounts and API bases without copying bearer tokens into storage keys',()=>{
  const {context}=app(),one=context.arSheetDraftKey(sample);
  context.cm.me.username='student-B';assert.notEqual(context.arSheetDraftKey(sample),one);
  context.cm.me.username='student-A';context.cmBase=()=> 'https://another-api.test';assert.notEqual(context.arSheetDraftKey(sample),one);
  context.cm.me=null;assert.equal(context.arSheetDraftKey(sample),null);
  assert.ok(!one.includes('Bearer'));
});

test('reusing a deleted account name cannot inherit its draft, and renaming an existing account keeps its draft',()=>{
  const {context}=app();context.cm.me={id:41,username:'reusable-name'};
  const first=context.arSheetDraftKey(sample);
  context.cm.me={id:92,username:'reusable-name'};assert.notEqual(context.arSheetDraftKey(sample),first);
  context.cm.me={id:41,username:'renamed-account'};assert.equal(context.arSheetDraftKey(sample),first);
  context.cm.me={username:'41'};assert.notEqual(context.arSheetDraftKey(sample),first,'legacy names and immutable ids occupy separate namespaces');
});

function bindingFixture(context,p=plain(sample)) {
  const fields=new Map(),previews=new Map(),button={disabled:false},out={innerHTML:''},counter={textContent:''};
  for(const part of p.answerSheet.parts) for(const kind of ['answer','working']) {
    fields.set(`${kind}:${part.id}`,{value:'',disabled:false});previews.set(`${kind}:${part.id}`,{innerHTML:''});
  }
  const form={querySelector(selector){
    if(selector==='button[type=submit]')return button;
    let m=/^\[data-sheet-(answer|working)="([^"]+)"\]$/.exec(selector);if(m)return fields.get(`${m[1]}:${m[2]}`);
    m=/^\[data-sheet-(answer|working)-preview="([^"]+)"\]$/.exec(selector);if(m)return previews.get(`${m[1]}:${m[2]}`);
    throw Error('unexpected selector '+selector);
  },querySelectorAll(selector){return selector.startsWith('[data-sheet-answer]')?[...fields.values()]:[];}};
  const rootNode={querySelector:selector=>({'#arSheetF':form,'#arOut':out,'#arSheetAttempts':counter}[selector])};
  context.arBindMonthlyAnswer(rootNode,p,()=>true,false);
  return{form,fields,button,out,counter,p};
}

test('network retries reuse one request id; successful acceptance requires an edit before another attempt',async()=>{
  const {context,storage}=app(),requests=[];
  context.cmApi=async(method,url,payload)=>{
    requests.push(plain(payload));
    if(requests.length===1)throw{code:'network_error'};
    return{status:'graded',score:70,detail:{scores:[]},attempts:{limit:3,used:1,remaining:2}};
  };
  const a=bindingFixture(context);
  a.fields.get('answer:a').value='\\omega^2=k/m';a.fields.get('working:a').value='Newton law';
  a.fields.get('answer:a').oninput();
  await a.form.onsubmit({preventDefault(){}});assert.equal(a.button.disabled,false);
  await a.form.onsubmit({preventDefault(){}});
  assert.equal(requests.length,2);assert.equal(requests[0].request_id,requests[1].request_id);
  assert.equal(requests[1].sheet_version,'2026-11-v1');assert.equal(requests[1].parts.length,2);
  assert.equal(a.counter.textContent,'남은 제출 기회 2 / 3회');assert.equal(a.button.disabled,true);
  assert.ok([...storage.values()].some(v=>JSON.parse(v).accepted===true));
  a.fields.get('working:a').value+=' with dimensions checked';a.fields.get('working:a').oninput();assert.equal(a.button.disabled,false);
  assert.equal(JSON.parse([...storage.values()][0]).request_id,null);
});

test('repository-owned diagrams inline with inherited colors while unknown assets stay ordinary images',()=>{
  const {context}=app();context.HL_MONTHLY_FIGURES={render:path=>path==='weekly/figures/proton-chain.svg'?'<svg data-safe="1"></svg>':''};
  assert.match(context.arPublishedText('![chain](weekly/figures/proton-chain.svg)'),/<svg data-safe="1"><\/svg>/);
  assert.match(context.arPublishedText('![other](weekly/figures/unknown.svg)'),/<img src="weekly\/figures\/unknown.svg"/);
  const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
  assert.match(html,/--monthly-figure-accent:#c4b2ee/);
  assert.ok(!html.includes('.ar .arfigure{margin:1.4em 0;padding:16px;background:#f8fafc'));
});
