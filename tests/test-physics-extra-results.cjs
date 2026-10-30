const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),read=name=>fs.readFileSync(path.join(root,name),'utf8'),data=JSON.parse(read('tools/results/physics-extra.json'));
const records=Object.values(data.competitions).flatMap(c=>c.records),byId=id=>records.find(r=>r.id===id),sort=a=>a.slice().sort((a,b)=>b-a);

test('extra physics records preserve verified scoring scales, complete populations and zeroes',()=>{
  assert.equal(records.length,24);
  for(const [year,n,th,ex]of [[2021,37,100,50],[2022,29,110,40]]){
    for(const [scope,max]of [['theory',th],['experiment',ex],['total',th+ex]]){
      const r=byId(`opho-${year}-invitational-${scope}`);assert.equal(r.max,max);assert.equal(r.complete,true);assert.equal(r.participants,n);assert.equal(r.scores.length,n);
    }
    const total=byId(`opho-${year}-invitational-total`);
    assert.equal(total.awardScope,true);assert.equal(total.cutoffKind,'observed');assert.deepEqual(total.components.map(c=>c.max),[th,ex]);
    assert.equal(byId(`opho-${year}-invitational-experiment`).scores.at(-1),0);
  }
  const a=byId('opho-2023-invitational-theory');assert.equal(a.max,160);assert.equal(a.participants,47);assert.equal(a.scores.at(-1),0);
  assert.equal(byId('opho-2023-invitational-total'),undefined);assert.equal(byId('opho-2023-invitational-experiment'),undefined);
  const b=byId('opho-2025-invitational-total');assert.equal(b.max,50);assert.equal(b.scores.length,46);assert.deepEqual(b.taskSets,[['T1i','T2i']]);assert.equal(b.medalCutoffs,undefined);
  assert.deepEqual(b.components.map(c=>c.max),[35,15]);assert.equal(b.awardScope,false);
});

test('weighted and partial fields cannot masquerade as matching HaslaLab raw grades',()=>{
  for(const r of records.filter(r=>r.manualOnly)){
    assert.deepEqual(r.taskSets,[]);assert.equal(r.awardScope,false);assert.equal(r.medalCutoffs,undefined);
    if(r.id!=='opho-2026-combined-total')assert.equal(r.max,null);
  }
  for(const [year,n,full]of [[2021,45,625],[2024,54,975]]){
    const r=byId(`opho-${year}-open-total`);assert.equal(r.complete,false);assert.equal(r.scores.length,n);assert.equal(r.participants,full);
  }
  const current=byId('opho-2026-combined-total');assert.equal(current.max,100);assert.equal(current.scores.length,443);assert.equal(current.complete,false);assert.equal(current.participants,519);
  for(const r of data.competitions.physcup.records){assert.equal(r.complete,false);assert.equal(r.participants,null);assert.equal(r.manualOnly,true);assert.ok(r.note.en.includes('joint submission'));}
});

