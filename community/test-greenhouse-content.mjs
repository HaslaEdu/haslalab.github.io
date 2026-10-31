import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync,readdirSync} from 'node:fs';
import {ensureWeeklyContent,publishWeeklyContent,migrateMonthlyPeriod,GREENHOUSE_MONTHLY_CONTENT,GREENHOUSE_PUBLICATION_ID,validateContent} from './src/weekly-content.js';
import {retireIntroMonthlyProblems} from './src/monthly-answers.js';
import {getMonthlyAnswerSheet} from '../monthly-problems.mjs';

function database(){
  const sql=new DatabaseSync(':memory:');
  for(const file of readdirSync(new URL('./migrations/',import.meta.url)).filter(name=>/^00(?:0[1-9]|1[01])_.*\.sql$/.test(name)).sort())sql.exec(readFileSync(new URL('./migrations/'+file,import.meta.url),'utf8'));
  const db={prepare(query){const st=sql.prepare(query),make=args=>({bind:(...values)=>make(values),async first(){return st.get(...args)||null;},async all(){return{results:st.all(...args)};},async run(){return this.runSync();},runSync(){if(st.columns().length)return{results:st.all(...args)};const r=st.run(...args);return{meta:{changes:r.changes,last_row_id:Number(r.lastInsertRowid)}};}});return make([]);},async batch(statements){sql.exec('BEGIN');try{const rows=statements.map(st=>st.runSync());sql.exec('COMMIT');return rows;}catch(e){sql.exec('ROLLBACK');throw e;}}};return{sql,db};
}

test('greenhouse Part D is one self-contained bilingual 100-point native problem with all original questions',()=>{
  validateContent(GREENHOUSE_MONTHLY_CONTENT);const problem=GREENHOUSE_MONTHLY_CONTENT.problems[0];
  assert.equal(problem.week,'2026-11');assert.equal(problem.no,4);assert.equal(problem.closes_at,1796050800);
  assert.equal(problem.rubric.reduce((sum,row)=>sum+row.max,0),100);
  assert.deepEqual(problem.rubric.map(row=>row.id),['16','17','18','19','20a','20b','20c','21a','21b','21c']);
  const sheet=getMonthlyAnswerSheet({...problem,id:7});assert.equal(sheet.key,'greenhouse-part-d-v1');
  assert.deepEqual(sheet.parts.map(row=>row.id),problem.rubric.map(row=>row.id));assert.equal(sheet.parts.reduce((sum,row)=>sum+row.points,0),100);
  assert.deepEqual(sheet.pages.flat().sort(),sheet.parts.map(row=>row.id).sort());
  const question17=problem.body_ko.split('### 논제 17')[1].split('### 논제 18')[0];
  assert.match(question17,/천정거리.*함수로 구하라/);assert.ok(!question17.includes('cos'));assert.ok(!question17.includes('보여라'));
  for(const body of[problem.body_ko,problem.body_en]){assert.ok(body.includes('25800'));assert.ok(body.includes('23.5'));assert.ok(body.includes('t_{lw}'));assert.ok(!/\.pdf|iframe|<img/i.test(body));}
  assert.match(problem.body_ko,/연주운동은 고려하지 않는다/);assert.match(problem.body_ko,/두 면은 언제나 같은 균일한 온도/);
  assert.match(problem.model_ko,/300\.347/);assert.match(problem.model_en,/1608\.76/);assert.match(problem.model_ko,/시간 반전에 대해 대칭/);
});

test('additive publication creates problem 4 at id7 and preserves existing problem data and later edits',async()=>{
  const {sql,db}=database();try{
    await ensureWeeklyContent(db);const before=sql.prepare('SELECT * FROM problems WHERE id<=6 ORDER BY id').all();
    const added=sql.prepare('SELECT * FROM problems WHERE week=? AND no=4').get('2026-11');assert.equal(added.id,7);
    assert.ok(getMonthlyAnswerSheet(added));assert.equal(sql.prepare('SELECT COUNT(*) n FROM problems').get().n,8);
    assert.ok(sql.prepare('SELECT id FROM weekly_publications WHERE id=?').get(GREENHOUSE_PUBLICATION_ID));
    sql.prepare("UPDATE problems SET title_ko='관리자가 유지한 제목',body_ko='수정한 문제' WHERE id=7").run();
    await ensureWeeklyContent(db,{});assert.deepEqual(sql.prepare('SELECT * FROM problems WHERE id<=6 ORDER BY id').all(),before);
    assert.equal(sql.prepare('SELECT body_ko FROM problems WHERE id=7').get().body_ko,'수정한 문제');
    assert.ok(getMonthlyAnswerSheet(sql.prepare('SELECT * FROM problems WHERE id=7').get()),'stable private source preserves the native form after a maintained title');
  }finally{sql.close();}
});

test('an occupied unrelated id7 yields a native greenhouse form at its actual later database ID',async()=>{
  const {sql,db}=database();try{
    await publishWeeklyContent(db);await migrateMonthlyPeriod(db);await retireIntroMonthlyProblems(db);
    const source=sql.prepare('SELECT * FROM problems WHERE id=1').get();
    sql.prepare(`INSERT INTO problems(id,week,no,kind,subject,level,points,title_ko,title_en,body_ko,body_en,opens_at,closes_at,created_at)
      VALUES(7,'2027-03',1,'essay','physics',10,100,'다른 문제','Different problem','본문','Body',?,?,?)`).run(source.opens_at,source.closes_at,source.created_at);
    await ensureWeeklyContent(db);const added=sql.prepare("SELECT * FROM problems WHERE week='2026-11' AND no=4").get();
    assert.notEqual(added.id,7);const sheet=getMonthlyAnswerSheet(added);assert.equal(sheet.key,'greenhouse-part-d-v1');assert.equal(sheet.limit,3);
    assert.equal(getMonthlyAnswerSheet(sql.prepare('SELECT * FROM problems WHERE id=7').get()),null);
    const publicProblem={id:added.id,week:added.week,no:4,title:added.title_en,source:null,answerSheet:sheet};assert.deepEqual(getMonthlyAnswerSheet(publicProblem),sheet);
  }finally{sql.close();}
});

test('the independent numerical reference uses unrounded solar inputs and physically correct two-face budgets',()=>{
  const sigma=5.67e-8,S=sigma*5770**4*(6.96e8/1.50e11)**2,eps=23.5*Math.PI/180,T0=(S/(2*sigma))**.25;
  const Tmin=T0*Math.cos(2*eps)**.25;
  const time=25800/(2*Math.PI)*Math.acos((((1-1/T0)**4)-Math.cos(eps)**2)/Math.sin(eps)**2);
  assert.ok(Math.abs(S-1353.0762547083193)<1e-8);assert.ok(Math.abs(Tmin-300.34688846775776)<1e-9);assert.ok(Math.abs(time-1608.7624939820307)<1e-7);
  const tsw=.9,tlw=.2,e=1-tlw,F=(1+tsw)*S/(2*(1+tlw)),Aplus=(e*F+(1-tsw)*S)/(2*e),Aminus=F/2;
  assert.ok(Math.abs(2*F-tsw*S-e*(Aplus+Aminus))<1e-9);
  assert.ok(Math.abs((F/sigma)**.25-370.7408089681081)<1e-9);
});
