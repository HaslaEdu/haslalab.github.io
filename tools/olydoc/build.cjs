/* Typeset HaslaLab's own olympiad documents (shortlist problems, unofficial solutions) as A4 PDFs in the layout
 * of a given edition's official papers.
 *
 *     node tools/olydoc/build.cjs tools/olydoc/docs/<spec>.cjs [...]
 *
 * A spec exports {docs:[{out, style, kind, lang, code, ...}]}: `out` is the PDF path (pdfx/<prefix>/…), `style` one of
 * STYLES below, `kind` paper | answer | solution | working, `code` the big corner label ("Q4", "T4", "AT4"…), and
 * `html` the body.  Mathematics is written as $…$ / $$…$$ and typeset by the vendored KaTeX; the fonts are the Noto
 * families in tools/ko/fonts, so the build is reproducible offline.  Answer and Working sheets carry the four black
 * scan squares where labscan/scanner.js looks for them (7 mm, centred 9.45 / 200.55 mm across, 10.4 / 286.6 mm
 * down — the same as sim/sheets.html), so a phone photograph is straightened from them.
 *
 * None of these documents carries an organiser's logo: each says in its footer that it is a HaslaLab edition and
 * where its content comes from. */
const fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const ROOT = path.resolve(__dirname, '../..');
const FONTS = path.join(ROOT, 'tools/ko/fonts');
const KATEX = path.join(ROOT, 'vendor/katex');
const url = p => 'file://' + p;

const fontFaces = `
@font-face{font-family:"HL Sans";src:url("${url(FONTS + '/NotoSans-Regular.ttf')}");font-weight:400}
@font-face{font-family:"HL Sans";src:url("${url(FONTS + '/NotoSans-Bold.ttf')}");font-weight:700}
@font-face{font-family:"HL Sans KR";src:url("${url(FONTS + '/NotoSansKR-Regular.ttf')}");font-weight:400}
@font-face{font-family:"HL Sans KR";src:url("${url(FONTS + '/NotoSansKR-Bold.ttf')}");font-weight:700}
@font-face{font-family:"HL Serif KR";src:url("${url(FONTS + '/NotoSerifKR-Regular.ttf')}");font-weight:400}`;

/* scan squares, drawn in the header (top pair) and footer (bottom pair) templates, which span the full page width */
const SQ = 'position:absolute;width:7mm;height:7mm;background:#000;-webkit-print-color-adjust:exact;print-color-adjust:exact';
const TOP_MARKS = `<div style="${SQ};left:5.95mm;top:6.9mm"></div><div style="${SQ};left:197.05mm;top:6.9mm"></div>`;
const BOTTOM_MARKS = `<div style="${SQ};left:5.95mm;bottom:6.9mm"></div><div style="${SQ};left:197.05mm;bottom:6.9mm"></div>`;

/* Each style: the page margins, and the header/footer printed on every page (Chromium's header templates run in
 * their own document: system fonts only — the Noto families are installed for the build, see README). */
