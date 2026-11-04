// QwQ 32B, Hasla AI's reasoning model, run so that it always comes back with an answer and thinks only as long as
// the task needs (the IPhO 2016 grading bench, 2026-11-04: one-shot calls timed out with 3046, and a streamed call
// thought past its 16k-token limit and never reached the answer).
//   · streamed, so a long think never meets the one-shot request timeout
//   · Qwen's sampling for QwQ (temperature 0.6, top_p 0.95): greedy decoding makes it repeat itself without end
//   · a thinking budget: the stream is cut when the think reaches `budget` tokens, «</think>» is written for it and a
//     second call writes only the answer from the thinking so far (budget forcing)
//   · the prompt is QwQ's own chat template sent raw, which is what lets the second call continue the same turn
// Workers AI's QwQ has a 24k-token context: the input, the budget and the answer together must fit in it.
import { sseTexts } from './ai-assistant.js';

export const QWQ_MODEL = '@cf/qwen/qwq-32b';
export const QWQ_CONTEXT = 24000;
const SAMPLING = { temperature: 0.6, top_p: 0.95 };

/* QwQ's chat template (ChatML), opened on the assistant's think */
export function qwqPrompt(system, messages) {
  const turn = (role, text) => `<|im_start|>${role}\n${text}<|im_end|>\n`;
  return (system ? turn('system', system) : '') + messages.map(m => turn(m.role === 'assistant' ? 'assistant' : 'user', String(m.content ?? ''))).join('')
    + '<|im_start|>assistant\n<think>\n';
}

/* reads a stream of pieces until it ends, the think closes, or a limit; returns what came */
async function readStream(stream, { thinking, budget, cap }) {
  let think = '', answer = '', n = 0, closed = !thinking, usage = null;
  for await (const p of sseTexts(stream)) {
    if (p.usage) usage = p.usage;
    if (!p.text) continue;
    n++;
    if (closed) { answer += p.text; if (n >= cap) break; continue; }
    think += p.text;
    const k = think.indexOf('</think>');
    if (k >= 0) { answer = think.slice(k + 8); think = think.slice(0, k); closed = true; n = 0; continue; }
    if (n >= budget) break;
  }
  return { think, answer, closed, pieces: n, usage };
}

/** one reasoning turn within a budget: {thinking, answer, forced, think_tokens, answer_tokens, ms} */
export async function reasonBudgeted(env, { system = '', messages, budget = 4000, answerTokens = 1500, lora = null, model = QWQ_MODEL } = {}) {
  const t0 = Date.now(), prompt = qwqPrompt(system, messages), extra = lora ? { lora } : {};
  const run = (p, max) => env.AI.run(model, { prompt: p, raw: true, stream: true, max_tokens: max, ...SAMPLING, ...extra });
  const first = await readStream(await run(prompt, budget + answerTokens), { thinking: true, budget, cap: answerTokens });
  let { think, answer } = first, forced = false, answerPieces = first.closed ? first.pieces : 0;
  if (!first.closed || !answer.trim()) {
    /* the budget ran out (or the think closed with nothing after it): the answer is written from the thinking so far */
    forced = !first.closed;
    const next = await readStream(await run(prompt + think.trimEnd() + '\n</think>\n\n', answerTokens), { thinking: false, budget: 0, cap: answerTokens });
    answer = next.answer; answerPieces = next.pieces;
  }
  return { thinking: think.trim(), answer: answer.replace(/<\|im_end\|>[\s\S]*$/, '').trim(), forced,
    think_tokens: first.closed ? null : first.pieces, answer_tokens: answerPieces, ms: Date.now() - t0 };
}

/* marks written one per line («A1.1 0.3», «B.1.2/1: 0.25»), the format asked of a reasoning model at the end of its
   thinking; JSON with misplaced quotes ({"items:[{id:A1.1,score":.3}) is read pair by pair */
export function readMarkLines(text) {
  const out = [], seen = new Set(), add = (id, score) => { if (!seen.has(id) && Number.isFinite(score)) { seen.add(id); out.push({ id, score }); } };
  for (const line of String(text || '').split('\n')) {
    const m = /^\s*(?:[-*•]\s*)?`?([A-Za-z0-9][\w.\/-]*)`?\s*[:=]?\s+(-?\d*\.?\d+)\s*(?:\/\s*\d*\.?\d+)?\s*$/.exec(line)
      || /^\s*(?:[-*•]\s*)?`?([A-Za-z0-9][\w.\/-]*)`?\s*[:=]\s*(-?\d*\.?\d+)\s*$/.exec(line);
    if (m && /[A-Za-z.]/.test(m[1])) add(m[1], +m[2]);
  }
  if (!out.length) for (const m of String(text || '').matchAll(/"?id"?\s*:\s*"?([\w.\/-]+)"?\s*,\s*"?score"?\s*:\s*"?(-?\d*\.?\d+)/g)) add(m[1], +m[2]);
  return out;
}
