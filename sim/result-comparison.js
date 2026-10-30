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
    return `<details class="hlcr-source"><summary>${en?'Data sources':'자료 출처'}${sources.some(s=>s.official===false)?(en?' · includes unofficial records':' · 비공식 기록 포함'):''}</summary><p>${links}</p></details>`;
  }
  function resultHtml(e, lang) {
    if (!e) return '';
    const en = lang === 'en', r = e.record, awards = names[en?'en':'ko'];
    const population = r.population === 'team' ? (en?'teams':'팀') : (en?'contestants':'명');
    const title = label(r.label,lang) || r.scope;
    const rank = e.rank == null ? '' : e.bounded ?
      (en ? `Hypothetical score rank ${e.rank}. All scores above this published coverage floor are available.` : `가상 ${e.rank}위입니다. 이 점수 이상의 기록이 모두 공개된 범위에서 계산했습니다.`) : e.complete ?
      (en ? `Against ${e.n} published ${population}: hypothetical score rank ${e.rank}${e.tied?' (tied)':''}.` : `실제 대회 ${e.n}${population}의 점수를 기준으로 가상 ${e.tied?'공동 ':''}${e.rank}위입니다.`) :
      (en ? `Position among ${e.n} published scores: ${e.rank}${e.tied?' (tied)':''}. The full-field rank is unavailable.` : `공개 점수 ${e.n}개 중 ${e.tied?'공동 ':''}${e.rank}위입니다. 전체 참가자 순위는 확인할 수 없습니다.`);
    const cutLabel = r.cutoffKind === 'observed' ? (en?'Lowest published award-winning scores':'공개 수상자 최저 점수') : (en?'Published award thresholds':'공개 수상 기준');
    const cuts = Object.entries(r.medalCutoffs || {}).filter(([k,v]) => awards[k] && finite(v))
      .map(([k,v]) => `${awards[k]} ${r.medalCutoffRule==='gt'?'>':'≥'} ${fmt(v)}`).join(' · ');
    let medal = '';
    if (e.medal) {
      const observed = r.cutoffKind === 'observed';
      medal = e.medal === 'none' ? awards.none : `${awards[e.medal]}${en ? (observed?' score range (reference)':' threshold met') : (observed?' 점수대 (참고)':' 기준 충족')}`;
    }
    return `<article class="hlcr-result" data-comparison="${esc(r.id)}"${e.medal?` data-medal="${esc(e.medal)}"`:''}>
      <h4>${esc(title)} · ${fmt(e.score)}${finite(r.max)?` / ${fmt(r.max)}`:''}</h4>
      ${e.manual?`<p class="hlcr-note">${en?'Reference comparison using your entered score; this does not change your graded result or HaslaLab sample.':'직접 입력한 점수의 참고 비교입니다. 채점 성적이나 HaslaLab 표본에는 반영되지 않습니다.'}</p>`:''}
      ${medal?`<p class="hlcr-award">${esc(medal)}</p>`:''}
      ${rank?`<p>${esc(rank)}${e.top_pct==null?'':` ${en?'Top':'상위'} ${fmt(Math.round(e.top_pct*10)/10)}%.`}</p>`:''}
      ${!e.n?`<p class="hlcr-note">${en?'A verified score distribution is unavailable, so a historical rank cannot be calculated.':'검증된 점수 분포가 없어 실제 대회 순위는 계산할 수 없습니다.'}</p>`:''}
      ${cuts?`<p class="hlcr-note">${esc(cutLabel)}: ${esc(cuts)}</p>`:''}
      ${r.scope==='total'&&!cuts?`<p class="hlcr-note">${en?'No verified score-based award threshold is available in this dataset; only score position is compared.':'확인된 점수 기반 수상 기준이 없어 점수 순위만 비교합니다.'}</p>`:''}
      ${r.scope!=='total'&&!r.awardScope?`<p class="hlcr-note">${en?'This round alone does not determine the overall medal.':'이 라운드 점수만으로 실제 대회 메달이 정해지지는 않습니다.'}</p>`:''}
      ${r.cutoffKind==='observed'&&medal?`<p class="hlcr-note">${en?'These are observed award-winning scores, not an official cutoff declaration. Other eligibility and tie rules may apply.':'공식 컷 발표가 아닌 공개 수상 점수의 관측값입니다. 자격·동점 처리 등 다른 수상 규정은 별도로 적용됩니다.'}</p>`:''}
      ${r.note?`<p class="hlcr-note">${esc(label(r.note,lang))}</p>`:''}
      ${sourcesHtml(r,lang)}
    </article>`;
  }
  function sampleHtml(s, lang) {
    const en = lang === 'en', x = s?.sample_standing;
    if (!hasScore(s)) return '';
    if (!x || !Number.isInteger(x.n) || x.n < 1) return `<article class="hlcr-result"><h4>${en?'HaslaLab sample':'HaslaLab 표본'}</h4><p>${en?'No comparable sample is available yet.':'비교 가능한 표본이 아직 없습니다.'}</p></article>`;
    const cohort = x.cohort === 'review' ? (en?'Untimed grading & feedback':'시간 제한 없는 채점·첨삭') : (en?'Timed attempts':'시간 제한 있는 실전 응시');
    const placement = x.n < 2 || !finite(x.top_pct) ?
      (en ? `Sample: ${x.n}. More comparable candidates are needed to report a percentile.` : `현재 표본 ${x.n}명입니다. 상위 비율을 표시하려면 비교 표본이 더 필요합니다.`) :
      (en ? `Rank ${x.rank} of ${x.n} · Top ${fmt(x.top_pct)}%` : `${x.n}명 중 ${x.rank}위 · 상위 ${fmt(x.top_pct)}%`);
    return `<article class="hlcr-result" data-cohort="${esc(x.cohort)}"><h4>${en?'HaslaLab sample':'HaslaLab 표본'}</h4>
      <p><b>${esc(placement)}</b></p><p class="hlcr-note">${esc(cohort)} · ${en?'Same contest, year, tasks and marking scale; one first graded attempt per person. Ties share a rank.':'같은 대회·연도·문항·배점의 1인 첫 채점 기준입니다. 동점은 같은 순위로 계산합니다.'}</p>
      ${x.first===false?`<p class="hlcr-note">${en?'This repeat attempt is compared with other candidates’ first graded attempts.':'이번 재응시 점수를 다른 응시자의 첫 채점 결과와 비교했습니다.'}</p>`:''}</article>`;
  }
  function manualHtml(record, session, lang) {
    const en = lang === 'en', components = record.components || [];
    const matched = !record.manualOnly && components.find(c => matches({...c,taskSets:c.taskSets || []}, session));
    const componentForm = matched && components.length > 1 && Math.abs(components.reduce((n,c)=>n+c.max,0)-record.max)<EPS;
    const fields = componentForm ? components.map(c => `<label>${esc(label(c.label,lang)||c.id)} / ${fmt(c.max)}
      <input type="number" name="${esc(c.id)}" min="0" max="${c.max}" step="any" required${c===matched?` value="${session.score}" readonly aria-label="${en?'Current graded score':'이번 채점 점수'}"`:''}></label>`).join('') :
      `<label>${en?'Total on the official score scale':'공식 점수 체계의 총점'}${finite(record.max)?` / ${fmt(record.max)}`:''}<input type="number" name="total" min="0"${finite(record.max)?` max="${record.max}"`:''} step="any" required></label>`;
    return `<details class="hlcr-manual"><summary>${esc(label(record.label,lang))} · ${en?'Compare a combined / entered total':'합산·총점 입력으로 비교'}</summary>
      <p class="hlcr-note">${componentForm?(en?'Enter the other round’s score to compare the overall total.':'다른 라운드 점수를 입력하면 전체 총점으로 비교합니다.'):(en?'This grading does not cover the complete competition score. Enter a total calculated on the official scale for a reference comparison.':'이번 채점은 대회 전체 점수 범위와 다릅니다. 공식 배점에 맞춘 총점을 직접 입력하면 참고 비교를 볼 수 있습니다.')}
      ${en?'Entered scores stay on this screen.':'입력 점수는 이 화면에서만 사용합니다.'}</p>
      <form data-result-record="${esc(record.id)}"><div class="hlcr-inputs">${fields}</div><button type="submit">${en?'Compare total':'총점 비교'}</button><p role="status" data-result-error></p></form><div data-manual-result="${esc(record.id)}"></div></details>`;
  }
  function coverageHtml(data, lang, hasEdition) {
    if (!data) return '';
    const en=lang==='en',coverage=data.coverage||{},note=label(coverage.limitations||coverage.note||coverage,lang);
    const years=[...new Set((data.records||[]).map(r=>String(r.year)))].sort((a,b)=>Number(b)-Number(a));
    const content=`${note?`<p class="hlcr-note">${esc(note)}</p>`:''}${years.length?`<p class="hlcr-note">${en?'Collected editions':'비교 자료 수록 연도'}: ${years.join(', ')}</p>`:''}${coverage.sources?.length?sourcesHtml(coverage,lang):''}`;
    if (!content) return '';
    return hasEdition?`<details class="hlcr-source"><summary>${en?'Coverage and limitations':'수록 범위·비교 제한'}</summary>${content}</details>`:content;
  }
  const style = `<style>.hlcr{margin-top:18px;border-top:1px solid var(--line,#7775);padding-top:14px;text-align:left}.hlcr h3{font-size:17px;margin:0 0 10px}.hlcr h4{font-size:14px;margin:0 0 6px}.hlcr p{margin:6px 0;line-height:1.6}.hlcr-result,.hlcr-manual{border:1px solid var(--line,#7775);border-radius:10px;padding:12px;margin:10px 0}.hlcr-note,.hlcr-source{font-size:12px;color:var(--muted,inherit)}.hlcr-award{font-weight:700}.hlcr-source a{color:inherit;text-decoration:underline}.hlcr-inputs{display:flex;gap:12px;flex-wrap:wrap;margin:10px 0}.hlcr label{display:flex;flex-direction:column;gap:4px;font-size:13px}.hlcr input{font:inherit;color:inherit;background:var(--paper,transparent);border:1px solid var(--line,#7778);border-radius:6px;padding:7px;max-width:150px}.hlcr input[readonly]{opacity:.7}.hlcr button{font:inherit;color:inherit;background:var(--paper,transparent);border:1px solid var(--line,#7778);border-radius:6px;padding:8px 12px;cursor:pointer}.hlcr summary{cursor:pointer;font-size:13px;font-weight:600}</style>`;
  function html(data, session, lang, loading = false) {
    if (!hasScore(session)) return '';
    const en = lang === 'en', a = assess(data,session);
    const explanation = a.comparisons.length ? '' : a.scaleMismatch ?
      (en?'The grading maximum differs from the published scoring scale, so no automatic score conversion or historical rank is shown.':'채점 만점과 공개 성적표의 공식 만점이 달라 점수를 자동 환산하거나 대회 순위를 표시하지 않습니다.') : a.records.length ?
      (en?'A full matching round is needed for a historical rank. Partial scores are not scaled to the complete competition.':'실제 대회 순위는 같은 범위의 전체 라운드를 채점했을 때 비교합니다. 일부 문제 점수를 전체 시험 점수로 환산하지 않습니다.') :
      (en?'Verified comparison data for this year have not yet been collected.':'해당 연도의 검증된 대회 비교 자료를 아직 확보하지 못했습니다.');
    return `${style}<section class="hlcr" aria-label="${en?'Historical results and sample comparison':'대회 기록·표본 비교'}"><h3>${en?'Historical results & sample comparison':'대회 기록·표본 비교'}</h3>
      <p class="hlcr-note">${en?'Practice grades are estimates. Historical positions and award thresholds are reference comparisons, not an official competition result.':'학습용 채점 점수에 따른 참고 비교입니다. 가상 순위·수상 기준 비교는 실제 대회의 공식 성적이나 수상을 뜻하지 않습니다.'}</p>
      ${sampleHtml(session,lang)}<h4>${en?'Historical competition results':'실제 대회 기록'}</h4>
      ${loading?`<p>${en?'Loading published results…':'공개 성적 자료를 불러오는 중…'}</p>`:a.comparisons.map(e=>resultHtml(e,lang)).join('')+(explanation?`<p class="hlcr-note">${esc(explanation)}</p>`:'')+a.totals.map(r=>manualHtml(r,session,lang)).join('')+coverageHtml(data,lang,a.records.length>0)}</section>`;
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
