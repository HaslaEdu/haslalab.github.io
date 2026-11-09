/* HPhO proctoring in the exam page (hpho-exam.js): the webcam and microphone, and the screen, watched on the candidate's
   own computer. Faces, a phone in view and sustained speech are detected locally (MediaPipe Tasks for vision, a level
   meter for sound), so the video never leaves the computer as a stream: what reaches the server are events and small
   JPEG snapshots, taken at random intervals (10-60 s, so a candidate cannot time them) and at once when something is
   detected. The AI that reviews the snapshots runs on the server after the exam; a person decides. */
(() => {
  const VISION = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.21";
  const MODELS = {
    face: "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite",
    objects: "https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite0/int8/1/efficientdet_lite0.tflite",
  };
  const NEAR = { face_missing: 6, faces_multiple: 3, phone_seen: 2, voice: 3 };   /* seconds a condition must last */
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
  async function check() {
    const out = { camera: false, mic: false, screen: false, detector: false };
    if (live(p?.cam)) { out.camera = p.cam.getVideoTracks().length > 0; out.mic = p.cam.getAudioTracks().length > 0; }
    else try {
      const cam = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, facingMode: "user" }, audio: { echoCancellation: false, noiseSuppression: false } });
      out.camera = cam.getVideoTracks().length > 0; out.mic = cam.getAudioTracks().length > 0;
      p = { ...(p || {}), cam };
    } catch (e) { out.error = e?.name || "camera"; }
    if (live(p?.scr)) out.screen = true;
    else try {
      const scr = await navigator.mediaDevices.getDisplayMedia({ video: { frameRate: 1 }, audio: false }); p = { ...(p || {}), scr };
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
  /* is the microphone heard? up to ten seconds while the candidate reads a sentence aloud; level(0..1) feeds a meter */
  async function micCheck(level) {
    if (!p?.cam?.getAudioTracks().length) return { ok: false, reason: "no_mic" };
    let ctx; try { ctx = new AudioContext(); await ctx.resume(); } catch (e) { return { ok: false, reason: "no_audio" }; }
    const an = ctx.createAnalyser(); an.fftSize = 1024; ctx.createMediaStreamSource(p.cam).connect(an);
    const buf = new Float32Array(an.fftSize); let voiced = 0, top = 0;
    try {
      for (let i = 0; i < 100 && voiced < 12; i++) {
        await wait(100);
        an.getFloatTimeDomainData(buf); let s = 0; for (const x of buf) s += x * x;
        const rms = Math.sqrt(s / buf.length); top = Math.max(top, rms); level?.(Math.min(1, rms * 8));
        if (rms > 0.03) voiced++;
      }
    } finally { level?.(0); ctx.close().catch(() => {}); }
    return voiced >= 12 ? { ok: true } : { ok: false, reason: top < 0.008 ? "silent" : "quiet" };
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
    const turned = async (sign) => {
      /* up to eight seconds for a clear turn held for half a second; then the photo is taken anyway */
      let held = 0, side = sign;
      for (let i = 0; i < 80; i++) {
        await wait(100);
        const y = p.det ? yaw(v) : null;
        if (y !== null && Math.abs(y) > 0.35 && (sign === 0 || Math.sign(y) === sign)) { side = Math.sign(y); if (++held >= 5) break; } else held = 0;
      }
      return { side, blob: await shot() };
    };
    step("first"); const a = await turned(0);
    step("second"); const b = await turned(a.side ? -a.side : 0);
    step("done");
    return a.blob && b.blob ? { first: a.blob, second: b.blob } : null;
  }

  function preview() {
    let v = document.getElementById("hphoSelf");
    if (!p?.cam) { v?.remove(); return; }
    if (!v) { v = p.video || document.createElement("video"); v.id = "hphoSelf"; v.className = "hpho-self"; v.muted = true; v.playsInline = true; v.autoplay = true; (p.slot?.isConnected ? p.slot : document.body).append(v); }
    p.video = v;
    if (v.srcObject !== p.cam) v.srcObject = p.cam;
    v.play?.().catch(() => {});
  }
  /* where the preview sits: in the check page's slot (large), or in the corner (slot null) */
  function dock(slot) {
    if (!p) { if (slot) p = {}; else return; }
    p.slot = slot || null;
    const v = p.video; if (!v) return;
    (slot || document.body).append(v); v.play?.().catch(() => {});
  }
  function frame(stream, width) {
    const track = stream?.getVideoTracks?.()[0]; if (!track) return null;
    const v = stream === p.cam ? document.getElementById("hphoSelf") : (p.scrVideo ||= Object.assign(document.createElement("video"), { muted: true, srcObject: stream }));
    if (v !== document.getElementById("hphoSelf")) v.play?.().catch(() => {});
    if (!v.videoWidth) return null;
    const c = document.createElement("canvas"), k = width / v.videoWidth; c.width = width; c.height = Math.round(v.videoHeight * k);
    c.getContext("2d").drawImage(v, 0, 0, c.width, c.height);
    return new Promise(res => c.toBlob(res, "image/jpeg", 0.6));
  }

  /* start watching: events go to onEvent(kind, detail), snapshots to upload(blob, source, reason) */
  function start({ onEvent, upload }) {
    if (!p?.cam) { onEvent("camera_stopped", "no camera"); return; }
    p.onEvent = onEvent; p.upload = upload; p.last = {}; p.since = {}; p.alive = true; p.errors = 0;
    if (p.scr) { p.scrVideo = Object.assign(document.createElement("video"), { muted: true, playsInline: true, srcObject: p.scr }); p.scrVideo.play?.().catch(() => {}); }
    onEvent("camera_started", p.det ? "local detection on" : "local detection unavailable");
    p.cam.getTracks().forEach(t => t.addEventListener("ended", () => p.alive && onEvent("camera_stopped", t.kind + " ended")));
    try {
      const ctx = new AudioContext(), src = ctx.createMediaStreamSource(p.cam), an = ctx.createAnalyser(); an.fftSize = 1024; src.connect(an);
      p.audio = { ctx, an, buf: new Float32Array(an.fftSize) };
    } catch (e) {}
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
      for (const [kind, on] of Object.entries(seen)) {
        if (!on) { p.since[kind] = 0; continue; }
        p.since[kind] = (p.since[kind] || 0) + 1;
        if (p.since[kind] >= NEAR[kind] && Date.now() / 1000 - (p.last[kind] || 0) > COOLDOWN) { p.last[kind] = Date.now() / 1000; onEvent(kind); snap(kind); }
      }
    }, 1000);
    const next = () => { p.timer = setTimeout(() => { snap("random"); if (p.alive) next(); }, (10 + Math.random() * 50) * 1000); };
    next();
  }
  async function snap(reason) {
    if (!p?.alive || !p.upload) return;
    for (const [source, stream, width] of [["webcam", p.cam, 320], ["screen", p.scr, 640]]) {
      try { const blob = await frame(stream, width); if (blob) p.upload(blob, source, reason); } catch (e) {}
    }
  }
  function stop() {
    if (!p) return;
    p.alive = false; clearInterval(p.loop); clearTimeout(p.timer);
    try { p.audio?.ctx.close(); } catch (e) {}
    for (const s of [p.cam, p.scr]) s?.getTracks().forEach(t => t.stop());
    document.getElementById("hphoSelf")?.remove();
    p = null;
  }
  /* counters only (no image, no stream), for the page's own status line and for tests */
  const stats = () => p ? { alive: !!p.alive, detector: !!p.det, faces: p.faces ?? null, errors: p.errors || 0, lastError: p.lastError || null, since: { ...(p.since || {}) } } : null;
  window.HL_HPHO_PROCTOR = { check, dock, faceCheck, micCheck, earShots, start, snap, stop, stats };
})();
