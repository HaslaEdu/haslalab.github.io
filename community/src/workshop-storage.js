/* Workshop storage (#/workshop/storage): each member's own files, kept by HaslaLab.
   - GET    /api/workshop/storage                       the member's folders and files, bytes used, the quota and the limits
                                                        (?kind=paper|problem|figure|sim|file and/or ?folder=… narrow the list)
   - POST   /api/workshop/storage/files                 multipart/form-data: "file" and "folder" ('' is the top level);
                                                        optional "kind" (WORKSHOP_KINDS) and "ensure_folder"="1" (the folder
                                                        and its parents are made when missing, as POST …/folders does)
   - GET    /api/workshop/storage/files/:id             the file, always as an attachment (owner only)
   - PUT    /api/workshop/storage/files/:id/content     replaces the file's bytes in place (the id, name and folder stay): a
                                                        multipart "file" (its extension, if it has one, must be the file's)
                                                        with optional "kind" and "base", or the raw bytes as the body with
                                                        ?kind=…&base=…; base = the updated_at the page last saw, 409 changed
                                                        when the file was saved since. Same type and first-byte checks, 20 MB,
                                                        and the quota counted with the size difference in the update itself.
                                                        The new bytes go to a new R2 key first; the old object is deleted only
                                                        once the row points at the new one.
   - PATCH  /api/workshop/storage/files/:id             {name} renames (the extension stays), {folder} moves, {kind} retags
   - DELETE /api/workshop/storage/files/:id             the row and its R2 object
   - POST   /api/workshop/storage/folders               {path} makes a folder (and the folders above it)
   - PATCH  /api/workshop/storage/folders               {path, to} renames or moves a folder with everything in it
   - DELETE /api/workshop/storage/folders?path=…        an empty folder
   Files go to the existing R2 binding env.LAB_PAGES under workshop/<userId>/<fileId>; the R2 key is made from ids only,
   never from a name or a folder the member typed, so nothing a member sends can reach another key. Names and folders
   live in D1. Shared files use the same attachment response after a class membership check. */
import { classStorageRoutes, STORAGE_SHARE_SCHEMA } from './workshop-class-storage.js';
import { ensureLearnSchema, planOf } from './learn-services.js';

export const WORKSHOP_SCHEMA = [
  `CREATE TABLE IF NOT EXISTS workshop_files (
     id TEXT PRIMARY KEY,
     owner_id INTEGER NOT NULL,
     folder TEXT NOT NULL DEFAULT '',
     name TEXT NOT NULL,
     size INTEGER NOT NULL,
     mime TEXT NOT NULL,
     r2_key TEXT NOT NULL,
     created_at INTEGER NOT NULL,
     updated_at INTEGER NOT NULL)`,
  `CREATE INDEX IF NOT EXISTS workshop_files_owner ON workshop_files(owner_id, folder, name)`,
  `CREATE TABLE IF NOT EXISTS workshop_folders (
     owner_id INTEGER NOT NULL,
     path TEXT NOT NULL,
     created_at INTEGER NOT NULL,
     PRIMARY KEY (owner_id, path))`
];
/* added after the table first went out: what made the file, so an app lists only its own documents. A duplicate column
   error means another isolate added it already. */
const WORKSHOP_COLUMNS = [`ALTER TABLE workshop_files ADD COLUMN kind TEXT NOT NULL DEFAULT 'file'`];
const WORKSHOP_INDEXES = [`CREATE INDEX IF NOT EXISTS workshop_files_kind ON workshop_files(owner_id, kind, updated_at)`];
/* paper: a test paper of the problem maker (teach.js); problem: one problem; figure: a figure editor scene or picture;
   sim: a simulation of the coding environment; file: anything uploaded by hand */
export const WORKSHOP_KINDS = ['file', 'paper', 'problem', 'figure', 'sim'];
const kindOf = v => (typeof v === 'string' && WORKSHOP_KINDS.includes(v) ? v : null);
export const WORKSHOP_PREFIX = 'workshop/';
export const WORKSHOP_MAX_FILE = 20 * 1024 * 1024;
export const WORKSHOP_FREE_QUOTA = 10 * 1024 * 1024;
export const WORKSHOP_PAID_QUOTA = 500 * 1024 * 1024;

