# HaslaLab 커뮤니티 서버

haslalab.org의 `#/community` 화면이 쓰는 API입니다. GitHub를 쓰지 않고 **Cloudflare Workers**(서버)와 **D1**(SQLite 데이터베이스) 위에서 돌아갑니다. 무료 요금제 한도 안에서 충분히 운영할 수 있습니다.

- 회원가입과 로그인을 지원합니다. 비밀번호는 PBKDF2-SHA256(100,000회)과 솔트로 해시해서 저장합니다.
- 로그인 토큰은 Authorization 헤더로 보냅니다. 서버에는 토큰의 SHA-256 값만 저장하고, 토큰은 30일 동안 유효합니다.
- 게시판은 자유게시판, 질문 · 답변, 시뮬레이터 제보, 스터디 · 자료 네 개입니다.
- 글과 댓글을 쓰고, 고치고, 지울 수 있고 좋아요, 검색, 신고 기능이 있습니다.
- 가입, 로그인, 글쓰기, 댓글, 신고에는 요청 횟수 제한을 둡니다.
- 계정은 삭제할 수 있습니다. 삭제하면 글은 남고 이름만 "탈퇴한 사용자"로 바뀝니다.

## 대시보드에서 배포하기 (명령줄 없이)

D1 데이터베이스 `haslalab-community`(id `96761b6d-c194-4ee5-9836-7845b51a5f07`)는 이미 만들었고, 표도 모두 들어 있습니다. Worker만 올리면 됩니다.

1. Cloudflare 대시보드 → **Workers & Pages** → **Create** → **Create Worker**로 가서 이름을 `haslalab-community`로 정하고 **Deploy**를 누릅니다.
2. **Edit code**를 눌러 기존 코드를 지우고 이 폴더의 `src/index.js` 내용을 그대로 붙여 넣은 뒤 **Deploy**를 누릅니다.
3. **Settings → Bindings → Add → D1 database**에서 변수 이름은 `DB`, 데이터베이스는 `haslalab-community`를 고릅니다.
4. **Settings → Variables and Secrets → Add**에서 이름은 `ALLOWED_ORIGINS`, 값은 아래로 넣습니다.
   `https://haslalab.org,https://www.haslalab.org,https://haslaedu.github.io`
5. **Settings → Domains & Routes**에서 workers.dev를 켜고, 그 주소를 `index.html`의 `COMMUNITY_API`에 넣습니다. (지금: `https://haslalab-community.haslalab.workers.dev`)

## v2로 올리기 (말머리 · 추천/비추천 · 답글 · 정렬 · 개념글)

`migrations/0002_v2.sql`은 이미 원격 D1에 적용해 두었습니다. 대시보드에서 **haslalab-community → Edit code**로 들어가 `src/index.js`의 새 내용을 다시 붙여 넣고 **Deploy**만 누르면 됩니다. 사이트는 서버 버전(`/api/health`의 `v`)을 보고 v1이면 비추천 버튼을 숨기는 식으로 알아서 맞춥니다.

## v3: 한국어 서버와 영어 서버 (계정은 공유)

글마다 `lang`(`ko`/`en`)이 붙고, 목록·게시판 통계·인기글은 사이트 언어의 서버 것만 보여 줍니다. `migrations/0003_lang.sql`은 원격 D1에 적용해 두었습니다(기존 글은 모두 한국어 서버). `src/index.js`를 다시 붙여 넣고 Deploy하면 됩니다.

## v4: 사이트 로그인 · 주간 문제 · 채점 · 랭킹

커뮤니티 계정이 그대로 사이트 계정이 됩니다. 사이트 오른쪽 위에 로그인 버튼이 생기고, 「주간 문제」(`#/weekly`), 랭킹(`#/rank`), 내 기록(`#/me`) 화면이 열립니다.

