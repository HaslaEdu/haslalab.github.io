// Exercise actual application callbacks with the original Python in WebAssembly.
// Source/physics parity lives in test-ipho2019-e1-python.mjs.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import {loadOriginalPython,OpticalLab,vis} from '../sim/ipho2019/e1-python.mjs';

await loadOriginalPython();
const close=(a,b)=>assert.ok(Math.abs(a-b)<1e-9,`${a} != ${b}`);
const source=readFileSync(new URL('../sim/ipho2019/e1-app.mjs',import.meta.url),'utf8')
  .replace(/^import .*;\r?\n/gm,'')
  .replace('await loadOriginalPython();','')
  .replace('await startScene();','startScene();');

function appHarness(language='ko'){
  const nodes=new Map(),events=new Map(),frames=new Map(),canvasCalls=[];
  let now=0,nextFrame=1,seed=201901,renderedLab,callbacks,placement=[136,104];
  const context2d=Object.fromEntries(['fillRect','strokeRect','beginPath','arc','fill','stroke','lineTo','moveTo','closePath','save','restore','translate','rotate','fillText']
    .map(name=>[name,(...args)=>canvasCalls.push([name,...args])]));
  context2d.createRadialGradient=()=>({addColorStop(){}});
  const node=id=>{
    if(!nodes.has(id)){
      const classes=new Set();
      nodes.set(id,{id,innerHTML:'',textContent:'',value:'',checked:false,hidden:false,open:false,width:1440,height:450,style:{},dataset:{},
        classList:{toggle(name,on){if(on)classes.add(name);else classes.delete(name);},contains:name=>classes.has(name)},
        querySelector(selector){return node(id+selector);},querySelectorAll(){return[];},setAttribute(){},
        showModal(){this.open=true;},close(){this.open=false;},getContext:()=>context2d,
        getBoundingClientRect:()=>({left:0,top:0,width:1440,height:450}),setPointerCapture(){}});
    }
    return nodes.get(id);
  };
  const groups={
    lang:['ko','en'],equipment:['ruler','disk','holder','screen','tape6','tape','ruler8'],view:['perspective','top'],
    move:['0,-1','-1,0','1,0','0,1'],rotate:['2','-2'],fine:['0.25','-0.25'],holder:['2','-2'],
  };
  const query=selector=>{
    const key=selector.match(/^\[data-(\w+)\]$/)?.[1];
    return (groups[key]||[]).map(value=>{const n=node(`${key}:${value}`);n.dataset[key]=value;return n;});
  };
  const document={hidden:false,documentElement:{lang:''},title:'',getElementById:node,querySelectorAll:query,
    addEventListener:(name,fn)=>events.set(name,fn)};
  runInNewContext(source,{
    OpticalLab,vis,URL,URLSearchParams,document,location:{search:'?lang='+language,href:'https://haslalab.org/sim/ipho2019_E1_web.html?lang='+language},
    performance:{now:()=>now},console,crypto:{getRandomValues(array){array[0]=seed++;return array;}},history:{replaceState(){}},
    sessionStorage:{getItem(){throw Error('The original lab starts fresh');},setItem(){throw Error('The original lab does not save a browser draft');}},
    window:{addEventListener:(name,fn)=>events.set('window:'+name,fn)},
    requestAnimationFrame:fn=>{const id=nextFrame++;frames.set(id,fn);return id;},cancelAnimationFrame:id=>frames.delete(id),
    createOpticalScene:(_container,options)=>{callbacks=options;return{
      update:lab=>{renderedLab=lab;},selected(){},setView(){},focus(){},dispose(){},placementPoint:()=>placement,
    };},
  },{filename:'e1-app-behavior.mjs'});
  assert.ok(renderedLab,'the application must pass its real Python-backed lab to the renderer');
  return{node,canvasCalls,lab:()=>renderedLab,callbacks:()=>callbacks,
    choose(key){node('selection').value=key;node('selection').onchange();},
    mount(key,point=placement){placement=point;node('equipment:'+key).onclick();},
    frame(timestamp){now=timestamp;const [id,fn]=frames.entries().next().value;frames.delete(id);fn(timestamp);},
    visibility(hidden,timestamp){now=timestamp;document.hidden=hidden;events.get('visibilitychange')();},
    scheduled:()=>frames.size,dispose:()=>renderedLab.dispose()};
}

test('the common tray, stage and panel start with the original empty equipment tray in both languages',()=>{
  for(const language of ['ko','en']){
    const app=appHarness(language),lab=app.lab(),markup=app.node('app').innerHTML;
    try{
      for(const name of ['tray','stage','panel'])assert.ok(markup.includes(`class="${name}"`));
      assert.doesNotMatch(markup,/masthead|titlebar|workbench|class="footer"/);
      assert.match(markup,language==='ko'?/장비/:/Equipment/);
      assert.equal(Object.values(lab.obj).some(item=>item.on),false);
      assert.equal(lab.tape_on,false);assert.equal(lab.laser_on,false);assert.equal(lab.clock,0);
      assert.equal(app.node('power').disabled,true);assert.equal(app.node('selection').value,'');
      for(const value of [lab.n_disk,lab.n_prism,lab.lam_over_d])assert.equal(markup.includes(String(value)),false,'hidden specimen values are not readouts');
    }finally{app.dispose();}
  }
});

