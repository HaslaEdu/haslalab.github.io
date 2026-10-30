import test from 'node:test';
import assert from 'node:assert/strict';
import { provision, QUEUES } from './provision-jobs.mjs';

test('deployment creates only the two named queues without requiring D1 import or management access', async () => {
  const calls = [];
  await provision(async args => { calls.push(args); return { code: 0, output: '' }; }, () => {});
  assert.deepEqual(calls, QUEUES.map(queue => ['queues', 'create', queue]));
});
test('repeated deployments reuse queues, while permission failures stop before migration or deploy', async () => {
  let calls = 0;
  await provision(async () => ({ code: ++calls <= 2 ? 1 : 0, output: 'A queue with this name already exists.' }), () => {});
  assert.equal(calls, 2);
  calls = 0;
  await assert.rejects(provision(async () => { calls++; return { code: 1, output: 'Authentication error: permission denied [403]' }; }, () => {}), /Cannot provision/);
  assert.equal(calls, 1);
});
test('network failures and misleading already-exists text cannot hide an authentication failure', async () => {
  await assert.rejects(provision(async () => ({ code: 1, output: 'connection timed out' }), () => {}), /Cannot provision/);
  await assert.rejects(provision(async () => ({ code: 1, output: 'A queue already exists. Authentication error [403]' }), () => {}), /Cannot provision/);
});
