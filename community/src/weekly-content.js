// Reviewed weekly problems are bundled with the Worker. Publish only through
// its existing D1 binding; deployment needs no D1 management/import credential.
import reviewed from '../weekly/2026-W44.json' with { type: 'json' };
import { isProblemPeriod, CURRENT_MONTHLY_PERIOD, LEGACY_MONTHLY_PERIOD, MONTHLY_CLOSES_AT } from './problem-period.js';
import { retireIntroMonthlyProblems } from './monthly-answers.js';

export const PROBLEM_FIELDS = Object.freeze(['week', 'no', 'kind', 'subject', 'level', 'points',
  'title_ko', 'title_en', 'body_ko', 'body_en', 'unit', 'answer', 'rubric', 'model_ko', 'model_en',
  'source', 'opens_at', 'closes_at', 'created_at']);
const TEXT_FIELDS = ['title_ko', 'title_en', 'body_ko', 'body_en', 'model_ko', 'model_en', 'source'];
const fail = message => { throw new Error('Weekly content: ' + message); };
const nonempty = value => typeof value === 'string' && value.trim().length > 0;
const encoder = new TextEncoder();

export function validateContent(content) {
  if (!Array.isArray(content?.problems) || !content.problems.length) fail('problems must be a nonempty array');
  // The collision check binds a publication id and four values per record.
  if (content.problems.length > 24) fail('at most 24 records may be published in one batch');
  const slots = new Set();
  for (const p of content.problems) {
    const label = `${p.week} #${p.no}`;
    if (!isProblemPeriod(p.week)) fail(`${label}: invalid problem period`);
    if (!Number.isInteger(p.no) || p.no < 1) fail(`${label}: invalid number`);
    if (slots.has(label)) fail(`${label}: duplicate week/number`);
    slots.add(label);
    if (p.id !== undefined) fail(`${label}: database ids must not be supplied`);
    if (p.kind !== 'essay') fail(`${label}: expected an essay problem`);
    if (!nonempty(p.subject)) fail(`${label}: missing subject`);
    if (!Number.isInteger(p.level) || p.level < 1 || p.level > 30) fail(`${label}: invalid level`);
    if (!Number.isInteger(p.points) || p.points <= 0) fail(`${label}: invalid points`);
    for (const field of TEXT_FIELDS) if (!nonempty(p[field])) fail(`${label}: missing ${field}`);
    for (const field of ['opens_at', 'closes_at', 'created_at']) {
      if (!Number.isSafeInteger(p[field]) || p[field] <= 0) fail(`${label}: invalid ${field}`);
    }
    if (p.opens_at >= p.closes_at) fail(`${label}: opening must precede closing`);
    if (!Array.isArray(p.rubric) || !p.rubric.length) fail(`${label}: missing rubric`);
    const ids = new Set();
    let maximum = 0;
    for (const c of p.rubric) {
      if (!nonempty(c.id) || ids.has(c.id)) fail(`${label}: missing or duplicate criterion id`);
      ids.add(c.id);
      if (!nonempty(c.name) || !nonempty(c.requirement)) fail(`${label}/${c.id}: missing criterion description`);
      if (!Number.isInteger(c.max) || c.max <= 0) fail(`${label}/${c.id}: invalid maximum`);
      if (c.partial !== undefined && typeof c.partial !== 'string') fail(`${label}/${c.id}: partial must be text`);
      maximum += c.max;
    }
    if (maximum !== p.points) fail(`${label}: rubric totals ${maximum}, expected ${p.points}`);
    const bytes = PROBLEM_FIELDS.reduce((sum, field) => sum + encoder.encode(field === 'rubric'
      ? JSON.stringify(p.rubric) : String(p[field] ?? '')).length, 0);
    if (bytes > 2000000) fail(`${label}: record exceeds D1's 2 MB row limit`);
  }
  return content;
}

export const REVIEWED_WEEKLY_CONTENT = validateContent(reviewed);
export const WEEKLY_PUBLICATION_ID = '2026-W44-uploaded-physics-v1';
export const MONTHLY_PUBLICATION_ID = 'monthly-2026-11-v1';

