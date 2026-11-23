/* Handouts in the Learn guide (#/learn/guide?tab=handouts): PDFs the owner uploads from the site.
   - GET    /api/learn/handouts               public handouts, newest first; ?unit=mechanics/kinematics&level=3 narrow it;
                                              an administrator adds ?all=1 to see hidden ones too
   - GET    /api/learn/handouts/:id/file      the PDF itself, inline, from R2 (a hidden one for administrators only)
   - POST   /api/learn/handouts               administrators: multipart/form-data (field "file") or JSON with file_base64
   - PATCH  /api/learn/handouts/:id           administrators: titles, summaries, unit, level, status
   - DELETE /api/learn/handouts/:id           administrators: the row and its R2 object
   Files go to the existing R2 binding env.LAB_PAGES under handouts/. No new binding, variable or secret. */

export const HANDOUT_SCHEMA = [
  `CREATE TABLE IF NOT EXISTS handouts (
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     title_ko TEXT NOT NULL DEFAULT '',
     title_en TEXT NOT NULL DEFAULT '',
     summary_ko TEXT NOT NULL DEFAULT '',
     summary_en TEXT NOT NULL DEFAULT '',
     unit TEXT,
     level INTEGER,
     file_key TEXT NOT NULL,
     file_name TEXT NOT NULL,
     bytes INTEGER NOT NULL,
     status TEXT NOT NULL DEFAULT 'hidden' CHECK (status IN ('public','hidden')),
     author_id INTEGER NOT NULL,
     created_at INTEGER NOT NULL,
     updated_at INTEGER NOT NULL)`,
  `CREATE INDEX IF NOT EXISTS handouts_public ON handouts(status, unit, level)`
];
export const HANDOUT_MAX_BYTES = 25 * 1024 * 1024;
export const HANDOUT_PREFIX = 'handouts/';
const TITLE_MAX = 120, SUMMARY_MAX = 600, NAME_MAX = 120;
/* a unit of the learning path (learn-path.js SUBTOPICS keys look like mechanics/kinematics) and a step 1–10 */
const UNIT = /^[a-z]{2,12}\/[a-z_]{2,24}$/;
const COLS = 'id,title_ko,title_en,summary_ko,summary_en,unit,level,file_name,bytes,status,created_at,updated_at';

const ready = new WeakSet();
export async function ensureHandoutSchema(env) {
  if (ready.has(env.DB)) return;
  for (const sql of HANDOUT_SCHEMA) await env.DB.prepare(sql).run();
  ready.add(env.DB);
}

/* "%PDF-" at the start of the file */
export const isPdf = bytes => bytes && bytes.length >= 5 && bytes[0] === 0x25 && bytes[1] === 0x50 && bytes[2] === 0x44 && bytes[3] === 0x46 && bytes[4] === 0x2d;

