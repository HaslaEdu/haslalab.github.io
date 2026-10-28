// The scan bench (sim/scanbench.html), admins only: a photo goes to every connected provider and to the on-device
// finder; the admin's true corners rank them.  Against `npm run dev` with test-lab-mock.mjs (its Gemini stand-in
// answers the corner question; Upstage's has no words, so it finds nothing) and the site on :8765.  node test-scanbench.cjs
const { chromium } = require("playwright");
const SITE = "http://localhost:8765", API = "http://127.0.0.1:8787";
let fails = 0;
const ok = (c, m) => { if (!c) fails++; console.log((c ? "PASS " : "FAIL ") + m); };
const call = async (m, p, body, tok) => { const r = await fetch(API + "/api" + p, { method: m, headers: { "Content-Type": "application/json", ...(tok ? { Authorization: "Bearer " + tok } : {}) }, body: body ? JSON.stringify(body) : undefined }); return [r.status, await r.json()]; };
(async () => {
  const rnd = Math.random().toString(36).slice(2, 7);
  const ADM = (await call("POST", "/signup", { username: "sbA" + rnd, nickname: "sbA" + rnd, password: "password1" }))[1].token;
  const USR = (await call("POST", "/signup", { username: "sbU" + rnd, nickname: "sbU" + rnd, password: "password1" }))[1].token;
  require("child_process").execSync(`npx wrangler d1 execute haslalab-community --local --command "UPDATE users SET role='admin' WHERE username='sbA${rnd}'"`, { cwd: __dirname, stdio: "ignore" });
  ok((await call("GET", "/admin/lab/scanbench", null, USR))[0] === 403, "not for ordinary users");
  const b = await chromium.launch(), ctx = await b.newContext({ viewport: { width: 430, height: 900 } });
  await ctx.addInitScript(([api, tok]) => { localStorage.setItem("hlCmApi", api); localStorage.setItem("hlCmTok", tok); }, [API, ADM]);
  const pg = await ctx.newPage(), errs = []; pg.on("pageerror", e => errs.push(e.message));
  await pg.goto(SITE + "/sim/scanbench.html"); await pg.waitForSelector("#sum table");
  /* a printed sheet with its corner squares, tilted on a desk */
  const photo = await pg.evaluate(() => { const c = document.createElement("canvas"); c.width = 1200; c.height = 1600; const g = c.getContext("2d");
    g.fillStyle = "#4a3a2c"; g.fillRect(0, 0, 1200, 1600); g.translate(600, 800); g.rotate(0.05); const W = 820, H = W * 297 / 210;
    g.fillStyle = "#f6f4ef"; g.fillRect(-W / 2, -H / 2, W, H); const m = W / 210 * 7; g.fillStyle = "#111";
    [[0.045, 0.035], [0.955, 0.035], [0.045, 0.965], [0.955, 0.965]].forEach(([u, v]) => g.fillRect(-W / 2 + u * W - m / 2, -H / 2 + v * H - m / 2, m, m));
    return c.toDataURL("image/jpeg", 0.9).split(",")[1]; });
  await pg.setInputFiles("#gal", { name: "a4.jpg", mimeType: "image/jpeg", buffer: Buffer.from(photo, "base64") });
  await pg.waitForFunction(() => /gemini/.test(document.getElementById("legend").textContent), null, { timeout: 30000 });
  const leg = await pg.textContent("#legend");
  ok(/haslalab/.test(leg) && /on-device · marker/.test(leg) && /gemini/.test(leg) && /upstage/.test(leg), "each provider and the on-device finder answered " + leg.replace(/\s+/g, " ").slice(0, 160));
  await pg.click("#save"); await pg.waitForFunction(() => /정답이 있는 사진 [1-9]/.test(document.getElementById("sum").textContent), null, { timeout: 10000 });
  const rows = await pg.$$eval("#sum tbody tr", t => t.map(r => [...r.children].map(x => x.textContent.trim())));
  const hl = rows.find(r => /^haslalab/.test(r[0])), gm = rows.find(r => /^gemini/.test(r[0]));
  ok(hl && parseFloat(hl[1]) < 0.5 && gm && parseFloat(gm[1]) > 1, "ranked against the saved truth: the on-device finder on its own marks, the stand-in off " + JSON.stringify(rows.map(r => r.slice(0, 3))));
  ok(rows.some(r => /^upstage/.test(r[0]) && r[4] !== "0"), "Upstage, with no page finder, counts as a failure here");
  ok(errs.length === 0, "no page errors " + JSON.stringify(errs));
  await b.close();
  console.log(fails ? fails + " FAILED" : "all passed"); process.exit(fails ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
