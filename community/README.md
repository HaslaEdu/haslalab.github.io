# HaslaLab 커뮤니티 서버

## 지연·트래픽 관리

현재 배포는 `.github/workflows/deploy-worker.yml`과 `wrangler deploy`를 사용합니다. ESM 의존 모듈, D1, R2, `LAB_JOBS` 큐를 함께 유지해야 하므로 아래의 과거 대시보드 붙여넣기 안내 대신 이 워크플로를 사용하세요. 배포 전 `provision-jobs.mjs`가 기존 자격 증명으로 작업 큐를 준비하며 권한·통신 오류는 배포를 중단합니다. 고정된 추가 작업 테이블은 기존 D1 바인딩에서 한 번 초기화하므로 배포 토큰에 D1 관리·가져오기 권한을 추가할 필요가 없습니다. 성능 원칙과 확인 방법은 [PERFORMANCE.md](../PERFORMANCE.md)에 있습니다.

브라우저의 현재 기본 API는 `https://haslalab-community-edge.haslalab.workers.dev`입니다. 이 엣지 Worker는 공개 캐시와 사전 요청을 가까운 위치에서 처리하고, 나머지는 Service Binding으로 기존 `haslalab-community` Worker에 전달합니다. 기존 Worker는 실측된 D1 primary(HKG) 가까이 배치되며 OAuth·결제·채점 Secrets와 작업 큐를 유지합니다. 공개 API의 기존 주소도 호환성을 위해 유지하며 등록된 OAuth 콜백·결제 webhook 주소는 바꾸지 않습니다. 배포 순서는 기존 Worker, `wrangler.edge.toml`의 엣지 Worker, PDF Worker입니다.

공개 게시판·게시글 목록과 비로그인 주간 목록·순위는 엣지의 `PUBLIC_DB.withSession()`에서 조회할 수 있습니다. 계정·잔액·답안·게시글 상세와 모든 쓰기는 기존 primary 경로를 유지합니다. `GLOBAL_PUBLIC_READS=1`은 공개 SELECT 경로를 켜는 설정이며 D1 복제 활성화 자체는 별도입니다. CI의 `provision-replication.mjs`가 기존 DB 설정을 조회·검증하고, 기존 키의 권한이 부족한 401/403은 `unverified`로 보고합니다. 이 경우 Cloudflare의 **D1 → haslalab-community → Settings → Read replication** 설정을 확인해야 합니다. 실제 복제본 동작은 `/api/health?read_region_check=1`의 `replica`, `primary`, 지역 정보로 판정합니다. 새 유료 상품·플랜·API 키는 만들지 않습니다.

## 2026-10-30: 하슬라논술과 같은 스캔 · Upstage 원문 처리

하슬라논술 저장소의 고정 버전 `24b8036037cb227237bd2fe75023f7b4d7472ef0`을 기준으로 촬영·전처리·Upstage 요청과 응답 처리를 맞췄습니다. 휴대폰 스캔, PC 검토용 사진·PDF, 주간 문제 사진 답안이 같은 스캐너를 사용합니다. 원문·수식은 그대로 보존하고 채점 입력에도 전달하며, Gemini는 기존 채점에 필요한 항목·그림 구조화를 보조합니다. OCR 오류가 나면 다른 엔진의 재필사로 조용히 대체하지 않습니다.

기존 `UPSTAGE_API_KEY` Secret을 그대로 사용합니다. 키나 학생 답안으로 자동 테스트하지 않습니다. D1 용량 제한, 시험 QR 토큰·마감·결제·답안 수정 규칙은 유지합니다. 출처와 저장 방식 차이는 [스캐너 이식 기록](../sim/labscan/README.md)에 있습니다.

회귀 검증: `node --test community/test-ocr-parity.mjs tests/test-scan-quality.mjs tests/test-contest-review.cjs` (저장소 루트에서 실행).

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

## v4: 사이트 로그인 · 월별 문제 · 채점 · 랭킹

커뮤니티 계정이 그대로 사이트 계정이 됩니다. 사이트 오른쪽 위에 로그인 버튼이 생기고, 「월별 문제」(`#/monthly`), 랭킹(`#/rank`), 내 기록(`#/me`) 화면이 열립니다. 예전 `#/weekly` 주소도 계속 열립니다.

