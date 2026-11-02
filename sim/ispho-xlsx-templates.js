/* ==========================================================================
   HaslaLab — the tables ISPhO hands out on the exam laptops, as workbooks
   --------------------------------------------------------------------------
   ISPhO 2025 E1 «LED colour» asks for its answers in tables that wait on
   the laptop in one folder per question (A2-ans.xlsx in A2, … F2-ans.xlsx
   in F2: Q1-6 – Q1-15 of the paper); ISPhO 2024 E1 has a «Results» folder
   with «Part A» … «Part D», «Recalibrate», a report and a calibration
   table; ISPhO 2025 T1 wants B3, C2 and C6 as Excel files in a «report»
   folder.  The papers name every file and say what goes in it; the columns
   below follow the papers and the official solutions (2025: table A2 has
   the colours, B1 the voltmeter ranges 600 V … 200 mV).  2024 E1's
   Report.docx and Calibration.docx are given as workbooks of the same
   tables (a graph is pasted in a row of the report as in the Word file).

   HLIsphoXlsx.pack(id) → { root, entries: [ { path, wb } | { path, dir: true } ] }
   for "2025E1", "2024E1" and "2025T1".  The simulators lay these out on
   their laptops (vexcel.js opens them); tools/ispho_xlsx.cjs writes them
   as the zip files the problem cards offer.
   ========================================================================== */
