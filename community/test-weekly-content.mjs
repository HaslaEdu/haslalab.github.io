// Real SQLite and the existing Worker grading route; no production account or API calls.
// Run: node --test community/test-weekly-content.mjs
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import test from 'node:test';
import worker from './src/index.js';
import { validateContent, publishWeeklyContent, ensureWeeklyContent, WEEKLY_PUBLICATION_ID, MONTHLY_PUBLICATION_ID } from './src/weekly-content.js';
import { MONTHLY_RETIREMENT_ID } from './src/monthly-answers.js';
import { getMonthlyAnswerSheet } from '../monthly-problems.mjs';
import { monthlyPublicPresentation } from './src/monthly-presentation.js';

const content = JSON.parse(readFileSync(new URL('./weekly/2026-W44.json', import.meta.url), 'utf8'));
const clone = value => JSON.parse(JSON.stringify(value));
const t = Math.floor(Date.now() / 1000);

function database() {
  const sqlite = new DatabaseSync(':memory:');
  const migrations = new URL('./migrations/', import.meta.url);
  for (const name of readdirSync(migrations).filter(n => /^00(?:0[1-9]|1[01])_.*\.sql$/.test(n)).sort()) {
    sqlite.exec(readFileSync(new URL(name, migrations), 'utf8'));
  }
  return sqlite;
}

function d1(sqlite) {
  return {
    prepare(sql) {
      const st = sqlite.prepare(sql);
      const make = args => ({
        bind: (...values) => make(values),
        async all() { return { results: st.all(...args) }; },
        async first() { return st.get(...args) || null; },
        async run() { return this.executeSync(); },
        executeSync() {
          if (st.columns().length) return { results: st.all(...args) };
          const r = st.run(...args);
          return { success: true, meta: { changes: r.changes, last_row_id: Number(r.lastInsertRowid) } };
        },
      });
      return make([]);
    },
    async batch(statements) {
      sqlite.exec('BEGIN');
      try {
        const results = statements.map(st => st.executeSync());
        sqlite.exec('COMMIT');
        return results;
      } catch (error) { sqlite.exec('ROLLBACK'); throw error; }
    },
  };
}

test('three reviewed web problems have bilingual references and complete partial-credit rubrics', () => {
  validateContent(content);
  assert.equal(content.problems.length, 3);
  assert.deepEqual(content.problems.map(p => p.no).sort((a, b) => a - b), [4, 5, 6]);
  assert.ok(content.problems.every(p => p.week === '2026-W44' && p.kind === 'essay' && p.subject === 'physics'));
  for (const p of content.problems) {
    for (const field of ['body_ko', 'body_en', 'model_ko', 'model_en']) assert.ok(p[field].length > 100, `${p.title_ko}: ${field}`);
    assert.equal(p.rubric.reduce((sum, c) => sum + c.max, 0), p.points);
    assert.ok(p.rubric.every(c => c.partial?.trim()), `${p.title_ko}: explicit partial credit`);
  }
});

test('publishing twice appends exactly three records and preserves existing problems, edits and submissions', async () => {
  const db = database();
  try {
    const originals = db.prepare('SELECT * FROM problems ORDER BY id').all();
    assert.equal(originals.length, 3);
    assert.equal((await publishWeeklyContent(d1(db), content)).inserted, 3);
    assert.equal((await publishWeeklyContent(d1(db), content)).inserted, 0);
    assert.equal(db.prepare('SELECT COUNT(*) n FROM problems').get().n, 6);
    assert.deepEqual(db.prepare('SELECT * FROM problems WHERE id<=3 ORDER BY id').all(), originals);
    const p = db.prepare('SELECT * FROM problems WHERE week=? AND no=?').get('2026-W44', 4);
    db.prepare("INSERT INTO users(id,username,nickname,pw,role,created_at) VALUES(1,'seed-student','Seed student','unused','user',?)").run(t);
    db.prepare("INSERT INTO submissions(problem_id,user_id,answer,status,score,in_week,created_at) VALUES(?,1,'Saved answer','graded',10,1,?)").run(p.id, t);
    db.prepare("UPDATE problems SET body_ko='An administrator maintained this body',title_ko='Administrator renamed this problem',source='Revised source credit' WHERE id=?").run(p.id);
    const before = db.prepare('SELECT * FROM submissions').all();
    await publishWeeklyContent(d1(db), content);
    const maintained = db.prepare('SELECT body_ko,title_ko,source FROM problems WHERE id=?').get(p.id);
    assert.equal(maintained.body_ko, 'An administrator maintained this body');
    assert.equal(maintained.title_ko, 'Administrator renamed this problem');
    assert.equal(maintained.source, 'Revised source credit');
    assert.deepEqual(db.prepare('SELECT * FROM submissions').all(), before);
  } finally { db.close(); }
});

