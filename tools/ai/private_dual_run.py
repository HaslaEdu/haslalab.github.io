"""One dedicated, bounded Pod per selected model; cumulative batch accounting."""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import signal
import sys
import tempfile
import time
import traceback
from urllib.parse import parse_qs, urlsplit

import private_corpus_run as cloud
from role_config import get_role_config
from private_pod_train import (MAX_ARTIFACT_RAW_BYTES, artifact_payloads, decode_payload,
                               rows_from_payload, verify_partitions)
from training_budget import BudgetLedger, BudgetPolicy, PodQuote, reserve_run, settle_run, should_stop, validate_observed_pod


# This one authored cohort was independently reviewed by parent agent /root.
# These nonsensitive hashes bind the exact reviewed synthetic rows; copying a
# reviewer label or recomputing a tampered message hash cannot grant approval.
_AUTHORED_CHAT_COHORT = {'approved_dataset_version': 'gemma-role-v6-approved-20261105',
 'authoring_agent': 'agent:codex/root/audit_native_wrapper',
 'metadata_keys': ['authored',
                   'authoring_agent',
                   'community_observation',
                   'context',
                   'curriculum_mode',
                   'curriculum_spec_sha256',
                   'dataset_version',
                   'derivation',
                   'domain',
                   'family_id',
                   'group_id',
                   'human_reviewed',
                   'input_language',
                   'language_origin',
                   'messages_sha256',
                   'old_synthetic_seed',
                   'output_language',
                   'provenance_type',
                   'review_receipt_sha256',
                   'review_status',
                   'reviewer',
                   'scientifically_verified',
                   'source_curriculum_version',
                   'source_dataset_version',
                   'source_refs',
                   'split',
                   'synthetic',
                   'target_role',
                   'task'],
 'provenance_type': 'authored_role_curriculum_v1',
 'review_receipt_sha256': 'd166bf573eda9ca5e458cce6ada3b61212521ade4f3364d639767554b997de94',
 'reviewer': 'agent:codex/root',
 'row_sha256': {'authored-gemma-role-v6-0001': 'a00459b72c142f8b2d1bf3a9c01196d79b7a3b66c8be9c6e7abc176985d453e5',
                'authored-gemma-role-v6-0002': '244cf1e1fffb1fd853196c6ce1e3f842f27dbd214e8180caeb05fc516270d45b',
                'authored-gemma-role-v6-0003': 'd5b31c901f5bf0475d1f0fc0b2d6400f4bf34e624492e024d7417abfa8813637',
                'authored-gemma-role-v6-0004': '3435a46197e54652e0f707ed5df42a5e4703cbef9d9afb97145431c1a0f428ac',
                'authored-gemma-role-v6-0005': '8ad0fcf96dd6b8388f8c8721e1a05c5a5560f79a56af72ccefcdb6c2d59d08d2',
                'authored-gemma-role-v6-0006': 'b6b47b5771f290e4bb681bee86ab4a109dc94f32da4ab85dc4683b3fdc401977',
                'authored-gemma-role-v6-0007': 'efc71b2a82becb8109565623d0a467c1cad2afb5743be9525f1fe56578f277a3',
                'authored-gemma-role-v6-0008': '2566de0014fb0709957416619c436c0e72d868e37d4c1695c4464240a04c18a9',
                'authored-gemma-role-v6-0009': '47dc1cf27642f2736a5ceeb5444da1471baac999256b548d9beb46357d201446',
                'authored-gemma-role-v6-0010': '30684092c596de6c54ef0296f7ef9f87ab1315bbefdcfc821908cee2b192533d',
                'authored-gemma-role-v6-0011': 'b961b172f53836b871ec97220c3aa767b1158f2f645ba14abd5c5e57ca386963',
                'authored-gemma-role-v6-0012': '7edef44aefc301663938d8ae3876dd9be3c9d7a345ab0cf09adb325967c0184e',
                'authored-gemma-role-v6-0013': '3ff65ce48fefb87d04928c51990f50408990a3942098301da8fcdc295882d282',
                'authored-gemma-role-v6-0014': '8076c2e48d2a37043d2052ed6da17011c0a6866b87d33a437fc1bf9648c9a283',
                'authored-gemma-role-v6-0015': '7bd3cff05940188def7594e79828e163ef52ed9762a5874afa8a586c156f9d0b',
                'authored-gemma-role-v6-0016': '6d8a598b66be086c1c2b4f703790c87d28c567d9ad0f26d0eed6a545ad16722d',
                'authored-gemma-role-v6-0017': '09b46a4dea4e387ba5ac827b9fd5b44bd9ba2e2b6dea5ab3867313bcae68ab2d',
                'authored-gemma-role-v6-0018': '2379e0f2aea88e77941813f1a0b2a7720810f795469f7829b06b132b8d2d99d7',
                'authored-gemma-role-v6-0019': 'a1543230e13d9843def4545d26b9b9c6bbe173bb958200a04c0eef84d9ce905c',
                'authored-gemma-role-v6-0020': 'a42b9a7eb715a9d474a149e0ca15a806ba311e7c81ce3890c113eba94bea51b5',
                'authored-gemma-role-v6-0021': 'c7b749512861da1599757f5b38fe830c2bc0a9f848124ec72871c836a3f32056',
                'authored-gemma-role-v6-0022': 'b9b0c8ef2a493bb130ba1c36431830116d736fb337e5b5277ce4ada7ff7ca882',
                'authored-gemma-role-v6-0023': '0ee596566742293aad333cdac487811133997407185b78eb1a26783185cad999',
                'authored-gemma-role-v6-0024': '7ec6c7de91897f2aa543c932941e7df3537005d086f7f9b7734c2163e484bf07',
                'authored-gemma-role-v6-0025': '5084db7e57e2246be3a39bd4ec71f9c2926dd1d5841499bfcc37d411b7f6b458',
                'authored-gemma-role-v6-0026': '3408d8520365eb023aab92d7407694baae7bdce18191a0bee75aadea692a480e',
                'authored-gemma-role-v6-0027': '896f2a941851d52dd5d98e56983a2c1eebf631b80d950ea3b5bbdca774833288',
                'authored-gemma-role-v6-0028': '15ba82b68e43beca025e5ded1087152623cbf3c2ce6bbfb475e4eccd2b58719b',
                'authored-gemma-role-v6-0029': '748a406ee4720023239c48d727d37479c1a30dafa5b619389bd31874cf81a49a',
                'authored-gemma-role-v6-0030': '043dd9be4ec387802aa9881e2477590871c05c177dee1b5cb99978d66a32a60a',
                'authored-gemma-role-v6-0031': 'eff28ccf7c0f339da0ddc10bb7fbc79bfc4628c0fd62bb32ca0cb9ff496aeae5',
                'authored-gemma-role-v6-0032': '90769194dc3bce74ce50c7b3e01f5c4a7a0d0a7b4187a343512b3cc637c852b1',
                'authored-gemma-role-v6-0033': '12ae750fb12317c5b7bd3b78dbbd5770505215f8db84be8421212f4ed78a3b4a',
                'authored-gemma-role-v6-0034': 'd4382293f4d207f6b72d04e89a8d60e621138856fbb7981df95f04d7c5d5029f',
                'authored-gemma-role-v6-0035': '019b01f168be649c202dca7a34121493ae733f2a772a898e843a30d655fbccfc',
                'authored-gemma-role-v6-0036': 'c122513a1cd8d8968033dff8b3551fc486e0658d700a1f87a7139093a8aba2ab',
                'authored-gemma-role-v6-0037': 'a1b77ffb69aed95a2c0deb813ba878a83e5ace9739e01f0a32b043836331b1d5',
                'authored-gemma-role-v6-0038': '2f413869dfe1d70cf6d7e3926ab4d4bcfee4c2f7a5bf95bc68a0591faa62d1e4',
                'authored-gemma-role-v6-0039': 'e184369ac6b4380695e7fa650b5afcde9c959b72a64378de1f109f7e9638ad61',
                'authored-gemma-role-v6-0040': 'd1bb229dce8275ce3a5ffc547683ee59e742b731e876b19bc8fa410a0c66a13f',
                'authored-gemma-role-v6-0041': 'a71bae3db51dd6847ac9ffe53ae42df1b2fcfede6541615a84511ea2bb6ef624',
                'authored-gemma-role-v6-0042': 'b5e0c82802b4c49b46feab37d45ef997172b4736b1a7b69b6c598852b9ac0889',
                'authored-gemma-role-v6-0043': 'ec1705879779545a2f28f1c95eff1956eb6ec4a9bce832575a4ef2d96fa3d046',
                'authored-gemma-role-v6-0044': '32ed3b722cf6612910fd58cca6602566df4b232db8c6cbdd94bbca4c2affce27',
                'authored-gemma-role-v6-0045': '5126c92f7e0f3b4e6230c6e24732b030e00f0e2a4f7535ad271f03da43d0152d',
                'authored-gemma-role-v6-0046': '834e9c142a270aae9440c8d9d716e2e2a311f062b9fe5b3645cdc90e3b159f0b',
                'authored-gemma-role-v6-0047': '7807e0375d6873834ec3ae063c6df252b879c18cdc0f04fe264900ad5b27c2aa',
                'authored-gemma-role-v6-0048': '3d87cf1a9275a286f701d7943e38d03b062ba23c8c28cfb1b3f850b8e6abaced',
                'authored-gemma-role-v6-0049': '42f79022c9cd1f58e007c4f195e8a84972dd858296b640dea7ba52459a2795b9',
                'authored-gemma-role-v6-0050': 'e6c603f2c6b167f3fc8440fe1dd094a73244bf8e188b1f1c118d8ce0e54e222e',
                'authored-gemma-role-v6-0051': '5b04d5d010a260bc9bc25b1bbb624d38f26a33bed3f6a9fabbef5cefbefe9eb7',
                'authored-gemma-role-v6-0052': '6ff0f9d6820f16419c0ef70cf53ddf2e8b99f43b0dea7df01d0b7f56a518cf2d',
                'authored-gemma-role-v6-0053': '151f82ed711a2a835bd809bd356b3bc7d6ffe325db8fbcfec1a419456e697b7e',
                'authored-gemma-role-v6-0054': '3120c174cc625a4d60628b1f0fd2fe447e8764821dc1d919fe6439ec4534c1dd',
                'authored-gemma-role-v6-0055': '8a0990fe895df92ea664cd90a26ebd28f1d72afb79b680e16c5e6b8aaab04209',
                'authored-gemma-role-v6-0056': '6164f938cd976e30cac336a9d6846e0d4a2fa6eb3a773aba27b2c01b2b643db4',
                'authored-gemma-role-v6-0057': 'c81cadf27c539f800c95a38963ecd28c02ed5ec69ae1ffa5c12de92e475d8c3b',
                'authored-gemma-role-v6-0058': '360768f62a0d4dd2f145ce86e9fb7184db2f2889d1eae3ad939e61348917bce2',
                'authored-gemma-role-v6-0059': '1b318472b33e7c2e23f5dae501c61e6d53183d93c626b1c990845ad5a7c693de',
                'authored-gemma-role-v6-0060': '432acd1ec89e09541e576608ab2b4f4a26601b9b97e39b97f9b207cdecec2b86',
                'authored-gemma-role-v6-0061': '1d8c57efdef04ce6bb7ea86bcf8cec4666be608299f5359e2339f3053549b3dc',
                'authored-gemma-role-v6-0062': '6deb88cf1032d17aceb5e946399865e05f1957d45922e433a60453deeca427fe',
                'authored-gemma-role-v6-0063': '036fb66546fbfff4340af5a3994c683c781def4c265e2e414a43afd413fcdfd6',
                'authored-gemma-role-v6-0064': '3249b351b05a1d579258740f7bff3d486aa7b97d2ab47690f0feca562787cd9d'},
 'source_curriculum_version': 'gemma-role-v6-draft-20261105',
 'source_dataset_version': 'gemma-chat-v5-approved-20261105',
 'source_refs': [{'path': 'community/src/ai-role-contract.js',
                  'scope': 'repository_contract_not_live_availability',
                  'sha256': '7c9157deec9c8da6fd9ad64245b556b5d49baf0133b775147052b6c13660d6ba'},
                 {'path': 'community/src/ai-assistant.js',
                  'scope': 'repository_contract_not_live_availability',
                  'sha256': 'a23b9794303815060f456aba3238267c68af040b752a46af056ecb65d9a06b6a'}],
 'spec_sha256': '51179a8984461d63dd5215ed9731c7320a211aa6da6f103912b2fc0d0fd36497'}
