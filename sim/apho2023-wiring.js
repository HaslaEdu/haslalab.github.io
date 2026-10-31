/* APhO 2023 (Mongolia) — the wiring board shared by the two experiments.

   The control box is drawn from above with its four walls folded out flat round its lid, the way a
   drawing shows a box opened up: the jacks on its left wall (COIL / LASER, PHOTOGATE, DC 12 V), the
   lugs on its right wall (CH1/2, GND) and the BALL WIRES socket on its front end can all be seen at
   once, each where it is on the box, beside the label printed on the lid.  Round it lie the things the
   leads come from (the photogate, the magnet holder, the wall adaptor, the oscilloscope and its probe,
   the multimeters, the laser), and every lead ends in the plug it really has.

   A plug is moved with the hand: drag it onto a socket it fits (a 3.5 mm plug into a 3.5 mm jack, a
   BNC onto a BNC, a clip onto a lug or a post, a banana plug into a banana socket) and it goes in;
   drag it off and it comes out and lies where it was.  A click on a plug picks it up and a click on a
   socket puts it in, for those who would rather click.  While a plug is in the hand, every socket it
   fits is ringed in green.  Nothing else is checked: a wrong but possible connection is made.

   new WiringBoard(canvas, cfg) — cfg:
     W, H                      logical size of the board in px
     box: {x, y, s, L, tex}    centre of the lid, px per cm, wall height (cm), the printed lid (canvas, 8.2 x 16.2 cm)
     sockets: {id: {x, y, kind, dir, cap, label, col}}   dir: angle (rad) a plug sticks out along, screen axes
     ends: {id: {kind, rest: [x, y, dir], col, label}}
     at: {endId: socketId|null} the state, shared with the simulation (changed in place)
     draw(g, P)                the simulation's own drawing under the plugs (instruments, cables); P(end) = [x, y, dir]
     drawLid(g, B)             the switches and the lamp on the lid; B(u, v) = px of a lid point (cm from left, from back)
     lidHit(x, y), lidWheel(x, y, s)   clicks and wheel on the lid's controls, true if taken
     changed()                 called after a plug went in or came out
     tr(key)                   text */
