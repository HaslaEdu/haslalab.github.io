/* HPhO phone (#/hpho/phone/<code>): the candidate's phone as the second camera, Monito-style. The exam page shows a QR
   with a one-time code; the phone opens this page from it (no sign-in on the phone; the first phone to open the code
   keeps it, community/src/hpho-exam.js phoneRoute) and
   1. scans the room view by view (the walls, behind, the ceiling, the desk top, under the desk). An animation shows how
      to move the phone; the gauge fills as the phone actually turns (the gyroscope, DeviceMotion rotationRate), turning
      too fast does not count, and a frame is taken at each sixth of the turn. Blurred or dark frames are dropped here,
      and the rest (at most six, 768 px: one image tile each for the model) are judged by a model on the server;
   2. is stood 1–1.5 m to the side of or behind the candidate, where it sees the candidate, the hands, the desk and the
      screen, and a model confirms that from a photo;
   3. then watches: a photo every 15 s and a heartbeat, until the answers are in.
   A confirmed step plays "ding-dong", a problem "beep-beep"; the network's state and delay are always shown. */
(() => {
  const L = () => (typeof lang === "string" && lang === "en") ? "en" : "ko";
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const KEEP = 6, SIDE = 768, FAST = 50;                   /* frames sent per view; their longest side; degrees per second */
  /* how far each view turns the phone (degrees) and which way: across (a wall, the desk) or up/down (ceiling, under) */
  const TURN = { front: 90, left: 90, right: 90, back: 90, ceiling: 70, desk: 70, under: 70 };
  const T = {
    ko: { title: "HPhO 휴대폰 감독", intro: "이 휴대폰은 시험 동안 두 번째 카메라로 쓰입니다. 먼저 방을 천천히 비춰 검사하고, 그다음 옆이나 뒤에 세워 두면 됩니다. 시험이 끝날 때까지 이 화면을 켜 두세요(충전기 연결).", cam: "카메라 켜기", camFail: "카메라를 켜지 못했습니다. 브라우저의 카메라 권한을 허용한 뒤 다시 시도하세요.",
      bad: "이 QR은 만료되었거나 잘못되었습니다. 시험 창에 보이는 새 QR을 다시 찍으세요.", inUse: "이 QR은 이미 다른 휴대폰에 연결되어 있습니다. 처음 연결한 휴대폰을 쓰거나, 시험 창에서 새 QR을 받으세요.", over: "시험이 끝났습니다. 이 화면을 닫아도 됩니다.", net: "서버에 연결하지 못했습니다. 다시 시도하는 중…",
      scanTitle: (i, n) => `주변 스캔 ${i} / ${n}`, views: { front: "앞쪽 벽", left: "왼쪽", right: "오른쪽", back: "뒤쪽 (의자 뒤)", ceiling: "천장", desk: "책상 위 전체", under: "책상 아래와 발밑" },
      how: { front: "앞쪽 벽을 보고 서서, 휴대폰을 왼쪽 끝에서 오른쪽 끝까지 천천히 돌리세요.", left: "왼쪽을 보고, 휴대폰을 벽의 한쪽 끝에서 다른 쪽 끝까지 천천히 돌리세요.", right: "오른쪽을 보고, 휴대폰을 벽의 한쪽 끝에서 다른 쪽 끝까지 천천히 돌리세요.", back: "의자 뒤쪽을 보고, 휴대폰을 왼쪽 끝에서 오른쪽 끝까지 천천히 돌리세요.", ceiling: "휴대폰을 눈높이에서 천천히 위로 들어 천장 끝까지 비추세요.", desk: "휴대폰을 책상 위로 들고, 책상 한쪽 끝에서 다른 쪽 끝까지(모니터 뒤까지) 천천히 비추세요.", under: "휴대폰을 책상 높이에서 천천히 아래로 내려 책상 밑과 발밑, 의자 주변을 비추세요." },
      example: "이렇게 움직이세요", go: "스캔 시작", turning: "천천히 계속 돌리세요", fast: "너무 빨라요! 천천히", hold: "움직여 주세요", judging: "AI가 확인하는 중…", gyroOff: "이 휴대폰은 움직임 센서를 쓸 수 없어 시간으로 잽니다. 8초 동안 천천히 돌리세요.",
      redo: "흐리거나 어두워서 잘 보이지 않았습니다. 더 천천히, 밝게 다시 비춰 주세요.", blocked: list => `${list}이(가) 보입니다. 치우거나 방 밖으로 옮긴 뒤 이 방향을 다시 비춰 주세요.`, unavailable: "AI 확인 서버가 응답하지 않았습니다. 다시 비춰 주세요.",
      found: { person: "다른 사람", phone: "휴대폰·스마트워치·태블릿", screen: "다른 화면", headset: "이어폰·헤드셋", notes: "책·필기" },
      placeTitle: "휴대폰 세워 두기", place: "휴대폰을 옆이나 뒤쪽 1~1.5m 거리에 가로로 세워 두세요. 화면에 본인(머리와 몸), 두 손, 책상 위, 컴퓨터 화면이 모두 보여야 합니다.", placeGo: "이 위치로 확인", placeMissing: list => `화면에 ${list}이(가) 잘 보이지 않습니다. 위치를 옮기고 다시 확인하세요.`,
      parts: { person: "본인", hands: "두 손", desk: "책상 위", screen: "컴퓨터 화면" }, watchTitle: "감독 중", watch: "이 화면을 끄거나 다른 앱으로 나가지 마세요. 충전기를 연결해 두세요. 시험이 끝나면 자동으로 멈춥니다.", hidden: "휴대폰 감독 화면을 벗어났습니다. 이 기록은 감독관에게 전달됩니다.",
      net: { label: "네트워크", good: "좋음", fair: "보통", poor: "느림", off: "끊김" } },
    en: { title: "HPhO phone proctoring", intro: "This phone is a second camera during the exam. First show the room slowly for the check, then stand the phone to your side or behind you. Keep this screen on until the exam ends (connect a charger).", cam: "Turn on the camera", camFail: "The camera could not start. Allow camera access in the browser, then try again.",
      bad: "This QR code has expired or is wrong. Scan the new QR shown in the exam window.", inUse: "This QR is already connected to another phone. Use the first phone, or get a new QR in the exam window.", over: "The exam is over. You can close this page.", net: "Could not reach the server. Retrying…",
      scanTitle: (i, n) => `Room scan ${i} / ${n}`, views: { front: "The wall in front", left: "The left side", right: "The right side", back: "Behind you", ceiling: "The ceiling", desk: "The whole desk", under: "Under the desk" },
      how: { front: "Face the front wall and turn the phone slowly from its left end to its right end.", left: "Face left and turn the phone slowly from one end of the wall to the other.", right: "Face right and turn the phone slowly from one end of the wall to the other.", back: "Face behind the chair and turn the phone slowly from left to right.", ceiling: "Raise the phone slowly from eye level until it shows the far end of the ceiling.", desk: "Hold the phone over the desk and move it slowly from one end to the other, behind the monitor too.", under: "Lower the phone slowly from desk height to show under the desk, your feet and around the chair." },
      example: "Move it like this", go: "Start the scan", turning: "Keep turning slowly", fast: "Too fast! Slower", hold: "Start moving", judging: "The AI is checking…", gyroOff: "This phone's motion sensor is not available, so the time is used instead: turn slowly for eight seconds.",
      redo: "It was blurred or dark. Sweep again, more slowly and with more light.", blocked: list => `${list} can be seen. Remove it or take it out of the room, then show this side again.`, unavailable: "The AI check did not answer. Sweep again.",
      found: { person: "another person", phone: "a phone, smartwatch or tablet", screen: "another screen", headset: "earphones or a headset", notes: "books or notes" },
      placeTitle: "Stand the phone", place: "Stand the phone sideways 1–1.5 m to your side or behind you. The picture must show you (head and body), both hands, the desk top and the computer screen.", placeGo: "Check this position", placeMissing: list => `${list} cannot be seen well. Move the phone and check again.`,
      parts: { person: "you", hands: "both hands", desk: "the desk top", screen: "the computer screen" }, watchTitle: "Proctoring", watch: "Do not turn off this screen or switch apps. Keep the charger connected. It stops by itself when the exam ends.", hidden: "You left the phone proctoring screen. This is reported to the proctor.",
      net: { label: "Network", good: "Good", fair: "Fair", poor: "Slow", off: "Offline" } },
  };
  let st = null;
  /* this phone: one id for the code, kept for the page's life (another phone opening the same code is refused) */
  const device = (() => { try { let d = sessionStorage.getItem("hphoPhoneDevice"); if (!d) { d = Array.from(crypto.getRandomValues(new Uint8Array(16)), b => b.toString(16).padStart(2, "0")).join(""); sessionStorage.setItem("hphoPhoneDevice", d); } return d; } catch (e) { return "p" + Math.random().toString(36).slice(2) + Date.now().toString(36); } })();
  const api = action => (window.HL_HPHO_API || cmBase()).replace(/\/+$/, "") + "/api/hpho/phone/" + encodeURIComponent(st.code) + "/" + action + "?d=" + device;
  const wait = ms => new Promise(r => setTimeout(r, ms));

  /* sounds: ding-dong (confirmed) and beep-beep (a problem), made here */
  let audio = null;
  function tones(list) {
    try { audio ||= new AudioContext(); audio.resume?.(); const t0 = audio.currentTime;
      for (const [f, at, len, vol] of list) { const o = audio.createOscillator(), g = audio.createGain(); o.type = "sine"; o.frequency.value = f;
        g.gain.setValueAtTime(0.0001, t0 + at); g.gain.exponentialRampToValueAtTime(vol, t0 + at + 0.015); g.gain.exponentialRampToValueAtTime(0.0001, t0 + at + len);
        o.connect(g).connect(audio.destination); o.start(t0 + at); o.stop(t0 + at + len + 0.05); } } catch (e) {}
  }
  const ding = () => tones([[1046.5, 0, 0.45, 0.25], [784, 0.18, 0.5, 0.25]]);
  const beep = () => tones([[1568, 0, 0.09, 0.2], [1568, 0.14, 0.09, 0.2]]);

  /* the network: every call's time; the badge shows its state */
  function netBadge() {
    const x = T[L()].net, ms = st?.rtt, level = !navigator.onLine || st?.offline ? "off" : ms == null ? "good" : ms < 300 ? "good" : ms < 900 ? "fair" : "poor";
    return `<span class="hpho-net is-${level}" id="hphoNet"><i></i><i></i><i></i> ${x.label}: ${x[level]}${ms != null && level !== "off" ? ` · ${ms} ms` : ""}</span>`;
  }
  const refreshNet = () => { const el = document.getElementById("hphoNet"); if (el) el.outerHTML = netBadge(); };
  async function call(action, fields) {
    const init = fields ? { method: "POST", body: Object.entries(fields).reduce((fd, [k, v]) => (v instanceof Blob ? fd.set(k, v, k + ".jpg") : fd.set(k, v), fd), new FormData()) } : {};
    const t0 = performance.now();
    let r; try { r = await fetch(api(action), init); } catch (e) { st.offline = true; refreshNet(); throw { code: "network" }; }
    st.offline = false; st.rtt = Math.round(performance.now() - t0); refreshNet();
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw { code: j.error || "network" };
    return j;
  }
  /* a JPEG of the camera now: longest side 768 px (one tile for the model), quality 0.85 */
  function grab(v, side = SIDE) {
    const k = Math.min(1, side / Math.max(v.videoWidth, v.videoHeight)), c = document.createElement("canvas");
    c.width = Math.round(v.videoWidth * k); c.height = Math.round(v.videoHeight * k); c.getContext("2d").drawImage(v, 0, 0, c.width, c.height);
    return new Promise(res => c.toBlob(res, "image/jpeg", 0.85));
  }
  /* sharpness (variance of the Laplacian) and brightness, on a 160 px copy */
  function measure(v) {
    const w = 160, h = Math.max(1, Math.round(160 * v.videoHeight / v.videoWidth)), c = document.createElement("canvas"); c.width = w; c.height = h;
    const g = c.getContext("2d", { willReadFrequently: true }); g.drawImage(v, 0, 0, w, h);
    const d = g.getImageData(0, 0, w, h).data, grey = new Float32Array(w * h); let light = 0;
    for (let i = 0; i < w * h; i++) { grey[i] = 0.299 * d[i * 4] + 0.587 * d[i * 4 + 1] + 0.114 * d[i * 4 + 2]; light += grey[i]; }
    let s = 0, s2 = 0, n = 0;
    for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) { const i = y * w + x, l = 4 * grey[i] - grey[i - 1] - grey[i + 1] - grey[i - w] - grey[i + w]; s += l; s2 += l * l; n++; }
    return { sharp: s2 / n - (s / n) ** 2, light: light / (w * h) };
  }

  /* how to move the phone, drawn (Monito-style): a turn across for the walls and the desk, a tilt for the ceiling and under */
  function example(view) {
    const across = ["front", "left", "right", "back", "desk"].includes(view), up = view === "ceiling";
    const scene = across
      ? `<rect x="20" y="${view === "desk" ? 70 : 14}" width="160" height="${view === "desk" ? 40 : 10}" rx="3" class="ex-wall"/><circle cx="100" cy="128" r="12" class="ex-me"/>
         <g class="ex-phone ex-sweep"><rect x="94" y="90" width="12" height="20" rx="2"/><path d="M100 90 L60 30 M100 90 L140 30" class="ex-ray"/></g>
         <path d="M58 52 Q100 30 142 52" class="ex-arrow" marker-end="url(#exArrow)"/>`
      : `<rect x="20" y="${up ? 10 : 132}" width="160" height="8" class="ex-wall"/><rect x="40" y="${up ? 120 : 70}" width="120" height="6" rx="2" class="ex-desk"/>
         <g class="ex-phone ${up ? "ex-tilt-up" : "ex-tilt-down"}" style="transform-origin:100px 96px"><rect x="94" y="86" width="12" height="20" rx="2"/><path d="M100 86 L${up ? "70 20 M100 86 L130 20" : "70 130 M100 106 L130 130"}" class="ex-ray"/></g>
         <path d="${up ? "M150 100 Q165 60 150 30" : "M150 60 Q165 95 150 125"}" class="ex-arrow" marker-end="url(#exArrow)"/>`;
    return `<figure class="hpho-example"><svg viewBox="0 0 200 150" role="img" aria-label="${esc(T[L()].example)}"><defs><marker id="exArrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0 L10 5 L0 10 z" class="ex-head"/></marker></defs>${scene}</svg><figcaption>${esc(T[L()].example)}</figcaption></figure>`;
  }

  function view() { return `<div class="shell hpho hpho-phone"><div id="hphoPhone"><p class="hpho-muted">…</p></div></div>`; }
  function paint(html) {
    const box = document.getElementById("hphoPhone");
    if (box) box.innerHTML = `<div class="hpho-phone-top"><h1 class="hpho-phone-title">${T[L()].title}</h1>${netBadge()}</div>${st?.state ? `<p class="hpho-muted">${esc(st.state.candidate_no)}</p>` : ""}${html}`;
    return box;
  }
  const videoHtml = () => `<div class="hpho-phone-cam" id="hphoPhoneCam"></div>`;
  function dockVideo() { const slot = document.getElementById("hphoPhoneCam"); if (slot && st.video) slot.append(st.video); }
  function problem(msg) { st.msg = msg; beep(); }

  async function next() {
    const x = T[L()];
    try { st.state = await call("state"); }
    catch (e) { beep(); paint(`<p class="hpho-form-msg">${e.code === "phone_not_found" ? x.bad : e.code === "phone_in_use" ? x.inUse : e.code === "exam_over" ? x.over : x.net}</p>`); if (e.code === "network") setTimeout(next, 5000); return; }
    if (!st.video) {
      const box = paint(`<p>${x.intro}</p><p><button type="button" class="hpho-btn" id="hphoCamGo">${x.cam}</button></p>${st.error ? `<p class="hpho-form-msg">${esc(st.error)}</p>` : ""}`);
      box.querySelector("#hphoCamGo").addEventListener("click", async () => {
        tones([[1, 0, 0.01, 0.0001]]);                                 /* the sounds may play from now on (a tap opened them) */
        try {
          const s = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false });
          st.video = Object.assign(document.createElement("video"), { muted: true, playsInline: true, autoplay: true, srcObject: s }); st.video.className = "hpho-phone-video";
          await st.video.play().catch(() => {}); for (let i = 0; i < 30 && !st.video.videoWidth; i++) await wait(100);
          try { st.lock = await navigator.wakeLock?.request("screen"); } catch (e) {}
          st.error = null; ding(); next();
        } catch (e) { st.error = x.camFail; beep(); next(); }
      });
      return;
    }
    const todo = st.state.views.find(v => !["clear", "notes", "unverified"].includes(st.state.scan[v]?.status));
    if (todo) return scanStep(todo);
    if (!st.state.placed && !st.placeAccepted) return placeStep();
    watchStep();
  }
  /* the motion sensor: iOS asks once (from a tap); elsewhere it just works. Returns whether rotation arrives */
  async function motionReady() {
    try { if (typeof DeviceMotionEvent?.requestPermission === "function" && (await DeviceMotionEvent.requestPermission()) !== "granted") return false; } catch (e) { return false; }
    return new Promise(res => { let got = false; const on = e => { if (e.rotationRate && (e.rotationRate.alpha != null || e.rotationRate.beta != null)) got = true; };
      addEventListener("devicemotion", on); setTimeout(() => { removeEventListener("devicemotion", on); res(got); }, 600); });
  }
  function scanStep(v) {
    const x = T[L()], views = st.state.views, i = views.indexOf(v) + 1, last = st.state.scan[v];
    const msg = st.msg || (last?.status === "blocked" ? x.blocked(last.found.filter(k => k !== "notes").map(k => x.found[k]).join(", ")) : last?.status === "redo" ? x.redo : last?.status === "unavailable" ? x.unavailable : "");
    if (!st.msg && ["blocked", "redo", "unavailable"].includes(last?.status) && st.beeped !== v + last.status + last.at) { st.beeped = v + last.status + last.at; beep(); }
    const box = paint(`<h2>${x.scanTitle(i, views.length)} · ${esc(x.views[v])}</h2><ol class="hpho-phone-steps">${views.map(k => `<li class="${["clear", "notes", "unverified"].includes(st.state.scan[k]?.status) ? "is-ok" : k === v ? "is-now" : ""}">${esc(x.views[k])}</li>`).join("")}</ol>
      <div class="hpho-phone-guide">${example(v)}<p>${esc(x.how[v])}</p></div>${videoHtml()}<div class="hpho-meter hpho-meter-big"><i id="hphoSweep"></i></div><p class="hpho-phone-hint" id="hphoHint"></p>
      ${msg ? `<p class="hpho-form-msg">${esc(msg)}</p>` : ""}<p><button type="button" class="hpho-btn" id="hphoScanGo">${x.go}</button></p>`);
    dockVideo(); st.msg = null;
    box.querySelector("#hphoScanGo").addEventListener("click", async e => {
      e.currentTarget.disabled = true;
      const hint = document.getElementById("hphoHint"), bar = document.getElementById("hphoSweep"), frames = [], target = TURN[v];
      const gyro = st.gyro ?? (st.gyro = await motionReady());
      if (!gyro) hint.textContent = x.gyroOff;
      /* the gauge: degrees actually turned (the gyroscope's rotation rate, all axes), counted only while slow enough;
         a frame at the start and at every sixth of the turn */
      let turned = 0, lastT = performance.now(), rate = 0, nextShot = 0;
      const onMotion = ev => { const r = ev.rotationRate || {}, now = performance.now(), dt = Math.min(0.2, (now - lastT) / 1000); lastT = now;
        rate = Math.hypot(r.alpha || 0, r.beta || 0, r.gamma || 0); if (rate > 3 && rate <= FAST) turned += rate * dt; };
      if (gyro) addEventListener("devicemotion", onMotion);
      const started = performance.now();
      while (true) {
        await wait(120);
        const progress = gyro ? turned / target : (performance.now() - started) / 8000;
        if (bar) bar.style.width = Math.min(100, Math.round(progress * 100)) + "%";
        if (gyro) { hint.textContent = rate > FAST ? x.fast : rate > 3 ? x.turning : x.hold; hint.classList.toggle("is-bad", rate > FAST); }
        if (progress >= nextShot / (KEEP - 1) && frames.length < KEEP + 2) { const m = measure(st.video); frames.push({ blob: await grab(st.video), ...m }); nextShot++; }
        if (progress >= 1) break;
        if (performance.now() - started > 60000) break;                /* a minute without the full turn: judge what there is */
      }
      if (gyro) removeEventListener("devicemotion", onMotion);
      /* blurred or dark frames are not sent (no money spent on them); too few good ones: sweep again */
      const good = frames.filter(f => f.sharp > 60 && f.light > 35);
      if (good.length < 4) { problem(x.redo); return scanStep(v); }
      hint.classList.remove("is-bad"); hint.textContent = x.judging;
      try {
        const fields = { view: v }; good.slice(0, KEEP).forEach((f, k) => { fields["f" + k] = f.blob; });
        const r = await call("scan", fields);
        st.state.scan[v] = { status: r.status, found: r.found, at: Date.now() };
        if (["clear", "notes", "unverified"].includes(r.status)) ding();
      } catch (err) { problem(x.net); }
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
        const r = await call("place", { image: await grab(st.video, 1024) });
        st.placeTries = (st.placeTries || 0) + 1;
        if (r.unavailable) { if (st.placeTries >= 3) { st.placeAccepted = true; ding(); } else problem(x.unavailable); }
        else if (!r.placed) problem(x.placeMissing(r.missing.map(k => x.parts[k]).join(", ")));
        else ding();
      } catch (err) { problem(x.net); }
      next();
    });
  }
  function watchStep() {
    const x = T[L()];
    paint(`<h2 class="hpho-phone-live">● ${x.watchTitle}</h2><p>${x.watch}</p>${videoHtml()}<p class="hpho-form-msg" id="hphoPhoneMsg"></p>`);
    dockVideo();
    if (st.watching) return; st.watching = true;
    const say = t => { const m = document.getElementById("hphoPhoneMsg"); if (m) m.textContent = t; };
    const snap = async reason => { try { await call("snap", { image: await grab(st.video, 960), reason }); say(""); }
      catch (e) { if (e.code === "exam_over") return stop(); say(x.net); beep(); } };
    snap("random");
    st.timers = [setInterval(() => snap("random"), 15000), setInterval(() => call("beat", {}).catch(e => e.code === "exam_over" ? stop() : beep()), 10000)];
    document.addEventListener("visibilitychange", st.onVis = () => { if (document.hidden) return; snap("phone_back"); say(x.hidden); beep(); try { navigator.wakeLock?.request("screen").then(l => st.lock = l); } catch (e) {} });
  }
  function stop() {
    for (const t of st?.timers || []) clearInterval(t);
    st?.video?.srcObject?.getTracks().forEach(t => t.stop()); st?.lock?.release?.().catch?.(() => {});
    if (st?.onVis) document.removeEventListener("visibilitychange", st.onVis);
    paint(`<p>${T[L()].over}</p>`); st = { ...st, video: null, watching: false, timers: [] };
  }
  function mount(code) {
    if (st?.code !== code) { if (st) stop(); st = { code }; }
    addEventListener("online", refreshNet); addEventListener("offline", refreshNet);
    next();
  }
  window.HL_HPHO_PHONE = { view, mount };
})();