async function storageLimits(env, userId, now) {
  await ensureLearnSchema(env);
  const {plan} = await planOf(env, userId, now);
  const quota = plan === 'free' ? WORKSHOP_FREE_QUOTA : WORKSHOP_PAID_QUOTA;
  return {plan, quota, max_file: Math.min(quota, WORKSHOP_MAX_FILE)};
}
const NAME_MAX = 120, SEG_MAX = 60, DEPTH_MAX = 5, PATH_MAX = 240, FILES_MAX = 2000, FOLDERS_MAX = 300;
const ID = /^[0-9a-f]{32}$/;

/* the types a member may keep: extension → the type the file is served with and how its first bytes are checked */
const ZIP = 'zip', TEXT = 'text';
export const WORKSHOP_TYPES = {
  pdf: {mime: 'application/pdf', sig: 'pdf'},
  png: {mime: 'image/png', sig: 'png'},
  jpg: {mime: 'image/jpeg', sig: 'jpg'},
  jpeg: {mime: 'image/jpeg', sig: 'jpg'},
  webp: {mime: 'image/webp', sig: 'webp'},
  svg: {mime: 'image/svg+xml', sig: 'svg'},
  json: {mime: 'application/json', sig: TEXT},
  txt: {mime: 'text/plain', sig: TEXT},
  csv: {mime: 'text/csv', sig: TEXT},
  md: {mime: 'text/markdown', sig: TEXT},
  hwpx: {mime: 'application/hwp+zip', sig: ZIP},
  docx: {mime: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', sig: ZIP},
  xlsx: {mime: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', sig: ZIP},
  pptx: {mime: 'application/vnd.openxmlformats-officedocument.presentationml.presentation', sig: ZIP}
};
const extOf = name => (/\.([A-Za-z0-9]{1,5})$/.exec(name)?.[1] || '').toLowerCase();
const starts = (b, ...xs) => xs.every((x, i) => b[i] === x);

/* do the first bytes match what the extension says? (a page named .png that is really HTML is refused) */
export function contentMatches(ext, bytes) {
  const t = WORKSHOP_TYPES[ext];
  if (!t || !bytes?.length) return false;
  switch (t.sig) {
    case 'pdf': return starts(bytes, 0x25, 0x50, 0x44, 0x46, 0x2d);
    case 'png': return starts(bytes, 0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a);
    case 'jpg': return starts(bytes, 0xff, 0xd8, 0xff);
    case 'webp': return starts(bytes, 0x52, 0x49, 0x46, 0x46) && bytes[8] === 0x57 && bytes[9] === 0x45 && bytes[10] === 0x42 && bytes[11] === 0x50;
    case ZIP: return starts(bytes, 0x50, 0x4b, 0x03, 0x04);
    case 'svg': case TEXT: {
      let s;
      try { s = new TextDecoder('utf-8', {fatal: true}).decode(bytes); } catch { return false; }
      if (s.includes('\u0000')) return false;
      return t.sig === 'svg' ? /<svg[\s>]/i.test(s.slice(0, 4096)) : true;
    }
  }
  return false;
}

/* a name that is safe in a header and keeps its extension */
export function cleanName(name, ext) {
  let n = String(name || '').split(/[\\/]/).pop().normalize('NFC').replace(/[\u0000-\u001f\u007f"<>|*?:]/g, '').replace(/\s+/g, ' ').trim();
  const tail = '.' + ext;
  if (!n.toLowerCase().endsWith(tail)) n = (n.replace(/\.+$/, '') || 'file') + tail;
  if (n.length === tail.length) n = 'file' + tail;
  if (n.length > NAME_MAX) n = n.slice(0, NAME_MAX - tail.length).trim() + tail;
  return n;
}
const asciiName = n => n.replace(/[^\x20-\x7e]/g, '_').replace(/[;\\"]/g, '_');

/* a folder path the member typed: segments joined by '/', '' for the top level; null when it is not acceptable */
export function cleanFolder(v) {
  if (v == null) return '';
  if (typeof v !== 'string') return null;
  const segs = v.normalize('NFC').split('/').map(s => s.replace(/\s+/g, ' ').trim()).filter(Boolean);
  if (segs.length > DEPTH_MAX) return null;
  for (const s of segs) if (s.length > SEG_MAX || s === '.' || s === '..' || /[\u0000-\u001f\u007f\\"<>|*?:]/.test(s)) return null;
  const p = segs.join('/');
  return p.length > PATH_MAX ? null : p;
}
const ancestors = p => { const s = p.split('/'), out = []; for (let i = 1; i <= s.length; i++) out.push(s.slice(0, i).join('/')); return out; };

const ready = new WeakSet();
export async function ensureWorkshopSchema(env) {
  if (ready.has(env.DB)) return;
  for (const sql of WORKSHOP_SCHEMA) await env.DB.prepare(sql).run();
  for (const sql of WORKSHOP_COLUMNS) {
    try { await env.DB.prepare(sql).run(); } catch (e) { if (!/duplicate column/i.test(String(e?.message || e))) throw e; }
  }
  for (const sql of STORAGE_SHARE_SCHEMA) await env.DB.prepare(sql).run();
  for (const sql of WORKSHOP_INDEXES) await env.DB.prepare(sql).run();
  ready.add(env.DB);
}

/* account deletion: every file of the member, R2 objects first */
export async function workshopForgetUser(env, userId) {
  await ensureWorkshopSchema(env);
  const rows = (await env.DB.prepare('SELECT r2_key FROM workshop_files WHERE owner_id=?').bind(userId).all()).results || [];
  if (env.LAB_PAGES) for (let i = 0; i < rows.length; i += 500) await env.LAB_PAGES.delete(rows.slice(i, i + 500).map(r => r.r2_key));
  await env.DB.prepare('DELETE FROM workshop_files WHERE owner_id=?').bind(userId).run();
  await env.DB.prepare('DELETE FROM workshop_folders WHERE owner_id=?').bind(userId).run();
  await env.DB.prepare('DELETE FROM workshop_class_shares WHERE owner_id=?').bind(userId).run();
  return rows.length;
}

const COLS = 'id,folder,name,size,mime,kind,created_at,updated_at';

/* keep bytes in the member's storage with every check an upload gets (type list, first bytes, 20 MB, folder, file count,
   quota, a free name); used by the upload route and by the connectors' copy into storage (workshop-connectors.js) */
export async function workshopSaveBytes(env, uid, {bytes, name, folder = '', kind = 'file', ensureFolder = false}, {HttpError, now}) {
  await ensureWorkshopSchema(env);
  const DB = env.DB, t = now();
  if (!env.LAB_PAGES) throw new HttpError(503, 'r2_unavailable');
  const ext = extOf(String(name || ''));
  if (!WORKSHOP_TYPES[ext]) throw new HttpError(415, 'type_not_allowed');
  if (!bytes?.length) throw new HttpError(400, 'file_required');
  if (bytes.length > WORKSHOP_MAX_FILE) throw new HttpError(413, 'file_too_large');
  if (!contentMatches(ext, bytes)) throw new HttpError(415, 'type_mismatch');
  const f = cleanFolder(folder);
  if (f == null) throw new HttpError(400, 'bad_folder');
  const limits = await storageLimits(env, uid, t);
  if (bytes.length > limits.max_file) throw new HttpError(413, 'file_too_large');
  const u = (await DB.prepare('SELECT COALESCE(SUM(size),0) AS n, COUNT(*) AS c FROM workshop_files WHERE owner_id=?').bind(uid).first()) || {n: 0, c: 0};
  if (u.c >= FILES_MAX) throw new HttpError(409, 'too_many_files');
  if (u.n + bytes.length > limits.quota) throw new HttpError(413, 'quota_exceeded');
  if (f && !await DB.prepare('SELECT 1 FROM workshop_folders WHERE owner_id=? AND path=?').bind(uid, f).first()) {
    if (!ensureFolder) throw new HttpError(404, 'folder_not_found');
    await workshopEnsureFolder(env, uid, f, t, {HttpError});
  }
  const k = kindOf(kind) || 'file';
  const taken = async n => !!(await DB.prepare('SELECT 1 FROM workshop_files WHERE owner_id=? AND folder=? AND name=?').bind(uid, f, n).first());
  let finalName = cleanName(name, ext);
  if (await taken(finalName)) {
    const dot = finalName.lastIndexOf('.'), base = finalName.slice(0, dot), tail = finalName.slice(dot);
    let i = 2;
    for (; i < 100; i++) { const n = `${base} (${i})${tail}`; if (!await taken(n)) { finalName = n; break; } }
    if (i >= 100) throw new HttpError(409, 'name_taken');
  }
  const id = crypto.randomUUID().replace(/-/g, ''), key = `${WORKSHOP_PREFIX}${uid}/${id}`, mime = WORKSHOP_TYPES[ext].mime;
  await env.LAB_PAGES.put(key, bytes, {httpMetadata: {contentType: mime}, customMetadata: {owner: String(uid)}});
  let row;
  try {
    /* the quota is checked again in the insert itself, so two uploads at once cannot both pass it */
    row = await DB.prepare(`INSERT INTO workshop_files(id,owner_id,folder,name,size,mime,r2_key,created_at,updated_at,kind)
      SELECT ?,?,?,?,?,?,?,?,?,? WHERE (SELECT COALESCE(SUM(size),0) FROM workshop_files WHERE owner_id=?)+?<=? RETURNING ${COLS}`)
      .bind(id, uid, f, finalName, bytes.length, mime, key, t, t, k, uid, bytes.length, limits.quota).first();
  } catch (e) { await env.LAB_PAGES.delete(key).catch(() => {}); throw e; }
  if (!row) { await env.LAB_PAGES.delete(key).catch(() => {}); throw new HttpError(413, 'quota_exceeded'); }
  return {file: fileView(row), used: u.n + bytes.length, ...limits};
}
const fileView = r => ({id: r.id, folder: r.folder, name: r.name, size: r.size, mime: r.mime, kind: r.kind || 'file', created_at: r.created_at, updated_at: r.updated_at});

/* a folder (and the folders above it) made when it is not there yet: the apps save into "시험지", "시뮬레이션" … by name */
export async function workshopEnsureFolder(env, uid, path, t, {HttpError}) {
  await ensureWorkshopSchema(env);
  const p = cleanFolder(path);
  if (p == null) throw new HttpError(400, 'bad_folder');
  if (!p) return '';
  const add = [];
  for (const a of ancestors(p)) if (!await env.DB.prepare('SELECT 1 FROM workshop_folders WHERE owner_id=? AND path=?').bind(uid, a).first()) add.push(a);
  if (!add.length) return p;
  const n = (await env.DB.prepare('SELECT COUNT(*) AS n FROM workshop_folders WHERE owner_id=?').bind(uid).first())?.n || 0;
  if (n + add.length > FOLDERS_MAX) throw new HttpError(409, 'too_many_folders');
  for (const a of add) await env.DB.prepare('INSERT OR IGNORE INTO workshop_folders(owner_id,path,created_at) VALUES(?,?,?)').bind(uid, a, t).run();
  return p;
}

/* new bytes for one of the member's files, in place: same id, name and folder. The type is the file's own (its
   extension); the first bytes are checked against it; the quota is checked with the size difference inside the
   UPDATE, so two saves at once cannot both pass it. Members over quota can still replace a file without increasing its size.
   The bytes go to a fresh R2 key and the old object goes only
   after the row has moved to the new one, so a failed save leaves the old file whole. base: the updated_at the
   caller last saw (optional): a file saved since is refused with 409 changed. */
export async function workshopReplaceBytes(env, uid, id, {bytes, kind = null, base = null}, {HttpError, now}) {
  await ensureWorkshopSchema(env);
  const DB = env.DB, t = now();
  if (!ID.test(String(id || ''))) throw new HttpError(404, 'not_found');
  const row = await DB.prepare(`SELECT ${COLS},r2_key FROM workshop_files WHERE id=? AND owner_id=?`).bind(id, uid).first();
  if (!row) throw new HttpError(404, 'not_found');
  if (!env.LAB_PAGES) throw new HttpError(503, 'r2_unavailable');
  const ext = extOf(row.name);
  if (!WORKSHOP_TYPES[ext]) throw new HttpError(415, 'type_not_allowed');
  if (!bytes?.length) throw new HttpError(400, 'file_required');
  if (bytes.length > WORKSHOP_MAX_FILE) throw new HttpError(413, 'file_too_large');
  if (!contentMatches(ext, bytes)) throw new HttpError(415, 'type_mismatch');
  if (base != null && Number(base) !== row.updated_at) throw new HttpError(409, 'changed');
  const k = kindOf(kind);
  if (kind != null && kind !== '' && !k) throw new HttpError(400, 'bad_kind');
  const limits = await storageLimits(env, uid, t);
  if (bytes.length > Math.max(limits.max_file, row.size)) throw new HttpError(413, 'file_too_large');
  const rev = crypto.randomUUID().replace(/-/g, '').slice(0, 12), key = `${WORKSHOP_PREFIX}${uid}/${row.id}-${rev}`, mime = WORKSHOP_TYPES[ext].mime;
  await env.LAB_PAGES.put(key, bytes, {httpMetadata: {contentType: mime}, customMetadata: {owner: String(uid)}});
  let r;
  /* a second save in the same second still moves updated_at on, so base always tells two versions apart */
  const stamp = Math.max(t, row.updated_at + 1);
  try {
    r = await DB.prepare(`UPDATE workshop_files SET size=?,r2_key=?,updated_at=?,kind=COALESCE(?,kind)
      WHERE id=? AND owner_id=? AND r2_key=?
        AND (?<=size OR (SELECT COALESCE(SUM(size),0) FROM workshop_files WHERE owner_id=?)-size+?<=?) RETURNING ${COLS}`)
      .bind(bytes.length, key, stamp, k, row.id, uid, row.r2_key, bytes.length, uid, bytes.length, limits.quota).first();
  } catch (e) { await env.LAB_PAGES.delete(key).catch(() => {}); throw e; }
  if (!r) {
    await env.LAB_PAGES.delete(key).catch(() => {});
    const now2 = await DB.prepare('SELECT r2_key FROM workshop_files WHERE id=? AND owner_id=?').bind(row.id, uid).first();
    if (!now2) throw new HttpError(404, 'not_found');
    if (now2.r2_key !== row.r2_key) throw new HttpError(409, 'changed');
    throw new HttpError(413, 'quota_exceeded');
  }
  await env.LAB_PAGES.delete(row.r2_key).catch(() => {});
  const u = (await DB.prepare('SELECT COALESCE(SUM(size),0) AS n FROM workshop_files WHERE owner_id=?').bind(uid).first()) || {n: 0};
  return {file: fileView(r), used: u.n, ...limits};
}
/* one of the member's files and its bytes (owner only), for the connectors' copy out of storage */
export async function workshopReadBytes(env, uid, id, {HttpError}) {
  await ensureWorkshopSchema(env);
  if (!ID.test(String(id || ''))) throw new HttpError(404, 'not_found');
  const row = await env.DB.prepare(`SELECT ${COLS},r2_key FROM workshop_files WHERE id=? AND owner_id=?`).bind(id, uid).first();
  if (!row) throw new HttpError(404, 'not_found');
  if (!env.LAB_PAGES) throw new HttpError(503, 'r2_unavailable');
  const obj = await env.LAB_PAGES.get(row.r2_key);
  if (!obj) throw new HttpError(404, 'file_missing');
  const bytes = new Uint8Array(await (obj.arrayBuffer ? obj.arrayBuffer() : new Response(obj.body).arrayBuffer()));
  return {name: row.name, mime: row.mime, folder: row.folder, bytes};
}

export function createWorkshopStorageRouter({HttpError, needUser, limit, now, bad}) {
  const folderOf = v => { const f = cleanFolder(v); return f == null ? bad('bad_folder') : f; };
  const used = async (DB, uid) => (await DB.prepare('SELECT COALESCE(SUM(size),0) AS n, COUNT(*) AS c FROM workshop_files WHERE owner_id=?').bind(uid).first()) || {n: 0, c: 0};
  const folderExists = async (DB, uid, f) => !f || !!(await DB.prepare('SELECT 1 FROM workshop_folders WHERE owner_id=? AND path=?').bind(uid, f).first());
  const nameTaken = async (DB, uid, f, name, selfId = '') => !!(await DB.prepare('SELECT 1 FROM workshop_files WHERE owner_id=? AND folder=? AND name=? AND id<>?').bind(uid, f, name, selfId).first());
  async function makeFolders(DB, uid, path, t) {
    const n = (await DB.prepare('SELECT COUNT(*) AS n FROM workshop_folders WHERE owner_id=?').bind(uid).first())?.n || 0;
    const add = ancestors(path);
    if (n + add.length > FOLDERS_MAX) throw new HttpError(409, 'too_many_folders');
    for (const p of add) await DB.prepare('INSERT OR IGNORE INTO workshop_folders(owner_id,path,created_at) VALUES(?,?,?)').bind(uid, p, t).run();
  }
  const own = async (DB, uid, id) => {
    if (!ID.test(id)) throw new HttpError(404, 'not_found');
    const r = await DB.prepare(`SELECT ${COLS},r2_key FROM workshop_files WHERE id=? AND owner_id=?`).bind(id, uid).first();
    if (!r) throw new HttpError(404, 'not_found');
    return r;
  };
  const view = fileView;
  const shared = classStorageRoutes({HttpError, limit, bad, cleanFolder, fileView, download});

  async function download(env, row, method, transform = null) {
    if (!env.LAB_PAGES) throw new HttpError(503, 'r2_unavailable');
    const obj = await env.LAB_PAGES.get(row.r2_key);
    if (!obj) throw new HttpError(404, 'file_missing');
    const headers = {
      'Content-Type': row.mime,
      'Content-Disposition': `attachment; filename="${asciiName(row.name)}"; filename*=UTF-8''${encodeURIComponent(row.name)}`,
      'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer',
      'Content-Security-Policy': "default-src 'none'; sandbox", 'X-Frame-Options': 'DENY'
    };
    if (transform) {
      if (method === 'HEAD') return new Response(null, {headers});
      if (row.size > 5 * 1024 * 1024) throw new HttpError(413, 'file_too_large');
      const body = await new Response(obj.body).json().then(transform).catch(() => null);
      if (!body) throw new HttpError(415, 'bad_worksheet');
      return new Response(JSON.stringify(body), {headers});
    }
    if (obj.size != null) headers['Content-Length'] = String(obj.size);
    return new Response(method === 'HEAD' ? null : obj.body, {headers});
  }

  async function readUpload(req) {
    const declared = Number(req?.headers?.get?.('Content-Length') || 0);
    if (declared > WORKSHOP_MAX_FILE + 64 * 1024) throw new HttpError(413, 'file_too_large');
    if (!(req?.headers?.get?.('Content-Type') || '').startsWith('multipart/form-data')) bad('bad_form');
    let form;
    try { form = await req.formData(); } catch { bad('bad_form'); }
    const file = form.get('file');
    if (!file || typeof file === 'string' || typeof file.arrayBuffer !== 'function') bad('file_required');
    if (file.size > WORKSHOP_MAX_FILE) throw new HttpError(413, 'file_too_large');
    const ext = extOf(String(file.name || ''));
    if (!WORKSHOP_TYPES[ext]) throw new HttpError(415, 'type_not_allowed');
    const bytes = new Uint8Array(await file.arrayBuffer());
    if (!bytes.length) bad('file_required');
    if (bytes.length > WORKSHOP_MAX_FILE) throw new HttpError(413, 'file_too_large');
    if (!contentMatches(ext, bytes)) throw new HttpError(415, 'type_mismatch');
    const folder = form.get('folder'), kind = form.get('kind');
    if (kind != null && kind !== '' && !kindOf(kind)) bad('bad_kind');
    return {bytes, ext, name: cleanName(file.name, ext), folder: folderOf(typeof folder === 'string' ? folder : ''), kind: kindOf(kind) || 'file', ensureFolder: form.get('ensure_folder') === '1'};
  }
  /* the body of PUT …/content: a multipart "file" (and "kind", "base"), or the bytes themselves (?kind, ?base) */
  async function readContent(req) {
    const declared = Number(req?.headers?.get?.('Content-Length') || 0);
    if (declared > WORKSHOP_MAX_FILE + 64 * 1024) throw new HttpError(413, 'file_too_large');
    const url = req?.url ? new URL(req.url) : null;
    if ((req?.headers?.get?.('Content-Type') || '').startsWith('multipart/form-data')) {
      let form;
      try { form = await req.formData(); } catch { bad('bad_form'); }
      const file = form.get('file');
      if (!file || typeof file === 'string' || typeof file.arrayBuffer !== 'function') bad('file_required');
      if (file.size > WORKSHOP_MAX_FILE) throw new HttpError(413, 'file_too_large');
      const kind = form.get('kind'), base = form.get('base');
      return {bytes: new Uint8Array(await file.arrayBuffer()), fname: String(file.name || ''), kind: typeof kind === 'string' && kind ? kind : null, base: typeof base === 'string' && base ? base : null};
    }
    let buf;
    try { buf = await req.arrayBuffer(); } catch { bad('bad_body'); }
    return {bytes: new Uint8Array(buf), fname: '', kind: url?.searchParams.get('kind') || null, base: url?.searchParams.get('base') || null};
  }

  return async function workshopStorageRoute(p, m, body, me, req, env) {
    if (p !== '/api/workshop/storage' && !p.startsWith('/api/workshop/storage/')) return undefined;
    needUser(me);
    await ensureWorkshopSchema(env);
    const DB = env.DB, t = now(), uid = me.id;
    if (p === '/api/workshop/storage/shared' || p.startsWith('/api/workshop/storage/shared/')) return shared(p, m, body, uid, t, env);

    if (p === '/api/workshop/storage' && m === 'GET') {
      const url = req?.url ? new URL(req.url) : null, qk = url?.searchParams.get('kind'), qf = url?.searchParams.get('folder');
      if (qk != null && !kindOf(qk)) bad('bad_kind');
      const where = ['owner_id=?'], args = [uid];
      if (qk != null) { where.push('kind=?'); args.push(qk); }
      if (qf != null) { where.push('folder=?'); args.push(folderOf(qf)); }
      const order = qk != null || qf != null ? 'updated_at DESC, name' : 'folder, name';
      const files = (await DB.prepare(`SELECT ${COLS} FROM workshop_files WHERE ${where.join(' AND ')} ORDER BY ${order} LIMIT ${FILES_MAX}`).bind(...args).all()).results || [];
      const folders = ((await DB.prepare('SELECT path FROM workshop_folders WHERE owner_id=? ORDER BY path').bind(uid).all()).results || []).map(r => r.path);
      const [u, limits] = await Promise.all([used(DB, uid), storageLimits(env, uid, t)]);
      return {files: files.map(view), folders, used: u.n, ...limits, types: Object.keys(WORKSHOP_TYPES)};
    }

    if (p === '/api/workshop/storage/files' && m === 'POST') {
      await limit(env, 'ws-up:' + uid, 120, 3600);
      if (!env.LAB_PAGES) throw new HttpError(503, 'r2_unavailable');
      const {bytes, name, folder, kind, ensureFolder} = await readUpload(req);
      return workshopSaveBytes(env, uid, {bytes, name, folder, kind, ensureFolder}, {HttpError, now: () => t});
    }

    if (p === '/api/workshop/storage/folders') {
      if (m === 'POST') {
        await limit(env, 'ws-edit:' + uid, 300, 3600);
        const path = folderOf(body?.path);
        if (!path) bad('bad_folder');
        await makeFolders(DB, uid, path, t);
        return {path};
      }
      if (m === 'PATCH') {
        await limit(env, 'ws-edit:' + uid, 300, 3600);
        const from = folderOf(body?.path), to = folderOf(body?.to);
        if (!from || !to) bad('bad_folder');
        if (from === to) return {path: to};
        if (to.startsWith(from + '/')) bad('folder_into_itself');
        if (!await folderExists(DB, uid, from)) throw new HttpError(404, 'folder_not_found');
        if (await folderExists(DB, uid, to)) throw new HttpError(409, 'folder_exists');
        const deepest = ((await DB.prepare("SELECT path FROM workshop_folders WHERE owner_id=? AND (path=? OR substr(path,1,?)=?)").bind(uid, from, from.length + 1, from + '/').all()).results || []).map(r => r.path);
        for (const f of deepest) if (cleanFolder(to + f.slice(from.length)) !== to + f.slice(from.length)) bad('bad_folder');
        const parent = to.includes('/') ? to.slice(0, to.lastIndexOf('/')) : '';
        if (parent) await makeFolders(DB, uid, parent, t);
        const n = from.length;
        await DB.prepare("UPDATE workshop_folders SET path=?||substr(path,?) WHERE owner_id=? AND (path=? OR substr(path,1,?)=?)").bind(to, n + 1, uid, from, n + 1, from + '/').run();
        await DB.prepare("UPDATE workshop_files SET folder=?||substr(folder,?),updated_at=? WHERE owner_id=? AND (folder=? OR substr(folder,1,?)=?)").bind(to, n + 1, t, uid, from, n + 1, from + '/').run();
        return {path: to};
      }
      if (m === 'DELETE') {
        const url = req?.url ? new URL(req.url) : null;
        const path = folderOf(url?.searchParams.get('path') ?? '');
        if (!path) bad('bad_folder');
        if (!await folderExists(DB, uid, path)) throw new HttpError(404, 'folder_not_found');
        const inside = await DB.prepare("SELECT 1 FROM workshop_files WHERE owner_id=? AND (folder=? OR substr(folder,1,?)=?) LIMIT 1").bind(uid, path, path.length + 1, path + '/').first()
          || await DB.prepare("SELECT 1 FROM workshop_folders WHERE owner_id=? AND substr(path,1,?)=? LIMIT 1").bind(uid, path.length + 1, path + '/').first();
        if (inside) throw new HttpError(409, 'folder_not_empty');
        await DB.prepare('DELETE FROM workshop_folders WHERE owner_id=? AND path=?').bind(uid, path).run();
        return {ok: true};
      }
      throw new HttpError(404, 'not_found');
    }

    const mc = /^\/api\/workshop\/storage\/files\/([^/]+)\/content$/.exec(p);
    if (mc) {
      if (m !== 'PUT') throw new HttpError(405, 'method_not_allowed');
      await limit(env, 'ws-up:' + uid, 120, 3600);
      await own(DB, uid, mc[1]);
      const c = await readContent(req);
      const row = await own(DB, uid, mc[1]);
      const fx = extOf(c.fname);
      if (fx && fx !== extOf(row.name)) throw new HttpError(415, 'type_change');
      return workshopReplaceBytes(env, uid, row.id, {bytes: c.bytes, kind: c.kind, base: c.base}, {HttpError, now: () => t});
    }
    const mm = /^\/api\/workshop\/storage\/files\/([^/]+)$/.exec(p);
    if (!mm) throw new HttpError(404, 'not_found');
    const row = await own(DB, uid, mm[1]);

    if (m === 'GET' || m === 'HEAD') {
      await limit(env, 'ws-down:' + uid, 600, 3600);
      return download(env, row, m);
    }

    if (m === 'PATCH') {
      await limit(env, 'ws-edit:' + uid, 300, 3600);
      const b = body || {};
      if (!('name' in b) && !('folder' in b) && !('kind' in b)) bad('nothing_to_change');
      if ('kind' in b && !kindOf(b.kind)) bad('bad_kind');
      const ext = extOf(row.name);
      let name = row.name, folder = row.folder;
      if ('name' in b) {
        if (typeof b.name !== 'string' || !b.name.trim()) bad('bad_name');
        name = cleanName(b.name, ext);
      }
      if ('folder' in b) {
        folder = folderOf(b.folder);
        if (!await folderExists(DB, uid, folder)) throw new HttpError(404, 'folder_not_found');
      }
      if (await nameTaken(DB, uid, folder, name, row.id)) throw new HttpError(409, 'name_taken');
      const r = await DB.prepare(`UPDATE workshop_files SET name=?,folder=?,kind=?,updated_at=? WHERE id=? AND owner_id=? RETURNING ${COLS}`).bind(name, folder, 'kind' in b ? b.kind : row.kind || 'file', Math.max(t, row.updated_at), row.id, uid).first();
      if (!r) throw new HttpError(404, 'not_found');
      return {file: view(r)};
    }

    if (m === 'DELETE') {
      if (env.LAB_PAGES) await env.LAB_PAGES.delete(row.r2_key);
      await DB.prepare('DELETE FROM workshop_files WHERE id=? AND owner_id=?').bind(row.id, uid).run();
      return {ok: true};
    }
    throw new HttpError(404, 'not_found');
  };
}
