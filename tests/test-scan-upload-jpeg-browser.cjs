// node --test tests/test-scan-upload-jpeg-browser.cjs  (HASLA_PLAYWRIGHT_PATH, CHROME_BIN as for the other browser tests,
// or a global `playwright`)
// A PNG or WebP chosen in the phone scanner reaches the server as JPEG: the Worker's strips, zoom crops and size fitting
// decode JPEG only. The real scan page, scanner engine and canvas run; only the upload API is a local fixture.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const root=path.resolve(__dirname,'..');let chromium,executable;
for(const from of [process.env.HASLA_PLAYWRIGHT_PATH&&path.resolve(root,process.env.HASLA_PLAYWRIGHT_PATH),path.join(root,'tmp/browser-qa/node_modules/playwright'),'playwright'].filter(Boolean)){
 try{({chromium}=require(from));break;}catch{}
}
try{
 executable=process.env.CHROME_BIN||(process.platform==='win32'?'C:/Program Files/Google/Chrome/Application/chrome.exe':['/usr/bin/google-chrome','/usr/bin/chromium',chromium.executablePath()].find(p=>fs.existsSync(p)));
 if(!executable||!fs.existsSync(executable))chromium=null;
}catch{chromium=null;}

function serve(){
 return http.createServer((req,res)=>{
  const u=new URL(req.url,'http://localhost');
  if(u.pathname==='/__jpeg_qa'){res.setHeader('Content-Type','text/html');return res.end('<!doctype html><title>JPEG upload QA</title>');}
  const file=path.resolve(root,'.'+u.pathname);
  if(!file.startsWith(root+path.sep)||!fs.existsSync(file)||fs.statSync(file).isDirectory()){res.writeHead(404);return res.end();}
  let body=fs.readFileSync(file);
  if(file===path.join(root,'sim/scan.html')){
   // test-only instrumentation in this response: a page whose straightening fails (the scanner then sends the chosen
   // file itself), and access to the shot. The production page has neither.
   body=body.toString().replace('processShot, reprocess','processShot as engineProcessShot, reprocess')
    .replace('const COMMUNITY_API =','const processShot=async(file,options)=>{if(window.__failScan)throw{code:"fixture_failed"};return engineProcessShot(file,options);};\nconst COMMUNITY_API =')
    .replace('if (!KEY) $("app")','window.__scan={getShot:()=>shot};\nif (!KEY) $("app")');
  }
  res.setHeader('Content-Type',/\.html$/.test(file)?'text/html':/\.m?js$/.test(file)?'text/javascript':file.endsWith('.wasm')?'application/wasm':'application/octet-stream');
  res.end(body);
 });
}

