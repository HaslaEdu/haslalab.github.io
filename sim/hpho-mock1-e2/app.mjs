// Photoelastic bench for HPhO mock-1 E2. Runs entirely in the browser; the apparatus lives in localStorage.
import {Lab, HELP, drawParams, initialState, clockText} from './model.mjs';

const $ = id => document.getElementById(id), screen = $('screen'), q = new URLSearchParams(location.search);
const lang = q.get('lang') === 'en' ? 'en' : 'ko', embedded = q.get('embed') === '1';
const KEY = 'hlHphoMock1E2';
const SHELL = 'student@haslalab:~/experiment$ ', INSIDE = 'photoelastic> ';
let inside = false, commandHistory = [], historyIndex = 0, saved = [], lab;
if (embedded) document.body.dataset.embedded = 'true';
document.documentElement.lang = lang;

function newSeed() { try { return crypto.getRandomValues(new Uint32Array(1))[0]; } catch { return (Math.random() * 2 ** 32) >>> 0; } }
function load() {
  try { const d = JSON.parse(localStorage.getItem(KEY) || 'null'); if (d && d.v === 1 && d.params && d.state) return d; } catch {}
  return null;
}
function fresh() { const seed = newSeed(); return {v: 1, seed, params: drawParams(seed), state: initialState(seed), screen: []}; }
let data = load() || fresh();
lab = new Lab(data.params, data.state, lang);
saved = data.screen || [];
function persist() { try { localStorage.setItem(KEY, JSON.stringify({v: 1, seed: data.seed, params: lab.P, state: lab.S, screen: saved.slice(-300)})); } catch {} }

const T = {
  ko: {
    title: '응력이 만드는 색', sub: 'HPhO 모의고사 1 · E2 · 10점', meta: 'Experiment · HPhO 모의고사 1 · E2', problem: '문제', sheet: '답안지', back: 'HPhO ↗',
    clear: '화면 지우기', saveLog: '기록 저장', csv: '측정 CSV', themeLabel: '색상 모드 전환',
    restored: '저장된 측정 기록을 다시 불러왔습니다.', banner: 'Photoelastic bench · HPhO mock-1 E2\nλ = 546 nm | 시편 3종 | 시각 ', nofile: '기록이 없습니다.',
  },
  en: {
    title: 'Colours made by stress', sub: 'HPhO mock paper 1 · E2 · 10 points', meta: 'Experiment · HPhO mock paper 1 · E2', problem: 'Problem', sheet: 'Answer sheet', back: 'HPhO ↗',
    clear: 'Clear screen', saveLog: 'Save log', csv: 'Records CSV', themeLabel: 'Toggle colour mode',
    restored: 'Saved measurements restored.', banner: 'Photoelastic bench · HPhO mock-1 E2\nλ = 546 nm | 3 specimens | clock ', nofile: 'No records.',
  },
}[lang];

