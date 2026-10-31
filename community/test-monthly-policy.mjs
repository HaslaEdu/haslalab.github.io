// Authenticated Worker routes and real SQLite; every model response below is local.
import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync, readdirSync } from 'node:fs';
import worker from './src/index.js';
import { assessMonthlyAuthorship, monthlySubmissionView } from './src/monthly-policy.js';

const NOW = Date.parse('2026-11-01T12:00:00+09:00') / 1000;
const CLOSE = Date.parse('2026-12-01T00:00:00+09:00') / 1000;
const equation = '$a^2+b^2=c^2$';
const disclosure = 'As an AI language model, I can present a derivation.';
const metadata = 'The generated message has "role": "assistant" in its metadata.';
const payload = (name, working = 'Apply the governing equation.') => ({
  provider:'gemini', request_id: name.padEnd(32, 'x'), lang: 'ko',
  parts: [{ id: 'a', answer: equation, working }],
});
const suspect = () => ({ assessment: 'ai_suspected', confidence: 0.999,
  signals: [
    { category: 'model_self_disclosure', quote: disclosure, reason: 'Explicit AI self-identification in the author’s voice.' },
    { category: 'assistant_message_artifact', quote: metadata, reason: 'Serialized assistant-role metadata retained in a generated answer.' },
  ] });
const uncertain = () => ({ assessment: 'uncertain', confidence: 0.5, signals: [] });

function database() {
  const sql = new DatabaseSync(':memory:'), migrations = new URL('./migrations/', import.meta.url);
  for (const name of readdirSync(migrations).filter(n => /^00(?:0[1-9]|1[01])_.*\.sql$/.test(n)).sort()) {
    sql.exec(readFileSync(new URL(name, migrations), 'utf8'));
  }
  const DB = {
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
      try { const result = statements.map(statement => statement.executeSync()); sql.exec('COMMIT'); return result; }
      catch (error) { sql.exec('ROLLBACK'); throw error; }
    },
  };
  return { sql, DB };
}

async function environment(run) {
  const { sql, DB } = database(), saved = { fetch: globalThis.fetch, caches: globalThis.caches, now: Date.now };
  let clock = NOW, screen = uncertain, beforeScreen = async () => {}, failScreen = false, failGrade = false;
  const calls = { screen: 0, grade: 0 };
  Date.now = () => clock * 1000;
  globalThis.caches = { default: { async match() {}, async put() {} } };
  const token = 'monthly-release-policy-student'.padEnd(48, 'x');
  const hash = Buffer.from(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(token))).toString('base64url');
  sql.prepare("INSERT INTO users(id,username,nickname,pw,role,created_at) VALUES(1,'release-student','Release student','unused','user',?)").run(NOW - 86400);
  sql.prepare('INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,1,?,?)').run(hash, NOW - 86400, CLOSE + 86400);
  const env = { DB, ALLOWED_ORIGINS: 'http://localhost:8765', LAB_KEEP_HOURS: 'off', GEMINI_API_KEY: 'local-test-only' };
  globalThis.fetch = async (url, init) => {
    assert.match(String(url), /:generateContent$/);
    const request = JSON.parse(init.body), schema = request.generationConfig.responseSchema;
    const prompt = request.contents[0].parts.map(part => part.text || '').join('\n');
    let raw;
    if (schema.properties.assessment) {
      calls.screen++;
      await beforeScreen(prompt);
      if (failScreen) throw new Error('Local screening provider unavailable');
      raw = screen(prompt);
    } else {
      calls.grade++;
      if (failGrade) throw new Error('Local grading provider unavailable');
      assert.ok(prompt.includes('[Student answer]'));
      const rubric = JSON.parse(sql.prepare('SELECT rubric FROM problems WHERE id=4').get().rubric);
      raw = {
        scores: rubric.map(criterion => ({ id: criterion.id, got: criterion.id === 'a' ? criterion.max : 0,
          decision: criterion.id === 'a' ? 'met' : 'not_met', note: 'PRIVATE_CRITERION_NOTE', evidence: criterion.id === 'a' ? [equation] : [] })),
        feedback: [{ quote: equation, note: 'PRIVATE_CORRECTION_FEEDBACK', kind: 'good' }], confidence: 0.99,
      };
    }
    return Response.json({ candidates: [{ content: { parts: [{ text: JSON.stringify(raw) }] } }] });
  };
  const api = async (path, { body, authenticated = true } = {}) => {
    const response = await worker.fetch(new Request('http://monthly-policy.local/api' + path, {
      method: body === undefined ? 'GET' : 'POST',
      headers: { 'Cache-Control': 'no-cache', ...(authenticated ? { Authorization: 'Bearer ' + token } : {}),
        ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    }), env);
    return { status: response.status, data: await response.json() };
  };
  try {
    return await run({ sql, DB, env, api, calls,
      time: timestamp => { clock = timestamp; },
      screen: callback => { screen = callback; },
      beforeScreen: callback => { beforeScreen = callback; },
      failScreen: value => { failScreen = value; }, failGrade: value => { failGrade = value; },
      admin: value => sql.prepare('UPDATE users SET role=? WHERE id=1').run(value ? 'admin' : 'user'),
    });
  } finally { globalThis.fetch = saved.fetch; globalThis.caches = saved.caches; Date.now = saved.now; sql.close(); }
}

