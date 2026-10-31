/* The items of a marking scheme as the model listed them, made safe to add up.
   A scheme read from a PDF sometimes repeats one part's id on each of its rows (IPhO 2017 E1: A1 once per concentration)
   and puts the part's total on every row, so the paper's points came out three times too high (33.2 instead of 10).
   Rows sharing an id and the same points are that case: they become one item worth those points once, with every row's
   requirement. Rows sharing an id with different points are separate marks: each keeps its points under its own id. */
const NUMERIC = ["full_min", "full_max", "partial", "checks", "unit", "n_min", "n_class"];

export function tidySchemeItems(raw) {
  const rows = (Array.isArray(raw) ? raw : []).filter(i => i && i.id != null && String(i.id).trim() && +i.points > 0)
    .map(i => ({ ...i, id: String(i.id).trim().slice(0, 20), points: +i.points }));
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
