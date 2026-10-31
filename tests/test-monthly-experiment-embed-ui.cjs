const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'..','arena.js'),'utf8');
const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const problem={id:8,no:5,title:'Pressure waves',body:'## A. 측정\n관의 지름을 구하여라.',points:100,subject:'Physics',level:12,open:true,closes_at:1796050800,answerSheet:{key:'pressure-wave-experiment-v1',parts:[{id:'A.1',points:100}]}};

class Events{
  constructor(){this.listeners=new Map();}
  addEventListener(name,fn){if(!this.listeners.has(name))this.listeners.set(name,new Set());this.listeners.get(name).add(fn);}
  removeEventListener(name,fn){this.listeners.get(name)?.delete(fn);}
  emit(name,event={}){for(const fn of [...(this.listeners.get(name)||[])])fn(event);}
  count(){return [...this.listeners.values()].reduce((total,set)=>total+set.size,0);}
}
class Element extends Events{
  constructor(){super();this.dataset={};this.attributes={};this.hidden=false;this.isConnected=true;this.srcWrites=[];}
  setAttribute(name,value){this.attributes[name]=String(value);}
  getAttribute(name){return this.attributes[name]??null;}
  set src(value){this._src=value;this.srcWrites.push(value);}
  get src(){return this._src||'';}
}
function fixture({wide=false,theme='light',language='ko',bind=true}={}){
  const win=new Events(),media=new Events(),frame=new Element(),statement=new Element(),lab=new Element(),workspace=new Element(),messages=[],observers=[];
  media.matches=wide;lab.hidden=true;
  const buttons=['problem','lab','split'].map(mode=>{const button=new Element();button.dataset.experimentMode=mode;return button;});
  frame.dataset.experimentSrc='sim/monthly-pressure-wave/index.html?embed=1&id=8&lang='+language+'&view=cmd';
  frame.contentWindow={postMessage:(data,origin)=>messages.push({data:JSON.parse(JSON.stringify(data)),origin})};
  workspace.querySelector=selector=>({'iframe':frame,'#arStmt':statement,'#arExperimentLab':lab}[selector]||null);
  workspace.querySelectorAll=selector=>selector==='[data-experiment-mode]'?buttons:[];
  const root={querySelector:selector=>selector==='.ar-experiment'?workspace:null};
  let identity='owner',connected=true;
  const document={documentElement:{dataset:{theme}}};
  const context={lang:language,esc,window:win,document,location:{origin:'https://haslalab.org'},MutationObserver:class{
    constructor(callback){this.callback=callback;this.disconnected=false;observers.push(this);}
    observe(target,options){this.target=target;this.options=options;}
    disconnect(){this.disconnected=true;}
    trigger(){if(!this.disconnected)this.callback();}
  }};
  win.matchMedia=query=>{assert.equal(query,'(min-width: 1200px)');return media;};
  vm.createContext(context);vm.runInContext(source,context,{filename:'arena.js'});
  if(bind)context.arBindMonthlyExperiment(root,problem,()=>connected&&identity==='owner');
  return{context,root,workspace,frame,statement,lab,buttons,win,media,document,messages,observers,
    click:mode=>buttons.find(button=>button.dataset.experimentMode===mode).onclick?.(),
    resize:value=>{media.matches=value;media.emit('change');},
    setIdentity:value=>{identity=value;},setAlive:value=>{connected=value;},
    cleanup:()=>vm.runInContext('ar.monthlyExperimentCleanup',context)};
}

