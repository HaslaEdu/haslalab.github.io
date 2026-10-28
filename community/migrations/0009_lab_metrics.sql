-- HaslaLab v10: what each grading costs, how long it takes and how right it is, and where the answer photos are kept.
-- Every AI call made for an exam is one row of lab_calls (tokens, an estimated price, time); an admin's own marks per
-- item go in lab_reviews, so the AI's marks can be compared with them; a page photo lives in R2 when the Worker has
-- an R2 bucket (r2_key), otherwise in lab_pages.data as before, and is removed when the keeping time is over
-- (LAB_KEEP_HOURS after grading; unset = kept — the test period).
CREATE TABLE lab_calls (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id  INTEGER NOT NULL,
  task        TEXT,                               -- 'E1'; null for a page read before it was filed
  page_id     INTEGER,                            -- the page read, for a reading
  step        TEXT NOT NULL,                      -- 'scheme' | 'read' | 'ocr' | 'grade'
  provider    TEXT NOT NULL,                      -- 'gemini' | 'upstage' | 'openai' …
  model       TEXT,
  in_tok      INTEGER,                            -- input tokens (images included)
  out_tok     INTEGER,                            -- output tokens, thinking included
  cached_tok  INTEGER,                            -- input tokens served from the provider's cache
  pages       INTEGER,                            -- pages billed (Upstage)
  usd         REAL,                               -- estimated price (LAB_PRICES or the built-in table)
  ms          INTEGER NOT NULL,
  ok          INTEGER NOT NULL DEFAULT 1,
  error       TEXT,
  created_at  INTEGER NOT NULL
);
CREATE INDEX lab_calls_session ON lab_calls(session_id);
CREATE INDEX lab_calls_time ON lab_calls(created_at);

-- an admin's mark for one item of one experiment of one sitting: the reference the AI is measured against
CREATE TABLE lab_reviews (
  session_id  INTEGER NOT NULL,
  task        TEXT NOT NULL,
  item_id     TEXT NOT NULL,
  ref_points  REAL NOT NULL,
  ai_points   REAL,                               -- the AI's mark when the reference was given
  max_points  REAL,
  note        TEXT,
  reviewer_id INTEGER NOT NULL,
  created_at  INTEGER NOT NULL,
  PRIMARY KEY (session_id, task, item_id)
);

ALTER TABLE lab_pages ADD COLUMN r2_key TEXT;      -- the photo in R2 (data is then empty)
ALTER TABLE lab_pages ADD COLUMN purged_at INTEGER; -- when the photo was removed after its keeping time

-- the phone's scan link: one code per sitting, never shared (looked up by its hash; struck out as 'void:…' when scanning ends)
CREATE UNIQUE INDEX lab_sessions_upload ON lab_sessions(upload_hash);
