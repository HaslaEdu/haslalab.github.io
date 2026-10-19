(() => {
  let mounted = false;
  let requestedEnglish = new URLSearchParams(location.search).get("lang") === "en";

  const isKorean = () => !requestedEnglish && document.documentElement.lang === "ko";
  const label = () => isKorean() ? "광고" : "Ad";

  function syncAd() {
    let banner = document.getElementById("haslalab-adfit-banner");
    if (!banner) {
      banner = document.createElement("aside");
      banner.id = "haslalab-adfit-banner";
      banner.innerHTML = '<span></span><div></div>';
      /* always the first thing on the page, so it sits in the same place in Korean and in English */
      document.body.prepend(banner);
      const pick = document.getElementById("hl-lang");
      if (pick) banner.after(pick);
    }
    banner.setAttribute("aria-label", isKorean() ? "광고" : "Advertisement");
    banner.querySelector("span").textContent = label();
    if (mounted) return;

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
    #haslalab-adfit-banner>div{width:320px;max-width:100%;height:50px}
    @media (min-width:700px){#haslalab-adfit-banner{margin-top:36px}}
    @media (min-width:768px){
      #haslalab-adfit-banner.haslalab-adfit-desktop{width:728px;max-width:calc(100% - 48px);height:90px;margin-top:44px}
      #haslalab-adfit-banner.haslalab-adfit-desktop>div{width:728px;height:90px}
    }
    @media print{#haslalab-adfit-banner{display:none}}
    /* the language buttons: always in the top right corner of the header, whatever the title and subtitle are */
    header:has(> .lang){position:relative;padding-right:190px !important}
    header > .lang{position:absolute;top:16px;right:12px}
    @media (max-width:600px){header:has(> .lang){padding-right:12px !important;padding-top:56px !important} header > .lang{top:12px}}
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
