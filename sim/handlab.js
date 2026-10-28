/* HaslaLab hands-on bench: the shared engine of the "experiment mode" pages.

   A page draws its apparatus every frame with plain canvas calls and asks the engine, at the
   same time, whether the user is touching a part (immediate-mode UI):

     const lab = HL.lab(host, { aspect: 0.62, speeds: [1, 10], frame: function (ui) { ... } });

   Inside frame(ui):
     ui.g, ui.W, ui.H      the canvas and its logical size (1000 wide; H = 1000 * aspect)
     ui.t, ui.dt           scene time and its step (s), already multiplied by the time speed
     ui.hit(id, shape, o)  register a touchable part drawn under the current transform; returns its
                           events since the last frame: {hover, down, press, click, release, dx, dy,
                           x, y, wheel, dbl}.  shape: {x,y,w,h} | {cx,cy,r} | function(x,y) -> bool
                           o.zoom = {x,y,w,h, title}: double-click opens that area as a close-up
     ui.pass               'main' or 'zoom' (the close-up draws the same scene through a lens)
     ui.keys               keys pressed since the last frame

   The close-up is a second canvas over the page that draws the same frame() under a magnifying
   transform, so every knob and button keeps working in it; the wheel zooms it, a drag on an empty
   spot pans it.  Systematic errors of the instruments come from HL.session(): one set per visit. */
