// v13: theory exams.  A year's theory paper sat in exam mode: the tasks are marked kind "theory" when it starts, the
// marking scheme is drawn from the official solution together with a separate marking scheme when there is one, and
// the page reading and grading speak of a theory paper.  Against `npm run dev` with test-lab-mock.mjs and the 6-second
// clock of test-lab.mjs:  node test-theory.mjs
import { execSync } from "node:child_process";
const API = process.env.API || "http://127.0.0.1:8787", B = API + "/api", MOCK = "http://127.0.0.1:8799";
const call = async (m, p, body, tok) => { const r = await fetch(B + p, { method: m, headers: { "Content-Type": "application/json", ...(tok ? { Authorization: "Bearer " + tok } : {}) }, body: body ? JSON.stringify(body) : undefined }); return [r.status, await r.json().catch(() => ({}))]; };
const up = async (key, task, kind, bytes) => { const r = await fetch(B + `/lab/up/${sid}/pages?task=${task}&kind=${kind}`, { method: "PUT", headers: { "Content-Type": "image/png", "X-Lab-Token": key }, body: bytes }); return [r.status, await r.json().catch(() => ({}))]; };
let fails = 0;
const ok = (c, msg) => { if (!c) fails++; console.log((c ? "PASS " : "FAIL ") + msg); };
const rnd = Math.random().toString(36).slice(2, 7);
const sql = q => execSync(`npx wrangler d1 execute haslalab-community --local --command "${q}"`, { cwd: new URL(".", import.meta.url).pathname, stdio: "ignore" });
const sign = async u => (await call("POST", "/signup", { username: u + rnd, nickname: u + rnd, password: "password1" }))[1].token;
const png = Buffer.from("89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4890000000D49444154789C6360000002000154A24F5D0000000049454E44AE426082", "hex");
const seen = async () => (await fetch(MOCK + "/seen")).json();

const U = await sign("thU"); let sid;
sql(`DELETE FROM ratelimits; DELETE FROM lab_schemes WHERE exam_key='ipho1995'`);
const before = (await seen()).theorySchemes?.length || 0;
let [s, j] = await call("POST", "/lab/start", { comp: "ipho", year: 1995, tasks: ["T1", "T2"], lang: "ko",
  sources: { T1: { sol: `IPhO_1995_T1S${rnd}.pdf`, mark: `IPhO_1995_T1M${rnd}.pdf`, kind: "theory" }, T2: { sol: `IPhO_1995_T2S${rnd}.pdf`, mark: "../../etc/passwd", kind: "theory" } } }, U);
ok(s === 200 && j.session.kind === "theory" && j.token, "a theory exam of 1995 starts (years before 1990 are allowed for theory) " + JSON.stringify([s, j.error, j.session && j.session.kind]));
sid = j.session.id; const key = j.token;
[s, j] = await call("POST", "/lab/start", { comp: "ipho", year: 1995, tasks: ["T1", "T2"], lang: "ko", sources: {} }, U);
ok(s === 200 && j.resumed && j.session.id === sid, "coming back resumes the same theory exam");
await call("POST", `/lab/sessions/${sid}/pay`, {}, U);
await call("POST", `/lab/sessions/${sid}/finish`, null, U);
ok((await up(key, "T1", "answer", png))[0] === 200 && (await up(key, "T2", "answer", png))[0] === 200, "answer pages of T1 and T2 sent");
ok(((await seen()).theoryReads || 0) >= 2, "the pages were read as theory answer sheets");
[s, j] = await call("POST", `/lab/sessions/${sid}/submit`, {}, U);
const t1 = j.session && j.session.detail.tasks.T1, t2 = j.session && j.session.detail.tasks.T2;
ok(s === 200 && j.session.status === "graded" && t1.status === "graded" && t2.status === "graded" && j.session.kind === "theory", "graded " + JSON.stringify([s, j.error, t1 && t1.status, t2 && t2.status]));
const sc = ((await seen()).theorySchemes || []).slice(before);
const s1 = sc.find(x => x.pdfs[0] === `IPhO_1995_T1S${rnd}.pdf`), s2 = sc.find(x => x.pdfs[0] === `IPhO_1995_T2S${rnd}.pdf`);
ok(s1 && s1.pdfs.length === 2 && s1.pdfs[1] === `IPhO_1995_T1M${rnd}.pdf`, "T1's marking scheme was built from its solution and its separate marking scheme " + JSON.stringify(s1));
ok(s2 && s2.pdfs.length === 1, "T2: the solution alone (a bad marking-scheme name is dropped) " + JSON.stringify(s2));
ok(((await seen()).theoryGrades || 0) >= 2, "grading used the theory exam's wording and review");
ok(t1.review && t1.review.summary && t1.items.length > 0, "T1 has marks per item and a review");
[, j] = await call("GET", "/lab/stats?comp=ipho", null, U);
ok(j.exams["ipho1995:T1+T2"] && j.exams["ipho1995:T1+T2"].sat >= 1, "the exam list counts it as ipho1995:T1+T2");
/* NBPhO: the experiments and the rest of the booklet in one exam ("mixed") */
sql(`DELETE FROM ratelimits; UPDATE users SET exam_tokens=5 WHERE username='thU${rnd}'`);
[s, j] = await call("POST", "/lab/start", { comp: "nbpho", year: 2024, tasks: ["E1", "E2", "T"], lang: "ko",
  sources: { E1: { sol: `NBPhO_2024_P5S${rnd}.pdf`, no: "5" }, E2: { sol: `NBPhO_2024_P10S_missing${rnd}.pdf`, no: "10" }, T: { sol: `NBPhO_2024_TS${rnd}.pdf`, kind: "theory", skip: "5,10" } } }, U);
ok(s === 200 && j.session.kind === "mixed", "NBPhO: experiments and theory start as one exam (mixed) " + JSON.stringify([s, j.error, j.session && j.session.kind]));
sid = j.session.id; const key2 = j.token;
await call("POST", `/lab/sessions/${sid}/pay`, {}, U);
await call("POST", `/lab/sessions/${sid}/finish`, null, U);
for (const k of ["E1", "E2", "T"]) await up(key2, k, "answer", png);
ok(((await seen()).mixedReads || 0) >= 3, "pages read with the booklet's numbers: Problem 5 is E1");
const site0 = (await seen()).siteSolutions || 0;
[s, j] = await call("POST", `/lab/sessions/${sid}/submit`, {}, U);
const per = j.session && j.session.detail.tasks;
ok(s === 200 && ["E1", "E2", "T"].every(k => per[k] && per[k].status === "graded"), "all three graded " + JSON.stringify(per && Object.fromEntries(Object.entries(per).map(([k, v]) => [k, v.status]))));
const sn = await seen();
ok((sn.bookletNos || []).includes(5) && (sn.bookletNos || []).includes(10), "each experiment's scheme names its booklet number " + JSON.stringify(sn.bookletNos));
ok(sn.leftOut === "5, 10", "the theory scheme leaves the experiments out " + JSON.stringify(sn.leftOut));
ok((sn.siteSolutions || 0) > site0, "a solution cut out of the booklet is fetched from the site (pdfx/nbpho)");
console.log(fails ? fails + " FAILED" : "all passed");
process.exit(fails ? 1 : 0);
