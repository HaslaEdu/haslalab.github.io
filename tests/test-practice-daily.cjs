/* The daily problems ("오늘의 문제"): how the working is handed in on each device, hints and their cost, "I can't solve
   this", the daily difficulty (the same numbers as the server's practice-progress.js), and the page's flow: one problem
   per screen, skip moves on, "I solved it" stays off until the answer is checked. */
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const T=require('../practice-tools.js');
const root=path.join(__dirname,'..'),read=f=>fs.readFileSync(path.join(root,f),'utf8');

test('device: phone, tablet or computer from the pointer, the screen, touch points and the iPad-as-Mac case',()=>{
  assert.equal(T.deviceKind({fine:true,w:1920,h:1080,touch:0,ua:'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',platform:'Win32'}),'computer');
  assert.equal(T.deviceKind({fine:true,coarse:false,w:1440,h:900,touch:0,ua:'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',platform:'MacIntel'}),'computer');
  assert.equal(T.deviceKind({fine:true,w:1366,h:1024,touch:5,ua:'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari',platform:'MacIntel'}),'tablet','iPadOS reports a desktop Mac');
  assert.equal(T.deviceKind({coarse:true,w:390,h:844,touch:5,ua:'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)',platform:'iPhone'}),'phone');
  assert.equal(T.deviceKind({coarse:true,w:412,h:915,touch:5,ua:'Mozilla/5.0 (Linux; Android 14; Pixel 8) Mobile Safari',platform:'Linux'}),'phone');
  assert.equal(T.deviceKind({coarse:true,w:800,h:1280,touch:10,ua:'Mozilla/5.0 (Linux; Android 14; SM-X710) Safari',platform:'Linux'}),'tablet');
  assert.equal(T.deviceKind({coarse:true,fine:false,w:820,h:1180,touch:5,ua:'x'}),'tablet');
  assert.equal(T.deviceKind({fine:true,coarse:false,w:1280,h:800,touch:10,ua:'Mozilla/5.0 (Windows NT 10.0)'}),'computer','a touch laptop with a mouse is a computer');
  assert.equal(T.deviceKind({}),'computer');
});