const PAGE = {
  ko: {
    intro: '이 페이지는 E2의 실험 장치를 브라우저 안에 옮긴 모의 장치이다. 문제와 답안지는 아래 PDF를 쓰고, 측정은 CMD 탭의 명령으로 한다. 문항 A부터 D까지 요구하는 측정을 모두 이 장치로 할 수 있다.',
    question: '문제지 PDF', answer: '답안지 PDF',
    h1: '장치', app: [
      '녹색 LED 백라이트($\\lambda = 546\\,\\mathrm{nm}$) 위에 첫 편광판이 고정되어 있고, 그 축을 각도 $0^\\circ$로 둔다. 두 번째 편광판(검광판)은 각도기 눈금으로 돌린다. 1/4 파장판 두 장은 함께 넣고 뺀다.',
      '시편 3종: 인장 시편, 굽힘 보(클램프에 물린 외팔보), 구멍 뚫린 인장 시편. 공칭 치수는 문제지 표 1과 같고, 실제 치수는 자와 버니어 캘리퍼스로 잰다.',
      '추 세트 $50\\,\\mathrm{g}\\times4$, $100\\,\\mathrm{g}\\times4$, $500\\,\\mathrm{g}\\times6$, 추걸이(각인 $50\\,\\mathrm{g}$). 굽힘 보에는 추걸이 없이 실 고리로 추를 걸 수 있다. 저울은 없다.',
    ],
    h2: '읽는 방법', read: [
      '밝기 $I$는 눈으로 읽은 값이며, 평행 편광판을 지난 백라이트 밝기를 $100\\,\\%$로 한다.',
      '<code>watch</code>로 점을 찍어 두면, 하중이나 시간이 바뀔 때 그 점을 지나간 어두운 줄과 밝은 줄의 수를 알려 준다.',
      '<code>fringes</code>는 한 선 위에 보이는 어두운 줄의 위치를 잰다. 줄의 차수는 알려 주지 않는다. 너무 촘촘한 줄은 눈으로 가를 수 없다.',
      '시각은 모의 시계로 흐른다. 각 명령은 실제 조작에 드는 시간만큼 시계를 넘기고, <code>wait</code>는 기다리지 않고 바로 시계를 넘긴다.',
      '장치의 숨은 값(재료와 시편의 실제 값)은 브라우저마다 따로 정해지고, 새로고침해도 유지된다. <code>reset</code>은 새 장치를 받는다.',
    ],
    h3: '좌표', fig: '좌표는 mm 단위이다. 인장 시편과 천공 시편의 $x$는 하중 축, 굽힘 보의 $x$는 클램프 끝에서 잰 거리, $y$는 아래 모서리에서 잰 높이이다.',
    h4: '명령어', cmdHead: ['명령', '설명', '예'],
  },
  en: {
    intro: 'This page is a simulated version of the E2 apparatus that runs in the browser. Use the PDFs below for the problem and the answer sheet, and make the measurements with the commands in the CMD tab. Every measurement asked for in Parts A to D can be made with it.',
    question: 'Problem PDF', answer: 'Answer sheet PDF',
    h1: 'Apparatus', app: [
      'The first polarizer is fixed on a green LED backlight ($\\lambda = 546\\,\\mathrm{nm}$); its axis defines $0^\\circ$. The second polarizer (analyzer) is turned on a protractor scale. The two quarter-wave plates are inserted and removed together.',
      'Three specimens: tension specimen, bending beam (clamped as a cantilever), tension specimen with a hole. Nominal dimensions are those of Table 1 in the paper; measure the actual ones with the ruler and the vernier caliper.',
      'Masses $50\\,\\mathrm{g}\\times4$, $100\\,\\mathrm{g}\\times4$, $500\\,\\mathrm{g}\\times6$ and a hanger (stamped $50\\,\\mathrm{g}$). Masses can hang from the beam on a thread loop without the hanger. There is no balance.',
    ],
    h2: 'How readings work', read: [
      'Brightness $I$ is read by eye, with the backlight seen through parallel polarizers taken as $100\\,\\%$.',
      'Mark a point with <code>watch</code>; whenever the load or the time changes, you are told how many dark and bright fringes passed it.',
      '<code>fringes</code> measures the positions of the dark fringes visible along one line. It does not give their orders. Fringes that are too close together cannot be separated by eye.',
      'Time runs on a simulated clock. Each command advances it by the time the real operation takes, and <code>wait</code> advances it at once.',
      'The hidden values of the apparatus (the actual material and specimen values) are drawn separately for each browser and kept after a reload. <code>reset</code> issues a new apparatus.',
    ],
    h3: 'Coordinates', fig: 'Coordinates are in mm. For the tension specimen and the specimen with a hole, $x$ is along the load axis; for the beam, $x$ is measured from the clamp edge and $y$ up from the lower edge.',
    h4: 'Commands', cmdHead: ['Command', 'Description', 'Example'],
  },
}[lang];

function math(el, text) {
  for (const chunk of String(text).split(/(\$[^$\n]+\$|<code>[^<]+<\/code>)/g)) {
    if (!chunk) continue;
    if (chunk.startsWith('$')) { const n = document.createElement('span'); try { window.katex.render(chunk.slice(1, -1), n, {throwOnError: false}); } catch { n.textContent = chunk.slice(1, -1); } el.append(n); }
    else if (chunk.startsWith('<code>')) { const c = document.createElement('code'); c.textContent = chunk.slice(6, -7); el.append(c); }
    else el.append(document.createTextNode(chunk));
  }
  return el;
}
const el = (tag, text) => math(document.createElement(tag), text);