_AUTHORED_CHAT_MODES = frozenset(('common_chat', 'platform_help', 'intent_classifier', 'rubric_missing',
                                'visual_evidence_missing', 'adapter_missing', 'protected_formatter'))
_AUTHORED_CHAT_TASKS = frozenset(('create', 'solve', 'explain', 'concept', 'grade', 'feedback'))
_AUTHORED_CHAT_FAMILIES = frozenset(('chat:greeting', 'chat:motivation', 'chat:scope', 'chat:web_honesty',
    'platform:competitions', 'platform:notes', 'platform:bank', 'platform:community',
    'intent:create', 'intent:solve', 'intent:explain', 'intent:concept', 'intent:grade', 'intent:feedback',
    'adapter:unavailable', 'formatter:protected'))


def _authored_chat_require(value):
    if not value:
        raise ValueError('Gemma authored curriculum requires exact independently approved provenance')


def _authored_chat_sha(value):
    try:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf8')
    except (TypeError, ValueError, UnicodeError):
        raise ValueError('Gemma authored curriculum canonical content is invalid') from None
    return hashlib.sha256(raw).hexdigest()


def validate_authored_chat(row):
    """A separate, exact reviewed cohort; never an exception to author filtering."""
    trusted = _AUTHORED_CHAT_COHORT
    _authored_chat_require(isinstance(row, dict) and set(row) == {'id', 'messages', 'metadata', 'review_status'})
    meta = row['metadata'];messages = row['messages']
    _authored_chat_require(isinstance(meta, dict) and set(meta) == set(trusted['metadata_keys'])
        and row['review_status'] == 'approved' and meta['review_status'] == 'approved'
        and meta['provenance_type'] == trusted['provenance_type']
        and meta['derivation'] == 'authored_repository_contract'
        and meta['authored'] is True and meta['synthetic'] is True and meta['community_observation'] is False
        and meta['old_synthetic_seed'] is False and meta['human_reviewed'] is False and meta['scientifically_verified'] is False
        and meta['target_role'] == 'chat' and meta['split'] in ('train', 'validation')
        and meta['dataset_version'] == trusted['approved_dataset_version']
        and meta['source_dataset_version'] == trusted['source_dataset_version']
        and meta['source_curriculum_version'] == trusted['source_curriculum_version']
        and meta['authoring_agent'] == trusted['authoring_agent'] and meta['reviewer'] == trusted['reviewer']
        and meta['reviewer'] != meta['authoring_agent']
        and meta['review_receipt_sha256'] == trusted['review_receipt_sha256']
        and meta['curriculum_spec_sha256'] == trusted['spec_sha256']
        and meta['source_refs'] == trusted['source_refs'])
    _authored_chat_require(isinstance(meta['curriculum_mode'], str) and meta['curriculum_mode'] in _AUTHORED_CHAT_MODES
        and meta['domain'] in ('haslalab', 'hasla_nonsul') and meta['input_language'] in ('ko', 'en')
        and meta['output_language'] == meta['input_language']
        and meta['language_origin'] == ('authored_english' if meta['input_language'] == 'en' else 'authored_korean')
        and isinstance(meta['family_id'], str) and meta['family_id'] in _AUTHORED_CHAT_FAMILIES
        and meta['group_id'] == 'authored-role-family:' + meta['family_id'])
    mode, task = meta['curriculum_mode'], meta['task']
    allowed_tasks = (_AUTHORED_CHAT_TASKS if mode == 'intent_classifier' else
        {'grade', 'feedback'} if mode == 'rubric_missing' else {'grade'} if mode == 'visual_evidence_missing' else
        {'solve', 'grade'} if mode == 'protected_formatter' else {None})
    _authored_chat_require((task is None or isinstance(task, str)) and task in allowed_tasks and isinstance(meta['context'], dict)
        and (mode != 'platform_help' or meta['domain'] == 'haslalab'))
    _authored_chat_require(isinstance(messages, list) and len(messages) == 3
        and all(isinstance(item, dict) and set(item) == {'role', 'content'}
                and item['role'] == expected and isinstance(item['content'], str) and item['content'].strip()
                for item, expected in zip(messages, ('system', 'user', 'assistant')))
        and meta['messages_sha256'] == _authored_chat_sha(messages))
    # Whole-row binding covers every reviewed fixture/context field as well as
    # IDs, family, split, source references and the fixed review receipt.
    _authored_chat_require(isinstance(row['id'], str) and row['id'] in trusted['row_sha256']
        and _authored_chat_sha(row) == trusted['row_sha256'][row['id']])


