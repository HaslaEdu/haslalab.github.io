#!/usr/bin/env node
/* Builds the HPhO sample papers from the Markdown-like sources described in FORMAT.md.
     node tools/hpho-mock/build.mjs mock-1 [T1 ...] [--lang ko|en]
   For each problem and language it writes <id>.pdf (problem, answer sheet, working sheets) and <id>-solution.pdf
   to hpho/samples/<set>/<lang>/. Pages are laid out by Chromium (Playwright) with KaTeX math; the running header
   carries the page label (Q1-2, A1-1, W1-3), the candidate code and the language, as on IPhO papers. */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';

const require = createRequire(import.meta.url);
const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../..');
const katex = require(path.join(ROOT, 'vendor/katex/katex.min.js'));
const {chromium} = require('playwright');
let QR = null;
try { QR = require('qrcode'); } catch { /* answer sheets are built without the QR code */ }

const LANG = {
  ko: {label: 'Korean (Republic of Korea)', code: 'KOR', pt: '점', theory: 'Theoretical Exam', experiment: 'Experimental Exam',
    back: '이 쪽의 뒷면에는 쓰지 마시오', caption: ''},
  en: {label: 'English (Official)', code: 'ENG', pt: 'pt', theory: 'Theoretical Exam', experiment: 'Experimental Exam',
    back: 'do not write on the back of this page', caption: ''}
};
const font = f => 'data:font/otf;base64,' + fs.readFileSync(path.join(ROOT, 'tools/ko/fonts', f)).toString('base64');
const FONTS = `@font-face{font-family:Paper;src:url(${font('NotoSansCJKkr-Regular.otf')});font-weight:400}
@font-face{font-family:Paper;src:url(${font('NotoSansCJKkr-Bold.otf')});font-weight:700}`;
const KATEX_CSS = fs.readFileSync(path.join(ROOT, 'vendor/katex/katex.min.css'), 'utf8')
  .replace(/url\(fonts\//g, 'url(file://' + path.join(ROOT, 'vendor/katex/fonts') + '/');
const LOGO = 'data:image/svg+xml;base64,' + fs.readFileSync(path.join(ROOT, 'logo/brand/hpho-wordmark-light.svg')).toString('base64');

const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const tex = (s, display) => katex.renderToString(s, {displayMode: display, throwOnError: true, strict: false, trust: false});
function inline(s, file) {
  /* $math$, **bold**, *italic*; everything else is text */
  let out = '', i = 0;
  while (i < s.length) {
    if (s[i] === '$') {
      const j = s.indexOf('$', i + 1);
      if (j < 0) throw new Error(`${file}: unclosed $ in: ${s}`);
      try { out += tex(s.slice(i + 1, j), false); } catch (e) { throw new Error(`${file}: KaTeX: ${e.message} in $${s.slice(i + 1, j)}$`); }
      i = j + 1; continue;
    }
    if (s.startsWith('**', i)) { const j = s.indexOf('**', i + 2); if (j > 0) { out += '<b>' + inline(s.slice(i + 2, j), file) + '</b>'; i = j + 2; continue; } }
    if (s[i] === '*' && s[i + 1] !== ' ') { const j = s.indexOf('*', i + 1); if (j > 0) { out += '<i>' + inline(s.slice(i + 1, j), file) + '</i>'; i = j + 1; continue; } }
    let j = i + 1; while (j < s.length && !'$*'.includes(s[j])) j++;
    out += esc(s.slice(i, j)); i = j;
  }
  return out;
}

export function parse(text, file = 'source') {
  const lines = text.replace(/\r/g, '').split('\n');
  const meta = {};
  let k = 0;
  for (; k < lines.length && lines[k].trim() !== '---'; k++) {
    const m = /^(\w+):\s*(.*)$/.exec(lines[k]); if (m) meta[m[1]] = m[2].trim();
  }
  if (k >= lines.length) throw new Error(`${file}: no front matter (end it with ---)`);
  const body = lines.slice(k + 1);
  /* fenced ::: blocks nest one level (a figure or table inside a question box) */
  function blocks(ls) {
    const out = []; let i = 0;
    const para = [];
    const flush = () => { if (para.length) { out.push({t: 'p', text: para.join(' ')}); para.length = 0; } };
    while (i < ls.length) {
      const line = ls[i], tr = line.trim();
      if (!tr) { flush(); i++; continue; }
      if (tr === '=== answer') { flush(); out.push({t: 'answer'}); i++; continue; }
      if (tr === '---page---') { flush(); out.push({t: 'page'}); i++; continue; }
      if (tr.startsWith(':::') && tr !== ':::') {
        flush();
        const head = tr.slice(3).trim().split(/\s+/), kind = head[0];
        let depth = 1, j = i + 1;
        for (; j < ls.length; j++) {
          const t = ls[j].trim();
          if (t.startsWith(':::') && t !== ':::') depth++;
          else if (t === ':::' && --depth === 0) break;
        }
        if (j >= ls.length) throw new Error(`${file}: ::: ${kind} opened at line ${i + k + 2} is not closed`);
        out.push({t: 'fence', kind, args: head.slice(1), raw: tr.slice(3).trim().slice(kind.length).trim(), lines: ls.slice(i + 1, j)});
        i = j + 1; continue;
      }
      if (tr.startsWith('$$')) {
        flush();
        let s = tr.slice(2), j = i;
        if (s.endsWith('$$') && s.length >= 2) s = s.slice(0, -2);
        else { j++; for (; j < ls.length && !ls[j].trim().endsWith('$$'); j++) s += '\n' + ls[j]; if (j >= ls.length) throw new Error(`${file}: unclosed $$ at line ${i + k + 2}`); s += '\n' + ls[j].trim().slice(0, -2); }
        out.push({t: 'eq', tex: s.trim()}); i = j + 1; continue;
      }
      const h = /^(#{2,4})\s+(.*)$/.exec(tr);
      if (h) { flush(); out.push({t: 'h' + h[1].length, text: h[2]}); i++; continue; }
      if (tr.startsWith('- ')) {
        flush(); const items = [];
        while (i < ls.length && ls[i].trim().startsWith('- ')) {
          let item = ls[i].trim().slice(2); i++;
          while (i < ls.length && /^\s{2,}\S/.test(ls[i]) && !ls[i].trim().startsWith('- ')) { item += ' ' + ls[i].trim(); i++; }
          items.push(item);
        }
        out.push({t: 'ul', items}); continue;
      }
      para.push(tr); i++;
    }
    flush(); return out;
  }
  return {meta, blocks: blocks(body)};
}

function render(bl, ctx) {
  const {file, dir} = ctx;
  return bl.map(b => {
    if (b.t === 'p') return `<p>${inline(b.text, file)}</p>`;
    if (b.t === 'eq') { try { return `<div class="eq">${tex(b.tex, true)}</div>`; } catch (e) { throw new Error(`${file}: KaTeX: ${e.message} in $$${b.tex}$$`); } }
    if (b.t === 'h2') return `<h2>${inline(b.text, file)}</h2>`;
    if (b.t === 'h3') return `<h3>${inline(b.text, file)}</h3>`;
    if (b.t === 'h4') return `<h4>${inline(b.text, file)}</h4>`;
    if (b.t === 'ul') return `<ul>${b.items.map(x => `<li>${inline(x, file)}</li>`).join('')}</ul>`;
    if (b.t === 'page') return '<div class="pb"></div>';
    if (b.t === 'answer') return '';
    if (b.t !== 'fence') throw new Error(`${file}: unknown block ${b.t}`);
    const inner = () => render(parseInner(b.lines, file), ctx);
    const rows = () => b.lines.filter(l => l.trim().startsWith('|')).map(l => l.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim()));
    const cap = () => { const c = b.lines.find(l => /^\s*Caption:/.test(l)); return c ? `<div class="cap">${inline(c.replace(/^\s*Caption:\s*/, ''), file)}</div>` : ''; };
    switch (b.kind) {
      case 'q': {
        const [label, pts] = b.args;
        return `<div class="qbox"><div class="ql">${esc(label)}</div><div class="qt">${inner()}</div><div class="qp">${esc(pts || '')}</div></div>`;
      }
      case 'a': {
        const [label, pts, h] = b.args;
        return `<div class="abox" style="min-height:${esc(h || '30mm')}"><div class="al"><b>${esc(label)}</b> <span>(${esc(pts || '')})</span></div><div class="at">${inner()}</div></div>`;
      }
      case 'table': {
        const r = rows();
        return `<figure class="tbl${b.args.includes('grid') ? ' grid' : ''}"><table>${r.map(cells => `<tr>${cells.map(c => `<td>${inline(c, file)}</td>`).join('')}</tr>`).join('')}</table>${cap()}</figure>`;
      }
      case 'marking': {
        const r = rows();
        return `<table class="mark">${r.map(([what, pts]) => `<tr><td>${inline(what, file)}</td><td class="mp">${esc(pts || '')}</td></tr>`).join('')}</table>`;
      }
      case 'figure': {
        const imgs = b.lines.map(l => /^\s*!\[(.*)\]\((\S+)(?:\s+(\d+%))?\)\s*$/.exec(l)).filter(Boolean);
        for (const m of imgs) if (!fs.existsSync(path.join(dir, m[2]))) throw new Error(`${file}: missing figure ${m[2]}`);
        return `<figure class="fig"><div class="row">${imgs.map(([, sub, src, w]) => `<div class="cell" style="width:${w || 'auto'}"><img src="file://${path.join(dir, src)}">${sub ? `<div class="sub">${inline(sub, file)}</div>` : ''}</div>`).join('')}</div>${cap()}</figure>`;
      }
      case 'box': return `<div class="box"><div class="bt">${inline(b.raw, file)}</div>${inner()}</div>`;
      case 'small': return `<div class="small">${inner()}</div>`;
      case 'intro': return `<div class="intro">${inner()}</div>`;
      default: throw new Error(`${file}: unknown fence ::: ${b.kind}`);
    }
  }).join('\n');
}
/* the blocks inside a box (a question, an answer box, a framed note); a table or figure nested in it keeps its own rows */
const parseInner = (lines, file) => parse('---\n' + lines.join('\n'), file).blocks;

const CSS = `${FONTS}${KATEX_CSS}

*{box-sizing:border-box}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{margin:0;font-family:Paper,sans-serif;font-size:9.6pt;line-height:1.5;color:#1a1a1a}
.katex{font-size:1.08em}
p{margin:0 0 7pt}
h1{font-size:15pt;color:#1515d8;margin:0 0 8pt;font-weight:700}
h2{font-size:10.5pt;color:#1515d8;margin:14pt 0 6pt;font-weight:700;break-after:avoid}
h3{font-size:10pt;color:#1515d8;margin:10pt 0 5pt;font-weight:700;break-after:avoid}
h4{font-size:9.6pt;color:#a08c0c;margin:10pt 0 5pt;font-weight:700;break-after:avoid;text-transform:uppercase}
ul{margin:0 0 7pt;padding-left:14pt}li{margin:0 0 2pt}
.eq{margin:4pt 0 8pt;text-align:center}
.qbox{display:grid;grid-template-columns:34pt 1fr 40pt;gap:8pt;border:1px solid #333;padding:7pt 9pt 3pt;margin:8pt 0 10pt;break-inside:avoid}
.ql{font-weight:700}.qp{text-align:right}
.abox{border:1px solid #333;padding:6pt 9pt;margin:0 0 8pt;break-inside:avoid}
.al{margin-bottom:6pt}.al span{font-size:9pt}.at{padding-left:8pt;color:#333}
.tbl{margin:10pt 0 12pt;text-align:center;break-inside:avoid}
.tbl table{margin:0 auto;border:1px solid #333;border-collapse:collapse;padding:6pt}
.tbl td{padding:2pt 12pt;text-align:left}
.tbl.grid td{border:1px solid #333;text-align:center}
.cap{font-size:8.6pt;margin-top:8pt;text-align:left;padding:0 16pt}
.cap b:first-child{font-weight:700}
.fig{margin:10pt 0 12pt;break-inside:avoid}
.fig .row{display:flex;justify-content:space-around;align-items:flex-end;gap:10pt}
.fig .cell{text-align:center}.fig img{max-width:100%;max-height:240mm}
.fig .sub{font-size:8.6pt;margin-top:4pt}
.box{border:1px solid #333;padding:8pt 10pt;margin:6pt 0 12pt}.bt{font-weight:700;margin-bottom:4pt}
.small{font-size:8.4pt;color:#555}
.intro{color:#1515d8;font-size:8.6pt}
.mark{width:84%;margin:4pt auto 12pt;border-collapse:collapse;break-inside:avoid}
.mark td{border:1px solid #333;padding:3pt 8pt}.mark td.mp{width:36pt;text-align:right;border-left:1px solid #333}
.pb{break-after:page}
.back{position:fixed;bottom:0}
`;

function header({kindLabel, code, big, color, langLabel, qr}) {
  return `<div style="width:100%;font-family:Paper,sans-serif;padding:0 15mm;-webkit-print-color-adjust:exact;position:relative;height:30mm;font-size:10px;color:#111">
  <style>${FONTS}</style>
  <div style="position:absolute;left:15mm;top:9mm;font-weight:700;font-size:15px">${esc(kindLabel)}</div>
  <img src="${LOGO}" style="position:absolute;left:15mm;top:15.5mm;height:11.5mm">
  ${qr ? `<img src="${qr}" style="position:absolute;left:92mm;top:2mm;height:17mm">` : ''}
  <div style="position:absolute;left:84mm;top:21.5mm;font-size:11.5px">${esc(code)}</div>
  <div style="position:absolute;right:15mm;top:6mm;font-weight:700;font-size:46px;line-height:1;color:${color}">${big}</div>
  <div style="position:absolute;right:15mm;top:22mm;font-size:11px">${esc(langLabel)}</div>
  <div style="position:absolute;left:15mm;right:15mm;top:28mm;border-bottom:1px solid #999"></div></div>`;
}

let tmpSeq = 0;
async function pdf(browser, html, opts) {
  const page = await browser.newPage();
  const tmp = path.join(os.tmpdir(), `hpho-mock-${process.pid}-${++tmpSeq}.html`);   /* one file per page set, so builds can run side by side */
  fs.writeFileSync(tmp, `<!doctype html><meta charset="utf-8"><style>${CSS}</style><body>${html}</body>`);
  await page.goto('file://' + tmp, {waitUntil: 'load'});
  await page.evaluate(() => document.fonts.ready);
  const buf = await page.pdf({format: 'A4', displayHeaderFooter: true, headerTemplate: opts.header, footerTemplate: opts.footer || '<span></span>',
    margin: {top: '34mm', bottom: '16mm', left: '15mm', right: '15mm'}, printBackground: true});
  await page.close(); fs.unlinkSync(tmp);
  return buf;
}
const pageNo = '<span class="pageNumber"></span>';

export async function build(set, only = [], langs = ['ko', 'en']) {
  const dir = path.join(HERE, set);
  const {PDFDocument} = await import('pdf-lib').catch(() => ({}));
  const browser = await chromium.launch();
  const made = [];
  try {
    for (const lang of langs) {
      const L = LANG[lang], out = path.join(ROOT, 'hpho/samples', set, lang);
      fs.mkdirSync(out, {recursive: true});
      /* the general instructions, one booklet per exam: G-theory.<lang>.md, G-experiment.<lang>.md */
      for (const g of fs.readdirSync(dir).filter(f => new RegExp(`^G-(theory|experiment)\\.${lang}\\.md$`).test(f)).sort()) {
        const id = g.split('.')[0];
        if (only.length && !only.includes(id)) continue;
        const src = parse(fs.readFileSync(path.join(dir, g), 'utf8'), g), m = src.meta;
        const kindLabel = m.kind === 'experiment' ? L.experiment : L.theory, T = m.kind === 'experiment' ? 'E' : 'T';
        const buf = await pdf(browser, `<h1>${inline(m.title, g)}</h1>` + render(src.blocks, {file: g, dir}),
          {header: header({kindLabel, code: `${L.code}-S-01 ${T}-0 G-0`, big: `G0-${pageNo}`, color: '#111', langLabel: L.label})});
        made.push(await join([buf], path.join(out, `${id}.pdf`), PDFDocument));
      }
      const files = fs.readdirSync(dir).filter(f => new RegExp(`^[TE]\\d+\\.${lang}\\.md$`).test(f)).sort();
      for (const f of files) {
        const id = f.split('.')[0];
        if (only.length && !only.includes(id)) continue;
        const src = parse(fs.readFileSync(path.join(dir, f), 'utf8'), f), m = src.meta;
        const T = m.kind === 'experiment' ? 'E' : 'T', no = m.no, code = (s) => `${L.code}-S-01 ${T}-${no} ${s}-${no}`;
        const kindLabel = m.kind === 'experiment' ? L.experiment : L.theory;
        const cut = src.blocks.findIndex(b => b.t === 'answer');
        const qb = cut < 0 ? src.blocks : src.blocks.slice(0, cut), ab = cut < 0 ? [] : src.blocks.slice(cut + 1);
        const title = `<h1>${inline(m.title, f)} (${esc(m.points)}${lang === 'ko' ? '점' : ' points'})</h1>`;
        const ctx = {file: f, dir};
        /* four files a problem: the problem (Q), the answer sheet (A), the writing sheets (W), the solution */
        made.push(await join([await pdf(browser, title + render(qb, ctx), {header: header({kindLabel, code: code('Q'), big: `Q${no}-${pageNo}`, color: '#111', langLabel: L.label})})], path.join(out, `${id}-question.pdf`), PDFDocument));
        if (ab.length) {
          const qr = QR ? await QR.toDataURL(`HPhO ${set} ${T}-${no} A`, {margin: 0, width: 160}) : null;
          made.push(await join([await pdf(browser, title + render(ab, ctx), {header: header({kindLabel, code: code('A'), big: `A${no}-${pageNo}`, color: '#111', langLabel: L.label, qr})})], path.join(out, `${id}-answer.pdf`), PDFDocument));
        }
        const nW = +(m.worksheets || 0);
        if (nW) {
          const blank = Array.from({length: nW}, (_, i) => `<div style="height:240mm"></div>${i < nW - 1 ? '<div class="pb"></div>' : ''}`).join('');
          made.push(await join([await pdf(browser, blank, {header: header({kindLabel, code: code('W'), big: `W${no}-${pageNo}`, color: '#111', langLabel: L.label}),
            footer: `<div style="width:100%;text-align:center;font-size:8px;color:#444;font-family:Paper,sans-serif"><style>${FONTS}</style>${esc(L.back)}</div>`})], path.join(out, `${id}-writing.pdf`), PDFDocument));
        }
        const sf = `${id}.sol.${lang}.md`;
        if (fs.existsSync(path.join(dir, sf))) {
          const s = parse(fs.readFileSync(path.join(dir, sf), 'utf8'), sf);
          const st = `<h1>${inline(s.meta.title || m.title, sf)} (${esc(m.points)}${lang === 'ko' ? '점' : ' points'})</h1>`;
          const buf = await pdf(browser, st + render(s.blocks, {file: sf, dir}), {header: header({kindLabel, code: code('Q'), big: `Q${no}-${pageNo}`, color: '#8f7f0b', langLabel: L.label})});
          made.push(await join([buf], path.join(out, `${id}-solution.pdf`), PDFDocument));
        }
      }
    }
  } finally { await browser.close(); }
  return made;
}

async function join(bufs, file, PDFDocument) {
  if (bufs.length === 1) { fs.writeFileSync(file, bufs[0]); return file; }
  if (PDFDocument) {
    const doc = await PDFDocument.create();
    for (const b of bufs) { const src = await PDFDocument.load(b); for (const p of await doc.copyPages(src, src.getPageIndices())) doc.addPage(p); }
    fs.writeFileSync(file, await doc.save()); return file;
  }
  /* without pdf-lib, join with pypdf */
  const {execFileSync} = await import('node:child_process');
  const tmps = bufs.map((b, i) => { const t = `${file}.part${i}.pdf`; fs.writeFileSync(t, b); return t; });
  execFileSync('python3', ['-I', '-c', 'import sys,pypdf\nw=pypdf.PdfWriter()\nfor f in sys.argv[2:]: w.append(f)\nw.write(sys.argv[1])', file, ...tmps]);
  tmps.forEach(t => fs.unlinkSync(t));
  return file;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2), set = args[0];
  if (!set) { console.error('usage: build.mjs <set> [ids...] [--lang ko|en]'); process.exit(2); }
  const li = args.indexOf('--lang'), langs = li >= 0 ? [args[li + 1]] : ['ko', 'en'];
  const ids = args.slice(1).filter((a, i, all) => a !== '--lang' && all[i - 1] !== '--lang');
  build(set, ids, langs).then(f => console.log(f.map(x => path.relative(ROOT, x)).join('\n'))).catch(e => { console.error(e.message); process.exit(1); });
}
