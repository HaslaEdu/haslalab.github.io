/* Small HTML builders shared by the document specs (tools/olydoc/docs/*.cjs). */
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

/* a question box as the paper prints it: label · text · points */
const q = (label, text, pts) => `<div class="q"><div class="l">${label}</div><div>${text}</div><div class="p">${pts}</div></div>`;
/* the solution under it, IPhO-2025 style (red), and its marking scheme */
const sol = (html, lang) => `<div class="sol"><span class="h">${lang === 'ko' ? '풀이' : 'SOLUTION'}:</span> ${html}</div>`;
const ms = (rows, lang) => `<table class="ms"><caption>${lang === 'ko' ? '채점 기준' : 'Marker Scheme'}</caption>${rows.map(([t, p]) => `<tr><td>${t}</td><td>${p.toFixed(1)}</td></tr>`).join('')}</table>`;
/* an answer box: its label, points and the lines on which the final answers go */
const ans = (label, pts, lines, unit = 'pt') => `<div class="ans"><div class="t"><span>${label}</span><span>${pts}${unit}</span></div><div class="b">${
  lines.map(l => `<div class="line"><span>${l}</span><i></i></div>`).join('')}<div style="height:${Math.max(8, 30 - lines.length * 7)}mm"></div></div></div>`;

/* a figure from tools/olydoc/img; `relabel` covers words printed in the image (e.g. Russian labels) with new text:
   [{x, y, w, h, text}] in percent of the image */
const path = require('path');
const fig = (file, caption, width = 100, relabel = []) => `<figure><div style="position:relative;display:inline-block;width:${width}%">
  <img src="file://${path.join(__dirname, 'img', file)}" style="width:100%;display:block">${relabel.map(r =>
    `<span style="position:absolute;left:${r.x}%;top:${r.y}%;width:${r.w}%;height:${r.h}%;background:#fff;display:flex;align-items:center;justify-content:${r.align || 'center'};font-size:${r.size || 9}pt;font-family:'HL Sans','HL Sans KR',sans-serif;white-space:nowrap">${r.text}</span>`).join('')}
</div>${caption ? `<figcaption>${caption}</figcaption>` : ''}</figure>`;

module.exports = { esc, q, sol, ms, ans, fig };
