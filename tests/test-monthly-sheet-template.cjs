const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..');
test('every actual subquestion has exactly one answer-sheet slot and its web points total 100',async()=>{
  const {getMonthlyAnswerSheet}=await import('../monthly-problems.mjs');
  const source=['2026-W44.json','2026-11-greenhouse-part-d.json'].flatMap(name=>JSON.parse(fs.readFileSync(path.join(root,'community/weekly',name),'utf8')).problems);
  for(const [index,id,count]of [[0,4,10],[1,5,5],[2,6,7],[3,7,10]]){
    const sheet=getMonthlyAnswerSheet(id),ids=sheet.parts.map(p=>p.id);
    assert.equal(sheet.limit,3);assert.equal(ids.length,count);assert.equal(new Set(ids).size,count);
    assert.deepEqual(sheet.pages.flat(),ids,'the printed form covers every subquestion exactly once');
    assert.equal(sheet.parts.reduce((s,p)=>s+p.points,0),100);
    for(const p of sheet.parts){
      const criteria=source[index].rubric.filter(c=>id===4?c.id===p.id:id===5?c.id.startsWith(p.id):c.id===p.id||c.id.startsWith(p.id));
      assert.equal(criteria.reduce((s,c)=>s+c.max,0),p.points,p.id+' matches the private rubric without exposing its answers');
      assert.ok(p.label_ko&&p.label_en);assert.ok(!('requirement'in p));
    }
    sheet.parts[0].id='mutated';assert.notEqual(getMonthlyAnswerSheet(id).parts[0].id,'mutated');
  }
  assert.equal(getMonthlyAnswerSheet(1),null);
});
test('printable pages provide separate final-answer and working boxes, identifiers and no PDF embed',async()=>{
  const {getMonthlyAnswerSheet}=await import('../monthly-problems.mjs');
  const {buildAnswerPages}=await import('../sim/monthly-answer-sheet.mjs');
  for(const lang of ['ko','en']){
    const sheet=getMonthlyAnswerSheet(6),html=buildAnswerPages({id:6,no:3,title:'<script>bad</script>'},sheet,lang);
    assert.equal((html.match(/class="answer"/g)||[]).length,7);
    assert.equal((html.match(/class="working"/g)||[]).length,7);
    assert.equal((html.match(/class="paper"/g)||[]).length,3);
    assert.ok(html.includes('B.4'));assert.ok(html.includes('HL-MONTHLY-6'));
    assert.ok(html.includes('&lt;script&gt;'));assert.ok(!/<script|<iframe|\.pdf/i.test(html));
  }
});

test('the astronomy sheet prints letter labels while keeping existing answer and photo identifiers',async()=>{
  const {getMonthlyAnswerSheet,getMonthlyProblemRound}=await import('../monthly-problems.mjs');
  const {buildAnswerPages}=await import('../sim/monthly-answer-sheet.mjs');
  const problem={id:8,week:'2026-11',no:4,title:'Radiative equilibrium and precession of a disk'};
  const sheet=getMonthlyAnswerSheet(problem);
  assert.deepEqual(sheet.parts.map(p=>p.displayId),['a','b','c','d','e','f','g','h','i','j']);
  assert.deepEqual(sheet.parts.map(p=>p.id),['16','17','18','19','20a','20b','20c','21a','21b','21c']);
  for(const lang of ['ko','en']){
    const html=buildAnswerPages(problem,sheet,lang);
    assert.equal((html.match(/data-display-part="\([a-j]\)"/g)||[]).length,10);
    assert.ok(html.includes('data-part="16"'));assert.ok(html.includes('data-part="21c"'));
    assert.ok(!/소문항 (?:16|17|18|19|20|21)|Part (?:16|17|18|19|20|21)/.test(html));
  }
  assert.equal(getMonthlyProblemRound(problem),'theory');
  assert.equal(getMonthlyProblemRound({...problem,round:'experiment'}),'experiment');
  assert.equal(getMonthlyProblemRound({answerSheet:{round:'experiment'}}),'experiment');
});

