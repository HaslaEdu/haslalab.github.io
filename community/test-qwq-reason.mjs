// QwQ run so it always answers within a thinking budget (qwq-reason.js), and the stream reader it relies on.
import test from 'node:test';
import assert from 'node:assert/strict';
import { reasonBudgeted, readMarkLines, qwqPrompt } from './src/qwq-reason.js';
import { sseTexts } from './src/ai-assistant.js';

const sse = pieces => new ReadableStream({ start(c) { for (const p of pieces) c.enqueue(new TextEncoder().encode(typeof p === 'string' ? p : `data: ${JSON.stringify(p)}\n`)); c.enqueue(new TextEncoder().encode('data: [DONE]\n')); c.close(); } });

test('a think that closes by itself: the answer is what follows it, with QwQ sampling and the raw template', async () => {
  const calls = [];
  const env = { AI: { async run(model, input) { calls.push({ model, input }); return sse([{ response: 'check B1' }, { response: '</think>\n\nA1.1 0.3' }, { response: '\nA1.2 0' }]); } } };
  const r = await reasonBudgeted(env, { system: 'S', messages: [{ role: 'user', content: 'U' }], budget: 100, answerTokens: 50 });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].model, '@cf/qwen/qwq-32b');
  assert.deepEqual([calls[0].input.raw, calls[0].input.stream, calls[0].input.temperature, calls[0].input.top_p], [true, true, 0.6, 0.95]);
  assert.ok(calls[0].input.prompt.endsWith('<|im_start|>assistant\n<think>\n'));
  assert.equal(r.thinking, 'check B1');
  assert.equal(r.answer, 'A1.1 0.3\nA1.2 0');
  assert.equal(r.forced, false);
});

test('a think that runs past the budget is cut, closed, and the answer is written from it in a second call', async () => {
  const calls = [];
  const env = { AI: { async run(model, input) {
    calls.push(input);
    return calls.length === 1 ? sse(Array.from({ length: 50 }, (_, i) => ({ response: ` step${i}` }))) : sse([{ response: 'A1.1 0.2' }, { response: '<|im_end|>' }]);
  } } };
  const r = await reasonBudgeted(env, { messages: [{ role: 'user', content: 'U' }], budget: 10, answerTokens: 40, lora: 'haslalab-solver' });
  assert.equal(calls.length, 2);
  assert.equal(r.forced, true);
  assert.equal(r.think_tokens, 10);
  assert.ok(calls[1].prompt.endsWith('step9\n</think>\n\n'), calls[1].prompt.slice(-40));
  assert.equal(calls[1].max_tokens, 40);
  assert.equal(calls[0].lora, 'haslalab-solver');
  assert.equal(r.answer, 'A1.1 0.2');
});

test('the stream reader keeps a lone 0 and a response it can read out of a line that is not JSON', async () => {
  const got = [];
  for await (const p of sseTexts(sse([{ response: 'IPhO 2' }, { response: 0 }, { response: '16' }, 'data: {"response":"\\"x\\"", broken\n', 'data: nonsense\n']))) got.push(p);
  assert.equal(got.map(p => p.text).join(''), 'IPhO 2016"x"');
  assert.equal(got.at(-1).bad, 'nonsense');
});

test('marks one per line, and JSON with misplaced quotes, are read', () => {
  assert.deepEqual(readMarkLines('A1.1 0.3\nA1.2: 0\n- B.1.2/1 0.25\nB2 .5 / 0.5'), [{ id: 'A1.1', score: 0.3 }, { id: 'A1.2', score: 0 }, { id: 'B.1.2/1', score: 0.25 }, { id: 'B2', score: 0.5 }]);
  assert.deepEqual(readMarkLines('{"items:[{id:A1.1,score":.3}]}'), [{ id: 'A1.1', score: 0.3 }]);
  assert.equal(qwqPrompt('', [{ role: 'user', content: 'U' }]), '<|im_start|>user\nU<|im_end|>\n<|im_start|>assistant\n<think>\n');
});
