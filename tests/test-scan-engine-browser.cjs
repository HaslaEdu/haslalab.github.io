const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const root=path.resolve(__dirname,'..');let chromium,executable;
try{
 ({chromium}=require(process.env.HASLA_PLAYWRIGHT_PATH?path.resolve(root,process.env.HASLA_PLAYWRIGHT_PATH):path.join(root,'tmp/browser-qa/node_modules/playwright')));
 executable=process.env.CHROME_BIN||(process.platform==='win32'?'C:/Program Files/Google/Chrome/Application/chrome.exe':['/usr/bin/google-chrome','/usr/bin/chromium',chromium.executablePath()].find(p=>fs.existsSync(p)));
 if(!fs.existsSync(executable))chromium=null;
}catch{}
test('real browser finds the page in a photo on the device, with a self-hosted corner model and no API request, and reuses a matching live frame',
 {skip:!chromium&&'Set HASLA_PLAYWRIGHT_PATH and CHROME_BIN',timeout:120000},async()=>{
 const server=http.createServer((req,res)=>{
  if(req.url==='/__engine_qa'){res.setHeader('Content-Type','text/html');return res.end('<!doctype html><title>Engine QA</title>');}
  const file=path.resolve(root,'.'+new URL(req.url,'http://localhost').pathname);
  if(!file.startsWith(root+path.sep)||!fs.existsSync(file)||fs.statSync(file).isDirectory()){res.writeHead(404);return res.end();}
  res.setHeader('Content-Type',/\.m?js$/.test(file)?'text/javascript':'application/octet-stream');
  fs.createReadStream(file).pipe(res);
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const origin='http://127.0.0.1:'+server.address().port,browser=await chromium.launch({headless:true,executablePath:executable});
 /* the fixture photo's sheet, measured by hand on its 900×1200 pixels */
 const truth=[{x:170,y:125},{x:675,y:210},{x:110,y:1040},{x:730,y:970}];
 try{
  const context=await browser.newContext();const requests=[];
  await context.route('**/*',route=>{const url=route.request().url();if(!url.startsWith(origin+'/'))return route.abort();requests.push(new URL(url).pathname);return route.continue();});
  try{
   const page=await context.newPage();await page.goto(origin+'/__engine_qa');
   const result=await page.evaluate(async()=>{
    const scanner=await import('/sim/labscan/scanner.js');
    const warm=await scanner.warmDocumentDetector();
    const file=await(await fetch('/tests/fixtures/scanner-graph-photo.jpg')).blob(),started=performance.now(),scan=await scanner.processShot(file),ms=performance.now()-started;
    const control=new AbortController(),dialog=scanner.editCorners(scan.baseUrl,scan.corners,{signal:control.signal});
    while(!document.querySelector('dialog'))await new Promise(resolve=>setTimeout(resolve,0));
    control.abort();const cancelled=await dialog;
    return{warm,warp:scan.warpApplied,method:scan.method,reliable:scan.cornersReliable,width:scan.width,ms,corners:scan.corners.map(p=>({x:p.x*900/scan.baseW,y:p.y*1200/scan.baseH})),cancelled,openDialogs:document.querySelectorAll('dialog').length};
   });
   assert.equal(result.warm,true);assert.equal(result.warp,true);assert.equal(result.method,'page');assert.equal(result.width,1654);
   result.corners.forEach((p,i)=>assert.ok(Math.hypot(p.x-truth[i].x,p.y-truth[i].y)<18,`corner ${i} within 1.2% of the photo: ${JSON.stringify(p)}`));
   assert.equal(result.cancelled,null);assert.equal(result.openDialogs,0);
   assert.ok(!requests.some(p=>/^\/api\//.test(p)),'no API request: '+requests.join(' '));
   assert.ok(requests.every(p=>!/\.(ort|wasm|onnx)$/.test(p)||p.startsWith('/vendor/scanic-ml-0.2.0/')),'the corner model and its runtime come from this site only: '+requests.join(' '));
   assert.ok(requests.includes('/vendor/scanic-ml-0.2.0/doccornernet_lean.ort'),'the learned corner model is loaded (self-hosted)');
  }finally{await context.close();}
  const hintContext=await browser.newContext();
  try{
   const page=await hintContext.newPage();await page.goto(origin+'/__engine_qa');
   const result=await page.evaluate(async()=>{
    const scanner=await import('/sim/labscan/scanner.js'),photo=await(await fetch('/tests/fixtures/scanner-graph-photo.jpg')).blob();
    const corners=[{x:170/900,y:125/1200},{x:675/900,y:210/1200},{x:110/900,y:1040/1200},{x:730/900,y:970/1200}];
    const scan=await scanner.processShot(photo,{detectionHint:{source:'same-video-frame',scanEligible:true,method:'page',score:.9,corners}});
    const bitmap=await createImageBitmap(scan.blob),canvas=document.createElement('canvas');canvas.width=bitmap.width;canvas.height=bitmap.height;canvas.getContext('2d').drawImage(bitmap,0,0);bitmap.close();
    const data=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;let blue=0,red=0;for(let i=0;i<data.length;i+=4){if(data[i+2]>data[i]*1.4&&data[i+2]>data[i+1]*1.15)blue++;if(data[i]>data[i+1]*1.4&&data[i]>data[i+2]*1.3)red++;}
    return{warp:scan.warpApplied,width:scan.width,height:scan.height,blue,red,method:scan.method};
   });
   assert.equal(result.warp,true);assert.equal(result.width,1654);assert.ok(result.height>2200);assert.equal(result.method,'page');
   assert.ok(result.blue>2000&&result.red>500,'colour-corrected graph and direction marks survive');
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
   assert.equal(result.preview.engine,'main-thread');assert.equal(result.preview.method,'page');assert.equal(result.preview.corners.length,4);
   assert.equal(result.preview.scanEligible,true);assert.equal(result.still.scanEligible,true);
   result.still.corners.forEach((p,i)=>assert.ok(Math.hypot(p.x-truth[i].x,p.y-truth[i].y)<18,'without the worker the same page is found'));
  }finally{await blockedWorker.close();}
 }finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
});
