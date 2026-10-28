// v9 grading from the page images: the scheme drawn from the official solution, the page read on arrival, the strict
// regulation applied in code.  Against `npm run dev` with test-lab-mock.mjs (see its header) and the 6-second clock
// of test-lab.mjs (LAB_TEST_EXAM_SEC=6 LAB_TEST_SCAN_SEC=6 LAB_TEST_GRACE_SEC=1), then:  node test-lab-grading.mjs
import { execSync } from "node:child_process";
const B = (process.env.API || "http://127.0.0.1:8787") + "/api";
const call = async (m, p, body, tok, extra) => { const r = await fetch(B + p, { method: m, headers: { "Content-Type": "application/json", ...(tok ? { Authorization: "Bearer " + tok } : {}), ...(extra || {}) }, body: body ? JSON.stringify(body) : undefined }); return [r.status, await r.json().catch(() => ({}))]; };
const up = async (sid, key, task, kind, bytes) => { const r = await fetch(B + `/lab/up/${sid}/pages?task=${task}&kind=${kind}`, { method: "PUT", headers: { "Content-Type": "image/png", "X-Lab-Token": key }, body: bytes }); return [r.status, await r.json().catch(() => ({}))]; };
let fails = 0;
const ok = (c, msg) => { if (!c) fails++; console.log((c ? "PASS " : "FAIL ") + msg); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const rnd = Math.random().toString(36).slice(2, 7);
const sign = async u => (await call("POST", "/signup", { username: u + rnd, nickname: u + rnd, password: "password1" }))[1].token;
const png = Buffer.from("89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4890000000D49444154789C6360000002000154A24F5D0000000049454E44AE426082", "hex");
const pad = n => Buffer.concat([png, Buffer.alloc(n, 0)]);           // bytes after IEND: the stand-in reads these as another header / a poor page
const sql = q => execSync(`npx wrangler d1 execute haslalab-community --local --json --command "${q}"`, { cwd: new URL(".", import.meta.url).pathname }).toString();
sql("DELETE FROM lab_schemes; DELETE FROM lab_rubrics; DELETE FROM ratelimits");
const X = { comp: "ipho", year: 2024, tasks: ["E1", "E2"], lang: "ko", sources: { E1: { sol: "IPhO_2024_S1_KO.pdf" }, E2: { sol: "IPhO_2099_missing.pdf" } } };
const toScan = async (tok, x) => {
  const [, j] = await call("POST", "/lab/start", x, tok);
  await call("POST", `/lab/sessions/${j.session.id}/finish`, null, tok);
  return { sid: j.session.id, key: j.token };
};

/* one exam, three pages */
const G = await sign("grA");
let { sid, key } = await toScan(G, X);
let [s, j] = await up(sid, key, "E1", "answer", png);
ok(s === 200 && j.task === "E1" && j.kind === "answer" && j.legible === "good" && j.items === 4 && !j.moved, "page 1 read on arrival: 4 answers, legible, stays E1 answer sheet " + JSON.stringify(j));
[s, j] = await up(sid, key, "E1", "answer", pad(400));
ok(s === 200 && j.task === "E2" && j.kind === "working" && j.moved, "page 2: the printed header says E2 working sheet, so it goes there although the phone said E1 answer");
[s, j] = await up(sid, key, "E1", "working", pad(800));
ok(s === 200 && j.legible === "poor", "page 3: a poor page is marked poor");
const P3 = j.id;
ok((await (await fetch("http://127.0.0.1:8799/seen")).json()).ocrIntoRead >= 3, "each page went through Upstage first, its transcript beside the image for Gemini");
[s, j] = await up(sid, key, "E1", "answer", pad(450));
ok(s === 200 && j.legible === "partial", "Upstage unsure of a page (confidence 0.5) → at best «partial», although Gemini called it good " + JSON.stringify(j));
await call("DELETE", `/lab/sessions/${sid}/pages/${j.id}`, null, G);
[s, j] = await call("GET", `/lab/up/${sid}`, null, null, { "X-Lab-Token": key });
ok(j.pages.map(p => p.legible).join() === "good,good,poor", "the phone sees how each page was read");
[s, j] = await call("GET", `/lab/sessions/${sid}`, null, G);
ok(j.session.pages[0].read && j.session.pages[0].read.items.length === 4 && j.session.regulation.rules.length === 11, "the computer sees what was read on each page and the regulation");
[s, j] = await call("PATCH", `/lab/sessions/${sid}/pages/${j.session.pages[0].id}`, { text: "A.3 h = 11 W/(m2 K)" }, G);
ok(s === 400 && j.error === "read_only", "the candidate cannot type answers in after the exam");

/* submit: E1 from the scheme of the official solution; E2's solution does not exist */
[s, j] = await call("POST", `/lab/sessions/${sid}/submit`, {}, G);
const e1 = j.session.detail.tasks.E1, e2 = j.session.detail.tasks.E2, it = id => e1.items.find(x => x.id === id);
ok(e1.status === "graded" && e1.points === 3.5 && e1.regulation === "2026-10-29", "E1 graded against the 3.5-point scheme, regulation version recorded");
ok(it("A.1").got === 0.4 && it("A.1").by === "code" && it("A.1").value === 108.2, "A.1: 108.2 in [105, 111] → full 0.4, decided by the code (the model said half)");
ok(it("A.2").got === 0.6, "A.2: 395 in [380, 410] → full 0.6");
ok(it("A.3").got === 0 && it("A.3").rules.includes("R9"), "A.3: the model claims 11, which was read on no page → 0 (R9)");
ok(it("B.1").got === 0.4 && it("B.1").rules.includes("R7"), "B.1 graph: axes 0.2 + fitted line 0.2; 6 points < 8 and no slope read → 0.4 (R7) " + JSON.stringify(it("B.1")));
ok(it("C.1").got === 0.5 && it("C.1").by === "model", "C.1 derivation: the model's half mark");
ok(e1.score === 1.9, "E1 total 0.4 + 0.6 + 0 + 0.4 + 0.5 = 1.9 (got " + e1.score + ")");
ok(e1.feedback.length === 1 && e1.feedback[0].page === 1, "feedback pointing at a page that does not exist is dropped");
ok(e2.status === "pending" && e2.why === "no_solution", "E2: no official solution file → waits (no_solution)");
const kept = sql("SELECT source FROM lab_schemes");
ok(/IPhO_2024_S1_KO\.pdf/.test(kept) && (kept.match(/"source"/g) || []).length === 1, "the scheme drawn from the English original is kept under the solution the exam named");

/* a final answer on a working sheet does not count (R1) */
const H = await sign("grB");
({ sid, key } = await toScan(H, { ...X, tasks: ["E1"], sources: { E1: { sol: "IPhO_2024_S1.pdf" } } }));
await up(sid, key, "E1", "working", png);
[s, j] = await call("POST", `/lab/sessions/${sid}/submit`, {}, H);
const w = j.session.detail.tasks.E1;
ok(w.status === "graded" && w.items.filter(x => x.id !== "C.1").every(x => x.got === 0 && x.rules.includes("R1")) && w.score === 0.5,
  "only a working sheet: every answer-sheet item 0 (R1), the method mark stays → 0.5 " + JSON.stringify(w.items.map(x => [x.id, x.got, x.rules])));
ok(/IPhO_2024_S1\.pdf/.test(sql("SELECT source FROM lab_schemes")), "a second solution name keeps its own scheme");

/* the owner can take a bad shot out before submitting */
const K = await sign("grC");
({ sid, key } = await toScan(K, { ...X, tasks: ["E1"] }));
[s, j] = await up(sid, key, "E1", "answer", pad(800));
[s] = await call("DELETE", `/lab/sessions/${sid}/pages/${j.id}`, null, K);
[, j] = await call("GET", `/lab/sessions/${sid}`, null, K);
ok(s === 200 && j.session.pages.length === 0, "a bad shot taken out from the computer");
[s] = await call("DELETE", `/lab/sessions/${sid}/pages/${P3}`, null, K);
[, j] = await call("GET", `/lab/sessions/${(await call("GET", "/lab/sessions", null, G))[1].sessions[0].id}`, null, G);
ok(j.session.pages.length === 3, "…but not someone else's page");
/* pages sent at the same moment get different numbers */
const M = await sign("grD");
({ sid, key } = await toScan(M, { ...X, tasks: ["E1"], sources: { E1: { sol: "IPhO_2024_flaky" + rnd + ".pdf" } } }));
const par = await Promise.all([1, 2, 3, 4, 5].map(() => up(sid, key, "E1", "answer", png)));
const nos = par.map(([, x]) => x.no).sort();
ok(par.every(([st]) => st === 200) && new Set(nos).size === 5 && nos.join() === "1,2,3,4,5", "5 pages sent at once are numbered 1–5 " + JSON.stringify(nos));
/* the solution could not be fetched this time: an error, graded again by itself later */
[s, j] = await call("POST", `/lab/sessions/${sid}/submit`, {}, M);
ok(j.session.status === "error" && j.session.detail.tasks.E1.why === "scheme_failed", "solution fetch failed → error (not «no solution») " + j.session.status);
await sleep(2500);
[s, j] = await call("GET", `/lab/sessions/${sid}`, null, M);
ok(j.session.status === "graded" && j.session.detail.tasks.E1.status === "graded" && j.session.detail.tries === 1, "…and graded by itself on the next look " + JSON.stringify([j.session.status, j.session.detail.tries]));
/* R11: measured tables and graphs need enough measurements — the scheme's number, else 3 / 5 / 7 for an experiment
   that needs few, a medium number or many points.  The page read has 4 rows in each table and 6 points on the graph */
const Q = await sign("grE");
({ sid, key } = await toScan(Q, { ...X, tasks: ["E1"], sources: { E1: { sol: "IPhO_2024_table" + rnd + ".pdf" } } }));
[s, j] = await up(sid, key, "E1", "answer", pad(120));
ok(s === 200 && j.items === 7, "a page with two tables and a graph read " + JSON.stringify(j));
[s, j] = await call("POST", `/lab/sessions/${sid}/submit`, {}, Q);
const tq = j.session.detail.tasks.E1, iq = id => tq.items.find(x => x.id === id);
ok(iq("D.1").got === 0.2 && iq("D.1").rules.includes("R11") && iq("D.1").rules.includes("R8"), "D.1 table: 4 rows < the 5 the scheme asks → no marks for the count, columns kept (R8, R11) " + JSON.stringify(iq("D.1")));
ok(iq("D.2").got === 0.3 && iq("D.2").n_min === 7 && iq("D.2").rules.includes("R11"), "D.2 graph of a many-point measurement: 6 points < 7 → no marks for the count (R11) " + JSON.stringify(iq("D.2")));
ok(iq("D.3").got === 0.25 && iq("D.3").n_min === 5 && iq("D.3").rules.includes("R11"), "D.3 table with no count check, medium → 5: 4 rows halve its mark 0.5 → 0.25 (R11) " + JSON.stringify(iq("D.3")));
ok(j.session.regulation ? j.session.regulation.rules.some(r => r.id === "R11") : true, "R11 is part of the regulation");
console.log(fails ? fails + " FAILED" : "all passed");
process.exit(fails ? 1 : 0);
