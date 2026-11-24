/* The Workshop's sharing place, 작품 공유 (#/workshop/share): members publish what they made in the Workshop's makers —
   a simulation or a Python problem (create.html), a figure (draw.html) or a problem set (teach.html) — and anyone can
   browse, run, like, keep, comment on and remix it.

   The store is the creations table (creations.js): one row per project, kind 'sim' | 'code' | 'figure' | 'set', with
   forked_from linking a remix to its original, plays as the view count and creation_likes as the likes. What a shared
   project adds lives beside it in share_meta (description, how to use, notes and credits, tags, topic, thumbnail, a
   figure's scene or a set's problems, staff pick), share_favs and share_comments. A creation published from create.html
   before this place existed shows here too, with no thumbnail and the topic "other".

   Routes (all JSON unless noted):
     GET    /api/share?tab=week|popular|new|featured&type=sim|python|figure|set&topic=&q=&sort=&page=&user=&fav=1
     POST   /api/share                         publish (new, or a draft/creation of one's own with creation_id)
     GET    /api/share/user/:id                an author's shared projects
     GET    /api/share/:id                     one project (payload included)
     PATCH  /api/share/:id                     owner edits
     DELETE /api/share/:id                     owner unpublishes; staff hide (and the owner cannot publish it again)
     GET    /api/share/:id/thumb               the thumbnail image (PNG/JPEG/WebP, or an SVG that passed svgSafe)
     POST   /api/share/:id/(like|fav)  {on}    idempotent per member
     POST   /api/share/:id/view                once a day per visitor (the same key as creations' play)
     POST   /api/share/:id/remix               a private draft copy linked to the original: {id, edit}
     POST   /api/share/:id/feature {on}        staff pick (admins only)
     POST   /api/share/:id/report  {reason}    into the community's reports table (kind 'share')
     GET    /api/share/:id/comments            POST the same with {body, parent_id}
     PATCH|DELETE /api/share/comments/:cid     the writer or an admin; POST /api/share/comments/:cid/report

   Safety: the page never puts a member's HTML or SVG into its own document. Descriptions are plain text (tags are
   stripped here; the page escapes and draws a small markdown subset), comments are escaped, thumbnails are served as
   images from this API with a CSP that allows nothing, an SVG is accepted only when it has no script, event handler,
   link, foreign object, style sheet or external reference, and a project's code runs only in sim-sandbox.html (an
   opaque-origin frame) or in a Pyodide worker in the reader's browser. */
import {ensureCreationSchema, LIMITS as CL} from './creations.js';
import {validateScene} from '../../draw-scene.mjs';

export const SHARE_SCHEMA = [
  `CREATE TABLE IF NOT EXISTS share_meta (
     creation_id INTEGER PRIMARY KEY,
     topic TEXT NOT NULL DEFAULT 'other',
     tags TEXT NOT NULL DEFAULT '',
     descr TEXT NOT NULL DEFAULT '',
     howto TEXT NOT NULL DEFAULT '',
     notes TEXT NOT NULL DEFAULT '',
     thumb TEXT NOT NULL DEFAULT '',
     payload TEXT,
     featured INTEGER NOT NULL DEFAULT 0,
     featured_at INTEGER,
     mod_hidden INTEGER NOT NULL DEFAULT 0,
     favs INTEGER NOT NULL DEFAULT 0,
     n_comments INTEGER NOT NULL DEFAULT 0,
     shared_at INTEGER,
     updated_at INTEGER)`,
  `CREATE INDEX IF NOT EXISTS share_meta_topic ON share_meta(topic)`,
  `CREATE INDEX IF NOT EXISTS share_meta_featured ON share_meta(featured, featured_at DESC)`,
  `CREATE INDEX IF NOT EXISTS creations_fork ON creations(forked_from)`,
  `CREATE TABLE IF NOT EXISTS share_favs (
     creation_id INTEGER NOT NULL,
     user_id INTEGER NOT NULL,
     created_at INTEGER NOT NULL,
     PRIMARY KEY (creation_id, user_id))`,
  `CREATE INDEX IF NOT EXISTS share_favs_user ON share_favs(user_id, created_at DESC)`,
  `CREATE TABLE IF NOT EXISTS share_comments (
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     creation_id INTEGER NOT NULL,
     parent_id INTEGER,
     user_id INTEGER NOT NULL,
     body TEXT NOT NULL,
     created_at INTEGER NOT NULL,
     updated_at INTEGER)`,
  `CREATE INDEX IF NOT EXISTS share_comments_item ON share_comments(creation_id, id)`
];
/* the page's types and the creations kinds they are kept as */
export const TYPES = {sim: 'sim', python: 'code', figure: 'figure', set: 'set'};
const TYPE_OF = {sim: 'sim', code: 'python', figure: 'figure', set: 'set'};
export const TOPICS = ['mechanics', 'em', 'thermal', 'optics', 'waves', 'modern', 'other'];
export const SHARE_LIMITS = {title: 80, descr: 3000, howto: 3000, notes: 2000, tag: 20, tags: 8, comment: 2000, reason: 300,
  thumbBytes: 200 * 1024, figureJson: 120000, setJson: 400000, setItems: 100, figSrc: 300000};
