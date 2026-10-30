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
  const hasScore = s => s?.status === 'graded' && validScore(s.score, s.points) &&
    !Object.values(s.detail?.tasks || {}).some(t => t.grading_mode === 'qualitative_review');
  function matches(record, session) {
    return !record.manualOnly && hasScore(session) && Math.abs(session.points - record.max) < EPS &&
      record.taskSets?.some(tasks => taskKey(tasks) === taskKey(session.tasks));
  }
  function evaluate(record, score, manual = false) {
    if (!record || record.manualOnly && !manual || !validReference(record,score)) return null;
    const scores = (record.scores || []).filter(x => validReference(record,x));
    const above = scores.filter(x => x > score + EPS).length;
    const tied = scores.filter(x => Math.abs(x - score) <= EPS).length;
    const complete = record.complete === true && scores.length > 0 && record.participants === scores.length;
    // Missing totals can affect rank only below a source-verified coverage floor.
    // This inference never applies to an individual round of a combined contest.
    const bounded = !complete && scores.length > 0 && record.scope === 'total' && finite(record.rankFloor) &&
      score + EPS >= record.rankFloor && Number.isInteger(record.participants) && record.participants >= scores.length;
    const fieldSize = complete || bounded ? record.participants : scores.length;
    let medal = null;
    if (record.awardScope === true) {
      const cuts = record.medalCutoffs || {};
      medal = ['gold','silver','bronze','hm'].find(k => finite(cuts[k]) &&
        (record.medalCutoffRule === 'gt' ? score > cuts[k] + EPS : score + EPS >= cuts[k])) ||
        (Object.keys(cuts).length ? 'none' : null);
    }
    return {record, score, manual, n:scores.length, rank:scores.length ? above + 1 : null,
      tied, complete, bounded, fieldSize, top_pct:(complete||bounded) && fieldSize > 1 && !record.participantCountUncertain ? Math.min(100,100 * (above + 1) / fieldSize) : null, medal};
  }
  function assess(data, session) {
    if (!hasScore(session)) return {records:[], comparisons:[], totals:[]};
    const records = (data?.comp === session.comp ? data.records || [] : []).filter(r => String(r.year) === String(session.year));
    return {records, scaleMismatch:records.some(r=>r.taskSets?.some(tasks=>taskKey(tasks)===taskKey(session.tasks))&&Math.abs(session.points-r.max)>=EPS),
      comparisons:records.filter(r => matches(r, session)).map(r => evaluate(r, session.score)),
      totals:records.filter(r => (r.scope==='total'||r.awardScope) && (r.medalCutoffs||r.scores?.length) && !matches(r, session))};
  }
  const names = {
    ko:{gold:'금메달',silver:'은메달',bronze:'동메달',hm:'장려상',none:'공개 수상 기준 미달'},
    en:{gold:'Gold',silver:'Silver',bronze:'Bronze',hm:'Honourable mention',none:'Below published award thresholds'}
  };
  function sourcesHtml(record, lang) {
    const en = lang === 'en';
    const sources=(record.sources || []).filter(s => /^https?:\/\//.test(s.url));
    const links=sources.map(s => {
      const title=label(s.title,lang) || (en?'Source':'출처');
      return `<a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(title)}${s.official===false&&!/unofficial|비공식/i.test(title)?(en?' (unofficial)':' (비공식)'):''} ↗</a>`;
    }).join(' · ');
    return `<div class="hlcr-source"><b>${en?'Data sources':'자료 출처'}${sources.some(s=>s.official===false)?(en?' · includes unofficial records':' · 비공식 기록 포함'):''}</b><p>${links}</p></div>`;
  }
  function resultHtml(e, lang) {
    if (!e) return '';
    const en = lang === 'en', r = e.record, awards = names[en?'en':'ko'];
    const population = r.population === 'team' ? (en?'teams':'팀') : (en?'contestants':'명');
    const title = label(r.label,lang) || r.scope;
    const cutLabel = r.cutoffKind === 'observed' ? (en?'Award-winning scores · reference':'수상자 최저점 · 참고') : (en?'Medal cutoffs':'메달 컷');
    const cutEntries = Object.entries(r.medalCutoffs || {}).filter(([k,v]) => awards[k] && finite(v));
    const cuts = cutEntries.map(([k,v]) => `<span class="hlcr-cut" data-tier="${k}"><i aria-hidden="true"></i>${esc(awards[k])} ${r.medalCutoffRule==='gt'?'>':'≥'} ${fmt(v)}</span>`).join('');
    let medal = '';
    if (e.medal) {
      const observed = r.cutoffKind === 'observed';
      medal = e.medal === 'none' ? (en?'Below verified cutoffs':'확인된 수상컷 미달') : `${awards[e.medal]}${en ? (observed?' range · reference':' threshold met') : (observed?' 점수대 · 참고':' 기준 충족')}`;
    }
    const icons={gold:'🥇',silver:'🥈',bronze:'🥉',hm:'🏅'};
    const context=e.bounded?(en?'Within the fully published score range':'순위 확인이 가능한 점수 범위'):
      e.complete?(en?`${e.n} ${population} in the score table`:`전체 ${e.n}${population} 성적 기준`):
      (en?`Among ${e.n} published scores`:`${e.n}개 공개 점수 중`);
    const limitations=[
      e.bounded?(en?'All scores above this published coverage floor are available.':'이 점수 이상의 기록이 모두 공개되어 가상 순위를 계산할 수 있습니다.'):null,
      !e.complete&&!e.bounded&&e.n?(en?'The full-field rank is unavailable.':'전체 참가자 순위는 확인할 수 없습니다.'):null,
      r.scope!=='total'&&!r.awardScope?(en?'This round alone does not determine the overall medal.':'이 라운드 점수만으로 실제 대회 메달이 정해지지는 않습니다.'):null,
      r.cutoffKind==='observed'&&medal?(en?'Observed award-winning scores, not an official cutoff declaration. Eligibility and tie rules may apply.':'공식 컷 발표가 아닌 공개 수상 점수의 관측값입니다. 자격·동점 처리 등 다른 수상 규정은 별도로 적용됩니다.'):null,
      r.note?label(r.note,lang):null
    ].filter(Boolean);
    return `<article class="hlcr-result" data-comparison="${esc(r.id)}"${e.medal?` data-medal="${esc(e.medal)}"`:''}>
      <div class="hlcr-result-head"><h4>${esc(title)} <span class="hlcr-score">${fmt(e.score)}${finite(r.max)?` / ${fmt(r.max)}`:''}</span></h4>
        ${medal?`<span class="hlcr-medal" data-medal="${esc(e.medal)}">${icons[e.medal]?`<span aria-hidden="true">${icons[e.medal]}</span> `:''}${esc(medal)}</span>`:`<span class="hlcr-scope">${en?'Score comparison':'점수 비교'}</span>`}</div>
      <div class="hlcr-result-line"><div class="hlcr-rank"><span>${en?'Historical score rank':'대회 가상 순위'}</span> <strong>${e.rank==null?'—':`${en?'':e.tied?'공동 ':''}${e.rank}${en?'':'위'}`}</strong>${en&&e.tied?'<small>tied</small>':''}</div>
        ${e.rank!=null?`<span class="hlcr-context">${esc(context)}</span>`:''}
        ${e.top_pct==null?'':`<span class="hlcr-history-top">${en?'Top':'상위'} ${fmt(Math.round(e.top_pct*10)/10)}%</span>`}</div>
      ${!e.n?`<p class="hlcr-caption">${en?'Historical rank data unavailable':'순위 비교 자료 미확보'}</p>`:''}
      ${!e.complete&&!e.bounded&&e.n?`<p class="hlcr-caption">${en?'Published scores only · full-field rank unknown':'공개 점수 기준 · 전체 순위 미확인'}</p>`:''}
      ${r.scope!=='total'&&!r.awardScope?`<p class="hlcr-caption">${en?'Round score only · medals use the overall total':'해당 라운드만 비교 · 메달은 전체 총점으로 결정'}</p>`:''}
      ${e.manual?`<p class="hlcr-caption hlcr-manual-note">${en?'Entered score · does not change your grade or HaslaLab standing':'직접 입력한 점수 · 채점 성적·HaslaLab 순위에 반영되지 않음'}</p>`:''}
      ${cuts?`<div class="hlcr-cuts"><span class="hlcr-cut-label">${esc(cutLabel)}</span>${cuts}</div>`:''}
      <details class="hlcr-details"><summary>${en?'Comparison details & sources':'비교 기준·출처'}</summary>
        ${e.manual?`<p>${en?'Reference comparison using your entered score; this does not change your graded result or HaslaLab sample.':'직접 입력한 점수의 참고 비교입니다. 채점 성적이나 HaslaLab 표본에는 반영되지 않습니다.'}</p>`:''}
        ${limitations.map(note=>`<p>${esc(note)}</p>`).join('')}${sourcesHtml(r,lang)}</details>
    </article>`;
  }
  function sampleHtml(s, lang) {
    const en = lang === 'en', x = s?.sample_standing;
    if (!hasScore(s)) return '';
    const known=x&&Number.isInteger(x.n)&&x.n>0, enough=known&&x.n>1;
    const pct=fmt(Math.round(1000*s.score/s.points)/10);
    const rank=known&&Number.isInteger(x.rank)&&x.rank>0?`${x.rank} <small>/ ${x.n}</small>`:'—';
    const cohort=(x?.cohort|| (s.review_only?'review':'timed'))==='review'?(en?'Untimed grading & feedback':'시간 제한 없는 채점·첨삭'):(en?'Timed attempts':'시간 제한 있는 실전 응시');
    const metric=(id,title,value,extra='')=>`<div class="hlcr-metric ${extra}" data-metric="${id}"><dt>${title}</dt><dd>${value}</dd></div>`;
    return `<div class="hlcr-summary" data-cohort="${esc(x?.cohort|| (s.review_only?'review':'timed'))}"><dl class="hlcr-metrics">
      ${metric('score',en?'Total':'총점',`${fmt(s.score)} <small>/ ${fmt(s.points)}</small>`,'hlcr-total')}
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
      ${sampleHtml(session,lang)}<div class="hlcr-section-head"><h3>${en?'Competition comparison':'실제 대회와 비교'}</h3><span>${esc(session.comp.toUpperCase())} ${esc(session.year)} · ${en?'reference':'참고 결과'}</span></div>
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
  return {hasScore, taskKey, matches, evaluate, assess, sampleHtml, resultHtml, html, load, mount};
});
