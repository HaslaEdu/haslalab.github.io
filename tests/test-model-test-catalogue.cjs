const test=require('node:test'),assert=require('node:assert/strict');
const {buildModelTestCatalogue,source}=require('../tools/model-test-catalogue.cjs');
const build=(data,options={})=>buildModelTestCatalogue(data,{thyOf:()=>null,theoryGroups:()=>[],examGroups:()=>[],examTask:p=>p.id,...options});

test('developer source records reject credentials, traversal, local networks and unsupported URL schemes',()=>{
  for(const value of ['file:///secret.pdf','http://official.org/paper.pdf','https://user:secret@official.org/paper.pdf','https://127.0.0.1/p.pdf','https://2130706433/p.pdf','https://[::1]/p.pdf','https://foo.internal/p.pdf','pdfx/ipho/../secret.pdf','IPhO_../secret.pdf'])assert.equal(source(value),null,value);
  assert.equal(source('https://haslalab-pdf.haslalab.workers.dev/pdf/IPhO_2024_T1_EN.pdf'),'IPhO_2024_T1_EN.pdf');
  assert.equal(source('https://haslalab.org/pdfx/ipho/IPhO_2024_T1.pdf'),'pdfx/ipho/IPhO_2024_T1.pdf');
  assert.equal(source('https://official.org/download.php?id=paper.pdf'),'https://official.org/download.php?id=paper.pdf');
});

test('theory choices preserve original context, translated viewing paper and explicit booklet exclusions',()=>{
  const data={test:{abbr:'Test',years:[{y:2025,problems:[]}]}};
  const result=build(data,{thyOf:()=>({f:{T1:{paper:'Test_2025_T1.pdf',sol:'Test_2025_T1S.pdf',mark:'Test_2025_T1M.pdf',ko:{paper:'Test_2025_T1_KO.pdf'}},T2:{paper:'Test_2025_T2_KO.pdf',kx:true}},p:[['T1','First problem']],pk:[['T1','첫 문제']]})});
  assert.equal(result.length,1);assert.equal(result[0].paper,'Test_2025_T1.pdf');assert.equal(result[0].paperKo,'Test_2025_T1_KO.pdf');assert.equal(result[0].title.ko,'첫 문제');assert.equal(result[0].mark,'Test_2025_T1M.pdf');assert.equal(result[0].wholePaper,false);
  const nb=build({nbpho:{years:[{y:2026,problems:[]}]}},{thyOf:()=>({x:[2,6],f:{T:{paper:'NBPhO_2026_T_EN.pdf',sol:'NBPhO_2026_TS.pdf'}}})});
  assert.deepEqual(nb[0].skip,['2','6']);assert.equal(nb[0].wholePaper,true);
});

test('experiment choices use the portal grouping and retain an explicit problem number',()=>{
  const problem={id:'E1',no:6,title:{ko:'실험',en:'Experiment'},files:{pdf:{en:'Test_2025_E1_EN.pdf',ko:'Test_2025_E1_KO.pdf'},sol:'Test_2025_E1S.pdf'}};
  const entries=build({test:{years:[{y:2025,problems:[problem]}]}},{examGroups:()=>[[problem]]});
  assert.equal(entries.length,1);assert.equal(entries[0].problemNo,6);assert.equal(entries[0].kind,'experiment');assert.equal(entries[0].paperKo,'Test_2025_E1_KO.pdf');
});

test('a division code such as AMC T8 selects its complete paper rather than problem eight',()=>{
  const entries=build({amc:{rounds:true,years:[{y:2026,problems:[]}]}},{thyOf:()=>({f:{T8:{paper:'AMC_2026_T8.pdf',sol:'AMC_2026_T8S.pdf'}},p:[['T8','AMC 8']]})});
  assert.equal(entries[0].task,'T8');assert.equal(entries[0].wholePaper,true);assert.equal(entries[0].title.en,'AMC 8');
});

test('different logical sittings sharing one PDF keep separate IDs and question ranges',()=>{
  const entries=[0,10].map((offset,i)=>({id:'kmo-2022-T1-s'+(i+1),comp:'kmo',year:2022,part:'T1',paper:'https://official.org/combined.pdf',questions:10,questionOffset:offset,title:'Session '+(i+1),practice:true}));
  const result=build({kmo:{years:[]}},{contests:{entries}});
  assert.equal(result.length,2);assert.notEqual(result[0].id,result[1].id);assert.equal(result[0].paper,result[1].paper);
  assert.deepEqual(result.find(e=>e.id.endsWith('s1')).questionNumbers,[1,2,3,4,5,6,7,8,9,10]);
  assert.deepEqual(result.find(e=>e.id.endsWith('s2')).questionNumbers,[11,12,13,14,15,16,17,18,19,20]);
});

test('generated selections connect real archive papers without treating missing or independent solutions as official',async()=>{
  const {MODEL_TEST_EXAMS:entries}=await import('../community/src/model-test-catalog.js');
  assert.equal(new Set(entries.map(e=>e.id)).size,entries.length);
  const ipho=entries.find(e=>e.id==='ipho-2024-T1');assert.equal(ipho.paper,'IPhO_2024_T1_EN.pdf');assert.equal(ipho.solution,'IPhO_2024_T1S.pdf');assert.equal(ipho.mark,'IPhO_2024_T1M.pdf');
  const latest=entries.find(e=>e.id==='ipho-2026-T');assert.equal(latest.wholePaper,true);assert.equal(latest.referenceStatus,'problem-only');
  assert.ok(entries.some(e=>e.comp==='kphe'&&e.year==='2026-2'&&e.referenceStatus==='independent'));
  const early=entries.find(e=>e.id==='kmo-2022-T1-s1'),late=entries.find(e=>e.id==='kmo-2022-T1-s2');assert.equal(early.paper,late.paper);assert.deepEqual(late.questionNumbers,[11,12,13,14,15,16,17,18,19,20]);
  const chem=entries.find(e=>e.id==='kmchc-2026-2-general');assert.equal(chem.verifiedScoring.questions,50);assert.equal(chem.verifiedScoring.point,3);assert.equal(chem.verifiedScoring.penalty,1);
  assert.equal(entries.find(e=>e.id==='amc-2026-T8').wholePaper,true);
  assert.ok(!entries.some(e=>e.comp==='ioi'),'programming tasks are not written-answer model tests');
  for(const entry of entries)for(const key of ['paper','paperKo','solution','mark'])if(entry[key])assert.ok(source(entry[key]),entry.id+' '+key);
});
