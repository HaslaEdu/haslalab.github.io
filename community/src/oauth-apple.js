/*
 * Sign in with Apple for the shared Hasla account (index.js OAUTH.apple).
 *
 * App Store Review Guideline 4.8: an iOS app that offers Google/Kakao/NAVER sign-in must also offer an equivalent
 * privacy-preserving one; Sign in with Apple is that option for the Hasla Nonsul app (haslaedu-web mobile/).
 *
 * How it differs from the other providers:
 * - No scope is asked for (no name, no e-mail), so Apple returns to the GET callback (response_mode=query) like the
 *   others and the account gets a free nickname. Nothing but Apple's stable user id (`sub`) is kept.
 * - The client secret is a short-lived ES256 JWT signed with the .p8 key from Apple Developer, made per request.
 * - There is no user-info endpoint: the user id comes from the id_token in Apple's token response. That response
 *   comes straight from appleid.apple.com over TLS in exchange for our secret, so its issuer, audience and expiry are
 *   checked but its signature is not re-verified (OpenID Connect Core 3.1.3.7, token endpoint responses).
 * - Account deletion revokes the member's Apple tokens (Guideline 5.1.1(v)): the refresh token from sign-in is kept
 *   in apple_tokens only for that, and dropped with the account.
 *
 * Worker secrets (set by the operator, never in the repository):
 *   APPLE_CLIENT_ID   the Services ID (e.g. kr.haslaedu.signin), with the return URL
 *                     https://haslaedu.kr/api/oauth/apple/callback registered for it
 *   APPLE_TEAM_ID     10-character Team ID
 *   APPLE_KEY_ID      Key ID of the "Sign in with Apple" key
 *   APPLE_PRIVATE_KEY contents of that AuthKey_<KEY_ID>.p8 (PEM, newlines kept or written as \n)
 * Without all four the provider is simply not offered (oauthProviders).
 */
