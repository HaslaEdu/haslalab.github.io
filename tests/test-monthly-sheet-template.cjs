const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..');
test('every actual subquestion has exactly one answer-sheet slot and its web points total 100',async()=>{
  const {getMonthlyAnswerSheet}=await import('../monthly-problems.mjs');
  const source=JSON.parse(fs.readFileSync(path.join(root,'community/weekly/2026-W44.json'),'utf8')).problems;
  for(const [index,id,count]of [[0,4,10],[1,5,5],[2,6,7]]){
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
