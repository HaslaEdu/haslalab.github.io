/* HaslaLab visit statistics: Cloudflare Web Analytics (no cookies, no browser storage, aggregate counts only).
   Cloudflare is already the site's processor (privacy.html, section 6); this adds "visit statistics" to its purpose.

   What it does NOT do: it never runs on account, payment, grading, exam, answer-sheet or scan pages (they don't load this file),
   inside embedded frames (exam mode, the monthly-problem embeds), off haslalab.org, before the privacy
   policy version that announces it takes effect, or when the browser sends Do Not Track / Global Privacy Control.

   To turn it on: Cloudflare dashboard → Analytics & Logs → Web Analytics → Add a site → haslalab.org
   → "Manage site" → copy the token from the JS snippet into TOKEN below. The token is public by design
   (it ends up in every page), so it can live in the repository. */
(() => {
  const TOKEN = "";
  const STARTS = Date.UTC(2026, 10, 10, 15); /* 2026-11-11 00:00 KST — privacy policy version 2026-11-11 */
  const HOSTS = ["haslalab.org", "www.haslalab.org"];
  try {
    if (!TOKEN || Date.now() < STARTS || !HOSTS.includes(location.hostname)) return;
    if (window.top !== window.self) return;
    if (navigator.doNotTrack === "1" || window.doNotTrack === "1" || navigator.globalPrivacyControl === true) return;
    const s = document.createElement("script");
    s.defer = true;
    s.src = "https://static.cloudflareinsights.com/beacon.min.js";
    s.setAttribute("data-cf-beacon", JSON.stringify({token: TOKEN}));
    document.head.appendChild(s);
  } catch (e) { /* statistics must never break a page */ }
})();
