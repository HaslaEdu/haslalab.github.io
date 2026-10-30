import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync,readdirSync } from 'node:fs';
import { ensureMonthlyRewardSchema,settleMonthlyRewards,monthlyRewardSummary,readFinalMonthlyRanking,
  MONTHLY_TOKEN_REWARDS } from './src/monthly-rewards.js';
import { readPublicRanking } from './src/public-data.js';

const OPEN = Date.parse('2026-11-01T00:00:00+09:00')/1000;
const CLOSE = Date.parse('2026-12-01T00:00:00+09:00')/1000;

async function environment(run) {
  const sql = new DatabaseSync(':memory:');
  for (const name of readdirSync(new URL('./migrations/',import.meta.url)).filter(name => /^00(?:0[1-9]|1[01])_.*\.sql$/.test(name)).sort()) {
    sql.exec(readFileSync(new URL('./migrations/'+name,import.meta.url),'utf8'));
  }
  const queries = []; let batchHook = async()=>{};
  const db = {
    prepare(query) {
      queries.push(query);
      const statement = sql.prepare(query), make = args => ({
        query,bind:(...values)=>make(values),async first(){return statement.get(...args)||null;},
        async all(){return{results:statement.all(...args)};},async run(){return this.executeSync();},
        executeSync(){if(statement.columns().length)return{results:statement.all(...args)};const r=statement.run(...args);return{results:[],meta:{changes:r.changes,last_row_id:Number(r.lastInsertRowid)}};},
      });return make([]);
    },
    async batch(statements){await batchHook(statements);sql.exec('BEGIN');try{const r=statements.map(statement=>statement.executeSync());sql.exec('COMMIT');return r;}catch(error){sql.exec('ROLLBACK');throw error;}},
  };
  for(let id=1;id<=5;id++) sql.prepare("INSERT INTO users(id,username,nickname,pw,created_at) VALUES(?,?,?,'unused',?)").run(id,'reward'+id,'Reward '+id,OPEN-86400);
  const problem=(id,period='2026-11',no=id,close=CLOSE,open=OPEN)=>sql.prepare(`INSERT INTO problems
    (id,week,no,kind,subject,level,points,title_ko,title_en,body_ko,body_en,opens_at,closes_at,created_at)
    VALUES(?,?,?,'essay','physics',10,100,'보상 검사','Reward test','문제','Problem',?,?,?)`).run(id,period,no,open,close,open);
  problem(20,'2026-11',1);problem(21,'2026-11',2);
  const submit=(user,problemId,score,created=OPEN+user,status='graded',inWeek=1)=>{
    const r=sql.prepare(`INSERT INTO submissions(problem_id,user_id,answer,via_ocr,status,score,detail,in_week,created_at,graded_at)
      VALUES(?,?,'Private answer',0,?,?,NULL,?,?,?)`).run(problemId,user,status,score,inWeek,created,status==='graded'?created:null);
    return Number(r.lastInsertRowid);
  };
  const participants=()=>{
    submit(1,20,85,OPEN+1);submit(1,20,90,OPEN+2);submit(1,20,88,OPEN+3);submit(1,21,60,OPEN+4);
    submit(2,20,80,OPEN+5);submit(2,21,60,OPEN+6);
    submit(3,20,70,OPEN+7);submit(3,21,60,OPEN+8);
    submit(4,20,60,OPEN+9);submit(4,21,60,OPEN+10);
  };
  const balances=()=>sql.prepare('SELECT exam_tokens FROM users ORDER BY id').all().map(row=>row.exam_tokens);
  try{return await run({sql,db,queries,problem,submit,participants,balances,beforeBatch:callback=>{batchHook=callback;}});}
  finally{sql.close();}
}

