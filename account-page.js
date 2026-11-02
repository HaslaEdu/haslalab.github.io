(()=>{
  'use strict';
  const params=new URLSearchParams(location.search),hash=new URLSearchParams(location.hash.split('?')[1]||''),media=matchMedia('(prefers-color-scheme: dark)');
  const read=key=>{try{return localStorage.getItem(key)||''}catch{return''}},write=(key,value)=>{try{localStorage.setItem(key,value)}catch{}};
  let language=['ko','en'].includes(params.get('lang'))?params.get('lang'):'ko';
  let preference=['light','dark','system'].includes(params.get('theme'))?params.get('theme'):read('hlThemePreference')||read('hlTheme')||'light';
  const purpose=['forgot-password','reset-password','verify-email'].find(value=>location.hash.startsWith('#/'+value))||'forgot-password';
  let token=hash.get('token')||'';
  // The credential never reaches analytics, browser storage, a Referer or the
  // visible URL after this self-script-only page starts.
  if(hash.has('token')){hash.delete('token');const next=new URL(location.href);next.hash='/'+purpose+(hash.size?'?'+hash:'');history.replaceState(history.state,'',next)}
  const root=document.getElementById('accountMain');
  const api=async(method,path,body)=>{let response;try{response=await fetch('https://haslalab-community-edge.haslalab.workers.dev/api'+path,{method,credentials:'omit',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined})}catch{throw{code:'network'}}const result=await response.json().catch(()=>({error:'network'}));if(!response.ok)throw{code:result.error,status:response.status};return result};
  function theme(){try{const next=new URL(location.href);if(next.searchParams.has("theme")){next.searchParams.set("theme",preference);history.replaceState(history.state,"",next)}}catch{}const dark=preference==='dark'||preference==='system'&&media.matches,value=dark?'dark':'light';document.documentElement.dataset.theme=value;document.getElementById('accountLogo').src='favicon-'+value+'.svg?v=20261103-brands';document.getElementById('accountFavicon').href='favicon-'+value+'.svg?v=20261103-brands';const button=document.getElementById('accountTheme');button.textContent=dark?'☀':'◐';button.setAttribute('aria-pressed',String(dark));button.setAttribute('aria-label',language==='en'?(dark?'White mode':'Dark mode'):(dark?'화이트 모드':'다크 모드'))}
  function render(){document.documentElement.lang=language;document.title=(language==='en'?'Account security':'계정 보안')+' · HaslaLab';document.getElementById('accountLanguage').textContent=language==='ko'?'EN':'KO';document.getElementById('accountLanguage').setAttribute('aria-label',language==='ko'?'Switch to English':'한국어로 변경');theme();window.HL_ACCOUNT_UI.recovery(root,purpose,{api,language:()=>language,token,done:()=>{token=''}})}
  document.getElementById('accountLanguage').addEventListener('click',()=>{language=language==='ko'?'en':'ko';render()});
  addEventListener('haslaedu:appearance',event=>{const value=event.detail;if(!value||value.version!==1||!['system','light','dark'].includes(value.preference)||!['light','dark'].includes(value.theme)||value.preference!=='system'&&value.preference!==value.theme)return;preference=value.preference;write('hlTheme',value.theme);write('hlThemePreference',preference);theme()});
  document.getElementById('accountTheme').addEventListener('click',()=>{preference=document.documentElement.dataset.theme==='dark'?'light':'dark';write('hlTheme',preference);write('hlThemePreference',preference);theme()});media.addEventListener?.('change',theme);render();
})();
