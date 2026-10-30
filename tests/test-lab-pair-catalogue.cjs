const test=require('node:test'),assert=require('node:assert/strict');
const {buildPairCatalogue}=require('../tools/lab-pair-catalogue.cjs');
const file=(extra={})=>({paper:'official-paper.pdf',sol:'official-solution.pdf',...extra});
const experiment=(id,extra={})=>({id,files:{sim:'sim/official_web.html'},...extra});
function build({files,problems,theory,lab,rounds=false,publishedParts}){
  const year={y:2025,problems};
  return buildPairCatalogue({test:{rounds,years:[year]}},{
    thyOf:()=>({f:files}),theoryGroups:()=>theory,examGroups:()=>lab,examTask:problem=>problem.id,officialTheoryParts:()=>publishedParts
  }).test?.['2025']||[];
}

test('only complete supported rounds form a pair; missing, simulated or split tasks cannot lower the price',()=>{
  const e1=experiment('E1'),e2=experiment('E2');
  const input={files:{T1:file(),T2:file(),T3:file()},problems:[e1,e2],theory:[['T1','T2','T3']],lab:[[e1,e2]]};
  assert.deepEqual(build(input),[{id:'default',theory:[['T1','T2','T3']],lab:[['E1','E2']]}]);
  assert.deepEqual(build({...input,theory:[['T2','T3']]}),[],'a simulated theory problem still belongs to the full round');
  assert.deepEqual(build({...input,lab:[[e1]]}),[],'an unavailable experiment still belongs to the full round');
  assert.deepEqual(build({...input,files:{...input.files,T4:file(),T5:file()},theory:[['T1','T2','T3','T4'],['T5']]}),[]);
  assert.deepEqual(build({...input,files:{T:file(),T1:file(),T2:file(),T3:file(),T4:file(),T5:file()},theory:[['T']]}),
    [{id:'default',theory:[['T']],lab:[['E1','E2']]}],'a supported whole paper covers its complete round without partial extrapolation');
  assert.deepEqual(build({...input,lab:[[e1,{...e2,thy:true}]]}),[],'an already combined sitting cannot become a discounted counterpart');
  assert.deepEqual(build({...input,rounds:true}),[],'separate national rounds need an explicit unambiguous shared identity');
  assert.deepEqual(build({...input,files:{T1:file(),T2:file(),T3:file({paper:''})}}),[]);
  assert.deepEqual(build({...input,files:{...input.files,T4:file({sol:null})},publishedParts:['T1','T2','T3']}),
    [{id:'default',theory:[['T1','T2','T3']],lab:[['E1','E2']]}],'a separately archived backup problem is not an official sitting task');
});

test('age/stage profiles never pair a theory paper with another stage or an unrelated practical simulator',()=>{
  const ea=experiment('Ea'),eb=experiment('Eb');
  const input={files:{Ta:file(),Tb:file()},problems:[ea,eb],theory:[['Ta'],['Tb']],lab:[[ea],[eb]]};
  assert.deepEqual(build(input),[
    {id:'a',theory:[['Ta']],lab:[['Ea']]},
    {id:'b',theory:[['Tb']],lab:[['Eb']]}
  ]);
  assert.deepEqual(build({...input,theory:[['Ta']],lab:[[eb]]}),[]);
  assert.deepEqual(build({...input,theory:[['Ta','Tb']]}),[]);
  for(const id of ['D1','O1','G1']){
    const practical=experiment(id);
    assert.deepEqual(build({files:{T:file()},problems:[practical],theory:[['T']],lab:[[practical]]}),[]);
  }
  assert.deepEqual(build({files:{T:file(),MC:file()},problems:[experiment('E1')],theory:[['T'],['MC']],lab:[[experiment('E1')]]}),[],
    'two distinct full theory families cannot silently become interchangeable counterparts');
});

test('generated backend pairs preserve complete IPhO sittings and omit known partial or already combined years',async()=>{
  const {LAB_PAIR_CATALOGUE:catalogue}=await import('../community/src/lab-pair-catalog.js');
  assert.deepEqual(catalogue.ipho['2025'],[{id:'default',theory:[['T1','T2','T3']],lab:[['E1','E2']]}]);
  assert.deepEqual(catalogue.ispho['2026'],[{id:'default',theory:[['T']],lab:[['E1']]}]);
  for(const year of ['2023','2024','2025'])assert.equal(catalogue.ispho[year],undefined,'ISPhO simulation-excluded theory is incomplete');
  assert.equal(catalogue.nbpho,undefined,'NBPhO already combines its theory and experiment');
  assert.equal(catalogue.ioaa,undefined,'individual observation/data analysis/team simulators are not the complete practical round');
  assert.equal(catalogue.opho['2025'].some(profile=>profile.id==='i'),false,'a missing international theory part must not qualify');
  for(const years of Object.values(catalogue))for(const profiles of Object.values(years)){
    assert.equal(new Set(profiles.map(profile=>profile.id)).size,profiles.length);
    for(const profile of profiles)for(const scope of ['theory','lab'])for(const tasks of profile[scope]){
      assert.ok(tasks.length>0&&tasks.length<=4);
      assert.equal(new Set(tasks).size,tasks.length);
    }
  }
});

test('canonical mixed catalogue distinguishes complete NBPhO editions from partial or separately paired rounds',async()=>{
  const {LAB_MIXED_CATALOGUE:mixed,LAB_PAIR_CATALOGUE:pairs}=await import('../community/src/lab-pair-catalog.js');
  assert.deepEqual(mixed.nbpho['2026'],[['E1','E2','T']]);
  assert.deepEqual(mixed.nbpho['2003'],[['E1','T']],'single-experiment editions have a distinct complete identity');
  assert.deepEqual(mixed.nbpho['2009'],[['E1','E2','E3','T']],'the four-task bound includes three experiments plus theory');
  assert.equal(pairs.nbpho,undefined,'mixed sittings never get a second complementary-round discount');
  assert.equal(mixed.ipho,undefined,'a client claiming mixed mode does not create an official mixed sitting');
  for(const [comp,years]of Object.entries(mixed))for(const [year,sets]of Object.entries(years)){
    assert.equal(new Set(sets.map(tasks=>tasks.join('|'))).size,sets.length,`${comp}/${year}`);
    for(const tasks of sets){
      assert.ok(tasks.length>1&&tasks.length<=4);
      assert.equal(new Set(tasks).size,tasks.length);
      assert.ok(tasks.includes('T'),'theory must remain part of the exact canonical task set regardless of client kind metadata');
      assert.ok(tasks.some(task=>/^E\d+$/.test(task)));
    }
  }
});
