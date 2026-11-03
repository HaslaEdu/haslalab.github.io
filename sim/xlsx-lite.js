/* ==========================================================================
   HaslaLab — xlsx-lite: Excel workbooks without a library
   --------------------------------------------------------------------------
   Reads and writes .xlsx (Office Open XML) and .csv for the spreadsheet on
   the simulated exam laptops (vexcel.js), for the template tables that
   ISPhO problems hand out (tools/ispho_xlsx.cjs) and for the answer files a
   candidate attaches for grading (exam.html), which are sent as text.

   A workbook here is
     { sheets: [ { name, cells: { "A1": { v, f, b } }, cols: { 0: width },
                   charts: [ chart ] } ] }
   v is the value (number, string, boolean or null; an error is a string
   "#DIV/0!" with err: true), f the formula without its "=", b a bold cell.
   A chart is
     { type: "scatter" | "line", title, x: { title, log }, y: { title, log },
       series: [ { name, x: "Sheet1!$A$2:$A$9", y: "...", line, marker,
                   trend: "linear" | "exp" | "log" | "power" | null,
                   eq, r2 } ],
       at: { c0, r0, c1, r1 } }               (cells the chart covers)

   read(bytes) is async (the zip's entries are inflated with the browser's
   DecompressionStream); write(wb) is synchronous and stores its entries
   uncompressed, which every spreadsheet program opens.  calc(wb) works out
   every formula (the functions an experiment needs: arithmetic, SUM, AVERAGE,
   SLOPE, INTERCEPT, RSQ, LN, MAX, MATCH, INDEX …).  toText(wb, name) is what
   the grader reads: every table, every formula and every chart.
   ========================================================================== */
