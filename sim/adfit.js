(() => {
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
      const desktop = matchMedia("(min-width: 768px)").matches;
      const experiment = document.querySelector(".wrap, main, #app");
      if (desktop && experiment) experiment.before(banner);
      else document.body.append(banner);
    }
    banner.hidden = !isKorean();
    if (!isKorean() || mounted) return;

    const desktop = matchMedia("(min-width: 768px)").matches;
    const ad = desktop
      ? {unit:"DAN-SftG79uMQrQr81Vk", width:728, height:90}
      : {unit:"DAN-iGyhh2ByjtPoCpiA", width:320, height:50};
    banner.classList.toggle("haslalab-adfit-desktop", desktop);
    const ins = document.createElement("ins");
    ins.className = "kakao_ad_area";
    ins.style.display = "none";
    ins.dataset.adUnit = ad.unit;
    ins.dataset.adWidth = String(ad.width);
    ins.dataset.adHeight = String(ad.height);
    banner.querySelector("div").append(ins);

    const script = document.createElement("script");
    script.src = "https://t1.kakaocdn.net/kas/static/ba.min.js";
    script.async = true;
    document.body.append(script);
    mounted = true;
  }

  const style = document.createElement("style");
  style.textContent = `
    #haslalab-adfit-banner{position:relative;width:320px;max-width:calc(100% - 24px);height:50px;margin:28px auto 44px}
    #haslalab-adfit-banner>span{position:absolute;top:-17px;left:0;color:#9aa3ab;font:9px/1.1 ui-monospace,monospace}
    #haslalab-adfit-banner>div{width:320px;max-width:100%;height:50px;overflow:hidden;border:1px solid #33373e;border-radius:6px;background:#20252c}
    @media (min-width:700px){#haslalab-adfit-banner{margin-top:36px}}
    @media (min-width:768px){
      #haslalab-adfit-banner.haslalab-adfit-desktop{width:728px;max-width:calc(100% - 48px);height:90px;margin-top:44px}
      #haslalab-adfit-banner.haslalab-adfit-desktop>div{width:728px;height:90px}
    }
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
