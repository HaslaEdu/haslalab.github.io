const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const html=fs.readFileSync(require.resolve('../sim/exam.html'),'utf8');
const trustedStart=html.indexOf('const timedEotvosPaper =');
const trustedEnd=html.indexOf('const OK_EXAM =',trustedStart);
const drawStart=html.indexOf('async function drawPaper()');
const drawEnd=html.indexOf('/* inside each simulator',drawStart);
assert.ok(trustedStart>=0&&trustedEnd>trustedStart&&drawStart>=0&&drawEnd>drawStart);

function app({year=2020,paper=`https://eik.bme.hu/~vanko/fizika/eotvos/Eotvos_${year}.pdf`,delayed=false}={}){
  const viewer={innerHTML:'',children:[]},session={status:'running',ended_at:12345},paperState={open:true,i:0,docs:{}};
  let reject;
  const failed=delayed?new Promise((resolve,no)=>{reject=no}):null;
  const context=vm.createContext({THY:true,EX:{c:'eotvos',y:year,pdfs:[paper]},PAPER:paperState,SES:session,lang:'en',
    $:id=>id==='pv'?viewer:null,t:()=>({paperLoading:'Loading',paperFail:'Could not load',paperNone:'No paper'}),
    esc:value=>String(value).replaceAll('&','&amp;').replaceAll('"','&quot;'),pdfUrl:value=>value,
    pdfjs:async()=>({getDocument:()=>({promise:failed||Promise.reject(new TypeError('CORS blocked'))})})});
  vm.runInContext(html.slice(trustedStart,trustedEnd)+html.slice(drawStart,drawEnd),context);
  return{context,viewer,session,paperState,reject};
}

test('CORS-blocked verified Eötvös native paper opens in its trusted original viewer during the timed sitting',async()=>{
  const a=app();await a.context.drawPaper();
  assert.match(a.viewer.innerHTML,/<iframe/);
  assert.match(a.viewer.innerHTML,/src="https:\/\/eik\.bme\.hu\/~vanko\/fizika\/eotvos\/Eotvos_2020\.pdf"/);
  assert.match(a.viewer.innerHTML,/Official Hungarian paper/);
  assert.match(a.viewer.innerHTML,/Open original/);
  assert.equal(a.session.status,'running');assert.equal(a.session.ended_at,12345);
});

test('foreign PDFs and unverified years cannot enter the trusted timed iframe fallback',async()=>{
  for(const options of [{year:2026},{paper:'https://eik.bme.hu.attacker.test/~vanko/fizika/eotvos/Eotvos_2020.pdf'},{paper:'https://eik.bme.hu/~vanko/fizika/eotvos/Eotvos_2014.pdf'}]){
    const a=app(options);await a.context.drawPaper();
    assert.doesNotMatch(a.viewer.innerHTML,/<iframe/);assert.match(a.viewer.innerHTML,/Could not load/);
  }
});

test('a late CORS failure cannot reopen the paper after the timed sitting has ended',async()=>{
  const a=app({delayed:true}),drawing=a.context.drawPaper();
  await Promise.resolve();a.session.status='scanning';a.paperState.open=false;a.reject(new TypeError('CORS blocked'));
  await drawing;
  assert.doesNotMatch(a.viewer.innerHTML,/<iframe/);
});
