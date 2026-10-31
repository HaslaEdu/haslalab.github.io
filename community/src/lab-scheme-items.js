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
  if (Array.isArray(out.partial)) out.partial = out.partial.filter(p => p && Number.isFinite(p.min) && Number.isFinite(p.max) && +p.points > 0);
  if (out.role !== "result" && out.role !== "step") delete out.role;                 // R13: what the answer alone earns
  return out;
}

export function tidySchemeItems(raw) {
  const rows = (Array.isArray(raw) ? raw : []).filter(i => i && i.id != null && String(i.id).trim() && +i.points > 0)
    .map(i => intervals({ ...i, id: String(i.id).trim().slice(0, 20), points: +i.points }));
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

export function cleanParts(raw) {
  const seen = new Set();
  return (Array.isArray(raw) ? raw : []).filter(p => p && p.id != null && +p.points > 0 && tokens(p.id).length)
    .map(p => ({ id: String(p.id).trim().slice(0, 20), points: +p.points }))
    .filter(p => { const k = tokens(p.id).join("."); if (seen.has(k)) return false; seen.add(k); return true; });
}

export function cappedSum(items, parts, total, value = i => i.points) {
  const list = cleanParts(parts).map(p => ({ ...p, t: tokens(p.id), max: 0, sum: 0, kids: [] }));
  const owner = t => list.filter(p => startsWith(t, p.t)).sort((a, b) => b.t.length - a.t.length)[0] || null;
  for (const p of list) { p.parent = owner(p.t); if (p.parent) p.parent.kids.push(p); }
  let loose = 0;
  for (const it of items || []) { const v = +value(it) || 0, p = owner(tokens(it.id)); if (p) { p.sum += v; p.max += +it.points || 0; } else loose += v; }
  /* a heading far below its own items (under half) is a misread id, not a cap: it is ignored */
  const full = p => p.max + p.kids.reduce((a, k) => a + full(k), 0);
  const capped = p => { const sum = p.sum + p.kids.reduce((a, k) => a + capped(k), 0); return p.points >= .5 * full(p) ? Math.min(p.points, sum) : sum; };
  const sum = loose + list.filter(p => !p.parent).reduce((a, p) => a + capped(p), 0);
  return +Math.min(+total > 0 ? +total : Infinity, sum).toFixed(2);
}

/* the paper's points: its items, bounded by the printed headings and total */
export const schemeTotal = scheme => cappedSum(scheme.items, scheme.parts, scheme.total);

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
const flat = t => String(t || "").toLowerCase().replace(/\\(?:mathrm|text|left|right|cdot|times|frac|sqrt)\b/g, "").replace(/[^a-z0-9\u3131-\uD79D\u0370-\u03FF]/g, "");
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
