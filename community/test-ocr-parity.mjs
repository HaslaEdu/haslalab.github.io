// node --test community/test-ocr-parity.mjs
// Real Worker + SQLite + loopback provider fixture server. No production requests or credentials.
// Reference: HaslaEdu/nonsul 24b8036037cb227237bd2fe75023f7b4d7472ef0, src/api/ocr.js and supabase/functions/ocr/index.ts.
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import http from "node:http";
import { DatabaseSync } from "node:sqlite";
import test from "node:test";
import worker from "./src/index.js";

const sqlite = new DatabaseSync(":memory:");
for (const name of readdirSync(new URL("./migrations/", import.meta.url)).filter(name => /^00(?:0[1-9]|1[01])_.*\.sql$/.test(name)).sort()) {
  sqlite.exec(readFileSync(new URL("./migrations/" + name, import.meta.url), "utf8"));
}
const DB = {
  prepare(sql) {
    const statement = sqlite.prepare(sql);
    const make = args => ({
      bind: (...bound) => make(bound),
      async first() { return statement.get(...args) || null; },
      async all() { return { results: statement.all(...args) }; },
      async run() { return this.executeSync(); },
      executeSync() {
        if (statement.columns().length) return { results: statement.all(...args) };
        const result = statement.run(...args);
        return { success: true, meta: { changes: result.changes, last_row_id: Number(result.lastInsertRowid) } };
      },
    });
    return make([]);
  },
  async batch(statements) {
    sqlite.exec("BEGIN");
    try { const result = statements.map(statement => statement.executeSync()); sqlite.exec("COMMIT"); return result; }
    catch (error) { sqlite.exec("ROLLBACK"); throw error; }
  },
};
globalThis.caches = { default: { async match() {}, async put() {} } };
const originalFetch = globalThis.fetch;
const png = Buffer.from("89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4890000000D49444154789C6360000002000154A24F5D0000000049454E44AE426082", "hex");
const FORMULA = String.raw`A.1: $R_0=108.2\,\Omega$\n$\frac{\alpha_i^2}{\sqrt{x}}+\int_0^1 f(t)\,dt$`;
let fixture = {}, captures = [], base, env, serial = 0;
const readFixture = () => ({ header: { task: "E1", sheet: "answer", page: 1 }, legible: "good", items: [
  { label: "A.1", kind: "value", text: "R0 = 999 (incorrect auxiliary transcription)", value: 108.2, unit: "ohm", crossed_out: false },
] });
function reset(extra = {}) {
  fixture = { upstage: { content: { markdown: FORMULA }, confidence: 0.94, modelVersion: "document-parse-fixture", usage: { pages: 1 } },
    statuses: [], read: readFixture(), geminiStatus: 200, ...extra };
  captures = [];
}
const server = http.createServer(async (request, response) => {
  try {
    const chunks = []; for await (const chunk of request) chunks.push(chunk);
    const bytes = Buffer.concat(chunks);
    if (request.url === "/upstage") {
      const incoming = new Request(base + request.url, { method: "POST", headers: request.headers, body: bytes });
      const form = await incoming.formData(), document = form.get("document");
      captures.push({ provider: "upstage", fields: Object.fromEntries([...form.entries()].filter(([key]) => key !== "document")),
        mime: document.type, filename: document.name, document: Buffer.from(await document.arrayBuffer()) });
      const status = fixture.statuses.shift() || 200;
      if (status === -1) return request.socket.destroy();
      response.statusCode = status;
      response.setHeader("Content-Type", "application/json");
      return response.end(status === 200 ? (fixture.rawResponse ?? JSON.stringify(fixture.upstage)) : JSON.stringify({ error: "fixture provider error" }));
    }
    if (request.url.includes(":generateContent")) {
      const body = JSON.parse(bytes), parts = body.contents[0].parts, prompt = parts.map(part => part.text || "").join("\n");
      captures.push({ provider: "gemini", prompt, parts });
      response.statusCode = fixture.geminiStatus;
      response.setHeader("Content-Type", "application/json");
      if (fixture.geminiStatus !== 200) return response.end('{"error":"fixture structure unavailable"}');
      const result = prompt.startsWith("[TASK: read page]") ? fixture.read : {
        items: [{ id: "A.1", found: true, page: 1, value: 108.2, unit_ok: true, score: 1, checks_met: [], rules: [], note: "fixture grounded value" }], feedback: [], review: null,
      };
      return response.end(JSON.stringify({ candidates: [{ content: { parts: [{ text: JSON.stringify(result) }] } }], usageMetadata: { promptTokenCount: 100, candidatesTokenCount: 50 } }));
    }
    response.statusCode = 404; response.end("unexpected fixture path");
  } catch (error) { response.statusCode = 500; response.end(String(error.message)); }
});
test.before(async () => {
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  base = "http://127.0.0.1:" + server.address().port;
  env = { DB, ALLOWED_ORIGINS: "http://localhost:8765", LAB_KEEP_HOURS: "off", UPSTAGE_API_KEY: "fixture-upstage-key", UPSTAGE_BASE: base + "/upstage", GEMINI_API_KEY: "fixture-gemini-key", GEMINI_BASE: base + "/gemini" };
  globalThis.fetch = (input, init) => {
    const url = typeof input === "string" ? input : input.url;
    if (!url.startsWith(base + "/")) throw new Error("External provider calls forbidden in this test");
    return originalFetch(input, init);
  };
});
test.after(async () => { globalThis.fetch = originalFetch; await new Promise(resolve => server.close(resolve)); sqlite.close(); });
const hash = async text => Buffer.from(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text))).toString("base64url");
async function session(options = {}) {
  const id = ++serial, timestamp = Math.floor(Date.now() / 1000), token = ("owner_fixture_" + id).padEnd(48, "a"), scan = ("scan_fixture_" + id).padEnd(48, "b");
  sqlite.prepare("INSERT INTO users(id,username,nickname,pw,created_at) VALUES(?,?,?,'unused',?)").run(id, "ocr" + id, "OCR " + id, timestamp);
  sqlite.prepare("INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)").run(await hash(token), id, timestamp, timestamp + 3600);
  sqlite.prepare(`INSERT INTO lab_sessions(id,user_id,exam_key,comp,year,tasks,lang,started_at,ended_at,scan_until,upload_hash,status,charged,created_at,sources)
    VALUES(?,?,'ipho2024','ipho',2024,'["E1"]','ko',?,?,?,?,?,?,?,?)`).run(id, id, timestamp - 18000, timestamp - 10, timestamp + 3600, await hash(scan), options.status || "scanning", options.charged ?? 1, timestamp, JSON.stringify({ E1: { sol: "IPhO_2024_S1.pdf" } }));
  return { id, token, scan };
}
async function api(path, options = {}, settings = env) {
  const response = await worker.fetch(new Request("http://worker.local/api" + path, options), settings);
  return { status: response.status, data: await response.json() };
}
async function recognize(s, mode = "math", settings = env) {
  const form = new FormData(); form.append("image", new File([png], "answer.png", { type: "image/png" }));
  return api("/ocr?mode=" + mode, { method: "POST", headers: { Authorization: "Bearer " + s.token }, body: form }, settings);
}
const upload = (s, image = png, scan = s.scan, settings = env) => api(`/lab/up/${s.id}/pages?task=E1&kind=answer`, {
  method: "PUT", headers: { "Content-Type": "image/png", "X-Lab-Token": scan }, body: image,
}, settings);
const getSession = s => api("/lab/sessions/" + s.id, { headers: { Authorization: "Bearer " + s.token } });

