// The global reader runs real SELECTs against SQLite, with every non-public SQL access rejected.
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync, readdirSync } from 'node:fs';
import test from 'node:test';
import { readPublicData, readPublicRanking, projectRankingRows, publicDataPath, publicIsoWeek, rateUser, tierOf, TIER_AT, PublicDataError, arenaPeriod, currentPeriod } from './src/public-data.js';
import { isoMonth } from './src/problem-period.js';

const sql = new DatabaseSync(':memory:');
for (const name of readdirSync(new URL('./migrations/', import.meta.url)).filter(n => /^\d{4}_.*\.sql$/.test(n)).sort()) sql.exec(readFileSync(new URL('./migrations/' + name, import.meta.url), 'utf8'));
sql.exec('DELETE FROM submissions; DELETE FROM problems;');
sql.exec('CREATE TABLE monthly_problem_retirements(problem_id INTEGER PRIMARY KEY, retired_at INTEGER NOT NULL, reason TEXT NOT NULL)');
const time = 1900000000, queries = []; let trips = 0;
const db = {
  prepare(query) {
    assert.match(query, /^SELECT\b/i, 'public reader can execute only SELECT');
    assert.doesNotMatch(query, /\b(?:pw|token_hash|exam_tokens|exam_half|token_parts|sessions|lab_sessions|lab_pages|lab_ledger|pay_orders|identities|answer|rubric|model_ko|model_en)\b/i, 'public SQL must not fetch account, financial or answer fields');
    assert.doesNotMatch(query, /SELECT\s+\*/i);
    const statement = sql.prepare(query), make = args => ({
      bind: (...values) => make(values),
      execute() { queries.push({ query, args }); return { results: statement.all(...args).map(row => ({ ...row })) }; },
      async all() { trips++; return this.execute(); },
    });
    return make([]);
  },
  async batch(statements) {
    trips++; sql.exec('BEGIN');
    try { const results = statements.map(statement => statement.execute()); sql.exec('COMMIT'); return results; }
    catch (error) { sql.exec('ROLLBACK'); throw error; }
  },
};
for (let id = 1; id <= 4; id++) sql.prepare("INSERT INTO users(id,username,nickname,pw,role,avatar,deleted,created_at) VALUES(?,?,?,'PRIVATE_PASSWORD',?,?,?,?)")
  .run(id, 'private_login_' + id, 'Person ' + id, id === 3 ? 'admin' : 'user', 'avatar' + id, id === 4 ? 1 : 0, time);
for (let id = 1; id <= 30; id++) sql.prepare("INSERT INTO posts(id,user_id,board,tag,lang,title,body,created_at,n_likes,n_dislikes,n_comments) VALUES(?,?,?,?, 'ko',?,?,?,?,?,?)")
  .run(id, id === 29 ? 4 : id % 2 ? 2 : 1, id === 1 ? 'qna' : 'free', id === 1 ? 'q' : 'gen', id === 2 ? '100% literal_a' : 'Post ' + id,
    'Public post body '.repeat(30), time - (id === 6 ? 100000 : 1000), id === 3 ? 8 : id === 4 ? 3 : 0, id === 3 ? 1 : 0, id === 5 ? 20 : 0);
for (const [id, board, lang] of [[101, 'free', 'ko'], [102, 'qna', 'ko'], [103, 'study', 'ko'], [104, 'free', 'en']]) sql.prepare("INSERT INTO posts(id,user_id,board,tag,lang,title,body,created_at) VALUES(?,3,?,'notice',?,'Notice','Public notice',?)").run(id, board, lang, time - 1000);
sql.prepare("INSERT INTO posts(id,user_id,board,tag,lang,title,body,created_at) VALUES(201,2,'free','gen','en','English post','English body',?)").run(time);
for (const [id, week, number, kind, points, level, open, close] of [
  [501, '2099-W01', 1, 'short', 100, 10, time - 600, time + 600],
  [502, '2099-W01', 2, 'essay', 20, 20, time - 600, time + 600],
  [503, '2098-W52', 1, 'short', 100, 30, time - 1000, time - 100],
  [504, '2100-W01', 1, 'short', 100, 30, time + 1000, time + 2000],
]) sql.prepare(`INSERT INTO problems(id,week,no,kind,points,level,title_ko,title_en,body_ko,body_en,answer,rubric,model_ko,model_en,opens_at,closes_at,created_at)
  VALUES(?,?,?,?,?,?,'공개 제목','Public title','PRIVATE_BODY','PRIVATE_BODY','PRIVATE_ANSWER','PRIVATE_RUBRIC','PRIVATE_MODEL','PRIVATE_MODEL',?,?,?)`)
  .run(id, week, number, kind, points, level, open, close, time);