- **단답형** 문제는 서버가 숫자를 정답과 비교해 바로 채점합니다(허용 오차는 문제마다 `rel` 또는 `abs`). AI 키가 없어도 동작합니다.
- **서술형** 문제는 하슬라논술 채점기(`grade-v2`)와 같은 방식으로 채점합니다. 문제의 채점 기준(루브릭)마다 점수를 매기고, 학생 답안에서 그대로 인용한 근거를 붙입니다. 답안에 없는 근거로 준 점수는 0점으로 바꿉니다. Gemini 키가 있으면 Gemini를, 없고 OpenAI 키가 있으면 OpenAI를 씁니다. 둘 다 없으면 답안은 「채점 대기」로 저장되고, 관리자가 `#/weekly/admin`에서 점수를 줍니다.
- **사진 답안**은 하슬라논술처럼 Upstage OCR로 읽습니다. 수식이 많으면 Document Parse로 LaTeX를 살려 읽습니다. 읽은 글은 학생이 확인하고 고친 뒤에 제출합니다. 이미지는 JPEG·PNG·WebP 한 장, 8 MB까지 받고, 한 사람이 하루 30번까지 쓸 수 있습니다.
- **월별 랭킹**은 해당 월의 제출 기간 안에 받은 문제별 최고 점수를 더합니다. 같은 점수면 먼저 도달한 사람이 앞섭니다. 마감 후에는 풀이가 공개되고, 이후 제출은 연습으로만 채점합니다. 전체 랭킹과 티어는 레이팅을 사용합니다.
- 문제는 관리자 화면에서 월 단위로 추가합니다. 기존 `week` 필드는 월 식별자 `YYYY-MM`도 받으며, `opens_at`/`closes_at`은 유닉스 초입니다. 마감은 포함하지 않는 경계입니다. 2026년 11월 문제는 11월 30일 전체를 포함하고 12월 1일 00:00 KST (`1796050800`)에 마감합니다.

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

모델은 `GEMINI_MODEL`(기본 `gemini-flash-latest`)이고, 솔루션 PDF는 GitHub Release(`pdf-<접두어>`)에서 바로 가져옵니다(`LAB_PDF_BASE`로 바꿀 수 있음 — Worker는 같은 계정의 다른 workers.dev 주소를 부를 수 없습니다). Gemini 키가 없으면 예전처럼 Upstage OCR 글자로 채점합니다.

**Upstage + Gemini 읽기**: `UPSTAGE_API_KEY`도 있으면 쪽마다 Upstage Document Parse가 먼저 손글씨를 받아 적고, Gemini는 그 전사문을 이미지 옆에 두고 문항 · 값 · 표 · 그래프를 정리합니다(숫자 · 기호는 전사문으로 확인, 판단은 이미지 기준). Upstage 신뢰도가 0.6 아래면 판독 상태가 「일부」를 넘지 못하고, 0.3 아래면 「거의 못 읽음」입니다.

**시험 전 · 중 · 후 (사이트 쪽)**
- `sim/sheets.html`: 시작 전에 인쇄하는 답안지. 대회가 공개한 **공식 Answer sheet · Working sheet**가 있으면 그것을 그대로 엽니다(`sim/sheets/`, `tools/labofficial.py` — 비어 있는 귀퉁이에만 스캐너용 검은 사각형을 덧찍음, 목록은 `sim/sheets/index.json`). 공개되지 않은 것만 HaslaLab 양식(문항 칸 · 측정표 · 그래프 용지, 문항 번호와 배점은 `sim/labsheets.json` / `tools/labsheets.py`)으로 인쇄합니다. 문제지는 여기 없습니다. 공식 시트의 머리글 코드(A1-3 = 실험 1 답안지 3쪽, W2-1 = 실험 2 연습지)는 읽을 때 실험 · 시트로 옮겨집니다.
- `sim/exam.html`: 문제지는 시험 중에만 «문제지 열기»로 책상 옆에 pdf.js로 그려 보여 줍니다(내려받기 · 인쇄 버튼 없음, 시험 창 인쇄는 빈 쪽).
- `sim/scan.html`: 실시간 카메라가 종이를 찾아 테두리를 그리고, 네 사각형이 1초쯤 멈추면 저절로 찍습니다(`labscan/scanner.js`의 `findSheetMarkersGray`).
- 성적표와 확인증: `sim/result-comparison.js`가 `sim/results/<대회>.json`의 공개 점수·수상 기준과 비교합니다. 같은 연도·전체 문항·공식 만점이 일치한 라운드만 자동 비교하며, 일부 문항을 전체 시험으로 환산하지 않습니다. 메달 기준은 그 수상을 결정하는 전체 점수에만 적용합니다. 이론·실험 합산 대회는 다른 라운드 점수를 입력해 총점을 참고 비교할 수 있습니다. 입력 점수는 서버에 저장하지 않습니다. 자료가 수상자 일부만 포함하면 전체 참가자 순위·상위 비율로 표시하지 않습니다. 데이터 출처와 수록 범위는 `tools/results/README.md`에 설명되어 있습니다.
- `GET /lab/sessions/:id`와 선택한 성적표의 bootstrap은 `sample_standing`을 반환합니다. 같은 대회·연도·문항·배점·채점 기준에서 1인 첫 채점 결과를 표본으로 삼고 실전/채점·첨삭은 분리합니다. 재응시는 본인의 현재 점수를 다른 사람의 첫 채점과 비교하며, 동점은 공동 순위입니다. 표본 1명일 때는 상위 비율을 표시하지 않습니다. 정성 첨삭과 점수가 없는 기록은 표본에서 제외합니다.

