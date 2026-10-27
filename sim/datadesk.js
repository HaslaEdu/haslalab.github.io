/* HaslaLab data-analysis desk — what an IOAA data-analysis round puts on the table, and nothing more:
   graph paper (1 mm, 5 mm and 1 cm lines) on which the student draws the axes with a scale of their own choosing
   and plots points (with error bars) from the values they worked out, a scientific calculator, and a worksheet table.
   No fitting, no regression, no slope: lines are drawn with the ruler (the chart desk's line tool) and read back off
   the paper.  Built on ChartLab (chartlab.js).
     DataDesk.paper(el, {key, lang, w_mm, h_mm})   graph-paper sheet with axes and a plotting form
     DataDesk.calc(el, {lang})                     scientific calculator
     DataDesk.table(el, {key, lang, rows, cols})   worksheet table */
(function () {
  "use strict";
  const CSS = `
.dd-form{display:flex;flex-wrap:wrap;gap:6px;align-items:flex-end;background:#12161b;border:1px solid #33373e;border-radius:8px;padding:8px;margin-top:6px}
.dd-form label{display:flex;flex-direction:column;font-size:11.5px;color:#9aa3ab;gap:2px}
.dd-form input,.dd-form select{width:84px;padding:5px 6px;border-radius:5px;border:1px solid #33373e;background:#1a1e24;color:#e8eef2;font:13px ui-monospace,Consolas,monospace}
.dd-form input.w{width:130px}
.dd-form button{height:30px;margin:0;padding:0 10px;border-radius:6px;border:1px solid #3a3f47;background:#2b2f36;color:#e8eef2;font:600 12.5px "Segoe UI","Malgun Gothic",sans-serif;cursor:pointer}
.dd-form button:hover{border-color:#f2c14e}
.dd-form .t{width:100%;font:600 12px "Segoe UI","Malgun Gothic",sans-serif;color:#f2c14e}
.dd-calc{background:#1b1f25;border:1px solid #33373e;border-radius:10px;padding:8px}
.dd-calc .scr{background:#c9d4c0;color:#111;border-radius:6px;padding:6px 8px;font:15px ui-monospace,Consolas,monospace;min-height:58px;margin-bottom:6px;word-break:break-all}
.dd-calc .scr .h{font-size:11px;color:#4b5548;min-height:14px}.dd-calc .scr .r{text-align:right;font-size:19px;font-weight:600}
.dd-calc input{width:100%;padding:6px 8px;border-radius:6px;border:1px solid #33373e;background:#0f1216;color:#e8eef2;font:14px ui-monospace,Consolas,monospace;margin-bottom:6px}
.dd-calc .keys{display:grid;grid-template-columns:repeat(5,1fr);gap:4px}
.dd-calc .keys button{height:30px;margin:0;padding:0;border-radius:5px;border:1px solid #33373e;background:#2b2f36;color:#e8eef2;font:600 12.5px "Segoe UI",sans-serif;cursor:pointer}
.dd-calc .keys button.op{background:#353b44}.dd-calc .keys button.eq{background:#f2c14e;color:#1c2027;border-color:#f2c14e}
.dd-calc .keys button.on{background:#f2c14e;color:#1c2027}
.dd-tab{overflow:auto;max-height:420px;border:1px solid #33373e;border-radius:8px;background:#fbfaf6}
.dd-tab table{border-collapse:collapse;font:13px ui-monospace,Consolas,monospace;color:#111}
.dd-tab td{border:1px solid #c9c4b6;padding:0;min-width:86px}
.dd-tab td input{width:100%;border:0;background:transparent;padding:4px 6px;font:inherit;color:inherit;outline:none}
.dd-tab tr:first-child td{background:#ece6d6}.dd-tab tr:first-child td input{font-weight:700}
.dd-tab td input:focus{background:#fff6cf}
.dd-tabbar{display:flex;gap:6px;margin-top:6px}.dd-tabbar button{margin:0;padding:5px 10px;border-radius:6px;border:1px solid #3a3f47;background:#2b2f36;color:#e8eef2;font:600 12px "Segoe UI","Malgun Gothic",sans-serif;cursor:pointer}
`;
  let cssDone = false;
  const css = () => { if (cssDone) return; const s = document.createElement("style"); s.textContent = CSS; document.head.appendChild(s); cssDone = true; };
  const store = {get(k) { try { return JSON.parse(localStorage.getItem(k) || "null"); } catch (e) { return null; } },
                 set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }};
  const T = {
    ko: {axes: "축 그리기 — 원점 위치와 1 cm(큰 칸)당 값은 직접 정합니다", ox: "원점 x (mm)", oy: "원점 y (mm)", x0: "원점의 x 값", dx: "x: 1 cm당", y0: "원점의 y 값", dy: "y: 1 cm당",
         xl: "x축 이름", yl: "y축 이름", draw: "축 그리기", erase: "축 지우기", plot: "점 찍기 — 계산한 값을 직접 넣습니다", x: "x", y: "y", sx: "±x (선택)", sy: "±y (선택)", sym: "모양",
         put: "찍기", syms: [["circle", "○"], ["dot", "•"], ["cross", "×"], ["plus", "+"]], noAxes: "먼저 축을 그리세요.", bad: "숫자를 넣으세요.", out: "그 점은 종이 밖입니다.",
         rdmm: "종이 위치", rdv: "축 눈금으로 읽은 값", deg: "DEG", rad: "RAD", err: "식 오류", addRow: "줄 추가", delRow: "마지막 줄 지우기", clear: "표 비우기", sure: "표를 모두 비울까요?"},
    en: {axes: "Draw the axes — you choose where the origin is and what one centimetre (big square) is worth", ox: "origin x (mm)", oy: "origin y (mm)", x0: "x at origin", dx: "x per cm", y0: "y at origin", dy: "y per cm",
         xl: "x label", yl: "y label", draw: "Draw axes", erase: "Remove axes", plot: "Plot a point — type the value you worked out", x: "x", y: "y", sx: "±x (opt.)", sy: "±y (opt.)", sym: "symbol",
         put: "Plot", syms: [["circle", "○"], ["dot", "•"], ["cross", "×"], ["plus", "+"]], noAxes: "Draw the axes first.", bad: "Type numbers.", out: "That point is off the paper.",
         rdmm: "on the paper", rdv: "read on your axes", deg: "DEG", rad: "RAD", err: "error", addRow: "Add row", delRow: "Remove last row", clear: "Clear table", sure: "Clear the whole table?"}
  };
  const L = (o) => T[(o.lang && o.lang()) === "en" ? "en" : "ko"];
  const fmt = (v) => { if (!isFinite(v)) return "—"; const a = Math.abs(v); return a !== 0 && (a < 1e-3 || a >= 1e5) ? v.toExponential(4) : (+v.toPrecision(6)).toString(); };

  /* ---------------- graph paper ---------------- */
  function paper(el, o) {
    css(); const PX = 4, Wmm = o.w_mm || 180, Hmm = o.h_mm || 250, W = Wmm * PX, H = Hmm * PX;
    const AK = o.key + "-axes"; let ax = store.get(AK);
    const mm = (u, v) => [u / PX, Hmm - v / PX];                 /* paper mm, y up from the bottom */
    const pxOf = (xm, ym) => [xm * PX, (Hmm - ym) * PX];
    function paint(g) {
      g.fillStyle = "#fffdf8"; g.fillRect(0, 0, W, H);
      for (let i = 0; i <= Wmm; i++) { const x = i * PX + 0.5; g.strokeStyle = i % 10 === 0 ? "#e2834a" : i % 5 === 0 ? "#efb08a" : "#f8d9c4"; g.lineWidth = i % 10 === 0 ? 1.1 : i % 5 === 0 ? 0.8 : 0.5; g.beginPath(); g.moveTo(x, 0); g.lineTo(x, H); g.stroke(); }
      for (let j = 0; j <= Hmm; j++) { const y = H - j * PX + 0.5; g.strokeStyle = j % 10 === 0 ? "#e2834a" : j % 5 === 0 ? "#efb08a" : "#f8d9c4"; g.lineWidth = j % 10 === 0 ? 1.1 : j % 5 === 0 ? 0.8 : 0.5; g.beginPath(); g.moveTo(0, y); g.lineTo(W, y); g.stroke(); }
      if (o.title) { g.fillStyle = "#b85a2a"; g.font = "600 13px Arial"; g.textAlign = "right"; g.textBaseline = "top"; g.fillText(o.title, W - 6, 4); }
      if (!ax) return;
      const [X0, Y0] = pxOf(ax.ox, ax.oy); g.strokeStyle = "#1b1b1b"; g.lineWidth = 1.6;
      g.beginPath(); g.moveTo(0, Y0); g.lineTo(W, Y0); g.moveTo(X0, H); g.lineTo(X0, 0); g.stroke();
      g.fillStyle = "#1b1b1b"; g.beginPath(); g.moveTo(W - 2, Y0); g.lineTo(W - 12, Y0 - 4); g.lineTo(W - 12, Y0 + 4); g.fill(); g.beginPath(); g.moveTo(X0, 2); g.lineTo(X0 - 4, 12); g.lineTo(X0 + 4, 12); g.fill();
      g.font = "12px 'Segoe Print','Comic Sans MS',cursive"; g.lineWidth = 1.2;
      for (let k = -40; k <= 40; k++) { const xm = ax.ox + 10 * k; if (xm < 2 || xm > Wmm - 6 || k === 0 && false) continue; const [x] = pxOf(xm, 0);
        g.beginPath(); g.moveTo(x, Y0 - 4); g.lineTo(x, Y0 + 4); g.stroke(); g.textAlign = "center"; g.textBaseline = "top"; g.fillText(fmt(ax.x0 + k * ax.dx), x, Y0 + 6); }
      for (let k = -40; k <= 40; k++) { const ym = ax.oy + 10 * k; if (ym < 2 || ym > Hmm - 6 || k === 0) continue; const [, y] = pxOf(0, ym);
        g.beginPath(); g.moveTo(X0 - 4, y); g.lineTo(X0 + 4, y); g.stroke(); g.textAlign = "right"; g.textBaseline = "middle"; g.fillText(fmt(ax.y0 + k * ax.dy), X0 - 7, y); }
      g.font = "600 14px 'Segoe Print','Comic Sans MS',cursive"; g.textAlign = "right"; g.textBaseline = "bottom"; if (ax.xl) g.fillText(ax.xl, W - 8, Y0 - 8);
      g.textAlign = "left"; g.textBaseline = "top"; if (ax.yl) g.fillText(ax.yl, X0 + 8, 6);
    }
    const lab = ChartLab.create({el, w: W, h: H, paint, key: o.key, lang: o.lang,
      readout: (u, v) => { const [xm, ym] = mm(u, v); let s = L(o).rdmm + "  " + xm.toFixed(1) + " mm, " + ym.toFixed(1) + " mm";
        if (ax) s += "     " + L(o).rdv + "  x = " + fmt(ax.x0 + (xm - ax.ox) / 10 * ax.dx) + ",  y = " + fmt(ax.y0 + (ym - ax.oy) / 10 * ax.dy); return s; }});
    /* the forms under the sheet */
    const f1 = document.createElement("div"), f2 = document.createElement("div"); f1.className = f2.className = "dd-form"; el.append(f1, f2);
    function build() {
      const t = L(o), a = ax || {ox: 20, oy: 20, x0: 0, dx: 1, y0: 0, dy: 1, xl: "", yl: ""};
      const inp = (k, lb, w) => '<label>' + lb + '<input data-k="' + k + '" value="' + String(a[k]).replace(/"/g, "&quot;") + '"' + (w ? ' class="w"' : "") + "></label>";
      f1.innerHTML = '<div class="t">' + t.axes + "</div>" + inp("ox", t.ox) + inp("oy", t.oy) + inp("x0", t.x0) + inp("dx", t.dx) + inp("y0", t.y0) + inp("dy", t.dy) + inp("xl", t.xl, 1) + inp("yl", t.yl, 1) +
        '<button data-a="ax">' + t.draw + '</button><button data-a="rm">' + t.erase + "</button>";
      f2.innerHTML = '<div class="t">' + t.plot + '</div><label>' + t.x + '<input data-p="x"></label><label>' + t.y + '<input data-p="y"></label><label>' + t.sx + '<input data-p="sx"></label><label>' + t.sy + '<input data-p="sy"></label>' +
        '<label>' + t.sym + '<select data-p="sym">' + t.syms.map(([k, s]) => '<option value="' + k + '">' + s + "</option>").join("") + '</select></label><button data-a="pt">' + t.put + '</button><span data-msg style="color:#f0a79f;font-size:12px"></span>';
      f1.querySelector('[data-a=ax]').onclick = () => { const v = {}; for (const i of f1.querySelectorAll("input")) v[i.dataset.k] = i.value;
        const n = (k) => parseFloat(String(v[k]).replace(",", ".")); const c = {ox: n("ox"), oy: n("oy"), x0: n("x0"), dx: n("dx"), y0: n("y0"), dy: n("dy"), xl: v.xl, yl: v.yl};
        if (["ox", "oy", "x0", "dx", "y0", "dy"].some((k) => !isFinite(c[k])) || !c.dx || !c.dy) { msg(t.bad); return; }
        ax = c; store.set(AK, ax); lab.repaint(); msg(""); };
      f1.querySelector('[data-a=rm]').onclick = () => { ax = null; store.set(AK, null); lab.repaint(); };
      const msg = (s) => { f2.querySelector("[data-msg]").textContent = s; };
      const go = () => { if (!ax) { msg(t.noAxes); return; } const g = (k) => parseFloat(String(f2.querySelector('[data-p="' + k + '"]').value).replace(",", "."));
        const x = g("x"), y = g("y"), sx = g("sx"), sy = g("sy"); if (!isFinite(x) || !isFinite(y)) { msg(t.bad); return; }
        const xm = ax.ox + (x - ax.x0) / ax.dx * 10, ym = ax.oy + (y - ax.y0) / ax.dy * 10;
        if (xm < 0 || xm > Wmm || ym < 0 || ym > Hmm) { msg(t.out); return; }
        const [u, v] = pxOf(xm, ym), sym = f2.querySelector('[data-p="sym"]').value, list = [{t: sym, x: u, y: v, r: sym === "circle" ? 7 : undefined, s: 10}];
        if (isFinite(sx) && sx > 0) { const d = sx / ax.dx * 10 * PX; list.push({t: "line", pts: [[u - d, v], [u + d, v]], s: 8}); }
        if (isFinite(sy) && sy > 0) { const d = sy / ax.dy * 10 * PX; list.push({t: "line", pts: [[u, v - d], [u, v + d]], s: 8}); }
        lab.add(list); msg(""); for (const k of ["x", "y", "sx", "sy"]) f2.querySelector('[data-p="' + k + '"]').value = ""; f2.querySelector('[data-p="x"]').focus(); };
      f2.querySelector('[data-a=pt]').onclick = go;
      for (const i of f2.querySelectorAll("input")) i.onkeydown = (e) => { e.stopPropagation(); if (e.key === "Enter") go(); };
      for (const i of f1.querySelectorAll("input")) i.onkeydown = (e) => e.stopPropagation();
    }
    build();
    return {lab, lang() { lab.lang(); build(); }, show(v) { lab.show(v); f1.style.display = f2.style.display = v ? "" : "none"; }};
  }

  /* ---------------- scientific calculator ---------------- */
  function calc(el, o) {
    css(); let deg = true, ans = 0, hist = "";
    const box = document.createElement("div"); box.className = "dd-calc"; el.appendChild(box);
    box.innerHTML = '<div class="scr"><div class="h"></div><div class="r">0</div></div><input spellcheck="false" autocomplete="off"><div class="keys"></div>';
    const scr = box.querySelector(".r"), hh = box.querySelector(".h"), inp = box.querySelector("input"), keys = box.querySelector(".keys");
    const K = [["DEG", "mode"], ["(", "("], [")", ")"], ["⌫", "bs"], ["AC", "ac"], ["sin", "sin("], ["cos", "cos("], ["tan", "tan("], ["^", "^"], ["√", "sqrt("],
      ["asin", "asin("], ["acos", "acos("], ["atan", "atan("], ["ln", "ln("], ["log", "log("], ["7", "7"], ["8", "8"], ["9", "9"], ["÷", "/"], ["eˣ", "exp("],
      ["4", "4"], ["5", "5"], ["6", "6"], ["×", "*"], ["π", "pi"], ["1", "1"], ["2", "2"], ["3", "3"], ["−", "-"], ["Ans", "Ans"], ["0", "0"], [".", "."], ["×10ˣ", "E"], ["+", "+"], ["=", "="]];
    keys.innerHTML = K.map(([l, v]) => '<button data-v="' + v + '" class="' + (v === "=" ? "eq" : /[()^*/+\-]|bs|ac|mode/.test(v) ? "op" : "") + '">' + l + "</button>").join("");
    const modeBtn = keys.querySelector('[data-v="mode"]');
    for (const b of keys.querySelectorAll("button")) b.onclick = () => { const v = b.dataset.v;
      if (v === "mode") { deg = !deg; modeBtn.textContent = deg ? "DEG" : "RAD"; return; }
      if (v === "ac") { inp.value = ""; scr.textContent = "0"; return; }
      if (v === "bs") { inp.value = inp.value.slice(0, -1); return; }
      if (v === "=") { run(); return; }
      inp.value += v; inp.focus(); };
    inp.onkeydown = (e) => { e.stopPropagation(); if (e.key === "Enter") run(); };
    /* a small parser: numbers, + - * / ^, parentheses, the functions on the keys, pi, e, Ans */
    function evaluate(src) {
      const s = src.replace(/×/g, "*").replace(/÷/g, "/").replace(/−/g, "-").replace(/\s+/g, ""); let i = 0;
      const peek = () => s[i], eat = (c) => { if (s[i] === c) { i++; return true; } return false; };
      const toR = (x) => deg ? x * Math.PI / 180 : x, fromR = (x) => deg ? x * 180 / Math.PI : x;
      const F = {sin: (x) => Math.sin(toR(x)), cos: (x) => Math.cos(toR(x)), tan: (x) => Math.tan(toR(x)), asin: (x) => fromR(Math.asin(x)), acos: (x) => fromR(Math.acos(x)), atan: (x) => fromR(Math.atan(x)),
        sqrt: Math.sqrt, ln: Math.log, log: Math.log10, exp: Math.exp, abs: Math.abs};
      function expr() { let v = term(); for (;;) { if (eat("+")) v += term(); else if (eat("-")) v -= term(); else return v; } }
      function term() { let v = power(); for (;;) { if (eat("*")) v *= power(); else if (eat("/")) v /= power(); else if (/[a-zA-Z(πp]/.test(peek() || "") ) v *= power(); else return v; } }
      function power() { const b = unary(); if (eat("^")) return Math.pow(b, power()); return b; }
      function unary() { if (eat("-")) return -unary(); if (eat("+")) return unary(); return atom(); }
      function atom() {
        if (eat("(")) { const v = expr(); if (!eat(")")) throw 0; return v; }
        const m = /^(\d+\.?\d*|\.\d+)(E[+-]?\d+)?/.exec(s.slice(i)); if (m) { i += m[0].length; return parseFloat(m[0].replace("E", "e")); }
        const w = /^[a-zA-Zπ]+/.exec(s.slice(i)); if (!w) throw 0; i += w[0].length; const n = w[0];
        if (n === "pi" || n === "π") return Math.PI; if (n === "e") return Math.E; if (n === "Ans") return ans;
        if (F[n]) { if (!eat("(")) throw 0; const v = expr(); if (!eat(")")) throw 0; return F[n](v); }
        throw 0; }
      const v = expr(); if (i < s.length) throw 0; return v; }
    function run() { const src = inp.value.trim(); if (!src) return; try { const v = evaluate(src); if (!isFinite(v)) throw 0; ans = v; hh.textContent = src + " ="; scr.textContent = fmt(v); inp.value = ""; }
      catch (e) { scr.textContent = L(o).err; } }
    return {lang() {}};
  }

  /* ---------------- worksheet table ---------------- */
  function table(el, o) {
    css(); const KEY = o.key; let data = store.get(KEY) || {rows: o.rows || 12, cols: o.cols || 6, v: {}};
    if (o.head && !store.get(KEY)) o.head.forEach((h, j) => data.v["0," + j] = h);
    if (o.init && !store.get(KEY)) o.init.forEach((row, i) => row.forEach((c, j) => data.v[(i + 1) + "," + j] = c));
    const wrap = document.createElement("div"); wrap.className = "dd-tab"; const bar = document.createElement("div"); bar.className = "dd-tabbar"; el.append(wrap, bar);
    function build() {
      let h = "<table>"; for (let i = 0; i <= data.rows; i++) { h += "<tr>"; for (let j = 0; j < data.cols; j++) h += '<td><input data-c="' + i + "," + j + '" value="' + String(data.v[i + "," + j] || "").replace(/"/g, "&quot;") + '"></td>'; h += "</tr>"; }
      wrap.innerHTML = h + "</table>";
      for (const c of wrap.querySelectorAll("input")) { c.oninput = () => { data.v[c.dataset.c] = c.value; store.set(KEY, data); }; c.onkeydown = (e) => { e.stopPropagation();
        if (e.key === "Enter" || e.key === "ArrowDown" || e.key === "ArrowUp") { const [i, j] = c.dataset.c.split(",").map(Number), n = wrap.querySelector('[data-c="' + (i + (e.key === "ArrowUp" ? -1 : 1)) + "," + j + '"]'); if (n) { e.preventDefault(); n.focus(); } } }; }
      const t = L(o); bar.innerHTML = '<button data-a="add">' + t.addRow + '</button><button data-a="del">' + t.delRow + '</button><button data-a="clr">' + t.clear + "</button>";
      bar.querySelector('[data-a=add]').onclick = () => { data.rows++; store.set(KEY, data); build(); };
      bar.querySelector('[data-a=del]').onclick = () => { if (data.rows > 1) { for (let j = 0; j < data.cols; j++) delete data.v[data.rows + "," + j]; data.rows--; store.set(KEY, data); build(); } };
      bar.querySelector('[data-a=clr]').onclick = () => { if (confirm(t.sure)) { const head = {}; for (let j = 0; j < data.cols; j++) head["0," + j] = data.v["0," + j] || ""; data.v = head; store.set(KEY, data); build(); } };
    }
    build();
    return {lang: build, show(v) { wrap.style.display = bar.style.display = v ? "" : "none"; }};
  }
  window.DataDesk = {paper, calc, table};
})();
