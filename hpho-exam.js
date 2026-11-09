/* HPhO exam page (#/hpho/exam), IsPhO-style: the theory and the experiment exam each on their own day, listed one above
   the other at the entrance. An exam's room opens an hour before its start (technical check, then the waiting room);
   a candidate must be seated twenty minutes before the start. The waiting room counts down to the start and shows the
   general guide and the answer sheets, and the paper's language can be changed there. At the start the paper appears in
   the page (PDF.js, like Hasla Nonsul's 실전 모드); the exam window cannot be left until the end, and a candidate who
   drops out comes back through the check (each return is counted; a person reviews the recording of frequent ones).
   Proctoring (hpho-proctor.js) runs from the seat in the waiting room: the webcam with the microphone and the screen
   with the computer's own sound are recorded, and the waiting room cannot be left. Before the seat (and again after a
   disconnect) the room is scanned with the webcam. The ear, voice and room checks are judged by a model on the server;
   when it cannot answer the page asks again, and after three tries lets the candidate in with the seat flagged.
   When the time is over the page moves by itself to the submission page: the paper is gone, the recording continues,
   and writing on the sheets from then on is cheating; the answer photos go up there.
   It runs only inside the HaslaEdu desktop app's exam window, whose preload gives it window.haslaExam. The page sends
   the window's events with its own heartbeat to the server (community/src/hpho-exam.js); no token or account data
   passes to the native shell. */
