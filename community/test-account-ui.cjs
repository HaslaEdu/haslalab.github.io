// DOM fixture only; no browser automation, real account or outgoing mail.
const fs=require('node:fs'),path=require('node:path'),test=require('node:test'),assert=require('node:assert/strict');
const {JSDOM,VirtualConsole}=require('jsdom');
const site=path.resolve(__dirname,'..'),ui=fs.readFileSync(path.join(site,'account-ui.js'),'utf8'),page=fs.readFileSync(path.join(site,'account-page.js'),'utf8');
const tick=()=>new Promise(resolve=>setTimeout(resolve,0));
function fixture({standalone=false,token='a'.repeat(43),lang='ko',state={has_password:true,email:'owner@example.com',email_verified:true,mail_available:true}}={}){
  const errors=[],calls=[],virtual=new VirtualConsole();virtual.on('jsdomError',e=>errors.push(e.message));
  const html=standalone?fs.readFileSync(path.join(site,'account.html'),'utf8'):'<!doctype html><main id="root"></main>';
  const dom=new JSDOM(html,{url:'https://haslalab.org/account.html?lang='+lang+'#/reset-password?token='+token+'&keep=1',runScripts:'outside-only',virtualConsole:virtual}),w=dom.window;
  w.matchMedia=()=>({matches:false,addEventListener(){}});
  const api=async(method,route,body)=>{calls.push({method,route,body});if(route==='/me/security')return state;if(route==='/auth/recovery')return {mail_available:state.mail_available};return{ok:true}};
  w.eval(ui);return{dom,w,d:w.document,calls,errors,api,root:w.document.getElementById(standalone?'accountMain':'root'),options:{api,language:()=>lang,token},close(){dom.window.close()}};
}
test('account security requires current password and new-password confirmation; profile data is escaped',async()=>{
  const f=fixture({state:{has_password:true,email:'<img src=x onerror=alert(1)>',email_verified:true,mail_available:true}});await f.w.HL_ACCOUNT_UI.profile(f.root,f.options);
  assert.equal(f.root.querySelector('img'),null);const form=f.root.querySelector('[data-password-form]');assert.equal(form.elements.old.required,true);assert.equal(form.elements.confirm.required,true);
  form.elements.old.value='old-secret';form.elements.password.value='new-secret';form.elements.confirm.value='different';form.dispatchEvent(new f.w.Event('submit',{cancelable:true}));await tick();assert.equal(f.calls.filter(x=>x.route==='/me/password').length,0);
  form.elements.confirm.value='new-secret';form.dispatchEvent(new f.w.Event('submit',{cancelable:true}));await tick();assert.deepEqual(JSON.parse(JSON.stringify(f.calls.at(-1).body)),{old:'old-secret',password:'new-secret'});assert.equal(form.elements.old.value,'');assert.ok(form.textContent.includes('바꿨습니다'));assert.deepEqual(f.errors,[]);f.close();
});
test('passwordless accounts are directed to verified email recovery; unavailable delivery is explicit',async()=>{
  const f=fixture({state:{has_password:false,email:null,email_verified:false,pending_email:null,mail_available:false}});await f.w.HL_ACCOUNT_UI.profile(f.root,f.options);
  assert.equal(f.root.querySelector('[data-password-form]'),null);assert.equal(f.root.querySelector('[data-email-form]'),null);assert.ok(f.root.textContent.includes('이메일 전송을 준비 중'));assert.ok(f.root.textContent.includes('첫 비밀번호'));assert.match(f.root.querySelector('a').href,/account\.html\?lang=ko#\/forgot-password$/);f.close();
});
test('reset proof stays out of the DOM; mismatches do not call the server and success clears form secrets',async()=>{
  const f=fixture();let done=false;await f.w.HL_ACCOUNT_UI.recovery(f.root,'reset-password',{...f.options,done:()=>{done=true}});assert.ok(!f.root.innerHTML.includes('a'.repeat(43)));
  const form=f.root.querySelector('form');form.elements.password.value='new-password';form.elements.confirm.value='other-password';form.dispatchEvent(new f.w.Event('submit',{cancelable:true}));await tick();assert.equal(f.calls.length,0);
  form.elements.confirm.value='new-password';form.dispatchEvent(new f.w.Event('submit',{cancelable:true}));await tick();assert.equal(f.calls[0].route,'/auth/reset-password');assert.equal(f.calls[0].body.token,'a'.repeat(43));assert.equal(form.elements.password.value,'');assert.equal(form.elements.password.disabled,true);assert.equal(done,true);f.close();
});
test('verification waits for an explicit click; malformed links cannot call an endpoint',async()=>{
  const f=fixture();await f.w.HL_ACCOUNT_UI.recovery(f.root,'verify-email',f.options);assert.equal(f.calls.length,0);f.root.querySelector('form').dispatchEvent(new f.w.Event('submit',{cancelable:true}));await tick();assert.equal(f.calls[0].route,'/auth/verify-email');f.close();
  const bad=fixture({token:'invalid'});await bad.w.HL_ACCOUNT_UI.recovery(bad.root,'reset-password',bad.options);assert.equal(bad.root.querySelector('button').disabled,true);assert.equal(bad.calls.length,0);bad.close();
});
test('standalone page removes URL proof, preserves history/hash, uses a fixed API, and changes theme without losing draft',async()=>{
  const f=fixture({standalone:true});f.w.history.replaceState({kept:1},'',f.w.location.href);f.w.fetch=async(url,options)=>{assert.match(url,/^https:\/\/haslalab-community-edge\.haslalab\.workers\.dev\/api\//);assert.equal(options.credentials,'omit');return{ok:true,json:async()=>({ok:true})}};
  f.w.eval(page);assert.equal(new URLSearchParams(f.w.location.hash.split('?')[1]).has('token'),false);assert.equal(new URLSearchParams(f.w.location.hash.split('?')[1]).get('keep'),'1');assert.equal(f.w.history.state.kept,1);
  const form=f.root.querySelector('form');form.elements.password.value='unsaved-secret';form.elements.confirm.value='unsaved-secret';f.d.getElementById('accountTheme').click();assert.equal(f.d.documentElement.dataset.theme,'dark');assert.equal(f.root.querySelector('form'),form);assert.equal(form.elements.password.value,'unsaved-secret');assert.match(f.d.getElementById('accountLogo').src,/favicon-dark\.svg(?:\?|$)/);
  f.d.getElementById('accountLanguage').click();assert.equal(f.d.documentElement.lang,'en');assert.equal(f.root.querySelector('[name=password]').value,'unsaved-secret');assert.deepEqual(f.errors,[]);f.close();
});
test('recovery document has no third-party scripts or inline handlers and uses restrictive credential-safe CSP',()=>{
  const html=fs.readFileSync(path.join(site,'account.html'),'utf8'),dom=new JSDOM(html),d=dom.window.document;
  assert.ok([...d.scripts].every(script=>script.src&&!/^https?:/.test(script.src)&&!script.textContent.trim()));assert.equal(d.querySelectorAll('[onclick],[onload]').length,0);
  const csp=d.querySelector('meta[http-equiv="Content-Security-Policy"]').content;assert.ok(csp.includes("script-src 'self'"));assert.ok(csp.includes("form-action 'none'"));assert.equal(d.querySelector('meta[name=referrer]').content,'no-referrer');dom.window.close();
});
