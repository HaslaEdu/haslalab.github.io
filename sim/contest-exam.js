/* Free, browser-local practice. Official papers remain on the organisers' websites. */
(function () {
  'use strict';
  const query = new URLSearchParams(location.search), lang = query.get('lang') === 'en' ? 'en' : 'ko', ko = lang === 'ko';
  const Core = window.ContestCore, entries = (window.CONTEST_EXAMS || {}).entries || [];
  const entry = entries.find(e => e.id === query.get('id'));
  const reviewId=Number(query.get('review'));
  const gradingOnly=query.get('grading')==='1';
  const $ = id => document.getElementById(id), esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const tr = (a, b) => ko ? a : b, local = v => v && typeof v === 'object' ? v[lang] || v.ko || v.en || '' : v || '';
  const questionNo = q => q + (Number.isInteger(entry && entry.questionOffset) ? entry.questionOffset : 0);
  const choiceLabel = v => (entry.choiceLabels || [])[v - 1] || '①②③④⑤⑥⑦⑧⑨'[v - 1] || String(v);
  const displayAnswer = v => v === undefined || v === null ? '—' : entry.kind === 'choice' ? choiceLabel(v) : entry.digits === 3 ? String(v).padStart(3,'0') : String(v);
  const title = entry ? local(entry.title) || `${entry.comp.toUpperCase()} ${entry.year} ${entry.part || ''}` : tr('시험을 찾지 못했습니다.', 'Exam not found.');
  const reprint=entry&&entry.sourceType&&entry.sourceType!=='official';
  const sourcePaperTitle=reprint?tr('재수록 문제지 열기','Open reprinted paper'):tr('공식 원문 문제지 열기','Open official original paper');
  const key = (gradingOnly?'hlContestGrading:':'hlContest:') + (entry ? entry.id : ''), historyKey = gradingOnly?'hlContestGradingHistory':'hlContestHistory', back = '../#/' + (entry ? entry.comp : '') + (gradingOnly?'/review':'');
  let storageOK = true, interval = null, run = null, localPaper = null, localName = '', pageMode = '', personalReader = null, originalReader = null;
  let scanner=null,reviewHandle=null,pendingScan=null,selectedMode='paper';
  const store = {
    get(k, fallback) { try { const text = localStorage.getItem(k); return text ? JSON.parse(text) : fallback; } catch (_) { storageOK = false; return fallback; } },
    set(k, value) { try { localStorage.setItem(k, JSON.stringify(value)); return true; } catch (_) { storageOK = false; return false; } },
    del(k) { try { localStorage.removeItem(k); return true; } catch (_) { storageOK = false; return false; } }
  };
  function safeUrl(url) { try { const u = new URL(url); return /^https?:$/.test(u.protocol) ? u.href : ''; } catch (_) { return ''; } }
  function link(url, text) { const u = safeUrl(url); return u ? `<a href="${esc(u)}" target="_blank" rel="noopener noreferrer">${esc(text)} ↗</a>` : ''; }
  function sources() { return (entry.sources || []).length ? `<ul class="sources">${entry.sources.map(s => `<li>${link(s.url, local(s.title) || tr('공식 출처', 'Official source'))}</li>`).join('')}</ul>` : ''; }
  function rules() { return `<ul class="rules">${(entry.rules || []).map(r => `<li>${esc(local(r))}</li>`).join('')}</ul>${entry.formatNote ? `<p class="notice">${esc(local(entry.formatNote))}</p>` : ''}${sources()}`; }
  function paperWarning() { if(reprint)return '<div class="notice">'+tr('공식 자료실 밖에서 확보한 재수록 문제지입니다. 출처와 회차를 확인하고 개인 학습용 PDF 또는 인쇄본을 준비하세요.','This is a reprinted paper from an external archive. Check its source and session and prepare your personal PDF or printout.')+'</div>'; return entry.paperContainsAnswers ? `<div class="notice warning">${tr('공식 원문에 정답이 포함돼 있습니다. 정답을 가린 개인 학습용 문제지 또는 인쇄본을 준비하세요. 시험 중 원문을 열면 정답이 보일 수 있습니다.', 'The official original contains answers. Prepare a personal study copy or printout with answers covered. Opening the original during the exam may reveal answers.')}</div>` : `<div class="notice">${tr('공식 원문을 미리 열어 문제지와 인쇄 상태를 확인하세요. 원문에 정답이 함께 있는 경우 정답 부분을 가린 뒤 사용하세요.', 'Check the official paper before starting. If answers are included, cover them before use.')}</div>`; }
  function paperInput() { return `<label class="hint">${tr('개인 학습용 PDF 선택 (선택 사항)', 'Select a personal study PDF (optional)')}<input id="localPaper" type="file" accept="application/pdf,.pdf"></label><p class="hint" id="fileStatus">${esc(localName || (gradingOnly?tr('선택한 PDF는 이 기기에서만 열리며 서버로 전송되지 않습니다. 새로고침 후에는 다시 선택하세요.','The selected PDF stays on this device and is never uploaded. Select it again after reloading.'):tr('선택한 PDF는 이 기기에서만 열리며 서버로 전송되지 않습니다. 새로고침 후에는 다시 선택하세요. 타이머는 계속 흐릅니다.', 'The selected PDF stays on this device and is never uploaded. Select it again after reloading; the clock keeps running.')))}</p>`; }
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
    const data = {format: 'haslalab-contest-answer-v2', exam: {id: entry.id, title, comp: entry.comp, year: entry.year, part: entry.part, kind: entry.kind, minutes: entry.minutes, questions: entry.questions}, attempt: selected, result: selected.done&&(selected.mode!=='paper'||selected.paperSubmission) ? Core.grade(entry, selected.marks) : null};
    const blob = new Blob([JSON.stringify(data, null, 2)], {type:'application/json;charset=utf-8'}), url = URL.createObjectURL(blob), a = document.createElement('a');
    a.href = url; a.download = entry.id.replace(/[^a-zA-Z0-9_-]/g, '_') + '-answers-' + selected.id + '.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function count() { return run ? Object.keys(run.marks).filter(q => Core.answer(entry, run.marks[q]) !== null).length : 0; }
  function render() {
    clearInterval(interval);disposeReaders(); pageMode = '';
    if(scanner?.dispose)scanner.dispose();scanner=null;
    if(reviewHandle?.dispose)reviewHandle.dispose();reviewHandle=null;
    document.documentElement.lang = lang; document.title = title + ' · HaslaLab'; $('examTitle').textContent = title;
    $('clock').textContent = gradingOnly?tr('시간 제한 없음','No time limit'):''; $('clock').setAttribute('aria-label',gradingOnly?tr('시간 제한 없음','No time limit'):tr('남은 시간','Time left'));
    if($('brandMode'))$('brandMode').textContent=gradingOnly?tr('채점·첨삭','Grading & feedback'):tr('실전 연습','Exam practice');
    $('backup').hidden = !run; $('backup').textContent = tr('답안 백업', 'Backup'); $('backup').onclick = () => exportRun();
    if (!entry) { $('root').innerHTML = `<div class="page"><div class="card"><h1>${esc(title)}</h1><a href="../#/">HaslaLab</a></div></div>`; return; }
    if(entry.kind==='proof'&&Number.isSafeInteger(reviewId)&&reviewId>0){
      pageMode='review';$('backup').hidden=true;
      $('root').innerHTML=`<div class="page"><div class="card"><p class="eyebrow">${tr('저장된 채점 접수','Saved review')}</p><h1>${esc(title)}</h1><div class="row"><a href="?id=${encodeURIComponent(entry.id)}&lang=${lang}">${tr('이 시험 연습 화면','Practise this exam')}</a><a href="${esc(back)}">${tr('대회 목록','Competition')}</a></div></div><section id="proofReview" class="card"></section></div>`;
      if(window.ContestReview)reviewHandle=window.ContestReview.mount($('proofReview'),entry,{lang,reviewId});
      return;
    }
    if (!Core.ready(entry,gradingOnly)) { $('root').innerHTML = `<div class="page"><div class="card"><h1>${esc(title)}</h1><p class="notice warning">${gradingOnly?tr('이 기출은 답안 양식을 확인 중입니다. 원문 문제지를 이용해 주세요.','The answer format is being verified. Please use the original paper.'):tr('이 기출은 시험 시간 또는 답안 양식의 공식 확인이 끝나지 않아 실전 응시를 준비 중입니다.', 'Exam practice is unavailable until its official duration and answer format are verified.')}</p>${link(entry.paper, tr('공식 원문', 'Official original'))}${rules()}<p><a href="${esc(back)}">${tr('대회 목록으로', 'Back to competition')}</a></p></div></div>`; storageNotice(); return; }
    if (run && run.done) {
      if(run.mode==='paper'&&entry.kind!=='proof'&&!run.paperSubmission)paperScanView();
      else {result();if(entry.kind==='proof')mountProofReview();}
    } else if (run) workspace(); else if(gradingOnly)gradingIntro();else intro();
    storageNotice();
  }
  function historyHtml() {
    const h = store.get(historyKey, []).filter(a => a && a.examId === entry.id).slice(-10).reverse();
    return `<div class="card"><h2>${gradingOnly?tr('이 브라우저의 채점 기록','Grading submissions in this browser'):tr('이 브라우저의 응시 기록', 'Attempts in this browser')}</h2>${h.length ? `<div class="attempt-list">${h.map((r,i) => {const waiting=r.mode==='paper'&&entry.kind!=='proof'&&!r.paperSubmission,g=waiting?null:Core.grade(entry,r.marks); return `<button data-history="${i}">${esc(new Date(r.at).toLocaleString(ko?'ko-KR':'en-US'))} · ${g ? g.weighted ? `${g.score} / ${g.total}` : `${g.correct} / ${entry.questions} ${tr('정답','correct')}` : waiting?tr('스캔 대기','Awaiting scan'):tr('답안 기록', 'Recorded answers')} · ${tr('백업 내려받기', 'Download backup')}</button>`;}).join('')}</div>` : `<p class="muted">${tr('아직 기록이 없습니다.', 'No attempts yet.')}</p>`}</div>`;
  }
  function bindHistory() {
    const h = store.get(historyKey, []).filter(a => a && a.examId === entry.id).slice(-10).reverse();
    document.querySelectorAll('[data-history]').forEach(b => b.onclick = () => exportRun(h[+b.dataset.history]));
  }
  function gradingIntro(){
    $('root').innerHTML=`<div class="page"><section class="card"><p class="eyebrow">${tr('채점·첨삭만 받기','Grading and feedback only')}</p><h1>${esc(title)}</h1><p>${tr('이미 작성한 답안을 스캔하거나 화면에 입력해 제출하세요. 시간 제한 없이 답안을 준비할 수 있습니다.','Submit work you have already completed, using scans or on-screen entry. There is no time limit.')}</p><div class="facts"><div><strong>${tr('시간 제한 없음','No time limit')}</strong><span>${tr('채점용 답안 제출','Submit completed answers')}</span></div><div><strong>${entry.questions} ${tr('문항','questions')}</strong><span>${entry.kind==='proof'?tr('서술형','Written proof'):tr('공식 정답으로 무료 채점','Free grading against official answers')}</span></div><div><strong>${entry.kind==='proof'?tr('채점 0.3토큰','0.3 token to grade'):Core.hasKey(entry)?tr('자동 채점','Auto grade'):tr('답안 기록','Answer record')}</strong><span>${tr('채점 요청 전 답안 확인','Review your answers before submission')}</span></div></div><p>${link(entry.paper,sourcePaperTitle)}</p><div class="row"><button class="primary" id="start">${tr('답안 제출 준비','Prepare answers')}</button><span class="sp"></span><a href="${esc(back)}">${tr('대회 목록으로','Back to competition')}</a></div></section>${historyHtml()}</div>`;
    augmentIntro();bindHistory();
    $('start').onclick=()=>{
      const other=Core.normalize(store.get(key,null),entry);
      run=other&&other.untimed&&!other.done?other:Core.create(entry,Date.now(),selectedMode,true);
      // Completed paper work can enter scan/review immediately, without a sitting.
      if(run.mode==='paper'&&!run.done)Core.finish(run,Date.now());
      save();render();
    };
  }
  function intro() {
    const format = entry.kind === 'choice' ? tr('객관식', 'Multiple choice') : entry.kind === 'integer' ? tr('단답형', 'Short answer') : tr('서술형', 'Written proof');
    $('root').innerHTML = `<div class="page"><section class="card"><p class="eyebrow">${tr('무료 실전 연습 · 이 기기에서 답안 저장', 'Free exam practice · answers stay on this device')}</p><h1>${esc(title)}</h1><div class="facts"><div><strong>${entry.minutes} ${tr('분','min')}</strong><span>${tr('본 시험 · 추가 제출 시간 없음','Working period · no extra submission time')}</span></div><div><strong>${entry.questions} ${tr('문항','questions')}</strong><span>${format}</span></div><div><strong>${Core.hasKey(entry) ? tr('자동 채점','Auto grade') : tr('답안 기록','Answer record')}</strong><span>${Core.hasKey(entry) ? tr('검증한 공식 정답 기준','Verified official answers') : tr('공식 정답 대조·자가 검토','Review against official materials')}</span></div></div><h2>${tr('시험 규정과 준비', 'Rules and preparation')}</h2>${rules()}${paperWarning()}<p>${link(entry.paper,sourcePaperTitle)}</p>${paperInput()}<p class="hint">${tr('HaslaLab 개인 연습 화면입니다. 공식 대회의 본인 확인·감독·제출 시스템과 연결되지 않습니다.', 'This is personal practice, without official identity checks, proctoring, or submission.')}${entry.kind==='proof'?' '+tr('KMO 서술형은 종이 답안 스캔 또는 화면에 입력한 풀이로 학습용 채점·첨삭을 요청할 수 있습니다. 채점 요청 시 교시당 실전 토큰 0.3개를 사용하며 공식 KMO 채점과 구별됩니다.', 'For KMO proofs, request practice grading and feedback on scanned paper or typed proofs for 0.3 exam token per session; this is distinct from official KMO marking.'):''}</p><div class="checks"><label><input type="checkbox" class="ready"><span>${entry.paperContainsAnswers ? tr('정답을 가린 문제지를 준비했고, 시작 후 제한 시간이 계속 흐르는 것을 확인했습니다.','I prepared a paper with the answers covered and understand that the time limit keeps running after starting.') : tr('문제지를 준비했고, 시작 후 제한 시간이 계속 흐르는 것을 확인했습니다.','I prepared my paper and understand that the time limit keeps running after starting.')}</span></label></div><div class="row"><button class="primary" id="start" disabled>${tr('시험 시작','Start exam')}</button><span class="sp"></span><a href="${esc(back)}">${tr('대회 목록으로','Back to competition')}</a></div></section>${historyHtml()}</div>`;
    bindPaper(); bindHistory(); augmentIntro();
    document.querySelectorAll('.ready').forEach(el => el.onchange = () => { $('start').disabled = ![...document.querySelectorAll('.ready')].every(c => c.checked); });
    $('start').onclick = () => {
      // Reuse an attempt started in another tab instead of resetting its clock.
      const other = Core.normalize(store.get(key,null),entry);
      run = other && !other.done ? other : Core.create(entry,Date.now(),selectedMode); save(); render();
    };
  }
  function workspace() {
    if (Core.remaining(run,Date.now()) <= 0) { finish('timeout'); return; }
    if(run.mode==='paper')return paperWorkspace();
    pageMode = 'work';
    $('root').innerHTML = `<div class="work"><section class="paper"><div class="card"><h2>${tr('문제지','Paper')}</h2>${paperWarning()}${paperInput()}<div id="personalPreview" aria-label="${tr('이 기기의 학습용 문제지','Personal study paper on this device')}" hidden></div><p>${link(entry.paper,sourcePaperTitle)}</p><details id="originalToggle"><summary>${tr('문제지를 화면에 표시','Display paper here')}</summary><p class="hint">${gradingOnly?tr('주최기관의 보안 설정에 따라 표시되지 않을 수 있습니다. 위 링크나 준비한 인쇄본을 이용하세요.','The organiser may block embedded viewing. Use the official link or your prepared printout.'):tr('주최기관의 보안 설정에 따라 표시되지 않을 수 있습니다. 위 링크나 준비한 인쇄본을 이용하세요. 문제지 오류가 발생해도 시험 시간은 계속 흐릅니다.','The organiser may block embedded viewing. Use the official link or your prepared printout. The exam clock continues if the paper cannot load.')}</p><div id="originalPreview" aria-label="${tr('공식 원문 문제지','Official original paper')}"></div></details><p class="hint">${tr('문제지와 답안은 주최기관의 권리를 따릅니다. 원문 파일은 HaslaLab에 복제·변형하여 저장하지 않습니다.','The organisers retain rights to the papers and answers. HaslaLab does not store modified or copied originals.')}</p></div></section><section class="sheet"><div class="card"><div class="row"><h2>${tr('답안지','Answer sheet')}</h2><span class="sp"></span><button id="rulesButton">${tr('규정','Rules')}</button></div><p class="hint">${gradingOnly?tr('답안은 이 브라우저에 저장됩니다. 제출 전까지 시간 제한 없이 확인하고 수정할 수 있습니다.','Answers stay in this browser. Review and edit them without a time limit until you submit.'):tr('답안은 이 브라우저에만 저장됩니다. 단답·객관식은 종료 즉시 기록이 확정됩니다.','Answers stay in this browser. Answers are locked when you submit or time runs out.')}</p><div id="progressText"></div><div class="progress"><i id="progressBar"></i></div><nav class="qgrid" id="questions" aria-label="${tr('문항 이동','Question navigation')}"></nav><div class="row"><h3 id="questionLabel"></h3><span class="sp"></span><button id="flag" class="flag"></button></div><div id="answer" class="answer"></div><button id="clear">${tr('현재 답안 지우기','Clear current answer')}</button><p id="saveStatus" class="save" role="status"></p><div class="nav"><button id="prev">‹ ${tr('이전','Previous')}</button><span id="position"></span><button id="next">${tr('다음','Next')} ›</button></div><hr style="border:0;border-top:1px solid var(--line);margin:22px 0"><div class="row"><button id="submit" class="primary">${tr('답안 제출 및 종료','Submit and end')}</button><button id="download">${tr('답안 백업','Backup answers')}</button></div></div></section></div>`;
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
    $('download').onclick = () => exportRun(); paintQuestion(); timer(); if(!run.untimed)interval = setInterval(timer,250);
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
    if(run.untimed){$('clock').textContent=tr('시간 제한 없음','No time limit');$('clock').classList.remove('low');return;}
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
    const noKey = entry.kind==='proof' ? gradingOnly?tr('아래에서 작성한 답안을 확인하고 실전 토큰 0.3개로 채점·첨삭을 요청하세요.','Review your completed work below and request grading and feedback for 0.3 exam token.'):tr('풀이 시간을 종료했습니다. 아래에서 종이 스캔 또는 화면 답안을 제출하고 실전 토큰 0.3개로 학습용 채점·첨삭을 요청할 수 있습니다.','Working time has ended. Submit scans or typed answers below and request practice grading and feedback for 0.3 exam token.') : tr('공식 정답표가 검증되지 않아 자동 채점하지 않습니다. 저장한 답안을 공식 원문과 대조하세요.','The official key has not been verified, so automatic grading is unavailable. Compare your saved answers with the official original.');
    $('root').innerHTML=`<div class="page"><div class="card"><p class="eyebrow">${gradingOnly?tr('채점용 답안','Answers for grading'):tr('응시 완료','Attempt finished')}</p><h1>${esc(title)}</h1><p>${gradingOnly&&run.mode==='paper'&&entry.kind==='proof'?tr('작성한 종이 답안 사진이나 스캔 PDF를 아래에서 제출하세요.','Submit photos or a scanned PDF of your completed work below.'):run.mode==='paper'&&entry.kind==='proof'?tr('종이 답안의 풀이 시간을 종료했습니다. 이제 작성한 답안을 스캔해 제출하세요.','Writing time has ended. Scan and submit your completed paper answers now.'):run.done.reason==='timeout'?tr('시험 시간이 끝나 답안이 자동 제출됐습니다.','Time ran out and the attempt was submitted automatically.'):tr('답안을 제출했습니다. 이후 수정할 수 없습니다.','Your answers are submitted and locked.')}</p>${g?`<div class="score">${g.weighted?`${g.score} / ${g.total}`:`${g.correct} / ${entry.questions}`}</div><p>${g.weighted?tr('공식 배점 기준 연습 점수','Practice score using official point values'):tr('정답 수 · 공식 점수가 아닙니다','Correct count · not an official point score')}</p><div class="row"><span class="correct">${tr('정답','Correct')} ${g.correct}</span><span class="wrong">${tr('오답','Wrong')} ${g.wrong}</span><span>${tr('미응답','Blank')} ${g.blank}</span></div>${g.penalty?`<p class="hint">${tr('오답 한 문항당 감점','Deduction per wrong answer')}: ${g.penalty}</p>`:''}`:`<p class="notice">${noKey}</p><p>${count()} / ${entry.questions} ${tr('문항 응답','answered')}</p>`}<div class="row" style="margin-top:20px">${link(entry.solution,tr('공식 정답·해설','Official answers / solutions'))}${link(entry.paper,tr('공식 원문','Official original'))}<span class="sp"></span><button id="downloadDone">${tr('답안 JSON 내려받기','Download answer JSON')}</button><button id="again" class="primary">${gradingOnly?tr('다른 답안 채점','Grade another answer set'):tr('새로 응시','New attempt')}</button><a href="${esc(back)}">${tr('대회 목록','Competition')}</a></div></div><div class="card"><h2>${tr('제출 답안','Submitted answers')}</h2>${entry.kind==='proof'?Array.from({length:entry.questions},(_,i)=>`<article class="result-q"><h3>${i+1}. ${tr('문항','Question')}</h3><pre class="proof">${esc(run.marks[i+1]||tr('미응답','Unanswered'))}</pre></article>`).join(''):`<div class="scroll"><table><thead><tr><th>${tr('문항','Question')}</th><th>${tr('내 답','Your answer')}</th>${g?`<th>${tr('정답','Key')}</th><th>${tr('결과','Result')}</th>`:''}</tr></thead><tbody>${Array.from({length:entry.questions},(_,i)=>{const row=g&&g.rows[i];return `<tr><td>${i+1}</td><td>${esc(run.marks[i+1]??'—')}</td>${row?`<td>${row.answer.join(' / ')}</td><td class="${row.status}">${row.status==='correct'?tr('정답','Correct'):row.status==='wrong'?tr('오답','Wrong'):tr('미응답','Blank')}${row.fullCredit?' ('+tr('전원 정답','all-candidate credit')+')':''}</td>`:''}</tr>`;}).join('')}</tbody></table></div>`}</div>${historyHtml()}</div>`;
    if(run.mode==='paper'&&entry.kind==='proof'){
      const cards=$('root').querySelectorAll('.page>.card');
      cards[0].querySelector('.notice')?.nextElementSibling?.remove();
      cards[1].innerHTML=`<h2>${tr('작성한 종이 답안','Completed paper answers')}</h2><p>${tr('아래 채점 접수에서 문항별 답안 사진이나 스캔 PDF를 보낼 수 있습니다.','Send each question’s answer photos or scanned PDF through the review panel below.')}</p>`;
    }
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
  function printAnswerSheets(){
    if(!window.ContestPaper){alert(tr('답안지 도구를 불러오지 못했습니다. 새로고침해 주세요.','The answer-sheet tool did not load. Please reload.'));return;}
    const extra=$('extraSheets');
    window.ContestPaper.print(entry,{extraSheets:entry.kind==='proof'?Math.max(0,Math.min(10,Number(extra?.value)||0)):0,lang});
  }
  function printControls(){
    return `<div class="print-controls row"><button type="button" id="printAnswers">${tr('A4 답안지 출력','Print A4 answer sheets')}</button><button type="button" id="previewAnswers">${tr('양식 미리보기','Preview sheet')}</button>${entry.kind==='proof'?`<label>${tr('추가 연습지','Extra working sheets')} <input id="extraSheets" type="number" min="0" max="10" value="1" style="width:65px"></label>`:''}</div><p class="hint">${tr('HaslaLab 학습용 답안지입니다. A4 · 배율 100% · 머리글/바닥글 끄기로 출력하세요. 공식 대회 배포 양식과는 구별됩니다.','These are HaslaLab practice sheets. Print on A4 at 100% with browser headers and footers off; they are distinct from official contest forms.')}</p>`;
  }
  function bindPrintControls(){
    if($('printAnswers'))$('printAnswers').onclick=printAnswerSheets;
    if($('previewAnswers'))$('previewAnswers').onclick=()=>{
      if(!window.ContestPaper)return;
      showDialog(`<h2>${tr('인쇄 양식 · 첫째 쪽','Printable form · first page')}</h2><div class="sheet-preview">${window.ContestPaper.svg(entry,0)}</div>`,false);
    };
  }
  function augmentIntro(){
    const savedMode=store.get('hlContestAnswerMode','paper');selectedMode=savedMode==='online'?'online':'paper';
    const box=document.createElement('section');box.className='answer-method';
    box.innerHTML=`<h2>${tr('답안 작성·채점 방법 선택','Choose how to answer and grade')}</h2>
      <p>${gradingOnly?tr('작성한 종이 답안을 스캔하거나 풀이를 화면에 입력하세요.','Scan your completed paper work or enter your solutions on screen.'):tr('종이 답안지로 대면 필기 시험처럼 연습하거나, 화면에 답을 입력해 연습할 수 있습니다.','Practise with printed paper as in an in-person written exam, or enter answers on screen.')}</p>
      <fieldset class="method-options"><legend>${tr('답안 제출 방법','Answer method')}</legend>
        <label><input type="radio" name="answerMode" value="paper" ${selectedMode==='paper'?'checked':''}><span><b>${tr('종이 답안지 · 스캔','Printed paper and scan')}</b><small>${gradingOnly?entry.kind==='proof'?tr('작성한 풀이 사진·스캔 PDF → 확인 → 첨삭','Completed work as photos or PDF → review → feedback'):tr('HaslaLab 답안지에 답 옮기기 → 스캔 → 무료 채점','Copy answers to a HaslaLab sheet → scan → free grading'):tr('답안지 출력 → 제한시간 풀이 → 종료 후 스캔 → 채점','Print → solve within the time limit → scan → grade')}</small></span></label>
        <label><input type="radio" name="answerMode" value="online" ${selectedMode==='online'?'checked':''}><span><b>${tr('화면 입력','On-screen entry')}</b><small>${tr('화면 양식에 답안 입력 → 제출 → 채점','Enter answers on screen → submit → grade')}</small></span></label>
      </fieldset><div id="paperPrintOptions">${printControls()}</div>
      <p class="notice">${entry.kind==='proof'?tr('KMO 서술형은 종이 스캔·직접 입력 모두 채점과 첨삭을 요청할 때 교시당 실전 토큰 0.3개를 사용합니다. 답안 준비·저장은 무료입니다.','For KMO proofs, paper scans and typed answers both use 0.3 exam token per session only when you request grading and feedback. Preparing and saving answers are free.'):Core.hasKey(entry)?tr('객관식·단답형은 검증한 공식 정답으로 무료 채점합니다. 스캔을 선택하면 인식 결과를 종이 답안과 대조한 뒤 확정합니다.','Multiple-choice and short answers are graded free against verified official keys. Review scan recognition against your paper before confirming.'):tr('이 회차는 공식 정답이 없어 자동 채점하지 않습니다. 종이·화면 답안을 저장하고 원문과 대조할 수 있습니다.','This session has no verified key. Save paper or screen answers for review against the source.')}</p>`;
    document.querySelector('.facts').after(box);
    bindPrintControls();
    const paint=()=>{$('paperPrintOptions').hidden=selectedMode!=='paper';};paint();
    box.querySelectorAll('[name=answerMode]').forEach(input=>input.onchange=()=>{selectedMode=input.value;store.set('hlContestAnswerMode',selectedMode);paint();});
    if(entry.kind==='proof'){
      const fact=document.querySelector('.facts>div:last-child');
      fact.innerHTML=`<strong>${tr('채점 0.3토큰','0.3 token to grade')}</strong><span>${tr('종이·화면 답안 모두 · 교시별','Paper or typed · per session')}</span>`;
    }
  }
  function paperPaneHtml(){
    return `<section class="paper"><div class="card"><h2>${tr('문제지','Paper')}</h2>${paperWarning()}${paperInput()}<div id="personalPreview" aria-label="${tr('개인 학습용 문제지','Personal study paper')}" hidden></div><p>${link(entry.paper,sourcePaperTitle)}</p><details id="originalToggle"><summary>${tr('문제지를 화면에 표시','Display paper here')}</summary><div id="originalPreview"></div></details></div></section>`;
  }
  function bindPaperPane(){
    bindPaper();if(localPaper)showPersonalPaper();
    if((!entry.paperContainsAnswers||Number.isInteger(entry.paperLastPage)&&entry.paperLastPage>0)&&!localPaper){$('originalToggle').open=true;showOriginalPaper();}
    $('originalToggle').ontoggle=()=>{if($('originalToggle').open){showOriginalPaper();originalReader?.refresh();}};
  }
  function paperWorkspace(){
    pageMode='paper';
    $('root').innerHTML=`<div class="work">${paperPaneHtml()}<section class="sheet"><div class="card"><p class="eyebrow">${tr('종이 답안지로 응시 중','Writing on paper')}</p><h2>${tr('답은 출력한 답안지에 작성하세요','Write on your printed answer sheets')}</h2><p>${entry.kind==='proof'?tr('풀이와 증명을 문항 번호에 맞춰 작성하세요. 시험을 종료한 뒤 답안 사진·스캔 PDF를 제출해 토큰 채점을 요청할 수 있습니다.','Write each proof under the correct problem number. After finishing, submit photos or a scanned PDF and request token grading.'):tr('객관식은 한 문항에 하나, 단답형은 자릿수별로 숫자 하나씩 진하게 마킹하세요. 시험 종료 후 스캔해 인식된 답을 확인합니다.','Fill one choice per question, or one digit in each short-answer column. Scan after the exam and review the recognised answers.')}</p>${printControls()}<p class="notice">${tr('본 시험 시간이 끝나면 풀이를 멈추세요. 이후 스캔·인식 확인은 새 답을 작성하는 시간이 아닙니다.','Stop solving when the working time ends. Scanning and recognition review afterward are not extra solving time.')}</p><div class="row"><button id="paperFinish" class="primary">${tr('풀이 종료 · 스캔으로','Finish writing · continue to scan')}</button><button id="rulesButton">${tr('시험 규정','Rules')}</button></div><p id="saveStatus" class="save"></p></div></section></div>`;
    bindPrintControls();
    $('rulesButton').onclick=()=>showDialog(`<h2>${tr('시험 규정','Exam rules')}</h2>${rules()}`,false);
    $('paperFinish').onclick=()=>{
      showDialog(`<h2>${tr('종이 답안 작성을 마칠까요?','Finish writing?')}</h2><p>${tr('풀이 시간이 끝나며 이후에는 종이에 새 답을 쓰거나 고치지 않고 스캔을 진행합니다.','Working time ends now. Continue to scan without adding or changing answers on your paper.')}</p>`,true);
      $('confirmSubmit').textContent=tr('풀이 종료 · 스캔','Finish writing · scan');
    };
    bindPaperPane();timer();interval=setInterval(timer,250);storageNotice();
  }
  function paperScanView(){
    pageMode='scan';pendingScan=null;
    $('root').innerHTML=`<div class="page"><div class="card"><p class="eyebrow">${gradingOnly?tr('채점할 종이 답안 제출','Submit completed paper answers'):tr('풀이 종료 · 종이 답안 제출','Writing finished · submit paper answers')}</p><h1>${esc(title)}</h1><p>${gradingOnly?tr('작성한 답안을 스캔해 제출하세요.','Scan and submit your completed answers.'):run.done.reason==='timeout'?tr('시험 시간이 끝났습니다.','The working time is over.'):tr('종이 답안 작성을 종료했습니다.','You have finished writing.')}${tr(' 종이 답안을 수정하지 말고 스캔해 주세요.',' Scan without changing your paper answers.')}</p><p class="notice">${tr('출력한 HaslaLab 답안지의 네 모서리와 모든 마킹이 보이게 촬영하거나 스캔하세요. 인식은 이 기기에서 처리하며, 인식 결과를 확인한 뒤 채점을 확정합니다.','Photograph or scan the printed HaslaLab sheet with all four markers and marks visible. Recognition runs on this device; confirm it before grading.')}</p><div class="row"><button id="printAnswers">${tr('답안지 양식 다시 보기·출력','Print answer-sheet template')}</button><a href="${esc(back)}">${tr('대회 목록','Competition')}</a></div></div><div class="card" id="scanHost"></div><div id="scanReview"></div>${historyHtml()}</div>`;
    $('printAnswers').onclick=printAnswerSheets;bindHistory();
    if(window.ContestPaper)scanner=window.ContestPaper.mountScan($('scanHost'),entry,{lang,confirmLabel:Core.hasKey(entry)?tr('확인한 답안으로 무료 채점','Grade reviewed answers free'):tr('확인한 답안 저장','Save reviewed answers'),onRecognized:report=>{
      if(pageMode!=='scan'||!report?.complete)return;
      if(report.reviewed===true&&Core.submitPaper(run,entry,report.marks,Date.now(),{complete:true,pages:report.pages?.length||1})){
        save();store.set(historyKey,Core.appendHistory(store.get(historyKey,[]),run));render();return;
      }
      pendingScan=report;paintScanReview();
    }});
    else $('scanHost').textContent=tr('스캔 도구를 불러오지 못했습니다. 새로고침해 주세요.','The scan tool did not load. Please reload.');
  }
  function paintScanReview(){
    if(!pendingScan)return;
    const draft={...pendingScan.marks},uncertain=new Set(pendingScan.uncertain||[]);
    $('scanReview').innerHTML=`<section class="card"><h2>${tr('인식된 답안 확인','Review recognised answers')}</h2><p>${tr('종이 답안과 다르게 읽힌 부분만 고치세요. 빈칸·복수 마킹·불확실 문항은 특히 확인해 주세요.','Correct recognition errors only, matching your paper. Check blanks, multiple marks and uncertain entries carefully.')}</p><div class="scan-answer-grid">${Array.from({length:entry.questions},(_,i)=>{
      const q=i+1,value=draft[q];
      return `<label class="${uncertain.has(q)?'uncertain':''}"><b>${questionNo(q)}</b>${entry.kind==='choice'?`<select data-scan-q="${q}" aria-label="${questionNo(q)} ${tr('문항 인식 답안','recognised answer')}"><option value="">${tr('미응답','Blank')}</option>${Array.from({length:entry.choices||5},(_,j)=>`<option value="${j+1}" ${Number(value)===j+1?'selected':''}>${esc(choiceLabel(j+1))}</option>`).join('')}</select>`:`<input data-scan-q="${q}" aria-label="${questionNo(q)} ${tr('문항 인식 답안','recognised answer')}" inputmode="numeric" value="${esc(value===undefined?'':entry.digits===3?String(value).padStart(3,'0'):value)}">`}</label>`;
    }).join('')}</div><p id="scanInputError" class="error"></p><label class="scan-confirm"><input type="checkbox" id="scanConfirmed"> ${tr('인식된 답안이 종이 답안과 일치하는지 확인했습니다.','I checked that recognition matches my paper answers.')}</label><div class="row"><button id="confirmScan" class="primary" disabled>${Core.hasKey(entry)?tr('이 답안으로 무료 채점','Grade these answers free'):tr('이 답안 저장','Save these answers')}</button></div></section>`;
    function validate(){
      let invalid=false;
      $('scanReview').querySelectorAll('[data-scan-q]').forEach(input=>{
        const q=Number(input.dataset.scanQ),value=input.value.trim(),parsed=Core.answer(entry,value);
        if(value&&parsed===null)invalid=true;
        if(parsed===null)delete draft[q];else draft[q]=parsed;
      });
      $('scanInputError').textContent=invalid?tr('허용 범위의 정수 답안을 입력하세요.','Enter integer answers within the permitted range.'):'';
      $('confirmScan').disabled=invalid||!$('scanConfirmed').checked;
    }
    $('scanReview').querySelectorAll('[data-scan-q]').forEach(input=>input.oninput=validate);
    $('scanConfirmed').onchange=validate;
    $('confirmScan').onclick=()=>{
      validate();if($('confirmScan').disabled)return;
      if(!Core.submitPaper(run,entry,draft,Date.now(),{complete:true,pages:pendingScan.pages?.length||1}))return;
      save();store.set(historyKey,Core.appendHistory(store.get(historyKey,[]),run));render();
    };
  }
  function mountProofReview(){
    const host=document.createElement('section');host.id='proofReview';host.className='card';
    $('root').querySelector('.page').insertBefore(host,$('root').querySelector('.page').children[1]||null);
    if(window.ContestReview)reviewHandle=window.ContestReview.mount(host,entry,{lang,mode:run.mode||'online',answers:run.marks,runId:run.id,completedAt:run.done.at});
    else host.innerHTML=`<h2>${tr('서술형 토큰 채점','Proof grading with tokens')}</h2><p>${tr('채점 화면을 불러오지 못했습니다. 새로고침해 주세요.','The grading screen did not load. Please reload.')}</p>`;
  }
  addEventListener('storage',e=>{if(e.key!==key || !entry)return;const changed=Core.normalize(store.get(key,null),entry);if(changed && (!run || changed.id===run.id)){run=changed;render();}});
  addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible' && run && !run.done)timer();});
  addEventListener('beforeunload',disposeReaders);
  if(entry)run=Core.normalize(store.get(key,null),entry); render();
})();
