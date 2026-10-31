/* Server regrades answers; browser scores are never accepted as ranking data. */
(function(){
  const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const apiBase=()=>{let value='';try{value=localStorage.getItem('hlCmApi')||'';}catch(e){}const base=(value||'https://haslalab-community-edge.haslalab.workers.dev').replace(/\/+$/,'');return base==='https://haslalab-community.haslalab.workers.dev'?'https://haslalab-community-edge.haslalab.workers.dev':base;};
  window.OmrServer={async mount({container,run,comp,year,part,count,lang}){
    if(comp!=='kphe'||!run.done)return;
    const ko=lang!=='en',card=document.createElement('div');card.className='card';
    card.innerHTML=`<h2>${ko?'서버 저장 · 응시자 비교':'Saved result and comparison'}</h2><div class="server-status" role="status"></div>`;
    container.insertBefore(card,container.children[1]||null);const status=card.querySelector('.server-status');
    let token='';try{token=localStorage.getItem('hlCmTok')||'';}catch{}
    if(!token){status.innerHTML=ko?'로그인하면 답안을 서버에서 다시 채점해 계정에 저장하고, 같은 시험·과정의 응시자와 비교합니다. <a href="../#/login">로그인</a>':'Sign in to save server-graded answers and compare the same paper and level. <a href="../#/login">Sign in</a>';return;}
    const save=async()=>{
      status.textContent=ko?'서버에서 채점·저장하는 중…':'Grading and saving on the server…';
      const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
      try{
        const response=await fetch(apiBase()+'/api/omr/attempts',{
          method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+token},signal:controller.signal,
          body:JSON.stringify({exam_key:`kphe:${year}:${part}`,client_id:run.id,answers:Array.from({length:count},(_,i)=>run.marks[i+1]||null)})});
        const data=await response.json();if(!response.ok)throw Error(data.error||String(response.status));
        const s=data.attempt.score,c=data.cohort;
        const score=s.officialScore==null?(ko?`감점 정답수: ${s.practice.score} / ${s.practice.maximum} (연습 지표)`:`Penalty-adjusted correct answers: ${s.practice.score} / ${s.practice.maximum} (practice metric)`):(ko?`최종점수 ${s.officialScore} / ${s.maximum} · 원점수 ${s.rawScore} · 감점 ${s.penalty}`:`Final ${s.officialScore} / ${s.maximum} · Raw ${s.rawScore} · Penalty ${s.penalty}`);
        const ranking=c.upperPercent==null?(ko?`비교군 ${c.n}명. 5명 이상 모이면 상위 비율을 표시합니다.`:`${c.n} candidates. Percentile is shown from 5 candidates.`):(ko?`${c.rank}위 / ${c.n}명 · 상위 ${c.upperPercent.toFixed(1)}% (동점 ${c.ties}명 포함)`:`Rank ${c.rank} of ${c.n} · Top ${c.upperPercent.toFixed(1)}% (including ${c.ties} tied candidates)`);
        status.innerHTML=`<strong>${ko?'서버에 저장했습니다.':'Saved on the server.'}</strong><p>${escape(score)}</p>${s.officialScore==null?`<p class="notice">${ko?'공식 문항 배점·분야별 비중·최종 산식을 아직 확인하지 못해 공식 최종점수는 표시하지 않습니다. 위 지표는 정답수 − 오답수 × 0.25이며, 공식 점수가 아닙니다.':'Official item/domain weights and the complete final-score formula are unverified. The practice metric is correct answers minus 0.25 times wrong answers; it is not an official score.'}</p>`:''}<p><b>${escape(ranking)}</b></p><p class="hint">${ko?'비교 대상: 같은 시험·과정·채점규정의 HaslaLab 응시자. 다른 계정은 첫 응시만 집계하고 본인은 이번 점수로 비교합니다. 실제 물리대회 참가자 전체의 백분위가 아닙니다.':'Compared with other accounts’ first HaslaLab attempts on the same paper, level and scoring version, using your current score. This is not the official competition population.'}</p>${s.fields?`<table><thead><tr><th>${ko?'분야':'Domain'}</th><th>${ko?'원점수':'Raw'}</th><th>${ko?'감점':'Penalty'}</th><th>${ko?'최종':'Final'}</th></tr></thead><tbody>${Object.entries(s.fields).map(([name,f])=>`<tr><td>${escape(name)}</td><td>${f.raw}/${f.maximum}</td><td>${f.penalty}</td><td>${f.final}</td></tr>`).join('')}</tbody></table>`:''}`;
      }catch(error){
        const messages={
          login_required:ko?'로그인이 만료됐습니다. 다시 로그인한 뒤 저장해 주세요.':'Your sign-in expired. Sign in again before saving.',
          invalid_answers:ko?'저장된 답안 형식을 확인할 수 없습니다.':'The saved answer format could not be validated.',
          invalid_exam:ko?'서버의 시험 목록을 갱신하는 중입니다. 잠시 뒤 다시 시도해 주세요.':'The server exam catalogue is being updated. Please retry shortly.',
          scoring_version_changed:ko?'채점 기준이 갱신되었습니다. 이 응시 기록은 이전 기준으로 보관됩니다.':'The scoring policy changed. This attempt remains saved under the previous policy.',
          rate_limited:ko?'하루 저장 횟수를 초과했습니다. 나중에 다시 시도해 주세요.':'The daily save limit has been reached. Please retry later.'
        };
        const detail=messages[error.message]||(error.name==='AbortError'?(ko?'서버 응답이 지연되고 있습니다.':'The server is taking too long to respond.'):(ko?'연결 상태를 확인한 뒤 다시 시도해 주세요.':'Check your connection and retry.'));
        status.innerHTML=`<p class="error">${ko?'서버에 저장하지 못했습니다. 브라우저 답안은 유지됩니다.':'Could not save to the server. Your browser copy remains.'} ${escape(detail)}</p><button type="button">${ko?'저장 다시 시도':'Retry saving'}</button>`;
        status.querySelector('button').onclick=save;
      }finally{clearTimeout(timer);}
    };await save();
  }};
})();