test('equipment buttons place apparatus at the camera centre and retain original measuring-tape placement',()=>{
  const app=appHarness(),lab=app.lab();
  try{
    app.mount('ruler',[120,160]);assert.deepEqual(lab.obj.ruler.pos,[120,160]);assert.equal(lab.obj.ruler.on,true);
    assert.equal(app.node('power').disabled,false);
    app.mount('tape',[160,120]);assert.deepEqual(lab.tape_a,[100,134]);assert.deepEqual(lab.tape_b,[220,134]);
    app.mount('ruler');assert.equal(lab.obj.ruler.on,false);assert.equal(app.node('power').disabled,true);
    const fresh=appHarness();try{assert.equal(fresh.lab().tape_on,false);assert.equal(fresh.lab().obj.ruler.on,false);}finally{fresh.dispose();}
  }finally{app.dispose();}
});

test('selection callbacks raise transparent rulers above and below the disk without altering specimen values',()=>{
  const app=appHarness(),lab=app.lab();
  try{
    app.mount('disk',[136,96]);app.mount('ruler8',[136,96]);
    const specimen=[lab.n_disk,lab.n_prism,lab.lam_over_d];
    app.choose('ruler8');assert.equal(lab.order.at(-1),'ruler8');assert.equal(lab.in_ruler8(136,96),true);
    app.choose('disk');assert.equal(lab.order.at(-1),'disk');assert.equal(lab.in_ruler8(136,96),false);
    app.choose('ruler8');assert.equal(lab.in_ruler8(136,96),true);
    assert.deepEqual([lab.n_disk,lab.n_prism,lab.lam_over_d],specimen);
    app.choose('');assert.equal(app.node('focus').disabled,true);
  }finally{app.dispose();}
});

test('dragging beyond the cubicle keeps apparatus until the original release rule returns it to the tray',()=>{
  const app=appHarness(),lab=app.lab();
  try{
    app.mount('disk',[136,96]);app.callbacks().onMove('disk',[-100,-100]);
    assert.equal(lab.obj.disk.on,true);app.callbacks().onRelease('disk');assert.equal(lab.obj.disk.on,false);
    app.mount('tape',[160,120]);app.callbacks().onTapeMove('a',[-30,120]);
    assert.equal(lab.tape_on,true);app.callbacks().onRelease('tape_a');assert.equal(lab.tape_on,false);
  }finally{app.dispose();}
});

test('animation batches original Python ticks every quarter second instead of crossing WebAssembly every frame',()=>{
  const app=appHarness(),lab=app.lab(),advance=lab.advance.bind(lab),steps=[];
  lab.advance=(...args)=>{steps.push(args);return advance(...args);};
  try{
    app.frame(1000);assert.equal(steps.length,1);close(lab.clock,0);
    app.frame(1100);app.frame(1249);assert.equal(steps.length,1);close(lab.clock,0);
    app.frame(1250);assert.equal(steps.length,2);close(lab.clock,.25);
    app.node('speed').value='10';app.node('speed').onchange();app.frame(1500);close(lab.clock,2.75);
  }finally{app.dispose();}
});

test('visibility callbacks advance the hidden lab clock and lighting at the selected speed',()=>{
  const app=appHarness(),lab=app.lab();
  try{
    app.frame(1000);app.frame(2000);close(lab.clock,1);
    app.node('speed').value='10';app.node('speed').onchange();
    app.visibility(true,2500);assert.equal(app.scheduled(),0);
    app.visibility(false,22500);close(lab.clock,201);close(lab.t,201);
    assert.equal(lab.dark,true);assert.equal(app.node('lightState').classList.contains('dark'),true);
    assert.equal(app.scheduled(),1);assert.equal(lab.light_phase()[0],true);
  }finally{app.dispose();}
});

test('the screen front view draws physical tape graduations and lets the user move a tape endpoint',()=>{
  const app=appHarness(),lab=app.lab();
  try{
    app.callbacks().onOpenScreen();assert.equal(app.node('front').open,false);
    app.mount('screen',[136,30]);app.callbacks().onOpenScreen();assert.equal(app.node('front').open,true);
    assert.ok(app.canvasCalls.some(([name])=>name==='fillText'),'the measurement view must draw printed graduations');
    const canvas=app.node('frontCanvas'),event=([x,y])=>({clientX:(x/132+.5)*canvas.width,clientY:(y/132+canvas.height/canvas.width*.5)*canvas.width,pointerId:1});
    canvas.onpointerdown(event(lab.ftape_a));canvas.onpointermove(event([-40,5]));canvas.onpointerup();
    close(lab.ftape_a[0],-40);close(lab.ftape_a[1],5);
    app.node('closeFront').onclick();assert.equal(app.node('front').open,false);
  }finally{app.dispose();}
});

test('a new experiment resets the original apparatus, clock and specimen after confirmation',()=>{
  const app=appHarness();
  try{
    app.mount('ruler',[136,170]);const original=app.lab();original.advance(80);
    app.node('reset').onclick();assert.equal(app.node('resetPrompt').open,true);assert.equal(app.lab(),original);
    app.node('cancelReset').onclick();assert.equal(app.node('resetPrompt').open,false);assert.equal(app.lab(),original);
    app.node('reset').onclick();app.node('confirmReset').onclick();
    const next=app.lab();assert.notEqual(next,original);assert.equal(original._id,null);assert.equal(next.clock,0);
    assert.equal(next.obj.ruler.on,false);assert.notEqual(next.n_disk,original.n_disk);assert.equal(app.node('selection').value,'');
  }finally{app.dispose();}
});
