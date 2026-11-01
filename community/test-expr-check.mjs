// node --test community/test-expr-check.mjs
// Final expressions compared by evaluation at random points (audit cases of 2026-11-01), with a closed parser.
import assert from "node:assert/strict";
import test from "node:test";
import { compareExpr, parseExpr, describeCheck } from "./src/expr-check.js";

test("the audit's over-credited results are told apart from the official ones", () => {
  assert.deepEqual(compareExpr("2*g*L*h^2*(rho_1-rho_0)^2/(k^2*rho_1)", "2*rho_1*g*h^2/k^2*(1-rho_0/rho_1)^2"), { verdict: "differs", missing: ["L"], extra: [] }, "IPhO 2021 T1 A.4: no L");
  assert.equal(compareExpr("G*M_2^3/(M_1+M_2)^2", "M_2^3/(M_1+M_2)^2").missing[0], "G", "IPhO 2018 T1 A.1: no G");
  assert.equal(compareExpr("v_1*sin(theta_1)/sin(theta_2)", "v_1*sin(theta_2)/sin(theta_1)").verdict, "differs", "an inverted relation");
  assert.deepEqual(compareExpr("(1/2)*rho*g*(z_b^2-z_a^2)", "(1/2)*rho*g*(z_a^2-z_b^2)"), { verdict: "factor", ratio: -1, missing: [], extra: [] }, "a wrong sign");
});
test("an equivalent form is equal, however it is written", () => {
  assert.equal(compareExpr("2*g*L*h^2*(rho_1-rho_0)^2/(k^2*rho_1)", "2 L g h^2 (rho_1-rho_0)^2/(k^2 rho_1)").verdict, "equal");
  assert.equal(compareExpr("A = 2*a_S/a_C", "2a_S/a_C").verdict, "equal", "the left-hand side is dropped, implicit products read");
  assert.equal(compareExpr("c*sqrt(1-(e*V/(m_p*c^2))^2)", "c√(1 − e²V²/(m_p²c⁴))").verdict, "equal", "Unicode roots, minus signs and superscripts");
  assert.equal(compareExpr("x^(-1)", "x⁻¹").verdict, "equal");
  assert.equal(compareExpr("omega*sqrt(L*C)", "ω √(L C)").verdict, "equal", "Greek letters spelled out");
});
test("anything outside the grammar is not judged", () => {
  assert.equal(parseExpr('import("fs")'), null);
  assert.equal(parseExpr("constructor.constructor('x')()"), null);
  assert.equal(compareExpr("x", "x +"), null, "an unfinished expression");
  assert.equal(compareExpr("sqrt(-1-x^2)", "sqrt(-1-x^2)"), null, "no real value anywhere");
  assert.equal(describeCheck(null), null);
  assert.match(describeCheck(compareExpr("G*M^3", "M^3")), /not equivalent.*missing G/);
});
