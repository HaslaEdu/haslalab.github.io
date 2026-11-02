/* ==========================================================================
   HaslaLab — Excel on the simulated exam laptops
   --------------------------------------------------------------------------
   VExcel({ lang, host }) builds a spreadsheet window: a ribbon (File, Home,
   Insert), the name box and formula bar, the grid, sheet tabs and a status
   bar with the sum and average of the selection.  Formulas are worked out
   by xlsx-lite (SUM, AVERAGE, SLOPE, INTERCEPT, LN, MAX, MATCH, INDEX …);
   charts are scatter or line charts with axis titles, logarithmic axes and
   trendlines (linear, exponential, logarithmic, power) showing their
   equation and R².  Workbooks are opened from and saved to the laptop's
   own files (host), and a copy can be downloaded as a real .xlsx or .csv.

   The host (a simulator's canvas desktop) puts .el over the window's client
   area with place(x, y, w, h, visible, scale), as it does a VBrowser, and
   draws VExcel.sketch() in its place while the window is moving or hidden.
     host.list()          → [{ id, path }]  workbooks and CSV files on the laptop
     host.load(id)        → { name, wb, id } the workbook of a file
     host.save(doc)       → saves doc.wb back to doc.id (false: ask for a name)
     host.saveAs(doc, folderId, name, type) → { id, name } a new file
     host.folders()       → [{ id, path }]  where Save As may put a file
   ========================================================================== */
