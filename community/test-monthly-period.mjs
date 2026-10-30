// Monthly scheduling, preserved submissions and the exact Korean month-end boundary.
// Real SQLite and Worker handlers; no production account or external provider call.
import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync, readdirSync } from 'node:fs';
import worker from './src/index.js';
import { publishWeeklyContent, migrateMonthlyPeriod } from './src/weekly-content.js';
import { isProblemPeriod, isoMonth, canonicalProblemPeriod, CURRENT_MONTHLY_PERIOD, MONTHLY_CLOSES_AT } from './src/problem-period.js';

const seconds = iso => Date.parse(iso) / 1000;
const OCTOBER_NOW = seconds('2026-10-30T22:00:00+09:00');
const NOVEMBER_END = seconds('2026-12-01T00:00:00+09:00');

function database() {
  const sql = new DatabaseSync(':memory:');
  const migrations = new URL('./migrations/', import.meta.url);
  for (const name of readdirSync(migrations).filter(n => /^00(?:0[1-9]|1[01])_.*\.sql$/.test(n)).sort()) {
    sql.exec(readFileSync(new URL(name, migrations), 'utf8'));
  }
  return sql;
}

function d1(sql) {
  return {
    prepare(query) {
      const statement = sql.prepare(query);
      const make = args => ({
        bind: (...values) => make(values),
        async first() { return statement.get(...args) || null; },
        async all() { return { results: statement.all(...args) }; },
        async run() { return this.executeSync(); },
        executeSync() {
          if (statement.columns().length) return { results: statement.all(...args) };
          const result = statement.run(...args);
          return { results: [], meta: { changes: result.changes, last_row_id: Number(result.lastInsertRowid) } };
        },
      });
      return make([]);
    },
    async batch(statements) {
      sql.exec('BEGIN');
      try {
        const result = statements.map(statement => statement.executeSync());
        sql.exec('COMMIT');
        return result;
      } catch (error) { sql.exec('ROLLBACK'); throw error; }
    },
  };
}

function cloneProblem(sql, { id = 999, week = '2099-W01', no = 1 } = {}) {
  const original = sql.prepare('SELECT * FROM problems WHERE id=1').get();
  const copy = { ...original, id, week, no, title_ko: '별도 보존 문제', title_en: 'Unrelated preserved problem', source: 'Unrelated source',
    opens_at: OCTOBER_NOW - 60, closes_at: NOVEMBER_END + 86400 };
  const fields = Object.keys(copy);
  sql.prepare(`INSERT INTO problems(${fields.join(',')}) VALUES(${fields.map(() => '?').join(',')})`).run(...Object.values(copy));
}

async function student(sql) {
  const token = 'monthly-local-student'.padEnd(48, 'x');
  const hash = Buffer.from(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(token))).toString('base64url');
  sql.prepare("INSERT INTO users(id,username,nickname,pw,role,created_at) VALUES(1,'monthly-student','Monthly student','local-unused','user',?)").run(OCTOBER_NOW - 86400);
  sql.prepare('INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,1,?,?)').run(hash, OCTOBER_NOW - 86400, NOVEMBER_END + 31 * 86400);
  return token;
}

async function api(env, path, { token, body } = {}) {
  const response = await worker.fetch(new Request('http://monthly.local/api' + path, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { 'Cache-Control': 'no-cache', ...(token ? { Authorization: 'Bearer ' + token } : {}),
      ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  }), env);
  return { status: response.status, data: await response.json() };
}

async function environment(run) {
  const sql = database(), binding = d1(sql);
  const caches = globalThis.caches, fetch = globalThis.fetch;
  globalThis.caches = { default: { async match() {}, async put() {} } };
  globalThis.fetch = () => { throw new Error('Unexpected external provider request'); };
  try {
    return await run({ sql, binding, env: { DB: binding, ALLOWED_ORIGINS: 'http://localhost:8765', LAB_KEEP_HOURS: 'off' } });
  } finally { globalThis.caches = caches; globalThis.fetch = fetch; sql.close(); }
}

