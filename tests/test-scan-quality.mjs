import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { createRequire } from 'node:module';
import vm from 'node:vm';

const scannerSource = await fs.readFile(new URL('../sim/labscan/scanner.js', import.meta.url), 'utf8');
const scanner = await import('data:text/javascript;base64,' + Buffer.from(scannerSource).toString('base64'));
const require = createRequire(import.meta.url), Review = require('../sim/contest-review.js');

test('JPEG, PNG and WebP already under the upload limit keep their original bytes and MIME', async () => {
  for (const type of ['image/jpeg', 'image/png', 'image/webp']) {
    const original = new Blob(['original pencil strokes'], { type });
    assert.equal(await scanner.encodeUpload(original), original);
  }
});

function encodingFixture(width, height, sizeFor) {
  const saved = { document: globalThis.document, createImageBitmap: globalThis.createImageBitmap };
  const calls = [], bitmaps = [];
  globalThis.createImageBitmap = async (_blob, options) => {
    const bitmap = { width, height, options, closed: false, close() { this.closed = true; } };
    bitmaps.push(bitmap); return bitmap;
  };
  globalThis.document = { createElement() {
    const c = { width: 0, height: 0, getContext() { return { drawImage() {}, fillRect() {} }; },
      toBlob(resolve, type, quality) { calls.push({ width: c.width, height: c.height, type, quality }); resolve(new Blob([new Uint8Array(sizeFor(c, quality))], { type })); } };
    return c;
  } };
  return { calls, bitmaps, restore() { Object.assign(globalThis, saved); } };
}

test('oversized 200dpi A4 tries quality settings without reducing document resolution', async () => {
  const fixture = encodingFixture(1654, 2339, (_canvas, q) => q > .84 ? 2000000 : 1700000);
  try {
    const out = await scanner.encodeUpload(new Blob([new Uint8Array(2100000)], { type: 'image/png' }));
    assert.equal(out.type, 'image/jpeg'); assert.equal(out.size, 1700000);
    assert.deepEqual(fixture.calls.map(x => x.quality), [.92, .88, .84]);
    assert.ok(fixture.calls.every(x => x.width === 1654 && x.height === 2339));
    assert.equal(fixture.bitmaps[0].options.imageOrientation, 'from-image');
    assert.equal(fixture.bitmaps[0].closed, true);
  } finally { fixture.restore(); }
});

test('a difficult photo stops at 200dpi instead of silently making a smaller unreadable upload', async () => {
  const fixture = encodingFixture(4000, 6000, () => 2000000);
  try {
    await assert.rejects(scanner.encodeUpload(new Blob([new Uint8Array(2200000)], { type: 'image/jpeg' })), e => e.code === 'image_too_big');
    assert.deepEqual([...new Set(fixture.calls.map(x => Math.max(x.width, x.height)))], [2400, 2339]);
    assert.ok(fixture.calls.every(x => x.quality >= .76));
    assert.equal(fixture.bitmaps[0].closed, true);
  } finally { fixture.restore(); }
});

test('white paper with crisp writing is not mistaken for reflected glare', () => {
  const W = 160, H = 220, data = new Uint8ClampedArray(W * H * 4).fill(255);
  for (let y = 20; y < H - 20; y += 12) for (let x = 15; x < W - 15; x++) {
    if (x % 7 < 3) { const i = (y * W + x) * 4; data[i] = data[i + 1] = data[i + 2] = 30; }
  }
  const q = scanner.inspectDocumentPixels(data, W, H);
  assert.ok(q.glare > .3); assert.ok(q.focus >= 22); assert.equal(q.ok, true); assert.equal(q.hint, null);
  data.fill(230); for (let i = 3; i < data.length; i += 4) data[i] = 255;
  assert.equal(scanner.inspectDocumentPixels(data, W, H).ok, false);
});

