/* Durable D1 outbox + Cloudflare Queue delivery. Messages carry IDs, never answer text or images. */
export const LAB_JOB_SCHEMA = [
  `CREATE TABLE IF NOT EXISTS lab_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, job_key TEXT NOT NULL UNIQUE, kind TEXT NOT NULL,
    session_id INTEGER NOT NULL REFERENCES lab_sessions(id) ON DELETE CASCADE, page_id INTEGER, task TEXT, lang TEXT NOT NULL DEFAULT 'ko',
    status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0, available_at INTEGER NOT NULL,
    dispatched_at INTEGER, lease_until INTEGER, lease_token TEXT, result TEXT, error TEXT,
    created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
  )`,
  `CREATE INDEX IF NOT EXISTS lab_jobs_due ON lab_jobs(status,available_at)`,
  `CREATE INDEX IF NOT EXISTS lab_jobs_session ON lab_jobs(session_id,id)`,
];
const ready = new WeakMap(), clock = () => Math.floor(Date.now() / 1000);
const MAX_ATTEMPTS = 4, LEASE_SECONDS = 720;
export class LabJobDeferred extends Error {
  constructor(seconds = 20) { super('job_waiting'); this.seconds = Math.max(1, Math.min(600, seconds)); }
}
export async function ensureLabJobs(env) {
  const key = env.LAB_JOBS || env.DB;
  if (!ready.has(key)) ready.set(key, (async()=>{
    await env.DB.prepare(LAB_JOB_SCHEMA[0]).run();
    await env.DB.batch(LAB_JOB_SCHEMA.slice(1).map(sql=>env.DB.prepare(sql)));
  })().catch(e => { ready.delete(key); throw e; }));
  await ready.get(key);
}
export function hasLabQueue(env) { return !!(env.LAB_JOBS && typeof env.LAB_JOBS.sendBatch === 'function'); }
export async function requireLabQueue(env) {
  if (!hasLabQueue(env)) throw Object.assign(new Error('jobs_unavailable'), { code: 'jobs_unavailable', status: 503 });
  await ensureLabJobs(env);
}
export async function enqueueLabJobs(env, jobs, { retryFailed = false,leadingStatements=[],admission } = {}) {
  await requireLabQueue(env);
  if (!jobs.length) return [];
  const at = clock();
  await env.DB.batch([...leadingStatements,...jobs.flatMap(j => [
    env.DB.prepare(`INSERT OR IGNORE INTO lab_jobs(job_key,kind,session_id,page_id,task,lang,status,available_at,created_at,updated_at)
      SELECT ?,?,?,?,?,?,'pending',?,?,?${admission?' WHERE '+admission.sql:''}`).bind(j.key, j.kind, j.sessionId, j.pageId || null, j.task || null, j.lang === 'en' ? 'en' : 'ko', at, at, at,...(admission?.args||[])),
    ...(retryFailed ? [env.DB.prepare(`UPDATE lab_jobs SET status='pending',attempts=0,available_at=?,error=NULL,lease_until=NULL,lease_token=NULL,updated_at=?
      WHERE job_key=? AND status='failed'`).bind(at, at, j.key)] : []),
  ])]);
  const rows = (await env.DB.prepare(`SELECT * FROM lab_jobs WHERE job_key IN (${jobs.map(() => '?').join(',')})`).bind(...jobs.map(j => j.key)).all()).results;
  // A failed broker call does not lose accepted work: the durable outbox is retried by the cron consumer.
  await dispatchLabJobs(env, rows).catch(e => console.error('lab job dispatch', String(e?.code || 'queue_unavailable')));
  return rows;
}
export async function dispatchLabJobs(env, given) {
  if (!hasLabQueue(env)) return 0;
  await ensureLabJobs(env);
  const at = clock(), rows = given || (await env.DB.prepare(`SELECT * FROM lab_jobs WHERE
    (status='pending' AND available_at<=?) OR (status='queued' AND dispatched_at<?) OR (status='running' AND lease_until<?)
    ORDER BY id LIMIT 50`).bind(at, at - 120, at).all()).results;
  if(!rows.length)return 0;
  const changed=await env.DB.batch(rows.map(row=>env.DB.prepare(`UPDATE lab_jobs SET status='queued',dispatched_at=?,updated_at=? WHERE id=? AND available_at<=?
      AND (status='pending' OR (status='queued' AND COALESCE(dispatched_at,0)<?) OR (status='running' AND lease_until<?))`)
      .bind(at, at, row.id, at, at - 120, at)));
  const claimed=rows.filter((row,i)=>changed[i].meta.changes).map(row=>row.id);
  if (!claimed.length) return 0;
  try { await env.LAB_JOBS.sendBatch(claimed.map(jobId => ({ body: { v: 1, jobId } }))); }
  catch (e) {
    await env.DB.batch(claimed.map(id => env.DB.prepare(`UPDATE lab_jobs SET status='pending',available_at=?,updated_at=? WHERE id=? AND status='queued' AND dispatched_at=?`).bind(at + 15, at, id, at)));
    throw e;
  }
  return claimed.length;
}
const leaseCheck = `EXISTS(SELECT 1 FROM lab_jobs WHERE id=? AND status='running' AND lease_token=?)`;
export function labJobGuard(job) { return { sql: leaseCheck, args: [job.id, job.lease_token] }; }
export async function consumeLabJobs(batch, env, handlers) {
  await requireLabQueue(env);
  for (const message of batch.messages) {
    const id = message.body?.v === 1 ? Number(message.body.jobId) : NaN;
    if (!Number.isSafeInteger(id) || id <= 0) { message.ack(); continue; }
    let row = await env.DB.prepare('SELECT * FROM lab_jobs WHERE id=?').bind(id).first();
    if (!row || ['done', 'failed'].includes(row.status)) { if(row&&handlers.after)await handlers.after(env,row);message.ack(); continue; }
    const at = clock(), token = crypto.randomUUID();
    const claim = await env.DB.prepare(`UPDATE lab_jobs SET status='running',attempts=attempts+1,lease_token=?,lease_until=?,updated_at=?
      WHERE id=? AND available_at<=? AND (status IN ('pending','queued') OR (status='running' AND lease_until<=?))`)
      .bind(token, at + LEASE_SECONDS, at, id, at, at).run();
    if (!claim.meta.changes) {
      row = await env.DB.prepare('SELECT * FROM lab_jobs WHERE id=?').bind(id).first();
      if (!row || ['done', 'failed'].includes(row.status)) message.ack();
      else message.retry({ delaySeconds: Math.max(1, Math.min(600, (row.status === 'running' ? row.lease_until : row.available_at) - at || 20)) });
      continue;
    }
    row = { ...row, status: 'running', attempts: row.attempts + 1, lease_token: token };
    const finish = async (result, failed = false) => {
      const statements = await handlers.statements(env, row, result, failed);
      // The domain row is the checkpoint. Do not duplicate long transcripts, images or feedback in the outbox.
      const summary=Object.fromEntries(['status','why','cancelled','score','points'].filter(k=>result?.[k]!==undefined).map(k=>[k,result[k]]));
      await env.DB.batch([...statements, env.DB.prepare(`UPDATE lab_jobs SET status=?,result=?,error=?,lease_until=NULL,lease_token=NULL,updated_at=?
        WHERE id=? AND status='running' AND lease_token=?`).bind(failed ? 'failed' : 'done', JSON.stringify(summary), failed ? String(result?.why || 'job_failed').slice(0, 100) : null, clock(), row.id, token)]);
      if (handlers.after) await handlers.after(env, row);
    };
    try {
      const result = await handlers.run({...env,LAB_JOB_DEADLINE:Date.now()+660000}, row);
      await finish(result);
      message.ack();
    } catch (e) {
      if (e instanceof LabJobDeferred) {
        await env.DB.prepare(`UPDATE lab_jobs SET status='pending',attempts=MAX(0,attempts-1),available_at=?,lease_until=NULL,lease_token=NULL,updated_at=? WHERE id=? AND lease_token=?`)
          .bind(clock() + e.seconds, clock(), id, token).run();
        // A dependency wait is not a failed attempt. A fresh delayed delivery preserves the broker retry budget.
        try { await env.LAB_JOBS.sendBatch([{body:{v:1,jobId:id},delaySeconds:e.seconds}]);message.ack(); }
        catch { message.retry({delaySeconds:e.seconds}); }
        continue;
      }
      const why = String(e?.code || e?.message || 'job_failed').slice(0, 100);
      console.error('lab job', row.kind, row.id, why);
      if (e?.retryable === false || row.attempts >= MAX_ATTEMPTS) {
        await finish(await handlers.failure(env, row, why, e), true);
        message.ack();
      } else {
        const delaySeconds = Math.min(300, 15 * 2 ** (row.attempts - 1));
        await env.DB.prepare(`UPDATE lab_jobs SET status='pending',available_at=?,error=?,lease_until=NULL,lease_token=NULL,updated_at=? WHERE id=? AND lease_token=?`)
          .bind(clock() + delaySeconds, why, clock(), id, token).run();
        message.retry({ delaySeconds });
      }
    }
  }
}
