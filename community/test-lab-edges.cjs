// Exam mode edge cases in a browser (Playwright): a computer whose clock is an hour off, a second exam opened while
// one runs, signing out mid-exam, the time running out while no page is open.  Same set-up as test-lab-browser.cjs:
//   node test-lab-edges.cjs
const { chromium } = require("playwright");
const SITE = "http://localhost:8765", API = "http://127.0.0.1:8787";
let fails = 0;
const ok = (c, m) => { if (!c) fails++; console.log((c ? "PASS " : "FAIL ") + m); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const call = async (m, p, body, tok) => { const r = await fetch(API + "/api" + p, { method: m, headers: { "Content-Type": "application/json", ...(tok ? { Authorization: "Bearer " + tok } : {}) }, body: body ? JSON.stringify(body) : undefined }); return [r.status, await r.json()]; };
const clockSec = t => { const p = t.match(/(\d+:)?\d+:\d+/)[0].split(":").map(Number); return p.length === 3 ? p[0] * 3600 + p[1] * 60 + p[2] : p[0] * 60 + p[1]; };

(async () => {
  const rnd = Math.random().toString(36).slice(2, 7);
  const TOK = (await call("POST", "/signup", { username: "edg" + rnd, nickname: "edg" + rnd, password: "password1" }))[1].token;
  /* this run is about the last token: the account starts with one instead of the five every account gets */
  require("child_process").execSync(`npx wrangler d1 execute haslalab-community --local --command "UPDATE users SET exam_tokens=1 WHERE username='edg${rnd}'"`, { cwd: __dirname, stdio: "ignore" });
  const browser = await chromium.launch();
  const errs = [];
  const mk = async (skewSec, tok = TOK) => {
    const ctx = await browser.newContext({ viewport: { width: 1500, height: 900 } });
    await ctx.addInitScript(([api, tok, skew]) => {
      if (!sessionStorage.getItem("seeded")) { sessionStorage.setItem("seeded", "1"); localStorage.setItem("hlCmApi", api); if (tok) localStorage.setItem("hlCmTok", tok); localStorage.setItem("hlLang", "ko"); }
      if (skew) { const D = Date, now = D.now; Date.now = () => now.call(D) + skew * 1000; }
    }, [API, tok, skewSec || 0]);
    return ctx;
  };
  /* the catalogue's exam links */
  let ctx = await mk(), pg = await ctx.newPage(); pg.on("pageerror", e => errs.push(e.message));
  const portal = async (comp, year) => { await pg.goto(SITE + "/#/" + comp + "/exam"); await pg.waitForSelector("#xmRoot tbody tr");
    return SITE + "/" + await pg.$$eval("#xmRoot tbody tr", (trs, y) => trs.find(t => t.querySelector(".y").textContent === y).querySelector("a.go").getAttribute("href"), String(year)); };
  const A = await portal("ipho", 2024), Bx = await portal("apho", 2025);
  await ctx.close();

  /* 1. a computer whose clock is an hour fast: the timer still shows the server's time */
  ctx = await mk(3600); pg = await ctx.newPage(); pg.on("pageerror", e => errs.push(e.message)); pg.on("dialog", d => d.accept());
  await pg.goto(A); await pg.waitForSelector("#go");
  for (const c of await pg.$$("[data-ag]")) await c.check();
  /* double click on start, then confirm twice as fast as possible */
  await pg.click("#go"); await pg.click(".modal button.red");
  await pg.waitForSelector(".desk iframe", { timeout: 15000 }); await sleep(1500);
  const c = clockSec(await pg.textContent("#clock"));
  ok(c > 80 && c <= 90, "clock right on a computer an hour fast: " + c);
  ok(await pg.$(".dark") === null, "…and the exam was not ended by the wrong local clock");
  let [, a] = await call("GET", "/lab/active", null, TOK);
  ok(a.tokens === 0 && a.active.status === "running", "one token spent, running");

  /* 2. another exam opened while this one runs: no start, a link back */
  await pg.goto(Bx); await sleep(1800);
  ok(await pg.$("#go") === null && /진행 중인 다른 실전 시험/.test(await pg.textContent("main")), "APhO page: «another exam in progress», no start");
  await pg.click("main a[href^=\"exam.html\"] button.pri"); await pg.waitForSelector(".desk iframe", { timeout: 15000 }); await sleep(1200);
  const c2 = clockSec(await pg.textContent("#clock"));
  ok(c2 < c && c2 > 0 && /IPhO 2024/.test(await pg.textContent("#bTitle")), `«go to that exam» resumes IPhO 2024 (${c} → ${c2})`);
  ok((await call("GET", "/lab/active", null, TOK))[1].tokens === 0, "still 0 tokens");

  /* 3. signed out mid-exam: the login gate; signed back in: the same exam resumes */
  await pg.evaluate(() => localStorage.removeItem("hlCmTok"));
  await pg.reload(); await sleep(1500);
  ok(/로그인한 사람만/.test(await pg.textContent("main")) && await pg.$(".desk iframe") === null, "signed out → login gate");
  await pg.evaluate(t => localStorage.setItem("hlCmTok", t), TOK);
  await pg.reload(); await pg.waitForSelector(".desk iframe", { timeout: 15000 }); await sleep(1200);
  const c3 = clockSec(await pg.textContent("#clock"));
  ok(c3 < c2, `signed back in → same exam, clock still running (${c2} → ${c3})`);
  const S = (await call("GET", "/lab/active", null, TOK))[1].active;
  await ctx.close();

  /* 4. the time runs out while no page is open: on return, straight to the scan with the right deadline */
  await sleep((S.ended_at - S.now + 3) * 1000);
  ctx = await mk(); pg = await ctx.newPage(); pg.on("pageerror", e => errs.push(e.message));
  await pg.goto(A); await pg.waitForSelector("#qr svg", { timeout: 15000 }); await sleep(800);
  const left = clockSec(await pg.textContent("#sClock"));
  const want = S.scan_until - (S.now + (S.ended_at - S.now + 3)) - 1;
  ok(Math.abs(left - want) <= 4, `returning after the time ran out: scan clock ${left} s (expected ≈ ${want}), counted from the end of the exam, not from now`);
  [, a] = await call("GET", "/lab/active", null, TOK);
  ok(a.active.status === "scanning" && a.active.ended_at === S.ended_at, "server: ended at start + exam");
  /* 5. the scan time runs out with the page closed: the session is submitted by itself */
  await ctx.close();
  await sleep((a.active.scan_until - a.active.now + 3) * 1000);
  ctx = await mk(); pg = await ctx.newPage();
  await pg.goto(SITE + "/#/lab"); await sleep(2500);
  [, a] = await call("GET", "/lab/active", null, TOK);
  const list = (await call("GET", "/lab/sessions", null, TOK))[1].sessions;
  ok(a.active === null && !["running", "scanning"].includes(list[0].status), "after the scan time with no page open: submitted as it stood (" + list[0].status + ")");
  await pg.goto(A); await sleep(1500);
  ok(await pg.$("#go") === null && /토큰이 없습니다/.test(await pg.textContent("main")), "and no new start without a token");
  await ctx.close();
  ok(errs.length === 0, "no page errors " + JSON.stringify(errs.slice(0, 4)));
  await browser.close();
  console.log(fails ? fails + " FAILED" : "all passed");
  process.exit(fails ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
