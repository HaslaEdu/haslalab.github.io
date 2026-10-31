// node --test community/test-ocr-parity.mjs
// Real Worker + SQLite + loopback provider fixture server. No production requests or credentials.
// Selected visual providers must retain original image/text evidence without hidden OCR fallbacks.
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import http from "node:http";
import { DatabaseSync } from "node:sqlite";
import test from "node:test";
import worker from "./src/index.js";
import { REG_VERSION } from "./src/grading-rules.js";
import { MODEL_TEST_EXAMS } from "./src/model-test-catalog.js";
import { ensureWeeklyContent } from "./src/weekly-content.js";

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
const messages=[];
async function drainQueue(settings=env){
  while(messages.length){
    const body=messages.shift();
    sqlite.prepare("UPDATE lab_jobs SET available_at=0 WHERE id=?").run(body.jobId);
    await worker.queue({messages:[{body,ack(){},retry(){messages.push(body);}}]},settings);
  }
}
const readFixture = () => ({ text: FORMULA, confidence: 0.94, header: { task: "E1", sheet: "answer", page: 1 }, legible: "good", items: [
  { label: "A.1", kind: "value", text: "R0 = 999 (incorrect auxiliary transcription)", value: 108.2, unit: "ohm", crossed_out: false },
] });
function reset(extra = {}) {
  fixture = { transcript: { text: FORMULA, confidence: 0.94, legible: true, uncertainties: [], visuals: [] },
    statuses: [], read: readFixture(), geminiStatus: 200, ...extra };
  captures = [];
}
const server = http.createServer(async (request, response) => {
  try {
    const chunks = []; for await (const chunk of request) chunks.push(chunk);
    const bytes = Buffer.concat(chunks);
    if (request.url.startsWith("/pdf/")) {response.setHeader("Content-Type","application/pdf");return response.end("%PDF-1.4 fixture public source "+decodeURIComponent(request.url));}
    if (request.url.includes(":generateContent") || request.url.endsWith("/chat/completions")) {
      const body = JSON.parse(bytes), provider = request.url.includes(":generateContent") ? "gemini" : "deepseek";
      const parts = provider === "gemini" ? body.contents[0].parts : body.messages[1].content.map(part => part.type === "text" ? {text:part.text} :
        {inline_data:{mime_type:part.image_url.url.split(";")[0].slice(5),data:part.image_url.url.split(",")[1]}});
      const prompt = parts.map(part => part.text || "").join("\n");
      const schema = provider === "gemini" ? body.generationConfig.responseSchema : JSON.parse(body.messages[0].content.split("JSON schema:\n")[1]);
      captures.push({ provider, url: request.url, body, prompt, parts });
      response.statusCode = fixture.statuses.shift() || fixture.geminiStatus;
      if (response.statusCode === -1) return request.socket.destroy();
      response.setHeader("Content-Type", "application/json");
      if (response.statusCode !== 200) return response.end('{"error":"PRIVATE_UPSTREAM_ERROR"}');
      if (fixture.rawResponse !== undefined) return response.end(fixture.rawResponse);
      const result = schema.properties?.uncertainties ? fixture.transcript : prompt.startsWith("[TASK: read page]") ? fixture.read : {
        items: [{ id: "A.1", found: true, page: 1, value: 108.2, unit_ok: true, score: 1, checks_met: [], rules: [], note: "fixture grounded value" }], feedback: [], review: null,
      };
      if (provider === "deepseek") return response.end(JSON.stringify({model:"deepseek-flash",choices:[{finish_reason:"stop",message:{content:fixture.geminiText ?? JSON.stringify(result)}}],
        usage:{prompt_tokens:100,completion_tokens:50,prompt_cache_hit_tokens:40,prompt_cache_miss_tokens:60}}));
      return response.end(JSON.stringify({ candidates: [{ content: { parts: [{ text: fixture.geminiText ?? JSON.stringify(result) }] } }],
        ...(fixture.geminiModel ? { modelVersion: fixture.geminiModel } : {}), usageMetadata: fixture.geminiUsage || { promptTokenCount: 100, candidatesTokenCount: 50 } }));
    }
    response.statusCode = 404; response.end("unexpected fixture path");
  } catch (error) { response.statusCode = 500; response.end(String(error.message)); }
});
test.before(async () => {
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  base = "http://127.0.0.1:" + server.address().port;
  env = { DB, LAB_JOBS:{async sendBatch(items){messages.push(...items.map(item=>item.body));}}, ALLOWED_ORIGINS: "http://localhost:8765", LAB_KEEP_HOURS: "off", GEMINI_API_KEY: "fixture-gemini-key", GEMINI_BASE: base + "/gemini", LAB_PDF_BASE:base+"/pdf/", DEEPSEEK_API_KEY:"fixture-deepseek-key", DEEPSEEK_BASE:base+"/deepseek" };
  await ensureWeeklyContent(DB,DB);
  sqlite.prepare("INSERT INTO problems(id,week,kind,title_ko,title_en,body_ko,body_en,opens_at,closes_at,created_at) VALUES(900001,'2099-01','essay','Fixture','Fixture','Fixture','Fixture',0,9999999999,0)").run();
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
  const comp = options.comp || "ipho", year = options.year || 2024, task = options.task || "E1", examKey = comp + year;
  const canonical=MODEL_TEST_EXAMS.find(e=>e.comp===comp&&String(e.year)===String(year)&&e.task===task);
  const sol = canonical?.solution || `IPhO_${year}_S1.pdf`, mark=canonical?.mark||"", sources = { _provider: options.provider || "gemini", [task]: { sol, ...(options.theory ? { kind: "theory" } : {}) } };
  sqlite.prepare("INSERT INTO users(id,username,nickname,pw,created_at) VALUES(?,?,?,'unused',?)").run(id, "ocr" + id, "OCR " + id, timestamp);
  sqlite.prepare("INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)").run(await hash(token), id, timestamp, timestamp + 3600);
  sqlite.prepare(`INSERT INTO lab_sessions(id,user_id,exam_key,comp,year,tasks,lang,started_at,ended_at,scan_until,upload_hash,status,charged,created_at,sources)
    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`).run(id, id, examKey, comp, year, JSON.stringify([task]), options.lang || "ko", timestamp - 18000, timestamp - 10, timestamp + 3600, await hash(scan), options.status || "scanning", options.charged ?? 1, timestamp, JSON.stringify(sources));
  return { id, token, scan, task, examKey, sol, mark };
}
async function api(path, options = {}, settings = env) {
  const response = await worker.fetch(new Request("http://worker.local/api" + path, options), settings);
  const out={status:response.status,data:await response.json()};
  // This provider-parity fixture explicitly drains the test broker; HTTP queue latency is covered separately.
  if(out.status===200&&options.method==='POST'&&(/\/submit$/.test(path)||/\/read$/.test(path))&&out.data.queued){
    await drainQueue(settings);
    return api('/lab/sessions/'+out.data.session.id,{headers:options.headers},settings);
  }
  return out;
}
async function recognize(s, mode = "math", settings = env, provider = "gemini") {
  const form = new FormData(); form.append("image", new File([png], "answer.png", { type: "image/png" }));
  return api("/ocr?mode=" + mode + "&problem_id=900001&provider=" + provider, { method: "POST", headers: { Authorization: "Bearer " + s.token }, body: form }, settings);
}
const upload = async(s,image=png,scan=s.scan,settings=env)=>{
  const out=await api(`/lab/up/${s.id}/pages?task=${s.task || 'E1'}&kind=answer`,{method:'PUT',headers:{'Content-Type':'image/png','X-Lab-Token':scan},body:image},settings);
  if(out.status===200&&out.data.queued){
    await drainQueue(settings);const page=(await api('/lab/sessions/'+s.id,{headers:{Authorization:'Bearer '+s.token}},settings)).data.session.pages.find(p=>p.id===out.data.id);
    out.data={...out.data,ocr_status:page.ocr_status,ocr_error:page.ocr_error,chars:page.text.length};
  }
  return out;
};
const getSession = s => api("/lab/sessions/" + s.id, { headers: { Authorization: "Bearer " + s.token } });

test("selected visual OCR preserves complete original images, LaTeX and CJK for both providers", async () => {
  for (const provider of ["gemini","deepseek"]) {
    const original=FORMULA+"\n수학문제 漢字 untouched <symbol>";
    reset({transcript:{text:original,confidence:0.72,legible:true,uncertainties:["문제"],visuals:[]}});
    const result=await recognize(await session(),"math",env,provider);
    assert.equal(result.status,200);assert.equal(result.data.engine,provider);assert.equal(result.data.text,original);
    assert.deepEqual(result.data.low,["문제"]);assert.equal(result.data.confidence,0.72);assert.equal(result.data.format,"markdown-latex");
    assert.equal(captures.length,1);assert.equal(captures[0].provider,provider);
    const images=captures[0].parts.filter(part=>part.inline_data);
    assert.equal(images.length,1);assert.equal(images[0].inline_data.mime_type,"image/png");
    assert.ok(Buffer.from(images[0].inline_data.data,"base64").equals(png),"no cropping, whitening or text-only substitution");
    assert.ok(!JSON.stringify(captures[0].body).includes('"cachedContent"'));
  }
});

test("visual-only graphical evidence remains legible without invented OCR text", async () => {
  reset({transcript:{text:"",legible:true,confidence:0.97,uncertainties:[],visuals:[{page:1,kind:"direction",description:"A visible handwritten rightward arrow",box:[0.1,0.1,0.8,0.8]}]}});
  const result=await recognize(await session());assert.equal(result.status,200);assert.equal(result.data.text,"");
  assert.equal(result.data.visuals[0].kind,"direction");assert.equal(captures.length,1);
});

test("selected-provider failures never silently switch provider or leak upstream bodies", async () => {
  for(const [status,error] of [[401,"vision_provider_auth"],[429,"vision_provider_rate_limited"],[503,"vision_provider_failed"]]) {
    reset({statuses:[status]});const result=await recognize(await session());assert.equal(result.status,502);assert.equal(result.data.error,error);
    assert.equal(captures.length,1);assert.equal(captures[0].provider,"gemini");
    assert.ok(!JSON.stringify(result).includes("PRIVATE_UPSTREAM_ERROR"));assert.ok(!JSON.stringify(result).includes("fixture-gemini-key"));
  }
  reset();const result=await recognize(await session(),"math",{...env,GEMINI_API_KEY:""});
  assert.equal(result.status,503);assert.equal(result.data.error,"provider_unavailable");assert.equal(captures.length,0);
});

test("malformed, oversized and structurally invalid provider payloads fail within byte bounds", async () => {
  for(const rawResponse of ["<PRIVATE_NOT_JSON>","x".repeat(2*1024*1024+1)]) {
    reset({rawResponse});const result=await recognize(await session());assert.equal(result.status,502);assert.equal(result.data.error,"vision_invalid_response");
    assert.equal(captures.length,1);assert.ok(!JSON.stringify(result).includes("PRIVATE_NOT_JSON"));
  }
  reset({transcript:{text:"x".repeat(160001),legible:true,uncertainties:[],visuals:[]}});
  assert.equal((await recognize(await session())).data.error,"vision_response_schema");
});

test("scan text and metadata preserve the complete selected-provider transcription beside its index", async () => {
  const original=FORMULA+"\n"+"long original line\n".repeat(1000)+String.raw`END: $x_{99}=\frac{a}{b}$`;
  reset({read:{...readFixture(),text:original,confidence:0.72},geminiModel:"gemini-fixture-version"});
  const s=await session(),uploaded=await upload(s);assert.equal(uploaded.data.ocr_status,"done");assert.equal(uploaded.data.chars,original.length);
  const page=(await getSession(s)).data.session.pages[0];assert.equal(page.text,original);assert.equal(page.read.ocr.text,original);
  assert.ok(!page.text.includes("999 (incorrect"));assert.equal(page.read.ocr.review_required,true);assert.equal(page.read.ocr.engine,"gemini");
  assert.equal(page.read.ocr.model,"gemini:gemini-fixture-version");assert.equal(captures.length,1,"one selected model reads text and image evidence together");
  const stored=sqlite.prepare("SELECT ocr,text,read FROM lab_pages WHERE id=?").get(uploaded.data.id);
  assert.equal(stored.ocr,original);assert.equal(stored.text,null);assert.ok(!JSON.parse(stored.read).ocr.text,"do not duplicate the original in metadata");
});

test("failed selected OCR preserves original image for retry without fabricated fallback text", async () => {
  reset({geminiStatus:403});const s=await session(),uploaded=await upload(s);
  assert.equal(uploaded.status,200);assert.equal(uploaded.data.ocr_status,"failed");assert.equal(captures.length,4,"the queue records its bounded retry attempts");
  assert.ok(captures.every(call=>call.provider==="gemini"));
  const stored=sqlite.prepare("SELECT data,ocr,text FROM lab_pages WHERE id=?").get(uploaded.data.id);
  assert.ok(Buffer.from(stored.data).equals(png));assert.equal(stored.ocr,null);assert.equal(stored.text,null);
});

test("D1 row budget preserves the photo and returns an explicit failure instead of truncating OCR", async () => {
  reset({ read:{...readFixture(),text:"x".repeat(100000)} });
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
  reset({ read: {...readFixture(),text:original} });
  const s = await session(); await upload(s);
  sqlite.prepare("INSERT OR REPLACE INTO lab_schemes(exam_key,task,source,scheme,model,created_at) VALUES('ipho2024','E1',?,?,'fixture',?)")
    .run(["gemini","gemini-3.5-flash-lite",REG_VERSION,"IPhO_2024_S1.pdf", ""].join(":"),JSON.stringify({ points: 1, items: [{ id: "A.1", points: 1, type: "value", sheet: "answer", what: "R0", unit: "ohm", full_min: 108, full_max: 109, partial: [] }] }), Math.floor(Date.now() / 1000));
  const result = await api(`/lab/sessions/${s.id}/submit`, { method: "POST", headers: { Authorization: "Bearer " + s.token, "Content-Type": "application/json" }, body: JSON.stringify({provider:"gemini"}) });
  assert.equal(result.status, 200); assert.equal(result.data.session.status, "graded");
  const grading = captures.find(row => row.provider === "gemini" && row.prompt.startsWith("[TASK: grade]"));
  assert.ok(grading.prompt.includes(original));
  assert.ok(grading.prompt.includes("original transcript"));
  assert.ok(grading.prompt.includes("auxiliary indexes"));
  assert.equal(result.data.session.score, 1, "existing range/unit/answer-sheet checks still determine the mark");
});

test("actual Gemini grading bodies share the regulation/output/evidence prefix across exams and students", async () => {
  const runs = [];
  for (const scope of [{ comp: "ipho", year: 2024, task: "E1", lang: "ko" },
    { comp: "apho", year: 2025, task: "E1", lang: "en" }, { comp: "ipho", year: 2026, task: "T2", theory: true, lang: "ko" }]) {
    const s = await session(scope), marker = `PRIVATE_STUDENT_${s.id}_FINAL_ANSWER`, original = FORMULA + "\n" + marker;
    const image = Buffer.concat([png, Buffer.from(marker)]), reading = readFixture(); reading.header.task = scope.task;
    reset({ read: {...reading,text:original},
      geminiModel: "gemini-2.5-flash", geminiUsage: { promptTokenCount: 1000, candidatesTokenCount: 80, thoughtsTokenCount: 20, cachedContentTokenCount: 400 } });
    assert.equal((await upload(s, image)).data.ocr_status, "done");
    sqlite.prepare("INSERT OR REPLACE INTO lab_schemes(exam_key,task,source,scheme,model,created_at) VALUES(?,?,?,?,'fixture',?)")
      .run(s.examKey, scope.task, ["gemini","gemini-3.5-flash-lite",REG_VERSION,s.sol,s.mark].join(":"), JSON.stringify({ points: 1, items: [{ id: "A.1", points: 1, type: "value", sheet: "answer", what: "R0", unit: "ohm", full_min: 108, full_max: 109, partial: [] }] }), Math.floor(Date.now() / 1000));
    const result = await api(`/lab/sessions/${s.id}/submit`, { method: "POST", headers: { Authorization: "Bearer " + s.token, "Content-Type": "application/json" }, body: JSON.stringify({ lang: scope.lang }) });
    assert.equal(result.status, 200); assert.equal(result.data.session.status, "graded"); assert.equal(result.data.session.score, 1);
    const grading = captures.find(row => row.provider === "gemini" && row.prompt.startsWith("[TASK: grade]")); assert.ok(grading);
    const head = grading.parts[0].text, boundary = head.indexOf("\n[Exam context]\n"); assert.ok(boundary > 0);
    const prefix = head.slice(0, boundary), tail = head.slice(boundary);
    for (const policy of ["Grading regulation", "R1.", "R10.", "For every scheme item", "primary evidence", "never changes a mark"]) assert.ok(prefix.includes(policy), policy);
    assert.ok(!prefix.includes(marker)); assert.ok(!prefix.includes(s.token)); assert.ok(!prefix.includes(original)); assert.ok(!prefix.includes("<<SCHEME>>"));
    assert.ok(tail.includes(scope.comp.toUpperCase() + " " + scope.year)); assert.ok(tail.includes(scope.task)); assert.ok(tail.includes(scope.lang === "en" ? "English" : "Korean"));
    assert.ok(grading.prompt.includes(original), "the complete original remains in the student tail");
    assert.ok(grading.parts.some(part => part.inline_data?.mime_type === "image/png" && Buffer.from(part.inline_data.data, "base64").equals(image)), "the original scan bytes remain attached");
    assert.ok(!JSON.stringify(grading.body).includes('"cachedContent"')); assert.match(grading.url, /:generateContent$/);
    const metered = sqlite.prepare("SELECT model,in_tok,out_tok,cached_tok,usd FROM lab_calls WHERE session_id=? AND step='grade'").get(s.id);
    assert.equal(metered.model, "gemini-2.5-flash"); assert.equal(metered.in_tok, 1000); assert.equal(metered.out_tok, 100); assert.equal(metered.cached_tok, 400); assert.ok(metered.usd > 0);
    runs.push({ prefix, core:prefix.split("[Review —")[0], original, prompt: grading.prompt });
  }
  assert.equal(runs[0].prefix, runs[1].prefix,"same competition family and paper kind share the complete fixed rules"); assert.equal(runs[1].core, runs[2].core,"the common role/evidence/output policy precedes paper-kind rules");
  assert.ok(runs[0].prefix.length > 1000, "compare the substantive common policy, not only a task tag");
  for (let i = 0; i < runs.length; i++) for (let j = 0; j < runs.length; j++) if (i !== j) assert.ok(!runs[i].prompt.includes(runs[j].original), "another student's tail never leaks into a reused prefix");
});

test("real Worker metering retains selected-model overrides and bills known-usage parse failures exactly once", async () => {
  const selectedModel = "gemini-3.5-flash-lite", settings = { ...env, LAB_PRICES: JSON.stringify({ [selectedModel]: [2,5,0.25] }) };
  const expected = ((1000-400)*2 + 400*0.25 + 100*5)/1e6;
  for(const invalid of [false,true]) {
    reset({ geminiModel: "gemini-2.5-flash", geminiUsage: { promptTokenCount:1000,candidatesTokenCount:80,thoughtsTokenCount:20,cachedContentTokenCount:400 },
      ...(invalid ? { geminiText:"not JSON PRIVATE_UPSTREAM_PAYLOAD" } : {}) });
    const s=await session(), result=await upload(s,png,s.scan,settings);
    assert.equal(result.status,200); assert.equal(result.data.ocr_status,invalid?"failed":"done");
    const rows=sqlite.prepare("SELECT model,in_tok,out_tok,cached_tok,usd,ok,error FROM lab_calls WHERE session_id=? AND provider='gemini'").all(s.id);
    assert.equal(rows.length,invalid?4:1,"one billing row per actual attempt, including bounded queue retries");
    for(const row of rows) { assert.equal(row.model,"gemini-2.5-flash"); assert.equal(row.in_tok,1000); assert.equal(row.out_tok,100); assert.equal(row.cached_tok,400);
    assert.ok(Math.abs(row.usd-expected)<1e-9,"the selected-model override is retained when the provider resolves a version");
    assert.equal(row.ok,invalid?0:1); assert.ok(!String(row.error||"").includes("PRIVATE_UPSTREAM_PAYLOAD")); }
    const calls=captures.filter(call=>call.provider==="gemini"); assert.equal(calls.length,rows.length); assert.match(calls[0].url,new RegExp(selectedModel+":generateContent$"));
    if(invalid) { const saved=sqlite.prepare("SELECT data,ocr FROM lab_pages WHERE id=?").get(result.data.id);assert.equal(saved.ocr,null);assert.ok(Buffer.from(saved.data).equals(png)); }
  }
});

test("real admin metrics keep incomplete totals null while exposing known costs and unknown-call counts", async () => {
  reset(); const admin=await session(), s=await session({status:"graded"}), timestamp=Math.floor(Date.now()/1000), model="gemini-metrics-fixture";
  sqlite.prepare("UPDATE users SET role='admin' WHERE id=?").run(admin.id);
  sqlite.prepare("UPDATE lab_sessions SET submitted_at=?,graded_at=?,score=1,points=1,detail=? WHERE id=?").run(timestamp,timestamp,JSON.stringify({grade_ms:42}),s.id);
  const insert=sqlite.prepare(`INSERT INTO lab_calls(session_id,task,step,provider,model,in_tok,out_tok,cached_tok,usd,ms,ok,error,created_at)
    VALUES(?,'E1','grade','gemini',?,?,?,?,?,?,?, ?,?)`);
  insert.run(s.id,model,1000,100,400,0.00234,30,1,null,timestamp);
  insert.run(s.id,model,null,null,null,null,20,0,"fixture unknown usage",timestamp);
  const result=await api("/admin/lab/metrics?days=1",{headers:{Authorization:"Bearer "+admin.token}});
  assert.equal(result.status,200); const step=result.data.steps.find(row=>row.model===model&&row.step==="grade"), sitting=result.data.sessions.find(row=>row.id===s.id);
  assert.ok(step); assert.equal(step.n,2); assert.equal(step.failed,1); assert.equal(step.usd,null); assert.equal(step.known_usd,0.00234); assert.equal(step.unknown_cost_calls,1);
  assert.equal(step.cache_hit_calls,1); assert.equal(step.unknown_cache_calls,1);
  assert.ok(sitting); assert.equal(sitting.calls,2); assert.equal(sitting.usd,null); assert.equal(sitting.known_usd,0.00234); assert.equal(sitting.unknown_cost_calls,1);
  assert.equal(captures.length,0,"reading administrator metrics cannot call any provider");
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

test("removing a selected provider key prevents grading without changing saved evidence or provider", async () => {
  const original=FORMULA+"\n"+"x".repeat(61000)+" END_MUST_NEVER_DISAPPEAR";
  reset({read:{...readFixture(),text:original}});const s=await session();assert.equal((await upload(s)).data.ocr_status,"done");
  const before=captures.length;const result=await api(`/lab/sessions/${s.id}/submit`,{method:"POST",headers:{Authorization:"Bearer "+s.token,"Content-Type":"application/json"},body:JSON.stringify({provider:"gemini"})},{...env,GEMINI_API_KEY:""});
  assert.equal(result.status,503);assert.equal(result.data.error,"provider_unavailable");assert.equal(captures.length,before);
  const page=(await getSession(s)).data.session.pages[0];assert.equal(page.text,original);
  assert.equal((await getSession(s)).data.session.provider,"gemini");
});

test("paid-session selection locks reject provider changes without mutating original evidence", async () => {
  const original="original OCR must survive conflicting requests\n".padEnd(80000,"x"),image=Buffer.alloc(1900000);png.copy(image);
  reset({read:{...readFixture(),text:original}});const s=await session(),uploaded=await upload(s,image);assert.equal(uploaded.data.ocr_status,"done");
  const before=sqlite.prepare("SELECT ocr,text,read,data FROM lab_pages WHERE id=?").get(uploaded.data.id);assert.equal(before.ocr,original);
  const calls=captures.length;
  const conflict=await api(`/lab/sessions/${s.id}/provider`,{method:"POST",headers:{Authorization:"Bearer "+s.token,"Content-Type":"application/json"},body:JSON.stringify({provider:"deepseek"})});
  assert.equal(conflict.status,409);assert.equal(conflict.data.error,"provider_locked");assert.equal(captures.length,calls);
  const after=sqlite.prepare("SELECT ocr,text,read,data FROM lab_pages WHERE id=?").get(uploaded.data.id);
  assert.equal(after.ocr,before.ocr);assert.equal(after.text,before.text);assert.equal(after.read,before.read);assert.ok(Buffer.from(after.data).equals(Buffer.from(before.data)));
});

test("proof review scan stores the same original and still requires the student's explicit confirmation", async () => {
  reset(); const owner = await session();
  sqlite.prepare("UPDATE lab_sessions SET status='ended' WHERE id=?").run(owner.id);
  const headers = { Authorization: "Bearer " + owner.token, "Content-Type": "application/json" };
  const started = await api("/lab/contest/start", { method: "POST", headers, body: JSON.stringify({ examId: "kmo-2025-T2-s2", purpose: "review", provider:"gemini", runId: "ocr-parity-proof" }) });
  assert.equal(started.status, 200);
  const sid = started.data.session.id, scan = started.data.token;
  const saved = await api(`/lab/up/${sid}/pages?task=Q5&kind=answer`, { method: "PUT", headers: { "Content-Type": "image/png", "X-Lab-Token": scan }, body: png });
  assert.equal(saved.data.ocr_status, "unpaid"); assert.equal(captures.length, 0);
  assert.equal((await api(`/lab/sessions/${sid}/pay`, { method: "POST", headers, body: JSON.stringify({provider:"gemini"}) })).status, 200);
  const read = await api(`/lab/contest/sessions/${sid}/read`, { method: "POST", headers, body: JSON.stringify({provider:"gemini"}) });
  assert.equal(read.status, 200);
  const page = read.data.session.pages[0];
  assert.equal(page.task, "Q5", "auxiliary header cannot override the student's chosen proof task");
  assert.equal(page.text, FORMULA); assert.equal(page.read.ocr.text, FORMULA); assert.equal(page.confirmed, false);
  assert.equal(sqlite.prepare("SELECT text FROM lab_pages WHERE id=?").get(page.id).text, null);
  const submit = await api(`/lab/sessions/${sid}/submit`, { method: "POST", headers, body: JSON.stringify({provider:"gemini"}) });
  assert.equal(submit.status, 409); assert.equal(submit.data.error, "needs_confirmation");
  const confirmed = await api(`/lab/contest/sessions/${sid}/pages/${page.id}/confirm`, { method: "POST", headers, body: JSON.stringify({ task: "Q5", text: FORMULA }) });
  assert.equal(confirmed.status, 200); assert.equal(confirmed.data.session.pages[0].confirmed, true);
  assert.equal(confirmed.data.session.pages[0].text, FORMULA);
  assert.equal(sqlite.prepare("SELECT text FROM lab_pages WHERE id=?").get(page.id).text, null, "confirming an unchanged original does not duplicate it in D1");
  const largeImage = Buffer.alloc(1900000); png.copy(largeImage);
  fixture.read = {...readFixture(),text:"original".padEnd(60000,"x")};
  const large = await api(`/lab/up/${sid}/pages?task=Q5&kind=answer`, { method: "PUT", headers: { "Content-Type": "image/png", "X-Lab-Token": scan }, body: largeImage });
  assert.equal(large.data.ocr_status, "queued");await drainQueue();
  assert.equal((await api(`/lab/sessions/${sid}`,{headers})).data.session.pages.find(p=>p.id===large.data.id).ocr_status,'done');
  const overBudget = await api(`/lab/contest/sessions/${sid}/pages/${large.data.id}/confirm`, { method: "POST", headers,
    body: JSON.stringify({ task: "Q5", text: "a corrected original".padEnd(50000, "y") }) });
  assert.equal(overBudget.status, 413); assert.equal(overBudget.data.error, "ocr_storage_limit");
  const preserved = sqlite.prepare("SELECT ocr,text,data,edited FROM lab_pages WHERE id=?").get(large.data.id);
  assert.equal(preserved.ocr, fixture.read.text); assert.equal(preserved.text, null); assert.equal(preserved.edited, 0);
  assert.ok(Buffer.from(preserved.data).equals(largeImage));
});
