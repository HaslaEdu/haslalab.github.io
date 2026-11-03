/* Excel for ISPhO: the workbook library (sim/xlsx-lite.js), the tables the papers hand out (sim/ispho-xlsx-templates.js,
   tools/ispho_xlsx.cjs), the spreadsheet on the simulator laptops (sim/vexcel.js) and the files handed in for grading
   (sim/exam.html → POST /api/lab/sessions/:id/files) */
const test = require("node:test"), assert = require("node:assert"), fs = require("fs"), path = require("path"), { execFileSync } = require("child_process");
const root = path.resolve(__dirname, ".."), X = require("../sim/xlsx-lite.js"), T = require("../sim/ispho-xlsx-templates.js");
const read = (f) => fs.readFileSync(path.join(root, f), "utf8");

test("formulas: arithmetic, ranges, fits and lookups as Excel works them out", () => {
  const wb = { sheets: [{ name: "Sheet1", cells: {}, cols: {}, charts: [] }, { name: "Data 2", cells: { A1: { v: 4 } }, cols: {}, charts: [] }] }, c = wb.sheets[0].cells;
  [[863, 620], [2105, 520], [2247, 460]].forEach(([n, l], i) => { c["A" + (i + 2)] = { v: n }; c["B" + (i + 2)] = { v: l }; });
  Object.assign(c, { D1: { f: "SLOPE(B2:B4,A2:A4)" }, D2: { f: "INTERCEPT(B2:B4,A2:A4)" }, D3: { f: "RSQ(B2:B4,A2:A4)" }, D4: { f: "INDEX(A2:A4,MATCH(MAX(B2:B4),B2:B4,0))" },
    D5: { f: "LN(B2)*2^2-10%" }, D6: { f: "1/0" }, D7: { f: "'Data 2'!A1+SUM(A2:A4)" }, D8: { f: "IF(D1<0,\"neg\",\"pos\")" }, D9: { f: "INDEX(LINEST(B2:B4,A2:A4),1,2)" }, D10: { f: "D10+1" }, D11: { f: "FOO(1)" } });
  X.calc(wb);
  assert.ok(Math.abs(c.D1.v - -0.1018232503) < 1e-9);
  assert.ok(Math.abs(c.D2.v - 710.3360834) < 1e-6);
  assert.ok(Math.abs(c.D3.v - 0.919941896) < 1e-8);
  assert.strictEqual(c.D4.v, 863);
  assert.ok(Math.abs(c.D5.v - (Math.log(620) * 4 - 0.1)) < 1e-12);
  assert.strictEqual(X.show(c.D6.v), "#DIV/0!");
  assert.strictEqual(c.D7.v, 4 + 863 + 2105 + 2247);
  assert.strictEqual(c.D8.v, "neg");
  assert.ok(Math.abs(c.D9.v - c.D2.v) < 1e-9);
  assert.strictEqual(X.show(c.D10.v), "#REF!");                    // circular
  assert.strictEqual(X.show(c.D11.v), "#NAME?");
  assert.strictEqual(X.shiftFormula("SUM(A2:$B$4)+Sheet1!C3*\"A1\"", 1, 2), "SUM(B4:$B$4)+Sheet1!D5*\"A1\"");
});

