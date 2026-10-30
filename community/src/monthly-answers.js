import { getMonthlyAnswerSheet } from '../../monthly-problems.mjs';

export const MONTHLY_ATTEMPT_LIMIT = 3;
export const MONTHLY_RETIREMENT_ID = 'monthly-2026-11-answer-sheets-v1';
export class MonthlyAnswerError extends Error {
  constructor(code, status = 400) { super(code); this.code = code; this.status = status; }
}
const fail = (code, status) => { throw new MonthlyAnswerError(code, status); };
const ready = new WeakMap();
const configured = new WeakMap();

export function ensureMonthlyAnswerSchema(db, key = db) {
  let promise = ready.get(key);
  if (!promise) {
    promise = db.batch([
      db.prepare(`CREATE TABLE IF NOT EXISTS monthly_answer_requests (
        user_id INTEGER NOT NULL, problem_id INTEGER NOT NULL, request_id TEXT NOT NULL,
        submission_id INTEGER UNIQUE, answer_sheet TEXT NOT NULL, answer_text TEXT NOT NULL,
        via_ocr INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL,
        PRIMARY KEY(user_id,problem_id,request_id)
      )`),
      db.prepare(`CREATE TABLE IF NOT EXISTS monthly_problem_retirements (
        problem_id INTEGER PRIMARY KEY, retired_at INTEGER NOT NULL, reason TEXT NOT NULL
      )`),
      db.prepare(`CREATE TABLE IF NOT EXISTS weekly_publications (
        id TEXT PRIMARY KEY, problems INTEGER NOT NULL, created_at INTEGER NOT NULL
      )`),
    ]).then(() => true);
    ready.set(key, promise);
    promise.catch(() => { if (ready.get(key) === promise) ready.delete(key); });
  }
  return promise;
}

export async function retireIntroMonthlyProblems(db, key = db) {
  await ensureMonthlyAnswerSchema(db, key);
  if (await db.prepare('SELECT id FROM weekly_publications WHERE id=?').bind(MONTHLY_RETIREMENT_ID).first()) return { applied: false };
  const current = (await db.prepare(`SELECT id FROM problems WHERE week='2026-11' AND
    ((id=1 AND title_ko='흔들리는 막대') OR (id=2 AND title_ko='시차와 절대 등급') OR
     (id=3 AND title_ko='쓰러지지 않는 팽이') OR id IN (4,5,6))`).all()).results;
  if (!current.length) return { applied: false };
  const timestamp = Math.floor(Date.now() / 1000);
  const result = await db.batch([
    db.prepare(`INSERT OR IGNORE INTO monthly_problem_retirements(problem_id,retired_at,reason)
      SELECT id,?,'Replaced introductory monthly problems' FROM problems
      WHERE week='2026-11' AND ((id=1 AND title_ko='흔들리는 막대') OR
        (id=2 AND title_ko='시차와 절대 등급') OR (id=3 AND title_ko='쓰러지지 않는 팽이'))
      AND NOT EXISTS(SELECT 1 FROM weekly_publications WHERE id=?)`).bind(timestamp, MONTHLY_RETIREMENT_ID),
    db.prepare(`UPDATE problems SET no=id-3 WHERE week='2026-11' AND id IN (4,5,6) AND no=id
      AND NOT EXISTS(SELECT 1 FROM weekly_publications WHERE id=?)`).bind(MONTHLY_RETIREMENT_ID),
    db.prepare(`INSERT INTO weekly_publications(id,problems,created_at) VALUES(?,?,?)
      ON CONFLICT(id) DO NOTHING`).bind(MONTHLY_RETIREMENT_ID, current.length, timestamp),
  ]);
  return { applied: !!result.at(-1).meta?.changes };
}

export function ensureMonthlyAnswerSetup(db, key = db) {
  let promise = configured.get(key);
  if (!promise) {
    promise = retireIntroMonthlyProblems(db, key);
    configured.set(key, promise);
    promise.catch(() => { if (configured.get(key) === promise) configured.delete(key); });
  }
  return promise;
}

// The known retired rows stay in the database for private history and admin review.
export const visibleMonthlySql = alias => `NOT EXISTS(SELECT 1 FROM monthly_problem_retirements mr WHERE mr.problem_id=${alias}.id)`;
export async function isMonthlyProblemRetired(db, id) {
  return !!await db.prepare('SELECT problem_id FROM monthly_problem_retirements WHERE problem_id=?').bind(id).first();
}

export function normalizeMonthlyParts(problem, body) {
  const sheet = getMonthlyAnswerSheet(problem);
  if (!sheet) return null;
  if (!Array.isArray(body.parts) || !body.parts.length || body.parts.length > sheet.parts.length) fail('bad_answer_sheet');
  if (body.sheet_version !== undefined && body.sheet_version !== sheet.version) fail('bad_answer_sheet');
  const requestId = body.request_id;
  if (typeof requestId !== 'string' || !/^[A-Za-z0-9_-]{16,100}$/.test(requestId)) fail('bad_request_id');
  const given = new Map(), known = new Set(sheet.parts.map(part => part.id));
  let length = 0, answered = 0;
  for (const part of body.parts) {
    if (!part || typeof part.id !== 'string' || !known.has(part.id) || given.has(part.id) ||
      typeof part.answer !== 'string' || typeof part.working !== 'string') fail('bad_answer_sheet');
    const answer = part.answer.replace(/\r\n?/g, '\n').trim(), working = part.working.replace(/\r\n?/g, '\n').trim();
    if (answer.length > 4000 || working.length > 16000) fail('bad_answer_sheet');
    if (!!answer !== !!working) fail('incomplete_part');
    length += answer.length + working.length;
    if (length > 60000) fail('bad_answer_sheet');
    if (answer) answered++;
    given.set(part.id, { id: part.id, answer, working });
  }
  if (!answered) fail('bad_answer');
  const parts = sheet.parts.map(part => given.get(part.id) || { id: part.id, answer: '', working: '' });
  const answerSheet = { version: sheet.version, parts };
  const answerText = parts.map(part => `[${part.id}]\nFinal answer:\n${part.answer || '(not answered)'}\nWorking:\n${part.working || '(not answered)'}`).join('\n\n');
  return { requestId, sheet: answerSheet, serialized: JSON.stringify(answerSheet), answer: answerText, viaOcr: body.via_ocr ? 1 : 0 };
}

