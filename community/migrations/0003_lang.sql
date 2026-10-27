-- HaslaLab community v3: a Korean and an English server sharing accounts

ALTER TABLE posts ADD COLUMN lang TEXT NOT NULL DEFAULT 'ko';
CREATE INDEX posts_lang ON posts(lang, board, id DESC);
