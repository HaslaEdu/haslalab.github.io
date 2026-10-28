-- HaslaLab v9: exam answers graded by Gemini from the page images, against the marking scheme printed in the
-- official solution, under HaslaLab's grading regulation (R1–R10, in the Worker).  A strict invigilator: what
-- cannot be read scores nothing, and the candidate cannot edit what was read — only photograph a page again.
ALTER TABLE lab_sessions ADD COLUMN sources TEXT;   -- JSON {"E1":{"sol":"IPhO_2024_S1.pdf"}}: the official solution of each experiment
ALTER TABLE lab_pages ADD COLUMN read TEXT;         -- JSON: what was read on the page (header, items, values, tables, graphs)
ALTER TABLE lab_pages ADD COLUMN legible TEXT;      -- 'good' | 'partial' | 'poor'

-- the marking scheme drawn once from an official solution PDF and kept: one per exam, experiment and file
CREATE TABLE lab_schemes (
  exam_key    TEXT NOT NULL,
  task        TEXT NOT NULL,
  source      TEXT NOT NULL,                      -- the solution file it came from
  scheme      TEXT NOT NULL,                      -- JSON {points, items:[{id, points, type, sheet, what, …}]}
  model       TEXT,
  created_at  INTEGER NOT NULL,
  PRIMARY KEY (exam_key, task, source)
);