function assertHeld(submission) {
  assert.equal(submission.feedback_held, true);
  assert.equal(submission.feedback_available_at, CLOSE);
  assert.equal(submission.detail, null);
  const json = JSON.stringify(submission);
  for (const privateText of ['PRIVATE_CRITERION_NOTE', 'PRIVATE_CORRECTION_FEEDBACK', 'self_reported_confidence', 'artifact_review_v1']) {
    assert.ok(!json.includes(privateText), privateText + ' must remain private');
  }
}

test('monthly details release exactly at the exclusive cutoff, with authorship audit remaining admin-only', () => {
  const problem = { week: '2026-11', closes_at: CLOSE };
  const submission = { id: 9, status: 'graded', score: 17, detail: { scores: [{ got: 17 }], feedback: ['private'], authorship: { signals: ['private audit'] } } };
  assertHeld(monthlySubmissionView(submission, problem, { timestamp: CLOSE - 1 }));
  const released = monthlySubmissionView(submission, problem, { timestamp: CLOSE });
  assert.equal(released.feedback_held, false);
  assert.deepEqual(released.detail.scores, [{ got: 17 }]);
  assert.equal(released.detail.authorship, undefined);
  assert.deepEqual(monthlySubmissionView(submission, problem, { admin: true, timestamp: NOW }).detail, submission.detail);
  const suspected = monthlySubmissionView({ status: 'ai_suspected', score: 0, detail: { authorship: {} } }, problem, { timestamp: CLOSE });
  assert.equal(suspected.score, null, 'a suspected answer never appears as a zero grade');
  assert.equal(suspected.detail, null);
  assert.equal(monthlySubmissionView(submission, { week: '2026-W45', closes_at: CLOSE }, { timestamp: NOW }), submission, 'weekly behavior is unchanged');
});

test('fresh submission and replay expose total score immediately but no correction until the deadline', async () => {
  await environment(async ({ api, sql, calls, time }) => {
    const first = await api('/problems/4/submit', { body: payload('release') });
    assert.equal(first.status, 200);
    assert.equal(first.data.status, 'graded');
    assert.ok(first.data.score > 0);
    assertHeld(first.data);
    assert.deepEqual(calls, { screen: 1, grade: 1 });
    const privateDetail = JSON.parse(sql.prepare('SELECT detail FROM submissions WHERE id=?').get(first.data.id).detail);
    assert.ok(privateDetail.scores.some(row => row.note === 'PRIVATE_CRITERION_NOTE'));
    assert.equal(privateDetail.authorship.assessment, 'uncertain');
    const replay = await api('/problems/4/submit', { body: payload('release') });
    assert.equal(replay.data.id, first.data.id);
    assertHeld(replay.data);
    assert.deepEqual(calls, { screen: 1, grade: 1 }, 'replay does not call either provider again');
    const mine = await api('/problems/4');
    assertHeld(mine.data.problem.mine[0]);
    time(CLOSE - 1);
    assertHeld((await api('/problems/4')).data.problem.mine[0]);
    time(CLOSE);
    const released = (await api('/problems/4')).data.problem.mine[0];
    assert.equal(released.feedback_held, false);
    assert.ok(released.detail.scores.some(row => row.note === 'PRIVATE_CRITERION_NOTE'));
    assert.equal(released.detail.feedback[0].note, 'PRIVATE_CORRECTION_FEEDBACK');
    assert.equal(released.detail.authorship, undefined);
    assert.equal(released.answer_sheet.parts[0].answer, equation, 'the original structured human answer remains stored');
    const replayReleased = await api('/problems/4/submit', { body: payload('release') });
    assert.equal(replayReleased.data.feedback_held, false);
    assert.ok(replayReleased.data.detail.scores);
  });
});

