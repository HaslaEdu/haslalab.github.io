// node --test community/test-curated-schemes.mjs
// Curated marking schemes (schemes/<exam>/<task>.json, served by the site and used before any machine-built scheme):
// every file is a valid scheme whose items add up to its total, and the Worker's list of curated papers matches the
// folders, so a paper's scheme is neither missed nor fetched for nothing.
import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { tidySchemeItems, cleanParts, cappedSum, oneMethod, schemeTotal } from "./src/lab-scheme-items.js";

const root = new URL("../schemes/", import.meta.url);
const exams = existsSync(root) ? readdirSync(root, { withFileTypes: true }).filter(d => d.isDirectory()).map(d => d.name).sort() : [];
const CHECKS = ["axes_labeled", "axes_units", "scale_ok", "points_min", "fit_line", "slope_read", "error_bars", "title", "rows_min", "columns_units"];

test("the Worker's curated list is exactly the schemes folders", () => {
  const src = readFileSync(new URL("./src/index.js", import.meta.url), "utf8");
  const m = /const CURATED_SCHEMES = new Set\(\[([^\]]*)\]\)/.exec(src); assert.ok(m, "CURATED_SCHEMES in index.js");
  const listed = [...m[1].matchAll(/"([a-z]{3,8}\d{4})"/g)].map(x => x[1]).sort();
  assert.deepEqual(listed, exams);
});

for (const exam of exams) for (const file of readdirSync(new URL(exam + "/", root)).filter(f => f.endsWith(".json"))) {
  test(`${exam}/${file}: a valid scheme whose items add up to its total`, () => {
    assert.match(exam, /^[a-z]{3,8}\d{4}$/); assert.match(file, /^[A-Z][A-Za-z0-9]{0,3}\.json$/);
    const sc = JSON.parse(readFileSync(new URL(`${exam}/${file}`, root), "utf8"));
    assert.ok(+sc.points > 0 && Array.isArray(sc.items) && sc.items.length);
    const ids = sc.items.map(i => String(i.id)); assert.equal(new Set(ids).size, ids.length, "ids unique");
    for (const it of sc.items) {
      assert.ok(+it.points > 0, `${it.id}: points`);
      assert.ok(["value", "graph", "table", "derivation", "other"].includes(it.type), `${it.id}: type`);
      assert.ok(["answer", "any"].includes(it.sheet), `${it.id}: sheet`);
      assert.ok(!it.role || ["result", "step"].includes(it.role), `${it.id}: role`);
      assert.ok(typeof it.what === "string" && it.what.length >= 3, `${it.id}: what`);
      for (const c of it.checks || []) assert.ok(CHECKS.includes(c.check), `${it.id}: check ${c.check}`);
      if (it.full_min != null || it.full_max != null) assert.ok(Number.isFinite(+it.full_min) && Number.isFinite(+it.full_max) && +it.full_min <= +it.full_max, `${it.id}: window`);
    }
    const items = tidySchemeItems(sc.items), parts = cleanParts(sc.parts);
    assert.equal(items.length, sc.items.length, "no item dropped by tidying");
    const total = cappedSum(oneMethod(items).kept, parts, null);
    assert.ok(Math.abs(total - sc.points) < 0.011, `items (capped by their parts) add up to ${sc.points}: ${total}`);
    assert.ok(Math.abs(schemeTotal({ ...sc, items, parts }) - sc.points) < 0.011);
  });
}
