/* Builds the Learn section's practice data from the PhysLeague export.
   usage: node tools/practice/build-practice.mjs EXPORT.json FIGURE_DIR
   Keeps only calculation problems (numeric or formula answers).
   Writes practice/index.json, practice/data/<area>.json and practice/fig/*.webp.
   Units come from tools/practice/classifications.json (reviewed keyword and model classifications);
   steps come from the exams' wrong-answer difficulty (learn-path.js stepFromCsat). */
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const P=require('../../learn-path.js');
const [exportPath,figDir]=process.argv.slice(2);
const root=path.resolve(path.dirname(new URL(import.meta.url).pathname),'../..');
const rows=JSON.parse(fs.readFileSync(exportPath,'utf8'));
const units=JSON.parse(fs.readFileSync(path.join(root,'tools/practice/classifications.json'),'utf8')).units;
const manifest=JSON.parse(fs.readFileSync(path.join(figDir,'manifest.json'),'utf8'));
const out=path.join(root,'practice');
/* only this script's outputs; practice/contests.json and practice/contest/ come from build-contests.mjs */
for(const sub of ['data','fig'])fs.rmSync(path.join(out,sub),{recursive:true,force:true});fs.rmSync(path.join(out,'index.json'),{force:true});
fs.mkdirSync(path.join(out,'data'),{recursive:true});fs.mkdirSync(path.join(out,'fig'),{recursive:true});

const SUBJECT={physics1:'물리학Ⅰ',physics2:'물리학Ⅱ'};
const EXAM={csat:'대학수학능력시험',mock_evaluation:'평가원 모의평가',education_office:'전국연합학력평가'};
const AUTH={kice:'한국교육과정평가원',sen:'서울특별시교육청',goe:'경기도교육청',ice:'인천광역시교육청'};
/* paragraphs keep their inline children only; the flat text is a duplicate */
function node(n,figs){
  if(n.type==='paragraph')return{p:(n.children||[{type:'text',text:n.text}]).map(c=>c.type==='math_inline'?{m:c.latex}:{t:c.text})};
  if(n.type==='math_block')return{mb:n.latex};
  if(n.type==='figure'){const f=figs[n.src];return f?{f:f.file,w:f.w,h:f.h,alt:n.alt||''}:null;}
  return null;
}
/* The text layer split a few one-symbol answers such as "4I₀" into "4I\n0" or "B 0"; only that exact shape is
   rebuilt as math. Anything longer stays as extracted. */
function subscriptFix(blocks){
  if(blocks.length!==1||!blocks[0].p||blocks[0].p.length!==1||blocks[0].p[0].t===undefined)return blocks;
  const m=/^\s*([−-]?\d*)\s*([A-Za-z])\s*\n?\s*0\s*$/.exec(blocks[0].p[0].t);
  return m?[{p:[{m:(m[1]||'').replace('−','-')+m[2]+'_0'}]}]:blocks;
}
const byArea={},index=[],skipped=[];
for(const r of rows){
  const unit=units[r.id];
  if(!unit||!P.SUBTOPICS.has(unit)){skipped.push([r.id,'no unit']);continue;}
  const answer=Number(r.answer_choice);
  if(!(answer>=1&&answer<=5)){skipped.push([r.id,'no answer']);continue;}
  const made=manifest[r.id]||{},figs={};
  r.media.forEach((m,i)=>{const f=made['f'+(i+1)];if(f)figs[m.url]=f;});
  const whole=made.q;  /* choices are pictures: the whole question is shown as one image */
  const body=whole?[{f:whole.file,w:whole.w,h:whole.h,alt:r.title}]:r.body_ast_json.map(n=>node(n,figs)).filter(Boolean);
  if(!whole&&r.media.length&&r.media.some(m=>!figs[m.url])){skipped.push([r.id,'figure missing']);continue;}
  const choices=r.choices.map(c=>({n:c.n,c:whole?[]:subscriptFix((c.ast||[]).map(n=>node(n,{})).filter(Boolean))}));
  /* only calculation problems: at least three choices are numbers or formulas (not ㄱ/ㄴ/ㄷ statements, letter sets or pictures) */
  const choiceText=c=>c.c.flatMap(b=>b.p||[]).map(x=>x.t??x.m??'').join('').trim();
  if(choices.filter(c=>{const t=choiceText(c);return /\d|\\/.test(t)&&!/^[ㄱㄴㄷ]/.test(t);}).length<3){skipped.push([r.id,'not a calculation']);continue;}
  const step=P.stepFromCsat(r.difficulty),area=unit.split('/')[0];
  const source=`${r.academic_year}${r.exam_type==='csat'?'학년도 ':'년 '+r.month+'월 '}${EXAM[r.exam_type]||r.contest} ${SUBJECT[r.subject]} ${r.question_number}번`;
  const item={id:r.id,u:unit,s:step,src:source,by:AUTH[r.authority]||'',pdf:r.official_problem_url||'',sec:r.recommended_seconds||90,b:body,ch:choices,a:answer};
  (byArea[area]||=[]).push(item);
  index.push([r.id,unit,step]);
  /* copy only the figures the item shows (a few recorded media are not placed in the text) */
  for(const b of body)if(b.f)fs.copyFileSync(path.join(figDir,b.f),path.join(out,'fig',b.f));
}
const counts={};
for(const [,u,s] of index){(counts[u]||={})[s]=(counts[u][s]||0)+1;}
for(const [area,items] of Object.entries(byArea)){items.sort((a,b)=>a.s-b.s||a.id.localeCompare(b.id));fs.writeFileSync(path.join(out,'data',area+'.json'),JSON.stringify({version:1,area,items}));}
fs.writeFileSync(path.join(out,'index.json'),JSON.stringify({version:1,taxonomy:P.VERSION,total:index.length,counts,attribution:'문항 출처: 한국교육과정평가원, 서울특별시교육청, 경기도교육청, 인천광역시교육청. 웹·앱 배포 허가 범위 안에서 제공합니다.'}));
console.log('items',index.length,'skipped',skipped.length,'(not calculation '+skipped.filter(x=>x[1]==='not a calculation').length+')',Object.fromEntries(Object.entries(byArea).map(([a,i])=>[a,i.length])));
for(const s of skipped.filter(x=>x[1]!=='not a calculation').slice(0,10))console.log('  ',...s);