test('IZhO2025 anonymous transcript validates every component sum and observed medal boundary',()=>{
  const sourcePath='tools/results/physics-extra-izho2025-source.json',raw=read(sourcePath),source=JSON.parse(raw),rows=source.rows;
  assert.equal(rows.length,180);assert.deepEqual(rows.map(r=>r[0]),Array.from({length:180},(_,i)=>i+1));
  assert.ok(source.title.includes('2025'));assert.ok(source.url.endsWith('results-izho-2020/'));
  for(const row of rows){assert.equal(row.length,7);assert.ok(Math.abs(row[1]+row[2]+row[3]+row[4]-row[5])<1e-6);assert.ok(row.slice(0,6).every(Number.isFinite));}
  assert.deepEqual(byId('izho-2025-theory').scores,sort(rows.map(r=>Math.round((r[1]+r[2]+r[3])*1e6)/1e6)));
  assert.deepEqual(byId('izho-2025-experiment').scores,sort(rows.map(r=>r[4])));
  const total=byId('izho-2025-total');assert.deepEqual(total.scores,sort(rows.map(r=>r[5])));assert.deepEqual(total.medalCutoffs,{gold:20.3,silver:15.3,bronze:12.1});
  const levels={gold:3,silver:2,bronze:1};
  for(const [tier,cut]of Object.entries(total.medalCutoffs)){
    assert.equal(cut,Math.min(...rows.filter(r=>r[6]===tier).map(r=>r[5])));
    assert.ok(rows.every(r=>r[5]<cut||(levels[r[6]]||0)>=levels[tier]),'no lower/no-award score reaches an inferred higher-tier threshold');
  }
  const receipt=JSON.parse(read('tools/results/physics-extra-receipts.json')).files.find(f=>f.transcript===sourcePath);
  assert.equal(receipt.transcriptSha256,crypto.createHash('sha256').update(raw).digest('hex'));assert.equal(receipt.scoreRows,180);
  assert.ok(total.sources.some(s=>s.official));assert.ok(total.sources.some(s=>s.official===false),'mirrored original schemes must not impersonate an official host');
});

test('unverified comparisons retain honest coverage instead of invented scores or cutoffs',()=>{
  for(const comp of ['plancks','ispho','gpho','ortvay']){assert.deepEqual(data.competitions[comp].records,[]);assert.ok(data.competitions[comp].coverage.en);}
  const plancks=JSON.parse(read('tools/results/physics-extra-receipts.json')).files.find(f=>f.url==='https://plancks23.ai-sf.it/files/list.pdf');
  assert.equal(plancks.rankOnly,true);assert.equal(plancks.numericScores,false);assert.equal(plancks.pages,5);
  for(const r of records){assert.ok(r.sources.length);assert.ok(r.sources.every(s=>/^https?:\/\//.test(s.url)));assert.deepEqual(r.scores,sort(r.scores));}
});

test('round-only reference bands use actual official award counts and cumulative score-rank boundaries',()=>{
  const expected=[
    ['opho-2021-invitational',{gold:7,silver:7,bronze:8}],
    ['opho-2022-invitational',{gold:3,silver:4,bronze:6}],
    ['izho-2025',{gold:24,silver:34,bronze:35}],
  ];
  const sourceRows=JSON.parse(read('tools/results/physics-extra-izho2025-source.json')).rows;
  assert.deepEqual(Object.fromEntries(['gold','silver','bronze'].map(t=>[t,sourceRows.filter(r=>r[6]===t).length])),expected[2][1]);
  for(const [prefix,counts]of expected)for(const scope of ['theory','experiment']){
    const record=byId(prefix+'-'+scope),ref=record.medalReference;
    assert.equal(record.awardScope,false);assert.equal(record.medalCutoffs,undefined);assert.equal(record.complete,true);
    assert.equal(ref.basis,'round_rank');assert.equal(ref.population,'complete');assert.deepEqual(ref.counts,counts);
    assert.deepEqual(Object.keys(ref.cuts).sort(),['bronze','gold','silver']);
    let running=0;
    for(const tier of ['gold','silver','bronze']){running+=counts[tier];assert.ok(running<=record.scores.length);assert.equal(ref.cuts[tier],record.scores[running-1]);}
    assert.ok(ref.cuts.gold>=ref.cuts.silver&&ref.cuts.silver>=ref.cuts.bronze);
    assert.ok(ref.sources.length&&ref.sources.every(s=>s.official===true&&/^https:\/\/(opho\.physoly\.org|izho\.kz)\//.test(s.url)));
  }
  assert.equal(records.filter(r=>r.medalReference).length,6);
  for(const r of records.filter(r=>r.scope==='total'||r.manualOnly||r.id.includes('2023')||r.id.includes('2025-invitational')))
    assert.equal(r.medalReference,undefined,'unverified scopes and undeclared prize tiers must not receive projected medals');
});
