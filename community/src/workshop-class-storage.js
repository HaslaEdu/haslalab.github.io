import { ensureLearnSchema } from './learn-services.js';

export const STORAGE_SHARE_SCHEMA = [
  `CREATE TABLE IF NOT EXISTS workshop_class_shares (
    id TEXT PRIMARY KEY,
    owner_id INTEGER NOT NULL,
    class_id INTEGER NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('resource','assignment')),
    title TEXT NOT NULL,
    instructions TEXT NOT NULL DEFAULT '',
    due_at INTEGER,
    file_ids TEXT NOT NULL,
    created_at INTEGER NOT NULL
  )`,
  'CREATE INDEX IF NOT EXISTS workshop_class_shares_class ON workshop_class_shares(class_id, created_at)',
  'CREATE INDEX IF NOT EXISTS workshop_class_shares_owner ON workshop_class_shares(owner_id)'
];

const member = uid => `(c.teacher_id=${uid} OR EXISTS (SELECT 1 FROM class_members m WHERE m.class_id=c.id AND m.user_id=${uid}))`;
const canRead = `c.closed_at IS NULL AND u.deleted=0 AND ${member('s.owner_id')} AND ${member('?')}`;
const access = `FROM workshop_class_shares s JOIN classes c ON c.id=s.class_id JOIN users u ON u.id=s.owner_id`;
const fileLink = `JOIN json_each(s.file_ids) item
  JOIN workshop_files f ON f.id=item.value AND f.owner_id=s.owner_id`;

// Strip answer keys, explanations, marking schemes and source data from student copies.
export function studentWorksheet(doc) {
  const str = (v, n) => typeof v === 'string' ? v.slice(0, n) : '';
  const paper = doc?.format === 'haslalab-paper' && Array.isArray(doc.paper?.items) ? doc.paper : null;
  const single = doc?.format === 'haslalab-problem' && doc.item?.own ? doc.item : null;
  if (!paper && !single) return null;
  const items = (paper ? paper.items : [single]).slice(0, 100).map(row => {
    const item = row?.own || row?.item || {};
    const fig = item.fig?.src;
    return {
      text: str(item.q, 8000),
      choices: (Array.isArray(row?.own ? item.choices : item.plainCh) ? (row?.own ? item.choices : item.plainCh) : []).slice(0, 10).map(c => str(c, 600)),
      points: Number.isFinite(row?.pts) ? Math.max(0, Math.min(100, row.pts)) : null,
      ...(typeof fig === 'string' && fig.length <= 390000 && /^data:image\/svg\+xml;base64,[A-Za-z0-9+/]+=*$/.test(fig) ? {figure: fig} : {})
    };
  });
  return {format: 'haslalab-assignment', title: str(paper?.title, 120), items};
}

