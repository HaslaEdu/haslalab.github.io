// node --test community/test-grading-rules.mjs
// The grading regulation by competition family and paper kind, and the cacheable prompt prefix it builds.
import assert from "node:assert/strict";
import test from "node:test";
import { REG_VERSION, familyOf, paperKind, rulesFor, regulationOf, regulationId, stablePrefix, rulesText, RULE_ID, FAMILY_LIST } from "./src/grading-rules.js";

const KINDS = ["theory", "experiment", "data", "observation"];

test("competitions that mark alike share a family; everything else is general", () => {
  for (const c of ["ipho", "apho", "eupho", "ispho", "nbpho", "physcup", "gpho", "rmph", "izho"]) assert.equal(familyOf(c), "ipho", c);
  for (const c of ["usapho", "baupc"]) assert.equal(familyOf(c), "usapho", c);
  for (const c of ["cpho", "rupho"]) assert.equal(familyOf(c), "derivation", c);
  assert.equal(familyOf("opho"), "answer"); assert.equal(familyOf("kphe"), "kphe");
  for (const c of ["ioaa", "ioaajr", "usaaao"]) assert.equal(familyOf(c), "ioaa", c);
  for (const c of ["iao", "apao", "owao"]) assert.equal(familyOf(c), "iao", c);
  for (const c of ["icho", "ibo", "", undefined, "IPHO"]) assert.equal(familyOf(c), c === "IPHO" ? "ipho" : "general", String(c));
  const seen = new Set();
  for (const f of Object.values(FAMILY_LIST)) for (const c of f.comps) { assert.ok(!seen.has(c), "one family per competition: " + c); seen.add(c); }
});

test("paper kinds: theory, physics experiments, astronomy data analysis and observation", () => {
  assert.equal(paperKind("ipho", "T1", true), "theory");
  assert.equal(paperKind("ipho", "E1", false), "experiment");
  assert.equal(paperKind("nbpho", "E2", false), "experiment");
  assert.equal(paperKind("ioaa", "D1", false), "data");
  assert.equal(paperKind("ioaa", "G1", false), "data");
  assert.equal(paperKind("ioaa", "O3", false), "observation");
  assert.equal(paperKind("iao", "T", true), "theory");
});