- **단답형** 문제는 서버가 숫자를 정답과 비교해 바로 채점합니다(허용 오차는 문제마다 `rel` 또는 `abs`). AI 키가 없어도 동작합니다.
- **서술형** 문제는 하슬라논술 채점기(`grade-v2`)와 같은 방식으로 채점합니다. 문제의 채점 기준(루브릭)마다 점수를 매기고, 학생 답안에서 그대로 인용한 근거를 붙입니다. 답안에 없는 근거로 준 점수는 0점으로 바꿉니다. Gemini 키가 있으면 Gemini를, 없고 OpenAI 키가 있으면 OpenAI를 씁니다. 둘 다 없으면 답안은 「채점 대기」로 저장되고, 관리자가 `#/weekly/admin`에서 점수를 줍니다.
- **사진 답안**은 하슬라논술처럼 Upstage OCR로 읽습니다. 수식이 많으면 Document Parse로 LaTeX를 살려 읽습니다. 읽은 글은 학생이 확인하고 고친 뒤에 제출합니다. 이미지는 JPEG·PNG·WebP 한 장, 8 MB까지 받고, 한 사람이 하루 30번까지 쓸 수 있습니다.
- **랭킹**은 문제마다 가장 높은 점수를 더해 매깁니다. 같은 점수면 그 점수에 먼저 닿은 사람이 앞섭니다. 주가 열려 있는 동안 낸 답만 셉니다. 주가 끝나면 풀이가 공개되므로, 그 뒤에 낸 답은 연습으로만 채점합니다. 티어는 총점 기준으로 브론즈(0), 실버(300), 골드(800), 플래티넘(1600), 다이아몬드(3000), 루비(5000)입니다.
- 새 주는 월요일 0시(한국 시각)에 열립니다. 문제는 관리자 화면에서 추가합니다(`week`, `opens_at`/`closes_at`은 유닉스 초).

### 올리는 순서

1. **표 만들기**: `migrations/0004_arena.sql`을 원격 D1에 적용합니다. `npm run db:remote`를 실행하거나, 대시보드에서 **D1 → haslalab-community → Console**에 파일 내용을 붙여 넣고 실행합니다. 첫 주(2026-W44) 문제 세 개가 함께 들어갑니다.
2. **코드 올리기**: `src/index.js`를 대시보드에 다시 붙여 넣고 **Deploy**를 누릅니다. `/api/health`가 `v: 4`를 돌려주면 사이트가 새 화면을 엽니다.
3. **키 넣기**: **Settings → Variables and Secrets**에서 *Secret*으로 넣습니다. 키는 서버에만 있고 사이트에는 들어가지 않습니다.
   - `UPSTAGE_API_KEY`: 사진 읽기(OCR)
   - `GEMINI_API_KEY`: 서술형 채점. 모델은 `GEMINI_MODEL`로 바꿀 수 있고, 기본값은 `gemini-flash-latest`입니다.
   - 또는 `OPENAI_API_KEY`: 모델은 `OPENAI_MODEL`로 정하고, 기본값은 `gpt-5.4`입니다.
4. **관리자 지정**: 아래 「관리」의 명령으로 관리자를 정하면 `#/weekly/admin`이 열립니다.

로컬 시험: `.dev.vars`에 키 대신 시험용 값과 `GEMINI_BASE`·`UPSTAGE_BASE`(가짜 서버 주소)를 넣고 `node test-arena.mjs`를 실행합니다.

## v5: Google · 카카오 · 네이버 · GitHub · Discord로 가입/로그인

로그인·회원가입 화면 맨 위에 외부 로그인 버튼이 생깁니다. 한국어 화면에는 Google · 카카오 · 네이버, 영어 화면에는 Google · GitHub · Discord가 보입니다(`arena.js`의 `OAUTH_BY_LANG`). 처음 들어오면 그 계정의 표시 이름을 닉네임으로 삼아 HaslaLab 계정이 만들어지고, 다음부터는 같은 계정으로 들어옵니다. 이메일은 받지도 저장하지도 않고, 각 서비스의 고유 번호만 `identities` 표에 둡니다. 「내 기록」(`#/me`)에서 닉네임을 바꾸고, 다른 서비스를 같은 계정에 연결하고, 아이디 로그인용 비밀번호를 만들 수 있습니다.