test("math request matches Nonsul model/force/Markdown/coordinates and preserves original image bytes", async () => {
  reset(); const s = await session(), result = await recognize(s);
  assert.equal(result.status, 200);
  assert.deepEqual(captures[0].fields, { model: "document-parse", ocr: "force", output_formats: '["markdown"]', coordinates: "true" });
  assert.ok(captures[0].document.equals(png), "no region is masked, cropped or removed on the server");
  assert.equal(captures[0].mime, "image/png");
  assert.equal(result.data.text, FORMULA);
  assert.equal(result.data.engine, "upstage-document-parse");
  assert.equal(result.data.format, "markdown-latex");
  assert.equal(result.data.modelVersion, "document-parse-fixture");
  assert.ok(result.data.equations.some(value => value.includes("\\frac")));
});

test("element HTML/text/equation fallback and averaged confidence match source interpretation", async () => {
  reset({ upstage: { model_version: "fixture-v2", elements: [
    { category: "paragraph", content: { text: "원문 <기호>" }, confidence: 0.9 },
    { category: "equation", content: { html: "<p>\\(x_i^2 &lt; \\frac{a}{b}\\)</p>", text: "x flattened" }, confidence: 0.5 },
  ] } });
  const result = await recognize(await session());
  assert.equal(result.data.text, "원문 <기호>\n\n\\(x_i^2 < \\frac{a}{b}\\)");
  assert.deepEqual(result.data.equations, ["\\(x_i^2 < \\frac{a}{b}\\)\n"]);
  assert.equal(result.data.confidence, 0.7);
  assert.equal(result.data.modelVersion, "fixture-v2");
});

