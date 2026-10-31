// v11: buying exam tokens (Toss Payments) and earning them from rewarded ads.  Against `npm run dev` with
// test-lab-mock.mjs (its /toss stand-in) and in .dev.vars: TOSS_CLIENT_KEY=test_ck_mock TOSS_SECRET_KEY=test_sk_mock
// TOSS_BASE=http://127.0.0.1:8799/toss ADS_REWARDED_UNIT=test ADS_MIN_SEC=1 ADS_DAILY=3, migration 0010 applied;
// the site on :8765 for the pay.html part.  node test-shop.mjs
import { execSync } from "node:child_process";
const API = process.env.API || "http://127.0.0.1:8787", B = API + "/api", SITE = "http://localhost:8765";
const call = async (m, p, body, tok) => { const r = await fetch(B + p, { method: m, headers: { "Content-Type": "application/json", ...(tok ? { Authorization: "Bearer " + tok } : {}) }, body: body ? JSON.stringify(body) : undefined }); return [r.status, await r.json().catch(() => ({}))]; };
let fails = 0;
const ok = (c, msg) => { if (!c) fails++; console.log((c ? "PASS " : "FAIL ") + msg); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const rnd = Math.random().toString(36).slice(2, 7);
const sign = async u => (await call("POST", "/signup", { username: u + rnd, nickname: u + rnd, password: "password1" }))[1].token;
const sql = q => execSync(`npx wrangler d1 execute haslalab-community --local --command "${q}"`, { cwd: new URL(".", import.meta.url).pathname, stdio: "ignore" });
const tokens = async tok => (await call("GET", "/lab/tokens", null, tok))[1];

const U = await sign("shU"), V = await sign("shV"), A = await sign("shA");
sql(`UPDATE users SET role='admin' WHERE username='shA${rnd}'; DELETE FROM ratelimits`);
let [s, j] = await call("GET", "/pay/config");
ok(s === 200 && j.pay.client_key === "test_ck_mock" && j.pay.packs.length === 3 && j.ads.unit === "/22639388115/rewarded_web_example" && j.ads.daily === 3, "config: the client key and packs, the ad unit (test = Google's sample)");
ok(!JSON.stringify(j).includes("test_sk"), "the secret key never leaves the server");

/* buying */
[s] = await call("POST", "/pay/order", { pack: "t5" });
ok(s === 401, "buying needs a sign-in");
[s, j] = await call("POST", "/pay/order", { pack: "t999" }, U);
ok(s === 400 && j.error === "bad_pack", "an unknown pack is refused");
[s, j] = await call("POST", "/pay/order", { pack: "t5" }, U);
const o1 = j;
ok(s === 200 && /^HL[0-9a-z]{8,9}[0-9A-Za-z]{21,22}$/.test(o1.order_id) && o1.amount === 7900 && o1.tokens === 5, "an order: id (time + random), 7,900 KRW for 5 tokens " + JSON.stringify(o1));
const t0 = (await tokens(U)).tokens;
[s, j] = await call("POST", "/pay/confirm", { paymentKey: "pk_" + rnd, orderId: o1.order_id, amount: 100 }, U);
ok(s === 400 && j.error === "amount_mismatch" && (await tokens(U)).tokens === t0, "an amount changed in the browser (100 for 7,900) is refused, nothing added");
[s, j] = await call("POST", "/pay/confirm", { paymentKey: "pk_" + rnd, orderId: o1.order_id, amount: 7900 }, U);
ok(s === 409 && j.error === "order_failed", "…and that order is dead");
[, j] = await call("POST", "/pay/order", { pack: "t5" }, U);
const o2 = j;
[s, j] = await call("POST", "/pay/confirm", { paymentKey: "pk2_" + rnd, orderId: o2.order_id, amount: 7900 }, V);
ok(s === 404, "another user cannot confirm my order");
const both = await Promise.all([1, 2].map(() => call("POST", "/pay/confirm", { paymentKey: "pk2_" + rnd, orderId: o2.order_id, amount: 7900 }, U)));
const after = await tokens(U);
ok(both.every(([st, x]) => st === 200 && x.ok) && after.tokens === t0 + 5, "paid: 5 tokens added once, though confirmed twice at the same moment " + JSON.stringify([t0, after.tokens]));
ok(after.ledger.filter(x => x.reason === "purchase").length === 1 && after.ledger[0].delta === 5, "one 'purchase' line in the token history");
[s, j] = await call("POST", "/pay/confirm", { paymentKey: "pk2_" + rnd, orderId: o2.order_id, amount: 7900 }, U);
ok(s === 200 && j.tokens === t0 + 5, "pay.html reloaded: the same answer, nothing more");
[, j] = await call("POST", "/pay/order", { pack: "t1" }, U);
[s, j] = await call("POST", "/pay/confirm", { paymentKey: "fail_" + rnd, orderId: j.order_id, amount: 1900 }, U);
ok(s === 402 && j.error === "pay_failed" && /한도초과/.test(j.message) && (await tokens(U)).tokens === t0 + 5, "a card refused by Toss: an error with Toss's message, nothing added");
[, j] = await call("POST", "/pay/order", { pack: "t1" }, U);
[s, j] = await call("POST", "/pay/confirm", { paymentKey: "dup_" + rnd, orderId: j.order_id, amount: 1900 }, U);
ok(s === 200 && j.tokens === t0 + 6, "Toss says it was confirmed already: looked up, found done, 1 token added");
[, j] = await call("GET", "/pay/orders", null, U);
ok(j.orders.filter(x => x.status === "done").length === 2 && j.orders.some(x => x.status === "failed"), "my orders: two paid, the failed ones listed");
/* a refund by an admin: Toss cancels, the unspent tokens go back */
[s] = await call("POST", `/admin/pay/${o2.order_id}/cancel`, { reason: "test" }, U);
ok(s === 403, "only admins refund");
[s, j] = await call("POST", `/admin/pay/${o2.order_id}/cancel`, { reason: "보호자 동의 없음" }, A);
const afterCancel = await tokens(U);
ok(s === 200 && afterCancel.tokens === t0 + 1 && afterCancel.ledger[0].reason === "cancel" && afterCancel.ledger[0].delta === -5, "refunded: the 5 tokens taken back " + JSON.stringify([afterCancel.tokens, afterCancel.ledger[0]]));
[s] = await call("POST", `/admin/pay/${o2.order_id}/cancel`, {}, A);
ok(s === 409, "a refunded order cannot be refunded again");

/* rewarded ads: a third of a token each, three a day */
const W = await sign("shW"), w0 = (await tokens(W)).tokens;
[s, j] = await call("POST", "/ads/start", null, W);
ok(s === 200 && j.nonce && j.left === 3, "an ad started: a one-time number, 3 left today");
let n1 = j.nonce;
[s, j] = await call("POST", "/ads/claim", { nonce: n1 }, W);
ok(s === 409 && j.error === "too_soon", "claimed at once → too soon (an ad takes time)");
await sleep(1200);
[s, j] = await call("POST", "/ads/claim", { nonce: n1 }, V);
ok(s === 404, "someone else cannot claim my ad");
const dbl = await Promise.all([1, 2].map(() => call("POST", "/ads/claim", { nonce: n1 }, W)));
ok(dbl.filter(([st]) => st === 200).length === 1 && dbl.some(([st, x]) => st === 409 && x.error === "already_granted") && (await tokens(W)).parts === 1, "claimed twice at once: one third given, the other told it was granted already " + JSON.stringify(dbl.map(([st, x]) => [st, x.error || x.parts])));
for (let i = 0; i < 2; i++) { [, j] = await call("POST", "/ads/start", null, W); const n = j.nonce; await sleep(1100); [s, j] = await call("POST", "/ads/claim", { nonce: n }, W); }
const ww = await tokens(W);
ok(s === 200 && j.parts === 0 && j.tokens === w0 + 1 && ww.ledger[0].reason === "ad" && ww.parts === 0, "three ads → one token, the thirds back to 0 " + JSON.stringify(j));
[s, j] = await call("POST", "/ads/start", null, W);
ok(s === 429 && j.error === "ads_daily" && j.daily === 3, "a fourth ad today is refused");
[s, j] = await call("POST", "/ads/claim", { nonce: "nope" }, W);
ok(s === 404, "an unknown number claims nothing");

/* pay.html: Toss sends the buyer back with paymentKey, orderId and amount */
const { chromium } = (await import("node:module")).createRequire(import.meta.url)("playwright");   // installed globally, found by require
const br = await chromium.launch(), ctx = await br.newContext();
await ctx.addInitScript(([api, tok]) => { localStorage.setItem("hlCmApi", api); localStorage.setItem("hlCmTok", tok); localStorage.setItem("hlLang", "ko"); }, [API, U]);
const pg = await ctx.newPage(), errs = []; pg.on("pageerror", e => errs.push(e.message));
[, j] = await call("POST", "/pay/order", { pack: "t12" }, U);
const before = (await tokens(U)).tokens;
await pg.goto(`${SITE}/pay.html?paymentKey=pk3_${rnd}&orderId=${j.order_id}&amount=15900`);
await pg.waitForSelector("h1.ok, h1.bad", { timeout: 15000 });
ok(/결제가 완료/.test(await pg.textContent("h1")) && /토큰 12개/.test(await pg.textContent("#box")) && (await tokens(U)).tokens === before + 12, "pay.html: confirmed, 12 tokens added, shown");
ok(!/paymentKey/.test(pg.url()), "the payment key is taken out of the address bar");
await pg.goto(`${SITE}/pay.html?code=PAY_PROCESS_CANCELED&message=x`);
await pg.waitForSelector("h1.bad");
ok(/취소/.test(await pg.textContent("#box")), "pay.html: a cancelled payment says so");
/* the shop on #/lab */
await pg.goto(SITE + "/#/lab"); await pg.waitForSelector("#lbShop", { timeout: 15000 });
if (await pg.$("#lbShop [data-tab='t']")) await pg.click("#lbShop [data-tab='t']");      // with Paddle configured too, the KRW packs are the second tab
const rows = await pg.$$eval("#lbShop [data-pack]", b => b.map(x => x.textContent.replace(/\s+/g, " ").trim()));
ok(rows.length === 3 && /5 ?토큰/.test(rows[1]) && /7,900원/.test(rows[1]) && await pg.isVisible("#lbShop [data-pack='t5']") && await pg.$("#lbAd") !== null && /광고 1편 = 토큰 1\/3/.test(await pg.textContent("#lbShop")), "#/lab: three packs, the consent line and the ad button " + rows.join(" | "));
ok(await pg.textContent("#lbTotal") === "7,900원" && /토스페이먼츠/.test(await pg.textContent("#lbFine")), "the KRW tab: its own total and terms");
await pg.click("#lbShop [data-pack='t1']");
ok(await pg.textContent("#lbTotal") === "1,900원", "picking the 1-token pack changes the total");
await pg.click("#lbPay");
ok(/동의/.test(await pg.textContent("#lbShopMsg")), "paying without ticking the consent line is stopped");
ok(errs.length === 0, "no page errors " + JSON.stringify(errs));
await br.close();
console.log(fails ? fails + " FAILED" : "all passed");
process.exit(fails ? 1 : 0);
