/* Country and daily goal: the two questions asked at sign-up and changed later in Settings ("Learning").
   One country list for the site and the server (community/src/learner-profile.js keeps the same codes; a test checks
   they match). The browser reads window.HL_LEARNER_FORM; Node tests require() it. */
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  if(root)root.HL_LEARNER_FORM=api;
})(typeof window==='object'?window:null,function(){
  /* ISO 3166-1 alpha-2, every officially assigned code */
  const COUNTRIES=Object.freeze(('AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ '
    +'CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR '
    +'GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP '
    +'KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT '
    +'MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW '
    +'SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG '
    +'UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW').split(' '));
  const SET=new Set(COUNTRIES);
  const DAILY_GOALS=Object.freeze([5,10,15,20]),DEFAULT_GOAL=10;
  const isCountry=c=>typeof c==='string'&&SET.has(c);
  const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const names={};
  function countryName(cc,lang){
    const l=lang==='ko'?'ko':'en';
    try{names[l]||=new Intl.DisplayNames([l],{type:'region'});return names[l].of(cc)||cc;}catch(e){return cc;}
  }
  /* a flag as an image (flagcdn, as the archive's host flags) and as text for places an image cannot go (an <option>) */
  const flagEmoji=cc=>isCountry(cc)?String.fromCodePoint(...[...cc].map(c=>0x1F1A5+c.charCodeAt(0))):'';
  const flagImg=(cc,cls='lf-flag')=>isCountry(cc)?`<img class="${cls}" alt="" loading="lazy" decoding="async" width="20" height="15" src="https://flagcdn.com/w40/${cc.toLowerCase()}.png" srcset="https://flagcdn.com/w80/${cc.toLowerCase()}.png 2x">`:'';
  /* a first guess the member confirms: the browser's region (ko-KR, en-IN), else the time zone, else the page language */
  const ZONES={'Asia/Seoul':'KR','Asia/Kolkata':'IN','Asia/Calcutta':'IN','Asia/Tokyo':'JP','Asia/Shanghai':'CN','Asia/Hong_Kong':'HK','Asia/Taipei':'TW','Asia/Singapore':'SG',
    'Asia/Ho_Chi_Minh':'VN','Asia/Bangkok':'TH','Asia/Jakarta':'ID','Asia/Manila':'PH','Asia/Kuala_Lumpur':'MY','Asia/Dubai':'AE','Asia/Karachi':'PK','Asia/Dhaka':'BD',
    'Europe/London':'GB','Europe/Paris':'FR','Europe/Berlin':'DE','Europe/Madrid':'ES','Europe/Rome':'IT','Europe/Moscow':'RU','Europe/Kyiv':'UA','Europe/Istanbul':'TR',
    'Europe/Warsaw':'PL','Europe/Amsterdam':'NL','Australia/Sydney':'AU','Australia/Melbourne':'AU','Pacific/Auckland':'NZ','America/Toronto':'CA','America/Vancouver':'CA',
    'America/Mexico_City':'MX','America/Sao_Paulo':'BR','America/Argentina/Buenos_Aires':'AR','Africa/Lagos':'NG','Africa/Cairo':'EG','Africa/Johannesburg':'ZA','Africa/Nairobi':'KE'};
  function guessCountry(lang,timeZone,languages){
    for(const l of languages||[]){const m=/^[a-z]{2,3}-([A-Z]{2})$/i.exec(String(l));if(m&&isCountry(m[1].toUpperCase()))return m[1].toUpperCase();}
    if(ZONES[timeZone])return ZONES[timeZone];
    if(/^America\/(New_York|Chicago|Denver|Los_Angeles|Phoenix|Anchorage|Detroit|Boise|Indiana|Kentucky)/.test(timeZone||'')||timeZone==='Pacific/Honolulu')return 'US';
    return lang==='ko'?'KR':'US';
  }
  function browserGuess(lang){
    let tz='',langs=[];
    try{tz=Intl.DateTimeFormat().resolvedOptions().timeZone||'';}catch(e){}
    try{langs=navigator.languages?.length?navigator.languages:[navigator.language];}catch(e){}
    return guessCountry(lang,tz,langs);
  }
  /* the practice page's region (learn-path.js REGIONS) for a country */
  const regionOf=cc=>cc==='KR'?'kr':cc==='IN'?'in':cc==='US'?'us':isCountry(cc)?'global':'';

  const T={
    ko:{country:'국적·나라',countryHelp:'추측한 나라입니다. 맞는지 확인해 주세요.',search:'나라 이름 검색',goal:'하루 목표',goalUnit:n=>`${n}문제`,goalHelp:'하루에 풀 문제 수입니다. 설정에서 바꿀 수 있습니다.',none:'찾는 나라가 없습니다'},
    en:{country:'Country',countryHelp:'This is a guess. Please check it.',search:'Search countries',goal:'Daily goal',goalUnit:n=>`${n} problems`,goalHelp:'How many problems a day. You can change it in Settings.',none:'No country matches'}
  };
  let seq=0;
  /* the two fields as HTML; wire() makes the search filter the list and returns read() */
  function fieldsHtml(lang,value={}){
    const t=T[lang==='ko'?'ko':'en'],id='lf'+(++seq),cc=isCountry(value.country)?value.country:browserGuess(lang),goal=DAILY_GOALS.includes(value.daily_goal)?value.daily_goal:DEFAULT_GOAL;
    const sorted=[...COUNTRIES].sort((a,b)=>countryName(a,lang).localeCompare(countryName(b,lang),lang==='ko'?'ko':'en'));
    return `<div class="lf" data-learner-fields>
      <div class="lf-field"><label for="${id}c">${t.country}</label>
        <input type="search" class="lf-search" placeholder="${t.search}" aria-label="${t.search}" aria-controls="${id}c" autocomplete="off">
        <div class="lf-pick"><span class="lf-show" aria-hidden="true">${flagImg(cc)}</span><select id="${id}c" name="country" required>${sorted.map(c=>`<option value="${c}"${c===cc?' selected':''}>${flagEmoji(c)} ${esc(countryName(c,lang))}</option>`).join('')}</select></div>
        <small class="lf-help">${value.country?'':t.countryHelp}</small></div>
      <fieldset class="lf-field lf-goal"><legend>${t.goal}</legend><div class="lf-goals">${DAILY_GOALS.map(n=>`<label><input type="radio" name="daily_goal" value="${n}"${n===goal?' checked':''} required><span>${t.goalUnit(n)}</span></label>`).join('')}</div>
        <small class="lf-help">${t.goalHelp}</small></fieldset></div>`;
  }
  function wire(box,lang){
    const t=T[lang==='ko'?'ko':'en'],sel=box.querySelector('select[name=country]'),search=box.querySelector('.lf-search'),show=box.querySelector('.lf-show'),help=box.querySelector('.lf-field small');
    const all=[...sel.options].map(o=>({value:o.value,text:o.textContent,key:(o.textContent+' '+o.value+' '+countryName(o.value,'en')).toLowerCase()}));
    sel.onchange=()=>{show.innerHTML=flagImg(sel.value);if(help)help.textContent='';};
    search.oninput=()=>{
      const q=search.value.trim().toLowerCase(),keep=sel.value;
      /* the exact name first, then names that start with the words typed, then any other match */
      const score=o=>{const n=o.text.replace(/^\S+\s/,'').toLowerCase();return n===q||o.value.toLowerCase()===q?0:n.startsWith(q)?1:2;};
      const list=q?all.filter(o=>o.key.includes(q)).sort((a,b)=>score(a)-score(b)):all;
      sel.innerHTML=list.length?list.map(o=>`<option value="${o.value}">${esc(o.text)}</option>`).join(''):`<option value="" disabled>${t.none}</option>`;
      if(q&&list.length)sel.value=list[0].value;else if(list.some(o=>o.value===keep))sel.value=keep;
      sel.onchange();
    };
    search.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();sel.focus();}};
    return ()=>{const country=sel.value,goal=Number(box.querySelector('input[name=daily_goal]:checked')?.value);return isCountry(country)&&DAILY_GOALS.includes(goal)?{country,daily_goal:goal}:null;};
  }
  /* the style both pages share; added once */
  const CSS=`.lf{display:grid;gap:14px}.lf-field{display:grid;gap:6px;border:0;margin:0;padding:0;min-width:0}.lf-field>label,.lf-field>legend{font-weight:600;font-size:14px;padding:0}
.lf-search,.lf-pick select{min-height:44px;font:inherit;font-size:16px;padding:8px 10px;border:1px solid var(--lf-line,#c9ccd1);border-radius:8px;background:var(--lf-bg,#fff);color:inherit;width:100%;box-sizing:border-box}
.lf-pick{display:flex;align-items:center;gap:8px}.lf-show{flex:0 0 24px;display:flex;justify-content:center}.lf-flag{width:20px;height:15px;object-fit:cover;border-radius:2px;box-shadow:0 0 0 1px rgba(0,0,0,.12)}
.lf-goals{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}@media (max-width:440px){.lf-goals{grid-template-columns:repeat(2,minmax(0,1fr))}}.lf-goals label{min-width:0}.lf-help{white-space:normal}.lf-goals label{display:block;margin:0}.lf-goals input{position:absolute;opacity:0;pointer-events:none}
.lf-goals span{display:flex;align-items:center;justify-content:center;min-height:44px;border:1px solid var(--lf-line,#c9ccd1);border-radius:8px;font-size:14px;cursor:pointer;text-align:center;padding:0 4px}
.lf-goals input:checked+span{border-color:var(--lf-on,#1c7ed6);box-shadow:inset 0 0 0 1px var(--lf-on,#1c7ed6);font-weight:700}.lf-goals input:focus-visible+span{outline:2px solid var(--lf-on,#1c7ed6);outline-offset:2px}
.lf-help{color:var(--lf-muted,#666);font-size:12px}
.lf-prompt{margin:0 0 18px;padding:16px;border:1px solid var(--lf-line,#c9ccd1);border-radius:12px;background:var(--lf-card,var(--paper,#fff));display:grid;gap:10px}
.lf-prompt h2{margin:0;font-size:17px}.lf-prompt p{margin:0;font-size:14px}.lf-acts{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-top:12px}
.lf-acts button{min-height:44px;padding:0 16px}
@media (min-width:720px){.lf-prompt .lf{grid-template-columns:1fr 1fr;align-items:start}}`;
  function addStyle(doc){if(!doc||doc.getElementById('lfStyle'))return;const s=doc.createElement('style');s.id='lfStyle';s.textContent=CSS;doc.head.append(s);}
  return{COUNTRIES,DAILY_GOALS,DEFAULT_GOAL,isCountry,countryName,flagEmoji,flagImg,guessCountry,browserGuess,regionOf,fieldsHtml,wire,addStyle,TEXT:T};
});
