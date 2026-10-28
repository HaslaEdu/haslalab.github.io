// v10: what each grading costs and how long it takes (lab_calls), the admins' reference marks (lab_reviews) and the
// answer photos' keeping (R2, LAB_KEEP_HOURS).  Against `npm run dev` with test-lab-mock.mjs and the 6-second clock of
// test-lab.mjs, migration 0009 applied:  node test-lab-metrics.mjs
// With R2=1 the run is against a Worker started with wrangler.test-r2.toml (an R2 bucket bound as LAB_PAGES and
// LAB_KEEP_HOURS=0): the photo goes to R2, and after grading it is removed.
import { execSync } from "node:child_process";
const API = process.env.API || "http://127.0.0.1:8787", B = API + "/api", R2 = !!process.env.R2;
const call = async (m, p, body, tok, extra) => { const r = await fetch(B + p, { method: m, headers: { "Content-Type": "application/json", ...(tok ? { Authorization: "Bearer " + tok } : {}), ...(extra || {}) }, body: body ? JSON.stringify(body) : undefined }); return [r.status, await r.json().catch(() => ({}))]; };
const up = async (sid, key, task, kind, bytes) => { const r = await fetch(B + `/lab/up/${sid}/pages?task=${task}&kind=${kind}`, { method: "PUT", headers: { "Content-Type": "image/png", "X-Lab-Token": key }, body: bytes }); return [r.status, await r.json().catch(() => ({}))]; };
let fails = 0;
const ok = (c, msg) => { if (!c) fails++; console.log((c ? "PASS " : "FAIL ") + msg); };
const near = (a, b) => Math.abs(a - b) < 1e-6, near5 = (a, b) => Math.abs(a - b) < 1e-5;   // prices are kept to 6 places, sums shown to 5
const rnd = Math.random().toString(36).slice(2, 7);
const sign = async u => (await call("POST", "/signup", { username: u + rnd, nickname: u + rnd, password: "password1" }))[1].token;
const png = Buffer.from("89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4890000000D49444154789C6360000002000154A24F5D0000000049454E44AE426082", "hex");
const sql = q => JSON.parse(execSync(`npx wrangler d1 execute haslalab-community --local --json ${R2 ? "--config wrangler.test-r2.toml" : ""} --command "${q}"`, { cwd: new URL(".", import.meta.url).pathname, stdio: ["ignore", "pipe", "ignore"] }).toString())[0].results;

const U = await sign("mtU"), A = await sign("mtA");
sql(`UPDATE users SET role='admin' WHERE username='mtA${rnd}'; DELETE FROM ratelimits; DELETE FROM lab_rubrics WHERE exam_key='ipho2024'`);   // graded from the solution's scheme, not an admin rubric
const [, st] = await call("POST", "/lab/start", { comp: "ipho", year: 2024, tasks: ["E1"], lang: "ko", sources: { E1: { sol: "IPhO_2024_S1" + rnd + ".pdf" } } }, U);
const sid = st.session.id, key = st.token;
await call("POST", `/lab/sessions/${sid}/finish`, null, U);
let [s, j] = await up(sid, key, "E1", "answer", png);
const pid = j.id;
ok(s === 200, "a page sent");

/* 1. a page read on arrival: Upstage, then Gemini, each one row with tokens, price and time */
let rows = sql(`SELECT step,provider,model,in_tok,out_tok,cached_tok,pages,usd,ms,ok FROM lab_calls WHERE session_id=${sid} ORDER BY id`);
const ocrRow = rows.find(r => r.step === "ocr"), readRow = rows.find(r => r.step === "read");
ok(ocrRow && ocrRow.provider === "upstage" && ocrRow.pages === 1 && near(ocrRow.usd, 0.01), "Upstage reading: one page, $0.01 " + JSON.stringify(ocrRow));
ok(readRow && readRow.in_tok === 1000 && readRow.out_tok === 250 && readRow.cached_tok === 400 && near(readRow.usd, ((1000 - 0.75 * 400) * 0.30 + 250 * 2.50) / 1e6),
  "Gemini reading: 1000 in (400 cached), 200 out + 50 thinking, priced as gemini-flash-latest " + JSON.stringify(readRow));

/* 2. the photo: in R2 (data empty) or in the row */
const pg = sql(`SELECT length(data) n, r2_key FROM lab_pages WHERE id=${pid}`)[0];
ok(R2 ? pg.r2_key && pg.n === 0 : !pg.r2_key && pg.n === png.length, R2 ? "the photo went to R2, the row keeps no copy " + JSON.stringify(pg) : "no R2 bucket: the photo stays in the row");
let img = await fetch(B + `/lab/pages/${pid}/img`, { headers: { Authorization: "Bearer " + U } });
ok(img.status === 200 && Buffer.from(await img.arrayBuffer()).equals(png), "the candidate gets the photo back");

