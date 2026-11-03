// Training data for models of our own (admin only; nothing is collected unless LAB_TRAIN_CAPTURE is on).
//  · grade: (marking scheme + the pages' transcripts) → the item marks, as chat messages: the format DeepSeek's open
//    weights are fine-tuned from (LoRA at a host, or our own server), served back as the «tuned» provider
//    (vision-provider.js). Only rows an admin has verified (or corrected) are exported for training.
//  · read: a page photo → its transcript (Claude's gold transcriptions in the bench), as Vertex AI's supervised-tuning
//    lines for Gemini (gs:// photo URIs: the photos go to a Cloud Storage bucket first).

export const LAB_TRAIN_SQL = `CREATE TABLE IF NOT EXISTS lab_train (id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL,
  session_id INTEGER, task TEXT, page_id INTEGER, exam_key TEXT, input TEXT NOT NULL, target TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'model', verified INTEGER NOT NULL DEFAULT 0, note TEXT,
  created_at INTEGER NOT NULL DEFAULT (unixepoch()), verified_at INTEGER)`;

export const GRADE_TRAIN_SYSTEM = [
  "You grade one student's olympiad paper against the official marking scheme, as an official marker would.",
  "Give each scheme line the marks the student's written work earns (0 up to its points): credit correct work in another form",
  "or another valid way, and steps a correct later result could not have been written without; give nothing for what is",
  "missing or wrong. Of alternative methods, mark only the one the student used.",
  'Return one JSON object: {"items":[{"id":"<scheme line id>","score":<number>}]}, one entry for every line.'].join(" ");

const clip = (v, n) => String(v ?? "").slice(0, n);

/** the grader's input: the scheme's lines, then each page's transcript (answer sheets first) */
export function gradeTrainInput(scheme, pages, { task = "", exam = "" } = {}) {
  const lines = (scheme?.items || []).map(it => [it.id, it.points, clip(it.what, 300),
    it.expr ? "official: " + clip(it.expr, 200) : it.value != null ? `official: ${it.value}${it.unit ? " " + it.unit : ""}` : "",
    it.alt ? `alternative method ${it.alt}` : ""].filter(x => x !== "").join(" | "));
  const order = [...(pages || [])].sort((a, b) => (a.kind === "answer" ? 0 : 1) - (b.kind === "answer" ? 0 : 1) || (a.no || 0) - (b.no || 0));
  const sheets = order.map(p => `[page ${p.no ?? ""} · ${p.kind || "page"}]\n${clip(p.ocr ?? p.text ?? "", 12000)}`);
  return [`Exam: ${exam} ${task}`.trim(), "", "Marking scheme (id | points | what earns them | official | method):", ...lines, "", "Student pages:", ...sheets].join("\n");
}

/** the target: one mark per scheme line (a line the grading left out is 0), each within its points */
export function gradeTrainTarget(scheme, items) {
  const by = new Map((items || []).filter(Boolean).map(i => [String(i.id), i]));
  return JSON.stringify({ items: (scheme?.items || []).map(it => {
    const got = +(by.get(String(it.id))?.got ?? by.get(String(it.id))?.score ?? 0) || 0;
    return { id: String(it.id), score: +Math.max(0, Math.min(+it.points || 0, got)).toFixed(3) };
  }) });
}

/** one chat-format training line (OpenAI / DeepSeek fine-tuning JSONL) */
export const chatLine = (input, target, system = GRADE_TRAIN_SYSTEM) =>
  JSON.stringify({ messages: [{ role: "system", content: system }, { role: "user", content: input }, { role: "assistant", content: target }] });

export const READ_TRAIN_PROMPT = "Transcribe this handwritten physics answer page exactly: keep the student's own notation, signs, subscripts, exponents and units, write mathematics as LaTeX, mark crossed-out text, and do not correct or complete anything. Leave out marks made by a grader in red pen.";

/** one Vertex AI supervised-tuning line for a Gemini page reader */
export function vertexReadLine({ fileUri, mime = "image/jpeg", transcript, prompt = READ_TRAIN_PROMPT }) {
  if (!/^gs:\/\/[a-z0-9._-]{3,222}\/\S+$/.test(String(fileUri || ""))) throw new Error("bad_file_uri");
  return JSON.stringify({ contents: [
    { role: "user", parts: [{ fileData: { mimeType: mime, fileUri } }, { text: prompt }] },
    { role: "model", parts: [{ text: String(transcript || "") }] }] });
}

/** a training split that keeps every exam paper on one side (a paper seen in training says nothing as validation) */
export function splitByExam(rows, share = 0.2) {
  const keys = [...new Set(rows.map(r => r.exam_key + ":" + r.task))].sort();
  const hash = k => [...k].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7);
  const val = new Set(keys.filter(k => (hash(k) % 1000) / 1000 < share));
  return { train: rows.filter(r => !val.has(r.exam_key + ":" + r.task)), validation: rows.filter(r => val.has(r.exam_key + ":" + r.task)) };
}