export function classStorageRoutes({HttpError, limit, bad, cleanFolder, fileView, download}) {
  const missing = () => { throw new HttpError(404, 'not_found'); };
  const failure = () => { throw new HttpError(405, 'method_not_allowed'); };
  return async function route(path, method, body, uid, now, env) {
    await ensureLearnSchema(env);
    const db = env.DB;
    if (path === '/api/workshop/storage/shared') {
      if (method === 'GET') {
        const shares = (await db.prepare(`SELECT s.id,s.kind,s.title,s.instructions,s.due_at,s.created_at,c.name AS group_name,
          (s.owner_id=?) AS mine,
          (SELECT COUNT(*) FROM json_each(s.file_ids) j JOIN workshop_files f ON f.id=j.value AND f.owner_id=s.owner_id) AS file_count
          ${access} WHERE ${canRead} ORDER BY s.created_at DESC,s.id LIMIT 100`).bind(uid, uid, uid).all()).results;
        return {shares};
      }
      if (method !== 'POST') failure();
      await limit(env, 'ws-share:' + uid, 30, 3600);
      const {class_id: group, kind, file_id: id, folder, due_at: due = null} = body || {};
      const title = typeof body?.title === 'string' ? body.title.trim() : '';
      const instructions = typeof body?.instructions === 'string' ? body.instructions.trim() : '';
      if (!Number.isSafeInteger(group) || group < 1 || !['resource', 'assignment'].includes(kind)
        || !title || title.length > 100 || instructions.length > 2000
        || (due !== null && (kind !== 'assignment' || !Number.isSafeInteger(due) || due <= now || due > now + 366 * 86400))) bad('bad_share');
      if ((typeof id === 'string') === (typeof folder === 'string')) bad('bad_share');
      const classRow = await db.prepare(`SELECT c.id FROM classes c WHERE c.id=? AND c.closed_at IS NULL
        AND ${kind === 'assignment' ? 'c.teacher_id=?' : member('?')}`).bind(group, uid, ...(kind === 'resource' ? [uid] : [])).first();
      if (!classRow) throw new HttpError(403, 'forbidden');
      let files;
      if (typeof id === 'string') {
        files = (await db.prepare('SELECT id,kind,mime FROM workshop_files WHERE owner_id=? AND id=?').bind(uid, id).all()).results;
      } else {
        const clean = cleanFolder(folder);
        if (!clean) bad('bad_folder');
        files = (await db.prepare('SELECT id,kind,mime FROM workshop_files WHERE owner_id=? AND (folder=? OR substr(folder,1,?)=?) LIMIT 201')
          .bind(uid, clean, clean.length + 1, clean + '/').all()).results;
      }
      if (!files.length) missing();
      if (files.length > 200) bad('share_too_many_files');
      if (kind === 'assignment' && files.some(file => file.mime === 'application/json' && !['problem','paper'].includes(file.kind))) bad('bad_worksheet');
      const share = crypto.randomUUID();
      const result = await db.prepare(`INSERT INTO workshop_class_shares(id,owner_id,class_id,kind,title,instructions,due_at,file_ids,created_at)
        SELECT ?,?,c.id,?,?,?,?,?,? FROM classes c WHERE c.id=? AND c.closed_at IS NULL
        AND ${kind === 'assignment' ? 'c.teacher_id=?' : member('?')}
        AND (SELECT COUNT(*) FROM workshop_class_shares WHERE owner_id=?)<200`)
        .bind(share, uid, kind, title, instructions, due, JSON.stringify(files.map(f => f.id)), now, group, uid, ...(kind === 'resource' ? [uid] : []), uid).run();
      if (!result.meta.changes) throw new HttpError(409, 'share_limit');
      return {id: share};
    }
    const match = /^\/api\/workshop\/storage\/shared\/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})(?:\/files\/([a-f0-9]{32}))?$/.exec(path);
    if (!match) missing();
    const [, id, file] = match;
    if (!file && method === 'DELETE') {
      const result = await db.prepare('DELETE FROM workshop_class_shares WHERE id=? AND owner_id=?').bind(id, uid).run();
      if (!result.meta.changes) missing();
      return {ok: true};
    }
    if (method !== 'GET' && !(file && method === 'HEAD')) failure();
    if (file) {
      await limit(env, 'ws-down:' + uid, 600, 3600);
      const row = await db.prepare(`SELECT f.*,s.kind AS share_kind ${access} ${fileLink} WHERE s.id=? AND f.id=? AND ${canRead}`).bind(id, file, uid, uid).first();
      if (!row) missing();
      const worksheet = row.share_kind === 'assignment' && row.mime === 'application/json';
      return download(env, row, method, worksheet ? studentWorksheet : null);
    }
    const shared = await db.prepare(`SELECT s.id ${access} WHERE s.id=? AND ${canRead}`).bind(id, uid, uid).first();
    if (!shared) missing();
    const rows = (await db.prepare(`SELECT f.* ${access} ${fileLink} WHERE s.id=? AND ${canRead} ORDER BY f.folder,f.name`).bind(id, uid, uid).all()).results;
    return {files: rows.map(row => { const {folder, ...file} = fileView(row); return file; })};
  };
}
