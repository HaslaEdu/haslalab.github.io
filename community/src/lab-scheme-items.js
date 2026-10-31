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
