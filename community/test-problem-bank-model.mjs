import test from 'node:test';
import assert from 'node:assert/strict';
import {estimateDifficulty,starsFromRubric,solveProbability,eloUpdate,recommendProblems,difficultyInfo} from './src/problem-bank-model.js';
test('rubric estimates are bounded, explicit and never promoted by source length or missing context',()=>{
 for(const level of ['high_school','olympiad','undergraduate','graduate','mixed'])for(const text of ['Find acceleration.','Derive the self-consistent Green function for a tensor wave equation.']){const r=estimateDifficulty({text,level});assert(r.stars>=1&&r.stars<=5);assert.equal(r.status,'provisional');assert.equal(r.confidence,'low');}
 const a=estimateDifficulty({text:'A mass moves. Find acceleration.',level:'undergraduate'}),b=estimateDifficulty({text:'A mass moves. Find acceleration.\n'.repeat(100),level:'undergraduate',unresolved_source:true});assert.equal(a.stars,b.stars);assert(b.reason_codes.includes('reference_context_pending'));
 assert.throws(()=>starsFromRubric({prerequisites:99,integration:1,mathematics:1,reasoning:1}),/invalid/);
});
test('advanced mathematical evidence raises a provisional estimate while language and problem numbering do not',()=>{
 const base=estimateDifficulty({text:'Find the acceleration of a mass.',level:'undergraduate'}),advanced=estimateDifficulty({text:'Construct a self-consistent asymptotic Green function of the tensor wave equation.',level:'graduate'});assert(advanced.stars>base.stars);assert(advanced.reason_codes.includes('advanced_mathematics'));
 assert.equal(estimateDifficulty({text:'Problem 1. Find acceleration.'}).stars,estimateDifficulty({text:'Problem 9999. Find acceleration.'}).stars);
});
test('one source can contain simple one-concept questions and advanced multi-method questions across the full scale',()=>{
 const prompts=['A mass moves. Find its acceleration.','Evaluate the integral of the velocity.','Solve the differential equation for a normal mode.','Find the Green function.','Construct a self-consistent asymptotic Green function for a tensor wave equation.'];
 assert.deepEqual(prompts.map(text=>estimateDifficulty({text,level:'undergraduate'}).stars),[1,2,3,4,5]);
 const text='A Lorentz transformation relates two frames.';
 assert.equal(estimateDifficulty({text,subjects:['relativity']}).stars,estimateDifficulty({text,subjects:['relativity','special_relativity','general_relativity']}).stars);
 assert.equal(estimateDifficulty({text:'A force starts at time zero.'}).rubric.integration,0);
});
test('unverified self reports cannot change Elo ability or item difficulty',()=>{
 assert.throws(()=>eloUpdate({ability:0,difficulty:0,correct:1,evidence:'self_report'}),/verified_grade_required/);
 const r=eloUpdate({ability:0,difficulty:0,correct:1,evidence:'verified_grade'});assert(r.ability>0&&r.difficulty<0);assert.equal(r.expected,.5);assert(solveProbability(1,0)>.5);assert(solveProbability(0,1)<.5);
});
test('recommendations exclude seen/exact duplicates, bound source concentration and favor a chosen difficulty',()=>{
 const items=Array.from({length:20},(_,i)=>({id:'q'+String(i).padStart(2,'0'),source_id:'s'+Math.floor(i/5),stars:i%5+1,subjects:['optics'],text_sha256:i<2?'same':'hash'+i}));
 const out=recommendProblems(items,{targetStars:3,limit:12,seen:['q03'],preferredSubjects:['optics']});assert(out.length>0&&out.length<=12);assert(!out.some(x=>x.id==='q03'));assert.equal(new Set(out.map(x=>x.text_sha256)).size,out.length);for(const s of new Set(out.map(x=>x.source_id)))assert(out.filter(x=>x.source_id===s).length<=3);assert([2,3].includes(out[0].stars));
});
test('difficulty response excludes private provenance and unknown reason payloads',()=>{
 const r=difficultyInfo({stars:3,difficulty_status:'provisional',confidence:'low',reason_codes_json:'["calculus","D:/private/source.pdf"]',proof_json:'private'});assert.deepEqual(r.reason_codes,['calculus']);assert(!JSON.stringify(r).includes('private'));assert.equal(difficultyInfo({stars:9}),null);
});
test('separate scans of the same published work share one recommendation cap',()=>{
 const items=Array.from({length:12},(_,i)=>({id:'q'+i,source_id:'scan'+i%2,source_title:'Modern Electrodynamics · Andrew Zangwill',stars:3,text_sha256:'different'+i}));
 assert.equal(recommendProblems(items,{limit:12}).length,3);
});
