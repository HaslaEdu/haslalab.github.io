// nicknames: one rule for sign-up, renaming and the live check.  Against `npm run dev`:  node test-nick.mjs
const B = (process.env.API || "http://127.0.0.1:8787") + "/api";
const call = async (m, p, body, tok) => { const r = await fetch(B + p, { method: m, headers: { "Content-Type": "application/json", Origin: "http://localhost:8765", ...(tok ? { Authorization: "Bearer " + tok } : {}) }, body: body ? JSON.stringify(body) : undefined }); return [r.status, await r.json().catch(() => ({}))]; };
let fails = 0;
const ok = (c, msg) => { if (!c) fails++; console.log((c ? "PASS " : "FAIL ") + msg); };
const r = Math.random().toString(36).slice(2, 6);
const sign = (u, n) => call("POST", "/signup", { username: u + r, nickname: n, password: "password1" });
const chk = (n, tok) => call("GET", "/nick-check?n=" + encodeURIComponent(n), null, tok);

let [s, j] = await sign("nA", "Kim" + r); const A = j.token;
ok(s === 200, "sign up Kim" + r);
[s, j] = await sign("nB", "kim" + r);
ok(s === 409 && j.error === "nickname_taken", "another case of the same name is taken");
[s, j] = await sign("nC", "Ｋｉｍ" + r);
ok(s === 409 && j.error === "nickname_taken", "full-width letters are the same name");
[s, j] = await sign("nD", "  Kim" + r + "  ");
ok(s === 409, "spaces around it do not make it new");
[s, j] = await sign("nE", "ㅤㅤㅤ");
ok(s === 400 && j.error === "bad_nickname", "invisible Hangul fillers are refused");
[s, j] = await sign("nF", "deleted_12");
ok(s === 400 && j.error === "bad_nickname", "the deleted-account pattern is reserved");
[s, j] = await sign("nG", "Lee  " + r + "  x");
ok(s === 200 && j.user.nickname === "Lee " + r + " x", "inner runs of spaces become one: «" + (j.user && j.user.nickname) + "»");
const G = j.token;

/* the live check */
[s, j] = await chk("KIM" + r);
ok(s === 200 && j.ok === false && j.error === "nickname_taken", "check: taken (any case)");
[s, j] = await chk("Park" + r);
ok(j.ok === true, "check: free");
[s, j] = await chk("a");
ok(j.ok === false && j.error === "bad_nickname", "check: too short");
[s, j] = await chk("Kim" + r, A);
ok(j.ok === true && j.same === true, "check: your own name is «your current name» for you");
[s, j] = await chk("kim" + r, A);
ok(j.ok === true && !j.same, "check: your own name in another case is free for you (a case change)");
[s, j] = await sign("nH", "가");
ok(s === 400 && j.error === "bad_nickname", "one character is too short (2–16, as the form says)");

/* renaming */
[s, j] = await call("PATCH", "/me", { nickname: "KIM" + r }, G);
ok(s === 409 && j.error === "nickname_taken", "cannot rename to someone else's name in another case");
for (let i = 0; i < 6; i++) await call("PATCH", "/me", { nickname: "kim" + r }, G);
[s, j] = await call("PATCH", "/me", { nickname: "Choi" + r }, G);
ok(s === 200 && j.nickname === "Choi" + r, "refused renames do not use up the five a day");
[s, j] = await call("PATCH", "/me", { nickname: "KIM" + r }, A);
ok(s === 200 && j.nickname === "KIM" + r, "changing the case of your own name is allowed");

/* two people at the same moment */
const same = "Race" + r;
const many = await Promise.all(Array.from({ length: 6 }, (_, i) => sign("race" + i, same)));
ok(many.filter(x => x[0] === 200).length === 1 && many.filter(x => x[0] === 409 && x[1].error === "nickname_taken").length === 5,
  "6 sign-ups with one name at once: 1 gets it, 5 are told it is taken " + JSON.stringify(many.map(x => x[0])));
const twoTok = [(await sign("rn1", "Rn1" + r))[1].token, (await sign("rn2", "Rn2" + r))[1].token];
const ren = await Promise.all(twoTok.map(t => call("PATCH", "/me", { nickname: "Swap" + r }, t)));
ok(ren.filter(x => x[0] === 200).length === 1 && ren.filter(x => x[0] === 409).length === 1, "two renames to one name at once: one wins " + JSON.stringify(ren.map(x => x[0])));
console.log(fails ? fails + " FAILED" : "all passed");
process.exit(fails ? 1 : 0);
