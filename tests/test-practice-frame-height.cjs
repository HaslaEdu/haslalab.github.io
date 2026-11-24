/* The tool frames on Learn (practice, studio, teach, draw, ...) are as tall as their content: each frame posts its
   height and index.html sets it. WebKit (Safari, every iOS browser) reports a frame's postMessage made from a callback
   (requestAnimationFrame, ResizeObserver, timers) with event.source set to the receiving window, so a check for
   event.source===frame.contentWindow alone dropped every height report there: the practice frame stayed 1050px tall and
   the rest of the problems could not be scrolled to. The browser part runs when Playwright is available
   (HASLA_PLAYWRIGHT_PATH, as in the scan tests); WebKit is used too when it is installed. */
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const root=path.resolve(__dirname,'..'),read=f=>fs.readFileSync(path.join(root,f),'utf8');

test('every tool frame on the page accepts its height reports through one same-origin check',()=>{
  const html=read('index.html');
  assert.match(html,/function fromSameOriginFrame\(event,frame\)\{\s*return !!frame&&event\.origin===location\.origin&&\(event\.source===frame\.contentWindow\|\|event\.source===window\);/);
  assert.doesNotMatch(html,/event\.source!==frame\.contentWindow/,'no frame listener checks event.source alone');
  for(const type of ['studio','concepts','practice','create','teach','draw','compute','problem-search']){
    const at=html.indexOf(`"hl-${type}-height"`)>=0?html.indexOf(`"hl-${type}-height"`):html.indexOf(`'hl-${type}-height'`);
    assert.ok(at>0,type+' height handler present');
    const listener=html.lastIndexOf('addEventListener("message"',at);
    assert.match(html.slice(listener,at),/fromSameOriginFrame\(event,frame\)/,type+' handler uses the shared check');
  }
});

test('the practice frame reports its height on layout changes, late figures, fonts and opened details',()=>{
  const js=read('practice.js');
  assert.match(js,/ro\.observe\(document\.documentElement\);ro\.observe\(document\.body\)/);
  assert.match(js,/document\.addEventListener\('load',e=>\{if\(e\.target\?\.tagName==='IMG'\)reportHeight\(\);\},true\)/);
  assert.match(js,/document\.fonts\?\.ready\?\.then\(reportHeight\)/);
  assert.match(js,/document\.addEventListener\('toggle',reportHeight,true\)/);
  assert.match(js,/heightTimer=setTimeout\(sendHeight,300\)/,'a timer backs up the animation frame');
});

let pw=null;
try{pw=require(process.env.HASLA_PLAYWRIGHT_PATH?path.resolve(root,process.env.HASLA_PLAYWRIGHT_PATH):path.join(root,'tmp/browser-qa/node_modules/playwright'));}catch{}
const FIG_UNIT='mechanics/newton';   /* every problem in this unit has a figure */

test('practice frame: after a slow figure load the page scrolls to the last line (desktop, phone, iPad)',
 {skip:!pw&&'Set HASLA_PLAYWRIGHT_PATH',timeout:240000},async()=>{
  const types={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.css':'text/css','.json':'application/json','.webp':'image/webp','.png':'image/png','.svg':'image/svg+xml','.woff2':'font/woff2'};
  const server=http.createServer((req,res)=>{
    const file=path.resolve(root,'.'+decodeURIComponent(new URL(req.url,'http://localhost').pathname));
    if(!file.startsWith(root+path.sep)||!fs.existsSync(file)||fs.statSync(file).isDirectory()){res.writeHead(404);return res.end();}
    res.setHeader('Content-Type',types[path.extname(file)]||'application/octet-stream');fs.createReadStream(file).pipe(res);
  });
  await new Promise(r=>server.listen(0,'127.0.0.1',r));
  const origin='http://127.0.0.1:'+server.address().port;
  const engines=[['chromium',pw.chromium],['webkit',pw.webkit]];
  const shapes=[['desktop',{viewport:{width:1280,height:800}}],['phone',{...pw.devices['iPhone 13'],hasTouch:true}],['ipad',{...pw.devices['iPad Pro 11']}]];
  try{
    for(const [engine,type] of engines){
      let browser;try{browser=await type.launch({headless:true});}catch(e){if(engine==='chromium')throw e;continue;}
      try{
        for(const [shape,options] of shapes){
          const {defaultBrowserType,...opts}=options;const context=await browser.newContext(opts);
          await context.addInitScript(()=>{try{localStorage.setItem('hl-notice-2026-12-monthly-extended','never');
            if(!localStorage.getItem('hlPractice'))localStorage.setItem('hlPractice',JSON.stringify({profile:{region:'kr',level:'',goal:'',oly:0,daily:10,quick:true,at:1},studyLevel:'L2'}));}catch(e){}});
          await context.route('**/*',async route=>{const url=route.request().url();if(!url.startsWith(origin+'/'))return route.abort();
            if(/\/practice\/fig\//.test(url))await new Promise(r=>setTimeout(r,1500));return route.continue();});
          const page=await context.newPage(),label=`${engine} ${shape}`;
          for(const hash of ['#/learn/practice','#/learn/practice?unit='+FIG_UNIT]){
            await page.goto(origin+'/index.html'+hash);await page.reload();
            const frame=page.frameLocator('#learnPracticeFrame');
            if(hash.includes('unit=')){await frame.locator('#icGo').click({timeout:20000});await frame.locator('.q').first().waitFor({timeout:20000});}
            else await frame.locator('.today').first().waitFor({timeout:20000});
            /* scroll to the bottom so lazy figures load, then wait for them (each one arrives 1.5 s late) */
            await page.evaluate(()=>scrollTo(0,document.documentElement.scrollHeight));
            await page.waitForFunction(()=>{const d=document.getElementById('learnPracticeFrame')?.contentDocument;return !!d&&[...d.images].every(i=>i.complete);},null,{timeout:20000});
            await page.waitForTimeout(800);
            await page.evaluate(()=>scrollTo(0,document.documentElement.scrollHeight));await page.waitForTimeout(200);
            const m=await page.evaluate(()=>{const f=document.getElementById('learnPracticeFrame'),d=f.contentDocument;
              const last=[...d.querySelectorAll('main *')].filter(e=>e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden'&&!e.closest('details:not([open]) > :not(summary)')).pop();
              return {frameH:f.getBoundingClientRect().height,innerScroll:d.documentElement.scrollHeight,innerClient:d.documentElement.clientHeight,
                mainBottom:d.querySelector('main').getBoundingClientRect().bottom,lastBottom:f.getBoundingClientRect().top+last.getBoundingClientRect().bottom,
                atEnd:Math.abs(scrollY+innerHeight-document.documentElement.scrollHeight)<=2,vh:innerHeight,images:d.images.length};});
            assert.ok(m.frameH>=m.mainBottom,`${label} ${hash}: the frame (${m.frameH}px) holds all of its content (${m.mainBottom}px)`);
            assert.ok(m.innerScroll<=m.innerClient+1,`${label} ${hash}: nothing scrolls inside the frame (${m.innerScroll} > ${m.innerClient})`);
            assert.ok(m.atEnd,`${label} ${hash}: the page scrolls to its end`);
            assert.ok(m.lastBottom<=m.vh+1,`${label} ${hash}: the last line of the frame is on screen at the end (${m.lastBottom} > ${m.vh})`);
            if(hash.includes('unit='))assert.ok(m.images>=1,`${label}: the figure problem has its figures`);
          }
          await context.close();
        }
      }finally{await browser.close();}
    }
  }finally{server.close();}
});
