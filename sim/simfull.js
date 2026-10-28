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
