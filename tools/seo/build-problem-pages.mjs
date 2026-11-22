/* One static, indexable page per Learn problem, so a search for a problem can land on it: the site itself is a single page
   with hash routes, which a crawler cannot index one by one.
     /en/problems/<id>/  the exam-track problems (AP Physics 1 · 2 · C: Mechanics, JEE Main), written in English
     /ko/problems/<id>/  the competition problems transcribed in Korean (EuPhO, BAUPC, Eötvös, Physics Cup, WoPhO, OPhO)
   plus an index page per language and sitemap-learn.xml.
   Each page links into the interactive practice page (hints, grading, the AI tutor).
   usage: node tools/seo/build-problem-pages.mjs [--check] */
import fs from 'node:fs';
import path from 'node:path';
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../..');
const ORIGIN = 'https://haslalab.org';
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const json = f => JSON.parse(fs.readFileSync(path.join(root, f), 'utf8'));

/* the math stays as $…$ and is typeset in the browser by KaTeX's auto-render (pre-rendering it made the pages four
   times larger); a reader without script sees the LaTeX itself */
export const mathHtml = text => esc(text);
const paras = t => String(t ?? '').split(/\n{2,}/).map(p => `<p>${mathHtml(p).replace(/\n/g, '<br>')}</p>`).join('');
const plain = t => String(t ?? '').replace(/\$\$?([^$]+)\$\$?/g, (m, x) => x.replace(/\\[a-zA-Z]+/g, ' ').replace(/[{}^_\\]/g, '')).replace(/\s+/g, ' ').trim();
const describe = t => { const s = plain(t); return s.length > 155 ? s.slice(0, 152).replace(/\s\S*$/, '') + '…' : s; };

const T = {
  en: {site: 'HaslaLab', learn: 'Learn', all: 'All problems', solve: 'Solve it on HaslaLab and have your answer checked →', hints: 'Hints', hint: 'Hint',
    solution: 'Solution', answer: 'Answer', step: 'Step', choices: 'Choices', orig: 'Original problem written by HaslaLab in the style of the exam. AP and Advanced Placement are trademarks of College Board; HaslaLab is not affiliated with College Board or the NTA.',
    indexTitle: 'Physics practice problems: AP Physics 1, 2, C and JEE Main', indexLede: 'Original problems written in the style of each exam, with hints and worked solutions. On HaslaLab your answer is graded as soon as you submit it, and an AI tutor can help when you are stuck.'},
  ko: {site: 'HaslaLab', learn: '학습', all: '전체 문제', solve: '하슬라랩에서 풀고 스스로 채점하기 →', hints: '힌트', hint: '힌트', solution: '풀이', answer: '답', step: '단계', choices: '보기',
    orig: '각 대회의 공식 문제를 하슬라랩이 문항별로 옮겨 적고 번역한 것입니다. 원문과 다르면 공식 PDF를 기준으로 하세요.',
    indexTitle: '물리 대회 기출 문제: EuPhO · BAUPC · Eötvös · Physics Cup · WoPhO · OPhO', indexLede: '유럽 물리올림피아드와 여러 국제 물리 대회의 본선 문제를 문항마다 글과 그림으로 옮겨 적었습니다. 하슬라랩에서 풀고 풀이를 보며 스스로 채점합니다.'}
};
function page({lang, title, desc, canonical, body, alternates = []}) {
  return `<!doctype html>
<html lang="${lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)}</title>
<meta name="description" content="${esc(desc)}">
<link rel="canonical" href="${canonical}">
${alternates.map(([l, h]) => `<link rel="alternate" hreflang="${l}" href="${h}">`).join('\n')}
<meta property="og:title" content="${esc(title)}">
<meta property="og:description" content="${esc(desc)}">
<meta property="og:image" content="${ORIGIN}/og.png">
<link rel="icon" href="/logo/brand/haslalab-light.svg" type="image/svg+xml">
<link rel="stylesheet" href="/vendor/katex/katex.min.css">
<script defer src="/vendor/katex/katex.min.js"></script>
<script defer src="/vendor/katex/contrib/auto-render.min.js" onload="renderMathInElement(document.body,{delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}],throwOnError:false})"></script>
<style>
:root{color-scheme:light dark;--ink:#263247;--muted:#657187;--line:#d5dbe6;--paper:#fbfcfd;--accent:#7059a4}
@media(prefers-color-scheme:dark){:root{--ink:#ebe8f5;--muted:#aca6bd;--line:#3b344d;--paper:#111017;--accent:#bca0ed}}
body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.7 system-ui,-apple-system,"Segoe UI",Roboto,"Apple SD Gothic Neo","Noto Sans KR",sans-serif}
main{max-width:760px;margin:auto;padding:24px 16px 48px}a{color:var(--accent)}nav{font-size:14px;color:var(--muted)}h1{font-size:1.45rem;line-height:1.35;margin:10px 0 6px}
.meta{color:var(--muted);font-size:14px}.q{margin:18px 0}ol.ch{padding-left:1.4em}ol.ch li{margin:6px 0}
details{margin:12px 0;border:1px solid var(--line);border-radius:10px;padding:10px 14px}summary{cursor:pointer;font-weight:600}
.cta{display:inline-block;margin:18px 0;padding:11px 18px;border-radius:10px;background:var(--accent);color:#fff;text-decoration:none;font-weight:650}
figure{margin:12px 0;text-align:center}figure img{max-width:100%;height:auto;background:#fff;border-radius:6px}.note{font-size:12.5px;color:var(--muted);margin-top:28px}
ul.list{padding-left:1.2em}ul.list li{margin:4px 0}.katex-display{overflow-x:auto;overflow-y:hidden}
</style>
</head>
<body><main>
${body}
</main></body>
</html>
`;
}

