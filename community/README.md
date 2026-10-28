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

## v5: Google · Discord · 네이버로 가입/로그인

로그인·회원가입 화면 맨 위에 「Google로 계속하기」, 「Discord로 계속하기」, 「네이버로 계속하기」 버튼이 생깁니다. 처음 들어오면 그 계정의 표시 이름을 닉네임으로 삼아 HaslaLab 계정이 만들어지고, 다음부터는 같은 계정으로 들어옵니다. 이메일은 받지도 저장하지도 않고, 각 서비스의 고유 번호만 `identities` 표에 둡니다. 「내 기록」(`#/me`)에서 닉네임을 바꾸고, 다른 서비스를 같은 계정에 연결하고, 아이디 로그인용 비밀번호를 만들 수 있습니다.

로그인이 끝나면 서버는 1분짜리 일회용 코드만 붙여 사이트로 돌려보내고, 사이트가 그 코드를 세션 토큰으로 바꿉니다. 토큰이 주소창이나 방문 기록에 남지 않습니다. 돌아갈 주소는 `ALLOWED_ORIGINS`에 있는 사이트만 허용합니다.

### 올리는 순서

1. `migrations/0005_oauth.sql`을 원격 D1에 적용합니다. 방법은 v4와 같습니다(Console에 붙여 넣기 또는 `npm run db:remote`).
2. `src/index.js`를 다시 붙여 넣고 Deploy 합니다. `/api/health`가 `v: 5`와 `oauth: [...]`를 돌려줍니다.
3. 각 서비스에 앱을 등록하고, 리디렉션 주소를 아래처럼 넣습니다. 받은 값은 Worker의 *Secret*으로 넣습니다.

| 서비스 | 앱 만드는 곳 | 리디렉션(콜백) 주소 | Secret 이름 |
|---|---|---|---|
| Google | Google Cloud Console → API 및 서비스 → 사용자 인증 정보 → OAuth 클라이언트 ID(웹 애플리케이션). 동의 화면 범위는 `openid`, `profile` | `https://haslalab-community.haslalab.workers.dev/api/oauth/google/callback` | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` |
| Discord | discord.com/developers/applications → OAuth2 | `https://haslalab-community.haslalab.workers.dev/api/oauth/discord/callback` | `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET` |
| 네이버 | developers.naver.com → 애플리케이션 등록 → 네이버 로그인(별명 또는 이름 제공 항목만 선택) | `https://haslalab-community.haslalab.workers.dev/api/oauth/naver/callback` | `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` |

키를 넣은 서비스만 버튼이 켜지고, 넣지 않은 서비스는 흐리게 「관리자가 아직 연결하지 않았습니다」로 보입니다. 로컬 시험에서는 `.dev.vars`의 `OAUTH_MOCK_BASE`로 가짜 로그인 서버를 가리킵니다.

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
| GET | `/api/oauth/:provider/start?return=` | Google · Discord · 네이버 로그인 시작 (브라우저 이동) |
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