test("every rule has a unique id the grader may cite, and both languages", () => {
  for (const family of Object.keys(FAMILY_LIST)) for (const kind of KINDS) {
    const rules = rulesFor(family, kind), ids = rules.map(r => r.id);
    assert.equal(new Set(ids).size, ids.length, `${family}/${kind} ids unique`);
    for (const r of rules) { assert.match(r.id, RULE_ID); assert.ok(r.en.length > 20 && r.ko.length > 10, r.id); }
  }
  // the general regulation is the one every exam had before families: R1–R11
  assert.deepEqual(rulesFor("general", "experiment").map(r => r.id).sort(), ["R1", "R10", "R11", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9"].sort());
  // the IPhO family carries forward errors instead of R5; OPhO marks answers only
  assert.ok(!rulesFor("ipho", "theory").some(r => r.id === "R5") && rulesFor("ipho", "theory").some(r => r.id === "IP1"));
  assert.ok(rulesFor("answer", "theory").some(r => r.id === "OP1"));
  assert.ok(rulesFor("ioaa", "observation").some(r => r.id === "OB1") && !rulesFor("ioaa", "theory").some(r => r.id === "OB1"));
  assert.ok(!rulesFor("ipho", "theory").some(r => r.id === "R11"), "measurement counts are not theory rules");
});

test("the cacheable prefix holds rules only: nothing from the year, the scheme or the candidate", () => {
  for (const family of Object.keys(FAMILY_LIST)) for (const kind of KINDS) {
    const head = stablePrefix(family, kind);
    assert.ok(head.startsWith("[TASK: grade]")); assert.ok(head.endsWith("[End of fixed rules]"));
    assert.ok(!/\b(19|20)\d\d\b(?!-)/.test(head.replace(REG_VERSION, "")), "no year in the prefix");
    assert.ok(!head.includes("<<SCHEME>>") && !head.includes("Exam context") && !head.includes("Korean") && !head.includes("English"));
    for (const r of rulesFor(family, kind)) assert.ok(head.includes(`${r.id}. ${r.en}`), `${family}/${kind} sends ${r.id}`);
    assert.equal(stablePrefix(family, kind), head, "deterministic, byte for byte");
  }
});

test("prefixes are shared from the most general block down: common, then kind, then family", () => {
  const common = (a, b) => { let i = 0; while (i < a.length && a[i] === b[i]) i++; return i; };
  const ipT = stablePrefix("ipho", "theory"), ipE = stablePrefix("ipho", "experiment"), kaE = stablePrefix("derivation", "experiment");
  const core = ipE.indexOf("[Paper rules"), kindEnd = ipE.indexOf("[Competition rules");
  assert.ok(core > 0 && kindEnd > 0);
  assert.ok(common(ipT, ipE) >= ipT.indexOf("[Review"), "theory and experiment share the common block");
  assert.ok(common(ipE, kaE) >= kindEnd, "two families share the common and kind blocks");
  assert.notEqual(ipE, kaE); assert.notEqual(ipT, ipE);
  // the text grader's rules follow the same order
  assert.ok(rulesText("ioaa", "data").indexOf("[Paper rules") < rulesText("ioaa", "data").indexOf("[Competition rules"));
});

test("a sign error carried into later parts is penalised once, as the official IPhO/APhO/EuPhO schemes say", () => {
  const ip1 = rulesFor("ipho", "theory").find(r => r.id === "IP1");
  assert.match(ip1.en, /penalised once, where the mistake is made/); assert.match(ip1.en, /sign/); assert.match(ip1.en, /only the first part loses marks/);
  assert.match(ip1.en, /dimensionally wrong/); assert.match(ip1.en, /wrong sign of a physical effect/, "IPhO 2022 Rule 1(a): an obviously wrong sign of the effect may be penalised again");
  for (const c of ["ipho", "apho", "eupho", "ispho"]) assert.ok(rulesFor(familyOf(c), "theory").includes(ip1), c);
  assert.ok(rulesFor("ioaa", "theory").some(r => r.id === "IO1" && r.en === ip1.en));
  assert.ok(!rulesFor("answer", "theory").some(r => r.id === "IP1"), "OPhO marks answers only");
});

test("a session shows the union of its papers' rules under one family title", () => {
  const reg = regulationOf("nbpho", ["experiment", "theory", "experiment"]);
  assert.equal(reg.version, REG_VERSION); assert.equal(reg.family, "ipho"); assert.deepEqual(reg.kinds, ["experiment", "theory"]);
  assert.ok(reg.title.ko && reg.title.en);
  const ids = reg.rules.map(r => r.id); assert.equal(new Set(ids).size, ids.length);
  assert.ok(ids.includes("R11") && ids.includes("IP6") && ids.includes("IP7"), "NBPhO's booklet: experiment and theory rules together");
  assert.equal(regulationOf("icho", []).rules.length, 11, "an unknown kind list falls back to the general experiment rules");
  assert.equal(regulationId("ipho", "theory"), REG_VERSION + "/ipho/theory");
});

test("IPhO-style theory: a correct boxed answer earns its question's method marks unless a derivation is required", () => {
  const ip8 = rulesFor("ipho", "theory").find(r => r.id === "IP8");
  assert.ok(ip8, "IPhO, APhO and the base family grade theory with IP8");
  assert.match(ip8.en, /correct final answer .* earns every mark of its question/);
  assert.match(ip8.en, /derive, show or prove/); assert.match(ip8.en, /without derivation earns nothing/);
  for (const c of ["ipho", "apho", "eupho"]) assert.ok(rulesFor(familyOf(c), "theory").includes(ip8), c);
  assert.ok(!rulesFor("ipho", "experiment").some(r => r.id === "IP8"), "experiments keep their own evidence rules");
  assert.ok(!rulesFor("usapho", "theory").some(r => r.id === "IP8") && !rulesFor("general", "theory").some(r => r.id === "IP8"));
});
