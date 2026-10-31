import { loadOriginalPython, OpticalLab, vis } from './e1-python.mjs?v=0f2cbe003c87';
import { createOpticalScene } from './e1-scene.mjs?v=32f860513667';

const $ = id => document.getElementById(id);
const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const params = new URLSearchParams(location.search);
let lang = params.get('lang') === 'en' ? 'en' : 'ko';
const I18N = {
  ko: {
    title:'광학 측정',sub:'IPhO 2019 · 실험 1번',back:'← IPhO 2019',paper:'문제지',bench:'실험 부스',view3d:'3D 보기',top:'위에서',screen:'스크린 확대',
    equipment:'장비',equipmentSub:'눌러서 배치·회수',place:'배치',remove:'회수',items:{ruler:'자 · 슬라이더 · 레이저',disk:'투명 원판 · 각도기',holder:'회전 홀더 · 광학 소자',screen:'검은 스크린',tape6:'접착 테이프',tape:'줄자 3 m',ruler8:'투명 자 30 cm'},
    laser:'레이저',low:'3A 낮음 · 원판',high:'3B 높음 · 격자·프리즘',powerOn:'3C 레이저 켜기',powerOff:'3C 레이저 끄기',slider:'2 슬라이더',fine:'4C 방향 조절',leftFine:'↶ 왼쪽',rightFine:'오른쪽 ↷',
    optics:'12B 회전 홀더',grating:'12C 회절격자',prism:'12D 삼각 프리즘',rotateMount:'광학 소자 회전',parchment:'11 양피지를 원판에 대기',lamp:'9 탁상 램프',
    selection:'장비 조작',select:'선택 장비',none:'장비를 선택하세요',move:'이동',fineStep:'정밀 조작',rotate:'회전',rotateLeft:'↶ 왼쪽',rotateRight:'오른쪽 ↷',focus:'선택 장비 가까이 보기',
    tapePick:'6 테이프 집기',tapePut:'테이프 내려놓기',tapeHelp:'테이프를 집은 뒤 장비의 붙일 곳을 누르세요. 한 곳은 축이 되고, 두 곳을 붙이면 고정됩니다.',peel:'테이프 떼기',taped:'테이프가 붙어 있습니다. 이동하려면 먼저 떼세요.',
    help:'장비를 끌어 이동 · 장비 위 휠로 회전 (Shift: 미세 조절) · 빈 바닥을 끌어 시점 이동',measure:'자·각도기·줄자의 눈금을 직접 읽어 측정하세요.',lit:'실내등 켜짐',dark:'암실',untilDark:'소등까지',untilLight:'점등까지',time:'시간',
    reset:'새 실험',resetQ:'현재 장비 배치를 초기화하고 새 시료로 시작할까요?',ready:'장비를 선택해 실험을 시작하세요.',screenHelp:'줄자의 양 끝 노란 점을 끌어 무늬에 눈금을 맞추세요. 눈금 간격은 1 mm입니다.',screenNeed:'검은 스크린을 먼저 배치하세요.',close:'닫기',
    instructions:'사용 방법',steps:['장비 목록에서 필요한 장비를 배치합니다. 장비를 끌어 옮기고, 장비 위에서 휠을 돌려 회전합니다. Shift를 누르면 미세하게 회전합니다.','A부는 낮은 레이저와 원판, B·C부는 높은 레이저와 회전 홀더를 사용합니다. 홀더의 받침과 12B는 따로 회전합니다.','슬라이더를 끌어 움직입니다. 슬라이더 위의 휠은 4C 방향 조절, 레이저 머리 클릭은 3C 스위치입니다.','접착 테이프를 집은 뒤 장비를 눌러 붙입니다. 한 곳을 붙이면 그 점이 축이 되고, 두 곳을 붙이면 고정됩니다. 붙인 테이프를 누르면 뗄 수 있습니다.','검은 스크린을 누르면 정면에서 측정할 수 있습니다. 공기 중 광선은 보이지 않습니다. 실내등은 처음 3분 후 소등됩니다.'],
    reference:'장비 형태는 공식 문제지의 사진을 기준으로 제작했습니다.',official:'공식 문제지 · 장비 사진 2–3쪽',error:'3D 화면을 열지 못했습니다. WebGL 2를 지원하는 브라우저에서 하드웨어 가속을 켜고 다시 열어 주세요.',footer:'눈금으로 측정하는 가상 실험실',fixed:'고정된 장비는 테이프를 떼면 움직일 수 있습니다.',
  },
  en: {
    title:'Optical measurements',sub:'IPhO 2019 · Experiment 1',back:'← IPhO 2019',paper:'Problem paper',bench:'Experimental cubicle',view3d:'3D view',top:'Top view',screen:'Screen close-up',
    equipment:'Equipment',equipmentSub:'Place / put away',place:'Place',remove:'Put away',items:{ruler:'Ruler · slider · laser',disk:'Transparent disk · protractor',holder:'Rotating holder · optical element',screen:'Black screen',tape6:'Adhesive tape',tape:'Measuring tape, 3 m',ruler8:'Transparent ruler, 30 cm'},
    laser:'Laser',low:'3A Low · disk',high:'3B High · grating / prism',powerOn:'3C Switch laser on',powerOff:'3C Switch laser off',slider:'2 Slider',fine:'4C Direction bar',leftFine:'↶ Turn left',rightFine:'Turn right ↷',
    optics:'12B Rotating holder',grating:'12C Diffraction grating',prism:'12D Triangular prism',rotateMount:'Rotate optical element',parchment:'11 Hold parchment at the disk',lamp:'9 Table lamp',
    selection:'Apparatus controls',select:'Selected apparatus',none:'Select an apparatus',move:'Move',fineStep:'Fine adjustment',rotate:'Rotate',rotateLeft:'↶ Turn left',rotateRight:'Turn right ↷',focus:'Look closely at selected apparatus',
    tapePick:'6 Pick up adhesive tape',tapePut:'Put the tape down',tapeHelp:'Pick up the tape, then click where it should stick. One strip pins a point; two strips fix the apparatus.',peel:'Peel strip',taped:'Peel the tape before moving this apparatus.',
    help:'Drag equipment to move · wheel over apparatus to rotate (Shift: fine) · drag the mat to orbit',measure:'Read the printed ruler, protractor and tape graduations yourself.',lit:'Room lights on',dark:'Dark room',untilDark:'Lights off in',untilLight:'Lights on in',time:'Clock',
    reset:'New experiment',resetQ:'Reset this arrangement and start with a new specimen?',ready:'Select equipment to begin.',screenHelp:'Drag the yellow tape ends to align the graduations with the pattern. Small divisions are 1 mm.',screenNeed:'Place the black screen first.',close:'Close',
    instructions:'Instructions',steps:['Place apparatus from the equipment list. Drag it to move; turn the wheel over it to rotate. Hold Shift for fine rotation.','Use the low laser and disk for part A, and the high laser and rotating holder for parts B and C. The base and cylinder 12B rotate separately.','Drag the slider. The wheel over it turns direction bar 4C; clicking the laser head operates switch 3C.','Pick up the adhesive tape and click an apparatus to attach a strip. One strip pins a point; two fix it. Click a strip to peel it off.','Click the black screen for the front measurement view. The laser is invisible in air. The room darkens after the first 3 minutes.'],
    reference:'Apparatus is modelled after photographs in the official problem paper.',official:'Official paper · equipment photographs on pages 2–3',error:'The 3D view could not start. Enable hardware acceleration and reopen this page in a browser that supports WebGL 2.',footer:'A virtual laboratory measured with printed scales',fixed:'Peel the adhesive tape before moving fixed equipment.',
  },
};
const numbers = {ruler:'01–04',disk:'10',holder:'12',screen:'05',tape6:'06',tape:'07',ruler8:'08'};
const KEYS = Object.keys(numbers);
let lab, scene, selected = null, view = 'perspective', speed = 1, last = 0, frame = 0, previousUpdate = 0, uiTime = 0;
let seed = crypto.getRandomValues(new Uint32Array(1))[0], frontDrag = null, hiddenAt = document.hidden ? performance.now() : null;
const S = () => I18N[lang];
const isOn = key => key === 'tape' ? lab.tape_on : !!lab.obj[key]?.on;
function initLab() {
  lab?.dispose?.();
  lab = new OpticalLab(seed);
}
try {
  await loadOriginalPython();
  initLab();
} catch(error) {
  $('app').innerHTML = `<p class="loading" role="alert">${lang==='ko'?'실험실을 불러오지 못했습니다. 페이지를 새로고침해 주세요.':'The laboratory could not load. Please reload this page.'}</p>`;
  console.error('IPhO 2019 original Python',error);
  throw error;
}
function note(message) { const n=$('notice');if(n)n.textContent=message; }
function draw() {
  if(!scene)return;
  const trace=lab.trace();scene.update(lab,trace);
  if($('front')?.open)drawFront(trace);
}
function changed() { lab.clearPoseCache();sync();draw(); }
function select(key) {
  selected=key==='laser'?'ruler':key==='holder12b'?'holder':key;
  lab.sel=key;if(lab.obj[selected]?.on)lab.raise_(selected);lab.clearPoseCache();scene?.selected(key);sync();draw();
}
function move(key,position,removeOutside=true) { if(!lab.move(key,position,{removeOutside}))note(S().taped);else note(S().measure);changed(); }
function rotate(key,delta) { if(!lab.rotate(key,delta))note(S().fixed);changed(); }
function mount(key) {
  lab.toggle(key,scene?.placementPoint?.());
  selected=key;lab.sel=key;scene?.selected(key);changed();
}
function build() {
  const t=S();document.documentElement.lang=lang;document.title=`IPhO 2019 E1 · ${t.title} · HaslaLab`;
  $('app').innerHTML=`
    <header class="lab-header"><div><h1>IPhO 2019 E1 — ${t.title}</h1><p><a href="../#/ipho/2019">${t.back}</a> · <a href="../pdf/IPhO_2019_E1_${lang==='ko'?'KO':'EN'}.pdf" target="_blank" rel="noopener">${t.paper} ↗</a></p></div><div class="lang" aria-label="Language"><button type="button" data-lang="ko" class="${lang==='ko'?'on':''}">한국어</button><button type="button" data-lang="en" class="${lang==='en'?'on':''}">English</button></div></header>
    <main class="wrap">
      <aside class="tray"><h3>${t.equipment}</h3><div class="equipment">${KEYS.map(key=>`<button type="button" data-equipment="${key}" aria-pressed="false"><span class="no">${numbers[key]}</span><span class="label">${t.items[key]}</span><span class="badge"></span></button>`).join('')}</div><p class="hint">${t.equipmentSub}</p><button type="button" id="tapePick" class="full"></button><p class="hint">${t.tapeHelp}</p></aside>
      <div class="stage"><section class="card"><div class="tabs"><button type="button" data-view="perspective">${t.bench} · 3D</button><button type="button" data-view="top">${t.top}</button><button type="button" id="openScreen">${t.screen}</button></div><h3>${t.measure}</h3><div id="scene" class="scene" aria-label="${t.bench}"></div><p class="hint scene-help">${t.help}</p></section><div id="notice" class="status" role="status">${t.ready}</div><details class="info"><summary>${t.instructions}</summary><ol>${t.steps.map(step=>`<li>${step}</li>`).join('')}</ol></details></div>
      <aside class="panel"><h2>${t.laser}</h2><label class="control-label" for="level">${lang==='ko'?'레이저 높이':'Laser level'}</label><select id="level" class="full"><option value="low">${t.low}</option><option value="high">${t.high}</option></select><button type="button" id="power" class="power"></button><label class="check"><input id="parchment" type="checkbox">${t.parchment}</label>
      <h2>${t.time}</h2><div class="row"><select id="speed" aria-label="${t.time}"><option value="1">1×</option><option value="10">10×</option></select><span id="clock"></span></div><p class="hint" id="lightState"></p>
      <h2>${t.optics}</h2><select id="optic" class="full" aria-label="${t.optics}"><option value="grating">${t.grating}</option><option value="prism">${t.prism}</option></select><div class="control-label">${t.rotateMount}</div><div class="row"><button type="button" data-holder="2">↶</button><button type="button" data-holder="-2">↷</button></div>
      <details class="control-details"><summary>${t.selection}</summary><label class="control-label" for="selection">${t.select}</label><select id="selection" class="full"><option value="">${t.none}</option>${KEYS.map(k=>`<option value="${k}">${numbers[k]} ${t.items[k]}</option>`).join('')}</select><button type="button" class="full" id="focus">${t.focus}</button><div id="objectControls"><div class="control-label"><span>${t.move}</span><label><input id="fineMove" type="checkbox"> ${t.fineStep}</label></div><div class="move-pad"><span></span><button type="button" data-move="0,-1" aria-label="${lang==='ko'?'뒤로 이동':'Move back'}">↑</button><span></span><button type="button" data-move="-1,0" aria-label="${lang==='ko'?'왼쪽 이동':'Move left'}">←</button><span class="centre">${t.move}</span><button type="button" data-move="1,0" aria-label="${lang==='ko'?'오른쪽 이동':'Move right'}">→</button><span></span><button type="button" data-move="0,1" aria-label="${lang==='ko'?'앞으로 이동':'Move forward'}">↓</button><span></span></div><div class="control-label">${t.rotate}</div><div class="row"><button type="button" data-rotate="2">${t.rotateLeft}</button><button type="button" data-rotate="-2">${t.rotateRight}</button></div><div id="tapes" class="tapes"></div></div><label class="control-label" for="slider">${t.slider}</label><input id="slider" type="range" min="-27" max="27" step="0.01"><div class="control-label">${t.fine}</div><div class="row"><button type="button" data-fine="0.25">${t.leftFine}</button><button type="button" data-fine="-0.25">${t.rightFine}</button></div></details>
      <button type="button" id="reset" class="full">${t.reset} ↻</button></aside>
    </main>
    <dialog id="front"><header><h2>${t.screen}</h2><button type="button" id="closeFront">${t.close} ✕</button></header><canvas id="frontCanvas" width="1440" height="450" aria-label="${t.screen}"></canvas><p class="hint">${t.screenHelp}</p></dialog>
    <dialog id="resetPrompt"><header><h2>${t.reset}</h2></header><p>${t.resetQ}</p><div class="row"><button type="button" id="cancelReset">${t.close}</button><button type="button" class="on" id="confirmReset">${t.reset}</button></div></dialog>`;
  for(const b of document.querySelectorAll('[data-lang]'))b.onclick=()=>changeLanguage(b.dataset.lang);
  for(const b of document.querySelectorAll('[data-equipment]'))b.onclick=()=>mount(b.dataset.equipment);
  for(const b of document.querySelectorAll('[data-view]'))b.onclick=()=>{view=b.dataset.view;scene?.setView(view);sync();};
  $('selection').onchange=()=>select($('selection').value||null);
  $('focus').onclick=()=>scene?.focus?.(selected);
  for(const b of document.querySelectorAll('[data-move]'))b.onclick=()=>{if(!selected||!lab.obj[selected])return;const step=$('fineMove').checked?.1:1;const d=b.dataset.move.split(',').map(Number);move(selected,lab.obj[selected].pos.map((v,i)=>v+d[i]*step));};
  for(const b of document.querySelectorAll('[data-rotate]'))b.onclick=()=>rotate(selected,Number(b.dataset.rotate)*($('fineMove').checked?.125:1));
  for(const b of document.querySelectorAll('[data-fine]'))b.onclick=()=>rotate('laser',Number(b.dataset.fine)*($('fineMove').checked?1:8));
  for(const b of document.querySelectorAll('[data-holder]'))b.onclick=()=>rotate('holder12b',Number(b.dataset.holder)*($('fineMove').checked?.125:1));
  $('level').onchange=()=>{lab.level=$('level').value;changed();};
  $('optic').onchange=()=>{lab.hold_item=$('optic').value;changed();};
  $('slider').oninput=()=>{lab.setSlider(Number($('slider').value));changed();};
  $('power').onclick=()=>{lab.laser_on=!lab.laser_on;changed();};
  for(const key of ['parchment'])$(key).onchange=()=>{lab[key]=$(key).checked;changed();};
  $('speed').onchange=()=>{speed=Number($('speed').value);};
  $('tapePick').onclick=()=>{lab.tape_held=!lab.tape_held;changed();};
  $('reset').onclick=()=>$('resetPrompt').showModal();
  $('cancelReset').onclick=()=>$('resetPrompt').close();
  $('confirmReset').onclick=()=>{$('resetPrompt').close();seed=crypto.getRandomValues(new Uint32Array(1))[0];initLab();selected=null;view='perspective';last=0;previousUpdate=0;note(t.ready);sync();startScene();};
  $('openScreen').onclick=openScreen;
  $('closeFront').onclick=()=>$('front').close();
  bindFront();sync();
}
function openScreen(){if(!lab.obj.screen.on){note(S().screenNeed);return;}$('front').showModal();drawFront(lab.trace());}
function sync() {
  if(!$('power'))return;const t=S();
  for(const b of document.querySelectorAll('[data-equipment]')){const on=isOn(b.dataset.equipment);b.classList.toggle('placed',on);b.setAttribute('aria-pressed',String(on));b.querySelector('.badge').textContent=on?t.remove:t.place;}
  for(const b of document.querySelectorAll('[data-view]')){const on=b.dataset.view===view;b.classList.toggle('on',on);b.setAttribute('aria-pressed',String(on));}
  $('selection').value=selected||'';$('focus').disabled=!selected||!isOn(selected);
  $('objectControls').hidden=!selected||!lab.obj[selected]||!isOn(selected)||selected==='tape6';
  const taped=!!lab.obj[selected]?.tapes.length;
  for(const b of document.querySelectorAll('[data-move]'))b.disabled=taped;
  for(const b of document.querySelectorAll('[data-rotate]'))b.disabled=(lab.obj[selected]?.tapes.length||0)>=2;
  $('tapes').innerHTML=(lab.obj[selected]?.tapes||[]).map((_,i)=>`<button type="button" data-peel="${i}">${t.peel} ${i+1} ✕</button>`).join('');
  for(const b of $('tapes').querySelectorAll('[data-peel]'))b.onclick=()=>{lab.peelTape(selected,Number(b.dataset.peel));changed();};
  $('level').value=lab.level;$('optic').value=lab.hold_item;$('slider').value=lab.slider;
  $('power').classList.toggle('on',lab.laser_on);$('power').textContent=lab.laser_on?t.powerOff:t.powerOn;$('power').disabled=!lab.obj.ruler.on;
  $('slider').disabled=!lab.obj.ruler.on;
  for(const b of document.querySelectorAll('[data-fine]'))b.disabled=!lab.obj.ruler.on;
  for(const b of document.querySelectorAll('[data-holder]'))b.disabled=!lab.obj.holder.on;
  $('parchment').checked=lab.parchment;
  $('tapePick').textContent=lab.tape_held?t.tapePut:t.tapePick;$('tapePick').disabled=!lab.obj.tape6.on;$('tapePick').classList.toggle('on',lab.tape_held);
  $('speed').value=String(speed);$('openScreen').disabled=!lab.obj.screen.on;
  updateClock();
}
const mmss = seconds => {const n=Math.max(0,Math.floor(seconds));return `${Math.floor(n/60)}:${String(n%60).padStart(2,'0')}`;};
function updateClock(){const t=S(),[dark,left]=lab.light_phase();$('clock').textContent=mmss(lab.clock);$('lightState').textContent=`${dark?t.dark:t.lit} · ${dark?t.untilLight:t.untilDark} ${mmss(left)}`;$('lightState').classList.toggle('dark',dark);}
async function startScene() {
  scene?.dispose();
  try {
    scene=createOpticalScene($('scene'),{
      onSelect:select,visibility:vis,language:lang,onOpenScreen:openScreen,
      onTapeHover:point=>{lab.obj.tape6.pos=point;lab.clearPoseCache();draw();},
      onTapeHeld:held=>{lab.tape_held=held;changed();},
      onMove:(key,point)=>move(key,point,false),onRotate:rotate,onSlider:value=>{lab.setSlider(value);changed();},
      onRelease:key=>{if(key==='tape_a'||key==='tape_b')lab.moveTapeEndpoint(key,lab[key]);else if(lab.obj[key])lab.move(key,lab.obj[key].pos);changed();},
      onSwitch:on=>{lab.laser_on=typeof on==='boolean'?on:!lab.laser_on;changed();},
      onHolderRotate:delta=>rotate('holder12b',delta),onFineRotate:delta=>rotate('laser',delta),
      onTapeMove:(end,point)=>{lab.moveTapeEndpoint(end==='a'?'tape_a':'tape_b',point,{removeOutside:false});changed();},
      onTapeStick:(_key,point)=>{const stuck=lab.stickTape(point[0],point[1]);changed();return stuck;},
      onTapePeel:(key,index)=>{lab.peelTape(key,index);changed();},
      onFrontTapeMove:(end,point)=>{lab.moveTapeEndpoint(end==='a'?'ftape_a':'ftape_b',point);changed();},
    });
    scene.setView(view);scene.selected(selected);draw();$('scene').dataset.ready='true';
  }catch(error){scene=null;$('scene').innerHTML=`<div class="scene-error" role="alert">${escape(S().error)}</div>`;console.error('IPhO 2019 E1 3D',error);}
}
function changeLanguage(next) {
  if(next===lang)return;lang=next;const url=new URL(location.href);url.searchParams.set('lang',lang);history.replaceState(null,'',url);build();startScene();
}
function animate(timestamp) {
  if(document.hidden){last=0;frame=0;return;}
  if(!last)last=timestamp;
  if(timestamp-previousUpdate>=250){const dt=Math.max(0,(timestamp-last)/1000);lab.advance(dt,speed);last=timestamp;draw();previousUpdate=timestamp;}
  if(timestamp-uiTime>500){updateClock();uiTime=timestamp;}
  frame=requestAnimationFrame(animate);
}
function drawFront(trace) {
  const canvas=$('frontCanvas'),ctx=canvas.getContext('2d'),w=canvas.width,h=canvas.height,sx=w/132,sy=sx;
  const px=([x,y])=>[w/2+x*sx,h/2+y*sy];
  ctx.fillStyle='#101113';ctx.fillRect(0,0,w,h);ctx.strokeStyle='#454148';ctx.strokeRect(6*sx, h/2-13*sy,120*sx,26*sy);
  for(const [s,I]of trace.shots||[]){const v=vis(I,lab.dark);if(v<=.02)continue;const[x,y]=px([s,0]),g=ctx.createRadialGradient(x,y,0,x,y,14+12*v);g.addColorStop(0,`rgba(255,185,150,${v})`);g.addColorStop(.15,`rgba(255,50,25,${v})`);g.addColorStop(1,'rgba(255,30,15,0)');ctx.fillStyle=g;ctx.beginPath();ctx.arc(x,y,14+12*v,0,2*Math.PI);ctx.fill();}
  const a=lab.ftape_a,b=lab.ftape_b,dx=b[0]-a[0],dy=b[1]-a[1],length=Math.hypot(dx,dy);if(length>.01){const ux=dx/length,uy=dy/length,nx=-uy,ny=ux,points=[[a[0]+nx*1.4,a[1]+ny*1.4],[b[0]+nx*1.4,b[1]+ny*1.4],[b[0]-nx*1.4,b[1]-ny*1.4],[a[0]-nx*1.4,a[1]-ny*1.4]];ctx.beginPath();points.map(px).forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.closePath();ctx.fillStyle='#e7dfc6';ctx.fill();ctx.strokeStyle='#202023';ctx.fillStyle='#202023';for(let i=0;i<=Math.min(3000,Math.floor(length*10));i++){const x=a[0]+ux*i*.1,y=a[1]+uy*i*.1,l=i%100===0?1.25:i%50===0?.9:.5,p=px([x-nx*1.4,y-ny*1.4]),q=px([x-nx*(1.4-l),y-ny*(1.4-l)]);ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(...p);ctx.lineTo(...q);ctx.stroke();if(i%100===0){const at=px([x+nx*.3,y+ny*.3]);ctx.save();ctx.translate(...at);ctx.rotate(Math.atan2(uy,ux));ctx.font='13px ui-monospace,monospace';ctx.textAlign='center';ctx.fillText(String(i/10),0,4);ctx.restore();}}}
  for(const p of[a,b]){const[x,y]=px(p);ctx.beginPath();ctx.arc(x,y,8,0,Math.PI*2);ctx.fillStyle='#f1ce5f';ctx.fill();ctx.strokeStyle='#8e7227';ctx.stroke();}
}
function bindFront(){const c=$('frontCanvas');const toCm=e=>{const r=c.getBoundingClientRect();return[((e.clientX-r.left)/r.width-.5)*132,((e.clientY-r.top)/r.width-c.height/c.width*.5)*132];};c.onpointerdown=e=>{const p=toCm(e),a=lab.ftape_a,b=lab.ftape_b,da=Math.hypot(p[0]-a[0],p[1]-a[1]),db=Math.hypot(p[0]-b[0],p[1]-b[1]);if(Math.min(da,db)<4){frontDrag=da<db?'ftape_a':'ftape_b';c.setPointerCapture(e.pointerId);}};c.onpointermove=e=>{if(!frontDrag)return;const p=toCm(e);lab.moveTapeEndpoint(frontDrag,[Math.max(-65,Math.min(65,p[0])),Math.max(-18,Math.min(18,p[1]))]);drawFront(lab.trace());};c.onpointerup=c.onpointercancel=()=>{frontDrag=null;};}
build();await startScene();frame=requestAnimationFrame(animate);
document.addEventListener('visibilitychange',()=>{
  if(document.hidden){hiddenAt=performance.now();cancelAnimationFrame(frame);frame=0;last=0;}
  else {if(hiddenAt!==null){lab.advance(Math.max(0,(performance.now()-hiddenAt)/1000),speed);hiddenAt=null;sync();draw();}if(!frame)frame=requestAnimationFrame(animate);}
});
window.addEventListener('pagehide',()=>{cancelAnimationFrame(frame);scene?.dispose();});