test('November rewards publish at the exclusive cutoff and 85,90,88 records 90 instead of accumulating',async()=>{
  await environment(async({db,participants,balances,sql})=>{
    participants();
    assert.deepEqual(await settleMonthlyRewards(db,{timestamp:CLOSE-1}),{published:[],waiting:[]});
    assert.deepEqual(balances(),[5,5,5,5,5]);
    assert.equal((await monthlyRewardSummary(db,'2026-11',{timestamp:CLOSE-1})).status,'scheduled');
    assert.deepEqual(await settleMonthlyRewards(db,{timestamp:CLOSE}),{published:['2026-11'],waiting:[]});
    const summary=await monthlyRewardSummary(db,'2026-11',{timestamp:CLOSE});
    assert.equal(summary.status,'published');assert.equal(summary.announcement_at,CLOSE);assert.equal(summary.published_at,CLOSE);
    assert.deepEqual(summary.rewards,MONTHLY_TOKEN_REWARDS);
    assert.deepEqual(summary.rows.map(row=>[row.rank,row.nickname,row.total,row.token_reward]),[
      [1,'Reward 1',150,9],[2,'Reward 2',140,6],[3,'Reward 3',130,3],[4,'Reward 4',120,0],
    ]);
    assert.deepEqual(balances(),[14,11,8,5,5]);
    const ledger=sql.prepare("SELECT user_id,delta,reason,note,created_at FROM lab_ledger WHERE reason='monthly_reward' ORDER BY user_id").all();
    assert.deepEqual(ledger.map(row=>[row.user_id,row.delta,row.note,row.created_at]),[[1,9,'monthly:2026-11',CLOSE],[2,6,'monthly:2026-11',CLOSE],[3,3,'monthly:2026-11',CLOSE]]);
    assert.ok(summary.rows.every(row=>!Object.hasOwn(row,'user_id')&&!Object.hasOwn(row,'levels')),'public final rows contain no account IDs or private inputs');
  });
});

test('concurrent cron runs, retries and later score edits cannot pay twice or replace the final snapshot',async()=>{
  await environment(async({db,sql,participants,submit,balances})=>{
    participants();
    await Promise.all(Array.from({length:4},()=>settleMonthlyRewards(db,{timestamp:CLOSE})));
    const original=await readFinalMonthlyRanking(db,'2026-11',{timestamp:CLOSE});
    assert.deepEqual(balances(),[14,11,8,5,5]);assert.equal(sql.prepare("SELECT COUNT(*) n FROM lab_ledger WHERE reason='monthly_reward'").get().n,3);
    submit(4,20,100,CLOSE+2,'graded',0);submit(4,21,100,CLOSE+3,'graded',0);
    sql.prepare('UPDATE submissions SET score=0 WHERE user_id=1').run();
    sql.prepare("INSERT INTO monthly_problem_retirements(problem_id,retired_at,reason) SELECT id,?,'retired after final' FROM problems WHERE week='2026-11'").run(CLOSE+20);
    await settleMonthlyRewards(db,{timestamp:CLOSE+86400});
    assert.deepEqual(await readFinalMonthlyRanking(db,'2026-11',{timestamp:CLOSE+86400}),original);
    assert.deepEqual(balances(),[14,11,8,5,5]);assert.equal(sql.prepare("SELECT COUNT(*) n FROM lab_ledger WHERE reason='monthly_reward'").get().n,3);
  });
});

