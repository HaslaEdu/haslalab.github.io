import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,readdirSync} from 'node:fs';
import {createRequire} from 'node:module';
import {DatabaseSync} from 'node:sqlite';
import {PRESSURE_WAVE_MONTHLY_CONTENT,PRESSURE_WAVE_PUBLICATION_ID,publishWeeklyContent,ensureWeeklyContent,migrateMonthlyPeriod,validateContent} from './src/weekly-content.js';
import {getMonthlyAnswerSheet,getMonthlyProblemRound} from '../monthly-problems.mjs';
import {normalizeMonthlyParts,guardMonthlyGrade,retireIntroMonthlyProblems} from './src/monthly-answers.js';

const problem=PRESSURE_WAVE_MONTHLY_CONTENT.problems[0],partIds=['A.1','A.2','B.1','B.2','B.3','C.1','C.2'];
const require=createRequire(import.meta.url),katex=require('../vendor/katex/katex.min.js');
function database(){
 const sql=new DatabaseSync(':memory:');
 for(const name of readdirSync(new URL('./migrations/',import.meta.url)).filter(n=>/^00(?:0[1-9]|1[01])_.*\.sql$/.test(n)).sort())sql.exec(readFileSync(new URL('./migrations/'+name,import.meta.url),'utf8'));
 const db={prepare(query){const statement=sql.prepare(query),make=args=>({
  bind:(...values)=>make(values),async first(){return statement.get(...args)||null;},async all(){return{results:statement.all(...args)};},async run(){return this.execute();},
  execute(){if(statement.columns().length)return{results:statement.all(...args)};const r=statement.run(...args);return{meta:{changes:r.changes,last_row_id:Number(r.lastInsertRowid)}};},
 });return make([]);},async batch(statements){sql.exec('BEGIN');try{const result=statements.map(s=>s.execute());sql.exec('COMMIT');return result;}catch(error){sql.exec('ROLLBACK');throw error;}}};
 return{sql,db};
}

