import test from 'node:test';
import assert from 'node:assert/strict';
import {OpticalLab} from '../sim/ipho2019/e1-physics.mjs';
import {opticalFocus} from '../sim/ipho2019/e1-scene.mjs';

test('a flexible measuring tape focuses its midpoint without looking for a nonexistent rigid apparatus pose',()=>{
  const lab=new OpticalLab(201901);
  lab.tape_a=[50,192];lab.tape_b=[170,192];
  assert.deepEqual(opticalFocus(lab,'tape'),{target:[110,1.5,192],distance:144});
  lab.tape_a=[100,90];lab.tape_b=[100,90];
  assert.deepEqual(opticalFocus(lab,'tape'),{target:[100,1.5,90],distance:30});
});

test('laser and holder component views keep their actual optical position while unknown selections are harmless',()=>{
  const lab=new OpticalLab(201901);lab.obj.ruler.tapes=[[20,0],[-20,0]];lab.slider=7;
  const p=lab.pivot();assert.deepEqual(opticalFocus(lab,'laser').target,[p[0],3,p[1]]);
  assert.deepEqual(opticalFocus(lab,'holder12b').target,opticalFocus(lab,'holder').target);
  assert.equal(opticalFocus(lab,'not-an-apparatus'),null);
  assert.equal(opticalFocus(null,'disk'),null);
});