(function () {
  var HL = window.HL = {};

  /* ---------- one set of instrument errors per visit ---------- */
  function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; var t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  HL.session = function (key) {
    var seed = 0;
    try { seed = +sessionStorage.getItem('hl-seed:' + key) || 0; } catch (e) {}
    if (!seed) { seed = 1 + Math.floor(Math.random() * 2147483646); try { sessionStorage.setItem('hl-seed:' + key, seed); } catch (e) {} }
    var r = mulberry32(seed), memo = {};
    function n() { var u = 1 - r(), v = r(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); }
    return {
      seed: seed,
      /* a fixed offset for one named instrument, drawn once: normal with this sigma */
      sys: function (name, sigma) { if (!(name in memo)) memo[name] = n() * sigma; return memo[name]; },
      uni: function (name, lo, hi) { if (!(name in memo)) memo[name] = lo + (hi - lo) * r(); return memo[name]; }
    };
  };
  HL.gauss = function (s) { var u = 1 - Math.random(), v = Math.random(); return s * Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); };

  var CSS = '' +
    '.hl-lab{position:relative;user-select:none;-webkit-user-select:none}' +
    '.hl-lab canvas.hl-main{display:block;width:100%;border-radius:6px;background:#15181d;touch-action:none}' +
    '.hl-bar{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-top:8px;font-size:12.5px;color:#9aa3ab}' +
    '.hl-bar button{padding:4px 11px}.hl-bar button.on{background:#4ec9b0;border-color:#4ec9b0;color:#0c0c0c;font-weight:600}' +
    '.hl-zoom{position:fixed;inset:0;z-index:80;background:rgba(6,8,10,.72);display:flex;align-items:center;justify-content:center}' +
    '.hl-zoom[hidden]{display:none}' +
    '.hl-zbox{background:#1b1f25;border:1px solid #353b43;border-radius:10px;padding:8px 10px 10px;box-shadow:0 10px 40px rgba(0,0,0,.5)}' +
    '.hl-zbar{display:flex;justify-content:space-between;align-items:center;gap:12px;color:#c9d1d9;font-size:12.5px;margin-bottom:6px}' +
    '.hl-zbox canvas{display:block;border-radius:6px;background:#15181d;touch-action:none}' +
    '.hl-note{width:100%;min-height:220px;resize:vertical;background:#0c0c0c;color:#d4d4d4;border:1px solid #2a2a2a;border-radius:6px;' +
      'padding:8px;font:12.5px/1.5 ui-monospace,Consolas,monospace}';
  var styled = false;

  HL.lab = function (host, opts) {
    if (!styled) { var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st); styled = true; }
    var W = 1000, H = Math.round(1000 * (opts.aspect || 0.62));
    var wrap = document.createElement('div'); wrap.className = 'hl-lab';
    var cv = document.createElement('canvas'); cv.className = 'hl-main'; wrap.appendChild(cv);
    var bar = document.createElement('div'); bar.className = 'hl-bar'; wrap.appendChild(bar);
    host.appendChild(wrap);
    var zoomEl = document.createElement('div'); zoomEl.className = 'hl-zoom'; zoomEl.hidden = true;
    zoomEl.innerHTML = '<div class="hl-zbox"><div class="hl-zbar"><span></span><button>닫기 (Esc)</button></div><canvas></canvas></div>';
    document.body.appendChild(zoomEl);
    var zcv = zoomEl.querySelector('canvas'), zcap = zoomEl.querySelector('span');

    var speed = 1, paused = false, t = 0, last = performance.now(), visible = true;
    if (opts.speeds && opts.speeds.length > 1) {
      var lab = document.createElement('span'); lab.textContent = '시간 배속'; bar.appendChild(lab);
      opts.speeds.forEach(function (s) { var b = document.createElement('button'); b.textContent = '×' + s; b.dataset.s = s;
        b.onclick = function () { speed = s; sync(); }; bar.appendChild(b); });
      var pb = document.createElement('button'); pb.textContent = '❚❚'; pb.onclick = function () { paused = !paused; sync(); }; bar.appendChild(pb);
      var sync = function () { bar.querySelectorAll('button[data-s]').forEach(function (b) { b.classList.toggle('on', +b.dataset.s === speed && !paused); });
        pb.classList.toggle('on', paused); };
      sync();
    }
    if (opts.hint) { var h = document.createElement('span'); h.style.marginLeft = 'auto'; h.textContent = opts.hint; bar.appendChild(h); }

    /* ---- input: every pass keeps the regions it drew last frame ---- */
    var passes = { main: { cv: cv, regions: [], ptr: null, dpr: 1 }, zoom: { cv: zcv, regions: [], ptr: null, dpr: 1 } };
    var ev = {}, active = null, keys = [], zoom = null, bgEv = { main: {}, zoom: {} };
    function evOf(id) { return ev[id] || (ev[id] = {}); }
    function devPos(P, e) { var r = P.cv.getBoundingClientRect(); return [(e.clientX - r.left) * P.cv.width / r.width, (e.clientY - r.top) * P.cv.height / r.height]; }
    function find(P, d) {
      for (var i = P.regions.length - 1; i >= 0; i--) { var R = P.regions[i], q = R.inv.transformPoint(new DOMPoint(d[0], d[1]));
        if (inside(R.shape, q.x, q.y)) return { R: R, x: q.x, y: q.y }; }
      return null;
    }
    function inside(s, x, y) {
      if (typeof s === 'function') return s(x, y);
      if (s.r !== undefined) return (x - s.cx) * (x - s.cx) + (y - s.cy) * (y - s.cy) <= s.r * s.r;
      return x >= s.x && x <= s.x + s.w && y >= s.y && y <= s.y + s.h;
    }
    function hook(name, P) {
      var c = P.cv;
      c.addEventListener('pointerdown', function (e) {
        var d = devPos(P, e), f = find(P, d); c.setPointerCapture(e.pointerId);
        if (f) { active = { id: f.R.id, pass: name, R: f.R, d: d, moved: 0 }; var E = evOf(f.R.id); E.press = true; E.down = true; E.x = f.x; E.y = f.y; }
        else active = { id: null, pass: name, d: d, moved: 0 };
        e.preventDefault();
      });
      c.addEventListener('pointermove', function (e) {
        var d = devPos(P, e); P.ptr = d;
        if (!active || active.pass !== name) return;
        var ddx = d[0] - active.d[0], ddy = d[1] - active.d[1]; active.d = d; active.moved += Math.abs(ddx) + Math.abs(ddy);
        if (active.id) { var E = evOf(active.id), inv = active.R.inv, a = inv.transformPoint(new DOMPoint(0, 0)), b = inv.transformPoint(new DOMPoint(ddx, ddy)),
            q = inv.transformPoint(new DOMPoint(d[0], d[1]));
          E.dx = (E.dx || 0) + (b.x - a.x); E.dy = (E.dy || 0) + (b.y - a.y); E.x = q.x; E.y = q.y; E.rawdy = (E.rawdy || 0) + ddy / P.dpr; }
        else { var B = bgEv[name]; B.dx = (B.dx || 0) + ddx / P.dpr; B.dy = (B.dy || 0) + ddy / P.dpr; }
      });
      c.addEventListener('pointerup', function (e) {
        if (!active || active.pass !== name) return;
        if (active.id) { var E = evOf(active.id); E.release = true; E.down = false; if (active.moved < 6 * P.dpr) E.click = true; }
        else if (active.moved < 6 * P.dpr) bgEv[name].click = true;
        active = null;
      });
      c.addEventListener('pointerleave', function () { P.ptr = null; });
      c.addEventListener('dblclick', function (e) {
        var f = find(P, devPos(P, e));
        if (f) { evOf(f.R.id).dbl = true; if (name === 'main' && f.R.o && f.R.o.zoom) openZoom(f.R.o.zoom); }
        else bgEv[name].dbl = true;
        e.preventDefault();
      });
      c.addEventListener('wheel', function (e) {
        var d = devPos(P, e), f = find(P, d), s = e.deltaY > 0 ? -1 : 1;
        if (f && f.R.o && f.R.o.wheel) { var E = evOf(f.R.id); E.wheel = (E.wheel || 0) + s; E.shift = e.shiftKey; e.preventDefault(); return; }
        if (name === 'zoom') { zoomBy(d, s > 0 ? 1.2 : 1 / 1.2); e.preventDefault(); return; }
        if (opts.wheelFree) { var B = bgEv.main; B.wheel = (B.wheel || 0) + s; B.wx = d[0] / P.dpr * W / (P.cv.width / P.dpr); B.wy = d[1] / P.dpr * W / (P.cv.width / P.dpr); e.preventDefault(); }
      }, { passive: false });
    }
    hook('main', passes.main); hook('zoom', passes.zoom);
    addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && zoom) { closeZoom(); return; }
      if (wrap.offsetParent === null) return;
      if (/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return;
      keys.push(e.key); if (opts.keys && opts.keys.indexOf(e.key) >= 0) e.preventDefault();
    });
    zoomEl.addEventListener('pointerdown', function (e) { if (e.target === zoomEl) closeZoom(); });
    zoomEl.querySelector('button').onclick = closeZoom;

    /* ---- the close-up: the same scene through a lens ---- */
    function openZoom(z) {
      var vw = innerWidth * 0.92, vh = innerHeight * 0.86 - 40, a = z.w / z.h;
      var cw = Math.min(vw, vh * a, z.maxW || 1400), ch = cw / a;
      zcv.style.width = Math.round(cw) + 'px'; zcv.style.height = Math.round(ch) + 'px';
      var dpr = Math.min(devicePixelRatio || 1, 2); zcv.width = Math.round(cw * dpr); zcv.height = Math.round(ch * dpr);
      passes.zoom.dpr = dpr;
      zoom = { x: z.x, y: z.y, w: z.w, h: z.h, s: cw * dpr / z.w, x0: z.x, y0: z.y, s0: cw * dpr / z.w };
      zcap.textContent = (z.title || '확대') + ' — 휠: 더 확대 · 빈 곳 끌기: 옮기기';
      zoomEl.hidden = false;
    }
    function closeZoom() { zoom = null; zoomEl.hidden = true; passes.zoom.regions = []; }
    function zoomBy(d, f) {
      if (!zoom) return; var wx = zoom.x + d[0] / zoom.s, wy = zoom.y + d[1] / zoom.s;
      zoom.s = Math.max(zoom.s0, Math.min(zoom.s0 * 12, zoom.s * f)); zoom.x = wx - d[0] / zoom.s; zoom.y = wy - d[1] / zoom.s; clampZoom();
    }
    function clampZoom() { var vw = zcv.width / zoom.s, vh = zcv.height / zoom.s;
      zoom.x = Math.max(Math.min(zoom.x0, 0), Math.min(Math.max(zoom.x0 + zoom.w, W) - vw, zoom.x));
      zoom.y = Math.max(Math.min(zoom.y0, 0), Math.min(Math.max(zoom.y0 + zoom.h, H) - vh, zoom.y)); }

    function layout() {
      var dpr = Math.min(devicePixelRatio || 1, 2), w = wrap.clientWidth || 800;
      var hmax = innerHeight * (document.fullscreenElement ? 0.9 : 0.78);
      var cw = Math.min(w, hmax / (H / W)), ch = cw * H / W;
      cv.style.width = cw + 'px'; cv.style.height = ch + 'px'; cv.width = Math.round(cw * dpr); cv.height = Math.round(ch * dpr);
      passes.main.dpr = dpr; passes.main.scale = cv.width / W;
    }
    addEventListener('resize', layout); layout();
    if (window.ResizeObserver) new ResizeObserver(function () { layout(); }).observe(wrap);

    function makeUI(name, g, P) {
      var ui = {
        g: g, W: W, H: H, t: t, dt: 0, pass: name, keys: keys, speed: speed, paused: paused,
        lens: name === 'zoom' ? zoom.s / P.dpr / (passes.main.scale / passes.main.dpr) : 1,
        hit: function (id, shape, o) {
          P.regions.push({ id: id, shape: shape, o: o, inv: g.getTransform().invertSelf() });
          var E = ev[id] || {}, ptr = P.ptr, hover = false;
          if (ptr) { var q = g.getTransform().invertSelf().transformPoint(new DOMPoint(ptr[0], ptr[1])); hover = inside(shape, q.x, q.y); }
          var out = { hover: hover, down: !!(active && active.id === id), press: !!E.press, click: !!E.click, release: !!E.release,
            dx: E.dx || 0, dy: E.dy || 0, rawdy: E.rawdy || 0, x: E.x, y: E.y, wheel: E.wheel || 0, shift: !!E.shift, dbl: !!E.dbl };
          if (hover || out.down) P.cursor = (o && o.cursor) || 'pointer';
          ev[id] = { down: out.down, x: E.x, y: E.y };
          return out;
        },
        bg: function () { var B = bgEv[name]; bgEv[name] = {}; return B; },
        zoomTo: function (z) { openZoom(z); },
        inZoom: function () { return !!zoom; }
      };
      return ui;
    }

    function frame(now) {
      var real = Math.min(0.1, (now - last) / 1000); last = now;
      var dt = paused ? 0 : real * speed; t += dt;
      ['main', 'zoom'].forEach(function (name) {
        if (name === 'zoom' && !zoom) return;
        var P = passes[name], g = P.cv.getContext('2d');
        P.regions = []; P.cursor = null;
        g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, P.cv.width, P.cv.height);
        if (name === 'main') g.setTransform(P.scale, 0, 0, P.scale, 0, 0);
        else g.setTransform(zoom.s, 0, 0, zoom.s, -zoom.x * zoom.s, -zoom.y * zoom.s);
        var ui = makeUI(name, g, P); ui.t = t; ui.dt = name === 'main' ? dt : 0; ui.real = name === 'main' ? real : 0;
        if (name === 'zoom') { var B = bgEv.zoom; if (B.dx || B.dy) { zoom.x -= (B.dx || 0) * P.dpr / zoom.s; zoom.y -= (B.dy || 0) * P.dpr / zoom.s; clampZoom(); } bgEv.zoom = {}; }
        g.save(); opts.frame(ui); g.restore();
        P.cv.style.cursor = P.cursor || (name === 'zoom' ? 'grab' : 'default');
      });
      /* events consumed by both passes */
      for (var k in ev) { var E = ev[k]; ev[k] = { down: E.down, x: E.x, y: E.y }; }
      keys.length = 0;
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
    return {
      el: wrap, canvas: cv, layout: layout,
      time: function () { return t; }, setSpeed: function (s) { speed = s; if (sync) sync(); },
      openZoom: openZoom, closeZoom: closeZoom
    };
  };

  /* ---------- the parts every bench uses ---------- */
  var FONT = 'ui-sans-serif,system-ui,"Segoe UI","Malgun Gothic",sans-serif', MONO = 'ui-monospace,Consolas,"Courier New",monospace';
  HL.FONT = FONT; HL.MONO = MONO;
  HL.text = function (g, s, x, y, col, size, align, weight, font) {
    g.fillStyle = col; g.font = (weight || '') + ' ' + size + 'px ' + (font || FONT);
    g.textAlign = align || 'left'; g.textBaseline = 'middle'; g.fillText(s, x, y);
  };
  HL.rr = function (g, x, y, w, h, r, fill, stroke, lw) {
    g.beginPath(); g.roundRect(x, y, w, h, r); if (fill) { g.fillStyle = fill; g.fill(); }
    if (stroke) { g.strokeStyle = stroke; g.lineWidth = lw || 1; g.stroke(); }
  };
  HL.circle = function (g, x, y, r, fill, stroke, lw) {
    g.beginPath(); g.arc(x, y, r, 0, 7); if (fill) { g.fillStyle = fill; g.fill(); } if (stroke) { g.strokeStyle = stroke; g.lineWidth = lw || 1; g.stroke(); }
  };
  /* a seven-segment style read-out */
  HL.lcd = function (g, x, y, w, h, txt, o) {
    o = o || {};
    HL.rr(g, x, y, w, h, Math.min(6, h * 0.15), o.bg || '#0f1a13', o.frame || '#2b3a30', 1.2);
    g.save(); g.shadowColor = o.glow || 'rgba(120,255,160,.35)'; g.shadowBlur = h * 0.25;
    HL.text(g, txt, x + w - h * 0.25, y + h / 2 + 1, o.col || '#8dffad', Math.round(h * (o.size || 0.66)), 'right', '700', MONO);
    g.restore();
  };
  /* a rotary knob: drag up or down, or roll the wheel over it; detent knobs click from step to step */
  var KS = {};
  HL.knob = function (ui, id, x, y, r, val, o) {
    var g = ui.g, lo = o.min, hi = o.max, sweep = (o.sweep || 270) * Math.PI / 180, span = hi - lo;
    var e = ui.hit(id, { cx: x, cy: y, r: r * 1.15 }, { wheel: true, cursor: 'ns-resize', zoom: o.zoom });
    var sens = (o.sens || span / 220) * (o.fine ? 0.25 : 1), st = KS[id] || (KS[id] = {});
    function clampV(v) { return o.wrap ? lo + ((v - lo) % span + span) % span : Math.max(lo, Math.min(hi, v)); }
    function snap(v) { return o.detents.reduce(function (b, d) { return Math.abs(d - v) < Math.abs(b - v) ? d : b; }, o.detents[0]); }
    if (e.down) { if (st.v === undefined) st.v = val; st.v = clampV(st.v - e.rawdy * sens); val = o.detents ? snap(st.v) : st.v; }
    else st.v = undefined;
    if (e.wheel) {
      if (o.detents) { var i = o.detents.indexOf(snap(val)); val = o.detents[Math.max(0, Math.min(o.detents.length - 1, i + e.wheel))]; }
      else val = clampV(val + e.wheel * (o.wheelStep || span / 100) * (e.shift ? 0.1 : 1));
    }
    var shown = e.down && o.detents ? val + (st.v - val) * 0.3 : val;
    var frac = (shown - lo) / span, ang = o.wrap || o.turns ? -Math.PI / 2 + frac * 2 * Math.PI * (o.turns || 1) : -Math.PI / 2 - sweep / 2 + frac * sweep;
    /* scale marks round the knob */
    if (o.marks) o.marks.forEach(function (m) { var f = (m[0] - lo) / span, a = -Math.PI / 2 - sweep / 2 + f * sweep;
      g.strokeStyle = o.markCol || '#c8ced6'; g.lineWidth = 1.2; g.beginPath(); g.moveTo(x + Math.cos(a) * r * 1.18, y + Math.sin(a) * r * 1.18);
      g.lineTo(x + Math.cos(a) * r * 1.32, y + Math.sin(a) * r * 1.32); g.stroke();
      if (m[1] !== undefined) HL.text(g, m[1], x + Math.cos(a) * r * 1.62, y + Math.sin(a) * r * 1.55, o.markCol || '#c8ced6', Math.max(7, r * 0.42), 'center'); });
    HL.circle(g, x + r * 0.06, y + r * 0.1, r * 1.04, 'rgba(0,0,0,.35)');
    HL.circle(g, x, y, r, o.col || '#2a2d31', '#111', 1);
    for (var k = 0; k < 24; k++) { var a2 = k / 24 * 2 * Math.PI; g.strokeStyle = 'rgba(255,255,255,.07)'; g.lineWidth = 1;
      g.beginPath(); g.moveTo(x + Math.cos(a2) * r * 0.86, y + Math.sin(a2) * r * 0.86); g.lineTo(x + Math.cos(a2) * r, y + Math.sin(a2) * r); g.stroke(); }
    var gr = g.createRadialGradient(x - r * 0.3, y - r * 0.35, r * 0.1, x, y, r); gr.addColorStop(0, 'rgba(255,255,255,.18)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
    HL.circle(g, x, y, r * 0.78, gr);
    g.strokeStyle = o.pointer || '#f2f2f2'; g.lineWidth = Math.max(1.5, r * 0.12); g.lineCap = 'round';
    g.beginPath(); g.moveTo(x + Math.cos(ang) * r * 0.25, y + Math.sin(ang) * r * 0.25); g.lineTo(x + Math.cos(ang) * r * 0.86, y + Math.sin(ang) * r * 0.86); g.stroke();
    g.lineCap = 'butt';
    if (e.hover || e.down) HL.circle(g, x, y, r * 1.12, null, 'rgba(78,201,176,.55)', 1.2);
    if (o.label) HL.text(g, o.label, x, y + r * (o.marks ? 2.1 : 1.6), o.labelCol || '#c8ced6', Math.max(8, r * 0.45), 'center', '600');
    return val;
  };
  /* a push button that sinks while held */
  HL.button = function (ui, id, x, y, w, h, o) {
    o = o || {};
    var g = ui.g, e = ui.hit(id, o.round ? { cx: x + w / 2, cy: y + h / 2, r: w / 2 } : { x: x, y: y, w: w, h: h }, { zoom: o.zoom });
    var dn = e.down || o.held, dy = dn ? h * 0.06 : 0;
    if (o.round) { HL.circle(g, x + w / 2, y + h / 2 + h * 0.08, w / 2, '#0b0c0e'); HL.circle(g, x + w / 2, y + h / 2 + dy, w / 2 * (dn ? 0.96 : 1), dn ? (o.downCol || shade(o.col || '#3b3f45')) : (o.col || '#3b3f45'), '#0a0a0a', 1); }
    else { HL.rr(g, x, y + h * 0.08, w, h, Math.min(6, h * 0.25), '#0b0c0e'); HL.rr(g, x, y + dy, w, h, Math.min(6, h * 0.25), dn ? (o.downCol || shade(o.col || '#3b3f45')) : (o.col || '#3b3f45'), '#0a0a0a', 1);
      if (!dn) HL.rr(g, x + 2, y + 2, w - 4, h * 0.3, Math.min(4, h * 0.2), 'rgba(255,255,255,.10)'); }
    if (o.label) HL.text(g, o.label, x + w / 2, y + h / 2 + dy, o.labelCol || '#eee', o.size || Math.max(8, h * 0.42), 'center', '700');
    if (e.hover && !dn) (o.round ? HL.circle(g, x + w / 2, y + h / 2, w / 2 + 2, null, 'rgba(78,201,176,.5)', 1.2) : HL.rr(g, x - 2, y - 2, w + 4, h + 4, 6, null, 'rgba(78,201,176,.5)', 1.2));
    return e;
  };
  function shade(c) { return c.replace(/^#(..)(..)(..)$/, function (m, r, g2, b) { return '#' + [r, g2, b].map(function (v) { return Math.round(parseInt(v, 16) * 0.72).toString(16).padStart(2, '0'); }).join(''); }); }
  /* a toggle (rocker) switch: click flips it */
  HL.toggle = function (ui, id, x, y, w, h, on, o) {
    o = o || {};
    var g = ui.g, e = ui.hit(id, { x: x, y: y, w: w, h: h }, { zoom: o.zoom });
    if (e.click) on = !on;
    HL.rr(g, x, y, w, h, 3, '#121316', '#000', 1);
    HL.rr(g, x + 2, on ? y + 2 : y + h / 2, w - 4, h / 2 - 2, 2, on ? (o.onCol || '#c0392b') : '#3a3d42');
    HL.rr(g, x + 2, on ? y + h / 2 : y + 2, w - 4, h / 2 - 2, 2, '#1e2024');
    if (o.label) HL.text(g, o.label, x + w / 2, y + h + 10, o.labelCol || '#c8ced6', 9, 'center', '600');
    if (e.hover) HL.rr(g, x - 2, y - 2, w + 4, h + 4, 4, null, 'rgba(78,201,176,.5)', 1.2);
    return on;
  };
  /* an analog panel meter */
  HL.meter = function (g, x, y, w, h, frac, o) {
    o = o || {};
    HL.rr(g, x, y, w, h, 6, '#1e2126', '#0c0d0f', 1.2);
    HL.rr(g, x + 6, y + 6, w - 12, h * 0.72, 4, '#f2efe4');
    var cx = x + w / 2, cy = y + h * 0.78, R = Math.min(w * 0.42, h * 0.6), a0 = -Math.PI * 0.78, a1 = -Math.PI * 0.22;
    var n = o.major || 5, m = o.minor || 5;
    for (var i = 0; i <= n * m; i++) { var a = a0 + (a1 - a0) * i / (n * m), L = i % m ? 0.07 : 0.13;
      g.strokeStyle = '#222'; g.lineWidth = i % m ? 0.8 : 1.4; g.beginPath(); g.moveTo(cx + Math.cos(a) * R, cy + Math.sin(a) * R);
      g.lineTo(cx + Math.cos(a) * R * (1 - L), cy + Math.sin(a) * R * (1 - L)); g.stroke();
      if (!(i % m) && o.labels) HL.text(g, o.labels[i / m], cx + Math.cos(a) * R * 0.76, cy + Math.sin(a) * R * 0.76, '#222', Math.max(7, R * 0.13), 'center', '600'); }
    /* a mirror strip under the needle, for reading without parallax */
    g.strokeStyle = 'rgba(150,170,190,.6)'; g.lineWidth = R * 0.04; g.beginPath(); g.arc(cx, cy, R * 1.04, a0, a1); g.stroke();
    if (o.unit) HL.text(g, o.unit, cx, cy - R * 0.38, '#333', Math.max(8, R * 0.16), 'center', '700');
    var f = Math.max(-0.02, Math.min(1.02, frac)), an = a0 + (a1 - a0) * f;
    g.strokeStyle = '#111'; g.lineWidth = 1.4; g.beginPath(); g.moveTo(cx, cy); g.lineTo(cx + Math.cos(an) * R * 1.02, cy + Math.sin(an) * R * 1.02); g.stroke();
    HL.circle(g, cx, cy, R * 0.06, '#333');
    if (o.label) HL.text(g, o.label, cx, y + h - 9, '#c8ced6', 10, 'center', '600');
  };
  /* a handheld stopwatch the user runs by hand; its buttons take a few ms to make contact */
  HL.Stopwatch = function (latency) {
    this.run = false; this.acc = 0; this.t0 = 0; this.lap = null; this.latency = latency || 0.03; this.pend = [];
  };
  HL.Stopwatch.prototype.read = function (t) { return this.acc + (this.run ? t - this.t0 : 0); };
  HL.Stopwatch.prototype.startStop = function (t) { this.pend.push(['ss', t + this.latency]); };
  HL.Stopwatch.prototype.lapReset = function (t) { this.pend.push(['lr', t + this.latency]); };
  HL.Stopwatch.prototype.update = function (t) {
    var keep = [];
    this.pend.forEach(function (p) {
      if (p[1] > t) { keep.push(p); return; }
      if (p[0] === 'ss') { if (this.run) { this.acc += p[1] - this.t0; this.run = false; } else { this.t0 = p[1]; this.run = true; } }
      else if (this.run) this.lap = this.lap === null ? this.read(p[1]) : null;
      else { this.acc = 0; this.lap = null; }
    }, this);
    this.pend = keep;
  };
  HL.fmtWatch = function (s) { s = Math.max(0, s); var m = Math.floor(s / 60), r = s - m * 60;
    return (m < 10 ? '0' : '') + m + ':' + (r < 10 ? '0' : '') + r.toFixed(2); };
  HL.drawStopwatch = function (ui, id, sw, x, y, sc) {
    var g = ui.g; sc = sc || 1; sw.update(ui.t);
    g.save(); g.translate(x, y); g.scale(sc, sc);
    var zoomR = { x: x - 70 * sc, y: y - 90 * sc, w: 140 * sc, h: 175 * sc, title: '스톱워치' };
    HL.rr(g, -8, -88, 16, 14, 3, '#9aa1a8');
    HL.circle(g, 0, 0, 66, '#1d2024', '#0b0c0e', 2); HL.circle(g, 0, 0, 58, '#2b2f35');
    HL.rr(g, -46, -22, 92, 34, 5, '#c9d2c2', '#333', 1);
    var shown = sw.lap !== null ? sw.lap : sw.read(ui.t);
    HL.text(g, HL.fmtWatch(shown), 41, -3, '#1a1f1a', 17, 'right', '700', MONO);
    if (sw.lap !== null) HL.text(g, 'LAP', -40, -15, '#1a1f1a', 8, 'left', '700');
    if (sw.run) HL.text(g, '▶', -40, 5, '#1a1f1a', 8, 'left', '700');
    HL.text(g, 'START/STOP', 0, 28, '#c8ced6', 7.5, 'center', '600'); HL.text(g, 'LAP/RESET', 0, 42, '#8b939c', 7, 'center', '600');
    g.restore();
    ui.hit(id + ':body', { cx: x, cy: y, r: 66 * sc }, { zoom: zoomR, cursor: 'default' });
    var a = HL.button(ui, id + ':ss', x + 26 * sc, y - 86 * sc, 26 * sc, 14 * sc, { col: '#b8433a', zoom: zoomR });
    var b = HL.button(ui, id + ':lr', x - 52 * sc, y - 86 * sc, 26 * sc, 14 * sc, { col: '#6f777f', zoom: zoomR });
    if (a.press) sw.startStop(ui.t);
    if (b.press) sw.lapReset(ui.t);
    return { ss: a, lr: b };
  };

  /* a lab notebook kept in this browser */
  HL.notebook = function (host, key, placeholder) {
    var ta = document.createElement('textarea'); ta.className = 'hl-note'; ta.placeholder = placeholder || '';
    try { ta.value = localStorage.getItem('hl-note:' + key) || ''; } catch (e) {}
    ta.addEventListener('input', function () { try { localStorage.setItem('hl-note:' + key, ta.value); } catch (e) {} });
    host.appendChild(ta); return ta;
  };
})();
