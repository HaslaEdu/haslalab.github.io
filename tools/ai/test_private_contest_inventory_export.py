"""Real ephemeral-key encryption with synthetic inventory; no service or source I/O."""
import base64
import contextlib
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch

from nacl.public import PrivateKey,SealedBox
from nacl.exceptions import CryptoError
import private_contest_delta as delta
from test_private_contest_delta import make_inventory,page_for,source_for
import test_private_contest_delta as fixtures


class InventoryExportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='hasla-inventory-export-unit-')
        self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.input=self.root/'private-input'
        self.inventory,self.pin=make_inventory(self.input,[(source_for('train'),[page_for(source_for('train'))])])
        self.raw=(self.input/'inventory.json').read_bytes();self.key=PrivateKey.generate()
        self.env={delta.EXPORT_PUBLIC_KEY:base64.b64encode(bytes(self.key.public_key)).decode(),
                  delta.EXPORT_EXPECTED_SHA:self.pin}
        self.addCleanup(patch.stopall)
        import requests
        for name in ('get','post','put','patch','delete','head','request'):
            patch.object(requests,name,side_effect=AssertionError('network forbidden')).start()

    def test_cipher_roundtrip_exact_bytes_sizes_hash_and_recipient_binding(self):
        config=delta.inventory_export_configuration(self.env,True)
        value,fragments=delta.encrypted_inventory_export(self.input,self.pin,config)
        cipher=base64.b64decode(''.join(f['ciphertext_b64'] for f in fragments),validate=True)
        compressed=SealedBox(self.key).decrypt(cipher);raw=gzip.decompress(compressed)
        self.assertEqual(raw,self.raw)
        self.assertEqual(value['raw_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(value['raw_bytes'],len(raw));self.assertEqual(value['gzip_bytes'],len(compressed))
        self.assertEqual(value['cipher_bytes'],len(cipher));self.assertEqual(len(cipher),len(compressed)+48)
        self.assertEqual(value['cipher_sha256'],hashlib.sha256(cipher).hexdigest())
        self.assertEqual(value['public_key_sha256'],hashlib.sha256(bytes(self.key.public_key)).hexdigest())
        with self.assertRaises(CryptoError):SealedBox(PrivateKey.generate()).decrypt(cipher)
        self.assertEqual((self.input/'inventory.json').read_bytes(),self.raw)

    def test_cli_emits_only_cipher_metadata_and_old_no_key_behavior_stays_unchanged(self):
        for env,exported in (({},False),(self.env,True)):
            with patch.dict(os.environ,env,clear=True),contextlib.redirect_stdout(io.StringIO()) as out:
                result=delta.main(['--input-dir',str(self.input),'--inspect'])
            self.assertEqual('inventory_export' in result,exported)
            self.assertNotIn('fixture-',out.getvalue());self.assertNotIn('archive_url',out.getvalue())
            self.assertNotIn(str(self.input),out.getvalue());self.assertNotIn(self.raw.decode(),out.getvalue())
            self.assertFalse(result['native_or_pdf_content_downloaded'])

    def test_half_invalid_or_noninspection_bindings_fail_before_any_read_or_download(self):
        cases=[({delta.EXPORT_PUBLIC_KEY:self.env[delta.EXPORT_PUBLIC_KEY]},True),
               ({delta.EXPORT_EXPECTED_SHA:self.pin},True),
               ({**self.env,delta.EXPORT_PUBLIC_KEY:'private-invalid-value'},True),
               ({**self.env,delta.EXPORT_EXPECTED_SHA:'not-sha'},True),(self.env,False)]
        for env,inspect in cases:
            with self.subTest(env=list(env),inspect=inspect),self.assertRaises(delta.DeltaError):
                delta.inventory_export_configuration(env,inspect)
        with self.assertRaises(delta.DeltaError):delta.inventory_export_configuration(self.env,True,'e'*64)
        with patch.dict(os.environ,{delta.EXPORT_PUBLIC_KEY:self.env[delta.EXPORT_PUBLIC_KEY]},clear=True), \
                patch.object(delta,'download_sources') as download,self.assertRaises(delta.DeltaError):
            delta.main(['--input-artifact','not-read','--inspect'])
        download.assert_not_called()

    def test_altered_raw_or_oversized_compressed_inventory_cannot_be_exported(self):
        config=delta.inventory_export_configuration(self.env,True)
        (self.input/'inventory.json').write_bytes(self.raw+b' ')
        with self.assertRaises(delta.DeltaError):delta.encrypted_inventory_export(self.input,self.pin,config)
        (self.input/'inventory.json').write_bytes(self.raw)
        with patch.object(delta.gzip,'compress',return_value=b'x'*(delta.MAX_INVENTORY+1)),self.assertRaises(delta.DeltaError):
            delta.encrypted_inventory_export(self.input,self.pin,config)

    def test_remote_inspection_still_downloads_inventory_only_before_encryption(self):
        # The shared fixture verifies PRIVATE twice and allows only bound-entry
        # downloads; its artifact.download method is deliberately unavailable.
        harness=fixtures.ContestDeltaTests('test_remote_inspect_downloads_inventory_only_and_rechecks_private')
        harness.setUp();self.addCleanup(harness.doCleanups)
        (report,pin),artifact,sdk,privacy,root=harness.remote(inspect=True)
        env={**self.env,delta.EXPORT_EXPECTED_SHA:pin}
        encrypted,fragments=delta.encrypted_inventory_export(root,pin,delta.inventory_export_configuration(env,True))
        self.assertEqual(artifact.downloaded,['inventory.json']);self.assertEqual(privacy.call_count,2)
        self.assertEqual(hashlib.sha256(gzip.decompress(SealedBox(self.key).decrypt(
            base64.b64decode(''.join(f['ciphertext_b64'] for f in fragments))))).hexdigest(),pin)

    def test_multifragment_cli_lines_are_bounded_and_reassemble_to_the_exact_inventory(self):
        report=json.loads(self.raw);report['synthetic_padding']=''.join(hashlib.sha256(str(i).encode()).hexdigest() for i in range(2000))
        raw=delta.canonical(report);(self.input/'inventory.json').write_bytes(raw)
        env={**self.env,delta.EXPORT_EXPECTED_SHA:hashlib.sha256(raw).hexdigest()}
        with patch.dict(os.environ,env,clear=True),contextlib.redirect_stdout(io.StringIO()) as out:
            result=delta.main(['--input-dir',str(self.input),'--inspect'])
        lines=out.getvalue().splitlines();events=[json.loads(line) for line in lines]
        metadata=events[-1]['inventory_export'];fragments=[event['inventory_export_fragment'] for event in events[:-1]]
        self.assertGreater(metadata['parts'],1)
        self.assertEqual([f['part'] for f in fragments],list(range(metadata['parts'])))
        self.assertTrue(all(len(line.encode())<=48*1024 for line in lines))
        self.assertTrue(all(len(f['ciphertext_b64'])<=32000 and f['parts']==len(fragments)
            and f['cipher_sha256']==metadata['cipher_sha256'] for f in fragments))
        encoded=''.join(f['ciphertext_b64'] for f in fragments)
        self.assertEqual(len(encoded),metadata['ciphertext_base64_characters'])
        cipher=base64.b64decode(encoded,validate=True)
        self.assertEqual(hashlib.sha256(cipher).hexdigest(),metadata['cipher_sha256'])
        self.assertEqual(gzip.decompress(SealedBox(self.key).decrypt(cipher)),raw)
        self.assertNotIn('ciphertext_b64',result['inventory_export'])


if __name__=='__main__':unittest.main()
