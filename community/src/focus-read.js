// Focused re-read: a numerical answer the code is about to mark wrong (R12) is read once more from the photo, alone.
// A page transcript reads the whole page at once and misses a digit or a power of ten (IPhO 2021 T3 audit: n_c read
// 10^13 for 10^18, n read 25 for 85, each zeroing the item). Asked for one value at a time, beside zoomed strips, the
// reader looks at those characters only. The official value is never shown, and a re-read is taken only when it is one
// character away from the first reading (a misread digit or exponent), never a different number the model worked out.

export const FOCUS_SCHEMA = { type: 'object', properties: { items: { type: 'array', items: { type: 'object', properties: {
  id: { type: 'string' }, found: { type: 'boolean' }, written: { type: 'string' }, value: { type: ['number', 'null'] }, unit: { type: ['string', 'null'] } },
  required: ['id', 'found', 'written', 'value'] } } }, required: ['items'] };

/* a number as its significant digits and power of ten: 1.59e18 -> "159e18", 85 -> "850e1" */
const sig = x => { const [m, e] = Math.abs(x).toExponential(2).split('e'); return (x < 0 ? '-' : '') + m.replace('.', '') + 'e' + Number(e); };
function editDistance(a, b) {
  const d = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array(b.length).fill(0)]);
  for (let j = 1; j <= b.length; j++) d[0][j] = j;
  for (let i = 1; i <= a.length; i++) for (let j = 1; j <= b.length; j++)
    d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
  return d[a.length][b.length];
}
/** one misread character apart: a digit (8 for 2), a power of ten (13 for 18) or a sign; not the same number */
export function misreadOf(first, again) {
  if (!Number.isFinite(first) || !Number.isFinite(again) || first === again || first === 0 || again === 0) return false;
  return editDistance(sig(first), sig(again)) === 1;
}

/** the question for one page: the items by id and unit only. Shown the first reading, DeepSeek copied it back in all
    13 bench re-reads (10^12 for 10^18 again): the re-read is blind, and never sees the official value either */
export function focusPrompt(items) {
  return ['[TASK: focus read] On this photographed answer page, find the candidate\'s own final answer to each question listed below and transcribe it exactly as written: every digit, the decimal point, the power of ten and its sign, and the unit.',
    'Read the characters, do not work anything out: never compute, correct, round or complete a value. Look closely at look-alike handwriting (0/6/8/9, 1/7, 2/z, 3/8, 4/9, 5/s, the exponent\'s digits). Red ink is a human marker\'s: ignore it. If a value is not written on this page, found is false.',
    'The questions (the label printed beside the answer box, and the unit asked for):',
    JSON.stringify(items.map(i => ({ id: i.id, unit: i.unit || null }))),
    'Return one JSON object: {"items":[{"id":"Q.1","found":true,"written":"2.47 × 10^{-3} s","value":0.00247,"unit":"s"}]}. value is the number as written (in the written unit), null when found is false.'].join('\n');
}

/** the re-read values that replace a misread one: [{id, value, written}] for the items whose new value is one character off */
export function acceptedRereads(disputed, reply) {
  const byId = new Map((Array.isArray(reply?.items) ? reply.items : []).filter(x => x && x.found === true).map(x => [String(x.id), x]));
  return disputed.flatMap(d => {
    const r = byId.get(String(d.id)), v = Number(r?.value);
    return r && misreadOf(d.value, v) ? [{ id: d.id, value: v, written: String(r.written || v).slice(0, 120) }] : [];
  });
}
