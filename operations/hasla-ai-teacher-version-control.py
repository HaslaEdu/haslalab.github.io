"""Bounded teacher calls through inherited secrets on a NONPRODUCTION Worker version.

No key retrieval, secret creation, deployment, routing changes, GPU or raw model
response logging. Preflight is read-only except for a private W&B proof artifact.
Official contracts: developers.cloudflare.com/api/resources/workers/subresources/
scripts/subresources/versions/methods/create/ and workers/versions-and-deployments/version-urls/.
"""
from __future__ import annotations
import argparse
import base64
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
import time

ACCOUNT = '3bcdf2f586d9d8486b3e473f27515f26'
WORKER = 'haslalab-community'
ENTITY = 'mimgyuson-haslaedu'
PROJECT = 'hasla-ai-private-training'
MODELS = {'openai': 'gpt-6.1-terra', 'deepseek': 'deepseek-v4-pro'}
TASKS = ('heat_exchange_review', 'heat_exchange_n2', 'heat_exchange_n10000', 'math_integral', 'physics_mechanics')
# Operational runaway ceiling, not an answer-length target or reward value.
MAX_OUTPUT = 32768
INPUT_TOKEN_UPPER = 16384
TEACHER_RESERVE_KRW = 1000
GENERAL_RESERVE_KRW = 5000
TOTAL_BUDGET_KRW = 100000
MAX_RESPONSE_BYTES = 1024 * 1024
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'community/src/ai-teacher.js'
SHA = re.compile(r'[a-f0-9]{40,64}\Z')
UUID = re.compile(r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}\Z')
ENTRY = b'''import teacher from './teacher.js';
import { WorkerEntrypoint } from 'cloudflare:workers';
// Preserve the existing named/default export surface for Worker-version upload.
// This version is NEVER deployed; RPC, queue and cron paths fail closed.
export class StudioProvider extends WorkerEntrypoint {
  async responses() { throw new Error('teacher_preview_rpc_disabled'); }
  async imageEdit() { throw new Error('teacher_preview_rpc_disabled'); }
}
export default {
  fetch: teacher.fetch,
  async queue() { throw new Error('teacher_preview_queue_disabled'); },
  async scheduled() { throw new Error('teacher_preview_cron_disabled'); }
};
'''


class TeacherControlError(RuntimeError):
    def __init__(self, code, *, phase=None, http_status=None, cloudflare_error_codes=None):
        super().__init__(code)
        self.phase = phase
        self.http_status = http_status
        self.cloudflare_error_codes = cloudflare_error_codes or []


def require(value, code):
    if not value:
        raise TeacherControlError(code)


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def cost_bound(prior):
    require(type(prior) is int and 0 <= prior <= TOTAL_BUDGET_KRW, 'invalid_prior_budget')
    # Standard/peak uncached input and all output (including reasoning), checked
    # 2026-11-05: OpenAI Terra $1/$5; DeepSeek V4 Pro $1.32/$3.96 per million.
    # Fixed handler prompts are <12KB, bounded at 16384 tokens including framing.
    usd = (Decimal(INPUT_TOKEN_UPPER) * Decimal('2.32') + Decimal(MAX_OUTPUT) * Decimal('8.96')) / 1000000
    upper = int((usd * 2000 * Decimal('1.15')).to_integral_value(rounding=ROUND_CEILING))
    require(upper <= TEACHER_RESERVE_KRW and prior + TEACHER_RESERVE_KRW + GENERAL_RESERVE_KRW <= TOTAL_BUDGET_KRW,
            'combined_authorized_budget_exhausted')
    return {'authorized_combined_krw': TOTAL_BUDGET_KRW, 'prior_upper_krw': prior,
            'teacher_reserved_upper_krw': TEACHER_RESERVE_KRW, 'modeled_model_upper_krw': upper,
            'general_reserve_krw': GENERAL_RESERVE_KRW, 'provider_bill_verified': False,
            'max_input_tokens_per_provider': INPUT_TOKEN_UPPER, 'max_output_tokens_per_provider': MAX_OUTPUT}


