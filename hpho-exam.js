/* HPhO exam page (#/hpho/exam), IsPhO-style: the theory and the experiment exam each on their own day, listed one above
   the other at the entrance. An exam's room opens an hour before its start (technical check, then the waiting room);
   a candidate must be seated twenty minutes before the start. The waiting room counts down to the start and shows the
   general guide and the answer sheets, and the paper's language can be changed there. At the start the paper appears in
   the page (PDF.js, like Hasla Nonsul's 실전 모드); the exam window cannot be left until the end, and a candidate who
   drops out comes back through the check (each return is counted; a person reviews the recording of frequent ones).
   When the time is over the page moves by itself to the submission page: the paper is gone, the recording continues,
   and writing on the sheets from then on is cheating; the answer photos go up there.
   It runs only inside the HaslaEdu desktop app's exam window, whose preload gives it window.haslaExam. The page sends
   the window's events with its own heartbeat to the server (community/src/hpho-exam.js); no token or account data
   passes to the native shell. */
(() => {
  const L = () => (typeof lang === "string" && lang === "en") ? "en" : "ko";
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const TRACKS = ["theory", "experiment"];
  const T = {
    ko: { title: "HPhO 시험", appOnly: "HPhO는 하슬라에듀 데스크톱 앱의 시험 창에서만 응시할 수 있습니다.", appGet: "데스크톱 앱 내려받기",
      entrance: "시험 입장", track: { theory: "이론 시험", experiment: "실험 시험" }, hours: "5시간", enter: "입장", back: "답안 제출하러 입장", reenter: "다시 입장",
      opensAt: v => `입장: ${v}부터 (시작 1시간 전)`, seatBy: v => `착석 마감: ${v} (시작 20분 전)`, opensLater: "입장 시간이 아닙니다", seatClosed: "착석 마감이 지나 입장할 수 없습니다", ended: "종료", submitted: "제출 완료", noRound: "응시할 수 있는 시험이 없습니다.",
      check: "기술 점검", checks: { app: "하슬라에듀 데스크톱 앱", net: "서버 연결", entry: "참가 접수", login: "로그인", camera: "웹캠", mic: "마이크", screen: "화면 기록", face: "얼굴 인식", voice: "문장 읽기 (마이크)", ears: "귀 검사 (이어폰)" }, retry: "다시 점검", preview: "카메라 미리보기", camNeed: "웹캠·마이크·화면 기록이 모두 켜져야 응시할 수 있습니다. 다른 프로그램이 카메라를 쓰고 있지 않은지 확인하세요.",
      screenNeed: "화면 기록을 시작하지 못했습니다. 앱을 최신 버전으로 업데이트한 뒤 다시 점검하세요.",
      faceStep: ["얼굴 확인", "카메라를 정면으로 바라보세요. 얼굴 전체가 미리보기 가운데에 오도록 앉아 주세요."],
      face: { no_video: "카메라 영상이 들어오지 않습니다. 다른 프로그램이 카메라를 쓰고 있지 않은지 확인하세요.", detector: "얼굴 인식 기능을 불러오지 못했습니다. 인터넷 연결을 확인한 뒤 다시 점검하세요.", none: "얼굴이 보이지 않습니다. 카메라를 정면으로 바라보세요.", many: "화면에 두 사람 이상이 보입니다. 혼자 있는 곳에서 응시하세요.", dark: "얼굴이 너무 어둡습니다. 조명을 켜거나 창 쪽을 바라보고 앉으세요.", small: "얼굴이 너무 작게 보입니다. 카메라에 조금 더 가까이 앉으세요.", off: "얼굴이 화면 가장자리에 있습니다. 미리보기 가운데로 오도록 자리를 옮기세요." },
      micStep: ["마이크 확인", "버튼을 누르고, 「지금 읽어 주세요」가 뜨면 아래 문장을 처음부터 끝까지 또박또박 읽어 주세요. 문장을 다 읽어야 통과합니다.", "마이크 점검 시작", "조용히 기다려 주세요… 주변 소리를 재는 중", "지금 읽어 주세요", "들은 문장을 확인하는 중…"],
      mic: { no_mic: "마이크를 찾지 못했습니다. 마이크를 연결하고 다시 점검하세요.", no_audio: "소리를 분석하지 못했습니다. 다시 점검하세요.", silent: "소리가 전혀 들리지 않습니다. 마이크가 음소거되어 있지 않은지, 올바른 마이크가 선택되었는지 확인하세요.", quiet: "목소리가 너무 작게 들립니다. 마이크에 가까이 앉아 조금 더 크게 읽어 주세요.", short: "문장 전체가 들리지 않았습니다. 소리를 지르거나 한 단어만 말하면 통과할 수 없습니다. 화면의 문장을 처음부터 끝까지 읽어 주세요.", not_said: "화면의 문장이 들리지 않았습니다. 문장을 그대로, 또박또박 읽어 주세요.", failed: "녹음을 보내지 못했습니다. 다시 점검하세요." },
      earStep: ["귀 검사", "이어폰·헤드폰을 끼고 있지 않은지 확인합니다. 머리카락을 귀 뒤로 넘기고 버튼을 누르세요.", "귀 검사 시작"],
      ear: { first: "고개를 천천히 한쪽으로 돌려 귀가 카메라에 보이게 하고, 잠시 멈추세요.", second: "이번에는 반대쪽으로 고개를 돌려 다른 쪽 귀를 보여 주세요.", done: "확인하는 중…", device: "귀에 이어폰이나 헤드폰 같은 기기가 보입니다. 모두 빼고 다시 검사하세요. 보청기를 써야 한다면 시험 전에 운영진에게 알려 주세요.", unclear: "귀가 잘 보이지 않았습니다. 머리카락을 넘기고 밝은 곳에서 고개를 조금 더 돌려 다시 검사하세요.", failed: "사진을 보내지 못했습니다. 다시 검사하세요." }, ok: "확인", bad: "문제 있음", wait: "확인 중…",
      notReg: "이 회차에 접수하지 않았습니다.", login: "로그인하세요.", room: "대기실", startsIn: "시험 시작까지", candidate: "수험번호", autoStart: "시작 시각이 되면 시험지가 자동으로 열립니다. 이 창을 닫지 마세요.",
      paperLang: "시험지 언어", paperLangNote: "시험 시작 전까지 바꿀 수 있습니다.", langs: { ko: "한국어", en: "English" },
      docs: "시험 자료", docNames: { guide: "General Guide", writing: "답안지", answer: "Answer Sheet", paper: "문제지" }, noDocs: "아직 공개된 자료가 없습니다.", docsNote: "답안지와 Answer Sheet는 미리 인쇄해 두세요.",
      left: "남은 시간", rules: ["시험 중에는 이 창만 사용하세요. 다른 프로그램과 웹사이트는 사용할 수 없습니다.", "시험이 끝날 때까지 퇴장할 수 없습니다. 연결이 끊기면 다시 들어올 수 있지만, 재접속은 모두 기록되며 잦으면 감독관이 녹화를 검토해 부정행위로 판정할 수 있습니다.", "시험 시간이 끝나면 화면이 제출 페이지로 바뀝니다. 그때부터 답안지에 무엇이든 쓰면 부정행위로 간주됩니다.", "답안지에는 수험번호만 적으세요."],
      reconnects: n => `재접속 ${n}회 · 잦은 재접속은 감독관이 녹화를 검토합니다`, paperLoading: "시험지를 불러오는 중…", paperFail: "시험지를 불러오지 못했습니다. 잠시 후 다시 시도합니다.", paperNone: "시험지가 아직 올라오지 않았습니다. 감독관에게 문의하세요.", zoomFit: "폭 맞춤",
      overTitle: "시험 시간이 끝났습니다", overPen: "지금 바로 펜을 내려놓으세요. 지금부터 답안지에 무엇이든 쓰면 부정행위로 간주됩니다.", overRec: "감독 녹화는 제출을 마칠 때까지 계속됩니다.",
      uploadTitle: "답안 제출", uploadUntil: "제출 마감까지", uploadHow: "답안지를 한 장씩 웹캠에 비추어 찍거나, 사진 파일을 올리세요. 순서대로 올리면 쪽 번호가 매겨집니다.", shoot: "웹캠으로 한 장 찍기", files: "사진 파일 올리기", pages: n => `올린 쪽: ${n}`, submit: "제출하기", submitAsk: n => `${n}쪽을 제출할까요? 제출하면 더 올릴 수 없습니다.`, submitEmpty: "아직 올린 쪽이 없습니다. 그래도 제출할까요?", uploading: "올리는 중…", uploadFail: "올리지 못했습니다. 다시 시도하세요.",
      done: "제출을 마쳤습니다", doneNote: "수고하셨습니다. 시험 창이 곧 닫힙니다.", leave: "시험 창 닫기", conn: "연결", connOk: "정상", connBad: "끊김 · 다시 연결 중", proctor: "감독", proctorOn: "기록 중",
      errors: { seating_closed: "착석 마감(시작 20분 전)이 지나 입장할 수 없습니다.", not_open: "아직 입장 시간이 아닙니다. 시작 1시간 전부터 입장할 수 있습니다.", exam_over: "시험이 끝났습니다.", not_registered: "이 회차에 접수하지 않았습니다.", desktop_app_required: "하슬라에듀 데스크톱 앱에서만 응시할 수 있습니다.", upload_closed: "제출 시간이 끝났습니다.", network: "서버에 연결하지 못했습니다. 인터넷 연결을 확인하세요." } },
    en: { title: "HPhO exam", appOnly: "HPhO can only be sat in the exam window of the HaslaEdu desktop app.", appGet: "Get the desktop app",
      entrance: "Exam entrance", track: { theory: "Theory exam", experiment: "Experimental exam" }, hours: "5 hours", enter: "Enter", back: "Enter to submit answers", reenter: "Enter again",
      opensAt: v => `Entry from ${v} (an hour before the start)`, seatBy: v => `Be seated by ${v} (20 minutes before the start)`, opensLater: "Not open yet", seatClosed: "Seating has closed", ended: "Over", submitted: "Submitted", noRound: "There is no exam to sit.",
      check: "Technical check", checks: { app: "HaslaEdu desktop app", net: "Server connection", entry: "Registration", login: "Signed in", camera: "Webcam", mic: "Microphone", screen: "Screen recording", face: "Face", voice: "Reading aloud (microphone)", ears: "Ear check (earphones)" }, retry: "Check again", preview: "Camera preview", camNeed: "The webcam, microphone and screen recording must all be on to sit the exam. Make sure no other program is using the camera.",
      screenNeed: "Screen recording could not start. Update the app to the latest version, then check again.",
      faceStep: ["Face check", "Look straight at the camera, with your whole face in the middle of the preview."],
      face: { no_video: "No picture from the camera. Make sure no other program is using it.", detector: "Face detection could not load. Check your internet connection and try again.", none: "Your face cannot be seen. Look straight at the camera.", many: "More than one person is in view. Sit the exam alone.", dark: "Your face is too dark. Turn on a light or face a window.", small: "Your face looks too small. Sit a little closer to the camera.", off: "Your face is at the edge of the picture. Move so it is in the middle of the preview." },
      micStep: ["Microphone check", "Press the button and, when “Read now” appears, read the whole sentence below clearly. Only the whole sentence passes.", "Start the microphone check", "Please wait quietly… measuring the room", "Read now", "Checking what was heard…"],
      mic: { no_mic: "No microphone was found. Connect one and check again.", no_audio: "The sound could not be analysed. Check again.", silent: "No sound at all. Make sure the microphone is not muted and the right one is selected.", quiet: "Your voice is too quiet. Sit closer to the microphone and read a little louder.", short: "The whole sentence was not heard. A shout or a single word does not pass: read the sentence on the screen from start to end.", not_said: "The sentence on the screen was not heard. Read it exactly as written, clearly.", failed: "The recording could not be sent. Check again." },
      earStep: ["Ear check", "This checks that you are not wearing earphones or headphones. Tuck your hair behind your ears and press the button.", "Start the ear check"],
      ear: { first: "Slowly turn your head to one side so one ear faces the camera, and hold still.", second: "Now turn to the other side to show the other ear.", done: "Checking…", device: "Earphones, headphones or another device can be seen in or on your ear. Take them off and check again. If you need a hearing aid, tell the organisers before the exam.", unclear: "Your ears could not be seen clearly. Move your hair aside, use more light, turn your head a little further and check again.", failed: "The photos could not be sent. Check again." }, ok: "OK", bad: "Problem", wait: "Checking…",
      notReg: "You are not registered for this round.", login: "Please sign in.", room: "Waiting room", startsIn: "Exam starts in", candidate: "Candidate number", autoStart: "The paper opens by itself at the start time. Keep this window open.",
      paperLang: "Language of the paper", paperLangNote: "You can change it until the start.", langs: { ko: "한국어", en: "English" },
      docs: "Exam documents", docNames: { guide: "General Guide", writing: "Writing sheet", answer: "Answer Sheet", paper: "Paper" }, noDocs: "No documents have been published yet.", docsNote: "Print the writing and answer sheets beforehand.",
      left: "Time left", rules: ["Use only this window during the exam. Other programs and websites are not allowed.", "You cannot leave until the exam ends. If you are disconnected you can come back, but every return is recorded, and if it happens often a proctor reviews the recording and may rule it cheating.", "When the time is over the screen changes to the submission page. Writing anything on your sheets from then on is cheating.", "Write only your candidate number on the answer sheets."],
      reconnects: n => `Reconnected ${n}× · frequent reconnects are reviewed by a proctor`, paperLoading: "Loading the paper…", paperFail: "The paper could not be loaded. Trying again shortly.", paperNone: "The paper has not been uploaded yet. Ask the organisers.", zoomFit: "Fit width",
      overTitle: "Time is over", overPen: "Put your pen down now. Writing anything on your sheets from now on is cheating.", overRec: "The proctoring recording continues until you have submitted.",
      uploadTitle: "Submit your answers", uploadUntil: "Submission closes in", uploadHow: "Hold each sheet up to the webcam and take a photo, or upload photo files. Pages are numbered in the order you add them.", shoot: "Take one page with the webcam", files: "Upload photo files", pages: n => `Pages added: ${n}`, submit: "Submit", submitAsk: n => `Submit ${n} page(s)? You cannot add more afterwards.`, submitEmpty: "No pages yet. Submit anyway?", uploading: "Uploading…", uploadFail: "Upload failed. Try again.",
      done: "Submitted", doneNote: "Well done. The exam window closes shortly.", leave: "Close the exam window", conn: "Connection", connOk: "Online", connBad: "Lost · reconnecting", proctor: "Proctoring", proctorOn: "Recording",
      errors: { seating_closed: "Seating closed 20 minutes before the start; you cannot enter.", not_open: "Not open yet. Entry opens an hour before the start.", exam_over: "The exam is over.", not_registered: "You are not registered for this round.", desktop_app_required: "The exam can only be sat in the HaslaEdu desktop app.", upload_closed: "Submission has closed.", network: "Could not reach the server. Check your internet connection." } },
  };
  const bridge = () => (window.haslaExam && typeof window.haslaExam.onEvent === "function") ? window.haslaExam : null;
  let st = { round: null, entry: null, track: null, tracks: {}, session: null, phase: "lobby", online: true, seq: 0, queue: [], timer: 0, flushTimer: 0, unsub: null, docs: [], pages: 0 };
  const fmt = sec => { sec = Math.max(0, Math.floor(sec)); const h = Math.floor(sec / 3600), m = Math.floor(sec % 3600 / 60), s = sec % 60; return (h ? h + ":" : "") + String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0"); };
  const skew = () => st.skew || 0, nowS = () => Math.floor(Date.now() / 1000) + skew();
  const when = s => new Date(s * 1000).toLocaleString(L() === "en" ? "en-GB" : "ko-KR", { dateStyle: "medium", timeStyle: "short" });
  const hm = s => new Date(s * 1000).toLocaleTimeString(L() === "en" ? "en-GB" : "ko-KR", { hour: "2-digit", minute: "2-digit" });
  const path = (a, track = st.track) => `/hpho/rounds/${encodeURIComponent(st.round.id)}/exam/${track}/${a}`;
  const errText = e => { const x = T[L()], c = e?.code || e?.message || "network"; return x.errors[c] || c; };
  const W = () => st.tracks[st.track]?.window;
  const sync = d => { if (d?.now) st.skew = d.now - Math.floor(Date.now() / 1000); };

  function push(kind, detail) {
    st.seq++;
    st.queue.push({ seq: st.seq, t: nowS(), kind, ...(detail ? { detail: String(detail).slice(0, 200) } : {}) });
  }
  async function flush() {
    if (!["exam", "submit"].includes(st.phase)) return;
    if (!st.queue.length) push("heartbeat");
    const batch = st.queue.splice(0, 100);
    try { const r = await cmApi("POST", path("events"), { events: batch }); st.online = true; sync(r);
      const w = W(); if (w && r.ends_at) { w.ends = r.ends_at; if (r.upload_until) w.upload_until = r.upload_until; } }
    catch (e) { st.queue.unshift(...batch); st.online = false; }
    paintBar();
  }
  /* multipart to the exam API (snapshots, checks, answer pages) */
  async function sendForm(action, fields) {
    const fd = new FormData(); for (const [k, v] of Object.entries(fields)) v instanceof Blob ? fd.set(k, v, k + (v.type === "audio/wav" ? ".wav" : ".jpg")) : fd.set(k, v);
    const res = await fetch(cmBase() + "/api" + path(action), { method: "POST", headers: { Authorization: "Bearer " + cmTok() }, body: fd });
    const j = await res.json().catch(() => ({}));
    if (!res.ok) throw { code: j.error || j.code || "network" };
    return j;
  }

  function view() {
    return `<div class="shell hpho hpho-exam"><div class="hpho-exam-bar" id="hphoExamBar"></div><div id="hphoExamMain"><p class="hpho-muted">…</p></div></div>`;
  }
  function paintBar() {
    const x = T[L()], bar = document.getElementById("hphoExamBar"); if (!bar) return;
    const w = W(), live = ["exam", "submit"].includes(st.phase);
    const left = st.phase === "exam" ? w.ends - nowS() : st.phase === "submit" ? w.upload_until - nowS() : null;
    bar.innerHTML = `<b class="hpho-exam-title"><img class="hpho-exam-icon hpho-logo-light" src="logo/brand/hpho-icon-light.svg?v=20261109-hpho" alt=""><img class="hpho-exam-icon hpho-logo-dark" src="logo/brand/hpho-icon-dark.svg?v=20261109-hpho" alt="" aria-hidden="true">${x.title}${st.round ? " · " + (st.round.status === "draft" ? (L() === "en" ? "Practice exam" : "모의 시험") : esc(st.round.title[L()])) : ""}${st.track && st.phase !== "lobby" ? " · " + x.track[st.track] : ""}</b>
      ${st.entry ? `<span>${x.candidate} <b class="hpho-no">${esc(st.entry.candidate_no)}</b></span>` : ""}
      ${live ? `<span class="hpho-light ${st.online ? "is-ok" : "is-bad"}">${x.conn}: ${st.online ? x.connOk : x.connBad}</span><span class="hpho-light is-ok">${x.proctor}: ${x.proctorOn}</span>
        <span class="hpho-exam-clock${left < 600 ? " is-low" : ""}">${st.phase === "submit" ? x.uploadUntil : x.left} <b>${fmt(left)}</b></span>` : ""}`;
  }
  const leaveBtn = () => bridge()?.leave ? `<button type="button" class="hpho-link" id="hphoExamLeave">${T[L()].leave}</button>` : "";
  const wireLeave = box => box.querySelector("#hphoExamLeave")?.addEventListener("click", () => bridge()?.leave?.());

  /* the entrance: the theory exam above, the experiment below; each opens an hour before its start */
  function trackState(track) {
    const s = st.tracks[track], w = s?.window, t = nowS(), seat = s?.session;
    if (!w) return null;
    if (seat?.submitted_at) return { label: T[L()].submitted, can: false };
    if (t >= w.upload_until) return { label: T[L()].ended, can: false };
    if (t >= w.ends) return seat?.started_at ? { label: T[L()].back, can: true } : { label: T[L()].ended, can: false };
    if (t < w.opens) return { label: T[L()].opensLater, can: false };
    if (!seat && t >= w.seat_by && st.round.status !== "draft") return { label: T[L()].seatClosed, can: false };
    return { label: seat ? T[L()].reenter : T[L()].enter, can: true };
  }
  function paintLobby(box) {
    const x = T[L()];
    const cards = TRACKS.filter(k => st.tracks[k]).map(k => {
      const w = st.tracks[k].window, s = trackState(k);
      return `<article class="hpho-track" data-track="${k}"><div class="hpho-track-head"><h3>${x.track[k]}</h3><span class="hpho-muted">${x.hours}</span></div>
        <p class="hpho-track-when">${when(w.start_at)} – ${hm(w.ends)}</p>
        <p class="hpho-muted">${x.opensAt(hm(w.opens))} · ${x.seatBy(hm(w.seat_by))}</p>
        <p><button type="button" class="hpho-btn" data-enter="${k}"${s.can ? "" : " disabled"}>${esc(s.label)}</button></p></article>`;
    }).join("");
    box.innerHTML = `<section class="hpho-round hpho-lobby"><h2>${x.entrance}</h2>
      <p class="hpho-muted">${L() === "en" ? "Times are in your time zone." : "시각은 내 시간대 기준입니다."}</p>
      <div class="hpho-tracks">${cards || `<p>${x.noRound}</p>`}</div>
      ${st.error ? `<p class="hpho-form-msg">${esc(st.error)}</p>` : ""}<p class="hpho-check-actions">${leaveBtn()}</p></section>`;
    box.querySelectorAll("[data-enter]").forEach(b => b.addEventListener("click", () => enter(b.dataset.enter)));
    wireLeave(box);
  }
  function paintCheck(box) {
    const x = T[L()], c = st.checks || {}, keys = ["app", "login", "net", "entry", "camera", "mic", "screen", ...(st.quick ? [] : ["face", "voice", "ears"])];
    const row = k => `<li class="${c[k] === true ? "is-ok" : c[k] === false ? "is-bad" : ""}"><span>${x.checks[k]}</span><b>${c[k] === true ? x.ok : c[k] === false ? x.bad : x.wait}</b></li>`;
    const s = st.step;
    const step = s ? `<div class="hpho-step"><h3>${esc(s.title)}</h3><p>${esc(s.text)}</p>${s.quote ? `<p class="hpho-step-quote">${esc(s.quote)}</p>` : ""}${s.cue ? `<p class="hpho-step-cue" id="hphoCue">${esc(s.cue)}</p>` : ""}${s.meter ? `<div class="hpho-meter" aria-hidden="true"><i id="hphoMeter"></i></div>` : ""}${s.button ? `<p><button type="button" class="hpho-btn" id="hphoStepGo">${esc(s.button)}</button></p>` : ""}</div>` : "";
    const done = keys.filter(k => c[k] === true).length;
    box.innerHTML = `<section class="hpho-round hpho-check"><div class="hpho-check-head"><h2>${x.check} · ${x.track[st.track]}</h2><span class="hpho-muted">${done} / ${keys.length}</span></div>
      <div class="hpho-check-grid"><ul class="hpho-checks">${keys.map(row).join("")}</ul>
      <div class="hpho-check-side"><div class="hpho-check-media"><div class="hpho-self-slot" id="hphoSelfSlot"><span>${x.preview}</span></div>
        <p class="hpho-check-actions">${st.error && st.checks?.entry ? `<button type="button" class="hpho-btn" id="hphoExamRetry">${x.retry}</button>` : ""}${leaveBtn()}</p></div>
        <div class="hpho-check-info">${step}${st.error ? `<div class="hpho-check-problem"><p class="hpho-form-msg">${esc(st.error)}</p></div>` : ""}</div></div></div></section>`;
    window.HL_HPHO_PROCTOR?.dock?.(box.querySelector("#hphoSelfSlot"));
    wireLeave(box);
    box.querySelector("#hphoExamRetry")?.addEventListener("click", () => { st.error = null; check(); });
    box.querySelector("#hphoStepGo")?.addEventListener("click", () => { const go = st.step?.go; st.step = { ...st.step, button: null, go: null }; paint(); go?.(); }, { once: true });
  }
  function docTabs(kinds) {
    /* each kind once, in the paper's language when there is one, else the other */
    const out = [];
    for (const kind of kinds) {
      const d = st.docs.find(d => d.kind === kind && d.lang === st.paperLang) || st.docs.find(d => d.kind === kind);
      if (d) out.push(d);
    }
    return out;
  }
  function paintRoom(box) {
    const x = T[L()], w = W(), langs = [...new Set(st.docs.filter(d => d.kind === "paper").map(d => d.lang))];
    const choices = langs.length ? langs : ["ko", "en"];
    const tabs = docTabs(["guide", "writing", "answer"]);
    window.HL_HPHO_PROCTOR?.dock?.(null);
    box.innerHTML = `<section class="hpho-round hpho-room"><h2>${x.room} · ${x.track[st.track]}</h2>
      <div class="hpho-room-grid"><div><p class="hpho-muted">${x.startsIn}</p><p class="hpho-exam-big" id="hphoCountdown">${fmt(w.start_at - nowS())}</p><p class="hpho-muted">${x.autoStart}</p>
        <label class="hpho-lang">${x.paperLang} <select id="hphoPaperLang">${choices.map(l => `<option value="${l}"${l === st.paperLang ? " selected" : ""}>${x.langs[l] || l}</option>`).join("")}</select></label>
        <p class="hpho-muted">${x.paperLangNote}</p></div>
        <ol class="hpho-exam-rules">${x.rules.map(r => `<li>${r}</li>`).join("")}</ol></div>
      ${st.session?.reconnects ? `<p class="hpho-muted">${x.reconnects(st.session.reconnects)}</p>` : ""}
      <h3>${x.docs}</h3>${tabs.length ? `<p class="hpho-muted">${x.docsNote}</p><div id="hphoDocs"></div>` : `<p class="hpho-muted">${x.noDocs}</p>`}
      ${st.error ? `<p class="hpho-form-msg">${esc(st.error)}</p>` : ""}<p class="hpho-check-actions">${leaveBtn()}</p></section>`;
    box.querySelector("#hphoPaperLang").addEventListener("change", async e => {
      const v = e.target.value;
      try { await cmApi("POST", path("lang"), { lang: v }); st.paperLang = v; push("paper_lang", v); st.error = null; }
      catch (err) { st.error = errText(err); e.target.value = st.paperLang; }
      paint();
    });
    if (tabs.length) box.querySelector("#hphoDocs").append(viewer(tabs));
    wireLeave(box);
  }
  function paintExam(box) {
    const x = T[L()];
    window.HL_HPHO_PROCTOR?.dock?.(null);                 /* the camera preview back in the corner, out of the check page */
    if (box.querySelector(".hpho-paper")) return;
    const paper = docTabs(["paper"]), sheets = docTabs(["answer", "writing", "guide"]);
    box.innerHTML = `<section class="hpho-round hpho-paper">${st.session?.reconnects ? `<p class="hpho-muted">${x.reconnects(st.session.reconnects)}</p>` : ""}<div id="hphoPaper"></div></section>`;
    const host = box.querySelector("#hphoPaper");
    if (!paper.length) host.innerHTML = `<p>${x.paperNone}</p>`;
    host.append(viewer([...paper, ...sheets]));
  }
  function paintSubmit(box) {
    const x = T[L()];
    box.innerHTML = `<section class="hpho-round hpho-over"><h2>${x.overTitle}</h2><p class="hpho-over-pen">${x.overPen}</p><p class="hpho-muted">${x.overRec}</p></section>
      <section class="hpho-round hpho-upload"><h2>${x.uploadTitle}</h2><p>${x.uploadHow}</p>
        <div class="hpho-upload-grid"><div class="hpho-self-slot" id="hphoSelfSlot"></div>
          <div><p class="hpho-check-actions"><button type="button" class="hpho-btn" id="hphoShoot">${x.shoot}</button>
            <label class="hpho-btn hpho-btn-quiet">${x.files}<input type="file" id="hphoFiles" accept="image/jpeg,image/png" multiple hidden></label></p>
            <p id="hphoPages"><b>${x.pages(st.pages)}</b></p><div class="hpho-thumbs" id="hphoThumbs"></div>
            <p class="hpho-form-msg" id="hphoUpMsg">${st.error ? esc(st.error) : ""}</p>
            <p><button type="button" class="hpho-btn" id="hphoSubmit">${x.submit}</button></p></div></div></section>`;
    window.HL_HPHO_PROCTOR?.dock?.(box.querySelector("#hphoSelfSlot"));
    const thumbs = box.querySelector("#hphoThumbs");
    for (const u of st.thumbs || []) thumbs.append(Object.assign(document.createElement("img"), { src: u, alt: "" }));
    box.querySelector("#hphoShoot").addEventListener("click", async () => { const b = await window.HL_HPHO_PROCTOR?.still?.(); if (b) addPages([b]); });
    box.querySelector("#hphoFiles").addEventListener("change", e => { addPages([...e.target.files]); e.target.value = ""; });
    box.querySelector("#hphoSubmit").addEventListener("click", () => { if (confirm(st.pages ? x.submitAsk(st.pages) : x.submitEmpty)) submit(); });
  }
  function paint() {
    const x = T[L()], box = document.getElementById("hphoExamMain"); if (!box) return;
    paintBar();
    if (!bridge()) { box.innerHTML = `<section class="hpho-round"><h2>${x.title}</h2><p>${x.appOnly}</p><a class="hpho-btn" href="https://physleague.kr/#/desktop" target="_blank" rel="noopener">${x.appGet}</a></section>`; return; }
    if (st.phase === "lobby") return paintLobby(box);
    if (st.phase === "check") return paintCheck(box);
    if (st.phase === "room") return paintRoom(box);
    if (st.phase === "exam") return paintExam(box);
    if (st.phase === "submit") return paintSubmit(box);
    window.HL_HPHO_PROCTOR?.dock?.(null);
    box.innerHTML = `<section class="hpho-round"><h2>${x.done}</h2><p>${x.doneNote}</p></section>`;
  }

  /* ── the PDF viewer (PDF.js), pages drawn as they scroll near, with tabs and zoom; no download button ── */
  const PDFJS = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/";
  let pdfjs = null;
  const loadPdfjs = () => pdfjs ||= new Promise((ok, fail) => {
    if (window.pdfjsLib) return ok(window.pdfjsLib);
    const s = document.createElement("script"); s.src = PDFJS + "pdf.min.js";
    s.onload = () => { if (!window.pdfjsLib) { pdfjs = null; return fail(Error("pdfjs")); } window.pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS + "pdf.worker.min.js"; ok(window.pdfjsLib); };
    s.onerror = () => { pdfjs = null; fail(Error("pdfjs")); }; document.head.append(s);
  });
  function viewer(files) {
    const x = T[L()], box = document.createElement("div"); box.className = "hpho-pv";
    box.innerHTML = `<div class="hpho-pv-bar">${files.length > 1 ? `<div class="hpho-pv-tabs" role="group">${files.map((f, i) => `<button type="button" aria-pressed="${i === 0}" data-i="${i}">${esc(x.docNames[f.kind])}${f.lang !== st.paperLang ? ` (${f.lang.toUpperCase()})` : ""}</button>`).join("")}</div>` : `<b>${esc(x.docNames[files[0]?.kind] || "")}</b>`}
      <span class="hpho-pv-zoom"><button type="button" data-z="-">−</button><button type="button" data-z="0">${x.zoomFit}</button><button type="button" data-z="+">+</button></span></div><p class="hpho-muted hpho-pv-status"></p><div class="hpho-pv-pages"></div>`;
    const pages = box.querySelector(".hpho-pv-pages"), status = box.querySelector(".hpho-pv-status");
    let doc = null, zoom = 1, token = 0, observer = null, current = null;
    box.addEventListener("contextmenu", e => e.preventDefault());
    async function draw(slot, my) {
      const page = await doc.getPage(Number(slot.dataset.n)); if (my !== token) return;
      const width = Math.max(280, pages.clientWidth - 2) * zoom, base = page.getViewport({ scale: 1 }), scale = width / base.width;
      const ratio = Math.min(Math.max((devicePixelRatio || 1) * 2, 2), 3), vp = page.getViewport({ scale: scale * ratio });
      const c = document.createElement("canvas"); c.width = Math.floor(vp.width); c.height = Math.floor(vp.height); c.style.width = Math.floor(width) + "px";
      await page.render({ canvasContext: c.getContext("2d", { alpha: false }), viewport: vp }).promise; if (my !== token) return;
      slot.style.minHeight = ""; slot.replaceChildren(c);
    }
    function layout() {
      if (!doc) return; const my = ++token; observer?.disconnect(); pages.replaceChildren();
      const width = Math.max(280, pages.clientWidth - 2) * zoom;
      observer = new IntersectionObserver(es => { for (const e of es) if (e.isIntersecting) { observer.unobserve(e.target); draw(e.target, my).catch(() => {}); } }, { rootMargin: "800px 0px" });
      for (let n = 1; n <= doc.numPages; n++) { const s = document.createElement("div"); s.className = "hpho-pv-page"; s.dataset.n = n; s.style.minHeight = Math.round(width * 1.414) + "px"; pages.append(s); observer.observe(s); }
    }
    async function open(f, tries = 0) {
      current = f; status.hidden = false; status.textContent = x.paperLoading; pages.replaceChildren(); doc = null;
      try {
        const lib = await loadPdfjs();
        const url = cmBase() + "/api" + path(`doc?kind=${f.kind}&lang=${f.lang}`);
        doc = await lib.getDocument({ url, httpHeaders: { Authorization: "Bearer " + cmTok() }, isEvalSupported: false, disableRange: true, cMapUrl: PDFJS + "cmaps/", cMapPacked: true, standardFontDataUrl: PDFJS + "standard_fonts/" }).promise;
        if (current !== f) return;
        status.hidden = true; layout();
      } catch (e) {
        status.textContent = x.paperFail;
        if (tries < 5 && box.isConnected) setTimeout(() => current === f && open(f, tries + 1), 4000 * (tries + 1));
      }
    }
    box.querySelectorAll("[data-i]").forEach(b => b.addEventListener("click", () => { box.querySelectorAll("[data-i]").forEach(o => o.setAttribute("aria-pressed", String(o === b))); open(files[+b.dataset.i]); }));
    box.querySelectorAll("[data-z]").forEach(b => b.addEventListener("click", () => { const z = b.dataset.z; zoom = z === "0" ? 1 : Math.max(0.5, Math.min(2.5, zoom + (z === "+" ? 0.25 : -0.25))); layout(); }));
    let rw = 0; new ResizeObserver(() => { const w = pages.clientWidth; if (doc && Math.abs(w - rw) > 40) { rw = w; layout(); } else rw = w; }).observe(pages);
    if (files[0]) open(files[0]);
    return box;
  }

  /* ── the flow ── */
  async function boot() {
    const x = T[L()]; st.error = null; st.phase = "lobby"; paint();
    if (!bridge()) return;
    try { await cmLoadMe(); } catch (e) {}
    if (!(typeof cm === "object" && cm && cm.me)) { st.error = x.login; return paint(); }
    try {
      const d = await cmApi("GET", "/hpho"); sync(d);
      const live = r => (r.tracks || [{ track: "theory", start_at: r.start_at, duration_min: r.duration_min }]).some(k => k.start_at + k.duration_min * 60 + 3600 > nowS());
      st.round = d.rounds.find(r => d.entries?.[r.id] && live(r)) || null;
      st.entry = st.round ? d.entries[st.round.id] : null;
      if (!st.entry) { st.error = x.notReg; return paint(); }
      await loadTracks();
    } catch (e) { st.error = errText(e); }
    paint();
  }
  async function loadTracks() {
    const list = (st.round.tracks || [{ track: "theory" }]).map(k => k.track);
    st.tracks = {};
    for (const k of list) { const s = await cmApi("GET", `/hpho/rounds/${encodeURIComponent(st.round.id)}/exam/${k}/state`); sync(s); st.tracks[k] = s; }
  }
  function enter(track) { st.track = track; st.error = null; st.phase = "check"; st.checks = {}; st.quick = !!st.tracks[track]?.session; check(); }
  async function check() {
    const x = T[L()];
    st.checks = { app: !!bridge(), login: true, net: true, entry: true }; st.phase = "check"; paint();
    try {
      const P = window.HL_HPHO_PROCTOR, pr = P ? await P.check() : {};
      Object.assign(st.checks, { camera: !!pr.camera, mic: !!pr.mic, screen: !!pr.screen });
      if (!pr.camera || !pr.mic) { st.error = x.camNeed; return paint(); }
      if (!pr.screen) { st.error = x.screenNeed; return paint(); }
      /* the face, voice and ear checks: on the first entry; a candidate coming back (already seated) skips them */
      if (!st.quick && !(await quality(P))) return;
      const r = await cmApi("POST", path("checkin"), { client: bridge().client, lang: st.paperLang || L() }); sync(r);
      st.session = r.session; st.tracks[st.track].session = r.session; st.tracks[st.track].window = r.window;
      st.paperLang = r.session.paper_lang; st.seq = Math.max(st.seq, r.seq || 0); st.pages = r.session.pages || 0;
      document.body.classList.remove("hpho-checking"); st.step = null;
      await loadDocs(); route();
    } catch (e) { st.error = errText(e); paint(); }
  }
  async function loadDocs() { try { st.docs = (await cmApi("GET", path("docs"))).docs || []; } catch (e) { st.docs = st.docs || []; } }
  /* where the clock says the candidate is: the waiting room, the exam, the submission page */
  function route() {
    const w = W(), t = nowS();
    if (st.session?.submitted_at || t >= w.upload_until) { st.phase = "done"; finish(); return; }
    if (t < w.start_at) { st.phase = "room"; paint(); return; }
    if (t < w.ends) { start(); return; }
    begin("submit");
  }
  /* the checks a program can judge: the face is well seen, the sentence is read, nothing is worn in the ears. A step
     that passed is not repeated on "check again"; each result also goes into the exam log */
  const waitGo = () => new Promise(res => { st.step.go = res; paint(); });
  async function quality(P) {
    const x = T[L()]; document.body.classList.add("hpho-checking");
    if (st.checks.face !== true && st.passed?.face !== true) {
      st.step = { title: x.faceStep[0], text: x.faceStep[1] }; paint();
      const f = await P.faceCheck(); st.checks.face = f.ok;
      if (!f.ok) { st.step = null; st.error = x.face[f.reason] || x.face.none; paint(); return false; }
    }
    (st.passed ||= {}).face = st.checks.face = true;
    if (st.passed.voice !== true) {
      const sentence = (L() === "en" ? "“I will sit HPhO honestly.”" : "“저는 HPhO에 정직하게 응시하겠습니다.”");
      st.step = { title: x.micStep[0], text: x.micStep[1], quote: sentence, button: x.micStep[2], meter: true }; st.checks.voice = undefined;
      await waitGo();
      st.step = { ...st.step, cue: x.micStep[3] }; paint();
      const m = await P.micCheck((v, cue) => { if (cue === "speak") { const c = document.getElementById("hphoCue"); if (c) { c.textContent = x.micStep[4]; c.classList.add("is-now"); } } const el = document.getElementById("hphoMeter"); if (el) el.style.width = Math.round(v * 100) + "%"; });
      let reason = m.ok ? null : m.reason;
      /* the level said a sentence-like voice was there: the server's model checks the words */
      if (!reason && m.wav) {
        st.step = { ...st.step, cue: x.micStep[5], meter: false }; paint();
        try { const r = await sendForm("voicecheck", { audio: m.wav, lang: L() }); if (!r.unavailable && !r.said) reason = "not_said"; }
        catch (e) { reason = "failed"; }
      }
      st.checks.voice = !reason;
      if (reason) { st.step = null; st.error = x.mic[reason] || x.mic.short; paint(); return false; }
      st.passed.voice = true;
    }
    st.checks.voice = true;
    if (st.passed.ears !== true) {
      st.step = { title: x.earStep[0], text: x.earStep[1], button: x.earStep[2] }; st.checks.ears = undefined;
      await waitGo();
      const shots = await P.earShots(name => { st.step = { title: x.earStep[0], text: x.ear[name] }; paint(); });
      let r = null;
      if (shots) try { r = await sendForm("earcheck", { first: shots.first, second: shots.second }); } catch (e) { r = null; }
      st.earTries = (st.earTries || 0) + 1;
      const verdicts = r && !r.unavailable ? [r.first, r.second] : [];
      /* a device: always stop. Unclear photos: try again, but after three tries the exam is not held up (the photos and verdict are kept) */
      const why = !r ? "failed" : verdicts.includes("device") ? "device" : verdicts.includes("unclear") && st.earTries < 3 ? "unclear" : null;
      st.checks.ears = !why;
      if (why) { st.step = null; st.error = x.ear[why]; paint(); return false; }
      st.passed.ears = true;
    }
    st.checks.ears = true;
    return true;
  }
  /* proctoring on (once): the window's events, the camera and the screen */
  function watch() {
    const b = bridge();
    if (!st.unsub) st.unsub = b.onEvent(e => { if (e && typeof e.kind === "string") { push(e.kind, e.detail); if (["focus_lost", "display_change", "screen_unlocked"].includes(e.kind)) window.HL_HPHO_PROCTOR?.snap(e.kind); } });
    if (!st.watching) { st.watching = true; window.HL_HPHO_PROCTOR?.start({ onEvent: (kind, detail) => push(kind, detail), upload: uploadSnap }); }
    b.started?.();
    clearInterval(st.flushTimer); st.flushTimer = setInterval(flush, 10000);
  }
  async function start() {
    const b = bridge(); st.error = null;
    try {
      const r = await cmApi("POST", path("start"), { client: b.client }); sync(r);
      st.seq = Math.max(st.seq, r.seq || 0); st.paperLang = r.paper_lang || st.paperLang;
      await loadDocs();
      st.phase = "exam"; watch();
      push("window_ready", r.resumed ? "resumed" : "started");
      flush(); paint();
    } catch (e) { st.error = errText(e); if (e?.code === "exam_over") return begin("submit"); paint(); }
  }
  /* the time is over: the paper goes, the recording goes on (faster, marked after_time), the answers go up */
  function begin(phase) {
    st.phase = phase; watch();
    push("time_over", st.track);
    window.HL_HPHO_PROCTOR?.pace?.(10, 20, "after_time");   /* two images a time: under the server's 120 per 10 min */
    flush(); paint();
  }
  function uploadSnap(blob, source, reason) { sendForm("snap", { image: blob, source, reason }).catch(() => {}); }
  /* a page: at most 2400 px on its longest side, JPEG, under the server's 4 MB */
  async function shrink(file) {
    const img = await createImageBitmap(file), k = Math.min(1, 2400 / Math.max(img.width, img.height));
    const c = document.createElement("canvas"); c.width = Math.round(img.width * k); c.height = Math.round(img.height * k); c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
    for (const q of [0.88, 0.75, 0.6]) { const b = await new Promise(res => c.toBlob(res, "image/jpeg", q)); if (b && b.size < 3.8e6) return b; }
    return null;
  }
  async function addPages(files) {
    const x = T[L()], msg = () => document.getElementById("hphoUpMsg");
    for (const f of files) {
      if (msg()) msg().textContent = x.uploading;
      try {
        const b = await shrink(f); if (!b) throw { code: "upload_too_large" };
        const page = st.pages + 1;
        await sendForm("answer", { image: b, page: String(page) });
        st.pages = page; push("answer_page", String(page));
        (st.thumbs ||= []).push(URL.createObjectURL(b)); st.error = null;
      } catch (e) { st.error = e?.code ? errText(e) : x.uploadFail; break; }
    }
    paint();
  }
  async function submit() {
    try { await cmApi("POST", path("submit"), {}); } catch (e) { if (e?.code !== "upload_closed") { st.error = errText(e); return paint(); } }
    st.phase = "done"; finish();
  }
  async function finish() {
    clearInterval(st.flushTimer);
    push("submitted", String(st.pages)); await flush().catch(() => {});
    window.HL_HPHO_PROCTOR?.stop(); st.watching = false;
    for (const u of st.thumbs || []) URL.revokeObjectURL(u); st.thumbs = [];
    bridge()?.finished?.(); paint();
  }
  /* the server's clock and the exam's times again (every 30 s in the entrance and the waiting room; the exam and the
     submission page sync with every heartbeat): a clock that drifted, or a time the organisers moved, is followed */
  async function resync() {
    if (!st.round || st.resyncing) return; st.resyncing = true;
    try {
      for (const k of Object.keys(st.tracks)) { const s = await cmApi("GET", path("state", k)); sync(s); st.tracks[k] = { ...st.tracks[k], window: s.window, session: s.session || st.tracks[k].session }; }
      if (st.phase === "lobby") paint();
    } catch (e) {} finally { st.resyncing = false; }
  }
  function tick() {
    if (!document.getElementById("hphoExamMain")) return clearInterval(st.timer);
    if (["lobby", "room"].includes(st.phase) && ++st.ticks % 30 === 0) resync();
    const w = W(), t = nowS();
    if (st.phase === "lobby") { if (st.round) document.querySelectorAll("[data-enter]").forEach(b => { const s = trackState(b.dataset.enter); b.disabled = !s.can; b.textContent = s.label; }); return; }
    if (!w) return;
    if (st.phase === "room") { const c = document.getElementById("hphoCountdown"); if (c) c.textContent = fmt(w.start_at - t); if (t >= w.start_at && !st.starting) { st.starting = true; start().finally(() => { st.starting = false; }); } return; }
    if (st.phase === "exam" && t >= w.ends) return begin("submit");
    if (st.phase === "submit" && t >= w.upload_until) { st.phase = "done"; finish(); return; }
    paintBar();
  }
  function mount() {
    clearInterval(st.timer); clearInterval(st.flushTimer);
    st = { ...st, phase: "lobby", session: null, error: null, queue: [], step: null, earTries: 0, track: null, docs: [], pages: 0, thumbs: [], ticks: 0 };
    if (!st.wired) { st.wired = true;
      document.addEventListener("visibilitychange", () => { if (["exam", "submit"].includes(st.phase)) push(document.hidden ? "page_hidden" : "page_visible"); });
      addEventListener("offline", () => { if (["exam", "submit"].includes(st.phase)) push("network_lost"); });
      addEventListener("online", () => { if (["exam", "submit"].includes(st.phase)) { push("network_back"); flush(); } }); }
    boot();
    st.timer = setInterval(tick, 1000);
  }
  window.HL_HPHO_EXAM = { view, mount, resync };
})();
