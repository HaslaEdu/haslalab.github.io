import test from 'node:test';
import assert from 'node:assert/strict';
import {loadOriginalPython,OpticalLab} from '../sim/ipho2019/e1-python.mjs';
import {opticalFocus,opticalWheelAction} from '../sim/ipho2019/e1-scene.mjs';

await loadOriginalPython();

test('a flexible measuring tape focuses its midpoint without looking for a nonexistent rigid apparatus pose',()=>{
  const lab=new OpticalLab(201901);
  lab.tape_a=[50,192];lab.tape_b=[170,192];
  assert.deepEqual(opticalFocus(lab,'tape'),{target:[110,1.5,192],distance:144});
  lab.tape_a=[100,90];lab.tape_b=[100,90];
  assert.deepEqual(opticalFocus(lab,'tape'),{target:[100,1.5,90],distance:30});
  lab.dispose();
});

test('laser and holder component views keep their actual optical position while unknown selections are harmless',()=>{
  const lab=new OpticalLab(201901);lab.obj.ruler.tapes=[[20,0],[-20,0]];lab.slider=7;
  const p=lab.pivot();assert.deepEqual(opticalFocus(lab,'laser').target,[p[0],3,p[1]]);
  assert.deepEqual(opticalFocus(lab,'holder12b').target,opticalFocus(lab,'holder').target);
  assert.equal(opticalFocus(lab,'not-an-apparatus'),null);
  assert.equal(opticalFocus(null,'disk'),null);
  lab.dispose();
});

test('ordinary and fine wheel steps turn apparatus without zooming or turning its mount instead of its optical element',()=>{
  assert.deepEqual(opticalWheelAction({key:'disk'},false,-120),{key:'disk',delta:2});
  assert.deepEqual(opticalWheelAction({key:'disk'},true,120),{key:'disk',delta:-.25});
  assert.deepEqual(opticalWheelAction({key:'holder',role:'holderRotate'},false,120),{key:'holder12b',delta:-2});
  assert.deepEqual(opticalWheelAction({key:'laser',role:'fine'},true,-1),{key:'laser',delta:.25});
  assert.deepEqual(opticalWheelAction({key:'ruler'},false,1),{key:'ruler',delta:-2});
  assert.equal(opticalWheelAction(null,false,120),null);
  assert.equal(opticalWheelAction({key:'tape6'},false,120),null);
  assert.equal(opticalWheelAction({key:'disk'},false,0),null);
});
