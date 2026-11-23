/* The problem and test maker's arithmetic (teach-tools.js): number variants computed by math-input.js, and the exam blueprint. */
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const T=require('../teach-tools.js');
const read=f=>fs.readFileSync(path.join(__dirname,'..',f),'utf8');
const drop={template:'질량 {m} kg인 공을 높이 {h} m에서 놓았다. 바닥에 닿기 직전의 속력은?',params:{m:{min:1,max:3,step:0.5},h:{min:2,max:20,step:1}},formula:'sqrt(2 g h)',constants:{g:9.8}};

test('each variant gets different values, the values written into the text, and the answer computed from them',()=>{
  const r=T.variants(drop,8,{rand:T.seeded(11)});
  assert.deepEqual(r.errors,[]);assert.equal(r.items.length,8);
  const keys=new Set(r.items.map(v=>v.values.m+'|'+v.values.h));assert.equal(keys.size,8,'no two variants alike');
  for(const v of r.items){
    assert.match(v.values.m,/^\d\.\d$/,'a value keeps its step\'s decimals');
    assert.ok(+v.values.h>=2&&+v.values.h<=20);
    assert.ok(v.text.includes(`질량 ${v.values.m} kg`)&&v.text.includes(`높이 ${v.values.h} m`));
    assert.ok(Math.abs(v.answer-Math.sqrt(2*9.8*+v.values.h))<1e-9);
    assert.equal(v.answerText,(Math.sqrt(2*9.8*+v.values.h)).toPrecision(3));
  }
  assert.equal(T.variants({...drop,params:{m:{min:1,max:1,step:1},h:{min:5,max:6,step:1}}},10).items.length,2,'never more variants than the ranges allow');
});

test('subscripts and Greek names read as one value; a skipped value never yields a broken answer',()=>{
  const r=T.variants({template:'{v_0} m/s, {theta} rad',params:{v_0:{min:5,max:20,step:5},theta:{min:0.2,max:1.2,step:0.2}},formula:'v_0^2 sin(2 theta)/g',constants:{g:9.8}},4,{rand:T.seeded(2)});
  assert.deepEqual(r.errors,[]);for(const v of r.items)assert.ok(Math.abs(v.answer-(+v.values.v_0)**2*Math.sin(2*+v.values.theta)/9.8)<1e-9);
  const z=T.variants({template:'{x}',params:{x:{min:0,max:0,step:1}},formula:'1/x'},3);
  assert.equal(z.items.length,0);assert.deepEqual(z.errors.map(e=>e.code),['no_valid_values']);
});

test('what is missing or wrong is named, and nothing is run with eval',()=>{
  const codes=t=>T.check(t).map(e=>e.code+(e.name?':'+e.name:''));
  assert.deepEqual(codes({template:'',params:{},formula:''}),['no_template','no_values','no_formula']);
  assert.deepEqual(codes({template:'{m}',params:{},formula:'m'}),['no_range:m']);
  assert.deepEqual(codes({template:'{m}',params:{m:{min:5,max:1,step:1}},formula:'m'}),['bad_range:m']);
  assert.deepEqual(codes({template:'{m}',params:{m:{min:1,max:5,step:0}},formula:'m'}),['bad_range:m']);
  assert.deepEqual(codes({template:'{mass}',params:{mass:{min:1,max:5,step:1}},formula:'2'}),['bad_name:mass']);
  assert.deepEqual(codes({template:'{m}',params:{m:{min:1,max:5,step:1}},formula:'m g'}),['unknown_in_formula:g']);
  assert.deepEqual(codes({template:'{m}',params:{m:{min:1,max:5,step:1}},formula:'m +'}),['bad_formula']);
  assert.deepEqual(codes({template:'{m}',params:{m:{min:1,max:5,step:1}},formula:'alert(1)'}).filter(c=>c.startsWith('unknown')).length>0,true);
  assert.doesNotMatch(read('teach-tools.js'),/\beval\s*\(|new Function\s*\(/);
  assert.deepEqual(T.constants('g = 9.8, c = 3e8'),{g:9.8,c:3e8});assert.equal(T.constants('g = x'),null);assert.equal(T.constants('2g = 1'),null);
  assert.equal(T.fmtSig(12345),'12300');assert.equal(T.fmtSig(9.9),'9.90');assert.equal(T.fmtSig(0.000123),'$1.23\\times 10^{-4}$');
});

test('the blueprint counts items and points by unit and level, with row and column totals',()=>{
  const B=T.blueprint([{unit:'역학',level:'apply',pts:3},{unit:'전자기',level:'know',pts:2},{unit:'역학',level:'apply',pts:4},{unit:'',level:'odd',pts:'x'}]);
  assert.deepEqual(B.units,['역학','전자기','-']);
  assert.deepEqual(B.cells['역학'].apply,{n:2,pts:7,nos:[1,3]});
  assert.deepEqual(B.rowTotals['역학'],{n:2,pts:7});assert.deepEqual(B.cells['-'].understand,{n:1,pts:0,nos:[4]},'an unknown level counts as understanding');
  assert.deepEqual(B.byLevel.know,{n:1,pts:2});assert.deepEqual(B.total,{n:4,pts:9});
});

test('teach.html loads the tools before teach.js, keeps its CSP, and the catalogue stamps them',()=>{
  const html=read('teach.html');
  assert.ok(html.indexOf('src="teach-tools.js?v=')>html.indexOf('src="math-input.js?v=')&&html.indexOf('src="teach-tools.js?v=')<html.indexOf('src="teach.js?v='));
  assert.match(html,/script-src 'self';/);assert.doesNotMatch(html,/<script>(?!\s*<\/script>)/,'no inline script');
  assert.match(read('tools/build-site-catalogue.cjs'),/'teach-tools\.js'/);
});
