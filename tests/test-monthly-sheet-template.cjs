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
