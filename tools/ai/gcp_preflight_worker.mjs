// Standalone, expiring, authenticated read-only preflight. No production imports/bindings.
// Compute scopes: https://docs.cloud.google.com/compute/docs/reference/rest/v1/regions/get
// Quotas: https://docs.cloud.google.com/service-usage/docs/reference/rest/v1beta1/services.consumerQuotaMetrics/list
// GCS scope: https://docs.cloud.google.com/storage/docs/oauth-scopes

export const PROJECT = 'project-hasla';
export const BUCKET = 'hasla-training';
export const REGIONS = Object.freeze(['us-central1', 'us-east4', 'asia-northeast3']);
export const SCOPES = Object.freeze([
  // Vertex requires this OAuth scope even for GET. All resource operations in
  // this expiring handler remain fixed reads and one IAM permission test.
  'https://www.googleapis.com/auth/cloud-platform',
]);
const TOKEN_URL = 'https://oauth2.googleapis.com/token';
const ENCODER = new TextEncoder();
const MAX_PAGES = 5;
const MAX_QUOTAS = 128;
const MAX_EXPIRY_MS = 3600000;
const GPU_MODELS = Object.freeze({
  GPUS_ALL_REGIONS: 'gpu_all_regions', GPUS: 'gpu_total', GPU_FAMILY: 'gpu_family_unspecified',
  NVIDIA_A100_GPUS: 'nvidia_a100_40gb', NVIDIA_A100_80GB_GPUS: 'nvidia_a100_80gb',
  NVIDIA_H100_GPUS: 'nvidia_h100', NVIDIA_H100_80GB_GPUS: 'nvidia_h100_80gb',
  NVIDIA_H200_GPUS: 'nvidia_h200', NVIDIA_L4_GPUS: 'nvidia_l4',
  NVIDIA_T4_GPUS: 'nvidia_t4', NVIDIA_V100_GPUS: 'nvidia_v100', NVIDIA_P100_GPUS: 'nvidia_p100',
  NVIDIA_P4_GPUS: 'nvidia_p4', NVIDIA_RTX_PRO_6000_GPUS: 'nvidia_rtx_pro_6000',
  NVIDIA_B200_GPUS: 'nvidia_b200', NVIDIA_GB200_GPUS: 'nvidia_gb200', NVIDIA_GB300_GPUS: 'nvidia_gb300',
});
const API_REASONS = new Set(['SERVICE_DISABLED', 'ACCESS_TOKEN_SCOPE_INSUFFICIENT', 'IAM_PERMISSION_DENIED',
  'CONSUMER_INVALID', 'PROJECT_DELETED', 'BILLING_DISABLED', 'RATE_LIMIT_EXCEEDED', 'USER_PROJECT_DENIED',
  'PERMISSION_DENIED', 'UNAUTHENTICATED', 'INVALID_ARGUMENT', 'FAILED_PRECONDITION', 'RESOURCE_EXHAUSTED',
  'NOT_FOUND', 'INTERNAL', 'UNAVAILABLE', 'DEADLINE_EXCEEDED', 'INVALID_RESOURCE',
  'invalid_grant', 'invalid_client', 'invalid_scope', 'unauthorized_client', 'access_denied']);
const VERTEX_GPUS = new Set(['a100', 'a100_80gb', 'h100', 'h100_80gb', 'h200', 'l4', 't4', 'v100', 'p100', 'p4', 'b200']);