test('an occupied number belonging to different content aborts all three inserts', async () => {
  const db = database();
  try {
    const collision = clone(content);
    collision.problems[0].no = 2;
    collision.problems[0].title_ko = 'A different problem in an existing slot';
    const originals = db.prepare('SELECT * FROM problems ORDER BY id').all();
    await assert.rejects(publishWeeklyContent(d1(db), collision), /NOT NULL constraint failed/);
    assert.deepEqual(db.prepare('SELECT * FROM problems ORDER BY id').all(), originals, 'guard failure rolls back the complete batch');
  } finally { db.close(); }
});

test('publication rejects incomplete English references, duplicate criteria and inconsistent points', () => {
  for (const [change, message] of [
    [p => { p.model_en = ''; }, /missing model_en/],
    [p => { p.body_en = ''; }, /missing body_en/],
    [p => { p.rubric.push(clone(p.rubric[0])); }, /duplicate criterion id/],
    [p => { p.points++; }, /rubric totals/],
  ]) {
    const invalid = clone(content);
    change(invalid.problems[0]);
    assert.throws(() => validateContent(invalid), message);
  }
});

test('long references use bound values instead of exceeding the SQL statement length limit', async () => {
  const db = database(), large = clone(content), sqlBytes = [];
  large.problems[0].model_en += '\n' + 'A'.repeat(110000);
  const base = d1(db), binding = {
    prepare(sql) {
      sqlBytes.push(Buffer.byteLength(sql));
      const st = base.prepare(sql);
      return { ...st, bind(...values) { assert.ok(values.length <= 100); return st.bind(...values); } };
    },
    batch: statements => base.batch(statements),
  };
  try {
    await publishWeeklyContent(binding, large);
    assert.ok(sqlBytes.every(size => size < 100000));
    assert.equal(db.prepare('SELECT model_en FROM problems WHERE week=? AND no=?').get('2026-W44', 4).model_en, large.problems[0].model_en);
  } finally { db.close(); }
});

test('simultaneous requests share publication and a failed batch can be retried', async () => {
  const db = database(), base = d1(db), key = {};
  let calls = 0;
  const binding = { prepare: sql => base.prepare(sql), async batch(statements) {
    calls++;
    if (calls === 1) throw new Error('Transient D1 test failure');
    return base.batch(statements);
  } };
  try {
    const first = ensureWeeklyContent(binding, key), second = ensureWeeklyContent(binding, key);
    assert.equal(first, second);
    await assert.rejects(first, /Transient D1 test failure/);
    const retry = ensureWeeklyContent(binding, key);
    assert.equal((await retry).inserted, 3);
    assert.equal(ensureWeeklyContent(binding, key), retry);
    assert.equal(calls, 5, 'failed seed, successful retry, monthly transition, answer schema, and introductory retirement');
    assert.equal(db.prepare('SELECT COUNT(*) n FROM problems').get().n, 6);
    assert.equal(db.prepare("SELECT COUNT(*) n FROM problems WHERE week='2026-11'").get().n, 6);
    assert.deepEqual(db.prepare(`SELECT p.id,p.no FROM problems p WHERE NOT EXISTS(
      SELECT 1 FROM monthly_problem_retirements r WHERE r.problem_id=p.id) ORDER BY p.no`).all().map(row => ({ ...row })),
      [{ id: 4, no: 1 }, { id: 5, no: 2 }, { id: 6, no: 3 }]);
  } finally { db.close(); }
});

