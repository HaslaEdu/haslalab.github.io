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
5. **Settings → Domains & Routes**에서 workers.dev를 켜고, 그 주소를 `index.html`의 `COMMUNITY_API`에 넣습니다. (지금: `https://haslalab-community.mgsnew88.workers.dev`)

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