**스캔 AI 비교** (`sim/scanbench.html`, 관리자만): 휴대폰으로 찍은 A4 사진을 연결된 AI마다 가장 싼 비전 모델(Gemini `gemini-flash-lite-latest`, OpenAI `gpt-5-nano`, Claude `claude-haiku-5-5` — `BENCH_*_MODEL`로 바꿈, Claude 키는 `ANTHROPIC_API_KEY` 또는 `CLAUDE_API_KEY`)과 Upstage(페이지 탐지가 없어 글자 범위로 대신)에 보내 종이 네 귀퉁이를 찾게 하고, HaslaLab 기기 안 탐지와 함께 관리자가 표시한 정답 귀퉁이와의 오차로 순위를 매깁니다. 사진과 결과는 `scan_bench` 표(처음 쓸 때 저절로 만들어짐)에 남습니다. API: `POST/GET /api/admin/lab/scanbench`, `PATCH /api/admin/lab/scanbench/:id {gt}`.

**응답 시간 보기**: 모든 응답에 `Server-Timing: db;desc="n queries";dur=…, total;dur=…`가 붙습니다(브라우저 개발자 도구 → Network → Timing). 서버 안에서 걸린 시간과 데이터베이스 왕복 횟수가 보이므로, 느릴 때 서버 탓인지 네트워크 탓인지 가를 수 있습니다.

### 올리는 순서

1. `migrations/0008_lab_grading.sql`을 원격 D1에 적용합니다(0007 다음). `/api/health`의 `lab`은 0007과 0008이 모두 있어야 `true`입니다.
2. Worker를 배포하고 `GEMINI_API_KEY`를 Secret으로 넣습니다.

로컬 시험: `node test-lab-mock.mjs`(가짜 Upstage · Gemini · PDF)를 띄우고 `.dev.vars`에 `LAB_PDF_BASE=http://127.0.0.1:8799/pdf/`를 더한 뒤 `node test-lab-grading.mjs`.

## v10: 채점 비용 · 시간 · 정확도 기록, 답안 사진 보관, 일회용 스캔 링크, 측정 개수 규정(R11)

