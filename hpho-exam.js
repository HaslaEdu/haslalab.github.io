/* HPhO exam page (#/hpho/exam), modelled on MIPT's online rounds: a technical check, a waiting room, the exam itself with
   one page open and the recording kept continuous, then an hour to upload the answer photos. It runs only inside the
   HaslaEdu desktop app's exam window, whose preload gives it window.haslaExam (the app's name and version, and the
   window's proctoring events). The page sends those events with its own heartbeat to the server
   (community/src/hpho-exam.js); no token or account data passes to the native shell. */
(() => {
  const L = () => (typeof lang === "string" && lang === "en") ? "en" : "ko";
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const T = {
    ko: { title: "HPhO 시험", appOnly: "HPhO는 하슬라에듀 데스크톱 앱의 시험 창에서만 응시할 수 있습니다.", appGet: "데스크톱 앱 내려받기",
      check: "기술 점검", checks: { app: "하슬라에듀 데스크톱 앱", net: "서버 연결", entry: "참가 접수", login: "로그인", camera: "웹캠", mic: "마이크", screen: "화면 기록", face: "얼굴 인식", voice: "마이크 소리", ears: "귀 검사 (이어폰)" }, retry: "다시 점검", preview: "카메라 미리보기", camNeed: "웹캠·마이크·화면 기록이 모두 켜져야 응시할 수 있습니다. 다른 프로그램이 카메라를 쓰고 있지 않은지 확인하세요.",
      screenNeed: "화면 기록을 시작하지 못했습니다. 앱을 최신 버전(0.5.3 이상)으로 업데이트한 뒤 다시 점검하세요.",
      faceStep: ["얼굴 확인", "카메라를 정면으로 바라보세요. 얼굴 전체가 오른쪽 아래 미리보기 가운데에 오도록 앉아 주세요."],
      face: { no_video: "카메라 영상이 들어오지 않습니다. 다른 프로그램이 카메라를 쓰고 있지 않은지 확인하세요.", detector: "얼굴 인식 기능을 불러오지 못했습니다. 인터넷 연결을 확인한 뒤 다시 점검하세요.", none: "얼굴이 보이지 않습니다. 카메라를 정면으로 바라보세요.", many: "화면에 두 사람 이상이 보입니다. 혼자 있는 곳에서 응시하세요.", dark: "얼굴이 너무 어둡습니다. 조명을 켜거나 창 쪽을 바라보고 앉으세요.", small: "얼굴이 너무 작게 보입니다. 카메라에 조금 더 가까이 앉으세요.", off: "얼굴이 화면 가장자리에 있습니다. 미리보기 가운데로 오도록 자리를 옮기세요." },
      micStep: ["마이크 확인", "버튼을 누른 뒤 아래 문장을 평소 목소리로 읽어 주세요.", "“저는 HPhO에 정직하게 응시하겠습니다.”", "마이크 점검 시작"],
      mic: { no_mic: "마이크를 찾지 못했습니다. 마이크를 연결하고 다시 점검하세요.", no_audio: "소리를 분석하지 못했습니다. 다시 점검하세요.", silent: "소리가 전혀 들리지 않습니다. 마이크가 음소거되어 있지 않은지, 올바른 마이크가 선택되었는지 확인하세요.", quiet: "목소리가 너무 작게 들립니다. 마이크에 가까이 앉아 조금 더 크게 읽어 주세요." },
      earStep: ["귀 검사", "이어폰·헤드폰을 끼고 있지 않은지 확인합니다. 머리카락을 귀 뒤로 넘기고 버튼을 누르세요.", "귀 검사 시작"],
      ear: { first: "고개를 천천히 한쪽으로 돌려 귀가 카메라에 보이게 하고, 잠시 멈추세요.", second: "이번에는 반대쪽으로 고개를 돌려 다른 쪽 귀를 보여 주세요.", done: "확인하는 중…", device: "귀에 이어폰이나 헤드폰 같은 기기가 보입니다. 모두 빼고 다시 검사하세요. 보청기를 써야 한다면 시험 전에 운영진에게 알려 주세요.", unclear: "귀가 잘 보이지 않았습니다. 머리카락을 넘기고 밝은 곳에서 고개를 조금 더 돌려 다시 검사하세요.", failed: "사진을 보내지 못했습니다. 다시 검사하세요." }, ok: "확인", bad: "문제 있음", wait: "확인 중…", ok: "확인", bad: "문제 있음", wait: "확인 중…",
      notReg: "이 회차에 접수하지 않았습니다.", login: "로그인하세요.", room: "대기실", startsIn: "시험 시작까지", start: "시험 시작", candidate: "수험번호",
      left: "남은 시간", end: "시험 종료", endAsk: "시험을 종료할까요? 종료하면 다시 돌아올 수 없습니다.", rules: ["시험 중에는 이 창만 사용하세요. 다른 프로그램과 웹사이트는 사용할 수 없습니다.", "창을 벗어나거나 화면이 잠기면 기록됩니다. 녹화가 끊기지 않도록 이 창을 유지하세요.", "답안지에는 수험번호만 적으세요."],
      problems: "문제", problemsSoon: "문제는 시험 시작 시각에 이 화면에 공개됩니다.", leave: "시험 창 닫기", over: "시험이 끝났습니다", upload: until => `답안 사진은 ${until}까지 올려 주세요.`, conn: "연결", connOk: "정상", connBad: "끊김 · 다시 연결 중", proctor: "감독", proctorOn: "기록 중" },
    en: { title: "HPhO exam", appOnly: "HPhO can only be sat in the exam window of the HaslaEdu desktop app.", appGet: "Get the desktop app",
      check: "Technical check", checks: { app: "HaslaEdu desktop app", net: "Server connection", entry: "Registration", login: "Signed in", camera: "Webcam", mic: "Microphone", screen: "Screen recording", face: "Face", voice: "Microphone sound", ears: "Ear check (earphones)" }, retry: "Check again", preview: "Camera preview", camNeed: "The webcam, microphone and screen recording must all be on to sit the exam. Make sure no other program is using the camera.",
      screenNeed: "Screen recording could not start. Update the app to the latest version (0.5.3 or later), then check again.",
      faceStep: ["Face check", "Look straight at the camera, with your whole face in the middle of the preview at the bottom right."],
      face: { no_video: "No picture from the camera. Make sure no other program is using it.", detector: "Face detection could not load. Check your internet connection and try again.", none: "Your face cannot be seen. Look straight at the camera.", many: "More than one person is in view. Sit the exam alone.", dark: "Your face is too dark. Turn on a light or face a window.", small: "Your face looks too small. Sit a little closer to the camera.", off: "Your face is at the edge of the picture. Move so it is in the middle of the preview." },
      micStep: ["Microphone check", "Press the button, then read the sentence below in your normal voice.", "“I will sit HPhO honestly.”", "Start the microphone check"],
      mic: { no_mic: "No microphone was found. Connect one and check again.", no_audio: "The sound could not be analysed. Check again.", silent: "No sound at all. Make sure the microphone is not muted and the right one is selected.", quiet: "Your voice is too quiet. Sit closer to the microphone and read a little louder." },
      earStep: ["Ear check", "This checks that you are not wearing earphones or headphones. Tuck your hair behind your ears and press the button.", "Start the ear check"],
      ear: { first: "Slowly turn your head to one side so one ear faces the camera, and hold still.", second: "Now turn to the other side to show the other ear.", done: "Checking…", device: "Earphones, headphones or another device can be seen in or on your ear. Take them off and check again. If you need a hearing aid, tell the organisers before the exam.", unclear: "Your ears could not be seen clearly. Move your hair aside, use more light, turn your head a little further and check again.", failed: "The photos could not be sent. Check again." }, ok: "OK", bad: "Problem", wait: "Checking…", ok: "OK", bad: "Problem", wait: "Checking…",
      notReg: "You are not registered for this round.", login: "Please sign in.", room: "Waiting room", startsIn: "Exam starts in", start: "Start the exam", candidate: "Candidate number",
      left: "Time left", end: "Finish exam", endAsk: "Finish the exam? You cannot come back once you finish.", rules: ["Use only this window during the exam. Other programs and websites are not allowed.", "Leaving the window or locking the screen is recorded. Keep this window open so the recording stays continuous.", "Write only your candidate number on the answer sheets."],
      problems: "Problems", problemsSoon: "The problems appear here at the start time.", leave: "Close the exam window", over: "The exam is over", upload: until => `Upload your answer photos by ${until}.`, conn: "Connection", connOk: "Online", connBad: "Lost · reconnecting", proctor: "Proctoring", proctorOn: "Recording" },
  };
  const bridge = () => (window.haslaExam && typeof window.haslaExam.onEvent === "function") ? window.haslaExam : null;
  let st = { round: null, entry: null, session: null, phase: "check", online: true, seq: 0, queue: [], timer: 0, flushTimer: 0, unsub: null };
  const fmt = sec => { sec = Math.max(0, Math.floor(sec)); const h = Math.floor(sec / 3600), m = Math.floor(sec % 3600 / 60), s = sec % 60; return (h ? h + ":" : "") + String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0"); };
  const skew = () => st.skew || 0, nowS = () => Math.floor(Date.now() / 1000) + skew();
  const path = a => `/hpho/rounds/${encodeURIComponent(st.round.id)}/exam/${a}`;

  function push(kind, detail) {
    try { st.seq = Math.max(st.seq, +sessionStorage.getItem("hphoSeq") || 0) + 1; sessionStorage.setItem("hphoSeq", st.seq); } catch (e) { st.seq++; }
    st.queue.push({ seq: st.seq, t: nowS(), kind, ...(detail ? { detail: String(detail).slice(0, 200) } : {}) });
  }
  async function flush() {
    if (!st.session || st.phase !== "exam") return;
    if (!st.queue.length) push("heartbeat");
    const batch = st.queue.splice(0, 100);
    try { const r = await cmApi("POST", path("events"), { events: batch }); st.online = true; if (r.now) st.skew = r.now - Math.floor(Date.now() / 1000); }
    catch (e) { st.queue.unshift(...batch); st.online = false; if (e?.code === "exam_over") return finish(true); }
    paintBar();
  }

  function view() {
    return `<div class="shell hpho hpho-exam"><div class="hpho-exam-bar" id="hphoExamBar"></div><div id="hphoExamMain"><p class="hpho-muted">…</p></div></div>`;
  }
  function paintBar() {
    const x = T[L()], bar = document.getElementById("hphoExamBar"); if (!bar) return;
    const left = st.session ? st.session.ends_at - nowS() : null;
    bar.innerHTML = `<b class="hpho-exam-title"><img class="hpho-exam-icon hpho-logo-light" src="logo/brand/hpho-icon-light.svg?v=20261109-hpho" alt=""><img class="hpho-exam-icon hpho-logo-dark" src="logo/brand/hpho-icon-dark.svg?v=20261109-hpho" alt="" aria-hidden="true">${x.title}${st.round ? " · " + (st.round.status === "draft" ? (L() === "en" ? "Practice exam" : "모의 시험") : esc(st.round.title[L()])) : ""}</b>
      ${st.entry ? `<span>${x.candidate} <b class="hpho-no">${esc(st.entry.candidate_no)}</b></span>` : ""}
      ${st.phase === "exam" ? `<span class="hpho-light ${st.online ? "is-ok" : "is-bad"}">${x.conn}: ${st.online ? x.connOk : x.connBad}</span><span class="hpho-light is-ok">${x.proctor}: ${x.proctorOn}</span>
        <span class="hpho-exam-clock${left < 600 ? " is-low" : ""}">${x.left} <b>${fmt(left)}</b></span><button type="button" class="hpho-link" id="hphoExamEnd">${x.end}</button>` : ""}`;
    bar.querySelector("#hphoExamEnd")?.addEventListener("click", () => { if (confirm(x.endAsk)) finish(false); });
  }
  function paint() {
    const x = T[L()], box = document.getElementById("hphoExamMain"); if (!box) return;
    paintBar();
    if (!bridge()) { box.innerHTML = `<section class="hpho-round"><h2>${x.title}</h2><p>${x.appOnly}</p><a class="hpho-btn" href="https://physleague.kr/#/desktop" target="_blank" rel="noopener">${x.appGet}</a></section>`; return; }
    if (st.phase === "check") {
      const c = st.checks || {}, row = k => `<li class="${c[k] === true ? "is-ok" : c[k] === false ? "is-bad" : ""}"><span>${x.checks[k]}</span><b>${c[k] === true ? x.ok : c[k] === false ? x.bad : x.wait}</b></li>`;
      const s = st.step;
      const step = s ? `<div class="hpho-step"><h3>${esc(s.title)}</h3><p>${esc(s.text)}</p>${s.quote ? `<p class="hpho-step-quote">${esc(s.quote)}</p>` : ""}${s.meter ? `<div class="hpho-meter" aria-hidden="true"><i id="hphoMeter"></i></div>` : ""}${s.button ? `<p><button type="button" class="hpho-btn" id="hphoStepGo">${esc(s.button)}</button></p>` : ""}</div>` : "";
      /* two columns: the list of checks on the left; the camera preview, the current step and any problem on the right */
      const done = ["app", "login", "net", "entry", "camera", "mic", "screen", "face", "voice", "ears"].filter(k => c[k] === true).length;
      box.innerHTML = `<section class="hpho-round hpho-check"><div class="hpho-check-head"><h2>${x.check}</h2><span class="hpho-muted">${done} / 10</span></div>
        <div class="hpho-check-grid"><ul class="hpho-checks">${["app", "login", "net", "entry", "camera", "mic", "screen", "face", "voice", "ears"].map(row).join("")}</ul>
        <div class="hpho-check-side"><div class="hpho-check-media"><div class="hpho-self-slot" id="hphoSelfSlot"><span>${x.preview}</span></div>
          <p class="hpho-check-actions">${st.error && st.checks?.entry ? `<button type="button" class="hpho-btn" id="hphoExamRetry">${x.retry}</button>` : ""}${bridge()?.leave ? `<button type="button" class="hpho-link" id="hphoExamLeave">${x.leave}</button>` : ""}</p></div>
          <div class="hpho-check-info">${step}${st.error ? `<div class="hpho-check-problem"><p class="hpho-form-msg">${esc(st.error)}</p></div>` : ""}</div></div></div></section>`;
      window.HL_HPHO_PROCTOR?.dock?.(box.querySelector("#hphoSelfSlot"));
      box.querySelector("#hphoExamLeave")?.addEventListener("click", () => bridge()?.leave?.());
      box.querySelector("#hphoExamRetry")?.addEventListener("click", () => { st.error = null; check(); });
      box.querySelector("#hphoStepGo")?.addEventListener("click", () => { const go = st.step?.go; st.step = { ...st.step, button: null, go: null }; paint(); go?.(); }, { once: true });
      return;
    }
    if (st.phase === "room") {
      const wait = st.round.start_at - nowS();
      window.HL_HPHO_PROCTOR?.dock?.(null);
      box.innerHTML = `<section class="hpho-round hpho-room"><h2>${x.room}</h2><p class="hpho-muted">${x.startsIn}</p><p class="hpho-exam-big">${fmt(wait)}</p>
        <ol class="hpho-exam-rules">${x.rules.map(r => `<li>${r}</li>`).join("")}</ol>
        <p class="hpho-exam-actions"><button type="button" class="hpho-btn" id="hphoExamStart"${wait > 0 ? " disabled" : ""}>${x.start}</button> ${bridge()?.leave ? `<button type="button" class="hpho-link" id="hphoExamLeave">${x.leave}</button>` : ""}</p>${st.error ? `<p class="hpho-form-msg">${esc(st.error)}</p>` : ""}</section>`;
      box.querySelector("#hphoExamStart").addEventListener("click", start);
      box.querySelector("#hphoExamLeave")?.addEventListener("click", () => bridge()?.leave?.());
      return;
    }
    if (st.phase === "exam") {
      if (!box.querySelector(".hpho-paper")) box.innerHTML = `<section class="hpho-round hpho-paper"><h2>${x.problems}</h2><p class="hpho-muted">${x.problemsSoon}</p></section>`;
      return;
    }
    const until = new Date((st.uploadUntil || 0) * 1000).toLocaleString(L() === "en" ? "en-GB" : "ko-KR", { timeStyle: "short", dateStyle: "medium" });
    box.innerHTML = `<section class="hpho-round"><h2>${x.over}</h2><p>${x.upload(esc(until))}</p></section>`;
  }

  async function check() {
    const x = T[L()]; st.checks = { app: !!bridge() }; paint();
    if (!bridge()) return;
    try { await cmLoadMe(); } catch (e) {}
    st.checks.login = !!(typeof cm === "object" && cm && cm.me); paint();
    if (!st.checks.login) { st.error = x.login; return paint(); }
    try {
      const d = await cmApi("GET", "/hpho"); st.checks.net = true;
      st.round = d.rounds.find(r => d.entries?.[r.id] && r.start_at + r.duration_min * 60 > (d.now || nowS())) || null;
      st.entry = st.round ? d.entries[st.round.id] : null; st.checks.entry = !!st.entry; if (d.now) st.skew = d.now - Math.floor(Date.now() / 1000);
      if (!st.entry) { st.error = x.notReg; return paint(); }
      const s = await cmApi("GET", `/hpho/rounds/${encodeURIComponent(st.round.id)}/exam/state`);
      if (s.session?.ended_at) { st.phase = "over"; st.uploadUntil = s.window.upload_until; return paint(); }
      const P = window.HL_HPHO_PROCTOR, pr = P ? await P.check() : {};
      Object.assign(st.checks, { camera: !!pr.camera, mic: !!pr.mic, screen: !!pr.screen });
      if (!pr.camera || !pr.mic) { st.error = x.camNeed; return paint(); }
      if (!pr.screen) { st.error = x.screenNeed; return paint(); }
      if (!s.session && !(await quality(P))) return;
      st.phase = "room"; st.step = null; document.body.classList.remove("hpho-checking"); paint();
      if (s.session) start();
    } catch (e) { st.checks.net = false; st.error = e?.code || "network"; paint(); }
  }
  /* the checks a program can judge: the face is well seen, the voice is heard, nothing is worn in the ears. A step that
     passed is not repeated on "check again"; each result also goes into the exam log */
  const waitGo = () => new Promise(res => { st.step.go = res; paint(); });
  async function quality(P) {
    const x = T[L()]; document.body.classList.add("hpho-checking");
    if (st.checks.face !== true) {
      st.step = { title: x.faceStep[0], text: x.faceStep[1] }; st.checks.face = undefined; paint();
      const f = await P.faceCheck(); st.checks.face = f.ok; push("face_check", f.ok ? "ok" : f.reason);
      if (!f.ok) { st.step = null; st.error = x.face[f.reason] || x.face.none; paint(); return false; }
    }
    if (st.checks.voice !== true) {
      st.step = { title: x.micStep[0], text: x.micStep[1], quote: x.micStep[2], button: x.micStep[3], meter: true }; st.checks.voice = undefined;
      await waitGo();
      const m = await P.micCheck(v => { const el = document.getElementById("hphoMeter"); if (el) el.style.width = Math.round(v * 100) + "%"; });
      st.checks.voice = m.ok; push("mic_check", m.ok ? "ok" : m.reason);
      if (!m.ok) { st.step = null; st.error = x.mic[m.reason] || x.mic.silent; paint(); return false; }
    }
    if (st.checks.ears !== true) {
      st.step = { title: x.earStep[0], text: x.earStep[1], button: x.earStep[2] }; st.checks.ears = undefined;
      await waitGo();
      const shots = await P.earShots(name => { st.step = { title: x.earStep[0], text: x.ear[name] }; paint(); });
      let r = null;
      if (shots) try {
        const fd = new FormData(); fd.set("first", shots.first, "first.jpg"); fd.set("second", shots.second, "second.jpg");
        const res = await fetch(cmBase() + "/api" + path("earcheck"), { method: "POST", headers: { Authorization: "Bearer " + cmTok() }, body: fd });
        r = res.ok ? await res.json() : null;
      } catch (e) { r = null; }
      st.earTries = (st.earTries || 0) + 1;
      const verdicts = r && !r.unavailable ? [r.first, r.second] : [];
      /* a device: always stop. Unclear photos: try again, but after three tries the exam is not held up (the photos and verdict are kept) */
      const why = !r ? "failed" : verdicts.includes("device") ? "device" : verdicts.includes("unclear") && st.earTries < 3 ? "unclear" : null;
      st.checks.ears = !why;
      if (why) { st.step = null; st.error = x.ear[why]; paint(); return false; }
    }
    return true;
  }
  async function start() {
    const b = bridge(); st.error = null;
    try {
      const r = await cmApi("POST", path("start"), { client: b.client });
      st.session = { ends_at: r.ends_at }; st.phase = "exam";
      if (!st.unsub) st.unsub = b.onEvent(e => { if (e && typeof e.kind === "string") { push(e.kind, e.detail); if (["focus_lost", "display_change", "screen_unlocked"].includes(e.kind)) window.HL_HPHO_PROCTOR?.snap(e.kind); } });
      window.HL_HPHO_PROCTOR?.start({ onEvent: (kind, detail) => push(kind, detail), upload: uploadSnap });
      push("window_ready", r.resumed ? "resumed" : "started"); b.started?.();
      clearInterval(st.flushTimer); st.flushTimer = setInterval(flush, 10000); flush(); paint();
    } catch (e) { st.error = e?.code || "network"; paint(); }
  }
  /* a snapshot goes to the server as it is taken; a failed one is not retried (the next comes within a minute) */
  function uploadSnap(blob, source, reason) {
    const fd = new FormData(); fd.set("image", blob, "snap.jpg"); fd.set("source", source); fd.set("reason", reason);
    fetch(cmBase() + "/api" + path("snap"), { method: "POST", headers: { Authorization: "Bearer " + cmTok() }, body: fd }).catch(() => {});
  }
  async function finish(byClock) {
    clearInterval(st.flushTimer); if (st.phase !== "exam") return;
    window.HL_HPHO_PROCTOR?.stop();
    await flush().catch(() => {});
    try { const r = await cmApi("POST", path("end"), {}); st.uploadUntil = r.upload_until; } catch (e) {}
    st.phase = "over"; bridge()?.finished?.(); paint();
  }
  function mount() {
    clearInterval(st.timer); st = { ...st, phase: "check", session: null, error: null, queue: [], step: null, earTries: 0 };
    if (!st.wired) { st.wired = true;
    document.addEventListener("visibilitychange", () => { if (st.phase === "exam") push(document.hidden ? "page_hidden" : "page_visible"); });
    addEventListener("offline", () => { if (st.phase === "exam") push("network_lost"); });
    addEventListener("online", () => { if (st.phase === "exam") { push("network_back"); flush(); } }); }
    check();
    st.timer = setInterval(() => { if (!document.getElementById("hphoExamMain")) return clearInterval(st.timer);
      if (st.phase === "exam" && st.session && nowS() >= st.session.ends_at) finish(true);
      if (st.phase === "room") { const b = document.getElementById("hphoExamStart"), big = document.querySelector(".hpho-exam-big"), w = st.round.start_at - nowS(); if (big) big.textContent = fmt(w); if (b) b.disabled = w > 0; }
      else paintBar(); }, 1000);
  }
  window.HL_HPHO_EXAM = { view, mount };
})();
