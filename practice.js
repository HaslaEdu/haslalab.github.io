/* Practice: short exam problems on the learning path, one at a time, graded at once.
   Like a language-learning app: a session of ten, the step rises after two right answers in a row and
   falls after a wrong one, and a daily streak. Progress stays in this browser (localStorage). */
(()=>{
  'use strict';
  const P=window.HL_LEARN_PATH,$=id=>document.getElementById(id);
  const params=new URL(location.href).searchParams;
  const embedded=params.get('embed')==='1'&&window.parent!==window;
  const SESSION=10;
  const copy={
    ko:{
      lvTitle:'레벨',lvPick:'어떤 문제를 풀까요?',lvIntro:'레벨을 고르면 오늘의 문제와 세트 만들기의 기본 출처가 그 레벨의 문제로 바뀝니다. 언제든 바꿀 수 있습니다.',lvHas:'들어 있는 문제',lvSoon:'준비 중',lvChange:'바꾸기',lvCurrent:'지금 레벨',lvBankNote:'교재 · 대학 문제는 "교재 · 대학 문제" 탭에서 풉니다.',ob_stage:'어느 레벨에서 시작할까요?',quickIntro:'고르면 바로 첫 문제가 나옵니다. 가입하지 않아도 풀 수 있고, 레벨은 언제든 바꿀 수 있습니다.',
      wTitle:'풀이 제출',wIntro:'종이에 풀어 사진을 찍거나, 패드에 쓰거나, 파일을 올리면 채점 기준표로 점수를 매깁니다.',wRule:'70% 이상이면 통과하고 다음 문제로 갑니다. 40–69%는 부분 점수: 복습 목록에 넣고 넘어갑니다. 40% 미만이면 힌트를 보고 다시 풀거나 넘어갈 수 있습니다.',
      wPhoto:'사진',wPad:'패드',wFile:'파일',wTake:'사진 찍기 · 고르기',wFilePick:'이미지나 PDF 고르기',wPdfNote:'PDF는 앞 4쪽까지 이미지로 바꿔 보냅니다.',wPdfFail:'이 PDF를 읽지 못했습니다. 페이지를 사진으로 올려 주세요.',wImgFail:'이 파일은 이미지로 읽을 수 없습니다.',
      wPen:'펜',wEraser:'지우개',wThin:'가늘게',wMid:'보통',wThick:'굵게',wUndo:'되돌리기',wClear:'지우기',wAddPage:'페이지로 추가',wPages:'보낼 페이지',wRemove:'빼기',wMax:'4쪽까지 보낼 수 있습니다.',wNone:'보낼 풀이가 없습니다. 사진을 올리거나 패드에 써 주세요.',
      wSend:'채점 받기',wReading:'읽는 중',wGrading:'채점 중',wLogin:'채점은 로그인해야 쓸 수 있습니다. 하루 10번까지 무료입니다.',wSoon:'채점 서버 준비 중입니다. 풀이는 이 화면에 남아 있으니 잠시 뒤에 다시 보내 주세요.',
      wLimit:'오늘 채점 횟수를 모두 썼습니다. 내일 다시 쓸 수 있습니다.',wUnreadable:'글씨를 읽지 못했습니다. 밝은 곳에서 다시 찍어 주세요. 횟수는 줄지 않았습니다.',wFail:'지금은 채점할 수 없습니다. 잠시 뒤에 다시 시도하세요. 횟수는 줄지 않았습니다.',wBad:'보낸 내용을 확인하세요.',
      wLeft:'오늘 남은 채점',wTranscript:'읽은 내용',wAiNote:'AI 채점이라 틀릴 수 있습니다. 이상하면 문제 신고로 알려 주세요.',wRubric:'채점 기준',wPoints:'점수',
      bandPass:'통과',bandPartial:'부분 점수',bandRetry:'다시 풀기',wRetry:'다시 풀기',wMoveOn:'넘어가기',wLast:'지난 채점',wNoText:'이 문제는 글로 옮겨 적지 않아 풀이 채점을 쓸 수 없습니다.',wUnitUp:'이 단원의 단계가 올랐습니다',wPassNote:'통과입니다. 다음 문제로 갑니다.',wPartialNote:'부분 점수입니다. 복습 목록에 넣었습니다.',wRetryNote:'힌트를 보고 다시 풀어 보세요.',wRetryPlain:'풀이를 고쳐서 다시 보내 보세요.',wOpen:'✎ 풀이 제출',
      rSentOk:'신고를 보냈습니다. 고치면 "내 신고"에서 상태가 바뀝니다.',rQueued:'지금은 보낼 수 없어 이 기기에 두었습니다. 연결되면 자동으로 다시 보냅니다.',rLimit:'오늘은 신고를 더 보낼 수 없습니다. 내일 다시 보내 주세요.',rStatus_open:'접수',rStatus_fixed:'고침',rStatus_rejected:'반려',rStatus_pending:'보내는 중',
      moreProblems:'10문제 더',typeNumber:'숫자로 답하세요 (예: 12.5, 3e8)',typeFormula:'식으로 답하세요 (예: 2*sqrt(gL))',answer:'답',keypad:'수식 키패드',typeHelp:'곱하기는 생략해도 됩니다(2mg). 거듭제곱은 ^, 분수는 a⁄b, 10의 거듭제곱은 ×10ⁿ.',notYet:'식을 끝까지 입력하세요',onlyNumber:'숫자만 입력하세요',unknownVar:'이 문제에 없는 문자',showChoices:'보기 보기 (힌트로 셉니다)',ob_region:'어디에서 공부하나요?',ob_level:'지금 어느 단계인가요?',ob_goal:'무엇을 위해 공부하나요?',ob_oly:'올림피아드는 어디까지 해 봤나요?',ob_daily:'하루 목표를 정하세요',
      obKr:'AP Physics, 한국 시험 계산 문제, 올림피아드',obIn:'JEE Main · Advanced',obUs:'AP Physics, F=ma · USAPhO',obGlobal:'AP Physics와 국제 올림피아드 준비',
      goSchool:'학교 공부 · 내신',goExam:'입시 시험',goOly:'물리 올림피아드',goCurious:'그냥 물리가 좋아서',oly0:'처음 준비합니다',oly1:'1차(예선) 시험을 쳐 봤습니다',oly2:'본선 이상 진출했습니다',
      perDay:'문제',tabLeague:'리그',goalTitle:'하루 목표',goalToday:'오늘',goalSave:'저장',goalSaved:'저장했습니다.',goalFailed:'저장하지 못했습니다. 다시 해 보세요.',goalMember:'계정에 저장됩니다. 오늘 목표는 오늘 첫 문제를 맞힐 때 정해지고, 바꾼 목표는 다음 날부터 셉니다.',goalGuest:'이 기기에만 저장됩니다. 로그인하면 목표를 채운 날 보너스 리그 XP를 받습니다.',goalMet:'목표 달성',goalMetGuest:'로그인하면 +{n} XP를 받습니다',goalTomorrow:'내일부터 {n}문제',goalNext:'다음',goalOpen:'하루 목표 바꾸기',goalLeft:'{n}문제 남음',lfAsk:'나라와 하루 목표를 정해 주세요',lfAskSub:'한 번만 묻습니다. 기본 시험과 하루 목표에 쓰이고, 설정에서 바꿀 수 있습니다.',lfSave:'저장',lfLater:'나중에',lfPick:'나라와 하루 목표를 골라 주세요.',lfFailed:'저장하지 못했습니다. 다시 시도해 주세요.',leagueFailed:'리그를 불러오지 못했습니다.',back:'이전',obDone:'시작 단계',obNext:'모든 단원이 이 단계에서 시작하고, 첫 문제는 위 시험에서 나옵니다. 12문제 수준 찾기로 더 정확하게 맞출 수 있습니다.',
      editProfile:'학습 설정',myExams:'내 시험',otherExams:'다른 시험 보기',dailyGoal:'오늘 목표',
      tabClass:'학급',classIntro:'선생님이 알려 준 6자리 코드로 학급에 들어가면 과제가 여기에 나옵니다. 선생님은 학급을 만들어 AP · JEE 문제를 과제로 내고, 학생별 단원 실력과 과제 진행을 볼 수 있습니다.',myAssignments:'내 과제',noAssignments:'아직 과제가 없습니다.',classCode:'학급 코드',join:'참여',leave:'나가기',leaveConfirm:'이 학급에서 나갈까요?',teach:'가르치기',students:'명',className:'학급 이름',newClass:'학급 만들기',classFree:'무료: 학급 1개, 학생 30명까지. 학생은 이 학급의 학습 기록만 공유합니다.',due:'마감',shareCode:'학생에게 학급 코드를 알려 주세요. 학생이 문제 풀기의 "학급" 탭에서 코드를 입력하면 참여합니다.',student:'학생',answered:'푼 문제',lastActive:'최근 학습',remove:'내보내기',removeConfirm:'이 학생을 학급에서 내보낼까요?',noStudents:'아직 학생이 없습니다.',newAssignment:'과제 내기',allOf:'전체',assign:'과제 내기',closeClass:'학급 닫기',closeConfirm:'학급을 닫을까요? 학생들은 더 이상 과제를 볼 수 없습니다.',
      cl_bad_name:'학급 이름을 입력하세요.',cl_class_limit:'무료로는 학급을 1개까지 만들 수 있습니다.',cl_bad_code:'코드는 6자리입니다.',cl_class_not_found:'그 코드의 학급이 없습니다.',cl_own_class:'내가 만든 학급입니다.',cl_class_full:'학급 정원이 찼습니다.',cl_bad_items:'문제를 고르세요.',cl_bad_due:'마감일을 확인하세요.',cl_rate_limited:'잠시 뒤에 다시 시도하세요.',
      tabTracks:'시험별',trackPick:'시험과 단원을 고르면 그 시험 형식의 문제 10개를 풉니다. 하슬라랩이 직접 만든 문제입니다.',mixed:'전체 섞어서',numPh:'답 (숫자)',check:'확인',notNumber:'숫자로 입력하세요 (예: 3.2, 1.5e3, 2×10^4)',hint:'힌트',tutor:'AI 튜터',discuss:'이 문제 토론',seeDiscuss:'이 문제의 질문 보기',newDiscuss:'질문 올리기',byHasla:'하슬라랩 창작 문제',
      tutorLogin:'AI 튜터는 로그인하면 하루 5번까지 무료로 쓸 수 있습니다.',login:'로그인',tutorPh:'어디서 막혔는지 적어 보세요',tutorSend:'묻기',thinking:'생각하는 중…',tutorLimit:'오늘 무료 질문을 모두 썼습니다. 내일 다시 쓸 수 있습니다.',tutorFail:'지금은 답할 수 없습니다. 잠시 뒤에 다시 시도하세요.',tutorLeft:'오늘 남은 질문',aiNote:'AI가 만든 답변이라 틀릴 수 있습니다.',
      aiTranslated:'AI 번역',showOriginal:'원문 보기',showTranslation:'번역 보기',translating:'번역하는 중…',withHints:'힌트 사용',
      diagTitle:'내 수준 찾기',diagBody:'분야별로 두 문제씩, 12문제(약 10분)를 풀면 단원별 시작 단계를 정해 드립니다. 건너뛰고 바로 풀어도 됩니다.',diagStart:'수준 찾기 시작',diagDone:'분야별 시작 단계를 정했습니다. 오늘의 추천은 이제 이 단계에서 나옵니다.',
      lvBeginner:'입문',lvFamiliar:'익숙',lvProficient:'능숙',lvMaster:'마스터',tier:'XP 등급',
      noteTracks:'AP · JEE 문제는 하슬라랩이 각 시험 형식에 맞춰 직접 만든 창작 문제입니다. AP와 Advanced Placement는 College Board의 상표이며, College Board · NTA와 관계가 없습니다. 기록은 이 기기에 저장되고, 로그인하면 계정에도 저장됩니다.',
      title:'문제 풀기',streak:'일 연속',xp:'XP',solved:'문제 해결',pick:'단원을 고르면 내 단계에 맞는 문제 10개를 풉니다.',
      none:'아직 문제가 없습니다',step:'단계',start:'시작',again:'한 번 더',units:'단원 목록',next:'다음 문제',finish:'결과 보기',
      right:'정답입니다.',wrong:'오답입니다. 정답은',up:'단계가 올랐습니다',down:'한 단계 쉬운 문제로 갑니다',
      result:'맞힌 문제',of:'/',done:'세션 완료',loading:'문제를 불러오는 중…',failed:'문제를 불러오지 못했습니다.',retry:'다시 시도',
      pdf:'원본 시험지',quit:'← 목록',time:'권장 시간',sec:'초',progress:'해결',skip:'건너뛰기',skipped:'건너뜀',
      tabUnits:'단원별',calcName:'계산 문제 (한국 시험 기출)',noteUnits:'단원마다 하슬라랩 창작 문제(AP · JEE · F=ma · USAPhO 형식)와 한국 시험 기출 계산 문제(출처: 한국교육과정평가원, 서울특별시교육청, 경기도교육청, 인천광역시교육청 · 웹·앱 배포 허가 범위 안에서 제공)를 함께 풉니다. 기록은 이 기기에 저장되고, 로그인하면 계정에도 저장됩니다.',synced:'계정에 저장됨',tabToday:'오늘의 추천',todayTitle:'오늘의 10문제',whyReview:'복습',whyWeak:'약한 단원',whyStretch:'도전',whyNew:'새 단원',focus:'집중 단원',startToday:'시작하기',mySkills:'단원별 실력',unit:'단원',accuracy:'정답률',noSkills:'단원별 실력은 그 단원 문제를 풀면 기록됩니다. 많이 풀수록 추천이 잘 맞습니다.',syncFailed:'저장 실패 · 다시 시도합니다',loginToSave:'로그인하면 기록이 계정에 저장됩니다 →',tabBank:'교재 · 대학 문제',tabContest:'대회 기출',
      bankPick:'분야와 난이도를 고르면 교재와 대학 강의 문제를 하나씩 풉니다. 풀이를 확인하고 스스로 채점하세요.',stars:'난이도',showSol:'풀이 보기',noSol:'아직 등록된 풀이가 없습니다. 커뮤니티 질문 · 답변 갤러리나 AI에게 물어보세요.',
      solvedIt:'풀었어요',missedIt:'못 풀었어요',original:'원문 보기',translated:'번역 보기',noKo:'한국어 번역이 아직 없어 원문을 보여 줍니다.',draft:'하슬라랩 작성 풀이 · 검수 전',refFig:'참고 그림',empty:'이 조건의 문제가 더 없습니다. 난이도나 분야를 바꿔 보세요.',
      contestPick:'대회를 고르면 기출 문제가 하나씩 나옵니다. PDF로 풀고, 풀이를 확인한 뒤 스스로 채점하세요.',paper:'문제',solution:'풀이',noContestSol:'이 문제는 공식 풀이가 없습니다.',problems:'문제',another:'다른 문제',figInPdf:'그림은 아래 원본 PDF에서 볼 수 있습니다.',transcribed:'문제 글은 원본 PDF에서 옮겨 적은 것입니다. 원본과 다르면 PDF를 기준으로 하세요.',noteBank:'문항 출처는 문제마다 표시합니다(교재 · 대학 강의). 한국어 번역과 "하슬라랩 작성" 풀이는 검수 중입니다. 기록은 이 기기에 저장되고, 로그인하면 계정에도 저장되어 다른 기기에서 이어집니다.',noteContest:'각 대회의 공식 문제와 풀이이며, 한국어판은 하슬라랩 번역입니다. 기록은 이 기기에 저장되고, 로그인하면 계정에도 저장되어 다른 기기에서 이어집니다.',
      tabReview:'복습',tabCustom:'세트 만들기',noteCustom:'세트, 복습 목록, 나중에 풀기는 이 기기에 저장됩니다. 정답 기록과 단원 실력은 로그인하면 계정에도 저장됩니다.',
      customIntro:'풀 문제의 출처, 주제, 난이도, 개수를 직접 정합니다. 조건에 맞는 문제 가운데 아직 풀지 않았고 최근에 보지 않은 문제가 먼저 나옵니다.',cSource:'문제 출처',cAll:'모든 문제',cCalc:'한국 학교 시험 기출',cContest:'대회 기출',cTopics:'주제',cAllTopics:'전체',cPickUnits:'단원별로 고르기',cDiff:'난이도 (단계)',cCount:'문제 수',cFormat:'답하는 방식',cChoice:'보기 고르기',cTyped:'직접 입력',cFormatNote:'직접 입력은 답이 숫자나 식인 문제만 남깁니다.',cCompetition:'대회',cAnyContest:'모든 대회',cYears:'연도',cTimer:'풀이 시간 재기',cMatch:'조건에 맞는 문제',cStartSet:'세트 시작',cNoMatch:'조건에 맞는 문제가 없습니다. 조건을 넓혀 보세요.',cContestNote:'대회 문제는 단원 구분이 없어 주제를 고르면 빠집니다. 풀이를 확인하고 스스로 채점합니다.',customName:'내 세트',
      reviewIntro:'틀린 문제와 힌트를 보고서야 맞힌 문제는 1일, 3일, 7일, 21일 뒤에 다시 나옵니다. 복습에서 맞히면 다음 간격으로 넘어가고, 틀리면 1일부터 다시 시작합니다.',dueToday:'오늘 복습',inQueue:'복습 대기',startReview:'복습 시작',noDue:'오늘 복습할 문제가 없습니다.',nextDue:'다음 복습',dueCard:'오늘 복습할 문제가 있습니다',
      laterTitle:'나중에 풀기',later:'나중에 풀기',laterOn:'저장됨',noLater:'저장한 문제가 없습니다. 문제 아래의 "나중에 풀기"를 누르면 여기에 모입니다.',startLater:'저장한 문제 풀기',removeLater:'빼기',
      report:'문제 신고',reportTitle:'이 문제에서 무엇이 잘못됐나요?',rWrongAnswer:'정답이 틀림',rTypo:'오타',rFigure:'그림',rTranslation:'번역',rOther:'기타',reportNote:'자세히 적어 주세요 (선택)',reportSend:'신고 보내기',reportCancel:'닫기',reportSent:'메일 앱에 신고 내용이 채워집니다. 열리지 않으면 이 주소로 보내 주세요:',myReports:'내 신고',noReports:'아직 보낸 신고가 없습니다.',reportPick:'무엇이 잘못됐는지 고르세요.',
      avgTime:'평균 풀이 시간',vsSuggested:'권장',strike:'이 보기 지우기',unstrike:'이 보기 되살리기',
      settings:'진도 관리',exportP:'진도 내보내기',importP:'불러오기',resetP:'초기화',resetConfirm:'이 기기의 진도를 모두 지울까요? 되돌릴 수 없습니다. 계정에 저장된 기록은 남습니다.',importDone:'불러왔습니다. 문제마다 더 최근 기록을 남겼습니다.',resetDone:'이 기기의 진도를 지웠습니다.',imp_not_json:'JSON 파일이 아닙니다.',imp_not_backup:'하슬라랩 진도 파일이 아닙니다.',imp_version:'이 페이지에서 읽을 수 없는 버전입니다.',imp_empty:'파일에 불러올 기록이 없습니다.',settingsNote:'진도는 이 기기에 저장됩니다. 파일로 내보내 두면 다른 브라우저로 옮기거나 나중에 되살릴 수 있습니다. 복습 목록과 나중에 풀기는 계정에 저장되지 않으니 파일로 옮기세요.',
      dHas:'이 문제에 쓰던 풀이가 있습니다',dHome:'쓰던 풀이가 있습니다',dPages:'페이지',dPad:'패드',dResume:'이어서 쓰기',dDrop:'지우기',dSaved:'이 기기에 자동 저장됩니다',
      wSendRead:'풀이 보내기',wReadTitle:'이렇게 읽었습니다. 틀린 곳을 고친 뒤 채점하세요.',wReadNote:'읽을 때 오늘 채점 1회가 쓰이고, 채점할 때는 더 쓰이지 않습니다. 읽은 내용은 1시간 동안 채점할 수 있습니다.',wGradeBtn:'채점하기',wReread:'다시 읽기',
      wConf:'확신',wLowConf:'확신 낮음 · 직접 확인해 보세요',wExpired:'읽은 지 1시간이 지났습니다. 풀이를 다시 보내 주세요.',wChanged:'고친 내용이 너무 많습니다. 잘못 읽은 글자만 고칠 수 있고, 사진에 없는 풀이는 더할 수 없습니다.',wUsed:'이 읽기는 이미 채점했습니다. 풀이를 다시 보내 주세요.',wEmptyT:'읽은 내용이 비어 있습니다.',
      apBtn:'이의 제기',apNote:'무엇이 잘못됐는지 한 줄 (적지 않아도 됩니다)',apSend:'보내기',apCancel:'취소',apStatus_open:'이의 제기 · 검토 중',apStatus_upheld:'이의 제기 · 점수 유지',apStatus_changed:'이의 제기 · 점수 바뀜',apExists:'이미 이의 제기한 채점입니다.',apFail:'보내지 못했습니다. 잠시 뒤에 다시 시도하세요.',
      apMine:'내 이의 제기',apNone:'이의 제기한 채점이 없습니다. 채점 결과 아래 "이의 제기"를 누르면 여기에 나옵니다.',apLogin:'로그인하면 이의 제기와 그 결과를 볼 수 있습니다.',apReply:'답변',
      skTitle:'연속 기록',skFreezeLeft:'이번 주 쉬는 날 1번 남음',skFreezeUsed:'이번 주 쉬는 날 씀',skFreezeNote:'하루를 건너뛰어도 한 주에 한 번은 연속 기록이 이어집니다. 매주 월요일에 다시 생깁니다.',skPause:'시험 기간 · 쉬기',
      skPauseNote:'켜 두면 최대 14일 동안 연속 기록이 멈춥니다. 문제는 그대로 풀 수 있습니다.',skPausedUntil:'쉬는 중 · {d}까지',skPauseWait:'다음 쉬기는 {d}부터 켤 수 있습니다.',skNoHearts:'틀려도 잃는 것은 없습니다. 하트나 에너지 같은 제한이 없습니다.',skClose:'닫기',
      icCovers:'이 단원에서 배우는 것',icFormula:'핵심 식',icGuide:'개념 정리 읽기',icSim:'개념 시뮬레이션 해 보기',icStart:'문제 풀기',icSkip:'건너뛰기',
      note:'문항 출처: 한국교육과정평가원, 서울특별시교육청, 경기도교육청, 인천광역시교육청 (웹·앱 배포 허가 범위 안에서 제공). 단원 분류 일부는 자동 분류이며 검수 중입니다. 기록은 이 기기에 저장되고, 로그인하면 계정에도 저장되어 다른 기기에서 이어집니다.'},
    en:{
      lvTitle:'Level',lvPick:'What do you want to practise?',lvIntro:'Your level decides where today’s problems and the set builder’s default source come from. You can change it at any time.',lvHas:'In the bank',lvSoon:'coming',lvChange:'Change',lvCurrent:'Your level',lvBankNote:'Textbook and university problems are in the Books & university tab.',ob_stage:'Which level do you want to start at?',quickIntro:'Pick one and the first problem opens. No account needed; you can change the level at any time.',
      wTitle:'Show your working',wIntro:'Solve on paper and take a photo, write on the pad, or upload a file. It is marked against a rubric.',wRule:'70% or more passes and moves you on. 40–69% is partial credit: the problem goes into your review queue and you move on. Below 40% you can look at a hint and try again, or move on.',
      wPhoto:'Photo',wPad:'Pad',wFile:'File',wTake:'Take or choose a photo',wFilePick:'Choose an image or a PDF',wPdfNote:'A PDF is sent as images of its first four pages.',wPdfFail:'This PDF could not be read. Upload the pages as photos.',wImgFail:'This file cannot be read as an image.',
      wPen:'Pen',wEraser:'Eraser',wThin:'Thin',wMid:'Medium',wThick:'Thick',wUndo:'Undo',wClear:'Clear',wAddPage:'Add as a page',wPages:'Pages to send',wRemove:'Remove',wMax:'You can send up to four pages.',wNone:'Nothing to send yet. Add a photo or write on the pad.',
      wSend:'Mark my working',wReading:'Reading',wGrading:'Marking',wLogin:'Marking needs an account. Ten markings a day are free.',wSoon:'The marking server is not ready yet. Your working stays here; send it again a little later.',
      wLimit:'You have used today’s markings. More tomorrow.',wUnreadable:'The writing could not be read. Take the photo again in better light. This did not use a marking.',wFail:'Marking is not available right now. Try again in a moment. This did not use a marking.',wBad:'Check what you sent.',
      wLeft:'Markings left today',wTranscript:'What was read',wAiNote:'AI marking can be wrong. If something looks off, report the problem.',wRubric:'Rubric',wPoints:'Points',
      bandPass:'Pass',bandPartial:'Partial credit',bandRetry:'Try again',wRetry:'Try again',wMoveOn:'Move on',wLast:'Last marked',wNoText:'This problem is only in the PDF, so it cannot be marked from your working.',wUnitUp:'Up one step in this unit',wPassNote:'Passed. On to the next problem.',wPartialNote:'Partial credit. It is in your review queue.',wRetryNote:'Look at the hint and try again.',wRetryPlain:'Fix your working and send it again.',wOpen:'✎ Show your working',
      rSentOk:'Report sent. When it is fixed, the status changes under My reports.',rQueued:'Could not send it now, so it is kept on this device and sent again when you are online.',rLimit:'No more reports today. Send it again tomorrow.',rStatus_open:'received',rStatus_fixed:'fixed',rStatus_rejected:'declined',rStatus_pending:'sending',
      moreProblems:'Ten more',typeNumber:'Type a number (e.g. 12.5, 3e8)',typeFormula:'Type a formula (e.g. 2*sqrt(gL))',answer:'Answer',keypad:'Math keypad',typeHelp:'You can leave out ×: 2mg works. ^ for powers, a⁄b for a fraction, ×10ⁿ for powers of ten.',notYet:'Finish the expression',onlyNumber:'Numbers only',unknownVar:'Not in this problem',showChoices:'Show the choices (counts as a hint)',ob_region:'Where do you study?',ob_level:'Where are you now?',ob_goal:'What are you studying for?',ob_oly:'How far have you got in olympiads?',ob_daily:'Pick a daily goal',
      obKr:'AP Physics, calculation problems from Korean exams, olympiads',obIn:'JEE Main and Advanced',obUs:'AP Physics, F=ma and the USAPhO',obGlobal:'AP Physics and international olympiad prep',
      goSchool:'School physics',goExam:'An entrance or AP exam',goOly:'Physics olympiad',goCurious:'Just curious',oly0:'Starting out',oly1:'I have sat a first round',oly2:'I have reached a national final or beyond',
      perDay:'problems',tabLeague:'League',goalTitle:'Daily goal',goalToday:'Today',goalSave:'Save',goalSaved:'Saved.',goalFailed:'Could not save. Please try again.',goalMember:'Saved to your account. Today’s goal is fixed by your first right answer of the day; a new goal counts from the next day.',goalGuest:'Saved on this device only. Sign in to get bonus league XP on the days you reach it.',goalMet:'Goal reached',goalMetGuest:'Sign in to get +{n} XP',goalTomorrow:'{n} from tomorrow',goalNext:'Next',goalOpen:'Change your daily goal',goalLeft:'{n} to go',lfAsk:'Set your country and daily goal',lfAskSub:'Asked once. They set your default exams and daily goal, and you can change them in Settings.',lfSave:'Save',lfLater:'Later',lfPick:'Choose a country and a daily goal.',lfFailed:'Could not save. Please try again.',leagueFailed:'Could not load the league.',back:'Back',obDone:'Your starting step',obNext:'Every unit starts at this step and your first problems come from the exams above. A 12-problem level check can tune it further.',
      editProfile:'Settings',myExams:'Your exams',otherExams:'Other exams',dailyGoal:'today',
      tabClass:'Class',classIntro:'Join your teacher’s class with its six-letter code and your assignments appear here. Teachers can make a class, set AP and JEE problems as assignments, and see each student’s units and progress.',myAssignments:'My assignments',noAssignments:'No assignments yet.',classCode:'Class code',join:'Join',leave:'Leave',leaveConfirm:'Leave this class?',teach:'Teach',students:'students',className:'Class name',newClass:'Make a class',classFree:'Free: one class of up to 30 students. Students share only their Learn practice with the class.',due:'due',shareCode:'Give your students the class code. They enter it in the Class tab of Practice to join.',student:'Student',answered:'Answered',lastActive:'Last active',remove:'Remove',removeConfirm:'Remove this student from the class?',noStudents:'No students yet.',newAssignment:'Set an assignment',allOf:'All',assign:'Assign',closeClass:'Close class',closeConfirm:'Close this class? Students will no longer see its assignments.',
      cl_bad_name:'Enter a class name.',cl_class_limit:'A free account can have one class.',cl_bad_code:'A code has six letters.',cl_class_not_found:'No class has that code.',cl_own_class:'That is your own class.',cl_class_full:'This class is full.',cl_bad_items:'Pick problems.',cl_bad_due:'Check the due date.',cl_rate_limited:'Try again in a moment.',
      tabTracks:'By exam',trackPick:'Pick an exam and a unit to solve ten problems in that exam’s style. Every problem is written by HaslaLab.',mixed:'All units mixed',numPh:'Answer (number)',check:'Check',notNumber:'Enter a number (e.g. 3.2, 1.5e3, 2×10^4)',hint:'Hint',tutor:'AI tutor',discuss:'Discuss',seeDiscuss:'Questions about this problem',newDiscuss:'Ask about it',byHasla:'Original problem by HaslaLab',
      tutorLogin:'Log in to use the AI tutor: five free questions a day.',login:'Log in',tutorPh:'Where are you stuck?',tutorSend:'Ask',thinking:'Thinking…',tutorLimit:'Today’s free questions are used up. More tomorrow.',tutorFail:'The tutor cannot answer right now. Try again in a moment.',tutorLeft:'Questions left today',aiNote:'AI answers can be wrong.',
      aiTranslated:'AI translation',showOriginal:'Show original',showTranslation:'Show translation',translating:'Translating…',withHints:'with hints',
      diagTitle:'Find your level',diagBody:'Solve twelve problems, two per area (about 10 minutes), and every unit gets a starting step. You can skip this and start right away.',diagStart:'Find my level',diagDone:'Your starting steps are set. Today’s picks now come from those steps.',
      lvBeginner:'Beginner',lvFamiliar:'Familiar',lvProficient:'Proficient',lvMaster:'Master',tier:'XP tier',
      noteTracks:'AP and JEE problems are original problems written by HaslaLab in each exam’s style. AP and Advanced Placement are trademarks of College Board; HaslaLab is not affiliated with College Board or the NTA. Progress is kept on this device and, when you log in, on your account too.',
      title:'Practice',streak:'day streak',xp:'XP',solved:'solved',pick:'Pick a unit to solve ten problems at your step.',
      none:'No problems yet',step:'Step',start:'Start',again:'Again',units:'Units',next:'Next',finish:'See results',
      right:'Correct.',wrong:'Incorrect. The answer is',up:'Up one step',down:'Back one step',
      result:'Correct',of:'/',done:'Session complete',loading:'Loading problems…',failed:'Could not load the problems.',retry:'Retry',
      pdf:'Original paper',quit:'← Back',time:'Suggested time',sec:'s',progress:'solved',skip:'Skip',skipped:'skipped',
      tabUnits:'By unit',calcName:'Calculation problems from Korean exams',noteUnits:'Each unit mixes HaslaLab’s original problems (in the style of AP, JEE, F=ma and the USAPhO) with calculation problems from Korean school exams (Korea Institute for Curriculum and Evaluation and the Seoul, Gyeonggi and Incheon education offices, shared within the permitted web and app use; shown in English as an AI translation). Progress is kept on this device and, when you log in, on your account too.',synced:'Saved to your account',tabToday:'Today',todayTitle:'Today’s ten',whyReview:'review',whyWeak:'weak unit',whyStretch:'stretch',whyNew:'new unit',focus:'focus',startToday:'Start',mySkills:'Your units',unit:'Unit',accuracy:'Correct',noSkills:'A unit gets a rating once you solve problems in it. The more you solve, the better the picks fit.',syncFailed:'Not saved · retrying',loginToSave:'Log in to keep your progress on your account →',tabBank:'Books & university',tabContest:'Competition problems',
      bankPick:'Pick a field and a difficulty to work through textbook and university course problems one at a time. Check the solution and mark yourself.',stars:'Difficulty',showSol:'Show solution',noSol:'No solution yet. Ask in the community Q&A gallery, or ask the AI.',
      solvedIt:'I solved it',missedIt:'I missed it',original:'Original',translated:'Translation',noKo:'',draft:'HaslaLab draft solution · not yet reviewed',refFig:'Reference figures',empty:'No more problems here. Try another difficulty or field.',
      contestPick:'Pick a competition to get its problems one at a time. Solve from the PDF, check the solution and mark yourself.',paper:'Problem',solution:'Solution',noContestSol:'This problem has no official solution.',problems:'problems',another:'Another problem',figInPdf:'The figures are in the original PDF below.',transcribed:'The text is transcribed from the original paper; if they differ, the PDF is authoritative.',noteBank:'Each problem shows its source (textbook or university course). Translations and HaslaLab draft solutions are under review. Progress is kept on this device and, when you log in, on your account too.',noteContest:'Official problems and solutions of each competition; Korean versions are HaslaLab translations. Progress is kept on this device and, when you log in, on your account too.',
      tabReview:'Review',tabCustom:'Build a set',noteCustom:'Sets, the review queue and saved problems are kept on this device. Answers and unit ratings also go to your account when you log in.',
      customIntro:'Choose the source, topics, difficulty and number of problems yourself. Among the problems that match, ones you have not solved or seen lately come first.',cSource:'Source',cAll:'Everything',cCalc:'Korean school exams',cContest:'Competition problems',cTopics:'Topics',cAllTopics:'All',cPickUnits:'Pick single units',cDiff:'Difficulty (step)',cCount:'Problems',cFormat:'Answer by',cChoice:'Picking a choice',cTyped:'Typing it',cFormatNote:'Typing keeps only problems whose answer is a number or a formula.',cCompetition:'Competition',cAnyContest:'All competitions',cYears:'Years',cTimer:'Time each problem',cMatch:'Problems that match',cStartSet:'Start the set',cNoMatch:'Nothing matches. Widen the filters.',cContestNote:'Competition problems have no unit, so picking topics leaves them out. You check the solution and mark them yourself.',customName:'My set',
      reviewIntro:'Problems you missed, or got right only with hints, come back after 1, 3, 7 and 21 days. A right answer on review moves a problem to the next gap; a miss starts it again at 1 day.',dueToday:'Due today',inQueue:'In the queue',startReview:'Start review',noDue:'Nothing is due today.',nextDue:'Next review',dueCard:'Problems are due for review today',
      laterTitle:'Saved for later',later:'Save for later',laterOn:'Saved',noLater:'Nothing saved yet. Tap "Save for later" under a problem to keep it here.',startLater:'Solve saved problems',removeLater:'Remove',
      report:'Report',reportTitle:'What is wrong with this problem?',rWrongAnswer:'Wrong answer',rTypo:'Typo',rFigure:'Figure',rTranslation:'Translation',rOther:'Other',reportNote:'Details (optional)',reportSend:'Send report',reportCancel:'Close',reportSent:'Your mail app opens with the report filled in. If it does not, send it to:',myReports:'My reports',noReports:'No reports yet.',reportPick:'Pick what is wrong.',
      avgTime:'Average time',vsSuggested:'suggested',strike:'Cross out this choice',unstrike:'Bring this choice back',
      settings:'Progress backup',exportP:'Export progress',importP:'Import',resetP:'Reset',resetConfirm:'Clear all progress on this device? This cannot be undone. Progress saved on your account stays.',importDone:'Imported. For each problem the newer record was kept.',resetDone:'Progress on this device is cleared.',imp_not_json:'That is not a JSON file.',imp_not_backup:'That is not a HaslaLab progress file.',imp_version:'This page cannot read that file’s version.',imp_empty:'The file has no progress to import.',settingsNote:'Progress is kept on this device. Export it to a file to move it to another browser or restore it later. The review queue and saved problems are not stored on your account, so move them with a file.',
      dHas:'You have unsent working for this problem',dHome:'You have unsent working',dPages:'pages',dPad:'pad',dResume:'Continue',dDrop:'Discard',dSaved:'Saved on this device as you go',
      wSendRead:'Send my working',wReadTitle:'This is what we read. Fix anything misread, then mark it.',wReadNote:'Reading uses one of today’s markings; marking it uses no more. A reading can be marked for an hour.',wGradeBtn:'Mark it',wReread:'Read again',
      wConf:'Confidence',wLowConf:'Low confidence · check it yourself',wExpired:'This reading is over an hour old. Send your working again.',wChanged:'Too much was changed. You can fix misread symbols, but not add working that is not on the page.',wUsed:'This reading has already been marked. Send your working again.',wEmptyT:'The reading is empty.',
      apBtn:'Appeal',apNote:'What looks wrong, in one line (optional)',apSend:'Send',apCancel:'Cancel',apStatus_open:'Appeal · under review',apStatus_upheld:'Appeal · score kept',apStatus_changed:'Appeal · score changed',apExists:'You have already appealed this marking.',apFail:'Could not send. Try again in a moment.',
      apMine:'My appeals',apNone:'No appeals yet. Tap "Appeal" under a marking result and it shows here.',apLogin:'Log in to see your appeals and their results.',apReply:'Reply',
      skTitle:'Streak',skFreezeLeft:'1 free day left this week',skFreezeUsed:'This week’s free day is used',skFreezeNote:'Miss a day and the streak still holds, once a week. The free day comes back every Monday.',skPause:'Exam time · take a break',
      skPauseNote:'While on, the streak is held for up to 14 days. You can still practise.',skPausedUntil:'On a break until {d}',skPauseWait:'You can take the next break from {d}.',skNoHearts:'Mistakes cost nothing here. There are no hearts or energy limits.',skClose:'Close',
      icCovers:'What this unit covers',icFormula:'Key formula',icGuide:'Read the guide chapter',icSim:'Try the concept simulation',icStart:'Start problems',icSkip:'Skip',
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
  const H=window.HL_PRACTICE_TOOLS;
  /* review, later and recent stay on this device: the account's state (community/src/practice-progress.js) keeps
     only the fields it knows, so they travel in the exported file instead */
  const fill=v=>{v.solved||={};v.level||={};v.xp||=0;v.days||=[];v.skills||={};v.queue||=[];v.wrong||={};v.bank||={done:{},stars:{}};v.contest||={done:{}};v.review||={};v.later||={};v.recent||={};v.graded||={};v.gradedHist||={};v.streakCfg||={pauses:[]};v.intro||={};v.appeals||={};return v;};
  let saved=fill(store.read());
  const save=()=>store.write(saved);

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
    /* the daily goal counts problems got right (or marked solved), each once a day, as the server's league does */
    if(result==='right'||result==='solved'){const d=today();if(saved.goalDay?.d!==d||!Array.isArray(saved.goalDay.ids))saved.goalDay={d,n:saved.goalDay?.d===d?saved.goalDay.n|0:0,ids:[]};
      if(!saved.goalDay.ids.includes(item_id)){const before=goalNow();saved.goalDay.ids.push(item_id);saved.goalDay.n++;goalCrossed(before);}}
    saved.queue.push({item_id,mode,unit,step,result,at});if(saved.queue.length>500)saved.queue=saved.queue.slice(-500);
    save();scheduleSync();
  }
  /* the merge rule lives in practice-tools.js (accountMerge), where the tests check a first sign-in carries a guest's progress over */
  const mergeState=H.accountMerge;
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
      /* a server not yet updated knows only the first three modes: the rest wait in the queue until it is */
      const sendable=a=>!state.serverOld||(['exam','bank','contest'].includes(a.mode)&&a.result!=='place');
      for(let batch;(batch=saved.queue.filter(sendable).slice(0,50)).length;){
        let r;try{r=await api('/api/practice/attempts','POST',{attempts:batch});}
        catch(e){if(!state.serverOld&&/api 400/.test(e.message)){state.serverOld=true;continue;}throw e;}
        if(r.league_today){state.today={...(state.today||{}),...r.league_today};state.todayAt=today();}
        if(r.goal_bonus>0){state.today={...(state.today||{}),earned:true,earned_xp:r.goal_bonus};goalMoment(r.goal_bonus);}
        const sent=new Set(batch);saved.queue=saved.queue.filter(a=>!sent.has(a));saved.skills=state.serverOld?H.skillsMerge(saved.skills,r.skills):{...saved.skills,...Object.fromEntries((r.skills||[]).map(k=>[k.unit,k]))};save();
      }
      const r=await api('/api/practice/state','POST',{state:stateOf()});Object.assign(saved,mergeState(stateOf(),r.state));save();state.sync='saved';
    }catch(e){state.sync='error';setTimeout(scheduleSync,30000);}
    syncing=false;paintStats();
  }
  /* on opening: the account's state and ratings join this device's, then anything queued here is sent */
  async function pull(){
    if(!token())return;
    try{const r=await api('/api/practice/state');Object.assign(saved,mergeState(stateOf(),r.state));saved.skills=H.skillsMerge(saved.skills,r.skills);save();state.sync='saved';}catch(e){state.sync='error';}
    paintStats();scheduleSync();
  }
  /* signing in on another tab (or the site around this frame) sets the token: this browser's progress joins the account then */
  addEventListener('storage',e=>{if(e.key==='hlCmTok'){state.sync=token()?'pending':'local';if(token())pull();else paintStats();}});
  const today=()=>new Date().toLocaleDateString('sv');   /* YYYY-MM-DD in local time */
  /* today not yet studied keeps the streak; a missed day uses the week's free day; a pause holds it (practice-tools.js) */
  const streakNow=()=>H.streakInfo(saved.days,saved.streakCfg,today());
  const streak=()=>streakNow().n;
  function reportHeight(){if(embedded)requestAnimationFrame(()=>window.parent.postMessage({type:'hl-practice-height',height:Math.ceil(document.querySelector('main').getBoundingClientRect().bottom+scrollY+12)},location.origin));}
  function tellUnit(unit){if(embedded&&!document.documentElement.classList.contains('play'))window.parent.postMessage({type:'hl-practice-unit',unit:unit||''},location.origin);}
  function math(latex,display){try{return window.katex?katex.renderToString(latex,{displayMode:!!display,throwOnError:false,strict:false}):esc(latex);}catch(e){return esc(latex);}}
  function blocks(list){
    return list.map(b=>{
      if(b.p)return '<p>'+b.p.map(s=>s.m!==undefined?math(s.m):esc(s.t||'')).join('')+'</p>';
      if(b.mb!==undefined)return '<div class="mb">'+math(b.mb,true)+'</div>';
      if(b.f)return `<figure><img src="practice/fig/${encodeURIComponent(b.f)}" width="${b.w}" height="${b.h}" alt="${esc(b.alt||'')}" loading="lazy"></figure>`;
      return '';
    }).join('');
  }
  const unitPlace=u=>u.startsWith('contest/')?nameOf(state.contests?.find(c=>'contest/'+c.key===u)?.name)||u.slice(8):unitName(u);
  const itemPlace=i=>i.kind==='contest'?unitPlace(i.u)+(i.year?' '+i.year:''):unitName(i.u);
  const unitName=key=>{const e=P.SUBTOPICS.get(key);return e?(state.lang==='ko'?e.sub.name.ko:tx(e.sub.name.en)):key;};
  const areaName=a=>state.lang==='ko'?a.name.ko:tx(a.name.en);
  function paintStats(){
    const solvedCount=Object.keys(saved.solved).length;
    const badge=state.sync==='saved'?`<span class="stat sync ok">☁ ${tr('synced')}</span>`:state.sync==='error'?`<span class="stat sync">⚠ ${tr('syncFailed')}</span>`:state.sync==='local'?`<a class="stat sync" href="/#/login" target="_top">${tr('loginToSave')}</a>`:'';
    const tier=tierOf(saved.xp),sk=streakNow();
    $('stats').innerHTML=`<span class="stat tier t-${tier[1].toLowerCase()}" title="${tr('tier')}"><b>◆</b>Lv.${TIERS.indexOf(tier)+1}</span><button type="button" class="stat fire${sk.pause?' paused':''}" id="streakBtn" aria-expanded="${!!state.streakOpen}" aria-controls="streakPanel"><b>🔥 ${sk.n}</b>${tr('streak')}<small class="sksub">${sk.pause?esc(tr('skPausedUntil').replace('{d}',shortDay(sk.pause.to))):tr(sk.freezeLeft?'skFreezeLeft':'skFreezeUsed')}</small></button><span class="stat"><b>${saved.xp}</b>${tr('xp')}</span>${goalStat()}<span class="stat"><b>${solvedCount}</b>${tr('solved')}</span>${badge}`;
    $('stats').insertAdjacentHTML('beforeend',state.streakOpen?streakPanel(sk):'');
    $('streakBtn').onclick=()=>{state.streakOpen=!state.streakOpen;paintStats();reportHeight();};
    $('goalBtn').onclick=()=>{state.goalOpen=!state.goalOpen;paintStats();paintGoalPanel();reportHeight();};
    if($('skPause'))$('skPause').onchange=e=>{
      const next=e.target.checked?H.pauseStart(saved.streakCfg,today()):H.pauseStop(saved.streakCfg,today());
      if(next){saved.streakCfg=next;save();}paintStats();reportHeight();
    };
    if($('skClose'))$('skClose').onclick=()=>{state.streakOpen=false;paintStats();reportHeight();};
  }
  const shortDay=d=>{const [,m,dd]=d.split('-').map(Number);return state.lang==='ko'?`${m}월 ${dd}일`:new Date(Date.UTC(2000,m-1,dd)).toLocaleDateString('en',{month:'short',day:'numeric',timeZone:'UTC'});};
  /* the streak's two safety nets, said plainly next to it */
  function streakPanel(sk){
    const last=(saved.streakCfg?.pauses||[]).slice(-1)[0],waitTo=last?H.addDays(last.to,H.PAUSE_GAP+1):'';
    return `<section class="skpanel" id="streakPanel"><div class="skrow"><b>${tr('skTitle')} ${sk.n}</b><button type="button" class="mini quiet" id="skClose">${tr('skClose')}</button></div>
      <p><span class="tag${sk.freezeLeft?' ok':''}">${tr(sk.freezeLeft?'skFreezeLeft':'skFreezeUsed')}</span> ${tr('skFreezeNote')}</p>
      <label class="switch"><input type="checkbox" id="skPause"${sk.pause?' checked':''}${sk.pause||sk.canPause?'':' disabled'}><span>${tr('skPause')}</span></label>
      <p class="src">${sk.pause?esc(tr('skPausedUntil').replace('{d}',shortDay(sk.pause.to)))+' · ':''}${tr('skPauseNote')}${!sk.pause&&!sk.canPause&&waitTo?' '+esc(tr('skPauseWait').replace('{d}',shortDay(waitTo))):''}</p>
      <p class="src">${tr('skNoHearts')}</p></section>`;
  }
  /* ── the daily goal: a ring on the goal stat; tapping it opens a small panel with the stepper (learner-form.js) and
     Save. Members save to the account (PUT /api/me/learner), guests on this device. When the day's counted problems
     reach it, the member gets a one-time bonus from the server (league.js goalBonus) and the page shows it. ── */
  const LF=()=>window.HL_LEARNER_FORM;
  const goalLocal=()=>saved.goalDay?.d===today()?saved.goalDay.n|0:0;
  const serverToday=()=>token()&&state.today&&state.todayAt===today()?state.today:null;
  function goalNow(){
    const srv=serverToday(),g=srv?.goal||dailyGoal()||LF()?.DEFAULT_GOAL||10;
    const n=Math.max(goalLocal(),srv?.counted||0);
    return {n,g,met:n>=g,earned:!!srv?.earned,bonus:srv?(srv.earned?srv.earned_xp||srv.bonus_xp:srv.bonus_xp):LF()?LF().goalBonus(g):0,next:srv?.next_goal||0};
  }
  function goalRing(n,g){
    const r=8,c=2*Math.PI*r,f=Math.max(0,Math.min(1,g?n/g:0));
    return `<svg class="goalring" viewBox="0 0 20 20" width="20" height="20" aria-hidden="true"><circle cx="10" cy="10" r="${r}"/><circle class="on" cx="10" cy="10" r="${r}" stroke-dasharray="${(c*f).toFixed(2)} ${c.toFixed(2)}" transform="rotate(-90 10 10)"/></svg>`;
  }
  function goalStat(){
    const G=goalNow();
    return `<button type="button" class="stat goal${G.met?' met':''}" id="goalBtn" aria-expanded="${!!state.goalOpen}" aria-controls="goalPanel" title="${esc(tr('goalOpen'))}">${goalRing(G.n,G.g)}<b>${Math.min(G.n,G.g)}/${G.g}</b>${tr('dailyGoal')}<small class="sksub">${G.met?esc(tr('goalMet'))+(G.earned?' +'+G.bonus+' XP':''):esc(tr('goalLeft').replace('{n}',G.g-G.n))+' · +'+G.bonus+' XP'}</small></button>`;
  }
  /* the panel lives outside #stats, so repainting the stats never resets a value being chosen */
  function paintGoalPanel(){
    let box=$('goalBox');if(!box){box=document.createElement('div');box.id='goalBox';$('stats').after(box);}
    const lf=LF();if(!state.goalOpen||!lf){box.innerHTML='';return;}
    lf.addStyle(document);
    const member=!!token(),needCountry=member&&state.learnerDone&&!state.learner,G=goalNow(),cur=dailyGoal()||lf.DEFAULT_GOAL;
    box.innerHTML=`<section class="skpanel goalpanel" id="goalPanel" aria-labelledby="goalPanelH"><div class="skrow"><b id="goalPanelH">${tr('goalToday')} ${Math.min(G.n,G.g)}/${G.g} <small class="src">${G.met?esc(tr('goalMet')):'+'+G.bonus+' XP'}</small></b><button type="button" class="mini quiet" id="goalClose">${tr('skClose')}</button></div>
      <form id="goalForm">${needCountry?lf.fieldsHtml(state.lang,{daily_goal:cur}):lf.goalHtml(state.lang,cur)}<div class="actions start"><button type="submit" class="primary">${tr('goalSave')}</button><span class="src" id="goalMsg" role="status"></span></div></form>
      <p class="src">${tr(member?'goalMember':'goalGuest')}${G.next?' · '+esc(tr('goalTomorrow').replace('{n}',G.next)):''}</p></section>`;
    const f=$('goalForm'),read=needCountry?lf.wire(f,state.lang):lf.wireGoal(f,state.lang),msg=$('goalMsg');
    $('goalClose').onclick=()=>{state.goalOpen=false;paintStats();paintGoalPanel();reportHeight();};
    f.onsubmit=async e=>{e.preventDefault();const v=read(),g=needCountry?v?.daily_goal:v;if(!g){msg.textContent=tr('lfPick');return;}
      const btn=f.querySelector('button[type=submit]');btn.disabled=true;msg.textContent='';
      try{
        if(member){const r=await api('/api/me/learner','PUT',needCountry?v:{country:state.learner.country,daily_goal:g});state.learner=r&&r.country?r:state.learner;state.learnerMissing=false;loadToday();}
        else{saved.dailyGoal=g;if(saved.profile)saved.profile.daily=g;save();}
        msg.textContent=tr('goalSaved');paintStats();
      }catch(er){msg.textContent=tr('goalFailed');}
      btn.disabled=false;reportHeight();};
  }
  /* the goal reached: a short moment (inside the site, the page around this frame shows it where the learner looks) */
  function goalMoment(xp){
    const guest=!token(),G=goalNow(),line=guest?tr('goalMetGuest').replace('{n}',G.bonus):'';
    if(embedded){window.parent.postMessage({type:'hl-practice-goal',xp:xp|0,goal:G.g,guest,line},location.origin);return;}
    document.querySelector('.goalmoment')?.remove();
    const el=document.createElement('div');el.className='goalmoment';el.setAttribute('role','status');
    el.innerHTML=`${goalRing(1,1)}<b>${tr('goalMet')}${xp?` +${xp} XP`:''}</b>${line?`<small>${esc(line)}</small>`:''}`;
    document.body.append(el);setTimeout(()=>el.classList.add('out'),3600);setTimeout(()=>el.remove(),4200);
  }
  /* a guest's goal is local; a member's bonus is the server's (sync() shows it when the server pays it) */
  function goalCrossed(before){
    const after=goalNow();if(before.met||!after.met)return;
    if(!token()&&!saved.goalDay.met){saved.goalDay.met=true;goalMoment(0);}
  }
  async function loadToday(){
    if(!token())return;
    try{const r=await api('/api/league/me');if(r?.today){state.today=r.today;state.todayAt=today();paintStats();}}catch(e){}
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
    await draftFirst(state.session);
    tellUnit(unit);withIntro(unit,next,home);
  }
  /* after a reload or a crash: the problem with unsent working comes first, with its draft offered back */
  async function draftFirst(s){
    const d=await Drafts.latest().catch(()=>null),it=d&&s.items.find(i=>i.id===d.id);
    if(it&&state.session===s)s.first=it;
  }
  /* ── before a unit's first problems: one short card (what it covers, the key formula, the guide chapter, the concept
     simulation if there is one). Shown once per unit, and never to someone who has already answered there ── */
  function withIntro(unit,go,back){
    const card=H.unitCard(unit);
    if(!card||saved.intro[unit]||saved.skills[unit]?.n>0){go();return;}
    const seen=()=>{saved.intro[unit]=Math.floor(Date.now()/1000);save();};
    $('app').innerHTML=`<section class="session introcard"><div class="shead"><button type="button" class="back" id="quit">${tr('quit')}</button></div>
      <h2>${esc(unitName(unit))}</h2>
      <p class="sublabel">${tr('icCovers')}</p><p>${esc(state.lang==='ko'?card.ko:card.en)}</p>
      <p class="sublabel">${tr('icFormula')}</p><div class="icf">${math(card.f,true)}</div>
      <p class="iclinks"><a href="${H.guideHref(unit)}" target="_top">${tr('icGuide')} →</a>${card.sim?`<a href="${H.simHref(card.sim)}" target="_top">${tr('icSim')} →</a>`:''}</p>
      <div class="actions"><button type="button" class="primary" id="icGo">${tr('icStart')}</button><button type="button" class="linkbtn" id="icSkip">${tr('icSkip')}</button></div></section>`;
    $('quit').onclick=back;
    $('icGo').onclick=()=>{seen();go();};$('icSkip').onclick=()=>{seen();go();};
    $('app').querySelectorAll('.iclinks a').forEach(a=>a.addEventListener('click',seen));
    reportHeight();window.scrollTo?.(0,0);
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
    if(s.n>=setTotal(s)&&!s.diag){summary();return;}
    const item=s.diag?pickDiag(s):pick(s);if(!item){summary();return;}
    s.current=item;s.answered=false;s.usedChoices=false;s.seen.add(item.id);s.n++;
    if(item.kind==='track'){showTrack(item);return;}
    if(item.kind==='contest'){contestShow(item.c,null,item);return;}
    const imageChoices=item.ch.every(c=>!c.c.length);
    $('app').innerHTML=`<div class="session">
      ${sessionHead(s,item)}
      <div class="q">${blocks(item.b)}</div>
      <div class="choices${imageChoices?' compact':''}" role="group">${item.ch.map(c=>`<button type="button" class="choice" data-n="${c.n}"><span class="no">${'①②③④⑤'[c.n-1]}</span>${imageChoices?'':`<span>${blocks(c.c).replace(/^<p>|<\/p>$/g,'')}</span>`}</button>`).join('')}</div>
      <div id="feedback"></div>
      ${toolsHtml(item)}
      <div class="foot"><span class="src">${esc(item.src)} · ${esc(item.by)}${item.pdf?` · <a href="${esc(item.pdf)}" target="_blank" rel="noopener noreferrer">${tr('pdf')}</a>`:''}</span><span class="footbtns"><button type="button" id="skip">${tr('skip')}</button><button type="button" class="primary" id="next" hidden>${s.n>=setTotal(s)?tr('finish'):tr('next')}</button></span></div>
    </div>`;
    $('quit').onclick=s.back||(s.fixed?todayHome:home);
    addStrike($('app'));wireTools(item,item.src);startPace(item);
    $('skip').hidden=!!s.diag;
    if(state.lang!=='ko')localizeExam(item);
    $('app').querySelectorAll('.choice').forEach(b=>b.addEventListener('click',()=>answer(Number(b.dataset.n))));
    const free=imageChoices||s.format==='choice'?null:freeOfExam(item);
    if(free){
      const ch=$('app').querySelector('.choices');ch.hidden=true;
      ch.insertAdjacentHTML('afterend',answerBox(free)+`<button type="button" class="linkbtn" id="showch">${tr('showChoices')}</button>`);
      $('showch').onclick=()=>{ch.hidden=false;$('ansbox').remove();$('showch').remove();s.usedChoices=true;reportHeight();};
      wireAnswer(free,ok=>{answer(ok?item.a:0);$('feedback').innerHTML=`<p class="feedback ${ok?'ok':'bad'}">${ok?tr('right'):tr('wrong')+' '+freeAnswerTex(free)}</p>`;$('showch')?.remove();reportHeight();});
    }
    $('next').onclick=next;
    const right=item.ch.find(c=>c.n===item.a);
    wireWritten(item,{source:'exam',mode:'exam',unit:item.u,step:item.s,xpItem:{kind:'exam',s:item.s},open:writtenDefault(false),
      gradeItem:()=>({id:item.id,source:'exam',q:item.b.map(b=>b.p?segText(b.p):b.mb!==undefined?'$$'+b.mb+'$$':b.f?(state.lang==='ko'?'[그림]':'[figure]'):'').filter(Boolean).join('\n\n'),
        answer:right?'①②③④⑤'[item.a-1]+' '+choiceText(right):'',choices:item.ch.map(c=>'①②③④⑤'[c.n-1]+' '+(choiceText(c)||(state.lang==='ko'?'[그림]':'[figure]')))}),
      answered:()=>s.answered,solve:()=>{saved.solved[item.id]=item.u;delete saved.wrong[item.id];},miss:()=>{saved.wrong[item.id]=Math.floor(Date.now()/1000);},
      lock:()=>{s.answered=true;$('app').querySelectorAll('.choice').forEach(b=>b.disabled=true);$('ansbox')?.remove();$('showch')?.remove();$('skip').hidden=true;$('next').hidden=false;reportHeight();}});
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
    const ok=choice===item.a;stopPace(item);noteOutcome(item,ok?(s.usedChoices?'hinted':'right'):'wrong');
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
    clearInterval(paceTick);
    const times=s.times||[],avg=k=>times.reduce((a,x)=>a+x[k],0)/Math.max(1,times.length);
    $('app').innerHTML=`<div class="session summary"><p class="eyebrow">${tr('done')}</p><p class="big">${s.right}${tr('of')}${s.n}</p><p>${tr('result')} · +${s.xp} XP · ${s.mode==='bank'?'★'.repeat(s.stars):s.fixed?esc(s.label||tr('tabToday')):tr('step')+' '+s.level+' · '+tr(LEVELS[levelOf(s.level)])}${s.skipped?` · ${s.skipped} ${tr('skipped')}`:''} · 🔥 ${streak()}${tr('streak')}</p>
      ${times.length?`<p class="pacesum">${tr('avgTime')} <b class="${avg('t')>avg('sug')?'over':''}">${H.clock(avg('t'))}</b> · ${tr('vsSuggested')} ${H.clock(avg('sug'))}</p>`:''}
      <div class="actions"><button type="button" class="primary" id="again">${tr('again')}</button><button type="button" id="units">${tr('units')}</button></div></div>`;
    if(s.unit==='today'&&document.documentElement.classList.contains('play')){$('again').onclick=playHome;$('units').onclick=todayHome;$('again').textContent=tr('moreProblems');reportHeight();return;}
    if(s.custom){$('again').onclick=s.again;$('units').onclick=s.back;$('units').textContent=s.back===customHome?tr('tabCustom'):tr('tabReview');reportHeight();return;}
    if(s.assignment){$('again').onclick=classHome;$('units').onclick=classHome;$('again').textContent=tr('tabClass');reportHeight();return;}
    $('again').onclick=()=>s.fixed?todayHome():s.mode==='bank'?bankStart(s.field,s.stars):s.mode==='track'?trackStart(s.track,s.syl):start(s.unit);$('units').onclick=s.fixed?todayHome:s.mode==='bank'?bankHome:s.mode==='track'?tracksHome:home;reportHeight();
  }


  /* ── modes: Korean exams (graded), books & university (problem bank, self-marked), competitions (PDF, self-marked) ── */
  const BANK_API='https://haslalab-problem-bank.haslalab.workers.dev';
  const PDF_HOST=/^https:\/\/haslalab-pdf\.haslalab\.workers\.dev\/pdf\//;
  const BANK_FIELDS=[['classical_mechanics','고전역학','Classical mechanics'],['electromagnetism','전자기학','Electromagnetism'],['oscillations_waves','진동과 파동','Oscillations and waves'],
    ['optics','광학','Optics'],['thermodynamics','열역학','Thermodynamics'],['statistical_mechanics','통계역학','Statistical mechanics'],['quantum_mechanics','양자역학','Quantum mechanics'],
    ['special_relativity','특수 상대성','Special relativity'],['general_relativity','일반 상대성','General relativity'],['mathematical_methods','수리물리','Mathematical methods']];
  const BANK_AREA={classical_mechanics:'mechanics',electromagnetism:'em',oscillations_waves:'waves',optics:'optics',thermodynamics:'thermal',statistical_mechanics:'thermal',quantum_mechanics:'modern',special_relativity:'modern',general_relativity:'modern',mathematical_methods:'math'};
  function studied(xp){saved.xp+=xp;if(!saved.days.includes(today())){saved.days.push(today());saved.days=saved.days.slice(-400);}save();paintStats();}
  function paintTabs(){
    /* no unit tab: the first-visit answers already say what to practise; a unit still opens from the unit map (?unit=) */
    const due=dueNow().length;
    $('tabs').innerHTML=[['today',tr('tabToday')],['review',tr('tabReview')+(due?` <b class="badge">${due}</b>`:'')],['league',tr('tabLeague')],['custom',tr('tabCustom')],['tracks',tr('tabTracks')],['bank',tr('tabBank')],['contest',tr('tabContest')],['class',tr('tabClass')]].map(([k,l])=>`<button type="button" role="tab" data-mode="${k}" aria-selected="${state.mode===k}">${l}</button>`).join('');
    $('tabs').querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>MODES[b.dataset.mode]());
    $('note').textContent=tr(state.mode==='bank'?'noteBank':state.mode==='contest'?'noteContest':state.mode==='exam'?'noteUnits':state.mode==='custom'||state.mode==='review'?'noteCustom':'noteTracks');
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
      <div class="shead"><button type="button" class="back" id="quit">${tr('quit')}</button><span class="unitname">${esc(state.lang==='ko'?label[1]:tx(label[2]))}</span><span class="lvl">${'★'.repeat(s.stars)}</span><span class="progress" aria-hidden="true"><i style="width:${Math.round(100*(s.n-1)/5)}%"></i></span><span>${s.n}/5</span>${paceHtml({id:pick.id,s:P.stepFromStars(s.stars)})}</div>
      ${v.missing?`<p class="src">${tr('noKo')}</p>`:''}<div class="q" id="qtext">${textHtml(v.main?.text)}</div>
      ${v.alt?`<details class="alt"><summary>${tr('original')}</summary><div class="q" id="qalt">${textHtml(v.alt.text)}</div></details>`:''}
      ${figs.filter(a=>a.placement!=='reference').map(fig).join('')}
      ${figs.some(a=>a.placement==='reference')?`<details class="alt"><summary>${tr('refFig')}</summary>${figs.filter(a=>a.placement==='reference').map(fig).join('')}</details>`:''}
      <div id="sol"></div><div id="feedback"></div>
      ${toolsHtml(pick,{noLater:true})}
      <div class="foot"><span class="src">${esc(pick.source_title||'')}${item.original_number?' · '+esc(item.original_number):''}</span>
        <span class="footbtns"><button type="button" id="skip">${tr('skip')}</button><button type="button" id="showSol">${tr('showSol')}</button><button type="button" class="primary" id="good">${tr('solvedIt')}</button><button type="button" id="miss">${tr('missedIt')}</button><button type="button" class="primary" id="next" hidden>${s.n>=5?tr('finish'):tr('next')}</button></span></div></div>`;
    typeset($('app'));
    $('quit').onclick=bankHome;startPace({id:pick.id,s:P.stepFromStars(s.stars)});wireTools(pick,(pick.source_title||'')+(item.original_number?' · '+item.original_number:''));
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
    const mark=ok=>{if(s.answered)return;s.answered=true;stopPace(pick);
      record(pick.id,'bank',bankUnit,bankStep,ok?'solved':'missed');
      if(ok){s.right++;const gain=10+5*s.stars;s.xp+=gain;saved.bank.done[pick.id]=1;studied(gain);}else{saved.bank.done[pick.id]=0;studied(2);}
      ['good','miss','skip'].forEach(id=>$(id).hidden=true);$('next').hidden=false;$('next').focus();
      $('feedback').innerHTML=`<p class="feedback ${ok?'ok':'bad'}">${ok?'✓ '+tr('solvedIt'):tr('missedIt')}</p>`;reportHeight();};
    $('good').onclick=()=>mark(true);$('miss').onclick=()=>mark(false);$('next').onclick=bankNext;
    wireWritten(pick,{source:'bank',mode:'bank',unit:bankUnit,step:bankStep,xpItem:{kind:'bank',stars:s.stars},open:writtenDefault(true),noReview:true,noText:!v.main?.text,
      gradeItem:()=>({id:String(pick.id),source:'bank',q:v.main?.text||''}),
      answered:()=>s.answered,solve:()=>{saved.bank.done[pick.id]=1;},miss:()=>{saved.bank.done[pick.id]=0;},
      lock:()=>{s.answered=true;['good','miss','skip'].forEach(id=>$(id).hidden=true);$('next').hidden=false;reportHeight();}});
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
  /* fixed: a problem of a running set (custom, review): marked within the set, then on to the set's next problem */
  async function contestShow(key,skipId,fixed){
    const c=state.contests.find(x=>x.key===key);if(!c){contestHome();return;}
    const items=await contestItems(key);
    const L={ko:'한국어',en:'English',hu:'Magyar'},safe=u=>PDF_HOST.test(u||'')?u:'';
    const s=fixed?state.session:null;
    let item=null,p;
    if(fixed){item=fixed;p=c.problems.find(x=>x.id===item.pdf);if(!p){next();return;}}
    else if(items.length){
      const open=items.filter(i=>saved.contest.done[i.id]!==1&&i.id!==skipId),pool=open.length?open:items;
      item=pool[Math.floor(Math.random()*pool.length)];p=c.problems.find(x=>x.id===item.pdf);
    }else{
      const open=c.problems.filter(x=>saved.contest.done[x.id]!==1&&x.id!==skipId),pool=open.length?open:c.problems;
      p=pool[Math.floor(Math.random()*pool.length)];
    }
    const doneId=item?item.id:p.id,paceItem={id:doneId,s:c.step},tItem={id:doneId,kind:'contest',c:key};
    const langs=Object.entries(p.papers).filter(([,u])=>safe(u)),pref=langs.find(([l])=>l===state.lang)||langs[0];
    const sols=Object.entries(p.sols||{}).filter(([,u])=>safe(u));
    const label=item?`${item.year} · ${p.key}${item.key&&item.key!==p.key?' · '+item.key:''}`:`${p.year} · ${p.key}`;
    const title=item?.title||p.title||'';
    const body=item?item.b.map(b=>b.f?`<figure><img src="practice/contest/fig/${encodeURIComponent(b.f)}" width="${b.w}" height="${b.h}" alt="" loading="lazy"></figure>`:textHtml(b.t)).join(''):'';
    $('app').innerHTML=`<div class="session">
      <div class="shead"><button type="button" class="back" id="quit">${tr('quit')}</button><span class="unitname">${s?esc(s.label||tr('tabToday'))+' · ':''}${esc(nameOf(c.name))}</span><span class="lvl">${esc(label)}</span>${title?`<span>${esc(title)}</span>`:''}${s?`<span class="progress" aria-hidden="true"><i style="width:${Math.round(100*(s.n-1)/setTotal(s))}%"></i></span><span>${s.n}/${setTotal(s)}</span>`:''}${paceHtml(paceItem)}</div>
      ${item?`<div class="q" id="qtext">${body}</div>`:''}
      <div class="langrow">${tr('paper')}: ${langs.map(([l,u])=>`<button type="button" class="${!item&&l===pref[0]?'cur':''}" data-pdf="${esc(u)}">${L[l]||l} PDF</button>`).join('')} <a href="${esc(pref[1])}" target="_blank" rel="noopener" id="openPdf">PDF ↗</a></div>
      <div id="pdf" class="pdf"${item?' hidden':''} role="document" aria-label="${esc(nameOf(c.name))} ${esc(label)}"><p class="src">${tr('loading')}</p></div>
      <div id="feedback"></div>
      ${toolsHtml(tItem)}
      <div class="foot"><span class="src">${sols.length?`${tr('solution')}: `+sols.map(([l,u])=>`<a href="${esc(u)}" target="_blank" rel="noopener">${L[l]||l} ↗</a>`).join(' · '):tr('noContestSol')}${item?' · '+tr('transcribed'):''}</span>
        <span class="footbtns"><button type="button" id="skip">${tr('skip')}</button><button type="button" class="primary" id="good">${tr('solvedIt')}</button><button type="button" id="miss">${tr('missedIt')}</button><button type="button" class="primary" id="next" hidden>${s?s.n>=setTotal(s)?tr('finish'):tr('next'):tr('another')}</button></span></div></div>`;
    startPace(paceItem);wireTools(tItem,nameOf(c.name)+' · '+label);
    wireWritten(tItem,{source:'contest',mode:'contest',unit:'contest/'+key,step:c.step,xpItem:{kind:'contest',s:c.step},open:!!item&&writtenDefault(true),noText:!item,
      gradeItem:()=>({id:doneId,source:'contest',q:(title?title+'\n\n':'')+item.b.filter(b=>b.t).map(b=>b.t).join('\n\n')}),
      answered:()=>s?s.answered:W.locked,solve:()=>{saved.contest.done[doneId]=1;},miss:()=>{saved.contest.done[doneId]=0;},
      lock:()=>{if(s)s.answered=true;W.locked=true;['good','miss','skip'].forEach(id=>$(id).hidden=true);$('next').hidden=false;reportHeight();}});
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
    $('quit').onclick=s?s.back:contestHome;
    $('skip').onclick=()=>{record(doneId,'contest','contest/'+key,c.step,'skip');if(s){if(s.answered)return;s.skipped=(s.skipped||0)+1;s.n--;next();return;}contestShow(key,doneId);};
    $('next').onclick=()=>s?next():contestShow(key,doneId);
    const mark=ok=>{if(W.locked&&W.item===tItem)return;W.locked=true;if(s){if(s.answered)return;s.answered=true;if(ok){s.right++;s.xp+=20+5*c.step;}}
      stopPace(paceItem);noteOutcome({id:doneId,kind:'contest',c:key},ok?'right':'wrong');
      saved.contest.done[doneId]=ok?1:0;record(doneId,'contest','contest/'+key,c.step,ok?'solved':'missed');studied(ok?20+5*c.step:2);['good','miss','skip'].forEach(id=>$(id).hidden=true);$('next').hidden=false;
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
    /* the first visit: the four level cards, then the first problem (the full questions stay in Settings) */
    if(!saved.profile){quickStart();return;}
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
    const due=dueNow().length;
    const dueCard=due?`<button type="button" class="area unit duecard" id="dueGo"><span class="name"><b>${tr('dueCard')}</b><small>${tr('dueToday')} ${due} · ${tr('startReview')}</small></span><span>→</span></button>`:'';
    const lv=studyLevel(),lvCard=`<button type="button" class="area unit levelbar" id="lvGo"><span class="name"><small>${tr('lvTitle')} ${lv.slice(1)} · ${tr('lvCurrent')}</small><b>${esc(levelName(lv))}</b></span><span class="btnlink">${tr('lvChange')}</span></button>`;
    $('app').innerHTML=`<div id="draftHome"></div>${lvCard}${placeCard}${dueCard}<section class="session today">
        <h2>${tr('todayTitle')} <a href="#" class="src" id="editProfile">${tr('editProfile')}</a></h2>
        <p class="src">${Object.entries(counts).map(([k,n])=>`${why[k]} ${n}`).join(' · ')}${weakUnits.length?` · ${tr('focus')}: ${weakUnits.map(u=>esc(unitPlace(u))).join(', ')}`:''}</p>
        <ol class="todaylist">${chosen.map(i=>`<li><span class="tag ${i.why}">${why[i.why]}</span> ${esc(itemPlace(i))} <small>${tr('step')} ${i.s}</small></li>`).join('')}</ol>
        <div class="actions"><button type="button" class="primary" id="startToday"${chosen.length?'':' disabled'}>${tr('startToday')}</button></div>
      </section>
      <div class="areas suggest">
        <button type="button" class="area unit" id="sugBank"><span class="name"><b>${tr('tabBank')}</b><small>${esc(state.lang==='ko'?field[1]:tx(field[2]))} · ${'★'.repeat(fieldStars)}</small></span><span>→</span></button>
        ${contest?`<button type="button" class="area unit" id="sugContest"><span class="name"><b>${tr('tabContest')}</b><small>${esc(nameOf(contest.name))} · ${tr('step')} ${contest.step}</small></span><span>→</span></button>`:''}
      </div>
      ${top.length?`<section class="area skills"><h2>${tr('mySkills')}</h2><table><thead><tr><th>${tr('unit')}</th><th>${tr('step')}</th><th>${tr('accuracy')}</th></tr></thead><tbody>${top.slice(0,12).map(x=>`<tr><td>${esc(unitPlace(x.u))}</td><td>${x.step} <span class="lv lv${levelOf(x.step)}">${tr(LEVELS[levelOf(x.step)])}</span></td><td>${Math.round(100*x.k.right_n/Math.max(1,x.k.n))}% <small>(${x.k.n})</small></td></tr>`).join('')}</tbody></table></section>`:`<p class="src">${tr('noSkills')}</p>`}
      ${settingsHtml()}`;
    if($('dueGo'))$('dueGo').onclick=reviewHome;wireSettings(todayHome);$('lvGo').onclick=levelHome;
    $('startToday').onclick=()=>startTodaySession(chosen);
    $('sugBank').onclick=()=>{state.bankField=field[0];bankStart(field[0],fieldStars);};
    if($('diagGo'))$('diagGo').onclick=diagStart;
    $('editProfile').onclick=e=>{e.preventDefault();startHome(true);};
    if($('sugContest'))$('sugContest').onclick=()=>{paintTabs();contestShow(contest.key);};
    reportHeight();
    draftHomeCard(todayHome);
  }
  /* after a reload or a crash: the newest unsent working, one tap from where it was */
  async function draftHomeCard(back){
    const d=await Drafts.latest().catch(()=>null),box=$('draftHome');
    if(!d||!box||!['exam','track','contest'].includes(d.meta?.k))return;
    box.innerHTML=`<div class="draftbar home"><span><b>${tr('dHome')}</b><small>${esc(d.t||d.id)} · ${draftSummary(d)}</small></span><span class="dbtns"><button type="button" class="primary" id="dhGo">${tr('dResume')}</button><button type="button" id="dhDrop">${tr('dDrop')}</button></span></div>`;
    $('dhDrop').onclick=()=>{Drafts.del(d.id);box.innerHTML='';reportHeight();};
    $('dhGo').onclick=async()=>{
      $('app').innerHTML=`<p>${tr('loading')}</p>`;
      await loadContests().catch(()=>{});
      const items=await resolveItems([d.id],{[d.id]:d.meta});
      if(!items.length){Drafts.del(d.id);back();return;}
      state.autoResume=d.id;runSet({items,label:tr('dHome'),back,again:back});
    };
    reportHeight();
  }

  /* ── typed answers (math-input.js): a number or a formula entered on a calculator keypad, no LaTeX. A problem whose
     correct choice is a number or a formula is answered this way; a concept question keeps its choices. The choices stay
     one tap away as a hint. ── */
  const MI=()=>window.HL_MATH;
  /* tolerance: 1 %, or less when a wrong choice lies closer than 2 % to the answer */
  function tolFor(ans,choices){
    let tol=ans.tol??0.01;
    for(const c of choices||[]){const d=c&&MI().answerOf(c);if(d&&d.kind==='num'&&d.value!==ans.value&&ans.value)tol=Math.min(tol,Math.abs(d.value-ans.value)/Math.abs(ans.value)/2);}
    return tol;
  }
  function freeOfTrack(item){
    if(!MI())return null;
    if(item.type==='num')return{kind:'num',value:item.answer.value,unit:item.answer.unit||'',tol:item.answer.tol,tex:String(item.answer.value)};
    const a=MI().answerOf(item.choices[item.answer]);if(!a)return null;
    if(a.kind==='num')a.tol=tolFor(a,item.choices.filter((c,i)=>i!==item.answer));
    return a;
  }
  const choiceText=c=>c.c.filter(b=>b.p).map(b=>segText(b.p)).join(' ');
  function freeOfExam(item){
    if(!MI()||item.ch.some(c=>c.c.some(b=>b.f)))return null;
    const right=item.ch.find(c=>c.n===item.a);if(!right)return null;
    const a=MI().answerOf(choiceText(right));if(!a)return null;
    if(a.kind==='num')a.tol=tolFor(a,item.ch.filter(c=>c!==right).map(choiceText));
    return a;
  }
  const KEYS=[['7','8','9','÷','⌫'],['4','5','6','×','('],['1','2','3','−',')'],['0','.','π','+','^'],['√','×10ⁿ','frac','←','→']];
  const KEY_IN={'÷':'/','×':'*','−':'-','√':'sqrt(','×10ⁿ':'*10^(','π':'π','frac':')/('};
  function answerBox(free){
    const vs=free.kind==='expr'?free.vars:[],show=v=>{const[n,s]=v.split('_');return (MI().GREEK_CHAR[n]||n)+(s?`<sub>${esc(s)}</sub>`:'');};
    const ins=v=>{const[n,s]=v.split('_');return (MI().GREEK_CHAR[n]||n)+(s?'_'+s:'');};
    return `<div class="ansbox" id="ansbox">
      <div class="ansline"><input id="ans" autocomplete="off" autocapitalize="off" spellcheck="false"${matchMedia('(pointer:coarse)').matches?' inputmode="none"':''} placeholder="${tr(free.kind==='num'?'typeNumber':'typeFormula')}" aria-label="${tr('answer')}">${free.unit?`<span class="unitlbl">${esc(free.unit)}</span>`:''}<button type="button" class="primary" id="ansgo">${tr('check')}</button></div>
      <div class="anspreview" id="anspreview" aria-live="polite"></div>
      <div class="keypad" role="group" aria-label="${tr('keypad')}">${vs.length?`<div class="keyrow vars">${vs.map(v=>`<button type="button" data-k="${esc(ins(v))}">${show(v)}</button>`).join('')}</div>`:''}
        ${KEYS.map(r=>`<div class="keyrow">${r.map(k=>`<button type="button" data-k="${k}"${/[⌫←→]/.test(k)?' class="op"':''}>${k==='frac'?'a⁄b':k}</button>`).join('')}</div>`).join('')}</div>
      <p class="src ansnote">${tr('typeHelp')}</p></div>`;
  }
  /* wires the box: keys insert at the caret, the typed text is shown as math, Enter or the button checks it */
  function wireAnswer(free,onDone){
    const inp=$('ans'),pv=$('anspreview');
    const paint=()=>{const v=inp.value.trim();if(!v){pv.innerHTML='';return;}const t=MI().preview(v);pv.innerHTML=t?math(t):`<span class="src">${tr('notYet')}</span>`;reportHeight();};
    const put=t=>{const a=inp.selectionStart??inp.value.length,b=inp.selectionEnd??a;inp.value=inp.value.slice(0,a)+t+inp.value.slice(b);const p=a+t.length;inp.setSelectionRange?.(p,p);paint();};
    $('ansbox').querySelectorAll('[data-k]').forEach(btn=>btn.onclick=()=>{
      const k=btn.dataset.k,a=inp.selectionStart??inp.value.length;
      if(k==='⌫'){if(a>0){inp.value=inp.value.slice(0,a-1)+inp.value.slice(a);inp.setSelectionRange?.(a-1,a-1);}paint();}
      else if(k==='←')inp.setSelectionRange?.(Math.max(0,a-1),Math.max(0,a-1));
      else if(k==='→')inp.setSelectionRange?.(a+1,a+1);
      else if(k==='frac'){inp.value='('+inp.value+')/(';inp.setSelectionRange?.(inp.value.length,inp.value.length);paint();}
      else put(KEY_IN[k]??k);
      if(!matchMedia('(pointer:coarse)').matches)inp.focus();
    });
    inp.oninput=paint;
    const go=()=>{
      const v=inp.value.trim();if(!v)return;
      const r=MI().check(v,free,free.tol??0.01);
      if(r.error==='syntax'){pv.innerHTML=`<span class="numerr">${tr('notYet')}</span>`;reportHeight();return;}
      if(r.error==='vars'){pv.innerHTML=`<span class="numerr">${tr(free.kind==='num'?'onlyNumber':'unknownVar')}${r.extra?': '+esc(r.extra.join(', ')):''}</span>`;reportHeight();return;}
      inp.disabled=true;$('ansgo').disabled=true;$('ansbox').classList.add(r.ok?'right':'wrong');$('ansbox').querySelector('.keypad').hidden=true;
      onDone(r.ok);reportHeight();
    };
    $('ansgo').onclick=go;inp.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();go();}};
  }
  const freeAnswerTex=free=>`${math(free.tex)}${free.unit?' '+esc(free.unit):''}`;

  /* ── levels: a unit's step reads as a level name; all XP together gives a tier, like a competitive-programming judge ── */
  const LEVELS=['lvBeginner','lvFamiliar','lvProficient','lvMaster'];
  const levelOf=step=>step<=2?0:step<=4?1:step<=6?2:3;
  const TIERS=[[0,'Bronze'],[500,'Silver'],[2000,'Gold'],[6000,'Platinum'],[15000,'Diamond'],[40000,'Ruby']];
  const tierOf=xp=>[...TIERS].reverse().find(t=>xp>=t[0]);
  function sessionHead(s,item){
    const name=s.diag?tr('diagTitle'):s.assignment?s.label:s.fixed?(s.label||tr('tabToday'))+' · '+unitName(item.u):s.mode==='track'?s.label:unitName(s.unit);
    const total=setTotal(s);
    return `<div class="shead"><button type="button" class="back" id="quit">${tr('quit')}</button><span class="unitname">${esc(name)}</span><span class="lvl">${tr('step')} ${item.s}</span><span class="progress" aria-hidden="true"><i style="width:${Math.round(100*(s.n-1)/total)}%"></i></span><span>${s.n}/${total}</span>${paceHtml(item)}</div>`;
  }

  /* ── the member's plan: tutor questions left today (GET /api/learn/plan) ── */
  /* ── the member's country and daily goal (GET /api/me/learner, set at sign-up and in Settings): the goal is fixed
     for members who have one (the first questions skip it), the country picks the default exams; guests choose here ── */
  const SETTINGS_HREF='/#/community/account?section=learning';
  async function loadLearner(){
    if(!token()){state.learner=null;state.learnerDone=true;return null;}
    try{const r=await api('/api/me/learner');state.learner=r&&r.country?r:null;state.learnerMissing=!state.learner;}catch(e){state.learner=null;state.learnerMissing=false;}
    state.learnerDone=true;return state.learner;
  }
  const dailyGoal=()=>state.learner?.daily_goal||saved.profile?.daily||saved.dailyGoal||0;
  const countryOf=()=>state.learner?.country||'';
  async function loadPlan(){if(!token()){state.plan={plan:'guest',tutorLeft:0};return;}try{state.plan=await api('/api/learn/plan');}catch(e){state.plan=null;if(/api 404/.test(e.message))state.serverOld=true;}}

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
  async function trackStart(key,syl,opts){
    state.mode='tracks';paintTabs();
    $('app').innerHTML=`<p>${tr('loading')}</p>`;
    let t,items;try{t=(await loadTracks()).find(x=>x.key===key);if(!t){tracksHome();return;}items=(await trackItems(key)).filter(i=>!syl||i.syl===syl);}catch(e){failed(()=>trackStart(key,syl));return;}
    if(!items.length){tracksHome();return;}
    const steps=[...new Set(items.map(i=>i.s))].sort((a,b)=>a-b),lk='track:'+key+'/'+(syl||'*');
    const own=ratingStep(saved.skills[items[0].u]?.rating??START),level=saved.level[lk]&&steps.includes(saved.level[lk])?saved.level[lk]:steps.reduce((b,x)=>Math.abs(x-own)<Math.abs(b-own)?x:b,steps[0]);
    state.session={mode:'track',track:key,syl,levelKey:lk,label:nameOf(t.name)+(syl?' · '+sylName(t,syl):''),items,steps,level,n:0,right:0,run:0,seen:new Set(),current:null,answered:false,xp:0};
    /* a syllabus unit: the card of the path unit most of its problems belong to (a mixed set goes straight in) */
    if(!opts?.noIntro)await draftFirst(state.session);
    const counts=items.reduce((m,i)=>(m[i.u]=(m[i.u]||0)+1,m),{}),main=syl?Object.entries(counts).sort((a,b)=>b[1]-a[1])[0]?.[0]:null;
    if(main&&!opts?.noIntro)withIntro(main,next,tracksHome);else next();
  }
  /* a problem opened by its link (a search page, a discussion): that one first, then its unit */
  async function openItem(id){
    const key=id.split('-')[0];let items;
    /* a competition problem (practice/contest/<key>.json, ids like eupho-2017-T1~T1): that problem, then the contest's next */
    if(id.includes('~')){
      try{await loadContests();}catch(e){contestHome();return;}
      if(!state.contests.some(c=>c.key===key)){contestHome();return;}
      const it=(await contestItems(key)).find(i=>i.id===id);
      state.mode='contest';state.session=null;paintTabs();
      if(!it||!state.contests.find(c=>c.key===key).problems.some(x=>x.id===it.pdf)){contestShow(key);return;}
      contestShow(key,null,it);return;
    }
    try{items=await trackItems(key);}catch(e){todayHome();return;}
    const it=items.find(i=>i.id===id);if(!it){tracksHome();return;}
    await trackStart(key,it.syl,{noIntro:true});const s=state.session;if(!s)return;
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
    const s=state.session;s.hints=0;s.answered=false;s.view=null;s.chat=[];s.free=s.format==='choice'&&item.type==='mc'?null:freeOfTrack(item);
    const L='ABCDE';
    $('app').innerHTML=`<div class="session">
      ${sessionHead(s,item)}
      <div class="q" id="qtext">${textHtml(item.q)}</div><p class="src" id="trnote"></p>
      ${s.free?answerBox(s.free)+`<button type="button" class="linkbtn" id="showch">${tr('showChoices')}</button>`:''}
      ${item.type==='mc'?`<div class="choices" role="group"${s.free?' hidden':''}>${item.choices.map((c,i)=>`<button type="button" class="choice" data-i="${i}"><span class="no">${L[i]}</span><span class="ct">${esc(c)}</span></button>`).join('')}</div>`
        :s.free?'':`<form class="numrow" id="numf"><input id="num" inputmode="decimal" autocomplete="off" placeholder="${tr('numPh')}" aria-label="${tr('numPh')}"><span class="unitlbl">${esc(item.answer.unit||'')}</span><button type="submit" class="primary">${tr('check')}</button><span class="numerr" id="numerr"></span></form>`}
      <div id="hints"></div><div id="feedback"></div><div id="sol"></div><div id="tutor"></div><div id="disc"></div>
      ${toolsHtml(item)}
      <div class="foot"><span class="src">${esc(s.fixed?unitName(item.u):s.label)} · ${tr('byHasla')} · <a href="#" id="discuss">${tr('discuss')}</a></span>
        <span class="footbtns"><button type="button" id="hint">${tr('hint')} (0/${item.hints.length})</button><button type="button" id="ask">✦ ${tr('tutor')}</button><button type="button" id="skip">${tr('skip')}</button><button type="button" class="primary" id="next" hidden>${s.n>=setTotal(s)?tr('finish'):tr('next')}</button></span></div></div>`;
    typeset($('qtext'));typeset($('app').querySelector('.choices')||$('app'));
    $('quit').onclick=s.back||(s.assignment?classHome:s.diag||s.fixed?todayHome:s.mode==='track'?tracksHome:home);
    $('skip').hidden=!!s.diag;
    addStrike($('app'));wireTools(item,(s.fixed?unitName(item.u):s.label)+' · '+item.id);startPace(item);
    if(s.free){
      wireAnswer(s.free,ok=>trackAnswer(null,ok));
      $('showch').onclick=()=>{if(item.type!=='mc')return;$('app').querySelector('.choices').hidden=false;$('ansbox').remove();$('showch').remove();s.free=null;s.hints++;reportHeight();};
      if(item.type!=='mc')$('showch').remove();
    }
    if(item.type==='mc')$('app').querySelectorAll('.choice').forEach(b=>b.onclick=()=>trackAnswer(Number(b.dataset.i)));
    else if(!s.free)$('numf').onsubmit=e=>{e.preventDefault();const v=parseNum($('num').value);if(!Number.isFinite(v)){$('numerr').textContent=tr('notNumber');return;}trackAnswer(v);};
    $('hint').onclick=()=>{if(s.hints>=item.hints.length)return;s.hints++;paintHints(item);$('hint').textContent=`${tr('hint')} (${s.hints}/${item.hints.length})`;if(s.hints>=item.hints.length)$('hint').disabled=true;reportHeight();};
    $('ask').onclick=()=>openTutor(item);
    $('skip').onclick=()=>{if(s.answered)return;record(item.id,'track',item.u,item.s,'skip');s.skipped=(s.skipped||0)+1;s.n--;s.extra=(s.extra||0)+1;if(s.extra>30){summary();return;}next();};
    $('next').onclick=next;
    $('discuss').onclick=e=>{e.preventDefault();discuss(item);};
    wireWritten(item,{source:'track',mode:'track',unit:item.u,step:item.s,xpItem:{kind:'track',s:item.s},open:writtenDefault(item.type!=='mc'),
      gradeItem:()=>({id:item.id,source:'track',q:item.q,answer:item.type==='mc'?'ABCDE'[item.answer]+'. '+item.choices[item.answer]:fmtNum(item.answer),sol:item.sol,choices:item.type==='mc'?item.choices:undefined}),
      answered:()=>s.answered,solve:()=>{saved.solved[item.id]=item.u;delete saved.wrong[item.id];},miss:()=>{saved.wrong[item.id]=Math.floor(Date.now()/1000);},
      hint:()=>{if(!s.hints&&item.hints.length)$('hint')?.click();},
      lock:()=>{s.answered=true;$('app').querySelectorAll('.choice').forEach(b=>b.disabled=true);
        if($('ans')){$('ans').disabled=true;$('ansgo').disabled=true;$('ansbox').querySelector('.keypad').hidden=true;}
        if($('numf')){$('num').disabled=true;$('numf').querySelector('button').disabled=true;}
        $('showch')?.remove();paintSolution(item);$('hint').hidden=true;$('skip').hidden=true;$('next').hidden=false;reportHeight();}});
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
  function trackAnswer(given,typedOk){
    const s=state.session,item=s.current;if(s.answered)return;s.answered=true;
    const ok=typedOk!==undefined?typedOk:item.type==='mc'?given===item.answer:numOk(given,item.answer);
    const result=ok?(s.hints?'solved':'right'):'wrong';stopPace(item);noteOutcome(item,ok?(s.hints?'hinted':'right'):'wrong');
    if(item.type==='mc')$('app').querySelectorAll('.choice').forEach(b=>{b.disabled=true;const i=Number(b.dataset.i);if(i===item.answer)b.classList.add('right');else if(i===given)b.classList.add('wrong');});
    else if($('numf')){$('num').disabled=true;$('numf').querySelector('button').disabled=true;$('numf').classList.add(ok?'right':'wrong');}
    $('showch')?.remove();
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
    const answerText=s.free?null:item.type==='mc'?'ABCDE'[item.answer]+'. '+(viewOf(item).choices[item.answer]||''):fmtNum(item.answer);
    $('feedback').innerHTML=`<p class="feedback ${ok?'ok':'bad'}">${ok?tr('right'):tr('wrong')+' '+(s.free?freeAnswerTex(s.free):esc(answerText))}${note}${ok&&s.hints?' · '+tr('withHints'):''}</p>`;
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
    if(token()&&!state.learnerDone){(state.learnerP||(state.learnerP=loadLearner())).finally(()=>startHome(edit));return;}
    state.mode='start';state.session=null;paintTabs();paintStats();tellUnit('');
    const old=saved.profile||{},tz=(()=>{try{return Intl.DateTimeFormat().resolvedOptions().timeZone;}catch(e){return '';}})();
    const a={region:old.region||P.guessRegion(state.lang,tz,countryOf()),level:old.level||'',goal:old.goal||'',oly:old.oly??0,daily:state.learner?.daily_goal||old.daily||10,stage:saved.studyLevel||''};
    /* a member's daily goal was set at sign-up (the goal panel and Settings change it): only guests choose it here */
    const steps=['region','level','goal','oly','stage',...(state.learner?.daily_goal?[]:['daily'])];let i=0;
    const q=()=>{
      const key=steps[i];if(key==='oly'&&a.goal!=='olympiad'){i+=dir;return q();}
      const R=P.REGIONS[a.region]||P.REGIONS.global;
      if(key==='stage'){
        const cur=a.stage||H.defaultLevel(a);
        $('app').innerHTML=`<div class="session onboard"><div class="shead"><button type="button" class="back" id="obBack">← ${tr('back')}</button><span class="progress" aria-hidden="true"><i style="width:${Math.round(100*i/steps.length)}%"></i></span></div>
          <h2>${tr('ob_stage')}</h2><p class="src">${tr('lvIntro')}</p><div class="obopts">${levelCards(cur)}</div></div>`;
        $('app').querySelectorAll('[data-level]').forEach(b=>b.onclick=()=>{a.stage=b.dataset.level;dir=1;i++;q();});
        $('obBack').onclick=()=>{dir=-1;i--;q();};
        reportHeight();return;
      }
      const opts={
        region:Object.entries(P.REGIONS).map(([k,r])=>[k,pickName(r.name),k==='kr'?tr('obKr'):k==='in'?tr('obIn'):k==='us'?tr('obUs'):tr('obGlobal')]),
        level:P.LEVELS.map(([k,n])=>[k,pickName(n),'']),
        goal:[['school',tr('goSchool'),''],['exam',tr('goExam'),pickName(R.examName)],['olympiad',tr('goOly'),pickName(R.olyName)],['curious',tr('goCurious'),'']],
        oly:[[0,tr('oly0'),''],[1,tr('oly1'),''],[2,tr('oly2'),'']],
      }[key];
      /* a guest's daily goal: the stepper from learner-form.js, 1 to 50, 10 suggested */
      if(key==='daily'&&LF()){
        LF().addStyle(document);
        $('app').innerHTML=`<div class="session onboard"><div class="shead"><button type="button" class="back" id="obBack">← ${tr('back')}</button><span class="progress" aria-hidden="true"><i style="width:${Math.round(100*i/steps.length)}%"></i></span></div>
          <h2>${tr('ob_daily')}</h2><form id="obGoal">${LF().goalHtml(state.lang,a.daily)}<div class="actions"><button type="submit" class="primary">${tr('goalNext')}</button></div></form></div>`;
        const read=LF().wireGoal($('obGoal'),state.lang);
        $('obGoal').onsubmit=e=>{e.preventDefault();const g=read();if(!g)return;a.daily=g;dir=1;i++;if(i>=steps.length)finish();else q();};
        $('obBack').onclick=()=>{dir=-1;i--;q();};
        reportHeight();return;
      }
      $('app').innerHTML=`<div class="session onboard"><div class="shead">${i?`<button type="button" class="back" id="obBack">← ${tr('back')}</button>`:edit?`<button type="button" class="back" id="obBack">${tr('quit')}</button>`:''}<span class="progress" aria-hidden="true"><i style="width:${Math.round(100*i/steps.length)}%"></i></span></div>
        <h2>${tr('ob_'+key)}</h2><div class="obopts">${opts.map(([v,label,note])=>`<button type="button" class="unit${String(a[key])===String(v)?' cur':''}" data-v="${v}"><span class="name"><b>${esc(label)}</b>${note?`<small>${esc(note)}</small>`:''}</span></button>`).join('')}</div></div>`;
      $('app').querySelectorAll('[data-v]').forEach(b=>b.onclick=()=>{a[key]=key==='oly'?Number(b.dataset.v):b.dataset.v;dir=1;i++;if(i>=steps.length)finish();else q();});
      if($('obBack'))$('obBack').onclick=()=>{if(!i){todayHome();return;}dir=-1;i--;q();};
      reportHeight();
    };
    let dir=1;
    const finish=()=>{
      const {stage,...rest}=a,profile={...rest,at:Math.floor(Date.now()/1000)},step=P.startStep(profile);
      saved.profile=profile;saved.studyLevel=stage||H.defaultLevel(profile);
      /* every unit with no answers yet starts at that step (the answers that follow move each one on its own) */
      for(const area of P.AREAS)for(const sub of area.subtopics){const unit=area.key+'/'+sub.key,k=saved.skills[unit];
        if(!k||!k.n)record('start-'+area.key,'diag',unit,step,'place');}
      save();scheduleSync();
      const exams=[tr('lvTitle')+' '+saved.studyLevel.slice(1)+' · '+levelName(saved.studyLevel)];
      $('app').innerHTML=`<div class="session summary onboard"><p class="eyebrow">${tr('obDone')}</p><p class="big">${tr('step')} ${step}</p>
        <p>${tr(LEVELS[levelOf(step)])} · ${esc(exams.join(' · '))}</p><p class="src">${tr('obNext')}</p>
        <div class="actions"><button type="button" class="primary" id="obToday">${tr('startToday')}</button><button type="button" id="obDiag">${tr('diagStart')}</button></div></div>`;
      $('obToday').onclick=document.documentElement.classList.contains('play')?playHome:todayHome;$('obDiag').onclick=diagStart;reportHeight();
    };
    loadTracks().catch(()=>{}).finally(q);
  }
  /* the problems a learner starts on: their exams, as graded items */
  /* the problems a learner starts on: the chosen level's pool (practice-tools.js STUDY_LEVELS), as set items */
  async function startPool(){
    const items=await levelItems(studyLevel());
    return items.length?items:allTrackItems();
  }
  /* the home page's own problem: today's set starts at once, one problem after another, no list in between */
  function startTodaySession(chosen){state.session={unit:'today',fixed:true,items:chosen,steps:[],level:0,n:0,right:0,run:0,seen:new Set(),current:null,answered:false,xp:0};next();}
  /* the home page's first visit: only the four level cards, then the first problem. The full questions (region, school
     year, goal, daily target) stay in the settings; until then every unit starts at the step startStep() gives the level. */
  const QUICK_PROFILE={L1:{},L2:{goal:'exam',region:'in'},L3:{goal:'olympiad',oly:1},L4:{level:'uni'}};
  function quickStart(){
    state.mode='start';state.session=null;paintTabs();paintStats();tellUnit('');
    $('app').innerHTML=`<div class="session onboard"><h2>${tr('lvPick')}</h2><p class="src">${tr('quickIntro')}</p><div class="obopts">${levelCards('')}</div></div>`;
    $('app').querySelectorAll('[data-level]').forEach(b=>b.onclick=()=>{
      const key=b.dataset.level,tz=(()=>{try{return Intl.DateTimeFormat().resolvedOptions().timeZone;}catch(e){return '';}})();
      const profile={region:P.guessRegion(state.lang,tz,countryOf()),level:'',goal:'',oly:0,daily:state.learner?.daily_goal||10,...QUICK_PROFILE[key],quick:true,at:Math.floor(Date.now()/1000)},step=P.startStep(profile);
      saved.profile=profile;saved.studyLevel=key;
      for(const area of P.AREAS)for(const sub of area.subtopics){const unit=area.key+'/'+sub.key,k=saved.skills[unit];
        if(!k||!k.n)record('start-'+area.key,'diag',unit,step,'place');}
      save();scheduleSync();playHome();
    });
    reportHeight();
  }
  async function playHome(){
    if(!saved.profile){quickStart();return;}
    state.mode='today';state.session=null;paintTabs();paintStats();
    $('app').innerHTML=`<p>${tr('loading')}</p>`;
    let items;try{items=await startPool();}catch(e){failed(playHome);return;}
    const {chosen}=chooseToday(items);
    if(!chosen.length){todayHome();return;}
    startTodaySession(chosen);
  }
  /* ── pace: a suggested time from the problem's step and a running clock that turns amber past it; it never stops
     the learner from answering. The time taken goes into the session summary. ── */
  const setTotal=s=>s.diag?s.diag.areas.length*2:s.total||SESSION;
  let paceTick=0;
  const paceHtml=item=>state.session?.timer===false?'':`<span class="pace" id="pace" title="${tr('time')} ${H.clock(H.paceFor(item))}"><span class="pt" id="pacet">0:00</span><small>/ ${H.clock(H.paceFor(item))}</small></span>`;
  function paintPace(){
    const p=state.pace,el=$('pace');if(!p||!el){clearInterval(paceTick);return;}
    const t=((p.end||Date.now())-p.t0)/1000;$('pacet').textContent=H.clock(t);el.classList.toggle('over',t>p.sug);
  }
  function startPace(item){clearInterval(paceTick);state.pace={id:item.id,t0:Date.now(),sug:H.paceFor(item)};paintPace();if($('pace'))paceTick=setInterval(paintPace,1000);}
  /* stops the clock for this item and adds the time to the running set */
  function stopPace(item){
    const p=state.pace;if(!p||p.id!==item.id||p.end)return;p.end=Date.now();clearInterval(paceTick);paintPace();
    const s=state.session;if(s)(s.times||=[]).push({t:(p.end-p.t0)/1000,sug:p.sug});
  }
  /* ── strike-out: a small ✕ beside each choice (or a long press on the choice) crosses it out; it stays clickable ── */
  function addStrike(root){
    root.querySelectorAll('.choice').forEach(b=>{
      const w=document.createElement('div');w.className='chrow';b.before(w);
      const x=document.createElement('button');x.type='button';x.className='strike';x.textContent='✕';x.setAttribute('aria-label',tr('strike'));x.setAttribute('aria-pressed','false');x.title=tr('strike');
      const flip=()=>{const on=!b.classList.contains('struck');b.classList.toggle('struck',on);x.setAttribute('aria-pressed',String(on));x.setAttribute('aria-label',tr(on?'unstrike':'strike'));x.title=tr(on?'unstrike':'strike');x.textContent=on?'↺':'✕';};
      x.onclick=flip;w.append(b,x);
      let timer=0,long=false;
      b.addEventListener('pointerdown',e=>{if(e.pointerType==='mouse'||b.disabled)return;long=false;clearTimeout(timer);timer=setTimeout(()=>{long=true;flip();try{navigator.vibrate?.(15);}catch(err){}},550);});
      for(const t of ['pointerup','pointerleave','pointercancel','pointermove'])b.addEventListener(t,e=>{if(t!=='pointermove'||Math.abs(e.movementX)+Math.abs(e.movementY)>6)clearTimeout(timer);});
      b.addEventListener('click',e=>{if(long){long=false;e.stopImmediatePropagation();e.preventDefault();}},true);
      b.addEventListener('contextmenu',e=>{if(e.pointerType!=='mouse')e.preventDefault();});
    });
  }
  /* ── the review queue (1, 3, 7, 21 days) and the record of when each problem was last tried ── */
  /* t: a readable name for the lists (the exam and question for school items, competition, year and problem for contest items) */
  const titleOf=item=>String(item.src||(item.kind==='contest'?[item.c,item.year,item.key].filter(Boolean).join(' · '):'')||'').slice(0,120);
  const metaOf=item=>({...(item.kind==='contest'?{k:'contest',c:item.c}:{k:item.kind==='track'?'track':'exam',u:item.u}),...(titleOf(item)?{t:titleOf(item)}:{})});
  function noteOutcome(item,outcome){
    saved.review=H.reviewUpdate(saved.review,item.id,outcome,today(),metaOf(item));
    saved.recent[item.id]=Math.floor(Date.now()/1000);
    const ids=Object.keys(saved.recent);if(ids.length>800)for(const [id] of Object.entries(saved.recent).sort((a,b)=>a[1]-b[1]).slice(0,ids.length-800))delete saved.recent[id];
    save();
  }
  const dueNow=()=>H.dueIds(saved.review,today());
  /* ── under each problem: show your working, save for later, and report a problem ── */
  const REASONS=['rWrongAnswer','rTypo','rFigure','rTranslation','rOther'];
  const REASON_API={rWrongAnswer:'wrong_answer',rTypo:'typo',rFigure:'figure',rTranslation:'translation',rOther:'other'};
  const laterLabel=on=>on?'★ '+tr('laterOn'):'☆ '+tr('later');
  const bandLabel=b=>tr(b==='pass'?'bandPass':b==='partial'?'bandPartial':'bandRetry');
  const lastGradedHtml=id=>{const g=saved.graded[id];return g?`<span class="lastgr band-${g.band}" id="lastgr">${tr('wLast')} ${Math.round(100*g.fraction)}% · ${bandLabel(g.band)} · ${day(g.at)}</span>`:'<span id="lastgr" hidden></span>';};
  function toolsHtml(item,opt){return `<div class="ptools"><button type="button" class="mini" id="writeBtn" aria-expanded="false">${tr('wOpen')}</button>${opt?.noLater?'':`<button type="button" class="mini" id="laterBtn" aria-pressed="${!!saved.later[item.id]}">${laterLabel(saved.later[item.id])}</button>`}<button type="button" class="mini quiet" id="reportBtn" aria-expanded="false">${tr('report')}</button>${lastGradedHtml(item.id)}</div><div id="draftBar"></div><div id="written"></div><div id="report"></div>`;}
  function wireTools(item,label){
    W.toolLabel=label;
    if($('laterBtn'))$('laterBtn').onclick=()=>{
      if(saved.later[item.id])delete saved.later[item.id];else saved.later[item.id]={...metaOf(item),at:Math.floor(Date.now()/1000),t:String(label||item.id).slice(0,120)};
      save();const on=!!saved.later[item.id];$('laterBtn').textContent=laterLabel(on);$('laterBtn').setAttribute('aria-pressed',String(on));paintTabs();
    };
    $('reportBtn').onclick=()=>openReport(item,label);
  }

  /* ── written answers: the working (photos, the pad, or a file) goes to POST /api/learn/grade and is marked against a
     rubric. The band decides what happens next (practice-tools.js moveOn); the last result per problem stays in
     saved.graded. ctx (from each mode): source, mode, unit, step, xpItem, open, noText, gradeItem(), answered(),
     solve(), miss(), lock(), hint() ── */
  const W={pages:[],mode:'photo'};
  const writtenDefault=noChoices=>H.levelInfo(studyLevel()).written||!!noChoices;
  const BAND_RANK={retry:0,partial:1,pass:2};
  function wireWritten(item,ctx){
    const btn=$('writeBtn');if(!btn)return;
    if(state.session?.diag){btn.remove();return;}
    Object.assign(W,{item,ctx,pages:[],padState:null,busy:false,bandSeen:null,locked:false,penSeen:false,read:null,draftHeld:false});
    btn.onclick=()=>$('written').innerHTML?closeWritten():openWritten();
    if(ctx.open)openWritten();
    if(ctx.noText)return;
    Drafts.get(item.id).then(d=>{
      if(!d||W.item!==item||H.draftEmpty(d))return;
      if(state.autoResume===item.id){state.autoResume=null;resumeDraft(d);return;}
      W.draftHeld=true;
      const bar=$('draftBar');if(!bar)return;
      bar.innerHTML=`<div class="draftbar" role="status"><span><b>${tr('dHas')}</b><small>${draftSummary(d)}</small></span><span class="dbtns"><button type="button" class="primary" id="dResume">${tr('dResume')}</button><button type="button" id="dDrop">${tr('dDrop')}</button></span></div>`;
      $('dResume').onclick=()=>resumeDraft(d);
      $('dDrop').onclick=()=>{W.draftHeld=false;bar.innerHTML='';Drafts.del(item.id);saveDraft();reportHeight();};
      reportHeight();
    }).catch(()=>{});
  }
  const draftSummary=d=>[d.pages.length?`${tr('dPages')} ${d.pages.length}`:'',d.strokes.length?tr('dPad'):'',day(d.at)].filter(Boolean).join(' · ');
  function resumeDraft(d){
    W.draftHeld=false;if($('draftBar'))$('draftBar').innerHTML='';
    W.pages=d.pages.slice(0,H.MAX_PAGES).map(url=>({url,from:'draft'}));
    W.padState={tool:'pen',size:1,strokes:d.strokes.map(st=>({...st}))};
    if(d.strokes.length&&!d.pages.length)W.mode='pad';
    if($('written').innerHTML){paintPane();paintThumbs();}else openWritten();
    reportHeight();
  }
  /* saved a moment after each change; held while the learner has not yet chosen between an old draft and a fresh start */
  let draftTimer=0;
  function saveDraft(){
    clearTimeout(draftTimer);const item=W.item;if(!item||W.draftHeld||W.ctx?.noText)return;
    draftTimer=setTimeout(()=>{if(W.item!==item)return;
      Drafts.put(H.draftOf(item.id,{pages:W.pages.map(p=>p.url),strokes:W.padState?.strokes,meta:metaOf(item),t:String(W.toolLabel||titleOf(item)||item.id)})).catch(()=>{});},600);
  }
  /* ── drafts (practice-tools.js draftOf): kept in IndexedDB; without it, a smaller copy in localStorage ── */
  const Drafts=(()=>{
    const now=()=>Math.floor(Date.now()/1000),idb=()=>{try{return typeof indexedDB!=='undefined'&&!!indexedDB;}catch(e){return false;}};
    let dbp=null;
    const open=()=>dbp||=new Promise((ok,no)=>{try{const r=indexedDB.open('hlPracticeDrafts',1);r.onupgradeneeded=()=>r.result.createObjectStore('drafts',{keyPath:'id'});r.onsuccess=()=>ok(r.result);r.onerror=()=>no(r.error);}catch(e){no(e);}});
    const run=async(mode,fn)=>{const db=await open();return new Promise((ok,no)=>{const t=db.transaction('drafts',mode),r=fn(t.objectStore('drafts'));t.oncomplete=()=>ok(r?.result);t.onerror=t.onabort=()=>no(t.error);});};
    const LS='hlPracticeDrafts',lsRead=()=>{try{const v=JSON.parse(localStorage.getItem(LS)||'{}');return v&&typeof v==='object'?v:{};}catch(e){return {};}};
    const lsWrite=v=>{try{localStorage.setItem(LS,JSON.stringify(v));return true;}catch(e){return false;}};
    async function all(){if(idb()){try{return (await run('readonly',st=>st.getAll()))||[];}catch(e){}}return Object.values(lsRead());}
    async function get(id){let d=null;if(idb()){try{d=await run('readonly',st=>st.get(id));}catch(e){}}if(!d)d=lsRead()[id]||null;return H.draftOk(d,now())?d:null;}
    async function del(id){if(idb()){try{await run('readwrite',st=>st.delete(id));}catch(e){}}const m=lsRead();if(m[id]){delete m[id];lsWrite(m);}}
    async function put(d){
      if(H.draftEmpty(d))return del(d.id);
      let done=false;if(idb()){try{await run('readwrite',st=>st.put(d));done=true;}catch(e){}}
      if(!done){const m=lsRead(),small=H.localDraft(d);if(small)m[d.id]=small;else delete m[d.id];if(!lsWrite(m)){delete m[d.id];lsWrite(m);}}
      for(const id of H.pruneDrafts(await all(),now()).drop)await del(id);
    }
    async function latest(){return (await all()).filter(d=>H.draftOk(d,now())&&!H.draftEmpty(d)).sort((a,b)=>b.at-a.at)[0]||null;}
    return{get,put,del,latest};
  })();
  function closeWritten(){$('written').innerHTML='';$('writeBtn').setAttribute('aria-expanded','false');reportHeight();}
  const msgW=(t,cls)=>{const m=$('wMsg');if(m){m.innerHTML=t;m.className='src wmsg'+(cls?' '+cls:'');}reportHeight();};
  function openWritten(){
    const ctx=W.ctx;$('writeBtn').setAttribute('aria-expanded','true');
    if(ctx.noText){$('written').innerHTML=`<section class="written"><p class="src">${tr('wNoText')}</p></section>`;reportHeight();return;}
    const left=state.plan&&Number.isFinite(state.plan.gradeLeft)?`<span class="src" id="wLeftTop">${tr('wLeft')}: ${state.plan.gradeLeft}</span>`:'';
    $('written').innerHTML=`<section class="written" id="wbox"><div class="whd"><h3>${tr('wTitle')}</h3>${left}</div><p class="src">${tr('wIntro')}</p>
      <details class="alt wrule"><summary>${tr('bandPass')} · ${tr('bandPartial')} · ${tr('bandRetry')}</summary><p>${tr('wRule')}</p></details>
      ${token()?'':`<p class="wlogin">${tr('wLogin')} <a class="btnlink primary" href="/#/login" target="_top">${tr('login')}</a></p>`}
      <div class="seg wmode" role="group" id="wMode">${[['photo','wPhoto'],['pad','wPad'],['file','wFile']].map(([k,l])=>`<button type="button" data-w="${k}" aria-pressed="${W.mode===k}">${tr(l)}</button>`).join('')}</div>
      <div id="wPane" class="wpane"></div>
      <div class="wpages"><p class="sublabel">${tr('wPages')} <span id="wCount"></span></p><div class="thumbs" id="wThumbs"></div></div>
      <div class="ractions"><button type="button" class="primary" id="wSend"${token()?'':' disabled'}>${tr('wSendRead')}</button><span class="src wmsg" id="wMsg" role="status"></span></div>
      <p class="src dsaved">${tr('dSaved')}</p>
      <div id="wRead"></div><div id="wResult"></div></section>`;
    $('wMode').querySelectorAll('[data-w]').forEach(b=>b.onclick=()=>{W.mode=b.dataset.w;$('wMode').querySelectorAll('[data-w]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));paintPane();});
    $('wSend').onclick=sendWritten;paintPane();paintThumbs();if(W.read){paintRead();setSendLabel();}reportHeight();
  }
  function paintPane(){
    const pane=$('wPane');if(!pane)return;
    if(W.mode==='pad'){paintPad();return;}
    const photo=W.mode==='photo';
    pane.innerHTML=`<label class="filebtn"><input type="file" id="wIn" accept="${photo?'image/*':'image/*,application/pdf,.pdf'}"${photo?' capture="environment"':''} multiple><span>${photo?'📷 '+tr('wTake'):'📄 '+tr('wFilePick')}</span></label>${photo?'':`<p class="src">${tr('wPdfNote')}</p>`}`;
    $('wIn').onchange=e=>{addFiles(e.target.files);e.target.value='';};
    reportHeight();
  }
  /* an image file → a drawable (createImageBitmap where it exists; else a data URL, which the page's CSP allows) */
  async function loadImage(file){
    if(window.createImageBitmap){try{return await createImageBitmap(file,{imageOrientation:'from-image'});}catch(e){}}
    const url=await new Promise((ok,no)=>{const r=new FileReader();r.onload=()=>ok(r.result);r.onerror=no;r.readAsDataURL(file);});
    const img=new Image();await new Promise((ok,no)=>{img.onload=ok;img.onerror=no;img.src=url;});return img;
  }
  /* any drawable → a JPEG data URL with the long side <= 1600 px and at most 1.5 MB (smaller and lower quality until it fits) */
  function toJpeg(src,w,h){
    for(const [side,q] of H.ENCODE_STEPS){
      const f=H.fitSize(w,h,side),c=document.createElement('canvas');c.width=f.w;c.height=f.h;
      const g=c.getContext('2d');g.fillStyle='#fff';g.fillRect(0,0,f.w,f.h);g.drawImage(src,0,0,f.w,f.h);
      const u=c.toDataURL('image/jpeg',q);if(H.pageOk(u))return u;
    }
    return null;
  }
  async function addFiles(list){
    let err='';
    for(const f of [...(list||[])]){
      if(W.pages.length>=H.MAX_PAGES){err=tr('wMax');break;}
      const pdf=f.type==='application/pdf'||/\.pdf$/i.test(f.name||'');
      try{
        if(pdf){msgW(tr('wReading')+'…');await addPdf(f);}
        else if(!f.type||/^image\//.test(f.type)){const img=await loadImage(f),u=toJpeg(img,img.width||img.naturalWidth,img.height||img.naturalHeight);img.close?.();if(!u)throw new Error('size');W.pages.push({url:u,from:'photo'});}
        else err=tr('wImgFail');
      }catch(e){err=tr(pdf?'wPdfFail':'wImgFail');}
      pagesChanged();paintThumbs();
    }
    msgW(err?`<span class="numerr">${err}</span>`:'');
  }
  async function addPdf(file){
    const lib=await loadPdfjs(),doc=await lib.getDocument({data:new Uint8Array(await file.arrayBuffer()),isEvalSupported:false}).promise;
    for(let i=1;i<=doc.numPages&&W.pages.length<H.MAX_PAGES;i++){
      const page=await doc.getPage(i),v1=page.getViewport({scale:1}),vp=page.getViewport({scale:H.PAGE_SIDE/Math.max(v1.width,v1.height)});
      const cv=document.createElement('canvas');cv.width=Math.round(vp.width);cv.height=Math.round(vp.height);
      const g=cv.getContext('2d');g.fillStyle='#fff';g.fillRect(0,0,cv.width,cv.height);
      await page.render({canvasContext:g,viewport:vp}).promise;
      const u=toJpeg(cv,cv.width,cv.height);if(u)W.pages.push({url:u,from:'pdf'});
    }
  }
  function paintThumbs(){
    const t=$('wThumbs');if(!t)return;
    t.innerHTML=W.pages.map((p,i)=>`<figure class="thumb"><img src="${p.url}" alt="${i+1}"><figcaption>${i+1}</figcaption><button type="button" class="rm" data-rm="${i}" aria-label="${tr('wRemove')} ${i+1}" title="${tr('wRemove')}">✕</button></figure>`).join('')||`<p class="src">${tr('wNone')}</p>`;
    $('wCount').textContent=W.pages.length+'/'+H.MAX_PAGES;
    t.querySelectorAll('[data-rm]').forEach(b=>b.onclick=()=>{W.pages.splice(Number(b.dataset.rm),1);pagesChanged();paintThumbs();});
    reportHeight();
  }
  /* the pad: a white page 1200 × 1600 drawn with pointer events (finger, stylus or mouse); once a stylus touches it,
     touches of the palm are ignored. Strokes are kept so undo can redraw. */
  const PAD_W=1200,PAD_H=1600,PAD_SIZES=[4,9,18];
  function drawStroke(g,st,from){
    const p=st.pts,i0=Math.max(0,from||0);g.save();g.lineCap='round';g.lineJoin='round';g.strokeStyle=st.tool==='eraser'?'#fff':'#14161c';g.lineWidth=st.w;
    g.beginPath();g.moveTo(p[i0][0],p[i0][1]);if(p.length===1)g.lineTo(p[0][0]+0.01,p[0][1]);for(let i=i0+1;i<p.length;i++)g.lineTo(p[i][0],p[i][1]);g.stroke();g.restore();
  }
  function padRender(c){const g=c.getContext('2d');g.fillStyle='#fff';g.fillRect(0,0,PAD_W,PAD_H);for(const st of W.padState?.strokes||[])drawStroke(g,st);}
  function padToJpeg(){const c=document.createElement('canvas');c.width=PAD_W;c.height=PAD_H;padRender(c);return toJpeg(c,PAD_W,PAD_H);}
  function padAddPage(){
    const P0=W.padState;if(!P0?.strokes.length)return false;
    if(W.pages.length>=H.MAX_PAGES){msgW(`<span class="numerr">${tr('wMax')}</span>`);return false;}
    const u=padToJpeg();if(!u)return false;W.pages.push({url:u,from:'pad'});P0.strokes=[];if($('wCanvas'))padRender($('wCanvas'));pagesChanged();paintThumbs();return true;
  }
  function paintPad(){
    const P0=W.padState||=({tool:'pen',size:1,strokes:[]});
    const seg=(name,list,cur)=>`<div class="seg" role="group">${list.map(([v,l])=>`<button type="button" data-${name}="${v}" aria-pressed="${String(cur)===String(v)}">${l}</button>`).join('')}</div>`;
    $('wPane').innerHTML=`<div class="padbar">${seg('tool',[['pen','✎ '+tr('wPen')],['eraser','⌫ '+tr('wEraser')]],P0.tool)}${seg('size',[[0,tr('wThin')],[1,tr('wMid')],[2,tr('wThick')]],P0.size)}
      <button type="button" class="mini" id="padUndo">↶ ${tr('wUndo')}</button><button type="button" class="mini" id="padClear">${tr('wClear')}</button><button type="button" class="mini" id="padAdd">＋ ${tr('wAddPage')}</button></div>
      <canvas id="wCanvas" class="padcv" width="${PAD_W}" height="${PAD_H}" aria-label="${tr('wPad')}"></canvas>`;
    const cv=$('wCanvas'),g=cv.getContext('2d');padRender(cv);
    let cur=null;
    const pt=e=>{const r=cv.getBoundingClientRect();return [(e.clientX-r.left)*PAD_W/r.width,(e.clientY-r.top)*PAD_H/r.height];};
    cv.addEventListener('pointerdown',e=>{
      if(e.pointerType==='pen')W.penSeen=true;else if(e.pointerType==='touch'&&W.penSeen)return;
      if(e.button>0||cur)return;e.preventDefault();try{cv.setPointerCapture(e.pointerId);}catch(err){}
      cur={tool:P0.tool,w:PAD_SIZES[P0.size]*(P0.tool==='eraser'?3:1),pts:[pt(e)],id:e.pointerId};P0.strokes.push(cur);drawStroke(g,cur);
    });
    cv.addEventListener('pointermove',e=>{
      if(!cur||e.pointerId!==cur.id)return;e.preventDefault();
      const n=cur.pts.length,evs=e.getCoalescedEvents?.()||[];for(const x of evs.length?evs:[e])cur.pts.push(pt(x));drawStroke(g,cur,n-1);
    });
    const end=e=>{if(cur&&e.pointerId===cur.id){cur=null;saveDraft();}};
    cv.addEventListener('pointerup',end);cv.addEventListener('pointercancel',end);
    cv.addEventListener('touchmove',e=>e.preventDefault(),{passive:false});
    $('wPane').querySelectorAll('[data-tool]').forEach(b=>b.onclick=()=>{P0.tool=b.dataset.tool;$('wPane').querySelectorAll('[data-tool]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));});
    $('wPane').querySelectorAll('[data-size]').forEach(b=>b.onclick=()=>{P0.size=Number(b.dataset.size);$('wPane').querySelectorAll('[data-size]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));});
    $('padUndo').onclick=()=>{P0.strokes.pop();padRender(cv);saveDraft();};
    $('padClear').onclick=()=>{P0.strokes=[];padRender(cv);saveDraft();};
    $('padAdd').onclick=padAddPage;
    reportHeight();
  }
  const wsteps=stage=>`<span class="wsteps"><span class="${stage==='read'?'on':'done'}">${tr('wReading')}</span> → <span class="${stage==='grade'?'on':''}">${tr('wGrading')}</span><span class="dots" aria-hidden="true"></span></span>`;
  /* the pages changed: an earlier reading no longer matches them */
  function pagesChanged(){if(W.read){W.read=null;if($('wRead'))$('wRead').innerHTML='';setSendLabel();}saveDraft();}
  const setSendLabel=()=>{const b=$('wSend');if(b){b.textContent=tr(W.read?'wReread':'wSendRead');b.classList.toggle('primary',!W.read);}};
  const gradeError=(r,code)=>r.status===404&&code!=='read_not_found'?tr('wSoon'):code==='login_required'||r.status===401?tr('wLogin'):code==='grade_limit'||r.status===429?tr('wLimit'):
    code==='read_expired'||code==='read_not_found'?tr('wExpired'):code==='read_used'?tr('wUsed'):code==='transcript_changed'?tr('wChanged'):code==='unreadable'||r.status===422?tr('wUnreadable'):r.status===400?tr('wBad'):tr('wFail');
  async function gradePost(body){
    let r=null,j={};
    try{r=await fetch(API+'/api/learn/grade',{method:'POST',headers:{'content-type':'application/json',Authorization:'Bearer '+token()},body:JSON.stringify(body)});j=await r.json().catch(()=>({}));}
    catch(e){r=null;}
    return{r,j};
  }
  const confHtml=c=>Number.isFinite(c)?(c<0.6?`<span class="conf low">${tr('wLowConf')}</span>`:`<span class="conf">${tr('wConf')} ${Math.round(100*c)}%</span>`):'';
  /* step 1: the pages are read (one model call, one of today's markings); the learner fixes the reading, then step 2 marks it */
  async function sendWritten(){
    if(W.busy)return;const item=W.item,ctx=W.ctx;
    if(!token()){msgW(tr('wLogin'));return;}
    if(W.padState?.strokes.length)padAddPage();
    if(!W.pages.length){msgW(`<span class="numerr">${tr('wNone')}</span>`);return;}
    W.busy=true;$('wSend').disabled=true;msgW(wsteps('read'));$('wResult').innerHTML='';$('wRead').innerHTML='';W.read=null;
    const {r,j}=await gradePost({step:'read',item:H.gradeItem(ctx.gradeItem()),pages:W.pages.map(p=>p.url),level:studyLevel(),lang:state.lang});
    W.busy=false;
    if(W.item!==item||!$('wSend'))return;
    $('wSend').disabled=false;
    if(!r){msgW(tr('wFail'),'bad');return;}
    if(!r.ok){if(j.error==='grade_limit'&&state.plan)state.plan.gradeLeft=0;msgW(gradeError(r,j.error),r.status===404?'soon':'bad');return;}
    msgW('');if(state.plan&&Number.isFinite(j.left)){state.plan.gradeLeft=j.left;if($('wLeftTop'))$('wLeftTop').textContent=`${tr('wLeft')}: ${j.left}`;}
    /* a server from before the two steps marks at once */
    if(j.step!=='read'||!Number.isInteger(j.read_id)){gradeDone(item,ctx,j);return;}
    W.read={id:j.read_id,transcript:String(j.transcript||''),confidence:j.confidence};
    paintRead();setSendLabel();
  }
  function paintRead(){
    const R=W.read,box=$('wRead');if(!R||!box)return;
    box.innerHTML=`<section class="wread"><p class="wrhead"><b>${tr('wReadTitle')}</b> ${confHtml(R.confidence)}</p>
      <div class="wrbody"><div class="thumbs mini">${W.pages.map((p,i)=>`<a href="${p.url}" target="_blank" rel="noopener"><img src="${p.url}" alt="${i+1}"></a>`).join('')}</div>
      <textarea id="wTx" rows="8" spellcheck="false" aria-label="${tr('wTranscript')}">${esc(R.transcript)}</textarea></div>
      <div id="wTxPrev" class="wtrans"></div>
      <p class="src">${tr('wReadNote')}</p>
      <div class="ractions"><button type="button" class="primary" id="wGrade">${tr('wGradeBtn')}</button></div></section>`;
    const prev=()=>{$('wTxPrev').innerHTML=textHtml($('wTx').value);typeset($('wTxPrev'));reportHeight();};
    let pt=0;$('wTx').oninput=()=>{clearTimeout(pt);pt=setTimeout(prev,400);};prev();
    $('wGrade').onclick=gradeRead;
    reportHeight();$('wRead').scrollIntoView?.({block:'nearest'});
  }
  async function gradeRead(){
    if(W.busy||!W.read)return;const item=W.item,ctx=W.ctx,R=W.read,text=$('wTx').value.trim();
    if(!text){msgW(`<span class="numerr">${tr('wEmptyT')}</span>`);return;}
    W.busy=true;$('wGrade').disabled=true;$('wSend').disabled=true;msgW(wsteps('grade'));
    const {r,j}=await gradePost({step:'grade',read_id:R.id,transcript:text,item:H.gradeItem(ctx.gradeItem()),level:studyLevel(),lang:state.lang});
    W.busy=false;
    if(W.item!==item||!$('wSend'))return;
    $('wSend').disabled=false;if($('wGrade'))$('wGrade').disabled=false;
    if(!r){msgW(tr('wFail'),'bad');return;}
    if(!r.ok){
      msgW(gradeError(r,j.error),'bad');
      /* the reading cannot be marked any more: back to sending the pages */
      if(['read_expired','read_not_found','read_used'].includes(j.error)){W.read=null;$('wRead').innerHTML='';setSendLabel();}
      return;
    }
    msgW('');W.read=null;$('wRead').innerHTML='';setSendLabel();
    gradeDone(item,ctx,j);
  }
  function gradeDone(item,ctx,j){
    /* graded: the draft is done with */
    clearTimeout(draftTimer);Drafts.del(item.id).catch(()=>{});
    applyGrade(item,ctx,j);
  }
  function stepUp(unit){
    const k=saved.skills[unit],cur=Math.max(saved.level[unit]||0,ratingStep(k?k.rating:START)),nx=Math.min(10,cur+1);
    saved.level[unit]=nx;if(k)k.rating=Math.max(k.rating,stepRating(nx));
    const s=state.session;if(s&&s.unit===unit&&s.steps?.length){const up=s.steps.find(x=>x>s.level);if(up)s.level=up;}
  }
  /* pass and partial settle the problem at once; a retry settles only when the learner moves on */
  function settle(item,ctx,mv){
    const s=state.session;stopPace(item);
    if(!ctx.noReview)noteOutcome(item,mv.review);
    record(item.id,ctx.mode,ctx.unit,ctx.step,mv.result);
    if(mv.solved){ctx.solve();if(s)s.right++;}else if(mv.review==='wrong')ctx.miss();
    if(!saved.days.includes(today())){saved.days.push(today());saved.days=saved.days.slice(-400);}
    ctx.lock();save();paintStats();
  }
  const pts=v=>{const x=Number(v)||0;return String(Math.round(x*10)/10);};
  function applyGrade(item,ctx,j){
    const fraction=Math.max(0,Math.min(1,Number.isFinite(Number(j.fraction))?Number(j.fraction):j.max?j.score/j.max:0));
    const band=H.BANDS.includes(j.band)?j.band:H.bandOf(fraction),was=ctx.answered(),s=state.session;
    saved.graded[item.id]={fraction,band,at:Math.floor(Date.now()/1000)};
    let gain=0,note='';
    if(!was){
      gain=H.gradedGain(H.baseXp(ctx.xpItem),band,W.bandSeen);
      if(!W.bandSeen||BAND_RANK[band]>BAND_RANK[W.bandSeen])W.bandSeen=band;
      if(gain){if(s)s.xp+=gain;saved.xp+=gain;}
      const h=H.pushGraded(saved.gradedHist,ctx.unit,fraction);saved.gradedHist=h.hist;if(h.up){stepUp(ctx.unit);note=tr('wUnitUp')+' ↑';}
    }
    save();paintStats();
    const last=$('lastgr');if(last)last.outerHTML=lastGradedHtml(item.id);
    const items=Array.isArray(j.items)?j.items:[],mv=H.moveOn(band);
    $('wResult').innerHTML=`<div class="wres band-${band}">
      <div class="wtop"><span class="wscore"><b>${pts(j.score)}</b> / ${pts(j.max)} <small>${Math.round(100*fraction)}%</small></span><span class="bandtag ${band}">${bandLabel(band)}</span>${gain?`<span class="wxp">+${gain} XP</span>`:''}${confHtml(j.confidence)}</div>
      ${was?'':`<p class="wnote">${tr(band==='pass'?'wPassNote':band==='partial'?'wPartialNote':ctx.hint?'wRetryNote':'wRetryPlain')}${note?' · <b>'+note+'</b>':''}</p>`}
      ${items.length?`<table class="rubric"><caption>${tr('wRubric')}</caption><tbody>${items.map(x=>`<tr class="${Number(x.got)>=Number(x.max)?'full':Number(x.got)>0?'some':'none'}"><td><span class="rd">${esc(x.desc||'')}</span>${x.note?`<small>${esc(x.note)}</small>`:''}</td><td class="pts">${pts(x.got)}/${pts(x.max)}</td></tr>`).join('')}</tbody></table>`:''}
      ${j.feedback?`<div class="wfb">${textHtml(j.feedback)}</div>`:''}
      ${j.transcript?`<details class="alt"><summary>${tr('wTranscript')}</summary><div class="wtrans">${textHtml(j.transcript)}</div></details>`:''}
      <p class="src">${Number.isFinite(j.left)?`${tr('wLeft')}: <b>${j.left}</b> · `:''}${tr('wAiNote')}</p>
      ${Number.isInteger(j.attempt_id)?`<div class="appeal" id="wAppeal">${appealHtml(j.attempt_id)}</div>`:''}
      ${mv.retry&&!was?`<div class="actions start"><button type="button" class="primary" id="wAgain">${tr('wRetry')}</button><button type="button" id="wOn">${tr('wMoveOn')}</button></div>`:''}</div>`;
    typeset($('wResult'));
    if(Number.isInteger(j.attempt_id))wireAppeal(j.attempt_id,item);
    if(!was&&mv.next)settle(item,ctx,mv);
    if($('wAgain')){
      $('wAgain').onclick=()=>{$('wResult').innerHTML='';ctx.hint?.();msgW(tr(ctx.hint?'wRetryNote':'wRetryPlain'));$('written').scrollIntoView?.({block:'nearest'});};
      $('wOn').onclick=()=>{settle(item,ctx,mv);$('next')?.click();};
    }
    reportHeight();
  }

  /* ── appeals: one tap and an optional line (POST /api/learn/grade/appeal); the status shows here and in the Review tab ── */
  const apLabel=st=>tr('apStatus_'+(['open','upheld','changed'].includes(st)?st:'open'));
  function appealHtml(id){
    const a=saved.appeals?.[id];
    if(a)return `<span class="tag ap-${esc(a.status)}">${apLabel(a.status)}</span>`;
    return `<button type="button" class="mini" id="apBtn" aria-expanded="false">${tr('apBtn')}</button><div id="apForm" hidden><input type="text" id="apNote" maxlength="500" placeholder="${tr('apNote')}" aria-label="${tr('apNote')}"><span class="dbtns"><button type="button" class="primary" id="apSend">${tr('apSend')}</button><button type="button" id="apCancel">${tr('apCancel')}</button></span><span class="src" id="apMsg" role="status"></span></div>`;
  }
  function wireAppeal(id,item){
    if(!$('apBtn'))return;
    const form=$('apForm');
    $('apBtn').onclick=()=>{form.hidden=!form.hidden;$('apBtn').setAttribute('aria-expanded',String(!form.hidden));if(!form.hidden)$('apNote').focus();reportHeight();};
    $('apCancel').onclick=()=>{form.hidden=true;$('apBtn').setAttribute('aria-expanded','false');reportHeight();};
    $('apSend').onclick=async()=>{
      $('apSend').disabled=true;let r=null,j={};
      try{r=await fetch(API+'/api/learn/grade/appeal',{method:'POST',headers:{'content-type':'application/json',Authorization:'Bearer '+token()},body:JSON.stringify({attempt_id:id,note:$('apNote').value.trim()})});j=await r.json().catch(()=>({}));}catch(e){r=null;}
      if(!$('wAppeal'))return;
      if(r&&(r.ok||j.error==='appeal_exists')){
        (saved.appeals||={})[id]={item:item.id,t:String(W.toolLabel||titleOf(item)||item.id).slice(0,120),status:r.ok&&j.status?j.status:'open',at:Math.floor(Date.now()/1000)};
        const keys=Object.keys(saved.appeals);if(keys.length>100)for(const k of keys.slice(0,keys.length-100))delete saved.appeals[k];
        save();$('wAppeal').innerHTML=appealHtml(id);reportHeight();return;
      }
      $('apSend').disabled=false;$('apMsg').textContent=tr('apFail');reportHeight();
    };
  }
  async function myAppealsHtml(){
    if(!token())return `<p class="src">${tr('apLogin')}</p>`;
    let list=[];try{const j=await api('/api/learn/grade/appeals/mine');list=Array.isArray(j.appeals)?j.appeals:[];}catch(e){return `<p class="src">${tr('failed')}</p>`;}
    for(const a of list)if(saved.appeals?.[a.attempt_id])saved.appeals[a.attempt_id].status=a.status;
    if(!list.length)return `<p class="src">${tr('apNone')}</p>`;
    return `<ul class="plainlist">${list.slice(0,20).map(a=>`<li><span class="name">${esc(saved.appeals?.[a.attempt_id]?.t||a.item_id)}<small>${pts(a.old_score)}${a.status==='changed'&&a.new_score!=null?' → '+pts(a.new_score):''} / ${pts(a.max)} · ${day(a.created_at)}${a.note?' · '+esc(String(a.note).slice(0,80)):''}</small>${a.reply?`<small>${tr('apReply')}: ${esc(String(a.reply).slice(0,300))}</small>`:''}</span><span class="tag ap-${esc(a.status)}">${apLabel(a.status)}</span></li>`).join('')}</ul>`;
  }

  /* ── problem reports go to the server (POST /api/learn/report), signed in or not. A report that cannot be sent stays in
     this browser and goes out later; "My reports" shows the server's status for a signed-in learner ── */
  const readReports=()=>{try{const v=JSON.parse(localStorage.getItem('hlPracticeReports')||'[]');return Array.isArray(v)?v:[];}catch(e){return [];}};
  const writeReports=list=>{try{localStorage.setItem('hlPracticeReports',JSON.stringify(list.slice(-50)));}catch(e){}};
  const sourceOf=item=>item.kind==='track'||item.kind==='contest'?item.kind:item.ch?'exam':'bank';
  async function postReport(body){
    const r=await fetch(API+'/api/learn/report',{method:'POST',headers:{'content-type':'application/json',...(token()?{Authorization:'Bearer '+token()}:{})},body:JSON.stringify(body)});
    return{status:r.status,ok:r.ok,j:await r.json().catch(()=>({}))};
  }
  /* sends what is waiting; a 400 drops the report (it will never be accepted), anything else waits for the next try */
  let flushing=false;
  async function flushReports(){
    if(flushing)return;flushing=true;
    try{
      for(const e of readReports().filter(x=>x.pending&&x.body)){
        let res;try{res=await postReport(e.body);}catch(err){break;}
        if(res.status===404||res.status>=500||res.status===429)break;
        const list=readReports(),k=list.findIndex(x=>x.at===e.at&&x.id===e.id);if(k<0)continue;
        if(res.ok)list[k]={...list[k],pending:false,sid:res.j.id??null,status:'open'};else list.splice(k,1);
        writeReports(list);
      }
    }finally{flushing=false;}
  }
  function openReport(item,label){
    const box=$('report');if(box.innerHTML){box.innerHTML='';$('reportBtn').setAttribute('aria-expanded','false');reportHeight();return;}
    $('reportBtn').setAttribute('aria-expanded','true');
    box.innerHTML=`<form class="reportf" id="reportf"><p class="rtitle">${tr('reportTitle')}</p>
      <div class="chips" role="radiogroup" aria-label="${tr('reportTitle')}">${REASONS.map(r=>`<label class="chip"><input type="radio" name="rr" value="${r}"><span>${tr(r)}</span></label>`).join('')}</div>
      <textarea id="rnote" rows="3" maxlength="1000" placeholder="${tr('reportNote')}" aria-label="${tr('reportNote')}"></textarea>
      <div class="ractions"><button type="submit" class="primary" id="rsend">${tr('reportSend')}</button><button type="button" id="rcancel">${tr('reportCancel')}</button><span class="numerr" id="rerr"></span></div></form>`;
    const f=$('reportf'),reason=()=>f.querySelector('input[name=rr]:checked')?.value;
    $('rcancel').onclick=()=>{box.innerHTML='';$('reportBtn').setAttribute('aria-expanded','false');reportHeight();};
    f.onchange=()=>{$('rerr').textContent='';};
    f.onsubmit=async e=>{
      e.preventDefault();const r=reason();if(!r){$('rerr').textContent=tr('reportPick');return;}
      const note=$('rnote').value.trim().slice(0,1000),page=`https://haslalab.org/?lang=${state.lang}#/learn/practice${/^[a-z0-9]+-[a-z0-9-]{1,40}$/.test(item.id)?'?item='+item.id:''}`;
      const body={item_id:String(item.id).slice(0,80),source:sourceOf(item),reason:REASON_API[r],note:(label?String(label).slice(0,120)+'\n':'')+note,page:page.slice(0,300),lang:state.lang};
      body.note=body.note.slice(0,1000);
      const entry={id:item.id,r,note:note.slice(0,800),at:Math.floor(Date.now()/1000),t:String(label||'').slice(0,120),body,pending:true};
      writeReports([...readReports(),entry]);
      $('rsend').disabled=true;
      let res=null;try{res=await postReport(body);}catch(err){}
      const list=readReports(),k=list.findIndex(x=>x.at===entry.at&&x.id===entry.id);
      let text;
      if(res?.ok){if(k>=0){list[k]={...list[k],pending:false,sid:res.j.id??null,status:'open'};writeReports(list);}text=tr('rSentOk');}
      else if(res&&res.status===400){if(k>=0){list.splice(k,1);writeReports(list);}$('rerr').textContent=tr('wBad');$('rsend').disabled=false;return;}
      else{text=res?.status===429?tr('rLimit'):tr('rQueued');setTimeout(flushReports,60000);}
      box.innerHTML=`<p class="src reportdone" role="status">${text}</p>`;$('reportBtn').setAttribute('aria-expanded','false');reportHeight();
    };
    reportHeight();
  }
  /* the learner's own reports with the server's status (GET /api/learn/reports/mine) joined to this browser's list */
  async function myReportsHtml(){
    const local=readReports().slice().reverse();let server=[];
    if(token()){try{const j=await api('/api/learn/reports/mine');server=Array.isArray(j)?j:Array.isArray(j.reports)?j.reports:[];}catch(e){}}
    const bySid=new Map(server.map(x=>[x.id,x])),seen=new Set();
    const rows=local.map(r=>{const sv=r.sid!=null?bySid.get(r.sid):null;if(sv)seen.add(sv.id);return{t:r.t||r.id,id:r.id,reason:r.r,note:r.note,at:r.at,status:r.pending?'pending':sv?.status||r.status||'open'};});
    const inv=Object.fromEntries(Object.entries(REASON_API).map(([k,v])=>[v,k]));
    for(const sv of server)if(!seen.has(sv.id))rows.push({t:sv.item_id,id:sv.item_id,reason:inv[sv.reason]||'rOther',note:sv.note,at:sv.created_at,status:sv.status});
    if(!rows.length)return `<p class="src">${tr('noReports')}</p>`;
    return `<ul class="plainlist">${rows.slice(0,20).map(r=>`<li><span class="name">${esc(r.t)}<small>${esc(r.id)} · ${tr(REASONS.includes(r.reason)?r.reason:'rOther')}${r.note?' · '+esc(String(r.note).slice(0,80)):''} · ${day(r.at)}</small></span><span class="tag rst-${esc(r.status)}">${tr('rStatus_'+(['open','fixed','rejected','pending'].includes(r.status)?r.status:'open'))}</span></li>`).join('')}</ul>`;
  }
  /* ── one set of fixed problems run through the usual session (custom sets, review, saved problems) ── */
  function runSet(o){
    if(!o.items.length){o.back();return;}
    state.session={mode:'custom',unit:'custom',fixed:true,custom:true,label:o.label,back:o.back,again:o.again,timer:o.timer!==false,format:o.format,total:o.items.length,items:o.items,steps:[],level:0,n:0,right:0,run:0,seen:new Set(),current:null,answered:false,xp:0,times:[]};
    next();
  }
  /* competition problems transcribed per problem, as set items (self-marked) */
  async function loadContests(){if(!state.contests){const r=await fetch('practice/contests.json');if(!r.ok)throw new Error('contests');state.contests=(await r.json()).contests;}return state.contests;}
  async function allContestItems(){
    if(state.allContest)return state.allContest;
    const cs=await loadContests(),lists=await Promise.all(cs.map(c=>contestItems(c.key)));
    return state.allContest=cs.flatMap((c,k)=>lists[k].filter(i=>c.problems.some(p=>p.id===i.pdf)).map(i=>({...i,kind:'contest',from:'contest',c:c.key,s:c.step,u:'contest/'+c.key,year:Number(i.year)||0})));
  }
  /* ── study level: picked in the first questions or on the today page; it picks the pool ── */
  const studyLevel=()=>/^L[1-4]$/.test(saved.studyLevel||'')?saved.studyLevel:H.defaultLevel(saved.profile);
  async function levelItems(key){
    const L=H.levelInfo(key),parts=[];
    if(L.calc)parts.push(allExamItems().then(a=>a.map(i=>({...i,from:'calc'}))).catch(()=>[]));
    for(const k of L.tracks)parts.push(trackItems(k).then(a=>a.map(i=>({...i,from:'track:'+k}))).catch(()=>[]));
    if(L.contests.length)parts.push(allContestItems().then(a=>a.filter(i=>L.contests.includes(i.c))).catch(()=>[]));
    return (await Promise.all(parts)).flat();
  }
  const levelName=key=>nameOf(H.levelInfo(key).name);
  function levelCards(cur){
    return H.STUDY_LEVELS.map((L,n)=>{const has=L.has[state.lang]||L.has.en,soon=L.soon[state.lang]||L.soon.en;
      return `<button type="button" class="unit lvcard${L.key===cur?' cur':''}" data-level="${L.key}" aria-pressed="${L.key===cur}"><span class="lvno">${n+1}</span><span class="name"><b>${esc(nameOf(L.name))}</b><small>${tr('lvHas')}: ${has.map(esc).join(' · ')}</small>${soon.length?`<small class="soon">${soon.map(x=>`<span class="tag">${tr('lvSoon')}</span> ${esc(x)}`).join(' ')}</small>`:''}${L.bank?`<small>${tr('lvBankNote')}</small>`:''}</span></button>`;}).join('');
  }
  function levelHome(){
    state.mode='level';state.session=null;paintTabs();paintStats();tellUnit('');
    $('app').innerHTML=`<section class="session onboard"><div class="shead"><button type="button" class="back" id="quit">${tr('quit')}</button><span class="unitname">${tr('lvTitle')}</span></div>
      <h2>${tr('lvPick')}</h2><p class="src">${tr('lvIntro')}</p><div class="obopts">${levelCards(studyLevel())}</div></section>`;
    $('quit').onclick=todayHome;
    $('app').querySelectorAll('[data-level]').forEach(b=>b.onclick=()=>{saved.studyLevel=b.dataset.level;delete saved.customOpts?.source;save();todayHome();});
    reportHeight();
  }
  /* the problems a set can draw from: each source tagged (from) so the filter can tell them apart */
  async function setPool(source){
    state.setPools||={};if(state.setPools[source])return state.setPools[source];
    if(source.startsWith('level:'))return state.setPools[source]=await levelItems(source.slice(6));
    const tracks=await loadTracks(),parts=[];
    if(source==='all'||source==='calc')parts.push(allExamItems().then(a=>a.map(i=>({...i,from:'calc'}))));
    for(const t of tracks)if(source==='all'||source==='track:'+t.key)parts.push(trackItems(t.key).then(a=>a.map(i=>({...i,from:'track:'+t.key}))));
    if(source==='all'||source==='contest')parts.push(allContestItems().catch(()=>[]));
    return state.setPools[source]=(await Promise.all(parts)).flat();
  }
  const typeable=new Map();
  const canType=i=>{if(i.kind==='contest')return false;if(!typeable.has(i.id))typeable.set(i.id,i.kind==='track'?i.type==='num'||!!freeOfTrack(i):!i.ch.every(c=>!c.c.length)&&!!freeOfExam(i));return typeable.get(i.id);};
  const hasChoices=i=>i.kind==='track'?i.type==='mc':i.kind!=='contest';
  const solvedMap=()=>({...saved.solved,...Object.fromEntries(Object.entries(saved.contest.done).filter(([,v])=>v===1))});
  const setOpts=()=>{const d={source:'all',units:[],min:1,max:10,count:10,format:'typed',contest:'',yearMin:0,yearMax:0,timer:true};
    d.source='level:'+studyLevel();
    return{...d,...(saved.customOpts||{})};};
  async function customHome(){
    state.mode='custom';state.session=null;paintTabs();paintStats();tellUnit('');
    $('app').innerHTML=`<p>${tr('loading')}</p>`;
    let tracks;try{tracks=await loadTracks();await loadContests().catch(()=>[]);}catch(e){failed(customHome);return;}
    const o=setOpts();let unitsOpen=false,job=0;
    const seg=(id,list,cur)=>`<div class="seg" role="group" id="${id}">${list.map(([v,l])=>`<button type="button" data-v="${v}" aria-pressed="${String(cur)===String(v)}">${l}</button>`).join('')}</div>`;
    const render=async()=>{
      const my=++job;
      $('app').innerHTML=`<section class="session builder"><h2>${tr('tabCustom')}</h2><p class="src">${tr('customIntro')}</p><p id="cMatch" class="matchline">${tr('loading')}</p></section>`;
      let pool;try{pool=await setPool(o.source);}catch(e){failed(customHome);return;}
      if(my!==job)return;
      const graded=pool.filter(i=>i.from!=='contest'),contests=pool.filter(i=>i.from==='contest');
      const unitSet=new Set(graded.map(i=>i.u));o.units=o.units.filter(u=>unitSet.has(u));
      const areas=P.AREAS.map(a=>({a,subs:a.subtopics.map(s=>a.key+'/'+s.key).filter(u=>unitSet.has(u))})).filter(x=>x.subs.length);
      const steps=[...new Set(pool.map(i=>i.s))].sort((x,y)=>x-y);
      const lo=steps[0]||1,hi=steps[steps.length-1]||10;o.min=Math.max(lo,Math.min(o.min,hi));o.max=Math.min(hi,Math.max(o.max,o.min));
      const inC=contests.filter(i=>!o.contest||i.c===o.contest),years=[...new Set(inC.map(i=>i.year))].sort((x,y)=>x-y);
      if(o.yearMin&&!years.includes(o.yearMin))o.yearMin=0;if(o.yearMax&&!years.includes(o.yearMax))o.yearMax=0;
      const chosen=new Set(o.units),areaOn=x=>x.subs.every(u=>chosen.has(u));
      const stepOpt=(v)=>steps.map(st=>`<option value="${st}"${st===v?' selected':''}>${st} · ${tr(LEVELS[levelOf(st)])}</option>`).join('');
      const srcOpts=[...H.STUDY_LEVELS.map(L=>['level:'+L.key,tr('lvTitle')+' '+L.key.slice(1)+' · '+nameOf(L.name)]),['all',tr('cAll')],...tracks.map(t=>['track:'+t.key,nameOf(t.name)]),['calc',tr('cCalc')],['contest',tr('cContest')]];
      $('app').innerHTML=`<section class="session builder"><h2>${tr('tabCustom')}</h2><p class="src">${tr('customIntro')}</p>
        <div class="field"><label class="flabel" for="cSrc">${tr('cSource')}</label><select id="cSrc">${srcOpts.map(([v,l])=>`<option value="${v}"${v===o.source?' selected':''}>${esc(l)}</option>`).join('')}</select></div>
        ${areas.length?`<div class="field"><span class="flabel">${tr('cTopics')}</span><div class="chips" id="cAreas"><button type="button" class="chipbtn" data-area="" aria-pressed="${!chosen.size}">${tr('cAllTopics')}</button>${areas.map(x=>`<button type="button" class="chipbtn" data-area="${x.a.key}" aria-pressed="${chosen.size>0&&areaOn(x)}">${esc(areaName(x.a))}</button>`).join('')}</div>
          <details class="alt units" id="cUnits"${unitsOpen?' open':''}><summary>${tr('cPickUnits')}${chosen.size?` (${chosen.size})`:''}</summary>${areas.map(x=>`<p class="sublabel">${esc(areaName(x.a))}</p><div class="chips">${x.subs.map(u=>`<button type="button" class="chipbtn" data-u="${u}" aria-pressed="${chosen.has(u)}">${esc(unitName(u))}</button>`).join('')}</div>`).join('')}</details></div>`:''}
        <div class="field"><span class="flabel">${tr('cDiff')}</span><div class="range"><select id="cMin" aria-label="${tr('cDiff')} min">${stepOpt(o.min)}</select><span>–</span><select id="cMax" aria-label="${tr('cDiff')} max">${stepOpt(o.max)}</select></div></div>
        <div class="field"><span class="flabel">${tr('cCount')}</span>${seg('cCount',[[5,'5'],[10,'10'],[20,'20']],o.count)}</div>
        ${graded.length?`<div class="field"><span class="flabel">${tr('cFormat')}</span>${seg('cFormat',[['choice',tr('cChoice')],['typed',tr('cTyped')]],o.format)}<p class="src">${tr('cFormatNote')}</p></div>`:''}
        ${contests.length?`<div class="field"><label class="flabel" for="cComp">${tr('cCompetition')}</label><select id="cComp"><option value="">${tr('cAnyContest')}</option>${state.contests.filter(c=>contests.some(i=>i.c===c.key)).map(c=>`<option value="${c.key}"${c.key===o.contest?' selected':''}>${esc(nameOf(c.name))}</option>`).join('')}</select>
          <span class="flabel">${tr('cYears')}</span><div class="range"><select id="cY1" aria-label="${tr('cYears')} min">${years.map(y=>`<option value="${y}"${y===(o.yearMin||years[0])?' selected':''}>${y}</option>`).join('')}</select><span>–</span><select id="cY2" aria-label="${tr('cYears')} max">${years.map(y=>`<option value="${y}"${y===(o.yearMax||years[years.length-1])?' selected':''}>${y}</option>`).join('')}</select></div>
          ${graded.length?`<p class="src">${tr('cContestNote')}</p>`:''}</div>`:''}
        <div class="field"><label class="check"><input type="checkbox" id="cTimer"${o.timer?' checked':''}> ${tr('cTimer')}</label></div>
        <p class="matchline" id="cMatch"></p>
        <div class="actions"><button type="button" class="primary" id="cGo">${tr('cStartSet')}</button></div></section>`;
      const count=H.matchSet(pool,o,canType,hasChoices).length;
      $('cMatch').innerHTML=count?`${tr('cMatch')}: <b>${count}</b>${count<o.count?` · ${count} ${tr('problems')}`:''}`:`<span class="numerr">${tr('cNoMatch')}</span>`;
      $('cGo').disabled=!count;
      const keep=()=>{saved.customOpts={...o};save();};
      $('cSrc').onchange=()=>{o.source=$('cSrc').value;o.units=[];o.min=1;o.max=10;o.yearMin=o.yearMax=0;o.contest='';keep();render();};
      $('app').querySelectorAll('[data-area]').forEach(b=>b.onclick=()=>{const x=areas.find(y=>y.a.key===b.dataset.area);
        if(!x)o.units=[];else if(chosen.size&&areaOn(x))o.units=o.units.filter(u=>!x.subs.includes(u));else o.units=[...new Set([...o.units,...x.subs])];keep();render();});
      $('app').querySelectorAll('[data-u]').forEach(b=>b.onclick=()=>{const u=b.dataset.u;o.units=chosen.has(u)?o.units.filter(x=>x!==u):[...o.units,u];unitsOpen=true;keep();render();});
      if($('cUnits'))$('cUnits').ontoggle=()=>{unitsOpen=$('cUnits').open;reportHeight();};
      $('cMin').onchange=()=>{o.min=Number($('cMin').value);if(o.max<o.min)o.max=o.min;keep();render();};
      $('cMax').onchange=()=>{o.max=Number($('cMax').value);if(o.min>o.max)o.min=o.max;keep();render();};
      $('cCount').querySelectorAll('[data-v]').forEach(b=>b.onclick=()=>{o.count=Number(b.dataset.v);keep();render();});
      $('cFormat')?.querySelectorAll('[data-v]').forEach(b=>b.onclick=()=>{o.format=b.dataset.v;keep();render();});
      if($('cComp')){$('cComp').onchange=()=>{o.contest=$('cComp').value;o.yearMin=o.yearMax=0;keep();render();};
        $('cY1').onchange=()=>{o.yearMin=Number($('cY1').value);if(o.yearMax&&o.yearMax<o.yearMin)o.yearMax=o.yearMin;keep();render();};
        $('cY2').onchange=()=>{o.yearMax=Number($('cY2').value);if(o.yearMin&&o.yearMin>o.yearMax)o.yearMin=o.yearMax;keep();render();};}
      $('cTimer').onchange=()=>{o.timer=$('cTimer').checked;keep();};
      $('cGo').onclick=()=>customStart({...o});
      reportHeight();
    };
    render();
  }
  async function customStart(o){
    $('app').innerHTML=`<p>${tr('loading')}</p>`;
    let pool;try{pool=await setPool(o.source);}catch(e){failed(()=>customStart(o));return;}
    const {items}=H.buildSet(pool,o,{recent:saved.recent,solved:solvedMap(),canType,hasChoices});
    runSet({items,label:tr('customName'),back:customHome,again:()=>customStart(o),timer:o.timer,format:o.format});
  }
  /* ── review: what is due today, the saved problems, my reports, and the progress backup ── */
  async function resolveItems(ids,extra){
    const meta=id=>saved.review[id]||saved.later[id]||extra?.[id]||{},parts=[];
    if(ids.some(id=>meta(id).k==='exam'))parts.push(allExamItems().catch(()=>[]));
    for(const k of new Set(ids.filter(id=>meta(id).k==='track').map(id=>id.split('-')[0])))parts.push(trackItems(k).catch(()=>[]));
    if(ids.some(id=>meta(id).k==='contest'))parts.push(allContestItems().catch(()=>[]));
    const byId=new Map((await Promise.all(parts)).flat().map(i=>[i.id,i]));
    return ids.map(id=>byId.get(id)).filter(Boolean);
  }
  const entryName=e=>e.k==='contest'?nameOf(state.contests?.find(c=>c.key===e.c)?.name)||e.c:unitName(e.u||'');
  async function reviewHome(){
    state.mode='review';state.session=null;paintTabs();paintStats();tellUnit('');
    await loadContests().catch(()=>{});
    const due=dueNow(),all=Object.entries(saved.review),later=Object.entries(saved.later).sort((a,b)=>b[1].at-a[1].at);
    const upcoming=all.filter(([,r])=>r.due>today()).sort((a,b)=>a[1].due<b[1].due?-1:1)[0];
    $('app').innerHTML=`<section class="session reviewcard"><h2>${tr('tabReview')}</h2><p class="src">${tr('reviewIntro')}</p>
        <div class="stats rstats"><span class="stat"><b>${due.length}</b>${tr('dueToday')}</span><span class="stat"><b>${all.length}</b>${tr('inQueue')}</span>${upcoming?`<span class="stat"><b>${esc(upcoming[1].due.slice(5))}</b>${tr('nextDue')}</span>`:''}</div>
        ${due.length?`<ol class="todaylist">${due.slice(0,20).map(id=>{const r=saved.review[id];return `<li><span class="tag review">${H.REVIEW_DAYS[r.box]}d</span> ${esc(r.t||entryName(r))} <small>${esc(r.t?entryName(r):'')}</small></li>`;}).join('')}</ol>`:`<p>${tr('noDue')}</p>`}
        <div class="actions"><button type="button" class="primary" id="goReview"${due.length?'':' disabled'}>${tr('startReview')}${due.length?` (${Math.min(20,due.length)})`:''}</button></div></section>
      <section class="area laterlist"><h2>${tr('laterTitle')}</h2>${later.length?`<ul class="plainlist">${later.map(([id,e])=>`<li><span class="name">${esc(e.t||id)}<small>${esc(entryName(e))}</small></span><button type="button" class="mini" data-unlater="${esc(id)}">${tr('removeLater')}</button></li>`).join('')}</ul>
        <div class="actions"><button type="button" class="primary" id="goLater">${tr('startLater')} (${Math.min(20,later.length)})</button></div>`:`<p class="src">${tr('noLater')}</p>`}</section>
      <section class="area laterlist"><h2>${tr('apMine')}</h2><div id="myAppeals"><p class="src">${tr('loading')}</p></div></section>
      <section class="area laterlist"><h2>${tr('myReports')}</h2><div id="myReports"><p class="src">${tr('loading')}</p></div></section>
      ${settingsHtml()}`;
    $('goReview').onclick=async()=>{$('app').innerHTML=`<p>${tr('loading')}</p>`;const items=await resolveItems(due.slice(0,20));runSet({items,label:tr('tabReview'),back:reviewHome,again:reviewHome});};
    if($('goLater'))$('goLater').onclick=async()=>{$('app').innerHTML=`<p>${tr('loading')}</p>`;const items=await resolveItems(later.slice(0,20).map(([id])=>id));runSet({items,label:tr('laterTitle'),back:reviewHome,again:reviewHome});};
    $('app').querySelectorAll('[data-unlater]').forEach(b=>b.onclick=()=>{delete saved.later[b.dataset.unlater];save();reviewHome();});
    wireSettings(reviewHome);reportHeight();
    flushReports().catch(()=>{}).then(myReportsHtml).then(h=>{if($('myReports')&&state.mode==='review'){$('myReports').innerHTML=h;reportHeight();}});
    myAppealsHtml().then(h=>{if($('myAppeals')&&state.mode==='review'){$('myAppeals').innerHTML=h;save();reportHeight();}});
  }
  /* ── progress backup: export the saved state as a file, import one (checked, then merged item by item), reset ── */
  function settingsHtml(){return `<details class="area settings" id="settings"><summary>${tr('settings')}</summary><p class="src">${tr('settingsNote')}</p>
    <div class="actions start"><button type="button" id="exportP">${tr('exportP')}</button><button type="button" id="importP">${tr('importP')}</button><input type="file" id="importFile" accept="application/json,.json" hidden><button type="button" class="danger" id="resetP">${tr('resetP')}</button></div><p class="src" id="setMsg" role="status"></p></details>`;}
  function wireSettings(again){
    const msg=t=>{$('setMsg').textContent=t;reportHeight();};
    $('settings').ontoggle=reportHeight;
    $('exportP').onclick=()=>{
      const blob=new Blob([JSON.stringify(H.exportOf(saved),null,1)],{type:'application/json'}),a=document.createElement('a');
      a.href=URL.createObjectURL(blob);a.download=`haslalab-practice-${today()}.json`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),4000);
    };
    $('importP').onclick=()=>$('importFile').click();
    $('importFile').onchange=async()=>{
      const file=$('importFile').files?.[0];if(!file)return;
      if(file.size>4e6){msg(tr('imp_not_backup'));return;}
      const v=H.validateBackup(await file.text());
      if(!v.ok){msg(tr('imp_'+v.error));return;}
      saved=fill(Object.assign(saved,H.mergeBackup(saved,v.state)));save();scheduleSync();paintStats();
      await again();if($('settings')){$('settings').open=true;msg(tr('importDone'));}
    };
    $('resetP').onclick=async()=>{
      if(!confirm(tr('resetConfirm')))return;
      saved=fill({});save();paintStats();await again();if($('settings')){$('settings').open=true;msg(tr('resetDone'));}
    };
  }
  /* ── the weekly league (community/src/league.js, drawn by league-view.js): the member's group this week with the
     promotion, demotion and (in Master) rebirth zones; guests see how it works and a sign-in button ── */
  async function leagueHome(){
    state.mode='league';state.session=null;paintTabs();paintStats();tellUnit('');
    const V=window.HL_LEAGUE_VIEW;if(!V){failed(leagueHome);return;}
    V.addStyle(document);
    if(!token()){$('app').innerHTML=V.guestHtml(state.lang);reportHeight();return;}
    $('app').innerHTML=`<p>${tr('loading')}</p>`;
    let data;try{data=await api('/api/league/me');}catch(e){if(state.mode==='league'){$('app').innerHTML=`<p>${tr('leagueFailed')}</p><button type="button" id="retry">${tr('retry')}</button>`;$('retry').onclick=leagueHome;reportHeight();}return;}
    if(state.mode!=='league'||state.session)return;
    if(data.today){state.today=data.today;state.todayAt=today();paintStats();}
    $('app').innerHTML=V.meHtml(data,state.lang,{rankingHref:'/#/ranking',settingsHref:SETTINGS_HREF,avatarSrc:k=>API+'/api/avatar/'+k});
    reportHeight();
  }
  /* a member from before the sign-up questions, on the practice page opened on its own (inside the site, the page
     around this frame asks): the two fields once, "Later" asks again next visit */
  function learnerPrompt(){
    const lf=window.HL_LEARNER_FORM;if(!lf||embedded||!state.learnerMissing||$('lfPrompt'))return;
    try{if(sessionStorage.getItem('hlLearnerLater'))return;}catch(e){}
    lf.addStyle(document);
    const box=document.createElement('section');box.id='lfPrompt';box.className='lf-prompt';
    box.innerHTML=`<h2>${tr('lfAsk')}</h2><p>${tr('lfAskSub')}</p><form>${lf.fieldsHtml(state.lang,{})}<div class="lf-acts"><button type="submit" class="primary">${tr('lfSave')}</button><button type="button" data-later>${tr('lfLater')}</button><span class="lf-err" role="status"></span></div></form>`;
    $('app').before(box);
    const f=box.querySelector('form'),read=lf.wire(f,state.lang),err=box.querySelector('.lf-err');
    box.querySelector('[data-later]').onclick=()=>{try{sessionStorage.setItem('hlLearnerLater','1');}catch(e){}box.remove();reportHeight();};
    f.onsubmit=async e=>{e.preventDefault();const v=read();if(!v){err.textContent=tr('lfPick');return;}
      try{const r=await api('/api/me/learner','PUT',v);state.learner=r;state.learnerMissing=false;box.remove();paintStats();reportHeight();}catch(er){err.textContent=tr('lfFailed');}};
    reportHeight();
  }
  const MODES={level:levelHome,start:startHome,play:playHome,today:todayHome,review:reviewHome,custom:customHome,tracks:tracksHome,exam:home,bank:bankHome,contest:contestHome,class:classHome,league:leagueHome};

  function applyTheme(){const t=params.get('theme'),dark=t==='dark'||(t!=='light'&&matchMedia('(prefers-color-scheme: dark)').matches);document.documentElement.dataset.theme=dark?'dark':'light';}
  function translate(){document.documentElement.lang=state.lang;document.querySelectorAll('[data-i18n]').forEach(el=>{el.textContent=tr(el.dataset.i18n);});$('note').textContent=tr('note');document.title=tr('title')+' · HaslaLab';}
  window.addEventListener('message',event=>{
    if(embedded&&event.origin===location.origin&&event.source===window.parent&&event.data?.type==='hl-practice-learner'){loadLearner().then(()=>paintStats());return;}
    if(!embedded||event.origin!==location.origin||event.source!==window.parent||event.data?.type!=='hl-practice-settings')return;
    if(['light','dark'].includes(event.data.theme))document.documentElement.dataset.theme=event.data.theme;
    if(LANGS.includes(event.data.lang)&&event.data.lang!==state.lang){state.lang=event.data.lang;translate();paintStats();paintTabs();if(!state.session)(MODES[state.mode]||todayHome)();}
  });
  addEventListener('keydown',e=>{
    const s=state.session;if(!s||s.mode==='bank'||/^(INPUT|TEXTAREA)$/.test(document.activeElement?.tagName||''))return;
    if(document.activeElement?.id==='ans')return;
    if(s.current?.kind==='contest')return;
    if(s.current?.kind==='track'){if(!s.answered&&!s.free&&s.current.type==='mc'&&/^[1-5a-eA-E]$/.test(e.key)){const i='abcde'.indexOf(e.key.toLowerCase());const n=i>=0?i:Number(e.key)-1;if(n<s.current.choices.length)trackAnswer(n);}else if(s.answered&&e.key==='Enter'&&document.activeElement?.id!=='next'){e.preventDefault();$('next')?.click();}return;}
    if(!s.answered&&!$('ansbox')&&/^[1-5]$/.test(e.key))answer(Number(e.key));
    else if(s.answered&&e.key==='Enter'&&document.activeElement?.id!=='next'){e.preventDefault();$('next')?.click();}
  });
  if(typeof ResizeObserver==='function')new ResizeObserver(reportHeight).observe(document.body);
  document.documentElement.classList.toggle('embedded',embedded);
  applyTheme();translate();
  addEventListener('online',()=>flushReports().catch(()=>{}));
  /* a course's unit link (#/learn/courses): the set builder opens on that level's problems in that unit */
  function presetCustom(level,unit){
    if(!H.STUDY_LEVELS.some(L=>L.key===level))return;
    saved.customOpts={...(saved.customOpts||{}),source:'level:'+level,units:unit&&P.SUBTOPICS.has(unit)?[unit]:[],min:1,max:10,contest:'',yearMin:0,yearMax:0};
  }
  const boot=()=>{paintStats();pull();loadPlan();(state.learnerP=loadLearner()).then(()=>{paintStats();learnerPrompt();loadToday();});setTimeout(()=>flushReports().catch(()=>{}),4000);const unit=params.get('unit'),mode=params.get('mode'),item=params.get('item'),track=params.get('track');state.mode='exam';paintTabs();
    if(item&&/^[a-z0-9]+-[A-Za-z0-9~._-]{1,60}$/.test(item))openItem(item);
    else if(mode==='bank')bankHome();else if(mode==='contest')contestHome();else if(mode==='tracks'||track)track&&/^[a-z0-9]{2,8}$/.test(track)?trackStart(track,params.get('syl')||''):tracksHome();
    else if(mode==='play'){document.documentElement.classList.add('play');playHome();}
    else if(mode==='diag')diagStart();else if(mode==='start')startHome(!!saved.profile);else if(mode==='class')classHome();else if(mode==='league')leagueHome();else if(mode==='review')reviewHome();else if(mode==='custom'){presetCustom(params.get('level'),unit);customHome();}else if(unit&&P.SUBTOPICS.has(unit))start(unit);else if(mode==='exam')home();else todayHome();};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();
