// Called by the existing deployment workflow, using its existing Cloudflare credential.
// Never ignores permission/network errors. The fixed additive job schema initializes through
// the Worker's existing D1 binding; this deploy token needs no D1 management/import permission.
import { spawn } from 'node:child_process';
import { pathToFileURL } from 'node:url';

export const QUEUES = ['haslalab-lab-jobs-dead', 'haslalab-lab-jobs'];
const alreadyExists = result => /\bqueue\b[^\n]*\balready exists\b/i.test(result.output || '') &&
  !/authentication error|permission denied|unauthorized|forbidden|\b403\b|\b401\b/i.test(result.output || '');

export async function provision(run, log = console.log) {
  for (const queue of QUEUES) {
    const result = await run(['queues', 'create', queue]);
    if (result.code !== 0 && !alreadyExists(result)) throw new Error(`Cannot provision ${queue}: ${result.output}`);
    log(`${queue}: ${result.code === 0 ? 'created' : 'already configured'}`);
  }
  log('Queue resources are ready; fixed job tables initialize through the existing D1 binding.');
}

function runWrangler(args) {
  return new Promise(resolve => {
    const child = spawn(process.execPath, ['./node_modules/wrangler/bin/wrangler.js', ...args], {
      env: { ...process.env, CI: 'true', WRANGLER_SEND_METRICS: 'false' }, stdio: ['ignore', 'pipe', 'pipe'],
    });
    let output = '', ended = false;
    const timer = setTimeout(() => { child.kill(); finish(124); }, 90000);
    const collect = data => { output = (output + data.toString()).slice(-20000); };
    const finish = code => {
      if (ended) return; ended = true; clearTimeout(timer);
      for (const key of ['CLOUDFLARE_API_TOKEN', 'CLOUDFLARE_API_KEY']) if (process.env[key]) output = output.split(process.env[key]).join('[redacted]');
      resolve({ code, output: output.replace(/\x1b\[[0-9;]*m/g, '').trim() });
    };
    child.stdout.on('data', collect); child.stderr.on('data', collect);
    child.on('error', error => { collect(error.message); finish(1); });
    child.on('close', code => finish(code ?? 1));
  });
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  if (!process.env.CLOUDFLARE_API_TOKEN && !process.env.CLOUDFLARE_API_KEY) {
    console.error('The deployment Cloudflare credential is required.'); process.exitCode = 1;
  } else {
    await provision(runWrangler).catch(error => { console.error(error.message); process.exitCode = 1; });
  }
}