test('opening the weekly list or a direct problem link publishes through the existing Worker binding', async () => {
  const originalCaches = globalThis.caches;
  globalThis.caches = { default: { async match() {}, async put() {} } };
  try {
    for (const path of ['/weekly?week=2026-W44&lang=ko', '/problems/4?lang=ko']) {
      const db = database();
      try {
        const env = { DB: d1(db), ALLOWED_ORIGINS: 'http://localhost:8765', LAB_KEEP_HOURS: 'off' };
        assert.equal(db.prepare('SELECT COUNT(*) n FROM problems').get().n, 3);
        const response = await worker.fetch(new Request('http://weekly.local/api' + path), env);
        assert.equal(response.status, 200);
        const data = await response.json();
        assert.equal(db.prepare('SELECT COUNT(*) n FROM problems').get().n, 6);
        assert.deepEqual(db.prepare('SELECT id FROM weekly_publications ORDER BY id').all().map(row => row.id),
          [WEEKLY_PUBLICATION_ID, MONTHLY_PUBLICATION_ID, MONTHLY_RETIREMENT_ID].sort(), 'publication, monthly transition and introductory retirement each run once');
        if (path.startsWith('/weekly')) assert.deepEqual(data.problems.map(p => p.id), [4, 5, 6]);
        else assert.equal(data.problem.body, monthlyPublicPresentation({ ...content.problems.find(p => p.no === 4), id: 4 }).body_ko);
      } finally { db.close(); }
    }
  } finally { globalThis.caches = originalCaches; }
});