def validate_source_lineage(rows, role):
    """Require observed chat exchanges or traceable HaslaLab educational sources."""
    for row in rows:
        meta = row.get('metadata') or {}
        if role == 'chat':
            if 'provenance_type' in meta:
                if meta['provenance_type'] != 'authored_role_curriculum_v1':
                    raise ValueError('unknown Gemma chat provenance type')
                validate_authored_chat(row)
                continue
            author_filter = meta.get('author_filter') or {}
            source = urlsplit(str(meta.get('source_url', '')))
            if source.hostname == 'gall.dcinside.com' and parse_qs(source.query).get('id') == ['physicalscience']:
                raise ValueError('the user excluded the 물리학 gallery; 물리학과 is a different allowed gallery')
            if (meta.get('derivation') != 'paraphrase_observed_exchange'
                    or meta.get('reconstructed') is not True
                    or meta.get('old_synthetic_seed') is not False
                    or not meta.get('observed_reply_link')
                    or not meta.get('reviewer')
                    or meta.get('review_status') != 'approved'
                    or not meta.get('collected_at')
                    or not isinstance(author_filter, dict)
                    or author_filter.get('policy_version') != 'exclude-bugiu-v1'
                    or author_filter.get('post_author_checked') is not True
                    or author_filter.get('selected_reply_authors_checked') is not True
                    or author_filter.get('reply_branch_checked') is not True
                    or author_filter.get('excluded_author_present') is not False
                    or not re.fullmatch(r'https://(?:orbi\.kr/[0-9]+|gall\.dcinside\.com/(?:m?gallery/)?board/view/\?id=[A-Za-z0-9_]+&no=[0-9]+)', str(meta.get('source_url', '')))
                    or any(not re.fullmatch(r'[a-f0-9]{64}', str(meta.get(key, '')))
                           for key in ('question_sha256', 'answer_sha256'))):
                raise ValueError('Gemma requires source-grounded exchanges with the current author exclusion checks')
        else:
            drive = meta.get('drive_provenance')
            drive_ok = (isinstance(drive, dict) and bool(drive.get('drive_file_id'))
                        and re.fullmatch(r'[a-f0-9]{64}', str(drive.get('local_original_pdf_sha256', '')))
                        and bool(meta.get('page_number')) and meta.get('scan_suspect') is not True)
            source = meta.get('haslalab_provenance')
            native_ok = (isinstance(source, dict) and bool(source.get('source_id'))
                         and bool(source.get('source_family'))
                         and re.fullmatch(r'[a-f0-9]{64}', str(source.get('local_source_sha256', '')))
                         and source.get('extraction') in ('native', 'canonical_body')
                         and bool(source.get('original_locator') or meta.get('page_number'))
                         and meta.get('target_role') == 'solver' and bool(meta.get('group_id'))
                         and meta.get('scan_suspect') is False
                         and meta.get('content_type') in ('textbook', 'competition_problem', 'school_problem',
                                                          'solution', 'research_paper'))
            if not drive_ok and not native_ok:
                raise ValueError('QwQ requires native text or canonical source bodies with checked provenance')


