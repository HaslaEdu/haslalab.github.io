// stand-in for Upstage OCR, Gemini, Toss Payments (/toss), Paddle's API (/paddle) and the PDF Worker (GET /seen: how many page readings got Upstage's transcript), for the exam-mode tests.  node test-lab-mock.mjs  (port 8799), and in
// .dev.vars: UPSTAGE_API_KEY=test UPSTAGE_BASE=http://127.0.0.1:8799/upstage GEMINI_API_KEY=test GEMINI_BASE=http://127.0.0.1:8799/gemini
//            LAB_PDF_BASE=http://127.0.0.1:8799/pdf/
// Gemini answers by the task tag at the head of the prompt:
//   [TASK: build marking scheme]  a fixed scheme (A.1, A.2, A.3 values, B.1 graph, C.1 derivation; 3.5 points)
//   [TASK: read page]             a fixed reading (A.1 108.2 ohm, A.2 395, a graph with 6 points, C.1 text); a page image
//                                 longer than 300 bytes carries the header «E2, working sheet», one longer than 600 is «poor»
//   [TASK: grade]                 every item found on the first answer page of the task (else the first page), half marks,
//                                 values as read — except A.3, claimed as 11, which is on no page (the Worker must give 0)
//   anything else                 the old text grader: half marks with a quote from the answer
import http from "node:http";
const flaky = new Set(), seen = { ocrIntoRead: 0 }, orders = new Map(), paddleTx = new Map();
const OCR_TEXT = "E1 A.1 R0 = 108.2 ohm, slope k = 0.385 ohm/K\nE1 A.2 lambda = 395 W/(m K)";
const SCHEME = { points: 3.5, unit_rule: "a missing unit loses the mark", items: [
  { id: "A.1", points: 0.4, type: "value", sheet: "answer", what: "R0", unit: "ohm", full_min: 105, full_max: 111, partial: [{ min: 100, max: 115, points: 0.2 }] },
  { id: "A.2", points: 0.6, type: "value", sheet: "answer", what: "lambda", unit: "W/(m K)", full_min: 380, full_max: 410, partial: [{ min: 360, max: 430, points: 0.3 }] },
  { id: "A.3", points: 0.5, type: "value", sheet: "answer", what: "h", unit: "W/(m2 K)", full_min: 10, full_max: 12, partial: [] },
  { id: "B.1", points: 1.0, type: "graph", sheet: "answer", what: "graph of ln(T) against t", checks: [
    { check: "axes_labeled", points: 0.2 }, { check: "points_min", n: 8, points: 0.3 }, { check: "fit_line", points: 0.2 }, { check: "slope_read", points: 0.3 }] },
  { id: "C.1", points: 1.0, type: "derivation", sheet: "any", what: "lambda = P L / (A dT)" }] };
/* a solution whose name says "table" has measured tables and a graph: D.1 needs 5 rows (stated), D.2 is a graph of a
   measurement that needs many points (no number given → 7), D.3 a table with no count check (medium → 5) */
const SCHEME_T = { points: 2.3, items: [
  { id: "D.1", points: 0.7, type: "table", sheet: "answer", what: "table of T(t)", checks: [{ check: "rows_min", n: 5, points: 0.5 }, { check: "columns_units", points: 0.2 }] },
  { id: "D.2", points: 0.6, type: "graph", sheet: "answer", what: "graph of T(t)", n_class: "many", checks: [{ check: "points_min", points: 0.3 }, { check: "axes_labeled", points: 0.3 }] },
  { id: "D.3", points: 1.0, type: "table", sheet: "answer", what: "table of V(I)", n_class: "medium" }] };
const TABLES = [
  { label: "D.1", kind: "table", text: "t/s | T/K", rows: 4, columns: ["t/s", "T/K"], crossed_out: false },
  { label: "D.2", kind: "graph", text: "graph", crossed_out: false, graph: { axes_labeled: true, axes_units: true, scale_ok: true, n_points: 6, fit_line: true, slope_read: false, error_bars: false, title: false, slope: null } },
  { label: "D.3", kind: "table", text: "I/A | V/V", rows: 4, columns: ["I/A", "V/V"], crossed_out: false }];