for (const [problem, user, score, status, inWeek, ago] of [
  [501, 1, 100, 'graded', 1, 40], [501, 1, 50, 'graded', 1, 80], [502, 1, 16, 'graded', 1, 50],
  [501, 2, 80, 'graded', 1, 70], [502, 2, 20, 'graded', 0, 60], [503, 2, 100, 'graded', 1, 100],
  [501, 3, null, 'pending', 1, 30], [501, 4, 100, 'graded', 1, 20], [503, 1, 0, 'error', 1, 10],
]) sql.prepare("INSERT INTO submissions(problem_id,user_id,answer,status,score,in_week,created_at) VALUES(?,?,'PRIVATE_SUBMISSION',?,?,?,?)").run(problem, user, status, score, inWeek, time - ago);
test.after(() => sql.close());
const url = path => new URL('https://public-reader.test' + path);
const read = path => readPublicData(url(path).pathname, url(path), db, time);
const noPrivateFields = data => {
  const value = JSON.stringify(data);
  for (const forbidden of ['PRIVATE_', 'private_login', 'user_id', 'problem_id', 'token_hash', 'username', 'exam_tokens']) assert.equal(value.includes(forbidden), false, forbidden);
};

test('only exact public paths issue reads; private endpoints never touch the database', async () => {
  trips = 0; queries.length = 0;
  for (const path of ['/api/me', '/api/me/stats', '/api/users/Person%201', '/api/posts/1', '/api/posts/1/vote', '/api/lab/tokens', '/api/health', '/api/pay/config', '/api/proble ms', '/api/boards/']) {
    assert.equal(publicDataPath(path), false);
    assert.equal(await read(path), undefined);
  }
  assert.equal(trips, 0); assert.equal(queries.length, 0);
});

test('board counters respect language and rolling day, including notices', async () => {
  trips = 0;
  const result = await read('/api/boards');
  assert.equal(trips, 1);
  assert.deepEqual(result.boards.find(row => row.board === 'free'), { board: 'free', n: 30, today: 29 });
  assert.deepEqual(result.boards.find(row => row.board === 'qna'), { board: 'qna', n: 2, today: 2 });
  const english = await read('/api/boards?lang=en');
  assert.deepEqual(english.boards, [{ board: 'free', n: 2, today: 2 }]);
  noPrivateFields(result);
});

test('post list preserves pagination, language, notices, snippets and deleted-author flags in one trip', async () => {
  trips = 0; queries.length = 0;
  const result = await read('/api/posts?board=free');
  assert.equal(trips, 1); assert.equal(queries.length, 3);
  assert.equal(result.total, 29); assert.equal(result.per, 20); assert.equal(result.page, 1);
  assert.equal(result.posts[0].id, 30); assert.equal(result.posts[0].snip.length, 160);
  assert.equal(result.posts.find(row => row.id === 29).gone, 1);
  assert.deepEqual(result.notices.map(row => row.id), [101]);
  assert.deepEqual((await read('/api/posts?board=qna')).notices.map(row => row.id), [102, 101]);
  const second = await read('/api/posts?board=free&page=2');
  assert.equal(second.posts.length, 9); assert.deepEqual(second.notices, []);
  const english = await read('/api/posts?lang=en');
  assert.deepEqual(english.posts.map(row => row.id), [201]); assert.deepEqual(english.notices.map(row => row.id), [104]);
  assert.equal((await read('/api/posts?page=999')).page, 500);
  assert.equal((await read('/api/posts?page=-9')).page, 1);
  noPrivateFields(result);
});

