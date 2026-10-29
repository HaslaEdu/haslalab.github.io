// v15: half tokens.  The experiments or the theory of a year that has both (pair) cost half a token to grade; a set of
// the two, one token.  Against `npm run dev` with test-lab-mock.mjs and the 6-second clock of test-lab.mjs, migration
// 0011 applied:  node test-half.mjs
import { execSync } from "node:child_process";
const B = (process.env.API || "http://127.0.0.1:8787") + "/api";
const call = async (m, p, body, tok) => { const r = await fetch(B + p, { method: m, headers: { "Content-Type": "application/json", ...(tok ? { Authorization: "Bearer " + tok } : {}) }, body: body ? JSON.stringify(body) : undefined }); return [r.status, await r.json().catch(() => ({}))]; };
let fails = 0;
const ok = (c, msg) => { if (!c) fails++; console.log((c ? "PASS " : "FAIL ") + msg); };
const rnd = Math.random().toString(36).slice(2, 7);
const sql = q => JSON.parse(execSync(`npx wrangler d1 execute haslalab-community --local --json --command "${q}"`, { cwd: new URL(".", import.meta.url).pathname, stdio: ["ignore", "pipe", "ignore"] }).toString())[0].results;
const U = (await call("POST", "/signup", { username: "hf" + rnd, nickname: "hf" + rnd, password: "password1" }))[1].token;
sql(`DELETE FROM ratelimits; UPDATE users SET exam_tokens=1, exam_half=0 WHERE username='hf${rnd}'`);
const sit = async (x) => { const [s, j] = await call("POST", "/lab/start", x, U); if (!j.session) console.log("start:", s, JSON.stringify(j).slice(0, 300)); await call("POST", `/lab/sessions/${j.session.id}/finish`, null, U); return [s, j]; };
const EXP = { comp: "ipho", year: 2024, tasks: ["E1"], lang: "ko", sources: { E1: { sol: "IPhO_2024_S1.pdf" } }, pair: true };
const THY = { comp: "ipho", year: 2024, tasks: ["T1"], lang: "ko", sources: { T1: { sol: "IPhO_2024_T1S.pdf", kind: "theory" } }, pair: true };

let [s, j] = await sit(EXP);
ok(s === 200 && j.session.cost === 0.5 && j.tokens === 1, "the experiments of a year with theory too: grading costs 0.5 " + JSON.stringify([s, j.session && j.session.cost, j.tokens]));
let [, p] = await call("POST", `/lab/sessions/${j.session.id}/pay`, {}, U);
ok(p.session && p.session.paid && p.tokens === 0.5, "paid half a token: 1 → 0.5 " + JSON.stringify([p.error, p.tokens]));
await call("POST", `/lab/sessions/${j.session.id}/submit`, {}, U);
[s, j] = await sit(THY);
ok(j.session.cost === 0.5 && j.session.kind === "theory", "the theory of the same year: 0.5");
[, p] = await call("POST", `/lab/sessions/${j.session.id}/pay`, {}, U);
ok(p.session && p.session.paid && p.tokens === 0, "the half put aside pays it: 0.5 → 0 (the set cost one token) " + JSON.stringify([p.error, p.tokens]));
await call("POST", `/lab/sessions/${j.session.id}/submit`, {}, U);
const led = sql(`SELECT delta, note FROM lab_ledger l JOIN users u ON u.id=l.user_id WHERE u.username='hf${rnd}' AND reason='grade' ORDER BY l.id`);
ok(led.length === 2 && led[0].delta === -1 && led[1].delta === 0 && led.every(r => r.note === "half"), "ledger: −1 (half put aside), then 0 from the half " + JSON.stringify(led));
[s, j] = await sit(EXP);
[s, p] = await call("POST", `/lab/sessions/${j.session.id}/pay`, {}, U);
ok(s === 402 && p.error === "no_tokens" && p.tokens === 0, "no token and no half: 402");
await call("POST", `/lab/sessions/${j.session.id}/submit`, { grade: false }, U);
/* a whole-token sitting never uses half: without pair, and a combined (NBPhO) one even with pair */
sql(`UPDATE users SET exam_tokens=0, exam_half=1 WHERE username='hf${rnd}'`);
[s, j] = await sit({ ...EXP, pair: undefined });
ok(j.session.cost === 1 && j.tokens === 0.5, "no pair: a whole token; the half shows as 0.5 tokens");
[s, p] = await call("POST", `/lab/sessions/${j.session.id}/pay`, {}, U);
ok(s === 402, "half a token does not pay a whole-token grading");
await call("POST", `/lab/sessions/${j.session.id}/submit`, { grade: false }, U);
[s, j] = await sit({ comp: "nbpho", year: 2024, tasks: ["E1", "T"], lang: "ko", pair: true, sources: { E1: { sol: "NBPhO_2024_P5S.pdf", no: "5" }, T: { sol: "NBPhO_2024_TS.pdf", kind: "theory", skip: "5" } } });
ok(j.session.kind === "mixed" && j.session.cost === 1, "NBPhO (experiments and theory in one sitting): a whole token, pair or not");
await call("POST", `/lab/sessions/${j.session.id}/submit`, { grade: false }, U);
/* two halves at the same moment: one token taken, not two */
sql(`UPDATE users SET exam_tokens=1, exam_half=0 WHERE username='hf${rnd}'`);
[s, j] = await sit(THY);
const r3 = await Promise.all([1, 2, 3].map(() => call("POST", `/lab/sessions/${j.session.id}/pay`, {}, U)));
const u = sql(`SELECT exam_tokens, exam_half FROM users WHERE username='hf${rnd}'`)[0];
ok(u.exam_tokens === 0 && u.exam_half === 1 && r3.every(([st]) => st === 200), "three pays at once charge half once " + JSON.stringify(u));
console.log(fails ? fails + " FAILED" : "all passed");
process.exit(fails ? 1 : 0);
