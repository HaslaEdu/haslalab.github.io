const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const Core = require('../sim/contest-core.js');
const scope = {window:{}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../theory.js'),'utf8'),scope);
const originalTheory=JSON.parse(JSON.stringify(scope.window.THEORY));
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../contest-exams.js'),'utf8'),scope);
const data = JSON.parse(JSON.stringify(scope.window.CONTEST_EXAMS));
const entries = data.entries;
const find = id => entries.find(e=>e.id===id);

test('every public chemistry paper and every KMO source part has an official link and practice entry',()=>{
  const chem = require('../data/research/kmchc-research.json');
  const kmo = require('../tools/theory/kmo.json');
  assert.equal(entries.filter(e=>e.comp==='kmchc'&&e.sourceType!=='reprint').length,chem.validation.exam_entries);
  for(const year of kmo.years) for(const paper of year.files.filter(f=>f.kind==='paper')) {
    assert.ok(entries.some(e=>e.comp==='kmo'&&e.year===year.y&&e.part===paper.part),`${year.y} ${paper.part}`);
  }
  assert.equal(new Set(entries.map(e=>e.id)).size,entries.length);
  for(const e of entries) {
    if(e.sourceType==='reprint') {
      assert.equal(e.year,2009);assert.equal(e.comp,'kmchc');assert.equal(e.answersVerified,false);
      assert.equal(new URL(e.paper).hostname,'cfile223.uf.daum.net');
    } else assert.match(new URL(e.paper).hostname,/^(www\.)?(kms\.or\.kr|kmo\.or\.kr)$|^olympiad\.kchem\.org$/);
    assert.ok(e.sources.length>0);
    if(e.practice!==false) assert.ok(Core.ready(e),e.id);
    if(e.answersVerified) assert.ok(Core.hasKey(e),e.id);
  }
});

test('all verified keys accept a perfect sheet, including corrections, alternative answers and all-candidate credit',()=>{
  for(const e of entries.filter(e=>e.answersVerified)) {
    const marks=Object.fromEntries(e.answers.map((answer,i)=>[i+1,Array.isArray(answer)?answer.at(-1):answer]));
    const grade=Core.grade(e,marks);
    assert.equal(grade.wrong,0,e.id);
    assert.equal(grade.blank,0,e.id);
    assert.equal(grade.correct,e.questions-(e.excluded||[]).length,e.id);
    if(grade.weighted) assert.equal(grade.score,grade.total,e.id);
  }
});

test('chemistry historical no-penalty online sessions differ from current OMR scoring',()=>{
  for(const year of [2021,2022,2023]) {
    const e=find('kmchc-'+year);
    assert.equal(e.minutes,120); assert.equal(e.questions,60); assert.equal(e.penalty,0);
    const wrong=e.answers[0]===1?2:1;
    const grade=Core.grade(e,{1:wrong});
    assert.equal(grade.wrong,1);
    assert.equal(grade.score,e.excluded.length?null:0);
  }
  const latest=find('kmchc-2026-2-general');
  assert.equal(latest.minutes,120); assert.equal(latest.questions,50); assert.equal(latest.choices,4);
  assert.equal(Core.grade(latest,{1:1}).score,-1);
  assert.equal(Core.grade(find('kmchc-2025-1-advanced'),{}).weighted,false,'unresolved deletion normalization must not claim official points');
});

test('KMO online sessions preserve their own lengths, offsets and unrestricted integer answers',()=>{
  for(const part of ['T1','T2','T4']) {
    const sessions=entries.filter(e=>e.id.startsWith('kmo-2020-'+part+'-s'));
    assert.deepEqual(sessions.map(e=>[e.minutes,e.questions,e.questionOffset]),[[60,10,0],[60,8,10],[60,7,18]]);
    assert.equal(sessions.flatMap(e=>e.points).reduce((a,b)=>a+b),100);
  }
  const online=find('kmo-2022-T1-s2');
  assert.equal(online.minutes,75); assert.equal(online.questionOffset,10);
  assert.equal(Core.answer(online,23252),23252);
  const modern=find('kmo-2026-T1');
  assert.equal(modern.minutes,150); assert.equal(modern.questions,20);
  assert.equal(Core.answer(modern,23252),null);
  assert.equal(modern.points.reduce((a,b)=>a+b),100);
});

test('all requested middle/high first and second rounds are enabled; unpublished 2026 round two is absent',()=>{
  assert.ok(entries.filter(e=>e.comp==='kmo'&&!e.title.ko.includes('최종')).every(e=>Core.ready(e)));
  assert.ok(!entries.some(e=>e.comp==='kmo'&&e.year===2026&&e.title.ko.includes('2차')));
  assert.ok(entries.filter(e=>e.practice===false).every(e=>e.title.ko.includes('최종')));
});

test('visual verification enables all six previously unparsed official final sessions',()=>{
  const corrections=require('../data/research/kmo-final-format-research.json');
  assert.equal(corrections.entries.length,6);
  for(const source of corrections.entries) {
    const e=find(source.id);assert.equal(e.practice,true);assert.equal(e.minutes,270);
    assert.equal(e.questions,3);assert.equal(e.questionOffset,source.questionOffset);
    assert.deepEqual(e.points,[7,7,7]);assert.equal(e.answersVerified,false);
  }
});

test('historical source additions preserve every existing official KMO year and label limited-access leads separately',()=>{
  const rendered=JSON.parse(JSON.stringify(scope.window.THEORY));
  for(const year of Object.keys(originalTheory.kmo))assert.deepEqual(rendered.kmo[year],originalTheory.kmo[year],year);
  const additions=require('../data/research/contest-archive-additions.json');
  assert.equal(additions.archives.length,17);
  for(const a of additions.archives) {
    const f=rendered[a.comp][a.year].f[a.part];
    assert.equal(f.paper,a.paper);assert.equal(f.archive.type,a.sourceType);
    assert.ok(f.archive.note&&f.archive.url&&a.verifiedPdf);
    if(!a.exam)assert.ok(!entries.some(e=>e.id===a.id),'An archive without verified timing must not become an exam');
  }
  assert.ok(data.resources.some(r=>r.access==='preview'));
  assert.ok(data.resources.some(r=>r.access==='login'));
});