로그인이 끝나면 서버는 1분짜리 일회용 코드만 붙여 사이트로 돌려보내고, 사이트가 그 코드를 세션 토큰으로 바꿉니다. 토큰이 주소창이나 방문 기록에 남지 않습니다. 돌아갈 주소는 `ALLOWED_ORIGINS`에 있는 사이트만 허용합니다.

### 올리는 순서

1. `migrations/0005_oauth.sql`을 원격 D1에 적용합니다. 방법은 v4와 같습니다(Console에 붙여 넣기 또는 `npm run db:remote`).
2. `src/index.js`를 다시 붙여 넣고 Deploy 합니다. `/api/health`가 `v: 5`와 `oauth: [...]`를 돌려줍니다.
3. 각 서비스에 앱을 등록하고, 리디렉션 주소를 아래처럼 넣습니다. 받은 값은 Worker의 *Secret*으로 넣습니다.

| 서비스 | 앱 만드는 곳 | 리디렉션(콜백) 주소 | Secret 이름 |
|---|---|---|---|
| Google | Google Cloud Console → API 및 서비스 → 사용자 인증 정보 → OAuth 클라이언트 ID(웹 애플리케이션). 동의 화면 범위는 `openid`, `profile` | `https://haslalab-community.haslalab.workers.dev/api/oauth/google/callback` | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` |
| Discord | discord.com/developers/applications → OAuth2 | `https://haslalab-community.haslalab.workers.dev/api/oauth/discord/callback` | `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET` |
| 네이버 | developers.naver.com → 애플리케이션 등록 → 네이버 로그인(별명 또는 이름 제공 항목만 선택). PC 웹 서비스 URL은 `https://haslalab.org` | `https://haslalab-community.haslalab.workers.dev/api/oauth/naver/callback` | `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` |
| GitHub | github.com/settings/developers → OAuth Apps → New OAuth App. Homepage URL은 `https://haslalab.org` | `https://haslalab-community.haslalab.workers.dev/api/oauth/github/callback` | `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` |
| 카카오 | developers.kakao.com → 내 애플리케이션 → 앱 추가. 카카오 로그인 활성화, 동의항목에서 닉네임(`profile_nickname`) 설정, 보안에서 Client Secret 생성·사용함 | `https://haslalab-community.haslalab.workers.dev/api/oauth/kakao/callback` | `KAKAO_CLIENT_ID`(REST API 키), `KAKAO_CLIENT_SECRET` |

키를 넣은 서비스만 버튼이 켜지고, 넣지 않은 서비스는 흐리게 「관리자가 아직 연결하지 않았습니다」로 보입니다. 로컬 시험에서는 `.dev.vars`의 `OAUTH_MOCK_BASE`로 가짜 로그인 서버를 가리킵니다.

## v6: 프로필 사진 · 백준(solved.ac)식 난이도와 레이팅 · 빨라진 응답

- **프로필 사진**: 「내 기록」이나 계정 설정에서 사진을 고르면, 브라우저가 정사각형으로 잘라 256px로 줄여(60KB 이하) `PUT /api/me/avatar`로 올립니다. 사진은 D1의 `avatars` 표에 무작위 키로 저장되고 `GET /api/avatar/<키>`로 1년 캐시되어 나갑니다. 주소에 계정 번호가 드러나지 않고, 새로 올리면 키가 바뀝니다.
- **난이도**: 문제의 `level`은 1–30입니다(브론즈 V = 1 … 브론즈 I = 5, 실버 V = 6 … 루비 I = 30). 예전 별 1–5개는 마이그레이션에서 각 티어의 가운데(3, 8, 13, 18, 23)로 바뀝니다.
- **레이팅과 티어**: 푼 문제(단답은 정답, 서술형은 80% 이상) 중 어려운 100문제의 난이도 점수 합에 푼 문제 수 보너스를 더한 값이 레이팅이고, 레이팅으로 브론즈 V … 루비 I, 마스터 티어가 정해집니다. 주간 랭킹은 그대로 그 주의 점수 합, 전체 랭킹은 레이팅 순입니다. 지난 주 문제를 풀어도 레이팅에 들어갑니다.
- **속도**: `wrangler.toml`의 `[placement] mode = "smart"`가 Worker를 데이터베이스 가까이에서 돌립니다(대시보드에서 붙여 넣어 배포한다면 Settings → Runtime → Placement를 Smart로). 주간 문제 화면은 요청 하나로 그 주 상위권까지 받고, 서버 쪽 질의는 한꺼번에 보냅니다. `/api/health`는 브라우저가 5분 동안 캐시합니다.

