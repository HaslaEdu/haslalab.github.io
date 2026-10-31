// Actual phone scanner UI, MediaStream/video/canvas, ML worker and image warp.
// Only the camera hardware and upload-session response are deterministic fixtures.
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const root=path.resolve(__dirname,'..');
let chromium,executable;
try{
 ({chromium}=require(process.env.HASLA_PLAYWRIGHT_PATH?path.resolve(root,process.env.HASLA_PLAYWRIGHT_PATH):path.join(root,'tmp/browser-qa/node_modules/playwright')));
 executable=process.env.CHROME_BIN||(process.platform==='win32'?'C:/Program Files/Google/Chrome/Application/chrome.exe':['/usr/bin/google-chrome','/usr/bin/chromium',chromium.executablePath()].find(file=>fs.existsSync(file)));
 if(!fs.existsSync(executable))chromium=null;
}catch{}
test('actual live camera keeps accepted video geometry separate from native still photos and creates a clean scan that keeps colours',
 {skip:!chromium&&'Set HASLA_PLAYWRIGHT_PATH and CHROME_BIN for camera UI integration',timeout:120000},async()=>{
 const server=http.createServer((request,response)=>{
  const target=path.resolve(root,'.'+new URL(request.url,'http://localhost').pathname);
  if(!target.startsWith(root+path.sep)||!fs.existsSync(target)||fs.statSync(target).isDirectory()){response.writeHead(404);return response.end();}
  const mime={'.html':'text/html','.mjs':'text/javascript','.js':'text/javascript','.wasm':'application/wasm','.jpg':'image/jpeg'};
  let body=fs.readFileSync(target);
  if(target===path.join(root,'sim/scan.html')){
   // Expose state and record the real engine invocations only in this local test
   // response. Production source contains neither instrumentation nor test grants.
   body=body.toString().replace('processShot, reprocess','processShot as engineProcessShot, reprocess')
    .replace('const COMMUNITY_API =','const processShot=async(file,options)=>{window.__scanCalls.push({mode:options.mode,hint:options.detectionHint||null});return engineProcessShot(file,options);};\nconst COMMUNITY_API =')
    .replace('if (!KEY) $("app")','window.__scanCalls=[];window.__scan={getShot:()=>shot};\nif (!KEY) $("app")');
  }
  response.writeHead(200,{'Content-Type':mime[path.extname(target)]||'application/octet-stream'});response.end(body);
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const origin='http://127.0.0.1:'+server.address().port;
 let browser;
 try{
  browser=await chromium.launch({headless:true,executablePath:executable});
  const context=await browser.newContext({viewport:{width:412,height:915}}),outside=[],errors=[];
  await context.route('**/*',route=>{
   const url=route.request().url();
   if(url.includes('/api/lab/up'))return route.fulfill({json:{comp:'ipho',year:2025,tasks:['T1'],open:true,status:'scanning',now:Date.now()/1000,scan_until:Date.now()/1000+3600,pages:[]}});
   if(!url.startsWith(origin+'/')){outside.push(url);return route.abort();}
   return route.continue();
  });
  await context.addInitScript(()=>{
   localStorage.setItem('hlScanAuto','0');
   window.__nativeMode='blank';window.__stopped=0;
   Object.defineProperty(navigator.mediaDevices,'getUserMedia',{value:async()=>{
    const file=await(await fetch('/tests/fixtures/scanner-graph-photo.jpg')).blob(),bitmap=await createImageBitmap(file),canvas=document.createElement('canvas');
    canvas.width=bitmap.width;canvas.height=bitmap.height;canvas.getContext('2d').drawImage(bitmap,0,0);bitmap.close();
    const stream=canvas.captureStream(15);
    for(const track of stream.getTracks()){const stop=track.stop.bind(track);track.stop=()=>{window.__stopped++;stop();};}
    window.__camera={canvas,file};return stream;
   }});
   window.ImageCapture=class{async takePhoto(){
    if(window.__nativeMode==='original')return window.__camera.file;
    if(window.__nativeMode==='throw')throw Error('Camera hardware fixture');
    if(window.__nativeMode==='weak'){
     // a native still in which a page-like quad is found but not verified (Samsung's different crop and exposure)
     const canvas=document.createElement('canvas');canvas.width=1600;canvas.height=1200;const g=canvas.getContext('2d');
     g.fillStyle='#8a8580';g.fillRect(0,0,1600,1200);g.filter='blur(14px)';g.fillStyle='#a19c96';g.fillRect(420,160,760,980);g.filter='none';
     return new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',.95));
    }
    // A native still can change field of view/exposure. In this fixture it no
    // longer contains a document; live coordinates MUST NOT be applied to it.
    const canvas=document.createElement('canvas');canvas.width=1600;canvas.height=900;
    canvas.getContext('2d').fillStyle='#777';canvas.getContext('2d').fillRect(0,0,1600,900);
    return new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',.95));
   }};
  });
  const page=await context.newPage();page.on('pageerror',error=>errors.push(error.message));
  await page.goto(origin+'/sim/scan.html#c=local-camera-fixture&l=en');
  async function openAndHold(){
   await page.locator('#live').click();
   await page.waitForFunction(()=>document.querySelector('.lv .msg')?.textContent==='Hold still…',{timeout:45000});
   await page.waitForTimeout(1800);
  }
  async function shoot(){
   await page.locator('[data-x="shoot"]').click();
   await page.waitForFunction(()=>window.__scan.getShot()&&!window.__scan.getShot().busy,{timeout:45000});
   return page.evaluate(()=>{const s=window.__scan.getShot();return{warp:s.warpApplied,width:s.width,height:s.height,method:s.method,fallback:s.liveFrameFallback===true,baseW:s.baseW,baseH:s.baseH,fileType:s.file.type,captureMatchesFile:s.captureFile===s.file,calls:window.__scanCalls,stopped:window.__stopped};});
  }
  await openAndHold();const fallback=await shoot();
  assert.equal(fallback.warp,true);assert.equal(fallback.fallback,true);assert.equal(fallback.method,'ml');
  assert.equal(fallback.width,1654);assert.ok(fallback.height>2200&&fallback.height<2700);
  assert.deepEqual([fallback.baseW,fallback.baseH],[900,1200],'fallback uses the same portrait video frame, not the different native crop');
  assert.equal(fallback.calls.length,2);assert.equal(fallback.calls[0].hint,null);
  assert.equal(fallback.calls[1].hint.source,'same-video-frame');assert.equal(fallback.calls[1].mode,'clean');
  assert.equal(fallback.stopped,1);assert.equal(await page.locator('.lv').count(),0);
  assert.equal(fallback.captureMatchesFile,true,'monthly original evidence uses the matching video frame, not the failed native still');
  const colours=await page.evaluate(async()=>{
   const bitmap=await createImageBitmap(window.__scan.getShot().blob),canvas=document.createElement('canvas');canvas.width=bitmap.width;canvas.height=bitmap.height;canvas.getContext('2d').drawImage(bitmap,0,0);bitmap.close();
   const pixels=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;let blue=0,red=0;
   for(let i=0;i<pixels.length;i+=4){if(pixels[i+2]>pixels[i]*1.4&&pixels[i+2]>pixels[i+1]*1.15&&pixels[i+2]>80)blue++;if(pixels[i]>pixels[i+1]*1.4&&pixels[i]>pixels[i+2]*1.3&&pixels[i]>80)red++;}
   return{blue,red};
  });
  assert.ok(colours.blue>2000&&colours.red>500,'the scan retains the drawn direction arrow and red graph points');
  await page.evaluate(()=>{window.__nativeMode='original';window.__scanCalls=[];});
  await page.locator('#again').click();
  await page.waitForFunction(()=>document.querySelector('.lv .msg')?.textContent==='Hold still…',{timeout:45000});
  await page.waitForTimeout(1800);
  const native=await shoot();
  assert.equal(native.warp,true);assert.equal(native.fallback,false,'a valid native high-resolution photo remains preferred');
  assert.equal(native.calls.length,1);assert.equal(native.calls[0].hint,null,'live coordinates never leak into native photo detection');
  assert.equal(native.captureMatchesFile,true);
  await page.evaluate(()=>{window.__nativeMode='weak';window.__scanCalls=[];});
  await page.locator('#again').click();
  await page.waitForFunction(()=>document.querySelector('.lv .msg')?.textContent==='Hold still…',{timeout:45000});
  await page.waitForTimeout(1800);
  const weak=await shoot();
  assert.equal(weak.fallback,true,'an uncertain quad in the native still gives way to the live frame whose page was verified');
  assert.equal(weak.warp,true);assert.deepEqual([weak.baseW,weak.baseH],[900,1200]);assert.equal(weak.calls.length,2);
  await page.evaluate(()=>{window.__scanCalls=[];});
  await page.locator('#cam').setInputFiles({name:'phone-camera.jpg',mimeType:'image/jpeg',buffer:fs.readFileSync(path.join(root,'tests/fixtures/scanner-graph-photo.jpg'))});
  await page.waitForFunction(()=>window.__scan.getShot()?.file.name==='phone-camera.jpg'&&!window.__scan.getShot().busy,{timeout:45000});
  const cameraFile=await page.evaluate(()=>{const s=window.__scan.getShot();return{warp:s.warpApplied,width:s.width,height:s.height,calls:window.__scanCalls,captureMatchesFile:s.captureFile===s.file};});
  assert.equal(cameraFile.warp,true);assert.equal(cameraFile.width,1654);assert.equal(cameraFile.captureMatchesFile,true);
  assert.equal(cameraFile.calls.length,1);assert.equal(cameraFile.calls[0].mode,'clean');assert.equal(cameraFile.calls[0].hint,null);
  assert.deepEqual(errors,[]);assert.deepEqual(outside,[]);
  console.log(JSON.stringify({fallback:{width:fallback.width,height:fallback.height,method:fallback.method},native:{width:native.width,height:native.height},colours,externalRequests:outside.length}));
 }finally{await browser?.close();await new Promise(resolve=>server.close(resolve));}
});
