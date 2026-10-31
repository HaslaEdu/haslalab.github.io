const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const comparison=require('../sim/result-comparison.js');
const source={url:'https://example.org/results',title:'Published results',official:true};
const theory={id:'test-2025-theory',year:2025,scope:'theory',label:{ko:'이론',en:'Theory'},max:30,taskSets:[['T1','T2','T3']],scores:[30,25,25,10,0],complete:true,participants:5,population:'individual',awardScope:false,sources:[source]};
const total={...theory,id:'test-2025-total',scope:'total',label:{ko:'전체 총점',en:'Overall total'},max:50,taskSets:[['T1','T2','T3','E1','E2']],scores:[48,40,35,35,10],awardScope:true,cutoffKind:'published',medalCutoffs:{gold:40,silver:35,bronze:20},components:[{id:'theory',label:{en:'Theory'},max:30,taskSets:[['T1','T2','T3']]},{id:'experiment',label:{en:'Experiment'},max:20,taskSets:[['E1','E2']]}]};
const roundTheory={...theory,medalReference:{basis:'round_rank',counts:{gold:1,silver:1,bronze:2},cuts:{gold:30,silver:25,bronze:10},population:'complete',sources:[source]}};
const experiment={...theory,id:'test-2025-experiment',scope:'experiment',label:{ko:'실험',en:'Experiment'},max:20,taskSets:[['E1','E2']],scores:[20,17,17,5,0],medalReference:{basis:'round_rank',counts:{gold:1,silver:1,bronze:2},cuts:{gold:20,silver:17,bronze:5},population:'complete',sources:[source]}};
const session=(extra={})=>({id:10,exam_key:'test-2025',comp:'test',year:2025,status:'graded',score:25,points:30,tasks:['T3','T1','T2'],review_only:false,graded_at:100,created_at:90,detail:{tasks:{}},...extra});
const dataset={schema:1,comp:'test',records:[theory,total]};
const scopedDataset={...dataset,records:[roundTheory,experiment,total]};
const complement=(extra={})=>session({id:11,tasks:['E2','E1'],score:17,points:20,graded_at:110,created_at:95,...extra});
const text=html=>html.replace(/<[^>]*>/g,' ').replace(/&amp;/g,'&').replace(/&nbsp;/g,' ').replace(/\s+/g,' ').trim();
function metric(html,name){
  const start=new RegExp('<([a-z][a-z0-9-]*)\\b[^>]*\\bdata-metric="'+name+'"[^>]*>','i').exec(html);
  assert.ok(start,`missing ${name} metric`);
  const tags=new RegExp('<\\/?'+start[1]+'\\b[^>]*>','gi');tags.lastIndex=start.index+start[0].length;
  let depth=1,tag;
  while((tag=tags.exec(html))){
    depth+=tag[0].startsWith('</')?-1:1;
    if(!depth)return text(html.slice(start.index+start[0].length,tag.index)).replace(/(\d)\s+%/g,'$1%');
  }
  assert.fail(`unclosed ${name} metric`);
}
function withoutDetails(html){
  const tags=/<\/?details\b[^>]*>/gi,ranges=[];let depth=0,start=0,tag;
  while((tag=tags.exec(html))){
    if(tag[0].startsWith('</')){if(!--depth)ranges.push([start,tags.lastIndex]);}
    else{if(!depth)start=tag.index;depth++;}
  }
  for(const [start,end] of ranges.reverse())html=html.slice(0,start)+html.slice(end);
  return html;
}
function assertCollapsed(html){
  for(const tag of html.match(/<details\b[^>]*>/g)||[])assert.doesNotMatch(tag,/\sopen(?:\s|=|>)/,'reference details start collapsed');
}

test('only the complete matching paper on the original scoring scale is compared',()=>{
  assert.equal(comparison.assess(dataset,session()).comparisons.length,1);
  assert.equal(comparison.assess(dataset,session()).comparisons[0].record.scope,'theory');
  assert.equal(comparison.assess(dataset,session({tasks:['T1'],points:10,score:9})).comparisons.length,0);
  assert.equal(comparison.assess(dataset,session({tasks:['T1'],points:30})).comparisons.length,0);
  assert.equal(comparison.assess(dataset,session({points:100,score:80})).comparisons.length,0);
  assert.equal(comparison.assess(dataset,session({year:2024})).comparisons.length,0);
  assert.equal(comparison.assess(dataset,session({comp:'another'})).comparisons.length,0);
});

