/* The items of a marking scheme as the model listed them, made safe to add up.
   A scheme read from a PDF sometimes repeats one part's id on each of its rows (IPhO 2017 E1: A1 once per concentration)
   and puts the part's total on every row, so the paper's points came out three times too high (33.2 instead of 10).
   Rows sharing an id and the same points are that case: they become one item worth those points once, with every row's
   requirement. Rows sharing an id with different points are separate marks: each keeps its points under its own id. */
const NUMERIC = ["full_min", "full_max", "partial", "checks", "unit", "n_min", "n_class"];

/* a value's full-mark interval only when both ends were given (IPhO 2025 T2 came back with lone lower bounds such as
   full_min 14.6, which read as «anything above 14.6»), and only the partial intervals with two ends */
function intervals(row) {
  const out = { ...row }, lo = out.full_min, hi = out.full_max;
  if (!(Number.isFinite(lo) && Number.isFinite(hi))) { delete out.full_min; delete out.full_max; }
  /* an interval of zero width is the solution's own number copied as a window (IPhO 2013 E1: n = 1.54 exactly, the sample
     apparatus's readings): the official value with its default tolerance instead */
  else if (lo === hi) { delete out.full_min; delete out.full_max; if (out.ref == null) out.ref = String(lo); }
  if (Array.isArray(out.partial)) out.partial = out.partial.filter(p => p && Number.isFinite(p.min) && Number.isFinite(p.max) && +p.points > 0);
  if (out.role !== "result" && out.role !== "step") delete out.role;                 // R13: what the answer alone earns
  return out;
}

export function tidySchemeItems(raw) {
  const rows = (Array.isArray(raw) ? raw : []).filter(i => i && i.id != null && String(i.id).trim() && +i.points > 0)
    .map(i => intervals({ ...i, id: String(i.id).trim().slice(0, 20), points: +i.points }))
    .map(i => { const alt = String(i.alt ?? "").trim(); if (/^[A-Za-z0-9.]{1,20}\/\d{1,2}$/.test(alt)) return { ...i, alt }; const { alt: _, ...rest } = i; return rest; });
  const groups = new Map();
  for (const row of rows) { const g = groups.get(row.id); if (g) g.push(row); else groups.set(row.id, [row]); }
  const out = [];
  for (const [id, group] of groups) {
    if (group.length === 1) { out.push(group[0]); continue; }
    if (group.every(r => Math.abs(r.points - group[0].points) < 1e-9)) {
      const merged = { ...group[0], what: group.map(r => String(r.what || "")).filter(Boolean).join(" / ").slice(0, 4000),
        sheet: group.some(r => r.sheet === "answer") ? "answer" : "any" };
      for (const k of NUMERIC) delete merged[k];                // the rows' own intervals and checks no longer add up to one mark
      out.push(merged);
      continue;
    }
    group.forEach((r, i) => out.push(i ? { ...r, id: `${id}#${i + 1}`.slice(0, 20) } : r));
  }
  return out;
}

export const schemePoints = items => +items.reduce((a, i) => a + i.points, 0).toFixed(2);

/* The printed points of each question bound what its items can add up to. Official solutions sometimes list items
   that add up to more than the question's own heading: IPhO 2025 T3 C.3 is headed 1.3 pt but its items give
   0.2+0.2+0.1+0.3+0.1+0.1+0.2+0.2 = 1.4, so the paper came out at 10.1 instead of 10 (30.1 for the three).
   `parts` are the headings as printed ({ id: "C.3", points: 1.3 }; a problem «C» can hold «C.3»), `total` the
   paper's printed total. An item belongs to the most specific part whose id starts its own (C.3 holds C.3.4 and
   C3.4, not C.31); each part counts at most its printed points, and the whole at most the printed total. A part whose
   items add up to less than its heading is left as listed: the missing marks cannot be given to anyone. */
const tokens = id => String(id || "").toLowerCase().match(/[a-z]+|\d+/g) || [];
const startsWith = (a, b) => b.length < a.length && b.every((t, i) => t === a[i]);
const same = (a, b) => a.length === b.length && b.every((t, i) => t === a[i]);

