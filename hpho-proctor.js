/* HPhO proctoring in the exam page (hpho-exam.js): the webcam and microphone, and the screen, watched on the candidate's
   own computer. Faces, a phone in view and sustained speech are detected locally (MediaPipe Tasks for vision, a level
   meter for sound), so the video never leaves the computer as a stream: what reaches the server are events and small
   JPEG snapshots, taken at random intervals (10-60 s, so a candidate cannot time them) and at once when something is
   detected. The AI that reviews the snapshots runs on the server after the exam; a person decides.
   From the seat in the waiting room until the answers are in, two recordings run as five-minute WebM segments, each
   uploaded as it closes: the webcam with the microphone, and the screen with the computer's own sound (Windows loopback,
   from the desktop app). Sound played on the computer is also detected (system_sound). Before the first seat, and again
   after a disconnect, the candidate shows the room with the webcam (roomScan): walls, ceiling, desk and under the desk. */
(() => {
  const VISION = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.21";
  const HAND_MODEL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task";
  let hands = null;
  /* the hand tracker (MediaPipe Hand Landmarker, 21 points a hand): only for the ear/head/wrist check */
  function handTracker() {
    return hands ||= (async () => {
      const { FilesetResolver, HandLandmarker } = await import(VISION + "/vision_bundle.mjs");
      const files = await FilesetResolver.forVisionTasks(VISION + "/wasm");
      return HandLandmarker.createFromOptions(files, { baseOptions: { modelAssetPath: HAND_MODEL, delegate: "GPU" }, runningMode: "VIDEO", numHands: 2 });
    })().catch(() => { hands = null; return null; });
  }
  const MODELS = {
    face: "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite",
    objects: "https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite0/int8/1/efficientdet_lite0.tflite",
  };
  const NEAR = { face_missing: 6, faces_multiple: 3, phone_seen: 2, voice: 3, system_sound: 3 };   /* seconds a condition must last */
  const COOLDOWN = 60;                                                         /* seconds before the same event again */
  let p = null;

  async function detectors() {
    try {
      const { FilesetResolver, FaceDetector, ObjectDetector } = await import(VISION + "/vision_bundle.mjs");
      const files = await FilesetResolver.forVisionTasks(VISION + "/wasm");
      const face = await FaceDetector.createFromOptions(files, { baseOptions: { modelAssetPath: MODELS.face, delegate: "GPU" }, runningMode: "VIDEO", minDetectionConfidence: 0.5 });
      const objects = await ObjectDetector.createFromOptions(files, { baseOptions: { modelAssetPath: MODELS.objects, delegate: "GPU" }, runningMode: "VIDEO", scoreThreshold: 0.45,
        categoryAllowlist: ["cell phone", "book", "laptop"] });
      return { face, objects };
    } catch (e) { return null; }
  }

  const live = s => !!s && s.getTracks().length > 0 && s.getTracks().every(t => t.readyState === "live");
  /* the technical check: camera and microphone (and the screen, inside the desktop app) can be opened; a stream already
     open from an earlier try is kept */
  /* screen: false leaves the screen for shareScreen(), which the page calls once the candidate pressed "allow" */
  async function check({ screen = true } = {}) {
    const out = { camera: false, mic: false, screen: false, system: false, detector: false };
    if (live(p?.cam)) { out.camera = p.cam.getVideoTracks().length > 0; out.mic = p.cam.getAudioTracks().length > 0; }
    else try {
      const cam = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, frameRate: { ideal: 15, max: 15 }, facingMode: "user" }, audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: true } });
      out.camera = cam.getVideoTracks().length > 0; out.mic = cam.getAudioTracks().length > 0;
      p = { ...(p || {}), cam };
    } catch (e) { out.error = e?.name || "camera"; }
    if (!screen) { /* asked later */ }
    else if (live(p?.scr)) { out.screen = true; out.system = p.scr.getAudioTracks().length > 0; }
    else try {
      /* the screen and the computer's own sound together (the desktop app answers with the primary display and loopback) */
      const scr = await navigator.mediaDevices.getDisplayMedia({ video: { frameRate: 2 }, audio: true }); p = { ...(p || {}), scr };
      /* the screen is text: keep its sharpness, let the frame rate give (the encoder keeps detail over motion) */
      scr.getVideoTracks().forEach(t => { try { t.contentHint = "text"; } catch (e) {} });
      out.system = scr.getAudioTracks().length > 0;
      /* a recording counts once a frame of it has arrived */
      const v = Object.assign(document.createElement("video"), { muted: true, playsInline: true, srcObject: scr }); v.play?.().catch(() => {});
      for (let i = 0; i < 30 && !v.videoWidth; i++) await wait(100);
      out.screen = !!v.videoWidth; if (!out.screen) out.screenError = "no_frames";
    } catch (e) { out.screenError = e?.name || "screen"; }
    if (out.camera) { p.det = p.det || await detectors(); out.detector = !!p.det; }
    preview();
    return out;
  }
  const wait = ms => new Promise(r => setTimeout(r, ms));
  /* the screen with the computer's sound, after the candidate allowed it */
  async function shareScreen() {
    const out = await check({ screen: true });
    return { screen: out.screen, system: out.system, error: out.screenError };
  }
  async function selfVideo() {
    const v = document.getElementById("hphoSelf");
    for (let i = 0; i < 30 && v && !v.videoWidth; i++) await wait(100);
    return v?.videoWidth ? v : null;
  }
  /* mean brightness (0-255) of a box of the video */
  function luma(v, x, y, w, h) {
    const c = document.createElement("canvas"); c.width = c.height = 24; const g = c.getContext("2d", { willReadFrequently: true });
    g.drawImage(v, Math.max(0, x), Math.max(0, y), Math.max(1, w), Math.max(1, h), 0, 0, 24, 24);
    const d = g.getImageData(0, 0, 24, 24).data; let s = 0; for (let i = 0; i < d.length; i += 4) s += 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
    return s / (d.length / 4);
  }
  /* is the face well seen? three seconds of frames: one face, big enough, near the middle, lit. reason: the commonest fault */
  async function faceCheck() {
    const v = await selfVideo(); if (!v) return { ok: false, reason: "no_video" };
    if (!p.det) p.det = await detectors();
    if (!p.det) return { ok: false, reason: "detector" };
    const n = { good: 0, none: 0, many: 0, small: 0, off: 0, dark: 0 };
    for (let i = 0; i < 12; i++) {
      await wait(250);
      let d; try { d = p.det.face.detectForVideo(v, performance.now()).detections; } catch (e) { continue; }
      if (!d.length) { n.none++; continue; }
      if (d.length > 1) { n.many++; continue; }
      const b = d[0].boundingBox, W = v.videoWidth, H = v.videoHeight, cx = (b.originX + b.width / 2) / W, cy = (b.originY + b.height / 2) / H;
      if (b.width / W < 0.16) n.small++;
      else if (Math.abs(cx - 0.5) > 0.25 || Math.abs(cy - 0.5) > 0.3) n.off++;
      else if (luma(v, b.originX, b.originY, b.width, b.height) < 55) n.dark++;
      else n.good++;
    }
    if (n.good >= 8) return { ok: true };
    const reason = ["many", "none", "dark", "small", "off"].reduce((a, k) => n[k] > n[a] ? k : a, "none");
    return { ok: false, reason };
  }
  /* is the sentence read aloud? The level is measured against the room's own noise first, then a voice must be heard in
     the speech band (100-3500 Hz), in more than one burst and for long enough to be a sentence: a shout, a cough or a tap
     on the desk does not pass. The recording (16 kHz WAV) goes to the server, where a model checks the words themselves.
     level(0..1) feeds the meter; level(0, "speak") tells the page to show "read now" */
  async function micCheck(level) {
    if (!p?.cam?.getAudioTracks().length) return { ok: false, reason: "no_mic" };
    let ctx; try { ctx = new AudioContext(); await ctx.resume(); } catch (e) { return { ok: false, reason: "no_audio" }; }
    const src = ctx.createMediaStreamSource(new MediaStream(p.cam.getAudioTracks())), an = ctx.createAnalyser(); an.fftSize = 2048; src.connect(an);
    const chunks = []; let recording = false, rec = null, sink = null;
    try { rec = ctx.createScriptProcessor(4096, 1, 1); rec.onaudioprocess = e => { if (recording) chunks.push(new Float32Array(e.inputBuffer.getChannelData(0))); };
      sink = ctx.createGain(); sink.gain.value = 0; src.connect(rec); rec.connect(sink); sink.connect(ctx.destination); } catch (e) { rec = null; }
    const buf = new Float32Array(an.fftSize), freq = new Float32Array(an.frequencyBinCount), hz = ctx.sampleRate / an.fftSize;
    const rms = () => { an.getFloatTimeDomainData(buf); let s = 0; for (const x of buf) s += x * x; return Math.sqrt(s / buf.length); };
    const speechShare = () => { an.getFloatFrequencyData(freq); let a = 0, b = 0;
      for (let i = 1; i < freq.length; i++) { const f = i * hz; if (f < 50 || f > 8000) continue; const e = Math.pow(10, freq[i] / 10); b += e; if (f >= 100 && f <= 3500) a += e; }
      return b ? a / b : 0; };
    try {
      /* the room's own noise: the median of eight readings (a click, or a candidate who starts reading at once, must not
         become the floor), and never above a quiet room's level */
      const quietRoom = []; for (let i = 0; i < 8; i++) { await wait(100); quietRoom.push(rms()); }
      const floor = Math.min(0.008, quietRoom.sort((a, b) => a - b)[4]);
      level?.(0, "speak"); recording = true;
      const thr = Math.max(0.006, floor * 2.5);
      let voiced = 0, bursts = 0, on = false, quiet = 0, top = 0, first = -1, last = -1;
      for (let i = 0; i < 100; i++) {
        await wait(100);
        const r = rms(); top = Math.max(top, r); level?.(Math.min(1, r * 8));
        if (r > thr && speechShare() > 0.45) { voiced++; if (!on) { bursts++; on = true; } quiet = 0; if (first < 0) first = i; last = i; }
        else { if (++quiet >= 2) on = false; }
        if (voiced >= 18 && bursts >= 2 && quiet >= 12) break;            /* the sentence, then a second of silence */
      }
      recording = false;
      const span = first < 0 ? 0 : last - first + 1;
      /* a loud but short sound (a shout, a word, a knock) is "short", not "quiet" */
      /* the Korean sentence takes about three seconds: under two seconds of speech is not it ("예, 아", a shout, a knock) */
      const reason = top < 0.004 ? "silent" : voiced < 3 ? "quiet" : voiced < 15 || bursts < 2 || span < 20 ? "short" : null;
      /* top: the loudest moment; the page lets the server's model hear a recording the level was unsure about */
      return { ok: !reason, ...(reason ? { reason } : {}), top, wav: rec ? wav16k(chunks, ctx.sampleRate) : null };
    } finally { recording = false; level?.(0); try { rec?.disconnect(); sink?.disconnect(); src.disconnect(); } catch (e) {} ctx.close().catch(() => {}); }
  }
  /* mono float chunks at the context's rate, as a 16 kHz 16-bit WAV (at most ten seconds: about 320 KB) */
  function wav16k(chunks, rate) {
    const n = chunks.reduce((a, c) => a + c.length, 0), k = rate / 16000, len = Math.min(160000, Math.floor(n / k));
    const all = new Float32Array(n); let o = 0; for (const c of chunks) { all.set(c, o); o += c.length; }
    const out = new DataView(new ArrayBuffer(44 + len * 2)), str = (at, t) => { for (let i = 0; i < t.length; i++) out.setUint8(at + i, t.charCodeAt(i)); };
    str(0, "RIFF"); out.setUint32(4, 36 + len * 2, true); str(8, "WAVE"); str(12, "fmt "); out.setUint32(16, 16, true); out.setUint16(20, 1, true); out.setUint16(22, 1, true);
    out.setUint32(24, 16000, true); out.setUint32(28, 32000, true); out.setUint16(32, 2, true); out.setUint16(34, 16, true); str(36, "data"); out.setUint32(40, len * 2, true);
    for (let i = 0; i < len; i++) { let s = 0, a = Math.floor(i * k), b = Math.max(a + 1, Math.floor((i + 1) * k)); for (let j = a; j < b; j++) s += all[j]; const v = Math.max(-1, Math.min(1, s / (b - a))); out.setInt16(44 + i * 2, v < 0 ? v * 0x8000 : v * 0x7fff, true); }
    return new Blob([out.buffer], { type: "audio/wav" });
  }
  /* which way the head is turned: the nose against the middle of the eyes, in eye-distances (BlazeFace keypoints 0,1 eyes, 2 nose) */
  function yaw(v) {
    try {
      const d = p.det.face.detectForVideo(v, performance.now()).detections; if (d.length !== 1) return null;
      const k = d[0].keypoints; if (!k || k.length < 3) return null;
      const span = Math.abs(k[0].x - k[1].x); if (span < 0.01) return null;
      return (k[2].x - (k[0].x + k[1].x) / 2) / span;
    } catch (e) { return null; }
  }
  /* the two ear photos: the head turned to one side, then to the other (step(name) tells the page what to say) */
  async function earShots(step) {
    const v = await selfVideo(); if (!v) return null;
    if (!p.det) p.det = await detectors();
    const shot = () => { const c = document.createElement("canvas"), k = Math.min(1, 640 / v.videoWidth); c.width = Math.round(v.videoWidth * k); c.height = Math.round(v.videoHeight * k);
      c.getContext("2d").drawImage(v, 0, 0, c.width, c.height); return new Promise(res => c.toBlob(res, "image/jpeg", 0.85)); };
    /* a turn of the head held for half a second, within ten seconds; no turn, no photo (the step stops: "turn further") */
    const turned = async (sign) => {
      if (!p.det) { await wait(3000); return { side: sign, blob: await shot() }; }
      let held = 0, side = sign;
      for (let i = 0; i < 100; i++) {
        await wait(100);
        const y = yaw(v);
        if (y !== null && Math.abs(y) > 0.35 && (sign === 0 || Math.sign(y) === sign)) { side = Math.sign(y); if (++held >= 5) return { side, blob: await shot() }; } else held = 0;
      }
      return null;
    };
    /* the front with both hands raised beside the face, palms and wrists showing: the hand tracker must see two hands up
       at face height for half a second, within fifteen seconds */
    const raised = async () => {
      const ht = await Promise.race([handTracker(), wait(8000).then(() => null)]);
      if (!ht) { await wait(3000); return shot(); }                  /* no tracker: the photo, and the server's model judges */
      let held = 0;
      for (let i = 0; i < 150; i++) {
        await wait(100);
        let r; try { r = ht.detectForVideo(v, performance.now()); } catch (e) { continue; }
        const up = (r.landmarks || []).filter(h => h[0].y < 0.9 && (h[9].y < 0.62));    /* wrist in the picture, the palm's middle high */
        if (up.length >= 2) { if (++held >= 5) return shot(); } else held = 0;
      }
      return null;
    };
    step("front"); const front = await raised(); if (!front) { step("stop"); return { error: "hands" }; }
    step("first"); const a = await turned(0); if (!a) { step("stop"); return { error: "turn" }; }
    step("second"); const b = await turned(-a.side || 0); if (!b) { step("stop"); return { error: "turn" }; }
    step("done");
    return a.blob && b.blob ? { front, first: a.blob, second: b.blob } : null;
  }
  /* the room scan: the webcam (or the laptop) turned to each view in turn, a still of each and a video of the whole of it.
     step(view, secondsLeft) tells the page what to show */
  const SCAN = ["front", "left", "right", "back", "ceiling", "desk", "under"];
  async function roomScan(step, seconds = 5) {
    const v = await selfVideo(); if (!v) return null;
    let rec = null; const parts = [];
    try { rec = new MediaRecorder(new MediaStream(p.cam.getVideoTracks()), { mimeType: "video/webm;codecs=vp8", videoBitsPerSecond: 250000 }); rec.ondataavailable = e => e.data.size && parts.push(e.data); rec.start(); } catch (e) { rec = null; }
    const stills = {};
    for (const view of SCAN) {
      for (let s = seconds; s > 0; s--) { step(view, s); await wait(1000); }
      const c = document.createElement("canvas"), k = Math.min(1, 640 / v.videoWidth); c.width = Math.round(v.videoWidth * k); c.height = Math.round(v.videoHeight * k);
      c.getContext("2d").drawImage(v, 0, 0, c.width, c.height); stills[view] = await new Promise(res => c.toBlob(res, "image/jpeg", 0.8));
    }
    step("done", 0);
    let clip = null;
    if (rec) { await new Promise(res => { rec.onstop = res; rec.stop(); }); clip = parts.length ? new Blob(parts, { type: "video/webm" }) : null; }
    return { stills, clip };
  }

  function preview() {
    let v = document.getElementById("hphoSelf");
    if (!p?.cam) { v?.remove(); return; }
    if (!v) { v = p.video || document.createElement("video"); v.id = "hphoSelf"; v.className = "hpho-self"; v.muted = true; v.playsInline = true; v.autoplay = true; (p.slot?.isConnected ? p.slot : document.body).append(v); }
    p.video = v;
    if (v.srcObject !== p.cam) v.srcObject = p.cam;
    v.play?.().catch(() => {});
  }
  /* where the preview sits: in the check page's slot (large, with the face tracked), or in the corner (slot null) */
  function dock(slot) {
    if (!p) { if (slot) p = {}; else return; }
    p.slot = slot || null;
    const v = p.video; if (!v) return;
    (slot || document.body).append(v); v.play?.().catch(() => {});
    if (slot) track(slot); else untrack();
  }
  /* face tracking on the preview, like a phone camera's: a box follows the face, green when it is well placed (one face,
     big enough, in the middle, lit), amber when it should move, red when there is no face or more than one */
  function track(slot) {
    let c = slot.querySelector(".hpho-track-box");
    if (!c) { c = Object.assign(document.createElement("canvas"), { className: "hpho-track-box" }); slot.append(c); }
    if (p.tracking) return; p.tracking = true;
    let last = 0;
    const loop = async now => {
      if (!p?.tracking) return;
      requestAnimationFrame(loop);
      if (now - last < 66) return; last = now;
      const v = document.getElementById("hphoSelf"), box = p.slot?.querySelector(".hpho-track-box");
      if (!v?.videoWidth || !box) return;
      if (!p.det) { if (!p.detLoading) { p.detLoading = true; p.det = await detectors(); } return; }
      const W = v.videoWidth, H = v.videoHeight; if (box.width !== W) { box.width = W; box.height = H; }
      const g = box.getContext("2d"); g.clearRect(0, 0, W, H);
      let d; try { d = p.det.face.detectForVideo(v, performance.now()).detections; } catch (e) { return; }
      const many = d.length > 1;
      for (const f of d) {
        const b = f.boundingBox, cx = (b.originX + b.width / 2) / W, cy = (b.originY + b.height / 2) / H;
        const good = !many && b.width / W >= 0.16 && Math.abs(cx - 0.5) <= 0.25 && Math.abs(cy - 0.5) <= 0.3;
        g.strokeStyle = many ? "#ff4d4f" : good ? "#2fd06b" : "#ffb020"; g.lineWidth = Math.max(3, W / 160);
        const r = 14, x = b.originX, y = b.originY, w = b.width, h = b.height;
        g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r); g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.stroke();
        g.fillStyle = g.strokeStyle; for (const k of (f.keypoints || []).slice(0, 6)) { g.beginPath(); g.arc(k.x * W, k.y * H, Math.max(2.5, W / 220), 0, 7); g.fill(); }
      }
      slot.dataset.face = d.length === 0 ? "none" : many ? "many" : "one";
    };
    requestAnimationFrame(loop);
  }
  function untrack() { if (p) p.tracking = false; document.querySelectorAll(".hpho-track-box").forEach(c => c.remove()); }
  function frame(stream, width) {
    const track = stream?.getVideoTracks?.()[0]; if (!track) return null;
    const v = stream === p.cam ? document.getElementById("hphoSelf") : (p.scrVideo ||= Object.assign(document.createElement("video"), { muted: true, srcObject: stream }));
    if (v !== document.getElementById("hphoSelf")) v.play?.().catch(() => {});
    if (!v.videoWidth) return null;
    const k = Math.min(1, width / v.videoWidth), c = document.createElement("canvas"); c.width = Math.round(v.videoWidth * k); c.height = Math.round(v.videoHeight * k);
    c.getContext("2d").drawImage(v, 0, 0, c.width, c.height);
    return new Promise(res => c.toBlob(res, "image/jpeg", 0.85));
  }

  /* start watching: events go to onEvent(kind, detail), snapshots to upload(blob, source, reason) */
  function start({ onEvent, upload, clip }) {
    if (!p?.cam) { onEvent("camera_stopped", "no camera"); return; }
    p.onEvent = onEvent; p.upload = upload; p.clip = clip; p.last = {}; p.since = {}; p.alive = true; p.errors = 0; p.pace = p.pace || [10, 60];
    if (p.scr) { p.scrVideo = Object.assign(document.createElement("video"), { muted: true, playsInline: true, srcObject: p.scr }); p.scrVideo.play?.().catch(() => {}); }
    onEvent("camera_started", p.det ? "local detection on" : "local detection unavailable");
    p.cam.getTracks().forEach(t => t.addEventListener("ended", () => p.alive && onEvent("camera_stopped", t.kind + " ended")));
    try {
      const ctx = new AudioContext(), src = ctx.createMediaStreamSource(p.cam), an = ctx.createAnalyser(); an.fftSize = 1024; src.connect(an);
      p.audio = { ctx, an, buf: new Float32Array(an.fftSize) };
      if (p.scr?.getAudioTracks().length) { const s2 = ctx.createMediaStreamSource(new MediaStream(p.scr.getAudioTracks())), a2 = ctx.createAnalyser(); a2.fftSize = 1024; s2.connect(a2); p.sys = { an: a2, buf: new Float32Array(a2.fftSize) }; }
    } catch (e) {}
    record();
    let tick = 0;
    p.loop = setInterval(() => {
      tick++;
      const v = document.getElementById("hphoSelf"), t = performance.now(), seen = {};
      if (p.det && v?.videoWidth) {
        try { const n = p.det.face.detectForVideo(v, t).detections.length; p.faces = n; seen.face_missing = n === 0; seen.faces_multiple = n > 1; } catch (e) { p.errors++; p.lastError = String(e?.message || e).slice(0, 120); }
        if (tick % 3 === 0) try { seen.phone_seen = p.det.objects.detectForVideo(v, t).detections.some(d => d.categories?.some(c => c.categoryName === "cell phone")); } catch (e) {}
        else seen.phone_seen = !!p.since.phone_seen;
      }
      if (p.audio) { p.audio.an.getFloatTimeDomainData(p.audio.buf); let s = 0; for (const x of p.audio.buf) s += x * x; seen.voice = Math.sqrt(s / p.audio.buf.length) > 0.04; }
      /* anything the computer itself plays (a video, a call, a voice assistant) */
      if (p.sys) { p.sys.an.getFloatTimeDomainData(p.sys.buf); let s = 0; for (const x of p.sys.buf) s += x * x; seen.system_sound = Math.sqrt(s / p.sys.buf.length) > 0.01; }
      for (const [kind, on] of Object.entries(seen)) {
        if (!on) { p.since[kind] = 0; continue; }
        p.since[kind] = (p.since[kind] || 0) + 1;
        if (p.since[kind] >= NEAR[kind] && Date.now() / 1000 - (p.last[kind] || 0) > COOLDOWN) { p.last[kind] = Date.now() / 1000; onEvent(kind); snap(kind); }
      }
    }, 1000);
    const next = () => { const [lo, hi] = p.pace; p.timer = setTimeout(() => { snap(p.paceReason || "random"); if (p.alive) next(); }, (lo + Math.random() * (hi - lo)) * 1000); };
    p.next = next; next();
  }
  /* how often the random snapshots come, and why they are taken: after the time is over they come every few seconds,
     marked after_time, so a person can see whether anyone kept writing */
  function pace(lo, hi, reason) {
    if (!p) return; p.pace = [lo, hi]; p.paceReason = reason || null;
    if (p.alive && p.next) { clearTimeout(p.timer); p.next(); }
  }
  /* a full-size still from the webcam (an answer page held up to it), JPEG */
  async function still() {
    const v = document.getElementById("hphoSelf"), track = p?.cam?.getVideoTracks()[0]; if (!v?.videoWidth || !track) return null;
    /* the camera's largest picture for the moment of the photo (an answer page needs its handwriting), then back to 640x480 */
    try { await track.applyConstraints({ width: { ideal: 3840 }, height: { ideal: 2160 }, frameRate: { ideal: 15 } }); } catch (e) {}
    for (let i = 0; i < 20 && v.videoWidth <= 640; i++) await wait(100);
    await wait(400);
    const c = document.createElement("canvas"); c.width = v.videoWidth; c.height = v.videoHeight; c.getContext("2d").drawImage(v, 0, 0);
    const blob = await new Promise(res => c.toBlob(res, "image/jpeg", 0.94));
    try { await track.applyConstraints({ width: 640, height: 480, frameRate: { ideal: 15, max: 15 } }); } catch (e) {}
    return blob;
  }
  async function snap(reason) {
    if (!p?.alive || !p.upload) return;
    /* like HaslaLab's page scans: the resolution is kept where reading depends on it, the bytes come off through the
       JPEG quality (0.85 is about half of 0.94 and still reads). The webcam at its 640 px; the screen at its own size
       up to 1920 px, so a chat window or a formula on it can be read */
    for (const [source, stream, width] of [["webcam", p.cam, 640], ["screen", p.scr, 1920]]) {
      try { const blob = await frame(stream, width); if (blob) p.upload(blob, source, reason); } catch (e) {}
    }
  }
  /* the two recordings, in five-minute segments: each segment is a whole WebM file (its own header), uploaded as it
     closes, so any five minutes can be played on its own. A segment that failed to go up is tried again with the next */
  const SEGMENT = 300000;
  function record() {
    if (!p?.clip || p.recs) return;
    p.recs = [];
    /* VP9 keeps small text and faces at fewer bytes than VP8; the bit rates are ceilings, and a screen that does not
       change costs almost nothing. Webcam 640x480 at 15 fps: enough to see where the eyes and hands go */
    const pick = t => ["video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm"].find(m => MediaRecorder.isTypeSupported?.(m)) || "";
    const sources = [["webcam", p.cam, 250000], ...(p.scr ? [["screen", p.scr, 350000]] : [])];
    for (const [source, stream, bits] of sources) {
      const segment = () => {
        if (!p?.alive || !stream.active) return;
        let r; const parts = [];
        try { r = new MediaRecorder(stream, { mimeType: pick(), videoBitsPerSecond: bits, audioBitsPerSecond: 32000 }); } catch (e) { p.onEvent?.("recording_failed", source + ": " + (e?.name || "recorder")); return; }
        r.ondataavailable = e => { if (e.data.size) parts.push(e.data); };
        r.onstop = () => { if (parts.length) p?.clip?.(new Blob(parts, { type: "video/webm" }), source); if (p?.alive) segment(); };
        r.start(1000); p.recs.push(r);
        setTimeout(() => { if (r.state !== "inactive") r.stop(); }, SEGMENT);
      };
      segment();
    }
    p.onEvent?.("recording_started", sources.map(s => s[0]).join("+"));
  }
  /* close the open segments now (the answers are in, or the page is leaving): their last minutes go up too */
  function flushRecordings() {
    const recs = p?.recs || []; if (p) p.alive = false;
    return Promise.all(recs.filter(r => r.state !== "inactive").map(r => new Promise(res => { const was = r.onstop; r.onstop = () => { was?.(); res(); }; r.stop(); })));
  }
  async function stop() {
    if (!p) return;
    await flushRecordings().catch(() => {});
    p.alive = false; clearInterval(p.loop); clearTimeout(p.timer);
    try { p.audio?.ctx.close(); } catch (e) {}
    for (const s of [p.cam, p.scr]) s?.getTracks().forEach(t => t.stop());
    document.getElementById("hphoSelf")?.remove();
    p = null;
  }
  /* counters only (no image, no stream), for the page's own status line and for tests */
  const stats = () => p ? { alive: !!p.alive, detector: !!p.det, faces: p.faces ?? null, errors: p.errors || 0, lastError: p.lastError || null, since: { ...(p.since || {}) } } : null;
  window.HL_HPHO_PROCTOR = { check, shareScreen, dock, faceCheck, micCheck, earShots, roomScan, start, snap, stop, stats, pace, still, wav16k, SCAN };
})();
