// Self-contained integration checks against the Worker and real in-memory SQLite (Node 22.13+).
// Run: node --test test-public-profile.mjs
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import test from "node:test";
import { runInNewContext } from "node:vm";
import worker from "./src/index.js";

const sqlite = new DatabaseSync(":memory:");
const migrations = new URL("./migrations/", import.meta.url);
for (const name of readdirSync(migrations).filter(n => /^00(?:0[1-9]|1[01])_.*\.sql$/.test(n)).sort()) {
  sqlite.exec(readFileSync(new URL(name, migrations), "utf8"));
}
// Small D1 adapter: actual schema, binding, joins, constraints and pagination run in SQLite.
const DB = {
  prepare(sql) {
    const statement = sqlite.prepare(sql);
    const make = args => ({
      bind: (...bound) => make(bound),
      async first() { return statement.get(...args) || null; },
      async all() { return { results: statement.all(...args) }; },
      async run() {
        const result = statement.run(...args);
        return { success: true, meta: { changes: result.changes, last_row_id: Number(result.lastInsertRowid) } };
      },
      execute() { return statement.columns().length ? this.all() : this.run(); },
    });
    return make([]);
  },
  async batch(statements) {
    sqlite.exec("BEGIN");
    try {
      const result = [];
      for (const statement of statements) result.push(await statement.execute());
      sqlite.exec("COMMIT");
      return result;
    } catch (error) { sqlite.exec("ROLLBACK"); throw error; }
  },
};
const env = { DB, ALLOWED_ORIGINS: "http://localhost:8765", LAB_KEEP_HOURS: "off" };
const timestamp = Math.floor(Date.now() / 1000);
const nickname = "한글 Author";
for (const row of [
  [41, "private_login", nickname, "private_password_hash", "admin", "publicAvatarKey", 0],
  [42, "other_login", "Other Person", "other_password_hash", "user", null, 0],
  [43, "former_login", "Former Person", null, "user", null, 1],
]) {
  sqlite.prepare("INSERT INTO users(id,username,nickname,pw,role,avatar,deleted,created_at) VALUES(?,?,?,?,?,?,?,?)").run(...row, timestamp);
}
for (let id = 1; id <= 25; id++) {
  sqlite.prepare("INSERT INTO posts(id,user_id,board,tag,lang,title,body,created_at) VALUES(?,41,'qna',?,?,?, ?,?)")
    .run(id, id === 1 ? "notice" : "gen", id > 23 ? "en" : "ko", `Public post ${id}`, "Public body ".repeat(30), timestamp);
}
sqlite.prepare("INSERT INTO posts(id,user_id,board,lang,title,body,created_at) VALUES(100,42,'study','ko','Other thread','Other body',?)").run(timestamp);
for (let id = 1; id <= 23; id++) {
  sqlite.prepare("INSERT INTO comments(id,user_id,post_id,parent_id,body,created_at) VALUES(?,41,?,?,?,?)")
    .run(id, id > 21 ? 25 : 100, id === 2 ? 1 : null, `Public comment ${id}`, timestamp);
}
sqlite.prepare("INSERT INTO comments(id,user_id,post_id,body,created_at) VALUES(90,42,1,'Other comment',?)").run(timestamp);

const token = "a".repeat(48);
const hash = Buffer.from(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(token))).toString("base64url");
sqlite.prepare("INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,41,?,?)").run(hash, timestamp, timestamp + 3600);

const path = "/api/users/" + encodeURIComponent(nickname);
async function request(p = path, options = {}) {
  const response = await worker.fetch(new Request("http://worker.local" + p, options), env);
  return { status: response.status, headers: response.headers, data: await response.json() };
}
const keys = value => Object.keys(value).sort();

test("anonymous profile includes only public display identity and both language histories", async () => {
  const { status, headers, data } = await request();
  assert.equal(status, 200);
  assert.equal(headers.get("cache-control"), "no-store");
  assert.deepEqual(data.profile, { nickname, avatar: "publicAvatarKey", role: "admin" });
  assert.deepEqual(data.counts, { posts: 25, comments: 23 });
  assert.equal(data.total, 25);
  assert.equal(data.page, 1);
  assert.equal(data.per, 20);
  assert.equal(data.tab, "posts");
  assert.equal(data.posts.length, 20);
  assert.deepEqual(data.comments, []);
  assert.deepEqual(data.posts.map(p => p.id), Array.from({ length: 20 }, (_, i) => 25 - i));
  assert.equal(data.posts[0].lang, "en");
  assert.ok(data.posts.some(p => p.lang === "ko"));
  assert.equal(sqlite.prepare("SELECT SUM(views) n FROM posts").get().n, 0, "reading history must not increment views");
});

