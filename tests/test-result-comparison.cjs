const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const comparison=require('../sim/result-comparison.js');
const source={url:'https://example.org/results',title:'Published results',official:true};
const theory={id:'test-2025-theory',year:2025,scope:'theory',label:{ko:'이론',en:'Theory'},max:30,taskSets:[['T1','T2','T3']],scores:[30,25,25,10,0],complete:true,participants:5,population:'individual',awardScope:false,sources:[source]};
const total={...theory,id:'test-2025-total',scope:'total',label:{ko:'전체 총점',en:'Overall total'},max:50,taskSets:[['T1','T2','T3','E1','E2']],scores:[48,40,35,35,10],awardScope:true,cutoffKind:'published',medalCutoffs:{gold:40,silver:35,bronze:20},components:[{id:'theory',label:{en:'Theory'},max:30,taskSets:[['T1','T2','T3']]},{id:'experiment',label:{en:'Experiment'},max:20,taskSets:[['E1','E2']]}]};
const session=(extra={})=>({comp:'test',year:2025,status:'graded',score:25,points:30,tasks:['T3','T1','T2'],detail:{tasks:{}},...extra});
const dataset={schema:1,comp:'test',records:[theory,total]};
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
  assert.match(html,/coverage floor|published (?:score )?range|verified range/i);
  assertCollapsed(html);
  assert.equal(below.bounded,false);assert.equal(below.top_pct,null);
  assert.equal(comparison.evaluate({...record,scope:'theory'},40).bounded,false);
  assert.equal(comparison.evaluate({...record,participantCountUncertain:true},40).top_pct,null);
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
