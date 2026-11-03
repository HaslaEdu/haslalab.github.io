// node --test community/test-upstage-ocr.mjs
// Upstage Document Parse as a page reader: the request it sends, and the tuned reader's strips and arbitration.
import assert from "node:assert/strict";
import test from "node:test";
import jpeg from "jpeg-js";
import { upstageParse, upstageTunedRead, joinStrips, disagreements } from "./src/upstage-ocr.js";

const page = (width, height) => new Uint8Array(jpeg.encode({ width, height, data: new Uint8Array(width * height * 4).fill(200) }, 90).data);

test("a page goes to Document Parse as a multipart «document», OCR forced, markdown asked for; enhanced is sent, standard is not", async () => {
  const seen = [];
  const fetchImpl = async (url, init) => { seen.push({ url, auth: init.headers.Authorization, form: init.body }); return Response.json({ model: "document-parse-260930", content: { markdown: "$r_2^4$", text: "r2 4" }, usage: { pages: 1 } }); };
  const r = await upstageParse({ UPSTAGE_API_KEY: " u\n" }, page(20, 20), "image/jpeg", { mode: "enhanced", fetchImpl });
  assert.equal(seen[0].url, "https://api.upstage.ai/v1/document-digitization"); assert.equal(seen[0].auth, "Bearer u");
  const f = seen[0].form; assert.ok(f.get("document") instanceof Blob); assert.equal(f.get("model"), "document-parse");
  assert.equal(f.get("mode"), "enhanced"); assert.equal(f.get("ocr"), "force"); assert.deepEqual(JSON.parse(f.get("output_formats")), ["markdown", "text"]);
  assert.equal(r.markdown, "$r_2^4$", "math is read from markdown, never from text"); assert.equal(r.usd, 0.03);
  await upstageParse({ UPSTAGE_API_KEY: "u" }, page(20, 20), "image/jpeg", { mode: "standard", fetchImpl });
  assert.equal(seen[1].form.get("mode"), null); await assert.rejects(upstageParse({}, page(20, 20)), e => e.code === "provider_unavailable");
});

test("strips are joined top to bottom without the lines their overlap repeats, and lines that disagree with the whole page are paired", () => {
  assert.equal(joinStrips(["A.1 x = 1\nA.2 y = 2", "A.2 y = 2\nA.3 z = 3"]), "A.1 x = 1\nA.2 y = 2\nA.3 z = 3");
  const d = disagreements("A.4 I = 1/2 (r_1^4 + r_2^4)\nA.5 h = M", "A.4 I = 1/2 (r_1^4 + r_2^2)\nA.5 h = M");
  assert.deepEqual(d.map(x => x.line), [0]); assert.match(d[0].whole, /r_2\^2/);
});

test("the tuned reader reads the page whole and in strips; the arbiter only picks between the two readings, and «uncertain» keeps the strips' line marked", async () => {
  let n = 0;
  const fetchImpl = async (url, init) => {
    const whole = n++ === 0;                                                       // the whole page is sent first
    return Response.json({ content: { markdown: whole ? "A.3 d^2 = Mb\nA.4 I = r_2^2" : "A.3 d = Mb\nA.4 I = r_2^4" }, usage: { pages: 1 } });
  };
  const asked = [];
  const visionJSON = async (env, req) => { asked.push(req); return { raw: { choices: [{ line: 0, pick: "strips" }, { line: 1, pick: "uncertain" }] }, usage: { input_tokens: 100, output_tokens: 20 } }; };
  const log = [];
  const r = await upstageTunedRead({ UPSTAGE_API_KEY: "u" }, page(300, 600), "image/jpeg", { strips: 2, fetchImpl, visionJSON, log });
  assert.equal(r.pieces, 3, "the whole page and two strips");
  assert.equal(asked.length, 1); assert.equal(asked[0].provider, "upstage"); assert.equal(asked[0].model, "solar-pro4");
  assert.match(asked[0].parts[0].text, /never by which one is physically right/);
  assert.equal(r.markdown.split("\n")[0], "A.3 d = Mb");
  assert.match(r.markdown.split("\n")[1], /^A\.4 I = r_2\^4 +\[\? whole page read: A\.4 I = r_2\^2\]$/);
  assert.equal(log.filter(c => c.step === "ocr").length, 3); assert.ok(log.some(c => c.step === "arbiter" && c.ok === 1));
});
