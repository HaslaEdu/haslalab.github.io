// Real Worker routes and transactional SQLite. All payment/queue endpoints are local stand-ins.
import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync, readdirSync } from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import worker from './src/index.js';
import { tokenUnits, tokenBalance } from './src/lab-tokens.js';
import { LAB_PAIR_CATALOGUE, LAB_MIXED_CATALOGUE } from './src/lab-pair-catalog.js';

const sql = new DatabaseSync(':memory:');
for (const file of readdirSync(new URL('./migrations/', import.meta.url)).filter(n => /^\d{4}_.*\.sql$/.test(n)).sort())
  sql.exec(readFileSync(new URL('./migrations/' + file, import.meta.url), 'utf8'));
let failCharge = false;
const DB = {
  prepare(query) {
    const st = sql.prepare(query), make = args => ({ query, bind: (...bound) => make(bound),
      async first() { return st.get(...args) || null; }, async all() { return { results: st.all(...args) }; },
      async run() { return this.executeSync(); }, executeSync() {
        if (st.columns().length) return { results: st.all(...args) };
        const r = st.run(...args); return { success: true, meta: { changes: r.changes, last_row_id: Number(r.lastInsertRowid) } };
      } }); return make([]);
  },
  async batch(statements) {
    sql.exec('BEGIN');
    try {
      const results = statements.map((s, i) => { const r = s.executeSync();
        if (failCharge && i === 0 && s.query.includes('WITH other AS')) { failCharge = false; throw Error('local transaction interruption'); }
        return r; }); sql.exec('COMMIT'); return results;
    } catch (e) { sql.exec('ROLLBACK'); throw e; }
  },
};
const time = Math.floor(Date.now() / 1000), auth = {};
for (let id = 1; id <= 80; id++) {
  sql.prepare("INSERT INTO users(id,username,nickname,pw,role,created_at) VALUES(?,?,?,'unused',?,?)")
    .run(id, 'price' + id, 'Price ' + id, id === 1 ? 'admin' : 'user', time);
  auth[id] = ('local_price_' + id).padEnd(48, 'x');
  const hash = Buffer.from(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(auth[id]))).toString('base64url');
  sql.prepare('INSERT INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)').run(hash, id, time, time + 3600);
}
const env = { DB,GEMINI_API_KEY:'local-selected-provider-no-AI', LAB_JOBS: { async sendBatch() {} }, LAB_KEEP_HOURS: 'off', ADS_REWARDED_UNIT: 'test', ADS_MIN_SEC: '0', ADS_DAILY: '10', TOSS_BASE: 'https://payments.test', TOSS_SECRET_KEY: 'local-stand-in' };
globalThis.caches = { default: { async match() {}, async put() {} } };
const originalFetch = globalThis.fetch;
let paymentCalls = 0;
globalThis.fetch = async (url, options) => {
  assert.match(String(url), /^https:\/\/payments\.test\/v1\/payments\/local_key\/cancel$/);
  assert.equal(options.method, 'POST'); paymentCalls++;
  return Response.json({ status: 'CANCELED' });
};
test.after(() => { globalThis.fetch = originalFetch; sql.close(); });
async function api(path, body, user = 1, settings = env) {
  if(body&&/^\/lab\/(?:start|sessions\/\d+\/(?:pay|submit))$/.test(path))body={provider:'gemini',...body};
  const r = await worker.fetch(new Request('https://worker.local/api' + path, {
    method: body === undefined ? 'GET' : 'POST', headers: { Authorization: 'Bearer ' + auth[user], ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  }), settings); return { status: r.status, data: await r.json() };
}
const balance = user => tokenBalance(sql.prepare('SELECT exam_tokens,exam_half FROM users WHERE id=?').get(user));
const fund = (user, tokens, half = 0) => sql.prepare('UPDATE users SET exam_tokens=?,exam_half=? WHERE id=?').run(tokens, half, user);
const paidLedger = id => sql.prepare("SELECT * FROM lab_ledger WHERE session_id=? AND reason='grade'").all(id);
function seed(user, { tasks = ['T1'], theory = tasks.filter(t => t.startsWith('T')), pair = false, review = false, comp = 'ipho', year = 2024, key = comp + year, charged = 0, pricing } = {}) {
  const sources = {_provider:'gemini',...Object.fromEntries(tasks.map(task => [task, { ...(theory.includes(task) ? { kind: 'theory' } : {}), sol: `IPhO_${year}_${task}S.pdf` }]))};
  if (pair) sources._half = 1; if (review) sources._review = 1; if (pricing) sources._pricing = pricing;
  const id = Number(sql.prepare(`INSERT INTO lab_sessions(user_id,comp,year,exam_key,tasks,sources,started_at,ended_at,scan_until,upload_hash,status,charged,created_at)
    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)`).run(user, comp, year, key, JSON.stringify(tasks), JSON.stringify(sources), time, time + 3600, time + 5400, crypto.randomUUID(), review ? 'scanning' : 'running', charged, time).lastInsertRowid);
  if (review) sql.prepare("INSERT INTO lab_pages(session_id,no,task,kind,mime,data,ocr,text,edited,ocr_status,created_at) VALUES(?,1,?,'answer','text/plain',X'','Local answer','Local answer',1,'done',?)").run(id, tasks[0], time);
  return id;
}
async function pay(id, user) {
  const r = await api(`/lab/sessions/${id}/pay`, {}, user);
  if (r.status === 200) sql.prepare("UPDATE lab_sessions SET status='pending' WHERE id=?").run(id);
  return r;
}
const full = LAB_PAIR_CATALOGUE.ipho['2024'][0];
const theory = full.theory[0], lab = full.lab[0];

test('tenths are exact; old whole+half balances stay intact without a migration', async () => {
  for (const [n, u] of [[0, 0], [0.2, 2], [0.3, 3], [0.5, 5], [5.2, 52]]) assert.equal(tokenUnits(n), u);
  for (const n of [0.03, 0.333, NaN, Infinity, '0.3', null]) assert.equal(tokenUnits(n), null);
  fund(2, 5, 1);
  assert.equal((await api('/lab/tokens', undefined, 2)).data.tokens, 5.5);
  assert.equal((await api('/lab/bootstrap', undefined, 2)).data.tokens, 5.5);
  assert.equal(sql.prepare('SELECT exam_half FROM users WHERE id=2').get().exam_half, 1, 'reads never consume the legacy half');
  const r = await pay(seed(2), 2); assert.equal(r.status, 200, JSON.stringify(r.data)); assert.equal(r.data.tokens, 5.2);
  assert.equal(r.data.session.cost, 0.3); assert.equal(r.data.session.pricing_version, 2);
  assert.deepEqual({ ...sql.prepare('SELECT exam_tokens,exam_half FROM users WHERE id=2').get() }, { exam_tokens: 5.2, exam_half: 0 });
  assert.equal(paidLedger(r.data.session.id)[0].delta, -0.3);
});

test('a full theory+experiment set costs 0.3+0.2 and records its exact complementary session', async () => {
  fund(3, 1);
  const first = seed(3, { tasks: theory, pair: true }), a = await pay(first, 3);
  const second = seed(3, { tasks: lab, pair: true }), b = await pay(second, 3);
  assert.equal(a.data.tokens, 0.7); assert.equal(b.data.tokens, 0.5); assert.equal(b.data.session.cost, 0.2);
  assert.equal(b.data.session.paired_with, first); assert.equal(b.data.session.discount, 0.1); assert.equal(b.data.session.pair_mixed_mode, false);
  const note = JSON.parse(paidLedger(second)[0].note);
  assert.equal(note.pair_profile, full.id); assert.equal(note.paired_with, first); assert.equal(note.units, 2);
  const retry = await pay(second, 3); assert.equal(retry.data.tokens, 0.5); assert.equal(paidLedger(second).length, 1);
  const third = await pay(seed(3, { tasks: lab, pair: true }), 3); assert.equal(third.data.session.cost, 0.3); assert.equal(third.data.tokens, 0.2);
});

test('reverse order and cross-mode pairs work while comparison cohorts remain unchanged', async () => {
  fund(4, 1);
  const first = seed(4, { tasks: lab, pair: true, review: true }); assert.equal((await pay(first, 4)).data.tokens, 0.7);
  const last = seed(4, { tasks: theory, pair: true }); const r = await pay(last, 4);
  assert.equal(r.data.tokens, 0.5); assert.equal(r.data.session.paired_with, first); assert.equal(r.data.session.pair_mixed_mode, true);
  assert.equal(r.data.session.review_only, false);
});

test('simultaneous complementary payments share one discount and never reuse a paid partner', async () => {
  fund(25, 2);
  const a = seed(25, { tasks: theory, pair: true }); sql.prepare("UPDATE lab_sessions SET status='ended' WHERE id=?").run(a);
  const b = seed(25, { tasks: lab, pair: true }); sql.prepare("UPDATE lab_sessions SET status='ended' WHERE id=?").run(b);
  const results = await Promise.all([pay(a, 25), pay(b, 25)]);
  assert.ok(results.every(r => r.status === 200), JSON.stringify(results)); assert.equal(balance(25), 1.5);
  assert.deepEqual(results.map(r => r.data.session.cost).sort(), [0.2, 0.3]);
  fund(26, 2); const first = seed(26, { tasks: theory, pair: true }); await pay(first, 26);
  const c = seed(26, { tasks: lab, pair: true }); sql.prepare("UPDATE lab_sessions SET status='ended' WHERE id=?").run(c);
  const d = seed(26, { tasks: lab, pair: true }); sql.prepare("UPDATE lab_sessions SET status='ended' WHERE id=?").run(d);
  const competing = await Promise.all([pay(c, 26), pay(d, 26)]);
  assert.ok(competing.every(r => r.status === 200)); assert.equal(balance(26), 1.2);
  assert.deepEqual(competing.map(r => r.data.session.cost).sort(), [0.2, 0.3]);
  assert.equal(competing.filter(r => r.data.session.paired_with === first).length, 1);
});

test('start, resume, selected GET and bootstrap quote the eligible 0.2 price without spending or reserving tokens', async () => {
  fund(27, 0.5); const first = seed(27, { tasks: theory, pair: true }); await pay(first, 27);
  const request = { comp:'ipho',year:2024,tasks:lab,pair:true,review:true,
    sources:Object.fromEntries(lab.map(task => [task,{sol:`IPhO_2024_S${task.slice(1)}.pdf`}])) };
  const opened = await api('/lab/start', request, 27); assert.equal(opened.status, 200, JSON.stringify(opened.data));
  const id = opened.data.session.id;
  const snapshots = [opened, await api('/lab/start', request, 27), await api('/lab/sessions/' + id, undefined, 27), await api('/lab/sessions/' + id)];
  const boot = await api('/lab/bootstrap?id=' + id, undefined, 27); snapshots.push(boot);
  for (const result of snapshots) {
    assert.equal(result.data.session.cost, 0.2); assert.equal(result.data.session.price_estimate, true);
    assert.equal(result.data.session.paired_with, first); assert.equal(result.data.session.discount, 0.1);
  }
  assert.equal(boot.data.active.cost, 0.2); assert.equal(balance(27), 0.2); assert.equal(paidLedger(id).length, 0);
  assert.equal((await api('/lab/sessions/' + id, undefined, 28)).status, 404);
  await api('/lab/sessions/' + id + '/text', { answers:{[lab[0]]:'Completed answer'} }, 27);
  const paid = await pay(id, 27); assert.equal(paid.status, 200); assert.equal(paid.data.tokens, 0);
  assert.equal(paid.data.session.cost, 0.2); assert.equal(paid.data.session.price_estimate, false);
});

test('a stale quote cannot spend a partner twice or debit an unaffordable full price', async () => {
  fund(28, 0.6); await pay(seed(28, { tasks:theory,pair:true }), 28);
  const a = seed(28, { tasks:lab,pair:true }); sql.prepare("UPDATE lab_sessions SET status='ended' WHERE id=?").run(a);
  const b = seed(28, { tasks:lab,pair:true });
  assert.equal((await api('/lab/sessions/' + a, undefined, 28)).data.session.cost, 0.2);
  assert.equal((await api('/lab/sessions/' + b, undefined, 28)).data.session.cost, 0.2);
  await pay(a, 28); assert.equal(balance(28), 0.1);
  const denied = await pay(b, 28); assert.equal(denied.status, 402); assert.equal(balance(28), 0.1); assert.equal(paidLedger(b).length, 0);
  assert.equal((await api('/lab/sessions/' + b, undefined, 28)).data.session.cost, 0.3);
});

test('a stale 0.2 quote cannot charge 0.3 above the confirmed max_cost even with sufficient balance', async () => {
  fund(29, 2); await pay(seed(29, { tasks:theory,pair:true }), 29);
  const a = seed(29, { tasks:lab,pair:true }); sql.prepare("UPDATE lab_sessions SET status='ended' WHERE id=?").run(a);
  const b = seed(29, { tasks:lab,pair:true });
  assert.equal((await api('/lab/sessions/' + b, undefined, 29)).data.session.cost, 0.2);
  assert.equal((await api(`/lab/sessions/${a}/pay`, { max_cost:0.2 }, 29)).status, 200);
  const denied = await api(`/lab/sessions/${b}/pay`, { max_cost:0.2 }, 29);
  assert.equal(denied.status, 409); assert.equal(denied.data.error, 'price_changed'); assert.equal(denied.data.cost, 0.3);
  assert.equal(denied.data.tokens, 1.5); assert.equal(balance(29), 1.5); assert.equal(paidLedger(b).length, 0);
  const confirmed = await api(`/lab/sessions/${b}/pay`, { max_cost:0.3 }, 29);
  assert.equal(confirmed.status, 200); assert.equal(confirmed.data.session.cost, 0.3); assert.equal(confirmed.data.tokens, 1.2);
  assert.equal((await api(`/lab/sessions/${b}/pay`, { max_cost:0.2 }, 29)).status, 200, 'a paid replay makes no new charge');
  assert.equal(balance(29), 1.2); assert.equal(paidLedger(b).length, 1);
});

test('submit obeys max_cost before charging/enqueueing and rejects non-tenth or nonnumeric caps', async () => {
  fund(30, 2); await pay(seed(30, { tasks:theory,pair:true }), 30);
  const a = seed(30, { tasks:lab,pair:true }); sql.prepare("UPDATE lab_sessions SET status='ended' WHERE id=?").run(a);
  const b = seed(30, { tasks:lab,pair:true,review:true });
  assert.equal((await api('/lab/sessions/' + b, undefined, 30)).data.session.cost, 0.2);
  await api(`/lab/sessions/${a}/pay`, { max_cost:0.2 }, 30);
  const denied = await api(`/lab/sessions/${b}/submit`, { grade:true,max_cost:0.2 }, 30);
  assert.equal(denied.status, 409); assert.equal(denied.data.error, 'price_changed'); assert.equal(denied.data.cost, 0.3);
  assert.equal(balance(30), 1.5); assert.equal(paidLedger(b).length, 0);
  assert.equal(sql.prepare('SELECT COUNT(*) n FROM lab_jobs WHERE session_id=?').get(b).n, 0);
  assert.equal(sql.prepare('SELECT charged FROM lab_sessions WHERE id=?').get(b).charged, 0);
  for (const max_cost of [0.21, null, '0.3', -0.1]) assert.equal((await api(`/lab/sessions/${b}/pay`, { max_cost }, 30)).status, 400);
});

test('partial sets, unmarked pairs and unrelated owners/years/keys cannot earn a discount', async () => {
  for (const [user, before, after] of [
    [5, { tasks: ['T1'], pair: true }, { tasks: lab, pair: true }],
    [6, { tasks: theory }, { tasks: lab, pair: true }],
    [7, { tasks: theory, pair: true }, { tasks: lab, pair: true, year: 2023 }],
    [8, { tasks: theory, pair: true }, { tasks: lab, pair: true, key: 'other-round' }],
    [9, { tasks: theory, pair: true }, { tasks: theory, pair: true }],
  ]) {
    fund(user, 1); await pay(seed(user, before), user); const r = await pay(seed(user, after), user);
    assert.equal(r.data.session.cost, 0.3, JSON.stringify({ user, result: r.data })); assert.equal(r.data.tokens, 0.4);
  }
  fund(10, 1); const r = await pay(seed(10, { tasks: lab, pair: true }), 10);
  assert.equal(r.data.session.cost, 0.3); assert.equal(r.data.session.paired_with, null);
});

test('mixed sittings cost 0.5 even when marked pair; exact balances work and insufficiency writes nothing', async () => {
  fund(11, 0.5); const r = await pay(seed(11, { tasks: ['T1', 'E1'], pair: true }), 11);
  assert.equal(r.status, 200); assert.equal(r.data.session.kind, 'mixed'); assert.equal(r.data.session.cost, 0.5); assert.equal(r.data.tokens, 0);
  fund(12, 0.2); const id = seed(12); const denied = await pay(id, 12);
  assert.equal(denied.status, 402); assert.equal(denied.data.tokens, 0.2); assert.equal(paidLedger(id).length, 0);
  assert.equal(sql.prepare('SELECT charged FROM lab_sessions WHERE id=?').get(id).charged, 0);
  fund(12, 0.3); assert.equal((await pay(id, 12)).data.tokens, 0);
  fund(13, 0.5); await pay(seed(13, { tasks: theory, pair: true }), 13);
  assert.equal((await pay(seed(13, { tasks: lab, pair: true }), 13)).data.tokens, 0);
});

test('canonical NBPhO mixed tasksets remain mixed and cost 0.5 when client theory-kind metadata is omitted', async () => {
  fund(31, 1); const tasks = LAB_MIXED_CATALOGUE.nbpho['2024'][0];
  const opened = await api('/lab/start', { comp:'nbpho',year:2024,tasks,pair:true,sources:{} }, 31);
  assert.equal(opened.status, 200); assert.equal(opened.data.session.kind, 'mixed'); assert.equal(opened.data.session.cost, 0.5);
  assert.equal(opened.data.session.exam_sec, 600 * 60);
  assert.equal(sql.prepare('SELECT ended_at-started_at duration FROM lab_sessions WHERE id=?').get(opened.data.session.id).duration, 600 * 60);
  const denied = await api(`/lab/sessions/${opened.data.session.id}/pay`, { max_cost:0.3 }, 31);
  assert.equal(denied.status, 409); assert.equal(denied.data.cost, 0.5); assert.equal(balance(31), 1);
  const paid = await pay(opened.data.session.id, 31); assert.equal(paid.data.session.cost, 0.5); assert.equal(balance(31), 0.5);
  const old = seed(32, { comp:'nbpho',tasks,theory:[],pair:true,charged:1 });
  assert.equal((await pay(old, 32)).data.session.cost, 0.5, 'historical paid price still uses the original source-kind rules');
});

test('repeated and concurrent pay requests debit once; a transaction interruption rolls everything back', async () => {
  fund(14, 1); const id = seed(14); const results = await Promise.all([1, 2, 3].map(() => pay(id, 14)));
  assert.ok(results.every(r => r.status === 200), JSON.stringify(results)); assert.equal(balance(14), 0.7); assert.equal(paidLedger(id).length, 1);
  fund(15, 1); const interrupted = seed(15); failCharge = true;
  const previousError = console.error; let failed;
  try { console.error = () => {}; failed = await pay(interrupted, 15); } finally { console.error = previousError; }
  assert.equal(failed.status, 500); assert.equal(balance(15), 1); assert.equal(paidLedger(interrupted).length, 0);
  assert.equal(sql.prepare('SELECT charged FROM lab_sessions WHERE id=?').get(interrupted).charged, 0);
  assert.equal((await pay(interrupted, 15)).data.tokens, 0.7);
});

test('ten single charges consume exactly three tokens, with no floating-point drift', async () => {
  fund(16, 3); for (let i = 0; i < 10; i++) assert.equal((await pay(seed(16), 16)).data.tokens, (27 - 3 * i) / 10);
  assert.equal(balance(16), 0); assert.equal(sql.prepare("SELECT ROUND(SUM(delta)*10) units FROM lab_ledger WHERE user_id=16 AND reason='grade'").get().units, -30);
});

test('legacy paid records retain old prices and never become new pair-discount credits', async () => {
  fund(17, 1); const old = seed(17, { tasks: theory, pair: true, charged: 1 });
  sql.prepare("INSERT INTO lab_ledger(user_id,delta,reason,note,session_id,created_at) VALUES(17,-1,'grade','half',?,?)").run(old, time);
  const before = await pay(old, 17); assert.equal(before.data.session.cost, 0.5); assert.equal(before.data.session.pricing_version, 1); assert.equal(before.data.tokens, 1);
  const r = await pay(seed(17, { tasks: lab, pair: true }), 17); assert.equal(r.data.session.cost, 0.3); assert.equal(r.data.session.paired_with, null);
  const whole = seed(18, { charged: 1 }); assert.equal((await pay(whole, 18)).data.session.cost, 1);
});

test('fractional admin grants/revokes preserve half balances and ledger actual clamped changes', async () => {
  fund(19, 0, 1);
  assert.equal((await api('/admin/lab/tokens', { user: 'price19', delta: 0.3 })).data.tokens, 0.8);
  assert.equal((await api('/admin/lab/tokens?user=price19')).data.user.exam_tokens, 0.8);
  const revoked = await Promise.all([1, 2].map(() => api('/admin/lab/tokens', { user: 'price19', delta: -0.5 })));
  assert.ok(revoked.every(r => r.status === 200)); assert.equal(balance(19), 0);
  assert.deepEqual(sql.prepare("SELECT delta FROM lab_ledger WHERE user_id=19 AND reason='revoke' ORDER BY id").all().map(r => r.delta), [-0.5, -0.3]);
  for (const delta of [0, 0.03, 0.333, 1000.1, 'invalid']) assert.equal((await api('/admin/lab/tokens', { user: 'price19', delta })).status, 400);
});

function order(id, user, tokens, credited = 0) {
  sql.prepare("INSERT INTO pay_orders(order_id,user_id,pack,tokens,amount,status,payment_key,credited,created_at) VALUES(?,?,'local',?,1900,'done','local_key',?,?)").run(id, user, tokens, credited, time);
}
test('purchases normalize old halves and credit once; refunds revoke only actual credited remainder', async () => {
  fund(20, 0.2, 1); order('local_credit', 20, 1);
  const credited = await Promise.all([1, 2].map(() => api('/pay/confirm', { orderId: 'local_credit' }, 20)));
  assert.ok(credited.every(r => r.status === 200)); assert.equal(balance(20), 1.7);
  assert.equal(sql.prepare("SELECT COUNT(*) n FROM lab_ledger WHERE user_id=20 AND reason='purchase'").get().n, 1);
  fund(20, 0.7); assert.equal((await api('/admin/pay/local_credit/cancel', {})).status, 200);
  assert.equal(balance(20), 0); assert.equal(sql.prepare("SELECT delta FROM lab_ledger WHERE user_id=20 AND reason='cancel'").get().delta, -0.7);
  assert.equal((await api('/admin/pay/local_credit/cancel', {})).status, 409);
  fund(21, 0.4, 1); order('local_uncredited', 21, 1);
  assert.equal((await api('/admin/pay/local_uncredited/cancel', {})).status, 200); assert.equal(balance(21), 0.9);
  assert.equal((await api('/pay/confirm', { orderId: 'local_uncredited' }, 21)).status, 409);
  assert.equal(paymentCalls, 2);
  fund(22, 0); order('local_fractional_pack', 22, 0.7);
  assert.equal((await api('/pay/confirm', { orderId: 'local_fractional_pack' }, 22)).data.tokens, 0.7);
});

test('rewarded ads preserve decimal/half balances and grant one whole token for three unique claims', async () => {
  fund(23, 0.2, 1); let nonce;
  for (let i = 0; i < 3; i++) {
    const started = await api('/ads/start', {}, 23); nonce = started.data.nonce; assert.equal(started.status, 200);
    const claimed = await api('/ads/claim', { nonce }, 23); assert.equal(claimed.status, 200);
    assert.equal(claimed.data.tokens, i === 2 ? 1.7 : 0.7); assert.equal(claimed.data.parts, (i + 1) % 3);
  }
  assert.equal((await api('/ads/claim', { nonce }, 23)).status, 409); assert.equal(balance(23), 1.7);
  assert.equal(sql.prepare("SELECT COUNT(*) n FROM lab_ledger WHERE user_id=23 AND reason='ad'").get().n, 1);
});

test('server pack configuration accepts tenths and refuses unrepresentable fractional token values', async () => {
  const config = async tokens => api('/pay/config', undefined, 1, { ...env, TOSS_CLIENT_KEY: 'local', PAY_PACKS: JSON.stringify([{ id: 'test', tokens, krw: 1900 }]) });
  assert.equal((await config(0.7)).data.pay.packs[0].tokens, 0.7);
  assert.equal((await config(0.333)).data.pay.packs[0].tokens, 1);
  assert.equal(balance(24), 5, 'existing signup/default grant remains five whole tokens');
});