class Cloudflare:
    def __init__(self, token, session):
        require(isinstance(token, str) and bool(token), 'existing_cloudflare_token_missing')
        self.token, self.session = token, session

    def call(self, method, suffix, *, files=None):
        # The only mutation this client can issue creates an UNDEPLOYED version.
        allowed_get = {f'/workers/scripts/{WORKER}/settings', f'/workers/scripts/{WORKER}/deployments',
                       f'/workers/scripts/{WORKER}/versions', f'/workers/scripts/{WORKER}/subdomain', '/workers/subdomain'}
        require((method == 'GET' and suffix in allowed_get) or
                (method == 'POST' and suffix == f'/workers/scripts/{WORKER}/versions?bindings_inherit=strict' and files),
                'cloudflare_operation_not_allowed')
        response = self.session.request(method, 'https://api.cloudflare.com/client/v4/accounts/' + ACCOUNT + suffix,
            headers={'Authorization': 'Bearer ' + self.token}, files=files, timeout=45, allow_redirects=False)
        try:
            phase = 'cloudflare_upload_version' if method == 'POST' else 'cloudflare_get_' + suffix.rsplit('/', 1)[-1]
            try:
                value = response.json()
            except ValueError:
                value = {}
            codes = sorted({e['code'] for e in value.get('errors', []) if isinstance(e, dict)
                            and type(e.get('code')) is int and 0 <= e['code'] <= 999999999}) if isinstance(value, dict) else []
            if response.status_code not in (200, 201):
                raise TeacherControlError('cloudflare_http_' + str(response.status_code), phase=phase,
                                         http_status=response.status_code, cloudflare_error_codes=codes)
            if not isinstance(value, dict) or value.get('success') is not True:
                raise TeacherControlError('cloudflare_request_rejected', phase=phase,
                                         http_status=response.status_code, cloudflare_error_codes=codes)
            return value['result']
        finally:
            response.close()


def snapshot(cf):
    settings = cf.call('GET', f'/workers/scripts/{WORKER}/settings')
    bindings = settings.get('bindings', [])
    by_name = {row.get('name'): row for row in bindings}
    require(all(by_name.get(name, {}).get('type') == 'secret_text' for name in ('OPENAI_API_KEY', 'DEEPSEEK_API_KEY')),
            'existing_provider_secret_binding_missing')
    deployed = cf.call('GET', f'/workers/scripts/{WORKER}/deployments')['deployments'][0]
    versions = deployed.get('versions')
    require(isinstance(versions, list) and len(versions) == 1 and versions[0].get('percentage') == 100
            and UUID.fullmatch(str(versions[0].get('version_id', ''))), 'single_production_version_required')
    latest_entry = cf.call('GET', f'/workers/scripts/{WORKER}/versions')['items'][0]
    latest = latest_entry['id']
    require(UUID.fullmatch(latest), 'invalid_latest_version')
    annotations = latest_entry.get('annotations') or (latest_entry.get('metadata') or {}).get('annotations') or {}
    safe_annotations = {key: value for key, value in annotations.items()
        if key in ('workers/message', 'workers/tag') and isinstance(value, str)
        and len(value) <= 200 and re.fullmatch(r'(?i)hasla[A-Za-z0-9 .:;_()/+\-]*', value)} if isinstance(annotations, dict) else {}
    subdomain_state = cf.call('GET', f'/workers/scripts/{WORKER}/subdomain')
    require(subdomain_state.get('previews_enabled') is True, 'existing_version_urls_disabled')
    subdomain = cf.call('GET', '/workers/subdomain').get('subdomain')
    require(isinstance(subdomain, str) and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,62}', subdomain), 'invalid_workers_subdomain')
    return {'production_deployment_id': deployed['id'], 'production_versions': versions,
            'latest_uploaded_version': latest, 'latest_safe_annotations': safe_annotations, 'subdomain': subdomain,
            'compatibility_date': settings.get('compatibility_date'),
            'compatibility_flags': settings.get('compatibility_flags', []),
            'existing_provider_bindings_verified': True, 'version_urls_already_enabled': True}


def private_wandb(session, key):
    require(isinstance(key, str) and bool(key), 'existing_wandb_key_missing')
    response = session.post('https://api.wandb.ai/graphql', auth=('api', key),
        json={'query': 'query($e:String!,$p:String!){project(name:$p,entityName:$e){name access}}',
              'variables': {'e': ENTITY, 'p': PROJECT}}, timeout=25, allow_redirects=False)
    try:
        require(response.status_code == 200, 'wandb_privacy_http_' + str(response.status_code))
        value = response.json()
        require(not value.get('errors') and str((value.get('data', {}).get('project') or {}).get('access', '')).upper() == 'PRIVATE',
                'wandb_project_not_verified_private')
    finally:
        response.close()