const PER_PAGE = 24;
const ready = new WeakSet();
export async function ensureShareSchema(env) {
  if (ready.has(env.DB)) return;
  await ensureCreationSchema(env);
  for (const sql of SHARE_SCHEMA) await env.DB.prepare(sql).run();
  ready.add(env.DB);
}

/* ── cleaning what members send ── */
const CTRL = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g;
/** plain text: no control characters, no HTML tags or comments (a bare "a < b" stays), at most max characters */
export function plainText(v, max) {
  if (v == null) return '';
  if (typeof v !== 'string') return null;
  const s = v.replace(/\r\n?/g, '\n').replace(CTRL, '').replace(/<!--[\s\S]*?-->/g, '').replace(/<\/?[A-Za-z!][^>]*>/g, '').trim();
  return s.length > max ? null : s;
}
/** tags: at most 8 short words, letters and digits of any script, deduplicated; '#' and spaces at the ends dropped */
export function cleanTags(v) {
  if (v == null || v === '') return [];
  const list = typeof v === 'string' ? v.split(/[,#\n]/) : Array.isArray(v) ? v : null;
  if (!list) return null;
  const out = [];
  for (const raw of list) {
    if (typeof raw !== 'string') return null;
    const t = raw.normalize('NFKC').replace(/^#+/, '').replace(/\s+/g, ' ').trim().toLowerCase();
    if (!t) continue;
    if ([...t].length > SHARE_LIMITS.tag || !/^[\p{L}\p{N}][\p{L}\p{N} _.+\-]*$/u.test(t)) return null;
    if (!out.includes(t)) out.push(t);
  }
  return out.length > SHARE_LIMITS.tags ? null : out;
}
const b64bytes = s => s.length * 3 / 4 - (s.endsWith('==') ? 2 : s.endsWith('=') ? 1 : 0);
const MAGIC = {png: b => b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47,
  jpeg: b => b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff,
  webp: b => String.fromCharCode(b[0], b[1], b[2], b[3]) === 'RIFF' && String.fromCharCode(b[8], b[9], b[10], b[11]) === 'WEBP'};
/** an SVG document with nothing that can run, load or link: true only for plain drawing markup */
export function svgSafe(text) {
  if (typeof text !== 'string') return false;
  const s = text.replace(/^﻿/, '').replace(/^\s*<\?xml[^?]*\?>/, '').trim();
  if (!/^<svg[\s>]/i.test(s) || !/<\/svg>\s*$/i.test(s)) return false;
  return ![/<!DOCTYPE|<!ENTITY|<!\[CDATA\[|<\?/i,
    /<\s*\/?\s*(?:[a-z]+:)?(?:script|foreignObject|iframe|object|embed|style|link|meta|image|img|use|a|animate\w*|set|handler|listener|audio|video|canvas|html|body|base|form|input|textarea|button)\b/i,
    /\son[a-z\-]+\s*=/i, /(?:^|[\s"'])(?:xlink:)?(?:href|src)\s*=/i, /\bstyle\s*=\s*["'][^"']*(?:url|@import|expression)/i,
    /javascript:|vbscript:|data:/i, /url\(\s*(?!['"]?#)/i, /@import|expression\s*\(/i, /&#/].some(re => re.test(s));
}
const utf8 = s => new TextEncoder().encode(s);
const toB64 = bytes => { let bin = ''; for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000)); return btoa(bin); };
/** a thumbnail as a data URL: a real PNG, JPEG or WebP, or an SVG that passed svgSafe (stored as base64), at most
 *  200 KB; '' for none, null when it is refused */
export function cleanThumb(v, maxBytes = SHARE_LIMITS.thumbBytes) {
  if (v == null || v === '') return '';
  if (typeof v !== 'string' || v.length > maxBytes * 1.4 + 100) return null;
  let m = /^data:image\/(png|jpeg|webp);base64,([A-Za-z0-9+/]+={0,2})$/.exec(v);
  if (m) {
    if (m[2].length % 4 || b64bytes(m[2]) > maxBytes || b64bytes(m[2]) < 24) return null;
    let head; try { head = Uint8Array.from(atob(m[2].slice(0, 16)), c => c.charCodeAt(0)); } catch { return null; }
    return MAGIC[m[1]](head) ? v : null;
  }
  m = /^data:image\/svg\+xml(?:;charset=utf-?8)?(;base64)?,([\s\S]*)$/i.exec(v);
  if (!m) return null;
  let svg;
  try {
    if (m[1]) { if (!/^[A-Za-z0-9+/]+={0,2}$/.test(m[2])) return null; svg = new TextDecoder('utf-8', {fatal: true}).decode(Uint8Array.from(atob(m[2]), c => c.charCodeAt(0))); }
    else svg = decodeURIComponent(m[2]);
  } catch { return null; }
  const bytes = utf8(svg);
  if (bytes.length > maxBytes || !svgSafe(svg)) return null;
  return 'data:image/svg+xml;base64,' + toB64(bytes);
}

/* ── payloads by type ── */
const str = (v, max, min = 0) => typeof v === 'string' && v.length <= max && v.trim().length >= min ? v : null;
const num = (v, lo, hi, d) => v == null ? d : typeof v === 'number' && Number.isFinite(v) && v >= lo && v <= hi ? v : null;
/** a problem set (teach.js's paper): its heading and items, each a HaslaLab problem key or the member's own problem;
 *  only the known fields are kept, an item's figure only when it is a safe SVG */
export function cleanSet(p) {
  if (!p || typeof p !== 'object' || Array.isArray(p)) return null;
  if (JSON.stringify(p).length > SHARE_LIMITS.setJson) return 'too_large';
  const items = Array.isArray(p.items) ? p.items : null;
  if (!items || !items.length || items.length > SHARE_LIMITS.setItems) return null;
  const out = {title: plainText(p.title, 120) ?? '', info: plainText(p.info, 300) ?? '', minutes: num(+p.minutes || 0, 0, 600, 0) ?? 0, items: []};
  for (const it of items) {
    if (!it || typeof it !== 'object' || typeof it.key !== 'string' || !/^[\w:.~\-]{1,80}$/.test(it.key)) return null;
    const o = {key: it.key, pts: num(it.pts, 0, 100, 3)};
    if (o.pts == null) return null;
    if (it.own != null) {
      const w = it.own; if (typeof w !== 'object') return null;
      const own = {q: plainText(w.q, 6000), answer: plainText(w.answer, 400), unit: plainText(w.unit, 24), sol: plainText(w.sol, 6000)};
      if (Object.values(own).some(x => x == null) || !own.q) return null;
      if (w.choices != null) {
        if (!Array.isArray(w.choices) || w.choices.length > 10) return null;
        own.choices = w.choices.map(c => plainText(c, 500)); if (own.choices.some(c => c == null)) return null;
        own.correct = Number.isInteger(w.correct) && w.correct >= 0 && w.correct < own.choices.length ? w.correct : null;
      }
      if (w.fig && typeof w.fig === 'object') {
        const src = cleanThumb(w.fig.src, SHARE_LIMITS.figSrc);
        if (src && src.startsWith('data:image/svg+xml')) own.fig = {src, w: num(+w.fig.w || 800, 40, 2000, 800) ?? 800, h: num(+w.fig.h || 400, 20, 3000, 400) ?? 400};
      }
      o.own = own;
    } else if (it.key.startsWith('own:')) return null;
    out.items.push(o);
  }
  return out;
}
/** the payload of one type as the columns it is kept in, or a bad_payload error */
function payloadColumns(type, p, bad) {
  if (!p || typeof p !== 'object' || Array.isArray(p)) bad('bad_payload');
  if (type === 'sim') {
    const code = str(p.code, CL.code, 1), body = str(p.question ?? '', CL.body), answer = str(p.answer ?? '', CL.answer), unit = str(p.answerUnit ?? '', CL.unit);
    if (code == null || body == null || answer == null || unit == null) bad('bad_payload');
    return {code, body, answer: answer.trim() || null, unit: unit.trim(), starter: '', grader: '', payload: null};
  }
  if (type === 'python') {
    const body = str(p.statement, CL.body, 1), starter = str(p.starter ?? '', CL.starter), grader = str(p.grader, CL.grader, 1);
    if (body == null || starter == null || grader == null || !/def\s+grade\s*\(/.test(grader)) bad('bad_payload');
    return {code: '', body, starter, grader, answer: null, unit: '', payload: null};
  }
  if (type === 'figure') {
    const scene = p.scene && typeof p.scene === 'object' ? p.scene : p;
    if (JSON.stringify(scene).length > SHARE_LIMITS.figureJson) bad('payload_too_large');
    const r = validateScene(scene, {lenient: true});
    if (!r.scene || !Array.isArray(r.scene.objects) || !r.scene.objects.length) bad('bad_payload');
    return {code: '', body: '', starter: '', grader: '', answer: null, unit: '', payload: JSON.stringify({scene: r.scene})};
  }
  const set = cleanSet(p);
  if (set === 'too_large') bad('payload_too_large');
  if (!set) bad('bad_payload');
  return {code: '', body: '', starter: '', grader: '', answer: null, unit: '', payload: JSON.stringify(set)};
}

const LIST_COLS = `c.id,c.kind,c.title,c.summary,c.plays AS views,c.likes,c.forked_from,c.created_at,c.updated_at,c.user_id,u.nickname,u.avatar AS av,
  COALESCE(s.topic,'other') AS topic,COALESCE(s.tags,'') AS tags,COALESCE(s.favs,0) AS favs,COALESCE(s.n_comments,0) AS comments,
  COALESCE(s.featured,0) AS featured,length(COALESCE(s.thumb,''))>0 AS has_thumb,COALESCE(s.shared_at,c.created_at) AS shared_at,
  (SELECT COUNT(*) FROM creations r WHERE r.forked_from=c.id AND r.status='public') AS remixes`;
const FROM = `FROM creations c LEFT JOIN users u ON u.id=c.user_id LEFT JOIN share_meta s ON s.creation_id=c.id`;
const VISIBLE = `c.status='public' AND c.kind IN ('sim','code','figure','set') AND COALESCE(s.mod_hidden,0)=0`;
const SORTS = {
  new: 'COALESCE(s.shared_at,c.created_at) DESC, c.id DESC',
  popular: '(c.likes*3+COALESCE(s.favs,0)*2+c.plays+(SELECT COUNT(*) FROM creations r WHERE r.forked_from=c.id AND r.status=\'public\')*4) DESC, c.id DESC',
  likes: 'c.likes DESC, c.id DESC', views: 'c.plays DESC, c.id DESC',
  remixes: '(SELECT COUNT(*) FROM creations r WHERE r.forked_from=c.id AND r.status=\'public\') DESC, c.id DESC',
  featured: 's.featured_at DESC, c.id DESC'};
const card = r => ({...r, type: TYPE_OF[r.kind], kind: undefined, tags: r.tags ? r.tags.split(',').filter(Boolean) : [], has_thumb: !!r.has_thumb, featured: !!r.featured,
  av: r.av && /^[A-Za-z0-9_-]{8,32}$/.test(r.av) ? r.av : null});
const likeEsc = s => s.replace(/[\\%_]/g, c => '\\' + c);

export function createShareRouter({HttpError, needUser, limit, now, bad, clientIp, text, isStaff = me => me?.role === 'admin'}) {
  const field = (body, key, max, code = 'bad_' + key) => { const v = plainText(body?.[key], max); if (v == null) bad(code); return v; };
  /** the fields of a publish or an edit; partial: only those sent */
  function meta(body, partial) {
    const o = {};
    const has = k => !partial || k in (body || {});
    if (has('title')) { o.title = field(body, 'title', SHARE_LIMITS.title); if (!o.title) bad('bad_title'); }
    if (has('description')) o.descr = field(body, 'description', SHARE_LIMITS.descr, 'bad_description');
    if (has('howto')) o.howto = field(body, 'howto', SHARE_LIMITS.howto);
    if (has('notes')) o.notes = field(body, 'notes', SHARE_LIMITS.notes);
    if (has('tags')) { const t = cleanTags(body?.tags); if (t == null) bad('bad_tags'); o.tags = t.length ? ',' + t.join(',') + ',' : ''; }
    const topic = body?.topic ?? (TOPICS.includes(body?.unit) ? body.unit : undefined);
    if (!partial || topic !== undefined) { if (topic != null && topic !== '' && !TOPICS.includes(topic)) bad('bad_topic'); o.topic = topic || 'other'; }
    if (has('thumbnail')) { const t = cleanThumb(body?.thumbnail); if (t == null) bad('bad_thumbnail'); o.thumb = t; }
    return o;
  }
  const summaryOf = d => (d || '').split('\n').find(l => l.trim())?.trim().slice(0, CL.summary) || '';
  async function load(DB, id) {
    return DB.prepare(`SELECT c.*,u.nickname,u.avatar AS av,u.deleted AS gone,s.creation_id AS has_meta,s.topic,s.tags,s.descr,s.howto,s.notes,length(COALESCE(s.thumb,'')) AS thumb_len,
      s.payload,s.featured,s.mod_hidden,s.favs,s.n_comments,s.shared_at FROM creations c LEFT JOIN users u ON u.id=c.user_id LEFT JOIN share_meta s ON s.creation_id=c.id WHERE c.id=?`).bind(id).first();
  }
  const visibleTo = (row, me) => row && (row.status === 'public' && !row.mod_hidden || me && (row.user_id === me.id || isStaff(me)));
  async function writeMeta(DB, id, o, t, shared) {
    await DB.prepare(`INSERT INTO share_meta(creation_id,topic,tags,descr,howto,notes,thumb,payload,shared_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)
      ON CONFLICT(creation_id) DO UPDATE SET topic=COALESCE(?,topic),tags=COALESCE(?,tags),descr=COALESCE(?,descr),howto=COALESCE(?,howto),notes=COALESCE(?,notes),
      thumb=COALESCE(?,thumb),payload=COALESCE(?,payload),shared_at=COALESCE(shared_at,?),updated_at=?`)
      .bind(id, o.topic ?? 'other', o.tags ?? '', o.descr ?? '', o.howto ?? '', o.notes ?? '', o.thumb ?? '', o.payload ?? null, shared ? t : null, t,
        o.topic ?? null, o.tags ?? null, o.descr ?? null, o.howto ?? null, o.notes ?? null, o.thumb ?? null, o.payload ?? null, shared ? t : null, t).run();
  }
  async function list(DB, q, me, extra = {}) {
    const where = [VISIBLE], args = [];
    const type = TYPES[q.get('type')];
    if (type) { where.push('c.kind=?'); args.push(type); }
    const topic = q.get('topic');
    if (TOPICS.includes(topic)) { where.push("COALESCE(s.topic,'other')=?"); args.push(topic); }
    const needle = (q.get('q') || '').normalize('NFKC').trim().slice(0, 60);
    if (needle) { const k = '%' + likeEsc(needle.toLowerCase()) + '%'; where.push("(lower(c.title) LIKE ? ESCAPE '\\' OR lower(c.summary) LIKE ? ESCAPE '\\' OR COALESCE(s.tags,'') LIKE ? ESCAPE '\\' OR lower(u.nickname) LIKE ? ESCAPE '\\')"); args.push(k, k, k, k); }
    const user = parseInt(extra.user ?? q.get('user'));
    if (user > 0) { where.push('c.user_id=?'); args.push(user); }
    if (q.get('fav') === '1') { needUser(me); where.push('EXISTS(SELECT 1 FROM share_favs f WHERE f.creation_id=c.id AND f.user_id=?)'); args.push(me.id); }
    const tab = q.get('tab');
    let order = SORTS[q.get('sort')] || (tab === 'new' ? SORTS.new : SORTS.popular), per = PER_PAGE, orderArgs = [];
    if (tab === 'featured') { where.push('s.featured=1'); order = SORTS[q.get('sort')] || SORTS.featured; }
    if (tab === 'week') {
      /* this week's favourites: likes given in the last seven days, then new projects with the most views */
      const since = now() - 7 * 86400;
      where.push('(c.created_at>? OR EXISTS(SELECT 1 FROM creation_likes l WHERE l.creation_id=c.id AND l.created_at>?))'); args.push(since, since);
      order = '(SELECT COUNT(*) FROM creation_likes l WHERE l.creation_id=c.id AND l.created_at>?) DESC, c.likes DESC, c.plays DESC, c.id DESC'; orderArgs = [since]; per = 8;
    }
    const page = Math.max(1, Math.min(200, parseInt(q.get('page')) || 1));
    const rows = (await DB.prepare(`SELECT ${LIST_COLS} ${FROM} WHERE ${where.join(' AND ')} ORDER BY ${order} LIMIT ? OFFSET ?`)
      .bind(...args, ...orderArgs, per + 1, (page - 1) * per).all()).results || [];
    return {items: rows.slice(0, per).map(card), more: rows.length > per, page};
  }

  return async function shareRoute(p, m, body, me, req, env) {
    if (p !== '/api/share' && !p.startsWith('/api/share/')) return undefined;
    await ensureShareSchema(env);
    const DB = env.DB, t = now(), q = new URL(req?.url || 'https://x/').searchParams;
    if (p === '/api/share' && m === 'GET') return list(DB, q, me);

    /* publish: a new project, or one of the member's own creations/drafts (creation_id) made public with its details */
    if (p === '/api/share' && m === 'POST') {
      needUser(me);
      const type = Object.hasOwn(TYPES, body?.type) ? body.type : bad('bad_type');
      let id = Number.isInteger(body?.creation_id) ? body.creation_id : null, cols = null;
      /* a new project sends every field; publishing an existing one keeps what it does not send */
      const o = meta(body, !!id);
      if (id) {
        const row = await load(DB, id);
        o.title ??= row?.title;
        if (!row || row.user_id !== me.id) throw new HttpError(404, 'not_found');
        if (row.mod_hidden) throw new HttpError(403, 'hidden_by_staff');
        if (TYPE_OF[row.kind] !== type) bad('bad_type');
        await limit(env, 'creation-edit:' + me.id, 120, 3600);
        if (body?.payload != null) cols = payloadColumns(type, body.payload, bad);
        await DB.prepare(`UPDATE creations SET title=?,summary=COALESCE(?,summary),status='public',updated_at=?${cols ? ',code=?,body=?,starter=?,grader=?,answer=?,unit=?' : ''} WHERE id=?`)
          .bind(o.title, o.descr !== undefined ? summaryOf(o.descr) : null, t, ...(cols ? [cols.code, cols.body, cols.starter, cols.grader, cols.answer, cols.unit] : []), id).run();
      } else {
        await limit(env, 'creation-new:' + me.id, 20, 86400);
        cols = payloadColumns(type, body?.payload, bad);
        const from = Number.isInteger(body?.remix_of) ? body.remix_of : null;
        const r = await DB.prepare(`INSERT INTO creations(user_id,kind,title,summary,body,code,starter,grader,answer,unit,forked_from,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)`).bind(me.id, TYPES[type], o.title, summaryOf(o.descr), cols.body, cols.code, cols.starter, cols.grader, cols.answer, cols.unit, from, t, t).run();
        id = r.meta.last_row_id;
      }
      await writeMeta(DB, id, {...o, payload: cols?.payload ?? undefined}, t, true);
      return {id, url: '#/workshop/share/' + id};
    }

    let r = /^\/api\/share\/user\/(\d+)$/.exec(p);
    if (r && m === 'GET') {
      const u = await DB.prepare('SELECT id,nickname,avatar,created_at,deleted FROM users WHERE id=?').bind(+r[1]).first();
      if (!u || u.deleted) throw new HttpError(404, 'not_found');
      const items = await list(DB, q, me, {user: u.id});
      const sum = await DB.prepare(`SELECT COUNT(*) AS n,COALESCE(SUM(c.likes),0) AS likes,COALESCE(SUM(c.plays),0) AS views ${FROM} WHERE ${VISIBLE} AND c.user_id=?`).bind(u.id).first();
      return {user: {id: u.id, nickname: u.nickname, av: u.avatar && /^[A-Za-z0-9_-]{8,32}$/.test(u.avatar) ? u.avatar : null, joined: u.created_at},
        totals: {projects: sum?.n || 0, likes: sum?.likes || 0, views: sum?.views || 0}, ...items};
    }

    /* comments on a shared project: the community's rules (one level of replies, the writer or an admin edits and
       deletes, 20 per ten minutes) in a table of their own */
    r = /^\/api\/share\/comments\/(\d+)(\/report)?$/.exec(p);
    if (r) {
      const c = await DB.prepare('SELECT * FROM share_comments WHERE id=?').bind(+r[1]).first();
      if (!c) throw new HttpError(404, 'not_found');
      needUser(me);
      if (r[2] && m === 'POST') {
        await limit(env, 'rep:' + me.id, 10, 3600);
        await DB.prepare('INSERT OR IGNORE INTO reports(kind,target_id,user_id,reason,created_at) VALUES(?,?,?,?,?)').bind('share_comment', c.id, me.id, text(body?.reason, SHARE_LIMITS.reason, 'bad_reason'), t).run();
        return {ok: true};
      }
      if (c.user_id !== me.id && !isStaff(me)) throw new HttpError(403, 'forbidden');
      if (m === 'PATCH') {
        await DB.prepare('UPDATE share_comments SET body=?,updated_at=? WHERE id=?').bind(text(body?.body, SHARE_LIMITS.comment, 'bad_body'), t, c.id).run();
        return {ok: true};
      }
      if (m === 'DELETE') {
        await DB.prepare('DELETE FROM share_comments WHERE id=? OR parent_id=?').bind(c.id, c.id).run();
        await DB.prepare('UPDATE share_meta SET n_comments=(SELECT COUNT(*) FROM share_comments WHERE creation_id=?) WHERE creation_id=?').bind(c.creation_id, c.creation_id).run();
        return {ok: true};
      }
      throw new HttpError(404, 'not_found');
    }

    r = /^\/api\/share\/(\d+)(?:\/(thumb|like|fav|view|remix|feature|report|comments))?$/.exec(p);
    if (!r) throw new HttpError(404, 'not_found');
    const id = +r[1], act = r[2], row = await load(DB, id);
    if (!visibleTo(row, me) || !Object.hasOwn(TYPE_OF, row.kind)) throw new HttpError(404, 'not_found');
    const owner = !!me && row.user_id === me.id, staff = isStaff(me);

    if (act === 'thumb' && m === 'GET') {
      const th = (await DB.prepare('SELECT thumb FROM share_meta WHERE creation_id=?').bind(id).first())?.thumb || '';
      const mm = /^data:(image\/(?:png|jpeg|webp|svg\+xml));base64,(.+)$/.exec(th);
      if (!mm) throw new HttpError(404, 'not_found');
      const bytes = Uint8Array.from(atob(mm[2]), c => c.charCodeAt(0));
      return new Response(bytes, {headers: {'Content-Type': mm[1], 'Cache-Control': 'public, max-age=300', 'X-Content-Type-Options': 'nosniff',
        'Content-Security-Policy': "default-src 'none'; style-src 'unsafe-inline'; sandbox", 'Cross-Origin-Resource-Policy': 'cross-origin', 'Content-Disposition': 'inline'}});
    }
    if (!act && m === 'GET') {
      const [liked, faved, original, remixes, nRemix] = await Promise.all([
        me ? DB.prepare('SELECT 1 AS y FROM creation_likes WHERE creation_id=? AND user_id=?').bind(id, me.id).first() : null,
        me ? DB.prepare('SELECT 1 AS y FROM share_favs WHERE creation_id=? AND user_id=?').bind(id, me.id).first() : null,
        row.forked_from ? DB.prepare(`SELECT c.id,c.title,c.status,u.nickname,COALESCE(s.mod_hidden,0) AS mod_hidden FROM creations c LEFT JOIN users u ON u.id=c.user_id LEFT JOIN share_meta s ON s.creation_id=c.id WHERE c.id=?`).bind(row.forked_from).first() : null,
        DB.prepare(`SELECT ${LIST_COLS} ${FROM} WHERE ${VISIBLE} AND c.forked_from=? ORDER BY c.id DESC LIMIT 24`).bind(id).all(),
        DB.prepare(`SELECT COUNT(*) AS n FROM creations WHERE forked_from=? AND status='public'`).bind(id).first()]);
      const type = TYPE_OF[row.kind], payload = row.payload ? JSON.parse(row.payload) : null;
      const project = {id, type, title: row.title, description: row.descr ?? row.summary ?? '', howto: row.howto || '', notes: row.notes || '',
        tags: row.tags ? row.tags.split(',').filter(Boolean) : [], topic: row.topic || 'other', status: row.status, featured: !!row.featured, hidden_by_staff: !!row.mod_hidden,
        author: {id: row.user_id, nickname: row.gone ? null : row.nickname, av: !row.gone && row.av && /^[A-Za-z0-9_-]{8,32}$/.test(row.av) ? row.av : null},
        created_at: row.created_at, updated_at: row.updated_at, shared_at: row.shared_at || row.created_at,
        likes: row.likes, views: row.plays, favs: row.favs || 0, comments: row.n_comments || 0, remixes: nRemix?.n || 0, has_thumb: row.thumb_len > 0, mine: owner,
        forked_from: row.forked_from || null,
        ...(type === 'sim' ? {code: row.code, question: row.body, answer: row.answer, answerUnit: row.unit} : {}),
        ...(type === 'python' ? {statement: row.body, starter: row.starter, grader: row.grader} : {}),
        ...(type === 'figure' || type === 'set' ? {payload} : {})};
      const shownOriginal = original && (original.status === 'public' && !original.mod_hidden) ? {id: original.id, title: original.title, nickname: original.nickname} : original ? {id: null, gone: true} : null;
      return {project, liked: !!liked, faved: !!faved, original: shownOriginal, remixList: (remixes.results || []).map(card), staff};
    }
    if (!act && m === 'PATCH') {
      needUser(me);
      if (!owner) throw new HttpError(403, 'not_owner');
      await limit(env, 'creation-edit:' + me.id, 120, 3600);
      const o = meta(body, true), cols = body?.payload != null ? payloadColumns(TYPE_OF[row.kind], body.payload, bad) : null;
      await DB.prepare(`UPDATE creations SET title=COALESCE(?,title),summary=COALESCE(?,summary),updated_at=?${cols ? ',code=?,body=?,starter=?,grader=?,answer=?,unit=?' : ''} WHERE id=?`)
        .bind(o.title ?? null, o.descr !== undefined ? summaryOf(o.descr) : null, t, ...(cols ? [cols.code, cols.body, cols.starter, cols.grader, cols.answer, cols.unit] : []), id).run();
      await writeMeta(DB, id, {...o, payload: cols?.payload ?? undefined}, t, row.status === 'public');
      return {ok: true};
    }
    if (!act && m === 'DELETE') {
      needUser(me);
      if (!owner && !staff) throw new HttpError(403, 'not_owner');
      await DB.prepare("UPDATE creations SET status='hidden',updated_at=? WHERE id=?").bind(t, id).run();
      if (staff && !owner) {
        await writeMeta(DB, id, {}, t, false);
        await DB.prepare('UPDATE share_meta SET mod_hidden=1,featured=0 WHERE creation_id=?').bind(id).run();
      }
      return {ok: true};
    }
    if (act === 'view' && m === 'POST') {
      /* one view per visitor a day: the same key as creations.js's play, so opening it in create.html too counts once */
      try { await limit(env, `creation-play:${id}:${me ? 'm' + me.id : clientIp(req)}`, 1, 86400); }
      catch (e) { if (e?.status === 429) return {ok: true, counted: false}; throw e; }
      await DB.prepare('UPDATE creations SET plays=plays+1 WHERE id=?').bind(id).run();
      return {ok: true, counted: true};
    }
    if (act === 'like' && m === 'POST') {
      needUser(me);
      await limit(env, 'creation-like:' + me.id, 300, 3600);
      const on = body?.on !== false;
      await (on ? DB.prepare('INSERT OR IGNORE INTO creation_likes(creation_id,user_id,created_at) VALUES(?,?,?)').bind(id, me.id, t)
        : DB.prepare('DELETE FROM creation_likes WHERE creation_id=? AND user_id=?').bind(id, me.id)).run();
      const n = (await DB.prepare('SELECT COUNT(*) AS n FROM creation_likes WHERE creation_id=?').bind(id).first()).n;
      await DB.prepare('UPDATE creations SET likes=? WHERE id=?').bind(n, id).run();
      return {liked: on, likes: n};
    }
    if (act === 'fav' && m === 'POST') {
      needUser(me);
      await limit(env, 'share-fav:' + me.id, 300, 3600);
      const on = body?.on !== false;
      await (on ? DB.prepare('INSERT OR IGNORE INTO share_favs(creation_id,user_id,created_at) VALUES(?,?,?)').bind(id, me.id, t)
        : DB.prepare('DELETE FROM share_favs WHERE creation_id=? AND user_id=?').bind(id, me.id)).run();
      const n = (await DB.prepare('SELECT COUNT(*) AS n FROM share_favs WHERE creation_id=?').bind(id).first()).n;
      await writeMeta(DB, id, {}, t, false);
      await DB.prepare('UPDATE share_meta SET favs=? WHERE creation_id=?').bind(n, id).run();
      return {faved: on, favs: n};
    }
    if (act === 'remix' && m === 'POST') {
      /* a private draft of the member's own, linked to the original; the maker opens it, and publishing it shares it */
      needUser(me);
      if (row.status !== 'public' || row.mod_hidden) throw new HttpError(404, 'not_found');
      await limit(env, 'share-remix:' + me.id, 30, 86400);
      const title = ((plainText(body?.title, SHARE_LIMITS.title) || '') || ('Remix: ' + row.title)).slice(0, SHARE_LIMITS.title);
      const ins = await DB.prepare(`INSERT INTO creations(user_id,kind,title,summary,body,code,starter,grader,answer,unit,status,forked_from,created_at,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,'draft',?,?,?)`).bind(me.id, row.kind, title, row.summary || '', row.body || '', row.code || '', row.starter || '', row.grader || '', row.answer, row.unit || '', id, t, t).run();
      const nid = ins.meta.last_row_id;
      await writeMeta(DB, nid, {topic: row.topic || 'other', tags: row.tags || '', descr: row.descr || '', howto: row.howto || '', notes: (row.notes || ''), thumb: undefined, payload: row.payload ?? undefined}, t, false);
      const type = TYPE_OF[row.kind];
      const edit = type === 'figure' ? '#/workshop/draw?share=' + nid : type === 'set' ? '#/workshop/make?share=' + nid : '#/workshop/create?view=edit&id=' + nid;
      return {id: nid, edit, remix_of: id};
    }
    if (act === 'feature' && m === 'POST') {
      needUser(me);
      if (!staff) throw new HttpError(403, 'forbidden');
      const on = body?.on !== false;
      await writeMeta(DB, id, {}, t, false);
      await DB.prepare('UPDATE share_meta SET featured=?,featured_at=? WHERE creation_id=?').bind(on ? 1 : 0, on ? t : null, id).run();
      return {featured: on};
    }
    if (act === 'report' && m === 'POST') {
      needUser(me);
      await limit(env, 'rep:' + me.id, 10, 3600);
      await DB.prepare('INSERT OR IGNORE INTO reports(kind,target_id,user_id,reason,created_at) VALUES(?,?,?,?,?)').bind('share', id, me.id, text(body?.reason, SHARE_LIMITS.reason, 'bad_reason'), t).run();
      return {ok: true};
    }
    if (act === 'comments' && m === 'GET') {
      const rows = (await DB.prepare(`SELECT c.id,c.parent_id,c.user_id,c.body,c.created_at,c.updated_at,u.nickname,u.avatar AS av,u.deleted AS gone
        FROM share_comments c LEFT JOIN users u ON u.id=c.user_id WHERE c.creation_id=? ORDER BY c.id LIMIT 301`).bind(id).all()).results || [];
      return {comments: rows.slice(0, 300).map(c => ({id: c.id, parent_id: c.parent_id, body: c.body, created_at: c.created_at, updated_at: c.updated_at,
        nickname: c.gone ? null : c.nickname, av: !c.gone && c.av && /^[A-Za-z0-9_-]{8,32}$/.test(c.av) ? c.av : null, mine: !!me && (c.user_id === me.id || staff)})), more: rows.length > 300};
    }
    if (act === 'comments' && m === 'POST') {
      needUser(me);
      if (row.status !== 'public' || row.mod_hidden) throw new HttpError(404, 'not_found');
      await limit(env, 'share-cmt:' + me.id, 20, 600);
      const content = text(body?.body, SHARE_LIMITS.comment, 'bad_body');
      let parent = null;
      if (body?.parent_id) {
        const pc = await DB.prepare('SELECT id,parent_id FROM share_comments WHERE id=? AND creation_id=?').bind(parseInt(body.parent_id) || 0, id).first();
        if (!pc) throw new HttpError(404, 'not_found');
        parent = pc.parent_id || pc.id;
      }
      const ins = await DB.prepare('INSERT INTO share_comments(creation_id,parent_id,user_id,body,created_at) VALUES(?,?,?,?,?)').bind(id, parent, me.id, content, t).run();
      await writeMeta(DB, id, {}, t, false);
      await DB.prepare('UPDATE share_meta SET n_comments=(SELECT COUNT(*) FROM share_comments WHERE creation_id=?) WHERE creation_id=?').bind(id, id).run();
      return {id: ins.meta.last_row_id, comment: {id: ins.meta.last_row_id, parent_id: parent, body: content, created_at: t, updated_at: null, nickname: me.nickname, av: me.avatar || null, mine: true}};
    }
    throw new HttpError(404, 'not_found');
  };
}

/** a member's account is deleted: their favourites go; their comments stay (as in the community) under no name */
export function shareDeletion(env, userId) {
  return [env.DB.prepare('DELETE FROM share_favs WHERE user_id=?').bind(userId)];
}