test('native theory forms prompt for the actual outputs and keep all response cells blank',async()=>{
  const {getMonthlyAnswerSheet}=await import('../monthly-problems.mjs');
  for(const id of [4,5,6,7]){
    const sheet=getMonthlyAnswerSheet(id);
    for(const p of sheet.parts){
      assert.ok(p.results?.length,'each theory part names its requested outputs');
      for(const field of p.results){assert.ok(field.label_ko&&field.label_en);assert.ok(!('value'in field));assert.ok(!('answer'in field));}
    }
  }
  assert.deepEqual(getMonthlyAnswerSheet(4).parts.find(p=>p.id==='c').results.map(r=>r.label_ko),['허용 파수 q_s','ω(0)','ω_max','이웃 간 위상차']);
  assert.equal(getMonthlyAnswerSheet(6).parts.find(p=>p.id==='B.4').tables[0].rows.length,8);
  assert.equal(getMonthlyAnswerSheet(7).parts.find(p=>p.id==='21a').tables[0].rows.length,3);
  assert.equal(getMonthlyAnswerSheet(7).parts.find(p=>p.id==='21b').tables[0].rows.length,5);
  const mutable=getMonthlyAnswerSheet(6);mutable.parts[6].tables[0].columns[0].label_ko='mutated';mutable.parts[0].results[0].label_en='mutated';
  assert.notEqual(getMonthlyAnswerSheet(6).parts[6].tables[0].columns[0].label_ko,'mutated');
  assert.notEqual(getMonthlyAnswerSheet(6).parts[0].results[0].label_en,'mutated');
});

test('custom experiment worksheets render arbitrary blank data tables and real printable graph grids',async()=>{
  const {buildAnswerPages,buildResponseGraph}=await import('../sim/monthly-answer-sheet.mjs');
  const sheet={version:'review',pages:[['A.1']],parts:[{id:'A.1',label_ko:'측정',label_en:'Measurement',points:100,
    results:[{label_ko:'기울기',label_en:'Slope',unit:'m/s'}],
    tables:[{title_ko:'측정 자료',title_en:'Measured data',columns:[{label_ko:'횟수',label_en:'Trial'},{label_ko:'측정값',label_en:'Reading'}],rows:Array.from({length:3},()=>['',''])}],
    graphs:[{title_ko:'측정 그래프',title_en:'Measurement graph',x_label_ko:'x (m)',x_label_en:'x (m)',y_label_ko:'t (ms)',y_label_en:'t (ms)',columns:28,rows:20,heightMm:65}]}]};
  const html=buildAnswerPages({id:'draft-5',no:5,title:'실험'},sheet,'ko');
  assert.equal((html.match(/<tr>/g)||[]).length,4,'one heading row and three blank record rows');
  assert.equal((html.match(/<line /g)||[]).length,50,'the grid is printable vector ink rather than a CSS background');
  assert.match(html,/class="result-field"/);assert.match(html,/\[m\/s\]/);
  assert.match(html,/x \(m\)/);assert.match(html,/t \(ms\)/);
  assert.match(html,/data-part="A\.1"/);assert.match(html,/HL-MONTHLY-draft-5/);
  const escaped=buildResponseGraph({title_en:'<script>',x_label_en:'<x>',y_label_en:'&y',heightMm:Infinity,columns:NaN,rows:Infinity},'en');
  assert.match(escaped,/&lt;script&gt;/);assert.match(escaped,/&lt;x&gt;/);assert.match(escaped,/&amp;y/);
  assert.ok(!/Infinity|NaN|<script/.test(escaped));
});

test('the printable browser entry resolves a native answer sheet after fetching its actual database ID',async()=>{
  const nodes=Object.fromEntries(['back','print','message','help','sheets'].map(id=>[id,{textContent:'',innerHTML:'',hidden:false,disabled:true,addEventListener(){}}]));
  const previous={document:global.document,location:global.location,fetch:global.fetch};
  global.document={documentElement:{},getElementById:id=>nodes[id]};global.location={search:'?id=8&lang=ko'};
  global.fetch=async url=>{assert.match(url,/\/problems\/8\?lang=ko$/);return Response.json({problem:{id:8,no:4,week:'2026-11',title:'원판 모형의 복사 평형과 세차'}});};
  try{
    await import('../sim/monthly-answer-sheet.mjs?case=actual-id8');
    for(let i=0;i<5&&nodes.print.disabled;i++)await new Promise(resolve=>setImmediate(resolve));
    assert.equal(nodes.print.disabled,false);assert.ok(nodes.sheets.innerHTML.includes('data-display-part="(a)"'));
    assert.ok(nodes.sheets.innerHTML.includes('HL-MONTHLY-8'));
  }finally{for(const [key,value]of Object.entries(previous)){if(value===undefined)delete global[key];else global[key]=value;}}
});

