/* HaslaLab assistant: a chat button on every page. It talks to the community Worker's /api/ai/chat (open-weight
   models on Workers AI, members only) and shows the answer as it is written (server-sent events); the conversation
   lives in this tab only (sessionStorage). Without signing in a visitor may ask twice a day. Whether a member's chats
   are kept to train the assistant is the AI-chat box of their consent (sign-up, profile, or the box under the chat;
   withdrawing deletes what was kept). */
(() => {
  'use strict';
  const PROD = 'https://haslalab-community-edge.haslalab.workers.dev', MAX_TURNS = 20, KEY = 'hlAiChat', STYLE_KEY = 'hlAiStyle';
  const BASE = new URL('.', (document.currentScript && document.currentScript.src) || location.href).href;
  const api = () => { try { const o = localStorage.getItem('hlCmApi') || ''; return (/^(?:https?:\/\/(?:localhost|127\.0\.0\.1)(?::\d+)?|https:\/\/[a-z0-9-]+\.haslalab\.workers\.dev)\/?$/.test(o) ? o : PROD).replace(/\/+$/, ''); } catch { return PROD; } };
  const token = () => { try { return localStorage.getItem('hlCmTok') || ''; } catch { return ''; } };
  // the page's language: the <html lang> the site sets when the language is switched, else the address (?lang=en)
  const ko = () => { const l = document.documentElement.lang; return l === 'en' ? false : l === 'ko' ? true : !/[?&]lang=en\b/.test(location.search); };
  const T = {
    ko: {open: 'AI에게 묻기', title: '하슬라 AI', hint: '문제 위치, 풀이 설명, 커뮤니티 글, 웹 정보를 물어보세요.', ph: '질문을 입력하세요 (Enter 전송, Shift+Enter 줄바꿈)',
      send: '보내기', clear: '대화 지우기', close: '닫기', style: {default: '말투: 기본', community: '말투: 커뮤'}, styleHint: '답변 말투 바꾸기', login: '로그인한 회원만 쓸 수 있습니다.', loginGo: '로그인하기', wait: '생각하는 중…', sources: '관련 링크',
      err: {guest_limit: '오늘 무료 질문 2번을 다 썼어요. 로그인하면 계속 쓸 수 있습니다.', rate_limited: '질문이 너무 많습니다. 잠시 후 다시 시도해 주세요.', login_required: '로그인이 필요합니다.', ai_unavailable: 'AI를 지금 쓸 수 없습니다.', _: '답을 받지 못했습니다. 잠시 후 다시 시도해 주세요.'},
      note: 'AI 답변은 틀릴 수 있습니다. 중요한 내용은 원문과 해설로 확인하세요.',
      train: '내 대화를 하슬라 AI 학습에 활용 동의 (끄면 남은 대화도 삭제)', edit: '수정', del: '삭제', resend: '다시 보내기', cancel: '취소', good: '도움이 됐어요', bad: '별로예요',
      ask: '하슬라 AI가 더 똑똑해지도록 대화를 학습에 활용해도 될까요? 관리자가 검토한 대화만 쓰고, 검토되지 않은 대화는 1년 뒤 지웁니다. 동의하지 않아도 AI는 그대로 쓸 수 있고, 아래 체크박스로 언제든 바꿀 수 있어요.',
      yes: '동의', later: '괜찮아요',
      guest: '로그인하지 않아도 하루 2번까지 물어볼 수 있어요. 로그인하면 계속 쓸 수 있습니다.', guestDone: '오늘 무료 질문 2번을 다 썼어요. 로그인하면 계속 쓸 수 있습니다.'},
    en: {open: 'Ask AI', title: 'Hasla AI', hint: 'Ask where a problem is, for an explanation, about posts, or for web information.', ph: 'Type a question (Enter to send, Shift+Enter for a new line)',
      send: 'Send', clear: 'Clear chat', close: 'Close', style: {default: 'Tone: default', community: 'Tone: casual'}, styleHint: 'Change the answer tone', login: 'Members only.', loginGo: 'Log in', wait: 'Thinking…', sources: 'Links',
      err: {guest_limit: 'You have used today\'s two free questions. Log in to keep going.', rate_limited: 'Too many questions. Please try again shortly.', login_required: 'Please log in.', ai_unavailable: 'The assistant is unavailable right now.', _: 'No answer came back. Please try again.'},
      note: 'AI answers can be wrong. Check important points against the papers and solutions.',
      train: 'Let Hasla AI learn from my chats (unticking deletes the kept chats)', edit: 'Edit', del: 'Delete', resend: 'Send again', cancel: 'Cancel', good: 'Helpful', bad: 'Not helpful',
      ask: 'May Hasla AI learn from your chats so it gets better? Only chats an admin reviews are used, and unreviewed ones are deleted after a year. You can use the AI either way and change this any time with the box below.',
      yes: 'Agree', later: 'No thanks',
      guest: 'You can ask twice a day without logging in. Log in to keep going.', guestDone: 'You have used today\'s two free questions. Log in to keep going.'},
  };
  const t = () => T[ko() ? 'ko' : 'en'];
  let history = [];
  try { history = JSON.parse(sessionStorage.getItem(KEY) || '[]').filter(m => m && typeof m.content === 'string').slice(-MAX_TURNS); } catch { history = []; }
  const save = () => { try { sessionStorage.setItem(KEY, JSON.stringify(history.slice(-MAX_TURNS))); } catch {} };
  let style = 'default', train = null;   // train: the account's AI-chat consent, read from the server (null: not known)
  try { if (localStorage.getItem(STYLE_KEY) === 'community') style = 'community'; } catch {}

  const css = `
.hlai-btn{position:fixed;right:18px;bottom:18px;z-index:60;border:0;border-radius:999px;padding:11px 16px;background:var(--rail,#2E3945);color:#fff;
  font:600 14px var(--sans,sans-serif);box-shadow:0 6px 20px rgba(0,0,0,.18);cursor:pointer}
.hlai-btn:hover{background:var(--ink,#16212E)}
.hlai{position:fixed;right:18px;bottom:18px;z-index:61;width:min(420px,calc(100vw - 24px));height:min(620px,calc(100vh - 36px));display:none;flex-direction:column;
  background:var(--paper,#FBFCFD);color:var(--ink,#16212E);border:1px solid var(--grid-bold,#B4CADC);border-radius:12px;box-shadow:0 12px 40px rgba(0,0,0,.22);overflow:hidden;font:14px/1.55 var(--sans,sans-serif)}
.hlai.on{display:flex}
.hlai *{box-sizing:border-box;margin:0}
.hlai-h{display:flex;align-items:center;gap:8px;padding:10px 12px;border-bottom:1px solid var(--grid-bold,#B4CADC)}
.hlai-h b{flex:1;font-size:15px}
.hlai-h button{border:0;background:none;color:var(--graphite,#5C6B7A);cursor:pointer;font:12px var(--sans,sans-serif);padding:4px 6px}
.hlai-log{flex:1;overflow:auto;padding:12px;display:flex;flex-direction:column;gap:10px}
.hlai-m{max-width:88%;padding:8px 11px;border-radius:10px;white-space:pre-wrap;word-break:break-word}
.hlai-m.u{align-self:flex-end;background:var(--rail,#2E3945);color:#fff}
.hlai-act{align-self:flex-end;display:flex;gap:4px;margin-top:-6px}
.hlai-act button{border:0;background:none;color:var(--graphite,#5C6B7A);font:11px var(--sans,sans-serif);cursor:pointer;padding:2px 4px;opacity:.75}
.hlai-act button:hover{opacity:1;text-decoration:underline}
.hlai-edit{align-self:stretch;display:flex;flex-direction:column;gap:6px}
.hlai-edit textarea{width:100%;min-height:64px;resize:vertical;border:1px solid var(--grid-bold,#B4CADC);border-radius:8px;padding:8px;font:14px var(--sans,sans-serif);background:transparent;color:inherit}
.hlai-edit div{display:flex;gap:6px;justify-content:flex-end}
.hlai-edit button{border:1px solid var(--grid-bold,#B4CADC);background:transparent;color:inherit;border-radius:999px;padding:3px 12px;font:12px var(--sans,sans-serif);cursor:pointer}
.hlai-edit button.y{background:var(--rail,#2E3945);color:#fff;border-color:var(--rail,#2E3945)}
.hlai-m.a{align-self:flex-start;background:rgba(46,57,69,.07)}
.hlai-m.e{align-self:flex-start;color:var(--laser,#E02424)}
.hlai-m a{color:inherit;text-decoration:underline}
.hlai-m .katex{font-size:1.05em}
.hlai-m .hlai-dm{display:block;overflow-x:auto;overflow-y:hidden;padding:2px 0;white-space:normal}
.hlai-m code{font:12.5px ui-monospace,SFMono-Regular,Menlo,monospace;background:rgba(127,127,127,.15);border-radius:4px;padding:0 3px}
.hlai-m pre{white-space:pre;overflow-x:auto;background:rgba(127,127,127,.12);border-radius:6px;padding:6px 8px;font:12.5px ui-monospace,SFMono-Regular,Menlo,monospace}
.hlai-src{margin-top:6px;font-size:12px;color:var(--graphite,#5C6B7A)}
.hlai-src a{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hlai-hint,.hlai-note{color:var(--graphite,#5C6B7A);font-size:12px}
.hlai-note{padding:0 12px 6px}
.hlai-note label{display:flex;gap:6px;align-items:center;margin-top:3px;cursor:pointer}
.hlai-note label[hidden]{display:none}
.hlai-ask{align-self:stretch;border:1px solid var(--grid-bold,#B4CADC);border-radius:10px;padding:9px 11px;font-size:13px}
.hlai-ask div{display:flex;gap:8px;margin-top:8px}
.hlai-ask button,.hlai-fb button{border:1px solid var(--grid-bold,#B4CADC);background:transparent;color:inherit;border-radius:999px;padding:3px 10px;font:12px var(--sans,sans-serif);cursor:pointer}
.hlai-ask button.y{background:var(--rail,#2E3945);color:#fff;border-color:var(--rail,#2E3945)}
.hlai-fb{display:flex;gap:6px;margin-top:6px;font-size:12px;color:var(--graphite,#5C6B7A);white-space:normal}
.hlai-fb button[aria-pressed=true]{background:var(--rail,#2E3945);color:#fff}
.hlai-f{display:flex;gap:8px;padding:10px 12px;border-top:1px solid var(--grid-bold,#B4CADC)}
.hlai-f textarea{flex:1;resize:none;height:44px;border:1px solid var(--grid-bold,#B4CADC);border-radius:8px;padding:8px;font:14px var(--sans,sans-serif);background:transparent;color:inherit}
.hlai-f button{border:0;border-radius:8px;padding:0 14px;background:var(--rail,#2E3945);color:#fff;font:600 13px var(--sans,sans-serif);cursor:pointer}
.hlai-f button:disabled{opacity:.5;cursor:default}
html[data-theme="dark"] .hlai{background:#151b22;color:#e6edf3;border-color:#2b3642}
html[data-theme="dark"] .hlai-m.a{background:rgba(255,255,255,.07)}
@media print{.hlai,.hlai-btn{display:none!important}}`;

  const esc = s => s.replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const linkify = s => esc(s).replace(/\bhttps?:\/\/[^\s<>"')\]]+/g, u => `<a href="${u}" target="_blank" rel="noopener">${u}</a>`);

  /* KaTeX (vendor/katex, the site's copy) is loaded the first time an answer has a formula; until then the source shows */
  let katexP = null;
  function loadKatex() {
    if (window.katex) return Promise.resolve(window.katex);
    if (!katexP) katexP = new Promise((resolve, reject) => {
      if (!document.querySelector('link[data-hlai-katex]')) {
        const css = document.createElement('link'); css.rel = 'stylesheet'; css.href = BASE + 'vendor/katex/katex.min.css'; css.dataset.hlaiKatex = '1'; document.head.append(css);
      }
      const js = document.createElement('script'); js.src = BASE + 'vendor/katex/katex.min.js';
      js.onload = () => window.katex ? resolve(window.katex) : reject(new Error('katex'));
      js.onerror = () => { katexP = null; reject(new Error('katex')); };
      document.head.append(js);
    });
    return katexP;
  }
  /* $$…$$ and \[…\] on their own line, $…$ and \(…\) in the text (a $ followed or preceded by a space is a dollar) */
  const MATH = /\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]|\\\(([\s\S]+?)\\\)|\$(?![\s$])((?:\\\$|[^$\n])+?)(?<![\s\\])\$/g;
  let pendingMath = false;
  function tex(src, display, raw) {
    if (window.katex) {
      try { const h = window.katex.renderToString(src.trim(), {displayMode: display, throwOnError: false, strict: 'ignore', trust: false, maxSize: 30, maxExpand: 1000}); return display ? `<span class="hlai-dm">${h}</span>` : h; }
      catch { return esc(raw); }
    }
    pendingMath = true;
    return esc(raw);
  }
  /* light Markdown: **bold**, `code`, ``` blocks, # headings as bold lines */
  const inline = s => linkify(s).replace(/\*\*([^*\n]+)\*\*/g, '<b>$1</b>').replace(/`([^`\n]+)`/g, '<code>$1</code>').replace(/^#{1,6}\s+(.+)$/gm, '<b>$1</b>');
  function rich(text) {
    let out = '';
    const parts = String(text).split(/```[a-zA-Z]*\n?([\s\S]*?)```/);
    parts.forEach((part, i) => {
      if (i % 2) { out += `<pre>${esc(part.replace(/\n$/, ''))}</pre>`; return; }
      let last = 0;
      for (const m of part.matchAll(MATH)) {
        const display = m[1] != null || m[2] != null;
        let before = part.slice(last, m.index);
        if (display) before = before.replace(/\n$/, '');
        out += inline(before) + tex(m[1] ?? m[2] ?? m[3] ?? m[4], display, m[0]);
        last = m.index + m[0].length;
        if (display && part[last] === '\n') last++;
      }
      out += inline(part.slice(last));
    });
    return out;
  }
  let box, log, input, sendBtn, busy = false;

  function bubble(role, text, sources, msg) {
    const d = document.createElement('div');
    d.className = 'hlai-m ' + role;
    d.innerHTML = role === 'a' ? rich(text) : linkify(text);
    if (msg && msg.id) d.appendChild(feedback(msg));
    if (sources && sources.length) {
      const s = document.createElement('div');
      s.className = 'hlai-src';
      s.innerHTML = `<div>${esc(t().sources)}</div>` + sources.map(x => `<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.title || x.url)}</a>`).join('');
      d.appendChild(s);
    }
    log.appendChild(d);
    log.scrollTop = log.scrollHeight;
    return d;
  }
  /* 👍/👎 on an answer that was kept for review */
  function feedback(msg) {
    const f = document.createElement('div');
    f.className = 'hlai-fb';
    for (const [good, label] of [[true, '👍 ' + t().good], [false, '👎 ' + t().bad]]) {
      const b = document.createElement('button');
      b.type = 'button'; b.textContent = label; b.setAttribute('aria-pressed', String(msg.fb === good));
      b.addEventListener('click', async () => {
        msg.fb = good; save();
        for (const x of f.querySelectorAll('button')) x.setAttribute('aria-pressed', String(x === b));
        try { await fetch(api() + '/api/ai/feedback', {method: 'POST', headers: {'Content-Type': 'application/json', Authorization: 'Bearer ' + token()}, body: JSON.stringify({id: msg.id, good})}); } catch {}
      });
      f.appendChild(b);
    }
    return f;
  }
  /* the AI-chat box of the member's consent: read when the chat opens, changed by the box under the chat */
  const authed = (method, path, body) => fetch(api() + path, {method, headers: {'Content-Type': 'application/json', Authorization: 'Bearer ' + token()}, ...(body ? {body: JSON.stringify(body)} : {})})
    .then(r => r.ok ? r.json() : Promise.reject(r.status));
  function showTrain() {
    const row = box.querySelector('.hlai-train'), cb = box.querySelector('[data-a=train]');
    row.hidden = !token() || train === null; cb.checked = train === true;
  }
  async function readTrain() {
    if (!token()) { train = null; return showTrain(); }
    try { const st = await authed('GET', '/api/me/consent'); train = st.consent_required ? null : st.ai_train_ok === true; } catch { train = null; }
    showTrain();
    if (train === false) askOnce();
  }
  /* asked once per browser of a member who has not agreed; declining changes nothing (the AI stays open to them) */
  function askOnce() {
    try { if (localStorage.getItem('hlAiAsked')) return; } catch { return; }
    if (box.querySelector('.hlai-ask')) return;
    const d = document.createElement('div'), row = document.createElement('div');
    d.className = 'hlai-ask'; d.textContent = t().ask;
    for (const [v, label, cls] of [[true, t().yes, 'y'], [false, t().later, '']]) {
      const b = document.createElement('button'); b.type = 'button'; b.textContent = label; b.className = cls;
      b.addEventListener('click', () => { try { localStorage.setItem('hlAiAsked', '1'); } catch {} d.remove(); if (v) setTrain(true); });
      row.appendChild(b);
    }
    d.appendChild(row);
    log.appendChild(d);
    log.scrollTop = log.scrollHeight;
  }
  async function setTrain(v) {
    try { const r = await authed('POST', '/api/me/consent/ai-train', {on: v}); train = r.ai_train_ok === true; } catch { /* left as it was */ }
    showTrain();
  }
  function loginLink() {
    const a = document.createElement('a');
    a.href = '#/login'; a.textContent = t().loginGo;
    a.addEventListener('click', () => { try { sessionStorage.setItem('hlCmBack', location.hash); } catch {} toggle(false); });
    return a;
  }
  function paint() {
    log.innerHTML = '';
    if (!history.length) { const h = document.createElement('div'); h.className = 'hlai-hint'; h.textContent = t().hint; log.appendChild(h); }
    if (!token()) {
      const d = document.createElement('div'); d.className = 'hlai-hint'; d.textContent = t().guest + ' ';
      d.appendChild(loginLink());
      log.appendChild(d);
    }
    pendingMath = false;
    history.forEach((m, i) => { bubble(m.role === 'user' ? 'u' : 'a', m.content, m.sources, m); if (m.role === 'user') log.appendChild(actions(i)); });
    if (pendingMath) loadKatex().then(() => { if (box.classList.contains('on')) paint(); }).catch(() => {});
  }
  /* the answer arrives as server-sent events: meta, delta (text), done (the whole answer, links, id) or error */
  async function readEvents(res, on) {
    const reader = res.body.getReader(), dec = new TextDecoder();
    let buf = '';
    for (;;) {
      const {value, done} = await reader.read();
      if (done) break;
      buf += dec.decode(value, {stream: true});
      let i;
      while ((i = buf.indexOf('\n\n')) >= 0) {
        const block = buf.slice(0, i); buf = buf.slice(i + 2);
        const ev = (/^event: (\w+)/m.exec(block) || [])[1], data = (/^data: (.*)$/m.exec(block) || [])[1];
        if (ev && data) { try { on(ev, JSON.parse(data)); } catch {} }
      }
    }
  }
  /* edit or delete one of the member's own messages, as other chat apps do. Deleting takes the message and the answer
     to it; editing drops everything from that message on and asks again. What the member allowed to be kept for
     training goes with it on the server too. */
  function dropFrom(i, n) {
    const gone = history.splice(i, n);
    const ids = gone.map(m => m.id).filter(Boolean);
    if (ids.length && token()) fetch(api() + '/api/ai/feedback', {method: 'POST', headers: {'Content-Type': 'application/json', Authorization: 'Bearer ' + token()}, body: JSON.stringify({remove: ids})}).catch(() => {});
    save();
  }
  function actions(i) {
    const row = document.createElement('div');
    row.className = 'hlai-act';
    const mk = (label, fn) => { const b = document.createElement('button'); b.type = 'button'; b.textContent = label; b.addEventListener('click', () => { if (!busy) fn(); }); row.appendChild(b); };
    mk(t().edit, () => editAt(i, row));
    mk(t().del, () => { dropFrom(i, history[i + 1] && history[i + 1].role === 'assistant' ? 2 : 1); paint(); });
    return row;
  }
  function editAt(i, row) {
    const bubbleEl = row.previousElementSibling, box2 = document.createElement('div'), ta = document.createElement('textarea'), btns = document.createElement('div');
    box2.className = 'hlai-edit'; ta.value = history[i].content; ta.maxLength = 4000;
    const mk = (label, cls, fn) => { const b = document.createElement('button'); b.type = 'button'; b.textContent = label; b.className = cls; b.addEventListener('click', fn); btns.appendChild(b); };
    mk(t().cancel, '', () => paint());
    mk(t().resend, 'y', () => { const v = ta.value.trim(); if (!v || busy) return; dropFrom(i, history.length - i); input.value = v; send(); });
    ta.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); btns.lastChild.click(); } else if (e.key === 'Escape') paint(); });
    box2.append(ta, btns);
    bubbleEl.replaceWith(box2); row.remove();
    ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length);
  }
  async function send() {
    const q = input.value.trim();
    if (!q || busy) return;
    input.value = '';
    history.push({role: 'user', content: q.slice(0, 4000)});
    save(); paint();
    busy = true; sendBtn.disabled = true;
    const live = bubble('a', t().wait);
    let text = '', final = null, failed = null, timer = 0;
    const draw = () => { timer = 0; live.innerHTML = rich(text.replace(/^\s+/, '')); log.scrollTop = log.scrollHeight; };
    try {
      const r = await fetch(api() + '/api/ai/chat', {method: 'POST', headers: {'Content-Type': 'application/json', ...(token() ? {Authorization: 'Bearer ' + token()} : {})},
        body: JSON.stringify({lang: ko() ? 'ko' : 'en', style, stream: true, messages: history.map(m => ({role: m.role, content: m.content}))})});
      if (!r.ok) { const data = await r.json().catch(() => ({})); throw Object.assign(new Error(data.error || '_'), {code: data.error}); }
      if (/event-stream/.test(r.headers.get('Content-Type') || '') && r.body) {
        await readEvents(r, (ev, data) => {
          if (ev === 'delta') { text += data.t || ''; if (!timer) timer = setTimeout(draw, 60); }
          else if (ev === 'done') final = data;
          else if (ev === 'error') failed = data.error || '_';
        });
      } else final = await r.json();
      if (failed || !final) throw Object.assign(new Error(failed || '_'), {code: failed});
      clearTimeout(timer);
      history.push({role: 'assistant', content: String(final.answer || text), sources: Array.isArray(final.sources) ? final.sources : [], id: final.id || null});
      save(); paint();
    } catch (e) {
      clearTimeout(timer);
      live.className = 'hlai-m e';
      live.textContent = (t().err[e.code] || t().err._) + ' ';
      if (e.code === 'guest_limit' || e.code === 'login_required') live.appendChild(loginLink());
      history.pop(); save();
    } finally { busy = false; sendBtn.disabled = false; input.focus(); }
  }
  function toggle(on) { box.classList.toggle('on', on); btn.style.display = on ? 'none' : ''; if (on) { paint(); readTrain(); input.focus(); } }

  const sheet = document.createElement('style'); sheet.textContent = css; document.head.appendChild(sheet);
  const btn = document.createElement('button');
  btn.className = 'hlai-btn'; btn.type = 'button'; btn.textContent = t().open;
  btn.addEventListener('click', () => toggle(true));
  box = document.createElement('div');
  box.className = 'hlai'; box.setAttribute('role', 'dialog'); box.setAttribute('aria-label', t().title);
  box.innerHTML = `<div class="hlai-h"><b data-t="title">${esc(t().title)}</b><button type="button" data-a="style" title="${esc(t().styleHint)}">${esc(t().style[style])}</button><button type="button" data-a="clear">${esc(t().clear)}</button><button type="button" data-a="close" aria-label="${esc(t().close)}">✕</button></div>
