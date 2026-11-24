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

  function launch(host, language, code, onPhase) {
    const frame = document.createElement('iframe');
    frame.hidden = true;
    frame.title = 'Computation runtime';
    frame.setAttribute('sandbox', 'allow-scripts');
    frame.src = 'workshop-runtime.html?v=db46d8098481';
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
        frame.contentWindow.postMessage({type: 'workshop-run', language, code}, '*');
      } else if (d?.phase === 'running') {
        clearTimeout(timer);
        timer = setTimeout(() => close({timeout: true}), 30000);
        onPhase('running');
      } else if (d?.phase === 'done') {
        close({stdout: clip(d.stdout, 32000), stderr: clip(d.stderr, 8000), error: clip(d.error, 8000),
          plots: Array.isArray(d.plots) ? d.plots.slice(0, 6) : []});
      }
    }
    addEventListener('message', receive);
    timer = setTimeout(() => close({timeout: true}), 180000);
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
    const localKey = transfer === 'draw' || transfer === 'problem' ? key + ':' + transfer : key;
    const previous = !id ? read(localStorage, localKey) : null;
    const question = transfer === 'problem' ? read(sessionStorage, 'hlWorkshopComputeQuestion') : null;
    const figure = transfer === 'draw' ? read(sessionStorage, 'hlWorkshopFigure') : question?.figure;
    const draft = question || isFigure(figure) ? null : previous;
    const project = {...blank(), ...draft, sources: {...examples, ...draft?.sources}};
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
    let active = true, running = null, busy = false, lastError = '', lastOutput = '', proposal = '', undo = null;
    if (!isLanguage(project.language)) project.language = 'python';
    root.innerHTML = '<div class="compute-maker">' +
      '<header class="head"><div><h1>' + tr('전산물리 제작', 'Computational physics maker') + '</h1><p class="lede">' +
      tr('Python 또는 C로 계산하고, 결과를 그래프로 확인하세요.', 'Compute in Python or C and plot the results.') +
      '</p></div><div class="acts"><a class="btn" href="/#/workshop/share" target="_top">' + tr('작품 공유', 'Showcase') + '</a>' +
      (preview ? '' : '<a class="btn" href="' + esc('create.html?' + new URLSearchParams({view:'edit',kind:'code',lang:ctx.lang,embed:new URLSearchParams(location.search).get('embed') || '0',theme:document.documentElement.dataset.theme})) + '">' + tr('Python 채점 문제', 'Graded Python problem') + '</a>') + '</div></header>' +
      '<div class="compute-meta"><label>' + tr('제목', 'Title') + '<input id="cpTitle" maxlength="80"></label>' +
      '<label>' + tr('언어', 'Language') + '<select id="cpLang"><option value="python">Python</option><option value="c">C</option></select></label></div>' +
      '<div class="compute-work"><section class="panel"><h2>' + tr('코드', 'Code') + '</h2><textarea id="cpCode" class="code" rows="16" maxlength="60000" spellcheck="false" aria-label="' + tr('코드', 'Code') + '"></textarea>' +
      '<p id="cpFormat" class="note"></p><div class="row"><button class="primary" id="cpRun">' + tr('실행', 'Run') + '</button><button id="cpStop" disabled>' + tr('중지', 'Stop') + '</button><button id="cpDown">' + tr('코드 내려받기', 'Download code') + '</button></div>' +
      '<div id="cpFigure" hidden></div><details><summary>' + tr('작품 설명', 'Project description') + '</summary><textarea id="cpDescription" rows="3" maxlength="3000" aria-label="' + tr('작품 설명', 'Project description') + '"></textarea></details></section>' +
      '<section class="panel"><h2>' + tr('실행 결과', 'Results') + '</h2><p id="cpRunStatus" role="status"></p><div id="cpPlots"></div><pre class="out" id="cpOutput" hidden></pre></section>' +
      (preview ? '' : '<section class="panel compute-chat"><h2>' + tr('AI에게 맡기기', 'Ask AI to build it') + '</h2><div id="cpChat" role="log" aria-live="polite"></div>' +
      '<form id="cpForm"><textarea id="cpPrompt" rows="3" maxlength="2000" required aria-label="' + tr('AI에게 요청할 내용', 'Prompt') + '" placeholder="' +
      tr('예: 공기 저항을 포함한 포물선 운동을 만들어 줘. 이후 질량을 바꿔 달라고 요청할 수 있어요.', 'E.g. Build a projectile model with air resistance. Then ask to change the mass.') + '"></textarea>' +
      '<label class="compute-check"><input type="checkbox" id="cpDelegate"> ' + tr('전권 위임 · 코드 적용, 실행 및 오류 시 1회 수정', 'Delegate · apply, run and fix errors once') + '</label>' +
      '<details id="cpProposal" hidden><summary>' + tr('제안 코드 보기', 'Review proposed code') + '</summary><pre class="out"></pre></details>' +
      '<div class="row"><button class="primary" type="submit">' + tr('보내기', 'Send') + '</button><button type="button" id="cpApply" hidden>' + tr('코드 적용', 'Apply code') + '</button><button type="button" id="cpUndo" hidden>' + tr('되돌리기', 'Undo') + '</button></div></form></section>') +
      '</div>' + (preview ? '' : '<div class="row compute-actions"><button id="cpSave">' + tr('보관함에 저장', 'Save to Storage') + '</button><button id="cpOpen">' + tr('보관함에서 열기', 'Open from Storage') + '</button>' +
      '<button id="cpPaper">' + tr('문제 제작에 활용', 'Use in a problem') + '</button><button class="primary" id="cpShare">' + tr('작품 공유', 'Share project') + '</button></div>') +
      '<p id="cpStatus" role="status" class="note"></p><div id="cpRuntime"></div></div>';
    const $ = id => root.querySelector('#' + id);
    const msg = s => { $('cpStatus').textContent = s || ''; height(); };
    const lang = $('cpLang'), source = $('cpCode'), title = $('cpTitle'), description = $('cpDescription');
    const snapshot = () => ({...project, storage: stored, sharedId, published});
    const persist = () => { if (!id && !preview) write(localStorage, localKey, snapshot()); };
    const chat = (who, content) => {
      project.history = [...project.history, {role: who, content: clip(content, 2000)}].slice(-8);
      paintChat(); persist();
    };
    function paintChat() {
      const box = $('cpChat');
      if (!box) return;
      box.replaceChildren(...project.history.map(turn => {
        const row = document.createElement('p'), name = document.createElement('strong');
        name.textContent = turn.role === 'user' ? tr('나', 'You') : 'AI';
        row.append(name, document.createTextNode(' ' + turn.content));
        return row;
      }));
      box.scrollTop = box.scrollHeight;
      height();
    }
    function paint() {
      lang.value = project.language; title.value = project.title; description.value = project.description;
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
    source.oninput = () => { project.sources[project.language] = source.value; persist(); };
    source.onkeydown = e => {
      if (e.key === 'Tab' && !e.shiftKey) {
        e.preventDefault();
        source.setRangeText('    ', source.selectionStart, source.selectionEnd, 'end');
        source.oninput();
      } else if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); run(); }
    };
    lang.onchange = () => {
      running?.stop(); project.language = lang.value; proposal = ''; lastError = lastOutput = '';
      if ($('cpApply')) $('cpApply').hidden = $('cpProposal').hidden = true;
      $('cpPlots').replaceChildren(); $('cpOutput').hidden = true; $('cpRunStatus').textContent = '';
      paint(); persist();
    };
    title.oninput = () => { project.title = title.value; persist(); };
    description.oninput = () => { project.description = description.value; persist(); };
    async function run() {
      if (!active || !source.value.trim() || source.value.length > 60000) return null;
      running?.stop();
      const status = $('cpRunStatus'), output = $('cpOutput'), plots = $('cpPlots');
      output.hidden = true; plots.replaceChildren(); $('cpStop').disabled = false;
      lastError = lastOutput = '';
      const task = launch($('cpRuntime'), project.language, source.value, phase => {
        status.textContent = phase === 'loading' ? tr('실행 환경을 불러오는 중…', 'Loading the runtime…') : tr('이 기기에서 실행 중…', 'Running on this device…');
      });
      running = task;
      const r = await task.result;
      if (!active || running !== task) return null;
      running = null;
      $('cpStop').disabled = true;
      lastError = r.error || (r.timeout ? tr('실행 시간이 초과됐습니다.', 'The runtime timed out.') : '');
      lastOutput = r.stdout || '';
      output.textContent = [lastOutput, r.stderr, lastError].filter(Boolean).join('\n');
      output.hidden = !output.textContent;
      for (const p of r.plots || []) drawPlot(plots, p);
      status.textContent = r.stopped ? tr('중지했습니다.', 'Stopped.') : lastError ? tr('실행 오류', 'Run failed') : tr('실행 완료', 'Run finished');
      height();
      return r;
    }
    $('cpRun').onclick = run;
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
      const prompt = $('cpPrompt'), send = form.querySelector('[type=submit]'), apply = $('cpApply'), undoButton = $('cpUndo'), review = $('cpProposal');
      if (project.question) prompt.value = tr('다음 문제를 시뮬레이션으로 만들어 줘. ', 'Build a simulation for this problem. ') + project.question.slice(0, 1500);
      else if (isFigure(figure)) prompt.value = tr('연결된 그림에 나타난 물리계의 시뮬레이션을 처음부터 만들어 줘.', 'Build a simulation for the physical system in the linked figure.');
      const commit = (code, language) => {
        if (!undo) undo = {language, code: project.sources[language]};
        project.sources[language] = clip(code, 60000);
        project.language = language;
        proposal = '';
        apply.hidden = review.hidden = true; undoButton.hidden = false; paint(); persist();
      };
      const turn = async (request, language, code, error, history) => {
        const scene = project.figure?.scene;
        const context = JSON.stringify({problem: project.question || '', objects: Array.isArray(scene?.objects) ? scene.objects.slice(0, 20) : []}).slice(0, 8000);
        return api('/api/workshop/code-ai', 'POST', {prompt: request, code, error: clip(error, 1000), lang: ctx.lang, language, history, context});
      };
      form.onsubmit = async e => {
        e.preventDefault();
        if (busy || !login() || !prompt.value.trim()) return;
        const request = prompt.value.trim(), language = project.language, code = source.value, delegate = $('cpDelegate').checked;
        const history = project.history.slice(-6);
        busy = send.disabled = lang.disabled = source.readOnly = true;
        proposal = ''; apply.hidden = review.hidden = true;
        chat('user', request); prompt.value = '';
        try {
          msg(tr('AI가 코드를 작성하는 중…', 'AI is writing code…'));
          let result = await turn(request, language, code, lastError, history);
          if (!active) return;
          chat('assistant', result.explanation || tr('코드를 작성했습니다.', 'Code is ready.'));
          if (delegate) {
            undo = null;
            commit(result.code, language);
            const first = await run();
            if (active && first?.error && result.left > 0) {
              const repair = await turn(tr('이 실행 오류를 수정하고 전체 코드를 다시 작성해 줘.', 'Fix this runtime error and return the entire program.'),
                language, source.value, lastError, project.history.slice(-6));
              if (!active) return;
              chat('assistant', repair.explanation || tr('오류를 수정했습니다.', 'I revised the code to fix the error.'));
              commit(repair.code, language);
              result = repair;
              await run();
            }
          } else {
            proposal = result.code;
            review.querySelector('pre').textContent = proposal;
            apply.hidden = review.hidden = false;
          }
          msg(Number.isFinite(result.left) ? tr('오늘 남은 AI 요청 ' + result.left + '회', result.left + ' AI requests left today') : '');
        } catch (e) { if (active) msg(errorText(e)); }
        finally { busy = send.disabled = lang.disabled = source.readOnly = false; }
      };
      apply.onclick = () => { if (proposal) { undo = null; commit(proposal, project.language); } };
      undoButton.onclick = () => {
        if (!undo) return;
        project.sources[undo.language] = undo.code;
        project.language = undo.language; undo = null;
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
      project.history = []; proposal = ''; undo = null;
      if ($('cpApply')) $('cpApply').hidden = $('cpUndo').hidden = $('cpProposal').hidden = true;
      paint();
    }
    const save = async () => {
      if (!project.title.trim()) { title.focus(); throw new Error(tr('작품 제목을 입력해 주세요.', 'Enter a project title.')); }
      const fd = new FormData();
      fd.append('kind','sim');
      fd.append('folder','전산물리');
      fd.append('ensure_folder','1');
      const {format, language, sources, figure, question, title: name, description} = project;
      if (stored?.updated_at) fd.append('base', String(stored.updated_at));
      fd.append('file', new Blob([JSON.stringify({format, language, sources, figure, question, title: name, description})], {type: 'application/json'}), stored?.name || (name + '.json'));
      const response = stored ? await fileRequest('/files/' + stored.id + '/content','PUT',fd) : await fileRequest('/files','POST',fd);
      stored = (await response.json()).file;
      persist();
    };
    async function perform(button, action) {
      if (busy) return;
      button.disabled = true;
      busy = true;
      try { await action(); } catch (e) { if (active) msg(errorText(e)); }
      finally { button.disabled = false; busy = false; }
    }
    if (!preview) {
      $('cpSave').onclick = () => {
        if (!login()) return;
        perform($('cpSave'), async () => { await save(); msg(tr('보관함에 저장했습니다.', 'Saved to Storage.')); });
      };
      $('cpOpen').onclick = () => {
        if (!login()) return;
        perform($('cpOpen'), async () => {
          const {files} = await api('/api/workshop/storage?kind=sim');
          if (!active) return;
          const dialog = document.createElement('dialog');
          dialog.className = 'stdlg';
          dialog.innerHTML = '<div class="dlg-head"><h2>' + tr('보관함에서 열기','Open from Storage') + '</h2><button type="button">' + tr('닫기','Close') + '</button></div><div class="row" data-files></div>';
          dialog.onclose = () => dialog.remove();
          dialog.querySelector('button').onclick = () => dialog.close();
          const list = dialog.querySelector('[data-files]');
          for (const f of files.filter(f => /\.json$/i.test(f.name))) {
            const b = document.createElement('button');
            b.textContent = f.name;
            b.onclick = () => perform(b, async () => {
              const r = await fileRequest('/files/' + f.id, 'GET');
              const data = await r.json();
              if (!active) return;
              running?.stop();
              hydrate(data);
              stored = f; sharedId = null; published = false; persist();
              dialog.close();
            });
            list.append(b);
          }
          if (!list.childElementCount) list.textContent = tr('저장한 전산물리 작품이 없습니다.', 'No saved computational physics projects.');
          root.append(dialog); dialog.showModal();
        });
      };
      $('cpPaper').onclick = () => {
        const transfer = {title: title.value.trim(), description: description.value.trim(), language: project.language, code: source.value, output: lastOutput, figure: project.figure};
        if (!write(sessionStorage, 'hlWorkshopProblem', transfer)) { msg(tr('문제 제작에 보낼 수 없습니다.', 'Could not send the project to the problem maker.')); return; }
        if (window.top !== window) window.top.location.hash = '/workshop/make?tab=ai&from=compute';
      else location.assign('/#/workshop/make?tab=ai&from=compute');
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
          publish: async input => { await save(); return share.publish(input); },
          update: async input => { await save(); return share.update(sharedId, input); },
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
    if (!id && transfer) persist();
    if (id) {
      $('cpRun').disabled = true;
      source.readOnly = lang.disabled = title.readOnly = description.readOnly = true;
      const shareButton = $('cpShare'), paperButton = $('cpPaper');
      if (shareButton) shareButton.disabled = paperButton.disabled = true;
      share.get(id).then(({project: p}) => {
        if (!active) return;
        if (!isLanguage(p.language) || typeof p.code !== 'string') throw new Error(tr('이 실행 형식을 열 수 없습니다.', 'This project uses a different runtime.'));
        if (!preview && !p.mine) throw new Error(tr('작품을 수정하려면 먼저 리믹스하세요.', 'Remix the project to edit it.'));
        project.title = p.title;
        project.description = p.description;
        project.language = p.language;
        project.sources[p.language] = p.code;
        published = p.status === 'public'; paint();
        $('cpRun').disabled = false;
        if (!preview) {
          source.readOnly = lang.disabled = title.readOnly = description.readOnly = false;
          shareButton.disabled = paperButton.disabled = false;
        }
      }).catch(e => { if (active) msg(errorText(e)); });
    }
    return {stop() { active = false; running?.stop(); }};
  }
  window.HL_WORKSHOP_COMPUTE = {open};
})();
