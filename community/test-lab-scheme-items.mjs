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
