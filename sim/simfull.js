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
/* HaslaLab sims: remember the last sims opened on this device (the home page offers "continue", the
   problem cards show "done"), and the first time any sim is opened, a short guided tour of the bench:
   the parts tray, the bench itself (with the sim's own instructions), then the side panel.
   Nothing here runs inside an exam (where the sim sits in a frame). */
(() => {
  const inFrame = (() => { try { return window.top !== window; } catch (e) { return true; } })();
  if (inFrame) return;
  const store = { get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
                  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} } };
  const file = location.pathname.split("/").pop();
  function remember() {
    const title = (document.title || file).replace(/\s*[·|]\s*HaslaLab\s*$/, "");
    const list = store.get("hl-recent-sims", []).filter(r => r.file !== file);
    list.unshift({ file, title, t: Date.now() });
    store.set("hl-recent-sims", list.slice(0, 40));
  }
  const lang = () => (document.documentElement.lang || "ko").startsWith("en") ? "en" : "ko";
  const TXT = {
    ko: { first: "처음 오셨네요", skip: "안내 건너뛰기", prev: "이전", next: "다음", done: "시작하기", again: "조작 안내",
          tray: ["부품함", "부품을 클릭해 집은 뒤, 실험대의 레일이나 책상을 클릭하면 놓입니다. 우클릭하면 부품함으로 되돌립니다."],
          bench: ["실험대", "빈 곳을 끌면 시점이 돌아가고 휠로 확대합니다."],
          panel: ["조작판", "시간 배속·측정·기록 같은 도구가 여기 있고, 맨 아래에 자세한 도움말이 있습니다. 이 안내는 왼쪽 아래 「조작 안내」로 다시 볼 수 있습니다."],
          trayT: ["부품함", "부품을 탭해 집은 뒤, 실험대의 레일이나 책상을 탭하면 놓입니다. 부품함으로 되돌리려면 오른쪽 아래 「우클릭」을 누른 뒤 부품을 탭하세요."],
          benchT: ["실험대", "빈 곳을 끌면 시점이 돌아가고, 두 손가락을 벌리거나 오므리면 확대·축소합니다. 다이얼·손잡이는 한 번 탭한 뒤 오른쪽 아래 ＋/－로 돌리고(「미세」는 작은 단계), 두 번 탭하면 시점이 처음으로 돌아갑니다."] },
    en: { first: "First time here", skip: "Skip the tour", prev: "Back", next: "Next", done: "Start", again: "How to use",
          tray: ["Parts box", "Click a part to pick it up, then click the rail or the desk to put it down. Right-click returns it to the box."],
          bench: ["The bench", "Drag empty space to turn the view and use the wheel to zoom."],
          panel: ["Side panel", "Time scale, measuring and recording tools are here, with the full help at the bottom. Open this tour again with «How to use» at the bottom left."],
          trayT: ["Parts box", "Tap a part to pick it up, then tap the rail or the desk to put it down. To return a part to the box, press «Right-click» at the bottom right, then tap the part."],
          benchT: ["The bench", "Drag empty space to turn the view and pinch with two fingers to zoom. Tap a dial or knob once, then turn it with ＋/－ at the bottom right («Fine» for small steps); double-tap to reset the view."] } };
  function steps() {
    const T = TXT[lang()], out = [], touch = document.documentElement.classList.contains("hl-touch");
    const tray = document.querySelector("aside.tray"), cv = document.getElementById("cv"), panel = document.querySelector("aside.panel");
    /* a sim whose left column is not a parts box says what it is: data-tour-ko / data-tour-en on the aside */
    if (tray && tray.offsetWidth) { const own = tray.getAttribute("data-tour-" + lang()), h = tray.querySelector("h3");
      out.push({ el: tray, t: own ? [(h && h.textContent.trim()) || T.tray[0], own] : (touch ? T.trayT : T.tray) }); }
    if (cv && cv.offsetWidth) { const cap = (document.getElementById("t-cap") || {}).textContent; out.push({ el: cv, t: touch ? T.benchT : [T.bench[0], cap && cap.trim().length > 20 ? cap.trim() : T.bench[1]] }); }
    if (panel && panel.offsetWidth) out.push({ el: panel, t: T.panel });
    return out;
  }
  let tour = null;
  function close(finished) {
    if (!tour) return; tour.ring.remove(); tour.box.remove(); removeEventListener("resize", tour.place); removeEventListener("keydown", tour.key, true);
    tour = null; store.set("hl-sim-tour-done", true); if (finished !== false) againBtn();
  }
  function start() {
    const S = steps(); if (S.length < 2 || tour) return;
    const T = TXT[lang()];
    const ring = document.createElement("div"), box = document.createElement("div");
    Object.assign(ring.style, { position: "fixed", zIndex: 9000, border: "3px solid #f2c14e", borderRadius: "12px", boxShadow: "0 0 0 9999px rgba(8,10,14,.55)", pointerEvents: "none", transition: "all .3s ease" });
    Object.assign(box.style, { position: "fixed", zIndex: 9001, width: "min(320px, calc(100vw - 24px))", background: "#fff", color: "#16212E", borderRadius: "12px", padding: "16px 18px",
      boxShadow: "0 14px 34px rgba(0,0,0,.4)", font: "14px/1.55 'IBM Plex Sans KR','Malgun Gothic',system-ui,sans-serif" });
    box.setAttribute("role", "dialog"); box.setAttribute("aria-live", "polite");
    document.body.append(ring, box);
    let k = 0;
    const place = () => {
      const r = S[k].el.getBoundingClientRect(), vh = innerHeight, vw = innerWidth;
      const top = Math.max(6, r.top - 6), h = Math.min(vh - 12 - top, r.height + 12);
      Object.assign(ring.style, { left: (r.left - 6) + "px", top: top + "px", width: (r.width + 12) + "px", height: h + "px" });
      const bw = box.offsetWidth, bh = box.offsetHeight;
      let x = r.right + 18; if (x + bw > vw - 12) x = r.left - bw - 18; if (x < 12) x = Math.min(vw - bw - 12, Math.max(12, r.left + 24));
      let y = Math.min(vh - bh - 12, Math.max(12, top + 30));
      if (x >= r.left - 6 && x <= r.right + 6) y = Math.min(vh - bh - 12, Math.max(12, top + h - bh - 20));   /* over a wide part: sit near its foot */
      Object.assign(box.style, { left: x + "px", top: y + "px" });
    };
    const paint = () => {
      const [title, body] = S[k].t, last = k === S.length - 1;
      box.innerHTML = `<div style="font:600 11px ui-monospace,Consolas,monospace;color:#5d43b0;letter-spacing:.1em;margin-bottom:4px">${T.first} · ${k + 1} / ${S.length}</div>`
        + `<b style="font-size:16px"></b><p style="margin:6px 0 0"></p>`
        + `<div style="display:flex;gap:8px;margin-top:14px;align-items:center"><button type="button" data-a="skip" style="margin-right:auto;border:0;background:none;color:#5C6B7A;font:inherit;font-size:12.5px;cursor:pointer;padding:4px 0">${T.skip}</button>`
        + (k ? `<button type="button" data-a="prev" style="border:1px solid #B4CADC;background:#fff;color:#16212E;border-radius:8px;padding:5px 12px;font:inherit;font-size:13px;cursor:pointer">${T.prev}</button>` : "")
        + `<button type="button" data-a="next" style="border:0;background:#5d43b0;color:#fff;border-radius:8px;padding:6px 14px;font:inherit;font-size:13px;font-weight:600;cursor:pointer">${last ? T.done : T.next}</button></div>`;
      box.querySelector("b").textContent = title; box.querySelector("p").textContent = body;
      place(); box.querySelector('[data-a="next"]').focus({ preventScroll: true });
    };
    box.addEventListener("click", e => { const a = e.target.closest("button"); if (!a) return;
      if (a.dataset.a === "skip") close(); else if (a.dataset.a === "prev") { k--; paint(); } else if (k < S.length - 1) { k++; paint(); } else close(); });
    const key = e => { if (e.key === "Escape") { close(); e.preventDefault(); } };
    addEventListener("resize", place); addEventListener("keydown", key, true);
    tour = { ring, box, place, key };
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) ring.style.transition = "none";
    paint();
  }
  function againBtn() {
    if (document.getElementById("hlTourAgain") || steps().length < 2) return;
    const b = document.createElement("button"); b.id = "hlTourAgain"; b.type = "button"; b.textContent = "? " + TXT[lang()].again;
    Object.assign(b.style, { position: "fixed", left: "12px", bottom: "12px", zIndex: 40, border: "1px solid #3b4450", background: "rgba(21,24,29,.85)", color: "#d8dee5",
      borderRadius: "999px", padding: "6px 12px", font: "12px 'IBM Plex Sans KR','Malgun Gothic',system-ui,sans-serif", cursor: "pointer" });
    b.addEventListener("click", start); document.body.append(b);
  }
  addEventListener("load", () => {
    remember();
    setTimeout(() => { if (store.get("hl-sim-tour-done", false)) againBtn(); else start(); }, 700);   /* after the sim has laid itself out */
  });
})();
/* HaslaLab sims on tablets: a finger works the bench the way a mouse does.
   - every touch on a canvas also sends the mouse events a mouse would (so sims that listen for mousedown/mousemove can
     be dragged), and a double tap is a double click;
   - two fingers pinch to zoom (sent as ctrl+wheel at the middle of the fingers, which every bench reads as zoom);
   - a small touch bar at the bottom right stands in for what a finger has no way to do:
     «우클릭 / Right-click» turns the next touch into a right-button press (put a part back in the box, or drag to pan),
     ＋ / － are the mouse wheel at the point last touched (turn the dial or knob there, or zoom), and
     «미세 / Fine» holds Shift on them for the fine steps;
   - buttons, boxes and text get larger.
   This runs inside the exam's frame too. */
