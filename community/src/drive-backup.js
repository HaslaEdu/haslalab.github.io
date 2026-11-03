/* Weekly backup to the owner's Google Drive.
   Secrets (Worker): GDRIVE_CLIENT_ID, GDRIVE_CLIENT_SECRET, GDRIVE_REFRESH_TOKEN, an OAuth refresh token for the scope
   drive.file, so the backup sees and changes only the files it made itself. BACKUP_DRIVE = "off" stops it.
   Drive: «HaslaLab backup»/db holds one gzipped SQL dump a week (the newest BACKUP_KEEP_DUMPS, 8 unless set, are kept);
   «HaslaLab backup»/photos holds each answer photo once, and a photo leaves it when its page or the photo itself is gone
   from the site (purged, deleted), so the copy never outlives what the site keeps.
   The minute cron drives a run in steps (backup_runs.phase db → photos → prune → done), each step short and leased, so
   no single invocation holds hundreds of photos or runs into the time limit. A run starts on Sunday 18:00 UTC (Monday
   03:00 KST), when no one sits an exam, or at once from the admin bench ({stage:'backup'}). */

const SCHEMA = [
  `CREATE TABLE IF NOT EXISTS backup_runs (id INTEGER PRIMARY KEY AUTOINCREMENT, started_at INTEGER NOT NULL, phase TEXT NOT NULL DEFAULT 'db',
    lease_until INTEGER, done_at INTEGER, error TEXT, stats TEXT NOT NULL DEFAULT '{}')`,
  `CREATE TABLE IF NOT EXISTS backup_photos (page_id INTEGER PRIMARY KEY, drive_id TEXT NOT NULL, bytes INTEGER NOT NULL, at INTEGER NOT NULL)`,
  `CREATE TABLE IF NOT EXISTS backup_kv (k TEXT PRIMARY KEY, v TEXT NOT NULL)`,
];
const FOLDER = 'application/vnd.google-apps.folder', API = 'https://www.googleapis.com', MULTIPART_MAX = 4 * 1024 * 1024;
const LEASE = 300, MAX_FAILS = 10, DUMP_MAX = 80 * 1024 * 1024;
const sec = ms => Math.floor(ms / 1000);

export function backupConfigured(env) {
  return env.BACKUP_DRIVE !== 'off' && !!(env.GDRIVE_CLIENT_ID && env.GDRIVE_CLIENT_SECRET && env.GDRIVE_REFRESH_TOKEN);
}
/* the weekly slot: Sunday 18:00-18:59 UTC */
export function backupDue(ms) { const d = new Date(ms); return d.getUTCDay() === 0 && d.getUTCHours() === 18; }

const ready = new WeakMap();
async function ensure(db) {
  if (!ready.has(db)) ready.set(db, db.batch(SCHEMA.map(s => db.prepare(s))).catch(e => { ready.delete(db); throw e; }));
  await ready.get(db);
}