def load_inputs(env):
    manifest = json.loads(env['HASLA_DUAL_MANIFEST'])
    if not isinstance(manifest, dict) or not isinstance(manifest.get('roles'), dict):
        raise ValueError('invalid model manifest')
    selected = manifest.get('selected_roles', ['chat', 'solver'])
    if (not isinstance(selected, list) or not 1 <= len(selected) <= 2
            or any(role not in ('chat', 'solver') for role in selected) or len(set(selected)) != len(selected)):
        raise ValueError('invalid selected model roles')
    if any(role not in manifest['roles'] for role in selected):
        raise ValueError('selected model input is missing')
    for role in selected:
        resource_settings(manifest, role)
        initial = manifest['roles'][role].get('initial_adapter')
        if initial is not None:
            from private_resume_adapter import validate_spec
            if role != 'solver' or not re.fullmatch(r'[a-f0-9]{64}', manifest.get('resume_script_sha256', '')):
                raise ValueError('continuation requires a solver adapter and pinned helper')
            manifest['roles'][role]['initial_adapter'] = validate_spec(initial, get_role_config(role))
    for key in ('train_script_sha256', 'role_config_sha256', 'pod_script_sha256', 'dual_pod_sha256'):
        if not re.fullmatch(r'[a-f0-9]{64}', manifest.get(key, '')):
            raise ValueError('pinned code checksums are required')
    if not re.fullmatch(r'[0-9a-f]{40}', env.get('GITHUB_SHA', '')):
        raise ValueError('a pinned public commit is required')
    payloads = {}
    for role in selected:
        spec = manifest['roles'][role]
        expected = spec.get('format')
        if expected not in (('chat',) if role == 'chat' else ('text', 'chat')):
            raise ValueError('role and corpus formats do not match')
        if spec.get('input_artifact'):
            reference = spec['input_artifact']
            if (not isinstance(reference, str) or not re.fullmatch(
                    r'[A-Za-z0-9_.-]+/hasla-ai-private-training/[A-Za-z0-9_.-]+:v[0-9]+', reference)):
                raise ValueError('immutable private staged input is required')
            for split in ('train', 'validation'):
                item = spec.get(split, {})
                if (type(item.get('records')) is not int or not 1 <= item['records'] <= 1000000
                        or type(item.get('raw_bytes')) is not int or not 0 < item['raw_bytes'] <= MAX_ARTIFACT_RAW_BYTES
                        or not re.fullmatch(r'[a-f0-9]{64}', str(item.get('raw_sha256', '')))):
                    raise ValueError('invalid private staged input inventory')
            payloads[role] = {'HASLA_INPUT_ARTIFACT': reference}
            continue
        data_env = {}
        for split, target in (('train', 'HASLA_DATA'), ('validation', 'HASLA_VALIDATION')):
            source = f'HASLA_{role.upper()}_' + ('DATA' if split == 'train' else 'VALIDATION')
            item = spec[split]
            count = item.get('parts')
            if type(count) is not int or not 1 <= count <= 16:
                raise ValueError('invalid private shard count')
            values = []
            for i in range(count):
                value = env.get(f'{source}_{i:02d}', '')
                if not value or len(value) > 40000:
                    raise ValueError('missing or oversized encrypted input shard')
                values.append(value)
                data_env[f'{target}_{i:02d}'] = value
            if hashlib.sha256(''.join(values).encode()).hexdigest() != item['encoded_sha256']:
                raise ValueError('private encoded input checksum mismatch')
            data_env[target + '_PARTS'] = str(count)
            data_env[target + '_SHA256'] = item['raw_sha256']
        training = rows_from_payload(decode_payload(data_env), 'train', expected)
        validation = rows_from_payload(decode_payload(data_env, 'HASLA_VALIDATION'), 'validation', expected)
        validate_source_lineage(training + validation, role)
        verify_partitions(training, validation)
        if len(training) != spec['train']['records'] or len(validation) != spec['validation']['records']:
            raise ValueError('private record count mismatch')
        payloads[role] = data_env
    return manifest, payloads


