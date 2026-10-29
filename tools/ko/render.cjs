// Render a translated solution to A4 PDF:  node tools/ko/render.cjs <body.html> <out.pdf> "<header text>"
// <body.html> holds only the body (h1, h2, p, figures, $math$); it is put into tools/ko/template.html, its math typeset
// with KaTeX (vendor/katex) and printed by Chromium with page numbers.  Figures are resolved next to <body.html>.
const { chromium } = require("playwright");
const fs = require("fs"), path = require("path");
(async () => {
  const [src, out, head] = process.argv.slice(2);
  const root = path.resolve(__dirname, "../.."), katex = "file://" + path.join(root, "vendor/katex");
  const tpl = fs.readFileSync(path.join(__dirname, "template.html"), "utf8").replace(/KATEX\//g, katex + "/");
  const html = tpl.replace("<!-- BODY -->", fs.readFileSync(src, "utf8"));
  const tmp = path.join(path.dirname(path.resolve(src)), ".render-" + path.basename(src));
  fs.writeFileSync(tmp, html);
  const br = await chromium.launch(), pg = await br.newPage();
  await pg.goto("file://" + tmp, { waitUntil: "networkidle" });
  await pg.addScriptTag({ path: path.join(root, "vendor/katex/katex.min.js") });
  await pg.addScriptTag({ path: path.join(root, "vendor/katex/contrib/auto-render.min.js") });
  const bad = await pg.evaluate(h => {
    document.getElementById("h1").textContent = h || "";
    const errs = [];
    renderMathInElement(document.body, { delimiters: [{ left: "$$", right: "$$", display: true }, { left: "\\[", right: "\\]", display: true }, { left: "$", right: "$", display: false }],
      throwOnError: false, errorCallback: (m, e) => errs.push(String(e).slice(0, 120)) });
    document.querySelectorAll(".katex-error").forEach(e => errs.push("katex: " + e.textContent.slice(0, 80)));
    return errs;
  }, head);
  await pg.evaluate(() => document.fonts.ready);
  await pg.pdf({ path: out, format: "A4", printBackground: true, displayHeaderFooter: true, headerTemplate: "<span></span>",
    footerTemplate: '<div style="font:8pt sans-serif;color:#666;width:100%;text-align:center"><span class="pageNumber"></span> / <span class="totalPages"></span></div>',
    margin: { top: "18mm", bottom: "20mm", left: "17mm", right: "17mm" } });
  await br.close(); fs.unlinkSync(tmp);
  if (bad.length) { console.error("math errors:\n" + bad.join("\n")); process.exitCode = 2; }
  console.log(out);
})();
