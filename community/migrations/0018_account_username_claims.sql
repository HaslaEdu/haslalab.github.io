CREATE TABLE IF NOT EXISTS account_username_claims (
 user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
 previous_username TEXT NOT NULL, chosen_username TEXT NOT NULL, claimed_at INTEGER NOT NULL
);
