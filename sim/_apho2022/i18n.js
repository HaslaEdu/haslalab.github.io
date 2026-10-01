/* HaslaLab: Korean for the organisers' APhO 2022 pages.
   ?lang=en keeps the original English; anything else (the default) shows Korean. */
(function(){
  var q=new URLSearchParams(location.search).get("lang");
  var LANG=window.APHO_LANG=(q==="en")?"en":"ko";
  var KO={
    "Magnetic Blackbox":"자기 블랙박스",
    "Acoustic Blackbox":"음향 블랙박스",
    "Intergrid spacing: 1 cm":"격자 간격: 1 cm",
    "Maximum magnetic field exceeded":"자기장이 측정 한계를 넘었습니다",
    "Rotate mobile:":"스마트폰 회전:",
    "Rotate magnet:":"자석 회전:",
    "Rotate scale:":"자 회전:",
    "Graph start time, t<sub>i</sub> (s):":"그래프 시작 시각, t<sub>i</sub> (s):",
    "Graph end time, t<sub>f</sub> (s):":"그래프 끝 시각, t<sub>f</sub> (s):",
    "Data-point interval Δ (s):":"데이터 간격 Δ (s):",
    "θ (degrees):":"θ (도):",
    "γ (degrees):":"γ (도):",
    "Start Measurement":"측정 시작",
    "Pause Measurement":"측정 일시정지",
    "Reset Graph":"그래프 초기화",
    "Drop":"떨어뜨리기",
    "Reset Positions":"위치 초기화",
    "2X Finer magnet movement":"자석 이동 2배 미세하게",
    "2X Coarser magnet movement":"자석 이동 2배 크게",
    "Show Scale":"자 보이기",
    "Hide Scale":"자 숨기기",
    "Plot Graph":"그래프 그리기",
    "B<sub>w</sub> &amp; B<sub>l</sub> vs t graph":"B<sub>w</sub>, B<sub>l</sub> – 시간 그래프",
    "B_w (in μT)":"B_w (μT)",
    "B_l (in μT)":"B_l (μT)",
    "Time (s)":"시간 (s)",
    "Magnetic field (μT)":"자기장 (μT)",
    "Frequency (Hz)":"진동수 (Hz)"
  };
  /* L("…") — the label in the page's language */
  window.L=function(s){ return LANG==="ko"&&KO[s]?KO[s]:s; };
  var norm=function(h){ return h.replace(/\s+/g," ").trim(); };
  function credit(el){
    var links=el.querySelectorAll("a");
    if(links.length<2) return;
    var mail=links[0].getAttribute("href"), repo=links[1].getAttribute("href");
    el.innerHTML="이 시뮬레이션은 Chandan Relekar, Siddhant Mukherjee, Siddharth Tiwary, Charudutt Kadolkar, Praveen Pathak이 "+
      "인도 데라둔에서 열린 2022 아시아 물리 올림피아드를 위해 만들었습니다. 개발팀 연락은 <a href=\""+mail+"\" target=\"_blank\">여기</a>로 하세요."+
      "<br> <br>소스 저장소는 <a href=\""+repo+"\" target=\"_blank\">여기</a>에 있습니다.";
  }
  function toggle(){
    var box=document.createElement("div");
    box.style.cssText="position:fixed;top:8px;left:8px;z-index:50;display:flex;gap:4px;font:13px sans-serif";
    ["ko","en"].forEach(function(l){
      var a=document.createElement("a"); a.textContent=l==="ko"?"한국어":"English";
      var u=new URL(location.href); u.searchParams.set("lang",l); a.href=u.toString();
      a.style.cssText="padding:4px 10px;border-radius:6px;text-decoration:none;"+(l===LANG?"background:#f2c14e;color:#111;font-weight:700":"background:#2a2f37;color:#e8eef2");
      box.appendChild(a);
    });
    document.body.appendChild(box);
  }
  document.addEventListener("DOMContentLoaded",function(){
    toggle();
    if(LANG!=="ko") return;
    document.documentElement.lang="ko";
    document.title=L(document.title);
    var els=document.querySelectorAll("span,p,b,button,h2,title");
    for(var i=0;i<els.length;i++){
      var el=els[i], h=norm(el.innerHTML);
      if(KO[h]) el.innerHTML=KO[h];
      else if(/This Simulation was developed by/.test(h)) credit(el);
    }
  });
})();
