/* The weekly league on the page: tier names, the badge (tier and rebirths), the group table with its zones, and the
   all-time ranking rows. The data comes from community/src/league.js (GET /api/league/me, /ranking, /history).
   Used by the practice page's League tab and the ranking page (index.html #/ranking). The browser reads
   window.HL_LEAGUE_VIEW; the tests require() this file. */
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  if(root)root.HL_LEAGUE_VIEW=api;
})(typeof window==='object'?window:null,function(){
  const TIERS=Object.freeze([
    ['bronze','브론즈','Bronze','#a8672f'],['silver','실버','Silver','#7d8791'],['gold','골드','Gold','#c8930a'],['platinum','플래티넘','Platinum','#2b9a92'],
    ['emerald','에메랄드','Emerald','#2b8a3e'],['sapphire','사파이어','Sapphire','#1b5fc7'],['ruby','루비','Ruby','#c2255c'],['amethyst','자수정','Amethyst','#8441b5'],
    ['diamond','다이아몬드','Diamond','#1c94d4'],['master','마스터','Master','#d9480f']]);
  const MASTER=TIERS.length-1;
  const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const ko=lang=>lang==='ko';
  const tierIndex=t=>Math.max(0,Math.min(MASTER,Number.isInteger(t)?t:TIERS.findIndex(x=>x[0]===t)));
  const tierName=(t,lang)=>TIERS[tierIndex(t)][ko(lang)?1:2];
  const rebirthText=(n,lang)=>n>0?(ko(lang)?`${n}환생`:`Rebirth ${n}`):'';
  /* the badge: a small gem in the tier's colour, the tier's name and, once reborn, the count */
  function badge(tier,rebirths,lang,{big=false}={}){
    const i=tierIndex(tier),[key,,,colour]=TIERS[i],rb=rebirthText(rebirths|0,lang);
    return `<span class="lg-badge lg-${key}${big?' lg-big':''}" style="--lg:${colour}" title="${esc(tierName(i,lang)+(rb?' · '+rb:''))}"><i aria-hidden="true"></i>${esc(tierName(i,lang))}${rb?`<b>${esc(rb)}</b>`:''}</span>`;
  }
  const daysLeftText=(n,lang)=>ko(lang)?`${n}일 남음`:n===1?'1 day left':`${n} days left`;
  const ZONE_TEXT={ko:{up:'승급',down:'강등',reborn:'환생',stay:''},en:{up:'Up',down:'Down',reborn:'Rebirth',stay:''}};
  const zoneText=(z,lang)=>ZONE_TEXT[ko(lang)?'ko':'en'][z]||'';
  function rulesLine(lang){
    return ko(lang)?'매주 그룹에서 1~7위는 한 단계 올라가고, 마지막 5명은 한 단계 내려갑니다. 마스터에서 1~3위는 환생합니다. 환생 횟수가 1 늘고 브론즈에서 다시 시작합니다.'
      :'Each week the top 7 in your group move up a league and the last 5 move down. In Master the top 3 are reborn: their rebirth count goes up by 1 and they start again in Bronze.';
  }
  function xpLine(lang,daily=200){
    return ko(lang)?`리그 XP는 맞힌 문제와 채점받은 풀이로만 쌓입니다. 같은 문제는 하루에 한 번, 하루 ${daily}문제까지 셉니다. 주는 월요일 0시(한국 시간)에 바뀝니다.`
      :`League XP comes only from problems you get right and answers that are graded. Each problem counts once a day, up to ${daily} problems a day. A new week starts Monday 00:00 Korea time.`;
  }
  /* the zones of a group of n, as the server's rule (league.js groupOutcomes) draws them, for the legend */
  function zoneCounts(tier,n){
    const i=tierIndex(tier);
    if(i>=MASTER)return{up:0,reborn:Math.min(3,n),down:Math.max(0,n-Math.max(3,n-5))};
    const up=Math.min(7,n);return{up,reborn:0,down:i>0?Math.max(0,n-Math.max(7,n-5)):0};
  }
  const flag=cc=>/^[A-Z]{2}$/.test(cc||'')?`<img class="lg-flag" alt="${esc(cc)}" title="${esc(cc)}" loading="lazy" decoding="async" width="20" height="15" src="https://flagcdn.com/w40/${cc.toLowerCase()}.png" srcset="https://flagcdn.com/w80/${cc.toLowerCase()}.png 2x">`:'<span class="lg-flag lg-noflag" aria-hidden="true"></span>';
  /* the group table; the server gives each row its zone */
  function standingsHtml(data,lang){
    const t=ko(lang),rows=data?.standings||[];
    if(!rows.length)return '';
    return `<table class="lg-table"><caption class="lg-sr">${t?'이번 주 그룹 순위':'This week\'s group'}</caption><thead><tr><th scope="col">${t?'순위':'Rank'}</th><th scope="col">${t?'닉네임':'Name'}</th><th scope="col" class="r">XP</th></tr></thead><tbody>${rows.map(r=>{
      const z=r.zone||'stay',label=zoneText(z,lang);
      return `<tr class="lg-z-${esc(z)}${r.me?' lg-me':''}"${r.me?' aria-current="true"':''}><td class="lg-rk">${r.rank}${label?`<small>${esc(label)}</small>`:''}</td><td><div class="lg-nm">${flag(r.country)}<span>${esc(r.nickname)}</span>${r.rebirths>0?`<em class="lg-rb">${esc(rebirthText(r.rebirths,lang))}</em>`:''}${r.me?`<em class="lg-you">${t?'나':'you'}</em>`:''}</div></td><td class="r">${Number(r.xp)||0}</td></tr>`;}).join('')}</tbody></table>`;
  }
  function legendHtml(data,lang){
    const t=ko(lang),z=data?.zones||{},n=(data?.standings||[]).length,c=zoneCounts(data?.tier??0,n);
    const items=[];
    if(z.reborn)items.push(['reborn',t?`1~${z.reborn}위 환생`:`Top ${z.reborn}: rebirth`]);
    if(z.up)items.push(['up',t?`1~${z.up}위 승급`:`Top ${z.up}: up`]);
    if(z.down)items.push(['down',t?`마지막 ${z.down}명 강등`:`Last ${z.down}: down`]);
    if(!z.down&&tierIndex(data?.tier??0)===0)items.push(['stay',t?'브론즈는 강등 없음':'No demotion from Bronze']);
    return `<ul class="lg-legend" data-counts="${c.up},${c.down},${c.reborn}">${items.map(([k,l])=>`<li class="lg-k-${k}">${esc(l)}</li>`).join('')}</ul>`;
  }
  /* the League tab for a signed-in member */
  function meHtml(data,lang,{rankingHref='#/ranking',settingsHref=''}={}){
    const t=ko(lang);
    const head=`<div class="lg-head">${badge(data.tier,data.rebirths,lang,{big:true})}<div class="lg-meta"><b>${esc(daysLeftText(data.days_left,lang))}</b><span>${t?'이번 주':'This week'} ${Number(data.xp)||0} XP${data.rank?` · ${t?data.rank+'위':'rank '+data.rank}`:''}</span></div></div>`;
    const body=data.joined?standingsHtml(data,lang)+legendHtml(data,lang)
      :`<p class="lg-empty">${t?`이번 주에는 아직 리그 XP가 없습니다. 문제를 하나 맞히면 ${esc(tierName(data.tier,lang))} 리그의 그룹(최대 30명)에 들어갑니다.`:`No league XP yet this week. Get one problem right and you join a group (up to 30 members) in the ${esc(tierName(data.tier,lang))} league.`}</p>`;
    return `<section class="lg" aria-label="${t?'리그':'League'}">${head}${body}<p class="lg-rule">${esc(rulesLine(lang))}</p><p class="lg-rule lg-small">${esc(xpLine(lang,data.rules?.daily_counted||200))}</p>
      <p class="lg-acts"><a class="lg-btn" href="${esc(rankingHref)}" target="_top">${t?'최종 순위 보기':'All-time ranking'}</a>${settingsHref?`<a class="lg-btn lg-sub" href="${esc(settingsHref)}" target="_top">${t?'설정':'Settings'}</a>`:''}</p></section>`;
  }
  function guestHtml(lang,{loginHref='/#/login'}={}){
    const t=ko(lang);
    return `<section class="lg lg-guest" aria-label="${t?'리그':'League'}"><h2>${t?'주간 리그':'Weekly leagues'}</h2>
      <p>${t?'로그인한 회원은 매주 비슷한 리그의 30명과 리그 XP를 겨룹니다. 브론즈에서 시작해 마스터까지 열 단계가 있습니다.':'Signed-in members compete each week with up to 30 others in the same league, on league XP. There are ten leagues, from Bronze to Master.'}</p>
      <p class="lg-tiers">${TIERS.map((_,i)=>badge(i,0,lang)).join('')}</p>
      <p class="lg-rule">${esc(rulesLine(lang))}</p>
      <p class="lg-acts"><a class="lg-btn" href="${esc(loginHref)}" target="_top">${t?'로그인하고 리그 참가':'Sign in to join'}</a><a class="lg-btn lg-sub" href="/#/ranking" target="_top">${t?'최종 순위 보기':'All-time ranking'}</a></p></section>`;
  }
  /* the all-time ranking: rebirths, then league, then total league XP (the server orders it) */
  function rankingHtml(data,lang){
    const t=ko(lang),rows=data?.rows||[];
    if(!rows.length)return `<p class="lg-empty">${t?'아직 순위에 오른 회원이 없습니다.':'No one is ranked yet.'}</p>`;
    return `<table class="lg-table lg-ranking"><thead><tr><th scope="col">${t?'순위':'Rank'}</th><th scope="col">${t?'닉네임':'Name'}</th><th scope="col">${t?'리그':'League'}</th><th scope="col" class="r">${t?'리그 XP':'League XP'}</th></tr></thead><tbody>${rows.map(r=>
      `<tr${r.me?' class="lg-me" aria-current="true"':''}><td class="lg-rk">${r.rank}</td><td><div class="lg-nm">${flag(r.country)}<span>${esc(r.nickname)}</span></div></td><td>${badge(r.tier,r.rebirths,lang)}</td><td class="r">${(Number(r.total_xp)||0).toLocaleString(t?'ko-KR':'en-US')}</td></tr>`).join('')}</tbody></table>`;
  }
  const pages=data=>Math.max(1,Math.ceil((data?.total||0)/(data?.per_page||100)));
  const CSS=`.lg{display:grid;gap:12px}.lg-head{display:flex;align-items:center;gap:14px;flex-wrap:wrap}.lg-meta{display:grid;gap:2px}.lg-meta b{font-size:16px}.lg-meta span{font-size:13px;opacity:.75}
.lg-badge{--lg:#888;display:inline-flex;align-items:center;gap:6px;padding:3px 10px 3px 8px;border-radius:999px;border:1.5px solid var(--lg);color:var(--lg);font-weight:700;font-size:13px;line-height:1.4;white-space:nowrap;background:color-mix(in srgb,var(--lg) 9%,transparent)}
.lg-badge i{width:10px;height:10px;background:var(--lg);transform:rotate(45deg);border-radius:2px;flex:none}.lg-badge b{font-weight:700;margin-left:2px;padding-left:6px;border-left:1px solid color-mix(in srgb,var(--lg) 45%,transparent)}
.lg-big{font-size:17px;padding:6px 14px 6px 12px}.lg-big i{width:14px;height:14px}.lg-master{background:color-mix(in srgb,var(--lg) 14%,transparent)}
.lg-table{width:100%;border-collapse:collapse;font-size:14px}.lg-table th{text-align:left;font-size:12px;font-weight:600;opacity:.7;padding:6px 8px;border-bottom:1px solid rgba(128,128,128,.35)}
.lg-table td{padding:8px;border-bottom:1px solid rgba(128,128,128,.18);vertical-align:middle}.lg-table .r{text-align:right;font-variant-numeric:tabular-nums}
.lg-rk{width:52px;font-weight:700;font-variant-numeric:tabular-nums}.lg-rk small{display:block;font-size:11px;font-weight:600}
.lg-nm{display:flex;align-items:center;gap:8px;min-width:0}.lg-nm span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.lg-flag{width:20px;height:15px;object-fit:cover;border-radius:2px;flex:none;box-shadow:0 0 0 1px rgba(0,0,0,.12)}.lg-noflag{display:inline-block;background:rgba(128,128,128,.2)}
.lg-rb,.lg-you{font-style:normal;font-size:11px;font-weight:700;padding:1px 6px;border-radius:999px;background:rgba(128,128,128,.16);flex:none}
.lg-z-up{background:rgba(47,158,68,.10)}.lg-z-up .lg-rk small{color:#2b8a3e}.lg-z-down{background:rgba(224,49,49,.09)}.lg-z-down .lg-rk small{color:#c92a2a}
.lg-z-reborn{background:rgba(132,65,181,.12)}.lg-z-reborn .lg-rk small{color:#8441b5}.lg-me td{font-weight:700}.lg-me{box-shadow:inset 3px 0 0 currentColor}
.lg-legend{display:flex;flex-wrap:wrap;gap:6px 14px;list-style:none;margin:0;padding:0;font-size:12px}.lg-legend li{display:flex;align-items:center;gap:6px}
.lg-legend li::before{content:"";width:12px;height:12px;border-radius:3px;background:rgba(128,128,128,.25)}.lg-k-up::before{background:rgba(47,158,68,.55)!important}.lg-k-down::before{background:rgba(224,49,49,.5)!important}.lg-k-reborn::before{background:rgba(132,65,181,.55)!important}
.lg-rule{margin:0;font-size:14px;line-height:1.55}.lg-small{font-size:12px;opacity:.75}.lg-empty{margin:0;padding:14px;border:1px dashed rgba(128,128,128,.45);border-radius:10px;font-size:14px}
.lg-acts{display:flex;flex-wrap:wrap;gap:8px;margin:0}.lg-btn{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:0 16px;border-radius:10px;background:#1c7ed6;color:#fff!important;text-decoration:none;font-weight:600;font-size:14px}
.lg-btn.lg-sub{background:transparent;color:inherit!important;border:1px solid rgba(128,128,128,.45)}.lg-tiers{display:flex;flex-wrap:wrap;gap:6px;margin:0}.lg-guest h2{margin:0;font-size:18px}.lg-guest p{margin:0}
@media (max-width:480px){.lg-table td,.lg-table th{padding:8px 4px}.lg-rk{width:40px}.lg-ranking .lg-badge{flex-wrap:wrap;white-space:normal;border-radius:10px;row-gap:0}.lg-ranking .lg-badge b{flex-basis:100%;border-left:0;padding-left:16px;margin-left:0;font-size:11px}}
.lg-sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.lg-pager{display:flex;gap:8px;align-items:center;justify-content:center;margin-top:12px}.lg-pager a,.lg-pager span{min-height:40px;min-width:40px;display:inline-flex;align-items:center;justify-content:center;padding:0 12px}`;
  function addStyle(doc){if(!doc||doc.getElementById('lgStyle'))return;const s=doc.createElement('style');s.id='lgStyle';s.textContent=CSS;doc.head.append(s);}
  return{TIERS,MASTER,tierIndex,tierName,rebirthText,badge,daysLeftText,zoneText,rulesLine,xpLine,zoneCounts,standingsHtml,legendHtml,meHtml,guestHtml,rankingHtml,pages,addStyle};
});