function pixelFixture() {
  const saved = { document: globalThis.document, Image: globalThis.Image, ImageData: globalThis.ImageData, createImageBitmap: globalThis.createImageBitmap };
  const decode = url => JSON.parse(Buffer.from(url.split(',')[1], 'base64').toString());
  class Canvas {
    width = 0; height = 0; data = null;
    ensure() { if (!this.data || this.data.length !== this.width * this.height * 4) this.data = new Uint8ClampedArray(this.width * this.height * 4); }
    getContext() { const c = this; return {
      drawImage(image, _x, _y, width = image.width, height = image.height) {
        c.ensure(); const source = image.data;
        for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
          const s = (Math.min(image.height - 1, Math.floor(y * image.height / height)) * image.width + Math.min(image.width - 1, Math.floor(x * image.width / width))) * 4;
          c.data.set(source.slice(s, s + 4), (y * c.width + x) * 4);
        }
      },
      getImageData() { c.ensure(); return { data: c.data, width: c.width, height: c.height }; },
      putImageData(image) { c.data = new Uint8ClampedArray(image.data); },
    }; }
    payload() { this.ensure(); return { width: this.width, height: this.height, data: [...this.data] }; }
    toDataURL(type) { return 'data:' + type + ';base64,' + Buffer.from(JSON.stringify(this.payload())).toString('base64'); }
    toBlob(resolve, type) { resolve(new Blob([JSON.stringify(this.payload())], { type })); }
  }
  globalThis.document = { createElement: () => new Canvas() };
  globalThis.ImageData = class { constructor(data, width, height) { Object.assign(this, { data, width, height }); } };
  globalThis.Image = class { set src(url) { Object.assign(this, decode(url)); this.data = new Uint8ClampedArray(this.data); queueMicrotask(() => this.onload()); } };
  globalThis.createImageBitmap = async file => { const p = JSON.parse(await file.text()); return { ...p, data: new Uint8ClampedArray(p.data), close() {} }; };
  return { decode, restore() { Object.assign(globalThis, saved); } };
}

test('manual mode changes reuse a lossless captured baseline and produce stable original-colour output', async () => {
  const fixture = pixelFixture(), W = 100, H = 141;
  const pixels = new Uint8ClampedArray(W * H * 4).fill(255);
  const pencil = (60 * W + 45) * 4; pixels[pencil] = 177; pixels[pencil + 1] = 183; pixels[pencil + 2] = 191;
  const corners = [{ x: 0, y: 0 }, { x: W - 1, y: 0 }, { x: 0, y: H - 1 }, { x: W - 1, y: H - 1 }];
  try {
    const file = new Blob([JSON.stringify({ width: W, height: H, data: [...pixels] })], { type: 'image/png' });
    const first = await scanner.processShot(file, { corners, mode: 'original', dpi: 12 });
    assert.ok(first.baseUrl.startsWith('data:image/png;'));
    assert.deepEqual(fixture.decode(first.baseUrl).data.slice(pencil, pencil + 4), [177, 183, 191, 255]);
    const a = await scanner.reprocess(first.baseUrl, first.corners, 'original', 12);
    await scanner.reprocess(first.baseUrl, first.corners, 'mono', 12);
    const b = await scanner.reprocess(first.baseUrl, first.corners, 'original', 12);
    assert.deepEqual(new Uint8Array(await a.blob.arrayBuffer()), new Uint8Array(await b.blob.arrayBuffer()));
    assert.equal(a.width, 99); assert.equal(a.height, 140);
  } finally { fixture.restore(); }
});

test('manual marker coordinates preserve the paper margins outside the printed squares', async () => {
  const fixture = pixelFixture(), W = 100, H = 141, pixels = new Uint8ClampedArray(W * H * 4).fill(255);
  for (let y = 0; y < 4; y++) for (let x = 0; x < W; x++) { const i = (y * W + x) * 4; pixels[i] = 180; pixels[i + 1] = 20; pixels[i + 2] = 20; }
  const m = scanner.MARKER_INSET, points = [{ x: m.left * W, y: m.top * H }, { x: m.right * W, y: m.top * H }, { x: m.left * W, y: m.bottom * H }, { x: m.right * W, y: m.bottom * H }];
  const base = 'data:image/png;base64,' + Buffer.from(JSON.stringify({ width: W, height: H, data: [...pixels] })).toString('base64');
  try {
    const marker = await scanner.reprocess(base, points, 'original', 12, m);
    const page = await scanner.reprocess(base, points, 'original', 12, null);
    const a = JSON.parse(await marker.blob.text()), b = JSON.parse(await page.blob.text()), at = 49 * 4;
    assert.ok(a.data[at + 1] < 100, 'red top margin survives the marker inset');
    assert.ok(b.data[at + 1] > 240, 'the same points treated as paper edges would crop that margin');
  } finally { fixture.restore(); }
});

