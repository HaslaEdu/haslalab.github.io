#!/usr/bin/env node
/* The ISPhO answer tables as zip files for the problem cards (sim/ispho-xlsx-templates.js says what is in them):
     pdfx/ispho/ISPhO_2025_E1_tables.zip   the folders A1 … F2 with A2-ans.xlsx … F2-ans.xlsx
     pdfx/ispho/ISPhO_2024_E1_Results.zip  «Results» with Part A–D, Recalibrate, Report.xlsx, Calibration.xlsx
     pdfx/ispho/ISPhO_2025_T1_report.zip   «report» with B3.xlsx, C2.xlsx, C6.xlsx
   The files come out the same every time (fixed zip dates), so a rerun changes nothing.
     node tools/ispho_xlsx.cjs [--check] */
const fs = require("fs"), path = require("path");
const X = require("../sim/xlsx-lite.js"), T = require("../sim/ispho-xlsx-templates.js");
const OUT = { "2025E1": "pdfx/ispho/ISPhO_2025_E1_tables.zip", "2024E1": "pdfx/ispho/ISPhO_2024_E1_Results.zip", "2025T1": "pdfx/ispho/ISPhO_2025_T1_report.zip" };
const root = path.resolve(__dirname, ".."), check = process.argv.includes("--check");
let stale = 0;
for (const id of T.ids) {
  const p = T.pack(id), entries = p.entries.map((e) => e.dir ? { name: e.path + "/", data: new Uint8Array(0) } : { name: e.path, data: X.write(e.wb) });
  const bytes = X.zip(entries), file = path.join(root, OUT[id]);
  const same = fs.existsSync(file) && Buffer.compare(fs.readFileSync(file), Buffer.from(bytes)) === 0;
  if (check) { if (!same) { console.error("stale: " + OUT[id]); stale++; } continue; }
  if (!same) fs.writeFileSync(file, bytes);
  console.log(OUT[id] + ": " + p.entries.filter((e) => !e.dir).length + " tables, " + bytes.length + " bytes" + (same ? " (unchanged)" : ""));
}
if (stale) process.exit(1);