test("text OCR reconstructs CJK word coordinates and retains low-confidence words", async () => {
  const word = (text, x0, x1, confidence) => ({ text, confidence, boundingBox: { vertices: [{ x: x0, y: 0 }, { x: x1, y: 0 }, { x: x1, y: 10 }, { x: x0, y: 10 }] } });
  reset({ upstage: { text: "수학문제", confidence: 0.8, modelVersion: "ocr-fixture", pages: [{ words: [word("수학", 0, 20, 0.95), word("문제", 20, 40, 0.4)] }] } });
  const result = await recognize(await session(), "text");
  assert.deepEqual(captures[0].fields, { model: "ocr" });
  assert.equal(result.data.text, "수학문제");
  assert.deepEqual(result.data.low, ["문제"]);
  assert.equal(result.data.words, 2); assert.equal(result.data.lines, 1);
  assert.equal(result.data.format, "plain-text");
});

test("rich equation elements take precedence over a flattened top-level plain-text fallback", async () => {
  reset({ upstage: { content: { text: "Let x = a / b (flattened)" }, elements: [
    { category: "paragraph", content: { text: "Let" } },
    { category: "equation", content: { html: "<p>\\(x_i^2=\\frac{a_i}{b^2}\\)</p>", text: "x i2 = ai / b2" } },
  ] } });
  const result = await recognize(await session());
  assert.equal(result.data.text, "Let\n\n\\(x_i^2=\\frac{a_i}{b^2}\\)");
  assert.ok(!result.data.text.includes("flattened"));
});

test("incomplete coordinates do not discard text the provider successfully read", async () => {
  reset({ upstage: { text: "This complete original must not disappear because only one word has coordinates.", pages: [{ words: [
    { text: "This", boundingBox: { vertices: [{ x: 0, y: 0 }, { x: 20, y: 10 }] } },
  ] }] } });
  const result = await recognize(await session(), "text");
  assert.equal(result.data.text, fixture.upstage.text);
});

test("429 and 5xx retry with the same complete document; metrics record each attempt", async () => {
  reset({ statuses: [429, 503, 200] }); const s = await session(), result = await upload(s);
  assert.equal(result.status, 200); assert.equal(result.data.ocr_status, "done");
  const requests = captures.filter(row => row.provider === "upstage");
  assert.equal(requests.length, 3); assert.ok(requests.every(row => row.document.equals(png)));
  const metrics = sqlite.prepare("SELECT ok FROM lab_calls WHERE session_id=? AND provider='upstage' ORDER BY id").all(s.id);
  assert.deepEqual(metrics.map(row => row.ok), [0, 0, 1]);
});

test("network interruption is retryable, while provider authorization failures are not", async () => {
  reset({ statuses: [-1, 200] });
  assert.equal((await recognize(await session())).status, 200);
  assert.equal(captures.filter(row => row.provider === "upstage").length, 2);
  reset({ statuses: [401] }); const failed = await recognize(await session());
  assert.equal(failed.status, 502); assert.equal(failed.data.error, "ocr_failed");
  assert.equal(captures.length, 1);
  assert.ok(!JSON.stringify(failed).includes("fixture-upstage-key"));
});

test("malformed or oversized provider responses fail clearly without leaking provider bodies", async () => {
  reset({ rawResponse: "<not-json>" });
  assert.equal((await recognize(await session())).data.error, "ocr_bad_response");
  reset({ upstage: { text: "x".repeat(2 * 1024 * 1024) } });
  assert.equal((await recognize(await session())).data.error, "ocr_response_too_large");
  assert.equal(captures.length, 1);
});

