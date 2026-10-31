// node --test tests/test-scan-resolution-browser.cjs  (HASLA_PLAYWRIGHT_PATH, CHROME_BIN as for the other browser tests)
// A 12 MP phone photo is straightened from its own pixels, not from the 2400px working copy, and a corner fix
// that passes the result's sourceBlob back keeps that resolution.
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const root=path.resolve(__dirname,'..');let chromium,executable;
try{
 ({chromium}=require(process.env.HASLA_PLAYWRIGHT_PATH?path.resolve(root,process.env.HASLA_PLAYWRIGHT_PATH):path.join(root,'tmp/browser-qa/node_modules/playwright')));
 executable=process.env.CHROME_BIN||(process.platform==='win32'?'C:/Program Files/Google/Chrome/Application/chrome.exe':['/usr/bin/google-chrome','/usr/bin/chromium',chromium.executablePath()].find(p=>fs.existsSync(p)));
 if(!fs.existsSync(executable))chromium=null;
}catch{}
test('a large photo keeps its stroke sharpness through straightening and a corner fix',{skip:!chromium&&'Set HASLA_PLAYWRIGHT_PATH and CHROME_BIN',timeout:120000},async()=>{
 const server=http.createServer((req,res)=>{
  if(req.url==='/__resolution_qa'){res.setHeader('Content-Type','text/html');return res.end('<!doctype html><title>Resolution QA</title>');}
  const file=path.resolve(root,'.'+new URL(req.url,'http://localhost').pathname);
  if(!file.startsWith(root+path.sep)||!fs.existsSync(file)||fs.statSync(file).isDirectory()){res.writeHead(404);return res.end();}
  res.setHeader('Content-Type',/\.m?js$/.test(file)?'text/javascript':file.endsWith('.wasm')?'application/wasm':'application/octet-stream');
  fs.createReadStream(file).pipe(res);
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const origin='http://127.0.0.1:'+server.address().port,browser=await chromium.launch({headless:true,executablePath:executable});
 try{
  const page=await browser.newPage();await page.goto(origin+'/__resolution_qa');
  const r=await page.evaluate(async()=>{
   const S=await import('/sim/labscan/scanner.js');
   const W=4032,H=3024,OW=1654,OH=2339,line='E = mc^2 + ∫ f(x) dx  ·  a_n = 1/n^2  ·  v_0 = 3.2×10^4 m/s  ·  θ = 37°';
   const quad=[{x:1180,y:160},{x:2900,y:210},{x:1120,y:2620},{x:2960,y:2560}];
   const page=scale=>{const c=document.createElement('canvas');c.width=OW*scale;c.height=OH*scale;const g=c.getContext('2d');g.scale(scale,scale);
    g.fillStyle='#fff';g.fillRect(0,0,OW,OH);g.fillStyle='#1b1b2a';g.font='22px serif';for(let y=120;y<OH-80;y+=34)g.fillText(line,70,y);return c;};
   const ideal=page(1),big=page(2),photo=document.createElement('canvas');photo.width=W;photo.height=H;
   const g=photo.getContext('2d');g.fillStyle='#6a6560';g.fillRect(0,0,W,H);
   const bd=big.getContext('2d').getImageData(0,0,big.width,big.height),pd=g.getImageData(0,0,W,H);
   const Hm=S.solveHomography(quad,[{x:0,y:0},{x:big.width,y:0},{x:0,y:big.height},{x:big.width,y:big.height}]);
   for(let y=0;y<H;y++)for(let x=0;x<W;x++){const w=Hm[6]*x+Hm[7]*y+Hm[8],u=(Hm[0]*x+Hm[1]*y+Hm[2])/w,v=(Hm[3]*x+Hm[4]*y+Hm[5])/w;
    if(u<0||v<0||u>=big.width||v>=big.height)continue;const s=((v|0)*big.width+(u|0))*4,o=(y*W+x)*4;for(let c=0;c<3;c++)pd.data[o+c]=bd.data[s+c]*.96;}
   g.putImageData(pd,0,0);
   const blob=await new Promise(res=>photo.toBlob(res,'image/jpeg',.92));
   const sharp=data=>{let s=0,n=0;for(let y=1;y<OH;y++)for(let x=1;x<OW;x++){const i=(y*OW+x)*4;s+=Math.abs(data[i]-data[i-4])+Math.abs(data[i]-data[i-OW*4]);n++;}return s/n;};
   const of=async b=>{const bmp=await createImageBitmap(b),c=document.createElement('canvas');c.width=OW;c.height=OH;c.getContext('2d').drawImage(bmp,0,0,OW,OH);return sharp(c.getContext('2d').getImageData(0,0,OW,OH).data);};
   const k=2400/W,corners=quad.map(q=>({x:q.x*k,y:q.y*k}));
   const scan=await S.processShot(blob,{corners,mode:'original',pageFormat:'a4'});
   const fixed=await S.reprocess(scan.baseUrl,scan.corners,'original',undefined,null,{pageFormat:'a4',source:scan.sourceBlob});
   return{ideal:sharp(ideal.getContext('2d').getImageData(0,0,OW,OH).data)*.96,scan:await of(scan.blob),fixed:await of(fixed.blob),
    baseW:scan.baseW,source:scan.sourceBlob===blob,shortSide:scan.sourceShortSide,size:[scan.width,scan.height]};
  });
  assert.deepEqual(r.size,[1654,2339]);assert.equal(r.baseW,2400,'detection and corner editing stay on the 2400px working copy');
  assert.equal(r.source,true);assert.ok(r.shortSide>1600,'the low-resolution warning reads the photo\'s own pixels');
  assert.ok(r.scan>=r.ideal*.92,`straightened sharpness ${r.scan.toFixed(2)} vs ideal ${r.ideal.toFixed(2)}`);
  assert.ok(r.fixed>=r.ideal*.92,`after a corner fix ${r.fixed.toFixed(2)} vs ideal ${r.ideal.toFixed(2)}`);
 }finally{await browser.close();server.close();}
});
