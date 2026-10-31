// node --test community/test-lab-scheme-items.mjs
// A scheme's items add up to the paper's points, and a Korean sitting reads each requirement in Korean.
import assert from "node:assert/strict";
import test from "node:test";
import { tidySchemeItems, schemePoints } from "./src/lab-scheme-items.js";
import { schemeWords, translationPrompt, checkTranslation, localizeItems } from "./src/lab-localize.js";

/* IPhO 2017 E1 as the model listed it on 2026-10-31: one row per concentration, each carrying its part's total */
const ipho2017E1 = [
  ...[23, 28, 33].map(c => ({ id: "A1", points: 1.2, type: "graph", sheet: "answer", what: `Deflectogram of C0 = ${c} g/150 mL (0.4 pts)`, checks: [{ check: "points_min", points: 0.4 }] })),
  ...[23, 28, 33].map(c => ({ id: "A2", points: 1.5, type: "table", sheet: "answer", what: `Table 1 of C0 = ${c} (0.5 pts)` })),
  ...Array.from({ length: 6 }, (_, i) => ({ id: "A3", points: 1.5, type: i % 2 ? "graph" : "table", sheet: "answer", what: `A3 row ${i + 1} (0.25 pts)` })),
  { id: "A4", points: 0.3, type: "value", sheet: "answer", what: "h = (1.5 ± 0.1) cm for each concentration" },
  { id: "B1", points: 0.9, type: "derivation", sheet: "any", what: "Linear form of eq.(3)" },
  ...Array.from({ length: 6 }, (_, i) => ({ id: "B2", points: 1.8, type: i % 2 ? "graph" : "table", sheet: "answer", what: `B2 row ${i + 1} (0.3 pts)` })),
  { id: "B3", points: 1.5, type: "value", sheet: "answer", what: "D for three concentrations" },
  ...[0, 1].map(i => ({ id: "C1", points: 1.3, type: i ? "value" : "graph", sheet: "answer", what: `C1 row ${i + 1}` })),
];

test("rows that repeat one part's total count it once: IPhO 2017 E1 is 10 points, not 33.2", () => {
  assert.equal(schemePoints(ipho2017E1.map(i => ({ points: i.points }))), 33.2, "the stored scheme's sum");
  const items = tidySchemeItems(ipho2017E1);
  assert.equal(schemePoints(items), 10);
  assert.deepEqual(items.map(i => i.id), ["A1", "A2", "A3", "A4", "B1", "B2", "B3", "C1"]);
  const a1 = items[0];
  assert.match(a1.what, /C0 = 23.*C0 = 28.*C0 = 33/, "every row's requirement is kept");
  assert.equal(a1.checks, undefined, "a row's own checks no longer stand for the merged mark");
  assert.equal(new Set(items.map(i => i.id)).size, items.length, "ids are unique, so each grade finds its item");
});

test("rows sharing an id with their own points stay separate marks under their own ids", () => {
  const items = tidySchemeItems([{ id: "C1", points: 0.8, type: "graph", sheet: "answer", what: "plot" }, { id: "C1", points: 0.5, type: "value", sheet: "answer", what: "slope" }, { id: "x", points: 0 }, null]);
  assert.deepEqual(items.map(i => [i.id, i.points]), [["C1", 0.8], ["C1#2", 0.5]]);
  assert.equal(schemePoints(items), 1.3);
  assert.deepEqual(tidySchemeItems([{ id: " A.1 ", points: "0.4", what: "R0" }]).map(i => [i.id, i.points]), [["A.1", 0.4]]);
});

test("a Korean sitting gets each requirement in Korean, in the scheme's order, numbers untouched", () => {
  const scheme = { items: [{ id: "A.1", what: "R0 in [105, 111] ohm" }, { id: "B.1", what: "graph of ln(T) against t" }] };
  const list = schemeWords(scheme), prompt = translationPrompt(list);
  assert.ok(prompt.startsWith("[TASK: translate marking-scheme items]"));
  assert.deepEqual(JSON.parse(prompt.split("\n").at(-1)), list, "the strings are the prompt's last line, as data");
  const words = checkTranslation(["R0가 [105, 111] ohm 범위", "  "], list);
  assert.deepEqual(words, ["R0가 [105, 111] ohm 범위", "graph of ln(T) against t"], "an empty translation keeps the original");
  assert.throws(() => checkTranslation(["하나"], list), /translation_mismatch/);
  const graded = { score: 1, items: [{ id: "A.1", what: list[0], note: "범위 안" }, { id: "B.1", what: list[1] }] };
  const out = localizeItems(graded, scheme, words);
  assert.deepEqual(out.items.map(i => i.what), words); assert.equal(out.items[0].note, "범위 안"); assert.equal(out.score, 1);
  assert.equal(localizeItems(graded, scheme, null), graded, "no translation: the report keeps the original words");
  assert.equal(localizeItems({ items: [graded.items[0]] }, scheme, words).items[0].what, list[0], "a mismatched list is left as graded");
});

