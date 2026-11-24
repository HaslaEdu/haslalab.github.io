/* Workshop storage connectors (#/workshop/storage): a member links their own Google Drive or GitHub, and HaslaLab can
   reach only one place there.
   - Google Drive, scope drive.file only: Drive shows the app nothing but the files it made (or the member picked). The
     site keeps its files in a folder «HaslaLab» (found again by appProperties haslalab=root) and folders it makes inside.
   - GitHub, through a GitHub App the member installs on the repositories they choose ("Only select repositories"); each
     request uses an installation token narrowed to the one repository the member picked, and only under its folder
     (default "haslalab/"). The App asks for Contents (read & write) and Metadata (read) only.

   Routes (all need a signed-in member, except the two provider callbacks, which act only through a one-time state):
   - GET    /api/workshop/connectors                     {drive:{configured,connected,email?}, github:{configured,connected,account?,repo?,folder?,manage_url?}}
   - POST   /api/workshop/connectors/<google|github>/start   {return} → {url} to open in the browser
   - GET    /api/workshop/connectors/google/callback     Google returns here (code, state)
   - GET    /api/workshop/connectors/github/callback     GitHub returns here after the install (installation_id, code, state)
   - POST   /api/workshop/connectors/finish              {ticket} the site finishes the link as the signed-in member
   - DELETE /api/workshop/connectors/<google|github>     disconnect (Google: the token is revoked at Google)
   - Drive:  GET drive/files?folder=  POST drive/files (multipart file, folder)  GET|PATCH|DELETE drive/files/:id
             POST drive/folders {name,parent}  POST drive/copy {direction:'to_drive',file_id,folder} | {direction:'to_storage',id,folder}
   - GitHub: GET github/repos  POST github/repo {repo_id,folder}  GET github/files?path=  POST github/files (multipart file, path)
             GET github/file?path=  DELETE github/file?path=  POST github/copy {direction:'to_github',file_id,path} | {direction:'to_storage',path,folder}

   The connect flow, both providers: /start (bearer) stores a random state (only its SHA-256) bound to the member, with
   the PKCE verifier for Google; the provider sends the browser to the callback with that state (single use, 10
   minutes); the callback stores the result under a fresh one-time ticket and sends the browser back to the site's
   #/workshop/storage only (an allowed https origin); the site posts the ticket with the member's bearer token and the
   link is made only if that member is the one who started it. Google's code is kept sealed until then and traded only
   at /finish; GitHub's code is traded at the callback just to confirm (GET /user/installations) that the installation
   belongs to the GitHub user who came back, and that user token is revoked at once.
   Secrets: GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET (the sign-in client), WORKSHOP_TOKEN_KEY (base64, 32 bytes: AES-GCM
   key for the Google tokens kept in D1); GITHUB_APP_ID, GITHUB_APP_CLIENT_ID, GITHUB_APP_CLIENT_SECRET,
   GITHUB_APP_PRIVATE_KEY (PEM, PKCS#8 or PKCS#1) and the var GITHUB_APP_SLUG. Without them the connector reports
   configured:false and every route answers 503 not_configured. No token is ever logged or sent to the browser.
   Setup for the owner: community/CONNECTORS.md. */
import {driveUpload, driveMkdir, driveList, driveQuote, DRIVE_FOLDER, DRIVE_API} from './drive-backup.js';
import {WORKSHOP_TYPES, WORKSHOP_MAX_FILE, contentMatches, cleanName, workshopSaveBytes, workshopReadBytes} from './workshop-storage.js';

/* where Google and GitHub send the browser back: this Worker's own address (not the haslaedu.kr sign-in passthrough) */
export const CONNECTOR_ORIGIN = 'https://haslalab-community.haslalab.workers.dev';
export const GOOGLE_CALLBACK_PATH = '/api/workshop/connectors/google/callback';
export const GITHUB_CALLBACK_PATH = '/api/workshop/connectors/github/callback';
export function connectorOrigin(env) {
  const v = String(env?.WORKSHOP_CONNECTOR_ORIGIN || '').trim().replace(/\/+$/, '');
  try { const u = new URL(v); if (u.protocol === 'https:' && u.origin === v) return v; } catch {}
  return CONNECTOR_ORIGIN;
}
export const googleRedirectUri = env => connectorOrigin(env) + GOOGLE_CALLBACK_PATH;
export const githubRedirectUri = env => connectorOrigin(env) + GITHUB_CALLBACK_PATH;
export const DRIVE_SCOPE = 'https://www.googleapis.com/auth/drive.file';
const GOOGLE_SCOPES = ['openid', 'email', DRIVE_SCOPE];
const G_AUTH = 'https://accounts.google.com/o/oauth2/v2/auth', G_TOKEN = 'https://oauth2.googleapis.com/token',
  G_REVOKE = 'https://oauth2.googleapis.com/revoke', G_ME = 'https://openidconnect.googleapis.com/v1/userinfo';