### 올리는 순서

1. `migrations/0006_avatar_levels.sql`을 원격 D1에 적용합니다.
2. `src/index.js`(와 `wrangler.toml`)로 Worker를 다시 배포합니다. `npx wrangler deploy`
3. 사이트(`index.html`, `arena.js`)는 GitHub Pages가 알아서 올립니다.

## v7: 시뮬레이터 속 태블릿·노트북의 YouTube 검색

시뮬레이터의 태블릿·휴대폰·노트북에서 YouTube를 검색하면 이 Worker의 `/api/yt/search`가 YouTube Data API v3로 실제 결과를 가져옵니다(퍼가기가 허용된 동영상만). 키가 없으면 503(`yt_off`)을 돌려주고, 기기 안의 YouTube는 미리 고른 동영상 목록에서만 찾습니다.

1. Google Cloud 콘솔에서 프로젝트를 만들고 **YouTube Data API v3**를 사용 설정한 뒤 API 키를 만듭니다. 키 제한은 "API 제한 → YouTube Data API v3"로 걸어 두세요.
2. 키를 Worker 비밀값으로 넣습니다(채팅이나 저장소에는 붙여 넣지 마세요): `npx wrangler secret put YT_API_KEY`
3. `npx wrangler deploy`

무료 할당량은 하루 10,000 단위이고 검색 한 번이 101 단위입니다. 같은 검색어는 하루 동안 엣지 캐시에서 답하고, 방문자(IP)마다 한 시간에 30번으로 제한합니다.

## v8: 실전 모드 (5시간 실험 + 30분 답안 스캔 · 실전 토큰)

대회 화면(`#/ipho`) 위쪽에서 「연습 모드 | 실전 모드」를 고릅니다. 연습 모드는 지금까지처럼 연도 → 실험 카드 → 시뮬레이터이고, 실전 모드(`#/ipho/exam`)는 대학 모의논술 응시 사이트처럼 **시험 목록**(연도별 시험, 응시 인원 · 평균, 내 상태, 응시하기 · 이어하기 · 성적표 · 다시 응시)과 **응시자 정보**(보유 토큰, 진행 중인 시험)를 보여 줍니다. 응시하기를 누르면 `sim/exam.html`이 **수험 안내**(시험 정보 표 · 유의사항 · 응시 동의 세 줄을 모두 체크해야 시작)를 보여 주고, 시험 중에는 위쪽에 **수험번호**(`HL-IPHO2024-000123`)와 응시자가, 제출 뒤에는 **답안 제출 확인증**(인쇄 가능)이 나오며, `#/lab/<번호>`는 **성적표**(총점 · 백분율 · 순위 · 상위 % · 응시자 평균 · 최고, 실험별 · 기준별 점수와 근거)입니다. 순위와 평균은 사람마다 **첫 응시**만 셉니다(`GET /api/lab/stats`). 실전 모드는 그 해의 E1·E2를 **한 책상**에 나란히 놓고 5시간 동안 칩니다. 같은 해라도 따로 치는 라운드(IOAA D1, D2 등)는 서로 다른 시험입니다.

