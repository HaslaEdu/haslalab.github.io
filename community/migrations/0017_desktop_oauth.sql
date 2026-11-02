CREATE TABLE IF NOT EXISTS oauth_desktop_intents (
 intent_hash TEXT PRIMARY KEY, provider TEXT NOT NULL, challenge TEXT NOT NULL,
 callback_url TEXT NOT NULL, client_state TEXT NOT NULL, link_user INTEGER,
 created_at INTEGER NOT NULL, started_at INTEGER, code_hash TEXT UNIQUE,
 user_id INTEGER, fresh INTEGER NOT NULL DEFAULT 0, used_at INTEGER
);
