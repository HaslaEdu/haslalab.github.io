(() => {
  const unit = "DAN-iGyhh2ByjtPoCpiA";
  let mounted = false;
  let requestedEnglish = new URLSearchParams(location.search).get("lang") === "en";

  const isKorean = () => !requestedEnglish && document.documentElement.lang === "ko";

  function syncAd() {
    let banner = document.getElementById("haslalab-adfit-banner");
    if (!banner) {
      banner = document.createElement("aside");
      banner.id = "haslalab-adfit-banner";
      banner.setAttribute("aria-label", "광고");
      banner.innerHTML = '<span>광고</span><div></div>';
      document.body.append(banner);
    }
    banner.hidden = !isKorean();
    if (!isKorean() || mounted) return;

    const ins = document.createElement("ins");
    ins.className = "kakao_ad_area";
    ins.style.display = "none";
    ins.dataset.adUnit = unit;
    ins.dataset.adWidth = "320";
    ins.dataset.adHeight = "50";
    banner.querySelector("div").append(ins);

    const script = document.createElement("script");
    script.src = "https://t1.kakaocdn.net/kas/static/ba.min.js";
    script.async = true;
    document.body.append(script);
    mounted = true;
  }

  const style = document.createElement("style");
  style.textContent = `
    #haslalab-adfit-banner{position:relative;width:320px;max-width:calc(100% - 32px);height:50px;margin:28px auto 44px}
    #haslalab-adfit-banner>span{position:absolute;top:-17px;left:0;color:#9aa3ab;font:9px/1.1 ui-monospace,monospace}
    #haslalab-adfit-banner>div{width:320px;max-width:100%;height:50px;overflow:hidden}
    #haslalab-adfit-banner:has(ins[style*="display: none"]){display:none}
    @media (min-width:700px){#haslalab-adfit-banner{margin-top:36px}}
    @media print{#haslalab-adfit-banner{display:none}}
  `;
  document.head.append(style);
  new MutationObserver(syncAd).observe(document.documentElement, {attributes:true, attributeFilter:["lang"]});
  document.addEventListener("click", event => {
    if (event.target.closest("#btn-ko")) requestedEnglish = false;
    if (event.target.closest("#btn-en")) requestedEnglish = true;
    syncAd();
  });
  syncAd();
})();