- **한 부품함**: 시뮬레이터마다 있던 부품함을 왼쪽의 공용 부품함 하나로 모읍니다. 공용 부품함을 누르면 그 클릭이 해당 시뮬레이터의 부품함으로 그대로 전달되어 손에 들리고, 그 실험의 책상에 놓습니다. 장치가 이미 책상에 놓여 있는 시뮬레이터는 그대로 두고 책상 폭 제한만 풉니다. 실전 모드에서는 시뮬레이터의 광고 자리도 비웁니다.
- **로그인 + 실전 토큰**: 로그인한 사람만 칠 수 있고, 시작할 때 토큰 1개를 씁니다. 잔액은 서버의 `users.exam_tokens`에 있고, 바뀔 때마다 `lab_ledger`에 기록됩니다. 가입하면 5개가 들어 있고(마이그레이션의 기본값 `DEFAULT 5`, 마이그레이션 때 이미 있던 계정도 5개), 더 주거나 회수하는 것은 관리자가 `#/weekly/admin` → 「실전 모드 관리」에서 합니다.
- **서버 시계**: 시작 시각은 서버가 기록하고(`started_at`), 5시간이 지나면 서버가 알아서 스캔 단계로, 다시 30분이 지나면 그때까지 받은 쪽으로 제출합니다. 창을 닫거나 새로 고치거나 다른 컴퓨터에서 들어와도 같은 시험이 이어지고 시간은 계속 흐르며, 토큰을 다시 쓰지 않습니다. 컴퓨터 시계가 틀려도 화면의 남은 시간은 서버 시각으로 계산합니다.
- **한 번에 하나**: 열려 있는(실험 중이거나 스캔 중인) 시험은 사람마다 하나뿐입니다(고유 인덱스 `lab_sessions_active`). 시작 요청이 동시에 여러 번 와도(더블 클릭, 탭 두 개) 세션 하나만 생기고 토큰도 하나만 나갑니다. 세션 생성 · 원장 기록 · 잔액 차감은 한 트랜잭션(`DB.batch`)이라, 토큰이 0이면 아무것도 생기지 않고 잔액이 음수가 되지 않습니다.
- **스캔**: 시간이 끝나면 실험 화면이 꺼지고 QR 코드가 뜹니다. QR에는 세션 번호와 일회용 업로드 토큰(서버에는 SHA-256만 저장)이 `#` 뒤에 들어 있어 휴대폰은 로그인 없이 `sim/scan.html`에서 답안지 · working sheet를 찍어 보냅니다. 사진은 휴대폰에서 하슬라논술 스캔 엔진(`sim/labscan/scanner.js`: 종이 모서리 → 원근 보정 → 그림자 제거)으로 A4로 펴고, 모서리는 손으로 맞출 수도 있습니다. 서버는 받은 쪽을 Upstage OCR(수식 모드)로 읽습니다.
- **채점**: 컴퓨터 화면에서 읽은 글을 확인 · 수정하고 제출하면, 실험마다 채점 기준(`lab_rubrics`, 관리자가 입력)으로 주간 서술형과 같은 방식으로 채점합니다 — 기준마다 0.1점 단위 점수, 답안에서 그대로 인용한 근거, 첨삭. 근거 없는 점수는 0점입니다. 채점 기준이 없는 실험이나 AI 키가 없으면 「채점 대기」로 두고 관리자가 점수를 주거나 나중에 「AI로 다시 채점」합니다. 결과는 `#/lab/<번호>`에, 기록과 토큰 내역은 `#/lab`에 있습니다.

### 올리는 순서

1. `migrations/0007_lab.sql`을 원격 D1에 적용합니다(`npm run db:remote`).
2. Worker를 다시 배포합니다(`npx wrangler deploy`). `/api/health`에 `lab: true`가 나오면 사이트가 실전 모드를 엽니다.
3. 관리자 화면에서 실험별 채점 기준을 넣습니다(`exam_key`는 `ipho2024`처럼 대회+연도, `task`는 `E1`). 기준 JSON은 `[{"id":"A.1","name":"…","max":0.5,"requirement":"…","partial":"…"}]`, `reference`에는 공식 답과 허용 오차를 적습니다.

