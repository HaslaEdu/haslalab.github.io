/* Practice by unit: short exam problems on the learning path, one at a time, graded at once.
   Like a language-learning app: a session of ten, the step rises after two right answers in a row and
   falls after a wrong one, and a daily streak. Progress stays in this browser (localStorage). */
(()=>{
  'use strict';
  const P=window.HL_LEARN_PATH,$=id=>document.getElementById(id);
  const params=new URL(location.href).searchParams;
  const embedded=params.get('embed')==='1'&&window.parent!==window;
  const SESSION=10;
  const copy={
    ko:{ob_region:'어디에서 공부하나요?',ob_level:'지금 어느 단계인가요?',ob_goal:'무엇을 위해 공부하나요?',ob_oly:'올림피아드는 어디까지 해 봤나요?',ob_daily:'하루 목표를 정하세요',
      obKr:'AP Physics와 한국 시험 계산 문제, 올림피아드',obIn:'JEE Main · Advanced',obUs:'AP Physics, F=ma · USAPhO',obGlobal:'AP Physics와 국제 올림피아드 준비',
      goSchool:'학교 공부 · 내신',goExam:'입시 시험',goOly:'물리 올림피아드',goCurious:'그냥 물리가 좋아서',oly0:'처음 준비합니다',oly1:'1차(예선) 시험을 쳐 봤습니다',oly2:'본선 이상 진출했습니다',
      perDay:'문제',daily5:'가볍게 · 약 5분',daily10:'꾸준히 · 약 10분',daily20:'열심히 · 약 20분',back:'이전',obDone:'시작 단계',obNext:'모든 단원이 이 단계에서 시작하고, 첫 문제는 위 시험에서 나옵니다. 12문제 수준 찾기로 더 정확하게 맞출 수 있습니다.',
      editProfile:'학습 설정',myExams:'내 시험',otherExams:'다른 시험 보기',dailyGoal:'오늘 목표',
      tabClass:'학급',classIntro:'선생님이 알려 준 6자리 코드로 학급에 들어가면 과제가 여기에 나옵니다. 선생님은 학급을 만들어 AP · JEE 문제를 과제로 내고, 학생별 단원 실력과 과제 진행을 볼 수 있습니다.',myAssignments:'내 과제',noAssignments:'아직 과제가 없습니다.',classCode:'학급 코드',join:'참여',leave:'나가기',leaveConfirm:'이 학급에서 나갈까요?',teach:'가르치기',students:'명',className:'학급 이름',newClass:'학급 만들기',classFree:'무료: 학급 1개, 학생 30명까지. 학생은 이 학급의 학습 기록만 공유합니다.',due:'마감',shareCode:'학생에게 학급 코드를 알려 주세요. 학생이 단원별 문제의 "학급" 탭에서 코드를 입력하면 참여합니다.',student:'학생',answered:'푼 문제',lastActive:'최근 학습',remove:'내보내기',removeConfirm:'이 학생을 학급에서 내보낼까요?',noStudents:'아직 학생이 없습니다.',newAssignment:'과제 내기',allOf:'전체',assign:'과제 내기',closeClass:'학급 닫기',closeConfirm:'학급을 닫을까요? 학생들은 더 이상 과제를 볼 수 없습니다.',
      cl_bad_name:'학급 이름을 입력하세요.',cl_class_limit:'무료로는 학급을 1개까지 만들 수 있습니다.',cl_bad_code:'코드는 6자리입니다.',cl_class_not_found:'그 코드의 학급이 없습니다.',cl_own_class:'내가 만든 학급입니다.',cl_class_full:'학급 정원이 찼습니다.',cl_bad_items:'문제를 고르세요.',cl_bad_due:'마감일을 확인하세요.',cl_rate_limited:'잠시 뒤에 다시 시도하세요.',
      tabTracks:'시험별',trackPick:'시험과 단원을 고르면 그 시험 형식의 문제 10개를 풉니다. 하슬라랩이 직접 만든 문제입니다.',mixed:'전체 섞어서',numPh:'답 (숫자)',check:'확인',notNumber:'숫자로 입력하세요 (예: 3.2, 1.5e3, 2×10^4)',hint:'힌트',tutor:'AI 튜터',discuss:'이 문제 토론',seeDiscuss:'이 문제의 질문 보기',newDiscuss:'질문 올리기',byHasla:'하슬라랩 창작 문제',
      tutorLogin:'AI 튜터는 로그인하면 하루 5번까지 무료로 쓸 수 있습니다.',login:'로그인',tutorPh:'어디서 막혔는지 적어 보세요',tutorSend:'묻기',thinking:'생각하는 중…',tutorLimit:'오늘 무료 질문을 모두 썼습니다. 내일 다시 쓸 수 있습니다.',tutorFail:'지금은 답할 수 없습니다. 잠시 뒤에 다시 시도하세요.',tutorLeft:'오늘 남은 질문',aiNote:'AI가 만든 답변이라 틀릴 수 있습니다.',
      aiTranslated:'AI 번역',showOriginal:'원문 보기',showTranslation:'번역 보기',translating:'번역하는 중…',withHints:'힌트 사용',
      diagTitle:'내 수준 찾기',diagBody:'분야별로 두 문제씩, 12문제(약 10분)를 풀면 단원별 시작 단계를 정해 드립니다. 건너뛰고 바로 풀어도 됩니다.',diagStart:'수준 찾기 시작',diagDone:'분야별 시작 단계를 정했습니다. 이제 오늘의 추천이 이 단계에 맞춰집니다.',
      lvBeginner:'입문',lvFamiliar:'익숙',lvProficient:'능숙',lvMaster:'마스터',tier:'XP 등급',
      noteTracks:'AP · JEE 문제는 하슬라랩이 각 시험 형식에 맞춰 직접 만든 창작 문제입니다. AP와 Advanced Placement는 College Board의 상표이며, College Board · NTA와 관계가 없습니다. 기록은 이 기기에 저장되고, 로그인하면 계정에도 저장됩니다.',
      title:'단원별 문제',streak:'일 연속',xp:'XP',solved:'문제 해결',pick:'단원을 고르면 내 단계에 맞는 문제 10개를 풉니다.',
      none:'아직 문제가 없습니다',step:'단계',start:'시작',again:'한 번 더',units:'단원 목록',next:'다음 문제',finish:'결과 보기',
      right:'정답입니다!',wrong:'오답입니다. 정답은',up:'단계가 올랐습니다',down:'한 단계 쉬운 문제로 갑니다',
      result:'맞힌 문제',of:'/',done:'세션 완료',loading:'문제를 불러오는 중…',failed:'문제를 불러오지 못했습니다.',retry:'다시 시도',
      pdf:'원본 시험지',quit:'← 단원 목록',time:'권장 시간',sec:'초',progress:'해결',skip:'건너뛰기',skipped:'건너뜀',
      tabUnits:'단원별',calcName:'계산 문제 (한국 시험 기출)',noteUnits:'단원마다 하슬라랩 창작 문제(AP · JEE · F=ma · USAPhO 형식)와 한국 시험 기출 계산 문제(출처: 한국교육과정평가원, 서울특별시교육청, 경기도교육청, 인천광역시교육청 · 웹·앱 배포 허가 범위 안에서 제공)를 함께 풉니다. 기록은 이 기기에 저장되고, 로그인하면 계정에도 저장됩니다.',synced:'계정에 저장됨',tabToday:'오늘의 추천',todayTitle:'오늘의 10문제',whyReview:'복습',whyWeak:'약한 단원',whyStretch:'도전',whyNew:'새 단원',focus:'집중 단원',startToday:'시작하기',mySkills:'단원별 실력',unit:'단원',accuracy:'정답률',noSkills:'문제를 풀수록 단원별 실력이 쌓이고 추천이 정확해집니다.',syncFailed:'저장 실패 · 다시 시도합니다',loginToSave:'로그인하면 기록이 계정에 저장됩니다 →',tabBank:'교재 · 대학 문제',tabContest:'대회 도전',
      bankPick:'분야와 난이도를 고르면 교재와 대학 강의 문제를 하나씩 풉니다. 풀이를 확인하고 스스로 채점하세요.',stars:'난이도',showSol:'풀이 보기',noSol:'아직 등록된 풀이가 없습니다. 커뮤니티 질문 · 답변 갤러리나 AI에게 물어보세요.',
      solvedIt:'풀었어요',missedIt:'못 풀었어요',original:'원문 보기',translated:'번역 보기',noKo:'한국어 번역이 아직 없어 원문을 보여 줍니다.',draft:'하슬라랩 작성 풀이 · 검수 전',refFig:'참고 그림',empty:'이 조건의 문제가 더 없습니다. 난이도나 분야를 바꿔 보세요.',
      contestPick:'대회를 고르면 기출 문제가 하나씩 나옵니다. PDF로 풀고, 풀이를 확인한 뒤 스스로 채점하세요.',paper:'문제',solution:'풀이',noContestSol:'이 문제는 공식 풀이가 없습니다.',problems:'문제',another:'다른 문제',figInPdf:'그림은 아래 원본 PDF에서 볼 수 있습니다.',transcribed:'문제 글은 원본 PDF에서 옮겨 적은 것입니다. 원본과 다르면 PDF를 기준으로 하세요.',noteBank:'문항 출처는 문제마다 표시합니다(교재 · 대학 강의). 한국어 번역과 "하슬라랩 작성" 풀이는 검수 중입니다. 기록은 이 기기에 저장되고, 로그인하면 계정에도 저장되어 다른 기기에서 이어집니다.',noteContest:'각 대회의 공식 문제와 풀이이며, 한국어판은 하슬라랩 번역입니다. 기록은 이 기기에 저장되고, 로그인하면 계정에도 저장되어 다른 기기에서 이어집니다.',
      note:'문항 출처: 한국교육과정평가원, 서울특별시교육청, 경기도교육청, 인천광역시교육청 (웹·앱 배포 허가 범위 안에서 제공). 단원 분류 일부는 자동 분류이며 검수 중입니다. 기록은 이 기기에 저장되고, 로그인하면 계정에도 저장되어 다른 기기에서 이어집니다.'},
    en:{ob_region:'Where do you study?',ob_level:'Where are you now?',ob_goal:'What are you studying for?',ob_oly:'How far have you got in olympiads?',ob_daily:'Pick a daily goal',
      obKr:'CSAT and school exams, Korean Physics Olympiad',obIn:'JEE Main and Advanced',obUs:'AP Physics, F=ma and the USAPhO',obGlobal:'AP Physics and international olympiad prep',
      goSchool:'School physics',goExam:'An entrance or AP exam',goOly:'Physics olympiad',goCurious:'Just curious',oly0:'Starting out',oly1:'I have sat a first round',oly2:'I have reached a national final or beyond',
      perDay:'problems',daily5:'Casual · about 5 min',daily10:'Steady · about 10 min',daily20:'Serious · about 20 min',back:'Back',obDone:'Your starting step',obNext:'Every unit starts at this step and your first problems come from the exams above. A 12-problem level check can tune it further.',
      editProfile:'Settings',myExams:'Your exams',otherExams:'Other exams',dailyGoal:'today',
      tabClass:'Class',classIntro:'Join your teacher’s class with its six-letter code and your assignments appear here. Teachers can make a class, set AP and JEE problems as assignments, and see each student’s units and progress.',myAssignments:'My assignments',noAssignments:'No assignments yet.',classCode:'Class code',join:'Join',leave:'Leave',leaveConfirm:'Leave this class?',teach:'Teach',students:'students',className:'Class name',newClass:'Make a class',classFree:'Free: one class of up to 30 students. Students share only their Learn practice with the class.',due:'due',shareCode:'Give your students the class code. They enter it in the Class tab of Practice to join.',student:'Student',answered:'Answered',lastActive:'Last active',remove:'Remove',removeConfirm:'Remove this student from the class?',noStudents:'No students yet.',newAssignment:'Set an assignment',allOf:'All',assign:'Assign',closeClass:'Close class',closeConfirm:'Close this class? Students will no longer see its assignments.',
      cl_bad_name:'Enter a class name.',cl_class_limit:'A free account can have one class.',cl_bad_code:'A code has six letters.',cl_class_not_found:'No class has that code.',cl_own_class:'That is your own class.',cl_class_full:'This class is full.',cl_bad_items:'Pick problems.',cl_bad_due:'Check the due date.',cl_rate_limited:'Try again in a moment.',
      tabTracks:'By exam',trackPick:'Pick an exam and a unit to solve ten problems in that exam’s style. Every problem is written by HaslaLab.',mixed:'All units mixed',numPh:'Answer (number)',check:'Check',notNumber:'Enter a number (e.g. 3.2, 1.5e3, 2×10^4)',hint:'Hint',tutor:'AI tutor',discuss:'Discuss',seeDiscuss:'Questions about this problem',newDiscuss:'Ask about it',byHasla:'Original problem by HaslaLab',
      tutorLogin:'Log in to use the AI tutor: five free questions a day.',login:'Log in',tutorPh:'Where are you stuck?',tutorSend:'Ask',thinking:'Thinking…',tutorLimit:'Today’s free questions are used up. More tomorrow.',tutorFail:'The tutor cannot answer right now. Try again in a moment.',tutorLeft:'Questions left today',aiNote:'AI answers can be wrong.',
      aiTranslated:'AI translation',showOriginal:'Show original',showTranslation:'Show translation',translating:'Translating…',withHints:'with hints',
      diagTitle:'Find your level',diagBody:'Two problems per area, twelve in all (about 10 minutes), set your starting step in every unit. You can also skip this and start right away.',diagStart:'Find my level',diagDone:'Your starting steps are set. Today’s picks now follow them.',
      lvBeginner:'Beginner',lvFamiliar:'Familiar',lvProficient:'Proficient',lvMaster:'Master',tier:'XP tier',
      noteTracks:'AP and JEE problems are original problems written by HaslaLab in each exam’s style. AP and Advanced Placement are trademarks of College Board; HaslaLab is not affiliated with College Board or the NTA. Progress is kept on this device and, when you log in, on your account too.',
      title:'Practice by unit',streak:'day streak',xp:'XP',solved:'solved',pick:'Pick a unit to solve ten problems at your step.',
      none:'No problems yet',step:'Step',start:'Start',again:'Again',units:'Units',next:'Next',finish:'See results',
      right:'Correct!',wrong:'Not quite. The answer is',up:'Step up',down:'Back one step',
      result:'Correct',of:'/',done:'Session complete',loading:'Loading problems…',failed:'Could not load the problems.',retry:'Retry',
      pdf:'Original paper',quit:'← Units',time:'Suggested time',sec:'s',progress:'solved',skip:'Skip',skipped:'skipped',
      tabUnits:'By unit',calcName:'Calculation problems from Korean exams',noteUnits:'Each unit mixes HaslaLab’s original problems (in the style of AP, JEE, F=ma and the USAPhO) with calculation problems from Korean school exams (Korea Institute for Curriculum and Evaluation and the Seoul, Gyeonggi and Incheon education offices, shared within the permitted web and app use; shown in English as an AI translation). Progress is kept on this device and, when you log in, on your account too.',synced:'Saved to your account',tabToday:'Today',todayTitle:'Today’s ten',whyReview:'review',whyWeak:'weak unit',whyStretch:'stretch',whyNew:'new unit',focus:'focus',startToday:'Start',mySkills:'Your units',unit:'Unit',accuracy:'Correct',noSkills:'Your unit ratings grow as you solve problems, and the picks get sharper.',syncFailed:'Not saved · retrying',loginToSave:'Log in to keep your progress on your account →',tabBank:'Books & university',tabContest:'Competition challenge',
      bankPick:'Pick a field and a difficulty to work through textbook and university course problems one at a time. Check the solution and mark yourself.',stars:'Difficulty',showSol:'Show solution',noSol:'No solution is stored yet. Ask in the community Q&A gallery or ask the AI.',
      solvedIt:'I solved it',missedIt:'I missed it',original:'Original',translated:'Translation',noKo:'',draft:'HaslaLab draft solution · not yet reviewed',refFig:'Reference figures',empty:'No more problems here. Try another difficulty or field.',
      contestPick:'Pick a competition to get its problems one at a time. Solve from the PDF, check the solution and mark yourself.',paper:'Problem',solution:'Solution',noContestSol:'This problem has no official solution.',problems:'problems',another:'Another problem',figInPdf:'The figures are in the original PDF below.',transcribed:'The text is transcribed from the original paper; if they differ, the PDF is authoritative.',noteBank:'Each problem shows its source (textbook or university course). Translations and HaslaLab draft solutions are under review. Progress is kept on this device and, when you log in, on your account too.',noteContest:'Official problems and solutions of each competition; Korean versions are HaslaLab translations. Progress is kept on this device and, when you log in, on your account too.',
      note:'Problems: Korea Institute for Curriculum and Evaluation and the Seoul, Gyeonggi and Incheon education offices (Korean only), shared within the permitted web and app use. Some unit labels are automatic and under review. Progress is kept on this device and, when you log in, on your account too.'}
  };
  /* Korean and English for now; tx() is where a further language would look up the English text */
  const LANGS=['ko','en'];
  const I18N=()=>window.HL_I18N||{};
  const state={lang:LANGS.includes(params.get('lang'))?params.get('lang'):'ko',index:null,shards:{},session:null};
  window.HL_PAGE_COPY=copy;   /* the strings, for the translation catalogue (tools/i18n) */
  const tx=en=>state.lang==='en'||state.lang==='ko'?en:(I18N().t?.(en,state.lang)??en);
  const tr=k=>copy[state.lang]?.[k]??tx(copy.en[k]);
  const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const store={
    read(){try{return JSON.parse(localStorage.getItem('hlPractice')||'{}')||{};}catch(e){return {};}},
    write(v){try{localStorage.setItem('hlPractice',JSON.stringify(v));}catch(e){}}
  };
  let saved=store.read();saved.solved||={};saved.level||={};saved.xp||=0;saved.days||=[];
  const save=()=>store.write(saved);
  saved.skills||={};saved.queue||=[];saved.wrong||={};

  /* ── progress on the account (community/src/practice-progress.js): the same Elo-style rating per unit is kept
     here so guests see it too; signed-in members' attempts go to the server in batches and their state merges
     with every other device ── */
  const START=1300,stepRating=st=>1000+100*st,ratingStep=r=>Math.max(1,Math.min(10,Math.round((r-1000)/100)));
  function updateRating(r,step,result){
    if(result==='skip')return r;
    const won=result==='right'||result==='solved'?1:0,expected=1/(1+10**((stepRating(step)-r)/400)),k=result==='right'||result==='wrong'?32:16;
    return Math.round((r+k*(won-expected))*10)/10;
  }
  const API=(()=>{let o='';try{o=localStorage.getItem('hlCmApi')||'';}catch(e){}return(/^https:\/\/[a-z0-9-]+\.haslalab\.workers\.dev\/?$/.test(o)?o:'https://haslalab-community-edge.haslalab.workers.dev').replace(/\/+$/,'');})();
  const token=()=>{try{const v=localStorage.getItem('hlCmTok')||'';return /^[A-Za-z0-9_-]{20,4096}$/.test(v)?v:'';}catch(e){return '';}};
  function record(item_id,mode,unit,step,result){
    const at=Math.floor(Date.now()/1000);
    if(result==='place'){const k=saved.skills[unit];if(!k||!k.n)saved.skills[unit]={unit,rating:stepRating(step),n:0,right_n:0,last_at:at};}
    else if(result!=='skip'){const k=saved.skills[unit]||{unit,rating:START,n:0,right_n:0,last_at:at};k.rating=updateRating(k.rating,step,result);k.n++;if(result==='right'||result==='solved')k.right_n++;k.last_at=at;saved.skills[unit]=k;}
    if(result!=='skip'&&result!=='place'){const d=today();if(saved.goalDay?.d!==d)saved.goalDay={d,n:0};saved.goalDay.n++;}
    saved.queue.push({item_id,mode,unit,step,result,at});if(saved.queue.length>500)saved.queue=saved.queue.slice(-500);
    save();scheduleSync();
  }
  function mergeState(a,b){
    const A=a||{},B=b||{},obj=(x,y,f)=>{const o={...(x||{})};for(const[k,v]of Object.entries(y||{}))o[k]=k in o?f(o[k],v):v;return o;},mx=(x,y)=>Math.max(Number(x)||0,Number(y)||0);
    const newer=(x,y)=>(Number(y?.at)||0)>(Number(x?.at)||0)?y:x||y;
    return{profile:newer(A.profile,B.profile),xp:mx(A.xp,B.xp),days:[...new Set([...(A.days||[]),...(B.days||[])])].sort().slice(-400),level:obj(A.level,B.level,mx),solved:obj(A.solved,B.solved,x=>x),wrong:obj(A.wrong,B.wrong,mx),
      bank:{done:obj(A.bank?.done,B.bank?.done,mx),stars:obj(A.bank?.stars,B.bank?.stars,(x,y)=>y??x)},contest:{done:obj(A.contest?.done,B.contest?.done,mx)}};
  }
  const stateOf=()=>({profile:saved.profile,xp:saved.xp,days:saved.days,level:saved.level,solved:saved.solved,wrong:saved.wrong,bank:saved.bank,contest:saved.contest});
  async function api(path,method='GET',body){
    const r=await fetch(API+path,{method,headers:{Authorization:'Bearer '+token(),...(body?{'content-type':'application/json'}:{})},body:body?JSON.stringify(body):undefined});
    if(!r.ok)throw new Error('api '+r.status);return r.json();
  }
  let syncTimer=0,syncing=false;state.sync=token()?'pending':'local';
  function scheduleSync(){clearTimeout(syncTimer);syncTimer=setTimeout(sync,1500);}
  async function sync(){
    if(!token()){state.sync='local';paintStats();return;}
    if(syncing){scheduleSync();return;}syncing=true;
    try{
      while(saved.queue.length){const batch=saved.queue.slice(0,50),r=await api('/api/practice/attempts','POST',{attempts:batch});saved.queue.splice(0,batch.length);for(const k of r.skills||[])saved.skills[k.unit]=k;save();}
      const r=await api('/api/practice/state','POST',{state:stateOf()});Object.assign(saved,mergeState(stateOf(),r.state));save();state.sync='saved';
    }catch(e){state.sync='error';setTimeout(scheduleSync,30000);}
    syncing=false;paintStats();
  }
  /* on opening: the account's state and ratings join this device's, then anything queued here is sent */
  async function pull(){
    if(!token())return;
    try{const r=await api('/api/practice/state');Object.assign(saved,mergeState(stateOf(),r.state));for(const k of r.skills||[])saved.skills[k.unit]=k;save();state.sync='saved';}catch(e){state.sync='error';}
    paintStats();scheduleSync();
  }
  const today=()=>new Date().toLocaleDateString('sv');   /* YYYY-MM-DD in local time */
  function streak(){
    const days=new Set(saved.days);let n=0;const d=new Date();
    if(!days.has(today()))d.setDate(d.getDate()-1);     /* today not yet studied: yesterday keeps the streak */
    while(days.has(d.toLocaleDateString('sv'))){n++;d.setDate(d.getDate()-1);}
    return n;
  }
  function reportHeight(){if(embedded)requestAnimationFrame(()=>window.parent.postMessage({type:'hl-practice-height',height:Math.ceil(document.documentElement.scrollHeight)},location.origin));}
  function tellUnit(unit){if(embedded)window.parent.postMessage({type:'hl-practice-unit',unit:unit||''},location.origin);}
  function math(latex,display){try{return window.katex?katex.renderToString(latex,{displayMode:!!display,throwOnError:false,strict:false}):esc(latex);}catch(e){return esc(latex);}}
  function blocks(list){
    return list.map(b=>{
      if(b.p)return '<p>'+b.p.map(s=>s.m!==undefined?math(s.m):esc(s.t||'')).join('')+'</p>';
      if(b.mb!==undefined)return '<div class="mb">'+math(b.mb,true)+'</div>';
      if(b.f)return `<figure><img src="practice/fig/${encodeURIComponent(b.f)}" width="${b.w}" height="${b.h}" alt="${esc(b.alt||'')}" loading="lazy"></figure>`;
      return '';
    }).join('');
  }
  const unitName=key=>{const e=P.SUBTOPICS.get(key);return e?(state.lang==='ko'?e.sub.name.ko:tx(e.sub.name.en)):key;};
  const areaName=a=>state.lang==='ko'?a.name.ko:tx(a.name.en);
  function paintStats(){
    const solvedCount=Object.keys(saved.solved).length;
    const badge=state.sync==='saved'?`<span class="stat sync ok">☁ ${tr('synced')}</span>`:state.sync==='error'?`<span class="stat sync">⚠ ${tr('syncFailed')}</span>`:state.sync==='local'?`<a class="stat sync" href="/#/login" target="_top">${tr('loginToSave')}</a>`:'';
    const tier=tierOf(saved.xp);
    $('stats').innerHTML=`<span class="stat tier t-${tier[1].toLowerCase()}" title="${tr('tier')}"><b>◆</b>${tier[1]}</span><span class="stat fire"><b>🔥 ${streak()}</b>${tr('streak')}</span><span class="stat"><b>${saved.xp}</b>${tr('xp')}</span>${saved.profile?`<span class="stat goal${(saved.goalDay?.d===today()?saved.goalDay.n:0)>=saved.profile.daily?' met':''}" title="${tr('dailyGoal')}"><b>🎯 ${saved.goalDay?.d===today()?saved.goalDay.n:0}/${saved.profile.daily}</b>${tr('dailyGoal')}</span>`:''}<span class="stat"><b>${solvedCount}</b>${tr('solved')}</span>${badge}`;
  }
  async function loadIndex(){
    if(!state.index){const r=await fetch('practice/index.json',{cache:'no-cache'});if(!r.ok)throw new Error('index');state.index=await r.json();}
    return state.index;
  }
  async function loadArea(area){
    if(!state.shards[area]){const r=await fetch('practice/data/'+encodeURIComponent(area)+'.json');if(!r.ok)throw new Error('shard');state.shards[area]=(await r.json()).items;}
    return state.shards[area];
  }
  function failed(retry){$('app').innerHTML=`<p>${tr('failed')}</p><button type="button" id="retry">${tr('retry')}</button>`;$('retry').onclick=retry;reportHeight();}

  /* ── unit list ── */
  async function home(){
    state.mode='exam';paintTabs();
    state.session=null;tellUnit('');paintStats();
    $('app').innerHTML=`<p>${tr('loading')}</p>`;
    let index,tracked;try{[index,tracked]=await Promise.all([loadIndex(),allTrackItems()]);}catch(e){failed(home);return;}
    /* a unit's problems: the Korean exams' calculation problems and the exam tracks' problems together */
    const counts={};for(const [u,c] of Object.entries(index.counts))counts[u]={...c};
    for(const i of tracked){const c=counts[i.u]||={};c[i.s]=(c[i.s]||0)+1;}
    const solvedIn=unit=>Object.entries(saved.solved).filter(([,u])=>u===unit).length;
    $('app').innerHTML=`<p class="pick">${tr('pick')}</p><div class="areas">${P.AREAS.map(area=>{
      const units=area.subtopics.map(sub=>{const key=area.key+'/'+sub.key,c=counts[key];return{key,sub,total:c?Object.values(c).reduce((a,b)=>a+b,0):0,steps:c?Object.keys(c).map(Number):[]};}).filter(u=>u.total);
      if(!units.length)return '';
      return `<section class="area"><h2>${esc(areaName(area))}</h2>${units.map(u=>{
        const done=solvedIn(u.key),lvl=saved.level[u.key]||Math.min(...u.steps);
        return `<button type="button" class="unit" data-unit="${u.key}"><span class="name">${esc(unitName(u.key))}<small>${tr('step')} ${lvl} · ${done}/${u.total} ${tr('progress')}</small></span><span class="bar"><i style="width:${Math.round(100*done/u.total)}%"></i></span></button>`;}).join('')}</section>`;
    }).join('')}</div>`;
    $('app').querySelectorAll('[data-unit]').forEach(b=>b.addEventListener('click',()=>start(b.dataset.unit)));
    reportHeight();
  }

  /* ── a session ── */
  async function start(unit){
    $('app').innerHTML=`<p>${tr('loading')}</p>`;
    let items;
    try{const [kr,tracked]=await Promise.all([loadArea(unit.split('/')[0]).catch(()=>[]),allTrackItems()]);items=[...kr,...tracked].filter(i=>i.u===unit);}catch(e){failed(()=>start(unit));return;}
    if(!items.length){home();return;}
    const steps=[...new Set(items.map(i=>i.s))].sort((a,b)=>a-b);
    const level=saved.level[unit]&&steps.includes(saved.level[unit])?saved.level[unit]:steps[0];
    state.session={unit,items,steps,level,n:0,right:0,run:0,seen:new Set(),current:null,answered:false,xp:0};
    tellUnit(unit);next();
  }
  function pick(s){
    if(s.first&&!s.seen.has(s.first.id))return s.first;
    if(s.fixed)return s.items.find(i=>!s.seen.has(i.id))||null;
    /* nearest step to the learner's level, unsolved and unseen first */
    const pool=s.items.filter(i=>!s.seen.has(i.id));
    const score=i=>Math.abs(i.s-s.level)*10+(saved.solved[i.id]?5:0)+Math.random();
    return pool.sort((a,b)=>score(a)-score(b))[0]||null;
  }
  function next(){
    const s=state.session;
    if(s.n>=SESSION&&!s.diag){summary();return;}
    const item=s.diag?pickDiag(s):pick(s);if(!item){summary();return;}
    s.current=item;s.answered=false;s.seen.add(item.id);s.n++;
    if(item.kind==='track'){showTrack(item);return;}
    const imageChoices=item.ch.every(c=>!c.c.length);
    $('app').innerHTML=`<div class="session">
      ${sessionHead(s,item)}
      <div class="q">${blocks(item.b)}</div>
      <div class="choices${imageChoices?' compact':''}" role="group">${item.ch.map(c=>`<button type="button" class="choice" data-n="${c.n}"><span class="no">${'①②③④⑤'[c.n-1]}</span>${imageChoices?'':`<span>${blocks(c.c).replace(/^<p>|<\/p>$/g,'')}</span>`}</button>`).join('')}</div>
      <div id="feedback"></div>
      <div class="foot"><span class="src">${esc(item.src)} · ${esc(item.by)}${item.pdf?` · <a href="${esc(item.pdf)}" target="_blank" rel="noopener noreferrer">${tr('pdf')}</a>`:''} · ${tr('time')} ${item.sec}${tr('sec')}</span><span class="footbtns"><button type="button" id="skip">${tr('skip')}</button><button type="button" class="primary" id="next" hidden>${s.n>=SESSION?tr('finish'):tr('next')}</button></span></div>
    </div>`;
    $('quit').onclick=s.fixed?todayHome:home;
    $('skip').hidden=!!s.diag;
    if(state.lang!=='ko')localizeExam(item);
    $('app').querySelectorAll('.choice').forEach(b=>b.addEventListener('click',()=>answer(Number(b.dataset.n))));
    $('next').onclick=next;
    $('skip').onclick=()=>{if(s.answered)return;record(item.id,'exam',item.u,item.s,'skip');s.skipped=(s.skipped||0)+1;s.n--;s.extra=(s.extra||0)+1;if(s.extra>30){summary();return;}next();};
    reportHeight();window.scrollTo?.(0,0);if(embedded)window.parent.postMessage({type:'hl-practice-top'},location.origin);
  }
  /* the Korean exams' calculation problems for English readers: each paragraph and choice goes to the cached AI
     translation as text with its math in $…$, figures stay; the Korean is one tap away */
  const segText=p=>p.map(x=>x.m!==undefined?'$'+x.m+'$':(x.t||'')).join('');
  async function localizeExam(item){
    const s=state.session,paras=item.b.filter(b=>b.p).map(b=>segText(b.p)),words=t=>/[^\s\d.,()+\-=]/.test(t.replace(/\$[^$]*\$/g,'')),
      chs=item.ch.map(c=>{const t=c.c.filter(b=>b.p).map(b=>segText(b.p)).join(' ');return words(t)?t:'';});   /* a choice that is only math needs no translation */
    if(!paras.length)return;
    const q=$('app').querySelector('.q');q.insertAdjacentHTML('afterend',`<p class="src" id="trnote">${tr('translating')}</p>`);
    const out=await aiTranslate([...paras,...chs]);
    if(state.session!==s||s.current!==item||!out.some(Boolean)){if($('trnote')&&s.current===item)$('trnote').textContent='';return;}
    const korean={q:q.innerHTML,ch:[...$('app').querySelectorAll('.choice')].map(b=>b.lastElementChild?.innerHTML)};let orig=false;
    const paint=()=>{
      if(orig)q.innerHTML=korean.q;
      else{let n=0;q.innerHTML=item.b.map(b=>{if(!b.p)return blocks([b]);const i=n++;return textHtml(out[i]||paras[i]);}).join('');typeset(q);}
      $('app').querySelectorAll('.choice').forEach((b,i)=>{const span=b.lastElementChild;if(!span||!chs[i]||span.classList.contains('no'))return;
        if(orig)span.innerHTML=korean.ch[i];else{span.innerHTML=textHtml(out[paras.length+i]||chs[i]).replace(/^<p>|<\/p>$/g,'');typeset(span);}});
      $('trnote').innerHTML=`${tr('aiTranslated')} · <a href="#" id="trtoggle">${orig?tr('showTranslation'):tr('showOriginal')}</a>`;$('trtoggle').onclick=e=>{e.preventDefault();orig=!orig;paint();};reportHeight();
    };
    paint();
  }
  function answer(choice){
    const s=state.session,item=s.current;if(s.answered)return;s.answered=true;
    const ok=choice===item.a;
    $('app').querySelectorAll('.choice').forEach(b=>{b.disabled=true;const n=Number(b.dataset.n);if(n===item.a)b.classList.add('right');else if(n===choice)b.classList.add('wrong');});
    let note='';
    if(ok){
      s.right++;s.run++;const gain=10+2*item.s;s.xp+=gain;saved.xp+=gain;saved.solved[item.id]=item.u;delete saved.wrong[item.id];
      if(s.fixed||s.diag){}else if(s.run>=2){const up=s.steps.find(x=>x>s.level);if(up){s.level=up;note=' · '+tr('up')+' ↑';}s.run=0;}
    }else{
      s.run=0;saved.wrong[item.id]=Math.floor(Date.now()/1000);
      if(!s.fixed&&!s.diag){const down=[...s.steps].reverse().find(x=>x<s.level);if(down){s.level=down;note=' · '+tr('down');}}
    }
    if(!s.fixed)saved.level[s.unit]=s.level;
    record(item.id,s.diag?'diag':'exam',item.u,item.s,ok?'right':'wrong');if(s.diag)diagStep(s,ok);
    if(!saved.days.includes(today())){saved.days.push(today());saved.days=saved.days.slice(-400);}
    save();paintStats();
    $('feedback').innerHTML=`<p class="feedback ${ok?'ok':'bad'}">${ok?tr('right'):tr('wrong')+' '+'①②③④⑤'[item.a-1]}${note}</p>`;
    $('next').hidden=false;$('skip').hidden=true;$('next').focus();reportHeight();
  }
  function summary(){
    const s=state.session;
    if(s.diag){diagSummary(s);return;}
    $('app').innerHTML=`<div class="session summary"><p class="eyebrow">${tr('done')}</p><p class="big">${s.right}${tr('of')}${s.n}</p><p>${tr('result')} · +${s.xp} XP · ${s.mode==='bank'?'★'.repeat(s.stars):s.fixed?tr('tabToday'):tr('step')+' '+s.level+' · '+tr(LEVELS[levelOf(s.level)])}${s.skipped?` · ${s.skipped} ${tr('skipped')}`:''} · 🔥 ${streak()}${tr('streak')}</p>
      <div class="actions"><button type="button" class="primary" id="again">${tr('again')}</button><button type="button" id="units">${tr('units')}</button></div></div>`;
    if(s.assignment){$('again').onclick=classHome;$('units').onclick=classHome;$('again').textContent=tr('tabClass');reportHeight();return;}
    $('again').onclick=()=>s.fixed?todayHome():s.mode==='bank'?bankStart(s.field,s.stars):s.mode==='track'?trackStart(s.track,s.syl):start(s.unit);$('units').onclick=s.fixed?todayHome:s.mode==='bank'?bankHome:s.mode==='track'?tracksHome:home;reportHeight();
  }


  /* ── modes: Korean exams (graded), books & university (problem bank, self-marked), competitions (PDF, self-marked) ── */
  const BANK_API='https://haslalab-problem-bank.haslalab.workers.dev';
  const PDF_HOST=/^https:\/\/haslalab-pdf\.haslalab\.workers\.dev\/pdf\//;
  const BANK_FIELDS=[['classical_mechanics','고전역학','Classical mechanics'],['electromagnetism','전자기학','Electromagnetism'],['oscillations_waves','진동과 파동','Oscillations and waves'],
    ['optics','광학','Optics'],['thermodynamics','열역학','Thermodynamics'],['statistical_mechanics','통계역학','Statistical mechanics'],['quantum_mechanics','양자역학','Quantum mechanics'],
    ['special_relativity','특수 상대성','Special relativity'],['general_relativity','일반 상대성','General relativity'],['mathematical_methods','수리물리','Mathematical methods']];
  saved.bank||={done:{},stars:{}};saved.contest||={done:{}};
  const BANK_AREA={classical_mechanics:'mechanics',electromagnetism:'em',oscillations_waves:'waves',optics:'optics',thermodynamics:'thermal',statistical_mechanics:'thermal',quantum_mechanics:'modern',special_relativity:'modern',general_relativity:'modern',mathematical_methods:'math'};
  function studied(xp){saved.xp+=xp;if(!saved.days.includes(today())){saved.days.push(today());saved.days=saved.days.slice(-400);}save();paintStats();}
  function paintTabs(){
    $('tabs').innerHTML=[['today',tr('tabToday')],['exam',tr('tabUnits')],['tracks',tr('tabTracks')],['bank',tr('tabBank')],['contest',tr('tabContest')],['class',tr('tabClass')]].map(([k,l])=>`<button type="button" role="tab" data-mode="${k}" aria-selected="${state.mode===k}">${l}</button>`).join('');
    $('tabs').querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>MODES[b.dataset.mode]());
    $('note').textContent=tr(state.mode==='bank'?'noteBank':state.mode==='contest'?'noteContest':state.mode==='exam'?'noteUnits':'noteTracks');
  }
  /* bank text: paragraphs with $…$ and $$…$$ left to KaTeX auto-render */
  function textHtml(t){return esc(t||'').split(/\n{2,}/).map(p=>'<p>'+p.replace(/\n/g,'<br>')+'</p>').join('');}
  function typeset(el){try{window.renderMathInElement?.(el,{delimiters:[{left:'$$',right:'$$',display:true},{left:'\\[',right:'\\]',display:true},{left:'$',right:'$',display:false},{left:'\\(',right:'\\)',display:false}],throwOnError:false});}catch(e){}}
  function pickVersion(item){
    const vs=item.versions||[],ko=vs.find(v=>v.language==='ko'),orig=vs.find(v=>v.role==='original')||vs[0];
    return state.lang==='ko'&&ko?{main:ko,alt:orig!==ko?orig:null}:{main:orig||ko,alt:null,missing:state.lang==='ko'&&!ko};
  }
  async function bankGet(path){const r=await fetch(BANK_API+path,{headers:{accept:'application/json'}});if(!r.ok)throw new Error('bank '+r.status);return r.json();}

  function bankHome(){
    state.mode='bank';state.session=null;paintTabs();paintStats();tellUnit('');
    const field=state.bankField||BANK_FIELDS[0][0];
    $('app').innerHTML=`<p class="pick">${tr('bankPick')}</p><div class="areas">${BANK_FIELDS.map(([k,ko,en])=>{
      const st=saved.bank.stars[k]||1;
      return `<section class="area"><h2>${esc(state.lang==='ko'?ko:tx(en))}</h2><div class="starrow" role="group" aria-label="${tr('stars')}">${[1,2,3,4,5].map(n=>`<button type="button" class="unit star${n===st?' cur':''}" data-field="${k}" data-stars="${n}">${'★'.repeat(n)}<small>${tr('step')} ${P.stepFromStars(n)}</small></button>`).join('')}</div></section>`;}).join('')}</div>`;
    $('app').querySelectorAll('[data-field]').forEach(b=>b.onclick=()=>bankStart(b.dataset.field,Number(b.dataset.stars)));
    reportHeight();
  }
  async function bankStart(field,stars){
    $('app').innerHTML=`<p>${tr('loading')}</p>`;
    saved.bank.stars[field]=stars;save();
    const s=state.session={mode:'bank',field,stars,pool:[],cursor:null,more:true,n:0,right:0,skipped:0,xp:0,seen:new Set()};
    try{await bankFill(s);}catch(e){failed(()=>bankStart(field,stars));return;}
    bankNext();
  }
  async function bankFill(s){
    for(let page=0;page<3&&s.more&&s.pool.length<40;page++){
      const q=new URLSearchParams({lang:state.lang,limit:'20',collection:'physics',subject:s.field,stars:String(s.stars)});if(s.cursor)q.set('cursor',s.cursor);
      const j=await bankGet('/api/problem-bank/search?'+q);
      s.pool.push(...(j.items||[]).filter(i=>!saved.bank.done[i.id]&&!s.seen.has(i.id)));s.cursor=j.next_cursor||null;s.more=!!(j.has_more&&s.cursor);
    }
    for(let i=s.pool.length-1;i>0;i--){const k=Math.floor(Math.random()*(i+1));[s.pool[i],s.pool[k]]=[s.pool[k],s.pool[i]];}
  }
  async function bankNext(){
    const s=state.session;
    if(s.n>=5){summary();return;}
    if(!s.pool.length&&s.more){try{await bankFill(s);}catch(e){}}
    const pick=s.pool.shift();
    if(!pick){$('app').innerHTML=`<div class="session"><p>${tr('empty')}</p><div class="actions"><button type="button" id="units">${tr('units')}</button></div></div>`;$('units').onclick=bankHome;reportHeight();return;}
    s.seen.add(pick.id);s.n++;s.answered=false;s.current=pick;
    $('app').innerHTML=`<div class="session"><p>${tr('loading')}</p></div>`;
    let item;try{item=(await bankGet('/api/problem-bank/questions/'+pick.id+'?lang='+state.lang)).question;}catch(e){failed(bankNext);return;}
    const v=pickVersion(item),figs=(item.assets||[]).filter(a=>a.role==='figure'&&/^\/api\/problem-bank\/assets\/a_[0-9a-f]{64}$/.test(a.url||''));
    const fig=a=>`<figure><img src="${BANK_API+a.url}" alt="" loading="lazy"></figure>`;
    const label=BANK_FIELDS.find(f=>f[0]===s.field);
    $('app').innerHTML=`<div class="session">
      <div class="shead"><button type="button" class="back" id="quit">${tr('quit')}</button><span class="unitname">${esc(state.lang==='ko'?label[1]:tx(label[2]))}</span><span class="lvl">${'★'.repeat(s.stars)}</span><span class="progress" aria-hidden="true"><i style="width:${Math.round(100*(s.n-1)/5)}%"></i></span><span>${s.n}/5</span></div>
      ${v.missing?`<p class="src">${tr('noKo')}</p>`:''}<div class="q" id="qtext">${textHtml(v.main?.text)}</div>
      ${v.alt?`<details class="alt"><summary>${tr('original')}</summary><div class="q" id="qalt">${textHtml(v.alt.text)}</div></details>`:''}
      ${figs.filter(a=>a.placement!=='reference').map(fig).join('')}
      ${figs.some(a=>a.placement==='reference')?`<details class="alt"><summary>${tr('refFig')}</summary>${figs.filter(a=>a.placement==='reference').map(fig).join('')}</details>`:''}
      <div id="sol"></div><div id="feedback"></div>
      <div class="foot"><span class="src">${esc(pick.source_title||'')}${item.original_number?' · '+esc(item.original_number):''}</span>
        <span class="footbtns"><button type="button" id="skip">${tr('skip')}</button><button type="button" id="showSol">${tr('showSol')}</button><button type="button" class="primary" id="good">${tr('solvedIt')}</button><button type="button" id="miss">${tr('missedIt')}</button><button type="button" class="primary" id="next" hidden>${s.n>=5?tr('finish'):tr('next')}</button></span></div></div>`;
    typeset($('app'));
    $('quit').onclick=bankHome;
    const bankUnit=(BANK_AREA[s.field]||'mechanics')+'/*',bankStep=P.stepFromStars(s.stars);
    $('skip').onclick=()=>{if(s.answered)return;record(pick.id,'bank',bankUnit,bankStep,'skip');s.skipped++;s.n--;bankNext();};
    $('showSol').onclick=async()=>{
      $('showSol').disabled=true;$('sol').innerHTML=`<p class="src">${tr('loading')}</p>`;
      try{const j=await bankGet('/api/problem-bank/questions/'+pick.id+'/solutions?lang='+state.lang);
        const sols=(j.solutions||[]).map(x=>({x,v:pickVersion(x).main})).filter(o=>o.v?.text);
        $('sol').innerHTML=sols.length?sols.map(({x,v})=>`<section class="solution"><h3>${tr('solution')}${x.authorship==='haslalab_original_draft'?` <small>${tr('draft')}</small>`:''}</h3>${textHtml(v.text)}</section>`).join(''):`<p class="feedback bad">${tr('noSol')}</p>`;
        typeset($('sol'));}catch(e){$('sol').innerHTML=`<p class="feedback bad">${tr('failed')}</p>`;}
      reportHeight();
    };
    const mark=ok=>{if(s.answered)return;s.answered=true;
      record(pick.id,'bank',bankUnit,bankStep,ok?'solved':'missed');
      if(ok){s.right++;const gain=10+5*s.stars;s.xp+=gain;saved.bank.done[pick.id]=1;studied(gain);}else{saved.bank.done[pick.id]=0;studied(2);}
      ['good','miss','skip'].forEach(id=>$(id).hidden=true);$('next').hidden=false;$('next').focus();
      $('feedback').innerHTML=`<p class="feedback ${ok?'ok':'bad'}">${ok?'✓ '+tr('solvedIt'):tr('missedIt')}</p>`;reportHeight();};
    $('good').onclick=()=>mark(true);$('miss').onclick=()=>mark(false);$('next').onclick=bankNext;
    reportHeight();if(embedded)window.parent.postMessage({type:'hl-practice-top'},location.origin);
  }

  async function contestHome(){
    state.mode='contest';state.session=null;paintTabs();paintStats();tellUnit('');
    $('app').innerHTML=`<p>${tr('loading')}</p>`;
    try{if(!state.contests){const r=await fetch('practice/contests.json');if(!r.ok)throw 0;state.contests=(await r.json()).contests;}}catch(e){failed(contestHome);return;}
    $('app').innerHTML=`<p class="pick">${tr('contestPick')}</p><div class="areas">${state.contests.map(c=>{
      const total=c.structured||c.problems.length,done=Object.entries(saved.contest.done).filter(([id,v])=>v===1&&id.startsWith(c.key+'-')&&(c.structured?id.includes('~'):!id.includes('~'))).length;
      return `<section class="area"><button type="button" class="unit" data-contest="${c.key}"><span class="name"><b>${esc(nameOf(c.name))}</b><small>${tr('step')} ${c.step} · ${total} ${tr('problems')} · ${done} ${tr('progress')}</small></span><span class="bar"><i style="width:${Math.round(100*done/Math.max(1,total))}%"></i></span></button></section>`;}).join('')}</div>`;
    $('app').querySelectorAll('[data-contest]').forEach(b=>b.onclick=()=>contestShow(b.dataset.contest));
    reportHeight();
  }
  /* PDFs are drawn page by page with pdf.js (the same build the HPhO exam uses), so phones show them too */
  const PDFJS='https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/';
  let pdfjs=null;
  const loadPdfjs=()=>pdfjs||=new Promise((ok,fail)=>{if(window.pdfjsLib)return ok(window.pdfjsLib);const sc=document.createElement('script');sc.src=PDFJS+'pdf.min.js';
    sc.onload=()=>{if(!window.pdfjsLib){pdfjs=null;return fail(Error('pdfjs'));}window.pdfjsLib.GlobalWorkerOptions.workerSrc=PDFJS+'pdf.worker.min.js';ok(window.pdfjsLib);};sc.onerror=()=>{pdfjs=null;fail(Error('pdfjs'));};document.head.append(sc);});
  let pdfJob=0;
  async function showPdf(url){
    const box=$('pdf');if(!box||!PDF_HOST.test(url))return;const job=++pdfJob;box.innerHTML=`<p class="src">${tr('loading')}</p>`;
    try{
      const lib=await loadPdfjs(),doc=await lib.getDocument({url,isEvalSupported:false}).promise;if(job!==pdfJob)return;
      box.innerHTML='';const width=Math.min(box.clientWidth||800,1000),dpr=Math.min(devicePixelRatio||1,2);
      for(let i=1;i<=Math.min(doc.numPages,16);i++){
        const page=await doc.getPage(i);if(job!==pdfJob)return;
        const vp=page.getViewport({scale:width/page.getViewport({scale:1}).width*dpr}),cv=document.createElement('canvas');
        cv.width=vp.width;cv.height=vp.height;cv.style.width='100%';box.append(cv);
        await page.render({canvasContext:cv.getContext('2d'),viewport:vp}).promise;reportHeight();
      }
    }catch(e){if(job===pdfJob)box.innerHTML=`<p class="src">${tr('failed')} <a href="${esc(url)}" target="_blank" rel="noopener">PDF ↗</a></p>`;}
    reportHeight();
  }
  /* a competition: problems transcribed per problem (text with LaTeX and the figures cut from the paper) when
     practice/contest/<key>.json has them; otherwise the paper itself, drawn with pdf.js */
  async function contestItems(key){
    state.contestItems||={};
    if(!(key in state.contestItems)){try{const r=await fetch('practice/contest/'+encodeURIComponent(key)+'.json');state.contestItems[key]=r.ok?(await r.json()).items:[];}catch(e){state.contestItems[key]=[];}}
    return state.contestItems[key];
  }
  async function contestShow(key,skipId){
    const c=state.contests.find(x=>x.key===key);if(!c){contestHome();return;}
    const items=await contestItems(key);
    const L={ko:'한국어',en:'English',hu:'Magyar'},safe=u=>PDF_HOST.test(u||'')?u:'';
    let item=null,p;
    if(items.length){
      const open=items.filter(i=>saved.contest.done[i.id]!==1&&i.id!==skipId),pool=open.length?open:items;
      item=pool[Math.floor(Math.random()*pool.length)];p=c.problems.find(x=>x.id===item.pdf);
    }else{
      const open=c.problems.filter(x=>saved.contest.done[x.id]!==1&&x.id!==skipId),pool=open.length?open:c.problems;
      p=pool[Math.floor(Math.random()*pool.length)];
    }
    const doneId=item?item.id:p.id;
    const langs=Object.entries(p.papers).filter(([,u])=>safe(u)),pref=langs.find(([l])=>l===state.lang)||langs[0];
    const sols=Object.entries(p.sols||{}).filter(([,u])=>safe(u));
    const label=item?`${item.year} · ${p.key}${item.key&&item.key!==p.key?' · '+item.key:''}`:`${p.year} · ${p.key}`;
    const title=item?.title||p.title||'';
    const body=item?item.b.map(b=>b.f?`<figure><img src="practice/contest/fig/${encodeURIComponent(b.f)}" width="${b.w}" height="${b.h}" alt="" loading="lazy"></figure>`:textHtml(b.t)).join(''):'';
    $('app').innerHTML=`<div class="session">
      <div class="shead"><button type="button" class="back" id="quit">${tr('quit')}</button><span class="unitname">${esc(nameOf(c.name))}</span><span class="lvl">${esc(label)}</span>${title?`<span>${esc(title)}</span>`:''}</div>
      ${item?`<div class="q" id="qtext">${body}</div>`:''}
      <div class="langrow">${tr('paper')}: ${langs.map(([l,u])=>`<button type="button" class="${!item&&l===pref[0]?'cur':''}" data-pdf="${esc(u)}">${L[l]||l} PDF</button>`).join('')} <a href="${esc(pref[1])}" target="_blank" rel="noopener" id="openPdf">PDF ↗</a></div>
      <div id="pdf" class="pdf"${item?' hidden':''} role="document" aria-label="${esc(nameOf(c.name))} ${esc(label)}"><p class="src">${tr('loading')}</p></div>
      <div id="feedback"></div>
      <div class="foot"><span class="src">${sols.length?`${tr('solution')}: `+sols.map(([l,u])=>`<a href="${esc(u)}" target="_blank" rel="noopener">${L[l]||l} ↗</a>`).join(' · '):tr('noContestSol')}${item?' · '+tr('transcribed'):''}</span>
        <span class="footbtns"><button type="button" id="skip">${tr('skip')}</button><button type="button" class="primary" id="good">${tr('solvedIt')}</button><button type="button" id="miss">${tr('missedIt')}</button><button type="button" class="primary" id="next" hidden>${tr('another')}</button></span></div></div>`;
    if(item)typeset($('qtext'));
    /* the transcriptions are Korean: other readers get an AI translation, with the Korean one tap away */
    if(item&&state.lang!=='ko'){
      const job=state.contestJob=(state.contestJob||0)+1,texts=item.b.filter(b=>b.t).map(b=>b.t);
      $('qtext').insertAdjacentHTML('beforebegin',`<p class="src" id="trnote">${tr('translating')}</p>`);
      aiTranslate(texts).then(out=>{
        if(state.contestJob!==job||!$('qtext'))return;
        if(!out.some(Boolean)){$('trnote').textContent='';return;}
        let orig=false;const map=new Map(texts.map((t,i)=>[t,out[i]||t]));
        const paint=()=>{$('qtext').innerHTML=item.b.map(b=>b.f?`<figure><img src="practice/contest/fig/${encodeURIComponent(b.f)}" width="${b.w}" height="${b.h}" alt="" loading="lazy"></figure>`:textHtml(orig?b.t:map.get(b.t))).join('');typeset($('qtext'));
          $('trnote').innerHTML=`${tr('aiTranslated')} · <a href="#" id="trtoggle">${orig?tr('showTranslation'):tr('showOriginal')}</a>`;$('trtoggle').onclick=e=>{e.preventDefault();orig=!orig;paint();};reportHeight();};
        paint();
      });
    }
    /* a figure that could not be cut out is described in brackets: point to the paper */
    if(item&&item.b.some(b=>/\[(그림|Figure)[^\]]*\]/.test(b.t||''))&&!item.b.some(b=>b.f))$('qtext').insertAdjacentHTML('beforeend',`<p class="src">${tr('figInPdf')}</p>`);
    $('app').querySelectorAll('[data-pdf]').forEach(b=>b.onclick=()=>{$('pdf').hidden=false;showPdf(b.dataset.pdf);$('openPdf').href=b.dataset.pdf;$('app').querySelectorAll('[data-pdf]').forEach(x=>x.classList.toggle('cur',x===b));});
    if(!item)showPdf(pref[1]);
    $('quit').onclick=contestHome;$('skip').onclick=()=>{record(doneId,'contest','contest/'+key,c.step,'skip');contestShow(key,doneId);};$('next').onclick=()=>contestShow(key,doneId);
    const mark=ok=>{saved.contest.done[doneId]=ok?1:0;record(doneId,'contest','contest/'+key,c.step,ok?'solved':'missed');studied(ok?20+5*c.step:2);['good','miss','skip'].forEach(id=>$(id).hidden=true);$('next').hidden=false;
      $('feedback').innerHTML=`<p class="feedback ${ok?'ok':'bad'}">${ok?'✓ '+tr('solvedIt'):tr('missedIt')}</p>`;reportHeight();};
    $('good').onclick=()=>mark(true);$('miss').onclick=()=>mark(false);
    reportHeight();if(embedded)window.parent.postMessage({type:'hl-practice-top'},location.origin);
  }


  /* ── today: ten graded problems chosen from the ratings — review of earlier mistakes, the weakest and the
     longest-untouched units at the learner's step, and one stretch problem — plus a textbook and a competition
     suggestion ── */
  async function allExamItems(){
    const index=await loadIndex(),areas=[...new Set(Object.keys(index.counts).map(u=>u.split('/')[0]))];
    return (await Promise.all(areas.map(loadArea))).flat();
  }
  function unitStatus(units){
    const nowS=Date.now()/1000;
    return units.map(u=>{const k=saved.skills[u];const r=k?k.rating:START,days=k?(nowS-k.last_at)/86400:99;
      /* lower is more urgent: a weak rating, few attempts, or a long gap since the last one */
      return{u,k,r,step:ratingStep(r),urgency:r-Math.min(days,30)*4-(k?0:60)+(k&&k.n>=6&&k.right_n/k.n>0.8?80:0)};}).sort((a,b)=>a.urgency-b.urgency);
  }
  function chooseToday(items){
    const byUnit={};for(const it of items)(byUnit[it.u]||=[]).push(it);
    const status=unitStatus(Object.keys(byUnit)),chosen=[],taken=new Set();
    const add=it=>{if(it&&!taken.has(it.id)&&chosen.length<SESSION){taken.add(it.id);chosen.push({...it,why:it.why});}};
    const near=(u,step,why)=>{const pool=(byUnit[u]||[]).filter(i=>!taken.has(i.id)&&!saved.solved[i.id]&&!saved.wrong[i.id]);
      pool.sort((a,b)=>Math.abs(a.s-step)-Math.abs(b.s-step)+(Math.random()-.5)*.4);return pool[0]&&{...pool[0],why};};
    const byId=new Map(items.map(i=>[i.id,i]));
    for(const [id] of Object.entries(saved.wrong).sort((a,b)=>a[1]-b[1]).slice(0,3)){const it=byId.get(id);if(it)add({...it,why:'review'});}
    for(const st of status.slice(0,3)){add(near(st.u,st.step,'weak'));add(near(st.u,st.step,'weak'));}
    const strong=[...status].filter(x=>x.k&&x.k.n>=3).sort((a,b)=>b.r-a.r)[0];
    if(strong)add(near(strong.u,strong.step+1,'stretch'));
    for(const st of status.slice(3)){if(chosen.length>=SESSION)break;add(near(st.u,st.step,'new'));}
    return{chosen,status};
  }
  async function todayHome(){
    if(!saved.profile){startHome();return;}
    state.mode='today';state.session=null;paintTabs();paintStats();tellUnit('');
    $('app').innerHTML=`<p>${tr('loading')}</p>`;
    let items;try{items=await startPool();}catch(e){failed(todayHome);return;}
    const {chosen,status}=chooseToday(items);
    const why={review:tr('whyReview'),weak:tr('whyWeak'),stretch:tr('whyStretch'),new:tr('whyNew')};
    const counts=chosen.reduce((m,i)=>(m[i.why]=(m[i.why]||0)+1,m),{});
    const weakUnits=[...new Set(chosen.filter(i=>i.why==='weak').map(i=>i.u))];
    /* textbook: the field whose area rating is lowest; competition: the one closest to the learner's best step */
    const areaRating=a=>saved.skills[a+'/*']?.rating??(()=>{const ks=Object.values(saved.skills).filter(k=>k.unit.startsWith(a+'/'));return ks.length?ks.reduce((x,k)=>x+k.rating,0)/ks.length:START;})();
    const field=[...BANK_FIELDS].sort((x,y)=>areaRating(BANK_AREA[x[0]])-areaRating(BANK_AREA[y[0]]))[0];
    const fieldStars=Math.max(1,Math.min(5,ratingStep(areaRating(BANK_AREA[field[0]]))-3));
    const best=Math.max(START,...Object.values(saved.skills).map(k=>k.rating)),bestStep=ratingStep(best);
    let contests=state.contests;try{if(!contests){const r=await fetch('practice/contests.json');contests=state.contests=(await r.json()).contests;}}catch(e){contests=[];}
    const contest=[...contests].sort((a,b)=>Math.abs(a.step-(bestStep+3))-Math.abs(b.step-(bestStep+3)))[0];
    const top=status.filter(x=>x.k).sort((a,b)=>a.r-b.r);
    const answers=Object.values(saved.skills).reduce((n,k)=>n+(k.n||0),0);
    const placeCard=answers<5&&!saved.diagAt?`<section class="session diagcard"><h2>${tr('diagTitle')}</h2><p class="src">${tr('diagBody')}</p><div class="actions"><button type="button" class="primary" id="diagGo">${tr('diagStart')}</button></div></section>`:'';
    $('app').innerHTML=`${placeCard}<section class="session today">
        <h2>${tr('todayTitle')} <a href="#" class="src" id="editProfile">${tr('editProfile')}</a></h2>
        <p class="src">${Object.entries(counts).map(([k,n])=>`${why[k]} ${n}`).join(' · ')}${weakUnits.length?` · ${tr('focus')}: ${weakUnits.map(u=>esc(unitName(u))).join(', ')}`:''}</p>
        <ol class="todaylist">${chosen.map(i=>`<li><span class="tag ${i.why}">${why[i.why]}</span> ${esc(unitName(i.u))} <small>${tr('step')} ${i.s}</small></li>`).join('')}</ol>
        <div class="actions"><button type="button" class="primary" id="startToday"${chosen.length?'':' disabled'}>${tr('startToday')}</button></div>
      </section>
      <div class="areas suggest">
        <button type="button" class="area unit" id="sugBank"><span class="name"><b>${tr('tabBank')}</b><small>${esc(state.lang==='ko'?field[1]:tx(field[2]))} · ${'★'.repeat(fieldStars)}</small></span><span>→</span></button>
        ${contest?`<button type="button" class="area unit" id="sugContest"><span class="name"><b>${tr('tabContest')}</b><small>${esc(nameOf(contest.name))} · ${tr('step')} ${contest.step}</small></span><span>→</span></button>`:''}
      </div>
      ${top.length?`<section class="area skills"><h2>${tr('mySkills')}</h2><table><thead><tr><th>${tr('unit')}</th><th>${tr('step')}</th><th>${tr('accuracy')}</th></tr></thead><tbody>${top.slice(0,12).map(x=>`<tr><td>${esc(unitName(x.u))}</td><td>${x.step} <span class="lv lv${levelOf(x.step)}">${tr(LEVELS[levelOf(x.step)])}</span></td><td>${Math.round(100*x.k.right_n/Math.max(1,x.k.n))}% <small>(${x.k.n})</small></td></tr>`).join('')}</tbody></table></section>`:`<p class="src">${tr('noSkills')}</p>`}`;
    $('startToday').onclick=()=>{state.session={unit:'today',fixed:true,items:chosen,steps:[],level:0,n:0,right:0,run:0,seen:new Set(),current:null,answered:false,xp:0};next();};
    $('sugBank').onclick=()=>{state.bankField=field[0];bankStart(field[0],fieldStars);};
    if($('diagGo'))$('diagGo').onclick=diagStart;
    $('editProfile').onclick=e=>{e.preventDefault();startHome(true);};
    if($('sugContest'))$('sugContest').onclick=()=>{paintTabs();contestShow(contest.key);};
    reportHeight();
  }

  /* ── levels: a unit's step reads as a level name; all XP together gives a tier, like a competitive-programming judge ── */
  const LEVELS=['lvBeginner','lvFamiliar','lvProficient','lvMaster'];
  const levelOf=step=>step<=2?0:step<=4?1:step<=6?2:3;
  const TIERS=[[0,'Bronze'],[500,'Silver'],[2000,'Gold'],[6000,'Platinum'],[15000,'Diamond'],[40000,'Ruby']];
  const tierOf=xp=>[...TIERS].reverse().find(t=>xp>=t[0]);
  function sessionHead(s,item){
    const name=s.diag?tr('diagTitle'):s.assignment?s.label:s.fixed?tr('tabToday')+' · '+unitName(item.u):s.mode==='track'?s.label:unitName(s.unit);
    const total=s.diag?s.diag.areas.length*2:SESSION;
    return `<div class="shead"><button type="button" class="back" id="quit">${tr('quit')}</button><span class="unitname">${esc(name)}</span><span class="lvl">${tr('step')} ${item.s}</span><span class="progress" aria-hidden="true"><i style="width:${Math.round(100*(s.n-1)/total)}%"></i></span><span>${s.n}/${total}</span></div>`;
  }

  /* ── the member's plan: tutor questions left today (GET /api/learn/plan) ── */
  async function loadPlan(){if(!token()){state.plan={plan:'guest',tutorLeft:0};return;}try{state.plan=await api('/api/learn/plan');}catch(e){state.plan=null;}}

  /* ── AI translation of English problem text into the learner's language: cached on the server for everyone; the
     original is one tap away and is shown whenever a translation is missing or loses the math ── */
  const trCache=new Map();
  async function aiTranslate(texts){
    const to=state.lang,keys=texts.map(t=>to+'\n'+t),need=[...new Set(texts.filter((t,i)=>t&&!trCache.has(keys[i])))];
    for(let i=0;i<need.length;i+=12){
      const part=need.slice(i,i+12);
      try{const r=await fetch(API+'/api/learn/translate',{method:'POST',headers:{'content-type':'application/json',...(token()?{Authorization:'Bearer '+token()}:{})},body:JSON.stringify({to,texts:part})});
        if(!r.ok)break;const j=await r.json();part.forEach((t,k)=>trCache.set(to+'\n'+t,j.texts?.[k]||null));}catch(e){break;}
    }
    return texts.map((t,i)=>trCache.get(keys[i])||null);
  }

  /* ── exam tracks: AP Physics 1 · 2 · C: Mechanics and JEE Main — original problems in each exam's style, graded at
     once (a choice, or a number within a tolerance), with hints, a worked solution, the AI tutor and a discussion link ── */
  async function loadTracks(){if(!state.tracks){const r=await fetch('practice/tracks.json');if(!r.ok)throw new Error('tracks');state.tracks=(await r.json()).tracks;}return state.tracks;}
  async function trackItems(key){
    state.trackData||={};
    if(!state.trackData[key]){const r=await fetch('practice/track/'+encodeURIComponent(key)+'.json');if(!r.ok)throw new Error('track');state.trackData[key]=(await r.json()).items.map(i=>({...i,kind:'track',track:key,u:i.unit,s:i.step}));}
    return state.trackData[key];
  }
  async function allTrackItems(){return (await Promise.all((await loadTracks()).map(t=>trackItems(t.key)))).flat();}
  const nameOf=o=>o?(state.lang==='ko'?o.ko||o.en:tx(o.en||'')):'';
  const sylName=(t,key)=>nameOf(t.syl.find(u=>u.key===key)?.name)||key;
  async function tracksHome(){
    state.mode='tracks';state.session=null;paintTabs();paintStats();tellUnit('');
    $('app').innerHTML=`<p>${tr('loading')}</p>`;
    let tracks;try{tracks=await loadTracks();}catch(e){failed(tracksHome);return;}
    const done=prefix=>Object.keys(saved.solved).filter(id=>id.startsWith(prefix)).length;
    /* the learner's own exams first (their region's school exam and olympiad), the rest folded away */
    const R=P.REGIONS[saved.profile?.region]||(state.lang==='ko'?P.REGIONS.kr:P.REGIONS.global),mine=new Set([...R.exam,...R.olympiad]);
    const card=t=>`<section class="area"><h2>${esc(nameOf(t.name))}</h2><p class="src">${esc(nameOf(t.blurb))}</p>
      ${t.syl.map(u=>{const d=done(t.key+'-'+u.key+'-');return `<button type="button" class="unit" data-track="${t.key}" data-syl="${u.key}"><span class="name">${esc(nameOf(u.name))}<small>${u.n} ${tr('problems')} · ${d} ${tr('progress')}</small></span><span class="bar"><i style="width:${Math.round(100*d/Math.max(1,u.n))}%"></i></span></button>`;}).join('')}
      <button type="button" class="unit mixed" data-track="${t.key}" data-syl=""><span class="name"><b>${tr('mixed')}</b><small>${t.n} ${tr('problems')} · ${done(t.key+'-')} ${tr('progress')}</small></span><span>→</span></button></section>`;
    const first=tracks.filter(t=>mine.has(t.key)),rest=tracks.filter(t=>!mine.has(t.key));
    $('app').innerHTML=`<p class="pick">${tr('trackPick')}</p>${first.length?`<h3 class="trackhead">${tr('myExams')} · ${esc(pickName(R.name))}</h3><div class="areas">${first.map(card).join('')}</div>`:''}
      ${rest.length?`<details class="alt otherexams"${first.length?'':' open'}><summary>${tr('otherExams')}</summary><div class="areas">${rest.map(card).join('')}</div></details>`:''}`;
    $('app').querySelectorAll('[data-track]').forEach(b=>b.onclick=()=>trackStart(b.dataset.track,b.dataset.syl));
    reportHeight();
  }
  async function trackStart(key,syl){
    state.mode='tracks';paintTabs();
    $('app').innerHTML=`<p>${tr('loading')}</p>`;
    let t,items;try{t=(await loadTracks()).find(x=>x.key===key);if(!t){tracksHome();return;}items=(await trackItems(key)).filter(i=>!syl||i.syl===syl);}catch(e){failed(()=>trackStart(key,syl));return;}
    if(!items.length){tracksHome();return;}
    const steps=[...new Set(items.map(i=>i.s))].sort((a,b)=>a-b),lk='track:'+key+'/'+(syl||'*');
    const own=ratingStep(saved.skills[items[0].u]?.rating??START),level=saved.level[lk]&&steps.includes(saved.level[lk])?saved.level[lk]:steps.reduce((b,x)=>Math.abs(x-own)<Math.abs(b-own)?x:b,steps[0]);
    state.session={mode:'track',track:key,syl,levelKey:lk,label:nameOf(t.name)+(syl?' · '+sylName(t,syl):''),items,steps,level,n:0,right:0,run:0,seen:new Set(),current:null,answered:false,xp:0};
    next();
  }
  /* a problem opened by its link (a search page, a discussion): that one first, then its unit */
  async function openItem(id){
    const key=id.split('-')[0];let items;
    try{items=await trackItems(key);}catch(e){todayHome();return;}
    const it=items.find(i=>i.id===id);if(!it){tracksHome();return;}
    await trackStart(key,it.syl);const s=state.session;if(!s)return;
    s.seen.clear();s.n=0;s.first=it;next();
  }
  /* "3.2e4", "3,2", "3.2×10^4", "3.2 x 10^4", "-1/2" → a number, or NaN */
  function parseNum(raw){
    let t=String(raw||'').trim().replace(/\s+/g,'').replace(/−/g,'-');
    if(/^-?\d+,\d+$/.test(t))t=t.replace(',','.');
    t=t.replace(/,/g,'');
    let m=/^(-?\d*\.?\d+)(?:[x×*·]10\^?\(?(-?\d+)\)?)$/i.exec(t);if(m)return Number(m[1])*10**Number(m[2]);
    m=/^(-?\d+)\/(\d+)$/.exec(t);if(m)return Number(m[1])/Number(m[2]);
    return /^-?(\d+\.?\d*|\.\d+)(e[+-]?\d+)?$/i.test(t)?Number(t):NaN;
  }
  const numOk=(v,a)=>a.tol>0?Math.abs(v-a.value)<=a.tol*Math.abs(a.value)+1e-12:Math.abs(v-a.value)<1e-9;
  const fmtNum=a=>`${a.value} ${a.unit||''}`.trim();
  function showTrack(item){
    const s=state.session;s.hints=0;s.answered=false;s.view=null;s.chat=[];
    const L='ABCDE';
    $('app').innerHTML=`<div class="session">
      ${sessionHead(s,item)}
      <div class="q" id="qtext">${textHtml(item.q)}</div><p class="src" id="trnote"></p>
      ${item.type==='mc'?`<div class="choices" role="group">${item.choices.map((c,i)=>`<button type="button" class="choice" data-i="${i}"><span class="no">${L[i]}</span><span class="ct">${esc(c)}</span></button>`).join('')}</div>`
        :`<form class="numrow" id="numf"><input id="num" inputmode="decimal" autocomplete="off" placeholder="${tr('numPh')}" aria-label="${tr('numPh')}"><span class="unitlbl">${esc(item.answer.unit||'')}</span><button type="submit" class="primary">${tr('check')}</button><span class="numerr" id="numerr"></span></form>`}
      <div id="hints"></div><div id="feedback"></div><div id="sol"></div><div id="tutor"></div><div id="disc"></div>
      <div class="foot"><span class="src">${esc(s.fixed?unitName(item.u):s.label)} · ${tr('byHasla')} · <a href="#" id="discuss">${tr('discuss')}</a></span>
        <span class="footbtns"><button type="button" id="hint">${tr('hint')} (0/${item.hints.length})</button><button type="button" id="ask">✦ ${tr('tutor')}</button><button type="button" id="skip">${tr('skip')}</button><button type="button" class="primary" id="next" hidden>${s.n>=SESSION||s.diag&&s.n>=s.diag.areas.length*2?tr('finish'):tr('next')}</button></span></div></div>`;
    typeset($('qtext'));typeset($('app').querySelector('.choices')||$('app'));
    $('quit').onclick=s.assignment?classHome:s.diag||s.fixed?todayHome:s.mode==='track'?tracksHome:home;
    $('skip').hidden=!!s.diag;
    if(item.type==='mc')$('app').querySelectorAll('.choice').forEach(b=>b.onclick=()=>trackAnswer(Number(b.dataset.i)));
    else $('numf').onsubmit=e=>{e.preventDefault();const v=parseNum($('num').value);if(!Number.isFinite(v)){$('numerr').textContent=tr('notNumber');return;}trackAnswer(v);};
    $('hint').onclick=()=>{if(s.hints>=item.hints.length)return;s.hints++;paintHints(item);$('hint').textContent=`${tr('hint')} (${s.hints}/${item.hints.length})`;if(s.hints>=item.hints.length)$('hint').disabled=true;reportHeight();};
    $('ask').onclick=()=>openTutor(item);
    $('skip').onclick=()=>{if(s.answered)return;record(item.id,'track',item.u,item.s,'skip');s.skipped=(s.skipped||0)+1;s.n--;s.extra=(s.extra||0)+1;if(s.extra>30){summary();return;}next();};
    $('next').onclick=next;
    $('discuss').onclick=e=>{e.preventDefault();discuss(item);};
    if(state.lang!=='en')localizeTrack(item);
    reportHeight();window.scrollTo?.(0,0);if(embedded)window.parent.postMessage({type:'hl-practice-top'},location.origin);
  }
  const viewOf=item=>state.session?.view&&!state.session.showOriginal?state.session.view:{q:item.q,choices:item.choices||[],hints:item.hints,sol:item.sol};
  function paintHints(item){const v=viewOf(item),s=state.session;$('hints').innerHTML=v.hints.slice(0,s.hints).map((h,i)=>`<p class="hintbox"><b>${tr('hint')} ${i+1}</b> ${esc(h)}</p>`).join('');typeset($('hints'));}
  function paintTexts(item){
    const v=viewOf(item),s=state.session;
    $('qtext').innerHTML=textHtml(v.q);typeset($('qtext'));
    $('app').querySelectorAll('.choice .ct').forEach((el,i)=>{el.textContent=v.choices[i]??'';typeset(el);});
    paintHints(item);if(s.answered)paintSolution(item);
    $('trnote').innerHTML=s.view?`${tr('aiTranslated')} · <a href="#" id="trtoggle">${s.showOriginal?tr('showTranslation'):tr('showOriginal')}</a>`:'';
    if($('trtoggle'))$('trtoggle').onclick=e=>{e.preventDefault();s.showOriginal=!s.showOriginal;paintTexts(item);};
    reportHeight();
  }
  async function localizeTrack(item){
    const s=state.session;$('trnote').textContent=tr('translating');
    const src=[item.q,...(item.choices||[]),...item.hints,item.sol],out=await aiTranslate(src);
    if(state.session!==s||s.current!==item)return;
    if(!out[0]){$('trnote').textContent='';return;}
    const nc=(item.choices||[]).length,nh=item.hints.length,pickT=(i)=>out[i]||src[i];
    s.view={q:pickT(0),choices:(item.choices||[]).map((c,i)=>pickT(1+i)),hints:item.hints.map((h,i)=>pickT(1+nc+i)),sol:pickT(1+nc+nh)};
    paintTexts(item);
  }
  function paintSolution(item){const v=viewOf(item);$('sol').innerHTML=`<section class="solution"><h3>${tr('solution')}</h3>${textHtml(v.sol)}</section>`;typeset($('sol'));}
  function trackAnswer(given){
    const s=state.session,item=s.current;if(s.answered)return;s.answered=true;
    const ok=item.type==='mc'?given===item.answer:numOk(given,item.answer);
    const result=ok?(s.hints?'solved':'right'):'wrong';
    if(item.type==='mc')$('app').querySelectorAll('.choice').forEach(b=>{b.disabled=true;const i=Number(b.dataset.i);if(i===item.answer)b.classList.add('right');else if(i===given)b.classList.add('wrong');});
    else{$('num').disabled=true;$('numf').querySelector('button').disabled=true;$('numf').classList.add(ok?'right':'wrong');}
    let note='';
    if(ok){
      s.right++;s.run++;const gain=Math.max(4,10+2*item.s-3*s.hints);s.xp+=gain;saved.xp+=gain;saved.solved[item.id]=item.u;delete saved.wrong[item.id];
      if(!s.fixed&&!s.diag&&s.run>=2){const up=s.steps.find(x=>x>s.level);if(up){s.level=up;note=' · '+tr('up')+' ↑';}s.run=0;}
    }else{
      s.run=0;saved.wrong[item.id]=Math.floor(Date.now()/1000);
      if(!s.fixed&&!s.diag){const down=[...s.steps].reverse().find(x=>x<s.level);if(down){s.level=down;note=' · '+tr('down');}}
    }
    if(s.levelKey)saved.level[s.levelKey]=s.level;
    record(item.id,s.diag?'diag':'track',item.u,item.s,result);if(s.diag)diagStep(s,ok);
    if(!saved.days.includes(today())){saved.days.push(today());saved.days=saved.days.slice(-400);}
    save();paintStats();
    const answerText=item.type==='mc'?'ABCDE'[item.answer]+'. '+(viewOf(item).choices[item.answer]||''):fmtNum(item.answer);
    $('feedback').innerHTML=`<p class="feedback ${ok?'ok':'bad'}">${ok?tr('right'):tr('wrong')+' '+esc(answerText)}${note}${ok&&s.hints?' · '+tr('withHints'):''}</p>`;
    typeset($('feedback'));if(!s.diag)paintSolution(item);
    $('next').hidden=false;$('skip').hidden=true;$('hint').hidden=true;$('next').focus();reportHeight();
  }
  function discuss(item){
    const link=`https://haslalab.org/?lang=${state.lang}#/learn/practice?item=${item.id}`;
    const title=`[${item.id}] `+String(item.q).replace(/\$[^$]*\$/g,'…').replace(/\s+/g,' ').slice(0,70);
    const write='/#/community/write/qna?'+new URLSearchParams({title,body:`${link}\n\n`}),list='/#/community/qna/1?'+new URLSearchParams({q:item.id,field:'title'});
    $('disc').innerHTML=`<div class="discuss"><a class="btnlink" href="${esc(list)}" target="_top">${tr('seeDiscuss')}</a><a class="btnlink primary" href="${esc(write)}" target="_top">${tr('newDiscuss')}</a></div>`;reportHeight();
  }

  /* ── the AI tutor beside the problem: a guiding step, never the answer before the learner has tried; free members get
     a few questions a day (community/src/learn-services.js) ── */
  function openTutor(item){
    const s=state.session;
    if(!token()){$('tutor').innerHTML=`<div class="tutor"><p class="src">${tr('tutorLogin')} <a href="/#/login" target="_top">${tr('login')}</a></p></div>`;reportHeight();return;}
    $('tutor').innerHTML=`<div class="tutor"><div class="tutorlog" id="tutorlog">${s.chat.map(chatHtml).join('')}</div>
      <form id="tutorf" class="tutorf"><textarea id="tutorq" rows="2" maxlength="1500" placeholder="${tr('tutorPh')}"></textarea><button type="submit" class="primary">${tr('tutorSend')}</button></form>
      <p class="src" id="tutorleft">${leftText()}</p></div>`;
    typeset($('tutorlog'));
    $('tutorf').onsubmit=async e=>{
      e.preventDefault();const q=$('tutorq').value.trim();if(!q)return;
      const btn=$('tutorf').querySelector('button');btn.disabled=true;$('tutorleft').textContent=tr('thinking');
      const v=viewOf(item);
      try{
        const r=await fetch(API+'/api/learn/tutor',{method:'POST',headers:{'content-type':'application/json',Authorization:'Bearer '+token()},
          body:JSON.stringify({problem:v.q,choices:v.choices,question:q,lang:state.lang,solved:s.answered,hintsSeen:s.hints,history:s.chat})});
        const j=await r.json().catch(()=>({}));
        if(!r.ok){$('tutorleft').textContent=j.error==='tutor_limit'?tr('tutorLimit'):tr('tutorFail');if(j.error==='tutor_limit'&&state.plan)state.plan.tutorLeft=0;btn.disabled=false;return;}
        s.chat.push({role:'user',content:q},{role:'assistant',content:j.answer});if(state.plan)state.plan.tutorLeft=j.tutorLeft;
        $('tutorlog').innerHTML=s.chat.map(chatHtml).join('');typeset($('tutorlog'));$('tutorq').value='';$('tutorleft').textContent=leftText();
      }catch(err){$('tutorleft').textContent=tr('tutorFail');}
      btn.disabled=false;reportHeight();
    };
    reportHeight();$('tutorq').focus();
  }
  const chatHtml=m=>`<div class="msg ${m.role}">${m.role==='assistant'?'<b>✦</b> ':''}${textHtml(m.content)}</div>`;
  const leftText=()=>state.plan&&Number.isFinite(state.plan.tutorLeft)?`${tr('tutorLeft')}: ${state.plan.tutorLeft} · ${tr('aiNote')}`:tr('aiNote');

  /* ── placement test: two questions per area — the first at step 4, the second harder or easier after it — and each
     area's units start at the step found (only units with no answers yet) ── */
  const DIAG_AREAS=['mechanics','waves','em','thermal','optics','modern'];
  async function diagStart(){
    $('app').innerHTML=`<p>${tr('loading')}</p>`;
    let items;try{items=await startPool();}catch(e){failed(diagStart);return;}
    const byArea={};for(const it of items)(byArea[it.u.split('/')[0]]||=[]).push(it);
    const areas=DIAG_AREAS.filter(a=>(byArea[a]||[]).length>=2);
    state.session={mode:'diag',fixed:true,diag:{areas,byArea,i:0,first:null,res:{}},items,steps:[],level:0,n:0,right:0,run:0,seen:new Set(),current:null,answered:false,xp:0};
    next();
  }
  function pickDiag(s){
    const d=s.diag;if(d.i>=d.areas.length)return null;
    const target=d.first===null?4:d.first?6:3,pool=d.byArea[d.areas[d.i]].filter(i=>!s.seen.has(i.id));
    return pool.sort((a,b)=>Math.abs(a.s-target)-Math.abs(b.s-target)+(Math.random()-.5)*.6)[0]||null;
  }
  function diagStep(s,ok){
    const d=s.diag;
    if(d.first===null){d.first=ok;return;}
    d.res[d.areas[d.i]]=d.first?(ok?7:5):(ok?4:2);d.first=null;d.i++;
  }
  function diagSummary(s){
    const d=s.diag;saved.diagAt=Math.floor(Date.now()/1000);
    for(const [area,step] of Object.entries(d.res)){const a=P.AREAS.find(x=>x.key===area);if(!a)continue;
      for(const sub of a.subtopics)record('diag-'+area,'diag',area+'/'+sub.key,step,'place');}
    save();
    $('app').innerHTML=`<div class="session summary"><p class="eyebrow">${tr('diagTitle')}</p><p class="big">${s.right}${tr('of')}${s.n}</p><p>${tr('diagDone')}</p>
      <table class="diagres">${Object.entries(d.res).map(([a,st])=>`<tr><td>${esc(areaName(P.AREAS.find(x=>x.key===a)))}</td><td>${tr('step')} ${st}</td><td><span class="lv lv${levelOf(st)}">${tr(LEVELS[levelOf(st)])}</span></td></tr>`).join('')}</table>
      <div class="actions"><button type="button" class="primary" id="units">${tr('startToday')}</button></div></div>`;
    $('units').onclick=todayHome;reportHeight();
  }
  /* ── classes: a teacher makes a class, students join with its six-letter code, the teacher sets exam-track problems and
     sees each student's units and assignments (community/src/learn-services.js). Free: one class of 30. ── */
  async function classApi(path,method='GET',body){
    const r=await fetch(API+'/api/learn/classes'+path,{method,headers:{Authorization:'Bearer '+token(),...(body?{'content-type':'application/json'}:{})},body:body?JSON.stringify(body):undefined});
    const j=await r.json().catch(()=>({}));if(!r.ok)throw Object.assign(new Error(j.error||'api'),{code:j.error});return j;
  }
  const classErr=e=>copy.en['cl_'+e.code]?tr('cl_'+e.code):tr('failed');
  const day=sec=>sec?new Date(sec*1000).toLocaleDateString(state.lang):'—';
  async function classHome(){
    state.mode='class';state.session=null;paintTabs();paintStats();tellUnit('');
    if(!token()){$('app').innerHTML=`<p class="pick">${tr('classIntro')}</p><p><a class="btnlink primary" href="/#/login" target="_top">${tr('login')}</a></p>`;reportHeight();return;}
    $('app').innerHTML=`<p>${tr('loading')}</p>`;
    let d;try{d=await classApi('');}catch(e){failed(classHome);return;}
    const byClass=new Map(d.joined.map(c=>[c.id,c]));
    $('app').innerHTML=`<p class="pick">${tr('classIntro')}</p><div class="areas">
      <section class="area"><h2>${tr('myAssignments')}</h2>
        ${d.assignments.length?d.assignments.map(a=>`<button type="button" class="unit" data-assign="${a.id}"><span class="name"><b>${esc(a.title)}</b><small>${esc(byClass.get(a.class_id)?.name||'')} · ${a.done}/${a.items.length}${a.due_at?' · '+tr('due')+' '+day(a.due_at):''}</small></span><span class="bar"><i style="width:${Math.round(100*a.done/Math.max(1,a.items.length))}%"></i></span></button>`).join(''):`<p class="src">${tr('noAssignments')}</p>`}
        <form id="joinf" class="numrow"><input id="joincode" maxlength="6" autocomplete="off" placeholder="${tr('classCode')}" aria-label="${tr('classCode')}"><button type="submit" class="primary">${tr('join')}</button><span class="numerr" id="joinerr"></span></form>
        ${d.joined.length?`<p class="src">${d.joined.map(c=>`${esc(c.name)}${c.teacher?' · '+esc(c.teacher):''} <a href="#" data-leave="${c.id}">${tr('leave')}</a>`).join('<br>')}</p>`:''}
      </section>
      <section class="area"><h2>${tr('teach')}</h2>
        ${d.teaching.map(c=>`<button type="button" class="unit" data-class="${c.id}"><span class="name"><b>${esc(c.name)}</b><small>${tr('classCode')} ${esc(c.code)} · ${c.n} ${tr('students')}</small></span><span>→</span></button>`).join('')}
        <form id="newclass" class="numrow"><input id="classname" maxlength="60" autocomplete="off" placeholder="${tr('className')}" aria-label="${tr('className')}"><button type="submit">${tr('newClass')}</button><span class="numerr" id="newerr"></span></form>
        <p class="src">${tr('classFree')}</p>
      </section></div>`;
    $('joinf').onsubmit=async e=>{e.preventDefault();try{await classApi('/join','POST',{code:$('joincode').value});classHome();}catch(err){$('joinerr').textContent=classErr(err);}};
    $('newclass').onsubmit=async e=>{e.preventDefault();try{const c=await classApi('','POST',{name:$('classname').value});classView(c.id);}catch(err){$('newerr').textContent=classErr(err);}};
    $('app').querySelectorAll('[data-leave]').forEach(a=>a.onclick=async e=>{e.preventDefault();if(!confirm(tr('leaveConfirm')))return;try{await classApi('/'+a.dataset.leave+'/leave','POST',{});}catch(err){}classHome();});
    $('app').querySelectorAll('[data-class]').forEach(b=>b.onclick=()=>classView(Number(b.dataset.class)));
    $('app').querySelectorAll('[data-assign]').forEach(b=>b.onclick=()=>{const a=d.assignments.find(x=>x.id===Number(b.dataset.assign));assignmentStart(a);});
    reportHeight();
  }
  async function assignmentStart(a){
    $('app').innerHTML=`<p>${tr('loading')}</p>`;
    let pool;try{pool=await allTrackItems();}catch(e){failed(()=>assignmentStart(a));return;}
    const byId=new Map(pool.map(i=>[i.id,i])),items=a.items.map(id=>byId.get(id)).filter(Boolean);
    if(!items.length){classHome();return;}
    state.session={unit:'assignment',fixed:true,assignment:true,label:a.title,items,steps:[],level:0,n:0,right:0,run:0,seen:new Set(),current:null,answered:false,xp:0};
    next();
  }
  async function classView(id){
    state.mode='class';paintTabs();
    $('app').innerHTML=`<p>${tr('loading')}</p>`;
    let c,tracks;try{[c,tracks]=await Promise.all([classApi('/'+id),loadTracks()]);}catch(e){failed(()=>classView(id));return;}
    $('app').innerHTML=`<div class="session"><div class="shead"><button type="button" class="back" id="quit">${tr('quit')}</button><span class="unitname">${esc(c.name)}</span><span class="lvl">${tr('classCode')} ${esc(c.code)}</span></div>
      <p class="src">${tr('shareCode')}</p>
      <div class="skills"><table><thead><tr><th>${tr('student')}</th><th>${tr('answered')}</th><th>${tr('lastActive')}</th>${c.assignments.map(a=>`<th>${esc(a.title)}</th>`).join('')}<th></th></tr></thead><tbody>
      ${c.members.map(m=>`<tr><td>${esc(m.nickname||'#'+m.id)}<br><small>${m.units.sort((x,y)=>x.rating-y.rating).slice(0,2).map(u=>esc(unitName(u.unit))+' '+tr(LEVELS[levelOf(ratingStep(u.rating))])).join(' · ')}</small></td><td>${m.answered}</td><td>${day(m.lastAt)}</td>${c.assignments.map(a=>`<td>${m.assignments[a.id]||0}/${a.items.length}</td>`).join('')}<td><a href="#" data-remove="${m.id}">${tr('remove')}</a></td></tr>`).join('')||`<tr><td colspan="${4+c.assignments.length}">${tr('noStudents')}</td></tr>`}
      </tbody></table></div>
      <h3>${tr('newAssignment')}</h3>
      <form id="assignf" class="numrow"><select id="asTrack">${tracks.map(t=>`<optgroup label="${esc(nameOf(t.name))}">${t.syl.map(u=>`<option value="${t.key}|${u.key}">${esc(nameOf(t.name))} · ${esc(nameOf(u.name))}</option>`).join('')}</optgroup>`).join('')}</select>
        <select id="asN"><option value="5">5</option><option value="10" selected>10</option><option value="0">${tr('allOf')}</option></select>
        <input id="asDue" type="date" aria-label="${tr('due')}"><button type="submit" class="primary">${tr('assign')}</button><span class="numerr" id="aserr"></span></form>
      <div class="actions"><button type="button" id="closeClass">${tr('closeClass')}</button></div></div>`;
    $('quit').onclick=classHome;
    $('assignf').onsubmit=async e=>{
      e.preventDefault();const [tk,syl]=$('asTrack').value.split('|'),n=Number($('asN').value);
      try{const t=tracks.find(x=>x.key===tk),items=(await trackItems(tk)).filter(i=>i.syl===syl).sort((a,b)=>a.s-b.s);
        const ids=(n?items.slice(0,n):items).map(i=>i.id).slice(0,40),due=$('asDue').value?Math.floor(new Date($('asDue').value+'T23:59').getTime()/1000):null;
        await classApi('/'+id+'/assignments','POST',{title:nameOf(t.name)+' · '+nameOf(t.syl.find(u=>u.key===syl).name),items:ids,due_at:due});classView(id);}
      catch(err){$('aserr').textContent=classErr(err);}
    };
    $('app').querySelectorAll('[data-remove]').forEach(a=>a.onclick=async e=>{e.preventDefault();if(!confirm(tr('removeConfirm')))return;try{await classApi('/'+id+'/members/'+a.dataset.remove,'DELETE');}catch(err){}classView(id);});
    $('closeClass').onclick=async()=>{if(!confirm(tr('closeConfirm')))return;try{await classApi('/'+id,'DELETE');}catch(err){}classHome();};
    reportHeight();
  }
  /* ── first visit (and right after sign-up): who are you? Like a language app's first questions — region, school level,
     goal, olympiad experience, daily goal — then every unit starts at the step this suggests (learn-path.js startStep) and
     the first problems come from the region's exams (startExams): Korea the CSAT, India JEE, the US F=ma and the USAPhO,
     elsewhere AP Physics. The placement test can then refine it. ── */
  const pickName=o=>o?(state.lang==='ko'?o.ko:o.en):'';
  function startHome(edit){
    state.mode='start';state.session=null;paintTabs();paintStats();tellUnit('');
    const old=saved.profile||{},tz=(()=>{try{return Intl.DateTimeFormat().resolvedOptions().timeZone;}catch(e){return '';}})();
    const a={region:old.region||P.guessRegion(state.lang,tz),level:old.level||'',goal:old.goal||'',oly:old.oly??0,daily:old.daily||10};
    const steps=['region','level','goal','oly','daily'];let i=0;
    const q=()=>{
      const key=steps[i];if(key==='oly'&&a.goal!=='olympiad'){i+=dir;return q();}
      const R=P.REGIONS[a.region]||P.REGIONS.global;
      const opts={
        region:Object.entries(P.REGIONS).map(([k,r])=>[k,pickName(r.name),k==='kr'?tr('obKr'):k==='in'?tr('obIn'):k==='us'?tr('obUs'):tr('obGlobal')]),
        level:P.LEVELS.map(([k,n])=>[k,pickName(n),'']),
        goal:[['school',tr('goSchool'),''],['exam',tr('goExam'),pickName(R.examName)],['olympiad',tr('goOly'),pickName(R.olyName)],['curious',tr('goCurious'),'']],
        oly:[[0,tr('oly0'),''],[1,tr('oly1'),''],[2,tr('oly2'),'']],
        daily:[[5,'5 '+tr('perDay'),tr('daily5')],[10,'10 '+tr('perDay'),tr('daily10')],[20,'20 '+tr('perDay'),tr('daily20')]]
      }[key];
      $('app').innerHTML=`<div class="session onboard"><div class="shead">${i?`<button type="button" class="back" id="obBack">← ${tr('back')}</button>`:edit?`<button type="button" class="back" id="obBack">${tr('quit')}</button>`:''}<span class="progress" aria-hidden="true"><i style="width:${Math.round(100*i/steps.length)}%"></i></span></div>
        <h2>${tr('ob_'+key)}</h2><div class="obopts">${opts.map(([v,label,note])=>`<button type="button" class="unit${String(a[key])===String(v)?' cur':''}" data-v="${v}"><span class="name"><b>${esc(label)}</b>${note?`<small>${esc(note)}</small>`:''}</span></button>`).join('')}</div></div>`;
      $('app').querySelectorAll('[data-v]').forEach(b=>b.onclick=()=>{a[key]=key==='oly'||key==='daily'?Number(b.dataset.v):b.dataset.v;dir=1;i++;if(i>=steps.length)finish();else q();});
      if($('obBack'))$('obBack').onclick=()=>{if(!i){todayHome();return;}dir=-1;i--;q();};
      reportHeight();
    };
    let dir=1;
    const finish=()=>{
      const profile={...a,at:Math.floor(Date.now()/1000)},step=P.startStep(profile);
      saved.profile=profile;
      /* every unit with no answers yet starts at that step (the answers that follow move each one on its own) */
      for(const area of P.AREAS)for(const sub of area.subtopics){const unit=area.key+'/'+sub.key,k=saved.skills[unit];
        if(!k||!k.n)record('start-'+area.key,'diag',unit,step,'place');}
      save();scheduleSync();
      const exams=P.startExams(profile).map(k=>k==='calc'?tr('calcName'):(state.tracks||[]).find(t=>t.key===k)?.name.en||k.toUpperCase());
      $('app').innerHTML=`<div class="session summary onboard"><p class="eyebrow">${tr('obDone')}</p><p class="big">${tr('step')} ${step}</p>
        <p>${tr(LEVELS[levelOf(step)])} · ${esc(exams.join(' · '))}</p><p class="src">${tr('obNext')}</p>
        <div class="actions"><button type="button" class="primary" id="obToday">${tr('startToday')}</button><button type="button" id="obDiag">${tr('diagStart')}</button></div></div>`;
      $('obToday').onclick=todayHome;$('obDiag').onclick=diagStart;reportHeight();
    };
    loadTracks().catch(()=>{}).finally(q);
  }
  /* the problems a learner starts on: their exams, as graded items */
  async function startPool(){
    const keys=P.startExams(saved.profile||{region:state.lang==='ko'?'kr':'global'});
    const parts=await Promise.all(keys.map(k=>k==='calc'?allExamItems():trackItems(k).catch(()=>[])));
    const items=parts.flat();
    return items.length?items:allTrackItems();
  }
  const MODES={start:startHome,today:todayHome,tracks:tracksHome,exam:home,bank:bankHome,contest:contestHome,class:classHome};

  function applyTheme(){const t=params.get('theme'),dark=t==='dark'||(t!=='light'&&matchMedia('(prefers-color-scheme: dark)').matches);document.documentElement.dataset.theme=dark?'dark':'light';}
  function translate(){document.documentElement.lang=state.lang;document.querySelectorAll('[data-i18n]').forEach(el=>{el.textContent=tr(el.dataset.i18n);});$('note').textContent=tr('note');document.title=tr('title')+' · HaslaLab';}
  window.addEventListener('message',event=>{
    if(!embedded||event.origin!==location.origin||event.source!==window.parent||event.data?.type!=='hl-practice-settings')return;
    if(['light','dark'].includes(event.data.theme))document.documentElement.dataset.theme=event.data.theme;
    if(LANGS.includes(event.data.lang)&&event.data.lang!==state.lang){state.lang=event.data.lang;translate();paintStats();paintTabs();if(!state.session)(MODES[state.mode]||todayHome)();}
  });
  addEventListener('keydown',e=>{
    const s=state.session;if(!s||s.mode==='bank'||/^(INPUT|TEXTAREA)$/.test(document.activeElement?.tagName||''))return;
    if(s.current?.kind==='track'){if(!s.answered&&s.current.type==='mc'&&/^[1-5a-eA-E]$/.test(e.key)){const i='abcde'.indexOf(e.key.toLowerCase());const n=i>=0?i:Number(e.key)-1;if(n<s.current.choices.length)trackAnswer(n);}else if(s.answered&&e.key==='Enter'&&document.activeElement?.id!=='next'){e.preventDefault();$('next')?.click();}return;}
    if(!s.answered&&/^[1-5]$/.test(e.key))answer(Number(e.key));
    else if(s.answered&&e.key==='Enter'&&document.activeElement?.id!=='next'){e.preventDefault();$('next')?.click();}
  });
  if(typeof ResizeObserver==='function')new ResizeObserver(reportHeight).observe(document.body);
  document.documentElement.classList.toggle('embedded',embedded);
  applyTheme();translate();
  const boot=()=>{pull();loadPlan();const unit=params.get('unit'),mode=params.get('mode'),item=params.get('item'),track=params.get('track');state.mode='exam';paintTabs();
    if(item&&/^[a-z0-9]+-[a-z0-9-]{1,40}$/.test(item))openItem(item);
    else if(mode==='bank')bankHome();else if(mode==='contest')contestHome();else if(mode==='tracks'||track)track&&/^[a-z0-9]{2,8}$/.test(track)?trackStart(track,params.get('syl')||''):tracksHome();
    else if(mode==='diag')diagStart();else if(mode==='start')startHome(!!saved.profile);else if(mode==='class')classHome();else if(unit&&P.SUBTOPICS.has(unit))start(unit);else if(mode==='exam')home();else todayHome();};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();