test("post responses use a fixed public field allowlist", async () => {
  const { data } = await request();
  assert.deepEqual(keys(data.profile), ["avatar", "nickname", "role"]);
  assert.deepEqual(keys(data.posts[0]), ["board", "created_at", "id", "lang", "n_comments", "n_dislikes", "n_likes", "snip", "tag", "title", "updated_at", "views"]);
  assert.equal(data.posts[0].snip.length, 160);
  const serialized = JSON.stringify(data);
  for (const secret of ["private_login", "private_password_hash", token, hash, "user_id", "username", "exam_tokens", "token_hash"]) {
    assert.ok(!serialized.includes(secret), `must not expose ${secret}`);
  }
});

test("post pagination is stable and includes notices authored by this member", async () => {
  const { data } = await request(path + "?page=2");
  assert.deepEqual(data.posts.map(p => p.id), [5, 4, 3, 2, 1]);
  assert.equal(data.posts.at(-1).tag, "notice");
  assert.equal(data.total, 25);
  const empty = await request(path + "?page=500");
  assert.equal(empty.status, 200);
  assert.deepEqual(empty.data.posts, []);
  assert.equal(empty.data.total, 25);
});

test("comments include own replies and original public thread context only", async () => {
  const { data } = await request(path + "?tab=comments");
  assert.equal(data.tab, "comments");
  assert.equal(data.total, 23);
  assert.deepEqual(data.posts, []);
  assert.deepEqual(data.comments.map(c => c.id), Array.from({ length: 20 }, (_, i) => 23 - i));
  assert.deepEqual(keys(data.comments[0]), ["board", "body", "created_at", "id", "lang", "parent_id", "post_id", "post_title", "tag", "updated_at"]);
  assert.equal(data.comments[0].post_id, 25);
  assert.equal(data.comments[0].post_title, "Public post 25");
  const second = (await request(path + "?tab=comments&page=2")).data;
  assert.deepEqual(second.comments.map(c => c.id), [3, 2, 1]);
  assert.equal(second.comments[1].parent_id, 1);
  assert.equal(second.comments[0].post_title, "Other thread");
  assert.ok(!second.comments.some(c => c.id === 90), "another user's comments are excluded");
});

test("explicit language filter applies equally to totals and activity", async () => {
  const ko = (await request(path + "?lang=ko")).data;
  assert.deepEqual(ko.counts, { posts: 23, comments: 21 });
  assert.ok(ko.posts.every(p => p.lang === "ko"));
  const en = (await request(path + "?lang=en&tab=comments")).data;
  assert.deepEqual(en.counts, { posts: 2, comments: 2 });
  assert.deepEqual(en.comments.map(c => c.id), [23, 22]);
  assert.ok(en.comments.every(c => c.lang === "en"));
});

test("encoded Korean, inner spaces, case and compatibility forms resolve canonical nickname", async () => {
  const { status, data } = await request("/api/users/" + encodeURIComponent("한글 ＡＵＴＨＯＲ"));
  assert.equal(status, 200);
  assert.equal(data.profile.nickname, nickname);
  assert.equal((await request("/api/users/" + encodeURIComponent("Author"))).status, 404, "nickname substring cannot select an account");
  assert.equal((await request("/api/users/private_login")).status, 404, "login identifiers cannot select a profile");
});

test("signed-in reader receives the identical public response", async () => {
  const anonymous = await request();
  const authenticated = await request(path, { headers: { Authorization: "Bearer " + token } });
  assert.equal(authenticated.status, 200);
  assert.deepEqual(authenticated.data, anonymous.data);
});

test("missing and deleted accounts have no public profile", async () => {
  assert.equal((await request("/api/users/Nobody")).status, 404);
  assert.equal((await request("/api/users/Former%20Person")).status, 404);
  const other = (await request("/api/users/Other%20Person")).data;
  assert.deepEqual(other.profile, { nickname: "Other Person", avatar: null, role: "user" });
  assert.deepEqual(other.counts, { posts: 1, comments: 1 });
});

test("invalid paging, tab, language and nickname return controlled client errors", async () => {
  for (const query of ["page=0", "page=-1", "page=1.5", "page=2foo", "page=501", "page=999999999999999999", "page=1e2"]) {
    const response = await request(path + "?" + query);
    assert.equal(response.status, 400, query);
    assert.equal(response.data.error, "bad_page");
  }
  assert.equal((await request(path + "?tab=identities")).data.error, "bad_tab");
  assert.equal((await request(path + "?lang=private")).data.error, "bad_lang");
  for (const invalid of ["%ZZ", "%2F", "a", "%3Cscript%3E", encodeURIComponent("deleted_41")]) {
    const response = await request("/api/users/" + invalid);
    assert.equal(response.status, 400, invalid);
    assert.equal(response.data.error, "bad_nickname");
  }
});

test("renaming immediately replaces the publicly addressable nickname", async () => {
  const renamed = "새 닉네임";
  sqlite.prepare("UPDATE users SET nickname=? WHERE id=41").run(renamed);
  assert.equal((await request()).status, 404);
  const response = await request("/api/users/" + encodeURIComponent(renamed));
  assert.equal(response.status, 200);
  assert.equal(response.data.profile.nickname, renamed);
  assert.equal(response.data.total, 25);
  sqlite.prepare("UPDATE users SET nickname=? WHERE id=41").run(nickname);
});

