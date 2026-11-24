CREATE TABLE IF NOT EXISTS account_signup_sources (
  user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  source TEXT NOT NULL CHECK (source IN ('lab', 'nonsul', 'unknown'))
);
