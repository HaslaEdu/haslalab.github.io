// Browser front end for the E1 apparatus. Everything runs locally; nothing is sent over the network.
import { newState, exec, banner, helpRows } from './lab.mjs';

const $ = id => document.getElementById(id), screen = $('screen'), q = new URLSearchParams(location.search);
const lang = q.get('lang') === 'en' ? 'en' : 'ko';
const embedded = q.get('embed') === '1';
const KEY = 'hlSimHphoE1', SCREEN_KEY = 'hlSimHphoE1Screen';
const SHELL = 'student@haslalab:~/experiment$ ', LAB = 'wicklab> ';

const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch {} }
};
let state;
try { state = JSON.parse(store.get(KEY)); } catch {}
if (!state || state.v !== 1) state = newState();
let saved = [];
try { saved = JSON.parse(store.get(SCREEN_KEY)) || []; } catch {}
const save = () => { store.set(KEY, JSON.stringify(state)); store.set(SCREEN_KEY, JSON.stringify(saved.slice(-300))); };

const L = {
  ko: {
    title: '종이 속으로 스며드는 물', sub: 'HPhO 모의고사 1 · 실험 E1 · 10점', problem: '문제', q: '문제지', a: '답안지',
    clear: '화면 지우기', saveLog: '기록 저장', csv: '측정 CSV', theme: '색상 모드 전환', cmd: '명령어',
    start: 'HaslaLab Experimental Laboratory\n\n./wicklab',
    restored: '이전 기록을 불러왔습니다. 측정과 모의 시계는 이 브라우저에 남아 있습니다.',
    shellHelp: 'ls\n./wicklab\nclear',
    notFound: c => `${c}: command not found`,
    noCsv: '저장된 측정이 없습니다.',
    pageTitle: '종이 속으로 스며드는 물 · HaslaLab'
  },
  en: {
    title: 'Water creeping into paper', sub: 'HPhO mock paper 1 · Experiment E1 · 10 points', problem: 'Problem', q: 'Question paper', a: 'Answer sheet',
    clear: 'Clear screen', saveLog: 'Save log', csv: 'Measurements CSV', theme: 'Toggle colour mode', cmd: 'Command',
    start: 'HaslaLab Experimental Laboratory\n\n./wicklab',
    restored: 'Earlier records restored. Measurements and the simulated clock are kept in this browser.',
    shellHelp: 'ls\n./wicklab\nclear',
    notFound: c => `${c}: command not found`,
    noCsv: 'No measurements yet.',
    pageTitle: 'Water creeping into paper · HaslaLab'
  }
}[lang];

const pdf = name => `../../hpho/samples/mock-1/${lang}/${name}`;
document.documentElement.lang = lang;
document.title = L.pageTitle;
$('hTitle').textContent = L.title; $('hSub').textContent = L.sub; $('problemTab').textContent = L.problem;
$('qLink').textContent = L.q; $('qLink').href = pdf('E1-question.pdf'); $('aLink').textContent = L.a; $('aLink').href = pdf('E1-answer.pdf');
$('clear').textContent = L.clear; $('saveLog').textContent = L.saveLog; $('downloadCsv').textContent = L.csv;
$('theme').setAttribute('aria-label', L.theme); $('command').setAttribute('aria-label', L.cmd);
if (lang === 'en') { $('terminal').setAttribute('aria-label', 'Experiment command terminal'); $('screen').setAttribute('aria-label', 'Experiment log'); }

const selectedTheme = q.get('theme'), storedTheme = store.get('hlTheme');
document.body.dataset.theme = selectedTheme === 'dark' || selectedTheme !== 'light' && (storedTheme === 'dark' || !storedTheme && matchMedia('(prefers-color-scheme:dark)').matches) ? 'dark' : 'light';
$('theme').onclick = () => { document.body.dataset.theme = document.body.dataset.theme === 'dark' ? 'light' : 'dark'; };
if (embedded) {
  document.body.dataset.embedded = 'true';
  window.addEventListener('message', e => {
    if (e.source !== parent || e.origin !== location.origin) return;
    if (e.data?.type === 'haslalab-experiment-theme' && ['dark', 'light'].includes(e.data.theme)) document.body.dataset.theme = e.data.theme;
  });
}