function buildPage() {
  const st = $('statement'), base = `../../hpho/samples/mock-1/${lang}/`;
  st.append(el('p', PAGE.intro));
  const links = document.createElement('div'); links.className = 'links';
  for (const [name, file] of [[PAGE.question, 'E2-question.pdf'], [PAGE.answer, 'E2-answer.pdf']]) { const a = document.createElement('a'); a.href = base + file; a.textContent = name; a.target = '_blank'; a.rel = 'noopener'; links.append(a); }
  st.append(links);
  st.append(el('h2', PAGE.h1)); const ul = document.createElement('ul'); for (const t of PAGE.app) ul.append(el('li', t)); st.append(ul);
  st.append(el('h2', PAGE.h3));
  const fig = document.createElement('figure'), box = document.createElement('div'); box.id = 'coords'; box.append($('coordsFig').content.cloneNode(true));
  if (lang === 'ko') { const L = {'tension (b₁)': '인장 시편 (b₁)', 'beam (h), y = 0 at the lower edge': '굽힘 보 (h), 아래 모서리 y = 0', 'with hole (b₂, d)': '천공 시편 (b₂, d)', notch: '홈'}; for (const t of box.querySelectorAll('text')) if (L[t.textContent]) t.textContent = L[t.textContent]; } fig.append(box, el('figcaption', PAGE.fig)); st.append(fig);
  st.append(el('h2', PAGE.h2)); const ul2 = document.createElement('ul'); for (const t of PAGE.read) ul2.append(el('li', t)); st.append(ul2);
  st.append(el('h2', PAGE.h4));
  const table = document.createElement('table'), head = document.createElement('tr');
  for (const h of PAGE.cmdHead) { const th = document.createElement('th'); th.textContent = h; head.append(th); } table.append(head);
  const shell = [['ls', lang === 'ko' ? '실행할 수 있는 프로그램' : 'list the programs', 'ls'], ['./photoelastic', lang === 'ko' ? '장치 프로그램을 연다' : 'open the apparatus program', './photoelastic'], ['clear', lang === 'ko' ? '화면을 지운다' : 'clear the screen', 'clear']];
  for (const [c, d, e] of [...shell, ...HELP[lang]]) { const tr = document.createElement('tr'); const td = document.createElement('td'), code = document.createElement('code'); code.textContent = c; td.append(code); const td3 = document.createElement('td'), c3 = document.createElement('code'); c3.textContent = e; td3.append(c3); tr.append(td, el('td', d), td3); table.append(tr); }
  st.append(table);
  const foot = document.createElement('footer'); foot.textContent = lang === 'ko' ? '측정 기록은 이 브라우저에만 저장된다. CSV로 받아 두어라.' : 'Records are stored in this browser only. Download them as CSV.'; st.append(foot);
}

