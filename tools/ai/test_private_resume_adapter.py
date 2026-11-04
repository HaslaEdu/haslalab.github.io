"""Synthetic offline continuation fixtures: no SDK, model or network calls."""
import copy
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import private_resume_adapter as resume
from role_config import get_role_config


PRIVATE = 'FIXTURE_PRIVATE_TOKEN_AND_TEXT_MUST_NOT_BE_PRINTED'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def container(tensors, *, reverse=False, metadata=None):
    header, payload = {}, b''
    if metadata is not None:
        header['__metadata__'] = metadata
    for name, dtype, shape, bits in (list(reversed(tensors)) if reverse else tensors):
        width = resume.DTYPES[dtype][0]
        raw = b''.join(value.to_bytes(width, 'little') for value in bits)
        header[name] = {'dtype': dtype, 'shape': shape, 'data_offsets': [len(payload), len(payload) + len(raw)]}
        payload += raw
    raw = json.dumps(header, separators=(',', ':')).encode()
    return struct.pack('<Q', len(raw)) + raw + payload


def tensors(dtype='F32', bits=None, *, embedding=False, output=1, prefix='base.block'):
    stem = 'lora_embedding' if embedding else 'lora'
    bits = [1] * (16 * output) if bits is None else bits
    return [(prefix + '.' + stem + '_A.weight', dtype, [16, 1], [0] * 16),
            (prefix + '.' + stem + '_B.weight', dtype, [output, 16], bits)]


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.destination = self.root / 'initial-adapter'
        self.config = get_role_config('solver')
        self.peft = {'peft_type': 'LORA', 'base_model_name_or_path': 'unsloth/QwQ-32B', 'r': 16}
        self.files = {'adapter_config.json': json.dumps(self.peft).encode(),
                      'adapter_model.safetensors': container(tensors())}
        self.spec = self.make_spec()
        self.downloads = []
        self.trace = []

    def make_spec(self):
        inventory = [{'name': name, 'bytes': len(self.files[name]), 'sha256': sha(self.files[name])} for name in resume.FILES]
        return {'version': 1, 'kind': 'private_adapter_continuation', 'role': 'solver',
                'base_model': 'Qwen/QwQ-32B', 'rank': 16, 'source_training_run_id': '123',
                'entity': 'fixture', 'artifact': f'fixture/{resume.PROJECT}/hasla-private-books-123-solver-lora:v2',
                'files': inventory, 'adapter_inventory_sha256': sha(json.dumps(inventory, sort_keys=True,
                    separators=(',', ':')).encode()), 'prior_verification_run_id': '456'}

    def sdk(self, **changes):
        def entry(name):
            def download(root, skip_cache):
                self.downloads.append(name)
                self.trace.append('download:' + name)
                path = Path(root) / name
                path.write_bytes(self.files[name])
                return str(path)
            return SimpleNamespace(path=name, size=len(self.files[name]), ref=None, download=download)
        entries = {name: entry(name) for name in resume.FILES}
        metadata = {'private': True, 'role': 'solver', 'base_model': self.spec['base_model'], 'rank': 16,
                    'adapter_sha256': self.spec['adapter_inventory_sha256']}
        artifact = SimpleNamespace(qualified_name=self.spec['artifact'], type='lora', state='COMMITTED',
            is_link=False, metadata=metadata, manifest=SimpleNamespace(entries=entries),
            get_entry=Mock(side_effect=lambda name: entry(name)), **changes)
        api = SimpleNamespace(artifact=Mock(side_effect=lambda *a, **kw: self.trace.append('artifact') or artifact))
        return api, artifact

    def privacy(self, entity):
        self.assertEqual(entity, 'fixture')
        self.trace.append('privacy')
        return {'entity': entity, 'project': resume.PROJECT, 'access': 'PRIVATE'}

    def compare(self, before, after):
        old, new = self.root / 'before.safetensors', self.root / 'after.safetensors'
        old.write_bytes(before)
        new.write_bytes(after)
        return resume.compare_lora_b(old, new, 16)

    def test_spec_is_detached_and_prior_verification_is_not_a_weight_proof(self):
        checked = resume.validate_spec(self.spec, self.config)
        checked['files'][0]['bytes'] = 1
        self.assertNotEqual(checked['files'][0]['bytes'], self.spec['files'][0]['bytes'])
        self.assertEqual(checked['prior_verification_run_id'], '456')
        self.assertNotIn('weights_updated', checked)

    def test_invalid_role_rank_base_kind_version_or_identity_fails_before_sdk(self):
        mutations = {'role': 'chat', 'rank': True, 'base_model': 'google/gemma-4-26B-A4B-it',
                     'kind': 'untrusted', 'version': True, 'source_training_run_id': '１２３',
                     'entity': '../fixture', 'prior_verification_run_id': PRIVATE}
        for field, value in mutations.items():
            spec = {**self.spec, field: value}
            with self.subTest(field=field), self.assertRaises(resume.ResumeError):
                resume.validate_spec(spec, self.config)
        with self.assertRaises(resume.ResumeError):
            resume.validate_spec({**self.spec, 'human_verified': True}, self.config)
        with self.assertRaises(resume.ResumeError):
            resume.validate_spec(self.spec, get_role_config('chat'))

    def test_artifact_reference_is_exact_entity_project_training_run_role_and_version(self):
        for ref in (self.spec['artifact'].replace(':v2', ':latest'), self.spec['artifact'].replace('123-solver', '999-solver'),
                    self.spec['artifact'].replace(resume.PROJECT, 'public'), self.spec['artifact'].replace('fixture/', 'other/'),
                    self.spec['artifact'] + '/extra'):
            with self.subTest(ref=ref), self.assertRaises(resume.ResumeError):
                resume.validate_spec({**self.spec, 'artifact': ref}, self.config)

    def test_inventory_order_sizes_and_canonical_hash_are_strict(self):
        cases = []
        reordered = copy.deepcopy(self.spec)
        reordered['files'].reverse()
        cases.append(reordered)
        for field, value in (('bytes', 0), ('bytes', True), ('bytes', resume.MAX_CONFIG_BYTES + 1),
                             ('sha256', 'not-a-hash'), ('name', '../escape')):
            bad = copy.deepcopy(self.spec)
            bad['files'][0][field] = value
            cases.append(bad)
        cases.append({**self.spec, 'adapter_inventory_sha256': '0' * 64})
        for spec in cases:
            with self.subTest(spec=spec['adapter_inventory_sha256']), self.assertRaises(resume.ResumeError):
                resume.validate_spec(spec, self.config)

    def test_download_reads_only_two_pinned_files_with_private_gates(self):
        api, artifact = self.sdk()
        result = resume.download_initial_adapter(self.spec, self.config, self.destination, api, self.privacy)
        self.assertEqual(set(path.name for path in self.destination.iterdir()), set(resume.FILES))
        self.assertEqual(self.downloads, list(resume.FILES))
        self.assertEqual(self.trace[0:2], ['privacy', 'artifact'])
        self.assertEqual(self.trace.count('privacy'), 4)
        self.assertTrue(result['integrity_verified'])
        self.assertFalse(result['relative_weight_change_verified'])
        self.assertFalse(result['prior_verification_independently_verified'])
        self.assertFalse(result['optimizer_state_restored'])
        self.assertEqual(result['adapter_inventory_sha256'], self.spec['adapter_inventory_sha256'])
        api.artifact.assert_called_once_with(self.spec['artifact'], type='lora')

    def test_private_gate_rejects_false_none_public_or_wrong_entity_before_sdk(self):
        for value in (False, None, {'access': 'PUBLIC', 'entity': 'fixture', 'project': resume.PROJECT},
                      {'access': 'PRIVATE', 'entity': 'other', 'project': resume.PROJECT}):
            api, _ = self.sdk()
            with self.subTest(value=value), self.assertRaises(resume.ResumeError):
                resume.download_initial_adapter(self.spec, self.config, self.destination, api, lambda _: value)
            api.artifact.assert_not_called()
            self.assertFalse(self.destination.exists())

    def test_artifact_metadata_links_state_entries_and_external_refs_are_rejected(self):
        for field, value in (('state', 'PENDING'), ('is_link', True), ('type', 'dataset')):
            api, artifact = self.sdk()
            setattr(artifact, field, value)
            with self.subTest(field=field), self.assertRaises(resume.ResumeError):
                resume.download_initial_adapter(self.spec, self.config, self.destination, api, self.privacy)
            self.assertEqual(self.downloads, [])
        api, artifact = self.sdk()
        artifact.metadata['adapter_sha256'] = '0' * 64
        with self.assertRaises(resume.ResumeError):
            resume.download_initial_adapter(self.spec, self.config, self.destination, api, self.privacy)
        api, artifact = self.sdk()
        artifact.manifest.entries['tokenizer.json'] = SimpleNamespace(path='tokenizer.json', size=1, ref=None)
        with self.assertRaises(resume.ResumeError):
            resume.download_initial_adapter(self.spec, self.config, self.destination, api, self.privacy)
        api, artifact = self.sdk()
        artifact.manifest.entries[resume.FILES[1]].ref = 'https://external.example/weights'
        with self.assertRaises(resume.ResumeError):
            resume.download_initial_adapter(self.spec, self.config, self.destination, api, self.privacy)

    def test_actual_hash_mismatch_cleans_only_new_files_and_preserves_originals(self):
        original = self.root / 'original.pdf'
        original.write_text(PRIVATE)
        api, _ = self.sdk()
        self.files[resume.FILES[1]] = self.files[resume.FILES[1]][:-1] + b'X'
        with self.assertRaisesRegex(resume.ResumeError, 'downloaded_adapter_hash_mismatch'):
            resume.download_initial_adapter(self.spec, self.config, self.destination, api, self.privacy)
        self.assertFalse(self.destination.exists())
        self.assertEqual(original.read_text(), PRIVATE)

    def test_peft_config_checks_base_rank_and_type_even_when_file_sha_matches(self):
        for field, value in (('base_model_name_or_path', 'foreign/model'), ('r', 8), ('r', True), ('peft_type', 'PREFIX_TUNING')):
            self.files[resume.FILES[0]] = json.dumps({**self.peft, field: value}).encode()
            self.spec = self.make_spec()
            api, _ = self.sdk()
            with self.subTest(field=field, value=value), self.assertRaises(resume.ResumeError):
                resume.download_initial_adapter(self.spec, self.config, self.destination, api, self.privacy)
            self.assertFalse(self.destination.exists())

    def test_sdk_path_escape_never_deletes_an_existing_external_file(self):
        external = self.root / 'external.json'
        external.write_bytes(self.files[resume.FILES[0]])
        api, artifact = self.sdk()
        artifact.get_entry.side_effect = lambda name: SimpleNamespace(path=name, size=len(self.files[name]), ref=None,
            download=lambda **_: str(external))
        with self.assertRaisesRegex(resume.ResumeError, 'downloaded_adapter_file_invalid'):
            resume.download_initial_adapter(self.spec, self.config, self.destination, api, self.privacy)
        self.assertEqual(external.read_bytes(), self.files[resume.FILES[0]])
        self.assertFalse(self.destination.exists())

    def test_existing_directory_is_preserved_before_sdk_or_private_network(self):
        self.destination.mkdir()
        existing = self.destination / 'user-file'
        existing.write_text(PRIVATE)
        api, _ = self.sdk()
        privacy = Mock()
        with self.assertRaisesRegex(resume.ResumeError, 'initial_adapter_directory_exists'):
            resume.download_initial_adapter(self.spec, self.config, self.destination, api, privacy)
        self.assertEqual(existing.read_text(), PRIVATE)
        api.artifact.assert_not_called()
        privacy.assert_not_called()

    def test_secret_sdk_exception_is_not_exposed_on_stdout_stderr_or_exception(self):
        api, _ = self.sdk()
        def bad(*_, **__):
            print(PRIVATE)
            os.write(2, PRIVATE.encode())
            raise RuntimeError(PRIVATE)
        api.artifact.side_effect = bad
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors), self.assertRaises(resume.ResumeError) as caught:
            resume.download_initial_adapter(self.spec, self.config, self.destination, api, self.privacy)
        self.assertNotIn(PRIVATE, output.getvalue() + errors.getvalue() + str(caught.exception))

    def test_private_gate_is_rechecked_before_each_download_and_cleans_partial(self):
        api, _ = self.sdk()
        privacy = Mock(side_effect=[True, True, False])
        with self.assertRaises(resume.ResumeError):
            resume.download_initial_adapter(self.spec, self.config, self.destination, api, privacy)
        self.assertEqual(self.downloads, [resume.FILES[0]])
        self.assertFalse(self.destination.exists())

    def test_nonzero_baseline_is_not_a_new_weight_update(self):
        raw = container(tensors(bits=[1] * 16))
        result = self.compare(raw, raw)
        self.assertFalse(result['weights_updated'])
        self.assertEqual(result['standard_b_changed_elements'], 0)
        self.assertEqual(result['before_b_payload_sha256'], result['after_b_payload_sha256'])
        self.assertTrue(result['all_b_finite'])

    def test_changed_standard_b_counts_relative_update_for_all_supported_dtypes(self):
        for dtype in resume.DTYPES:
            with self.subTest(dtype=dtype), patch.object(resume, 'CHUNK', 6):
                result = self.compare(container(tensors(dtype, [1] * 16)), container(tensors(dtype, [2] + [1] * 15)))
            self.assertTrue(result['relative_weight_change_verified'])
            self.assertEqual(result['standard_b_changed_tensors'], 1)
            self.assertEqual(result['standard_b_changed_elements'], 1)
            self.assertEqual(result['b_finite_elements_per_adapter'], 16)
            self.assertNotEqual(result['before_b_payload_sha256'], result['after_b_payload_sha256'])
            self.assertEqual(result['before_file_sha256'], sha(container(tensors(dtype, [1] * 16))))

    def test_signed_zero_only_changes_are_normalized_and_do_not_prove_update(self):
        for dtype, sign in (('F32', 0x80000000), ('F16', 0x8000), ('BF16', 0x8000)):
            with self.subTest(dtype=dtype):
                result = self.compare(container(tensors(dtype, [0] * 16)), container(tensors(dtype, [sign] * 16)))
            self.assertFalse(result['weights_updated'])
            self.assertEqual(result['b_changed_elements'], 0)
            self.assertEqual(result['before_b_payload_sha256'], result['after_b_payload_sha256'])
            self.assertNotEqual(result['before_file_sha256'], result['after_file_sha256'])

    def test_nonfinite_baseline_or_after_is_rejected_in_all_dtypes(self):
        for dtype, exponent in (('F32', 0x7F800000), ('F16', 0x7C00), ('BF16', 0x7F80)):
            clean = container(tensors(dtype))
            for nonfinite in (exponent, exponent | 1):
                bad = container(tensors(dtype, [nonfinite] + [1] * 15))
                for before, after in ((clean, bad), (bad, clean)):
                    with self.subTest(dtype=dtype, nonfinite=nonfinite), self.assertRaisesRegex(resume.ResumeError, 'relative_lora_b_nonfinite'):
                        self.compare(before, after)

    def test_shape_dtype_names_or_pair_mismatch_are_rejected(self):
        raw = container(tensors())
        cases = [container(tensors('F16')), container(tensors(output=2)),
                 container(tensors(prefix='other.block')), container(tensors()[1:])]
        for bad in cases:
            with self.assertRaises(resume.ResumeError):
                self.compare(raw, bad)

    def test_embedding_only_or_a_only_change_is_not_standard_b_evidence(self):
        before = container(tensors(embedding=True))
        after = container(tensors(embedding=True, bits=[2] + [1] * 15))
        result = self.compare(before, after)
        self.assertFalse(result['weights_updated'])
        self.assertEqual(result['embedding_b_changed_elements'], 1)
        self.assertEqual(result['standard_b_changed_tensors'], 0)
        changed_a = tensors()
        changed_a[0] = (*changed_a[0][:3], [1] * 16)
        result = self.compare(container(tensors()), container(changed_a))
        self.assertFalse(result['weights_updated'])

    def test_header_order_offsets_and_metadata_do_not_create_false_relative_change(self):
        result = self.compare(container(tensors(), metadata={'fixture': 'old'}),
                              container(tensors(), reverse=True, metadata={'fixture': 'new'}))
        self.assertFalse(result['weights_updated'])
        self.assertEqual(result['before_b_payload_sha256'], result['after_b_payload_sha256'])

    def test_malformed_offsets_header_and_unsupported_rank_fail_closed(self):
        raw = container(tensors())
        for bad in (b'not-a-safetensors-file', struct.pack('<Q', resume.MAX_HEADER_BYTES + 1) + b'{}', raw[:-1]):
            with self.assertRaises(resume.ResumeError):
                self.compare(raw, bad)
        path = self.root / 'fixture.safetensors'
        path.write_bytes(raw)
        with self.assertRaisesRegex(resume.ResumeError, 'unsupported_continuation_rank'):
            resume.compare_lora_b(path, path, 15)

    def test_moe_3d_and_folded_pairs_have_strict_rank_shapes(self):
        for a_shape, b_shape in (([2, 16, 1], [2, 1, 16]), ([32, 1], [1, 32])):
            factors = [('base.experts.lora_A.weight', 'BF16', a_shape, [0] * 32),
                       ('base.experts.lora_B.weight', 'BF16', b_shape, [1] * 32)]
            changed = [factors[0], (*factors[1][:3], [2] + [1] * 31)]
            with self.subTest(shape=b_shape):
                result = self.compare(container(factors), container(changed))
                self.assertTrue(result['weights_updated'])
                self.assertEqual(result['standard_b_changed_elements'], 1)
        empty = [('base.block.lora_A.weight', 'F32', [16, 0], []), tensors()[1]]
        with self.assertRaises(resume.ResumeError):
            self.compare(container(empty), container(empty))

    def test_exact_metadata_role_base_rank_and_visibility_are_required(self):
        for field, value in (('role', 'chat'), ('base_model', 'unsloth/QwQ-32B'), ('rank', True), ('private', False)):
            api, artifact = self.sdk()
            artifact.metadata[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(resume.ResumeError, 'source_artifact_metadata_mismatch'):
                resume.download_initial_adapter(self.spec, self.config, self.destination, api, self.privacy)
            self.assertEqual(self.downloads, [])

    def test_returned_symlink_is_rejected_even_when_bytes_and_hash_match(self):
        api, _ = self.sdk()
        original = Path.is_symlink
        def symlink(path):
            return path.name == resume.FILES[0] and path.parent.name.startswith('.download-') or original(path)
        with patch.object(Path, 'is_symlink', symlink), self.assertRaisesRegex(resume.ResumeError, 'downloaded_adapter_file_invalid'):
            resume.download_initial_adapter(self.spec, self.config, self.destination, api, self.privacy)
        self.assertFalse(self.destination.exists())

    def test_directory_collision_after_private_metadata_does_not_delete_foreign_files(self):
        api, artifact = self.sdk()
        def collide(*_, **__):
            self.destination.mkdir()
            (self.destination / 'foreign').write_text(PRIVATE)
            return artifact
        api.artifact.side_effect = collide
        with self.assertRaises(resume.ResumeError):
            resume.download_initial_adapter(self.spec, self.config, self.destination, api, self.privacy)
        self.assertEqual((self.destination / 'foreign').read_text(), PRIVATE)


if __name__ == '__main__':
    unittest.main()
