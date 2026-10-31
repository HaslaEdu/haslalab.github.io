const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const root=path.resolve(__dirname,'..');
const read=name=>JSON.parse(fs.readFileSync(path.join(root,name),'utf8'));
const manifest=read('tools/theory/eotvos.json');
const report=read('tools/eotvos_archive_report.json');

test('Eotvos physics archive covers every recovered recent year without mathematical-predecessor placeholders',()=>{
  assert.equal(manifest.since,1916);
  const years=manifest.years.map(year=>year.y);
  assert.equal(new Set(years).size,years.length);
  assert.ok(years.every(year=>Number.isInteger(year)&&year>=1916&&year<=2026));
  for(let year=1994;year<=2026;year++)assert.ok(years.includes(year),String(year));
  assert.ok(years.includes(1949));
  assert.ok(manifest.resourceNote.en.includes('incomplete'));
  assert.ok(manifest.resources.some(source=>source.url==='https://phoxiv.org/olympiads/eotvos'));
});

test('all Eotvos documents are usable local PDFs with preserved source URLs and content fingerprints',()=>{
  const files=new Set();
  for(const year of manifest.years)for(const file of year.files){
    assert.match(file.local,/^pdfx\/eotvos\/[A-Za-z0-9_.-]+\.pdf$/);
    assert.match(file.url,/^https:\/\//);
    const content=fs.readFileSync(path.join(root,file.local));
    assert.ok(content.subarray(0,1024).includes(Buffer.from('%PDF-')),file.local);
    assert.equal(content.length,file.bytes,file.local);
    assert.equal(crypto.createHash('sha256').update(content).digest('hex'),file.sha256,file.local);
    assert.ok(file.pages>0,file.local);files.add(file.local);
  }
  assert.ok(files.size>=56);
  assert.ok(report.files.every(file=>!file.error));
});

test('annual combined reports and genuine historical reprints disclose solutions and exact year context',()=>{
  for(const year of manifest.years){
    const original=year.files.find(file=>file.kind==='paper'&&file.lang==='HU');
    assert.ok(original,String(year.y));
    if(year.source_type==='report_reprint'){
      assert.equal(year.paper_contains_solutions,true);
      assert.equal(original.contains_solutions,true);
      assert.ok(year.files.some(file=>file.kind==='solution'&&file.local===original.local));
    }
    if(original.source_document_year){
      assert.equal(year.source_type,'historical_reprint');
      assert.equal(original.complete_problem_set,true);
      assert.ok(original.source_pages.length>0);
      assert.ok(!year.files.some(file=>file.kind==='solution'),'A reprinted statement must not invent a solution to the historical set.');
      const audit=report.historical_reprints.find(item=>item.year===year.y);
      assert.ok(audit&&audit.section_header_verified,String(year.y));
      assert.deepEqual(audit.source_pages,original.source_pages);
    }
  }
  // The 2018 translator explicitly corrected problem 2; keep that separate from
  // the unchanged Hungarian original rather than silently replacing it.
  const english=manifest.years.find(year=>year.y===2018).files.find(file=>file.lang==='EN');
  assert.match(english.note,/corrected final temperature/);
});