test("scan text and metadata use full Upstage original, never auxiliary Gemini transcription", async () => {
  const original = FORMULA + "\n" + "long original line\n".repeat(1000) + String.raw`END: $x_{99}=\frac{a}{b}$`;
  reset({ upstage: { content: { markdown: original }, confidence: 0.72, model: "fixture-document", usage: { pages: 1 } } });
  const s = await session(), uploaded = await upload(s);
  assert.equal(uploaded.data.ocr_status, "done"); assert.equal(uploaded.data.chars, original.length);
  const page = (await getSession(s)).data.session.pages[0];
  assert.equal(page.text, original); assert.equal(page.read.ocr.text, original);
  assert.ok(!page.text.includes("999 (incorrect"));
  assert.equal(page.read.ocr.review_required, true);
  assert.equal(page.read.ocr.modelVersion, "fixture-document");
  assert.ok(captures.find(row => row.provider === "gemini").prompt.includes(original), "structure input has the entire original past 12,000 chars");
  const stored = sqlite.prepare("SELECT ocr,text,read FROM lab_pages WHERE id=?").get(uploaded.data.id);
  assert.equal(stored.ocr, original); assert.equal(stored.text, null);
  assert.ok(!JSON.parse(stored.read).ocr.text, "database does not store the same original a third time");
});

test("successful OCR survives unavailable auxiliary structure; configured OCR failures do not fall back silently", async () => {
  reset({ geminiStatus: 503 }); const s = await session(), uploaded = await upload(s);
  assert.equal(uploaded.data.ocr_status, "done");
  const page = (await getSession(s)).data.session.pages[0];
  assert.equal(page.text, FORMULA); assert.equal(page.read.structure_status, "failed");
  reset({ statuses: [403] }); const failedSession = await session(), failed = await upload(failedSession);
  assert.equal(failed.status, 200); assert.equal(failed.data.ocr_status, "failed");
  assert.ok(!captures.some(row => row.provider === "gemini"));
  assert.equal(sqlite.prepare("SELECT length(data) n FROM lab_pages WHERE id=?").get(failed.data.id).n, png.length);
});

test("D1 row budget preserves the photo and returns an explicit failure instead of truncating OCR", async () => {
  reset({ upstage: { content: { markdown: "x".repeat(100000) }, confidence: 0.99 } });
  const image = Buffer.alloc(1900000); png.copy(image);
  const s = await session(), uploaded = await upload(s, image);
  assert.equal(uploaded.status, 200); assert.equal(uploaded.data.ocr_status, "failed");
  assert.equal(uploaded.data.ocr_error, "ocr_storage_limit");
  const stored = sqlite.prepare("SELECT data,ocr,text,read FROM lab_pages WHERE id=?").get(uploaded.data.id);
  assert.ok(Buffer.from(stored.data).equals(image)); assert.equal(stored.ocr, null); assert.equal(stored.text, null);
  assert.equal(JSON.parse(stored.read).ocr.error, "ocr_storage_limit");
  assert.ok(stored.data.length + Buffer.byteLength(stored.read) < 2000000);
  const computer = await getSession(s);
  assert.equal(computer.data.session.pages[0].ocr_error, "ocr_storage_limit");
  const phone = await api(`/lab/up/${s.id}`, { headers: { "X-Lab-Token": s.scan } });
  assert.equal(phone.data.pages[0].ocr_error, "ocr_storage_limit");
});

test("real grading input retains unabridged original equations and existing numeric evidence rules", async () => {
  const original = FORMULA + "\n" + "evidence\n".repeat(1700) + String.raw`FINAL: $u_n=\frac{1}{n^2}$`;
  reset({ upstage: { content: { markdown: original }, confidence: 0.94 } });
  const s = await session(); await upload(s);
  sqlite.prepare("INSERT OR REPLACE INTO lab_schemes(exam_key,task,source,scheme,model,created_at) VALUES('ipho2024','E1','IPhO_2024_S1.pdf',?,'fixture',?)")
    .run(JSON.stringify({ points: 1, items: [{ id: "A.1", points: 1, type: "value", sheet: "answer", what: "R0", unit: "ohm", full_min: 108, full_max: 109, partial: [] }] }), Math.floor(Date.now() / 1000));
  const result = await api(`/lab/sessions/${s.id}/submit`, { method: "POST", headers: { Authorization: "Bearer " + s.token, "Content-Type": "application/json" }, body: "{}" });
  assert.equal(result.status, 200); assert.equal(result.data.session.status, "graded");
  const grading = captures.find(row => row.provider === "gemini" && row.prompt.startsWith("[TASK: grade]"));
  assert.ok(grading.prompt.includes(original));
  assert.ok(grading.prompt.includes("Upstage original transcript"));
  assert.ok(grading.prompt.includes("auxiliary indexes"));
  assert.equal(result.data.session.score, 1, "existing range/unit/answer-sheet checks still determine the mark");
});