export function cleanParts(raw) {
  const seen = new Set();
  return (Array.isArray(raw) ? raw : []).filter(p => p && p.id != null && +p.points > 0 && tokens(p.id).length)
    .map(p => ({ id: String(p.id).trim().slice(0, 20), points: +p.points, ...(p.final_full === true ? { final_full: true } : {}) }))
    .filter(p => { const k = tokens(p.id).join("."); if (seen.has(k)) return false; seen.add(k); return true; });
}

/* Where the official solution says a correct final answer earns a part's marks without the working (IPhO 2023 T3 «a
   correct final answer gets full points», IPhO 2018 T1 A.1–A.3), the scheme marks that part final_full: once every result
   item of the part is fully met, its step items are full too (the part's printed points still cap it). The scheme listed
   the steps as items that add up, so a correct final 0.23 m/s earned 0.6 of 2.0. */
export function finalAnswerFull(items, scheme) {
  const spec = new Map((scheme?.items || []).map(i => [i.id, i]));
  for (const part of cleanParts(scheme?.parts).filter(p => p.final_full)) {
    const t = tokens(part.id), mine = (items || []).filter(i => { const it = tokens(i.id); return it.length >= t.length && t.every((x, k) => x === it[k]); });
    const results = mine.filter(i => spec.get(i.id)?.role === "result");
    if (!results.length || !results.every(i => +i.got >= +i.points)) continue;
    for (const i of mine) if (+i.got < +i.points) { i.got = +i.points; i.decision = "met"; i.final = true; }
  }
  return items;
}

/* A step the solution credits «even if it was done inherently» (APhO 2025 T1 A.2.1 ω, C.2.1 «the net torque on a sphere
   is zero», C.2.2 «τ = −τ'») has no line of its own to quote: it is earned when a result of its question is fully met
   (the correct h_max cannot be had without ω). Code gives it then; the grader and R13 zeroed all three, written or not. */
export const INHERENT = /\b(?:even if (?:it (?:was|is) )?(?:done |used |shown )?(?:inherently|implicitly)|(?:done|used) (?:inherently|implicitly))\b/i;
export function impliedSteps(items, scheme) {
  const spec = new Map((scheme?.items || []).map(i => [i.id, i]));
  for (const i of items || []) {
    const it = spec.get(i.id);
    if (!it || +i.got >= +i.points || !INHERENT.test(String(it.what || ""))) continue;
    const t = tokens(i.id).slice(0, -1);
    if (!t.length) continue;
    const results = (items || []).filter(j => j !== i && spec.get(j.id)?.role === "result" && (spec.get(j.id)?.alt || null) === (it.alt || null)
      && (() => { const u = tokens(j.id); return u.length >= t.length && t.every((x, k) => x === u[k]); })());
    if (results.length && results.some(j => +j.got >= +j.points)) { i.got = +i.points; i.decision = "met"; i.implied = true; }
  }
  return items;
}

export function cappedSum(items, parts, total, value = i => i.points) {
  const list = cleanParts(parts).map(p => ({ ...p, t: tokens(p.id), max: 0, sum: 0, kids: [] }));
  /* a heading owns the items under it and an item with its own id (IPhO 2023 T2 lists A.1's final answer as item A.1 beside
     its steps A.1.1…; counted outside the heading, that paper came out at 16.6 of 10) */
  const owner = (t, self = false) => list.filter(p => startsWith(t, p.t) || (self && same(t, p.t))).sort((a, b) => b.t.length - a.t.length)[0] || null;
  for (const p of list) { p.parent = owner(p.t); if (p.parent) p.parent.kids.push(p); }
  let loose = 0;
  for (const it of items || []) { const v = +value(it) || 0, p = owner(tokens(it.id), true); if (p) { p.sum += v; p.max += +it.points || 0; } else loose += v; }
  /* Headings that hold every item and add up to the printed total (or stand for it where none was read) are the paper's
     own outline and always cap: IPhO 2023 T1 prints A 1.6, B 1.8, C 2.7, D 2.4, E 1.5 = 10, but its scheme listed E's
     partial-credit breakdown as items (4.2) and the paper came out at 12.7. Otherwise a heading far below its own items
     (under half) is taken for a misread id, not a cap, and ignored. */
  const tops = list.filter(p => !p.parent), topSum = tops.reduce((a, p) => a + p.points, 0);
  const trusted = tops.length > 0 && (items || []).every(it => owner(tokens(it.id), true)) && (!(+total > 0) || Math.abs(topSum - +total) <= .02 * +total);
  const full = p => p.max + p.kids.reduce((a, k) => a + full(k), 0);
  const capped = p => { const sum = p.sum + p.kids.reduce((a, k) => a + capped(k), 0); return trusted || p.points >= .5 * full(p) ? Math.min(p.points, sum) : sum; };
  const sum = loose + list.filter(p => !p.parent).reduce((a, p) => a + capped(p), 0);
  return +Math.min(+total > 0 ? +total : Infinity, sum).toFixed(2);
}