function line(text, kind = '', keep = true) {
  const n = document.createElement('pre'); n.className = 'entry ' + kind; n.textContent = text; screen.append(n); screen.scrollTop = screen.scrollHeight;
  if (keep) saved.push({text, kind});
}
function setPrompt() { $('prompt').textContent = inside ? INSIDE : SHELL; }
function download(text, name, type = 'text/plain;charset=utf-8') { const blob = new Blob([text], {type}), url = URL.createObjectURL(blob), a = document.createElement('a'); a.href = url; a.download = name; document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
function downloadCsv() { download(lab.csv(), 'hpho-mock1-e2-records.csv', 'text/csv;charset=utf-8'); return lab.S.records.length; }
function mode(cmd, focus = true) { cmd = embedded || cmd; $('problem').hidden = cmd; $('terminal').hidden = !cmd; $('problemTab').setAttribute('aria-selected', String(!cmd)); $('cmdTab').setAttribute('aria-selected', String(cmd)); if (cmd && focus) $('command').focus(); }

function enter() {
  inside = true; setPrompt();
  if (saved.length) { line(T.restored, 'notice', false); }
  line(T.banner + clockText(lab.S.clock) + '\nhelp');
}
function accept(input) {
  input = input.trim(); if (!input) return;
  commandHistory.push(input); historyIndex = commandHistory.length;
  line($('prompt').textContent + input, 'typed');
  if (input === 'clear') { screen.replaceChildren(); saved = []; persist(); return; }
  if (!inside) {
    if (input === 'ls') line('photoelastic');
    else if (['./photoelastic', 'photoelastic', 'photoelastic.exe'].includes(input)) enter();
    else if (input === 'help') line('ls\n./photoelastic\nclear');
    else line(input + ': command not found', 'error');
    persist(); return;
  }
  if (['exit', 'quit'].includes(input)) { inside = false; setPrompt(); persist(); return; }
  if (input === 'csv') { const n = downloadCsv(); line(lang === 'ko' ? `기록 ${n}개를 CSV로 내려받았다.` : `Downloaded ${n} records as CSV.`); persist(); return; }
  let r;
  try { r = lab.exec(input); } catch (e) { console.error(e); r = {ok: false, text: lang === 'ko' ? '명령을 처리하지 못했다.' : 'The command could not be processed.'}; }
  if (r.reset) {
    data = fresh(); lab = new Lab(data.params, data.state, lang); saved = [];
    screen.replaceChildren(); line(r.text, 'notice'); line(T.banner + clockText(lab.S.clock) + '\nhelp');
  } else line(r.text, r.ok ? '' : 'error');
  persist();
}

// header, theme, tabs
$('hTitle').textContent = T.title; $('hSub').textContent = T.sub; $('meta').textContent = T.meta; $('title').textContent = T.title; document.title = T.title + ' · HaslaLab';
$('problemTab').textContent = T.problem; $('sheet').textContent = T.sheet; $('back').textContent = T.back; $('theme').setAttribute('aria-label', T.themeLabel);
$('sheet').href = `../../hpho/samples/mock-1/${lang}/E2-answer.pdf`; $('back').href = '../../?lang=' + lang + '#/hpho';
$('clear').textContent = T.clear; $('saveLog').textContent = T.saveLog; $('downloadCsv').textContent = T.csv;
if (lang === 'en') { $('terminal').setAttribute('aria-label', 'Experiment command terminal'); $('screen').setAttribute('aria-label', 'Experiment log'); $('command').setAttribute('aria-label', 'Experiment command'); document.querySelector('header nav').setAttribute('aria-label', 'Experiment views'); }
const selectedTheme = q.get('theme'); let storedTheme; try { storedTheme = localStorage.getItem('hlTheme'); } catch {}
document.body.dataset.theme = selectedTheme === 'dark' || selectedTheme !== 'light' && (storedTheme === 'dark' || !storedTheme && matchMedia('(prefers-color-scheme:dark)').matches) ? 'dark' : 'light';
$('theme').onclick = () => { document.body.dataset.theme = document.body.dataset.theme === 'dark' ? 'light' : 'dark'; };
$('problemTab').onclick = () => mode(false); $('cmdTab').onclick = () => mode(true);
if (embedded) window.addEventListener('message', e => { if (e.source === parent && e.origin === location.origin && e.data?.type === 'haslalab-experiment-theme' && ['dark', 'light'].includes(e.data.theme)) document.body.dataset.theme = e.data.theme; });

$('bar').onsubmit = e => { e.preventDefault(); const v = $('command').value; $('command').value = ''; accept(v); };
$('command').onkeydown = e => {
  if (e.key === 'ArrowUp' || e.key === 'ArrowDown') { e.preventDefault(); historyIndex = Math.max(0, Math.min(commandHistory.length, historyIndex + (e.key === 'ArrowUp' ? -1 : 1))); $('command').value = commandHistory[historyIndex] || ''; }
  if (e.ctrlKey && e.key.toLowerCase() === 'c' && !window.getSelection()?.toString()) { e.preventDefault(); $('command').value = ''; if (inside) { inside = false; setPrompt(); } line('^C', 'notice', false); }
};
$('clear').onclick = () => { screen.replaceChildren(); saved = []; persist(); $('command').focus(); };
$('saveLog').onclick = () => download([...screen.querySelectorAll('.entry')].map(n => n.textContent).join('\n\n') + '\n', 'hpho-mock1-e2-log.txt');
$('downloadCsv').onclick = () => { const n = downloadCsv(); if (!n) line(T.nofile, 'notice', false); };

buildPage();
line('HaslaLab Experimental Laboratory\n\n./photoelastic', 'notice', false);
for (const s of saved) line(s.text, s.kind, false);
if (embedded) { mode(true, false); accept('./photoelastic'); }
else if (q.get('view') === 'cmd') mode(true);