def publish_private(sdk, value, name, artifact_type):
    os.environ.update(WANDB_CONSOLE='off', WANDB_DISABLE_CODE='true', WANDB_SILENT='true')
    with tempfile.TemporaryDirectory(prefix='hasla-teacher-private-') as directory:
        path = Path(directory) / ('preflight.json' if artifact_type == 'teacher-preflight' else 'final-proofs.json')
        path.write_bytes(canonical(value))
        run = sdk.init(entity=ENTITY, project=PROJECT, job_type='private-teacher-' + artifact_type,
                       name=name, config={'private': True, 'gpu_used': False, 'production_deployed': False},
                       settings=sdk.Settings(console='off', disable_code=True, disable_git=True, save_code=False,
                           disable_job_creation=True, x_disable_meta=True, x_disable_stats=True), dir=directory)
        try:
            artifact = sdk.Artifact(name, type=artifact_type, metadata={'private': True, 'production_deployed': False})
            artifact.add_file(str(path), name=path.name)
            uploaded = run.log_artifact(artifact, aliases=[])
            uploaded.wait(timeout=120)
            reference = uploaded.qualified_name
            require(isinstance(reference, str) and reference.startswith(ENTITY + '/' + PROJECT + '/')
                    and re.search(r':v[0-9]+\Z', reference), 'private_artifact_exact_version_missing')
            return reference
        finally:
            run.finish()


def load_preflight(sdk, reference):
    require(isinstance(reference, str) and re.fullmatch(re.escape(ENTITY + '/' + PROJECT + '/') +
            r'hasla-teacher-preflight-[0-9]+:v[0-9]+', reference), 'exact_private_preflight_artifact_required')
    artifact = sdk.Api().artifact(reference, type='teacher-preflight')
    entries = artifact.manifest.entries
    require(set(entries) == {'preflight.json'} and entries['preflight.json'].ref is None
            and 0 < entries['preflight.json'].size <= 64000, 'private_preflight_artifact_manifest_invalid')
    with tempfile.TemporaryDirectory(prefix='hasla-teacher-proof-') as directory:
        root = Path(artifact.download(root=directory))
        path = root / 'preflight.json'
        require(path.is_file() and not path.is_symlink(), 'private_preflight_artifact_invalid')
        return json.loads(path.read_text())


def make_upload(source, body, token, expires, snap):
    require(0 < len(source) <= 100000, 'teacher_source_size_invalid')
    bindings = [{'name': key, 'type': 'inherit'} for key in ('OPENAI_API_KEY', 'DEEPSEEK_API_KEY')]
    for name, text in (('HASLA_TEACHER_AUTH_SHA256', sha(token.encode())),
                       ('HASLA_TEACHER_EXPIRES_AT', str(expires)), ('HASLA_TEACHER_REQUEST_SHA256', sha(body))):
        bindings.append({'name': name, 'type': 'plain_text', 'text': text})
    metadata = {'main_module': 'teacher-entry.mjs', 'bindings': bindings,
                'compatibility_date': snap['compatibility_date'], 'compatibility_flags': snap['compatibility_flags'],
                'annotations': {'workers/message': 'Hasla bounded private teacher proof version; NEVER DEPLOY',
                                'workers/tag': 'hasla-teacher-private'}}
    return {'metadata': (None, json.dumps(metadata), 'application/json'),
            'teacher.js': ('teacher.js', source, 'application/javascript+module'),
            'teacher-entry.mjs': ('teacher-entry.mjs', ENTRY, 'application/javascript+module')}


def source_manifest(source):
    modules = [{'name': 'teacher.js', 'sha256': sha(source), 'bytes': len(source)},
               {'name': 'teacher-entry.mjs', 'sha256': sha(ENTRY), 'bytes': len(ENTRY)}]
    return {'uploaded_source_manifest': modules, 'uploaded_source_sha256': sha(canonical(modules)),
            'uploaded_source_hash_format': 'canonical_json_module_manifest_ascii_sorted_keys_v1'}


def same_production(cf, snap):
    deployed = cf.call('GET', f'/workers/scripts/{WORKER}/deployments')['deployments'][0]
    return deployed.get('id') == snap['production_deployment_id'] and deployed.get('versions') == snap['production_versions']