test("query lookup supports valid dot-segment nicknames without URL path normalization", async () => {
  sqlite.prepare("UPDATE users SET nickname='..' WHERE id=41").run();
  const response = await request("/api/users?nickname=..&tab=comments");
  assert.equal(response.status, 200);
  assert.equal(response.data.profile.nickname, "..");
  assert.equal(response.data.total, 23);
  sqlite.prepare("UPDATE users SET nickname=? WHERE id=41").run(nickname);
  const korean = await request("/api/users?nickname=" + encodeURIComponent(nickname));
  assert.equal(korean.status, 200);
  assert.equal(korean.data.profile.nickname, nickname);
});

test("actual frontend profile renderer and API client integrate with Worker responses", async () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  const section = (start, end) => html.slice(html.indexOf(start), html.indexOf(end, html.indexOf(start)));
  const frontend = [
    section("const CMT = {", "\nconst cm = {"),
    html.match(/^const esc = .*$/m)[0],
    section("async function cmApi(", "\n/* who is signed in"),
    section("const p2 = n", "\nfunction cmGoLogin("),
    section("async function cmProfile(", "\nasync function cmPost("),
    "globalThis.renderProfile=cmProfile; globalThis.authorName=cmName;",
  ].join("\n");
  const document = { title: "" }, location = { hash: "" };
  const context = {
    URLSearchParams, Blob, document, location, lang: "ko",
    cmBase: () => "http://worker.local", cmTok: () => "",
    fetch: (url, options) => worker.fetch(new Request(url, options), env),
  };
  runInNewContext(frontend, context);
  const root = { innerHTML: "" };
  await context.renderProfile(root, encodeURIComponent(nickname), new URLSearchParams(), () => true);
  assert.ok(root.innerHTML.includes(nickname));
  assert.ok(root.innerHTML.includes("작성 글 25"));
  assert.ok(root.innerHTML.includes("작성 댓글 23"));
  assert.ok(root.innerHTML.includes("Public post 25"), "English-origin post stays visible in Korean UI");
  assert.ok(root.innerHTML.includes("Public post 23"));
  assert.ok(root.innerHTML.includes('href="#/community/post/25"'));
  assert.ok(!root.innerHTML.includes("private_login"));
  assert.equal(document.title, `${nickname} · 공개 프로필 | HaslaLab`);

  sqlite.prepare("UPDATE comments SET body=? WHERE id=23").run('<img src=x onerror="alert(1)">');
  await context.renderProfile(root, encodeURIComponent(nickname), new URLSearchParams("tab=comments"), () => true);
  assert.ok(root.innerHTML.includes('href="#/community/post/25?comment=23"'));
  assert.ok(root.innerHTML.includes("&lt;img src=x onerror=&quot;alert(1)&quot;&gt;"));
  assert.ok(!root.innerHTML.includes("<img src=x"));
  assert.ok(root.innerHTML.includes('aria-current="page">작성 댓글 23'));
  sqlite.prepare("UPDATE comments SET body='Public comment 23' WHERE id=23").run();

  await context.renderProfile(root, encodeURIComponent(nickname), new URLSearchParams("page=2"), () => true);
  assert.ok(root.innerHTML.includes("Public post 1"));
  assert.ok(!root.innerHTML.includes("Public post 25"));
  assert.ok(root.innerHTML.includes('aria-current="page">2</span>'));
  await context.renderProfile(root, encodeURIComponent(nickname), new URLSearchParams("page=500"), () => true);
  assert.equal(location.hash, `#/community/user/${encodeURIComponent(nickname)}?tab=posts&page=2`);

  await context.renderProfile(root, "Nobody", new URLSearchParams(), () => true);
  assert.ok(root.innerHTML.includes("사용자를 찾을 수 없습니다"));
  assert.ok(!context.authorName({ nickname, gone: 1 }).includes("<a"));
  assert.ok(context.authorName({ nickname }).includes(encodeURIComponent(nickname)));
});

test("deleted posts and their comments disappear from all history counts and pages", async () => {
  const deleted = await request("/api/posts/25", { method: "DELETE", headers: { Authorization: "Bearer " + token } });
  assert.equal(deleted.status, 200);
  const posts = (await request()).data;
  assert.deepEqual(posts.counts, { posts: 24, comments: 21 });
  assert.ok(!posts.posts.some(p => p.id === 25));
  const comments = (await request(path + "?tab=comments")).data;
  assert.ok(comments.comments.every(c => c.post_id !== 25));
});

test("closing an account makes its profile unavailable even while public threads remain", async () => {
  sqlite.prepare("UPDATE users SET deleted=1,username='deleted_41',nickname='deleted_41',pw=NULL WHERE id=41").run();
  assert.equal((await request()).status, 404);
  assert.equal((await request("/api/users/deleted_41")).status, 400);
  assert.equal(sqlite.prepare("SELECT COUNT(*) n FROM posts WHERE user_id=41").get().n, 24);
  sqlite.close();
});
