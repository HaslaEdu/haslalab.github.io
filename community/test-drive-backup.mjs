// node --test community/test-drive-backup.mjs
// The weekly Google Drive backup: a gzipped SQL dump that loads back into an empty database, each answer photo once,
// photos removed from Drive when the site lets them go, old dumps pruned, one run a week, leased steps.
import assert from "node:assert/strict";
import test from "node:test";
import { gunzipSync } from "node:zlib";
import { DatabaseSync } from "node:sqlite";
import { backupTick, backupDue, dumpDatabase } from "./src/drive-backup.js";

/* a D1-shaped wrapper over node:sqlite */
function d1(sql = new DatabaseSync(":memory:")) {
  const isRead = s => /^\s*(SELECT|PRAGMA|WITH)\b/i.test(s);
  const stmt = (s, args = []) => ({
    bind: (...a) => stmt(s, a),
    async all() { return { results: sql.prepare(s).all(...args).map(r => ({ ...r })) }; },
    async first() { const r = sql.prepare(s).get(...args); return r ? { ...r } : null; },
    async run() { const r = sql.prepare(s).run(...args); return { meta: { changes: Number(r.changes) } }; },
    exec() { return isRead(s) ? this.all() : this.run(); },
  });
  return { sql, prepare: s => stmt(s), batch: async list => Promise.all(list.map(x => x.exec())) };
}
function seed() {
  const db = d1();
  db.sql.exec(`CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT, note TEXT);
    CREATE TABLE lab_pages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, mime TEXT, data BLOB, r2_key TEXT, purged_at INTEGER);
    CREATE TABLE avatars (k TEXT PRIMARY KEY, data BLOB) WITHOUT ROWID;
    CREATE INDEX lab_pages_s ON lab_pages(session_id);
    CREATE VIEW v_users AS SELECT id FROM users;`);
  db.sql.prepare("INSERT INTO users VALUES (1, 'a@b.c', ?)").run("it's \"quoted\"\nline two");
  for (let i = 2; i <= 450; i++) db.sql.prepare("INSERT INTO users VALUES (?, ?, NULL)").run(i, `u${i}@x`);   // over two pages of 200
  const ins = db.sql.prepare("INSERT INTO lab_pages(session_id,mime,data,r2_key,purged_at) VALUES (?,?,?,?,?)");
  ins.run(7, "image/jpeg", new Uint8Array(0), "lab/7/a.jpg", null);           // 1: in R2
  ins.run(7, "image/jpeg", new Uint8Array([0xff, 0xd8, 9, 9, 0xff, 0xd9]), null, null);   // 2: still inline
  ins.run(7, "text/plain", new TextEncoder().encode("typed answer"), null, null);      // 3: a typed page
  ins.run(8, "image/jpeg", new Uint8Array(0), "lab/8/gone.jpg", 1700000000);   // 4: purged
  ins.run(8, "image/png", new Uint8Array(0), "lab/8/big.png", null);          // 5: a large photo (resumable upload)
  db.sql.prepare("INSERT INTO avatars VALUES ('k1', ?)").run(new Uint8Array([1, 2, 3]));
  return db;
}
const big = new Uint8Array(5 * 1024 * 1024).map((_, i) => i % 251);
function bucket() {
  const m = new Map([["lab/7/a.jpg", new Uint8Array([0xff, 0xd8, 1, 2, 3, 0xff, 0xd9])], ["lab/8/big.png", big]]);
  return { m, async get(k) { const v = m.get(k); return v ? { arrayBuffer: async () => v.slice().buffer } : null; } };
}
/* a Drive with folders, files, multipart and resumable uploads */
function drive() {
  const files = new Map(); let n = 0, sessions = new Map(), fail = null;
  const add = f => { const id = "f" + (++n); files.set(id, { id, createdTime: new Date(Date.UTC(2026, 0, 1, 0, 0, n)).toISOString(), ...f }); return id; };
  const json = (v, s = 200, h = {}) => new Response(JSON.stringify(v), { status: s, headers: { "Content-Type": "application/json", ...h } });
  const fetchImpl = async (url, init = {}) => {
    const u = new URL(url), method = init.method || "GET";
    if (fail && fail(u, method)) return json({ error: "boom" }, 500);
    if (u.host === "oauth2.googleapis.com") { const f = new URLSearchParams(init.body); assert.equal(f.get("grant_type"), "refresh_token"); assert.equal(f.get("refresh_token"), "rt"); return json({ access_token: "at", expires_in: 3600 }); }
    assert.equal(init.headers?.Authorization ?? "Bearer at", "Bearer at");
    if (u.pathname === "/drive/v3/files" && method === "GET") {
      const q = u.searchParams.get("q"), parent = /'([^']+)' in parents/.exec(q)[1], name = /name='([^']+)'/.exec(q)?.[1];
      let list = [...files.values()].filter(f => (f.parents?.[0] || "root") === parent && (!name || f.name === name) && (!/mimeType=/.test(q) || f.mimeType === "application/vnd.google-apps.folder"));
      list.sort((a, b) => b.createdTime.localeCompare(a.createdTime));
      return json({ files: list.map(({ id, name, createdTime }) => ({ id, name, createdTime })) });
    }
    if (u.pathname === "/drive/v3/files" && method === "POST") { const m = JSON.parse(init.body); return json({ id: add(m) }); }
    if (u.pathname.startsWith("/drive/v3/files/") && method === "DELETE") { const id = decodeURIComponent(u.pathname.split("/").pop()); return files.delete(id) ? new Response(null, { status: 204 }) : json({}, 404); }
    if (u.pathname === "/upload/drive/v3/files" && u.searchParams.get("uploadType") === "multipart") {
      const b = /boundary=(\S+)/.exec(init.headers["Content-Type"])[1], raw = Buffer.from(init.body), s = raw.toString("latin1");
      const parts = s.split(`--${b}`), meta = JSON.parse(parts[1].split("\r\n\r\n")[1].trim());
      const start = s.indexOf("\r\n\r\n", s.indexOf(`--${b}`, 10)) + 4, end = s.lastIndexOf(`\r\n--${b}--`);
      if (!files.has(meta.parents[0])) return json({ error: "parent" }, 404);
      return json({ id: add({ ...meta, bytes: new Uint8Array(raw.subarray(start, end)), mime: /Content-Type: (\S+)\r\n\r\n/.exec(parts[2])[1] }) });
    }
    if (u.pathname === "/upload/drive/v3/files" && u.searchParams.get("uploadType") === "resumable") {
      const k = "https://upload.test/s" + sessions.size; sessions.set(k, { meta: JSON.parse(init.body), mime: init.headers["X-Upload-Content-Type"], len: +init.headers["X-Upload-Content-Length"] });
      return new Response(null, { status: 200, headers: { Location: k } });
    }
    if (sessions.has(url) && method === "PUT") { const s = sessions.get(url), bytes = new Uint8Array(init.body); assert.equal(bytes.byteLength, s.len); return json({ id: add({ ...s.meta, bytes, mime: s.mime }) }); }
    throw new Error("unexpected " + method + " " + url);
  };
  return { files, fetchImpl, setFail: f => { fail = f; }, byName: name => [...files.values()].find(f => f.name === name) };
}
const SUN = Date.UTC(2026, 10, 8, 18, 5), MON = Date.UTC(2026, 10, 9, 3, 0);
const env = (db, extra = {}) => ({ DB: db, LAB_PAGES: bucket(), GDRIVE_CLIENT_ID: "cid", GDRIVE_CLIENT_SECRET: "cs", GDRIVE_REFRESH_TOKEN: "rt", ...extra });

