import { OMR_CATALOG } from './omr-catalog.js';
import { OMR_SCHEMA } from './omr-schema.js';

let schemaReady=false;
export async function ensureOmrSchema(env){
  if(schemaReady)return;
  // Each request owns its D1 I/O. Concurrent cold requests can safely repeat
  // these idempotent statements without sharing another request's promise.
  await env.DB.batch(OMR_SCHEMA.map(sql=>env.DB.prepare(sql)));
  schemaReady=true;
}

const round = x => Math.round((x + Number.EPSILON) * 1e8) / 1e8;
const hasVerifiedWeights = exam => exam.policy?.verified === true && Array.isArray(exam.policy.points)
  && exam.policy.points.length === exam.key.length && exam.policy.points.every(v => Number.isFinite(v) && v > 0);
export function scoreOmr(exam, answers) {
  if (!Array.isArray(answers) || answers.length !== exam.key.length || answers.some(a => a !== null && (!Number.isInteger(a) || a < 1 || a > 5))) throw Error('invalid_answers');
  const p = exam.policy || {}, official = hasVerifiedWeights(exam);
  let correct = 0, wrong = 0, blank = 0, raw = 0, deduction = 0, max = 0;
  const fields = {};
  const rows = answers.map((answer, i) => {
    const full = (exam.fullCredit || []).includes(i + 1), key = exam.key[i];
    const good = full || (answer !== null && (Array.isArray(key) ? key.includes(answer) : key === answer));
    const status = good ? 'correct' : answer === null ? 'blank' : 'wrong';
    if (good) correct++; else if (answer === null) blank++; else wrong++;
    const points = official ? p.points[i] : 1, earned = good ? points : 0, penalty = status === 'wrong' ? points * exam.penaltyRate : 0;
    raw += earned; deduction += penalty; max += points;
    if (official && p.fields && p.fields[i]) {
      const f = fields[p.fields[i]] ||= {raw:0, penalty:0, maximum:0};
      f.raw += earned; f.penalty += penalty; f.maximum += points;
    }
    return {number:i + 1, answer, accepted:key, fullCredit:full, status, points:official ? points : null};
  });
  let total = raw - deduction;
  if (official && Number.isFinite(p.floor)) total = Math.max(p.floor, total);
  if (official && Number.isInteger(p.roundingDigits)) total = +total.toFixed(p.roundingDigits);
  for (const f of Object.values(fields)) { f.final = round(f.raw - f.penalty); f.raw=round(f.raw); f.penalty=round(f.penalty); }
  return {correct, wrong, blank, officialScore:official ? round(total) : null,
    rawScore:official ? round(raw) : null, penalty:official ? round(deduction) : null,
    maximum:official ? round(max) : null, fields:official ? fields : null,
    practice:{score:round(correct - exam.penaltyRate * wrong), maximum:answers.length, metric:'correct_minus_wrong_penalty', official:false},
    scoreStatus:official ? 'verified_weights' : 'official_weights_unverified', sources:p.sources || [],
    reviewQuestions:exam.reviewQuestions || [], rows};
}

export function percentileCounts(higher, equal, n) {
  if (n < 5) return {n, rank:null, upperPercent:null, ties:equal, minimumSample:5};
  return {n, rank:higher + 1, upperPercent:round(100 * (higher + equal) / n), ties:equal, minimumSample:5};
}

async function cohort(env, exam, value, userId) {
  // The first recorded attempt per account, on exactly the same paper and metric.
  // Old policy versions and deleted accounts never enter a new comparison group.
  const rows = await env.DB.prepare(`SELECT COUNT(*) n, SUM(a.comparison_score>?) higher, SUM(a.comparison_score=?) equal
    FROM omr_attempts a JOIN users u ON u.id=a.user_id AND u.deleted=0
    WHERE a.exam_key=? AND a.policy_version=? AND a.user_id<>? AND a.id=(SELECT MIN(b.id) FROM omr_attempts b
      WHERE b.user_id=a.user_id AND b.exam_key=a.exam_key AND b.policy_version=a.policy_version)`)
    .bind(value, value, exam.id, exam.version, userId).first();
  return {...percentileCounts(+rows.higher || 0, (+rows.equal || 0) + 1, (+rows.n || 0) + 1),
    metric:hasVerifiedWeights(exam) ? 'official_weighted_score' : 'practice_correct_minus_wrong_penalty',
    population:'Other accounts first attempts on this paper, level and scoring version; your current attempt replaces your previous score', includesOfficialContestants:false};
}

export function createOmrRouter({HttpError, needUser, limit, now}, catalog = OMR_CATALOG) {
  return async function omr(p, method, body, me, req, env, url) {
    if (!p.startsWith('/api/omr/')) return undefined;
    await ensureOmrSchema(env);
    if (method === 'GET' && p === '/api/omr/catalog') return {exams:Object.values(catalog).map(e=>({id:e.id,count:e.key.length,version:e.version,penaltyRate:e.penaltyRate,policy:e.policy}))};
    if (method !== 'POST' || p !== '/api/omr/attempts') throw new HttpError(404,'not_found');
    needUser(me);
    const exam = catalog[body.exam_key];
    if (!exam) throw new HttpError(400,'invalid_exam');
    if (typeof body.client_id !== 'string' || !/^[A-Za-z0-9:_-]{8,90}$/.test(body.client_id)) throw new HttpError(400,'invalid_attempt_id');
    let score;
    try { score = scoreOmr(exam, body.answers); } catch { throw new HttpError(400,'invalid_answers'); }
    let row = await env.DB.prepare('SELECT * FROM omr_attempts WHERE user_id=? AND client_id=?').bind(me.id, body.client_id).first();
    if (!row) {
      await limit(env,'omr:' + me.id,30,86400);
      const comparison = score.officialScore ?? score.practice.score;
      await env.DB.prepare(`INSERT INTO omr_attempts(user_id,client_id,exam_key,policy_version,answers,score,comparison_score,created_at)
        VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(user_id,client_id) DO NOTHING`)
        .bind(me.id,body.client_id,exam.id,exam.version,JSON.stringify(body.answers),JSON.stringify(score),comparison,now()).run();
      row = await env.DB.prepare('SELECT * FROM omr_attempts WHERE user_id=? AND client_id=?').bind(me.id,body.client_id).first();
    }
    // Repeated IDs cannot change a saved answer or overwrite a first score.
    if (row.exam_key !== exam.id) throw new HttpError(409,'attempt_id_conflict');
    const savedExam = catalog[row.exam_key];
    const saved = row.policy_version === savedExam?.version ? JSON.parse(row.score) : null;
    if (!saved) throw new HttpError(409,'scoring_version_changed');
    return {attempt:{id:row.id,examKey:row.exam_key,createdAt:row.created_at,score:saved},
      cohort:await cohort(env,savedExam,row.comparison_score,me.id)};
  };
}