(() => {
  const L = () => (typeof lang === "string" && lang === "en") ? "en" : "ko";
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const TRACKS = ["theory", "experiment"];
  const T = {
    ko: { title: "HPhO 시험", appOnly: "HPhO는 하슬라에듀 데스크톱 앱의 시험 창에서만 응시할 수 있습니다.", appGet: "데스크톱 앱 내려받기",
      entrance: "시험 입장", track: { theory: "이론 시험", experiment: "실험 시험" }, hours: "5시간", enter: "입장", back: "답안 제출하러 입장", reenter: "다시 입장",
      opensAt: v => `입장: ${v}부터 (시작 1시간 전)`, seatBy: v => `착석 마감: ${v} (시작 20분 전)`, opensLater: "입장 시간이 아닙니다", seatClosed: "착석 마감이 지나 입장할 수 없습니다", ended: "종료", submitted: "제출 완료", noRound: "응시할 수 있는 시험이 없습니다.",
      check: "기술 점검", checks: { app: "하슬라에듀 데스크톱 앱", net: "서버 연결", entry: "참가 접수", login: "로그인", camera: "웹캠 (얼굴 인식)", mic: "마이크 (문장 읽기)", screen: "화면 기록 (모니터 1대)", face: "얼굴 인식", voice: "문장 읽기 (마이크)", ears: "귀·머리·손목 검사", system: "컴퓨터 소리 녹음", displays: "모니터 1대", phone: "휴대폰 연결", room: "주변 인식 (휴대폰)", place: "휴대폰 위치" }, retry: "다시 점검", preview: "카메라 미리보기", camNeed: "웹캠·마이크·화면 기록이 모두 켜져야 응시할 수 있습니다. 다른 프로그램이 카메라를 쓰고 있지 않은지 확인하세요.",
      screenNeed: "화면 기록을 시작하지 못했습니다. 앱을 최신 버전으로 업데이트한 뒤 다시 점검하세요.", systemNeed: "컴퓨터 소리를 녹음하지 못했습니다. 하슬라에듀 앱을 최신 버전으로 업데이트한 뒤 다시 점검하세요.", displaysNeed: n => n > 1 ? `모니터가 ${n}대 연결되어 있습니다. 모니터를 하나만 남기고 나머지는 케이블을 뽑은 뒤 다시 점검하세요.` : "모니터 수를 확인하지 못했습니다. 하슬라에듀 앱을 최신 버전으로 업데이트하세요.",
      unavailable: "확인 서버가 응답하지 않았습니다. 잠시 후 다시 점검하세요.", earLive: { front: i => `${i.faces > 1 ? "두 사람 이상 보임" : i.face ? "얼굴 ✓" : "얼굴을 가운데로"} · 들어 올린 손 ${i.hands}/2${i.hands === 2 ? " ✓" : ""}${i.hold > 0 ? " · 그대로 유지" : ""}`, turn: i => !i.face ? "얼굴이 보이지 않습니다" : i.turn >= 1 ? "좋습니다, 그대로 유지" : "고개를 더 돌려 주세요" }, glassStep: "안경 가까이 보여 주기", glassFront: "안경을 벗어서 앞면(렌즈와 테 모서리)이 카메라를 향하게 가까이 들어 주세요.", glassInside: "이번에는 안경다리 안쪽이 보이게 돌려서 카메라 가까이 들어 주세요.",
      allowStep: ["화면 감시 허용", "시험 동안 아래 항목이 감독을 위해 기록됩니다. 허용해야 다음 단계로 넘어갈 수 있습니다.", "허용"],
      allowList: ["컴퓨터 화면 전체 (녹화와 사진)", "컴퓨터에서 나오는 소리", "실행 중인 프로그램 이름 (창 제목·내용은 아님)", "창 이탈·모니터 연결·화면 잠금"], net: { label: "네트워크", good: "좋음", fair: "보통", poor: "느림", off: "끊김", how: "10초마다 시험 서버까지 왕복 시간을 잽니다. 속도(Mbps)는 브라우저가 추정한 값입니다." }, phoneFirst: "먼저 휴대폰을 연결합니다. 휴대폰 카메라로 아래 QR을 찍어 여세요. 휴대폰 화면에서 「카메라 켜기」를 누르면 연결되고, 다음 점검으로 넘어갑니다. 주변 스캔은 얼굴·마이크·귀 점검 뒤에 휴대폰으로 합니다.", coverTitle: "모니터가 추가로 연결되었습니다", coverText: "추가 모니터의 케이블을 지금 뽑으세요. 뽑을 때까지 시험지가 가려지며, 이 상황은 기록되어 감독관이 검토합니다.",
      phoneStep: ["휴대폰 감독 연결", "휴대폰 카메라로 아래 QR을 찍어 휴대폰에서 여세요. 휴대폰으로 방을 한 방향씩 천천히 비추면 AI가 확인하고, 마지막으로 휴대폰을 옆이나 뒤에 세워 본인·손·책상·화면이 보이게 합니다. 이 세 가지가 끝나야 연결이 완료되고 다음 점검으로 넘어갑니다."],
      phoneList: { online: "QR로 휴대폰 열기", waiting: "QR을 찍어 주세요", scan: (n, m) => `주변 스캔 ${n} / ${m}`, placed: "휴대폰 위치 확인" }, phoneLost: "휴대폰 감독이 끊겼습니다. 휴대폰 화면을 다시 켜거나, 이 QR을 휴대폰으로 다시 찍으세요. 끊긴 시간은 기록됩니다.", phoneOn: "휴대폰", phoneOk: "연결", phoneBad: "끊김",
      saving: (n, m) => `감독 녹화를 올리는 중… ${n} / ${m}. 창이 닫힐 때까지 기다려 주세요.`,
      roomStep: ["주변 스캔", "웹캠(노트북이면 노트북 화면)을 천천히 돌려 방을 보여 주세요. 화면에 나오는 방향으로 돌리고, 숫자가 0이 될 때까지 멈춰 주세요.", "주변 스캔 시작"],
      views: { front: "앞쪽 벽", left: "왼쪽 벽", right: "오른쪽 벽", back: "뒤쪽 (등 뒤)", ceiling: "천장", desk: "책상 위 전체", under: "책상 아래 · 발밑", done: "확인하는 중…" },
      room: { person: "다른 사람", phone: "휴대폰·스마트워치·태블릿", screen: "다른 화면(모니터·노트북·TV)", headset: "이어폰·헤드셋", notes: "책·필기" }, roomBlocked: list => `주변에서 ${list}이(가) 보였습니다. 치우거나 다른 곳으로 옮긴 뒤 다시 스캔하세요.`, roomFail: "스캔 사진을 보내지 못했습니다. 다시 스캔하세요.",
      faceStep: ["웹캠 · 얼굴 인식", "카메라를 정면으로 바라보세요. 미리보기의 얼굴 테두리가 초록색이 되도록 가운데에 앉아 주세요."],
      face: { no_video: "카메라 영상이 들어오지 않습니다. 다른 프로그램이 카메라를 쓰고 있지 않은지 확인하세요.", detector: "얼굴 인식 기능을 불러오지 못했습니다. 인터넷 연결을 확인한 뒤 다시 점검하세요.", none: "얼굴이 보이지 않습니다. 카메라를 정면으로 바라보세요.", many: "화면에 두 사람 이상이 보입니다. 혼자 있는 곳에서 응시하세요.", dark: "얼굴이 너무 어둡습니다. 조명을 켜거나 창 쪽을 바라보고 앉으세요.", small: "얼굴이 너무 작게 보입니다. 카메라에 조금 더 가까이 앉으세요.", off: "얼굴이 화면 가장자리에 있습니다. 미리보기 가운데로 오도록 자리를 옮기세요." },
      micStep: ["마이크 확인", "버튼을 누르고, 「지금 읽어 주세요」가 뜨면 아래 문장을 처음부터 끝까지 또박또박 읽어 주세요. 문장을 다 읽어야 통과합니다.", "마이크 점검 시작", "조용히 기다려 주세요… 주변 소리를 재는 중", "지금 읽어 주세요", "들은 문장을 확인하는 중…"],
      mic: { no_mic: "마이크를 찾지 못했습니다. 마이크를 연결하고 다시 점검하세요.", no_audio: "소리를 분석하지 못했습니다. 다시 점검하세요.", silent: "소리가 전혀 들리지 않습니다. 마이크가 음소거되어 있지 않은지, 올바른 마이크가 선택되었는지 확인하세요.", quiet: "목소리가 너무 작게 들립니다. 마이크에 가까이 앉아 조금 더 크게 읽어 주세요.", short: "문장 전체가 들리지 않았습니다. 소리를 지르거나 한 단어만 말하면 통과할 수 없습니다. 화면의 문장을 처음부터 끝까지 읽어 주세요.", not_said: "화면의 문장이 들리지 않았습니다. 문장을 그대로, 또박또박 읽어 주세요.", failed: "녹음을 보내지 못했습니다. 다시 점검하세요." },
      earStep: ["귀·머리·손목 검사", "이어폰·헤드셋, 챙 있는 모자(야구모자 등), 스마트워치, 스마트 안경을 확인합니다. 비니처럼 챙 없는 모자는 괜찮습니다. 머리카락을 귀 뒤로 넘기고 버튼을 누르세요.", "검사 시작"],
      ear: { front: "모자나 머리카락이 귀를 덮지 않게 하고, 카메라를 정면으로 보고, 두 손을 얼굴 양옆으로 들어 손바닥과 손목이 보이게 하세요. 두 손이 보이면 자동으로 찍힙니다.", detector: "손·얼굴 인식 기능을 불러오지 못해 검사를 진행할 수 없습니다. 인터넷 연결을 확인하고 다시 검사하세요.", hands: "두 손이 얼굴 높이로 올라온 것이 보이지 않았습니다. 두 손을 얼굴 양옆으로 들고 손목까지 화면에 보이게 한 뒤 다시 검사하세요.", turn: "고개가 충분히 돌아가지 않았습니다. 귀가 카메라를 향할 때까지 고개를 더 돌리고 잠시 멈춰 주세요.", wrists: "사진에서 두 손목이 잘 보이지 않았습니다. 소매를 걷고 두 손을 얼굴 옆으로 들어 다시 검사하세요.", stop: "", cap: "챙이 있는 모자(야구모자·버킷햇 등)는 눈을 가릴 수 있어 벗어야 합니다. 비니처럼 챙 없는 모자는 귀가 다 보이면 괜찮습니다.", covered: "모자(비니 등)나 머리카락이 귀를 덮고 있습니다. 귀가 다 보이게 올리거나 벗은 뒤 다시 검사하세요.", glasses: "스마트 안경으로 보입니다(카메라·스피커·불빛). 일반 안경으로 바꾼 뒤 다시 검사하세요.", glasses_unclear: "안경이 잘 보이지 않았습니다. 밝은 곳에서 카메라에 더 가까이 보여 주세요.", watch: "시계·스마트워치는 종류와 상관없이 착용할 수 없습니다(남은 시간은 시험 화면에 표시됩니다). 풀어서 손이 닿지 않는 곳에 두고 다시 검사하세요.", first: "고개를 천천히 한쪽으로 돌려 귀가 카메라에 보이게 하고, 잠시 멈추세요.", second: "이번에는 반대쪽으로 고개를 돌려 다른 쪽 귀를 보여 주세요.", done: "확인하는 중…", device_first: "처음 보여 준 쪽 귀에 이어폰 같은 기기가 보입니다. 한쪽만 끼어도 안 됩니다. 빼고 다시 검사하세요.", device_second: "두 번째로 보여 준 쪽 귀에 이어폰 같은 기기가 보입니다. 한쪽만 끼어도 안 됩니다. 빼고 다시 검사하세요.", device: "귀나 머리에 이어폰·헤드폰·헤드셋 같은 기기가 보입니다. 모두 빼고 다시 검사하세요. 보청기를 써야 한다면 시험 전에 운영진에게 알려 주세요.", unclear: "귀가 잘 보이지 않았습니다. 머리카락을 넘기고 밝은 곳에서 고개를 조금 더 돌려 다시 검사하세요.", failed: "사진을 보내지 못했습니다. 다시 검사하세요." }, ok: "확인", bad: "문제 있음", wait: "확인 중…",
      notReg: "이 회차에 접수하지 않았습니다.", login: "로그인하세요.", room: "대기실", startsIn: "시험 시작까지", candidate: "수험번호", autoStart: "시작 시각이 되면 시험지가 자동으로 열립니다. 이 창을 닫지 마세요.",
      paperLang: "시험지 언어", paperLangNote: "시험 시작 전까지 바꿀 수 있습니다.", langs: { ko: "한국어", en: "English" },
      docs: "시험 자료", docNames: { guide: "General Guide", writing: "답안지", answer: "Answer Sheet", paper: "문제지" }, noDocs: "아직 공개된 자료가 없습니다.", docsNote: "답안지와 Answer Sheet는 미리 인쇄해 두세요.",
      left: "남은 시간", rules: ["시험 중에는 이 창만 사용하세요. 다른 프로그램과 웹사이트는 사용할 수 없습니다.", "시험이 끝날 때까지 퇴장할 수 없습니다. 연결이 끊기면 다시 들어올 수 있지만, 재접속은 모두 기록되며 잦으면 감독관이 녹화를 검토해 부정행위로 판정할 수 있습니다.", "시험 시간이 끝나면 화면이 제출 페이지로 바뀝니다. 그때부터 답안지에 무엇이든 쓰면 부정행위로 간주됩니다.", "시계·스마트워치는 착용할 수 없습니다. 남은 시간은 이 창 위쪽에 표시됩니다.", "답안지에는 수험번호만 적으세요."],
      reconnects: n => `재접속 ${n}회 · 잦은 재접속은 감독관이 녹화를 검토합니다`, paperLoading: "시험지를 불러오는 중…", paperFail: "시험지를 불러오지 못했습니다. 잠시 후 다시 시도합니다.", paperNone: "시험지가 아직 올라오지 않았습니다. 감독관에게 문의하세요.", zoomFit: "폭 맞춤",
      overTitle: "시험 시간이 끝났습니다", overPen: "지금 바로 펜을 내려놓으세요. 지금부터 답안지에 무엇이든 쓰면 부정행위로 간주됩니다.", overRec: "감독 녹화는 제출을 마칠 때까지 계속됩니다.",
      uploadTitle: "답안 제출", uploadUntil: "제출 마감까지", uploadHow: "답안지를 한 장씩 웹캠에 비추어 찍거나, 사진 파일을 올리세요. 순서대로 올리면 쪽 번호가 매겨집니다.", shoot: "웹캠으로 한 장 찍기", files: "사진 파일 올리기", pages: n => `올린 쪽: ${n}`, submit: "제출하기", submitAsk: n => `${n}쪽을 제출할까요? 제출하면 더 올릴 수 없습니다.`, submitEmpty: "아직 올린 쪽이 없습니다. 그래도 제출할까요?", uploading: "올리는 중…", uploadFail: "올리지 못했습니다. 다시 시도하세요.",
      done: "제출을 마쳤습니다", doneNote: "수고하셨습니다. 시험 창이 곧 닫힙니다.", leave: "시험 창 닫기", conn: "연결", connOk: "정상", connBad: "끊김 · 다시 연결 중", proctor: "감독", proctorOn: "기록 중",
      errors: { seating_closed: "착석 마감(시작 20분 전)이 지나 입장할 수 없습니다.", not_open: "아직 입장 시간이 아닙니다. 시작 1시간 전부터 입장할 수 있습니다.", exam_over: "시험이 끝났습니다.", not_registered: "이 회차에 접수하지 않았습니다.", desktop_app_required: "하슬라에듀 데스크톱 앱에서만 응시할 수 있습니다.", upload_closed: "제출 시간이 끝났습니다.", network: "서버에 연결하지 못했습니다. 인터넷 연결을 확인하세요." } },
    en: { title: "HPhO exam", appOnly: "HPhO can only be sat in the exam window of the HaslaEdu desktop app.", appGet: "Get the desktop app",
      entrance: "Exam entrance", track: { theory: "Theory exam", experiment: "Experimental exam" }, hours: "5 hours", enter: "Enter", back: "Enter to submit answers", reenter: "Enter again",
      opensAt: v => `Entry from ${v} (an hour before the start)`, seatBy: v => `Be seated by ${v} (20 minutes before the start)`, opensLater: "Not open yet", seatClosed: "Seating has closed", ended: "Over", submitted: "Submitted", noRound: "There is no exam to sit.",
      check: "Technical check", checks: { app: "HaslaEdu desktop app", net: "Server connection", entry: "Registration", login: "Signed in", camera: "Webcam (face)", mic: "Microphone (reading aloud)", screen: "Screen recording (one monitor)", face: "Face", voice: "Reading aloud (microphone)", ears: "Ears, head and wrists", system: "Computer sound recording", displays: "One monitor", phone: "Phone connected", room: "Room check (phone)", place: "Phone position" }, retry: "Check again", preview: "Camera preview", camNeed: "The webcam, microphone and screen recording must all be on to sit the exam. Make sure no other program is using the camera.",
      screenNeed: "Screen recording could not start. Update the app to the latest version, then check again.", systemNeed: "The computer's sound could not be recorded. Update the HaslaEdu app to the latest version, then check again.", displaysNeed: n => n > 1 ? `${n} monitors are connected. Unplug all but one, then check again.` : "The number of monitors could not be read. Update the HaslaEdu app to the latest version.",
      unavailable: "The checking server did not answer. Check again in a moment.", earLive: { front: i => `${i.faces > 1 ? "more than one person" : i.face ? "face ✓" : "face to the middle"} · hands up ${i.hands}/2${i.hands === 2 ? " ✓" : ""}${i.hold > 0 ? " · hold still" : ""}`, turn: i => !i.face ? "your face is not seen" : i.turn >= 1 ? "good, hold still" : "turn your head further" }, glassStep: "Show your glasses up close", glassFront: "Take your glasses off and hold the front (lenses and frame corners) close to the camera.", glassInside: "Now turn them to show the inside of the temples, close to the camera.",
      allowStep: ["Allow screen monitoring", "During the exam the following are recorded for proctoring. You must allow them to go on.", "Allow"],
      allowList: ["The whole computer screen (recording and photos)", "Sound played on the computer", "The names of running programs (not window titles or contents)", "Leaving the window, connecting a monitor, locking the screen"], net: { label: "Network", good: "Good", fair: "Fair", poor: "Slow", off: "Offline", how: "The round trip to the exam server, measured every 10 s; the speed (Mbps) is the browser's estimate." }, phoneFirst: "First connect your phone: scan the QR below with its camera and open it. Press “Turn on the camera” on the phone to connect; the next checks follow. The room scan is done with the phone after the face, microphone and ear checks.", coverTitle: "Another monitor was connected", coverText: "Unplug the extra monitor now. The paper is covered until you do; this is recorded and reviewed by a proctor.",
      phoneStep: ["Connect the phone", "Scan the QR below with your phone camera and open it on the phone. Show the room slowly, one side at a time, for the AI to check; then stand the phone to your side or behind you so it sees you, your hands, the desk and the screen. The connection is complete, and the next checks follow, only when all three are done."],
      phoneList: { online: "Phone opened from the QR", waiting: "scan the QR", scan: (n, m) => `Room scan ${n} / ${m}`, placed: "Phone position checked" }, phoneLost: "The phone proctoring stopped. Turn the phone's screen back on, or scan this QR again. The time it was off is recorded.", phoneOn: "Phone", phoneOk: "Connected", phoneBad: "Lost",
      saving: (n, m) => `Uploading the proctoring recording… ${n} / ${m}. Wait until the window closes.`,
      roomStep: ["Room scan", "Slowly turn the webcam (or the laptop) to show the room. Point it where the screen says and hold still until the count reaches 0.", "Start the room scan"],
      views: { front: "The wall in front", left: "The left wall", right: "The right wall", back: "Behind you", ceiling: "The ceiling", desk: "The whole desk top", under: "Under the desk, your feet", done: "Checking…" },
      room: { person: "another person", phone: "a phone, smartwatch or tablet", screen: "another screen (monitor, laptop, TV)", headset: "earphones or a headset", notes: "books or notes" }, roomBlocked: list => `The scan shows ${list}. Remove it, then scan again.`, roomFail: "The scan photos could not be sent. Scan again.",
      faceStep: ["Webcam · face", "Look straight at the camera. Sit so the frame around your face in the preview turns green."],
      face: { no_video: "No picture from the camera. Make sure no other program is using it.", detector: "Face detection could not load. Check your internet connection and try again.", none: "Your face cannot be seen. Look straight at the camera.", many: "More than one person is in view. Sit the exam alone.", dark: "Your face is too dark. Turn on a light or face a window.", small: "Your face looks too small. Sit a little closer to the camera.", off: "Your face is at the edge of the picture. Move so it is in the middle of the preview." },
      micStep: ["Microphone check", "Press the button and, when “Read now” appears, read the whole sentence below clearly. Only the whole sentence passes.", "Start the microphone check", "Please wait quietly… measuring the room", "Read now", "Checking what was heard…"],
      mic: { no_mic: "No microphone was found. Connect one and check again.", no_audio: "The sound could not be analysed. Check again.", silent: "No sound at all. Make sure the microphone is not muted and the right one is selected.", quiet: "Your voice is too quiet. Sit closer to the microphone and read a little louder.", short: "The whole sentence was not heard. A shout or a single word does not pass: read the sentence on the screen from start to end.", not_said: "The sentence on the screen was not heard. Read it exactly as written, clearly.", failed: "The recording could not be sent. Check again." },
      earStep: ["Ears, head and wrists", "This checks for earphones or a headset, a cap or hat with a brim, and a smartwatch. A beanie or other hat without a brim is fine. Tuck your hair behind your ears and press the button.", "Start the check"],
      ear: { front: "Look straight at the camera and raise both hands beside your face, palms and wrists showing. The photo is taken once both hands are seen.", detector: "The hand and face recognition could not load, so the check cannot go on. Check your internet connection and check again.", hands: "Both hands were not seen raised to face height. Raise them beside your face with the wrists in the picture, then check again.", turn: "Your head did not turn far enough. Turn until the ear faces the camera and hold still.", wrists: "Both wrists could not be seen in the photo. Push up your sleeves, raise both hands beside your face and check again.", stop: "", cap: "A cap or hat with a brim (a baseball cap, a bucket hat) can hide your eyes: take it off. A beanie is fine if both ears show.", covered: "A hat (a beanie…) or hair covers your ears. Lift it or take it off so both ears show, then check again.", glasses: "These look like smart glasses (camera, speaker or light). Switch to ordinary glasses, then check again.", glasses_unclear: "The glasses could not be seen well. Hold them closer to the camera in good light.", watch: "No watch of any kind may be worn (the time left is shown on the exam screen). Take it off, put it out of reach and check again.", first: "Slowly turn your head to one side so one ear faces the camera, and hold still.", second: "Now turn to the other side to show the other ear.", done: "Checking…", device_first: "A device such as an earbud can be seen in the first ear you showed. Even one earbud is not allowed: take it out and check again.", device_second: "A device such as an earbud can be seen in the second ear you showed. Even one earbud is not allowed: take it out and check again.", device: "Earphones, headphones, a headset or another device can be seen on your ears or head. Take them off and check again. If you need a hearing aid, tell the organisers before the exam.", unclear: "Your ears could not be seen clearly. Move your hair aside, use more light, turn your head a little further and check again.", failed: "The photos could not be sent. Check again." }, ok: "OK", bad: "Problem", wait: "Checking…",
      notReg: "You are not registered for this round.", login: "Please sign in.", room: "Waiting room", startsIn: "Exam starts in", candidate: "Candidate number", autoStart: "The paper opens by itself at the start time. Keep this window open.",
      paperLang: "Language of the paper", paperLangNote: "You can change it until the start.", langs: { ko: "한국어", en: "English" },
      docs: "Exam documents", docNames: { guide: "General Guide", writing: "Writing sheet", answer: "Answer Sheet", paper: "Paper" }, noDocs: "No documents have been published yet.", docsNote: "Print the writing and answer sheets beforehand.",
      left: "Time left", rules: ["Use only this window during the exam. Other programs and websites are not allowed.", "You cannot leave until the exam ends. If you are disconnected you can come back, but every return is recorded, and if it happens often a proctor reviews the recording and may rule it cheating.", "When the time is over the screen changes to the submission page. Writing anything on your sheets from then on is cheating.", "No watch or smartwatch may be worn. The time left is shown at the top of this window.", "Write only your candidate number on the answer sheets."],
      reconnects: n => `Reconnected ${n}× · frequent reconnects are reviewed by a proctor`, paperLoading: "Loading the paper…", paperFail: "The paper could not be loaded. Trying again shortly.", paperNone: "The paper has not been uploaded yet. Ask the organisers.", zoomFit: "Fit width",
      overTitle: "Time is over", overPen: "Put your pen down now. Writing anything on your sheets from now on is cheating.", overRec: "The proctoring recording continues until you have submitted.",
      uploadTitle: "Submit your answers", uploadUntil: "Submission closes in", uploadHow: "Hold each sheet up to the webcam and take a photo, or upload photo files. Pages are numbered in the order you add them.", shoot: "Take one page with the webcam", files: "Upload photo files", pages: n => `Pages added: ${n}`, submit: "Submit", submitAsk: n => `Submit ${n} page(s)? You cannot add more afterwards.`, submitEmpty: "No pages yet. Submit anyway?", uploading: "Uploading…", uploadFail: "Upload failed. Try again.",
      done: "Submitted", doneNote: "Well done. The exam window closes shortly.", leave: "Close the exam window", conn: "Connection", connOk: "Online", connBad: "Lost · reconnecting", proctor: "Proctoring", proctorOn: "Recording",
      errors: { seating_closed: "Seating closed 20 minutes before the start; you cannot enter.", not_open: "Not open yet. Entry opens an hour before the start.", exam_over: "The exam is over.", not_registered: "You are not registered for this round.", desktop_app_required: "The exam can only be sat in the HaslaEdu desktop app.", upload_closed: "Submission has closed.", network: "Could not reach the server. Check your internet connection." } },
  };
  const bridge = () => (window.haslaExam && typeof window.haslaExam.onEvent === "function") ? window.haslaExam : null;
  let st = { round: null, entry: null, track: null, tracks: {}, session: null, phase: "lobby", online: true, seq: 0, queue: [], timer: 0, flushTimer: 0, unsub: null, docs: [], pages: 0 };
  const fmt = sec => { sec = Math.max(0, Math.floor(sec)); const h = Math.floor(sec / 3600), m = Math.floor(sec % 3600 / 60), s = sec % 60; return (h ? h + ":" : "") + String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0"); };
  const skew = () => st.skew || 0, nowS = () => Math.floor(Date.now() / 1000) + skew();
  const when = s => new Date(s * 1000).toLocaleString(L() === "en" ? "en-GB" : "ko-KR", { dateStyle: "medium", timeStyle: "short" });
  const hm = s => new Date(s * 1000).toLocaleTimeString(L() === "en" ? "en-GB" : "ko-KR", { hour: "2-digit", minute: "2-digit" });
  const path = (a, track = st.track) => `/hpho/rounds/${encodeURIComponent(st.round.id)}/exam/${track}/${a}`;
  const errText = e => { const x = T[L()], c = e?.code || e?.message || "network"; return x.errors[c] || c; };
  const W = () => st.tracks[st.track]?.window;
  const sync = d => { if (d?.now) st.skew = d.now - Math.floor(Date.now() / 1000); };

  function push(kind, detail) {
    st.seq++;
    st.queue.push({ seq: st.seq, t: nowS(), kind, ...(detail ? { detail: String(detail).slice(0, 200) } : {}) });
  }
  async function flush() {
    if (!["room", "exam", "submit"].includes(st.phase)) return;
    if (!st.queue.length) push("heartbeat");
    const batch = st.queue.splice(0, 100);
    try { const r = await cmApi("POST", path("events"), { events: batch }); st.online = true; sync(r);
      const w = W(); if (w && r.ends_at) { w.ends = r.ends_at; if (r.upload_until) w.upload_until = r.upload_until; } }
    catch (e) { st.queue.unshift(...batch); st.online = false; }
    paintBar();
  }
  /* multipart to the exam API (snapshots, checks, answer pages) */
  async function sendForm(action, fields) {
    const fd = new FormData(); for (const [k, v] of Object.entries(fields)) v instanceof Blob ? fd.set(k, v, k + (v.type === "audio/wav" ? ".wav" : ".jpg")) : fd.set(k, v);
    const res = await fetch(cmBase() + "/api" + path(action), { method: "POST", headers: { Authorization: "Bearer " + cmTok() }, body: fd });
    const j = await res.json().catch(() => ({}));
    if (!res.ok) throw { code: j.error || j.code || "network" };
    return j;
  }

  function view() {
    return `<div class="shell hpho hpho-exam"><div class="hpho-exam-bar" id="hphoExamBar"></div><div id="hphoExamMain"><p class="hpho-muted">…</p></div></div>`;
  }
  function paintBar() {
    const x = T[L()], bar = document.getElementById("hphoExamBar"); if (!bar) return;
    const w = W(), live = ["room", "exam", "submit"].includes(st.phase);
    const left = st.phase === "exam" ? w.ends - nowS() : st.phase === "submit" ? w.upload_until - nowS() : st.phase === "room" ? w.start_at - nowS() : null;
    const n = x.net, level = !navigator.onLine || st.offline ? "off" : st.rtt == null || st.rtt < 300 ? "good" : st.rtt < 900 ? "fair" : "poor";
    const conn = navigator.connection, speed = level !== "off" && conn?.downlink ? ` · ${conn.downlink >= 10 ? Math.round(conn.downlink) : conn.downlink} Mbps` : "";
    const netBadge = `<span class="hpho-net is-${level}" title="${n.how}"><i></i><i></i><i></i> ${n.label}: ${n[level]}${st.rtt != null && level !== "off" ? ` · ${st.rtt} ms` : ""}${speed}</span>`;
    bar.innerHTML = `<b class="hpho-exam-title"><img class="hpho-exam-icon hpho-logo-light" src="logo/brand/hpho-icon-light.svg?v=20261109-hpho" alt=""><img class="hpho-exam-icon hpho-logo-dark" src="logo/brand/hpho-icon-dark.svg?v=20261109-hpho" alt="" aria-hidden="true">${x.title}${st.round ? " · " + (st.round.status === "draft" ? (L() === "en" ? "Practice exam" : "모의 시험") : esc(st.round.title[L()])) : ""}${st.track && st.phase !== "lobby" ? " · " + x.track[st.track] : ""}</b>
      ${st.entry ? `<span>${x.candidate} <b class="hpho-no">${esc(st.entry.candidate_no)}</b></span>` : ""}${netBadge}
      ${live ? `<span class="hpho-light ${st.online ? "is-ok" : "is-bad"}">${x.conn}: ${st.online ? x.connOk : x.connBad}</span><span class="hpho-light is-ok">${x.proctor}: ${x.proctorOn}</span><span class="hpho-light ${st.phoneOnline === false ? "is-bad" : "is-ok"}">${x.phoneOn}: ${st.phoneOnline === false ? x.phoneBad : x.phoneOk}</span>
        <span class="hpho-exam-clock${left < 600 && st.phase !== "room" ? " is-low" : ""}">${st.phase === "submit" ? x.uploadUntil : st.phase === "room" ? x.startsIn : x.left} <b>${fmt(left)}</b></span>` : ""}`;
  }
  const leaveBtn = () => bridge()?.leave ? `<button type="button" class="hpho-link" id="hphoExamLeave">${T[L()].leave}</button>` : "";
  const wireLeave = box => box.querySelector("#hphoExamLeave")?.addEventListener("click", () => bridge()?.leave?.());

  /* the entrance: the theory exam above, the experiment below; each opens an hour before its start */
  function trackState(track) {
    const s = st.tracks[track], w = s?.window, t = nowS(), seat = s?.session;
    if (!w) return null;
    if (seat?.submitted_at) return { label: T[L()].submitted, can: false };
    if (t >= w.upload_until) return { label: T[L()].ended, can: false };
    if (t >= w.ends) return seat?.started_at ? { label: T[L()].back, can: true } : { label: T[L()].ended, can: false };
    if (t < w.opens) return { label: T[L()].opensLater, can: false };
    if (!seat && t >= w.seat_by && st.round.status !== "draft") return { label: T[L()].seatClosed, can: false };
    return { label: seat ? T[L()].reenter : T[L()].enter, can: true };
  }
  function paintLobby(box) {
    const x = T[L()];
    const cards = TRACKS.filter(k => st.tracks[k]).map(k => {
      const w = st.tracks[k].window, s = trackState(k);
      return `<article class="hpho-track" data-track="${k}"><div class="hpho-track-head"><h3>${x.track[k]}</h3><span class="hpho-muted">${x.hours}</span></div>
        <p class="hpho-track-when">${when(w.start_at)} – ${hm(w.ends)}</p>
        <p class="hpho-muted">${x.opensAt(hm(w.opens))} · ${x.seatBy(hm(w.seat_by))}</p>
        <p><button type="button" class="hpho-btn" data-enter="${k}"${s.can ? "" : " disabled"}>${esc(s.label)}</button></p></article>`;
    }).join("");
    box.innerHTML = `<section class="hpho-round hpho-lobby"><h2>${x.entrance}</h2>
      <p class="hpho-muted">${L() === "en" ? "Times are in your time zone." : "시각은 내 시간대 기준입니다."}</p>
      <div class="hpho-tracks">${cards || `<p>${x.noRound}</p>`}</div>
      ${st.error ? `<p class="hpho-form-msg">${esc(st.error)}</p>` : ""}<p class="hpho-check-actions">${leaveBtn()}</p></section>`;
    box.querySelectorAll("[data-enter]").forEach(b => b.addEventListener("click", () => enter(b.dataset.enter)));
    wireLeave(box);
  }
  function paintCheck(box) {
    const x = T[L()], c = st.checks || {}, keys = ["net", "screen", "camera", "mic", "system", ...(st.quick ? [] : ["ears"]), "phone", "room"];
    const row = k => `<li class="${c[k] === true ? "is-ok" : c[k] === false ? "is-bad" : ""}"><span>${x.checks[k]}</span><b>${c[k] === true ? x.ok : c[k] === false ? x.bad : x.wait}</b></li>`;
    const s = st.step;
    const step = s ? `<div class="hpho-step"><h3>${esc(s.title)}</h3><p>${esc(s.text)}</p>${s.list ? `<ul class="hpho-allow-list">${s.list.map(i => `<li>${esc(i)}</li>`).join("")}</ul>` : ""}${s.qr ? `<div class="hpho-qr">${s.qr}<ul id="hphoPhoneList"></ul></div>` : ""}${s.view ? `<p class="hpho-scan-view">${esc(s.view)}${s.count ? ` <b>${s.count}</b>` : ""}</p>` : ""}${s.quote ? `<p class="hpho-step-quote">${esc(s.quote)}</p>` : ""}${s.cue ? `<p class="hpho-step-cue" id="hphoCue">${esc(s.cue)}</p>` : ""}${s.meter ? `<div class="hpho-meter" aria-hidden="true"><i id="hphoMeter"></i></div>` : ""}${s.button ? `<p><button type="button" class="hpho-btn" id="hphoStepGo">${esc(s.button)}</button></p>` : ""}</div>` : "";
    const done = keys.filter(k => c[k] === true).length;
    box.innerHTML = `<section class="hpho-round hpho-check"><div class="hpho-check-head"><h2>${x.check} · ${x.track[st.track]}</h2><span class="hpho-muted">${done} / ${keys.length}</span></div>
      <div class="hpho-check-grid"><ul class="hpho-checks">${keys.map(row).join("")}</ul>
      <div class="hpho-check-side"><div class="hpho-check-media"><div class="hpho-self-slot" id="hphoSelfSlot"><span>${x.preview}</span></div>
        <p class="hpho-check-actions">${st.error ? `<button type="button" class="hpho-btn" id="hphoExamRetry">${x.retry}</button>` : ""}${leaveBtn()}</p></div>
        <div class="hpho-check-info">${step}${st.error ? `<div class="hpho-check-problem"><p class="hpho-form-msg">${esc(st.error)}</p></div>` : ""}</div></div></div></section>`;
    window.HL_HPHO_PROCTOR?.dock?.(box.querySelector("#hphoSelfSlot"));
    const fresh = keys.filter(k => c[k] === true && !st.dinged?.has(k));
    if (fresh.length) { (st.dinged ||= new Set()); fresh.forEach(k => st.dinged.add(k)); ding(); }
    wireLeave(box);
    box.querySelector("#hphoExamRetry")?.addEventListener("click", () => { st.error = null; check(); });
    box.querySelector("#hphoStepGo")?.addEventListener("click", () => { const go = st.step?.go; st.step = { ...st.step, button: null, go: null }; paint(); go?.(); }, { once: true });
  }
  function docTabs(kinds) {
    /* each kind once, in the paper's language when there is one, else the other */
    const out = [];
    for (const kind of kinds) {
      const d = st.docs.find(d => d.kind === kind && d.lang === st.paperLang) || st.docs.find(d => d.kind === kind);
      if (d) out.push(d);
    }
    return out;
  }
  function paintRoom(box) {
    const x = T[L()], w = W(), langs = [...new Set(st.docs.filter(d => d.kind === "paper").map(d => d.lang))];
    const choices = langs.length ? langs : ["ko", "en"];
    const tabs = docTabs(["guide", "writing", "answer"]);
    window.HL_HPHO_PROCTOR?.dock?.(null);
    box.innerHTML = `<section class="hpho-round hpho-room"><h2>${x.room} · ${x.track[st.track]}</h2>
      <div class="hpho-room-grid"><div><p class="hpho-muted">${x.startsIn}</p><p class="hpho-exam-big" id="hphoCountdown">${fmt(w.start_at - nowS())}</p><p class="hpho-muted">${x.autoStart}</p>
        <label class="hpho-lang">${x.paperLang} <select id="hphoPaperLang">${choices.map(l => `<option value="${l}"${l === st.paperLang ? " selected" : ""}>${x.langs[l] || l}</option>`).join("")}</select></label>
        <p class="hpho-muted">${x.paperLangNote}</p></div>
        <ol class="hpho-exam-rules">${x.rules.map(r => `<li>${r}</li>`).join("")}</ol></div>
      ${st.session?.reconnects ? `<p class="hpho-muted">${x.reconnects(st.session.reconnects)}</p>` : ""}
      <h3>${x.docs}</h3>${tabs.length ? `<p class="hpho-muted">${x.docsNote}</p><div id="hphoDocs"></div>` : `<p class="hpho-muted">${x.noDocs}</p>`}
      ${st.error ? `<p class="hpho-form-msg">${esc(st.error)}</p>` : ""}</section>`;
    box.querySelector("#hphoPaperLang").addEventListener("change", async e => {
      const v = e.target.value;
      try { await cmApi("POST", path("lang"), { lang: v }); st.paperLang = v; push("paper_lang", v); st.error = null; }
      catch (err) { st.error = errText(err); e.target.value = st.paperLang; }
      paint();
    });
    if (tabs.length) box.querySelector("#hphoDocs").append(viewer(tabs));
  }
  function paintExam(box) {
    const x = T[L()];
    window.HL_HPHO_PROCTOR?.dock?.(null);                 /* the camera preview back in the corner, out of the check page */
    if (box.querySelector(".hpho-paper")) return;
    const paper = docTabs(["paper"]), sheets = docTabs(["answer", "writing", "guide"]);
    box.innerHTML = `<section class="hpho-round hpho-paper">${st.session?.reconnects ? `<p class="hpho-muted">${x.reconnects(st.session.reconnects)}</p>` : ""}<div id="hphoPaper"></div></section>`;
    const host = box.querySelector("#hphoPaper");
    if (!paper.length) host.innerHTML = `<p>${x.paperNone}</p>`;
    host.append(viewer([...paper, ...sheets]));
  }
  function paintSubmit(box) {
    const x = T[L()];
    box.innerHTML = `<section class="hpho-round hpho-over"><h2>${x.overTitle}</h2><p class="hpho-over-pen">${x.overPen}</p><p class="hpho-muted">${x.overRec}</p></section>
      <section class="hpho-round hpho-upload"><h2>${x.uploadTitle}</h2><p>${x.uploadHow}</p>
        <div class="hpho-upload-grid"><div class="hpho-self-slot" id="hphoSelfSlot"></div>
          <div><p class="hpho-check-actions"><button type="button" class="hpho-btn" id="hphoShoot">${x.shoot}</button>
            <label class="hpho-btn hpho-btn-quiet">${x.files}<input type="file" id="hphoFiles" accept="image/jpeg,image/png" multiple hidden></label></p>
            <p id="hphoPages"><b>${x.pages(st.pages)}</b></p><div class="hpho-thumbs" id="hphoThumbs"></div>
            <p class="hpho-form-msg" id="hphoUpMsg">${st.error ? esc(st.error) : ""}</p>
            <p><button type="button" class="hpho-btn" id="hphoSubmit">${x.submit}</button></p></div></div></section>`;
    window.HL_HPHO_PROCTOR?.dock?.(box.querySelector("#hphoSelfSlot"));
    const thumbs = box.querySelector("#hphoThumbs");
    for (const u of st.thumbs || []) thumbs.append(Object.assign(document.createElement("img"), { src: u, alt: "" }));
    box.querySelector("#hphoShoot").addEventListener("click", async () => { const b = await window.HL_HPHO_PROCTOR?.still?.(); if (b) addPages([b]); });
    box.querySelector("#hphoFiles").addEventListener("change", e => { addPages([...e.target.files]); e.target.value = ""; });
    box.querySelector("#hphoSubmit").addEventListener("click", () => { if (confirm(st.pages ? x.submitAsk(st.pages) : x.submitEmpty)) submit(); });
  }
  function paint() {
    const x = T[L()], box = document.getElementById("hphoExamMain"); if (!box) return;
    if (st.error && st.error !== st.beeped && ["check", "lobby", "room", "submit"].includes(st.phase)) { st.beeped = st.error; beep(); }
    if (!st.error) st.beeped = null;
    paintBar();
    if (!bridge()) { box.innerHTML = `<section class="hpho-round"><h2>${x.title}</h2><p>${x.appOnly}</p><a class="hpho-btn" href="https://physleague.kr/#/desktop" target="_blank" rel="noopener">${x.appGet}</a></section>`; return; }
    if (st.phase === "lobby") return paintLobby(box);
    if (st.phase === "check") return paintCheck(box);
    if (st.phase === "room") return paintRoom(box);
    if (st.phase === "exam") return paintExam(box);
    if (st.phase === "submit") return paintSubmit(box);
    window.HL_HPHO_PROCTOR?.dock?.(null);
    box.innerHTML = `<section class="hpho-round"><h2>${x.done}</h2><p>${x.doneNote}</p></section>`;
  }

  /* ── the PDF viewer (PDF.js), pages drawn as they scroll near, with tabs and zoom; no download button ── */
  const PDFJS = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/";
  let pdfjs = null;
  const loadPdfjs = () => pdfjs ||= new Promise((ok, fail) => {
    if (window.pdfjsLib) return ok(window.pdfjsLib);
    const s = document.createElement("script"); s.src = PDFJS + "pdf.min.js";
    s.onload = () => { if (!window.pdfjsLib) { pdfjs = null; return fail(Error("pdfjs")); } window.pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS + "pdf.worker.min.js"; ok(window.pdfjsLib); };
    s.onerror = () => { pdfjs = null; fail(Error("pdfjs")); }; document.head.append(s);
  });
  function viewer(files) {
    const x = T[L()], box = document.createElement("div"); box.className = "hpho-pv";
    box.innerHTML = `<div class="hpho-pv-bar">${files.length > 1 ? `<div class="hpho-pv-tabs" role="group">${files.map((f, i) => `<button type="button" aria-pressed="${i === 0}" data-i="${i}">${esc(x.docNames[f.kind])}${f.lang !== st.paperLang ? ` (${f.lang.toUpperCase()})` : ""}</button>`).join("")}</div>` : `<b>${esc(x.docNames[files[0]?.kind] || "")}</b>`}
      <span class="hpho-pv-zoom"><button type="button" data-z="-">−</button><button type="button" data-z="0">${x.zoomFit}</button><button type="button" data-z="+">+</button></span></div><p class="hpho-muted hpho-pv-status"></p><div class="hpho-pv-pages"></div>`;
    const pages = box.querySelector(".hpho-pv-pages"), status = box.querySelector(".hpho-pv-status");
    let doc = null, zoom = 1, token = 0, observer = null, current = null;
    box.addEventListener("contextmenu", e => e.preventDefault());
    async function draw(slot, my) {
      const page = await doc.getPage(Number(slot.dataset.n)); if (my !== token) return;
      const width = Math.max(280, pages.clientWidth - 2) * zoom, base = page.getViewport({ scale: 1 }), scale = width / base.width;
      const ratio = Math.min(Math.max((devicePixelRatio || 1) * 2, 2), 3), vp = page.getViewport({ scale: scale * ratio });
      const c = document.createElement("canvas"); c.width = Math.floor(vp.width); c.height = Math.floor(vp.height); c.style.width = Math.floor(width) + "px";
      await page.render({ canvasContext: c.getContext("2d", { alpha: false }), viewport: vp }).promise; if (my !== token) return;
      slot.style.minHeight = ""; slot.replaceChildren(c);
    }
    function layout() {
      if (!doc) return; const my = ++token; observer?.disconnect(); pages.replaceChildren();
      const width = Math.max(280, pages.clientWidth - 2) * zoom;
      observer = new IntersectionObserver(es => { for (const e of es) if (e.isIntersecting) { observer.unobserve(e.target); draw(e.target, my).catch(() => {}); } }, { rootMargin: "800px 0px" });
      for (let n = 1; n <= doc.numPages; n++) { const s = document.createElement("div"); s.className = "hpho-pv-page"; s.dataset.n = n; s.style.minHeight = Math.round(width * 1.414) + "px"; pages.append(s); observer.observe(s); }
    }
    async function open(f, tries = 0) {
      current = f; status.hidden = false; status.textContent = x.paperLoading; pages.replaceChildren(); doc = null;
      try {
        const lib = await loadPdfjs();
        const url = cmBase() + "/api" + path(`doc?kind=${f.kind}&lang=${f.lang}`);
        doc = await lib.getDocument({ url, httpHeaders: { Authorization: "Bearer " + cmTok() }, isEvalSupported: false, disableRange: true, cMapUrl: PDFJS + "cmaps/", cMapPacked: true, standardFontDataUrl: PDFJS + "standard_fonts/" }).promise;
        if (current !== f) return;
        status.hidden = true; layout();
      } catch (e) {
        status.textContent = x.paperFail;
        if (tries < 5 && box.isConnected) setTimeout(() => current === f && open(f, tries + 1), 4000 * (tries + 1));
      }
    }
    box.querySelectorAll("[data-i]").forEach(b => b.addEventListener("click", () => { box.querySelectorAll("[data-i]").forEach(o => o.setAttribute("aria-pressed", String(o === b))); open(files[+b.dataset.i]); }));
    box.querySelectorAll("[data-z]").forEach(b => b.addEventListener("click", () => { const z = b.dataset.z; zoom = z === "0" ? 1 : Math.max(0.5, Math.min(2.5, zoom + (z === "+" ? 0.25 : -0.25))); layout(); }));
    let rw = 0; new ResizeObserver(() => { const w = pages.clientWidth; if (doc && Math.abs(w - rw) > 40) { rw = w; layout(); } else rw = w; }).observe(pages);
    if (files[0]) open(files[0]);
    return box;
  }

  /* ── the flow ── */
  async function boot() {
    const x = T[L()]; st.error = null; st.phase = "lobby"; paint();
    if (!bridge()) return;
    try { await cmLoadMe(); } catch (e) {}
    if (!(typeof cm === "object" && cm && cm.me)) { st.error = x.login; return paint(); }
    try {
      const d = await cmApi("GET", "/hpho"); sync(d);
      const live = r => (r.tracks || [{ track: "theory", start_at: r.start_at, duration_min: r.duration_min }]).some(k => k.start_at + k.duration_min * 60 + 3600 > nowS());
      st.round = d.rounds.find(r => d.entries?.[r.id] && live(r)) || null;
      st.entry = st.round ? d.entries[st.round.id] : null;
      if (!st.entry) { st.error = x.notReg; return paint(); }
      await loadTracks();
    } catch (e) { st.error = errText(e); }
    paint();
  }
  async function loadTracks() {
    const list = (st.round.tracks || [{ track: "theory" }]).map(k => k.track);
    st.tracks = {};
    for (const k of list) { const s = await cmApi("GET", `/hpho/rounds/${encodeURIComponent(st.round.id)}/exam/${k}/state`); sync(s); st.tracks[k] = s;
      /* recordings left on this computer by an exam that ended (the app was closed before they were settled) */
      if (s.window && nowS() >= s.window.ends && s.session) settleRecordings(k).catch(() => {}); }
  }
  function enter(track) { loadAsr(); st.track = track; st.error = null; st.phase = "check"; st.checks = {}; st.phoneQr = null; st.dinged = new Set(); st.scanDone = 0; st.quick = !!st.tracks[track]?.session; check(); }
  async function check() {
    const x = T[L()];
    st.checks = { net: !st.offline }; st.phase = "check"; paint();
    try {
      const P = window.HL_HPHO_PROCTOR, pr = P ? await P.check({ screen: false }) : {};
      if (!pr.camera || !pr.mic) { st.checks.camera = pr.camera ? undefined : false; st.checks.mic = pr.mic ? undefined : false; st.error = x.camNeed; return paint(); }

      /* Monito-style: the candidate allows the screen, the computer's sound and the program list to be watched;
         nothing goes on without it */
      if (!st.screenAllowed) {
        st.step = { title: x.allowStep[0], text: x.allowStep[1], list: x.allowList, button: x.allowStep[2] }; paint();
        await waitGo(); st.screenAllowed = true; st.step = null;
      }
      Object.assign(pr, await P.shareScreen());
      const displays = typeof bridge().displays === "function" ? bridge().displays() : 0;
      st.checks.screen = !!pr.screen && displays === 1;
      if (!pr.screen) { st.error = x.screenNeed; return paint(); }
      if (displays !== 1) { st.error = x.displaysNeed(displays); return paint(); }
      /* the webcam when the face is seen well, the microphone when the sentence is read (once; a return skips them) */
      if (st.quick) Object.assign(st.checks, { camera: true, mic: true });
      else if (!(await quality(P, ["face", "voice"]))) return;
      st.checks.system = !!pr.system;
      if (!pr.system) { st.error = x.systemNeed; return paint(); }
      /* the face, voice and ear checks: on the first entry; a candidate coming back (already seated) skips them.
         The room scan: every time, a return after a disconnect too */
      if (!st.quick && !(await quality(P, ["ears"]))) return;
      if (!(await phoneCheck())) return;
      const r = await cmApi("POST", path("checkin"), { client: bridge().client, lang: st.paperLang || L() }); sync(r);
      st.session = r.session; st.tracks[st.track].session = r.session; st.tracks[st.track].window = r.window;
      st.paperLang = r.session.paper_lang; st.seq = Math.max(st.seq, r.seq || 0); st.pages = r.session.pages || 0;
      document.body.classList.remove("hpho-checking"); st.step = null;
      await loadDocs();
      /* seated: the window is locked and recorded from here on, the waiting room included */
      watch();
      route();
    } catch (e) { st.error = errText(e); paint(); }
  }
  async function loadDocs() { try { st.docs = (await cmApi("GET", path("docs"))).docs || []; } catch (e) { st.docs = st.docs || []; } }
  /* where the clock says the candidate is: the waiting room, the exam, the submission page */
  function route() {
    const w = W(), t = nowS();
    if (st.session?.submitted_at || t >= w.upload_until) { st.phase = "done"; finish(); return; }
    if (t < w.start_at) { st.phase = "room"; paint(); return; }
    if (t < w.ends) { start(); return; }
    begin("submit");
  }
  /* the checks a program can judge: the face is well seen, the sentence is read, nothing is worn in the ears. A step
     that passed is not repeated on "check again"; each result also goes into the exam log */
  const waitGo = () => new Promise(res => { st.step.go = res; paint(); });
  async function quality(P, which) {
    const x = T[L()]; document.body.classList.add("hpho-checking"); st.passed ||= {};
    if (which.includes("face") && st.passed.face !== true) {
      st.step = { title: x.faceStep[0], text: x.faceStep[1] }; paint();
      const f = await P.faceCheck(); st.checks.camera = f.ok ? true : false;
      if (!f.ok) { st.step = null; st.error = x.face[f.reason] || x.face.none; paint(); return false; }
      st.passed.face = true;
    }
    if (which.includes("face")) st.checks.camera = true;
    if (which.includes("voice") && st.passed.voice !== true) {
      const sentence = (L() === "en" ? "“I will sit HPhO honestly.”" : "“저는 HPhO에 정직하게 응시하겠습니다.”");
      st.step = { title: x.micStep[0], text: x.micStep[1], quote: sentence, button: x.micStep[2], meter: true }; st.checks.voice = undefined;
      await waitGo();
      st.step = { ...st.step, cue: x.micStep[3] }; paint();
      const m = await P.micCheck((v, cue) => { if (cue === "speak") { const c = document.getElementById("hphoCue"); if (c) { c.textContent = x.micStep[4]; c.classList.add("is-now"); } } const el = document.getElementById("hphoMeter"); if (el) el.style.width = Math.round(v * 100) + "%"; });
      let reason = m.ok ? null : m.reason;
      /* the server's model hears the words: always when the level found a sentence, and also when the level was unsure
         (a quiet microphone) but something was heard. Then the model decides; without it the level's verdict stands */
      if (m.wav && (!reason || (["quiet", "short"].includes(reason) && m.top >= 0.004))) {
        st.step = { ...st.step, cue: x.micStep[5], meter: false }; paint();
        const heard = await hearLocally(m.wav, L());
        if (heard?.zone === "fail") reason = "not_said";
        else try {
          const r = await sendForm("voicecheck", { audio: m.wav, lang: L(), ...(heard?.zone === "pass" ? { local: "said", heard: heard.text } : {}) });
          reason = r.unavailable ? (reason || retry("voice")) : r.said ? null : "not_said"; }
        catch (e) { reason = reason || "failed"; }
      }
      st.checks.mic = reason ? false : true;
      if (reason) { st.step = null; st.error = reason === "unavailable" ? x.unavailable : x.mic[reason] || x.mic.short; paint(); return false; }
      st.passed.voice = true;
    }
    if (which.includes("voice")) st.checks.mic = true;
    if (which.includes("ears") && st.passed.ears !== true) {
      st.step = { title: x.earStep[0], text: x.earStep[1], button: x.earStep[2] }; st.checks.ears = undefined;
      await waitGo();
      let earStep = null;
      /* each sub-step shown live: face seen, hands up 0/2, how long held, how far the head is turned */
      const shots = await P.earShots((name, info) => {
        if (name !== earStep) { if (earStep && !["stop", "done"].includes(name)) ding(); earStep = name; st.step = { title: x.earStep[0], text: x.ear[name], cue: " ", meter: name !== "done" && name !== "stop" }; paint(); }
        if (!info) return;
        const c = document.getElementById("hphoCue"), m = document.getElementById("hphoMeter");
        if (c) c.textContent = name === "front" ? x.earLive.front(info) : x.earLive.turn(info);
        if (m) m.style.width = Math.round((name === "front" ? info.hold : Math.min(info.turn, 1) * 0.5 + info.hold * 0.5) * 100) + "%";
      });
      let r = null;
      if (shots?.error) { st.step = null; st.checks.ears = false; st.error = x.ear[shots.error]; paint(); return false; }
      if (shots) try { r = await sendForm("earcheck", shots); } catch (e) { r = null; }
      if (r?.verdict === "device" && r.ears?.length === 1) r.verdict = r.ears[0] === 1 ? "device_first" : "device_second";
      /* a device: always stop. Unclear photos or no answer from the model: try again; after three tries the exam is not
         held up, and the seat is flagged for a person to look at the photos */
      /* glasses that might be smart: taken off and shown up close, front then the inside of the temples (3 s each) */
      if (r?.verdict === "glasses_check") {
        const shoot = async (text) => { for (let n = 3; n > 0; n--) { st.step = { title: x.glassStep, text, count: n, view: " " }; paint(); await new Promise(res => setTimeout(res, 1000)); } return P.closeUp(); };
        const front = await shoot(x.glassFront), inside = await shoot(x.glassInside);
        let g = null; try { g = await sendForm("glasscheck", { front, inside }); } catch (e) {}
        r = !g ? null : g.unavailable ? { unavailable: true } : { verdict: g.smart ? "glasses" : g.clear ? "clear" : "glasses_unclear" };
      }
      const why = !r ? "failed" : r.unavailable ? retry("ears") : ["device", "device_first", "device_second", "cap", "watch", "glasses", "wrists", "covered", "glasses_unclear"].includes(r.verdict) ? r.verdict : r.verdict === "unclear" && (st.tries.ears_unclear = (st.tries.ears_unclear || 0) + 1) < 3 ? "unclear" : null;
      st.checks.ears = !why;
      if (why) { st.step = null; st.error = why === "unavailable" ? x.unavailable : x.ear[why]; paint(); return false; }
      st.passed.ears = true;
    }
    if (which.includes("ears")) st.checks.ears = true;
    return true;
  }
  /* the sentence heard on this computer first (Whisper, transformers.js; evaluated with recorded voices, clean and noisy:
     whisper-base decided 20 of 24 here and was never wrong, the other 4 went to the server). The core of the sentence is
     matched anywhere in the transcript, so what "HPhO" becomes does not matter. Clearly said: no server model call;
     clearly not: "read the sentence"; in between, or the model could not load: the server's model listens */
  const ASR = { lib: "https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.8.1/dist/transformers.min.js", model: "onnx-community/whisper-base" };
  const CORE = { ko: "정직하게응시하겠습니다", en: "willsithphohonestly" };
  let asr = null;
  function loadAsr() {
    return asr ||= (async () => { const { pipeline, env } = await import(ASR.lib); env.allowLocalModels = false;
      return pipeline("automatic-speech-recognition", ASR.model, { dtype: "q8", device: "wasm" }); })().catch(() => { asr = null; return null; });
  }
  const normText = (s, lang) => s.toLowerCase().normalize("NFC").replace(/[\s.,!?'"“”‘’·~\-]/g, "");
  function similar(a, b) {
    const m = a.length, n = b.length; if (!m || !n) return 0;
    let prev = Array.from({ length: n + 1 }, (_, j) => j);
    for (let i = 1; i <= m; i++) { const cur = [i]; for (let j = 1; j <= n; j++) cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1)); prev = cur; }
    return 1 - prev[n] / Math.max(m, n);
  }
  function coreScore(text, lang) {
    const t = normText(text, lang), c = CORE[lang]; let best = 0;
    for (let len = Math.max(1, c.length - 3); len <= c.length + 3; len++) for (let i = 0; i + len <= t.length; i++) best = Math.max(best, similar(t.slice(i, i + len), c));
    return best * (lang === "ko" ? (t.startsWith("저는") ? 1 : 0.85) : 1);
  }
  /* our own 16 kHz WAV back to samples */
  async function wavSamples(blob) { const v = new DataView(await blob.arrayBuffer()), n = (v.byteLength - 44) >> 1, out = new Float32Array(n); for (let i = 0; i < n; i++) out[i] = v.getInt16(44 + i * 2, true) / 32768; return out; }
  async function hearLocally(wav, lang) {
    const model = await Promise.race([loadAsr(), new Promise(r => setTimeout(() => r(null), 20000))]);
    if (!model) return null;
    try { const r = await model(await wavSamples(wav), { language: lang === "en" ? "english" : "korean", task: "transcribe", max_new_tokens: 48 });
      const score = coreScore(r.text || "", lang);
      return { text: (r.text || "").trim().slice(0, 100), zone: score >= 0.7 ? "pass" : score < 0.45 ? "fail" : "unsure" }; }
    catch (e) { return null; }
  }
  /* "ding-dong" when a check is confirmed (Monito-style): two soft tones, made here (no sound file) */
  /* and "beep-beep" when a check finds a problem or something fails (the AI did not recognise it, no answer, an error) */
  let audio = null;
  function tones(list) {
    try { audio ||= new AudioContext(); audio.resume?.(); const t0 = audio.currentTime;
      for (const [f, at, len, vol] of list) { const o = audio.createOscillator(), g = audio.createGain(); o.type = "sine"; o.frequency.value = f;
        g.gain.setValueAtTime(0.0001, t0 + at); g.gain.exponentialRampToValueAtTime(vol, t0 + at + 0.015); g.gain.exponentialRampToValueAtTime(0.0001, t0 + at + len);
        o.connect(g).connect(audio.destination); o.start(t0 + at); o.stop(t0 + at + len + 0.05); } } catch (e) {}
  }
  const ding = () => tones([[1046.5, 0, 0.45, 0.25], [784, 0.18, 0.5, 0.25]]);
  const beep = () => tones([[1568, 0, 0.09, 0.2], [1568, 0.14, 0.09, 0.2]]);

  /* a check the server's model could not answer: "unavailable" for the first three tries, then let through (flagged) */
  function retry(what) { st.tries[what] = (st.tries[what] || 0) + 1; return st.tries[what] < 3 ? "unavailable" : null; }
  /* the phone (hpho-phone.js): paired by a QR, it scans the room view by view (the model judges each), then stands where
     it sees the candidate. A return after a disconnect scans again. The page waits until the phone reports all of it */
  const qrSvg = async url => {
    if (typeof window.qrcode !== "function") await new Promise((res, rej) => { const sc = document.createElement("script"); sc.src = "vendor/qrcode/qrcode.js"; sc.onload = res; sc.onerror = rej; document.head.append(sc); });
    const q = window.qrcode(0, "M"); q.addData(url); q.make(); return q.createSvgTag({ cellSize: 4, margin: 2, scalable: true });
  };
  const phoneUrl = code => (window.HL_HPHO_PHONE_BASE || location.origin + location.pathname.replace(/[^/]*$/, "")).replace(/\/?$/, "/") + `?lang=${L()}#/hpho/phone/${code}`;
  async function pairPhone(rescan) { const r = await cmApi("POST", path("phone"), { rescan: !!rescan }); st.phoneCode = r.code; return qrSvg(phoneUrl(r.code)); }
  /* until "online": the QR, until the phone has opened it; until "done": the room scan and the placement as well.
     One QR for both (a new code would cut off the phone that is already connected) */
  async function phoneCheck() {
    const x = T[L()];
    if (!st.phoneQr) { st.checks.phone = st.checks.room = st.checks.place = undefined; st.phoneQr = await pairPhone(st.quick); }
    st.step = { title: x.phoneStep[0], text: x.phoneStep[1], qr: st.phoneQr }; paint();
    let shown = -1;
    for (;;) {
      if (st.phase !== "check") return false;
      let ph = null; try { ph = (await cmApi("GET", path("phone"))).phone; } catch (e) {}
      const done = ph ? Object.values(ph.scan || {}).filter(v => ["clear", "notes", "unverified"].includes(v.status)).length : 0;
      st.checks.room = ph?.scanned || undefined; st.checks.place = !!(ph?.placed || ph?.scanned && ph.place_note === "model unavailable") || undefined;
      /* done only when the phone is connected, has scanned the room and stands in place */
      st.checks.phone = !!(ph?.online && st.checks.place) || undefined;
      const list = document.getElementById("hphoPhoneList");
      if (list) list.innerHTML = `<li class="${ph?.online ? "is-ok" : ""}">${x.phoneList.online}${ph?.online ? "" : ` — ${x.phoneList.waiting}`}</li><li class="${ph?.scanned ? "is-ok" : ""}">${x.phoneList.scan(done, 4)}</li><li class="${st.checks.place ? "is-ok" : ""}">${x.phoneList.placed}</li>`;
      const key = [st.checks.phone, st.checks.room, st.checks.place, done].join();
      if (key !== shown) { if (shown !== -1 && done > (st.scanDone || 0)) ding(); st.scanDone = done; shown = key; paint(); }
      if (st.checks.phone && st.checks.room) { st.step = null; return true; }
      await new Promise(r => setTimeout(r, 2000));
    }
  }
  /* during the exam: the phone's heartbeat every 20 s; while it is lost, a banner with a new QR */
  async function watchPhone() {
    if (!["room", "exam", "submit"].includes(st.phase)) return;
    let ph = null; try { ph = (await cmApi("GET", path("phone"))).phone; } catch (e) { return; }
    const was = st.phoneOnline !== false; st.phoneOnline = !!ph?.online;
    if (was && !st.phoneOnline) push("phone_lost");
    if (!was && st.phoneOnline) push("phone_back");
    let el = document.getElementById("hphoPhoneBanner");
    if (st.phoneOnline) el?.remove();
    else if (!el) { el = Object.assign(document.createElement("div"), { id: "hphoPhoneBanner", className: "hpho-phone-banner" }); el.innerHTML = `${await pairPhone(false).catch(() => "")}<p>${T[L()].phoneLost}</p>`; document.body.append(el); }
    paintBar();
  }
  /* the recordings stay on this computer (IndexedDB, in the app's own storage) during the exam; at the end the server
     says whether the seat was flagged: then they go up, else they are deleted here */
  const REC_DB = "hpho-recordings";
  const idb = () => new Promise((res, rej) => { const o = indexedDB.open(REC_DB, 1); o.onupgradeneeded = () => o.result.createObjectStore("seg", { keyPath: "id", autoIncrement: true }).createIndex("seat", "seat"); o.onsuccess = () => res(o.result); o.onerror = () => rej(o.error); });
  const seatKey = (track = st.track) => `${st.round.id}|${track}`;
  async function storeClip(blob, source) {
    if (!blob || !st.round) return;
    try { const db = await idb(); await new Promise((res, rej) => { const tx = db.transaction("seg", "readwrite"); tx.objectStore("seg").add({ seat: seatKey(), source, at: nowS(), blob }); tx.oncomplete = res; tx.onerror = () => rej(tx.error); }); db.close(); }
    catch (e) { push("recording_failed", "kept on this computer: " + (e?.name || "storage")); }
  }
  async function segments(track) {
    const db = await idb();
    const list = await new Promise((res, rej) => { const q = db.transaction("seg").objectStore("seg").index("seat").getAll(seatKey(track)); q.onsuccess = () => res(q.result); q.onerror = () => rej(q.error); });
    return { db, list };
  }
  /* the end: ask the server (keep), then upload or delete the recordings kept here */
  async function settleRecordings(track = st.track) {
    let keep = false; try { keep = (await cmApi("POST", path("keep", track), {})).keep; } catch (e) { return; }
    let db, list; try { ({ db, list } = await segments(track)); } catch (e) { return; }
    for (const [i, seg] of list.entries()) {
      if (keep) {
        const box = document.getElementById("hphoExamMain"); if (box) box.innerHTML = `<section class="hpho-round"><p>${T[L()].saving(i + 1, list.length)}</p></section>`;
        let sent = false;
        for (let a = 0; a < 3 && !sent; a++) try { const fd = new FormData(); fd.set("clip", seg.blob, "clip.webm"); fd.set("source", seg.source);
          const r = await fetch(cmBase() + "/api" + path("clip", track), { method: "POST", headers: { Authorization: "Bearer " + cmTok() }, body: fd }); sent = r.ok || r.status === 403 || r.status === 409; } catch (e) { await new Promise(r => setTimeout(r, 3000)); }
        if (!sent) continue;                                   /* kept here, sent on the next opening */
      }
      await new Promise(res => { const tx = db.transaction("seg", "readwrite"); tx.objectStore("seg").delete(seg.id); tx.oncomplete = res; tx.onerror = res; });
    }
    db.close();
  }
  /* a monitor connected during the exam: the page is covered (the paper cannot be seen on it) until it is unplugged */
  function cover(on) {
    let el = document.getElementById("hphoCover");
    if (!on) { el?.remove(); return; }
    if (el) return;
    const x = T[L()];
    el = Object.assign(document.createElement("div"), { id: "hphoCover", className: "hpho-cover" });
    el.innerHTML = `<div><h2>${x.coverTitle}</h2><p>${x.coverText}</p></div>`;
    document.body.append(el);
  }
  /* proctoring on (once): the window's events, the camera and the screen */
  function watch() {
    const b = bridge();
    if (!st.unsub) st.unsub = b.onEvent(e => {
      if (!e || typeof e.kind !== "string") return;
      push(e.kind, e.detail);
      if (["focus_lost", "display_change", "screen_unlocked"].includes(e.kind) || e.kind === "process_new" && /(^| )!/.test(e.detail || "")) window.HL_HPHO_PROCTOR?.snap(e.kind);
      if (e.kind === "display_change") cover(parseInt(e.detail, 10) > 1);
    });
    if (!st.watching) { st.watching = true; window.HL_HPHO_PROCTOR?.start({ onEvent: (kind, detail) => push(kind, detail), upload: uploadSnap, clip: storeClip }); }
    clearInterval(st.phoneTimer); st.phoneTimer = setInterval(watchPhone, 20000);
    push("displays", String(typeof b.displays === "function" ? b.displays() : "?"));
    b.started?.();
    clearInterval(st.flushTimer); st.flushTimer = setInterval(flush, 10000);
  }
  async function start() {
    const b = bridge(); st.error = null;
    if (!st.watching) watch();
    try {
      const r = await cmApi("POST", path("start"), { client: b.client }); sync(r);
      st.seq = Math.max(st.seq, r.seq || 0); st.paperLang = r.paper_lang || st.paperLang;
      await loadDocs();
      st.phase = "exam"; watch();
      push("window_ready", r.resumed ? "resumed" : "started");
      flush(); paint();
    } catch (e) { st.error = errText(e); if (e?.code === "exam_over") return begin("submit"); paint(); }
  }
  /* the time is over: the paper goes, the recording goes on (faster, marked after_time), the answers go up */
  function begin(phase) {
    st.phase = phase; watch();
    push("time_over", st.track);
    window.HL_HPHO_PROCTOR?.pace?.(10, 20, "after_time");   /* two images a time: under the server's 120 per 10 min */
    flush(); paint();
  }
  function uploadSnap(blob, source, reason) { sendForm("snap", { image: blob, source, reason }).catch(() => {}); }
  /* a page: through HaslaLab's own scan encoder (sim/labscan/scanner.js: the 200 dpi floor, then JPEG quality steps),
     else at most 2400 px on its longest side; JPEG under the server's 4 MB */
  let scanner = null;
  async function shrink(file) {
    try {
      scanner ||= await import("./sim/labscan/scanner.js");
      const b = await scanner.encodeUpload(file, { maxBytes: 3.8e6, recompress: true });
      if (b && b.type === "image/jpeg" && b.size < 3.8e6) return b;
    } catch (e) {}
    return shrinkPlain(file);
  }
  async function shrinkPlain(file) {
    const img = await createImageBitmap(file), k = Math.min(1, 2400 / Math.max(img.width, img.height));
    const c = document.createElement("canvas"); c.width = Math.round(img.width * k); c.height = Math.round(img.height * k); c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
    for (const q of [0.88, 0.75, 0.6]) { const b = await new Promise(res => c.toBlob(res, "image/jpeg", q)); if (b && b.size < 3.8e6) return b; }
    return null;
  }
  async function addPages(files) {
    const x = T[L()], msg = () => document.getElementById("hphoUpMsg");
    for (const f of files) {
      if (msg()) msg().textContent = x.uploading;
      try {
        const b = await shrink(f); if (!b) throw { code: "upload_too_large" };
        const page = st.pages + 1;
        await sendForm("answer", { image: b, page: String(page) });
        st.pages = page; push("answer_page", String(page));
        (st.thumbs ||= []).push(URL.createObjectURL(b)); st.error = null;
      } catch (e) { st.error = e?.code ? errText(e) : x.uploadFail; break; }
    }
    paint();
  }
  async function submit() {
    try { await cmApi("POST", path("submit"), {}); } catch (e) { if (e?.code !== "upload_closed") { st.error = errText(e); return paint(); } }
    st.phase = "done"; finish();
  }
  async function finish() {
    clearInterval(st.flushTimer);
    push("submitted", String(st.pages)); await flush().catch(() => {});
    clearInterval(st.phoneTimer); document.getElementById("hphoPhoneBanner")?.remove();
    await window.HL_HPHO_PROCTOR?.stop(); st.watching = false;
    await settleRecordings().catch(() => {});
    for (const u of st.thumbs || []) URL.revokeObjectURL(u); st.thumbs = [];
    bridge()?.finished?.(); paint();
  }
  /* the server's clock and the exam's times again (every 30 s in the entrance and the waiting room; the exam and the
     submission page sync with every heartbeat): a clock that drifted, or a time the organisers moved, is followed */
  async function resync() {
    if (!st.round || st.resyncing) return; st.resyncing = true;
    try {
      for (const k of Object.keys(st.tracks)) { const s = await cmApi("GET", path("state", k)); sync(s); st.tracks[k] = { ...st.tracks[k], window: s.window, session: s.session || st.tracks[k].session }; }
      if (st.phase === "lobby") paint();
    } catch (e) {} finally { st.resyncing = false; }
  }
  /* the network's delay: one light request every 10 s (the exam's heartbeat is timed too) */
  async function ping() {
    const t0 = performance.now();
    try { const r = await fetch(cmBase() + "/api/health", { cache: "no-store" }); if (!r.ok && r.status >= 500) throw 0; st.offline = false; st.rtt = Math.round(performance.now() - t0); }
    catch (e) { const was = st.offline; st.offline = true; if (!was) beep(); }
    paintBar();
  }
  function tick() {
    if (!document.getElementById("hphoExamMain")) return clearInterval(st.timer);
    if (++st.ticks % 10 === 5) ping();
    if (["lobby", "room"].includes(st.phase) && st.ticks % 30 === 0) resync();
    const w = W(), t = nowS();
    if (st.phase === "lobby") { if (st.round) document.querySelectorAll("[data-enter]").forEach(b => { const s = trackState(b.dataset.enter); b.disabled = !s.can; b.textContent = s.label; }); return; }
    if (!w) return;
    if (st.phase === "room") { const c = document.getElementById("hphoCountdown"); if (c) c.textContent = fmt(w.start_at - t); if (t >= w.start_at && !st.starting) { st.starting = true; start().finally(() => { st.starting = false; }); } return; }
    if (st.phase === "exam" && t >= w.ends) return begin("submit");
    if (st.phase === "submit" && t >= w.upload_until) { st.phase = "done"; finish(); return; }
    paintBar();
  }
  function mount() {
    clearInterval(st.timer); clearInterval(st.flushTimer);
    st = { ...st, phase: "lobby", session: null, error: null, queue: [], step: null, tries: {}, track: null, docs: [], pages: 0, thumbs: [], ticks: 0 };
    if (!st.wired) { st.wired = true;
      document.addEventListener("visibilitychange", () => { if (["room", "exam", "submit"].includes(st.phase)) push(document.hidden ? "page_hidden" : "page_visible"); });
      addEventListener("offline", () => { if (["room", "exam", "submit"].includes(st.phase)) push("network_lost"); });
      addEventListener("online", () => { if (["room", "exam", "submit"].includes(st.phase)) { push("network_back"); flush(); } }); }
    boot();
    if (bridge()) loadAsr();
    st.timer = setInterval(tick, 1000);
  }
  window.HL_HPHO_EXAM = { view, mount, resync };
})();