test('real zero is compared; missing, qualitative, out-of-range and unfinished grades are never compared',()=>{
  assert.equal(comparison.hasScore(session({score:0})),true);
  for(const extra of [{score:null},{points:null},{score:NaN},{score:-1},{score:31},{status:'grading'},{detail:{tasks:{T1:{grading_mode:'qualitative_review'}}}}]){
    assert.equal(comparison.hasScore(session(extra)),false);
    assert.equal(comparison.html(dataset,session(extra),'en'),'');
  }
});

test('historical score ranks preserve ties and cannot produce a top percentage over 100',()=>{
  const tied=comparison.evaluate(theory,25);
  assert.equal(tied.rank,2);assert.equal(tied.tied,2);assert.equal(tied.top_pct,40);
  assert.equal(comparison.evaluate(theory,0).rank,5);
  const below=comparison.evaluate({...theory,scores:[30,25,25,10,1]},0);
  assert.equal(below.rank,6);assert.equal(below.top_pct,100);
  const html=comparison.resultHtml(below,'en');
  assert.match(html,/<[^>]*class="[^"]*hlcr-rank\b[^>]*>[\s\S]*?<strong[^>]*>\s*6\b/);
  assert.match(text(withoutDetails(html)),/5/,'published population remains visible next to the numeric position');
});

test('winner-only or inconsistent distributions cannot claim a full-field rank or percentile',()=>{
  for(const record of [{...theory,complete:false},{...theory,participants:20}]){
    const e=comparison.evaluate(record,25),html=comparison.resultHtml(e,'en');
    assert.equal(e.complete,false);assert.equal(e.top_pct,null);
    assert.match(text(withoutDetails(html)),/partial|subset|published scores|full-field.*unavailable/i,'an incomplete field is qualified before expanding details');
    assert.doesNotMatch(text(withoutDetails(html)),/Top [\d.]+%/);
  }
});

test('a verified total-score coverage floor permits full-field rank only within that published score range',()=>{
  const record={...total,scores:[48,40,35,35,20],complete:false,participants:20,rankFloor:20};
  const above=comparison.evaluate(record,40),below=comparison.evaluate(record,19);
  assert.equal(above.complete,false);assert.equal(above.bounded,true);assert.equal(above.rank,2);assert.equal(above.top_pct,10);
  const html=comparison.resultHtml(above,'en');
  assert.match(html,/whole field|full field/i);assert.match(html,/Full field · 20 contestants/);
  assertCollapsed(html);
  assert.equal(below.bounded,false);assert.equal(below.top_pct,null);
  assert.equal(comparison.evaluate({...record,scope:'theory'},40).bounded,false);
  assert.equal(comparison.evaluate({...record,participantCountUncertain:true},40).top_pct,null);
});

