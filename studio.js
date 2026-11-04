/* HaslaLab Problem Studio. Public UI: credentials for model providers stay on the server. */
(function () {
  'use strict';
  const DEFAULT_API = 'https://haslalab-community.haslalab.workers.dev';
  const $ = id => document.getElementById(id);
  const readStore = key => { try { return localStorage.getItem(key) || ''; } catch (_) { return ''; } };
  const writeStore = (key, value) => { try { value ? localStorage.setItem(key, value) : localStorage.removeItem(key); } catch (_) {} };
  const studioParams = new URLSearchParams(location.search);
  const embedded = studioParams.get('embed') === '1' && window.parent !== window;
  if (embedded) document.body.classList.add('studio-embedded');
  const subjects = ['math', 'physics', 'chemistry', 'biology', 'astronomy', 'informatics'];
  const modes = ['digitize', 'generate', 'restore'];
  const activeStatuses = new Set(['queued', 'running']);
  const imageTypes = new Set(['image/png', 'image/jpeg', 'image/webp', 'image/svg+xml']);
  const TEXT = {
    ko: {
      skip: '작업 영역으로 건너뛰기', library: '문제 라이브러리', practice: '실전 연습', signIn: '로그인',
      heading: '한 장에서, 다음 문제까지.', intro: '올림피아드 문제를 편집 가능한 글과 수식으로 정리하고, 사진이나 원하는 주제를 바탕으로 새 문제를 만들어 보세요.',
      newWork: '새 작업', mode: '작업 선택', digitize: '문제 디지털화', digitizeHint: '글·수식·그림을 정리해요',
      generate: '문제 제작', generateHint: '사진이나 요청을 바탕으로', restore: '그림 제작', restoreHint: '사진으로 도형·그래프 재구성', takePhoto: '사진 촬영', search: '문제 검색', searchHint: '문제은행에서 글로 찾기',
      sourceImage: '원본 이미지', upload: '사진을 놓거나 선택하세요', uploadHint: 'PNG · JPG · WebP / 붙여넣기 가능',
      sourceImageOptional: '원본 이미지 (선택)', generationRequest: '제작 요청', requestRequired: '사진 없으면 5자 이상',
      generateNote: '사진 없이도 제작할 수 있어요. 과목과 원하는 주제·조건을 5자 이상 적어 주세요.',
      generatePlaceholder: '예: 에너지 보존을 이용하는 고등학교 물리 올림피아드 문제를 만들어 주세요. 필요한 조건과 그림도 포함해 주세요.',
      generateInput: '원본 사진을 선택하거나, 만들고 싶은 문제의 주제와 조건을 5자 이상 적어 주세요.', standardDifficulty: '기본 난이도',
      replaceImage: '다른 사진 선택', subject: '과목', outputLanguage: '결과 언어', math: '수학', physics: '물리', chemistry: '화학',
      biology: '생물', astronomy: '천문', informatics: '정보', difficulty: '난이도', similar: '원본과 비슷하게', easier: '조금 쉽게', harder: '더 어렵게',
      count: '문제 수', instruction: '추가 요청', optional: '선택', instructionPlaceholder: '유지할 조건, 필요한 그림, 바꾸고 싶은 부분을 적어 주세요.',
      start: '작업 시작', sending: '요청을 보내는 중…', working: '작업을 진행하고 있어요',
      uploadNote: '시작하면 입력한 자료와 요청이 처리 서버로 전송됩니다. 결과에서 수식과 조건을 확인해 주세요.',
      recentWork: '최근 작업', refresh: '새로고침', historySignIn: '로그인하면 이전 작업을 볼 수 있어요.', historyEmpty: '아직 작업이 없습니다.',
      workspace: '작업 공간', retry: '같은 설정으로 다시', cancel: '작업 취소', cancelling: '취소하는 중…',
      emptyEyebrow: 'YOUR NEXT PROBLEM STARTS HERE', emptyHeading: '문제 한 장을 올려 보세요.',
      emptyBody: '원본과 결과를 나란히 보고,\n필요한 문제와 그림을 내려받을 수 있어요.', original: '원본', enlarge: '크게 보기', result: '결과',
      sourceUnavailable: '원본 이미지를 불러오지 못했습니다.', preparing: '문제와 수식을 정리하고 있습니다.',
      exportHint: '결과를 확인하고 원하는 형식으로 보관하세요.', includeSolutions: '정답·해설도 인쇄', print: '인쇄 / PDF', help: '질문·의견 남기기 ↗',
      accountHint: '기존 HaslaLab 계정으로 작업을 이어가세요.', username: '아이디', password: '비밀번호', otherLogin: '소셜 로그인 · 회원가입 ↗',
      queued: '대기 중', running: '진행 중', completed: '완료', needs_review: '확인 필요', failed: '작업 실패', cancelled: '취소됨', expired: '보관 기간 만료',
      reviewNeeded: '조건·수식을 확인하세요', reviewPassed: '검토 완료', answer: '정답 보기', explanation: '해설 보기',
      figure: '그림', downloadFigure: '그림 저장', loadingFigure: '그림을 불러오는 중…', figureError: '그림을 불러오지 못했습니다.',
      noProblems: '표시할 문제가 없습니다. 다른 사진으로 다시 시도해 주세요.', chooseImage: '원본 사진을 먼저 선택해 주세요.',
      badImage: 'PNG, JPG, WebP 이미지 한 장을 선택해 주세요.', imageTooLarge: '사진이 너무 큽니다. 최대 {size}MB까지 올릴 수 있습니다.',
      network: '서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.', unavailable: '현재 작업을 시작할 수 없습니다. 잠시 후 다시 확인해 주세요.',
      loginRequired: '로그인한 뒤 작업을 시작해 주세요.', sessionExpired: '로그인이 만료되었습니다. 다시 로그인해 주세요.',
      badCredentials: '아이디 또는 비밀번호가 맞지 않습니다.', rateLimited: '요청이 많습니다. 잠시 후 다시 시도해 주세요.',
      jobFailed: '작업을 마치지 못했습니다. 원본을 확인하고 다시 시도해 주세요.', cancelledHint: '작업이 취소되었습니다. 같은 사진으로 다시 시작할 수 있어요.',
      pollError: '진행 상태를 다시 확인하고 있습니다. 연결이 돌아오면 자동으로 이어집니다.',
      historyError: '이전 작업을 불러오지 못했습니다. 새로고침으로 다시 확인해 주세요.', unknownStatus: '상태 확인 중',
      preparingExport: '그림과 파일을 준비하고 있습니다…', exportFailed: '파일을 준비하지 못했습니다. 다시 시도해 주세요.',
      markdownImages: 'Markdown과 그림을 ZIP 파일로 저장했습니다.', retrySource: '이 작업의 원본을 불러오지 못했습니다. 사진을 다시 선택해 주세요.',
      signedIn: '로그인했습니다.', removeImage: '사진 지우기', close: '닫기', created: '시작', updated: '최근 갱신',
      adminOnly: '현재 관리자 계정으로 시험 운영 중입니다.', badInput: '입력 항목과 추가 요청 길이를 확인해 주세요.',
      imageDimensions: '사진의 가로·세로 크기가 너무 큽니다. 문제 영역을 잘라 다시 올려 주세요.',
      quotaReached: '오늘의 제작 한도에 도달했거나 진행 중인 작업이 있습니다. 잠시 후 확인해 주세요.',
      expiredHint: '보관 기간이 끝난 작업입니다. 원본 사진을 다시 올려 새 작업을 시작해 주세요.',
      limits: '이미지 {size}MB 이하 · 하루 {daily}회 · 작업 보관 {hours}시간',
      stage: { queued: '앞선 작업이 끝나기를 기다리고 있습니다.', prepare: '원본을 준비하고 있습니다.', preparing: '원본을 준비하고 있습니다.',
        validate: '입력 내용을 확인하고 있습니다.', reading: '문제의 조건과 수식을 읽고 있습니다.', read: '문제의 조건과 수식을 읽고 있습니다.',
        ocr: '글자와 수식을 읽고 있습니다.', transcribe: '문제를 디지털 전사하고 있습니다.', transcribing: '문제를 디지털 전사하고 있습니다.',
        digitize: '문제를 디지털 전사하고 있습니다.', analyzing: '문제의 핵심 개념을 살펴보고 있습니다.', analyze: '문제의 핵심 개념을 살펴보고 있습니다.',
        generate: '새 문제를 만들고 있습니다.', generating: '새 문제를 만들고 있습니다.', restore: '그림을 복원하고 있습니다.', restoring: '그림을 복원하고 있습니다.',
        figures: '그림을 정리하고 있습니다.', illustration: '그림을 정리하고 있습니다.', verify: '조건과 정답을 검토하고 있습니다.', verifying: '조건과 정답을 검토하고 있습니다.',
        write: '문제의 조건과 수식을 정리하고 있습니다.', solve: '문제를 독립적으로 풀어 조건과 정답을 확인하고 있습니다.',
        repair: '검토 결과에 따라 문제를 다듬고 있습니다.', render: '문제와 그림을 준비하고 있습니다.', audit: '복원한 그림을 원본과 비교하고 있습니다.',
        review: '조건과 정답을 검토하고 있습니다.', save: '결과를 저장하고 있습니다.', saving: '결과를 저장하고 있습니다.', done: '결과가 준비되었습니다.' }
    },
    en: {
      skip: 'Skip to workspace', library: 'Problem library', practice: 'Exam practice', signIn: 'Sign in',
      heading: 'One image. Your next problem.', intro: 'Turn an olympiad problem into editable text and equations, or create new problems from an image or a topic you describe.',
      newWork: 'New work', mode: 'Choose a task', digitize: 'Digitize a problem', digitizeHint: 'Text, equations and figures',
      generate: 'Create a problem', generateHint: 'From an image or your request', restore: 'Create a figure', restoreHint: 'Reconstruct a figure from a photo', takePhoto: 'Take a photo', search: 'Search problems', searchHint: 'Search the problem library',
      sourceImage: 'Source image', upload: 'Drop an image or choose a file', uploadHint: 'PNG · JPG · WebP / paste an image',
      sourceImageOptional: 'Source image (optional)', generationRequest: 'Problem request', requestRequired: '5+ characters without an image',
      generateNote: 'You can create problems without an image. Describe the topic and conditions in at least 5 characters.',
      generatePlaceholder: 'For example: Create a high-school physics olympiad problem using conservation of energy. Include the necessary conditions and diagrams.',
      generateInput: 'Choose a source image or describe the topic and conditions in at least 5 characters.', standardDifficulty: 'Standard difficulty',
      replaceImage: 'Choose another image', subject: 'Subject', outputLanguage: 'Output language', math: 'Mathematics', physics: 'Physics', chemistry: 'Chemistry',
      biology: 'Biology', astronomy: 'Astronomy', informatics: 'Informatics', difficulty: 'Difficulty', similar: 'Similar to the original', easier: 'Easier', harder: 'Harder',
      count: 'Problems', instruction: 'Additional request', optional: 'Optional', instructionPlaceholder: 'Describe conditions to keep, figures you need, or changes you would like.',
      start: 'Start task', sending: 'Sending your request…', working: 'A task is in progress',
      uploadNote: 'Starting sends your materials and request to the processing server. Check the equations and conditions in the result.',
      recentWork: 'Recent work', refresh: 'Refresh', historySignIn: 'Sign in to see your previous work.', historyEmpty: 'No tasks yet.',
      workspace: 'Workspace', retry: 'Run again', cancel: 'Cancel task', cancelling: 'Cancelling…',
      emptyEyebrow: 'YOUR NEXT PROBLEM STARTS HERE', emptyHeading: 'Start with a problem image.',
      emptyBody: 'Compare the original with your result,\nthen save the problems and figures you need.', original: 'Original', enlarge: 'Enlarge', result: 'Result',
      sourceUnavailable: 'The source image could not be loaded.', preparing: 'Preparing the problem and equations.',
      exportHint: 'Check your result and save it in your preferred format.', includeSolutions: 'Print answers and solutions', print: 'Print / PDF', help: 'Questions & feedback ↗',
      accountHint: 'Continue with your existing HaslaLab account.', username: 'Username', password: 'Password', otherLogin: 'Social sign-in · Create account ↗',
      queued: 'Queued', running: 'In progress', completed: 'Completed', needs_review: 'Needs review', failed: 'Failed', cancelled: 'Cancelled', expired: 'Expired',
      reviewNeeded: 'Check conditions and equations', reviewPassed: 'Review complete', answer: 'Show answer', explanation: 'Show solution',
      figure: 'Figure', downloadFigure: 'Save figure', loadingFigure: 'Loading the figure…', figureError: 'The figure could not be loaded.',
      noProblems: 'No problems to display. Please try another image.', chooseImage: 'Choose a source image first.',
      badImage: 'Choose one PNG, JPG or WebP image.', imageTooLarge: 'This image is too large. The maximum is {size}MB.',
      network: 'Could not reach the server. Please try again shortly.', unavailable: 'Tasks are unavailable at the moment. Please check again later.',
      loginRequired: 'Sign in to start a task.', sessionExpired: 'Your session expired. Please sign in again.',
      badCredentials: 'The username or password is incorrect.', rateLimited: 'Too many requests. Please try again shortly.',
      jobFailed: 'This task could not be completed. Check the source and try again.', cancelledHint: 'The task was cancelled. You can start again with the same image.',
      pollError: 'Reconnecting to check progress. Your task will reappear when the connection returns.',
      historyError: 'Previous work could not be loaded. Try refreshing.', unknownStatus: 'Checking status',
      preparingExport: 'Preparing your files and figures…', exportFailed: 'Could not prepare the file. Please try again.',
      markdownImages: 'Saved Markdown and figures together in a ZIP file.', retrySource: 'The source for this task could not be loaded. Please select the image again.',
      signedIn: 'Signed in.', removeImage: 'Remove image', close: 'Close', created: 'Started', updated: 'Updated',
      adminOnly: 'Studio is currently being tested with administrator accounts.', badInput: 'Check the input fields and the length of your additional request.',
      imageDimensions: 'The image dimensions are too large. Crop to the problem area and try again.',
      quotaReached: 'You have reached the daily limit or have tasks in progress. Please check again later.',
      expiredHint: 'This task has reached its retention limit. Upload the original image to start a new task.',
      limits: 'Images up to {size}MB · {daily} tasks/day · Saved for {hours} hours',
      stage: { queued: 'Waiting for the previous tasks to finish.', prepare: 'Preparing your source.', preparing: 'Preparing your source.',
        validate: 'Checking the input.', reading: 'Reading the conditions and equations.', read: 'Reading the conditions and equations.',
        ocr: 'Reading the text and equations.', transcribe: 'Digitizing your problem.', transcribing: 'Digitizing your problem.', digitize: 'Digitizing your problem.',
        analyzing: 'Examining the core ideas.', analyze: 'Examining the core ideas.', generate: 'Creating new problems.', generating: 'Creating new problems.',
        restore: 'Restoring your figure.', restoring: 'Restoring your figure.', figures: 'Preparing the figures.', illustration: 'Preparing the figures.',
        write: 'Organizing the conditions and equations.', solve: 'Solving independently to check the conditions and answer.',
        repair: 'Refining the problem after review.', render: 'Preparing the problem and figures.', audit: 'Comparing the restored figure with the source.',
        verify: 'Checking conditions and answers.', verifying: 'Checking conditions and answers.', review: 'Checking conditions and answers.',
        save: 'Saving your result.', saving: 'Saving your result.', done: 'Your result is ready.' }
    }
  };
  const state = {
    lang: ['ko','en'].includes(studioParams.get('lang')) ? studioParams.get('lang') : readStore('hlLang') === 'en' ? 'en' : 'ko',
    user: null, capabilities: null, file: null, fileUrl: '', jobs: [], selected: null,
    creating: false, cancelling: false, exporting: false, timer: null, pollFailures: 0, epoch: 0,
    renderKey: '', originalUrl: '', sourceInputs: new Map(), assets: new Map(), toastTimer: null, pendingSubmission: null,
    sessionVersion: 0, requests: new Set()
  };
  const t = key => TEXT[state.lang][key] || key;
  const text = (value, max = 100000) => String(value == null ? '' : value).slice(0, max);
  const node = (tag, className, value) => { const e = document.createElement(tag); if (className) e.className = className; if (value != null) e.textContent = value; return e; };
  const token = () => readStore('hlCmTok');
  function apiBase() {
    try {
      const o = readStore('hlCmApi') || '';
      const u = new URL(/^(?:https?:\/\/(?:localhost|127\.0\.0\.1)(?::\d+)?|https:\/\/[a-z0-9-]+\.haslalab\.workers\.dev)\/?$/.test(o) ? o : DEFAULT_API);
      const localHosts = ['localhost', '127.0.0.1', '[::1]'];
      if (u.origin === DEFAULT_API || localHosts.includes(location.hostname) && ['http:', 'https:'].includes(u.protocol) && localHosts.includes(u.hostname)) return u.origin;
    } catch (_) {}
    return DEFAULT_API;
  }
  function localError(key, status = 0) { const e = new Error(key); e.code = key; e.status = status; return e; }
  function errorMessage(error) {
    const code = text(typeof error === 'string' ? error : error && (error.code || error.error || error.message), 150).toLowerCase();
    if (['chooseimage', 'badimage', 'network', 'exportfailed', 'retrysource'].includes(code)) return t({ chooseimage: 'chooseImage', badimage: 'badImage', exportfailed: 'exportFailed', retrysource: 'retrySource', network: 'network' }[code]);
    if (/bad_credentials|invalid_credentials/.test(code)) return t('badCredentials');
    if (code === 'admin_only') return t('adminOnly');
    if (code === 'bad_input' || code === 'request_conflict') return t('badInput');
    if (code === 'image_required') return t('chooseImage');
    if (code === 'image_dimensions') return t('imageDimensions');
    if (code === 'quota_reached') return t('quotaReached');
    if (code === 'expired') return t('expiredHint');
    if (/login_required|unauthorized|session_expired/.test(code) || error && error.status === 401) return t('sessionExpired');
    if (/rate|too_many/.test(code) || error && error.status === 429) return t('rateLimited');
    if (/image_too_large|payload_too_large|image_limit|body_too_large/.test(code) || error && error.status === 413) return imageLimitMessage();
    if (/bad_image|unsupported_image/.test(code)) return t('badImage');
    if (/unavailable|not_configured|studio_off|not_enabled/.test(code) || error && [404, 503].includes(error.status)) return t('unavailable');
    return t('jobFailed');
  }
  function message(id, value) { $(id).textContent = value || ''; $(id).hidden = !value; }
  function toast(value) { clearTimeout(state.toastTimer); message('toast', value); state.toastTimer = setTimeout(() => message('toast', ''), 4500); }
  async function request(path, options = {}) {
    const auth = token(), base = apiBase(), version = state.sessionVersion, headers = new Headers(options.headers || {});
    const current = () => version === state.sessionVersion && token() === auth && apiBase() === base;
    const assertCurrent = () => { if (!current()) throw localError('account_changed'); };
    const controller = new AbortController(); state.requests.add(controller);
    const { binary, ...fetchOptions } = options;
    if (auth) headers.set('Authorization', 'Bearer ' + auth);
    let timeout;
    const perform = async () => {
      let response;
      try { response = await fetch(base + '/api' + path, { ...fetchOptions, headers, signal: controller.signal, cache: 'no-store', credentials: 'omit' }); }
      catch (_) { throw localError(current() ? 'network' : 'account_changed'); }
      assertCurrent();
      if (!response.ok) {
        const data = await response.json().catch(() => ({})); assertCurrent();
        if (response.status === 401 && auth) { writeStore('hlCmTok', ''); resetWorkspace(); }
        throw localError(data.error && typeof data.error === 'object' ? data.error.code : data.error || data.code || 'server_error', response.status);
      }
      if (binary) {
        const type = (response.headers.get('content-type') || '').split(';')[0].trim().toLowerCase();
        if (!imageTypes.has(type) || Number(response.headers.get('content-length') || 0) > 32 * 1048576) throw localError('bad_image');
        const blob = await response.blob(); assertCurrent();
        if (blob.size > 32 * 1048576) throw localError('bad_image');
        return { blob, type };
      }
      const data = await response.json().catch(() => { throw localError(current() ? 'network' : 'account_changed'); }); assertCurrent(); return data;
    };
    try {
      return await Promise.race([perform(), new Promise((_, reject) => { timeout = setTimeout(() => {
        controller.abort(); reject(localError(current() ? 'network' : 'account_changed'));
      }, 30000); })]);
    } finally { clearTimeout(timeout); state.requests.delete(controller); }
  }
  function dateValue(v) { const n = typeof v === 'number' ? v < 1e12 ? v * 1000 : v : v; const d = new Date(n); return Number.isNaN(d.getTime()) ? null : d; }
  function dateLabel(v) { const d = dateValue(v); return d ? new Intl.DateTimeFormat(state.lang === 'en' ? 'en-GB' : 'ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(d) : ''; }
  function statusLabel(status) { return Object.hasOwn(TEXT[state.lang], status) && typeof t(status) === 'string' ? t(status) : t('unknownStatus'); }
  function modeValue() { return document.querySelector('input[name="mode"]:checked').value; }
  function isActive(job) { return job && activeStatuses.has(job.status); }
  function currentJob() { return state.jobs.find(j => String(j.id) === String(state.selected)) || null; }
  function maxBytes() { const v = state.capabilities && (state.capabilities.maxImageBytes || state.capabilities.limits?.maxImageBytes); return Number.isFinite(Number(v)) && Number(v) > 0 ? Number(v) : 4 * 1024 * 1024; }
  function imageLimitMessage() { return t('imageTooLarge').replace('{size}', String(Math.round(maxBytes() / 1048576 * 10) / 10)); }
  function renderLimits() {
    const cap = state.capabilities;
    $('limitsNote').hidden = !cap || !Number.isFinite(Number(cap.dailyLimit)) || !Number.isFinite(Number(cap.retentionHours));
    if (!$('limitsNote').hidden) $('limitsNote').textContent = t('limits').replace('{size}', String(Math.round(maxBytes() / 1048576 * 10) / 10)).replace('{daily}', String(cap.dailyLimit)).replace('{hours}', String(cap.retentionHours));
  }
  function updateSubmit() {
    const active = isActive(currentJob());
    $('submitJob').disabled = state.creating || active || state.capabilities?.available === false;
    $('submitJob').firstElementChild.textContent = state.creating ? t('sending') : active ? t('working') : t('start');
    $('cancelJob').disabled = state.cancelling;
    $('cancelJob').textContent = state.cancelling ? t('cancelling') : t('cancel');
    ['exportMarkdown', 'exportJson', 'printResult'].forEach(id => { $(id).disabled = state.exporting; });
  }
  function updateAccount() {
    $('accountButton').textContent = state.user ? text(state.user.nickname || state.user.username || 'HaslaLab', 40) : token() ? (state.lang === 'ko' ? '내 계정' : 'My account') : t('signIn');
    $('removeImage').setAttribute('aria-label', t('removeImage'));
    ['closeLogin', 'closeImage'].forEach(id => $(id).setAttribute('aria-label', t('close')));
  }
  function applyLanguage() {
    document.documentElement.lang = state.lang;
    document.title = (state.lang === 'en' ? 'Problem Studio' : '문제 제작소') + ' · HaslaLab';
    document.querySelectorAll('[data-i18n]').forEach(e => { e.textContent = t(e.dataset.i18n); });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(e => { e.placeholder = t(e.dataset.i18nPlaceholder); });
    $('uiLanguage').textContent = state.lang === 'en' ? '한국어' : 'EN';
    $('captureInput').setAttribute('aria-label',t('takePhoto'));
    updateSearchLink();
    $('sourceImage').alt = t('original');
    $('dropZone').querySelector('strong').textContent = state.file ? t('replaceImage') : t('upload');
    state.renderKey = ''; updateMode(); updateAccount(); updateSubmit(); renderHistory(); renderSelected(); renderLimits();
    if (state.capabilities?.available === false) message('serviceNotice', t('unavailable'));
  }
  function updateSearchLink() {
    const link=$('problemSearchLink');if(!link)return;
    const url=new URL('./',location.href);url.searchParams.set('lang',state.lang);
    url.searchParams.set('theme',document.documentElement.dataset.theme==='dark'?'dark':'light');
    url.hash='/learn/physics/search';link.href=url.href;
  }
  if(typeof MutationObserver==='function')new MutationObserver(updateSearchLink).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
  function updateMode() {
    const generation = modeValue() === 'generate';
    document.querySelectorAll('.generation-option').forEach(e => { e.hidden = !generation; });
    $('sourceImageLabel').textContent = t(generation ? 'sourceImageOptional' : 'sourceImage');
    $('instructionTitle').textContent = t(generation ? 'generationRequest' : 'instruction');
    $('instructionOptional').textContent = t(generation && !state.file ? 'requestRequired' : 'optional');
    $('instruction').placeholder = t(generation ? 'generatePlaceholder' : 'instructionPlaceholder');
    $('generateNote').hidden = !generation;
    $('difficulty').querySelector('option[value="similar"]').textContent = t(generation && !state.file ? 'standardDifficulty' : 'similar');
  }
  function selectFile(file) {
    if (!file) return;
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) { message('formError', t('badImage')); return; }
    if (file.size > maxBytes()) { message('formError', imageLimitMessage()); return; }
    if (state.fileUrl) URL.revokeObjectURL(state.fileUrl);
    state.file = file; state.fileUrl = URL.createObjectURL(file);
    $('fileThumbnail').src = state.fileUrl; $('fileName').textContent = text(file.name, 180);
    $('fileSize').textContent = file.size < 1048576 ? Math.ceil(file.size / 1024) + ' KB' : (file.size / 1048576).toFixed(1) + ' MB';
    $('selectedFile').hidden = false; $('dropZone').classList.add('has-file');
    $('dropZone').querySelector('strong').textContent = t('replaceImage'); message('formError', ''); updateMode();
  }
  function removeFile() {
    if (state.fileUrl) URL.revokeObjectURL(state.fileUrl);
    state.file = null; state.fileUrl = ''; $('imageInput').value = ''; $('captureInput').value = ''; $('fileThumbnail').removeAttribute('src');
    $('selectedFile').hidden = true; $('dropZone').classList.remove('has-file'); $('dropZone').querySelector('strong').textContent = t('upload'); updateMode();
  }
  function safeJob(job) { return job && typeof job === 'object' && job.id != null && String(job.id).length <= 180 ? job : null; }
  function upsertJob(job) {
    if (!safeJob(job)) throw localError('server_error');
    const old = state.jobs.find(j => String(j.id) === String(job.id));
    const next = { ...old, ...job };
    if (old && job.originalAssetId === null && !job.options && !job.result) next.originalAssetId = old.originalAssetId;
    state.jobs = [next, ...state.jobs.filter(j => String(j.id) !== String(job.id))].sort((a, b) => (dateValue(b.createdAt)?.getTime() || 0) - (dateValue(a.createdAt)?.getTime() || 0)).slice(0, 40);
    return next;
  }
  function originalAssetId(job) {
    const assets = Array.isArray(job.assets) ? job.assets : [];
    const original = assets.find(a => a && ['original', 'source', 'input'].includes(a.kind || a.role));
    return job.originalAssetId || job.sourceAssetId || job.source?.assetId || job.input?.assetId || original?.assetId || original?.id || 'original';
  }
  function hasOriginal(job) {
    const saved = state.sourceInputs.get(String(job.id));
    if (saved) return !!saved.file;
    return !(job.mode === 'generate' && job.originalAssetId == null);
  }
  async function asset(job, assetId) {
    const id = text(assetId, 180), key = String(job.id) + ':' + id;
    if (!id) throw localError('bad_image');
    if (!state.assets.has(key)) {
      const task = (async () => {
        const { blob, type } = await request('/studio/jobs/' + encodeURIComponent(job.id) + '/assets/' + encodeURIComponent(id), { binary: true });
        return { blob, url: URL.createObjectURL(blob), type };
      })();
      state.assets.set(key, task);
      task.catch(() => { if (state.assets.get(key) === task) state.assets.delete(key); });
    }
    return state.assets.get(key);
  }
  function clearAssets() { state.assets.forEach(p => p.then(a => URL.revokeObjectURL(a.url), () => {})); state.assets.clear(); }
  function resetWorkspace() {
    ++state.sessionVersion; ++state.epoch; clearTimeout(state.timer); clearAssets();
    state.requests.forEach(controller => controller.abort()); state.requests.clear();
    if (state.selected) { const u = new URL(location.href); u.searchParams.delete('job'); history.replaceState(null, '', u.pathname + u.search + u.hash); }
    state.jobs = []; state.selected = null; state.user = null; state.renderKey = ''; state.originalUrl = '';
    state.sourceInputs.clear(); state.pendingSubmission = null; state.creating = false; state.cancelling = false; state.exporting = false;
    if ($('imageDialog').open) $('imageDialog').close();
    $('sourceImage').removeAttribute('src'); $('resultContent').replaceChildren();
    message('pageMessage', ''); renderHistory(); renderSelected(); updateAccount();
  }
  async function showOriginal(job, epoch) {
    $('sourceImage').hidden = true; $('sourceImage').removeAttribute('src'); $('sourceUnavailable').hidden = true; state.originalUrl = '';
    if (!hasOriginal(job)) return;
    try {
      const file = state.sourceInputs.get(String(job.id))?.file;
      let data;
      if (file) {
        const key = job.id + ':local-original';
        if (!state.assets.has(key)) state.assets.set(key, Promise.resolve({ blob: file, url: URL.createObjectURL(file), type: file.type }));
        data = await state.assets.get(key);
      } else data = await asset(job, originalAssetId(job));
      if (state.epoch !== epoch) return;
      state.originalUrl = data.url; $('sourceImage').src = data.url; $('sourceImage').hidden = false;
    } catch (_) { if (state.epoch === epoch) $('sourceUnavailable').hidden = false; }
  }
  function renderHistory() {
    $('jobHistory').replaceChildren();
    $('historyEmpty').hidden = !!state.jobs.length;
    $('historyEmpty').textContent = token() ? t('historyEmpty') : t('historySignIn');
    state.jobs.slice(0, 20).forEach(job => {
      const li = node('li'), b = node('button', 'history-item' + (String(job.id) === String(state.selected) ? ' selected' : ''));
      b.type = 'button'; b.setAttribute('aria-current', String(job.id) === String(state.selected) ? 'true' : 'false');
      const icon = node('span', 'history-icon', job.mode === 'generate' ? '↗' : job.mode === 'restore' ? '◇' : '¶'); icon.setAttribute('aria-hidden', 'true');
      const body = node('span', 'history-body');
      body.append(node('span', 'history-title', text(job.result?.title || job.title || t(modes.includes(job.mode) ? job.mode : 'digitize'), 120)));
      const meta = node('span', 'history-meta'), dot = node('i', 'status-dot ' + (activeStatuses.has(job.status) || ['completed', 'needs_review', 'failed', 'cancelled'].includes(job.status) ? job.status : ''));
      dot.setAttribute('aria-hidden', 'true'); meta.append(dot, node('span', '', statusLabel(job.status)), node('span', '', dateLabel(job.createdAt))); body.append(meta); b.append(icon, body);
      b.addEventListener('click', () => openJob(job.id)); li.append(b); $('jobHistory').append(li);
    });
  }
  function mathText(value, className = 'math-text') {
    const host = node('div', className), source = text(value), pattern = /\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]|\\\(([\s\S]+?)\\\)|\$([^$\n]+?)\$/g;
    let cursor = 0, match;
    while ((match = pattern.exec(source))) {
      let slashes = 0; for (let i = match.index - 1; i >= 0 && source[i] === '\\'; i--) slashes++;
      if (slashes % 2) continue;
      host.append(document.createTextNode(source.slice(cursor, match.index)));
      const span = node('span'), formula = match[1] || match[2] || match[3] || match[4], display = !!(match[1] || match[2]);
      try {
        if (!window.katex || formula.length > 12000) throw new Error('math_unavailable');
        window.katex.render(formula, span, { displayMode: display, throwOnError: false, trust: false, strict: 'ignore', maxExpand: 1000, maxSize: 10, output: 'htmlAndMathml' });
      } catch (_) { span.textContent = match[0]; }
      host.append(span); cursor = pattern.lastIndex;
    }
    host.append(document.createTextNode(source.slice(cursor))); return host;
  }
  function warnings(values, host) {
    const list = Array.isArray(values) ? values.filter(v => typeof v === 'string' && v.trim()).slice(0, 15) : [];
    if (!list.length) return;
    const ul = node('ul', 'warnings'); list.forEach(v => ul.append(node('li', '', text(v, 2000)))); host.append(ul);
  }
  function openStudioDialog(dialog) { dialog.showModal(); if (embedded) requestAnimationFrame(()=>{
    const rect=dialog.getBoundingClientRect();window.parent.postMessage({type:'hl-studio-dialog',top:rect.top,height:rect.height},location.origin);
  }); }
  function showImage(url, alt) { if (!url || !url.startsWith('blob:')) return; $('largeImage').src = url; $('largeImage').alt = text(alt, 300); openStudioDialog($('imageDialog')); }
  function extension(type) { return type === 'image/svg+xml' ? 'svg' : type === 'image/jpeg' ? 'jpg' : type === 'image/webp' ? 'webp' : 'png'; }
  function download(blob, filename) {
    const url = URL.createObjectURL(blob), a = node('a'); a.href = url; a.download = filename; a.hidden = true; document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 10000);
  }
  function renderFigure(job, figure, index, epoch) {
    const fig = node('figure', 'problem-figure'), loading = node('p', 'figure-loading', t('loadingFigure'));
    fig.append(loading);
    const caption = text(figure.caption || t('figure') + ' ' + index, 2000);
    if (figure.caption) fig.append(node('figcaption', '', caption));
    if (!figure.assetId) { loading.textContent = t('figureError'); return fig; }
    asset(job, figure.assetId).then(data => {
      if (state.epoch !== epoch || !fig.isConnected) return;
      const img = node('img'); img.alt = caption; img.src = data.url; img.loading = 'lazy';
      img.addEventListener('error', () => { loading.hidden = false; loading.textContent = t('figureError'); img.hidden = true; }, { once: true });
      loading.hidden = true; fig.prepend(img);
      const actions = node('div', 'figure-actions'), enlarge = node('button', 'text-button', t('enlarge')), save = node('button', 'text-button', t('downloadFigure'));
      enlarge.type = save.type = 'button'; enlarge.addEventListener('click', () => showImage(data.url, caption));
      save.addEventListener('click', () => download(data.blob, 'haslalab-figure-' + index + '.' + extension(data.type))); actions.append(enlarge, save); fig.append(actions);
    }).catch(() => { if (state.epoch === epoch) loading.textContent = t('figureError'); });
    return fig;
  }
  function renderResult(job, epoch) {
    const host = $('resultContent'); host.replaceChildren();
    if (!job.result || typeof job.result !== 'object') return;
    const result = job.result, doc = node('div', 'result-document');
    doc.append(node('h2', '', text(result.title || t(job.mode), 500)), node('p', 'document-meta', 'HASLALAB / ' + t(subjects.includes(result.subject || job.subject) ? result.subject || job.subject : 'math') + ' / ' + dateLabel(job.createdAt)));
    warnings(result.warnings, doc);
    const problems = Array.isArray(result.problems) ? result.problems.slice(0, 20) : [];
    let figureIndex = 0;
    if (!problems.length) doc.append(node('p', 'result-placeholder', t('noProblems')));
    problems.forEach((p, i) => {
      if (!p || typeof p !== 'object') return;
      const article = node('article', 'problem'); article.append(node('h3', 'problem-heading', String(p.number || i + 1).slice(0, 12) + '.'));
      article.append(mathText(p.statement));
      if (Array.isArray(p.choices) && p.choices.length) { const ol = node('ol', 'problem-choices'); p.choices.slice(0, 20).forEach(c => { const li = node('li'); li.append(mathText(c)); ol.append(li); }); article.append(ol); }
      (Array.isArray(p.figures) ? p.figures.slice(0, 20) : []).forEach(f => { if (f && typeof f === 'object') article.append(renderFigure(job, f, ++figureIndex, epoch)); });
      warnings(p.warnings, article);
      [['answer', p.answer], ['explanation', p.explanation]].forEach(([key, value]) => { if (value) { const d = node('details', 'solution'); d.append(node('summary', '', t(key)), mathText(value)); article.append(d); } });
      doc.append(article);
    });
    const checks = result.review?.checks;
    if (Array.isArray(checks) && checks.length) {
      const ul = node('ul', 'review-checks'); checks.slice(0, 20).forEach(check => { const value = typeof check === 'string' ? check : check && (check.label || check.message || check.name); if (value) { const prefix = typeof check === 'object' ? check.passed === true ? '✓ ' : '· ' : ''; ul.append(node('li', '', prefix + text(value, 1200) + (check.detail ? ' — ' + text(check.detail, 2000) : ''))); } }); if (ul.children.length) doc.append(ul);
    }
    host.append(doc);
  }
  function renderSelected() {
    const job = currentJob();
    $('emptyWorkspace').hidden = !!job; $('jobProgress').hidden = !job; $('comparison').hidden = !job;
    const textOnly = !!job && !hasOriginal(job);
    $('sourcePane').hidden = textOnly; $('comparison').classList.toggle('text-only', textOnly);
    $('exportBar').hidden = !job?.result; $('cancelJob').hidden = !isActive(job);
    $('retryJob').hidden = !job || isActive(job); message('jobError', '');
    updateSubmit(); if (!job) return;
    const status = activeStatuses.has(job.status) || ['completed', 'needs_review', 'failed', 'cancelled', 'expired'].includes(job.status) ? job.status : '';
    $('jobStatus').className = 'status-tag ' + status; $('jobStatus').textContent = statusLabel(job.status);
    $('jobProgress').classList.toggle('finished', !isActive(job));
    const stage = text(typeof job.stage === 'object' ? job.stage?.id : job.stage, 80);
    $('jobStage').textContent = isActive(job) ? TEXT[state.lang].stage[stage] || t('preparing') : job.status === 'cancelled' ? t('cancelledHint') : job.status === 'failed' ? '' : TEXT[state.lang].stage.done;
    $('jobTime').textContent = t('created') + ' ' + dateLabel(job.createdAt) + (job.updatedAt ? '  ·  ' + t('updated') + ' ' + dateLabel(job.updatedAt) : '');
    $('resultTitle').textContent = text(job.result?.title || t(modes.includes(job.mode) ? job.mode : 'workspace'), 180);
    $('resultPlaceholder').hidden = !!job.result || !isActive(job);
    if (job.status === 'failed') message('jobError', errorMessage(job.error));
    if (job.status === 'expired') message('jobError', t('expiredHint'));
    const review = job.result?.review?.status, passed = ['passed', 'verified', 'complete', 'approved', 'ok'].includes(review) && job.status !== 'needs_review';
    $('reviewStatus').hidden = !job.result; $('reviewStatus').textContent = passed ? t('reviewPassed') : t('reviewNeeded'); $('reviewStatus').classList.toggle('passed', passed);
    const key = String(job.id) + ':' + text(job.updatedAt || '') + ':' + job.status + ':' + (job.result ? JSON.stringify(job.result) : '');
    if (state.renderKey !== key) { state.renderKey = key; const epoch = ++state.epoch; showOriginal(job, epoch); renderResult(job, epoch); }
  }
  function selectJob(job) {
    clearTimeout(state.timer); state.selected = String(job.id); state.renderKey = ''; state.pollFailures = 0;
    const u = new URL(location.href); u.searchParams.set('job', state.selected); history.replaceState(null, '', u.pathname + u.search + u.hash);
    renderHistory(); renderSelected(); schedulePoll();
  }
  async function openJob(id) {
    const old = state.jobs.find(j => String(j.id) === String(id)); if (old) selectJob(old);
    try { const data = await request('/studio/jobs/' + encodeURIComponent(id)); const job = upsertJob(data.job); if (!old || String(state.selected) === String(id)) selectJob(job); }
    catch (error) { if (error.code !== 'account_changed') message('pageMessage', errorMessage(error)); }
  }
  function schedulePoll(delay = 1800) {
    clearTimeout(state.timer);
    if (isActive(currentJob()) && token()) state.timer = setTimeout(poll, delay);
  }
  async function poll() {
    const job = currentJob(); if (!isActive(job) || !token()) return;
    if (document.hidden) { schedulePoll(5000); return; }
    try {
      const data = await request('/studio/jobs/' + encodeURIComponent(job.id));
      upsertJob(data.job); state.pollFailures = 0; message('pageMessage', '');
      if (String(state.selected) === String(job.id)) { renderHistory(); renderSelected(); schedulePoll(); }
    } catch (error) {
      if (error.code === 'account_changed') return;
      if (String(state.selected) !== String(job.id)) return;
      if (error.status === 410) { upsertJob({ ...job, status: 'expired' }); renderHistory(); renderSelected(); return; }
      state.pollFailures++;
      if (error.status === 401 || error.status === 404) { message('pageMessage', errorMessage(error)); return; }
      if (state.pollFailures >= 2) message('pageMessage', t('pollError'));
      schedulePoll(Math.min(20000, 1800 * Math.pow(2, state.pollFailures)));
    }
  }
  async function loadHistory() {
    if (!token()) { renderHistory(); return; }
    $('refreshHistory').disabled = true;
    try {
      const data = await request('/studio/jobs'), list = Array.isArray(data.jobs) ? data.jobs : [];
      list.filter(safeJob).forEach(upsertJob); renderHistory();
      const wanted = new URLSearchParams(location.search).get('job');
      if (!state.selected && wanted) await openJob(wanted);
      else if (!state.selected && state.jobs.length) await openJob(state.jobs[0].id);
      else if (currentJob()) renderSelected();
    } catch (error) { if (error.code !== 'account_changed') message('pageMessage', error.status === 401 ? errorMessage(error) : t('historyError')); }
    finally { $('refreshHistory').disabled = false; }
  }
  async function capabilities() {
    try {
      const data = await request('/studio/capabilities'); state.capabilities = data.capabilities || data;
      const max = Math.max(1, Math.min(3, Number(state.capabilities.maxCount || state.capabilities.limits?.maxCount) || 3));
      Array.from($('count').options).forEach(o => { o.disabled = Number(o.value) > max; });
      if (Number($('count').value) > max) $('count').value = '1';
      message('serviceNotice', state.capabilities.available === false ? t('unavailable') : '');
    } catch (error) { if (error.code !== 'account_changed') message('serviceNotice', t('network')); }
    renderLimits(); updateSubmit();
  }
  async function loadAccount() {
    if (!token()) { state.user = null; updateAccount(); return; }
    try { const data = await request('/me'); state.user = data.user || null; } catch (error) { if (error.code === 'account_changed') return; state.user = null; }
    updateAccount();
  }
  function formValues() { return { mode: modeValue(), subject: $('subject').value, difficulty: $('difficulty').value, language: $('language').value, count: modeValue() === 'generate' ? $('count').value : '1', instruction: $('instruction').value.trim() }; }
  async function createJob() {
    if (state.creating || isActive(currentJob())) return;
    message('formError', ''); message('pageMessage', '');
    if (!token()) { message('formError', t('loginRequired')); openStudioDialog($('loginDialog')); return; }
    const values = formValues(), file = state.file, fingerprint = JSON.stringify(values), previous = state.pendingSubmission, version = state.sessionVersion;
    if (!file && values.mode !== 'generate') { message('formError', t('chooseImage')); $('dropZone').focus(); return; }
    if (!file && values.instruction.length < 5) { message('formError', t('generateInput')); $('instruction').focus(); return; }
    if (file && file.size > maxBytes()) { message('formError', imageLimitMessage()); return; }
    const requestId = previous && previous.file === file && previous.fingerprint === fingerprint ? previous.requestId : crypto.randomUUID();
    state.pendingSubmission = { file, fingerprint, requestId };
    const form = new FormData();
    Object.entries(values).forEach(([k, v]) => form.append(k, v)); if (file) form.append('image', file, file.name); form.append('requestId', requestId);
    state.creating = true; updateSubmit();
    try {
      let data;
      for (let attempt = 0; attempt < 2; attempt++) {
        if (version !== state.sessionVersion) throw localError('account_changed');
        try { data = await request('/studio/jobs', { method: 'POST', body: form }); break; }
        catch (error) { if (error.code !== 'network' || attempt === 1) throw error; await new Promise(resolve => setTimeout(resolve, 800)); }
      }
      state.pendingSubmission = null;
      const job = upsertJob(data.job); state.sourceInputs.set(String(job.id), { ...values, file }); selectJob(job);
      if (matchMedia('(max-width: 720px)').matches) $('resultTitle').scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (error) { if (error.code === 'account_changed') return; if (error.code !== 'network') state.pendingSubmission = null; message('formError', errorMessage(error)); if (error.status === 401) openStudioDialog($('loginDialog')); }
    finally { if (version === state.sessionVersion) { state.creating = false; updateSubmit(); } }
  }
  async function cancelJob() {
    const job = currentJob(), version = state.sessionVersion; if (!isActive(job) || state.cancelling) return;
    state.cancelling = true; updateSubmit();
    try {
      const data = await request('/studio/jobs/' + encodeURIComponent(job.id) + '/cancel', { method: 'POST' }); upsertJob(data.job);
      if (String(state.selected) === String(job.id)) { renderHistory(); renderSelected(); schedulePoll(); }
    } catch (error) { if (error.code !== 'account_changed') message('pageMessage', errorMessage(error)); }
    finally { if (version === state.sessionVersion) { state.cancelling = false; updateSubmit(); } }
  }
  async function retryJob() {
    const job = currentJob(), version = state.sessionVersion; if (!job || isActive(job) || state.creating) return;
    $('retryJob').disabled = true;
    try {
      const saved = state.sourceInputs.get(String(job.id)), options = saved || job.input || job.options || job;
      let file = saved?.file;
      if (!file && hasOriginal(job)) { const data = await asset(job, originalAssetId(job)); if (data.type === 'image/svg+xml') throw localError('retrySource'); file = new File([data.blob], 'original.' + extension(data.type), { type: data.type }); }
      if (version !== state.sessionVersion) return;
      const mode = modes.includes(job.mode) ? job.mode : 'digitize'; document.querySelector('input[name="mode"][value="' + mode + '"]').checked = true;
      $('subject').value = subjects.includes(options.subject) ? options.subject : subjects.includes(job.subject) ? job.subject : 'math';
      $('language').value = options.language === 'en' ? 'en' : 'ko'; $('difficulty').value = ['similar', 'easier', 'harder'].includes(options.difficulty) ? options.difficulty : 'similar';
      $('count').value = String(Math.max(1, Math.min(3, Number(options.count) || 1))); $('instruction').value = text(options.instruction || '', 1200);
      if (file) selectFile(file); else removeFile(); updateMode(); await createJob();
    } catch (error) { if (error.code !== 'account_changed') message('pageMessage', t('retrySource')); }
    finally { $('retryJob').disabled = false; }
  }
  function exportName(job) { return 'haslalab-studio-' + String(job.id).replace(/[^A-Za-z0-9_-]/g, '').slice(0, 60); }
  function resultExport(job) { return { version: 1, exportedAt: new Date().toISOString(), job: { id: job.id, mode: job.mode, status: job.status, createdAt: job.createdAt }, result: job.result }; }
  function crc32(bytes) { let crc = -1; for (const byte of bytes) { crc ^= byte; for (let i = 0; i < 8; i++) crc = crc >>> 1 ^ (crc & 1 ? 0xedb88320 : 0); } return (crc ^ -1) >>> 0; }
  /* Store-only ZIP keeps Markdown and its authenticated figure assets portable, without an external dependency. */
  function zipFiles(files) {
    const encoder = new TextEncoder(), parts = [], central = []; let offset = 0, centralSize = 0;
    for (const file of files) {
      const name = encoder.encode(file.name), data = file.data instanceof Uint8Array ? file.data : encoder.encode(file.data), crc = crc32(data);
      const local = new Uint8Array(30 + name.length), v = new DataView(local.buffer);
      v.setUint32(0, 0x04034b50, true); v.setUint16(4, 20, true); v.setUint16(6, 0x800, true); v.setUint32(14, crc, true); v.setUint32(18, data.length, true); v.setUint32(22, data.length, true); v.setUint16(26, name.length, true); local.set(name, 30);
      const record = new Uint8Array(46 + name.length), c = new DataView(record.buffer);
      c.setUint32(0, 0x02014b50, true); c.setUint16(4, 20, true); c.setUint16(6, 20, true); c.setUint16(8, 0x800, true); c.setUint32(16, crc, true); c.setUint32(20, data.length, true); c.setUint32(24, data.length, true); c.setUint16(28, name.length, true); c.setUint32(42, offset, true); record.set(name, 46);
      parts.push(local, data); central.push(record); offset += local.length + data.length; centralSize += record.length;
    }
    const end = new Uint8Array(22), v = new DataView(end.buffer); v.setUint32(0, 0x06054b50, true); v.setUint16(8, files.length, true); v.setUint16(10, files.length, true); v.setUint32(12, centralSize, true); v.setUint32(16, offset, true);
    return new Blob([...parts, ...central, end], { type: 'application/zip' });
  }
  const markdownText = value => text(value).replace(/\u0000/g, '');
  async function exportMarkdown() {
    const job = currentJob(), version = state.sessionVersion; if (!job?.result || state.exporting) return;
    state.exporting = true; updateSubmit(); toast(t('preparingExport'));
    try {
      const result = job.result, files = [], lines = ['# ' + markdownText(result.title || t(job.mode)), '', 'HaslaLab · ' + dateLabel(job.createdAt), '']; let index = 0;
      if (Array.isArray(result.warnings)) { result.warnings.forEach(w => lines.push('> ' + markdownText(w).replace(/\n/g, '\n> '))); lines.push(''); }
      for (const [i, p] of (Array.isArray(result.problems) ? result.problems.slice(0, 20) : []).entries()) {
        lines.push('## ' + text(p.number || i + 1, 12), '', markdownText(p.statement), '');
        (Array.isArray(p.choices) ? p.choices : []).forEach((c, n) => lines.push((n + 1) + '. ' + markdownText(c))); lines.push('');
        for (const figure of (Array.isArray(p.figures) ? p.figures.slice(0, 20) : [])) {
          if (version !== state.sessionVersion) throw localError('account_changed');
          if (!figure?.assetId) continue;
          const data = await asset(job, figure.assetId), name = 'figures/figure-' + (++index) + '.' + extension(data.type);
          files.push({ name, data: new Uint8Array(await data.blob.arrayBuffer()) });
          lines.push('![' + markdownText(figure.caption || t('figure') + ' ' + index).replace(/[\[\]\r\n]/g, ' ') + '](' + name + ')', '');
        }
        if (p.answer) lines.push('### ' + (state.lang === 'en' ? 'Answer' : '정답'), '', markdownText(p.answer), '');
        if (p.explanation) lines.push('### ' + (state.lang === 'en' ? 'Solution' : '해설'), '', markdownText(p.explanation), '');
        (Array.isArray(p.warnings) ? p.warnings : []).forEach(w => lines.push('> ' + markdownText(w).replace(/\n/g, '\n> '))); lines.push('');
      }
      if (version !== state.sessionVersion) return;
      const md = lines.join('\n');
      if (files.length) { files.unshift({ name: 'problems.md', data: md }, { name: 'result.json', data: JSON.stringify(resultExport(job), null, 2) }); download(zipFiles(files), exportName(job) + '.zip'); toast(t('markdownImages')); }
      else { download(new Blob([md], { type: 'text/markdown;charset=utf-8' }), exportName(job) + '.md'); message('toast', ''); }
    } catch (error) { if (error.code !== 'account_changed') toast(t('exportFailed')); }
    finally { if (version === state.sessionVersion) { state.exporting = false; updateSubmit(); } }
  }
  async function printResult() {
    const job = currentJob(), version = state.sessionVersion; if (!job?.result || state.exporting) return;
    state.exporting = true; updateSubmit();
    try {
      await Promise.all(Array.from(state.assets.entries()).filter(([key]) => key.startsWith(job.id + ':')).map(([, p]) => p.catch(() => null)));
      await Promise.all(Array.from($('resultContent').querySelectorAll('img')).map(img => img.decode ? img.decode().catch(() => {}) : Promise.resolve()));
      if (document.fonts?.ready) await document.fonts.ready;
      if (version !== state.sessionVersion || String(state.selected) !== String(job.id)) return;
      const details = Array.from($('resultContent').querySelectorAll('details')), previous = details.map(d => d.open);
      document.body.classList.toggle('print-with-solutions', $('printSolutions').checked);
      if ($('printSolutions').checked) details.forEach(d => { d.open = true; });
      const restore = () => { details.forEach((d, i) => { d.open = previous[i]; }); document.body.classList.remove('print-with-solutions'); };
      window.addEventListener('afterprint', restore, { once: true }); window.print(); setTimeout(restore, 60000);
    } catch (_) { toast(t('exportFailed')); }
    finally { if (version === state.sessionVersion) { state.exporting = false; updateSubmit(); } }
  }
  async function signIn(event) {
    event.preventDefault(); const form = $('loginForm'); $('loginSubmit').disabled = true; message('loginError', '');
    try {
      const data = await request('/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: form.elements.username.value.trim(), password: form.elements.password.value }) });
      if (!data.token) throw localError('server_error');
      resetWorkspace();
      writeStore('hlCmTok', data.token); state.user = data.user || null; form.elements.password.value = ''; $('loginDialog').close(); updateAccount(); renderHistory(); renderSelected(); toast(t('signedIn')); message('formError', '');
      await Promise.all([capabilities(), loadHistory()]);
    } catch (error) { if (error.code !== 'account_changed') message('loginError', errorMessage(error)); }
    finally { $('loginSubmit').disabled = false; }
  }
  $('language').value = state.lang;
  if (subjects.includes(studioParams.get('subject'))) $('subject').value = studioParams.get('subject');
  if (modes.includes(studioParams.get('mode'))) document.querySelector('input[name="mode"][value="'+studioParams.get('mode')+'"]').checked=true;
  if (embedded) {
    let heightQueued=false;
    const reportHeight=()=>{if(heightQueued)return;heightQueued=true;requestAnimationFrame(()=>{
      heightQueued=false;window.parent.postMessage({type:'hl-studio-height',height:Math.ceil(document.body.getBoundingClientRect().height)+2},location.origin);
    });};
    if (typeof ResizeObserver==='function') new ResizeObserver(reportHeight).observe(document.body);
    window.addEventListener('load',reportHeight);
    window.addEventListener('message',event=>{
      if(event.origin!==location.origin||event.source!==window.parent||event.data?.type!=='hl-studio-settings')return;
      if(['light','dark'].includes(event.data.theme))document.documentElement.dataset.theme=event.data.theme;
      if(Number.isFinite(event.data.viewportHeight))document.documentElement.style.setProperty('--studio-viewport-height',Math.max(300,Math.min(3000,event.data.viewportHeight))+'px');
      if(['ko','en'].includes(event.data.lang)&&event.data.lang!==state.lang){state.lang=event.data.lang;applyLanguage();}
      if(modes.includes(event.data.mode)){document.querySelector('input[name="mode"][value="'+event.data.mode+'"]').checked=true;updateMode();}
      reportHeight();
    });
    reportHeight();
  }
  $('studioForm').addEventListener('submit', e => { e.preventDefault(); createJob(); });
  document.querySelectorAll('input[name="mode"]').forEach(e => e.addEventListener('change', updateMode));
  $('imageInput').addEventListener('change', e => selectFile(e.target.files[0]));
  const phoneCaptureAvailable=navigator.userAgentData?.mobile===true||/(?:iPhone|iPod|Android[^\n]*Mobile)/i.test(navigator.userAgent||'');
  $('phoneCapture').hidden=!phoneCaptureAvailable;
  $('capturePhoto').addEventListener('click',()=>{if(phoneCaptureAvailable)$('captureInput').click();});
  $('captureInput').addEventListener('change',e=>{selectFile(e.target.files[0]);e.target.value='';});
  const paintBrand=()=>{$('studioBrandMark').src='logo/brand/haslalab-'+(document.documentElement.dataset.theme==='dark'?'dark':'light')+'.svg?v=20261103-brands';};
  new MutationObserver(paintBrand).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});paintBrand();
  $('dropZone').addEventListener('click', e => { if (e.target !== $('imageInput')) $('imageInput').click(); });
  $('dropZone').addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); $('imageInput').click(); } });
  ['dragenter', 'dragover'].forEach(name => $('dropZone').addEventListener(name, e => { e.preventDefault(); $('dropZone').classList.add('drag-over'); }));
  ['dragleave', 'drop'].forEach(name => $('dropZone').addEventListener(name, e => { e.preventDefault(); $('dropZone').classList.remove('drag-over'); }));
  $('dropZone').addEventListener('drop', e => selectFile(Array.from(e.dataTransfer.files).find(f => f.type.startsWith('image/'))));
  document.addEventListener('paste', e => { if ($('loginDialog').open) return; const item = Array.from(e.clipboardData?.items || []).find(x => x.kind === 'file' && x.type.startsWith('image/')); if (item) { e.preventDefault(); selectFile(item.getAsFile()); } });
  $('removeImage').addEventListener('click', removeFile); $('refreshHistory').addEventListener('click', loadHistory);
  $('cancelJob').addEventListener('click', cancelJob); $('retryJob').addEventListener('click', retryJob);
  $('exportMarkdown').addEventListener('click', exportMarkdown);
  $('exportJson').addEventListener('click', () => { const job = currentJob(); if (job?.result) download(new Blob([JSON.stringify(resultExport(job), null, 2)], { type: 'application/json' }), exportName(job) + '.json'); });
  $('printResult').addEventListener('click', printResult);
  $('expandSource').addEventListener('click', () => showImage(state.originalUrl, t('original')));
  $('closeImage').addEventListener('click', () => $('imageDialog').close());
  $('imageDialog').addEventListener('close', () => $('largeImage').removeAttribute('src'));
  $('accountButton').addEventListener('click', () => { if (token()) location.href = './#/me'; else openStudioDialog($('loginDialog')); });
  $('loginForm').addEventListener('submit', signIn); $('closeLogin').addEventListener('click', () => $('loginDialog').close());
  $('loginDialog').addEventListener('close', () => { $('loginForm').elements.password.value = ''; message('loginError', ''); });
  $('uiLanguage').addEventListener('click', () => { state.lang = state.lang === 'ko' ? 'en' : 'ko'; writeStore('hlLang', state.lang); applyLanguage(); });
  document.addEventListener('visibilitychange', () => { if (!document.hidden) schedulePoll(50); });
  window.addEventListener('focus', () => { if (token() && !state.user) { loadAccount(); loadHistory(); } });
  window.addEventListener('storage', e => {
    if (e.key !== null && !['hlCmTok', 'hlCmApi'].includes(e.key)) return;
    resetWorkspace();
    Promise.all([loadAccount(), capabilities(), loadHistory()]);
  });
  window.addEventListener('pagehide', () => { clearTimeout(state.timer); clearAssets(); if (state.fileUrl) URL.revokeObjectURL(state.fileUrl); });
  window.addEventListener('pageshow', event => { if (event.persisted) { if (state.file) selectFile(state.file); state.renderKey = ''; renderSelected(); schedulePoll(); } });
  updateMode(); applyLanguage(); Promise.all([loadAccount(), capabilities(), loadHistory()]);
})();
