// Tools the grader calls while it grades (function calling, OpenAI format, which DeepSeek speaks): it asks the code
// what code does better than a language model, instead of guessing. Each tool reads only the paper's marking scheme
// and the candidate's transcribed pages handed in `ctx`; none reaches the network, the database or a secret, and every
// answer is short text for the model. The model still gives the marks; a tool answer is evidence, not a verdict.
import { compareExpr, describeCheck } from './expr-check.js';
import { refTolerance, valueMatches, quoteOnPage } from './lab-scheme-items.js';

export const GRADE_TOOLS = [
  { type: 'function', function: { name: 'compare_expressions',
    description: "Compare the candidate's final expression for a scheme item with the official one by evaluating both at random values of their variables. Use it before marking any formula answer, above all one that looks right or looks wrong only by a factor, sign, exponent or variable.",
    parameters: { type: 'object', properties: {
      item_id: { type: 'string', description: 'the scheme item id' },
      candidate: { type: 'string', description: "the candidate's right-hand side exactly as written, in plain ASCII math (sqrt, exp, ln, ^, *, /), Greek letters spelled out, the official variable names where the meaning is the same" } },
    required: ['item_id', 'candidate'] } } },
  { type: 'function', function: { name: 'check_value',
    description: "Check the candidate's number for a numerical scheme item against the official value and tolerance (interval, nearest power of ten, or the last printed digit / 2 %). Give the value converted into the item's unit.",
    parameters: { type: 'object', properties: {
      item_id: { type: 'string' }, value: { type: 'number', description: "the candidate's value in the item's unit" } },
    required: ['item_id', 'value'] } } },
  { type: 'function', function: { name: 'find_on_pages',
    description: "Look for a line, expression or number in the candidate's transcribed pages before deciding that something is or is not written. Returns the pages where it appears, with the surrounding line.",
    parameters: { type: 'object', properties: { text: { type: 'string', description: 'the line, expression or number to look for' } }, required: ['text'] } } },
];

const line = (text, at, width = 160) => text.slice(Math.max(0, text.lastIndexOf('\n', at) + 1), Math.min(text.length, (text.indexOf('\n', at) + 1 || text.length + 1) - 1)).slice(0, width);

/** the answer to one tool call, as short text; ctx = { scheme, pages:[{no, kind, ocr, text}] } */
export function runGradeTool(name, args, ctx) {
  const items = new Map((ctx?.scheme?.items || []).map(it => [String(it.id), it]));
  if (name === 'compare_expressions') {
    const it = items.get(String(args?.item_id ?? ''));
    if (!it) return 'no such item';
    if (!it.expr) return 'this item has no official expression to compare with';
    const c = compareExpr(it.expr, String(args?.candidate ?? ''));
    return c ? describeCheck(c) : 'no verdict: the expressions could not both be evaluated (notation, a misreading or an undefined function); judge from the page';
  }
  if (name === 'check_value') {
    const it = items.get(String(args?.item_id ?? '')), v = Number(args?.value);
    if (!it) return 'no such item';
    if (!Number.isFinite(v)) return 'not a number';
    if (Number.isFinite(+it.full_min) && Number.isFinite(+it.full_max) && +it.full_max > +it.full_min) {
      const inside = v >= +it.full_min && v <= +it.full_max;
      const part = (it.partial || []).find(p => v >= +p.min && v <= +p.max);
      return inside ? `within the full-mark interval [${it.full_min}, ${it.full_max}]` : part ? `outside the full-mark interval [${it.full_min}, ${it.full_max}], inside a partial interval [${part.min}, ${part.max}] worth ${part.points}` : `outside the full-mark interval [${it.full_min}, ${it.full_max}] and every partial interval`;
    }
    const r = refTolerance(it.ref);
    if (!r) return 'this item has no official value to compare with';
    return valueMatches(it, v) ? `matches the official value ${it.ref} within tolerance` : `does not match the official value ${it.ref} (tolerance ${it.tol === 'order' ? 'nearest power of ten' : '±' + +r.tol.toPrecision(3)})`;
  }
  if (name === 'find_on_pages') {
    const needle = String(args?.text ?? '').trim();
    if (needle.length < 2) return 'nothing to look for';
    const hits = [];
    for (const p of ctx?.pages || []) {
      const text = String(p.ocr ?? p.text ?? '');
      if (!text) continue;
      const at = text.indexOf(needle);
      if (at >= 0) hits.push(`p${p.no} (${p.kind}): ${line(text, at)}`);
      else if (quoteOnPage(needle, text)) hits.push(`p${p.no} (${p.kind}): found in another notation`);
      if (hits.length >= 4) break;
    }
    return hits.length ? hits.join('\n') : 'not found in any transcript (the transcript may have missed it: check the photo before deciding it is not written)';
  }
  return 'unknown tool';
}
