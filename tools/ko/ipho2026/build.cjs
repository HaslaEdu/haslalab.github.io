// IPhO 2026 theory papers in Korean, in the layout of the official English booklet page for page.
//   node tools/ko/ipho2026/build.cjs [T1 T2 T3]   ->  pdfx/ipho/IPhO_2026_T<n>_KO.pdf
// T<n>.html holds one <section class="page" data-n="..."> per booklet page. Every block is placed at the position of
// its English counterpart (in pt, measured on the booklet: --y the top of the first line, --x/--w the column); figures
// and the logo are the booklet's own images. KaTeX at its default size as in the booklet. The build stops when a block
// runs into the next one or below the footer.
const { chromium } = require("playwright");
const fs = require("fs"), path = require("path");
const here = __dirname, root = path.resolve(here, "../../.."), katex = "file://" + path.join(root, "vendor/katex");
const gs = "https://fonts.gstatic.com/s/";
const face = (fam, w, st, url) => `@font-face{font-family:"${fam}";font-weight:${w};font-style:${st};src:url(${gs}${url}) format("truetype")}`;
const css = `
${face("Noto Sans", 400, "normal", "notosans/v42/o-0mIpQlx3QUlC5A4PNB6Ryti20_6n1iPHjcz6L1SoM-jCpoiyD9A99d.ttf")}
${face("Noto Sans", 700, "normal", "notosans/v42/o-0mIpQlx3QUlC5A4PNB6Ryti20_6n1iPHjcz6L1SoM-jCpoiyAaBN9d.ttf")}
${face("Noto Sans", 400, "italic", "notosans/v42/o-0kIpQlx3QUlC5A4PNr4C5OaxRsfNNlKbCePevHtVtX57DGjDU1QDce6Vc.ttf")}
${face("Noto Sans", 700, "italic", "notosans/v42/o-0kIpQlx3QUlC5A4PNr4C5OaxRsfNNlKbCePevHtVtX57DGjDU1QNAZ6Vc.ttf")}
${face("Noto Sans KR", 400, "normal", "notosanskr/v40/PbyxFmXiEBPT4ITbgNA5Cgms3VYcOA-vvnIzzuoyeLQ.ttf")}
${face("Noto Sans KR", 700, "normal", "notosanskr/v40/PbyxFmXiEBPT4ITbgNA5Cgms3VYcOA-vvnIzzg01eLQ.ttf")}
@page{size:612pt 792pt;margin:0}
*{box-sizing:border-box}
body{margin:0;font:10.5pt/15pt "Noto Sans","Noto Sans KR",sans-serif;color:#000;word-break:keep-all}
.page{position:relative;width:612pt;height:792pt;overflow:hidden;break-after:page}
.logo{position:absolute;left:50pt;top:6pt;width:100pt;height:100pt}
.hd{position:absolute;right:50pt;top:45pt;text-align:right;font:700 10pt/15pt "Liberation Sans",Arial,"Noto Sans KR",sans-serif}
.ft{position:absolute;left:50pt;right:50pt;top:743.6pt;display:flex;justify-content:space-between;font:700 10pt/12pt "Liberation Sans",Arial,sans-serif}
.rule{position:absolute;left:0;width:612pt;height:2pt;background:#000}
.a{position:absolute;left:calc(var(--x,54)*1pt);top:calc(var(--y)*1pt - 2.6pt);width:calc(var(--w,504)*1pt);margin:0;text-align:justify}
h1.a{font-size:21pt;line-height:25pt;top:calc(var(--y)*1pt - 2.4pt);color:#236fa1;font-weight:700;text-align:left}
h3.a{font-size:12.28pt;line-height:16pt;top:calc(var(--y)*1pt - 1.9pt);color:#236fa1;font-weight:700;text-align:left}
img.a{top:calc(var(--y)*1pt);height:calc(var(--h)*1pt)}
.cap{text-align:center}.mono{font-family:"Liberation Mono","Noto Sans KR",monospace}
.eq{text-align:center}.eq .katex-display{margin:0}
.box{position:absolute;left:54pt;width:calc(var(--w,504)*1pt);top:calc(var(--y)*1pt);height:calc(var(--h)*1pt);border:.75pt solid #ccc;
     padding:calc((var(--t) - var(--y))*1pt - 2.6pt) 5.5pt 0;text-align:justify}
.box p{margin:0 0 6pt}
p.a+p.a{margin-top:0}
.katex{font-size:1.21em}
table.a{border-collapse:collapse;top:calc(var(--y)*1pt);table-layout:fixed}
table.a td,table.a th{border:.75pt solid #ccc;text-align:center;vertical-align:middle;padding:0 4pt;line-height:14pt}
table.a th{font-weight:700}
`;
const which = process.argv.slice(2).length ? process.argv.slice(2) : ["T1", "T2", "T3"];
(async () => {
  const br = await chromium.launch();
  let bad = 0;
  for (const t of which) {
    const body = fs.readFileSync(path.join(here, t + ".html"), "utf8");
    const pages = body.replace(/<section class="page" data-n="(\d+)">/g, (_, n) =>
      `<section class="page"><img class="logo" src="logo.png"><div class="hd">Theoretical Exam -- Korean (Korea (Republic of))<br>Page ${n} of 14</div>` +
      `<div class="rule" style="top:106pt"></div><div class="rule" style="top:731pt"></div><div class="ft"><span>IPhO 2026</span><span>30 points | 5.0 hours</span></div>`);
    const html = `<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><link rel="stylesheet" href="${katex}/katex.min.css"><style>${css}</style></head><body>${pages}</body></html>`;
    const tmp = path.join(here, ".build-" + t + ".html");
    fs.writeFileSync(tmp, html);
    const pg = await br.newPage();
    await pg.goto("file://" + tmp, { waitUntil: "networkidle" });
    await pg.addScriptTag({ path: path.join(root, "vendor/katex/katex.min.js") });
    await pg.addScriptTag({ path: path.join(root, "vendor/katex/contrib/auto-render.min.js") });
    const errs = await pg.evaluate(() => {
      const e = [];
      renderMathInElement(document.body, { delimiters: [{ left: "$$", right: "$$", display: true }, { left: "$", right: "$", display: false }],
        throwOnError: false, errorCallback: (m, x) => e.push(String(x).slice(0, 120)) });
      document.querySelectorAll(".katex-error").forEach(x => e.push("katex: " + x.textContent.slice(0, 80)));
      return e;
    });
    await pg.evaluate(() => document.fonts.ready);
    // overlap check: blocks in order of their top must not run into the next block, nor below the footer rule
    const clash = await pg.evaluate(() => {
      const out = [], pt = 0.75;
      document.querySelectorAll(".page").forEach((p, i) => {
        const P = p.getBoundingClientRect();
        const bs = [...p.querySelectorAll(".a,.box")].map(el => {
          const r = el.getBoundingClientRect();
          let bottom = r.bottom;
          if (el.classList.contains("box")) bottom = Math.max(...[...el.children].map(c => c.getBoundingClientRect().bottom), r.top) + 2;
          return { el, top: (r.top - P.top) * pt, bottom: (bottom - P.top) * pt, left: (r.left - P.left) * pt, right: (r.right - P.left) * pt,
                   full: el.classList.contains("box") ? (r.bottom - P.top) * pt : null, name: (el.textContent || el.getAttribute("src") || "").trim().slice(0, 30) };
        });
        for (const b of bs) {
          if (b.bottom > 728) out.push(`page ${i + 1}: «${b.name}» ends at ${b.bottom.toFixed(1)}pt, below the footer`);
          if (b.full != null && b.bottom > b.full) out.push(`page ${i + 1}: «${b.name}» overflows its box by ${(b.bottom - b.full).toFixed(1)}pt`);
          for (const c of bs) if (c !== b && c.top > b.top && c.top < b.bottom - 1 && c.left < b.right - 1 && c.right > b.left + 1 && !(b.el.contains(c.el)))
            out.push(`page ${i + 1}: «${b.name}» (to ${b.bottom.toFixed(1)}pt) runs into «${c.name}» (at ${c.top.toFixed(1)}pt)`);
        }
      });
      return out;
    });
    const out = path.join(root, "pdfx/ipho/IPhO_2026_" + t + "_KO.pdf");
    await pg.pdf({ path: out, width: "8.5in", height: "11in", printBackground: true, preferCSSPageSize: true });
    await pg.close(); fs.unlinkSync(tmp);
    for (const m of [...errs, ...clash]) { console.error(t + ": " + m); bad++; }
    console.log(out);
  }
  await br.close();
  if (bad) process.exitCode = 2;
})();