test('unresolved on-time grading holds publication; AI suspicion and late practice do not earn marks or block it',async()=>{
  await environment(async({db,sql,submit,balances})=>{
    submit(1,20,90);const pending=submit(2,20,null,OPEN+2,'pending');
    submit(3,20,null,OPEN+3,'ai_suspected');submit(4,20,null,CLOSE+1,'pending',0);
    assert.deepEqual(await settleMonthlyRewards(db,{timestamp:CLOSE}),{published:[],waiting:['2026-11']});
    assert.equal((await monthlyRewardSummary(db,'2026-11',{timestamp:CLOSE})).status,'awaiting_grading');
    assert.deepEqual(balances(),[5,5,5,5,5]);
    sql.prepare("UPDATE submissions SET status='error' WHERE id=?").run(pending);
    assert.deepEqual(await settleMonthlyRewards(db,{timestamp:CLOSE+1}),{published:[],waiting:['2026-11']});
    sql.prepare("UPDATE submissions SET status='graded',score=80,graded_at=? WHERE id=?").run(CLOSE+2,pending);
    assert.deepEqual(await settleMonthlyRewards(db,{timestamp:CLOSE+2}),{published:['2026-11'],waiting:[]});
    assert.deepEqual((await readFinalMonthlyRanking(db,'2026-11')).map(row=>row.nickname),['Reward 1','Reward 2']);
    assert.deepEqual(balances(),[14,11,5,5,5]);
  });
});

test('historical weekly/monthly periods are not rewarded, while a later eligible month settles independently',async()=>{
  await environment(async({db,problem,submit,balances,sql})=>{
    const OCTOBER=OPEN;
    problem(22,'2026-10',1,OCTOBER,OPEN-86400);submit(1,22,100,OPEN-100);
    problem(23,'2026-W43',1,OCTOBER,OPEN-86400);submit(2,23,100,OPEN-100);
    submit(3,20,80);
    await settleMonthlyRewards(db,{timestamp:CLOSE});assert.deepEqual(balances(),[5,5,14,5,5]);
    const JANUARY=Date.parse('2027-01-01T00:00:00+09:00')/1000;
    problem(24,'2026-12',1,JANUARY,CLOSE);submit(1,24,100,CLOSE+1);
    await settleMonthlyRewards(db,{timestamp:JANUARY});assert.deepEqual(balances(),[14,5,14,5,5]);
    assert.deepEqual(sql.prepare('SELECT period FROM monthly_result_publications ORDER BY period').all().map(row=>row.period),['2026-11','2026-12']);
    assert.equal((await monthlyRewardSummary(db,'2026-10')).eligible,false);assert.equal((await monthlyRewardSummary(db,'2026-W43')).eligible,false);
  });
});

test('retired problems, deleted users and submissions outside the actual window are excluded even with forged flags',async()=>{
  await environment(async({db,sql,submit,problem,balances})=>{
    await ensureMonthlyRewardSchema(db);
    problem(22);sql.prepare("INSERT INTO monthly_problem_retirements(problem_id,retired_at,reason) VALUES(22,?,'retired')").run(OPEN);
    submit(1,22,100);submit(2,20,99,OPEN-1);submit(3,20,100,CLOSE,'graded',1);submit(4,20,90);
    sql.prepare('UPDATE users SET deleted=1 WHERE id=4').run();submit(4,21,null,OPEN+1,'pending');
    submit(5,20,30);submit(1,20,null,OPEN+2,'ai_suspected');
    await settleMonthlyRewards(db,{timestamp:CLOSE});
    assert.deepEqual((await readFinalMonthlyRanking(db,'2026-11')).map(row=>[row.nickname,row.total]),[['Reward 5',30]]);
    assert.deepEqual(balances(),[5,5,5,5,14]);
  });
});

test('tie order matches the live monthly ranking and has a stable last-resort account tie break',async()=>{
  await environment(async({db,submit})=>{
    submit(2,20,90,OPEN+2);submit(1,20,85,OPEN+1);submit(1,20,90,OPEN+20);
    submit(3,20,90,OPEN+2);submit(4,20,90,OPEN+3);
    await ensureMonthlyRewardSchema(db);
    const live=await readPublicRanking(db,'2026-11');
    await settleMonthlyRewards(db,{timestamp:CLOSE});const final=await readFinalMonthlyRanking(db,'2026-11');
    assert.deepEqual(final.map(row=>row.nickname),live.map(row=>row.nickname));
    assert.deepEqual(final.map(row=>row.nickname),['Reward 1','Reward 2','Reward 3','Reward 4']);
    assert.deepEqual(final.map(({token_reward,rank,...row})=>row),live);
  });
});

