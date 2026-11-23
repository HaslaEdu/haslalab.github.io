const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const G=require('../guide.js'),P=require('../learn-path.js'),Runtime=require('../site-runtime.js'),{build}=require('../tools/build-guide.cjs');
const read=f=>fs.readFileSync(path.join(__dirname,'..',f),'utf8');
const PLAIN=/—|unlock|seamless|elevate|comprehensive|empower|journey|delve|잠금 해제|원활|한 단계 높/i;

test('Markdown: numbered equations and figures, references, the five boxes, and a solution inside an exercise',()=>{
  const md=`---\ntitle_ko: 시험\ntitle_en: Test\nunit: mechanics/kinematics\nlevel: 3\norder: 2\n---\n## First $v$\n\nSee [@a] and [@f].\n\n$$ v = v_0 + at $$ {#a}\n\n$$\nx = \\frac12 a t^2\n$$ {#b}\n\n![A graph](fig/x.svg){#f}\n\n:::remark\nNote **bold** and *it*.\n:::\n\n:::result\n- one\n- two\n:::\n\n:::why Why so?\nBecause.\n:::\n\n:::derivation From [@b]\nSteps.\n:::\n\n:::example A car\nWork.\n:::\n\n## Try\n\n:::try A\n1. Q\n\n:::solution\nAnswer.\n:::\n:::\n`;
  const d=G.renderMarkdown(md,'en');
  assert.deepEqual(d.errors,[]);
  assert.equal(d.meta.level,3);assert.equal(d.meta.order,2);assert.equal(d.meta.title_en,'Test');
  assert.equal(d.equations,2);assert.equal(d.tries,1);assert.deepEqual(d.figures,['fig/x.svg']);
  assert.deepEqual(d.toc.map(s=>s.id),['s-1','s-2']);
  assert.match(d.html,/<div class="geq" id="eq-a">[\s\S]*?<span class="geq-n">\(1\)<\/span>/);
  assert.match(d.html,/id="eq-b"[\s\S]*?\(2\)/);
  assert.match(d.html,/See <a class="gref" href="#eq-a" data-gd-jump="eq-a">\(1\)<\/a> and <a class="gref" href="#fig-f" data-gd-jump="fig-f">Figure 1<\/a>/);
  assert.match(d.html,/<figure class="gfig" id="fig-f"><img src="guide\/fig\/x\.svg"/);
  for(const k of ['g-remark','g-result','g-why','g-example'])assert.match(d.html,new RegExp('class="gbox '+k+'"'),k);
  assert.match(d.html,/<details class="gbox g-deriv"><summary>[\s\S]*?From <a class="gref"[^>]*>\(2\)<\/a>/,'a derivation is a show/hide box, its title may cite an equation');
  assert.match(d.html,/<section class="gbox g-try" id="try-1">[\s\S]*<details class="g-sol"><summary>Show the solution/,'the solution is hidden inside the exercise');
  assert.match(d.html,/<strong>bold<\/strong> and <em>it<\/em>/);
  assert.match(d.html,/<span class="gm" data-tex="v">v<\/span>/,'inline math waits for KaTeX');
  assert.match(G.renderMarkdown(md,'ko').html,/직접 풀어 보기 1[\s\S]*풀이 보기/);
});

test('Markdown: text is escaped, only safe links survive, and mistakes are reported',()=>{
  const d=G.renderMarkdown('<script>alert(1)</script> [x](javascript:alert(1)) [y](https://example.org) [z](#/learn/practice) $<b>$ "q"\n','en');
  assert.doesNotMatch(d.html,/<script|<b>|javascript:/);
  assert.match(d.html,/&lt;script&gt;/);assert.match(d.html,/<a href="https:\/\/example\.org" target="_blank" rel="noopener">y<\/a>/);
  assert.match(d.html,/<a href="#\/learn\/practice">z<\/a>/);
  const bad=G.renderMarkdown(':::nope\n:::\n\n:::solution\nx\n:::\n\n[@missing]\n\n:::remark\nopen\n','en');
  assert.ok(bad.errors.some(e=>/unknown box/.test(e)));assert.ok(bad.errors.some(e=>/solution outside/.test(e)));
  assert.ok(bad.errors.some(e=>/unknown reference/.test(e)));assert.ok(bad.errors.some(e=>/never closed/.test(e)));
  assert.equal(G.plainText('---\nunit: a/b\n---\n## Head\n\nSpeed $v_0$ and **bold**.\n\n$$x=1$$\n'),'Head Speed v 0 and bold.');
});