/* IPhO 2025 T3 as printed: question headings add up to 10, but the items of C.3 (headed 1.3 pt) add up to 1.4 */
const ipho2025T3 = {
  headings: { "A.1": .2, "A.2": .5, "A.3": 1.2, "A.4": .8, "A.5": .5, "A.6": 1.1, "B.1": 1.1, "B.2": 1.1, "B.3": 1.1, "C.1": .4, "C.2": .7, "C.3": 1.3 },
  extra: [.2, .2, .1, .3, .1, .1, .2, .2],
};
const t3Items = () => [
  ...Object.entries(ipho2025T3.headings).filter(([id]) => id !== "C.3").map(([id, points]) => ({ id: id + ".1", points })),
  ...ipho2025T3.extra.map((points, i) => ({ id: `C.3.${i + 1}`, points })),
];

test("a question counts at most its printed points: IPhO 2025 T3 is 10, not 10.1", async () => {
  const { cappedSum, schemeTotal, cleanParts } = await import("./src/lab-scheme-items.js");
  const items = t3Items(), parts = Object.entries(ipho2025T3.headings).map(([id, points]) => ({ id, points }));
  assert.equal(schemePoints(items), 10.1, "the items as listed");
  assert.equal(schemeTotal({ items, parts }), 10);
  assert.equal(schemeTotal({ items, parts: [], total: 10 }), 10, "a printed total bounds the paper too");
  assert.equal(schemeTotal({ items, parts: [] }), 10.1, "without headings the items stand");
  const all = items.map(i => ({ ...i, got: i.points }));
  assert.equal(cappedSum(all, parts, null, i => i.got), 10, "full marks on every item is the paper's 10, never more");
  const c3 = all.map(i => ({ ...i, got: i.id.startsWith("C.3") ? i.points : 0 }));
  assert.equal(cappedSum(c3, parts, null, i => i.got), 1.3, "C.3's own items earn at most its 1.3");
  assert.equal(cappedSum([{ id: "C4.1", points: .5 }, { id: "C.31", points: .4 }], [{ id: "C.4", points: .3 }, { id: "C.3", points: .1 }]), .7,
    "C.4 holds C4.1 (capped to .3); C.3 does not hold C.31; and a heading under half its items is a misread id, ignored");
  assert.equal(cappedSum([{ id: "A.1.1", points: .3 }, { id: "A.2.1", points: .4 }], [{ id: "A", points: .6 }, { id: "A.1", points: .2 }]), .6, "nested headings: a problem bounds its questions");
  assert.deepEqual(cleanParts([{ id: "C.3", points: 1.3 }, { id: "C3", points: 1 }, { id: "", points: 1 }, { id: "D", points: 0 }]), [{ id: "C.3", points: 1.3 }]);
});

test("a value's interval is kept only with both ends", () => {
  const [a, b] = tidySchemeItems([
    { id: "A.2.2", points: .1, type: "value", sheet: "answer", what: "Fmax", full_min: 14.6, partial: [{ min: 1 }] },
    { id: "A.2.3", points: .1, type: "value", sheet: "answer", what: "h", full_min: 1.9, full_max: 2.1, partial: [{ min: 1.8, max: 2.2, points: .05 }] },
  ]);
  assert.equal(a.full_min, undefined, "a lone lower bound would read as «anything above 14.6»");
  assert.deepEqual(a.partial, []);
  assert.deepEqual([b.full_min, b.full_max, b.partial.length], [1.9, 2.1, 1]);
});

test("each item keeps whether the answer alone earns it (R13): result or step, nothing else", () => {
  const [a, b, c] = tidySchemeItems([
    { id: "A.1.1", points: .1, type: "derivation", sheet: "any", what: "Using Newton's second law", role: "step" },
    { id: "A.1.2", points: .1, type: "derivation", sheet: "answer", what: "Expression of the velocity", role: "result" },
    { id: "A.1.3", points: .1, type: "value", sheet: "answer", what: "v", role: "maybe" },
  ]);
  assert.deepEqual([a.role, b.role, c.role], ["step", "result", undefined]);
});

