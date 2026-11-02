// Public authentication and transport only. Prompts and AI orchestration are deployed separately.
import { ensureStudioSchema } from './studio-schema.js';
export const STUDIO_LIMITS = Object.freeze({ imageBytes: 4 * 1024 * 1024, bodyBytes: 6 * 1024 * 1024,
  maxPixels: 16_000_000, maxCount: 3, instructionChars: 1200, retentionSeconds: 86400 });
const MODES = new Set(['digitize', 'generate', 'restore']);
const SUBJECTS = new Set(['math', 'physics', 'chemistry', 'biology', 'astronomy', 'informatics']);
const STATUSES = new Set(['queued', 'running', 'completed', 'needs_review', 'failed', 'cancelled', 'expired']);
const UUID = /^[a-f0-9]{8}-[a-f0-9]{4}-[1-5][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i;
const ASSET_ID = /^[a-zA-Z0-9_-]{1,80}$/;
const encoder = new TextEncoder();
const seconds = () => Math.floor(Date.now() / 1000);
export class StudioError extends Error { constructor(status, code) { super(code); this.status = status; this.code = code; } }
export const fail = (status, code) => { throw new StudioError(status, code); };
const messages = {
  login_required: 'HaslaLab 계정으로 로그인해 주세요.', forbidden_origin: '허용되지 않은 연결입니다.',
  unavailable: '제작실 연결을 준비하고 있습니다.', admin_only: '현재 관리자 계정에서 시험 운영 중입니다.',
  bad_input: '입력 항목을 확인해 주세요.', image_required: '문제 사진을 올려 주세요.',
  bad_image: 'PNG, JPEG 또는 WebP 사진을 사용해 주세요.', image_too_large: '사진은 4MB 이하로 올려 주세요.',
  image_dimensions: '사진의 크기가 지원 범위를 벗어납니다.', body_too_large: '업로드 용량이 너무 큽니다.',
  quota_reached: '오늘의 제작 한도에 도달했거나 진행 중인 작업이 있습니다. 잠시 후 확인해 주세요.',
  request_conflict: '요청 정보가 변경되었습니다. 새 작업으로 다시 시작해 주세요.',
  not_found: '작업을 찾을 수 없습니다.', expired: '보관 기간이 끝난 작업입니다.',
  processing_failed: '작업을 완료하지 못했습니다. 원본과 결과를 확인한 뒤 다시 시도해 주세요.',
};
export function publicError(code) { const known = Object.hasOwn(messages,code) ? code : 'processing_failed';
  return { code:known, message:messages[known] }; }
function securityHeaders(cors = {}) { return { ...cors, 'Cache-Control': 'private, no-store',
  'X-Content-Type-Options': 'nosniff', 'Content-Security-Policy': "default-src 'none'; frame-ancestors 'none'",
  'Referrer-Policy': 'no-referrer' }; }
function json(data, status, cors) { return new Response(JSON.stringify(data), { status, headers: {
  ...securityHeaders(cors), 'Content-Type': 'application/json; charset=utf-8' } }); }
function corsFor(request, env) {
  const origin = request.headers.get('Origin');
  const allowed = String(env.ALLOWED_ORIGINS || '').split(',').map(x => x.trim()).filter(Boolean);
  if (origin && !allowed.includes(origin)) fail(403, 'forbidden_origin');
  return { ...(origin ? { 'Access-Control-Allow-Origin': origin } : {}), Vary: 'Origin',
    'Access-Control-Allow-Methods': 'GET,POST,DELETE,OPTIONS',
    'Access-Control-Allow-Headers': 'Authorization,Content-Type,Idempotency-Key',
    'Access-Control-Max-Age': '600' };
}
export async function hash(value) {
  const bytes = typeof value === 'string' ? encoder.encode(value) : value;
  return [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(x => x.toString(16).padStart(2, '0')).join('');
}
function base64url(bytes) { let value = ''; for (const byte of bytes) value += String.fromCharCode(byte);
  return btoa(value).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, ''); }
function toBase64(bytes) { let out = ''; for (let i = 0; i < bytes.length; i += 24576)
  out += btoa(String.fromCharCode(...bytes.subarray(i, i + 24576))); return out; }
export async function studioUser(request, env) {
  const token = /^Bearer\s+([A-Za-z0-9_-]{20,})$/.exec(request.headers.get('Authorization') || '');
  if (!token) fail(401, 'login_required');
  const digest = base64url(new Uint8Array(await crypto.subtle.digest('SHA-256', encoder.encode(token[1]))));
  const user = await env.DB.prepare(`SELECT u.id,u.role FROM sessions s JOIN users u ON u.id=s.user_id
    WHERE s.token_hash=? AND s.expires_at>? AND u.deleted=0`).bind(digest, seconds()).first();
  if (!user) fail(401, 'login_required');
  if (env.STUDIO_ACCESS === 'admin' && user.role !== 'admin') fail(403, 'admin_only');
  return user;
}
function intSetting(value, fallback, ceiling) { const number = Number(value);
  return Number.isInteger(number) && number > 0 ? Math.min(number, ceiling) : fallback; }
export async function readLimited(request, maximum = STUDIO_LIMITS.bodyBytes) {
  const declared = Number(request.headers.get('Content-Length') || 0);
  if (declared > maximum) fail(413, 'body_too_large');
  if (!request.body) return new Uint8Array();
  const reader = request.body.getReader(), chunks = []; let length = 0;
  try { while (true) { const { value, done } = await reader.read(); if (done) break;
    length += value.byteLength; if (length > maximum) { await reader.cancel(); fail(413, 'body_too_large'); } chunks.push(value); }
  } finally { reader.releaseLock(); }
  const bytes = new Uint8Array(length); let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; } return bytes;
}
export function inspectImage(bytes, declaredMime) {
  let mime, width, height; const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  if (bytes.length >= 33 && [137,80,78,71,13,10,26,10].every((v,i) => bytes[i] === v) &&
      String.fromCharCode(...bytes.subarray(12,16)) === 'IHDR') {
    mime = 'image/png'; width = view.getUint32(16); height = view.getUint32(20);
  } else if (bytes.length >= 12 && bytes[0] === 255 && bytes[1] === 216) {
    mime = 'image/jpeg'; let p = 2;
    while (p + 9 < bytes.length) {
      if (bytes[p++] !== 255) continue; while (p < bytes.length && bytes[p] === 255) p++;
      const marker = bytes[p++]; if (marker === 217 || marker === 218) break;
      if (marker === 216 || marker === 1 || (marker >= 208 && marker <= 215)) continue;
      if (p + 2 > bytes.length) break; const size = view.getUint16(p);
      if (size < 2 || p + size > bytes.length) break;
      if ([192,193,194,195,197,198,199,201,202,203,205,206,207].includes(marker)) {
        height = view.getUint16(p + 3); width = view.getUint16(p + 5); break;
      } p += size;
    }
  } else if (bytes.length >= 30 && String.fromCharCode(...bytes.subarray(0,4)) === 'RIFF' &&
      String.fromCharCode(...bytes.subarray(8,12)) === 'WEBP') {
    mime = 'image/webp'; const type = String.fromCharCode(...bytes.subarray(12,16));
    if (type === 'VP8X') { width = 1 + bytes[24] + (bytes[25] << 8) + (bytes[26] << 16);
      height = 1 + bytes[27] + (bytes[28] << 8) + (bytes[29] << 16); }
    else if (type === 'VP8L' && bytes[20] === 47) { width = 1 + (view.getUint32(21, true) & 0x3fff);
      height = 1 + ((view.getUint32(21, true) >>> 14) & 0x3fff); }
    else if (type === 'VP8 ' && bytes.length >= 30 && bytes[23] === 157 && bytes[24] === 1 && bytes[25] === 42) {
      width = view.getUint16(26, true) & 0x3fff; height = view.getUint16(28, true) & 0x3fff;
    }
  }
  if (!mime || (declaredMime && declaredMime !== mime)) fail(400, 'bad_image');
  if (!width || !height || width < 16 || height < 16 || width * height > STUDIO_LIMITS.maxPixels || Math.max(width,height) > 8192)
    fail(400, 'image_dimensions');
  return { mime, width, height };
}
function field(form, name, fallback = '') { const value = form.get(name); return value == null ? fallback : typeof value === 'string' ? value.trim() : fail(400, 'bad_input'); }
export async function studioInput(request) {
  if (!(request.headers.get('Content-Type') || '').startsWith('multipart/form-data')) fail(415, 'bad_input');
  const bytes = await readLimited(request);
  let form; try { form = await new Response(bytes, { headers: { 'Content-Type': request.headers.get('Content-Type') } }).formData(); }
  catch { fail(400, 'bad_input'); }
  const mode = field(form,'mode'), subject = field(form,'subject','math'), language = field(form,'language','ko');
  const difficulty = field(form,'difficulty','similar'), instruction = field(form,'instruction');
  const count = Number(field(form,'count','1'));
  if (!MODES.has(mode) || !SUBJECTS.has(subject) || !['ko','en'].includes(language) ||
      !['similar','easier','harder'].includes(difficulty) || !Number.isInteger(count) || count < 1 || count > STUDIO_LIMITS.maxCount ||
      instruction.length > STUDIO_LIMITS.instructionChars) fail(400,'bad_input');
  const requestKey = request.headers.get('Idempotency-Key') || field(form,'requestId') || crypto.randomUUID();
  if (!UUID.test(requestKey)) fail(400,'bad_input');
  const input = { mode, subject, language, difficulty, count: mode === 'generate' ? count : 1, instruction };
  const image = form.get('image');
  if (image && typeof image !== 'string' && image.size) {
    if (image.size > STUDIO_LIMITS.imageBytes) fail(413,'image_too_large');
    const imageBytes = new Uint8Array(await image.arrayBuffer()), details = inspectImage(imageBytes, image.type);
    input.image = { ...details, base64: toBase64(imageBytes) };
  }
  if (mode !== 'generate' && !input.image) fail(400,'image_required');
  if (mode === 'generate' && !input.image && instruction.length < 5) fail(400,'bad_input');
  return { input, requestKey, fingerprint: await hash(JSON.stringify(input)) };
}
function string(value, max = 30000) { return typeof value === 'string' ? value.slice(0,max) : ''; }
function safeResult(result) {
  if (!result || typeof result !== 'object') return undefined;
  return { title: string(result.title,200), subject: string(result.subject,30),
    problems: (Array.isArray(result.problems) ? result.problems : []).slice(0,3).map((p,i) => ({
      id: string(p.id,80) || String(i+1), number: string(String(p.number ?? i+1),20), statement: string(p.statement),
      choices: (Array.isArray(p.choices) ? p.choices : []).slice(0,10).map(x => string(x,5000)),
      answer: string(p.answer,10000), explanation: string(p.explanation,40000),
      figures: (Array.isArray(p.figures) ? p.figures : []).slice(0,6).filter(f => ASSET_ID.test(f.assetId)).map(f => ({
        id: string(f.id,80), kind: string(f.kind,30), assetId: f.assetId, caption: string(f.caption,1000) })),
      warnings: (Array.isArray(p.warnings) ? p.warnings : []).slice(0,20).map(x => string(x,1000)),
    })), warnings: (Array.isArray(result.warnings) ? result.warnings : []).slice(0,20).map(x => string(x,1000)),
    review: { status: string(result.review?.status,40), checks: Array.isArray(result.review?.checks) ?
      result.review.checks.slice(0,20).map(c => typeof c === 'string' ? string(c,1000) : {
        name: string(c.name || c.check || c.label || c.problemId,120), passed: c.passed === true || c.pass === true,
        detail: string(c.detail || c.reason || c.message || (Array.isArray(c.issues) ? c.issues.filter(x=>typeof x==='string').join('\n') : ''),2000) }) : [] },
  };
}
export function publicJob(job, fallback = {}) {
  return { id: fallback.id || job.id, mode: MODES.has(job.mode) ? job.mode : fallback.mode,
    subject: SUBJECTS.has(job.subject) ? job.subject : fallback.subject,
    status: STATUSES.has(job.status) ? job.status : 'running', stage: string(job.stage,100),
    progress: Math.max(0,Math.min(100,Number(job.progress)||0)),
    createdAt: job.createdAt || fallback.created_at, updatedAt: job.updatedAt || fallback.updated_at,
    expiresAt: fallback.expires_at, originalAssetId: job.originalAssetId === 'original' ? 'original' : null,
    ...(job.options ? {options:{
      difficulty:['similar','easier','harder'].includes(job.options.difficulty)?job.options.difficulty:'similar',
      language:['ko','en'].includes(job.options.language)?job.options.language:'ko',
      count:Math.max(1,Math.min(3,Number(job.options.count)||1)),instruction:string(job.options.instruction,1200),
    }} : {}),
    ...(job.result ? { result: safeResult(job.result) } : {}),
    ...(job.error ? { error: publicError(job.error.code || 'processing_failed') } : {}) };
}
async function engine(env, path, userId, init = {}) {
  const headers = new Headers(init.headers); headers.set('X-Studio-User-Id',String(userId));
  const url = new URL('https://studio.internal' + path); url.searchParams.set('userId',String(userId));
  return env.STUDIO_ENGINE.fetch(new Request(url, { ...init, headers }));
}
export async function cleanupStudioUser(env, userId) {
  if (!Number.isSafeInteger(Number(userId)) || Number(userId) < 1) return;
  await ensureStudioSchema(env.DB);
  const owner = await env.DB.prepare('SELECT deleted FROM users WHERE id=?').bind(userId).first();
  if (!owner?.deleted) return; // Account deletion only; no Studio access/admin gate.
  // Disable further calls and erase provider replay data before network cleanup.
  // Failed DO deletions remain indexed for the next scheduled retry.
  await env.DB.batch([
    env.DB.prepare("UPDATE studio_jobs SET status='deleted',updated_at=? WHERE user_id=?").bind(seconds(),userId),
    env.DB.prepare('DELETE FROM studio_provider_chunks WHERE job_id IN (SELECT id FROM studio_jobs WHERE user_id=?)').bind(userId),
    env.DB.prepare('DELETE FROM studio_provider_calls WHERE job_id IN (SELECT id FROM studio_jobs WHERE user_id=?)').bind(userId),
  ]);
  if (!env.STUDIO_ENGINE) return;
  const rows = (await env.DB.prepare('SELECT id FROM studio_jobs WHERE user_id=? ORDER BY created_at LIMIT 50').bind(userId).all()).results;
  for (let offset=0; offset<rows.length; offset+=4) await Promise.all(rows.slice(offset,offset+4).map(async row => {
    try {
      const response = await engine(env,`/internal/jobs/${row.id}`,userId,{method:'DELETE'});
      if (response.ok || response.status === 404 || response.status === 410)
        await env.DB.prepare("DELETE FROM studio_jobs WHERE id=? AND user_id=? AND status='deleted'").bind(row.id,userId).run();
    } catch { /* Keep the id for a bounded scheduled retry; never log source/provider data. */ }
  }));
}
export async function sweepDeletedStudioUsers(env) {
  await ensureStudioSchema(env.DB);
  const rows = (await env.DB.prepare('SELECT DISTINCT j.user_id FROM studio_jobs j JOIN users u ON u.id=j.user_id WHERE u.deleted=1 LIMIT 20').all()).results;
  for (const row of rows) await cleanupStudioUser(env,row.user_id);
}
export async function deleteCommunityAccount(request,env,ctx,communityFetch) {
  // Reuse the existing account API authentication, including ordinary users who
  // cannot currently enter the admin-only Studio preview. Do not consume DELETE.
  let owner;
  try {
    const headers = new Headers();
    for (const key of ['Authorization','Origin']) if (request.headers.has(key)) headers.set(key,request.headers.get(key));
    const url = new URL(request.url); url.pathname='/api/me'; url.search='';
    const me = await communityFetch(new Request(url,{method:'GET',headers}),env,ctx);
    if (me.ok) owner = (await me.json()).user?.id;
  } catch { /* Let the original account handler determine the response. */ }
  const response = await communityFetch(request,env,ctx);
  if (response.ok && owner) {
    const body = await response.clone().json().catch(()=>null);
    if (body?.ok === true) await cleanupStudioUser(env,owner).catch(()=>{});
  }
  return response;
}
async function rowFor(env,userId,id) {
  const row = await env.DB.prepare('SELECT * FROM studio_jobs WHERE id=? AND user_id=?').bind(id,userId).first();
  if (!row) fail(404,'not_found'); if (row.status === 'deleted') fail(404,'not_found');
  if (row.expires_at <= seconds()) fail(410,'expired'); return row;
}
async function refresh(env,row) {
  const response = await engine(env,`/internal/jobs/${row.id}`,row.user_id);
  if (!response.ok) { if (response.status === 404) fail(404,'not_found'); fail(503,'processing_failed'); }
  const body = await response.json(), job = publicJob(body.job || body,row);
  await env.DB.prepare('UPDATE studio_jobs SET status=?,updated_at=? WHERE id=? AND user_id=?')
    .bind(job.status,seconds(),row.id,row.user_id).run(); return job;
}
export async function studioRoute(request,env) {
  let cors = {};
  try {
    cors = corsFor(request,env); if (request.method === 'OPTIONS') return new Response(null,{ status:204,headers:securityHeaders(cors) });
    const path = new URL(request.url).pathname.replace(/\/+$/,''), method = request.method;
    const available = !!(env.STUDIO_ENGINE && env.OPENAI_API_KEY) && env.STUDIO_ENABLED !== 'false';
    if (path === '/api/studio/capabilities' && method === 'GET') return json({ available, modes:[...MODES], subjects:[...SUBJECTS],
      maxImageBytes:STUDIO_LIMITS.imageBytes,maxCount:3,retentionHours:24,
      dailyLimit:intSetting(env.STUDIO_DAILY_LIMIT,3,100), reason:available ? null : 'unavailable' },200,cors);
    const user = await studioUser(request,env);
    if (!env.STUDIO_ENGINE) fail(503,'unavailable');
    await ensureStudioSchema(env.DB);
    if (path === '/api/studio/jobs' && method === 'GET') {
      const rows = (await env.DB.prepare("SELECT id,mode,subject,status,created_at,updated_at,expires_at FROM studio_jobs WHERE user_id=? AND status!='deleted' AND expires_at>? ORDER BY created_at DESC LIMIT 30")
        .bind(user.id,seconds()).all()).results;
      return json({jobs:rows.map(r => publicJob(r,r))},200,cors);
    }
    if (path === '/api/studio/jobs' && method === 'POST') {
      if (!available) fail(503,'unavailable');
      const {input,requestKey,fingerprint} = await studioInput(request);
      const previous = await env.DB.prepare('SELECT * FROM studio_jobs WHERE user_id=? AND request_key=?').bind(user.id,requestKey).first();
      if (previous) { if (previous.fingerprint !== fingerprint) fail(409,'request_conflict');
        if (previous.expires_at <= seconds() || previous.status === 'deleted') fail(410,'expired');
        return json({job:await refresh(env,previous),reused:true},200,cors); }
      const active = (await env.DB.prepare("SELECT * FROM studio_jobs WHERE user_id=? AND status IN ('queued','running') AND expires_at>?").bind(user.id,seconds()).all()).results;
      await Promise.all(active.map(row => refresh(env,row).catch(()=>{})));
      const now = seconds(), day = Math.floor((now+32400)/86400)*86400-32400, id = crypto.randomUUID();
      const perUser = intSetting(env.STUDIO_DAILY_LIMIT,3,100), globalLimit = intSetting(env.STUDIO_GLOBAL_DAILY_LIMIT,30,500);
      const result = await env.DB.prepare(`INSERT OR IGNORE INTO studio_jobs(id,user_id,request_key,fingerprint,mode,subject,status,created_at,updated_at,expires_at)
        SELECT ?,?,?,?,?,?,'queued',?,?,? WHERE
        EXISTS (SELECT 1 FROM users WHERE id=? AND deleted=0) AND
        (SELECT COUNT(*) FROM studio_jobs WHERE user_id=? AND created_at>=?)<? AND
        (SELECT COUNT(*) FROM studio_jobs WHERE created_at>=?)<? AND
        (SELECT COUNT(*) FROM studio_jobs WHERE user_id=? AND status IN ('queued','running') AND expires_at>?)<2`)
        .bind(id,user.id,requestKey,fingerprint,input.mode,input.subject,now,now,now+STUDIO_LIMITS.retentionSeconds,
          user.id,user.id,day,perUser,day,globalLimit,user.id,now).run();
      if (!result.meta?.changes) {
        const reused = await env.DB.prepare('SELECT * FROM studio_jobs WHERE user_id=? AND request_key=?').bind(user.id,requestKey).first();
        if (reused && reused.fingerprint === fingerprint) return json({job:await refresh(env,reused),reused:true},200,cors);
        fail(429,'quota_reached');
      }
      const row = await rowFor(env,user.id,id);
      try {
        const response = await engine(env,`/internal/jobs/${id}`,user.id,{method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({...input,userId:String(user.id)})});
        if (!response.ok) fail(503,'processing_failed');
        const body = await response.json(); return json({job:publicJob(body.job || body,row)},202,cors);
      } catch {
        await env.DB.prepare("UPDATE studio_jobs SET status='failed',updated_at=? WHERE id=?").bind(seconds(),id).run();
        fail(503,'processing_failed');
      }
    }
    const match = /^\/api\/studio\/jobs\/([^/]+)(?:\/(cancel|assets)(?:\/([^/]+))?)?$/.exec(path);
    if (!match || !UUID.test(match[1])) fail(404,'not_found');
    const row = await rowFor(env,user.id,match[1]);
    if (!match[2] && method === 'GET') return json({job:await refresh(env,row)},200,cors);
    if (!match[2] && method === 'DELETE') {
      const response = await engine(env,`/internal/jobs/${row.id}`,user.id,{method:'DELETE'});
      if (!response.ok && response.status !== 404) fail(503,'processing_failed');
      await env.DB.prepare("UPDATE studio_jobs SET status='deleted',updated_at=? WHERE id=? AND user_id=?").bind(seconds(),row.id,user.id).run();
      await env.DB.prepare('DELETE FROM studio_provider_calls WHERE job_id=?').bind(row.id).run();
      return json({ok:true},200,cors);
    }
    if (match[2] === 'cancel' && !match[3] && method === 'POST') {
      const response = await engine(env,`/internal/jobs/${row.id}/cancel`,user.id,{method:'POST'});
      if (!response.ok) fail(503,'processing_failed'); const body = await response.json();
      const job = publicJob(body.job || body,row);
      await env.DB.prepare('UPDATE studio_jobs SET status=?,updated_at=? WHERE id=? AND user_id=?').bind(job.status,seconds(),row.id,user.id).run();
      return json({job},200,cors);
    }
    if (match[2] === 'assets' && ASSET_ID.test(match[3] || '') && method === 'GET') {
      const response = await engine(env,`/internal/jobs/${row.id}/assets/${match[3]}`,user.id);
      if (!response.ok) fail(response.status === 404 ? 404 : 503,response.status === 404 ? 'not_found' : 'processing_failed');
      const mime = (response.headers.get('Content-Type') || '').split(';')[0];
      if (!['image/png','image/jpeg','image/webp','image/svg+xml'].includes(mime)) fail(503,'processing_failed');
      return new Response(response.body,{headers:{...securityHeaders(cors),'Content-Type':mime,
        'Content-Security-Policy':"default-src 'none'; img-src data:; frame-ancestors 'none'",
        'Content-Disposition':`inline; filename="${match[3]}.${mime === 'image/svg+xml' ? 'svg' : mime.split('/')[1]}"`}});
    }
    fail(405,'not_found');
  } catch (error) { const known = error instanceof StudioError;
    return json({error:publicError(known ? error.code : 'processing_failed')},known ? error.status : 503,cors); }
}