test('every A4 page has four printable black corner marks with white quiet zones',async()=>{
  const {getMonthlyAnswerSheet}=await import('../monthly-problems.mjs');
  const {buildAnswerPages}=await import('../sim/monthly-answer-sheet.mjs');
  for(const id of [4,5,6,7]) for(const lang of ['ko','en']){
    const sheet=getMonthlyAnswerSheet(id),html=buildAnswerPages({id,no:id-3,title:'Corner-mark check'},sheet,lang);
    const pages=html.split('<section class="paper"').slice(1);
    assert.equal(pages.length,sheet.pages.length);
    for(const page of pages){
      const markers=[...page.matchAll(/<span class="scan-mark" data-scan-corner="([^"]+)" aria-hidden="true">([\s\S]*?)<\/span>/g)];
      assert.deepEqual(markers.map(m=>m[1]),['tl','tr','bl','br']);
      for(const marker of markers){
        assert.match(marker[2],/viewBox="0 0 10 10"/);
        assert.match(marker[2],/<rect width="10" height="10" fill="#fff"\/>/);
        assert.match(marker[2],/<rect x="2" y="2" width="6" height="6" fill="#000"\/>/);
        assert.ok(!/<image|href=|foreignObject|onload=|script/i.test(marker[2]));
      }
    }
  }
});

test('corner geometry matches scanner calibration and keeps clear of A4 writing areas and narrow previews',async()=>{
  const html=fs.readFileSync(path.join(root,'sim/monthly-answer-sheet.html'),'utf8');
  const scannerSource=fs.readFileSync(path.join(root,'sim/labscan/scanner.js'),'utf8');
  const {MARKER_INSET}=await import('data:text/javascript;base64,'+Buffer.from(scannerSource).toString('base64'));
  assert.match(html,/\.paper\{position:relative\}/);
  assert.match(html,/width:4\.76190476%;height:3\.36700337%/);
  assert.match(html,/top:1\.81649832%/);assert.match(html,/bottom:1\.81649832%/);
  assert.match(html,/left:2\.11904762%/);assert.match(html,/right:2\.11904762%/);
  assert.match(html,/print-color-adjust:exact;-webkit-print-color-adjust:exact/);
  assert.match(html,/@page\{size:A4;margin:0\}/);
  // Percentages yield 10 mm quiet zones at the existing scanner's marker centres.
  const width=210*4.76190476/100,height=297*3.36700337/100,left=210*2.11904762/100,top=297*1.81649832/100;
  for(const value of [width,height])assert.ok(Math.abs(value-10)<1e-6);
  const x=(left+width/2)/210,y=(top+height/2)/297;
  assert.ok(Math.abs(x-MARKER_INSET.left)<1e-8);
  assert.ok(Math.abs(1-x-MARKER_INSET.right)<1e-8);
  assert.ok(Math.abs(y-MARKER_INSET.top)<1e-8);
  assert.ok(Math.abs(1-y-MARKER_INSET.bottom)<1e-8);
  assert.ok(left+width<15,'entire white quiet zone stays outside the 15 mm side content padding');
  assert.ok(left+2>=5&&top+2>=5,'black ink clears the usual 5 mm printer margins');
  for(const rect of [{x:left,y:top},{x:210-left-width,y:top},{x:left,y:297-top-height},{x:210-left-width,y:297-top-height}]){
    assert.ok(rect.x>=0&&rect.y>=0&&rect.x+width<=210&&rect.y+height<=297);
    assert.ok(rect.x+width<15||rect.x>195||rect.y+height<13||rect.y>284,'each quiet zone clears the complete writing rectangle');
  }
  for(const viewport of [320,390,600,820]){
    const paperWidth=viewport-24,quietZoneEnd=paperWidth*(left+width)/210;
    assert.ok(viewport*.072>quietZoneEnd,'mobile side clearance');
  }
  assert.match(html,/padding:6\.2vw 7\.2vw/);
});