const GH = 'https://api.github.com', GH_WEB = 'https://github.com';
const UA = 'HaslaLab (https://haslalab.org, 1.0)';
const STATE_TTL = 600, DRIVE_ROOT = 'HaslaLab', GH_DEFAULT_FOLDER = 'haslalab';
const GH_SEG = /^[\p{L}\p{N}_(][\p{L}\p{N} ._()\-]{0,79}$/u, GH_DEPTH = 8, GH_PATH_MAX = 300;
const DRIVE_ID = /^[A-Za-z0-9_-]{10,200}$/;

export const CONNECTOR_SCHEMA = [
  `CREATE TABLE IF NOT EXISTS workshop_connector_states (
     state_hash TEXT PRIMARY KEY,
     user_id INTEGER NOT NULL,
     provider TEXT NOT NULL,
     verifier TEXT,
     return_to TEXT NOT NULL,
     created_at INTEGER NOT NULL,
     called_at INTEGER,
     ticket_hash TEXT,
     code_enc TEXT,
     installation_id INTEGER,
     account TEXT,
     account_type TEXT)`,
  `CREATE INDEX IF NOT EXISTS workshop_connector_states_ticket ON workshop_connector_states(ticket_hash)`,
  `CREATE TABLE IF NOT EXISTS workshop_connectors (
     user_id INTEGER NOT NULL,
     provider TEXT NOT NULL,
     account TEXT,
     account_type TEXT,
     refresh_enc TEXT,
     access_enc TEXT,
     access_exp INTEGER,
     root_id TEXT,
     installation_id INTEGER,
     repo_id INTEGER,
     repo TEXT,
     branch TEXT,
     folder TEXT,
     created_at INTEGER NOT NULL,
     updated_at INTEGER NOT NULL,
     PRIMARY KEY (user_id, provider))`
];
const ready = new WeakSet();
export async function ensureConnectorSchema(env) {
  if (ready.has(env.DB)) return;
  for (const sql of CONNECTOR_SCHEMA) await env.DB.prepare(sql).run();
  ready.add(env.DB);
}

/* ---- small helpers ---- */
const enc = new TextEncoder(), dec = new TextDecoder();
export function b64u(buf) {
  let s = ''; const u = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode(...u.subarray(i, i + 0x8000));
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
export function unb64u(s) {
  s = String(s).replace(/-/g, '+').replace(/_/g, '/');
  const bin = atob(s + '==='.slice((s.length + 3) % 4));
  return Uint8Array.from(bin, c => c.charCodeAt(0));
}
const b64 = u => { let s = ''; for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode(...u.subarray(i, i + 0x8000)); return btoa(s); };
const fromB64 = s => Uint8Array.from(atob(String(s).replace(/\s+/g, '')), c => c.charCodeAt(0));
const sha = async s => b64u(await crypto.subtle.digest('SHA-256', enc.encode(s)));
const rand = n => b64u(crypto.getRandomValues(new Uint8Array(n)));

/* ---- tokens at rest: AES-GCM, bound to the member and the use (additional data) ----
   The key is WORKSHOP_TOKEN_KEY (base64, 32 bytes) when the owner set one ("v1." tokens); otherwise it is derived with
   HKDF-SHA256 from the existing GOOGLE_CLIENT_SECRET ("d1." tokens; owner's choice, 2026-11-24, so no new secret is needed).
   Changing the Google client secret (or adding WORKSHOP_TOKEN_KEY later) only means members link Drive again. */
const keys = new Map();
function tokenKeyBytes(env) {
  try { const k = fromB64(String(env?.WORKSHOP_TOKEN_KEY || '').trim()); return k.length === 32 ? k : null; } catch { return null; }
}
const derivable = env => String(env?.GOOGLE_CLIENT_SECRET || '').length >= 16;
async function aesKey(env, kind) {
  if (kind === 'v1') {
    const raw = String(env.WORKSHOP_TOKEN_KEY || '').trim(), id = 'v1:' + raw;
    if (!keys.has(id)) {
      const k = tokenKeyBytes(env);
      if (!k) throw Object.assign(new Error('token_key_missing'), {status: 503, code: 'not_configured'});
      keys.set(id, await crypto.subtle.importKey('raw', k, 'AES-GCM', false, ['encrypt', 'decrypt']));
    }
    return keys.get(id);
  }
  const secret = String(env.GOOGLE_CLIENT_SECRET || ''), id = 'd1:' + secret;
  if (!keys.has(id)) {
    if (!derivable(env)) throw Object.assign(new Error('token_key_missing'), {status: 503, code: 'not_configured'});
    const base = await crypto.subtle.importKey('raw', enc.encode(secret), 'HKDF', false, ['deriveKey']);
    keys.set(id, await crypto.subtle.deriveKey({name: 'HKDF', hash: 'SHA-256', salt: enc.encode('haslalab-workshop-connectors'), info: enc.encode('drive-token-key-v1')},
      base, {name: 'AES-GCM', length: 256}, false, ['encrypt', 'decrypt']));
  }
  return keys.get(id);
}
export async function sealToken(env, plain, aad) {
  const kind = tokenKeyBytes(env) ? 'v1' : 'd1';
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ct = await crypto.subtle.encrypt({name: 'AES-GCM', iv, additionalData: enc.encode(aad)}, await aesKey(env, kind), enc.encode(plain));
  return kind + '.' + b64u(iv) + '.' + b64u(ct);
}
export async function openToken(env, sealed, aad) {
  const [v, iv, ct] = String(sealed || '').split('.');
  if ((v !== 'v1' && v !== 'd1') || !iv || !ct) throw new Error('sealed_bad');
  return dec.decode(await crypto.subtle.decrypt({name: 'AES-GCM', iv: unb64u(iv), additionalData: enc.encode(aad)}, await aesKey(env, v), unb64u(ct)));
}

/* ---- configuration ---- */
export const driveConfigured = env => !!(env.GOOGLE_CLIENT_ID && env.GOOGLE_CLIENT_SECRET && (tokenKeyBytes(env) || derivable(env)));
export const githubConfigured = env => !!(env.GITHUB_APP_ID && env.GITHUB_APP_SLUG && /^[a-z0-9][a-z0-9-]{0,99}$/i.test(String(env.GITHUB_APP_SLUG))
  && env.GITHUB_APP_CLIENT_ID && env.GITHUB_APP_CLIENT_SECRET && env.GITHUB_APP_PRIVATE_KEY);

/* ---- GitHub App JWT (RS256 through WebCrypto) ---- */
const derLen = n => n < 128 ? [n] : n < 256 ? [0x81, n] : n < 65536 ? [0x82, n >> 8, n & 255] : [0x83, n >> 16, (n >> 8) & 255, n & 255];
/* GitHub hands out PKCS#1 ("BEGIN RSA PRIVATE KEY"); WebCrypto imports PKCS#8, so a PKCS#1 key is wrapped here */
export function pkcs1ToPkcs8(pkcs1) {
  const alg = [0x30, 0x0d, 0x06, 0x09, 0x2a, 0x86, 0x48, 0x86, 0xf7, 0x0d, 0x01, 0x01, 0x01, 0x05, 0x00];
  const octet = [0x04, ...derLen(pkcs1.length)];
  const inner = 3 + alg.length + octet.length + pkcs1.length;
  const head = [0x30, ...derLen(inner), 0x02, 0x01, 0x00, ...alg, ...octet];
  const out = new Uint8Array(head.length + pkcs1.length); out.set(head); out.set(pkcs1, head.length);
  return out;
}
const rsaKeys = new Map();
async function appKey(pem) {
  if (!rsaKeys.has(pem)) {
    const text = String(pem).replace(/\\n/g, '\n');
    const m = /-----BEGIN (RSA )?PRIVATE KEY-----([\s\S]+?)-----END \1?PRIVATE KEY-----/.exec(text);
    if (!m) throw Object.assign(new Error('github_key_bad'), {status: 503, code: 'not_configured'});
    let der = fromB64(m[2]);
    if (m[1]) der = pkcs1ToPkcs8(der);
    rsaKeys.set(pem, await crypto.subtle.importKey('pkcs8', der, {name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256'}, false, ['sign']));
  }
  return rsaKeys.get(pem);
}
export async function githubAppJwt(env, nowSec) {
  const head = b64u(enc.encode(JSON.stringify({alg: 'RS256', typ: 'JWT'})));
  const body = b64u(enc.encode(JSON.stringify({iat: nowSec - 60, exp: nowSec + 540, iss: String(env.GITHUB_APP_ID)})));
  const sig = await crypto.subtle.sign('RSASSA-PKCS1-v1_5', await appKey(env.GITHUB_APP_PRIVATE_KEY), enc.encode(head + '.' + body));
  return head + '.' + body + '.' + b64u(sig);
}

/* ---- GitHub paths: segments of letters, digits, space . _ - ( ); no "..", no leading "." (no .github), no leading "/" ---- */
export function cleanGhPath(v, {allowEmpty = true} = {}) {
  if (v == null) v = '';
  if (typeof v !== 'string') return null;
  let s = v.normalize('NFC').trim();
  if (s.startsWith('/') || s.includes('\\') || /[\u0000-\u001f\u007f]/.test(s)) return null;
  s = s.replace(/\/+$/, '');
  if (!s) return allowEmpty ? '' : null;
  const segs = s.split('/');
  if (segs.length > GH_DEPTH) return null;
  for (const g of segs) if (!g || g === '.' || g === '..' || !GH_SEG.test(g) || g.endsWith('.') || g.endsWith(' ')) return null;
  const p = segs.join('/');
  return p.length > GH_PATH_MAX ? null : p;
}
const joinPath = (...xs) => xs.filter(Boolean).join('/');
/* a file name for GitHub: the storage rules first, then anything outside the path alphabet becomes "_" */
export function ghFileName(name, ext) {
  let n = cleanName(name, ext).replace(/[^\p{L}\p{N} ._()\-]/gu, '_').replace(/^[.\- ]+/, '_');
  if (!GH_SEG.test(n)) n = 'file.' + ext;
  return n;
}
const extOf = name => (/\.([A-Za-z0-9]{1,5})$/.exec(String(name || ''))?.[1] || '').toLowerCase();
/* an https return address on an allowed origin (as the sign-in's allowedReturn); the fragment is set on the way back */
export function allowedReturn(env, raw) {
  let u; try { u = new URL(String(raw || '')); } catch { return null; }
  const ok = u.protocol === 'https:' && String(env.ALLOWED_ORIGINS || '').split(',').map(s => s.trim()).filter(Boolean).includes(u.origin);
  return ok ? u.origin + u.pathname : null;
}
const back = (ret, q) => new Response(null, {status: 302, headers: {Location: ret + '#/workshop/storage?' + q, 'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'}});
const plain = (status, text) => new Response(text, {status, headers: {'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer', 'X-Content-Type-Options': 'nosniff'}});
const asciiName = n => n.replace(/[^\x20-\x7e]/g, '_').replace(/[;\\"]/g, '_');
function attachment(body, name, size) {
  const ext = extOf(name), mime = WORKSHOP_TYPES[ext]?.mime || 'application/octet-stream';
  const headers = {'Content-Type': mime, 'Content-Disposition': `attachment; filename="${asciiName(name)}"; filename*=UTF-8''${encodeURIComponent(name)}`,
    'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer',
    'Content-Security-Policy': "default-src 'none'; sandbox", 'X-Frame-Options': 'DENY'};
  if (size != null) headers['Content-Length'] = String(size);
  return new Response(body, {status: 200, headers});
}

export function createWorkshopConnectorsRouter({HttpError, needUser, limit, now, bad, fetchImpl = null}) {
  const f = (...a) => (fetchImpl || globalThis.fetch)(...a);
  const fail = (status, code) => { throw new HttpError(status, code); };
  const notConfigured = () => fail(503, 'not_configured');
  const row = async (env, uid, prov) => env.DB.prepare('SELECT * FROM workshop_connectors WHERE user_id=? AND provider=?').bind(uid, prov).first();

  /* ======== Google ======== */
  const gForm = body => ({method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded', Accept: 'application/json'}, body: new URLSearchParams(body).toString()});
  async function googleRevoke(token) {
    try { await f(G_REVOKE, gForm({token})); } catch { /* best effort: the token is forgotten here either way */ }
  }
  async function driveFetch(token, url, init = {}, what = 'drive') {
    let r;
    try { r = await f(url, {...init, headers: {Authorization: 'Bearer ' + token, ...(init.headers || {})}}); }
    catch { fail(502, what + '_unreachable'); }
    if (r.status === 404) fail(404, 'not_found');
    if (r.status === 401) fail(409, 'drive_reconnect');
    if (r.status === 403 || r.status === 429) { const j = await r.json().catch(() => ({})); console.error('workshop drive', what, r.status, String(j?.error?.errors?.[0]?.reason || '').slice(0, 40)); fail(r.status === 429 ? 429 : 403, r.status === 429 ? 'rate_limited' : 'drive_forbidden'); }
    if (!r.ok) { console.error('workshop drive', what, r.status); fail(502, 'drive_failed'); }
    return r;
  }
  async function driveAccess(env, conn) {
    const uid = conn.user_id, t = now();
    if (conn.access_enc && conn.access_exp > t + 60) {
      try { return await openToken(env, conn.access_enc, 'drive-access:' + uid); } catch { /* refresh below */ }
    }
    let refresh;
    try { refresh = await openToken(env, conn.refresh_enc, 'drive-refresh:' + uid); }
    catch { await env.DB.prepare("DELETE FROM workshop_connectors WHERE user_id=? AND provider='google'").bind(uid).run(); fail(409, 'drive_reconnect'); }
    let r, j;
    try { r = await f(G_TOKEN, gForm({client_id: env.GOOGLE_CLIENT_ID, client_secret: env.GOOGLE_CLIENT_SECRET, refresh_token: refresh, grant_type: 'refresh_token'})); j = await r.json().catch(() => ({})); }
    catch { fail(502, 'drive_unreachable'); }
    if (!r.ok || !j.access_token) {
      console.error('workshop drive refresh', r.status, String(j?.error || '').slice(0, 40));
      /* the member revoked HaslaLab at Google, or the token expired: the link is gone */
      if (j?.error === 'invalid_grant') { await env.DB.prepare("DELETE FROM workshop_connectors WHERE user_id=? AND provider='google'").bind(uid).run(); fail(409, 'drive_reconnect'); }
      fail(502, 'drive_failed');
    }
    const exp = t + Math.max(60, Math.min(3600, +j.expires_in || 3600));
    await env.DB.prepare("UPDATE workshop_connectors SET access_enc=?,access_exp=?,updated_at=? WHERE user_id=? AND provider='google'")
      .bind(await sealToken(env, j.access_token, 'drive-access:' + uid), exp, t, uid).run();
    conn.access_exp = exp;
    return j.access_token;
  }
  const META = 'id,name,mimeType,size,modifiedTime,parents,trashed,appProperties';
  const driveMeta = (token, id) => driveFetch(token, `${DRIVE_API}/drive/v3/files/${encodeURIComponent(id)}?fields=${encodeURIComponent(META)}`, {}, 'meta').then(r => r.json());
  /* the «HaslaLab» folder: the one we know, else the one marked haslalab=root, else a new one */
  async function driveRoot(env, conn, token) {
    if (conn.root_id) {
      try { const m = await driveMeta(token, conn.root_id); if (!m.trashed && m.mimeType === DRIVE_FOLDER) return conn.root_id; }
      catch (e) { if (e.code !== 'not_found') throw e; }
    }
    const query = `appProperties has { key='haslalab' and value='root' } and mimeType=${driveQuote(DRIVE_FOLDER)} and trashed=false`;
    const r = await driveFetch(token, `${DRIVE_API}/drive/v3/files?q=${encodeURIComponent(query)}&fields=files(id)&pageSize=1`, {}, 'find');
    let id = (await r.json()).files?.[0]?.id;
    if (!id) {
      try { id = await driveMkdir(token, DRIVE_ROOT, null, f, {appProperties: {haslalab: 'root'}}); }
      catch (e) { console.error('workshop drive mkdir', e?.status || ''); fail(502, 'drive_failed'); }
    }
    await env.DB.prepare("UPDATE workshop_connectors SET root_id=?,updated_at=? WHERE user_id=? AND provider='google'").bind(id, now(), conn.user_id).run();
    conn.root_id = id;
    return id;
  }
  /* a file or folder is ours only if its parents lead up to the «HaslaLab» folder (at most 8 levels); returns its metadata
     and the trail of folders from the root */
  async function driveInside(token, root, id, {folder = null} = {}) {
    if (!DRIVE_ID.test(String(id || ''))) fail(404, 'not_found');
    const meta = id === root ? {id: root, name: DRIVE_ROOT, mimeType: DRIVE_FOLDER} : await driveMeta(token, id);
    if (meta.trashed) fail(404, 'not_found');
    const trail = [];
    let cur = meta;
    for (let i = 0; i < 9; i++) {
      if (cur.id === root) { trail.unshift({id: root, name: DRIVE_ROOT}); break; }
      trail.unshift({id: cur.id, name: cur.name});
      const parent = cur.parents?.[0];
      if (!parent || i === 8) fail(404, 'not_found');
      cur = parent === root ? {id: root} : await driveMeta(token, parent);
      if (cur.id !== root && (cur.trashed || cur.mimeType !== DRIVE_FOLDER)) fail(404, 'not_found');
    }
    if (folder === true && meta.mimeType !== DRIVE_FOLDER) fail(400, 'not_a_folder');
    if (folder === false && meta.mimeType === DRIVE_FOLDER) fail(400, 'is_a_folder');
    return {meta, trail};
  }
  async function driveDownload(token, root, id, maxBytes = WORKSHOP_MAX_FILE) {
    const {meta} = await driveInside(token, root, id, {folder: false});
    if (/^application\/vnd\.google-apps\./.test(meta.mimeType || '')) fail(415, 'type_not_allowed');
    if (+meta.size > maxBytes) fail(413, 'file_too_large');
    const r = await driveFetch(token, `${DRIVE_API}/drive/v3/files/${encodeURIComponent(id)}?alt=media`, {}, 'download');
    const bytes = new Uint8Array(await r.arrayBuffer());
    if (bytes.length > maxBytes) fail(413, 'file_too_large');
    return {meta, bytes};
  }
  const driveView = x => ({id: x.id, name: x.name, folder: x.mimeType === DRIVE_FOLDER, size: x.size != null ? +x.size : null, modified: x.modifiedTime || null});
  async function driveUp(token, parent, name, bytes) {
    const ext = extOf(name);
    if (!WORKSHOP_TYPES[ext]) fail(415, 'type_not_allowed');
    if (!bytes.length) bad('file_required');
    if (bytes.length > WORKSHOP_MAX_FILE) fail(413, 'file_too_large');
    if (!contentMatches(ext, bytes)) fail(415, 'type_mismatch');
    try { return await driveUpload(token, {name: cleanName(name, ext), parent, mime: WORKSHOP_TYPES[ext].mime, bytes}, f); }
    catch (e) { console.error('workshop drive upload', e?.status || ''); fail(e?.status === 403 ? 403 : 502, e?.status === 403 ? 'drive_forbidden' : 'drive_failed'); }
  }

  /* ======== GitHub ======== */
  const ghHeaders = (token, extra = {}) => ({Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': UA, ...extra});
  const tokens = new Map();
  /* a short-lived installation token, narrowed to one repository when given; kept in memory only, never stored or sent out */
  async function installationToken(env, installationId, {repoId = null, write = false} = {}) {
    const key = `${installationId}:${repoId || '*'}:${write ? 'w' : 'r'}`, hit = tokens.get(key), t = now();
    if (hit && hit.exp > t + 300) return hit.token;
    const body = {permissions: repoId ? {contents: write ? 'write' : 'read', metadata: 'read'} : {metadata: 'read'}};
    if (repoId) body.repository_ids = [repoId];
    let r;
    try {
      r = await f(`${GH}/app/installations/${encodeURIComponent(installationId)}/access_tokens`, {method: 'POST',
        headers: ghHeaders(await githubAppJwt(env, t), {'Content-Type': 'application/json'}), body: JSON.stringify(body)});
    } catch (e) { if (e?.code === 'not_configured') throw new HttpError(503, 'not_configured'); fail(502, 'github_unreachable'); }
    if (r.status === 404 || r.status === 401) fail(409, 'github_reconnect');
    if (r.status === 422 || r.status === 403) fail(403, 'github_repo_not_allowed');
    if (!r.ok) { console.error('workshop github token', r.status); fail(502, 'github_failed'); }
    const j = await r.json();
    const exp = Math.floor(Date.parse(j.expires_at || '') / 1000) || t + 3000;
    tokens.set(key, {token: j.token, exp});
    if (tokens.size > 500) tokens.delete(tokens.keys().next().value);
    return j.token;
  }
  async function ghFetch(token, url, init = {}, what = 'github') {
    let r;
    try { r = await f(url, {...init, headers: ghHeaders(token, init.headers || {})}); } catch { fail(502, 'github_unreachable'); }
    if (r.status === 404) fail(404, 'not_found');
    if (r.status === 401) fail(409, 'github_reconnect');
    if (r.status === 403 || r.status === 429) { console.error('workshop github', what, r.status); fail(r.status === 429 ? 429 : 403, r.status === 429 ? 'rate_limited' : 'github_forbidden'); }
    if (r.status === 409 || r.status === 422) fail(409, 'github_conflict');
    if (!r.ok) { console.error('workshop github', what, r.status); fail(502, 'github_failed'); }
    return r;
  }
  async function ghRepos(env, conn) {
    const token = await installationToken(env, conn.installation_id);
    const out = [];
    for (let page = 1; page <= 3; page++) {
      const j = await (await ghFetch(token, `${GH}/installation/repositories?per_page=100&page=${page}`, {}, 'repos')).json();
      for (const r of j.repositories || []) out.push({id: r.id, full_name: r.full_name, private: !!r.private, default_branch: r.default_branch || 'main'});
      if (!j.repositories || j.repositories.length < 100) break;
    }
    return out;
  }
  const contentsUrl = (repo, path, branch) => `${GH}/repos/${repo.split('/').map(encodeURIComponent).join('/')}/contents/${path.split('/').map(encodeURIComponent).join('/')}${branch ? '?ref=' + encodeURIComponent(branch) : ''}`;
  function ghReady(conn) {
    if (!conn) fail(409, 'not_connected');
    if (!conn.repo || !conn.repo_id || !conn.folder) fail(409, 'repo_not_chosen');
    return conn;
  }
  async function ghMeta(token, conn, full) {
    try { return await (await ghFetch(token, contentsUrl(conn.repo, full, conn.branch), {}, 'meta')).json(); }
    catch (e) { if (e.code === 'not_found') return null; throw e; }
  }
  async function ghPut(env, conn, rel, bytes, what) {
    const token = await installationToken(env, conn.installation_id, {repoId: conn.repo_id, write: true});
    const full = joinPath(conn.folder, rel), old = await ghMeta(token, conn, full);
    if (Array.isArray(old) || (old && old.type !== 'file')) fail(409, 'is_a_folder');
    const name = full.split('/').pop();
    const body = {message: `HaslaLab: ${old ? 'update' : 'add'} ${name}${what ? ' (' + what + ')' : ''}`, content: b64(bytes), branch: conn.branch || undefined, ...(old?.sha ? {sha: old.sha} : {})};
    const r = await ghFetch(token, contentsUrl(conn.repo, full, null), {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)}, 'put');
    const j = await r.json();
    return {path: rel, name, size: bytes.length, sha: j.content?.sha || null, updated: !!old};
  }
  async function ghDownload(env, conn, rel, maxBytes = WORKSHOP_MAX_FILE) {
    const token = await installationToken(env, conn.installation_id, {repoId: conn.repo_id});
    const full = joinPath(conn.folder, rel), meta = await ghMeta(token, conn, full);
    if (!meta) fail(404, 'not_found');
    if (Array.isArray(meta) || meta.type !== 'file') fail(400, 'is_a_folder');
    if (+meta.size > maxBytes) fail(413, 'file_too_large');
    const r = await ghFetch(token, contentsUrl(conn.repo, full, conn.branch), {headers: {Accept: 'application/vnd.github.raw'}}, 'raw');
    const bytes = new Uint8Array(await r.arrayBuffer());
    if (bytes.length > maxBytes) fail(413, 'file_too_large');
    return {name: meta.name, bytes};
  }
  const relOf = v => { const p = cleanGhPath(v); return p == null ? bad('bad_path') : p; };
  const fileRel = v => { const p = cleanGhPath(v, {allowEmpty: false}); return p == null ? bad('bad_path') : p; };

  async function readForm(req) {
    if (Number(req?.headers?.get?.('Content-Length') || 0) > WORKSHOP_MAX_FILE + 64 * 1024) fail(413, 'file_too_large');
    if (!(req?.headers?.get?.('Content-Type') || '').startsWith('multipart/form-data')) bad('bad_form');
    let form; try { form = await req.formData(); } catch { bad('bad_form'); }
    const file = form.get('file');
    if (!file || typeof file === 'string' || typeof file.arrayBuffer !== 'function') bad('file_required');
    if (file.size > WORKSHOP_MAX_FILE) fail(413, 'file_too_large');
    const ext = extOf(file.name);
    if (!WORKSHOP_TYPES[ext]) fail(415, 'type_not_allowed');
    const bytes = new Uint8Array(await file.arrayBuffer());
    if (!bytes.length) bad('file_required');
    if (bytes.length > WORKSHOP_MAX_FILE) fail(413, 'file_too_large');
    if (!contentMatches(ext, bytes)) fail(415, 'type_mismatch');
    const val = k => { const v = form.get(k); return typeof v === 'string' ? v : ''; };
    return {bytes, ext, name: file.name, folder: val('folder'), path: val('path')};
  }

  /* ======== the connect flow ======== */
  async function start(env, me, prov, body) {
    if (prov === 'google' ? !driveConfigured(env) : !githubConfigured(env)) notConfigured();
    await limit(env, 'wsc-start:' + me.id, 20, 3600);
    const ret = allowedReturn(env, body?.return);
    if (!ret) bad('bad_return');
    const t = now(), state = rand(32), verifier = prov === 'google' ? rand(48) : null;
    await env.DB.prepare('DELETE FROM workshop_connector_states WHERE created_at<?').bind(t - STATE_TTL).run();
    await env.DB.prepare('INSERT INTO workshop_connector_states(state_hash,user_id,provider,verifier,return_to,created_at) VALUES(?,?,?,?,?,?)')
      .bind(await sha(state), me.id, prov, verifier, ret, t).run();
    if (prov === 'google') {
      const q = new URLSearchParams({client_id: env.GOOGLE_CLIENT_ID, redirect_uri: googleRedirectUri(env), response_type: 'code', scope: GOOGLE_SCOPES.join(' '),
        state, code_challenge: b64u(await crypto.subtle.digest('SHA-256', enc.encode(verifier))), code_challenge_method: 'S256',
        access_type: 'offline', include_granted_scopes: 'true', prompt: 'consent'});
      return {url: G_AUTH + '?' + q};
    }
    /* authorize:true (the page resuming after an install whose redirect carried no state): GitHub's plain user
       authorization, which always returns the state; the installation is then found among the member's own */
    if (body?.authorize === true) return {url: `${GH_WEB}/login/oauth/authorize?` + new URLSearchParams({client_id: env.GITHUB_APP_CLIENT_ID, redirect_uri: githubRedirectUri(env), state})};
    return {url: `${GH_WEB}/apps/${encodeURIComponent(env.GITHUB_APP_SLUG)}/installations/new?` + new URLSearchParams({state})};
  }
  /* the state as the provider sent it back: known, for this provider, fresh, not used */
  async function stateRow(env, prov, state) {
    if (!/^[A-Za-z0-9_-]{20,100}$/.test(state || '')) return null;
    const r = await env.DB.prepare('SELECT * FROM workshop_connector_states WHERE state_hash=? AND provider=?').bind(await sha(state), prov).first();
    if (!r || r.called_at) return null;
    if (r.created_at < now() - STATE_TTL) { await env.DB.prepare('DELETE FROM workshop_connector_states WHERE state_hash=?').bind(r.state_hash).run(); return {expired: true, ...r}; }
    return r;
  }
  /* single use: only the first callback for a state gets a ticket */
  async function issueTicket(env, st, fields) {
    const ticket = rand(32), cols = Object.keys(fields);
    const r = await env.DB.prepare(`UPDATE workshop_connector_states SET called_at=?,ticket_hash=?${cols.map(c => `,${c}=?`).join('')} WHERE state_hash=? AND called_at IS NULL RETURNING state_hash`)
      .bind(now(), await sha(ticket), ...cols.map(c => fields[c]), st.state_hash).first();
    return r ? ticket : null;
  }
  const dropState = (env, st) => env.DB.prepare('DELETE FROM workshop_connector_states WHERE state_hash=?').bind(st.state_hash).run();

  async function googleCallback(env, url) {
    const st = await stateRow(env, 'google', url.searchParams.get('state'));
    if (!st) return plain(400, 'This link has expired or was already used. Please connect again from HaslaLab.');
    if (st.expired) return back(st.return_to, 'connector=google&error=expired');
    const code = url.searchParams.get('code');
    if (!code || url.searchParams.get('error')) { await dropState(env, st); return back(st.return_to, 'connector=google&error=cancelled'); }
    if (code.length > 2048) { await dropState(env, st); return back(st.return_to, 'connector=google&error=failed'); }
    const ticket = await issueTicket(env, st, {code_enc: await sealToken(env, code, 'drive-code:' + st.user_id)});
    if (!ticket) return plain(400, 'This link was already used. Please connect again from HaslaLab.');
    return back(st.return_to, 'connector=google&ticket=' + ticket);
  }
  async function googleFinish(env, st) {
    const code = await openToken(env, st.code_enc, 'drive-code:' + st.user_id);
    let r, j;
    try {
      r = await f(G_TOKEN, gForm({grant_type: 'authorization_code', code, client_id: env.GOOGLE_CLIENT_ID, client_secret: env.GOOGLE_CLIENT_SECRET,
        redirect_uri: googleRedirectUri(env), code_verifier: st.verifier}));
      j = await r.json().catch(() => ({}));
    } catch { fail(502, 'drive_unreachable'); }
    if (!r.ok || !j.access_token) { console.error('workshop drive code', r.status, String(j?.error || '').slice(0, 40)); fail(502, 'drive_failed'); }
    const granted = String(j.scope || '').split(/\s+/);
    if (!granted.includes(DRIVE_SCOPE)) { if (j.refresh_token || j.access_token) await googleRevoke(j.refresh_token || j.access_token); fail(400, 'drive_scope_missing'); }
    if (!j.refresh_token) { await googleRevoke(j.access_token); fail(502, 'drive_no_refresh'); }
    let email = null;
    try { const mr = await f(G_ME, {headers: {Authorization: 'Bearer ' + j.access_token}}); if (mr.ok) email = String((await mr.json()).email || '').slice(0, 200) || null; } catch {}
    const uid = st.user_id, t = now(), old = await row(env, uid, 'google');
    if (old?.refresh_enc) { try { await googleRevoke(await openToken(env, old.refresh_enc, 'drive-refresh:' + uid)); } catch {} }
    await env.DB.prepare(`INSERT INTO workshop_connectors(user_id,provider,account,refresh_enc,access_enc,access_exp,root_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)
      ON CONFLICT(user_id,provider) DO UPDATE SET account=excluded.account,refresh_enc=excluded.refresh_enc,access_enc=excluded.access_enc,access_exp=excluded.access_exp,updated_at=excluded.updated_at`)
      .bind(uid, 'google', email, await sealToken(env, j.refresh_token, 'drive-refresh:' + uid), await sealToken(env, j.access_token, 'drive-access:' + uid),
        t + Math.max(60, Math.min(3600, +j.expires_in || 3600)), old?.root_id || null, t, t).run();
    const conn = await row(env, uid, 'google');
    await driveRoot(env, conn, j.access_token);
    return {provider: 'google', connected: true, email};
  }

  async function githubCallback(env, url) {
    const state = url.searchParams.get('state');
    /* an install that came back without our state: nothing is linked; the site asks GitHub again with a fresh state */
    if (!state && (url.searchParams.get('installation_id') || url.searchParams.get('code'))) {
      const site = String(env.ALLOWED_ORIGINS || '').split(',').map(v => v.trim()).find(v => /^https:\/\//.test(v));
      if (site) return back(site + '/', 'connector=github&resume=1');
    }
    const st = await stateRow(env, 'github', state);
    if (!st) return plain(400, 'This link has expired or was already used. Please connect again from HaslaLab.');
    if (st.expired) return back(st.return_to, 'connector=github&error=expired');
    if (url.searchParams.get('setup_action') === 'request') { await dropState(env, st); return back(st.return_to, 'connector=github&error=install_requested'); }
    const instRaw = url.searchParams.get('installation_id'), inst = /^\d{1,15}$/.test(instRaw || '') ? +instRaw : null;
    const code = url.searchParams.get('code');
    if (!code) {
      /* the App does not ask for authorization during the install: ask for it now, keeping the same state */
      if (!inst && !st.installation_id) { await dropState(env, st); return back(st.return_to, 'connector=github&error=cancelled'); }
      if (inst) await env.DB.prepare('UPDATE workshop_connector_states SET installation_id=? WHERE state_hash=? AND called_at IS NULL').bind(inst, st.state_hash).run();
      return new Response(null, {status: 302, headers: {Location: `${GH_WEB}/login/oauth/authorize?` + new URLSearchParams({client_id: env.GITHUB_APP_CLIENT_ID, redirect_uri: githubRedirectUri(env), state}),
        'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'}});
    }
    /* claim the state first, so a second callback with it gets nothing */
    const claimed = await env.DB.prepare('UPDATE workshop_connector_states SET called_at=? WHERE state_hash=? AND called_at IS NULL RETURNING installation_id').bind(now(), st.state_hash).first();
    if (!claimed) return plain(400, 'This link was already used. Please connect again from HaslaLab.');
    const want = inst || claimed.installation_id || null;
    let userToken = null;
    try {
      const r = await f(`${GH_WEB}/login/oauth/access_token`, {method: 'POST', headers: {Accept: 'application/json', 'Content-Type': 'application/json', 'User-Agent': UA},
        body: JSON.stringify({client_id: env.GITHUB_APP_CLIENT_ID, client_secret: env.GITHUB_APP_CLIENT_SECRET, code, redirect_uri: githubRedirectUri(env)})});
      const j = await r.json().catch(() => ({}));
      if (!r.ok || !j.access_token) { console.error('workshop github code', r.status, String(j?.error || '').slice(0, 40)); await dropState(env, st); return back(st.return_to, 'connector=github&error=failed'); }
      userToken = j.access_token;
      /* the installations this GitHub user can reach, of this App only: the one they came back with must be among them */
      const ir = await f(`${GH}/user/installations?per_page=100`, {headers: ghHeaders(userToken)});
      const list = ir.ok ? ((await ir.json()).installations || []) : [];
      if (!ir.ok) console.error('workshop github installations', ir.status);
      const appId = String(env.GITHUB_APP_ID);
      const mine = list.filter(i => String(i.app_id) === appId);
      /* no installation id (the plain authorization): the one on the user's own account, else the only one */
      let found = want ? mine.find(i => +i.id === want) : null;
      if (!want) {
        let login = null;
        try { const ur = await f(`${GH}/user`, {headers: ghHeaders(userToken)}); if (ur.ok) login = String((await ur.json()).login || ''); } catch {}
        found = mine.find(i => login && i.account?.login === login && i.account?.type !== 'Organization') || (mine.length === 1 ? mine[0] : null);
      }
      if (!found) { await dropState(env, st); return back(st.return_to, 'connector=github&error=' + (want ? 'not_your_installation' : 'no_installation')); }
      const ticket = rand(32);
      await env.DB.prepare('UPDATE workshop_connector_states SET ticket_hash=?,installation_id=?,account=?,account_type=? WHERE state_hash=?')
        .bind(await sha(ticket), +found.id, String(found.account?.login || '').slice(0, 100), found.account?.type === 'Organization' ? 'Organization' : 'User', st.state_hash).run();
      return back(st.return_to, 'connector=github&ticket=' + ticket);
    } catch (e) {
      console.error('workshop github callback', String(e?.message || 'error').slice(0, 60));
      await dropState(env, st);
      return back(st.return_to, 'connector=github&error=failed');
    } finally {
      /* the user token was only for that check: revoke it */
      if (userToken) {
        try {
          await f(`${GH}/applications/${encodeURIComponent(env.GITHUB_APP_CLIENT_ID)}/token`, {method: 'DELETE',
            headers: {Authorization: 'Basic ' + btoa(env.GITHUB_APP_CLIENT_ID + ':' + env.GITHUB_APP_CLIENT_SECRET), Accept: 'application/vnd.github+json', 'User-Agent': UA, 'Content-Type': 'application/json'},
            body: JSON.stringify({access_token: userToken})});
        } catch {}
      }
    }
  }
  async function githubFinish(env, st) {
    if (!st.installation_id) fail(400, 'bad_ticket');
    const t = now(), uid = st.user_id, old = await row(env, uid, 'github');
    const same = old && +old.installation_id === +st.installation_id;
    await env.DB.prepare(`INSERT INTO workshop_connectors(user_id,provider,account,account_type,installation_id,repo_id,repo,branch,folder,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)
      ON CONFLICT(user_id,provider) DO UPDATE SET account=excluded.account,account_type=excluded.account_type,installation_id=excluded.installation_id,
        repo_id=excluded.repo_id,repo=excluded.repo,branch=excluded.branch,folder=excluded.folder,updated_at=excluded.updated_at`)
      .bind(uid, 'github', st.account || null, st.account_type || 'User', st.installation_id, same ? old.repo_id : null, same ? old.repo : null, same ? old.branch : null,
        same ? old.folder : null, t, t).run();
    return {provider: 'github', connected: true, account: st.account || null};
  }
  async function finish(env, me, body) {
    await limit(env, 'wsc-finish:' + me.id, 30, 3600);
    const ticket = String(body?.ticket || '');
    if (!/^[A-Za-z0-9_-]{20,100}$/.test(ticket)) bad('bad_ticket');
    const st = await env.DB.prepare('DELETE FROM workshop_connector_states WHERE ticket_hash=? RETURNING *').bind(await sha(ticket)).first();
    if (!st) bad('bad_ticket');
    if (st.user_id !== me.id) fail(403, 'wrong_user');
    if (st.created_at < now() - STATE_TTL) bad('expired');
    if (st.provider === 'google') { if (!driveConfigured(env)) notConfigured(); return googleFinish(env, st); }
    if (st.provider === 'github') { if (!githubConfigured(env)) notConfigured(); return githubFinish(env, st); }
    bad('bad_ticket');
  }
  const manageUrl = c => c?.installation_id ? (c.account_type === 'Organization' && c.account
    ? `${GH_WEB}/organizations/${encodeURIComponent(c.account)}/settings/installations/${c.installation_id}` : `${GH_WEB}/settings/installations/${c.installation_id}`) : null;

  async function status(env, uid) {
    const [d, g] = [await row(env, uid, 'google'), await row(env, uid, 'github')];
    return {
      drive: {configured: driveConfigured(env), connected: !!d, ...(d ? {email: d.account || null} : {})},
      github: {configured: githubConfigured(env), connected: !!g, ...(g ? {account: g.account || null, repo: g.repo || null, folder: g.folder || null, manage_url: manageUrl(g)} : {})},
      max_file: WORKSHOP_MAX_FILE, types: Object.keys(WORKSHOP_TYPES)
    };
  }

  /* ======== routes ======== */
  return async function workshopConnectorsRoute(p, m, body, me, req, env, projectSource = null) {
    if (p !== '/api/workshop/connectors' && !p.startsWith('/api/workshop/connectors/')) return undefined;
    await ensureConnectorSchema(env);
    const url = new URL(req?.url || 'https://x.invalid' + p);

    /* the provider callbacks: a top-level navigation with no bearer token; only the state says who started it */
    if ((p === GOOGLE_CALLBACK_PATH || p === GITHUB_CALLBACK_PATH) && (m === 'GET' || m === 'HEAD')) {
      try { await limit(env, 'wsc-cb:' + (req?.headers?.get?.('CF-Connecting-IP') || 'local'), 60, 600); }
      catch { return plain(429, 'Too many attempts. Please wait a moment and try again.'); }
      if (p === GOOGLE_CALLBACK_PATH) return driveConfigured(env) ? googleCallback(env, url) : plain(503, 'Google Drive is not set up yet.');
      return githubConfigured(env) ? githubCallback(env, url) : plain(503, 'GitHub is not set up yet.');
    }

    needUser(me);
    const uid = me.id;
    if (p === '/api/workshop/connectors' && m === 'GET') return status(env, uid);
    if (p === '/api/workshop/connectors/finish' && m === 'POST') return finish(env, me, body);
    let mm;
    if ((mm = /^\/api\/workshop\/connectors\/(google|github)\/start$/.exec(p)) && m === 'POST') return start(env, me, mm[1], body);
    if ((mm = /^\/api\/workshop\/connectors\/(google|github)$/.exec(p)) && m === 'DELETE') {
      await limit(env, 'wsc-edit:' + uid, 120, 3600);
      const c = await row(env, uid, mm[1]);
      if (mm[1] === 'google' && c?.refresh_enc) { try { await googleRevoke(await openToken(env, c.refresh_enc, 'drive-refresh:' + uid)); } catch {} }
      await env.DB.prepare('DELETE FROM workshop_connectors WHERE user_id=? AND provider=?').bind(uid, mm[1]).run();
      await env.DB.prepare('DELETE FROM workshop_connector_states WHERE user_id=? AND provider=?').bind(uid, mm[1]).run();
      return {ok: true, ...(mm[1] === 'github' ? {manage_url: manageUrl(c)} : {})};
    }

    /* ---- Drive ---- */
    if (p.startsWith('/api/workshop/connectors/drive/')) {
      if (!driveConfigured(env)) notConfigured();
      const conn = await row(env, uid, 'google');
      if (!conn) fail(409, 'not_connected');
      const read = m === 'GET';
      await limit(env, (read ? 'wsc-read:' : 'wsc-write:') + uid, read ? 600 : 200, 3600);
      const token = await driveAccess(env, conn), root = await driveRoot(env, conn, token);
      if (projectSource) {
        const {meta,bytes}=await driveDownload(token,root,projectSource.ref,projectSource.maxBytes);
        return {name:meta.name,mime:WORKSHOP_TYPES[extOf(meta.name)]?.mime,bytes,key:'drive:'+projectSource.ref};
      }

      if (p === '/api/workshop/connectors/drive/files' && m === 'GET') {
        const id = url.searchParams.get('folder') || root;
        const {trail} = await driveInside(token, root, id, {folder: true});
        let list;
        try { list = await driveList(token, id, f, {fields: 'files(id,name,mimeType,size,modifiedTime)', orderBy: 'folder,name'}); }
        catch (e) { console.error('workshop drive list', e?.status || ''); fail(502, 'drive_failed'); }
        return {folder: id, root, trail, files: list.filter(x => !/^application\/vnd\.google-apps\.(?!folder$)/.test(x.mimeType || '')).map(driveView)};
      }
      if (p === '/api/workshop/connectors/drive/files' && m === 'POST') {
        const form = await readForm(req), parent = form.folder || root;
        await driveInside(token, root, parent, {folder: true});
        return {file: {id: await driveUp(token, parent, form.name, form.bytes), name: cleanName(form.name, form.ext), size: form.bytes.length}};
      }
      if (p === '/api/workshop/connectors/drive/folders' && m === 'POST') {
        const parent = String(body?.parent || '') || root;
        await driveInside(token, root, parent, {folder: true});
        const name = String(body?.name || '').normalize('NFC').replace(/[\u0000-\u001f\u007f\\/"<>|*?:]/g, '').replace(/\s+/g, ' ').trim().slice(0, 60);
        if (!name || name === '.' || name === '..') bad('bad_name');
        let id;
        try { id = await driveMkdir(token, name, parent, f, {appProperties: {haslalab: 'folder'}}); }
        catch (e) { console.error('workshop drive mkdir', e?.status || ''); fail(502, 'drive_failed'); }
        return {folder: {id, name}};
      }
      if (p === '/api/workshop/connectors/drive/copy' && m === 'POST') {
        await limit(env, 'wsc-copy:' + uid, 120, 3600);
        if (body?.direction === 'to_drive') {
          const src = await workshopReadBytes(env, uid, body.file_id, {HttpError});
          const parent = String(body.folder || '') || root;
          await driveInside(token, root, parent, {folder: true});
          return {file: {id: await driveUp(token, parent, src.name, src.bytes), name: src.name, size: src.bytes.length}};
        }
        if (body?.direction === 'to_storage') {
          const {meta, bytes} = await driveDownload(token, root, String(body.id || ''));
          return workshopSaveBytes(env, uid, {bytes, name: meta.name, folder: body.folder || ''}, {HttpError, now});
        }
        bad('bad_direction');
      }
      const fm = /^\/api\/workshop\/connectors\/drive\/files\/([A-Za-z0-9_-]{10,200})$/.exec(p);
      if (!fm) fail(404, 'not_found');
      const id = fm[1];
      if (id === root) fail(403, 'root_folder');
      if (m === 'GET') {
        const {meta, bytes} = await driveDownload(token, root, id);
        return attachment(bytes, meta.name, bytes.length);
      }
      if (m === 'PATCH') {
        const {meta} = await driveInside(token, root, id);
        if (typeof body?.name !== 'string' || !body.name.trim()) bad('bad_name');
        const isFolder = meta.mimeType === DRIVE_FOLDER, ext = extOf(meta.name);
        const name = isFolder ? body.name.normalize('NFC').replace(/[\u0000-\u001f\u007f\\/"<>|*?:]/g, '').trim().slice(0, 60) : ext ? cleanName(body.name, ext) : '';
        if (!name) bad('bad_name');
        await driveFetch(token, `${DRIVE_API}/drive/v3/files/${encodeURIComponent(id)}?fields=id`, {method: 'PATCH', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({name})}, 'rename');
        return {file: {id, name}};
      }
      if (m === 'DELETE') {
        await driveInside(token, root, id);
        /* to the member's Drive trash, from where they can still restore it */
        await driveFetch(token, `${DRIVE_API}/drive/v3/files/${encodeURIComponent(id)}?fields=id`, {method: 'PATCH', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({trashed: true})}, 'trash');
        return {ok: true};
      }
      fail(404, 'not_found');
    }

    /* ---- GitHub ---- */
    if (p.startsWith('/api/workshop/connectors/github/')) {
      if (!githubConfigured(env)) notConfigured();
      const conn = await row(env, uid, 'github');
      if (!conn) fail(409, 'not_connected');
      const read = m === 'GET';
      await limit(env, (read ? 'wsc-read:' : 'wsc-write:') + uid, read ? 600 : 200, 3600);

      if (p === '/api/workshop/connectors/github/repos' && m === 'GET') return {repos: await ghRepos(env, conn), repo: conn.repo || null, folder: conn.folder || null};
      if (p === '/api/workshop/connectors/github/repo' && m === 'POST') {
        const repoId = Number(body?.repo_id);
        if (!Number.isSafeInteger(repoId) || repoId <= 0) bad('bad_repo');
        const folder = cleanGhPath(body?.folder == null || body.folder === '' ? GH_DEFAULT_FOLDER : body.folder, {allowEmpty: false});
        if (folder == null) bad('bad_path');
        const repo = (await ghRepos(env, conn)).find(r => r.id === repoId);
        if (!repo) fail(403, 'github_repo_not_allowed');
        if (!/^[A-Za-z0-9_.-]{1,100}\/[A-Za-z0-9_.-]{1,100}$/.test(repo.full_name)) bad('bad_repo');
        await env.DB.prepare("UPDATE workshop_connectors SET repo_id=?,repo=?,branch=?,folder=?,updated_at=? WHERE user_id=? AND provider='github'")
          .bind(repo.id, repo.full_name, String(repo.default_branch || 'main').slice(0, 200), folder, now(), uid).run();
        return {repo: repo.full_name, folder};
      }
      ghReady(conn);
      if (p === '/api/workshop/connectors/github/files' && m === 'GET') {
        const rel = relOf(url.searchParams.get('path'));
        const token = await installationToken(env, conn.installation_id, {repoId: conn.repo_id});
        const j = await ghMeta(token, conn, joinPath(conn.folder, rel));
        if (j && !Array.isArray(j)) fail(400, 'not_a_folder');
        const base = conn.folder + '/';
        const files = (j || []).filter(x => x.type === 'file' || x.type === 'dir').filter(x => String(x.path || '').startsWith(base))
          .map(x => ({name: x.name, path: x.path.slice(base.length), folder: x.type === 'dir', size: x.type === 'file' ? +x.size || 0 : null}))
          .sort((a, b) => (b.folder - a.folder) || a.name.localeCompare(b.name));
        return {repo: conn.repo, folder: conn.folder, path: rel, files};
      }
      if (p === '/api/workshop/connectors/github/files' && m === 'POST') {
        const form = await readForm(req), dir = relOf(form.path);
        return {file: await ghPut(env, conn, joinPath(dir, ghFileName(form.name, form.ext)), form.bytes)};
      }
      if (projectSource) {
        const rel=fileRel(projectSource.ref);
        const {name,bytes}=await ghDownload(env,conn,rel,projectSource.maxBytes);
        return {name,mime:WORKSHOP_TYPES[extOf(name)]?.mime,bytes,key:['github',conn.repo_id,conn.branch,conn.folder,rel].join(':')};
      }
      if (p === '/api/workshop/connectors/github/file') {
        const rel = fileRel(url.searchParams.get('path'));
        if (m === 'GET') { const {name, bytes} = await ghDownload(env, conn, rel); return attachment(bytes, name, bytes.length); }
        if (m === 'DELETE') {
          const token = await installationToken(env, conn.installation_id, {repoId: conn.repo_id, write: true});
          const full = joinPath(conn.folder, rel), meta = await ghMeta(token, conn, full);
          if (!meta) fail(404, 'not_found');
          if (Array.isArray(meta) || meta.type !== 'file') fail(400, 'is_a_folder');
          await ghFetch(token, contentsUrl(conn.repo, full, null), {method: 'DELETE', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({message: `HaslaLab: delete ${meta.name}`, sha: meta.sha, branch: conn.branch || undefined})}, 'delete');
          return {ok: true};
        }
      }
      if (p === '/api/workshop/connectors/github/copy' && m === 'POST') {
        await limit(env, 'wsc-copy:' + uid, 120, 3600);
        if (body?.direction === 'to_github') {
          const src = await workshopReadBytes(env, uid, body.file_id, {HttpError});
          const dir = relOf(body.path), ext = extOf(src.name);
          return {file: await ghPut(env, conn, joinPath(dir, ghFileName(src.name, ext)), src.bytes, 'from storage')};
        }
        if (body?.direction === 'to_storage') {
          const {name, bytes} = await ghDownload(env, conn, fileRel(body.path));
          return workshopSaveBytes(env, uid, {bytes, name, folder: body.folder || ''}, {HttpError, now});
        }
        bad('bad_direction');
      }
      fail(404, 'not_found');
    }
    fail(404, 'not_found');
  };
}

/* account deletion: revoke the member's Google token at Google, then forget both links and any flow in progress */
export async function workshopConnectorsForgetUser(env, userId, {fetchImpl = null} = {}) {
  await ensureConnectorSchema(env);
  const d = await env.DB.prepare("SELECT refresh_enc FROM workshop_connectors WHERE user_id=? AND provider='google'").bind(userId).first();
  if (d?.refresh_enc && tokenKeyBytes(env)) {
    try {
      const token = await openToken(env, d.refresh_enc, 'drive-refresh:' + userId);
      await (fetchImpl || globalThis.fetch)(G_REVOKE, {method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'}, body: new URLSearchParams({token}).toString()});
    } catch { /* the rows go regardless */ }
  }
  await env.DB.prepare('DELETE FROM workshop_connectors WHERE user_id=?').bind(userId).run();
  await env.DB.prepare('DELETE FROM workshop_connector_states WHERE user_id=?').bind(userId).run();
}
