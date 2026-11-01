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

module.exports = { esc, q, sol, ms, ans };
