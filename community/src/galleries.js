/* Galleries, as on DCInside: the main gallery is the built-in boards (free, qna, sim, study); any signed-in member
   can open a minor gallery with its own address. A gallery's posts use posts.board = "g-<address>", so lists,
   counts, search and moderation work exactly as for the built-in boards. The opener manages the gallery's name
   and introduction and can close it; administrators can close any gallery. */
export const GALLERY_BOARD = /^g-[a-z0-9](?:[a-z0-9-]{1,22}[a-z0-9])$/;
export const GALLERY_SCHEMA = [
  `CREATE TABLE IF NOT EXISTS galleries (
     board TEXT PRIMARY KEY,
     name TEXT NOT NULL,
     intro TEXT NOT NULL DEFAULT '',
     owner_id INTEGER NOT NULL,
     status TEXT NOT NULL DEFAULT 'active',
     created_at INTEGER NOT NULL,
     updated_at INTEGER)`,
  `CREATE INDEX IF NOT EXISTS galleries_owner ON galleries(owner_id, status)`,
  `CREATE UNIQUE INDEX IF NOT EXISTS galleries_name ON galleries(name COLLATE NOCASE) WHERE status='active'`
];
const RESERVED = new Set(['admin','administrator','notice','main','haslalab','haslaedu','official','free','qna','sim','study','best','hot','all',
  'new','write','edit','post','user','login','signup','account','galleries','gallery','mod','moderator','system','help','root']);
const MAX_OWNED = 3;

const ready = new WeakSet();   /* per database binding; the statements are idempotent */
export async function ensureGallerySchema(env) {
  if (ready.has(env.DB)) return;
  await env.DB.batch(GALLERY_SCHEMA.map(sql => env.DB.prepare(sql)));
  ready.add(env.DB);
}

export function galleryBoard(address) {
  const slug = String(address || '').trim().toLowerCase();
  return GALLERY_BOARD.test('g-' + slug) && !RESERVED.has(slug) ? 'g-' + slug : null;
}

export async function activeGallery(env, board) {
  if (!GALLERY_BOARD.test(board || '')) return null;
  await ensureGallerySchema(env);
  return env.DB.prepare("SELECT board,name,intro,owner_id FROM galleries WHERE board=? AND status='active'").bind(board).first();
}

export function createGalleryRouter({ HttpError, needUser, limit, now, text, bad, invalidate = () => {} }) {
  const cleanName = v => {
    const name = text(v, 24, 'bad_gallery_name').replace(/\s+/g, ' ');
    if ([...name].length < 2) bad('bad_gallery_name');
    return name;
  };
  const cleanIntro = v => v === undefined || v === '' ? '' : text(v, 200, 'bad_gallery_intro');
  return async function galleryRoute(p, m, body, me, env) {
    if (p === '/api/galleries' && m === 'GET') {
      await ensureGallerySchema(env);
      const rows = await env.DB.prepare(`SELECT g.board,g.name,g.intro,g.created_at,u.nickname AS owner,
          (SELECT COUNT(*) FROM posts WHERE board=g.board) AS n,
          (SELECT MAX(created_at) FROM posts WHERE board=g.board) AS last_at
        FROM galleries g JOIN users u ON u.id=g.owner_id WHERE g.status='active' ORDER BY n DESC, g.created_at DESC LIMIT 500`).all();
      return { galleries: rows.results };
    }
    if (p === '/api/galleries' && m === 'POST') {
      needUser(me);
      await ensureGallerySchema(env);
      const board = galleryBoard(body.address) || bad('bad_gallery_address');
      const name = cleanName(body.name), intro = cleanIntro(body.intro);
      const owned = await env.DB.prepare("SELECT COUNT(*) n FROM galleries WHERE owner_id=? AND status='active'").bind(me.id).first();
      if (me.role !== 'admin' && (owned?.n || 0) >= MAX_OWNED) throw new HttpError(409, 'gallery_limit');
      await limit(env, 'gallery:' + me.id, 2, 86400);
      try {
        await env.DB.prepare('INSERT INTO galleries(board,name,intro,owner_id,created_at) VALUES(?,?,?,?,?)').bind(board, name, intro, me.id, now()).run();
      } catch (e) {
        if (/UNIQUE constraint/i.test(String(e && e.message))) throw new HttpError(409, 'gallery_taken');
        throw e;
      }
      invalidate(env);
      return { board, name, intro };
    }
    const r = /^\/api\/galleries\/(g-[a-z0-9-]{3,24})$/.exec(p);
    if (r) {
      await ensureGallerySchema(env);
      const g = await env.DB.prepare("SELECT board,name,intro,owner_id,status FROM galleries WHERE board=?").bind(r[1]).first();
      if (m === 'GET') {
        if (!g || g.status !== 'active') throw new HttpError(404, 'not_found');
        return { board: g.board, name: g.name, intro: g.intro };
      }
      needUser(me);
      if (!g || g.status !== 'active') throw new HttpError(404, 'not_found');
      if (g.owner_id !== me.id && me.role !== 'admin') throw new HttpError(403, 'forbidden');
      if (m === 'PATCH') {
        const name = body.name === undefined ? g.name : cleanName(body.name), intro = body.intro === undefined ? g.intro : cleanIntro(body.intro);
        try { await env.DB.prepare('UPDATE galleries SET name=?,intro=?,updated_at=? WHERE board=?').bind(name, intro, now(), g.board).run(); }
        catch (e) { if (/UNIQUE constraint/i.test(String(e && e.message))) throw new HttpError(409, 'gallery_taken'); throw e; }
        invalidate(env);
        return { board: g.board, name, intro };
      }
      if (m === 'DELETE') {
        /* closing hides the gallery and stops new posts; its posts stay readable at their own addresses */
        await env.DB.prepare("UPDATE galleries SET status='closed',updated_at=? WHERE board=?").bind(now(), g.board).run();
        invalidate(env);
        return { ok: true };
      }
    }
    return undefined;
  };
}
