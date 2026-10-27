/* HaslaLab chart desk — a printed sky map you mark with a pencil, as in the star-chart rounds of IOAA, IAO and APAO.
   ChartLab.create({el, w, h, paint, key, lang}) puts one map sheet into `el`.  The map is painted once at its own
   size by paint(g, w, h); on top of it the student draws boxes, plus signs, crosses, circles, labels, straight lines,
   free curves, arrows, shading, and lines decorated with bars, rings or crosses.  Nothing is recognised or checked:
   the sheet only holds what was drawn.  Wheel zooms, the right or middle button (or Space) pans, Ctrl+Z / Ctrl+Y
   undo and redo.  Marks are kept in this browser (localStorage) under `key`. */
(function () {
  "use strict";
  const CSS = `
.cl{display:flex;flex-direction:column;gap:8px}
.cl-bar{display:flex;flex-wrap:wrap;gap:4px;align-items:center}
.cl-bar button{min-width:34px;height:32px;margin:0;padding:0 8px;border-radius:6px;border:1px solid #3a3f47;background:#2b2f36;color:#e8eef2;font:600 13px/1 "Segoe UI","Malgun Gothic",sans-serif;cursor:pointer;white-space:nowrap}
.cl-bar button:hover{border-color:#f2c14e}
.cl-bar button.on{background:#f2c14e;border-color:#f2c14e;color:#1c2027}
.cl-bar .sep{width:1px;height:22px;background:#3a3f47;margin:0 3px}
.cl-bar .col{width:22px;height:22px;min-width:22px;border-radius:50%;padding:0;border:2px solid #3a3f47}
.cl-bar .col.on{border-color:#f2c14e;box-shadow:0 0 0 2px #1c2027 inset}
.cl-wrap{position:relative;background:#6b6257;border-radius:6px;overflow:hidden;touch-action:none}
.cl-wrap canvas{display:block;width:100%}
.cl-txt{position:absolute;z-index:3;font:600 15px "Segoe UI","Malgun Gothic",sans-serif;padding:1px 4px;border:1px solid #f2c14e;background:#fffef6;color:#111;outline:none;min-width:40px}
.cl-hint{font-size:11.5px;color:#9aa3ab}
`;
  const T = {
    ko: {sel: "옮기기", box: "□ 상자", plus: "+ 더하기", cross: "× 가위표", oplus: "⊗", circle: "○ 원", dot: "• 점", text: "가 글자", line: "／ 직선", pen: "∿ 곡선", arrow: "→ 화살표",
         shade: "▨ 칠하기", bars: "┼ 막대 선", rings: "-o- 고리 선", xs: "-×- 가위표 선", erase: "지우개", undo: "↶", redo: "↷", clear: "모두 지우기", png: "PNG 저장", fit: "⤢",
         sure: "이 지도에 그린 것을 모두 지울까요?", hint: "휠: 확대·축소 / 오른쪽·가운데 버튼 또는 Space+끌기: 이동 / Ctrl+Z·Y: 되돌리기·다시 / 글자: 클릭하고 입력 후 Enter"},
    en: {sel: "Move", box: "□ Box", plus: "+ Plus", cross: "× Cross", oplus: "⊗", circle: "○ Circle", dot: "• Dot", text: "A Text", line: "／ Line", pen: "∿ Curve", arrow: "→ Arrow",
         shade: "▨ Shade", bars: "┼ Bar line", rings: "-o- Ring line", xs: "-×- Cross line", erase: "Eraser", undo: "↶", redo: "↷", clear: "Clear all", png: "Save PNG", fit: "⤢",
         sure: "Erase everything drawn on this map?", hint: "Wheel: zoom / right or middle button, or Space+drag: pan / Ctrl+Z·Y: undo·redo / Text: click, type, Enter"}
  };
  const COLS = ["#111111", "#c62828", "#1f4fd1", "#1b8a3a"];
  let cssDone = false;
  const store = {get(k) { try { return JSON.parse(localStorage.getItem(k) || "null"); } catch (e) { return null; } },
                 set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }};

  function create(o) {
    if (!cssDone) { const s = document.createElement("style"); s.textContent = CSS; document.head.appendChild(s); cssDone = true; }
    const L = () => T[(o.lang && o.lang()) === "en" ? "en" : "ko"];
    const W = o.w, H = o.h, tools = o.tools || ["sel", "box", "plus", "cross", "oplus", "circle", "dot", "text", "line", "pen", "arrow", "shade", "bars", "rings", "xs", "erase"];
    const root = document.createElement("div"); root.className = "cl";
    const bar = document.createElement("div"); bar.className = "cl-bar";
    const wrap = document.createElement("div"); wrap.className = "cl-wrap";
    const cv = document.createElement("canvas"); wrap.appendChild(cv);
    const hint = document.createElement("div"); hint.className = "cl-hint";
    root.append(bar, wrap, hint); o.el.appendChild(root);
    /* the printed map, painted once at twice its size */
    const base = document.createElement("canvas"); base.width = W * 2; base.height = H * 2;
    const bg = base.getContext("2d"); bg.scale(2, 2); o.paint(bg, W, H);
    const g = cv.getContext("2d");
    let items = (store.get(o.key) || []).filter((x) => x && x.t), undo = [], redo = [], tool = "box", col = COLS[0];
    const view = {z: 1, x: 0, y: 0}; let CW = 0, CH = 0, DPR = 1, drag = null, space = false, txt = null;
    const size = () => Math.max(6, Math.round(Math.min(W, H) * 0.016));
    function save() { store.set(o.key, items); if (o.onchange) o.onchange(items); }
    function commit(fn) { undo.push(JSON.stringify(items)); if (undo.length > 200) undo.shift(); redo = []; fn(); save(); draw(); }
    function layout() {
      const w = wrap.clientWidth || 800; DPR = Math.min(window.devicePixelRatio || 1, 2); CW = w; CH = Math.round(w * H / W);
      cv.width = Math.round(CW * DPR); cv.height = Math.round(CH * DPR); cv.style.height = CH + "px"; clampView(); draw(); }
    const k0 = () => CW / W;
    function clampView() { view.z = Math.max(1, Math.min(8, view.z)); const vw = W / view.z, vh = H / view.z;
      view.x = Math.max(0, Math.min(W - vw, view.x)); view.y = Math.max(0, Math.min(H - vh, view.y)); }
    const toMap = (e) => { const r = cv.getBoundingClientRect(), k = k0() * view.z; return [(e.clientX - r.left) / k + view.x, (e.clientY - r.top) / k + view.y]; };
    /* the marks */
    function mark(c, it) {
      const s = it.s || size(); c.strokeStyle = c.fillStyle = it.c || "#111"; c.lineWidth = Math.max(1.2, s * 0.13); c.lineCap = "round"; c.lineJoin = "round";
      const [x, y] = [it.x, it.y];
      switch (it.t) {
        case "box": c.strokeRect(x - s * 0.7, y - s * 0.7, s * 1.4, s * 1.4); break;
        case "plus": c.beginPath(); c.moveTo(x - s * 0.75, y); c.lineTo(x + s * 0.75, y); c.moveTo(x, y - s * 0.75); c.lineTo(x, y + s * 0.75); c.stroke(); break;
        case "cross": c.beginPath(); c.moveTo(x - s * 0.6, y - s * 0.6); c.lineTo(x + s * 0.6, y + s * 0.6); c.moveTo(x + s * 0.6, y - s * 0.6); c.lineTo(x - s * 0.6, y + s * 0.6); c.stroke(); break;
        case "oplus": c.beginPath(); c.arc(x, y, s * 0.7, 0, 7); c.moveTo(x - s * 0.5, y - s * 0.5); c.lineTo(x + s * 0.5, y + s * 0.5); c.moveTo(x + s * 0.5, y - s * 0.5); c.lineTo(x - s * 0.5, y + s * 0.5); c.stroke(); break;
        case "circle": c.beginPath(); c.arc(x, y, it.r || s, 0, 7); c.stroke(); break;
        case "dot": c.beginPath(); c.arc(x, y, s * 0.28, 0, 7); c.fill(); break;
        case "text": c.font = "600 " + Math.round(s * 1.25) + 'px "Segoe UI","Malgun Gothic",sans-serif'; c.textBaseline = "middle"; c.fillText(it.str, x, y); break;
        case "line": case "pen": case "arrow": case "bars": case "rings": case "xs": case "shade": {
          const p = it.pts; if (!p || p.length < 2) break;
          c.beginPath(); c.moveTo(p[0][0], p[0][1]); for (let i = 1; i < p.length; i++) c.lineTo(p[i][0], p[i][1]);
          if (it.t === "shade") { c.closePath(); c.globalAlpha = 0.45; c.fill(); c.globalAlpha = 1; c.lineWidth = Math.max(1, s * 0.08); }
          c.stroke();
          if (it.t === "arrow") { const a = p[p.length - 2], b = p[p.length - 1], an = Math.atan2(b[1] - a[1], b[0] - a[0]), h = s * 0.9;
            c.beginPath(); c.moveTo(b[0], b[1]); c.lineTo(b[0] - h * Math.cos(an - 0.45), b[1] - h * Math.sin(an - 0.45)); c.moveTo(b[0], b[1]); c.lineTo(b[0] - h * Math.cos(an + 0.45), b[1] - h * Math.sin(an + 0.45)); c.stroke(); }
          if (it.t === "bars" || it.t === "rings" || it.t === "xs") symbolsAlong(c, it, s);
          break; }
      }
    }
    /* small bars, rings or crosses every so often along a drawn curve (the symbols IOAA asks for on the ecliptic, the equator, the galactic equator) */
    function symbolsAlong(c, it, s) {
      const p = it.pts, step = s * 2.2; let acc = step / 2;
      for (let i = 1; i < p.length; i++) { const dx = p[i][0] - p[i - 1][0], dy = p[i][1] - p[i - 1][1], L = Math.hypot(dx, dy); if (!L) continue;
        const ux = dx / L, uy = dy / L; let d = acc;
        while (d <= L) { const x = p[i - 1][0] + ux * d, y = p[i - 1][1] + uy * d, h = s * 0.55; c.beginPath();
          if (it.t === "bars") { c.moveTo(x - uy * h, y + ux * h); c.lineTo(x + uy * h, y - ux * h); c.stroke(); }
          else if (it.t === "rings") { c.save(); c.fillStyle = "#fff"; c.arc(x, y, h * 0.6, 0, 7); c.fill(); c.restore(); c.beginPath(); c.arc(x, y, h * 0.6, 0, 7); c.stroke(); }
          else { c.moveTo(x - h * 0.7, y - h * 0.7); c.lineTo(x + h * 0.7, y + h * 0.7); c.moveTo(x + h * 0.7, y - h * 0.7); c.lineTo(x - h * 0.7, y + h * 0.7); c.stroke(); }
          d += step; }
        acc = d - L; }
    }
    function bounds(it) { const s = it.s || size();
      if (it.pts) { let a = [1e9, 1e9, -1e9, -1e9]; for (const [x, y] of it.pts) a = [Math.min(a[0], x), Math.min(a[1], y), Math.max(a[2], x), Math.max(a[3], y)]; return [a[0] - s * 0.6, a[1] - s * 0.6, a[2] + s * 0.6, a[3] + s * 0.6]; }
      if (it.t === "text") { g.font = "600 " + Math.round(s * 1.25) + "px sans-serif"; return [it.x, it.y - s * 0.8, it.x + g.measureText(it.str).width, it.y + s * 0.8]; }
      const r = it.t === "circle" ? (it.r || s) : s; return [it.x - r, it.y - r, it.x + r, it.y + r]; }
    function nearItem(p) { const tol = 6 / (k0() * view.z);
      for (let i = items.length - 1; i >= 0; i--) { const it = items[i];
        if (it.pts && it.t !== "shade") { for (let j = 1; j < it.pts.length; j++) if (segDist(p, it.pts[j - 1], it.pts[j]) < tol + (it.s || size()) * 0.4) return i; continue; }
        const b = bounds(it); if (p[0] > b[0] - tol && p[0] < b[2] + tol && p[1] > b[1] - tol && p[1] < b[3] + tol) return i; }
      return -1; }
    function segDist(p, a, b) { const dx = b[0] - a[0], dy = b[1] - a[1], L = dx * dx + dy * dy; let t = L ? ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L : 0; t = Math.max(0, Math.min(1, t));
      return Math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy); }
    function draw() {
      if (!CW) return; const k = k0() * view.z * DPR;
      g.setTransform(1, 0, 0, 1, 0, 0); g.fillStyle = "#fff"; g.fillRect(0, 0, cv.width, cv.height);
      g.setTransform(k, 0, 0, k, -k * view.x, -k * view.y); g.imageSmoothingQuality = "high"; g.drawImage(base, 0, 0, W, H);
      for (const it of items) mark(g, it);
      if (drag && drag.it) mark(g, drag.it);
    }
    /* input */
    function startText(p) {
      if (txt) endText(); const r = cv.getBoundingClientRect(), wr = wrap.getBoundingClientRect(), k = k0() * view.z;
      const inp = document.createElement("input"); inp.className = "cl-txt"; inp.style.left = (r.left - wr.left + (p[0] - view.x) * k) + "px";
      inp.style.top = (r.top - wr.top + (p[1] - view.y) * k - 12) + "px"; inp.style.color = col; wrap.appendChild(inp); inp.focus();
      txt = {inp, p};
      inp.onkeydown = (e) => { e.stopPropagation(); if (e.key === "Enter") endText(); else if (e.key === "Escape") { inp.value = ""; endText(); } };
      inp.onblur = () => setTimeout(endText, 0); }
    function endText() { if (!txt) return; const {inp, p} = txt; txt = null; const s = inp.value.trim(); inp.remove();
      if (s) commit(() => items.push({t: "text", x: p[0], y: p[1], str: s, c: col, s: size()})); }
    cv.addEventListener("contextmenu", (e) => e.preventDefault());
    cv.addEventListener("pointerdown", (e) => {
      const p = toMap(e); try { cv.setPointerCapture(e.pointerId); } catch (er) {}
      if (e.button === 1 || e.button === 2 || space) { drag = {pan: true, cx: e.clientX, cy: e.clientY, vx: view.x, vy: view.y}; return; }
      if (e.button !== 0) return;
      if (tool === "text") { e.preventDefault(); startText(p); return; }
      if (tool === "erase") { const i = nearItem(p); if (i >= 0) commit(() => items.splice(i, 1)); drag = {erase: true}; return; }
      if (tool === "sel") { const i = nearItem(p); if (i >= 0) { undo.push(JSON.stringify(items)); redo = []; drag = {move: items[i], p0: p}; } return; }
      if (["line", "pen", "arrow", "bars", "rings", "xs", "shade"].includes(tool)) { drag = {it: {t: tool, pts: [p, p.slice()], c: col, s: size()}}; return; }
      if (tool === "circle") { drag = {it: {t: "circle", x: p[0], y: p[1], r: size(), c: col, s: size()}, circ: true}; return; }
      commit(() => items.push({t: tool, x: p[0], y: p[1], c: col, s: size()}));
    });
    cv.addEventListener("pointermove", (e) => {
      if (!drag) return; const p = toMap(e);
      if (drag.pan) { const k = k0() * view.z; view.x = drag.vx - (e.clientX - drag.cx) / k; view.y = drag.vy - (e.clientY - drag.cy) / k; clampView(); draw(); return; }
      if (drag.erase) { const i = nearItem(p); if (i >= 0) commit(() => items.splice(i, 1)); return; }
      if (drag.move) { const it = drag.move, dx = p[0] - drag.p0[0], dy = p[1] - drag.p0[1]; drag.p0 = p;
        if (it.pts) it.pts = it.pts.map(([x, y]) => [x + dx, y + dy]); else { it.x += dx; it.y += dy; } draw(); return; }
      if (drag.circ) { drag.it.r = Math.max(2, Math.hypot(p[0] - drag.it.x, p[1] - drag.it.y)); draw(); return; }
      const it = drag.it; if (!it) return;
      if (it.t === "line" || it.t === "arrow") it.pts[1] = p;
      else { const q = it.pts[it.pts.length - 1]; if (Math.hypot(p[0] - q[0], p[1] - q[1]) > 2 / (k0() * view.z)) it.pts.push(p); }
      draw();
    });
    const up = () => { if (!drag) return; const d = drag; drag = null;
      if (d.move) { save(); draw(); return; }
      if (d.it) { const it = d.it, ok = it.pts ? Math.hypot(it.pts[0][0] - it.pts[it.pts.length - 1][0], it.pts[0][1] - it.pts[it.pts.length - 1][1]) > 2 || it.pts.length > 3 : true;
        if (it.pts && it.t !== "line" && it.t !== "arrow" && it.pts.length > 2) it.pts = simplify(it.pts, 0.6);
        if (ok) commit(() => items.push(it)); else draw(); }
      else draw(); };
    cv.addEventListener("pointerup", up); cv.addEventListener("pointercancel", up);
    cv.addEventListener("wheel", (e) => { e.preventDefault(); const p = toMap(e), r = cv.getBoundingClientRect();
      view.z *= e.deltaY < 0 ? 1.18 : 1 / 1.18; clampView(); const k = k0() * view.z;
      view.x = p[0] - (e.clientX - r.left) / k; view.y = p[1] - (e.clientY - r.top) / k; clampView(); draw(); }, {passive: false});
    function simplify(pts, eps) { if (pts.length < 3) return pts; let dm = 0, idx = 0;
      for (let i = 1; i < pts.length - 1; i++) { const d = segDist(pts[i], pts[0], pts[pts.length - 1]); if (d > dm) { dm = d; idx = i; } }
      if (dm > eps) { const a = simplify(pts.slice(0, idx + 1), eps), b = simplify(pts.slice(idx), eps); return a.slice(0, -1).concat(b); }
      return [pts[0], pts[pts.length - 1]]; }
    const keyH = (e) => { if (root.offsetParent === null || /INPUT|TEXTAREA|SELECT/.test(e.target.tagName)) return;
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") { e.preventDefault(); doUndo(); }
      else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") { e.preventDefault(); doRedo(); }
      else if (e.key === " ") { space = true; } };
    addEventListener("keydown", keyH); addEventListener("keyup", (e) => { if (e.key === " ") space = false; });
    function doUndo() { if (!undo.length) return; redo.push(JSON.stringify(items)); items = JSON.parse(undo.pop()); save(); draw(); }
    function doRedo() { if (!redo.length) return; undo.push(JSON.stringify(items)); items = JSON.parse(redo.pop()); save(); draw(); }
    function exportPNG(name) { const c = document.createElement("canvas"); c.width = W * 2; c.height = H * 2; const x = c.getContext("2d"); x.scale(2, 2);
      x.drawImage(base, 0, 0, W, H); for (const it of items) mark(x, it);
      const a = document.createElement("a"); a.download = (name || o.key || "map") + ".png"; a.href = c.toDataURL("image/png"); a.click(); }
    function buildBar() {
      const t = L(); bar.innerHTML = "";
      for (const k of tools) { const b = document.createElement("button"); b.textContent = t[k]; b.title = t[k]; b.className = k === tool ? "on" : ""; b.onclick = () => { tool = k; buildBar(); }; bar.appendChild(b); }
      bar.appendChild(Object.assign(document.createElement("span"), {className: "sep"}));
      for (const c of COLS) { const b = document.createElement("button"); b.className = "col" + (c === col ? " on" : ""); b.style.background = c; b.onclick = () => { col = c; buildBar(); }; bar.appendChild(b); }
      bar.appendChild(Object.assign(document.createElement("span"), {className: "sep"}));
      const mk = (lab, fn, tip) => { const b = document.createElement("button"); b.textContent = lab; if (tip) b.title = tip; b.onclick = fn; bar.appendChild(b); };
      mk(t.undo, doUndo, "Ctrl+Z"); mk(t.redo, doRedo, "Ctrl+Y"); mk(t.fit, () => { view.z = 1; view.x = view.y = 0; draw(); });
      mk(t.clear, () => { if (items.length && confirm(t.sure)) commit(() => { items = []; }); }); mk(t.png, () => exportPNG());
      hint.textContent = t.hint; }
    addEventListener("resize", layout);
    buildBar(); requestAnimationFrame(layout);
    return {el: root, layout, draw, lang: buildBar, exportPNG, items: () => items, show(v) { root.style.display = v ? "" : "none"; if (v) layout(); }};
  }
  /* the star list in skydata.js: [{ra, de (degrees), m (V), bv}], brightest first */
  let STARS = null;
  function stars() {
    if (STARS) return STARS; const D = window.SKY_DATA.stars, bin = atob(D.b64), dv = new DataView(new ArrayBuffer(bin.length));
    for (let i = 0; i < bin.length; i++) dv.setUint8(i, bin.charCodeAt(i));
    STARS = []; for (let i = 0; i < D.n; i++) { const o = i * 7; STARS.push({ra: dv.getUint16(o, true) / 180, de: dv.getInt16(o + 2, true) / 360, m: dv.getInt16(o + 4, true) / 100, bv: dv.getUint8(o + 6) / 80 - 0.5}); }
    return STARS; }
  /* how a printed chart inks a star: darker and larger when brighter, tinted by its colour */
  function starInk(bv, m) { const t = Math.max(-0.3, Math.min(1.8, bv)), f = Math.max(0, Math.min(1, (m - 4.2) / 2.2)) * 0.72;
    const tint = t < 0.4 ? [24, 34, 92] : t > 1.1 ? [88, 52, 18] : [26, 26, 26], w = t < 0.4 ? Math.min(1, (0.4 - t) / 0.5) : t > 1.1 ? Math.min(1, (t - 1.1) / 0.5) : 0;
    const c = tint.map((x) => 22 + (x - 22) * w * 0.8), mix = (a) => Math.round(a + (190 - a) * f); return "rgb(" + c.map(mix).join(",") + ")"; }
  /* the ecliptic as [ra, dec] points, and the equatorial position of ecliptic longitude lam (degrees) */
  const EPS = 23.4393 * Math.PI / 180;
  function eclToEq(lam, bet) { const l = lam * Math.PI / 180, b = (bet || 0) * Math.PI / 180;
    const ra = Math.atan2(Math.sin(l) * Math.cos(EPS) - Math.tan(b) * Math.sin(EPS), Math.cos(l)), de = Math.asin(Math.sin(b) * Math.cos(EPS) + Math.cos(b) * Math.sin(EPS) * Math.sin(l));
    return [((ra * 180 / Math.PI) % 360 + 360) % 360, de * 180 / Math.PI]; }
  window.ChartLab = {create, stars, starInk, eclToEq};
})();
