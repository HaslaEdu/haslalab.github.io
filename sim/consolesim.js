/* Console emulator for the olympiad programs whose originals are command-line
   executables, with a second, simulation mode.  A program module defines a global PROGRAM:

     PROGRAM = { title, subtitle, notes: [...], run: async function (term) {...},
                 sim: { ... } }            // optional, see below

   CMD mode drives the screen through term.write / term.writeln / term.ask, so the prompts and the
   streamed output land on screen exactly as the original executable prints them; what is typed
   appears right after the prompt, as in a terminal.

   Simulation mode feeds the same engine from a form and draws the apparatus:

     sim: {
       intro:   'what the picture shows',
       fields:  [{ id, label, unit, lo, hi, step, quant, value, type: 'number' | 'text', hint }],
       columns: ['#', ...],                // the measurement table
       aspect:  0.6,                       // canvas height / width
       measure: function (vals) { return { rows: [[...]], st: {...}, ms: 1500 } },   // may be async
       check:   function (vals) { return 'error text' or null },                    // optional
       draw:    function (g, W, H, s) {}   // s = { vals, st, p (0..1 of the run), done, hist }
       replace: false                      // true: each run replaces the table
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
    '#cmdpane[hidden],#simpane[hidden]{display:none}' +
    '#screen{cursor:text}' +
    '#screen #inp{display:inline;background:transparent;border:0;outline:0;color:#9cdcfe;padding:0;margin:0;' +
      'font:inherit;min-width:2ch;max-width:100%;caret-color:#cccccc}' +
    '#screen #inp[hidden]{display:none}' +
    '#simpane{flex:1;overflow:auto;padding:14px 16px 24px}' +
    '#simpane .sgrid{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(320px,1fr);gap:14px;align-items:start;max-width:1500px;margin:0 auto}' +
    '@media (max-width:980px){#simpane .sgrid{grid-template-columns:1fr}}' +
    '#simpane .card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px}' +
    '#simpane h3{margin:0 0 8px;font-size:13px;color:#e8e8e8;font-weight:600}' +
    '#scv{display:block;width:100%;border-radius:6px;background:#0b0d10}' +
    '#scap{margin-top:7px;color:var(--dim);font-size:12.5px;line-height:1.5}' +
    '#sfields{display:grid;grid-template-columns:1fr 1fr;gap:10px 12px}' +
    '#sfields .f{display:flex;flex-direction:column;gap:3px;min-width:0}' +
    '#sfields .f.wide{grid-column:1/-1}' +
    '#sfields label{font-size:12.5px;color:#e0e0e0}' +
    '#sfields .rg{font-size:11.5px;color:var(--dim)}' +
    '#sfields input[type=text],#sfields input[type=number]{background:#0c0c0c;color:#9cdcfe;border:1px solid var(--line);border-radius:4px;' +
      'padding:5px 8px;font:13px ui-monospace,Consolas,monospace;width:100%}' +
    '#sfields input[type=range]{width:100%;accent-color:var(--accent)}' +
    '#sgo{margin-top:12px;padding:8px 22px;font-weight:600;background:var(--accent);color:#0c0c0c;border-color:var(--accent)}' +
    '#sgo:disabled{opacity:.5;cursor:default}' +
    '#serr{color:#f48771;font-size:12.5px;min-height:18px;margin-top:6px;white-space:pre-wrap}' +
    '#stbl{width:100%;border-collapse:collapse;font:12.5px ui-monospace,Consolas,monospace}' +
    '#stbl th{position:sticky;top:0;background:#1b1b1b;color:#dcdcaa;font-weight:600;text-align:right;padding:5px 6px;border-bottom:1px solid var(--line)}' +
    '#stbl td{text-align:right;padding:4px 6px;border-bottom:1px solid #202020;color:#d4d4d4;white-space:nowrap}' +
    '#stbl tr.new td{background:rgba(78,201,176,.12)}' +
    '#stwrap{max-height:420px;overflow:auto;border:1px solid var(--line);border-radius:6px}' +
    '#stools{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap}' +
    '#sempty{color:var(--dim);font-size:12.5px;padding:14px;text-align:center}';

  var cols = [], liveReq = false, mode = 'cmd', sim = null, simState = null, hist = [], rows = [], anim = null, cv, g;

  window.addEventListener('DOMContentLoaded', function () {
    document.title = PROGRAM.title;
    sim = PROGRAM.sim || null;
    var style = document.createElement('style'); style.textContent = CSS; document.head.appendChild(style);

    var head = document.createElement('header');
    head.innerHTML =
      '<h1>' + esc(PROGRAM.title) + '</h1>' +
      (PROGRAM.subtitle ? '<p>' + esc(PROGRAM.subtitle) + '</p>' : '') +
      (PROGRAM.notes && PROGRAM.notes.length
        ? '<details><summary>이 프로그램에 대하여</summary><ul>' +
          PROGRAM.notes.map(function (n) { return '<li>' + n + '</li>'; }).join('') + '</ul></details>'
        : '') +
      (sim ? '<nav class="modes"><button data-m="cmd">CMD 모드</button><button data-m="sim">시뮬레이션 모드</button></nav>' : '');
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

    /* ---- simulation mode ---- */
    if (sim) {
      buildSim();
      var want = new URLSearchParams(location.search).get('mode');
      if (!want) { try { want = localStorage.getItem('hl-mode:' + location.pathname); } catch (e) {} }
      setMode(want === 'sim' ? 'sim' : 'cmd');
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
    document.getElementById('simpane').hidden = m !== 'sim';
    document.querySelectorAll('header .modes button').forEach(function (b) { b.classList.toggle('on', b.dataset.m === m); });
    try { localStorage.setItem('hl-mode:' + location.pathname, m); } catch (e) {}
    if (m === 'sim') { layoutSim(); paint(); } else focusInp();
  }

  function buildSim() {
    var pane = document.createElement('div'); pane.id = 'simpane'; pane.hidden = true;
    var fieldsHtml = sim.fields.map(function (f) {
      var rng = f.type === 'text' ? (f.hint || '') :
        '범위: ' + f.lo + ' ~ ' + f.hi + (f.unit ? ' ' + f.unit : '');
      return '<div class="f' + (f.type === 'text' || f.wide ? ' wide' : '') + '"><label for="sf-' + f.id + '">' + f.label +
        (f.unit ? ' (' + f.unit + ')' : '') + '</label><span class="rg">' + rng + '</span>' +
        (f.type === 'text'
          ? '<input type="text" id="sf-' + f.id + '" value="' + esc(f.value) + '" spellcheck="false" autocomplete="off">'
          : '<input type="number" id="sf-' + f.id + '" value="' + f.value + '" step="any">' +
            '<input type="range" id="sr-' + f.id + '" min="' + f.lo + '" max="' + f.hi + '" step="' + (f.step || 'any') + '" value="' + f.value + '">') +
        '</div>';
    }).join('');
    pane.innerHTML =
      '<div class="sgrid">' +
        '<section class="card"><canvas id="scv"></canvas><div id="scap">' + (sim.intro || '') + '</div></section>' +
        '<div style="display:flex;flex-direction:column;gap:14px;min-width:0">' +
          '<section class="card"><h3>입력값</h3><div id="sfields">' + fieldsHtml + '</div>' +
            '<button id="sgo">' + (sim.goLabel || '측정') + '</button><div id="serr"></div></section>' +
          '<section class="card"><h3>측정 기록</h3><div id="stwrap"><table id="stbl"><thead><tr></tr></thead><tbody></tbody></table><div id="sempty">아직 기록이 없습니다. 값을 넣고 측정하세요.</div></div>' +
            '<div id="stools"><button id="scsv">CSV 저장</button><button id="scopy">표 복사</button><button id="sclear">기록 지우기</button></div>' +
            (sim.tableNote ? '<div id="scap" style="margin-top:8px">' + sim.tableNote + '</div>' : '') +
          '</section>' +
        '</div>' +
      '</div>';
    document.body.insertBefore(pane, document.getElementById('cmdpane').nextSibling);
    cv = document.getElementById('scv'); g = cv.getContext('2d');

    sim.fields.forEach(function (f) {
      var n = document.getElementById('sf-' + f.id), r = document.getElementById('sr-' + f.id);
      if (r) {
        r.addEventListener('input', function () { n.value = r.value; paint(); });
        n.addEventListener('input', function () { if (n.value !== '' && isFinite(+n.value)) r.value = n.value; paint(); });
      } else n.addEventListener('input', paint);
      n.addEventListener('keydown', function (e) { if (e.key === 'Enter') go(); });
    });
    document.getElementById('sgo').onclick = go;
    document.getElementById('sclear').onclick = function () { rows = []; hist = []; simState = null; table(); paint(); };
    document.getElementById('scsv').onclick = function () {
      download(PROGRAM.title.replace(/[^\w.-]+/g, '_') + '.csv',
        [cols.join(',')].concat(rows.map(function (r) { return r.join(','); })).join('\n'), 'text/csv');
    };
    document.getElementById('scopy').onclick = function () {
      var b = this;
      navigator.clipboard.writeText([cols.join('\t')].concat(rows.map(function (r) { return r.join('\t'); })).join('\n'))
        .then(function () { b.textContent = '복사됨'; setTimeout(function () { b.textContent = '표 복사'; }, 1200); }, function () {});
    };
    addEventListener('resize', function () { if (mode === 'sim') { layoutSim(); paint(); } });
    cols = typeof sim.columns === 'function' ? sim.columns(readVals(false).vals) : sim.columns;
    table();
  }

  function layoutSim() {
    var dpr = Math.min(window.devicePixelRatio || 1, 2), w = cv.parentElement.clientWidth - 24;
    var h = Math.round(Math.min(w * (sim.aspect || 0.6), window.innerHeight * 0.72));
    cv.style.height = h + 'px'; cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
    cv._w = w; cv._h = h; cv._dpr = dpr;
  }

  /* the form's values: numbers are checked against their range and rounded as the program does */
  function readVals(strict) {
    var vals = {}, err = null;
    sim.fields.forEach(function (f) {
      var raw = document.getElementById('sf-' + f.id).value;
      if (f.type === 'text') { vals[f.id] = raw; return; }
      var v = parseFloat(raw);
      if (raw.trim() === '' || isNaN(v)) { if (!err) err = f.label + ': 숫자를 넣으세요.'; v = f.value; }
      else if (v < f.lo || v > f.hi) { if (!err) err = f.label + ': 범위(' + f.lo + ' ~ ' + f.hi + ')를 벗어났습니다.'; v = Math.max(f.lo, Math.min(f.hi, v)); }
      if (f.quant) v = Math.round(v / f.quant) * f.quant;
      vals[f.id] = v;
    });
    if (strict && !err && sim.check) err = sim.check(vals);
    return { vals: vals, err: err };
  }

  function go() {
    if (anim) return;
    var r = readVals(true), errBox = document.getElementById('serr');
    errBox.textContent = r.err || '';
    if (r.err) return;
    var btn = document.getElementById('sgo'); btn.disabled = true;
    Promise.resolve(sim.measure(r.vals)).then(function (res) {
      if (!res) { btn.disabled = false; return; }
      if (res.error) { errBox.textContent = res.error; btn.disabled = false; return; }
      simState = { vals: r.vals, st: res.st };
      anim = { t0: performance.now(), ms: Math.max(1, res.ms || 1200), res: res };
      tick();
    }, function (e) { errBox.textContent = String(e && e.message || e); btn.disabled = false; });
  }

  function tick() {
    if (!anim) return;
    var p = Math.min(1, (performance.now() - anim.t0) / anim.ms);
    paint(p);
    if (p < 1) { requestAnimationFrame(tick); return; }
    var res = anim.res; anim = null;
    if (sim.replace) rows = [];
    if (typeof sim.columns === 'function') cols = sim.columns(simState.vals);
    (res.rows || []).forEach(function (row) { rows.push(row); });
    hist.push(simState);
    table(res.rows ? res.rows.length : 0);
    document.getElementById('sgo').disabled = false;
    paint(1);
  }

  function table(fresh) {
    document.querySelector('#stbl thead tr').innerHTML = cols.map(function (c) { return '<th>' + c + '</th>'; }).join('');
    var tb = document.querySelector('#stbl tbody');
    tb.innerHTML = rows.map(function (r, i) {
      return '<tr' + (fresh && i >= rows.length - fresh ? ' class="new"' : '') + '>' +
        r.map(function (c) { return '<td>' + esc(c) + '</td>'; }).join('') + '</tr>';
    }).join('');
    document.getElementById('sempty').style.display = rows.length ? 'none' : '';
    var wrap = document.getElementById('stwrap'); wrap.scrollTop = wrap.scrollHeight;
  }

  function paint(p) {
    if (!cv || mode !== 'sim') return;
    if (!cv._w) layoutSim();
    var cur = readVals(false).vals;
    g.setTransform(cv._dpr, 0, 0, cv._dpr, 0, 0);
    g.clearRect(0, 0, cv._w, cv._h);
    var running = !!anim, s;
    if (running) s = { vals: simState.vals, st: simState.st, p: p === undefined ? 0 : p, done: false, hist: hist };
    else if (simState) s = { vals: cur, st: simState.st, last: simState.vals, p: 1, done: true, hist: hist };
    else s = { vals: cur, st: null, p: 0, done: false, hist: hist };
    try { sim.draw(g, cv._w, cv._h, s); } catch (e) { console.error(e); }
  }

  /* small drawing helpers the program modules share */
  window.SIMDRAW = {
    text: function (g, s, x, y, col, size, align, bold, font) {
      g.fillStyle = col; g.font = (bold ? '600 ' : '') + size + 'px ' + (font || 'ui-sans-serif,system-ui,"Segoe UI","Malgun Gothic",sans-serif');
      g.textAlign = align || 'left'; g.textBaseline = 'middle'; g.fillText(s, x, y);
    },
    mono: 'ui-monospace,Consolas,"Courier New",monospace',
    lcd: function (g, x, y, w, h, txt, col) {
      g.fillStyle = '#0d1a12'; g.fillRect(x, y, w, h);
      g.strokeStyle = '#2a3a30'; g.lineWidth = 1; g.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
      SIMDRAW.text(g, txt, x + w - 8, y + h / 2 + 1, col || '#7dff9b', Math.round(h * 0.62), 'right', true, SIMDRAW.mono);
    },
    arrow: function (g, x0, y0, x1, y1, col, w) {
      var a = Math.atan2(y1 - y0, x1 - x0), L = 7 + (w || 1.5) * 2;
      g.strokeStyle = col; g.fillStyle = col; g.lineWidth = w || 1.5;
      g.beginPath(); g.moveTo(x0, y0); g.lineTo(x1, y1); g.stroke();
      g.beginPath(); g.moveTo(x1, y1); g.lineTo(x1 - L * Math.cos(a - 0.4), y1 - L * Math.sin(a - 0.4));
      g.lineTo(x1 - L * Math.cos(a + 0.4), y1 - L * Math.sin(a + 0.4)); g.closePath(); g.fill();
    },
    ease: function (p) { return p < 0 ? 0 : p > 1 ? 1 : p; },
    repaint: function () { paint(); },
    /* a picture that keeps moving after the run (electrons, a swinging needle) asks for the next frame */
    live: function () {
      if (liveReq) return; liveReq = true;
      requestAnimationFrame(function () { liveReq = false; if (!anim) paint(); });
    }
  };
})();