export async function publishWeeklyContent(db, content = REVIEWED_WEEKLY_CONTENT, publicationId = WEEKLY_PUBLICATION_ID) {
  validateContent(content);
  if (!nonempty(publicationId)) fail('missing publication identity');
  await db.prepare(`CREATE TABLE IF NOT EXISTS weekly_publications (
    id TEXT PRIMARY KEY, problems INTEGER NOT NULL, created_at INTEGER NOT NULL
  )`).run();
  if (await db.prepare('SELECT id FROM weekly_publications WHERE id=?').bind(publicationId).first()) {
    return { problems: content.problems.length, inserted: 0, applied: false };
  }
  const problems = [...content.problems].sort((a, b) => a.week.localeCompare(b.week) || a.no - b.no);
  const occupied = problems.map(() => "(week=? AND no=? AND (title_ko<>? OR COALESCE(source,'')<>?))").join(' OR ');
  // The guard deliberately violates NOT NULL on a collision. D1 batch() is a
  // transaction, so that failure prevents every insert in this publication.
  const guard = db.prepare(`INSERT INTO problems(${PROBLEM_FIELDS.join(',')})
    SELECT ${PROBLEM_FIELDS.map(() => 'NULL').join(',')}
    WHERE NOT EXISTS(SELECT 1 FROM weekly_publications WHERE id=?)
    AND EXISTS(SELECT 1 FROM problems WHERE ${occupied})`)
    .bind(publicationId, ...problems.flatMap(p => [p.week, p.no, p.title_ko, p.source]));
  const inserts = problems.map(p => db.prepare(`INSERT INTO problems(${PROBLEM_FIELDS.join(',')})
    SELECT ${PROBLEM_FIELDS.map(() => '?').join(',')}
    WHERE NOT EXISTS(SELECT 1 FROM weekly_publications WHERE id=?)
    AND NOT EXISTS(SELECT 1 FROM problems WHERE week=? AND no=?)`)
    .bind(...PROBLEM_FIELDS.map(field => field === 'rubric' ? JSON.stringify(p.rubric) : p[field] ?? null), publicationId, p.week, p.no));
  const marker = db.prepare(`INSERT INTO weekly_publications(id,problems,created_at) VALUES(?,?,?)
    ON CONFLICT(id) DO NOTHING`).bind(publicationId, problems.length, Math.floor(Date.now() / 1000));
  const result = await db.batch([guard, ...inserts, marker]);
  return { problems: problems.length, inserted: result.slice(1, -1).reduce((n, item) => n + (item.meta?.changes || 0), 0),
    applied: !!result.at(-1).meta?.changes };
}

// One additive transition changes the schedule, never the problem ids, statements, rubrics,
// scores or evidence. The marker allows administrators to maintain these records afterwards.
export async function migrateMonthlyPeriod(db) {
  await db.prepare(`CREATE TABLE IF NOT EXISTS weekly_publications (
    id TEXT PRIMARY KEY, problems INTEGER NOT NULL, created_at INTEGER NOT NULL
  )`).run();
  if (await db.prepare('SELECT id FROM weekly_publications WHERE id=?').bind(MONTHLY_PUBLICATION_ID).first()) {
    return { changed: 0, applied: false };
  }
  const rows = (await db.prepare('SELECT id FROM problems WHERE week=? AND no BETWEEN 1 AND 6 ORDER BY no')
    .bind(LEGACY_MONTHLY_PERIOD).all()).results;
  const ids = rows.map(row => row.id), places = ids.map(() => '?').join(',');
  const statements = [];
  if (ids.length) {
    // A different problem already in a destination slot must abort the entire transition.
    statements.push(db.prepare(`INSERT INTO weekly_publications(id,problems,created_at)
      SELECT NULL,NULL,NULL WHERE NOT EXISTS(SELECT 1 FROM weekly_publications WHERE id=?)
      AND EXISTS(SELECT 1 FROM problems old JOIN problems target ON target.no=old.no AND target.id<>old.id
        WHERE old.id IN (${places}) AND target.week=?)`)
      .bind(MONTHLY_PUBLICATION_ID, ...ids, CURRENT_MONTHLY_PERIOD));
    statements.push(db.prepare(`UPDATE problems SET week=?,closes_at=? WHERE id IN (${places}) AND week=?
      AND NOT EXISTS(SELECT 1 FROM weekly_publications WHERE id=?)`)
      .bind(CURRENT_MONTHLY_PERIOD, MONTHLY_CLOSES_AT, ...ids, LEGACY_MONTHLY_PERIOD, MONTHLY_PUBLICATION_ID));
    statements.push(db.prepare(`UPDATE submissions SET in_week=CASE
      WHEN created_at>=(SELECT opens_at FROM problems WHERE problems.id=submissions.problem_id)
        AND created_at<? THEN 1 ELSE 0 END
      WHERE problem_id IN (${places})
        AND EXISTS(SELECT 1 FROM problems WHERE problems.id=submissions.problem_id AND week=?)
        AND NOT EXISTS(SELECT 1 FROM weekly_publications WHERE id=?)`)
      .bind(MONTHLY_CLOSES_AT, ...ids, CURRENT_MONTHLY_PERIOD, MONTHLY_PUBLICATION_ID));
  }
  statements.push(db.prepare(`INSERT INTO weekly_publications(id,problems,created_at) VALUES(?,?,?)
    ON CONFLICT(id) DO NOTHING`).bind(MONTHLY_PUBLICATION_ID, ids.length, Math.floor(Date.now() / 1000)));
  const result = await db.batch(statements);
  return { changed: ids.length ? result[1].meta?.changes || 0 : 0, applied: !!result.at(-1).meta?.changes };
}

const initialized = new WeakMap();
export function ensureWeeklyContent(db, cacheKey = db) {
  let promise = initialized.get(cacheKey);
  if (!promise) {
    promise = publishWeeklyContent(db).then(async publication => ({ ...publication,
      monthly: await migrateMonthlyPeriod(db), answerSheet: await retireIntroMonthlyProblems(db, cacheKey) }));
    initialized.set(cacheKey, promise);
    promise.catch(() => { if (initialized.get(cacheKey) === promise) initialized.delete(cacheKey); });
  }
  return promise;
}