(function (root) {
  "use strict";
  const X = root.HLXlsx || (typeof require !== "undefined" ? require("./xlsx-lite.js") : null);
  /* a sheet: a bold header row, then rows (null leaves a cell empty) */
  function sheet(name, head, rows, widths) {
    const cells = {}, cols = {};
    head.forEach((h, c) => { cells[X.ref(c, 0)] = { v: h, b: true }; cols[c] = (widths && widths[c]) || Math.max(10, Math.min(28, String(h).length + 3)); });
    (rows || []).forEach((row, r) => row.forEach((v, c) => { if (v !== null && v !== undefined && v !== "") cells[X.ref(c, r + 1)] = { v }; }));
    return { name, cells, cols, charts: [] };
  }
  const book = (...sheets) => ({ sheets });
  const n = (k) => Array.from({ length: k }, (_, i) => [i + 1]);           /* a numbered column of k rows */
  const VV = (k) => sheet("Sheet1", ["No.", "V1, (unit)", "V2, (unit)"], n(k), [6, 14, 14]);
  const IU = (k) => sheet("Sheet1", ["No.", "I, mA", "U, V"], n(k), [6, 12, 12]);

  function pack2025E1() {
    const R = "ISPhO", e = [], dir = (d) => e.push({ path: R + "/" + d, dir: true }), file = (d, name, wb) => e.push({ path: R + "/" + d + "/" + name, wb });
    for (const d of ["A1", "A2", "A3", "B1", "B4", "B7", "B8", "B9", "B12", "B13", "B14", "C1", "C2", "C3", "C4", "C5", "C6",
      "D1", "D2", "D3", "D4", "D5", "D7", "D8", "D9", "E4", "E5", "F1", "F2"]) dir(d);
    file("A2", "A2-ans.xlsx", book(sheet("Sheet1", ["Color", "N"], [["Red"], ["Green"], ["Blue"]], [10, 10])));
    file("A3", "A3-sol.xlsx", book(sheet("Sheet1", ["Color", "λ, nm", "N"], [["Red", 620], ["Green", 520], ["Blue", 460], [], ["slope ="], ["shift ="]], [10, 10, 10])));
    file("B1", "B1-sol.xlsx", book(sheet("Sheet1", ["Range, V", "RV, MΩ"], [["600"], ["200"], ["20"], ["2"], ["200m"]], [10, 10])));
    file("B4", "B4-ans.xlsx", book(VV(10)));
    file("B7", "B7-ans.xlsx", book(VV(15)));
    file("B8", "B8-low.xlsx", book(IU(10)));
    file("B8", "B8-high.xlsx", book(IU(15)));
    file("B9", "B9-ans.xlsx", book(IU(25)));
    file("B14", "B14-ans.xlsx", book(sheet("Sheet1", ["t, s", "λ, nm"], [], [10, 10])));
    file("C1", "C1-ans.xlsx", book(VV(15)));
    file("C2", "C2-ans.xlsx", book(IU(15)));
    file("C3", "C3-ans.xlsx", book(sheet("Sheet1", ["I (air), mA", "U (air), V", "I (water), mA", "U (water), V"], [], [13, 13, 15, 15])));
    file("C6", "C6-ans.xlsx", book(sheet("Sheet1", ["t, s", "λ, nm"], [], [10, 10])));
    file("D2", "D2-ans.xlsx", book(VV(10)));
    file("D3", "D3-ans.xlsx", book(VV(15)));
    file("D4", "D4-low.xlsx", book(IU(10)));
    file("D4", "D4-high.xlsx", book(IU(15)));
    file("D5", "D5-ans.xlsx", book(IU(25)));
    file("D8", "D8-ans.xlsx", book(sheet("Sheet1", ["File", "I, mA", "λ, nm"], [], [16, 10, 10])));
    file("D9", "D9-ans.xlsx", book(sheet("Sheet1", ["I (air), mA", "λ (air), nm", "I (water), mA", "λ (water), nm", "I (N2), mA", "λ (N2), nm"], [], [13, 13, 15, 15, 13, 13])));
    file("E4", "E4-air.xlsx", book(sheet("Sheet1", ["t, s", "T, K"], [], [10, 10])));
    file("E4", "E4-water.xlsx", book(sheet("Sheet1", ["t, s", "T, K"], [], [10, 10])));
    file("E5", "E5.xlsx", book(sheet("air", ["t, s", "(linearized)"], [], [10, 16]), sheet("water", ["t, s", "(linearized)"], [], [10, 16])));
    file("F1", "F1-ans.xlsx", book(sheet("Sheet1", ["T, K", "ln(I0/mA)"], [], [10, 12])));
    file("F2", "F2-ans.xlsx", book(sheet("Sheet1", ["T, K", "ln(I0/mA)"], [], [10, 12])));
    return { root: R, entries: e };
  }
  function pack2024E1() {
    const R = "Results", e = [];
    for (const d of ["Part A", "Part B", "Part C", "Part D", "Recalibrate"]) e.push({ path: R + "/" + d, dir: true });
    /* Report.docx of the paper: one row per graph it asks for (B.7, C.7, C.8, D.3, D.5) and room for any other */
    const rows = [["IC-result", "B.7"], ...[1, 2, 3, 4, 5].map((i) => [`C-OH-${"x" + i}-t`, "C.7"]), ...[1, 2, 3, 4, 5].map((i) => [`C-OH-${"x" + i}-r`, "C.8"]),
      ...[1, 2, 3, 4].map((i) => [`IC-${i}-beta`, "D.3"]), ["IC-t", "D.5"], ["(other)", ""], ["(other)", ""]];
    e.push({ path: R + "/Report.xlsx", wb: book(sheet("Report", ["Row", "Question", "Graph (insert the chart beside its row; xN = the OH⁻ concentration, mol/l)"], rows, [14, 10, 70])) });
    e.push({ path: R + "/Calibration.xlsx", wb: book(sheet("Calibration", ["Calibration no.", "Questions done with it"], [[0, "all, unless listed below"], [1], [2], [3], [4]], [16, 50])) });
    return { root: R, entries: e };
  }
  function pack2025T1() {
    const R = "report", e = [{ path: R, dir: true }];
    e.push({ path: R + "/B3.xlsx", wb: book(sheet("B3", ["β", "d, a"], [], [10, 10])) });
    e.push({ path: R + "/C2.xlsx", wb: book(sheet("C2", ["b", "v", "φ"], [], [10, 10, 10])) });
    e.push({ path: R + "/C6.xlsx", wb: book(sheet("C6", ["t", "x (domain wall)"], [], [10, 16])) });
    return { root: R, entries: e };
  }
  const PACKS = { "2025E1": pack2025E1, "2024E1": pack2024E1, "2025T1": pack2025T1 };
  const api = { pack: (id) => PACKS[id] ? PACKS[id]() : null, ids: Object.keys(PACKS) };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.HLIsphoXlsx = api;
})(typeof window !== "undefined" ? window : globalThis);