const page = (big, tables) => ({ header: big ? { task: "E2", sheet: "working", page: 2 } : { task: null, sheet: null, page: null }, legible: big === 2 ? "poor" : "good", items: [
  { label: "A.1", kind: "value", text: "R0 = 108.2 ohm", value: 108.2, unit: "ohm", crossed_out: false, box: [100, 100, 150, 400] },
  { label: "A.2", kind: "value", text: "lambda = 395 W/(m K)", value: 395, unit: "W/(m K)", crossed_out: false, box: [200, 100, 250, 400] },
  { label: "B.1", kind: "graph", text: "graph", crossed_out: false, graph: { axes_labeled: true, axes_units: true, scale_ok: true, n_points: 6, fit_line: true, slope_read: false, error_bars: false, title: false, slope: null } },
  { label: "C.1", kind: "text", text: "lambda = P L/(A dT)", crossed_out: false }, ...(tables ? TABLES : [])] });
/* every answer reports its tokens as Gemini does: 1000 in (400 of them cached), 200 out and 50 of thinking */
const reply = (res, o) => { res.setHeader("Content-Type", "application/json"); res.end(JSON.stringify({ candidates: [{ content: { parts: [{ text: JSON.stringify(o) }] } }],
  usageMetadata: { promptTokenCount: 1000, cachedContentTokenCount: 400, candidatesTokenCount: 200, thoughtsTokenCount: 50 } })); };
