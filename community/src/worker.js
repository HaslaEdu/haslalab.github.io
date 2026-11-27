import { WorkerEntrypoint } from 'cloudflare:workers';
import { useEgress } from './ai-egress.js';
import community from './index.js';
import { studioRoute, deleteCommunityAccount, sweepDeletedStudioUsers } from './studio-gateway.js';
import { studioResponses, studioImageEdit, purgeStudioReceipts } from './studio-provider.js';
import { ensureStudioSchema } from './studio-schema.js';
import { hasNonsulOpus, gradeNonsulWithOpus } from './nonsul-opus.js';

// Named service-binding RPC. No HTTP route exposes this credential-bearing interface.
export class StudioProvider extends WorkerEntrypoint {
  async responses(args) { useEgress(this.env); return studioResponses(this.env,args); }
  async imageEdit(args) { useEgress(this.env); return studioImageEdit(this.env,args); }
}
// Named service-binding RPC for the HaslaEdu Worker (haslaedu-web src/account-sync.js): which of these account ids
// have been deleted, so a withdrawal made on haslalab.org also removes the member's Hasla Nonsul records. Only answers
// for ids it is given (no listing of accounts), and only deleted ones (deleted=1; suspended accounts are not deleted).
export class AccountEvents extends WorkerEntrypoint {
  nonsulOpusReady() { return hasNonsulOpus(this.env); }
  async nonsulOpusGrade(input) {
    useEgress(this.env);
    return gradeNonsulWithOpus(this.env, input);
  }
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
