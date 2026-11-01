-- Private, standalone question bank. Apply only to its separate database.
-- Original files and crops belong in a private object store, never public Git assets.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS book_sources (
  id TEXT PRIMARY KEY,
  drive_id TEXT NOT NULL,
  revision TEXT NOT NULL,
  title TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  sha256 TEXT NOT NULL CHECK(length(sha256)=64),
  page_count INTEGER NOT NULL CHECK(page_count>0),
  subjects_json TEXT NOT NULL CHECK(json_valid(subjects_json)),
  level TEXT NOT NULL,
  source_language TEXT NOT NULL,
  private_object_key TEXT,
  local_path TEXT,
  expected_question_count INTEGER CHECK(expected_question_count>0),
  extraction_complete INTEGER NOT NULL DEFAULT 0 CHECK(extraction_complete IN (0,1)),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(drive_id,revision),
  CHECK(extraction_complete=0 OR expected_question_count IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS book_sources_shortest ON book_sources(page_count,id);
CREATE INDEX IF NOT EXISTS book_sources_content_hash ON book_sources(sha256);

CREATE TABLE IF NOT EXISTS bank_questions (
  id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES book_sources(id),
  locator TEXT NOT NULL,
  original_number TEXT NOT NULL,
  chapter TEXT,
  kind TEXT NOT NULL CHECK(kind IN ('exercise','example','problem')),
  subjects_json TEXT NOT NULL CHECK(json_valid(subjects_json)),
  level TEXT NOT NULL,
  spans_json TEXT NOT NULL CHECK(json_valid(spans_json)),
  review_status TEXT NOT NULL DEFAULT 'pending' CHECK(review_status IN ('pending','verified','rejected')),
  metadata_hash TEXT NOT NULL CHECK(length(metadata_hash)=64),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(source_id,locator)
);
CREATE INDEX IF NOT EXISTS bank_questions_source ON bank_questions(source_id,id);

CREATE TABLE IF NOT EXISTS bank_question_context (
  question_id TEXT PRIMARY KEY REFERENCES bank_questions(id),
  source_language TEXT NOT NULL,
  context_json TEXT NOT NULL CHECK(json_valid(context_json)),
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bank_question_versions (
  id TEXT PRIMARY KEY,
  question_id TEXT NOT NULL REFERENCES bank_questions(id),
  language TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('original','translation')),
  text TEXT NOT NULL CHECK(length(text)>0),
  text_sha256 TEXT NOT NULL CHECK(length(text_sha256)=64),
  review_status TEXT NOT NULL DEFAULT 'pending' CHECK(review_status IN ('pending','verified','rejected')),
  active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(question_id,language,text_sha256)
);
CREATE UNIQUE INDEX IF NOT EXISTS bank_versions_current ON bank_question_versions(question_id,language) WHERE active=1;
CREATE INDEX IF NOT EXISTS bank_versions_hash ON bank_question_versions(text_sha256);

CREATE TABLE IF NOT EXISTS bank_assets (
  id TEXT PRIMARY KEY,
  question_id TEXT NOT NULL REFERENCES bank_questions(id),
  asset_id TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('figure','question_crop')),
  private_object_key TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  sha256 TEXT NOT NULL CHECK(length(sha256)=64),
  spans_json TEXT NOT NULL CHECK(json_valid(spans_json)),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(question_id,asset_id)
);
CREATE INDEX IF NOT EXISTS bank_assets_hash ON bank_assets(sha256);

-- Optional small, private crops when no private object bucket is connected.
-- 32 KiB export chunks stay comfortably below D1's SQL-statement size limit;
-- the schema permits chunks up to 256 KiB for future prepared-statement writes.
CREATE TABLE IF NOT EXISTS bank_asset_payloads (
  asset_id TEXT PRIMARY KEY REFERENCES bank_assets(id),
  byte_length INTEGER NOT NULL CHECK(byte_length>0),
  sha256 TEXT NOT NULL CHECK(length(sha256)=64),
  chunk_count INTEGER NOT NULL CHECK(chunk_count>0)
);
CREATE TABLE IF NOT EXISTS bank_asset_chunks (
  asset_id TEXT NOT NULL REFERENCES bank_assets(id),
  chunk_index INTEGER NOT NULL CHECK(chunk_index>=0),
  byte_length INTEGER NOT NULL CHECK(byte_length>0 AND byte_length<=262144),
  sha256 TEXT NOT NULL CHECK(length(sha256)=64),
  payload BLOB NOT NULL CHECK(length(payload)=byte_length),
  PRIMARY KEY(asset_id,chunk_index)
);

CREATE TABLE IF NOT EXISTS bank_jobs (
  id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL REFERENCES book_sources(id),
  question_id TEXT REFERENCES bank_questions(id),
  stage TEXT NOT NULL CHECK(stage IN ('extract','translate_ko','translate_en','review')),
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','running','done','failed','blocked')),
  input_hash TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0 CHECK(attempts>=0),
  lease_token TEXT,
  lease_until TEXT,
  last_error TEXT,
  input_tokens INTEGER NOT NULL DEFAULT 0 CHECK(input_tokens>=0),
  output_tokens INTEGER NOT NULL DEFAULT 0 CHECK(output_tokens>=0),
  actual_usd REAL NOT NULL DEFAULT 0 CHECK(actual_usd>=0),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS bank_jobs_due ON bank_jobs(status,stage,source_id);

-- A source is ready only when extraction is declared complete, its exact question
-- count agrees, and every question and both current language versions are verified.
DROP VIEW IF EXISTS bank_source_readiness;
CREATE VIEW bank_source_readiness AS
SELECT s.id,s.title,s.page_count,s.expected_question_count,s.extraction_complete,
  (SELECT COUNT(*) FROM bank_questions q WHERE q.source_id=s.id) AS stored_questions,
  (SELECT COUNT(*) FROM bank_questions q WHERE q.source_id=s.id AND q.review_status='verified'
    AND NOT EXISTS(SELECT 1 FROM bank_question_context c WHERE c.question_id=q.id AND json_extract(c.context_json,'$.unresolved_source')=1)
    AND EXISTS(SELECT 1 FROM bank_question_versions v WHERE v.question_id=q.id AND v.language='ko' AND v.active=1 AND v.review_status='verified')
    AND EXISTS(SELECT 1 FROM bank_question_versions v WHERE v.question_id=q.id AND v.language='en' AND v.active=1 AND v.review_status='verified')) AS bilingual_verified_questions,
  CASE WHEN s.extraction_complete=1 AND s.expected_question_count=(SELECT COUNT(*) FROM bank_questions q WHERE q.source_id=s.id)
    AND NOT EXISTS(SELECT 1 FROM bank_questions q WHERE q.source_id=s.id AND (q.review_status!='verified'
      OR EXISTS(SELECT 1 FROM bank_question_context c WHERE c.question_id=q.id AND json_extract(c.context_json,'$.unresolved_source')=1)
      OR NOT EXISTS(SELECT 1 FROM bank_question_versions v WHERE v.question_id=q.id AND v.language='ko' AND v.active=1 AND v.review_status='verified')
      OR NOT EXISTS(SELECT 1 FROM bank_question_versions v WHERE v.question_id=q.id AND v.language='en' AND v.active=1 AND v.review_status='verified')))
    THEN 1 ELSE 0 END AS ready
FROM book_sources s;