(function (root) {
  "use strict";
  const TE = typeof TextEncoder !== "undefined" ? new TextEncoder() : null;
  const TD = typeof TextDecoder !== "undefined" ? new TextDecoder() : null;
  const utf8 = (s) => TE.encode(s), unutf8 = (b) => TD.decode(b);

  /* ── cell references ── */
  function colName(c) { let s = ""; c++; while (c > 0) { const m = (c - 1) % 26; s = String.fromCharCode(65 + m) + s; c = (c - 1 - m) / 26; } return s; }
  function colIndex(s) { let n = 0; for (const ch of s.toUpperCase()) n = n * 26 + ch.charCodeAt(0) - 64; return n - 1; }
  function parseRef(r) { const m = /^\$?([A-Za-z]{1,3})\$?(\d{1,7})$/.exec(String(r).trim()); return m ? [colIndex(m[1]), +m[2] - 1] : null; }
  const ref = (c, r) => colName(c) + (r + 1);
  function parseRange(s) {               /* "Sheet 1!$A$2:$B$9" → { sheet, c0, r0, c1, r1 } */
    let sheet = null, x = String(s).trim();
    const bang = x.lastIndexOf("!");
    if (bang >= 0) { sheet = x.slice(0, bang).replace(/^'(.*)'$/, "$1").replace(/''/g, "'"); x = x.slice(bang + 1); }
    const [a, b] = x.split(":"), p = parseRef(a), q = b ? parseRef(b) : p;
    if (!p || !q) return null;
    return { sheet, c0: Math.min(p[0], q[0]), r0: Math.min(p[1], q[1]), c1: Math.max(p[0], q[0]), r1: Math.max(p[1], q[1]) };
  }
  const quoteSheet = (n) => /^[A-Za-z_][A-Za-z0-9_.]*$/.test(n) ? n : "'" + String(n).replace(/'/g, "''") + "'";
  const absRange = (sheet, c0, r0, c1, r1) => quoteSheet(sheet) + "!$" + colName(c0) + "$" + (r0 + 1) + ":$" + colName(c1) + "$" + (r1 + 1);

  /* ── zip ── */
  const CRC = (() => { const t = new Uint32Array(256); for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
  function crc32(b) { let c = 0xffffffff; for (let i = 0; i < b.length; i++) c = CRC[(c ^ b[i]) & 0xff] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; }
  /* entries [{ name, data }] → a zip, stored (no compression); dates are a fixed 2026-01-01 so that a file is the same every time */
  function zip(entries) {
    const parts = [], central = []; let off = 0;
    const DOSTIME = 0, DOSDATE = ((2026 - 1980) << 9) | (1 << 5) | 1;
    for (const e of entries) {
      const name = utf8(e.name), data = typeof e.data === "string" ? utf8(e.data) : e.data, crc = crc32(data);
      const h = new DataView(new ArrayBuffer(30));
      h.setUint32(0, 0x04034b50, true); h.setUint16(4, 20, true); h.setUint16(6, 0x0800, true); h.setUint16(8, 0, true);
      h.setUint16(10, DOSTIME, true); h.setUint16(12, DOSDATE, true); h.setUint32(14, crc, true);
      h.setUint32(18, data.length, true); h.setUint32(22, data.length, true); h.setUint16(26, name.length, true); h.setUint16(28, 0, true);
      parts.push(new Uint8Array(h.buffer), name, data);
      const c = new DataView(new ArrayBuffer(46));
      c.setUint32(0, 0x02014b50, true); c.setUint16(4, 20, true); c.setUint16(6, 20, true); c.setUint16(8, 0x0800, true); c.setUint16(10, 0, true);
      c.setUint16(12, DOSTIME, true); c.setUint16(14, DOSDATE, true); c.setUint32(16, crc, true); c.setUint32(20, data.length, true); c.setUint32(24, data.length, true);
      c.setUint16(28, name.length, true); c.setUint32(38, e.name.endsWith("/") ? 0x10 : 0, true); c.setUint32(42, off, true);
      central.push(new Uint8Array(c.buffer), name);
      off += 30 + name.length + data.length;
    }
    const cdSize = central.reduce((n, p) => n + p.length, 0), end = new DataView(new ArrayBuffer(22));
    end.setUint32(0, 0x06054b50, true); end.setUint16(8, entries.length, true); end.setUint16(10, entries.length, true);
    end.setUint32(12, cdSize, true); end.setUint32(16, off, true);
    const all = [...parts, ...central, new Uint8Array(end.buffer)], out = new Uint8Array(all.reduce((n, p) => n + p.length, 0));
    let o = 0; for (const p of all) { out.set(p, o); o += p.length; }
    return out;
  }
  async function inflate(data) {
    if (typeof DecompressionStream !== "undefined") {
      const s = new Blob([data]).stream().pipeThrough(new DecompressionStream("deflate-raw"));
      return new Uint8Array(await new Response(s).arrayBuffer());
    }
    return new Uint8Array(require("zlib").inflateRawSync(data));
  }
  async function unzip(bytes) {
    const b = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes), dv = new DataView(b.buffer, b.byteOffset, b.byteLength), out = new Map();
    let e = -1; for (let i = b.length - 22; i >= Math.max(0, b.length - 65557); i--) if (dv.getUint32(i, true) === 0x06054b50) { e = i; break; }
    if (e < 0) throw new Error("not_zip");
    let p = dv.getUint32(e + 16, true); const n = dv.getUint16(e + 10, true);
    for (let k = 0; k < n; k++) {
      if (dv.getUint32(p, true) !== 0x02014b50) throw new Error("bad_zip");
      const method = dv.getUint16(p + 10, true), csize = dv.getUint32(p + 20, true), nl = dv.getUint16(p + 28, true),
        xl = dv.getUint16(p + 30, true), cl = dv.getUint16(p + 32, true), lo = dv.getUint32(p + 42, true);
      const name = unutf8(b.subarray(p + 46, p + 46 + nl));
      const start = lo + 30 + dv.getUint16(lo + 26, true) + dv.getUint16(lo + 28, true), raw = b.subarray(start, start + csize);
      if (!name.endsWith("/")) out.set(name, method === 0 ? raw.slice() : method === 8 ? await inflate(raw) : null);
      p += 46 + nl + xl + cl;
    }
    return out;
  }

  /* ── a small XML reader: elements by local name, attributes, text ── */
  const ENT = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'" };
  const unxml = (s) => s.replace(/&(#x[0-9a-f]+|#\d+|\w+);/gi, (m, e) => e[0] === "#" ? String.fromCodePoint(e[1] === "x" || e[1] === "X" ? parseInt(e.slice(2), 16) : +e.slice(1)) : ENT[e] ?? m);
  const xml = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])).replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, "");
  function parseXml(s) {
    const rootN = { n: "#root", a: {}, k: [], t: "" }, stack = [rootN], re = /<!\[CDATA\[([\s\S]*?)\]\]>|<!--[\s\S]*?-->|<\?[\s\S]*?\?>|<(\/?)([\w:.-]+)((?:\s+[\w:.-]+\s*=\s*(?:"[^"]*"|'[^']*'))*)\s*(\/?)>|([^<]+)/g;
    let m;
    while ((m = re.exec(s))) {
      const top = stack[stack.length - 1];
      if (m[1] !== undefined) top.t += m[1];
      else if (m[3]) {
        if (m[2]) { stack.length > 1 && stack.pop(); continue; }
        const a = {}, ar = /([\w:.-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')/g; let q;
        while ((q = ar.exec(m[4]))) a[q[1].replace(/^.*:/, "")] = unxml(q[2] ?? q[3]);
        const el = { n: m[3].replace(/^.*:/, ""), a, k: [], t: "" };
        top.k.push(el); if (!m[5]) stack.push(el);
      } else if (m[6] !== undefined) top.t += unxml(m[6]);
    }
    return rootN;
  }
  const kid = (el, n) => el && el.k.find((x) => x.n === n);
  const kids = (el, n) => el ? el.k.filter((x) => x.n === n) : [];
  function find(el, n) { if (!el) return null; for (const x of el.k) { if (x.n === n) return x; const y = find(x, n); if (y) return y; } return null; }
  function findAll(el, n, out = []) { if (!el) return out; for (const x of el.k) { if (x.n === n) out.push(x); findAll(x, n, out); } return out; }
  const textOf = (el) => el ? el.t + el.k.map(textOf).join("") : "";
  const path = (base, target) => { if (target.startsWith("/")) return target.slice(1); const p = base.split("/"); p.pop(); for (const s of target.split("/")) { if (s === "..") p.pop(); else if (s !== ".") p.push(s); } return p.join("/"); };
  function rels(files, part) {
    const i = part.lastIndexOf("/"), rp = part.slice(0, i + 1) + "_rels/" + part.slice(i + 1) + ".rels", d = files.get(rp), out = {};
    if (!d) return out;
    for (const r of findAll(parseXml(unutf8(d)), "Relationship")) out[r.a.Id] = { target: path(part, r.a.Target), type: (r.a.Type || "").replace(/^.*\//, "") };
    return out;
  }

  /* ── formulas: tokens, a parser and the functions ── */
  class XErr { constructor(c) { this.c = c; } toString() { return this.c; } }
  const E = (c) => new XErr(c), isErr = (v) => v instanceof XErr;
  function tokenize(f) {
    const t = [], re = /\s+|("(?:[^"]|"")*")|('(?:[^']|'')+'!\$?[A-Za-z]{1,3}\$?\d+(?::\$?[A-Za-z]{1,3}\$?\d+)?)|([A-Za-z_][\w.]*!\$?[A-Za-z]{1,3}\$?\d+(?::\$?[A-Za-z]{1,3}\$?\d+)?)|(\$?[A-Za-z]{1,3}\$?\d+(?::\$?[A-Za-z]{1,3}\$?\d+)?)(?![\w(])|(\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)|([A-Za-z_][\w.]*)\s*(?=\()|(TRUE|FALSE)(?![\w(])|(<>|<=|>=|[-+*/^&=<>%(),;:])|(#(?:DIV\/0!|VALUE!|REF!|NAME\?|N\/A|NUM!|NULL!))|(.)/gy;
    let m;
    while (re.lastIndex < f.length && (m = re.exec(f))) {
      if (m[1]) t.push({ k: "s", v: m[1].slice(1, -1).replace(/""/g, '"') });
      else if (m[2] || m[3] || m[4]) t.push({ k: "r", v: m[2] || m[3] || m[4] });
      else if (m[5]) t.push({ k: "n", v: +m[5] });
      else if (m[6]) t.push({ k: "f", v: m[6].toUpperCase() });
      else if (m[7]) t.push({ k: "b", v: m[7].toUpperCase() === "TRUE" });
      else if (m[8]) t.push({ k: "o", v: m[8] === ";" ? "," : m[8] });
      else if (m[9]) t.push({ k: "e", v: m[9] });
      else if (m[10]) t.push({ k: "x", v: m[10] });
    }
    return t;
  }
  const BIN = { "=": 1, "<>": 1, "<": 1, ">": 1, "<=": 1, ">=": 1, "&": 2, "+": 3, "-": 3, "*": 4, "/": 4, "^": 5 };
  function parseFormula(f) {
    const t = tokenize(f); let i = 0;
    const peek = () => t[i], next = () => t[i++];
    function primary() {
      const x = next();
      if (!x) throw E("#VALUE!");
      if (x.k === "n") return { k: "n", v: x.v };
      if (x.k === "s") return { k: "s", v: x.v };
      if (x.k === "b") return { k: "b", v: x.v };
      if (x.k === "e") return { k: "e", v: x.v };
      if (x.k === "r") return { k: "r", v: x.v };
      if (x.k === "f") {
        next(); const args = [];
        if (!(peek() && peek().k === "o" && peek().v === ")")) for (;;) {
          if (peek() && peek().k === "o" && (peek().v === "," || peek().v === ")")) args.push({ k: "blank" }); else args.push(expr(0));
          const s = next(); if (!s || s.k !== "o") throw E("#VALUE!"); if (s.v === ")") return { k: "f", v: x.v, a: args }; if (s.v !== ",") throw E("#VALUE!");
        }
        next(); return { k: "f", v: x.v, a: args };
      }
      if (x.k === "o" && x.v === "(") { const e = expr(0), c = next(); if (!c || c.v !== ")") throw E("#VALUE!"); return e; }
      if (x.k === "o" && (x.v === "-" || x.v === "+")) return { k: "u", v: x.v, a: expr(6) };
      if (x.k === "x" && /[A-Za-z]/.test(x.v)) throw E("#NAME?");
      throw E("#VALUE!");
    }
    function postfix() { let e = primary(); while (peek() && peek().k === "o" && peek().v === "%") { next(); e = { k: "%", a: e }; } return e; }
    function expr(min) {
      let l = postfix();
      for (;;) {
        const o = peek(); if (!o || o.k !== "o" || !(o.v in BIN) || BIN[o.v] < min) return l;
        next(); const p = BIN[o.v], r = expr(o.v === "^" ? p : p + 1); l = { k: "bin", v: o.v, l, r };
      }
    }
    const e = expr(0); if (i < t.length) throw E(t[i].k === "f" || t[i].k === "x" ? "#NAME?" : "#VALUE!"); return e;
  }
  /* a formula moved by (dc, dr) cells: relative references follow, $-anchored ones stay */
  function shiftFormula(f, dc, dr) {
    const mv = (r) => r.replace(/(\$?)([A-Za-z]{1,3})(\$?)(\d+)/g, (m, ca, c, ra, n) => {
      const ci = ca ? colIndex(c) : colIndex(c) + dc, ri = ra ? +n - 1 : +n - 1 + dr;
      return ci < 0 || ri < 0 ? "#REF!" : ca + colName(ci) + ra + (ri + 1);
    });
    let out = "", last = 0; const re = /("(?:[^"]|"")*")|((?:'(?:[^']|'')+'|[A-Za-z_][\w.]*)!)?(\$?[A-Za-z]{1,3}\$?\d+(?::\$?[A-Za-z]{1,3}\$?\d+)?)(?![\w(])/g; let m;
    while ((m = re.exec(f))) { if (m[1]) continue; out += f.slice(last, m.index) + (m[2] || "") + mv(m[3]); last = m.index + m[0].length; }
    return out + f.slice(last);
  }
  const num = (v) => {
    if (isErr(v)) return v; if (typeof v === "number") return v; if (typeof v === "boolean") return v ? 1 : 0; if (v == null || v === "") return 0;
    const n = Number(String(v).trim().replace(",", ".")); return Number.isFinite(n) && String(v).trim() !== "" ? n : E("#VALUE!");
  };
  const flat = (a) => Array.isArray(a) ? a.flat(Infinity) : [a];
  /* numbers of a range (text and blanks skipped, as Excel does in SUM); a number typed straight in counts */
  function nums(args) { const out = []; for (const a of args) { if (a && a.range) { for (const v of flat(a.v)) { if (isErr(v)) throw v; if (typeof v === "number") out.push(v); } } else { const n = num(a); if (isErr(n)) throw n; out.push(n); } } return out; }
  function pairs(a, b) { const x = flat(a.range ? a.v : [a]), y = flat(b.range ? b.v : [b]), out = []; if (x.length !== y.length) throw E("#N/A"); for (let i = 0; i < x.length; i++) if (typeof x[i] === "number" && typeof y[i] === "number") out.push([x[i], y[i]]); return out; }
  function fit(p) {
    const n = p.length; if (n < 2) throw E("#DIV/0!");
    let sx = 0, sy = 0; for (const [x, y] of p) { sx += x; sy += y; }
    const mx = sx / n, my = sy / n; let sxx = 0, sxy = 0, syy = 0;
    for (const [x, y] of p) { sxx += (x - mx) ** 2; sxy += (x - mx) * (y - my); syy += (y - my) ** 2; }
    if (!sxx) throw E("#DIV/0!");
    const k = sxy / sxx, b = my - k * mx, r2 = syy ? sxy * sxy / (sxx * syy) : 1;
    const se = n > 2 ? Math.sqrt(Math.max(0, (syy - k * sxy) / (n - 2))) : 0;
    return { k, b, r2, sk: se / Math.sqrt(sxx), sb: se * Math.sqrt(1 / n + mx * mx / sxx), n };
  }
  const val1 = (a) => a && a.range ? (Array.isArray(a.v) && a.v.length === 1 && a.v[0].length === 1 ? a.v[0][0] : E("#VALUE!")) : a;
  const N1 = (a) => { const v = num(val1(a)); if (isErr(v)) throw v; return v; };
  const math1 = (fn) => (a) => { const x = N1(a[0]), y = fn(x); if (!Number.isFinite(y)) throw E("#NUM!"); return y; };
  const FN = {
    SUM: (a) => nums(a).reduce((s, x) => s + x, 0),
    AVERAGE: (a) => { const v = nums(a); if (!v.length) throw E("#DIV/0!"); return v.reduce((s, x) => s + x, 0) / v.length; },
    MIN: (a) => { const v = nums(a); return v.length ? Math.min(...v) : 0; },
    MAX: (a) => { const v = nums(a); return v.length ? Math.max(...v) : 0; },
    COUNT: (a) => nums(a).length,
    COUNTA: (a) => a.reduce((n, x) => n + (x && x.range ? flat(x.v).filter((v) => v !== null && v !== "").length : 1), 0),
    PRODUCT: (a) => nums(a).reduce((s, x) => s * x, 1),
    SUMSQ: (a) => nums(a).reduce((s, x) => s + x * x, 0),
    STDEV: (a) => { const v = nums(a), n = v.length; if (n < 2) throw E("#DIV/0!"); const m = v.reduce((s, x) => s + x, 0) / n; return Math.sqrt(v.reduce((s, x) => s + (x - m) ** 2, 0) / (n - 1)); },
    STDEVP: (a) => { const v = nums(a), n = v.length; if (!n) throw E("#DIV/0!"); const m = v.reduce((s, x) => s + x, 0) / n; return Math.sqrt(v.reduce((s, x) => s + (x - m) ** 2, 0) / n); },
    VAR: (a) => FN.STDEV(a) ** 2, VARP: (a) => FN.STDEVP(a) ** 2,
    MEDIAN: (a) => { const v = nums(a).sort((x, y) => x - y), n = v.length; if (!n) throw E("#NUM!"); return n % 2 ? v[(n - 1) / 2] : (v[n / 2 - 1] + v[n / 2]) / 2; },
    ABS: math1(Math.abs), SQRT: math1(Math.sqrt), EXP: math1(Math.exp), LN: math1(Math.log), LOG10: math1(Math.log10),
    SIN: math1(Math.sin), COS: math1(Math.cos), TAN: math1(Math.tan), ASIN: math1(Math.asin), ACOS: math1(Math.acos), ATAN: math1(Math.atan),
    SINH: math1(Math.sinh), COSH: math1(Math.cosh), TANH: math1(Math.tanh), DEGREES: math1((x) => x * 180 / Math.PI), RADIANS: math1((x) => x * Math.PI / 180),
    INT: math1(Math.floor), SIGN: math1(Math.sign), EVEN: math1((x) => 2 * Math.ceil(x / 2)),
    LOG: (a) => { const x = N1(a[0]), b = a[1] && a[1].k !== "blank" ? N1(a[1]) : 10, y = Math.log(x) / Math.log(b); if (!Number.isFinite(y)) throw E("#NUM!"); return y; },
    POWER: (a) => { const y = N1(a[0]) ** N1(a[1]); if (!Number.isFinite(y)) throw E("#NUM!"); return y; },
    ATAN2: (a) => Math.atan2(N1(a[1]), N1(a[0])),
    PI: () => Math.PI,
    MOD: (a) => { const x = N1(a[0]), d = N1(a[1]); if (!d) throw E("#DIV/0!"); return x - d * Math.floor(x / d); },
    ROUND: (a) => { const k = 10 ** (a[1] ? N1(a[1]) : 0); return Math.round(N1(a[0]) * k) / k; },
    ROUNDUP: (a) => { const k = 10 ** (a[1] ? N1(a[1]) : 0), x = N1(a[0]); return Math.sign(x) * Math.ceil(Math.abs(x) * k) / k; },
    ROUNDDOWN: (a) => { const k = 10 ** (a[1] ? N1(a[1]) : 0), x = N1(a[0]); return Math.sign(x) * Math.floor(Math.abs(x) * k) / k; },
    SLOPE: (a) => fit(pairs(a[1], a[0])).k, INTERCEPT: (a) => fit(pairs(a[1], a[0])).b, RSQ: (a) => fit(pairs(a[1], a[0])).r2,
    CORREL: (a) => { const f = fit(pairs(a[1], a[0])); return Math.sign(f.k) * Math.sqrt(f.r2); },
    PEARSON: (a) => FN.CORREL(a),
    STEYX: (a) => { const p = pairs(a[1], a[0]), f = fit(p), mx = p.reduce((t, q) => t + q[0], 0) / p.length;
      return f.sk * Math.sqrt(p.reduce((t, [x]) => t + (x - mx) ** 2, 0)); },
    /* LINEST in a single cell gives the slope; INDEX(LINEST(...),1,2) the intercept, (2,1) and (2,2) their errors, (3,1) R² */
    LINEST: (a) => { const f = fit(pairs(a[1], a[0])); return { range: true, v: [[f.k, f.b], [f.sk, f.sb], [f.r2, null]] }; },
    IF: (a) => { const c = val1(a[0]); if (isErr(c)) throw c; return truthy(c) ? (a[1] ? a[1] : true) : (a[2] && a[2].k !== "blank" ? a[2] : false); },
    IFERROR: (a) => isErr(a[0]) ? a[1] : a[0],
    AND: (a) => a.every((x) => flat(x && x.range ? x.v : [x]).every(truthy)), OR: (a) => a.some((x) => flat(x && x.range ? x.v : [x]).some(truthy)),
    NOT: (a) => !truthy(val1(a[0])),
    INDEX: (a) => { const g = a[0] && a[0].range ? a[0].v : [[a[0]]], r = a[1] ? N1(a[1]) : 1, c = a[2] ? N1(a[2]) : 1;
      const R = g.length === 1 && !a[2] ? 1 : r, C = g.length === 1 && !a[2] ? r : c; const row = g[R - 1]; if (!row || !(C - 1 in row)) throw E("#REF!"); const v = row[C - 1]; return v == null ? 0 : v; },
    MATCH: (a) => { const x = val1(a[0]), list = flat(a[1].range ? a[1].v : [a[1]]), type = a[2] !== undefined && !(a[2] && a[2].k === "blank") ? N1(a[2]) : 1;
      if (type === 0) { const i = list.findIndex((v) => v === x || (typeof v === "string" && typeof x === "string" && v.toLowerCase() === x.toLowerCase()) || (typeof v === "number" && v === num(x))); if (i < 0) throw E("#N/A"); return i + 1; }
      let best = -1; for (let i = 0; i < list.length; i++) { if (typeof list[i] !== "number") continue; if (type > 0 ? list[i] <= x : list[i] >= x) best = i; else break; } if (best < 0) throw E("#N/A"); return best + 1; },
    ROWS: (a) => a[0].range ? a[0].v.length : 1, COLUMNS: (a) => a[0].range ? a[0].v[0].length : 1,
    CONCATENATE: (a) => a.map((x) => str(val1(x))).join(""), CONCAT: (a) => a.map((x) => flat(x && x.range ? x.v : [x]).map(str).join("")).join(""),
    TEXT: (a) => str(val1(a[0])), VALUE: (a) => N1(a[0]), LEN: (a) => str(val1(a[0])).length,
    ISNUMBER: (a) => typeof val1(a[0]) === "number", ISBLANK: (a) => { const v = val1(a[0]); return v == null || v === ""; }, ISERROR: (a) => isErr(a[0]),
    NA: () => { throw E("#N/A"); },
  };
  FN["STDEV.S"] = FN.STDEV; FN["STDEV.P"] = FN.STDEVP; FN["VAR.S"] = FN.VAR; FN["VAR.P"] = FN.VARP;
  const truthy = (v) => typeof v === "string" ? v.toUpperCase() === "TRUE" || (v !== "" && v.toUpperCase() !== "FALSE" && !!num(v)) : !!v;
  const str = (v) => v == null ? "" : typeof v === "number" ? fmtNum(v) : typeof v === "boolean" ? (v ? "TRUE" : "FALSE") : String(v);
  function fmtNum(x) {
    if (!Number.isFinite(x)) return "#NUM!";
    if (x === 0) return "0";
    const a = Math.abs(x);
    if (a >= 1e11 || a < 1e-9) return x.toExponential(5).replace(/\.?0+e/, "E").replace("e", "E");
    return String(+x.toPrecision(11));
  }
  function evalSheet(wb, sheet, a1, stack) {
    const key = sheet.name + "!" + a1, cell = sheet.cells[a1];
    if (!cell) return null;
    if (!cell.f) return cell.v ?? null;
    if (cell._ok === wb._gen) return cell.v;
    if (stack.has(key)) return E("#REF!");                 /* a circular reference */
    stack.add(key);
    let v;
    try { v = run(wb, sheet, parseFormula(cell.f), stack); if (v && v.range) v = v.v[0] ? v.v[0][0] ?? 0 : 0; if (v === null) v = 0; if (typeof v === "number" && !Number.isFinite(v)) v = E("#NUM!"); }
    catch (e) { v = isErr(e) ? e : E("#VALUE!"); }
    stack.delete(key);
    cell.v = v; cell._ok = wb._gen; return v;
  }
  function rangeOf(wb, sheet, text, stack) {
    const r = parseRange(text); if (!r) throw E("#REF!");
    const sh = r.sheet == null ? sheet : wb.sheets.find((s) => s.name.toLowerCase() === r.sheet.toLowerCase());
    if (!sh) throw E("#REF!");
    if ((r.r1 - r.r0 + 1) * (r.c1 - r.c0 + 1) > 2e6) throw E("#NUM!");
    const rows = [];
    for (let rr = r.r0; rr <= Math.min(r.r1, maxRow(sh)); rr++) { const row = []; for (let cc = r.c0; cc <= r.c1; cc++) row.push(evalSheet(wb, sh, ref(cc, rr), stack)); rows.push(row); }
    return { range: true, v: rows.length ? rows : [[null]], single: r.r0 === r.r1 && r.c0 === r.c1 };
  }
  function maxRow(sh) { if (sh._maxRowGen !== sh._gen || sh._gen === undefined) { let m = 0; for (const k in sh.cells) { const p = parseRef(k); if (p && p[1] > m) m = p[1]; } sh._maxRow = m; sh._maxRowGen = sh._gen; } return sh._maxRow; }
  function run(wb, sheet, n, stack) {
    switch (n.k) {
      case "n": case "s": case "b": return n.v;
      case "e": return E(n.v);
      case "blank": return null;
      case "r": { const r = rangeOf(wb, sheet, n.v, stack); if (r.single) { const v = r.v[0][0]; if (isErr(v)) throw v; return v; } return r; }
      case "u": { const v = num(val1(run(wb, sheet, n.a, stack))); if (isErr(v)) throw v; return n.v === "-" ? -v : v; }
      case "%": { const v = num(val1(run(wb, sheet, n.a, stack))); if (isErr(v)) throw v; return v / 100; }
      case "bin": {
        const L = val1(run(wb, sheet, n.l, stack)), R = val1(run(wb, sheet, n.r, stack));
        if (isErr(L)) throw L; if (isErr(R)) throw R;
        if (n.v === "&") return str(L) + str(R);
        if ("=<><=>=".includes(n.v) && ["=", "<>", "<", ">", "<=", ">="].includes(n.v)) {
          const a = typeof L === "string" ? L.toLowerCase() : L ?? 0, b = typeof R === "string" ? R.toLowerCase() : R ?? 0;
          return { "=": a === b, "<>": a !== b, "<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b }[n.v];
        }
        const a = num(L), b = num(R); if (isErr(a)) throw a; if (isErr(b)) throw b;
        if (n.v === "+") return a + b; if (n.v === "-") return a - b; if (n.v === "*") return a * b;
        if (n.v === "/") { if (!b) throw E("#DIV/0!"); return a / b; }
        const p = a ** b; if (!Number.isFinite(p)) throw E("#NUM!"); return p;
      }
      case "f": {
        const fn = FN[n.v]; if (!fn) throw E("#NAME?");
        const lazy = n.v === "IF" || n.v === "IFERROR";
        if (lazy) {
          if (n.v === "IFERROR") { let v; try { v = run(wb, sheet, n.a[0], stack); } catch (e) { v = isErr(e) ? e : E("#VALUE!"); } return isErr(v) ? run(wb, sheet, n.a[1], stack) : v; }
          const c = val1(run(wb, sheet, n.a[0], stack)); if (isErr(c)) throw c;
          return truthy(c) ? (n.a[1] ? run(wb, sheet, n.a[1], stack) : true) : (n.a[2] && n.a[2].k !== "blank" ? run(wb, sheet, n.a[2], stack) : false);
        }
        const args = n.a.map((a) => a.k === "blank" ? { k: "blank" } : run(wb, sheet, a, stack));
        for (const a of args) if (isErr(a) && n.v !== "ISERROR") throw a;
        return fn(args);
      }
    }
    throw E("#VALUE!");
  }
  /* works out every formula of the workbook (values kept on the cells, errors as XErr) */
  function calc(wb) {
    wb._gen = (wb._gen || 0) + 1;
    for (const sh of wb.sheets) sh._gen = wb._gen;           /* before any formula: one may read another sheet */
    for (const sh of wb.sheets) for (const k in sh.cells) if (sh.cells[k].f) evalSheet(wb, sh, k, new Set());
    return wb;
  }
  /* what a cell shows */
  function show(v) { if (isErr(v)) return v.c; return str(v); }

  /* ── reading ── */
  async function read(bytes) {
    const files = await unzip(bytes), T = (p) => files.has(p) ? unutf8(files.get(p)) : null;
    const wbPart = (() => { const r = rels(files, ""); for (const k in r) if (r[k].type === "officeDocument") return r[k].target; return "xl/workbook.xml"; })();
    const wx = parseXml(T(wbPart) || ""), wr = rels(files, wbPart);
    let shared = [];
    for (const k in wr) if (wr[k].type === "sharedStrings" && files.has(wr[k].target)) shared = kids(find(parseXml(T(wr[k].target)), "sst"), "si").map(textOfRun);
    const wb = { sheets: [] };
    for (const s of findAll(wx, "sheet")) {
      const target = wr[s.a.id] && wr[s.a.id].target; if (!target || !files.has(target)) continue;
      const sx = parseXml(T(target)), sheet = { name: s.a.name, cells: {}, cols: {}, charts: [] }, sharedF = {};
      for (const c of findAll(find(sx, "cols"), "col")) { const w = +c.a.width; if (w) for (let i = +c.a.min; i <= Math.min(+c.a.max, 60); i++) sheet.cols[i - 1] = w; }
      for (const c of findAll(find(sx, "sheetData"), "c")) {
        const t = c.a.t, v = kid(c, "v"), fe = kid(c, "f"), is = kid(c, "is"), cell = {};
        if (t === "s") cell.v = shared[+textOf(v)] ?? "";
        else if (t === "inlineStr") cell.v = textOfRun(is);
        else if (t === "str") cell.v = textOf(v);
        else if (t === "b") cell.v = textOf(v) === "1";
        else if (t === "e") cell.v = E(textOf(v));
        else if (v) cell.v = +textOf(v);
        if (fe) {
          const ft = textOf(fe);
          if (fe.a.t === "shared") { if (ft) sharedF[fe.a.si] = { f: ft, at: parseRef(c.a.r) }; else if (sharedF[fe.a.si]) { const m = sharedF[fe.a.si], p = parseRef(c.a.r); cell.f = shiftFormula(m.f, p[0] - m.at[0], p[1] - m.at[1]); } }
          if (ft) cell.f = ft;
        }
        if (cell.v === undefined && !cell.f) continue;
        if (cell.v === undefined) cell.v = null;
        sheet.cells[c.a.r] = cell;
      }
      const sr = rels(files, target), dr = find(sx, "drawing");
      if (dr && sr[dr.a.id]) {
        const dpart = sr[dr.a.id].target, dx = parseXml(T(dpart) || ""), drels = rels(files, dpart);
        for (const anc of [...findAll(dx, "twoCellAnchor"), ...findAll(dx, "oneCellAnchor")]) {
          const ch = find(anc, "chart"), fr = kid(anc, "from"), to = kid(anc, "to");
          if (!ch || !drels[ch.a.id]) continue;
          const chart = readChart(parseXml(T(drels[ch.a.id].target) || ""));
          if (!chart) continue;
          const at = (e) => e ? [+textOf(kid(e, "col")), +textOf(kid(e, "row"))] : null, a = at(fr), b = at(to) || (a && [a[0] + 8, a[1] + 15]);
          chart.at = a ? { c0: a[0], r0: a[1], c1: b[0], r1: b[1] } : { c0: 4, r0: 1, c1: 12, r1: 16 };
          sheet.charts.push(chart);
        }
      }
      wb.sheets.push(sheet);
    }
    if (!wb.sheets.length) wb.sheets.push({ name: "Sheet1", cells: {}, cols: {}, charts: [] });
    return wb;
  }
  function textOfRun(si) { if (!si) return ""; const t = kid(si, "t"); if (t) return t.t; return kids(si, "r").map((r) => textOf(kid(r, "t"))).join(""); }
  function readChart(cx) {
    const plot = find(cx, "plotArea"); if (!plot) return null;
    const kind = plot.k.find((k) => /Chart$/.test(k.n)); if (!kind) return null;
    const type = kind.n === "scatterChart" ? "scatter" : kind.n === "lineChart" ? "line" : kind.n.replace(/Chart$/, "");
    const titleText = (t) => t ? findAll(t, "t").map((x) => x.t).join("") || textOf(find(t, "v")) : "";
    const chart = { type, title: titleText(kid(find(cx, "chart"), "title")), x: {}, y: {}, series: [] };
    for (const s of kids(kind, "ser")) {
      const tx = kid(s, "tx"), xs = kid(s, "xVal") || kid(s, "cat"), ys = kid(s, "yVal") || kid(s, "val"), tl = kid(s, "trendline"), sp = kid(s, "spPr");
      const ln = sp && kid(sp, "ln"), mk = kid(s, "marker");
      chart.series.push({ name: tx ? (textOf(find(tx, "v")) || textOf(find(tx, "f"))) : "", x: xs ? textOf(find(xs, "f")) : "", y: ys ? textOf(find(ys, "f")) : "",
        line: !(ln && kid(ln, "noFill")), marker: !(mk && find(mk, "symbol") && find(mk, "symbol").a.val === "none"),
        trend: tl ? (find(tl, "trendlineType") || { a: {} }).a.val || "linear" : null, eq: !!(tl && find(tl, "dispEq") && find(tl, "dispEq").a.val !== "0"),
        r2: !!(tl && find(tl, "dispRSqr") && find(tl, "dispRSqr").a.val !== "0") });
    }
    const axes = [...kids(plot, "valAx"), ...kids(plot, "catAx")];
    for (const ax of axes) {
      const pos = (kid(ax, "axPos") || { a: {} }).a.val, o = pos === "l" || pos === "r" ? chart.y : chart.x, lb = find(kid(ax, "scaling"), "logBase");
      o.title = titleText(kid(ax, "title")); o.log = !!lb;
    }
    return chart;
  }

  /* ── writing ── */
  const NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main", NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    NS_PKG = "http://schemas.openxmlformats.org/package/2006/relationships", NS_C = "http://schemas.openxmlformats.org/drawingml/2006/chart",
    NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main", NS_XDR = "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing";
  const HEAD = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n';
  const relsXml = (list) => HEAD + `<Relationships xmlns="${NS_PKG}">` + list.map(([id, type, target]) => `<Relationship Id="${id}" Type="${NS_R}/${type}" Target="${xml(target)}"/>`).join("") + "</Relationships>";
  function sheetXml(sh, hasDrawing) {
    const rows = new Map();
    for (const k in sh.cells) { const p = parseRef(k); if (!p) continue; if (!rows.has(p[1])) rows.set(p[1], []); rows.get(p[1]).push([p[0], k, sh.cells[k]]); }
    const rowXml = [...rows.keys()].sort((a, b) => a - b).map((r) => `<row r="${r + 1}">` + rows.get(r).sort((a, b) => a[0] - b[0]).map(([, k, c]) => {
      const s = c.b ? ' s="1"' : "", f = c.f ? `<f>${xml(c.f)}</f>` : "", v = c.v;
      if (isErr(v)) return `<c r="${k}"${s} t="e">${f}<v>${xml(v.c)}</v></c>`;
      if (typeof v === "number" && Number.isFinite(v)) return `<c r="${k}"${s}>${f}<v>${v}</v></c>`;
      if (typeof v === "boolean") return `<c r="${k}"${s} t="b">${f}<v>${v ? 1 : 0}</v></c>`;
      if (v == null || v === "") return c.f ? `<c r="${k}"${s}>${f}</c>` : c.b ? `<c r="${k}"${s}/>` : "";
      return c.f ? `<c r="${k}"${s} t="str">${f}<v>${xml(v)}</v></c>` : `<c r="${k}"${s} t="inlineStr"><is><t xml:space="preserve">${xml(v)}</t></is></c>`;
    }).join("") + "</row>").join("");
    const cols = Object.keys(sh.cols || {}).map(Number).sort((a, b) => a - b);
    return HEAD + `<worksheet xmlns="${NS_MAIN}" xmlns:r="${NS_R}"><sheetViews><sheetView workbookViewId="0"/></sheetViews><sheetFormatPr defaultRowHeight="15"/>` +
      (cols.length ? "<cols>" + cols.map((c) => `<col min="${c + 1}" max="${c + 1}" width="${+sh.cols[c] || 10}" customWidth="1"/>`).join("") + "</cols>" : "") +
      `<sheetData>${rowXml}</sheetData><pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3"/>` + (hasDrawing ? '<drawing r:id="rId1"/>' : "") + "</worksheet>";
  }
  const rich = (t, size) => `<c:tx><c:rich><a:bodyPr/><a:lstStyle/><a:p><a:pPr><a:defRPr sz="${size}" b="0"/></a:pPr><a:r><a:rPr lang="en-US" sz="${size}" b="0"/><a:t>${xml(t)}</a:t></a:r></a:p></c:rich></c:tx>`;
  function cacheOf(wb, refText, numeric) {
    const r = parseRange(refText || ""); if (!r) return "";
    const sh = (r.sheet && wb.sheets.find((s) => s.name === r.sheet)) || wb.sheets[0], vals = [];
    for (let rr = r.r0; rr <= r.r1; rr++) for (let cc = r.c0; cc <= r.c1; cc++) { const c = sh.cells[ref(cc, rr)]; vals.push(c ? c.v : null); }
    if (numeric) return `<c:numCache><c:formatCode>General</c:formatCode><c:ptCount val="${vals.length}"/>` + vals.map((v, i) => typeof v === "number" && Number.isFinite(v) ? `<c:pt idx="${i}"><c:v>${v}</c:v></c:pt>` : "").join("") + "</c:numCache>";
    return `<c:strCache><c:ptCount val="${vals.length}"/>` + vals.map((v, i) => v == null || v === "" ? "" : `<c:pt idx="${i}"><c:v>${xml(show(v))}</c:v></c:pt>`).join("") + "</c:strCache>";
  }
  const COLORS = ["4472C4", "ED7D31", "A5A5A5", "FFC000", "5B9BD5", "70AD47", "264478", "9E480E"];
  function chartXml(wb, ch) {
    const scatter = ch.type !== "line";
    const ser = (ch.series || []).map((s, i) => {
      const col = COLORS[i % COLORS.length];
      const sp = `<c:spPr>${s.line ? `<a:ln w="19050" cap="rnd"><a:solidFill><a:srgbClr val="${col}"/></a:solidFill><a:round/></a:ln>` : '<a:ln w="25400" cap="rnd"><a:noFill/><a:round/></a:ln>'}</c:spPr>`;
      const mk = s.marker === false ? '<c:marker><c:symbol val="none"/></c:marker>' : `<c:marker><c:symbol val="circle"/><c:size val="5"/><c:spPr><a:solidFill><a:srgbClr val="${col}"/></a:solidFill><a:ln w="9525"><a:solidFill><a:srgbClr val="${col}"/></a:solidFill></a:ln></c:spPr></c:marker>`;
      const tl = s.trend ? `<c:trendline><c:spPr><a:ln w="19050" cap="rnd"><a:solidFill><a:srgbClr val="${col}"/></a:solidFill><a:prstDash val="sysDot"/></a:ln></c:spPr><c:trendlineType val="${s.trend}"/><c:dispRSqr val="${s.r2 ? 1 : 0}"/><c:dispEq val="${s.eq ? 1 : 0}"/>${s.eq || s.r2 ? '<c:trendlineLbl><c:numFmt formatCode="General" sourceLinked="0"/></c:trendlineLbl>' : ""}</c:trendline>` : "";
      const tx = s.name ? `<c:tx><c:v>${xml(s.name)}</c:v></c:tx>` : "";
      const xs = scatter ? `<c:xVal><c:numRef><c:f>${xml(s.x)}</c:f>${cacheOf(wb, s.x, true)}</c:numRef></c:xVal><c:yVal><c:numRef><c:f>${xml(s.y)}</c:f>${cacheOf(wb, s.y, true)}</c:numRef></c:yVal><c:smooth val="0"/>`
        : (s.x ? `<c:cat><c:numRef><c:f>${xml(s.x)}</c:f>${cacheOf(wb, s.x, true)}</c:numRef></c:cat>` : "") + `<c:val><c:numRef><c:f>${xml(s.y)}</c:f>${cacheOf(wb, s.y, true)}</c:numRef></c:val><c:smooth val="0"/>`;
      return `<c:ser><c:idx val="${i}"/><c:order val="${i}"/>${tx}${sp}${mk}${tl}${xs}</c:ser>`;
    }).join("");
    const axis = (id, cross, pos, o, cat) => `<c:${cat ? "catAx" : "valAx"}><c:axId val="${id}"/><c:scaling>${o.log ? '<c:logBase val="10"/>' : ""}<c:orientation val="minMax"/></c:scaling><c:delete val="0"/><c:axPos val="${pos}"/>` +
      `<c:majorGridlines><c:spPr><a:ln w="6350"><a:solidFill><a:srgbClr val="D9D9D9"/></a:solidFill></a:ln></c:spPr></c:majorGridlines>` +
      (o.title ? `<c:title>${rich(o.title, 1000)}<c:overlay val="0"/></c:title>` : "") + `<c:numFmt formatCode="General" sourceLinked="1"/><c:majorTickMark val="out"/><c:minorTickMark val="none"/><c:tickLblPos val="low"/>` +
      `<c:crossAx val="${cross}"/><c:crosses val="autoZero"/>${cat ? '<c:auto val="1"/><c:lblAlgn val="ctr"/><c:lblOffset val="100"/><c:noMultiLvlLbl val="0"/>' : '<c:crossBetween val="midCat"/>'}</c:${cat ? "catAx" : "valAx"}>`;
    const kindXml = scatter ? `<c:scatterChart><c:scatterStyle val="lineMarker"/><c:varyColors val="0"/>${ser}<c:axId val="500000001"/><c:axId val="500000002"/></c:scatterChart>`
      : `<c:lineChart><c:grouping val="standard"/><c:varyColors val="0"/>${ser}<c:marker val="1"/><c:axId val="500000001"/><c:axId val="500000002"/></c:lineChart>`;
    return HEAD + `<c:chartSpace xmlns:c="${NS_C}" xmlns:a="${NS_A}" xmlns:r="${NS_R}"><c:roundedCorners val="0"/><c:chart>` +
      (ch.title ? `<c:title>${rich(ch.title, 1300)}<c:overlay val="0"/></c:title><c:autoTitleDeleted val="0"/>` : '<c:autoTitleDeleted val="1"/>') +
      `<c:plotArea><c:layout/>${kindXml}${axis(500000001, 500000002, "b", ch.x || {}, !scatter)}${axis(500000002, 500000001, "l", ch.y || {}, false)}</c:plotArea>` +
      ((ch.series || []).length > 1 ? '<c:legend><c:legendPos val="r"/><c:overlay val="0"/></c:legend>' : "") + '<c:plotVisOnly val="1"/><c:dispBlanksAs val="gap"/></c:chart></c:chartSpace>';
  }
  function drawingXml(charts) {
    return HEAD + `<xdr:wsDr xmlns:xdr="${NS_XDR}" xmlns:a="${NS_A}">` + charts.map((ch, i) => {
      const at = ch.at || { c0: 4, r0: 1, c1: 12, r1: 16 };
      return `<xdr:twoCellAnchor editAs="oneCell"><xdr:from><xdr:col>${at.c0}</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>${at.r0}</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:from>` +
        `<xdr:to><xdr:col>${at.c1}</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>${at.r1}</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:to>` +
        `<xdr:graphicFrame macro=""><xdr:nvGraphicFramePr><xdr:cNvPr id="${i + 2}" name="Chart ${i + 1}"/><xdr:cNvGraphicFramePr/></xdr:nvGraphicFramePr>` +
        `<xdr:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/></xdr:xfrm><a:graphic><a:graphicData uri="${NS_C}"><c:chart xmlns:c="${NS_C}" xmlns:r="${NS_R}" r:id="rId${i + 1}"/></a:graphicData></a:graphic></xdr:graphicFrame><xdr:clientData/></xdr:twoCellAnchor>`;
    }).join("") + "</xdr:wsDr>";
  }
  const STYLES = HEAD + `<styleSheet xmlns="${NS_MAIN}"><fonts count="2"><font><sz val="11"/><name val="Calibri"/><family val="2"/></font><font><b/><sz val="11"/><name val="Calibri"/><family val="2"/></font></fonts>` +
    `<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>` +
    `<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>` +
    `<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>`;
  function write(wb) {
    calc(wb);
    const files = [], ct = [], wbRels = [];
    let chartN = 0, drawN = 0;
    wb.sheets.forEach((sh, i) => {
      const charts = (sh.charts || []).filter((c) => c.series && c.series.length);
      files.push({ name: `xl/worksheets/sheet${i + 1}.xml`, data: sheetXml(sh, charts.length > 0) });
      ct.push([`/xl/worksheets/sheet${i + 1}.xml`, "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"]);
      wbRels.push([`rId${i + 1}`, "worksheet", `worksheets/sheet${i + 1}.xml`]);
      if (charts.length) {
        const d = ++drawN;
        files.push({ name: `xl/worksheets/_rels/sheet${i + 1}.xml.rels`, data: relsXml([["rId1", "drawing", `../drawings/drawing${d}.xml`]]) });
        files.push({ name: `xl/drawings/drawing${d}.xml`, data: drawingXml(charts) });
        ct.push([`/xl/drawings/drawing${d}.xml`, "application/vnd.openxmlformats-officedocument.drawing+xml"]);
        const dr = [];
        charts.forEach((ch, k) => {
          const n = ++chartN;
          files.push({ name: `xl/charts/chart${n}.xml`, data: chartXml(wb, ch) });
          ct.push([`/xl/charts/chart${n}.xml`, "application/vnd.openxmlformats-officedocument.drawingml.chart+xml"]);
          dr.push([`rId${k + 1}`, "chart", `../charts/chart${n}.xml`]);
        });
        files.push({ name: `xl/drawings/_rels/drawing${d}.xml.rels`, data: relsXml(dr) });
      }
    });
    wbRels.push([`rId${wb.sheets.length + 1}`, "styles", "styles.xml"]);
    const sheetsXml = wb.sheets.map((sh, i) => `<sheet name="${xml(String(sh.name).slice(0, 31))}" sheetId="${i + 1}" r:id="rId${i + 1}"/>`).join("");
    const out = [
      { name: "[Content_Types].xml", data: HEAD + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>' +
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>' +
        ct.map(([p, t]) => `<Override PartName="${p}" ContentType="${t}"/>`).join("") + "</Types>" },
      { name: "_rels/.rels", data: relsXml([["rId1", "officeDocument", "xl/workbook.xml"]]) },
      { name: "xl/workbook.xml", data: HEAD + `<workbook xmlns="${NS_MAIN}" xmlns:r="${NS_R}"><bookViews><workbookView/></bookViews><sheets>${sheetsXml}</sheets><calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>` },
      { name: "xl/_rels/workbook.xml.rels", data: relsXml(wbRels) },
      { name: "xl/styles.xml", data: STYLES },
      ...files,
    ];
    return zip(out);
  }

  /* ── CSV ── */
  function parseCsv(text, sep) {
    text = String(text).replace(/^﻿/, "");
    if (!sep) { const head = text.slice(0, 2000), c = (s) => (head.match(new RegExp(s, "g")) || []).length; sep = c("\t") > c(",") && c("\t") >= c(";") ? "\t" : c(";") > c(",") ? ";" : ","; }
    const rows = []; let row = [], cell = "", q = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (q) { if (ch === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; } else cell += ch; continue; }
      if (ch === '"' && cell === "") q = true;
      else if (ch === sep) { row.push(cell); cell = ""; }
      else if (ch === "\n" || ch === "\r") { if (ch === "\r" && text[i + 1] === "\n") i++; row.push(cell); rows.push(row); row = []; cell = ""; }
      else cell += ch;
    }
    if (cell !== "" || row.length) { row.push(cell); rows.push(row); }
    return rows;
  }
  function typed(s) { const t = String(s).trim(); if (t === "") return null; if (/^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$/.test(t)) return +t; if (/^(true|false)$/i.test(t)) return t.toLowerCase() === "true"; return s; }
  function fromCsv(text, name) {
    const sheet = { name: String(name || "Sheet1").replace(/\.[^.]*$/, "").replace(/[\\/?*[\]:]/g, "_").slice(0, 31) || "Sheet1", cells: {}, cols: {}, charts: [] };
    parseCsv(text).forEach((row, r) => row.forEach((s, c) => { const v = typed(s); if (v !== null) sheet.cells[ref(c, r)] = { v }; }));
    return { sheets: [sheet] };
  }
  function bounds(sh) { let r1 = -1, c1 = -1; for (const k in sh.cells) { const p = parseRef(k); if (p) { if (p[0] > c1) c1 = p[0]; if (p[1] > r1) r1 = p[1]; } } return { r1, c1 }; }
  function toCsv(sh, sep = ",") {
    const { r1, c1 } = bounds(sh), lines = [];
    for (let r = 0; r <= r1; r++) { const row = []; for (let c = 0; c <= c1; c++) { const cell = sh.cells[ref(c, r)], s = cell ? show(cell.v) : ""; row.push(/[",\n\r;\t]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s); } lines.push(row.join(sep)); }
    return lines.join("\r\n") + (lines.length ? "\r\n" : "");
  }

  /* ── what the grader reads ── */
  function toText(wb, name, opt) {
    opt = opt || {}; const MAXR = opt.maxRows || 120, MAXC = opt.maxCols || 26, CH = opt.maxChars || 60000;
    calc(wb);
    const out = [`[Spreadsheet file: ${name}${wb.sheets.length > 1 ? " · " + wb.sheets.length + " sheets" : ""}]`];
    for (const sh of wb.sheets) {
      const { r1, c1 } = bounds(sh);
      out.push("", `Sheet "${sh.name}"` + (r1 < 0 ? " (empty)" : ` · ${ref(0, 0)}:${ref(c1, r1)} (${r1 + 1} rows × ${c1 + 1} columns)`));
      if (r1 >= 0) {
        const cell = (c, r) => { const x = sh.cells[ref(c, r)]; if (!x) return ""; const s = show(x.v); return x.f ? `${s} {=${x.f}}` : s; };
        const wide = c1 + 1 > MAXC, cols = Math.min(c1 + 1, MAXC);
        const line = (r) => `${r + 1}\t` + Array.from({ length: cols }, (_, c) => cell(c, r)).join("\t") + (wide ? `\t… (${c1 + 1 - MAXC} more columns)` : "");
        out.push("\t" + Array.from({ length: cols }, (_, c) => colName(c)).join("\t"));
        if (r1 + 1 <= MAXR) for (let r = 0; r <= r1; r++) out.push(line(r));
        else {
          /* a long table: its head, rows spread evenly through it, the rows around the peak of its last numeric column, its end */
          const keep = new Set(), step = Math.ceil((r1 + 1) / Math.max(10, Math.round(MAXR / 3)));
          for (let r = 0; r < 12; r++) keep.add(r);
          for (let r = 0; r <= r1; r += step) keep.add(r);
          for (let c = c1; c >= 0; c--) { let mx = -Infinity, at = -1; for (let r = 1; r <= r1; r++) { const x = sh.cells[ref(c, r)]; if (x && typeof x.v === "number" && x.v > mx) { mx = x.v; at = r; } }
            if (at >= 0) { for (let r = Math.max(0, at - 6); r <= Math.min(r1, at + 6); r++) keep.add(r); break; } }
          for (let r = Math.max(0, r1 - 2); r <= r1; r++) keep.add(r);
          let prev = -1;
          for (const r of [...keep].sort((a, b) => a - b)) { if (r > prev + 1) out.push(`… ${r - prev - 1} rows …`); out.push(line(r)); prev = r; }
        }
        /* long or wide data: what each column holds, and where each row peaks (a spectrum, a time series) */
        if (r1 + 1 > MAXR || wide) {
          const stats = [];
          for (let c = 0; c <= Math.min(c1, 40); c++) { let n = 0, mn = Infinity, mx = -Infinity, at = -1; for (let r = 0; r <= r1; r++) { const x = sh.cells[ref(c, r)]; if (x && typeof x.v === "number") { n++; if (x.v < mn) mn = x.v; if (x.v > mx) { mx = x.v; at = r; } } } if (n) stats.push(`${colName(c)}: ${n} numbers, min ${fmtNum(mn)}, max ${fmtNum(mx)} at row ${at + 1}`); }
          if (stats.length) out.push("Columns (summary computed by the site, not written by the student): " + stats.join("; "));
          if (wide) {
            const peaks = [];
            for (let r = 0; r <= r1 && peaks.length < 80; r += Math.max(1, Math.ceil((r1 + 1) / 80))) { let mx = -Infinity, at = -1; for (let c = 1; c <= c1; c++) { const x = sh.cells[ref(c, r)]; if (x && typeof x.v === "number" && x.v > mx) { mx = x.v; at = c; } } if (at >= 0) { const h = sh.cells[ref(at, 0)], a0 = sh.cells[ref(0, r)]; peaks.push(`row ${r + 1}${a0 ? " (" + show(a0.v) + ")" : ""}: max ${fmtNum(mx)} in column ${colName(at)}${h && r ? " [" + show(h.v) + "]" : ""}`); } }
            if (peaks.length) out.push("Row maxima (computed by the site, not written by the student): " + peaks.join("; "));
          }
        }
      }
      for (const ch of sh.charts || []) {
        out.push(`Chart (${ch.type})${ch.title ? ` "${ch.title}"` : ""} at ${ref(ch.at ? ch.at.c0 : 0, ch.at ? ch.at.r0 : 0)}: x axis "${(ch.x && ch.x.title) || ""}"${ch.x && ch.x.log ? " (log scale)" : ""}, y axis "${(ch.y && ch.y.title) || ""}"${ch.y && ch.y.log ? " (log scale)" : ""}`);
        for (const s of ch.series || []) {
          let fitTxt = "";
          if (s.trend) {
            try {
              const xs = rangeOf(wb, sh, s.x, new Set()), ys = rangeOf(wb, sh, s.y, new Set()), p = [];
              const xv = flat(xs.v), yv = flat(ys.v);
              for (let i = 0; i < Math.min(xv.length, yv.length); i++) if (typeof xv[i] === "number" && typeof yv[i] === "number") p.push([xv[i], yv[i]]);
              const tr = s.trend, P = tr === "exp" ? p.filter((q) => q[1] > 0).map(([x, y]) => [x, Math.log(y)]) : tr === "log" ? p.filter((q) => q[0] > 0).map(([x, y]) => [Math.log(x), y]) : tr === "power" ? p.filter((q) => q[0] > 0 && q[1] > 0).map(([x, y]) => [Math.log(x), Math.log(y)]) : p;
              const f = fit(P);
              fitTxt = tr === "exp" ? `; trendline y = ${fmtNum(Math.exp(f.b))}·e^(${fmtNum(f.k)}x)` : tr === "log" ? `; trendline y = ${fmtNum(f.k)}·ln(x) + ${fmtNum(f.b)}` : tr === "power" ? `; trendline y = ${fmtNum(Math.exp(f.b))}·x^${fmtNum(f.k)}` : `; trendline y = ${fmtNum(f.k)}x + ${fmtNum(f.b)}`;
              fitTxt += `, R² = ${fmtNum(+f.r2.toFixed(5))}${s.eq ? " (equation shown)" : ""}${s.r2 ? " (R² shown)" : ""}`;
            } catch (e) { fitTxt = `; trendline ${s.trend}`; }
          }
          out.push(`  series${s.name ? ` "${s.name}"` : ""}: x = ${s.x || "—"}, y = ${s.y || "—"}${s.line ? ", lines" : ", markers only"}${fitTxt}`);
        }
      }
      if (out.join("\n").length > CH) { out.push("… (file truncated)"); break; }
    }
    const t = out.join("\n"); return t.length > CH ? t.slice(0, CH) + "\n… (file truncated)" : t;
  }
  /* a text file handed in as it is (an instrument's .txt, a program's output); long ones are cut */
  function textFileToText(text, name, maxChars) {
    const lim = maxChars || 60000, t = String(text).replace(/\r\n/g, "\n");
    return `[Text file: ${name}]\n` + (t.length > lim ? t.slice(0, lim) + "\n… (file truncated)" : t);
  }
  /* any file the candidate attaches: .xlsx/.xlsm, .csv/.tsv, .txt/.dat → the text the grader reads */
  async function fileToText(name, bytes, opt) {
    const ext = (/\.([^.]+)$/.exec(name) || [])[1]?.toLowerCase() || "";
    if (ext === "xlsx" || ext === "xlsm") return toText(await read(bytes), name, opt);
    const text = typeof bytes === "string" ? bytes : unutf8(bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes));
    if (ext === "csv" || ext === "tsv") return toText(fromCsv(text, name), name, opt);
    return textFileToText(text, name, opt && opt.maxChars);
  }

  /* a deep copy (errors stay errors; the calculation marks are dropped) */
  function clone(wb) {
    return { sheets: wb.sheets.map((sh) => ({ name: sh.name, cols: { ...(sh.cols || {}) }, charts: JSON.parse(JSON.stringify(sh.charts || [])),
      cells: Object.fromEntries(Object.entries(sh.cells).map(([k, c]) => [k, { v: c.v, ...(c.f ? { f: c.f } : {}), ...(c.b ? { b: true } : {}) }])) })) };
  }
  const api = { clone, colName, colIndex, parseRef, parseRange, ref, absRange, quoteSheet, zip, unzip, crc32, parseXml, read, write, calc, show, fmtNum,
    parseFormula, shiftFormula, isErr, XErr, FN, fit, parseCsv, fromCsv, toCsv, toText, fileToText, bounds, typed };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.HLXlsx = api;
})(typeof window !== "undefined" ? window : globalThis);
