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

test('the community keeps the gallery layout in HaslaLab\'s own colours, only on community pages, and keeps the phone layout',()=>{
  const css=read('site-design.css');
  assert.match(css,/body\.hl-site\[data-site-route="community"\] \.cm\{--cm-ink:#263247;[^}]*--cm-acc:#7059a4/,'the site\'s ink and violet accent');
  assert.doesNotMatch(css,/--dc:#3b4890|DCInside-style/,'no copy of another site\'s colours');
  assert.match(css,/@media\(min-width:1280px\)\{body\.hl-site\[data-site-route="community"\] \.cmgrid/,'three columns only where the list keeps room');
  assert.match(css,/@media\(min-width:761px\) and \(max-width:1279px\)\{body\.hl-site\[data-site-route="community"\] \.cmgrid\{grid-template-columns:200px minmax\(0,1fr\)/);
  assert.doesNotMatch(css,/@media\(max-width:1100px\)\{body\.hl-site\[data-site-route="community"\] \.cmgrid/,'the two-column rule must not reach phones');
});

test('the rules sit under the menu on the left, the side boxes never float over the list or a post',()=>{
  const html=read('index.html'),css=read('site-design.css'),a=app();
  a.run('lang="ko"');
  const view=a.run('viewCommunity()');
  assert.match(view,/<div class="cmleft"><aside class="cmrail" id="cmRail"><\/aside>\s*<aside class="cmside cmrules" id="cmRules"><h3>커뮤니티 규칙<\/h3>/,'rules under the menu rail');
  assert.ok(view.indexOf('id="cmRules"')<view.indexOf('id="cmRoot"'),'rules belong to the left column');
  assert.doesNotMatch(a.run('cmRight.toString()'),/rulesH/,'the right column no longer carries the rules');
  /* every column is in the grid's flow: nothing sticky, fixed or absolute that could slide over the list */
  const rules=[...html.matchAll(/^\.(cmgrid|cmleft|cmrail|cmright|cmside)\{[^}]*\}/gm)].map(m=>m[0]);
  assert.equal(rules.length,5);for(const r of rules)assert.doesNotMatch(r,/position:(sticky|fixed|absolute)|z-index|margin[^;]*-\d/,r);
  assert.doesNotMatch(css,/\.cm(rail|right|side|left)\{[^}]*position:(sticky|fixed|absolute)/);
  assert.match(html,/@media\(max-width:1279px\)\{\.cmgrid\{grid-template-columns:200px minmax\(0,1fr\);grid-template-areas:"left main" "left side"\}/,'medium widths: side boxes under the list');
  assert.match(html,/@media\(max-width:760px\)\{\.cmgrid\{grid-template-columns:minmax\(0,1fr\);grid-template-areas:"rail" "main" "side" "rules"\}/,'phones: menu, list, side boxes, rules');
});

test('gallery names are escaped wherever a post shows its board',()=>{
  const html=read('index.html');
  assert.ok(!/T\.boards\[(p|item)\.board\]\|\|/.test(html),'board labels go through cmBoardName');
  assert.match(html,/# \$\{esc\(bName\)\}/);
});