test('a non-A4 rectangle is still cropped to A4 with its best corners, flagged for a check; keeping the original stays possible', async () => {
  const fixture = pixelFixture(), W = 200, H = 220, pixels = new Uint8ClampedArray(W * H * 4);
  for (let y=0;y<H;y++)for(let x=0;x<W;x++) {
    const inside=x>=35&&x<165&&y>=45&&y<175;
    pixels.set(inside?[240,238,230,255]:[50,55,60,255],(y*W+x)*4);
  }
  pixels.set([35,65,190,255],(80*W+80)*4);
  const original=new Blob([JSON.stringify({width:W,height:H,data:[...pixels]})],{type:'image/png'});
  try {
    const first=await scanner.processShot(original,{mode:'mono',dpi:12});
    assert.equal(first.method,'page');assert.equal(first.paperStatus,'aspect_mismatch');
    assert.equal(first.a4WarpApplied,true);assert.equal(first.cornersReliable,false,'an unverified quad asks for a corner check');
    assert.deepEqual([first.width,first.height],[99,140]);
    const changed=await scanner.reprocess(first.baseUrl,first.corners,'clean',12,null,{preserveOriginal:true});
    assert.equal(changed.a4WarpApplied,false);assert.equal(changed.warpApplied,false);
    assert.deepEqual([changed.width,changed.height],[W,H],'keeping the original never silently forces A4; the photo is still cleaned as a scan');
    const confirmed=await scanner.reprocess(first.baseUrl,first.corners,'original',12,null,{pageFormat:'a4'});
    assert.equal(confirmed.a4WarpApplied,true);assert.deepEqual([confirmed.width,confirmed.height],[99,140]);
    const explicit=await scanner.processShot(original,{corners:first.corners,mode:'original',dpi:12,pageFormat:'a4'});
    assert.equal(explicit.paperStatus,'manual_a4');assert.equal(explicit.a4WarpApplied,true);
  } finally { fixture.restore(); }
});

test('without a document worker the classical proposal makes the scan, flagged for a check, and correction preserves coloured page detail', async () => {
  const fixture = pixelFixture(), W = 320, H = 450, pixels = new Uint8ClampedArray(W * H * 4);
  const rect = (x0,y0,x1,y1,color) => { for(let y=y0;y<y1;y++)for(let x=x0;x<x1;x++)pixels.set([...color,255],(y*W+x)*4); };
  rect(0,0,W,H,[42,48,54]); rect(45,40,275,366,[246,244,240]);
  rect(60,46,260,55,[195,45,55]); // coloured heading close to the real paper margin
  rect(130,90,137,320,[35,65,190]); // original coloured pencil stroke
  for(let y=125;y<300;y+=25)rect(75,y,230,y+3,[40,40,40]);
  const original = new Blob([JSON.stringify({width:W,height:H,data:[...pixels]})],{type:'image/png'});
  try {
    const result=await scanner.processShot(original,{mode:'original',dpi:12});
    assert.equal(result.method,'page'); assert.ok(result.autoScore>.5);
    const expected=[{x:45,y:40},{x:275,y:40},{x:45,y:366},{x:275,y:366}];
    result.corners.forEach((corner,index)=>assert.ok(Math.hypot(corner.x-expected[index].x,corner.y-expected[index].y)<9,'each detected point follows the outer paper edge'));
    assert.equal(result.warpApplied,true);assert.equal(result.cornersReliable,false);assert.deepEqual([result.width,result.height],[99,140]);assert.ok(Math.abs(result.sourceShortSide-230)<12);
    const corrected=await scanner.reprocess(result.baseUrl,result.corners,'original',12,null,{pageFormat:'a4'});
    assert.equal(corrected.width,99);assert.equal(corrected.height,140);
    const base=fixture.decode(result.baseUrl); assert.equal(base.width,W); assert.equal(base.height,H); assert.ok(Buffer.from(base.data).equals(Buffer.from(pixels)),'the editable baseline retains every original pixel');
    const output=JSON.parse(await corrected.blob.text()), rows=[]; let blue=0,darkBorder=0;
    for(let y=0;y<output.height;y++)for(let x=0;x<output.width;x++) {
      const i=(y*output.width+x)*4,[r,g,b]=output.data.slice(i,i+3);
      if(r>140&&g<100&&b<110)rows.push(y);
      if(b>130&&r<110&&g<130)blue++;
      if((x===0||y===0||x===output.width-1||y===output.height-1)&&r<90&&g<90&&b<100)darkBorder++;
    }
    assert.ok(rows.length>20&&Math.min(...rows)<10,'the coloured top margin remains near the output edge without invented marker inset');
    assert.ok(blue>40,'colour and pencil detail are preserved in original mode');
    assert.ok(darkBorder<30,'the wrapper does not invent an expanded desk border by treating paper corners as marker centres');
  } finally { fixture.restore(); }
});

