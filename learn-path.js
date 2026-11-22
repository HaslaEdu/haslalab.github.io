/* HaslaLab learning path: one topic taxonomy and one difficulty scale for every physics problem,
   from a middle-school first step to the national team. The browser reads window.HL_LEARN_PATH;
   Node tools (the problem bank's reclassification) require() the same file. */
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.HL_LEARN_PATH=api;
})(typeof globalThis==='object'?globalThis:this,function(){
  'use strict';

  /* Ten steps in five stages. A step is the difficulty of a problem and the level a learner works at. */
  const STAGES=[
    {key:'intro',steps:[1,2],name:{ko:'입문',en:'First steps'},
      who:{ko:'중학생 · 물리를 처음 배우는 학생',en:'Middle school, or new to physics'},
      goal:{ko:'힘, 에너지, 전기, 빛을 말과 그림으로 설명하고 간단한 식을 세웁니다.',en:'Explain force, energy, electricity and light in words and pictures, and set up simple equations.'},
      sources:{ko:'중학 과학 · 통합과학 · KPhO 중등부 쉬운 문제',en:'Middle-school science · KPhO junior, easier problems'}},
    {key:'basic',steps:[3,4],name:{ko:'기초',en:'Foundations'},
      who:{ko:'고1–고2 · 고등학교 물리를 배우는 학생',en:'Grades 10–11, first physics course'},
      goal:{ko:'뉴턴 법칙, 보존 법칙, 회로, 파동 문제를 계산해서 답을 냅니다.',en:'Work out numerical answers on Newton’s laws, conservation laws, circuits and waves.'},
      sources:{ko:'AP Physics 1 · 한국 시험 계산 문제',en:'AP Physics 1 · calculation problems from Korean exams'}},
    {key:'advanced',steps:[5,6],name:{ko:'심화',en:'Advanced'},
      who:{ko:'AP Physics 2 · C, JEE Main, 올림피아드 1차 준비',en:'AP Physics 2 and C, JEE Main, first olympiad rounds'},
      goal:{ko:'여러 개념을 엮고, 미적분과 근사를 처음으로 씁니다.',en:'Combine several ideas and start using calculus and approximations.'},
      sources:{ko:'AP Physics C · JEE Main · F=ma · KPhO 1차',en:'AP Physics C · JEE Main · F=ma · KPhO first round'}},
    {key:'olympiad',steps:[7,8],name:{ko:'올림피아드',en:'Olympiad'},
      who:{ko:'KPhO 고등부 · 국가대표 선발 2차 준비',en:'KPhO senior and national selection'},
      goal:{ko:'대학 일반물리 수준으로 상황을 모델링하고, 실험 데이터를 다루고, 긴 서술형 풀이를 씁니다.',en:'Model a situation at first-year university level, handle experimental data and write long solutions.'},
      sources:{ko:'KPhO · 국가대표 선발 · 각국 국내 대회',en:'KPhO · national selection · other national olympiads'}},
    {key:'national',steps:[9,10],name:{ko:'국가대표',en:'National team'},
      who:{ko:'APhO · IPhO 준비',en:'APhO and IPhO preparation'},
      goal:{ko:'국제 대회 이론 · 실험 문제를 시험 시간 안에 풉니다.',en:'Solve international theory and experimental problems within the exam time.'},
      sources:{ko:'APhO · IPhO · EuPhO',en:'APhO · IPhO · EuPhO'}}
  ];
  const stageOf=step=>STAGES.find(stage=>step>=stage.steps[0]&&step<=stage.steps[1])||null;

  /* Areas and subtopics. `bank` is the problem bank's subject (BANK_SUBJECTS) used for search filters;
     `kw` are Korean/English phrases that identify the subtopic in an existing label. */
  const S=(key,ko,en,from,kw,bank)=>({key,name:{ko,en},from,kw,...(bank?{bank}:{})});
  const AREAS=[
    {key:'mechanics',bank:'classical_mechanics',name:{ko:'역학',en:'Mechanics'},subtopics:[
      S('kinematics','운동의 기술','Kinematics',1,['등가속도','등속도','속도와 가속도','위치-시간','운동의 분류','운동의 종류','여러 가지 운동','운동의 분석','포물선','던진 물체','평면에서','평면상의','2차원 운동','kinematic','projectile']),
      S('newton','뉴턴 법칙과 힘','Newton’s laws and forces',1,['뉴턴','운동 법칙','운동의 법칙','작용 반작용','힘의 합성','힘의 분해','마찰','빗면','구속 운동','물체에 작용하는 힘','newton']),
      S('energy','일과 에너지','Work and energy',1,['역학적 에너지','일-운동','일·운동','일․운동','일ㆍ운동','일 • 운동','일과 에너지','일과 운동 에너지','일과 역학적','에너지 보존','줄의 실험','work-energy']),
      S('momentum','운동량과 충돌','Momentum and collisions',3,['운동량','충격량','충돌','충격을','momentum','collision']),
      S('circular','원운동','Circular motion',3,['원운동','구심력','circular']),
      S('gravitation','중력과 행성 운동','Gravitation and orbits',3,['케플러','중력 법칙','행성','탈출 속','중력장','블랙홀','kepler','orbit']),
      S('statics','평형과 돌림힘','Equilibrium and torque',3,['평형','돌림힘','무게 중심','안정성','torque','equilibrium']),
      S('noninertial','관성력과 비관성계','Non-inertial frames',5,['관성력','가속 좌표계','비관성','엘리베이터','inertial force']),
      S('rigid_body','강체의 회전','Rigid-body rotation',6,['강체','회전 운동','관성 모멘트','각운동량','rolling','angular momentum']),
      S('fluids','유체','Fluids',5,['유체','부력','압력과 유체','베르누이','fluid','buoyancy'])]},
    {key:'waves',bank:'oscillations_waves',name:{ko:'진동과 파동',en:'Oscillations and waves'},subtopics:[
      S('shm','단진동과 진자','Simple harmonic motion',3,['단진동','단진자','진자','용수철','harmonic','pendulum']),
      S('wave_motion','파동의 진행','Wave propagation',2,['파동의 진행','파동의 요소','파동의 표현','파동의 기술','파동의 속력','파동의 이용','물결파','wave speed']),
      S('sound','소리와 도플러 효과','Sound and the Doppler effect',2,['소리','도플러','음파','doppler','sound']),
      S('superposition','중첩과 정상파','Superposition and standing waves',4,['파동의 중첩','정상파','공명','standing wave','resonance'])]},
    {key:'optics',bank:'optics',name:{ko:'광학',en:'Optics'},subtopics:[
      S('refraction','반사 · 굴절 · 전반사','Reflection and refraction',2,['굴절','전반사','반사','광섬유','refraction','total internal']),
      S('lenses','렌즈와 거울','Lenses and mirrors',2,['렌즈','거울','광학 현미경','lens','mirror']),
      S('interference','간섭과 회절','Interference and diffraction',4,['간섭','회절','이중 슬릿','슬릿','interference','diffraction']),
      S('polarization','편광','Polarisation',6,['편광','polariz','polaris'])]},
    {key:'em',bank:'electromagnetism',name:{ko:'전자기',en:'Electricity and magnetism'},subtopics:[
      S('electrostatics','전하와 전기장','Charge and electric field',2,['전기력','전기장','쿨롱','점전하','전하와','정전기','전기력선','coulomb','electric field']),
      S('capacitors','전위와 축전기','Potential and capacitors',4,['축전기','전위','전기 용량','유전체','capacitor']),
      S('dc_circuits','직류 회로','DC circuits',2,['저항','직류 회로','옴의 법칙','소비 전력','전력','회로 과도','resistor','circuit']),
      S('magnetic_field','전류와 자기장','Currents and magnetic fields',3,['전류에 의한 자기장','직선 전류','원형 전류','솔레노이드','자기장','오른나사','magnetic field']),
      S('lorentz','자기력과 하전 입자','Magnetic force on charges',5,['로렌츠','자기력','하전 입자','사이클로트론','lorentz']),
      S('induction','전자기 유도','Electromagnetic induction',3,['전자기 유도','유도 기전력','유도 전류','상호유도','상호 유도','변압기','자체 유도','induction','transformer']),
      S('ac_circuits','교류 회로','AC circuits',6,['교류','RLC','코일과 축전기','공명 진동수','ac circuit']),
      S('em_waves','전자기파','Electromagnetic waves',2,['전자기파','electromagnetic wave']),
      S('magnetic_materials','자성체','Magnetic materials',3,['자성체','물질의 자성','자성','강자성','상자성','반자성','magnetic material'])]},
    {key:'thermal',bank:'thermodynamics',name:{ko:'열과 통계',en:'Heat and statistics'},subtopics:[
      S('ideal_gas','이상 기체','Ideal gases',3,['이상 기체','기체의 상태','상태방정식','압력-부피','ideal gas']),
      S('first_law','열역학 법칙','Laws of thermodynamics',3,['열역학 제1법칙','열역학 제 1법칙','열역학 법칙','열역학 과정','일과 열','열과 일','열의 일당량','first law']),
      S('heat_engines','열기관과 효율','Heat engines',4,['열기관','열효율','카르노','heat engine','carnot']),
      S('heat_transfer','열전달','Heat transfer',5,['열전도','복사','대류','열전달','heat transfer','conduction']),
      S('kinetic_theory','분자 운동과 통계','Kinetic theory and statistics',7,['분자 운동','엔트로피','볼츠만','통계','kinetic theory','entropy','boltzmann'],'statistical_mechanics')]},
    {key:'modern',bank:'quantum_mechanics',name:{ko:'현대물리',en:'Modern physics'},subtopics:[
      S('special_relativity','특수 상대성 이론','Special relativity',3,['특수 상대성','상대성 이론','질량-에너지','질량 에너지','special relativity'],'special_relativity'),
      S('general_relativity','등가 원리와 일반 상대성','Equivalence principle and general relativity',4,['일반 상대성','등가원리','등가 원리','등가중력','중력 렌즈','general relativity'],'general_relativity'),
      S('photon','광전 효과와 빛의 이중성','Photons and the photoelectric effect',3,['광전','빛의 이중성','빛의 입자성','빛과 물질의 이중성','광자','photoelectric','photon']),
      S('matter_waves','물질파와 불확정성','Matter waves and uncertainty',4,['물질파','물질의 파동성','물질의 이중성','전자의 파동성','불확정성','전자 현미경','de broglie','uncertainty']),
      S('atoms','원자와 에너지 준위','Atoms and energy levels',3,['보어','수소 원자','에너지 준위','선 스펙트럼','스펙트럼','원자 모형','전자의 전이','bohr','energy level']),
      S('nuclear','핵반응','Nuclear reactions',3,['핵반응','핵분열','핵융합','질량 결손','방사성','nuclear']),
      S('solids','고체와 반도체','Solids and semiconductors',3,['에너지띠','다이오드','트랜지스터','반도체','p-n','n-p-n','발광 다이오드','고체의','절연체','semiconductor','diode','transistor'])]},
    {key:'experiment',bank:null,name:{ko:'실험',en:'Experiment'},subtopics:[
      S('uncertainty','측정과 불확도','Measurement and uncertainty',3,['불확도','불확실성','오차','uncertainty']),
      S('graphs','그래프와 선형화','Graphs and linearisation',4,['회귀','선형화','그래프 해석','자료 해석','regression','linearis','lineariz']),
      S('design','실험 설계','Experimental design',5,['탐구 설계','실험 설계','정상상태 측정','experimental design'])]},
    {key:'math',bank:'mathematical_methods',name:{ko:'수학 도구',en:'Mathematical tools'},subtopics:[
      S('vectors','벡터와 좌표','Vectors and coordinates',3,['벡터','vector']),
      S('calculus','미적분','Calculus',5,['미분','적분','calculus']),
      S('approximation','근사와 차원 분석','Approximation and dimensional analysis',6,['근사','차원 분석','approximation','dimensional']),
      S('ode','미분방정식','Differential equations',7,['미분방정식','differential equation'])]}
  ];
  const SUBTOPICS=new Map();
  for(const area of AREAS)for(const sub of area.subtopics)SUBTOPICS.set(area.key+'/'+sub.key,{area,sub});

  /* PhysLeague's top-level labels; used only when the subtopic text says nothing usable. */
  const LEAGUE_AREAS={'역학':'mechanics','전자기':'em','광학':'optics','열물리':'thermal','현대물리':'modern','실험':'experiment'};
  /* Words that are never evidence: PDF extraction noise and the CSAT inquiry-skill suffixes. */
  const NOISE=/(\{출제의도\}|\{오답풀이\}|\[ *\]|문항 \d+ 개념|\(검수 필요\)|탐구 설계 및 수행하기|문제 인식 및 가설 설정하기|자료 분석 및 해석하기|결론 도출 및 평가하기|를? ?이해한다\.?|이해하기|적용하기)/g;

  /* Finds the subtopic a free-text label describes. Returns null when nothing matches, so the
     caller can send the problem to review (or to the AI classifier) instead of guessing. */
  function classifyLabel(label,{area}={}){
    const text=String(label||'').replace(NOISE,' ').toLowerCase();
    if(!/[가-힣a-z]{2}/.test(text))return null;
    let best=null;
    for(const a of AREAS){
      if(area&&a.key!==area&&!matchesStrongly(a,text))continue;
      for(const sub of a.subtopics)for(const word of sub.kw){
        const w=word.toLowerCase();
        if(text.includes(w)&&(!best||w.length>best.length))best={area:a.key,subtopic:sub.key,length:w.length,matched:word};
      }
    }
    return best&&{area:best.area,subtopic:best.subtopic,matched:best.matched};
  }
  /* PhysLeague filed semiconductors and magnetism under 역학; a specific phrase from another area wins. */
  function matchesStrongly(area,text){return area.subtopics.some(sub=>sub.kw.some(word=>word.length>=3&&text.includes(word.toLowerCase())));}

  function classifyLeagueTopic(topic,subtopic){
    const found=classifyLabel(subtopic,{area:LEAGUE_AREAS[topic]});
    if(found)return{...found,confidence:'keyword'};
    return LEAGUE_AREAS[topic]?{area:LEAGUE_AREAS[topic],subtopic:null,confidence:'area_only'}:null;
  }

  /* PhysLeague's CSAT difficulty runs 2 (easiest) to 24 (hardest, from wrong-answer rates).
     Korean school exams span the 기초 and 심화 stages: steps 2 to 6. */
  function stepFromCsat(difficulty){
    const d=Number(difficulty);
    if(!Number.isFinite(d))return null;
    return Math.max(2,Math.min(6,2+Math.round(4*(Math.max(2,Math.min(24,d))-2)/22)));
  }
  /* Problem-bank stars (rubric-v1, 1–5) describe olympiad problems: steps 5 to 9.
     Step 10 is reserved for problems an editor marks as the hardest international ones. */
  function stepFromStars(stars){
    const s=Math.round(Number(stars));
    return s>=1&&s<=5?s+4:null;
  }

  function bankSubjectOf(areaKey,subtopicKey){
    const area=AREAS.find(item=>item.key===areaKey);
    return area?.subtopics.find(sub=>sub.key===subtopicKey)?.bank||area?.bank||null;
  }

  /* ── who the learner is → where they start. Each region studies for its own exams: Korea for AP-level physics (with the
     Korean exams' calculation problems, 'calc') and KPhO, India
     for JEE, the United States for F=ma and the USAPhO, everyone else for AP Physics. The onboarding asks for the
     region (guessed from the language and time zone), the school level, the goal and, for olympiad learners, how far they
     have got; startStep() turns that into the step every unit starts at, and the region's exams fill the first
     problems. The other exams stay one tap away. ── */
  const REGIONS={
    kr:{name:{ko:'한국',en:'Korea'},lang:'ko',exam:['ap1','ap2','apcm','calc'],olympiad:['fma','usapho','calc'],other:['jeem'],
      examName:{ko:'AP Physics · 계산 문제',en:'AP Physics and calculation problems'},olyName:{ko:'물리올림피아드(KPhO · F=ma · USAPhO 형식)',en:'Physics olympiad (KPhO, F=ma, USAPhO style)'}},
    in:{name:{ko:'인도',en:'India'},lang:'en',exam:['jeem'],olympiad:['jeem'],other:['ap1','ap2','apcm','fma','usapho'],
      examName:{ko:'JEE Main · Advanced',en:'JEE Main · Advanced'},olyName:{ko:'JEE Advanced · INPhO',en:'JEE Advanced · INPhO'}},
    us:{name:{ko:'미국',en:'United States'},lang:'en',exam:['ap1','ap2','apcm'],olympiad:['fma','usapho'],other:['jeem'],
      examName:{ko:'AP Physics',en:'AP Physics'},olyName:{ko:'F=ma · USAPhO',en:'F=ma · USAPhO'}},
    global:{name:{ko:'그 밖의 나라',en:'Another country'},lang:'en',exam:['ap1','ap2','apcm'],olympiad:['ap1','apcm'],other:['jeem','fma','usapho'],
      examName:{ko:'AP Physics',en:'AP Physics'},olyName:{ko:'국제 올림피아드 준비',en:'International olympiad prep'}}
  };
  const LEVELS=[['middle',{ko:'중학생',en:'Middle school'},2],['high1',{ko:'고1',en:'High school, first years'},3],['high2',{ko:'고2 · 고3',en:'High school, final years'},4],['uni',{ko:'대학생 · 성인',en:'University or adult'},5]];
  const GOALS=['school','exam','olympiad','curious'];
  /* olympiad experience: 0 first time, 1 has sat the first round, 2 has reached the national final or beyond */
  function guessRegion(lang,timeZone){
    if(lang==='ko'||/^Asia\/Seoul$/.test(timeZone||''))return 'kr';
    if(/^Asia\/(Kolkata|Calcutta)$/.test(timeZone||''))return 'in';
    if(/^America\/(New_York|Chicago|Denver|Los_Angeles|Phoenix|Anchorage|Detroit|Boise|Indiana|Kentucky|North_Dakota|Juneau|Sitka|Nome|Adak|Menominee|Metlakatla|Yakutat)|^Pacific\/Honolulu$/.test(timeZone||''))return 'us';
    return 'global';
  }
  function startStep(p){
    const level=LEVELS.find(l=>l[0]===p?.level),base=level?level[2]:3;
    const lift=p?.goal==='olympiad'?1+Math.max(0,Math.min(2,p.oly|0)):p?.goal==='exam'&&(p.region==='in'||p.level==='uni')?1:0;
    return Math.max(1,Math.min(9,base+lift));
  }
  /* the exams that fill the first problems: the goal's own, else the region's school exam */
  function startExams(p){const r=REGIONS[p?.region]||REGIONS.global;return p?.goal==='olympiad'?r.olympiad:r.exam;}
  return{VERSION:'learn-path-v1',STAGES,AREAS,SUBTOPICS,stageOf,classifyLabel,classifyLeagueTopic,stepFromCsat,stepFromStars,bankSubjectOf,REGIONS,LEVELS,GOALS,guessRegion,startStep,startExams};
});
