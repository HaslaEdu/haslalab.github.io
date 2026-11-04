import assert from "node:assert/strict";
import test from "node:test";
import { misreadOf, mathpixRereads, labelSection, sameDigitCount, focusCandidates } from "./src/focus-read.js";

test("a re-read replaces a reading only one character off: a digit or a power of ten", () => {
  assert.ok(misreadOf(1.59e12, 1.59e18), "IPhO 2021 T3 C.3: 10^12 for 10^18");
  assert.ok(misreadOf(25, 85), "IPhO 2021 T3 D.5: 25 for 85");
  assert.ok(misreadOf(0.31, 0.37));
  assert.ok(!misreadOf(223, 129), "a different number is a different answer, not a misread");
  assert.ok(!misreadOf(648, 648), "the same reading");
  assert.ok(!misreadOf(0, 8));
  assert.ok(!misreadOf(3.3, NaN));
  // what Mathpix split or ran together on the bench (IPhO 2016 T2, 2015 T1): the same digits at another power of ten
  assert.ok(!misreadOf(6.23e7, 6.23)); assert.ok(!misreadOf(5.3295, 53295)); assert.ok(!misreadOf(120, 12)); assert.ok(!misreadOf(6.1e10, 6.101));
  assert.ok(misreadOf(2.4e-5, 2.4e-6), "an exponent's digit, both written out");
});
test("Mathpix's page gives the one number a character off the first reading, absent from the first transcript", () => {
  // IPhO 2021 T3, session 34: what DeepSeek and Mathpix read on the answer pages
  assert.deepEqual(mathpixRereads([{ id: "C.3", value: 1.59e12 }], "Numerical value: $n_{c} \\approx 1,59 \\cdot 10^{18}$ ... $n_{0} / n_{c} \\approx(.5) \\cdot 10^{7}$", "n_c ≈ 1.59·10^{12}"),
    [{ id: "C.3", value: 1.59e18, written: "Mathpix: 1590000000000000000" }]);
  assert.deepEqual(mathpixRereads([{ id: "D.5", value: 25 }], "D. 5 (1.1 pt) Numerical value: $n \\approx 85$", "D.5 (1.1 pt) n ≈ 25").map(r => r.value), [85]);
  assert.deepEqual(mathpixRereads([{ id: "2.3.b", value: 3.11 }], "3,11·10⁹ pa", "3,11·10⁹ pa"), [], "a unit, not a misread: the transcript has the same number");
  assert.deepEqual(mathpixRereads([{ id: "B.2", value: 223 }], "\\Delta \\lambda \\approx 223 \\mathrm{hm}", "Δλ ≈ 223 nm"), [], "the same reading");
  assert.deepEqual(mathpixRereads([{ id: "X", value: 25 }], "n = 85 and m = 35", "n = 25"), [], "two candidates: no choice");
});
test("two candidates on the page: the one under the item's own label", () => {
  const page = "D. 3 (1.2 pt) $x=\\frac{4 \\pi}{3 k}$ y 23 D. 4 (0.8 pt) $a / \\lambda=\\frac{2}{3}$\nD. 5 (1.1 pt)\nNumerical value: $n \\approx 85$";
  assert.equal(labelSection(page, "D.5"), " (1.1 pt)\nNumerical value: $n \\approx 85$");
  assert.equal(labelSection(page, "D.6"), null);
  assert.deepEqual(mathpixRereads([{ id: "D.5", value: 25 }], page, "D.5 (1.1 pt) n ≈ 25").map(r => r.value), [85], "IPhO 2021 T3: 23 elsewhere, 85 under D. 5");
  assert.deepEqual(mathpixRereads([{ id: "1.1.e", value: 25 }], "n = 85 and m = 35", "n = 25"), [], "no label to go by: no choice");
});

test('a zoomed reading must keep the number of written digits: a crop that cut one off is no fix', () => {
  for (const [a, b] of [[3.3, 3.8], [1.84e-4, 1.04e-4], [2.45e-2, 2.45e2], [54.3, 54.9], [20, 20], [1.59e13, 1.59e18]]) assert.equal(sameDigitCount(a, b), true, `${a} ${b}`);
  for (const [a, b] of [[3.3, 3], [9.31, 0.31], [1.6e-4, 1.65e-4], [5, NaN]]) assert.equal(sameDigitCount(a, b), false, `${a} ${b}`);
});

test("a leading zero read as a nine is one misread character, though it moves the number a power of ten", () => {
  assert.ok(misreadOf(9.23, 0.23) && misreadOf(0.23, 9.23), "0,23 read 9,23 (IPhO 2023 T3 A.1)");
  assert.ok(misreadOf(0.5, 6.5), "a tailed zero read as a six");
  assert.ok(!misreadOf(9.23, 0.24), "two characters apart is another number");
  assert.ok(!misreadOf(1.5, 1.05) && !misreadOf(120, 12) && !misreadOf(5.3295, 53295), "a digit added or dropped is never a misread");
  const { fits } = focusCandidates(9.23, String.raw`v = \frac{6}{10}\sqrt{\frac{\gamma}{\rho a}(1-2^{-1/3})} = 0,23 \mathrm{m/s}`, "v = 9,23 m/s");
  assert.deepEqual(fits, [0.23]);
});