test("auth, QR token, payment, upload limit and read-only exam transcript checks remain enforced", async () => {
  reset(); const s = await session();
  assert.equal((await upload(s, png, "invalid-token")).status, 403);
  const form = new FormData(); form.append("image", new Blob([png]));
  assert.equal((await api("/ocr?mode=math", { method: "POST", body: form })).status, 401);
  assert.equal((await upload(s, Buffer.alloc(1900001))).status, 415);
  const tooLarge = Buffer.alloc(1900001); png.copy(tooLarge);
  assert.equal((await upload(s, tooLarge)).status, 413);
  const unpaid = await session({ charged: 0 }), saved = await upload(unpaid);
  assert.equal(saved.data.ocr_status, "unpaid"); assert.equal(captures.length, 0);
  const paid = await upload(s);
  const patch = await api(`/lab/sessions/${s.id}/pages/${paid.data.id}`, { method: "PATCH", headers: { Authorization: "Bearer " + s.token, "Content-Type": "application/json" }, body: JSON.stringify({ text: "changed answer" }) });
  assert.equal(patch.status, 400); assert.equal(patch.data.error, "read_only");
  sqlite.prepare("UPDATE lab_sessions SET status='ended',upload_hash='void:'||upload_hash WHERE id=?").run(s.id);
  assert.equal((await upload(s)).status, 410);
});

test("text-grader fallback explicitly defers overlong answers instead of silently discarding the tail", async () => {
  const original = FORMULA + "\n" + "x".repeat(61000) + " END_MUST_NEVER_DISAPPEAR";
  reset({ upstage: { content: { markdown: original }, confidence: 0.94 } });
  const s = await session(), fallback = { ...env, GEMINI_API_KEY: "", OPENAI_API_KEY: "fixture-openai-unused" };
  assert.equal((await upload(s, png, s.scan, fallback)).data.ocr_status, "done");
  sqlite.prepare("INSERT OR REPLACE INTO lab_rubrics(exam_key,task,points,rubric,reference,updated_at) VALUES('ipho2024','E1',1,?,'fixture',?)")
    .run(JSON.stringify([{ id: "A.1", max: 1, name: "value", requirement: "grounded value" }]), Math.floor(Date.now() / 1000));
  const result = await api(`/lab/sessions/${s.id}/submit`, { method: "POST", headers: { Authorization: "Bearer " + s.token, "Content-Type": "application/json" }, body: "{}" }, fallback);
  assert.equal(result.status, 200); assert.equal(result.data.session.status, "pending");
  assert.equal(result.data.session.detail.tasks.E1.why, "answer_too_long");
  assert.equal(result.data.session.pages[0].text, original);
  assert.ok(captures.every(row => row.provider === "upstage"), "no truncated answer is sent to a text grader");
});

test("oversized structure on grading retry preserves a previously stored complete OCR original", async () => {
  const original = "original OCR that must survive retries\n".padEnd(80000, "x"), image = Buffer.alloc(1900000); png.copy(image);
  reset({ upstage: { content: { markdown: original }, confidence: 0.94 }, geminiStatus: 503 });
  const s = await session(), uploaded = await upload(s, image);
  assert.equal(uploaded.data.ocr_status, "done");
  const before = sqlite.prepare("SELECT ocr,text,read,data FROM lab_pages WHERE id=?").get(uploaded.data.id);
  assert.equal(before.ocr, original); assert.equal(JSON.parse(before.read).structure_status, "failed");
  sqlite.prepare("INSERT OR REPLACE INTO lab_rubrics(exam_key,task,points,rubric,reference,updated_at) VALUES('ipho2024','E1',1,?,'fixture',?)")
    .run(JSON.stringify([{ id: "A.1", max: 1, name: "value", requirement: "grounded value" }]), Math.floor(Date.now() / 1000));
  fixture.geminiStatus = 200;
  fixture.read = readFixture(); fixture.read.items[0].text = "auxiliary structure".padEnd(20000, "y");
  const result = await api(`/lab/sessions/${s.id}/submit`, { method: "POST", headers: { Authorization: "Bearer " + s.token, "Content-Type": "application/json" }, body: "{}" });
  assert.equal(result.status, 200); assert.equal(result.data.session.status, "error");
  assert.equal(result.data.session.detail.tasks.E1.why, "ocr_storage_limit");
  const after = sqlite.prepare("SELECT ocr,text,read,data FROM lab_pages WHERE id=?").get(uploaded.data.id);
  assert.equal(after.ocr, before.ocr); assert.equal(after.text, before.text); assert.equal(after.read, before.read);
  assert.ok(Buffer.from(after.data).equals(Buffer.from(before.data)));
  assert.ok(!captures.some(row => row.provider === "gemini" && row.prompt.startsWith("[TASK: grade]")), "failed structure storage cannot proceed to grading with lost evidence");
});

