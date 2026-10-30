import test from 'node:test';
import assert from 'node:assert/strict';
import { provision, QUEUES } from './provision-jobs.mjs';

test('deployment creates only the two named queues and applies only the additive job migration', async () => {
  const calls = [];
  await provision(async args => { calls.push(args); return { code: 0, output: '' }; }, () => {});
  assert.deepEqual(calls.slice(0, 2), QUEUES.map(queue => ['queues', 'create', queue]));
  assert.deepEqual(calls[2], ['d1', 'execute', 'haslalab-community', '--remote', '--yes', '--file', 'migrations/0013_lab_jobs.sql']);
});
test('repeated deployments reuse queues, while permission failures stop before migration or deploy', async () => {
  let calls = 0;
  await provision(async () => ({ code: ++calls <= 2 ? 1 : 0, output: 'A queue with this name already exists.' }), () => {});
  assert.equal(calls, 3);
  calls = 0;
  await assert.rejects(provision(async () => { calls++; return { code: 1, output: 'Authentication error: permission denied [403]' }; }, () => {}), /Cannot provision/);
  assert.equal(calls, 1);
});
test('network and SQL failures cannot be treated as successful provisioning', async () => {
  await assert.rejects(provision(async () => ({ code: 1, output: 'connection timed out' }), () => {}), /Cannot provision/);
  let calls = 0;
  await assert.rejects(provision(async () => ({ code: ++calls <= 2 ? 0 : 1, output: 'database unavailable' }), () => {}), /Cannot prepare job storage/);
});
