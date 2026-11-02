import assert from "node:assert/strict";
import test from "node:test";
import { misreadOf, focusPrompt, acceptedRereads } from "./src/focus-read.js";

test("a re-read replaces a reading only one character off: a digit or a power of ten", () => {
  assert.ok(misreadOf(1.59e13, 1.59e18), "IPhO 2021 T3 C.3: 10^13 for 10^18");
  assert.ok(misreadOf(25, 85), "IPhO 2021 T3 D.5: 25 for 85");
  assert.ok(misreadOf(0.31, 0.37));
  assert.ok(!misreadOf(223, 129), "a different number is a different answer, not a misread");
  assert.ok(!misreadOf(648, 648), "the same reading");
  assert.ok(!misreadOf(0, 8));
  assert.ok(!misreadOf(3.3, NaN));
});
test("the question names the items and the first reading, never the official value", () => {
  const p = focusPrompt([{ id: "C.3", unit: "m^-3", first: "15900000000000" }]);
  assert.match(p, /\[TASK: focus read\]/); assert.match(p, /"first_reading":"15900000000000"/);
  assert.match(p, /never compute/);
});
test("only found values one character off are accepted", () => {
  const disputed = [{ id: "C.3", value: 1.59e13 }, { id: "D.5", value: 25 }, { id: "B.2", value: 223 }, { id: "B.4", value: 3.3 }];
  const out = acceptedRereads(disputed, { items: [
    { id: "C.3", found: true, written: "1.59 × 10^{18}", value: 1.59e18 },
    { id: "D.5", found: false, written: "", value: null },
    { id: "B.2", found: true, written: "129 nm", value: 129 },
    { id: "B.4", found: true, written: "3.3 ns", value: 3.3 }] });
  assert.deepEqual(out, [{ id: "C.3", value: 1.59e18, written: "1.59 × 10^{18}" }]);
  assert.deepEqual(acceptedRereads(disputed, null), []);
});
