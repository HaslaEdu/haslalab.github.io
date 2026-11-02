// This module holds no prompts. Only the private engine can invoke the named RPC entrypoint.
// Provider credentials remain in the existing community Worker's secret bindings.
const TEXT_MODELS = new Set(['gpt-6.1-sol','gpt-6.1-terra','gpt-6-luna']);
const IMAGE_MODELS = new Set(['gpt-image-2.5-sunburst','gpt-image-2.5-flare']);
const UUID = /^[a-f0-9]{8}-[a-f0-9]{4}-[1-5][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i;
const STAGE = /^[a-zA-Z0-9_.:-]{1,90}$/;
const enc = new TextEncoder();
const now = () => Math.floor(Date.now()/1000);
export class ProviderError extends Error { constructor(code) { super(code); this.name = 'ProviderError'; this.code = code; } }
const reject = code => { throw new ProviderError(code); };
async function digest(value) { return [...new Uint8Array(await crypto.subtle.digest('SHA-256',enc.encode(value)))].map(b=>b.toString(16).padStart(2,'0')).join(''); }
function object(value) { return value && typeof value === 'object' && !Array.isArray(value); }
function permitModel(model,kind,env) {
  const configured = String(kind === 'responses' ? env.STUDIO_TEXT_MODELS || '' : env.STUDIO_IMAGE_MODELS || '').split(',').map(x=>x.trim()).filter(Boolean);
  return (configured.length ? new Set(configured) : kind === 'responses' ? TEXT_MODELS : IMAGE_MODELS).has(model);
}
function checkImages(value) {
  if (!value || typeof value !== 'object') return;
  if (Array.isArray(value)) { for (const item of value) checkImages(item); return; }
  if (value.type === 'input_image') {
    if (typeof value.image_url !== 'string' || !/^data:image\/(png|jpeg|webp);base64,[A-Za-z0-9+/]+=*$/.test(value.image_url)) reject('invalid_provider_request');
    if (value.image_url.length > 6*1024*1024) reject('invalid_provider_request');
  }
  for (const item of Object.values(value)) if (item && typeof item === 'object') checkImages(item);
}
export function responsePayload(request,env,userId) {
  if (!object(request) || !permitModel(request.model,'responses',env) || !Array.isArray(request.input) || request.input.length > 12)
    reject('invalid_provider_request');
  if (request.tools || request.tool_choice || request.previous_response_id || request.background || request.stream)
    reject('invalid_provider_request');
  if (request.text?.format?.type !== 'json_schema' || request.text.format.strict !== true || !object(request.text.format.schema))
    reject('invalid_provider_request');
  checkImages(request.input);
  const effort = request.reasoning?.effort || 'medium';
  if (!['low','medium','high','xhigh','max'].includes(effort)) reject('invalid_provider_request');
  const payload = {model:request.model,input:request.input,text:request.text,reasoning:{effort},
    max_output_tokens:Math.max(512,Math.min(16384,Number(request.max_output_tokens)||8192)),store:false,
    ...(typeof request.instructions === 'string' ? {instructions:request.instructions} : {}),
    metadata:request.metadata || {}};
  if (JSON.stringify(payload).length > 9*1024*1024) reject('invalid_provider_request');
  return payload;
}
export function editPayload(args,env) {
  const model = args.model || 'gpt-image-2.5-sunburst';
  if (!permitModel(model,'image_edit',env) || typeof args.prompt !== 'string' || !args.prompt.trim() || args.prompt.length > 20000 ||
      !object(args.image) || !['image/png','image/jpeg','image/webp'].includes(args.image.mime) ||
      typeof args.image.base64 !== 'string' || !/^[A-Za-z0-9+/]+=*$/.test(args.image.base64) || args.image.base64.length > 6*1024*1024)
    reject('invalid_provider_request');
  // GPT Image 2.x does not use the older input_fidelity parameter.
  return {model,images:[{image_url:`data:${args.image.mime};base64,${args.image.base64}`}],prompt:args.prompt,
    size:'auto',quality:'high',background:'opaque',output_format:'png',n:1};
}
async function authorize(env,args,callKey,kind) {
  const userId = Number(args.userId);
  if (!Number.isSafeInteger(userId) || userId < 1 || !UUID.test(args.jobId || '') || !STAGE.test(callKey)) reject('invalid_provider_request');
  if (!env.OPENAI_API_KEY) reject('provider_unavailable');
  const row = await env.DB.prepare(`SELECT j.* FROM studio_jobs j JOIN users u ON u.id=j.user_id
    WHERE j.id=? AND j.user_id=? AND u.deleted=0`).bind(args.jobId,userId).first();
  if (!row || row.expires_at <= now() || !['queued','running'].includes(row.status)) reject('job_inactive');
  const old = await env.DB.prepare('SELECT * FROM studio_provider_calls WHERE job_id=? AND call_key=?').bind(args.jobId,callKey).first();
  if (old) {
    if (old.kind !== kind) reject('invalid_provider_request');
    if (old.status !== 'completed') reject(old.status === 'running' ? 'provider_request_pending' : 'provider_request_failed');
    if (old.result_json && old.result_json !== 'chunks') return {cached:JSON.parse(old.result_json)};
    const rows = (await env.DB.prepare('SELECT value FROM studio_provider_chunks WHERE job_id=? AND call_key=? ORDER BY part').bind(args.jobId,callKey).all()).results;
    if (!rows?.length) reject('provider_result_expired');
    return {cached:JSON.parse(rows.map(r=>r.value).join(''))};
  }
  const configuredLimit = Number(env.STUDIO_PROVIDER_CALL_LIMIT), limit = Number.isInteger(configuredLimit) && configuredLimit > 0 ? Math.min(configuredLimit,12) : 10;
  const timestamp = now();
  const reserved = await env.DB.prepare(`INSERT OR IGNORE INTO studio_provider_calls(job_id,call_key,kind,status,created_at,updated_at)
    SELECT ?,?,?,'running',?,? WHERE
    EXISTS (SELECT 1 FROM studio_jobs j JOIN users u ON u.id=j.user_id
      WHERE j.id=? AND j.user_id=? AND u.deleted=0 AND j.status IN ('queued','running') AND j.expires_at>?) AND
    (SELECT COUNT(*) FROM studio_provider_calls WHERE job_id=?)<? AND
    (?!='image_edit' OR (SELECT COUNT(*) FROM studio_provider_calls WHERE job_id=? AND kind='image_edit')<1)`)
    .bind(args.jobId,callKey,kind,timestamp,timestamp,args.jobId,userId,timestamp,args.jobId,limit,kind,args.jobId).run();
  if (!reserved.meta?.changes) reject('provider_call_limit');
  return {cached:null};
}
function compact(body,kind) {
  if (kind === 'image_edit') {
    const image = body.data?.[0]?.b64_json;
    if (typeof image !== 'string' || image.length > 24*1024*1024 || !/^[A-Za-z0-9+/]+=*$/.test(image)) reject('invalid_provider_response');
    return {created:body.created,data:[{b64_json:image}],output_format:'png',size:body.size,usage:body.usage};
  }
  if (!Array.isArray(body.output) || body.status === 'incomplete' || body.error) reject('invalid_provider_response');
  // Return only response data, never a provider echo of input/instructions.
  return {id:body.id,status:body.status,output:body.output,
    ...(typeof body.output_text === 'string' ? {output_text:body.output_text} : {}),usage:body.usage};
}
async function cacheResult(env,args,key,result) {
  const serialized = JSON.stringify(result), chunkLength = 48000;
  if (serialized.length > 25*1024*1024) reject('invalid_provider_response');
  // Authorization before the network call is insufficient: an account/job can
  // be deleted while a paid response is in flight. Make each persistence write
  // conditional on the live owner/job and original running reservation in SQL.
  const active = `EXISTS (SELECT 1 FROM studio_jobs j JOIN users u ON u.id=j.user_id
    JOIN studio_provider_calls c ON c.job_id=j.id
    WHERE j.id=? AND j.user_id=? AND u.deleted=0 AND j.status IN ('queued','running')
      AND j.expires_at>? AND c.call_key=? AND c.status='running')`;
  const activeArgs = () => [args.jobId,Number(args.userId),now(),key];
  if (serialized.length <= chunkLength) {
    const saved = await env.DB.prepare(`UPDATE studio_provider_calls SET status='completed',result_json=?,updated_at=? WHERE job_id=? AND call_key=? AND ${active}`)
      .bind(serialized,now(),args.jobId,key,...activeArgs()).run();
    if (!saved.meta?.changes) reject('job_inactive');
    return;
  }
  const statements = [];
  for (let i=0;i<serialized.length;i+=chunkLength) statements.push(env.DB.prepare(`INSERT OR REPLACE INTO studio_provider_chunks(job_id,call_key,part,value) SELECT ?,?,?,? WHERE ${active}`)
    .bind(args.jobId,key,i/chunkLength,serialized.slice(i,i+chunkLength),...activeArgs()));
  for (let i=0;i<statements.length;i+=50) await env.DB.batch(statements.slice(i,i+50));
  const saved = await env.DB.prepare(`UPDATE studio_provider_calls SET status='completed',result_json='chunks',updated_at=? WHERE job_id=? AND call_key=? AND ${active}`)
    .bind(now(),args.jobId,key,...activeArgs()).run();
  if (!saved.meta?.changes) reject('job_inactive');
}
async function invoke(env,args,key,kind,payload) {
  const authorization = await authorize(env,args,key,kind); if (authorization.cached) return authorization.cached;
  try {
    payload.safety_identifier = await digest(`studio-user:${args.userId}`);
    const response = await fetch(`https://api.openai.com/v1/${kind === 'responses' ? 'responses' : 'images/edits'}`,{
      method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${env.OPENAI_API_KEY}`,
        'Idempotency-Key':`haslalab:${args.jobId}:${key}`},body:JSON.stringify(payload),
      signal:AbortSignal.timeout(kind === 'image_edit' ? 180000 : 150000)});
    if (!response.ok) {
      // Never include provider bodies, headers, prompts or credentials in exceptions.
      if (response.status === 401 || response.status === 403) reject('provider_access_denied');
      if (response.status === 429) reject('provider_capacity_reached');
      if (response.status === 400 || response.status === 404) reject('provider_model_unavailable');
      reject('provider_unavailable');
    }
    const body = await response.json(), result = compact(body,kind);
    await cacheResult(env,args,key,result); return result;
  } catch (error) {
    await env.DB.prepare("UPDATE studio_provider_calls SET status='failed',updated_at=? WHERE job_id=? AND call_key=? AND status='running'")
      .bind(now(),args.jobId,key).run().catch(()=>{});
    throw error instanceof ProviderError ? error : new ProviderError('provider_unavailable');
  }
}
export async function studioResponses(env,args) {
  if (!object(args) || !object(args.request)) reject('invalid_provider_request');
  const metadata = args.request.metadata || {};
  if (metadata.studio_job_id !== args.jobId || !STAGE.test(metadata.studio_stage || '') || !/^\d{1,2}$/.test(String(metadata.studio_attempt ?? 0)))
    reject('invalid_provider_request');
  const key = `text:${metadata.studio_stage}:${metadata.studio_attempt ?? 0}`;
  return invoke(env,args,key,'responses',responsePayload(args.request,env,args.userId));
}
export async function studioImageEdit(env,args) {
  if (!object(args) || (args.requestId && args.requestId !== `${args.jobId}:restore`)) reject('invalid_provider_request');
  return invoke(env,args,'image:restore','image_edit',editPayload(args,env));
}
export async function purgeStudioReceipts(env) {
  // Receipts can include generated images; remove them with the 24-hour job retention.
  await env.DB.prepare('DELETE FROM studio_provider_chunks WHERE job_id IN (SELECT id FROM studio_jobs WHERE expires_at<=? OR status=?)')
    .bind(now(),'deleted').run();
  await env.DB.prepare('DELETE FROM studio_provider_calls WHERE job_id IN (SELECT id FROM studio_jobs WHERE expires_at<=? OR status=?)')
    .bind(now(),'deleted').run();
  await env.DB.prepare("UPDATE studio_jobs SET status='expired' WHERE expires_at<=? AND status NOT IN ('expired','deleted')").bind(now()).run();
  await env.DB.prepare('DELETE FROM studio_jobs WHERE expires_at<?').bind(now()-7*86400).run();
}