test('search parameters remain bound and LIKE wildcards are literal; sort and best filters retain semantics', async () => {
  const search = '/api/posts?' + new URLSearchParams({ q: '100%', field: 'title' });
  assert.deepEqual((await read(search)).posts.map(row => row.id), [2]);
  assert.deepEqual((await read('/api/posts?' + new URLSearchParams({ q: '_a', field: 'title' }))).posts.map(row => row.id), [2]);
  const author = await read('/api/posts?' + new URLSearchParams({ q: 'Person 2', field: 'author' }));
  assert.ok(author.posts.length > 0 && author.posts.every(row => row.nickname === 'Person 2'));
  const attack = "%' OR 1=1 --";
  assert.equal((await read('/api/posts?' + new URLSearchParams({ q: attack }))).total, 0);
  assert.ok(queries.every(({ query }) => !query.includes(attack)));
  assert.equal((await read('/api/posts?sort=top')).posts[0].id, 3);
  assert.equal((await read('/api/posts?sort=cmt')).posts[0].id, 5);
  assert.equal((await read('/api/posts?sort=hot')).posts[0].id, 5);
  assert.deepEqual((await read('/api/posts?best=1')).posts.map(row => row.id), [4, 3]);
  assert.deepEqual((await read('/api/posts?tag=q')).posts.map(row => row.id), [1]);
  const before = trips;
  await assert.rejects(read('/api/posts?board=invalid'), error => error instanceof PublicDataError && error.status === 400 && error.code === 'bad_board');
  assert.equal(trips, before);
});

test('anonymous weekly data batches metadata, counts and ranking without reading or leaking answer material', async () => {
  trips = 0; queries.length = 0;
  const result = await read('/api/weekly?lang=en');
  assert.equal(trips, 1); assert.equal(queries.length, 4);
  assert.equal(result.week, '2099-W01'); assert.equal(result.now, time); assert.equal(result.user, null);
  assert.deepEqual(result.problems.map(row => row.id), [501, 502]);
  assert.equal(result.problems[0].title, 'Public title');
  assert.equal(result.problems[0].users, 4); assert.equal(result.problems[0].solvers, 2);
  assert.equal(result.problems[1].users, 2); assert.equal(result.problems[1].solvers, 1);
  assert.equal(result.top[0].nickname, 'Person 1'); assert.equal(result.top[0].total, 116);
  assert.equal(result.top[0].solved, 2); assert.equal(result.top[1].total, 80);
  assert.ok(result.problems.every(row => row.open && !row.closed));
  assert.ok(result.weeks.every(row => row.week !== '2100-W01'));
  for (const problem of result.problems) for (const field of ['answer', 'body', 'criteria', 'solution', 'rubric', 'model_ko']) assert.equal(field in problem, false);
  const closed = await read('/api/weekly?week=2098-W52');
  assert.equal(closed.problems[0].closed, true); noPrivateFields(closed); noPrivateFields(result);
  const empty = await read('/api/weekly?week=2100-W01');
  assert.deepEqual(empty.problems, []); assert.equal(empty.week, '2100-W01');
});

test('ranking preserves best-per-problem, weekly eligibility and rating order without account identifiers', async () => {
  trips = 0;
  const all = await read('/api/rank'); assert.equal(trips, 1);
  assert.equal(all.rows[0].nickname, 'Person 2'); assert.equal(all.rows[0].total, 200);
  assert.equal(all.rows[0].rank, 1); assert.equal(all.mine, null); assert.equal(all.user, null);
  assert.deepEqual(all.tierAt, TIER_AT);
  const week = await read('/api/rank?scope=week&week=2099-W01');
  assert.equal(week.rows[0].nickname, 'Person 1'); assert.equal(week.rows[0].total, 116);
  assert.equal(week.rows[0].last, time - 50); assert.equal(week.rows[1].tried, 1);
  assert.ok(week.rows.every(row => !['Person 3', 'Person 4'].includes(row.nickname)));
  assert.deepEqual(await readPublicRanking(db, '2099-W01'), week.rows.map(({ rank, ...row }) => row));
  noPrivateFields(all); noPrivateFields(week);
});

test('shared pure ranking helpers retain tier boundaries, tie order and Korean ISO-week rollover', () => {
  assert.equal(rateUser([1]), 2); assert.equal(tierOf(0), 0); assert.equal(tierOf(3000), 31);
  assert.equal(publicIsoWeek(Date.parse('2026-10-25T14:59:59Z') / 1000), '2026-W43');
  assert.equal(publicIsoWeek(Date.parse('2026-10-25T15:00:00Z') / 1000), '2026-W44');
  const raw = Array.from({ length: 205 }, (_, i) => ({ user_id: i, problem_id: 1, s: 100, at: 205 - i, points: 100, level: 1, nickname: 'Public ' + i, av: null }));
  const ranked = projectRankingRows(raw, true);
  assert.equal(ranked.length, 200); assert.equal(ranked[0].nickname, 'Public 204'); noPrivateFields(ranked);
});

