/* ==========================================================================
   HaslaLab — a web browser inside the simulated laptops, tablets and phones
   --------------------------------------------------------------------------
   VBrowser({kind, mobile, lang, online, links, onchange}) builds Microsoft
   Edge (kind "edge") or Google Chrome (kind "chrome"), desktop or mobile.
   The toolbar, the new-tab page, the offline page and the menu are drawn
   here; real pages load in an iframe.  Edge searches with Bing and Chrome
   with Google, as they do out of the box.  A site that forbids being shown
   inside another page stays blank: the info bar offers to open it in the
   real browser.  Pages of this site (the problem sheets) open directly.

   The host puts .el where the browser window's client area is: inside a
   window element (HTML desktops) or, over a canvas desktop, with
   place(x, y, w, h, visible) in page coordinates.
   ========================================================================== */
(function () {
  const CSS = `
.vb{position:absolute;display:flex;flex-direction:column;background:#fff;color:#1b1b1b;font:13px "Segoe UI Variable Text","Segoe UI","Malgun Gothic","Apple SD Gothic Neo",Roboto,Arial,sans-serif;overflow:hidden;z-index:40;box-sizing:border-box}
.vb *{box-sizing:border-box}
.vb.emb{position:relative;width:100%;height:100%}
.vb-bar{flex:none;display:flex;align-items:center;gap:2px;padding:4px 6px;height:40px;background:#f7f7f7;border-bottom:1px solid #e2e2e2}
.vb.vb-chrome .vb-bar{background:#fff;border-bottom:1px solid #dadce0}
.vb-b{flex:none;width:32px;height:32px;border:0;border-radius:4px;background:none;color:#1b1b1b;font-size:16px;line-height:32px;text-align:center;cursor:pointer;padding:0;margin:0}
.vb-chrome .vb-b{border-radius:50%}
.vb-b:hover{background:rgba(0,0,0,.07)} .vb-b:disabled{color:#b5b5b5;background:none;cursor:default}
.vb-addr{flex:1;min-width:0;display:flex;align-items:center;height:30px;margin:0 6px;padding:0 10px;border-radius:4px;background:#fff;border:1px solid #d6d6d6}
.vb-chrome .vb-addr{border:0;background:#f1f3f4;border-radius:15px}
.vb-addr:focus-within{border-color:#0067c0;box-shadow:0 0 0 1px #0067c0;background:#fff}
.vb-chrome .vb-addr:focus-within{box-shadow:0 0 0 2px #1a73e8}
.vb-addr .ic{flex:none;margin-right:8px;color:#5f6368;font-size:12px}
.vb-addr input{flex:1;min-width:0;border:0;outline:0;background:none;font:inherit;color:#1b1b1b;padding:0;margin:0;height:28px}
.vb-body{flex:1;position:relative;min-height:0;background:#fff}
.vb-frame{position:absolute;left:0;top:0;width:100%;height:100%;border:0;background:#fff;transform-origin:0 0}
.vb-page{position:absolute;inset:0;overflow:auto}
.vb-info{position:absolute;left:0;right:0;bottom:0;display:flex;align-items:center;gap:10px;padding:6px 10px;background:#fff8d6;border-top:1px solid #e9d98a;font-size:12px;color:#3a3a3a}
.vb-info span{flex:1;min-width:0}
.vb-info button{margin:0;padding:3px 10px;border:1px solid #c9b45a;background:#fff;border-radius:4px;font:inherit;cursor:pointer;color:#1b1b1b;width:auto}
.vb-info .x{border:0;background:none;padding:0 4px}
.vb-menu{position:absolute;right:6px;top:38px;min-width:230px;background:#fff;border:1px solid #d8d8d8;border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,.18);padding:4px;z-index:5}
.vb-menu div{padding:8px 12px;border-radius:4px;cursor:pointer;display:flex;justify-content:space-between;gap:16px}
.vb-menu div:hover{background:#f0f0f0} .vb-menu i{font-style:normal;color:#6b6b6b}
.vb-menu hr{border:0;border-top:1px solid #e5e5e5;margin:4px 0}
.vb-ntp{min-height:100%;display:flex;flex-direction:column;align-items:center;padding:9% 16px 24px}
.vb-edge .vb-ntp{background:linear-gradient(160deg,#dbeafa 0%,#f3f7fc 45%,#e8f0f9 100%)}
.vb-logo{font:600 46px "Segoe UI",Arial,sans-serif;letter-spacing:-1px;margin-bottom:22px;user-select:none}
.vb-edge .vb-logo{color:#174ea6;font-weight:600}
.vb-logo b{font-weight:500}
.vb-q{width:min(580px,92%);display:flex;align-items:center;height:46px;border-radius:24px;background:#fff;border:1px solid #dfe1e5;padding:0 18px;box-shadow:0 1px 6px rgba(32,33,36,.12)}
.vb-edge .vb-q{border-radius:8px;border-color:#c8d3df}
.vb-q input{flex:1;border:0;outline:0;font:inherit;font-size:15px;background:none;color:#1b1b1b;margin:0;padding:0;height:40px}
.vb-tiles{display:flex;flex-wrap:wrap;justify-content:center;gap:10px;margin-top:30px;max-width:620px}
.vb-tile{width:108px;padding:12px 6px;border-radius:8px;text-align:center;cursor:pointer;color:#1b1b1b;font-size:12px;line-height:1.3}
.vb-tile:hover{background:rgba(0,0,0,.06)}
.vb-tile .c{width:48px;height:48px;margin:0 auto 8px;border-radius:50%;background:#e8eaed;display:flex;align-items:center;justify-content:center;font:600 20px Arial;color:#3c4043}
.vb-edge .vb-tile .c{border-radius:10px;background:#fff;box-shadow:0 1px 4px rgba(0,0,0,.14)}
.vb-off{max-width:600px;margin:0 auto;padding:12% 28px 30px;color:#3c4043;font-size:14px;line-height:1.6}
.vb-off h1{font:400 24px "Segoe UI",Roboto,Arial,sans-serif;color:#202124;margin:18px 0 12px}
.vb-off ul{margin:8px 0;padding-left:20px} .vb-off code{font-size:12px;color:#5f6368}
.vb.vb-mob .vb-bar{height:52px;padding:6px 8px;background:#fff;border-bottom:1px solid #e3e3e3}
.vb.vb-mob .vb-addr{height:38px;border-radius:19px}
.vb-mob .vb-tabs{flex:none;width:22px;height:22px;border:2px solid #3c4043;border-radius:4px;font:700 11px Arial;display:flex;align-items:center;justify-content:center;margin:0 8px;color:#3c4043}
.vb-mob .vb-ntp{padding-top:14%}
.vb-mob .vb-logo{font-size:40px}
.vb-mob .vb-tile{width:76px}`;
  let styled = false;
  function inject() { if (styled) return; styled = true; const s = document.createElement("style"); s.textContent = CSS; document.head.appendChild(s); }

  const TXT = {
    ko: {newTab: "새 탭", search: (k) => k === "edge" ? "웹 검색" : "Google 검색 또는 URL 입력", addr: (k) => k === "edge" ? "검색 또는 웹 주소 입력" : "Google 검색 또는 URL 입력",
      menuNew: "새 탭", zoomIn: "확대", zoomOut: "축소", zoomR: "원래 크기", real: "실제 브라우저에서 열기", reload: "새로 고침",
      info: "내용이 나오지 않으면 이 사이트가 다른 화면 안에 표시되는 것을 막아 둔 것입니다.",
      offT: (k) => k === "edge" ? "인터넷에 연결되어 있지 않습니다." : "인터넷에 연결되어 있지 않음",
      offL: ["네트워크 케이블, 모뎀, 라우터 확인", "Wi-Fi에 다시 연결", "Windows 네트워크 진단 실행"], offH: "다음 방법을 시도해 보세요.",
      results: (q) => q + " - 검색", sheet: "문제지"},
    en: {newTab: "New tab", search: (k) => k === "edge" ? "Search the web" : "Search Google or type a URL", addr: (k) => k === "edge" ? "Search or enter web address" : "Search Google or type a URL",
      menuNew: "New tab", zoomIn: "Zoom in", zoomOut: "Zoom out", zoomR: "Reset zoom", real: "Open in your real browser", reload: "Reload",
      info: "If nothing shows, this site does not allow being shown inside another page.",
      offT: (k) => k === "edge" ? "You're not connected." : "No internet",
      offL: ["Checking the network cables, modem, and router", "Reconnecting to Wi-Fi", "Running Windows Network Diagnostics"], offH: "Try:",
      results: (q) => q + " - Search", sheet: "Problem sheet"}};

  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
  const DINO = '<svg width="44" height="47" viewBox="0 0 44 47" shape-rendering="crispEdges"><path fill="#535353" d="M22 0h20v3h2v14h-10v3h8v3h-11v4h4v5h-4v3h-3v3h-3v5h3v3h-6v-8h-3v3h-3v2h3v3h-6v-9h-3v-3h-3v-3h-3v-3H0v-11h3v6h3v3h3v-3h3v-3h3v-3h3v-3h4z"/><path fill="#fff" d="M25 3h3v3h-3z"/></svg>';

  function isUrl(s) { return /^(https?:\/\/|about:|\.{0,2}\/|[\w-]+\.(html?|pdf)(\?|#|$))/i.test(s) || (/^[\w-]+(\.[\w-]+)+(:\d+)?(\/\S*)?$/.test(s) && !/\s/.test(s)); }
  function abs(u) { if (/^https?:\/\//i.test(u) || /^about:/i.test(u)) return u; if (/^[\w-]+(\.[\w-]+)+(:\d+)?(\/\S*)?$/.test(u) && !/\.(html?|pdf)$/i.test(u)) return "https://" + u;
    try { return new URL(u, location.href).href; } catch (e) { return "https://" + u; } }

  window.VBrowser = function (o) {
    inject();
    const kind = o.kind || "edge", mob = !!o.mobile, L = () => TXT[(o.lang && o.lang()) === "en" ? "en" : "ko"];
    const online = o.online || (() => true), links = o.links || [];
    const el = document.createElement("div");
    el.className = "vb vb-" + kind + (mob ? " vb-mob" : "") + (o.embedded ? " emb" : "");
    el.innerHTML = (mob
      ? '<div class="vb-bar"><button class="vb-b" data-k="home" title="Home">⌂</button><div class="vb-addr"><span class="ic">🔒</span><input spellcheck="false" autocomplete="off"></div><span class="vb-tabs">1</span><button class="vb-b" data-k="menu">⋮</button></div>'
      : '<div class="vb-bar"><button class="vb-b" data-k="back" title="Back">←</button><button class="vb-b" data-k="fwd" title="Forward">→</button><button class="vb-b" data-k="reload" title="Reload">⟳</button>' +
        '<button class="vb-b" data-k="home" title="Home">⌂</button><div class="vb-addr"><span class="ic">🔒</span><input spellcheck="false" autocomplete="off"></div><button class="vb-b" data-k="menu">' + (kind === "edge" ? "···" : "⋮") + "</button></div>") +
      '<div class="vb-body"><div class="vb-page"></div><iframe class="vb-frame" hidden allow="fullscreen" referrerpolicy="strict-origin-when-cross-origin"></iframe><div class="vb-info" hidden><span></span><button data-k="real"></button><button class="x" data-k="noinfo">✕</button></div></div><div class="vb-menu" hidden></div>';
    const $ = (s) => el.querySelector(s), inp = $(".vb-addr input"), page = $(".vb-page"), info = $(".vb-info"), menu = $(".vb-menu");
    let frame = $(".vb-frame");
    const st = {hist: [], i: -1, zoom: 1, cur: null, info: true};

    function title() { const c = st.cur; if (!c || c.t === "ntp") return L().newTab; if (c.t === "off") return c.url; return c.title || c.url; }
    function changed() { inp.value = st.cur && st.cur.t !== "ntp" ? st.cur.url : ""; inp.placeholder = L().addr(kind);
      const b = (k) => el.querySelector('[data-k="' + k + '"]'); if (b("back")) b("back").disabled = st.i <= 0; if (b("fwd")) b("fwd").disabled = st.i >= st.hist.length - 1;
      $(".vb-addr .ic").textContent = st.cur && st.cur.t === "web" && /^https:/.test(st.cur.url) ? "🔒" : st.cur && st.cur.t === "web" ? "ⓘ" : "🔍";
      if (o.onchange) o.onchange(title()); }
    function newFrame(sandbox) { const f = document.createElement("iframe"); f.className = "vb-frame"; f.setAttribute("allow", "fullscreen"); f.setAttribute("referrerpolicy", "strict-origin-when-cross-origin");
      if (sandbox) f.setAttribute("sandbox", "allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox");    /* no top navigation: a page cannot break out of the laptop */
      frame.replaceWith(f); frame = f; applyZoom(); }
    function applyZoom() { const z = st.zoom; frame.style.transform = z === 1 ? "" : "scale(" + z + ")"; frame.style.width = 100 / z + "%"; frame.style.height = 100 / z + "%"; }
    function show(c) { st.cur = c; menu.hidden = true;
      if (c.t === "web" && !online()) { show({t: "off", url: c.url}); return; }
      if (c.t === "web") { const same = new URL(c.url, location.href).origin === location.origin; newFrame(!same); frame.hidden = false; page.hidden = true; frame.src = c.url;
        info.hidden = same || !st.info; if (!info.hidden) { info.querySelector("span").textContent = L().info; info.querySelector('[data-k="real"]').textContent = L().real; } }
      else { frame.hidden = true; frame.src = "about:blank"; info.hidden = true; page.hidden = false; page.innerHTML = c.t === "ntp" ? ntp() : offline(); wirePage(); }
      changed(); }
    function nav(c) { st.hist = st.hist.slice(0, st.i + 1); st.hist.push(c); st.i = st.hist.length - 1; show(c); }
    function go(s) { s = String(s || "").trim(); if (!s) return;
      if (isUrl(s)) { const u = abs(s), nm = decodeURIComponent(u.split("?")[0].split("/").filter(Boolean).pop() || u); nav({t: "web", url: u, title: /^https?:/.test(u) && !/\.pdf$/i.test(u) ? new URL(u).hostname : nm}); return; }
      const u = kind === "edge" ? "https://www.bing.com/search?q=" + encodeURIComponent(s) : "https://www.google.com/search?igu=1&q=" + encodeURIComponent(s);
      nav({t: "web", url: u, title: L().results(s)}); }
    function ntp() { const t = L(), logo = kind === "edge" ? '<div class="vb-logo">Microsoft <b>Bing</b></div>'
        : '<div class="vb-logo"><span style="color:#4285f4">G</span><span style="color:#ea4335">o</span><span style="color:#fbbc05">o</span><span style="color:#4285f4">g</span><span style="color:#34a853">l</span><span style="color:#ea4335">e</span></div>';
      return '<div class="vb-ntp">' + logo + '<div class="vb-q"><span style="margin-right:10px;color:#5f6368">🔍</span><input placeholder="' + esc(t.search(kind)) + '" spellcheck="false"></div><div class="vb-tiles">' +
        links.map((l, i) => '<div class="vb-tile" data-i="' + i + '"><div class="c"' + (l.col ? ' style="background:' + l.col + ';color:#fff"' : "") + ">" + esc(l.ic || (typeof l.t === "string" ? l.t : l.t[(o.lang && o.lang()) === "en" ? "en" : "ko"]).charAt(0)) + "</div>" +
          esc(typeof l.t === "string" ? l.t : l.t[(o.lang && o.lang()) === "en" ? "en" : "ko"]) + "</div>").join("") + "</div></div>"; }
    function offline() { const t = L();
      return '<div class="vb-off">' + (kind === "edge" ? '<div style="font-size:40px">🏄</div>' : DINO) + "<h1>" + esc(t.offT(kind)) + "</h1>" + (kind === "edge" ? "" : "<div>" + esc(t.offH) + "</div>") +
        "<ul>" + t.offL.slice(0, kind === "edge" ? 3 : 2).map((x) => "<li>" + esc(x) + "</li>").join("") + "</ul>" + (kind === "edge" ? "" : "<code>ERR_INTERNET_DISCONNECTED</code>") + "</div>"; }
    function wirePage() { const q = page.querySelector(".vb-q input"); if (q) q.onkeydown = (e) => { e.stopPropagation(); if (e.key === "Enter") go(q.value); };
      page.querySelectorAll(".vb-tile").forEach((d) => d.onclick = () => go(links[+d.dataset.i].url)); }
    function setMenu() { const t = L(); menu.innerHTML = '<div data-m="new">' + t.menuNew + "<i>Ctrl+T</i></div><hr>" +
        '<div data-m="zin">' + t.zoomIn + "<i>" + Math.round(st.zoom * 100) + "%</i></div>" + '<div data-m="zout">' + t.zoomOut + "</div>" + '<div data-m="zr">' + t.zoomR + "</div><hr>" +
        '<div data-m="reload">' + t.reload + "</div>" + (st.cur && st.cur.t === "web" ? '<div data-m="real">' + t.real + "</div>" : "");
      menu.querySelectorAll("[data-m]").forEach((d) => d.onclick = (e) => { e.stopPropagation(); const m = d.dataset.m; menu.hidden = true;
        if (m === "new") nav({t: "ntp"}); else if (m === "zin") { st.zoom = Math.min(2, st.zoom + 0.1); applyZoom(); } else if (m === "zout") { st.zoom = Math.max(0.5, st.zoom - 0.1); applyZoom(); }
        else if (m === "zr") { st.zoom = 1; applyZoom(); } else if (m === "reload") reload(); else if (m === "real") window.open(st.cur.url, "_blank", "noopener"); }); }
    function reload() { if (st.cur) show(st.cur); }
    function back() { if (st.i > 0) { st.i--; show(st.hist[st.i]); return true; } return false; }
    function fwd() { if (st.i < st.hist.length - 1) { st.i++; show(st.hist[st.i]); } }
    el.addEventListener("click", (e) => { const b = e.target.closest("[data-k]"); if (!b) { if (!e.target.closest(".vb-menu")) menu.hidden = true; return; } const k = b.dataset.k;
      if (k === "back") back(); else if (k === "fwd") fwd(); else if (k === "reload") reload(); else if (k === "home") nav({t: "ntp"});
      else if (k === "menu") { setMenu(); menu.hidden = !menu.hidden; } else if (k === "real") window.open(st.cur.url, "_blank", "noopener"); else if (k === "noinfo") { st.info = false; info.hidden = true; } });
    inp.onfocus = () => inp.select();
    inp.onkeydown = (e) => { e.stopPropagation(); if (e.key === "Enter") { go(inp.value); inp.blur(); } else if (e.key === "Escape") { changed(); inp.blur(); } };
    el.addEventListener("keydown", (e) => e.stopPropagation());
    el.addEventListener("wheel", (e) => e.stopPropagation(), {passive: true});
    nav({t: "ntp"});
    let shown = null;
    return {el, go, back, reload, title, kind,
      canBack: () => st.i > 0,
      /* over a canvas: page coordinates of the client area */
      place(x, y, w, h, vis) { const key = vis ? [x, y, w, h].map(Math.round).join(",") : "off"; if (key === shown) return; shown = key;
        if (!vis || w < 40 || h < 40) { el.style.display = "none"; return; } el.style.display = ""; el.style.left = Math.round(x) + "px"; el.style.top = Math.round(y) + "px"; el.style.width = Math.round(w) + "px"; el.style.height = Math.round(h) + "px"; },
      refresh() { if (st.cur && st.cur.t !== "web") show(st.cur); else changed(); },
      home() { nav({t: "ntp"}); },
      netChanged() { if (st.cur && ((st.cur.t === "off" && online()) || (st.cur.t === "web" && !online()))) show(st.cur.t === "off" ? {t: "web", url: st.cur.url, title: st.cur.url} : st.cur); }};
  };
  /* a picture of the browser for canvases that cannot hold the live page (window thumbnails, the laptop seen on the bench) */
  window.VBrowser.sketch = function (g, x, y, w, h, kind, title) {
    g.save(); g.beginPath(); g.rect(x, y, w, h); g.clip(); g.fillStyle = "#fff"; g.fillRect(x, y, w, h);
    const bh = Math.min(40, h * 0.12); g.fillStyle = kind === "edge" ? "#f7f7f7" : "#fff"; g.fillRect(x, y, w, bh); g.fillStyle = "#e2e2e2"; g.fillRect(x, y + bh - 1, w, 1);
    g.fillStyle = kind === "edge" ? "#fff" : "#f1f3f4"; g.strokeStyle = "#d6d6d6"; const ax = x + Math.min(140, w * 0.18), aw = w - (ax - x) - Math.min(50, w * 0.08);
    g.beginPath(); g.rect(ax, y + bh * 0.18, aw, bh * 0.64); g.fill(); if (kind === "edge") g.stroke();
    g.fillStyle = "#5f6368"; g.font = Math.max(8, Math.round(bh * 0.32)) + "px Arial"; g.textBaseline = "middle"; g.textAlign = "left"; g.fillText(title || "", ax + 10, y + bh / 2, aw - 20);
    g.fillStyle = kind === "edge" ? "#174ea6" : "#4285f4"; g.font = "600 " + Math.round(Math.min(46, w * 0.06)) + "px Arial"; g.textAlign = "center"; g.fillText(kind === "edge" ? "Microsoft Bing" : "Google", x + w / 2, y + bh + (h - bh) * 0.32);
    g.fillStyle = "#fff"; g.strokeStyle = "#dfe1e5"; g.lineWidth = 1; const qw = Math.min(w * 0.7, 560), qh = Math.min(44, h * 0.08);
    g.beginPath(); if (g.roundRect) g.roundRect(x + (w - qw) / 2, y + bh + (h - bh) * 0.42, qw, qh, qh / 2); else g.rect(x + (w - qw) / 2, y + bh + (h - bh) * 0.42, qw, qh); g.fill(); g.stroke();
    g.restore(); };
})();
