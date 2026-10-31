/* Console emulator for the olympiad programs whose originals are command-line
   executables, with a second, experiment mode.  A program module defines a global PROGRAM:

     PROGRAM = { title, subtitle, notes: [...], run: async function (term) {...},
                 lab: { ... } }            // optional, see below
   A page with no run (no original program) is experiment mode only: the bench, without the CMD tab.

   CMD mode drives the screen through term.write / term.writeln / term.ask, so the prompts and the
   streamed output land on screen exactly as the original executable prints them; what is typed
   appears right after the prompt, as in a terminal.

   Experiment mode puts the same engine behind apparatus the user works by hand (sim/handlab.js):

     lab: {
       intro: {ko, en}, howto: {ko: ['...'], en: ['...']},  // shown beside the bench
       mount: function (host, ctx) {}                       // build the 3-D bench (sim/bench3d.js) in host;
     }                                                      // ctx.lang() is 'ko' or 'en', ctx.S the session errors

   Every text may be a string or {ko, en}; the page follows ?lang=en and the 한국어/English buttons.
   The program itself prints what the original executable prints, in English.
*/
(function () {
  var out, inp, screen, pending = null, history = [], hpos = 0, live = null;

  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function scroll() { screen.scrollTop = screen.scrollHeight; }

  /* every run gets its own term; a restarted run's old term goes quiet instead of writing on */
  function makeTerm() {
    var t = { alive: true };
    t.write = function (s) { if (!t.alive) return; out.insertAdjacentHTML('beforeend', esc(s)); scroll(); };
    t.writeln = function (s) { t.write((s === undefined ? '' : s) + '\n'); };
    t.echo = function (s) {
      if (!t.alive) return;
      out.insertAdjacentHTML('beforeend', '<span class="in">' + esc(s) + '</span>\n'); scroll();
    };
    t.clear = function () { if (t.alive) out.innerHTML = ''; };
    /* write the prompt and wait for a line, typed right after it */
    t.ask = function (prompt) {
      if (!t.alive) return new Promise(function () {});
      t.write(prompt === undefined ? '' : prompt);
      inp.hidden = false; inp.value = ''; sizeInput();
      focusInp();
      scroll();
      return new Promise(function (resolve) { pending = resolve; });
    };
    t.yieldFrame = function () { return new Promise(function (r) { setTimeout(r, 0); }); };
    return t;
  }
  function focusInp() { if (mode === 'cmd' && !inp.hidden) inp.focus({ preventScroll: true }); }
  function sizeInput() { inp.style.width = Math.max(2, inp.value.length + 2) + 'ch'; }

  function submit() {
    if (!pending) return;
    var v = inp.value;
    inp.value = ''; inp.hidden = true;
    if (v !== '') { history.push(v); hpos = history.length; }
    live.echo(v);
    var done = pending; pending = null; done(v);
  }

  var CSS = '' +
    'body{height:100vh;display:flex;flex-direction:column;overflow:hidden}' +
    'header .modes{display:flex;gap:6px;margin-top:9px}' +
    'header .modes button{padding:6px 14px;border-radius:5px}' +
    'header .modes button.on{background:var(--accent);border-color:var(--accent);color:#0c0c0c;font-weight:600}' +
    '#cmdpane{flex:1;display:flex;flex-direction:column;min-height:0}' +
    '#cmdpane[hidden]{display:none}' +
    '#screen{cursor:text}' +
    '#screen #inp{display:inline;background:transparent;border:0;outline:0;color:#9cdcfe;padding:0;margin:0;' +
      'font:inherit;min-width:2ch;max-width:100%;caret-color:#cccccc}' +
    '#screen #inp[hidden]{display:none}' +
    '#labpane{flex:1;overflow:auto;padding:14px 16px 24px}' +
    '#labpane[hidden]{display:none}' +
    '#labpane .lgrid{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:14px;align-items:start;max-width:1600px;margin:0 auto}' +
    '@media (max-width:1100px){#labpane .lgrid{grid-template-columns:1fr}}' +
    '#labpane .card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px}' +
    '#labpane .lside{display:flex;flex-direction:column;gap:14px;min-width:0}' +
    '#labpane h3{margin:0 0 8px;font-size:13px;color:#e8e8e8;font-weight:600}' +
    '#labpane .lcap{margin-top:7px;color:var(--dim);font-size:12.5px;line-height:1.55}' +
    '#labpane .lhow{margin:0;padding-left:18px;color:#c8c8c8;font-size:12.5px;line-height:1.6}' +
    'header{position:relative}header>.lang{position:absolute;top:10px;right:14px;display:flex;align-items:center}' +
    'header>.lang .lb{display:flex;border:1px solid var(--line);border-radius:7px;overflow:hidden}' +
    'header>.lang .lb button{border:0;border-radius:0;padding:6px 13px}header>.lang .lb button.on{background:var(--accent);color:#0c0c0c;font-weight:600}' +
    'header h1,header>p{padding-right:220px}@media (max-width:700px){header h1,header>p{padding-right:0}header>.lang{position:static;margin-top:8px}}';

  var mode = 'cmd', lab = null, mounted = false, lang = new URLSearchParams(location.search).get('lang') === 'en' ? 'en' : 'ko';
  var langCbs = [];
  function tx(v) { return v && typeof v === 'object' && !Array.isArray(v) ? (v[lang] !== undefined ? v[lang] : v.ko) : v; }
  var UI = { ko: { about: '이 프로그램에 대하여', cmd: 'CMD 모드', lab: '실험 모드', restart: '다시 시작 (Ctrl+C)', copy: '화면 복사', copied: '복사됨',
                   save: '.txt로 저장', how: '조작', note: '실험 노트', noteN: '값은 장비에서 직접 읽어 여기에 적습니다. 이 브라우저에 저장됩니다.' },
             en: { about: 'About this program', cmd: 'CMD mode', lab: 'Experiment mode', restart: 'Restart (Ctrl+C)', copy: 'Copy screen', copied: 'Copied',
                   save: 'Save as .txt', how: 'How to', note: 'Lab notebook', noteN: 'Read the values off the instruments and write them here. Saved in this browser.' } };

  window.addEventListener('DOMContentLoaded', function () {
    document.title = PROGRAM.title;
    lab = PROGRAM.lab || null;
    var style = document.createElement('style'); style.textContent = CSS; document.head.appendChild(style);

    var head = document.createElement('header');
    document.body.appendChild(head);
    function renderHead() {
      document.title = tx(PROGRAM.title); document.documentElement.lang = lang;
      var notes = tx(PROGRAM.notes);
      head.innerHTML =
        '<div class="lang"><div class="lb"><button data-l="ko">한국어</button><button data-l="en">English</button></div></div>' +
        '<h1>' + esc(tx(PROGRAM.title)) + '</h1>' +
        (PROGRAM.subtitle ? '<p>' + esc(tx(PROGRAM.subtitle)) + '</p>' : '') +
        (notes && notes.length
          ? '<details><summary>' + UI[lang].about + '</summary><ul>' + notes.map(function (n) { return '<li>' + n + '</li>'; }).join('') + '</ul></details>'
          : '') +
        (lab && PROGRAM.run ? '<nav class="modes"><button data-m="cmd">' + UI[lang].cmd + '</button><button data-m="lab">' + UI[lang].lab + '</button></nav>' : '');
      head.querySelectorAll('.lb button').forEach(function (b) { b.classList.toggle('on', b.dataset.l === lang); b.onclick = function () { setLang(b.dataset.l); }; });
      head.querySelectorAll('.modes button').forEach(function (b) { b.classList.toggle('on', b.dataset.m === mode); b.onclick = function () { setMode(b.dataset.m); }; });
      var full = document.getElementById('hl-full'); if (full && full.parentNode !== document.body) head.querySelector('.lang').appendChild(full);
    }
    function setLang(l) {
      lang = l; var u = new URL(location.href); u.searchParams.set('lang', l); window.history.replaceState(null, '', u);
      renderHead(); renderTools(); renderLabText(); langCbs.forEach(function (f) { f(lang); });
    }
    window.HLlang = function () { return lang; };
    renderHead();

    /* ---- CMD mode ---- */
    var cmd = document.createElement('div'); cmd.id = 'cmdpane';
    screen = document.createElement('div'); screen.id = 'screen';
    out = document.createElement('span'); out.id = 'out';
    inp = document.createElement('input'); inp.id = 'inp'; inp.autocomplete = 'off'; inp.spellcheck = false; inp.hidden = true;
    screen.appendChild(out); screen.appendChild(inp);
    cmd.appendChild(screen);
    var tools = document.createElement('div'); tools.id = 'tools';
    var bRestart = button(''), bCopy = button(''), bSave = button('');
    function renderTools() { bRestart.textContent = UI[lang].restart; bCopy.textContent = UI[lang].copy; bSave.textContent = UI[lang].save; }
    renderTools();
    tools.appendChild(bRestart); tools.appendChild(bCopy); tools.appendChild(bSave);
    cmd.appendChild(tools);
    document.body.appendChild(cmd);

    inp.addEventListener('input', sizeInput);
    inp.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { submit(); e.preventDefault(); }
      else if (e.key === 'ArrowUp') { if (hpos > 0) { hpos--; inp.value = history[hpos]; sizeInput(); } e.preventDefault(); }
      else if (e.key === 'ArrowDown') {
        if (hpos < history.length - 1) { hpos++; inp.value = history[hpos]; } else { hpos = history.length; inp.value = ''; }
        sizeInput(); e.preventDefault();
      }
    });
    /* Ctrl+C stops the program and starts it again, unless there is text selected to copy */
    document.addEventListener('keydown', function (e) {
      if (mode !== 'cmd' || !e.ctrlKey || (e.key !== 'c' && e.key !== 'C')) return;
      if (window.getSelection().toString()) return;
      start(); e.preventDefault();
    });
    screen.addEventListener('click', function () { if (!window.getSelection().toString()) focusInp(); });
    bRestart.addEventListener('click', start);
    bCopy.addEventListener('click', function () {
      navigator.clipboard.writeText(screen.textContent).then(function () {
        bCopy.textContent = UI[lang].copied; setTimeout(function () { bCopy.textContent = UI[lang].copy; }, 1200);
      }, function () {});
    });
    bSave.addEventListener('click', function () { download(tx(PROGRAM.title).replace(/[^\w.-]+/g, '_') + '.txt', out.textContent); });

    function start() {
      if (live) live.alive = false;
      pending = null; inp.value = ''; inp.hidden = true; out.innerHTML = '';
      live = makeTerm();
      var t = live;
      Promise.resolve(PROGRAM.run(t)).catch(function (err) { t.writeln('\n[' + err.message + ']'); });
    }
    if (PROGRAM.run) start(); else cmd.hidden = true;

    /* ---- experiment mode ---- */
    if (lab) {
      buildLab();
      var want = new URLSearchParams(location.search).get('mode');
      if (!want) { try { want = localStorage.getItem('hl-mode:' + location.pathname); } catch (e) {} }
      setMode(!PROGRAM.run || want === 'lab' || want === 'sim' ? 'lab' : 'cmd');
    }
  });

  function button(t) { var b = document.createElement('button'); b.textContent = t; return b; }
  function download(name, text, type) {
    var blob = new Blob([text], { type: (type || 'text/plain') + ';charset=utf-8' });
    var a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
  }

  function setMode(m) {
    mode = m;
    document.getElementById('cmdpane').hidden = m !== 'cmd';
    document.getElementById('labpane').hidden = m !== 'lab';
    document.querySelectorAll('header .modes button').forEach(function (b) { b.classList.toggle('on', b.dataset.m === m); });
    try { localStorage.setItem('hl-mode:' + location.pathname, m); } catch (e) {}
    if (m === 'lab') { if (!mounted) mountLab(); dispatchEvent(new Event('resize')); } else focusInp();
  }

  function buildLab() {
    var pane = document.createElement('div'); pane.id = 'labpane'; pane.hidden = true;
    pane.innerHTML =
      '<div class="lgrid">' +
        '<section class="card"><div id="lbench"></div><div class="lcap" id="lintro"></div></section>' +
        '<div class="lside">' +
          '<section class="card"><h3 id="lhowH"></h3><ul class="lhow" id="lhow"></ul></section>' +
          '<section class="card"><h3 id="lnoteH"></h3><div id="lnote"></div><div class="lcap" id="lnoteN"></div></section>' +
        '</div>' +
      '</div>';
    document.body.insertBefore(pane, document.getElementById('cmdpane').nextSibling);
    renderLabText();
  }
  function renderLabText() {
    if (!lab || !document.getElementById('lintro')) return;
    document.getElementById('lintro').innerHTML = tx(lab.intro) || '';
    var how = tx(lab.howto) || [];
    document.getElementById('lhowH').textContent = UI[lang].how;
    document.getElementById('lhow').innerHTML = how.map(function (h) { return '<li>' + h + '</li>'; }).join('');
    document.getElementById('lnoteH').textContent = UI[lang].note;
    document.getElementById('lnoteN').textContent = UI[lang].noteN;
    var ta = document.querySelector('#lnote textarea'); if (ta && lab.notePlaceholder) ta.placeholder = tx(lab.notePlaceholder);
  }
  function mountLab() {
    mounted = true;
    var S = HL.session(location.pathname);
    lab.mount(document.getElementById('lbench'), { lang: function () { return lang; }, S: S, onLang: function (f) { langCbs.push(f); } });
    HL.notebook(document.getElementById('lnote'), location.pathname, tx(lab.notePlaceholder) || '');
  }
})();