test('the monthly experiment resolves by stable identity at any database ID without claiming unrelated records',async()=>{
  const {getMonthlyAnswerSheet,getMonthlyProblemRound}=await import('../monthly-problems.mjs');
  const base={week:'2026-11',no:5,title:'압력파를 이용한 관의 내부 지름 측정'};
  for(const id of [7,8,413]){
    const sheet=getMonthlyAnswerSheet({...base,id});
    assert.equal(sheet.key,'pressure-wave-experiment-v1');
    assert.equal(sheet.version,'2026-11-pressure-wave-v1');
    assert.equal(sheet.round,'experiment');assert.equal(sheet.limit,3);
    assert.equal(sheet.experimentUrl,'/sim/monthly-pressure-wave/index.html');
    assert.equal(getMonthlyProblemRound({...base,id}),'experiment');
  }
  for(const period of ['week','period','month']){
    const problem={id:22,[period]:'2026-11',no:'5',title:'Other title',source:'HaslaLab · pressure-wave-experiment-v1'};
    assert.equal(getMonthlyAnswerSheet(problem).key,'pressure-wave-experiment-v1');
  }
  assert.equal(getMonthlyAnswerSheet({id:8,week:'2026-11',no:5,title_en:'Measuring the internal diameter of a pipe with pressure waves'}).round,'experiment');
  assert.equal(getMonthlyAnswerSheet({id:7,month:'2026-11',no:5,answerSheet:{key:'pressure-wave-experiment-v1'}}).round,'experiment');
  for(const id of [7,8,413])assert.equal(getMonthlyAnswerSheet({id,week:'2026-11',no:5,title:'Unrelated problem'}),null);
  assert.equal(getMonthlyAnswerSheet({...base,id:8,no:4}),null);
  assert.equal(getMonthlyAnswerSheet({...base,id:8,week:'2026-12'}),null);
  assert.equal(getMonthlyAnswerSheet(8),null,'a new database number alone does not identify the experiment');
  assert.equal(getMonthlyAnswerSheet(5).parts[0].id,'a','legacy problem 2 is unchanged');
});

test('published experiment metadata contains blank forms linked to canonical rubric parts, not private answers',async()=>{
  const {getMonthlyAnswerSheet}=await import('../monthly-problems.mjs');
  const problem={id:817,week:'2026-11',no:5,source:'HaslaLab · pressure-wave-experiment-v1'};
  const sheet=getMonthlyAnswerSheet(problem);
  const seeded=JSON.parse(fs.readFileSync(path.join(root,'community/weekly/2026-11-pressure-wave.json'),'utf8')).problems[0];
  assert.deepEqual(sheet.parts.map(p=>p.id),['A.1','A.2','B.1','B.2','B.3','C.1','C.2']);
  assert.deepEqual(sheet.pages,sheet.parts.map(p=>[p.id]));assert.equal(sheet.pages.length,7);
  assert.equal(sheet.parts.reduce((sum,p)=>sum+p.points,0),100);
  for(const p of sheet.parts){
    const criteria=seeded.rubric.filter(row=>row.id.startsWith(p.id+'.'));
    assert.ok(criteria.length>0,'canonical rubric covers '+p.id);
    assert.equal(criteria.reduce((sum,c)=>sum+c.max,0),p.points);
    for(const field of p.results){assert.ok(field.label_ko&&field.label_en);assert.ok(!('value'in field));}
  }
  const json=JSON.stringify(sheet);
  for(const forbidden of ['requirement','reference','hidden','expected','repeat_credit','minimum_repeats','D0_m','c_m_s'])assert.ok(!json.includes('"'+forbidden+'"'));
  assert.ok(!/최소\s*7|7회|7개|적어도|at least|minimum number/i.test(json));
  assert.match(sheet.instructions_ko,/빈칸은 측정 횟수를 뜻하지/);
  assert.match(sheet.instructions_ko,/CSV.*선택/);
  for(const lang of ['ko','en'])assert.match(sheet.parts.find(p=>p.id==='A.2').tables[0]['title_'+lang],/\$2\\,\\mathrm\{ms\}\$/,'initial acquisition uses the closure valid throughout the model range');
  assert.deepEqual(sheet.parts.find(p=>p.id==='C.2').tables[0].rows.map(row=>row[0]),['2','5','10','20','50'],'candidate 5 ms remains available for valid models');
  const mutable=getMonthlyAnswerSheet(problem);mutable.parts[0].tables[0].columns[0].label_ko='mutated';mutable.pages[0][0]='mutated';
  assert.notEqual(getMonthlyAnswerSheet(problem).parts[0].tables[0].columns[0].label_ko,'mutated');
  assert.equal(getMonthlyAnswerSheet(problem).pages[0][0],'A.1');
});

