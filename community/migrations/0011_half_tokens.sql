-- HaslaLab v15: a year's experiments and theory are graded as a set for one token — or each on its own for half a
-- token.  A half paid from a whole token leaves the other half here (0 or 1), and the next half-priced grading uses it.
ALTER TABLE users ADD COLUMN exam_half INTEGER NOT NULL DEFAULT 0;