/* the paper's points: its items, bounded by the printed headings and total */
/* the paper's points: its items bounded by the printed headings and total; a printed total is the paper's maximum even
   when the scheme missed an item under it (IPhO 2025 T3 came out at 9.9 when one 0.1-pt item was not listed) */
export const schemeTotal = scheme => +scheme.total > 0 ? +(+scheme.total).toFixed(2) : cappedSum(oneMethod(scheme.items).kept, scheme.parts, null);

/* Alternative methods for one question (Method 1 / Method 2, as EuPhO and IPhO solutions give them) are alternatives:
   a candidate who writes several earns the marks of one, the one worth most, never their sum. Items carry
   alt «<part>/<method>»; for each part with more than one method, only the best method's items are kept (by value:
   the marks earned, or the points when the paper's maximum is reckoned; a tie keeps the lower method number). */
const ALT = /^(.+)\/(\d+)$/;
export function oneMethod(items, value = i => i.points) {
  const parts = new Map();
  for (const it of items || []) {
    const m = ALT.exec(String(it.alt || "")); if (!m) continue;
    const g = parts.get(m[1]) || new Map(); g.set(+m[2], (g.get(+m[2]) || 0) + (+value(it) || 0)); parts.set(m[1], g);
  }
  const best = new Map();
  for (const [part, g] of parts) if (g.size > 1) best.set(part, [...g].sort((a, b) => b[1] - a[1] || a[0] - b[0])[0][0]);
  const dropped = new Set();
  for (const it of items || []) { const m = ALT.exec(String(it.alt || "")); if (m && best.has(m[1]) && best.get(m[1]) !== +m[2]) dropped.add(it.id); }
  return { kept: (items || []).filter(it => !dropped.has(it.id)), dropped };
}

/* R1: whether a task's answer sheets give an answer to an item's question (its first two id parts: A.2 for A.2.3,
   A.2.b or A2.1), as the page reader indexed them. Where they do not (an empty box, no answer sheet at all), a final
   answer marked on a working sheet counts in its place. */
export function answeredOnSheet(id, pages) {
  const q = tokens(id).slice(0, 2);
  if (!q.length) return false;
  for (const p of pages || []) {
    if (p.kind !== "answer" || !p.read) continue;
    let read; try { read = typeof p.read === "string" ? JSON.parse(p.read) : p.read; } catch { continue; }
    for (const i of read?.items || []) {
      if (!i || i.crossed_out) continue;
      const l = tokens(i.label);
      if (l.length >= q.length && q.every((t, k) => t === l[k]) && (String(i.text || "").trim() || i.value != null)) return true;
    }
  }
  return false;
}

/* Every number written in a transcribed answer, scientific notation included: «5.31 \\cdot 10^{-11} m», «2.2 × 10^9»,
   «1.0 * 10^-10», «3e8», «−4.5». A value the grader reports must be one of the numbers on its page; the reader's own
   value field sometimes keeps only the mantissa (IPhO 2025 T1 A.2.3 read «5.31» for 5.31·10⁻¹¹ m, so a correct answer
   scored 0 under R9). */