test('a round score at or above the total coverage floor gets an exact full-field round rank and band',()=>{
  // Unpublished contestants all totalled below 20, so their theory score was below 20 as well.
  const floorTotal={...total,id:'floor-total',scores:[48,44,40,35,31,26,22,20],complete:false,participants:20,rankFloor:20};
  const round={...roundTheory,id:'floor-theory',scores:[29,27,25,24,22,18,12,9],complete:false,participants:20,
    medalReference:{...roundTheory.medalReference,counts:{gold:1,silver:2,bronze:3},cuts:{gold:29,silver:25,bronze:18},population:'published'}};
  const records=[floorTotal,round];
  const coverage=comparison.componentFloor(records,round);
  assert.equal(coverage.floor,20);assert.equal(coverage.total.id,'floor-total');
  const high=comparison.evaluate(round,26,false,coverage);
  assert.equal(high.bounded,true);assert.equal(high.rank,3);assert.equal(high.fieldSize,20);assert.equal(high.top_pct,15);
  assert.equal(high.reference.medal,'silver');assert.equal(high.reference.fullField,true);
  const low=comparison.evaluate(round,18,false,coverage);
  assert.equal(low.bounded,false);assert.equal(low.top_pct,null);
  assert.equal(low.reference.medal,'bronze');assert.equal(low.reference.fullField,false,'a band whose cut is below the floor may fall in the whole field');
  assert.equal(comparison.evaluate(round,5,false,coverage).reference.fullField,true,'below every band can never improve');
  const ko=comparison.resultHtml(high,'ko'),en=comparison.resultHtml(high,'en');
  assert.match(text(withoutDetails(ko)),/전체 20명 기준/);assert.match(text(withoutDetails(ko)),/상위 15%/);
  assert.match(text(withoutDetails(ko)),/이론 기준 은메달권/);assert.match(text(withoutDetails(en)),/Full field · 20 contestants/);
  assert.match(text(withoutDetails(comparison.resultHtml(low,'ko'))),/전체 기준으로는 낮아질 수 있음/);
  assertCollapsed(ko);assertCollapsed(en);
  // Without the sibling total, a mismatched published set, or a mismatched population, nothing is inferred.
  assert.equal(comparison.componentFloor([round],round),null);
  assert.equal(comparison.componentFloor([{...floorTotal,scores:floorTotal.scores.slice(1)},round],round),null);
  assert.equal(comparison.componentFloor([{...floorTotal,participants:21},round],round),null);
  assert.equal(comparison.componentFloor([{...floorTotal,rankFloor:undefined},round],round),null);
  assert.equal(comparison.evaluate(round,26).bounded,false,'a bare round record never infers coverage');
});

test('the best score comes from a declared topScore or the highest published score',()=>{
  const declared={...total,scores:[],topScore:44.75,medalCutoffs:{gold:38,silver:33,bronze:27,hm:21}};
  const e=comparison.evaluate(declared,40);
  assert.equal(e.best,44.75);assert.equal(e.rank,null);assert.equal(e.medal,'gold');
  assert.match(text(comparison.resultHtml(e,'ko')),/1위 점수 44.75 \/ 50 · 1위와 4.75점 차이/);
  assert.match(text(comparison.resultHtml(comparison.evaluate(declared,45,true),'en')),/Best score 44.75 \/ 50 · at or above the best/);
  assert.equal(comparison.evaluate(total,30).best,48);
  assert.match(text(comparison.resultHtml(comparison.evaluate(roundTheory,20),'ko')),/이론 1위 점수/);
});

test('medals use verified thresholds for the full award scope, including exact-boundary rules',()=>{
  assert.equal(comparison.evaluate(total,40).medal,'gold');
  assert.equal(comparison.evaluate(total,35).medal,'silver');
  assert.equal(comparison.evaluate(total,20).medal,'bronze');
  assert.equal(comparison.evaluate(total,19.99).medal,'none');
  assert.equal(comparison.evaluate({...total,medalCutoffRule:'gt'},40).medal,'silver');
  assert.equal(comparison.evaluate({...theory,medalCutoffs:{gold:20}},25).medal,null);
  const observed=comparison.resultHtml(comparison.evaluate({...total,cutoffKind:'observed'},40),'ko');
  assert.match(observed,/<[^>]*class="[^"]*hlcr-medal\b[^>]*data-medal="gold"/);
  assert.match(text(withoutDetails(observed)),/참고/,'an observed medal badge retains its reference qualifier');
  assertCollapsed(observed);
});

test('round-reference medals use declared same-round rank bands and preserve boundary ties without awarding an actual overall medal',()=>{
  for(const [record,score,medal] of [[roundTheory,30,'gold'],[roundTheory,25,'silver'],[roundTheory,24.9,'bronze'],[roundTheory,10,'bronze'],[roundTheory,0,'none'],[experiment,17,'silver']]){
    const reference=comparison.roundReference(record,score),evaluation=comparison.evaluate(record,score);
    assert.equal(reference.medal,medal);
    assert.equal(reference.scope,record.scope);
    assert.equal(reference.population,'complete');
    assert.deepEqual(reference.cuts,record.medalReference.cuts);
    assert.deepEqual(reference.counts,record.medalReference.counts);
    assert.equal(evaluation.medal,null,'a component does not become an actual competition medal');
    assert.equal(evaluation.reference.medal,medal);
  }
  assert.equal(comparison.evaluate(roundTheory,25).tied,2);
  assert.equal(comparison.evaluate(total,40).medal,'gold','published overall thresholds keep their independent meaning');
  assert.equal(comparison.roundReference(theory,25),null,'no undeclared default medal quotas');
  assert.equal(comparison.roundReference(roundTheory,31),null);
  assert.equal(comparison.roundReference(roundTheory,NaN),null);
  for(const lang of ['ko','en']){
    const html=comparison.resultHtml(comparison.evaluate(roundTheory,25),lang);
    assert.match(html,/<[^>]*class="[^"]*hlcr-medal\b[^>]*data-medal="silver"/);
    assert.match(text(withoutDetails(html)),lang==='en'?/reference/i:/참고/,'the component medal qualifier is visible without opening details');
    assertCollapsed(html);
  }
});