test('the desktop review sends PNG as PNG and retains the dedicated QR token header', async () => {
  const calls = [], body = new Blob(['lossless mono'], { type: 'image/png' });
  const client = Review.createClient({ fetch: async (url, options) => { calls.push({ url, ...options }); return { ok: true, json: async () => ({}) }; } });
  await client.upload('fixture-token', 'Q1', body);
  assert.equal(calls[0].headers['Content-Type'], 'image/png');
  assert.equal(calls[0].headers['X-Lab-Token'], 'fixture-token');
  assert.equal(calls[0].body, body); assert.ok(!calls[0].url.includes('fixture-token'));
});

test('a saved photo with failed OCR reports storage/provider failure instead of claiming it was read', () => {
  const failed = { ocr_status: 'failed', ocr_error: 'ocr_storage_limit', legible: 'good' };
  assert.match(Review.uploadWarning(failed), /사진은 보관.*합계 용량/);
  assert.match(Review.uploadWarning(failed, 'en'), /photo was saved.*storage limit/i);
  assert.match(Review.uploadWarning({ ocr_status: 'failed', read: { ocr: { error: 'ocr_storage_limit' } } }), /합계 용량/);
  assert.match(Review.uploadWarning({ ocr_status: 'failed', ocr_error: 'provider_error' }), /글자를 읽지 못/);
  assert.equal(Review.uploadWarning({ ocr_status: 'done', legible: 'good' }), '');
  assert.equal(Review.uploadWarning({ ocr_status: 'unpaid' }), '');
});