- **비용 · 시간**: 실전 시험에서 AI를 부를 때마다(쪽 읽기의 Upstage · Gemini, 채점 기준표, 채점) `lab_calls`에 한 줄씩 남깁니다 — 토큰(입력 · 출력 · 캐시), Upstage 쪽 수, 걸린 시간, 추정 가격. 가격은 코드의 `PRICES`(USD / 100만 토큰, Upstage는 쪽당)로 매기고, `LAB_PRICES`(JSON, 같은 모양)로 바꾸거나 더할 수 있습니다. 실험마다 `detail.tasks.E1.usage`, 시험마다 `detail.grade_ms`도 남습니다.
- **정확도**: 관리자는 성적표(`#/lab/<id>`)에서 문항마다 «기준» 점수를 넣고 저장합니다(`lab_reviews`). `#/weekly/admin`의 실전 모드 관리에 «채점 비용 · 시간 · 정확도»가 나옵니다: 시험 1회당 평균 비용 · 토큰 · 호출 수 · 채점 시간, 단계별 표, 문항당 평균 차이, 일치율, 실험 총점 차이. API: `GET /api/admin/lab/metrics?days=30`, `POST /api/admin/lab/:id/review {task, items:[{id, ref}]}`.
- **답안 사진**: Worker에 R2 버킷을 `LAB_PAGES`로 연결하면 사진은 R2에, 아니면 예전처럼 D1(`lab_pages.data`)에 둡니다. D1 무료 한도(데이터베이스당 500MB)를 생각하면 R2가 낫습니다. 채점이 끝나고 **2시간** 지난 시험의 사진을 지웁니다 — 읽힌 내용과 점수, 성적표는 남고 사진만 410(`purged`)이 됩니다. `LAB_KEEP_HOURS`로 시간을 바꾸고(예: `24`), `off`면 지우지 않습니다. 관리자의 기준 점수(정확도)는 사진이 있는 2시간 안에 넣는 것이 좋습니다. 지우기는 요청 10번에 한 번꼴로 저절로 돌고, Cron Trigger(`*/15 * * * *` 등)를 걸면 제때 돕니다.
- **스캔 링크**: QR 링크에는 시험 번호 없이 코드 하나(`#c=` — 만든 시각을 36진수로 + 128비트 난수를 62진수로)만 들어갑니다. 해시만 저장하고 모든 시험에 걸쳐 유일합니다(고유 인덱스). 스캔이 끝나면(제출 또는 마감) 서버가 링크를 파기하고(`void:…`), 휴대폰은 410 `scan_over`를 받습니다. 예전 링크(`#s=…&k=…`)도 그대로 됩니다.
- **R11 측정 개수**(규정 `2026-10-29`): 측정표와 그래프는 채점 기준표가 정한 수 이상의 측정값이 있어야 합니다. 기준표에 수가 없으면 실험에 따라 적음 3 · 중간 5 · 많음 7개(기준표를 뽑을 때 `n_min`, `n_class`). 표의 행 수와 그래프의 점 수는 읽힌 내용으로 코드가 셉니다: 개수 확인 항목(`rows_min`, `points_min`)은 모자라면 0점, 그런 항목이 없는 표 · 그래프는 모자라면 절반.

### 올리는 순서

1. `migrations/0009_lab_metrics.sql`을 원격 D1에 적용합니다(0008 다음). 적용 전에도 채점은 되지만 기록 · 기준 점수 · R2는 쓰이지 않습니다.
2. Worker를 배포합니다. 필요하면 R2 버킷을 만들어 `LAB_PAGES`로 연결합니다. 사진 보관 시간을 2시간에서 바꿀 때만 `LAB_KEEP_HOURS`를 넣습니다.

로컬 시험: `node test-lab-metrics.mjs`, R2와 파기는 `npx wrangler dev --config wrangler.test-r2.toml --port 8789` 뒤 `R2=1 API=http://127.0.0.1:8789 node test-lab-metrics.mjs`.

## v11: 실전 토큰 구매(Paddle · 토스페이먼츠)와 영상 광고 충전

