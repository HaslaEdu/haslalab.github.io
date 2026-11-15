// Print an HTML file to PDF with Playwright's Chromium (build.py uses it where no desktop Chrome is installed).
//   node print_pw.cjs page.html out.pdf
const { chromium } = require("playwright");
(async () => {
  const [src, out] = process.argv.slice(2);
  const br = await chromium.launch(), pg = await br.newPage();
  await pg.goto("file://" + require("path").resolve(src), { waitUntil: "networkidle" });
  await pg.evaluate(() => document.fonts.ready);
  await pg.pdf({ path: out, printBackground: true, preferCSSPageSize: true });
  await br.close();
})().catch(e => { console.error(e); process.exit(1); });
