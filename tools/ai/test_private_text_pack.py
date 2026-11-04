"""Synthetic local fixtures only. No model, GPU, API or tokenizer download."""
from contextlib import redirect_stdout
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import private_text_pack as packing
from private_contest_delta import canonical, sha_file

PRIVATE='SYNTHETIC_PRIVATE_SOURCE_OR_AUTH_MUST_NOT_BE_LOGGED'


class ByteTokenizer:
    """Exact UTF-8 byte fallback fixture, with the official EOS as one token."""
    def __init__(self):self.truncation_disabled=False;self.padding_disabled=False
    def no_truncation(self):self.truncation_disabled=True
    def no_padding(self):self.padding_disabled=True
    def token_to_id(self,text):return 1000 if text==packing.EOS else None
    def encode(self,text,add_special_tokens=False):
        assert add_special_tokens is False
        ids=[]
        for i,part in enumerate(text.split(packing.EOS)):
            if i:ids.append(1000)
            ids.extend(part.encode('utf8'))
        return SimpleNamespace(ids=ids)


def row_for(text,split='train',source='a'*64,identifier='fixture-row'):
    return {'id':identifier,'source_id':'contest-native:'+source,'document_id':'contest-pdf:'+source,
        'review_status':'approved','text':text,'extra_row_field':{'preserve':[1,2,PRIVATE]},
        'metadata':{'dataset_version':'fixture-native','target_role':'solver','role':'text',
            'group_id':'contest-pdf:'+source,'split':split,'content_type':'competition_problem',
            'source_ids':['contest-native:'+source],'scan_suspect':False,'ocr_performed':False,
            'token_length_measured':False,'human_reviewed':False,'scientifically_verified':False,
            'text_sha256':packing.text_sha(text),'char_start':40,'char_end':40+len(text),
            'page_number':3,'quality_evidence':{'preserve':['nested',PRIVATE]},
            'haslalab_provenance':{'source_id':'contest-native:'+source,'local_source_sha256':source,
                'source_family':'competition_document','original_locator':'page:3','extraction':'native'}}}


class TextPackTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.input=self.root/'input';self.input.mkdir()
        self.tokenizer_dir=self.root/'tokenizer';self.tokenizer_dir.mkdir();self.output=self.root/'output'
        (self.tokenizer_dir/'tokenizer.json').write_bytes(b'{"synthetic_fixture":true}')
        (self.tokenizer_dir/'tokenizer_config.json').write_bytes(canonical({'eos_token':packing.EOS,'tokenizer_class':'Qwen2Tokenizer'}))
        self.tokenizer_pin=sha_file(self.tokenizer_dir/'tokenizer.json')
        self.config_pin=sha_file(self.tokenizer_dir/'tokenizer_config.json')
        self.rows={'train':[row_for('TRAIN content is losslessly kept. '*30)],
            'validation':[row_for('VALIDATION data remains separate. '*20,'validation','b'*64,'held-row')]}
        self.write_input()
        self.tokenizer=ByteTokenizer()
        self.factory=Mock(return_value=SimpleNamespace(Tokenizer=SimpleNamespace(from_file=Mock(return_value=self.tokenizer)),__version__='synthetic-fixture'))
        self.real_loader=packing.load_tokenizer
        self.addCleanup(patch.stopall)
        patch.object(packing,'load_tokenizer',side_effect=lambda *a,**kw:self.real_loader(*a,loader=self.factory,**kw)).start()
        import requests
        patch.object(requests.sessions.Session,'request',side_effect=AssertionError('network forbidden')).start()
        patch('socket.create_connection',side_effect=AssertionError('network forbidden')).start()
    def write_input(self):
        files={}
        for split,rows in self.rows.items():
            raw=b''.join(canonical(r) for r in rows);path=self.input/(split+'.text.jsonl');path.write_bytes(raw)
            files[split]={'bytes':len(raw),'sha256':sha_file(path),'records':len(rows)}
        self.manifest={'schema_version':1,'kind':'private_contest_native_delta','private':True,
            'target_role':'solver','format':'text','native_extraction_gate_passed':True,'ocr_performed':False,
            'human_reviewed':False,'scientifically_verified':False,'training_or_upload_performed':False,
            'token_length_measured':False,'partial_source_inventory':True,'files':files}
        (self.input/'manifest.json').write_bytes(canonical(self.manifest));self.input_pin=sha_file(self.input/'manifest.json')
    def prepare(self,**changes):
        args=dict(input_dir=self.input,input_manifest_sha256=self.input_pin,tokenizer_dir=self.tokenizer_dir,
            tokenizer_sha256=self.tokenizer_pin,tokenizer_config_sha256=self.config_pin,output_dir=self.output,
            dataset_version='fixture-packed-v1',max_tokens=1024)
        args.update(changes);return packing.prepare(**args)
    def output_rows(self,split):
        return [json.loads(t) for t in (self.output/(split+'.text.jsonl')).read_text(encoding='utf8').splitlines()]

    def test_pipeline_measures_eos_preserves_all_metadata_and_passes_existing_gates(self):
        result=self.prepare(max_tokens=64)
        self.assertTrue(result['training_ready']);self.assertTrue(result['token_length_measured'])
        self.assertTrue(result['existing_solver_gates_passed'])
        for split,originals in self.rows.items():
            recovered={r['id']:[] for r in originals}
            for row in self.output_rows(split):
                self.assertLessEqual(row['metadata']['tokens_including_eos'],64)
                self.assertEqual(row['metadata']['tokens_including_eos'],len(self.tokenizer.encode(row['text']+packing.EOS).ids))
                for segment in row['metadata']['packing']['segments']:
                    original=next(r for r in originals if r['id']==segment['original_id'])
                    text=row['text'][segment['packed_char_start']:segment['packed_char_end']]
                    recovered[original['id']].append((segment['original_char_start'],text))
                    self.assertEqual(segment['metadata'],original['metadata'])
                    self.assertEqual(segment['original_fields'],{k:v for k,v in original.items() if k not in ('text','metadata')})
            for original in originals:self.assertEqual(''.join(t for _,t in sorted(recovered[original['id']])),original['text'])
        self.assertTrue(self.tokenizer.truncation_disabled and self.tokenizer.padding_disabled)

    def test_1024_includes_terminal_eos_and_1024_payload_is_split(self):
        fitting=list(packing.split_row(row_for('x'*1023),self.tokenizer))
        self.assertEqual([p['tokens_including_eos'] for p in fitting],[1024])
        row=row_for('x'*1024)
        pieces=list(packing.split_row(row,self.tokenizer))
        self.assertEqual([p['tokens_including_eos'] for p in pieces],[513,513])
        self.assertEqual(''.join(p['text'] for p in pieces),row['text'])

    def test_balanced_long_sources_keep_shared_tiny_footer_with_context(self):
        footer='\nEND\n'
        texts=[('Algebra exercise: factor polynomials and compare roots. '*24)[:1023]+footer,
            ('Astronomy exercise: estimate stellar flux and orbital periods. '*24)[:1023]+footer]
        # The former 1023-byte payload prefixes left this identical tiny tail.
        self.assertEqual([text[1023:] for text in texts],[footer,footer])
        self.rows={'train':[row_for(texts[0])],
            'validation':[row_for(texts[1],'validation','b'*64,'held-row')]}
        piece_sets=[]
        for original in (self.rows['train'][0],self.rows['validation'][0]):
            pieces=list(packing.split_row(original,self.tokenizer))
            self.assertEqual(len(pieces),2)
            self.assertEqual(''.join(p['text'] for p in pieces),original['text'])
            self.assertTrue(pieces[-1]['text'].endswith(footer))
            self.assertGreater(len(pieces[-1]['text']),len(footer))
            self.assertTrue(all(p['tokens_including_eos']==packing.measure(p['text'],self.tokenizer)
                and p['tokens_including_eos']<=1024 for p in pieces))
            piece_sets.append({p['segment_text_sha256'] for p in pieces})
        self.assertTrue(piece_sets[0].isdisjoint(piece_sets[1]))
        self.write_input();result=self.prepare()
        self.assertTrue(result['training_ready'] and result['existing_solver_gates_passed'])
        for split in ('train','validation'):
            self.assertEqual(len(self.output_rows(split)),2)

    def test_unicode_combining_whitespace_and_existing_eos_are_exact(self):
        text=' 한글🙂e\u0301\n\t'+packing.EOS+' αβ\n'*20+'\r\n  '
        row=row_for(text);pieces=list(packing.split_row(row,self.tokenizer,capacity=16))
        self.assertEqual(''.join(p['text'] for p in pieces),text)
        self.assertEqual([p['original_char_start'] for p in pieces][0],0)
        self.assertEqual(pieces[-1]['original_char_end'],len(text))
        self.assertEqual([p['original_char_start'] for p in pieces[1:]],
            [p['original_char_end'] for p in pieces[:-1]])
        self.assertTrue(all(p['text']==text[p['original_char_start']:p['original_char_end']]
            and p['tokens_including_eos']==packing.measure(p['text'],self.tokenizer)
            and p['tokens_including_eos']<=16 for p in pieces))

    def test_same_split_group_and_type_only_are_packed(self):
        originals=[row_for('a','train','a'*64,'a'),row_for('b','train','a'*64,'b'),
            row_for('c','train','c'*64,'c'),row_for('d','validation','d'*64,'d')]
        originals[1]['metadata']['content_type']='solution'
        pieces=[next(packing.split_row(r,self.tokenizer)) for r in originals]
        bins=list(packing.arrange(pieces))
        self.assertEqual(len(bins),4)
        with self.assertRaisesRegex(packing.PackError,'packing_crossed_boundary'):
            packing.pack(pieces,self.tokenizer,'fixture')

    def test_same_boundary_short_rows_pack_with_eos_separator_only(self):
        originals=[row_for('abc',identifier='one'),row_for('def',identifier='two')]
        pieces=[next(packing.split_row(r,self.tokenizer,input_index=i)) for i,r in enumerate(originals)]
        bins=list(packing.arrange(pieces,capacity=16));self.assertEqual(len(bins),1)
        row=packing.pack(bins[0],self.tokenizer,'fixture',capacity=16)
        self.assertEqual(row['text'],'abc'+packing.EOS+'def');self.assertEqual(row['metadata']['tokens_including_eos'],8)

    def test_reconstruction_detects_span_metadata_text_and_coverage_tampering(self):
        original=row_for('abc');pieces=list(packing.split_row(original,self.tokenizer))
        packed=packing.pack(pieces,self.tokenizer,'fixture');expected={original['id']:original}
        mutations=[lambda r:r['metadata']['packing']['segments'][0].update(original_char_end=2),
            lambda r:r['metadata']['packing']['segments'][0]['metadata'].update(page_number=99),
            lambda r:r['metadata']['packing']['segments'][0].update(segment_text_sha256='f'*64),
            lambda r:r.update(text='modified')]
        from collections import defaultdict
        for mutation in mutations:
            row=copy.deepcopy(packed);mutation(row)
            with self.assertRaises(packing.PackError):packing.verify_packed(row,expected,defaultdict(set),self.tokenizer)
        with self.assertRaisesRegex(packing.PackError,'coverage_gap_or_overlap'):
            packing.verify_coverage(expected,{original['id']:{(1,3)}})
        coverage=defaultdict(set);packing.verify_packed(packed,expected,coverage,self.tokenizer)
        with self.assertRaisesRegex(packing.PackError,'original_span_repeated'):
            packing.verify_packed(packed,expected,coverage,self.tokenizer)

    def test_original_repetitions_are_kept_with_distinct_provenance_identities(self):
        self.rows['train']=[row_for('A'*126)]
        self.write_input();self.prepare(max_tokens=64)
        values=self.output_rows('train')
        self.assertEqual(len(values),2);self.assertEqual(values[0]['text'],values[1]['text'])
        self.assertNotEqual(values[0]['id'],values[1]['id'])

    def test_duplicate_original_content_and_source_split_conflicts_fail(self):
        self.rows['validation'][0]['text']=self.rows['train'][0]['text']
        self.rows['validation'][0]['metadata']['text_sha256']=packing.text_sha(self.rows['validation'][0]['text']);self.write_input()
        with self.assertRaisesRegex(packing.PackError,'duplicate_original_input_content'):self.prepare()
        self.rows['validation']=[row_for('unique held text','validation','a'*64,'held')]
        self.rows['validation'][0]['metadata']['group_id']='different-group';self.write_input()
        with self.assertRaisesRegex(packing.PackError,'input_source_split_overlap'):self.prepare()

    def test_duplicate_long_pieces_across_sources_fail(self):
        self.rows={'train':[row_for('Z'*100+' train')],
            'validation':[row_for('Z'*100+' validation','validation','b'*64,'held')]}
        self.write_input()
        with self.assertRaisesRegex(packing.PackError,'duplicate_piece_crossed_split_or_source'):self.prepare(max_tokens=32)
        self.assertFalse(self.output.exists())

    def test_wrong_native_role_ocr_scan_review_and_source_fields_rejected(self):
        original=copy.deepcopy(self.rows['train'][0])
        for field,value in (('target_role','chat'),('scan_suspect',True),('ocr_performed',True),
                            ('human_reviewed',True),('scientifically_verified',True),('token_length_measured',True)):
            self.rows['train'][0]=copy.deepcopy(original);self.rows['train'][0]['metadata'][field]=value;self.write_input()
            with self.subTest(field=field),self.assertRaises(packing.PackError):self.prepare()
        self.rows['train'][0]=copy.deepcopy(original);self.rows['train'][0]['review_status']='pending';self.write_input()
        with self.assertRaisesRegex(packing.PackError,'input_record_rejected'):self.prepare()

    def test_manifest_and_input_sha_pins_precede_tokenizer_import(self):
        with self.assertRaises(packing.DeltaError):self.prepare(input_manifest_sha256='f'*64)
        self.factory.assert_not_called()
        (self.input/'train.text.jsonl').write_bytes(b'changed')
        with self.assertRaises(packing.DeltaError):self.prepare()
        self.factory.assert_not_called()

    def test_both_tokenizer_sha_pins_precede_lazy_import(self):
        for tp,cp in (('f'*64,self.config_pin),(self.tokenizer_pin,'f'*64)):
            factory=Mock()
            with self.assertRaises(packing.DeltaError):self.real_loader(self.tokenizer_dir,tp,cp,loader=factory)
            factory.assert_not_called()

    def test_official_eos_and_tokenizer_configuration_required(self):
        (self.tokenizer_dir/'tokenizer_config.json').write_bytes(canonical({'eos_token':'wrong','tokenizer_class':'Qwen2Tokenizer'}))
        with self.assertRaisesRegex(packing.PackError,'official_qwq_config_required'):
            self.real_loader(self.tokenizer_dir,self.tokenizer_pin,sha_file(self.tokenizer_dir/'tokenizer_config.json'),loader=self.factory)
        self.factory.assert_not_called()

    def test_tokenizer_errors_are_fixed_codes_never_raw_source(self):
        tokenizer=ByteTokenizer();tokenizer.encode=Mock(side_effect=RuntimeError(PRIVATE))
        with self.assertRaisesRegex(packing.PackError,'token_measurement_failed') as caught:
            packing.measure(PRIVATE,tokenizer)
        self.assertNotIn(PRIVATE,str(caught.exception))

    def test_balanced_split_needs_no_monotonic_token_count_assumption(self):
        class Nonmonotone(ByteTokenizer):
            def encode(self,text,add_special_tokens=False):
                plain=text.removesuffix(packing.EOS)
                size=4 if len(plain)%7==0 else len(plain)+1
                return SimpleNamespace(ids=[1]*(size-1)+[1000])
        tokenizer=Nonmonotone();original=row_for('abcdefghi'*25)
        pieces=list(packing.split_row(original,tokenizer,capacity=8))
        self.assertGreater(packing.measure('abcdef',tokenizer),packing.measure('abcdefg',tokenizer))
        self.assertEqual(''.join(p['text'] for p in pieces),original['text'])
        self.assertTrue(any(len(p['text'])>8 for p in pieces))
        self.assertTrue(all(p['tokens_including_eos']==packing.measure(p['text'],tokenizer)
            and p['tokens_including_eos']<=8 for p in pieces))

    def test_oversized_single_unicode_character_fails_closed(self):
        with self.assertRaisesRegex(packing.PackError,'one_character_exceeds_capacity'):
            list(packing.split_row(row_for('🙂'),self.tokenizer,capacity=4))

    def test_nonadditive_eos_boundaries_fail_closed(self):
        class Nonadditive(ByteTokenizer):
            def encode(self,text,add_special_tokens=False):
                ids=super().encode(text,add_special_tokens).ids
                if text.count(packing.EOS)>1:ids=ids[1:]
                return SimpleNamespace(ids=ids)
        tokenizer=Nonadditive();parts=[next(packing.split_row(row_for(t,identifier=t),tokenizer)) for t in ('abc','def')]
        with self.assertRaisesRegex(packing.PackError,'packed_eos_boundary_or_capacity_rejected'):
            packing.pack(parts,tokenizer,'fixture')

    def test_empty_splits_capacity_and_existing_output_are_rejected(self):
        for capacity in (0,1,True,1025):
            with self.subTest(capacity=capacity),self.assertRaisesRegex(packing.PackError,'invalid_token_capacity'):
                self.prepare(max_tokens=capacity)
        self.rows['validation']=[];self.write_input()
        with self.assertRaisesRegex(packing.PackError,'input_inventory_rejected'):self.prepare()
        self.output.mkdir()
        with self.assertRaisesRegex(packing.PackError,'output_collision_or_overlap'):self.prepare()

    def test_size_limits_and_collision_fail_atomically(self):
        with patch.object(packing,'MAX_OUTPUT',10),self.assertRaisesRegex(packing.PackError,'output_size_limit'):self.prepare()
        self.assertFalse(self.output.exists())
        with patch.object(packing,'MAX_PIECES',1),self.assertRaisesRegex(packing.PackError,'piece_count_limit'):self.prepare(max_tokens=32)
        self.assertFalse(self.output.exists())

    def test_input_change_before_publish_is_detected(self):
        original=packing.pack;changed=False
        def mutate(*args,**kwargs):
            nonlocal changed
            if not changed:(self.input/'train.text.jsonl').write_bytes(b'changed');changed=True
            return original(*args,**kwargs)
        with patch.object(packing,'pack',side_effect=mutate),self.assertRaisesRegex(packing.PackError,'input_changed_during_pack'):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_deterministic_outputs_and_stdout_are_metadata_only(self):
        first=self.prepare();other=self.root/'another';second=self.prepare(output_dir=other)
        for split in ('train','validation'):
            self.assertEqual((self.output/(split+'.text.jsonl')).read_bytes(),(other/(split+'.text.jsonl')).read_bytes())
        with redirect_stdout(io.StringIO()) as stdout:
            packing.main(['--input-dir',str(self.input),'--input-manifest-sha256',self.input_pin,
                '--tokenizer-dir',str(self.tokenizer_dir),'--tokenizer-sha256',self.tokenizer_pin,
                '--tokenizer-config-sha256',self.config_pin,'--output-dir',str(self.root/'cli'),
                '--dataset-version','fixture-cli'])
        self.assertNotIn(PRIVATE,stdout.getvalue());self.assertTrue(json.loads(stdout.getvalue())['training_ready'])
        self.assertEqual(first['files'],second['files'])

    def test_module_import_is_lazy_and_cli_errors_have_no_traceback_or_body(self):
        script=Path(packing.__file__)
        probe=subprocess.run([sys.executable,'-c','import private_text_pack,sys; print("tokenizers" in sys.modules, "torch" in sys.modules)'],
            cwd=script.parent,capture_output=True,text=True,timeout=30)
        self.assertEqual(probe.returncode,0);self.assertEqual(probe.stdout.strip(),'False False')
        run=subprocess.run([sys.executable,str(script),'--input-dir',str(self.input),'--input-manifest-sha256','f'*64,
            '--tokenizer-dir',str(self.tokenizer_dir),'--tokenizer-sha256',self.tokenizer_pin,
            '--tokenizer-config-sha256',self.config_pin,'--output-dir',str(self.output),'--dataset-version','fixture'],
            capture_output=True,text=True,timeout=30)
        self.assertEqual(run.returncode,1);self.assertNotIn(PRIVATE,run.stdout+run.stderr)
        self.assertNotIn('Traceback',run.stdout+run.stderr)


if __name__=='__main__':unittest.main()
