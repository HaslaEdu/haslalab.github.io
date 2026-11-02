-- Private solution storage, separate from searchable question statements.
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS bank_solution_sources (
  id TEXT PRIMARY KEY,
  source_json TEXT NOT NULL CHECK(json_valid(source_json)),
  source_sha256 TEXT NOT NULL CHECK(length(source_sha256)=64),
  source_metadata_sha256 TEXT NOT NULL CHECK(length(source_metadata_sha256)=64),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bank_solutions (
  id TEXT PRIMARY KEY,
  question_id TEXT NOT NULL,
  question_source_json TEXT NOT NULL CHECK(json_valid(question_source_json)),
  question_locator TEXT NOT NULL,
  source_id TEXT NOT NULL REFERENCES bank_solution_sources(id),
  solution_locator TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('worked_solution','answer_only','hint')),
  authorship TEXT NOT NULL CHECK(authorship IN ('source_transcription','haslalab_original_draft')),
  spans_json TEXT NOT NULL CHECK(json_valid(spans_json)),
  context_json TEXT NOT NULL CHECK(json_valid(context_json)),
  metadata_sha256 TEXT NOT NULL CHECK(length(metadata_sha256)=64),
  review_status TEXT NOT NULL DEFAULT 'pending' CHECK(review_status IN ('pending','verified','rejected')),
  publication_ready INTEGER NOT NULL DEFAULT 0 CHECK(publication_ready=0),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(question_id,source_id,authorship,solution_locator)
);
CREATE INDEX IF NOT EXISTS bank_solutions_question ON bank_solutions(question_id,id);
CREATE TABLE IF NOT EXISTS bank_solution_versions (
  id TEXT PRIMARY KEY,
  solution_id TEXT NOT NULL REFERENCES bank_solutions(id),
  language TEXT NOT NULL CHECK(length(language)=2 AND language=lower(language)),
  role TEXT NOT NULL CHECK(role IN ('original','translation')),
  text TEXT NOT NULL CHECK(length(text)>0),
  text_sha256 TEXT NOT NULL CHECK(length(text_sha256)=64),
  review_status TEXT NOT NULL DEFAULT 'pending' CHECK(review_status IN ('pending','verified','rejected')),
  active INTEGER NOT NULL CHECK(active IN (0,1)),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(solution_id,language,role,text_sha256)
);
CREATE UNIQUE INDEX IF NOT EXISTS bank_solution_current_version ON bank_solution_versions(solution_id,language) WHERE active=1;
CREATE TABLE IF NOT EXISTS bank_solution_assets (
  id TEXT PRIMARY KEY,
  solution_id TEXT NOT NULL REFERENCES bank_solutions(id),
  asset_key TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('solution_crop','figure','source_context')),
  mime_type TEXT NOT NULL,
  sha256 TEXT NOT NULL CHECK(length(sha256)=64),
  byte_length INTEGER NOT NULL CHECK(byte_length>0),
  chunk_count INTEGER NOT NULL CHECK(chunk_count>0),
  spans_json TEXT NOT NULL CHECK(json_valid(spans_json)),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(solution_id,asset_key)
);
CREATE TABLE IF NOT EXISTS bank_solution_asset_chunks (
  asset_id TEXT NOT NULL REFERENCES bank_solution_assets(id) ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL CHECK(chunk_index>=0),
  byte_length INTEGER NOT NULL CHECK(byte_length>0 AND byte_length<=32768),
  sha256 TEXT NOT NULL CHECK(length(sha256)=64),
  payload BLOB NOT NULL CHECK(length(payload)=byte_length),
  PRIMARY KEY(asset_id,chunk_index)
);
-- Optional generated-figure records. Existing source crops have no child row;
-- their original asset columns and nonempty PDF spans remain unchanged.
CREATE TABLE IF NOT EXISTS bank_solution_asset_provenance (
  asset_id TEXT PRIMARY KEY REFERENCES bank_solution_assets(id) ON DELETE CASCADE,
  provenance_json TEXT NOT NULL CHECK(json_valid(provenance_json) AND json_type(provenance_json)='object'),
  sha256 TEXT NOT NULL CHECK(length(sha256)=64)
);
CREATE TRIGGER IF NOT EXISTS bank_solution_generated_provenance_insert
BEFORE INSERT ON bank_solution_asset_provenance
WHEN NOT EXISTS (
  SELECT 1 FROM bank_solution_assets a JOIN bank_solutions s ON s.id=a.solution_id
  WHERE a.id=NEW.asset_id AND a.role='figure'
    AND s.authorship='haslalab_original_draft' AND json_type(a.spans_json)='array' AND json_array_length(a.spans_json)=0
    AND json_extract(NEW.provenance_json,'$.kind')='generated_figure'
    AND json_extract(NEW.provenance_json,'$.input_question_id')=s.question_id
)
BEGIN SELECT RAISE(ABORT,'Generated figure provenance must match an original draft and its exact question'); END;
CREATE TRIGGER IF NOT EXISTS bank_solution_generated_provenance_update
BEFORE UPDATE ON bank_solution_asset_provenance
WHEN NOT EXISTS (
  SELECT 1 FROM bank_solution_assets a JOIN bank_solutions s ON s.id=a.solution_id
  WHERE a.id=NEW.asset_id AND a.role='figure'
    AND s.authorship='haslalab_original_draft' AND json_type(a.spans_json)='array' AND json_array_length(a.spans_json)=0
    AND json_extract(NEW.provenance_json,'$.kind')='generated_figure'
    AND json_extract(NEW.provenance_json,'$.input_question_id')=s.question_id
)
BEGIN SELECT RAISE(ABORT,'Generated figure provenance must match an original draft and its exact question'); END;
