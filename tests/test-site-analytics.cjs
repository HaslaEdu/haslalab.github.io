'use strict';
/* Visit statistics (site-analytics.js): Cloudflare Web Analytics, loaded only where privacy.html says it is. */
const test = require('node:test'), assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const ROOT = path.join(__dirname, '..');
const read = f => fs.readFileSync(path.join(ROOT, f), 'utf8');
const SRC = read('site-analytics.js');
const STARTS = Date.UTC(2026, 10, 10, 15);

function run({token = 'tok123', now = STARTS + 1, host = 'haslalab.org', framed = false, dnt, gpc} = {}) {
  const appended = [];
  const self = {};
  const ctx = {
    location: {hostname: host},
    navigator: {doNotTrack: dnt, globalPrivacyControl: gpc},
    document: {
      createElement: () => { const attrs = {}; return {attrs, setAttribute: (k, v) => { attrs[k] = v; }}; },
      head: {appendChild: el => appended.push(el)},
    },
    Date: {UTC: Date.UTC, now: () => now},
    JSON,
  };
  ctx.window = ctx; ctx.window.self = self; ctx.window.top = framed ? {} : self;
  vm.createContext(ctx);
  vm.runInContext(SRC.replace('const TOKEN = "";', `const TOKEN = ${JSON.stringify(token)};`), ctx);
  return appended;
}

test('loads the Cloudflare beacon with the token on haslalab.org once the policy is in force', () => {
  const [s, ...rest] = run();
  assert.equal(rest.length, 0);
  assert.equal(s.src, 'https://static.cloudflareinsights.com/beacon.min.js');
  assert.equal(s.defer, true);
  assert.deepEqual(JSON.parse(s.attrs['data-cf-beacon']), {token: 'tok123'});
  assert.equal(run({host: 'www.haslalab.org'}).length, 1);
});

test('stays off without a token, before the policy date, off the site, in frames and under DNT/GPC', () => {
  assert.equal(SRC.includes('const TOKEN = "";'), true, 'the committed file carries the token placeholder line');
  assert.equal(run({token: ''}).length, 0);
  assert.equal(run({now: STARTS - 1}).length, 0);
  assert.equal(run({host: 'localhost'}).length, 0);
  assert.equal(run({host: 'haslaedu.github.io'}).length, 0);
  assert.equal(run({framed: true}).length, 0);
  assert.equal(run({dnt: '1'}).length, 0);
  assert.equal(run({gpc: true}).length, 0);
});

test('the policy start date in the script matches privacy.html', () => {
  const privacy = read('privacy.html');
  assert.match(privacy, /시행일: 2026년 11월 11일 · 버전 2026-11-11/);
  assert.match(privacy, /방문 통계/);
  assert.match(privacy, /Effective 11 November 2026/);
  assert.equal(new Date(STARTS + 9 * 3600e3).toISOString().slice(0, 10), '2026-11-11');
});

test('public pages load it once; account, payment, grading, studio and exam pages do not', () => {
  const pages = ['index.html', 'problems.html', 'problems-en.html', 'problem-search.html', 'privacy.html', 'terms.html', '404.html'];
  for (const p of pages) assert.equal(read(p).split('src="site-analytics.js"').length - 1, 1, p);
  const sims = fs.readdirSync(path.join(ROOT, 'sim')).filter(f => f.endsWith('_web.html') || f === 'ipho2021_app.html');
  assert.ok(sims.length > 100);
  for (const f of sims) assert.equal(read('sim/' + f).split('src="../site-analytics.js"').length - 1, 1, 'sim/' + f);
  for (const p of ['account.html', 'pay.html', 'ai-review.html', 'studio.html', 'sim/exam.html', 'sim/contest-exam.html', 'sim/monthly-answer-sheet.html', 'sim/monthly-scan.html', 'sim/omr.html', 'sim/scan.html', 'sim/scanbench.html', 'sim/sheets.html']) assert.ok(!read(p).includes('site-analytics.js'), p);
  assert.match(read('build_seo.js'), /<script defer src="site-analytics.js"><\/script>\n<\/head>/, 'the generator keeps the tag in problems*.html');
});

test('problem-search.html CSP lets the beacon load and report', () => {
  const csp = read('problem-search.html').match(/Content-Security-Policy" content="([^"]+)"/)[1];
  assert.match(csp, /script-src 'self' https:\/\/static\.cloudflareinsights\.com;/);
  assert.match(csp, /connect-src [^;]*https:\/\/cloudflareinsights\.com/);
});
