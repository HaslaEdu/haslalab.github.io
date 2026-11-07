/* HaslaLab: things that make the site quicker to get around.
   - the home page: four large ways in (experiments, past papers, the monthly problem, the AI) and "continue"
     with the sims last opened on this device (sim/simfull.js keeps that list);
   - search from anywhere (Ctrl+K, ⌘K or /): competitions, years, experiments, theory papers and the main pages;
   - on a year's page, the experiments opened before on this device are marked "done", with a filter;
   - on phones, the main menu moves to a bar at the bottom of the screen.
   index.html's render() calls HL_UX.afterRender(first, second) after every page it draws. */
(() => {
  const L = () => (typeof lang === "string" && lang === "en") ? "en" : "ko";
  const TX = {
    ko: { exp: "실험하기", expB: "가상 실험대 열기", expS: n => `대회·연도별 실험 ${n}개`, thy: "기출 풀기", thyB: "대회·연도별 이론", thyS: "문제지·해설·답안지, 실전 모드",
          mon: "월별문제", monB: "이번 달 문제", monS: "매달 새 문제 · 랭킹", ai: "AI에게 묻기", aiB: "하슬라 AI", aiS: "개념·풀이·사이트 사용법",
          cont: "이어서 하기", contGo: "이어서 →", last: "마지막으로 연 실험", also: "최근", search: "검색", ph: "대회, 연도, 실험, 이론 문제, 메뉴 검색…",
          none: q => `"${q}"에 맞는 결과가 없습니다. 대회 이름(IPhO)이나 연도(2017)로 찾아보세요.`, nav: "↑↓ 이동", open: "Enter 열기", esc: "Esc 닫기",
          kind: { comp: "대회", year: "연도", exp: "실험", thy: "이론", page: "메뉴", recent: "최근" },
          done: "해 봄", all: "전체", todo: "안 해 본 것만", ago: t => { const m = Math.round((Date.now() - t) / 60000); return m < 60 ? `${Math.max(1, m)}분 전` : m < 1440 ? `${Math.round(m / 60)}시간 전` : `${Math.round(m / 1440)}일 전`; },
          pages: [["홈", "#/"], ["아카이브 · 대회 목록", "#/comps"], ["학습", "#/learn"], ["문제 검색", "#/learn/physics/search"], ["문제 제작소", "#/learn/physics/studio"],
                  ["월별문제", "#/monthly"], ["랭킹", "#/rank"], ["커뮤니티", "#/community"], ["소개", "#/about"], ["로그인", "#/login"], ["내 정보", "#/me"]] },
    en: { exp: "Experiments", expB: "Open a virtual bench", expS: n => `${n} experiments by competition and year`, thy: "Past papers", thyB: "Theory by competition", thyS: "Papers, solutions, answer sheets, exam mode",
          mon: "Monthly problem", monB: "This month's problem", monS: "A new problem each month · ranking", ai: "Ask the AI", aiB: "Hasla AI", aiS: "Concepts, solutions, using the site",
          cont: "Continue", contGo: "Continue →", last: "Last opened", also: "Recent", search: "Search", ph: "Search competitions, years, experiments, theory, pages…",
          none: q => `Nothing matches "${q}". Try a competition (IPhO) or a year (2017).`, nav: "↑↓ move", open: "Enter open", esc: "Esc close",
          kind: { comp: "Comp", year: "Year", exp: "Exp", thy: "Theory", page: "Page", recent: "Recent" },
          done: "Done", all: "All", todo: "Not tried yet", ago: t => { const m = Math.round((Date.now() - t) / 60000); return m < 60 ? `${Math.max(1, m)} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} d ago`; },
          pages: [["Home", "#/"], ["Archive · competitions", "#/comps"], ["Learn", "#/learn"], ["Search problems", "#/learn/physics/search"], ["Problem Studio", "#/learn/physics/studio"],
                  ["Monthly problem", "#/monthly"], ["Ranking", "#/rank"], ["Community", "#/community"], ["About", "#/about"], ["Sign in", "#/login"], ["My page", "#/me"]] }
  };
  const T = () => TX[L()];
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const recent = () => { try { const v = JSON.parse(localStorage.getItem("hl-recent-sims") || "[]"); return Array.isArray(v) ? v.filter(r => r && r.file && /^[\w.-]+\.html$/.test(r.file)) : []; } catch (e) { return []; } };
  const simHref = file => `sim/${file}?lang=${L()}`;
  const hasData = () => typeof DATA === "object" && DATA;
  const shown = k => typeof compShown !== "function" || compShown(k);

  /* ── the home page ── */
  function liveCount() {
    let n = 0; if (!hasData()) return n;
    for (const [k, c] of Object.entries(DATA)) if (shown(k)) for (const y of c.years) n += y.problems.filter(p => !p.hold && p.files && p.files.sim).length;
    return n;
  }
  function home() {
    const cover = document.querySelector(".hl-home-cover"); if (!cover || document.querySelector(".hlx-actions")) return;
    const t = T(), cta = cover.querySelector(".cta"); if (cta) cta.remove();
    const wrap = document.createElement("div"); wrap.className = "hlx-home";
    wrap.innerHTML = `<div class="hlx-actions" role="navigation" aria-label="${t.exp} · ${t.thy} · ${t.mon} · ${t.ai}">
      <a href="#/comps" data-k="exp"><i>${t.exp}</i><b>${t.expB}</b><small>${t.expS(liveCount())}</small></a>
      <a href="#/comps" data-k="thy"><i>${t.thy}</i><b>${t.thyB}</b><small>${t.thyS}</small></a>
      <a href="#/monthly"><i>${t.mon}</i><b>${t.monB}</b><small>${t.monS}</small></a>
      <a href="#" data-k="ai"><i>${t.ai}</i><b>${t.aiB}</b><small>${t.aiS}</small></a></div>`;
    const r = recent();
    if (r.length) {
      const [a, ...more] = r;
      wrap.insertAdjacentHTML("beforeend", `<div class="hlx-cont"><div class="m"><b>${t.cont} · ${esc(a.title)}</b><span>${t.last} · ${t.ago(a.t)}</span></div>
        ${more.length ? `<div class="more"><span>${t.also}</span>${more.slice(0, 2).map(x => `<a href="${simHref(x.file)}">${esc(x.title.split(/[—·]/)[0].trim())}</a>`).join("")}</div>` : ""}
        <a class="go" href="${simHref(a.file)}">${t.contGo}</a></div>`);
    }
    cover.after(wrap);
    wrap.querySelector('[data-k="thy"]').addEventListener("click", () => { if (typeof setTrack === "function") { try { localStorage.setItem("hlTrack", "thy"); } catch (e) {} } });
    wrap.querySelector('[data-k="exp"]').addEventListener("click", () => { try { localStorage.setItem("hlTrack", "exp"); } catch (e) {} });
    wrap.querySelector('[data-k="ai"]').addEventListener("click", e => { e.preventDefault(); const b = document.querySelector(".hlai-btn"); if (b) b.click(); });
  }

  /* ── a year's page: what was opened before ── */
  function year() {
    const cards = [...document.querySelectorAll("#view article.prob")]; if (!cards.length) return;
    const seen = new Map(recent().map(r => [r.file, r.t])), t = T(); let any = false;
    for (const c of cards) {
      const a = c.querySelector('a[href^="sim/"]'); if (!a) continue;
      const file = a.getAttribute("href").split("?")[0].replace(/^sim\//, ""), at = seen.get(file);
      c.dataset.hlxDone = at ? "1" : "0";
      if (at && !c.querySelector(".hlx-done")) { any = true; const top = c.querySelector(".top .tr") || c.querySelector(".top");
        top.insertAdjacentHTML("afterbegin", `<span class="hlx-done" title="${t.ago(at)}">✓ ${t.done}</span>`); }
    }
    const grid = cards[0].parentElement;
    if (any && !grid.previousElementSibling?.classList.contains("hlx-filter")) {
      const f = document.createElement("div"); f.className = "hlx-filter"; f.setAttribute("role", "group");
      f.innerHTML = `<button type="button" aria-pressed="true" data-f="all">${t.all}</button><button type="button" aria-pressed="false" data-f="todo">${t.todo}</button>`;
      f.addEventListener("click", e => { const b = e.target.closest("button"); if (!b) return;
        f.querySelectorAll("button").forEach(x => x.setAttribute("aria-pressed", x === b));
        for (const c of cards) c.hidden = b.dataset.f === "todo" && c.dataset.hlxDone === "1"; });
      grid.before(f);
    }
  }

  /* ── search from anywhere ── */
  let index = null, indexLang = "";
  function buildIndex() {
    const t = T(), lg = L(), out = [];
    for (const [name, href] of t.pages) out.push({ k: "page", label: name, href, hay: name });
    if (hasData()) for (const [key, c] of Object.entries(DATA)) {
      if (!shown(key)) continue;
      const full = (c.full && (c.full[lg] || c.full.ko)) || "";
      out.push({ k: "comp", label: `${c.abbr} · ${full}`, href: `#/${key}`, hay: `${c.abbr} ${full} ${c.full ? c.full.en : ""}` });
      for (const y of c.years) {
        const host = y.host ? (y.host[lg] || y.host.ko || "") : "";
        out.push({ k: "year", label: `${c.abbr} ${y.y}${host ? " · " + host : ""}`, href: `#/${key}/${y.y}`, hay: `${c.abbr} ${y.y} ${host}` });
        for (const p of y.problems) {
          if (c.plain) continue;
          const title = p.title ? (p.title[lg] || p.title.ko || p.title.en || "") : "";
          out.push({ k: "exp", label: `${c.abbr} ${y.y} ${p.id || ""} · ${title}`, href: `#/${key}/${y.y}`, track: "exp", sim: p.files && p.files.sim,
            hay: `${c.abbr} ${y.y} ${p.id || ""} ${title} ${p.title ? (p.title.en || "") + " " + (p.title.ko || "") : ""} ${(p.tags || []).join(" ")} ${(p.tagsEn || []).join(" ")}` });
        }
        if (typeof thyOf === "function" && thyOf(key, y.y)) out.push({ k: "thy", label: `${c.abbr} ${y.y} · ${lg === "ko" ? "이론 문제" : "theory"}`, href: `#/${key}/${y.y}`, track: "thy", hay: `${c.abbr} ${y.y} 이론 theory` });
      }
    }
    /* theory papers load per competition when opened; the catalogue already says which competitions have them */
    const tk = (window.HL_CATALOGUE && window.HL_CATALOGUE.theoryKeys) || [];
    if (hasData()) for (const key of tk) if (DATA[key] && shown(key)) {
      const c = DATA[key], full = (c.full && (c.full[lg] || c.full.ko)) || "";
      out.push({ k: "thy", label: `${c.abbr} · ${lg === "ko" ? "이론 문제" : "theory papers"}`, href: `#/${key}`, track: "thy", hay: `${c.abbr} ${full} 이론 기출 theory papers` });
    }
    index = out; indexLang = lg;
  }
  const norm = s => String(s).toLowerCase().replace(/\s+/g, " ");
  function find(q) {
    if (!index || indexLang !== L()) buildIndex();
    const words = norm(q).trim().split(" ").filter(Boolean);
    if (!words.length) {
      const r = recent().slice(0, 4).map(x => ({ k: "recent", label: x.title, href: simHref(x.file), ext: true }));
      return r.concat(index.filter(i => i.k === "page").slice(0, 8 - r.length));
    }
    const order = { comp: 0, page: 1, exp: 2, thy: 3, year: 4 }, hits = [];
    for (const it of index) {
      const h = norm(it.hay); let s = 0, ok = true;
      for (const w of words) { const at = h.indexOf(w); if (at < 0) { ok = false; break; } s += at === 0 ? 0 : at < 6 ? 1 : 2; }
      if (ok) hits.push([s * 10 + order[it.k], it]);
    }
    return hits.sort((a, b) => a[0] - b[0]).slice(0, 9).map(h => h[1]);
  }
  let pal = null, sel = 0, items = [];
  function go(it) {
    if (!it) return; close();
    if (it.ext) { location.href = it.href; return; }
    if (it.track) { try { localStorage.setItem("hlTrack", it.track); } catch (e) {} }
    if (location.hash === it.href) { if (it.track && typeof setTrack === "function") setTrack(it.track); } else location.hash = it.href;
  }
  function paint() {
    const t = T(), q = pal.input.value; items = find(q); if (sel >= items.length) sel = 0;
    pal.list.innerHTML = items.length ? items.map((it, n) => `<li role="option" id="hlx-o${n}" aria-selected="${n === sel}" data-n="${n}"><span class="k">${t.kind[it.k]}</span><span class="l">${esc(it.label)}</span>${it.sim ? '<span class="s">▶</span>' : ""}</li>`).join("")
      : `<li class="none">${esc(t.none(q))}</li>`;
    pal.input.setAttribute("aria-activedescendant", items.length ? "hlx-o" + sel : "");
    const on = pal.list.querySelector('[aria-selected="true"]'); if (on) on.scrollIntoView({ block: "nearest" });
  }
  function open() {
    if (pal) { pal.input.focus(); return; }
    index = null;                                        /* theory papers may have loaded since the last search */
    const t = T(), dim = document.createElement("div"); dim.className = "hlx-dim";
    dim.innerHTML = `<div class="hlx-pal" role="dialog" aria-modal="true" aria-label="${t.search}"><input type="search" id="hlxQ" placeholder="${esc(t.ph)}" autocomplete="off" role="combobox" aria-expanded="true" aria-controls="hlxList"><ul id="hlxList" role="listbox"></ul><div class="f"><span>${t.nav}</span><span>${t.open}</span><span>${t.esc}</span></div></div>`;
    document.body.append(dim);
    pal = { dim, input: dim.querySelector("input"), list: dim.querySelector("ul"), back: document.activeElement };
    sel = 0; paint(); pal.input.focus();
    pal.input.addEventListener("input", () => { sel = 0; paint(); });
    pal.input.addEventListener("keydown", e => {
      if (e.key === "ArrowDown") { sel = Math.min(sel + 1, items.length - 1); paint(); e.preventDefault(); }
      else if (e.key === "ArrowUp") { sel = Math.max(sel - 1, 0); paint(); e.preventDefault(); }
      else if (e.key === "Enter") { go(items[sel]); e.preventDefault(); }
      else if (e.key === "Escape") { close(); e.preventDefault(); } });
    pal.list.addEventListener("click", e => { const li = e.target.closest("li[data-n]"); if (li) go(items[+li.dataset.n]); });
    dim.addEventListener("mousedown", e => { if (e.target === dim) close(); });
  }
  function close() { if (!pal) return; const back = pal.back; pal.dim.remove(); pal = null; if (back && back.focus) back.focus(); }
  function searchButton() {
    const nav = document.getElementById("nav"); if (!nav) return;
    let b = document.getElementById("hlxSearch");
    if (!b) { b = document.createElement("button"); b.id = "hlxSearch"; b.type = "button"; b.addEventListener("click", open); const th = document.getElementById("siteTheme"); if (th) th.before(b); else nav.after(b); }
    const mac = /Mac|iPhone|iPad/.test(navigator.platform || "");
    b.setAttribute("aria-label", T().search);
    b.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/></svg><span class="t">${T().search}</span><span class="kb">${mac ? "⌘" : "Ctrl"} K</span>`;
  }
  addEventListener("keydown", e => {
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName || "") || document.activeElement?.isContentEditable;
    if ((e.key === "k" || e.key === "K") && (e.ctrlKey || e.metaKey)) { e.preventDefault(); pal ? close() : open(); }
    else if (e.key === "/" && !typing && !pal) { e.preventDefault(); open(); }
  });

  /* ── phones: the main menu as a bar at the bottom ── */
  const ICONS = { "#/": '<path d="M4 11l8-6.5 8 6.5v8.5H4z"/><path d="M10 19.5v-5h4v5"/>', "#/comps": '<rect x="4.5" y="4" width="15" height="16" rx="2"/><path d="M8 9h8M8 12.5h8M8 16h5"/>',
    "#/learn": '<path d="M3 8l9-4 9 4-9 4z"/><path d="M7 10v4.5c3 2 7 2 10 0V10"/>', "#/monthly": '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 9.5h16M9 3v4M15 3v4"/>',
    "#/community": '<path d="M4.5 5h15v10.5H10L5.5 19z"/>', "#/about": '<circle cx="12" cy="12" r="8"/><path d="M12 11v5M12 8h.01"/>' };
  function tabs() {
    const nav = document.getElementById("nav"); if (!nav) return;
    let bar = document.getElementById("hlxTabs");
    if (!bar) { bar = document.createElement("div"); bar.id = "hlxTabs"; bar.setAttribute("role", "navigation"); document.body.append(bar); }
    bar.setAttribute("aria-label", nav.getAttribute("aria-label") || "menu");
    bar.innerHTML = [...nav.querySelectorAll("a")].map(a => { const h = a.getAttribute("href");
      return `<a href="${h}"${a.classList.contains("on") ? ' aria-current="page"' : ""}><svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[h] || '<circle cx="12" cy="12" r="7"/>'}</svg><span>${esc(a.textContent.trim())}</span></a>`; }).join("")
      + `<button type="button" data-hlx="search"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/></svg><span>${T().search}</span></button>`;
    bar.querySelector('[data-hlx="search"]').addEventListener("click", open);
    const exam = /^#\/lab\b|\/(exam|review)(\/|$)/.test(location.hash);
    document.documentElement.classList.toggle("hlx-has-tabs", !exam);
  }

  window.HL_UX = {
    afterRender(first, second) {
      try { searchButton(); tabs();
        if (!first) home();
        else if (hasData() && DATA[first] && second && /^\d{4}$/.test(second)) year();
      } catch (e) { if (window.console) console.warn("site-ux", e); }
    },
    open
  };
  addEventListener("hashchange", () => setTimeout(() => { try { tabs(); } catch (e) {} }, 0));
})();
