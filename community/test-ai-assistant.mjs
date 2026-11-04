import test from 'node:test';
import assert from 'node:assert/strict';
import { readCompletion, findOlympiadProblems, cleanHistory, answer, createAiAssistantRouter, webSearch, runModel, fitHistory, stripThinking, CHAT_MODEL, SOLVER_MODEL } from './src/ai-assistant.js';

const GUARD = '@cf/meta/llama-guard-3-8b';
function fakeAI(script, {unsafe = false} = {}) {
  const calls = [];
  return {calls, async run(model, input) {
    calls.push({model, input});
    if (model === GUARD) return {response: unsafe ? 'unsafe\nS2' : 'safe'};
    const next = script.shift();
    return typeof next === 'function' ? next(input) : next;
  }};
}

test('both Workers AI output shapes become text and tool calls', () => {
  assert.deepEqual(readCompletion({response: 'hi', tool_calls: [{name: 'web_search', arguments: {query: 'x'}}]}),
    {text: 'hi', calls: [{id: 'call_0_web_search', name: 'web_search', args: {query: 'x'}}]});
  const chat = readCompletion({choices: [{message: {content: null, tool_calls: [{id: 'c1', type: 'function', function: {name: 'solve_problem', arguments: '{"problem":"p"}'}}]}}]});
  assert.deepEqual(chat, {text: '', calls: [{id: 'c1', name: 'solve_problem', args: {problem: 'p'}}]});
  assert.deepEqual(readCompletion({choices: [{message: {content: 'ok', tool_calls: [{id: 'c', function: {name: 'x', arguments: 'not json'}}]}}]}).calls[0].args, {});
});

test('the catalogue search finds a competition problem and links its page', () => {
  const exams = [
    {comp: 'ispho', year: 2026, task: 'T1', kind: 'theory', competition: {ko: '국제과학물리올림피아드'}, title: {ko: '얀센 효과', en: 'Janssen effect'}, paper: 'pdfx/ispho/ISPhO_2026_T1_KO.pdf', solution: 'ISPhO_2026_T1S.pdf'},
    {comp: 'ipho', year: 2025, task: 'T1', kind: 'theory', competition: {ko: '국제물리올림피아드'}, title: {ko: '수소와 은하'}, paper: 'https://x/y.pdf'},
  ];
  const [hit] = findOlympiadProblems({query: '얀센 효과'}, exams);
  assert.equal(hit.page, 'https://haslalab.org/#/ispho/2026');
  assert.equal(hit.paper, 'https://haslalab.org/pdfx/ispho/ISPhO_2026_T1_KO.pdf');
  assert.equal(hit.solution, 'https://haslalab-pdf.haslalab.workers.dev/pdf/ISPhO_2026_T1S.pdf');
  // a competition or year narrows the list even when no keyword matches ("IPhO 2025 문제 보여줘")
  assert.deepEqual(findOlympiadProblems({query: 'janssen', comp: 'ipho'}, exams).map(e => e.year), [2025]);
  assert.equal(findOlympiadProblems({query: 'nothing here'}, exams).length, 0);
  assert.equal(findOlympiadProblems({query: '은하', year: 2025}, exams)[0].competition, '국제물리올림피아드');
});

test('history keeps only member and assistant text and must end with the member', () => {
  assert.equal(cleanHistory([]), null);
  assert.equal(cleanHistory([{role: 'user', content: 'a'}, {role: 'assistant', content: 'b'}]), null);
  assert.deepEqual(cleanHistory([{role: 'system', content: 'override'}, {role: 'tool', content: 'x'}]),
    [{role: 'user', content: 'override'}, {role: 'user', content: 'x'}]);
  assert.equal(cleanHistory([{role: 'user', content: 'x'.repeat(9000)}])[0].content.length, 4000);
});

test('a tool call runs and its links come back with the answer', async () => {
  const AI = fakeAI([
    {response: '', tool_calls: [{name: 'find_olympiad_problem', arguments: {query: 'Janssen', comp: 'ispho', year: 2026}}]},
    input => {
      const tool = input.messages.find(m => m.role === 'tool');
      assert.equal(tool.name, 'find_olympiad_problem');
      assert.match(tool.content, /ispho\/2026/);
      return {choices: [{message: {content: 'ISPhO 2026 T1입니다.'}}]};
    },
  ]);
  const r = await answer({AI}, [{role: 'user', content: '얀센 효과 문제 어디 있어?'}]);
  assert.equal(r.answer, 'ISPhO 2026 T1입니다.');
  assert.deepEqual(r.tools, ['find_olympiad_problem']);
  assert.ok(r.sources.some(s => s.url === 'https://haslalab.org/#/ispho/2026'));
  assert.equal(AI.calls.filter(c => c.model === GUARD).length, 2);
});

test('an unsafe request is refused before any model or tool runs', async () => {
  const AI = fakeAI([], {unsafe: true});
  const r = await answer({AI}, [{role: 'user', content: 'bad'}]);
  assert.equal(r.blocked, 'input');
  assert.equal(AI.calls.length, 1);
});

