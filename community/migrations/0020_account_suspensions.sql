-- accounts suspended for an answer that instructed the grader (injection-guard.js also creates it at run time)
CREATE TABLE IF NOT EXISTS account_suspensions (
  user_id INTEGER PRIMARY KEY,
  reason TEXT NOT NULL,
  source TEXT NOT NULL,
  evidence TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  lifted_at INTEGER
);