로컬 시험: `.dev.vars`에 가짜 OCR · 채점 서버 주소와 짧은 시계(`LAB_TEST_EXAM_SEC=6`, `LAB_TEST_SCAN_SEC=6`, `LAB_TEST_GRACE_SEC=1`)를 넣고 `npm run dev` 뒤 `node test-lab.mjs`를 실행합니다(동시 시작 8번에 토큰 1개, 재입장 무료, 시간 초과 자동 전환, 업로드 토큰 교체, 다른 사람 접근 차단 등). 배포된 Worker에는 `LAB_TEST_*`를 넣지 마세요.

### API (v8)

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/lab/active` | 열려 있는 내 시험과 토큰 잔액 |
| POST | `/api/lab/start` | `{comp, year, tasks, entry}` → 새 시험(토큰 1개) 또는 열려 있는 같은 시험(토큰 0개). 다른 시험이 열려 있으면 409 `other_active`, 토큰이 없으면 402 `no_tokens` |
| POST | `/api/lab/sessions/:id/finish` | 일찍 끝내기 → 스캔 단계 |
| POST | `/api/lab/sessions/:id/qr` | 업로드 토큰 새로 받기(예전 QR은 무효) |
| GET · DELETE | `/api/lab/sessions/:id` | 시험 · 쪽 · 점수 / 끝난 시험 지우기(토큰은 돌아오지 않음) |
| PATCH | `/api/lab/sessions/:id/pages/:pid` | `{text, task, kind}` 읽은 글 고치기 |
| POST | `/api/lab/sessions/:id/submit` | 제출하고 채점 |
| GET | `/api/lab/sessions` · `/api/lab/tokens` | 내 시험 목록 · 토큰 잔액과 내역 |
| GET | `/api/lab/pages/:pid/img` | 쪽 사진(본인 · 관리자) |
| GET · PUT · DELETE | `/api/lab/up/:id`, `/api/lab/up/:id/pages?task=&kind=`, `/api/lab/up/:id/pages/:pid` | 휴대폰(헤더 `X-Lab-Token`): 상태 / 쪽 보내기(JPEG · PNG · WebP, 1.9 MB까지, 40쪽까지) / 빼기 |
| GET · POST | `/api/admin/lab/tokens`, `/api/admin/lab/rubrics`, `/api/admin/lab/queue`, `/api/admin/lab/:id` | 관리자: 토큰 주기 · 채점 기준 · 채점 대기 · 점수 주기/다시 채점 |

## v9: 답안 이미지 채점 (Gemini Flash · 공식 채점 기준표 · 엄격 규정)

실전 모드의 답안은 공식 대회 Answer sheet · Working sheet에 쓰고, 채점은 사람 검토 없이 끝까지 자동으로 합니다. 엄격한 감독관처럼 읽을 수 없는 것은 응시자 책임입니다.

1. **채점 기준표**: 실험을 처음 채점할 때, 그 실험의 공식 솔루션 PDF(영문 원본이 있으면 영문)를 Gemini에 보내 동봉된 채점 기준표를 항목별 JSON으로 뽑습니다. 항목마다 번호, 배점, 종류(값 · 그래프 · 표 · 유도 · 기타), 답안지 전용 여부, 만점 범위, 부분 점수 범위, 그래프 확인 항목을 담고, `lab_schemes`에 (시험, 실험, 솔루션 파일)마다 한 번만 저장해 계속 씁니다. 관리자가 `#/weekly/admin`에서 직접 넣은 채점 기준이 있으면 그것을 먼저 씁니다.
2. **쪽 읽기**: 휴대폰에서 쪽이 올라오는 즉시 공식 답안지의 머리글(어느 실험, 답안지/연습지, 몇 쪽)과 판독 상태(잘 읽힘 · 일부 · 거의 못 읽음), 문항별 답(값과 단위, 표, 그래프의 축 · 점 개수 · 맞춤선 등)을 읽습니다. 머리글이 있으면 휴대폰에서 고른 것보다 머리글을 따릅니다. **읽힌 내용은 응시자가 고칠 수 없고**(`read_only`), 잘못 읽혔으면 그 쪽을 빼고 다시 찍어야 합니다.
3. **채점**: 제출하면 실험마다 채점 규정 → 채점 기준표 → 쪽마다 라벨 · 이미지 · 읽힌 내용을 한 번에 보냅니다. 앞부분(규정 · 기준표)은 응시자마다 같아서 Gemini의 자동 캐시가 재사용합니다. 그 결과에서 코드가 다음을 직접 정합니다.
   - 값 항목은 읽힌 값이 만점 · 부분 점수 범위에 드는지로 점수를 매깁니다(모델 점수는 쓰지 않음).
   - 그래프 항목은 기준표의 확인 항목 중 실제로 읽힌 그래프에서 확인되는 것만 더합니다(R7).
   - 최종 답 항목의 근거가 연습지면 0점(R1), 근거 쪽이나 값이 읽힌 내용에 없으면 0점(R9).
   - 유도 · 기타 항목만 모델 점수를 씁니다.