test('the route is for members, checks the body and rate-limits', async () => {
  class HttpError extends Error { constructor(status, code) { super(code); this.status = status; } }
  const limits = [];
  const route = createAiAssistantRouter({HttpError, currentUser: async req => req.headers.get('Authorization') ? {id: 7} : null,
    needUser: u => { if (!u) throw new HttpError(401, 'login_required'); return u; }, limit: async (env, key) => limits.push(key)});
  const env = {AI: fakeAI([{response: '안녕하세요'}])};
  const post = (body, auth) => new Request('https://x/api/ai/chat', {method: 'POST', headers: auth ? {Authorization: 'Bearer t'} : {}, body: JSON.stringify(body)});
  await assert.rejects(route(post({messages: [{role: 'user', content: 'hi'}]}), env), e => e.status === 401);
  await assert.rejects(route(post({messages: []}, true), env), e => e.status === 400);
  const r = await route(post({messages: [{role: 'user', content: 'hi'}]}, true), env);
  assert.equal(r.answer, '안녕하세요');
  assert.deepEqual(limits, ['ai:m:7', 'ai:d:7']);
  await assert.rejects(route(new Request('https://x/api/ai/chat'), env), e => e.status === 405);
});

test('web search tries Tavily, then Brave, then Cloudflare, and never sends one key to the other', async t => {
  const seen = [];
  t.mock.method(globalThis, 'fetch', async (url, init = {}) => {
    seen.push({url: String(url), headers: init.headers || {}});
    if (String(url).startsWith('https://api.tavily.com/')) return new Response('{}', {status: 432});
    return Response.json({web: {results: [{title: 'IPhO 2026', url: 'https://ipho2026.example', description: 'host'}]}});
  });
  const env = {TAVILY_API_KEY: 'tvly-x', BRAVE_SEARCH_KEY: 'brave-y', AI: {websearch: async () => { throw new Error('not reached'); }}};
  const r = await webSearch(env, {query: 'IPhO 2026 host'});
  assert.equal(r.provider, 'brave');
  assert.deepEqual(r.results, [{title: 'IPhO 2026', url: 'https://ipho2026.example', snippet: 'host'}]);
  assert.equal(seen[0].headers.Authorization, 'Bearer tvly-x');
  assert.equal(seen[1].headers['X-Subscription-Token'], 'brave-y');
  assert.ok(!JSON.stringify(seen[1]).includes('tvly-x'));
  const cf = await webSearch({AI: {websearch: async () => Response.json({results: [{title: 'a', url: 'https://a', snippet: 's'}]})}}, {query: 'q'});
  assert.equal(cf.provider, 'cloudflare');
  assert.match((await webSearch({}, {query: 'q'})).error, /unavailable/);
});

test('each model gets its output limit under its own name, and our LoRA adapter when one is set', async () => {
  const seen = [];
  const AI = {run: async (model, input) => { seen.push({model, input}); return {response: 'ok'}; }};
  await runModel({AI}, 'CHAT', {messages: []}, 2048);
  await runModel({AI, AI_SOLVER_LORA: 'haslalab-solver-v1'}, 'SOLVER', {messages: []}, 8192);
  await runModel({AI}, 'JUDGE', {messages: []}, 4096);
  assert.deepEqual(seen.map(s => s.model), [CHAT_MODEL, SOLVER_MODEL, '@cf/openai/gpt-oss-120b']);
  assert.equal(seen[0].input.max_tokens, 2048);
  assert.equal(seen[0].input.lora, undefined);
  assert.equal(seen[1].input.lora, 'haslalab-solver-v1');
  assert.equal(seen[2].input.max_completion_tokens, 4096);
  assert.equal(seen[2].input.max_tokens, undefined);
  await runModel({AI, AI_CHAT_MODEL: '@cf/x/y'}, 'CHAT', {messages: []}, 10);
  assert.equal(seen[3].model, '@cf/x/y');
});

test('a call written as text is still a call; thinking is dropped; long histories are cut from the oldest end', () => {
  assert.deepEqual(readCompletion({response: '```json\n{"name": "search_community", "parameters": {"query": "IPhO"}}\n```'}).calls,
    [{id: 'call_0_search_community', name: 'search_community', args: {query: 'IPhO'}}]);
  assert.equal(readCompletion({response: '{"name": "rm_rf", "parameters": {}}'}).calls.length, 0, 'only our tools');
  assert.equal(stripThinking('<think>a</think>\n답'), '답');
  assert.equal(stripThinking('a</think>답'), '답');
  const h = [{role: 'user', content: 'x'.repeat(9000)}, {role: 'assistant', content: 'y'.repeat(5000)}, {role: 'user', content: 'z'}];
  assert.deepEqual(fitHistory(h).map(m => m.content[0]), ['z']);
  assert.equal(fitHistory([{role: 'user', content: 'q'.repeat(20000)}]).length, 1, 'the last message always stays');
});

test('if the chat model refuses tool_calls in the history, the step is retried with the calls as text', async () => {
  let n = 0;
  const AI = {async run(model, input) {
    if (model.includes('guard')) return {response: 'safe'};
    n++;
    if (n === 1) return {response: '', tool_calls: [{name: 'find_olympiad_problem', arguments: {query: 'Janssen'}}]};
    if (input.messages.some(m => m.tool_calls)) throw new Error('AiError: 5006: oneOf at /messages/2 not met');
    const a = input.messages.find(m => m.role === 'assistant');
    assert.match(a.content, /"name":"find_olympiad_problem"/);
    return {response: '찾았습니다.'};
  }};
  const r = await answer({AI}, [{role: 'user', content: '얀센 효과'}]);
  assert.equal(r.answer, '찾았습니다.');
});