def verify_staged_inputs(manifest, payloads, env, entity):
    """Validate full private artifact bytes on CPU before any paid Pod is created."""
    external = [role for role in manifest['selected_roles'] if manifest['roles'][role].get('input_artifact')]
    initial_roles = [role for role in manifest['selected_roles'] if manifest['roles'][role].get('initial_adapter')]
    if not external and not initial_roles:
        return
    from private_verify_adapter import quiet_sdk
    with tempfile.TemporaryDirectory(prefix='hasla-staged-input-') as directory:
        with quiet_sdk(Path(directory)):
            import wandb
            private = {'entity': entity, 'project': cloud.PROJECT, 'access': 'PRIVATE',
                       'base_url': 'https://api.wandb.ai'}
            for role in external:
                spec = manifest['roles'][role]
                settings = {'WANDB_API_KEY': env['WANDB_API_KEY'], 'WANDB_ENTITY': entity,
                            'WANDB_PROJECT': cloud.PROJECT, 'ROLE': role, 'HASLA_DATA_FORMAT': spec['format'],
                            'HASLA_INPUT_ARTIFACT': spec['input_artifact'],
                            'HASLA_DATA_SHA256': spec['train']['raw_sha256'],
                            'HASLA_VALIDATION_SHA256': spec['validation']['raw_sha256']}
                training_raw, validation_raw = artifact_payloads(settings, Path(directory) / role, wandb, private)
                rows = []
                for split, raw in (('train', training_raw), ('validation', validation_raw)):
                    if raw is None or len(raw) != spec[split]['raw_bytes']:
                        raise ValueError('private staged input byte count mismatch')
                    values = rows_from_payload(raw, split, spec['format'])
                    if len(values) != spec[split]['records']:
                        raise ValueError('private staged input row count mismatch')
                    validate_source_lineage(values, role)
                    rows.append(values)
                verify_partitions(*rows)
            if initial_roles:
                from private_resume_adapter import download_initial_adapter
                api = wandb.Api(api_key=env['WANDB_API_KEY'], overrides={'base_url': private['base_url']}, timeout=30)
                def checked_privacy(requested):
                    if requested != entity:
                        raise ValueError('initial adapter must belong to the same private project')
                    observed = cloud.wandb_query('query($e:String!,$p:String!){project(name:$p,entityName:$e){name access}}',
                                                 {'e': entity, 'p': cloud.PROJECT}).get('project') or {}
                    if observed.get('name') != cloud.PROJECT or observed.get('access') != 'PRIVATE':
                        raise ValueError('initial adapter project is not PRIVATE')
                    return True
                for role in initial_roles:
                    download_initial_adapter(manifest['roles'][role]['initial_adapter'], get_role_config(role),
                        Path(directory) / (role + '-initial'), api, checked_privacy)


