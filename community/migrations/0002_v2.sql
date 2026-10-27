-- HaslaLab community v2: post tags (말머리), down-votes, threaded replies

ALTER TABLE posts ADD COLUMN tag TEXT NOT NULL DEFAULT 'gen';
ALTER TABLE posts ADD COLUMN n_dislikes INTEGER NOT NULL DEFAULT 0;
ALTER TABLE comments ADD COLUMN parent_id INTEGER;

CREATE TABLE dislikes (
  post_id     INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  user_id     INTEGER NOT NULL REFERENCES users(id),
  created_at  INTEGER NOT NULL,
  PRIMARY KEY (post_id, user_id)
);

CREATE INDEX posts_score ON posts(n_likes DESC, id DESC);
CREATE INDEX posts_tag   ON posts(tag, id DESC);
CREATE INDEX comments_parent ON comments(parent_id);
