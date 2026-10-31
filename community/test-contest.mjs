// node --test community/test-contest.mjs — no external provider calls or production tokens.
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import test from "node:test";
import worker from "./src/index.js";
import { CONTEST_PROOF_EXAMS } from "./src/contest-catalog.js";
import { contestGradeTask, contestMeta, CONTEST_REG } from "./src/contest.js";

const sqlite = new DatabaseSync(":memory:");
for (const file of readdirSync(new URL("./migrations/", import.meta.url)).filter(n => /^00(?:0[1-9]|1[01])_.*\.sql$/.test(n)).sort()) {
  sqlite.exec(readFileSync(new URL("./migrations/" + file, import.meta.url), "utf8"));
}
const DB = {
  prepare(sql) {
    const st = sqlite.prepare(sql);
    const make = args => ({ bind: (...bound) => make(bound), async first() { return st.get(...args) || null; },
      async all() { return { results: st.all(...args) }; }, async run() { return this.executeSync(); },
      executeSync() { if (st.columns().length) return { results: st.all(...args) }; const r = st.run(...args); return { success: true, meta: { changes: r.changes, last_row_id: Number(r.lastInsertRowid) } }; },
    });
    return make([]);
  },
  async batch(statements) {
    sqlite.exec("BEGIN");
    try { const out = statements.map(s => s.executeSync()); sqlite.exec("COMMIT"); return out; }
    catch (e) { sqlite.exec("ROLLBACK"); throw e; }
  },
};
globalThis.caches = { default: { async match() {}, async put() {} } };
const timestamp = Math.floor(Date.now() / 1000), tokens = {};
for (let id = 1; id <= 14; id++) {
  sqlite.prepare("INSERT INTO users(id,username,nickname,pw,role,created_at,exam_tokens) VALUES(?,?,?,?,?,?,?)").run(id, "student" + id, "Student " + id, "unused", id === 14 ? "admin" : "user", timestamp, 5);
  const token = String(id).padStart(48, "a"); tokens[id] = token;
  const hash = Buffer.from(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(token))).toString("base64url");
  sqlite.prepare("INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)").run(hash, id, timestamp, timestamp + 3600);
}
const messages=[];
const env = { DB, LAB_JOBS:{async sendBatch(items){messages.push(...items.map(item=>item.body));}}, ALLOWED_ORIGINS: "http://localhost:8765", LAB_KEEP_HOURS: "off", GEMINI_API_KEY: "mock-existing-key" };
const examId = "kmo-2025-T2-s2", base = "/api/lab/contest", sessionBase = id => `/api/lab/sessions/${id}`;
let providerCalls = [], providerBodies = [], providerUrls = [], proofMode = "valid", proofSummary = "";
const originalFetch = globalThis.fetch;
globalThis.fetch = async (input, init = {}) => {
  const url = String(input);
  providerUrls.push(url);
  if (/https:\/\/www\.(kms|kmo)\.or\.kr\//.test(url)) return new Response("%PDF-1.7\nMock trusted problem paper", { headers: { "content-type": "application/pdf" } });
  if (url.includes(":generateContent")) {
    const req = JSON.parse(init.body), prompt = req.contents[0].parts.filter(p => p.text).map(p => p.text).join("\n");
    providerCalls.push(prompt);
    providerBodies.push(req);
    let result;
    if (prompt.includes("[TASK: read page]")) result = { text:"Let n be an integer. This is the submitted proof.",header: { task: "Q5", sheet: "answer", page: 1 }, legible: "good", items: [{ label: "proof", kind: "text", text: "Let n be an integer. This is the submitted proof.", crossed_out: false }] };
    else {
      const number = +(prompt.match(/Review ONLY problem (\d+)/)?.[1] || 0), no = +(prompt.match(/\[Page (\d+);/)?.[1] || 1);
      result = { problem_no: number, score: 7, confidence: 0.96, verdict: "valid", summary: proofSummary || "검토한 논증입니다.", strengths: ["조건을 사용했습니다."], gaps: [], evidence: [{ page: no, quote: proofMode === "ungrounded" ? "invented unsupported words" : "Let n be an integer.", note: "제출한 문장" }] };
      if (proofMode === "uncertain") { result.verdict = "uncertain"; result.confidence = 0.3; }
    }
    return Response.json({ candidates: [{ content: { parts: [{ text: JSON.stringify(result) }] } }], usageMetadata: { promptTokenCount: 100, candidatesTokenCount: 50 } });
  }
  throw new Error("Unexpected external fetch " + url);
};
test.after(() => { globalThis.fetch = originalFetch; sqlite.close(); });
async function request(path, body, id = 1, method = body === undefined ? "GET" : "POST", headers = {}) {
  const response = await worker.fetch(new Request("http://worker.local" + path, { method,
    headers: { ...(id ? { Authorization: "Bearer " + tokens[id] } : {}), ...(body === undefined ? {} : { "Content-Type": "application/json" }), ...headers },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  }), env);
  return { status: response.status, data: await response.json() };
}
const start = (id, extra = {}) => request(base + "/start", { provider:"gemini", examId, purpose: "review", runId: "run-" + id, ...extra }, id);
const save = (sid, id, answers) => request(`${base}/sessions/${sid}/text`, { answers }, id);
async function drainQueue(settings=env){
  while(messages.length){const body=messages.shift();await worker.queue({messages:[{body,ack(){},retry(){throw Error('unexpected retry in completed-review fixture');}}]},settings);}
}
async function settled(path,body,id=1){
  const r=await request(path,body,id);
  if(r.status===200&&r.data.session?.status==='grading'){
    await drainQueue();return request(sessionBase(r.data.session.id),undefined,id);
  }
  return r;
}

test("catalogue uses trusted questions, offsets, time and 0.3-token review capability", async () => {
  const r = await request(base + "/catalog", undefined, null);
  assert.equal(r.status, 200); assert.equal(r.data.cost, 0.3); assert.equal(r.data.official, false);
  assert.equal(r.data.exams.length, Object.keys(CONTEST_PROOF_EXAMS).length);
  assert.deepEqual(r.data.exams.find(e => e.id === examId).tasks, ["Q5", "Q6", "Q7", "Q8"]);
  assert.ok(r.data.regulation.rules.every(r => /^M\d+$/.test(r.id)));
  assert.equal((await request(base + "/start", { examId }, null)).status, 401);
  assert.equal((await start(1, { examId: "injected-exam", sources: { Q5: { paper: "https://attacker.invalid" } } })).status, 400);
  for (const id of ["constructor", "toString", "__proto__"]) assert.equal((await start(1, { examId: id })).status, 400);
});

let first;
test("review start does not charge, trusts only catalog and records reception time honestly", async () => {
  const r = await start(1, { minutes: 1, points: [99], tasks: ["Q99"], sources: { _half: 1, _contest: { originalMinutes: 1 } }, entry: "?evil=true" });
  assert.equal(r.status, 200); first = r.data;
  const s = r.data.session;
  assert.equal(s.status, "scanning"); assert.equal(s.cost, 0.3); assert.equal(s.paid, false); assert.equal(r.data.tokens, 5);
  assert.equal(s.started_at, s.ended_at); assert.ok(Math.abs(s.started_at - timestamp) < 15);
  assert.equal(s.scan_until - s.started_at, 1800); assert.equal(s.exam_sec, 0); assert.equal(s.original_minutes, 180);
  assert.equal(s.purpose, "review"); assert.ok(s.entry_url.includes("contest-exam.html?id=" + examId));
  assert.deepEqual(s.tasks, ["Q5", "Q6", "Q7", "Q8"]); assert.deepEqual(s.regulation, CONTEST_REG);
  const stored = sqlite.prepare("SELECT * FROM lab_sessions WHERE id=?").get(s.id), src = JSON.parse(stored.sources);
  assert.equal(src.Q5.points, 7); assert.equal(src.Q5.paper, CONTEST_PROOF_EXAMS[examId].paper); assert.ok(!src._half);
  assert.equal((await start(1)).data.session.id, s.id);
  assert.equal((await start(1, { runId: "another-run" })).status, 409);
});

test("ownership, task validation, answer length and idempotent concurrent text saves", async () => {
  const sid = first.session.id;
  assert.equal((await save(sid, 2, { 5: "foreign" })).status, 404);
  for (const answers of [{ 1: "wrong offset" }, { Q5: "one", 5: "duplicate" }, { 5: "x".repeat(50001) }, ["array"]]) assert.equal((await save(sid, 1, answers)).status, 400);
  const results = await Promise.all([save(sid, 1, { 5: "Let n be an integer. Submitted proof." }), save(sid, 1, { Q5: "Let n be an integer. Updated proof." })]);
  assert.ok(results.every(r => r.status === 200));
  assert.equal(sqlite.prepare("SELECT COUNT(*) n FROM lab_pages WHERE session_id=?").get(sid).n, 1);
  assert.equal(results[1].data.session.pages[0].confirmed, true); assert.equal(results[1].data.session.pages[0].source, "typed");
  const qr = await request(sessionBase(sid) + "/qr", {}, 1); assert.equal(qr.status, 200); assert.ok(qr.data.token);
});

test("concurrent pay is charged exactly once at 0.3 token and no OCR until explicitly read", async () => {
  const sid = first.session.id, beforeCalls = providerCalls.length;
  const results = await Promise.all([request(sessionBase(sid) + "/pay", {}, 1), request(sessionBase(sid) + "/pay", {}, 1)]);
  assert.ok(results.every(r => r.status === 200)); assert.equal(providerCalls.length, beforeCalls);
  assert.equal(sqlite.prepare("SELECT exam_tokens FROM users WHERE id=1").get().exam_tokens, 4.7);
  assert.equal(sqlite.prepare("SELECT COUNT(*) n FROM lab_ledger WHERE session_id=? AND reason='grade'").get(sid).n, 1);
  assert.equal((await request(sessionBase(sid) + "/pay", {}, 2)).status, 404);
});

test("proof submission uses mathematics rules, two grounded reviews and retry-safe session payment", async () => {
  const sid = first.session.id, before = providerCalls.length;
  const r = await settled(sessionBase(sid) + "/submit", {}, 1);
  assert.equal(r.status, 200); assert.equal(r.data.session.status, "graded"); assert.equal(r.data.session.score, 7); assert.equal(r.data.session.points, 28);
  const q5 = r.data.session.detail.tasks.Q5;
  assert.equal(q5.grading_mode, "proof_review"); assert.equal(q5.official, false); assert.equal(q5.reference, "published_problem_only"); assert.equal(q5.verification.passes, 2);
  assert.equal(providerCalls.length - before, 2);
  assert.ok(providerCalls.slice(before).every(p => !p.includes("R1:") && !p.includes("EXPERIMENTAL physics")));
  assert.equal((await settled(sessionBase(sid) + "/submit", {}, 1)).data.tokens, 4.7); assert.equal(providerCalls.length - before, 2);
  assert.equal((await save(sid, 1, { 5: "late change" })).status, 409);
  assert.equal((await start(1)).data.session.id, sid, "same run returns the closed review rather than a duplicate charge");
  assert.equal((await request(sessionBase(sid), undefined, 1)).data.session.standing, null);
});

test("six-problem historic sessions keep the catalog's actual task count and time", async () => {
  const r = await start(3, { examId: "kmo-2020-T3" });
  assert.equal(r.status, 200); assert.equal(r.data.session.tasks.length, 6); assert.equal(r.data.session.original_minutes, 240);
  assert.equal((await save(r.data.session.id, 3, Object.fromEntries(Array.from({ length: 6 }, (_, i) => [i + 1, "Let n be an integer. Test proof."])))).status, 200);
});

test("unpaid scans are saved, require explicit payment, read once and require student confirmation", async () => {
  const r = await start(4, { mode: "paper" }), sid = r.data.session.id;
  const image = new Uint8Array([255, 216, 255, 224, 0, 16, 74, 70, 73, 70]);
  const response = await worker.fetch(new Request(`http://worker.local/api/lab/up/pages?task=Q5&kind=answer`, { method: "PUT", headers: { "X-Lab-Token": r.data.token, "Content-Type": "image/jpeg" }, body: image }), env);
  const upload = await response.json(); assert.equal(response.status, 200); assert.equal(upload.ocr_status, "unpaid");
  assert.equal((await request(`${base}/sessions/${sid}/read`, {}, 4)).status, 402);
  assert.equal((await settled(sessionBase(sid) + "/submit", {}, 4)).data.error, "needs_confirmation");
  assert.equal(sqlite.prepare("SELECT exam_tokens FROM users WHERE id=4").get().exam_tokens, 5);
  await request(sessionBase(sid) + "/pay", {}, 4);
  const before = providerCalls.length;
  const readResults = await Promise.all([request(`${base}/sessions/${sid}/read`, {}, 4), request(`${base}/sessions/${sid}/read`, {}, 4)]);
  assert.ok(readResults.every(r => r.status === 200)); assert.equal(providerCalls.length - before, 0);
  await drainQueue(); assert.equal(providerCalls.length-before,1);
  const pg = sqlite.prepare("SELECT * FROM lab_pages WHERE id=?").get(upload.id);
  assert.equal(pg.ocr_status, "done"); assert.equal(pg.edited, 0);
  assert.equal((await settled(sessionBase(sid) + "/submit", {}, 4)).data.error, "needs_confirmation");
  assert.equal((await request(`${base}/sessions/${sid}/pages/${pg.id}/confirm`, { text: "Let n be an integer. Corrected formula: n^2.", task: 9 }, 4)).status, 400);
  const confirmed = await request(`${base}/sessions/${sid}/pages/${pg.id}/confirm`, { text: "Let n be an integer. Corrected formula: n^2.", task: 5 }, 4);
  assert.equal(confirmed.status, 200); assert.equal(confirmed.data.session.pages[0].confirmed, true);
  assert.equal(confirmed.data.session.pages[0].source, "scan"); assert.ok(confirmed.data.session.pages[0].read.items.length);
  assert.equal((await settled(sessionBase(sid) + "/submit", {}, 4)).data.session.status, "graded");
});

test("empty submissions cannot spend tokens and insufficient balance stays atomic", async () => {
  const r = await start(5), sid = r.data.session.id;
  assert.equal((await settled(sessionBase(sid) + "/submit", {}, 5)).data.error, "no_answers");
  assert.equal(sqlite.prepare("SELECT exam_tokens FROM users WHERE id=5").get().exam_tokens, 5);
  sqlite.prepare("UPDATE users SET exam_tokens=0.2,exam_half=0 WHERE id=5").run();
  await save(sid, 5, { 5: "Let n be an integer." });
  const noBalance = await request(sessionBase(sid) + "/pay", {}, 5); assert.equal(noBalance.status, 402); assert.equal(noBalance.data.tokens, 0.2);
  assert.equal(sqlite.prepare("SELECT charged FROM lab_sessions WHERE id=?").get(sid).charged, 0);
  assert.equal(sqlite.prepare("SELECT COUNT(*) n FROM lab_ledger WHERE session_id=?").get(sid).n, 0);
});

test("unsupported or uncertain AI evidence yields pending, never an invented score", async () => {
  for (const [id, mode] of [[6, "ungrounded"], [7, "uncertain"]]) {
    const r = await start(id), sid = r.data.session.id; await save(sid, id, { 5: "Let n be an integer. Incomplete proof." });
    proofMode = mode;
    const result = await settled(sessionBase(sid) + "/submit", {}, id);
    assert.equal(result.status, 200); assert.equal(result.data.session.status, "pending"); assert.equal(result.data.session.score, null);
    assert.equal(result.data.session.detail.tasks.Q5.why, "uncertain_proof"); assert.equal(result.data.session.detail.tasks.Q5.manual_review, true);
  }
  proofMode = "valid";
});

test("math-specific admin reference and manual review preserve 7-point maximum", async () => {
  const r = await start(8), sid = r.data.session.id; await save(sid, 8, { 5: "Let n be an integer." });
  const noGrader = { ...env }; delete noGrader.GEMINI_API_KEY;
  const response = await worker.fetch(new Request("http://worker.local" + sessionBase(sid) + "/submit", { method: "POST", headers: { Authorization: "Bearer " + tokens[8], "Content-Type": "application/json" }, body: "{}" }), noGrader);
  assert.equal(response.status,503); assert.equal((await response.json()).error,'provider_unavailable');
  assert.equal(sqlite.prepare('SELECT charged FROM lab_sessions WHERE id=?').get(sid).charged,0,'no token is spent when selected provider is unavailable');
  assert.equal((await request(sessionBase(sid)+'/submit',{},8)).data.session.status,'grading');await drainQueue(noGrader);
  const pending=(await request(sessionBase(sid),undefined,8)).data; assert.equal(pending.session.status, "pending"); assert.equal(pending.session.detail.tasks.Q5.why, "provider_unavailable");
  assert.equal((await request(`/api/admin/lab/${sid}`, { task: "Q5", score: 8, points: 8 }, 14)).status, 400);
  const manual = await request(`/api/admin/lab/${sid}`, { task: "Q5", score: 4, points: 7, note: "수동 검토" }, 14);
  assert.equal(manual.status, 200); assert.equal(manual.data.session.detail.tasks.Q5.reviewed_by_admin, true); assert.equal(manual.data.session.official, false);
  const rubric = await request("/api/admin/lab/rubrics", { exam_key: "contest:" + examId, task: "Q5", points: 7, rubric: JSON.stringify([{ id: "M", max: 7, requirement: "Mathematical argument" }]), reference: "Reviewed mathematical reference" }, 14);
  assert.equal(rubric.status, 200);
});

test("catalog session validation cannot be forged through ordinary lab metadata", () => {
  assert.equal(contestMeta({ exam_key: "kmo2025", comp: "kmo", year: 2025, tasks: '["Q5"]', sources: JSON.stringify({ _contest: { examId, purpose: "review" } }) }), null);
});

test("parallel starts and parallel submits never create duplicate runs or provider charges", async () => {
  const starts = await Promise.all([start(9), start(9)]);
  assert.ok(starts.every(r => r.status === 200)); assert.equal(starts[0].data.session.id, starts[1].data.session.id);
  const sid = starts[0].data.session.id; await save(sid, 9, { 5: "Let n be an integer. Submitted proof." });
  const before = providerCalls.length, results = await Promise.all([settled(sessionBase(sid) + "/submit", {}, 9), settled(sessionBase(sid) + "/submit", {}, 9)]);
  assert.ok(results.every(r => r.status === 200)); assert.equal(providerCalls.length - before, 2);
  assert.equal(sqlite.prepare("SELECT COUNT(*) n FROM lab_sessions WHERE user_id=9").get().n, 1);
  assert.equal(sqlite.prepare("SELECT COUNT(*) n FROM lab_ledger WHERE session_id=?").get(sid).n, 1);
  assert.equal(sqlite.prepare("SELECT exam_tokens FROM users WHERE id=9").get().exam_tokens, 4.7);
});

test("provider disagreement and unexpected problem identities remain pending", async () => {
  const stored = sqlite.prepare("SELECT * FROM lab_sessions WHERE user_id=9").get();
  const page = { no: 1, task: "Q5", text: "Let n be an integer. Submitted proof.", edited: 1 };
  const valid = { problem_no: 5, score: 7, confidence: 0.95, verdict: "valid", summary: "Study review", strengths: [], gaps: [], evidence: [{ page: 1, quote: "Let n be an integer.", note: "Visible argument" }] };
  let calls = 0;
  const disagree = await contestGradeTask(env, stored, "Q5", [page], null, "ko", {}, { b64: v => Buffer.from(v).toString("base64"),
    async labVision() { calls++; return { model: "mock", raw: calls === 1 ? valid : { ...valid, score: 2, verdict: "partial" } }; } });
  assert.equal(disagree.status, "pending"); assert.equal(disagree.why, "review_disagreement"); assert.equal(disagree.score, null);
  const wrongTask = await contestGradeTask(env, stored, "Q5", [page], null, "ko", {}, { b64: v => Buffer.from(v).toString("base64"), async labVision() { return { model: "mock", raw: { ...valid, problem_no: 1 } }; } });
  assert.equal(wrongTask.why, "uncertain_proof");
  const tooLong = await contestGradeTask(env, stored, "Q5", [{ ...page, text: "x".repeat(150001) }], null, "ko", {}, { async labVision() { assert.fail("oversized answer reached provider"); } });
  assert.equal(tooLong.why, "answer_too_long");
});

test("untrusted redirects and non-PDF official-server responses never reach the grader", async () => {
  const stored = sqlite.prepare("SELECT * FROM lab_sessions WHERE user_id=9").get(), ex = CONTEST_PROOF_EXAMS["kmo-2025-T5"];
  const sources = { _provider:"gemini",_contest: { examId: ex.id, purpose: "review" } };
  const s = { ...stored, exam_key: "contest:" + ex.id, year: ex.year, tasks: '["Q1","Q2","Q3"]', sources: JSON.stringify(sources) };
  const fake = async mode => {
    const previous = globalThis.fetch, urls = [];
    globalThis.fetch = async url => { urls.push(String(url)); return mode === "redirect" ? new Response(null, { status: 302, headers: { location: "https://attacker.invalid/problem.pdf" } }) : new Response("<html>not a problem paper</html>"); };
    try {
      const result = await contestGradeTask(env, s, "Q1", [{ no: 1, text: "Let n be an integer.", edited: 1 }], null, "ko", {}, { b64: v => Buffer.from(v).toString("base64"), async labVision() { assert.fail("untrusted document reached provider"); } });
      assert.equal(result.why, "problem_unavailable"); assert.equal(result.score, null); assert.equal(urls.length, 1); assert.ok(!urls[0].includes("attacker.invalid"));
    } finally { globalThis.fetch = previous; }
  };
  await fake("redirect"); await fake("html");
});

test("ordinary experiment/theory session timing, physics rules and single-round cost still work", async () => {
  const r = await request("/api/lab/start", { provider:"gemini",comp: "ipho", year: 2024, tasks: ["E1"], pair: true, sources: { E1: { sol: "IPhO_2024_S1.pdf" }, _contest: { examId, purpose: "review" } } }, 10);
  assert.equal(r.status, 200); assert.equal(r.data.session.exam_sec, 5 * 3600); assert.equal(r.data.session.status, "running"); assert.equal(r.data.session.cost, 0.3);
  assert.equal(r.data.session.purpose, undefined); assert.ok(r.data.session.regulation.rules.some(r => r.id === "R1"));
  const sid = r.data.session.id;
  await request(sessionBase(sid) + "/finish", {}, 10);
  assert.equal((await request(sessionBase(sid) + "/pay", {}, 10)).data.tokens, 4.7);
  assert.equal((await request(`${base}/sessions/${sid}/text`, { answers: { 1: "injected proof" } }, 10)).status, 404);
});

test("actual KMO requests share policies and public PDF before independent student tails", async () => {
  const runs = [], scan = Buffer.from([255,216,255,224,0,16,74,70,73,70,17,23]), sentinel = "FIRST_PROVIDER_RESULT_PRIVATE_SENTINEL";
  proofSummary = sentinel;
  try {
    for (const id of [11,12]) {
      const marker = `PRIVATE_STUDENT_${id}_PROOF_TAIL`, started = await start(id), sid = started.data.session.id;
      assert.equal(started.status,200); assert.equal((await save(sid,id,{5:"Let n be an integer. " + marker})).status,200);
      if(id===12) sqlite.prepare(`INSERT INTO lab_pages(session_id,no,task,kind,mime,data,ocr,ocr_status,edited,legible,created_at)
        VALUES(?,2,'Q5','answer','image/jpeg',?,?,'done',1,'good',?)`).run(sid,scan,"Let n be an integer. Original scan diagram " + marker,timestamp);
      const before=providerBodies.length, firstUrl=providerUrls.length, graded=await settled(sessionBase(sid)+"/submit",{},id);
      assert.equal(graded.status,200); assert.equal(graded.data.session.status,"graded"); assert.equal(graded.data.session.score,7);
      const bodies=providerBodies.slice(before); assert.equal(bodies.length,2,"the two independent reviews retain exactly two provider calls");
      const prefixes=[];
      for(const [pass,body] of bodies.entries()) {
        const parts=body.contents[0].parts, pdfIndex=parts.findIndex(part=>part.inline_data?.mime_type==="application/pdf");
        assert.ok(pdfIndex>0,"fixed policy and exam context precede the public PDF");
        assert.ok(parts[0].text.includes("M1:")); assert.ok(parts[0].text.includes("not an official KMO grade"));
        assert.ok(!parts[0].text.includes("Review ONLY problem"),"the policy part does not start with dynamic exam scope");
        assert.ok(parts.slice(1,pdfIndex).some(part=>part.text?.includes("Review ONLY problem 5")));
        const adminIndex=parts.findIndex(part=>part.text?.includes("[ADMIN REVIEW REFERENCE"));
        assert.equal(adminIndex,pdfIndex+1,"the public/admin reference is before student content");
        const referenceEnd=adminIndex+1, reference=parts.slice(0,referenceEnd);
        const studentIndex=parts.findIndex(part=>part.text?.includes("[Page 1; task Q5]")); assert.ok(studentIndex>=referenceEnd);
        const tail=parts.slice(referenceEnd), text=tail.map(part=>part.text||"").join("\n");
        assert.ok(text.includes(marker)); assert.ok(!JSON.stringify(reference).includes(marker)); assert.ok(!JSON.stringify(reference).includes(tokens[id]));
        assert.ok(!JSON.stringify(body).includes(sentinel),"the independent second review never receives the first result");
        if(pass===0) assert.equal(studentIndex,referenceEnd);
        else {
          assert.equal(studentIndex,referenceEnd+1);
          assert.match(parts[referenceEnd].text,/Independently audit/);
          assert.ok(!parts.slice(0,referenceEnd).some(part=>part.text?.includes("Independently audit")),"the second-pass instruction stays after the reusable reference prefix");
        }
        if(id===12) assert.ok(tail.some(part=>part.inline_data?.mime_type==="image/jpeg"&&Buffer.from(part.inline_data.data,"base64").equals(scan)),"original student scan bytes remain in the tail");
        assert.ok(!Object.hasOwn(body,"cachedContent")); prefixes.push(reference);
      }
      assert.deepEqual(prefixes[0],prefixes[1],"both independent passes have an identical public/reference prefix");
      assert.ok(providerUrls.slice(firstUrl).every(url=>url.includes(":generateContent")||/https:\/\/www\.(kms|kmo)\.or\.kr\//.test(url)),"no explicit provider-cache creation or update endpoint is called");
      runs.push({marker,bodies,prefix:prefixes[0]});
    }
    assert.deepEqual(runs[0].prefix,runs[1].prefix,"different users selecting the same exam share the prefix through the PDF/reference");
    for(const [index,run] of runs.entries()) assert.ok(!JSON.stringify(run.bodies).includes(runs[1-index].marker),"the other user's submission is never reused");
  } finally { proofSummary=""; }
});