test('the chapters build cleanly and guide/index.json and the asset digests are current',()=>{
  const {errors,index,html,chapters}=build();
  assert.deepEqual(errors,[]);
  assert.equal(read('guide/index.json'),index,'run node tools/build-guide.cjs');
  assert.equal(read('index.html'),html,'guide.js and guide.css digests in index.html (node tools/build-guide.cjs)');
  assert.deepEqual(chapters.map(c=>c.unit+'/'+c.slug),['mechanics/kinematics/constant-acceleration','mechanics/energy/conservation-of-energy']);
  const idx=JSON.parse(index);
  assert.equal(idx.sims['mechanics/kinematics'].id,'projectile','the kinematics unit links its concept simulation');
  for(const c of idx.chapters){assert.ok(P.SUBTOPICS.has(c.unit));assert.ok(c.text.ko.length>500&&c.text.en.length>500);assert.ok(c.sections.ko.length===c.sections.en.length);}
});

test('the two sample chapters: derivations, a worked example, two exercises with solutions, one figure, in both languages and plain words',()=>{
  for(const [unit,slug,fig] of [['mechanics/kinematics','constant-acceleration','kinematics-vt-graph.svg'],['mechanics/energy','conservation-of-energy','energy-track.svg']]){
    for(const l of ['ko','en']){
      const src=read(`guide/${unit}/${slug}.${l}.md`),d=G.renderMarkdown(src,l);
      assert.deepEqual(d.errors,[],slug+'.'+l);
      assert.ok((d.html.match(/class="gbox g-deriv"/g)||[]).length>=1,'a derivation');
      assert.equal((d.html.match(/class="gbox g-example"/g)||[]).length,1,'a worked example');
      assert.equal(d.tries,2);assert.equal((d.html.match(/class="g-sol"/g)||[]).length,2,'each exercise has a solution');
      assert.ok(/class="gbox g-result"/.test(d.html)&&/class="gbox g-why"/.test(d.html)&&/class="gbox g-remark"/.test(d.html));
      assert.deepEqual(d.figures,['fig/'+fig]);assert.ok(d.equations>=6);
      assert.doesNotMatch(src,PLAIN,slug+'.'+l);
    }
    const svg=read('guide/fig/'+fig);assert.match(svg,/^<svg xmlns="http:\/\/www\.w3\.org\/2000\/svg" viewBox=/);assert.doesNotMatch(svg,/<script|on\w+=/i);
  }
  /* the worked numbers */
  assert.ok(Math.abs(Math.sqrt(15**2+2*9.8*20)-24.8)<0.05);assert.ok(Math.abs((15+Math.sqrt(617))/9.8-4.1)<0.05);
  assert.ok(Math.abs(20+15**2/(2*9.8)-31.5)<0.05);assert.ok(Math.abs(Math.sqrt(200)-10-4.1)<0.05);
  assert.ok(Math.abs(Math.sqrt(2*9.8*1.8)-5.9)<0.05);assert.ok(Math.abs(1.8/0.3-6)<1e-9);
  assert.ok(Math.abs(Math.sqrt(2*9.8*0.5)-3.1)<0.05);assert.ok(Math.abs(2.5/(0.2*9.8)-1.28)<0.01);
  assert.match(read('guide/README.md'),/:::try[\s\S]*:::solution/);
});

/* the site script, as tests/test-learn-path.cjs runs it */
function app(hash){
  const main=[...read('index.html').matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].find(m=>m[1].includes('const REL ='))[1];
  let navHtml='';
  const node={dataset:{},style:{},classList:{toggle(){},add(){},remove(){}},setAttribute(){},addEventListener(){},querySelector(){return null},querySelectorAll(){return[]}};
  const nav={...node,set innerHTML(v){navHtml=v;},get innerHTML(){return navHtml;}};
  const context={window:{HL_RUNTIME:Runtime},URL,URLSearchParams,console,location:{hash,search:''},history:{replaceState(){}},
    document:{getElementById:id=>id==='nav'?nav:node,querySelector:()=>null,querySelectorAll:()=>[],documentElement:{dataset:{theme:'light'}},body:node},
    localStorage:{getItem:()=>null,setItem(){}},sessionStorage:{getItem:()=>null,setItem(){}},
    addEventListener(){},matchMedia:()=>({matches:false}),setTimeout(){},clearTimeout(){},requestAnimationFrame(){},cancelAnimationFrame(){},
    fetch:async()=>{throw Error('no fetch');}};
  vm.createContext(context);
  for(const file of ['site-catalogue.js','paper-languages.js','examdur.js','rupho-archive.js','learn-path.js','site-design.js','guide.js'])vm.runInContext(read(file),context,{filename:file});
  context.HLexam=context.window.HLexam;context.window.HL_LEARN_PATH=context.HL_LEARN_PATH;context.window.HL_GUIDE=context.HL_GUIDE;
  vm.runInContext(main.replace(/render\(\);\s*$/,''),context,{filename:'index-main.js'});
  return{run:code=>vm.runInContext(code,context),context};
}