def bounded_result(response, task, nonce):
    require(response.status_code in (200, 207, 502), 'teacher_preview_http_' + str(response.status_code))
    require(len(response.content) <= MAX_RESPONSE_BYTES, 'teacher_response_too_large')
    value = response.json()
    require(isinstance(value, dict) and value.get('task') == task and value.get('nonce') == nonce
            and isinstance(value.get('results'), list) and len(value['results']) == 2, 'teacher_response_contract_invalid')
    require({r.get('provider'): r.get('requested_model') for r in value['results']} == MODELS, 'teacher_response_models_changed')
    allowed = {'provider', 'requested_model', 'reported_model', 'status', 'attempted', 'http_status',
               'response_id', 'usage', 'code', 'output', 'elapsed_ms', 'model', 'request_bytes',
               'request_sha256', 'finish_status', 'output_sha256', 'output_hash_format', 'fixture', 'requested_reasoning_profile'}
    require(set(value) <= {'version', 'task', 'nonce', 'status', 'both_providers_used', 'results',
                          'mathematics_verified', 'admitted_to_training', 'fixture', 'question', 'question_sha256'}
            and value.get('mathematics_verified') is False and value.get('admitted_to_training') is False
            and value.get('fixture') is False,
            'teacher_response_review_boundary_changed')
    require(all(isinstance(r, dict) and not set(r) - allowed and r.get('status') in ('ok', 'failed', 'not_configured')
                and r.get('fixture') is False
                for r in value['results']), 'teacher_response_provider_contract_invalid')
    # The fixed handler must already have stripped all reasoning/provider bodies.
    require(not any(k in canonical(value).decode().lower() for k in ('reasoning_content', 'reasoning_text', '<think>', 'api_key')),
            'teacher_response_contains_disallowed_fields')
    return value


def export_key(value):
    require(isinstance(value, str), 'root_export_public_key_required')
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, TypeError):
        raise TeacherControlError('root_export_public_key_invalid') from None
    require(len(raw) == 32 and base64.b64encode(raw).decode() == value, 'root_export_public_key_invalid')
    return raw


