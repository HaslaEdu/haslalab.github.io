// Instrument generation and saved measurements belong to the authenticated Worker.
const $=id=>document.getElementById(id),screen=$('screen'),q=new URLSearchParams(location.search);
const lang=q.get('lang')==='en'?'en':'ko';
const embedded=q.get('embed')==='1';
let problemId=Number(q.get('id')),inside=false,revision=0,sessionId=null,busy=false;
let accountChanged=false;
const validProblemId=()=>Number.isSafeInteger(problemId)&&problemId>0;
if(embedded)document.body.dataset.embedded='true';
let commandHistory=[],historyIndex=0,fullLog=[];
let apiBase='https://haslalab-community-edge.haslalab.workers.dev';
try{apiBase=(localStorage.getItem('hlCmApi')||apiBase).replace(/\/+$/,'');}catch{}
if(apiBase==='https://haslalab-community.haslalab.workers.dev')apiBase='https://haslalab-community-edge.haslalab.workers.dev';
const ownerToken=(()=>{try{return localStorage.getItem('hlCmTok')||'';}catch{return '';}})();
const message={ko:{busy:'장치에 연결하는 중…',login:'계측하려면 하슬라랩에 로그인하세요.',changed:'다른 창에서 측정 기록이 바뀌었습니다. 기록을 다시 불러왔습니다. 명령어를 확인한 뒤 실행하세요.',network:'연결을 확인한 뒤 같은 명령어를 다시 실행하세요.',retry:'미완료 요청이 있습니다. 같은 명령어를 다시 입력하면 중복 측정 없이 결과를 확인합니다.'},en:{busy:'Connecting to the apparatus…',login:'Sign in to HaslaLab to use the apparatus.',changed:'The measurements changed in another tab. Records have been refreshed. Review them before running the command again.',network:'Check the connection and retry the same command.',retry:'A request is pending. Repeat the same command to retrieve its result without another measurement.'}}[lang];
function line(value,kind=''){const n=document.createElement('pre');n.className='entry '+kind;n.textContent=value;screen.append(n);fullLog.push(value);screen.scrollTop=screen.scrollHeight;}
function setPrompt(){ $('prompt').textContent=inside?'waterhammer> ':'student@haslalab:~/experiment$ ';}
function math(el,text){
 for(const chunk of String(text||'').split(/(\$\$[\s\S]*?\$\$|\$[^$\n]+\$|`[^`\n]+`)/g)){
  if(!chunk)continue;const node=document.createElement(chunk.startsWith('$$')?'div':chunk.startsWith('`')?'code':'span');
  if(chunk.startsWith('$')&&chunk.endsWith('$')){const display=chunk.startsWith('$$'),n=display?2:1;window.katex.render(chunk.slice(n,-n),node,{displayMode:display,throwOnError:false,trust:false});}
  else node.textContent=chunk.startsWith('`')?chunk.slice(1,-1):chunk;el.append(node);
 }
 return el;
}
const para=text=>math(document.createElement('p'),text);
function download(data,name,type='text/plain;charset=utf-8'){const blob=new Blob([data],{type}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function mode(cmd,focus=true){cmd=embedded||cmd;$('problem').hidden=cmd;$('terminal').hidden=!cmd;$('problemTab').setAttribute('aria-selected',String(!cmd));$('cmdTab').setAttribute('aria-selected',String(cmd));if(cmd&&focus)$('command').focus();}
$('problemTab').onclick=()=>mode(false);$('cmdTab').onclick=()=>mode(true);
const selectedTheme=q.get('theme');let storedTheme;try{storedTheme=localStorage.getItem('hlTheme');}catch{}
document.body.dataset.theme=selectedTheme==='dark'||selectedTheme!=='light'&&(storedTheme==='dark'||!storedTheme&&matchMedia('(prefers-color-scheme:dark)').matches)?'dark':'light';
$('theme').onclick=()=>{document.body.dataset.theme=document.body.dataset.theme==='dark'?'light':'dark';};
function embeddedNotice(text,signIn=false){
 if(!embedded)return;
 $('embeddedNotice').hidden=!text;$('embeddedMessage').textContent=text;$('embeddedLogin').hidden=!signIn;
}
function commandState(){
 const blocked=embedded&&(!validProblemId()||!ownerToken||accountChanged);
 $('command').disabled=busy||blocked;
 if(embedded){$('downloadCsv').disabled=blocked;$('downloadAllCsv').disabled=blocked;}
}
if(embedded){
 document.documentElement.lang=lang;
 $('embeddedLogin').href='../../?lang='+lang+'#/login';
 $('embeddedLogin').onclick=()=>{try{sessionStorage.setItem('hlCmBack','#/monthly/p/'+problemId);}catch{}};
 if(lang==='en'){
  $('embeddedLogin').textContent='Sign in';$('command').setAttribute('aria-label','Experiment command');
  $('terminal').setAttribute('aria-label','Experiment command terminal');$('screen').setAttribute('aria-label','Experiment log');
  $('clear').textContent='Clear screen';$('saveLog').textContent='Save log';$('downloadCsv').textContent='Latest trace CSV';$('downloadAllCsv').textContent='All records CSV';
 }
 window.addEventListener('message',event=>{
  if(event.source!==parent||event.origin!==location.origin)return;
  if(event.data?.type==='haslalab-experiment-theme'&&['dark','light'].includes(event.data.theme))document.body.dataset.theme=event.data.theme;
 });
 window.addEventListener('storage',event=>{
  if(event.key!=='hlCmTok'&&event.key!==null)return;
  let token;try{token=localStorage.getItem('hlCmTok')||'';}catch{return;}
  if(token===ownerToken)return;
  accountChanged=true;inside=false;pending=null;setPrompt();commandState();
  embeddedNotice(lang==='ko'?'로그인 정보가 바뀌었습니다. 문제 페이지를 새로고침하세요.':'Your sign-in changed. Reload the problem page.');
 });
}
function plot(trace){
 const ns='http://www.w3.org/2000/svg',figure=document.createElement('figure');figure.className='trace';
 const svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 880 285');svg.setAttribute('role','img');svg.setAttribute('aria-label',`${trace.sensor} RUN ${trace.run_id} pressure-time graph`);
 const points=trace.points,ys=points.map(p=>p.r_kPa),lo=Math.floor((Math.min(...ys)-3)/10)*10,hi=Math.ceil((Math.max(...ys)+3)/10)*10;
 const tmin=points[0].t_ms,tmax=points.at(-1).t_ms,sx=t=>64+760*(t-tmin)/(tmax-tmin),sy=r=>235-190*(r-lo)/(hi-lo);
 const node=(tag,attrs,text)=>{const n=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,v);if(text!==undefined)n.textContent=text;svg.append(n);};
 for(let i=0;i<=4;i++){const v=lo+(hi-lo)*i/4,y=sy(v);node('line',{x1:64,y1:y,x2:824,y2:y,stroke:'#29313c'});node('text',{x:54,y:y+4,'text-anchor':'end',fill:'#adbacb','font-size':12},v.toFixed(0));}
 for(let t=0;t<=160;t+=20){const x=sx(t);node('line',{x1:x,y1:45,x2:x,y2:235,stroke:'#202935'});node('text',{x,y:255,'text-anchor':'middle',fill:'#adbacb','font-size':12},String(t));}
 node('text',{x:15,y:25,fill:'#cbd5e1','font-size':13},'r (kPa)');node('text',{x:825,y:276,'text-anchor':'end',fill:'#cbd5e1','font-size':13},'t (ms)');
 node('polyline',{points:points.map(p=>`${sx(p.t_ms).toFixed(2)},${sy(p.r_kPa).toFixed(2)}`).join(' '),fill:'none',stroke:'#78c7d8','stroke-width':1.4});
 const cap=document.createElement('figcaption');cap.textContent=`RUN ${trace.run_id} · ${trace.sensor} · x=${trace.x_m} m · τ=${trace.close_ms} ms`;figure.append(svg,cap);screen.append(figure);screen.scrollTop=screen.scrollHeight;
}
async function api(method,path,body){
 let currentToken;try{currentToken=localStorage.getItem('hlCmTok')||'';}catch{}
 if(currentToken!==ownerToken){if(embedded)accountChanged=true;throw{code:'account_changed'};}
 const r=await fetch(apiBase+'/api'+path,{method,cache:'no-store',signal:AbortSignal.timeout(30000),headers:{...(ownerToken?{Authorization:'Bearer '+ownerToken}:{}),...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{})});
 const data=await r.json();
 if(embedded){let current;try{current=localStorage.getItem('hlCmTok')||'';}catch{}if(current!==ownerToken){accountChanged=true;throw{code:'account_changed'};}}
 if(!r.ok)throw{code:data.error||'experiment_unavailable',...data,status:r.status};return data;
}
async function restore(){
 if(!ownerToken){line(message.login,'notice');return false;}
 const data=await api('GET',`/problems/${problemId}/experiment`);revision=data.revision;sessionId=data.session_id;
 screen.replaceChildren();fullLog=[];for(const item of data.logs||[]){line('waterhammer> '+item.command,'typed');if(item.text)line(item.text);}
 $('status').textContent=lang==='ko'?`저장된 측정 · RUN ${data.status?.run_count||0} · CAL ${data.status?.cal_count||0}`:`Saved measurements · RUN ${data.status?.run_count||0} · CAL ${data.status?.cal_count||0}`;
 return true;
}
let pending=null;
async function accept(command){
 const input=command.trim();if(!input||busy||embedded&&(!validProblemId()||!ownerToken||accountChanged))return;commandHistory.push(input);historyIndex=commandHistory.length;
 line($('prompt').textContent+input,'typed');
 if(input==='clear'){screen.replaceChildren();return;}
 if(!inside){if(input==='ls')line('waterhammer');else if(['./waterhammer','waterhammer','waterhammer.exe'].includes(input)){try{busy=true;if(embedded)commandState();if(await restore()){inside=true;setPrompt();embeddedNotice('');line('Water-hammer laboratory\nL = 120.0 m | sensors S0-S7 | 0.10 ms sampling\nhelp');}}catch(error){line(error.code==='login_required'?message.login:message.network,'error');if(embedded&&error.code==='login_required')embeddedNotice(message.login,true);else if(embedded&&error.code==='account_changed'){accountChanged=true;embeddedNotice(lang==='ko'?'로그인 정보가 바뀌었습니다. 문제 페이지를 새로고침하세요.':'Your sign-in changed. Reload the problem page.');}}finally{busy=false;if(embedded)commandState();}}else if(input==='help')line('ls\n./waterhammer\nclear');else line(input+': command not found','error');return;}
 if(['exit','quit'].includes(input)){inside=false;setPrompt();return;}
 if(pending&&pending.command!==input){line(message.retry,'notice');return;}
 pending ||= {command:input,revision,request_id:crypto.randomUUID()};
 busy=true;$('command').disabled=true;
 try{const data=await api('POST',`/problems/${problemId}/experiment`,pending);pending=null;revision=data.revision;sessionId=data.session_id;const r=data.result;
  if(r.clear)screen.replaceChildren();else line(r.text,r.ok?'':'error');if(r.trace)plot(r.trace);if(r.csv)download(r.csv,r.filename,'text/csv;charset=utf-8');
  $('status').textContent=lang==='ko'?'측정 기록이 계정에 저장됩니다.':'Measurements are saved to your account.';
 }catch(error){if(error.code==='experiment_changed'){pending=null;await restore();line(message.changed,'notice');}else if(error.code==='account_changed'){pending=null;line(lang==='ko'?'로그인 정보가 바뀌었습니다. 페이지를 새로고침한 뒤 장치를 다시 여세요.':'Your sign-in changed. Reload this page and reopen the apparatus.','error');}else if(error.code==='login_required'){pending=null;line(message.login,'error');}else if(error.code==='experiment_command_limit'){pending=null;line(lang==='ko'?'명령 기록 한도에 도달했습니다. 저장한 측정 자료로 답안을 작성하세요.':'The command-history limit has been reached. Use your saved measurements to complete the answer sheet.','error');}else if(error.code&&error.status<500&&![408,429].includes(error.status)&&!['TypeError','NetworkError'].includes(error.code)){pending=null;line(error.message||error.code,'error');}else line(message.network+' '+message.retry,'error');}
 finally{busy=false;commandState();$('command').focus();}
}
$('bar').onsubmit=e=>{e.preventDefault();const input=$('command').value;$('command').value='';void accept(input);};
$('command').onkeydown=e=>{if(e.key==='ArrowUp'||e.key==='ArrowDown'){e.preventDefault();historyIndex=Math.max(0,Math.min(commandHistory.length,historyIndex+(e.key==='ArrowUp'?-1:1)));$('command').value=commandHistory[historyIndex]||'';}if(e.ctrlKey&&e.key.toLowerCase()==='c'){e.preventDefault();if(!busy){inside=false;setPrompt();$('command').value='';line('^C');}}};
$('clear').onclick=()=>{screen.replaceChildren();$('command').focus();};$('saveLog').onclick=()=>download(fullLog.join('\n\n'),'waterhammer-log.txt');
$('downloadCsv').onclick=()=>{if(inside)void accept('export');else line(message.login,'notice');};$('downloadAllCsv').onclick=()=>{if(inside)void accept('export all');else line(message.login,'notice');};
line('HaslaLab Experimental Laboratory\n\n./waterhammer');
if(embedded){
 mode(true,false);
 if(!validProblemId())embeddedNotice(lang==='ko'?'실험 정보를 확인할 수 없습니다. 월별 문제에서 장치를 다시 여세요.':'The experiment could not be identified. Reopen the apparatus from the monthly problem.');
 else if(!ownerToken)embeddedNotice(message.login,true);
 else await accept('./waterhammer');
 commandState();
}else try{
 const [content,svg]=await Promise.all([fetch('./problem.json').then(r=>r.json()),fetch('../../weekly/figures/pressure-wave-apparatus.svg').then(r=>r.text())]);
 const d=content,statement=$('statement');statement.append(para(d.intro));
 const figure=document.createElement('figure'),drawing=document.createElement('div');drawing.id='apparatus';drawing.append(document.importNode(new DOMParser().parseFromString(svg,'image/svg+xml').documentElement,true));const caption=math(document.createElement('figcaption'),d.figure_caption);figure.append(drawing,caption);statement.append(figure);
 for(const p of d.model)statement.append(para(p));
 const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent='장치 조작';details.append(summary);
 const table=document.createElement('table');for(const[cmd,text]of d.commands){const tr=document.createElement('tr');const td=document.createElement('td');const code=document.createElement('code');code.textContent=cmd;td.append(code);tr.append(td,math(document.createElement('td'),text));table.append(tr);}details.append(table);statement.append(details);
 for(const section of d.sections){const h=document.createElement('h2');h.textContent=`Part ${section.id}. ${section.title} (${section.points}점)`;statement.append(h);for(const b of section.blocks)statement.append(b.equation?math(document.createElement('div'),'$$'+b.equation+'$$'):para(b.text));for(const id of section.partIds){const p=d.parts.find(p=>p.id===id),article=document.createElement('section');article.className='part';const h=document.createElement('h3');h.textContent=`${p.id}  ${p.title} (${p.points}점)`;article.append(h,para(p.prompt));statement.append(article);}}
 if(lang==='en'&&d.body_en){
  statement.replaceChildren();document.documentElement.lang='en';document.querySelector('h1').textContent=d.title_en;document.querySelector('header strong').textContent=d.title_en;
  document.title=d.title_en+' · HaslaLab';$('problemTab').textContent='Problem';$('sheet').textContent='Answer sheet';$('back').textContent='Monthly problems';$('login').textContent='Sign in';document.querySelector('header small').textContent='Experiment · 100 points';document.querySelector('main .meta').textContent='Experiment · Monthly problem 5';$('clear').textContent='Clear screen';$('saveLog').textContent='Save log';$('downloadCsv').textContent='Latest trace CSV';$('downloadAllCsv').textContent='All records CSV';caption.replaceChildren();math(caption,'Figure 1. The reservoir, pipe, valve and pressure sensors $S_0$-$S_7$. The coordinate $x$ increases from the valve $(x=0)$ towards the reservoir $(x=L)$. The bore and diameter variation are exaggerated.');
  for(const block of d.body_en.split(/(\$\$[\s\S]*?\$\$)/g)){
   if(block.startsWith('$$')){statement.append(math(document.createElement('div'),block));continue;}
   for(const paragraph of block.split(/\n\s*\n/)){
    const value=paragraph.trim();if(!value)continue;
    if(/^!\[.*\]\(weekly\/figures\/pressure-wave-apparatus\.svg\)$/.test(value)){statement.append(figure);continue;}
    const heading=/^(#{2,3})\s+([^\n]+)(?:\n([\s\S]*))?$/.exec(value);
    if(heading){statement.append(math(document.createElement('h'+heading[1].length),heading[2]));if(heading[3])statement.append(para(heading[3]));}else statement.append(para(value));
   }
  }
 }
 if(!Number.isSafeInteger(problemId)||problemId<1){const list=await api('GET','/monthly?month=2026-11&lang='+lang);const p=list.problems?.find(p=>p.no===5&&p.answerSheet?.key==='pressure-wave-experiment-v1');if(!p)throw Error('problem unavailable');problemId=p.id;}
 $('back').href='../../?lang='+lang+'#/monthly/p/'+problemId;$('sheet').href='../monthly-answer-sheet.html?id='+problemId+'&lang='+lang;
 if(!ownerToken){$('status').textContent=message.login;$('login').hidden=false;$('login').href='../../?lang='+lang+'#/login';}
 else {$('status').textContent=lang==='ko'?'측정 기록은 계정별로 저장됩니다.':'Measurements are saved to your account.';}
}catch(error){$('loadError').hidden=false;console.error(error);}
if(!embedded&&q.get('view')==='cmd')mode(true);