test('a newer phone photo survives late progress, correction errors and rotation from older photos', async () => {
  const html = await fs.readFile(new URL('../sim/scan.html', import.meta.url), 'utf8');
  const script = html.match(/<script type="module">([\s\S]*?)<\/script>/)[1].replace(/^import .*?;\s*$/m, '');
  const nodes = new Map(), processed = [], rebuilt = [], rotated = [], revoked = [];
  const node = id => {
    if (!nodes.has(id)) nodes.set(id, { innerHTML: '', style: {}, classList: { toggle() {} }, querySelectorAll: () => [], querySelector: () => node('child'), remove() {}, click() {} });
    return nodes.get(id);
  };
  let nextURL = 0;
  class FixtureURL extends URL {
    static createObjectURL() { return 'blob:fixture/' + (++nextURL); }
    static revokeObjectURL(url) { revoked.push(url); }
  }
  const context = vm.createContext({
    URL: FixtureURL, URLSearchParams, Blob, AbortController, console,
    document: { getElementById: node, querySelector: node, createElement: () => node('element'), body: { append() {} }, documentElement: {} },
    location: { hash: '', pathname: '/sim/scan.html' }, history: { replaceState() {} },
    navigator: { language: 'ko' }, window: { HLExamNetwork: require('../sim/exam-network.js') },
    sessionStorage: { getItem: () => null }, localStorage: { getItem: () => null },
    setInterval() {}, setTimeout() {}, clearTimeout() {},
    canProcess: () => true,
    processShot: (file, options) => new Promise((resolve, reject) => processed.push({ file, options, resolve, reject })),
    reprocess: (...args) => new Promise((resolve, reject) => rebuilt.push({ args, resolve, reject })),
    rotatePhoto: file => new Promise(resolve => rotated.push({ file, resolve })),
  });
  new vm.Script(script + '\nglobalThis.phone = { take, redo, releaseShot, getShot: () => shot, getMode: () => mode };').runInContext(context);
  const file = label => new Blob([label], { type: 'image/png' });
  const result = label => ({ blob: file(label), previewUrl: label, baseUrl: label, corners: [], method: 'page', autoScore: 1 });
  const a = file('a'), b = file('b'), c = file('c'), d = file('d');
  const takingA = context.phone.take(a), urlA = context.phone.getShot().originalUrl;
  const takingB = context.phone.take(b), urlB = context.phone.getShot().originalUrl;
  processed[0].options.onProgress(95);
  assert.equal(context.phone.getShot().pct, 0, 'old progress cannot update the new photo');
  processed[0].resolve(result('old-a')); await takingA;
  assert.equal(context.phone.getShot().file, b); assert.equal(context.phone.getShot().busy, true);
  processed[1].resolve(result('current-b')); await takingB;
  assert.equal(context.phone.getShot().previewUrl, 'current-b');

  const editingB = context.phone.redo([], 'mono'), takingC = context.phone.take(c);
  rebuilt[0].reject(new Error('older correction failed')); await editingB;
  assert.equal(context.phone.getShot().file, c); assert.equal(context.phone.getShot().busy, true);
  assert.equal(context.phone.getMode(), 'clean');
  processed[2].resolve(result('current-c')); await takingC;

  const rotatingC = node('rotate').onclick(), takingD = context.phone.take(d);
  rotated[0].resolve(file('rotated-old-c')); await rotatingC;
  assert.equal(processed.length, 4, 'an old rotation cannot start another take over the newest photo');
  assert.equal(context.phone.getShot().file, d);
  processed[3].resolve(result('current-d')); await takingD;
  assert.equal(context.phone.getShot().previewUrl, 'current-d');
  assert.ok(revoked.includes(urlA)); assert.ok(revoked.includes(urlB));
  context.phone.releaseShot(); assert.equal(context.phone.getShot(), null);
});

test('photo preview warns on ambiguous high-score corners until the user confirms them', async () => {
  const html=await fs.readFile(new URL('../sim/scan.html',import.meta.url),'utf8'), script=html.match(/<script type="module">([\s\S]*?)<\/script>/)[1];
  const block=script.slice(script.indexOf('function paintShot()'),script.indexOf('async function redo('));
  const nodes=new Map(), node=id=>{if(!nodes.has(id))nodes.set(id,{innerHTML:'',querySelectorAll:()=>[]});return nodes.get(id);};
  const labels={weak:'UNCERTAIN_CORNERS',a4Shape:'UNVERIFIED_A4_ORIGINAL_RETAINED',processFailed:'PROCESS_FAILED',detail:'detail',answer:'answer',working:'working'};
  const context=vm.createContext({lang:'en',shot:{task:'E1',kind:'answer',previewUrl:'data:fixture',autoScore:.95,cornersReliable:false},$:node,t:()=>labels,
    esc:String,canProcess:()=>false,MONTHLY:false,send(){}});
  vm.runInContext(block,context);context.paintShot();assert.match(node('shot').innerHTML,/UNCERTAIN_CORNERS/,'a balanced quadrilateral is not sufficient evidence for a correct crop');
  context.shot={...context.shot,autoScore:1,cornersReliable:true,method:'manual'};context.paintShot();assert.doesNotMatch(node('shot').innerHTML,/UNCERTAIN_CORNERS/,'confirmed manual paper corners clear the detector warning');
  context.shot={...context.shot,autoScore:.6,cornersReliable:undefined};context.paintShot();assert.match(node('shot').innerHTML,/UNCERTAIN_CORNERS/,'the old score-only response still retains its warning');
  context.shot={...context.shot,autoScore:.95};context.paintShot();assert.doesNotMatch(node('shot').innerHTML,/UNCERTAIN_CORNERS/,'legacy responses without the new flag remain compatible');
  context.shot={...context.shot,a4WarpApplied:false,paperStatus:'aspect_mismatch'};context.paintShot();
  assert.match(node('shot').innerHTML,/not been converted to a scan/,'an unconfirmed proposal explicitly requires corner confirmation rather than pretending it is already a scan');
});