4. **채점 규정**(`LAB_REG`, 버전 `2026-10-28`, R1–R10)은 Worker 코드에 있고 `/api/health`의 `lab_reg`로도 나갑니다. 성적표는 항목마다 점수, 판정, 근거(쪽 · 시트 · 값), 계산 방식(범위·검증 / AI 판단), 적용 규정을 보여 줍니다.
5. 채점 모델이 응답하지 않아 실패하면 2분 간격으로 세 번까지 저절로 다시 채점합니다. 솔루션 파일이 없는 실험은 「채점 대기」(`no_solution`)로 남습니다.

모델은 `GEMINI_MODEL`(기본 `gemini-flash-latest`)이고, 솔루션 PDF는 `LAB_PDF_BASE`(기본 PDF Worker)에서 가져옵니다. Gemini 키가 없으면 예전처럼 Upstage OCR 글자로 채점합니다.

### 올리는 순서

1. `migrations/0008_lab_grading.sql`을 원격 D1에 적용합니다(0007 다음). `/api/health`의 `lab`은 0007과 0008이 모두 있어야 `true`입니다.
2. Worker를 배포하고 `GEMINI_API_KEY`를 Secret으로 넣습니다.

로컬 시험: `node test-lab-mock.mjs`(가짜 Upstage · Gemini · PDF)를 띄우고 `.dev.vars`에 `LAB_PDF_BASE=http://127.0.0.1:8799/pdf/`를 더한 뒤 `node test-lab-grading.mjs`.

## 처음 배포하기 (명령줄)

Node.js 18 이상이 필요합니다.

```bash
cd community
npm install

# 1. Cloudflare 계정에 로그인 (브라우저가 열립니다)
npx wrangler login

# 2. 데이터베이스 만들기 → 출력되는 database_id 를 wrangler.toml 에 붙여 넣기
npx wrangler d1 create haslalab-community

# 3. 표 만들기
npm run db:remote

# 4. 서버 올리기 → https://haslalab-community.<계정이름>.workers.dev 주소가 나옵니다
npm run deploy
```

그다음 `index.html`에서 아래 줄을 찾아 4단계에서 나온 주소를 넣고 커밋하면 사이트에 커뮤니티가 열립니다.

```js
const COMMUNITY_API = "https://haslalab-community.<계정이름>.workers.dev";
```

`api.haslalab.org`처럼 자기 도메인을 쓰고 싶다면 조건이 하나 있습니다. haslalab.org의 DNS가 Cloudflare에 있어야 합니다. 그러면 Workers → haslalab-community → Settings → Domains & Routes에서 Custom Domain을 추가하고, 그 주소를 `COMMUNITY_API`에 넣으면 됩니다.

