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
  form.elements.confirm.value='new-secret';form.dispatchEvent(new f.w.Event('submit',{cancelable:true}));await tick();assert.deepEqual(JSON.parse(JSON.stringify(f.calls.at(-1).body)),{old:'old-secret',password:'new-secret'});assert.equal(form.elements.old.value,'');assert.ok(form.textContent.includes('변경했습니다'));assert.deepEqual(f.errors,[]);f.close();
});
test('passwordless accounts are directed to verified email recovery; unavailable delivery is explicit',async()=>{
  const f=fixture({state:{has_password:false,email:null,email_verified:false,pending_email:null,mail_available:false}});await f.w.HL_ACCOUNT_UI.profile(f.root,f.options);
  assert.equal(f.root.querySelector('[data-password-form]'),null);assert.equal(f.root.querySelector('[data-email-form]'),null);assert.ok(f.root.textContent.includes('현재 이메일을 보낼 수 없습니다'));assert.ok(f.root.textContent.includes('현재 비밀번호가 없습니다'));assert.match(f.root.querySelector('a').href,/account\.html\?lang=ko#\/forgot-password$/);f.close();
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

test('password visibility is accessible and toggles preserve values and autocomplete',async()=>{
  const f=fixture();await f.w.HL_ACCOUNT_UI.profile(f.root,f.options);const form=f.root.querySelector('[data-password-form]'),input=form.elements.password,toggle=f.root.querySelector('[aria-controls="'+input.id+'"]');input.value='draft-new-password';assert.equal(input.autocomplete,'new-password');assert.equal(form.elements.old.autocomplete,'current-password');assert.equal(toggle.type,'button');assert.equal(toggle.closest('label'),null);toggle.click();assert.equal(input.type,'text');assert.equal(input.value,'draft-new-password');assert.equal(toggle.getAttribute('aria-pressed'),'true');toggle.click();assert.equal(input.type,'password');assert.equal(input.value,'draft-new-password');assert.ok(input.getAttribute('aria-describedby'));f.close();
});

test('live password confirmation and same-password prevention avoid API calls',async()=>{
  const f=fixture();await f.w.HL_ACCOUNT_UI.profile(f.root,f.options);const form=f.root.querySelector('[data-password-form]');form.elements.old.value='current-password';form.elements.password.value='current-password';form.elements.confirm.value='different-password';form.elements.confirm.dispatchEvent(new f.w.Event('input'));assert.equal(form.elements.confirm.getAttribute('aria-invalid'),'true');form.elements.confirm.value='current-password';form.elements.confirm.dispatchEvent(new f.w.Event('input'));assert.equal(form.elements.confirm.getAttribute('aria-invalid'),'false');form.dispatchEvent(new f.w.Event('submit',{cancelable:true}));await tick();assert.equal(f.calls.filter(call=>call.route==='/me/password').length,0);assert.match(form.textContent,/현재 비밀번호와 다른/);f.close();
});

test('forgot-password response is uniform, retains the email and enforces resend cooldown across language rendering',async()=>{
  const f=fixture();let language='ko',now=100000;f.w.Date.now=()=>now;let callback;f.w.setTimeout=fn=>{callback=fn;return 1;};f.w.clearTimeout=()=>{};const options={...f.options,language:()=>language};await f.w.HL_ACCOUNT_UI.recovery(f.root,'forgot-password',options);let form=f.root.querySelector('form');form.elements.email.value='unlisted@example.invalid';form.dispatchEvent(new f.w.Event('submit',{cancelable:true}));await tick();let submit=form.querySelector('[type=submit]');assert.equal(f.calls.filter(call=>call.route==='/auth/forgot-password').length,1);assert.equal(submit.disabled,true);assert.match(submit.textContent,/60/);assert.match(f.root.textContent,/등록·인증된 복구 이메일이라면/);assert.match(f.root.textContent,/15분/);assert.equal(form.elements.email.value,'unlisted@example.invalid');form.dispatchEvent(new f.w.Event('submit',{cancelable:true}));await tick();assert.equal(f.calls.filter(call=>call.route==='/auth/forgot-password').length,1);language='en';await f.w.HL_ACCOUNT_UI.recovery(f.root,'forgot-password',options);form=f.root.querySelector('form');submit=form.querySelector('[type=submit]');assert.equal(submit.disabled,true);assert.equal(form.elements.email.value,'unlisted@example.invalid');assert.match(f.root.textContent,/registered, verified recovery address/);now+=61000;callback();assert.equal(submit.disabled,false);assert.match(submit.textContent,/another reset link/);f.close();
});

test('expired reset links discard secrets and offer a fresh request; incorrect current passwords retain the new draft',async()=>{
  const f=fixture();const options={...f.options,api:async(method,path)=>{if(path==='/auth/reset-password')throw{code:'invalid_or_expired_link'};return f.api(method,path);}};await f.w.HL_ACCOUNT_UI.recovery(f.root,'reset-password',options);let form=f.root.querySelector('form');form.elements.password.value=form.elements.confirm.value='new-password';form.dispatchEvent(new f.w.Event('submit',{cancelable:true}));await tick();assert.equal(form.elements.password.value,'');assert.equal(form.elements.password.disabled,true);assert.ok([...f.root.querySelectorAll('a')].some(a=>a.href.endsWith('#/forgot-password')));assert.match(f.root.textContent,/만료되었거나 이미 사용/);f.close();
  const wrong=fixture();await wrong.w.HL_ACCOUNT_UI.profile(wrong.root,{...wrong.options,api:async(method,path,body)=>{if(path==='/me/password')throw{code:'bad_current_password'};return wrong.api(method,path,body);}});form=wrong.root.querySelector('[data-password-form]');form.elements.old.value='wrong-password';form.elements.password.value=form.elements.confirm.value='new-password';form.dispatchEvent(new wrong.w.Event('submit',{cancelable:true}));await tick();assert.equal(form.elements.password.value,'new-password');assert.equal(form.elements.old.getAttribute('aria-invalid'),'true');assert.match(form.textContent,/현재 비밀번호가 맞지 않습니다/);wrong.close();
});

test('legacy generated identifiers get an optional one-time username setup without changing role or account identity',async()=>{
  const f=fixture();const user={id:19,username:'g_synthetic123',username_kind:'generated',username_setup_available:true,unique_identifier:'g_synthetic123',role:'admin'};let updated;f.w.HL_ACCOUNT_UI.username(f.root,{...f.options,user,api:async(method,path,body)=>{assert.equal(method,'POST');assert.equal(path,'/me/username');assert.equal(body.username,'chosen_admin');return{user:{...user,username:'chosen_admin',username_kind:'chosen',username_setup_available:false}};},done:value=>updated=value});const form=f.root.querySelector('form');assert.match(f.root.textContent,/고유번호 · g_synthetic123/);assert.match(f.root.textContent,/관리자 권한, 학습 기록/);form.elements.username.value='chosen_admin';form.dispatchEvent(new f.w.Event('submit',{cancelable:true}));await tick();assert.equal(updated.id,19);assert.equal(updated.role,'admin');assert.equal(updated.unique_identifier,'g_synthetic123');assert.equal(form.querySelector('[type=submit]').disabled,true);f.close();
});

test('unchanged-password reset errors retain the proof and allow a different password without consuming it',async()=>{
  const f=fixture();let attempts=0,done=0;await f.w.HL_ACCOUNT_UI.recovery(f.root,'reset-password',{...f.options,api:async(method,path,body)=>{if(path==='/auth/reset-password'){attempts++;assert.equal(body.token,'a'.repeat(43));if(attempts===1)throw{code:'password_unchanged'};}return{ok:true};},done:()=>done++});const form=f.root.querySelector('form');form.elements.password.value=form.elements.confirm.value='same-password';form.dispatchEvent(new f.w.Event('submit',{cancelable:true}));await tick();assert.equal(form.elements.password.disabled,false);assert.equal(done,0);assert.match(form.textContent,/현재 비밀번호와 다른/);form.elements.password.value=form.elements.confirm.value='different-password';form.dispatchEvent(new f.w.Event('submit',{cancelable:true}));await tick();assert.equal(attempts,2);assert.equal(done,1);f.close();
});

test('the Lab profile setup wrapper accepts only the same account and role and invalidates stale views',()=>{
  const vm=require('node:vm'),source=fs.readFileSync(path.join(site,'index.html'),'utf8'),block=source.slice(source.indexOf('function cmAccountUsername('),source.indexOf('function cmAccountSecurity('));let options,invalidated=0,done=0,chips=0;const context={window:{HL_ACCOUNT_UI:{username(_root,value){options=value;}}},lang:'ko',cm:{me:{id:19,role:'admin',username:'g_synthetic',username_setup_available:true}},cmApi(){},cmInvalidate(){invalidated++;},arChip(){chips++;},cmMeP:1,cmBootstrapP:1,cmOverviewP:1};vm.createContext(context);vm.runInContext(block,context);context.cmAccountUsername({},()=>done++);assert.equal(options.user.username_setup_available,true);assert.throws(()=>options.done({id:19,role:'user',username:'chosen'}),value=>value.code==='account_changed');assert.equal(context.cm.me.role,'admin');options.done({id:19,role:'admin',username:'chosen',username_kind:'chosen'});assert.equal(context.cm.me.id,19);assert.equal(context.cm.me.role,'admin');assert.equal(context.cm.me.username,'chosen');assert.equal(invalidated,1);assert.equal(chips,1);assert.equal(done,1);assert.equal(context.cmOverviewP,null);for(const name of ['index.html','arena.js'])assert.equal(fs.readFileSync(path.join(site,name),'utf8').includes('g_QFAlJRmIyg'),false);
});
test('a social sign-up sends the page consent with its username; a missing required box stops before the server is called',async()=>{
  const f=fixture(),user={id:21,username:'~pending_x',username_required:true,consent_required:true,role:'user'},sent=[];let agreed=false;
  f.w.HL_ACCOUNT_UI.username(f.root,{...f.options,user,consent:()=>{if(!agreed)throw{code:'consent_required'};return{terms:true,privacy:true,age14:true,train:false};},api:async(method,route,body)=>{sent.push(body);return{user:{...user,username:'chosen_social',username_required:undefined}};}});
  const form=f.root.querySelector('form');form.elements.username.value='chosen_social';form.dispatchEvent(new f.w.Event('submit',{cancelable:true}));await tick();
  assert.equal(sent.length,0);assert.match(form.textContent,/필수 항목/);
  agreed=true;form.dispatchEvent(new f.w.Event('submit',{cancelable:true}));await tick();
  assert.deepEqual(JSON.parse(JSON.stringify(sent)),[{username:'chosen_social',consent:{terms:true,privacy:true,age14:true,train:false}}]);f.close();
});
