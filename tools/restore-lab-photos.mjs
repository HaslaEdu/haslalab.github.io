#!/usr/bin/env node
// Puts purged answer photos back from a saved copy (the zip of photos/page_<id>.jpg with manifest.json).
//   node tools/restore-lab-photos.mjs <unzipped folder> <admin token> [api base]
// The admin token is the site's own login token: in the browser, logged in as the admin, run
//   localStorage.getItem("hlCmTok")
// in the developer console. Each page goes to POST /api/admin/lab/pages/<id>/photo; a page that still has its photo is
// skipped by the server, so running it twice does nothing more.
import { readFileSync } from "node:fs";
import { join } from "node:path";

const [dir, token, base = "https://haslalab-community.haslalab.workers.dev"] = process.argv.slice(2);
if (!dir || !token) { console.error("usage: node tools/restore-lab-photos.mjs <folder> <admin token> [api base]"); process.exit(1); }
const manifest = JSON.parse(readFileSync(join(dir, "manifest.json"), "utf8"));
let restored = 0, skipped = 0, failed = 0;
for (const page of manifest) {
  const image = readFileSync(join(dir, "photos", page.file)).toString("base64");
  const res = await fetch(`${base.replace(/\/+$/, "")}/api/admin/lab/pages/${page.page_id}/photo`, {
    method: "POST", headers: { Authorization: "Bearer " + token, "Content-Type": "application/json" }, body: JSON.stringify({ image }) });
  const out = await res.json().catch(() => ({}));
  if (res.ok && out.restored) restored++; else if (res.ok) skipped++; else { failed++; console.error(`page ${page.page_id}: ${res.status} ${out.error || ""}`); }
}
console.log(`restored ${restored}, already there ${skipped}, failed ${failed} (of ${manifest.length})`);