test('experiment labels are valid LaTeX and remain escaped until the explicit browser render step',async()=>{
  const {getMonthlyAnswerSheet}=await import('../monthly-problems.mjs');
  const {buildAnswerPages,renderAnswerSheetMath}=await import('../sim/monthly-answer-sheet.mjs');
  const katex=require('../vendor/katex/katex.min.js');
  const problem={id:817,week:'2026-11',no:5,title:'압력파를 이용한 관의 내부 지름 측정'};
  const sheet=getMonthlyAnswerSheet(problem);
  let mathCount=0;
  function check(value){
    if(typeof value==='string'){
      const pieces=value.split('$');assert.equal(pieces.length%2,1,'paired inline delimiters');
      for(let i=1;i<pieces.length;i+=2){katex.renderToString(pieces[i],{throwOnError:true,trust:false,strict:'error'});mathCount++;}
    }else if(value&&typeof value==='object')for(const item of Object.values(value))check(item);
  }
  check(sheet);assert.ok(mathCount>100);
  const previous=global.renderMathInElement,calls=[];
  global.renderMathInElement=(element,options)=>calls.push({element,options});
  try{
    const html=buildAnswerPages({...problem,title:'<script>alert(1)</script>'},sheet);
    assert.equal(calls.length,0,'HTML construction is pure and does not typeset or execute content');
    assert.equal((html.match(/class="paper"/g)||[]).length,7);
    assert.equal((html.match(/data-scan-corner=/g)||[]).length,28);
    assert.match(html,/class="graph-math-plane"/);
    assert.match(html,/class="graph-x-label"/);assert.match(html,/class="graph-y-label"/);
    assert.ok(html.includes('&lt;script&gt;'));assert.ok(!/<script|<iframe|foreignObject/.test(html));
    const node={};renderAnswerSheetMath(node);assert.equal(calls[0].element,node);
    assert.equal(calls[0].options.trust,false);assert.equal(calls[0].options.throwOnError,false);
    assert.ok(calls[0].options.delimiters.some(d=>d.left==='$'&&d.right==='$'));
  }finally{if(previous===undefined)delete global.renderMathInElement;else global.renderMathInElement=previous;}
  const entry=fs.readFileSync(path.join(root,'sim/monthly-answer-sheet.html'),'utf8');
  assert.match(entry,/vendor\/katex\/katex\.min\.css/);assert.match(entry,/vendor\/katex\/katex\.min\.js/);assert.match(entry,/vendor\/katex\/contrib\/auto-render\.min\.js/);
});

test('the printable experiment fetches its actual database record and typesets the seven-page form',async()=>{
  const previous={document:global.document,location:global.location,fetch:global.fetch,renderMathInElement:global.renderMathInElement};
  try{
    for(const id of [7,8,413]){
      const nodes=Object.fromEntries(['back','print','message','help','sheets'].map(key=>[key,{textContent:'',innerHTML:'',hidden:false,disabled:true,addEventListener(){}}]));
      const rendered=[];
      global.document={documentElement:{},getElementById:key=>nodes[key]};global.location={search:`?id=${id}&lang=en`};
      global.fetch=async url=>{assert.match(url,new RegExp(`/problems/${id}\\?lang=en$`));return Response.json({problem:{id,week:'2026-11',no:5,title:'Measuring the internal diameter of a pipe with pressure waves'}});};
      global.renderMathInElement=(element,options)=>rendered.push({element,options});
      await import('../sim/monthly-answer-sheet.mjs?case=experiment-id'+id);
      for(let i=0;i<5&&nodes.print.disabled;i++)await new Promise(resolve=>setImmediate(resolve));
      assert.equal(nodes.print.disabled,false);assert.equal(nodes.message.hidden,true);
      assert.equal((nodes.sheets.innerHTML.match(/class="paper"/g)||[]).length,7);
      assert.ok(nodes.sheets.innerHTML.includes('HL-MONTHLY-'+id));
      assert.equal(rendered.length,1);assert.equal(rendered[0].element,nodes.sheets);
      assert.equal(rendered[0].options.trust,false);
    }
  }finally{for(const [key,value]of Object.entries(previous)){if(value===undefined)delete global[key];else global[key]=value;}}
});