function math(el, text) {
  for (const chunk of String(text).split(/(\$[^$\n]+\$|`[^`\n]+`)/g)) {
    if (!chunk) continue;
    const node = document.createElement(chunk.startsWith('`') ? 'code' : 'span');
    if (chunk.startsWith('$') && chunk.endsWith('$') && chunk.length > 1 && window.katex) window.katex.render(chunk.slice(1, -1), node, { throwOnError: false });
    else node.textContent = chunk.replace(/^`|`$/g, '');
    el.append(node);
  }
  return el;
}
const el = (tag, text) => text === undefined ? document.createElement(tag) : math(document.createElement(tag), text);

const P = {
  ko: {
    meta: 'HPhO 모의고사 1 · 실험 E1 · 브라우저 모의 실험',
    intro: [
      '이 페이지는 실험 E1의 장치를 브라우저 안에서 흉내 낸 것이다. 문제와 답안지는 PDF로 보고, 측정은 CMD 탭에서 명령어로 한다. 인터넷 연결 없이 이 브라우저 안에서만 동작한다.',
      '장치의 값(종이, 액체, 실내 공기)은 브라우저마다 문제에 맞는 범위 안에서 한 번 정해지고, 새로고침해도 그대로 남는다. 답은 직접 잰 자료로 구해야 한다.'
    ],
    links: [['문제지 PDF', 'E1-question.pdf'], ['답안지 PDF', 'E1-answer.pdf'], ['풀이 용지 PDF', 'E1-writing.pdf']],
    hApp: '장치',
    app: [
      '스트립 12장. 폭은 문제지의 값, 길이 $300\\,\\mathrm{mm}$. `dip` 하면 아래 끝 $5\\,\\mathrm{mm}$가 액체에 잠기고 스톱워치가 시작된다. 눈금자의 0은 액면에 맞춰져 있다. 한 번 담근 스트립은 다시 쓸 수 없다.',
      '접시 d1, d2. 눈금 실린더(최소 눈금 $1\\,\\mathrm{mL}$)로 $10$-$50\\,\\mathrm{mL}$를 채운다. 액체를 바꾸면 접시를 헹군 뒤 채운다. 스트립을 거는 클램프 스탠드는 접시마다 하나씩이다.',
      '뚜껑 있는 투명 용기 1개. 접시 하나가 들어가며, 뚜껑을 닫은 채로 눈금자와 스톱워치를 읽을 수 있다.',
      '눈금자 $1\\,\\mathrm{mm}$, 스톱워치 $0.01\\,\\mathrm{s}$, 전자저울 $0.01\\,\\mathrm{g}$, 버니어 캘리퍼스 $0.02\\,\\mathrm{mm}$. 젖은 앞면은 번져 있으므로 읽을 때마다 값이 조금씩 흔들린다.',
      '시간은 모의 시계로 흐른다. `wait 5 min`은 바로 5분을 보낸다. 다른 동작도 시간이 든다: 채우기 60 s, 담그기 20 s, 읽기 5 s, 무게 재기 10-20 s, 캘리퍼스 15-30 s. 두 접시의 실험은 같은 시계 위에서 동시에 진행된다.'
    ],
    hCmd: '명령어',
    cmdHead: ['명령', '동작', '예'],
    cmdNote: 'CMD 탭에서 `./wicklab`을 입력하면 장치가 열린다. 위아래 화살표로 이전 명령을 다시 부르고, Ctrl+C로 장치에서 나간다.',
    hRec: '기록',
    rec: 'read, until, weigh, caliper의 결과는 측정 기록에 쌓이고 이 브라우저(localStorage)에 저장된다. `log`로 보고, `csv` 또는 「측정 CSV」 버튼으로 내려받는다. 「기록 저장」은 화면의 글을 텍스트 파일로 내려받는다. `reset`은 새 장치를 뽑고 기록과 시계를 지운다.',
    foot: '모의 실험은 문제지의 모형을 따르며 실제 실험의 모든 효과를 담지는 않는다.'
  },
  en: {
    meta: 'HPhO mock paper 1 · Experiment E1 · browser simulation',
    intro: [
      'This page simulates the apparatus of experiment E1 in the browser. Read the problem and the answer sheet in the PDFs and take your measurements with commands in the CMD tab. It runs only inside this browser and needs no network.',
      'The apparatus values (paper, liquids, room air) are drawn once per browser from ranges that suit the problem, and they stay the same after a reload. Find the answers from the data you measure.'
    ],
    links: [['Question paper (PDF)', 'E1-question.pdf'], ['Answer sheet (PDF)', 'E1-answer.pdf'], ['Writing sheets (PDF)', 'E1-writing.pdf']],
    hApp: 'Apparatus',
    app: [
      '12 strips, width as given in the paper, length $300\\,\\mathrm{mm}$. `dip` puts the lower $5\\,\\mathrm{mm}$ into the liquid and starts the stopwatch. The zero of the ruler is at the liquid surface. A strip that has been dipped cannot be used again.',
      'Dishes d1 and d2. Fill them with $10$-$50\\,\\mathrm{mL}$ from the measuring cylinder (smallest division $1\\,\\mathrm{mL}$). Changing the liquid rinses the dish first. Each dish has one clamp stand for a strip.',
      'One transparent container with a lid. It holds one dish. You can read the ruler and the stopwatch with the lid closed.',
      'Ruler $1\\,\\mathrm{mm}$, stopwatch $0.01\\,\\mathrm{s}$, balance $0.01\\,\\mathrm{g}$, vernier caliper $0.02\\,\\mathrm{mm}$. The wet front is not sharp, so repeated readings scatter a little.',
      'Time runs on a simulated clock. `wait 5 min` passes 5 minutes at once. Other actions take time as well: filling 60 s, dipping 20 s, reading 5 s, weighing 10-20 s, caliper 15-30 s. Experiments in the two dishes run at the same time on the same clock.'
    ],
    hCmd: 'Commands',
    cmdHead: ['command', 'action', 'example'],
    cmdNote: 'In the CMD tab type `./wicklab` to open the apparatus. The up and down arrows recall earlier commands and Ctrl+C leaves the apparatus.',
    hRec: 'Records',
    rec: 'Results of read, until, weigh and caliper go into the measurement log, which is saved in this browser (localStorage). `log` shows it, and `csv` or the Measurements CSV button downloads it. Save log downloads the screen text. `reset` draws a new apparatus and erases the records and the clock.',
    foot: 'The simulation follows the model in the paper and does not include every effect of a real experiment.'
  }
}[lang];

function buildProblem() {
  const m = $('problem');
  const meta = el('p', P.meta); meta.className = 'meta';
  m.append(meta, el('h1', L.title));
  for (const t of P.intro) m.append(el('p', t));
  const links = el('div'); links.className = 'links';
  for (const [t, f] of P.links) { const a = el('a', t); a.href = pdf(f); links.append(a); }
  m.append(links, el('h2', P.hApp));
  const ul = el('ul'); for (const t of P.app) ul.append(el('li', t)); m.append(ul);
  m.append(el('h2', P.hCmd), el('p', P.cmdNote));
  const wrap = el('div'); wrap.className = 'wrap';
  const tb = el('table'), hr = el('tr'); for (const h of P.cmdHead) hr.append(el('th', h)); tb.append(hr);
  for (const [c, d, ex] of helpRows(lang)) { const tr = el('tr'); tr.append(el('td', '`' + c + '`'), el('td', d), el('td', '`' + ex + '`')); tb.append(tr); }
  wrap.append(tb); m.append(wrap, el('h2', P.hRec), el('p', P.rec));
  const f = el('footer', P.foot); m.append(f);
}

function line(text, kind = '', keep = true) {
  const n = document.createElement('pre'); n.className = 'entry ' + kind; n.textContent = text; screen.append(n);
  if (keep) saved.push([text, kind]);
  screen.scrollTop = screen.scrollHeight;
}
function download(data, name, type = 'text/plain;charset=utf-8') {
  const url = URL.createObjectURL(new Blob([data], { type })), a = document.createElement('a');
  a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
const setPrompt = () => { $('prompt').textContent = state.inside ? LAB : SHELL; };
function mode(cmd, focus = true) {
  cmd = embedded || cmd; $('problem').hidden = cmd; $('terminal').hidden = !cmd;
  $('problemTab').setAttribute('aria-selected', String(!cmd)); $('cmdTab').setAttribute('aria-selected', String(cmd));
  if (cmd && focus) $('command').focus();
}
$('problemTab').onclick = () => mode(false); $('cmdTab').onclick = () => mode(true);

let history = []; try { history = JSON.parse(store.get('hlSimHphoE1Hist')) || []; } catch {}
let hIndex = history.length;
function accept(input) {
  input = input.trim(); if (!input) return;
  history.push(input); history = history.slice(-200); hIndex = history.length; store.set('hlSimHphoE1Hist', JSON.stringify(history));
  line($('prompt').textContent + input, 'typed');
  if (input === 'clear') { screen.replaceChildren(); saved = []; save(); return; }
  if (!state.inside) {
    if (input === 'ls') line('wicklab');
    else if (['./wicklab', 'wicklab', 'wicklab.exe'].includes(input)) { state.inside = true; setPrompt(); line(banner(lang)); }
    else if (input === 'help') line(L.shellHelp);
    else line(L.notFound(input.split(/\s+/)[0]), 'error');
    save(); return;
  }
  const r = exec(state, input, lang);
  if (r.exit) { state.inside = false; setPrompt(); }
  else if (r.reset) { const inside = state.inside; state = newState(); state.inside = inside; line(r.text, 'notice'); }
  else if (r.text) line(r.text, r.ok ? '' : 'error');
  if (r.csv) download(r.csv, r.filename, 'text/csv;charset=utf-8');
  save();
}
$('bar').onsubmit = e => { e.preventDefault(); const v = $('command').value; $('command').value = ''; accept(v); };
$('command').onkeydown = e => {
  if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
    e.preventDefault(); hIndex = Math.max(0, Math.min(history.length, hIndex + (e.key === 'ArrowUp' ? -1 : 1)));
    $('command').value = history[hIndex] || '';
  }
  if (e.ctrlKey && e.key.toLowerCase() === 'c' && !window.getSelection()?.toString()) {
    e.preventDefault(); line($('prompt').textContent + $('command').value + '^C', 'typed');
    $('command').value = ''; state.pendingReset = false; state.inside = false; setPrompt(); save();
  }
};
$('clear').onclick = () => { screen.replaceChildren(); saved = []; save(); $('command').focus(); };
$('saveLog').onclick = () => download(saved.map(x => x[0]).join('\n\n') + '\n', 'hpho-e1-wicklab-log.txt');
$('downloadCsv').onclick = () => {
  if (!state.records.length) { line(L.noCsv, 'notice'); return; }
  const r = exec(state, 'csv', lang); if (r.csv) download(r.csv, r.filename, 'text/csv;charset=utf-8'); save();
};

if (!embedded) buildProblem();
if (saved.length) { for (const [t, k] of saved) line(t, k, false); line(L.restored, 'notice', false); }
else line(L.start, 'notice');
setPrompt();
if (embedded) { mode(true, false); if (!state.inside) accept('./wicklab'); }
else if (q.get('view') === 'cmd') mode(true);
save();
