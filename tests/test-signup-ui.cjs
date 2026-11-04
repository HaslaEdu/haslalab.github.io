// DOM fixture only: the sign-up form's email, «send code» button and code field in index.html (cmSignup).
const fs=require('node:fs'),path=require('node:path'),test=require('node:test'),assert=require('node:assert/strict');
const {JSDOM}=require('node:module').createRequire(path.resolve(__dirname,'../community/package.json'))('jsdom');
const html=fs.readFileSync(path.join(__dirname,'..','index.html'),'utf8');
const slice=(from,to)=>{const a=html.indexOf(from),b=html.indexOf(to,a);assert.ok(a>=0&&b>a,from);return html.slice(a,b);};
const dictionary=slice('const CMT = {','const cm = {');
const consent=slice('let cmConsentInfoP=null;','function cmLogin(');
const signup=slice('function cmSignup(root){','/* the profile picture');
const plain=v=>JSON.parse(JSON.stringify(v));
const tick=()=>new Promise(resolve=>setTimeout(resolve,0));
// `fail` maps a route to the error code the stand-in server answers with
function page({lang='ko',fail={}}={}){
  const dom=new JSDOM('<!doctype html><body><main id="root"></main></body>',{url:'https://haslalab.org/#/community/signup',runScripts:'outside-only'}),w=dom.window,calls=[];
  w.__api=async(method,route,body)=>{calls.push({method,route,body});if(route==='/consent/info')return{age_required:false};if(fail[route])throw{code:fail[route]};if(route==='/signup')return{token:'t',user:{id:1}};return{ok:true};};
  w.eval(`var lang=${JSON.stringify(lang)};${dictionary};var cm={me:null};var done=[];
    const cmApi=(...a)=>window.__api(...a);const cmErr=e=>CMT[lang].err[e&&e.code]||CMT[lang].err.server_error;
    const cmNickCheck=()=>async()=>true;const cmAuthDone=r=>done.push(r);const arOauth=()=>{};${consent}${signup}`);
  const root=w.document.getElementById('root');w.eval('cmSignup')(root);
  const f=root.querySelector('#cmS'),fill=(name,value)=>{f.querySelector(`[name=${name}]`).value=value;};
  // browsers expose form controls by name (f.email); jsdom does not, so the page's code gets them the same way here
  for(const el of f.elements)if(el.name&&!(el.name in f))Object.defineProperty(f,el.name,{get:()=>f.elements[el.name]});
  const submit=async()=>{f.dispatchEvent(new w.Event('submit',{cancelable:true}));for(let i=0;i<4;i++)await tick();};
  const ready=()=>{fill('username','new_user');fill('nickname','New user');fill('password','fixture-password');fill('password2','fixture-password');
    f.querySelector('[name=agree]').checked=f.querySelector('[name=cTerms]').checked=f.querySelector('[name=cPrivacy]').checked=true;};
  return{w,f,calls,fill,submit,ready,err:()=>f.querySelector('.cmerr').textContent,close(){w.close();}};
}
test('the code button checks the address, sends it with the language and waits before another send',async()=>{
  const p=page(),send=p.f.querySelector('[data-code]');
  assert.equal(send.textContent,'인증 코드 받기');assert.ok(p.f.querySelector('.rules'),'the community rules stay');assert.ok(p.f.querySelector('.cmconsent'),'the consent boxes stay');
  send.click();await tick();assert.match(p.err(),/이메일 주소를 확인/);assert.equal(p.calls.filter(c=>c.route==='/signup/email-code').length,0);
  p.fill('email',' owner@example.com ');send.click();await tick();await tick();
  assert.deepEqual(plain(p.calls.find(c=>c.route==='/signup/email-code')),{method:'POST',route:'/signup/email-code',body:{email:'owner@example.com',lang:'ko'}});
  assert.equal(send.disabled,true);assert.match(send.textContent,/^60초 뒤 다시 받기$/);assert.match(p.f.querySelector('[data-codeinfo]').textContent,/코드를 보냈습니다/);
  p.close();
});
test('a refused send says why in English and leaves the button usable',async()=>{
  const p=page({lang:'en',fail:{'/signup/email-code':'email_taken'}}),send=p.f.querySelector('[data-code]');
  assert.equal(send.textContent,'Send code');p.fill('email','taken@example.com');send.click();await tick();await tick();
  assert.match(p.err(),/already on an account/);assert.equal(send.disabled,false);p.close();
  const q=page({fail:{'/signup/email-code':'mail_unavailable'}});q.fill('email','a@example.com');q.f.querySelector('[data-code]').click();await tick();await tick();
  assert.match(q.err(),/인증 메일을 보낼 수 없습니다/);q.close();
});
test('the sign-up needs the code and sends the address and code with the rest',async()=>{
  const p=page();p.ready();
  await p.submit();assert.match(p.err(),/이메일 주소를 확인/);
  p.fill('email','owner@example.com');await p.submit();assert.match(p.err(),/6자리 인증 코드/);assert.equal(p.calls.filter(c=>c.route==='/signup').length,0);
  p.fill('code','123 456');await p.submit();
  assert.deepEqual(plain(p.calls.find(c=>c.route==='/signup').body),{username:'new_user',nickname:'New user',password:'fixture-password',consent:{terms:true,privacy:true,age14:false,train:false},email:'owner@example.com',code:'123456'});
  assert.equal(p.w.eval('done.length'),1);p.close();
});
test('the code errors from the server read in both languages',async()=>{
  for(const [lang,code,text] of [['ko','code_expired',/만료/],['ko','code_attempts',/너무 여러 번/],['ko','code_invalid',/맞지 않습니다/],['en','code_expired',/expired/],['en','code_attempts',/Too many wrong codes/],['en','email_taken',/already on an account/]]){
    const p=page({lang,fail:{'/signup':code}});p.ready();p.fill('email','owner@example.com');p.fill('code','123456');await p.submit();
    assert.match(p.err(),text,lang+' '+code);p.close();
  }
});
