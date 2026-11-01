// Actual phone scanner UI with automatic capture on: a sheet whose outline turns green is taken without the shutter.
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
test('automatic capture takes a sheet once its outline is green and held still, without the shutter (a phone held at an ordinary slant)',
 {skip:!chromium&&'Set HASLA_PLAYWRIGHT_PATH and CHROME_BIN for camera UI integration',timeout:120000},async()=>{
 const server=http.createServer((request,response)=>{
  const target=path.resolve(root,'.'+new URL(request.url,'http://localhost').pathname);
  if(!target.startsWith(root+path.sep)||!fs.existsSync(target)||fs.statSync(target).isDirectory()){response.writeHead(404);return response.end();}
  const mime={'.html':'text/html','.mjs':'text/javascript','.js':'text/javascript','.wasm':'application/wasm','.jpg':'image/jpeg'};
  let body=fs.readFileSync(target);
  if(target===path.join(root,'sim/scan.html'))body=body.toString().replace('if (!KEY) $("app")','window.__scan={getShot:()=>shot};\nif (!KEY) $("app")');
  response.writeHead(200,{'Content-Type':mime[path.extname(target)]||'application/octet-stream'});response.end(body);
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const origin='http://127.0.0.1:'+server.address().port;
 let browser;
 try{
  browser=await chromium.launch({headless:true,executablePath:executable});
  const context=await browser.newContext({viewport:{width:412,height:915}}),errors=[];
  await context.route('**/*',route=>{
   const url=route.request().url();
   if(url.includes('/api/lab/up'))return route.fulfill({json:{comp:'ipho',year:2025,tasks:['T1'],open:true,status:'scanning',now:Date.now()/1000,scan_until:Date.now()/1000+3600,pages:[]}});
   if(!url.startsWith(origin+'/'))return route.abort();
   return route.continue();
  });
  await context.addInitScript(()=>{
   localStorage.setItem('hlScanAuto','1');
   Object.defineProperty(navigator.mediaDevices,'getUserMedia',{value:async()=>{
    // an A4 sheet of ruled writing on a desk, seen with the phone some 26° off the vertical (the ordinary way to hold it):
    // its outline is green, and automatic capture once still waited for a flatter view
    const W=900,H=1200,f=.62*Math.hypot(W,H),D=430,tilt=.45,canvas=document.createElement('canvas'),g=canvas.getContext('2d');
    const at=(x,y)=>{const Y=y*Math.cos(tilt),Z=D+y*Math.sin(tilt);return[W/2+f*x/Z,H/2+f*Y/Z];};
    canvas.width=W;canvas.height=H;g.fillStyle='rgb(120,116,112)';g.fillRect(0,0,W,H);
    g.fillStyle='rgb(240,240,236)';g.beginPath();[[-105,-148.5],[105,-148.5],[105,148.5],[-105,148.5]].forEach(([x,y],i)=>g[i?'lineTo':'moveTo'](...at(x,y)));g.closePath();g.fill();
    g.strokeStyle='rgb(60,60,70)';g.lineWidth=2;
    for(let k=0;k<14;k++){const y=-120+k*18;g.beginPath();g.moveTo(...at(-85,y));g.lineTo(...at(60,y));g.stroke();}
    return canvas.captureStream(15);
   }});
  });
  const page=await context.newPage();page.on('pageerror',error=>errors.push(error.message));
  await page.goto(origin+'/sim/scan.html#c=local-camera-fixture&l=en');
  await page.locator('#live').click();
  const started=Date.now();
  await page.waitForFunction(()=>window.__scan.getShot()&&!window.__scan.getShot().busy,{timeout:30000});
  const shot=await page.evaluate(()=>{const s=window.__scan.getShot();return{warp:s.warpApplied,method:s.method,width:s.width};});
  assert.equal(await page.locator('.lv').count(),0,'the camera closed itself after taking the sheet');
  assert.equal(shot.warp,true);assert.equal(shot.method,'page');
  assert.deepEqual(errors,[]);
  console.log(JSON.stringify({autoCaptureMs:Date.now()-started,shot}));
 }finally{await browser?.close();await new Promise(resolve=>server.close(resolve));}
});
