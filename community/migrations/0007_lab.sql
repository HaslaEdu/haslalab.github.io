-- HaslaLab v8: exam mode for the experiments.  A five-hour run of a year's experiments (E1 and E2 together)
-- ends with thirty minutes to photograph the answer sheets and working sheets on a phone.  Only signed-in users
-- sit it, and each start costs one exam token, counted here on the server: the balance is users.exam_tokens and
-- every change is written to lab_ledger.  The clock is the server's too (started_at), so leaving the page and
-- coming back, or opening it on another computer, carries on the same exam without spending again.  The phone reaches
-- the session through a QR code that carries a one-off upload token (only its SHA-256 is kept here); every
-- page is read by OCR, checked by the student and graded against the task's marking scheme, the way the
-- weekly written answers are.
CREATE TABLE lab_sessions (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id      INTEGER NOT NULL REFERENCES users(id),
  exam_key     TEXT NOT NULL,                     -- competition + year, 'ipho2024'
  comp         TEXT NOT NULL,                     -- 'ipho'
  year         INTEGER NOT NULL,
  tasks        TEXT NOT NULL,                     -- JSON, the experiments of the exam: ["E1","E2"]
  lang         TEXT NOT NULL DEFAULT 'ko',
  entry        TEXT,                              -- the exam page's query string, to come back to it from anywhere
  started_at   INTEGER NOT NULL,                  -- when the five hours began (server time)
  ended_at     INTEGER NOT NULL,                  -- when the experiments go dark: started_at + 5 h, or earlier if finished early
  scan_until   INTEGER NOT NULL,                  -- the end of the thirty minutes for scanning
  upload_hash  TEXT NOT NULL,                     -- SHA-256 of the phone's upload token
  status       TEXT NOT NULL,                     -- 'running' | 'scanning' | 'grading' | 'graded' | 'pending' (waits for a marking scheme or a person) | 'error'
  charged      INTEGER NOT NULL DEFAULT 0,        -- the exam token for this start has been taken
  score        REAL,
  points       REAL,
  detail       TEXT,                              -- JSON: per task, per criterion scores and comments
  created_at   INTEGER NOT NULL,
  submitted_at INTEGER,
  graded_at    INTEGER
);
CREATE INDEX lab_sessions_user   ON lab_sessions(user_id, id DESC);
CREATE INDEX lab_sessions_status ON lab_sessions(status, id);
-- one exam at a time: a second start (a double click, another tab) cannot open a second session, so it cannot spend twice
CREATE UNIQUE INDEX lab_sessions_active ON lab_sessions(user_id) WHERE status IN ('running','scanning');

ALTER TABLE users ADD COLUMN exam_tokens INTEGER NOT NULL DEFAULT 5;   -- every account starts with five exams
CREATE TABLE lab_ledger (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id     INTEGER NOT NULL,
  delta       INTEGER NOT NULL,                   -- -1 for a start, + for a grant
  reason      TEXT NOT NULL,                      -- 'start' | 'grant' | 'refund' ...
  session_id  INTEGER,
  by_user     INTEGER,                            -- the admin who granted it
  note        TEXT,
  created_at  INTEGER NOT NULL
);
CREATE INDEX lab_ledger_user ON lab_ledger(user_id, id DESC);

CREATE TABLE lab_pages (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id  INTEGER NOT NULL REFERENCES lab_sessions(id),
  no          INTEGER NOT NULL,                   -- order of arrival
  task        TEXT NOT NULL,                      -- 'E1'
  kind        TEXT NOT NULL,                      -- 'answer' (answer sheet) | 'working' (working sheet)
  mime        TEXT NOT NULL,
  data        BLOB NOT NULL,                      -- the straightened page, at most 1.9 MB
  ocr         TEXT,                               -- what OCR read
  ocr_conf    REAL,
  ocr_status  TEXT NOT NULL DEFAULT 'none',       -- 'done' | 'failed' | 'off' (no OCR key)
  text        TEXT,                               -- the text after the student checked it
  edited      INTEGER NOT NULL DEFAULT 0,         -- the student changed what OCR read
  created_at  INTEGER NOT NULL
);
CREATE INDEX lab_pages_session ON lab_pages(session_id, no);

-- marking schemes, one per experiment; private, entered by admins at #/weekly/admin
CREATE TABLE lab_rubrics (
  exam_key    TEXT NOT NULL,
  task        TEXT NOT NULL,
  points      REAL NOT NULL,                      -- full marks of the task (IPhO: 10)
  rubric      TEXT NOT NULL,                      -- [{"id","name","max","requirement","partial"}]
  reference   TEXT,                               -- the official answers and tolerances, in words
  updated_at  INTEGER NOT NULL,
  PRIMARY KEY (exam_key, task)
);
