// node --test community/test-expr-check.mjs
// Final expressions compared by evaluation at random points (audit cases of 2026-11-01), with a closed parser.
import assert from "node:assert/strict";
import test from "node:test";
import { compareExpr, parseExpr, describeCheck, schemeSymbols } from "./src/expr-check.js";

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
test("the candidate's own names for official variables are matched; an unmatched name leaves no verdict", () => {
  assert.equal(compareExpr("sigma*T_s^4*R_sun^2/d_sun^2", "sigma*T^4*R_s^2/d_s^2").verdict, "equal", "IPhO 2015 T1: R_s for R_sun");
  assert.equal(compareExpr("mu*I0/(2*pi*r)", "mu_0*I_0/(2*pi*r)").verdict, "equal");
  assert.equal(compareExpr("p_c*V", "P_c*V").verdict, "equal");
  assert.equal(compareExpr("a*b", "a*b*q"), null, "a name of the candidate's own");
  assert.equal(compareExpr("K*gamma*x", "x"), null, "two official names gone");
});
test("anything outside the grammar is not judged", () => {
  assert.equal(parseExpr('import("fs")'), null);
  assert.equal(parseExpr("constructor.constructor('x')()"), null);
  assert.equal(compareExpr("x", "x +"), null, "an unfinished expression");
  assert.equal(compareExpr("sqrt(-1-x^2)", "sqrt(-1-x^2)"), null, "no real value anywhere");
  assert.equal(describeCheck(null), null);
  assert.match(describeCheck(compareExpr("G*M^3", "M^3")), /not equivalent.*missing G/);
});
test("an extra variable that is one of the paper's own symbols is a real dependence, not another notation", () => {
  // IPhO 2021 T1 (audit, session 34): tau with an extra L, and B.2 with an extra 1/L, both given full marks
  const known = schemeSymbols(["2*g*L*h^2*(rho_1-rho_0)^2/(k^2*rho_1)", "A*c*rho_1*D^2/kappa", "2*E*z_0/(pi*(4*z_0^2+x^2))", "x +"]);
  assert.ok(known.has("L") && known.has("z_0"));
  const b2 = compareExpr("2*E*z_0/(pi*(4*z_0^2+x^2))", "E/(pi*L)*2*z_0/(x^2+4*z_0^2)", { known });
  assert.equal(b2.verdict, "differs"); assert.deepEqual(b2.extra, ["L"]);
  assert.equal(compareExpr("2*E*z_0/(pi*(4*z_0^2+x^2))", "E/(pi*L)*2*z_0/(x^2+4*z_0^2)"), null, "without the paper's symbols: no verdict, as before");
  assert.equal(compareExpr("2*E*z_0/(pi*(4*z_0^2+x^2))", "2*E*z_s/(pi*(4*z_s^2+x^2))", { known }), null, "a name the paper does not use is still notation");
});
