// node --test community/test-unit-check.mjs
import assert from "node:assert/strict";
import test from "node:test";
import { parseUnit, compareUnits } from "./src/unit-check.js";

test("equivalent units are the same unit; the factor converts a written value into the official unit", () => {
  assert.deepEqual(compareUnits("J·T^-1", "A·m^2"), { same: true, factor: 1 }, "32 T1 F.1.b: A·m² is J/T");
  assert.deepEqual(compareUnits("J T^{-1}", "A m²"), { same: true, factor: 1 });
  assert.equal(compareUnits("m/s", "km/s").factor, 1000);
  assert.equal(compareUnits("m", "μm").factor, 1e-6);
  assert.ok(Math.abs(compareUnits("\\mathrm{m\\,s^{-1}}", "km/h").factor - 1 / 3.6) < 1e-12);
  assert.equal(compareUnits("Pa", "N/m^2").factor, 1);
  assert.equal(compareUnits("J/(mol K)", "J mol^-1 K^-1").factor, 1);
  assert.ok(Math.abs(compareUnits("J", "eV").factor - 1.602176634e-19) < 1e-30);
  assert.equal(compareUnits("m^-3", "m⁻³").factor, 1);
});
test("different dimensions are a wrong unit; what cannot be read is left to the grader", () => {
  assert.deepEqual(compareUnits("m^-3", "m"), { same: false, factor: null });
  assert.equal(compareUnits("K", "°C"), null, "an affine scale is not converted");
  assert.equal(compareUnits("m", ""), null);
  assert.equal(compareUnits("m", "2 m"), null, "a number is not a unit");
  assert.equal(parseUnit("furlong"), null);
  assert.equal(parseUnit("constructor"), null);
});
