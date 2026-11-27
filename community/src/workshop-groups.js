/* Groups of the Workshop storage's shared storage (#/workshop/storage). A group is a Learn class (learn-services.js):
   the owner is classes.teacher_id, everyone else is a class_members row with role 'admin' or 'member'. Every route needs
   a signed-in member and checks the caller's role in the group on each request, so a removed member loses access at once.
   Members are named by nickname only: no user ids or emails leave this file.

   - GET    /api/workshop/storage/groups                       the caller's groups: name, role, member count, first avatars
   - POST   /api/workshop/storage/groups                       {name, description?, approval?} a new group (Learn's limits)
   - POST   /api/workshop/storage/groups/preview               {code} what the code joins: name, owner, member count
   - POST   /api/workshop/storage/groups/join                  {code} joins, or asks to join when approval is on
   - GET    /api/workshop/storage/groups/:id                   detail: settings, storage, members; managers also get the
                                                               invite codes and the join requests
   - PATCH  /api/workshop/storage/groups/:id                   {name, legacy_code} owner; {description, approval} owner/admin
   - DELETE /api/workshop/storage/groups/:id?confirm=<name>    owner: closes the group (the name typed again)
   - POST   /api/workshop/storage/groups/:id/leave             admin or member
   - POST   /api/workshop/storage/groups/:id/transfer          {nickname} owner: that member becomes the owner, the old
                                                               owner an admin
   - PATCH  /api/workshop/storage/groups/:id/members/:nickname {role: 'admin'|'member'} owner
   - DELETE /api/workshop/storage/groups/:id/members/:nickname owner (admins and members) or admin (members only)
   - POST   /api/workshop/storage/groups/:id/requests/:nickname {approve: true|false} owner/admin
   - POST   /api/workshop/storage/groups/:id/invites           {expires: '1d'|'7d'|'never', max_uses: 1|10|50|null}
                                                               owner/admin; the code is in this answer only
   - DELETE /api/workshop/storage/groups/:id/invites/:inviteId revokes
   - POST   /api/workshop/storage/groups/:id/invites/:inviteId/regenerate  revokes it and makes a new code with its settings

   Invite codes: 8 characters from a 32-letter alphabet without I, O, 0 and 1 (40 bits), shown as XXXX-XXXX; case,
   spaces and dashes do not matter. Only SHA-256('hasla-group-invite:v1:' + code) is stored. Entering a code (preview or
   join) is limited per member and per address; failed entries lock the member or the address out for an hour.
   The six-letter class code of Learn still works unless the owner turns it off (legacy_code). */
import { ensureLearnSchema, planOf, FREE_CLASSES, PLAN_CLASSES, FREE_SEATS, PLAN_SEATS } from './learn-services.js';
import { ensureGroupSchema } from './workshop-group-gate.js';

export const INVITE_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
export const INVITE_EXPIRY = {'1d': 86400, '7d': 7 * 86400, never: null};
export const INVITE_USES = [1, 10, 50, null];
/* code entries: ATTEMPTS per member and per address in WINDOW seconds; FAILS wrong codes in FAIL_WINDOW lock for LOCK */
export const JOIN_RULES = {userAttempts: 10, ipAttempts: 60, window: 600, userFails: 8, ipFails: 40, failWindow: 3600, lock: 3600};
const INVITES_ACTIVE = 10, REQUESTS_MAX = 200, LIST_MAX = 100, PREVIEW_AVATARS = 5;
const LEGACY_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';

export function newInviteCode() {
  return [...crypto.getRandomValues(new Uint8Array(8))].map(b => INVITE_ALPHABET[b & 31]).join('');
}
export const formatInviteCode = c => c.slice(0, 4) + '-' + c.slice(4);
/* what a member typed: {invite: 'ABCDEFGH'} for an invite code, {legacy: 'ABC123'} for a Learn class code, else null */
export function parseCode(raw) {
  const s = String(raw ?? '').toUpperCase().replace(/[\s-]/g, '');
  if (s.length === 8 && [...s].every(ch => INVITE_ALPHABET.includes(ch))) return {invite: s};
  if (/^[A-Z0-9]{6}$/.test(s)) return {legacy: s};
  return null;
}
export async function hashInviteCode(code) {
  const bytes = new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode('hasla-group-invite:v1:' + code)));
  return [...bytes].map(b => b.toString(16).padStart(2, '0')).join('');
}
const newLegacyCode = () => [...crypto.getRandomValues(new Uint8Array(6))].map(b => LEGACY_CHARS[b & 31]).join('');
const ROLE_ORDER = "CASE x.role WHEN 'admin' THEN 0 ELSE 1 END";
const person = r => ({nickname: r.nickname, avatar: r.avatar || null});