test('reward publication, balances and ledger roll back together if a write fails',async()=>{
  await environment(async({db,sql,participants,balances})=>{
    participants();await ensureMonthlyRewardSchema(db);
    sql.exec("CREATE TRIGGER reject_monthly_reward BEFORE INSERT ON lab_ledger WHEN NEW.reason='monthly_reward' BEGIN SELECT RAISE(ABORT,'test ledger failure'); END");
    await assert.rejects(settleMonthlyRewards(db,{timestamp:CLOSE}),/test ledger failure/);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_result_publications').get().n,0);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_result_rows').get().n,0);assert.deepEqual(balances(),[5,5,5,5,5]);
    sql.exec('DROP TRIGGER reject_monthly_reward');await settleMonthlyRewards(db,{timestamp:CLOSE});assert.deepEqual(balances(),[14,11,8,5,5]);
  });
});

test('deadline changes between eligibility read and transaction cannot cause early payment',async()=>{
  await environment(async({db,sql,participants,beforeBatch,balances})=>{
    participants();await ensureMonthlyRewardSchema(db);
    let extended=false;beforeBatch(async statements=>{
      if(!extended&&statements.some(st=>st.query.startsWith('INSERT INTO monthly_result_publications'))){extended=true;sql.prepare('UPDATE problems SET closes_at=? WHERE week=?').run(CLOSE+3600,'2026-11');}
    });
    await settleMonthlyRewards(db,{timestamp:CLOSE});assert.deepEqual(balances(),[5,5,5,5,5]);
    assert.equal(sql.prepare('SELECT COUNT(*) n FROM monthly_result_publications').get().n,0);
    await settleMonthlyRewards(db,{timestamp:CLOSE+3600});assert.deepEqual(balances(),[14,11,8,5,5]);
  });
});

test('final public reads are SELECT-only, tolerate pre-schema deployment and preserve privacy after rename/deletion',async()=>{
  await environment(async({db,sql,queries,participants})=>{
    await db.prepare('CREATE TABLE monthly_problem_retirements(problem_id INTEGER PRIMARY KEY,retired_at INTEGER,reason TEXT)').run();
    queries.length=0;
    const before=await monthlyRewardSummary(db,'2026-11',{timestamp:CLOSE});
    assert.equal(before.status,'awaiting_publication');assert.equal(before.rows,null);
    assert.ok(queries.every(query=>/^SELECT\b/i.test(query)),'public lookup must not initialize tables');
    participants();await settleMonthlyRewards(db,{timestamp:CLOSE});
    sql.prepare("UPDATE users SET nickname='Renamed winner' WHERE id=1").run();
    sql.prepare("UPDATE users SET deleted=1,nickname='deleted_2',avatar=NULL WHERE id=2").run();
    queries.length=0;
    const rows=await readFinalMonthlyRanking(db,'2026-11',{timestamp:CLOSE});
    assert.equal(rows[0].nickname,'Renamed winner');assert.equal(rows[1].nickname,'탈퇴한 사용자');assert.equal(rows[1].av,null);
    assert.ok(queries.every(query=>/^SELECT\b/i.test(query)));
    assert.ok(!JSON.stringify(rows).includes('Private answer'));assert.ok(rows.every(row=>!('user_id' in row)&&!('deleted' in row)));
  });
});

test('an empty final month is published without creating nonexistent prize recipients',async()=>{
  await environment(async({db,sql,balances})=>{
    await settleMonthlyRewards(db,{timestamp:CLOSE});
    assert.deepEqual(await readFinalMonthlyRanking(db,'2026-11'),[]);
    assert.equal(sql.prepare("SELECT COUNT(*) n FROM lab_ledger WHERE reason='monthly_reward'").get().n,0);
    assert.deepEqual(balances(),[5,5,5,5,5]);
  });
});