/* a file name that is safe in a header and still says what the file is */
export function cleanFileName(name) {
  let n = String(name || '').split(/[\\/]/).pop().normalize('NFC').replace(/[\u0000-\u001f\u007f"]/g, '').replace(/\s+/g, ' ').trim();
  if (!/\.pdf$/i.test(n)) n = (n || 'handout') + '.pdf';
  if (n.length > NAME_MAX) n = n.slice(0, NAME_MAX - 4).trim() + '.pdf';
  return n;
}
const asciiName = n => n.replace(/[^\x20-\x7e]/g, '_').replace(/[;\\]/g, '_');

export function createHandoutRouter({HttpError, needUser, limit, now, bad, isAdmin}) {
  const field = (v, max, code) => {
    if (v == null) return '';
    if (typeof v !== 'string') bad(code);
    const s = v.replace(/\r\n?/g, '\n').replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, '').trim();
    if (s.length > max) bad(code);
    return s;
  };
  const unitOf = v => v == null || v === '' ? null : typeof v === 'string' && UNIT.test(v) ? v : bad('bad_unit');
  const levelOf = v => {
    if (v == null || v === '') return null;
    const n = Number(v);
    return Number.isInteger(n) && n >= 1 && n <= 10 ? n : bad('bad_level');
  };
  const statusOf = v => v == null || v === '' ? 'hidden' : v === 'public' || v === 'hidden' ? v : bad('bad_status');
  const admin = me => { needUser(me); if (!isAdmin(me)) throw new HttpError(403, 'forbidden'); return me; };
  const view = r => ({...r, file: `/api/learn/handouts/${r.id}/file`});

  async function readUpload(req, body) {
    const declared = Number(req?.headers?.get?.('Content-Length') || 0);
    /* base64 is a third larger than the file; a form adds a little for its boundaries */
    if (declared > Math.ceil(HANDOUT_MAX_BYTES * 4 / 3) + 64 * 1024) throw new HttpError(413, 'file_too_large');
    const type = req?.headers?.get?.('Content-Type') || '';
    let fields, bytes, name;
    if (type.startsWith('multipart/form-data')) {
      let form;
      try { form = await req.formData(); } catch { bad('bad_form'); }
      const file = form.get('file');
      if (!file || typeof file === 'string' || typeof file.arrayBuffer !== 'function') bad('file_required');
      if (file.size > HANDOUT_MAX_BYTES) throw new HttpError(413, 'file_too_large');
      bytes = new Uint8Array(await file.arrayBuffer());
      name = file.name;
      fields = {};
      for (const k of ['title_ko', 'title_en', 'summary_ko', 'summary_en', 'unit', 'level', 'status']) { const v = form.get(k); if (typeof v === 'string') fields[k] = v; }
    } else {
      fields = body || {};
      if (typeof fields.file_base64 !== 'string' || !fields.file_base64) bad('file_required');
      const b64 = fields.file_base64.replace(/^data:application\/pdf;base64,/, '').replace(/\s+/g, '');
      if (b64.length > Math.ceil(HANDOUT_MAX_BYTES * 4 / 3) + 4) throw new HttpError(413, 'file_too_large');
      if (!/^[A-Za-z0-9+/]*={0,2}$/.test(b64)) bad('bad_file');
      try { bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0)); } catch { bad('bad_file'); }
      name = fields.file_name;
    }
    if (!bytes.length) bad('file_required');
    if (bytes.length > HANDOUT_MAX_BYTES) throw new HttpError(413, 'file_too_large');
    if (!isPdf(bytes)) throw new HttpError(415, 'pdf_only');
    return {fields, bytes, name: cleanFileName(name)};
  }

  return async function handoutRoute(p, m, body, me, req, env) {
    if (p !== '/api/learn/handouts' && !p.startsWith('/api/learn/handouts/')) return undefined;
    await ensureHandoutSchema(env);
    const DB = env.DB, t = now();

    if (p === '/api/learn/handouts' && m === 'GET') {
      const url = req?.url ? new URL(req.url) : null, q = url?.searchParams;
      const all = q?.get('all') === '1' && me && isAdmin(me);
      const where = [], args = [];
      if (!all) where.push("status='public'");
      const unit = q?.get('unit'), level = q?.get('level');
      if (unit) { if (UNIT.test(unit)) { where.push('unit=?'); args.push(unit); } else if (/^[a-z]{2,12}$/.test(unit)) { where.push("unit LIKE ?"); args.push(unit + '/%'); } else bad('bad_unit'); }
      if (level) { where.push('level=?'); args.push(levelOf(level)); }
      const rows = (await DB.prepare(`SELECT ${COLS} FROM handouts${where.length ? ' WHERE ' + where.join(' AND ') : ''} ORDER BY unit IS NULL, unit, level IS NULL, level, id DESC LIMIT 300`).bind(...args).all()).results;
      return {handouts: rows.map(view), admin: !!(me && isAdmin(me))};
    }

    if (p === '/api/learn/handouts' && m === 'POST') {
      admin(me);
      await limit(env, 'handout-up:' + me.id, 40, 3600);
      if (!env.LAB_PAGES) throw new HttpError(503, 'r2_unavailable');
      const {fields, bytes, name} = await readUpload(req, body);
      const row = {
        title_ko: field(fields.title_ko, TITLE_MAX, 'bad_title'), title_en: field(fields.title_en, TITLE_MAX, 'bad_title'),
        summary_ko: field(fields.summary_ko, SUMMARY_MAX, 'bad_summary'), summary_en: field(fields.summary_en, SUMMARY_MAX, 'bad_summary'),
        unit: unitOf(fields.unit), level: levelOf(fields.level), status: statusOf(fields.status)
      };
      if (!row.title_ko && !row.title_en) bad('bad_title');
      const key = HANDOUT_PREFIX + crypto.randomUUID() + '.pdf';
      await env.LAB_PAGES.put(key, bytes, {httpMetadata: {contentType: 'application/pdf'}, customMetadata: {name}});
      try {
        const r = await DB.prepare(`INSERT INTO handouts(title_ko,title_en,summary_ko,summary_en,unit,level,file_key,file_name,bytes,status,author_id,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) RETURNING ${COLS}`).bind(row.title_ko, row.title_en, row.summary_ko, row.summary_en, row.unit, row.level, key, name, bytes.length, row.status, me.id, t, t).first();
        return {handout: view(r)};
      } catch (e) { await env.LAB_PAGES.delete(key).catch(() => {}); throw e; }
    }

    const mm = /^\/api\/learn\/handouts\/(\d{1,12})(\/file)?$/.exec(p);
    if (!mm) throw new HttpError(404, 'not_found');
    const id = +mm[1];

    if (mm[2] && (m === 'GET' || m === 'HEAD')) {
      const row = await DB.prepare('SELECT id,file_key,file_name,bytes,status,updated_at FROM handouts WHERE id=?').bind(id).first();
      const open = row && (row.status === 'public' || (me && isAdmin(me)));
      if (!open) throw new HttpError(404, 'not_found');
      if (!env.LAB_PAGES) throw new HttpError(503, 'r2_unavailable');
      const obj = await env.LAB_PAGES.get(row.file_key);
      if (!obj) throw new HttpError(404, 'file_missing');
      const etag = obj.httpEtag || `"h${row.id}-${row.updated_at}"`;
      const headers = {
        'Content-Type': 'application/pdf',
        'Content-Disposition': `inline; filename="${asciiName(row.file_name)}"; filename*=UTF-8''${encodeURIComponent(row.file_name)}`,
        /* a public handout can be kept for an hour (and revalidated by its ETag); a hidden one is never stored */
        'Cache-Control': row.status === 'public' ? 'public, max-age=3600, must-revalidate' : 'private, no-store',
        'ETag': etag, 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer',
        'Content-Security-Policy': "default-src 'none'; frame-ancestors 'self' https://haslalab.org https://*.haslalab.org"
      };
      if (obj.size != null) headers['Content-Length'] = String(obj.size);
      if (row.status === 'public' && req?.headers?.get?.('If-None-Match') === etag) { obj.body?.cancel?.(); return new Response(null, {status: 304, headers}); }
      return new Response(m === 'HEAD' ? null : obj.body, {status: 200, headers});
    }
    if (mm[2]) throw new HttpError(404, 'not_found');

    if (m === 'PATCH') {
      admin(me);
      await limit(env, 'handout-edit:' + me.id, 120, 3600);
      const b = body || {}, set = [], args = [];
      for (const [k, max, code] of [['title_ko', TITLE_MAX, 'bad_title'], ['title_en', TITLE_MAX, 'bad_title'], ['summary_ko', SUMMARY_MAX, 'bad_summary'], ['summary_en', SUMMARY_MAX, 'bad_summary']])
        if (k in b) { set.push(k + '=?'); args.push(field(b[k], max, code)); }
      if ('unit' in b) { set.push('unit=?'); args.push(unitOf(b.unit)); }
      if ('level' in b) { set.push('level=?'); args.push(levelOf(b.level)); }
      if ('status' in b) { if (b.status !== 'public' && b.status !== 'hidden') bad('bad_status'); set.push('status=?'); args.push(b.status); }
      if (!set.length) bad('nothing_to_change');
      const cur = await DB.prepare('SELECT title_ko,title_en FROM handouts WHERE id=?').bind(id).first();
      if (!cur) throw new HttpError(404, 'not_found');
      const titleKo = 'title_ko' in b ? field(b.title_ko, TITLE_MAX, 'bad_title') : cur.title_ko, titleEn = 'title_en' in b ? field(b.title_en, TITLE_MAX, 'bad_title') : cur.title_en;
      if (!titleKo && !titleEn) bad('bad_title');
      const r = await DB.prepare(`UPDATE handouts SET ${set.join(',')},updated_at=? WHERE id=? RETURNING ${COLS}`).bind(...args, t, id).first();
      if (!r) throw new HttpError(404, 'not_found');
      return {handout: view(r)};
    }

    if (m === 'DELETE') {
      admin(me);
      const row = await DB.prepare('SELECT file_key FROM handouts WHERE id=?').bind(id).first();
      if (!row) throw new HttpError(404, 'not_found');
      if (env.LAB_PAGES) await env.LAB_PAGES.delete(row.file_key);
      await DB.prepare('DELETE FROM handouts WHERE id=?').bind(id).run();
      return {ok: true};
    }
    throw new HttpError(404, 'not_found');
  };
}
