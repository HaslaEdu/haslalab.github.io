// v8 exam mode: tokens, the server clock, scanning, grading.  Against `npm run dev` on a fresh local DB whose
// .dev.vars has the stand-in OCR/grader of test-lab-mock.mjs (UPSTAGE_BASE, GEMINI_BASE) and a short clock:
//   LAB_TEST_EXAM_SEC=6  LAB_TEST_SCAN_SEC=6  LAB_TEST_GRACE_SEC=1
// then:  node test-lab.mjs
import { execSync } from "node:child_process";
const B = (process.env.API || "http://127.0.0.1:8787") + "/api";
const EXAM = 6, SCAN = 6;
const call = async (m, p, body, tok, extra) => {
  const r = await fetch(B + p, { method: m, headers: { "Content-Type": "application/json", Origin: "http://localhost:8765", ...(tok ? { Authorization: "Bearer " + tok } : {}), ...(extra || {}) }, body: body ? JSON.stringify(body) : undefined });
  return [r.status, await r.json().catch(() => ({}))];
};
const up = async (sid, key, task, kind, bytes) => {
  const r = await fetch(B + `/lab/up/${sid}/pages?task=${task}&kind=${kind}`, { method: "PUT", headers: { "Content-Type": "image/png", "X-Lab-Token": key }, body: bytes });
  return [r.status, await r.json().catch(() => ({}))];
};
let fails = 0;
const ok = (c, msg) => { if (!c) fails++; console.log((c ? "PASS " : "FAIL ") + msg); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const rnd = Math.random().toString(36).slice(2, 7);
const sign = async u => (await call("POST", "/signup", { username: u + rnd, nickname: u + rnd, password: "password1" }))[1].token;
const tokens = async tok => (await call("GET", "/lab/active", null, tok))[1].tokens;
const ledger = async tok => (await call("GET", "/lab/tokens", null, tok))[1].ledger;
const png = Buffer.from("89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4890000000D49444154789C6360000002000154A24F5D0000000049454E44AE426082", "hex");
const X = { comp: "ipho", year: 2024, tasks: ["E1", "E2"], lang: "ko" };

const A = await sign("labA"), Bt = await sign("labB"), ADM = await sign("labAdm");
execSync(`npx wrangler d1 execute haslalab-community --local --command "UPDATE users SET role='admin' WHERE username='labAdm${rnd}'; DELETE FROM lab_rubrics WHERE exam_key='ipho2024'"`, { stdio: "ignore" });

/* login and the first token */
let [s, j] = await call("POST", "/lab/start", X);
ok(s === 401, "start needs login " + s);
[s, j] = await call("GET", "/lab/active", null, A);
ok(s === 200 && j.tokens === 5 && j.active === null, "a new account has five tokens, nothing open");
ok(await tokens(Bt) === 5, "so does another");
/* the rest of the run starts A from one token: an admin takes four back */
[s, j] = await call("POST", "/admin/lab/tokens", { user: "labA" + rnd, delta: -4, note: "test" }, ADM);
ok(s === 200 && j.tokens === 1, "admin takes back 4 → 1");

/* eight starts at once (double clicks, two tabs): one session, one token spent */
const many = await Promise.all(Array.from({ length: 8 }, () => call("POST", "/lab/start", X, A)));
const ids = new Set(many.map(([st, x]) => st === 200 && x.session && x.session.id));
ok(ids.size === 1 && !ids.has(false), "8 parallel starts → one session " + JSON.stringify(many.map(x => x[0])));
ok(many.filter(([, x]) => x.token).length === 1, "exactly one start got the upload token");
const first = many.find(([, x]) => x.token)[1], SID = first.session.id, T0 = first.session.started_at;
let KEY = first.token;
ok(await tokens(A) === 0, "one token spent, not eight");
let L = (await ledger(A)).filter(x => x.reason === "start");
ok(L.length === 1 && L[0].delta === -1 && L[0].reason === "start" && L[0].session_id === SID, "ledger: one -1 for this session");
ok(first.session.status === "running" && first.session.ended_at === T0 + EXAM && first.session.exam_sec === EXAM, "running, the clock ends at start + exam");

/* leaving and coming back: same session, same start, nothing spent */
await sleep(1500);
[s, j] = await call("POST", "/lab/start", X, A);
ok(s === 200 && j.resumed && j.session.id === SID && j.session.started_at === T0 && !j.token, "re-entering resumes the same exam");
ok(j.session.now - j.session.started_at >= 1, "the clock kept running while away (" + (j.session.now - T0) + " s)");
[s, j] = await call("GET", "/lab/active", null, A);
ok(j.active && j.active.id === SID && j.active.started_at === T0 && j.tokens === 0, "active: same session, started_at unchanged, still 0 tokens");
[s, j] = await call("POST", "/lab/start", { ...X, year: 2023 }, A);
ok(s === 409 && j.error === "other_active", "another exam while one is open → 409");
ok(await tokens(A) === 0 && (await ledger(A)).length === 2, "…and nothing spent");

/* the phone cannot send while the experiments run */
[s, j] = await up(SID, KEY, "E1", "answer", png);
ok(s === 409 && j.error === "closed", "no uploads while running " + s);
[s, j] = await call("POST", `/lab/sessions/${SID}/submit`, { pages: [] }, A);
ok(s === 409 && j.error === "running", "no submit while running");

/* other people */
[s, j] = await call("GET", `/lab/sessions/${SID}`, null, Bt);
ok(s === 404, "someone else cannot read the session");
[s, j] = await call("POST", `/lab/sessions/${SID}/finish`, null, Bt);
ok(s === 404, "someone else cannot finish it");

/* five hours (here: EXAM s) after the server's start, the bench goes dark by itself */
await sleep((T0 + EXAM + 1) * 1000 - Date.now() + 300);
[s, j] = await call("GET", "/lab/active", null, A);
ok(j.active && j.active.status === "scanning" && j.active.ended_at === T0 + EXAM && j.active.scan_until === T0 + EXAM + SCAN, "after the exam time: scanning, ended_at = start + exam " + JSON.stringify(j.active && [j.active.status, j.active.ended_at - T0]));
[s, j] = await call("POST", "/lab/start", X, A);
ok(s === 200 && j.resumed && j.session.id === SID && j.session.status === "scanning", "re-entering while scanning resumes the scan, no spend");
ok(await tokens(A) === 0, "still 0 tokens");

/* the phone */
[s, j] = await call("GET", `/lab/up/${SID}`, null, null, { "X-Lab-Token": "x".repeat(32) });
ok(s === 403, "wrong upload token → 403");
[s, j] = await call("GET", `/lab/up/${SID}`, null, null, { "X-Lab-Token": KEY });
ok(s === 200 && j.open && j.tasks.join() === "E1,E2", "phone sees the open session");
[s, j] = await up(SID, KEY, "E1", "answer", png);
ok(s === 200 && j.ocr_status === "done" && j.no === 1, "page 1 uploaded and read " + JSON.stringify(j));
const P1 = j.id;
[s, j] = await up(SID, KEY, "E2", "working", png);
ok(s === 200 && j.no === 2, "page 2");
[s, j] = await up(SID, KEY, "E3", "answer", png);
ok(s === 400 && j.error === "bad_task", "unknown task refused");
[s, j] = await up(SID, KEY, "E1", "answer", Buffer.from("not an image"));
ok(s === 415, "non-image refused");
/* a new QR (a computer that lost the token) retires the old one */
[s, j] = await call("POST", `/lab/sessions/${SID}/qr`, null, A);
ok(s === 200 && j.token && j.token !== KEY, "new upload token");
[s] = await call("GET", `/lab/up/${SID}`, null, null, { "X-Lab-Token": KEY });
ok(s === 403, "old token retired");
KEY = j.token;
let r = await fetch(B + `/lab/pages/${P1}/img`, { headers: { Authorization: "Bearer " + A } });
ok(r.status === 200 && r.headers.get("content-type") === "image/png", "owner reads the page image");
r = await fetch(B + `/lab/pages/${P1}/img`, { headers: { Authorization: "Bearer " + Bt } });
ok(r.status === 404, "others cannot");

/* check the text and submit: E1 has a marking scheme, E2 not yet */
[s, j] = await call("POST", "/admin/lab/rubrics", { exam_key: "ipho2024", task: "E1", points: 10, rubric: JSON.stringify([{ id: "A1", name: "R0", max: 4, requirement: "R0 about 108 ohm" }, { id: "A2", name: "lambda", max: 6, requirement: "lambda 380-410" }]), reference: "R0 = 108 ohm" }, A);
ok(s === 403, "rubrics are admin only");
[s, j] = await call("POST", "/admin/lab/rubrics", { exam_key: "ipho2024", task: "E1", points: 10, rubric: JSON.stringify([{ id: "A1", name: "R0", max: 4, requirement: "R0 about 108 ohm" }, { id: "A2", name: "lambda", max: 6, requirement: "lambda 380-410" }]), reference: "R0 = 108 ohm" }, ADM);
ok(s === 200, "admin saves the E1 scheme");
[s, j] = await call("GET", `/lab/sessions/${SID}`, null, A);
const txt = j.session.pages.find(p => p.id === P1).text;
[s, j] = await call("PATCH", `/lab/sessions/${SID}/pages/${P1}`, { text: txt + "\nA.3 h = 12 W/(m2 K)" }, A);
ok(s === 400 && j.error === "read_only", "what was read cannot be edited (a strict invigilator)");
[s, j] = await call("POST", `/lab/sessions/${SID}/submit`, { pages: [] }, A);
const ses = j.session;
ok(s === 200 && ses.status === "pending" && ses.detail.tasks.E1.status === "graded" && ses.detail.tasks.E1.score === 5 && ses.detail.tasks.E2.why === "no_solution",
  "E1 graded 5/10 from the scheme, E2 waits for one " + JSON.stringify(ses.detail && Object.values(ses.detail.tasks).map(x => [x.status, x.score])));
ok(ses.pages.find(p => p.id === P1).text === txt && ses.detail.tasks.E1.grader.startsWith("gemini"), "the text stayed as read; graded by Gemini from the images");
[s, j] = await call("POST", `/lab/sessions/${SID}/submit`, { pages: [] }, A);
ok(s === 200 && j.session.status === "pending", "a second submit grades nothing again");
[s, j] = await up(SID, KEY, "E1", "answer", png);
ok(s === 409, "no uploads after submitting");
[s, j] = await call("GET", "/lab/active", null, A);
ok(j.active === null && j.tokens === 0, "nothing open after submitting");

/* no tokens left: no new exam, the balance never goes negative */
const tries = await Promise.all(Array.from({ length: 5 }, () => call("POST", "/lab/start", X, A)));
ok(tries.every(([st, x]) => st === 402 && x.error === "no_tokens"), "0 tokens → 402 every time " + JSON.stringify(tries.map(x => x[0])));
ok(await tokens(A) === 0 && (await ledger(A)).length === 2, "balance 0, ledger unchanged");
[s, j] = await call("GET", "/lab/sessions", null, A);
ok(j.sessions.length === 1, "no session was created by the refused starts");

/* admin: the scheme for E2 arrives, regrade; tokens are granted */
await call("POST", "/admin/lab/rubrics", { exam_key: "ipho2024", task: "E2", points: 10, rubric: JSON.stringify([{ id: "B1", name: "t", max: 10, requirement: "thickness" }]) }, ADM);
[s, j] = await call("POST", `/admin/lab/${SID}`, { task: "E2", regrade: true }, ADM);
ok(s === 200 && j.session.status === "graded" && j.session.score === 10, "regrade E2 → graded 5+5 = " + (j.session && j.session.score));
[s, j] = await call("POST", "/admin/lab/tokens", { user: "labA" + rnd, delta: 2 }, A);
ok(s === 403, "granting is admin only");
[s, j] = await call("POST", "/admin/lab/tokens", { user: "labA" + rnd, delta: 2, note: "test" }, ADM);
ok(s === 200 && j.tokens === 2 && await tokens(A) === 2, "admin grants 2");

/* two tokens, parallel starts: still only one spent */
const two = await Promise.all(Array.from({ length: 6 }, () => call("POST", "/lab/start", X, A)));
ok(new Set(two.map(([, x]) => x.session && x.session.id)).size === 1 && await tokens(A) === 1, "6 parallel starts with 2 tokens → one spent, 1 left");
const S2 = two[0][1].session.id;
/* finish early, twice */
[s, j] = await call("POST", `/lab/sessions/${S2}/finish`, null, A);
const end2 = j.session.ended_at;
ok(s === 200 && j.session.status === "scanning" && end2 < j.session.started_at + EXAM, "finish early → scanning now");
await sleep(1100);
[s, j] = await call("POST", `/lab/sessions/${S2}/finish`, null, A);
ok(j.session.ended_at === end2 && j.session.scan_until === end2 + SCAN, "a second finish changes nothing (the scan clock is not reset)");
[s, j] = await call("POST", "/lab/start", X, A);
ok(j.resumed && j.session.id === S2 && j.session.scan_until === end2 + SCAN && await tokens(A) === 1, "coming back during the scan: same deadline, no spend");
/* nobody submits: after the scan time the pages that arrived are submitted by themselves */
await sleep((end2 + SCAN + 2) * 1000 - Date.now() + 300);
[s, j] = await call("GET", `/lab/sessions/${S2}`, null, A);
ok(j.session.status === "graded" && j.session.detail.tasks.E1.status === "empty", "after the scan time: submitted as it stood (no pages → empty) " + j.session.status);
[s, j] = await call("DELETE", `/lab/sessions/${S2}`, null, A);
ok(s === 200, "a finished session can be deleted");
ok(await tokens(A) === 1, "…which gives no token back");

/* the last token */
[s, j] = await call("POST", "/lab/start", { comp: "apho", year: 2025, tasks: ["E1"] }, A);
ok(s === 200 && !j.resumed && await tokens(A) === 0, "the last token starts APhO 2025");
L = await ledger(A);
ok(5 + L.reduce((a, x) => a + x.delta, 0) === 0 && L.filter(x => x.reason === "start").length === 3, "ledger: 5 (default) - 4 (revoke) + 2 (grant) - 3 (starts) = 0 " + JSON.stringify(L.map(x => x.delta)));
[s, j] = await call("DELETE", `/lab/sessions/${j.session.id}`, null, A);
ok(s === 409, "an open exam cannot be deleted (no way to dodge the clock)");

/* B is untouched by all of this */
ok(await tokens(Bt) === 5, "another account still has its own five tokens");
/* a year with separate rounds (IOAA D1, D2): another round is another exam, not a resume */
const io0 = (await call("GET", "/lab/stats?comp=ioaa", null, Bt))[1].exams["ioaa2024:D1"] || { sat: 0, graded: 0 };   // earlier runs leave theirs; signed in, so not an edge copy
[s, j] = await call("POST", "/lab/start", { comp: "ioaa", year: 2024, tasks: ["D1"] }, Bt);
ok(s === 200 && !j.resumed && j.session.tasks.join() === "D1", "B starts IOAA 2024 D1");
[s, j] = await call("POST", "/lab/start", { comp: "ioaa", year: 2024, tasks: ["D2"] }, Bt);
ok(s === 409 && j.error === "other_active" && j.other.tasks.join() === "D1", "D2 of the same year while D1 is open → 409, not a resume of D1");
[s, j] = await call("POST", "/lab/start", { comp: "ioaa", year: 2024, tasks: ["D1"] }, Bt);
ok(s === 200 && j.resumed && await tokens(Bt) === 4, "D1 again → resumed, one token spent in all");
/* the exam list's numbers and the score report's standing */
[s, j] = await call("GET", "/lab/stats?comp=ipho");
const st = j.exams && j.exams["ipho2024:E1+E2"];
ok(s === 200 && st && st.sat >= 1 && st.graded >= 1 && typeof st.avg === "number", "stats: IPhO 2024 E1+E2 has candidates and an average " + JSON.stringify(st));
ok(j.exams && !j.exams["ioaa2024:D1"], "stats are per competition");
[s, j] = await call("GET", "/lab/stats?comp=ioaa", null, Bt);        // signed in: not the few-second edge copy
ok(j.exams["ioaa2024:D1"] && j.exams["ioaa2024:D1"].sat === io0.sat + 1 && j.exams["ioaa2024:D1"].graded === io0.graded, "stats: an ungraded sitting counts as a candidate, not in the average " + JSON.stringify([io0, j.exams["ioaa2024:D1"]]));
[s, j] = await call("GET", `/lab/sessions/${SID}`, null, A);
ok(j.session.standing && j.session.standing.rank >= 1 && j.session.standing.n >= 1 && j.session.standing.first === true && j.session.nickname === "labA" + rnd,
  "score report: rank among first sittings, first sitting, candidate name " + JSON.stringify(j.session.standing));
[s, j] = await call("POST", "/admin/lab/tokens", { user: "labB" + rnd, delta: -9 }, ADM);
ok(s === 200 && j.tokens === 0, "taking back more than the balance stops at 0");
console.log(fails ? `${fails} FAILED` : "all passed");
process.exit(fails ? 1 : 0);