test('published native problems use authenticated, evidence-backed grading and remain practice after closing', async () => {
  const db = database();
  await publishWeeklyContent(d1(db), content);
  const token = 'w'.repeat(48);
  const tokenHash = Buffer.from(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(token))).toString('base64url');
  db.prepare("INSERT INTO users(id,username,nickname,pw,role,created_at) VALUES(1,'weekly-student','Weekly student','unused','user',?)").run(t);
  db.prepare('INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,1,?,?)').run(tokenHash, t, t + 3600);
  db.prepare('UPDATE problems SET opens_at=?,closes_at=? WHERE no IN (4,5,6) AND week=?').run(t - 60, t + 3600, '2026-W44');
  const rows = db.prepare('SELECT * FROM problems WHERE no IN (4,5,6) AND week=? ORDER BY no').all('2026-W44');
  const env = { DB: d1(db), ALLOWED_ORIGINS: 'http://localhost:8765', LAB_KEEP_HOURS: 'off', GEMINI_API_KEY: 'test-key-no-real-provider' };
  const originalFetch = globalThis.fetch, originalCaches = globalThis.caches;
  globalThis.caches = { default: { async match() {}, async put() {} } };
  const answer = 'I derive the governing equation from the stated assumptions and check its limiting case.';
  let requestNumber = 0;
  const answerBody = row => ({
    request_id: ('weekly-structured-test-' + ++requestNumber).padEnd(40, 'x'), lang: 'ko',
    parts: getMonthlyAnswerSheet(row).parts.map(part => ({ id: part.id, answer, working: answer })),
  });
  let calls = 0, evidenceMode = 'valid';
  globalThis.fetch = async (input, init) => {
    assert.match(String(input), /:generateContent$/);
    const request = JSON.parse(init.body);
    const prompt = request.contents[0].parts.map(part => part.text || '').join('\n');
    calls++;
    if (request.generationConfig.responseSchema.properties.assessment) {
      return Response.json({ candidates: [{ content: { parts: [{ text: JSON.stringify({ assessment: 'uncertain', confidence: 0.5, signals: [] }) }] } }] });
    }
    const p = rows.find(row => prompt.includes(row.body_en));
    assert.ok(p, 'grader receives the complete English web problem');
    assert.ok(prompt.includes(p.model_en), 'grader receives the complete worked reference');
    assert.ok(prompt.includes('[Student answer]\n['));
    assert.ok(prompt.includes('Final answer:\n' + answer));
    assert.ok(prompt.includes('Working:\n' + answer));
    const rubric = JSON.parse(p.rubric);
    const result = {
      scores: rubric.map((c, i) => ({ id: c.id, got: c.max, note: 'Test criterion assessment', decision: 'met',
        evidence: [evidenceMode === 'invented' && i === 0 ? 'Words absent from the submitted answer' : answer] })),
      feedback: [{ quote: answer, note: 'Test feedback linked to the submitted answer', kind: 'good' }],
      confidence: 0.95,
    };
    return Response.json({ candidates: [{ content: { parts: [{ text: JSON.stringify(result) }] } }] });
  };
  async function request(path, { authenticated = false, body } = {}) {
    const response = await worker.fetch(new Request('http://weekly.local/api' + path, {
      method: body === undefined ? 'GET' : 'POST',
      headers: { ...(authenticated ? { Authorization: 'Bearer ' + token } : {}), ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    }), env);
    return { status: response.status, data: await response.json() };
  }
  try {
    const list = await request('/weekly?week=2026-W44&lang=ko');
    assert.equal(list.status, 200);
    assert.deepEqual(list.data.problems.map(p => p.id), [4, 5, 6]);
    for (const p of list.data.problems) for (const key of ['body', 'rubric', 'solution', 'model_en']) assert.equal(key in p, false);
    for (const row of rows) {
      const pub = await request(`/problems/${row.id}?lang=ko`);
      assert.equal(pub.status, 200);
      assert.equal(pub.data.problem.body, monthlyPublicPresentation(row).body_ko);
      assert.equal(pub.data.problem.source, null);
      assert.equal(pub.data.problem.criteria.length, JSON.parse(row.rubric).length);
      assert.equal(pub.data.problem.solution, undefined);
      assert.equal(pub.data.problem.rubric, undefined);
      assert.ok(pub.data.problem.criteria.every(c => !('requirement' in c) && !('partial' in c)));
      const denied = await request(`/problems/${row.id}/submit`, { body: answerBody(row) });
      assert.equal(denied.status, 401);
      const graded = await request(`/problems/${row.id}/submit`, { authenticated: true, body: answerBody(row) });
      assert.equal(graded.status, 200);
      assert.equal(graded.data.status, 'graded');
      assert.equal(graded.data.score, row.points);
      assert.equal(graded.data.detail, null, 'criterion scores and feedback remain private before closing');
      assert.equal(graded.data.feedback_held, true);
      const stored = db.prepare('SELECT * FROM submissions WHERE id=?').get(graded.data.id);
      assert.equal(JSON.parse(stored.detail).scores.reduce((sum, criterion) => sum + criterion.got, 0), row.points);
      assert.equal(stored.in_week, 1);
      assert.ok(stored.answer.includes('Final answer:\n' + answer));
      assert.ok(stored.answer.includes('Working:\n' + answer));
    }
    evidenceMode = 'invented';
    const row = rows[0];
    const unsupported = await request(`/problems/${row.id}/submit`, { authenticated: true, body: answerBody(row) });
    assert.equal(unsupported.data.score, row.points - JSON.parse(row.rubric)[0].max);
    assert.equal(unsupported.data.detail, null);
    const unsupportedDetail = JSON.parse(db.prepare('SELECT detail FROM submissions WHERE id=?').get(unsupported.data.id).detail);
    assert.equal(unsupportedDetail.evidenceIssue, true);
    assert.equal(unsupportedDetail.scores[0].got, 0);
    evidenceMode = 'valid';
    db.prepare('UPDATE problems SET closes_at=? WHERE id=?').run(t - 1, row.id);
    const closed = await request(`/problems/${row.id}?lang=ko`, { authenticated: true });
    assert.equal(closed.data.problem.solution, row.model_ko);
    assert.equal(closed.data.problem.open, false);
    assert.equal(closed.data.problem.mine.length, 2);
    assert.equal(closed.data.problem.mine[0].feedback_held, false);
    assert.equal(closed.data.problem.mine[0].detail.evidenceIssue, true, 'saved feedback releases without another model request');
    assert.equal(closed.data.problem.mine[0].detail.authorship, undefined, 'authorship audit remains private after the deadline');
    const practice = await request(`/problems/${row.id}/submit`, { authenticated: true, body: answerBody(row) });
    assert.equal(practice.data.status, 'graded');
    assert.equal(practice.data.score, row.points);
    assert.equal(db.prepare('SELECT in_week FROM submissions WHERE id=?').get(practice.data.id).in_week, 0);
    assert.equal(calls, 10, 'five accepted answers each use a screen followed by grading');
  } finally {
    globalThis.fetch = originalFetch;
    globalThis.caches = originalCaches;
    db.close();
  }
});
