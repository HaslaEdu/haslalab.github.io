import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {loadOriginalPython,OpticalLab,vis} from '../sim/ipho2019/e1-python.mjs';

const root=new URL('../',import.meta.url);
const fixture=JSON.parse(readFileSync(new URL('./fixtures/ipho2019-e1-python.json',import.meta.url),'utf8'));
const source=readFileSync(new URL('../src/ipho2019_E1_sim_KO.py',import.meta.url));
const ready=await loadOriginalPython();
const close=(actual,expected,path='value')=>{
  if(typeof expected==='number')return assert.ok(Math.abs(actual-expected)<=1e-10*Math.max(1,Math.abs(expected)),`${path}: ${actual} != ${expected}`);
  if(Array.isArray(expected)){
    assert.ok(Array.isArray(actual),path);assert.equal(actual.length,expected.length,path);
    return expected.forEach((entry,index)=>close(actual[index],entry,`${path}[${index}]`));
  }
  if(expected&&typeof expected==='object')return Object.keys(expected).forEach(key=>close(actual[key],expected[key],`${path}.${key}`));
  assert.equal(actual,expected,path);
};
const fixed=(x,y,ang=0)=>({on:true,pos:[x,y],ang,tapes:[[-12,-2],[12,2]]});

test('the browser executes the byte-identical supplied Python in local CPython/WebAssembly',()=>{
  assert.equal(createHash('sha256').update(source).digest('hex'),'dae656e74496a3f2c224c068ceaa7c820978301aa0d6d1f9d2a78001aa19ba12');
  assert.equal(ready.version,'0.29.3');assert.equal(ready.python,'3.13.2');
  const lab=new OpticalLab(201901);
  assert.ok(Object.values(lab.obj).every(obj=>obj.on===false));assert.equal(lab.tape_on,false);
  assert.equal(lab.n_disk,1.5156659521538987);assert.equal(lab.grating_id,'#726');
  assert.deepEqual(lab.trace(),{segments:[],segs:[],spots:[],hits:[],shots:[]});
  lab.dispose();
});

for(const entry of fixture.cases)test(`original Python optical parity: ${entry.input.name}`,()=>{
  const lab=new OpticalLab(201901);lab.laser_on=true;
  for(const[key,value]of Object.entries(entry.input.objects||{}))Object.assign(lab.obj[key],structuredClone(value));
  for(const[key,value]of Object.entries(entry.input))if(!['name','objects'].includes(key))lab[key]=value;
  lab.clearPoseCache();close(lab.trace(),entry.trace);lab.dispose();
});

test('placement, SAT dragging, fine wheel, tape fixation and the clock match native original LabTab methods',()=>{
  const oracle=spawnSync('python',[fileURLToPath(new URL('./fixtures/ipho2019-e1-oracle.py',import.meta.url))],{cwd:fileURLToPath(root),encoding:'utf8'});
  assert.equal(oracle.status,0,oracle.stderr);const expected=JSON.parse(oracle.stdout),actual=[];
  const lab=new OpticalLab(201901);
  const state=()=>JSON.parse(JSON.stringify(Object.fromEntries(['obj','order','slider','laser_fine','hold_rot','tape_on','tape_held','tape_a','tape_b','clock','t','dark'].map(key=>[key,lab[key]]))));
  const capture=()=>actual.push(state());
  for(const[key,point]of [['ruler',[136,170]],['disk',[136,96]],['holder',[136,96]],['tape6',[40,60]]]){lab.toggle(key,point);capture();}
  lab.move('disk',[142,112],{removeOutside:false});capture();
  lab.rotate('disk',2);capture();lab.rotate('holder12b',-.25);capture();
  lab.tape_held=true;let[x,y]=lab.pose('disk');lab.stickTape(x-5,y);capture();
  [x,y]=lab.pose('disk');lab.stickTape(x+5,y);capture();
  assert.equal(lab.move('disk',[10,10]),false);assert.equal(lab.rotate('disk',2),false);capture();
  lab.advance(18.1,10);capture();close(actual,expected);assert.equal(lab.dark,true);
  assert.equal(lab.peelTape('disk',1),true);assert.equal(lab.peelTape('disk',0),true);assert.equal(lab.move('disk',[10,10]),true);
  lab.dispose();
});

test('slider stops at original adhesive boundaries, screen stays solid and removal restores the tray',()=>{
  const lab=new OpticalLab(201901);
  Object.assign(lab.obj.ruler,fixed(136,170));lab.obj.ruler.tapes=[[-10,0],[12,0]];
  assert.equal(lab.setSlider(25),5.5);assert.equal(lab.setSlider(-25),-3.5);
  Object.assign(lab.obj.screen,fixed(136,70));Object.assign(lab.obj.disk,{on:true,pos:[136,105],ang:0,tapes:[]});
  lab.move('disk',[136,30]);assert.ok(lab.obj.disk.pos[1]>70);
  lab.move('disk',[-100,-100]);assert.equal(lab.obj.disk.on,false);
  lab.toggle('tape',[100,120]);assert.deepEqual(lab.tape_a,[40,134]);assert.deepEqual(lab.tape_b,[160,134]);
  lab.moveTapeEndpoint('tape_a',[-20,50]);assert.equal(lab.tape_on,false);lab.dispose();
});

test('original visibility and transparent ruler coverage remain distinct from the 3D renderer',()=>{
  assert.equal(vis(1,false),.8);assert.equal(vis(.019,false),0);assert.equal(vis(.00009,true),0);assert.equal(vis(1,true),1);
  const lab=new OpticalLab(201901);Object.assign(lab.obj.ruler,fixed(136,170));Object.assign(lab.obj.disk,fixed(136,96,270));
  Object.assign(lab.obj.ruler8,{on:true,pos:[136,96],ang:90,tapes:[]});lab.order=lab.order.filter(key=>key!=='ruler8').concat('ruler8');
  lab.laser_on=true;const trace=lab.trace();
  for(const segment of trace.segments.filter(segment=>segment[5]==='glass')){
    const[x0,y0,x1,y1]=segment,x=(x0+x1)/2,y=(y0+y1)/2;
    assert.equal(typeof lab.in_ruler8(x,y),'boolean');
  }
  assert.equal(lab.in_ruler8(136,96),true);lab.order=lab.order.filter(key=>key!=='ruler8');lab.order.unshift('ruler8');
  lab.clearPoseCache();assert.equal(lab.in_ruler8(136,96),false);lab.dispose();
});
