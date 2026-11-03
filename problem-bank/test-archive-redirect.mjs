import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {BANK_SUBJECTS} from '../community/src/problem-bank-model.js';
import {BANK_DISCIPLINES} from '../community/src/problem-bank-catalogue.js';

const code = readFileSync(new URL('./public/archive-redirect.js', import.meta.url), 'utf8');
const context = vm.createContext({URL, URLSearchParams});
vm.runInContext(code + '\nglobalThis.targetFor = archiveRedirectTarget;', context);
const targetFor = href => new URL(context.targetFor(href));
const oldURL = params => 'https://legacy.example/problem-bank/public/index.html?' + new URLSearchParams(params);
const hashParams = target => new URLSearchParams(target.hash.split('?')[1] || '');
const qid = 'q_' + 'a'.repeat(64), sid = 'src_' + 'b'.repeat(64);

test('known legacy IDs and search filters move to the fixed resolver with header language', () => {
  const values = {problem:qid, source:sid, collection:'astronomy', kind:'course', subject:'general_relativity', lang:'en', stars:'4', competition:'ipho', year:'1967', type:'theory', q:'  $E=mc^2$ 한글  '};
  const target = targetFor(oldURL(values));
  assert.equal(target.origin, 'https://haslalab.org');
  assert.equal(target.pathname, '/');
  assert.equal(target.search, '?lang=en');
  assert.equal(target.hash.split('?')[0], '#/archive/open');
  assert.deepEqual(Object.fromEntries(hashParams(target)), {...values, q:values.q.trim()});
});

test('empty, malformed and language-only links retain a usable book archive fallback', () => {
  for (const input of ['not a URL', 'https://legacy.example/', oldURL({problem:'q_bad',source:'src_bad'}), oldURL({lang:'invalid'})]) {
    assert.equal(targetFor(input).href, 'https://haslalab.org/#/archive/books/phys');
  }
  assert.equal(targetFor(oldURL({lang:'en'})).href, 'https://haslalab.org/?lang=en#/archive/books/phys');
});

test('credentials, destinations, cursors, embedding settings and all old hash data are discarded', () => {
  const values = {problem:qid, token:'PRIVATE_SYNTHETIC_TOKEN', access_token:'PRIVATE_ACCESS', password:'PRIVATE_PASSWORD', authorization:'Bearer PRIVATE', apiKey:'PRIVATE_KEY', session:'PRIVATE_SESSION', return:'https://evil.example', redirect:'//evil.example', next:'javascript:alert(1)', url:'https://evil.example', cursor:'sc_private', offset:'50', limit:'30', sort:'source', embed:'1', theme:'dark'};
  const target = targetFor(oldURL(values) + '#/arbitrary?token=PRIVATE_HASH');
  assert.deepEqual(Object.fromEntries(hashParams(target)), {problem:qid});
  assert.equal(target.search, '');
  assert.doesNotMatch(target.href, /PRIVATE|evil|javascript|arbitrary/);
  const userinfo = targetFor('https://username:PRIVATE_PASSWORD@legacy.example/?problem=' + qid);
  assert.equal(userinfo.username, '');
  assert.equal(userinfo.password, '');
});

test('duplicate keys and malformed filters are dropped without losing a valid problem', () => {
  const params = new URLSearchParams({problem:qid, source:'src_'+'B'.repeat(64), collection:'combined', kind:'school', subject:'javascript:alert(1)', lang:'fr', stars:'0', competition:'../evil', year:'1799', type:'written', q:'bad\nquery'});
  params.append('problem', qid);
  assert.equal(targetFor('https://legacy.example/?' + params).href, 'https://haslalab.org/#/archive/books/phys');
  params.delete('problem'); params.set('problem', qid); params.set('lang','en'); params.append('lang','ko');
  assert.deepEqual(Object.fromEntries(hashParams(targetFor('https://legacy.example/?' + params))), {problem:qid});
});

test('actual subject and collection enums are accepted and search values stay bounded', () => {
  for (const subject of BANK_SUBJECTS) assert.equal(hashParams(targetFor(oldURL({subject}))).get('subject'), subject);
  for (const collection of BANK_DISCIPLINES) assert.equal(hashParams(targetFor(oldURL({collection}))).get('collection'), collection);
  for (const year of ['1800','2199']) assert.equal(hashParams(targetFor(oldURL({year}))).get('year'),year);
  for (const [key,values] of Object.entries({year:['1799','2200','02000','1e3'],stars:['0','6','01'],competition:['a','a'.repeat(51),'IPhO'],q:['x'.repeat(601),'\u0000','\u007f','\u0085','   '],problem:[qid+'0',qid.slice(0,-1),'q_'+'g'.repeat(64)]})) {
    for (const value of values) assert.equal(hashParams(targetFor(oldURL({[key]:value}))).has(key),false,`${key}: ${JSON.stringify(value)}`);
  }
  const query = '$x=1$ & q=changed #/login?token=TEXT';
  assert.equal(hashParams(targetFor(oldURL({q:query}))).get('q'),query);
  assert.equal(targetFor(oldURL({q:query})).hash.split('?')[0],'#/archive/open');
});

function page(href, blocked = false) {
  const nodes = new Map(['archiveLink','archiveHeading','archiveMessage'].map(id => [id, {}]));
  const calls = [], deny = () => {throw new Error('Redirect must not read credentials or make requests');};
  const sandbox = {URL,URLSearchParams,window:{location:{href,replace(target){calls.push(target);if(blocked)throw new Error('Navigation blocked');}}},document:{documentElement:{lang:'ko'},getElementById:id=>nodes.get(id)}};
  for (const key of ['localStorage','sessionStorage','fetch']) Object.defineProperty(sandbox,key,{get:deny});
  Object.defineProperty(sandbox.document,'cookie',{get:deny});
  Object.defineProperty(sandbox.document,'referrer',{get:deny});
  Object.defineProperty(sandbox.window,'parent',{get:deny});
  vm.runInNewContext(code,sandbox);
  return {nodes,calls,document:sandbox.document};
}

test('entry replaces history once without storage, parent-session, cookie or network access', () => {
  const p = page(oldURL({problem:qid,lang:'en',token:'PRIVATE_SYNTHETIC_TOKEN'}));
  assert.equal(p.calls.length,1);
  assert.equal(p.calls[0],p.nodes.get('archiveLink').href);
  assert.equal(p.document.documentElement.lang,'en');
  assert.equal(p.nodes.get('archiveLink').textContent,'Open archive');
  assert.doesNotMatch(p.calls[0],/PRIVATE/);
});

test('blocked automatic navigation leaves the validated manual destination available', () => {
  const p = page(oldURL({source:sid,collection:'physics'}),true);
  assert.equal(p.calls.length,1);
  assert.equal(p.nodes.get('archiveLink').href,p.calls[0]);
  assert.equal(new URL(p.calls[0]).origin,'https://haslalab.org');
});
