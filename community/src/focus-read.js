// Focused re-read: a numerical answer the code is about to mark wrong (R12) is read once more by a second reader. A page
// transcript misses a digit or a power of ten (IPhO 2021 T3 audit: n_c read 10^12 for 10^18, n read 25 for 85, each
// zeroing the item). DeepSeek asked again for that value alone, with zoomed strips, shown its first reading or not,
// read the same characters every time (13 of 13 on the bench), so the second reader is Mathpix, an independent
// math-OCR engine, called only on a page with such a value. Its reading replaces the first only when it is one
// character away from it (a misread digit or exponent), never a different number, and the official value plays no
// part in the choice.
import { numbersIn } from './lab-scheme-items.js';

/* a number as its significant digits and power of ten: 1.59e18 -> "159e18", 85 -> "850e1" */
const sig = x => { const [m, e] = Math.abs(x).toExponential(2).split('e'); return (x < 0 ? '-' : '') + m.replace('.', '') + 'e' + Number(e); };
function editDistance(a, b) {
  const d = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array(b.length).fill(0)]);
  for (let j = 1; j <= b.length; j++) d[0][j] = j;
  for (let i = 1; i <= a.length; i++) for (let j = 1; j <= b.length; j++)
    d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
  return d[a.length][b.length];
}
/** one misread character apart: a digit (8 for 2), an exponent's digit (10^12 for 10^18) or a sign; not the same number.
    The same digits at another power of ten only between two powers of ten written out (both at least 10^3 or 10^-3
    in size): on the bench every other such change was a number Mathpix split or ran together (6.23 from 6.23·10^7,
    53295 from 5.3295, 12 from 120), never a misread */
export function misreadOf(first, again) {
  if (!Number.isFinite(first) || !Number.isFinite(again) || first === again || first === 0 || again === 0) return false;
  const a = sig(first), b = sig(again);
  if (editDistance(a, b) !== 1) return false;
  const [ma, ea] = a.split('e'), [mb, eb] = b.split('e');
  return ma !== mb || Math.abs(+ea) >= 3 && Math.abs(+eb) >= 3;
}

/** as many significant digits written in both (3.3 and 3.8, 1.04e-4 and 1.84e-4): a zoomed crop that cut a digit off
    (3.3 read again as 3) is not a misread fixed */
export function sameDigitCount(a, b) {
  const digits = x => Math.abs(x).toExponential(11).split('e')[0].replace('.', '').replace(/0+$/, '');   // 1.59e13 -> 159
  return Number.isFinite(a) && Number.isFinite(b) && digits(a).length === digits(b).length;
}
/* ⁹ -> ^9, so 3,11·10⁹ is one number */
const SUP = '⁰¹²³⁴⁵⁶⁷⁸⁹';
const plainDigits = text => String(text || '').replace(/⁻?[⁰¹²³⁴⁵⁶⁷⁸⁹]+/g, m => '^' + (m[0] === '⁻' ? '-' : '') + [...m.replace('⁻', '')].map(c => SUP.indexOf(c)).join(''));
const sameValue = (a, b) => Math.abs(a - b) <= 1e-9 * Math.max(Math.abs(a), Math.abs(b));

/** the values Mathpix reads on the page that replace a misread one: for each disputed {id, value}, the single number on
    Mathpix's page one character off the first reading and absent from the first transcript (a number the transcript
    already has differs by a unit, not by a misread: 3.11 GPa written 3,11·10⁹ Pa) */
export function mathpixRereads(disputed, mathpixText, transcript) {
  return disputed.flatMap(d => {
    let { fits } = focusCandidates(d.value, mathpixText, transcript);
    /* more than one: the one written under the item's own label (D.5: 23 elsewhere on the page, 85 under «D. 5») */
    if (fits.length > 1) { const own = labelSection(mathpixText, d.id); if (own) fits = focusCandidates(d.value, own, transcript).fits; }
    return fits.length === 1 ? [{ id: d.id, value: fits[0], written: `Mathpix: ${fits[0]}` }] : []; });
}
/** the text from an item's label (D.5, written «D. 5» or «D.5») to the next label of that form, or null */
export function labelSection(text, id) {
  const parts = String(id || '').match(/^([A-Za-z]{1,2})\.?\s*(\d+)$/);
  if (!parts) return null;
  const start = new RegExp(`(^|[^A-Za-z0-9])${parts[1]}\\.\\s*${parts[2]}(?![0-9.])`).exec(text);
  if (!start) return null;
  const from = start.index + start[0].length, next = /(^|[^A-Za-z0-9])[A-Za-z]{1,2}\.\s*\d+(?![0-9.])/.exec(text.slice(from));
  return text.slice(from, next ? from + next.index : undefined);
}
/** Mathpix's numbers one character off a reading: fits (absent from the transcript) and in_transcript (left out) */
export function focusCandidates(value, mathpixText, transcript) {
  const seen = numbersIn(plainDigits(transcript)), near = [];
  for (const n of numbersIn(plainDigits(mathpixText))) if (misreadOf(value, n) && !near.some(x => sameValue(x, n))) near.push(n);
  return { fits: near.filter(n => !seen.some(x => sameValue(x, n))), in_transcript: near.filter(n => seen.some(x => sameValue(x, n))) };
}