export async function monthlyAttempts(db, problemId, userId) {
  const row = await db.prepare('SELECT COUNT(*) used FROM submissions WHERE problem_id=? AND user_id=?').bind(problemId, userId).first();
  const used = Number(row?.used || 0);
  return { limit: MONTHLY_ATTEMPT_LIMIT, used, remaining: Math.max(0, MONTHLY_ATTEMPT_LIMIT - used) };
}

const quoteKey = value => String(value ?? '').normalize('NFKC').replace(/\s+/g, ' ').trim();
// The grader sees labels and blank-slot markers for structure, but only student text
// from the matching subquestion can support its marks. A blank slot always earns zero.
export function guardMonthlyGrade(grade, problem, normalized, lang) {
  if (!grade) return grade;
  const parts = [...normalized.sheet.parts].sort((a, b) => b.id.length - a.id.length);
  const allUserText = quoteKey(parts.flatMap(part => [part.answer, part.working]).join('\n'));
  let evidenceIssue = !!grade.detail.evidenceIssue;
  const scores = grade.detail.scores.map(row => {
    const part = parts.find(part => String(row.id) === part.id || String(row.id).startsWith(part.id));
    const answered = !!(part?.answer && part?.working);
    const corpus = answered ? quoteKey(part.answer + '\n' + part.working) : '';
    const evidence = answered ? (row.evidence || []).filter(value => {
      const key = quoteKey(value); return key && corpus.includes(key);
    }) : [];
    const unsupported = row.got > 0 && (!answered || !evidence.length);
    if (unsupported) evidenceIssue = true;
    return { ...row, got: answered && evidence.length ? row.got : 0, evidence,
      decision: !answered ? 'not_met' : unsupported ? 'uncertain' : row.decision,
      note: !answered ? (lang === 'en' ? 'This subquestion was not submitted.' : '제출하지 않은 소문항입니다.') : unsupported
        ? (lang === 'en' ? 'The cited evidence was not found in this subquestion’s answer or working.' : '이 소문항의 답·풀이에서 채점 근거를 확인할 수 없습니다.') : row.note };
  });
  const feedback = (grade.detail.feedback || []).filter(item => {
    const quote = quoteKey(item.quote); return quote && allUserText.includes(quote);
  });
  return { score: Math.min(problem.points, scores.reduce((sum, row) => sum + row.got, 0)),
    detail: { ...grade.detail, scores, feedback, evidenceIssue } };
}

export async function reserveMonthlySubmission(db, problem, userId, normalized, timestamp) {
  const result = await db.batch([
    db.prepare(`INSERT INTO monthly_answer_requests(user_id,problem_id,request_id,answer_sheet,answer_text,via_ocr,created_at)
      SELECT ?,?,?,?,?,?,? WHERE (SELECT COUNT(*) FROM submissions WHERE user_id=? AND problem_id=?)<?
      AND NOT EXISTS(SELECT 1 FROM monthly_answer_requests WHERE user_id=? AND problem_id=? AND request_id=?)`)
      .bind(userId, problem.id, normalized.requestId, normalized.serialized, normalized.answer, normalized.viaOcr, timestamp,
        userId, problem.id, MONTHLY_ATTEMPT_LIMIT, userId, problem.id, normalized.requestId),
    db.prepare(`INSERT INTO submissions(problem_id,user_id,answer,via_ocr,status,score,detail,in_week,created_at,graded_at)
      SELECT problem_id,user_id,answer_text,via_ocr,'pending',NULL,NULL,?,?,NULL FROM monthly_answer_requests
      WHERE user_id=? AND problem_id=? AND request_id=? AND submission_id IS NULL`)
      .bind(timestamp < problem.closes_at ? 1 : 0, timestamp, userId, problem.id, normalized.requestId),
    db.prepare(`UPDATE monthly_answer_requests SET submission_id=(SELECT id FROM submissions
      WHERE user_id=? AND problem_id=? ORDER BY id DESC LIMIT 1)
      WHERE user_id=? AND problem_id=? AND request_id=? AND submission_id IS NULL`)
      .bind(userId, problem.id, userId, problem.id, normalized.requestId),
  ]);
  const request = await db.prepare(`SELECT r.*,s.status,s.score,s.detail,s.graded_at FROM monthly_answer_requests r
    JOIN submissions s ON s.id=r.submission_id
    WHERE r.user_id=? AND r.problem_id=? AND r.request_id=?`).bind(userId, problem.id, normalized.requestId).first();
  if (!request) fail('attempts_exhausted', 409);
  if (request.answer_sheet !== normalized.serialized || request.via_ocr !== normalized.viaOcr) fail('request_conflict', 409);
  return { created: !!result[0].meta?.changes, request };
}