test('published-only round references remain visibly limited and invalid reference bands are rejected',()=>{
  const partial={...roundTheory,complete:false,participants:20,medalReference:{...roundTheory.medalReference,population:'published'}};
  const result=comparison.evaluate(partial,25);
  assert.equal(result.reference.medal,'silver');
  assert.equal(result.reference.population,'published');
  assert.equal(result.medal,null);assert.equal(result.complete,false);assert.equal(result.top_pct,null);
  for(const lang of ['ko','en']){
    const visible=text(withoutDetails(comparison.resultHtml(result,lang)));
    assert.match(visible,lang==='en'?/published.*reference|reference.*published/i:/공개.*참고/);
    assert.doesNotMatch(visible,/Top [\d.]+%|상위 [\d.]+%/);
  }
  const badReferences=[
    {...roundTheory.medalReference,counts:{gold:-1,silver:1,bronze:2}},
    {...roundTheory.medalReference,counts:{gold:1.5,silver:1,bronze:2}},
    {...roundTheory.medalReference,counts:{gold:4,silver:1,bronze:2}},
    {...roundTheory.medalReference,cuts:{gold:31,silver:25,bronze:10}},
    {...roundTheory.medalReference,cuts:{gold:20,silver:25,bronze:10}},
    {...roundTheory.medalReference,cuts:{gold:30,silver:NaN,bronze:10}}
  ];
  for(const medalReference of badReferences)assert.equal(comparison.roundReference({...roundTheory,medalReference},25),null);
  assert.equal(comparison.roundReference({...roundTheory,complete:false},25),null,'complete-population reference requires the full field');
  assert.equal(comparison.roundReference({...roundTheory,participants:20},25),null,'a mismatched participant count cannot become a complete-population reference');
  assert.equal(comparison.roundReference({...roundTheory,complete:false,scope:'theory',rankFloor:10},25),null,'a total-score coverage floor does not complete a component population');
});

test('separately scored subrounds retain a round rank label rather than becoming experiments',()=>{
  for(const part of ['A','B']){
    const record={...theory,scope:'round',label:{ko:`이론 ${part}`,en:`Theory ${part}`}};
    for(const lang of ['ko','en']){
      const visible=text(withoutDetails(comparison.resultHtml(comparison.evaluate(record,25),lang)));
      assert.match(visible,lang==='en'?/Round score rank/:/라운드 기준 가상 순위/);
      assert.doesNotMatch(visible,lang==='en'?/Experiment score rank/:/실험 기준 가상 순위/);
    }
  }
});

