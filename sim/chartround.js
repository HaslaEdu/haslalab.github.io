/* HaslaLab examination desk page — one page for a star-chart, observation-on-paper or data-analysis round,
   built from a description of the problems.  The left column holds the problem text, the middle the sheets
   (maps drawn from data, the examination's own figures, graph paper), the right the summary answer sheet,
   optionally a calculator, and the official (or, where none was published, HaslaLab's) solution on request.
   Uses chartlab.js and datadesk.js.

   ChartRound.page({
     key, assets,                       storage prefix, folder of the page's images
     title, sub, about: {ko, en},
     calc: true,                        show the scientific calculator
     maps: {id: {w, h, name, note, readout(x, y, lang), paint(g, W, H) | img | paper: {w_mm, h_mm, title, logy}}},
     tasks: [{id, marks, name, lead, parts: [{id, mk, ko, en, table, eq} | {h, ko, en, img, eq, table}],
              maps: [ids], fields: [[id, label, options]], table: {head, init},
              key: [[label, text | {ko, en}]], sol: [[image, caption] | {draw(g, W, H), w, h, cap}], solNote}]
   }) */
(function () {
  "use strict";
  const CSS = `
:root{--bg:#1c2027;--panel:#22262d;--ink:#e8eef2;--muted:#9aa3ab;--line:#33373e;--accent:#f2c14e;--accent-soft:#2b2f36;--deep:#12161b}
*{box-sizing:border-box}[hidden]{display:none!important}html,body{margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Apple SD Gothic Neo","Malgun Gothic",sans-serif}
.cr-head{max-width:1680px;margin:0 auto;padding:16px 12px 0;display:flex;justify-content:space-between;align-items:flex-end;gap:12px;flex-wrap:wrap}
.cr-head h1{margin:0;font-size:18px;font-weight:650;color:var(--accent)}.cr-head p{margin:3px 0 0;font-size:13px;color:var(--muted);max-width:1100px}
.cr-lang{display:flex;border:1px solid var(--line);border-radius:7px;overflow:hidden;background:var(--panel)}
.cr-lang button{margin:0;border:0;border-radius:0;padding:7px 15px;font-size:13px;font-weight:600;color:var(--muted);background:transparent;cursor:pointer}
.cr-lang button.on{background:var(--accent);color:#1c2027}
.cr-wrap{max-width:1680px;margin:0 auto;padding:12px 12px max(160px,24vh);display:flex;gap:12px;align-items:flex-start}
@media (max-width:1180px){.cr-wrap{flex-wrap:wrap}}
.cr-side{flex:0 0 370px;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px;position:sticky;top:12px;max-height:calc(100vh - 24px);overflow:auto}
.cr-ans{flex:0 0 310px}
@media (max-width:1180px){.cr-side{position:static;max-height:none;flex:1 1 100%}.cr-stage{order:-1}}
.cr-stage{flex:1 1 auto;min-width:0;display:flex;flex-direction:column;gap:10px}
.cr-card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px}.cr-card h3{margin:2px 0 8px;font-size:13px;font-weight:600;color:var(--muted)}
.cr-tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}
.cr-tabs button{margin:0;padding:7px 12px;font-size:13px;font-weight:650;border-radius:6px;border:1px solid var(--line);background:var(--accent-soft);color:var(--muted);cursor:pointer}
.cr-tabs button.on{background:var(--accent);border-color:var(--accent);color:#1c2027}
.cr-maps{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px}
.cr-maps button{margin:0;padding:5px 10px;font-size:12.5px;border-radius:6px;border:1px solid var(--line);background:#1a1d22;color:var(--muted);cursor:pointer}
.cr-maps button.on{border-color:var(--accent);color:var(--accent)}
.cr-q{font-size:13.3px;line-height:1.65;color:#d6dde2}
.cr-q h2{font-size:14px;color:var(--accent);margin:0 0 8px;display:flex;justify-content:space-between;gap:8px}
.cr-q .lead{color:#c3cbd2;margin:0 0 8px}.cr-q h4{color:#f3d58a;margin:12px 0 4px;font-size:13px}
.cr-q .part{background:var(--deep);border:1px solid var(--line);border-radius:6px;padding:8px 10px;margin:7px 0}
.cr-q .part b{color:#f3d58a}.cr-q .part .mk{float:right;color:var(--muted);font-size:12px;margin-left:6px}
.cr-q table{border-collapse:collapse;margin:6px 0;font-size:12.5px}.cr-q td,.cr-q th{border:1px solid #444a52;padding:2px 8px;text-align:center}
.cr-q .eq{font-family:"Cambria Math","Times New Roman",serif;font-size:14px;margin:4px 0 4px 10px;color:#e8eef2}
.cr-q img{display:block;max-width:100%;background:#fff;border-radius:4px;margin:6px 0}
.cr-side h2.t{font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:var(--accent);margin:4px 0 8px;padding-bottom:5px;border-bottom:1px solid var(--line)}
.cr-fld{margin:6px 0;display:grid;grid-template-columns:1fr 130px;gap:6px;align-items:center}.cr-fld label{font-size:12.3px;color:#c3cbd2}
.cr-fld input,.cr-fld select{width:100%;padding:5px 7px;border-radius:6px;border:1px solid var(--line);background:#14171c;color:var(--ink);font:13px ui-monospace,Consolas,monospace}
.cr-btn{width:100%;margin:8px 0 0;padding:8px;border-radius:6px;border:1px solid var(--line);background:var(--accent-soft);color:var(--ink);font:600 13px inherit;cursor:pointer}
.cr-btn:hover{border-color:var(--accent)}.cr-btn.on{background:var(--accent);color:#1c2027;border-color:var(--accent)}
.cr-hint{font-size:11.8px;color:var(--muted);line-height:1.6}
.cr-sol img,.cr-sol canvas{display:block;max-width:100%;border-radius:4px;background:#fff;margin:6px 0 2px}
.cr-sol .cap{font-size:12.5px;color:#c3cbd2;margin:10px 0 0}.cr-sol .note{font-size:12px;color:#f0c27a;margin:0 0 6px}
.cr-sol table{border-collapse:collapse;font-size:12.8px;margin:4px 0}.cr-sol td{border:1px solid #3a3f47;padding:3px 8px;vertical-align:top}.cr-sol td:first-child{color:#f3d58a;white-space:nowrap}
.cr-sheet{background:#fbfaf6;border-radius:6px;padding:8px 10px;color:#222;font:600 12px "Segoe UI","Malgun Gothic",sans-serif;margin-bottom:6px;display:flex;justify-content:space-between;gap:8px}
`;
  const UI = {
    ko: {ans: "요약 답안지", calc: "공학용 계산기", bSol: "해답 보기", bSolOff: "해답 숨기기", ansHint: "그린 것과 답안은 이 브라우저에 저장됩니다. 해답은 다 푼 뒤에 보세요.", marks: "점",
         sure: "해답을 볼까요? 시험처럼 풀어 보려면 먼저 끝까지 풀어 보세요.", solH: "해답", about: "이 시뮬레이터", tab: "계산표", none: "이 문제는 지도·종이에 그리는 것이 답입니다.",
         paperNote: "1 mm 모눈 · 축은 직접 그립니다"},
    en: {ans: "Summary answer sheet", calc: "Scientific calculator", bSol: "Show the solution", bSolOff: "Hide the solution", ansHint: "What you draw and write stays in this browser. Look at the solution only when you are done.", marks: "marks",
         sure: "Show the solution? To work it like the examination, finish first.", solH: "Solution", about: "About this simulator", tab: "Worksheet", none: "This problem is answered on the map or paper itself.",
         paperNote: "1 mm graph paper · draw your own axes"}
  };
  const store = {get(k) { try { return JSON.parse(localStorage.getItem(k) || "null"); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }};
  const tx = (v, L) => v == null ? "" : typeof v === "string" ? v : (v[L] || v.en || v.ko || "");

  function page(C) {
    const s = document.createElement("style"); s.textContent = CSS; document.head.appendChild(s);
    const Q = new URLSearchParams(location.search); let lang = Q.get("lang") === "en" ? "en" : "ko";
    const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
    const head = el("header", "cr-head"), hl = el("div"), h1 = el("h1"), sub = el("p"); hl.append(h1, sub);
    const lb = el("div", "cr-lang"), bko = el("button", "", "한국어"), ben = el("button", "", "English"); lb.append(bko, ben); head.append(hl, lb);
    const wrap = el("div", "cr-wrap"), left = el("aside", "cr-side"), tabs = el("div", "cr-tabs"), qBox = el("div", "cr-q"); left.append(tabs, qBox);
    const stage = el("div", "cr-stage"), mapCard = el("div", "cr-card"), maps = el("div", "cr-maps"), sheet = el("div", "cr-sheet"), mapName = el("span"), mapNote = el("span"), labs = el("div");
    sheet.append(mapName, mapNote); mapCard.append(maps, sheet, labs);
    const tabCard = el("div", "cr-card"), tabH = el("h3"), tabBox = el("div"); tabCard.append(tabH, tabBox);
    const solCard = el("div", "cr-card cr-sol"), solH = el("h3"), solBox = el("div"); solCard.append(solH, solBox); solCard.hidden = true;
    stage.append(mapCard, tabCard, solCard);
    const right = el("aside", "cr-side cr-ans"), calcH = el("h2", "t"), calcBox = el("div"), ansH = el("h2", "t"), ansBox = el("div"), bSol = el("button", "cr-btn"), ansHint = el("p", "cr-hint"), abH = el("h2", "t"), abP = el("p", "cr-hint");
    ansH.style.marginTop = "14px"; abH.style.marginTop = "16px";
    if (C.calc) right.append(calcH, calcBox); right.append(ansH, ansBox, bSol, ansHint, abH, abP);
    wrap.append(left, stage, right);
    const first = document.body.firstChild; document.body.insertBefore(wrap, first); document.body.insertBefore(head, wrap);
    if (C.calc) DataDesk.calc(calcBox, {lang: () => lang});
    const SK = C.key + "-answers", ANS = store.get(SK) || {}, LABS = {}, TABS = {}, IMGS = {};
    let cur = C.tasks[Math.max(0, C.tasks.findIndex((x) => x.id === Q.get("task")))], curMap = null, solOn = false;
    for (const id in C.maps) { const M = C.maps[id]; if (M.img) { const im = new Image(); im.onload = im.onerror = () => { if (curMap === id) showMap(id); }; im.src = C.assets + M.img; IMGS[id] = im; } }
    function sheetOf(id) {
      if (LABS[id]) return LABS[id]; const M = C.maps[id], host = document.createElement("div"); labs.appendChild(host);
      if (M.custom) LABS[id] = M.custom(host, () => lang);
      else if (M.paper) LABS[id] = DataDesk.paper(host, {key: C.key + "-" + id, lang: () => lang, title: M.paper.title, w_mm: M.paper.w_mm, h_mm: M.paper.h_mm, logy: M.paper.logy});
      else { const im = IMGS[id], paint = M.paint || ((g, W, H) => { g.fillStyle = "#fff"; g.fillRect(0, 0, W, H); if (im.complete && im.naturalWidth) g.drawImage(im, 0, 0, W, H); });
        const lab = ChartLab.create({el: host, w: M.w, h: M.h, paint, key: C.key + "-" + id, lang: () => lang, readout: M.readout && ((x, y) => M.readout(x, y, lang))}); LABS[id] = {lang: lab.lang, show: lab.show};
        /* a tall sheet is kept within the window's height; the wheel zooms in on it */
        if (M.h > M.w * 1.15) { const w = host.querySelector(".cl-wrap"); w.style.maxWidth = "max(340px, calc((100vh - 120px) * " + (M.w / M.h).toFixed(4) + "))"; w.style.margin = "0 auto"; w.style.width = "100%"; lab.layout(); } }
      return LABS[id]; }
    function showMap(id) { curMap = id; const M = C.maps[id];
      if (M.img && !(IMGS[id].complete && IMGS[id].naturalWidth)) return;
      maps.hidden = cur.maps.length < 2 && !!M.custom; sheet.hidden = !!M.custom;
      for (const k in LABS) LABS[k].show(k === id); sheetOf(id).show(true);
      mapName.textContent = tx(M.name, lang); mapNote.textContent = M.note ? tx(M.note, lang) : M.paper ? UI[lang].paperNote : "";
      for (const b of maps.querySelectorAll("button")) b.className = b.dataset.m === id ? "on" : ""; }
    function renderTask() {
      const L = lang, t = UI[L];
      tabs.innerHTML = C.tasks.map((x) => '<button data-t="' + x.id + '" class="' + (x === cur ? "on" : "") + '">' + x.id + "</button>").join("");
      tabs.hidden = C.tasks.length < 2;
      for (const b of tabs.querySelectorAll("button")) b.onclick = () => { cur = C.tasks.find((x) => x.id === b.dataset.t); solOn = false; renderTask(); };
      let h = "<h2><span>(" + cur.id + ") " + tx(cur.name, L) + "</span><span>" + (cur.marks ? "[" + cur.marks + " " + t.marks + "]" : "") + "</span></h2>" + (cur.lead ? '<p class="lead">' + tx(cur.lead, L) + "</p>" : "");
      const tbl = (T) => T ? "<table>" + T.map((r, i) => "<tr>" + r.map((c) => (i ? "<td>" : "<th>") + c + (i ? "</td>" : "</th>")).join("") + "</tr>").join("") + "</table>" : "";
      for (const p of cur.parts) {
        if (p.h) { h += "<h4>" + tx(p.h, L) + "</h4>" + (p.img ? '<img alt="" src="' + C.assets + p.img + '">' : "") + (p[L] ? '<p class="lead">' + p[L] + "</p>" : "") + (p.eq ? p.eq.map((e) => '<div class="eq">' + e + "</div>").join("") : "") + tbl(p.table); continue; }
        h += '<div class="part">' + (p.mk ? '<span class="mk">' + p.mk + "</span>" : "") + "<b>(" + p.id + ")</b> " + p[L];
        h += tbl(p.table);
        if (p.eq) h += p.eq.map((e) => '<div class="eq">' + e + "</div>").join("");
        h += "</div>"; }
      qBox.innerHTML = h;
      maps.innerHTML = cur.maps.map((m) => '<button data-m="' + m + '">' + tx(C.maps[m].name, L) + "</button>").join("");
      for (const b of maps.querySelectorAll("button")) b.onclick = () => showMap(b.dataset.m);
      showMap(cur.maps.includes(curMap) ? curMap : cur.maps[0]);
      tabCard.hidden = !cur.table; for (const k in TABS) TABS[k].show(k === cur.id);
      if (cur.table) { if (!TABS[cur.id]) { const host = document.createElement("div"); tabBox.appendChild(host);
          TABS[cur.id] = DataDesk.table(host, {key: C.key + "-tab-" + cur.id, lang: () => lang, rows: Math.max(14, (cur.table.init || []).length + 4), cols: cur.table.head.length, head: cur.table.head, init: cur.table.init}); }
        else TABS[cur.id].lang(); tabH.textContent = tx(cur.table.title, L) || t.tab; }
      ansBox.innerHTML = ""; const F = cur.fields || [];
      if (!F.length) ansBox.appendChild(el("p", "cr-hint", t.none));
      for (const [id, lab, opts] of F) { const d = el("div", "cr-fld"), l = el("label"); l.textContent = tx(lab, L); d.appendChild(l);
        const k = cur.id + "." + id;
        if (opts && opts.checks) { const box = el("div"); box.style.cssText = "display:flex;flex-direction:column;gap:2px"; const on = new Set((ANS[k] || "").split("|").filter(Boolean));
          for (const o of opts.checks) { const v = tx(o, "en"), lb = el("label"), cb = el("input"); cb.type = "checkbox"; cb.style.width = "auto"; cb.checked = on.has(v); lb.style.cssText = "display:flex;gap:6px;align-items:center;font-size:12.5px";
            cb.onchange = () => { cb.checked ? on.add(v) : on.delete(v); ANS[k] = [...on].join("|"); store.set(SK, ANS); }; lb.append(cb, document.createTextNode(tx(o, L))); box.appendChild(lb); }
          d.style.gridTemplateColumns = "1fr"; d.appendChild(box); ansBox.appendChild(d); continue; }
        let e; if (opts) { e = el("select"); e.innerHTML = '<option value="">—</option>' + opts.map((o) => "<option>" + tx(o, L) + "</option>").join(""); } else e = el("input");
        e.value = ANS[k] || ""; e.oninput = e.onchange = () => { ANS[k] = e.value; store.set(SK, ANS); }; e.onkeydown = (ev) => ev.stopPropagation(); d.appendChild(e); ansBox.appendChild(d); }
      renderSol(); history.replaceState(null, "", "?" + (C.tasks.length > 1 ? "task=" + cur.id + "&" : "") + (lang === "en" ? "lang=en" : "")); }
    function renderSol() { const t = UI[lang]; solCard.hidden = !solOn; if (C.onSol) C.onSol(solOn); bSol.textContent = solOn ? t.bSolOff : t.bSol; bSol.className = "cr-btn" + (solOn ? " on" : ""); if (!solOn) return;
      solBox.innerHTML = (cur.solNote ? '<p class="note">' + tx(cur.solNote, lang) + "</p>" : "") + (cur.key && cur.key.length ? "<table>" + cur.key.map(([k, v]) => "<tr><td>" + k + "</td><td>" + (typeof v === "function" ? v(lang, ANS) : tx(v, lang)) + "</td></tr>").join("") + "</table>" : "");
      for (const s of cur.sol || []) {
        if (Array.isArray(s)) { solBox.appendChild(el("p", "cap", tx(s[1], lang))); const im = el("img"); im.loading = "lazy"; im.alt = tx(s[1], lang); im.src = C.assets + s[0]; solBox.appendChild(im); }
        else { solBox.appendChild(el("p", "cap", tx(s.cap, lang))); const c = el("canvas"); c.width = s.w * 2; c.height = s.h * 2; c.style.width = s.w + "px"; const g = c.getContext("2d"); g.scale(2, 2);
          const go = () => s.draw(g, s.w, s.h, lang); if (s.needs && !(s.needs.complete && s.needs.naturalWidth)) s.needs.addEventListener("load", go); else go(); solBox.appendChild(c); } } }
    bSol.onclick = () => { if (!solOn && !confirm(UI[lang].sure)) return; solOn = !solOn; renderSol(); if (solOn) solCard.scrollIntoView({behavior: "smooth", block: "start"}); };
    function applyLang() { const t = UI[lang]; document.documentElement.lang = lang;
      h1.textContent = tx(C.title, lang); sub.textContent = tx(C.sub, lang); calcH.textContent = t.calc; ansH.textContent = t.ans; ansHint.textContent = t.ansHint; solH.textContent = tx(C.solTitle, lang) || t.solH;
      abH.textContent = t.about; abP.textContent = tx(C.about, lang); bko.className = lang === "ko" ? "on" : ""; ben.className = lang === "en" ? "on" : "";
      if (C.docTitle) document.title = tx(C.docTitle, lang);
      for (const k in LABS) LABS[k].lang(); renderTask(); }
    bko.onclick = () => { lang = "ko"; applyLang(); }; ben.onclick = () => { lang = "en"; applyLang(); };
    applyLang();
    return {lang: () => lang, answers: () => ANS, refreshSol: () => renderSol()};
  }
  window.ChartRound = {page};
})();