test('only the pressure-wave experiment adds a titled lazy same-origin iframe',()=>{
  const {context}=fixture({bind:false});
  for(const answerSheet of [undefined,{key:'other-experiment'},{key:'theory-v1'}]){
    const html=context.arMonthlyExperimentHtml({...problem,answerSheet});
    assert.match(html,/id="arStmt"/);assert.match(html,/<h2>A\. 측정<\/h2>/);assert.doesNotMatch(html,/iframe|ar-experiment-toolbar/);
  }
  const html=context.arMonthlyExperimentHtml(problem),iframe=html.match(/<iframe\b[^>]*>/)?.[0];
  assert.ok(iframe);assert.match(iframe,/title="압력파 CMD 실험"/);
  assert.match(iframe,/data-experiment-src="sim\/monthly-pressure-wave\/index\.html\?embed=1&amp;id=8&amp;lang=ko&amp;view=cmd"/);
  assert.doesNotMatch(iframe,/\ssrc=/,'the frame must remain unloaded until the apparatus is visible');
  assert.doesNotMatch(html,/target="_blank"|Bearer|hlCmTok/);
  context.lang='en';assert.match(context.arMonthlyExperimentHtml(problem),/Pressure-wave CMD experiment/);assert.match(context.arMonthlyExperimentHtml(problem),/amp;lang=en/);
});

test('narrow screens begin with the statement and no simulator load',()=>{
  const f=fixture();
  assert.equal(f.workspace.dataset.mode,'problem');assert.equal(f.statement.hidden,false);assert.equal(f.lab.hidden,true);
  assert.deepEqual(f.frame.srcWrites,[]);assert.equal(f.buttons[0].getAttribute('aria-pressed'),'true');
  f.cleanup()();assert.deepEqual(f.frame.srcWrites,[],'disposing an unopened apparatus must not start navigation');
});

test('a screen at least 1200px wide starts split with one correctly themed simulator',()=>{
  const f=fixture({wide:true,theme:'dark'});
  assert.equal(f.workspace.dataset.mode,'split');assert.equal(f.statement.hidden,false);assert.equal(f.lab.hidden,false);
  assert.equal(f.buttons[2].getAttribute('aria-pressed'),'true');
  assert.deepEqual(f.frame.srcWrites,['sim/monthly-pressure-wave/index.html?embed=1&id=8&lang=ko&view=cmd&theme=dark']);
});

test('problem, experiment and split controls preserve the same iframe and its loaded document',()=>{
  const f=fixture();f.click('lab');const src=f.frame.src;
  assert.equal(f.workspace.dataset.mode,'lab');assert.equal(f.statement.hidden,true);assert.equal(f.lab.hidden,false);
  f.frame.savedExperiment={runs:[1,2,3]};
  f.click('problem');assert.equal(f.frame.src,src);assert.equal(f.lab.hidden,true);assert.equal(f.statement.hidden,false);
  f.click('lab');f.resize(true);f.click('split');
  assert.equal(f.workspace.querySelector('iframe'),f.frame);assert.equal(f.frame.srcWrites.length,1);
  assert.deepEqual(f.frame.savedExperiment.runs,[1,2,3]);assert.equal(f.workspace.dataset.mode,'split');
  assert.equal(f.buttons.filter(button=>button.getAttribute('aria-pressed')==='true').length,1);
});

test('theme updates are sent to the exact site origin without iframe navigation',()=>{
  const f=fixture();f.document.documentElement.dataset.theme='dark';f.observers[0].trigger();
  assert.equal(f.messages.length,0,'a hidden, unloaded apparatus has no recipient');
  f.click('lab');f.frame.emit('load');
  assert.deepEqual(f.messages,[{data:{type:'haslalab-experiment-theme',theme:'dark'},origin:'https://haslalab.org'}]);
  f.document.documentElement.dataset.theme='light';f.observers[0].trigger();
  assert.deepEqual(f.messages.at(-1),{data:{type:'haslalab-experiment-theme',theme:'light'},origin:'https://haslalab.org'});
  assert.equal(f.frame.srcWrites.length,1);assert.ok(f.frame.src.endsWith('&theme=dark'));
  assert.equal(f.observers[0].target,f.document.documentElement);assert.deepEqual(Array.from(f.observers[0].options.attributeFilter),['data-theme']);
});