test('team medal references describe awarded teams and preserve the team population unit',()=>{
  const record={...roundTheory,population:'team'},evaluation=comparison.evaluate(record,25);
  const ko=comparison.resultHtml(evaluation,'ko'),en=comparison.resultHtml(evaluation,'en');
  assert.match(text(ko),/팀 수\(1·1·2팀\)/);
  assert.doesNotMatch(text(ko),/인원\(|1·1·2명/);
  assert.match(text(withoutDetails(ko)),/전체 5팀 성적 기준/);
  assert.match(text(withoutDetails(en)),/5 teams in the score table/);
  assert.doesNotMatch(text(withoutDetails(en)),/5 contestants/);
  assertCollapsed(ko);assertCollapsed(en);
});

test('same-edition full rounds automatically combine using the latest valid same-mode complement without mutating earned scores',()=>{
  const related=[complement({id:12,score:20,graded_at:101}),complement({id:11,score:17,graded_at:110})];
  const anchor=session({related_results:related,sample_standing:{cohort:'timed',n:20,rank:3,top_pct:15,avg:60,max:100,first:true}}),before=JSON.stringify(anchor);
  for(const related_results of [related,[...related].reverse()]){
    const entries=comparison.combinedResults(scopedDataset,{...anchor,related_results});
    assert.equal(entries.length,1);
    const result=entries[0];
    assert.equal(result.record.id,total.id);assert.equal(result.score,42);assert.equal(result.record.max,50);
    assert.equal(result.rank,2);assert.equal(result.medal,'gold');
    assert.equal(result.combined.mixedMode,false);
    assert.deepEqual(result.combined.sessions.map(s=>s.id),[10,11]);
    assert.deepEqual(result.combined.sessions.map(s=>s.scope),['theory','experiment']);
  }
  const assessment=comparison.assess(scopedDataset,anchor);
  assert.equal(assessment.comparisons.filter(e=>e.record.scope==='total').length,1);
  assert.deepEqual(assessment.comparisons.map(e=>e.record.scope),['theory','total'],'the graded round keeps its own card before the combined total');
  assert.equal(assessment.comparisons[0].reference.medal,'silver');
  const roundNotes=comparison.html(scopedDataset,anchor,'ko').match(/data-round-medal="[^"]*"/g)||[];
  assert.equal(roundNotes.length,2,'each combined round shows its own round rank and band');
  assert.equal(assessment.totals.length,0,'an automatically covered total does not also request manual entry');
  assert.equal(JSON.stringify(anchor),before);
  const html=comparison.html(scopedDataset,anchor,'en');
  assert.match(metric(html,'score'),/25\s*\/\s*30/,'the HaslaLab summary remains this sitting\'s earned grade');
  assert.match(metric(html,'rank'),/3\s*\/\s*20/,'the HaslaLab sample is not recomputed from a historical reference total');
  assert.match(text(withoutDetails(html)),/auto.*combin|combin.*score|combined total/i);
});

test('automatic totals reject another edition, key, unfinished or partial work, wrong scales and task overlap',()=>{
  const invalid=[
    complement({comp:'another'}),complement({year:2024}),complement({exam_key:'test-2025-another'}),
    complement({status:'grading'}),complement({status:'pending'}),complement({status:'ended'}),
    complement({score:null}),complement({points:100}),complement({score:21}),
    complement({tasks:['E1'],points:10,score:9}),complement({tasks:['T1','E1'],points:20}),
    complement({tasks:['T1','T2','T3','E1','E2'],points:50,score:42}),complement({id:10}),
    complement({detail:{tasks:{E1:{grading_mode:'qualitative_review'}}}})
  ];
  for(const related of invalid)assert.deepEqual(comparison.combinedResults(scopedDataset,session({related_results:[related]})),[],JSON.stringify(related));
  assert.deepEqual(comparison.combinedResults(scopedDataset,session({tasks:['T1'],points:10,score:9,related_results:[complement()]})),[],'the anchor also needs the complete component');
  assert.deepEqual(comparison.combinedResults(scopedDataset,session({tasks:['T1','T2','T3','E1','E2'],points:50,score:42,related_results:[complement()]})),[],'a full combined sitting cannot count another experiment again');
  const duplicate=complement();
  const entries=comparison.combinedResults(scopedDataset,session({related_results:[duplicate,duplicate]}));
  assert.equal(entries.length,1);assert.equal(entries[0].score,42);
  const zero=comparison.combinedResults(scopedDataset,session({related_results:[complement({score:0})]}));
  assert.equal(zero[0].score,25,'zero is a valid earned complement');
  const unknown={...total,manualOnly:true,max:null,taskSets:[],components:[]};
  assert.deepEqual(comparison.combinedResults({...scopedDataset,records:[roundTheory,experiment,unknown]},session({related_results:[complement()]})),[]);
});

test('same-mode complements take priority and cross-mode fallback is explicit rather than silently changing the cohort',()=>{
  const same=complement({id:12,score:15,graded_at:100}),other=complement({id:13,score:20,review_only:true,graded_at:200});
  const current=session({related_results:[other,same]});
  const preferred=comparison.combinedResults(scopedDataset,current)[0];
  assert.equal(preferred.score,40);assert.equal(preferred.combined.mixedMode,false);
  assert.deepEqual(preferred.combined.sessions.map(s=>s.id),[10,12]);
  const mixedSession=session({related_results:[other]}),before=JSON.stringify(mixedSession);
  const mixed=comparison.combinedResults(scopedDataset,mixedSession)[0];
  assert.equal(mixed.score,45);assert.equal(mixed.combined.mixedMode,true);
  assert.deepEqual(mixed.combined.sessions.map(s=>s.review_only),[false,true]);
  for(const lang of ['ko','en'])assert.match(text(withoutDetails(comparison.resultHtml(mixed,lang))),lang==='en'?/mixed|different.*mode|timed.*untimed/i:/혼합|다른.*모드|실전.*첨삭|실전.*시간 제한 없는.*채점|모드.*다름/);
  assert.equal(JSON.stringify(mixedSession),before);
});

test('aggregation anchors either full round and selects latest graded time, creation fallback and id deterministically',()=>{
  const candidates=[
    complement({id:20,score:20,graded_at:101,created_at:999}),
    complement({id:21,score:10,graded_at:null,created_at:102}),
    complement({id:22,score:5,graded_at:null,created_at:102})
  ];
  for(const related_results of [candidates,[...candidates].reverse()]){
    const result=comparison.combinedResults(scopedDataset,session({related_results}))[0];
    assert.equal(result.score,30,'a lower score from the most recent qualifying sitting wins');
    assert.deepEqual(result.combined.sessions.map(s=>s.id),[10,22]);
  }
  const result=comparison.combinedResults(scopedDataset,complement({related_results:[session()]}))[0];
  assert.equal(result.score,42);
  assert.deepEqual(result.combined.sessions.map(s=>s.id),[10,11],'component order is stable when the current anchor is experiment');
  const duplicateTasks=complement({tasks:['E1','E2','E2']});
  assert.deepEqual(comparison.combinedResults(scopedDataset,session({related_results:[duplicateTasks]})),[]);
  assert.deepEqual(comparison.combinedResults(scopedDataset,session({tasks:['T1','T2','T3','T3'],related_results:[complement()]})),[]);
});

test('component grades offer an explicitly manual combined score without changing the graded result',()=>{
  const s=session(),before=JSON.stringify(s),html=comparison.html(dataset,s,'ko');
  assert.match(html,/<details\b[^>]*class="[^"]*hlcr-manual\b/);
  assertCollapsed(html);
  assert.match(html,/value="25" readonly/);
  assert.match(html,/name="experiment" min="0" max="20"/);
  assert.equal(comparison.assess(dataset,s).comparisons.some(x=>x.record.scope==='total'),false);
  const manual=comparison.resultHtml(comparison.evaluate(total,42,true),'ko');
  assert.match(manual,/채점 성적|HaslaLab 표본/);
  assert.equal(JSON.stringify(s),before);
});