/* the last time a member opened the shared storage, kept at most every five minutes */
export async function touchGroupActivity(env, uid, t) {
  await ensureLearnSchema(env);
  await ensureGroupSchema(env);
  await env.DB.prepare('UPDATE class_members SET last_active_at=? WHERE user_id=? AND (last_active_at IS NULL OR last_active_at<?)').bind(t, uid, t - 300).run();
  await env.DB.prepare(`INSERT INTO workshop_groups(class_id,owner_active_at) SELECT id,? FROM classes WHERE teacher_id=? AND closed_at IS NULL
    ON CONFLICT(class_id) DO UPDATE SET owner_active_at=excluded.owner_active_at WHERE owner_active_at IS NULL OR owner_active_at<?`).bind(t, uid, t - 300).run();
}

/* the shares, invites, requests and removals of a group that has closed */
async function dropGroupRows(db, gid) {
  for (const sql of ['DELETE FROM workshop_group_invites WHERE class_id=?', 'DELETE FROM workshop_group_requests WHERE class_id=?',
    'DELETE FROM workshop_group_blocks WHERE class_id=?', 'DELETE FROM workshop_class_shares WHERE class_id=?'])
    await db.prepare(sql).bind(gid).run().catch(e => { if (!/no such table/i.test(String(e?.message))) throw e; });
}

/* account deletion: every group the member owns is closed (as index.js closes the classes still owned). Memberships,
   requests, removals and the member's invite codes go. */
export async function groupsForgetUser(env, uid, t) {
  await ensureLearnSchema(env);
  await ensureGroupSchema(env);
  const db = env.DB;
  const owned = (await db.prepare('SELECT id FROM classes WHERE teacher_id=? AND closed_at IS NULL').bind(uid).all()).results || [];
  /* a group the member owns always closes with the account (owner's choice, 2026-11-27): no one inherits it or the
     members' practice records that come with a Learn class */
  for (const {id} of owned) {
    await db.prepare('UPDATE classes SET closed_at=? WHERE id=?').bind(t, id).run();
    await dropGroupRows(db, id);
  }
  await db.prepare('UPDATE workshop_group_invites SET revoked_at=? WHERE created_by=? AND revoked_at IS NULL').bind(t, uid).run();
  await db.prepare('DELETE FROM workshop_group_requests WHERE user_id=?').bind(uid).run();
  await db.prepare('DELETE FROM workshop_group_blocks WHERE user_id=?').bind(uid).run();
  await db.prepare('DELETE FROM class_members WHERE user_id=?').bind(uid).run();
  await db.prepare('DELETE FROM workshop_group_join_fails WHERE k=?').bind('u:' + uid).run();
  return {transferred: 0, closed: owned.length};
}

