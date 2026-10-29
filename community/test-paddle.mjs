// v11: buying exam tokens with Paddle (USD).  Against `npm run dev` with test-lab-mock.mjs (its /paddle stand-in of
// Paddle's API) and in .dev.vars: PADDLE_CLIENT_TOKEN=test_mockclienttoken PADDLE_API_KEY=pdl_mock
// PADDLE_WEBHOOK_SECRET=pdl_ntfset_mocksecret PADDLE_BASE=http://127.0.0.1:8799/paddle
// PADDLE_PACKS=[{"id":"p1","tokens":1,"price_id":"pri_01mockone","usd":1.49},{"id":"p5","tokens":5,"price_id":"pri_01mockfive","usd":5.99}]
// migration 0010 applied; the site on :8765.  node test-paddle.mjs
import { execSync } from "node:child_process";
import { createHmac } from "node:crypto";
const API = process.env.API || "http://127.0.0.1:8787", B = API + "/api", SITE = "http://localhost:8765", MOCK = "http://127.0.0.1:8799";
const SECRET = "pdl_ntfset_mocksecret";
const call = async (m, p, body, tok) => { const r = await fetch(B + p, { method: m, headers: { "Content-Type": "application/json", ...(tok ? { Authorization: "Bearer " + tok } : {}) }, body: body ? JSON.stringify(body) : undefined }); return [r.status, await r.json().catch(() => ({}))]; };
let fails = 0;
const ok = (c, msg) => { if (!c) fails++; console.log((c ? "PASS " : "FAIL ") + msg); };
const rnd = Math.random().toString(36).slice(2, 7);
const sign = async u => (await call("POST", "/signup", { username: u + rnd, nickname: u + rnd, password: "password1" }))[1].token;
const sql = q => execSync(`npx wrangler d1 execute haslalab-community --local --command "${q}"`, { cwd: new URL(".", import.meta.url).pathname, stdio: "ignore" });
const tokens = async tok => (await call("GET", "/lab/tokens", null, tok))[1];
/* a webhook as Paddle sends it: the raw body signed with HMAC-SHA256 over "ts:body" */
const hook = async (ev, { secret = SECRET, ts = Math.floor(Date.now() / 1000) } = {}) => {
  const raw = JSON.stringify(ev), h1 = createHmac("sha256", secret).update(ts + ":" + raw).digest("hex");
  const r = await fetch(B + "/pay/paddle/webhook", { method: "POST", headers: { "Content-Type": "application/json", "Paddle-Signature": `ts=${ts};h1=${h1}` }, body: raw });
  return r.status;
};
const txn = (id, order, price, status = "completed") => ({ id, status, custom_data: { order_id: order }, items: [{ price: { id: price }, quantity: 1 }], details: { totals: { total: "599", currency_code: "USD" } } });

const U = await sign("pdU"), A = await sign("pdA");
sql(`UPDATE users SET role='admin' WHERE username='pdA${rnd}'; DELETE FROM ratelimits`);
let [s, j] = await call("GET", "/pay/config");
ok(s === 200 && j.paddle && j.paddle.token === "test_mockclienttoken" && j.paddle.env === "sandbox" && j.paddle.packs.length === 2 && j.paddle.packs[1].usd === 5.99, "config: Paddle's client token (sandbox, from test_…) and its packs");
ok(!/pdl_mock|ntfset/.test(JSON.stringify(j)), "the API key and the webhook secret never leave the server");

