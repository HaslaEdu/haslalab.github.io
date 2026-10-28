/* Console emulator for the olympiad programs whose originals are command-line
   executables, with a second, experiment mode.  A program module defines a global PROGRAM:

     PROGRAM = { title, subtitle, notes: [...], run: async function (term) {...},
                 lab: { ... } }            // optional, see below

   CMD mode drives the screen through term.write / term.writeln / term.ask, so the prompts and the
   streamed output land on screen exactly as the original executable prints them; what is typed
   appears right after the prompt, as in a terminal.

   Experiment mode puts the same engine behind apparatus the user works by hand (sim/handlab.js):

     lab: {
       intro: 'what is on the bench', howto: ['...'],     // shown beside the bench
       aspect: 0.62, speeds: [1, 10],                      // the bench's shape, the time speeds
       init: function (S) {},                              // S = HL.session(...) for the instrument errors
       frame: function (ui) {}                             // draw and work the bench every frame
     }
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
    '#labpane .lhow{margin:0;padding-left:18px;color:#c8c8c8;font-size:12.5px;line-height:1.6}';

  var mode = 'cmd', lab = null, bench = null;

  window.addEventListener('DOMContentLoaded', function () {
    document.title = PROGRAM.title;
    lab = PROGRAM.lab || null;
    var style = document.createElement('style'); style.textContent = CSS; document.head.appendChild(style);

    var head = document.createElement('header');
    head.innerHTML =
      '<h1>' + esc(PROGRAM.title) + '</h1>' +
      (PROGRAM.subtitle ? '<p>' + esc(PROGRAM.subtitle) + '</p>' : '') +
      (PROGRAM.notes && PROGRAM.notes.length
        ? '<details><summary>이 프로그램에 대하여</summary><ul>' +
          PROGRAM.notes.map(function (n) { return '<li>' + n + '</li>'; }).join('') + '</ul></details>'
        : '') +
      (lab ? '<nav class="modes"><button data-m="cmd">CMD 모드</button><button data-m="lab">실험 모드</button></nav>' : '');
    document.body.appendChild(head);

    /* ---- CMD mode ---- */
    var cmd = document.createElement('div'); cmd.id = 'cmdpane';
    screen = document.createElement('div'); screen.id = 'screen';
    out = document.createElement('span'); out.id = 'out';
    inp = document.createElement('input'); inp.id = 'inp'; inp.autocomplete = 'off'; inp.spellcheck = false; inp.hidden = true;
    screen.appendChild(out); screen.appendChild(inp);
    cmd.appendChild(screen);
    var tools = document.createElement('div'); tools.id = 'tools';
    var bRestart = button('다시 시작 (Ctrl+C)'), bCopy = button('화면 복사'), bSave = button('.txt로 저장');
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
        bCopy.textContent = '복사됨'; setTimeout(function () { bCopy.textContent = '화면 복사'; }, 1200);
      }, function () {});
    });
    bSave.addEventListener('click', function () { download(PROGRAM.title.replace(/[^\w.-]+/g, '_') + '.txt', out.textContent); });

    function start() {
      if (live) live.alive = false;
      pending = null; inp.value = ''; inp.hidden = true; out.innerHTML = '';
      live = makeTerm();
      var t = live;
      Promise.resolve(PROGRAM.run(t)).catch(function (err) { t.writeln('\n[' + err.message + ']'); });
    }
    start();

    /* ---- experiment mode ---- */
    if (lab) {
      buildLab();
      var want = new URLSearchParams(location.search).get('mode');
      if (!want) { try { want = localStorage.getItem('hl-mode:' + location.pathname); } catch (e) {} }
      setMode(want === 'lab' || want === 'sim' ? 'lab' : 'cmd');
      head.querySelectorAll('.modes button').forEach(function (b) { b.onclick = function () { setMode(b.dataset.m); }; });
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
    if (m === 'lab') { if (bench) bench.layout(); } else focusInp();
  }

  function buildLab() {
    var pane = document.createElement('div'); pane.id = 'labpane'; pane.hidden = true;
    pane.innerHTML =
      '<div class="lgrid">' +
        '<section class="card"><div id="lbench"></div><div class="lcap">' + (lab.intro || '') + '</div></section>' +
        '<div class="lside">' +
          (lab.howto ? '<section class="card"><h3>조작</h3><ul class="lhow">' + lab.howto.map(function (h) { return '<li>' + h + '</li>'; }).join('') + '</ul></section>' : '') +
          '<section class="card"><h3>실험 노트</h3><div id="lnote"></div>' +
            '<div class="lcap">값은 장비에서 직접 읽어 여기에 적습니다. 이 브라우저에 저장됩니다.</div></section>' +
        '</div>' +
      '</div>';
    document.body.insertBefore(pane, document.getElementById('cmdpane').nextSibling);
    var S = HL.session(location.pathname);
    if (lab.init) lab.init(S);
    bench = HL.lab(document.getElementById('lbench'), { aspect: lab.aspect, speeds: lab.speeds, keys: lab.keys, wheelFree: lab.wheelFree,
      hint: '두 번 클릭: 확대해서 보기', frame: function (ui) { if (mode === 'lab') lab.frame(ui); } });
    HL.notebook(document.getElementById('lnote'), location.pathname, lab.notePlaceholder || '예) h = 1200 m, r = 10 cm, ρ = 1.00 g/cm³ → t = …, s = …');
  }
})();
