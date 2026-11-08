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

  /* the technical check: camera and microphone (and the screen, inside the desktop app) can be opened */
  async function check() {
    const out = { camera: false, mic: false, screen: false, detector: false };
    try {
      const cam = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, facingMode: "user" }, audio: { echoCancellation: false, noiseSuppression: false } });
      out.camera = cam.getVideoTracks().length > 0; out.mic = cam.getAudioTracks().length > 0;
      p = { ...(p || {}), cam };
    } catch (e) { out.error = e?.name || "camera"; }
    try { const scr = await navigator.mediaDevices.getDisplayMedia({ video: { frameRate: 1 }, audio: false }); out.screen = scr.getVideoTracks().length > 0; p = { ...(p || {}), scr }; }
    catch (e) { out.screenError = e?.name || "screen"; }
    if (out.camera) { p.det = p.det || await detectors(); out.detector = !!p.det; }
    preview();
    return out;
  }
  function preview() {
    let v = document.getElementById("hphoSelf");
    if (!p?.cam) { v?.remove(); return; }
    if (!v) { v = document.createElement("video"); v.id = "hphoSelf"; v.className = "hpho-self"; v.muted = true; v.playsInline = true; v.autoplay = true; document.body.append(v); }
    if (v.srcObject !== p.cam) v.srcObject = p.cam;
    v.play?.().catch(() => {});
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
  window.HL_HPHO_PROCTOR = { check, start, snap, stop, stats };
})();
