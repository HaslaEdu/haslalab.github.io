/* HaslaLab 3-D bench instruments (needs sim/handlab.js and sim/bench3d.js).

   Each instrument is drawn after a real model: its case in 3-D, its front as a panel worked by hand.
   Sizes are the makers' (cm); the front panels follow their photographs and manuals.

     B3.korad(b, name, [x, z], st, o)    KORAD KA3005D (30 V / 5 A) — or, with o.model 'KD6005P', the
                                          60 V / 5 A KD6005P: two LED read-outs, I-SET / V-SET, one
                                          encoder (push it to step the digit), OUTPUT; st.load(V) → A
                                          tells what the load draws, the supply finds CV or CC itself
     B3.knife(b, name, [x, z], st)       a double-pole double-throw knife switch on a porcelain base,
                                          wired as a reversing switch: st.pos = +1 / 0 / −1
     B3.post(x, y, z, col)               a binding post standing on a horizontal surface */
(function () {
  "use strict";
  const { box3, cyl3, prism3, text3, tex3, line3, poly3 } = B3;

  B3.post = function (x, y, z, col, id){
    const o = id ? { id, seg: 12 } : { seg: 12 };
    cyl3('y', y, y + 0.35, x, z, 0.62, '#2a2a2a', o);
    cyl3('y', y + 0.35, y + 1.25, x, z, 0.5, col, Object.assign({ cap: B3.shade(col, 0.8) }, o));
    cyl3('y', y + 1.25, y + 1.4, x, z, 0.24, '#c8b26a', o);
  };

  /* ---------- KORAD KA3005D / KD6005P programmable DC supply ---------- */
  const MODELS = {
    KA3005D: { w: 15.7, h: 11.7, d: 26.1, vmax: 30, imax: 5, vdig: [10, 1, 0.1, 0.01], idig: [1, 0.1, 0.01, 0.001] },
    KD6005P: { w: 15.7, h: 11.7, d: 26.1, vmax: 60, imax: 5, vdig: [10, 1, 0.1, 0.01], idig: [1, 0.1, 0.01, 0.001] }
  };
  B3.korad = function (b, name, p, st, o){
    o = o || {};
    const M = MODELS[o.model || 'KA3005D'], [x, z] = p, w = M.w, h = M.h, d = M.d;
    const x0 = x - w / 2, x1 = x + w / 2, z1 = z + d / 2, z0 = z - d / 2;
    const def = { power: true, out: false, vset: o.vset || 5, iset: 0, mode: null, dig: 2, edit: 0, acc: 0 };
    for (const k in def) if (st[k] === undefined) st[k] = def[k];
    /* the case: a grey U-cover over a black chassis, feet, a carrying handle folded under */
    box3(x0, x1, 0.9, h, z0, z1 - 0.6, '#9da3a8', { id: 'm:' + name, top: '#aab0b5' });
    box3(x0 + 0.2, x1 - 0.2, 0.9, h - 0.2, z1 - 0.6, z1, '#1d1f22', { id: 'm:' + name });
    for (const fx of [x0 + 1.2, x1 - 1.2]) for (const fz of [z0 + 2, z1 - 2]) box3(fx - 0.9, fx + 0.9, 0, 0.9, fz - 0.9, fz + 0.9, '#111', { id: 'm:' + name });
    for (let i = 0; i < 7; i++) box3(x0 + 2 + i * 1.7, x0 + 2.6 + i * 1.7, h - 0.02, h + 0.01, z0 + 3, z0 + 10, '#7d8388');   /* vents */
    /* the circuit as the load sees it */
    const R = st.loadR ? st.loadR() : Infinity;
    let Vo = 0, Io = 0, cc = false;
    if (st.power && st.out){ const ic = st.vset / R; if (ic > st.iset){ cc = true; Io = st.iset; Vo = st.iset * R; } else { Io = ic; Vo = st.vset; } }
    st.V = Vo; st.I = Io; st.cc = cc;
    if (st.edit > 0) st.edit -= b.real || 0; if (st.edit <= 0) st.mode = null;
    const W = 470, H = 350;
    const cv = b.panel(name, W, H, ui => {
      const g = ui.g;
      g.fillStyle = '#1d1f22'; g.fillRect(0, 0, W, H);
      g.fillStyle = '#25282c'; g.fillRect(8, 8, W - 16, H - 16);
      HL.text(g, 'KORAD', 22, 30, '#f2f2f2', 22, 'left', '900');
      HL.text(g, (o.model || 'KA3005D') + '  PROGRAMMABLE DC POWER SUPPLY', 120, 31, '#aeb4ba', 10.5, 'left', '600');
      /* the two read-outs */
      const blink = Math.floor((b.t + performance.now() / 1000) * 3) % 2 === 0;
      function digits(val, decs, digit, editing){
        let s = Math.abs(val).toFixed(decs); while (s.length < 5) s = '0' + s;
        if (editing && blink){ const dd = s.replace('.', ''), k = dd.length - 1 - digit; return s; }
        return s;
      }
      const vShow = st.mode === 'V' ? st.vset : Vo * (1 + (st.gV || 0)) + (st.out ? (st.oV || 0) : 0);
      const iShow = st.mode === 'I' ? st.iset : Io * (1 + (st.gI || 0)) + (st.out && Io > 0 ? (st.oI || 0) : 0);
      HL.rr(g, 22, 52, 196, 96, 6, '#0b0b0c', '#000', 1);
      HL.rr(g, 236, 52, 212, 96, 6, '#0b0b0c', '#000', 1);
      g.save(); g.shadowBlur = 14;
      g.shadowColor = 'rgba(255,60,40,.7)'; HL.text(g, st.power ? digits(Math.max(0, vShow), 2) : '', 196, 101, st.mode === 'V' && blink ? '#ff7a62' : '#ff3b25', 56, 'right', '700', HL.MONO);
      g.shadowColor = 'rgba(80,255,120,.7)'; HL.text(g, st.power ? digits(Math.max(0, iShow), 3) : '', 426, 101, st.mode === 'I' && blink ? '#9dffb2' : '#38ff6a', 56, 'right', '700', HL.MONO);
      g.restore();
      if (st.mode){ const dg = st.mode === 'V' ? M.vdig : M.idig, k = st.dig, x0p = st.mode === 'V' ? 196 : 426, step = 33.7;
        const decs = st.mode === 'V' ? 2 : 3, pos = k <= dg.length - 1 - decs ? k : k + 1;   /* skip the point */
        g.fillStyle = '#ffd479'; g.fillRect(x0p - step * (dg.length - k) - (k <= dg.length - 1 - decs ? 12 : 0) + 2, 134, 26, 3); }
      HL.text(g, 'V', 208, 140, '#9aa0a6', 12, 'right', '700'); HL.text(g, 'A', 438, 140, '#9aa0a6', 12, 'right', '700');
      /* status lamps */
      const lamp = (xx, lab, on, col) => { HL.circle(g, xx, 166, 5, on ? col : '#3a2e2a', '#000', 1); HL.text(g, lab, xx + 10, 166, '#c8ced6', 10.5, 'left', '700'); };
      lamp(30, 'C.V', st.power && st.out && !cc, '#3cff6e'); lamp(90, 'C.C', st.power && st.out && cc, '#ff3b25'); lamp(150, 'OUT', st.power && st.out, '#ffb02e');
      /* keys */
      const key = (id, xx, yy, lab, col) => HL.button(ui, id, xx, yy, 56, 30, { col: col || '#3a3e44', label: lab, size: 11 });
      const iS = key('iset', 22, 190, 'I-SET'), vS = key('vset', 84, 190, 'V-SET');
      ['M1', 'M2', 'M3', 'M4', 'M5'].forEach((m, i) => key('m' + i, 22 + i * 62, 232, m));
      key('ocp', 146, 190, 'OCP'); key('ovp', 208, 190, 'OVP');
      const out = HL.button(ui, 'out', 22, 276, 118, 40, { col: st.out ? '#7a2b22' : '#3a3e44', label: 'OUTPUT', size: 13 });
      if (iS.press){ st.mode = 'I'; st.dig = 2; st.edit = 4; } if (vS.press){ st.mode = 'V'; st.dig = 1; st.edit = 4; }
      if (out.press && st.power) st.out = !st.out;
      /* the encoder: turn it (drag or wheel), push it to step the digit */
      const ex = 372, ey = 222, er = 44;
      const e = ui.hit('enc', { cx: ex, cy: ey, r: er }, { wheel: true, cursor: 'ns-resize' });
      let steps = e.wheel || 0;
      if (e.down){ st.acc += -e.rawdy; while (st.acc > 14){ steps++; st.acc -= 14; } while (st.acc < -14){ steps--; st.acc += 14; } } else st.acc = 0;
      if (e.click && !e.rawdy){ if (st.mode){ const n = (st.mode === 'V' ? M.vdig : M.idig).length; st.dig = (st.dig + n - 1) % n; st.edit = 4; } }
      if (steps){
        if (!st.mode){ st.mode = 'V'; st.dig = 1; }
        if (st.mode === 'V') st.vset = Math.max(0, Math.min(M.vmax, Math.round((st.vset + steps * M.vdig[st.dig]) * 100) / 100));
        else st.iset = Math.max(0, Math.min(M.imax, Math.round((st.iset + steps * M.idig[st.dig]) * 1000) / 1000));
        st.edit = 4;
      }
      st.encA = (st.encA || 0) + steps * 0.26;
      HL.circle(g, ex + 3, ey + 4, er + 3, 'rgba(0,0,0,.45)');
      HL.circle(g, ex, ey, er, '#5a5f66', '#151515', 1.5);
      for (let i = 0; i < 30; i++){ const a = i / 30 * 2 * Math.PI + st.encA; g.strokeStyle = 'rgba(0,0,0,.35)'; g.lineWidth = 2;
        g.beginPath(); g.moveTo(ex + Math.cos(a) * er * 0.86, ey + Math.sin(a) * er * 0.86); g.lineTo(ex + Math.cos(a) * er, ey + Math.sin(a) * er); g.stroke(); }
      const gr = g.createRadialGradient(ex - 12, ey - 14, 4, ex, ey, er); gr.addColorStop(0, 'rgba(255,255,255,.35)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); HL.circle(g, ex, ey, er * 0.8, gr);
      HL.circle(g, ex + Math.cos(st.encA - 1.2) * er * 0.6, ey + Math.sin(st.encA - 1.2) * er * 0.6, 4, '#2a2d31');
      if (e.down) HL.circle(g, ex, ey, er + 4, null, 'rgba(78,201,176,.6)', 1.5);
      /* the output terminals and the power switch, printed where they are */
      HL.text(g, '+', 300, 300, '#ff6a5a', 16, 'center', '900'); HL.text(g, 'GND', 352, 300, '#7fe08a', 10, 'center', '800'); HL.text(g, '−', 404, 300, '#c8ced6', 16, 'center', '900');
      HL.text(g, 'POWER', 170, 296, '#c8ced6', 9.5, 'left', '700');
      const pw = HL.toggle(ui, 'pwr', 214, 282, 26, 32, st.power, { onCol: '#e1b12c' });
      if (pw !== st.power){ st.power = pw; if (!pw) st.out = false; }
    });
    tex3(cv, 0, 0, cv.width, cv.height, [x0 + 0.2, h - 0.25, z1 + 0.01], [w - 0.4, 0, 0], [0, -(h - 1.15), 0], { id: 'p:' + name });
    /* the binding posts stand out of the front */
    const fy = 0.9 + (h - 1.15) * (1 - 300 / 350), jx = t => x0 + 0.2 + (w - 0.4) * t / 470;
    const jacks = { plus: [jx(300), fy, z1 + 1.3], gnd: [jx(352), fy, z1 + 1.3], minus: [jx(404), fy, z1 + 1.3] };
    for (const [k, col] of [['plus', '#c0392b'], ['gnd', '#2e8b3a'], ['minus', '#1b1b1b']]){ const q = jacks[k];
      cyl3('z', z1, z1 + 1.1, q[0], q[1], 0.6, col, { seg: 14, cap: B3.shade(col, 0.7) }); cyl3('z', z1 + 1.1, z1 + 1.3, q[0], q[1], 0.25, '#c8b26a', { seg: 10 }); }
    return jacks;
  };



  /* a rotary encoder (no end stops): returns the clicks turned this frame — drag up / wheel up is + */
  const ENC = {};
  B3.encoder = function (ui, id, x, y, r, o){
    o = o || {};
    const g = ui.g, e = ui.hit(id, { cx: x, cy: y, r: r * 1.15 }, { wheel: true, cursor: 'ns-resize' }), st = ENC[id] || (ENC[id] = { acc: 0, a: 0 });
    let n = e.wheel || 0;
    if (e.down){ st.acc += -e.rawdy; while (st.acc > (o.px || 10)){ n++; st.acc -= o.px || 10; } while (st.acc < -(o.px || 10)){ n--; st.acc += o.px || 10; } } else st.acc = 0;
    st.a += n * 0.22;
    HL.circle(g, x + r * 0.07, y + r * 0.1, r * 1.04, 'rgba(0,0,0,.35)'); HL.circle(g, x, y, r, o.col || '#3a3d42', '#111', 1);
    for (let k = 0; k < 20; k++){ const a = k / 20 * 2 * Math.PI + st.a; g.strokeStyle = 'rgba(255,255,255,.12)'; g.lineWidth = 1;
      g.beginPath(); g.moveTo(x + Math.cos(a) * r * 0.82, y + Math.sin(a) * r * 0.82); g.lineTo(x + Math.cos(a) * r, y + Math.sin(a) * r); g.stroke(); }
    const gr = g.createRadialGradient(x - r * 0.3, y - r * 0.35, r * 0.1, x, y, r); gr.addColorStop(0, 'rgba(255,255,255,.22)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); HL.circle(g, x, y, r * 0.78, gr);
    HL.circle(g, x + Math.cos(st.a - 1.3) * r * 0.55, y + Math.sin(st.a - 1.3) * r * 0.55, Math.max(1.5, r * 0.1), '#d8d8d8');
    if (e.down || e.hover) HL.circle(g, x, y, r * 1.12, null, 'rgba(78,201,176,.55)', 1.2);
    if (o.label) HL.text(g, o.label, x, y + r + 9, o.labelCol || '#333', 8.5, 'center', '700');
    return e.shift ? n * 0.1 : n;
  };

  /* ---------- SIGLENT SDS1202X-E digital oscilloscope (312 × 157 × 116 mm) ----------
     Two channels fed by st.push(t, v1, v2) at the page's own rate; V/div, position, time/div, horizontal
     position, edge trigger (source, slope, level, Auto/Normal), RUN/STOP, SINGLE, roll mode from
     100 ms/div, cursors (X or Y, moved with the Adjust knob) and four measurements of a channel. */
  const VDIV = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10];
  const TDIV = [1e-3, 2e-3, 5e-3, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10];
  const vlab = v => v >= 1 ? v + 'V' : (v * 1000) + 'mV';
  const tlab = t => t >= 1 ? t + 's' : (Math.round(t * 1e4) / 10) + 'ms';
  const vfmt = v => Math.abs(v) >= 1 ? v.toFixed(3) + 'V' : (v * 1000).toFixed(1) + 'mV';
  const tfmt = t => Math.abs(t) >= 1 ? t.toFixed(4) + 's' : (t * 1000).toFixed(2) + 'ms';
  B3.Scope = function (){
    this.on = true; this.ch = [{ on: true, vi: 9, pos: 0 }, { on: false, vi: 9, pos: -2 }];
    this.ti = 7; this.hpos = 0; this.trig = { src: 0, slope: 1, level: 0, mode: 'Auto' };
    this.run = true; this.single = false; this.frame = null; this.cur = { mode: 'Off', sel: 0, x: [-2, 2], y: [1, -1] }; this.meas = false;
    this.N = 240000; this.bt = new Float64Array(this.N); this.b1 = new Float32Array(this.N); this.b2 = new Float32Array(this.N); this.n = 0; this.head = 0; this.now = 0;
  };
  B3.Scope.prototype.push = function (t, v1, v2){ const i = this.head; this.bt[i] = t; this.b1[i] = v1; this.b2[i] = v2; this.head = (i + 1) % this.N; if (this.n < this.N) this.n++; this.now = t; };
  B3.Scope.prototype.idx = function (k){ return (this.head - this.n + k + this.N) % this.N; };     /* k-th oldest */
  B3.Scope.prototype.find = function (t){ let lo = 0, hi = this.n - 1; if (this.n === 0) return 0;
    while (lo < hi){ const m = (lo + hi) >> 1; if (this.bt[this.idx(m)] < t) lo = m + 1; else hi = m; } return lo; };
  B3.Scope.prototype.window = function (t0, t1, px){            /* min/max per pixel column for both channels */
    const out = [[], []], k0 = this.find(t0), k1 = this.find(t1);
    if (this.n === 0 || k1 <= k0) return null;
    for (let c = 0; c < px; c++){
      const ta = t0 + (t1 - t0) * c / px, tb = t0 + (t1 - t0) * (c + 1) / px; let a = this.find(ta), bb = this.find(tb);
      if (bb <= a) bb = a + 1; let mn1 = Infinity, mx1 = -Infinity, mn2 = Infinity, mx2 = -Infinity, any = false;
      for (let k = a; k < bb && k < this.n; k++){ const i = this.idx(k), tt = this.bt[i]; if (tt < t0 || tt > t1) continue; any = true;
        const v1 = this.b1[i], v2 = this.b2[i]; if (v1 < mn1) mn1 = v1; if (v1 > mx1) mx1 = v1; if (v2 < mn2) mn2 = v2; if (v2 > mx2) mx2 = v2; }
      out[0].push(any ? [mn1, mx1] : null); out[1].push(any ? [mn2, mx2] : null);
    }
    return { t0, t1, d: out };
  };
  /* the newest edge on the trigger source at the level, with a full record after it */
  B3.Scope.prototype.lastTrig = function (after, span){
    const src = this.trig.src ? this.b2 : this.b1, L = this.trig.level, s = this.trig.slope;
    const kmax = this.find(this.now - span) - 1, kmin = Math.max(1, this.find(after));
    for (let k = Math.min(this.n - 1, kmax); k >= kmin; k--){ const a = src[this.idx(k - 1)], b = src[this.idx(k)];
      if (s > 0 ? (a < L && b >= L) : (a > L && b <= L)) return this.bt[this.idx(k)]; }
    return null;
  };
  B3.scope = function (b, name, p, st, o){
    o = o || {};
    const [x, z] = p, w = 31.2, h = 15.7, d = 11.6, x0 = x - w / 2, z1 = z + d / 2;
    box3(x0, x0 + w, 0.8, h, z - d / 2 + 2.5, z1 - 0.8, '#d9dcdf', { id: 'm:' + name, top: '#e3e6e8' });
    box3(x0 + 3, x0 + w - 3, 0.8, h - 1.5, z - d / 2, z - d / 2 + 2.5, '#c7cacd', { id: 'm:' + name });
    box3(x0 - 0.2, x0 + w + 0.2, 0.6, h + 0.2, z1 - 0.8, z1, '#3c4045', { id: 'm:' + name });
    for (const fx of [x0 + 2, x0 + w - 2]) box3(fx - 1, fx + 1, 0, 0.8, z - 2, z + 4, '#222', { id: 'm:' + name });
    const tdiv = TDIV[st.ti], span = 10 * tdiv;
    /* acquisition */
    if (st.on && st.run){
      if (tdiv >= 0.1) st.frame = st.window(st.now - span, st.now, 440), st.rolling = true;
      else { st.rolling = false;
        const tc = st.lastTrig(st.armT || -Infinity, span / 2 - st.hpos);
        if (tc !== null && tc !== st.lastTc){ st.lastTc = tc; st.frame = st.window(tc + st.hpos - span / 2, tc + st.hpos + span / 2, 440); st.frame.trig = true;
          if (st.single){ st.run = false; st.single = false; } }
        else if (st.trig.mode === 'Auto' && !st.single && (tc === null || st.now - tc > span + 0.25)) st.frame = st.window(st.now - span, st.now, 440); }
    }
    const W = 780, H = 392;
    const cv = b.panel(name, W, H, ui => {
      const g = ui.g;
      g.fillStyle = '#c9ccd0'; g.fillRect(0, 0, W, H); HL.rr(g, 6, 6, W - 12, H - 12, 10, '#d8dbde');
      HL.text(g, 'SIGLENT', 24, 22, '#1d3f8a', 19, 'left', '900'); HL.text(g, 'SDS1202X-E', 470, 18, '#333', 12, 'right', '800'); HL.text(g, '200 MHz   1 GSa/s', 470, 32, '#555', 9.5, 'right', '700');
      HL.rr(g, 18, 40, 466, 300, 6, '#16181b'); HL.rr(g, 24, 46, 454, 288, 3, '#04070a');
      const gx = 32, gy = 64, gw = 440, gh = 240, NXd = 10, NYd = 8;
      if (st.on){
        HL.text(g, st.run ? (st.rolling ? 'Roll' : (st.trig.mode === 'Auto' ? 'Auto' : 'Trig\'d')) : 'Stop', 34, 55, st.run ? '#5cff6e' : '#ff4a3c', 10, 'left', '800');
        HL.text(g, 'H ' + tlab(tdiv) + '/div', 140, 55, '#e8e8e8', 10, 'left', '700'); HL.text(g, 'Delay ' + tfmt(st.hpos), 250, 55, '#e8e8e8', 10, 'left', '600');
        HL.text(g, (st.trig.src ? 'C2' : 'C1') + ' ' + (st.trig.slope > 0 ? '↑' : '↓') + ' ' + vfmt(st.trig.level), 470, 55, '#ffcf3a', 10, 'right', '700');
        /* the graticule */
        g.strokeStyle = 'rgba(160,160,160,.35)'; g.lineWidth = 0.6;
        for (let i = 0; i <= NXd; i++){ g.beginPath(); g.moveTo(gx + i * gw / NXd, gy); g.lineTo(gx + i * gw / NXd, gy + gh); g.stroke(); }
        for (let j = 0; j <= NYd; j++){ g.beginPath(); g.moveTo(gx, gy + j * gh / NYd); g.lineTo(gx + gw, gy + j * gh / NYd); g.stroke(); }
        g.strokeStyle = 'rgba(200,200,200,.5)'; for (let i = 0; i <= NXd * 5; i++){ const xx = gx + i * gw / (NXd * 5); g.beginPath(); g.moveTo(xx, gy + gh / 2 - 2); g.lineTo(xx, gy + gh / 2 + 2); g.stroke(); }
        for (let j = 0; j <= NYd * 5; j++){ const yy = gy + j * gh / (NYd * 5); g.beginPath(); g.moveTo(gx + gw / 2 - 2, yy); g.lineTo(gx + gw / 2 + 2, yy); g.stroke(); }
        const COL = ['#f7e34b', '#e45bd5'];
        const yOf = (c, v) => gy + gh / 2 - (v / VDIV[st.ch[c].vi] + st.ch[c].pos) * gh / NYd;
        g.save(); g.beginPath(); g.rect(gx, gy, gw, gh); g.clip();
        if (st.frame) for (const c of [0, 1]) if (st.ch[c].on){ g.strokeStyle = COL[c]; g.lineWidth = 1.2; g.beginPath(); let pen = false;
          st.frame.d[c].forEach((q, k) => { if (!q){ pen = false; return; } const xx = gx + k * gw / st.frame.d[c].length, y1 = yOf(c, q[0]), y2 = yOf(c, q[1]);
            if (!pen){ g.moveTo(xx, y1); pen = true; } else g.lineTo(xx, y1); if (Math.abs(y2 - y1) > 0.5) g.lineTo(xx, y2); }); g.stroke(); }
        /* cursors */
        if (st.cur.mode !== 'Off'){ g.setLineDash([4, 3]); g.lineWidth = 1;
          for (const j of [0, 1]){ g.strokeStyle = st.cur.sel === j || st.cur.sel === 2 ? '#ff9b3a' : '#9b5a20'; g.beginPath();
            if (st.cur.mode === 'X'){ const xx = gx + gw / 2 + st.cur.x[j] * gw / NXd; g.moveTo(xx, gy); g.lineTo(xx, gy + gh); }
            else { const yy = gy + gh / 2 - st.cur.y[j] * gh / NYd; g.moveTo(gx, yy); g.lineTo(gx + gw, yy); } g.stroke(); }
          g.setLineDash([]); }
        g.restore();
        /* channel ground markers and the trigger level marker */
        for (const c of [0, 1]) if (st.ch[c].on){ const yy = Math.max(gy + 4, Math.min(gy + gh - 4, gy + gh / 2 - st.ch[c].pos * gh / NYd));
          g.fillStyle = COL[c]; g.beginPath(); g.moveTo(gx - 9, yy - 5); g.lineTo(gx - 1, yy - 5); g.lineTo(gx + 3, yy); g.lineTo(gx - 1, yy + 5); g.lineTo(gx - 9, yy + 5); g.fill();
          HL.text(g, String(c + 1), gx - 6, yy, '#000', 8, 'center', '900'); }
        if (!st.rolling){ const yy = Math.max(gy, Math.min(gy + gh, yOf(st.trig.src, st.trig.level))); g.fillStyle = '#ffcf3a'; g.beginPath(); g.moveTo(gx + gw + 1, yy); g.lineTo(gx + gw + 8, yy - 5); g.lineTo(gx + gw + 8, yy + 5); g.fill();
          const tx = gx + gw / 2 - st.hpos / tdiv * gw / NXd; if (tx >= gx && tx <= gx + gw){ g.fillStyle = '#ff8c2a'; g.beginPath(); g.moveTo(tx - 5, gy - 7); g.lineTo(tx + 5, gy - 7); g.lineTo(tx, gy - 1); g.fill(); } }
        /* the foot line: channel scales */
        for (const c of [0, 1]){ const xx = 34 + c * 110; HL.rr(g, xx, 312, 100, 16, 3, st.ch[c].on ? COL[c] : '#333');
          HL.text(g, 'C' + (c + 1) + ' DC1M  ' + vlab(VDIV[st.ch[c].vi]), xx + 50, 320, '#000', 9, 'center', '800'); }
        /* cursor read-outs and measurements */
        let info = [];
        if (st.cur.mode === 'X'){ const tA = st.hpos + st.cur.x[0] * tdiv, tB = st.hpos + st.cur.x[1] * tdiv; info = ['X1 ' + tfmt(tA), 'X2 ' + tfmt(tB), 'ΔX ' + tfmt(tB - tA), '1/ΔX ' + (Math.abs(tB - tA) > 0 ? (1 / Math.abs(tB - tA)).toFixed(3) + 'Hz' : '****')]; }
        if (st.cur.mode === 'Y'){ const c = st.ms || 0, vd = VDIV[st.ch[c].vi], vA = (st.cur.y[0] - st.ch[c].pos) * vd, vB = (st.cur.y[1] - st.ch[c].pos) * vd; info = ['C' + (c + 1) + ' Y1 ' + vfmt(vA), 'Y2 ' + vfmt(vB), 'ΔY ' + vfmt(vB - vA)]; }
        if (info.length){ HL.rr(g, gx + 4, gy + 4, 132, info.length * 14 + 6, 3, 'rgba(10,10,10,.85)', '#ff9b3a', 1); info.forEach((s2, k) => HL.text(g, s2, gx + 10, gy + 13 + k * 14, '#ff9b3a', 10, 'left', '700', HL.MONO)); }
        if (st.meas && st.frame){ const c = st.ms || 0; let mn = Infinity, mx = -Infinity, sm = 0, nn = 0;
          st.frame.d[c].forEach(q => { if (!q) return; mn = Math.min(mn, q[0]); mx = Math.max(mx, q[1]); sm += (q[0] + q[1]) / 2; nn++; });
          const ms = nn ? ['Max ' + vfmt(mx), 'Min ' + vfmt(mn), 'Pk-Pk ' + vfmt(mx - mn), 'Mean ' + vfmt(sm / nn)] : [];
          ms.forEach((s2, k) => { HL.rr(g, gx + k * 110, gy + gh - 18, 106, 16, 2, 'rgba(0,0,0,.8)'); HL.text(g, 'C' + (c + 1) + ' ' + s2, gx + 4 + k * 110, gy + gh - 10, COL[c], 9.5, 'left', '700', HL.MONO); }); }
      }
      /* soft keys under the glass */
      const soft = st.cur.mode !== 'Off' ? [st.cur.mode === 'X' ? 'X1' : 'Y1', st.cur.mode === 'X' ? 'X2' : 'Y2', 'Track', 'Source C' + ((st.ms || 0) + 1), '', ''] :
        st.meas ? ['Source C' + ((st.ms || 0) + 1), '', '', '', '', 'Clear'] : ['', '', '', '', '', ''];
      soft.forEach((lab, k) => { const e = HL.button(ui, 'sk' + k, 30 + k * 76, 348, 64, 24, { col: '#4a4e54', label: lab, size: 9.5 });
        if (e.click && st.cur.mode !== 'Off'){ if (k < 3) st.cur.sel = k; if (k === 3) st.ms = 1 - (st.ms || 0); }
        if (e.click && st.meas){ if (k === 0) st.ms = 1 - (st.ms || 0); if (k === 5) st.meas = false; } });
      const pw = HL.button(ui, 'pwr', 496, 352, 26, 26, { round: true, col: st.on ? '#2e7d4a' : '#333', label: '⏻', size: 13 });
      if (pw.click) st.on = !st.on;
      /* the right-hand controls */
      const key = (id, xx, yy, lab, col, ww) => HL.button(ui, id, xx, yy, ww || 52, 22, { col: col || '#e9ebed', labelCol: '#222', label: lab, size: 9.5 });
      if (key('cursors', 540, 46, 'Cursors').click){ st.cur.mode = st.cur.mode === 'Off' ? 'X' : st.cur.mode === 'X' ? 'Y' : 'Off'; st.meas = false; }
      if (key('measure', 598, 46, 'Measure').click){ st.meas = !st.meas; if (st.meas) st.cur.mode = 'Off'; }
      if (key('auto', 656, 46, 'Auto Setup').click){ st.ti = 7; st.ch[0].vi = 10; st.ch[0].pos = -2; st.run = true; st.trig.mode = 'Auto'; }
      const rs = key('runstop', 714, 46, 'Run/Stop', st.run ? '#45b35a' : '#d9473b', 52);
      if (rs.click){ st.run = !st.run; st.single = false; }
      const sg = key('single', 714, 74, 'Single', st.single ? '#f0a020' : '#e9ebed');
      if (sg.click){ st.single = true; st.run = true; st.armT = st.now; st.lastTc = null; }
      /* the Adjust (universal) knob: moves the selected cursor */
      const adj = B3.encoder(ui, 'adj', 570, 102, 20, { label: 'Adjust' });
      if (adj){ const dv = adj * (0.04); if (st.cur.mode === 'X'){ if (st.cur.sel !== 1) st.cur.x[0] = Math.max(-5, Math.min(5, st.cur.x[0] + dv)); if (st.cur.sel !== 0) st.cur.x[1] = Math.max(-5, Math.min(5, st.cur.x[1] + dv)); }
        else if (st.cur.mode === 'Y'){ if (st.cur.sel !== 1) st.cur.y[0] = Math.max(-4, Math.min(4, st.cur.y[0] + dv)); if (st.cur.sel !== 0) st.cur.y[1] = Math.max(-4, Math.min(4, st.cur.y[1] + dv)); } }
      /* trigger */
      HL.text(g, 'TRIGGER', 700, 108, '#333', 9, 'center', '800');
      const lv = B3.encoder(ui, 'tlev', 700, 140, 17, { label: 'Level' });
      if (lv) st.trig.level = Math.round((st.trig.level + lv * VDIV[st.ch[st.trig.src].vi] * 0.04) * 1e4) / 1e4;
      if (key('tsrc', 598, 128, 'Source').click) st.trig.src = 1 - st.trig.src;
      if (key('tslope', 598, 154, 'Slope').click) st.trig.slope = -st.trig.slope;
      if (key('tmode', 730, 176, st.trig.mode, '#e9ebed', 40).click) st.trig.mode = st.trig.mode === 'Auto' ? 'Normal' : 'Auto';
      /* horizontal */
      HL.text(g, 'HORIZONTAL', 596, 196, '#333', 9, 'center', '800');
      const td = HL.knob(ui, 'tdiv', 580, 230, 22, st.ti, { min: 0, max: TDIV.length - 1, detents: TDIV.map((_, i) => i), sens: 0.04, label: 'S/div', labelCol: '#333', col: '#3a3d42' });
      st.ti = TDIV.length - 1 - (TDIV.length - 1 - td);
      const hp = B3.encoder(ui, 'hpos', 640, 236, 13, { label: 'Position' });
      if (hp) st.hpos = Math.round((st.hpos + hp * tdiv * 0.2) * 1e6) / 1e6;
      /* vertical: each channel its own position, V/div and on/off */
      HL.text(g, 'VERTICAL', 712, 210, '#333', 9, 'center', '800');
      [0, 1].forEach(c => { const xx = 686 + c * 52;
        const ps = B3.encoder(ui, 'vpos' + c, xx, 232, 11);
        if (ps) st.ch[c].pos = Math.max(-4, Math.min(4, Math.round((st.ch[c].pos + ps * 0.04) * 100) / 100));
        const vd = HL.knob(ui, 'vdiv' + c, xx, 278, 17, st.ch[c].vi, { min: 0, max: VDIV.length - 1, detents: VDIV.map((_, i) => i), sens: 0.04, col: '#3a3d42' });
        st.ch[c].vi = VDIV.length - 1 - (VDIV.length - 1 - vd);
        if (HL.button(ui, 'ch' + c, xx - 18, 304, 36, 22, { col: st.ch[c].on ? ['#e8d230', '#d050c4'][c] : '#e9ebed', labelCol: '#222', label: 'CH' + (c + 1), size: 9.5 }).click) st.ch[c].on = !st.ch[c].on;
        HL.circle(g, xx, 352, 13, '#c8b26a', '#555', 1); HL.circle(g, xx, 352, 6, '#2a2a2a'); HL.text(g, 'CH' + (c + 1), xx, 374, '#333', 8.5, 'center', '800'); });
      HL.text(g, 'Position', 712, 248, '#555', 8, 'center', '600'); HL.text(g, 'Volts/div', 712, 296, '#555', 8, 'center', '600');
      HL.circle(g, 600, 352, 11, '#c8b26a', '#555', 1); HL.circle(g, 600, 352, 5, '#2a2a2a'); HL.text(g, 'EXT TRIG', 600, 374, '#333', 8.5, 'center', '800');
    });
    tex3(cv, 0, 0, cv.width, cv.height, [x0 + 0.1, h - 0.1, z1 + 0.01], [w - 0.2, 0, 0], [0, -(h - 0.7), 0], { id: 'p:' + name });
    const bnc = c => [x0 + 0.1 + (w - 0.2) * (686 + c * 52) / 780, h - 0.1 - (h - 0.7) * 352 / 392, z1 + 0.6];
    for (const c of [0, 1]){ const q = bnc(c); cyl3('z', z1, z1 + 0.6, q[0], q[1], 0.42, '#c8b26a', { seg: 12 }); }
    return { ch1: bnc(0), ch2: bnc(1) };
  };

  /* ---------- SIGLENT SDG1032X function / arbitrary waveform generator (262 × 107 × 295 mm) ----------
     Square wave on CH1: frequency, amplitude (Vpp), offset 0, start phase; Burst mode with N cycles,
     fired by its Trigger soft key; Output CH1 on/off.  st.value(t) gives the output in volts. */
  B3.Sdg = function (){ Object.assign(this, { on: true, out: false, f: 1.667, amp: 4, ph: 0, burst: true, n: 3, sel: 'f', dig: 4, t0: null, cont0: 0 }); };
  B3.Sdg.prototype.value = function (t){
    if (!this.on || !this.out) return 0;
    const A = this.amp / 2;
    if (this.burst){ if (this.t0 === null) return 0; const u = t - this.t0; if (u < 0 || u >= this.n / this.f){ return 0; }
      return Math.sin(2 * Math.PI * this.f * u + this.ph * Math.PI / 180) >= 0 ? A : -A; }
    return Math.sin(2 * Math.PI * this.f * (t - this.cont0) + this.ph * Math.PI / 180) >= 0 ? A : -A;
  };
  B3.sdg = function (b, name, p, st){
    const [x, z] = p, w = 26.2, h = 10.7, d = 29.5, x0 = x - w / 2, z1 = z + d / 2;
    box3(x0, x0 + w, 0.8, h, z - d / 2, z1 - 0.8, '#d9dcdf', { id: 'm:' + name, top: '#e3e6e8' });
    box3(x0 - 0.2, x0 + w + 0.2, 0.6, h + 0.2, z1 - 0.8, z1, '#3c4045', { id: 'm:' + name });
    for (const fx of [x0 + 2, x0 + w - 2]) box3(fx - 1, fx + 1, 0, 0.8, z - 8, z + 8, '#222', { id: 'm:' + name });
    const PAR = { f: ['Freq', 'Hz', [100, 10, 1, 0.1, 0.01, 0.001], 0.001, 1000], amp: ['Ampl', 'Vpp', [10, 1, 0.1, 0.01, 0.001], 0.002, 20], ph: ['Phase', '°', [100, 10, 1, 0.1], 0, 360], n: ['N Cycle', 'Cyc', [100, 10, 1], 1, 50000] };
    const W = 654, H = 268;
    const cv = b.panel(name, W, H, ui => {
      const g = ui.g;
      g.fillStyle = '#c9ccd0'; g.fillRect(0, 0, W, H); HL.rr(g, 6, 6, W - 12, H - 12, 10, '#d8dbde');
      HL.text(g, 'SIGLENT', 22, 22, '#1d3f8a', 17, 'left', '900'); HL.text(g, 'SDG1032X  30MHz  Function/Arbitrary Waveform Generator', 120, 23, '#444', 9, 'left', '700');
      HL.rr(g, 18, 36, 280, 168, 6, '#16181b'); HL.rr(g, 24, 42, 268, 156, 3, '#0a1220');
      if (st.on){
        HL.text(g, 'CH1  Square' + (st.burst ? '  Burst' : ''), 32, 54, '#ffd23a', 11, 'left', '800'); HL.text(g, 'HiZ', 284, 54, '#9fc3ff', 9.5, 'right', '700');
        /* the waveform icon */
        g.strokeStyle = '#ffd23a'; g.lineWidth = 1.5; g.beginPath(); let yy = st.ph < 180 ? 72 : 96; g.moveTo(36, yy);
        for (let k = 0; k < 4; k++){ const x1 = 36 + k * 30; g.lineTo(x1 + 15, yy); yy = yy === 72 ? 96 : 72; g.lineTo(x1 + 15, yy); g.lineTo(x1 + 30, yy); yy = yy === 72 ? 96 : 72; g.lineTo(x1 + 30, yy); } g.stroke();
        const rows = [['f', st.f.toFixed(3) + ' Hz'], ['amp', st.amp.toFixed(3) + ' Vpp'], ['off', '0.000 Vdc'], ['ph', st.ph.toFixed(1) + ' °']].concat(st.burst ? [['n', st.n + ' Cycle']] : []);
        rows.forEach((r, k) => { const yy2 = 116 + k * 17; const lab = r[0] === 'off' ? 'Offset' : PAR[r[0]][0];
          if (st.sel === r[0]) HL.rr(g, 160, yy2 - 8, 126, 16, 2, '#1f4f8f');
          HL.text(g, lab, 168, yy2, '#c8d6e5', 10, 'left', '700'); HL.text(g, r[1], 282, yy2, '#ffffff', 10.5, 'right', '700', HL.MONO); });
        HL.text(g, st.out ? 'Output ON' : 'Output OFF', 36, 186, st.out ? '#5cff6e' : '#ff6a5a', 10, 'left', '800');
      }
      /* the soft keys right of the glass */
      const soft = [['f', 'Freq'], ['amp', 'Ampl'], ['ph', 'Phase'], ['n', 'N Cycle'], ['trig', 'Trigger'], ['burst', st.burst ? 'Burst On' : 'Burst Off']];
      soft.forEach((s2, k) => { const e = HL.button(ui, 'sk' + k, 304, 40 + k * 28, 60, 22, { col: '#4a4e54', label: s2[1], size: 9 });
        if (!e.click) return; if (PAR[s2[0]]) { st.sel = s2[0]; st.dig = { f: 4, amp: 2, ph: 1, n: 2 }[s2[0]]; }
        if (s2[0] === 'trig' && st.burst && st.out) st.t0 = b.t + 0.001;
        if (s2[0] === 'burst'){ st.burst = !st.burst; st.cont0 = b.t; } });
      /* waveform keys, the knob, the arrows, the outputs */
      ['Sine', 'Square', 'Ramp', 'Pulse', 'Noise', 'Arb'].forEach((wv, k) => HL.button(ui, 'wv' + k, 22 + k * 46, 212, 40, 20, { col: wv === 'Square' ? '#f0c53a' : '#e9ebed', labelCol: '#222', label: wv, size: 8.5 }));
      const kn = Math.round(B3.encoder(ui, 'knob', 430, 82, 26, { px: 14 }));
      if (kn){ const P = PAR[st.sel], step = P[2][Math.min(st.dig, P[2].length - 1)];
        st[st.sel] = Math.max(P[3], Math.min(P[4], Math.round((st[st.sel] + kn * step) * 1000) / 1000)); if (st.sel === 'n') st.n = Math.round(st.n); }
      if (HL.button(ui, 'left', 396, 124, 30, 22, { col: '#e9ebed', labelCol: '#222', label: '◀', size: 10 }).click) st.dig = Math.max(0, st.dig - 1);
      if (HL.button(ui, 'right', 434, 124, 30, 22, { col: '#e9ebed', labelCol: '#222', label: '▶', size: 10 }).click) st.dig = Math.min(PAR[st.sel][2].length - 1, st.dig + 1);
      HL.text(g, 'step ' + PAR[st.sel][2][Math.min(st.dig, PAR[st.sel][2].length - 1)] + ' ' + PAR[st.sel][1], 430, 160, '#333', 9, 'center', '700');
      ['Mod', 'Sweep', 'Burst'].forEach((m, k) => { const e = HL.button(ui, 'm' + k, 494, 40 + k * 28, 52, 22, { col: m === 'Burst' && st.burst ? '#f0c53a' : '#e9ebed', labelCol: '#222', label: m, size: 9 }); if (m === 'Burst' && e.click){ st.burst = !st.burst; st.cont0 = b.t; } });
      const o1 = HL.button(ui, 'out1', 494, 190, 52, 24, { col: st.out ? '#45b35a' : '#e9ebed', labelCol: '#222', label: 'CH1', size: 10 });
      if (o1.click) st.out = !st.out;
      HL.button(ui, 'out2', 562, 190, 52, 24, { col: '#e9ebed', labelCol: '#222', label: 'CH2', size: 10 });
      HL.circle(g, 520, 236, 11, '#c8b26a', '#555', 1); HL.circle(g, 520, 236, 5, '#2a2a2a'); HL.circle(g, 588, 236, 11, '#c8b26a', '#555', 1); HL.circle(g, 588, 236, 5, '#2a2a2a');
      const pw = HL.button(ui, 'pwr', 610, 40, 26, 26, { round: true, col: st.on ? '#2e7d4a' : '#333', label: '⏻', size: 13 }); if (pw.click){ st.on = !st.on; if (!st.on) st.out = false; }
    });
    tex3(cv, 0, 0, cv.width, cv.height, [x0 + 0.1, h - 0.1, z1 + 0.01], [w - 0.2, 0, 0], [0, -(h - 0.7), 0], { id: 'p:' + name });
    const q = [x0 + 0.1 + (w - 0.2) * 520 / 654, h - 0.1 - (h - 0.7) * 236 / 268, z1 + 0.6];
    cyl3('z', z1, z1 + 0.6, q[0], q[1], 0.42, '#c8b26a', { seg: 12 });
    return { ch1: q };
  };

  /* ---------- a reversing switch: DPDT knife switch on porcelain ---------- */
  B3.knife = function (b, name, p, st){
    const [x, z] = p, w = 7, d = 10.4, y0 = 0;
    if (st.pos === undefined) st.pos = 0;
    box3(x - w / 2, x + w / 2, y0, 1.2, z - d / 2, z + d / 2, '#efece4', { id: 'm:' + name, top: '#f6f4ee' });
    /* the clips: two at the hinge (middle), two at each end */
    const clip = (cx, cz) => { box3(cx - 0.25, cx + 0.25, 1.2, 2.6, cz - 0.6, cz + 0.6, '#c39a4a', { id: 'c:' + name }); };
    for (const cx of [x - 1.4, x + 1.4]) for (const cz of [z - 3.2, z, z + 3.2]) clip(cx, cz);
    /* the cross wires that make it reverse */
    line3([x - 1.4, 1.22, z - 3.2], [x + 1.4, 1.22, z + 3.2], '#b87333', 1.6); line3([x + 1.4, 1.22, z - 3.2], [x - 1.4, 1.22, z + 3.2], '#b87333', 1.6);
    /* the binding posts the leads go to, on the edges, with copper strips under to their clips:
       the supply on the right-hand edge to the hinge clips, the load on the back end to one pair of end clips */
    const T = { in1: [x + w / 2 - 0.75, z - 1.1], in2: [x + w / 2 - 0.75, z + 1.1], out1: [x - 1.4, z - d / 2 + 0.75], out2: [x + 1.4, z - d / 2 + 0.75] };
    line3([T.in1[0], 1.22, T.in1[1]], [x - 1.4, 1.22, z], '#b87333', 2.2); line3([T.in2[0], 1.22, T.in2[1]], [x + 1.4, 1.22, z], '#b87333', 2.2);
    line3([T.out1[0], 1.22, T.out1[1]], [x - 1.4, 1.22, z - 3.2], '#b87333', 2.2); line3([T.out2[0], 1.22, T.out2[1]], [x + 1.4, 1.22, z - 3.2], '#b87333', 2.2);
    B3.post(T.in1[0], 1.2, T.in1[1], '#c0392b'); B3.post(T.in2[0], 1.2, T.in2[1], '#1b1b1b');
    B3.post(T.out1[0], 1.2, T.out1[1], '#c0392b'); B3.post(T.out2[0], 1.2, T.out2[1], '#1b1b1b');
    /* the blades and the handle bar, turned about the hinge at z */
    const a = st.pos === 0 ? 0 : st.pos > 0 ? -1.38 : 1.38, L = 3.6;
    const tip = [0, 2.0 + Math.cos(a) * L, z + Math.sin(a) * L];
    for (const cx of [x - 1.4, x + 1.4]) B3.cylAB([cx, 2.0, z], [cx, tip[1], tip[2]], 0.18, '#d5b25c', { id: 'c:' + name, seg: 6 });
    B3.cylAB([x - 2.2, tip[1], tip[2]], [x + 2.2, tip[1], tip[2]], 0.45, '#1a1a1a', { id: 'c:' + name });
    B3.cylAB([x, tip[1], tip[2]], [x, tip[1] + Math.cos(a) * 1.8, tip[2] + Math.sin(a) * 1.8], 0.55, '#1a1a1a', { id: 'c:' + name });
    if (b.clicked('c:' + name)) st.pos = st.pos === 0 ? 1 : st.pos > 0 ? -1 : 0;
    text3([x - w / 2 + 0.3, 1.21, z + d / 2 - 0.4], [1, 0, 0], [0, 0, -1], st.pos > 0 ? '▲ +' : st.pos < 0 ? '▼ −' : 'OFF', 0.9, '#555', { weight: '800' });
    const top = 1.2 + 1.35;
    return { in1: [T.in1[0], top, T.in1[1]], in2: [T.in2[0], top, T.in2[1]], out1: [T.out1[0], top, T.out1[1]], out2: [T.out2[0], top, T.out2[1]] };
  };
})();
