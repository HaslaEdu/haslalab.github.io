// stand-in for Upstage OCR and Gemini, for the exam-mode tests: OCR returns a fixed answer text; the grader gives every
// rubric criterion half marks with a quote taken from the student's text.  node test-lab-mock.mjs  (port 8799), and in
// .dev.vars: UPSTAGE_API_KEY=test UPSTAGE_BASE=http://127.0.0.1:8799/upstage GEMINI_API_KEY=test GEMINI_BASE=http://127.0.0.1:8799/gemini
import http from "node:http";
const OCR_TEXT = "E1 A.1 R0 = 108.2 ohm, slope k = 0.385 ohm/K\nE1 A.2 lambda = 395 W/(m K)";
http.createServer(async (req, res) => {
  let b = []; for await (const c of req) b.push(c); b = Buffer.concat(b);
  if (req.url.startsWith("/upstage")) {
    res.setHeader("Content-Type", "application/json");
    return res.end(JSON.stringify({ text: OCR_TEXT, content: { markdown: OCR_TEXT }, confidence: 0.91 }));
  }
  if (req.url.includes(":generateContent")) {
    const prompt = JSON.parse(b).contents[0].parts[0].text;
    const ids = [...prompt.matchAll(/^- (\S+) \(.*?\): 0~([\d.]+)/gm)].map(m => [m[1], +m[2]]);
    const ans = prompt.split("[Student answer and working sheets]")[1] || "";
    const quote = (ans.match(/R0 = 108\.2 ohm/) || [""])[0];
    const out = { scores: ids.map(([id, max]) => ({ id, got: max / 2, note: "ok", decision: "partial", evidence: quote ? [quote] : [] })),
      feedback: quote ? [{ quote, note: "units ok", kind: "good" }] : [], confidence: 0.8 };
    res.setHeader("Content-Type", "application/json");
    return res.end(JSON.stringify({ candidates: [{ content: { parts: [{ text: JSON.stringify(out) }] } }] }));
  }
  res.statusCode = 404; res.end("{}");
}).listen(8799, () => console.log("mock on 8799"));
