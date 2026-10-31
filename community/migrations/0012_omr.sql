CREATE TABLE IF NOT EXISTS omr_attempts (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 client_id TEXT NOT NULL,
 exam_key TEXT NOT NULL,
 policy_version TEXT NOT NULL,
 answers TEXT NOT NULL,
 score TEXT NOT NULL,
 comparison_score REAL NOT NULL,
 created_at INTEGER NOT NULL,
 UNIQUE(user_id,client_id)
);
CREATE INDEX IF NOT EXISTS omr_cohort ON omr_attempts(exam_key,policy_version,user_id,id);
