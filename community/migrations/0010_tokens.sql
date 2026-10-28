-- HaslaLab v11: exam tokens can be bought (Toss Payments) or earned a third at a time by watching a rewarded video ad.
-- Every token that comes in is a row of lab_ledger as before ('purchase', 'ad', 'cancel' for a refunded purchase).
ALTER TABLE users ADD COLUMN token_parts INTEGER NOT NULL DEFAULT 0;   -- thirds of a token from ads (0–2; three make a token)

-- one row per purchase: written before the payment window opens, so the amount cannot be changed on the way
CREATE TABLE pay_orders (
  order_id     TEXT PRIMARY KEY,                -- HL… (time in base 36 + random), sent to Toss as orderId
  user_id      INTEGER NOT NULL,
  pack         TEXT NOT NULL,                   -- which pack (PAY_PACKS)
  tokens       INTEGER NOT NULL,
  amount       INTEGER NOT NULL,                -- KRW
  status       TEXT NOT NULL DEFAULT 'ready',   -- 'ready' | 'done' | 'failed' | 'canceled'
  credited     INTEGER NOT NULL DEFAULT 0,      -- the tokens were added (once)
  payment_key  TEXT,
  method       TEXT,
  receipt_url  TEXT,
  error        TEXT,
  created_at   INTEGER NOT NULL,
  approved_at  INTEGER,
  canceled_at  INTEGER
);
CREATE INDEX pay_orders_user ON pay_orders(user_id, created_at);

-- one row per rewarded ad started; granted once, a few a day
CREATE TABLE ad_views (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id      INTEGER NOT NULL,
  nonce_hash   TEXT NOT NULL UNIQUE,
  claim        TEXT,                            -- the request that granted it (a second claim changes nothing)
  started_at   INTEGER NOT NULL,
  granted_at   INTEGER
);
CREATE INDEX ad_views_user ON ad_views(user_id, granted_at);