test('monthly and legacy routes prefer one active month and expose compatible period and selector aliases', async () => {
  const month = isoMonth(time);
  for (const [id, period, ago] of [[505, month, 700], [506, '2029-01', 800]]) sql.prepare(`INSERT INTO problems(id,week,no,kind,points,level,title_ko,title_en,body_ko,body_en,opens_at,closes_at,created_at)
    VALUES(?,?,1,'short',100,10,'월간 제목','Monthly title','PRIVATE_BODY','PRIVATE_BODY',?,?,?)`).run(id, period, time - ago, time + 600, time);
  sql.prepare("INSERT INTO submissions(problem_id,user_id,answer,status,score,in_week,created_at) VALUES(505,2,'PRIVATE_MONTHLY_SUBMISSION','graded',100,1,?)").run(time);
  trips = 0;
  const monthly = await read('/api/monthly'); assert.equal(trips, 1);
  assert.equal(monthly.week, month); assert.equal(monthly.period, month); assert.equal(monthly.month, month);
  assert.deepEqual(monthly.problems.map(row => row.id), [505], 'month preference beats a newer overlapping legacy week');
  assert.deepEqual(monthly.months, monthly.weeks);
  assert.deepEqual((await read('/api/weekly')).problems, monthly.problems);
  assert.equal(await currentPeriod(db, time), month);
  const explicit = await read('/api/monthly?' + new URLSearchParams({ month, week: '2099-W01' }));
  assert.equal(explicit.week, month, 'month query parameter takes precedence');
  assert.deepEqual((await read('/api/monthly?week=2099-W01')).problems.map(row => row.id), [501, 502]);
  trips = 0;
  const ranked = await read('/api/rank?scope=month'); assert.equal(trips, 1, 'active period and ranking share one batch');
  assert.equal(ranked.scope, 'month'); assert.equal(ranked.week, month); assert.equal(ranked.month, month);
  assert.deepEqual(ranked.rows.map(row => row.nickname), ['Person 2']);
  assert.equal((await read('/api/rank?scope=week')).week, month);
  noPrivateFields(monthly); noPrivateFields(ranked);
});

test('the migrated 2026-W44 bookmark route resolves to November without breaking other legacy weeks', async () => {
  sql.prepare(`INSERT INTO problems(id,week,no,kind,points,level,title_ko,title_en,body_ko,body_en,opens_at,closes_at,created_at)
    VALUES(507,'2026-11',1,'short',100,10,'11월 문제','November problem','PRIVATE_BODY','PRIVATE_BODY',?,?,?)`).run(time - 1000, time + 600, time);
  assert.equal(arenaPeriod(url('/api/weekly?week=2026-W44')), '2026-11');
  assert.equal(arenaPeriod(url('/api/weekly?week=2099-W01')), '2099-W01');
  const migrated = await read('/api/weekly?week=2026-W44');
  assert.equal(migrated.period, '2026-11'); assert.equal(migrated.month, '2026-11');
  assert.deepEqual(migrated.problems.map(row => row.id), [507]);
  const rank = await read('/api/rank?scope=week&week=2026-W44');
  assert.equal(rank.week, '2026-11'); assert.equal(rank.month, '2026-11');
});

test('invalid month and week values are rejected before querying even for all-time rankings', async () => {
  const before = trips;
  for (const period of ['2026-00', '2026-13', '2026-W00', '2026-W54', "2026-11' OR 1=1"]) {
    for (const path of ['/api/monthly', '/api/weekly', '/api/rank?scope=all']) {
      const target = url(path); target.searchParams.set('month', period);
      await assert.rejects(read(target.pathname + target.search), error => error instanceof PublicDataError && error.code === 'bad_week');
    }
  }
  assert.equal(trips, before);
});

test('empty active data falls back to the Korean calendar month rather than an ISO week', async () => {
  const later = time + 40 * 86400, month = isoMonth(later);
  const empty = await readPublicData('/api/monthly', url('/api/monthly'), db, later);
  assert.equal(empty.week, month); assert.equal(empty.period, month); assert.equal(empty.month, month); assert.deepEqual(empty.problems, []);
  const ranking = await readPublicData('/api/rank', url('/api/rank?scope=month'), db, later);
  assert.equal(ranking.week, month); assert.equal(ranking.month, month); assert.deepEqual(ranking.rows, []);
  assert.equal(await currentPeriod(db, later), month);
});

