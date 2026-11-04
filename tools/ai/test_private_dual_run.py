"""Offline dual-role parent checks: no credentials, network, GPUs or uploads."""
import base64
import copy
import contextlib
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import private_dual_run as dual


PRIVATE = "SYNTHETIC_PRIVATE_DUAL_FIXTURE"


def fixture():
    env = {"GITHUB_SHA": "a" * 40, "GITHUB_RUN_ID": "12345", "HASLA_PREFLIGHT_ONLY": "false",
           "RUNPOD_API_KEY": "fixture-key", "WANDB_API_KEY": "fixture-key", "HF_TOKEN": "fixture-key"}
    manifest = {"budget_krw": 30000, "prior_upper_krw": 10, "selected_roles": ["solver"],
                **{key: "1" * 64 for key in ("train_script_sha256", "role_config_sha256", "pod_script_sha256", "dual_pod_sha256")},
                "roles": {}}
    for role in ("chat", "solver"):
        spec = {"role": role, "format": "chat" if role == "chat" else "text", "dataset_version": "fixture-v1"}
        for split in ("train", "validation"):
            row = {"metadata": {"group_id": f"{role}-{split}", "split": split}}
            if role == "chat":
                row["metadata"].update(derivation="paraphrase_observed_exchange", reconstructed=True,
                    old_synthetic_seed=False, observed_reply_link="fixture top-level body reply",
                    reviewer="agent:fixture", review_status="approved", collected_at="2026-11-04T00:00:00Z",
                    source_url="https://orbi.kr/00079999827", question_sha256="a" * 64, answer_sha256="b" * 64)
                row['metadata']['author_filter'] = {'policy_version': 'exclude-bugiu-v1', 'post_author_checked': True,
                    'selected_reply_authors_checked': True, 'reply_branch_checked': True, 'excluded_author_present': False}
                row["messages"] = [{"role": "user", "content": "fixture question " + split},
                                   {"role": "assistant", "content": PRIVATE + split}]
            else:
                row["metadata"].update(drive_provenance={"drive_file_id": "fixture-drive-book", "local_original_pdf_sha256": "c" * 64}, page_number=10)
                row["text"] = PRIVATE + role + split
            raw = (json.dumps(row) + "\n").encode()
            encoded = base64.b64encode(gzip.compress(raw)).decode()
            prefix = f"HASLA_{role.upper()}_" + ("DATA" if split == "train" else "VALIDATION")
            env[prefix + "_00"] = encoded
            spec[split] = {"parts": 1, "records": 1, "raw_sha256": hashlib.sha256(raw).hexdigest(),
                           "encoded_sha256": hashlib.sha256(encoded.encode()).hexdigest()}
        manifest["roles"][role] = spec
    env["HASLA_DUAL_MANIFEST"] = json.dumps(manifest)
    return env, manifest


class PrivateDualParentTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(patch.stopall)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        cwd = os.getcwd()
        self.addCleanup(os.chdir, cwd)
        os.chdir(self.temp.name)
        self.env, self.manifest = fixture()
        patch.dict(os.environ, self.env, clear=True).start()
        patch.object(dual.sys, "argv", ["private_dual_run.py"]).start()
        patch.object(dual.cloud, "E", {}).start()
        for name in ("request", "post", "get", "delete", "head"):
            patch.object(dual.cloud.requests, name, side_effect=AssertionError("external I/O forbidden in tests")).start()
        patch.object(dual.time, "monotonic", return_value=100).start()
        patch.object(dual.time, "sleep", side_effect=AssertionError("unexpected polling wait")).start()

    def pod(self, **kw):
        return {"id": "fixture-pod", "name": dual.cloud.PREFIX + "12345", "costPerHr": "2.5",
                "containerDiskInGb": 200, "volumeInGb": 0, "gpu": {"id":dual.cloud.GPU_IDS[1],"count": 1}, "desiredStatus": "RUNNING", **kw}

    @contextlib.contextmanager
    def ready(self, failed=False, lost=False):
        operations, lists = [], []
        def api(method, path, **kw):
            operations.append((method, path))
            if path == "/pods":
                lists.append(True)
                return [] if len(lists) == 1 else [self.pod(), self.pod(id="other", name="unrelated")]
            if path == "/pods/fixture-pod":
                return self.pod()
            raise AssertionError("unexpected Runpod operation")
        def create(*args, **kwargs):
            if lost:
                raise dual.cloud.requests.Timeout("synthetic lost response")
            return {"id": "fixture-pod"}
        def publish(entity, run, spec, data):
            return {"HASLA_INPUT_ARTIFACT": f"{entity}/{dual.cloud.PROJECT}/{run}-data:v2"}
        def result(entity, run, **kwargs):
            role = "chat" if run.endswith("-chat") else "solver"
            return {"role": role, "status": "failed" if failed else "uploaded", "artifact": role + "-adapter:v0"}
        patches = [patch.object(dual.cloud, "runpod", side_effect=api),
                   patch.object(dual.cloud, "graphql_create_pod", side_effect=create),
                   patch.object(dual.cloud, "capacity_preflight", return_value=dual.cloud.GPU_IDS[1]),
                   patch.object(dual.cloud, "private_project", return_value="fixture-entity"),
                   patch.object(dual.cloud.requests, "head", return_value=SimpleNamespace(ok=True)),
                   patch.object(dual.cloud, "publish_private_input", side_effect=publish),
                   patch.object(dual.cloud, "result_for", side_effect=result),
                   patch.object(dual.cloud, "delete_and_confirm", return_value=True),
                   patch.object(dual, "verify_pinned_scripts")]
        mocks = [p.start() for p in patches]
        try:
            yield SimpleNamespace(operations=operations, api=mocks[0], create=mocks[1], publish=mocks[5],
                                  result=mocks[6], delete=mocks[7])
        finally:
            for p in reversed(patches):
                p.stop()

    def test_role_specific_inputs_reject_hash_format_and_group_contamination(self):
        manifest, payloads = dual.load_inputs(self.env)
        self.assertEqual(list(payloads), ["solver"])
        for role in ("chat", "solver"):
            broken = json.loads(json.dumps(self.manifest))
            broken['selected_roles'] = [role]
            broken["roles"][role]["train"]["raw_sha256"] = "0" * 64
            with self.subTest(role=role), self.assertRaises(RuntimeError):
                dual.load_inputs({**self.env, "HASLA_DUAL_MANIFEST": json.dumps(broken)})
        broken = json.loads(json.dumps(self.manifest))
        broken['selected_roles'] = ['chat']
        broken["roles"]["chat"]["format"] = "text"
        with self.assertRaises(ValueError):
            dual.load_inputs({**self.env, "HASLA_DUAL_MANIFEST": json.dumps(broken)})
        # Validation is an intact, correctly hashed JSONL, but belongs to a training group.
        row = {"text": "different passage", "metadata": {"group_id": "solver-train", "split": "validation",
            "drive_provenance": {"drive_file_id": "fixture-drive-book", "local_original_pdf_sha256": "c" * 64}, "page_number": 11}}
        raw = (json.dumps(row) + "\n").encode()
        encoded = base64.b64encode(gzip.compress(raw)).decode()
        broken = json.loads(json.dumps(self.manifest))
        broken["roles"]["solver"]["validation"].update(raw_sha256=hashlib.sha256(raw).hexdigest(),
                                                            encoded_sha256=hashlib.sha256(encoded.encode()).hexdigest())
        with self.assertRaisesRegex(RuntimeError, "group_overlap"):
            dual.load_inputs({**self.env, "HASLA_SOLVER_VALIDATION_00": encoded, "HASLA_DUAL_MANIFEST": json.dumps(broken)})

    def test_preflight_is_zero_gpu_and_uses_selected_role_budget(self):
        os.environ["HASLA_PREFLIGHT_ONLY"] = "true"
        output = io.StringIO()
        with self.ready() as mocks, contextlib.redirect_stdout(output):
            self.assertEqual(dual.main(), 0)
        mocks.create.assert_not_called()
        mocks.publish.assert_not_called()
        event = next(json.loads(line) for line in output.getvalue().splitlines() if json.loads(line)["event"] == "dual_preflight")
        self.assertEqual(event["runtime_seconds"], 3600)
        self.assertLess(int(event["reserved_upper_krw"]) + 5000 + 10, 30000)

    def test_staged_private_input_needs_exact_version_and_bounded_inventory(self):
        spec = self.manifest['roles']['solver']
        spec['input_artifact'] = 'fixture-entity/hasla-ai-private-training/expanded-source:v1'
        for split in ('train', 'validation'):
            spec[split]['raw_bytes'] = 100
        env = {'GITHUB_SHA': 'a' * 40, 'HASLA_DUAL_MANIFEST': json.dumps(self.manifest)}
        _, payloads = dual.load_inputs(env)
        self.assertEqual(payloads, {'solver': {'HASLA_INPUT_ARTIFACT': spec['input_artifact']}})
        for reference in (spec['input_artifact'].replace(':v1', ':latest'),
                          spec['input_artifact'].replace('hasla-ai-private-training', 'public-project')):
            spec['input_artifact'] = reference
            with self.assertRaises(ValueError):
                dual.load_inputs({**env, 'HASLA_DUAL_MANIFEST': json.dumps(self.manifest)})

    def test_chat_requires_current_author_filter_and_distinguishes_physics_galleries(self):
        raw = gzip.decompress(base64.b64decode(self.env['HASLA_CHAT_DATA_00']))
        row = json.loads(raw)
        row['metadata']['source_url'] = 'https://gall.dcinside.com/mgallery/board/view/?id=physics&no=398'
        dual.validate_source_lineage([row], 'chat')
        row['metadata']['source_url'] = 'https://gall.dcinside.com/board/view/?id=physicalscience&no=1'
        with self.assertRaisesRegex(ValueError, 'excluded'):
            dual.validate_source_lineage([row], 'chat')
        row['metadata']['source_url'] = 'https://orbi.kr/00079999827'
        for key, value in (('post_author_checked', False), ('selected_reply_authors_checked', False),
                           ('reply_branch_checked', False), ('excluded_author_present', True)):
            failed = json.loads(json.dumps(row))
            failed['metadata']['author_filter'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                dual.validate_source_lineage([failed], 'chat')

    def test_expanded_educational_sources_require_native_provenance_and_traceable_locator(self):
        meta = {'haslalab_provenance': {'source_id': 'fixture-competition-2024', 'source_family': 'competition',
                'local_source_sha256': 'c' * 64, 'extraction': 'native', 'original_locator': 'page:1'},
                'group_id': 'fixture-competition-2024', 'target_role': 'solver', 'content_type': 'competition_problem',
                'scan_suspect': False}
        dual.validate_source_lineage([{'text': PRIVATE, 'metadata': meta}], 'solver')
        for changed in ({'scan_suspect': True}, {'target_role': 'chat'}, {'group_id': ''},
                        {'content_type': 'fabricated_solution'}, {'haslalab_provenance': {}},
                        {'haslalab_provenance': {**meta['haslalab_provenance'], 'extraction': 'guessed_ocr'}}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                dual.validate_source_lineage([{'text': PRIVATE, 'metadata': {**meta, **changed}}], 'solver')

    def test_staged_full_bytes_are_verified_before_paid_creation(self):
        os.environ['HASLA_PREFLIGHT_ONLY'] = 'false'
        with self.ready() as mocks, patch.object(dual, 'verify_staged_inputs', side_effect=ValueError('staged mismatch')), \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, 'staged mismatch'):
            dual.main()
        mocks.create.assert_not_called()
        mocks.publish.assert_not_called()

    def test_remote_line_endings_are_verified_before_any_gpu_or_private_upload(self):
        public_code = b'print("fixture")\n'
        pinned = {key: hashlib.sha256(public_code).hexdigest() for key in
                  ('train_script_sha256','role_config_sha256','pod_script_sha256','dual_pod_sha256')}
        with patch.object(dual.cloud.requests, 'get', return_value=SimpleNamespace(status_code=200,content=public_code)) as get, \
                contextlib.redirect_stdout(io.StringIO()):
            dual.verify_pinned_scripts(pinned, 'a' * 40)
            self.assertEqual(get.call_count, 4)
        with patch.object(dual.cloud.requests, 'get', return_value=SimpleNamespace(status_code=200,content=public_code.replace(b'\n',b'\r\n'))), \
                self.assertRaisesRegex(ValueError,'checksum mismatch'):
            dual.verify_pinned_scripts(pinned, 'a' * 40)
        with patch.object(dual,'verify_pinned_scripts',side_effect=ValueError('checksum mismatch')), \
                patch.object(dual.cloud,'runpod') as resource, patch.object(dual.cloud,'publish_private_input') as upload, \
                self.assertRaisesRegex(ValueError,'checksum mismatch'):
            dual.main()
        resource.assert_not_called()
        upload.assert_not_called()

    def test_authored_seed_or_source_less_book_cannot_masquerade_as_collected_material(self):
        for role in ('chat', 'solver'):
            spec = self.manifest['roles'][role]['train']
            prefix = f'HASLA_{role.upper()}_DATA_00'
            row = json.loads(gzip.decompress(base64.b64decode(self.env[prefix])).decode())
            if role == 'chat':
                row['metadata']['old_synthetic_seed'] = True
            else:
                row['metadata'].pop('drive_provenance')
            raw = (json.dumps(row) + '\n').encode()
            encoded = base64.b64encode(gzip.compress(raw)).decode()
            changed = json.loads(json.dumps(self.manifest))
            changed['selected_roles'] = [role]
            changed['roles'][role]['train'].update(raw_sha256=hashlib.sha256(raw).hexdigest(),
                encoded_sha256=hashlib.sha256(encoded.encode()).hexdigest())
            with self.subTest(role=role), self.assertRaisesRegex(ValueError, 'requires'):
                dual.load_inputs({**self.env, prefix: encoded, 'HASLA_DUAL_MANIFEST': json.dumps(changed)})

    def test_one_dedicated_pod_handles_one_reference_and_result_then_always_cleans_up(self):
        output = io.StringIO()
        with self.ready() as mocks, contextlib.redirect_stdout(output):
            self.assertEqual(dual.main(), 0)
        mocks.create.assert_called_once()
        self.assertEqual(mocks.publish.call_count, 1)
        gpu_env = mocks.create.call_args.args[1]
        jobs = json.loads(gpu_env["HASLA_ROLE_JOBS"])
        self.assertEqual([j["role"] for j in jobs], ["solver"])
        self.assertEqual(jobs[0]['runtime_seconds'],3000)
        self.assertTrue(all(j["input_artifact"].endswith(":v2") for j in jobs))
        self.assertFalse(any(repr(gpu_env).find(value) >= 0 for key, value in self.env.items()
                             if key.startswith(("HASLA_CHAT_DATA_", "HASLA_SOLVER_DATA_"))))
        self.assertFalse(any(key.startswith(("HASLA_CHAT_", "HASLA_SOLVER_", "HASLA_DATA_00")) for key in gpu_env))
        self.assertNotIn("RUNPOD_API_KEY", gpu_env)
        self.assertNotIn(PRIVATE, output.getvalue())
        results = json.loads(Path("private-dual-result.json").read_text())
        self.assertEqual(set(results), {"solver"})
        mocks.delete.assert_called_once_with("fixture-pod")

    def test_model_failures_are_recorded_and_cleanup_is_confirmed(self):
        with self.ready(failed=True) as mocks, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(dual.main(), 1)
        self.assertEqual(mocks.result.call_count, 1)
        mocks.delete.assert_called_once_with("fixture-pod")
        self.assertEqual(json.loads(Path("private-dual-result.json").read_text()), {})
        self.assertEqual(set(json.loads(Path("private-dual-failures.json").read_text())), {'solver'})

    def test_dedicated_solver_does_not_consult_chat_failure(self):
        with self.ready() as mocks, contextlib.redirect_stdout(io.StringIO()):
            mocks.result.side_effect = lambda entity, run, **kw: {'status':'uploaded','artifact':'solver-adapter:v0'} if run.endswith('-solver') else {'status':'failed','error_code':'trainer_process_failed'}
            self.assertEqual(dual.main(), 0)
        self.assertEqual(set(json.loads(Path('private-dual-result.json').read_text())), {'solver'})
        self.assertFalse(Path('private-dual-failures.json').exists())
        mocks.delete.assert_called_once_with('fixture-pod')

    def test_independent_solver_run_uses_one_hour_and_never_uploads_chat_input(self):
        self.manifest['selected_roles'] = ['solver']
        os.environ['HASLA_DUAL_MANIFEST'] = json.dumps(self.manifest)
        output = io.StringIO()
        with self.ready() as mocks, contextlib.redirect_stdout(output):
            self.assertEqual(dual.main(), 0)
        mocks.publish.assert_called_once()
        self.assertTrue(mocks.publish.call_args.args[1].endswith('-solver'))
        self.assertEqual([j['role'] for j in json.loads(mocks.create.call_args.args[1]['HASLA_ROLE_JOBS'])], ['solver'])
        event=next(json.loads(line) for line in output.getvalue().splitlines() if json.loads(line)['event']=='dual_preflight')
        self.assertEqual(event['runtime_seconds'],3600)
        self.assertEqual(set(json.loads(Path('private-dual-result.json').read_text())),{'solver'})
        for selected in ([], ['chat','chat'], ['unknown'], 'solver'):
            bad={**self.manifest,'selected_roles':selected}
            with self.subTest(selected=selected), self.assertRaisesRegex(ValueError,'selected'):
                dual.load_inputs({**self.env,'HASLA_DUAL_MANIFEST':json.dumps(bad)})

    def test_lost_creation_response_recovers_only_exact_name_without_recreation(self):
        with self.ready(lost=True) as mocks, contextlib.redirect_stdout(io.StringIO()), \
                self.assertRaises(dual.cloud.requests.Timeout):
            dual.main()
        mocks.create.assert_called_once()
        mocks.delete.assert_called_once_with("fixture-pod")

    def test_two_role_paid_pod_is_rejected_before_any_io(self):
        self.manifest['selected_roles']=['chat','solver']
        os.environ['HASLA_DUAL_MANIFEST']=json.dumps(self.manifest)
        with self.ready() as mocks, self.assertRaisesRegex(ValueError,'exactly one'):
            dual.main()
        mocks.api.assert_not_called()
        mocks.create.assert_not_called()
        mocks.publish.assert_not_called()

    def test_new_budget_and_role_limits_are_checked_before_gpu_creation(self):
        self.manifest.update(budget_krw=100000,authorized_budget_krw=100000,prior_upper_krw=7653)
        self.manifest['roles']['solver'].update(runtime_seconds=14400,gpu_ids=[dual.cloud.GPU_IDS[1]],gpu_usd_per_hour_upper='4')
        os.environ['HASLA_DUAL_MANIFEST']=json.dumps(self.manifest)
        output=io.StringIO()
        with self.ready() as mocks, contextlib.redirect_stdout(output):
            self.assertEqual(dual.main(),0)
        event=next(json.loads(line) for line in output.getvalue().splitlines() if json.loads(line)['event']=='dual_preflight')
        self.assertEqual(event['runtime_seconds'],14400)
        self.assertEqual(event['budget_krw'],100000)
        self.assertLessEqual(int(event['reserved_upper_krw'])+7653+5000,100000)
        self.assertEqual(json.loads(mocks.create.call_args.args[1]['HASLA_ROLE_JOBS'])[0]['runtime_seconds'],13800)
        self.assertIn('14280s',mocks.create.call_args.args[2])
        for role,seconds in [('chat',1801),('solver',14401),('solver',True),('solver',659)]:
            broken=json.loads(json.dumps(self.manifest))
            broken['selected_roles']=[role]
            broken['roles'][role]['runtime_seconds']=seconds
            with self.subTest(role=role,seconds=seconds), self.assertRaises(ValueError):
                dual.load_inputs({**self.env,'HASLA_DUAL_MANIFEST':json.dumps(broken)})

    def test_budget_authorization_prior_gpu_policy_and_observed_identity_fail_closed(self):
        for update in ({'budget_krw':100000},{'budget_krw':100001,'authorized_budget_krw':100000},{'prior_upper_krw':-1}):
            broken={**self.manifest,**update}
            with self.subTest(update=update),self.assertRaises(ValueError):
                dual.load_inputs({**self.env,'HASLA_DUAL_MANIFEST':json.dumps(broken)})
        missing={**self.manifest}
        missing.pop('prior_upper_krw')
        with self.assertRaisesRegex(ValueError,'prior'):
            dual.load_inputs({**self.env,'HASLA_DUAL_MANIFEST':json.dumps(missing)})
        with self.ready() as mocks,contextlib.redirect_stdout(io.StringIO()),patch.object(dual,'validate_observed_pod'),patch.object(dual.cloud,'runpod',side_effect=[[],self.pod(gpu={'id':'WRONG_GPU','count':1})]),self.assertRaisesRegex(ValueError,'created GPU'):
            dual.main()
        mocks.delete.assert_called_once_with('fixture-pod')

    def test_unselected_input_is_not_required_but_an_earlier_private_pod_blocks_run(self):
        env={key:value for key,value in self.env.items() if not key.startswith('HASLA_CHAT_')}
        _,payloads=dual.load_inputs(env)
        self.assertEqual(list(payloads),['solver'])
        with self.ready() as mocks,patch.object(dual.cloud,'runpod',return_value=[self.pod(name=dual.cloud.PREFIX+'earlier')]),self.assertRaisesRegex(RuntimeError,'earlier private Pod'):
            dual.main()
        mocks.create.assert_not_called()
        mocks.publish.assert_not_called()


class AuthoredGemmaProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import gemma_role_curriculum as authored
        cls.authored = authored
        trusted = dual._AUTHORED_CHAT_COHORT
        pins = {item['path']:item['sha256'] for item in trusted['source_refs']}
        _current, classifier, _about = authored.source_contract(Path(authored.__file__).resolve().parents[2])
        rows, _proof, spec = authored.author_rows(classifier, pins)
        if authored.sha(authored.canonical(spec)) != trusted['spec_sha256']:
            raise AssertionError('The public authored fixture builder changed; do not silently reapprove a cohort')
        for row in rows:
            row['review_status'] = 'approved'
            row['metadata'].update(dataset_version=trusted['approved_dataset_version'],
                source_dataset_version=trusted['source_dataset_version'], source_curriculum_version=trusted['source_curriculum_version'],
                review_status='approved', reviewer=trusted['reviewer'], review_receipt_sha256=trusted['review_receipt_sha256'])
        cls.rows = rows

    def test_all_exact_root_reviewed_synthetic_records_pass_without_private_files(self):
        self.assertEqual(len(self.rows),64)
        dual.validate_source_lineage(self.rows,'chat')
        self.assertNotEqual(dual._AUTHORED_CHAT_COHORT['reviewer'],dual._AUTHORED_CHAT_COHORT['authoring_agent'])
        self.assertTrue(all(row['metadata']['synthetic'] for row in self.rows))

    def test_tampered_message_cannot_pass_by_recomputing_its_own_hash(self):
        row=copy.deepcopy(self.rows[0]);row['messages'][-1]['content']='A changed, never-reviewed authored answer.'
        row['metadata']['messages_sha256']=dual._authored_chat_sha(row['messages'])
        with self.assertRaises(ValueError):dual.validate_source_lineage([row],'chat')

    def test_approval_reviewer_spec_receipt_and_source_versions_are_exact(self):
        changes={'review_status':'pending_independent_review','reviewer':dual._AUTHORED_CHAT_COHORT['authoring_agent'],
            'authoring_agent':'another-author','review_receipt_sha256':'0'*64,'curriculum_spec_sha256':'0'*64,
            'dataset_version':'another-export','source_dataset_version':'another-source','source_curriculum_version':'another-curriculum'}
        for key,value in changes.items():
            row=copy.deepcopy(self.rows[0]);row['metadata'][key]=value
            with self.subTest(field=key),self.assertRaises(ValueError):dual.validate_source_lineage([row],'chat')
        row=copy.deepcopy(self.rows[0]);row['review_status']='pending_independent_review'
        with self.assertRaises(ValueError):dual.validate_source_lineage([row],'chat')

    def test_typed_authorship_booleans_cannot_be_missing_or_numeric(self):
        for key in ('authored','synthetic','community_observation','old_synthetic_seed','human_reviewed','scientifically_verified'):
            for value in (None,0,1):
                row=copy.deepcopy(self.rows[0]);row['metadata'][key]=value
                with self.subTest(field=key,value=value),self.assertRaises(ValueError):dual.validate_source_lineage([row],'chat')

    def test_unknown_schema_modes_languages_domains_tasks_and_test_split_are_rejected(self):
        for key,value in {'curriculum_mode':'unrecognized','input_language':'ja','output_language':'en',
            'language_origin':'observed_translation','domain':'shared','task':'solve','split':'test',
            'group_id':'another-group','family_id':'unknown-family'}.items():
            row=copy.deepcopy(self.rows[0]);row['metadata'][key]=value
            with self.subTest(field=key),self.assertRaises(ValueError):dual.validate_source_lineage([row],'chat')

    def test_family_or_record_identity_cannot_be_moved_even_with_valid_looking_labels(self):
        row=copy.deepcopy(self.rows[0]);row['metadata'].update(family_id='chat:motivation',group_id='authored-role-family:chat:motivation',split='validation')
        with self.assertRaises(ValueError):dual.validate_source_lineage([row],'chat')
        row=copy.deepcopy(self.rows[0]);row['id']=self.rows[1]['id']
        with self.assertRaises(ValueError):dual.validate_source_lineage([row],'chat')

    def test_source_refs_and_fixture_context_are_bound_by_the_reviewed_whole_row(self):
        row=copy.deepcopy(self.rows[0]);row['metadata']['source_refs'][0]['sha256']='0'*64
        with self.assertRaises(ValueError):dual.validate_source_lineage([row],'chat')
        row=copy.deepcopy(self.rows[0]);row['metadata']['context']['model_verified']=True
        with self.assertRaises(ValueError):dual.validate_source_lineage([row],'chat')

    def test_malformed_container_types_fail_with_fixed_validation_errors(self):
        for field in ('curriculum_mode','family_id','task'):
            row=copy.deepcopy(self.rows[0]);row['metadata'][field]=[]
            with self.subTest(field=field),self.assertRaises(ValueError):dual.validate_source_lineage([row],'chat')

    def test_extra_fields_community_impersonation_and_unknown_provenance_cannot_bypass_filters(self):
        for key in ('source_url','author_filter','observed_reply_link','collected_at'):
            row=copy.deepcopy(self.rows[0]);row['metadata'][key]='forged-community-evidence'
            with self.subTest(field=key),self.assertRaises(ValueError):dual.validate_source_lineage([row],'chat')
        row=copy.deepcopy(self.rows[0]);row['extra']='not approved'
        with self.assertRaises(ValueError):dual.validate_source_lineage([row],'chat')
        row=copy.deepcopy(self.rows[0]);row['metadata']['provenance_type']='unknown_authored_kind'
        with self.assertRaisesRegex(ValueError,'unknown'):dual.validate_source_lineage([row],'chat')

    def test_existing_community_author_exclusion_and_forbidden_gallery_remain_enforced(self):
        from test_gemma_role_curriculum import community_row
        row=community_row('train',0);dual.validate_source_lineage([row],'chat')
        row['metadata']['author_filter']['excluded_author_present']=True
        with self.assertRaises(ValueError):dual.validate_source_lineage([row],'chat')
        row=community_row('train',0);row['metadata']['source_url']='https://gall.dcinside.com/mgallery/board/view/?id=physicalscience&no=1'
        with self.assertRaises(ValueError):dual.validate_source_lineage([row],'chat')

    def test_approved_gemma_authoring_never_becomes_solver_or_test_data(self):
        with self.assertRaises(ValueError):dual.validate_source_lineage(self.rows,'solver')
        row=copy.deepcopy(self.rows[0]);row['metadata']['target_role']='solver'
        with self.assertRaises(ValueError):dual.validate_source_lineage([row],'chat')
        row=copy.deepcopy(self.rows[0]);row['metadata']['split']='test'
        with self.assertRaises(ValueError):dual.validate_source_lineage([row],'chat')


if __name__ == "__main__":
    unittest.main()