http.createServer(async (req, res) => {
  let b = []; for await (const c of req) b.push(c); b = Buffer.concat(b);
  /* Toss Payments: confirm (paymentKey "fail…" is refused, "dup…" was confirmed already), look up, cancel; the secret key must be test_sk_mock */
  if (req.url.startsWith("/toss/")) {
    res.setHeader("Content-Type", "application/json");
    if (req.headers.authorization !== "Basic " + Buffer.from("test_sk_mock:").toString("base64")) { res.statusCode = 401; return res.end(JSON.stringify({ code: "UNAUTHORIZED_KEY", message: "bad key" })); }
    const body = b.length ? JSON.parse(b) : {}, path = req.url.slice(5);
    const done = (key, orderId, amount) => ({ paymentKey: key, orderId, totalAmount: amount, status: "DONE", method: "카드", approvedAt: new Date().toISOString(), receipt: { url: "https://receipt.example/" + key } });
    if (path === "/v1/payments/confirm") {
      seen.confirms = (seen.confirms || 0) + 1;
      if (/^fail/.test(body.paymentKey)) { res.statusCode = 400; return res.end(JSON.stringify({ code: "REJECT_CARD_PAYMENT", message: "한도초과 혹은 잔액부족으로 결제에 실패했습니다." })); }
      if (/^dup/.test(body.paymentKey)) { orders.set(body.paymentKey, body); res.statusCode = 400; return res.end(JSON.stringify({ code: "ALREADY_PROCESSED_PAYMENT", message: "이미 처리된 결제 입니다." })); }
      orders.set(body.paymentKey, body);
      return res.end(JSON.stringify(done(body.paymentKey, body.orderId, body.amount)));
    }
    const mm = /^\/v1\/payments\/([^/]+)(\/cancel)?$/.exec(path), o = mm && orders.get(decodeURIComponent(mm[1]));
    if (!o) { res.statusCode = 404; return res.end(JSON.stringify({ code: "NOT_FOUND_PAYMENT", message: "no payment" })); }
    if (mm[2]) return res.end(JSON.stringify({ ...done(o.paymentKey, o.orderId, o.amount), status: "CANCELED" }));
    return res.end(JSON.stringify(done(o.paymentKey, o.orderId, o.amount)));
  }
  /* Paddle's API: GET /transactions/:id (txn_ok… completed for the order named in its id's tail, txn_open… not yet
     paid), POST /adjustments (a refund); the API key must be pdl_mock.  POST /paddle/txn registers a transaction */
  if (req.url.startsWith("/paddle/")) {
    res.setHeader("Content-Type", "application/json");
    const path = req.url.slice(7), body = b.length ? JSON.parse(b) : {};
    if (path === "/txn") { paddleTx.set(body.id, body); return res.end("{}"); }
    if (req.headers.authorization !== "Bearer pdl_mock") { res.statusCode = 403; return res.end(JSON.stringify({ error: { code: "forbidden", detail: "bad key" } })); }
    const mm = /^\/transactions\/(txn_\w+)$/.exec(path);
    if (mm) { const tx = paddleTx.get(mm[1]); if (!tx) { res.statusCode = 404; return res.end(JSON.stringify({ error: { code: "not_found" } })); } return res.end(JSON.stringify({ data: tx })); }
    if (path === "/adjustments") { seen.refunds = (seen.refunds || 0) + 1; res.statusCode = 201; return res.end(JSON.stringify({ data: { id: "adj_1", action: body.action, status: "pending_approval", transaction_id: body.transaction_id } })); }
    res.statusCode = 404; return res.end("{}");
  }
  if (req.url === "/seen") { res.setHeader("Content-Type", "application/json"); return res.end(JSON.stringify(seen)); }
  if (req.url.startsWith("/upstage")) {
    /* an image of 500–599 bytes (a test PNG with padding) is one Upstage is unsure of */
    const i = b.indexOf(Buffer.from([0x89, 0x50, 0x4e, 0x47])), e = i < 0 ? -1 : b.indexOf("\r\n--", i), unsure = e - i >= 500 && e - i < 600;
    res.setHeader("Content-Type", "application/json");
    return res.end(JSON.stringify({ text: OCR_TEXT, content: { markdown: OCR_TEXT }, confidence: unsure ? 0.5 : 0.91, usage: { pages: 1 } }));
  }
  if (req.url.startsWith("/pdf/")) {
    const name = decodeURIComponent(req.url.slice(5));
    if (/missing|_KO\.pdf$/.test(name)) { res.statusCode = 404; return res.end("nope"); }   // only the English originals exist here
    if (/flaky/.test(name) && !flaky.has(name)) { flaky.add(name); res.statusCode = 502; return res.end("bad gateway"); }   // fails once, then works
    res.setHeader("Content-Type", "application/pdf"); return res.end("%PDF-1.4 fake solution " + name);
  }
  if (req.url.includes(":generateContent")) {
    const parts = JSON.parse(b).contents[0].parts, prompt = parts.map(p => p.text || "").join("\n");
    if (prompt.includes("Find the four corners of the sheet of paper")) return reply(res, { tl: [100, 80], tr: [900, 90], br: [880, 950], bl: [110, 940] });
    if (prompt.startsWith("[TASK: build marking scheme]")) {        // the stand-in solution PDF carries its own name
      const pdf = parts.find(p => p.inline_data), name = pdf ? Buffer.from(pdf.inline_data.data, "base64").toString() : "";
      return reply(res, /_table/.test(name) ? SCHEME_T : SCHEME);
    }
    if (prompt.startsWith("[TASK: read page]")) {
      if (prompt.includes("<<OCR>>") && prompt.includes("R0 = 108.2 ohm")) seen.ocrIntoRead++;
      /* only the tests' PNGs choose a header or a poor page by their length; a phone's JPEG is an ordinary, legible page */
      const img = parts.find(p => p.inline_data), n = img && img.inline_data.mime_type === "image/png" ? Buffer.from(img.inline_data.data, "base64").length : 0;
      return reply(res, page(n > 600 ? 2 : n > 300 ? 1 : 0, n >= 150 && n <= 300));   // 150–300 bytes: a page with the measured tables
    }
    if (prompt.startsWith("[TASK: grade]")) {
      const sc = JSON.parse(prompt.split("<<SCHEME>>")[1].split("<<END>>")[0]), pages = JSON.parse(prompt.split("<<PAGES>>")[1].split("<<END>>")[0]);
      const pg = (pages.find(p => p.kind === "answer") || pages[0] || {}).no ?? null;
      const val = { "A.1": 108.2, "A.2": 395, "A.3": 11 };
      return reply(res, { items: sc.items.map(it => ({ id: it.id, found: true, page: pg, label: it.id, value: val[it.id] ?? null, unit_ok: true,
        checks_met: ["axes_labeled", "points_min", "fit_line", "slope_read", "rows_min", "columns_units"], score: it.points / 2, decision: "partial", rules: [], note: "ok" })),
        feedback: [{ page: pg, label: "A.1", note: "units ok", kind: "good" }, { page: 999, label: "X", note: "a page that does not exist", kind: "fix" }] });
    }
    const ids = [...prompt.matchAll(/^- (\S+) \(.*?\): 0~([\d.]+)/gm)].map(m => [m[1], +m[2]]);
    const ans = prompt.split("[Student answer and working sheets]")[1] || "";
    const quote = (ans.match(/R0 = 108\.2 ohm/) || [""])[0];
    return reply(res, { scores: ids.map(([id, max]) => ({ id, got: max / 2, note: "ok", decision: "partial", evidence: quote ? [quote] : [] })),
      feedback: quote ? [{ quote, note: "units ok", kind: "good" }] : [], confidence: 0.8 });
  }
  res.statusCode = 404; res.end("{}");
}).listen(8799, () => console.log("mock on 8799"));