- **Paddle (해외 · USD, 먼저 여는 쪽)**: Paddle이 판매자 대행(merchant of record)이라 나라별 세금 · 영수증 · 환불 처리를 맡습니다. Paddle 카탈로그에 상품(실전 토큰)과 묶음별 일회성 가격 3개 — **1개 $1.49 · 5개 $5.99 · 10개 $9.99** — 를 만들고, 그 가격 ID를 이 순서대로 `PADDLE_PRICES=pri_…,pri_…,pri_…`에 넣습니다. 묶음을 바꾸려면 `PADDLE_PACKS`(JSON, 있으면 우선)에 직접 적습니다 — 예: `[{"id":"p1","tokens":1,"price_id":"pri_…","usd":1.49},{"id":"p5","tokens":5,"price_id":"pri_…","usd":5.99}]` (`usd`는 버튼에 보이는 값, 실제 금액 · 통화는 Paddle 결제창이 정함).
  - 흐름: 서버가 주문을 먼저 저장 → Paddle.js v2 오버레이 결제창(`custom_data.order_id`에 주문번호) → Paddle이 보내는 **서명된 웹훅** `transaction.completed`/`transaction.paid`(`POST /api/pay/paddle/webhook`, `Paddle-Signature`를 HMAC-SHA256 `ts:원문`으로 검증, 5분 넘은 것은 거절)으로 토큰을 한 번만 더함. 결제가 끝나 `pay.html`로 오면 서버가 거래를 Paddle API로 조회해 웹훅보다 먼저 끝낼 수도 있음(주문번호 · 가격이 맞을 때만).
  - 환불: 관리자 `POST /api/admin/pay/<주문>/cancel` → Paddle 환불 조정(`/adjustments`, full) + 토큰 회수. Paddle 대시보드에서 승인한 환불도 웹훅(`adjustment.*`, refund · approved)으로 받아 토큰을 회수합니다.
  - 환경 변수: `PADDLE_CLIENT_TOKEN`(공개 — `test_…`면 샌드박스, `live_…`면 실제), `PADDLE_API_KEY`(Secret — 새 API 키를 만들 때 권한은 **Transactions: Read**(`transaction.read`)와 **Adjustments: Write**(`adjustment.write`) 두 개만), `PADDLE_WEBHOOK_SECRET`(Secret — Paddle › Developer tools › Notifications에서 이 주소로 대상 만들 때 나오는 비밀 키), `PADDLE_PRICES`(또는 `PADDLE_PACKS`). 웹훅 대상: `https://haslalab-community.haslalab.workers.dev/api/pay/paddle/webhook`, 이벤트 `transaction.completed`, `transaction.paid`, `adjustment.created`, `adjustment.updated`.
  - 로컬 시험: `node test-paddle.mjs`(mock의 `/paddle`).

- **구매**: `#/lab`의 «토큰 충전»에서 묶음(기본 1개 1,900원 · 5개 7,900원 · 12개 15,900원 — `PAY_PACKS` JSON으로 바꿈)을 고르고, 구매 안내(만 19세 미만은 보호자 동의) 확인 후 토스페이먼츠 결제창(v2 SDK, 카드 · 간편결제)이 열립니다. 서버가 먼저 주문(`pay_orders`, 주문번호 = 시각 + 난수)을 저장하고, 결제가 끝나면 토스가 `pay.html`로 돌려보내며, 서버가 **금액을 자기 주문과 비교한 뒤** 시크릿 키로 결제를 승인하고 토큰을 한 번만 더합니다(같은 트랜잭션에서 `credited` 표시 — 새로고침이나 동시 요청에도 한 번). 이미 승인된 결제(`ALREADY_PROCESSED_PAYMENT`)는 조회해서 확인합니다.
- **환불**: 관리자가 `POST /api/admin/pay/<주문번호>/cancel {reason}` — 토스에서 결제를 취소하고, 남은 토큰에서 그만큼 회수합니다. 결제 목록: `GET /api/admin/pay/orders`.
- **영상 광고**: Google Ad Manager의 **보상형 광고(rewarded)** 만 씁니다(일반 광고를 보상과 묶는 것은 정책 위반). 1편 = 토큰 1/3(`users.token_parts`), 3편이면 토큰 1개. 광고를 시작할 때 서버가 일회용 번호를 주고, 광고가 «보상 획득»을 알리면 그 번호로 받습니다 — 시작 후 `ADS_MIN_SEC`(기본 10초) 이상 지나야 하고, 하루(한국 날짜) `ADS_DAILY`(기본 3)편까지, 같은 번호는 한 번만. 웹 보상형 광고는 **휴대폰 화면에서만** 나옵니다(Google 제약).
- 환경 변수: `TOSS_CLIENT_KEY`, `TOSS_SECRET_KEY`(Secret), `PAY_PACKS`(선택), `ADS_REWARDED_UNIT`(Ad Manager 보상형 광고 단위 경로, `test`면 Google 샘플 단위), `ADS_DAILY`, `ADS_MIN_SEC`. 키가 없으면 해당 칸은 «준비 중»으로 나옵니다.
- 실제 판매 전에: 사업자등록 · 통신판매업 신고, 사이트 하단의 사업자 정보와 환불 규정, 토스페이먼츠 가맹 심사(라이브 키). Ad Manager 계정과 보상형 광고 단위.

### 올리는 순서

