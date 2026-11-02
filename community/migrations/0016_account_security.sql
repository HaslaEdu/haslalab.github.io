-- Verified recovery addresses. Existing accounts have no inferred email address.
CREATE TABLE IF NOT EXISTS account_emails (
  user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  email TEXT NOT NULL UNIQUE COLLATE NOCASE,
  verified_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS account_email_tokens (
  token_hash TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  purpose TEXT NOT NULL CHECK(purpose IN ('verify','reset')),
  email TEXT NOT NULL,
  password_stamp TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL,
  used_at INTEGER
);
CREATE INDEX IF NOT EXISTS account_email_tokens_user ON account_email_tokens(user_id,purpose,created_at);
CREATE INDEX IF NOT EXISTS account_email_tokens_expiry ON account_email_tokens(expires_at);