async function liveCameraFixture({ auto = true, capturePhoto } = {}) {
  const html = await fs.readFile(new URL('../sim/scan.html', import.meta.url), 'utf8');
  const script = html.match(/<script type="module">([\s\S]*?)<\/script>/)[1];
  const block = script.slice(script.indexOf('const LIVE_OK ='), script.indexOf('/* the deadline, on the server'));
  const timers = new Map(), photos = [], detections = [], calls = { stopped: 0, nativePhotos: 0, overlay: 0 }; let timerId = 0;
  const corners = [{ x: 80, y: 60 }, { x: 450, y: 70 }, { x: 70, y: 650 }, { x: 460, y: 640 }];
  const state = { detection: { corners, score: .9, method: 'page', edgeSupport: .95, clipped: false, autoCaptureEligible: true }, focus: 40, now:0 };
  const pixels = new Uint8ClampedArray(540 * 720 * 4), photo = new Blob(['original camera photo'], { type: 'image/jpeg' });
  const drawing = { drawImage() {}, getImageData: () => ({ data: pixels }), clearRect() {}, beginPath() {}, moveTo() {}, lineTo() {}, closePath() {}, fill() { calls.overlay++; }, stroke() {} };
  const canvas = () => ({ width: 0, height: 0, getContext: () => drawing, getBoundingClientRect: () => ({ width: 360, height: 640 }), toBlob: done => done(photo) });
  const overlayCanvas = canvas(), message = { textContent: '', classList: { toggle() {} } }, video = { videoWidth: 960, videoHeight: 1280, async play() {} };
  const overlay = { innerHTML: '', querySelector: selector => selector === 'video' ? video : selector === 'canvas' ? overlayCanvas : message, remove() {} };
  const track = { stop() { calls.stopped++; } }, stream = { getTracks: () => [track], getVideoTracks: () => [track] };
  const ImageCapture = class { async takePhoto() { calls.nativePhotos++; return capturePhoto ? capturePhoto() : photo; } };
  const labels = { lvAim: 'aim', lvPage: 'outline found', lvCandidate: 'confirm candidate after capture', lvHold: 'hold still', lvTake: 'taking', blurry: 'blurred', lvNoCam: 'no camera', lvAspect: 'not A4', lvPerspective: 'hold parallel' };
  const context = vm.createContext({ navigator: { mediaDevices: { getUserMedia: async () => stream } }, canProcess: () => true,
    localStorage: { getItem: () => auto ? '1' : '0', setItem() {} }, document: { createElement: tag => tag === 'div' ? overlay : canvas(), body: { append() {} } },
    window: { ImageCapture }, ImageCapture, AbortController, performance:{now:()=>state.now}, lang:'en', devicePixelRatio: 1, MONTHLY: false, SCAN_ACCENT: '#abc',
    t: () => labels, toast() {}, toGray: () => new Uint8Array(1), inspectDocumentPixels: () => ({ focus: state.focus }),
    detectDocumentQuad: async canvas => { detections.push({ width:canvas.width, height:canvas.height }); return state.pending ? await state.pending : state.detection; },
    warmDocumentDetector: async () => true,
    take: async (blob, live, _internal, options) => photos.push({ blob, live, options }),
    setTimeout: fn => { const id = ++timerId; timers.set(id, fn); return id; }, clearTimeout: id => timers.delete(id) });
  vm.runInContext(block + '\nglobalThis.openCamera = liveCamera;', context);
  await context.openCamera();
  const next = async (count = 1) => { for (let i = 0; i < count; i++) { const [id, fn] = timers.entries().next().value || []; if (!fn) break; timers.delete(id); await fn(); } };
  const click = async name => { overlay.onclick({ target: { closest: () => ({ dataset: { x: name }, classList: { toggle() {} } }) } }); await new Promise(done => setImmediate(done)); };
  return { state, photos, calls, timers, detections, next, click, message, photo };
}