test('unknown official maxima permit only an explicitly entered raw-total rank, never a grade conversion',()=>{
  const record={...total,id:'manual-total',max:null,manualOnly:true,taskSets:[],components:[],scores:[89.1,81.4,50.2],participants:3,awardScope:false,medalCutoffs:undefined};
  assert.equal(comparison.matches(record,session()),false);
  assert.equal(comparison.evaluate(record,82),null);
  const manual=comparison.evaluate(record,82,true);
  assert.equal(manual.rank,2);assert.equal(manual.medal,null);
  assert.doesNotMatch(comparison.resultHtml(manual,'en'),/\/ —/);
  const html=comparison.html({...dataset,records:[record]},session(),'en');
  assert.match(html,/name="total" min="0" step="any" required/);
  assert.doesNotMatch(html,/max="null"/);
  const knownManual=comparison.html({...dataset,records:[{...total,manualOnly:true}]},session(),'en');
  assert.doesNotMatch(knownManual,/value="25" readonly/);
  assert.match(knownManual,/name="total" min="0" max="50"/);
});

test('compact score metrics distinguish earned percentage from the HaslaLab cohort in Korean and English',()=>{
  const s=session({sample_standing:{cohort:'timed',n:20,rank:3,top_pct:15,mine:99,avg:60,max:100,first:false}});
  for(const lang of ['ko','en']){
    const html=comparison.sampleHtml(s,lang);
    assert.match(html,/<dl\b[^>]*class="[^"]*hlcr-metrics\b/);
    assert.equal((html.match(/class="hlcr-metric(?:\s|")/g)||[]).length,5,'average and best share the fifth metric cell');
    assert.match(metric(html,'score'),/25\s*\/\s*30/);
    assert.match(metric(html,'percentage'),/83\.3\d*%/,'own percentage follows earned score rather than stale cohort mine');
    assert.match(metric(html,'rank'),/3\s*\/\s*20|20.*3/);
    assert.match(metric(html,'top'),/15%/);
    assert.match(metric(html,'average'),/60%/);
    assert.match(metric(html,'best'),/100%/);
    assert.match(html,lang==='en'?/Timed attempts/:/시간 제한.*실전/);
    assert.match(html,lang==='en'?/repeat attempt/:/재응시/);
    assertCollapsed(html);
  }
});