(function(){
  const FIT = {j35: ["j35"], barrel: ["barrel"], bnc: ["bnc"], hook: ["lug", "post"], clip: ["lug", "post"], banana: ["banana"]};
  class WiringBoard {
    constructor(cv, cfg){
      this.cv = cv; this.cfg = cfg; this.g = cv.getContext("2d");
      this.hand = null; this.drag = null; this.mouse = [0, 0]; this.hover = null;
      this.order = [];                                   /* the last plug put in each socket goes on top */
      const P = e => this.pos(e);
      this.P = P;
      cv.style.touchAction = "none";
      cv.addEventListener("pointerdown", e => this.down(e));
      cv.addEventListener("pointermove", e => this.move(e));
      cv.addEventListener("pointerup", e => this.up(e));
      cv.addEventListener("pointercancel", () => { this.drag = null; this.draw(); });
      cv.addEventListener("contextmenu", e => { e.preventDefault(); if (this.hand){ this.hand = null; this.draw(); } else if (cfg.back) cfg.back(); });
      cv.addEventListener("wheel", e => { const p = this.xy(e); if (cfg.lidWheel && cfg.lidWheel(p[0], p[1], e.deltaY < 0 ? 1 : -1)){ e.preventDefault(); this.draw(); } }, {passive: false});
      this.layout();
    }
    layout(){
      const dpr = Math.min(2, Math.max(1, window.devicePixelRatio || 1)), w = this.cv.parentElement ? this.cv.parentElement.clientWidth || this.cfg.W : this.cfg.W;
      this.cv.style.width = Math.min(w, this.cfg.W * 1.4) + "px"; this.cv.style.height = "auto";
      this.cv.width = Math.round(this.cfg.W * dpr); this.cv.height = Math.round(this.cfg.H * dpr); this.dpr = dpr; this.draw(); }
    xy(e){ const r = this.cv.getBoundingClientRect(); return [(e.clientX - r.left) * this.cfg.W / r.width, (e.clientY - r.top) * this.cfg.H / r.height]; }
    fits(end, sock){ const e = this.cfg.ends[end], s = this.cfg.sockets[sock]; return !!(e && s && FIT[e.kind] && FIT[e.kind].includes(s.kind)); }
    inSock(sock){ const at = this.cfg.at; return Object.keys(at).filter(k => at[k] === sock).sort((a, b) => this.order.indexOf(a) - this.order.indexOf(b)); }
    /* where an end is now: in the hand, in its socket (sticking out along the socket's direction), or at rest */
    pos(end){
      if (this.drag && this.drag.end === end && this.drag.moved) return [this.mouse[0], this.mouse[1], this.drag.dir];
      const s = this.cfg.at[end] && this.cfg.sockets[this.cfg.at[end]];
      if (s){ const i = this.inSock(this.cfg.at[end]).indexOf(end), off = i * 0.45; return [s.x, s.y, s.dir + off]; }
      return this.cfg.ends[end].rest; }
    endAt(x, y){
      let best = null, bd = 1e9;
      for (const k in this.cfg.ends){ const p = this.pos(k), L = PLUG_LEN[this.cfg.ends[k].kind] || 30;
        /* the plug's body runs out from its tip along dir: the whole of it is a handle */
        for (let t = 0; t <= 1; t += 0.25){ const qx = p[0] + Math.cos(p[2]) * L * t, qy = p[1] + Math.sin(p[2]) * L * t, d = Math.hypot(x - qx, y - qy);
          if (d < 15 && d < bd){ bd = d; best = k; } } }
      return best; }
    sockAt(x, y, r){ let best = null, bd = r || 22;
      for (const k in this.cfg.sockets){ const s = this.cfg.sockets[k], d = Math.hypot(x - s.x, y - s.y); if (d < bd){ bd = d; best = k; } }
      return best; }
    /* a plug goes into a socket; one that was there and has no room is pushed out */
    plug(end, sock){
      const at = this.cfg.at, cap = this.cfg.sockets[sock].cap || 1, there = this.inSock(sock).filter(k => k !== end);
      while (there.length >= cap){ at[there.shift()] = null; }
      at[end] = sock; this.order = this.order.filter(k => k !== end).concat(end);
      if (this.cfg.changed) this.cfg.changed(); }
    pull(end){ if (this.cfg.at[end] !== null){ this.cfg.at[end] = null; if (this.cfg.changed) this.cfg.changed(); } }
    down(e){
      if (e.button === 2){ return; }
      if (e.button) return;
      const [x, y] = this.xy(e); this.mouse = [x, y]; this.cv.setPointerCapture(e.pointerId);
      if (this.cfg.lidHit && this.cfg.lidHit(x, y)){ this.draw(); return; }
      let end = this.endAt(x, y);
      if (!end){ const s = this.sockAt(x, y); if (s){ const there = this.inSock(s); if (there.length) end = there[there.length - 1];
        else if (this.hand && this.fits(this.hand, s)){ this.plug(this.hand, s); this.hand = null; this.draw(); return; } } }
      if (end){ const p = this.pos(end); this.drag = {end, dir: p[2], x0: x, y0: y, moved: false}; this.draw(); return; }
      if (this.hand){ this.hand = null; this.draw(); }
    }
    move(e){
      const [x, y] = this.xy(e); this.mouse = [x, y];
      if (this.drag){ if (Math.hypot(x - this.drag.x0, y - this.drag.y0) > 5) this.drag.moved = true; this.draw(); return; }
      const h = this.endAt(x, y) || this.sockAt(x, y) || (this.cfg.lidHit && this.cfg.lidHit(x, y, true) ? "lid" : null);
      this.cv.style.cursor = this.hand ? "copy" : h ? "pointer" : "default";
      if (this.hand) this.draw(); }
    up(e){
      const d = this.drag; this.drag = null; if (!d){ return; }
      const [x, y] = this.xy(e);
      if (!d.moved){ this.hand = this.hand === d.end ? null : d.end; this.draw(); return; }   /* a click: picked up */
      const s = this.sockAt(x, y, 30);
      if (s && this.fits(d.end, s)) this.plug(d.end, s); else this.pull(d.end);
      this.hand = null; this.draw(); }
    /* ---- drawing ---- */
    draw(){
      const g = this.g, c = this.cfg, b = c.box, s = b.s, dpr = this.dpr || 1;
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
      const bg = g.createLinearGradient(0, 0, 0, c.H); bg.addColorStop(0, "#3a3f46"); bg.addColorStop(1, "#2b2f35");
      g.fillStyle = bg; g.fillRect(0, 0, c.W, c.H);
      /* the box opened out: lid in the middle, a wall on each side */
      const LW = 8.2 * s, LL = 16.2 * s, WL = b.L * s, x0 = b.x - LW / 2, y0 = b.y - LL / 2;
      const wall = (pts) => { g.beginPath(); pts.forEach((p, i) => i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1])); g.closePath();
        const gr = g.createLinearGradient(pts[0][0], pts[0][1], pts[2][0], pts[2][1]); gr.addColorStop(0, "#1d1e22"); gr.addColorStop(1, "#141518"); g.fillStyle = gr; g.fill();
        g.strokeStyle = "#45484e"; g.lineWidth = 1; g.stroke(); };
      wall([[x0, y0], [x0 - WL, y0 + 10], [x0 - WL, y0 + LL - 10], [x0, y0 + LL]]);
      wall([[x0 + LW, y0], [x0 + LW + WL, y0 + 10], [x0 + LW + WL, y0 + LL - 10], [x0 + LW, y0 + LL]]);
      wall([[x0, y0 + LL], [x0 + 10, y0 + LL + WL], [x0 + LW - 10, y0 + LL + WL], [x0 + LW, y0 + LL]]);
      wall([[x0, y0], [x0 + 10, y0 - WL], [x0 + LW - 10, y0 - WL], [x0 + LW, y0]]);
      g.setLineDash([5, 4]); g.strokeStyle = "rgba(255,255,255,0.28)"; g.lineWidth = 1; g.strokeRect(x0, y0, LW, LL); g.setLineDash([]);
      g.fillStyle = "rgba(255,255,255,0.42)"; g.font = "600 11px -apple-system,'Segoe UI','Malgun Gothic',sans-serif"; g.textAlign = "center"; g.textBaseline = "middle";
      g.save(); g.translate(x0 - WL / 2, y0 + 18); g.fillText(c.tr("wbLeft"), 0, 0); g.restore();
      g.save(); g.translate(x0 + LW + WL / 2, y0 + 18); g.fillText(c.tr("wbRight"), 0, 0); g.restore();
      g.fillText(c.tr("wbFront"), b.x, y0 + LL + WL - 12); g.fillText(c.tr("wbBack"), b.x, y0 - WL + 14);
      g.save(); g.beginPath(); g.roundRect(x0, y0, LW, LL, 10); g.clip(); g.drawImage(b.tex, x0, y0, LW, LL); g.restore();
      const B = (u, v) => [x0 + u * s, y0 + v * s];
      if (c.drawLid) c.drawLid(g, B, s);
      /* the instruments round the box (their sockets are drawn on them), then the sockets */
      if (c.under) c.under(g);
      const handEnd = this.drag && this.drag.moved ? this.drag.end : this.hand;
      for (const k in c.sockets){ const so = c.sockets[k]; drawSocket(g, so);
        if (so.label){ g.font = "600 12px -apple-system,'Segoe UI','Malgun Gothic',sans-serif"; g.fillStyle = "#e8eef2"; g.textBaseline = "middle";
          const lx = so.lx !== undefined ? so.lx : so.x, ly = so.ly !== undefined ? so.ly : so.y + 22; g.textAlign = so.la || "center"; g.fillText(so.label, lx, ly); }
        if (handEnd){ const ok = this.fits(handEnd, k), near = ok && Math.hypot(this.mouse[0] - so.x, this.mouse[1] - so.y) < 30;
          if (ok){ g.strokeStyle = near ? "#7dff6a" : "rgba(125,255,106,0.55)"; g.lineWidth = near ? 4 : 2; g.beginPath(); g.arc(so.x, so.y, near ? 17 : 14, 0, 6.2832); g.stroke(); } } }
      /* the things round the box and the leads, then every plug on top */
      if (c.draw) c.draw(g, this.P);
      const ends = Object.keys(c.ends).sort((a, b2) => (a === handEnd) - (b2 === handEnd));
      for (const k of ends){ const p = this.pos(k), e = c.ends[k]; drawPlug(g, e.kind, p[0], p[1], p[2], e.col, k === handEnd || k === this.hand);
        if (!c.at[k] && e.label && !(this.drag && this.drag.end === k && this.drag.moved)){
          g.font = "11px -apple-system,'Segoe UI','Malgun Gothic',sans-serif"; g.fillStyle = "#c9d1d9"; g.textAlign = "center"; g.textBaseline = "top";
          const L = PLUG_LEN[e.kind] || 30; g.fillText(e.label, p[0] + Math.cos(p[2]) * L * 0.5, p[1] + Math.sin(p[2]) * L * 0.5 + 12); } }
      if (this.hand && !(this.drag && this.drag.moved)){ const p = this.pos(this.hand);
        g.setLineDash([5, 4]); g.strokeStyle = "#ffb347"; g.lineWidth = 1.5; g.beginPath(); g.moveTo(p[0], p[1]); g.lineTo(this.mouse[0], this.mouse[1]); g.stroke(); g.setLineDash([]); }
      if (c.after) c.after(g);
    }
  }
  /* a plug's length along its axis, from its tip, in px */
  const PLUG_LEN = {j35: 38, barrel: 40, bnc: 44, hook: 58, clip: 40, banana: 36};
  function drawSocket(g, s){
    const {x, y, kind} = s;
    g.save(); g.translate(x, y);
    if (kind === "j35"){ hex(g, 11, "#a9afb5", "#7c8288"); circ(g, 6.5, "#c3c8cd"); circ(g, 3.3, "#0b0b0c"); }
    else if (kind === "barrel"){ circ(g, 11, "#1b1c1f", "#5b5f66"); circ(g, 7, "#0b0b0c"); circ(g, 2.2, "#d7dbdf"); }
    else if (kind === "lug"){ hex(g, 9, "#b9bfc5", "#80868c"); g.save(); g.rotate(s.dir); g.fillStyle = "#d6d9dc"; g.strokeStyle = "#8f959b"; g.lineWidth = 1;
      g.beginPath(); g.roundRect(4, -5, 22, 10, 4); g.fill(); g.stroke(); circ2(g, 19, 0, 2.6, "#2a2c2f"); g.restore(); circ(g, 4, "#d0d5da"); }
    else if (kind === "banana"){ circ(g, 11, s.col || "#c8262b", "#5a1010"); circ(g, 5.2, "#2a0c0b"); circ(g, 2.6, "#0b0b0c"); }
    else if (kind === "bnc"){ if (s.col){ circ(g, 15, s.col); } circ(g, 11, "#cfd3d7", "#80868c"); circ(g, 7, "#1b1c1f"); circ(g, 2.2, "#e2c46a");
      g.fillStyle = "#b5babf"; g.fillRect(-14, -1.8, 4, 3.6); g.fillRect(10, -1.8, 4, 3.6); }
    else if (kind === "post"){ circ(g, 12, s.col || "#c0392b", "#3a0b08"); circ(g, 6, shadeHex(s.col || "#c0392b", 1.25)); circ(g, 2, "#e6e6e6"); }
    g.restore(); }
  function drawPlug(g, kind, x, y, a, col, lit){
    g.save(); g.translate(x, y); g.rotate(a);
    if (lit){ g.shadowColor = "rgba(255,170,60,0.9)"; g.shadowBlur = 12; }
    const body = (x0, x1, h, c1, c2) => { const gr = g.createLinearGradient(0, -h, 0, h); gr.addColorStop(0, c2 || shadeHex(c1, 1.5)); gr.addColorStop(0.5, c1); gr.addColorStop(1, shadeHex(c1, 0.6));
      g.fillStyle = gr; g.beginPath(); g.roundRect(x0, -h, x1 - x0, 2 * h, Math.min(h, 4)); g.fill(); };
    if (kind === "j35"){ body(0, 9, 2.4, "#c9ced3"); body(8, 12, 3.2, "#9aa0a6"); body(12, 38, 5.2, col || "#1b1c1f"); }
    else if (kind === "barrel"){ body(0, 10, 4.2, "#c9ced3"); body(9, 40, 6.4, col || "#1b1c1f"); }
    else if (kind === "bnc"){ body(0, 16, 8.5, "#c4c8cc"); for (let i = 2; i < 15; i += 3){ g.fillStyle = "rgba(90,95,100,0.6)"; g.fillRect(i, -8.5, 1, 17); } body(15, 44, 5.5, col || "#1d1f22"); }
    else if (kind === "hook"){ g.strokeStyle = "#d9dde1"; g.lineWidth = 2.2; g.beginPath(); g.moveTo(0, 0); g.lineTo(9, 0); g.arc(4, -3, 3.5, 0.3, Math.PI * 1.2, true); g.stroke();
      body(9, 24, 4.4, "#8e949a"); body(24, 58, 6.2, col || "#2b2d30"); g.fillStyle = "#e7c843"; g.fillRect(44, -6.2, 3, 12.4); }
    else if (kind === "clip"){ g.fillStyle = "#c9ced3"; g.beginPath(); g.moveTo(0, -1); g.lineTo(16, -5); g.lineTo(16, 5); g.lineTo(0, 1); g.closePath(); g.fill();
      g.strokeStyle = "#8a9096"; g.lineWidth = 0.8; for (let i = 3; i < 15; i += 3){ g.beginPath(); g.moveTo(i, -2.5); g.lineTo(i, 2.5); g.stroke(); }
      body(14, 40, 5.6, col || "#1b1c1f"); }
    else if (kind === "banana"){ body(0, 11, 2.2, "#d0d4d8"); for (const xx of [3, 6, 9]){ g.fillStyle = "#a9afb5"; g.fillRect(xx, -2.6, 1, 5.2); } body(10, 36, 5.4, col || "#c8262b"); body(16, 20, 6.4, col || "#c8262b"); }
    g.restore(); }
  function circ(g, r, f, s){ g.beginPath(); g.arc(0, 0, r, 0, 6.2832); g.fillStyle = f; g.fill(); if (s){ g.strokeStyle = s; g.lineWidth = 1.2; g.stroke(); } }
  function circ2(g, x, y, r, f){ g.beginPath(); g.arc(x, y, r, 0, 6.2832); g.fillStyle = f; g.fill(); }
  function hex(g, r, f, s){ g.beginPath(); for (let i = 0; i < 6; i++){ const t = i / 6 * 6.2832 + 0.52; i ? g.lineTo(r * Math.cos(t), r * Math.sin(t)) : g.moveTo(r * Math.cos(t), r * Math.sin(t)); } g.closePath(); g.fillStyle = f; g.fill(); g.strokeStyle = s; g.lineWidth = 1; g.stroke(); }
  function shadeHex(c, f){ const h = c.replace("#", ""); const v = [0, 2, 4].map(i => Math.max(0, Math.min(255, Math.round(parseInt(h.slice(i, i + 2), 16) * f))));
    return "#" + v.map(n => n.toString(16).padStart(2, "0")).join(""); }
  /* a lead drawn as a cable: a shaded line along a smooth curve through the points */
  function cable(g, pts, col, w){
    const path = () => { g.beginPath(); g.moveTo(pts[0][0], pts[0][1]);
      for (let i = 1; i < pts.length - 1; i++){ const mx = (pts[i][0] + pts[i + 1][0]) / 2, my = (pts[i][1] + pts[i + 1][1]) / 2; g.quadraticCurveTo(pts[i][0], pts[i][1], mx, my); }
      g.lineTo(pts[pts.length - 1][0], pts[pts.length - 1][1]); };
    g.lineCap = "round"; g.lineJoin = "round";
    path(); g.strokeStyle = "rgba(0,0,0,0.35)"; g.lineWidth = w + 3; g.stroke();
    path(); g.strokeStyle = col; g.lineWidth = w; g.stroke();
    path(); g.strokeStyle = "rgba(255,255,255,0.18)"; g.lineWidth = Math.max(1, w * 0.3); g.stroke(); }
  /* the tail of a plug: the point its cable leaves from */
  function tail(p, kind){ const L = PLUG_LEN[kind] || 30; return [p[0] + Math.cos(p[2]) * L, p[1] + Math.sin(p[2]) * L]; }
  /* a cable leaving a plug's tail straight back along it before it bends */
  function behind(p, kind, d){ const L = (PLUG_LEN[kind] || 30) + d; return [p[0] + Math.cos(p[2]) * L, p[1] + Math.sin(p[2]) * L]; }
  /* a toggle seen from above: its nut, and the lever leaning towards the side it is thrown to */
  function toggleTop(g, x, y, up, s){
    g.save(); g.translate(x, y);
    hex(g, 0.5 * s, "#c7ccd1", "#8a9096"); circ(g, 0.3 * s, "#aeb4ba");
    const ty = (up ? -1 : 1) * 1.05 * s;
    g.strokeStyle = "#dfe3e7"; g.lineWidth = 0.22 * s; g.lineCap = "round"; g.beginPath(); g.moveTo(0, 0); g.lineTo(0, ty * 0.7); g.stroke();
    g.beginPath(); g.ellipse(0, ty, 0.28 * s, 0.42 * s, 0, 0, 6.2832); g.fillStyle = "#c8262b"; g.fill(); g.strokeStyle = "#7e1418"; g.lineWidth = 1; g.stroke();
    g.restore(); }
  function lamp(g, x, y, lit, s){ g.save(); g.translate(x, y); circ(g, 0.42 * s, "#141416");
    if (lit){ const gr = g.createRadialGradient(0, 0, 1, 0, 0, 1.4 * s); gr.addColorStop(0, "rgba(255,80,60,0.75)"); gr.addColorStop(1, "rgba(255,80,60,0)"); g.fillStyle = gr; g.beginPath(); g.arc(0, 0, 1.4 * s, 0, 6.2832); g.fill(); }
    circ(g, 0.3 * s, lit ? "#ff3b2e" : "#6e1712"); g.restore(); }
  function knobTop(g, x, y, a, s){ g.save(); g.translate(x, y); circ(g, 0.82 * s, "#141518", "#3a3c40");
    for (let i = 0; i < 18; i++){ const t = i / 18 * 6.2832; g.strokeStyle = "#2c2e33"; g.lineWidth = 1; g.beginPath(); g.moveTo(0.7 * s * Math.cos(t), 0.7 * s * Math.sin(t)); g.lineTo(0.82 * s * Math.cos(t), 0.82 * s * Math.sin(t)); g.stroke(); }
    circ(g, 0.62 * s, "#d5d9dd", "#9aa0a6"); g.strokeStyle = "#4a4f55"; g.lineWidth = 2; g.beginPath(); g.moveTo(0.12 * s * Math.sin(a), -0.12 * s * Math.cos(a)); g.lineTo(0.56 * s * Math.sin(a), -0.56 * s * Math.cos(a)); g.stroke(); g.restore(); }
  function label(g, t, x, y, o){ o = o || {}; g.font = (o.w || "600") + " " + (o.px || 12) + "px -apple-system,'Segoe UI','Malgun Gothic',sans-serif";
    g.textAlign = o.al || "center"; g.textBaseline = "middle"; g.fillStyle = o.col || "#e8eef2"; g.fillText(t, x, y); }
  window.WiringBoard = WiringBoard;
  window.WB = {cable, tail, behind, toggleTop, lamp, knobTop, label, drawPlug, PLUG_LEN, shadeHex};

  /* ---- one control box for both experiments ----------------------------------------------------
     In the exam both experiments are on the bench at once (exam.html shows them side by side) and, as
     at the olympiad, there is only one control box and one 12 V adaptor.  The set stands on one bench
     at a time: the other bench sees an empty place and a button that carries it over, which pulls out
     every plug that was in it.  Outside the exam each page has its own box. */
  window.SharedBox = function(me, onMove){
    const exam = new URLSearchParams(location.search).get("exam") === "1";
    const self = {exam, here: true, other: null, me, shared: () => false, take: () => {}};
    if (!exam || typeof BroadcastChannel === "undefined") return self;
    const ch = new BroadcastChannel("hl-apho2023-box"), KEY = "hlApho2023Box";
    const read = () => { try { return sessionStorage.getItem(KEY); } catch (e){ return null; } };
    const write = v => { try { sessionStorage.setItem(KEY, v); } catch (e){} };
    const apply = (owner) => { const was = self.here; self.here = owner === me; if (was !== self.here) onMove(self.here); };
    ch.onmessage = ev => { const m = ev.data || {};
      if (m.t === "hello" && m.from !== me){ self.other = m.from; ch.postMessage({t: "here", from: me}); if (!read()) write(me < m.from ? me : m.from); apply(read()); onMove(self.here, true); }
      else if (m.t === "here" && m.from !== me){ self.other = m.from; if (!read()) write(me < m.from ? me : m.from); apply(read()); onMove(self.here, true); }
      else if (m.t === "owner"){ apply(m.owner); } };
    self.take = () => { write(me); ch.postMessage({t: "owner", owner: me}); apply(me); };
    self.shared = () => !!self.other;
    ch.postMessage({t: "hello", from: me});
    const o = read(); if (o) apply(o);
    return self;
  };
})();