const STYLES = {
  /* IPhO 2025 (France): «Theory» over the competition line at the left, the big «Q4-n» at the right, the language
     under it, a rule; no footer */
  ipho2025: {
    margin: { top: '44mm', bottom: '16mm', left: '18mm', right: '18mm' },
    header: d => `<div style="position:absolute;left:18mm;right:18mm;top:8mm;height:28mm;font-family:'Noto Sans','Noto Sans KR',sans-serif">
      <div style="position:absolute;left:0;right:0;bottom:-0.6mm;height:0.6mm;background:#000"></div>
      <div style="position:absolute;left:0;top:2mm;font-size:13pt;font-weight:700">${d.section || 'Theory'}</div>
      <div style="position:absolute;left:0;top:9mm;font-size:6.5pt;line-height:1.25;color:#e8505b;font-weight:700">International<br>Physics Olympiad<br>FRANCE 2025</div>
      <div style="position:absolute;right:0;top:3mm;font-size:34pt;font-weight:700;line-height:1">${d.code}${d.paged === false ? '' : '-<span class="pageNumber"></span>'}</div>
      <div style="position:absolute;right:0;bottom:1mm;font-size:8pt">${d.langLabel}</div></div>`,
    footer: d => `<div style="position:absolute;left:18mm;right:18mm;bottom:6mm;font-family:'Noto Sans','Noto Sans KR',sans-serif;font-size:6.5pt;color:#666;text-align:center">${d.credit}</div>`,
  },
  /* IPhO 2017 (Indonesia): «Theory» and the language at the left, «T4» / «AT4» at the right, «page n of N» below */
  ipho2017: {
    margin: { top: '30mm', bottom: '22mm', left: '20mm', right: '20mm' },
    header: d => `<div style="position:absolute;left:20mm;right:20mm;top:9mm;height:18mm;font-family:'DejaVu Sans','Noto Sans KR',sans-serif">
      <div style="position:absolute;left:0;top:0;font-size:12.5pt;font-weight:700">${d.section || 'Theory'}</div>
      <div style="position:absolute;left:0;top:6.5mm;font-size:8pt">${d.langLabel}</div>
      <div style="position:absolute;right:0;top:0;font-size:20pt">${d.code}</div></div>`,
    footer: d => `<div style="position:absolute;left:20mm;right:20mm;bottom:8mm;font-family:'DejaVu Sans','Noto Sans KR',sans-serif;font-size:7pt;text-align:center">
      <i>page <b class="pageNumber"></b> of <b class="totalPages"></b></i><div style="margin-top:1.5mm;font-size:6pt;color:#777">${d.credit}</div></div>`,
  },
  /* IPhO 2017 solutions: «Solutions/ Marking Scheme» and the problem at the right over a double rule */
  ipho2017sol: {
    margin: { top: '42mm', bottom: '22mm', left: '20mm', right: '20mm' },
    header: d => `<div style="position:absolute;left:20mm;right:20mm;top:11mm;height:19mm;font-family:Calibri,Carlito,'DejaVu Sans','Noto Sans KR',sans-serif">
      <div style="position:absolute;left:0;right:0;bottom:-1.6mm;height:0.5mm;background:#555"></div><div style="position:absolute;left:0;right:0;bottom:-0.6mm;height:0.3mm;background:#555"></div>
      <div style="position:absolute;left:0;top:2mm;font-size:13pt;font-weight:700;line-height:1.15">${d.section || 'Solutions/<br>Marking Scheme'}</div>
      <div style="position:absolute;right:0;top:1mm;font-size:22pt">${d.code}</div></div>`,
    footer: d => `<div style="position:absolute;left:20mm;right:20mm;bottom:8mm;border-top:0.3mm solid #999;padding-top:1.5mm;font-family:Calibri,Carlito,'DejaVu Sans','Noto Sans KR',sans-serif;font-size:7.5pt;text-align:center">
      <i>Page <span class="pageNumber"></span> of <span class="totalPages"></span></i><div style="margin-top:1mm;font-size:6pt;color:#777">${d.credit}</div></div>`,
  },
  /* APhO 2018 (Viet Nam): IPhO-2018-like oxygen layout — «Theory» and the competition at the left, «Q4-n» right */
  apho2018: {
    margin: { top: '44mm', bottom: '16mm', left: '18mm', right: '18mm' },
    header: d => `<div style="position:absolute;left:18mm;right:18mm;top:8mm;height:28mm;font-family:'Noto Sans','Noto Sans KR',sans-serif">
      <div style="position:absolute;left:0;right:0;bottom:-0.5mm;height:0.5mm;background:#000"></div>
      <div style="position:absolute;left:0;top:1mm;font-size:12pt;font-weight:700">${d.section || 'Theory'}</div>
      <div style="position:absolute;left:0;top:8mm;font-size:7pt;line-height:1.3"><b style="color:#b0302a">19<sup>th</sup> APhO</b><br>Asian Physics Olympiad<br>HANOI · VIET NAM 2018</div>
      <div style="position:absolute;right:0;top:4mm;font-size:32pt;font-weight:700;line-height:1">${d.code}${d.paged === false ? '' : '-<span class="pageNumber"></span>'}</div>
      <div style="position:absolute;right:0;bottom:1mm;font-size:8pt">${d.langLabel}</div></div>`,
    footer: d => `<div style="position:absolute;left:18mm;right:18mm;bottom:6mm;font-family:'Noto Sans','Noto Sans KR',sans-serif;font-size:6.5pt;color:#666;text-align:center">${d.credit}</div>`,
  },
  /* APhO 2018 solutions: a centred serif title block on the first page, «Page n» at the bottom */
  apho2018sol: {
    margin: { top: '16mm', bottom: '20mm', left: '18mm', right: '18mm' },
    header: () => '<div></div>',
    footer: d => `<div style="position:absolute;left:18mm;right:18mm;bottom:8mm;font-family:'Times New Roman','Liberation Serif','DejaVu Serif','Noto Serif KR',serif;font-size:9pt;text-align:center">
      Page <span class="pageNumber"></span><div style="font-family:'Noto Sans','Noto Sans KR',sans-serif;font-size:6pt;color:#777;margin-top:1mm">${d.credit}</div></div>`,
  },
};

