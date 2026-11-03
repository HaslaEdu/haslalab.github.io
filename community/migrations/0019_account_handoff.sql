CREATE TABLE IF NOT EXISTS account_session_handoffs (
 code_hash TEXT PRIMARY KEY, source_session_hash TEXT NOT NULL REFERENCES sessions(token_hash) ON DELETE CASCADE,
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 source_origin TEXT NOT NULL, target_origin TEXT NOT NULL, challenge TEXT NOT NULL, state TEXT NOT NULL,
 created_at INTEGER NOT NULL, used_at INTEGER, used_session_hash TEXT
);