test('public monthly summaries include blank answer-sheet descriptors and period aliases without student answers', async () => {
  sql.prepare(`INSERT INTO problems(id,week,no,kind,points,level,title_ko,title_en,body_ko,body_en,opens_at,closes_at,created_at)
    VALUES(4,'2026-11',10,'essay',100,10,'구조화 답안','Structured answer','PRIVATE_BODY','PRIVATE_BODY',?,?,?)`).run(time - 1000, time + 600, time);
  const monthly = await read('/api/monthly?month=2026-11');
  const problem = monthly.problems.find(row => row.id === 4);
  assert.equal(problem.period, '2026-11'); assert.equal(problem.month, '2026-11');
  assert.equal(problem.answerSheet.limit, 3);
  assert.equal(problem.answerSheet.parts.reduce((sum, part) => sum + part.points, 0), 100);
  assert.deepEqual(Object.keys(problem.answerSheet).sort(), ['key', 'limit', 'pages', 'parts', 'round', 'version']);
  assert.equal(problem.answerSheet.key,'proton-chain-v1');
  assert.deepEqual(problem.answerSheet.parts.map(part=>part.displayId),['A.1','A.2','A.3','A.4','A.5','B.1','B.2','B.3','B.4','B.5']);
  assert.equal(problem.round,'theory');assert.equal(problem.answerSheet.round,'theory');
  assert.ok(problem.answerSheet.parts.every(part => !('answer' in part) && !('working' in part) && part.label_ko && part.label_en));
  assert.equal('attempts' in problem, false, 'per-account remaining attempts never enter public data');
  assert.equal('answer_sheet' in problem, false); noPrivateFields(monthly);
});

test('public monthly and legacy summaries omit native problem credits while preserving unrelated sources and stored provenance', async () => {
  const nativeCredit = 'xPhO 2026 Week 1 · Carina · 제공 자료 번역·웹 편집';
  const unrelatedCredit = 'Independent competition source';
  for (const [id, number, source] of [[6, 1, nativeCredit], [509, 2, unrelatedCredit]]) {
    sql.prepare(`INSERT INTO problems(id,week,no,kind,points,level,title_ko,title_en,source,body_ko,body_en,opens_at,closes_at,created_at)
      VALUES(?,'2031-12',?,'essay',100,10,'공개 제목','Public title',?,'PRIVATE_BODY','PRIVATE_BODY',?,?,?)`)
      .run(id, number, source, time - 1000, time + 600, time);
  }
  try {
    for (const route of ['monthly', 'weekly']) {
      const result = await read(`/api/${route}?month=2031-12&lang=en`);
      assert.deepEqual(result.problems.map(problem => problem.id), [6, 509]);
      assert.equal(result.problems[0].source, null, 'the shared public lane applies native monthly presentation policy');
      assert.equal(result.problems[1].source, unrelatedCredit, 'other competition credits remain visible');
      assert.ok(result.problems[0].answerSheet);
      assert.equal('answerSheet' in result.problems[1], false);
      assert.ok(!JSON.stringify(result).includes(nativeCredit));
      noPrivateFields(result);
    }
    assert.equal(sql.prepare('SELECT source FROM problems WHERE id=6').get().source, nativeCredit,
      'public projection never changes stored source metadata');
  } finally { sql.prepare('DELETE FROM problems WHERE id IN (6,509)').run(); }
});

