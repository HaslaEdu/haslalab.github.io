-- HaslaLab v5: sign in with Google, Discord or NAVER (OAuth 2.0), next to the username and password

-- one row per outside account; a HaslaLab account can hold several
CREATE TABLE identities (
  provider    TEXT NOT NULL,                     -- 'google' | 'discord' | 'naver'
  sub         TEXT NOT NULL,                     -- the provider's stable user id (no e-mail is kept)
  user_id     INTEGER NOT NULL REFERENCES users(id),
  created_at  INTEGER NOT NULL,
  PRIMARY KEY (provider, sub)
);
CREATE INDEX identities_user ON identities(user_id);

-- the state of a sign-in on its way to the provider and back (10 minutes)
CREATE TABLE oauth_states (
  state       TEXT PRIMARY KEY,
  provider    TEXT NOT NULL,
  verifier    TEXT,                              -- PKCE code verifier
  return_to   TEXT NOT NULL,                     -- the page to come back to, checked against ALLOWED_ORIGINS
  link_user   INTEGER,                           -- set when a signed-in user adds this provider to the account
  created_at  INTEGER NOT NULL
);

-- one-time codes the site trades for a session token after the redirect (1 minute)
CREATE TABLE oauth_codes (
  code_hash   TEXT PRIMARY KEY,
  user_id     INTEGER NOT NULL,
  fresh       INTEGER NOT NULL DEFAULT 0,        -- the account was just created
  created_at  INTEGER NOT NULL
);