test('markerless live preview automatically captures only a sharp validated outline held for eight frames', async () => {
  const live = await liveCameraFixture(); await live.next(6);
  assert.equal(live.photos.length, 0, 'seven frames are not yet enough for paper-edge capture');
  assert.ok(live.calls.overlay >= 7); assert.equal(live.message.textContent, 'hold still');
  await live.next(); assert.equal(live.photos.length, 1); assert.equal(live.photos[0].blob, live.photo); assert.equal(live.photos[0].live, true);
  assert.equal(live.calls.nativePhotos, 1); assert.equal(live.calls.stopped, 1); assert.equal(live.timers.size, 0);
  assert.ok(live.detections.every(size => size.width === 768 && size.height === 1024), 'live detection uses a bounded sharper preview rather than losing weak paper edges at 720 pixels');
});

test('high-confidence learned perspective uses three stable observations without an A4 frontality gate', async () => {
  const live=await liveCameraFixture();
  live.state.detection={...live.state.detection,method:'ml',paperStatus:'document',scanEligible:true};
  await live.next(2);assert.equal(live.photos.length,0);
  await live.next();assert.equal(live.photos.length,1);assert.equal(live.calls.nativePhotos,1);
});

test('closing a camera during asynchronous detection ignores its late outline and never resumes capture', async () => {
  const live=await liveCameraFixture();let resolve;
  live.state.pending=new Promise(done=>{resolve=done;});
  const next=live.next();await new Promise(done=>setImmediate(done));
  await live.click('close');resolve(live.state.detection);await next;
  assert.equal(live.photos.length,0);assert.equal(live.calls.stopped,1);assert.equal(live.timers.size,0);
});

test('uncertain or clipped paper outlines remain manual-shutter candidates rather than triggering automatic photos', async () => {
  for (const method of ['page', 'marker', 'frame']) {
    const live = await liveCameraFixture(); live.state.detection = { ...live.state.detection, method, score: .99, edgeSupport: .2, clipped: true, autoCaptureEligible: false };
    await live.next(12); assert.equal(live.photos.length, 0, 'a high geometry score alone cannot allow ' + method + ' capture');
    if (method !== 'frame') assert.equal(live.message.textContent, 'confirm candidate after capture');
    await live.click('shoot'); assert.equal(live.photos.length, 1, 'the shutter remains usable for manual review and corner correction');
  }
});

test('unconfirmed model proposals stay manual independently of a projected A4 classification', async () => {
  for (const [paperStatus, expected] of [['aspect_mismatch','confirm candidate after capture'],['perspective_uncertain','confirm candidate after capture']]) {
    const live=await liveCameraFixture();
    live.state.detection={...live.state.detection,paperStatus,autoCaptureEligible:false};
    await live.next(12);assert.equal(live.photos.length,0);assert.equal(live.message.textContent,expected);
    await live.click('shoot');assert.equal(live.photos.length,1,'original capture remains available for review');
  }
});

