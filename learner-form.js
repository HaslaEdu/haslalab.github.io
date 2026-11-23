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
  /* the daily goal: any whole number from 1 to 50 (the server's learner-profile.js), 10 suggested, five quick picks */
  const GOAL_MIN=1,GOAL_MAX=50,DEFAULT_GOAL=10,GOAL_PICKS=Object.freeze([1,5,10,20,30]);
  const isDailyGoal=g=>Number.isInteger(g)&&g>=GOAL_MIN&&g<=GOAL_MAX;
  const clampGoal=v=>{const n=Math.round(Number(v));return Number.isFinite(n)?Math.max(GOAL_MIN,Math.min(GOAL_MAX,n)):DEFAULT_GOAL;};
  /* the one-time bonus for reaching the day's goal, as the server pays it (community/src/league.js goalBonus) */
  const goalBonus=g=>isDailyGoal(g)?Math.round(5*g+2*g**1.3):0;
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
    ko:{country:'국적·나라',countryHelp:'추측한 나라입니다. 맞는지 확인해 주세요.',search:'나라 이름 검색',goal:'하루 목표',goalUnit:n=>`${n}문제`,goalHelp:'맞힌 문제 수로 셉니다. 연습 화면에서 언제든 바꿀 수 있습니다.',none:'찾는 나라가 없습니다',
      recommended:'권장 10',less:'1 줄이기',more:'1 늘리기',count:'문제 수',reward:n=>`달성하면 +${n} XP`,unit:'문제'},
    en:{country:'Country',countryHelp:'This is a guess. Please check it.',search:'Search countries',goal:'Daily goal',goalUnit:n=>`${n} problems`,goalHelp:'Counted in problems you get right. Change it any time on the practice page.',none:'No country matches',
      recommended:'10 suggested',less:'One less',more:'One more',count:'Problems',reward:n=>`Reach it: +${n} XP`,unit:'problems'}
  };
  let seq=0;
  /* the goal on its own (sign-up, Settings and the practice page's goal panel): a stepper, five quick picks and the
     bonus it pays. wireGoal() returns read(), the number or null. */
  function goalHtml(lang,value){
    const t=T[lang==='ko'?'ko':'en'],id='lf'+(++seq),goal=isDailyGoal(value)?value:DEFAULT_GOAL;
    return `<fieldset class="lf-field lf-goal" data-goal-field><legend>${t.goal} <small class="lf-rec">${t.recommended}</small></legend>
        <div class="lf-step"><button type="button" class="lf-sb" data-goal-step="-1" aria-label="${t.less}">−</button>
          <div class="lf-num"><input id="${id}g" class="lf-goalnum" type="number" name="daily_goal" min="${GOAL_MIN}" max="${GOAL_MAX}" step="1" inputmode="numeric" value="${goal}" aria-label="${t.goal} (${GOAL_MIN}–${GOAL_MAX})" required><span class="lf-unit" aria-hidden="true">${t.unit}</span></div>
          <button type="button" class="lf-sb" data-goal-step="1" aria-label="${t.more}">+</button></div>
        <div class="lf-picks" role="group" aria-label="${t.goal}">${GOAL_PICKS.map(n=>`<button type="button" data-goal-pick="${n}" aria-pressed="${n===goal}"${n===DEFAULT_GOAL?' class="lf-recpick"':''}>${n}</button>`).join('')}</div>
        <small class="lf-help"><b class="lf-bonus">${t.reward(goalBonus(goal))}</b> · ${t.goalHelp}</small></fieldset>`;
  }
  function wireGoal(box,lang){
    const t=T[lang==='ko'?'ko':'en'],input=box.querySelector('input[name=daily_goal]');if(!input)return()=>null;
    const field=input.closest('[data-goal-field]'),bonus=field.querySelector('.lf-bonus');
    const paint=()=>{const g=Number(input.value);field.querySelectorAll('[data-goal-pick]').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.goalPick)===g)));
      field.querySelector('[data-goal-step="-1"]').disabled=g<=GOAL_MIN;field.querySelector('[data-goal-step="1"]').disabled=g>=GOAL_MAX;
      if(bonus)bonus.textContent=t.reward(goalBonus(isDailyGoal(g)?g:clampGoal(g)));};
    const set=v=>{input.value=String(clampGoal(v));paint();input.dispatchEvent(new Event('change',{bubbles:true}));};
    field.querySelectorAll('[data-goal-step]').forEach(b=>b.onclick=()=>set(Number(input.value||DEFAULT_GOAL)+Number(b.dataset.goalStep)));
    field.querySelectorAll('[data-goal-pick]').forEach(b=>b.onclick=()=>set(b.dataset.goalPick));
    input.oninput=paint;input.onblur=()=>set(input.value);
    paint();
    return ()=>{const g=Number(input.value);return isDailyGoal(g)?g:null;};
  }
  /* the two fields as HTML; wire() makes the search filter the list and returns read() */
  function fieldsHtml(lang,value={}){
    const t=T[lang==='ko'?'ko':'en'],id='lf'+(++seq),cc=isCountry(value.country)?value.country:browserGuess(lang);
    const sorted=[...COUNTRIES].sort((a,b)=>countryName(a,lang).localeCompare(countryName(b,lang),lang==='ko'?'ko':'en'));
    return `<div class="lf" data-learner-fields>
      <div class="lf-field"><label for="${id}c">${t.country}</label>
        <input type="search" class="lf-search" placeholder="${t.search}" aria-label="${t.search}" aria-controls="${id}c" autocomplete="off">
        <div class="lf-pick"><span class="lf-show" aria-hidden="true">${flagImg(cc)}</span><select id="${id}c" name="country" required>${sorted.map(c=>`<option value="${c}"${c===cc?' selected':''}>${flagEmoji(c)} ${esc(countryName(c,lang))}</option>`).join('')}</select></div>
        <small class="lf-help">${value.country?'':t.countryHelp}</small></div>
      ${goalHtml(lang,value.daily_goal)}</div>`;
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
    const goal=wireGoal(box,lang);
    return ()=>{const country=sel.value,g=goal();return isCountry(country)&&g?{country,daily_goal:g}:null;};
  }
  /* the style both pages share; added once */
  const CSS=`.lf{display:grid;gap:14px}.lf-field{display:grid;gap:6px;border:0;margin:0;padding:0;min-width:0}.lf-field>label,.lf-field>legend{font-weight:600;font-size:14px;padding:0}
.lf-search,.lf-pick select{min-height:44px;font:inherit;font-size:16px;padding:8px 10px;border:1px solid var(--lf-line,#c9ccd1);border-radius:8px;background:var(--lf-bg,#fff);color:inherit;width:100%;box-sizing:border-box}
.lf-pick{display:flex;align-items:center;gap:8px}.lf-show{flex:0 0 24px;display:flex;justify-content:center}.lf-flag{width:20px;height:15px;object-fit:cover;border-radius:2px;box-shadow:0 0 0 1px rgba(0,0,0,.12)}
.lf-rec{font-weight:600;font-size:12px;color:var(--lf-on,#1c7ed6);margin-left:4px}.lf-help{white-space:normal}
.lf-step{display:flex;align-items:stretch;gap:8px;max-width:280px}.lf-sb{flex:0 0 44px;min-height:44px;border:1px solid var(--lf-line,#c9ccd1);border-radius:8px;background:var(--lf-bg,#fff);color:inherit;font:inherit;font-size:20px;line-height:1;cursor:pointer}
.lf-sb:disabled{opacity:.4;cursor:default}.lf-num{flex:1;display:flex;align-items:center;gap:6px;min-height:44px;padding:0 10px;border:1px solid var(--lf-line,#c9ccd1);border-radius:8px;background:var(--lf-bg,#fff);margin:0}
.lf-num input.lf-goalnum{width:100%!important;min-width:0;height:auto!important;margin:0!important;border:0!important;box-shadow:none!important;outline:0;background:transparent!important;color:inherit;font:inherit;font-size:18px;font-weight:700;text-align:right;padding:0!important;-moz-appearance:textfield}.lf-num input::-webkit-inner-spin-button,.lf-num input::-webkit-outer-spin-button{-webkit-appearance:none;margin:0}
.lf-num .lf-unit{flex:none;white-space:nowrap;font-size:14px;font-weight:400;text-transform:none;letter-spacing:normal;opacity:.75;margin:0}.lf-num:focus-within{outline:2px solid var(--lf-on,#1c7ed6);outline-offset:1px}
.lf-picks{display:flex;flex-wrap:wrap;gap:6px}.lf-picks button{min-width:44px;min-height:40px;padding:0 10px;border:1px solid var(--lf-line,#c9ccd1);border-radius:999px;background:var(--lf-bg,#fff);color:inherit;font:inherit;font-size:14px;cursor:pointer}
.lf-picks button[aria-pressed=true]{border-color:var(--lf-on,#1c7ed6);box-shadow:inset 0 0 0 1px var(--lf-on,#1c7ed6);font-weight:700}.lf-picks .lf-recpick{border-style:dashed}
.lf-bonus{font-weight:700;color:inherit}
.lf-help{color:var(--lf-muted,#666);font-size:12px}
.lf-prompt{margin:0 0 18px;padding:16px;border:1px solid var(--lf-line,#c9ccd1);border-radius:12px;background:var(--lf-card,var(--paper,#fff));display:grid;gap:10px}
.lf-prompt h2{margin:0;font-size:17px}.lf-prompt p{margin:0;font-size:14px}.lf-acts{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-top:12px}
.lf-acts button{min-height:44px;padding:0 16px}
@media (min-width:720px){.lf-prompt .lf{grid-template-columns:1fr 1fr;align-items:start}}`;
  function addStyle(doc){if(!doc||doc.getElementById('lfStyle'))return;const s=doc.createElement('style');s.id='lfStyle';s.textContent=CSS;doc.head.append(s);}
  return{COUNTRIES,GOAL_MIN,GOAL_MAX,GOAL_PICKS,DEFAULT_GOAL,isDailyGoal,clampGoal,goalBonus,goalHtml,wireGoal,isCountry,countryName,flagEmoji,flagImg,guessCountry,browserGuess,regionOf,fieldsHtml,wire,addStyle,TEXT:T};
});
