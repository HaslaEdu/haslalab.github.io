// Requests to the AI providers that refuse this Worker's Hong Kong placement (Gemini, Vertex, Anthropic, OpenAI,
// Tavily) leave through the haslalab-ai-egress Worker (ai-egress/, placed in Seoul) over the AI_EGRESS service binding.
// Every handler in worker.js calls useEgress(env) first; the global fetch then sends those hosts there and everything
// else (the database, DeepSeek, the site …) straight out as before. Without the binding nothing changes.
import { egressHost } from '../../ai-egress/src/index.js';

const nativeFetch = globalThis.fetch.bind(globalThis);
let egress = null;
export function useEgress(env) { egress = env && env.AI_EGRESS && typeof env.AI_EGRESS.fetch === 'function' ? env.AI_EGRESS : null; }

export function egressFetch(input, init) {
  if (egress) {
    let url = null;
    try { url = new URL(typeof input === 'string' || input instanceof URL ? String(input) : input.url); } catch { url = null; }
    if (url && url.protocol === 'https:' && egressHost(url.hostname)) {
      const req = new Request(input, init), headers = new Headers(req.headers);
      headers.set('x-egress-url', req.url); headers.set('x-egress-redirect', req.redirect || 'follow');
      return egress.fetch('https://ai-egress.internal/', { method: req.method, headers, body: req.body, signal: req.signal, redirect: 'manual' });
    }
  }
  return nativeFetch(input, init);
}
globalThis.fetch = egressFetch;