def resource_settings(manifest, role):
    """Validate one immutable role's budget, GPU preferences and total Pod time."""
    if role not in ('chat', 'solver') or not isinstance(manifest['roles'].get(role), dict):
        raise ValueError('invalid selected model resources')
    policy = BudgetPolicy(fx_krw_per_usd_upper=2000, budget_krw=manifest.get('budget_krw'),
        authorized_budget_krw=manifest.get('authorized_budget_krw', 30000), reserve_krw=5000, tax_multiplier='1.15')
    if 'prior_upper_krw' not in manifest:
        raise ValueError('cumulative prior budget is required')
    ledger = BudgetLedger(policy, prior_spend_krw=manifest['prior_upper_krw'])
    spec = manifest['roles'][role]
    # Pure profile validation precedes any provider or corpus request.
    profile = spec.get('training_profile')
    get_role_config(role, profile)
    maximum = 1800 if role == 'chat' else 14400
    seconds = spec.get('runtime_seconds', 1800 if role == 'chat' else 3600)
    if type(seconds) is not int or not 660 <= seconds <= maximum:
        raise ValueError('role runtime must include setup/upload and stay within its time ceiling')
    low_memory_gpus = ['NVIDIA A100-PCIE-40GB', 'NVIDIA L40S', 'NVIDIA L40', 'NVIDIA A40']
    legacy_gpus = [gpu for gpu in cloud.GPU_IDS if gpu not in low_memory_gpus]
    default_gpus = ([*legacy_gpus[2:], legacy_gpus[1], legacy_gpus[0]] if role == 'chat' else legacy_gpus)
    if profile is not None:
        default_gpus = low_memory_gpus
    gpu_ids = spec.get('gpu_ids', default_gpus)
    if (not isinstance(gpu_ids, list) or not gpu_ids
            or any(not isinstance(gpu, str) or gpu not in cloud.GPU_IDS for gpu in gpu_ids)
            or len(set(gpu_ids)) != len(gpu_ids)):
        raise ValueError('only configured training GPUs may be preferred')
    if (profile is not None and any(gpu not in low_memory_gpus for gpu in gpu_ids)
            or profile is None and any(gpu in low_memory_gpus for gpu in gpu_ids)):
        raise ValueError('40/48GB GPU eligibility requires the explicit low-memory Gemma profile')
    quote = PodQuote(gpu_usd_per_hour_upper=spec.get('gpu_usd_per_hour_upper', 4), container_disk_gb=200, volume_disk_gb=0)
    ceiling = 6 if role == 'chat' and profile is None else 4
    if quote.gpu_usd_per_hour_upper > ceiling:
        raise ValueError(f'role GPU hourly ceiling exceeds USD{ceiling}')
    return ledger, quote, seconds, gpu_ids