1. `migrations/0010_tokens.sql`을 원격 D1에 적용합니다(0009 다음).
2. Worker를 배포하고 위 환경 변수를 넣습니다(테스트 키 `test_ck_…` / `test_sk_…`로 먼저 시험).

로컬 시험: `.dev.vars`에 `TOSS_CLIENT_KEY=test_ck_mock TOSS_SECRET_KEY=test_sk_mock TOSS_BASE=http://127.0.0.1:8799/toss ADS_REWARDED_UNIT=test ADS_MIN_SEC=1 ADS_DAILY=3`, `node test-lab-mock.mjs` 후 `node test-shop.mjs`.

## v12: 실험 채점의 총평 · 첨삭

실험 채점(Gemini, `GRADE_SCHEMA`)이 점수와 별도로 코치처럼 `review`를 씁니다 — 점수는 바꾸지 않습니다.
- `summary`: 답안 전체에 대한 총평 2–4문장(무엇이 점수를 지켰고 무엇이 깎였는지).
- `strengths`: 잘한 점(최대 3).
- `habits`: 고쳐야 할 습관과 고치는 방법, 그 습관이 보인 쪽(최대 5) — 예: 단위 · 유효숫자 누락, 그래프 점 부족 · 축 눈금, 불확도 생략, 표의 머리말 누락, 계산 과정 없이 답만.
- `handwriting`: 글씨 평가 `clear | readable | hard`와 메모 — 헷갈리는 숫자(1/7, 0/6, 4/9, u/μ), 소수점 · 음수 부호 · 지수, 붙은 글씨, 칸 밖으로 나간 답.
- `presentation`: 답을 정해진 칸에 썼는지, 표 · 그래프 배치, 페이지 번호.

성적표(`#/lab/<id>`)의 실험별 피드백 아래 «📝 총평» 칸에 나옵니다. 저장 위치: `detail.tasks.E1.review`.

## v13: 이론 문제와 이론 실전 모드

- **이론 문제(원문)**: 모든 대회의 해마다 공개된 이론 문제지 · 해설(번역 없이 원문), 따로 공개된 채점 기준표와 답안지를 연도 페이지의 «이론 문제»에 둡니다. 목록은 `tools/theory/<대회>.json`, 사이트는 그것으로 만든 `theory.js`를 읽습니다(`python tools/theory_build.py`). PDF는 GitHub Actions(«Theory papers to releases»)가 원래 주소에서 받아 릴리스 `pdf-<접두어>`에 올리고, PDF Worker가 내줍니다. 자세한 규칙: `tools/theory/README.md`.
- **이론 실전 모드**: 실험 실전 모드와 같은 화면(수험 안내 → 시험 → 30분 스캔 → 채점)입니다. 시험 중에는 실험 책상 대신 **이론 문제지가 화면 가득** 열립니다(pdf.js로 그려서 내려받기 · 인쇄 버튼이 없고, 시험 창을 인쇄해도 아무것도 찍히지 않음). 시간: 5시간(USAPhO · IJSO · IBO · IESO · OPhO는 3시간, `THEORY_SEC` / `examdur.js`). 답안지는 공식 답안지가 공개된 해는 그것을, 아니면 HaslaLab 이론 답안지(빈 답 칸 + 스캔 마커)를 인쇄합니다.
- **채점**: 시작할 때 각 문제가 `sources[task] = {sol, mark, kind:"theory"}`로 서버에 남습니다. 채점 기준표는 **공식 해설과 따로 공개된 채점 기준표를 함께** Gemini에 보내 만들고(`lab_schemes`의 source는 `해설+기준표`), 쪽 읽기와 채점은 이론 시험용 지시(수식은 LaTeX식으로 그대로 옮기기, 최종 답 칸, 풀이 점수)를 씁니다. 총평 · 잘한 점 · 고칠 습관(답 칸에 최종 답, 단계 생략, 차원 · 극한 확인, 근사 표시, 부호 · 2배 실수, 숫자를 너무 일찍 대입 …) · 글씨 · 답안 구성까지 첨삭합니다. DB 변경은 없습니다.
- **NBPhO**: 대회 책자 한 권에 실험과 이론이 함께 있어 실전 모드도 **실험 + 이론 한 시험**입니다(과제 `E1, E2, T`, `kind: "mixed"`). 시간은 그해 대회 전체 시간(`NBPHO_TIME`, 두 라운드면 10시간). 책상 왼쪽 아래(부품함 밑)에 **문제지 더미**가 놓여 있고 누르면 책자가 열립니다(다른 실험 시험에도 같은 문제지가 놓입니다). 이론 과제 `T`의 채점 기준은 책자 해설에서 실험 문제(`skip`)를 빼고 만들고, 실험은 책자 번호(`no`, 예: Problem 5 → E1)로 찾습니다. 쪽 읽기도 이 번호표로 과제를 고릅니다.
- **NBPhO 연습 모드**: 책자를 문제별 PDF로 잘라 `pdfx/nbpho/`에 둡니다(`python tools/nbpho_split.py <책자 폴더>`, PyMuPDF). 단 단위로 문제 영역만 남기고 나머지는 지운(redaction) 뒤 잘라 내 글자 · 그림은 벡터 그대로입니다. 실험 카드의 문제지 · 해설과 이론의 T1, T2 …가 이 파일을 씁니다. 스캔본이라 글자 정보가 없는 2003–2005 · 2007 · 2009년과 일부 해설은 책자 그대로입니다. 서버는 릴리스에 없는 해설을 사이트의 `pdfx/<대회>/`에서 찾습니다(`LAB_SITE_BASE`).
- 메달 추정은 실험 점수 자료라 이론 · 통합 시험에는 보이지 않습니다.
- 로컬 시험: `node test-theory.mjs`(mock, 6초 시계).