test('the Learn bar has 교재 / Guide between the roadmap and the courses, with a short line, marked on every guide page',()=>{
  const a=app('#/learn/guide');
  for(const language of ['ko','en']){
    a.run(`lang=${JSON.stringify(language)}`);
    const links=Array.from(a.run('sectionLinks("learn")'));
    assert.deepEqual(links.map(x=>x[0]),['#/learn/practice','#/learn/roadmap','#/learn/guide','#/learn/courses','#/learn/physics/search','#/learn/lab']);
    assert.equal(links[2][1],language==='ko'?'교재':'Guide');assert.ok(links[2][3].length<90);assert.doesNotMatch(links[2][3],PLAIN);
    for(const h of ['#/learn/guide','#/learn/guide/mechanics/kinematics','#/learn/guide/mechanics/kinematics/constant-acceleration'])
      assert.deepEqual(links.filter(x=>x[2](h)).map(x=>x[0]),['#/learn/guide'],h);
    assert.equal(links[2][2]('#/learn/guidebook'),false);
  }
  for(const h of ['#/learn/guide','#/learn/guide/mechanics/energy/conservation-of-energy'])assert.deepEqual(Runtime.routeNeeds(h),[],h);
});

test('the guide views: one line and two tabs on the front page, the unit and chapter frames, nothing fetched before mount',()=>{
  const a=app('#/learn/guide');
  for(const language of ['ko','en']){
    a.run(`lang=${JSON.stringify(language)}`);
    a.context.location.hash='#/learn/guide';
    let html=a.run('HL_GUIDE.view()');
    assert.match(html,language==='ko'?/단원마다 읽는 물리 교재입니다/:/A physics textbook, unit by unit/);
    assert.match(html,/href="#\/learn\/guide" aria-current="page"/);assert.match(html,/href="#\/learn\/guide\?tab=handouts"/);
    assert.match(html,/data-gd="book"/);assert.doesNotMatch(html,PLAIN);
    a.context.location.hash='#/learn/guide?tab=handouts';
    assert.match(a.run('HL_GUIDE.view()'),/data-gd="handouts"[\s\S]*href="#\/learn\/guide\?tab=handouts" aria-current="page"/);
    a.context.location.hash='#/learn/guide/mechanics/energy';
    html=a.run('HL_GUIDE.view()');assert.match(html,/data-gd="unit"/);assert.match(html,language==='ko'?/일과 에너지/:/Work and energy/);
    a.context.location.hash='#/learn/guide/mechanics/kinematics/constant-acceleration';
    assert.match(a.run('HL_GUIDE.view()'),/data-gd="chapter"[\s\S]*id="gdTitle"/);
  }
});

test('every archive solution link has a «report an error» action that posts to /api/learn/report',()=>{
  const a=app('#/');
  const key=a.run('archiveReportKey("ipho",2019,"T1")');
  assert.equal(key,'archive:ipho-2019-T1');assert.match(key,/^[\w~.:-]{1,80}$/,'the server\'s item_id pattern');
  assert.equal(a.run('archiveReportKey("x y",2020,"T<1>")'),'archive:x-y-2020-T-1-');
  for(const language of ['ko','en']){
    a.run(`lang=${JSON.stringify(language)}`);
    const card=a.run('probCard({code:"T1",report:"archive:ipho-2019-T1",mode:"dl",chip:"",heading:"H",tags:["t"],main:["<a>s</a>"],docs:[]})');
    assert.match(card,/data-sol-report="archive:ipho-2019-T1"/);
    assert.match(card,language==='ko'?/해설 오류 신고/:/Report an error in the solution/);
    assert.doesNotMatch(a.run('probCard({code:"T1",mode:"dl",chip:"",heading:"H",tags:["t"],main:[],docs:[]})'),/data-sol-report/,'no solution, no report button');
  }
  const src=read('index.html');
  assert.match(src,/report:S\[0\]\?archiveReportKey\(key,yr\.y,code\):""/,'the theory cards pass a key only when there is a solution');
  assert.match(src,/cmApi\("POST","\/learn\/report",\{item_id:btn\.dataset\.solReport,reason,note,source:"archive"/);
  assert.match(src,/value="wrong_answer"[\s\S]{0,200}value="other"/);
});

test('handouts: the page talks to the handout API and admins get the upload form; the guide has its README',()=>{
  const src=read('guide.js');
  assert.match(src,/'\/learn\/handouts'/);assert.match(src,/\/api\/learn\/handouts'/);
  assert.match(src,/role==='admin'/);assert.match(src,/accept="application\/pdf,\.pdf"/);assert.match(src,/25\*1024\*1024/);
  for(const k of ['title_ko','title_en','summary_ko','summary_en','unit','level','status'])assert.match(src,new RegExp(`'${k}'`),k);
  assert.match(src,/localStorage\.setItem\(READ_KEY/,'the read marks stay in this browser');
  assert.match(src,/#\/learn\/practice\?mode=custom&unit=/);
  assert.match(src,/#\/community\/write\/qna\?/,'the discussion link opens a Q&A post');
});
