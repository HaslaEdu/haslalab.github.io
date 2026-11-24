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
        const folder = kind === 'compute' ? '전산물리' : '그림';
        return (r.files || []).filter(f => f.folder === folder && /\.json$/i.test(f.name)).map(f => ({...f, provider}));
      }
      const r = await request(connector(provider, 'files'));
      return (r.files || []).filter(f => !f.folder && /\.json$/i.test(f.name) &&
        (f.name.endsWith(suffix(kind)) || !/-haslalab-(figure|compute)\.json$/i.test(f.name))).map(f => ({...f, provider, scope: provider === 'github' ? scopeOf(r) : null}));
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
  function library(host, storage, {kind, title, onOpen, onNew, onResume, initial = 'store', height = () => {}}) {
    const heading = make('h1', title, 'project-library-title'); heading.tabIndex = -1;
    const tools = make('div', null, 'row project-library-tools');
    const select = providerSelect(initial);
    const list = make('div', null, 'grid project-library-grid');
    const status = make('p', null, 'note'); status.setAttribute('role', 'status');
    if (onNew) tools.append(button(txt('새 프로젝트', 'New project'), onNew, 'primary'));
    if (onResume) tools.append(button(txt('현재 작업 이어서', 'Resume current work'), onResume));
    tools.append(select);
    const storageLink = make('a', txt('저장소 연결 관리', 'Manage storage connections'), 'btn');
    storageLink.href = '/#/workshop/storage'; storageLink.target = '_top'; tools.append(storageLink);
    host.replaceChildren(heading, tools, status, list);
    let generation = 0, opening = 0;
    async function refresh() {
      const round = ++generation;
      list.replaceChildren();
      status.textContent = txt('프로젝트 불러오는 중…', 'Loading projects…');
      try {
        const rows = await storage.list(kind, select.value);
        if (round !== generation || !host.isConnected) return;
        status.textContent = rows.length ? '' : txt('이 저장소에 저장한 프로젝트가 없습니다.', 'No projects in this location.');
        for (const entry of rows) {
          const name = entry.name.replace(/(?:-[a-f0-9]{8}-haslalab-(?:figure|compute))?\.json$/i, '');
          const item = button(name, async () => {
            const selection = ++opening;
            item.disabled = true;
            status.textContent = txt('프로젝트 여는 중…', 'Opening project…');
            try {
              const data = await storage.load(entry);
              if (round !== generation || selection !== opening || !host.isConnected || host.hidden) return;
              await onOpen(data, entry);
              status.textContent = '';
            } catch (e) { if (round === generation) status.textContent = error(e); }
            finally { item.disabled = false; height(); }
          }, 'card project-library-card');
          const stamp = entry.modified || (typeof entry.updated_at === 'number' ? new Date(entry.updated_at*1000) : null);
          if (stamp && Number.isFinite(new Date(stamp).valueOf())) item.append(make('span', new Date(stamp).toLocaleDateString(document.documentElement.lang), 'note'));
          list.append(item);
        }
      } catch (e) {
        if (round === generation) status.textContent = error(e);
      } finally { height(); }
    }
    select.onchange = refresh;
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
  async function figure(scene) {
    const [S,R] = await Promise.all([import('./draw-scene.mjs'), import('./draw-render.mjs')]);
    const v = S.validateScene(scene);
    if (!v.ok) throw new Error(txt('그림 데이터를 읽을 수 없습니다.', 'Could not read the figure.'));
    const clean = v.scene, view = clean.view || S.sceneBounds(clean);
    const svg = R.renderSVG(clean, {width:800, view, ...R.printScale(clean.style, clean.printW)});
    const bytes = new TextEncoder().encode(svg);
    let binary = '';
    for (let i=0; i<bytes.length; i+=0x8000) binary += String.fromCharCode(...bytes.subarray(i,i+0x8000));
    const src = 'data:image/svg+xml;base64,' + btoa(binary);
    if (src.length >= 390000) throw new Error(txt('그림이 커서 첨부할 수 없습니다.', 'The figure is too large to attach.'));
    const m = /viewBox="0 0 ([\d.]+) ([\d.]+)"/.exec(svg);
    return {src, w:m ? +m[1] : 800, h:m ? +m[2] : 400, scene:clean};
  }
  function pickFigure(storage, {onPick, height, local}) {
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
      const list = pages(raw);
      choices.replaceChildren(make('h3', name.replace(/\.json$/i,'')));
      for (const [i, scene] of list.entries()) {
        const label = (i+1) + ' · ' + (scene?.title || txt('그림','Figure'));
        const el = button(label, () => choose(scene, el));
        choices.append(el);
      }
      choices.querySelector('button')?.focus();
    };
    library(host, storage, {kind:'figure', title:txt('그림 프로젝트','Figure projects'), height,
      onOpen: (raw, entry) => showPages(raw, entry.name),
      onResume: local ? () => showPages(local, txt('현재 브라우저 작업','Current browser draft')) : null});
  }
  window.HL_WORKSHOP_PROJECTS = {client, library, providerSelect, pickFigure, error};
})();