## v14: 응시는 무료, 채점 · 첨삭에 토큰

- 실전 모드 시작은 토큰을 쓰지 않습니다. **채점 · 첨삭을 신청할 때 실전 토큰 1개**(시험마다 한 번)를 씁니다 — 시작할 때(안내 화면의 «채점 · 첨삭도 신청»), 스캔 화면에서, 또는 끝난 뒤 성적표에서. `POST /api/lab/sessions/:id/pay`(한 번만 차감, 동시에 눌러도 한 번), `submit`은 `grade:false`면 채점 없이 끝내고(`status: 'ended'`) 그 밖에는 차감한 뒤 채점합니다. 장부 사유는 `grade`.
- 채점을 신청하기 전에는 보낸 쪽을 **읽지 않습니다**(`ocr_status: 'unpaid'`, AI 비용이 들지 않음). 신청 뒤 온 쪽은 바로 읽고, 그 전에 온 쪽은 채점할 때 읽습니다.
- 스캔 시간이 끝났는데 신청하지 않았으면 채점 없이 `ended`가 되고, 사진은 7일(`LAB_KEEP_ENDED_HOURS`) 보관한 뒤 지웁니다. 그 안에 성적표에서 채점을 신청할 수 있습니다.
- 이전 응시(시작할 때 토큰을 쓴 것)는 이미 `charged=1`이라 그대로 채점됩니다. DB 변경은 없습니다.

## v15: 실험 + 이론 세트, 0.5토큰
- 실험과 이론이 둘 다 있는 해는 **세트**로 봅니다. 실험과 이론을 따로(이어서 볼 필요 없이) 응시하고, 채점은 한쪽에 **0.5토큰**, 둘 다 하면 1토큰입니다. NBPhO처럼 실험과 이론을 한 번에 치르는 시험은 그대로 1토큰입니다.
- 시험 주소의 `h=1`(대회 포털이 붙임)이 시작 요청의 `pair: true`가 되고, 서버는 `sources._half`로 기억합니다(`labCost`).
- 0.5토큰은 `users.exam_half`(0/1)로 셉니다. 남은 0.5가 있으면 그것을 쓰고(원장 0), 없으면 토큰 1개에서 쓰고 나머지 0.5를 적립합니다(원장 −1). 원장의 `note='half'`가 0.5 채점 표시입니다. 토큰 수는 `exam_tokens + exam_half/2`로 보입니다(예: 2.5).
- **운영 DB에 `migrations/0011_half_tokens.sql`을 적용해야 켜집니다.** 적용 전에는 0.5 채점도 토큰 1개를 씁니다(이전과 같음).
- 시험: `node test-half.mjs` (6초 시계).

## 자동 배포 (GitHub Actions)