test('period helpers accept real months, retain legacy weeks and use Korea time at month boundaries', () => {
  assert.equal(CURRENT_MONTHLY_PERIOD, '2026-11');
  assert.equal(MONTHLY_CLOSES_AT, NOVEMBER_END);
  for (const value of ['2026-01', '2026-11', '2026-12', '2026-W44']) assert.equal(isProblemPeriod(value), true, value);
  for (const value of ['2026-00', '2026-13', '2026-1', '2026-W00', '2026-W54', '2026-11-extra']) assert.equal(isProblemPeriod(value), false, value);
  assert.equal(canonicalProblemPeriod('2026-W44'), '2026-11');
  assert.equal(canonicalProblemPeriod('2099-W01'), '2099-W01');
  assert.equal(isoMonth(NOVEMBER_END - 1), '2026-11');
  assert.equal(isoMonth(NOVEMBER_END), '2026-12');
  assert.equal(isoMonth(seconds('2026-12-31T23:59:59+09:00')), '2026-12');
  assert.equal(isoMonth(seconds('2027-01-01T00:00:00+09:00')), '2027-01');
});

test('monthly migration moves the original six IDs and deadline without changing questions, grades or other periods', async () => {
  await environment(async ({ sql, binding }) => {
    await publishWeeklyContent(binding);
    cloneProblem(sql);
    await student(sql);
    const saved = [
      [1, 'Original ranked answer', 55, 1, OCTOBER_NOW],
      [4, 'Answer within the extended November window', 77, 0, seconds('2026-11-20T12:00:00+09:00')],
      [5, 'Last November second', 88, 0, NOVEMBER_END - 1],
      [6, 'December practice', 99, 0, NOVEMBER_END],
      [999, 'Unrelated practice answer', 66, 0, OCTOBER_NOW],
    ];
    for (const [problem, answer, score, inWeek, at] of saved) {
      sql.prepare("INSERT INTO submissions(problem_id,user_id,answer,status,score,detail,in_week,created_at,graded_at) VALUES(?,1,?,'graded',?,'{\"saved\":true}',?,?,?)")
        .run(problem, answer, score, inWeek, at, at);
    }
    const originals = sql.prepare('SELECT * FROM problems ORDER BY id').all();
    const submissions = sql.prepare('SELECT * FROM submissions ORDER BY id').all();
    await migrateMonthlyPeriod(binding);
    const after = sql.prepare('SELECT * FROM problems ORDER BY id').all();
    assert.deepEqual(after.map(p => p.id), originals.map(p => p.id));
    for (let i = 0; i < 6; i++) {
      assert.equal(after[i].week, '2026-11');
      assert.equal(after[i].closes_at, NOVEMBER_END);
      assert.deepEqual({ ...after[i], week: originals[i].week, closes_at: originals[i].closes_at }, { ...originals[i] });
    }
    assert.deepEqual(after[6], originals[6], 'unrelated legacy period remains unchanged');
    const ranked = sql.prepare('SELECT * FROM submissions ORDER BY id').all();
    assert.deepEqual(ranked.map(s => s.in_week), [1, 1, 1, 0, 0]);
    assert.deepEqual(ranked.map((s, i) => ({ ...s, in_week: submissions[i].in_week })), submissions.map(s => ({ ...s })), 'saved scores, evidence and answer history are preserved');
    sql.prepare("UPDATE problems SET title_ko='관리자가 유지한 제목',closes_at=? WHERE id=4").run(NOVEMBER_END + 3600);
    const maintained = sql.prepare('SELECT * FROM problems WHERE id=4').get();
    await migrateMonthlyPeriod(binding);
    assert.deepEqual(sql.prepare('SELECT * FROM problems WHERE id=4').get(), maintained, 'completed migration does not overwrite later administrator edits');
  });
});

