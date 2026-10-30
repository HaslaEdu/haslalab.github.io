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

test('custom experiment worksheets render seven-row measurement tables and real printable graph grids',async()=>{
  const {buildAnswerPages,buildResponseGraph}=await import('../sim/monthly-answer-sheet.mjs');
  const sheet={version:'review',pages:[['A.1']],parts:[{id:'A.1',label_ko:'측정',label_en:'Measurement',points:100,
    results:[{label_ko:'기울기',label_en:'Slope',unit:'m/s'}],
    tables:[{title_ko:'7회 반복 측정',title_en:'Seven repeated measurements',columns:[{label_ko:'횟수',label_en:'Trial'},{label_ko:'측정값',label_en:'Reading'}],rows:Array.from({length:7},(_,i)=>[String(i+1),''])}],
    graphs:[{title_ko:'측정 그래프',title_en:'Measurement graph',x_label_ko:'x (m)',x_label_en:'x (m)',y_label_ko:'t (ms)',y_label_en:'t (ms)',columns:28,rows:20,heightMm:65}]}]};
  const html=buildAnswerPages({id:'draft-5',no:5,title:'실험'},sheet,'ko');
  assert.equal((html.match(/<tr>/g)||[]).length,8,'one heading row and seven blank measurement rows');
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
