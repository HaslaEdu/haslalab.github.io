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

  /* ---------- circuits: what the leads join, solved by nodal analysis every frame ----------
     c = new B3.Circuit(); c.R(a, b, ohm); c.C(a, b, farad, key); c.V(a, b, emf, rint)  (a is +);
     c.D(a, b, {Is, n, Vz, Rz, Gl, Rs})  (a is the anode; Vz for a Zener's reverse breakdown, Gl its leakage);
     c.I(a, b, amp)  (driven from b to a inside).  Terminal names are strings; c.join(x, y) shorts two of them.
     c.solve(dt) → node voltages; c.V_(t) the voltage of a terminal, c.cur(el) the current through an element (a→b inside).
     Capacitors keep their charge between frames under their key. */
  B3.Circuit = function (){ this.mem = {}; this.reset(); };
  B3.Circuit.prototype.reset = function (){ this.els = []; this.joins = []; };
  B3.Circuit.prototype.R = function (a, b, R){ const e = { k: 'R', a, b, R }; this.els.push(e); return e; };
  B3.Circuit.prototype.C = function (a, b, C, key){ const e = { k: 'C', a, b, C, key: key || a + '|' + b }; this.els.push(e); return e; };
  B3.Circuit.prototype.V = function (a, b, E, R){ const e = { k: 'V', a, b, E, R: R || 1e-3 }; this.els.push(e); return e; };
  /* a diode a → b; its bulk resistance Rs sits in series on an inner node of its own */
  B3.Circuit.prototype.D = function (a, b, o){
    const e = Object.assign({ k: 'D', a, b, Is: 1e-12, n: 1.8, Gl: 1e-9, Rs: 1 }, o || {});
    if (e.Rs > 0){ const mid = '_d' + this.els.length; e.rs = this.R(a, mid, e.Rs); e.j = mid; }
    this.els.push(e); return e; };
  B3.Circuit.prototype.I = function (a, b, I){ const e = { k: 'I', a, b, I }; this.els.push(e); return e; };
  B3.Circuit.prototype.join = function (a, b){ this.joins.push([a, b]); };
  B3.Circuit.prototype.solve = function (dt){
    dt = Math.max(1e-6, dt || 0.02);
    const par = {}, find = x => { while (par[x] !== undefined && par[x] !== x) x = par[x]; return x; };
    const add = x => { if (par[x] === undefined) par[x] = x; };
    for (const e of this.els){ add(e.a); add(e.b); }
    for (const [a, b] of this.joins){ add(a); add(b); const ra = find(a), rb = find(b); if (ra !== rb) par[ra] = rb; }
    const idx = {}; let n = 0; for (const k in par){ const r = find(k); if (idx[r] === undefined) idx[r] = n++; }
    this.node = t => par[t] === undefined ? -1 : idx[find(t)];
    const VT = 0.02585, mem = this.mem;
    /* the separate circuits (what the elements and leads connect), each needs one reference node */
    const cp = Array.from({ length: n }, (_, i) => i), cf = x => { while (cp[x] !== x) x = cp[x] = cp[cp[x]]; return x; };
    for (const e of this.els){ const a = this.node(e.a), b = this.node(e.b); if (a >= 0 && b >= 0) cp[cf(a)] = cf(b); }
    const refs = [...new Set(Array.from({ length: n }, (_, i) => cf(i)))];
    let v = new Float64Array(n); if (this.vlast && this.vlast.length === n) v.set(this.vlast);
    for (let it = 0; it < 40; it++){
      const G = Array.from({ length: n }, () => new Float64Array(n)), I = new Float64Array(n);
      for (let i = 0; i < n; i++) G[i][i] += 1e-12;
      for (const r of refs) G[r][r] += 1;                                 /* one node of each separate circuit held at 0 V */
      const st = (a, b, g) => { if (a >= 0) G[a][a] += g; if (b >= 0) G[b][b] += g; if (a >= 0 && b >= 0){ G[a][b] -= g; G[b][a] -= g; } };
      const src = (a, b, i) => { if (a >= 0) I[a] += i; if (b >= 0) I[b] -= i; };          /* i pushed into a, out of b */
      for (const e of this.els){
        const a = this.node(e.a), b = this.node(e.b);
        if (e.k === 'R') st(a, b, 1 / Math.max(1e-9, e.R));
        else if (e.k === 'V'){ const g = 1 / e.R; st(a, b, g); src(a, b, e.E * g); }
        else if (e.k === 'I') src(a, b, e.I);
        else if (e.k === 'C'){ const g = e.C / dt, v0 = mem[e.key] || 0; st(a, b, g); src(a, b, g * v0); }
        else if (e.k === 'D'){
          const ja = e.j ? this.node(e.j) : a;                          /* the junction, behind its series resistance */
          let vd = (ja >= 0 ? v[ja] : 0) - (b >= 0 ? v[b] : 0); const nv = e.n * VT, vmax = nv * Math.log(10 / e.Is + 1); vd = Math.min(vd, vmax);
          let id = e.Is * (Math.exp(vd / nv) - 1), gd = e.Is / nv * Math.exp(vd / nv);
          if (e.Vz && vd < -e.Vz){ id += (vd + e.Vz) / (e.Rz || 5); gd += 1 / (e.Rz || 5); }
          id += e.Gl * vd; gd += e.Gl;
          st(ja, b, gd); src(ja, b, -(id - gd * vd));
        }
      }
      const x = gaussSolve(G, I); if (!x) break;
      let dv = 0; for (let i = 0; i < n; i++){ const d = x[i] - v[i]; dv = Math.max(dv, Math.abs(d)); v[i] = v[i] + Math.max(-0.5, Math.min(0.5, d)); }
      if (dv < 1e-7) break;
    }
    this.vlast = v; this.v = v;
    for (const e of this.els) if (e.k === 'C') mem[e.key] = this.vd(e);
    return v;
  };
  B3.Circuit.prototype.V_ = function (t){ const i = this.node ? this.node(t) : -1; return i >= 0 && this.v ? this.v[i] : 0; };
  B3.Circuit.prototype.vd = function (e){ return this.V_(e.a) - this.V_(e.b); };
  B3.Circuit.prototype.cur = function (e){ const v = this.vd(e);
    if (e.k === 'R') return v / e.R; if (e.k === 'V') return (v - e.E) / e.R; if (e.k === 'I') return -e.I;
    if (e.k === 'D'){ if (e.rs) return this.cur(e.rs);
      const nv = e.n * 0.02585; let id = e.Is * (Math.exp(Math.min(v, nv * Math.log(10 / e.Is + 1)) / nv) - 1); if (e.Vz && v < -e.Vz) id += (v + e.Vz) / (e.Rz || 5); return id + e.Gl * v; }
    return 0; };
  B3.Circuit.prototype.charge = function (key){ return this.mem[key] || 0; };
  function gaussSolve(A, b){ const n = b.length, M = A.map((r, i) => { const x = Array.from(r); x.push(b[i]); return x; });
    for (let c = 0; c < n; c++){ let p = c; for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
      if (Math.abs(M[p][c]) < 1e-30) return null; [M[c], M[p]] = [M[p], M[c]];
      for (let r = 0; r < n; r++){ if (r === c) continue; const f = M[r][c] / M[c][c]; if (!f) continue; for (let k = c; k <= n; k++) M[r][k] -= f * M[c][k]; } }
    return M.map((r, i) => r[n] / r[i]); }

  /* ---------- generic laboratory parts ---------- */
  /* a printed scale as a texture: len cm long, mm marks, cm numbers every o.every cm; o.from the first number;
     vertical (numbers grow upwards) unless o.horiz.  Cached by its options. */
  const _scales = {};
  B3.scaleTex = function (len, o){
    o = o || {}; const key = JSON.stringify([len, o]); if (_scales[key]) return _scales[key];
    const k = o.px || 40, W = Math.round((o.width || 3) * k), Lp = Math.round(len * k), c = document.createElement('canvas');
    if (o.horiz){ c.width = Lp + 2 * k; c.height = W; } else { c.width = W; c.height = Lp + 2 * k; }
    c._static = true; const g = c.getContext('2d'); g.fillStyle = o.bg || '#f1e2b8'; g.fillRect(0, 0, c.width, c.height);
    g.strokeStyle = o.ink || '#1a1a1a'; g.fillStyle = o.ink || '#1a1a1a';
    const step = o.step || 0.1, n = Math.round(len / step), from = o.from || 0, every = o.every || 1;
    for (let i = 0; i <= n; i++){ const v = i * step, pos = k + v * k, cm = Math.abs(v - Math.round(v)) < 1e-6, half = Math.abs(v * 2 - Math.round(v * 2)) < 1e-6;
      const L = (cm ? 0.45 : half ? 0.32 : 0.2) * W; g.lineWidth = cm ? 2 : 1.2; g.beginPath();
      if (o.horiz){ g.moveTo(pos, 0); g.lineTo(pos, L); if (o.both){ g.moveTo(pos, W); g.lineTo(pos, W - L); } }
      else { const y = c.height - pos; g.moveTo(0, y); g.lineTo(L, y); if (o.both){ g.moveTo(W, y); g.lineTo(W - L, y); } }
      g.stroke();
      if (cm && Math.round(v) % every === 0){ g.font = '700 ' + Math.round(k * 0.55) + 'px sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
        if (o.horiz) g.fillText(String(Math.round(v) + from), pos, W * 0.68); else { g.save(); g.translate(W * 0.7, c.height - pos); g.rotate(-Math.PI / 2); g.fillText(String(Math.round(v) + from), 0, 0); g.restore(); } } }
    if (o.label){ g.font = '600 ' + Math.round(k * 0.4) + 'px sans-serif'; g.fillText(o.label, o.horiz ? k * 0.6 : W * 0.7, o.horiz ? W * 0.68 : c.height - k * 0.5); }
    _scales[key] = c; return c;
  };
  /* a metre stick standing upright on a little foot, scale on the +z face; returns the y of a reading r (cm) */
  B3.meterStick = function (x, z, len, id, o){
    o = o || {}; const w = 2.8, t = 0.6, base = 0.8;
    box3(x - 3, x + 3, 0, base, z - 3, z + 3, '#5d4630', { id, top: '#6b5238' });
    box3(x - w / 2, x + w / 2, base, base + len + 1, z - t / 2, z + t / 2, '#d9c48f', { id });
    const c = B3.scaleTex(len, { width: w, both: true });
    tex3(c, 0, 0, c.width, c.height, [x - w / 2, base + len + 1, z + t / 2 + 0.01], [w, 0, 0], [0, -(len + 2), 0], { id });
    return r => base + r;
  };
  /* a retort stand: heavy base, rod; returns {rod:[x, z], top} */
  B3.stand = function (x, z, H, o){
    o = o || {}; const id = o.id;
    box3(x - (o.bw || 10), x + (o.bw || 10), 0, 1.6, z - (o.bd || 14), z + 4, '#3b4048', { id, top: '#474c55' });
    cyl3('y', 1.6, H, x, z, 0.6, '#c3c8cd', { id, seg: 14, cap: '#dde1e4' });
    return { rod: [x, z], top: H };
  };
  /* a boss-head clamp on a rod at height y with an arm of length len pointing along +z (or o.dir 'x') */
  B3.clampArm = function (x, z, y, len, o){
    o = o || {}; const id = o.id, dir = o.dir || 'z';
    box3(x - 1.3, x + 1.3, y - 1.3, y + 1.3, z - 1.3, z + 1.3, '#3a3f46', { id, top: '#474c55' });
    cyl3('x', x + 1.3, x + 3.0, y, z, 0.35, '#9aa0a6', { id, seg: 8 }); box3(x + 3, x + 3.6, y - 0.9, y + 0.9, z - 0.9, z + 0.9, '#25282c', { id });
    if (dir === 'z') cyl3('z', z + 1.3, z + len, x, y, 0.5, '#c3c8cd', { id, seg: 12, cap: '#dde1e4' });
    else cyl3('x', x - len, x - 1.3, y, z, 0.5, '#c3c8cd', { id, seg: 12, cap: '#dde1e4' });
    return dir === 'z' ? [x, y - 0.5, z + len - 0.6] : [x - len + 0.6, y - 0.5, z];
  };
  /* a coil spring from point a (top) down to b, with n turns of radius r */
  B3.spring = function (a, b, n, r, col, lw, o){
    const pts = [], N = Math.max(24, Math.round(n * 14)), d = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], L = Math.hypot(...d);
    const u = d.map(v => v / L), e1 = Math.abs(u[1]) > 0.9 ? [1, 0, 0] : [0, 1, 0];
    let p1 = [u[1] * e1[2] - u[2] * e1[1], u[2] * e1[0] - u[0] * e1[2], u[0] * e1[1] - u[1] * e1[0]]; const m1 = Math.hypot(...p1); p1 = p1.map(v => v / m1);
    const p2 = [u[1] * p1[2] - u[2] * p1[1], u[2] * p1[0] - u[0] * p1[2], u[0] * p1[1] - u[1] * p1[0]];
    const end = Math.min(1.2, L * 0.08);
    pts.push(a); for (let i = 0; i <= N; i++){ const s = i / N, th = s * n * 2 * Math.PI, along = end + s * (L - 2 * end);
      pts.push([a[0] + u[0] * along + r * (Math.cos(th) * p1[0] + Math.sin(th) * p2[0]), a[1] + u[1] * along + r * (Math.cos(th) * p1[1] + Math.sin(th) * p2[1]), a[2] + u[2] * along + r * (Math.cos(th) * p1[2] + Math.sin(th) * p2[2])]); }
    pts.push(b); poly3(pts, col || '#9aa3ab', lw || 1.6, o);
  };
  /* a glass vessel (beaker / jar) standing at (x, z): outer radius r, height h, liquid up to level (cm above
     the inside bottom, 0 = empty); o.liq the liquid colour, o.id */
  B3.vessel = function (x, z, r, h, level, o){
    o = o || {}; const id = o.id, wall = o.wall || 0.3, base = o.base || 0.6, seg = o.seg || 40;
    cyl3('y', 0, base, x, z, r, 'rgba(200,225,235,.5)', { id, seg, cap: 'rgba(210,235,245,.35)' });
    if (level > 0) cyl3('y', base, base + level, x, z, r - wall, o.liq || 'rgba(110,170,220,.38)', { id, seg, cap: o.liqTop || 'rgba(140,195,235,.45)', noObst: true });
    cyl3('y', base, h, x, z, r, o.glass || 'rgba(205,228,238,.16)', { id, seg, caps: false, noObst: true });
    if (o.marks) for (const [yy, lab] of o.marks){ line3([x - r * 0.5, base + yy, z + r + 0.01], [x - r * 0.15, base + yy, z + r + 0.01], 'rgba(255,255,255,.8)', 1);
      if (lab) text3([x - r * 0.1, base + yy + 0.25, z + r + 0.02], [0.6, 0, 0], [0, -0.6, 0], lab, 0.7, 'rgba(255,255,255,.85)'); }
    return base;
  };

  /* a black box on the desk: a closed case with its terminals (4 mm sockets) along the top front.
     terms: [{ name, col, label }]; returns the terminal ids (name → 'box.<name>' unless given) */
  B3.blackBox = function (b, leads, name, p, terms, o){
    o = o || {}; const [x, z] = p, w = o.w || Math.max(10, terms.length * 4 + 2), d = o.d || 8, h = o.h || 4.5;
    box3(x - w / 2, x + w / 2, 0, h, z - d / 2, z + d / 2, o.col || '#1d1f22', { id: 'm:' + name, top: o.top || '#26292d' });
    if (o.label) text3([x - w / 2 + 0.8, h + 0.02, z + d / 2 - 0.8], [1, 0, 0], [0, 0, -1], o.label, 0.7, '#8a9096', { weight: '700' });
    const ids = {};
    terms.forEach((t, i) => { const tx = x - (terms.length - 1) * 2 + i * 4, id = t.id || name + '.' + t.name; ids[t.name] = id;
      leads.term(b, id, [tx, h, z - 0.8], { col: t.col, label: t.label || '', lc: '#d8d8d8', ls: 0.9 }); });
    return ids;
  };
  /* cells in a holder (n in series, EMF each e, internal resistance r each), its leads ending in sockets:
     returns { plus, minus } terminal ids and stamps itself with .stamp(c) */
  B3.cells = function (b, leads, name, p, o){
    o = o || {}; const [x, z] = p, n = o.n || 1, L = 5.2, D = 1.45, w = n * (D + 0.2) + 0.6;
    box3(x - w / 2, x + w / 2, 0, 1.0, z - L / 2 - 0.6, z + L / 2 + 0.6, '#1b1b1b', { id: 'm:' + name, top: '#242424' });
    for (let i = 0; i < n; i++){ const cx = x - w / 2 + 0.3 + D / 2 + 0.1 + i * (D + 0.2);
      cyl3('z', z - L / 2, z + L / 2, cx, 1.0 + D / 2 - 0.25, D / 2, o.cellCol || '#c9a227', { seg: 16, id: 'm:' + name, cap: '#b8b8b8' });
      cyl3('z', z - L / 2 + 0.3, z + L / 2 - 1.2, cx, 1.0 + D / 2 - 0.25, D / 2 + 0.01, o.wrap || '#2b2b2b', { seg: 16, caps: false, id: 'm:' + name }); }
    const P = name + '.plus', M = name + '.minus';
    leads.term(b, P, [x - w / 2 - 1.4, 0.6, z + L / 2], { col: '#c0392b', label: '+', lc: '#e8e8e8' });
    leads.term(b, M, [x + w / 2 + 1.4, 0.6, z + L / 2], { col: '#1b1b1b', label: '−', lc: '#e8e8e8' });
    B3.cable([x - w / 2 + 0.2, 0.7, z + L / 2 + 0.4], [x - w / 2 - 1.4, 0.8, z + L / 2], '#c0392b', 0.2, 2);
    B3.cable([x + w / 2 - 0.2, 0.7, z + L / 2 + 0.4], [x + w / 2 + 1.4, 0.8, z + L / 2], '#1b1b1b', 0.2, 2);
    return { plus: P, minus: M, stamp: c => c.V(P, M, (o.e || 1.55) * n, Math.max(1e-3, (o.r || 0.3) * n)) };
  };

  /* ---------- test leads: click a terminal, then another; click a terminal with a plug in it to pull
     that plug out (the lead then follows the pointer until it goes into another terminal or is dropped
     on the desk).  Terminals are registered every frame with B3.Leads.term; their ids are 'c:t:<name>'. */
  const LEADCOL = ['#c0392b', '#1b1b1b', '#2f6ea6', '#e0a526', '#3f8f4f', '#7d4fa0'];
  B3.Leads = function (o){ o = o || {}; this.list = o.list || []; this.held = null; this.T = {}; this.n = 0; this.max = o.max || 12; };
  /* a terminal: a 4 mm socket (or a post, o.post) at p; o.col its ring colour, o.label printed beside it */
  B3.Leads.prototype.term = function (b, name, p, o){
    o = o || {}; this.T[name] = { p, up: o.up || [0, 1, 0] };
    const id = 'c:t:' + name, col = o.col || '#1b1b1b';
    if (o.post) B3.post(p[0], p[1], p[2], col, id);
    else if (o.face === 'z'){ cyl3('z', p[2], p[2] + 0.35, p[0], p[1], 0.62, col, { seg: 14, id, cap: B3.shade(col, 0.7) }); cyl3('z', p[2] + 0.35, p[2] + 0.37, p[0], p[1], 0.24, '#0a0a0a', { seg: 10, id }); }
    else { cyl3('y', p[1] - 0.05, p[1] + 0.3, p[0], p[2], 0.62, col, { seg: 14, id, cap: B3.shade(col, 0.7) }); cyl3('y', p[1] + 0.3, p[1] + 0.32, p[0], p[2], 0.24, '#0a0a0a', { seg: 10, id }); }
    if (o.label) text3([p[0] + (o.lx || 0.9), p[1] + 0.33, p[2] + (o.lz || 0.3)], [1, 0, 0], [0, 0, -1], o.label, o.ls || 0.7, o.lc || '#e8e8e8', { weight: '800' });
    if (b.clicked(id)) this.click(b, name);
  };
  B3.Leads.prototype.click = function (b, name){
    if (this.held){ const h = this.held; this.held = null;
      if (h.from === name) return;
      if (this.list.length >= this.max){ b.say('선이 더 없습니다.', 'No leads left.'); return; }
      this.list.push({ a: h.from, b: name, col: h.col }); return; }
    const i = this.list.map((l, k) => [l, k]).reverse().find(([l]) => l.a === name || l.b === name);
    if (i){ const [l, k] = i; this.list.splice(k, 1); this.held = { from: l.a === name ? l.b : l.a, col: l.col }; return; }
    this.held = { from: name, col: LEADCOL[this.n++ % LEADCOL.length] };
  };
  B3.Leads.prototype.joined = function (a, b){ return this.list.some(l => (l.a === a && l.b === b) || (l.a === b && l.b === a)); };
  B3.Leads.prototype.wire = function (c){ for (const l of this.list) c.join(l.a, l.b); };
  /* the leads themselves, drawn last so they lie over everything; a click on the bare desk drops a held one */
  B3.Leads.prototype.draw = function (b){
    const plug = (p, up, col) => { const top = [p[0] + up[0] * 2.2, p[1] + up[1] * 2.2, p[2] + up[2] * 2.2];
      B3.cylAB([p[0] + up[0] * 0.3, p[1] + up[1] * 0.3, p[2] + up[2] * 0.3], top, 0.42, col, { seg: 10 });
      B3.cylAB([p[0], p[1], p[2]], [p[0] + up[0] * 0.35, p[1] + up[1] * 0.35, p[2] + up[2] * 0.35], 0.22, '#c8b26a', { seg: 8 }); return top; };
    for (const l of this.list){ const A = this.T[l.a], Bt = this.T[l.b]; if (!A || !Bt) continue;
      const col = l.col || '#c0392b', a = plug(A.p, A.up, col), c = plug(Bt.p, Bt.up, col);
      B3.cable(a, c, col, Math.min(14, 2 + Math.hypot(c[0] - a[0], c[2] - a[2]) * 0.18), 2.4); }
    if (this.held){ const A = this.T[this.held.from]; const m = b.mouseOn ? b.mouseOn(0.6) : null;
      if (A && m){ const a = plug(A.p, A.up, this.held.col), end = [m[0], 3.2, m[2]];
        B3.cylAB(end, [end[0], end[1] + 2, end[2]], 0.42, this.held.col, { seg: 10 }); B3.cable(a, end, this.held.col, 2, 2.4); }
      if (b.clicked('desk')) this.held = null; }
  };

  /* ---------- a handheld digital multimeter lying on the desk (after a UNI-T UT33-class meter) ----------
     B3.dmm(b, name, [x, z], st, leads, o) draws it, registers its jacks (COM, VΩ, mA) with the leads and
     returns the meter as circuit elements to add: m.stamp(c) before c.solve, m.read(c) after.
     o.ranges lists the dial by full scale: [['OFF'], ['V', 0.2], ['V', 2], ['A', 2e-4], ['Ω', 2000], …]; o.counts 2000 or 4000 (the resolution);
     o.rA {range: Ω} the shunt of each current range; st.err {V, A, R} the meter's gain errors. */
  B3.dmm = function (b, name, p, st, leads, o){
    o = o || {}; const counts = o.counts || 2000;
    const R = o.ranges || [['OFF'], ['V', 0.2], ['V', 2], ['V', 20], ['V', 200], ['A', 2e-4], ['A', 2e-3], ['A', 2e-2], ['A', 0.2], ['Ω', 200], ['Ω', 2e3], ['Ω', 2e4], ['Ω', 2e5], ['Ω', 2e6]];
    if (st.dial === undefined) st.dial = 0; if (st.fuse === undefined) st.fuse = true; if (!st.err) st.err = { V: 0, A: 0, R: 0 };
    const [x, z] = p, w = 8.6, d = 16.5, h = 3.4, J = { COM: name + '.COM', V: name + '.V', mA: name + '.mA' };
    box3(x - w / 2, x + w / 2, 0, h, z - d / 2, z + d / 2, '#e5a400', { id: 'm:' + name, top: '#3a3d42' });
    box3(x - w / 2 + 0.25, x + w / 2 - 0.25, h, h + 0.12, z - d / 2 + 0.25, z + d / 2 - 0.25, '#2b2e33', { id: 'm:' + name });
    const pos = st.dial, sel = R[pos] || ['OFF'], mode = sel[0], rng = sel[1];
    const fmt = () => {
      if (mode === 'OFF') return '';
      const m = st.meas; if (m === undefined || m === null) return '';
      const fs = rng;
      if (Math.abs(m) > fs * 1.0) return mode === 'Ω' ? 'OL' : (m < 0 ? '-OL' : 'OL');
      const unit = mode === 'V' ? (rng < 1 ? 1e-3 : 1) : mode === 'A' ? (rng < 1e-3 ? 1e-6 : rng < 1 ? 1e-3 : 1) : (rng < 1e3 ? 1 : rng < 1e6 ? 1e3 : 1e6);
      const val = m / unit, fsU = fs / unit, dp = Math.max(0, 3 - Math.floor(Math.log10(fsU * 1.0001)));
      return (val < 0 ? '-' : '') + Math.abs(val).toFixed(Math.min(3, dp));
    };
    const unitTxt = () => mode === 'V' ? (rng < 1 ? 'mV' : 'V') : mode === 'A' ? (rng < 1e-3 ? 'µA' : rng < 1 ? 'mA' : 'A') : mode === 'Ω' ? (rng < 1e3 ? 'Ω' : rng < 1e6 ? 'kΩ' : 'MΩ') : '';
    const cv = b.panel(name, 300, 560, ui => {
      const g = ui.g; HL.rr(g, 0, 0, 300, 560, 22, '#2b2e33');
      HL.text(g, o.brand || 'UNI-T', 24, 26, '#e5a400', 15, 'left', '800'); HL.text(g, o.model || 'UT33C+', 276, 26, '#c8ced6', 12, 'right', '700');
      HL.rr(g, 24, 44, 252, 116, 10, '#11161a'); HL.rr(g, 32, 52, 236, 100, 6, '#aab89a');
      const s = st.fuse ? fmt() : (mode === 'A' ? 'FUSE' : fmt());
      HL.text(g, s, 244, 104, '#1b2318', 50, 'right', '700', HL.MONO);
      HL.text(g, unitTxt(), 250, 136, '#1b2318', 14, 'right', '800');
      if (mode !== 'OFF') HL.text(g, mode === 'V' ? 'DC' : mode === 'A' ? 'DC' : '', 44, 66, '#1b2318', 12, 'left', '800');
      /* the dial: positions round the knob, click one to turn to it, or roll the wheel on the knob */
      const cx = 150, cy = 330, Rr = 118;
      HL.circle(g, cx, cy, Rr + 14, '#33373d');
      const ang = i => -Math.PI / 2 + (i - 0) * 2 * Math.PI / R.length;
      R.forEach((r, i) => { const a = ang(i), lx = cx + Math.cos(a) * Rr, ly = cy + Math.sin(a) * Rr;
        const lab = r[0] === 'OFF' ? 'OFF' : r[0] === 'V' ? (r[1] < 1 ? r[1] * 1e3 + 'm' : String(r[1])) : r[0] === 'A' ? (r[1] < 1e-3 || r[1] === 4e-3 ? Math.round(r[1] * 1e6) + 'µ' : r[1] < 1 ? Math.round(r[1] * 1e3) + 'm' : r[1] + 'A') : (r[1] < 1e3 ? String(r[1]) : r[1] < 1e6 ? r[1] / 1e3 + 'k' : r[1] / 1e6 + 'M');
        const col = r[0] === 'V' ? '#ffd27a' : r[0] === 'A' ? '#ff9a8a' : r[0] === 'Ω' ? '#9ad0ff' : '#e8e8e8';
        const e = ui.hit('d' + i, { cx: lx, cy: ly, r: 17 }); if (e.click) st.dial = i;
        HL.text(g, lab, lx, ly, i === pos ? '#ffffff' : col, i === pos ? 15 : 13, 'center', i === pos ? '800' : '600'); });
      HL.text(g, 'V⎓', cx - 92, cy - 4, '#ffd27a', 14, 'center', '800'); HL.text(g, 'A⎓', cx + 92, cy + 30, '#ff9a8a', 14, 'center', '800'); HL.text(g, 'Ω', cx - 70, cy + 92, '#9ad0ff', 16, 'center', '800');
      const k = ui.hit('knob', { cx, cy, r: 62 }, { wheel: true, cursor: 'pointer' });
      if (k.wheel) st.dial = (st.dial - k.wheel + R.length * 9) % R.length; else if (k.click) st.dial = (st.dial + 1) % R.length;
      HL.circle(g, cx, cy, 62, '#1d2024', '#0b0c0e', 2); HL.rr(g, cx - 12, cy - 60, 24, 120, 10, '#3a3f46');
      const a = ang(pos); g.strokeStyle = '#ffffff'; g.lineWidth = 5; g.beginPath(); g.moveTo(cx + Math.cos(a) * 20, cy + Math.sin(a) * 20); g.lineTo(cx + Math.cos(a) * 56, cy + Math.sin(a) * 56); g.stroke();
      [[o.aJack || 'mA', 66], ['COM', 150], ['VΩ', 234]].forEach(([t, jx]) => { HL.text(g, t, jx, 545, t === 'COM' ? '#e8e8e8' : '#ff9a8a', 12, 'center', '800'); });
      if (!st.fuse) HL.text(g, o.fuseTxt || 'FUSE ✕', 66, 470, '#ff6b5a', 11, 'center', '800');
    });
    B3.tex3(cv, 0, 0, cv.width, cv.height, [x - w / 2 + 0.3, h + 0.13, z - d / 2 + 0.3], [w - 0.6, 0, 0], [0, 0, d - 0.6], { id: 'p:' + name });
    const jy = h + 0.13, jz = z - d / 2 + 0.3 + (d - 0.6) * 505 / 560;
    leads.term(b, J.mA, [x - w / 2 + 0.3 + (w - 0.6) * 66 / 300, jy, jz], { col: '#c0392b' });
    leads.term(b, J.COM, [x - w / 2 + 0.3 + (w - 0.6) * 150 / 300, jy, jz], { col: '#1b1b1b' });
    leads.term(b, J.V, [x - w / 2 + 0.3 + (w - 0.6) * 234 / 300, jy, jz], { col: '#c0392b' });
    const rA = o.rA || {}, shunt = r => rA[r] !== undefined ? rA[r] : r <= 2e-4 ? 1000 : r <= 2e-3 ? 100 : r <= 2e-2 ? 10 : 1;
    const fuseI = o.fuseI || 0.4;
    return {
      jacks: J,
      stamp(c){
        if (mode === 'V' || mode === 'OFF' || mode === 'A') c.R(J.V, J.COM, 1e7);
        if (mode === 'Ω'){ this.ohm = c.V(J.V, J.COM, 1.0, rng); }                     /* a 1 V source behind the range resistor */
        if (mode === 'A' && st.fuse) this.sh = c.R(J.mA, J.COM, shunt(rng)); else this.sh = null;
      },
      /* the true value now (st.now) and what the display shows, which takes a new reading about three times
         a second (o.rate) with a little noise in the last digit */
      read(c){
        let m;
        if (mode === 'V') m = (c.V_(J.V) - c.V_(J.COM)) * (1 + st.err.V);
        else if (mode === 'A'){ const i = this.sh ? c.cur(this.sh) : 0; if (Math.abs(i) > fuseI){ st.fuse = false; b.say('퍽! 전류계 퓨즈가 끊어졌습니다.', 'Pop! The ammeter fuse has blown.'); } m = i * (1 + st.err.A); }
        else if (mode === 'Ω'){ const v = c.V_(J.V) - c.V_(J.COM), i = (1.0 - v) / rng; m = i > 1e-12 ? Math.max(0, v / i) * (1 + st.err.R) : Infinity; }
        else m = null;
        st.now = m;
        const key = mode + rng, per = 1 / (o.rate || 3);
        if (key !== st.key || st.tUpd === undefined || b.t - st.tUpd >= per || b.t < st.tUpd){
          st.key = key; st.tUpd = b.t;
          st.meas = m === null || !isFinite(m) ? m : m + HL.gauss(rng / counts * 0.4);
        }
        return st.meas;
      },
      mode, range: rng
    };
  };
})();
