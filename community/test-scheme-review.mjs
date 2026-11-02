// node --test community/test-scheme-review.mjs
// The automatic scheme review: what code fixes by itself, and which of a review call's corrections code applies.
import assert from "node:assert/strict";
import test from "node:test";
import { checkSchemeCode, applySchemeReview } from "./src/lab-scheme-items.js";

test("code widens a one-point window to the printed tolerance and makes an implied-step part «final answer earns the part»", () => {
  const { scheme, applied } = checkSchemeCode({ items: [
    { id: "A.1", points: 0.3, type: "value", full_min: 4.5, full_max: 4.5, ref: "4.5" },
    { id: "A.2.4", points: 0.7, type: "derivation", role: "step", what: "A = 2*a_S/a_C. 0.7 pt is given if the correct expression for A appears even if the intermediate steps are not fully written." },
    { id: "A.2.1", points: 0.1, type: "derivation", role: "step", what: "d(B/A)/dA = 0" }],
    parts: [{ id: "A.2", points: 1.0 }, { id: "A", points: 2 }] });
  const a1 = scheme.items.find(i => i.id === "A.1");
  assert.ok(a1.full_min < 4.5 && a1.full_max > 4.5, "a one-point window is widened");
  assert.equal(scheme.parts.find(p => p.id === "A.2").final_full, true, "the deepest part holding the item");
  assert.equal(scheme.items.find(i => i.id === "A.2.4").role, "result");
  assert.deepEqual(applied.map(a => a.fix), ["window", "final_full"]);
});

test("review fixes keep ids and points, take only valid values, and drop only a duplicate its part can spare", () => {
  const base = { items: [
    { id: "B.1", points: 0.5, type: "value", what: "v" },
    { id: "B.2.1", points: 0.4, type: "derivation", role: "step", what: "x" },
    { id: "B.2.2", points: 0.4, type: "derivation", role: "step", what: "y" },
    { id: "B.2.3", points: 0.4, type: "derivation", role: "result", what: "z" },
    { id: "C.1", points: 1, type: "derivation", what: "c" }],
    parts: [{ id: "B.2", points: 0.8 }, { id: "C", points: 1 }] };
  const { scheme, applied } = applySchemeReview(base, {
    fixes: [{ id: "B.1", full_min: 2, full_max: 1.5, unit: "m/s", reason: "printed ±" }, { id: "B.1", full_min: 3, full_max: 3 },
      { id: "B.2.1", alt: "B.2/1", role: "step", add_rule: "0.2 if the sign is wrong" }, { id: "nope", role: "result" }, { id: "C.1", alt: "bad alt id!" }, { id: "C.1", points: 9 }],
    drop: [{ id: "B.2.1" }, { id: "B.2.2" }, { id: "C.1" }], final_full: ["B.2", "Z.9"] });
  const by = id => scheme.items.find(i => i.id === id);
  assert.deepEqual([by("B.1").full_min, by("B.1").full_max, by("B.1").unit], [1.5, 2, "m/s"]);
  assert.equal(by("B.2.1")?.alt, undefined, "dropped: B.2 lists 1.2 against its printed 0.8");
  assert.equal(by("B.2.2").what, "y", "the second drop would take B.2 below 0.8 and is refused");
  assert.ok(by("C.1") && by("C.1").points === 1 && !by("C.1").alt, "points never change; an invalid alt is ignored; C cannot spare C.1");
  assert.equal(scheme.parts.find(p => p.id === "B.2").final_full, true);
  assert.deepEqual(applied.map(a => a.id + ":" + a.fix), ["B.1:window,unit", "B.2.1:alt,role,rule", "B.2.1:drop", "B.2:final_full"]);
});
