// Actual Chrome + actual vendored ONNX model. No API keys, remote images or provider calls.
const test = require('node:test'), assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path'), http = require('node:http');
const root = path.resolve(__dirname, '..');
let chromium, executable;
try {
  ({chromium} = require(process.env.HASLA_PLAYWRIGHT_PATH ? path.resolve(root,process.env.HASLA_PLAYWRIGHT_PATH) : path.join(root, 'tmp/browser-qa/node_modules/playwright')));
  executable = process.env.CHROME_BIN || (process.platform === 'win32' ? 'C:/Program Files/Google/Chrome/Application/chrome.exe' : ['/usr/bin/google-chrome','/usr/bin/chromium','/usr/bin/chromium-browser',chromium.executablePath()].find(file=>fs.existsSync(file)));
  if (!fs.existsSync(executable)) chromium = null;
} catch {}

test('real local document model scans perspective graphs in colour, stays off the API and reuses verified asset cache',
  { skip: !chromium && 'Set HASLA_PLAYWRIGHT_PATH and CHROME_BIN to run the local browser benchmark', timeout: 120000 }, async () => {
  const mime = {'.mjs':'text/javascript','.js':'text/javascript','.wasm':'application/wasm','.jpg':'image/jpeg','.json':'application/json'};
  const server = http.createServer((req, res) => {
    if (req.url === '/__scanner_qa.html') { res.writeHead(200, {'Content-Type':'text/html'}); return res.end('<!doctype html><title>Local scanner QA</title>'); }
    let target; try { target = path.resolve(root, '.' + decodeURIComponent(new URL(req.url, 'http://localhost').pathname)); } catch { res.writeHead(400); return res.end(); }
    if (!target.startsWith(root + path.sep) || !fs.existsSync(target) || fs.statSync(target).isDirectory()) { res.writeHead(404); return res.end(); }
    res.writeHead(200, {'Content-Type':mime[path.extname(target)] || 'application/octet-stream','Content-Length':fs.statSync(target).size}); fs.createReadStream(target).pipe(res);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = 'http://127.0.0.1:' + server.address().port, browser = await chromium.launch({headless:true,executablePath:executable});
  const context = await browser.newContext(), requests = [], outside = [], errors = [];
  await context.route('**/*', route => {
    const url = route.request().url(); requests.push(url);
    if (!url.startsWith(origin + '/')) { outside.push(url); return route.abort(); }
    return route.continue();
  });
  try {
    const page = await context.newPage(); page.on('pageerror', error => errors.push(error.message));
    await page.goto(origin + '/__scanner_qa.html');
    const result = await page.evaluate(async () => {
      const scanner = await import('/sim/labscan/scanner.js'), file = await (await fetch('/tests/fixtures/scanner-graph-photo.jpg')).blob();
      let ticks = 0, gap = 0, last = performance.now(); const timer = setInterval(() => { const now = performance.now(); gap = Math.max(gap, now-last); last=now; ticks++; }, 10);
      const started = performance.now(), scan = await scanner.processShot(file, {pageFormat:'a4'}); clearInterval(timer);
      const bitmap = await createImageBitmap(scan.blob), canvas = document.createElement('canvas'); canvas.width=bitmap.width;canvas.height=bitmap.height;const ctx=canvas.getContext('2d');ctx.drawImage(bitmap,0,0);bitmap.close();
      const data=ctx.getImageData(0,0,canvas.width,canvas.height).data;let blue=0,red=0;
      for(let i=0;i<data.length;i+=4){if(data[i+2]>data[i]*1.4&&data[i+2]>data[i+1]*1.15&&data[i+2]>80)blue++;if(data[i]>data[i+1]*1.4&&data[i]>data[i+2]*1.3&&data[i]>80)red++;}
      const url = await new Promise(resolve=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.readAsDataURL(scan.blob);});
      const cacheUrls=[];for(const name of await caches.keys())if(name.startsWith('haslalab-document-assets-'))for(const request of await(await caches.open(name)).keys())cacheUrls.push(request.url);
      return {corners:scan.corners,method:scan.method,warpApplied:scan.warpApplied,outputFormat:scan.outputFormat,width:scan.width,height:scan.height,blue,red,ticks,maxGap:gap,elapsed:performance.now()-started,url,cacheUrls};
    });
    const truth = JSON.parse(fs.readFileSync(path.join(root, 'tests/fixtures/scanner-graph-photo.json'))).corners;
    const cornerError = Math.max(...truth.map((p,i)=>Math.hypot(p.x-result.corners[i].x,p.y-result.corners[i].y)));
    assert.equal(result.method,'ml');assert.equal(result.warpApplied,true);assert.equal(result.outputFormat,'a4');
    assert.deepEqual([result.width,result.height],[1654,2339]);assert.ok(cornerError<15,'learned/refined corners follow the real outside edge');
    assert.ok(result.blue>2000&&result.red>500,'blue curve/arrow and red measurements survive colour scanning');
    assert.ok(result.ticks>10,'the main thread continues while the model and warp run');
    assert.equal(result.cacheUrls.length,2);assert.ok(result.cacheUrls.every(url=>url.includes('/vendor/')),'only public static assets are cached');
    assert.deepEqual(outside,[]);assert.deepEqual(errors,[]);
    const destination=path.join(root,'tmp/scanner-ml-qa');fs.mkdirSync(destination,{recursive:true});fs.writeFileSync(path.join(destination,'graph-scan.jpg'),Buffer.from(result.url.split(',')[1],'base64'));
    const firstAssets=requests.filter(url=>/\.(?:onnx|wasm)$/.test(url)).length;assert.equal(firstAssets,2);
    await page.reload();await page.evaluate(async()=>{const {getDocumentDetector}=await import('/sim/labscan/document-detector.mjs');await getDocumentDetector().warm();});
    assert.equal(requests.filter(url=>/\.(?:onnx|wasm)$/.test(url)).length,firstAssets,'reloading reuses verified model and WASM bytes without another download');
    const automatic=await page.evaluate(async()=>{
      const scanner=await import('/sim/labscan/scanner.js'),file=await(await fetch('/tests/fixtures/scanner-graph-photo.jpg')).blob();
      const scan=await scanner.processShot(file);
      return {warp:scan.warpApplied,a4:scan.a4WarpApplied,format:scan.outputFormat,width:scan.width,height:scan.height};
    });
    assert.equal(automatic.warp,true);assert.equal(automatic.a4,true);assert.equal(automatic.format,'a4');
    assert.deepEqual([automatic.width,automatic.height],[1654,2339],'by default the page is rectified to A4 at 200dpi, as the first exam scans were');
    await page.evaluate(async()=>{const scanner=await import('/sim/labscan/scanner.js'),canvas=document.createElement('canvas');canvas.width=400;canvas.height=600;canvas.getContext('2d').fillStyle='#ddd';canvas.getContext('2d').fillRect(0,0,400,600);const d=await scanner.detectDocumentQuad(canvas);if(d.scanEligible||d.autoCaptureEligible)throw Error('blank background must stay manual');});
    const unavailable=await browser.newContext();
    try {
      await unavailable.route('**/*',route=>{
        const url=route.request().url();
        if(!url.startsWith(origin+'/')){outside.push(url);return route.abort();}
        return /\.onnx$/.test(url)?route.abort():route.continue();
      });
      const fallbackPage=await unavailable.newPage();await fallbackPage.goto(origin+'/__scanner_qa.html');
      const fallback=await fallbackPage.evaluate(async()=>{
        const scanner=await import('/sim/labscan/scanner.js'),file=await(await fetch('/tests/fixtures/scanner-graph-photo.jpg')).blob();
        const scan=await scanner.processShot(file);
        return {warp:scan.warpApplied,a4:scan.a4WarpApplied,format:scan.outputFormat,width:scan.width,height:scan.height,type:scan.blob.type};
      });
      assert.deepEqual(fallback,{warp:true,a4:true,format:'a4',width:1654,height:2339,type:'image/jpeg'},'without the model the classical page finder still makes an A4 scan, flagged for a corner check');
      await fallbackPage.route('**/sim/labscan/document-worker.mjs*',route=>route.abort());
      await fallbackPage.reload();
      const manual=await fallbackPage.evaluate(async corners=>{
        const scanner=await import('/sim/labscan/scanner.js'),file=await(await fetch('/tests/fixtures/scanner-graph-photo.jpg')).blob();
        const scan=await scanner.processShot(file,{corners,pageFormat:'a4'});
        return {warp:scan.warpApplied,a4:scan.a4WarpApplied,width:scan.width,height:scan.height};
      },truth);
      assert.deepEqual(manual,{warp:true,a4:true,width:1654,height:2339},'explicit manual correction still works if the worker cannot start');
    } finally { await unavailable.close(); }
    assert.deepEqual(outside,[]);
    delete result.url;fs.writeFileSync(path.join(destination,'benchmark.json'),JSON.stringify({...result,cornerError,firstAssetBytes:16014019,externalRequests:outside.length},null,2));
    console.log('Local ML scanner: '+cornerError.toFixed(2)+'px corner error; '+result.blue+' blue / '+result.red+' red pixels; '+result.elapsed.toFixed(0)+'ms first scan; max UI timer gap '+result.maxGap.toFixed(0)+'ms');
  } finally { await context.close();await browser.close();await new Promise(resolve=>server.close(resolve)); }
});
