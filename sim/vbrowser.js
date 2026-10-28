/* ==========================================================================
   HaslaLab — a web browser inside the simulated laptops, tablets and phones
   --------------------------------------------------------------------------
   VBrowser({kind, mobile, lang, online, links, onchange}) builds Microsoft
   Edge (kind "edge") or Google Chrome (kind "chrome"), desktop or mobile.
   The toolbar, the new-tab page, the offline page and the menu are drawn
   here; real pages load in an iframe.  Edge searches with Bing and Chrome
   with Google, as they do out of the box.  A site that forbids being shown
   inside another page stays blank: the info bar offers to open it in the
   real browser.  Pages of this site (the problem sheets) open directly.

   The host puts .el where the browser window's client area is: inside a
   window element (HTML desktops) or, over a canvas desktop, with
   place(x, y, w, h, visible, scale) in page coordinates.  With a scale the
   browser lays its pages out at the device's own resolution and is shrunk
   onto the screen, as a virtual machine's display is.

   YouTube: the home feed starts from the hand-picked library below and then
   leans towards what this viewer has watched (kept in this browser only).
   Searches go to the real YouTube through the HaslaLab server (YouTube Data
   API v3); without it they search the library.  Videos play in YouTube's own
   embedded player (IFrame Player API), and one that may not be embedded
   says so and offers YouTube itself.
   ========================================================================== */