test('blur, moving corners and detector-method changes reset the live hold instead of accumulating old frames', async () => {
  const blurred = await liveCameraFixture(); blurred.state.focus = 10; await blurred.next(12);
  assert.equal(blurred.photos.length, 0); assert.equal(blurred.message.textContent, 'blurred');
  blurred.state.focus = 40; await blurred.next(7); assert.equal(blurred.photos.length, 0); await blurred.next(); assert.equal(blurred.photos.length, 1);
  const moving = await liveCameraFixture(), points = moving.state.detection.corners;
  for (let frame = 0; frame < 12; frame++) { const shift = frame % 2 ? 20 : -20; for (const point of points) point.x += shift; await moving.next(); }
  assert.equal(moving.photos.length, 0, 'history retains copies even when a detector reuses its corner objects'); await moving.click('close');
  const switched = await liveCameraFixture(); await switched.next(4); switched.state.detection = { ...switched.state.detection, method: 'marker' };
  await switched.next(5); assert.equal(switched.photos.length, 0, 'paper-edge frames cannot complete the marker hold'); await switched.next(); assert.equal(switched.photos.length, 1);
});

test('turning automatic capture off retains the shutter and toggling it back starts a fresh hold', async () => {
  const manual = await liveCameraFixture({ auto: false }); await manual.next(12); assert.equal(manual.photos.length, 0);
  await manual.click('shoot'); assert.equal(manual.photos.length, 1);
  const toggled = await liveCameraFixture(); await toggled.next(4); await toggled.click('auto'); await toggled.next(5); assert.equal(toggled.photos.length, 0);
  await toggled.click('auto'); await toggled.next(7); assert.equal(toggled.photos.length, 0); await toggled.next(); assert.equal(toggled.photos.length, 1);
});

test('closing a camera while a native photo is pending stops tracks and ignores its late result', async () => {
  let resolve; const pending = new Promise(done => resolve = done), live = await liveCameraFixture({ auto: false, capturePhoto: () => pending });
  await live.click('shoot'); assert.equal(live.calls.nativePhotos, 1); await live.click('close'); assert.equal(live.calls.stopped, 1);
  resolve(live.photo); await new Promise(done => setImmediate(done)); assert.equal(live.photos.length, 0); assert.equal(live.calls.stopped, 1); assert.equal(live.timers.size, 0);
});

test('a manual shutter retains any fresh accepted video frame without requiring the automatic hold',async()=>{
  const live=await liveCameraFixture({auto:false});
  live.state.detection={...live.state.detection,method:'ml',scanEligible:true,autoCaptureEligible:false};
  await live.next();await live.click('shoot');
  const options=live.photos[0].options;
  assert.equal(options.detectionHint,undefined,'native still photo always earns its own detection first');
  assert.equal(options.fallback.detectionHint.source,'same-video-frame');
  assert.equal(options.fallback.detectionHint.scanEligible,true);
  assert.ok(options.fallback.detectionHint.corners.every(p=>p.x>=0&&p.x<=1&&p.y>=0&&p.y<=1));
});

test('expired or delayed live detections never transfer stale corners to a new still photo',async()=>{
  const live=await liveCameraFixture({auto:false});let resolve;
  live.state.detection={...live.state.detection,method:'ml',scanEligible:true,autoCaptureEligible:false};
  live.state.pending=new Promise(done=>resolve=done);
  const next=live.next();await new Promise(done=>setImmediate(done));
  live.state.now=2000;resolve(live.state.detection);await next;
  await live.click('shoot');
  assert.equal(live.photos.length,1);assert.deepEqual(Object.keys(live.photos[0].options),[],'manual capture remains available but a 2-second-old sampled frame is not reused');
});

test('native camera failure may reuse the matching video frame but a CV proposal cannot supply a hint',async()=>{
  const live=await liveCameraFixture({auto:false,capturePhoto:async()=>{throw Error('native camera fixture');}});
  live.state.detection={...live.state.detection,method:'ml',scanEligible:true,autoCaptureEligible:false};
  await live.next();await live.click('shoot');
  assert.equal(live.photos[0].options.detectionHint.source,'same-video-frame');
  assert.equal(live.photos[0].options.fallback,undefined);
  const proposal=await liveCameraFixture({auto:false});proposal.state.detection={...proposal.state.detection,scanEligible:false,autoCaptureEligible:false};
  await proposal.next();await proposal.click('shoot');
  assert.deepEqual(Object.keys(proposal.photos[0].options),[],'a visible but unconfirmed rectangle never silently becomes an accepted scan');
});