export function numbersIn(text) {
  const t = String(text || "").replace(/\\(?:cdot|times)|[×·⋅*]/g, " x ").replace(/[−–]/g, "-").replace(/\{\s*(-?\d+)\s*\}/g, "$1");
  const out = [], re = /(-?\d+(?:[.,]\d+)?)(?:\s*x\s*10\s*\^\s*(-?\d+)|\s*[eE](-?\d+))?/g;
  for (let m; (m = re.exec(t));) {
    const base = +m[1].replace(",", "."), exp = m[2] ?? m[3];
    if (Number.isFinite(base)) out.push(exp != null ? base * 10 ** +exp : base);   // never the mantissa alone: 1.04·10⁻⁹ is not 1.04
  }
  // a simple fraction written as an answer is also its value: W*/W_pr* = 1/2 is 0.5 (\frac{1}{2}, 1/2, 3 / 4)
  const frac = /\\[dt]?frac\s*\{\s*(-?\d+)\s*\}\s*\{\s*(\d+)\s*\}|(?<![\d.])(-?\d+)\s*\/\s*(\d+)(?![\d.])/g;
  for (let m; (m = frac.exec(String(text || "")));) { const a = +(m[1] ?? m[3]), b = +(m[2] ?? m[4]); if (b) out.push(a / b); }
  return out;
}
export const sameNumber = (a, b) => Math.abs(a - b) <= Math.max(1e-12, 1e-6 * Math.max(Math.abs(a), Math.abs(b)));
/* the same number with a unit prefix moved (0.415 mm reported as 0.000415 m): a grader that converts a value it should
   have copied still points at a number on the page, never at a new one */
export const samePrefixed = (a, b) => [0, 2, 3, 6, 9, -2, -3, -6, -9].some(k => sameNumber(a * 10 ** k, b));

/* LaTeX the model put into its JSON without doubling the backslash comes back with JSON escapes turned into control
   characters: «\frac» as a form feed + «rac», «\beta» as a backspace + «eta», «\theta» / «\times» / «\text» as a tab,
   «\rho» / «\right» as a carriage return, «\nabla» as a newline (seen in IPhO 2025 T1: «Η = \x0crac{R}{G}»). Form
   feeds and backspaces never belong in a transcript; a tab or carriage return directly before letters is a command. */
export function restoreLatex(text) {
  return typeof text !== "string" ? text : text.replace(/\f/g, "\\f").replace(/\x08/g, "\\b")
    .replace(/\t(?=[a-zA-Z])/g, "\\t").replace(/\r(?=[a-zA-Z])/g, "\\r").replace(/\n(?=abla\b)/g, "\\n");
}

/* R13: a step of the working earns its marks only where it is written. The grader quotes it; the quote must be found
   on the page it cites (its transcript), allowing for how differently a formula can be typed: both are reduced to
   letters, digits and Hangul, and at least 75 % of the quote's character pairs must occur on the page. Gemini had given
   every step of IPhO 2025 T2 C.1–C.5 its marks from final answers alone. */
/* a grader quotes in LaTeX (\\Omega, \\sqrt{2\\pi}, a^{2}) what the transcript holds in Unicode (Ω, √(2π), a²) or the other way
   round: both go to one spelling first. Without this the steps of 13 items of IPhO 2024 T3 and 18 of IPhO 2018, plainly
   written, were zeroed. */
const GREEK = { alpha: "α", beta: "β", gamma: "γ", delta: "δ", epsilon: "ε", varepsilon: "ε", zeta: "ζ", eta: "η", theta: "θ", vartheta: "θ",
  iota: "ι", kappa: "κ", lambda: "λ", mu: "μ", nu: "ν", xi: "ξ", pi: "π", varpi: "π", rho: "ρ", varrho: "ρ", sigma: "σ", varsigma: "σ", tau: "τ",
  upsilon: "υ", phi: "φ", varphi: "φ", chi: "χ", psi: "ψ", omega: "ω", hbar: "ħ", ell: "l", infty: "∞", partial: "∂", nabla: "∇" };
