/* Hasla AI review (admins): the nightly self-test cases from the community Worker's /api/admin/ai-eval */
(() => {
  'use strict';
  const PROD = 'https://haslalab-community-edge.haslalab.workers.dev';
  const api = () => { try { const o = localStorage.getItem('hlCmApi') || ''; return (/^(?:https?:\/\/(?:localhost|127\.0\.0\.1)(?::\d+)?|https:\/\/[a-z0-9-]+\.haslalab\.workers\.dev)\/?$/.test(o) ? o : PROD).replace(/\/+$/, ''); } catch { return PROD; } };
  const token = () => { try { return localStorage.getItem('hlCmTok') || ''; } catch { return ''; } };
  const $ = id => document.getElementById(id);
  const el = (tag, props = {}, ...kids) => { const e = Object.assign(document.createElement(tag), props); e.append(...kids.filter(k => k != null)); return e; };
  const ROUTE = {cache: '저장된 답', site: '사이트 찾기', web: '웹 검색', chat: '잡담', explain: '개념 설명', solve: '문제 풀이', off: '주제 밖', tools: '도구 사용',
    'site→tools': '사이트→도구', 'web→tools': '웹→도구', fast: '작은 모델', 'fast→big': '작은→큰 모델', big: '큰 모델', blocked: '차단'}, STYLE = {default: '기본 말투', community: '커뮤 말투'};
  const KIND = {bank: '문제풀이', site: '문제위치', member: '회원 대화'}, VERDICT = {correct: '맞음', wrong: '틀림', blocked: '차단됨', ungraded: '채점 안 됨', good: '👍 회원 좋아요', bad: '👎 회원 별로'};
  let before = 0;

  async function call(path, init = {}) {
    if (!token()) throw new Error('로그인이 필요합니다. 하슬라랩에서 관리자 계정으로 로그인한 뒤 이 페이지를 다시 여세요.');
    const r = await fetch(api() + '/api/admin/ai-eval' + path, {...init, headers: {Authorization: 'Bearer ' + token(), ...(init.body ? {'Content-Type': 'application/json'} : {})}});
    if (!r.ok) {
      const e = (await r.json().catch(() => ({}))).error || r.status;
      throw new Error({forbidden: '관리자만 쓸 수 있습니다.', login_required: '로그인이 필요합니다.', busy: '이미 실행 중인 시험이 있습니다. 잠시 후 다시 시도하세요.'}[e] || `오류: ${e}`);
    }
    return r;
  }
  const show = e => { $('msg').hidden = !e; $('msg').textContent = e ? e.message || String(e) : ''; };

  function caseView(c) {
    const note = el('textarea', {placeholder: '고친 답 (비워 두면 AI의 답 그대로 승인)', value: c.corrected || ''});
    const act = action => async () => {
      try { const r = await call('/' + c.id, {method: 'POST', body: JSON.stringify({action, corrected: note.value})}); box.replaceWith(caseView(await r.json())); show(null); }
      catch (e) { show(e); }
    };
    const score = c.score == null ? '–' : c.kind === 'site' ? (c.score ? '통과' : '실패') : `${Math.round(c.score * 10)}/10`;
    const tools = (() => { try { return JSON.parse(c.tools || '[]').join(', '); } catch { return ''; } })();
    const box = el('section', {className: 'case'},
      el('h2', {}, `#${c.id}`, el('span', {className: 'tag'}, KIND[c.kind] || c.kind), c.verdict ? el('span', {className: 'tag ' + c.verdict}, VERDICT[c.verdict] || c.verdict) : null,
        c.route ? el('span', {className: 'tag'}, ROUTE[c.route] || c.route) : null, c.style === 'community' ? el('span', {className: 'tag'}, STYLE.community) : null,
        el('span', {}, `점수 ${score}`), el('span', {className: 'muted'}, `${c.day} · ${c.status}${tools ? ' · 도구: ' + tools : ''}`)),
      c.context ? el('div', {}, el('b', {}, '앞 대화'), el('pre', {textContent: (() => { try { return JSON.parse(c.context).map(m => (m.role === 'user' ? '회원: ' : 'AI: ') + m.content).join('\n\n'); } catch { return ''; } })()})) : null,
      el('div', {className: 'cols'},
        el('div', {}, el('b', {}, '질문'), el('pre', {textContent: c.question || ''})),
        el('div', {}, el('b', {}, 'AI의 답'), el('pre', {textContent: c.answer || ''})),
        c.kind === 'member' ? null : el('div', {}, el('b', {}, '공식 풀이 / 정답'), el('pre', {textContent: c.reference || ''}))),
      c.kind === 'member' ? null : el('div', {}, el('b', {}, '채점 이유'), el('pre', {textContent: c.reason || ''})),
      c.status === 'failed' ? null : note,
      c.status === 'failed' ? null : el('div', {className: 'bar'},
        el('button', {type: 'button', className: 'primary', textContent: '승인', onclick: act('approve')}),
        el('button', {type: 'button', textContent: '거절', onclick: act('reject')}),
        c.status !== 'graded' ? el('button', {type: 'button', textContent: '검토 대기로 되돌리기', onclick: act('reset')}) : null));
    return box;
  }

  async function load(more = false) {
    try {
      if (!more) { before = 0; $('list').textContent = ''; }
      const q = new URLSearchParams({status: $('status').value, limit: '20'});
      if ($('verdict').value) q.set('verdict', $('verdict').value);
      if ($('kind').value) q.set('kind', $('kind').value);
      if (before) q.set('before', before);
      const d = await (await call('?' + q)).json();
      $('config').textContent = `매일 ${d.config.daily}건, 한국시간 ${d.config.hour}시부터 · 검토 대기 ${d.counts.graded || 0} · 승인 ${d.counts.approved || 0} · 거절 ${d.counts.rejected || 0} · 실패 ${d.counts.failed || 0}`;
      if (!more && d.usage) {
        const total = d.usage.routes.reduce((n, r) => n + r.n, 0) || 1;
        $('usage').replaceChildren(...d.usage.routes.map(r => el('tr', {}, ...[ROUTE[r.route] || r.route, r.n, Math.round(r.n / total * 100) + '%',
          r.ms == null ? '–' : (r.ms / 1000).toFixed(1) + '초', Math.round(r.tokens_in || 0), Math.round(r.tokens_out || 0)].map(v => el('td', {}, String(v))))));
        $('usageNote').textContent = `최근 ${d.usage.days}일 회원 질문 · 저장된 답 ${d.usage.memory}개`;
      }
      if (!more) $('days').replaceChildren(...d.days.map(r => el('tr', {}, ...[r.day, (KIND[r.kind] || r.kind) + (r.route ? ` · ${ROUTE[r.route] || r.route}` : ''), r.n, r.avg == null ? '–' : (r.kind === 'site' ? Math.round(r.avg * 100) + '%' : (r.avg * 10).toFixed(1) + '/10'), r.correct, r.failed, r.approved].map(v => el('td', {}, String(v ?? 0))))));
      for (const c of d.items) $('list').append(caseView(c));
      if (!d.items.length && !more) $('list').append(el('p', {className: 'muted', textContent: '해당하는 시험이 없습니다.'}));
      before = d.items.length ? d.items[d.items.length - 1].id : before;
      $('more').hidden = d.items.length < 20;
      show(null);
    } catch (e) { show(e); }
  }
  async function run(kind, btn) {
    btn.disabled = true; btn.textContent = '실행 중… (1~3분)';
    try { const r = await (await call('/run', {method: 'POST', body: JSON.stringify({kind})})).json(); $('list').prepend(caseView(r)); show(null); }
    catch (e) { show(e); }
    finally { btn.disabled = false; btn.textContent = kind === 'site' ? '문제위치 1건 지금 실행' : '문제풀이 1건 지금 실행'; }
  }
  /* the automatic training runs (ai-train.js / train-ai.yml), with promote and rollback */
  const RUN_STATUS = {starting: '시작', downloading: '데이터 받는 중', training: '학습 중', uploaded: '업로드됨', trained: '학습 끝', testing: '비교 시험 중',
    tested: '시험 끝', promoted: '✓ 적용됨', rejected: '적용 안 함 (점수 부족)', rolled_back: '되돌림', failed: '✗ 실패'};
  async function loadTrain() {
    try {
      const r = await fetch(api() + '/api/admin/ai-train/status', {headers: {Authorization: 'Bearer ' + token()}});
      if (!r.ok) return;
      const d = await r.json();
      const pct = v => (v == null ? '–' : (v * 10).toFixed(1));
      $('train').replaceChildren(...d.runs.map(x => {
        const act = x.promoted ? el('button', {type: 'button', textContent: '되돌리기', onclick: () => trainAct('rollback', x.run)})
          : x.status === 'rejected' && x.candidate ? el('button', {type: 'button', textContent: '그래도 적용', onclick: () => trainAct('promote', x.run)}) : null;
        return el('tr', {title: x.note || ''}, ...[x.run, x.role === 'solver' ? '풀이 (QwQ)' : '총괄 (Gemma 4)', RUN_STATUS[x.status] || x.status,
          x.examples ?? '–', `${pct(x.base_score)} → ${pct(x.cand_score)}${x.trials ? ` (${x.trials}문제)` : ''}`, x.cost == null ? '–' : '$' + x.cost].map(v => el('td', {}, String(v))), el('td', {}, act));
      }));
      if (!d.runs.length) $('train').append(el('tr', {}, el('td', {colSpan: 7, className: 'muted', textContent: '아직 학습한 적이 없습니다.'})));
      const c = d.counts;
      $('trainSettings').textContent = `학습용 승인 데이터: 풀이 ${c.solver.approved}개(새로 ${c.solver.new_since_last}), 총괄 ${c.chat.approved}개(새로 ${c.chat.new_since_last}) · 적용 중: ` +
        (d.settings.length ? d.settings.map(s => `${s.k}=${s.v}`).join(', ') : '기본 모델(학습 전)');
    } catch {}
  }
  async function trainAct(action, run) {
    if (!confirm(action === 'rollback' ? `${run}을(를) 되돌릴까요? 이전 설정으로 돌아갑니다.` : `${run}을(를) 적용할까요?`)) return;
    try {
      const r = await fetch(api() + '/api/admin/ai-train/' + action, {method: 'POST', headers: {Authorization: 'Bearer ' + token(), 'Content-Type': 'application/json'}, body: JSON.stringify({run})});
      if (!r.ok) throw new Error('오류: ' + r.status);
      show(null); loadTrain();
    } catch (e) { show(e); }
  }
  async function exportData() {
    try {
      const st = $('exportStyle').value;
      const blob = await (await call('/export' + (st ? '?style=' + st : ''))).blob();
      const a = el('a', {href: URL.createObjectURL(blob), download: `haslalab-ai-train${st ? '-' + st : ''}.jsonl`});
      document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 5000);
    } catch (e) { show(e); }
  }
  $('reload').onclick = () => load();
  $('status').onchange = $('verdict').onchange = $('kind').onchange = () => load();
  $('more').onclick = () => load(true);
  $('runBank').onclick = e => run('bank', e.currentTarget);
  $('runSite').onclick = e => run('site', e.currentTarget);
  $('export').onclick = exportData;
  load();
  loadTrain();
})();