## 관리

관리자 계정은 모든 글과 댓글을 지울 수 있습니다. 관리자로 지정하려면 다음 명령을 실행합니다.

```bash
npx wrangler d1 execute haslalab-community --remote \
  --command "UPDATE users SET role='admin' WHERE username='아이디'"
```

신고 목록은 이렇게 봅니다.

```bash
npx wrangler d1 execute haslalab-community --remote \
  --command "SELECT * FROM reports ORDER BY id DESC LIMIT 50"
```

API를 부를 수 있는 사이트 주소는 `wrangler.toml`의 `ALLOWED_ORIGINS`에서 정합니다.

## 로컬에서 시험하기

```bash
npm run db:local
npm run dev          # http://127.0.0.1:8787
```

사이트를 `http://localhost:8765`로 띄웁니다. 그다음 브라우저 콘솔에서 아래 명령을 한 번 실행하면 로컬 서버에 붙습니다.

```js
localStorage.setItem("hlCmApi", "http://127.0.0.1:8787")
```

## API

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `/api/signup` | `{username, nickname, password}` → `{token, user}` |
| POST | `/api/login` | `{username, password}` → `{token, user}` |
| POST | `/api/logout` | 현재 토큰 폐기 |
| GET | `/api/me` | 로그인한 사용자 |
| POST | `/api/me/password` | `{old, password}` |
| DELETE | `/api/me` | 계정 삭제 |
| GET | `/api/posts?board=&q=&page=` | 글 목록 (20개씩) |
| POST | `/api/posts` | `{board, title, body}` |
| GET | `/api/posts/:id` | 글 + 댓글 (`?view=1`이면 조회수 +1) |
| PATCH / DELETE | `/api/posts/:id` | 글 수정 / 삭제 (작성자 · 관리자) |
| POST | `/api/posts/:id/like` | 좋아요 토글 |
| POST | `/api/posts/:id/comments` | `{body}` |
| PATCH / DELETE | `/api/comments/:id` | 댓글 수정 / 삭제 |
| POST | `/api/report` | `{kind: "post"\|"comment", id, reason}` |
| PUT · DELETE | `/api/me/avatar` | 프로필 사진 올리기(본문은 JPG · PNG · WebP, 64KB 이하) · 지우기 |
| GET | `/api/avatar/:key` | 프로필 사진 |
| GET | `/api/oauth/:provider/start?return=` | Google · 카카오 · 네이버 · GitHub · Discord 로그인 시작 (브라우저 이동) |
| GET | `/api/oauth/:provider/callback` | 서비스에서 돌아오는 곳 |
| POST | `/api/oauth/redeem` | `{code}` → `{token, user, fresh}` |
| POST | `/api/oauth/ticket` | 로그인한 계정에 서비스를 연결할 때 쓰는 일회용 표 |
| GET | `/api/me/identities` | 연결된 서비스, 비밀번호 유무 |
| PATCH | `/api/me` | `{nickname}` 닉네임 바꾸기 |
| GET | `/api/weekly?lang=&week=` | 이번 주(또는 그 주) 문제 목록, 내 최고 점수, 주 목록 |
| GET | `/api/problems/:id?lang=` | 문제 본문, 채점 항목, 내 제출, (마감 후) 풀이 |
| POST | `/api/problems/:id/submit` | `{answer, via_ocr}` → `{status, score, detail}` |
| POST | `/api/ocr?mode=text\|math` | multipart `image` → `{text, confidence}` |
| GET | `/api/rank?scope=week\|all&week=` | 랭킹 100위까지 |
| GET | `/api/me/stats` | 내 순위, 총점, 최근 제출 |
| GET/POST | `/api/admin/problems` | 문제 목록 / 추가·수정 (관리자) |
| GET | `/api/admin/queue` | 채점 대기 답안 (관리자) |
| POST | `/api/admin/submissions/:id` | `{score, note}` 또는 `{regrade: true}` (관리자) |
