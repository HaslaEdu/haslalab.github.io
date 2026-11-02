import { WorkerEntrypoint } from 'cloudflare:workers';
import community from './index.js';
import { studioRoute, deleteCommunityAccount, sweepDeletedStudioUsers } from './studio-gateway.js';
import { studioResponses, studioImageEdit, purgeStudioReceipts } from './studio-provider.js';
import { ensureStudioSchema } from './studio-schema.js';

// Named service-binding RPC. No HTTP route exposes this credential-bearing interface.
export class StudioProvider extends WorkerEntrypoint {
  async responses(args) { return studioResponses(this.env,args); }
  async imageEdit(args) { return studioImageEdit(this.env,args); }
}
export default {
  fetch(request,env,ctx) {
    const path = new URL(request.url).pathname.replace(/\/+$/,'');
    if (path.startsWith('/api/studio/')) return studioRoute(request,env);
    if (path === '/api/me' && request.method === 'DELETE')
      return deleteCommunityAccount(request,env,ctx,(...args)=>community.fetch(...args));
    return community.fetch(request,env,ctx);
  },
  async scheduled(event,env,ctx) {
    if (community.scheduled) await community.scheduled(event,env,ctx);
    if (env.STUDIO_ENGINE) ctx.waitUntil(ensureStudioSchema(env.DB)
      .then(()=>sweepDeletedStudioUsers(env)).then(()=>purgeStudioReceipts(env)).catch(()=>{}));
  },
  async queue(batch,env,ctx) {
    if (typeof community.queue !== 'function') throw new Error('queue_handler_unavailable');
    return community.queue(batch,env,ctx);
  },
};
