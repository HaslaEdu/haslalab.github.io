/* Project entry and figure picker shared by all three Workshop editors. */
(function () {
  'use strict';
  const providers = ['store', 'drive', 'github'];
  const CONNECT = '/api/workshop/connectors';
  const labels = ko => ({store: ko ? '하슬라랩 보관함' : 'HaslaLab storage', drive: 'Google Drive', github: 'GitHub'});
  const suffix = kind => '-haslalab-' + kind + '.json';
  const scopeOf = data => data.repo + '/' + data.folder;
  const txt = (ko, en) => document.documentElement.lang === 'ko' ? ko : en;
  const messages = {
    not_connected: ['보관함에서 계정을 먼저 연결해 주세요.', 'Connect your account in Storage first.'],
    not_configured: ['아직 이 저장소가 연결 설정되지 않았습니다.', 'This storage provider is not configured.'],
    repo_not_chosen: ['보관함에서 GitHub 저장소를 먼저 선택해 주세요.', 'Choose a GitHub repository in Storage first.'],
    github_conflict: ['GitHub 파일이나 저장소가 바뀌었습니다. 프로젝트를 다시 열고 저장해 주세요.', 'The GitHub file or repository changed. Reopen it before saving.'],
    drive_reconnect: ['보관함에서 Google Drive를 다시 연결해 주세요.', 'Reconnect Google Drive in Storage.'],
    github_reconnect: ['보관함에서 GitHub를 다시 연결해 주세요.', 'Reconnect GitHub in Storage.'],
    drive_conflict: ['Google Drive 파일이 바뀌었습니다. 프로젝트를 다시 열고 저장해 주세요.', 'The Drive file changed. Reopen it before saving.'],
    quota_exceeded: ['하슬라랩 보관함 용량이 부족합니다.', 'HaslaLab storage is full.'],
    login_required: ['로그인하면 저장한 프로젝트를 볼 수 있습니다.', 'Sign in to see saved projects.'],
  };
  function error(err) {
    const message = messages[err?.code];
    return message ? txt(...message) : err?.message || txt('처리하지 못했습니다. 다시 시도해 주세요.', 'Could not complete the action. Try again.');
  }
  const make = (tag, text, cls) => {
    const el = document.createElement(tag);
    if (text) el.textContent = text;
    if (cls) el.className = cls;
    return el;
  };
  const button = (text, fn, cls) => {
    const el = make('button', text, cls);
    el.type = 'button';
    el.onclick = fn;
    return el;
  };
  function providerSelect(value = 'store') {
    const select = make('select', null, 'project-provider');
    select.setAttribute('aria-label', txt('저장 위치', 'Storage location'));
    for (const [key, name] of Object.entries(labels(document.documentElement.lang === 'ko'))) {
      const option = make('option', name);
      option.value = key;
      select.append(option);
    }
    select.value = providers.includes(value) ? value : 'store';
    return select;
  }
  function client({base, token}) {
    async function request(path, method = 'GET', body) {
      const auth = token();
      if (!auth) throw {code:'login_required'};
      let r;
      try { r = await fetch(base + path, {method, body, headers:{Authorization:'Bearer ' + auth}}); }
      catch { throw new Error(txt('저장소에 연결할 수 없습니다.', 'Could not connect to storage.')); }
      if (!r.ok) {
        const body = await r.json().catch(() => ({}));
        throw {code:body.error, status:r.status};
      }
      return r.json();
    }
    const connector = (provider, route) => CONNECT + '/' + provider + '/' + route;
    async function list(kind, provider) {
      if (provider === 'store') {
        const r = await request('/api/workshop/storage?kind=' + (kind === 'compute' ? 'sim' : 'figure'));
        const folders = kind === 'compute' ? ['전산물리'] : kind === 'attachment' ? ['그림','삽화'] : kind === 'asset' ? ['에셋'] : ['그림'];
        return (r.files || []).filter(f => folders.includes(f.folder) && /\.json$/i.test(f.name)).map(f => ({...f, provider}));
      }
      const r = await request(connector(provider, 'files'));
      return (r.files || []).filter(f => !f.folder && /\.json$/i.test(f.name) &&
        (f.name.endsWith(suffix(kind)) || (kind === 'attachment' && (f.name.endsWith(suffix('figure')) || f.name.endsWith(suffix('illustration')))) || (kind !== 'asset' && !/-haslalab-(figure|compute|illustration|asset)\.json$/i.test(f.name)))).map(f => ({...f, provider, scope: provider === 'github' ? scopeOf(r) : null}));
    }
    function load(entry) {
      const p = entry.provider || 'store';
      if (p === 'store') return request('/api/workshop/storage/files/' + encodeURIComponent(entry.id));
      if (p === 'drive') return request(connector(p, 'files/' + encodeURIComponent(entry.id)));
      return request(connector(p, 'file?' + new URLSearchParams({path:entry.path,scope:entry.scope || ''})));
    }
    async function saveExternal(provider, kind, title, data, previous) {
      const existing = previous?.provider === provider ? previous : null;
      const safe = (title || 'project').replace(/[^\p{L}\p{N} ._-]/gu, '_').replace(/^[. -]+/, '').slice(0, 32) || 'project';
      const name = existing?.name || safe + '-' + crypto.randomUUID().slice(0, 8) + suffix(kind);
      const form = new FormData();
      form.append('file', new Blob([JSON.stringify(data)], {type:'application/json'}), name);
      form.append('project','1');
      let scope = null;
      if (provider === 'github') {
        scope = scopeOf(await request(connector(provider, 'files')));
        if (existing && scope !== existing.scope) throw {code:'github_conflict'};
        form.append('scope', scope);
      }
      if (existing) {
        form.append('base', existing.modified || existing.sha || '');
        const route = provider === 'drive' ? 'files/' + encodeURIComponent(existing.id) : 'file?path=' + encodeURIComponent(existing.path);
        return {...(await request(connector(provider, route), 'PUT', form)).file, provider, scope};
      }
      return {...(await request(connector(provider, 'files'), 'POST', form)).file, provider, scope};
    }
    return {list, load, saveExternal, token};
  }
  function library(host, storage, {kind, title, onOpen, onNew, onResume, initial = 'store', unified = false, height = () => {}}) {
    host.classList.toggle('project-library', unified);
    const heading = make('h1', title, 'project-library-title'); heading.tabIndex = -1;
    const tools = make('div', null, 'row project-library-tools');
    const list = make('div', null, 'grid project-library-grid');
    const status = make('p', null, 'note'); status.setAttribute('role', 'status'); status.hidden = true;
    const notice = make('p', null, 'note'); notice.hidden = true;
    const say = message => { status.textContent = message; status.hidden = !message; };
    if (onNew) tools.append(button(txt('새 프로젝트', 'New project'), onNew, 'primary'));
    if (onResume) tools.append(button(txt('현재 작업 이어서', 'Resume current work'), onResume));
    const select = unified ? null : providerSelect(initial);
    const search = make('input'), sort = make('select');
    search.type = 'search';
    search.placeholder = txt('프로젝트 이름 검색', 'Search project names');
    search.setAttribute('aria-label', search.placeholder);
    sort.setAttribute('aria-label', txt('프로젝트 정렬', 'Sort projects'));
    sort.append(new Option(txt('최근 수정순', 'Last modified'), 'recent'), new Option(txt('이름순', 'Name'), 'name'));
    const filters = make('div', null, 'project-library-filters');
    filters.append(search, sort);
    if (select) tools.append(select);
    const storageLink = make('a', txt('저장소 연결 관리', 'Manage storage connections'), 'btn project-library-manage');
    storageLink.href = '/#/workshop/storage'; storageLink.target = '_top'; tools.append(storageLink);
    const head = make('div', null, 'project-library-head');
    head.append(heading, tools);
    host.replaceChildren(head, ...(unified ? [filters] : []), notice, status, list);
    const names = labels(document.documentElement.lang === 'ko');
    const docs = new WeakMap();
    function load(entry) {
      if (!docs.has(entry)) docs.set(entry, storage.load(entry).catch(e => { docs.delete(entry); throw e; }));
      return docs.get(entry);
    }
    let generation = 0, opening = 0, rendering = 0, activePreviews = 0, rows = [], pending = [];
    const cardName = entry => entry.name.replace(/(?:-[a-f0-9]{8}-haslalab-(?:figure|compute|illustration|asset))?\.json$/i, '');
    const timestamp = entry => Date.parse(entry.modified || '') || (entry.updated_at || 0) * 1000;
    let observer;
    function queue(cover, entry) {
      pending.push({cover,entry,render:rendering});
      paintPreviews();
    }
    function paintPreviews() {
      while (activePreviews < 3 && pending.length) {
        const {cover,entry,render} = pending.shift();
        if (render !== rendering || !cover.isConnected) continue;
        activePreviews++;
        load(entry).then(async raw => {
          if (render !== rendering || !cover.isConnected) return;
          const summary = cover.parentElement.querySelector('.project-card-summary');
          if (kind === 'figure') {
            const data = await figure(raw, 320);
            const img = make('img'); img.alt = ''; img.src = data.src; img.decoding = 'async';
            cover.replaceChildren(img);
            const count = pages(raw).length;
            summary.textContent = txt('그림 ' + count + '개', count + (count === 1 ? ' figure' : ' figures'));
          } else {
            summary.textContent = typeof raw?.description === 'string' ? raw.description.trim().slice(0,180) : '';
            const lang = raw?.language === 'c' ? 'c' : 'python';
            const source = raw?.sources?.[lang];
            if (typeof source !== 'string') return;
            const snippet = source.split(/\r?\n/).filter(line => line.trim()).slice(0,4).map(line => line.slice(0,64)).join('\n');
            const badge = make('span', lang === 'c' ? 'C' : 'Python', 'project-preview-language');
            cover.replaceChildren(badge, make('code', snippet));
          }
        }).catch(() => {}).finally(() => { activePreviews--; paintPreviews(); });
      }
    }
    function renderRows() {
      rendering++;
      observer?.disconnect();
      pending = [];
      list.replaceChildren();
      const query = search.value.trim().toLocaleLowerCase();
      const orderByName = (a,b) => cardName(a).localeCompare(cardName(b), document.documentElement.lang);
      const shown = rows.filter(entry => !query || cardName(entry).toLocaleLowerCase().includes(query))
        .sort((a,b) => (sort.value === 'recent' ? timestamp(b) - timestamp(a) : 0) || orderByName(a,b));
      if (!shown.length && !status.textContent) {
        list.append(make('p', query ? txt('검색 결과가 없습니다.', 'No projects match your search.')
          : txt('저장된 프로젝트가 없습니다.', 'No saved projects.'), 'project-library-empty'));
      }
      if (unified && typeof IntersectionObserver === 'function') {
        observer = new IntersectionObserver((entries, current) => {
          for (const item of entries) if (item.isIntersecting) {
            current.unobserve(item.target);
            const entry = shown[Number(item.target.dataset.preview)];
            if (entry) queue(item.target, entry);
          }
        }, {rootMargin:'120px'});
      }
      shown.forEach((entry,index) => {
        const name = cardName(entry);
        const item = button(unified ? '' : name, async () => {
          const selection = ++opening, round = generation;
          item.disabled = true;
          say(txt('프로젝트 여는 중…', 'Opening project…'));
          try {
            const data = await load(entry);
            if (round !== generation || selection !== opening || !host.isConnected || host.hidden) return;
            await onOpen(data, entry);
            say('');
          } catch (e) { if (selection === opening && round === generation) say(error(e)); }
          finally { item.disabled = false; height(); }
        }, 'card project-library-card');
        const stamp = timestamp(entry), date = stamp ? new Date(stamp).toLocaleDateString(document.documentElement.lang) : '';
        if (unified) {
          const cover = make('span', null, 'project-preview project-preview--' + kind);
          cover.setAttribute('aria-hidden','true');
          cover.append(make('span', kind === 'compute' ? '</>' : '◇', 'project-preview-placeholder'));
          cover.dataset.preview = String(index);
          const meta = make('span', null, 'project-card-meta');
          if (date) meta.append(make('span',date));
          meta.append(make('span', names[entry.provider] || names.store, 'project-card-source'));
          const title = make('strong',name,'project-card-name'); title.title = name;
          const body = make('span',null,'project-card-body');
          body.append(title,make('span',null,'project-card-summary'),meta);
          item.append(cover,body);
          if (observer) observer.observe(cover);
          else if (index < 9) queueMicrotask(() => queue(cover,entry));
        } else if (date) item.append(make('span', date, 'note'));
        list.append(item);
      });
      height();
    }
    async function refresh() {
      const round = ++generation;
      rows = [];
      say(txt('프로젝트 불러오는 중…', 'Loading projects…'));
      notice.hidden = true;
      renderRows();
      try {
        if (unified) {
          if (!storage.token()) throw {code:'login_required'};
          const results = await Promise.allSettled(providers.map(provider => storage.list(kind, provider)));
          if (round !== generation || !host.isConnected) return;
          if (results.every(r => r.status === 'rejected')) throw results[0].reason;
          rows = results.flatMap(r => r.status === 'fulfilled' ? r.value : []);
          const unavailable = results.flatMap((r,i) => r.status === 'rejected' && !['not_connected','not_configured','repo_not_chosen'].includes(r.reason?.code) ? [names[providers[i]]] : []);
          if (unavailable.length) {
            notice.textContent = txt('일부 저장소를 불러오지 못했습니다. ', 'Some storage locations could not be loaded. ') + unavailable.join(', ');
            notice.hidden = false;
          }
        } else {
          const result = await storage.list(kind, select.value);
          if (round !== generation || !host.isConnected) return;
          rows = result;
        }
        if (round !== generation || !host.isConnected) return;
        say('');
      } catch (e) { if (round === generation) say(error(e)); }
      finally { if (round === generation) renderRows(); }
    }
    if (select) select.onchange = refresh;
    search.oninput = sort.onchange = renderRows;
    refresh();
    return {refresh, heading};
  }
  function pages(raw) {
    if (!raw || !Array.isArray(raw.objects)) throw new Error(txt('그림 프로젝트 파일을 선택해 주세요.', 'Choose a figure project.'));
    if (raw.project?.version !== 1) return [raw];
    const {index, otherPages} = raw.project;
    if (!Array.isArray(otherPages) || !Number.isInteger(index) || index < 0 || index > otherPages.length) throw new Error(txt('그림 목록을 읽을 수 없습니다.', 'Could not read the figure pages.'));
    const {project, ...scene} = raw;
    const result = [...otherPages];
    result.splice(index, 0, scene);
    return result;
  }
  async function figure(scene, width = 800) {
    const [S,R] = await Promise.all([import('./draw-scene.mjs'), import('./draw-render.mjs')]);
    const v = S.validateScene(scene);
    if (!v.ok) throw new Error(txt('그림 데이터를 읽을 수 없습니다.', 'Could not read the figure.'));
    const clean = v.scene, view = clean.view || S.sceneBounds(clean);
    const svg = R.renderSVG(clean, {width, view, ...R.printScale(clean.style, clean.printW)});
    const bytes = new TextEncoder().encode(svg);
    let binary = '';
    for (let i=0; i<bytes.length; i+=0x8000) binary += String.fromCharCode(...bytes.subarray(i,i+0x8000));
    const src = 'data:image/svg+xml;base64,' + btoa(binary);
    if (src.length >= 390000) throw new Error(txt('그림이 커서 첨부할 수 없습니다.', 'The figure is too large to attach.'));
    const m = /viewBox="0 0 ([\d.]+) ([\d.]+)"/.exec(svg);
    return {src, w:m ? +m[1] : 800, h:m ? +m[2] : 400, scene:clean};
  }
  function pickFigure(storage, {onPick, height, local, allowIllustrations = false}) {
    const dialog = make('dialog', null, 'stdlg');
    const head = make('div', null, 'dlg-head');
    head.append(make('h2', txt('그림 불러오기','Import figure')), button(txt('닫기','Close'), () => dialog.close()));
    const host = make('div'), choices = make('div'), status = make('p', null, 'note');
    status.setAttribute('role', 'status');
    dialog.append(head, host, choices, status);
    dialog.onclose = () => dialog.remove();
    document.body.append(dialog);
    dialog.showModal();
    async function choose(scene, el) {
      el.disabled = true;
      try {
        const attachment = await figure(scene);
        if (!dialog.open) return;
        await onPick(attachment);
        dialog.close();
      } catch (e) { status.textContent = error(e); }
      finally { el.disabled = false; height?.(); }
    }
    const showPages = (raw, name) => {
      if (allowIllustrations && raw?.format === 'haslalab-illustration') {
        const src = raw.image, w = raw.width, h = raw.height;
        if (typeof src !== 'string' || src.length >= 390000 || !/^data:image\/(png|jpeg|webp);base64,[A-Za-z0-9+/]+={0,2}$/.test(src) ||
          !Number.isInteger(w) || w < 1 || w > 2000 || !Number.isInteger(h) || h < 1 || h > 2000)
          throw new Error(txt('삽화 파일을 읽을 수 없습니다.', 'Could not read the illustration.'));
        const preview = make('img'); preview.src = src; preview.alt = raw.title || txt('삽화','Illustration');
        preview.style.maxWidth = '100%'; preview.style.maxHeight = '180px';
        const use = button(txt('이 삽화 사용','Use this illustration'), async () => {
          use.disabled = true;
          try { await onPick({src,w,h}); if (dialog.open) dialog.close(); }
          catch (e) { status.textContent = error(e); } finally { use.disabled = false; height?.(); }
        });
        choices.replaceChildren(preview, use);
        use.focus();
        return;
      }
      const list = pages(raw);
      choices.replaceChildren(make('h3', name.replace(/\.json$/i,'')));
      for (const [i, scene] of list.entries()) {
        const label = (i+1) + ' · ' + (scene?.title || txt('그림','Figure'));
        const el = button(label, () => choose(scene, el));
        choices.append(el);
      }
      choices.querySelector('button')?.focus();
    };
    library(host, storage, {kind:allowIllustrations ? 'attachment' : 'figure', title:allowIllustrations ? txt('그림과 삽화','Figures and illustrations') : txt('그림 프로젝트','Figure projects'), height,
      onOpen: (raw, entry) => showPages(raw, entry.name),
      onResume: local ? () => showPages(local, txt('현재 브라우저 작업','Current browser draft')) : null});
  }
  function panelControls(bodyId, {collapse = true} = {}) {
    return '<span class="dock-controls">' + (collapse ? '<button type="button" data-dock-action="collapse" aria-controls="'+bodyId+'" aria-expanded="true">'+txt('접기','Collapse')+'</button>' : '') +
      '<button type="button" data-dock-action="expand" aria-controls="'+bodyId+'" aria-pressed="false">'+txt('확대','Expand')+'</button></span>';
  }
  function bindPanels(grid, changed) {
    const controls = [...grid.querySelectorAll('[data-dock]')].map(panel => ({
      panel, body:panel.querySelector('[data-dock-body]'),
      collapse:panel.querySelector('[data-dock-action="collapse"]'), expand:panel.querySelector('[data-dock-action="expand"]'),
    }));
    function layout(expanded) {
      grid.classList.toggle('is-dock-expanded', !!expanded);
      for (const {panel,expand} of controls) {
        const on = panel === expanded;
        panel.classList.toggle('is-dock-expanded-item', on);
        expand.setAttribute('aria-pressed',String(on));
        expand.textContent = on ? txt('복원','Restore') : txt('확대','Expand');
      }
      changed();
    }
    for (const {panel,body,collapse,expand} of controls) {
      function setCollapsed(on) {
        body.hidden = on;panel.classList.toggle('is-dock-collapsed',on);
        collapse.setAttribute('aria-expanded', String(!on));
        collapse.textContent = on ? txt('펼치기','Show') : txt('접기','Collapse');
      }
      if (collapse) collapse.onclick = () => { setCollapsed(!body.hidden); changed(); };
      expand.onclick = () => {
        const on = !panel.classList.contains('is-dock-expanded-item');
        if (on && collapse && body.hidden) setCollapsed(false);
        layout(on ? panel : null);
      };
    }
    return {
      restore:() => { if (grid.classList.contains('is-dock-expanded')) layout(null); },
      reveal:panel => { const item = controls.find(item => item.panel === panel); if (item?.body?.hidden) item.collapse?.click(); },
    };
  }
  window.HL_WORKSHOP_PROJECTS = {client, library, providerSelect, pickFigure, error, panelControls, bindPanels};
})();