`main`에서 `community/src`나 `wrangler.toml`이 바뀌면 `.github/workflows/deploy-worker.yml`이 `wrangler deploy`로 Worker를 올립니다 — 대시보드에 붙여 넣을 필요가 없습니다. Actions 탭의 «Deploy community Worker» › Run workflow로 손으로 돌릴 수도 있습니다.
- 필요한 것: 저장소 Settings › Secrets and variables › Actions에 `CLOUDFLARE_API_TOKEN`(Cloudflare › My Profile › API Tokens › «Edit Cloudflare Workers» 템플릿).
- 대시보드에서 넣은 변수와 Secret은 그대로 남습니다(`keep_vars = true`). `wrangler.toml`에 적힌 `ALLOWED_ORIGINS`만 그 값으로 덮어씁니다.
- Cron Trigger `*/15 * * * *`(답안 사진 제때 지우기)도 함께 걸립니다.
- D1 마이그레이션은 돌리지 않습니다 — 지금처럼 콘솔에서 적용합니다.

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
| GET | `/api/users?nickname=&tab=posts\|comments&page=` | 공개 프로필과 작성 글·댓글 (20개씩, 로그인 불필요). 닉네임·프로필 사진·공개 활동만 반환하며, 기본은 한국어·영어 활동 전체 (`lang=ko\|en`으로 제한 가능) |
| GET | `/api/users/:nickname?tab=posts\|comments&page=` | 같은 공개 프로필 API의 경로 방식. `..`처럼 URL에서 정규화되는 닉네임은 위의 쿼리 방식 사용 |
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
| GET | `/api/monthly?lang=&month=` | 해당 월 문제 목록, 내 최고 점수, 월 목록 (`/api/weekly` 호환 주소 유지) |
| GET | `/api/problems/:id?lang=` | 문제 본문, 채점 항목, 내 제출, (마감 후) 풀이 |
| POST | `/api/problems/:id/submit` | `{answer, via_ocr}` → `{status, score, detail}` |
| POST | `/api/ocr?mode=text\|math` | multipart `image` → `{text, confidence}` |
| GET | `/api/rank?scope=month\|all&month=` | 월별·전체 랭킹 100위까지 (`scope=week` 호환 유지) |
| GET | `/api/me/stats` | 내 순위, 총점, 최근 제출 |
| GET/POST | `/api/admin/problems` | 문제 목록 / 추가·수정 (관리자) |
| GET | `/api/admin/queue` | 채점 대기 답안 (관리자) |
| POST | `/api/admin/submissions/:id` | `{score, note}` 또는 `{regrade: true}` (관리자) |
| GET | `/api/omr/catalog` | 실전모드 시험 목록·문항 수·채점 기준 버전 |
| POST | `/api/omr/attempts` | 로그인 필요. `{exam_key, client_id, answers}` → 서버 재채점 결과와 비교군 |

## 물리대회 실전 점수

`python tools/kphe_scoring_build.py`는 검증한 정답표와 `tools/kphe_scoring_policy.json`을 Worker에 묶습니다. 클라이언트가 보내는 점수는 받지 않고 답안을 다시 채점합니다. 같은 계정의 `client_id`는 다시 전송해도 기존 답안을 덮어쓰지 않습니다. 저장 테이블은 기존 D1 바인딩에서 멱등적인 `0012_omr.sql`을 최초 요청 시 실행해 준비합니다. 계정 삭제 시 답안 기록도 삭제됩니다.

현재 공개 자료로 확인한 규정은 오답 문항 배점의 25% 감점입니다. 공식 문항별 배점·분야별 비중·최종 환산식은 미확보 상태여서 `officialScore`는 `null`입니다. `correct − wrong × 0.25`는 공식 점수와 구분한 연습 지표입니다. 향후 `exams[회차][과정]`에 `verified: true`를 넣으려면 문항별 최종 배점(`points`, 분야 가중치가 있다면 반영한 값), 분야 대응(`fields`), 미응답 처리, 최저점·반올림·환산 규칙과 근거까지 확인하고 채점 코드를 함께 검증해야 합니다. 문항 수로 배점을 균등 분배하지 않습니다.

비교군은 같은 시험·과정·채점 버전에서 다른 계정의 첫 응시만 집계하고, 본인은 현재 응시 점수 하나로 비교합니다. 삭제 계정은 제외합니다. 5명 미만이면 백분위를 표시하지 않으며, 동점자는 모두 포함한 상위 비율을 사용합니다. 실제 대회 전체 참가자의 백분위가 아닙니다.
