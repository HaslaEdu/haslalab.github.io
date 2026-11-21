const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const Runtime=require('../site-runtime.js');
const read=file=>fs.readFileSync(path.join(__dirname,'..',file),'utf8');
const main=[...read('index.html').matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].find(match=>match[1].includes('const REL ='))[1];
const links=html=>[...html.matchAll(/<a\b[^>]*href="([^"]+)"/g)].map(match=>match[1]);
function app(){
  const node={dataset:{},style:{},classList:{toggle(){},add(){},remove(){}},setAttribute(){},addEventListener(){},querySelector(){return null},querySelectorAll(){return[]}};
  const root={...node,innerHTML:''};
  const context={window:{HL_RUNTIME:Runtime},URL,URLSearchParams,console,location:{hash:'#/community',search:''},history:{replaceState(){}},
    document:{getElementById:id=>id==='cmRoot'?root:node,querySelector:()=>null,querySelectorAll:()=>[],documentElement:{dataset:{theme:'light'}},body:node},
    localStorage:{getItem:()=>null,setItem(){}},sessionStorage:{getItem:()=>null,setItem(){}},
    addEventListener(){},matchMedia:()=>({matches:false}),setTimeout(){},clearTimeout(){},requestAnimationFrame(){},cancelAnimationFrame(){},fetch:async()=>{throw Error('no network');}};
  vm.createContext(context);
  for(const file of ['site-catalogue.js','paper-languages.js','examdur.js','rupho-archive.js','site-design.js'])vm.runInContext(read(file),context,{filename:file});
  context.HLexam=context.window.HLexam;
  vm.runInContext(main.replace(/render\(\);\s*$/,''),context,{filename:'index-main.js'});
  return{run:code=>vm.runInContext(code,context),root};
}
const G={'g-kpho':{board:'g-kpho',name:'KPhO 갤러리',intro:'한국물리올림피아드 <준비>',owner:'kim',n:3}};

test('gallery boards are recognised next to the main gallery boards, and anything else is not',()=>{
  const a=app();
  for(const b of ['free','qna','sim','study','g-kpho','g-kpho-2027'])assert.equal(a.run(`cmIsBoard(${JSON.stringify(b)})`),true,b);
  for(const b of ['g-','g-ab','g-ABC','g-<x>','secret','all','galleries'])assert.equal(a.run(`cmIsBoard(${JSON.stringify(b)})`),false,b);
  a.run(`cm.galleries=${JSON.stringify(G)}`);
  assert.equal(a.run('cmBoardName("g-kpho")'),'KPhO 갤러리');assert.equal(a.run('cmBoardName("g-unknown")'),'unknown');
});

test('the rail shows the main gallery, minor galleries, the directory and the opener, in both languages',()=>{
  const a=app();a.run(`cm.galleries=${JSON.stringify(G)}`);
  for(const language of ['ko','en']){
    a.run(`lang=${JSON.stringify(language)}`);
    const html=a.run('cmRailHtml("g-kpho")'),hrefs=links(html);
    for(const h of ['#/community/free','#/community/g-kpho','#/community/galleries','#/community/new-gallery'])assert.ok(hrefs.includes(h),h);
    assert.match(html,language==='ko'?/메인 갤러리[\s\S]*마이너 갤러리/:/Main gallery[\s\S]*Minor galleries/);
    assert.match(html,/class="ch on" href="#\/community\/g-kpho"/);
  }
});

test('the gallery directory escapes what members wrote',()=>{
  const a=app();a.run(`cm.galleries=${JSON.stringify(G)};lang="ko"`);
  a.run('cmGalleries(document.getElementById("cmRoot"))');
  assert.match(a.root.innerHTML,/href="#\/community\/g-kpho"/);
  assert.match(a.root.innerHTML,/&lt;준비&gt;/);assert.doesNotMatch(a.root.innerHTML,/<준비>/);
});
