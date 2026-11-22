/* Typed answers: what a learner types on the keypad is compared with the problem's answer by value. */
const test=require('node:test'),assert=require('node:assert/strict'),path=require('path'),fs=require('fs');
const M=require(path.join(__dirname,'..','math-input.js'));
const ok=(input,choice)=>M.check(input,M.answerOf(choice)).ok;

test('equivalent forms of a formula count; a different formula does not',()=>{
  assert.ok(ok('2*sqrt(g L)','$2\\sqrt{gL}$'));assert.ok(ok('sqrt(4gL)','$2\\sqrt{gL}$'));assert.ok(!ok('sqrt(gL)','$2\\sqrt{gL}$'));
  assert.ok(ok('1/2 m v^2','$\\frac{1}{2}mv^2$'));assert.ok(ok('mv^2/2','$\\dfrac{mv^{2}}{2}$'));
  assert.ok(ok('2π sqrt(L/g)','$2\\pi\\sqrt{\\dfrac{L}{g}}$'));assert.ok(ok('v_0^2/(2g)','$\\frac{v_{0}^{2}}{2g}$'));assert.ok(ok('mg sin θ','$mg\\sin\\theta$'));
});
test('numbers carry their unit and a tolerance; letters in a number answer are refused, not graded',()=>{
  const a=M.answerOf('12 m/s');assert.equal(a.kind,'num');assert.equal(a.unit,'m/s');
  assert.ok(ok('3.0e8','$3.0\\times10^{8}$ m/s'));assert.ok(ok('3*10^8','$3.0\\times10^{8}$ m/s'));
  assert.equal(M.check('2x',M.answerOf('12')).error,'vars');assert.equal(M.check('2+',M.answerOf('12')).error,'syntax');
  assert.equal(M.answerOf('Eight times as far'),null,'a choice in words keeps the choices');
});
test('every exam-track answer that can be typed checks against itself, and no wrong choice passes',()=>{
  let typed=0;
  for(const t of JSON.parse(fs.readFileSync(path.join(__dirname,'..','practice/tracks.json'),'utf8')).tracks)
    for(const it of JSON.parse(fs.readFileSync(path.join(__dirname,'..',`practice/track/${t.key}.json`),'utf8')).items){
      if(it.type!=='mc')continue;const a=M.answerOf(it.choices[it.answer]);if(!a)continue;typed++;
      const own=a.kind==='num'?String(a.value):M.fromLatex(a.tex);assert.ok(M.check(own,a).ok,it.id);
      for(const [i,c] of it.choices.entries()){if(i===it.answer)continue;const d=M.answerOf(c);if(!d||d.kind!==a.kind||a.kind==='num')continue;assert.ok(!M.check(M.fromLatex(d.tex),a).ok,`${it.id} choice ${i}`);}
    }
  assert.ok(typed>=100,'most choice problems become typed answers: '+typed);
});
