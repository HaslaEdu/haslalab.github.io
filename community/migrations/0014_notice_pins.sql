-- Also created lazily by the admin pin endpoint where D1 management access is
-- unavailable. IF NOT EXISTS keeps a later migration safe in either order.
CREATE TABLE IF NOT EXISTS notice_pins (
  post_id INTEGER PRIMARY KEY REFERENCES posts(id) ON DELETE CASCADE,
  pinned_at INTEGER NOT NULL
);
