// DOM fixture only: the consent boxes, the dialog for accounts without consent, and the training toggle in index.html.
const fs=require('node:fs'),path=require('node:path'),test=require('node:test'),assert=require('node:assert/strict');
const {JSDOM}=require('node:module').createRequire(path.resolve(__dirname,'../community/package.json'))('jsdom');
const html=fs.readFileSync(path.join(__dirname,'..','index.html'),'utf8');
const slice=(from,to)=>{const a=html.indexOf(from),b=html.indexOf(to,a);assert.ok(a>=0&&b>a,from);return html.slice(a,b);};
const dictionary=slice('const CMT = {','const cm = {');
const consent=slice('let cmConsentInfoP=null;','function cmLogin(');
const plain=v=>JSON.parse(JSON.stringify(v));   // objects made inside the page are of its realm
const tick=()=>new Promise(resolve=>setTimeout(resolve,0));
function page({info={age_required:true},me=null,lang='ko',status}={}){
  const dom=new JSDOM('<!doctype html><body><main id="root"></main></body>',{url:'https://haslalab.org/#/community',runScripts:'outside-only'}),w=dom.window,calls=[];
  w.__api=async(method,route,body)=>{calls.push({method,route,body});if(route==='/consent/info')return info;if(route==='/me/consent'&&method==='GET')return status;if(route==='/me/consent/train')return{ok:true,train_ok:body.train};if(route==='/me/consent')return{ok:true,user:{...me,consent_required:undefined}};return{ok:true};};
  w.eval(`var lang=${JSON.stringify(lang)};${dictionary};var cm={me:${JSON.stringify(me)}};var cmMeP=1,cmBootstrapP=1,cmOverviewP=1;
    const cmApi=(...a)=>window.__api(...a);const cmErr=e=>CMT[lang].err[e&&e.code]||CMT[lang].err.server_error;const cmTok=()=>{};${consent}`);
  return{w,d:w.document,calls,close(){dom.window.close();}};
}
test('the boxes link the policies, show the age box only when the server asks, and refuse a missing required box locally',async()=>{
  const p=page({info:{age_required:false}}),box=p.d.getElementById('root');box.innerHTML=p.w.eval('cmConsentHtml()');const read=p.w.eval('cmConsentWire')(box);await tick();
  assert.ok(box.querySelector('a[href="terms.html"]'));assert.ok(box.querySelector('a[href="privacy.html"]'));
  assert.match(box.textContent,/\[필수\] 이용약관 동의/);assert.match(box.textContent,/\[선택\] 내 답안과 채점 결과를 AI 채점 개선\(학습\)에 최대 1년/);assert.match(box.textContent,/참고용 결과이며 실제 대회 점수와 다를 수/);
  assert.equal(box.querySelector('[data-age]').hidden,true);
  assert.throws(()=>read(),e=>e.code==='consent_required');
  box.querySelector('[name=cTerms]').checked=box.querySelector('[name=cPrivacy]').checked=true;
  assert.deepEqual({...read()},{terms:true,privacy:true,age14:false,train:false,aiTrain:false});
  assert.match(box.textContent,/\[선택\] 하슬라 AI와 나눈 대화를 AI 답변 개선/);box.querySelector('[name=cAiTrain]').checked=true;
  assert.deepEqual({...read()},{terms:true,privacy:true,age14:false,train:false,aiTrain:true},'the AI-chat box is its own choice');
  const kr=page(),b2=kr.d.getElementById('root');b2.innerHTML=kr.w.eval('cmConsentHtml()');const r2=kr.w.eval('cmConsentWire')(b2);await tick();
  assert.equal(b2.querySelector('[data-age]').hidden,false);b2.querySelector('[name=cTerms]').checked=b2.querySelector('[name=cPrivacy]').checked=true;
  assert.throws(()=>r2(),e=>e.code==='age_required');b2.querySelector('[name=cAge]').checked=b2.querySelector('[name=cTrain]').checked=true;
  assert.deepEqual({...r2()},{terms:true,privacy:true,age14:true,train:true,aiTrain:false});p.close();kr.close();
});
test('an account without consent gets one dialog that posts /me/consent; a pending social sign-up is left to its username step',async()=>{
  const pending=page({me:{id:3,username_required:true,consent_required:true}});pending.w.eval('cmConsentGate()');assert.equal(pending.d.getElementById('cmConsentDlg'),null);pending.close();
  const p=page({me:{id:4,consent_required:true}});p.w.eval('cmConsentGate()');p.w.eval('cmConsentGate()');assert.equal(p.d.querySelectorAll('#cmConsentDlg').length,1);await tick();
  const f=p.d.querySelector('#cmConsentDlg form');f.dispatchEvent(new p.w.Event('submit',{cancelable:true}));await tick();
  assert.equal(p.calls.filter(c=>c.route==='/me/consent').length,0);assert.match(f.querySelector('.cmerr').textContent,/필수 항목/);
  for(const n of ['cTerms','cPrivacy','cAge'])f.querySelector(`[name=${n}]`).checked=true;
  f.dispatchEvent(new p.w.Event('submit',{cancelable:true}));await tick();await tick();
  assert.deepEqual(plain(p.calls.find(c=>c.route==='/me/consent').body),{consent:{terms:true,privacy:true,age14:true,train:false,aiTrain:false}});
  assert.equal(p.d.getElementById('cmConsentDlg'),null);assert.equal(p.w.eval('cm.me.consent_required'),undefined);p.close();
  const none=page({me:{id:5}});none.w.eval('cmConsentGate()');assert.equal(none.d.getElementById('cmConsentDlg'),null);none.close();
});
test('the profile toggle shows the server state and withdraws through /me/consent/train',async()=>{
  const p=page({me:{id:6,train_ok:false},status:{consent_required:false,train_ok:true},lang:'en'}),box=p.d.getElementById('root');
  await p.w.eval('cmTrainToggle')(box);assert.match(box.textContent,/Agreed/);
  box.querySelector('[data-train]').click();await tick();await tick();
  assert.deepEqual(plain(p.calls.at(-1)),{method:'POST',route:'/me/consent/train',body:{train:false}});assert.match(box.textContent,/Withdrawn/);assert.equal(p.w.eval('cm.me.train_ok'),false);p.close();
});
