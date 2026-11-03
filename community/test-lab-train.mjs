// node --test community/test-lab-train.mjs
// Training data for models of our own: the grader's input and target, the JSONL lines, the exam-wise split, and the
// «tuned» provider a fine-tuned model is served back through.
import assert from "node:assert/strict";
import test from "node:test";
import { gradeTrainInput, gradeTrainTarget, chatLine, vertexReadLine, splitByExam, GRADE_TRAIN_SYSTEM } from "./src/lab-train.js";
import { visionJSON, requireVisionProvider } from "./src/vision-provider.js";

const scheme = { items: [{ id: "A.1", points: 0.3, what: "v = sqrt(GM/r)", expr: "sqrt(G*M/r)" }, { id: "A.2", points: 0.2, what: "period", value: 1.5, unit: "s", alt: "A2/1" }] };

test("the grader's input lists the scheme's lines and the pages, answer sheets first; the target has one mark per line, within its points", () => {
  const input = gradeTrainInput(scheme, [{ no: 2, kind: "working", ocr: "W text" }, { no: 1, kind: "answer", ocr: "A text" }], { task: "T1", exam: "ipho2025" });
  assert.match(input, /^Exam: ipho2025 T1/);
  assert.match(input, /A\.1 \| 0\.3 \| v = sqrt\(GM\/r\) \| official: sqrt\(G\*M\/r\)/);
  assert.match(input, /A\.2 \| 0\.2 \| period \| official: 1\.5 s \| alternative method A2\/1/);
  assert.ok(input.indexOf("A text") < input.indexOf("W text"), "answer sheets first");
  assert.deepEqual(JSON.parse(gradeTrainTarget(scheme, [{ id: "A.1", got: 0.9 }])).items, [{ id: "A.1", score: 0.3 }, { id: "A.2", score: 0 }]);
  const line = JSON.parse(chatLine("in", "out"));
  assert.deepEqual(line.messages, [{ role: "system", content: GRADE_TRAIN_SYSTEM }, { role: "user", content: "in" }, { role: "assistant", content: "out" }]);
});

test("a page reader's line is Vertex AI's supervised-tuning format with a gs:// photo; a split keeps each paper on one side", () => {
  const v = JSON.parse(vertexReadLine({ fileUri: "gs://bucket-1/lab-pages/9.jpg", transcript: "A.1 v = 1" }));
  assert.equal(v.contents[0].role, "user"); assert.deepEqual(v.contents[0].parts[0], { fileData: { mimeType: "image/jpeg", fileUri: "gs://bucket-1/lab-pages/9.jpg" } });
  assert.deepEqual(v.contents[1], { role: "model", parts: [{ text: "A.1 v = 1" }] });
  assert.throws(() => vertexReadLine({ fileUri: "https://x/9.jpg", transcript: "x" }), /bad_file_uri/);
  const rows = Array.from({ length: 40 }, (_, i) => ({ exam_key: "ex" + (i % 10), task: "T1", i }));
  const { train, validation } = splitByExam(rows, 0.3);
  assert.equal(train.length + validation.length, 40);
  for (const v of validation) assert.ok(!train.some(t => t.exam_key === v.exam_key), "no paper on both sides");
});

test("the «tuned» provider: an OpenAI-compatible endpoint from TUNED_BASE/TUNED_MODEL, text only (photos left out), unavailable until set", async () => {
  assert.throws(() => requireVisionProvider({ TUNED_API_KEY: "k" }, "tuned"), e => e.code === "provider_unavailable");
  const seen = [];
  const fetchImpl = async (url, init) => { seen.push({ url, body: JSON.parse(init.body), auth: init.headers.Authorization }); return Response.json({ model: "acct/ds-lora", choices: [{ finish_reason: "stop", message: { content: '{"items":[]}' } }], usage: { prompt_tokens: 10, completion_tokens: 3 } }); };
  const env = { TUNED_API_KEY: "k", TUNED_BASE: "https://host.example/v1", TUNED_MODEL: "acct/ds-lora" };
  const out = await visionJSON(env, { provider: "tuned", fetchImpl, parts: [{ text: "grade this" }, { mime: "image/png", data: "iVBORw0KGgo=", label: "p1" }] });
  assert.equal(seen[0].url, "https://host.example/v1/chat/completions"); assert.equal(seen[0].auth, "Bearer k");
  assert.equal(seen[0].body.model, "acct/ds-lora"); assert.deepEqual(seen[0].body.response_format, { type: "json_object" });
  assert.ok(!JSON.stringify(seen[0].body).includes("image_url"), "no photo is sent");
  assert.deepEqual(out.raw, { items: [] });
});

import { auditedLines, vertexGradeLine, gradeAgainstAudit } from "./src/lab-train.js";
test("an audited paper as a grading example: audit marks matched to the scheme's lines, a lettered id by its number, too little coverage left out", () => {
  const scheme = { items: [{ id: "1.1.a", points: 0.4, what: "a" }, { id: "1.2", points: 0.6, what: "b" }, { id: "2.1", points: 1, what: "c" }] };
  const lines = auditedLines(scheme, [{ id: "1.1.1", points: 0.4, got: 0.4 }, { id: "1.2", points: 0.6, got: 0 }, { id: "2.1", points: 1, got: 1.5 }]);
  assert.deepEqual(lines.map(l => [l.item.id, l.got]), [["1.1.a", 0.4], ["1.2", 0], ["2.1", 1]], "a mark is held within the line's points");
  assert.equal(auditedLines(scheme, [{ id: "1.2", points: 0.6, got: 0 }]), null, "one line of three stands for no paper");
  assert.equal(auditedLines(scheme, [{ id: "1.2", points: 0.5, got: 0 }, { id: "2.1", points: 1, got: 1 }, { id: "1.1.a", points: 0.4, got: 0 }], 0.5).length, 2, "points that differ: another scheme's line");
  const line = JSON.parse(vertexGradeLine("input", lines));
  assert.equal(line.contents[0].parts[0].text, "input"); assert.equal(line.contents[1].role, "model");
  assert.deepEqual(JSON.parse(line.contents[1].parts[0].text), { items: [{ id: "1.1.a", score: 0.4 }, { id: "1.2", score: 0 }, { id: "2.1", score: 1 }] });
  assert.match(line.systemInstruction.parts[0].text, /official marker/);
  const e = gradeAgainstAudit(lines, [{ id: "1.1.a", score: 0.4 }, { id: "1.2", score: 0.5 }]);
  assert.equal(e.mis, 2); assert.equal(e.over, 1); assert.equal(e.under, 1); assert.equal(e.missing, 1); assert.equal(e.score, 0.9); assert.equal(e.ref, 1.4);
});