test('shrinking a split layout keeps the apparatus open and preserves its document',()=>{
  const f=fixture({wide:true});f.resize(false);
  assert.equal(f.workspace.dataset.mode,'lab');assert.equal(f.statement.hidden,true);assert.equal(f.lab.hidden,false);
  f.click('split');assert.equal(f.workspace.dataset.mode,'lab','a narrow viewport cannot force unreadable split columns');
  f.resize(true);assert.equal(f.workspace.dataset.mode,'lab','resizing wider does not discard a deliberately selected mode');
  assert.equal(f.frame.srcWrites.length,1);
});

test('leaving the route disposes observers and controls and clears the private simulator once',()=>{
  for(const event of ['hashchange','pagehide']){
    const f=fixture({wide:true});f.win.emit(event);
    assert.equal(f.frame.src,'about:blank');assert.equal(f.frame.srcWrites.length,2);
    assert.equal(f.observers[0].disconnected,true);assert.equal(f.win.count(),0);assert.equal(f.media.count(),0);assert.equal(f.frame.count(),0);
    assert.ok(f.buttons.every(button=>button.onclick===null));assert.equal(f.cleanup(),null);
    f.win.emit(event);f.observers[0].trigger();assert.equal(f.frame.srcWrites.length,2);assert.equal(f.messages.length,0);
  }
});

test('account or page identity changes prevent further interaction with the old private apparatus',()=>{
  for(const event of ['storage','focus']){
    const f=fixture({wide:true});f.setIdentity('another-owner');f.win.emit(event,{key:'hlCmTok'});
    assert.equal(f.cleanup(),null);assert.equal(f.frame.src,'about:blank');assert.equal(f.win.count(),0);
  }
  const detached=fixture({wide:true});detached.workspace.isConnected=false;detached.observers[0].trigger();
  assert.equal(detached.cleanup(),null);assert.equal(detached.frame.src,'about:blank');
  const stale=fixture();stale.setAlive(false);stale.click('lab');assert.equal(stale.cleanup(),null);assert.equal(stale.frame.srcWrites.length,0);
});

test('the real problem renderer keeps the answer form outside the simulator workspace and binds it after the apparatus',async()=>{
  const f=fixture({bind:false}),calls=[],root={innerHTML:'',querySelector:()=>null},context=f.context;
  context.cm={me:{id:1}};context.arMath=()=>{};context.arBindMonthlyPhotos=()=>{};
  context.arT=()=>({pts:'점',weekH:'월별 문제'});
  for(const name of ['arPeriodId','arPeriodLabel','arProblemKindBadge','arLevel','tierName','arDeadline','arLeft'])context[name]=()=>'';
  context.arMonthlyAnswerHtml=()=>'<form id="arSheetF"><textarea data-sheet-answer="A.1"></textarea></form>';
  context.arBindMonthlyExperiment=()=>calls.push('experiment');context.arBindMonthlyAnswer=()=>calls.push('answer');
  await context.arProblem(root,()=>true,8,{problem,health:{ocr:true}});
  assert.deepEqual(calls,['experiment','answer']);
  const stack=[];let answerAncestors=null;
  for(const match of root.innerHTML.matchAll(/<\/?([a-z][a-z0-9]*)\b([^>]*)>/gi)){
    if(match[0].startsWith('</')){stack.pop();continue;}
    if(/\bid="arAns"/.test(match[2]))answerAncestors=[...stack];
    if(!/^(?:area|base|br|col|embed|hr|img|input|link|meta|param|source|track|wbr)$/i.test(match[1]))stack.push(match[0]);
  }
  assert.ok(answerAncestors);assert.ok(answerAncestors.every(tag=>!/(?:\bclass="[^"]*\bar-experiment\b|\bid="arExperimentLab")/.test(tag)));
  assert.equal((root.innerHTML.match(/<iframe\b/g)||[]).length,1);assert.match(root.innerHTML,/<form id="arSheetF">/);
});