const BASE_CSS = `
*{box-sizing:border-box}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{margin:0;color:#000;font-size:10pt;line-height:1.45}
p{margin:0 0 2.2mm}
h1{font-size:15pt;margin:0 0 3mm;color:#0b3d91}
h2{font-size:11.5pt;margin:5mm 0 2mm;color:#0b3d91}
h3{font-size:10pt;margin:3mm 0 1.5mm}
h1,h2,h3,.qh{break-after:avoid}
figure{margin:3mm 0;text-align:center}
figure img{max-width:100%}
figcaption{font-size:8.5pt;text-align:left;margin:1.5mm 8mm 0}
.q{display:grid;grid-template-columns:12mm 1fr 14mm;gap:0 3mm;border:0.3mm solid #444;padding:2.2mm 3mm;margin:3mm 0;break-inside:avoid}
.q>.l{font-weight:700}.q>.p{text-align:right;white-space:nowrap}
.sol{color:#d0021b;margin:2mm 0 1mm;break-inside:auto}
.sol .h{font-weight:700}
.box{border:0.3mm solid #d0021b;padding:0.3mm 1.2mm;display:inline-block}
.ms{margin:2mm auto 4mm;width:72%;border-collapse:collapse;font-size:8.8pt;break-inside:avoid}
.ms td{border:0.25mm solid #888;padding:0.8mm 2mm}.ms td:last-child{width:14mm;text-align:right}
.ms caption{text-align:left;font-weight:700;color:#d0021b;padding-bottom:1mm}
.ans{border:0.35mm solid #000;margin:0 0 3mm;break-inside:avoid}
.ans .t{display:flex;justify-content:space-between;border-bottom:0.3mm solid #000;padding:1mm 2mm;font-weight:700}
.ans .b{padding:2mm 3mm}
.ans .line{display:flex;align-items:flex-end;gap:2mm;margin-top:2mm}.ans .line i{flex:1;border-bottom:0.25mm solid #666;height:5mm}
.note{font-size:8.5pt;color:#333}
.credit{font-size:7.5pt;color:#555;margin-top:6mm;border-top:0.2mm solid #bbb;padding-top:1.5mm}
.katex{font-size:1.05em}`;

/* the body fonts of each style */
const BODY = {
  ipho2025: "font-family:'HL Sans','HL Sans KR',sans-serif",
  ipho2017: "font-family:'DejaVu Sans','HL Sans KR',sans-serif;font-size:9.6pt",
  ipho2017sol: "font-family:Calibri,Carlito,'HL Sans','HL Sans KR',sans-serif",
  apho2018: "font-family:'HL Sans','HL Sans KR',sans-serif;font-size:9.8pt",
  apho2018sol: "font-family:'Times New Roman','Liberation Serif','DejaVu Serif','HL Serif KR',serif;font-size:11pt",
};

/* «<» inside $…$ would open an HTML tag: escape it there (KaTeX reads the decoded text) */
const mathSafe = html => html.replace(/\$\$[\s\S]*?\$\$|\$[^$]*\$/g, m => m.replace(/</g, '&lt;').replace(/>/g, '&gt;'));

function page(doc) {
  return `<!doctype html><html lang="${doc.lang}"><head><meta charset="utf-8">
<link rel="stylesheet" href="${url(KATEX + '/katex.min.css')}">
<style>${fontFaces}${BASE_CSS}body{${BODY[doc.style]}}${doc.css || ''}</style>
<script src="${url(KATEX + '/katex.min.js')}"></script><script src="${url(KATEX + '/contrib/auto-render.min.js')}"></script>
</head><body>${mathSafe(doc.html)}
<script>renderMathInElement(document.body,{delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}],throwOnError:true});</script>
</body></html>`;
}

async function build(docs) {
  const browser = await chromium.launch();
  try {
    for (const doc of docs) {
      if (!STYLES[doc.style]) throw new Error('unknown style ' + doc.style);
      const s = STYLES[doc.style], ctx = await browser.newContext(), p = await ctx.newPage();
      const errors = [];
      p.on('pageerror', e => errors.push(String(e)));
      p.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
      const tmp = path.join(require('os').tmpdir(), 'olydoc-' + process.pid + '.html');
      fs.writeFileSync(tmp, page(doc));
      await p.goto(url(tmp), { waitUntil: 'load' });
      await p.evaluate(() => document.fonts.ready);
      for (const img of await p.$$eval('img', xs => xs.filter(x => !x.complete || !x.naturalWidth).map(x => x.src))) errors.push('image not loaded: ' + img);
      if (errors.length) throw new Error(doc.out + ': ' + errors.join('; '));
      const out = path.join(ROOT, doc.out);
      fs.mkdirSync(path.dirname(out), { recursive: true });
      const sheet = doc.kind === 'answer' || doc.kind === 'working';
      await p.pdf({ path: out, format: 'A4', printBackground: true, displayHeaderFooter: true,
        headerTemplate: `<div style="width:100%;height:100%;position:relative;margin:0;-webkit-print-color-adjust:exact">${sheet ? TOP_MARKS : ''}${s.header(doc)}</div>`,
        footerTemplate: `<div style="width:100%;height:100%;position:relative;margin:0;-webkit-print-color-adjust:exact">${sheet ? BOTTOM_MARKS : ''}${s.footer(doc)}</div>`, margin: doc.margin || s.margin });
      await ctx.close();
      console.log('built', doc.out);
    }
  } finally { await browser.close(); }
}

if (require.main === module) {
  const specs = process.argv.slice(2);
  if (!specs.length) { console.error('usage: node tools/olydoc/build.cjs <spec.cjs> [...]'); process.exit(2); }
  build(specs.flatMap(f => require(path.resolve(f)).docs)).catch(e => { console.error(e); process.exit(1); });
}
module.exports = { build, STYLES };
