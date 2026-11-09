/* HPhO page (#/hpho): what the contest is, the next round in the visitor's own time zone, and registration.
   The server (community/src/hpho.js) holds rounds and entries; index.html's render() calls HL_HPHO.view() and, once the
   page is in the document, HL_HPHO.mount(). */
(() => {
  const L = () => (typeof lang === "string" && lang === "en") ? "en" : "ko";
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const COUNTRIES = "AD AE AF AG AI AL AM AO AR AS AT AU AW AZ BA BB BD BE BF BG BH BI BJ BM BN BO BR BS BT BW BY BZ CA CD CF CG CH CI CK CL CM CN CO CR CU CV CW CY CZ DE DJ DK DM DO DZ EC EE EG ER ES ET FI FJ FM FO FR GA GB GD GE GH GI GL GM GN GQ GR GT GU GW GY HK HN HR HT HU ID IE IL IN IQ IR IS IT JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MG MH MK ML MM MN MO MR MT MU MV MW MX MY MZ NA NC NE NG NI NL NO NP NR NZ OM PA PE PF PG PH PK PL PR PS PT PW PY QA RO RS RU RW SA SB SC SD SE SG SI SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TG TH TJ TL TM TN TO TR TT TV TW TZ UA UG US UY UZ VA VC VE VG VI VN VU WS XK YE ZA ZM ZW".split(" ");
  /* the server's AID_AUTO_COUNTRIES (community/src/hpho.js): the fee is waived there without asking */
  /* fee assistance is on hold (community/src/hpho.js AID_ENABLED): its section and form fields are not shown */
  const AID_ON = false;
  const AID_AUTO = new Set("AF BF BI CF TD CD ER ET GM GW KP LR MG MW ML MZ NE RW SL SO SS SD SY TG UG YE AO BD BJ BT BO KH CM CV KM CG CI DJ EG SZ GH GN HT HN IN KE KI KG LA LB LS MR FM MA MM NP NI NG PK PG PH WS ST SN SB LK TJ TZ TL TN UZ VU VN PS ZM ZW".split(" "));
  const T = {
    ko: {
      tabMonthly: "월별문제", tabHpho: "HPhO", eyebrow: "HaslaLab Physics Olympiad",
      title: "HPhO", lead: "올림피아드를 실제로 겪어보는 연습 대회입니다.",
      note: "HPhO는 입시나 수상 실적을 위한 공인 대회가 아닙니다. 새로운 주제의 문제를 실전처럼 풀어보는 경험을 위해 HaslaEdu가 직접 출제합니다.",
      facts: [["개인전", "혼자 응시합니다"], ["반기 1회", "1년에 두 번 열립니다"], ["이론 + 실험", "실험은 하슬라랩 가상 실험대에서"], ["전 세계 동시", "모든 참가자가 같은 시각에 시작합니다"], ["AI 채점", "채점 후 이의신청 기간이 있습니다"]],
      tracks: { theory: "이론 시험", experiment: "실험 시험" }, hours: "5시간", entryNote: "각 시험은 시작 1시간 전부터 입장할 수 있고, 시작 20분 전까지 대기실에 착석해야 합니다.",
      admin: { title: "관리자", upload: "시험 자료 올리기", track: "시험", kind: "자료", lang: "언어", file: "PDF 파일", send: "올리기", sent: "올렸습니다.", kinds: { guide: "General Guide", writing: "답안지", answer: "Answer Sheet", paper: "문제지" },
        seats: "응시 기록 검토", load: "불러오기", cols: ["수험번호", "착석", "시작", "재접속", "끊김", "답안 쪽", "제출", "판정"], review: "검토 필요", none: "아직 착석한 응시자가 없습니다.", log: "기록 보기", save: "판정 저장", verdicts: { "": "—", clear: "이상 없음", review: "검토 중", cheating: "부정행위" }, note: "메모", events: "이벤트", snaps: "감독 사진", answers: "답안 사진", clips: "녹화 (5분 단위)", purge: "검토 완료 · 기록 삭제", purgeAsk: n => `${n}의 감독 녹화와 사진을 모두 삭제합니다. 판정과 이벤트 기록은 남습니다. 되돌릴 수 없습니다. 삭제할까요?`, purged: n => `삭제됨 (${n}개)`, checkNote: "점검 미확인",
        live: "실시간 감독", liveStart: "감독 시작", liveStop: "멈춤", liveNote: "20초마다 최신 웹캠·화면 사진과 최근 15분 경고를 다시 불러옵니다.", online: "접속 중", offline: "끊김", noPhoto: "사진 없음",
        alerts: { focus_lost: "창 이탈", display_change: "모니터 변경", screen_locked: "화면 잠금", suspend: "절전", shortcut_blocked: "단축키", window_close_attempt: "창 닫기 시도", network_lost: "네트워크 끊김", page_hidden: "화면 숨김", camera_stopped: "카메라 꺼짐", face_missing: "얼굴 없음", faces_multiple: "여러 명", phone_seen: "휴대폰", voice: "말소리", system_sound: "컴퓨터 소리", reconnect: "재접속", recording_failed: "녹화 실패", after_time: "종료 후" } },
      next: "다음 대회", none: "첫 대회 일정은 곧 공개됩니다.", regOpen: "접수", regClose: "접수 마감", start: "시험 시작", length: "시험 시간", min: "분", fee: "참가비", free: "무료",
      localTz: z => `내 시간대(${z}) 기준`, until: "남음", d: "일", h: "시간", m: "분",
      status: { open: "접수 중", closed: "접수 마감", finished: "종료", soon: "접수 예정", rehearsal: "관리자 전용" },
      signIn: "접수하려면 로그인하세요.", login: "로그인",
      email: "연락 이메일", emailNote: "시험 전날 시험 시각과 환경 테스트 안내를 이 주소로 보냅니다. 계정 이메일과 달라도 됩니다.", formTitle: "참가 접수", country: "국가", level: "과정", levels: { middle: "중학생", high: "고등학생", university: "대학생", other: "기타" }, birth: "출생 연도",
      pledge: "대회 규정을 읽었고, 시험 중 다른 사람·AI·인터넷·교재의 도움을 받지 않겠습니다.",
      proctor: "시험은 하슬라에듀 데스크톱 앱으로 응시하며, 감독을 위해 웹캠·마이크·화면이 기록되는 데 동의합니다. 시험 중 찍힌 얼굴·화면 사진은 하슬라 서버에 저장되고, 부정행위 검토를 위해 외부 AI 서비스(Google Gemini)로 전송되어 분석될 수 있습니다(AI 감독관). 감독 기록은 결과 확정 후 정해진 기간이 지나면 삭제됩니다.",
      age14: "만 14세 이상입니다. (HPhO는 만 14세 이상만 응시할 수 있습니다.)",
      identity: "답안지에는 수험번호만 적습니다. 이름·학교 등 신원 정보를 적어 생기는 일은 제 책임입니다.",
      guardian: "만 19세 미만이며, 보호자가 참가와 감독 기록에 동의했습니다.",
      trainGuardian: "만 19세 미만이며, 보호자가 감독 기록을 감독관 AI 학습에 사용하는 것에도 동의했습니다.",
      train: "(선택) 내 감독 기록(얼굴·화면 사진과 감독 이벤트)을 HaslaEdu 감독관 AI의 학습 자료로 사용하는 데 동의합니다. 동의하지 않아도 응시에 아무 영향이 없고, 대회 전까지 접수 수정에서 언제든 철회할 수 있습니다.",
      submit: "접수하기", update: "접수 내용 수정", withdraw: "접수 취소", withdrawAsk: "접수를 취소할까요?",
      mine: "접수 완료", candidate: "수험번호", candidateNote: "답안지에는 이 수험번호만 적으세요.",
      rulesTitle: "규정 요약", examRulesTitle: "온라인 응시 규정 (전체)", examRules: [["응시 장소", ["혼자 있는 방(1인 1실)에서 응시합니다. 카페·도서관·독서실 등 여러 사람이 쓰는 곳이나 이동 중에는 응시할 수 없습니다.", "밝고 조용하며 전원과 인터넷이 끊기지 않는 곳이어야 합니다. 응시용 PC와 감독용 휴대폰은 충전기에 연결해 둡니다.", "시험 중 다른 사람(보호자 포함)은 방에 들어올 수 없습니다."]], ["기기", ["응시용 PC: 하슬라에듀 데스크톱 앱을 설치한 Windows 노트북 또는 데스크톱 1대. 태블릿·스마트폰·터치스크린 입력은 사용할 수 없습니다.", "모니터는 1대만 사용합니다. 노트북에 외부 모니터를 연결했다면 노트북 화면은 닫습니다.", "키보드·마우스·웹캠·마이크는 각 1개만 사용하며, 웹캠과 마이크는 시험 내내 켜 둡니다.", "감독용 휴대폰은 QR로 연결하고 방해 금지 모드를 켭니다. 알림·알람·재난문자·자동 잠금은 끕니다."]], ["책상 위에 둘 수 있는 것 (이 외에는 모두 치웁니다)", ["응시용 PC와 키보드·마우스·웹캠", "필기구: 연필·볼펜·지우개·자 (필통은 책상 아래에 둡니다)", "대회가 배포한 답안지(Writing Sheet)·Answer Sheet 인쇄본, 앞뒤가 백지인 A4 연습지 (그 밖의 종이와 수험표 인쇄본은 안 됩니다)", "공학용 계산기 1개 (그래프 계산기, 프로그램·메모를 저장하거나 통신할 수 있는 계산기, 휴대폰·PC 계산기 앱은 안 됩니다)", "라벨을 뗀 투명한 물병 1개 (그 밖의 음식물은 안 됩니다)"]], ["금지 물품 (몸에 지니거나 손이 닿는 곳에 둘 수 없음)", ["시계·스마트워치 (종류 무관, 남은 시간은 시험 화면에 표시됩니다)", "감독용이 아닌 휴대폰, 태블릿, 이북리더, 다른 노트북", "이어폰·헤드셋(한쪽만 껴도 안 됨), 보청기류 기기, 스마트 안경 (일반 안경은 됩니다)", "챙 있는 모자 (비니 등 챙 없는 모자는 귀가 다 보이면 됩니다)", "교재·책·메모·포스트잇, 벽이나 책상의 글씨 (책장에 꽂힌 책은 시험 중 꺼내지 않으면 됩니다)"]], ["카메라 배치", ["웹캠(정면): 마스크를 쓰지 않은 얼굴 전체가 보여야 합니다.", "감독용 휴대폰(옆이나 뒤 1~1.5 m): 응시자의 옆모습·두 손·책상 위 전체·모니터 화면이 한 화면에 모두 보여야 합니다. 거치대 사용을 권장합니다.", "카메라 배치 때문에 부정행위 여부를 판단할 수 없으면(책상 위가 안 보임, 손이 화면 밖으로 나감 등) 부정행위로 처리할 수 있습니다."]], ["입실과 점검", ["시작 1시간 전부터 입실할 수 있고, 시작 20분 전까지 점검을 마치고 착석해야 합니다. 그 뒤에는 새로 입실할 수 없습니다.", "점검: 서버 연결 → 화면 기록 → 웹캠(얼굴) → 마이크(문장 읽기) → 컴퓨터 소리 → 귀·머리·손목 → 휴대폰 연결 → 주변 인식.", "착석 후에는 대기실에서도 감독과 녹화가 진행되며 나갈 수 없습니다."]], ["화장실과 자리 이탈", ["시험 중에는 화장실을 포함해 어떤 이유로도 자리를 비울 수 없습니다. 입실 전에 미리 다녀오세요.", "대기실에서 자리를 비우면(‘자리 비우기’ 버튼, 또는 얼굴이 20초 이상 보이지 않으면) 돌아와서 모든 점검(얼굴·마이크·귀·휴대폰·주변 인식)을 처음부터 다시 해야 합니다. 그 사이 시험이 시작되어도 시간은 늘어나지 않습니다."]], ["시험 중", ["시험 창 밖으로 나가거나 다른 프로그램(메신저·브라우저·원격 제어 등)을 실행하지 않습니다.", "다른 사람과 소통하지 않습니다. 소리 내어 읽기·통화·말하기도 안 됩니다.", "얼굴과 두 손이 카메라 밖으로 나가지 않게 합니다.", "문제 내용에 대한 질문은 받지 않습니다."]], ["연결이 끊겼을 때", ["앱을 다시 열면 이어서 볼 수 있으며, 다시 들어올 때 주변 인식을 다시 합니다.", "끊긴 시간만큼 시간을 연장하지 않습니다. 끊긴 횟수와 시간은 모두 기록되며, 3회 이상이면 녹화를 검토합니다."]], ["종료와 제출", ["종료 시각이 되면 즉시 펜을 내려놓습니다. 그 뒤의 필기는 부정행위입니다(종료 후에도 감독은 계속됩니다).", "답안지를 한 장씩 촬영해 제출 시간 안에 올립니다."]], ["부정행위 처리", ["녹화와 기록을 사람이 검토해 판정합니다. AI 경고만으로 판정하지 않습니다.", "예: 허용되지 않은 물품, 다른 사람 등장, 자리 이탈, 얼굴·손이 사라짐, 다른 프로그램 사용, 종료 후 필기, 카메라 배치로 판단 불가.", "처분: 해당 시험 0점 또는 실격, 이후 대회 응시 제한."]]],
      rules: [
        "답안지에는 수험번호만 적습니다. 이름·학교 등 신원을 알 수 있는 정보는 적지 마세요. 적어서 생기는 불이익은 본인 책임입니다.",
        "시험 중에는 다른 사람, AI, 인터넷 검색, 교재의 도움을 받을 수 없습니다.",
        "시계·스마트워치(종류 무관), 이어폰·헤드셋, 스마트 안경, 챙 있는 모자는 착용할 수 없습니다. 남은 시간은 시험 화면에 표시됩니다.",
        "책상 위에는 필기구, 배포된 답안지, 백지 A4, 공학용 계산기, 투명 물병만 둘 수 있습니다. 시험 중에는 화장실도 갈 수 없으니 미리 다녀오세요.",
        "시험은 하슬라에듀 Windows 데스크톱 앱의 감독 모드로 응시합니다. 웹캠·마이크·화면과 창 전환이 기록되며, 얼굴·화면 사진은 부정행위 검토를 위해 외부 AI 서비스(Google Gemini)로 분석될 수 있습니다.",
        "AI는 의심 장면을 표시만 하며, 실격 여부는 사람이 검토해 결정합니다. 감독 기록은 결과 확정 후 정해진 기간이 지나면 삭제됩니다.",
        "답안은 AI가 채점하고, 결과 공개 후 이의신청 기간이 있습니다. 입상 후보에게는 짧은 화상 확인을 요청할 수 있습니다.",
      ],
      aidTitle: "참가비 지원",
      aidIntro: "비용 때문에 HPhO를 포기하는 학생이 없도록 참가비를 지원합니다.",
      aidRules: ["세계은행 기준 저소득·중저소득 국가에서 응시하면 신청 없이 참가비가 면제됩니다.", "그 밖의 학생은 접수할 때 ‘참가비 지원 신청’을 고르고 사유를 적어 주세요. 증빙 서류는 받지 않습니다.", "HaslaEdu가 접수 마감 전까지 검토해 결과를 이 페이지에 알려드립니다. 지원 여부는 채점이나 결과에 전혀 영향을 주지 않습니다.", "적어 주신 사유는 심사에만 쓰고, 대회가 끝나면 삭제합니다."],
      aidAuto: "이 국가에서는 참가비가 자동으로 면제됩니다.", aidAsk: "참가비 지원을 신청합니다.", aidReason: "사유", aidNote: "간단한 설명 (10~300자)",
      aidReasons: { family_income: "가계 형편이 어려움", public_assistance: "기초생활수급·차상위 등 공공 지원 대상", school_referral: "학교·기관의 추천", other: "기타" },
      feeLabel: "참가비", feeState: { auto: "면제 (자동)", pending: "지원 심사 중", approved: "면제 (지원 승인)", declined: "지원 미승인 · 납부 필요", none: "납부 필요" },
      saved: "접수되었습니다.", err: "처리하지 못했습니다: ",
      errors: { bad_aid_reason: "지원 사유를 고르세요.", aid_note_required: "지원 사유를 10자 이상 적어 주세요.", bad_email: "연락 이메일을 확인하세요.", bad_country: "국가를 고르세요.", bad_level: "과정을 고르세요.", bad_birth_year: "출생 연도를 확인하세요.", pledge_required: "규정 서약에 동의해야 합니다.", proctoring_consent_required: "감독 기록에 동의해야 합니다.", identity_notice_required: "답안지 안내를 확인해야 합니다.", guardian_consent_required: "만 19세 미만은 보호자 동의가 필요합니다.", too_young: "HPhO는 만 14세 이상만 응시할 수 있습니다.", age14_required: "만 14세 이상인지 확인해 주세요.", train_guardian_consent_required: "만 19세 미만이 감독관 AI 학습에 동의하려면 보호자 동의도 필요합니다.", registration_closed: "접수 기간이 아닙니다.", login_required: "로그인이 필요합니다." },
    },
    en: {
      tabMonthly: "Monthly", tabHpho: "HPhO", eyebrow: "HaslaLab Physics Olympiad",
      title: "HPhO", lead: "A practice olympiad that feels like the real thing.",
      note: "HPhO is not an accredited contest and is not meant for admissions or award records. HaslaEdu writes it so you can meet new topics and sit a paper under real conditions.",
      facts: [["Individual", "You sit it on your own"], ["Twice a year", "One round each half-year"], ["Theory + experiment", "Experiments on the HaslaLab virtual bench"], ["Same time worldwide", "Everyone starts at the same moment"], ["AI-marked", "With a window for appeals"]],
      tracks: { theory: "Theory exam", experiment: "Experimental exam" }, hours: "5 hours", entryNote: "Each exam room opens an hour before the start; be seated in the waiting room 20 minutes before it.",
      admin: { title: "Organisers", upload: "Upload exam documents", track: "Exam", kind: "Document", lang: "Language", file: "PDF file", send: "Upload", sent: "Uploaded.", kinds: { guide: "General Guide", writing: "Writing sheet", answer: "Answer Sheet", paper: "Paper" },
        seats: "Review the exam records", load: "Load", cols: ["Candidate", "Seated", "Started", "Reconnects", "Gaps", "Pages", "Submitted", "Verdict"], review: "Needs review", none: "No candidate has been seated yet.", log: "Open record", save: "Save verdict", verdicts: { "": "—", clear: "Clear", review: "Under review", cheating: "Cheating" }, note: "Note", events: "Events", snaps: "Proctoring photos", answers: "Answer photos", clips: "Recordings (5-minute parts)", purge: "Reviewed · delete records", purgeAsk: n => `Delete every proctoring recording and photo of ${n}? The verdict and the events stay. This cannot be undone.`, purged: n => `Deleted (${n})`, checkNote: "Unverified checks",
        live: "Live proctoring", liveStart: "Start watching", liveStop: "Stop", liveNote: "Every 20 s: the latest webcam and screen photo and the alerts of the last 15 minutes.", online: "Online", offline: "Disconnected", noPhoto: "No photo",
        alerts: { focus_lost: "Left window", display_change: "Display change", screen_locked: "Screen locked", suspend: "Sleep", shortcut_blocked: "Shortcut", window_close_attempt: "Tried to close", network_lost: "Network lost", page_hidden: "Hidden", camera_stopped: "Camera off", face_missing: "No face", faces_multiple: "Several people", phone_seen: "Phone", voice: "Speech", system_sound: "Computer sound", reconnect: "Reconnect", recording_failed: "Recording failed", after_time: "After time" } },
      next: "Next round", none: "The first round's dates will be announced soon.", regOpen: "Registration opens", regClose: "Registration closes", start: "Exam starts", length: "Duration", min: "min", fee: "Fee", free: "Free",
      localTz: z => `in your time zone (${z})`, until: "left", d: "d", h: "h", m: "m",
      status: { open: "Registration open", closed: "Registration closed", finished: "Finished", soon: "Opens soon", rehearsal: "Admins only" },
      signIn: "Sign in to register.", login: "Sign in",
      email: "Contact email", emailNote: "The day before each exam we send the times and the environment test link here. It need not be your account's email.", formTitle: "Register", country: "Country", level: "Level", levels: { middle: "Middle school", high: "High school", university: "University", other: "Other" }, birth: "Year of birth",
      pledge: "I have read the rules and will take no help from people, AI, the internet or books during the exam.",
      proctor: "I will sit the exam in the HaslaEdu desktop app and agree that my webcam, microphone and screen are recorded for proctoring. Photos of my face and screen taken during the exam are stored on HaslaLab's server and may be sent to an external AI service (Google Gemini) for review (the AI proctor). Proctoring records are deleted a set time after results are final.",
      age14: "I am 14 or older. (HPhO is open to candidates aged 14 and over.)",
      identity: "I will write only my candidate number on the answer sheets. Anything identifying I write is my own responsibility.",
      guardian: "I am under 19 and a parent or guardian has agreed to my taking part and to the proctoring records.",
      trainGuardian: "I am under 19 and a parent or guardian has also agreed that my proctoring records may be used to train the AI proctor.",
      train: "(Optional) I agree that my proctoring records (photos of my face and screen, and proctoring events) may be used to train HaslaEdu's AI proctor. Not agreeing has no effect on taking part, and I can withdraw this before the round by editing my registration.",
      submit: "Register", update: "Update registration", withdraw: "Withdraw", withdrawAsk: "Withdraw your registration?",
      mine: "Registered", candidate: "Candidate number", candidateNote: "Write only this number on your answer sheets.",
      rulesTitle: "Rules in brief", examRulesTitle: "Online exam rules (in full)", examRules: [["Where", ["Sit the exam alone in a room. Not in a café, library, study room or on the move.", "Bright, quiet, with power and internet that will not drop. Keep the computer and the proctoring phone on chargers.", "No one else (a parent included) may enter the room during the exam."]], ["Devices", ["One Windows laptop or desktop with the HaslaEdu desktop app. No tablet, phone or touchscreen input.", "One monitor only: close the laptop's screen if an external monitor is connected.", "One keyboard, mouse, webcam and microphone; the webcam and microphone stay on throughout.", "The proctoring phone connects by QR, in do-not-disturb mode with notifications, alarms and auto-lock off."]], ["Allowed on the desk (nothing else)", ["The computer, keyboard, mouse and webcam", "Pencils, pens, an eraser and a ruler (the pencil case under the desk)", "The printed writing sheets and answer sheets from the organisers and blank A4 scratch paper (no other paper, no printed admission ticket)", "One scientific calculator (no graphing, programmable or communicating calculators, no calculator apps)", "One clear water bottle without its label (no other food or drink)"]], ["Not allowed (worn or within reach)", ["Any watch or smartwatch (the time left is on the exam screen)", "Any phone other than the proctoring phone, tablets, e-readers, other laptops", "Earphones or a headset (even in one ear), hearing devices, smart glasses (ordinary glasses are fine)", "A cap or hat with a brim (a beanie is fine if both ears show)", "Books, notes, sticky notes, writing on walls or the desk (books on a shelf may stay if not taken out)"]], ["Cameras", ["Webcam (front): your whole face, without a mask.", "Proctoring phone (side or behind, 1–1.5 m): your side, both hands, the whole desk and the monitor in one picture. A stand is recommended.", "A camera set-up that makes it impossible to judge (the desk not seen, hands out of the picture) can be treated as cheating."]], ["Entry and checks", ["The room opens an hour before the start; finish the checks and be seated 20 minutes before the start. After that no one can enter.", "Checks: server, screen recording, webcam (face), microphone (reading aloud), computer sound, ears/head/wrists, phone, room.", "Once seated, the waiting room is proctored and recorded and cannot be left."]], ["Toilet and leaving the seat", ["You cannot leave your seat for any reason during the exam, the toilet included: go before you enter.", "If you leave in the waiting room (the ‘Step away’ button, or your face not seen for 20 seconds), every check (face, microphone, ears, phone, room) must be done again when you return. The exam does not wait."]], ["During the exam", ["Do not leave the exam window or run other programs (messengers, browsers, remote control).", "No contact with anyone; no reading aloud, calls or talking.", "Keep your face and both hands in view.", "No questions about the problems are answered."]], ["If the connection drops", ["Open the app again to continue; the room check is repeated.", "No time is added. Every drop is recorded; three or more lead to a review of the recording."]], ["End and submission", ["At the end time put your pen down at once; writing after it is cheating (proctoring continues).", "Photograph your answer sheets one by one and upload them before the upload closes."]], ["Cheating", ["A person decides from the recordings and records; an AI flag alone decides nothing.", "Examples: items not allowed, another person, leaving the seat, face or hands out of view, other programs, writing after the end, a camera set-up that makes it impossible to judge.", "Outcome: zero for that exam or disqualification, and a ban from later rounds."]]],
      rules: [
        "Write only your candidate number on the answer sheets. Do not write your name, school or anything that identifies you; anything you write is your own responsibility.",
        "No help from other people, AI, internet search or books during the exam.",
        "No watch or smartwatch of any kind, earphones or headset, smart glasses, or brimmed cap. The time left is shown on the exam screen.",
        "Only writing tools, the answer sheets, blank A4, a scientific calculator and a clear water bottle on the desk. No toilet breaks during the exam: go before.",
        "The exam is sat in the proctoring mode of the HaslaEdu Windows desktop app. Your webcam, microphone, screen and window switches are recorded, and photos of your face and screen may be analysed by an external AI service (Google Gemini) for review.",
        "AI only flags moments; a person reviews every flag before any disqualification. Proctoring records are deleted a set time after results are final.",
        "Answers are marked by AI, with an appeal window after results. Prize candidates may be asked for a short video check.",
      ],
      aidTitle: "Fee assistance",
      aidIntro: "No student should miss HPhO because of the fee.",
      aidRules: ["Candidates in a low- or lower-middle-income economy (World Bank classification) pay nothing, without asking.", "Anyone else can tick ‘Request fee assistance’ when registering and give a reason. No documents are needed.", "HaslaEdu reviews requests before registration closes and shows the decision on this page. Assistance never affects marking or results.", "Your reason is used only for the review and is deleted after the round."],
      aidAuto: "The fee is waived automatically for this country.", aidAsk: "I request fee assistance.", aidReason: "Reason", aidNote: "A short explanation (10–300 characters)",
      aidReasons: { family_income: "My family cannot easily afford it", public_assistance: "I receive public financial assistance", school_referral: "Referred by my school or an organisation", other: "Other" },
      feeLabel: "Fee", feeState: { auto: "Waived (automatic)", pending: "Assistance under review", approved: "Waived (assistance approved)", declined: "Assistance declined · fee due", none: "Fee due" },
      saved: "You are registered.", err: "Could not complete: ",
      errors: { bad_aid_reason: "Choose a reason for assistance.", aid_note_required: "Please explain in at least 10 characters.", bad_email: "Check the contact email.", bad_country: "Choose your country.", bad_level: "Choose your level.", bad_birth_year: "Check your year of birth.", pledge_required: "You must accept the pledge.", proctoring_consent_required: "You must agree to proctoring.", identity_notice_required: "Please confirm the answer-sheet notice.", guardian_consent_required: "Under 19: a guardian's consent is required.", too_young: "HPhO is open to candidates aged 14 and over.", age14_required: "Please confirm that you are 14 or older.", train_guardian_consent_required: "Under 19: training the AI proctor also needs a guardian's consent.", registration_closed: "Registration is not open.", login_required: "Please sign in." },
    },
  };
  let state = { data: null, error: null, busy: false };

  const tz = () => { try { return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"; } catch (e) { return "UTC"; } };
  const when = s => new Date(s * 1000).toLocaleString(L() === "en" ? "en-GB" : "ko-KR", { dateStyle: "medium", timeStyle: "short" });
  const countryName = (() => { let dn = null; return c => { try { dn = dn && dn.lang === L() ? dn : Object.assign(new Intl.DisplayNames([L()], { type: "region" }), { lang: L() }); return dn.of(c); } catch (e) { return c; } }; })();
  function left(s, t) {
    const x = T[L()], sec = Math.max(0, s - Math.floor(Date.now() / 1000)), d = Math.floor(sec / 86400), h = Math.floor(sec % 86400 / 3600), m = Math.floor(sec % 3600 / 60);
    return (d ? d + x.d + " " : "") + h + x.h + " " + m + x.m + " " + x.until;
  }
  function roundStatus(r) {
    const t = Math.floor(Date.now() / 1000);
    const end = Math.max(r.start_at + r.duration_min * 60, ...(r.tracks || []).map(k => k.start_at + k.duration_min * 60));
    if (r.status === "finished" || t >= end) return "finished";
    if (r.status === "draft") return "rehearsal";   /* only admins are sent drafts: a test round open until it ends */
    if (r.status === "open" && t < r.reg_open) return "soon";
    if (r.status === "open" && t < r.reg_close) return "open";
    return "closed";
  }

  function view() {
    const x = T[L()];
    return `<div class="shell hpho">
      <nav class="hpho-tabs" aria-label="${x.tabHpho}"><a href="#/monthly">${x.tabMonthly}</a><a href="#/hpho" aria-current="page">${x.tabHpho}</a></nav>
      <div class="phead"><p class="eyebrow">${x.eyebrow}</p><h1 class="hpho-logo"><img class="hpho-wordmark hpho-logo-light" src="logo/brand/hpho-wordmark-light.svg?v=20261109-hpho" alt="HPhO"><img class="hpho-wordmark hpho-logo-dark" src="logo/brand/hpho-wordmark-dark.svg?v=20261109-hpho" alt="" aria-hidden="true"></h1><div class="sub">${x.lead}</div></div>
      <p class="hpho-note">${x.note}</p>
      <ul class="hpho-facts">${x.facts.map(([a, b]) => `<li><b>${a}</b><span>${b}</span></li>`).join("")}</ul>
      <section class="hpho-round" id="hphoRound" aria-live="polite"><p class="hpho-muted">…</p></section>
      ${AID_ON ? `<section class="hpho-rules"><h2>${x.aidTitle}</h2><p>${x.aidIntro}</p><ul>${x.aidRules.map(r => `<li>${r}</li>`).join("")}</ul></section>` : ""}
      <section class="hpho-rules"><h2>${x.rulesTitle}</h2><ol>${x.rules.map(r => `<li>${r}</li>`).join("")}</ol>
        <details class="hpho-exam-rulebook"><summary>${x.examRulesTitle}</summary>${x.examRules.map(([h, items], i) => `<h3>${i + 1}. ${h}</h3><ul>${items.map(t => `<li>${t}</li>`).join("")}</ul>`).join("")}</details></section>
    </div>`;
  }

  function roundHtml() {
    const x = T[L()], d = state.data;
    if (state.error) return `<p class="hpho-muted">${esc(x.err + state.error)}</p>`;
    if (!d) return `<p class="hpho-muted">…</p>`;
    const r = d.rounds.find(r => roundStatus(r) !== "finished") || null;
    if (!r) return `<h2>${x.next}</h2><p class="hpho-muted">${x.none}</p>`;
    const st = roundStatus(r), mine = d.entries?.[r.id], me = typeof cm === "object" && cm ? cm.me : null;
    /* IsPhO-style: the theory and the experiment exam, each with its own date and time */
    const tracks = r.tracks?.length ? r.tracks : [{ track: "theory", start_at: r.start_at, duration_min: r.duration_min }];
    const rows = [[x.regOpen, when(r.reg_open)], [x.regClose, when(r.reg_close)],
      ...tracks.map(k => [x.tracks[k.track], `${when(k.start_at)} <small>(${k.duration_min === 300 ? x.hours : k.duration_min + x.min}${k.start_at > Date.now() / 1000 ? " · " + left(k.start_at) : ""})</small>`]),
      [x.fee, r.fee_usd ? "$" + r.fee_usd.toFixed(2) : x.free]];
    let action;
    if (mine) action = `<div class="hpho-mine"><p class="hpho-badge">${x.mine}</p><p>${x.candidate}: <b class="hpho-no">${esc(mine.candidate_no)}</b></p><p class="hpho-muted">${x.candidateNote}</p>
      <p><a class="hpho-btn" href="#/hpho/exam">${L() === "en" ? "Technical check · exam room" : "기술 점검 · 시험장 입장"}</a></p>
      ${r.fee_usd ? `<p>${x.feeLabel}: <b>${x.feeState[mine.aid] || x.feeState.none}</b>${mine.fee_due ? ` · $${Number(mine.fee_due).toFixed(2)}` : ""}</p>` : ""}
      ${st === "open" || st === "rehearsal" ? `<details><summary>${x.update}</summary>${formHtml(r, mine)}</details><button type="button" class="hpho-link" data-hpho-withdraw="${esc(r.id)}">${x.withdraw}</button>` : ""}</div>`;
    else if (st !== "open" && st !== "rehearsal") action = "";
    else if (!me) action = `<p>${x.signIn} <a class="hpho-btn" href="#/login">${x.login}</a></p>`;
    else action = formHtml(r, null);
    /* a draft is the admins' practice round: named as such, whatever title it was given */
    const heading = st === "rehearsal" ? (L() === "en" ? "Practice exam" : "모의 시험") : `${x.next} · ${esc(r.title[L()])}`;
    return `<div class="hpho-round-head"><h2>${heading}</h2><span class="hpho-status is-${st}">${x.status[st]}</span></div>
      <p class="hpho-muted">${x.localTz(esc(tz()))}</p>
      <dl class="hpho-times">${rows.map(([a, b]) => `<div><dt>${a}</dt><dd>${b}</dd></div>`).join("")}</dl><p class="hpho-muted">${x.entryNote}</p>${action}
      ${me?.role === "admin" ? adminHtml(r, tracks) : ""}`;
  }

  /* the organisers' tools: upload the guide, the sheets and the paper (per exam and language), and review the seats */
  function adminHtml(r, tracks) {
    const a = T[L()].admin, opt = (o, f = v => v) => o.map(v => `<option value="${v}">${esc(f(v))}</option>`).join("");
    const trackOpt = opt(tracks.map(k => k.track), v => T[L()].tracks[v]);
    return `<details class="hpho-admin" data-hpho-admin="${esc(r.id)}"><summary>${a.title}</summary>
      <form class="hpho-form" data-hpho-upload><h3>${a.upload}</h3>
        <label>${a.track}<select name="track">${trackOpt}</select></label>
        <label>${a.kind}<select name="kind">${opt(["guide", "writing", "answer", "paper"], v => a.kinds[v])}</select></label>
        <label>${a.lang}<select name="lang">${opt(["ko", "en"])}</select></label>
        <label>${a.file}<input type="file" name="file" accept="application/pdf" required></label>
        <p class="hpho-form-msg" role="status"></p><button type="submit" class="hpho-btn">${a.send}</button></form>
      <div class="hpho-form" data-hpho-seats><h3>${a.seats}</h3><label>${a.track}<select name="track">${trackOpt}</select></label>
        <p><button type="button" class="hpho-btn" data-hpho-load>${a.load}</button></p><div data-hpho-seat-list></div><div data-hpho-seat-log></div></div>
      <div class="hpho-form hpho-live-box" data-hpho-live><h3>${a.live}</h3><p class="hpho-muted">${a.liveNote}</p><label>${a.track}<select name="track">${trackOpt}</select></label>
        <p><button type="button" class="hpho-btn" data-hpho-live-go>${a.liveStart}</button></p><div class="hpho-live" data-hpho-live-grid></div></div></details>`;
  }
  const authFetch = (p, init = {}) => fetch(cmBase() + "/api" + p, { ...init, headers: { ...(init.headers || {}), Authorization: "Bearer " + cmTok() } });
  function bindAdmin(box) {
    const root = box.querySelector("[data-hpho-admin]"); if (!root) return;
    const a = T[L()].admin, id = encodeURIComponent(root.dataset.hphoAdmin), up = root.querySelector("[data-hpho-upload]");
    up.addEventListener("submit", async e => {
      e.preventDefault(); const msg = up.querySelector(".hpho-form-msg"); msg.textContent = "…";
      const fd = new FormData(); fd.set("kind", up.kind.value); fd.set("lang", up.lang.value); fd.set("file", up.file.files[0]);
      const res = await authFetch(`/hpho/rounds/${id}/exam/${up.track.value}/upload`, { method: "POST", body: fd }).catch(() => null);
      const j = res ? await res.json().catch(() => ({})) : {};
      msg.textContent = res?.ok ? `${a.sent} (${Math.round(j.size / 1024)} KB)` : T[L()].err + (j.error || "network");
    });
    const seats = root.querySelector("[data-hpho-seats]"), list = seats.querySelector("[data-hpho-seat-list]"), logBox = seats.querySelector("[data-hpho-seat-log]");
    const time = s => s ? new Date(s * 1000).toLocaleTimeString(L() === "en" ? "en-GB" : "ko-KR") : "—";
    async function load() {
      const track = seats.querySelector("[name=track]").value;
      try {
        const d = await cmApi("GET", `/hpho/rounds/${id}/exam/${track}/seats`);
        list.innerHTML = d.seats.length ? `<div class="hpho-table-wrap"><table class="hpho-table"><thead><tr>${a.cols.map(c => `<th>${c}</th>`).join("")}<th></th></tr></thead><tbody>${d.seats.map(s => `<tr class="${s.review ? "is-review" : ""}">
          <td><b class="hpho-no">${esc(s.candidate_no)}</b>${s.review ? ` <span class="hpho-status is-review">${a.review}</span>` : ""}${s.check_note ? `<br><small title="${esc(s.check_note)}">${a.checkNote}: ${esc(s.check_note)}</small>` : ""}</td><td>${time(s.checked_in_at)}</td><td>${time(s.started_at)}</td><td>${s.reconnects}</td><td>${s.gaps}</td><td>${s.pages}</td><td>${time(s.submitted_at)}</td>
          <td><select data-v="${esc(s.candidate_no)}">${Object.entries(a.verdicts).map(([k, v]) => `<option value="${k}"${(s.verdict || "") === k ? " selected" : ""}>${v}</option>`).join("")}</select> <input data-n="${esc(s.candidate_no)}" placeholder="${a.note}" value="${esc(s.verdict_note || "")}" maxlength="500"> <button type="button" class="hpho-link" data-save="${esc(s.candidate_no)}">${a.save}</button>${s.verdict && s.kept ? ` <button type="button" class="hpho-link" data-purge="${esc(s.candidate_no)}">${a.purge}</button>` : ""}</td>
          <td><button type="button" class="hpho-link" data-log="${esc(s.candidate_no)}">${a.log}</button></td></tr>`).join("")}</tbody></table></div>` : `<p class="hpho-muted">${a.none}</p>`;
        list.querySelectorAll("[data-save]").forEach(b => b.addEventListener("click", async () => {
          const no = b.dataset.save, v = list.querySelector(`[data-v="${CSS.escape(no)}"]`).value; if (!v) return;
          try { await cmApi("POST", `/hpho/rounds/${id}/exam/${track}/verdict`, { candidate: no, verdict: v, note: list.querySelector(`[data-n="${CSS.escape(no)}"]`).value }); b.textContent = "✓"; } catch (e) { alert(T[L()].err + (e?.code || "")); }
        }));
        list.querySelectorAll("[data-log]").forEach(b => b.addEventListener("click", () => openLog(track, b.dataset.log)));
        list.querySelectorAll("[data-purge]").forEach(b => b.addEventListener("click", async () => {
          if (!confirm(a.purgeAsk(b.dataset.purge))) return;
          try { const r = await cmApi("POST", `/hpho/rounds/${id}/exam/${track}/purge`, { candidate: b.dataset.purge }); b.textContent = a.purged(r.deleted); b.disabled = true; } catch (e) { alert(T[L()].err + (e?.code || "")); }
        }));
      } catch (e) { list.innerHTML = `<p class="hpho-muted">${esc(T[L()].err + (e?.code || "network"))}</p>`; }
    }
    /* one candidate: the events in order, and the proctoring and answer photos (fetched with the admin's sign-in) */
    async function openLog(track, no) {
      logBox.innerHTML = "<p class='hpho-muted'>…</p>";
      try {
        const d = await cmApi("GET", `/hpho/rounds/${id}/exam/${track}/log?candidate=${encodeURIComponent(no)}`);
        logBox.innerHTML = `<h3>${esc(no)}</h3><details open><summary>${a.events} (${d.events.length})</summary><ol class="hpho-events">${d.events.map(e => `<li><time>${time(e.at)}</time> <b>${esc(e.kind)}</b> ${esc(e.detail || "")}</li>`).join("")}</ol></details>
          <details><summary>${a.snaps} (${d.snaps.length})</summary><div class="hpho-thumbs" data-keys="snaps"></div></details>
          <details><summary>${a.answers} (${d.answers.length})</summary><div class="hpho-thumbs" data-keys="answers"></div></details>
          <details><summary>${a.clips} (${d.clips.length})</summary><ol class="hpho-clips">${d.clips.map(k => `<li><button type="button" class="hpho-link" data-clip="${esc(k)}">${esc(k.split("/").pop())}</button></li>`).join("")}</ol><video class="hpho-clip-video" controls hidden></video></details>`;
        const player = logBox.querySelector(".hpho-clip-video");
        logBox.querySelectorAll("[data-clip]").forEach(b => b.addEventListener("click", async () => {
          const res = await authFetch(`/hpho/rounds/${id}/exam/${track}/media?key=${encodeURIComponent(b.dataset.clip)}`).catch(() => null); if (!res?.ok) return;
          if (player.src) URL.revokeObjectURL(player.src); player.src = URL.createObjectURL(await res.blob()); player.hidden = false; player.play().catch(() => {}); }));
        for (const [kind, keys] of [["snaps", d.snaps.filter(k => /\.jpg$/.test(k))], ["answers", d.answers]]) {
          const host = logBox.querySelector(`[data-keys="${kind}"]`), det = host.closest("details");
          const fill = async () => { det.removeEventListener("toggle", fill); for (const k of keys) {
            const res = await authFetch(`/hpho/rounds/${id}/exam/${track}/media?key=${encodeURIComponent(k)}`).catch(() => null); if (!res?.ok) continue;
            const img = Object.assign(document.createElement("img"), { src: URL.createObjectURL(await res.blob()), title: k.split("/").pop(), loading: "lazy" });
            const link = Object.assign(document.createElement("a"), { href: img.src, target: "_blank" }); link.append(img); host.append(link); } };
          if (det.open) fill(); else det.addEventListener("toggle", fill);
        }
      } catch (e) { logBox.innerHTML = `<p class="hpho-muted">${esc(T[L()].err + (e?.code || "network"))}</p>`; }
    }
    seats.querySelector("[data-hpho-load]").addEventListener("click", load);
    /* live proctoring: a tile per seat with its latest webcam and screen photo, its heartbeat and recent alerts */
    const live = root.querySelector("[data-hpho-live]"), grid = live.querySelector("[data-hpho-live-grid]"), go = live.querySelector("[data-hpho-live-go]");
    const urls = new Map();
    const photo = async key => { if (!key) return null; if (urls.has(key)) return urls.get(key);
      const res = await authFetch(`/hpho/rounds/${id}/exam/${live.querySelector("[name=track]").value}/media?key=${encodeURIComponent(key)}`).catch(() => null); if (!res?.ok) return null;
      const u = URL.createObjectURL(await res.blob()); urls.set(key, u); return u; };
    async function refresh() {
      if (!root.isConnected) return stopLive();
      try {
        const d = await cmApi("GET", `/hpho/rounds/${id}/exam/${live.querySelector("[name=track]").value}/monitor`), keep = new Set();
        const tiles = await Promise.all(d.seats.map(async s => { const cam = await photo(s.last_webcam), scr = await photo(s.last_screen); keep.add(s.last_webcam); keep.add(s.last_screen);
          return `<article class="hpho-live-tile${s.review ? " is-review" : ""}${s.online ? "" : " is-off"}"><header><b class="hpho-no">${esc(s.candidate_no)}</b> <span class="hpho-light ${s.online ? "is-ok" : "is-bad"}">${s.online ? a.online : a.offline}</span>${s.reconnects ? ` · ${a.cols[3]} ${s.reconnects}` : ""}</header>
            <div class="hpho-live-pics">${cam ? `<img src="${cam}" alt="">` : `<span>${a.noPhoto}</span>`}${scr ? `<img src="${scr}" alt="">` : `<span>${a.noPhoto}</span>`}</div>
            <ul>${s.alerts.map(e => `<li><time>${time(e.at)}</time> ${esc(a.alerts[e.kind] || e.kind)}${e.detail ? ` <small>${esc(e.detail)}</small>` : ""}</li>`).join("")}</ul></article>`; }));
        grid.innerHTML = tiles.join("") || `<p class="hpho-muted">${a.none}</p>`;
        for (const [k, u] of urls) if (!keep.has(k)) { URL.revokeObjectURL(u); urls.delete(k); }
      } catch (e) { grid.innerHTML = `<p class="hpho-muted">${esc(T[L()].err + (e?.code || "network"))}</p>`; }
    }
    let liveTimer = 0;
    function stopLive() { clearInterval(liveTimer); liveTimer = 0; go.textContent = a.liveStart; }
    go.addEventListener("click", () => { if (liveTimer) return stopLive(); go.textContent = a.liveStop; refresh(); liveTimer = setInterval(refresh, 20000); });
  }

  function formHtml(r, mine) {
    const x = T[L()], y = new Date().getUTCFullYear(), years = [];
    for (let v = y - 14; v >= y - 40; v--) years.push(v);
    const opts = COUNTRIES.map(c => [c, countryName(c)]).sort((a, b) => a[0] === "KR" ? -1 : b[0] === "KR" ? 1 : a[1].localeCompare(b[1]));
    const sel = mine || {};
    return `<form class="hpho-form" data-hpho-round="${esc(r.id)}"><h3>${mine ? x.update : x.formTitle}</h3>
      <label>${x.country}<select name="country" required><option value=""></option>${opts.map(([c, n]) => `<option value="${c}"${sel.country === c ? " selected" : ""}>${esc(n)}</option>`).join("")}</select></label>
      <label>${x.level}<select name="level" required><option value=""></option>${Object.entries(x.levels).map(([k, v]) => `<option value="${k}"${sel.level === k ? " selected" : ""}>${v}</option>`).join("")}</select></label>
      <label>${x.email}<input type="email" name="email" required maxlength="254" autocomplete="email" value="${esc(sel.email || "")}"><small class="hpho-muted">${x.emailNote}</small></label>
      <label>${x.birth}<select name="birth_year" required><option value=""></option>${years.map(v => `<option${+sel.birth_year === v ? " selected" : ""}>${v}</option>`).join("")}</select></label>
      <label class="hpho-check"><input type="checkbox" name="age14" required> ${x.age14}</label>
      <label class="hpho-check"><input type="checkbox" name="pledge" required> ${x.pledge}</label>
      <label class="hpho-check"><input type="checkbox" name="proctoring" required> ${x.proctor}</label>
      <label class="hpho-check"><input type="checkbox" name="identity_notice" required> ${x.identity}</label>
      ${r.fee_usd && AID_ON ? `<div class="hpho-aid"><p class="hpho-muted" data-hpho-aid-auto hidden>${x.aidAuto}</p>
        <div data-hpho-aid-ask><label class="hpho-check"><input type="checkbox" name="aid_request"${sel.aid && sel.aid !== "none" && sel.aid !== "auto" ? " checked" : ""}> ${x.aidAsk}</label>
        <div data-hpho-aid-fields hidden><label>${x.aidReason}<select name="aid_reason"><option value=""></option>${Object.entries(x.aidReasons).map(([k, v]) => `<option value="${k}"${sel.aid_reason === k ? " selected" : ""}>${v}</option>`).join("")}</select></label>
        <label>${x.aidNote}<textarea name="aid_note" maxlength="300" rows="3">${esc(sel.aid_note || "")}</textarea></label></div></div></div>` : ""}
      <label class="hpho-check"><input type="checkbox" name="train_consent"${sel.train_consent ? " checked" : ""}> ${x.train}</label>
      <label class="hpho-check" data-hpho-train-guardian hidden><input type="checkbox" name="train_guardian_consent"${sel.train_consent ? " checked" : ""}> ${x.trainGuardian}</label>
      <label class="hpho-check" data-hpho-guardian hidden><input type="checkbox" name="guardian_consent"> ${x.guardian}</label>
      <p class="hpho-form-msg" role="status"></p>
      <button type="submit" class="hpho-btn">${mine ? x.update : x.submit}</button></form>`;
  }

  async function load() {
    try { if (typeof cmLoadMe === "function") await cmLoadMe(); state.data = await cmApi("GET", "/hpho"); state.error = null; }
    catch (e) { state.error = e?.code || e?.message || "network"; }
    paint();
  }
  function paint() {
    const box = document.getElementById("hphoRound"); if (!box) return;
    box.innerHTML = roundHtml();
    box.querySelectorAll(".hpho-form[data-hpho-round]").forEach(bindForm);
    bindAdmin(box);
    box.querySelector("[data-hpho-withdraw]")?.addEventListener("click", async e => {
      if (!confirm(T[L()].withdrawAsk)) return;
      try { await cmApi("DELETE", `/hpho/rounds/${encodeURIComponent(e.currentTarget.dataset.hphoWithdraw)}/entry`); } catch (err) { alert(T[L()].err + (err?.message || "")); }
      load();
    });
  }
  function bindForm(form) {
    const x = T[L()], guard = form.querySelector("[data-hpho-guardian]"), msg = form.querySelector(".hpho-form-msg");
    const sync = () => { const y = +form.birth_year.value, minor = y && new Date().getUTCFullYear() - y < 19; guard.hidden = !minor; guard.querySelector("input").required = !!minor; };
    form.birth_year.addEventListener("change", sync); sync();
    const tg = form.querySelector("[data-hpho-train-guardian]");
    const syncTrain = () => { const y = +form.birth_year.value, on = !!(y && new Date().getUTCFullYear() - y < 19) && form.train_consent.checked; tg.hidden = !on; tg.querySelector("input").required = on; };
    form.birth_year.addEventListener("change", syncTrain); form.train_consent.addEventListener("change", syncTrain); syncTrain();
    const aidBox = form.querySelector(".hpho-aid");
    const syncAid = () => { if (!aidBox) return; const auto = AID_AUTO.has(form.country.value);
      aidBox.querySelector("[data-hpho-aid-auto]").hidden = !auto; aidBox.querySelector("[data-hpho-aid-ask]").hidden = auto;
      const on = !auto && form.aid_request.checked, fields = aidBox.querySelector("[data-hpho-aid-fields]");
      fields.hidden = !on; form.aid_reason.required = on; form.aid_note.required = on; };
    if (aidBox) { form.country.addEventListener("change", syncAid); form.aid_request.addEventListener("change", syncAid); syncAid(); }
    form.addEventListener("submit", async e => {
      e.preventDefault(); if (state.busy) return; state.busy = true; msg.textContent = "…";
      const body = { country: form.country.value, level: form.level.value, birth_year: +form.birth_year.value, email: form.email.value,
        age14: form.age14.checked, pledge: form.pledge.checked, proctoring: form.proctoring.checked, identity_notice: form.identity_notice.checked, guardian_consent: form.guardian_consent.checked, train_consent: form.train_consent.checked, train_guardian_consent: form.train_guardian_consent.checked,
        ...(form.aid_request && form.aid_request.checked && !AID_AUTO.has(form.country.value) ? { aid_request: true, aid_reason: form.aid_reason.value, aid_note: form.aid_note.value } : {}) };
      try { await cmApi("POST", `/hpho/rounds/${encodeURIComponent(form.dataset.hphoRound)}/entry`, body); msg.textContent = x.saved; await load(); }
      catch (err) { const c = err?.code || err?.message || ""; msg.textContent = x.errors[c] || x.err + c; }
      finally { state.busy = false; }
    });
  }
  let timer = 0;
  function mount() {
    clearInterval(timer); state.data = null; load();
    timer = setInterval(() => { if (!document.getElementById("hphoRound")) return clearInterval(timer); if (!document.querySelector(".hpho-form:focus-within, .hpho-admin[open]")) paint(); }, 60000);
  }
  window.HL_HPHO = { view, mount, roundStatus };
})();