test("the weekly slot is Sunday 18:00-18:59 UTC (Monday 03:00 KST)", () => {
  assert.equal(backupDue(SUN), true); assert.equal(backupDue(MON), false); assert.equal(backupDue(Date.UTC(2026, 10, 8, 19, 0)), false);
});

test("without the Drive secrets, or with BACKUP_DRIVE off, nothing runs and no table is made", async () => {
  const db = seed();
  assert.equal(await backupTick({ DB: db }, { now: SUN }), null);
  assert.deepEqual(await backupTick({ DB: db }, { now: SUN, force: true }), { error: "drive_not_configured" });
  assert.equal(await backupTick(env(db, { BACKUP_DRIVE: "off" }), { now: SUN }), null);
  assert.equal(db.sql.prepare("SELECT COUNT(*) n FROM sqlite_master WHERE name LIKE 'backup_%'").get().n, 0);
});

test("the dump loads back into an empty database: every row, quotes and blobs, but no answer photos", async () => {
  const db = seed(), { bytes, tables } = await dumpDatabase(db, { at: SUN });
  assert.deepEqual(tables, { users: 450, lab_pages: 5, avatars: 1 });
  const sql = gunzipSync(bytes).toString("utf8"), back = new DatabaseSync(":memory:");
  back.exec(sql);
  assert.equal(back.prepare("SELECT COUNT(*) n FROM users").get().n, 450);
  assert.equal(back.prepare("SELECT note FROM users WHERE id=1").get().note, "it's \"quoted\"\nline two");
  assert.deepEqual([...back.prepare("SELECT data FROM avatars").get().data], [1, 2, 3]);
  assert.equal(back.prepare("SELECT length(data) n FROM lab_pages WHERE id=2").get().n, 0, "an inline photo is not in the dump (it goes to photos/)");
  assert.equal(Buffer.from(back.prepare("SELECT data FROM lab_pages WHERE id=3").get().data).toString(), "typed answer", "a typed page keeps its text");
  assert.equal(back.prepare("SELECT r2_key FROM lab_pages WHERE id=1").get().r2_key, "lab/7/a.jpg");
  assert.ok(back.prepare("SELECT 1 FROM sqlite_master WHERE name='lab_pages_s'").get(), "indexes come after the rows");
  assert.ok(back.prepare("SELECT 1 FROM sqlite_master WHERE name='v_users'").get());
});