const reply = (body, status = 200) => new Response(JSON.stringify(body), { status,
  headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' } });
const hex = bytes => Array.from(new Uint8Array(bytes), b => b.toString(16).padStart(2, '0')).join('');
function equalHash(left, right) { let mismatch = 0; for (let i = 0; i < 64; i++) mismatch |= left.charCodeAt(i) ^ right.charCodeAt(i); return mismatch === 0; }
function b64url(bytes) {
  let binary = ''; for (const value of new Uint8Array(bytes)) binary += String.fromCharCode(value);
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
const b64text = value => b64url(ENCODER.encode(value));

export function expiryMillis(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/.test(value)) return null;
  const time = Date.parse(value);
  if (!Number.isFinite(time)) return null;
  const canonical = new Date(time).toISOString();
  return canonical === value || canonical.replace('.000Z', 'Z') === value ? time : null;
}

export async function authenticate(request, env, cryptoImpl, now) {
  const expires = expiryMillis(env.GCP_PREFLIGHT_EXPIRES_AT);
  if (expires === null || expires <= now || expires - now > MAX_EXPIRY_MS) return { ok: false, reason: 'expired_or_invalid_gate' };
  const expected = env.GCP_PREFLIGHT_AUTH_SHA256;
  const authorization = request.headers.get('Authorization') || '';
  const match = /^Bearer ([A-Za-z0-9_-]{43,128})$/.exec(authorization);
  if (typeof expected !== 'string' || !/^[a-f0-9]{64}$/.test(expected) || !match) return { ok: false, reason: 'unauthorized' };
  const digest = hex(await cryptoImpl.subtle.digest('SHA-256', ENCODER.encode(match[1])));
  return equalHash(digest, expected) ? { ok: true, expires } : { ok: false, reason: 'unauthorized' };
}

function configuration(env) {
  const present = { GCP_SA_KEY: typeof env.GCP_SA_KEY === 'string' && env.GCP_SA_KEY.length > 0,
    GCP_PROJECT: typeof env.GCP_PROJECT === 'string' && env.GCP_PROJECT.length > 0,
    GCP_TUNING_BUCKET: typeof env.GCP_TUNING_BUCKET === 'string' && env.GCP_TUNING_BUCKET.length > 0 };
  if (!Object.values(present).every(Boolean) || env.GCP_PROJECT !== PROJECT
      || ![BUCKET, 'gs://' + BUCKET].includes(env.GCP_TUNING_BUCKET)
      || env.GCP_SA_KEY.length > 32768) return { ok: false, present };
  let key;
  try { key = JSON.parse(env.GCP_SA_KEY); } catch { return { ok: false, present }; }
  if (!key || typeof key !== 'object' || Array.isArray(key) || key.type !== 'service_account'
      || key.project_id !== PROJECT || typeof key.client_email !== 'string'
      || !/^[A-Za-z0-9._-]{1,128}@(?:[a-z0-9-]+\.)*gserviceaccount\.com$/.test(key.client_email)
      || typeof key.private_key !== 'string' || key.private_key.length > 16384
      || !/^-----BEGIN PRIVATE KEY-----\r?\n[A-Za-z0-9+/=\r\n]+-----END PRIVATE KEY-----\r?\n?$/.test(key.private_key)
      || (key.token_uri !== undefined && key.token_uri !== TOKEN_URL)) return { ok: false, present };
  return { ok: true, present, key };
}

function reasonFrom(data, httpStatus) {
  const error = data?.error;
  for (const detail of Array.isArray(error?.details) ? error.details.slice(0, 20) : []) {
    if (API_REASONS.has(detail?.reason)) return detail.reason;
  }
  if (API_REASONS.has(error?.status)) return error.status;
  if (typeof error === 'string' && API_REASONS.has(error)) return error;
  return httpStatus === 401 ? 'UNAUTHENTICATED' : httpStatus === 403 ? 'PERMISSION_DENIED'
    : httpStatus === 404 ? 'NOT_FOUND' : httpStatus === 429 ? 'RESOURCE_EXHAUSTED' : 'upstream_error';
}

async function boundedJson(response, limit) {
  const declared = response.headers.get('Content-Length');
  if (declared !== null && (!/^\d+$/.test(declared) || Number(declared) > limit)) {
    await response.body?.cancel().catch(() => {}); throw new Error('bounded_response_rejected');
  }
  if (!response.body) throw new Error('empty_response');
  const reader = response.body.getReader(); let bytes = 0; const chunks = [];
  try {
    for (;;) {
      const part = await reader.read(); if (part.done) break;
      bytes += part.value.byteLength;
      if (bytes > limit) { await reader.cancel(); throw new Error('bounded_response_rejected'); }
      chunks.push(part.value);
    }
  } finally { reader.releaseLock(); }
  const combined = new Uint8Array(bytes); let offset = 0;
  for (const chunk of chunks) { combined.set(chunk, offset); offset += chunk.length; }
  return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(combined));
}

async function requestJson(fetchImpl, url, options, limit) {
  let response;
  try { response = await fetchImpl(url, { ...options, redirect: 'manual', signal: AbortSignal.timeout(10000) }); }
  catch { return { ok: false, http_status: null, reason: 'transport_unavailable' }; }
  const status = Number.isInteger(response.status) ? response.status : null;
  if (status === null || status >= 300 && status < 400) {
    await response.body?.cancel().catch(() => {}); return { ok: false, http_status: status, reason: 'redirect_rejected' };
  }
  let data;
  try { data = await boundedJson(response, limit); }
  catch { return { ok: false, http_status: status, reason: 'malformed_or_oversized_response' }; }
  return status >= 200 && status < 300 ? { ok: true, http_status: status, data }
    : { ok: false, http_status: status, reason: reasonFrom(data, status) };
}

async function tokenFor(key, gateExpiry, { fetchImpl, cryptoImpl, now }) {
  let signingKey;
  try {
    const der = Uint8Array.from(atob(key.private_key.replace(/-----[^-]+-----/g, '').replace(/\s+/g, '')), c => c.charCodeAt(0));
    if (der.length < 512 || der.length > 8192) throw new Error('invalid_key');
    signingKey = await cryptoImpl.subtle.importKey('pkcs8', der,
      { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['sign']);
  } catch { return { ok: false, http_status: null, reason: 'service_account_key_invalid' }; }
  const issued = Math.floor(now / 1000), expires = Math.min(issued + 600, Math.floor(gateExpiry / 1000));
  const encoded = b64text(JSON.stringify({ alg: 'RS256', typ: 'JWT' })) + '.' + b64text(JSON.stringify({
    iss: key.client_email, scope: SCOPES.join(' '), aud: TOKEN_URL, iat: issued, exp: expires }));
  let signature;
  try { signature = b64url(await cryptoImpl.subtle.sign('RSASSA-PKCS1-v1_5', signingKey, ENCODER.encode(encoded))); }
  catch { return { ok: false, http_status: null, reason: 'jwt_signing_failed' }; }
  const result = await requestJson(fetchImpl, TOKEN_URL, { method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer', assertion: encoded + '.' + signature }).toString() }, 65536);
  if (!result.ok) return result;
  if (typeof result.data.access_token !== 'string' || !/^[A-Za-z0-9._~+/-]{1,8192}$/.test(result.data.access_token)
      || String(result.data.token_type || '').toLowerCase() !== 'bearer') return { ok: false, http_status: result.http_status, reason: 'oauth_response_invalid' };
  return { ok: true, http_status: result.http_status, token: result.data.access_token };
}

function number(value, allowUnlimited = false) {
  if (typeof value === 'string' && /^-?\d+(?:\.\d+)?$/.test(value) && value.length <= 32) value = Number(value);
  return typeof value === 'number' && Number.isFinite(value) && (value >= 0 || allowUnlimited && value === -1)
    && Math.abs(value) <= Number.MAX_SAFE_INTEGER ? value : null;
}
function computeQuotas(data) {
  if (!Array.isArray(data?.quotas) || data.quotas.length > 1000) return { quota_fields_available: false, quotas: [] };
  const rows = [];
  for (const quota of data.quotas) {
    if (!Object.hasOwn(GPU_MODELS, quota?.metric)) continue;
    const model = GPU_MODELS[quota.metric];
    const limit = number(quota.limit, true), usage = number(quota.usage);
    if (limit !== null && usage !== null) rows.push({ gpu: model, limit, usage });
  }
  return { quota_fields_available: !data.quotaStatusWarning, quotas: rows.slice(0, MAX_QUOTAS),
    numeric_rows_complete: rows.length <= MAX_QUOTAS };
}
function vertexQuotas(data) {
  if (!Array.isArray(data?.metrics) || data.metrics.length > 200) return null;
  const rows = [];
  for (const metric of data.metrics) {
    const match = /^aiplatform\.googleapis\.com\/custom_model_training_nvidia_([a-z0-9_]+)_gpus$/.exec(String(metric?.metric || '').toLowerCase());
    if (!match || !VERTEX_GPUS.has(match[1]) || !Array.isArray(metric.consumerQuotaLimits)) continue;
    for (const limit of metric.consumerQuotaLimits.slice(0, 100)) {
      if (!Array.isArray(limit.quotaBuckets)) continue;
      for (const bucket of limit.quotaBuckets.slice(0, 100)) {
        if (!bucket || typeof bucket !== 'object' || Array.isArray(bucket)) continue;
        if (bucket.dimensions !== undefined && (!bucket.dimensions || typeof bucket.dimensions !== 'object' || Array.isArray(bucket.dimensions))) continue;
        const dims = bucket.dimensions || {}, region = dims.region || dims.location;
        if (region !== undefined && !REGIONS.includes(region)) continue;
        // A successful FULL Service Usage response contains proto3 QuotaBucket
        // messages. Its implicit-presence int64 effective_limit defaults to zero
        // when omitted. Missing metrics/buckets or explicit invalid values still
        // remain unavailable rather than being converted to a zero quota.
        // https://github.com/googleapis/googleapis/blob/master/google/api/serviceusage/v1beta1/resources.proto
        const omitted = !Object.hasOwn(bucket, 'effectiveLimit');
        const effective = omitted ? 0 : number(bucket.effectiveLimit, true);
        if (effective !== null) rows.push({ gpu: 'nvidia_' + match[1], region: region || 'global_default', limit: effective,
          ...(omitted ? { limit_basis: 'proto3_default_zero' } : {}) });
      }
    }
  }
  return rows;
}

async function checkTarget(target, url, token, fetchImpl, parser) {
  const result = await requestJson(fetchImpl, url, { method: 'GET', headers: { Authorization: 'Bearer ' + token } }, 2 * 1024 * 1024);
  if (!result.ok) return { target, http_status: result.http_status, reason: result.reason };
  return { target, http_status: result.http_status, reason: 'ok', ...parser(result.data) };
}
async function vertexQuotaCheck(token, fetchImpl) {
  const base = 'https://serviceusage.googleapis.com/v1beta1/projects/' + PROJECT + '/services/aiplatform.googleapis.com/consumerQuotaMetrics';
  let next = '', complete = false, rows = [], pages = 0, metricIds = [], shapes = [];
  for (; pages < MAX_PAGES; pages++) {
    const query = new URLSearchParams({ view: 'FULL', pageSize: '200', ...(next ? { pageToken: next } : {}) });
    const result = await requestJson(fetchImpl, base + '?' + query, { method: 'GET', headers: { Authorization: 'Bearer ' + token } }, 2 * 1024 * 1024);
    if (!result.ok) return { target: 'vertex_custom_gpu_quotas', http_status: result.http_status, reason: result.reason,
      quota_inventory_complete: false, pages_read: pages, quotas: rows.slice(0, MAX_QUOTAS) };
    const values = vertexQuotas(result.data);
    if (!values) return { target: 'vertex_custom_gpu_quotas', http_status: result.http_status,
      reason: 'quota_schema_unavailable', quota_inventory_complete: false, pages_read: pages + 1, quotas: rows.slice(0, MAX_QUOTAS) };
    rows.push(...values);
    for (const metric of result.data.metrics) {
      const name = String(metric?.metric || '');
      if (/^[A-Za-z0-9_/.-]{1,220}$/.test(name) && /training/i.test(name) && /gpu|a100|h100/i.test(name)) metricIds.push(name);
      if (/^aiplatform\.googleapis\.com\/custom_model_training_nvidia_(?:a100(?:_80gb)?|h100)_gpus$/i.test(name)) {
        const limits = Array.isArray(metric.consumerQuotaLimits) ? metric.consumerQuotaLimits.filter(v => v && typeof v === 'object' && !Array.isArray(v)) : [];
        shapes.push({ metric: name, limit_count: limits.length, limits: limits.slice(0, 4).map(limit => ({
          has_quota_buckets: Array.isArray(limit.quotaBuckets), default_limit: number(limit.defaultLimit, true),
          limit_fields: Object.keys(limit).filter(k => /^[A-Za-z_]{1,40}$/.test(k)).slice(0, 20),
          buckets: (Array.isArray(limit.quotaBuckets) ? limit.quotaBuckets : []).filter(v => v && typeof v === 'object' && !Array.isArray(v)).slice(0, 12).map(bucket => ({
            effective_limit: number(bucket.effectiveLimit, true), default_limit: number(bucket.defaultLimit, true),
            bucket_fields: Object.keys(bucket).filter(k => /^[A-Za-z_]{1,40}$/.test(k)).slice(0, 20),
            effective_limit_type: typeof bucket.effectiveLimit,
            region: /^[a-z]+-[a-z]+\d$/.test(String(bucket.dimensions?.region || bucket.dimensions?.location || ''))
              ? String(bucket.dimensions?.region || bucket.dimensions?.location) : 'global_or_unrecognized',
          })) })) });
      }
    }
    const value = result.data.nextPageToken;
    if (value === undefined || value === '') { complete = true; pages++; break; }
    if (typeof value !== 'string' || value.length > 4096 || value === next) { pages++; break; }
    next = value;
  }
  return { target: 'vertex_custom_gpu_quotas', http_status: 200, reason: 'ok',
    quota_inventory_complete: complete && rows.length <= MAX_QUOTAS, pages_read: pages,
    quotas: rows.slice(0, MAX_QUOTAS), training_gpu_metric_ids: [...new Set(metricIds)].slice(0, 128), quota_schema_samples: shapes.slice(0, 4) };
}

async function vertexPermissions(token, fetchImpl) {
  const allowed = ['aiplatform.customJobs.create', 'aiplatform.customJobs.get', 'aiplatform.customJobs.list', 'aiplatform.customJobs.cancel'];
  const result = await requestJson(fetchImpl, 'https://cloudresourcemanager.googleapis.com/v1/projects/' + PROJECT + ':testIamPermissions',
    { method: 'POST', headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' }, body: JSON.stringify({ permissions: allowed }) }, 65536);
  return result.ok ? { target: 'vertex_custom_job_permissions', http_status: result.http_status, reason: 'ok',
    permissions: allowed.filter(p => Array.isArray(result.data?.permissions) && result.data.permissions.includes(p)) }
    : { target: 'vertex_custom_job_permissions', http_status: result.http_status, reason: result.reason };
}

export async function handle(request, env, options = {}) {
  const fetchImpl = options.fetchImpl || globalThis.fetch, cryptoImpl = options.cryptoImpl || globalThis.crypto;
  const now = options.now === undefined ? Date.now() : options.now;
  try {
    const url = new URL(request.url);
    if (url.pathname !== '/preflight' || url.search || url.hash) return reply({ reason: 'not_found' }, 404);
    if (request.method !== 'GET') return reply({ reason: 'method_not_allowed' }, 405);
    const gate = await authenticate(request, env, cryptoImpl, now);
    if (!gate.ok) return reply({ reason: gate.reason }, 403);
    const gatedFetch = (url, init) => {
      const current = typeof options.currentTime === 'function' ? options.currentTime() : options.now === undefined ? Date.now() : options.now;
      if (current >= gate.expires) throw new Error('gate_expired');
      return fetchImpl(url, init);
    };
    const config = configuration(env);
    if (!config.ok) return reply({ reason: 'configuration_invalid', binding_presence: config.present }, 503);
    const oauth = await tokenFor(config.key, gate.expires, { fetchImpl: gatedFetch, cryptoImpl, now });
    const publicOauth = { http_status: oauth.http_status, reason: oauth.ok ? 'ok' : oauth.reason };
    if (!oauth.ok) return reply({ kind: 'gcp_readonly_preflight_v1', binding_presence: config.present, oauth: publicOauth, checks: [] }, 502);
    const quotaQuery = '?fields=quotas(metric,limit,usage)';
    const tasks = [checkTarget('compute_project_quotas', 'https://compute.googleapis.com/compute/v1/projects/' + PROJECT + quotaQuery,
      oauth.token, gatedFetch, computeQuotas)];
    for (const region of REGIONS) tasks.push(checkTarget('compute_region_' + region,
      'https://compute.googleapis.com/compute/v1/projects/' + PROJECT + '/regions/' + region + '?fields=quotas(metric,limit,usage),quotaStatusWarning(code)',
      oauth.token, gatedFetch, computeQuotas));
    for (const service of ['compute.googleapis.com', 'aiplatform.googleapis.com', 'storage.googleapis.com', 'cloudquotas.googleapis.com']) {
      tasks.push(checkTarget('service_' + service.split('.')[0],
        'https://serviceusage.googleapis.com/v1/projects/' + PROJECT + '/services/' + service + '?fields=state,name', oauth.token, gatedFetch,
        data => ({ state: ['ENABLED', 'DISABLED'].includes(data?.state) ? data.state : 'UNKNOWN',
          project_number: /^projects\/([0-9]{6,30})\/services\//.exec(String(data?.name || ''))?.[1] || null })));
    }
    tasks.push(checkTarget('gcs_bucket_metadata', 'https://storage.googleapis.com/storage/v1/b/' + BUCKET + '?fields=location',
      oauth.token, gatedFetch, () => ({ bucket_readable: true })));
    tasks.push(checkTarget('gcs_object_permissions', 'https://storage.googleapis.com/storage/v1/b/' + BUCKET + '/iam/testPermissions?permissions=storage.objects.get&permissions=storage.objects.create&permissions=storage.objects.list',
      oauth.token, gatedFetch, data => ({ permissions: ['storage.objects.get', 'storage.objects.create', 'storage.objects.list'].filter(p => Array.isArray(data?.permissions) && data.permissions.includes(p)) })));
    tasks.push(checkTarget('vertex_custom_jobs_list', 'https://us-central1-aiplatform.googleapis.com/v1/projects/' + PROJECT + '/locations/us-central1/customJobs?pageSize=1',
      oauth.token, gatedFetch, () => ({ custom_jobs_readable: true })));
    tasks.push(vertexQuotaCheck(oauth.token, gatedFetch));
    tasks.push(vertexPermissions(oauth.token, gatedFetch));
    tasks.push(checkTarget('cloud_quotas_a100_info',
      'https://cloudquotas.googleapis.com/v1/projects/315617551669/locations/global/services/aiplatform.googleapis.com/quotaInfos?pageSize=200',
      oauth.token, gatedFetch, data => ({ first_page_only: true,
        schema_available: Array.isArray(data?.quotaInfos),
        quota_ids: (Array.isArray(data?.quotaInfos) ? data.quotaInfos : []).filter(q =>
          /^aiplatform\.googleapis\.com\/custom_model_training_nvidia_a100_80gb_gpus$/i.test(String(q?.metric || ''))
          && typeof q.quotaId === 'string' && /^[A-Za-z0-9_.-]{1,200}$/.test(q.quotaId))
          .slice(0, 10).map(q => ({ quota_id: q.quotaId, metric: q.metric })) })));
    const checks = await Promise.all(tasks);
    return reply({ kind: 'gcp_readonly_preflight_v1', binding_presence: config.present, oauth: publicOauth, checks,
      write_api_calls: 0, gpu_creation_attempted: false, quota_does_not_prove_gpu_stock: true });
  } catch { return reply({ reason: 'preflight_failed', write_api_calls: 0, gpu_creation_attempted: false }, 500); }
}

export default { fetch(request, env) { return handle(request, env); } };
// Pure helpers for the separately authenticated Gemma controller; HTTP behavior above is unchanged.
export { configuration as gcpConfiguration, tokenFor as gcpTokenFor, requestJson as gcpRequestJson };
