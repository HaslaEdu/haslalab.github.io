/* Free, browser-local practice. Official papers remain on the organisers' websites. */
(function () {
  'use strict';
  const query = new URLSearchParams(location.search), lang = query.get('lang') === 'en' ? 'en' : 'ko', ko = lang === 'ko';
  const Core = window.ContestCore, entries = (window.CONTEST_EXAMS || {}).entries || [];
  const entry = entries.find(e => e.id === query.get('id'));
  const $ = id => document.getElementById(id), esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const tr = (a, b) => ko ? a : b, local = v => v && typeof v === 'object' ? v[lang] || v.ko || v.en || '' : v || '';
  const questionNo = q => q + (Number.isInteger(entry && entry.questionOffset) ? entry.questionOffset : 0);
  const choiceLabel = v => (entry.choiceLabels || [])[v - 1] || '①②③④⑤⑥⑦⑧⑨'[v - 1] || String(v);
  const displayAnswer = v => v === undefined || v === null ? '—' : entry.kind === 'choice' ? choiceLabel(v) : entry.digits === 3 ? String(v).padStart(3,'0') : String(v);
  const title = entry ? local(entry.title) || `${entry.comp.toUpperCase()} ${entry.year} ${entry.part || ''}` : tr('시험을 찾지 못했습니다.', 'Exam not found.');
  const key = 'hlContest:' + (entry ? entry.id : ''), historyKey = 'hlContestHistory', back = '../#/' + (entry ? entry.comp : '');
  let storageOK = true, interval = null, run = null, localPaper = null, localName = '', pageMode = '', personalReader = null, originalReader = null;
  const store = {
    get(k, fallback) { try { const text = localStorage.getItem(k); return text ? JSON.parse(text) : fallback; } catch (_) { storageOK = false; return fallback; } },
    set(k, value) { try { localStorage.setItem(k, JSON.stringify(value)); return true; } catch (_) { storageOK = false; return false; } },
    del(k) { try { localStorage.removeItem(k); return true; } catch (_) { storageOK = false; return false; } }
  };
  function safeUrl(url) { try { const u = new URL(url); return /^https?:$/.test(u.protocol) ? u.href : ''; } catch (_) { return ''; } }
  function link(url, text) { const u = safeUrl(url); return u ? `<a href="${esc(u)}" target="_blank" rel="noopener noreferrer">${esc(text)} ↗</a>` : ''; }
  function sources() { return (entry.sources || []).length ? `<ul class="sources">${entry.sources.map(s => `<li>${link(s.url, local(s.title) || tr('공식 출처', 'Official source'))}</li>`).join('')}</ul>` : ''; }
  function rules() { return `<ul class="rules">${(entry.rules || []).map(r => `<li>${esc(local(r))}</li>`).join('')}</ul>${entry.formatNote ? `<p class="notice">${esc(local(entry.formatNote))}</p>` : ''}${sources()}`; }
  function paperWarning() { return entry.paperContainsAnswers ? `<div class="notice warning">${tr('공식 원문에 정답이 포함돼 있습니다. 정답을 가린 개인 학습용 문제지 또는 인쇄본을 준비하세요. 시험 중 원문을 열면 정답이 보일 수 있습니다.', 'The official original contains answers. Prepare a personal study copy or printout with answers covered. Opening the original during the exam may reveal answers.')}</div>` : `<div class="notice">${tr('공식 원문을 미리 열어 문제지와 인쇄 상태를 확인하세요. 원문에 정답이 함께 있는 경우 정답 부분을 가린 뒤 사용하세요.', 'Check the official paper before starting. If answers are included, cover them before use.')}</div>`; }
  function paperInput() { return `<label class="hint">${tr('개인 학습용 PDF 선택 (선택 사항)', 'Select a personal study PDF (optional)')}<input id="localPaper" type="file" accept="application/pdf,.pdf"></label><p class="hint" id="fileStatus">${esc(localName || tr('선택한 PDF는 이 기기에서만 열리며 서버로 전송되지 않습니다. 새로고침 후에는 다시 선택하세요. 타이머는 계속 흐릅니다.', 'The selected PDF stays on this device and is never uploaded. Select it again after reloading; the clock keeps running.'))}</p>`; }
  function bindPaper() {
    if (!$('localPaper')) return;
    $('localPaper').onchange = e => {
      const file = e.target.files[0];
      if (!file) return;
      if (!/\.pdf$/i.test(file.name) && file.type !== 'application/pdf') { $('fileStatus').textContent = tr('PDF 파일을 선택하세요.', 'Please select a PDF.'); return; }
      localPaper = file; localName = file.name;
      $('fileStatus').textContent = file.name + tr(' · 이 기기에서만 열림', ' · opened on this device only');
      if ($('personalPreview')) {
        if(originalReader){originalReader.dispose();originalReader=null;}
        $('originalToggle').open=false;
        showPersonalPaper();
      }
    };
  }
  function disposeReaders(){if(personalReader)personalReader.dispose();if(originalReader)originalReader.dispose();personalReader=originalReader=null;}
  function showPersonalPaper(){
    const host=$('personalPreview');if(!host||!localPaper)return;
    if(personalReader)personalReader.dispose();host.hidden=false;
    personalReader=window.ContestPdf.mount(host,{file:localPaper},{lang});
  }
  function showOriginalPaper(){
    const host=$('originalPreview');if(!host||originalReader)return;
    const fragment=/[?#&]page=(\d+)/.exec(entry.paper||'');
    const firstPage=Number.isInteger(entry.paperPage)?entry.paperPage:fragment?Number(fragment[1]):1;
    originalReader=window.ContestPdf.mount(host,{url:safeUrl(entry.paper).split('#')[0]},{lang,firstPage,lastPage:entry.paperLastPage});
  }
  function storageNotice() {
    let banner = $('storageNotice');
    if (!storageOK) {
      if (!banner) { banner = document.createElement('div'); banner.id = 'storageNotice'; banner.className = 'statusbar'; banner.setAttribute('role', 'alert'); document.body.append(banner); }
      banner.textContent = tr('이 브라우저에 저장할 수 없습니다. 창을 닫으면 답안을 잃을 수 있으니 ‘답안 백업’으로 내려받으세요.', 'This browser cannot save your answers. Download an answer backup before closing the tab.');
    }
    if ($('saveStatus')) { $('saveStatus').textContent = storageOK ? tr('답안이 이 브라우저에 자동 저장됩니다.', 'Answers are saved automatically in this browser.') : tr('저장 실패 · 답안 백업을 내려받으세요.', 'Saving failed · download an answer backup.'); $('saveStatus').classList.toggle('error', !storageOK); }
  }
  function save() { if (run) store.set(key, run); storageNotice(); }
  function exportRun(selected = run) {
    if (!selected) return;
    const data = {format: 'haslalab-contest-answer-v1', exam: {id: entry.id, title, comp: entry.comp, year: entry.year, part: entry.part, kind: entry.kind, minutes: entry.minutes, questions: entry.questions}, attempt: selected, result: selected.done ? Core.grade(entry, selected.marks) : null};
    const blob = new Blob([JSON.stringify(data, null, 2)], {type:'application/json;charset=utf-8'}), url = URL.createObjectURL(blob), a = document.createElement('a');
    a.href = url; a.download = entry.id.replace(/[^a-zA-Z0-9_-]/g, '_') + '-answers-' + selected.id + '.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function count() { return run ? Object.keys(run.marks).filter(q => Core.answer(entry, run.marks[q]) !== null).length : 0; }
  function render() {
    clearInterval(interval);disposeReaders(); pageMode = '';
    document.documentElement.lang = lang; document.title = title + ' · HaslaLab'; $('examTitle').textContent = title;
    $('clock').textContent = ''; $('backup').hidden = !run; $('backup').textContent = tr('답안 백업', 'Backup'); $('backup').onclick = () => exportRun();
    if (!entry) { $('root').innerHTML = `<div class="page"><div class="card"><h1>${esc(title)}</h1><a href="../#/">HaslaLab</a></div></div>`; return; }
    if (!Core.ready(entry)) { $('root').innerHTML = `<div class="page"><div class="card"><h1>${esc(title)}</h1><p class="notice warning">${tr('이 기출은 시험 시간 또는 답안 양식의 공식 확인이 끝나지 않아 실전 응시를 준비 중입니다.', 'Exam practice is unavailable until its official duration and answer format are verified.')}</p>${link(entry.paper, tr('공식 원문', 'Official original'))}${rules()}<p><a href="${esc(back)}">${tr('대회 목록으로', 'Back to competition')}</a></p></div></div>`; storageNotice(); return; }
    if (run && run.done) result(); else if (run) workspace(); else intro();
    storageNotice();
  }
  function historyHtml() {
    const h = store.get(historyKey, []).filter(a => a && a.examId === entry.id).slice(-10).reverse();
    return `<div class="card"><h2>${tr('이 브라우저의 응시 기록', 'Attempts in this browser')}</h2>${h.length ? `<div class="attempt-list">${h.map((r,i) => {const g=Core.grade(entry,r.marks); return `<button data-history="${i}">${esc(new Date(r.at).toLocaleString(ko?'ko-KR':'en-US'))} · ${g ? g.weighted ? `${g.score} / ${g.total}` : `${g.correct} / ${entry.questions} ${tr('정답','correct')}` : tr('답안 기록', 'Recorded answers')} · ${tr('백업 내려받기', 'Download backup')}</button>`;}).join('')}</div>` : `<p class="muted">${tr('아직 기록이 없습니다.', 'No attempts yet.')}</p>`}</div>`;
  }
  function bindHistory() {
    const h = store.get(historyKey, []).filter(a => a && a.examId === entry.id).slice(-10).reverse();
    document.querySelectorAll('[data-history]').forEach(b => b.onclick = () => exportRun(h[+b.dataset.history]));
  }
  function intro() {
    const format = entry.kind === 'choice' ? tr('객관식', 'Multiple choice') : entry.kind === 'integer' ? tr('단답형', 'Short answer') : tr('서술형', 'Written proof');
    $('root').innerHTML = `<div class="page"><section class="card"><p class="eyebrow">${tr('무료 실전 연습 · 이 기기에서 답안 저장', 'Free exam practice · answers stay on this device')}</p><h1>${esc(title)}</h1><div class="facts"><div><strong>${entry.minutes} ${tr('분','min')}</strong><span>${tr('본 시험 · 추가 제출 시간 없음','Working period · no extra submission time')}</span></div><div><strong>${entry.questions} ${tr('문항','questions')}</strong><span>${format}</span></div><div><strong>${Core.hasKey(entry) ? tr('자동 채점','Auto grade') : tr('답안 기록','Answer record')}</strong><span>${Core.hasKey(entry) ? tr('검증한 공식 정답 기준','Verified official answers') : tr('공식 정답 대조·자가 검토','Review against official materials')}</span></div></div><h2>${tr('시험 규정과 준비', 'Rules and preparation')}</h2>${rules()}${paperWarning()}<p>${link(entry.paper,tr('공식 원문 문제지 열기','Open official original paper'))}</p>${paperInput()}<p class="hint">${tr('HaslaLab 개인 연습 화면입니다. 공식 대회의 본인 확인·감독·제출 시스템과 연결되지 않습니다.', 'This is personal practice, without official identity checks, proctoring, or submission.')}${entry.kind==='proof'?' '+tr('서술형은 종이에 풀이한 뒤 문항별 요약을 기록하거나 이 화면에 직접 입력할 수 있으며 공식 채점·부분점수는 제공하지 않습니다.', 'For proof exams, work on paper and record a summary or type your proof here; official marking and partial credit are not provided.'):''}</p><div class="checks"><label><input type="checkbox" class="ready"><span>${entry.paperContainsAnswers ? tr('정답을 가린 문제지를 준비했고, 시작 후 제한 시간이 계속 흐르는 것을 확인했습니다.','I prepared a paper with the answers covered and understand that the time limit keeps running after starting.') : tr('문제지를 준비했고, 시작 후 제한 시간이 계속 흐르는 것을 확인했습니다.','I prepared my paper and understand that the time limit keeps running after starting.')}</span></label></div><div class="row"><button class="primary" id="start" disabled>${tr('시험 시작','Start exam')}</button><span class="sp"></span><a href="${esc(back)}">${tr('대회 목록으로','Back to competition')}</a></div></section>${historyHtml()}</div>`;
    bindPaper(); bindHistory();
    document.querySelectorAll('.ready').forEach(el => el.onchange = () => { $('start').disabled = ![...document.querySelectorAll('.ready')].every(c => c.checked); });
    $('start').onclick = () => {
      // Reuse an attempt started in another tab instead of resetting its clock.
      const other = Core.normalize(store.get(key,null),entry);
      run = other && !other.done ? other : Core.create(entry,Date.now()); save(); render();
    };
  }
  function workspace() {
    if (Core.remaining(run,Date.now()) <= 0) { finish('timeout'); return; }
    pageMode = 'work';
    $('root').innerHTML = `<div class="work"><section class="paper"><div class="card"><h2>${tr('문제지','Paper')}</h2>${paperWarning()}${paperInput()}<div id="personalPreview" aria-label="${tr('이 기기의 학습용 문제지','Personal study paper on this device')}" hidden></div><p>${link(entry.paper,tr('공식 원문 열기','Open official original'))}</p><details id="originalToggle"><summary>${tr('공식 원문을 화면에 표시','Display official original here')}</summary><p class="hint">${tr('주최기관의 보안 설정에 따라 표시되지 않을 수 있습니다. 위 링크나 준비한 인쇄본을 이용하세요. 문제지 오류가 발생해도 시험 시간은 계속 흐릅니다.','The organiser may block embedded viewing. Use the official link or your prepared printout. The exam clock continues if the paper cannot load.')}</p><div id="originalPreview" aria-label="${tr('공식 원문 문제지','Official original paper')}"></div></details><p class="hint">${tr('문제지와 답안은 주최기관의 권리를 따릅니다. 원문 파일은 HaslaLab에 복제·변형하여 저장하지 않습니다.','The organisers retain rights to the papers and answers. HaslaLab does not store modified or copied originals.')}</p></div></section><section class="sheet"><div class="card"><div class="row"><h2>${tr('답안지','Answer sheet')}</h2><span class="sp"></span><button id="rulesButton">${tr('규정','Rules')}</button></div><p class="hint">${tr('답안은 이 브라우저에만 저장됩니다. 단답·객관식은 종료 즉시 기록이 확정됩니다.','Answers stay in this browser. Answers are locked when you submit or time runs out.')}</p><div id="progressText"></div><div class="progress"><i id="progressBar"></i></div><nav class="qgrid" id="questions" aria-label="${tr('문항 이동','Question navigation')}"></nav><div class="row"><h3 id="questionLabel"></h3><span class="sp"></span><button id="flag" class="flag"></button></div><div id="answer" class="answer"></div><button id="clear">${tr('현재 답안 지우기','Clear current answer')}</button><p id="saveStatus" class="save" role="status"></p><div class="nav"><button id="prev">‹ ${tr('이전','Previous')}</button><span id="position"></span><button id="next">${tr('다음','Next')} ›</button></div><hr style="border:0;border-top:1px solid var(--line);margin:22px 0"><div class="row"><button id="submit" class="primary">${tr('답안 제출 및 종료','Submit and end')}</button><button id="download">${tr('답안 백업','Backup answers')}</button></div></div></section></div>`;
    bindPaper();
    if(localPaper)showPersonalPaper();
    if((!entry.paperContainsAnswers || Number.isInteger(entry.paperLastPage)&&entry.paperLastPage>0) && !localPaper){$('originalToggle').open=true;showOriginalPaper();}
    $('originalToggle').ontoggle = () => { if ($('originalToggle').open){showOriginalPaper();if(originalReader)originalReader.refresh();} };
    $('rulesButton').onclick = () => showDialog(`<h2>${tr('시험 규정','Exam rules')}</h2>${rules()}`,false);
    $('questions').onclick = e => { const b = e.target.closest('[data-q]'); if (b) selectQuestion(+b.dataset.q); };
    $('prev').onclick = () => selectQuestion(run.q-1); $('next').onclick = () => selectQuestion(run.q+1);
    $('flag').onclick = () => { if (!editable()) return; if (run.flags[run.q]) delete run.flags[run.q]; else run.flags[run.q] = true; save(); paintQuestion(); };
    $('clear').onclick = () => { if (!editable()) return; Core.setAnswer(run,entry,run.q,null,Date.now()); save(); paintQuestion(); };
    $('submit').onclick = () => showDialog(`<h2>${tr('답안을 제출하시겠습니까?','Submit this attempt?')}</h2><p>${tr('제출 후에는 답안을 수정할 수 없습니다.','Submitted answers cannot be changed.')}</p><p>${count()} / ${entry.questions} ${tr('문항 응답','answered')}</p>`,true);
    $('download').onclick = () => exportRun(); paintQuestion(); timer(); interval = setInterval(timer,250);
  }
  function editable() {
    if (!run || run.done) return false;
    const latest = Core.normalize(store.get(key,null),entry);
    if (latest && latest.id === run.id && latest.done) { run = latest; render(); return false; }
    if (Core.remaining(run,Date.now()) <= 0) { finish('timeout'); return false; }
    return true;
  }
  function paintQuestion() {
    if (pageMode !== 'work') return;
    const q = run.q;
    $('questions').innerHTML = Array.from({length:entry.questions},(_,i) => `<button data-q="${i+1}" class="${Core.answer(entry,run.marks[i+1])!==null?'answered ':''}${q===i+1?'active ':''}${run.flags[i+1]?'flagged':''}"${q===i+1?' aria-current="true"':''} aria-label="${tr('문항','Question')} ${questionNo(i+1)}${run.marks[i+1]!==undefined?', '+tr('응답함','answered'):''}">${questionNo(i+1)}</button>`).join('');
    $('questionLabel').textContent = `${questionNo(q)}. ${tr('문항','Question')}`; $('position').textContent = `${q} / ${entry.questions}`;
    $('prev').disabled = q <= 1; $('next').disabled = q >= entry.questions;
    $('flag').textContent = run.flags[q] ? tr('⚑ 검토 표시됨','⚑ Flagged') : tr('⚐ 검토 표시','⚐ Flag for review'); $('flag').classList.toggle('on',!!run.flags[q]);
    if (entry.kind === 'choice') {
      $('answer').innerHTML = `<div class="choices" role="group" aria-label="${tr('문항','Question')} ${questionNo(q)}">${Array.from({length:entry.choices||5},(_,i) => `<button class="choice${run.marks[q]===i+1?' selected':''}" data-choice="${i+1}" aria-pressed="${run.marks[q]===i+1}">${esc(choiceLabel(i+1))}</button>`).join('')}</div>`;
      $('answer').onclick = e => { const b=e.target.closest('[data-choice]'); if (!b || !editable()) return; Core.setAnswer(run,entry,q,+b.dataset.choice,Date.now()); save(); paintQuestion(); };
    } else {
      $('answer').onclick = null;
      const range=entry.answerMax===null ? tr(`${entry.answerMin??0} 이상의 정수`, `integer ≥ ${entry.answerMin??0}`) : `${entry.answerMin??0}–${entry.answerMax??999}`;
      const label = entry.kind === 'proof' ? tr('풀이·증명 또는 종이 답안의 요약','Proof, solution, or summary of your paper work') : tr(`정수 답안 (${range})`,`Answer (${range})`);
      const displayed=run.marks[q]===undefined?'':entry.digits===3?String(run.marks[q]).padStart(3,'0'):String(run.marks[q]);
      $('answer').innerHTML = `<label for="response">${esc(label)}</label>${entry.kind==='proof'?`<textarea id="response" maxlength="50000" spellcheck="false">${esc(run.marks[q]||'')}</textarea>`:`<input id="response" type="text" inputmode="numeric" pattern="[0-9]*" autocomplete="off"${entry.answerMax===null?'':` maxlength="${String(entry.answerMax??999).length}"`} value="${esc(displayed)}">`}${entry.digits===3?`<p class="hint">${tr('세 자리 답안 양식입니다. 예: 7 → 007, 0 → 000.','Three-digit answer format: 7 → 007; 0 → 000.')}</p>`:''}<p id="inputError" class="hint error"></p>`;
      $('response').oninput = e => {
        if (!editable()) return;
        const value=e.target.value, valid=Core.answer(entry,value);
        Core.setAnswer(run,entry,q,value,Date.now()); save(); paintProgress(); paintNavStatus(q);
        $('inputError').textContent = value.trim() && valid===null ? tr('허용 범위의 정수만 답안으로 저장됩니다.','Only an integer in the permitted range is recorded.') : '';
      };
    }
    paintProgress(); storageNotice();
  }
  function paintNavStatus(q) { const button=$('questions').querySelector(`[data-q="${q}"]`); if (button) button.classList.toggle('answered',Core.answer(entry,run.marks[q])!==null); }
  function paintProgress() { $('progressText').textContent = `${count()} / ${entry.questions} ${tr('문항 응답','answered')}`; $('progressBar').style.width = 100*count()/entry.questions+'%'; }
  function selectQuestion(q) { if (!editable() || q<1 || q>entry.questions) return; run.q=q; save(); paintQuestion(); }
  function timer() {
    if (!run || run.done) return;
    const seconds=Math.ceil(Core.remaining(run,Date.now())/1000);
    $('clock').textContent = String(Math.floor(seconds/60)).padStart(2,'0')+':'+String(seconds%60).padStart(2,'0'); $('clock').classList.toggle('low',seconds<=300);
    if (seconds<=0) finish('timeout');
  }
  function showDialog(body,ending) {
    const d=$('dialog'); d.innerHTML=body+`<div class="row"><button id="closeDialog">${ending?tr('계속 풀기','Continue'):tr('닫기','Close')}</button>${ending?`<button class="primary" id="confirmSubmit">${tr('제출 및 종료','Submit and end')}</button>`:''}</div>`; d.showModal(); $('closeDialog').onclick=()=>d.close(); if (ending) $('confirmSubmit').onclick=()=>finish('manual');
  }
  function finish(reason) {
    if (!run || run.done) return;
    const latest=Core.normalize(store.get(key,null),entry); if (latest && latest.id===run.id && latest.done) run=latest;
    else Core.finish(run,Date.now(),reason);
    clearInterval(interval); save(); store.set(historyKey,Core.appendHistory(store.get(historyKey,[]),run)); if ($('dialog').open) $('dialog').close(); render();
  }
  function result() {
    pageMode='result'; const g=Core.grade(entry,run.marks);
    const noKey = entry.kind==='proof' ? tr('서술형 답안을 기록했습니다. 증명의 타당성·부분점수는 자동으로 평가하지 않습니다. 공식 자료 또는 선생님의 지도로 검토하세요.','Your written answers have been recorded. Proof validity and partial credit are not automatically assessed; review with official materials or a teacher.') : tr('공식 정답표가 검증되지 않아 자동 채점하지 않습니다. 저장한 답안을 공식 원문과 대조하세요.','The official key has not been verified, so automatic grading is unavailable. Compare your saved answers with the official original.');
    $('root').innerHTML=`<div class="page"><div class="card"><p class="eyebrow">${tr('응시 완료','Attempt finished')}</p><h1>${esc(title)}</h1><p>${run.done.reason==='timeout'?tr('시험 시간이 끝나 답안이 자동 제출됐습니다.','Time ran out and the attempt was submitted automatically.'):tr('답안을 제출했습니다. 이후 수정할 수 없습니다.','Your answers are submitted and locked.')}</p>${g?`<div class="score">${g.weighted?`${g.score} / ${g.total}`:`${g.correct} / ${entry.questions}`}</div><p>${g.weighted?tr('공식 배점 기준 연습 점수','Practice score using official point values'):tr('정답 수 · 공식 점수가 아닙니다','Correct count · not an official point score')}</p><div class="row"><span class="correct">${tr('정답','Correct')} ${g.correct}</span><span class="wrong">${tr('오답','Wrong')} ${g.wrong}</span><span>${tr('미응답','Blank')} ${g.blank}</span></div>${g.penalty?`<p class="hint">${tr('오답 한 문항당 감점','Deduction per wrong answer')}: ${g.penalty}</p>`:''}`:`<p class="notice">${noKey}</p><p>${count()} / ${entry.questions} ${tr('문항 응답','answered')}</p>`}<div class="row" style="margin-top:20px">${link(entry.solution,tr('공식 정답·해설','Official answers / solutions'))}${link(entry.paper,tr('공식 원문','Official original'))}<span class="sp"></span><button id="downloadDone">${tr('답안 JSON 내려받기','Download answer JSON')}</button><button id="again" class="primary">${tr('새로 응시','New attempt')}</button><a href="${esc(back)}">${tr('대회 목록','Competition')}</a></div></div><div class="card"><h2>${tr('제출 답안','Submitted answers')}</h2>${entry.kind==='proof'?Array.from({length:entry.questions},(_,i)=>`<article class="result-q"><h3>${i+1}. ${tr('문항','Question')}</h3><pre class="proof">${esc(run.marks[i+1]||tr('미응답','Unanswered'))}</pre></article>`).join(''):`<div class="scroll"><table><thead><tr><th>${tr('문항','Question')}</th><th>${tr('내 답','Your answer')}</th>${g?`<th>${tr('정답','Key')}</th><th>${tr('결과','Result')}</th>`:''}</tr></thead><tbody>${Array.from({length:entry.questions},(_,i)=>{const row=g&&g.rows[i];return `<tr><td>${i+1}</td><td>${esc(run.marks[i+1]??'—')}</td>${row?`<td>${row.answer.join(' / ')}</td><td class="${row.status}">${row.status==='correct'?tr('정답','Correct'):row.status==='wrong'?tr('오답','Wrong'):tr('미응답','Blank')}${row.fullCredit?' ('+tr('전원 정답','all-candidate credit')+')':''}</td>`:''}</tr>`;}).join('')}</tbody></table></div>`}</div>${historyHtml()}</div>`;
    if(g && !g.weighted) $('root').querySelector('.score').textContent = `${g.correct} / ${g.gradedCount}`;
    $('root').querySelectorAll('table tbody tr').forEach((row,i)=>{
      row.cells[0].textContent=questionNo(i+1);
      row.cells[1].textContent=displayAnswer(run.marks[i+1]);
      if(g)row.cells[2].textContent=g.rows[i].answer.map(displayAnswer).join(' / ');
      if(g && g.rows[i].status==='excluded') row.cells[3].textContent=tr('채점 제외','Excluded from grading');
      if(g && g.rows[i].fullCredit) row.cells[2].textContent=tr('전원 정답','All-candidate credit');
    });
    $('root').querySelectorAll('.result-q h3').forEach((heading,i)=>{heading.textContent=`${questionNo(i+1)}. ${tr('문항','Question')}`;});
    $('downloadDone').onclick=()=>exportRun(); $('again').onclick=()=>{store.del(key);run=null;render();}; bindHistory();
  }
  addEventListener('storage',e=>{if(e.key!==key || !entry)return;const changed=Core.normalize(store.get(key,null),entry);if(changed && (!run || changed.id===run.id)){run=changed;render();}});
  addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible' && run && !run.done)timer();});
  addEventListener('beforeunload',disposeReaders);
  if(entry)run=Core.normalize(store.get(key,null),entry); render();
})();