test("a weekly run: dump, then each photo once, then done; the slot starts no second run", async () => {
  const db = seed(), dr = drive(), e = env(db), o = { fetchImpl: dr.fetchImpl, photosPerStep: 1 };
  assert.equal(await backupTick(e, { ...o, now: MON }), null, "outside the slot nothing starts");
  let r = await backupTick(e, { ...o, now: SUN });
  assert.equal(r.phase, "photos"); assert.equal(r.error, null);
  const root = dr.byName("HaslaLab backup"), dbDir = dr.byName("db"), photos = dr.byName("photos");
  assert.ok(root && dbDir.parents[0] === root.id && photos.parents[0] === root.id);
  const dump = [...dr.files.values()].find(f => f.name.endsWith(".sql.gz"));
  assert.equal(dump.parents[0], dbDir.id); assert.equal(dump.mime, "application/gzip");
  assert.match(dump.name, /^haslalab-2026-11-08-run1\.sql\.gz$/);
  for (let i = 0; i < 6 && r.phase !== "done"; i++) r = await backupTick(e, { ...o, now: SUN + (i + 1) * 60000 });
  assert.equal(r.phase, "done");
  assert.deepEqual([...dr.byName("s7-p1.jpg").bytes], [0xff, 0xd8, 1, 2, 3, 0xff, 0xd9], "an R2 photo, byte for byte");
  assert.deepEqual([...dr.byName("s7-p2.jpg").bytes], [0xff, 0xd8, 9, 9, 0xff, 0xd9], "a photo still kept in D1");
  assert.equal(dr.byName("s8-p5.png").bytes.byteLength, big.byteLength, "a photo over 4 MB goes up resumably");
  assert.equal(dr.byName("s8-p4.jpg"), undefined, "a purged photo is not copied");
  assert.equal(dr.byName("s7-p3.bin"), undefined, "a typed page is in the dump, not a photo");
  assert.deepEqual(r.stats.photos, { copied: 3, bytes: 7 + 6 + big.byteLength, missing: 0 });
  assert.equal(await backupTick(e, { ...o, now: SUN + 30 * 60000 }), null, "one run a week");
  assert.equal(db.sql.prepare("SELECT COUNT(*) n FROM backup_runs").get().n, 1);
});