test('supported independent artifacts consume exactly one attempt, never invoke grading, and stay private', async () => {
  await environment(async ({ api, sql, calls, screen, admin }) => {
    screen(suspect);
    const body = payload('suspect', disclosure + '\n' + metadata);
    const response = await api('/problems/4/submit', { body });
    assert.equal(response.status, 200);
    assert.equal(response.data.status, 'ai_suspected');
    assert.equal(response.data.score, null);
    assertHeld(response.data);
    assert.equal(response.data.attempts.used, 1);
    assert.deepEqual(calls, { screen: 1, grade: 0 });
    const stored = sql.prepare('SELECT * FROM submissions WHERE id=?').get(response.data.id);
    const audit = JSON.parse(stored.detail).authorship;
    assert.equal(audit.blocked, true);
    assert.equal(audit.signals.length, 2);
    assert.equal(stored.graded_at, null);
    assert.equal(stored.score, null);
    assert.equal((await api('/problems/4/submit', { body })).data.id, response.data.id);
    assert.deepEqual(calls, { screen: 1, grade: 0 });
    assert.equal((await api('/admin/submissions/' + response.data.id)).status, 403);
    admin(true);
    const review = await api('/admin/submissions/' + response.data.id);
    assert.equal(review.status, 200);
    assert.deepEqual(review.data.submission.detail.authorship.signals, audit.signals);
    assert.equal((await api('/admin/queue')).data.subs[0].status, 'ai_suspected');
    const override = await api('/admin/submissions/' + response.data.id, { body: { score: 12, note: 'Human review resolved the suspicion.' } });
    assert.equal(override.data.score, 12);
    admin(false);
    const resolved = (await api('/problems/4')).data.problem;
    assert.equal(resolved.mine[0].status, 'graded');
    assert.equal(resolved.mine[0].score, 12);
    assert.equal(resolved.attempts.used, 1, 'manual review does not spend another student attempt');
    assertHeld(resolved.mine[0]);
    const resolvedAudit = JSON.parse(sql.prepare('SELECT detail FROM submissions WHERE id=?').get(response.data.id).detail).authorship;
    assert.equal(resolvedAudit.reviewed_by_admin, true);
  });
});

test('a duplicate request while screening is pending is not screened or graded twice', async () => {
  await environment(async ({ api, calls, beforeScreen }) => {
    let release, entered;
    const waiting = new Promise(resolve => { release = resolve; });
    const started = new Promise(resolve => { entered = resolve; });
    beforeScreen(async () => { entered(); await waiting; });
    const body = payload('pending-replay');
    const pending = api('/problems/4/submit', { body });
    await started;
    const replay = await api('/problems/4/submit', { body });
    assert.equal(replay.data.status, 'pending');
    assert.equal(replay.data.processing, true);
    assertHeld(replay.data);
    assert.deepEqual(calls, { screen: 1, grade: 0 });
    release();
    assert.equal((await pending).data.status, 'graded');
    assert.deepEqual(calls, { screen: 1, grade: 1 });
  });
});