test('pressure-wave publication is bilingual, self-contained and complete without a measurement-count quota',()=>{
 validateContent(PRESSURE_WAVE_MONTHLY_CONTENT);
 assert.equal(problem.week,'2026-11');assert.equal(problem.no,5);assert.equal(problem.kind,'essay');assert.equal(problem.subject,'physics');
 assert.equal(problem.points,100);assert.equal(problem.level,16);assert.equal(problem.closes_at,1796050800);
 assert.equal(problem.rubric.reduce((sum,c)=>sum+c.max,0),100);
 assert.deepEqual([...new Set(problem.rubric.map(c=>c.id.match(/^[ABC]\.\d/)[0]))],partIds);
 assert.ok(problem.rubric.every(c=>partIds.some(id=>c.id.startsWith(id+'.'))));
 for(const field of ['body_ko','body_en']){
  const body=problem[field];assert.equal((body.match(/^### [ABC]\.\d /gm)||[]).length,7);
  assert.ok(body.includes('weekly/figures/pressure-wave-apparatus.svg'));
  assert.match(body,/120\.0/);assert.match(body,/200\.0/);assert.match(body,/\\varepsilon/);
  assert.doesNotMatch(body,/최소\s*7|7회|많이 측정|at least\s+7|seven (?:runs|trials|measurements)|\.pdf|iframe|<script|editor|repeat_credit/i);
  assert.doesNotMatch(body,/1483\.24|2\.200|50\.0\\left|0\.0800|0\.0400|113\.311/,'private numerical answers are absent from the statement');
 }
 assert.match(problem.model_en,/5\.66328/);assert.match(problem.model_ko,/17\.2260/);
 assert.match(problem.model_en,/single reading/i);assert.match(problem.model_ko,/측정 횟수 자체는 채점하지 않는다/);
 assert.match(problem.model_en,/trusted server-side session reference overrides/);
 assert.match(problem.rubric.find(c=>c.id==='C.2.choice').requirement,/trusted session reference/);
 assert.match(problem.body_en,/Set the closure time to \$2\\,\\mathrm\{ms\}\$/);
 assert.match(problem.body_ko,/폐쇄 시간을 \$2\\,\\mathrm\{ms\}\$/);
 assert.match(problem.rubric.find(c=>c.id==='A.2.records').requirement,/2 ms/);
});

test('all pressure-wave statement and reference formulas parse as LaTeX',()=>{
 let count=0;
 for(const field of ['body_ko','body_en','model_ko','model_en']){
  const text=problem[field];
  for(const formula of text.matchAll(/\$\$([\s\S]*?)\$\$|\$([^$\n]+)\$/g)){
   assert.doesNotThrow(()=>katex.renderToString(formula[1]??formula[2],{displayMode:formula[1]!==undefined,throwOnError:true}),field+': '+formula[0]);count++;
  }
  const without=text.replace(/\$\$[\s\S]*?\$\$|\$[^$\n]+\$/g,'');assert.ok(!without.includes('$'),field+' has balanced math delimiters');
 }
 assert.ok(count>180,'all mathematical statements and worked references are checked');
});

test('pressure-wave publication is atomic and idempotent and preserves maintained text and submissions',async()=>{
 const{sql,db}=database();try{
  const before=sql.prepare('SELECT * FROM problems ORDER BY id').all();
  const first=await publishWeeklyContent(db,PRESSURE_WAVE_MONTHLY_CONTENT,PRESSURE_WAVE_PUBLICATION_ID);assert.equal(first.inserted,1);assert.equal(first.applied,true);
  const row=sql.prepare("SELECT * FROM problems WHERE week='2026-11' AND no=5").get();
  sql.prepare("INSERT INTO users(id,username,nickname,pw,role,created_at)VALUES(1,'pressure-student','Pressure student','unused','user',?)").run(problem.opens_at);
  sql.prepare("INSERT INTO submissions(problem_id,user_id,answer,status,score,in_week,created_at)VALUES(?,1,'Stored answer','graded',72,1,?)").run(row.id,problem.opens_at);
  sql.prepare("UPDATE problems SET title_ko='관리자가 유지한 제목',body_ko='Maintained statement' WHERE id=?").run(row.id);
  const saved=sql.prepare('SELECT * FROM submissions').all();
  const second=await publishWeeklyContent(db,PRESSURE_WAVE_MONTHLY_CONTENT,PRESSURE_WAVE_PUBLICATION_ID);assert.equal(second.inserted,0);assert.equal(second.applied,false);
  assert.deepEqual(sql.prepare('SELECT * FROM problems WHERE id<=3 ORDER BY id').all(),before);
  assert.equal(sql.prepare('SELECT body_ko FROM problems WHERE id=?').get(row.id).body_ko,'Maintained statement');
  assert.deepEqual(sql.prepare('SELECT * FROM submissions').all(),saved);
 }finally{sql.close();}
});

test('a different problem occupying November slot 5 aborts the new publication without mutation',async()=>{
 const{sql,db}=database();try{
  const other=structuredClone(PRESSURE_WAVE_MONTHLY_CONTENT);other.problems[0].title_ko='별도 관리 문제';other.problems[0].source='Different source';
  await publishWeeklyContent(db,other,'test-other-pressure-slot');
  const before=sql.prepare('SELECT * FROM problems ORDER BY id').all();
  await assert.rejects(publishWeeklyContent(db,PRESSURE_WAVE_MONTHLY_CONTENT,PRESSURE_WAVE_PUBLICATION_ID),/NOT NULL/);
  assert.deepEqual(sql.prepare('SELECT * FROM problems ORDER BY id').all(),before);
  assert.equal(sql.prepare('SELECT id FROM weekly_publications WHERE id=?').get(PRESSURE_WAVE_PUBLICATION_ID),undefined);
 }finally{sql.close();}
});

test('first monthly initialization appends problem 5 and its form follows the actual database ID',async()=>{
 const{sql,db}=database();try{
  await ensureWeeklyContent(db);
  const row=sql.prepare("SELECT * FROM problems WHERE week='2026-11' AND no=5").get();assert.ok(row);
  const sheet=getMonthlyAnswerSheet(row);assert.ok(sheet,'a stable publication identity resolves the native form');
  assert.equal(sheet.key,'pressure-wave-experiment-v1');assert.equal(sheet.round,'experiment');assert.equal(getMonthlyProblemRound(row),'experiment');
  assert.deepEqual(sheet.parts.map(p=>p.id),partIds);assert.equal(sheet.parts.reduce((sum,p)=>sum+p.points,0),100);assert.equal(sheet.limit,3);
  assert.ok(sql.prepare('SELECT id FROM weekly_publications WHERE id=?').get(PRESSURE_WAVE_PUBLICATION_ID));
  const unrelated={...row,no:6,title_ko:'Unrelated',title_en:'Unrelated',source:'Unrelated',id:999};assert.equal(getMonthlyAnswerSheet(unrelated),null);
 }finally{sql.close();}
});

test('an unrelated reserved ID is preserved while pressure-wave metadata follows the newly allocated record',async()=>{
 const{sql,db}=database();try{
  await publishWeeklyContent(db);await migrateMonthlyPeriod(db);await retireIntroMonthlyProblems(db);
  const original=sql.prepare('SELECT * FROM problems WHERE id=1').get();
  sql.prepare(`INSERT INTO problems(id,week,no,kind,subject,level,points,title_ko,title_en,body_ko,body_en,opens_at,closes_at,created_at)
   VALUES(80,'2027-03',1,'essay','physics',10,100,'별도 관리자 문제','Unrelated maintained problem','본문','Body',?,?,?)`).run(original.opens_at,original.closes_at,original.created_at);
  const before=sql.prepare('SELECT * FROM problems WHERE id=80').get();
  await ensureWeeklyContent(db);
  const row=sql.prepare("SELECT * FROM problems WHERE week='2026-11' AND no=5").get();
  assert.ok(row.id>80);assert.equal(getMonthlyAnswerSheet(row).key,'pressure-wave-experiment-v1');
  assert.deepEqual(sql.prepare('SELECT * FROM problems WHERE id=80').get(),before);
  assert.equal(getMonthlyAnswerSheet(before),null);
 }finally{sql.close();}
});

test('each pressure-wave marking group receives only evidence from its matching answer part',()=>{
 const stored={...problem,id:987};
 for(const partId of partIds){
  const normalized=normalizeMonthlyParts(stored,{request_id:'pressure-wave-rubric-test-'+partId.replace('.','-'),parts:[{id:partId,answer:'Student numerical result',working:'Student analysis and measured table'}]});
  const grade={score:100,detail:{scores:problem.rubric.map(c=>({id:c.id,max:c.max,got:c.max,decision:'met',evidence:['Student analysis and measured table']})),feedback:[]}};
  const guarded=guardMonthlyGrade(grade,stored,normalized,'ko');
  const expected=problem.rubric.filter(c=>c.id.startsWith(partId+'.')).reduce((sum,c)=>sum+c.max,0);
  assert.equal(guarded.score,expected,partId+' maps to its own supported criteria');
 }
});
