// Additive runtime bootstrap through the existing D1 binding. Keep in sync with
// migrations/0015_studio.sql; no database management credential is required.
const schema = [
  `CREATE TABLE IF NOT EXISTS studio_jobs (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    request_key TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    mode TEXT NOT NULL CHECK(mode IN ('digitize','generate','restore')),
    subject TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    UNIQUE(user_id, request_key)
  )`,
  `CREATE INDEX IF NOT EXISTS studio_jobs_owner ON studio_jobs(user_id, created_at DESC)`,
  `CREATE INDEX IF NOT EXISTS studio_jobs_created ON studio_jobs(created_at)`,
  `CREATE TABLE IF NOT EXISTS studio_provider_calls (
    job_id TEXT NOT NULL REFERENCES studio_jobs(id) ON DELETE CASCADE,
    call_key TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('responses','image_edit')),
    status TEXT NOT NULL,
    result_json TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    PRIMARY KEY(job_id, call_key)
  )`,
  `CREATE TABLE IF NOT EXISTS studio_provider_chunks (
    job_id TEXT NOT NULL,
    call_key TEXT NOT NULL,
    part INTEGER NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY(job_id, call_key, part),
    FOREIGN KEY(job_id, call_key) REFERENCES studio_provider_calls(job_id, call_key) ON DELETE CASCADE
  )`,
];

const initializing = new WeakMap();

export function ensureStudioSchema(DB) {
  if (!DB || typeof DB.prepare !== 'function' || typeof DB.batch !== 'function') {
    return Promise.reject(new TypeError('Studio requires a D1 database binding'));
  }
  const existing = initializing.get(DB);
  if (existing) return existing;

  const pending = Promise.resolve()
    .then(() => DB.batch(schema.map(sql => DB.prepare(sql))))
    .then(results => {
      if (!Array.isArray(results) || results.length !== schema.length || results.some(result => result?.success === false)) {
        throw new Error('Studio schema initialization failed');
      }
    })
    .catch(error => {
      if (initializing.get(DB) === pending) initializing.delete(DB);
      throw error;
    });
  initializing.set(DB, pending);
  return pending;
}