const ISSUER = 'https://appleid.apple.com';
export const APPLE = {
  auth: 'https://appleid.apple.com/auth/authorize', token: 'https://appleid.apple.com/auth/token',
  revoke: 'https://appleid.apple.com/auth/revoke', me: null, scope: '', pkce: false,
};
const b64u = bytes => btoa(String.fromCharCode(...new Uint8Array(bytes))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const b64uJson = value => b64u(new TextEncoder().encode(JSON.stringify(value)));

export function appleConfigured(env) {
  return !!(env && env.APPLE_CLIENT_ID && /^[A-Z0-9]{10}$/.test(String(env.APPLE_TEAM_ID || ''))
    && /^[A-Z0-9]{10}$/.test(String(env.APPLE_KEY_ID || '')) && /BEGIN PRIVATE KEY/.test(String(env.APPLE_PRIVATE_KEY || '')));
}

const keyCache = new Map();
async function signingKey(pem) {
  let key = keyCache.get(pem);
  if (!key) {
    const body = String(pem).replace(/\\n/g, '\n').replace(/-----(BEGIN|END) PRIVATE KEY-----/g, '').replace(/\s+/g, '');
    const der = Uint8Array.from(atob(body), c => c.charCodeAt(0));
    key = crypto.subtle.importKey('pkcs8', der, {name: 'ECDSA', namedCurve: 'P-256'}, false, ['sign']);
    keyCache.set(pem, key);
    key.catch(() => keyCache.delete(pem));
  }
  return key;
}

/** The client_secret JWT Apple's token and revoke endpoints ask for (valid 5 minutes; Apple allows up to 6 months). */
export async function appleClientSecret(env, nowSec = Math.floor(Date.now() / 1000)) {
  if (!appleConfigured(env)) throw Object.assign(new Error('apple_not_configured'), {code: 'apple_off'});
  const header = {alg: 'ES256', kid: String(env.APPLE_KEY_ID)};
  const payload = {iss: String(env.APPLE_TEAM_ID), iat: nowSec, exp: nowSec + 300, aud: ISSUER, sub: String(env.APPLE_CLIENT_ID)};
  const input = b64uJson(header) + '.' + b64uJson(payload);
  // WebCrypto ECDSA signatures are already the raw r||s form JWS ES256 uses.
  const sig = await crypto.subtle.sign({name: 'ECDSA', hash: 'SHA-256'}, await signingKey(env.APPLE_PRIVATE_KEY), new TextEncoder().encode(input));
  return input + '.' + b64u(sig);
}

/** Apple's user id from the token response's id_token, or null when it is not a current token for our Services ID. */
export function appleSubject(idToken, clientId, nowSec = Math.floor(Date.now() / 1000)) {
  const parts = String(idToken || '').split('.');
  if (parts.length !== 3) return null;
  let claims;
  try { claims = JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')), c => c.charCodeAt(0)))); }
  catch { return null; }
  const aud = Array.isArray(claims.aud) ? claims.aud : [claims.aud];
  if (claims.iss !== ISSUER || !aud.includes(String(clientId)) || !(Number(claims.exp) > nowSec - 60)) return null;
  const sub = String(claims.sub || '');
  return /^[A-Za-z0-9._-]{1,255}$/.test(sub) ? sub : null;
}

/* The one refresh token per Apple user, kept only to revoke it when the account is deleted. Made on first use. */
const tableReady = new WeakMap();
export function ensureAppleTokens(db) {
  let ready = tableReady.get(db);
  if (!ready) {
    ready = db.prepare('CREATE TABLE IF NOT EXISTS apple_tokens(sub TEXT PRIMARY KEY, user_id INTEGER NOT NULL, refresh_token TEXT NOT NULL, updated_at INTEGER NOT NULL)').run()
      .then(() => db.prepare('CREATE INDEX IF NOT EXISTS apple_tokens_user ON apple_tokens(user_id)').run())
      .catch(error => { tableReady.delete(db); throw error; });
    tableReady.set(db, ready);
  }
  return ready;
}
export async function keepAppleToken(db, sub, userId, refreshToken, nowSec = Math.floor(Date.now() / 1000)) {
  if (!refreshToken || typeof refreshToken !== 'string' || refreshToken.length > 2048) return;
  await ensureAppleTokens(db);
  await db.prepare('INSERT INTO apple_tokens(sub,user_id,refresh_token,updated_at) VALUES(?,?,?,?) ON CONFLICT(sub) DO UPDATE SET user_id=excluded.user_id,refresh_token=excluded.refresh_token,updated_at=excluded.updated_at')
    .bind(sub, userId, refreshToken, nowSec).run();
}

/**
 * Revokes and forgets every Apple token of a member (account deletion, or unlinking Apple). Apple failing to answer
 * does not stop the deletion: the row is still dropped and the failure is logged without the token.
 */
export async function revokeAppleTokens(env, userId, fetcher = fetch, mockBase = env?.OAUTH_MOCK_BASE) {
  await ensureAppleTokens(env.DB);
  const rows = (await env.DB.prepare('SELECT sub,refresh_token FROM apple_tokens WHERE user_id=?').bind(userId).all()).results || [];
  let revoked = 0;
  for (const row of rows) {
    try {
      if (!appleConfigured(env)) throw new Error('apple_not_configured');
      const form = new URLSearchParams({client_id: String(env.APPLE_CLIENT_ID), client_secret: await appleClientSecret(env), token: row.refresh_token, token_type_hint: 'refresh_token'});
      const url = mockBase ? mockBase + new URL(APPLE.revoke).pathname : APPLE.revoke;
      const response = await fetcher(url, {method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'}, body: form});
      if (response.ok) revoked++; else console.error('apple revoke', response.status);
    } catch (error) { console.error('apple revoke', String(error && error.message || error).slice(0, 80)); }
  }
  await env.DB.prepare('DELETE FROM apple_tokens WHERE user_id=?').bind(userId).run();
  return {tokens: rows.length, revoked};
}
