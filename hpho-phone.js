/* HPhO phone (#/hpho/phone/<code>): the candidate's phone as the second camera, Monito-style. The exam page shows a QR
   with a one-time code; the phone opens this page from it (no sign-in on the phone) and
   1. scans the room slowly, view by view (the walls, behind, the ceiling, the desk top, under the desk): about eight
      seconds of turning per view, frames every second; a sweep too fast to be sharp is asked again before anything is
      sent, and the frames of each view are judged by a model on the server (community/src/hpho-exam.js phoneRoute);
   2. is stood 1–1.5 m to the side of or behind the candidate, where it sees the candidate, the hands, the desk and the
      screen, and a model confirms that from a photo;
   3. then watches: a photo every 15 s and a heartbeat, until the answers are in. The exam page shows whether it is
      connected, and a phone that drops out is recorded. */
(() => {
  const L = () => (typeof lang === "string" && lang === "en") ? "en" : "ko";
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const SWEEP = 8, KEEP = 8;
  const T = {
    ko: { title: "HPhO 휴대폰 감독", intro: "이 휴대폰은 시험 동안 두 번째 카메라로 쓰입니다. 먼저 방을 천천히 비춰 검사하고, 그다음 옆이나 뒤에 세워 두면 됩니다. 시험이 끝날 때까지 이 화면을 켜 두세요(충전기 연결).", cam: "카메라 켜기", camFail: "카메라를 켜지 못했습니다. 브라우저의 카메라 권한을 허용한 뒤 다시 시도하세요.",
      bad: "이 QR은 만료되었거나 잘못되었습니다. 시험 창에 보이는 새 QR을 다시 찍으세요.", over: "시험이 끝났습니다. 이 화면을 닫아도 됩니다.", net: "서버에 연결하지 못했습니다. 다시 시도하는 중…",
      scanTitle: (i, n) => `주변 스캔 ${i} / ${n}`, views: { front: "앞쪽 벽", left: "왼쪽", right: "오른쪽", back: "뒤쪽 (의자 뒤)", ceiling: "천장", desk: "책상 위 전체 (모니터 뒤와 주변까지)", under: "책상 아래와 의자 주변 바닥" },
      how: { front: "앞쪽 벽을 왼쪽 끝에서 오른쪽 끝까지", left: "왼쪽 벽을 위에서 아래까지", right: "오른쪽 벽을 위에서 아래까지", back: "뒤쪽을 왼쪽 끝에서 오른쪽 끝까지", ceiling: "천장을 한쪽 끝에서 다른 쪽 끝까지", desk: "책상 위를 한쪽 끝에서 다른 쪽 끝까지, 모니터 뒤도", under: "책상 아래와 발밑, 의자 주변을" },
      sweep: v => `${v} 8초 동안 아주 천천히 비추세요. 버튼을 누르면 시작합니다.`, go: "스캔 시작", slow: "천천히…", fast: "너무 빨라요! 더 천천히", judging: "AI가 확인하는 중…",
      redo: "흐리거나 너무 빨리 돌려서 잘 보이지 않았습니다. 더 천천히, 밝게 다시 비춰 주세요.", blocked: list => `${list}이(가) 보입니다. 치우거나 방 밖으로 옮긴 뒤 이 방향을 다시 비춰 주세요.`, unavailable: "AI 확인 서버가 응답하지 않았습니다. 다시 비춰 주세요.", ok: "확인됨", notes: "확인됨 (책·필기는 감독관이 검토합니다)",
      found: { person: "다른 사람", phone: "휴대폰·스마트워치·태블릿", screen: "다른 화면", headset: "이어폰·헤드셋", notes: "책·필기" },
      placeTitle: "휴대폰 세워 두기", place: "휴대폰을 옆이나 뒤쪽 1~1.5m 거리에 가로로 세워 두세요. 화면에 본인(머리와 몸), 두 손, 책상 위, 컴퓨터 화면이 모두 보여야 합니다.", placeGo: "이 위치로 확인", placeMissing: list => `화면에 ${list}이(가) 잘 보이지 않습니다. 위치를 옮기고 다시 확인하세요.`,
      parts: { person: "본인", hands: "두 손", desk: "책상 위", screen: "컴퓨터 화면" }, watchTitle: "감독 중", watch: "이 화면을 끄거나 다른 앱으로 나가지 마세요. 충전기를 연결해 두세요. 시험이 끝나면 자동으로 멈춥니다.", hidden: "휴대폰 감독 화면을 벗어났습니다. 이 기록은 감독관에게 전달됩니다." },
    en: { title: "HPhO phone proctoring", intro: "This phone is a second camera during the exam. First show the room slowly for the check, then stand the phone to your side or behind you. Keep this screen on until the exam ends (connect a charger).", cam: "Turn on the camera", camFail: "The camera could not start. Allow camera access in the browser, then try again.",
      bad: "This QR code has expired or is wrong. Scan the new QR shown in the exam window.", over: "The exam is over. You can close this page.", net: "Could not reach the server. Retrying…",
      scanTitle: (i, n) => `Room scan ${i} / ${n}`, views: { front: "The wall in front", left: "The left side", right: "The right side", back: "Behind you (behind the chair)", ceiling: "The ceiling", desk: "The whole desk (behind the monitor too)", under: "Under the desk, the floor around the chair" },
      how: { front: "the front wall from its left end to its right end", left: "the left wall from top to bottom", right: "the right wall from top to bottom", back: "behind you from left to right", ceiling: "the ceiling from one end to the other", desk: "the desk from one end to the other, behind the monitor too", under: "under the desk, your feet and around the chair" },
      sweep: v => `Show ${v} very slowly, over eight seconds. Press the button to start.`, go: "Start the scan", slow: "Slowly…", fast: "Too fast! Slower", judging: "The AI is checking…",
      redo: "It was blurred or turned too fast to see. Sweep again, more slowly and with more light.", blocked: list => `${list} can be seen. Remove it or take it out of the room, then show this side again.`, unavailable: "The AI check did not answer. Sweep again.", ok: "OK", notes: "OK (books or notes are reviewed by a proctor)",
      found: { person: "another person", phone: "a phone, smartwatch or tablet", screen: "another screen", headset: "earphones or a headset", notes: "books or notes" },
      placeTitle: "Stand the phone", place: "Stand the phone sideways 1–1.5 m to your side or behind you. The picture must show you (head and body), both hands, the desk top and the computer screen.", placeGo: "Check this position", placeMissing: list => `${list} cannot be seen well. Move the phone and check again.`,
      parts: { person: "you", hands: "both hands", desk: "the desk top", screen: "the computer screen" }, watchTitle: "Proctoring", watch: "Do not turn off this screen or switch apps. Keep the charger connected. It stops by itself when the exam ends.", hidden: "You left the phone proctoring screen. This is reported to the proctor." },
  };
  let st = null;
  const api = () => (window.HL_HPHO_API || cmBase()).replace(/\/+$/, "") + "/api/hpho/phone/" + encodeURIComponent(st.code) + "/";
  const wait = ms => new Promise(r => setTimeout(r, ms));
  async function call(action, fields) {
    const init = fields ? { method: "POST", body: Object.entries(fields).reduce((fd, [k, v]) => (v instanceof Blob ? fd.set(k, v, k + ".jpg") : fd.set(k, v), fd), new FormData()) } : {};
    const r = await fetch(api() + action, init), j = await r.json().catch(() => ({}));
    if (!r.ok) throw { code: j.error || "network" };
    return j;
  }
  /* a JPEG of the camera now (longest side 960 px, quality 0.85: readable, small) */
  function grab(v, side = 960) {
    const k = Math.min(1, side / Math.max(v.videoWidth, v.videoHeight)), c = document.createElement("canvas");
    c.width = Math.round(v.videoWidth * k); c.height = Math.round(v.videoHeight * k); c.getContext("2d").drawImage(v, 0, 0, c.width, c.height);
    return new Promise(res => c.toBlob(res, "image/jpeg", 0.85));
  }
  /* sharpness (variance of the Laplacian) and the grey picture, on a 160 px copy: a frame blurred by turning too fast scores low */
  function measure(v) {
    const w = 160, h = Math.max(1, Math.round(160 * v.videoHeight / v.videoWidth)), c = document.createElement("canvas"); c.width = w; c.height = h;
    const g = c.getContext("2d", { willReadFrequently: true }); g.drawImage(v, 0, 0, w, h);
    const d = g.getImageData(0, 0, w, h).data, grey = new Float32Array(w * h);
    for (let i = 0; i < w * h; i++) grey[i] = 0.299 * d[i * 4] + 0.587 * d[i * 4 + 1] + 0.114 * d[i * 4 + 2];
    let s = 0, s2 = 0, n = 0;
    for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) { const i = y * w + x, l = 4 * grey[i] - grey[i - 1] - grey[i + 1] - grey[i - w] - grey[i + w]; s += l; s2 += l * l; n++; }
    return { sharp: s2 / n - (s / n) ** 2, grey };
  }
  const moved = (a, b) => { if (!a || !b) return 0; let s = 0; for (let i = 0; i < a.length; i += 3) s += Math.abs(a[i] - b[i]); return s / (a.length / 3); };

  function view() { return `<div class="shell hpho hpho-phone"><div id="hphoPhone"><p class="hpho-muted">…</p></div></div>`; }
  function paint(html) { const box = document.getElementById("hphoPhone"); if (box) box.innerHTML = `<h1 class="hpho-phone-title">${T[L()].title}</h1>${st?.state ? `<p class="hpho-muted">${esc(st.state.candidate_no)}</p>` : ""}${html}`; return box; }
  function videoHtml() { return `<div class="hpho-phone-cam" id="hphoPhoneCam"></div>`; }
  function dockVideo() { const slot = document.getElementById("hphoPhoneCam"); if (slot && st.video) slot.append(st.video); }

  async function next() {
    const x = T[L()];
    try { st.state = await call("state"); } catch (e) { return paint(`<p>${e.code === "phone_not_found" ? x.bad : e.code === "exam_over" ? x.over : x.net}</p>`), e.code === "network" && setTimeout(next, 5000); }
    if (!st.video) {
      const box = paint(`<p>${x.intro}</p><p><button type="button" class="hpho-btn" id="hphoCamGo">${x.cam}</button></p>${st.error ? `<p class="hpho-form-msg">${esc(st.error)}</p>` : ""}`);
      box.querySelector("#hphoCamGo").addEventListener("click", async () => {
        try {
          const s = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false });
          st.video = Object.assign(document.createElement("video"), { muted: true, playsInline: true, autoplay: true, srcObject: s }); st.video.className = "hpho-phone-video";
          await st.video.play().catch(() => {}); for (let i = 0; i < 30 && !st.video.videoWidth; i++) await wait(100);
          try { st.lock = await navigator.wakeLock?.request("screen"); } catch (e) {}
          st.error = null; next();
        } catch (e) { st.error = x.camFail; next(); }
      });
      return;
    }
    const todo = st.state.views.find(v => !["clear", "notes", "unverified"].includes(st.state.scan[v]?.status));
    if (todo) return scanStep(todo);
    if (!st.state.placed && !st.placeAccepted) return placeStep();
    watchStep();
  }
  function scanStep(v) {
    const x = T[L()], views = st.state.views, i = views.indexOf(v) + 1, last = st.state.scan[v];
    const msg = st.msg || (last?.status === "blocked" ? x.blocked(last.found.filter(k => k !== "notes").map(k => x.found[k]).join(", ")) : last?.status === "redo" ? x.redo : last?.status === "unavailable" ? x.unavailable : "");
    const box = paint(`<h2>${x.scanTitle(i, views.length)} · ${esc(x.views[v])}</h2><ol class="hpho-phone-steps">${views.map(k => `<li class="${["clear", "notes", "unverified"].includes(st.state.scan[k]?.status) ? "is-ok" : k === v ? "is-now" : ""}">${esc(x.views[k])}</li>`).join("")}</ol>
      <p>${esc(x.sweep(x.how[v]))}</p>${videoHtml()}<div class="hpho-meter"><i id="hphoSweep"></i></div><p class="hpho-phone-hint" id="hphoHint"></p>
      ${msg ? `<p class="hpho-form-msg">${esc(msg)}</p>` : ""}<p><button type="button" class="hpho-btn" id="hphoScanGo">${x.go}</button></p>`);
    dockVideo(); st.msg = null;
    box.querySelector("#hphoScanGo").addEventListener("click", async e => {
      e.currentTarget.disabled = true;
      const hint = document.getElementById("hphoHint"), bar = document.getElementById("hphoSweep"), frames = [];
      let prev = null, fast = 0;
      /* eight seconds: every 250 ms the motion is measured (too fast: say so); every second a frame is kept with its sharpness */
      for (let tick = 0; tick < SWEEP * 4; tick++) {
        await wait(250);
        const m = measure(st.video), move = moved(prev, m.grey); prev = m.grey;
        if (move > 28) { fast++; hint.textContent = x.fast; hint.classList.add("is-bad"); } else { hint.textContent = x.slow; hint.classList.remove("is-bad"); }
        if (bar) bar.style.width = Math.round((tick + 1) / (SWEEP * 4) * 100) + "%";
        if (tick % 4 === 3) frames.push({ blob: await grab(st.video), sharp: m.sharp });
      }
      /* too fast or too blurred: sweep again before anything is sent */
      const sharp = frames.filter(f => f.sharp > 60);
      if (fast > SWEEP * 4 / 3 || sharp.length < 4) { st.msg = x.redo; return scanStep(v); }
      hint.textContent = x.judging;
      try {
        const fields = { view: v }; sharp.slice(0, KEEP).forEach((f, i) => { fields["f" + i] = f.blob; });
        const r = await call("scan", fields);
        st.state.scan[v] = { status: r.status, found: r.found };
      } catch (err) { st.msg = x.net; }
      next();
    });
  }
  function placeStep() {
    const x = T[L()];
    const box = paint(`<h2>${x.placeTitle}</h2><p>${x.place}</p>${videoHtml()}${st.msg ? `<p class="hpho-form-msg">${esc(st.msg)}</p>` : ""}<p><button type="button" class="hpho-btn" id="hphoPlaceGo">${x.placeGo}</button></p>`);
    dockVideo(); st.msg = null;
    box.querySelector("#hphoPlaceGo").addEventListener("click", async e => {
      e.currentTarget.disabled = true;
      try {
        const r = await call("place", { image: await grab(st.video, 1280) });
        st.placeTries = (st.placeTries || 0) + 1;
        if (r.unavailable) { if (st.placeTries >= 3) st.placeAccepted = true; else st.msg = x.unavailable; }
        else if (!r.placed) st.msg = x.placeMissing(r.missing.map(k => x.parts[k]).join(", "));
      } catch (err) { st.msg = x.net; }
      next();
    });
  }
  function watchStep() {
    const x = T[L()];
    paint(`<h2 class="hpho-phone-live">● ${x.watchTitle}</h2><p>${x.watch}</p>${videoHtml()}<p class="hpho-form-msg" id="hphoPhoneMsg"></p>`);
    dockVideo();
    if (st.watching) return; st.watching = true;
    const snap = async reason => { try { await call("snap", { image: await grab(st.video), reason }); document.getElementById("hphoPhoneMsg").textContent = ""; }
      catch (e) { if (e.code === "exam_over") return stop(); const m = document.getElementById("hphoPhoneMsg"); if (m) m.textContent = x.net; } };
    snap("random");
    st.timers = [setInterval(() => snap("random"), 15000), setInterval(() => call("beat", {}).catch(e => e.code === "exam_over" && stop()), 10000)];
    document.addEventListener("visibilitychange", st.onVis = () => { if (document.hidden) return; snap("phone_back"); const m = document.getElementById("hphoPhoneMsg"); if (m) m.textContent = x.hidden; try { navigator.wakeLock?.request("screen").then(l => st.lock = l); } catch (e) {} });
  }
  function stop() {
    for (const t of st?.timers || []) clearInterval(t);
    st?.video?.srcObject?.getTracks().forEach(t => t.stop()); st?.lock?.release?.().catch?.(() => {});
    if (st?.onVis) document.removeEventListener("visibilitychange", st.onVis);
    paint(`<p>${T[L()].over}</p>`); st = { ...st, video: null, watching: false, timers: [] };
  }
  function mount(code) {
    if (st?.code !== code) { if (st) stop(); st = { code }; }
    next();
  }
  window.HL_HPHO_PHONE = { view, mount };
})();