test("xlsx: a workbook with formulas and a log-axis scatter chart survives writing and reading", async () => {
  const wb = { sheets: [{ name: "Sheet1", cols: { 0: 12 }, charts: [], cells: { A1: { v: "U, V", b: true }, B1: { v: "I, mA", b: true }, A2: { v: 1.8 }, B2: { v: 0.05 }, A3: { v: 2.0 }, B3: { v: 0.4 }, A4: { v: 2.2 }, B4: { v: 3.9 }, C2: { f: "LN(B2)" } } }] };
  wb.sheets[0].charts.push({ type: "scatter", title: "I(U)", x: { title: "U, V" }, y: { title: "I, mA", log: true }, series: [{ name: "air", x: "Sheet1!$A$2:$A$4", y: "Sheet1!$B$2:$B$4", line: false, trend: "exp", eq: true, r2: true }], at: { c0: 4, r0: 1, c1: 12, r1: 16 } });
  const bytes = X.write(wb), back = await X.read(bytes), sh = back.sheets[0];
  assert.strictEqual(sh.cells.A1.v, "U, V"); assert.ok(sh.cells.A1.b === undefined || sh.cells.A1.b === true);
  assert.strictEqual(sh.cells.C2.f, "LN(B2)"); assert.ok(Math.abs(sh.cells.C2.v - Math.log(0.05)) < 1e-12);
  const ch = sh.charts[0];
  assert.deepStrictEqual([ch.type, ch.title, ch.y.log, ch.x.log, ch.series[0].trend, ch.series[0].eq, ch.series[0].r2, ch.series[0].y], ["scatter", "I(U)", true, false, "exp", true, true, "Sheet1!$A$2:$A$4".replace("A$2:$A$4", "B$2:$B$4")]);
  const text = X.toText(back, "B9-ans.xlsx");
  assert.match(text, /\[Spreadsheet file: B9-ans\.xlsx\]/);
  assert.match(text, /\{=LN\(B2\)\}/);
  assert.match(text, /Chart \(scatter\) "I\(U\)".*\(log scale\)/);
  assert.match(text, /trendline y = .*e\^.*R² = /);
  /* the same bytes every time: the zip files of the cards do not change on a rerun */
  assert.strictEqual(Buffer.compare(Buffer.from(X.write(wb)), Buffer.from(bytes)), 0);
});

test("CSV and long data: a spectrum is summarised around its peak for the grader", async () => {
  const csv = "N,I\n" + Array.from({ length: 3648 }, (_, i) => i + "," + Math.round(1000 * Math.exp(-(((i - 900) / 40) ** 2)))).join("\n");
  const text = await X.fileToText("R.csv", Buffer.from(csv), { maxRows: 60 });
  assert.match(text, /3649 rows × 2 columns/);
  assert.match(text, /B: 3648 numbers, min 0, max 1000 at row 902/);
  assert.match(text, /\n902\t900\t1000/);                     // the peak row itself is shown
  assert.ok(text.length < 8000);
  assert.deepStrictEqual(X.parseCsv('a;"b;c"\n1;2'), [["a", "b;c"], ["1", "2"]]);
  assert.match(await X.fileToText("B8_in.txt", Buffer.from("T\tB\n1000\t174")), /^\[Text file: B8_in\.txt\]\nT\tB/);
});

