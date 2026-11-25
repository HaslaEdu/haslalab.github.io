/* Class and club materials are private to signed-in members of the selected group. */
(() => {
  const path = '/workshop/storage/shared';
  window.HL_WS_CLASS_STORAGE = function mount({host, root, api, fetchFile, text, esc, error, files, folders, here}) {
    const tr = text;
    const folderPlaceholder = tr('폴더 선택', 'Choose a folder');
    const sharedLabel = tr('학급·동아리 공유 보관함', 'Shared storage for classes and clubs');
    const empty = tr('아직 공유한 자료나 과제가 없습니다.', 'No materials or assignments have been shared yet.');
    const message = e => ({
      bad_code: tr('초대 코드 6자리를 확인해 주세요.', 'Enter the six-character invite code.'),
      class_not_found: tr('이 코드로 참여할 수 있는 그룹이 없습니다.', 'No active group matches this code.'),
      class_full: tr('그룹의 정원이 찼습니다.', 'This group is full.'),
      class_limit: tr('만들 수 있는 그룹 수에 도달했습니다.', 'You have reached the group limit.'),
      own_class: tr('이미 이 그룹을 운영 중입니다.', 'You already manage this group.'),
      bad_name: tr('그룹 이름을 입력해 주세요.', 'Enter a group name.'),
      bad_share: tr('제목과 파일, 마감 시간을 확인해 주세요.', 'Check the title, file and due date.'),
      forbidden: tr('이 그룹에 공유할 권한이 없습니다.', 'You cannot share to this group.'),
      not_found: tr('자료를 찾을 수 없습니다.', 'The material could not be found.'),
      share_too_many_files: tr('한 번에 파일 200개까지 공유할 수 있습니다.', 'Share up to 200 files at a time.'),
      bad_worksheet: tr('과제용 JSON은 문제 제작에서 저장한 문제나 시험지를 사용해 주세요.', 'Use a problem or paper from the problem maker for JSON assignments.'),
      share_limit: tr('공유한 자료가 너무 많습니다. 기존 공유를 정리해 주세요.', 'Remove an old share before adding another.')
    }[e?.code] || error(e?.code));
    let groups;
    const memberships = () => [...groups.teaching.map(c => ({...c, owner: true})), ...groups.joined];
    const getGroups = fresh => !fresh && groups ? Promise.resolve(groups) : api('GET','/learn/classes',undefined,{forcePrimary:fresh}).then(data => (groups = data));
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
        dialog.append(title,list,close); root.append(dialog);
        window.renderMathInElement?.(list,{delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}],throwOnError:false});
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
      return api('GET', path,undefined,{forcePrimary:fresh}).then(({shares}) => {
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
    host.innerHTML = `<h2>${sharedLabel}</h2><details class="ws-group-panel" data-group-panel><summary>${tr('그룹 만들기 · 멤버 초대 · 참여','Create a group, invite members or join')}</summary><div data-group-tools></div></details><p class="ws-note" data-shared-status role="status"></p><div data-shared-list></div>`;
    const status = host.querySelector('[data-shared-status]');
    refresh().catch(e => { status.textContent = message(e); });
    mountGroups();
    function mountGroups() {
      const panel = host.querySelector('[data-group-panel]'), area = panel.querySelector('[data-group-tools]');
      const params = new URLSearchParams(location.hash.split('?')[1] || '');
      let invite = (params.get('invite') || '').trim().toUpperCase();
      if (!/^[A-Z0-9]{6}$/.test(invite)) invite = '';
      let selected;
      function render() {
        if (!here() || !area.isConnected) return;
        const owned = groups.teaching, joined = groups.joined;
        const current = owned.find(group => group.id === selected) || owned[0];
        const link = current ? new URL('#/workshop/storage?invite=' + encodeURIComponent(current.code),location.href).href : '';
        area.innerHTML = `<div class="ws-group-forms">
          <form data-group-action="/learn/classes"><label>${tr('학급 또는 동아리 이름','Class or club name')}<input name="name" maxlength="60" required></label><button type="submit" class="ws-btn">${tr('그룹 만들기','Create group')}</button></form>
          <form data-group-action="/learn/classes/join"><label>${tr('받은 초대 코드','Invite code')}<input name="code" maxlength="6" minlength="6" pattern="[A-Za-z0-9]{6}" autocapitalize="characters" autocomplete="off" required value="${esc(invite)}"></label><button type="submit" class="ws-btn">${tr('그룹 참여','Join group')}</button></form>
          </div>
          ${current ? `<div class="ws-group-invite"><label>${tr('운영하는 그룹','Groups you manage')}<select data-group-select>${owned.map(group => `<option value="${+group.id}"${group.id === current.id ? ' selected' : ''}>${esc(group.name)} · ${Number(group.n) || 0}${tr('명',' members')}</option>`).join('')}</select></label>
            <label>${tr('멤버 초대 링크','Member invitation link')}<input data-group-link readonly value="${esc(link)}"></label>
            <button type="button" class="ws-btn pri" data-copy-invite>${tr('초대 링크 복사','Copy invitation link')}</button>
            <p class="ws-note">${tr('멤버에게 링크 또는 초대 코드','Send members the link or invite code')} <strong>${esc(current.code)}</strong>${tr('를 전달하세요.','.')}</p></div>` : ''}
          ${joined.length ? `<p class="ws-note">${tr('참여 중인 그룹','Groups you joined')} · ${joined.map(group => esc(group.name)).join(' · ')}</p>` : ''}
          <p class="ws-note" role="status"></p>`;
        const feedback = area.querySelector('[role=status]');
        area.querySelector('[data-group-select]')?.addEventListener('change', event => {
          selected = Number(event.target.value);
          render();
          area.querySelector('[data-group-select]')?.focus({preventScroll:true});
        });
        area.querySelector('[data-copy-invite]')?.addEventListener('click',async () => {
          try {
            await navigator.clipboard.writeText(link);
            feedback.textContent = tr('초대 링크를 복사했습니다.','Invitation link copied.');
          } catch {
            const field = area.querySelector('[data-group-link]');
            field.focus();
            field.select();
            feedback.textContent = tr('선택된 초대 링크를 복사해 주세요.','Copy the selected invitation link.');
          }
        });
        area.querySelectorAll('form').forEach(form => form.onsubmit = async event => {
          event.preventDefault();
          const button = form.querySelector('button'), data = new FormData(form);
          button.disabled = true;
          const joining = data.has('code');
          try {
            const group = await api('POST',form.dataset.groupAction,Object.fromEntries(data));
            if (!here() || !area.isConnected) return;
            if (!joining) selected = group.id;
            else if (invite) {
              invite = '';
              params.delete('invite');
              history.replaceState(history.state,'','#/workshop/storage' + (params.size ? '?' + params : ''));
            }
            await getGroups(true);
            if (!here() || !area.isConnected) return;
            render();
            area.querySelector('[role=status]').textContent = joining ? tr('그룹에 참여했습니다.','You joined the group.') : tr('그룹을 만들었습니다. 초대 링크를 복사해 멤버에게 보내세요.','Group created. Copy the link to invite members.');
            if (joining) await refresh(true);
          } catch (e) { (area.querySelector('[role=status]') || feedback).textContent = message(e); }
          finally { button.disabled = false; }
        });
      }
      panel.ontoggle = async () => {
        if (!panel.open || area.querySelector('form')) return;
        area.textContent = tr('그룹을 불러오는 중…','Loading groups…');
        try { await getGroups(); render(); }
        catch (e) { area.textContent = message(e); }
      };
      const open = () => { panel.open = true; panel.scrollIntoView({block:'nearest'}); };
      root.querySelector('[data-ws-invites]')?.addEventListener('click',open);
      if (invite) open();
    }
    root.querySelectorAll('[data-class-share]').forEach(button => {
      button.onclick = async () => {
        button.disabled = true;
        try {
          await getGroups();
          if (!here() || !button.isConnected) return;
          const choices = memberships();
          if (!choices.length) {
            status.replaceChildren(document.createTextNode(tr('먼저 학급이나 동아리에 가입하거나 그룹을 만드세요. ', 'Create or join a class or club first. ')));
            const panel = host.querySelector('[data-group-panel]');
            panel.open = true;
            panel.scrollIntoView({block: 'nearest'});
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
            option.disabled = !choices.find(c => c.id === Number(fields.group.value))?.owner;
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
})();
