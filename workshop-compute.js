(() => {
  const examples = {
    python: 'g = 9.81\nv0 = 15\nsamples = [i / 20 for i in range(62)]\nheights = [max(0, v0*t - g*t*t/2) for t in samples]\nplot(samples, heights, "t (s), h (m)")\nprint("Max height (m):", round(max(heights), 2))\n',
    c: '#include <stdio.h>\n\nint main(void) {\n    const double g = 9.81, v0 = 15;\n    for (int i = 0; i <= 61; ++i) {\n        double t = i / 20.0;\n        double h = v0*t - g*t*t/2;\n        printf("%.3f,%.3f\\n", t, h < 0 ? 0 : h);\n    }\n    return 0;\n}\n'
  };
  const key = 'hlWorkshopCompute';
  const isLanguage = language => Object.hasOwn(examples, language);
  const read = (storage, k) => { try { return JSON.parse(storage.getItem(k)); } catch { return null; } };
  const write = (storage, k, v) => { try { storage.setItem(k, JSON.stringify(v)); return true; } catch { return false; } };
  const isFigure = f => f && typeof f.src === 'string' && f.src.length < 390000 && /^data:image\/svg\+xml;base64,[A-Za-z0-9+/]+=*$/.test(f.src);
  const clip = (text, n) => typeof text === 'string' ? text.slice(0, n) : '';
  const blank = () => ({format: 'haslalab-compute', language: 'python', title: '', description: '', sources: {...examples}, history: []});
  function cleanHistory(history) {
    const ids = new Set();
    return (Array.isArray(history) ? history : []).flatMap((item,index) => {
      if (!['user','assistant'].includes(item?.role) || typeof item.content !== 'string') return [];
      let id = typeof item.id === 'string' && /^[\w-]{1,80}$/.test(item.id) ? item.id : 'legacy-' + index;
      if (ids.has(id)) id = crypto.randomUUID();
      ids.add(id);
      const entry = {id,role:item.role,content:clip(item.content,2000)};
      if (item.role === 'assistant' && isLanguage(item.version?.language) && typeof item.version.code === 'string' && item.version.code.length <= 60000) {
        entry.version = {language:item.version.language,code:item.version.code};
      }
      return [entry];
    });
  }

  const chatMath = [
    {left:'$$', right:'$$', display:true},
    {left:'\\[', right:'\\]', display:true},
    {left:'\\(', right:'\\)', display:false},
    {left:'$', right:'$', display:false},
  ];
  function formatAnswer(node, value) {
    const chunks = value.split(/```[^\n]*\n([\s\S]*?)```/g);
    chunks.forEach((chunk, index) => {
      if (index % 2 === 0) node.append(document.createTextNode(chunk));
      else {
        const block = document.createElement('pre'), code = document.createElement('code');
        code.textContent = chunk;
        block.className = 'out';
        block.append(code);
        node.append(block);
      }
    });
    window.renderMathInElement?.(node, {delimiters:chatMath, throwOnError:false, trust:false, strict:'ignore'});
  }

  function launch(host, language, code, onPhase, stdin = '') {
    const frame = document.createElement('iframe');
    frame.className = 'compute-runtime-frame';
    frame.title = 'Computation runtime';
    frame.setAttribute('aria-hidden','true');
    frame.tabIndex = -1;
    frame.setAttribute('sandbox', 'allow-scripts');
    frame.src = 'workshop-runtime.html?v=0523eed3716b';
    let timer, finish, sent = false;
    const result = new Promise(resolve => { finish = resolve; });
    const close = value => {
      if (!finish) return;
      clearTimeout(timer);
      removeEventListener('message', receive);
      frame.remove();
      finish(value);
      finish = null;
    };
    function receive(event) {
      if (event.source !== frame.contentWindow || event.origin !== 'null') return;
      const d = event.data;
      if (d?.phase === 'ready' && !sent) {
        sent = true;
        clearTimeout(timer);
        timer = setTimeout(() => close({timeout:'runtime'}), language === 'c' ? 180000 : 120000);
        frame.contentWindow.postMessage({type: 'workshop-run', language, code, stdin}, '*');
      } else if (d?.phase === 'running') {
        clearTimeout(timer);
        timer = setTimeout(() => close({timeout:'program'}), 30000);
        onPhase('running');
      } else if (['python','compiler','retrying'].includes(d?.phase)) {
        onPhase(d.phase);
      } else if (d?.phase === 'done') {
        close({stage:d.stage === 'program' ? 'program' : 'runtime', stdout: clip(d.stdout, 32000), stderr: clip(d.stderr, 8000), error: clip(d.error, 8000),
          plots: Array.isArray(d.plots) ? d.plots.slice(0, 6) : [], images:Array.isArray(d.images) ? d.images.slice(0,4) : []});
      }
    }
    addEventListener('message', receive);
    timer = setTimeout(() => close({timeout:'frame'}), 20000);
    host.append(frame);
    onPhase('loading');
    return {result, stop: () => close({stopped: true})};
  }

  function drawPlot(host, plot) {
    if (!Array.isArray(plot?.x) || !Array.isArray(plot.y)) return;
    const points = plot.x.slice(0, 2000).map((x, i) => [Number(x), Number(plot.y[i])]).filter(p => p.every(Number.isFinite));
    if (points.length < 2) return;
    const xs = points.map(p => p[0]), ys = points.map(p => p[1]);
    const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 480 208');
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', clip(plot.label, 80) || 'x, y');
    function shape(tag, props, text) {
      const el = document.createElementNS(svg.namespaceURI, tag);
      for (const [k, v] of Object.entries(props)) el.setAttribute(k, v);
      if (text != null) el.textContent = text;
      svg.append(el);
    }
    shape('path', {d:'M 54 24 V 177 H 454', fill:'none', stroke:'currentColor', opacity:'.55'});
    shape('polyline', {points: points.map(([x, y]) => (54 + (x-minX)/(maxX-minX || 1)*400).toFixed(2) + ',' + (177 - (y-minY)/(maxY-minY || 1)*145).toFixed(2)).join(' '),
      fill:'none', stroke:'var(--accent, #7c64b1)', 'stroke-width': '2'});
    const tick = (x, y, v) => shape('text', {x,y, fill:'currentColor', 'font-size':'11'}, Number(v.toPrecision(4)));
    tick(5, 36, maxY); tick(5, 177, minY); tick(54, 194, minX); tick(420, 194, maxX);
    const fig = document.createElement('figure');
    fig.append(svg);
    if (plot.label) {
      const cap = document.createElement('figcaption');
      cap.textContent = clip(plot.label, 80);
      fig.append(cap);
    }
    host.append(fig);
  }

  function open(ctx, {id, preview = false, transfer = false}) {
    const {root, api, apiBase, token, height, esc} = ctx, ko = ctx.lang === 'ko';
    const tr = (a,b) => ko ? a : b;
    const share = window.HL_SHARE, forms = window.HL_SHARE_MAKER;
    const P = window.HL_WORKSHOP_PROJECTS, cloud = P.client({base:apiBase,token});
    const resumeKey = key + ':resume';
    const remembered = read(localStorage, resumeKey);
    const draftKeys = [key, key + ':draw', key + ':problem'];
    const localKey = id ? key + ':project:' + id :
      transfer === 'draw' || transfer === 'problem' ? key + ':' + transfer :
      draftKeys.includes(remembered) ? remembered : key;
    const previous = !id && !preview ? read(localStorage, localKey) : null;
    const question = transfer === 'problem' ? read(sessionStorage, 'hlWorkshopComputeQuestion') : null;
    const figure = transfer === 'draw' ? read(sessionStorage, 'hlWorkshopFigure') : question?.figure;
    const draft = question || isFigure(figure) ? null : previous;
    const project = {...blank(), ...draft, sources: {...examples, ...draft?.sources}, history:cleanHistory(draft?.history)};
    if (isFigure(figure)) {
      project.figure = figure;
      try { sessionStorage.removeItem('hlWorkshopFigure'); } catch {}
    }
    if (question) {
      project.title = clip(question.title, 80);
      project.question = clip(question.text, 4000);
      try { sessionStorage.removeItem('hlWorkshopComputeQuestion'); } catch {}
    }
    let stored = draft?.storage || null, sharedId = id ? +id : draft?.sharedId || null, published = !!draft?.published;
    let active = true, running = null, busy = false, lastError = '', lastOutput = '', copyOutput = '', copyPlot = null, undo = null;
    let canPersist = !preview && !id, projectOpened = Boolean(draft || transfer);
    const {panelHandle,panelTab} = P;
    if (!isLanguage(project.language)) project.language = 'python';
    root.innerHTML = '<section id="cpProjects" hidden></section><div class="compute-maker" id="cpEditor">' +
      '<header class="head"><div><h1>' + tr('전산물리 제작', 'Computational physics maker') + '</h1><p class="lede">' +
      tr('Python 또는 C로 계산하고, 결과를 그래프로 확인하세요.', 'Compute in Python or C and plot the results.') +
      '</p></div><div class="acts"><a class="btn" href="/#/workshop/share" target="_top">' + tr('작품 공유', 'Showcase') + '</a>' +
      (preview ? '' : '<button type="button" id="cpWorkspace" aria-controls="cpAssistant" aria-expanded="false">' + tr('AI에게 맡기기','Ask AI') + '</button><a class="btn" href="' + esc('create.html?' + new URLSearchParams({view:'edit',kind:'code',lang:ctx.lang,embed:new URLSearchParams(location.search).get('embed') || '0',theme:document.documentElement.dataset.theme})) + '">' + tr('Python 채점 문제', 'Graded Python problem') + '</a>') + '</div></header>' +
      '<div class="compute-meta"><label>' + tr('제목', 'Title') + '<input id="cpTitle" maxlength="80"></label>' +
      '<label>' + tr('언어', 'Language') + '<select id="cpLang"><option value="python">Python</option><option value="c">C</option></select></label></div>' +
      (preview ? '' : '<div class="compute-viewbar" id="cpViewbar" role="group" aria-label="' + tr('작업 화면','Workspace views') + '" hidden><button type="button" data-pane="assistant">' + tr('대화','Chat') + '</button><button type="button" data-pane="code">' + tr('코드','Code') + '</button><button type="button" data-pane="result">' + tr('실행 결과','Results') + '</button></div>') +
      '<div class="compute-work" id="cpDock"><div class="compute-document"><section class="panel" id="cpCodePane" data-dock="code"><header class="dock-bar">' + panelTab('cpCodeBody',['코드','Code'],'⌘') + '</header><div id="cpCodeBody" data-dock-body><textarea id="cpCode" class="code" rows="16" maxlength="60000" spellcheck="false" autocapitalize="off" autocorrect="off" aria-label="' + tr('코드', 'Code') + '"></textarea>' +
      '<p id="cpFormat" class="note"></p><div class="row"><button class="primary" id="cpRun">' + tr('실행', 'Run') + '</button><button type="button" id="cpCopyCode">' + tr('코드 복사','Copy code') + '</button><button id="cpDown">' + tr('코드 내려받기', 'Download code') + '</button></div><details><summary>' + tr('실행 입력 (stdin)','Program input (stdin)') + '</summary><textarea id="cpInput" rows="3" maxlength="8000" aria-label="' + tr('실행 입력','Program input') + '"></textarea></details>' +
      (preview ? '' : '<div class="row"><button id="cpImportFigure">' + tr('그림 불러오기','Import figure') + '</button></div>') +
      '<div id="cpFigure" hidden></div><details><summary>' + tr('작품 설명', 'Project description') + '</summary><textarea id="cpDescription" rows="3" maxlength="3000" aria-label="' + tr('작품 설명', 'Project description') + '"></textarea></details></div>' + panelHandle('cpCodeBody',['코드','code']) + '</section>' +
      '<section class="panel" id="cpResultPane" data-dock="result"><header class="dock-bar">' + panelTab('cpResultBody',['실행 결과','Results'],'≋') + '</header><div id="cpResultBody" data-dock-body><div class="row"><button id="cpStop" disabled>' + tr('중지','Stop') + '</button><button type="button" id="cpCopyResult" disabled>' + tr('결과 복사','Copy result') + '</button></div><p id="cpRunStatus" role="status"></p><div id="cpPlots"></div><pre class="out" id="cpOutput" hidden></pre></div>' + panelHandle('cpResultBody',['실행 결과','results']) + '</section></div>' +
      (preview ? '' : '<section class="panel compute-chat" id="cpAssistant" data-dock="assistant" data-dock-floor-width="320" data-dock-floor-height="340" aria-labelledby="cpChatHeading" hidden><div id="cpAssistantBody" data-dock-body><header class="compute-chat-header"><h2 id="cpChatHeading">' + tr('하슬라 AI','Hasla AI') + '</h2><div class="compute-chat-tools"><button type="button" id="cpChatSize" aria-pressed="false"></button><button type="button" id="cpChatClose" aria-label="' + tr('대화 닫기','Close chat') + '" title="' + tr('대화 닫기','Close chat') + '">×</button></div></header><div class="compute-transcript" id="cpChatScroll" tabindex="0" aria-label="' + tr('대화 기록','Conversation') + '"><p id="cpChatEmpty" class="note">' + tr('물리 모델을 설명하거나 열린 코드에 대해 질문해 보세요.', 'Describe a physical model or ask about the open code.') + '</p><div id="cpChat" role="log" aria-live="polite"></div></div><p id="cpTaskStatus" class="note" role="status"></p>' +
      '<form id="cpForm"><textarea id="cpPrompt" rows="3" maxlength="2000" required aria-label="' + tr('AI에게 요청할 내용', 'Prompt') + '" placeholder="' +
      tr('예: 공기 저항을 포함한 포물선 운동을 만들어 줘. 이후 질량을 바꿔 달라고 요청할 수 있어요.', 'E.g. Build a projectile model with air resistance. Then ask to change the mass.') + '"></textarea>' +
      '<div class="compute-composer"><span class="note" id="cpChatLanguage"></span><label for="cpTaskMode">' + tr('작업 방식','Task mode') + '</label><select id="cpTaskMode"><option value="edit">' + tr('코드 제안','Propose code') + '</option><option value="delegate">' + tr('적용하고 실행','Apply and run') + '</option><option value="chat">' + tr('질문만','Ask a question') + '</option></select><button class="primary" type="submit">' + tr('보내기','Send') + '</button></div>' +
      '</form><button type="button" id="cpUndo" hidden>' + tr('AI 변경 되돌리기','Undo AI change') + '</button></div>' + panelHandle('cpAssistantBody',['AI 대화','AI chat']) + '</section>') +
      '</div>' + (preview ? '' : '<div class="row compute-actions"><span id="cpProvider"></span><button id="cpSave">' + tr('저장', 'Save') + '</button><button id="cpOpen">' + tr('프로젝트 목록', 'Projects') + '</button>' +
      '<button class="primary" id="cpShare">' + tr('작품 공유', 'Share project') + '</button></div>') +
      '<p id="cpCopyStatus" role="status" class="note"></p><p id="cpStatus" role="status" class="note"></p><div id="cpRuntime"></div></div>';
    const $ = id => root.querySelector('#' + id);
    const msg = s => { $('cpStatus').textContent = s || ''; height(); };
    const lang = $('cpLang'), source = $('cpCode'), title = $('cpTitle'), description = $('cpDescription');
    const editor = $('cpEditor'), workToggle = $('cpWorkspace');
    const dock = P.bindPanels($('cpDock'),height);
    let chatScroll = Infinity;
    function setExpanded(expanded) {
      const control = $('cpChatSize');
      const label = expanded ? tr('대화 축소','Restore chat size') : tr('대화 확대','Expand chat');
      editor.classList.toggle('chat-expanded', expanded);
      control.setAttribute('aria-pressed', String(expanded));
      control.setAttribute('aria-label', label);
      control.title = label;
      control.textContent = expanded ? '⤡' : '⤢';
    }
    function selectPane(pane) {
      const log = $('cpChatScroll');
      if (editor.dataset.pane === 'assistant' && pane !== 'assistant' && log?.getClientRects().length) chatScroll = log.scrollTop;
      editor.dataset.pane = pane;
      if (pane === 'assistant') log.scrollTop = Math.min(log.scrollHeight,chatScroll);
      else {
        editor.dataset.document = pane;
        setExpanded(false);
      }
      $('cpViewbar')?.querySelectorAll('[data-pane]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.pane === pane)));
      height();
    }
    function setWorkspace(opened) {
      if (!workToggle) return;
      editor.classList.toggle('is-workspace', opened);
      workToggle.setAttribute('aria-expanded', String(opened));
      if (!opened && $('cpChatScroll').getClientRects().length) chatScroll = $('cpChatScroll').scrollTop;
      $('cpAssistant').hidden = $('cpViewbar').hidden = !opened;
      if (opened) {
        editor.dataset.document ||= 'code';
        selectPane('assistant');
        if (document.activeElement === workToggle) $('cpPrompt').focus({preventScroll:true});
      }
      height();
    }
    if (workToggle) {
      const closeChat = () => {
        setWorkspace(false);
        persist();
        workToggle.focus({preventScroll:true});
      };
      setExpanded(false);
      workToggle.onclick = () => {
        if (editor.classList.contains('is-workspace')) closeChat();
        else {
          setWorkspace(true);
          persist();
        }
      };
      $('cpChatClose').onclick = closeChat;
      $('cpChatSize').onclick = () => {
        const expanded = !editor.classList.contains('chat-expanded');
        if (expanded) selectPane('assistant');
        setExpanded(expanded);
        persist();
        height();
      };
      $('cpAssistant').addEventListener('keydown', event => {
        if (event.key === 'Escape' && !event.defaultPrevented && !event.isComposing) {
          event.preventDefault();
          closeChat();
        }
      });
      $('cpViewbar').onclick = e => {
        const pane = e.target.closest('[data-pane]')?.dataset.pane;
        if (pane) { selectPane(pane); persist(); }
      };
    }
    function resetCopyResult() {
      copyOutput = '';
      copyPlot = null;
      $('cpCopyResult').disabled = true;
      $('cpCopyStatus').textContent = '';
    }
    async function copyText(value) {
      if (!value) return;
      let copied = false;
      try { await navigator.clipboard.writeText(value); copied = true; }
      catch {
        const active = document.activeElement, field = document.createElement('textarea');
        field.className = 'copy-fallback-field'; field.value = value; field.readOnly = true;
        document.body.append(field); field.select(); field.setSelectionRange(0,field.value.length);
        try { copied = document.execCommand('copy'); } catch {}
        field.remove(); active?.focus({preventScroll:true});
      }
      $('cpCopyStatus').textContent = copied ? tr('복사했습니다.','Copied.') : tr('복사할 수 없습니다. 텍스트를 선택해 복사해 주세요.','Could not copy. Select the text to copy it manually.');
      height();
    }
    $('cpCopyCode').onclick = () => copyText(source.value);
    $('cpCopyResult').onclick = async () => {
      if (copyOutput) return copyText(copyOutput);
      if (!copyPlot) return;
      try {
        const bytes = Uint8Array.from(atob(copyPlot), ch => ch.charCodeAt(0));
        await navigator.clipboard.write([new ClipboardItem({'image/png':new Blob([bytes],{type:'image/png'})})]);
        $('cpCopyStatus').textContent = tr('그래프를 복사했습니다.','Plot copied.');
      } catch { $('cpCopyStatus').textContent = tr('그래프를 길게 누르거나 우클릭해 복사해 주세요.','Press and hold or right-click the plot to copy it.'); }
      height();
    };
    if (!preview) $('cpProvider').append(P.providerSelect(stored?.provider));
    const projectData = () => {
      const {format, language, sources, figure, question, title, description, history, appliedVersion} = project;
      return {format, language, sources, figure, question, title, description, history, appliedVersion};
    };
    const legacyUnsaved = draft?.format === 'haslalab-compute' && draft.dirty === undefined && !stored;
    let savedSignature = draft?.dirty || legacyUnsaved || question || isFigure(figure) ? null : JSON.stringify(projectData());
    let hasDraft = !!draft || savedSignature === null;
    const isDirty = () => savedSignature !== JSON.stringify(projectData());
    const stopProtecting = preview ? () => {} : P.protectDraft(() => projectOpened && isDirty());
    const snapshot = () => ({
      ...projectData(), storage: stored, sharedId, published, dirty: isDirty(),
      assistant_open: editor.classList.contains('is-workspace'),
      assistant_expanded: editor.classList.contains('chat-expanded'),
    });
    let lastSnapshot;
    const persist = () => {
      if (!active || !canPersist || !projectOpened) return;
      const currentDraft = snapshot();
      hasDraft ||= currentDraft.dirty || !!stored;
      if (!hasDraft) return;
      const data = JSON.stringify(currentDraft);
      if (data === lastSnapshot) return;
      try {
        localStorage.setItem(localKey, data);
        lastSnapshot = data;
        if (!id) write(localStorage, resumeKey, localKey);
      } catch {
        msg(tr('브라우저 저장공간이 부족합니다. 대화와 코드를 보관하려면 프로젝트를 저장해 주세요.','Browser storage is full. Save the project to keep the code and chat.'));
      }
    };
    if (!preview) window.addEventListener('pagehide', persist);
    const contextHistory = () => project.history.slice(-6).map(({role,content}) => ({role,content}));
    const chat = (role, content, code, language) => {
      const entry = {id:crypto.randomUUID(),role,content:clip(content,2000)};
      if (typeof code === 'string' && code.trim() && isLanguage(language)) entry.version = {language,code:clip(code,60000)};
      project.history.push(entry);
      persist(); paintChat(true);
      return entry;
    };
    function applyVersion(entry, {keepUndo = false} = {}) {
      if (!entry.version) return;
      const {language,code} = entry.version;
      if (!keepUndo || !undo) undo = {language, code:project.sources[language], activeLanguage:project.language, appliedVersion:project.appliedVersion};
      cancelRun();
      project.sources[language] = code;
      project.language = language;
      project.appliedVersion = entry.id;
      lastError = lastOutput = '';
      resetCopyResult();
      $('cpPlots').replaceChildren(); $('cpOutput').hidden = true; $('cpRunStatus').textContent = '';
      $('cpUndo').hidden = false;
      paint(); persist();
    }
    function paintChat(toLatest = false) {
      const box = $('cpChat'), scroll = $('cpChatScroll');
      if (!box) return;
      $('cpChatEmpty').hidden = project.history.length > 0;
      if (toLatest) chatScroll = Infinity;
      const position = scroll.scrollTop, opened = new Set([...box.querySelectorAll('details[open]')].map(item => item.dataset.id));
      let versionNumber = 0;
      box.replaceChildren(...project.history.map(turn => {
        const row = document.createElement('article'), name = document.createElement('strong');
        row.className = turn.role === 'user' ? 'compute-turn-user' : 'compute-turn-assistant';
        name.textContent = turn.role === 'user' ? tr('나', 'You') : tr('하슬라 AI','Hasla AI');
        const message = document.createElement('div');
        message.className = 'compute-message';
        if (turn.role === 'assistant') formatAnswer(message, turn.content);
        else message.textContent = turn.content;
        row.append(name, message);
        if (turn.version) {
          const {language,code} = turn.version;
          const current = project.appliedVersion === turn.id && project.sources[language] === code;
          const details = document.createElement('details'), summary = document.createElement('summary'), example = document.createElement('pre');
          details.dataset.id = turn.id;
          details.open = opened.has(turn.id);
          versionNumber++;
          summary.textContent = tr('코드 버전 ','Code version ') + versionNumber + ' · ' + (language === 'c' ? 'C' : 'Python');
          example.className = 'out'; example.textContent = code;
          const apply = document.createElement('button'); apply.type = 'button';
          apply.disabled = busy || current;
          apply.textContent = current ? tr('적용됨','Applied') : tr('이 버전 적용','Apply this version');
          apply.onclick = () => { if (!busy) applyVersion(turn); };
          details.append(summary,example);
          row.append(details,apply);
        }
        return row;
      }));
      scroll.scrollTop = toLatest ? scroll.scrollHeight : position;
      height();
    }
    function paint() {
      lang.value = project.language; title.value = project.title; description.value = project.description;
      if ($('cpChatLanguage')) $('cpChatLanguage').textContent = project.language === 'c' ? 'C17' : 'Python 3';
      source.value = project.sources[project.language] || '';
      $('cpFormat').textContent = project.language === 'python'
        ? tr('그래프: plot(x, y, "제목")', 'Plot: plot(x, y, "title")')
        : tr('그래프: 각 줄에 숫자 x,y를 출력하세요. 첫 실행은 컴파일러를 내려받습니다.', 'Plot: print one numeric x,y pair per line. The first run downloads the compiler.');
      const box = $('cpFigure');
      box.replaceChildren();
      box.hidden = !isFigure(project.figure);
      if (!box.hidden) {
        const image = new Image();
        image.src = project.figure.src;
        image.alt = tr('연결된 워크샵 그림', 'Linked Workshop figure');
        box.append(image);
        if (!preview) {
          const detach = document.createElement('button');
          detach.textContent = tr('그림 연결 해제', 'Detach figure');
          detach.onclick = () => { delete project.figure; paint(); persist(); };
          box.append(detach);
        }
      }
      paintChat();
    }
    source.oninput = () => {
      project.sources[project.language] = source.value;
      if (undo) { undo = null; $('cpUndo').hidden = true; }
      if (project.appliedVersion) { delete project.appliedVersion; paintChat(); }
      persist();
    };
    source.onkeydown = e => {
      if (e.key === 'Tab' && !e.shiftKey) {
        e.preventDefault();
        source.setRangeText('    ', source.selectionStart, source.selectionEnd, 'end');
        source.oninput();
      } else if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); run(); }
    };
    function cancelRun() {
      const task = running;
      running = null;
      task?.stop();
      const stop = $('cpStop');
      if (stop) stop.disabled = true;
    }
    lang.onchange = () => {
      cancelRun(); project.language = lang.value; lastError = lastOutput = ''; resetCopyResult();
      $('cpPlots').replaceChildren(); $('cpOutput').hidden = true; $('cpRunStatus').textContent = '';
      paint(); persist();
    };
    title.oninput = () => { project.title = title.value; persist(); };
    description.oninput = () => { project.description = description.value; persist(); };
    async function run({fromAI = false} = {}) {
      if (!active || !source.value.trim() || source.value.length > 60000) return null;
      dock.reveal($('cpResultPane'));
      if (editor.classList.contains('is-workspace')) {
        editor.dataset.document = 'result';
        if (!fromAI) selectPane('result');
      }
      running?.stop();
      const status = $('cpRunStatus'), output = $('cpOutput'), plots = $('cpPlots');
      output.hidden = true; plots.replaceChildren(); $('cpStop').disabled = false; resetCopyResult();
      lastError = lastOutput = '';
      const phases = {
        loading:tr('실행 환경을 여는 중…','Opening the runtime…'),
        python:tr('Python과 필요한 패키지를 불러오는 중…','Loading Python and required packages…'),
        compiler:tr('C 컴파일러를 불러오고 코드를 컴파일하는 중…','Loading the C compiler and compiling your code…'),
        retrying:tr('다운로드에 실패해 다른 경로로 다시 시도하는 중…','Download failed. Trying an alternate source…'),
        running:tr('이 기기에서 실행 중…','Running on this device…'),
      };
      const task = launch($('cpRuntime'), project.language, source.value, phase => { status.textContent = phases[phase]; }, $('cpInput').value);
      if (!fromAI && innerWidth < 760 && !editor.classList.contains('is-workspace')) status.scrollIntoView({block:'nearest'});
      running = task;
      const r = await task.result;
      if (!active || running !== task) return null;
      running = null;
      $('cpStop').disabled = true;
      lastError = r.error || (r.timeout === 'program' ? tr('코드 실행 시간이 30초를 넘었습니다.', 'The program exceeded 30 seconds.')
        : r.timeout ? tr('실행 환경을 제시간에 열지 못했습니다. 네트워크를 확인한 뒤 다시 실행해 주세요.', 'Could not load the runtime in time. Check your connection and try again.') : '');
      lastOutput = r.stdout || '';
      output.textContent = [lastOutput, r.stderr, lastError].filter(Boolean).join('\n');
      output.hidden = !output.textContent;
      for (const p of r.plots || []) drawPlot(plots, p);
      for (const data of r.images || []) {
        if (typeof data !== 'string' || data.length > 500000 || !/^[A-Za-z0-9+/]+=*$/.test(data)) continue;
        const img = new Image();img.src = 'data:image/png;base64,' + data;img.alt = tr('Python 실행 그래프','Python plot'); plots.append(img); copyPlot ||= data;
      }
      const series = project.language === 'python' ? (r.plots || []).filter(p => Array.isArray(p?.x) && Array.isArray(p.y)).map(p =>
        [p.label || 'x,y',...p.x.slice(0,2000).map((x,i) => Number(x)+','+Number(p.y[i]))].join('\n')) : [];
      copyOutput = [output.textContent,...series].filter(Boolean).join('\n\n');
      $('cpCopyResult').disabled = !copyOutput && !copyPlot;
      const startupFailed = (r.stage === 'runtime' && lastError) || (r.timeout && r.timeout !== 'program');
      status.textContent = r.stopped ? tr('중지했습니다.','Stopped.') : startupFailed
        ? tr('실행 환경을 시작하지 못했습니다.','Could not start the runtime.') : lastError ? tr('코드 실행 오류','Program error') : tr('실행 완료','Run finished');
      height();
      return r;
    }
    $('cpRun').onclick = () => run();
    $('cpStop').onclick = () => running?.stop();
    $('cpDown').onclick = () => {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([source.value], {type: 'text/plain'}));
      a.download = (title.value.trim() || 'simulation') + (project.language === 'c' ? '.c' : '.py');
      a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 30000);
    };
    const login = () => { if (!token()) { msg(tr('로그인한 뒤 이용할 수 있습니다.', 'Sign in to use this feature.')); return false; } return true; };
    const errorText = e => e?.code === 'code_ai_limit' ? tr('오늘의 AI 사용량을 모두 사용했습니다.', 'Today’s AI quota is used up.')
      : e?.code === 'quota_exceeded' ? tr('보관함의 남은 용량이 부족합니다.', 'There is not enough space in Storage.')
      : e?.code === 'changed' ? tr('다른 곳에서 파일을 수정했습니다. 다시 열어 주세요.', 'The file changed elsewhere. Reopen it.')
      : tr('처리하지 못했습니다. ', 'Could not complete the request. ') + (e?.code || e?.message || '');
    const form = $('cpForm');
    if (form) {
      const prompt = $('cpPrompt'), send = form.querySelector('[type=submit]'), undoButton = $('cpUndo');
      const taskStatus = text => { $('cpTaskStatus').textContent = text; height(); };
      const modeInput = $('cpTaskMode');
      modeInput.onchange = () => {
        taskStatus(modeInput.value === 'delegate' ? tr('코드를 적용해 실행하고, 코드 오류가 있으면 한 번 수정합니다.','Applies and runs the code, with one revision if the program fails.') : '');
      };
      if (project.question) prompt.value = tr('다음 문제를 시뮬레이션으로 만들어 줘. ', 'Build a simulation for this problem. ') + project.question.slice(0, 1500);
      else if (isFigure(figure)) prompt.value = tr('연결된 그림에 나타난 물리계의 시뮬레이션을 처음부터 만들어 줘.', 'Build a simulation for the physical system in the linked figure.');
      prompt.addEventListener('keydown', event => {
        if (event.key === 'Enter' && !event.shiftKey && !event.isComposing && event.keyCode !== 229) {
          event.preventDefault();
          form.requestSubmit();
        }
      });
      const turn = async (request, language, code, error, history, mode) => {
        const scene = project.figure?.scene;
        const context = JSON.stringify({problem: project.question || '', objects: Array.isArray(scene?.objects) ? scene.objects.slice(0, 20) : []}).slice(0, 8000);
        return api('/api/workshop/code-ai', 'POST', {prompt: request, code, error: clip(error, 1000), lang: ctx.lang, language, history, context, mode});
      };
      form.onsubmit = async e => {
        e.preventDefault();
        if (busy || !login() || !prompt.value.trim()) return;
        const request = prompt.value.trim(), language = project.language, code = source.value, mode = $('cpTaskMode').value;
        const delegate = mode === 'delegate';
        const history = contextHistory();
        busy = send.disabled = lang.disabled = source.readOnly = $('cpRun').disabled = true;
        chat('user', request); prompt.value = '';
        try {
          taskStatus(mode === 'chat' ? tr('답변을 작성하는 중…','Preparing an answer…') : tr('코드를 작성하는 중…','Writing code…'));
          let result = await turn(request, language, code, lastError, history, mode === 'chat' ? 'chat' : 'edit');
          if (!active) return;
          const answer = chat('assistant', result.explanation || tr('코드를 작성했습니다.', 'Code is ready.'), mode === 'chat' ? null : result.code, language);
          if (delegate && answer.version) {
            applyVersion(answer);
            taskStatus(tr('코드를 적용하고 이 기기에서 실행하는 중…','Applied code and running it on this device…'));
            let outcome = await run({fromAI:true});
            if (active && outcome?.error && outcome.stage === 'program' && result.left > 0) {
              taskStatus(tr('실행 오류를 반영해 한 번 더 수정하는 중…','Revising once using the runtime error…'));
              const repair = await turn(tr('이 실행 오류를 수정하고 전체 코드를 다시 작성해 줘.', 'Fix this runtime error and return the entire program.'),
                language, source.value, lastError, contextHistory(), 'edit');
              if (!active) return;
              const revision = chat('assistant', repair.explanation || tr('오류를 수정했습니다.', 'I revised the code to fix the error.'), repair.code, language);
              applyVersion(revision,{keepUndo:true});
              result = repair;
              outcome = await run({fromAI:true});
            }
            if (active) chat('assistant', lastError ? tr('실행 결과 탭에 오류를 표시했습니다.','See the Results tab for the error.') : outcome?.stopped ? tr('실행이 중지됐습니다.','The run was stopped.') : tr('실행 결과 탭에서 출력과 그래프를 확인할 수 있습니다.','Output and plots are available in Results.'));
          }
          taskStatus(Number.isFinite(result.left) ? tr('오늘 남은 AI 요청 ' + result.left + '회', result.left + ' AI requests left today') : '');
        } catch (e) { if (active) { taskStatus(errorText(e)); prompt.value ||= request; } }
        finally {
          if (active) { busy = send.disabled = lang.disabled = source.readOnly = $('cpRun').disabled = false; paintChat(); }
        }
      };
      undoButton.onclick = () => {
        if (!undo || busy) return;
        project.sources[undo.language] = undo.code;
        project.appliedVersion = undo.appliedVersion;
        project.language = undo.activeLanguage; undo = null;
        cancelRun(); lastError = lastOutput = ''; resetCopyResult();
        $('cpPlots').replaceChildren(); $('cpOutput').hidden = true; $('cpRunStatus').textContent = '';
        undoButton.hidden = true; paint(); persist();
      };
    }

    async function fileRequest(path, method, body) {
      const response = await fetch(apiBase + '/api/workshop/storage' + path, {method, body, headers: {Authorization: 'Bearer ' + token()}});
      if (!response.ok) throw await response.json().then(j => ({code: j.error})).catch(() => ({code: 'network'}));
      return response;
    }
    function hydrate(data) {
      if (data?.format !== 'haslalab-compute' || !isLanguage(data.language) || !data.sources ||
          !Object.keys(examples).every(k => typeof data.sources[k] === 'string' && data.sources[k].length <= 60000)) throw new Error(tr('전산물리 파일 형식이 아닙니다.', 'This is not a computational physics project.'));
      project.language = data.language;
      project.title = clip(data.title, 80);
      project.description = clip(data.description, 3000);
      project.sources = {python: data.sources.python, c: data.sources.c};
      project.figure = isFigure(data.figure) ? data.figure : undefined;
      project.question = clip(data.question, 4000);
      project.history = cleanHistory(data.history);
      project.appliedVersion = project.history.some(item => item.id === data.appliedVersion && item.version) ? data.appliedVersion : undefined;
      undo = null;
      if ($('cpTaskStatus')) $('cpTaskStatus').textContent = '';
      if ($('cpPrompt')) $('cpPrompt').value = '';
      if ($('cpUndo')) $('cpUndo').hidden = true;
      paint();
    }
    const save = async () => {
      if (!project.title.trim()) { title.focus(); throw new Error(tr('작품 제목을 입력해 주세요.', 'Enter a project title.')); }
      const fd = new FormData();
      fd.append('kind','sim');
      fd.append('folder','전산물리');
      fd.append('ensure_folder','1');
      const data = projectData(), name = data.title;
      const signature = JSON.stringify(data);
      const provider = $('cpProvider').querySelector('select').value;
      if (provider !== 'store') stored = await cloud.saveExternal(provider,'compute',name,data,stored);
      else {
        const local = stored?.provider === 'store' || (stored && !stored.provider) ? stored : null;
        if (local?.updated_at) fd.append('base', String(local.updated_at));
        fd.append('file', new Blob([signature], {type:'application/json'}), local?.name || (name+'.json'));
        const response = local ? await fileRequest('/files/' + encodeURIComponent(local.id) + '/content','PUT',fd) : await fileRequest('/files','POST',fd);
        stored = {...(await response.json()).file,provider:'store'};
      }
      savedSignature = signature;
      persist();
    };

    let storageRevision = 0;
    function showEditor(preferences) {
      $('cpProjects').hidden = true;
      $('cpEditor').hidden = false;
      $('cpProvider').querySelector('select').value = stored?.provider || 'store';
      projectOpened = true;
      setExpanded(preferences?.assistant_expanded === true);
      setWorkspace(preferences?.assistant_open ?? project.history.length > 0);
      height();
    }
    function showProjects() {
      if (!active || busy) return;
      cancelRun();
      persist();
      $('cpEditor').hidden = true;
      const host = $('cpProjects');
      host.hidden = false;
      const panel = P.library(host,cloud,{kind:'compute', unified:true, title:tr('전산물리 프로젝트','Computational physics projects'), height,
        onResume:hasDraft ? () => showEditor(snapshot()) : null,
        onNew() { loadProject(blank(), null); },
        onOpen:loadProject,
      });
      panel.heading.focus();
      height();
    }
    function loadProject(data, entry) {
      if (!active || busy || $('cpProjects').hidden || (isDirty() && !P.confirmReplacement())) return;
      cancelRun();
      hydrate(data);
      savedSignature = JSON.stringify(projectData());
      hasDraft = !!entry;
      lastSnapshot = undefined;
      if (!entry) { try { localStorage.removeItem(localKey); } catch {} }
      chatScroll = Infinity;
      editor.dataset.pane = '';
      editor.dataset.document = 'code';
      storageRevision++;
      stored=entry; sharedId=null; published=false; lastOutput=''; lastError=''; resetCopyResult(); $('cpInput').value = '';
      $('cpPlots').replaceChildren(); $('cpOutput').hidden=true; $('cpRunStatus').textContent='';
      showEditor(data);
      persist();
      title.focus();
    }
    async function perform(button, action) {
      if (busy) return;
      button.disabled = true;
      busy = true;
      try { await action(); } catch (e) { if (active) msg(P.error(e)); }
      finally { button.disabled = false; busy = false; }
    }
    if (!preview) {
      $('cpSave').onclick = () => {
        if (!login()) return;
        perform($('cpSave'), async () => { await save(); msg(tr('선택한 저장소에 저장했습니다.', 'Saved to the selected storage.')); });
      };
      $('cpOpen').onclick = showProjects;
      $('cpImportFigure').onclick = () => {
        const local = read(localStorage,'hlDrawScene');
        const revision = storageRevision;
        P.pickFigure(cloud,{local,height,onPick(figure) {
          if (!active || revision !== storageRevision) return;
          project.figure=figure; paint(); persist();
        }});
      };
      $('cpShare').onclick = () => {
        if (!login()) return;
        if (!title.value.trim()) { title.focus(); return; }
        if (!source.value.trim() || !share || !forms) { msg(tr('공유할 코드를 입력해 주세요.', 'Enter code to share.')); return; }
        const thumbnail = isFigure(project.figure) && project.figure.src.length < 180000 ? project.figure.src : '';
        const payload = () => ({language: project.language, code: source.value});
        const dlg = forms.dialog({lang: ctx.lang, type: 'sim', values: {title: title.value.trim(),description: description.value}, thumbnail,
          shared: sharedId && published ? {id: sharedId, published: true} : null, height,
          build: form => forms.publishInput({type: 'sim', form, payload: payload(), thumbnail, creationId: sharedId || undefined}),
          publish: input => share.publish(input),
          update: input => share.update(sharedId, input),
          unpublish: () => share.unpublish(sharedId),
          onDone: r => {
            if (r?.id) sharedId = r.id;
            published = !r?.unpublished;
            persist();
          }
        });
        dlg.showModal();
      };
    }
    paint();
    if (!preview && !id) {
      if (draft || transfer) {
        showEditor(draft || (question || isFigure(figure) ? {assistant_open:true} : null));
        if (draft) lastSnapshot = JSON.stringify(snapshot());
        else if (transfer) persist();
      } else showProjects();
      P.showGuide('compute');
    }
    if (id) {
      $('cpRun').disabled = true;
      source.readOnly = lang.disabled = title.readOnly = description.readOnly = true;
      const shareButton = $('cpShare');
      if (shareButton) shareButton.disabled = true;
      if (workToggle) workToggle.disabled = true;
      share.get(id).then(({project: p}) => {
        if (!active) return;
        if (!isLanguage(p.language) || typeof p.code !== 'string') throw new Error(tr('이 실행 형식을 열 수 없습니다.', 'This project uses a different runtime.'));
        if (!preview && !p.mine) throw new Error(tr('작품을 수정하려면 먼저 리믹스하세요.', 'Remix the project to edit it.'));
        project.title = p.title;
        project.description = p.description;
        project.language = p.language;
        project.sources[p.language] = p.code;
        published = p.status === 'public';
        savedSignature = JSON.stringify(projectData());
        const ownerDraft = !preview ? read(localStorage, localKey) : null;
        if (ownerDraft) {
          try {
            hydrate(ownerDraft);
            stored = ownerDraft.storage || null;
            hasDraft = true;
            if (ownerDraft.dirty === false) savedSignature = JSON.stringify(projectData());
          } catch {}
        }
        paint();
        $('cpRun').disabled = false;
        if (!preview) {
          canPersist = true;
          source.readOnly = lang.disabled = title.readOnly = description.readOnly = false;
          shareButton.disabled = workToggle.disabled = false;
          showEditor(ownerDraft);
          lastSnapshot = JSON.stringify(snapshot());
        }
      }).catch(e => { if (active) msg(errorText(e)); });
    }
    return {stop() {
      persist();
      active = false;
      window.removeEventListener('pagehide', persist);
      cancelRun();
      stopProtecting();
    }};
  }
  window.HL_WORKSHOP_COMPUTE = {open};
})();