const SCRIPT = { "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9", "⁻": "", "⁺": "",
  "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4", "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9", "µ": "μ", "ϵ": "ε", "ϑ": "θ", "ϕ": "φ", "ℓ": "l" };
const flat = t => String(t || "").normalize("NFKC").replace(/\\([A-Za-z]+)/g, (m, w) => GREEK[w.toLowerCase()] ?? (/^(mathrm|text|textrm|mathbf|mathit|operatorname|left|right|cdot|times|frac|dfrac|tfrac|sqrt|quad|qquad|displaystyle)$/.test(w) ? "" : w))
  .replace(/[⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺₀₁₂₃₄₅₆₇₈₉µϵϑϕℓ]/g, c => SCRIPT[c]).toLowerCase().replace(/[^a-z0-9\u3131-\uD79D\u0370-\u03FF\u0127\u2202\u2207\u221E]/g, "");
export function quoteOnPage(quote, page) {
  const q = flat(quote), p = flat(page);
  if (q.length < 3) return false;
  if (p.includes(q)) return true;
  const pairs = new Set(); for (let i = 0; i < p.length - 1; i++) pairs.add(p.slice(i, i + 2));
  let hit = 0; for (let i = 0; i < q.length - 1; i++) if (pairs.has(q.slice(i, i + 2))) hit++;
  return hit / (q.length - 1) >= .75;
}

/* R12 in code, where the scheme gives the official value but prints no interval: the candidate's value (converted into
   the item's unit by the grader) is right within ±1 in the official value's last printed digit or 2 %, whichever is
   wider; «nearest power of ten» items compare orders of magnitude. The models got these sums wrong in both directions
   (IPhO 2025 T1: −13.5 eV marked wrong against −13.6 eV, 6.1×10¹⁰ M☉ wrong against «nearest power of ten» 10¹¹). */
export function refTolerance(ref) {
  const text = String(ref ?? "").trim().replace(/[−–]/g, "-").replace(/\s+/g, "");
  const m = text.match(/^(-?)(\d*)(?:\.(\d+))?(?:[eE]([+-]?\d+))?$/);
  if (!m || !(m[2] || m[3])) return null;
  const value = +text, decimals = (m[3] || "").length, exp = +(m[4] || 0);
  if (!Number.isFinite(value)) return null;
  return { value, tol: Math.max(.02 * Math.abs(value), 10 ** (exp - decimals)) };
}
export function valueMatches(item, v) {
  if (!Number.isFinite(v)) return false;
  const r = refTolerance(item.ref);
  if (!r) return false;
  if (item.tol === "order") return r.value !== 0 && v !== 0 && Math.sign(v) === Math.sign(r.value) && Math.round(Math.log10(Math.abs(v))) === Math.round(Math.log10(Math.abs(r.value)));
  return Math.abs(v - r.value) <= r.tol * (1 + 1e-9);
}

/* ── automatic scheme review (LAB_SCHEME_CHECK): a scheme is built once per paper and marks every candidate, so a fault
   in it is a misgrade for all of them (bench 2026-11-02: 3 of 4 item misgrades came back identically on a second
   grading). Code fixes what code can see; a review call against the official solution proposes the rest, and code
   applies only what keeps ids and points as they are. */
const IMPLIED = /(given|awarded|credited|full (?:marks|points))[^.;]{0,80}\bif\b[^.;]{0,120}\b(appears|is stated|is written|is obtained|is given)[^.;]{0,80}even if[^.;]{0,60}(intermediate|not (?:fully|explicitly))/i;
/** code checks: a full-mark window of one point is widened to the official value's printed tolerance, and an item whose
    own text gives its marks for a correct result even without the steps makes its part «final answer earns the part» */
