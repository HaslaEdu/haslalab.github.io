// The global reader runs real SELECTs against SQLite, with every non-public SQL access rejected.
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync, readdirSync } from 'node:fs';
import test from 'node:test';
import { readPublicData, readPublicRanking, projectRankingRows, publicDataPath, publicIsoWeek, rateUser, tierOf, TIER_AT, PublicDataError } from './src/public-data.js';

const sql = new DatabaseSync(':memory:');
for (const name of readdirSync(new URL('./migrations/', import.meta.url)).filter(n => /^\d{4}_.*\.sql$/.test(n)).sort()) sql.exec(readFileSync(new URL('./migrations/' + name, import.meta.url), 'utf8'));
sql.exec('DELETE FROM submissions; DELETE FROM problems;');
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
  [501, 'TEST-W01', 1, 'short', 100, 10, time - 600, time + 600],
  [502, 'TEST-W01', 2, 'essay', 20, 20, time - 600, time + 600],
  [503, 'OLD-W01', 1, 'short', 100, 30, time - 1000, time - 100],
  [504, 'FUTURE-W01', 1, 'short', 100, 30, time + 1000, time + 2000],
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
  assert.equal(result.week, 'TEST-W01'); assert.equal(result.now, time); assert.equal(result.user, null);
  assert.deepEqual(result.problems.map(row => row.id), [501, 502]);
  assert.equal(result.problems[0].title, 'Public title');
  assert.equal(result.problems[0].users, 4); assert.equal(result.problems[0].solvers, 2);
  assert.equal(result.problems[1].users, 2); assert.equal(result.problems[1].solvers, 1);
  assert.equal(result.top[0].nickname, 'Person 1'); assert.equal(result.top[0].total, 116);
  assert.equal(result.top[0].solved, 2); assert.equal(result.top[1].total, 80);
  assert.ok(result.problems.every(row => row.open && !row.closed));
  assert.ok(result.weeks.every(row => row.week !== 'FUTURE-W01'));
  for (const problem of result.problems) for (const field of ['answer', 'body', 'criteria', 'solution', 'rubric', 'model_ko']) assert.equal(field in problem, false);
  const closed = await read('/api/weekly?week=OLD-W01');
  assert.equal(closed.problems[0].closed, true); noPrivateFields(closed); noPrivateFields(result);
  const empty = await read('/api/weekly?week=FUTURE-W01');
  assert.deepEqual(empty.problems, []); assert.equal(empty.week, 'FUTURE-W01');
});

test('ranking preserves best-per-problem, weekly eligibility and rating order without account identifiers', async () => {
  trips = 0;
  const all = await read('/api/rank'); assert.equal(trips, 1);
  assert.equal(all.rows[0].nickname, 'Person 2'); assert.equal(all.rows[0].total, 200);
  assert.equal(all.rows[0].rank, 1); assert.equal(all.mine, null); assert.equal(all.user, null);
  assert.deepEqual(all.tierAt, TIER_AT);
  const week = await read('/api/rank?scope=week&week=TEST-W01');
  assert.equal(week.rows[0].nickname, 'Person 1'); assert.equal(week.rows[0].total, 116);
  assert.equal(week.rows[0].last, time - 50); assert.equal(week.rows[1].tried, 1);
  assert.ok(week.rows.every(row => !['Person 3', 'Person 4'].includes(row.nickname)));
  assert.deepEqual(await readPublicRanking(db, 'TEST-W01'), week.rows.map(({ rank, ...row }) => row));
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
