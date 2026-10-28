-- HaslaLab v6: profile pictures and 1–30 problem levels.  The picture is kept under a random key so its
-- address says nothing about the account; a new upload gets a new key, so the
-- old address can be cached for good.
ALTER TABLE users ADD COLUMN avatar TEXT;                -- key of the current picture, NULL for the letter avatar
CREATE TABLE avatars (
  k           TEXT PRIMARY KEY,
  user_id     INTEGER NOT NULL,
  mime        TEXT NOT NULL,                             -- image/webp | image/jpeg | image/png
  data        BLOB NOT NULL,                             -- at most 64 KB; the site shrinks it to 256 px first
  created_at  INTEGER NOT NULL
);
CREATE INDEX avatars_user ON avatars(user_id);

-- problem levels move from 1–5 stars to the 1–30 scale (Bronze V … Ruby I): each star becomes the middle of its tier
UPDATE problems SET level = (level - 1) * 5 + 3 WHERE level BETWEEN 1 AND 6;
