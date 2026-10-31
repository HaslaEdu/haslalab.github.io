-- Durable queue outbox. IDs alone cross the Queue binding; student answers stay in D1/R2.
CREATE TABLE IF NOT EXISTS lab_jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_key TEXT NOT NULL UNIQUE,
  kind TEXT NOT NULL,
  session_id INTEGER NOT NULL REFERENCES lab_sessions(id) ON DELETE CASCADE,
  page_id INTEGER,
  task TEXT,
  lang TEXT NOT NULL DEFAULT 'ko',
  status TEXT NOT NULL DEFAULT 'pending',
  attempts INTEGER NOT NULL DEFAULT 0,
  available_at INTEGER NOT NULL,
  dispatched_at INTEGER,
  lease_until INTEGER,
  lease_token TEXT,
  result TEXT,
  error TEXT,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS lab_jobs_due ON lab_jobs(status, available_at);
CREATE INDEX IF NOT EXISTS lab_jobs_session ON lab_jobs(session_id, id);