(function () {
  const CSS = `
.vb{position:absolute;display:flex;flex-direction:column;background:#fff;color:#1b1b1b;font:13px "Segoe UI Variable Text","Segoe UI","Malgun Gothic","Apple SD Gothic Neo",Roboto,Arial,sans-serif;overflow:hidden;z-index:40;box-sizing:border-box}
.vb *{box-sizing:border-box}
.vb.emb{position:relative;width:100%;height:100%}
.vb-bar{flex:none;display:flex;align-items:center;gap:2px;padding:4px 6px;height:40px;background:#f7f7f7;border-bottom:1px solid #e2e2e2}
.vb.vb-chrome .vb-bar{background:#fff;border-bottom:1px solid #dadce0}
.vb-b{flex:none;width:32px;height:32px;border:0;border-radius:4px;background:none;color:#1b1b1b;font-size:16px;line-height:32px;text-align:center;cursor:pointer;padding:0;margin:0}
.vb-chrome .vb-b{border-radius:50%}
.vb-b:hover{background:rgba(0,0,0,.07)} .vb-b:disabled{color:#b5b5b5;background:none;cursor:default}
.vb-addr{flex:1;min-width:0;display:flex;align-items:center;height:30px;margin:0 6px;padding:0 10px;border-radius:4px;background:#fff;border:1px solid #d6d6d6}
.vb-chrome .vb-addr{border:0;background:#f1f3f4;border-radius:15px}
.vb-addr:focus-within{border-color:#0067c0;box-shadow:0 0 0 1px #0067c0;background:#fff}
.vb-chrome .vb-addr:focus-within{box-shadow:0 0 0 2px #1a73e8}
.vb-addr .ic{flex:none;margin-right:8px;color:#5f6368;font-size:12px}
.vb-addr input{flex:1;min-width:0;border:0;outline:0;background:none;font:inherit;color:#1b1b1b;padding:0;margin:0;height:28px}
.vb-body{flex:1;position:relative;min-height:0;background:#fff}
.vb-frame{position:absolute;left:0;top:0;width:100%;height:100%;border:0;background:#fff;transform-origin:0 0}
.vb-page{position:absolute;inset:0;overflow:auto}
.vb-info{position:absolute;left:0;right:0;bottom:0;display:flex;align-items:center;gap:10px;padding:6px 10px;background:#fff8d6;border-top:1px solid #e9d98a;font-size:12px;color:#3a3a3a}
.vb-info span{flex:1;min-width:0}
.vb-info button{margin:0;padding:3px 10px;border:1px solid #c9b45a;background:#fff;border-radius:4px;font:inherit;cursor:pointer;color:#1b1b1b;width:auto}
.vb-info .x{border:0;background:none;padding:0 4px}
.vb-menu{position:absolute;right:6px;top:38px;min-width:230px;background:#fff;border:1px solid #d8d8d8;border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,.18);padding:4px;z-index:5}
.vb-menu div{padding:8px 12px;border-radius:4px;cursor:pointer;display:flex;justify-content:space-between;gap:16px}
.vb-menu div:hover{background:#f0f0f0} .vb-menu i{font-style:normal;color:#6b6b6b}
.vb-menu hr{border:0;border-top:1px solid #e5e5e5;margin:4px 0}
.vb-ntp{min-height:100%;display:flex;flex-direction:column;align-items:center;padding:9% 16px 24px}
.vb-edge .vb-ntp{background:linear-gradient(160deg,#dbeafa 0%,#f3f7fc 45%,#e8f0f9 100%)}
.vb-logo{font:600 46px "Segoe UI",Arial,sans-serif;letter-spacing:-1px;margin-bottom:22px;user-select:none}
.vb-edge .vb-logo{color:#174ea6;font-weight:600}
.vb-logo b{font-weight:500}
.vb-q{width:min(580px,92%);display:flex;align-items:center;height:46px;border-radius:24px;background:#fff;border:1px solid #dfe1e5;padding:0 18px;box-shadow:0 1px 6px rgba(32,33,36,.12)}
.vb-edge .vb-q{border-radius:8px;border-color:#c8d3df}
.vb-q input{flex:1;border:0;outline:0;font:inherit;font-size:15px;background:none;color:#1b1b1b;margin:0;padding:0;height:40px}
.vb-tiles{display:flex;flex-wrap:wrap;justify-content:center;gap:10px;margin-top:30px;max-width:620px}
.vb-tile{width:108px;padding:12px 6px;border-radius:8px;text-align:center;cursor:pointer;color:#1b1b1b;font-size:12px;line-height:1.3}
.vb-tile:hover{background:rgba(0,0,0,.06)}
.vb-tile .c{width:48px;height:48px;margin:0 auto 8px;border-radius:50%;background:#e8eaed;display:flex;align-items:center;justify-content:center;font:600 20px Arial;color:#3c4043}
.vb-edge .vb-tile .c{border-radius:10px;background:#fff;box-shadow:0 1px 4px rgba(0,0,0,.14)}
.vb-off{max-width:600px;margin:0 auto;padding:12% 28px 30px;color:#3c4043;font-size:14px;line-height:1.6}
.vb-off h1{font:400 24px "Segoe UI",Roboto,Arial,sans-serif;color:#202124;margin:18px 0 12px}
.vb-off ul{margin:8px 0;padding-left:20px} .vb-off code{font-size:12px;color:#5f6368}
.vb.vb-mob .vb-bar{height:52px;padding:6px 8px;background:#fff;border-bottom:1px solid #e3e3e3}
.vb.vb-mob .vb-addr{height:38px;border-radius:19px}
.vb-mob .vb-tabs{flex:none;width:22px;height:22px;border:2px solid #3c4043;border-radius:4px;font:700 11px Arial;display:flex;align-items:center;justify-content:center;margin:0 8px;color:#3c4043}
.vb-mob .vb-ntp{padding-top:14%}
.vb-mob .vb-logo{font-size:40px}
.vb-mob .vb-tile{width:76px}`;
  let styled = false;
  function inject() { if (styled) return; styled = true; const s = document.createElement("style"); s.textContent = CSS + YTCSS; document.head.appendChild(s); }

  const TXT = {
    ko: {newTab: "새 탭", search: (k) => k === "edge" ? "웹 검색" : "Google 검색 또는 URL 입력", addr: (k) => k === "edge" ? "검색 또는 웹 주소 입력" : "Google 검색 또는 URL 입력",
      menuNew: "새 탭", zoomIn: "확대", zoomOut: "축소", zoomR: "원래 크기", real: "실제 브라우저에서 열기", reload: "새로 고침",
      info: "내용이 나오지 않으면 이 사이트가 다른 화면 안에 표시되는 것을 막아 둔 것입니다.",
      offT: (k) => k === "edge" ? "인터넷에 연결되어 있지 않습니다." : "인터넷에 연결되어 있지 않음",
      offL: ["네트워크 케이블, 모뎀, 라우터 확인", "Wi-Fi에 다시 연결", "Windows 네트워크 진단 실행"], offH: "다음 방법을 시도해 보세요.",
      results: (q) => q + " - 검색", sheet: "문제지"},
    en: {newTab: "New tab", search: (k) => k === "edge" ? "Search the web" : "Search Google or type a URL", addr: (k) => k === "edge" ? "Search or enter web address" : "Search Google or type a URL",
      menuNew: "New tab", zoomIn: "Zoom in", zoomOut: "Zoom out", zoomR: "Reset zoom", real: "Open in your real browser", reload: "Reload",
      info: "If nothing shows, this site does not allow being shown inside another page.",
      offT: (k) => k === "edge" ? "You're not connected." : "No internet",
      offL: ["Checking the network cables, modem, and router", "Reconnecting to Wi-Fi", "Running Windows Network Diagnostics"], offH: "Try:",
      results: (q) => q + " - Search", sheet: "Problem sheet"}};

  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
  const DINO = '<svg width="44" height="47" viewBox="0 0 44 47" shape-rendering="crispEdges"><path fill="#535353" d="M22 0h20v3h2v14h-10v3h8v3h-11v4h4v5h-4v3h-3v3h-3v5h3v3h-6v-8h-3v3h-3v2h3v3h-6v-9h-3v-3h-3v-3h-3v-3H0v-11h3v6h3v3h3v-3h3v-3h3v-3h3v-3h4z"/><path fill="#fff" d="M25 3h3v3h-3z"/></svg>';

  /* ---- the real app logos (Wikimedia Commons, public domain) and YouTube ----------------------
     ICONS are data URIs so a sim opened from disk shows them too.  YouTube cannot be framed, so it is
     drawn here: home, search and watch pages over a library of real videos (titles, channels, lengths
     and view counts as YouTube listed them), each played through YouTube's own embedded player. */
  const ICONS={"chrome": "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHhtbG5zOnhsaW5rPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5L3hsaW5rIiB2aWV3Qm94PSIwIDAgNDggNDgiIGhlaWdodD0iNDgiIHdpZHRoPSI0OCI+PGRlZnM+PGxpbmVhckdyYWRpZW50IGlkPSJhIiB4MT0iMy4yMTczIiB5MT0iMTUiIHgyPSI0NC43ODEyIiB5Mj0iMTUiIGdyYWRpZW50VW5pdHM9InVzZXJTcGFjZU9uVXNlIj48c3RvcCBvZmZzZXQ9IjAiIHN0b3AtY29sb3I9IiNkOTMwMjUiLz48c3RvcCBvZmZzZXQ9IjEiIHN0b3AtY29sb3I9IiNlYTQzMzUiLz48L2xpbmVhckdyYWRpZW50PjxsaW5lYXJHcmFkaWVudCBpZD0iYiIgeDE9IjIwLjcyMTkiIHkxPSI0Ny42NzkxIiB4Mj0iNDEuNTAzOSIgeTI9IjExLjY4MzciIGdyYWRpZW50VW5pdHM9InVzZXJTcGFjZU9uVXNlIj48c3RvcCBvZmZzZXQ9IjAiIHN0b3AtY29sb3I9IiNmY2M5MzQiLz48c3RvcCBvZmZzZXQ9IjEiIHN0b3AtY29sb3I9IiNmYmJjMDQiLz48L2xpbmVhckdyYWRpZW50PjxsaW5lYXJHcmFkaWVudCBpZD0iYyIgeDE9IjI2LjU5ODEiIHkxPSI0Ni41MDE1IiB4Mj0iNS44MTYxIiB5Mj0iMTAuNTA2IiBncmFkaWVudFVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHN0b3Agb2Zmc2V0PSIwIiBzdG9wLWNvbG9yPSIjMWU4ZTNlIi8+PHN0b3Agb2Zmc2V0PSIxIiBzdG9wLWNvbG9yPSIjMzRhODUzIi8+PC9saW5lYXJHcmFkaWVudD48L2RlZnM+PGNpcmNsZSBjeD0iMjQiIGN5PSIyMy45OTQ3IiByPSIxMiIgc3R5bGU9ImZpbGw6I2ZmZiIvPjxwYXRoIGQ9Ik0zLjIxNTQsMzZBMjQsMjQsMCwxLDAsMTIsMy4yMTU0LDI0LDI0LDAsMCwwLDMuMjE1NCwzNlpNMzQuMzkyMywxOEExMiwxMiwwLDEsMSwxOCwxMy42MDc3LDEyLDEyLDAsMCwxLDM0LjM5MjMsMThaIiBzdHlsZT0iZmlsbDpub25lIi8+PHBhdGggZD0iTTI0LDEySDQ0Ljc4MTJhMjMuOTkzOSwyMy45OTM5LDAsMCwwLTQxLjU2MzkuMDAyOUwxMy42MDc5LDMwbC4wMDkzLS4wMDI0QTExLjk4NTIsMTEuOTg1MiwwLDAsMSwyNCwxMloiIHN0eWxlPSJmaWxsOnVybCgjYSkiLz48Y2lyY2xlIGN4PSIyNCIgY3k9IjI0IiByPSI5LjUiIHN0eWxlPSJmaWxsOiMxYTczZTgiLz48cGF0aCBkPSJNMzQuMzkxMywzMC4wMDI5LDI0LjAwMDcsNDhBMjMuOTk0LDIzLjk5NCwwLDAsMCw0NC43OCwxMi4wMDMxSDIzLjk5ODlsLS4wMDI1LjAwOTNBMTEuOTg1LDExLjk4NSwwLDAsMSwzNC4zOTEzLDMwLjAwMjlaIiBzdHlsZT0iZmlsbDp1cmwoI2IpIi8+PHBhdGggZD0iTTEzLjYwODYsMzAuMDAzMSwzLjIxOCwxMi4wMDZBMjMuOTk0LDIzLjk5NCwwLDAsMCwyNC4wMDI1LDQ4TDM0LjM5MzEsMzAuMDAyOWwtLjAwNjctLjAwNjhhMTEuOTg1MiwxMS45ODUyLDAsMCwxLTIwLjc3NzguMDA3WiIgc3R5bGU9ImZpbGw6dXJsKCNjKSIvPjwvc3ZnPg==", "edge": "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNTYgMjU2Ij48ZGVmcz48cmFkaWFsR3JhZGllbnQgaWQ9ImIiIGN4PSIxNjEuOCIgY3k9IjY4LjkiIHI9Ijk1LjQiIGdyYWRpZW50VHJhbnNmb3JtPSJtYXRyaXgoMSAwIDAgLS45NSAwIDI0OC44KSIgZ3JhZGllbnRVbml0cz0idXNlclNwYWNlT25Vc2UiPjxzdG9wIG9mZnNldD0iLjciIHN0b3Atb3BhY2l0eT0iMCIvPjxzdG9wIG9mZnNldD0iLjkiIHN0b3Atb3BhY2l0eT0iLjUiLz48c3RvcCBvZmZzZXQ9IjEiLz48L3JhZGlhbEdyYWRpZW50PjxyYWRpYWxHcmFkaWVudCBpZD0iZCIgY3g9Ii0zNDAuMyIgY3k9IjYzIiByPSIxNDMuMiIgZ3JhZGllbnRUcmFuc2Zvcm09Im1hdHJpeCguMTUgLS45OSAtLjggLS4xMiAxNzYuNiAtMTI1LjQpIiBncmFkaWVudFVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHN0b3Agb2Zmc2V0PSIuOCIgc3RvcC1vcGFjaXR5PSIwIi8+PHN0b3Agb2Zmc2V0PSIuOSIgc3RvcC1vcGFjaXR5PSIuNSIvPjxzdG9wIG9mZnNldD0iMSIvPjwvcmFkaWFsR3JhZGllbnQ+PHJhZGlhbEdyYWRpZW50IGlkPSJlIiBjeD0iMTEzLjQiIGN5PSI1NzAuMiIgcj0iMjAyLjQiIGdyYWRpZW50VHJhbnNmb3JtPSJtYXRyaXgoLS4wNCAxIDIuMTMgLjA4IC0xMTc5LjUgLTEwNi43KSIgZ3JhZGllbnRVbml0cz0idXNlclNwYWNlT25Vc2UiPjxzdG9wIG9mZnNldD0iMCIgc3RvcC1jb2xvcj0iIzM1YzFmMSIvPjxzdG9wIG9mZnNldD0iLjEiIHN0b3AtY29sb3I9IiMzNGMxZWQiLz48c3RvcCBvZmZzZXQ9Ii4yIiBzdG9wLWNvbG9yPSIjMmZjMmRmIi8+PHN0b3Agb2Zmc2V0PSIuMyIgc3RvcC1jb2xvcj0iIzJiYzNkMiIvPjxzdG9wIG9mZnNldD0iLjciIHN0b3AtY29sb3I9IiMzNmM3NTIiLz48L3JhZGlhbEdyYWRpZW50PjxyYWRpYWxHcmFkaWVudCBpZD0iZiIgY3g9IjM3Ni41IiBjeT0iNTY4IiByPSI5Ny4zIiBncmFkaWVudFRyYW5zZm9ybT0ibWF0cml4KC4yOCAuOTYgLjc4IC0uMjMgLTMwMy44IC0xNDguNSkiIGdyYWRpZW50VW5pdHM9InVzZXJTcGFjZU9uVXNlIj48c3RvcCBvZmZzZXQ9IjAiIHN0b3AtY29sb3I9IiM2NmViNmUiLz48c3RvcCBvZmZzZXQ9IjEiIHN0b3AtY29sb3I9IiM2NmViNmUiIHN0b3Atb3BhY2l0eT0iMCIvPjwvcmFkaWFsR3JhZGllbnQ+PGxpbmVhckdyYWRpZW50IGlkPSJhIiB4MT0iNjMuMyIgeTE9Ijg0IiB4Mj0iMjQxLjciIHkyPSI4NCIgZ3JhZGllbnRUcmFuc2Zvcm09Im1hdHJpeCgxIDAgMCAtMSAwIDI2NikiIGdyYWRpZW50VW5pdHM9InVzZXJTcGFjZU9uVXNlIj48c3RvcCBvZmZzZXQ9IjAiIHN0b3AtY29sb3I9IiMwYzU5YTQiLz48c3RvcCBvZmZzZXQ9IjEiIHN0b3AtY29sb3I9IiMxMTRhOGIiLz48L2xpbmVhckdyYWRpZW50PjxsaW5lYXJHcmFkaWVudCBpZD0iYyIgeDE9IjE1Ny4zIiB5MT0iMTYxLjQiIHgyPSI0NiIgeTI9IjQwLjEiIGdyYWRpZW50VHJhbnNmb3JtPSJtYXRyaXgoMSAwIDAgLTEgMCAyNjYpIiBncmFkaWVudFVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHN0b3Agb2Zmc2V0PSIwIiBzdG9wLWNvbG9yPSIjMWI5ZGUyIi8+PHN0b3Agb2Zmc2V0PSIuMiIgc3RvcC1jb2xvcj0iIzE1OTVkZiIvPjxzdG9wIG9mZnNldD0iLjciIHN0b3AtY29sb3I9IiMwNjgwZDciLz48c3RvcCBvZmZzZXQ9IjEiIHN0b3AtY29sb3I9IiMwMDc4ZDQiLz48L2xpbmVhckdyYWRpZW50PjwvZGVmcz48cGF0aCBkPSJNMjM1LjcgMTk1LjVhOTMuNyA5My43IDAgMCAxLTEwLjYgNC43IDEwMS45IDEwMS45IDAgMCAxLTM1LjkgNi40Yy00Ny4zIDAtODguNS0zMi41LTg4LjUtNzQuM2EzMS41IDMxLjUgMCAwIDEgMTYuNC0yNy4zYy00Mi44IDEuOC01My44IDQ2LjQtNTMuOCA3Mi41IDAgNzQgNjguMSA4MS40IDgyLjggODEuNCA3LjkgMCAxOS44LTIuMyAyNy00LjZsMS4zLS40YTEyOC4zIDEyOC4zIDAgMCAwIDY2LjYtNTIuOCA0IDQgMCAwIDAtNS4zLTUuNloiIHRyYW5zZm9ybT0idHJhbnNsYXRlKC00LjYgLTUpIiBzdHlsZT0iZmlsbDp1cmwoI2EpIi8+PHBhdGggZD0iTTIzNS43IDE5NS41YTkzLjcgOTMuNyAwIDAgMS0xMC42IDQuNyAxMDEuOSAxMDEuOSAwIDAgMS0zNS45IDYuNGMtNDcuMyAwLTg4LjUtMzIuNS04OC41LTc0LjNhMzEuNSAzMS41IDAgMCAxIDE2LjQtMjcuM2MtNDIuOCAxLjgtNTMuOCA0Ni40LTUzLjggNzIuNSAwIDc0IDY4LjEgODEuNCA4Mi44IDgxLjQgNy45IDAgMTkuOC0yLjMgMjctNC42bDEuMy0uNGExMjguMyAxMjguMyAwIDAgMCA2Ni42LTUyLjggNCA0IDAgMCAwLTUuMy01LjZaIiB0cmFuc2Zvcm09InRyYW5zbGF0ZSgtNC42IC01KSIgc3R5bGU9Imlzb2xhdGlvbjppc29sYXRlO29wYWNpdHk6LjM1O2ZpbGw6dXJsKCNiKSIvPjxwYXRoIGQ9Ik0xMTAuMyAyNDYuM0E3OS4yIDc5LjIgMCAwIDEgODcuNiAyMjVhODAuNyA4MC43IDAgMCAxIDI5LjUtMTIwYzMuMi0xLjUgOC41LTQuMSAxNS42LTRhMzIuNCAzMi40IDAgMCAxIDI1LjcgMTMgMzEuOSAzMS45IDAgMCAxIDYuMyAxOC43YzAtLjIgMjQuNS03OS42LTgwLTc5LjYtNDMuOSAwLTgwIDQxLjYtODAgNzguMmExMzAuMiAxMzAuMiAwIDAgMCAxMi4xIDU2IDEyOCAxMjggMCAwIDAgMTU2LjQgNjcgNzUuNSA3NS41IDAgMCAxLTYyLjgtOFoiIHRyYW5zZm9ybT0idHJhbnNsYXRlKC00LjYgLTUpIiBzdHlsZT0iZmlsbDp1cmwoI2MpIi8+PHBhdGggZD0iTTExMC4zIDI0Ni4zQTc5LjIgNzkuMiAwIDAgMSA4Ny42IDIyNWE4MC43IDgwLjcgMCAwIDEgMjkuNS0xMjBjMy4yLTEuNSA4LjUtNC4xIDE1LjYtNGEzMi40IDMyLjQgMCAwIDEgMjUuNyAxMyAzMS45IDMxLjkgMCAwIDEgNi4zIDE4LjdjMC0uMiAyNC41LTc5LjYtODAtNzkuNi00My45IDAtODAgNDEuNi04MCA3OC4yYTEzMC4yIDEzMC4yIDAgMCAwIDEyLjEgNTYgMTI4IDEyOCAwIDAgMCAxNTYuNCA2NyA3NS41IDc1LjUgMCAwIDEtNjIuOC04WiIgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoLTQuNiAtNSkiIHN0eWxlPSJvcGFjaXR5Oi40MTtmaWxsOnVybCgjZCk7aXNvbGF0aW9uOmlzb2xhdGUiLz48cGF0aCBkPSJNMTU3IDE1My44Yy0uOSAxLTMuNCAyLjUtMy40IDUuNiAwIDIuNiAxLjcgNS4yIDQuOCA3LjMgMTQuMyAxMCA0MS40IDguNiA0MS41IDguNmE1OS42IDU5LjYgMCAwIDAgMzAuMy04LjMgNjEuNCA2MS40IDAgMCAwIDMwLjQtNTIuOWMuMy0yMi40LTgtMzcuMy0xMS4zLTQzLjlDMjI4IDI4LjggMTgyLjMgNSAxMzIuNiA1YTEyOCAxMjggMCAwIDAtMTI4IDEyNi4yYy41LTM2LjUgMzYuOC02NiA4MC02NiAzLjUgMCAyMy41LjMgNDIgMTBhNzIuNiA3Mi42IDAgMCAxIDMwLjkgMjkuM2M2LjEgMTAuNiA3LjIgMjQuMSA3LjIgMjkuNXMtMi43IDEzLjMtNy44IDE5LjlaIiB0cmFuc2Zvcm09InRyYW5zbGF0ZSgtNC42IC01KSIgc3R5bGU9ImZpbGw6dXJsKCNlKSIvPjxwYXRoIGQ9Ik0xNTcgMTUzLjhjLS45IDEtMy40IDIuNS0zLjQgNS42IDAgMi42IDEuNyA1LjIgNC44IDcuMyAxNC4zIDEwIDQxLjQgOC42IDQxLjUgOC42YTU5LjYgNTkuNiAwIDAgMCAzMC4zLTguMyA2MS40IDYxLjQgMCAwIDAgMzAuNC01Mi45Yy4zLTIyLjQtOC0zNy4zLTExLjMtNDMuOUMyMjggMjguOCAxODIuMyA1IDEzMi42IDVhMTI4IDEyOCAwIDAgMC0xMjggMTI2LjJjLjUtMzYuNSAzNi44LTY2IDgwLTY2IDMuNSAwIDIzLjUuMyA0MiAxMGE3Mi42IDcyLjYgMCAwIDEgMzAuOSAyOS4zYzYuMSAxMC42IDcuMiAyNC4xIDcuMiAyOS41cy0yLjcgMTMuMy03LjggMTkuOVoiIHRyYW5zZm9ybT0idHJhbnNsYXRlKC00LjYgLTUpIiBzdHlsZT0iZmlsbDp1cmwoI2YpIi8+PC9zdmc+Cg==", "youtube": "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIGNsYXNzPSJleHRlcm5hbC1pY29uIiB2aWV3Qm94PSIwIDAgMjguNTcgIDIwIiBmb2N1c2FibGU9ImZhbHNlIiBzdHlsZT0icG9pbnRlci1ldmVudHM6IG5vbmU7IGRpc3BsYXk6IGJsb2NrOyB3aWR0aDogMTAwJTsgaGVpZ2h0OiAxMDAlOyI+DQogIDxzdmcgdmlld0JveD0iMCAwIDI4LjU3IDIwIiBwcmVzZXJ2ZUFzcGVjdFJhdGlvPSJ4TWlkWU1pZCBtZWV0IiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPg0KICAgIDxnPg0KICAgICAgPHBhdGggZD0iTTI3Ljk3MjcgMy4xMjMyNEMyNy42NDM1IDEuODkzMjMgMjYuNjc2OCAwLjkyNjYyMyAyNS40NDY4IDAuNTk3MzY2QzIzLjIxOTcgMi4yNDI4OGUtMDcgMTQuMjg1IDAgMTQuMjg1IDBDMTQuMjg1IDAgNS4zNTA0MiAyLjI0Mjg4ZS0wNyAzLjEyMzIzIDAuNTk3MzY2QzEuODkzMjMgMC45MjY2MjMgMC45MjY2MjMgMS44OTMyMyAwLjU5NzM2NiAzLjEyMzI0QzIuMjQyODhlLTA3IDUuMzUwNDIgMCAxMCAwIDEwQzAgMTAgMi4yNDI4OGUtMDcgMTQuNjQ5NiAwLjU5NzM2NiAxNi44NzY4QzAuOTI2NjIzIDE4LjEwNjggMS44OTMyMyAxOS4wNzM0IDMuMTIzMjMgMTkuNDAyNkM1LjM1MDQyIDIwIDE0LjI4NSAyMCAxNC4yODUgMjBDMTQuMjg1IDIwIDIzLjIxOTcgMjAgMjUuNDQ2OCAxOS40MDI2QzI2LjY3NjggMTkuMDczNCAyNy42NDM1IDE4LjEwNjggMjcuOTcyNyAxNi44NzY4QzI4LjU3MDEgMTQuNjQ5NiAyOC41NzAxIDEwIDI4LjU3MDEgMTBDMjguNTcwMSAxMCAyOC41Njc3IDUuMzUwNDIgMjcuOTcyNyAzLjEyMzI0WiIgZmlsbD0iI0ZGMDAwMCI+PC9wYXRoPg0KICAgICAgPHBhdGggZD0iTTExLjQyNTMgMTQuMjg1NEwxOC44NDc3IDEwLjAwMDRMMTEuNDI1MyA1LjcxNTMzVjE0LjI4NTRaIiBmaWxsPSJ3aGl0ZSI+PC9wYXRoPg0KICAgIDwvZz4NCiAgPC9zdmc+DQo8L3N2Zz4=", "windows": "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA0ODc1IDQ4NzUiPjxwYXRoIGZpbGw9IiMwMDc4ZDQiIGQ9Ik0wIDBoMjMxMXYyMzEwSDB6bTI1NjQgMGgyMzExdjIzMTBIMjU2NHpNMCAyNTY0aDIzMTF2MjMxMUgwem0yNTY0IDBoMjMxMXYyMzExSDI1NjQiLz48L3N2Zz4=", "samsung_internet": "data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz4KPCEtLSBHZW5lcmF0b3I6IEFkb2JlIElsbHVzdHJhdG9yIDIzLjAuMSwgU1ZHIEV4cG9ydCBQbHVnLUluIC4gU1ZHIFZlcnNpb246IDYuMDAgQnVpbGQgMCkgIC0tPgo8c3ZnIHZlcnNpb249IjEuMSIgaWQ9IkxpdmVsbG9fMSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB4bWxuczp4bGluaz0iaHR0cDovL3d3dy53My5vcmcvMTk5OS94bGluayIgeD0iMHB4IiB5PSIwcHgiCgkgdmlld0JveD0iMCAwIDQ5MyA0OTMiIGVuYWJsZS1iYWNrZ3JvdW5kPSJuZXcgMCAwIDQ5MyA0OTMiIHhtbDpzcGFjZT0icHJlc2VydmUiPgo8Zz4KCTxwYXRoIGZpbGw9IiM3ODgyRkYiIGQ9Ik00ODguNSwxNzNjLTYuMS00NS44LTIyLjMtODcuMy01MC44LTExNy43aDBDNDA3LjMsMjYuOCwzNjUuOCwxMC42LDMyMCw0LjVjLTQzLjctNS44LTczLjUtNC40LTczLjUtNC40CgkJUzIxNi43LTEuMywxNzMsNC41Yy00NS44LDYuMS04Ny4zLDIyLjMtMTE3LjYsNTAuOEMyNi44LDg1LjcsMTAuNiwxMjcuMiw0LjUsMTczYy01LjgsNDMuNy00LjQsNzMuNS00LjQsNzMuNXMtMS40LDI5LjgsNC40LDczLjUKCQljNi4xLDQ1LjgsMjIuMyw4Ny4zLDUwLjgsMTE3LjdjMzAuNCwyOC42LDcxLjksNDQuOCwxMTcuNiw1MC45YzQzLjcsNS44LDczLjUsNC40LDczLjUsNC40czI5LjgsMS40LDczLjUtNC40CgkJYzQ1LjgtNi4xLDg3LjMtMjIuMywxMTcuNi01MC45aDBjMjguNi0zMC40LDQ0LjgtNzEuOSw1MC44LTExNy43YzUuOC00My43LDQuNC03My41LDQuNC03My41UzQ5NC4zLDIxNi43LDQ4OC41LDE3MyIvPgoJPHBhdGggZmlsbD0iI0ZGRkZGRiIgZD0iTTM3Mi43LDIxMGMxOS41LDcwLTIxLjUsMTQyLjYtOTEuNSwxNjIuMWMtNzAsMTkuNS0xNDIuNi0yMS41LTE2Mi4xLTkxLjVjLTE5LjUtNzAsMjEuNS0xNDIuNiw5MS41LTE2Mi4xCgkJQzI4MC42LDk5LDM1My4yLDE0MCwzNzIuNywyMTAiLz4KCTxwYXRoIGZpbGw9IiNGRkZGRkYiIGQ9Ik0zNzIuNywyMTBjNy4zLDI2LjMsNi4xLDUyLjktMS45LDc2LjljLTAuNiwxLjktMS4zLDMuOS0yLjEsNS44Ii8+Cgk8cGF0aCBmaWxsPSIjRkZGRkZGIiBkPSJNMzcwLjYsMjEwYzUuMSwxOC40LDYuMSwzNywzLjQsNTQuNyIvPgoJPHBhdGggZmlsbD0iIzRENUNDMSIgZD0iTTMzMy45LDMzNy43TDMzMy45LDMzNy43Yy0zMy4zLDAtNzMuOC04LjUtMTE0LjItMjMuOGMtNDAuNC0xNS4zLTc2LjMtMzUuOS0xMDEuMi01OAoJCWMtNDAuNC0zNS45LTM3LjktNjMuNy0zMi44LTc3LjFjNS4xLTEzLjQsMjEuNy0zNS45LDc1LjctMzUuOWgwYzMzLjMsMCw3My44LDguNSwxMTQuMiwyMy44YzQwLjQsMTUuMyw3Ni4zLDM1LjksMTAxLjIsNTgKCQljNDAuNCwzNS45LDM3LjksNjMuNywzMi44LDc3LjFDNDA0LjYsMzE1LjIsMzg4LDMzNy43LDMzMy45LDMzNy43IE0xNjEuNSwxODQuNmMtMjUsMC0zNS43LDYuMi0zNi44LDkKCQljLTEuMSwyLjgsMi45LDE0LjYsMjEuNiwzMS4yYzIwLjksMTguNSw1My4xLDM2LjksODguMyw1MC4yYzM1LjIsMTMuNCw3MS41LDIxLjEsOTkuNCwyMS4xaDBjMjUsMCwzNS43LTYuMiwzNi44LTkKCQljMS4xLTIuOC0yLjktMTQuNi0yMS41LTMxLjJjLTIwLjktMTguNS01My4xLTM2LjktODguMy01MC4yQzIyNS42LDE5Mi4zLDE4OS40LDE4NC42LDE2MS41LDE4NC42TDE2MS41LDE4NC42TDE2MS41LDE4NC42eiIvPgoJPHBhdGggZmlsbD0iI0ZGRkZGRiIgZD0iTTEyNC43LDE5NGwyNDUuOSw5My40YzguMi0yNC4yLDkuNS01MSwyLjEtNzcuNGMtMTkuNS03MC05Mi0xMTEtMTYyLjEtOTEuNQoJCUMxNzAuNCwxMjkuNywxMzkuOCwxNTguNCwxMjQuNywxOTQiLz4KPC9nPgo8L3N2Zz4K", "play": "data:image/svg+xml;base64,PHN2ZyB2aWV3Qm94PSIwIDAgMjguOTkgMzEuOTkiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGcgZGF0YS1uYW1lPSJDYXBhIDIiPjxnIGRhdGEtbmFtZT0iQ2FwYSAxIj48cGF0aCBkPSJNMTMuNTQgMTUuMjguMTIgMjkuMzRhMy42NiAzLjY2IDAgMCAwIDUuMzMgMi4xNmwxNS4xLTguNloiIHN0eWxlPSJmaWxsOiNlYTQzMzUiLz48cGF0aCBkPSJtMjcuMTEgMTIuODktNi41My0zLjc0LTcuMzUgNi40NSA3LjM4IDcuMjggNi40OC0zLjdhMy41NCAzLjU0IDAgMCAwIDEuNS00Ljc5IDMuNjIgMy42MiAwIDAgMC0xLjUtMS41eiIgc3R5bGU9ImZpbGw6I2ZiYmMwNCIvPjxwYXRoIGQ9Ik0uMTIgMi42NmEzLjU3IDMuNTcgMCAwIDAtLjEyLjkydjI0Ljg0YTMuNTcgMy41NyAwIDAgMCAuMTIuOTJMMTQgMTUuNjRaIiBzdHlsZT0iZmlsbDojNDI4NWY0Ii8+PHBhdGggZD0ibTEzLjY0IDE2IDYuOTQtNi44NUw1LjUuNTFBMy43MyAzLjczIDAgMCAwIDMuNjMgMCAzLjY0IDMuNjQgMCAwIDAgLjEyIDIuNjVaIiBzdHlsZT0iZmlsbDojMzRhODUzIi8+PC9nPjwvZz48L3N2Zz4="};
  const YT=[["k4vjvPo4JgE","이론·실험 5문제에 총 10시간이요?😲 국가대표들이 받은 물리 올림피아드 실제 문제 등장 ㄷㄷ | 유퀴즈온더블럭","tvN Joy","12:11","조회수 3,322회","2년 전","ko","olym"],["34-NtwmnZ4E","유럽 물리올림피아드 싹쓸이?! 과학고 자기님들과의 부끄러운(?) 토크 #유퀴즈온더블럭 | YOU QUIZ ON THE BLOCK EP.71","유 퀴즈 온 더 튜브","3:50","조회수 22,927회","6년 전","ko","olym"],["ND3vB8Y6ifY","[#유퀴즈온더블럭] 물리올림피아드 🥇금메달🥇을 싹쓸이한 대한민국 물리짱들 모셨습니다👍 문제는 다섯 개, 시험은 10시간?! 아기자기와 큰자기를 당황시킨 물리의 모든 것","디글 :Diggle","12:06","조회수 165,162회","3년 전","ko","olym"],["QR_5pL28EDg","제26회 아시아물리올림피아드 부산에서 개막 / YTN 사이언스","YTN 사이언스 투데이","0:46","조회수 208회","5개월 전","ko","olym"],["gUSbHVWbc9M","6분만에 배우는 오실로스코프 사용법","큐블","5:50","조회수 308,744회","12년 전","ko","scope"],["fNvbxzn8fSk","[한빛아카데미]오실로스코프 사용법","한빛아카데미","6:49","조회수 34,918회","5년 전","ko","scope"],["FlDmRzjwJQY","오실로스코프 사용법 및 주의 사항 : 오실로스코프의 잘못된 측정 예시와 AC 220V 전원/SMPS/드레인 파형 측정 시 올바른 방법","루드비크 전원회로 설계 연구소","10:35","조회수 50,899회","5년 전","ko","scope"],["SfMYQLmhIik","과제3 측정 - 오실로스코프 [전자기능사 실기]","전자기능사실기-electronic0303","12:00","조회수 12,608회","3년 전","ko","scope"],["vHGxIfHH3Qw","중등과학교육지원콘텐츠_지구과학_천체망원경 사용법","경상북도교육청과학원","8:25","조회수 19,666회","5년 전","ko","tele"],["9ZQTqIYHW1A","🔭천체망원경 처음 써보는 분들 필수 시청!","곽포유(충북과학문화거점센터)","15:01","조회수 10,505회","1년 전","ko","tele"],["-s1DPRxi8Wo","천체 망원경 사용법-파인더조절","아이테크","1:19","조회수 21,309회","13년 전","ko","tele"],["dqCAWWg6jkE","[천체장비1편] 경위대? 적도의? 그게 뭐지? ㅣ망원경 가대 요약 설명","코스믹 사이언스","1:49","조회수 7,321회","4년 전","ko","tele"],["2FN8d2fMcO4","표준 분동의 오차(Error)와 측정 불확도(Uncertainty)의 관계 이해하기","계측학개론 - 계량·계측 이야기","5:54","조회수 115회","3개월 전","ko","err"],["8Wp75YkMzLA","오차론 실험: 측정값 분석과 불확도 계산 방법","해피캠퍼스","0:53","조회수 110회","1년 전","ko","err"],["9bEaWINzqo4","1. 오차론","환타타","8:55","조회수 3,187회","9년 전","ko","err"],["8JIgbB4AtHM","별자리를 정말 쉽게 찾는 방법 5가지 [미드나잇]","미드나잇 천체관측 channel","7:23","조회수 29,555회","5년 전","ko","sky"],["bEcCIRk2RvI","봄철 별자리 찾는 꿀팁 총정리⭐","대구어린이천문대","3:06","조회수 156회","6개월 전","ko","sky"],["brhabNPr0KU","방향찾기 북극성 찾기","아이테크","1:19","조회수 109,645회","13년 전","ko","sky"],["dRc0JHcl6ms","봄철 별자리, 쉽게 찾아보자! l 쉽게 배우는 천문학 l 봄철 별자리 찾기","쉬운우주","5:41","조회수 2,166회","2년 전","ko","sky"],["jii87F-2JxY","7 Steps for Gold in a Physics Olympiad","ZPhysics","9:04","84,675 views","2y ago","en","olym"],["GlrreXLkzrk","Experimental problem for the 34th Latvian Open Physics Olympiad 2009","FizikasDraugiem","1:45","10,388 views","15y ago","en","olym"],["WaBYOVpQFhw","EuPhO 2022, Experimental exam","European Physics Olympiad Ljubljana Slovenia","2:40","839 views","4y ago","en","olym"],["zwPm8W2kr-4","EASIEST question on the International Physics Olympiad?","ZPhysics","3:06","17,670 views","4y ago","en","olym"],["6lhd04kKv_M","IPhO Problem | Detailed Solution Walkthrough","Physinov","10:44","471 views","8mo ago","en","olym"],["s4-N7qVtzuY","IPHO 2015 Video Complete RBK","Rajesh Khaparde","38:40","6,288 views","10y ago","en","olym"],["4T2IfC3VpTk","How I'd Solve a Physics Olympiad Problem","ZPhysics","9:25","8,281 views","2y ago","en","olym"],["gjT9021i7Kc","A Simple Problem on the Hardest Physics Olympiad (IPhO)","Overthinking Dude","18:38","462,164 views","6y ago","en","olym"],["lSHAE_Y6snc","Oscilloscope Tutorial (Basics 101)","TheGeekPub","7:37","821,221 views","7y ago","en","scope"],["LaY47Qrfs0c","How to ACTUALLY Use an Oscilloscope (Beginner-Friendly Guide!)","The Engineering Mindset","35:07","850,218 views","1y ago","en","scope"],["DgYGRtkd9Vs","What’s an OSCILLOSCOPE?","ElectroBOOM","11:49","1,888,463 views","6y ago","en","scope"],["6lrKFFEPJqI","Oscilloscope Basics for Beginners","Robonyx","8:31","99,149 views","1y ago","en","scope"],["Chi-ju6ityc","A Level Physics Revision: All of Uncertainties (in under 11 minutes!)","ZPhysics","11:10","292,944 views","5y ago","en","err"],["aHYKal3kcgM","Uncertainty and error - IB Physics","Dr. Brown","21:54","7,331 views","7y ago","en","err"],["IBRzTvoHbHY","Uncertainty - Addition and Subtraction","The Organic Chemistry Tutor","11:24","217,471 views","4y ago","en","err"],["GbnR6QsbE1M","Measurement Uncertainty - IB Physics","IB Physics - Andy Masley","4:20","98,812 views","7y ago","en","err"],["j-u3IEgcTiQ","Michelson Interferometer (P12) [6D40.10]","MIT Physics Instructional Resources Lab","4:07","543,526 views","14y ago","en","optics"],["lzBKlY4f1XA","Michelson Interferometer - Amrita University","Amrita Vlab","7:34","261,609 views","13y ago","en","optics"],["iDaaNKWqfUs","The Michelson Interferometer","K2 Optics","2:26","2,375 views","3y ago","en","optics"],["cilV-37oxS4","Michelson Interfereomter Alignment SAMPLE","Peter Beyersdorf","1:11","15,955 views","12y ago","en","optics"],["t1Ip2ta8NuU","How To Use a Beginner Telescope","LearnToStargaze","14:49","89,082 views","1y ago","en","tele"],["eQ3IP60Fj9c","How To Use Any Telescope: From Setup To Stargazing","LearnToStargaze","22:34","574,646 views","3y ago","en","tele"],["eoZyR7U8cuo","How To Actually Use That Damn Telescope!","Dean Hansen","15:14","640,064 views","8y ago","en","tele"],["I3DCyhLFPdA","Five best things to see with a beginner telescope","The Planetary Society","4:24","22,873 views","3y ago","en","tele"],["NyPsyzz1WPY","The Most Competitive Astronomy Exam","Tibees","9:23","54,557 views","3y ago","en","olym"],["hUuvObsjysg","IOAA 2016 T1 General Aspects of Astronomy","IOAA and IPhO Preparation","7:16","71 views","2mo ago","en","olym"],["gk-3v_ktX0c","NIGHT OBSERVATION - IOAA2019 - Hungary","Rafael Schmall","1:50","3,531 views","7y ago","en","olym"],["JZ9mxMXYpEo","IOAA 2026 Phenikaa University planetarium demo","IOAA","8:33","879 views","4w ago","en","olym"],["qNmlZzlgt5o","How to Read a Star Chart","Learn the Sky","14:31","57,745 views","2y ago","en","sky"],["XUbG8jboh4M","Getting oriented to better learn the night sky: Stargazing Basics 1 of 3","Eyes on the Sky","5:59","852,211 views","14y ago","en","sky"],["3qygnn7Zlkk","How to Use a Sky Chart","Sky & Telescope","3:19","60,855 views","4y ago","en","sky"],["IOlVtC-1q8I","Saturn through my Telescope","J.W.Astronomy","2:46","19,470,812 views","9y ago","en","sky"],["CvNvzxok8v8","Saturn through my Telescope | Zoom","Jupiter TV","1:05","8,951 views","1y ago","en","sky"],["HlWbiD9ftLo","Jupiter, Saturn & Uranus through my Telescope","Tom Williams","0:49","38,979 views","4y ago","en","sky"],["kkI65xo6vTI","What Planets Look Like Through a Super Telescope","D.A","8:27","976,113 views","1y ago","en","sky"],["1Ez9H0BQp0A","2016 Smartphone Optics Project: Light Source Smartphone Spectroscopy","UGA Modern Optics: Smartphone Projects","5:26","128 views","5y ago","en","optics"],["0954J_5NI88","Smartphone Spectroscopy - #ChemistryInYourCupboard","Royal Society of Chemistry","3:45","21,654 views","6y ago","en","optics"],["4-ZXXtv-ENA","Smartphone Spectrometer | Unboxing and installation of the Goyalab GoSpectro","Axiom Optics","1:28","1,146 views","3y ago","en","optics"],["0LjrPesqP4k","Smartphone Spectrometer | Calibration of the GoyaLab GoSpectro","Axiom Optics","1:02","3,140 views","3y ago","en","optics"],["bF3OyQ3HwfU","THE BEST Multimeter tutorial (HD)","Afrotechmods","4:36","6,180,958 views","16y ago","en","elec"],["0loXukB302Q","How to use a multimeter like a pro, the ultimate guide","Anthony Mendez ","12:55","6,272,454 views","2y ago","en","elec"],["TdUK6RPdIrA","How to Use a Multimeter for Beginners - How to Measure Voltage, Resistance, Continuity and Amps","Ratchets And Wrenches","8:08","8,655,755 views","10y ago","en","elec"],["4lAyzRxsbDc","How to use a multimeter like a pro! The Ultimate guide","The Engineering Mindset","28:43","3,549,320 views","3y ago","en","elec"],["XeFOzxozypY","Diffraction Grating Experiment - A Level Physics Practical","Physics Online","3:16","16,266 views","1y ago","en","optics"],["desLn3tMLcc","Diffraction Grating Experiment: measuring wavelength | A Level Physics","vt.physics","1:59","73,341 views","7y ago","en","optics"],["vt86k8yoe08","White light with a diffraction grating","Physics with Simon Poliakoff","1:12","16,592 views","5y ago","en","optics"],["RM7Ijt9q4_I","Diffraction Grating Experiment","Sachin Tanwade and Mridula Chandola","12:20","514,472 views","5y ago","en","optics"],["8JxyT0edT6c","How FOUCAULT PENDULUM Works and Proves Earth is a Round SPINNING Sphere","Stick Science","5:49","320,773 views","4y ago","en","mech"],["TRmnI1u1rPM","Amazing Foucault’s pendulum at Pantheon in Paris, France 🇫🇷","fredrikdrevon","0:55","8,319 views","3y ago","en","mech"],["_77eXLGBVNs","Foucault Pendulum, Science Museum of Valencia, Spain - August 3 2019","Henry Webb","0:42","12,187 views","6y ago","en","mech"]];
  const YT_CAT = {olym: ["물리 올림피아드", "Olympiads"], scope: ["오실로스코프", "Oscilloscopes"], err: ["측정 · 오차", "Uncertainty"], tele: ["천체망원경", "Telescopes"],
    sky: ["별자리 · 관측", "Night sky"], optics: ["광학 · 분광", "Optics"], elec: ["멀티미터", "Multimeters"], mech: ["역학", "Mechanics"]};
  const YTCSS = `
.vb .yt{min-height:100%;background:#fff;color:#0f0f0f;font-family:Roboto,Arial,"Malgun Gothic","Apple SD Gothic Neo",sans-serif}
.vb .yt-top{position:sticky;top:0;z-index:2;display:flex;align-items:center;gap:12px;padding:8px 16px;background:#fff}
.vb .yt-hb{border:0;background:none;font-size:18px;width:38px;height:38px;border-radius:50%;cursor:pointer;color:#0f0f0f}
.vb .yt-hb:hover{background:#f2f2f2}
.vb .yt-logo{display:flex;align-items:center;gap:3px;font:600 19px/1 "YouTube Sans",Roboto,Arial,sans-serif;letter-spacing:-.7px;cursor:pointer;color:#0f0f0f;white-space:nowrap}
.vb .yt-logo img{width:30px;height:21px}
.vb .yt-logo sup{font-size:9px;font-weight:400;color:#606060;margin-left:2px;align-self:flex-start;margin-top:2px}
.vb .yt-s{flex:1;max-width:620px;margin:0 auto;display:flex}
.vb .yt-s input{flex:1;min-width:0;height:38px;border:1px solid #d3d3d3;border-right:0;border-radius:20px 0 0 20px;padding:0 16px;font:15px Roboto,Arial,sans-serif;outline:none}
.vb .yt-s input:focus{border-color:#1c62b9;box-shadow:inset 0 1px 2px rgba(0,0,0,.2)}
.vb .yt-s button{width:62px;height:38px;border:1px solid #d3d3d3;border-radius:0 20px 20px 0;background:#f8f8f8;cursor:pointer;font-size:15px}
.vb .yt-av{width:32px;height:32px;border-radius:50%;background:#7b3fe4;color:#fff;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:600;flex:none}
.vb .yt-chips{display:flex;gap:10px;padding:8px 16px 12px;overflow-x:auto;scrollbar-width:none;position:sticky;top:54px;background:#fff;z-index:1}
.vb .yt-chips button{flex:none;border:0;border-radius:8px;padding:6px 12px;background:#f2f2f2;font:500 14px Roboto,Arial,sans-serif;cursor:pointer;color:#0f0f0f}
.vb .yt-chips button.on{background:#0f0f0f;color:#fff}
.vb .yt-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:28px 16px;padding:8px 16px 24px}
.vb .yt-card{cursor:pointer;display:block}
.vb .yt-th{position:relative;border-radius:12px;overflow:hidden;background:#e5e5e5;aspect-ratio:16/9}
.vb .yt-th img{width:100%;height:100%;object-fit:cover;display:block}
.vb .yt-th span{position:absolute;right:6px;bottom:6px;background:rgba(0,0,0,.8);color:#fff;font:500 12px Roboto,Arial,sans-serif;padding:1px 4px;border-radius:4px}
.vb .yt-meta{display:flex;gap:12px;margin-top:12px}
.vb .yt-ch{width:36px;height:36px;border-radius:50%;flex:none;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:600;font-size:15px}
.vb .yt-meta b{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font:500 16px/22px Roboto,Arial,sans-serif;margin-bottom:4px}
.vb .yt-meta i{display:block;font:400 14px/20px Roboto,Arial,sans-serif;color:#606060;font-style:normal}
.vb .yt-row{display:flex;flex-direction:column;gap:8px;padding:8px 16px 24px;max-width:1100px}
.vb .yt-row .yt-card{display:flex;gap:16px}
.vb .yt-row .yt-th{width:360px;flex:none}
.vb .yt-row .yt-meta{margin-top:0}
.vb .yt-row .yt-meta b{font-size:18px;line-height:26px}
.vb .yt-note{padding:4px 16px 10px;color:#606060;font-size:14px}
.vb .yt-watch{display:grid;grid-template-columns:minmax(0,1fr) 400px;gap:24px;padding:16px 24px}
.vb .yt-player{position:relative;aspect-ratio:16/9;background:#000;border-radius:12px;overflow:hidden}
.vb .yt-player iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
.vb .yt-wt{font:600 20px/28px Roboto,Arial,sans-serif;margin:12px 0 8px}
.vb .yt-own{display:flex;align-items:center;gap:12px}
.vb .yt-own b{font:500 16px Roboto,Arial,sans-serif;display:block}
.vb .yt-own i{font-style:normal;font-size:12px;color:#606060}
.vb .yt-sub{margin-left:8px;border:0;border-radius:18px;background:#0f0f0f;color:#fff;padding:0 16px;height:36px;font:500 14px Roboto,Arial,sans-serif;cursor:pointer}
.vb .yt-sub.on{background:#f2f2f2;color:#0f0f0f}
.vb .yt-acts{margin-left:auto;display:flex;gap:8px}
.vb .yt-acts button{border:0;border-radius:18px;background:#f2f2f2;padding:0 14px;height:36px;font:500 14px Roboto,Arial,sans-serif;cursor:pointer}
.vb .yt-acts button.on{background:#0f0f0f;color:#fff}
.vb .yt-desc{margin-top:12px;background:#f2f2f2;border-radius:12px;padding:12px;font-size:14px;line-height:20px}
.vb .yt-ext{color:#065fd4;text-decoration:none;font-weight:500}
.vb .yt-player iframe,.vb .yt-player>div{position:absolute;inset:0;width:100%;height:100%;border:0}
.vb .yt-err{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;padding:20px;text-align:center;color:#fff;background:#0f0f0f;font-size:15px}
.vb .yt-err .yt-ext{color:#3ea6ff}
.vb .yt-side .yt-card{display:flex;gap:8px;margin-bottom:8px}
.vb .yt-side .yt-th{width:168px;flex:none;border-radius:8px}
.vb .yt-side .yt-meta{margin:0}
.vb .yt-side .yt-meta b{font-size:14px;line-height:20px}
.vb .yt-side .yt-meta i{font-size:12px;line-height:18px}
.vb .yt-off{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;padding:18% 20px;text-align:center;color:#0f0f0f}
.vb .yt-off .ic{width:96px;height:96px;border-radius:50%;background:#f2f2f2;display:flex;align-items:center;justify-content:center;font-size:42px}
.vb .yt-off button{margin-top:8px;border:1px solid #d3d3d3;border-radius:18px;background:#fff;color:#065fd4;padding:8px 16px;font:500 14px Roboto,Arial,sans-serif;cursor:pointer}
.vb.vb-mob .yt-top{padding:6px 10px;gap:8px;flex-wrap:wrap}
.vb.vb-mob .yt-hb{display:none}
.vb.vb-mob .yt-s{order:3;flex-basis:100%;max-width:none}
.vb.vb-mob .yt-s input{height:34px}
.vb.vb-mob .yt-s button{height:34px;width:52px}
.vb.vb-mob .yt-av{margin-left:auto;width:28px;height:28px}
.vb.vb-mob .yt-chips{top:90px}
.vb.vb-mob .yt-grid{grid-template-columns:1fr;gap:20px;padding:4px 0 20px}
.vb.vb-mob .yt-grid .yt-th{border-radius:0}
.vb.vb-mob .yt-grid .yt-meta{padding:0 12px}
.vb.vb-mob .yt-row .yt-card{flex-direction:column}
.vb.vb-mob .yt-row .yt-th{width:100%}
.vb.vb-mob .yt-watch{grid-template-columns:1fr;padding:0;gap:12px}
.vb.vb-mob .yt-player{border-radius:0}
.vb.vb-mob .yt-info{padding:0 12px}
.vb.vb-mob .yt-acts{display:none}
.vb.vb-mob .yt-side{padding:0 12px}
@media(max-width:900px){.vb .yt-watch{grid-template-columns:1fr}.vb .yt-row .yt-th{width:240px}}
.vb-app .vb-bar{display:none}
.vb-samsung .vb-bar{background:#fff}
.vb-samsung .vb-logo{font:700 30px/1 "Samsung Sharp Sans",Arial,sans-serif;color:#5a62f2;display:flex;align-items:center;gap:10px}
`;
  const ytHue = (s) => { let h = 0; for (const ch of String(s)) h = (h * 31 + ch.codePointAt(0)) >>> 0; return h % 360; };
  function ytParse(u) {
    try { const x = new URL(u); if (!/(^|\.)youtube(-nocookie)?\.com$|^youtu\.be$/i.test(x.hostname)) return null;
      if (/^youtu\.be$/i.test(x.hostname)) return {t: "yt", v: x.pathname.slice(1)};
      if (x.pathname === "/watch") return {t: "yt", v: x.searchParams.get("v")};
      if (/^\/(embed|shorts)\//.test(x.pathname)) return {t: "yt", v: x.pathname.split("/")[2]};
      if (x.pathname === "/results") return {t: "yt", q: x.searchParams.get("search_query") || ""};
      return {t: "yt"}; } catch (e) { return null; } }
  const ytUrl = (c) => c.v ? "https://www.youtube.com/watch?v=" + c.v : c.q ? "https://www.youtube.com/results?search_query=" + encodeURIComponent(c.q).replace(/%20/g, "+") : "https://www.youtube.com/";
  /* videos met through a real search, in the library's row format */
  const META = new Map();
  const ytFind = (id) => YT.find((v) => v[0] === id) || META.get(id);
  YT_CAT.web = ["YouTube 검색", "From search"];
  const YT_API = () => (window.HL_COMMUNITY_API || "https://haslalab-community.haslalab.workers.dev") + "/api/yt/";
  const fmtViews = (n, k) => { n = +n || 0;
    if (k) return "조회수 " + (n >= 1e8 ? (n / 1e8).toFixed(n < 1e9 ? 1 : 0) + "억" : n >= 1e4 ? (n / 1e4).toFixed(n < 1e5 ? 1 : 0) + "만" : n >= 1e3 ? (n / 1e3).toFixed(1) + "천" : n) + "회";
    return (n >= 1e9 ? (n / 1e9).toFixed(1) + "B" : n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e3 ? (n / 1e3).toFixed(n < 1e4 ? 1 : 0) + "K" : n) + " views"; };
  const fmtAgo = (iso, k) => { const d = (Date.now() - Date.parse(iso)) / 864e5; if (!(d >= 0)) return "";
    const [n, u] = d < 1 ? [Math.max(1, Math.round(d * 24)), k ? "시간" : "hour"] : d < 30 ? [Math.round(d), k ? "일" : "day"] : d < 365 ? [Math.round(d / 30), k ? "개월" : "month"] : [Math.round(d / 365), k ? "년" : "year"];
    return k ? n + u + " 전" : n + " " + u + (n > 1 ? "s" : "") + " ago"; };
  /* a real search: null when the server has no YouTube key or cannot be reached */
  const SEARCHES = new Map();
  function ytRemote(q, k) { const key = (k ? "ko:" : "en:") + q.toLowerCase();
    if (SEARCHES.has(key)) return SEARCHES.get(key);
    const ctl = typeof AbortController !== "undefined" ? new AbortController() : null; if (ctl) setTimeout(() => ctl.abort(), 8000);
    const pr = fetch(YT_API() + "search?hl=" + (k ? "ko" : "en") + "&q=" + encodeURIComponent(q), ctl ? {signal: ctl.signal} : {})
      .then((r) => r.ok ? r.json() : null).then((j) => { if (!j || !Array.isArray(j.items)) return null;
        return j.items.map((x) => { const row = [x.id, x.t, x.ch, x.len || "", fmtViews(x.views, k), fmtAgo(x.at, k), k ? "ko" : "en", "web"]; if (!YT.some((v) => v[0] === x.id)) META.set(x.id, row); return row; }); })
      .catch(() => null);
    SEARCHES.set(key, pr); pr.then((r) => { if (!r) SEARCHES.delete(key); }); return pr; }
  /* what this viewer watched and searched, for the home feed (this browser only) */
  const HKEY = "hl_yt_hist";
  function hist() { try { const h = JSON.parse(localStorage.getItem(HKEY) || "{}"); return {w: h.w || [], q: h.q || []}; } catch (e) { return {w: [], q: []}; } }
  function histSave(h) { try { localStorage.setItem(HKEY, JSON.stringify({w: h.w.slice(-60), q: h.q.slice(-12)})); } catch (e) {} }
  function noteWatch(v) { const h = hist(); h.w = h.w.filter((x) => x.id !== v[0]); h.w.push({id: v[0], c: v[7], row: META.has(v[0]) ? v : null}); histSave(h); }
  function noteSearch(q) { const h = hist(); h.q = h.q.filter((x) => x !== q); h.q.push(q); histSave(h); }
  /* the home feed: the library in its hand-picked order to begin with, then topics watched first,
     videos found through searches mixed in, and what was just watched moved down */
  function feed(lib) { const h = hist(); if (!h.w.length) return lib;
    const wc = {}, seen = new Set(h.w.map((x) => x.id)); h.w.forEach((x, i) => { wc[x.c] = (wc[x.c] || 0) + 1 + i / h.w.length; });
    const extra = []; for (const x of h.w.slice().reverse()) if (x.row && !extra.some((r) => r[0] === x.row[0])) { extra.push(x.row); if (!ytFind(x.row[0])) META.set(x.row[0], x.row); }
    for (const r of META.values()) if (extra.length < 12 && !extra.some((e) => e[0] === r[0])) extra.push(r);
    const score = (v, i) => (wc[v[7]] || 0) * 3 - i * 0.08 - (seen.has(v[0]) ? 6 : 0);
    const all = lib.concat(extra.filter((r) => !lib.some((v) => v[0] === r[0])));
    return all.map((v, i) => [score(v, i), v]).sort((a, b) => b[0] - a[0]).map((x) => x[1]); }
  /* the official IFrame Player API, loaded once */
  let ytApiP = null;
  function ytApi() { if (window.YT && window.YT.Player) return Promise.resolve(window.YT);
    if (!ytApiP) ytApiP = new Promise((res, rej) => { const prev = window.onYouTubeIframeAPIReady; window.onYouTubeIframeAPIReady = () => { if (prev) try { prev(); } catch (e) {} res(window.YT); };
      const sc = document.createElement("script"); sc.src = "https://www.youtube.com/iframe_api"; sc.async = true; sc.onerror = () => { ytApiP = null; rej(new Error("iframe_api")); }; document.head.appendChild(sc);
      setTimeout(() => rej(new Error("timeout")), 9000); });
    return ytApiP; }
  /* search the library the way a viewer would: every word should appear in the title, channel or topic */
  function ytSearch(q) { const w = String(q).toLowerCase().split(/\s+/).filter(Boolean); if (!w.length) return [];
    return YT.map((v) => { const hay = (v[1] + " " + v[2] + " " + YT_CAT[v[7]].join(" ")).toLowerCase(); let s = 0; for (const t of w) if (hay.includes(t)) s += t.length; return [s, v]; })
      .filter((x) => x[0] > 0).sort((a, b) => b[0] - a[0]).map((x) => x[1]); }

  function isUrl(s) { return /^(https?:\/\/|about:|\.{0,2}\/|[\w-]+\.(html?|pdf)(\?|#|$))/i.test(s) || (/^[\w-]+(\.[\w-]+)+(:\d+)?(\/\S*)?$/.test(s) && !/\s/.test(s)); }
  function abs(u) { if (/^https?:\/\//i.test(u) || /^about:/i.test(u)) return u; if (/^[\w-]+(\.[\w-]+)+(:\d+)?(\/\S*)?$/.test(u) && !/\.(html?|pdf)$/i.test(u)) return "https://" + u;
    try { return new URL(u, location.href).href; } catch (e) { return "https://" + u; } }

  window.VBrowser = function (o) {
    inject();
    const kind = o.kind || "edge", mob = !!o.mobile, L = () => TXT[(o.lang && o.lang()) === "en" ? "en" : "ko"];
    const online = o.online || (() => true), links = o.links || [];
    const el = document.createElement("div");
    const app = o.app || null;            /* "youtube": the YouTube app itself, no browser around it */
    el.className = "vb vb-" + kind + (mob ? " vb-mob" : "") + (o.embedded ? " emb" : "") + (app ? " vb-app" : "");
    el.innerHTML = (mob
      ? '<div class="vb-bar"><button class="vb-b" data-k="home" title="Home">⌂</button><div class="vb-addr"><span class="ic">🔒</span><input spellcheck="false" autocomplete="off"></div><span class="vb-tabs">1</span><button class="vb-b" data-k="menu">⋮</button></div>'
      : '<div class="vb-bar"><button class="vb-b" data-k="back" title="Back">←</button><button class="vb-b" data-k="fwd" title="Forward">→</button><button class="vb-b" data-k="reload" title="Reload">⟳</button>' +
        '<button class="vb-b" data-k="home" title="Home">⌂</button><div class="vb-addr"><span class="ic">🔒</span><input spellcheck="false" autocomplete="off"></div><button class="vb-b" data-k="menu">' + (kind === "edge" ? "···" : "⋮") + "</button></div>") +
      '<div class="vb-body"><div class="vb-page"></div><iframe class="vb-frame" hidden allow="fullscreen" referrerpolicy="strict-origin-when-cross-origin"></iframe><div class="vb-info" hidden><span></span><button data-k="real"></button><button class="x" data-k="noinfo">✕</button></div></div><div class="vb-menu" hidden></div>';
    const $ = (s) => el.querySelector(s), inp = $(".vb-addr input"), page = $(".vb-page"), info = $(".vb-info"), menu = $(".vb-menu");
    let frame = $(".vb-frame");
    const st = {hist: [], i: -1, zoom: 1, cur: null, info: true};

    const ko = () => !((o.lang && o.lang()) === "en");
    function title() { const c = st.cur; if (!c || c.t === "ntp") return L().newTab; if (c.t === "off") return c.url;
      if (c.t === "yt") { const v = c.v && ytFind(c.v); return (v ? v[1] + " - " : c.q ? c.q + " - " : "") + "YouTube"; } return c.title || c.url; }
    function changed() { inp.value = st.cur && st.cur.t === "yt" ? ytUrl(st.cur) : st.cur && st.cur.t !== "ntp" ? st.cur.url : ""; inp.placeholder = L().addr(kind);
      const b = (k) => el.querySelector('[data-k="' + k + '"]'); if (b("back")) b("back").disabled = st.i <= 0; if (b("fwd")) b("fwd").disabled = st.i >= st.hist.length - 1;
      $(".vb-addr .ic").textContent = st.cur && (st.cur.t === "yt" || (st.cur.t === "web" && /^https:/.test(st.cur.url))) ? "🔒" : st.cur && st.cur.t === "web" ? "ⓘ" : "🔍";
      if (o.onchange) o.onchange(title()); }
    function newFrame(sandbox) { const f = document.createElement("iframe"); f.className = "vb-frame"; f.setAttribute("allow", "fullscreen"); f.setAttribute("referrerpolicy", "strict-origin-when-cross-origin");
      if (sandbox) f.setAttribute("sandbox", "allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox");    /* no top navigation: a page cannot break out of the laptop */
      frame.replaceWith(f); frame = f; applyZoom(); }
    function applyZoom() { const z = st.zoom; frame.style.transform = z === 1 ? "" : "scale(" + z + ")"; frame.style.width = 100 / z + "%"; frame.style.height = 100 / z + "%"; }
    function show(c) { st.cur = c; menu.hidden = true;
      if (c.t === "web" && !online()) { show({t: "off", url: c.url}); return; }
      if (c.t === "web") { const same = new URL(c.url, location.href).origin === location.origin; newFrame(!same); frame.hidden = false; page.hidden = true; frame.src = c.url;
        info.hidden = same || !st.info; if (!info.hidden) { info.querySelector("span").textContent = L().info; info.querySelector('[data-k="real"]').textContent = L().real; } }
      else { frame.hidden = true; frame.src = "about:blank"; info.hidden = true; page.hidden = false; page.innerHTML = c.t === "yt" ? ytPage(c) : c.t === "ntp" ? ntp() : offline(); page.scrollTop = 0; wirePage(); }
      if (c.t === "yt" && c.q && c.res === undefined && online()) ytRemote(c.q, ko()).then((r) => { c.res = r; if (st.cur === c) { page.innerHTML = ytPage(c); wirePage(); } });
      if (c.t === "yt" && c.v) { const v = ytFind(c.v); if (v) noteWatch(v); mountPlayer(); }
      changed(); }
    /* the watch page's player: YouTube's IFrame Player API, or a plain embed if the API script cannot load */
    function mountPlayer() { const box = page.querySelector("[data-player]"); if (!box) return; const id = box.dataset.player, k = ko(), slot = box.firstChild;
      const plain = () => { if (!slot.isConnected) return; const f = document.createElement("iframe");
        f.src = "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(id) + "?autoplay=1&rel=0&playsinline=1&hl=" + (k ? "ko" : "en") + (/^https?:/.test(location.origin) ? "&origin=" + encodeURIComponent(location.origin) : "");
        f.setAttribute("allow", "autoplay; encrypted-media; picture-in-picture; fullscreen"); f.setAttribute("allowfullscreen", ""); f.setAttribute("referrerpolicy", "strict-origin-when-cross-origin"); slot.replaceWith(f); };
      const fail = (code) => { if (!box.isConnected) return; box.innerHTML = '<div class="yt-err"><b>' + esc(code === 101 || code === 150 || code === 153 ? (k ? "이 동영상은 다른 사이트에서 재생할 수 없게 설정되어 있습니다." : "The owner does not allow this video to play on other sites.")
          : code === 100 ? (k ? "동영상을 찾을 수 없습니다 (삭제되었거나 비공개)." : "Video unavailable (removed or private).") : (k ? "동영상을 재생할 수 없습니다." : "This video cannot be played.")) +
        '</b><a class="yt-ext" href="https://www.youtube.com/watch?v=' + encodeURIComponent(id) + '" target="_blank" rel="noopener">' + (k ? "YouTube에서 보기 ↗" : "Watch on YouTube ↗") + "</a></div>"; };
      if (!/^https?:/.test(location.protocol)) { plain(); return; }
      ytApi().then((YTN) => { if (!slot.isConnected) return;
        new YTN.Player(slot, {host: "https://www.youtube-nocookie.com", videoId: id, width: "100%", height: "100%",
          playerVars: {autoplay: 1, rel: 0, playsinline: 1, hl: k ? "ko" : "en", origin: location.origin}, events: {onError: (e) => fail(e.data)}}); }).catch(plain); }
    function nav(c) { st.hist = st.hist.slice(0, st.i + 1); st.hist.push(c); st.i = st.hist.length - 1; show(c); }
    function go(s) { s = String(s || "").trim(); if (!s) return;
      if (isUrl(s)) { const y = ytParse(abs(s)); if (y) { nav(y); return; } const u = abs(s), nm = decodeURIComponent(u.split("?")[0].split("/").filter(Boolean).pop() || u); nav({t: "web", url: u, title: /^https?:/.test(u) && !/\.pdf$/i.test(u) ? new URL(u).hostname : nm}); return; }
      const u = kind === "edge" ? "https://www.bing.com/search?q=" + encodeURIComponent(s) : "https://www.google.com/search?igu=1&q=" + encodeURIComponent(s);
      nav({t: "web", url: u, title: L().results(s)}); }
    function ntp() { const t = L(), logo = kind === "edge" ? '<div class="vb-logo">Microsoft <b>Bing</b></div>'
        : kind === "samsung" ? '<div class="vb-logo"><img alt="" src="' + ICONS.samsung_internet + '" style="width:44px;height:44px">' + (ko() ? "삼성 인터넷" : "Samsung Internet") + "</div>"
        : '<div class="vb-logo"><span style="color:#4285f4">G</span><span style="color:#ea4335">o</span><span style="color:#fbbc05">o</span><span style="color:#4285f4">g</span><span style="color:#34a853">l</span><span style="color:#ea4335">e</span></div>';
      return '<div class="vb-ntp">' + logo + '<div class="vb-q"><span style="margin-right:10px;color:#5f6368">🔍</span><input placeholder="' + esc(t.search(kind)) + '" spellcheck="false"></div><div class="vb-tiles">' +
        links.map((l, i) => '<div class="vb-tile" data-i="' + i + '"><div class="c"' + (l.col ? ' style="background:' + l.col + ';color:#fff"' : "") + ">" + esc(l.ic || (typeof l.t === "string" ? l.t : l.t[(o.lang && o.lang()) === "en" ? "en" : "ko"]).charAt(0)) + "</div>" +
          esc(typeof l.t === "string" ? l.t : l.t[(o.lang && o.lang()) === "en" ? "en" : "ko"]) + "</div>").join("") + "</div></div>"; }
    function ytCard(v) { const h = ytHue(v[2]);
      return '<a class="yt-card" data-v="' + v[0] + '"><div class="yt-th"><img loading="lazy" alt="" src="https://i.ytimg.com/vi/' + v[0] + '/mqdefault.jpg"><span>' + esc(v[3]) + "</span></div>" +
        '<div class="yt-meta"><span class="yt-ch" style="background:hsl(' + h + ' 50% 45%)">' + esc([...v[2]][0] || "?") + "</span><div><b>" + esc(v[1]) + "</b><i>" + esc(v[2]) + "</i><i>" + esc(v[4]) + (v[5] ? " · " + esc(v[5]) : "") + "</i></div></div></a>"; }
    function ytPage(c) { const k = ko(), mine = (v) => (v[6] === "ko") === k;
      const top = '<div class="yt-top"><button class="yt-hb" type="button">☰</button><a class="yt-logo" data-yt="home"><img alt="" src="' + ICONS.youtube + '">YouTube<sup>' + (k ? "KR" : "") + "</sup></a>" +
        '<form class="yt-s"><input value="' + esc(c.q || "") + '" placeholder="' + (k ? "검색" : "Search") + '" spellcheck="false"><button type="submit">🔍</button></form><span class="yt-av">H</span></div>';
      if (!online()) return '<div class="yt">' + top + '<div class="yt-off"><div class="ic">📡</div><h2>' + (k ? "인터넷에 연결되어 있지 않습니다" : "You're offline") + "</h2><div>" +
        (k ? "연결 상태를 확인하세요." : "Check your connection.") + '</div><button data-yt="retry">' + (k ? "다시 시도" : "Retry") + "</button></div></div>";
      const lib = YT.filter(mine).concat(YT.filter((v) => !mine(v)));
      if (c.v) { const v = ytFind(c.v) || [c.v, "YouTube", "YouTube", "", "", "", "en", "olym"], h = ytHue(v[2]);
        const next = lib.filter((x) => x[0] !== v[0] && x[7] === v[7]).concat(lib.filter((x) => x[0] !== v[0] && x[7] !== v[7])).slice(0, 14);
        return '<div class="yt">' + top + '<div class="yt-watch"><div><div class="yt-player" data-player="' + esc(v[0]) + '"><div></div></div><div class="yt-info"><div class="yt-wt">' + esc(v[1]) + "</div>" +
          '<div class="yt-own"><span class="yt-ch" style="background:hsl(' + h + ' 50% 45%)">' + esc([...v[2]][0] || "?") + "</span><div><b>" + esc(v[2]) + "</b><i>" + (k ? "구독자" : "subscribers") + '</i></div><button class="yt-sub" data-yt="sub">' + (k ? "구독" : "Subscribe") + "</button>" +
          '<div class="yt-acts"><button data-yt="like">👍 ' + (k ? "좋아요" : "Like") + "</button><button>↗ " + (k ? "공유" : "Share") + "</button></div></div>" +
          '<div class="yt-desc"><b>' + esc(v[4]) + (v[5] ? " · " + esc(v[5]) : "") + "</b><br>" + esc((k ? "주제: " : "Topic: ") + YT_CAT[v[7]][k ? 0 : 1]) + '<br><a class="yt-ext" href="https://www.youtube.com/watch?v=' + encodeURIComponent(v[0]) + '" target="_blank" rel="noopener">' + (k ? "재생이 안 되면 YouTube에서 열기 ↗" : "Won’t play? Open on YouTube ↗") + "</a></div></div></div>" +
          '<div class="yt-side">' + next.map(ytCard).join("") + "</div></div></div>"; }
      if (c.q) { const local = ytSearch(c.q), remote = c.res || [], r = remote.concat(local.filter((v) => !remote.some((x) => x[0] === v[0])));
        const ext = '<a class="yt-ext" href="https://www.youtube.com/results?search_query=' + encodeURIComponent(c.q) + '" target="_blank" rel="noopener">' + (k ? "YouTube에서 검색 ↗" : "Search on YouTube ↗") + "</a>";
        const note = c.res === undefined ? (k ? "YouTube에서 찾는 중…" : "Searching YouTube…") : c.res === null ? (r.length ? (k ? "추천 목록에서 찾은 결과입니다 · " : "From the picks · ") + ext
          : (k ? "‘" + c.q + "’에 대한 결과가 없습니다 · " : "No results for “" + c.q + "” · ") + ext) : "";
        return '<div class="yt">' + top + (note ? '<div class="yt-note">' + (c.res === undefined ? esc(note) : note) + "</div>" : "") +
          '<div class="yt-row">' + (r.length ? r : c.res === undefined ? [] : lib.slice(0, 12)).map(ytCard).join("") + "</div></div>"; }
      const cat = c.cat || "", chips = '<div class="yt-chips"><button data-cat="" class="' + (cat ? "" : "on") + '">' + (k ? "전체" : "All") + "</button>" +
        Object.keys(YT_CAT).map((x) => '<button data-cat="' + x + '" class="' + (cat === x ? "on" : "") + '">' + YT_CAT[x][k ? 0 : 1] + "</button>").join("") + "</div>";
      const home = feed(lib);
      return '<div class="yt">' + top + chips + '<div class="yt-grid">' + (cat ? home.filter((v) => v[7] === cat) : home).map(ytCard).join("") + "</div></div>"; }
    function offline() { const t = L();
      return '<div class="vb-off">' + (kind === "edge" ? '<div style="font-size:40px">🏄</div>' : DINO) + "<h1>" + esc(t.offT(kind)) + "</h1>" + (kind === "edge" ? "" : "<div>" + esc(t.offH) + "</div>") +
        "<ul>" + t.offL.slice(0, kind === "edge" ? 3 : 2).map((x) => "<li>" + esc(x) + "</li>").join("") + "</ul>" + (kind === "edge" ? "" : "<code>ERR_INTERNET_DISCONNECTED</code>") + "</div>"; }
    function wirePage() { const q = page.querySelector(".vb-q input"); if (q) q.onkeydown = (e) => { e.stopPropagation(); if (e.key === "Enter") go(q.value); };
      const yf = page.querySelector(".yt-s"); if (yf) { const yi = yf.querySelector("input"); yi.onkeydown = (e) => e.stopPropagation();
        yf.onsubmit = (e) => { e.preventDefault(); const v = yi.value.trim(); if (v) noteSearch(v); nav(v ? {t: "yt", q: v} : {t: "yt"}); }; }
      page.querySelectorAll("[data-v]").forEach((d) => d.onclick = () => nav({t: "yt", v: d.dataset.v}));
      page.querySelectorAll("[data-cat]").forEach((d) => d.onclick = () => { st.cur.cat = d.dataset.cat; show(st.cur); });
      page.querySelectorAll("[data-yt]").forEach((d) => d.onclick = () => { const k = d.dataset.yt; if (k === "home") nav({t: "yt"}); else if (k === "retry") show(st.cur);
        else if (k === "sub" || k === "like") d.classList.toggle("on"); });
      page.querySelectorAll(".vb-tile").forEach((d) => d.onclick = () => go(links[+d.dataset.i].url)); }
    function setMenu() { const t = L(); menu.innerHTML = '<div data-m="new">' + t.menuNew + "<i>Ctrl+T</i></div><hr>" +
        '<div data-m="zin">' + t.zoomIn + "<i>" + Math.round(st.zoom * 100) + "%</i></div>" + '<div data-m="zout">' + t.zoomOut + "</div>" + '<div data-m="zr">' + t.zoomR + "</div><hr>" +
        '<div data-m="reload">' + t.reload + "</div>" + (st.cur && st.cur.t === "web" ? '<div data-m="real">' + t.real + "</div>" : "");
      menu.querySelectorAll("[data-m]").forEach((d) => d.onclick = (e) => { e.stopPropagation(); const m = d.dataset.m; menu.hidden = true;
        if (m === "new") nav({t: "ntp"}); else if (m === "zin") { st.zoom = Math.min(2, st.zoom + 0.1); applyZoom(); } else if (m === "zout") { st.zoom = Math.max(0.5, st.zoom - 0.1); applyZoom(); }
        else if (m === "zr") { st.zoom = 1; applyZoom(); } else if (m === "reload") reload(); else if (m === "real") window.open(st.cur.url, "_blank", "noopener"); }); }
    function reload() { if (st.cur) show(st.cur); }
    function back() { if (st.i > 0) { st.i--; show(st.hist[st.i]); return true; } return false; }
    function fwd() { if (st.i < st.hist.length - 1) { st.i++; show(st.hist[st.i]); } }
    el.addEventListener("click", (e) => { const b = e.target.closest("[data-k]"); if (!b) { if (!e.target.closest(".vb-menu")) menu.hidden = true; return; } const k = b.dataset.k;
      if (k === "back") back(); else if (k === "fwd") fwd(); else if (k === "reload") reload(); else if (k === "home") nav(app === "youtube" ? {t: "yt"} : {t: "ntp"});
      else if (k === "menu") { setMenu(); menu.hidden = !menu.hidden; } else if (k === "real") window.open(st.cur.url, "_blank", "noopener"); else if (k === "noinfo") { st.info = false; info.hidden = true; } });
    inp.onfocus = () => inp.select();
    inp.onkeydown = (e) => { e.stopPropagation(); if (e.key === "Enter") { go(inp.value); inp.blur(); } else if (e.key === "Escape") { changed(); inp.blur(); } };
    el.addEventListener("keydown", (e) => e.stopPropagation());
    el.addEventListener("wheel", (e) => e.stopPropagation(), {passive: true});
    nav(app === "youtube" ? {t: "yt"} : {t: "ntp"});
    let shown = null;
    return {el, go, back, reload, title, kind,
      canBack: () => st.i > 0,
      /* over a canvas: page coordinates of the client area */
      place(x, y, w, h, vis, scale) { const sc = scale > 0 && scale < 4 ? scale : 1, key = vis ? [x, y, w, h, sc.toFixed(4)].map((v) => typeof v === "number" ? Math.round(v) : v).join(",") : "off"; if (key === shown) return; shown = key;
        if (!vis || w < 40 || h < 40) { el.style.display = "none"; return; } el.style.display = ""; el.style.left = Math.round(x) + "px"; el.style.top = Math.round(y) + "px";
        /* laid out at the device's own pixels, then shrunk onto its screen */
        el.style.width = Math.round(w / sc) + "px"; el.style.height = Math.round(h / sc) + "px"; el.style.transformOrigin = "0 0"; el.style.transform = sc === 1 ? "" : "scale(" + sc + ")"; },
      refresh() { if (st.cur && st.cur.t !== "web") show(st.cur); else changed(); },
      home() { nav(app === "youtube" ? {t: "yt"} : {t: "ntp"}); },
      netChanged() { if (st.cur && ((st.cur.t === "off" && online()) || (st.cur.t === "web" && !online()))) show(st.cur.t === "off" ? {t: "web", url: st.cur.url, title: st.cur.url} : st.cur); }};
  };
  /* a picture of the browser for canvases that cannot hold the live page (window thumbnails, the laptop seen on the bench) */
  /* the real logos for hosts that draw on a canvas: VBrowser.icon(name) is an <img> ready to drawImage */
  window.VBrowser.ICONS = ICONS;
  const ICON_IMG = {};
  window.VBrowser.icon = function (n) { if (!ICON_IMG[n] && ICONS[n]) { const i = new Image(); i.src = ICONS[n]; ICON_IMG[n] = i; } return ICON_IMG[n]; };
  for (const n in ICONS) window.VBrowser.icon(n);
  window.VBrowser.sketch = function (g, x, y, w, h, kind, title) {
    if (kind === "youtube") { g.fillStyle = "#fff"; g.fillRect(x, y, w, h); const s = Math.min(36, h * 0.1), ic = window.VBrowser.icon("youtube");
      if (ic && ic.complete) g.drawImage(ic, x + 12, y + 10, s * 1.43, s); g.fillStyle = "#0f0f0f"; g.font = "600 " + Math.round(s * 0.8) + "px Arial"; g.textAlign = "left"; g.fillText("YouTube", x + 16 + s * 1.43, y + 10 + s * 0.78);
      for (let i = 0; i < 6; i++){ const cw = (w - 48) / 3, cx = x + 12 + (i % 3) * (cw + 12), cy = y + s + 28 + Math.floor(i / 3) * (cw * 0.56 + 40); g.fillStyle = "#e5e5e5"; g.fillRect(cx, cy, cw, cw * 0.56); g.fillStyle = "#d9d9d9"; g.fillRect(cx, cy + cw * 0.56 + 8, cw * 0.8, 8); }
      return; }
    g.save(); g.beginPath(); g.rect(x, y, w, h); g.clip(); g.fillStyle = "#fff"; g.fillRect(x, y, w, h);
    const bh = Math.min(40, h * 0.12); g.fillStyle = kind === "edge" ? "#f7f7f7" : "#fff"; g.fillRect(x, y, w, bh); g.fillStyle = "#e2e2e2"; g.fillRect(x, y + bh - 1, w, 1);
    g.fillStyle = kind === "edge" ? "#fff" : "#f1f3f4"; g.strokeStyle = "#d6d6d6"; const ax = x + Math.min(140, w * 0.18), aw = w - (ax - x) - Math.min(50, w * 0.08);
    g.beginPath(); g.rect(ax, y + bh * 0.18, aw, bh * 0.64); g.fill(); if (kind === "edge") g.stroke();
    g.fillStyle = "#5f6368"; g.font = Math.max(8, Math.round(bh * 0.32)) + "px Arial"; g.textBaseline = "middle"; g.textAlign = "left"; g.fillText(title || "", ax + 10, y + bh / 2, aw - 20);
    g.fillStyle = kind === "edge" ? "#174ea6" : "#4285f4"; g.font = "600 " + Math.round(Math.min(46, w * 0.06)) + "px Arial"; g.textAlign = "center"; g.fillText(kind === "edge" ? "Microsoft Bing" : "Google", x + w / 2, y + bh + (h - bh) * 0.32);
    g.fillStyle = "#fff"; g.strokeStyle = "#dfe1e5"; g.lineWidth = 1; const qw = Math.min(w * 0.7, 560), qh = Math.min(44, h * 0.08);
    g.beginPath(); if (g.roundRect) g.roundRect(x + (w - qw) / 2, y + bh + (h - bh) * 0.42, qw, qh, qh / 2); else g.rect(x + (w - qw) / 2, y + bh + (h - bh) * 0.42, qw, qh); g.fill(); g.stroke();
    g.restore(); };
})();