test('one candidate never gets cohort percentile, average or best even if stale fields contain 100',()=>{
  const s=session({score:30,sample_standing:{cohort:'review',n:1,rank:1,top_pct:100,mine:100,avg:100,max:100,first:true}});
  for(const lang of ['ko','en']){
    const html=comparison.sampleHtml(s,lang);
    assert.match(metric(html,'percentage'),/100%/,'the earned perfect percentage remains valid');
    assert.match(metric(html,'rank'),/1\s*\/\s*1|1.*1/);
    for(const key of ['top','average','best']){
      assert.match(metric(html,key),/—|–/);
      assert.doesNotMatch(metric(html,key),/100%/);
    }
    assert.match(html,lang==='en'?/Untimed grading/:/시간 제한 없는 채점/);
  }
});

test('score metrics survive missing samples, loading and unavailable historical data',()=>{
  for(const lang of ['ko','en']){
    for(const html of [comparison.sampleHtml(session(),lang),comparison.html(null,session(),lang,true),comparison.html({...dataset,records:[]},session(),lang)]){
      assert.match(metric(html,'score'),/25\s*\/\s*30/);
      assert.match(metric(html,'percentage'),/83\.3\d*%/);
      for(const key of ['rank','top','average','best'])assert.match(metric(html,key),/—|–/);
    }
    const zero=comparison.sampleHtml(session({score:0}),lang);
    assert.match(metric(zero,'score'),/0\s*\/\s*30/);
    assert.match(metric(zero,'percentage'),/0%/);
  }
});

test('historical comparisons use medal badges and collapsed detail panels without hiding partial-scope warnings',()=>{
  for(const lang of ['ko','en']){
    for(const [score,medal] of [[40,'gold'],[35,'silver'],[20,'bronze']]){
      const html=comparison.resultHtml(comparison.evaluate(total,score),lang);
      assert.match(html,new RegExp('<[^>]*class="[^"]*hlcr-medal\\b[^>]*data-medal="'+medal+'"'));
      assert.match(html,/<details\b[^>]*class="[^"]*hlcr-details\b/);
      assertCollapsed(html);
    }
    const round=comparison.resultHtml(comparison.evaluate(theory,25),lang);
    assert.doesNotMatch(round,/class="[^"]*hlcr-medal\b/);
    assert.match(text(withoutDetails(round)),lang==='en'?/round|theory|medal/i:/라운드|이론|메달/);
    const partial=comparison.html(dataset,session({tasks:['T1'],points:10,score:9}),lang);
    assert.doesNotMatch(partial,/data-comparison=/,'partial grades do not create a scored historical card');
    assert.doesNotMatch(partial,/class="[^"]*hlcr-medal\b/);
    assertCollapsed(partial);
  }
});

test('source attribution, unavailable editions and text escaping stay honest',()=>{
  const html=comparison.resultHtml(comparison.evaluate({...total,sources:[{url:'https://example.org',title:'<script>x</script>',official:false}]},40),'en');
  assert.match(html,/&lt;script&gt;x&lt;\/script&gt; \(unofficial\)/);
  assert.doesNotMatch(html,/<script>/);
  assert.doesNotMatch(comparison.html({...dataset,records:[]},session(),'ko'),/data-comparison=/);
  assert.equal(comparison.assess(dataset,session({tasks:['T1'],points:10,score:9})).comparisons.length,0);
});