/* 3. grading: the scheme, the grade, each recorded; the session keeps the totals */
[s, j] = await call("POST", `/lab/sessions/${sid}/submit`, {}, U);
const e1 = j.session.detail.tasks.E1;
ok(j.session.status === "graded" && e1.usage && e1.usage.calls === 2 && e1.usage.in === 2000 && near(e1.usage.usd, 2 * ((1000 - 300) * 0.30 + 250 * 2.50) / 1e6) && e1.usage.wall_ms >= 0,
  "the experiment's grading: scheme + grade calls, tokens and price " + JSON.stringify(e1.usage));
ok(typeof j.session.detail.grade_ms === "number", "the session records how long grading took");
rows = sql(`SELECT step FROM lab_calls WHERE session_id=${sid} ORDER BY id`).map(r => r.step);
ok(rows.join() === "ocr,read,scheme,grade", "four calls in all, in order " + rows.join());

/* 4. the admins' view: cost, tokens and time per exam and per step */
[s] = await call("GET", "/admin/lab/metrics", null, U);
ok(s === 403, "metrics are for admins only");
[s, j] = await call("GET", "/admin/lab/metrics?days=1", null, A);
const mine = j.sessions && j.sessions.find(x => x.id === sid);
ok(s === 200 && mine && mine.calls === 4 && near5(mine.usd, 0.01 + 3 * ((1000 - 300) * 0.30 + 250 * 2.50) / 1e6) && mine.wait_s != null && mine.grade_ms != null,
  "metrics: this exam's 4 calls, its price, and its times " + JSON.stringify(mine));
ok(j.per_exam.n >= 1 && j.per_exam.avg_usd > 0 && ["ocr", "read", "scheme", "grade"].every(x => j.steps.some(y => y.step === x)), "averages per exam and a line per step");
ok(j.storage.pages >= 1 && (R2 ? j.r2 === true : j.r2 === false), "how many photos are kept, and where " + JSON.stringify(j.storage));

/* 5. accuracy: an admin's reference marks against the AI's */
[s, j] = await call("GET", `/lab/sessions/${sid}`, null, A);
ok(s === 200 && Array.isArray(j.session.reviews) && j.session.reviews.length === 0, "an admin sees the reference marks (none yet)");
[, j] = await call("GET", `/lab/sessions/${sid}`, null, U);
ok(j.session.reviews === undefined, "…the candidate does not");
[s] = await call("POST", `/admin/lab/${sid}/review`, { task: "E1", items: [{ id: "A.1", ref: 0.4 }] }, U);
ok(s === 403, "only admins give reference marks");
const ai = Object.fromEntries(e1.items.map(i => [i.id, i.got]));
[s, j] = await call("POST", `/admin/lab/${sid}/review`, { task: "E1", items: [{ id: "A.1", ref: 0.4 }, { id: "A.2", ref: 0.3 }, { id: "C.1", ref: 1.0 }, { id: "B.1", ref: 99 }, { id: "Z.9", ref: 1 }] }, A);
ok(s === 200 && j.saved === 3, "three marks kept; one above full marks and one unknown item refused " + JSON.stringify(j));
[, j] = await call("GET", "/admin/lab/metrics?days=1", null, A);
const want = [Math.abs(ai["A.1"] - 0.4), Math.abs(ai["A.2"] - 0.3), Math.abs(ai["C.1"] - 1.0)];
const t = j.accuracy.tasks.find(x => x.key === sid + ":E1");
ok(j.accuracy.items >= 3 && t && near(t.ai, ai["A.1"] + ai["A.2"] + ai["C.1"]) && near(t.ref, 1.7), "accuracy: the AI's and the reference totals of the reviewed items " + JSON.stringify(t));
ok(want.length === 3, "per-item differences " + JSON.stringify(want));
[, j] = await call("GET", `/lab/sessions/${sid}`, null, A);
ok(j.session.reviews.length === 3 && j.session.reviews.find(r => r.item_id === "A.2").ref_points === 0.3, "the report shows the admin the marks given");

/* 6. the keeping time (R2 run: LAB_KEEP_HOURS=0): after grading the photo is removed, the report stays */
if (R2) {
  await call("GET", "/admin/lab/metrics?days=1", null, A);                   // runs the removal
  const after = sql(`SELECT length(data) n, purged_at FROM lab_pages WHERE id=${pid}`)[0];
  img = await fetch(B + `/lab/pages/${pid}/img`, { headers: { Authorization: "Bearer " + U } });
  ok(after.purged_at > 0 && img.status === 410, "keeping time over: the photo is removed (410), marked purged " + JSON.stringify(after));
  [, j] = await call("GET", `/lab/sessions/${sid}`, null, U);
  ok(j.session.status === "graded" && j.session.pages[0].read && j.session.detail.tasks.E1.items.length === 5, "…what was read and the marks stay");
}
console.log(fails ? fails + " FAILED" : "all passed");
process.exit(fails ? 1 : 0);