test("a value is found on its page in scientific notation, not only in the reader's value field (IPhO 2025 T1 A.2.3)", async () => {
  const { numbersIn, sameNumber } = await import("./src/lab-scheme-items.js");
  const has = (text, v) => numbersIn(text).some(x => sameNumber(x, v));
  assert.ok(has(String.raw`숫자 값: r_1 = 5.31 \cdot 10^{-11} m`, 5.31e-11), "LaTeX \\cdot 10^{-11}");
  assert.ok(has("M_b = 2.2 × 10^9 M_☉", 2.2e9));
  assert.ok(has("a_m = 1.0 * 10^-10 m/s^2", 1e-10));
  assert.ok(has("E_1 = −13.5 eV", -13.5), "a typographic minus");
  assert.ok(has("c = 3e8 m/s", 3e8));
  assert.ok(!has(String.raw`r_1 = 5.31 \cdot 10^{-11} m`, 5.31e-10), "a different exponent is a different number");
  assert.ok(!has("W = 20 mJ", 2), "no number is invented");
});

test("LaTeX the reader left unescaped in its JSON is restored, ordinary line breaks are kept", async () => {
  const { restoreLatex } = await import("./src/lab-scheme-items.js");
  const parsed = JSON.parse(String.raw`{"t":"H = \frac{R}{G}, \beta, \theta \times \text{m}, \rho, \nabla\nnext line"}`).t;
  assert.equal(restoreLatex(parsed), String.raw`H = \frac{R}{G}, \beta, \theta \times \text{m}, \rho, \nabla` + "\nnext line");
  assert.equal(restoreLatex("a\tb"), "a\\tb", "a tab before a letter is a command");
  assert.equal(restoreLatex("x =\t2"), "x =\t2", "a tab before a digit stays a tab");
  assert.equal(restoreLatex(null), null);
});

test("R13: a step's quote must be on its page, however the formula was typed", async () => {
  const { quoteOnPage, numbersIn } = await import("./src/lab-scheme-items.js");
  const page = String.raw`C.4 (1pt) F_s^* = \frac{1}{2} A S_L  W^* = \frac{A^2}{2\rho g} S_L  수치값: W^* = 20 mJ`;
  assert.ok(quoteOnPage("W* = A^2/(2 ρ g) S_L", page) || quoteOnPage(String.raw`W^* = \frac{A^2}{2\rho g} S_L`, page), "the same formula typed differently");
  assert.ok(quoteOnPage("수치값: W^* = 20 mJ", page));
  assert.ok(!quoteOnPage("W = 4 F_s X", page), "IPhO 2025 T2 C.4.1: the starting point is not on the answer sheet");
  assert.ok(!quoteOnPage("mass conservation of the fluid in both vessels", page), "a step that was never written");
  assert.ok(!quoteOnPage("", page) && !quoteOnPage(null, page), "no quote, no marks");
  assert.deepEqual(numbersIn(String.raw`K = 1.04 \cdot 10^{-9} m s^{-1}`).filter(x => Math.abs(x - 1.04) < 1e-9), [], "the mantissa alone is not a written number");
});

test("R12 in code: the official value, its last printed digit or 2 %, and nearest powers of ten", async () => {
  const { valueMatches, refTolerance } = await import("./src/lab-scheme-items.js");
  const ok = (ref, v, tol = "default") => valueMatches({ ref, tol }, v);
  assert.ok(ok("-13.6", -13.5), "IPhO 2025 T1 A.3.3: −13.5 eV against −13.6 eV is within the last digit");
  assert.ok(!ok("-13.6", -13.3));
  assert.ok(ok("7.7", 7.6) && !ok("7.7", 7.9) && !ok("7.7", 0.069), "H_c = 6.9 cm is 0.069 m, far from 7.7 m");
  assert.ok(ok("184.3", 184) && !ok("184.3", 194));
  assert.ok(!ok("1.0e-4", 1.04e-9), "an exponent off by five orders is wrong");
  assert.ok(ok("1e11", 6.1e10, "order") && !ok("1e11", 2.2e9, "order"), "IPhO 2025 T1 B.3.11: nearest power of ten");
  assert.deepEqual(refTolerance("2.2e9"), { value: 2.2e9, tol: 1e8 });
  assert.equal(refTolerance("about 7"), null, "no official number, no code check: the grader judges");
});