test('retired problems disappear from public lists, period selection, week selectors and rankings', async () => {
  const rankingBefore = await readPublicRanking(db), periodBefore = await currentPeriod(db, time);
  sql.prepare(`INSERT INTO problems(id,week,no,kind,points,level,title_ko,title_en,body_ko,body_en,opens_at,closes_at,created_at)
    VALUES(508,'2050-01',1,'short',100,30,'Retired title','Retired title','PRIVATE_BODY','PRIVATE_BODY',?,?,?)`).run(time - 1, time + 5000, time);
  sql.prepare("INSERT INTO submissions(problem_id,user_id,answer,status,score,in_week,created_at) VALUES(508,1,'PRIVATE_RETIRED_ANSWER','graded',100,1,?)").run(time);
  sql.prepare("INSERT INTO monthly_problem_retirements(problem_id,retired_at,reason) VALUES(508,?,'Public visibility change')").run(time);
  assert.deepEqual(await readPublicRanking(db), rankingBefore);
  assert.equal(await currentPeriod(db, time), periodBefore);
  const monthly = await read('/api/monthly');
  assert.equal(monthly.problems.some(problem => problem.id === 508), false);
  assert.equal(monthly.weeks.some(period => period.week === '2050-01'), false);
  assert.deepEqual((await read('/api/monthly?month=2050-01')).problems, []);
  sql.prepare("INSERT INTO monthly_problem_retirements(problem_id,retired_at,reason) VALUES(501,?,'Retired legacy item')").run(time);
  const legacy = await read('/api/weekly?week=2099-W01');
  assert.deepEqual(legacy.problems.map(problem => problem.id), [502]);
  assert.equal(legacy.weeks.find(period => period.week === '2099-W01').n, 1);
  assert.equal((await readPublicRanking(db)).find(row => row.nickname === 'Person 1').total, 16);
});

test('monthly public metadata announces 9/6/3 prizes and published rankings use the frozen result without financial or answer reads',async()=>{
  const period='2040-07',close=time-100;
  for(const [id,no] of [[701,1],[702,2]]) sql.prepare(`INSERT INTO problems(id,week,no,kind,points,level,title_ko,title_en,body_ko,body_en,opens_at,closes_at,created_at)
    VALUES(?,?,?,'short',100,10,'최종 결과','Final result','PRIVATE_BODY','PRIVATE_BODY',?,?,?)`).run(id,period,no,time-1000,close,time-1000);
  for(const [problem,user,score] of [[701,1,40],[702,1,60],[701,2,30],[702,2,50]]) sql.prepare(`INSERT INTO submissions(problem_id,user_id,answer,status,score,in_week,created_at)
    VALUES(?,?,'PRIVATE_PRIZE_SUBMISSION','graded',?,1,?)`).run(problem,user,score,time-500);
  const planned=await read('/api/monthly?month='+period);
  assert.equal(planned.reward.eligible,true);assert.equal(planned.reward.announcement_at,close);
  assert.equal(planned.reward.status,'awaiting_publication');assert.equal(planned.reward.rows,null);
  assert.deepEqual(planned.reward.rewards,[{rank:1,tokens:9},{rank:2,tokens:6},{rank:3,tokens:3}]);
  sql.exec(`CREATE TABLE monthly_result_publications(period TEXT PRIMARY KEY,announcement_at INTEGER,published_at INTEGER,policy_version TEXT);
    CREATE TABLE monthly_result_rows(period TEXT,rank INTEGER,user_id INTEGER,nickname TEXT,av TEXT,total REAL,solved INTEGER,tried INTEGER,last INTEGER,levels TEXT,token_reward INTEGER,PRIMARY KEY(period,rank))`);
  sql.prepare("INSERT INTO monthly_result_publications VALUES(?,?,?,'monthly-token-awards-v1')").run(period,close,close+1);
  for(const [rank,user,total,tokens] of [[1,1,100,9],[2,2,80,6]]) sql.prepare("INSERT INTO monthly_result_rows VALUES(?,?,?,?,NULL,?,0,2,?,'[]',?)").run(period,rank,user,'Person '+user,total,time-500,tokens);
  sql.prepare('UPDATE submissions SET score=100 WHERE problem_id IN (701,702) AND user_id=2').run();
  queries.length=0;
  const monthly=await read('/api/monthly?month='+period),rank=await read('/api/rank?scope=month&month='+period);
  assert.equal(monthly.reward.status,'published');assert.equal(rank.reward.status,'published');
  assert.deepEqual(monthly.top.map(row=>[row.rank,row.nickname,row.total,row.token_reward]),[[1,'Person 1',100,9],[2,'Person 2',80,6]]);
  assert.deepEqual(rank.rows,monthly.top);
  assert.equal((await readPublicRanking(db,period)).find(row=>row.nickname==='Person 2').total,200,'live scores changed while the published month stays frozen');
  assert.ok(queries.every(({query})=>/^SELECT\b/i.test(query)));
  noPrivateFields(monthly);noPrivateFields(rank);
  assert.equal((await read('/api/rank')).reward,undefined,'all-time ranking has no monthly prize overlay');
});