test("proof review scan stores the same original and still requires the student's explicit confirmation", async () => {
  reset(); const owner = await session();
  sqlite.prepare("UPDATE lab_sessions SET status='ended' WHERE id=?").run(owner.id);
  const headers = { Authorization: "Bearer " + owner.token, "Content-Type": "application/json" };
  const started = await api("/lab/contest/start", { method: "POST", headers, body: JSON.stringify({ examId: "kmo-2025-T2-s2", purpose: "review", runId: "ocr-parity-proof" }) });
  assert.equal(started.status, 200);
  const sid = started.data.session.id, scan = started.data.token;
  const saved = await api(`/lab/up/${sid}/pages?task=Q5&kind=answer`, { method: "PUT", headers: { "Content-Type": "image/png", "X-Lab-Token": scan }, body: png });
  assert.equal(saved.data.ocr_status, "unpaid"); assert.equal(captures.length, 0);
  assert.equal((await api(`/lab/sessions/${sid}/pay`, { method: "POST", headers, body: "{}" })).status, 200);
  const read = await api(`/lab/contest/sessions/${sid}/read`, { method: "POST", headers, body: "{}" });
  assert.equal(read.status, 200);
  const page = read.data.session.pages[0];
  assert.equal(page.task, "Q5", "auxiliary header cannot override the student's chosen proof task");
  assert.equal(page.text, FORMULA); assert.equal(page.read.ocr.text, FORMULA); assert.equal(page.confirmed, false);
  assert.equal(sqlite.prepare("SELECT text FROM lab_pages WHERE id=?").get(page.id).text, null);
  const submit = await api(`/lab/sessions/${sid}/submit`, { method: "POST", headers, body: "{}" });
  assert.equal(submit.status, 409); assert.equal(submit.data.error, "needs_confirmation");
  const confirmed = await api(`/lab/contest/sessions/${sid}/pages/${page.id}/confirm`, { method: "POST", headers, body: JSON.stringify({ task: "Q5", text: FORMULA }) });
  assert.equal(confirmed.status, 200); assert.equal(confirmed.data.session.pages[0].confirmed, true);
  assert.equal(confirmed.data.session.pages[0].text, FORMULA);
  assert.equal(sqlite.prepare("SELECT text FROM lab_pages WHERE id=?").get(page.id).text, null, "confirming an unchanged original does not duplicate it in D1");
  const largeImage = Buffer.alloc(1900000); png.copy(largeImage);
  fixture.upstage = { content: { markdown: "original".padEnd(60000, "x") }, confidence: 0.94 };
  const large = await api(`/lab/up/${sid}/pages?task=Q5&kind=answer`, { method: "PUT", headers: { "Content-Type": "image/png", "X-Lab-Token": scan }, body: largeImage });
  assert.equal(large.data.ocr_status, "done");
  const overBudget = await api(`/lab/contest/sessions/${sid}/pages/${large.data.id}/confirm`, { method: "POST", headers,
    body: JSON.stringify({ task: "Q5", text: "a corrected original".padEnd(50000, "y") }) });
  assert.equal(overBudget.status, 413); assert.equal(overBudget.data.error, "ocr_storage_limit");
  const preserved = sqlite.prepare("SELECT ocr,text,data,edited FROM lab_pages WHERE id=?").get(large.data.id);
  assert.equal(preserved.ocr, fixture.upstage.content.markdown); assert.equal(preserved.text, null); assert.equal(preserved.edited, 0);
  assert.ok(Buffer.from(preserved.data).equals(largeImage));
});