/* 1. the webhook adds the tokens */
[s, j] = await call("POST", "/pay/order", { pack: "p5", provider: "paddle" }, U);
const o1 = j;
ok(s === 200 && o1.price_id === "pri_01mockfive" && o1.tokens === 5 && /^HL/.test(o1.order_id), "a Paddle order: our id, the pack's Paddle price " + JSON.stringify(o1));
const t0 = (await tokens(U)).tokens;
const ev1 = { event_type: "transaction.completed", event_id: "evt_1" + rnd, data: txn("txn_01hv8wptq8987qa" + rnd, o1.order_id, "pri_01mockfive") };
ok(await hook(ev1, { secret: "wrong" }) === 401 && (await tokens(U)).tokens === t0, "a webhook with a wrong signature → 401, nothing added");
ok(await hook(ev1, { ts: Math.floor(Date.now() / 1000) - 3600 }) === 401, "…an old one (replayed an hour later) → 401");
ok(await hook({ ...ev1, data: txn("txn_01hv8wptq8987qb" + rnd, o1.order_id, "pri_01mockone") }) === 200 && (await tokens(U)).tokens === t0, "a transaction for another price does not pay this order");
ok(await hook(ev1) === 200 && (await tokens(U)).tokens === t0 + 5, "the signed transaction.completed → 5 tokens");
ok(await hook(ev1) === 200 && await hook({ ...ev1, event_type: "transaction.paid" }) === 200 && (await tokens(U)).tokens === t0 + 5, "the same event again, and transaction.paid after it: nothing more");
ok((await tokens(U)).ledger[0].reason === "purchase" && (await tokens(U)).ledger[0].delta === 5, "one 'purchase' line");

/* 2. pay.html asks before the webhook: the server looks the transaction up with Paddle */
[, j] = await call("POST", "/pay/order", { pack: "p1", provider: "paddle" }, U);
const o2 = j, tx2 = "txn_01hv8wptq8987qc" + rnd;
await fetch(MOCK + "/paddle/txn", { method: "POST", body: JSON.stringify(txn(tx2, o2.order_id, "pri_01mockone", "billed")) });
[s, j] = await call("POST", "/pay/paddle/check", { orderId: o2.order_id, txn: tx2 }, U);
ok(s === 200 && j.status === "ready", "the transaction is not paid yet: the order waits");
await fetch(MOCK + "/paddle/txn", { method: "POST", body: JSON.stringify(txn("txn_01hv8wptq8987qd" + rnd, o1.order_id, "pri_01mockone")) });
[s, j] = await call("POST", "/pay/paddle/check", { orderId: o2.order_id, txn: "txn_01hv8wptq8987qd" + rnd }, U);
ok(s === 200 && j.status === "ready", "another order's transaction does not pay this one");
await fetch(MOCK + "/paddle/txn", { method: "POST", body: JSON.stringify(txn(tx2, o2.order_id, "pri_01mockone")) });
const V = await sign("pdV");
[s] = await call("POST", "/pay/paddle/check", { orderId: o2.order_id, txn: tx2 }, V);
ok(s === 404, "someone else cannot check my order");
[s, j] = await call("POST", "/pay/paddle/check", { orderId: o2.order_id, txn: tx2 }, U);
ok(s === 200 && j.status === "done" && j.tokens === t0 + 6, "completed now: looked up with Paddle, 1 token added " + JSON.stringify([s, j, t0]));
ok(await hook({ event_type: "transaction.completed", data: txn(tx2, o2.order_id, "pri_01mockone") }) === 200 && (await tokens(U)).tokens === t0 + 6, "the webhook arriving afterwards adds nothing");

/* 3. refunds: from our admin page (Paddle refund adjustment) and approved in Paddle's own dashboard (webhook) */
[s] = await call("POST", `/admin/pay/${o1.order_id}/cancel`, { reason: "test" }, U);
ok(s === 403, "only admins refund");
const r0 = (await (await fetch(MOCK + "/seen")).json()).refunds || 0;
[s, j] = await call("POST", `/admin/pay/${o1.order_id}/cancel`, { reason: "requested within 14 days" }, A);
const tk = await tokens(U);
ok(s === 200 && (await (await fetch(MOCK + "/seen")).json()).refunds === r0 + 1 && tk.tokens === t0 + 1 && tk.ledger[0].reason === "cancel" && tk.ledger[0].delta === -5, "admin refund: a Paddle refund adjustment, the 5 tokens taken back");
ok(await hook({ event_type: "adjustment.updated", data: { action: "refund", status: "approved", transaction_id: tx2 } }) === 200 && (await tokens(U)).tokens === t0, "a refund approved in Paddle's dashboard: that order's token taken back");
ok(await hook({ event_type: "adjustment.updated", data: { action: "refund", status: "approved", transaction_id: tx2 } }) === 200 && (await tokens(U)).tokens === t0, "…once");
[, j] = await call("GET", "/pay/orders", null, U);
ok(j.orders.filter(x => x.provider === "paddle" && x.status === "canceled").length === 2 && j.orders[0].currency === "USD", "my orders: both refunded, in USD");

