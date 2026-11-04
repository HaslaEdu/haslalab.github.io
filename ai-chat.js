/* HaslaLab assistant: a chat button on every page. It talks to the community Worker's /api/ai/chat (open-weight
   models on Workers AI, members only); the conversation lives in this tab only (sessionStorage). */
(() => {
  'use strict';
  const PROD = 'https://haslalab-community-edge.haslalab.workers.dev', MAX_TURNS = 20, KEY = 'hlAiChat';
  const api = () => { try { const o = localStorage.getItem('hlCmApi') || ''; return (/^(?:https?:\/\/(?:localhost|127\.0\.0\.1)(?::\d+)?|https:\/\/[a-z0-9-]+\.haslalab\.workers\.dev)\/?$/.test(o) ? o : PROD).replace(/\/+$/, ''); } catch { return PROD; } };
  const token = () => { try { return localStorage.getItem('hlCmTok') || ''; } catch { return ''; } };
  const ko = () => !/[?&]lang=en\b/.test(location.search) && document.documentElement.lang !== 'en';
  const T = {
    ko: {open: 'AI에게 묻기', title: '하슬라랩 AI', hint: '문제 위치, 풀이 설명, 커뮤니티 글, 웹 정보를 물어보세요.', ph: '질문을 입력하세요 (Enter 전송, Shift+Enter 줄바꿈)',
      send: '보내기', clear: '대화 지우기', close: '닫기', login: '로그인한 회원만 쓸 수 있습니다.', loginGo: '로그인하기', wait: '생각하는 중…', sources: '관련 링크',
      err: {rate_limited: '질문이 너무 많습니다. 잠시 후 다시 시도해 주세요.', login_required: '로그인이 필요합니다.', ai_unavailable: 'AI를 지금 쓸 수 없습니다.', _: '답을 받지 못했습니다. 잠시 후 다시 시도해 주세요.'},
      note: 'AI 답변은 틀릴 수 있습니다. 중요한 내용은 원문과 해설로 확인하세요.'},
    en: {open: 'Ask AI', title: 'HaslaLab AI', hint: 'Ask where a problem is, for an explanation, about posts, or for web information.', ph: 'Type a question (Enter to send, Shift+Enter for a new line)',
      send: 'Send', clear: 'Clear chat', close: 'Close', login: 'Members only.', loginGo: 'Log in', wait: 'Thinking…', sources: 'Links',
      err: {rate_limited: 'Too many questions. Please try again shortly.', login_required: 'Please log in.', ai_unavailable: 'The assistant is unavailable right now.', _: 'No answer came back. Please try again.'},
      note: 'AI answers can be wrong. Check important points against the papers and solutions.'},
  };
  const t = () => T[ko() ? 'ko' : 'en'];
  let history = [];
  try { history = JSON.parse(sessionStorage.getItem(KEY) || '[]').filter(m => m && typeof m.content === 'string').slice(-MAX_TURNS); } catch { history = []; }
  const save = () => { try { sessionStorage.setItem(KEY, JSON.stringify(history.slice(-MAX_TURNS))); } catch {} };

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
.hlai-m.a{align-self:flex-start;background:rgba(46,57,69,.07)}
.hlai-m.e{align-self:flex-start;color:var(--laser,#E02424)}
.hlai-m a{color:inherit;text-decoration:underline}
.hlai-src{margin-top:6px;font-size:12px;color:var(--graphite,#5C6B7A)}
.hlai-src a{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hlai-hint,.hlai-note{color:var(--graphite,#5C6B7A);font-size:12px}
.hlai-note{padding:0 12px 6px}
.hlai-f{display:flex;gap:8px;padding:10px 12px;border-top:1px solid var(--grid-bold,#B4CADC)}
.hlai-f textarea{flex:1;resize:none;height:44px;border:1px solid var(--grid-bold,#B4CADC);border-radius:8px;padding:8px;font:14px var(--sans,sans-serif);background:transparent;color:inherit}
.hlai-f button{border:0;border-radius:8px;padding:0 14px;background:var(--rail,#2E3945);color:#fff;font:600 13px var(--sans,sans-serif);cursor:pointer}
.hlai-f button:disabled{opacity:.5;cursor:default}
html[data-theme="dark"] .hlai{background:#151b22;color:#e6edf3;border-color:#2b3642}
html[data-theme="dark"] .hlai-m.a{background:rgba(255,255,255,.07)}
@media print{.hlai,.hlai-btn{display:none!important}}`;

  const esc = s => s.replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const linkify = s => esc(s).replace(/\bhttps?:\/\/[^\s<>"')\]]+/g, u => `<a href="${u}" target="_blank" rel="noopener">${u}</a>`);
  let box, log, input, sendBtn, busy = false;

  function bubble(role, text, sources) {
    const d = document.createElement('div');
    d.className = 'hlai-m ' + role;
    d.innerHTML = linkify(text);
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
  function paint() {
    log.innerHTML = '';
    if (!token()) {
      const d = bubble('a', t().login);
      const a = document.createElement('a');
      a.href = '#/login'; a.textContent = ' ' + t().loginGo;
      a.addEventListener('click', () => { try { sessionStorage.setItem('hlCmBack', location.hash); } catch {} toggle(false); });
      d.appendChild(a);
      return;
    }
    if (!history.length) { const h = document.createElement('div'); h.className = 'hlai-hint'; h.textContent = t().hint; log.appendChild(h); }
    for (const m of history) bubble(m.role === 'user' ? 'u' : 'a', m.content, m.sources);
  }
  async function send() {
    const q = input.value.trim();
    if (!q || busy || !token()) return;
    input.value = '';
    history.push({role: 'user', content: q.slice(0, 4000)});
    save(); paint();
    busy = true; sendBtn.disabled = true;
    const wait = bubble('a', t().wait);
    try {
      const r = await fetch(api() + '/api/ai/chat', {method: 'POST', headers: {'Content-Type': 'application/json', Authorization: 'Bearer ' + token()},
        body: JSON.stringify({lang: ko() ? 'ko' : 'en', messages: history.map(m => ({role: m.role, content: m.content}))})});
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw Object.assign(new Error(data.error || '_'), {code: data.error});
      history.push({role: 'assistant', content: String(data.answer || ''), sources: Array.isArray(data.sources) ? data.sources : []});
      save(); paint();
    } catch (e) {
      wait.className = 'hlai-m e';
      wait.textContent = t().err[e.code] || t().err._;
      history.pop(); save();
    } finally { busy = false; sendBtn.disabled = false; input.focus(); }
  }
  function toggle(on) { box.classList.toggle('on', on); btn.style.display = on ? 'none' : ''; if (on) { paint(); input.focus(); } }

  const style = document.createElement('style'); style.textContent = css; document.head.appendChild(style);
  const btn = document.createElement('button');
  btn.className = 'hlai-btn'; btn.type = 'button'; btn.textContent = t().open;
  btn.addEventListener('click', () => toggle(true));
  box = document.createElement('div');
  box.className = 'hlai'; box.setAttribute('role', 'dialog'); box.setAttribute('aria-label', t().title);
  box.innerHTML = `<div class="hlai-h"><b>${esc(t().title)}</b><button type="button" data-a="clear">${esc(t().clear)}</button><button type="button" data-a="close" aria-label="${esc(t().close)}">✕</button></div>
<div class="hlai-log" aria-live="polite"></div><div class="hlai-note">${esc(t().note)}</div>
<form class="hlai-f"><textarea rows="2" maxlength="4000" placeholder="${esc(t().ph)}"></textarea><button type="submit">${esc(t().send)}</button></form>`;
  log = box.querySelector('.hlai-log'); input = box.querySelector('textarea'); sendBtn = box.querySelector('.hlai-f button');
  box.querySelector('[data-a=close]').addEventListener('click', () => toggle(false));
  box.querySelector('[data-a=clear]').addEventListener('click', () => { history = []; save(); paint(); });
  box.querySelector('form').addEventListener('submit', e => { e.preventDefault(); send(); });
  input.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(); } });
  addEventListener('storage', e => { if (e.key === 'hlCmTok' && box.classList.contains('on')) paint(); });
  document.body.append(btn, box);
})();
