// Exam mode in a browser (Playwright): catalogue → login gate → token start → shared kit and bench → reloads, leaving
// and a second computer (timer not reset, no second token) → time up → QR → phone scan upload → check text → submit
// → result → #/lab, and the Discord page.  Needs `npm run dev` with .dev.vars
//   LAB_TEST_EXAM_SEC=90  LAB_TEST_SCAN_SEC=120  LAB_TEST_GRACE_SEC=1  (+ the stand-in OCR/grader of test-lab.mjs)
// the site served at http://localhost:8765 (python3 -m http.server 8765 in the repository root), then:
//   node test-lab-browser.cjs     (Playwright with Chromium must be installed)
const { chromium } = require("playwright");
const SITE = "http://localhost:8765", API = "http://127.0.0.1:8787";
const OUT = require("os").tmpdir() + "/haslalab-lab-shots/";
require("fs").mkdirSync(OUT, { recursive: true });
let fails = 0;
const ok = (c, m) => { if (!c) fails++; console.log((c ? "PASS " : "FAIL ") + m); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const call = async (m, p, body, tok) => { const r = await fetch(API + "/api" + p, { method: m, headers: { "Content-Type": "application/json", ...(tok ? { Authorization: "Bearer " + tok } : {}) }, body: body ? JSON.stringify(body) : undefined }); return [r.status, await r.json()]; };
const clockSec = t => { const p = t.match(/(\d+:)?\d+:\d+/)[0].split(":").map(Number); return p.length === 3 ? p[0] * 3600 + p[1] * 60 + p[2] : p[0] * 60 + p[1]; };

(async () => {
  const rnd = Math.random().toString(36).slice(2, 7);
  const [, su] = await call("POST", "/signup", { username: "e2e" + rnd, nickname: "e2e" + rnd, password: "password1" });
  const TOK = su.token;
  /* an E1 marking scheme, so one experiment is graded and the other waits for an admin */
  require("child_process").execSync(`npx wrangler d1 execute haslalab-community --local --command "UPDATE users SET exam_tokens=1 WHERE username='e2e${rnd}'; DELETE FROM lab_rubrics WHERE exam_key='ipho2024' AND task='E2'; INSERT OR REPLACE INTO lab_rubrics(exam_key,task,points,rubric,reference,updated_at) VALUES('ipho2024','E1',10,'[{\\"id\\":\\"A1\\",\\"name\\":\\"R0\\",\\"max\\":4,\\"requirement\\":\\"R0 108\\"},{\\"id\\":\\"A2\\",\\"name\\":\\"lambda\\",\\"max\\":6,\\"requirement\\":\\"lambda\\"}]','R0 = 108 ohm',0)"`, { cwd: __dirname, stdio: "ignore" });
  const browser = await chromium.launch();
  const mk = async (opts) => {
    const ctx = await browser.newContext({ viewport: { width: 1600, height: 950 }, ...(opts || {}) });
    await ctx.addInitScript(([api, tok]) => { localStorage.setItem("hlCmApi", api); if (tok) localStorage.setItem("hlCmTok", tok); localStorage.setItem("hlLang", "ko"); }, [API, opts && opts.anon ? "" : TOK]);
    return ctx;
  };
  const errs = [];
  const watch = pg => { pg.on("pageerror", e => errs.push(e.message)); };

  /* 1. the catalogue */
  let ctx = await mk(), pg = await ctx.newPage(); watch(pg);
  /* practice (the competition page as before) and exam (the portal) */
  await pg.goto(SITE + "/#/ipho"); await pg.waitForSelector(".modesw");
  ok(await pg.$(".modesw a.on[href='#/ipho']") !== null && await pg.$(".years") !== null, "competition page: practice is chosen, the year grid shows");
  await pg.goto(SITE + "/#/ipho/2024"); await pg.waitForSelector(".prob");
  const runBtns = await pg.$$eval(".prob .acts .main .btn", a => a.map(x => x.textContent.trim()));
  ok(runBtns.filter(x => x === "브라우저에서 실행").length === 2 && await pg.$("a.btn.exam") === null, "practice cards: run in the browser, no exam buttons " + JSON.stringify(runBtns));
  ok(await pg.$(".yrexam a[href='#/ipho/exam']") !== null, "the year page points to the exam portal");
  await pg.click(".yrexam a"); await pg.waitForSelector("#xmRoot table");
  ok(await pg.$(".modesw a.ex.on") !== null && await pg.$(".years") === null, "exam portal: exam chosen, no year grid");
  const row = await pg.$$eval("#xmRoot tbody tr", trs => trs.map(t => [t.querySelector(".y").textContent, t.querySelector(".t").textContent, (t.querySelector("a.go") || {}).getAttribute && t.querySelector("a.go").getAttribute("href")]).find(r => r[0] === "2024"));
  ok(row && /E1 \+ E2/.test(row[1]) && /e=E1%2CE2/.test(row[2]), "portal row: IPhO 2024 · E1 + E2 → the exam " + JSON.stringify(row && row.slice(0, 2)));
  await pg.screenshot({ path: OUT + "1-portal.png", fullPage: true });
  const EXAM_URL = SITE + "/" + row[2];
  await ctx.close();

  /* 2. not signed in: no way to start */
  ctx = await mk({ anon: true }); pg = await ctx.newPage(); watch(pg);
  await pg.goto(EXAM_URL); await pg.waitForSelector(".card h1");
  await sleep(800);
  ok(await pg.$("#go") === null && /로그인한 사람만/.test(await pg.textContent("main")), "signed out: login required, no start button");
  await ctx.close();

  /* 3. signed in with one token: start */
  ctx = await mk(); pg = await ctx.newPage(); watch(pg);
  await pg.goto(EXAM_URL); await pg.waitForSelector("#go");
  ok(/보유 1개/.test(await pg.textContent("main")) && /수험 안내/.test(await pg.textContent("main")), "instructions page shows 1 token");
  ok(await pg.$eval("#go", b => b.disabled), "start is locked until the declaration is ticked");
  await pg.screenshot({ path: OUT + "2-instructions.png", fullPage: true });
  ok(await pg.$("main a[href*='.pdf']") === null, "the problem sheet is not offered before the exam");
  const sheetsUrl = await pg.$eval("main a[href^='sheets.html']", a => a.href);
  ok(/c=ipho/.test(sheetsUrl) && /e=E1%2CE2/.test(sheetsUrl), "…the answer and working sheets are, to print beforehand");
  const sp = await ctx.newPage(); await sp.goto(sheetsUrl); await sp.waitForSelector("#off .o");
  const offs = await sp.$$eval("#off a", as => as.map(a => a.getAttribute("href")));
  ok(offs.includes("sheets/IPhO_2024_E1_AS.pdf") && offs.includes("sheets/IPhO_2024_E2_AS.pdf"), "sheets page: the official IPhO 2024 answer sheets " + JSON.stringify(offs));
  ok((await fetch(SITE + "/sim/sheets/IPhO_2024_E1_AS.pdf")).headers.get("content-type") === "application/pdf", "…which are there to open");
  const sh = await sp.$$eval(".pg", ps => ps.map(p => p.querySelector(".k").textContent));
  ok(!sh.some(x => /ANSWER SHEET/.test(x)) && sh.some(x => /E2 · WORKING SHEET/.test(x)) && await sp.$(".pg .mk.d") !== null && !(await sp.textContent("body")).includes("_E1_EN.pdf"),
    "no official working sheet that year: HaslaLab's, with corner markers; no problem text " + sh.length);
  await sp.goto(sheetsUrl.replace("y=2024", "y=2015")); await sp.waitForSelector(".pg .bx");
  ok(await sp.$$("#off a") .then(x => x.length === 0) && await sp.$$eval(".pg .k", ks => ks.some(k => /E1 · ANSWER SHEET/.test(k.textContent))), "a year without official sheets: HaslaLab's answer sheets");
  await sp.close();
  for (const c of await pg.$$("[data-ag]")) await c.check();
  ok(!(await pg.$eval("#go", b => b.disabled)), "…and opens when every line is ticked");
  await pg.click("#go"); await pg.waitForSelector(".modal");
  await pg.click(".modal button.red");
  await pg.waitForSelector(".desk iframe");
  ok((await call("GET", "/lab/active", null, TOK))[1].tokens === 0, "token spent on start (server: 0)");
  await pg.waitForFunction(() => document.querySelectorAll("#kit canvas").length === 2, null, { timeout: 15000 });
  await sleep(1500);
  const c1 = clockSec(await pg.textContent("#clock"));
  ok(c1 > 70 && c1 <= 90, "the clock runs from the server's 90 s: " + c1);
  /* the kit mirrors both simulators' parts boxes */
  const inked = await pg.$$eval("#kit canvas", cs => cs.map(c => { const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 0; i < d.length; i += 4) if (d[i] + d[i + 1] + d[i + 2] > 200) n++; return [c.width, c.height, n]; }));
  ok(inked.every(([w, h, n]) => w > 50 && h > 50 && n > 100), "both kits drawn in the shared kit " + JSON.stringify(inked));
  const hidden = await pg.$$eval(".desk iframe", fs => fs.map(f => { const t = f.contentDocument.getElementById("hlExamTray"); return t ? f.contentWindow.getComputedStyle(t).left : "none"; }));
  ok(hidden.every(x => x === "-10000px"), "the simulators' own parts boxes are moved off screen " + JSON.stringify(hidden));
  /* pick a part from the shared kit: it must end up in that simulator's hand */
  const kc = await pg.$('#kit canvas[data-k="0"]'), kb = await kc.boundingBox();
  await pg.mouse.click(kb.x + kb.width / 2, kb.y + 20);
  await sleep(300);
  const held = await pg.$eval(".desk iframe", f => { try { return f.contentWindow.eval("typeof hand!=='undefined'&&hand?JSON.stringify(hand):null"); } catch (e) { return "err " + e.message; } });
  ok(held && held !== "null" && !/^err/.test(held), "clicking the shared kit picks the part up in E1: " + held);
  ok(/E1/.test(await pg.textContent("#hand")), "the kit says where to put it");
  /* put it down on the E1 bench */
  const fr = await (await pg.$(".desk iframe")).boundingBox();
  const cvb = await pg.$eval(".desk iframe", f => { const r = f.contentDocument.getElementById("cv").getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; });
  await pg.mouse.move(fr.x + cvb[0] + cvb[2] * 0.4, fr.y + cvb[1] + cvb[3] * 0.5);
  await pg.mouse.click(fr.x + cvb[0] + cvb[2] * 0.4, fr.y + cvb[1] + cvb[3] * 0.5);
  await sleep(300);
  const after = await pg.$eval(".desk iframe", f => f.contentWindow.eval("typeof hand!=='undefined'&&hand?'holding':'placed'"));
  ok(after === "placed", "…and clicking the E1 bench puts it down: " + after);
  ok(await pg.$$eval(".desk iframe", fs => fs.every(f => { const b = f.contentDocument.getElementById("haslalab-adfit-banner"); return !b || f.contentWindow.getComputedStyle(b).display === "none"; })), "no ad slots on the exam bench");
  /* the problem sheet: only here, drawn by pdf.js beside the bench, and not printable */
  ok(!(await pg.$eval("#bPaper", b => b.hidden)), "«문제지 열기» on the exam bar");
  await pg.click("#bPaper");
  await pg.waitForSelector("#ps .pv canvas", { timeout: 30000 }).catch(() => {});
  const pcs = await pg.$$eval("#ps .pv canvas", cs => cs.map(c => c.width));
  ok(pcs.length >= 1 && pcs[0] > 200, "the problem sheet opens beside the bench as drawn pages " + JSON.stringify(pcs.slice(0, 3)));
  ok(await pg.$("#ps a[href], #ps iframe, #ps embed") === null, "…with no link, frame or viewer toolbar to download it from");
  await pg.screenshot({ path: OUT + "2-paper.png" });
  await pg.emulateMedia({ media: "print" });
  ok(await pg.$eval("main", m => getComputedStyle(m).display) === "none", "printing the exam window prints nothing");
  await pg.emulateMedia({ media: "screen" });
  await pg.click("#bPaper");
  ok(await pg.$eval("#ps", e => e.hidden), "…and closes again");
  await pg.screenshot({ path: OUT + "2-bench.png" });

  /* 4. leaving and coming back: reload, other page, second computer — same exam, timer not reset, no spend */
  await sleep(2000);
  pg.on("dialog", d => d.accept());
  await pg.reload(); await pg.waitForSelector(".desk iframe", { timeout: 15000 }); await sleep(1200);
  const c2 = clockSec(await pg.textContent("#clock"));
  ok(c2 < c1 - 2 && c2 > 0, `after a reload the clock carries on (${c1} → ${c2}), not reset`);
  await pg.goto(SITE + "/#/ipho/2024"); await pg.waitForSelector(".prob"); await sleep(3000);
  await pg.goto(EXAM_URL); await pg.waitForSelector(".desk iframe", { timeout: 15000 }); await sleep(1200);
  const c3 = clockSec(await pg.textContent("#clock"));
  ok(c3 < c2 - 3, `away 3 s and back: ${c2} → ${c3} (time kept running)`);
  const ctx2 = await mk(), pg2 = await ctx2.newPage(); watch(pg2);
  await pg2.goto(EXAM_URL); await pg2.waitForSelector(".desk iframe", { timeout: 15000 }); await sleep(1200);
  const c4 = clockSec(await pg2.textContent("#clock")), c3b = clockSec(await pg.textContent("#clock"));
  ok(Math.abs(c4 - c3b) <= 2, `another computer shows the same clock (${c3b} vs ${c4})`);
  let [, act] = await call("GET", "/lab/active", null, TOK);
  ok(act.tokens === 0, "still 0 tokens after reload, leaving, second computer");
  const [, tk] = await call("GET", "/lab/tokens", null, TOK);
  ok(tk.ledger.length === 1, "ledger has the one start only");
  /* the second computer starts nothing new even if its script asks */
  const again = await pg2.evaluate(async () => { const r = await fetch(localStorage.getItem("hlCmApi") + "/api/lab/start", { method: "POST", headers: { "Content-Type": "application/json", Authorization: "Bearer " + localStorage.getItem("hlCmTok") }, body: JSON.stringify({ comp: "ipho", year: 2024, tasks: ["E1", "E2"] }) }); return r.json(); });
  ok(again.resumed === true && (await call("GET", "/lab/active", null, TOK))[1].tokens === 0, "start called again → resumed, no spend");
  await ctx2.close();

  /* 5. time is up: the bench goes dark, the QR code appears */
  const left = clockSec(await pg.textContent("#clock"));
  await sleep((left + 1) * 1000);
  await pg.waitForSelector("#qr svg", { timeout: 20000 });
  ok(await pg.$(".desk iframe") === null, "the experiments are switched off");
  const scanLink = await pg.$eval('#qrArea a[target="_blank"]', a => a.href);
  ok(/scan\.html#c=[0-9a-z]{8,9}[0-9A-Za-z]{22}&/.test(scanLink) && !/[#&]s=/.test(scanLink), "QR / link carries one scan code (time + random digits), no session number " + scanLink.split("#")[1]);
  await pg.screenshot({ path: OUT + "3-scan.png" });
  [, act] = await call("GET", "/lab/active", null, TOK);
  ok(act.active && act.active.status === "scanning", "server: scanning");
  /* reload during the scan: same deadline */
  const s1 = clockSec(await pg.textContent("#sClock"));
  await pg.reload(); await pg.waitForSelector("#qr svg"); await sleep(1500);
  const s2 = clockSec(await pg.textContent("#sClock"));
  ok(s2 <= s1 && s2 > s1 - 5, `scan clock not reset by a reload (${s1} → ${s2})`);
  const scanLink2 = await pg.$eval('#qrArea a[target="_blank"]', a => a.href);
  ok(scanLink2 === scanLink, "same QR after a reload (the upload token is kept)");

  /* 6. the phone */
  const phone = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  const ph = await phone.newPage(); watch(ph);
  await ph.goto(scanLink); await ph.waitForSelector("#cam", { state: "attached" });
  ok(!/k=/.test(ph.url()), "the token is taken out of the phone's address bar");
  /* a photo: a white sheet with writing, tilted on a dark desk */
  const photo = await ph.evaluate(() => { const c = document.createElement("canvas"); c.width = 1200; c.height = 1600; const g = c.getContext("2d");
    g.fillStyle = "#3b2f25"; g.fillRect(0, 0, 1200, 1600); g.fillStyle = "#f4f1ea"; g.beginPath(); g.moveTo(180, 140); g.lineTo(1040, 200); g.lineTo(1000, 1480); g.lineTo(140, 1420); g.closePath(); g.fill();
    g.fillStyle = "#222"; g.font = "42px sans-serif"; ["E1 A.1  R0 = 108.2 ohm", "slope k = 0.385 ohm/K", "A.2  lambda = 395 W/(m K)"].forEach((t, i) => g.fillText(t, 260, 380 + i * 90));
    return c.toDataURL("image/jpeg", 0.9).split(",")[1]; });
  await ph.setInputFiles("#cam", { name: "p1.jpg", mimeType: "image/jpeg", buffer: Buffer.from(photo, "base64") });
  await ph.waitForSelector("#send", { timeout: 20000 });
  await ph.screenshot({ path: OUT + "4-phone-preview.png" });
  await ph.click("#send");
  await ph.waitForFunction(() => /보낸 쪽 · 1/.test(document.body.textContent), null, { timeout: 20000 });
  ok(true, "phone sent page 1");
  /* a second page, working sheet for E2 */
  await ph.click('#kinds [data-k="working"]'); await ph.click('#tasks [data-t="E2"]');
  await ph.setInputFiles("#gal", { name: "p2.jpg", mimeType: "image/jpeg", buffer: Buffer.from(photo, "base64") });
  await ph.waitForSelector("#send", { timeout: 20000 }); await ph.click("#send");
  await ph.waitForFunction(() => /보낸 쪽 · 2/.test(document.body.textContent), null, { timeout: 20000 });
  await ph.screenshot({ path: OUT + "5-phone-sent.png" });
  ok(true, "phone sent page 2 (E2 working sheet)");
  /* the live camera: a printed sheet with its four corner squares in view is outlined and taken by itself */
  await ph.click('#kinds [data-k="answer"]'); await ph.click('#tasks [data-t="E1"]');
  await ph.evaluate(() => {
    const c = document.createElement("canvas"); c.width = 1080; c.height = 1440; const g = c.getContext("2d");
    const draw = () => { g.setTransform(1, 0, 0, 1, 0, 0); g.fillStyle = "#4a3a2c"; g.fillRect(0, 0, 1080, 1440);
      g.translate(540, 720); g.rotate(0.06); const W = 760, H = W * 297 / 210; g.fillStyle = "#f6f4ef"; g.fillRect(-W / 2, -H / 2, W, H);
      const m = W / 210 * 7; g.fillStyle = "#111"; [[0.045, 0.035], [0.955, 0.035], [0.045, 0.965], [0.955, 0.965]].forEach(([u, v]) => g.fillRect(-W / 2 + u * W - m / 2, -H / 2 + v * H - m / 2, m, m));
      g.font = "30px sans-serif"; g.fillText("E1 · ANSWER SHEET", -W / 2 + 60, -H / 2 + 70); g.fillText("A.1  R0 = 108.2 ohm", -W / 2 + 60, -H / 2 + 200); };
    draw(); setInterval(draw, 100);
    navigator.mediaDevices.getUserMedia = async () => c.captureStream(15);
  });
  await ph.click("#live");
  await ph.waitForSelector(".lv video");
  await ph.waitForFunction(() => /멈추세요|찍는 중/.test((document.querySelector(".lv .msg") || {}).textContent || "") || !document.querySelector(".lv"), null, { timeout: 15000 });
  await ph.screenshot({ path: OUT + "5b-phone-live.png" });
  await ph.waitForSelector("#send", { timeout: 25000 });
  ok(await ph.$(".lv") === null, "live camera: the page was found by its corner squares and taken by itself");
  ok(!/모서리를 확실히 찾지 못했습니다/.test(await ph.textContent("#shot")), "…straightened from the squares, no corner warning");
  await ph.click("#send");
  await ph.waitForFunction(() => /보낸 쪽 · 3/.test(document.body.textContent), null, { timeout: 20000 });
  if (await ph.$(".lv")) await ph.click('.lv [data-x="close"]');                // it opens again for the next page
  const lastId = (await call("GET", "/lab/sessions/" + (await call("GET", "/lab/active", null, TOK))[1].active.id, null, TOK))[1].session.pages.slice(-1)[0].id;
  await ph.click(`[data-del="${lastId}"]`);
  await ph.waitForFunction(() => /보낸 쪽 · 2/.test(document.body.textContent), null, { timeout: 10000 });
  ok(true, "…sent, and taken out again from the phone");

  /* 7. the computer sees the pages, the text is checked and submitted */
  await pg.waitForFunction(() => document.querySelectorAll("#pages .pg").length === 2, null, { timeout: 15000 });
  await pg.waitForSelector("#pages .th img", { timeout: 10000 });
  const kinds = await pg.$$eval("#pages .pg", ps => ps.map(p => [p.querySelector('[data-f="task"]').value, p.querySelector('[data-f="kind"]').value, p.querySelector(".rd").textContent, (p.querySelector(".leg") || {}).textContent]));
  ok(kinds[0][0] === "E1" && kinds[0][1] === "answer" && kinds[1][0] === "E2" && kinds[1][1] === "working" && /A\.1\s*108\.2 ohm/.test(kinds[0][2]) && /잘 읽힘/.test(kinds[0][3]),
    "pages arrive with task, kind, what was read and how legible " + JSON.stringify(kinds.map(k => k.map(x => String(x).slice(0, 30)))));
  ok(await pg.$("#pages textarea") === null && /고칠 수 없습니다/.test(await pg.textContent("#pages")), "nothing to type in: what was read is final");
  await pg.screenshot({ path: OUT + "6-pc-pages.png" });
  await pg.click("#sub"); await pg.click(".modal button.red");
  await pg.waitForSelector(".result", { timeout: 60000 });
  const res = await pg.textContent("main");
  ok(/답안 제출 확인증/.test(res) && /HL-IPHO2024-\d{6}/.test(res) && /\b5\s*\/\s*10\b/.test(res) && /0\.5\s*\/\s*3\.5/.test(res) && /답안지 1쪽/.test(res),
    "receipt: candidate number, pages, E1 5 / 10 (admin rubric), E2 0.5 / 3.5 (scheme drawn from the solution; only a working sheet)");
  await pg.waitForSelector("#medal .lbmedal", { timeout: 8000 }).catch(() => {});
  const md = await pg.$eval("#medal", e => [e.textContent, (e.querySelector(".lbmedal") || {}).dataset]).catch(() => ["", {}]);
  ok(/실험만으로 본 메달권/.test(md[0]) && /IPHO 2024/.test(md[0]) && /135개/.test(md[0]) && md[1] && md[1].medal,
    "receipt: the medal the experiment alone would have earned in 2024 " + JSON.stringify(md[0].slice(0, 120)));
  await pg.screenshot({ path: OUT + "7-result.png" });
  [, act] = await call("GET", "/lab/active", null, TOK);
  ok(act.active === null && act.tokens === 0, "nothing open, 0 tokens");
  await ph.reload(); await sleep(1500);
  ok(/파기/.test(await ph.textContent("body")), "the phone says scanning is over and its link destroyed");

  /* 8. coming back to the exam page now: the intro, no tokens, no start */
  await pg.goto(SITE + "/#/"); await pg.goto(EXAM_URL); await sleep(1500);
  ok(await pg.$("#go") === null && /토큰이 없습니다/.test(await pg.textContent("main")), "after the exam: 0 tokens, cannot start");
  /* 9. the record on the site */
  await pg.goto(SITE + "/#/lab"); await pg.waitForSelector(".arpanel"); await sleep(500);
  ok(/IPHO 2024/.test(await pg.textContent("#arRoot")), "#/lab lists the exam");
  const sid = act && (await call("GET", "/lab/sessions", null, TOK))[1].sessions[0].id;
  await pg.goto(SITE + "/#/lab/" + sid); await pg.waitForSelector(".arpanel"); await sleep(700);
  ok(/E1/.test(await pg.textContent("#arRoot")) && (await pg.$$(".arpanel")).length >= 3, "#/lab/<id> shows each experiment and the pages");
  ok(/성적표/.test(await pg.textContent("#arRoot")) && /HL-IPHO2024-/.test(await pg.textContent("#arRoot")), "#/lab/<id> is a score report with the candidate number");
  ok(await pg.$("#arRoot .lbmedal") !== null, "…with the experiment-only medal estimate");
  const r1 = await pg.$$eval(".arrule", xs => xs.map(x => [x.textContent, x.title]));
  ok(r1.some(([id, ttl]) => id === "R1" && /답안지/.test(ttl)) && /채점 규정/.test(await pg.textContent("#arRoot")), "report: R1 marks on the E2 items, with the rule on hover, and the regulation " + JSON.stringify(r1.slice(0, 2)));
  /* the portal now shows this candidate's status on the exam */
  await pg.goto(SITE + "/#/ipho/exam"); await pg.waitForFunction(() => /채점 완료/.test((document.querySelector("#xmRoot") || {}).textContent || ""), null, { timeout: 8000 });
  const r24 = await pg.$$eval("#xmRoot tbody tr", trs => trs.map(t => t.textContent).find(x => /^2024/.test(x.trim())));
  ok(/채점 완료/.test(r24) && /성적표/.test(r24) && /다시 응시/.test(r24) && /\d+명 응시/.test(r24), "portal row: my status, report, sit again, the number of candidates");
  await pg.screenshot({ path: OUT + "8-lab.png", fullPage: true });
  /* 10. the community's Discord channel */
  await pg.goto(SITE + "/#/community/discord"); await pg.waitForSelector(".dcban", { timeout: 15000 });
  ok(/discord\.gg\/SNBDY5nsgf/.test(await pg.$eval(".dcbody a.join", a => a.href)), "Discord page links the Physics Olympiads invite");
  ok(await pg.$("a.ch.dc") !== null, "Discord channel in the rail");
  await pg.screenshot({ path: OUT + "9-discord.png" });

  ok(errs.length === 0, "no page errors " + JSON.stringify(errs.slice(0, 5)));
  await browser.close();
  console.log(fails ? fails + " FAILED" : "all passed");
  process.exit(fails ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