(function () {
  "use strict";
  const X = window.HLXlsx;
  const CSS = `
.vx{position:absolute;display:flex;flex-direction:column;background:#fff;color:#1b1b1b;font:12px "Segoe UI Variable Text","Segoe UI","Malgun Gothic","Apple SD Gothic Neo",Roboto,Arial,sans-serif;overflow:hidden;z-index:40;box-sizing:border-box;transform-origin:0 0;user-select:none}
.vx *{box-sizing:border-box}
.vx-tabs{flex:none;display:flex;align-items:flex-end;gap:2px;height:30px;padding:0 8px;background:#107c41;color:#fff}
.vx-tabs button{border:0;background:none;color:#fff;font:inherit;font-size:12.5px;padding:6px 12px;cursor:pointer;border-radius:4px 4px 0 0}
.vx-tabs button.on{background:#f3f3f3;color:#107c41;font-weight:600}
.vx-tabs .file{background:#0b5e31}
.vx-tabs .doc{margin-left:auto;align-self:center;font-size:12px;opacity:.9;padding-right:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:50%}
.vx-rib{flex:none;display:flex;align-items:center;gap:2px;height:58px;padding:4px 8px;background:#f3f3f3;border-bottom:1px solid #d6d6d6;overflow:hidden}
.vx-rib button{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;min-width:52px;height:50px;border:1px solid transparent;border-radius:4px;background:none;font:inherit;font-size:11px;color:#1b1b1b;cursor:pointer;padding:2px 6px}
.vx-rib button:hover{background:#e1e1e1;border-color:#d0d0d0}
.vx-rib button:disabled{opacity:.4;cursor:default;background:none;border-color:transparent}
.vx-rib button.on{background:#d3e9db;border-color:#9fcfb2}
.vx-rib button i{font-style:normal;font-size:18px;line-height:20px}
.vx-rib .sep{width:1px;height:42px;background:#d6d6d6;margin:0 6px}
.vx-fbar{flex:none;display:flex;align-items:center;height:28px;border-bottom:1px solid #d6d6d6;background:#fff}
.vx-name{width:90px;height:22px;margin:0 6px;border:1px solid #c8c8c8;font:inherit;padding:0 4px;outline:0}
.vx-fx{flex:none;width:30px;text-align:center;color:#666;font-style:italic;border-left:1px solid #e1e1e1;border-right:1px solid #e1e1e1}
.vx-fin{flex:1;height:26px;border:0;outline:0;font:inherit;font-size:12.5px;padding:0 6px;user-select:text}
.vx-body{flex:1;position:relative;min-height:0;overflow:hidden;background:#fff}
.vx-cv{position:absolute;left:0;top:0;cursor:cell}
.vx-ed{position:absolute;border:2px solid #107c41;outline:0;font:12.5px Calibri,"Segoe UI","Malgun Gothic",sans-serif;padding:0 3px;background:#fff;color:#1b1b1b;z-index:3;user-select:text}
.vx-ed.off{opacity:0;pointer-events:none;width:1px!important;height:1px!important;border:0;padding:0}
.vx-ch{position:absolute;border:1px solid #bfbfbf;background:#fff;z-index:2;cursor:move}
.vx-ch.sel{border:1px solid #107c41;box-shadow:0 0 0 1px #107c41}
.vx-ch canvas{position:absolute;left:0;top:0;width:100%;height:100%}
.vx-ch .rz{position:absolute;right:-5px;bottom:-5px;width:10px;height:10px;background:#fff;border:1px solid #107c41;cursor:nwse-resize;display:none}
.vx-ch.sel .rz{display:block}
.vx-sheets{flex:none;display:flex;align-items:stretch;height:26px;background:#f3f3f3;border-top:1px solid #d6d6d6;padding-left:8px;overflow:hidden}
.vx-sheets button{border:0;border-right:1px solid #d6d6d6;background:none;font:inherit;padding:0 14px;cursor:pointer;color:#333}
.vx-sheets button.on{background:#fff;color:#107c41;font-weight:600;border-bottom:2px solid #107c41}
.vx-sheets .add{font-size:16px;color:#555;padding:0 10px}
.vx-stat{flex:none;display:flex;justify-content:flex-end;gap:18px;height:22px;align-items:center;padding:0 12px;background:#107c41;color:#fff;font-size:11.5px}
.vx-stat .msg{margin-right:auto}
.vx-dlg{position:absolute;inset:0;background:rgba(0,0,0,.25);display:flex;align-items:center;justify-content:center;z-index:10}
.vx-dlg>div{background:#fff;border-radius:6px;box-shadow:0 10px 30px rgba(0,0,0,.25);padding:16px 18px;min-width:380px;max-width:92%;max-height:92%;overflow:auto;user-select:text}
.vx-dlg h3{margin:0 0 10px;font-size:15px;font-weight:600}
.vx-dlg label{display:block;margin:6px 0 2px;color:#444}
.vx-dlg input[type=text],.vx-dlg select{width:100%;height:26px;border:1px solid #c8c8c8;border-radius:3px;font:inherit;padding:0 6px}
.vx-dlg .row{display:flex;gap:8px;align-items:center}
.vx-dlg .row>*{flex:1}
.vx-dlg .chk{display:inline-flex;align-items:center;gap:4px;margin:6px 12px 0 0;color:#333}
.vx-dlg .btns{display:flex;justify-content:flex-end;gap:8px;margin-top:14px}
.vx-dlg button{min-width:76px;height:28px;border:1px solid #c8c8c8;border-radius:4px;background:#fff;font:inherit;cursor:pointer}
.vx-dlg button.pri{background:#107c41;border-color:#107c41;color:#fff}
.vx-dlg .ser{border:1px solid #e1e1e1;border-radius:4px;padding:6px 8px;margin-top:8px}
.vx-dlg ul{list-style:none;margin:0;padding:0;max-height:300px;overflow:auto;border:1px solid #e1e1e1}
.vx-dlg li{padding:6px 10px;cursor:pointer;border-bottom:1px solid #f0f0f0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.vx-dlg li:hover,.vx-dlg li.on{background:#e6f2ea}
.vx-menu{position:absolute;background:#fff;border:1px solid #d0d0d0;border-radius:6px;box-shadow:0 6px 18px rgba(0,0,0,.18);padding:4px;z-index:9;min-width:180px}
.vx-menu div{padding:6px 12px;border-radius:4px;cursor:pointer;display:flex;justify-content:space-between;gap:16px}
.vx-menu div:hover{background:#eef4f0}
.vx-menu i{font-style:normal;color:#777}
.vx-menu hr{border:0;border-top:1px solid #e5e5e5;margin:4px 0}`;
  const L = {
    ko: { file: "파일", home: "홈", insert: "삽입", newB: "새로 만들기", open: "열기", save: "저장", saveAs: "다른 이름으로 저장", dl: "내 PC로 내려받기", dlCsv: "CSV로 내려받기", close: "닫기",
      paste: "붙여넣기", cut: "잘라내기", copy: "복사", bold: "굵게", sum: "자동 합계", fill: "아래로 채우기", clear: "지우기", undo: "실행 취소", redo: "다시 실행",
      scatter: "분산형 차트", line: "꺾은선형 차트", chartEdit: "차트 편집", chartDel: "차트 삭제", sheetAdd: "새 시트",
      avg: "평균", count: "개수", sumS: "합계", ready: "준비", book: "통합 문서", chartT: "차트", title: "차트 제목", xT: "가로 축 제목", yT: "세로 축 제목", logX: "가로 축 로그 눈금", logY: "세로 축 로그 눈금",
      series: "계열", name: "이름", xs: "X 값", ys: "Y 값", lines: "선", markers: "표식", trend: "추세선", none: "없음", lin: "선형", exp: "지수", log: "로그", pow: "거듭제곱", eq: "수식 표시", r2: "R² 표시",
      addSer: "계열 추가", delSer: "계열 삭제", ok: "확인", cancel: "취소", openT: "열기", noFiles: "이 PC에 통합 문서나 CSV 파일이 없습니다.", folder: "폴더", fname: "파일 이름", ftype: "파일 형식",
      xlsx: "Excel 통합 문서 (*.xlsx)", csv: "CSV UTF-8 (*.csv)", saved: "저장했습니다", savedTo: (p) => p + "에 저장했습니다", unsaved: (n) => `'${n}'의 변경 내용을 저장하시겠습니까?`, dontSave: "저장 안 함",
      csvOne: "CSV에는 현재 시트만 저장됩니다.", needSel: "차트로 그릴 데이터(열 두 개 이상)를 먼저 선택하세요.", rowIns: "행 삽입", rowDel: "행 삭제", fxBad: "수식에 오류가 있습니다" },
    en: { file: "File", home: "Home", insert: "Insert", newB: "New", open: "Open", save: "Save", saveAs: "Save As", dl: "Download to my computer", dlCsv: "Download as CSV", close: "Close",
      paste: "Paste", cut: "Cut", copy: "Copy", bold: "Bold", sum: "AutoSum", fill: "Fill Down", clear: "Clear", undo: "Undo", redo: "Redo",
      scatter: "Scatter chart", line: "Line chart", chartEdit: "Edit chart", chartDel: "Delete chart", sheetAdd: "New sheet",
      avg: "Average", count: "Count", sumS: "Sum", ready: "Ready", book: "Book", chartT: "Chart", title: "Chart title", xT: "Horizontal axis title", yT: "Vertical axis title", logX: "Logarithmic horizontal axis", logY: "Logarithmic vertical axis",
      series: "Series", name: "Name", xs: "X values", ys: "Y values", lines: "Lines", markers: "Markers", trend: "Trendline", none: "None", lin: "Linear", exp: "Exponential", log: "Logarithmic", pow: "Power", eq: "Display equation", r2: "Display R²",
      addSer: "Add series", delSer: "Remove series", ok: "OK", cancel: "Cancel", openT: "Open", noFiles: "There are no workbooks or CSV files on this PC.", folder: "Folder", fname: "File name", ftype: "Save as type",
      xlsx: "Excel Workbook (*.xlsx)", csv: "CSV UTF-8 (*.csv)", saved: "Saved", savedTo: (p) => "Saved to " + p, unsaved: (n) => `Do you want to save the changes to '${n}'?`, dontSave: "Don't Save",
      csvOne: "Only the current sheet is saved in a CSV file.", needSel: "First select the data to plot (two or more columns).", rowIns: "Insert row", rowDel: "Delete row", fxBad: "There's a problem with this formula" },
  };
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const RH = 21, HW = 46, HH = 21, MAXC = 120, MAXR = 20000, CF = '12.5px Calibri,"Segoe UI","Malgun Gothic",sans-serif';
  const pxW = (w) => Math.round((w || 8.43) * 7 + 5);
  let cssDone = false;

  function VExcel(opt) {
    if (!cssDone) { const st = document.createElement("style"); st.textContent = CSS; document.head.appendChild(st); cssDone = true; }
    const host = opt.host || {}, lang = () => (opt.lang && opt.lang()) === "en" ? "en" : "ko", t = () => L[lang()];
    const el = document.createElement("div"); el.className = "vx"; el.style.display = "none";
    el.innerHTML = `<div class="vx-tabs"></div><div class="vx-rib"></div><div class="vx-fbar"><input class="vx-name" spellcheck="false"><span class="vx-fx">fx</span><input class="vx-fin" spellcheck="false"></div>
      <div class="vx-body"><canvas class="vx-cv"></canvas><input class="vx-ed off" spellcheck="false" autocomplete="off"></div><div class="vx-sheets"></div><div class="vx-stat"></div>`;
    const $ = (s) => el.querySelector(s), tabs = $(".vx-tabs"), rib = $(".vx-rib"), nameBox = $(".vx-name"), fin = $(".vx-fin"), body = $(".vx-body"),
      cv = $(".vx-cv"), ed = $(".vx-ed"), sheetsBar = $(".vx-sheets"), stat = $(".vx-stat");
    let doc = null, si = 0, ribTab = "home", scale = 1, shown = "", W = 0, H = 0, msg = "", msgT = 0;
    let sel = { c0: 0, r0: 0, c1: 0, r1: 0, ac: 0, ar: 0 }, sx = 0, sy = 0, editing = null, chartSel = -1, undo = [], redo = [], clip = null;
    const sh = () => doc.wb.sheets[si];
    function blank(n) { return { name: n || t().book + "1.xlsx", id: null, wb: { sheets: [{ name: "Sheet1", cells: {}, cols: {}, charts: [] }] }, dirty: false, csv: false }; }
    doc = blank();

    /* ── geometry: columns have their own widths, rows are all RH high ── */
    const colPx = (c) => pxW(sh().cols && sh().cols[c]);
    function colX(c) { let x = 0; for (let i = 0; i < c; i++) x += colPx(i); return x; }
    function colAt(x) { let s = 0; for (let c = 0; c < MAXC; c++) { const w = colPx(c); if (x < s + w) return c; s += w; } return MAXC - 1; }
    const rowAt = (y) => Math.max(0, Math.min(MAXR - 1, Math.floor(y / RH)));
    function nRows() { const b = X.bounds(sh()); return Math.max(60, b.r1 + 40, sel.r1 + 30); }

    /* ── the cells ── */
    const cell = (c, r, s) => (s || sh()).cells[X.ref(c, r)];
    function setCells(changes, sheetIdx) {        /* [{k, cell|null}] as one undoable step */
      const s = doc.wb.sheets[sheetIdx ?? si], before = changes.map(({ k }) => ({ k, cell: s.cells[k] ? { ...s.cells[k] } : null }));
      for (const { k, cell: c } of changes) { if (c && (c.v !== null && c.v !== undefined && c.v !== "" || c.f || c.b)) s.cells[k] = c; else delete s.cells[k]; }
      undo.push({ si: sheetIdx ?? si, before, after: changes.map(({ k, cell: c }) => ({ k, cell: c ? { ...c } : null })) }); if (undo.length > 80) undo.shift(); redo = [];
      dirty();
    }
    function applyStep(step, back) {
      const s = doc.wb.sheets[step.si]; if (!s) return;
      for (const { k, cell: c } of back ? step.before : step.after) { if (c) s.cells[k] = { ...c }; else delete s.cells[k]; }
      si = step.si; dirty();
    }
    function chartStep(fn) { const s = sh(), before = JSON.stringify(s.charts || []); fn(s); undo.push({ si, charts: [before, JSON.stringify(s.charts || [])] }); redo = []; dirty(); }
    function doUndo(re) {
      const step = (re ? redo : undo).pop(); if (!step) return; (re ? undo : redo).push(step);
      const s = doc.wb.sheets[step.si]; if (!s) return;
      if (step.charts) { s.charts = JSON.parse(step.charts[re ? 1 : 0]); si = step.si; chartSel = -1; dirty(); }
      else if (step.all) { s.cells = JSON.parse(re ? step.after : step.before); si = step.si; dirty(); }
      else applyStep(step, !re);
    }
    function dirty() { doc.dirty = true; recalc(); draw(); opt.onchange && opt.onchange(); }
    function recalc() { try { X.calc(doc.wb); } catch (e) {} }
    function parseInput(s) {
      if (typeof s !== "string") return { v: s };
      if (s.startsWith("=") && s.length > 1) return { f: s.slice(1), v: null };
      const v = X.typed(s); return { v: v === null ? null : v };
    }
    function editText(c) { if (!c) return ""; if (c.f) return "=" + c.f; return c.v === null || c.v === undefined ? "" : X.show(c.v); }
    function commit(text, c, r) {
      const old = cell(c, r), p = parseInput(text);
      if (p.f) { try { X.parseFormula(p.f); } catch (e) { if (!(X.isErr(e) && e.c === "#NAME?")) say(t().fxBad); } }   /* an unknown function shows #NAME?, as in Excel */
      const nc = p.f || (p.v !== null && p.v !== undefined) ? { ...p, ...(old && old.b ? { b: true } : {}) } : old && old.b ? { v: null, b: true } : null;
      setCells([{ k: X.ref(c, r), cell: nc }]);
    }

    /* ── drawing the grid ── */
    function fit() { const r = body.getBoundingClientRect(); W = Math.max(50, Math.round(body.clientWidth)); H = Math.max(50, Math.round(body.clientHeight)); const d = 2;
      if (cv.width !== W * d || cv.height !== H * d) { cv.width = W * d; cv.height = H * d; cv.style.width = W + "px"; cv.style.height = H + "px"; } return r; }
    function cellText(c) {
      if (!c) return ["", "l"]; const v = c.v;
      if (X.isErr(v)) return [v.c, "c"]; if (typeof v === "number") return [X.fmtNum(v), "r"]; if (typeof v === "boolean") return [v ? "TRUE" : "FALSE", "c"];
      return [v == null ? "" : String(v), "l"];
    }
    function fitNum(g, v, w) {
      let s = X.fmtNum(v); if (g.measureText(s).width <= w) return s;
      for (let p = 9; p >= 1; p--) { const a = Math.abs(v), u = a >= 1e-4 && a < 1e9 ? String(+v.toPrecision(p)) : v.toExponential(Math.max(0, p - 1)).replace("e", "E"); if (g.measureText(u).width <= w) return u; }
      return "#".repeat(Math.max(1, Math.floor(w / 7)));
    }
    function draw() {
      if (el.style.display === "none") return;
      fit(); const g = cv.getContext("2d"); g.setTransform(2, 0, 0, 2, 0, 0); g.clearRect(0, 0, W, H);
      g.fillStyle = "#fff"; g.fillRect(0, 0, W, H); g.font = CF; g.textBaseline = "middle";
      const c0 = colAt(sx), r0 = rowAt(sy), x0 = HW + colX(c0) - sx, y0 = HH + r0 * RH - sy;
      const cols = []; for (let c = c0, x = x0; x < W && c < MAXC; c++) { const w = colPx(c); cols.push([c, x, w]); x += w; }
      const rows = []; for (let r = r0, y = y0; y < H && r < MAXR; r++) { rows.push([r, y]); y += RH; }
      const S = sel, inSel = (c, r) => c >= S.c0 && c <= S.c1 && r >= S.r0 && r <= S.r1;
      /* selection fill */
      const sxA = HW + colX(S.c0) - sx, syA = HH + S.r0 * RH - sy, sw = colX(S.c1 + 1) - colX(S.c0), shh = (S.r1 - S.r0 + 1) * RH;
      if (S.c1 > S.c0 || S.r1 > S.r0) { g.fillStyle = "rgba(16,124,65,0.10)"; g.fillRect(sxA, syA, sw, shh); }
      /* grid lines */
      g.strokeStyle = "#e1e1e1"; g.lineWidth = 1; g.beginPath();
      for (const [, x, w] of cols) { g.moveTo(Math.round(x + w) + 0.5, HH); g.lineTo(Math.round(x + w) + 0.5, H); }
      for (const [, y] of rows) { g.moveTo(HW, Math.round(y + RH) + 0.5); g.lineTo(W, Math.round(y + RH) + 0.5); }
      g.stroke();
      /* cells: text overflows into empty cells on its right, as in Excel */
      const s = sh();
      for (const [r, y] of rows) for (let i = 0; i < cols.length; i++) {
        const [c, x, w] = cols[i], cc = s.cells[X.ref(c, r)]; if (!cc) continue;
        const [txt0, al] = cellText(cc); if (!txt0) continue;
        g.font = (cc.b ? "bold " : "") + CF; g.fillStyle = X.isErr(cc.v) ? "#c00" : "#1b1b1b";
        let txt = typeof cc.v === "number" ? fitNum(g, cc.v, w - 6) : txt0, room = w;
        if (al === "l") { for (let j = i + 1; j < cols.length && !s.cells[X.ref(cols[j][0], r)]; j++) room += cols[j][2]; }
        g.save(); g.beginPath(); g.rect(x + 1, y, room - 2, RH); g.clip();
        g.textAlign = al === "r" ? "right" : al === "c" ? "center" : "left";
        g.fillText(txt, al === "r" ? x + w - 4 : al === "c" ? x + w / 2 : x + 4, y + RH / 2 + 1); g.restore();
      }
      /* headers */
      g.font = '12px "Segoe UI","Malgun Gothic",sans-serif'; g.textAlign = "center";
      g.fillStyle = "#f3f3f3"; g.fillRect(0, 0, W, HH); g.fillRect(0, 0, HW, H);
      for (const [c, x, w] of cols) { const on = c >= S.c0 && c <= S.c1; if (on) { g.fillStyle = "#d3e9db"; g.fillRect(x, 0, w, HH); g.fillStyle = "#107c41"; g.fillRect(x, HH - 2, w, 2); }
        g.fillStyle = on ? "#0b5e31" : "#444"; g.fillText(X.colName(c), x + w / 2, HH / 2 + 1); g.fillStyle = "#d0d0d0"; g.fillRect(Math.round(x + w), 0, 1, HH); }
      for (const [r, y] of rows) { const on = r >= S.r0 && r <= S.r1; if (on) { g.fillStyle = "#d3e9db"; g.fillRect(0, y, HW, RH); g.fillStyle = "#107c41"; g.fillRect(HW - 2, y, 2, RH); }
        g.fillStyle = on ? "#0b5e31" : "#444"; g.fillText(String(r + 1), HW / 2, y + RH / 2 + 1); g.fillStyle = "#d0d0d0"; g.fillRect(0, Math.round(y + RH), HW, 1); }
      g.fillStyle = "#e6e6e6"; g.fillRect(0, 0, HW, HH); g.strokeStyle = "#c8c8c8"; g.beginPath(); g.moveTo(0, HH + 0.5); g.lineTo(W, HH + 0.5); g.moveTo(HW + 0.5, 0); g.lineTo(HW + 0.5, H); g.stroke();
      /* the selection outline, the active cell and the fill handle */
      g.save(); g.beginPath(); g.rect(HW, HH, W - HW, H - HH); g.clip();
      g.strokeStyle = "#107c41"; g.lineWidth = 2; g.strokeRect(sxA + 1, syA + 1, sw - 1, shh - 1);
      const ax = HW + colX(S.ac) - sx, ay = HH + S.ar * RH - sy; g.lineWidth = 1; if (S.c1 > S.c0 || S.r1 > S.r0) { g.strokeStyle = "#107c41"; g.strokeRect(ax + 1.5, ay + 1.5, colPx(S.ac) - 3, RH - 3); }
      g.fillStyle = "#107c41"; g.fillRect(sxA + sw - 3, syA + shh - 3, 6, 6); g.fillStyle = "#fff"; g.fillRect(sxA + sw - 4, syA + shh - 4, 1, 8); g.fillRect(sxA + sw - 4, syA + shh - 4, 8, 1);
      if (clip && clip.si === si && clip.cut) { g.setLineDash([4, 3]); g.strokeStyle = "#107c41"; const cx = HW + colX(clip.c0) - sx, cy = HH + clip.r0 * RH - sy; g.strokeRect(cx + 0.5, cy + 0.5, colX(clip.c1 + 1) - colX(clip.c0), (clip.r1 - clip.r0 + 1) * RH); g.setLineDash([]); }
      g.restore();
      drawCharts(); paintBars(); placeEditor();
    }

    /* ── charts ── */
    let chartEls = [];
    function rangeVals(refText, s) {
      const r = X.parseRange(refText || ""); if (!r) return [];
      const S = r.sheet ? doc.wb.sheets.find((q) => q.name.toLowerCase() === r.sheet.toLowerCase()) : s; if (!S) return [];
      const out = []; for (let rr = r.r0; rr <= Math.min(r.r1, r.r0 + 20000); rr++) for (let cc = r.c0; cc <= r.c1; cc++) { const c = S.cells[X.ref(cc, rr)]; out.push(c && typeof c.v === "number" && Number.isFinite(c.v) ? c.v : null); }
      return out;
    }
    function drawCharts() {
      const s = sh(), list = s.charts || [];
      while (chartEls.length > list.length) chartEls.pop().remove();
      while (chartEls.length < list.length) { const d = document.createElement("div"); d.className = "vx-ch"; d.innerHTML = '<canvas></canvas><div class="rz"></div>'; body.appendChild(d); chartEls.push(d); hookChart(d); }
      list.forEach((ch, i) => {
        const d = chartEls[i], at = ch.at || (ch.at = { c0: 3, r0: 1, c1: 10, r1: 16 }), x = HW + colX(at.c0) - sx, y = HH + at.r0 * RH - sy, w = Math.max(160, colX(at.c1) - colX(at.c0)), h = Math.max(110, (at.r1 - at.r0) * RH);
        d.dataset.i = i; d.classList.toggle("sel", chartSel === i);
        Object.assign(d.style, { left: x + "px", top: y + "px", width: w + "px", height: h + "px", display: x + w < HW || y + h < HH || x > W || y > H ? "none" : "block" });
        const c = d.firstChild, key = JSON.stringify([w, h, ch, doc.wb._gen]);
        if (c._key !== key) { c._key = key; c.width = w * 2; c.height = h * 2; const g = c.getContext("2d"); g.setTransform(2, 0, 0, 2, 0, 0); VExcel.drawChart(g, w, h, ch, (rf) => rangeVals(rf, s)); }
      });
    }
    function hookChart(d) {
      d.addEventListener("pointerdown", (e) => {
        e.stopPropagation(); e.preventDefault(); stopEdit(true);
        const i = +d.dataset.i, ch = sh().charts[i], at0 = { ...ch.at }, p0 = pt(e), rz = e.target.classList.contains("rz");
        chartSel = i; draw(); ed.focus({ preventScroll: true });
        let moved = false;
        const mv = (m) => { const p = pt(m), dx = p[0] - p0[0], dy = p[1] - p0[1]; if (Math.abs(dx) + Math.abs(dy) < 3 && !moved) return; moved = true;
          if (rz) { ch.at.c1 = Math.max(at0.c0 + 2, colAt(colX(at0.c1) + dx) ); ch.at.r1 = Math.max(at0.r0 + 4, at0.r1 + Math.round(dy / RH)); }
          else { const nc = Math.max(0, colAt(Math.max(0, colX(at0.c0) + dx + 4))), nr = Math.max(0, at0.r0 + Math.round(dy / RH)), wc = at0.c1 - at0.c0, hr = at0.r1 - at0.r0; ch.at = { c0: nc, r0: nr, c1: nc + wc, r1: nr + hr }; }
          draw(); };
        const up = () => { window.removeEventListener("pointermove", mv); window.removeEventListener("pointerup", up); if (moved) { const after = { ...ch.at }; ch.at = at0; chartStep(() => { ch.at = after; }); } };
        window.addEventListener("pointermove", mv); window.addEventListener("pointerup", up);
      });
      d.addEventListener("dblclick", (e) => { e.stopPropagation(); chartDialog(+d.dataset.i); });
      d.addEventListener("contextmenu", (e) => { e.preventDefault(); e.stopPropagation(); chartSel = +d.dataset.i; draw(); menu(e, [[t().chartEdit, () => chartDialog(chartSel)], [t().chartDel, () => delChart()]]); });
    }
    function delChart() { if (chartSel < 0) return; const i = chartSel; chartSel = -1; chartStep((s) => s.charts.splice(i, 1)); }
    function insertChart(type) {
      const s = sh(), S = sel, cols = S.c1 - S.c0 + 1;
      if (cols < 2 && S.r1 === S.r0) { say(t().needSel); return; }
      let r0 = S.r0; const head = cell(S.c0 + (cols > 1 ? 1 : 0), r0), hasHead = head && typeof head.v === "string";
      if (hasHead) r0++;
      let r1 = S.r1; if (S.r1 === S.r0) { r1 = X.bounds(s).r1; }
      const rng = (c) => X.absRange(s.name, c, r0, c, Math.max(r0, r1));
      const series = [];
      if (cols === 1) series.push({ name: hasHead ? X.show(head.v) : "", x: "", y: rng(S.c0), line: type === "line", marker: true, trend: null });
      else for (let c = S.c0 + 1; c <= S.c1; c++) { const h = cell(c, S.r0); series.push({ name: hasHead && h ? X.show(h.v) : "", x: rng(S.c0), y: rng(c), line: type === "line", marker: true, trend: null }); }
      const xh = cell(S.c0, S.r0), c0 = S.c1 + 2;
      const ch = { type: type === "line" ? "line" : "scatter", title: "", x: { title: hasHead && xh && cols > 1 ? X.show(xh.v) : "", log: false }, y: { title: series.length === 1 ? series[0].name : "", log: false }, series, at: { c0, r0: S.r0, c1: c0 + 8, r1: S.r0 + 16 } };
      chartStep((sh2) => { (sh2.charts || (sh2.charts = [])).push(ch); }); chartSel = sh().charts.length - 1; draw(); chartDialog(chartSel);
    }

    /* ── the editor: one input, invisible until typing starts, so a key always lands somewhere the page ignores ── */
    function placeEditor() {
      const S = sel, x = HW + colX(S.ac) - sx, y = HH + S.ar * RH - sy;
      if (editing) { const w = Math.max(colPx(S.ac), Math.min(420, ed.value.length * 7.5 + 16)); Object.assign(ed.style, { left: x - 1 + "px", top: y - 1 + "px", width: w + 2 + "px", height: RH + 2 + "px" }); }
      else Object.assign(ed.style, { left: Math.max(HW, Math.min(W - 4, x)) + "px", top: Math.max(HH, Math.min(H - 4, y)) + "px" });
    }
    function startEdit(text, mode) { editing = { c: sel.ac, r: sel.ar, mode }; ed.classList.remove("off"); ed.value = text; placeEditor(); fin.value = text; ed.focus({ preventScroll: true });
      const n = ed.value.length; try { ed.setSelectionRange(n, n); } catch (e) {} }
    function stopEdit(save) {
      if (!editing) return; const e = editing; editing = null; const v = ed.value;
      ed.classList.add("off"); ed.value = "";
      if (save) commit(v, e.c, e.r); else draw();
    }
    function finEdit() { const s = sel; return { c: s.ac, r: s.ar }; }
    ed.addEventListener("input", () => {
      if (!editing) { const v = ed.value; if (!v) return; startEdit(v, "enter"); }
      fin.value = ed.value; placeEditor();
    });
    ed.addEventListener("compositionstart", () => { if (!editing) startEdit("", "enter"); });
    fin.addEventListener("focus", () => { fin._c = finEdit(); });
    fin.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); const p = fin._c || finEdit(); commit(fin.value, p.c, p.r); move(0, 1, false); ed.focus({ preventScroll: true }); }
      else if (e.key === "Escape") { fin.value = editText(cell(sel.ac, sel.ar)); ed.focus({ preventScroll: true }); }
      e.stopPropagation();
    });
    nameBox.addEventListener("keydown", (e) => {
      e.stopPropagation(); if (e.key !== "Enter") return; e.preventDefault();
      const r = X.parseRange(nameBox.value.toUpperCase()); if (r) { sel = { c0: r.c0, r0: r.r0, c1: r.c1, r1: r.r1, ac: r.c0, ar: r.r0 }; reveal(); draw(); }
      ed.focus({ preventScroll: true });
    });
    function canPickRef() { if (!editing || !ed.value.startsWith("=")) return false; const i = ed.selectionStart ?? ed.value.length, ch = ed.value.slice(0, i).trimEnd().slice(-1); return /[=(,+\-*/^&<>:;]/.test(ch); }

    /* ── selection and moving ── */
    function reveal() {
      const x = colX(sel.ac), w = colPx(sel.ac), y = sel.ar * RH;
      if (x < sx) sx = x; else if (x + w > sx + W - HW) sx = x + w - (W - HW);
      if (y < sy) sy = y; else if (y + RH > sy + H - HH) sy = y + RH - (H - HH);
      sx = Math.max(0, sx); sy = Math.max(0, sy);
    }
    function move(dc, dr, extend) {
      const S = sel;
      if (extend) { let c = (S.ac === S.c0 ? S.c1 : S.c0) + dc, r = (S.ar === S.r0 ? S.r1 : S.r0) + dr; c = Math.max(0, Math.min(MAXC - 1, c)); r = Math.max(0, Math.min(MAXR - 1, r));
        sel = { c0: Math.min(S.ac, c), c1: Math.max(S.ac, c), r0: Math.min(S.ar, r), r1: Math.max(S.ar, r), ac: S.ac, ar: S.ar }; }
      else { const c = Math.max(0, Math.min(MAXC - 1, S.ac + dc)), r = Math.max(0, Math.min(MAXR - 1, S.ar + dr)); sel = { c0: c, c1: c, r0: r, r1: r, ac: c, ar: r }; }
      chartSel = -1; reveal(); draw();
    }
    function jump(dc, dr) {          /* Ctrl+arrow: to the edge of the data */
      const s = sh(); let c = sel.ac, r = sel.ar; const has = (cc, rr) => !!s.cells[X.ref(cc, rr)], b = X.bounds(s);
      const lim = (cc, rr) => cc >= 0 && rr >= 0 && cc <= Math.max(b.c1, 0) + 1 && rr <= Math.max(b.r1, 0) + 1;
      if (has(c, r) && has(c + dc, r + dr)) { while (lim(c + dc, r + dr) && has(c + dc, r + dr)) { c += dc; r += dr; } }
      else { c += dc; r += dr; while (lim(c, r) && !has(c, r)) { c += dc; r += dr; } if (!lim(c, r)) { c = dc ? (dc > 0 ? b.c1 : 0) : c; r = dr ? (dr > 0 ? b.r1 : 0) : r; } }
      sel = { c0: Math.max(0, c), c1: Math.max(0, c), r0: Math.max(0, r), r1: Math.max(0, r), ac: Math.max(0, c), ar: Math.max(0, r) }; reveal(); draw();
    }
    const pt = (e) => { const r = body.getBoundingClientRect(); return [(e.clientX - r.left) / scale, (e.clientY - r.top) / scale]; };
    let drag = null;
    cv.addEventListener("pointerdown", (e) => {
      if (e.button === 2) return;
      const [x, y] = pt(e); e.preventDefault(); chartSel = -1;
      if (y < HH && x > HW) {                       /* a column border: resize; a header: the column */
        let acc = HW - sx; for (let c = 0; c < MAXC; c++) { acc += colPx(c); if (Math.abs(x - acc) <= 3) { drag = { k: "cw", c, x0: x, w0: colPx(c) }; cv.setPointerCapture(e.pointerId); return; } if (acc > x + 4) break; }
        stopEdit(true); const c = colAt(x - HW + sx); sel = { c0: c, c1: c, r0: 0, r1: nRows() - 1, ac: c, ar: 0 }; drag = { k: "cols", c }; cv.setPointerCapture(e.pointerId); draw(); ed.focus({ preventScroll: true }); return; }
      if (x < HW && y > HH) { stopEdit(true); const r = rowAt(y - HH + sy); sel = { c0: 0, c1: 20, r0: r, r1: r, ac: 0, ar: r }; drag = { k: "rows", r }; cv.setPointerCapture(e.pointerId); draw(); ed.focus({ preventScroll: true }); return; }
      if (x < HW || y < HH) { stopEdit(true); sel = { c0: 0, r0: 0, c1: 30, r1: nRows() - 1, ac: 0, ar: 0 }; draw(); return; }
      const c = colAt(x - HW + sx), r = rowAt(y - HH + sy);
      /* the fill handle */
      const hx = HW + colX(sel.c1 + 1) - sx, hy = HH + (sel.r1 + 1) * RH - sy;
      if (!editing && Math.abs(x - hx) <= 5 && Math.abs(y - hy) <= 5) { drag = { k: "fill", c1: sel.c1, r1: sel.r1 }; cv.setPointerCapture(e.pointerId); return; }
      if (canPickRef()) {                           /* a click while writing a formula puts the cell into it */
        const at = ed.selectionStart ?? ed.value.length, a = X.ref(c, r);
        ed.value = ed.value.slice(0, at) + a + ed.value.slice(ed.selectionEnd ?? at); const n = at + a.length; ed.setSelectionRange(n, n); fin.value = ed.value;
        drag = { k: "ref", c, r, at, len: a.length }; cv.setPointerCapture(e.pointerId); ed.focus({ preventScroll: true }); return; }
      stopEdit(true);
      if (e.shiftKey) sel = { c0: Math.min(sel.ac, c), c1: Math.max(sel.ac, c), r0: Math.min(sel.ar, r), r1: Math.max(sel.ar, r), ac: sel.ac, ar: sel.ar };
      else sel = { c0: c, c1: c, r0: r, r1: r, ac: c, ar: r };
      drag = { k: "sel" }; cv.setPointerCapture(e.pointerId); draw(); ed.focus({ preventScroll: true });
    });
    cv.addEventListener("pointermove", (e) => {
      const [x, y] = pt(e);
      if (!drag) { let cur = "cell"; if (y < HH && x > HW) { let acc = HW - sx; for (let c = 0; c < MAXC; c++) { acc += colPx(c); if (Math.abs(x - acc) <= 3) { cur = "col-resize"; break; } if (acc > x + 4) break; } if (cur === "cell") cur = "s-resize"; }
        else { const hx = HW + colX(sel.c1 + 1) - sx, hy = HH + (sel.r1 + 1) * RH - sy; if (Math.abs(x - hx) <= 5 && Math.abs(y - hy) <= 5) cur = "crosshair"; }
        cv.style.cursor = cur; return; }
      const c = colAt(Math.max(0, x - HW + sx)), r = rowAt(Math.max(0, y - HH + sy));
      if (drag.k === "cw") { const w = Math.max(12, drag.w0 + x - drag.x0); (sh().cols || (sh().cols = {}))[drag.c] = +((w - 5) / 7).toFixed(2); doc.dirty = true; draw(); return; }
      if (drag.k === "sel") { sel = { c0: Math.min(sel.ac, c), c1: Math.max(sel.ac, c), r0: Math.min(sel.ar, r), r1: Math.max(sel.ar, r), ac: sel.ac, ar: sel.ar }; draw(); }
      else if (drag.k === "cols") { sel = { c0: Math.min(drag.c, c), c1: Math.max(drag.c, c), r0: 0, r1: nRows() - 1, ac: drag.c, ar: 0 }; draw(); }
      else if (drag.k === "rows") { sel = { c0: 0, c1: 20, r0: Math.min(drag.r, r), r1: Math.max(drag.r, r), ac: 0, ar: drag.r }; draw(); }
      else if (drag.k === "fill") { drag.to = r - sel.r1 >= c - sel.c1 ? { r, c: sel.c1 } : { r: sel.r1, c }; const d2 = drag.to; draw();
        const g = cv.getContext("2d"); g.setTransform(2, 0, 0, 2, 0, 0); g.setLineDash([3, 3]); g.strokeStyle = "#555";
        g.strokeRect(HW + colX(sel.c0) - sx + 0.5, HH + sel.r0 * RH - sy + 0.5, colX(Math.max(d2.c, sel.c1) + 1) - colX(sel.c0), (Math.max(d2.r, sel.r1) - sel.r0 + 1) * RH); g.setLineDash([]); }
      else if (drag.k === "ref") { const a = X.ref(Math.min(drag.c, c), Math.min(drag.r, r)) + (c !== drag.c || r !== drag.r ? ":" + X.ref(Math.max(drag.c, c), Math.max(drag.r, r)) : "");
        ed.value = ed.value.slice(0, drag.at) + a + ed.value.slice(drag.at + drag.len); drag.len = a.length; const n = drag.at + a.length; ed.setSelectionRange(n, n); fin.value = ed.value; placeEditor(); }
    });
    cv.addEventListener("pointerup", () => { if (drag && drag.k === "fill" && drag.to) fill(drag.to); drag = null; });
    cv.addEventListener("dblclick", (e) => { const [x, y] = pt(e); if (x < HW || y < HH) return; startEdit(editText(cell(sel.ac, sel.ar)), "edit"); });
    cv.addEventListener("contextmenu", (e) => { e.preventDefault(); const [x, y] = pt(e); if (x > HW && y > HH) { const c = colAt(x - HW + sx), r = rowAt(y - HH + sy); if (!(c >= sel.c0 && c <= sel.c1 && r >= sel.r0 && r <= sel.r1)) { sel = { c0: c, c1: c, r0: r, r1: r, ac: c, ar: r }; draw(); } }
      menu(e, [[t().cut, () => copySel(true), "Ctrl+X"], [t().copy, () => copySel(false), "Ctrl+C"], [t().paste, () => pasteInternal(), "Ctrl+V"], null, [t().clear, () => clearSel(), "Del"], null,
        [t().rowIns, () => shiftRows(sel.r0, 1)], [t().rowDel, () => shiftRows(sel.r0, -(sel.r1 - sel.r0 + 1))], null, [t().scatter, () => insertChart("scatter")]]); });
    body.addEventListener("wheel", (e) => { e.preventDefault(); sy = Math.max(0, sy + (e.shiftKey ? 0 : e.deltaY)); sx = Math.max(0, sx + (e.shiftKey ? e.deltaY : e.deltaX)); draw(); }, { passive: false });

    /* ── fill, copy and paste: formulas follow their cells, $ anchors stay ── */
    function fill(to) {
      const S = sel, ch = [];
      if (to.r > S.r1) {
        for (let c = S.c0; c <= S.c1; c++) {
          const src = []; for (let r = S.r0; r <= S.r1; r++) src.push(cell(c, r));
          const nums = src.every((q) => q && !q.f && typeof q.v === "number") && src.length > 1, step = nums ? (src[src.length - 1].v - src[0].v) / (src.length - 1) : 0;
          for (let r = S.r1 + 1; r <= to.r; r++) { const k = (r - S.r0) % src.length, q = src[k];
            ch.push({ k: X.ref(c, r), cell: nums ? { v: +(src[0].v + step * (r - S.r0)).toPrecision(12) } : q ? (q.f ? { f: X.shiftFormula(q.f, 0, r - S.r0 - k), v: null, ...(q.b ? { b: true } : {}) } : { ...q }) : null }); }
        }
        sel = { ...S, r1: to.r };
      } else if (to.c > S.c1) {
        for (let r = S.r0; r <= S.r1; r++) {
          const src = []; for (let c = S.c0; c <= S.c1; c++) src.push(cell(c, r));
          for (let c = S.c1 + 1; c <= to.c; c++) { const k = (c - S.c0) % src.length, q = src[k];
            ch.push({ k: X.ref(c, r), cell: q ? (q.f ? { f: X.shiftFormula(q.f, c - S.c0 - k, 0), v: null } : { ...q }) : null }); }
        }
        sel = { ...S, c1: to.c };
      }
      if (ch.length) setCells(ch); else draw();
    }
    function selTsv() { const out = []; for (let r = sel.r0; r <= Math.min(sel.r1, sel.r0 + 5000); r++) { const row = []; for (let c = sel.c0; c <= sel.c1; c++) { const q = cell(c, r); row.push(q ? X.show(q.v) : ""); } out.push(row.join("\t")); } return out.join("\r\n"); }
    function copySel(cut) {
      const cells = []; const r1 = Math.min(sel.r1, sel.r0 + 5000);
      for (let r = sel.r0; r <= r1; r++) { const row = []; for (let c = sel.c0; c <= sel.c1; c++) { const q = cell(c, r); row.push(q ? { ...q } : null); } cells.push(row); }
      clip = { si, c0: sel.c0, r0: sel.r0, c1: sel.c1, r1, cells, cut, text: selTsv() };
      try { navigator.clipboard && navigator.clipboard.writeText(clip.text).catch(() => {}); } catch (e) {}
      draw(); return clip.text;
    }
    function pasteInternal() { if (clip) pasteCells(clip); }
    function pasteCells(cp) {
      const ch = [];
      cp.cells.forEach((row, i) => row.forEach((q, j) => { const c = sel.ac + j, r = sel.ar + i; if (c >= MAXC || r >= MAXR) return;
        ch.push({ k: X.ref(c, r), cell: q ? (q.f && !cp.cut ? { ...q, f: X.shiftFormula(q.f, sel.ac - cp.c0, sel.ar - cp.r0), v: null } : { ...q }) : null }); }));
      if (cp.cut && cp.si === si) for (let r = cp.r0; r <= cp.r1; r++) for (let c = cp.c0; c <= cp.c1; c++) { const k = X.ref(c, r); if (!ch.some((x) => x.k === k)) ch.push({ k, cell: null }); }
      setCells(ch); sel = { c0: sel.ac, r0: sel.ar, c1: sel.ac + cp.cells[0].length - 1, r1: sel.ar + cp.cells.length - 1, ac: sel.ac, ar: sel.ar };
      if (cp.cut) clip = null; draw();
    }
    function pasteText(txt) {
      const rows = X.parseCsv(txt.replace(/\r?\n$/, ""), txt.includes("\t") ? "\t" : ",");
      pasteCells({ c0: sel.ac, r0: sel.ar, cells: rows.map((row) => row.map((s) => { const p = parseInput(s); return p.f || (p.v !== null && p.v !== undefined) ? p : null; })), cut: false, si });
    }
    ed.addEventListener("copy", (e) => { if (editing) return; e.preventDefault(); e.clipboardData.setData("text/plain", copySel(false)); });
    ed.addEventListener("cut", (e) => { if (editing) return; e.preventDefault(); e.clipboardData.setData("text/plain", copySel(true)); });
    ed.addEventListener("paste", (e) => { if (editing) return; e.preventDefault(); const txt = e.clipboardData.getData("text/plain");
      if (clip && (!txt || txt.replace(/\r/g, "") === clip.text.replace(/\r/g, ""))) pasteInternal(); else if (txt) pasteText(txt); });
    function clearSel() { if (chartSel >= 0) { delChart(); return; } const ch = []; for (let r = sel.r0; r <= Math.min(sel.r1, sel.r0 + 20000); r++) for (let c = sel.c0; c <= sel.c1; c++) { const k = X.ref(c, r), q = sh().cells[k]; if (q) ch.push({ k, cell: q.b ? { v: null, b: true } : null }); } if (ch.length) setCells(ch); }
    function shiftRows(at, n) {                  /* insert (n > 0) or delete (n < 0) rows at «at»; formulas on the sheet follow */
      const s = sh(), before = JSON.stringify(s.cells), moved = {};
      for (const [k, q] of Object.entries(s.cells)) { const p = X.parseRef(k); if (n < 0 && p[1] >= at && p[1] < at - n) continue; const r = p[1] >= at ? p[1] + n : p[1]; moved[X.ref(p[0], r)] = q; }
      for (const q of Object.values(moved)) if (q.f) q.f = q.f.replace(/(\$?)([A-Za-z]{1,3})(\$?)(\d+)(?![\w(])/g, (m, a, c, b, d) => { const r = +d - 1; return r >= at ? a + c + b + (r + n + 1 > 0 ? r + n + 1 : 1) : m; });
      s.cells = moved; undo.push({ si, all: true, before, after: JSON.stringify(moved) }); redo = []; dirty();
    }
    function boldSel() { const any = []; for (let r = sel.r0; r <= Math.min(sel.r1, sel.r0 + 2000); r++) for (let c = sel.c0; c <= sel.c1; c++) any.push([X.ref(c, r), cell(c, r)]);
      const on = !any.every(([, q]) => q && q.b); setCells(any.map(([k, q]) => ({ k, cell: on ? { ...(q || { v: null }), b: true } : q ? (() => { const n = { ...q }; delete n.b; return n; })() : null }))); }
    function autoSum() {
      const S = sel; let c = S.ac, r = S.ar, r0 = r - 1; const num = (rr) => { const q = cell(c, rr); return q && typeof q.v === "number"; };
      if (S.r1 > S.r0) { const ch = []; for (let cc = S.c0; cc <= S.c1; cc++) ch.push({ k: X.ref(cc, S.r1 + 1), cell: { f: `SUM(${X.ref(cc, S.r0)}:${X.ref(cc, S.r1)})`, v: null } }); setCells(ch); return; }
      while (r0 >= 0 && num(r0)) r0--; if (r0 === r - 1) { startEdit("=SUM()", "edit"); try { ed.setSelectionRange(5, 5); } catch (e) {} return; }
      startEdit(`=SUM(${X.ref(c, r0 + 1)}:${X.ref(c, r - 1)})`, "edit");
    }
    function fillDown() { if (sel.r1 <= sel.r0) return; const top = { ...sel, r1: sel.r0 }, to = { r: sel.r1, c: sel.c1 }, save = sel; sel = top; fill(to); sel = save; draw(); }

    /* ── keys ── */
    ed.addEventListener("keydown", (e) => {
      const k = e.key, ctrl = e.ctrlKey || e.metaKey;
      e.stopPropagation();
      if (ctrl && (k === "s" || k === "S")) { e.preventDefault(); stopEdit(true); save(); return; }
      if (ctrl && (k === "z" || k === "Z")) { e.preventDefault(); stopEdit(false); doUndo(false); return; }
      if (ctrl && (k === "y" || k === "Y")) { e.preventDefault(); stopEdit(false); doUndo(true); return; }
      if (editing) {
        if (k === "Enter") { e.preventDefault(); stopEdit(true); move(0, e.shiftKey ? -1 : 1, false); }
        else if (k === "Tab") { e.preventDefault(); stopEdit(true); move(e.shiftKey ? -1 : 1, 0, false); }
        else if (k === "Escape") { e.preventDefault(); stopEdit(false); fin.value = editText(cell(sel.ac, sel.ar)); }
        else if (editing.mode === "enter" && /^Arrow/.test(k) && !canPickRef()) { e.preventDefault(); stopEdit(true); move(k === "ArrowLeft" ? -1 : k === "ArrowRight" ? 1 : 0, k === "ArrowUp" ? -1 : k === "ArrowDown" ? 1 : 0, false); }
        else if (k === "F4") { e.preventDefault(); /* $A$1 → A$1 → $A1 → A1 at the caret */
          const v = ed.value, i = ed.selectionStart, m = /(\$?[A-Z]{1,3}\$?\d+)$/i.exec(v.slice(0, i)); if (!m) return;
          const a = m[1], bare = a.replace(/\$/g, ""), cm = /^([A-Z]+)(\d+)$/i.exec(bare), nx = a === bare ? "$" + cm[1] + "$" + cm[2] : a === "$" + cm[1] + "$" + cm[2] ? cm[1] + "$" + cm[2] : a === cm[1] + "$" + cm[2] ? "$" + cm[1] + cm[2] : bare;
          ed.value = v.slice(0, i - a.length) + nx + v.slice(i); const n = i - a.length + nx.length; ed.setSelectionRange(n, n); fin.value = ed.value; }
        return;
      }
      const arrows = { ArrowUp: [0, -1], ArrowDown: [0, 1], ArrowLeft: [-1, 0], ArrowRight: [1, 0] };
      if (arrows[k]) { e.preventDefault(); if (ctrl && !e.shiftKey) jump(...arrows[k]); else move(...arrows[k], e.shiftKey); return; }
      if (k === "Enter") { e.preventDefault(); move(0, e.shiftKey ? -1 : 1, false); return; }
      if (k === "Tab") { e.preventDefault(); move(e.shiftKey ? -1 : 1, 0, false); return; }
      if (k === "PageDown" || k === "PageUp") { e.preventDefault(); move(0, (k === "PageDown" ? 1 : -1) * Math.floor((H - HH) / RH), e.shiftKey); return; }
      if (k === "Home") { e.preventDefault(); move(-sel.ac, ctrl ? -sel.ar : 0, e.shiftKey); return; }
      if (k === "Delete" || k === "Backspace") { e.preventDefault(); if (k === "Backspace" && chartSel < 0) { clearSel(); startEdit("", "enter"); } else clearSel(); return; }
      if (k === "F2") { e.preventDefault(); startEdit(editText(cell(sel.ac, sel.ar)), "edit"); return; }
      if (k === "Escape") { if (clip) { clip = null; draw(); } chartSel = -1; draw(); return; }
      if (ctrl && (k === "a" || k === "A")) { e.preventDefault(); const b = X.bounds(sh()); sel = { c0: 0, r0: 0, c1: Math.max(0, b.c1), r1: Math.max(0, b.r1), ac: 0, ar: 0 }; draw(); return; }
      if (ctrl && (k === "d" || k === "D")) { e.preventDefault(); fillDown(); return; }
      if (ctrl && (k === "b" || k === "B")) { e.preventDefault(); boldSel(); return; }
      if (ctrl && (k === "v" || k === "V") && !navigator.clipboard) { pasteInternal(); return; }
    });

    /* ── ribbon, tabs, status ── */
    const icons = { save: "💾", undo: "↶", redo: "↷", paste: "📋", cut: "✂", copy: "⧉", bold: "B", sum: "Σ", fill: "⤓", clear: "⌫", scatter: "⁘", line: "📈", sheetAdd: "＋", open: "📂", newB: "🗋", saveAs: "🖫", dl: "⬇", dlCsv: "⬇" };
    function rbtn(k, f, on) { return `<button data-a="${k}"${on ? ' class="on"' : ""} title="${esc(t()[k])}"><i>${icons[k] || ""}</i>${esc(t()[k])}</button>`; }
    function paintBars() {
      const key = [lang(), ribTab, doc.name, doc.dirty, si, doc.wb.sheets.map((s) => s.name).join("|"), undo.length, redo.length].join("·");
      if (key !== shown) {
        shown = key;
        tabs.innerHTML = `<button class="file" data-t="file">${t().file}</button><button data-t="home" class="${ribTab === "home" ? "on" : ""}">${t().home}</button><button data-t="insert" class="${ribTab === "insert" ? "on" : ""}">${t().insert}</button><span class="doc">${esc(doc.name)}${doc.dirty ? " •" : ""}</span>`;
        rib.innerHTML = ribTab === "insert" ? [rbtn("scatter"), rbtn("line"), '<span class="sep"></span>', rbtn("sheetAdd")].join("")
          : [rbtn("save"), rbtn("undo"), rbtn("redo"), '<span class="sep"></span>', rbtn("paste"), rbtn("cut"), rbtn("copy"), '<span class="sep"></span>', rbtn("bold"), rbtn("sum"), rbtn("fill"), rbtn("clear")].join("");
        rib.querySelector('[data-a="undo"]') && (rib.querySelector('[data-a="undo"]').disabled = !undo.length);
        rib.querySelector('[data-a="redo"]') && (rib.querySelector('[data-a="redo"]').disabled = !redo.length);
        sheetsBar.innerHTML = doc.wb.sheets.map((s, i) => `<button data-s="${i}" class="${i === si ? "on" : ""}">${esc(s.name)}</button>`).join("") + `<button class="add" data-a="sheetAdd" title="${esc(t().sheetAdd)}">＋</button>`;
      }
      nameBox !== document.activeElement && (nameBox.value = sel.c0 === sel.c1 && sel.r0 === sel.r1 ? X.ref(sel.ac, sel.ar) : X.ref(sel.c0, sel.r0) + ":" + X.ref(sel.c1, sel.r1));
      if (!editing && fin !== document.activeElement) fin.value = editText(cell(sel.ac, sel.ar));
      let n = 0, s = 0, cnt = 0; for (let r = sel.r0; r <= Math.min(sel.r1, sel.r0 + 20000); r++) for (let c = sel.c0; c <= sel.c1; c++) { const q = cell(c, r); if (!q || q.v === null || q.v === "") continue; cnt++; if (typeof q.v === "number") { n++; s += q.v; } }
      const m = msg && performance.now() - msgT < 4000 ? msg : t().ready;
      stat.innerHTML = `<span class="msg">${esc(m)}</span>` + (n > 1 || cnt > 1 ? `<span>${t().avg}: ${n ? X.fmtNum(+(s / n).toPrecision(10)) : "—"}</span><span>${t().count}: ${cnt}</span><span>${t().sumS}: ${X.fmtNum(+s.toPrecision(12))}</span>` : "");
    }
    function say(s) { msg = s; msgT = performance.now(); paintBars(); setTimeout(() => paintBars(), 4100); }
    tabs.addEventListener("click", (e) => { const b = e.target.closest("[data-t]"); if (!b) return; if (b.dataset.t === "file") fileMenu(b); else { ribTab = b.dataset.t; shown = ""; paintBars(); } ed.focus({ preventScroll: true }); });
    rib.addEventListener("mousedown", (e) => e.preventDefault());
    rib.addEventListener("click", (e) => { const b = e.target.closest("[data-a]"); if (b) act(b.dataset.a); });
    sheetsBar.addEventListener("click", (e) => { const b = e.target.closest("button"); if (!b) return; if (b.dataset.a) { act(b.dataset.a); return; } stopEdit(true); si = +b.dataset.s; sel = { c0: 0, r0: 0, c1: 0, r1: 0, ac: 0, ar: 0 }; sx = sy = 0; chartSel = -1; shown = ""; draw(); ed.focus({ preventScroll: true }); });
    sheetsBar.addEventListener("dblclick", (e) => { const b = e.target.closest("[data-s]"); if (!b) return; const i = +b.dataset.s, cur = doc.wb.sheets[i].name;
      prompt1(t().name, cur, (v) => { v = v.replace(/[\\/?*[\]:]/g, "").slice(0, 31).trim(); if (!v || doc.wb.sheets.some((s, j) => j !== i && s.name.toLowerCase() === v.toLowerCase())) return; doc.wb.sheets[i].name = v; doc.dirty = true; shown = ""; draw(); }); });
    function act(a) {
      stopEdit(true);
      if (a === "save") save(); else if (a === "undo") doUndo(false); else if (a === "redo") doUndo(true);
      else if (a === "copy") copySel(false); else if (a === "cut") copySel(true); else if (a === "paste") {
        if (navigator.clipboard && navigator.clipboard.readText) navigator.clipboard.readText().then((txt) => { if (clip && (!txt || txt.replace(/\r/g, "") === clip.text.replace(/\r/g, ""))) pasteInternal(); else if (txt) pasteText(txt); else pasteInternal(); }).catch(() => pasteInternal());
        else pasteInternal(); }
      else if (a === "bold") boldSel(); else if (a === "sum") autoSum(); else if (a === "fill") fillDown(); else if (a === "clear") clearSel();
      else if (a === "scatter" || a === "line") insertChart(a);
      else if (a === "sheetAdd") { let k = doc.wb.sheets.length + 1; while (doc.wb.sheets.some((s) => s.name === "Sheet" + k)) k++; doc.wb.sheets.push({ name: "Sheet" + k, cells: {}, cols: {}, charts: [] }); si = doc.wb.sheets.length - 1; sel = { c0: 0, r0: 0, c1: 0, r1: 0, ac: 0, ar: 0 }; doc.dirty = true; shown = ""; draw(); }
      ed.focus({ preventScroll: true });
    }
    function menu(e, items) {
      const old = el.querySelector(".vx-menu"); if (old) old.remove();
      const m = document.createElement("div"); m.className = "vx-menu";
      m.innerHTML = items.map((x, i) => x ? `<div data-i="${i}">${esc(x[0])}${x[2] ? `<i>${esc(x[2])}</i>` : ""}</div>` : "<hr>").join("");
      const r = el.getBoundingClientRect(); m.style.left = Math.min((e.clientX - r.left) / scale, el.offsetWidth - 200) + "px"; m.style.top = Math.min((e.clientY - r.top) / scale, el.offsetHeight - items.length * 30) + "px";
      el.appendChild(m);
      const off = (ev) => { if (!m.contains(ev.target)) { m.remove(); window.removeEventListener("pointerdown", off, true); } };
      window.addEventListener("pointerdown", off, true);
      m.addEventListener("click", (ev) => { const d = ev.target.closest("[data-i]"); if (!d) return; m.remove(); window.removeEventListener("pointerdown", off, true); items[+d.dataset.i][1](); ed.focus({ preventScroll: true }); });
    }
    function fileMenu(b) {
      const r = b.getBoundingClientRect();
      menu({ clientX: r.left, clientY: r.bottom }, [[t().newB, () => guard(() => load(blank(nextName())))], [t().open, () => openDialog(), "Ctrl+O"], null, [t().save, () => save(), "Ctrl+S"], [t().saveAs, () => saveAsDialog()], null,
        [t().dl, () => download("xlsx")], [t().dlCsv, () => download("csv")], null, [t().close, () => guard(() => opt.onclose && opt.onclose())]]);
    }
    let bookN = 1; const nextName = () => t().book + (++bookN) + ".xlsx";

    /* ── dialogs ── */
    function dialog(html, onOk, init) {
      const d = document.createElement("div"); d.className = "vx-dlg"; d.innerHTML = `<div>${html}<div class="btns"><button class="pri" data-ok>${t().ok}</button><button data-no>${t().cancel}</button></div></div>`;
      el.appendChild(d); const close = () => { d.remove(); ed.focus({ preventScroll: true }); };
      d.addEventListener("keydown", (e) => { e.stopPropagation(); if (e.key === "Escape") close(); if (e.key === "Enter" && e.target.tagName === "INPUT") { e.preventDefault(); d.querySelector("[data-ok]").click(); } });
      d.querySelector("[data-no]").onclick = close;
      d.querySelector("[data-ok]").onclick = () => { if (onOk(d) !== false) close(); };
      init && init(d); const f = d.querySelector("input[type=text],select,li"); f && f.focus && f.focus();
      return d;
    }
    function prompt1(label, value, ok) { dialog(`<label>${esc(label)}</label><input type="text" value="${esc(value)}">`, (d) => ok(d.querySelector("input").value)); }
    function guard(go) {
      if (!doc.dirty || (!doc.id && isEmpty())) { go(); return; }
      const d = document.createElement("div"); d.className = "vx-dlg";
      d.innerHTML = `<div><h3>Microsoft Excel</h3><p>${esc(t().unsaved(doc.name))}</p><div class="btns"><button class="pri" data-y>${t().save}</button><button data-n>${t().dontSave}</button><button data-c>${t().cancel}</button></div></div>`;
      el.appendChild(d); d.querySelector("[data-c]").onclick = () => d.remove(); d.querySelector("[data-n]").onclick = () => { d.remove(); go(); };
      d.querySelector("[data-y]").onclick = () => { d.remove(); save(go); };
    }
    const isEmpty = () => doc.wb.sheets.every((s) => !Object.keys(s.cells).length && !(s.charts || []).length);
    function openDialog() {
      const list = (host.list && host.list()) || [];
      let pick = list.length ? list[0].id : null;
      dialog(`<h3>${t().openT}</h3>${list.length ? `<ul>${list.map((f, i) => `<li data-id="${esc(f.id)}" class="${i ? "" : "on"}" title="${esc(f.path)}">${esc(f.path)}</li>`).join("")}</ul>` : `<p>${t().noFiles}</p>`}`,
        () => { if (pick == null) return; guard(() => { const r = host.load(pick); if (r) load(r); }); },
        (d) => d.querySelectorAll("li").forEach((li) => { li.onclick = () => { d.querySelectorAll("li").forEach((x) => x.classList.remove("on")); li.classList.add("on"); pick = li.dataset.id; };
          li.ondblclick = () => { pick = li.dataset.id; d.querySelector("[data-ok]").click(); }; }));
    }
    function save(then) {
      recalc();
      if (doc.id != null && host.save && host.save(doc) !== false) { doc.dirty = false; shown = ""; say(t().saved); draw(); then && then(); return; }
      saveAsDialog(then);
    }
    function saveAsDialog(then) {
      const folders = (host.folders && host.folders()) || [], base = doc.name.replace(/\.(xlsx|csv)$/i, "");
      dialog(`<h3>${t().saveAs}</h3><label>${t().folder}</label><select data-f>${folders.map((f) => `<option value="${esc(f.id)}"${f.id === doc.folder ? " selected" : ""}>${esc(f.path)}</option>`).join("")}</select>
        <label>${t().fname}</label><input type="text" data-n value="${esc(base)}"><label>${t().ftype}</label><select data-t><option value="xlsx">${t().xlsx}</option><option value="csv"${doc.csv ? " selected" : ""}>${t().csv}</option></select>`,
        (d) => { const name = d.querySelector("[data-n]").value.trim().replace(/[\\/:*?"<>|]/g, ""), type = d.querySelector("[data-t]").value; if (!name) return false;
          if (type === "csv" && doc.wb.sheets.length > 1) say(t().csvOne);
          const r = host.saveAs && host.saveAs(doc, d.querySelector("[data-f]").value, name + "." + type, type, si);
          if (!r) return false;
          doc.id = r.id; doc.name = r.name; doc.folder = r.folder; doc.csv = type === "csv"; doc.dirty = false; shown = ""; say(t().savedTo(r.path || r.name)); draw(); then && then(); });
    }
    function download(type) {
      recalc(); const base = doc.name.replace(/\.(xlsx|csv)$/i, "");
      const blob = type === "csv" ? new Blob(["﻿" + X.toCsv(sh())], { type: "text/csv" }) : new Blob([X.write(X.clone(doc.wb))], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
      const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = base + (type === "csv" && doc.wb.sheets.length > 1 ? "-" + sh().name : "") + "." + type; document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 4000);
    }
    function chartDialog(i) {
      const ch = sh().charts[i]; if (!ch) return;
      const trendOpt = (v) => ["", "linear", "exp", "log", "power"].map((k) => `<option value="${k}"${(v || "") === k ? " selected" : ""}>${esc(k ? t()[{ linear: "lin", exp: "exp", log: "log", power: "pow" }[k]] : t().none)}</option>`).join("");
      const serHtml = (s, k) => `<div class="ser" data-k="${k}"><div class="row"><b>${t().series} ${k + 1}</b><button data-del="${k}" style="flex:none">${t().delSer}</button></div>
        <label>${t().name}</label><input type="text" data-sn value="${esc(s.name || "")}">
        <div class="row"><div><label>${t().xs}</label><input type="text" data-sx value="${esc(s.x || "")}"></div><div><label>${t().ys}</label><input type="text" data-sy value="${esc(s.y || "")}"></div></div>
        <span class="chk"><input type="checkbox" data-sm${s.marker !== false ? " checked" : ""}>${t().markers}</span><span class="chk"><input type="checkbox" data-sl${s.line ? " checked" : ""}>${t().lines}</span>
        <div class="row"><div><label>${t().trend}</label><select data-st>${trendOpt(s.trend)}</select></div><div><span class="chk"><input type="checkbox" data-se${s.eq ? " checked" : ""}>${t().eq}</span><span class="chk"><input type="checkbox" data-sr${s.r2 ? " checked" : ""}>${t().r2}</span></div></div></div>`;
      const work = JSON.parse(JSON.stringify(ch));
      const html = () => `<h3>${t().chartEdit}</h3><label>${t().title}</label><input type="text" data-ti value="${esc(work.title || "")}">
        <div class="row"><div><label>${t().xT}</label><input type="text" data-xt value="${esc(work.x.title || "")}"></div><div><label>${t().yT}</label><input type="text" data-yt value="${esc(work.y.title || "")}"></div></div>
        <span class="chk"><input type="checkbox" data-lx${work.x.log ? " checked" : ""}>${t().logX}</span><span class="chk"><input type="checkbox" data-ly${work.y.log ? " checked" : ""}>${t().logY}</span>
        <div data-list>${work.series.map(serHtml).join("")}</div><button data-add style="margin-top:8px">${t().addSer}</button>`;
      const pull = (d) => {
        work.title = d.querySelector("[data-ti]").value; work.x = { ...work.x, title: d.querySelector("[data-xt]").value, log: d.querySelector("[data-lx]").checked }; work.y = { ...work.y, title: d.querySelector("[data-yt]").value, log: d.querySelector("[data-ly]").checked };
        const norm = (v) => { v = v.trim().replace(/^=/, ""); if (!v) return ""; const r = X.parseRange(v); if (!r) return v; return X.absRange(r.sheet || sh().name, r.c0, r.r0, r.c1, r.r1); };
        work.series = [...d.querySelectorAll(".ser")].map((x) => ({ name: x.querySelector("[data-sn]").value, x: norm(x.querySelector("[data-sx]").value), y: norm(x.querySelector("[data-sy]").value),
          marker: x.querySelector("[data-sm]").checked, line: x.querySelector("[data-sl]").checked, trend: x.querySelector("[data-st]").value || null, eq: x.querySelector("[data-se]").checked, r2: x.querySelector("[data-sr]").checked }));
      };
      const wire = (d) => {
        d.querySelector("[data-add]").onclick = () => { pull(d); work.series.push({ name: "", x: work.series[0] ? work.series[0].x : "", y: "", marker: true, line: false, trend: null }); d.firstChild.innerHTML = html() + d.firstChild.querySelector(".btns").outerHTML; rewire(d); };
        d.querySelectorAll("[data-del]").forEach((b) => b.onclick = () => { pull(d); work.series.splice(+b.dataset.del, 1); d.firstChild.innerHTML = html() + d.firstChild.querySelector(".btns").outerHTML; rewire(d); });
      };
      let dlg;
      const rewire = (d) => { wire(d); d.querySelector("[data-no]").onclick = () => { d.remove(); ed.focus({ preventScroll: true }); }; d.querySelector("[data-ok]").onclick = () => { pull(d); chartStep((s) => { s.charts[i] = { ...work, at: ch.at }; }); d.remove(); ed.focus({ preventScroll: true }); }; };
      dlg = dialog(html(), (d) => { pull(d); chartStep((s) => { s.charts[i] = { ...work, at: ch.at }; }); }, wire);
      void dlg;
    }

    /* ── opening a workbook ── */
    function load(d) {
      doc = { name: d.name, id: d.id ?? null, folder: d.folder ?? null, wb: X.clone(d.wb), dirty: false, csv: /\.csv$/i.test(d.name) };
      if (!doc.wb.sheets.length) doc.wb.sheets.push({ name: "Sheet1", cells: {}, cols: {}, charts: [] });
      si = 0; sel = { c0: 0, r0: 0, c1: 0, r1: 0, ac: 0, ar: 0 }; sx = sy = 0; undo = []; redo = []; chartSel = -1; editing = null; ed.classList.add("off"); ed.value = "";
      recalc(); shown = ""; draw(); opt.onchange && opt.onchange();
    }

    return {
      el,
      place(x, y, w, h, vis, sc) {
        const s = sc > 0 && sc < 4 ? sc : 1;
        if (!vis) { if (el.style.display !== "none") { stopEdit(true); el.style.display = "none"; } return; }
        const was = el.style.display === "none";
        Object.assign(el.style, { display: "flex", left: x + "px", top: y + "px", width: w / s + "px", height: h / s + "px", transform: `scale(${s})` });
        scale = s;
        if (was || el._w !== w || el._h !== h) { el._w = w; el._h = h; draw(); if (was) ed.focus({ preventScroll: true }); }
      },
      open(d) { load(d); },
      newBook() { load(blank(nextName())); },
      title() { return doc.name.replace(/\.xlsx$/i, "") + (doc.dirty ? "*" : ""); },
      doc() { return doc; },
      focus() { ed.focus({ preventScroll: true }); },
      redraw() { shown = ""; draw(); },
      guard,
    };
  }

  /* ── drawing a chart on a 2D context (the window and the canvas desktop both use it) ── */
  const COL = ["#4472c4", "#ed7d31", "#a5a5a5", "#ffc000", "#5b9bd5", "#70ad47", "#264478", "#9e480e"];
  function nice(lo, hi, n) {
    if (!(hi > lo)) { hi = lo + 1; lo -= 1; }
    const span = hi - lo, step0 = Math.pow(10, Math.floor(Math.log10(span / n))), err = span / n / step0, step = step0 * (err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1);
    const a = Math.floor(lo / step) * step, b = Math.ceil(hi / step) * step, ticks = [];
    for (let v = a; v <= b + step * 1e-9; v += step) ticks.push(+v.toPrecision(12));
    return { lo: a, hi: b, ticks };
  }
  function logAxis(lo, hi) {
    const a = Math.floor(Math.log10(lo)), b = Math.ceil(Math.log10(hi)), ticks = [];
    for (let e = a; e <= b; e++) ticks.push(Math.pow(10, e));
    return { lo: Math.pow(10, a), hi: Math.pow(10, b === a ? a + 1 : b), ticks, log: true };
  }
  const tickTxt = (v) => { const a = Math.abs(v); if (a !== 0 && (a >= 1e5 || a < 1e-3)) return v.toExponential(0).replace("e+", "E").replace("e-", "E-"); return String(+v.toPrecision(6)); };
  VExcel.drawChart = function (g, W, H, ch, vals) {
    const F = '"Segoe UI","Malgun Gothic",sans-serif';
    g.fillStyle = "#fff"; g.fillRect(0, 0, W, H);
    const series = (ch.series || []).map((s, i) => {
      const ys = vals(s.y), xs = s.x ? vals(s.x) : ys.map((_, k) => k + 1), pts = [];
      for (let k = 0; k < ys.length; k++) if (ys[k] != null && xs[k] != null && (!ch.x.log || xs[k] > 0) && (!ch.y.log || ys[k] > 0)) pts.push([xs[k], ys[k]]);
      return { s, pts, col: COL[i % COL.length] };
    });
    const top = ch.title ? 30 : 12, legend = series.length > 1 ? Math.min(130, W * 0.28) : 0, left = 54 + (ch.y && ch.y.title ? 16 : 0), bottom = 30 + (ch.x && ch.x.title ? 18 : 0), right = 14 + legend;
    if (ch.title) { g.fillStyle = "#404040"; g.font = "600 13px " + F; g.textAlign = "center"; g.textBaseline = "middle"; g.fillText(ch.title, W / 2, 16); }
    const all = series.flatMap((q) => q.pts);
    const pw = W - left - right, ph = H - top - bottom;
    if (!all.length || pw < 30 || ph < 30) { g.fillStyle = "#999"; g.font = "12px " + F; g.textAlign = "center"; g.fillText("—", W / 2, H / 2); return; }
    const xr = [Math.min(...all.map((p) => p[0])), Math.max(...all.map((p) => p[0]))], yr = [Math.min(...all.map((p) => p[1])), Math.max(...all.map((p) => p[1]))];
    const ax = ch.x && ch.x.log ? logAxis(xr[0], xr[1]) : nice(xr[0], xr[1], Math.max(3, Math.floor(pw / 70)));
    const ay = ch.y && ch.y.log ? logAxis(yr[0], yr[1]) : nice(yr[0], yr[1], Math.max(3, Math.floor(ph / 40)));
    const X0 = (v) => left + (ax.log ? (Math.log10(v) - Math.log10(ax.lo)) / (Math.log10(ax.hi) - Math.log10(ax.lo)) : (v - ax.lo) / (ax.hi - ax.lo)) * pw;
    const Y0 = (v) => top + ph - (ay.log ? (Math.log10(v) - Math.log10(ay.lo)) / (Math.log10(ay.hi) - Math.log10(ay.lo)) : (v - ay.lo) / (ay.hi - ay.lo)) * ph;
    g.strokeStyle = "#d9d9d9"; g.lineWidth = 1; g.font = "11px " + F; g.fillStyle = "#595959";
    g.textAlign = "right"; g.textBaseline = "middle";
    for (const v of ay.ticks) { const y = Math.round(Y0(v)) + 0.5; g.beginPath(); g.moveTo(left, y); g.lineTo(left + pw, y); g.stroke(); g.fillText(tickTxt(v), left - 5, y); }
    g.textAlign = "center"; g.textBaseline = "top";
    for (const v of ax.ticks) { const x = Math.round(X0(v)) + 0.5; g.beginPath(); g.moveTo(x, top + ph); g.lineTo(x, top + ph + 4); g.stroke(); g.fillText(tickTxt(v), x, top + ph + 6); }
    g.strokeStyle = "#bfbfbf"; g.strokeRect(left + 0.5, top + 0.5, pw, ph);
    if (ch.x && ch.x.title) { g.fillStyle = "#404040"; g.font = "12px " + F; g.textAlign = "center"; g.textBaseline = "bottom"; g.fillText(ch.x.title, left + pw / 2, H - 4); }
    if (ch.y && ch.y.title) { g.save(); g.translate(14, top + ph / 2); g.rotate(-Math.PI / 2); g.fillStyle = "#404040"; g.font = "12px " + F; g.textAlign = "center"; g.textBaseline = "middle"; g.fillText(ch.y.title, 0, 0); g.restore(); }
    g.save(); g.beginPath(); g.rect(left, top, pw, ph); g.clip();
    let labels = [];
    for (const q of series) {
      const P = q.pts.slice(); if (ch.type === "line" || q.s.line) P.sort((a, b) => a[0] - b[0]);
      if (q.s.line && P.length > 1) { g.strokeStyle = q.col; g.lineWidth = 2; g.beginPath(); P.forEach(([x, y], k) => k ? g.lineTo(X0(x), Y0(y)) : g.moveTo(X0(x), Y0(y))); g.stroke(); }
      if (q.s.marker !== false) { g.fillStyle = q.col; for (const [x, y] of P) { g.beginPath(); g.arc(X0(x), Y0(y), 3.2, 0, 7); g.fill(); } }
      if (q.s.trend && P.length > 1) {
        const tr = q.s.trend, L = tr === "exp" ? P.filter((p) => p[1] > 0).map(([x, y]) => [x, Math.log(y)]) : tr === "log" ? P.filter((p) => p[0] > 0).map(([x, y]) => [Math.log(x), y]) : tr === "power" ? P.filter((p) => p[0] > 0 && p[1] > 0).map(([x, y]) => [Math.log(x), Math.log(y)]) : P;
        let f = null; try { f = window.HLXlsx.fit(L); } catch (e) {}
        if (f) {
          const fy = (x) => tr === "exp" ? Math.exp(f.b) * Math.exp(f.k * x) : tr === "log" ? f.k * Math.log(x) + f.b : tr === "power" ? Math.exp(f.b) * Math.pow(x, f.k) : f.k * x + f.b;
          g.strokeStyle = q.col; g.lineWidth = 1.5; g.setLineDash([2, 3]); g.beginPath();
          const xa = Math.max(xr[0], ax.lo), xb = Math.min(xr[1], ax.hi);
          for (let k = 0; k <= 80; k++) { const x = ax.log ? Math.pow(10, Math.log10(xa) + (Math.log10(xb) - Math.log10(xa)) * k / 80) : xa + (xb - xa) * k / 80, y = fy(x); if (!Number.isFinite(y) || (ay.log && y <= 0)) continue; k ? g.lineTo(X0(x), Y0(y)) : g.moveTo(X0(x), Y0(y)); }
          g.stroke(); g.setLineDash([]);
          const n = (v) => window.HLXlsx.fmtNum(+v.toPrecision(5));
          const eq = tr === "exp" ? `y = ${n(Math.exp(f.b))}e^${n(f.k)}x` : tr === "log" ? `y = ${n(f.k)}ln(x) ${f.b < 0 ? "−" : "+"} ${n(Math.abs(f.b))}` : tr === "power" ? `y = ${n(Math.exp(f.b))}x^${n(f.k)}` : `y = ${n(f.k)}x ${f.b < 0 ? "−" : "+"} ${n(Math.abs(f.b))}`;
          const parts = []; if (q.s.eq) parts.push(eq); if (q.s.r2) parts.push("R² = " + n(f.r2));
          if (parts.length) labels.push([parts, q.col]);
        }
      }
    }
    g.restore();
    g.font = "11.5px " + F; g.textAlign = "right"; g.textBaseline = "top"; let ly = top + 6;
    for (const [parts, col] of labels) for (const p of parts) { const w = g.measureText(p).width; g.fillStyle = "rgba(255,255,255,0.6)"; g.fillRect(left + pw - 8 - w - 3, ly - 1, w + 6, 15); g.fillStyle = col; g.fillText(p, left + pw - 8, ly); ly += 15; }
    if (legend) { g.textAlign = "left"; g.textBaseline = "middle"; g.font = "11px " + F; series.forEach((q, i) => { const y = top + 10 + i * 18; g.fillStyle = q.col; g.beginPath(); g.arc(W - legend + 6, y, 4, 0, 7); g.fill(); g.fillStyle = "#404040"; g.fillText((q.s.name || "Series " + (i + 1)).slice(0, 22), W - legend + 14, y); }); }
  };
  /* the window's face drawn on the desktop canvas while the live grid is hidden (moving, behind another window) */
  VExcel.sketch = function (ctx, x, y, w, h, name) {
    ctx.save(); ctx.beginPath(); ctx.rect(x, y, w, h); ctx.clip();
    ctx.fillStyle = "#107c41"; ctx.fillRect(x, y, w, 30); ctx.fillStyle = "#f3f3f3"; ctx.fillRect(x, y + 30, w, 58); ctx.fillStyle = "#fff"; ctx.fillRect(x, y + 88, w, h - 88);
    ctx.fillStyle = "#fff"; ctx.font = '12px "Segoe UI",sans-serif'; ctx.textBaseline = "middle"; ctx.fillText(name || "", x + 12, y + 15);
    ctx.strokeStyle = "#e1e1e1"; ctx.lineWidth = 1; ctx.beginPath();
    for (let cx = x + 46; cx < x + w; cx += 69) { ctx.moveTo(cx + 0.5, y + 117); ctx.lineTo(cx + 0.5, y + h - 48); }
    for (let cy = y + 117; cy < y + h - 48; cy += 21) { ctx.moveTo(x, cy + 0.5); ctx.lineTo(x + w, cy + 0.5); }
    ctx.stroke(); ctx.fillStyle = "#f3f3f3"; ctx.fillRect(x, y + 117, 46, h - 165); ctx.fillRect(x, y + 96, w, 21);
    ctx.fillStyle = "#107c41"; ctx.fillRect(x, y + h - 22, w, 22);
    ctx.restore();
  };
  window.VExcel = VExcel;
})();