<div class="hlai-log" aria-live="polite"></div><div class="hlai-note"><span data-t="note">${esc(t().note)}</span><label class="hlai-train" hidden><input type="checkbox" data-a="train"><span data-t="train">${esc(t().train)}</span></label></div>
<form class="hlai-f"><textarea rows="2" maxlength="4000" placeholder="${esc(t().ph)}"></textarea><button type="submit" data-t="send">${esc(t().send)}</button></form>`;
  log = box.querySelector('.hlai-log'); input = box.querySelector('textarea'); sendBtn = box.querySelector('.hlai-f button');
  box.querySelector('[data-a=close]').addEventListener('click', () => toggle(false));
  box.querySelector('[data-a=style]').addEventListener('click', e => {
    style = style === 'community' ? 'default' : 'community';
    try { localStorage.setItem(STYLE_KEY, style); } catch {}
    e.currentTarget.textContent = t().style[style];
  });
  box.querySelector('[data-a=train]').addEventListener('change', e => setTrain(e.currentTarget.checked));
  box.querySelector('[data-a=clear]').addEventListener('click', () => { history = []; save(); paint(); });
  box.querySelector('form').addEventListener('submit', e => { e.preventDefault(); send(); });
  input.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(); } });
  addEventListener('storage', e => { if (e.key === 'hlCmTok' && box.classList.contains('on')) { paint(); readTrain(); } });
  /* the site switches language without a reload (setLang sets <html lang>): every fixed label follows */
  function relabel() {
    const T = t();
    btn.textContent = T.open;
    box.setAttribute('aria-label', T.title);
    for (const el of box.querySelectorAll('[data-t]')) el.textContent = T[el.dataset.t];
    const sb = box.querySelector('[data-a=style]'); sb.textContent = T.style[style]; sb.title = T.styleHint;
    box.querySelector('[data-a=clear]').textContent = T.clear;
    box.querySelector('[data-a=close]').setAttribute('aria-label', T.close);
    input.placeholder = T.ph;
    if (box.classList.contains('on') && !busy) paint();
  }
  let shown = ko();
  new MutationObserver(() => { if (ko() !== shown) { shown = ko(); relabel(); } }).observe(document.documentElement, {attributes: true, attributeFilter: ['lang']});
  document.body.append(btn, box);
})();
