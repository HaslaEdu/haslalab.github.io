/* Build the official-link catalogue and verified per-session practice settings.
 * No original PDFs or question text are copied into this site.
 * node tools/contest_build.cjs
 */
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const read = name => JSON.parse(fs.readFileSync(path.join(root, name), 'utf8'));
const chem = read('data/research/kmchc-research.json');
const math = read('data/research/kmo-research.json');
const km = read('tools/theory/kmo.json');
const rule = 'https://olympiad.kchem.org/board/article/1664';
const archive = 'https://www.kmo.or.kr/kmo/sub07.html';
const competitions = {
  kmchc: {
    coverage: '공식 자료실의 2010~2019·2021~2026 공개 기출 전체. 2024년부터 연 2회, 2025년부터 일반·심화로 구분합니다. 2020년은 공개 기출 게시글을 찾지 못했습니다.',
    coverageEn: 'All publicly listed papers for 2010–2019 and 2021–2026. Two sittings a year since 2024, general and advanced tracks since 2025. No 2020 paper is listed in the official archive.',
    rules: ['최신 기준: 일반·심화 각각 120분, 객관식 50문항. 정답 +3점, 오답 −1점, 미기입 0점.', 'OMR에 검정 컴퓨터용 사인펜으로 기입합니다. 수정테이프 사용 가능, 액체 수정액 불가.', '계산기·휴대전화·웨어러블 등 전자기기 사용 금지. 2026년 2차는 13:30 입실, 14:00~16:00 시험입니다.', '과거 시험은 해당 연도의 문항 수·선택지·정정된 정답과 삭제 문항을 적용합니다. 삭제 후 공식 환산 방식이 미확인인 회차는 참고 점수로만 표시합니다.'],
    rulesEn: ['Current format: 120 minutes, 50 multiple-choice questions per track; +3 correct, −1 wrong, 0 blank.', 'Use a black OMR pen. Correction tape is allowed; correction fluid is not.', 'Calculators, phones and wearable electronics are prohibited. For 2026 sitting 2, arrive by 13:30; the exam runs 14:00–16:00.', 'Historical papers use their own question counts, choices and corrected keys. The 2021–2023 online exams had no wrong-answer deduction. Scores affected by unresolved deletion policies are labelled as practice scores.'],
    sources: [{title:'대한화학회 공식 기출 자료실',url:chem.archive_url},{title:'2026년 2차 대회 요강',url:rule},{title:'2026년 2차 응시 유의사항',url:'https://olympiad.kchem.org/board/article/1709'}]
  },
  kmo: {
    coverage: '대한수학회 공식 자료실의 2009~2026 공개 문제를 중등·고등, 1차·2차·최종시험으로 구분했습니다. 2008년 이전은 공식 온라인 자료실에 공개된 기출이 없습니다. 2026년 2차는 11월 14일 예정으로 아직 기출이 공개되지 않았습니다.',
    coverageEn: 'Official papers for 2009–2026, separated by middle/high school, first/second round and final. Pre-2009 papers are not published in the official online archive. The 2026 second round is scheduled for November 14 and its paper is not yet available.',
    rules: ['2026년 1차: 중등·고등 공통 150분, 단답형 20문항, 4·5·6점 배점으로 총 100점. 답은 세 자리, 1000 이상은 1000으로 나눈 나머지입니다.', '2026년 2차: 서술형 8문항, 각 7점. 오전 09:30~12:30, 오후 14:20~17:20에 각 4문항을 풉니다.', '수험표·신분증·필기구를 준비합니다. 2차는 자·컴퍼스 허용, 각도기·계산기·통신기기·손목시계·이어폰·개인 연습장 금지입니다.', '과거 1차 240분, 2020년 온라인 형식, 2021~2022년 75분씩 두 교시 등은 당시 원문 지침으로 나누었습니다. 온라인 회차에는 세 자리 제한이 없는 시험이 있습니다.', '공식 문제·정답 합본에는 문항 옆에 정답이 인쇄된 경우가 있습니다. 정답을 가린 개인 학습용 문제지 또는 인쇄본을 준비하세요. 서술형에는 자동 점수를 매기지 않습니다.'],
    rulesEn: ['2026 first round: 150 minutes, 20 short-answer questions, worth 4/5/6 points for a total of 100. Use three digits; answers of 1000 or more are reduced modulo 1000.', '2026 second round: eight proofs worth seven points each, four per 180-minute session, 09:30–12:30 and 14:20–17:20.', 'Bring admission slip, ID and writing tools. Ruler and compass are allowed in round two; protractors, calculators, communication devices, watches, earphones and personal scratch paper are prohibited.', 'Historical timing follows each paper, including 240-minute first rounds, the 2020 online format, and two 75-minute sessions in 2021–2022. Some online papers have no three-digit answer limit.', 'Some official PDFs print answers beside the questions. Prepare a personal copy with answers covered, or a printed paper. Proofs are saved for self-review, without an automatic score.'],
    sources: [{title:'대한수학회 공식 기출 자료실',url:archive},{title:'2026년 1차 시험 요강',url:math.rulesSources.latestFirstNotice},{title:'2026년 2차 시험 요강',url:math.rulesSources.latestSecondNotice},{title:'공식 기출 사용 안내',url:'https://www.kmo.or.kr/board/list.html?code=kmo_notice01&num=26255'}]
  }
};
const entries = [];
const years = new Map();
for (const raw of chem.entries || []) {
  const y = raw.year;
  if (!years.has(y)) years.set(y, []);
  const list = years.get(y), part = 'T' + (list.length + 1);
  const title = raw.label || {ko:raw.id,en:raw.id};
  const e = {
    id:raw.id, comp:'kmchc', year:y, part, title,
    minutes:raw.durationMinutes, questions:raw.questionCount, kind:'choice', choices:raw.choiceCount,
    choiceLabels:raw.choiceLabels, answers:raw.answers || [],
    answersVerified:raw.answersVerified === true || chem.validation?.answer_keys_complete === true,
    point:raw.scoring?.correct, penalty:Math.abs(raw.scoring?.wrong || 0),
    scoringVerified:raw.scoring?.verifiedForSession === true && !(raw.excluded || []).length,
    excluded:raw.excluded || [], fullCredit:raw.fullCredit || [],
    paper:raw.questionUrl, solution:raw.answerUrl,
    ...(raw.combinedPdf && raw.answerPage>1?{paperLastPage:raw.answerPage-1}:{}),
    paperContainsAnswers:raw.combinedPdf === true || raw.paperContainsAnswers === true || raw.questionUrl === raw.answerUrl,
    rules:raw.rules || [`${raw.durationMinutes}분, ${raw.questionCount}문항, ${raw.choiceCount}지선다. 해당 연도 원문의 주의사항을 따릅니다.`, ...(y>=2024?chem.latest_rules.rules:[])], formatNote:(raw.specialNotes || []).join(' '),
    sources:[{title:'공식 기출 · 정정 안내',url:raw.sourceUrl},{title:'대회 요강',url:raw.ruleUrl||rule},...(raw.scoringSourceUrl?[{title:'당시 채점 규정',url:raw.scoringSourceUrl}]:[])],
    practice:raw.practice !== false && !!raw.durationMinutes && !!raw.questionCount
  };
  list.push(e); entries.push(e);
}
for (const raw of math.entries || []) {
  const all = raw.fullCredit || raw.allCorrectQuestions || [];
  const base = {
    ...raw, fullCredit:all, sources:raw.sources || [{title:'공식 기출 자료실',url:raw.source_url||archive},{title:'2026년 1차 요강',url:math.rulesSources.latestFirstNotice},{title:'2026년 2차 요강',url:math.rulesSources.latestSecondNotice}],
    title:{ko:`KMO ${raw.year} · ${raw.title.ko}`,en:`KMO ${raw.year} · ${raw.title.en}`},
    paper:raw.paper+(raw.paperPage?'#page='+raw.paperPage:''),
    paperContainsAnswers:raw.paperContainsAnswers === true || raw.inlineAnswers === true,
    answers:(raw.answers || []).map(x=>x === '*' ? null : Array.isArray(x)?x.map(Number):x === null?null:Number(x)),
    rules:[...(raw.rules || []),...(['가','나'].includes(raw.examForm)?[`공식 공개 ${raw.examForm}형 문제지 기준으로 채점합니다. 다른 유형의 문제지를 사용하지 마세요.`]:[])], formatNote:raw.formatNote || '',
    penalty:0
  };
  if (raw.sessions?.length > 1) {
    for (let i=0;i<raw.sessions.length;i++) {
      const s = raw.sessions[i], offset = s.questionOffset || 0, count = s.questions;
      entries.push({...base, ...s, id:base.id+'-s'+(i+1),
        title:{ko:base.title.ko+' · '+s.label,en:base.title.en+' · '+(s.labelEn||'Session '+(i+1))},
        answers:base.answers.slice(offset,offset+count), points:base.points?.slice(offset,offset+count),
        fullCredit:all.filter(q=>q>offset&&q<=offset+count).map(q=>q-offset),
        questionOffset:offset, sessions:undefined,
        formatNote:base.formatNote || '교시별 독립 응시 · 원문에 표시된 해당 문항만 풉니다.'});
    }
  } else entries.push({...base,sessions:undefined});
}
const seen = new Set();
for (const e of entries) {
  if (seen.has(e.id)) throw new Error('Duplicate exam id: '+e.id);
  seen.add(e.id);
  if (!/^https:\/\//.test(e.paper || '')) throw new Error('Invalid official paper URL: '+e.id);
  if (e.answersVerified && e.answers.length !== e.questions) throw new Error('Wrong answer count: '+e.id);
}
entries.sort((a,b)=>b.year-a.year||a.comp.localeCompare(b.comp)||(a.comp==='kmchc'?(Number(b.id.split('-')[2])||0)-(Number(a.id.split('-')[2])||0):0)||a.id.localeCompare(b.id,undefined,{numeric:true}));
const theory = {};
for (const [y,list] of years) {
  theory[y] = {p:list.map(e=>[e.part,e.title.ko]),f:Object.fromEntries(list.map(e=>[e.part,{paper:e.paper,...(e.solution?{sol:e.solution}:{})}])),h:{ko:'대한민국',en:'South Korea'},cc:'kr'};
}
const metadata = {abbr:'KMChC',full:{ko:'한국중학생화학대회',en:'Korean Middle-School Chemistry Competition'},since:2010,scope:{ko:'대한민국 · 중학생',en:'South Korea · middle school'},plain:true,rounds:true};
const payload = {checkedAt:'2026-10-30',competitions,entries};
const built = '/* Generated by tools/contest_build.cjs: official links and verified exam metadata only. */\n'+
  'window.CONTEST_EXAMS='+JSON.stringify(payload)+';\n'+
  'window.THEORY=window.THEORY||{};window.THEORY.kmchc='+JSON.stringify(theory)+';\n'+
  'window.THEORY_META=window.THEORY_META||{};window.THEORY_META.kmchc='+JSON.stringify(metadata)+';\n';
fs.writeFileSync(path.join(root,'contest-exams.js'),built);
console.log(`Built ${entries.length} exams: KMChC ${entries.filter(e=>e.comp==='kmchc').length}, KMO ${entries.filter(e=>e.comp==='kmo').length}; ${entries.filter(e=>e.answersVerified).length} official keys.`);