test("the tables ISPhO 2025 E1 names are all on the laptop, in their folders", () => {
  const paper = ["A2/A2-ans.xlsx", "A3/A3-sol.xlsx", "B1/B1-sol.xlsx", "B4/B4-ans.xlsx", "B7/B7-ans.xlsx", "B8/B8-low.xlsx", "B8/B8-high.xlsx", "B9/B9-ans.xlsx", "B14/B14-ans.xlsx",
    "C1/C1-ans.xlsx", "C2/C2-ans.xlsx", "C3/C3-ans.xlsx", "C6/C6-ans.xlsx", "D2/D2-ans.xlsx", "D3/D3-ans.xlsx", "D4/D4-low.xlsx", "D4/D4-high.xlsx", "D5/D5-ans.xlsx",
    "D8/D8-ans.xlsx", "D9/D9-ans.xlsx", "E4/E4-air.xlsx", "E4/E4-water.xlsx", "E5/E5.xlsx", "F1/F1-ans.xlsx", "F2/F2-ans.xlsx"];
  const p = T.pack("2025E1"), have = p.entries.filter((e) => e.wb).map((e) => e.path.replace(/^ISPhO\//, ""));
  assert.deepStrictEqual(have.slice().sort(), paper.slice().sort());
  for (const d of ["A1", "B12", "B13", "C4", "C5", "D1", "D7"]) assert.ok(p.entries.some((e) => e.dir && e.path === "ISPhO/" + d), d);   // the spectra's folders
  const b1 = p.entries.find((e) => /B1-sol/.test(e.path)).wb.sheets[0].cells;
  assert.deepStrictEqual(["A2", "A3", "A4", "A5", "A6"].map((k) => b1[k].v), ["600", "200", "20", "2", "200m"]);
  const r24 = T.pack("2024E1").entries.map((e) => e.path);
  for (const f of ["Results/Part A", "Results/Part D", "Results/Recalibrate", "Results/Report.xlsx", "Results/Calibration.xlsx"]) assert.ok(r24.includes(f), f);
  assert.deepStrictEqual(T.pack("2025T1").entries.filter((e) => e.wb).map((e) => e.path), ["report/B3.xlsx", "report/C2.xlsx", "report/C6.xlsx"]);
  execFileSync(process.execPath, [path.join(root, "tools/ispho_xlsx.cjs"), "--check"], { stdio: "pipe" });
});

test("the cards offer the tables; the simulators carry Excel; files are handed in and graded", () => {
  const index = read("index.html");
  assert.match(index, /data:"pdfx\/ispho\/ISPhO_2025_E1_tables\.zip"/);
  assert.match(index, /data:"pdfx\/ispho\/ISPhO_2024_E1_Results\.zip"/);
  assert.match(read("theory.js"), /ISPhO_2025_T1_report\.zip/);
  for (const f of ["sim/ispho2025_E1_web.html", "sim/ispho2024_E1_web.html"]) {
    const s = read(f);
    for (const src of ["xlsx-lite.js", "ispho-xlsx-templates.js", "vexcel.js"]) assert.ok(s.indexOf(`<script src="${src}`) >= 0 && s.indexOf(`<script src="${src}`) < s.indexOf('"use strict";'), f + " loads " + src + " before the laptop");
    assert.match(s, /window\.HL_EXAM_FILES=/);
    assert.match(s, /const START_APPS=\[[^\]]*"excel"/);
  }
  const exam = read("sim/exam.html");
  assert.match(exam, /<script src="xlsx-lite\.js\?v=/);
  assert.match(exam, /collectPcFiles\(id\);\n  \/\* switch the experiments off/);
  assert.match(exam, /api\("POST", `\/lab\/sessions\/\$\{id\}\/files`/);
  const worker = read("community/src/index.js");
  assert.match(worker, /\/api\\\/lab\\\/sessions\\\/\(\\d\+\)\\\/files\$/);
  assert.match(worker, /'data','text\/plain'/);
  assert.match(worker, /function labPageTag\(p\)/);
  /* typed answers never remove an attached file, and a phone's page limit does not count files */
  assert.match(worker, /DELETE FROM lab_pages WHERE session_id=\? AND task=\? AND mime='text\/plain' AND kind='answer'/);
  assert.match(worker, /FROM lab_pages WHERE session_id=\? AND kind<>'data'"\)\.bind\(s\.id\)\.first\(\);/);
});

test("the file box offers only the problems whose paper has files handed in, year by year, and shows a needed one first", () => {
  const vm = require("vm"), html = read("sim/exam.html");
  const begin = html.indexOf("const FILE_TASKS"), end = html.indexOf("function bindFilesBox", begin);
  const run = (c, y, tasks, review = true) => { const ctx = { EX: { c, y, tasks }, KEY: c + y, lang: "ko", REVIEW: review, esc: String };
    vm.createContext(ctx); vm.runInContext(html.slice(begin, end), ctx); return ctx; };
  const t26 = run("ispho", 2026, ["T1", "T2", "T3"]);
  assert.deepStrictEqual(t26.fileTasks(), ["T2"], "2026 theory: only T2 (its Part D data, optional)");
  assert.strictEqual(t26.filesNeeded(), false); assert.strictEqual(t26.filesNoteHtml(), "");
  assert.ok(!/id="fileTask"/.test(t26.filesBoxHtml()) && /T2/.test(t26.filesBoxHtml()), "one problem: no choice to make");
  const t25 = run("ispho", 2025, ["T1", "T2", "T3"]);
  assert.deepStrictEqual(t25.fileTasks(), ["T1"]); assert.strictEqual(t25.filesNeeded(), true);
  assert.match(t25.filesBoxHtml(), /class="files need"[^>]* open/); assert.match(t25.filesBoxHtml(), /B3 · C2 · C6/);
  assert.match(t25.filesNoteHtml(), /T1: 엑셀 파일 B3/);
  assert.deepStrictEqual(run("ispho", 2026, ["E1"]).fileTasks(), [], "2026 E1 hands in no files");
  assert.strictEqual(run("ispho", 2026, ["E1"]).filesBoxHtml(), "");
  assert.deepStrictEqual(run("ispho", 2024, ["E1"]).fileTasks(), ["E1"]);
  assert.deepStrictEqual(run("ipho", 2025, ["T1", "T2"]).fileTasks(), ["T1", "T2"], "elsewhere every problem may have files");
});