def verify_pinned_scripts(manifest, commit):
    files = {'train_script_sha256': 'train_lora.py', 'role_config_sha256': 'role_config.py',
             'pod_script_sha256': 'private_pod_train.py', 'dual_pod_sha256': 'private_dual_pod.py'}
    if any(manifest['roles'][role].get('initial_adapter')
           for role in manifest.get('selected_roles', list(manifest.get('roles', {})))):
        files['resume_script_sha256'] = 'private_resume_adapter.py'
    for key, filename in files.items():
        url = f'https://raw.githubusercontent.com/HaslaEdu/haslalab.github.io/{commit}/tools/ai/{filename}'
        response = cloud.requests.get(url, timeout=20)
        if (response.status_code != 200 or len(response.content) > 256 * 1024
                or hashlib.sha256(response.content).hexdigest() != manifest[key]):
            raise ValueError('pinned public code checksum mismatch: ' + filename)
    cloud.safe_event('public_code_verified', files=len(files), commit=commit)


def main():
    env = os.environ
    cloud.E = env
    if '--cleanup' in sys.argv:
        return cloud.cleanup()
    manifest, payloads = load_inputs(env)
    selected_roles = manifest.get('selected_roles', ['chat', 'solver'])
    if len(selected_roles) != 1 and env.get('HASLA_PREFLIGHT_ONLY') != 'true':
        raise ValueError('each paid Pod must select exactly one model role')
    role = selected_roles[0]
    ledger, quote, run_seconds, preferred_gpus = resource_settings(manifest, role)
    for key in ('RUNPOD_API_KEY', 'WANDB_API_KEY', 'HF_TOKEN'):
        if not env.get(key):
            raise ValueError('missing required training credential')
    verify_pinned_scripts(manifest, env['GITHUB_SHA'])
    run_id = cloud.PREFIX + env['GITHUB_RUN_ID']
    if any(str(p.get('name', '')).startswith(cloud.PREFIX) for p in cloud.runpod('GET', '/pods')):
        raise RuntimeError('an earlier private Pod remains; confirm cleanup before another role')
    selected_gpu = cloud.capacity_preflight(preferred_gpu_ids=preferred_gpus,
                                            hourly_ceiling=quote.gpu_usd_per_hour_upper)
    if selected_gpu not in preferred_gpus:
        raise ValueError('selected GPU differs from the frozen role policy')
    bases = {'chat': 'google/gemma-4-26B-A4B-it', 'solver': 'Qwen/QwQ-32B'}
    for role in selected_roles:
        model = bases[role]
        response = cloud.requests.head(f'https://huggingface.co/{model}/resolve/main/config.json',
            headers={'Authorization': 'Bearer ' + env['HF_TOKEN']}, allow_redirects=True, timeout=20)
        if not response.ok:
            cloud.safe_event('model_access_failed', role=role, http_status=response.status_code)
            raise RuntimeError('base model access check failed')
    entity = cloud.private_project()
    verify_staged_inputs(manifest, payloads, env, entity)
    ledger = reserve_run(ledger,
                         run_id, 'dual' if len(selected_roles) == 2 else selected_roles[0], quote,
                         time.monotonic(), run_seconds, run_seconds)
    plan = ledger.runs[-1].plan
    if plan.run_seconds < 660:
        raise ValueError('remaining budget cannot cover setup, training and upload')
    budget = int(ledger.policy.budget_krw)
    cloud.safe_event('dual_preflight', roles={r: {'format': s['format'], 'training_records': s['train']['records'],
        'validation_records': s['validation']['records']} for r, s in manifest['roles'].items() if r in selected_roles},
        selected_roles=selected_roles, dedicated_pod=True, budget_krw=budget,
        prior_upper_krw=str(ledger.prior_spend_krw), reserved_upper_krw=str(plan.reserved_krw), runtime_seconds=plan.run_seconds)
    if env.get('HASLA_PREFLIGHT_ONLY') == 'true':
        return 0
    jobs = []
    for role in selected_roles:
        spec = manifest['roles'][role]
        if spec.get('input_artifact'):
            input_ref = payloads[role]
            cloud.safe_event('private_input_ready', artifact=spec['input_artifact'], raw_files=2, public=False)
        else:
            input_ref = cloud.publish_private_input(entity, run_id + '-' + role, {**spec, 'role': role}, payloads[role])
        jobs.append({'role': role, 'format': spec['format'], 'run': run_id + '-' + role,
                     'input_artifact': input_ref['HASLA_INPUT_ARTIFACT'],
                     'training_sha256': spec['train']['raw_sha256'],
                     'validation_sha256': spec['validation']['raw_sha256'],
                     'runtime_seconds': plan.run_seconds - 600})
        if spec.get('training_profile') is not None:
            jobs[-1]['training_profile'] = spec['training_profile']
    pod_env = {'HASLA_ROLE_JOBS': json.dumps(jobs, separators=(',', ':')), 'REPO_SHA': env['GITHUB_SHA'],
        'HASLA_TRAIN_SCRIPT_SHA256': manifest['train_script_sha256'],
        'HASLA_ROLE_CONFIG_SHA256': manifest['role_config_sha256'],
        'HASLA_POD_SCRIPT_SHA256': manifest['pod_script_sha256'],
        'HF_TOKEN': env['HF_TOKEN'], 'WANDB_API_KEY': env['WANDB_API_KEY'],
        'WANDB_ENTITY': entity, 'WANDB_PROJECT': cloud.PROJECT,
        'WANDB_CONSOLE': 'off', 'WANDB_DISABLE_CODE': 'true'}
    url = f'https://raw.githubusercontent.com/HaslaEdu/haslalab.github.io/{env["GITHUB_SHA"]}/tools/ai/private_dual_pod.py'
    start = ('set -eu; mkdir -p /workspace; export PIP_DISABLE_PIP_VERSION_CHECK=1; '
             'pip install -q --upgrade unsloth trl datasets wandb >/workspace/install.log 2>&1; '
             f'curl -fsSL {url} -o /workspace/private_dual_pod.py; '
             f'echo "{manifest["dual_pod_sha256"]}  /workspace/private_dual_pod.py" | sha256sum -c - >/dev/null; '
             'python /workspace/private_dual_pod.py')
    command = 'bash -lc ' + shlex.quote(f'timeout --signal=TERM --kill-after=30s {plan.run_seconds - 120}s bash -lc ' + shlex.quote(start))
    pod, attempted, results, failures = None, False, {}, {}
    try:
        attempted = True
        cloud.safe_event('gpu_request', api='rest_v2', gpu=selected_gpu, roles=selected_roles,
                         private_environment_bytes=sum(len(v) for v in pod_env.values()))
        pod = cloud.graphql_create_pod(run_id, pod_env, command, gpu_id=selected_gpu)
        pod = cloud.runpod('GET', '/pods/' + pod['id'])
        validate_observed_pod(plan, pod)
        if (pod.get('gpu') or {}).get('id') != selected_gpu:
            raise ValueError('created GPU differs from the selected role GPU')
        cloud.safe_event('pod_started', pod_id=pod['id'], hourly_usd=pod['costPerHr'], roles=selected_roles)
        last_roles = []
        while not should_stop(plan, time.monotonic()):
            for job in jobs:
                if job['role'] in results or job['role'] in failures:
                    continue
                remaining = float(plan.deadline_monotonic) - time.monotonic()
                if remaining <= 0:
                    break
                row = cloud.result_for(entity, job['run'], timeout=min(10, remaining))
                if row:
                    if row.get('status') != 'uploaded':
                        cloud.safe_event('role_failed', role=job['role'], stage=row.get('stage'), error_code=row.get('error_code'))
                        failures[job['role']] = row
                    else:
                        results[job['role']] = row
            if sorted(results) != last_roles:
                last_roles = sorted(results)
                cloud.safe_event('roles_completed', roles=last_roles)
            if len(results) + len(failures) == len(jobs):
                if failures:
                    cloud.safe_event('training_partial', completed_roles=sorted(results), failed_roles=sorted(failures),
                                     artifacts={role: row['artifact'] for role, row in results.items()})
                    Path('private-dual-result.json').write_text(json.dumps(results, ensure_ascii=True), encoding='utf8')
                    Path('private-dual-failures.json').write_text(json.dumps(failures, ensure_ascii=True), encoding='utf8')
                    return 1
                cloud.safe_event('dual_training_completed', artifacts={r: x['artifact'] for r, x in results.items()},
                                 weights_updated=True, production_promotion=False)
                Path('private-dual-result.json').write_text(json.dumps(results, ensure_ascii=True), encoding='utf8')
                return 0
            remaining = float(plan.deadline_monotonic) - time.monotonic()
            if remaining <= 0:
                break
            info = cloud.runpod('GET', '/pods/' + pod['id'], request_timeout=min(10, remaining))
            validate_observed_pod(plan, info)
            if (info.get('gpu') or {}).get('id') != selected_gpu:
                raise ValueError('observed GPU differs from the selected role GPU')
            if info.get('desiredStatus') in ('EXITED', 'ERROR', 'TERMINATED'):
                raise RuntimeError('GPU stopped before both private adapters were uploaded')
            time.sleep(min(20, max(0, float(plan.deadline_monotonic) - time.monotonic())))
        raise RuntimeError('dual-model deadline reached')
    finally:
        if attempted:
            matches = [pod] if pod and pod.get('id') else cloud.reconcile_created_pods(run_id)
            outcomes = [cloud.delete_and_confirm(p['id']) for p in matches]
            confirmed = all(outcomes)
            cloud.safe_event('pod_cleanup', matched_pods=len(matches), deletion_confirmed=confirmed)
            if confirmed:
                ledger = settle_run(ledger, run_id, time.monotonic(), deletion_confirmed=True)
                cloud.safe_event('cost_estimate_upper', krw=str(ledger.spent_krw), budget_krw=budget)
            else:
                raise RuntimeError('GPU deletion could not be confirmed')


if __name__ == '__main__':
    def terminate(_signum, _frame):
        raise SystemExit(143)
    signal.signal(signal.SIGTERM, terminate)
    try:
        raise SystemExit(main())
    except Exception as error:
        frames = [{'file': Path(f.filename).name, 'line': f.lineno, 'function': f.name}
                  for f in traceback.extract_tb(error.__traceback__)[-5:]]
        cloud.safe_event('failed', error_class=type(error).__name__, trace=frames, weights_updated=False)
        raise SystemExit(1)
