/* Class and club materials are private to signed-in members of the selected group.
   The groups part (community/src/workshop-groups.js): the member's groups as cards with the first faces, one group's
   detail (members with picture, nickname, role and dates; invite codes and join requests for the owner and admins;
   settings), and "코드로 참여": an eight-letter code (XXXX-XXXX) is enough to join.
   Addresses: #/workshop/storage?group=<id> opens a group, ?code=XXXX-XXXX (the invite link) fills in the code and shows
   what it joins; the old ?invite=<six letters> links still work. */
(() => {
  const path = '/workshop/storage/shared', G = '/workshop/storage/groups';
  const ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  /* what the member typed, as XXXX-XXXX while typing (or the six letters of a class code) */
  function formatCode(v) {
    const s = String(v || '').toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 8);
    return s.length > 4 ? s.slice(0, 4) + '-' + s.slice(4) : s;
  }
  const codeOk = v => { const s = String(v || '').toUpperCase().replace(/[\s-]/g, ''); return (s.length === 8 && [...s].every(ch => ALPHABET.includes(ch))) || /^[A-Z0-9]{6}$/.test(s); };
  /* the page's address: which group is open and which code came in a link */
  function route(hash) {
    const params = new URLSearchParams(String(hash || '').split('?')[1] || '');
    const group = /^\d{1,12}$/.test(params.get('group') || '') ? Number(params.get('group')) : null;
    const raw = params.get('code') || params.get('invite') || '';
    return {group, code: codeOk(raw) ? formatCode(raw) : ''};
  }
  function setParams(change) {
    const [head, query] = location.hash.split('?');
    const params = new URLSearchParams(query || '');
    for (const [k, v] of Object.entries(change)) { if (v == null || v === '') params.delete(k); else params.set(k, v); }
    history.replaceState(history.state, '', (head || '#/workshop/storage') + (params.size ? '?' + params : ''));
  }
  const AV = /^[A-Za-z0-9_-]{8,32}$/;
  function letterAvatar(name, cls, esc) {
    const n = String(name || '?'); let h = 0; for (const ch of n) h = (h * 31 + ch.codePointAt(0)) >>> 0;
    return `<span class="cmav ${cls}" aria-hidden="true" style="background:hsl(${h % 360} 55% 46%)">${esc(([...n][0] || '?').toUpperCase())}</span>`;
  }
  const CSS = `.wsg{display:grid;gap:14px;margin:0 0 18px}.wsg [hidden]{display:none!important}
.wsg-top{display:flex;flex-wrap:wrap;gap:10px 16px;align-items:flex-end;justify-content:space-between}
.wsg-join{display:flex;gap:8px;align-items:flex-end;flex:1 1 280px;max-width:420px}
.wsg label{display:grid;gap:4px;font-size:13px;min-width:0}
.wsg-join label{flex:1}
.wsg :is(input,select,textarea),.wsg-dialog :is(input,select){width:100%;box-sizing:border-box;font:inherit;color:inherit;padding:7px 9px;border:1px solid var(--rule,#d5dbe6);border-radius:8px;background:var(--paper,#fff)}
.wsg-code-in{font-family:var(--mono,monospace);letter-spacing:.12em;text-transform:uppercase}
.wsg-cards{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(min(260px,100%),1fr));gap:10px}
.wsg-card{display:grid;gap:8px;width:100%;text-align:start;font:inherit;color:inherit;background:var(--paper,#fff);border:1px solid var(--rule,#d5dbe6);border-radius:12px;padding:12px 14px;cursor:pointer}
.wsg-card:hover{border-color:#7059a4}
.wsg-card b{font-size:15px;overflow-wrap:anywhere}
.wsg-card p{margin:0;font-size:13px;color:var(--graphite,#5c6b7a);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.wsg-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap;min-width:0}
.wsg-sp{flex:1}
.wsg-role{font-size:11px;font-weight:600;padding:1px 7px;border-radius:99px;background:#eceaf4;color:#4a3575;white-space:nowrap}
.wsg-role.owner{background:#5c438f;color:#fff}.wsg-role.admin{background:#dcd3ef}
.wsg-badge{font-size:11px;font-weight:600;padding:1px 7px;border-radius:99px;background:#fdecc8;color:#7a4b00}
.wsg-stack{display:flex;align-items:center}
.wsg-stack .cmav{width:28px;height:28px;border-radius:50%;border:2px solid var(--paper,#fff);margin-inline-start:-8px;display:inline-grid;place-items:center;color:#fff;font:600 12px var(--sans);object-fit:cover}
.wsg-stack .cmav:first-child{margin-inline-start:0}
.wsg-more{margin-inline-start:-8px;width:28px;height:28px;border-radius:50%;border:2px solid var(--paper,#fff);background:#e6e9ef;color:#3a4657;display:inline-grid;place-items:center;font:600 11px var(--sans)}
.wsg-count{font-size:13px;color:var(--graphite,#5c6b7a)}
.wsg-av{width:36px;height:36px;border-radius:50%;flex:none;display:inline-grid;place-items:center;color:#fff;font:600 14px var(--sans);object-fit:cover}
.wsg-av.sm{width:24px;height:24px;font-size:11px}
/* doubled class: the site's .ws section{padding:0} would otherwise win */
.wsg .wsg-panel.wsg-panel{background:var(--paper,#fff);border:1px solid var(--rule,#d5dbe6);border-radius:12px;padding:14px 16px;display:grid;gap:10px}
.wsg-panel h3,.wsg-panel h4{margin:0}.wsg-panel h4{font-size:14px}
.wsg-panel p{margin:0}
.wsg-meta{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:13px;color:var(--graphite,#5c6b7a)}
.wsg-bar{height:6px;border-radius:9px;background:#e8ebf1;overflow:hidden}.wsg-bar span{display:block;height:100%;background:#7059a4}
.wsg-list{list-style:none;margin:0;padding:0;display:grid}
.wsg-list li{display:flex;align-items:center;gap:10px;padding:9px 0;border-top:1px solid var(--rule,#e3e7ee);flex-wrap:wrap}
.wsg-list li:first-child{border-top:0}
.wsg-who{display:grid;min-width:0;flex:1 1 140px}.wsg-who b{overflow-wrap:anywhere}.wsg-who small{color:var(--graphite,#5c6b7a);font-size:12px}
.wsg-acts{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.wsg-acts select{width:auto}
.wsg-code{font:600 26px var(--mono,monospace);letter-spacing:.14em;text-align:center;padding:10px;border:1px dashed #7059a4;border-radius:10px;background:#f6f3fc;color:#3d2c63}
.wsg-confirm{border-color:#7059a4;box-shadow:0 0 0 3px #7059a41f}
.wsg-confirm .wsg-av{width:48px;height:48px;font-size:18px}
.wsg-danger{border-color:#e7b4b4}
.wsg-danger .ws-btn.bad{color:#a01818;border-color:#e0a5a5}
.wsg-check{display:flex!important;align-items:center;gap:8px;grid-template-columns:none}
.wsg-check input{width:auto}
.wsg-dialog{width:min(440px,calc(100% - 24px));border:1px solid var(--rule,#d5dbe6);border-radius:14px;color:var(--ink);background:var(--paper,#fff);padding:20px}
.wsg-dialog::backdrop{background:#17203675}.wsg-dialog form{display:grid;gap:12px}.wsg-dialog h2,.wsg-dialog p{margin:0}.wsg-dialog label{display:grid;gap:4px;font-size:13px}
.wsg-note{font-size:13px;color:var(--graphite,#5c6b7a)}
.wsg-back{justify-self:start}
@media(max-width:520px){.wsg-join{max-width:none}.wsg-list li .wsg-acts{margin-inline-start:46px}.wsg .wsg-panel.wsg-panel{padding:12px}.wsg-code{font-size:22px}}`;

  window.HL_WS_CLASS_STORAGE = function mount({host, root, api, fetchFile, text, esc, error, files, folders, here, av}) {
    const tr = text;
    if (!document.getElementById('wsg-css')) { const s = document.createElement('style'); s.id = 'wsg-css'; s.textContent = CSS; document.head.append(s); }
    const face = (name, key, cls = 'wsg-av') => (typeof av === 'function' ? av(name, cls, key && AV.test(key) ? key : null) : letterAvatar(name, cls, esc));
    const locale = tr('ko-KR', 'en-US');
    const date = t => (t ? new Date(t * 1000).toLocaleDateString(locale) : '');
    const bytes = n => (n >= 1048576 ? (n / 1048576).toFixed(1) + ' MB' : n >= 1024 ? Math.round(n / 1024) + ' KB' : (n || 0) + ' B');
    const roleName = r => ({owner: tr('소유자', 'Owner'), admin: tr('관리자', 'Admin'), member: tr('멤버', 'Member')}[r] || r);
    const folderPlaceholder = tr('폴더 선택', 'Choose a folder');
    const sharedLabel = tr('학급·동아리 공유 보관함', 'Shared storage for classes and clubs');
    const empty = tr('아직 공유한 자료나 과제가 없습니다.', 'No materials or assignments have been shared yet.');
    const message = e => ({
      bad_code: tr('초대 코드를 확인해 주세요. 예: ABCD-EF23', 'Check the invite code, e.g. ABCD-EF23.'),
      invite_not_found: tr('이 코드로 참여할 수 있는 그룹이 없습니다.', 'No group matches this code.'),
      class_not_found: tr('이 코드로 참여할 수 있는 그룹이 없습니다.', 'No active group matches this code.'),
      group_not_found: tr('그룹을 찾을 수 없거나 더 이상 멤버가 아닙니다.', 'The group was not found or you are no longer a member.'),
      invite_expired: tr('만료된 초대 코드입니다. 새 코드를 받아 주세요.', 'This invite code has expired. Ask for a new one.'),
      invite_used_up: tr('사용 횟수를 모두 쓴 초대 코드입니다.', 'This invite code has no uses left.'),
      join_locked: tr('잘못된 코드를 여러 번 입력해 잠시 잠겼습니다. 1시간 뒤에 다시 시도해 주세요.', 'Too many wrong codes. Try again in an hour.'),
      rate_limited: tr('잠시 뒤에 다시 시도해 주세요.', 'Try again in a moment.'),
      removed_from_group: tr('이 그룹에서 내보내졌습니다. 관리자에게 새 초대 코드를 받아 주세요.', 'You were removed from this group. Ask a manager for a new code.'),
      join_pending: tr('참여 요청을 보냈습니다. 승인을 기다려 주세요.', 'Request sent. Wait for approval.'),
      class_full: tr('그룹의 정원이 찼습니다.', 'This group is full.'),
      class_limit: tr('만들 수 있는 그룹 수에 도달했습니다.', 'You have reached the group limit.'),
      invite_limit: tr('사용 중인 초대 코드가 너무 많습니다. 쓰지 않는 코드를 취소해 주세요.', 'Too many active codes. Revoke one first.'),
      request_limit: tr('참여 요청이 너무 많이 쌓였습니다.', 'Too many pending requests.'),
      owner_must_transfer: tr('소유자는 먼저 다른 멤버에게 소유권을 넘겨야 나갈 수 있습니다.', 'Transfer ownership before leaving.'),
      confirm_name: tr('그룹 이름을 정확히 입력해 주세요.', 'Type the group name exactly.'),
      member_not_found: tr('멤버를 찾을 수 없습니다.', 'Member not found.'),
      request_not_found: tr('요청을 찾을 수 없습니다.', 'Request not found.'),
      bad_name: tr('그룹 이름을 입력해 주세요.', 'Enter a group name.'),
      bad_description: tr('소개는 300자까지 쓸 수 있습니다.', 'The description can be up to 300 characters.'),
      bad_share: tr('제목과 파일, 마감 시간을 확인해 주세요.', 'Check the title, file and due date.'),
      forbidden: tr('권한이 없습니다.', 'You do not have permission.'),
      not_found: tr('자료를 찾을 수 없습니다.', 'The material could not be found.'),
      share_too_many_files: tr('한 번에 파일 200개까지 공유할 수 있습니다.', 'Share up to 200 files at a time.'),
      bad_worksheet: tr('과제용 JSON은 문제 제작에서 저장한 문제나 시험지를 사용해 주세요.', 'Use a problem or paper from the problem maker for JSON assignments.'),
      share_limit: tr('공유한 자료가 너무 많습니다. 기존 공유를 정리해 주세요.', 'Remove an old share before adding another.')
    }[e?.code] || error(e?.code));
    let groups = null;
    const getGroups = fresh => (!fresh && groups ? Promise.resolve(groups) : api('GET', G, undefined, {forcePrimary: !!fresh}).then(d => (groups = d.groups || [])));
    const saveFile = async (share, file, name, worksheet) => {
      const response = await fetchFile('GET', '/shared/' + share + '/files/' + file);
      if (worksheet) {
        const data = await response.json();
        if (data.format !== 'haslalab-assignment') throw {code: 'bad_worksheet'};
        const dialog = document.createElement('dialog');
        dialog.className = 'ws-share-dialog ws-student-paper';
        const title = document.createElement('h2'), list = document.createElement('ol'), close = document.createElement('button');
        title.textContent = data.title || name;
        close.type = 'button'; close.className = 'ws-btn'; close.textContent = tr('닫기', 'Close');
        close.onclick = () => dialog.close(); dialog.onclose = () => dialog.remove();
        for (const question of data.items) {
          const row = document.createElement('li'), text = document.createElement('p');
          text.textContent = question.text;
          row.append(text);
          if (question.figure && /^data:image\/svg\+xml;base64,/.test(question.figure)) {
            const figure = new Image(); figure.src = question.figure; figure.alt = tr('문제 그림', 'Problem figure'); row.append(figure);
          }
          if (question.choices.length) {
            const options = document.createElement('ol'); options.type = 'A';
            for (const choice of question.choices) { const li = document.createElement('li'); li.textContent = choice; options.append(li); }
            row.append(options);
          }
          list.append(row);
        }
        dialog.append(title, list, close); root.append(dialog);
        window.renderMathInElement?.(list, {delimiters: [{left: '$$', right: '$$', display: true}, {left: '$', right: '$', display: false}], throwOnError: false});
        dialog.showModal();
        return;
      }
      const b = await response.blob();
      const url = URL.createObjectURL(b), a = document.createElement('a');
      a.href = url;
      a.download = name;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 30000);
    };
    const label = kind => kind === 'assignment' ? tr('과제', 'Assignment') : tr('공유 자료', 'Material');
    function refresh(fresh = false) {
      return api('GET', path, undefined, {forcePrimary: fresh}).then(({shares}) => {
        if (!here() || !host.isConnected) return;
        const area = host.querySelector('[data-shared-list]');
        area.innerHTML = shares.length ? shares.map(s => `<details class="ws-share-item" data-share="${esc(s.id)}" data-share-kind="${esc(s.kind)}"><summary>${esc(s.title)} <small>${esc(s.group_name)} · ${label(s.kind)} · ${s.file_count}</small></summary>
          ${s.instructions ? `<p class="ws-share-instructions">${esc(s.instructions)}</p>` : ''}
          ${s.due_at ? `<p>${tr('마감', 'Due')} <time datetime="${new Date(s.due_at * 1000).toISOString()}">${new Date(s.due_at * 1000).toLocaleString()}</time></p>` : ''}
          <ul></ul><p role="status"></p>${s.mine ? `<button type="button" class="ws-btn" data-revoke>${tr('공유 취소', 'Stop sharing')}</button>` : ''}</details>`).join('') : `<p>${empty}</p>`;
        area.querySelectorAll('[data-share]').forEach(item => {
          const id = item.dataset.share, status = item.querySelector('[role=status]');
          item.ontoggle = async () => {
            if (!item.open) return;
            try {
              const {files} = await api('GET', path + '/' + id);
              item.querySelector('ul').replaceChildren(...files.map(f => {
                const li = document.createElement('li'), b = document.createElement('button');
                b.type = 'button';
                b.className = 'ws-btn';
                b.textContent = f.name;
                const worksheet = item.dataset.shareKind === 'assignment' && f.mime === 'application/json';
                b.onclick = async () => { try { await saveFile(id, f.id, f.name, worksheet); } catch (e) { status.textContent = message(e); } };
                li.append(b);
                return li;
              }));
              status.textContent = files.length ? '' : tr('공유할 수 있는 파일이 없습니다.', 'No shared files are available.');
            } catch (e) { status.textContent = message(e); }
          };
          const revoke = item.querySelector('[data-revoke]');
          if (revoke) revoke.onclick = async () => {
            try { await api('DELETE', path + '/' + id); await refresh(true); }
            catch (e) { status.textContent = message(e); }
          };
        });
      });
    }
    host.innerHTML = `<h2>${sharedLabel}</h2><div class="wsg" data-groups></div><p class="ws-note" data-shared-status role="status"></p>
      <h3 class="wsg-shared-h">${tr('공유된 자료와 과제', 'Shared materials and assignments')}</h3><div data-shared-list></div>`;
    const status = host.querySelector('[data-shared-status]');
    const box = host.querySelector('[data-groups]');
    const alive = () => here() && box.isConnected;
    refresh().catch(e => { status.textContent = message(e); });

    /* ── the list: join by code, make a group, the member's groups as cards ── */
    function stack(g) {
      const shown = (g.avatars || []).slice(0, 5), more = Math.max(0, g.member_count - shown.length);
      return `<span class="wsg-stack" aria-hidden="true">${shown.map(p => face(p.nickname, p.avatar, '')).join('')}${more ? `<span class="wsg-more">+${more}</span>` : ''}</span>`;
    }
    function paintList(note = '') {
      if (!alive()) return;
      const {code} = route(location.hash);
      box.innerHTML = `<div class="wsg-top">
          <form class="wsg-join" data-wsg-join novalidate><label>${tr('코드로 참여', 'Join with a code')}<input name="code" class="wsg-code-in" placeholder="XXXX-XXXX" maxlength="9" autocomplete="off" autocapitalize="characters" spellcheck="false" inputmode="text" value="${esc(code)}" aria-describedby="wsg-join-hint"></label><button type="submit" class="ws-btn pri">${tr('확인', 'Check')}</button></form>
          <button type="button" class="ws-btn" data-wsg-new aria-expanded="false">+ ${tr('새 그룹 만들기', 'New group')}</button>
        </div>
        <p class="wsg-note" id="wsg-join-hint">${tr('받은 초대 코드 8자리만 입력하면 됩니다. 대소문자와 하이픈은 상관없습니다.', 'Enter the eight-character code you received. Case and dashes do not matter.')}</p>
        <div data-wsg-confirm></div>
        <form class="wsg-panel" data-wsg-create hidden><h4>${tr('새 그룹', 'New group')}</h4>
          <label>${tr('학급 또는 동아리 이름', 'Class or club name')}<input name="name" maxlength="60" required></label>
          <label>${tr('소개 (선택)', 'Description (optional)')}<textarea name="description" maxlength="300" rows="2"></textarea></label>
          <label class="wsg-check"><input type="checkbox" name="approval"> ${tr('참여 승인 필요', 'Require approval to join')}</label>
          <div class="wsg-acts"><button type="submit" class="ws-btn pri">${tr('그룹 만들기', 'Create group')}</button><button type="button" class="ws-btn ghost" data-wsg-cancel>${tr('취소', 'Cancel')}</button></div></form>
        <p class="ws-note" role="status" data-wsg-status>${esc(note)}</p>
        <div data-wsg-cards><p class="wsg-note">${tr('그룹을 불러오는 중…', 'Loading groups…')}</p></div>`;
      const st = box.querySelector('[data-wsg-status]'), join = box.querySelector('[data-wsg-join]'), input = join.elements.code;
      const create = box.querySelector('[data-wsg-create]'), newBtn = box.querySelector('[data-wsg-new]');
      input.addEventListener('input', () => { input.value = formatCode(input.value); });
      join.onsubmit = event => { event.preventDefault(); preview(input.value); };
      newBtn.onclick = () => { create.hidden = !create.hidden; newBtn.setAttribute('aria-expanded', String(!create.hidden)); if (!create.hidden) create.elements.name.focus(); };
      create.querySelector('[data-wsg-cancel]').onclick = () => { create.hidden = true; newBtn.setAttribute('aria-expanded', 'false'); };
      create.onsubmit = async event => {
        event.preventDefault();
        const f = create.elements, button = create.querySelector('[type=submit]');
        button.disabled = true;
        try {
          const g = await api('POST', G, {name: f.name.value, description: f.description.value, approval: f.approval.checked});
          await getGroups(true);
          openGroup(g.id, tr('그룹을 만들었습니다. 초대 코드를 만들어 멤버에게 보내세요.', 'Group created. Make an invite code for your members.'));
        } catch (e) { st.textContent = message(e); }
        finally { button.disabled = false; }
      };
      getGroups().then(list => {
        if (!alive() || !box.querySelector('[data-wsg-cards]')) return;
        const cards = box.querySelector('[data-wsg-cards]');
        cards.innerHTML = list.length ? `<ul class="wsg-cards">${list.map(g => `<li><button type="button" class="wsg-card" data-wsg-open="${+g.id}">
            <span class="wsg-row"><b>${esc(g.name)}</b><span class="wsg-sp"></span><span class="wsg-role ${esc(g.role)}">${roleName(g.role)}</span></span>
            ${g.description ? `<p>${esc(g.description)}</p>` : ''}
            <span class="wsg-row">${stack(g)}<span class="wsg-count">${tr(`${g.member_count}명`, `${g.member_count} member${g.member_count === 1 ? '' : 's'}`)}</span><span class="wsg-sp"></span>${g.pending_requests ? `<span class="wsg-badge">${tr(`요청 ${g.pending_requests}`, `${g.pending_requests} waiting`)}</span>` : ''}${g.approval ? `<span class="wsg-count" title="${tr('참여 승인 필요', 'Approval required')}">🔒</span>` : ''}</span>
          </button></li>`).join('')}</ul>`
          : `<p class="wsg-note">${tr('아직 참여한 그룹이 없습니다. 받은 코드로 참여하거나 새 그룹을 만드세요.', 'No groups yet. Join with a code or create a group.')}</p>`;
        cards.querySelectorAll('[data-wsg-open]').forEach(b => b.onclick = () => openGroup(Number(b.dataset.wsgOpen)));
      }).catch(e => { const c = box.querySelector('[data-wsg-cards]'); if (c) c.textContent = message(e); });
      if (code) preview(code);
    }

    /* the code's group, to confirm before joining */
    async function preview(raw) {
      const area = box.querySelector('[data-wsg-confirm]'), st = box.querySelector('[data-wsg-status]');
      if (!area) return;
      st.textContent = '';
      if (!codeOk(raw)) { st.textContent = message({code: 'bad_code'}); return; }
      const code = formatCode(raw);
      area.innerHTML = `<p class="wsg-note">${tr('확인하는 중…', 'Checking…')}</p>`;
      let g;
      try { ({group: g} = await api('POST', G + '/preview', {code})); }
      catch (e) { area.innerHTML = ''; st.textContent = message(e); return; }
      if (!alive()) return;
      const action = g.member ? '' : g.pending ? `<p class="wsg-note">${tr('참여 요청을 보냈습니다. 소유자나 관리자의 승인을 기다리는 중입니다.', 'Your request is waiting for approval.')}</p>`
        : `<button type="button" class="ws-btn pri" data-wsg-do>${g.approval ? tr('참여 요청 보내기', 'Ask to join') : tr('참여하기', 'Join')}</button>`;
      area.innerHTML = `<section class="wsg-panel wsg-confirm" aria-labelledby="wsg-confirm-h">
        <div class="wsg-row">${face(g.owner.nickname, g.owner.avatar)}<div class="wsg-who"><small>${tr(`${esc(g.owner.nickname)} 님의 그룹`, `A group by ${esc(g.owner.nickname)}`)}</small><b id="wsg-confirm-h">${esc(g.name)}</b></div></div>
        ${g.description ? `<p>${esc(g.description)}</p>` : ''}
        <p class="wsg-meta"><span>${tr(`멤버 ${g.member_count}명`, `${g.member_count} member${g.member_count === 1 ? '' : 's'}`)}</span>${g.approval ? `<span>🔒 ${tr('소유자나 관리자가 승인하면 참여됩니다', 'A manager approves new members')}</span>` : ''}</p>
        ${g.member ? `<p>${tr('이미 이 그룹의 멤버입니다.', 'You are already a member.')}</p>` : ''}
        <div class="wsg-acts">${action}<button type="button" class="ws-btn ghost" data-wsg-dismiss>${tr('닫기', 'Close')}</button></div></section>`;
      area.querySelector('[data-wsg-dismiss]').onclick = () => { area.innerHTML = ''; setParams({code: null, invite: null}); };
      const go = area.querySelector('[data-wsg-do]');
      if (go) go.onclick = async () => {
        go.disabled = true;
        try {
          const r = await api('POST', G + '/join', {code});
          setParams({code: null, invite: null});
          await getGroups(true);
          if (r.status === 'pending') { paintList(tr('참여 요청을 보냈습니다. 승인되면 그룹이 목록에 나타납니다.', 'Request sent. The group appears here once approved.')); return; }
          refresh(true).catch(() => {});
          openGroup(r.group.id, r.status === 'joined' ? tr('그룹에 참여했습니다.', 'You joined the group.') : '');
        } catch (e) { go.disabled = false; st.textContent = message(e); }
      };
    }

    function openGroup(id, note = '') { setParams({group: id, code: null, invite: null}); paintDetail(id, note); }
    function closeGroup(note = '') { setParams({group: null}); paintList(note); }

    /* ── one group ── */
    async function paintDetail(id, note = '') {
      if (!alive()) return;
      box.innerHTML = `<button type="button" class="ws-btn ghost wsg-back" data-wsg-back>← ${tr('내 그룹', 'My groups')}</button><p class="wsg-note">${tr('불러오는 중…', 'Loading…')}</p>`;
      box.querySelector('[data-wsg-back]').onclick = () => closeGroup();
      let d;
      try { d = await api('GET', G + '/' + id, undefined, {forcePrimary: true}); }
      catch (e) { if (alive()) { getGroups(true).catch(() => {}); closeGroup(message(e)); } return; }
      if (!alive()) return;
      const g = d.group, owner = g.role === 'owner', manager = g.role !== 'member';
      const pct = g.storage.quota ? Math.min(100, Math.round(g.storage.used / g.storage.quota * 1000) / 10) : 0;
      const expiry = i => (i.expires_at ? tr(`${date(i.expires_at)}까지`, `until ${date(i.expires_at)}`) : tr('만료 없음', 'No expiry'));
      const uses = i => (i.max_uses == null ? tr(`${i.uses}회 사용 · 제한 없음`, `${i.uses} used · unlimited`) : tr(`${i.uses}/${i.max_uses}회 사용`, `${i.uses}/${i.max_uses} used`));
      const memberRow = m => {
        const acts = [];
        if (owner && m.role !== 'owner') acts.push(`<select data-wsg-role="${esc(m.nickname)}" aria-label="${tr(`${esc(m.nickname)} 역할`, `Role of ${esc(m.nickname)}`)}"><option value="member"${m.role === 'member' ? ' selected' : ''}>${roleName('member')}</option><option value="admin"${m.role === 'admin' ? ' selected' : ''}>${roleName('admin')}</option></select>`);
        if (!m.me && m.role !== 'owner' && (owner || (manager && m.role === 'member'))) acts.push(`<button type="button" class="ws-btn" data-wsg-remove="${esc(m.nickname)}">${tr('내보내기', 'Remove')}</button>`);
        return `<li data-member="${esc(m.nickname)}">${face(m.nickname, m.avatar)}<span class="wsg-who"><b>${esc(m.nickname)}${m.me ? ` <small>(${tr('나', 'you')})</small>` : ''}</b>
          <small>${tr('참여', 'Joined')} ${date(m.joined_at)}${m.last_active_at ? ` · ${tr('최근 활동', 'Active')} ${date(m.last_active_at)}` : ''}</small></span>
          ${owner && m.role !== 'owner' ? '' : `<span class="wsg-role ${esc(m.role)}">${roleName(m.role)}</span>`}<span class="wsg-acts">${acts.join('')}</span></li>`;
      };
      const others = d.members.filter(m => m.role !== 'owner');
      box.innerHTML = `<button type="button" class="ws-btn ghost wsg-back" data-wsg-back>← ${tr('내 그룹', 'My groups')}</button>
        <section class="wsg-panel" aria-labelledby="wsg-h"><div class="wsg-row"><h3 id="wsg-h">${esc(g.name)}</h3><span class="wsg-role ${esc(g.role)}">${roleName(g.role)}</span>${g.approval ? `<span class="wsg-count">🔒 ${tr('참여 승인 필요', 'Approval required')}</span>` : ''}</div>
          ${g.description ? `<p>${esc(g.description)}</p>` : ''}
          <p class="wsg-meta"><span class="wsg-row">${face(g.owner.nickname, g.owner.avatar, 'wsg-av sm')} ${tr('소유자', 'Owner')} ${esc(g.owner.nickname)}</span><span>${tr('만든 날', 'Created')} ${date(g.created_at)}</span><span>${tr(`멤버 ${g.member_count}/${g.seats}명`, `${g.member_count}/${g.seats} members`)}</span></p>
          <div><div class="wsg-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}" aria-label="${tr('공유 자료 용량', 'Shared storage')}"><span style="width:${pct}%"></span></div>
          <p class="wsg-note">${tr(`공유 자료 ${bytes(g.storage.used)} / ${bytes(g.storage.quota)} · 파일 ${g.storage.files}개 · 공유 ${g.storage.shares}건`, `Shared ${bytes(g.storage.used)} / ${bytes(g.storage.quota)} · ${g.storage.files} files · ${g.storage.shares} shares`)}</p></div>
        </section>
        <p class="ws-note" role="status" data-wsg-status>${esc(note)}</p>
        ${manager ? `<section class="wsg-panel" aria-labelledby="wsg-inv-h"><div class="wsg-row"><h4 id="wsg-inv-h">${tr('초대 코드', 'Invite codes')}</h4><span class="wsg-sp"></span><button type="button" class="ws-btn pri" data-wsg-invite>${tr('초대 코드 만들기', 'New invite code')}</button></div>
          ${d.invites.length ? `<ul class="wsg-list">${d.invites.map(i => `<li><span class="wsg-who"><b>${tr(`<span class="mono">${esc(i.hint.slice(0, 2))}</span>로 시작하는 코드`, `Code starting <span class="mono">${esc(i.hint.slice(0, 2))}</span>`)}</b><small>${expiry(i)} · ${uses(i)}${i.created_by ? ' · ' + esc(i.created_by) : ''}</small></span>
            <span class="wsg-acts"><button type="button" class="ws-btn" data-wsg-regen="${esc(i.id)}">${tr('새로 만들기', 'Regenerate')}</button><button type="button" class="ws-btn" data-wsg-revoke="${esc(i.id)}">${tr('취소', 'Revoke')}</button></span></li>`).join('')}</ul>`
            : `<p class="wsg-note">${tr('사용 중인 초대 코드가 없습니다.', 'No active invite codes.')}</p>`}
          <p class="wsg-note">${tr('코드는 만들 때 한 번만 보입니다. 잊었다면 "새로 만들기"로 바꾸세요.', 'A code is shown once, when it is made. Regenerate it if it is lost.')}${g.class_code ? ` ${tr('기존 학급 코드', 'Class code')} <b class="mono">${esc(g.class_code)}</b>${tr('도 쓸 수 있습니다.', ' also works.')}` : ''}</p></section>` : ''}
        ${manager && d.requests.length ? `<section class="wsg-panel" aria-labelledby="wsg-req-h"><h4 id="wsg-req-h">${tr(`참여 요청 ${d.requests.length}`, `Join requests (${d.requests.length})`)}</h4><ul class="wsg-list">${d.requests.map(r => `<li>${face(r.nickname, r.avatar)}<span class="wsg-who"><b>${esc(r.nickname)}</b><small>${tr('요청', 'Asked')} ${date(r.requested_at)}</small></span>
          <span class="wsg-acts"><button type="button" class="ws-btn pri" data-wsg-approve="${esc(r.nickname)}">${tr('승인', 'Approve')}</button><button type="button" class="ws-btn" data-wsg-deny="${esc(r.nickname)}">${tr('거절', 'Decline')}</button></span></li>`).join('')}</ul></section>` : ''}
        <section class="wsg-panel" aria-labelledby="wsg-mem-h"><h4 id="wsg-mem-h">${tr(`멤버 ${d.members.length}명`, `Members (${d.members.length})`)}</h4><ul class="wsg-list" data-wsg-members>${d.members.map(memberRow).join('')}</ul></section>
        ${manager ? `<form class="wsg-panel" data-wsg-settings aria-labelledby="wsg-set-h"><h4 id="wsg-set-h">${tr('설정', 'Settings')}</h4>
          ${owner ? `<label>${tr('그룹 이름', 'Group name')}<input name="name" maxlength="60" required value="${esc(g.name)}"></label>` : ''}
          <label>${tr('소개', 'Description')}<textarea name="description" maxlength="300" rows="2">${esc(g.description)}</textarea></label>
          <label class="wsg-check"><input type="checkbox" name="approval"${g.approval ? ' checked' : ''}> ${tr('참여 승인 필요 (코드로 들어오면 요청으로 받습니다)', 'Require approval (a code sends a request)')}</label>
          ${owner ? `<label class="wsg-check"><input type="checkbox" name="legacy_code"${g.legacy_code ? ' checked' : ''}> ${tr('기존 6자리 학급 코드로도 참여 허용', 'Also accept the six-letter class code')}</label>` : ''}
          <div class="wsg-acts"><button type="submit" class="ws-btn pri">${tr('저장', 'Save')}</button></div></form>` : ''}
        ${owner ? `<section class="wsg-panel wsg-danger" aria-labelledby="wsg-own-h"><h4 id="wsg-own-h">${tr('소유권과 삭제', 'Ownership and deletion')}</h4>
          ${others.length ? `<div class="wsg-row"><label style="flex:1 1 180px">${tr('소유권 넘기기', 'Transfer ownership to')}<select data-wsg-heir>${others.map(m => `<option value="${esc(m.nickname)}">${esc(m.nickname)} · ${roleName(m.role)}</option>`).join('')}</select></label><button type="button" class="ws-btn" data-wsg-transfer>${tr('넘기기', 'Transfer')}</button></div>` : ''}
          <div class="wsg-row"><label style="flex:1 1 180px">${tr(`삭제하려면 그룹 이름 "${esc(g.name)}"을 입력하세요`, `Type "${esc(g.name)}" to delete the group`)}<input data-wsg-confirm-name autocomplete="off"></label><button type="button" class="ws-btn bad" data-wsg-delete disabled>${tr('그룹 삭제', 'Delete group')}</button></div>
          <p class="wsg-note">${tr('삭제하면 멤버 모두 접근할 수 없고 공유 목록이 사라집니다. 각자의 파일은 보관함에 남습니다.', 'Deleting removes everyone\'s access and the shared list. Each member\'s own files stay in their storage.')}</p></section>`
          : `<div><button type="button" class="ws-btn" data-wsg-leave>${tr('그룹 나가기', 'Leave group')}</button></div>`}`;
      const st = box.querySelector('[data-wsg-status]');
      const act = async (fn, done) => { try { const r = await fn(); await getGroups(true); if (done !== false) paintDetail(g.id, typeof done === 'function' ? done(r) : done || ''); return r; } catch (e) { st.textContent = message(e); } };
      const q = (sel, fn) => box.querySelectorAll(sel).forEach(fn);
      box.querySelector('[data-wsg-back]').onclick = () => closeGroup();
      q('[data-wsg-role]', s => s.onchange = () => act(() => api('PATCH', G + '/' + g.id + '/members/' + encodeURIComponent(s.dataset.wsgRole), {role: s.value}), tr('역할을 바꿨습니다.', 'Role changed.')));
      q('[data-wsg-remove]', b => b.onclick = () => {
        const n = b.dataset.wsgRemove;
        if (!window.confirm(tr(`${n} 님을 그룹에서 내보낼까요? 바로 접근할 수 없게 되고, 이 그룹에 공유한 자료도 내려갑니다.`, `Remove ${n}? They lose access at once and their shares to this group are withdrawn.`))) return;
        act(() => api('DELETE', G + '/' + g.id + '/members/' + encodeURIComponent(n)), tr('내보냈습니다.', 'Removed.'));
      });
      q('[data-wsg-approve]', b => b.onclick = () => act(() => api('POST', G + '/' + g.id + '/requests/' + encodeURIComponent(b.dataset.wsgApprove), {approve: true}), tr('승인했습니다.', 'Approved.')));
      q('[data-wsg-deny]', b => b.onclick = () => act(() => api('POST', G + '/' + g.id + '/requests/' + encodeURIComponent(b.dataset.wsgDeny), {approve: false}), tr('거절했습니다.', 'Declined.')));
      q('[data-wsg-revoke]', b => b.onclick = () => {
        if (!window.confirm(tr('이 초대 코드를 취소할까요? 더는 이 코드로 참여할 수 없습니다.', 'Revoke this code? It will stop working.'))) return;
        act(() => api('DELETE', G + '/' + g.id + '/invites/' + b.dataset.wsgRevoke), tr('초대 코드를 취소했습니다.', 'Code revoked.'));
      });
      q('[data-wsg-regen]', b => b.onclick = () => act(() => api('POST', G + '/' + g.id + '/invites/' + b.dataset.wsgRegen + '/regenerate', {}), false).then(r => { if (r) { paintDetail(g.id); showCode(g, r); } }));
      box.querySelector('[data-wsg-invite]')?.addEventListener('click', () => inviteDialog(g));
      const settings = box.querySelector('[data-wsg-settings]');
      if (settings) settings.onsubmit = event => {
        event.preventDefault();
        const f = settings.elements, change = {description: f.description.value, approval: f.approval.checked};
        if (owner) { change.name = f.name.value; change.legacy_code = f.legacy_code.checked; }
        act(() => api('PATCH', G + '/' + g.id, change), tr('저장했습니다.', 'Saved.'));
      };
      box.querySelector('[data-wsg-transfer]')?.addEventListener('click', () => {
        const n = box.querySelector('[data-wsg-heir]').value;
        if (!window.confirm(tr(`소유권을 ${n} 님에게 넘길까요? 나는 관리자가 됩니다.`, `Make ${n} the owner? You become an admin.`))) return;
        act(() => api('POST', G + '/' + g.id + '/transfer', {nickname: n}), tr(`${n} 님이 소유자가 되었습니다.`, `${n} is now the owner.`));
      });
      const typed = box.querySelector('[data-wsg-confirm-name]'), del = box.querySelector('[data-wsg-delete]');
      if (typed) typed.oninput = () => { del.disabled = typed.value.trim() !== g.name; };
      if (del) del.onclick = async () => {
        try { await api('DELETE', G + '/' + g.id + '?confirm=' + encodeURIComponent(typed.value.trim())); await getGroups(true); refresh(true).catch(() => {}); closeGroup(tr('그룹을 삭제했습니다.', 'Group deleted.')); }
        catch (e) { st.textContent = message(e); }
      };
      box.querySelector('[data-wsg-leave]')?.addEventListener('click', async () => {
        if (!window.confirm(tr(`"${g.name}" 그룹에서 나갈까요? 다시 들어오려면 초대 코드가 필요합니다.`, `Leave "${g.name}"? You will need a code to come back.`))) return;
        try { await api('POST', G + '/' + g.id + '/leave', {}); await getGroups(true); refresh(true).catch(() => {}); closeGroup(tr('그룹에서 나왔습니다.', 'You left the group.')); }
        catch (e) { st.textContent = message(e); }
      });
    }

    /* ── a new invite code: expiry and uses, then the code and its link, shown once ── */
    function inviteDialog(g) {
      const dialog = document.createElement('dialog');
      dialog.className = 'wsg-dialog';
      dialog.innerHTML = `<form><h2>${tr('초대 코드 만들기', 'New invite code')}</h2><p class="wsg-note">${esc(g.name)}</p>
        <label>${tr('유효 기간', 'Expires')}<select name="expires"><option value="1d">${tr('1일', '1 day')}</option><option value="7d" selected>${tr('7일', '7 days')}</option><option value="never">${tr('만료 없음', 'Never')}</option></select></label>
        <label>${tr('사용 횟수', 'Uses')}<select name="max_uses"><option value="1">${tr('1회', 'Once')}</option><option value="10">${tr('10회', '10 times')}</option><option value="50" selected>${tr('50회', '50 times')}</option><option value="">${tr('제한 없음', 'Unlimited')}</option></select></label>
        ${g.approval ? `<p class="wsg-note">🔒 ${tr('참여 승인이 켜져 있어 코드를 입력하면 참여 요청이 됩니다.', 'Approval is on: the code sends a request.')}</p>` : ''}
        <p role="alert"></p><div class="wsg-acts"><button type="submit" class="ws-btn pri">${tr('만들기', 'Create')}</button><button type="button" class="ws-btn ghost" data-close>${tr('닫기', 'Close')}</button></div></form>`;
      const form = dialog.querySelector('form');
      dialog.onclose = () => dialog.remove();
      dialog.querySelector('[data-close]').onclick = () => dialog.close();
      form.onsubmit = async event => {
        event.preventDefault();
        const f = form.elements, button = form.querySelector('[type=submit]');
        button.disabled = true;
        try {
          const r = await api('POST', G + '/' + g.id + '/invites', {expires: f.expires.value, max_uses: f.max_uses.value ? Number(f.max_uses.value) : null});
          dialog.close();
          await getGroups(true);
          paintDetail(g.id);
          showCode(g, r);
        } catch (e) { form.querySelector('[role=alert]').textContent = message(e); button.disabled = false; }
      };
      root.append(dialog);
      dialog.showModal?.();
    }
    function showCode(g, {code, invite}) {
      const link = new URL('#/workshop/storage?code=' + encodeURIComponent(code), location.href).href;
      const dialog = document.createElement('dialog');
      dialog.className = 'wsg-dialog';
      dialog.innerHTML = `<form method="dialog"><h2>${tr('초대 코드', 'Invite code')}</h2><p class="wsg-note">${esc(g.name)} · ${invite.expires_at ? tr(`${date(invite.expires_at)}까지`, `until ${date(invite.expires_at)}`) : tr('만료 없음', 'No expiry')} · ${invite.max_uses == null ? tr('사용 제한 없음', 'Unlimited uses') : tr(`${invite.max_uses}회`, `${invite.max_uses} uses`)}</p>
        <output class="wsg-code" data-wsg-code>${esc(code)}</output>
        <label>${tr('초대 링크', 'Invite link')}<input readonly data-wsg-link value="${esc(link)}"></label>
        <p class="wsg-note">${tr('코드만 알려 줘도 보관함의 "코드로 참여"에서 들어올 수 있습니다. 이 창을 닫으면 코드를 다시 볼 수 없습니다.', 'The code alone is enough: members enter it under "Join with a code". It will not be shown again after you close this.')}</p>
        <p role="status"></p><div class="wsg-acts"><button type="button" class="ws-btn pri" data-copy="code">${tr('코드 복사', 'Copy code')}</button><button type="button" class="ws-btn" data-copy="link">${tr('링크 복사', 'Copy link')}</button><button class="ws-btn ghost">${tr('닫기', 'Close')}</button></div></form>`;
      dialog.onclose = () => dialog.remove();
      dialog.querySelectorAll('[data-copy]').forEach(b => b.onclick = async () => {
        const value = b.dataset.copy === 'code' ? code : link, out = dialog.querySelector('[role=status]');
        try { await navigator.clipboard.writeText(value); out.textContent = tr('복사했습니다.', 'Copied.'); }
        catch { const field = dialog.querySelector('[data-wsg-link]'); field.value = value; field.focus(); field.select(); out.textContent = tr('선택된 내용을 복사해 주세요.', 'Copy the selected text.'); }
      });
      root.append(dialog);
      dialog.showModal?.();
    }

    const start = route(location.hash);
    if (start.group && !start.code) paintDetail(start.group); else paintList();
    root.querySelector('[data-ws-invites]')?.addEventListener('click', () => {
      if (route(location.hash).group) closeGroup();
      host.scrollIntoView?.({block: 'start'});
      box.querySelector('[data-wsg-join] input')?.focus({preventScroll: true});
    });

    root.querySelectorAll('[data-class-share]').forEach(button => {
      button.onclick = async () => {
        button.disabled = true;
        try {
          const choices = await getGroups();
          if (!here() || !button.isConnected) return;
          if (!choices.length) {
            status.replaceChildren(document.createTextNode(tr('먼저 학급이나 동아리에 가입하거나 그룹을 만드세요. ', 'Create or join a class or club first. ')));
            if (route(location.hash).group) closeGroup();
            box.scrollIntoView?.({block: 'nearest'});
            return;
          }
          const id = button.dataset.classShare;
          const file = files.find(f => f.id === id);
          const folder = !file && folders.includes(id) ? id : '';
          if (!file && !folder) return;
          const name = file?.name || folder.split('/').pop() || folderPlaceholder;
          const dialog = document.createElement('dialog');
          dialog.className = 'ws-share-dialog';
          dialog.innerHTML = `<form><h2>${tr('학급·동아리에 공유', 'Share with a class or club')}</h2>
            <label>${tr('그룹', 'Group')}<select name="group">${choices.map(c => `<option value="${+c.id}">${esc(c.name)}</option>`).join('')}</select></label>
            <label>${tr('종류', 'Type')}<select name="kind"><option value="resource">${label('resource')}</option><option value="assignment">${label('assignment')}</option></select></label>
            <label>${tr('제목', 'Title')}<input name="title" required maxlength="100" value="${esc(name.slice(0, 100))}"></label>
            <label>${tr('안내', 'Instructions')}<textarea name="instructions" rows="3" maxlength="2000"></textarea></label>
            <label data-due hidden>${tr('마감 시간', 'Due date')}<input type="datetime-local" name="due"></label>
            <p>${folder ? tr('현재 폴더에 있는 파일이 공유됩니다. 공유한 파일을 수정하면 새 내용이 보입니다.', 'This shares the files currently in the folder. Members see later revisions to those files.') : tr('그룹 구성원이 파일을 내려받을 수 있습니다.', 'Group members can download the file.')}</p>
            <p role="alert"></p><div class="ws-acts"><button class="ws-btn pri" type="submit">${tr('공유', 'Share')}</button><button class="ws-btn" type="button" data-close>${tr('닫기', 'Close')}</button></div></form>`;
          const form = dialog.querySelector('form'), fields = form.elements;
          const update = () => {
            const option = fields.kind.options[1];
            option.disabled = choices.find(c => c.id === Number(fields.group.value))?.role !== 'owner';
            if (option.disabled) fields.kind.value = 'resource';
            dialog.querySelector('[data-due]').hidden = fields.kind.value !== 'assignment';
          };
          fields.group.onchange = fields.kind.onchange = update;
          update();
          dialog.onclose = () => dialog.remove();
          dialog.querySelector('[data-close]').onclick = () => dialog.close();
          form.onsubmit = async e => {
            e.preventDefault();
            const submit = form.querySelector('[type=submit]');
            submit.disabled = true;
            try {
              const kind = fields.kind.value;
              await api('POST', path, {class_id: Number(fields.group.value), kind, title: fields.title.value, instructions: fields.instructions.value,
                ...(kind === 'assignment' && fields.due.value ? {due_at: Math.floor(new Date(fields.due.value).getTime() / 1000)} : {}),
                ...(file ? {file_id: file.id} : {folder})});
              dialog.close();
              await refresh(true);
              status.textContent = tr('공유했습니다.', 'Shared.');
            } catch (error) {
              if (dialog.open) form.querySelector('[role=alert]').textContent = message(error);
              else status.textContent = message(error);
            } finally { submit.disabled = false; }
          };
          root.append(dialog);
          dialog.showModal();
        } catch (e) { status.textContent = message(e); }
        finally { button.disabled = false; }
      };
    });
  };
  Object.assign(window.HL_WS_CLASS_STORAGE, {route, formatCode, codeOk});
})();
