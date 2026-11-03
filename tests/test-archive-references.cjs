const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const file=path.resolve(__dirname,'../archive-reference-media.js');
const code=fs.readFileSync(file,'utf8').replace(/^export /gm,'');
const references=vm.runInNewContext(code+'\nARCHIVE_BOOK_REFERENCES');
const expected=new Map([
  ['goldstein-classical-mechanics','https://www.pearson.com/en-us/subject-catalog/p/Goldstein-Classical-Mechanics-3rd-Edition/P200000006871?view=educator'],
  ['kzhou-handouts','https://knzhou.github.io/teaching/'],
  ['feynman-1','https://www.feynmanlectures.caltech.edu/I_toc.html'],
  ['feynman-2','https://www.feynmanlectures.caltech.edu/II_toc.html'],
  ['feynman-3','https://www.feynmanlectures.caltech.edu/III_toc.html']
]);

test('external book references point to five distinct verified primary pages without inventing source IDs or question counts',()=>{
  assert.equal(references.length,5);const ids=new Set(),urls=new Set();
  for(const item of references){
    assert.match(item.id,/^[a-z][a-z0-9-]+$/);assert(!ids.has(item.id));ids.add(item.id);
    assert.equal(item.href,expected.get(item.id));const url=new URL(item.href);assert.equal(url.protocol,'https:');assert(!urls.has(url.href));urls.add(url.href);
    assert.equal(item.collection,'physics');assert(item.author&&item.short_title);
    for(const key of ['title','full_title','topic_label'])for(const lang of ['ko','en'])assert.equal(typeof item[key][lang],'string');
    assert(['textbook','handouts','lectures'].includes(item.resource_kind));
    assert(['official_online','digitization_pending'].includes(item.availability));
    assert.doesNotMatch(JSON.stringify(item),/src_[a-f0-9]{64}|question_count|solution_count|digital_question|source_id|canonical_id|drive\.google\.com|(?:^|["'\s])[A-Z]:[\\/]|file:\/\/|OneDrive|\.codex-remote-attachments/i);
    assert.equal(item.image_url,undefined,'no unverified or fabricated reference cover');
  }
  assert.equal(ids.size,expected.size);assert(Object.isFrozen(references));
});

test('Feynman references are separate Caltech lecture volumes with the correct subjects and current authorship',()=>{
  const volumes=references.filter(item=>item.id.startsWith('feynman-'));
  assert.equal(volumes.length,3);
  assert.deepEqual(Array.from(volumes,item=>item.topic_label.en),['Mechanics, radiation and heat','Electromagnetism and matter','Quantum mechanics']);
  for(const item of volumes){assert.equal(item.availability,'official_online');assert.equal(item.resource_kind,'lectures');assert.match(item.author,/Feynman.*Leighton.*Sands/);assert.match(item.full_title.en,/The Feynman Lectures on Physics, Volume I{1,3}/);}
});

test('Goldstein remains marked pending digitization and Kevin Zhou links to his actual teaching and handout index',()=>{
  const goldstein=references.find(item=>item.id==='goldstein-classical-mechanics'),kzhou=references.find(item=>item.id==='kzhou-handouts');
  assert.equal(goldstein.availability,'digitization_pending');assert.equal(goldstein.resource_kind,'textbook');assert.match(goldstein.author,/Goldstein.*Poole.*Safko/);
  assert.equal(kzhou.availability,'official_online');assert.equal(kzhou.resource_kind,'handouts');assert.equal(kzhou.author,'Kevin Zhou');
});
