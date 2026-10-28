/* HaslaLab sims: a close-up opens with a short zoom, the way a camera moves in on the instrument.
   HLzoom(canvas) is called just before a view changes: the frame as it is now is kept and blown up
   towards the point last clicked while it fades, and the new view comes up out of that point, over
   about half a second (HLzoom(canvas, {out: true}) backs out the other way).  Nothing is drawn into the sim's own canvas, so it can go on running. */
(() => {
  let last = null;
  addEventListener("pointerdown", e => { last = { x: e.clientX, y: e.clientY, t: performance.now() }; }, true);
  let live = null;
  window.HLzoom = function (cv, o) {
    o = o || {};
    if (!cv || !cv.getBoundingClientRect || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const r = cv.getBoundingClientRect();
    if (r.width < 4 || r.height < 4 || !cv.width || !cv.height) return;
    if (live) live.stop();
    const snap = document.createElement("canvas"); snap.width = cv.width; snap.height = cv.height;
    try { snap.getContext("2d").drawImage(o.from || cv, 0, 0, cv.width, cv.height); } catch (e) { return; }
    /* where the zoom goes in: the click, if it was on this canvas a moment ago, else its middle */
    let fx = 0.5, fy = 0.5;
    if (o.x !== undefined) { fx = o.x; fy = o.y; }
    else if (last && performance.now() - last.t < 1500 && last.x >= r.left && last.x <= r.right && last.y >= r.top && last.y <= r.bottom) {
      fx = (last.x - r.left) / r.width; fy = (last.y - r.top) / r.height; }
    const ov = document.createElement("canvas"); ov.width = cv.width; ov.height = cv.height;
    Object.assign(ov.style, { position: "fixed", left: r.left + "px", top: r.top + "px", width: r.width + "px", height: r.height + "px",
      pointerEvents: "none", zIndex: 60, borderRadius: getComputedStyle(cv).borderRadius });
    (document.fullscreenElement || document.body).appendChild(ov);
    const g = ov.getContext("2d"), W = ov.width, H = ov.height, ox = fx * W, oy = fy * H, bg = getComputedStyle(cv).backgroundColor;
    const dur = o.dur || 560, t0 = performance.now(); let raf = 0, done = false;
    const ease = s => s < 0.5 ? 4 * s * s * s : 1 - Math.pow(-2 * s + 2, 3) / 2;
    function draw(src, k, a) { g.globalAlpha = a; g.setTransform(k, 0, 0, k, ox - ox * k, oy - oy * k); g.drawImage(src, 0, 0); }
    function step(now) {
      if (done) return;
      const s = Math.min(1, (now - t0) / dur), e = ease(s);
      g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha = 1; g.clearRect(0, 0, W, H);
      if (bg && bg !== "rgba(0, 0, 0, 0)") { g.fillStyle = bg; g.fillRect(0, 0, W, H); }
      if (o.out) { try { draw(cv, 1.8 - 0.8 * e, 1); } catch (err) {} draw(snap, 1 - 0.55 * e, 1 - e); }   /* backing out: the close-up shrinks away */
      else { draw(snap, 1 + 1.4 * e, 1 - e); try { draw(cv, 0.5 + 0.5 * e, Math.min(1, e * 1.25)); } catch (err) {} }
      if (s >= 1) stop(); else raf = requestAnimationFrame(step);
    }
    function stop() { done = true; cancelAnimationFrame(raf); ov.remove(); if (live === api) live = null; }
    const api = { stop }; live = api;
    step(t0);
  };
  /* a close-up that opens as its own box (a dialog over the bench): it grows out of the point clicked */
  window.HLpop = function (el, o) {
    o = o || {};
    if (!el || !el.animate || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const r = el.getBoundingClientRect(); if (r.width < 4) return;
    let x = r.left + r.width / 2, y = r.top + r.height / 2;
    if (last && performance.now() - last.t < 1500) { x = last.x; y = last.y; }
    const dx = x - (r.left + r.width / 2), dy = y - (r.top + r.height / 2);
    el.animate([{ transform: `translate(${dx}px,${dy}px) scale(.18)`, opacity: 0 }, { transform: "none", opacity: 1 }],
      { duration: o.dur || 560, easing: "cubic-bezier(.45,0,.2,1)" });
  };
})();
/* HaslaLab sims: a full-screen button, as in the observation sims.
   The whole page goes full screen (so the parts box, the bench, the side panel and every close-up stay
   usable); the header and the ad are hidden while it is, and Esc or the button brings the page back. */
(() => {
  const root = document.documentElement;
  if (!(document.fullscreenEnabled || document.webkitFullscreenEnabled)) return;
  const isFull = () => !!(document.fullscreenElement || document.webkitFullscreenElement);
  const en = () => root.lang === "en";
  const text = () => isFull() ? (en() ? "Exit full screen (Esc)" : "전체화면 끝내기 (Esc)") : (en() ? "⛶ Full screen" : "⛶ 전체화면");

  const style = document.createElement("style");
  style.textContent = `
    #hl-full{font:600 12.5px/1 inherit;font-family:inherit;padding:7px 11px;border-radius:7px;cursor:pointer;
             border:1px solid #3a414a;background:#232830;color:#dfe7ee;white-space:nowrap}
    #hl-full:hover{background:#2c323b}
    #hl-full.float{position:fixed;right:14px;bottom:14px;z-index:70;box-shadow:0 4px 14px rgba(0,0,0,.35)}
    header > .lang #hl-full{margin-left:8px}
    html.hl-full #hl-full{position:fixed;left:14px;bottom:14px;top:auto;right:auto;z-index:70;margin:0;opacity:.82}
    html.hl-full #hl-full:hover{opacity:1}
    html.hl-full header, html.hl-full #haslalab-adfit-banner{display:none !important}
    html.hl-full .wrap{max-width:none !important}
  `;
  document.head.append(style);

  const btn = document.createElement("button");
  btn.id = "hl-full"; btn.type = "button";
  const lang = document.querySelector("header > .lang");
  if (lang) lang.append(btn); else { btn.classList.add("float"); document.body.append(btn); }

  /* while full screen the header is hidden, so the button moves out to the page itself */
  const sync = () => { const f = isFull(); root.classList.toggle("hl-full", f); btn.textContent = text();
    if (lang) { if (f && btn.parentNode !== document.body) document.body.append(btn); else if (!f && btn.parentNode !== lang) lang.append(btn); } };
  btn.addEventListener("click", () => {
    try {
      if (isFull()) (document.exitFullscreen || document.webkitExitFullscreen).call(document);
      else (root.requestFullscreen || root.webkitRequestFullscreen).call(root);
    } catch (e) {}
  });
  /* the sims lay their canvases out again on resize; give them one once the page has settled */
  const changed = () => { sync(); setTimeout(() => dispatchEvent(new Event("resize")), 60); };
  document.addEventListener("fullscreenchange", changed);
  document.addEventListener("webkitfullscreenchange", changed);
  new MutationObserver(sync).observe(root, {attributes: true, attributeFilter: ["lang"]});
  sync();
})();