export function createGroupRoutes({HttpError, limit, bad, quotaOf = () => null}) {
  const fail = (status, code) => { throw new HttpError(status, code); };
  const missing = () => fail(404, 'group_not_found');
  const forbidden = () => fail(403, 'forbidden');
  const str = v => (typeof v === 'string' ? v.trim() : '');

  async function roleOf(db, gid, uid) {
    const c = await db.prepare(`SELECT c.id,c.teacher_id,c.name,c.code,c.created_at,COALESCE(g.description,'') AS description,
      COALESCE(g.approval,0) AS approval,COALESCE(g.legacy_code,1) AS legacy_code,g.owner_active_at
      FROM classes c LEFT JOIN workshop_groups g ON g.class_id=c.id WHERE c.id=? AND c.closed_at IS NULL`).bind(gid).first();
    if (!c) return null;
    if (c.teacher_id === uid) return {c, role: 'owner'};
    const m = await db.prepare('SELECT role FROM class_members WHERE class_id=? AND user_id=?').bind(gid, uid).first();
    return m ? {c, role: m.role === 'admin' ? 'admin' : 'member'} : null;
  }
  const seatsOf = async (env, ownerId, t) => ((await planOf(env, ownerId, t)).plan === 'free' ? FREE_SEATS : PLAN_SEATS);
  const memberCount = async (db, gid) => (await db.prepare('SELECT COUNT(*) AS n FROM class_members WHERE class_id=?').bind(gid).first()).n;
  const settings = (db, gid, t) => db.prepare('INSERT OR IGNORE INTO workshop_groups(class_id,updated_at) VALUES(?,?)').bind(gid, t).run();
  /* a member by nickname, never the owner; null when not in the group */
  const memberByNick = (db, gid, nick) => db.prepare(`SELECT x.user_id,x.role,u.nickname FROM class_members x JOIN users u ON u.id=x.user_id AND u.deleted=0
    WHERE x.class_id=? AND u.nickname=?`).bind(gid, nick).first();
  const dropShares = (db, gid, uid) => db.prepare('DELETE FROM workshop_class_shares WHERE class_id=? AND owner_id=?').bind(gid, uid).run();

  /* the lock check before a code is looked at, and the count of a wrong one */
  const failKeys = (uid, ip) => [['u:' + uid, JOIN_RULES.userFails], ...(ip ? [['ip:' + ip, JOIN_RULES.ipFails]] : [])];
  async function guard(env, uid, ip, t) {
    for (const [k] of failKeys(uid, ip)) {
      const row = await env.DB.prepare('SELECT locked_until FROM workshop_group_join_fails WHERE k=?').bind(k).first();
      if (row?.locked_until > t) fail(429, 'join_locked');
    }
    await limit(env, 'wsg-try:' + uid, JOIN_RULES.userAttempts, JOIN_RULES.window);
    if (ip) await limit(env, 'wsg-try-ip:' + ip, JOIN_RULES.ipAttempts, JOIN_RULES.window);
  }
  async function wrong(env, uid, ip, t) {
    const w = JOIN_RULES.failWindow;
    for (const [k, max] of failKeys(uid, ip)) {
      const row = await env.DB.prepare(`INSERT INTO workshop_group_join_fails(k,start,n) VALUES(?,?,1)
        ON CONFLICT(k) DO UPDATE SET n=CASE WHEN excluded.start-start>=? THEN 1 ELSE n+1 END,
          start=CASE WHEN excluded.start-start>=? THEN excluded.start ELSE start END RETURNING n`).bind(k, t, w, w).first();
      if (row && row.n >= max) await env.DB.prepare('UPDATE workshop_group_join_fails SET locked_until=?,n=0,start=? WHERE k=?').bind(t + JOIN_RULES.lock, t, k).run();
    }
  }
  /* a code to its group: {c, invite?}; a wrong, revoked, used-up or expired code counts as a failed entry */
  async function resolve(env, raw, uid, ip, t) {
    const db = env.DB, code = parseCode(raw);
    if (!code) bad('bad_code');
    await guard(env, uid, ip, t);
    const refuse = async (status, err) => { await wrong(env, uid, ip, t); fail(status, err); };
    if (code.invite) {
      const row = await db.prepare(`SELECT i.id AS invite_id,i.created_at AS invite_at,i.expires_at,i.max_uses,i.uses,i.revoked_at,c.id,c.teacher_id,c.name
        FROM workshop_group_invites i JOIN classes c ON c.id=i.class_id AND c.closed_at IS NULL WHERE i.code_hash=?`).bind(await hashInviteCode(code.invite)).first();
      if (!row || row.revoked_at) await refuse(404, 'invite_not_found');
      if (row.expires_at != null && row.expires_at <= t) await refuse(410, 'invite_expired');
      if (row.max_uses != null && row.uses >= row.max_uses) await refuse(410, 'invite_used_up');
      return {c: row, invite: row};
    }
    const c = await db.prepare(`SELECT c.id,c.teacher_id,c.name FROM classes c LEFT JOIN workshop_groups g ON g.class_id=c.id
      WHERE c.code=? AND c.closed_at IS NULL AND COALESCE(g.legacy_code,1)=1`).bind(code.legacy).first();
    if (!c) await refuse(404, 'invite_not_found');
    return {c, invite: null};
  }
  async function summary(db, c, uid) {
    const owner = await db.prepare('SELECT nickname,avatar FROM users WHERE id=?').bind(c.teacher_id).first();
    const g = await db.prepare('SELECT approval,description FROM workshop_groups WHERE class_id=?').bind(c.id).first();
    const mine = c.teacher_id === uid || !!await db.prepare('SELECT 1 FROM class_members WHERE class_id=? AND user_id=?').bind(c.id, uid).first();
    const pending = !!await db.prepare('SELECT 1 FROM workshop_group_requests WHERE class_id=? AND user_id=?').bind(c.id, uid).first();
    return {name: c.name, description: g?.description || '', owner: person(owner || {}), member_count: 1 + await memberCount(db, c.id),
      approval: !!g?.approval, member: mine, pending};
  }
  /* one use of the invite, inside the update so two joins at once cannot pass max_uses */
  const takeUse = (db, invite, t) => db.prepare(`UPDATE workshop_group_invites SET uses=uses+1 WHERE id=? AND revoked_at IS NULL
    AND (expires_at IS NULL OR expires_at>?) AND (max_uses IS NULL OR uses<max_uses)`).bind(invite.invite_id, t).run();
  const giveUse = (db, invite) => db.prepare('UPDATE workshop_group_invites SET uses=MAX(0,uses-1) WHERE id=?').bind(invite.invite_id).run();

  async function addMember(env, c, uid, t, inviteAt) {
    const db = env.DB;
    if (await memberCount(db, c.id) >= await seatsOf(env, c.teacher_id, t)) fail(403, 'class_full');
    await db.prepare("INSERT OR IGNORE INTO class_members(class_id,user_id,joined_at,role) VALUES(?,?,?,'member')").bind(c.id, uid, t).run();
    await db.prepare('DELETE FROM workshop_group_blocks WHERE class_id=? AND user_id=?').bind(c.id, uid).run();
    await db.prepare('DELETE FROM workshop_group_requests WHERE class_id=? AND user_id=?').bind(c.id, uid).run();
  }
  const inviteView = r => ({id: r.id, hint: r.hint + '··-····', created_at: r.created_at, expires_at: r.expires_at, max_uses: r.max_uses,
    uses: r.uses, created_by: r.nickname || null});
  async function makeInvite(env, gid, uid, t, expires, maxUses) {
    const db = env.DB;
    const n = (await db.prepare(`SELECT COUNT(*) AS n FROM workshop_group_invites WHERE class_id=? AND revoked_at IS NULL
      AND (expires_at IS NULL OR expires_at>?) AND (max_uses IS NULL OR uses<max_uses)`).bind(gid, t).first()).n;
    if (n >= INVITES_ACTIVE) fail(409, 'invite_limit');
    for (let k = 0; k < 5; k++) {
      const code = newInviteCode(), id = crypto.randomUUID();
      try {
        await db.prepare(`INSERT INTO workshop_group_invites(id,class_id,code_hash,hint,created_by,created_at,expires_at,max_uses,uses)
          VALUES(?,?,?,?,?,?,?,?,0)`).bind(id, gid, await hashInviteCode(code), code.slice(0, 2), uid, t, expires == null ? null : t + expires, maxUses).run();
        const me = await db.prepare('SELECT nickname FROM users WHERE id=?').bind(uid).first();
        return {code: formatInviteCode(code), invite: inviteView({id, hint: code.slice(0, 2), created_at: t, expires_at: expires == null ? null : t + expires,
          max_uses: maxUses, uses: 0, nickname: me?.nickname})};
      } catch (e) { if (!/UNIQUE/i.test(String(e?.message))) throw e; }
    }
    fail(503, 'try_again');
  }

  return async function groupRoute(p, m, body, uid, t, env, req) {
    await ensureLearnSchema(env);
    await ensureGroupSchema(env);
    const db = env.DB, ip = req?.headers?.get?.('CF-Connecting-IP') || '';
    const all = async (sql, ...a) => (await db.prepare(sql).bind(...a).all()).results || [];
    const base = '/api/workshop/storage/groups';

    if (p === base && m === 'GET') {
      await touchGroupActivity(env, uid, t);
      const groups = await all(`SELECT c.id,c.name,c.created_at,c.teacher_id,COALESCE(g.description,'') AS description,COALESCE(g.approval,0) AS approval,
        o.nickname AS owner_nickname,o.avatar AS owner_avatar,x.role AS my_role
        FROM classes c LEFT JOIN workshop_groups g ON g.class_id=c.id LEFT JOIN users o ON o.id=c.teacher_id
        LEFT JOIN class_members x ON x.class_id=c.id AND x.user_id=?
        WHERE c.closed_at IS NULL AND (c.teacher_id=? OR x.user_id IS NOT NULL) ORDER BY c.id DESC LIMIT ${LIST_MAX}`, uid, uid);
      const ids = groups.map(g => g.id), q = ids.map(() => '?').join(',');
      const counts = new Map(), faces = new Map(), waiting = new Map();
      if (ids.length) {
        for (const r of await all(`SELECT class_id,COUNT(*) AS n FROM class_members WHERE class_id IN (${q}) GROUP BY class_id`, ...ids)) counts.set(r.class_id, r.n);
        for (const r of await all(`SELECT class_id,nickname,avatar FROM (SELECT x.class_id,u.nickname,u.avatar,
            ROW_NUMBER() OVER (PARTITION BY x.class_id ORDER BY ${ROLE_ORDER},x.joined_at,u.nickname) AS k
            FROM class_members x JOIN users u ON u.id=x.user_id AND u.deleted=0 WHERE x.class_id IN (${q})) WHERE k<${PREVIEW_AVATARS}`, ...ids))
          (faces.get(r.class_id) || faces.set(r.class_id, []).get(r.class_id)).push(person(r));
        for (const r of await all(`SELECT class_id,COUNT(*) AS n FROM workshop_group_requests WHERE class_id IN (${q}) GROUP BY class_id`, ...ids)) waiting.set(r.class_id, r.n);
      }
      return {groups: groups.map(g => {
        const role = g.teacher_id === uid ? 'owner' : g.my_role === 'admin' ? 'admin' : 'member';
        return {id: g.id, name: g.name, description: g.description, created_at: g.created_at, approval: !!g.approval, role,
          owner: {nickname: g.owner_nickname, avatar: g.owner_avatar || null}, member_count: 1 + (counts.get(g.id) || 0),
          avatars: [{nickname: g.owner_nickname, avatar: g.owner_avatar || null}, ...(faces.get(g.id) || [])],
          ...(role !== 'member' ? {pending_requests: waiting.get(g.id) || 0} : {})};
      })};
    }
    if (p === base && m === 'POST') {
      const name = str(body?.name);
      if (!name || name.length > 60) bad('bad_name');
      const description = str(body?.description);
      if (description.length > 300) bad('bad_description');
      await limit(env, 'class-new:' + uid, 10, 86400);
      const plan = await planOf(env, uid, t), max = plan.plan === 'free' ? FREE_CLASSES : PLAN_CLASSES;
      const have = (await db.prepare('SELECT COUNT(*) AS n FROM classes WHERE teacher_id=? AND closed_at IS NULL').bind(uid).first()).n;
      if (have >= max) fail(403, 'class_limit');
      for (let k = 0; k < 5; k++) {
        try {
          const r = await db.prepare('INSERT INTO classes(teacher_id,name,code,created_at) VALUES(?,?,?,?)').bind(uid, name, newLegacyCode(), t).run();
          const id = r.meta.last_row_id;
          await db.prepare('INSERT OR REPLACE INTO workshop_groups(class_id,description,approval,legacy_code,updated_at) VALUES(?,?,?,1,?)').bind(id, description, body?.approval ? 1 : 0, t).run();
          return {id, name};
        } catch (e) { if (!/UNIQUE/i.test(String(e?.message))) throw e; }
      }
      fail(503, 'try_again');
    }
    if (p === base + '/preview' && m === 'POST') {
      const {c} = await resolve(env, body?.code, uid, ip, t);
      return {group: await summary(db, c, uid)};
    }
    if (p === base + '/join' && m === 'POST') {
      const {c, invite} = await resolve(env, body?.code, uid, ip, t);
      const group = {id: c.id, name: c.name};
      if (c.teacher_id === uid || await db.prepare('SELECT 1 FROM class_members WHERE class_id=? AND user_id=?').bind(c.id, uid).first()) return {status: 'member', group};
      const block = await db.prepare('SELECT removed_at FROM workshop_group_blocks WHERE class_id=? AND user_id=?').bind(c.id, uid).first();
      if (block && (!invite || invite.invite_at <= block.removed_at)) fail(403, 'removed_from_group');
      const g = await db.prepare('SELECT approval FROM workshop_groups WHERE class_id=?').bind(c.id).first();
      if (g?.approval) {
        if (await db.prepare('SELECT 1 FROM workshop_group_requests WHERE class_id=? AND user_id=?').bind(c.id, uid).first()) return {status: 'pending', group};
        if ((await db.prepare('SELECT COUNT(*) AS n FROM workshop_group_requests WHERE class_id=?').bind(c.id).first()).n >= REQUESTS_MAX) fail(409, 'request_limit');
        if (invite && !(await takeUse(db, invite, t)).meta.changes) fail(410, 'invite_used_up');
        await db.prepare('INSERT OR IGNORE INTO workshop_group_requests(class_id,user_id,invite_id,created_at) VALUES(?,?,?,?)').bind(c.id, uid, invite?.invite_id || null, t).run();
        return {status: 'pending', group};
      }
      if (invite && !(await takeUse(db, invite, t)).meta.changes) fail(410, 'invite_used_up');
      try { await addMember(env, c, uid, t); }
      catch (e) { if (invite) await giveUse(db, invite); throw e; }
      return {status: 'joined', group};
    }

    const mm = /^\/api\/workshop\/storage\/groups\/(\d{1,12})(?:\/(leave|transfer|members|requests|invites)(?:\/([^/]{1,200}))?(?:\/(regenerate))?)?$/.exec(p);
    if (!mm) missing();
    const gid = Number(mm[1]), [, , part, arg, sub] = mm;
    const access = await roleOf(db, gid, uid);
    if (!access) missing();   /* not a member: the group does not exist for them */
    const {c, role} = access, owner = role === 'owner', manager = role !== 'member';
    let nick = '';
    if (arg != null && part !== 'invites') { try { nick = decodeURIComponent(arg); } catch { bad('bad_nickname'); } }

    if (!part && m === 'GET') {
      await touchGroupActivity(env, uid, t);
      const ownerRow = await db.prepare('SELECT nickname,avatar FROM users WHERE id=?').bind(c.teacher_id).first() || {};
      const rows = await all(`SELECT u.nickname,u.avatar,x.role,x.joined_at,x.last_active_at,(x.user_id=?) AS me FROM class_members x
        JOIN users u ON u.id=x.user_id AND u.deleted=0 WHERE x.class_id=? ORDER BY ${ROLE_ORDER},x.joined_at,u.nickname LIMIT 500`, uid, gid);
      const members = [{...person(ownerRow), role: 'owner', joined_at: c.created_at, last_active_at: c.owner_active_at ?? null, me: owner},
        ...rows.map(r => ({...person(r), role: r.role === 'admin' ? 'admin' : 'member', joined_at: r.joined_at, last_active_at: r.last_active_at ?? null, me: !!r.me}))]
        .map(r => (manager ? r : (({last_active_at, ...rest}) => rest)(r)));
      /* the distinct files shared into the group by people still in it, as the shared list counts them */
      const used = await db.prepare(`SELECT COUNT(*) AS files,COALESCE(SUM(size),0) AS bytes FROM (SELECT DISTINCT f.id,f.size
        FROM workshop_class_shares s JOIN json_each(s.file_ids) j JOIN workshop_files f ON f.id=j.value AND f.owner_id=s.owner_id
        WHERE s.class_id=? AND (s.owner_id=? OR EXISTS (SELECT 1 FROM class_members y WHERE y.class_id=s.class_id AND y.user_id=s.owner_id)))`)
        .bind(gid, c.teacher_id).first();
      const shares = (await db.prepare('SELECT COUNT(*) AS n FROM workshop_class_shares WHERE class_id=?').bind(gid).first()).n;
      const {plan} = await planOf(env, c.teacher_id, t);
      const out = {group: {id: c.id, name: c.name, description: c.description, created_at: c.created_at, approval: !!c.approval, role,
        owner: person(ownerRow), member_count: members.length, seats: 1 + await seatsOf(env, c.teacher_id, t),
        storage: {used: used.bytes, files: used.files, shares, quota: quotaOf(plan)},
        ...(manager ? {legacy_code: !!c.legacy_code, class_code: c.legacy_code ? c.code : null} : {})}, members};
      if (manager) {
        out.invites = (await all(`SELECT i.id,i.hint,i.created_at,i.expires_at,i.max_uses,i.uses,u.nickname FROM workshop_group_invites i LEFT JOIN users u ON u.id=i.created_by
          WHERE i.class_id=? AND i.revoked_at IS NULL AND (i.expires_at IS NULL OR i.expires_at>?) AND (i.max_uses IS NULL OR i.uses<i.max_uses)
          ORDER BY i.created_at DESC`, gid, t)).map(inviteView);
        out.requests = (await all(`SELECT u.nickname,u.avatar,r.created_at FROM workshop_group_requests r JOIN users u ON u.id=r.user_id AND u.deleted=0
          WHERE r.class_id=? ORDER BY r.created_at`, gid)).map(r => ({...person(r), requested_at: r.created_at}));
      }
      return out;
    }
    if (!part && m === 'PATCH') {
      const b = body || {};
      if (!['name', 'description', 'approval', 'legacy_code'].some(k => k in b)) bad('nothing_to_change');
      if (('name' in b || 'legacy_code' in b) && !owner) forbidden();
      if (!manager) forbidden();
      await limit(env, 'wsg-edit:' + uid, 120, 3600);
      await settings(db, gid, t);
      if ('name' in b) {
        const name = str(b.name);
        if (!name || name.length > 60) bad('bad_name');
        await db.prepare('UPDATE classes SET name=? WHERE id=?').bind(name, gid).run();
      }
      if ('description' in b) {
        const d = str(b.description);
        if (d.length > 300) bad('bad_description');
        await db.prepare('UPDATE workshop_groups SET description=?,updated_at=? WHERE class_id=?').bind(d, t, gid).run();
      }
      if ('approval' in b) await db.prepare('UPDATE workshop_groups SET approval=?,updated_at=? WHERE class_id=?').bind(b.approval ? 1 : 0, t, gid).run();
      if ('legacy_code' in b) await db.prepare('UPDATE workshop_groups SET legacy_code=?,updated_at=? WHERE class_id=?').bind(b.legacy_code ? 1 : 0, t, gid).run();
      return {ok: true};
    }
    if (!part && m === 'DELETE') {
      if (!owner) forbidden();
      /* index.js reads no body on DELETE, so the typed name comes as ?confirm= */
      const typed = body?.confirm ?? (req?.url ? new URL(req.url).searchParams.get('confirm') : null);
      if (str(typed) !== c.name) bad('confirm_name');
      await db.prepare('UPDATE classes SET closed_at=? WHERE id=? AND teacher_id=?').bind(t, gid, uid).run();
      await dropGroupRows(db, gid);
      return {ok: true};
    }
    if (part === 'leave' && m === 'POST' && arg == null) {
      if (owner) fail(409, 'owner_must_transfer');
      await db.prepare('DELETE FROM class_members WHERE class_id=? AND user_id=?').bind(gid, uid).run();
      await dropShares(db, gid, uid).catch(() => {});
      return {ok: true};
    }
    if (part === 'transfer' && m === 'POST' && arg == null) {
      if (!owner) forbidden();
      const nickname = str(body?.nickname);
      const target = nickname && await memberByNick(db, gid, nickname);
      if (!target) fail(404, 'member_not_found');
      const r = await db.prepare('UPDATE classes SET teacher_id=? WHERE id=? AND teacher_id=? AND closed_at IS NULL').bind(target.user_id, gid, uid).run();
      if (!r.meta.changes) missing();
      await db.prepare('DELETE FROM class_members WHERE class_id=? AND user_id=?').bind(gid, target.user_id).run();
      await db.prepare("INSERT OR REPLACE INTO class_members(class_id,user_id,joined_at,role) VALUES(?,?,?,'admin')").bind(gid, uid, c.created_at).run();
      return {ok: true, owner: target.nickname};
    }
    if (part === 'members' && arg != null && !sub) {
      const target = await memberByNick(db, gid, nick);
      if (m === 'PATCH') {
        if (!owner) forbidden();
        if (!target) fail(404, 'member_not_found');
        const next = body?.role;
        if (next !== 'admin' && next !== 'member') bad('bad_role');
        await db.prepare('UPDATE class_members SET role=? WHERE class_id=? AND user_id=?').bind(next, gid, target.user_id).run();
        return {ok: true, role: next};
      }
      if (m === 'DELETE') {
        if (!manager) forbidden();
        if (!target) fail(404, 'member_not_found');
        if (target.user_id === uid) bad('use_leave');
        if (!owner && target.role === 'admin') forbidden();
        await db.prepare('DELETE FROM class_members WHERE class_id=? AND user_id=?').bind(gid, target.user_id).run();
        await db.prepare('INSERT OR REPLACE INTO workshop_group_blocks(class_id,user_id,removed_at) VALUES(?,?,?)').bind(gid, target.user_id, t).run();
        await db.prepare('DELETE FROM workshop_group_requests WHERE class_id=? AND user_id=?').bind(gid, target.user_id).run();
        await dropShares(db, gid, target.user_id).catch(() => {});
        return {ok: true};
      }
    }
    if (part === 'requests' && arg != null && !sub && m === 'POST') {
      if (!manager) forbidden();
      const r = await db.prepare(`SELECT r.user_id FROM workshop_group_requests r JOIN users u ON u.id=r.user_id AND u.deleted=0
        WHERE r.class_id=? AND u.nickname=?`).bind(gid, nick).first();
      if (!r) fail(404, 'request_not_found');
      if (body?.approve === true) { await addMember(env, c, r.user_id, t); return {ok: true, status: 'joined'}; }
      await db.prepare('DELETE FROM workshop_group_requests WHERE class_id=? AND user_id=?').bind(gid, r.user_id).run();
      return {ok: true, status: 'denied'};
    }
    if (part === 'invites') {
      if (!manager) forbidden();
      if (arg == null && m === 'POST') {
        if (!Object.hasOwn(INVITE_EXPIRY, body?.expires ?? '')) bad('bad_expiry');
        const maxUses = body?.max_uses ?? null;
        if (!INVITE_USES.includes(maxUses)) bad('bad_max_uses');
        await limit(env, 'wsg-invite:' + uid, 30, 3600);
        return makeInvite(env, gid, uid, t, INVITE_EXPIRY[body.expires], maxUses);
      }
      if (arg != null && /^[0-9a-f-]{36}$/.test(arg)) {
        const inv = await db.prepare('SELECT * FROM workshop_group_invites WHERE id=? AND class_id=? AND revoked_at IS NULL').bind(arg, gid).first();
        if (!inv) fail(404, 'invite_not_found');
        if (!sub && m === 'DELETE') {
          await db.prepare('UPDATE workshop_group_invites SET revoked_at=? WHERE id=?').bind(t, arg).run();
          return {ok: true};
        }
        if (sub === 'regenerate' && m === 'POST') {
          await limit(env, 'wsg-invite:' + uid, 30, 3600);
          await db.prepare('UPDATE workshop_group_invites SET revoked_at=? WHERE id=?').bind(t, arg).run();
          const life = inv.expires_at == null ? null : Math.max(86400, inv.expires_at - inv.created_at);
          return makeInvite(env, gid, uid, t, life, inv.max_uses);
        }
      }
    }
    fail(405, 'method_not_allowed');
  };
}