export function checkSchemeCode(scheme) {
  const items = scheme?.items || [], parts = cleanParts(scheme?.parts), applied = [];
  for (const it of items) {
    if (it.type === "value" && it.full_min != null && it.full_max != null && +it.full_min === +it.full_max) {
      const v = +it.full_min, t = refTolerance(it.ref ?? String(v)) || { tol: .02 * Math.abs(v) };
      if (Number.isFinite(v) && t.tol > 0) { it.full_min = v - t.tol; it.full_max = v + t.tol; applied.push({ id: it.id, fix: "window" }); }
    }
    if (IMPLIED.test(String(it.what || ""))) {
      const t = tokens(it.id);
      const own = parts.filter(p => { const pt = tokens(p.id); return pt.length < t.length && pt.every((x, k) => x === t[k]); }).sort((a, b) => tokens(b.id).length - tokens(a.id).length)[0];
      if (own && !own.final_full) { own.final_full = true; it.role = "result"; applied.push({ id: it.id, fix: "final_full", part: own.id }); }
    }
  }
  return { scheme: { ...scheme, items, parts }, applied };
}
const ALT_ID = /^[A-Za-z0-9.]{1,20}\/\d{1,2}$/;
/** the review call's corrections, applied by code: ids and points never change; a field is set only to a valid value;
    an item is dropped only where its part's items add up to more than the part's printed points and dropping it does
    not take them below (a step the scheme lists twice, inside its own result and on its own) */
export function applySchemeReview(scheme, review) {
  const items = (scheme?.items || []).map(it => ({ ...it })), parts = cleanParts(scheme?.parts), byId = new Map(items.map(it => [String(it.id), it])), applied = [];
  const num = x => x != null && x !== "" && Number.isFinite(+x) ? +x : null;
  for (const f of Array.isArray(review?.fixes) ? review.fixes.slice(0, 80) : []) {
    const it = byId.get(String(f?.id)); if (!it) continue;
    const done = [];
    const lo = num(f.full_min), hi = num(f.full_max);
    if (it.type === "value" && lo != null && hi != null && lo !== hi) { it.full_min = Math.min(lo, hi); it.full_max = Math.max(lo, hi); done.push("window"); }
    if (typeof f.ref === "string" && refTolerance(f.ref)) { it.ref = f.ref.trim(); done.push("ref"); }
    if (["interval", "order", "digits"].includes(f.tol)) { it.tol = f.tol; done.push("tol"); }
    if (typeof f.unit === "string" && f.unit.trim().length <= 30) { it.unit = f.unit.trim(); done.push("unit"); }
    if (typeof f.alt === "string" && ALT_ID.test(f.alt.trim())) { it.alt = f.alt.trim(); done.push("alt"); }
    if (f.alt === "") { delete it.alt; done.push("alt-"); }
    if (["result", "step"].includes(f.role)) { it.role = f.role; done.push("role"); }
    if (typeof f.add_rule === "string" && f.add_rule.trim() && !String(it.what || "").includes(f.add_rule.trim())) { it.what = `${it.what || ""} [Scheme rule: ${f.add_rule.trim().slice(0, 400)}]`.slice(0, 4000); done.push("rule"); }
    if (done.length) applied.push({ id: it.id, fix: done.join(",") });
  }
  const owner = id => { const t = tokens(id); return parts.filter(p => { const pt = tokens(p.id); return pt.length < t.length && pt.every((x, k) => x === t[k]); }).sort((a, b) => tokens(b.id).length - tokens(a.id).length)[0] || null; };
  let kept = items;
  for (const d of Array.isArray(review?.drop) ? review.drop.slice(0, 20) : []) {
    const it = kept.find(x => String(x.id) === String(d?.id)); if (!it) continue;
    const p = owner(it.id); if (!p) continue;
    const sum = oneMethod(kept.filter(x => owner(x.id) === p)).kept.reduce((a, x) => a + (+x.points || 0), 0);
    if (sum - it.points >= p.points - 1e-9) { kept = kept.filter(x => x !== it); applied.push({ id: it.id, fix: "drop" }); }
  }
  for (const id of Array.isArray(review?.final_full) ? review.final_full.slice(0, 40) : []) {
    const p = parts.find(x => tokens(x.id).join(".") === tokens(id).join("."));
    if (p && !p.final_full) { p.final_full = true; applied.push({ id: p.id, fix: "final_full" }); }
  }
  return { scheme: { ...scheme, items: kept, parts }, applied };
}
