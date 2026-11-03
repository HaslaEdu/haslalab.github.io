const assert=require('node:assert/strict');
const path=require('node:path');

module.exports=function validateIChO2019Final(qa,item,read) {
  assert.equal(item.file,'IChO_2019_T_KO.pdf');
  assert.equal(qa.pages,60);
  const source='5821bab3b65b216cc74df99d7ec643389d212c15b4d88c95a7da22de8baf97d8';
  assert.equal(qa.source_sha256,source);
  const evidence=(name,digest)=>{
    const pins=(qa.supplemental_evidence||[]).filter(p=>p.path.endsWith('/'+name));
    assert.equal(pins.length,1,'Missing or duplicate final IChO2019 evidence: '+name);
    assert.equal(pins[0].sha256,digest);
    return read(pins[0].path,digest);
  };
  const ready=evidence('READY-for-root-assembly-r2.json','e7ac28136d66573a9674322876b08458ef0165dcf0e3aab2a682cf48665b6737');
  const freeze=evidence('final-code-freeze-r2.json','81156ebe66c0872dd0301e5a22d0b72f8e29dd8ba56ed3eae60b87d3422ba49a');
  for(const [name,digest] of [
    ['final-r2-page53-semantics-amendment.json','95f51bb3527ea0f83202c4c071e01b884a09369c615b7de5cd628896b3083f39'],
    ['final-r2-source-checkbox-columns-amendment.json','22eebd85186fae16a0c31ad8d3b23e8e67d5f015e2efd7eddbf730a0694faee7'],
    ['final-r2-page51-second-answer-row-amendment.json','cd50b0b21e8fba85c47bc79923453aab684d379676830d61c2ae98aa7e45a9f2'],
    ['final-r2-page54-starting-compound-amendment.json','fc26e9089730d02d6c03c7f052b194c6c5366548267ead8a2faba220250b8475']]) {
    const document=evidence(name,digest);
    assert.equal(document.source_sha256,source);
    assert.equal(document.base_freeze_sha256,'81156ebe66c0872dd0301e5a22d0b72f8e29dd8ba56ed3eae60b87d3422ba49a');
  }
  assert.equal(ready.status,'READY_FOR_ROOT_ASSEMBLY');assert.equal(ready.pages,60);
  assert.equal(ready.source.sha256,source);assert.equal(freeze.source_sha256,source);
  assert.equal(freeze.files.length,197);
  const programs=freeze.files.filter(p=>p.path.endsWith('.py'));
  assert.equal(programs.length,69);
  for(const program of programs) {
    const name=path.win32.basename(program.path.replaceAll('/','\\'));
    assert.ok(qa.authoring_programs.some(p=>p.path.endsWith('/'+name)&&p.sha256===program.sha256),'Changed frozen producer: '+name);
  }
  assert.equal(ready.actual_changed_R2_inputs.length,6);
  const expectedPages=[13,45,46,51,53,54];
  const changedPages=[];
  for(const changed of ready.actual_changed_R2_inputs) {
    const name=path.win32.basename(changed.path.replaceAll('/','\\'));
    const number=Number(/^page(\d+)\.overrides\.json$/.exec(name)[1]);
    changedPages.push(number);
    const original=freeze.files.find(p=>p.path.replaceAll('\\','/')===changed.path.replaceAll('\\','/'));
    assert.ok(original);assert.equal(original.sha256,changed.before_sha256);
    assert.equal(qa.page_audits[number-1].overrides_sha256,changed.after_sha256);
  }
  assert.deepEqual(changedPages,expectedPages);
  assert.equal(ready.page_artifacts.length,60);
  for(const [i,row]of ready.page_artifacts.entries()) {
    const page=qa.page_audits[i];
    assert.equal(row.page,i+1);assert.equal(row.passed,true);
    for(const [suffix,field]of [['.pdf','proof_sha256'],['.layout.json','qa_sha256'],['.effective-plan.json','effective_plan_sha256']]) {
      const pins=row.artifacts.filter(p=>p.path.endsWith(suffix));
      assert.equal(pins.length,1);assert.equal(pins[0].sha256,page[field]);
    }
  }
};