test("the next run copies only new photos, drops photos the site let go, and keeps the newest 8 dumps", async () => {
  const db = seed(), dr = drive(), e = env(db), o = { fetchImpl: dr.fetchImpl };
  let r = await backupTick(e, { ...o, now: SUN });
  while (r.phase !== "done") r = await backupTick(e, { ...o, now: SUN + 60000 });
  const dbDir = dr.byName("db");
  for (let i = 0; i < 9; i++) await dr.fetchImpl("https://www.googleapis.com/drive/v3/files?fields=id", { method: "POST", headers: { Authorization: "Bearer at" }, body: JSON.stringify({ name: `old-${i}.sql.gz`, parents: [dbDir.id] }) });
  db.sql.exec("DELETE FROM lab_pages WHERE id=1; UPDATE lab_pages SET data=X'', purged_at=1 WHERE id=2;");
  db.sql.prepare("INSERT INTO lab_pages(session_id,mime,data,r2_key) VALUES (9,'image/jpeg',?,NULL)").run(new Uint8Array([0xff, 0xd8, 5, 0xff, 0xd9]));
  const next = SUN + 7 * 86400000;
  r = await backupTick(e, { ...o, now: next });
  while (r.phase !== "done") r = await backupTick(e, { ...o, now: next + 60000 });
  assert.equal(r.stats.photos.copied, 1, "only the new page"); assert.ok(dr.byName("s9-p6.jpg"));
  assert.equal(dr.byName("s7-p1.jpg"), undefined, "a deleted page's photo leaves Drive");
  assert.equal(dr.byName("s7-p2.jpg"), undefined, "a purged photo leaves Drive");
  assert.equal(r.stats.pruned.photos, 2);
  assert.equal([...dr.files.values()].filter(f => f.parents?.[0] === dbDir.id).length, 8, "the newest 8 dumps");
  assert.ok([...dr.files.values()].some(f => /run2\.sql\.gz$/.test(f.name)), "the new dump is among them");
  assert.deepEqual(db.sql.prepare("SELECT page_id FROM backup_photos ORDER BY page_id").all().map(x => x.page_id), [5, 6]);
});

test("a step in progress is leased; a failing Drive is retried and gives up after ten tries; a folder deleted by hand is made again", async () => {
  const db = seed(), dr = drive(), e = env(db), o = { fetchImpl: dr.fetchImpl };
  dr.setFail((u, m) => u.pathname.startsWith("/upload/"));
  let r = await backupTick(e, { ...o, now: SUN });
  assert.equal(r.phase, "db"); assert.match(r.error, /drive_upload_500/); assert.equal(r.stats.fails, 1);
  db.sql.exec("UPDATE backup_runs SET lease_until=" + (Math.floor(SUN / 1000) + 999));
  assert.deepEqual(await backupTick(e, { ...o, now: SUN + 60000 }), { run: 1, busy: true });
  db.sql.exec("UPDATE backup_runs SET lease_until=NULL");
  for (let i = 0; i < 9; i++) r = await backupTick(e, { ...o, now: SUN + (i + 2) * 60000 });
  assert.equal(r.phase, "failed"); assert.equal(r.stats.fails, 10);
  assert.ok(db.sql.prepare("SELECT done_at FROM backup_runs WHERE id=1").get().done_at, "a failed run is closed");

  dr.setFail(null);
  r = await backupTick(e, { ...o, now: SUN + 20 * 60000, force: true });
  assert.equal(r.phase, "photos", "a forced run starts at once");
  const photos = dr.byName("photos"); dr.files.delete(photos.id);
  r = await backupTick(e, { ...o, now: SUN + 21 * 60000 });
  assert.match(r.error, /404/);
  r = await backupTick(e, { ...o, now: SUN + 22 * 60000 });
  assert.equal(r.error, null); assert.notEqual(dr.byName("photos").id, photos.id, "made again");
});
