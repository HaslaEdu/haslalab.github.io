-- HaslaLab community — initial schema (Cloudflare D1 / SQLite)

CREATE TABLE users (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  username    TEXT NOT NULL UNIQUE COLLATE NOCASE,   -- login id, ASCII
  nickname    TEXT NOT NULL UNIQUE COLLATE NOCASE,   -- shown on posts
  pw          TEXT,                                  -- pbkdf2$iter$salt$hash; NULL once the account is closed
  role        TEXT NOT NULL DEFAULT 'user',          -- 'user' | 'admin'
  created_at  INTEGER NOT NULL,
  deleted     INTEGER NOT NULL DEFAULT 0
);

-- only a SHA-256 of the bearer token is kept, so a leaked table can't sign anyone in
CREATE TABLE sessions (
  token_hash  TEXT PRIMARY KEY,
  user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at  INTEGER NOT NULL,
  expires_at  INTEGER NOT NULL
);
CREATE INDEX sessions_user ON sessions(user_id);

CREATE TABLE posts (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  board       TEXT NOT NULL,
  user_id     INTEGER NOT NULL REFERENCES users(id),
  title       TEXT NOT NULL,
  body        TEXT NOT NULL,
  created_at  INTEGER NOT NULL,
  updated_at  INTEGER,
  views       INTEGER NOT NULL DEFAULT 0,
  n_comments  INTEGER NOT NULL DEFAULT 0,
  n_likes     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX posts_board ON posts(board, id DESC);
CREATE INDEX posts_user  ON posts(user_id);

CREATE TABLE comments (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  post_id     INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  user_id     INTEGER NOT NULL REFERENCES users(id),
  body        TEXT NOT NULL,
  created_at  INTEGER NOT NULL,
  updated_at  INTEGER
);
CREATE INDEX comments_post ON comments(post_id, id);

CREATE TABLE likes (
  post_id     INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  user_id     INTEGER NOT NULL REFERENCES users(id),
  created_at  INTEGER NOT NULL,
  PRIMARY KEY (post_id, user_id)
);

CREATE TABLE reports (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  kind        TEXT NOT NULL,            -- 'post' | 'comment'
  target_id   INTEGER NOT NULL,
  user_id     INTEGER NOT NULL REFERENCES users(id),
  reason      TEXT NOT NULL,
  created_at  INTEGER NOT NULL,
  UNIQUE (kind, target_id, user_id)
);

-- fixed-window counters for sign-up / login / posting limits
CREATE TABLE ratelimits (
  k           TEXT PRIMARY KEY,
  start       INTEGER NOT NULL,
  n           INTEGER NOT NULL
);
