const test = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {resolve} = require('node:path');
const {createRequire} = require('node:module');
const {JSDOM} = createRequire(resolve(__dirname, '../community/package.json'))('jsdom');

const read = path => readFileSync(resolve(__dirname, '..', path), 'utf8');
const flush = () => new Promise(done => setImmediate(done));
const key = 'hlWorkshopCompute';
const answer = [
  'Energy is $E=mc^2$ and \\(p=mv\\).',
  '\\[F=ma\\]',
  '$$v=at$$',
  '```python',
  'print("$literal$")',
  '```',
  '<img src=x onerror=alert(1)>',
].join('\n');

function setup(t) {
  const dom = new JSDOM('<!doctype html><main></main>', {
    url:'https://haslalab.org/create.html?view=compute', runScripts:'outside-only',
  });
  t.after(() => dom.window.close());
  const w = dom.window;
  const root = w.document.querySelector('main');
  const $ = id => root.querySelector('#' + id);
  w.HL_WORKSHOP_PROJECTS = {
    client: () => ({}), panelHandle: () => '', panelTab: () => '',
    bindPanels: () => ({reveal() {}}),
    providerSelect: () => {
      const select = w.document.createElement('select');
      select.append(new w.Option('Storage', 'store'));
      return select;
    },
    library: (host, _, {onResume}) => {
      const heading = w.document.createElement('button');
      heading.onclick = onResume;
      host.replaceChildren(heading);
      return {heading};
    },
  };
  w.eval(read('vendor/katex/katex.min.js'));
  w.eval(read('vendor/katex/contrib/auto-render.min.js'));
  w.eval(read('workshop-compute.js'));
  const ctx = {
    root, apiBase:'https://worker.test', token:() => 'test', height() {}, lang:'ko', esc: x => x,
    api:async (path, method, body) => {
      assert.equal(path, '/api/workshop/code-ai');
      assert.equal(method, 'POST');
      assert.equal(body.mode, 'chat');
      return {explanation:answer, left:1};
    },
  };
  return {w, $, open: params => w.HL_WORKSHOP_COMPUTE.open(ctx, params)};
}

test('compute responses render four LaTeX delimiters and preserve the chat when closed or reopened from an unsaved draft', async t => {
  const {w, $, open} = setup(t);
  const previous = {format:'haslalab-compute', title:'Other draft', history:[]};
  w.localStorage.setItem(key, JSON.stringify(previous));
  w.sessionStorage.setItem('hlWorkshopComputeQuestion', JSON.stringify({title:'Motion', text:'A physics problem'}));
  const instance = open({transfer:'problem'});
  assert.equal($('cpWorkspace').getAttribute('aria-expanded'), 'true');
  $('cpTaskMode').value = 'chat';
  $('cpPrompt').value = 'Explain energy';
  $('cpPrompt').dispatchEvent(new w.KeyboardEvent('keydown', {key:'Enter', shiftKey:true, cancelable:true}));
  assert.equal($('cpChat').children.length, 0);
  $('cpPrompt').dispatchEvent(new w.KeyboardEvent('keydown', {key:'Enter', cancelable:true}));
  await flush();
  const response = $('cpChat').querySelector('.compute-turn-assistant');
  assert.equal(response.querySelectorAll('.katex').length, 4);
  assert.equal(response.querySelector('pre code').textContent.trim(), 'print("$literal$")');
  assert.equal(response.querySelector('img'), null);
  $('cpChatSize').click();
  assert.ok($('cpEditor').classList.contains('chat-expanded'));
  $('cpChatSize').click();
  assert.ok(!$('cpEditor').classList.contains('chat-expanded'));
  $('cpChatClose').click();
  assert.ok($('cpAssistant').hidden);
  $('cpWorkspace').click();
  assert.ok(!$('cpAssistant').hidden);
  assert.equal($('cpChat').children.length, 2);
  $('cpChatClose').click();
  instance.stop();
  assert.deepEqual(JSON.parse(w.localStorage.getItem(key)), previous);
  const resumed = open({});
  assert.equal($('cpTitle').value, 'Motion');
  assert.ok($('cpAssistant').hidden);
  $('cpWorkspace').click();
  assert.equal($('cpChat').querySelectorAll('.katex').length, 4);
  assert.equal($('cpChat').children.length, 2);
  resumed.stop();
});

test('editing a saved work restores its local conversation and keeps it out of preview mode', async t => {
  const {w, $, open} = setup(t);
  const record = {
    format:'haslalab-compute', language:'python', sources:{python:'print("draft")', c:''},
    title:'Draft', history:[{role:'assistant', content:'Local answer $F=ma$'}], assistant_open:true,
  };
  w.localStorage.setItem(key + ':project:17', JSON.stringify(record));
  w.HL_SHARE = {get: async () => ({project:{mine:true, language:'python', code:'print("remote")', title:'Saved'}})};
  const editor = open({id:'17'});
  await flush();
  assert.equal($('cpTitle').value, 'Draft');
  assert.match($('cpChat').textContent, /Local answer/);
  assert.equal($('cpChat').querySelectorAll('.katex').length, 1);
  editor.stop();
  const preview = open({id:'17', preview:true});
  await flush();
  assert.equal($('cpTitle').value, 'Saved');
  assert.equal($('cpChat'), null);
  preview.stop();
});
