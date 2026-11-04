"""CPU-only encrypted staging fixtures. No real sockets, APIs, tunnels or GPUs."""
import base64
import contextlib
import gzip
import io
import json
from pathlib import Path
import runpy
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

try:
    from nacl.secret import SecretBox
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / '.private-problem-bank-runtime/hasla-ai-corpus/secure-upload-runtime'))
    from nacl.secret import SecretBox

import private_stage_corpus as stage


PRIVATE = 'SYNTHETIC_PRIVATE_STAGE_FIXTURE'


def fixture():
    files = {}
    for split in ('train', 'validation'):
        row = {'text': PRIVATE + split, 'metadata': {'group_id': split, 'split': split, 'page_number': 1,
            'drive_provenance': {'drive_file_id': 'fixture', 'local_original_pdf_sha256': 'a' * 64}}}
        files[split] = (json.dumps(row) + '\n').encode()
    cipher, descriptor = stage.make_bundle('solver', 'fixture-v1', files['train'], files['validation'], key=b'k' * 32, nonce=b'n' * 24)
    descriptor['url'] = 'https://fixture.trycloudflare.com/input'
    return cipher, descriptor, files


class StageTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(patch.stopall)
        for name in ('get', 'post', 'request', 'put', 'delete'):
            patch.object(stage.requests, name, side_effect=AssertionError('network forbidden')).start()
        self.cipher, self.descriptor, self.files = fixture()

    def response(self, cipher=None, status=200, length=None):
        value = self.cipher if cipher is None else cipher
        class Response:
            status_code = status
            headers = {'Content-Length': str(len(value)) if length is None else length}
            closed = False
            def iter_content(self, chunk_size):
                for i in range(0, len(value), 13):
                    yield value[i:i + 13]
            def close(self):
                self.closed = True
        return Response()

    def test_roundtrip_is_authenticated_two_file_frame_and_no_plaintext_in_cipher(self):
        metadata, files = stage.decode_bundle(self.cipher, self.descriptor)
        self.assertEqual(files, self.files)
        self.assertEqual(metadata['role'], 'solver')
        self.assertNotIn(PRIVATE.encode(), self.cipher)
        self.assertEqual(set(files), {'train', 'validation'})

    def test_tiny_bundle_never_requests_a_large_upfront_decompression_read(self):
        real = gzip.GzipFile
        sizes = []
        class MemoryCeiling:
            def __init__(self, *args, **kwargs):
                self.stream = real(*args, **kwargs)
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.stream.close()
            def read(self, size=-1):
                sizes.append(size)
                if not 0 < size <= 64 * 1024:
                    raise MemoryError('synthetic allocation ceiling')
                return self.stream.read(size)
        with patch.object(stage.gzip, 'GzipFile', MemoryCeiling):
            metadata, files = stage.decode_bundle(self.cipher, self.descriptor)
        self.assertEqual(files, self.files)
        self.assertEqual(metadata['role'], 'solver')
        self.assertTrue(sizes and max(sizes) <= 64 * 1024)
        self.assertEqual(stage.PLAIN_LIMIT, 512 * 1024**2)

    def test_streaming_decompression_keeps_exact_limit_and_one_byte_over_detection(self):
        compressed = SecretBox(b'k' * 32).decrypt(self.cipher)
        plain = gzip.decompress(compressed)
        with patch.object(stage, 'PLAIN_LIMIT', len(plain)):
            _metadata, files = stage.decode_bundle(self.cipher, self.descriptor)
        self.assertEqual(files, self.files)
        with patch.object(stage, 'PLAIN_LIMIT', len(plain) - 1), self.assertRaisesRegex(stage.StageError, 'plain_size_limit'):
            stage.decode_bundle(self.cipher, self.descriptor)
        # Retain only limit+1 bytes even when the gzip payload is much larger.
        cipher = bytes(SecretBox(b'k' * 32).encrypt(gzip.compress(b'x' * 8192), nonce=b'n' * 24))
        descriptor = {**self.descriptor, 'cipher_bytes':len(cipher), 'cipher_sha256':stage.sha(cipher)}
        real = gzip.GzipFile
        consumed = []
        class CountingStream:
            def __init__(self, *args, **kwargs):
                self.stream = real(*args, **kwargs)
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.stream.close()
            def read(self, size=-1):
                value = self.stream.read(size)
                consumed.append(len(value))
                return value
        with patch.object(stage, 'PLAIN_LIMIT', 256), patch.object(stage.gzip, 'GzipFile', CountingStream), self.assertRaisesRegex(stage.StageError, 'plain_size_limit'):
            stage.decode_bundle(cipher, descriptor)
        self.assertEqual(sum(consumed), 257)

    def test_solver_supervised_chat_roundtrip_keeps_format_and_source_guards(self):
        files = {}
        for split, raw in self.files.items():
            row = json.loads(raw)
            text = row.pop('text')
            row['messages'] = [{'role': 'user', 'content': 'Source-grounded fixture question ' + split},
                               {'role': 'assistant', 'content': text}]
            files[split] = (json.dumps(row) + '\n').encode()
        cipher, descriptor = stage.make_bundle('solver', 'solver-chat-fixture', files['train'], files['validation'],
            data_format='chat', key=b'k' * 32, nonce=b'n' * 24)
        descriptor['url'] = self.descriptor['url']
        metadata, decoded = stage.decode_bundle(cipher, descriptor)
        self.assertEqual(metadata['format'], 'chat')
        self.assertEqual(decoded, files)
        broken = json.loads(files['train'])
        broken['metadata'].pop('drive_provenance')
        with self.assertRaisesRegex(stage.StageError, 'source_or_row'):
            stage.make_bundle('solver', 'solver-chat-fixture', (json.dumps(broken) + '\n').encode(), files['validation'], data_format='chat')
        with self.assertRaisesRegex(stage.StageError, 'invalid_format'):
            stage.make_bundle('chat', 'wrong-role-fixture', self.files['train'], self.files['validation'], data_format='text')

    def test_cipher_hash_key_header_and_raw_metadata_mismatch_fail_closed(self):
        for update in ({'cipher_sha256':'0'*64}, {'key_b64':base64.b64encode(b'x'*32).decode()},
                       {'header_sha256':'0'*64}, {'train':{**self.descriptor['train'],'raw_sha256':'0'*64}}):
            with self.subTest(update_keys=list(update)),self.assertRaises(stage.StageError):
                stage.decode_bundle(self.cipher,{**self.descriptor,**update})
        bad=bytearray(self.cipher)
        bad[-1]^=1
        with self.assertRaises(stage.StageError):
            stage.decode_bundle(bytes(bad),{**self.descriptor,'cipher_sha256':stage.sha(bad)})

    def test_descriptor_rejects_noncanonical_network_targets_and_bad_secrets(self):
        for url in ('http://fixture.trycloudflare.com/input','https://evil.example/input', 'https://fixture.trycloudflare.com/input?secret=x',
                    'https://user@fixture.trycloudflare.com/input','https://fixture.trycloudflare.com:443/input','https://fixture.trycloudflare.com/../data'):
            with self.subTest(url=url),self.assertRaises((stage.StageError,ValueError)):
                stage.descriptor_check({**self.descriptor,'url':url})
        for update in ({'version':True},{'bearer':'short'},{'key_b64':'invalid'}, {'cipher_bytes':stage.CIPHER_LIMIT+1}):
            with self.subTest(update=update),self.assertRaises(stage.StageError):
                stage.descriptor_check({**self.descriptor,**update})

    def test_gzip_plain_and_header_limits_stop_bombs_without_extracting_paths(self):
        with patch.object(stage,'PLAIN_LIMIT',10),self.assertRaisesRegex(stage.StageError,'plain_size_limit'):
            stage.decode_bundle(self.cipher,self.descriptor)
        payload=struct.pack('>Q',stage.HEADER_LIMIT+1)+b'{}'
        cipher=bytes(SecretBox(b'k'*32).encrypt(gzip.compress(payload),nonce=b'n'*24))
        descriptor={**self.descriptor,'cipher_bytes':len(cipher),'cipher_sha256':stage.sha(cipher)}
        with self.assertRaisesRegex(stage.StageError,'header_size'):
            stage.decode_bundle(cipher,descriptor)
        with self.assertRaises(stage.StageError):
            stage.strict_json('{"path":"../private","path":"other"}')

    def test_row_source_split_and_record_counts_are_validated(self):
        row=json.loads(self.files['train'])
        row['metadata'].pop('drive_provenance')
        with self.assertRaisesRegex(stage.StageError,'source_or_row'):
            stage.make_bundle('solver','fixture-v1',(json.dumps(row)+'\n').encode(),self.files['validation'])
        metadata=stage.metadata_check(self.descriptor)
        metadata['train']['records']=2
        with self.assertRaisesRegex(stage.StageError,'record_count'):
            stage.validate_corpora(metadata,self.files)
        row=json.loads(self.files['validation'])
        row['metadata']['group_id']='train'
        with self.assertRaisesRegex(stage.StageError,'source_split_overlap'):
            stage.make_bundle('solver','fixture-v1',self.files['train'],(json.dumps(row)+'\n').encode())

    def test_fetch_is_bounded_authenticated_no_redirect_and_always_closes(self):
        response=self.response()
        def get(url,**kwargs):
            self.assertEqual(url,self.descriptor['url'])
            self.assertEqual(kwargs['headers'],{'Authorization':'Bearer '+self.descriptor['bearer']})
            self.assertFalse(kwargs['allow_redirects'])
            self.assertTrue(kwargs['stream'])
            return response
        self.assertEqual(stage.fetch_cipher(self.descriptor,get=get,clock=lambda:0),self.cipher)
        self.assertTrue(response.closed)
        for response in (self.response(status=302),self.response(length=str(stage.CIPHER_LIMIT+1)),self.response(cipher=self.cipher+b'x')):
            with self.assertRaises(stage.StageError):
                stage.fetch_cipher(self.descriptor,get=lambda *args,**kwargs:response,clock=lambda:0)
            self.assertTrue(response.closed)
        response=self.response()
        ticks=iter([0,601])
        with self.assertRaisesRegex(stage.StageError,'deadline'):
            stage.fetch_cipher(self.descriptor,get=lambda *args,**kwargs:response,clock=lambda:next(ticks,601))
        self.assertTrue(response.closed)

    def sdk(self):
        observed=SimpleNamespace(files=[],finished=False,uploaded=False)
        class Artifact:
            def __init__(self,name,type,metadata):
                self.qualified_name='fixture-entity/'+stage.PROJECT+'/'+name+':v3'
                self.metadata=metadata
            def add_file(self,path,name):
                observed.files.append((name,Path(path).read_bytes()))
            def wait(self,timeout):
                self.timeout=timeout
        class Run:
            def log_artifact(self,artifact):
                observed.uploaded=True
            def finish(self):
                observed.finished=True
        def init(**kwargs):
            print('PRIVATE_SDK_DIAGNOSTIC')
            self.assertEqual(kwargs['project'],stage.PROJECT)
            self.assertEqual(kwargs['resume'],'never')
            return Run()
        return SimpleNamespace(Settings=lambda **kwargs:kwargs,init=init,Artifact=Artifact),observed

    def query(self,document,variables=None):
        self.assertNotIn('mutation',document.lower())
        return {'viewer':{'entity':'fixture-entity'}} if variables is None else {'project':{'name':stage.PROJECT,'access':'PRIVATE'}}

    def test_private_gate_precedes_fetch_sdk_and_uploads_only_two_named_files(self):
        sdk,observed=self.sdk()
        env={'WANDB_API_KEY':'PRIVATE_KEY','GITHUB_RUN_ID':'12345','HASLA_STAGE_INPUT':json.dumps(self.descriptor)}
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            event=stage.stage(env,query=self.query,get=lambda *args,**kwargs:self.response(),sdk=sdk)
        self.assertEqual(output.getvalue(),'')
        self.assertTrue(observed.finished and observed.uploaded)
        self.assertEqual([name for name,_ in observed.files],['train.text.jsonl','validation.text.jsonl'])
        self.assertTrue(event['input_artifact'].endswith(':v3'))
        self.assertEqual(event['train'],self.descriptor['train'])
        for secret in (PRIVATE,'PRIVATE_KEY',self.descriptor['url'],self.descriptor['bearer'],self.descriptor['key_b64'],self.descriptor['header_sha256']):
            self.assertNotIn(secret,json.dumps(event))
        called=[]
        def nonprivate(document,variables=None):
            return {'viewer':{'entity':'fixture-entity'}} if variables is None else {'project':{'name':stage.PROJECT,'access':'PUBLIC'}}
        with self.assertRaisesRegex(stage.StageError,'private_project'):
            stage.stage(env,query=nonprivate,get=lambda *args,**kwargs:called.append(True),sdk=sdk)
        self.assertEqual(called,[])

    def test_gpu_credentials_and_arbitrary_errors_never_leave_main(self):
        for key in ('HF_TOKEN','RUNPOD_API_KEY','HUGGING_FACE_HUB_TOKEN','HUGGINGFACE_TOKEN','HF_API_TOKEN'):
            with self.assertRaisesRegex(stage.StageError,'unexpected_gpu'):
                stage.stage({key:'PRIVATE_SECRET'})
        output=io.StringIO()
        with patch.object(stage,'stage',side_effect=RuntimeError('PRIVATE_TRACE https://secret.example TOKEN')),contextlib.redirect_stdout(output):
            self.assertEqual(stage.main(),1)
        self.assertNotIn('PRIVATE_',output.getvalue())
        self.assertEqual(json.loads(output.getvalue())['code'],'private_staging_failed')


class LocalControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=Path(__file__).resolve().parents[3]/'operations/hasla-ai-stage-control.py'
        cls.control=runpy.run_path(str(path),run_name='stage_control_offline')

    def test_only_exact_path_and_constant_time_bearer_gets_cipher(self):
        authorize=self.control['authorized_request']
        self.assertTrue(authorize('/input','Bearer '+('b'*43),'b'*43))
        for path,auth in (('/input?x=1','Bearer '+('b'*43)),('/../cipher.bin','Bearer '+('b'*43)),('/input','wrong'),('/input','한글')):
            self.assertFalse(authorize(path,auth,'b'*43))

    def test_private_output_rejects_git_and_onedrive_without_starting_servers(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'.git').mkdir()
            with self.assertRaisesRegex(stage.StageError,'private_directory'):
                self.control['private_directory'](root/'private')
        with self.assertRaisesRegex(stage.StageError,'private_directory'):
            self.control['private_directory'](Path.home()/'OneDrive - fixture'/'private')

    def test_installer_checks_pinned_official_sha_before_writing(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,size):return b'WRONG_BINARY'
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'cloudflared.exe'
            with self.assertRaisesRegex(stage.StageError,'checksum'):
                self.control['install_cloudflared'](output,opener=lambda *args,**kwargs:Response())
            self.assertFalse(output.exists())

    def test_stage_dispatch_only_has_cpu_flag_and_cannot_repeat(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'transfer.private.json').write_text('{}')
            (root/'published.json').write_text('{}')
            calls=[]
            result=self.control['dispatch'](root,api=lambda *args:calls.append(args))
            self.assertFalse(result['gpu_creation_enabled'])
            self.assertEqual(len(calls),1)
            method,path,body=calls[0]
            self.assertEqual(method,'POST')
            self.assertEqual(body['inputs']['stage_only'],'true')
            self.assertEqual(body['inputs']['preflight_only'],'true')
            self.assertEqual(body['inputs']['collection_only'],'false')
            with self.assertRaisesRegex(stage.StageError,'already_attempted'):
                self.control['dispatch'](root,api=lambda *args:self.fail('duplicate dispatch'))

    def test_only_single_sealed_descriptor_secret_is_published(self):
        from nacl.public import PrivateKey, SealedBox
        cipher,descriptor,_=fixture()
        key=PrivateKey.generate()
        calls=[]
        def api(method,path,body=None):
            calls.append((method,path,body))
            if method=='GET' and '/runs?' in path:return {'workflow_runs':[]}
            if method=='GET' and path.endswith('/public-key'):
                return {'key':base64.b64encode(bytes(key.public_key)).decode(),'key_id':'fixture-key-id'}
            self.assertEqual((method,path),('PUT','/actions/secrets/HASLA_STAGE_INPUT'))
            opened=SealedBox(key).decrypt(base64.b64decode(body['encrypted_value']))
            self.assertEqual(json.loads(opened),descriptor)
            self.assertNotIn(descriptor['bearer'],json.dumps(body))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'transfer.private.json').write_text(json.dumps(descriptor))
            (root/'ready.json').write_text('{}')
            output=io.StringIO()
            with contextlib.redirect_stdout(output):
                event=self.control['publish'](root,api=api)
            self.assertEqual(output.getvalue(),'')
            self.assertEqual(event['secret_count'],1)
            self.assertEqual(sum(method=='PUT' for method,_,_ in calls),1)
            for secret in (descriptor['url'],descriptor['bearer'],descriptor['key_b64'],descriptor['header_sha256']):
                self.assertNotIn(secret,json.dumps(event))

    def test_handler_returns_only_cipher_at_exact_authorized_route(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'cipher.bin').write_bytes(b'ENCRYPTED_ONLY')
            descriptor={'bearer':'b'*43,'cipher_bytes':14}
            Handler=self.control['handler_for'](root,descriptor)
            handler=Handler.__new__(Handler)
            handler.path='/input'
            handler.headers={'Authorization':'Bearer '+('b'*43)}
            handler.wfile=io.BytesIO()
            statuses=[]
            handler.send_response=lambda code:statuses.append(code)
            handler.send_header=lambda *args:None
            handler.end_headers=lambda:None
            handler.send_error=lambda code:statuses.append(code)
            handler.do_GET()
            self.assertEqual(handler.wfile.getvalue(),b'ENCRYPTED_ONLY')
            self.assertEqual(statuses,[200])
            for route in ('/transfer.private.json','/../cipher.bin','/input?key=x'):
                handler.path=route
                handler.wfile=io.BytesIO()
                handler.do_GET()
                self.assertEqual(statuses[-1],404)
                self.assertEqual(handler.wfile.getvalue(),b'')


if __name__ == '__main__':
    unittest.main()