(() => {
  const root = document.documentElement;
  const coarse = matchMedia("(pointer: coarse)");
  const en = () => (root.lang || "ko").startsWith("en");
  let on = false, bar = null;
  const style = document.createElement("style");
  style.textContent = `
    html.hl-touch canvas{-webkit-touch-callout:none;-webkit-user-select:none;user-select:none}
    html.hl-touch button,html.hl-touch select,html.hl-touch input:not([type=checkbox]):not([type=radio]):not([type=range]){min-height:36px;touch-action:manipulation}
    html.hl-touch input[type=checkbox],html.hl-touch input[type=radio]{width:20px;height:20px}
    html.hl-touch input[type=range]{min-height:30px;touch-action:manipulation}
    html.hl-touch aside.panel,html.hl-touch aside.tray,html.hl-touch .card{font-size:max(1em,14px)}
    html.hl-touch .hint{font-size:13px !important;line-height:1.6}
    html.hl-touch .chk{min-height:32px}
    #hlTouch{position:fixed;right:12px;bottom:12px;z-index:65;display:flex;flex-direction:column;gap:8px;align-items:flex-end;
             font:600 13px/1 'IBM Plex Sans KR','Malgun Gothic',system-ui,sans-serif;-webkit-user-select:none;user-select:none}
    #hlTouch button{min-width:52px;height:52px;border-radius:26px;border:1px solid #4a5260;background:rgba(21,24,29,.86);color:#e4e9ee;
             padding:0 14px;font:inherit;font-size:13px;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.35);touch-action:manipulation}
    #hlTouch button.big{font-size:24px;font-weight:500;padding:0}
    #hlTouch button[aria-pressed=true]{background:#f2c14e;color:#16212e;border-color:#f2c14e}
    #hlTouch .row{display:flex;gap:8px}
    #hlTouch.min button:not(.tg){display:none}
    #hlTouch button.tg{min-width:40px;height:40px;font-size:15px;opacity:.75}
    html.hl-full #hlTouch{bottom:62px}
    @media print{#hlTouch{display:none}}`;
  document.head.append(style);

  /* the touch bar */
  const S = { right: false, fine: false, last: null };   /* last: {el, x, y} the last point touched on a canvas */
  function label() {
    if (!bar) return;
    const E = en();
    bar.querySelector('[data-k="right"]').textContent = E ? "Right-click" : "우클릭";
    bar.querySelector('[data-k="right"]').title = E ? "The next touch is a right-button press: put a part back, or drag to pan" : "다음 터치를 오른쪽 버튼으로: 부품 되돌리기, 끌면 시점 이동";
    bar.querySelector('[data-k="fine"]').textContent = E ? "Fine" : "미세";
    bar.querySelector('[data-k="fine"]').title = E ? "＋/－ in fine steps (Shift)" : "＋/－를 미세 단계로 (Shift)";
    bar.querySelector('[data-k="up"]').title = E ? "Wheel up at the point last touched (zoom in, or turn the dial there)" : "마지막으로 누른 곳에서 휠 위로 (확대, 또는 그곳의 다이얼 돌리기)";
    bar.querySelector('[data-k="down"]').title = E ? "Wheel down at the point last touched" : "마지막으로 누른 곳에서 휠 아래로";
    bar.querySelector('[data-k="tg"]').title = E ? "Hide or show the touch bar" : "터치 도구 숨기기/보이기";
  }
  function bigCanvas() {
    let best = null, area = 0;
    for (const c of document.querySelectorAll("canvas")) { const r = c.getBoundingClientRect(), a = r.width * r.height;
      if (a > area && r.width > 120 && r.bottom > 0 && r.top < innerHeight) { best = c; area = a; } }
    return best;
  }
  function wheel(dir) {
    let t = S.last && document.contains(S.last.el) ? S.last : null;
    if (!t) { const c = bigCanvas(); if (!c) return; const r = c.getBoundingClientRect(); t = { el: c, x: r.left + r.width / 2, y: r.top + r.height / 2 }; }
    t.el.dispatchEvent(new WheelEvent("wheel", { bubbles: true, cancelable: true, composed: true, clientX: t.x, clientY: t.y, screenX: t.x, screenY: t.y,
      deltaY: dir * -100, deltaMode: 0, shiftKey: S.fine }));
  }
  function makeBar() {
    if (bar || !document.body) return;
    bar = document.createElement("div"); bar.id = "hlTouch";
    bar.innerHTML = `<button type="button" class="tg" data-k="tg" aria-label="touch tools">✋</button>
      <button type="button" data-k="right" aria-pressed="false"></button>
      <div class="row"><button type="button" class="big" data-k="down">－</button><button type="button" class="big" data-k="up">＋</button></div>
      <button type="button" data-k="fine" aria-pressed="false"></button>`;
    /* the bar's own buttons repeat while held, like a wheel turned on */
    let rep = 0;
    const stopRep = () => { clearTimeout(rep); clearInterval(rep); rep = 0; };
    bar.addEventListener("pointerdown", e => {
      const b = e.target.closest("button"); if (!b) return; e.preventDefault();
      const k = b.dataset.k;
      if (k === "up" || k === "down") { const d = k === "up" ? 1 : -1; wheel(d); stopRep(); rep = setTimeout(() => { rep = setInterval(() => wheel(d), 90); }, 380); }
      else if (k === "right") { S.right = !S.right; b.setAttribute("aria-pressed", S.right); }
      else if (k === "fine") { S.fine = !S.fine; b.setAttribute("aria-pressed", S.fine); }
      else if (k === "tg") bar.classList.toggle("min");
    });
    ["pointerup", "pointercancel", "pointerleave"].forEach(t => bar.addEventListener(t, stopRep));
    bar.addEventListener("click", e => e.stopPropagation());
    document.body.append(bar); label();
    new MutationObserver(label).observe(root, { attributes: true, attributeFilter: ["lang"] });
  }
  function enable() {
    if (on) return; on = true; root.classList.add("hl-touch");
    if (document.body) makeBar(); else addEventListener("DOMContentLoaded", makeBar);
    canvases();
  }
  /* a finger on a big canvas must not scroll or zoom the page */
  function canvases() { if (!on) return; for (const c of document.querySelectorAll("canvas")) if (c.getBoundingClientRect().width >= 160 && !c.style.touchAction) c.style.touchAction = "none"; }
  addEventListener("load", canvases); addEventListener("resize", canvases);
  if (coarse.matches || navigator.maxTouchPoints > 1 && !matchMedia("(hover: hover)").matches) enable();

  /* forwarding: what a mouse would have sent */
  const ME = (type, src, x, y, button, buttons, extra) => Object.assign({ bubbles: true, cancelable: true, composed: true, view: window,
    clientX: x, clientY: y, screenX: src.screenX, screenY: src.screenY, button, buttons }, extra || {});
  const send = (el, type, init, pointer) => el.dispatchEvent(pointer ? new PointerEvent(type, init) : (type === "wheel" ? new WheelEvent(type, init) : new MouseEvent(type, init)));
  const G = new Map();            /* active touches on canvases: pointerId -> {el, x, y, x0, y0, right} */
  let pinch = null, lastTap = null, sentDbl = 0;
  const isCv = el => el && el.tagName === "CANVAS" && el.getBoundingClientRect().width >= 60;
  addEventListener("pointerdown", e => {
    if (e.pointerType !== "touch" || !e.isTrusted) return;
    enable();
    if (!isCv(e.target)) return;
    const el = e.target, x = e.clientX, y = e.clientY, own = !!el.closest("[data-hl-own-touch]");   /* a bench with its own touch handling */
    S.last = { el, x, y };
    if (!own) e.preventDefault();          /* no late compat mouse events: they are sent here, in step with the finger */
    if (G.size === 1 && !pinch) {  /* a second finger: pinch. The first finger's press is let go where it is now */
      const [id, g] = [...G.entries()][0];
      if (!g.right && !g.own) { send(g.el, "pointerup", ME("pointerup", e, g.x, g.y, 0, 0, { pointerId: id, pointerType: "touch", isPrimary: true }), true);
        send(g.el, "mouseup", ME("mouseup", e, g.x, g.y, 0, 0)); }
      G.set(e.pointerId, { el, x, y, x0: x, y0: y, pinch: true }); g.pinch = true;
      const a = [...G.values()]; pinch = { d: Math.hypot(a[0].x - a[1].x, a[0].y - a[1].y) || 1, el: g.el };
      e.stopImmediatePropagation(); return;
    }
    if (pinch || G.size >= 2) { e.stopImmediatePropagation(); return; }
    const g = { el, x, y, x0: x, y0: y, right: S.right, own };
    G.set(e.pointerId, g);
    if (g.right) {               /* a right-button press, then the right-click mode lets go */
      e.stopImmediatePropagation();
      send(el, "pointerdown", ME("pointerdown", e, x, y, 2, 2, { pointerId: e.pointerId, pointerType: "mouse", isPrimary: true }), true);
      send(el, "mousedown", ME("mousedown", e, x, y, 2, 2));
      send(el, "contextmenu", ME("contextmenu", e, x, y, 2, 2));
      return;
    }
    if (!own) send(el, "mousedown", ME("mousedown", e, x, y, 0, 1));
  }, { capture: true, passive: false });
  addEventListener("pointermove", e => {
    if (e.pointerType !== "touch" || !e.isTrusted) return;
    const g = G.get(e.pointerId); if (!g) return;
    g.x = e.clientX; g.y = e.clientY;
    if (pinch) {
      e.stopImmediatePropagation();
      const a = [...G.values()]; if (a.length < 2) return;
      const d = Math.hypot(a[0].x - a[1].x, a[0].y - a[1].y), mx = (a[0].x + a[1].x) / 2, my = (a[0].y + a[1].y) / 2;
      const k = d / pinch.d;
      if (k > 1.09 || k < 1 / 1.09) { pinch.d = d;
        send(pinch.el, "wheel", { bubbles: true, cancelable: true, composed: true, clientX: mx, clientY: my, deltaY: k > 1 ? -100 : 100, deltaMode: 0, ctrlKey: true }); }
      return;
    }
    if (g.right) { e.stopImmediatePropagation();
      send(g.el, "pointermove", ME("pointermove", e, g.x, g.y, -1, 2, { pointerId: e.pointerId, pointerType: "mouse", isPrimary: true }), true);
      send(g.el, "mousemove", ME("mousemove", e, g.x, g.y, 0, 2)); return; }
    if (!g.own) send(g.el, "mousemove", ME("mousemove", e, g.x, g.y, 0, 1));
  }, { capture: true, passive: false });
  function up(e) {
    if (e.pointerType !== "touch" || !e.isTrusted) return;
    const g = G.get(e.pointerId); if (!g) return;
    G.delete(e.pointerId);
    if (g.pinch || pinch) { e.stopImmediatePropagation(); if (!G.size) pinch = null; return; }
    const x = e.clientX, y = e.clientY;
    if (g.right) { e.stopImmediatePropagation();
      send(g.el, "pointerup", ME("pointerup", e, x, y, 2, 0, { pointerId: e.pointerId, pointerType: "mouse", isPrimary: true }), true);
      send(g.el, "mouseup", ME("mouseup", e, x, y, 2, 0));
      S.right = false; const b = bar && bar.querySelector('[data-k="right"]'); if (b) b.setAttribute("aria-pressed", "false");
      return; }
    if (g.own) return;
    send(g.el, "mouseup", ME("mouseup", e, x, y, 0, 0));
    if (e.type === "pointerup" && Math.hypot(x - g.x0, y - g.y0) < 10) {   /* a tap; two taps close together are a double click */
      const now = performance.now();
      if (lastTap && now - lastTap.t < 350 && lastTap.el === g.el && Math.hypot(x - lastTap.x, y - lastTap.y) < 24) {
        send(g.el, "dblclick", ME("dblclick", e, x, y, 0, 0, { detail: 2 })); lastTap = null; sentDbl = performance.now(); }
      else lastTap = { t: now, el: g.el, x, y };
    }
  }
  addEventListener("pointerup", up, { capture: true, passive: false });
  addEventListener("pointercancel", up, { capture: true, passive: false });
  /* the browser's own double click from a double tap would come twice */
  addEventListener("dblclick", e => { if (e.isTrusted && performance.now() - sentDbl < 600 && e.target && e.target.tagName === "CANVAS") e.stopImmediatePropagation(); }, true);
  window.HLtouch = { enable, state: S };
})();
