import { WorkerEntrypoint } from 'cloudflare:workers';
import { useEgress } from './ai-egress.js';
import community from './index.js';
import { studioRoute, deleteCommunityAccount, sweepDeletedStudioUsers } from './studio-gateway.js';
import { studioResponses, studioImageEdit, purgeStudioReceipts } from './studio-provider.js';
import { ensureStudioSchema } from './studio-schema.js';

// Named service-binding RPC. No HTTP route exposes this credential-bearing interface.
export class StudioProvider extends WorkerEntrypoint {
  async responses(args) { useEgress(this.env); return studioResponses(this.env,args); }
  async imageEdit(args) { useEgress(this.env); return studioImageEdit(this.env,args); }
}
// Temporary server-to-server access for the two synthetic Hasla Nonsul samples.
const nonsulProbeDigest = '78ffb21cf9699f6be6f36afdef2a0c7200cbadd63f04582243476326517210e2';
const nonsulProbeExpires = Date.parse('2026-11-26T18:15:03.502997+00:00');
const nonsulProbeModels = new Set(['claude-sonnet-5-5', 'claude-opus-5-5']);
async function canRunNonsulProbe(token) {
  if (Date.now() >= nonsulProbeExpires || typeof token !== 'string' || !/^[A-Za-z0-9_-]{64}$/.test(token)) return false;
  const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(token));
  return Array.from(new Uint8Array(bytes), byte => byte.toString(16).padStart(2, '0')).join('') === nonsulProbeDigest;
}
async function nonsulClaudeReady(env, token) {
  return await canRunNonsulProbe(token) && !!(env.ANTHROPIC_API_KEY || env.CLAUDE_API_KEY);
}
async function nonsulClaudeGrade(env, token, {model, system, prompt, schema, effort, maxTokens} = {}) {
  if (!(await nonsulClaudeReady(env, token))) return {status: 404};
  if (!nonsulProbeModels.has(model) || typeof system !== 'string' || system.length > 16000 ||
      typeof prompt !== 'string' || prompt.length > 16000 || schema?.type !== 'object' ||
      JSON.stringify(schema).length > 16000 || maxTokens !== 24000 ||
      !['low', 'medium', 'high'].includes(effort)) return {status: 400};
  useEgress(env);
  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST', redirect: 'manual', signal: AbortSignal.timeout(150000),
    headers: {'content-type': 'application/json', 'anthropic-version': '2023-06-01',
      'x-api-key': env.ANTHROPIC_API_KEY || env.CLAUDE_API_KEY},
    body: JSON.stringify({model, system, max_tokens: maxTokens,
      messages: [{role: 'user', content: prompt}],
      output_config: {effort, format: {type: 'json_schema', schema}}}),
  });
  const body = await response.json().catch(() => null);
  return {
    status: response.status, usage: body?.usage || null, errorType: body?.error?.type || null,
    stopReason: body?.stop_reason || null,
    text: response.ok ? (body?.content || []).filter(block => block.type === 'text').map(block => block.text).join('') : '',
  };
}
// Named service-binding RPC for the HaslaEdu Worker (haslaedu-web src/account-sync.js): which of these account ids
// have been deleted, so a withdrawal made on haslalab.org also removes the member's Hasla Nonsul records. Only answers
// for ids it is given (no listing of accounts), and only deleted ones (deleted=1; suspended accounts are not deleted).
export class AccountEvents extends WorkerEntrypoint {
  async nonsulClaudeReady(token) { return nonsulClaudeReady(this.env, token); }
  async nonsulClaudeGrade(token, input) { return nonsulClaudeGrade(this.env, token, input); }
  async deletedAmong(ids) {
    const wanted = [...new Set((Array.isArray(ids) ? ids : []).filter(id => Number.isSafeInteger(id) && id > 0))].slice(0, 500);
    const out = [];
    for (let i = 0; i < wanted.length; i += 90) {
      const part = wanted.slice(i, i + 90);
      const rows = (await this.env.DB.prepare(`SELECT id FROM users WHERE deleted=1 AND id IN (${part.map(() => '?').join(',')})`).bind(...part).all()).results || [];
      for (const row of rows) out.push(Number(row.id));
    }
    return out;
  }
}
export default {
  fetch(request,env,ctx) {
    useEgress(env);
    const path = new URL(request.url).pathname.replace(/\/+$/,'');
    if (path.startsWith('/api/studio/')) return studioRoute(request,env);
    if (path === '/api/me' && request.method === 'DELETE')
      return deleteCommunityAccount(request,env,ctx,(...args)=>community.fetch(...args));
    return community.fetch(request,env,ctx);
  },
  async scheduled(event,env,ctx) {
    useEgress(env);
    if (community.scheduled) await community.scheduled(event,env,ctx);
    if (env.STUDIO_ENGINE) ctx.waitUntil(ensureStudioSchema(env.DB)
      .then(()=>sweepDeletedStudioUsers(env)).then(()=>purgeStudioReceipts(env)).catch(()=>{}));
  },
  async queue(batch,env,ctx) {
    useEgress(env);
    if (typeof community.queue !== 'function') throw new Error('queue_handler_unavailable');
    return community.queue(batch,env,ctx);
  },
};