def export_encrypted(record, public_key, directory):
    from nacl.public import PublicKey, SealedBox
    target = Path(directory).absolute()
    require(not target.exists() and not any(path.is_symlink() for path in (target, *target.parents)),
            'fresh_runner_export_directory_required')
    require(not any((path / '.git').exists() for path in (target, *target.parents)), 'export_outside_repository_required')
    plain = canonical(record)
    cipher = SealedBox(PublicKey(public_key)).encrypt(plain)
    target.mkdir(parents=True)
    (target / 'final-proofs.sealed').write_bytes(cipher)
    manifest = {'schema': 1, 'algorithm': 'crypto_box_seal', 'cipher_file': 'final-proofs.sealed',
        'cipher_sha256': sha(cipher), 'plaintext_sha256': sha(plain), 'cipher_bytes': len(cipher),
        'export_public_key_sha256': sha(public_key), **{key: record[key] for key in
            ('code_commit', 'workflow_run_id', 'private_artifact', 'source_sha256', 'request_sha256')}}
    (target / 'manifest.json').write_bytes(canonical(manifest))
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('preflight', 'execute'), required=True)
    parser.add_argument('--task', choices=TASKS, default='heat_exchange_review')
    parser.add_argument('--prior-upper-krw', type=int, required=True)
    parser.add_argument('--preflight-artifact', default='')
    parser.add_argument('--export-public-key', default=os.environ.get('HASLA_TEACHER_EXPORT_PUBLIC_KEY', ''))
    parser.add_argument('--export-dir', default=os.environ.get('HASLA_TEACHER_EXPORT_DIR', ''))
    args = parser.parse_args(argv)
    import requests
    import wandb
    code_sha = os.environ.get('GITHUB_SHA', '')
    run_id = os.environ.get('GITHUB_RUN_ID', '')
    require(SHA.fullmatch(code_sha) and re.fullmatch(r'[0-9]+', run_id), 'github_run_identity_required')
    public_key = export_key(args.export_public_key)
    if args.mode == 'execute':
        require(bool(args.export_dir), 'runner_cipher_export_directory_required')
    budget = cost_bound(args.prior_upper_krw)
    session = requests.Session()
    private_wandb(session, os.environ.get('WANDB_API_KEY'))
    cf = Cloudflare(os.environ.get('CLOUDFLARE_API_TOKEN'), session)
    source = SOURCE.read_bytes()
    snap = snapshot(cf)
    proof = {'schema': 1, 'code_commit': code_sha, 'handler_sha256': sha(source), 'task': args.task,
             'snapshot': snap, 'budget': budget, 'private_project_verified': True,
             'export_public_key_sha256': sha(public_key),
             **source_manifest(source),
             'recorded_at': datetime.now(timezone.utc).isoformat(), 'gpu_used': False, 'production_deployed': False}
    if args.mode == 'preflight':
        reference = publish_private(wandb, proof, 'hasla-teacher-preflight-' + run_id, 'teacher-preflight')
        print(json.dumps({'event': 'hasla_teacher_private_preflight', 'status': 'ready',
                          'preflight_artifact': reference, 'budget': budget, 'production_mutated': False,
                          'production_deployment_id': snap['production_deployment_id'],
                          'production_versions': snap['production_versions'],
                          'latest_uploaded_version': snap['latest_uploaded_version'],
                          'latest_safe_annotations': snap['latest_safe_annotations'], 'source_sha256': sha(source),
                          'provider_inference_calls': 0, 'secret_values_exported': False}))
        return
    prior = load_preflight(wandb, args.preflight_artifact)
    require(all(prior.get(key) == proof[key] for key in ('schema', 'code_commit', 'handler_sha256', 'task', 'snapshot', 'budget',
                                                      'export_public_key_sha256', 'uploaded_source_manifest',
                                                      'uploaded_source_sha256', 'uploaded_source_hash_format')),
            'preflight_proof_changed')
    token, nonce = secrets.token_hex(32), secrets.token_hex(24)
    body = canonical({'task': args.task, 'nonce': nonce})
    expires = int(time.time()) + 600
    require(cf.call('GET', f'/workers/scripts/{WORKER}/versions')['items'][0]['id'] == snap['latest_uploaded_version']
            and same_production(cf, snap), 'worker_changed_before_version_upload')
    version = cf.call('POST', f'/workers/scripts/{WORKER}/versions?bindings_inherit=strict',
                      files=make_upload(source, body, token, expires, snap))
    version_id = version.get('id')
    require(isinstance(version_id, str) and UUID.fullmatch(version_id), 'teacher_version_identity_invalid')
    require(same_production(cf, snap), 'production_changed_after_version_upload')
    url = f'https://{version_id[:8]}-{WORKER}.{snap["subdomain"]}.workers.dev/__hasla_teacher'
    # Exactly one request; transport failures are never retried because billing
    # may have started even when the client receives no result.
    response = session.post(url, data=body, headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'},
                            timeout=240, allow_redirects=False)
    try:
        result = bounded_result(response, args.task, nonce)
    finally:
        response.close()
    unchanged = same_production(cf, snap)
    record = {'schema': 1, 'teacher_result': result, 'budget': budget, 'version_id': version_id,
              'source_sha256': sha(source), 'production_deployment_unchanged': unchanged,
              'gpu_used': False, 'secret_values_exported': False, 'expires_at': expires,
              'code_commit': code_sha, 'workflow_run_id': run_id, 'preflight_artifact': args.preflight_artifact,
              'request_sha256': sha(body), 'export_public_key_sha256': sha(public_key), **source_manifest(source)}
    reference = publish_private(wandb, record, 'hasla-teacher-final-' + run_id, 'teacher-final-proof')
    record['private_artifact'] = reference
    sealed_manifest = export_encrypted(record, public_key, args.export_dir)
    print(json.dumps({'event': 'hasla_teacher_private_completed', 'artifact': reference, 'version_id': version_id,
                      'production_deployment_unchanged': unchanged, 'gpu_used': False,
                      'providers': [{k: r.get(k) for k in ('provider', 'requested_model', 'reported_model', 'status', 'usage')} for r in result['results']],
                      'teacher_reserved_upper_krw': TEACHER_RESERVE_KRW, 'secret_values_exported': False}))
    print(json.dumps({'event': 'hasla_teacher_encrypted_export_ready', 'cipher_sha256': sealed_manifest['cipher_sha256'],
                      'plaintext_sha256': sealed_manifest['plaintext_sha256'],
                      'export_public_key_sha256': sealed_manifest['export_public_key_sha256'],
                      'plaintext_in_actions_artifacts': False}))
    require(unchanged, 'production_changed_concurrently')
    require(result.get('both_providers_used') is True and all(r['status'] == 'ok' for r in result['results']),
            'one_or_both_teacher_calls_failed_private_partial_receipt_preserved')


if __name__ == '__main__':
    try:
        main()
    except TeacherControlError as error:
        print(json.dumps({'event': 'hasla_teacher_private_failed', 'code': str(error), 'gpu_used': False,
                          'phase': error.phase, 'http_status': error.http_status,
                          'cloudflare_error_codes': error.cloudflare_error_codes}))
        raise SystemExit(1)
    except Exception as error:
        # Never print exceptions carrying provider responses, prompts or secrets.
        print(json.dumps({'event': 'hasla_teacher_private_failed', 'code': type(error).__name__, 'gpu_used': False}))
        raise SystemExit(1)
