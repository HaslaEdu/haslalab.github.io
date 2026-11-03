// Vertex AI (Gemini Enterprise Agent Platform) supervised tuning of a Gemini page reader, from the Worker (admin bench).
// A service account (GCP_SA_KEY: its JSON key, a Worker secret) signs a JWT for an OAuth access token; the training
// photos and JSONL go to the tuning bucket (GCP_TUNING_BUCKET, gs://name), then a tuning job is created and polled.
// An API key cannot do this: Vertex answered 401 «API keys are not supported» for the tuning-jobs API.

const b64url = bytes => btoa(String.fromCharCode(...new Uint8Array(bytes))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const b64urlText = text => b64url(new TextEncoder().encode(text));

export function gcpConfig(env) {
  let key = null;
  try { key = env.GCP_SA_KEY ? JSON.parse(env.GCP_SA_KEY) : null; } catch { key = null; }
  const bucket = String(env.GCP_TUNING_BUCKET || '').trim().replace(/^gs:\/\//, '').replace(/\/+$/, '');
  return { key: key?.private_key && key?.client_email ? key : null, project: String(env.GCP_PROJECT || key?.project_id || '').trim(),
    bucket, region: String(env.GCP_REGION || 'us-central1').trim(),
    /* names only, never values: what the admin has set */
    present: { GCP_SA_KEY: !!env.GCP_SA_KEY, sa_key_valid: !!(key?.private_key && key?.client_email), GCP_PROJECT: !!env.GCP_PROJECT, GCP_TUNING_BUCKET: !!env.GCP_TUNING_BUCKET } };
}

/** an OAuth access token for the service account (cloud-platform scope), from a signed JWT */
export async function gcpToken(env, { fetchImpl = globalThis.fetch, now = Date.now() } = {}) {
  const { key } = gcpConfig(env); if (!key) throw new Error('gcp_sa_key_missing');
  const der = Uint8Array.from(atob(key.private_key.replace(/-----[^-]+-----/g, '').replace(/\s+/g, '')), c => c.charCodeAt(0));
  const pk = await crypto.subtle.importKey('pkcs8', der, { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['sign']);
  const iat = Math.floor(now / 1000), head = b64urlText(JSON.stringify({ alg: 'RS256', typ: 'JWT' }));
  const claim = b64urlText(JSON.stringify({ iss: key.client_email, scope: 'https://www.googleapis.com/auth/cloud-platform', aud: 'https://oauth2.googleapis.com/token', iat, exp: iat + 3600 }));
  const sig = b64url(await crypto.subtle.sign('RSASSA-PKCS1-v1_5', pk, new TextEncoder().encode(head + '.' + claim)));
  const r = await fetchImpl('https://oauth2.googleapis.com/token', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: 'grant_type=' + encodeURIComponent('urn:ietf:params:oauth:grant-type:jwt-bearer') + '&assertion=' + head + '.' + claim + '.' + sig });
  const j = await r.json().catch(() => ({}));
  if (!r.ok || !j.access_token) throw new Error('gcp_token_' + r.status + ':' + String(j.error_description || j.error || '').slice(0, 120));
  return j.access_token;
}

/** one object into the tuning bucket */
export async function gcsPut(env, token, name, bytes, contentType, { fetchImpl = globalThis.fetch } = {}) {
  const { bucket } = gcpConfig(env); if (!bucket) throw new Error('gcp_bucket_missing');
  const r = await fetchImpl(`https://storage.googleapis.com/upload/storage/v1/b/${encodeURIComponent(bucket)}/o?uploadType=media&name=${encodeURIComponent(name)}`,
    { method: 'POST', headers: { Authorization: 'Bearer ' + token, 'Content-Type': contentType }, body: bytes });
  if (!r.ok) throw new Error('gcs_put_' + r.status + ':' + (await r.text().catch(() => '')).slice(0, 160));
  return `gs://${bucket}/${name}`;
}

const api = (env, path) => { const { project, region } = gcpConfig(env); return `https://${region}-aiplatform.googleapis.com/v1/projects/${project}/locations/${region}/${path}`; };

/** a supervised tuning job for a Gemini base model over the uploaded JSONL */
export async function startTuning(env, token, { baseModel, train, validation, epochs = 3, name, fetchImpl = globalThis.fetch }) {
  const body = { baseModel, tunedModelDisplayName: String(name || 'haslalab-reader').slice(0, 120),
    supervisedTuningSpec: { trainingDatasetUri: train, ...(validation ? { validationDatasetUri: validation } : {}), hyperParameters: { epochCount: Math.max(1, Math.min(20, +epochs || 3)) } } };
  const r = await fetchImpl(api(env, 'tuningJobs'), { method: 'POST', headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error('tuning_start_' + r.status + ':' + String(j?.error?.message || '').slice(0, 300));
  return { job: j.name, state: j.state };
}

/** a tuning job's state, and the tuned model's endpoint once it has one */
export async function tuningStatus(env, token, job, { fetchImpl = globalThis.fetch } = {}) {
  if (!/^projects\/[\w-]+\/locations\/[\w-]+\/tuningJobs\/\d+$/.test(String(job || ''))) throw new Error('bad_job');
  const { region } = gcpConfig(env);
  const r = await fetchImpl(`https://${region}-aiplatform.googleapis.com/v1/${job}`, { headers: { Authorization: 'Bearer ' + token } });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error('tuning_status_' + r.status + ':' + String(j?.error?.message || '').slice(0, 300));
  return { job: j.name, state: j.state, error: j.error?.message || null, model: j.tunedModel?.model || null, endpoint: j.tunedModel?.endpoint || null,
    created: j.createTime || null, ended: j.endTime || null };
}
