const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const root=path.resolve(__dirname,'..');let chromium,executable;
try{
 ({chromium}=require(process.env.HASLA_PLAYWRIGHT_PATH?path.resolve(root,process.env.HASLA_PLAYWRIGHT_PATH):path.join(root,'tmp/browser-qa/node_modules/playwright')));
 executable=process.env.CHROME_BIN||(process.platform==='win32'?'C:/Program Files/Google/Chrome/Application/chrome.exe':['/usr/bin/google-chrome','/usr/bin/chromium',chromium.executablePath()].find(p=>fs.existsSync(p)));
 if(!fs.existsSync(executable))chromium=null;
}catch{}
test('real browser recovers a failed model download and rectifies a matching captured frame without losing its outline',
 {skip:!chromium&&'Set HASLA_PLAYWRIGHT_PATH and CHROME_BIN',timeout:120000},async()=>{
 const server=http.createServer((req,res)=>{
  if(req.url==='/__engine_qa'){res.setHeader('Content-Type','text/html');return res.end('<!doctype html><title>Engine QA</title>');}
  const file=path.resolve(root,'.'+new URL(req.url,'http://localhost').pathname);
  if(!file.startsWith(root+path.sep)||!fs.existsSync(file)||fs.statSync(file).isDirectory()){res.writeHead(404);return res.end();}
  res.setHeader('Content-Type',/\.m?js$/.test(file)?'text/javascript':file.endsWith('.wasm')?'application/wasm':'application/octet-stream');
  fs.createReadStream(file).pipe(res);
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const origin='http://127.0.0.1:'+server.address().port,browser=await chromium.launch({headless:true,executablePath:executable});
 try{
  const context=await browser.newContext();let modelRequests=0;const external=[];
  await context.route('**/*',route=>{
   const url=route.request().url();if(!url.startsWith(origin+'/')){external.push(url);return route.abort();}
   if(url.endsWith('.onnx')&&++modelRequests===1)return route.fulfill({status:503,body:'temporary local fixture failure'});
   return route.continue();
  });
  try{
   const page=await context.newPage();await page.goto(origin+'/__engine_qa');
   const result=await page.evaluate(async()=>{
    const scanner=await import('/sim/labscan/scanner.js');
    const first=await scanner.warmDocumentDetector();
    const file=await(await fetch('/tests/fixtures/scanner-graph-photo.jpg')).blob(),scan=await scanner.processShot(file);
    const second=await scanner.warmDocumentDetector({retry:true});
    const control=new AbortController(),dialog=scanner.editCorners(scan.baseUrl,scan.corners,{signal:control.signal});
    while(!document.querySelector('dialog'))await new Promise(resolve=>setTimeout(resolve,0));
    control.abort();const cancelled=await dialog;
    return{first,second,warp:scan.warpApplied,method:scan.method,width:scan.width,cancelled,openDialogs:document.querySelectorAll('dialog').length};
   });
   assert.equal(result.first,false);assert.equal(result.second,true,'a new photo operation must recover in the same page');
   assert.equal(modelRequests,2);assert.equal(result.warp,true);assert.equal(result.method,'ml');assert.equal(result.width,1654);
   assert.equal(result.cancelled,null);assert.equal(result.openDialogs,0);assert.deepEqual(external,[]);
  }finally{await context.close();}
  const hintContext=await browser.newContext();let forbiddenModelCalls=0;
  await hintContext.route('**/*',route=>{if(route.request().url().endsWith('.onnx')){forbiddenModelCalls++;return route.abort();}return route.continue();});
  try{
   const page=await hintContext.newPage();await page.goto(origin+'/__engine_qa');
   const result=await page.evaluate(async()=>{
    const scanner=await import('/sim/labscan/scanner.js'),photo=await(await fetch('/tests/fixtures/scanner-graph-photo.jpg')).blob();
    const corners=[{x:170/900,y:125/1200},{x:675/900,y:210/1200},{x:110/900,y:1040/1200},{x:730/900,y:970/1200}];
    const scan=await scanner.processShot(photo,{detectionHint:{source:'same-video-frame',scanEligible:true,method:'ml',score:.9,corners}});
    const bitmap=await createImageBitmap(scan.blob),canvas=document.createElement('canvas');canvas.width=bitmap.width;canvas.height=bitmap.height;canvas.getContext('2d').drawImage(bitmap,0,0);bitmap.close();
    const data=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;let blue=0,red=0;for(let i=0;i<data.length;i+=4){if(data[i+2]>data[i]*1.4&&data[i+2]>data[i+1]*1.15)blue++;if(data[i]>data[i+1]*1.4&&data[i]>data[i+2]*1.3)red++;}
    return{warp:scan.warpApplied,width:scan.width,height:scan.height,blue,red};
   });
   assert.equal(result.warp,true);assert.equal(result.width,1654);assert.ok(result.height>2200);
   assert.ok(result.blue>2000&&result.red>500,'colour-corrected graph and direction marks survive');
   assert.equal(forbiddenModelCalls,0,'same-frame accepted corners must not be discarded for an unnecessary re-detection');
  }finally{await hintContext.close();}
  const blockedWorker=await browser.newContext();
  await blockedWorker.route('**/document-worker.mjs*',route=>route.abort());
  try{
   const page=await blockedWorker.newPage();await page.goto(origin+'/__engine_qa');
   const result=await page.evaluate(async()=>{
    const scanner=await import('/sim/labscan/scanner.js'),bitmap=await createImageBitmap(await(await fetch('/tests/fixtures/scanner-graph-photo.jpg')).blob());
    const canvas=document.createElement('canvas');canvas.width=bitmap.width;canvas.height=bitmap.height;canvas.getContext('2d').drawImage(bitmap,0,0);bitmap.close();
    const preview=await scanner.detectDocumentQuad(canvas,{preview:true}),still=await scanner.detectDocumentQuad(canvas);
    return{preview,still};
   });
   assert.equal(result.preview.engine,'manual-fallback');assert.notEqual(result.preview.method,'frame');assert.equal(result.preview.corners.length,4);
   // without the worker the classical outer quad still makes the scan (flagged for a corner check); only automatic capture waits for verified edges
   assert.equal(result.preview.scanEligible,true);assert.equal(result.preview.verified,false);assert.equal(result.preview.autoCaptureEligible,false);
   assert.equal(result.still.scanEligible,true);assert.equal(result.still.verified,false);assert.equal(result.still.autoCaptureEligible,false);
   result.preview.corners.forEach((p,i)=>assert.ok(Math.hypot(p.x-result.still.corners[i].x,p.y-result.still.corners[i].y)<30,'preview proposes the same physical outer corners at bounded resolution'));
  }finally{await blockedWorker.close();}
 }finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
});
