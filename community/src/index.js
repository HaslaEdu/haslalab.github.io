/* HaslaLab community API — Cloudflare Worker + D1
 *
 * Auth is a bearer token in the Authorization header (no cookies), so the
 * static site on haslalab.org can call this from any origin listed in
 * ALLOWED_ORIGINS without third-party-cookie trouble.
 */

const BOARDS = ["free", "qna", "sim", "study"];
// 말머리: general, question, info, review, bug report, notice (admins only)
const TAGS = ["gen", "q", "info", "review", "bug", "notice"];
const BEST = 3;
// two servers, one account: the Korean and the English community keep their own posts
const LANGS = ["ko", "en"];
const pickLang = l => LANGS.includes(l) ? l : "ko";                      // net votes that make a post a 개념글 / best post
const PAGE = 20;
const SESSION_DAYS = 30;
const PBKDF2_ITER = 100000;          // Workers' WebCrypto ceiling for PBKDF2

const LIMITS = {
  title: 120, body: 20000, comment: 3000, reason: 300,
};

/* ── tiny helpers ───────────────────────────────────────────── */
const now = () => Math.floor(Date.now() / 1000);
const enc = new TextEncoder();

function b64u(buf) {
  let s = "";
  for (const b of new Uint8Array(buf)) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
function unb64u(s) {
  s = s.replace(/-/g, "+").replace(/_/g, "/");
  const bin = atob(s + "===".slice((s.length + 3) % 4));
  return Uint8Array.from(bin, c => c.charCodeAt(0));
}
async function sha256(s) {
  return b64u(await crypto.subtle.digest("SHA-256", enc.encode(s)));
}
function eqBytes(a, b) {
  if (a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a[i] ^ b[i];
  return d === 0;
}

async function pbkdf2(pw, salt, iter) {
  const key = await crypto.subtle.importKey("raw", enc.encode(pw), "PBKDF2", false, ["deriveBits"]);
  return new Uint8Array(await crypto.subtle.deriveBits(
    { name: "PBKDF2", hash: "SHA-256", salt, iterations: iter }, key, 256));
}
async function hashPw(pw) {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  return `pbkdf2$${PBKDF2_ITER}$${b64u(salt)}$${b64u(await pbkdf2(pw, salt, PBKDF2_ITER))}`;
}
async function checkPw(pw, stored) {
  if (!stored) return false;
  const [kind, iter, salt, hash] = stored.split("$");
  if (kind !== "pbkdf2") return false;
  return eqBytes(await pbkdf2(pw, unb64u(salt), +iter), unb64u(hash));
}

class HttpError extends Error {
  constructor(status, code) { super(code); this.status = status; this.code = code; }
}
const bad = code => { throw new HttpError(400, code); };

/* ── CORS ───────────────────────────────────────────────────── */
function corsHeaders(req, env) {
  const origin = req.headers.get("Origin") || "";
  const allowed = (env.ALLOWED_ORIGINS || "").split(",").map(s => s.trim()).filter(Boolean);
  const h = {
    "Access-Control-Allow-Methods": "GET,POST,PATCH,DELETE,OPTIONS",
    "Access-Control-Allow-Headers": "Authorization,Content-Type",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  };
  if (allowed.includes(origin)) h["Access-Control-Allow-Origin"] = origin;
  return h;
}
function json(data, status, cors) {
  return new Response(JSON.stringify(data), {
    status: status || 200,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", ...cors },
  });
}

/* ── rate limiting: fixed window per key ────────────────────── */
async function limit(env, key, max, windowSec) {
  const t = now();
  const row = await env.DB.prepare("SELECT start,n FROM ratelimits WHERE k=?").bind(key).first();
  if (!row || t - row.start >= windowSec) {
    await env.DB.prepare("INSERT INTO ratelimits(k,start,n) VALUES(?,?,1) ON CONFLICT(k) DO UPDATE SET start=excluded.start,n=1")
      .bind(key, t).run();
    return;
  }
  if (row.n >= max) throw new HttpError(429, "rate_limited");
  await env.DB.prepare("UPDATE ratelimits SET n=n+1 WHERE k=?").bind(key).run();
}
const clientIp = req => req.headers.get("CF-Connecting-IP") || "local";

/* ── input validation ───────────────────────────────────────── */
const USERNAME_RE = /^[A-Za-z0-9_]{3,20}$/;
// letters (any script), digits, _ . -  and inner spaces; 2–16 chars
const NICK_RE = /^[\p{L}\p{N}_.\-](?:[\p{L}\p{N}_.\- ]{0,14}[\p{L}\p{N}_.\-])?$/u;

function text(v, max, code) {
  if (typeof v !== "string") bad(code);
  v = v.replace(/\r\n?/g, "\n").replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "").trim();
  if (!v || v.length > max) bad(code);
  return v;
}
function pwOk(pw) {
  return typeof pw === "string" && pw.length >= 8 && pw.length <= 200;
}

/* ── sessions ───────────────────────────────────────────────── */
async function newSession(env, userId) {
  const token = b64u(crypto.getRandomValues(new Uint8Array(32)));
  const t = now();
  await env.DB.prepare("INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)")
    .bind(await sha256(token), userId, t, t + SESSION_DAYS * 86400).run();
  return token;
}
async function currentUser(req, env) {
  const m = /^Bearer\s+([A-Za-z0-9_-]{20,})$/.exec(req.headers.get("Authorization") || "");
  if (!m) return null;
  const th = await sha256(m[1]);
  const u = await env.DB.prepare(
    `SELECT u.id,u.username,u.nickname,u.role,u.created_at FROM sessions s JOIN users u ON u.id=s.user_id
     WHERE s.token_hash=? AND s.expires_at>? AND u.deleted=0`).bind(th, now()).first();
  if (u) u.tokenHash = th;
  return u || null;
}
function needUser(u) { if (!u) throw new HttpError(401, "login_required"); return u; }
const pubUser = u => ({ id: u.id, username: u.username, nickname: u.nickname, role: u.role, created_at: u.created_at });
const canEdit = (u, ownerId) => u && (u.id === ownerId || u.role === "admin");
const pickTag = (t, u) => (TAGS.includes(t) && (t !== "notice" || u.role === "admin")) ? t : "gen";

/* ── routes ─────────────────────────────────────────────────── */
async function handle(req, env, url) {
  const p = url.pathname.replace(/\/+$/, "");
  const m = req.method;
  const body = (m === "POST" || m === "PATCH") ? await req.json().catch(() => ({})) : {};
  const me = await currentUser(req, env);
  let r;

  if (p === "/api/health") return { ok: true, v: 3, boards: BOARDS, tags: TAGS, best: BEST, langs: LANGS };
  if (p === "/api/boards" && m === "GET") {
    const day = now() - 86400, lang = pickLang(url.searchParams.get("lang"));
    const rows = (await env.DB.prepare(
      `SELECT board, COUNT(*) n, SUM(created_at > ?) today FROM posts WHERE lang=? GROUP BY board`).bind(day, lang).all()).results;
    return { boards: rows };
  }

  /* auth */
  if (p === "/api/signup" && m === "POST") {
    const username = String(body.username || "").trim();
    const nickname = String(body.nickname || "").trim();
    if (!USERNAME_RE.test(username)) bad("bad_username");
    if (!NICK_RE.test(nickname)) bad("bad_nickname");
    if (!pwOk(body.password)) bad("bad_password");
    const clash = await env.DB.prepare("SELECT username,nickname FROM users WHERE username=? OR nickname=?")
      .bind(username, nickname).first();
    if (clash) throw new HttpError(409, clash.username.toLowerCase() === username.toLowerCase() ? "username_taken" : "nickname_taken");
    // a whole classroom often shares one address, so this is per hour, not per day
    await limit(env, "signup:" + clientIp(req), 20, 3600);
    const res = await env.DB.prepare("INSERT INTO users(username,nickname,pw,created_at) VALUES(?,?,?,?)")
      .bind(username, nickname, await hashPw(body.password), now()).run();
    const id = res.meta.last_row_id;
    const user = await env.DB.prepare("SELECT id,username,nickname,role,created_at FROM users WHERE id=?").bind(id).first();
    return { token: await newSession(env, id), user: pubUser(user) };
  }
  if (p === "/api/login" && m === "POST") {
    const username = String(body.username || "").trim();
    await limit(env, "login:" + clientIp(req), 20, 900);
    await limit(env, "loginu:" + username.toLowerCase(), 10, 900);
    const u = await env.DB.prepare("SELECT * FROM users WHERE username=? AND deleted=0").bind(username).first();
    if (!u || !(await checkPw(String(body.password || ""), u.pw))) throw new HttpError(401, "bad_credentials");
    return { token: await newSession(env, u.id), user: pubUser(u) };
  }
  if (p === "/api/logout" && m === "POST") {
    if (me) await env.DB.prepare("DELETE FROM sessions WHERE token_hash=?").bind(me.tokenHash).run();
    return { ok: true };
  }
  if (p === "/api/me" && m === "GET") return { user: me ? pubUser(me) : null };
  if (p === "/api/me/password" && m === "POST") {
    needUser(me);
    await limit(env, "pw:" + me.id, 10, 900);
    const u = await env.DB.prepare("SELECT pw FROM users WHERE id=?").bind(me.id).first();
    if (!(await checkPw(String(body.old || ""), u.pw))) throw new HttpError(401, "bad_credentials");
    if (!pwOk(body.password)) bad("bad_password");
    await env.DB.batch([
      env.DB.prepare("UPDATE users SET pw=? WHERE id=?").bind(await hashPw(body.password), me.id),
      env.DB.prepare("DELETE FROM sessions WHERE user_id=? AND token_hash<>?").bind(me.id, me.tokenHash),
    ]);
    return { ok: true };
  }
  if (p === "/api/me" && m === "DELETE") {
    needUser(me);
    // posts and comments stay so threads keep making sense; the name goes
    await env.DB.batch([
      env.DB.prepare("UPDATE users SET deleted=1,pw=NULL,username=?,nickname=? WHERE id=?")
        .bind("deleted_" + me.id, "deleted_" + me.id, me.id),
      env.DB.prepare("DELETE FROM sessions WHERE user_id=?").bind(me.id),
    ]);
    return { ok: true };
  }

  /* posts */
  if (p === "/api/posts" && m === "GET") {
    const sp = url.searchParams, board = sp.get("board") || "", tag = sp.get("tag") || "";
    const q = (sp.get("q") || "").trim().slice(0, 60), field = sp.get("field") || "all";
    const sort = sp.get("sort") || "new", best = sp.get("best") === "1";
    const page = Math.max(1, Math.min(500, parseInt(sp.get("page")) || 1));
    if (board && !BOARDS.includes(board)) bad("bad_board");
    const lang = pickLang(sp.get("lang"));
    const where = ["p.tag<>'notice'", "p.lang=?"], args = [lang];
    if (board) { where.push("p.board=?"); args.push(board); }
    if (tag && TAGS.includes(tag)) { where.push("p.tag=?"); args.push(tag); }
    if (best) where.push(`(p.n_likes-p.n_dislikes)>=${BEST}`);
    if (q) {
      const l = "%" + q.replace(/[\\%_]/g, "\\$&") + "%";
      if (field === "title") { where.push("p.title LIKE ? ESCAPE '\\'"); args.push(l); }
      else if (field === "author") { where.push("u.nickname LIKE ? ESCAPE '\\'"); args.push(l); }
      else { where.push("(p.title LIKE ? ESCAPE '\\' OR p.body LIKE ? ESCAPE '\\')"); args.push(l, l); }
    }
    const w = "WHERE " + where.join(" AND ");
    const order = sort === "top" ? "(p.n_likes-p.n_dislikes) DESC, p.id DESC"
      : sort === "cmt" ? "p.n_comments DESC, p.id DESC"
      : sort === "hot" ? `((p.n_likes-p.n_dislikes)*2+p.n_comments+p.views*0.05+1)*1.0/((${now()}-p.created_at)/3600.0+2) DESC, p.id DESC`
      : "p.id DESC";
    const cols = `p.id,p.board,p.tag,p.title,substr(p.body,1,160) AS snip,p.created_at,p.updated_at,p.views,p.n_comments,p.n_likes,p.n_dislikes,u.nickname,u.deleted AS gone`;
    const total = (await env.DB.prepare(`SELECT COUNT(*) n FROM posts p JOIN users u ON u.id=p.user_id ${w}`).bind(...args).first()).n;
    const rows = (await env.DB.prepare(`SELECT ${cols} FROM posts p JOIN users u ON u.id=p.user_id ${w} ORDER BY ${order} LIMIT ? OFFSET ?`)
      .bind(...args, PAGE, (page - 1) * PAGE).all()).results;
    // notices sit on top of the first page, as on every Korean board
    const notices = page === 1 && !q ? (await env.DB.prepare(
      `SELECT ${cols} FROM posts p JOIN users u ON u.id=p.user_id WHERE p.tag='notice' AND p.lang=? ${board ? "AND (p.board=? OR p.board='free')" : ""} ORDER BY p.id DESC LIMIT 5`)
      .bind(lang, ...(board ? [board] : [])).all()).results : [];
    return { posts: rows, notices, total, page, per: PAGE };
  }
  if (p === "/api/posts" && m === "POST") {
    needUser(me);
    await limit(env, "post:" + me.id, 5, 600);
    const board = BOARDS.includes(body.board) ? body.board : bad("bad_board");
    const tag = pickTag(body.tag, me);
    const title = text(body.title, LIMITS.title, "bad_title");
    const content = text(body.body, LIMITS.body, "bad_body");
    const res = await env.DB.prepare("INSERT INTO posts(board,tag,lang,user_id,title,body,created_at) VALUES(?,?,?,?,?,?,?)")
      .bind(board, tag, pickLang(body.lang), me.id, title, content, now()).run();
    return { id: res.meta.last_row_id };
  }
  if ((r = /^\/api\/posts\/(\d+)$/.exec(p))) {
    const id = +r[1];
    const post = await env.DB.prepare(
      `SELECT p.*,u.nickname,u.deleted AS gone FROM posts p JOIN users u ON u.id=p.user_id WHERE p.id=?`).bind(id).first();
    if (!post) throw new HttpError(404, "not_found");
    if (m === "GET") {
      if (url.searchParams.get("view") === "1") {
        await env.DB.prepare("UPDATE posts SET views=views+1 WHERE id=?").bind(id).run();
        post.views++;
      }
      const comments = (await env.DB.prepare(
        `SELECT c.id,c.parent_id,c.user_id,c.body,c.created_at,c.updated_at,u.nickname,u.deleted AS gone
         FROM comments c JOIN users u ON u.id=c.user_id WHERE c.post_id=? ORDER BY c.id`).bind(id).all()).results;
      const liked = me ? !!(await env.DB.prepare("SELECT 1 FROM likes WHERE post_id=? AND user_id=?").bind(id, me.id).first()) : false;
      const disliked = me ? !!(await env.DB.prepare("SELECT 1 FROM dislikes WHERE post_id=? AND user_id=?").bind(id, me.id).first()) : false;
      for (const c of comments) { c.mine = canEdit(me, c.user_id); delete c.user_id; }
      post.mine = canEdit(me, post.user_id);
      delete post.user_id;
      return { post, comments, liked, my: liked ? 1 : disliked ? -1 : 0 };
    }
    if (!canEdit(needUser(me), post.user_id)) throw new HttpError(403, "forbidden");
    if (m === "PATCH") {
      const title = text(body.title, LIMITS.title, "bad_title");
      const content = text(body.body, LIMITS.body, "bad_body");
      const board = BOARDS.includes(body.board) ? body.board : post.board;
      const tag = body.tag === undefined ? post.tag : pickTag(body.tag, me);
      await env.DB.prepare("UPDATE posts SET title=?,body=?,board=?,tag=?,updated_at=? WHERE id=?")
        .bind(title, content, board, tag, now(), id).run();
      return { ok: true };
    }
    if (m === "DELETE") {
      await env.DB.batch([
        env.DB.prepare("DELETE FROM comments WHERE post_id=?").bind(id),
        env.DB.prepare("DELETE FROM likes WHERE post_id=?").bind(id),
        env.DB.prepare("DELETE FROM dislikes WHERE post_id=?").bind(id),
        env.DB.prepare("DELETE FROM posts WHERE id=?").bind(id),
      ]);
      return { ok: true };
    }
  }
  if ((r = /^\/api\/posts\/(\d+)\/(like|vote)$/.exec(p)) && m === "POST") {
    needUser(me);
    await limit(env, "vote:" + me.id, 60, 600);
    const id = +r[1], v = r[2] === "like" ? 1 : (body.v === -1 ? -1 : 1);
    if (!(await env.DB.prepare("SELECT 1 FROM posts WHERE id=?").bind(id).first())) throw new HttpError(404, "not_found");
    const up = !!(await env.DB.prepare("SELECT 1 FROM likes WHERE post_id=? AND user_id=?").bind(id, me.id).first());
    const down = !!(await env.DB.prepare("SELECT 1 FROM dislikes WHERE post_id=? AND user_id=?").bind(id, me.id).first());
    const ops = [];
    if (up) ops.push(env.DB.prepare("DELETE FROM likes WHERE post_id=? AND user_id=?").bind(id, me.id), env.DB.prepare("UPDATE posts SET n_likes=n_likes-1 WHERE id=?").bind(id));
    if (down) ops.push(env.DB.prepare("DELETE FROM dislikes WHERE post_id=? AND user_id=?").bind(id, me.id), env.DB.prepare("UPDATE posts SET n_dislikes=n_dislikes-1 WHERE id=?").bind(id));
    const my = (v === 1 && up) || (v === -1 && down) ? 0 : v;      // pressing the same button again takes the vote back
    if (my === 1) ops.push(env.DB.prepare("INSERT INTO likes(post_id,user_id,created_at) VALUES(?,?,?)").bind(id, me.id, now()), env.DB.prepare("UPDATE posts SET n_likes=n_likes+1 WHERE id=?").bind(id));
    if (my === -1) ops.push(env.DB.prepare("INSERT INTO dislikes(post_id,user_id,created_at) VALUES(?,?,?)").bind(id, me.id, now()), env.DB.prepare("UPDATE posts SET n_dislikes=n_dislikes+1 WHERE id=?").bind(id));
    if (ops.length) await env.DB.batch(ops);
    const c = await env.DB.prepare("SELECT n_likes,n_dislikes FROM posts WHERE id=?").bind(id).first();
    return { my, liked: my === 1, n_likes: c.n_likes, n_dislikes: c.n_dislikes };
  }

  /* comments */
  if ((r = /^\/api\/posts\/(\d+)\/comments$/.exec(p)) && m === "POST") {
    needUser(me);
    await limit(env, "cmt:" + me.id, 20, 600);
    const id = +r[1];
    if (!(await env.DB.prepare("SELECT 1 FROM posts WHERE id=?").bind(id).first())) throw new HttpError(404, "not_found");
    const content = text(body.body, LIMITS.comment, "bad_body");
    // replies are one level deep: answering a reply joins its thread
    let parent = null;
    if (body.parent_id) {
      const pc = await env.DB.prepare("SELECT id,parent_id FROM comments WHERE id=? AND post_id=?").bind(parseInt(body.parent_id) || 0, id).first();
      if (!pc) throw new HttpError(404, "not_found");
      parent = pc.parent_id || pc.id;
    }
    const [ins] = await env.DB.batch([
      env.DB.prepare("INSERT INTO comments(post_id,parent_id,user_id,body,created_at) VALUES(?,?,?,?,?)").bind(id, parent, me.id, content, now()),
      env.DB.prepare("UPDATE posts SET n_comments=n_comments+1 WHERE id=?").bind(id),
    ]);
    return { id: ins.meta.last_row_id };
  }
  if ((r = /^\/api\/comments\/(\d+)$/.exec(p))) {
    const id = +r[1];
    const c = await env.DB.prepare("SELECT * FROM comments WHERE id=?").bind(id).first();
    if (!c) throw new HttpError(404, "not_found");
    if (!canEdit(needUser(me), c.user_id)) throw new HttpError(403, "forbidden");
    if (m === "PATCH") {
      await env.DB.prepare("UPDATE comments SET body=?,updated_at=? WHERE id=?")
        .bind(text(body.body, LIMITS.comment, "bad_body"), now(), id).run();
      return { ok: true };
    }
    if (m === "DELETE") {
      const n = 1 + (await env.DB.prepare("SELECT COUNT(*) n FROM comments WHERE parent_id=?").bind(id).first()).n;   // its replies go with it
      await env.DB.batch([
        env.DB.prepare("DELETE FROM comments WHERE id=? OR parent_id=?").bind(id, id),
        env.DB.prepare("UPDATE posts SET n_comments=n_comments-? WHERE id=?").bind(n, c.post_id),
      ]);
      return { ok: true };
    }
  }

  /* reports (read with: wrangler d1 execute ... "SELECT * FROM reports") */
  if (p === "/api/report" && m === "POST") {
    needUser(me);
    await limit(env, "rep:" + me.id, 10, 3600);
    const kind = body.kind === "comment" ? "comment" : body.kind === "post" ? "post" : bad("bad_kind");
    const target = parseInt(body.id) || bad("bad_id");
    await env.DB.prepare("INSERT OR IGNORE INTO reports(kind,target_id,user_id,reason,created_at) VALUES(?,?,?,?,?)")
      .bind(kind, target, me.id, text(body.reason, LIMITS.reason, "bad_reason"), now()).run();
    return { ok: true };
  }

  throw new HttpError(404, "not_found");
}

export default {
  async fetch(req, env) {
    const cors = corsHeaders(req, env);
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    const url = new URL(req.url);
    if (!url.pathname.startsWith("/api/")) return json({ error: "not_found" }, 404, cors);
    try {
      return json(await handle(req, env, url), 200, cors);
    } catch (e) {
      if (e instanceof HttpError) return json({ error: e.code }, e.status, cors);
      console.error(e && e.stack || e);
      return json({ error: "server_error" }, 500, cors);
    }
  },
};
