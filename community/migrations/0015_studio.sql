-- No prompts, credentials or source images are persisted in the gateway.
-- Bounded provider replay results expire with the private job (24 hours).
CREATE TABLE IF NOT EXISTS studio_jobs (
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
);
CREATE INDEX IF NOT EXISTS studio_jobs_owner ON studio_jobs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS studio_jobs_created ON studio_jobs(created_at);
CREATE TABLE IF NOT EXISTS studio_provider_calls (
  job_id TEXT NOT NULL REFERENCES studio_jobs(id) ON DELETE CASCADE,
  call_key TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('responses','image_edit')),
  status TEXT NOT NULL,
  result_json TEXT,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  PRIMARY KEY(job_id, call_key)
);
CREATE TABLE IF NOT EXISTS studio_provider_chunks (
  job_id TEXT NOT NULL,
  call_key TEXT NOT NULL,
  part INTEGER NOT NULL,
  value TEXT NOT NULL,
  PRIMARY KEY(job_id, call_key, part),
  FOREIGN KEY(job_id, call_key) REFERENCES studio_provider_calls(job_id, call_key) ON DELETE CASCADE
);