/* ---- Google Drive ---- */
let cached = null;
export async function driveToken(env, { fetchImpl = globalThis.fetch, now = Date.now() } = {}) {
  if (cached && cached.key === env.GDRIVE_REFRESH_TOKEN && cached.exp > now + 60000) return cached.token;
  const r = await fetchImpl('https://oauth2.googleapis.com/token', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ client_id: env.GDRIVE_CLIENT_ID, client_secret: env.GDRIVE_CLIENT_SECRET, refresh_token: env.GDRIVE_REFRESH_TOKEN, grant_type: 'refresh_token' }).toString() });
  const j = await r.json().catch(() => ({}));
  if (!r.ok || !j.access_token) throw new Error('drive_token_' + r.status + ':' + String(j.error || '').slice(0, 60));
  cached = { key: env.GDRIVE_REFRESH_TOKEN, token: j.access_token, exp: now + (+j.expires_in || 3600) * 1000 };
  return j.access_token;
}
async function driveFail(r, what) {
  const t = await r.text().catch(() => '');
  throw Object.assign(new Error(`drive_${what}_${r.status}:${t.slice(0, 160)}`), { status: r.status });
}
const q = s => "'" + String(s).replace(/\\/g, '\\\\').replace(/'/g, "\\'") + "'";
async function driveFind(token, name, parent, fetchImpl) {
  const query = `name=${q(name)} and mimeType=${q(FOLDER)} and trashed=false and ${q(parent || 'root')} in parents`;
  const r = await fetchImpl(`${API}/drive/v3/files?q=${encodeURIComponent(query)}&fields=files(id)&pageSize=1`, { headers: { Authorization: 'Bearer ' + token } });
  if (!r.ok) await driveFail(r, 'find');
  return (await r.json()).files?.[0]?.id || null;
}
async function driveMkdir(token, name, parent, fetchImpl) {
  const r = await fetchImpl(`${API}/drive/v3/files?fields=id`, { method: 'POST', headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, mimeType: FOLDER, ...(parent ? { parents: [parent] } : {}) }) });
  if (!r.ok) await driveFail(r, 'mkdir');
  return (await r.json()).id;
}
/* one file into a folder: a single multipart request up to 4 MB, a resumable upload (one PUT) above */
export async function driveUpload(token, { name, parent, mime, bytes }, fetchImpl = globalThis.fetch) {
  const meta = JSON.stringify({ name, parents: [parent] });
  if (bytes.byteLength <= MULTIPART_MAX) {
    const b = 'hasla' + crypto.randomUUID().replace(/-/g, ''), enc = new TextEncoder();
    const head = enc.encode(`--${b}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n${meta}\r\n--${b}\r\nContent-Type: ${mime}\r\n\r\n`), tail = enc.encode(`\r\n--${b}--`);
    const body = new Uint8Array(head.length + bytes.byteLength + tail.length);
    body.set(head); body.set(new Uint8Array(bytes.buffer ?? bytes, bytes.byteOffset || 0, bytes.byteLength), head.length); body.set(tail, head.length + bytes.byteLength);
    const r = await fetchImpl(`${API}/upload/drive/v3/files?uploadType=multipart&fields=id`, { method: 'POST',
      headers: { Authorization: 'Bearer ' + token, 'Content-Type': `multipart/related; boundary=${b}` }, body });
    if (!r.ok) await driveFail(r, 'upload');
    return (await r.json()).id;
  }
  const s = await fetchImpl(`${API}/upload/drive/v3/files?uploadType=resumable&fields=id`, { method: 'POST',
    headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json; charset=UTF-8', 'X-Upload-Content-Type': mime, 'X-Upload-Content-Length': String(bytes.byteLength) }, body: meta });
  if (!s.ok) await driveFail(s, 'upload');
  const loc = s.headers.get('Location'); if (!loc) throw new Error('drive_upload_no_session');
  const r = await fetchImpl(loc, { method: 'PUT', headers: { 'Content-Type': mime }, body: bytes });
  if (!r.ok) await driveFail(r, 'upload');
  return (await r.json()).id;
}
async function driveDelete(token, id, fetchImpl) {
  const r = await fetchImpl(`${API}/drive/v3/files/${encodeURIComponent(id)}`, { method: 'DELETE', headers: { Authorization: 'Bearer ' + token } });
  if (!r.ok && r.status !== 404) await driveFail(r, 'delete');
}
async function driveList(token, parent, fetchImpl) {
  const query = `${q(parent)} in parents and trashed=false`;
  const r = await fetchImpl(`${API}/drive/v3/files?q=${encodeURIComponent(query)}&orderBy=createdTime%20desc&fields=files(id,name,createdTime)&pageSize=100`, { headers: { Authorization: 'Bearer ' + token } });
  if (!r.ok) await driveFail(r, 'list');
  return (await r.json()).files || [];
}
/* «HaslaLab backup», its db and photos folders: found or made once, their ids kept in backup_kv */
async function folders(db, token, fetchImpl) {
  const kv = Object.fromEntries((await db.prepare("SELECT k,v FROM backup_kv WHERE k IN ('root','db','photos')").all()).results.map(r => [r.k, r.v]));
  if (kv.root && kv.db && kv.photos) return kv;
  const root = kv.root || await driveFind(token, 'HaslaLab backup', null, fetchImpl) || await driveMkdir(token, 'HaslaLab backup', null, fetchImpl);
  const out = { root };
  for (const k of ['db', 'photos']) out[k] = kv[k] || await driveFind(token, k, root, fetchImpl) || await driveMkdir(token, k, root, fetchImpl);
  await db.batch(Object.entries(out).map(([k, v]) => db.prepare('INSERT OR REPLACE INTO backup_kv(k,v) VALUES(?,?)').bind(k, v)));
  return out;
}

/* ---- the SQL dump ---- */
const ident = s => '"' + String(s).replace(/"/g, '""') + '"';
const hex = b => { const u = b instanceof Uint8Array ? b : new Uint8Array(b); let s = ''; for (let i = 0; i < u.length; i++) s += (u[i] < 16 ? '0' : '') + u[i].toString(16); return s; };
function literal(v) {
  if (v === null || v === undefined) return 'NULL';
  if (typeof v === 'number') return Number.isFinite(v) ? String(v) : 'NULL';
  if (typeof v === 'bigint') return String(v);
  if (typeof v === 'string') return "'" + v.replace(/'/g, "''") + "'";
  if (v instanceof ArrayBuffer || ArrayBuffer.isView(v) || Array.isArray(v)) return "X'" + hex(Array.isArray(v) ? Uint8Array.from(v) : ArrayBuffer.isView(v) ? new Uint8Array(v.buffer, v.byteOffset, v.byteLength) : v) + "'";
  return "'" + String(v).replace(/'/g, "''") + "'";
}
/* Every table but SQLite's and D1's own, as statements sqlite3 or `wrangler d1 execute --file` can load into an empty
   database: the tables, their rows, then indexes, views and triggers. Answer photos are not in it (they go to the
   photos folder): an image page's data is written empty, as it is once the photo is in R2. */
export async function dumpDatabase(db, { at = Date.now() } = {}) {
  const objs = (await db.prepare(`SELECT type,name,tbl_name,sql FROM sqlite_master WHERE sql IS NOT NULL
    AND substr(name,1,7)<>'sqlite_' AND substr(name,1,4)<>'_cf_' AND substr(tbl_name,1,4)<>'_cf_' ORDER BY type='table' DESC, rowid`).all()).results;
  const cs = new CompressionStream('gzip'), w = cs.writable.getWriter(), done = new Response(cs.readable).arrayBuffer(), enc = new TextEncoder();
  let pending = '', size = 0;
  const put = async line => { pending += line + '\n'; if (pending.length > 1 << 20) { size += pending.length; await w.write(enc.encode(pending)); pending = ''; } };
  await put(`-- HaslaLab database dump, ${new Date(at).toISOString()}`);
  await put('PRAGMA foreign_keys=OFF;');
  const tables = {};
  for (const o of objs.filter(o => o.type === 'table')) {
    await put(o.sql + ';');
    const cols = (await db.prepare(`PRAGMA table_info(${ident(o.name)})`).all()).results;
    const blobby = cols.some(c => /BLOB/i.test(c.type || '')), page = blobby ? 20 : 200;
    const select = cols.map(c => o.name === 'lab_pages' && c.name === 'data' ? `CASE WHEN mime='text/plain' THEN data ELSE X'' END AS data` : ident(c.name)).join(',');
    const insert = `INSERT INTO ${ident(o.name)}(${cols.map(c => ident(c.name)).join(',')}) VALUES(`;
    let last = null, n = 0, rowid = !/WITHOUT\s+ROWID/i.test(o.sql);
    for (;;) {
      const rows = rowid
        ? (await db.prepare(`SELECT rowid AS __hasla_rowid,${select} FROM ${ident(o.name)}${last === null ? '' : ' WHERE rowid>?'} ORDER BY rowid LIMIT ${page}`).bind(...(last === null ? [] : [last])).all()).results
        : (await db.prepare(`SELECT ${select} FROM ${ident(o.name)} LIMIT ${page} OFFSET ${n}`).all()).results;
      for (const r of rows) await put(insert + cols.map(c => literal(r[c.name])).join(',') + ');');
      n += rows.length;
      if (rows.length < page) break;
      if (rowid) last = rows[rows.length - 1].__hasla_rowid;
      if (size > DUMP_MAX * 4) throw new Error('dump_too_large');
    }
    tables[o.name] = n;
  }
  for (const o of objs.filter(o => o.type !== 'table')) await put(o.sql + ';');
  size += pending.length; if (pending) await w.write(enc.encode(pending));
  await w.close();
  const bytes = new Uint8Array(await done);
  if (bytes.byteLength > DUMP_MAX) throw new Error('dump_too_large');
  return { bytes, tables, sql_bytes: size };
}

/* ---- the steps ---- */
const ext = mime => ({ 'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp', 'image/heic': 'heic', 'application/pdf': 'pdf' })[mime] || 'bin';
async function photoBytes(env, p) {
  if (p.r2_key) { const o = env.LAB_PAGES ? await env.LAB_PAGES.get(p.r2_key) : null; return o ? new Uint8Array(await o.arrayBuffer()) : null; }
  const row = await env.DB.prepare('SELECT data FROM lab_pages WHERE id=?').bind(p.id).first(), d = row?.data;
  const n = d ? (d.byteLength ?? d.length) : 0;
  return n ? new Uint8Array(d) : null;
}
async function step(env, run, stats, { fetchImpl, now, photosPerStep, budgetMs }) {
  const db = env.DB, token = await driveToken(env, { fetchImpl, now }), dirs = await folders(db, token, fetchImpl), t0 = Date.now();
  if (run.phase === 'db') {
    const d = await dumpDatabase(db, { at: now }), name = `haslalab-${new Date(now).toISOString().slice(0, 10)}-run${run.id}.sql.gz`;
    const id = await driveUpload(token, { name, parent: dirs.db, mime: 'application/gzip', bytes: d.bytes }, fetchImpl);
    stats.db = { name, id, bytes: d.bytes.byteLength, sql_bytes: d.sql_bytes, rows: Object.values(d.tables).reduce((a, b) => a + b, 0), tables: Object.keys(d.tables).length };
    return 'photos';
  }
  if (run.phase === 'photos') {
    const list = (await db.prepare(`SELECT p.id, p.session_id, p.mime, p.r2_key FROM lab_pages p LEFT JOIN backup_photos b ON b.page_id=p.id
      WHERE b.page_id IS NULL AND p.mime<>'text/plain' AND p.purged_at IS NULL AND (p.r2_key IS NOT NULL OR length(p.data)>0) ORDER BY p.id LIMIT ?`).bind(photosPerStep).all()).results;
    if (!list.length) return 'prune';
    const s = stats.photos ||= { copied: 0, bytes: 0, missing: 0 };
    for (const p of list) {
      if (Date.now() - t0 > budgetMs) break;
      const bytes = await photoBytes(env, p);
      /* a photo the site no longer has is noted, so it is not asked for again every week */
      const id = bytes ? await driveUpload(token, { name: `s${p.session_id}-p${p.id}.${ext(p.mime)}`, parent: dirs.photos, mime: p.mime, bytes }, fetchImpl) : 'missing';
      await db.prepare('INSERT OR REPLACE INTO backup_photos(page_id,drive_id,bytes,at) VALUES(?,?,?,?)').bind(p.id, id, bytes ? bytes.byteLength : 0, sec(now)).run();
      if (bytes) { s.copied++; s.bytes += bytes.byteLength; } else s.missing++;
    }
    return 'photos';
  }
  if (run.phase === 'prune') {
    const gone = (await db.prepare(`SELECT b.page_id, b.drive_id FROM backup_photos b LEFT JOIN lab_pages p ON p.id=b.page_id
      WHERE p.id IS NULL OR p.purged_at IS NOT NULL LIMIT 50`).all()).results;
    const s = stats.pruned ||= { photos: 0, dumps: 0 };
    for (const g of gone) {
      if (g.drive_id !== 'missing') await driveDelete(token, g.drive_id, fetchImpl);
      await db.prepare('DELETE FROM backup_photos WHERE page_id=?').bind(g.page_id).run();
      s.photos++;
    }
    if (gone.length === 50) return 'prune';
    const keep = Math.max(1, Number.parseInt(env.BACKUP_KEEP_DUMPS, 10) || 8);
    for (const f of (await driveList(token, dirs.db, fetchImpl)).slice(keep)) { await driveDelete(token, f.id, fetchImpl); s.dumps++; }
    return 'done';
  }
  return 'done';
}

/* One step of the backup; the cron calls it every minute (start: only in the weekly slot, unless forced). */
export async function backupTick(env, { now = Date.now(), force = false, fetchImpl = globalThis.fetch, photosPerStep = 40, budgetMs = 40000 } = {}) {
  if (!backupConfigured(env)) return force ? { error: 'drive_not_configured' } : null;
  const db = env.DB; await ensure(db);
  let run = await db.prepare('SELECT * FROM backup_runs WHERE done_at IS NULL ORDER BY id DESC LIMIT 1').first();
  if (!run) {
    if (!force && !backupDue(now)) return null;
    /* one run a week: a slot that already has one (or a forced run in the last six days) starts nothing */
    const res = await db.prepare(`INSERT INTO backup_runs(started_at) SELECT ? WHERE NOT EXISTS (SELECT 1 FROM backup_runs WHERE started_at>? OR done_at IS NULL)`)
      .bind(sec(now), force ? sec(now) - 60 : sec(now) - 6 * 86400).run();
    if (!res.meta?.changes) return null;
    run = await db.prepare('SELECT * FROM backup_runs WHERE done_at IS NULL ORDER BY id DESC LIMIT 1').first();
  }
  const claim = await db.prepare('UPDATE backup_runs SET lease_until=? WHERE id=? AND done_at IS NULL AND (lease_until IS NULL OR lease_until<?)').bind(sec(now) + LEASE, run.id, sec(now)).run();
  if (!claim.meta?.changes) return { run: run.id, busy: true };
  const stats = JSON.parse(run.stats || '{}');
  let phase = run.phase, error = null;
  try { phase = await step(env, run, stats, { fetchImpl, now, photosPerStep, budgetMs }); stats.fails = 0; }
  catch (e) {
    error = String(e?.message || e).slice(0, 300);
    stats.fails = (stats.fails || 0) + 1;
    /* a folder deleted by hand in Drive: found or made again on the next step */
    if (e?.status === 404) await db.prepare("DELETE FROM backup_kv WHERE k IN ('root','db','photos')").run();
    if (stats.fails >= MAX_FAILS) phase = 'failed';
  }
  const done = phase === 'done' || phase === 'failed';
  await db.prepare('UPDATE backup_runs SET phase=?,stats=?,error=?,lease_until=NULL,done_at=? WHERE id=?')
    .bind(phase, JSON.stringify(stats), error, done ? sec(now) : null, run.id).run();
  return { run: run.id, phase, error, stats };
}
