/* Maintainer guide. Loaded only after the arena verifies the current server role.
   Architecture text is documentation, not a live inventory or an authorization boundary. */
(function (scope) {
  'use strict';
  const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const repo = 'https://github.com/HaslaEdu/haslalab.github.io/';
  const copy = {
    ko: {
      title: '서버 구조·운영 가이드', kicker: 'DEVELOPER / OPERATIONS',
      intro: '처음 업무를 맡은 담당자를 위한 HaslaLab 서버 안내입니다. 요청이 어디로 가는지 이해한 뒤, 문제가 생긴 구간부터 확인하세요.',
      date: '구현 기준 2026.10.31 · 구조가 바뀌면 이 가이드도 함께 수정',
      tools: '개발자 도구', model: '모델 테스트', back: '응시·채점 기록', current: '현재 문서',
      map: '한눈에 보는 구조', mapNote: '화살표는 요청·작업의 이동 방향입니다. 응답은 반대 방향으로 돌아옵니다.',
      browser: ['사용자 브라우저', '화면·입력·결과 표시'], static: ['GitHub Pages', 'HTML·JS·기출 자료'],
      gateway: ['Cloudflare Edge Gateway', '가까운 서버에서 공개 캐시·요청 분기'],
      public: ['공개 조회', '캐시 적중 → 즉시 응답', '캐시 없음 → D1 복제본 / 필요시 원본'],
      backend: ['지역 Backend Worker', '인증·개인 조회·모든 쓰기', 'D1 원본 DB · 현재 홍콩(HKG)'],
      jobs: ['실전시험 작업', 'Outbox → Queue → Worker', '외부 OCR·AI → 결과 저장'],
      storage: ['답안·사진 보관', 'D1 / 선택적으로 R2', '보관 정책에 따라 정리'],
      legend: ['공개 데이터', '개인 데이터·쓰기', '시간이 오래 걸리는 작업'],
      paths: '요청별로 따라가기', pathHint: '아래 버튼을 누르면 해당 기능의 처리 순서와 주의점이 바뀝니다.',
      flows: [
        {label:'공개 목록', lead:'게시판·게시글 목록, 비로그인 월간문제·순위의 읽기 경로입니다.',
          steps:[['브라우저','첫 화면의 API 요청을 일찍 시작하고 같은 GET 요청을 합칩니다. 공개 게시글 목록은 짧게 보관한 내용을 먼저 보여 주며 갱신할 수 있습니다.'],
            ['가까운 Gateway','공개 캐시가 있으면 Backend·DB를 호출하지 않습니다. 일반 공개 캐시는 15초, 일부 설정은 300초입니다.'],
            ['읽기 복제본','캐시가 없으면 허용된 공개 SELECT만 D1 Sessions API로 읽습니다. Cloudflare가 사용 가능한 복제본을 고르며 필요하면 원본을 사용할 수 있습니다.'],
            ['일관성 확인','글을 쓴 뒤에는 원본 확인과 북마크를 사용해 이전 버전이 다시 보이지 않게 합니다. 복제 오류·명시적 새로고침은 원본 경로로 보냅니다.']],
          note:'북마크는 “이 버전 이상을 읽기” 위한 값입니다. 로그인·권한을 대신하지 않습니다. 로그인한 월간문제·순위처럼 개인 결과가 섞인 응답은 Backend로 갑니다.'},
        {label:'계정·결제', lead:'계정, 권한, 잔액, 개인 답안, 시험 상태와 모든 변경 요청의 경로입니다.',
          steps:[['Gateway 통과','개인 응답은 공용 캐시에 넣지 않고 Service Binding으로 기존 Backend에 전달합니다.'],
            ['인증·권한 검사','Backend가 현재 세션과 서버 역할을 확인합니다. 버튼 숨김이나 브라우저에 남은 역할 값만으로 접근을 허용하지 않습니다.'],
            ['원본 DB 처리','소유권·마감·잔액 등을 원본 DB에서 확인합니다. 잔액·장부·중복 방지는 원자적 처리 규칙을 유지합니다.'],
            ['화면 갱신','성공 후 관련 공개 캐시·클라이언트 상태를 무효화합니다. 계정이나 언어가 바뀐 뒤 도착한 이전 응답은 화면에 반영하지 않습니다.']],
          note:'원본 경로를 쓰는 이유는 최신 상태와 일관성을 지키기 위해서입니다. “해외 서버는 덜 안전하다”는 의미가 아닙니다. OAuth 콜백·결제 웹훅의 기존 Backend 주소를 임의로 바꾸지 마세요.'},
        {label:'월간문제·실전시험 채점', lead:'월간문제와 실전시험은 서로 다른 채점 경로를 사용합니다.',
          steps:[['월간문제 제출','원본 DB에서 문제별 제출 횟수 제한과 같은 요청의 중복 접수를 확인합니다. 월간 채점은 현재 요청 안에서 처리하며 모든 채점을 Queue로 보내지는 않습니다.'],
            ['실전시험 작업 접수','답안·작업 상태를 저장하고 Outbox에 남깁니다. Queue에는 사진·비밀 키 대신 작은 작업 ID를 보냅니다. 상태 조회는 AI 작업을 기다리지 않습니다.'],
            ['Queue 소비·AI 호출','Worker가 작업을 선점하고 OCR·채점을 수행합니다. 실패는 제한적으로 재시도하며 반복 실패는 Dead Letter Queue에서 확인합니다.'],
            ['저장·복구','결과를 D1에 저장하고 화면이 필요한 동안만 상태를 조회합니다. 매분 복구 작업이 끊긴 전달을 확인하고, 사진 정리는 15분 간격으로 실행합니다.']],
          note:'재시도가 토큰을 다시 차감하거나 결과를 중복 저장하지 않도록 기존 장부·요청 ID·작업 선점 규칙을 유지하세요. 실제 AI 호출은 외부 제공업체 사용료가 발생할 수 있습니다.'},
        {label:'개발자 모델 테스트', lead:'운영 채점과 분리해 OCR·채점 모델 조합을 비교하는 개발자 도구입니다.',
          steps:[['개발자 권한 확인','서버가 현재 admin 역할을 확인합니다. 일반 계정은 테스트 API를 실행할 수 없습니다.'],
            ['조건 준비','테스트 화면에서 문제·배점·채점 기준·답안 사진과 지원되는 모델 조합을 선택합니다. 지원 모델은 현재 서버 설정이 기준입니다.'],
            ['명시적으로 실행','실행 버튼을 눌렀을 때 외부 OCR·채점 API를 호출합니다. 현재 모델 테스트는 요청 안에서 처리하며 실전시험 Queue 경로와 구분합니다.'],
            ['비교·판단','OCR 글, 채점 결과, 사용량·시간·예상비용을 비교합니다. 비용은 공개 단가 기준 추정값이며 실제 청구액과 다를 수 있습니다. 테스트 결과가 운영 모델을 자동으로 바꾸지는 않습니다.']],
          note:'시험 기록·랭킹·토큰 장부는 변경하지 않지만 외부 API 사용료는 발생할 수 있습니다. 공급자 키는 Backend Secret에 두고, 개인정보 없는 검증용 답안을 사용하세요.'}
      ],
      operate: '느리거나 멈췄을 때',
      runbooks: [
        ['화면·API가 느림', ['브라우저 개발자 도구 Network에서 느린 요청 URL·상태 코드·시각·최초/반복 여부를 기록합니다. 정적 파일과 API 요청을 구분합니다.',
          'API의 X-Edge-Cache와 Server-Timing을 확인합니다. hit는 캐시 적중, db는 DB 왕복을 포함한 대기, sql은 DB 내부 실행 시간입니다. gateway·total과 합산하지 마세요. 동시 실행 시간은 겹칠 수 있습니다.',
          'd1_region·d1_colo에서 primary/replica와 지역을 확인합니다. 캐시가 없는 공개 조회와 인증이 필요한 조회를 따로 비교합니다. 이 화면의 읽기 진단은 그 순간의 한 요청만 확인합니다.']],
        ['공개 조회가 계속 원본으로 감', ['Cloudflare의 D1 → 해당 DB → Settings → Read replication 설정과 Gateway의 GLOBAL_PUBLIC_READS=1을 확인합니다. 복제 설정만 켜고 Sessions API를 사용하지 않으면 원본만 읽습니다.',
          '읽기 진단 버튼으로 실제 replica·primary·지역을 확인합니다. 캐시가 없는 공개 요청도 비교하세요. Cache-Control: no-cache는 의도적으로 원본 경로를 선택하므로 복제 성능 측정에 사용하지 않습니다.',
          '복제본이 최신 버전을 따라가는 중이거나 원본이 선택될 수 있습니다. 한 번의 primary 응답만으로 장애라고 판단하지 말고 공개 요청 조건·북마크·Worker 버전을 확인합니다.']],
        ['채점이 대기 상태에서 멈춤', ['작업 ID·현재 상태·마지막 변경 시각부터 확인합니다. 공급자 장애, 사용 한도, 인증 오류와 Queue 전달 오류를 구분합니다.',
          'Cloudflare에서 Queue 소비 상태·재시도·Dead Letter Queue와 Worker 로그를 확인합니다. 동시 처리 수를 늘리기 전에 원인을 확인하세요. 현재 설정은 동시 4개, 배치 1개입니다.',
          '중복 제출·강제 차감으로 복구하지 마세요. 요청 ID·장부·작업 선점을 확인한 뒤 기존 재시도 경로를 사용합니다. 로그를 공유할 때 세션·답안 사진·비밀 키를 제거합니다.']],
        ['수정·배포·인수인계', ['원본 데이터와 생성 파일을 구분합니다. 화면·카탈로그 수정 뒤 node tools/build-site-catalogue.cjs 와 --check를 실행합니다.',
          '변경 범위의 로컬 SQLite·가짜 공급자 테스트와 CI를 통과시킵니다. 속도 확인만을 위해 운영 답안이나 유료 AI 호출을 사용하지 마세요.',
          'main 변경 후 Pages 배포와 Deploy community Worker 결과를 각각 확인합니다. Worker 배포 순서는 Backend → Gateway → PDF Worker입니다. 정적 사이트 배포는 별도이므로 두 배포 사이의 호환성도 확인합니다.',
          '장애 시각·영향 범위·변경 커밋·처리 내용·검증 결과를 남깁니다. 되돌릴 때는 마지막 정상 버전과 데이터·스키마 호환성을 확인하고, 구조 변경은 이 문서에도 반영합니다.']]
      ],
      probeTitle: '현재 공개 읽기 경로 확인', probeText: '누를 때만 SELECT 1 진단을 한 번 실행합니다. 로그인 토큰·답안·AI 호출을 보내지 않으며 자동 반복하지 않습니다.',
      probe: '읽기 경로 확인', probing: '확인 중…', probeIdle: '아직 실행하지 않았습니다. 위 구조도는 문서이며 실시간 상태판이 아닙니다.',
      probeResult: '이번 요청', replica: '읽기 복제본', primary: '원본 DB', unknown: '판정 불가', region: '지역', colo: '처리 지점',
      probeFailed: '진단에 실패했습니다. Network에서 요청 상태와 연결을 확인한 뒤 다시 시도하세요.',
      probeUnsupported: '현재 API에서 복제 진단을 확인할 수 없습니다. 연결한 API 주소와 Worker 배포 버전을 확인하세요.',
      probeFoot: '원본이 응답했다고 복제가 꺼졌다고 단정할 수는 없습니다. 복제 활성화 설정과 실제 요청의 처리 위치는 별도로 확인합니다.',
      sources: '업무별 코드·문서 찾기', responsibility: '담당 구간', files: '먼저 볼 파일',
      sourceRows: [['화면·요청 캐시','arena.js','site-runtime.js'],['공개 분기·복제·일관성','community/src/edge-gateway.js','community/src/public-reader.js','community/src/public-consistency.js'],
        ['공개 SQL·DB 시간 계측','community/src/public-data.js','community/src/d1-timing.js'],['인증·계정·실전시험 API','community/src/index.js'],
        ['Queue·복구','community/src/lab-jobs.js','community/wrangler.toml'],['월간 제출·사진·공개 정책','community/src/monthly-answers.js','community/src/monthly-photos.js','community/src/monthly-policy.js'],
        ['개발자 모델 비교','community/src/model-test-route.js','community/src/model-test.js','community/src/model-test-pricing.js'],['배포·성능 원칙','PERFORMANCE.md','.github/workflows/deploy-worker.yml','.github/workflows/site-performance.yml']],
      handoff: '담당자 인수인계 시 확인', handoffItems: ['저장소·Cloudflare·GitHub Actions 접근 권한과 담당 연락처', '현재 운영 커밋·환경 설정·Secret의 관리 위치 (값은 문서에 복사하지 않기)',
        'D1 복제 설정·캐시 제외 대상·기존 OAuth 및 결제 웹훅 주소', 'Queue·실패 작업·외부 AI 사용량과 비용 확인 위치', '사진 보관·삭제 정책 및 현재 환경의 실제 설정', '최근 정상 배포와 복구 절차·미해결 장애'],
      reference: '공식 참고', refs: ['D1 읽기 복제·북마크','Workers·D1 사용량 요금','Queue 재시도'],
      cost: '이 가이드를 여는 것과 읽기 진단에는 AI 호출이 없습니다. 복제본 자체의 별도 저장·컴퓨팅 요금은 없지만 일반 Workers·D1·Queue 및 외부 AI 사용량은 기존 요금제에 따라 계산합니다.'
    },
    en: {
      title:'Server architecture & operations', kicker:'DEVELOPER / OPERATIONS', intro:'A handover guide for HaslaLab maintainers. Follow the request path, then inspect the part that failed.',
      date:'Implementation reference: 2026-10-31 · Update this guide when the architecture changes', tools:'Developer tools', model:'Model test', back:'My exams', current:'Current guide',
      map:'Architecture at a glance', mapNote:'Arrows show requests and work moving forward. Responses return along the reverse path.',
      browser:['User browser','Interface, input and results'], static:['GitHub Pages','HTML, JS and past papers'], gateway:['Cloudflare Edge Gateway','Nearby public cache and request routing'],
      public:['Public reads','Cache hit → immediate response','Cache miss → D1 replica / primary when needed'], backend:['Regional Backend Worker','Authentication, private reads, all writes','Primary D1 · currently Hong Kong (HKG)'],
      jobs:['Exam jobs','Outbox → Queue → Worker','External OCR/AI → saved result'], storage:['Answers and photos','D1 / optional R2','Cleaned up by retention policy'],
      legend:['Public data','Private data and writes','Long-running work'], paths:'Follow a request', pathHint:'Choose a feature to see its processing steps and operational boundaries.',
      flows:[
        {label:'Public lists',lead:'Boards, post lists, and anonymous monthly problems and rankings.',steps:[
          ['Browser','Start the initial API read early and merge identical GETs. A short-lived public post snapshot may display while it refreshes.'],
          ['Nearby gateway','A public cache hit avoids the backend and DB. Ordinary public entries last 15 seconds; selected settings last 300 seconds.'],
          ['Read replica','Cache misses use allowlisted public SELECTs through D1 Sessions. Cloudflare chooses an available replica and may use primary when needed.'],
          ['Consistency','After a write, primary confirmation and bookmarks prevent older versions from reappearing. Replica failures and explicit refreshes use the primary path.']],
          note:'A bookmark sets a minimum read version; it does not authenticate a user. Signed monthly/ranking responses with personal results stay on the backend.'},
        {label:'Accounts and payments',lead:'Accounts, permissions, balances, private answers, exam state and every mutation.',steps:[
          ['Through the gateway','Private responses bypass the shared cache and reach the existing backend through a Service Binding.'],
          ['Validate access','The backend checks the current session and server role. A hidden button or a role remembered in the browser is not authorization.'],
          ['Primary database','Check ownership, deadlines and balances against primary. Preserve atomic ledger, balance and duplicate-request handling.'],
          ['Update the interface','Invalidate related public/client state after success. Ignore responses that belong to an earlier account, language or route.']],
          note:'Primary is used for current state and consistency, not because a foreign server is inherently less secure. Keep established OAuth callback and payment webhook backend URLs stable.'},
        {label:'Monthly and exam grading',lead:'Monthly problems and timed exams use different grading paths.',steps:[
          ['Monthly submission','Primary checks the attempt limit and request identity. Monthly grading currently runs inside the request; not all grading uses Queues.'],
          ['Accept an exam job','Persist answers and work state, then the outbox. Enqueue a small job ID, not scans or secrets. A status GET does not wait for AI.'],
          ['Queue consumer and AI','A worker claims the job and performs OCR/grading. Retries are bounded; inspect the Dead Letter Queue for repeated failures.'],
          ['Save and recover','Store results in D1 and poll only while the screen needs updates. Recovery runs every minute; photo cleanup runs every 15 minutes.']],
          note:'Preserve request IDs, atomic token ledgers and job claims so retries do not charge twice or duplicate results. External AI calls may incur provider charges.'},
        {label:'Developer model test',lead:'Compare OCR and grading combinations separately from production grading.',steps:[
          ['Verify developer access','The server requires the current admin role. Ordinary accounts cannot run the test API.'],
          ['Prepare a comparison','Supply the problem, rubric, marks and answer images, then choose a currently supported combination. The server configuration determines available models.'],
          ['Run explicitly','Only the run button starts external OCR and grading calls. This test runs inside the request, separately from the exam Queue path.'],
          ['Inspect results','Compare OCR text, marks, usage, timing and estimated cost. Public-price estimates may differ from actual bills. Tests do not automatically change production models.']],
          note:'Tests do not modify exam records, rankings or token ledgers, but provider API charges may apply. Keep provider keys in backend Secrets and use samples without personal information.'}
      ],
      operate:'When requests slow down or stop', runbooks:[
        ['Slow interface or API',['In browser Network tools, record the request URL, status, time and whether it was a first or repeated load. Separate static assets from API requests.',
          'Inspect X-Edge-Cache and Server-Timing. hit means a cache hit; db includes binding/network wait; sql is execution inside D1. Do not add these to gateway/total: concurrent times can overlap.',
          'Inspect d1_region and d1_colo for primary/replica and location. Compare uncached public reads separately from authenticated reads. The diagnostic below describes one request, not overall health.']],
        ['Public reads keep using primary',['Check D1 → database → Settings → Read replication and the gateway GLOBAL_PUBLIC_READS=1 flag. Enabling replication without using the Sessions API still reads only from primary.',
          'Use the diagnostic to inspect actual replica/primary metadata and location. Also compare uncached public requests. Cache-Control: no-cache deliberately chooses primary, so do not use it to benchmark replicas.',
          'Replicas may need to catch up and primary may be selected. One primary response is not sufficient to diagnose an outage: check public-read eligibility, bookmarks and the Worker version.']],
        ['Grading stays pending',['Start with the job ID, state and last update. Distinguish provider outage, quota or authentication errors from queue delivery failures.',
          'Inspect queue consumption, retries, the Dead Letter Queue and Worker logs. Identify the cause before increasing concurrency. Current settings are concurrency 4, batch size 1.',
          'Do not repair by submitting or charging again. Check request IDs, ledgers and job claims, then use the existing retry path. Remove sessions, scans and secrets before sharing logs.']],
        ['Changes, deployment and handover',['Distinguish source datasets from generated files. Run node tools/build-site-catalogue.cjs and --check after relevant UI/catalogue changes.',
          'Run relevant local SQLite/fake-provider tests and CI. Do not use real submissions or paid AI merely to benchmark latency.',
          'Verify Pages and Deploy community Worker separately after main changes. Worker order is Backend → Gateway → PDF Worker; static hosting deploys independently, so keep mixed versions compatible.',
          'Record incident time, impact, commit, actions and validation. Before rollback, check the last healthy version and data/schema compatibility. Update this guide when the architecture changes.']]
      ],
      probeTitle:'Check the current public read path',probeText:'Runs one SELECT 1 diagnostic only when clicked. Sends no login token, answers or AI calls, and never polls automatically.',probe:'Check read path',probing:'Checking…',
      probeIdle:'Not run yet. The architecture diagram is documentation, not a live status board.',probeResult:'This request',replica:'Read replica',primary:'Primary database',unknown:'Unknown',region:'Region',colo:'Serving colo',
      probeFailed:'The diagnostic failed. Inspect the request status and connection in Network tools, then retry.',probeUnsupported:'This API did not report replica diagnostics. Check the selected API URL and Worker deployment.',
      probeFoot:'A primary response alone does not prove replication is disabled. Check both the replication setting and the location serving actual requests.',
      sources:'Find the responsible code',responsibility:'Area',files:'Start here',sourceRows:[
        ['Interface and request cache','arena.js','site-runtime.js'],['Public routing, replication and consistency','community/src/edge-gateway.js','community/src/public-reader.js','community/src/public-consistency.js'],
        ['Public SQL and DB timing','community/src/public-data.js','community/src/d1-timing.js'],['Authentication, accounts and exam API','community/src/index.js'],
        ['Queues and recovery','community/src/lab-jobs.js','community/wrangler.toml'],['Monthly answers, photos and release policy','community/src/monthly-answers.js','community/src/monthly-photos.js','community/src/monthly-policy.js'],
        ['Developer model comparisons','community/src/model-test-route.js','community/src/model-test.js','community/src/model-test-pricing.js'],['Deployment and performance policy','PERFORMANCE.md','.github/workflows/deploy-worker.yml','.github/workflows/site-performance.yml']],
      handoff:'Handover checklist',handoffItems:['Repository, Cloudflare and GitHub Actions access, and responsible contacts','Current release, environment configuration and where Secrets are managed (never copy their values here)',
        'D1 replication, cache exclusions, existing OAuth and payment webhook URLs','Where to inspect queues, failed jobs, AI usage and costs','Photo retention/deletion policy and actual environment settings','Last healthy deployment, recovery steps and unresolved incidents'],
      reference:'Official references',refs:['D1 replication and bookmarks','Workers and D1 usage pricing','Queue retries'],cost:'Opening this guide and running its read diagnostic makes no AI calls. Replicas have no separate storage/compute charge; ordinary Workers, D1, Queue and provider usage remains subject to the existing plans.'
    }
  };
  const css = `<style>
    .sg{--sg-blue:#225f87;--sg-green:#286950;--sg-amber:#86601b;color:var(--ink,#16212e)}
    .sg h1{margin:6px 0 8px}.sg h2{font-size:20px;margin:0 0 10px}.sg h3{font-size:16px;margin:0 0 6px}.sg p{margin:0 0 12px}.sg small,.sg .sg-muted{color:var(--graphite,#5c6b7a)}
    .sg-kicker{font:11px var(--mono,monospace);letter-spacing:.12em;color:var(--graphite,#5c6b7a)}.sg .sg-head{position:static;top:auto;z-index:auto;background:none;border:0;box-shadow:none;backdrop-filter:none;padding:0;max-width:820px;margin:24px 0}.sg-date{font-size:12px}
    .sg-nav{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:22px}.sg-nav [aria-current=page]{border-color:var(--ink);font-weight:600}
    .sg-section{padding:24px 0;border-top:1px solid var(--grid-bold,#b4cadc)}.sg-map{padding:20px;background:var(--paper,#fbfcfd);border:1px solid var(--grid-bold,#b4cadc);border-radius:10px}
    .sg-start,.sg-branches,.sg-tail{display:grid;grid-template-columns:1fr 42px 1.3fr;align-items:stretch;gap:12px}.sg-node{border:1px solid var(--grid-bold,#b4cadc);background:#fff;padding:14px;border-radius:8px;min-width:0}
    .sg-node b,.sg-node small{display:block;overflow-wrap:anywhere}.sg-node small{font-size:12px;line-height:1.55;margin-top:4px}.sg-arrow{display:grid;place-items:center;color:var(--graphite);font-size:22px}.sg-down{text-align:center;margin:8px 0;color:var(--graphite)}
    .sg-branches{grid-template-columns:1fr 1fr}.sg-node.public{border-top:3px solid var(--sg-green)}.sg-node.private{border-top:3px solid var(--sg-blue)}.sg-node.jobs{border-top:3px solid var(--sg-amber)}
    .sg-tail{grid-template-columns:1fr 1fr;margin-top:12px}.sg-static{font-size:12px;text-align:center;margin:10px 0!important}.sg-legend{display:flex;flex-wrap:wrap;gap:18px;font-size:12px;margin-top:15px}.sg-legend span:before{content:'';display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--sg-green);margin-right:7px}.sg-legend span:nth-child(2):before{background:var(--sg-blue)}.sg-legend span:nth-child(3):before{background:var(--sg-amber)}
    .sg-choices{display:flex;flex-wrap:wrap;gap:8px;margin:15px 0}.sg-choices button[aria-pressed=true]{background:var(--ink,#16212e);color:#fff;border-color:var(--ink,#16212e)}.sg-flow{border:1px solid var(--grid-bold,#b4cadc);border-radius:10px;padding:20px;background:#fff}.sg-steps{list-style:none;padding:0;counter-reset:step;display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:18px 0}.sg-steps li{counter-increment:step;position:relative;padding-left:34px;min-width:0}.sg-steps li:before{content:counter(step);position:absolute;left:0;top:0;width:24px;height:24px;display:grid;place-items:center;border:1px solid var(--grid-bold);border-radius:50%;font:12px var(--mono,monospace)}.sg-steps p{font-size:13px;color:var(--graphite);margin:5px 0 0}.sg-note{font-size:13px;padding:12px 14px;border-left:3px solid var(--sg-blue);background:var(--paper,#fbfcfd);margin:0!important}
    .sg details{border:1px solid var(--grid-bold,#b4cadc);border-radius:8px;padding:14px 16px;margin-top:10px;background:#fff}.sg summary{font-weight:600;cursor:pointer}.sg details ol{padding-left:22px;font-size:13px}.sg details li+li{margin-top:10px}.sg-probe{padding:20px;border:1px solid var(--grid-bold,#b4cadc);border-radius:10px;background:#fff}.sg-output{white-space:pre-wrap;overflow-wrap:anywhere;padding:12px;border-radius:6px;background:var(--paper,#fbfcfd);font:12px/1.7 var(--mono,monospace);margin:14px 0}.sg-probe small{display:block;margin-top:12px}
    .sg-table{width:100%;border-collapse:collapse;font-size:13px}.sg-table th,.sg-table td{text-align:left;vertical-align:top;padding:12px 10px;border-bottom:1px solid var(--grid-fine,#dce7f0)}.sg-table th:first-child{width:28%}.sg-table a{display:block;font:12px/1.8 var(--mono,monospace);overflow-wrap:anywhere;color:var(--sg-blue)}.sg-checks{padding-left:22px;font-size:13px}.sg-checks li+li{margin-top:8px}.sg-refs{display:flex;flex-wrap:wrap;gap:10px 20px;font-size:13px}.sg-cost{font-size:12px;color:var(--graphite);margin-top:16px!important}
    @media(max-width:640px){.sg-map,.sg-flow,.sg-probe{padding:14px}.sg-start{grid-template-columns:1fr}.sg-arrow{transform:rotate(90deg);height:24px}.sg-branches,.sg-tail,.sg-steps{grid-template-columns:1fr}.sg-table th:first-child{width:34%}.sg-head h1{font-size:25px}.sg-choices button{flex:1 1 45%}}
    @media(prefers-reduced-motion:reduce){.sg *{scroll-behavior:auto}}
  </style>`;
  const external = (path, label) => `<a href="${repo}blob/main/${path}" target="_blank" rel="noopener noreferrer">${escape(label || path)}</a>`;
  const node = (lines, kind = '') => `<div class="sg-node ${kind}"><b>${escape(lines[0])}</b>${lines.slice(1).map(line => `<small>${escape(line)}</small>`).join('')}</div>`;
  function flowHtml(T, index) {
    const flow = T.flows[index];
    return `<h3>${escape(flow.label)}</h3><p class="sg-muted">${escape(flow.lead)}</p><ol class="sg-steps">${flow.steps.map(([title, body]) => `<li><b>${escape(title)}</b><p>${escape(body)}</p></li>`).join('')}</ol><p class="sg-note">${escape(flow.note)}</p>`;
  }
  function html(language) {
    const T = copy[language === 'en' ? 'en' : 'ko'];
    const refs = ['https://developers.cloudflare.com/d1/best-practices/read-replication/', 'https://developers.cloudflare.com/workers/platform/pricing/', 'https://developers.cloudflare.com/queues/configuration/batching-retries/'];
    return `${css}<article class="sg">
      <nav class="sg-nav" aria-label="${T.tools}"><a class="cmbtn sm" href="#/lab/model-test">${T.model}</a><a class="cmbtn sm" href="#/lab/server-guide" aria-current="page">${T.title}</a><a class="cmbtn sm" href="#/lab">${T.back}</a></nav>
      <header class="sg-head"><span class="sg-kicker">${T.kicker}</span><h1>${T.title}</h1><p>${T.intro}</p><small class="sg-date">${T.date}</small></header>
      <section class="sg-section" aria-labelledby="sgMapTitle"><h2 id="sgMapTitle">${T.map}</h2><p class="sg-muted">${T.mapNote}</p>
        <div class="sg-map" role="group" aria-label="${T.map}"><div class="sg-start">${node(T.browser)}<span class="sg-arrow" aria-hidden="true">→</span>${node(T.gateway)}</div>
          <p class="sg-static">${escape(T.browser[0])} ↔ ${escape(T.static.join(' · '))}</p><div class="sg-down" aria-hidden="true">↓</div>
          <div class="sg-branches">${node(T.public, 'public')}${node(T.backend, 'private')}</div>
          <div class="sg-tail"><div></div><div><div class="sg-down" aria-hidden="true">↓</div>${node(T.jobs, 'jobs')}<div class="sg-down" aria-hidden="true">↕</div>${node(T.storage)}</div></div>
          <div class="sg-legend">${T.legend.map(text => `<span>${escape(text)}</span>`).join('')}</div></div></section>
      <section class="sg-section" aria-labelledby="sgPathsTitle"><h2 id="sgPathsTitle">${T.paths}</h2><p class="sg-muted">${T.pathHint}</p><div class="sg-choices" role="group" aria-label="${T.paths}">${T.flows.map((flow, i) => `<button type="button" class="cmbtn sm" data-guide-flow="${i}" aria-pressed="${i === 0}" aria-controls="sgFlow">${escape(flow.label)}</button>`).join('')}</div><div class="sg-flow" id="sgFlow" data-guide-flow-content aria-live="polite">${flowHtml(T, 0)}</div></section>
      <section class="sg-section" aria-labelledby="sgOperateTitle"><h2 id="sgOperateTitle">${T.operate}</h2>${T.runbooks.map(([title, steps]) => `<details><summary>${escape(title)}</summary><ol>${steps.map(step => `<li>${escape(step)}</li>`).join('')}</ol></details>`).join('')}</section>
      <section class="sg-section"><div class="sg-probe"><h2>${T.probeTitle}</h2><p>${T.probeText}</p><button type="button" class="cmbtn sm" data-guide-probe>${T.probe}</button><div class="sg-output" data-guide-probe-output role="status" aria-live="polite">${T.probeIdle}</div><small>${T.probeFoot}</small></div></section>
      <section class="sg-section" aria-labelledby="sgSourcesTitle"><h2 id="sgSourcesTitle">${T.sources}</h2><table class="sg-table"><thead><tr><th scope="col">${T.responsibility}</th><th scope="col">${T.files}</th></tr></thead><tbody>${T.sourceRows.map(([area, ...files]) => `<tr><th scope="row">${escape(area)}</th><td>${files.map(file => external(file)).join('')}</td></tr>`).join('')}</tbody></table></section>
      <section class="sg-section"><h2>${T.handoff}</h2><ul class="sg-checks">${T.handoffItems.map(text => `<li>${escape(text)}</li>`).join('')}</ul></section>
      <footer class="sg-section"><h2>${T.reference}</h2><div class="sg-refs">${refs.map((url, i) => `<a href="${url}" target="_blank" rel="noopener noreferrer">${T.refs[i]}</a>`).join('')}</div><p class="sg-cost">${T.cost}</p></footer>
    </article>`;
  }
  function mount(root, {language = 'ko', apiBase, alive = () => true, fetchImpl = scope.fetch} = {}) {
    const T = copy[language === 'en' ? 'en' : 'ko'];
    let disposed = false, controller = null, timer = null;
    const current = () => !disposed && alive();
    if (!current()) return {dispose() {}};
    root.innerHTML = html(language);
    const choices = root.querySelectorAll('[data-guide-flow]'), content = root.querySelector('[data-guide-flow-content]');
    for (const button of choices) button.onclick = () => {
      if (!current()) return;
      const index = Number(button.dataset.guideFlow);
      if (!Number.isInteger(index) || !T.flows[index]) return;
      for (const item of choices) item.setAttribute('aria-pressed', String(item === button));
      content.innerHTML = flowHtml(T, index);
    };
    const button = root.querySelector('[data-guide-probe]'), output = root.querySelector('[data-guide-probe-output]');
    button.onclick = async () => {
      if (!current() || controller) return;
      controller = new AbortController();
      const signal = controller.signal;
      timer = setTimeout(() => controller?.abort(), 15000);
      button.disabled = true; button.textContent = T.probing; output.textContent = T.probing;
      try {
        const endpoint = new URL(String(apiBase).replace(/\/$/, '') + '/api/health?read_region_check=1');
        if (!['http:', 'https:'].includes(endpoint.protocol) || endpoint.username || endpoint.password) throw new Error('invalid API base');
        const response = await fetchImpl(endpoint.href, {method:'GET', credentials:'omit', cache:'no-store', referrerPolicy:'no-referrer', signal});
        if (!response.ok) throw new Error('probe failed');
        const data = await response.json();
        if (!current()) return;
        if (data?.supported !== true || typeof data.replica !== 'boolean' || typeof data.primary !== 'boolean') {
          output.textContent = T.probeUnsupported; return;
        }
        const list = values => Array.isArray(values) ? values.filter(x => typeof x === 'string').slice(0, 6).map(x => x.slice(0, 32)).join(', ') || '—' : '—';
        const source = [data.replica && T.replica, data.primary && T.primary].filter(Boolean).join(' + ') || T.unknown;
        output.textContent = `${T.probeResult}: ${source}\n${T.region}: ${list(data.regions)}\n${T.colo}: ${list(data.colos)}\n${new Intl.DateTimeFormat(language === 'en' ? 'en-GB' : 'ko-KR', {dateStyle:'medium', timeStyle:'medium', timeZone:'Asia/Seoul'}).format(new Date())} KST`;
      } catch (_) { if (current()) output.textContent = T.probeFailed; }
      finally {
        clearTimeout(timer); timer = null; controller = null;
        if (current()) { button.disabled = false; button.textContent = T.probe; }
      }
    };
    return {dispose() { disposed = true; clearTimeout(timer); controller?.abort(); }};
  }
  scope.HL_SERVER_GUIDE = Object.freeze({html, mount});
})(typeof window === 'object' ? window : globalThis);