test('unsupported or stylistic AI guesses fail open, as does an unavailable screen', async () => {
  await environment(async ({ api, calls, screen, failScreen, sql }) => {
    screen(suspect); // Its alleged quotations do not occur in this student answer.
    const unsupported = await api('/problems/4/submit', { body: payload('unsupported') });
    assert.equal(unsupported.data.status, 'graded');
    const unsupportedAudit = JSON.parse(sql.prepare('SELECT detail FROM submissions WHERE id=?').get(unsupported.data.id).detail).authorship;
    assert.equal(unsupportedAudit.assessment, 'uncertain');
    assert.equal(unsupportedAudit.signals.length, 0);
    screen(() => ({ assessment: 'ai_suspected', confidence: 1, signals: [
      { category: 'model_self_disclosure', quote: 'Apply the governing equation.', reason: 'Polished style' },
      { category: 'assistant_message_artifact', quote: equation, reason: 'Beautiful LaTeX' },
    ] }));
    assert.equal((await api('/problems/4/submit', { body: payload('style') })).data.status, 'graded');
    failScreen(true);
    const unavailable = await api('/problems/4/submit', { body: payload('unavailable') });
    assert.equal(unavailable.data.status, 'graded');
    assert.equal(unavailable.data.attempts.used, 3);
    assert.equal(JSON.parse(sql.prepare('SELECT detail FROM submissions WHERE id=?').get(unavailable.data.id).detail).authorship.reason, 'screen_error');
    assert.deepEqual(calls, { screen: 3, grade: 3 });
  });
});

test('client via_ocr cannot skip screening, and an administrator regrade skips it while retaining the private audit', async () => {
  await environment(async ({ api, calls, screen, admin, sql }) => {
    screen(suspect);
    const response = await api('/problems/4/submit', { body: { ...payload('forged-ocr', disclosure + '\n' + metadata), via_ocr: true } });
    assert.equal(response.data.status, 'ai_suspected');
    assert.deepEqual(calls, { screen: 1, grade: 0 });
    assert.equal(sql.prepare('SELECT via_ocr FROM submissions WHERE id=?').get(response.data.id).via_ocr, 0);
    admin(true);
    const regraded = await api('/admin/submissions/' + response.data.id, { body: { regrade: true } });
    assert.equal(regraded.status, 200);
    assert.ok(regraded.data.score > 0);
    assert.deepEqual(calls, { screen: 1, grade: 1 });
    assert.equal((await api('/admin/submissions/' + response.data.id)).data.submission.detail.authorship.reviewed_by_admin, true);
  });
});

test('photo-covered subquestions are omitted from screening, while unphotographed typed parts remain eligible', async () => {
  const normalized = { sheet: { parts: [
    { id: 'a', answer: equation, working: disclosure + '\n' + metadata },
    { id: 'b', answer: '$x=1$', working: 'Typed independent derivation.' },
  ] }, photographedPartIds: ['a'] };
  let calls = 0;
  const mixed = await assessMonthlyAuthorship({ title_en: 'A problem' }, normalized, async prompt => {
    calls++;
    assert.ok(!prompt.includes(disclosure), 'retained photograph OCR must not be used to guess authorship');
    assert.ok(prompt.includes('Typed independent derivation.'));
    return { raw: suspect(), model: 'mock' }; // Photo-only quotes cannot support a typed-text block.
  });
  assert.equal(mixed.blocked, false);
  assert.deepEqual(mixed.typed_part_ids, ['b']);
  normalized.photographedPartIds.push('b');
  const photoOnly = await assessMonthlyAuthorship({}, normalized, async () => { throw new Error('must not be called'); });
  assert.equal(photoOnly.assessment, 'not_screened');
  assert.equal(calls, 1);
});

test('a low-confidence, single-category or repeated-quote allegation never blocks a submission', async () => {
  const normalized = { sheet: { parts: [{ id: 'a', answer: equation, working: disclosure + '\n' + metadata }] } };
  const cases = [
    { ...suspect(), confidence: 0.979 },
    { ...suspect(), signals: [suspect().signals[0]] },
    { ...suspect(), signals: [suspect().signals[0], { ...suspect().signals[0], reason: 'The same allegation repeated' }] },
    { ...suspect(), signals: [{ ...suspect().signals[0], quote: disclosure + '\n' + metadata }, suspect().signals[1]] },
    { ...suspect(), confidence: '0.999' },
  ];
  for (const raw of cases) {
    const audit = await assessMonthlyAuthorship({}, normalized, async () => ({ raw, model: 'local-mock' }));
    assert.equal(audit.blocked, false);
  }
});