export function build() {
  const files = new Map(), urls = [];
  /* exam tracks, in English */
  const tracks = json('practice/tracks.json').tracks, t = T.en;
  const index = [];
  for (const tr of tracks) {
    const items = json(`practice/track/${tr.key}.json`).items;
    const group = [];
    items.forEach((it, i) => {
      const syl = tr.syl.find(u => u.key === it.syl), loc = `${ORIGIN}/en/problems/${it.id}/`;
      const title = `${tr.name.en} · ${syl.name.en} — practice problem ${i + 1}`;
      const solve = `${ORIGIN}/?lang=en#/learn/practice?item=${it.id}`;
      const body = `<nav><a href="/?lang=en#/">${t.site} ${t.learn}</a> / <a href="/en/problems/">${t.all}</a> / ${esc(tr.name.en)}</nav>
<h1>${esc(title)}</h1><p class="meta">${esc(tr.name.en)} · ${esc(syl.name.en)} · ${t.step} ${it.step}</p>
<div class="q">${paras(it.q)}</div>
${it.type === 'mc' ? `<ol class="ch" type="A">${it.choices.map(c => `<li>${mathHtml(c)}</li>`).join('')}</ol>` : ''}
<a class="cta" href="${solve}">${t.solve}</a>
<details><summary>${t.hints}</summary>${it.hints.map((h, k) => `<p><b>${t.hint} ${k + 1}.</b> ${mathHtml(h)}</p>`).join('')}</details>
<details><summary>${t.solution}</summary>${paras(it.sol)}<p><b>${t.answer}:</b> ${it.type === 'mc' ? 'ABCDE'[it.answer] + '. ' + mathHtml(it.choices[it.answer]) : esc(`${it.answer.value} ${it.answer.unit}`.trim())}</p></details>
<p class="note">${t.orig}</p>`;
      files.set(`en/problems/${it.id}/index.html`, page({lang: 'en', title: `${title} | HaslaLab`, desc: describe(it.q), canonical: loc, body}));
      urls.push(loc);
      group.push(`<li><a href="/en/problems/${it.id}/">${esc(syl.name.en)} · ${i + 1}</a> <span class="meta">${t.step} ${it.step}</span></li>`);
    });
    index.push(`<h2>${esc(tr.name.en)}</h2><p class="meta">${esc(tr.blurb.en)}</p><ul class="list">${group.join('')}</ul>`);
  }
  files.set('en/problems/index.html', page({lang: 'en', title: `${t.indexTitle} | HaslaLab`, desc: t.indexLede, canonical: `${ORIGIN}/en/problems/`,
    body: `<nav><a href="/?lang=en#/">${t.site} ${t.learn}</a></nav><h1>${t.indexTitle}</h1><p>${t.indexLede}</p>${index.join('')}<p class="note">${t.orig}</p>`}));
  urls.push(`${ORIGIN}/en/problems/`);

  /* competition problems, transcribed in Korean */
  const k = T.ko, contests = json('practice/contests.json').contests, kindex = [];
  for (const c of contests) {
    const file = `practice/contest/${c.key}.json`;
    if (!fs.existsSync(path.join(root, file))) continue;
    const items = json(file).items, group = [];
    for (const it of items) {
      const slug = it.id.replace(/~/g, '-').toLowerCase(), loc = `${ORIGIN}/ko/problems/${slug}/`;
      const title = `${c.name.ko} ${it.year} ${it.key}${it.title ? ' · ' + it.title : ''}`;
      const text = it.b.filter(b => b.t).map(b => b.t).join('\n\n');
      const body = `<nav><a href="/?lang=ko#/">${k.site} ${k.learn}</a> / <a href="/ko/problems/">${k.all}</a> / ${esc(c.name.ko)}</nav>
<h1>${esc(title)}</h1><p class="meta">${esc(c.name.ko)} · ${it.year} · ${k.step} ${c.step}</p>
<div class="q">${it.b.map(b => b.f ? `<figure><img src="/practice/contest/fig/${encodeURIComponent(b.f)}" width="${b.w}" height="${b.h}" alt="" loading="lazy"></figure>` : paras(b.t)).join('')}</div>
<a class="cta" href="${ORIGIN}/?lang=ko#/learn/practice?mode=contest">${k.solve}</a>
<p class="note">${k.orig}</p>`;
      files.set(`ko/problems/${slug}/index.html`, page({lang: 'ko', title: `${title} | 하슬라랩`, desc: describe(text), canonical: loc, body}));
      urls.push(loc);
      group.push(`<li><a href="/ko/problems/${slug}/">${it.year} ${esc(it.key)}${it.title ? ' · ' + esc(it.title) : ''}</a></li>`);
    }
    kindex.push(`<h2>${esc(c.name.ko)}</h2><ul class="list">${group.join('')}</ul>`);
  }
  files.set('ko/problems/index.html', page({lang: 'ko', title: `${k.indexTitle} | 하슬라랩`, desc: k.indexLede, canonical: `${ORIGIN}/ko/problems/`,
    body: `<nav><a href="/?lang=ko#/">${k.site} ${k.learn}</a></nav><h1>${k.indexTitle}</h1><p>${k.indexLede}</p>${kindex.join('')}<p class="note">${k.orig}</p>`}));
  urls.push(`${ORIGIN}/ko/problems/`);

  files.set('sitemap-learn.xml', `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.map(u => `  <url><loc>${u}</loc></url>`).join('\n')}\n</urlset>\n`);
  return files;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const files = build();
  if (process.argv.includes('--check')) {
    const stale = [...files].filter(([f, v]) => !fs.existsSync(path.join(root, f)) || fs.readFileSync(path.join(root, f), 'utf8') !== v).map(([f]) => f);
    if (stale.length) { console.error(`${stale.length} problem pages are stale: run node tools/seo/build-problem-pages.mjs`); process.exit(1); }
    console.log('problem pages up to date', files.size);
  } else {
    for (const dir of ['en/problems', 'ko/problems']) fs.rmSync(path.join(root, dir), {recursive: true, force: true});
    for (const [f, v] of files) { fs.mkdirSync(path.dirname(path.join(root, f)), {recursive: true}); fs.writeFileSync(path.join(root, f), v); }
    console.log('pages', files.size);
  }
}
