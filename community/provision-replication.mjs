// Uses the existing deployment token only. Updates only read replication on the existing D1 database.
// No database creation, data migration, credential changes or plan changes belong in this helper.
import { appendFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

export const REPLICATION_URL = 'https://api.cloudflare.com/client/v4/accounts/3bcdf2f586d9d8486b3e473f27515f26/d1/database/96761b6d-c194-4ee5-9836-7845b51a5f07';
const UNVERIFIED = Object.freeze({ verified: false, mode: 'unverified' });

export async function provisionReplication(request, log = console.log, warn = console.warn) {
  async function call(method, body) {
    let response;
    try { response = await request(method, body); }
    catch { throw new Error(`D1 read replication ${method}: network request failed.`); }
    log(`D1 read replication ${method}: HTTP ${response.status}.`);
    if (response.status === 403) {
      response.body?.cancel().catch(() => {});
      warn('::warning::D1 read replication is unverified: HTTP 403 with the existing deployment token. No credential or permission changes were attempted.');
      return null;
    }
    if (!response.ok) {
      response.body?.cancel().catch(() => {});
      throw new Error(`D1 read replication ${method}: unexpected HTTP ${response.status}.`);
    }
    let data;
    try { data = await response.json(); }
    catch { throw new Error(`D1 read replication ${method}: invalid JSON response.`); }
    if (data?.success !== true) throw new Error(`D1 read replication ${method}: API did not report success.`);
    if (method === 'PUT') return {};
    if (!data.result || typeof data.result !== 'object' || Array.isArray(data.result)) throw new Error('D1 read replication GET: missing database result.');
    const mode = data.result.read_replication?.mode;
    if (mode !== undefined && mode !== 'auto' && mode !== 'disabled') throw new Error('D1 read replication GET: unexpected mode.');
    log(`D1 read replication mode: ${mode || 'missing'}.`);
    return { mode };
  }
  const current = await call('GET');
  if (!current) return UNVERIFIED;
  if (current.mode === 'auto') return { verified: true, mode: 'auto' };
  if (!await call('PUT', { read_replication: { mode: 'auto' } })) return UNVERIFIED;
  const verified = await call('GET');
  if (!verified) return UNVERIFIED;
  if (verified.mode !== 'auto') throw new Error('D1 read replication verification failed: mode is not auto.');
  return { verified: true, mode: 'auto' };
}

export async function runReplicationProvision({ token, fetchImpl = globalThis.fetch, log = console.log, warn = console.warn } = {}) {
  if (typeof token !== 'string' || !token.trim()) throw new Error('The existing deployment Cloudflare token is required.');
  return provisionReplication((method, body) => fetchImpl(REPLICATION_URL, {
    method, redirect: 'error', signal: AbortSignal.timeout(15000),
    headers: { Authorization: 'Bearer ' + token, ...(body ? { 'Content-Type': 'application/json' } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {}),
  }), log, warn);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  let mode = 'unverified';
  try { mode = (await runReplicationProvision({ token: process.env.CLOUDFLARE_API_TOKEN })).mode; }
  catch (error) { console.error(error.message); process.exitCode = 1; }
  finally {
    if (process.env.GITHUB_OUTPUT) {
      try { appendFileSync(process.env.GITHUB_OUTPUT, `read_replication=${mode}\n`); }
      catch { console.error('Unable to write the read replication deployment output.'); process.exitCode = 1; }
    }
  }
}