test('a PNG or WebP chosen in the exam and monthly scanners is uploaded as image/jpeg, flattened onto white',
 {skip:!chromium&&'Set HASLA_PLAYWRIGHT_PATH and CHROME_BIN, or install playwright',timeout:180000},async()=>{
 const server=serve();await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const origin='http://127.0.0.1:'+server.address().port,browser=await chromium.launch({headless:true,executablePath:executable});
 try{
  const context=await browser.newContext({viewport:{width:412,height:915}}),uploads=[],outside=[],errors=[];
  const info=monthly=>({...(monthly?{title:'Monthly fixture'}:{comp:'ipho',year:2025}),tasks:[monthly?'1':'T1'],open:true,status:'scanning',now:Date.now()/1000,scan_until:Date.now()/1000+3600,pages:[]});
  await context.route('**/*',route=>{
   const request=route.request(),url=new URL(request.url());
   const up=/\/api\/(lab|monthly)\/up(?:\/pages)?$/.exec(url.pathname);
   if(up){
    if(request.method()==='GET')return route.fulfill({json:info(up[1]==='monthly')});
    uploads.push({path:url.pathname,method:request.method(),type:request.headers()['content-type'],body:request.postDataBuffer()});
    return route.fulfill({json:{id:uploads.length,no:uploads.length,task:url.searchParams.get('task'),kind:'answer',ocr_status:'queued'}});
   }
   if(!request.url().startsWith(origin+'/')){outside.push(request.url());return route.abort();}
   return route.continue();
  });
  await context.addInitScript(()=>{try{localStorage.setItem('hlScanAuto','0');}catch{}});
  const page=await context.newPage();page.on('pageerror',error=>errors.push(error.message));
  await page.goto(origin+'/__jpeg_qa');
  // a written page whose top band is transparent, as a PNG and as a WebP
  const files=await page.evaluate(async()=>{
   const c=document.createElement('canvas');c.width=1240;c.height=1754;const g=c.getContext('2d');
   g.fillStyle='#f4f2ee';g.fillRect(0,300,c.width,c.height-300);g.fillStyle='#1b1b2a';g.font='30px serif';
   for(let y=380;y<c.height-60;y+=48)g.fillText('v = 3.2 × 10^4 m/s,  θ = 37°,  a_n = 1/n^2',70,y);
   const b64=async type=>{const blob=await new Promise(r=>c.toBlob(r,type,.9));const bytes=new Uint8Array(await blob.arrayBuffer());let s='';for(const b of bytes)s+=String.fromCharCode(b);return{type:blob.type,data:btoa(s)};};
   return{png:await b64('image/png'),webp:await b64('image/webp')};
  });
  assert.equal(files.png.type,'image/png');assert.equal(files.webp.type,'image/webp');
  const decode=body=>page.evaluate(async data=>{
   const bytes=Uint8Array.from(atob(data),ch=>ch.charCodeAt(0)),bmp=await createImageBitmap(new Blob([bytes],{type:'image/jpeg'}));
   const c=document.createElement('canvas');c.width=bmp.width;c.height=bmp.height;const g=c.getContext('2d');g.drawImage(bmp,0,0);
   const top=g.getImageData(Math.floor(bmp.width/2),Math.floor(bmp.height*.05),1,1).data;return{width:bmp.width,height:bmp.height,top:[...top]};
  },body.toString('base64'));
  const isJpeg=bytes=>bytes[0]===0xff&&bytes[1]===0xd8&&bytes[2]===0xff;
  const choose=async(name,file)=>{
   await page.locator('#gal').setInputFiles({name,mimeType:file.type,buffer:Buffer.from(file.data,'base64')});
   await page.waitForFunction(n=>window.__scan.getShot()?.file?.name===n&&!window.__scan.getShot().busy,name,{timeout:60000});
   const before=uploads.length;await page.locator('#send').click();
   await page.waitForFunction(()=>!window.__scan.getShot(),null,{timeout:60000});
   assert.equal(uploads.length,before+1);return uploads.at(-1);
  };

  // the exam scanner: straightening fails, so the chosen file itself is what is sent
  await page.goto(origin+'/sim/scan.html#c=local-jpeg-fixture&l=en');await page.locator('#gal').waitFor({state:'attached'});
  await page.evaluate(()=>{window.__failScan=true;});
  for(const [name,file] of [['screenshot.png',files.png],['photo.webp',files.webp]]){
   const sent=await choose(name,file),shown=await decode(sent.body);
   assert.equal(sent.method,'PUT');assert.match(sent.path,/\/api\/lab\/up\/pages$/);
   assert.equal(sent.type,'image/jpeg',name+' is uploaded as image/jpeg');assert.ok(isJpeg(sent.body),name+' bytes are a JPEG');
   assert.deepEqual([shown.width,shown.height],[1240,1754],'converted at its own size');
   assert.ok(shown.top.slice(0,3).every(v=>v>=245),`${name}: the transparent band is white, not black (${shown.top})`);
  }

  // the monthly scanner: the straightened scan and the original photo (the chosen PNG) both go up as JPEG
  await page.goto(origin+'/sim/scan.html?monthly=1#c=local-jpeg-fixture&l=en');await page.locator('#gal').waitFor({state:'attached'});
  const sent=await choose('monthly.png',files.png);
  assert.equal(sent.method,'POST');assert.match(sent.path,/\/api\/monthly\/up\/pages$/);
  const form=await new Response(sent.body,{headers:{'Content-Type':sent.type}}).formData();
  for(const field of ['image','original_image']){
   const part=form.get(field),bytes=new Uint8Array(await part.arrayBuffer());
   assert.equal(part.type,'image/jpeg',field+' is image/jpeg');assert.match(part.name,/\.jpg$/);assert.ok(isJpeg(bytes),field+' bytes are a JPEG');
  }
  const original=await decode(Buffer.from(await form.get('original_image').arrayBuffer()));
  assert.ok(original.top.slice(0,3).every(v=>v>=245),'the original photo\'s transparent band is white');
  assert.deepEqual(errors,[]);assert.deepEqual(outside,[]);
 }finally{await browser.close();server.close();}
});
