/* The tables of the shared-storage groups (workshop-groups.js) and the one check the Learn class join
   (learn-services.js, POST /api/learn/classes/join with the six-letter class code) must make too, so the old code cannot
   get round a removal or the group's "참여 승인 필요" setting. No imports: learn-services.js and workshop-groups.js both
   use this file. A group is a Learn class: classes (owner = teacher_id) and class_members (role admin|member). */

export const GROUP_SCHEMA = [
  /* per-group settings; a class with no row has the defaults (no description, no approval, the class code works) */
  `CREATE TABLE IF NOT EXISTS workshop_groups (
     class_id INTEGER PRIMARY KEY,
     description TEXT NOT NULL DEFAULT '',
     approval INTEGER NOT NULL DEFAULT 0,
     legacy_code INTEGER NOT NULL DEFAULT 1,
     owner_active_at INTEGER,
     updated_at INTEGER)`,
  /* invite codes: only the SHA-256 of the normalised code is kept, with two letters as a hint for the managers' list */
  `CREATE TABLE IF NOT EXISTS workshop_group_invites (
     id TEXT PRIMARY KEY,
     class_id INTEGER NOT NULL,
     code_hash TEXT NOT NULL UNIQUE,
     hint TEXT NOT NULL,
     created_by INTEGER NOT NULL,
     created_at INTEGER NOT NULL,
     expires_at INTEGER,
     max_uses INTEGER,
     uses INTEGER NOT NULL DEFAULT 0,
     revoked_at INTEGER)`,
  'CREATE INDEX IF NOT EXISTS workshop_group_invites_class ON workshop_group_invites(class_id, created_at)',
  /* join requests waiting for an owner or admin (groups with approval on) */
  `CREATE TABLE IF NOT EXISTS workshop_group_requests (
     class_id INTEGER NOT NULL,
     user_id INTEGER NOT NULL,
     invite_id TEXT,
     created_at INTEGER NOT NULL,
     PRIMARY KEY (class_id, user_id))`,
  'CREATE INDEX IF NOT EXISTS workshop_group_requests_user ON workshop_group_requests(user_id)',
  /* a removed member: the class code and invite codes made before the removal no longer let them back in */
  `CREATE TABLE IF NOT EXISTS workshop_group_blocks (
     class_id INTEGER NOT NULL,
     user_id INTEGER NOT NULL,
     removed_at INTEGER NOT NULL,
     PRIMARY KEY (class_id, user_id))`,
  /* failed code entries per member and per address, and the lock that follows too many */
  `CREATE TABLE IF NOT EXISTS workshop_group_join_fails (
     k TEXT PRIMARY KEY,
     start INTEGER NOT NULL,
     n INTEGER NOT NULL,
     locked_until INTEGER)`
];
/* added to the Learn table; a duplicate column error means another isolate added it already */
const GROUP_COLUMNS = [
  `ALTER TABLE class_members ADD COLUMN role TEXT NOT NULL DEFAULT 'member'`,
  'ALTER TABLE class_members ADD COLUMN last_active_at INTEGER'
];

const ready = new WeakSet();
/* call after ensureLearnSchema (class_members must exist) */
export async function ensureGroupSchema(env) {
  if (ready.has(env.DB)) return;
  for (const sql of GROUP_SCHEMA) await env.DB.prepare(sql).run();
  for (const sql of GROUP_COLUMNS) {
    try { await env.DB.prepare(sql).run(); } catch (e) { if (!/duplicate column/i.test(String(e?.message || e))) throw e; }
  }
  ready.add(env.DB);
}

/* the Learn join with the class code: null to go ahead, else the error code to refuse with. With approval on, the
   member's request is recorded and 'join_pending' comes back. */
export async function legacyJoinGate(env, classId, userId, t) {
  await ensureGroupSchema(env);
  const db = env.DB;
  if (await db.prepare('SELECT 1 FROM class_members WHERE class_id=? AND user_id=?').bind(classId, userId).first()) return null;
  const g = await db.prepare('SELECT approval,legacy_code FROM workshop_groups WHERE class_id=?').bind(classId).first();
  if (g && !g.legacy_code) return 'class_not_found';
  if (await db.prepare('SELECT 1 FROM workshop_group_blocks WHERE class_id=? AND user_id=?').bind(classId, userId).first()) return 'removed_from_group';
  if (g?.approval) {
    await db.prepare('INSERT OR IGNORE INTO workshop_group_requests(class_id,user_id,invite_id,created_at) VALUES(?,?,NULL,?)').bind(classId, userId, t).run();
    return 'join_pending';
  }
  return null;
}