test('an occupied November slot rolls back the complete period migration', async () => {
  await environment(async ({ sql, binding }) => {
    await publishWeeklyContent(binding);
    cloneProblem(sql, { week: '2026-11', no: 4 });
    const original = sql.prepare('SELECT * FROM problems ORDER BY id').all();
    await assert.rejects(migrateMonthlyPeriod(binding));
    assert.deepEqual(sql.prepare('SELECT * FROM problems ORDER BY id').all(), original);
  });
});

test('October visitors see the active November month, and legacy weekly API links still resolve', async t => {
  t.mock.timers.enable({ apis: ['Date'], now: new Date(OCTOBER_NOW * 1000) });
  await environment(async ({ sql, binding, env }) => {
    await publishWeeklyContent(binding);
    cloneProblem(sql);
    const token = await student(sql);
    sql.prepare("INSERT INTO submissions(problem_id,user_id,answer,status,score,in_week,created_at) VALUES(1,1,'Existing ranked answer','graded',70,1,?)").run(OCTOBER_NOW - 1);
    const monthly = await api(env, '/monthly?lang=ko', { token });
    assert.equal(monthly.status, 200);
    assert.equal(monthly.data.week, '2026-11');
    assert.deepEqual(monthly.data.problems.map(p => p.id), [1, 2, 3, 4, 5, 6]);
    assert.ok(monthly.data.problems.every(p => p.closes_at === NOVEMBER_END && p.open));
    const legacy = await api(env, '/weekly?week=2026-W44&lang=ko', { token });
    assert.equal(legacy.status, 200);
    assert.equal(legacy.data.week, '2026-11');
    assert.deepEqual(legacy.data.problems, monthly.data.problems);
    const rank = await api(env, '/rank?scope=month', { token });
    assert.equal(rank.status, 200);
    assert.equal(rank.data.week, '2026-11');
    assert.equal(rank.data.rows[0].total, 70, 'published active month wins over October calendar fallback');
    const oldRank = await api(env, '/rank?scope=week&week=2026-W44', { token });
    assert.deepEqual(oldRank.data.rows, rank.data.rows);
    const unrelated = await api(env, '/weekly?week=2099-W01&lang=ko', { token });
    assert.equal(unrelated.status, 200);
    assert.equal(unrelated.data.week, '2099-W01');
    assert.deepEqual(unrelated.data.problems.map(p => p.id), [999]);
  });
});

test('November 30 remains ranked through 23:59:59 KST; December begins practice and releases solutions', async t => {
  t.mock.timers.enable({ apis: ['Date'], now: new Date((NOVEMBER_END - 1) * 1000) });
  await environment(async ({ sql, env }) => {
    const token = await student(sql);
    const before = await api(env, '/problems/1?lang=ko', { token });
    assert.equal(before.status, 200);
    assert.equal(before.data.problem.open, true);
    assert.equal(before.data.problem.solution, undefined);
    const ranked = await api(env, '/problems/1/submit', { token, body: { answer: '0', lang: 'ko' } });
    assert.equal(ranked.status, 200);
    assert.equal(ranked.data.score, 0);
    assert.equal(sql.prepare('SELECT in_week FROM submissions WHERE id=?').get(ranked.data.id).in_week, 1);
    t.mock.timers.setTime(NOVEMBER_END * 1000);
    const closed = await api(env, '/problems/1?lang=ko', { token });
    assert.equal(closed.data.problem.open, false);
    assert.ok(closed.data.problem.solution?.length > 0);
    const practice = await api(env, '/problems/1/submit', { token, body: { answer: '1.79', lang: 'ko' } });
    assert.equal(practice.status, 200);
    assert.equal(practice.data.score, 100);
    assert.equal(sql.prepare('SELECT in_week FROM submissions WHERE id=?').get(practice.data.id).in_week, 0);
    const monthRank = await api(env, '/rank?scope=month&month=2026-11', { token });
    assert.equal(monthRank.data.rows[0].total, 0, 'a late perfect answer does not enter the closed monthly ranking');
    const allTime = await api(env, '/rank?scope=all', { token });
    assert.equal(allTime.data.rows[0].total, 100, 'post-close practice still updates the existing all-time record');
  });
});