/* 4. pay.html after Paddle's checkout, and the shop on #/lab */
const { chromium } = (await import("node:module")).createRequire(import.meta.url)("playwright");
const br = await chromium.launch(), ctx = await br.newContext();
await ctx.addInitScript(([api, tok]) => { localStorage.setItem("hlCmApi", api); localStorage.setItem("hlCmTok", tok); localStorage.setItem("hlLang", "ko"); }, [API, U]);
const pg = await ctx.newPage(), errs = []; pg.on("pageerror", e => errs.push(e.message));
[, j] = await call("POST", "/pay/order", { pack: "p5", provider: "paddle" }, U);
const tx3 = "txn_01hv8wptq8987qe" + rnd, before = (await tokens(U)).tokens;
await fetch(MOCK + "/paddle/txn", { method: "POST", body: JSON.stringify(txn(tx3, j.order_id, "pri_01mockfive")) });
await pg.goto(`${SITE}/pay.html?paddle=1&order=${j.order_id}&txn=${tx3}`);
await pg.waitForSelector("h1.ok, h1.bad", { timeout: 20000 });
ok(/결제가 완료/.test(await pg.textContent("h1")) && /토큰 5개/.test(await pg.textContent("#box")) && (await tokens(U)).tokens === before + 5, "pay.html (Paddle): checked, 5 tokens added, shown");
await pg.goto(SITE + "/#/lab"); await pg.waitForSelector("#lbShop", { timeout: 15000 });
const rows = await pg.$$eval("#lbShop [data-ppack]", b => b.map(x => [x.dataset.ppack, x.textContent.replace(/\s+/g, " ").trim(), x.getAttribute("aria-pressed")]));
ok(rows.length === 2 && /5 ?토큰/.test(rows[1][1]) && /\$5\.99/.test(rows[1][1]) && /개당 \$1\.20/.test(rows[1][1]) && /20% 절약/.test(rows[1][1]) && /Paddle/.test(await pg.textContent("#lbShop")), "#/lab: the Paddle packs in USD, the price per token and the saving " + JSON.stringify(rows));
ok(rows[1][2] === "true" && await pg.textContent("#lbTotal") === "$5.99" && /\$5\.99 결제하기/.test(await pg.textContent("#lbPay")), "the middle pack is picked; one total and one pay button");
const tabs = await pg.$$eval("#lbShop [data-tab]", b => b.map(x => x.dataset.tab + ":" + x.getAttribute("aria-selected")));
ok(tabs.length === 0 || tabs[0] === "p:true", "with Toss configured too, the USD tab comes first " + tabs.join());
await pg.click("#lbShop [data-ppack='p1']");
ok(await pg.textContent("#lbTotal") === "$1.49" && /\$1\.49/.test(await pg.textContent("#lbPay")) && await pg.getAttribute("#lbShop [data-ppack='p1']", "aria-pressed") === "true", "picking the 1-token pack changes the total");
await pg.click("#lbPay");
ok(/동의/.test(await pg.textContent("#lbShopMsg")), "paying without ticking the consent line is stopped");
ok(errs.length === 0, "no page errors " + JSON.stringify(errs));
await br.close();
console.log(fails ? fails + " FAILED" : "all passed");
process.exit(fails ? 1 : 0);