test('failed public data loads retry and stale score reports cannot repaint a newer page',async()=>{
  let calls=0;
  const context={window:{},module:{exports:{}},Map,fetch:async()=>{calls++;if(calls===1)return{ok:false};return{ok:true,json:async()=>dataset};}};
  vm.runInNewContext(fs.readFileSync(require.resolve('../sim/result-comparison.js'),'utf8'),context);
  const api=context.module.exports;
  assert.equal(await api.load('test','results/'),null);
  assert.equal((await api.load('test','results/')).comp,'test');
  assert.equal(calls,2);
  const host={innerHTML:'',isConnected:true};
  await api.mount(host,session(),'en',{base:'results/',isCurrent:()=>false});
  assert.match(host.innerHTML,/Loading published results/);
  assert.doesNotMatch(host.innerHTML,/data-comparison=/);
  assert.match(metric(host.innerHTML,'score'),/25\s*\/\s*30/);
});

test('report and receipt both use the scoped comparison and IPhO labels its unofficial archive',()=>{
  const arena=fs.readFileSync(require.resolve('../arena.js'),'utf8'),exam=fs.readFileSync(require.resolve('../sim/exam.html'),'utf8'),index=fs.readFileSync(require.resolve('../index.html'),'utf8');
  assert.match(arena,/labComparison\.mount/);assert.match(exam,/labComparison\.mount/);
  assert.doesNotMatch(arena,/labMedal\.estimate/);assert.doesNotMatch(exam,/labMedal\.estimate/);
  assert.match(index,/IPhO unofficial records · scores and awards/);assert.match(index,/https:\/\/ipho-unofficial\.org\//);
});

test('the real report mounts comparisons for scored untimed reviews and skips qualitative feedback',async()=>{
  const calls=[],slot={innerHTML:''},host={innerHTML:'',querySelector:s=>s==='#arLabComparison'?slot:null,querySelectorAll:()=>[]};
  const context={lang:'en',cm:{me:{nickname:'Student'}},DATA:{},window:{labComparison:{...comparison,mount:(...args)=>calls.push(args)}},
    esc:x=>String(x??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),
    cmFull:()=> '2026-10-30 12:00',cmShort:()=> '10-30',URLSearchParams,encodeURIComponent};
  vm.createContext(context);vm.runInContext(fs.readFileSync(require.resolve('../arena.js'),'utf8'),context);
  vm.runInContext('arMath=()=>{};arShopWire=()=>{}',context);
  const s=session({id:7,review_only:true,pages:[],started_at:1,sample_standing:{cohort:'review',n:3,rank:1,top_pct:33.3,first:true}});
  context.cmApi=async()=>({session:s});
  await context.arLabOne(host,()=>true,7);
  assert.equal(calls.length,1);assert.equal(calls[0][0],slot);assert.equal(calls[0][1],s);
  assert.match(host.innerHTML,/arLabComparison/);
  assert.doesNotMatch(host.innerHTML,/class="arstats"/,'the scoped summary replaces the legacy score strip');
  s.score=null;s.points=null;s.detail={tasks:{T1:{status:'graded',grading_mode:'qualitative_review',score:null,points:null,reference:'published_problem_only',official:false,items:[],
    evidence:[{page:1,quote:'F = ma',note:'State the force directions.'}],feedback:[{kind:'fix',note:'Define the coordinate axis.'}],
    review:{summary:'Qualitative explanation survives the compact score layout.',strengths:['Clear diagram.'],habits:[]}}}};
  await context.arLabOne(host,()=>true,7);
  assert.equal(calls.length,1);assert.doesNotMatch(host.innerHTML,/arLabComparison/);
  assert.match(host.innerHTML,/Qualitative explanation survives the compact score layout/);
  assert.match(host.innerHTML,/F = ma/);assert.match(host.innerHTML,/Define the coordinate axis/);
  assert.doesNotMatch(host.innerHTML,/hlcr-metrics|hlcr-medal|data-metric=/);
});
