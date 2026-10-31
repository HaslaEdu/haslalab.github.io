/* Score comparisons use the same complete paper and published scale. A partial
 * paper is never extrapolated into a complete round or an overall medal score. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.labComparison = api;
})(typeof window === 'object' ? window : null, function () {
  'use strict';
  const pending = new Map(), EPS = 1e-7;
  const finite = x => typeof x === 'number' && Number.isFinite(x);
  const validScore = (score, max) => finite(score) && finite(max) && max > 0 && score >= 0 && score <= max + EPS;
  const validReference = (r,score) => r?.manualOnly && r.max == null ? finite(score) && score >= 0 : validScore(score,r?.max);
  const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const label = (x, lang) => typeof x === 'string' ? x : x?.[lang] || x?.en || x?.ko || '';
  const fmt = x => finite(x) ? String(Math.round(x * 1000) / 1000) : '—';
  const taskKey = tasks => Array.isArray(tasks) ? [...new Set(tasks.map(String))].sort().join('|') : '';
  const uniqueTasks=s=>Array.isArray(s.tasks)&&s.tasks.length>0&&s.tasks.every(t=>typeof t==='string'&&t)&&new Set(s.tasks).size===s.tasks.length;
  const hasScore = s => s?.status === 'graded' && validScore(s.score, s.points) &&
    !Object.values(s.detail?.tasks || {}).some(t => t.grading_mode === 'qualitative_review');
  function matches(record, session) {
    return !record.manualOnly && hasScore(session) && uniqueTasks(session) && Math.abs(session.points - record.max) < EPS &&
      record.taskSets?.some(tasks => taskKey(tasks) === taskKey(session.tasks));
  }
  /* A theory or experiment score can never exceed its own total.  When the year's total has a
   * source-verified coverage floor (every total at or above it is published) and the published
   * round scores belong to exactly those published totals, any unpublished contestant scored
   * strictly below the floor in this round too.  A round score at or above the floor therefore
   * has an exact rank in the whole field. */
  function componentFloor(records, record) {
    if (!record || !['theory','experiment'].includes(record.scope) || record.complete === true || record.awardScope || record.manualOnly) return null;
    const n=(record.scores||[]).length;
    const total=(records||[]).find(t=>t.scope==='total'&&t.awardScope===true&&String(t.year)===String(record.year)&&
      finite(t.rankFloor)&&t.rankFloor>0&&(t.participants==null||Number.isInteger(t.participants))&&t.participants===record.participants&&
      t.complete!==true&&(t.scores||[]).length===n&&n>0&&
      (t.components||[]).some(c=>c.id===record.scope&&finite(c.max)&&Math.abs(c.max-record.max)<EPS));
    return total ? {floor:total.rankFloor,total} : null;
  }
  function roundReference(record, score, coverage = null) {
    const ref=record?.medalReference,tiers=['gold','silver','bronze'];
    if (!ref || ref.basis!=='round_rank' || record.awardScope || record.manualOnly ||
        !['theory','experiment'].includes(record.scope) || !validScore(score,record.max)) return null;
    const scores=(record.scores||[]).filter(x=>validScore(x,record.max)).slice().sort((a,b)=>b-a);
    const complete=record.complete===true&&record.participants===scores.length;
    if (!scores.length || ref.population!==(complete?'complete':'published') ||
        !ref.sources?.length || !ref.sources.every(s=>/^https?:\/\//.test(s.url||''))) return null;
    if (!tiers.every(k=>Number.isInteger(ref.counts?.[k])&&ref.counts[k]>=0)) return null;
    const total=tiers.reduce((n,k)=>n+ref.counts[k],0);
    if (!(total>0) || total>scores.length) return null;
    const cuts={};let boundary=0;
    for(const tier of tiers){
      boundary+=ref.counts[tier];
      if(ref.counts[tier]){
        const cut=scores[boundary-1];
        if(!finite(ref.cuts?.[tier])||Math.abs(ref.cuts[tier]-cut)>EPS)return null;
        cuts[tier]=cut;
      }else if(ref.cuts?.[tier]!=null)return null;
    }
    const medal=tiers.find(k=>finite(cuts[k])&&score+EPS>=cuts[k])||'none';
    /* Unpublished scores can only raise a cut, so "below every band" can never improve.  At or
     * above the coverage floor the rank itself is exact in the whole field, and so is its band;
     * below it, a band is unchanged only when its own cut is at or above the floor. */
    const floor=finite(coverage?.floor)?coverage.floor:null;
    const fullField=complete||medal==='none'||floor!=null&&(score+EPS>=floor||cuts[medal]+EPS>=floor);
    return {medal,scope:record.scope,counts:{...ref.counts},cuts,population:ref.population,sources:ref.sources,fullField,floor};
  }
  function evaluate(record, score, manual = false, coverage = null) {
    if (!record || record.manualOnly && !manual || !validReference(record,score)) return null;
    const scores = (record.scores || []).filter(x => validReference(record,x));
    const above = scores.filter(x => x > score + EPS).length;
    const tied = scores.filter(x => Math.abs(x - score) <= EPS).length;
    const complete = record.complete === true && scores.length > 0 && record.participants === scores.length;
    // Missing totals can affect rank only below a source-verified coverage floor.
    // This inference never applies to an individual round of a combined contest.
    const floor = record.scope === 'total' ? record.rankFloor : finite(coverage?.floor) ? coverage.floor : null;
    const bounded = !complete && scores.length > 0 && finite(floor) &&
      score + EPS >= floor && (record.participants == null || Number.isInteger(record.participants) && record.participants >= scores.length);
    // An unknown entrant count still allows an exact rank above the floor, but no field size or percentile.
    const fieldSize = complete || bounded ? record.participants ?? null : scores.length;
    let medal = null;
    if (record.awardScope === true) {
      const cuts = record.medalCutoffs || {};
      medal = ['gold','silver','bronze','hm'].find(k => finite(cuts[k]) &&
        (record.medalCutoffRule === 'gt' ? score > cuts[k] + EPS : score + EPS >= cuts[k])) ||
        (Object.keys(cuts).length ? 'none' : null);
    }
    // The best score: declared (editions without a score table) or the highest published one, which is always an awardee's.
    const best = finite(record.topScore) ? record.topScore : scores.length ? Math.max(...scores) : null;
    return {record, score, manual, best, n:scores.length, rank:scores.length ? above + 1 : null,
      tied, complete, bounded, fieldSize, top_pct:(complete||bounded) && Number.isInteger(fieldSize) && fieldSize > 1 && !record.participantCountUncertain ? Math.min(100,100 * (above + 1) / fieldSize) : null, medal,
      reference:roundReference(record,score,coverage), coverage:record.scope==='total'?null:coverage?{floor:coverage.floor,total:coverage.total.id}:null};
  }
  const mode=s=>s.review_only===true;
  const stamp=s=>finite(s.graded_at)?s.graded_at:finite(s.created_at)?s.created_at:0;
  const examKey=s=>s.exam_key||`${s.comp}${s.year}`;
  function componentMatches(component,s){
    if(!uniqueTasks(s)||!matches(component,s))return false;
    if(component.id==='theory'&&s.kind&&s.kind!=='theory')return false;
    if(['experiment','practical'].includes(component.id)&&s.kind&&s.kind!=='lab')return false;
    return true;
  }
  function combinedResults(data,session){
    if(data?.comp!==session?.comp||!hasScore(session)||!uniqueTasks(session)||!Number.isInteger(session.id)||session.id<1)return [];
    const records=(data.records||[]).filter(r=>String(r.year)===String(session.year));
    const history=(Array.isArray(session.related_results)?session.related_results:[]).filter(s=>s&&Number.isInteger(s.id)&&s.id>0&&s.id!==session.id&&
      s.comp===session.comp&&String(s.year)===String(session.year)&&examKey(s)===examKey(session)&&hasScore(s)&&uniqueTasks(s))
      .slice().sort((a,b)=>Number(mode(a)!==mode(session))-Number(mode(b)!==mode(session))||stamp(b)-stamp(a)||b.id-a.id);
    const results=[];
    for(const record of records){
      const components=record.components||[];
      if(record.manualOnly||!finite(record.max)||components.length<2||components.length>4||matches(record,session)||
        !components.every(c=>finite(c.max)&&c.max>0&&c.taskSets?.length)||
        Math.abs(components.reduce((n,c)=>n+c.max,0)-record.max)>EPS)continue;
      const anchors=components.map((c,i)=>componentMatches(c,session)?i:-1).filter(i=>i>=0);
      if(anchors.length!==1)continue;
      const chosen=components.map(()=>null);chosen[anchors[0]]=session;
      function fill(index,usedIds,usedTasks){
        if(index===components.length)return true;
        if(chosen[index])return fill(index+1,usedIds,usedTasks);
        for(const candidate of history){
          if(usedIds.has(candidate.id)||candidate.tasks.some(t=>usedTasks.has(t))||!componentMatches(components[index],candidate))continue;
          chosen[index]=candidate;
          if(fill(index+1,new Set([...usedIds,candidate.id]),new Set([...usedTasks,...candidate.tasks])))return true;
          chosen[index]=null;
        }
        return false;
      }
      if(!fill(0,new Set([session.id]),new Set(session.tasks)))continue;
      const score=Math.round(chosen.reduce((n,s)=>n+s.score,0)*1e8)/1e8,e=evaluate(record,score);
      if(!e)continue;
      // Each round also keeps its own round-rank reference, so a combined total never hides it.
      const roundOf=(c,s)=>{const rec=records.find(r=>r.scope===c.id&&matches(r,s));return rec?evaluate(rec,s.score,false,componentFloor(records,rec)):null;};
      e.combined={sessions:chosen.map((s,i)=>{const round=roundOf(components[i],s);
        return {id:s.id,scope:components[i].id,label:components[i].label,score:s.score,points:s.points,review_only:mode(s),
          round:round?{record:round.record.id,rank:round.rank,tied:round.tied,exact:round.complete||round.bounded,n:round.n,medal:round.reference?.medal||null,fullField:round.reference?.fullField??null}:null};}),
        mixedMode:chosen.some(s=>mode(s)!==mode(session))};
      results.push(e);
    }
    return results;
  }
  function assess(data, session) {
    if (!hasScore(session)) return {records:[], comparisons:[], totals:[]};
    const records = (data?.comp === session.comp ? data.records || [] : []).filter(r => String(r.year) === String(session.year));
    const direct=records.filter(r=>matches(r,session)).map(r=>evaluate(r,session.score,false,componentFloor(records,r)));
    const combined=direct.some(e=>e.record.awardScope||e.record.scope==='total')?[]:combinedResults(data,session);
    // A graded round keeps its own round card; an automatically combined total is added after it.
    const comparisons=combined.length?[...direct.filter(e=>e.record.scope!=='total'&&!e.record.awardScope),...combined]:direct,covered=new Set(comparisons.map(e=>e.record.id));
    return {records, scaleMismatch:records.some(r=>r.taskSets?.some(tasks=>taskKey(tasks)===taskKey(session.tasks))&&Math.abs(session.points-r.max)>=EPS),
      comparisons,totals:records.filter(r => (r.scope==='total'||r.awardScope) && (r.medalCutoffs||r.scores?.length) && !covered.has(r.id))};
  }
  const names = {
    ko:{gold:'금메달',silver:'은메달',bronze:'동메달',hm:'장려상',none:'공개 수상 기준 미달'},
    en:{gold:'Gold',silver:'Silver',bronze:'Bronze',hm:'Honourable mention',none:'Below published award thresholds'}
  };
  function sourcesHtml(record, lang) {
    const en = lang === 'en';
    const sources=(record.sources || []).filter((s,i,a) => /^https?:\/\//.test(s.url) && a.findIndex(x => x.url === s.url) === i);
    const links=sources.map(s => {
      const title=label(s.title,lang) || (en?'Source':'출처');
      return `<a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(title)}${s.official===false&&!/unofficial|비공식/i.test(title)?(en?' (unofficial)':' (비공식)'):''} ↗</a>`;
    }).join(' · ');
    return `<div class="hlcr-source"><b>${en?'Data sources':'자료 출처'}${sources.some(s=>s.official===false)?(en?' · includes unofficial records':' · 비공식 기록 포함'):''}</b><p>${links}</p></div>`;
  }
  function roundNote(s, lang) {
    const r=s.round,en=lang==='en';
    if(!r||r.rank==null)return '';
    const awards=names[en?'en':'ko'],scope=s.scope==='theory'?(en?'theory':'이론'):(en?'experiment':'실험');
    const icons={gold:'🥇',silver:'🥈',bronze:'🥉'};
    const rank=en?`#${r.rank}${r.tied?' tied':''}${r.exact?'':` of ${r.n} published`}`:`${r.exact?'':`공개 ${r.n}개 중 `}${r.tied?'공동 ':''}${r.rank}위`;
    const medal=r.medal&&r.medal!=='none'?(en?` · ${icons[r.medal]} ${scope} ${awards[r.medal]} range${r.fullField?'':' among published'}`:` · ${icons[r.medal]} ${scope} 기준 ${awards[r.medal]}권${r.fullField?'':'(공개 점수 기준)'}`):'';
    return ` <small class="hlcr-round-note" data-round-medal="${esc(r.medal||'')}">(${esc(rank+medal)})</small>`;
  }
  function resultHtml(e, lang) {
    if (!e) return '';
    const en = lang === 'en', r = e.record, awards = names[en?'en':'ko'];
    const reference=e.reference,shownMedal=e.medal||reference?.medal;
    const scopeName=r.scope==='theory'?(en?'Theory':'이론'):r.scope==='experiment'?(en?'Experiment':'실험'):(en?'Round':'라운드');
    const population = r.population === 'team' ? (en?'teams':'팀') : (en?'contestants':'명');
    const title = label(r.label,lang) || r.scope;
    const cutLabel = reference?(en?`${scopeName} medal bands · reference`:`${scopeName} 기준 메달권 컷 · 참고`):r.cutoffKind === 'observed' ? (en?'Award-winning scores · reference':'수상자 최저점 · 참고') : (en?'Medal cutoffs':'메달 컷');
    const cutEntries = Object.entries(reference?.cuts||r.medalCutoffs || {}).filter(([k,v]) => awards[k] && finite(v));
    const cuts = cutEntries.map(([k,v]) => `<span class="hlcr-cut" data-tier="${k}"><i aria-hidden="true"></i>${esc(awards[k])} ${!reference&&r.medalCutoffRule==='gt'?'>':'≥'} ${fmt(v)}</span>`).join('');
    let medal = '';
    if(reference){
      medal=reference.medal==='none'?(en?`${scopeName} · below medal bands (reference)`:`${scopeName} 기준 메달권 밖 · 참고`):
        (en?`${scopeName} · ${awards[reference.medal]} range (reference)`:`${scopeName} 기준 ${awards[reference.medal]}권 · 참고`);
    }else if (e.medal) {
      const observed = r.cutoffKind === 'observed';
      medal = e.medal === 'none' ? (en?'Below verified cutoffs':'확인된 수상컷 미달') : `${awards[e.medal]}${en ? (observed?' range · reference':' threshold met') : (observed?' 점수대 · 참고':' 기준 충족')}`;
    }
    const icons={gold:'🥇',silver:'🥈',bronze:'🥉',hm:'🏅'};
    const component=r.scope==='theory'||r.scope==='experiment',fieldCount=r.participantCountUncertain||!Number.isInteger(r.participants)?'':String(r.participants);
    const context=e.bounded?(en?(fieldCount?`Full field · ${fieldCount} ${population}`:'Full-field rank'):(fieldCount?`전체 ${fieldCount}${population} 기준`:'전체 참가자 기준')):

      e.complete?(en?`${e.n} ${population} in the score table`:`전체 ${e.n}${population} 성적 기준`):
      (en?`Among ${e.n} published scores`:`${e.n}개 공개 점수 중`);
    const limitations=[
      e.bounded&&component?(en?`Every contestant whose score is unpublished had a total below ${fmt(e.coverage.floor)} (the lowest award), so their ${scopeName.toLowerCase()} score was lower too. At or above ${fmt(e.coverage.floor)} this ${scopeName.toLowerCase()} rank is therefore exact in the whole field.`:
        `점수가 공개되지 않은 참가자는 모두 총점이 최저 수상점 ${fmt(e.coverage.floor)}점 미만이므로 ${scopeName} 점수도 그보다 낮습니다. 따라서 ${scopeName} ${fmt(e.coverage.floor)}점 이상은 전체 참가자 기준 순위가 확정됩니다.`):
      e.bounded?(en?`All totals at or above ${fmt(r.rankFloor)} (the lowest award) are published, so this rank is exact in the whole field.`:`최저 수상점 ${fmt(r.rankFloor)}점 이상의 총점은 모두 공개되어 전체 참가자 기준 순위가 확정됩니다.`):null,
      !e.complete&&!e.bounded&&e.n&&e.coverage?(en?`Below ${fmt(e.coverage.floor)} points unpublished scores may be higher, so the full-field rank is a lower bound only.`:`${fmt(e.coverage.floor)}점 미만에서는 비공개 점수가 더 높을 수 있어 전체 참가자 순위를 확정할 수 없습니다.`):
      !e.complete&&!e.bounded&&e.n?(en?'The full-field rank is unavailable.':'전체 참가자 순위는 확인할 수 없습니다.'):null,
      r.scope!=='total'&&!r.awardScope?(en?'This round alone does not determine the overall medal.':'이 라운드 점수만으로 실제 대회 메달이 정해지지는 않습니다.'):null,
      reference&&!reference.fullField?(en?`The ${awards[reference.medal]} band among published scores (cut ${fmt(reference.cuts[reference.medal])}) lies below ${fmt(reference.floor ?? 0)}; unpublished scores could raise that cut, so the band may be lower in the whole field.`:
        `공개 점수 기준 ${awards[reference.medal]}권 컷(${fmt(reference.cuts[reference.medal])}점)이 ${reference.floor!=null?`최저 수상점 ${fmt(reference.floor)}점보다 낮아`:'공개 범위 밖이라'} 비공개 점수가 포함되면 컷이 올라갈 수 있습니다. 전체 참가자 기준으로는 더 낮은 메달권일 수 있습니다.`):null,
      reference?(en?`The actual award counts (${reference.counts.gold} gold, ${reference.counts.silver} silver, ${reference.counts.bronze} bronze) are applied to scores ranked within this round. This is a round-specific reference, not an official medal allocation.`:
        `그해 실제 금·은·동메달 ${r.population==='team'?'팀 수':'인원'}(${reference.counts.gold}·${reference.counts.silver}·${reference.counts.bronze}${r.population==='team'?'팀':'명'})을 해당 라운드의 점수 순위에 적용했습니다. 라운드별 참고 메달권이며 공식 수상 결과는 아닙니다.`):null,
      r.cutoffKind==='observed'&&medal?(en?'Observed award-winning scores, not an official cutoff declaration. Eligibility and tie rules may apply.':'공식 컷 발표가 아닌 공개 수상 점수의 관측값입니다. 자격·동점 처리 등 다른 수상 규정은 별도로 적용됩니다.'):null,
      // The edition note describes the published-only distribution; above the floor the exact full-field rank replaces it.
      r.note&&!e.bounded?label(r.note,lang):null,
      e.bounded&&r.participantCountUncertain?(en?'Published entrant counts disagree, so no full-field percentile is shown.':'공개된 참가 인원 자료가 서로 달라 전체 백분위는 표시하지 않습니다.'):null
    ].filter(Boolean);
    const rankTitle=(r.scope==='total'||r.awardScope)?(en?'Overall score rank':'총합 기준 가상 순위'):(en?`${scopeName} score rank`:`${scopeName} 기준 가상 순위`);
    const sources=reference?{...r,sources:[...(r.sources||[]),...reference.sources].filter((s,i,a)=>a.findIndex(x=>x.url===s.url)===i)}:r;
    return `<article class="hlcr-result" data-comparison="${esc(r.id)}"${shownMedal?` data-medal="${esc(shownMedal)}" data-medal-basis="${reference?'round_rank':esc(r.cutoffKind||'published')}"`:''}>
      <div class="hlcr-result-head"><h4>${esc(title)} <span class="hlcr-score">${fmt(e.score)}${finite(r.max)?` / ${fmt(r.max)}`:''}</span></h4>
        ${medal?`<span class="hlcr-medal" data-medal="${esc(shownMedal)}">${icons[shownMedal]?`<span aria-hidden="true">${icons[shownMedal]}</span> `:''}${esc(medal)}</span>`:`<span class="hlcr-scope">${en?'Score comparison':'점수 비교'}</span>`}</div>
      ${e.combined?`<div class="hlcr-combined" data-combined="true"><b>${en?'Theory + experiment · automatically combined':'이론 + 실험 자동 합산'}</b><p>${e.combined.sessions.map(s=>`<a href="/#/lab/${s.id}">${esc(label(s.label,lang)||s.scope)} ${fmt(s.score)} / ${fmt(s.points)}</a>${roundNote(s,lang)}`).join(' + ')}</p><p class="hlcr-caption">${e.combined.mixedMode?(en?'Mixed timed and untimed records · reference total':'실전·시간 제한 없는 채점 기록을 합산한 참고 총점'):(en?'This result plus the latest matching result from the other round':'이번 성적표와 같은 모드의 최근 다른 라운드 성적을 합산했습니다.')}</p></div>`:''}
      ${e.n?`<div class="hlcr-result-line"><div class="hlcr-rank"><span>${esc(rankTitle)}</span> <strong>${e.rank==null?'—':`${en?'':e.tied?'공동 ':''}${e.rank}${en?'':'위'}`}</strong>${en&&e.tied?'<small>tied</small>':''}</div>
        ${e.rank!=null?`<span class="hlcr-context">${esc(context)}</span>`:''}
        ${e.top_pct==null?'':`<span class="hlcr-history-top">${en?'Top':'상위'} ${fmt(Math.round(e.top_pct*10)/10)}%</span>`}</div>`:''}
      ${finite(e.best)?`<p class="hlcr-best" data-best="${esc(e.best)}"><span>${esc(component?(en?`Best ${scopeName.toLowerCase()} score`:`${scopeName} 1위 점수`):(en?'Best score':'1위 점수'))}</span> <b>${fmt(e.best)}${finite(r.max)?` / ${fmt(r.max)}`:''}</b> <small>${e.score+EPS>=e.best?(en?'· at or above the best':'· 1위 점수 이상'):(en?`· ${fmt(Math.round((e.best-e.score)*100)/100)} below`:`· 1위와 ${fmt(Math.round((e.best-e.score)*100)/100)}점 차이`)}</small></p>`:''}
      ${!e.n?`<p class="hlcr-caption">${finite(e.best)||cutEntries.length?(en?`No public ranking · compared with ${[cutEntries.length?'the award thresholds':'',finite(e.best)?'the best score':''].filter(Boolean).join(' and ')}`:`순위표 미공개 · ${cutEntries.length&&finite(e.best)?'메달 컷과 1위 점수로':cutEntries.length?'메달 컷으로':'1위 점수로'} 비교`):(en?'Historical rank data unavailable':'순위 비교 자료 미확보')}</p>`:''}
      ${!e.complete&&!e.bounded&&e.n?`<p class="hlcr-caption">${e.coverage?(en?`Published scores only · full-field rank exact from ${fmt(e.coverage.floor)} points`:`공개 점수 기준 · ${fmt(e.coverage.floor)}점 이상부터 전체 순위 확정`):(en?'Published scores only · full-field rank unknown':'공개 점수 기준 · 전체 순위 미확인')}</p>`:''}
      ${e.bounded&&component?`<p class="hlcr-caption" data-full-field="true">${en?`Full-field ${scopeName.toLowerCase()} rank · every score at or above ${fmt(e.coverage.floor)} is published`:`전체 참가자 ${scopeName} 순위 · ${fmt(e.coverage.floor)}점 이상 점수는 모두 공개됨`}</p>`:''}
      ${reference?`<p class="hlcr-caption">${reference.population==='published'&&reference.fullField?(en?'Reference medal range on the full-field round ranking':`전체 참가자 ${scopeName} 순위 기준의 참고 메달권`):reference.population==='published'?(en?'Published scores only · reference medal range · may be lower in the full field':`공개 ${scopeName} 점수 기준의 참고 메달권 · 전체 기준으로는 낮아질 수 있음`):(en?'Reference medal range based on this round’s ranking':`${scopeName} 순위 기준의 참고 메달권`)}</p>`:r.scope!=='total'&&!r.awardScope?`<p class="hlcr-caption">${en?'Round score only · medal reference data unavailable':'해당 라운드만 비교 · 메달권 기준 자료 미확보'}</p>`:''}
      ${e.manual?`<p class="hlcr-caption hlcr-manual-note">${en?'Entered score · does not change your grade or HaslaLab standing':'직접 입력한 점수 · 채점 성적·HaslaLab 순위에 반영되지 않음'}</p>`:''}
      ${cuts?`<div class="hlcr-cuts"><span class="hlcr-cut-label">${esc(cutLabel)}</span>${cuts}</div>`:''}
      <details class="hlcr-details"><summary>${en?'Comparison details & sources':'비교 기준·출처'}</summary>
        ${e.manual?`<p>${en?'Reference comparison using your entered score; this does not change your graded result or HaslaLab sample.':'직접 입력한 점수의 참고 비교입니다. 채점 성적이나 HaslaLab 표본에는 반영되지 않습니다.'}</p>`:''}
        ${limitations.map(note=>`<p>${esc(note)}</p>`).join('')}${sourcesHtml(sources,lang)}</details>
    </article>`;
  }
  function sampleHtml(s, lang, combined = false) {
    const en = lang === 'en', x = s?.sample_standing;
    if (!hasScore(s)) return '';
    const known=x&&Number.isInteger(x.n)&&x.n>0, enough=known&&x.n>1;
    const pct=fmt(Math.round(1000*s.score/s.points)/10);
    const rank=known&&Number.isInteger(x.rank)&&x.rank>0?`${x.rank} <small>/ ${x.n}</small>`:'—';
    const cohort=(x?.cohort|| (s.review_only?'review':'timed'))==='review'?(en?'Untimed grading & feedback':'시간 제한 없는 채점·첨삭'):(en?'Timed attempts':'시간 제한 있는 실전 응시');
    const metric=(id,title,value,extra='')=>`<div class="hlcr-metric ${extra}" data-metric="${id}"><dt>${title}</dt><dd>${value}</dd></div>`;
    return `<div class="hlcr-summary" data-cohort="${esc(x?.cohort|| (s.review_only?'review':'timed'))}"><dl class="hlcr-metrics">
      ${metric('score',combined?(en?'This graded round':'이번 채점'):(en?'Total':'총점'),`${fmt(s.score)} <small>/ ${fmt(s.points)}</small>`,'hlcr-total')}
      ${metric('percentage',en?'Percentage':'득점률',`${pct}<small>%</small>`)}
      ${metric('rank',en?'HaslaLab rank':'HaslaLab 순위',rank)}
      ${metric('top',en?'HaslaLab top':'HaslaLab 상위',enough&&finite(x.top_pct)?`${fmt(x.top_pct)}<small>%</small>`:'—')}
      <div class="hlcr-metric hlcr-averages"><dt>${en?'Sample average / best':'표본 평균 / 최고'}</dt><dd><span data-metric="average">${enough&&finite(x.avg)?`${fmt(x.avg)}%`:'—'}</span><small> / </small><span data-metric="best">${enough&&finite(x.max)?`${fmt(x.max)}%`:'—'}</span></dd></div>
      </dl><p class="hlcr-caption">${esc(cohort)} · ${known?(en?`${x.n} in sample`:`표본 ${x.n}명`):(en?'Collecting comparable results':'비교 표본 수집 중')}${enough?(en?' · first graded attempt per person':' · 1인 첫 채점 기준'):(en?' · percentile available with 2+ comparable candidates':' · 2명 이상 모이면 상위 비율 표시')}${x?.first===false?(en?' · repeat attempt':' · 재응시 점수 비교'):''}</p></div>`;
  }
  function manualHtml(record, session, lang) {
    const en = lang === 'en', components = record.components || [];
    const matched = !record.manualOnly && components.find(c => matches({...c,taskSets:c.taskSets || []}, session));
    const componentForm = matched && components.length > 1 && Math.abs(components.reduce((n,c)=>n+c.max,0)-record.max)<EPS;
    const hasCuts=Object.keys(record.medalCutoffs||{}).length>0;
    const action=en?(hasCuts?'Check medal & rank':'Check rank'):(hasCuts?'메달·순위 확인':'순위 확인');
    const remaining=componentForm?components.filter(c=>c!==matched):[];
    const otherName=remaining.length===1?({theory:en?'theory':'이론',experiment:en?'experiment':'실험'}[remaining[0].id]||label(remaining[0].label,lang)||remaining[0].id):'';
    const summary=remaining.length===1?(en?`Add ${otherName} score · ${action}`:`${otherName} 점수 추가 · ${action}`):`${label(record.label,lang)} · ${action}`;
    const fields = componentForm ? components.map(c => `<label>${esc(label(c.label,lang)||c.id)} / ${fmt(c.max)}
      <input type="number" name="${esc(c.id)}" min="0" max="${c.max}" step="any" required${c===matched?` value="${session.score}" readonly aria-label="${en?'Current graded score':'이번 채점 점수'}"`:''}></label>`).join('') :
      `<label>${en?'Total on the official score scale':'공식 점수 체계의 총점'}${finite(record.max)?` / ${fmt(record.max)}`:''}<input type="number" name="total" min="0"${finite(record.max)?` max="${record.max}"`:''} step="any" required></label>`;
    return `<details class="hlcr-manual"><summary>${esc(summary)}</summary>
      <p class="hlcr-note">${componentForm?(en?'Enter the other round’s score to compare the overall total.':'다른 라운드 점수를 입력하면 전체 총점으로 비교합니다.'):(en?'This grading does not cover the complete competition score. Enter a total calculated on the official scale for a reference comparison.':'이번 채점은 대회 전체 점수 범위와 다릅니다. 공식 배점에 맞춘 총점을 직접 입력하면 참고 비교를 볼 수 있습니다.')}
      ${en?'Entered scores stay on this screen.':'입력 점수는 이 화면에서만 사용합니다.'}</p>
      <form data-result-record="${esc(record.id)}"><div class="hlcr-inputs">${fields}<button type="submit">${action}</button></div><p role="status" data-result-error></p></form><div data-manual-result="${esc(record.id)}"></div></details>`;
  }
  function coverageHtml(data, lang, hasEdition) {
    if (!data) return '';
    const en=lang==='en',coverage=data.coverage||{},note=label(coverage.limitations||coverage.note||coverage,lang);
    const years=[...new Set((data.records||[]).map(r=>String(r.year)))].sort((a,b)=>Number(b)-Number(a));
    const content=`${note?`<p class="hlcr-note">${esc(note)}</p>`:''}${years.length?`<p class="hlcr-note">${en?'Collected editions':'비교 자료 수록 연도'}: ${years.join(', ')}</p>`:''}${coverage.sources?.length?sourcesHtml(coverage,lang):''}`;
    if (!content) return '';
    return `<details class="hlcr-details hlcr-coverage"><summary>${en?'Available years & data notes':'수록 연도·자료 안내'}</summary>${content}</details>`;
  }
  const style = `<style>
.hlcr{--hlcr-line:var(--cm-line,var(--line,#dbe1e8));--hlcr-muted:var(--graphite,var(--muted,#657184));--hlcr-soft:var(--cm-soft,var(--panel,transparent));margin-top:14px;padding:0;text-align:left;color:inherit;min-width:0}
.hlcr *{box-sizing:border-box}.hlcr h3,.hlcr h4,.hlcr p,.hlcr dl,.hlcr dd{margin:0}.hlcr h3{font-size:14px}.hlcr h4{font-size:13px;font-weight:700}.hlcr p{line-height:1.6}
.hlcr .hlcr-metrics{display:grid;grid-template-columns:1.15fr 1fr 1fr 1fr 1.35fr;border:1px solid var(--hlcr-line);border-radius:10px;overflow:hidden;margin:0}
.hlcr-metric{min-width:0;padding:14px 16px;border-right:1px solid var(--hlcr-line)}.hlcr-metric:last-child{border-right:0}.hlcr-metric dt{font-size:11.5px;line-height:1.4;color:var(--hlcr-muted);margin-bottom:6px}.hlcr-metric dd{font:700 25px/1.3 var(--mono,ui-monospace,SFMono-Regular,Consolas,monospace);letter-spacing:-.04em;white-space:nowrap}.hlcr-metric dd small{font-size:15px;font-weight:500;letter-spacing:-.02em;color:var(--hlcr-muted)}.hlcr-total dd{font-size:29px}.hlcr-averages dd{font-size:18px;line-height:1.8;letter-spacing:-.04em}
.hlcr .hlcr-caption,.hlcr-note,.hlcr-source{font-size:11.5px;color:var(--hlcr-muted)}.hlcr-summary>.hlcr-caption{margin:7px 2px 14px}.hlcr-section-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:12px 0 8px}.hlcr-section-head>span{font-size:11px;color:var(--hlcr-muted)}
.hlcr-result{--medal-bg:#eef1f5;--medal-fg:#4d5967;--medal-line:var(--hlcr-line);border:1px solid var(--medal-line);border-left:3px solid var(--medal-line);border-radius:9px;padding:12px 14px;margin:8px 0}
.hlcr [data-medal="gold"]{--medal-bg:#fff2bc;--medal-fg:#705300;--medal-line:#d4b45b}.hlcr [data-medal="silver"]{--medal-bg:#edf1f6;--medal-fg:#46556a;--medal-line:#aebbc9}.hlcr [data-medal="bronze"]{--medal-bg:#f7e5d8;--medal-fg:#804728;--medal-line:#cd9b79}.hlcr [data-medal="hm"]{--medal-bg:#e8f0ff;--medal-fg:#315b96;--medal-line:#9db8dd}
.hlcr-result-head{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:7px 12px}.hlcr-score{font-weight:500;color:var(--hlcr-muted);margin-left:7px;white-space:nowrap}.hlcr-medal,.hlcr-scope{display:inline-flex;align-items:center;gap:5px;border-radius:999px;padding:4px 10px;font-size:12px;font-weight:700;line-height:1.4}.hlcr-medal{background:var(--medal-bg);color:var(--medal-fg);border:1px solid var(--medal-line)}.hlcr-scope{background:var(--hlcr-soft);color:var(--hlcr-muted);border:1px solid var(--hlcr-line)}
.hlcr-result-line{display:flex;align-items:baseline;gap:8px 12px;flex-wrap:wrap;margin:8px 0 3px}.hlcr-rank{display:flex;align-items:baseline;gap:9px}.hlcr-rank>span{font-size:12px;color:var(--hlcr-muted)}.hlcr-rank strong{font:700 23px/1.3 var(--mono,ui-monospace,SFMono-Regular,Consolas,monospace);letter-spacing:-.04em}.hlcr-rank small,.hlcr-context,.hlcr-history-top{font-size:12px;color:var(--hlcr-muted)}.hlcr-history-top{margin-left:auto;font-weight:700}.hlcr-manual-note{margin-top:3px!important}
.hlcr-cuts{display:flex;align-items:center;flex-wrap:wrap;gap:5px 12px;margin-top:9px;font-size:11.5px}.hlcr-cut-label{color:var(--hlcr-muted)}.hlcr-cut{display:inline-flex;align-items:center;gap:5px;white-space:nowrap}.hlcr-cut i{display:inline-block;width:7px;height:7px;border-radius:50%;background:#8099bd}.hlcr-cut[data-tier="gold"] i{background:#bd912c}.hlcr-cut[data-tier="silver"] i{background:#8b9eb2}.hlcr-cut[data-tier="bronze"] i{background:#b27850}
.hlcr-details{font-size:11.5px;color:var(--hlcr-muted);margin-top:9px}.hlcr-details summary{font-size:11.5px;font-weight:500}.hlcr-details[open]{border-top:1px dashed var(--hlcr-line);padding-top:8px}.hlcr-details p{margin:7px 0}.hlcr-source{margin-top:8px}.hlcr-source a{color:inherit;text-decoration:underline;text-underline-offset:2px}.hlcr summary{cursor:pointer;line-height:1.5}.hlcr-coverage{margin-top:12px}
.hlcr-manual{border:1px dashed var(--hlcr-line);border-radius:9px;background:var(--hlcr-soft);padding:10px 13px;margin:8px 0}.hlcr-manual>summary{font-size:12.5px;font-weight:650}.hlcr-manual>.hlcr-note{margin-top:9px}.hlcr-inputs{display:flex;align-items:flex-end;gap:10px 12px;flex-wrap:wrap;margin-top:10px}.hlcr label{display:flex;flex-direction:column;gap:5px;font-size:12px;max-width:100%;font-weight:600}.hlcr input{font:inherit;color:inherit;background:transparent;border:1px solid var(--hlcr-line);border-radius:6px;padding:8px 10px;width:146px;max-width:100%}.hlcr input[readonly]{opacity:.65}.hlcr button{font:inherit;font-size:12.5px;font-weight:700;color:inherit;background:transparent;border:1px solid var(--hlcr-line);border-radius:6px;padding:8px 12px;cursor:pointer}.hlcr input:focus,.hlcr button:focus-visible,.hlcr summary:focus-visible{outline:2px solid var(--accent,#637d9e);outline-offset:3px}.hlcr [data-result-error]{font-size:12px;color:#bd3d35;margin-top:5px}.hlcr [data-result-error]:empty{display:none}
.hlcr-empty{border:1px solid var(--hlcr-line);border-radius:9px;padding:11px 13px;margin:8px 0;font-size:12px}.hlcr-empty p{font-size:12px;color:var(--hlcr-muted);margin-top:3px}.hlcr-footer{font-size:11px;color:var(--hlcr-muted);margin-top:9px!important}
.hlcr-averages dd{display:flex;align-items:baseline;flex-wrap:wrap;gap:0 4px;white-space:normal;line-height:1.5;padding-top:2px}
.hlcr-combined{margin:9px 0 7px;padding-bottom:8px;border-bottom:1px dashed var(--hlcr-line);font-size:12px}.hlcr-combined p{margin-top:4px}.hlcr-combined a{color:inherit;text-decoration:underline;text-underline-offset:3px}.hlcr-best{margin:2px 0 4px;font-size:12px;color:var(--hlcr-muted)}.hlcr-best b{color:var(--hlcr-ink,inherit);font-weight:650}.hlcr-round-note{font-size:11px;opacity:.78;white-space:nowrap}
@media(max-width:760px){.hlcr .hlcr-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.hlcr-total{grid-column:1/-1;border-bottom:1px solid var(--hlcr-line);border-right:0}.hlcr-metric{padding:11px 13px}.hlcr-metric:nth-child(2),.hlcr-metric:nth-child(3){border-bottom:1px solid var(--hlcr-line)}.hlcr-metric:nth-child(3){border-right:0}.hlcr-metric dd{font-size:23px}.hlcr-total dd{font-size:28px}.hlcr-averages dd{font-size:17px;line-height:1.75}.hlcr-result{padding:11px 12px}.hlcr-result-head{align-items:flex-start}.hlcr-history-top{margin-left:0}.hlcr-section-head{align-items:flex-start}.hlcr-section-head>span{text-align:right}.hlcr-inputs>*{flex:1 1 125px}.hlcr input{width:100%}.hlcr-inputs>button{flex-grow:0}.hlcr-rank strong{font-size:22px}}
@media print{.hlcr{--hlcr-line:#bbb;--hlcr-muted:#444;--hlcr-soft:#fff;color:#111}.hlcr-result,.hlcr-metrics{break-inside:avoid}.hlcr-medal{color:#111;border-color:#888}.hlcr input,.hlcr button{color:#111}.hlcr-coverage{display:none}}
</style>`;
  function html(data, session, lang, loading = false) {
    if (!hasScore(session)) return '';
    const en = lang === 'en', a = assess(data,session);
    const explanation = a.comparisons.length ? '' : a.scaleMismatch ?
      (en?'The grading scale differs from the official scale. Enter an official-scale total below to compare.':'채점 배점이 공식 배점과 달라요. 아래에 공식 총점을 입력하면 비교할 수 있어요.') : a.records.length ?
      (en?'This grade covers only part of the competition. Partial scores are not scaled to the full paper; compare a complete total below.':'대회 전체 점수로 비교해야 해요. 일부 문제 점수를 전체 총점으로 환산하지 않습니다.') :
      (en?'Verified comparison data for this year have not yet been collected.':'해당 연도의 비교 자료를 아직 확보하지 못했습니다.');
    return `${style}<section class="hlcr" aria-label="${en?'Score summary and competition comparison':'성적 요약·대회 비교'}">
      ${sampleHtml(session,lang,a.comparisons.some(e=>e.combined))}<div class="hlcr-section-head"><h3>${en?'Competition comparison':'실제 대회와 비교'}</h3><span>${esc(session.comp.toUpperCase())} ${esc(session.year)} · ${en?'reference':'참고 결과'}</span></div>
      ${loading?`<div class="hlcr-empty">${en?'Loading published results…':'대회 성적을 불러오는 중…'}</div>`:a.comparisons.map(e=>resultHtml(e,lang)).join('')+(explanation?`<div class="hlcr-empty">${esc(explanation)}</div>`:'')+a.totals.map(r=>manualHtml(r,session,lang)).join('')+coverageHtml(data,lang,a.records.length>0)}
      <p class="hlcr-footer">${en?'Practice-score reference · not an official competition result.':'학습용 채점에 따른 참고 비교이며 실제 대회의 공식 성적·수상을 뜻하지 않습니다.'}</p></section>`;
  }
  async function load(comp, base = 'sim/results/') {
    if (!/^[a-z]+$/.test(comp || '')) return null;
    const url = base + comp + '.json';
    if (!pending.has(url)) pending.set(url, fetch(url,{cache:'no-cache'}).then(async r => {
      if (!r.ok) throw Error('results_unavailable');
      const data = await r.json();
      if (data.schema !== 1 || data.comp !== comp || !Array.isArray(data.records)) throw Error('invalid_results');
      return data;
    }).catch(() => { pending.delete(url); return null; }));
    return pending.get(url);
  }
  async function mount(host, session, lang = 'ko', options = {}) {
    if (!host || !hasScore(session)) return;
    const current = () => options.isCurrent ? options.isCurrent() : host.isConnected !== false;
    host.innerHTML = html(null,session,lang,true);
    const data = await load(session.comp,options.base);
    if (!current()) return;
    host.innerHTML = html(data,session,lang);
    for (const form of host.querySelectorAll('form[data-result-record]')) {
      form.addEventListener('submit', event => {
        event.preventDefault();
        const record = data.records.find(r => r.id === form.dataset.resultRecord);
        const inputs = [...form.querySelectorAll('input[type="number"]')];
        const values = inputs.map(i => i.value.trim() === '' ? NaN : Number(i.value));
        const error = form.querySelector('[data-result-error]');
        if (values.some((v,i) => !finite(v) || v < 0 || inputs[i].max!=='' && v > Number(inputs[i].max) + EPS)) {
          error.textContent = lang === 'en' ? 'Enter every score within its published range.' : '각 점수를 공개 배점 범위 안에서 입력하세요.'; return;
        }
        error.textContent = '';
        const result = evaluate(record,values.reduce((n,v)=>n+v,0),true);
        const target = [...host.querySelectorAll('[data-manual-result]')].find(n => n.dataset.manualResult === record.id);
        if (target) target.innerHTML = resultHtml(result,lang);
      });
    }
  }
  return {hasScore, taskKey, matches, componentFloor, roundReference, combinedResults, evaluate, assess, sampleHtml, resultHtml, html, load, mount};
});