test('device options: each device\'s ways first, the rest under "other ways"',()=>{
  assert.deepEqual(T.submitOptions('computer'),{main:['phone','file'],more:['pad','photo']},'computer: the phone (QR) or a file');
  assert.deepEqual(T.submitOptions('tablet'),{main:['photo','pad','file'],more:['phone']},'tablet: a photo, the pad, or a file');
  assert.deepEqual(T.submitOptions('phone'),{main:['photo','file'],more:['pad']},'phone: the camera or a file');
  for(const k of ['computer','tablet','phone']){const o=T.submitOptions(k);assert.deepEqual([...o.main,...o.more].sort(),['file','pad','phone','photo'].filter(x=>k!=='phone'||x!=='phone').sort());}
  assert.deepEqual(T.submitOptions('toaster'),T.submitOptions('computer'));
  const js=read('practice.js');
  assert.match(js,/const opt=H\.submitOptions\(deviceNow\(\)\);if\(!W\.modeChosen\|\|!\[\.\.\.opt\.main,\.\.\.opt\.more\]\.includes\(W\.mode\)\)W\.mode=opt\.main\[0\];/,'the first of this device\'s ways is chosen');
  assert.match(js,/<details class="alt wmore"[^`]*<summary>\$\{tr\('wMore'\)\}/);
  assert.match(js,/deviceKind\(\{coarse:mm\('\(pointer:coarse\)'\),fine:mm\('\(any-pointer:fine\)'\),w:screen\?\.width,h:screen\?\.height,touch:navigator\.maxTouchPoints\|\|0,ua:navigator\.userAgent,platform:navigator\.platform\}\)/);
});

test('the phone hand-off: a QR and a short link to practice.html#ph=<code>, the phone page, the computer polling',()=>{
  assert.equal(T.handoffLink('https://haslalab.org/practice.html?embed=1&lang=ko','K7QM2XPA'),'https://haslalab.org/practice.html#ph=K7QM2XPA');
  assert.ok(T.HANDOFF_RE.test('K7QM2XPA'));assert.ok(!T.HANDOFF_RE.test('K7QM2XP0'),'no 0, O, 1 or I');assert.ok(!T.HANDOFF_RE.test('k7qm2xpa'));
  const js=read('practice.js');
  assert.match(js,/api\('\/api\/learn\/grade\/handoff','POST',\{item:H\.gradeItem\(ctx\.gradeItem\(\)\)/,'the same problem the marking will use');
  assert.match(js,/api\('\/api\/learn\/grade\/handoff\?id='\+h\.id\)/);assert.match(js,/W\.hoTimer=setTimeout\(tick,2500\)/);
  assert.match(js,/const ph=\/\^#ph=\(\[A-HJ-NP-Z2-9\]\{8\}\)\$\/\.exec\(location\.hash\);if\(ph\)\{phoneHome\(ph\[1\]\);return;\}/);
  assert.match(js,/id="phCam" accept="image\/\*" capture="environment" multiple/,'the phone page opens the camera');
  assert.match(js,/sc\.src='vendor\/qrcode\/qrcode\.js'/,'the QR is drawn by the vendored generator (no outside script)');
  assert.ok(fs.existsSync(path.join(root,'vendor/qrcode/qrcode.js')));
});

test('the pad: a stylus\'s pressure rides along with each point and survives a draft; palms are ignored once a pen is seen',()=>{
  const st=T.compactStrokes([{tool:'pen',w:9,pts:[[10.4,20.6,0.333],[11,21,1.7],[12,22]]}]);
  assert.deepEqual(st[0].pts,[[10,21,0.33],[11,21,1],[12,22]]);
  const js=read('practice.js');
  assert.match(js,/if\(e\.pointerType==='pen'&&e\.pressure>0\)p\.push/);
  assert.match(js,/if\(e\.pointerType==='pen'\)W\.penSeen=true;else if\(e\.pointerType==='touch'&&W\.penSeen\)return;/,'palm rejection');
  assert.match(js,/padUndo/);assert.match(js,/data-tool/);
});

test('hints: a problem\'s own, else the first step of its solution, else (typed exam answers) its choices, else none',()=>{
  assert.deepEqual(T.hintList({kind:'track',hints:['a','b'],sol:'x'}).map(h=>h.text),['a','b']);
  const step=T.hintList({kind:'track',hints:[],sol:'From rest, $\\Delta x=\\tfrac12 a t^2$. So the distance is four times.\n\nMore.'});
  assert.deepEqual(step,[{kind:'solstep',text:'From rest, $\\Delta x=\\tfrac12 a t^2$.'}]);
  assert.deepEqual(T.hintList({kind:'exam',ch:[]},{choices:true}),[{kind:'choices'}]);
  assert.deepEqual(T.hintList({kind:'exam',ch:[]},{choices:false}),[],'nothing is made up: the button is off');
  assert.deepEqual(T.hintList({kind:'contest',b:[]}),[]);
  assert.equal(T.firstStep('Use $v=1.5$ m/s. Then go.'),'Use $v=1.5$ m/s.','a full stop inside math does not end the step');
  assert.equal(T.firstStep(''),'');
});

test('hint cost: 25 % of the problem\'s XP each, never below 25 % (the same rule as the league on the server)',async()=>{
  assert.deepEqual([0,1,2,3,4,9].map(T.hintMult),[1,0.75,0.5,0.25,0.25,0.25]);
  const L=await import(path.join(root,'community/src/league.js'));
  for(const h of [0,1,2,3,4,7])assert.equal(T.hintMult(h),L.hintMult(h),'hints '+h);
});

test('a hint brings the problem back once tomorrow, even when solved today; then it leaves',()=>{
  let r=T.reviewUpdate({},'ap1-u1-001','hinted','2026-11-24',{k:'track',u:'mechanics/kinematics',once:1},1);
  assert.equal(r['ap1-u1-001'].due,'2026-11-25');
  r=T.reviewUpdate(r,'ap1-u1-001','right','2026-11-24',{k:'track'},2);
  assert.equal(r['ap1-u1-001'].due,'2026-11-25','solved today: still due tomorrow');assert.deepEqual(T.dueIds(r,'2026-11-25'),['ap1-u1-001']);
  r=T.reviewUpdate(r,'ap1-u1-001','right','2026-11-25',null,3);
  assert.ok(!('ap1-u1-001' in r),'right tomorrow: it leaves (once)');
  /* without "once" the usual 1, 3, 7, 21 days */
  const plain=T.reviewUpdate(T.reviewUpdate({},'x','wrong','2026-11-24',{k:'track'},1),'x','right','2026-11-25',null,2);
  assert.equal(plain.x.box,1);
});

test('daily difficulty: the page\'s numbers are the server\'s',async()=>{
  const S=await import(path.join(root,'community/src/practice-progress.js'));
  assert.deepEqual(T.LEVEL_STEPS,S.LEVEL_STEPS);
  for(const lv of ['L1','L2','L3','L4']){assert.equal(T.dailyStart(lv),S.dailyStart(lv));assert.deepEqual(T.dailyBounds(lv),S.dailyBounds(lv));}
  for(const result of ['right','solved','wrong','missed','giveup','skip','hint'])for(const n of [0,9,10,40])for(const step of [2,4.5,7,9])for(const h of [0,1,2,3])
    for(const lv of ['L1','L3'])for(const r of [1100,1450,1700,1900])assert.equal(T.dailyUpdate(r,n,step,result,h,lv),S.dailyUpdate(r,n,step,result,h,lv),[r,n,step,result,h,lv].join());
});

test('daily difficulty: new learners start at medium; right goes up, "I can\'t solve this" goes down; shown gently',()=>{
  assert.equal(T.dailyStart('L1'),1450);assert.equal(T.dailyStart('L4'),1850);
  const label=T.dailyLabel(null,'L1','ko');assert.equal(label.word,'보통');assert.equal(label.text,'보통','no arrow before any answer');
  assert.equal(T.dailyLabel(null,'L3','en').word,'medium');
  let d=T.dailyApply(null,'L1',4.5,'right',0,100);assert.equal(d.r,1474);assert.equal(d.n,1);assert.equal(d.dir,1);
  assert.equal(T.dailyLabel(d,'L1','ko').text,'보통 ↑');
  d=T.dailyApply(d,'L1',4.5,'giveup',0,200);assert.ok(d.r<1474);assert.equal(d.dir,-1);assert.match(T.dailyLabel(d,'L1','ko').text,/↓$/);
  assert.equal(T.dailyApply(d,'L1',4.5,'skip',0,300),d,'a skip changes nothing');
  assert.equal(T.dailyLabel({r:1100},'L1','ko').word,'쉬움');assert.equal(T.dailyLabel({r:1800},'L1','ko').word,'어려움');
  assert.doesNotMatch(T.dailyLabel(d,'L1','ko').text,/\d/,'no number is shown');
  /* the next problem is picked near the rating */
  const pool=[2,3,4,5,6,7].map(s=>({id:'p'+s,u:'mechanics/energy',s}));
  assert.equal(T.dailyPick(pool,1450,{rand:()=>0.5}).s,4,'1450 is between steps 4 and 5');
  assert.equal(T.dailyPick(pool,1200,{rand:()=>0.5}).s,2,'after a fall: easier');
  assert.equal(T.dailyPick(pool,1450,{rand:()=>0.5,seen:new Set(['p4'])}).s,5);
  /* the onboarding and the level change start a level at medium */
  const js=read('practice.js');
  assert.match(js,/saved\.studyLevel=key;dailyEnsure\(key\);/,'the four level cards');
  assert.match(js,/saved\.studyLevel=stage\|\|H\.defaultLevel\(profile\);dailyEnsure\(saved\.studyLevel\);/,'the full first questions, with the daily goal');
  assert.match(js,/function dailyEnsure\(level\)\{if\(!saved\.dailyR\[level\]\)\{saved\.dailyR\[level\]=\{r:H\.dailyStart\(level\)/);
  assert.match(js,/if\(r\.daily\)dailyMerge\(r\.daily,true\)/,'the server\'s value wins for members');
});

test('the daily flow: one problem a screen; skip moves on; "I solved it" is off until checked; hint and "I can\'t solve this"',()=>{
  const js=read('practice.js'),css=read('practice.css');
  /* the footer of every daily problem */
  assert.match(js,/<button type="button" id="skip">\$\{tr\('skip'\)\}<\/button><button type="button" id="hint">💡 \$\{tr\('hint'\)\}<\/button><button type="button" id="giveup">\$\{tr\('giveUp'\)\}<\/button><button type="button" class="primary" id="next" disabled title="\$\{esc\(tr\('dWait'\)\)\}">\$\{tr\('solvedIt'\)\}<\/button>/,'"I solved it" starts disabled');
  assert.equal((js.match(/dailyFoot\(/g)||[]).length,4,'exam, track and competition problems use it (and its definition)');
  assert.match(js,/function ready\(ok\)\{\s*const b=\$\('next'\);if\(!b\)return;b\.hidden=false;b\.disabled=false;/,'checked: it opens');
  for(const place of ['ready(ok);$(\'skip\').hidden=true;$(\'next\').focus();','ready(ok);$(\'skip\').hidden=true;$(\'hint\').hidden=true;$(\'next\').focus();'])assert.ok(js.includes(place),place);
  assert.doesNotMatch(js,/\$\('next'\)\.hidden=false;\$\('skip'\)\.hidden=true;\$\('next'\)\.focus\(\)/,'no path shows next before the check');
  assert.match(js,/ctx\.lock\(!!mv\.solved\)/,'a marked answer opens it');
  assert.match(js,/if\(isDaily\(s\)&&mv\.retry&&!was&&\$\('next'\)\)\{ready\(false\);/,'a "try again" marking opens it too, as "Continue"');
  /* skip: record, a short line, the next problem at once; the new screen slides in */
  assert.match(js,/record\(item\.id,'exam',item\.u,item\.s,'skip'\);if\(daily\)flash\(tr\('dSkipNote'\)\+' →'\);[^\n]*next\(\);\};/);
  assert.match(js,/record\(item\.id,'track',item\.u,item\.s,'skip'\);if\(daily\)flash\(tr\('dSkipNote'\)\+' →'\);[^\n]*next\(\);\};/);
  assert.match(css,/\.session\.daily\{animation:dIn/);assert.match(css,/prefers-reduced-motion:reduce\)\{\.session\.daily\{animation:none\}/);
  /* a hint: recorded at once, back tomorrow once */
  assert.match(js,/record\(item\.id,kindMode\(item\),item\.u,item\.s,'hint'\);\s*saved\.review=H\.reviewUpdate\(saved\.review,item\.id,'hinted',today\(\),\{\.\.\.metaOf\(item\),once:1\}\)/);
  assert.match(js,/if\(result==='hint'\)sync\(\);/,'sent at once, before any answer');
  assert.match(js,/hint:daily\?undefined:/,'a daily hint is never opened for the learner');
  /* "I can't solve this": a give-up attempt, not back tomorrow, then the next problem */
  assert.match(js,/record\(item\.id,kindMode\(item\),item\.u,item\.s,'giveup'\);\s*delete saved\.wrong\[item\.id\];delete saved\.review\[item\.id\];/);
  assert.match(js,/flash\(tr\('dGiveUpNote'\)\);next\(\);/);
  /* the daily answer carries its context, level and hints; a daily hinted answer is right with hints, not "solved" */
  assert.match(js,/if\(!extra&&isDaily\(s\)&&s\.current\?\.id===item_id\)extra=\{ctx:'daily',level:s\.lv,hints:s\.hints\|0\};/);
  assert.match(js,/const result=ok\?\(s\.hints&&!isDaily\(s\)\?'solved':'right'\):'wrong';/);
  /* the picks follow the daily difficulty, reviews first */
  assert.match(js,/const reviews=\[\.\.\.new Set\(\[\.\.\.dueNow\(\),/);assert.match(js,/if\(isDaily\(s\)\)return pickDaily\(s\);/);
  /* copy in both languages */
  for(const k of ['giveUp','dContinue','dLevel','dHintCost','dHintTomorrow','dGiveUpNote','dSkipNote','dWait','wPhone','wMore','hoTitle','hoWait','hoGot','phTitle','phSent','phBad'])
    assert.match(js,new RegExp(k+":'[^']+'[\\s\\S]*"+k+":'[^']+'"),k+' in both languages');
});
