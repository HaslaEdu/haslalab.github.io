// the live nickname check (sign-up, community account, #/me) and cropping the profile picture, in a browser
// (Playwright).  Needs `npm run dev` and the site at http://localhost:8765, then:  node test-profile-browser.cjs
const { chromium } = require("playwright");
const SITE = "http://localhost:8765", API = "http://127.0.0.1:8787";
let fails = 0;
const ok = (c, m) => { if (!c) fails++; console.log((c ? "PASS " : "FAIL ") + m); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const call = async (m, p, body, tok) => { const r = await fetch(API + "/api" + p, { method: m, headers: { "Content-Type": "application/json", ...(tok ? { Authorization: "Bearer " + tok } : {}) }, body: body ? JSON.stringify(body) : undefined }); return [r.status, await r.json()]; };

(async () => {
  const r = Math.random().toString(36).slice(2, 6);
  const [, other] = await call("POST", "/signup", { username: "pfo" + r, nickname: "Taken" + r, password: "password1" });
  const browser = await chromium.launch(), errs = [];
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  await ctx.addInitScript(api => { if (!sessionStorage.getItem("s")) { sessionStorage.setItem("s", 1); localStorage.setItem("hlCmApi", api); localStorage.removeItem("hlCmTok"); localStorage.setItem("hlLang", "ko"); } }, API);
  const pg = await ctx.newPage(); pg.on("pageerror", e => errs.push(e.message));

  /* sign-up: the nickname is checked while it is typed */
  await pg.goto(SITE + "/#/signup"); await pg.waitForSelector("#cmS");
  await pg.fill("#cmS [name=nickname]", "taken" + r);
  await pg.waitForFunction(() => /이미 쓰고 있는/.test(document.querySelector("#cmSnick").textContent), null, { timeout: 5000 });
  ok(await pg.$eval("#cmSnick", e => e.classList.contains("no")), "sign-up: a taken name (other case) is flagged while typing");
  await pg.fill("#cmS [name=username]", "pfa" + r);
  await pg.fill("#cmS [name=password]", "password1"); await pg.fill("#cmS [name=password2]", "password1"); await pg.check("#cmS [name=agree]");
  await pg.click("#cmS button[type=submit]"); await sleep(800);
  ok(/#\/signup/.test(pg.url()) && /이미 쓰고 있는/.test(await pg.textContent("#cmS .cmerr")), "…and the form is not sent");
  await pg.fill("#cmS [name=nickname]", "Fresh" + r);
  await pg.waitForFunction(() => /쓸 수 있는/.test(document.querySelector("#cmSnick").textContent), null, { timeout: 5000 });
  ok(true, "a free name says so");
  await pg.click("#cmS button[type=submit]");
  await pg.waitForFunction(() => !!localStorage.getItem("hlCmTok"), null, { timeout: 8000 });
  ok(true, "signed up with the free name");

  /* community account: rename with the same check */
  await pg.goto(SITE + "/#/community/account"); await pg.waitForSelector("#cmNick");
  await pg.fill("#cmNick [name=nickname]", "TAKEN" + r); await sleep(700);
  ok(await pg.$eval("#cmNick .cmnick", e => e.classList.contains("no")), "account: a taken name is flagged");
  await pg.click("#cmNick button[type=submit]"); await sleep(600);
  ok(/이미 쓰고 있는/.test(await pg.textContent("#cmNick .cmerr")), "…and refused");
  await pg.fill("#cmNick [name=nickname]", "Renamed" + r); await sleep(700);
  await pg.click("#cmNick button[type=submit]"); await sleep(900);
  ok(/바꿨습니다/.test(await pg.textContent("#cmNick .cmerr")) && (await pg.textContent(".cmpost h2")) === "Renamed" + r, "account: renamed, the heading follows");

  /* the uploaded picture's pixels, read on a page opened at its own address (the site may not read another origin's pixels) */
  const avatarPx = async (pts) => {
    const tok = await pg.evaluate(() => localStorage.getItem("hlCmTok"));
    const [, me] = await call("GET", "/me", null, tok);
    const p2 = await ctx.newPage(); await p2.goto(API + "/api/avatar/" + me.user.avatar);
    const out = await p2.evaluate(async (pts) => { const img = document.querySelector("img"); await img.decode();
      const c = document.createElement("canvas"); c.width = img.naturalWidth; c.height = img.naturalHeight; const g = c.getContext("2d"); g.drawImage(img, 0, 0);
      const o = { w: c.width }; for (const [k, x, y] of pts) o[k] = [...g.getImageData(x, y, 1, 1).data.slice(0, 3)]; return o; }, pts);
    await p2.close(); return out;
  };
  /* the profile picture: half red, half blue, 800×400 */
  const png = await pg.evaluate(() => { const c = document.createElement("canvas"); c.width = 800; c.height = 400; const g = c.getContext("2d");
    g.fillStyle = "#ff0000"; g.fillRect(0, 0, 400, 400); g.fillStyle = "#0000ff"; g.fillRect(400, 0, 400, 400); return c.toDataURL("image/png").split(",")[1]; });
  const pick = () => pg.setInputFiles("#cmAvatar input[type=file]", { name: "p.png", mimeType: "image/png", buffer: Buffer.from(png, "base64") });
  /* cancel uploads nothing */
  await pick(); await pg.waitForSelector(".cmcrop canvas");
  ok(/원본 800×400px · 400×400px → 올라가는 크기 256×256px/.test(await pg.textContent(".cmcrop .meta")), "crop dialog shows the sizes: " + await pg.textContent(".cmcrop .meta"));
  await pg.click(".cmcrop [data-no]"); await sleep(400);
  const [, me0] = await call("GET", "/me", null, await pg.evaluate(() => localStorage.getItem("hlCmTok")));
  ok(!(await pg.$(".cmcrop")) && !me0.user.avatar, "cancel: closed, nothing uploaded");
  /* zoom 2× with the slider: the kept square halves */
  await pick(); await pg.waitForSelector(".cmcrop canvas");
  await pg.$eval(".cmcrop input[type=range]", e => { e.value = "2"; e.dispatchEvent(new Event("input")); });
  ok(/200×200px/.test(await pg.textContent(".cmcrop .meta")), "zoom 2× keeps a 200×200 square");
  await pg.click(".cmcrop [data-reset]");
  /* drag the picture right as far as it goes: the square moves onto the red half */
  const b = await (await pg.$(".cmcrop canvas")).boundingBox();
  await pg.mouse.move(b.x + b.width / 2, b.y + b.height / 2); await pg.mouse.down();
  await pg.mouse.move(b.x + b.width * 1.4, b.y + b.height / 2, { steps: 8 }); await pg.mouse.up();
  await pg.click(".cmcrop [data-ok]");
  await pg.waitForFunction(() => !document.querySelector(".cmcrop") && document.querySelector("#cmAvBox img"), null, { timeout: 8000 });
  const px = await avatarPx([["l", 40, 128], ["r", 216, 128]]);
  ok(px.w === 256, "uploaded at 256×256");
  ok(px.l[0] > 200 && px.l[2] < 60 && px.r[0] > 200 && px.r[2] < 60, "dragged onto the red half: the whole picture is red " + JSON.stringify(px));
  /* the same picture, not moved: half and half */
  await pick(); await pg.waitForSelector(".cmcrop canvas"); await pg.click(".cmcrop [data-ok]");
  await sleep(1500);
  const px2 = await avatarPx([["l", 40, 128], ["r", 216, 128]]);
  ok(px2.l[0] > 200 && px2.r[2] > 200, "not moved: the middle square, red on the left and blue on the right " + JSON.stringify(px2));
  /* rotate a quarter: red on top, blue below */
  await pick(); await pg.waitForSelector(".cmcrop canvas"); await pg.click(".cmcrop [data-rot]"); await pg.click(".cmcrop [data-ok]"); await sleep(1500);
  const px3 = await avatarPx([["top", 128, 40], ["bottom", 128, 216]]);
  ok(px3.top[0] > 200 && px3.bottom[2] > 200, "rotated 90°: red on top, blue below " + JSON.stringify(px3));

  /* #/me: the same live check */
  await pg.goto(SITE + "/#/me"); await pg.waitForSelector("#arNick");
  await pg.fill("#arNick [name=n]", "taken" + r); await sleep(700);
  ok(await pg.$eval("#arNick .cmnick", e => e.classList.contains("no")), "#/me: a taken name is flagged");
  await pg.click("#arNick button"); await sleep(600);
  ok(/이미 쓰고 있는/.test(await pg.textContent("#arNick .arinfo")), "#/me: …and refused");

  ok(errs.length === 0, "no page errors " + JSON.stringify(errs.slice(0, 3)));
  await browser.close();
  console.log(fails ? fails + " FAILED" : "all passed");
  process.exit(fails ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });
