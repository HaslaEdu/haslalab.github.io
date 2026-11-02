"""Synthetic URL/Drive provenance checks across extraction, preparation and storage."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
import pymupdf
from source_identity import source_reference, source_key, select_profile_source


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


extractor = load('url_columns', 'extract-column-questions.py')
preparer = load('url_prepare', 'prepare-extracted.py')


class IdentityTests(unittest.TestCase):
    def test_drive_references_keep_the_existing_shape_and_separate_revisions(self):
        source = {'drive_id': 'synthetic-drive', 'revision': 'v1', 'title': 'Ignored metadata'}
        self.assertEqual(source_reference(source), {'drive_id': 'synthetic-drive', 'revision': 'v1'})
        self.assertNotEqual(source_key(source), source_key(dict(source, revision='v2')))

    def test_url_reference_excludes_attribution_from_identity_and_never_invents_drive(self):
        source = {'origin': {'kind': 'url', 'url': 'https://example.edu/problem.pdf#page=2',
                             'attribution': 'Synthetic author'}, 'revision': 'sha256:'+'a'*64}
        reference = source_reference(source)
        self.assertNotIn('drive_id', reference)
        self.assertEqual(reference['origin'], {'kind': 'url', 'url': 'https://example.edu/problem.pdf'})
        self.assertEqual(source_key(reference), source_key(source))
        with self.assertRaises(ValueError):
            source_reference(dict(source, drive_id='ambiguous-drive'))

    def test_profile_selection_is_hash_bound_and_requires_one_source_revision(self):
        a = {'drive_id': 'synthetic-drive', 'revision': 'v1', 'sha256': 'a'*64}
        b = dict(a, revision='v2', sha256='b'*64)
        self.assertIs(select_profile_source([a,b], {'drive_id': a['drive_id']}, 'b'*64), b)
        self.assertIs(select_profile_source([a,b], {'source': source_reference(a)}, 'a'*64), a)
        for sources, profile, checksum in [([a], {'source': source_reference(a)}, 'b'*64),
                ([a,dict(a,revision='v3')], {'drive_id':a['drive_id']}, 'a'*64),
                ([a], {'drive_id':a['drive_id'],'source':source_reference(a)}, 'a'*64)]:
            with self.assertRaises(ValueError):
                select_profile_source(sources, profile, checksum)

    def test_official_url_profile_round_trips_native_text_crops_languages_and_wave_topics(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('PROBLEM_BANK_TEST_TMPDIR')) as temporary:
            root = Path(temporary)
            pdf = root/'synthetic.pdf'
            document = pymupdf.open()
            document.new_page(width=200,height=240).insert_text((20,40), '1. Find x.')
            document.save(pdf)
            document.close()
            checksum = hashlib.sha256(pdf.read_bytes()).hexdigest()
            origin = {'kind':'url','url':'https://example.edu/synthetic.pdf',
                      'attribution':'Synthetic author','license_identifier':'CC-BY-4.0',
                      'license_url':'https://creativecommons.org/licenses/by/4.0/'}
            source = {'origin':origin,'revision':'sha256:'+checksum,'sha256':checksum,
                      'title':'Synthetic exercise','mime_type':'application/pdf','page_count':1,
                      'subjects':['electromagnetism'],'level':'undergraduate','source_language':'en',
                      'local_path':str(pdf),'expected_question_count':1,'extraction_complete':True}
            manifest = root/'manifest.json'
            manifest.write_text(json.dumps({'version':1,'sources':[source]}),encoding='utf8')
            profile = {'source':source_reference(source),'source_sha256':checksum,'page_count':1,
                       'source_author':'Synthetic author','source_language':'en','source_text_method':'native',
                       'subjects':['electromagnetism','waves'],'level':'undergraduate','expected_question_count':1,
                       'body_top':20,'body_bottom':100,'page_statement_columns':{'1':[[10,190]]},
                       'sections':[{'chapter':1,'first_page':1,'first_body_top':20,'last_page':1,'expected_count':1}]}
            headers = {'source_sha256':checksum,'errors':[],'headers':[{'chapter':1,'number':1,
                       'page':1,'column':0,'bbox':[20,30,35,42],'origin':'synthetic reviewed header'}]}
            for name,value in [('profile.json',profile),('headers.json',headers)]:
                (root/name).write_text(json.dumps(value),encoding='utf8')
            folder = root/'synthetic-url'
            args = SimpleNamespace(pdf=pdf,manifest=manifest,profile=root/'profile.json',headers=root/'headers.json',
                                   out=folder,dpi=96,max_render_side=0,reuse_matching_crops=False)
            with contextlib.redirect_stdout(io.StringIO()):
                extractor.extract(args)
            raw = json.loads((folder/'questions.raw.json').read_text())['questions'][0]
            self.assertEqual(raw['source'], source_reference(source))
            self.assertIn('Find x.', raw['versions'][0]['text'])
            self.assertEqual(len(raw['assets']),1)
            (folder/'translations').mkdir()
            (folder/'translations/001.json').write_text(json.dumps({'items':[{
                'original_number':'1','locator':raw['locator'],'text_en':'Find $x$.',
                'text_ko':'$x$를 구하여라.','source_image_checked':True}]}),encoding='utf8')
            preparer.prepare(root,profiles=['synthetic-url'])
            prepared = json.loads((root/'import-questions.json').read_text())['questions'][0]
            self.assertEqual(prepared['subjects'],['electromagnetism','oscillations_waves'])
            self.assertEqual(prepared['source'],source_reference(source))
            store = Path(__file__).with_name('store.mjs').resolve().as_uri()
            script = 'import {readFileSync} from "node:fs"; import {normalizeImport} from '+json.dumps(store)+';'
            script += 'const p=normalizeImport(JSON.parse(readFileSync(process.argv[1])),JSON.parse(readFileSync(process.argv[2])));'
            script += 'process.stdout.write(JSON.stringify({drive:p.sources[0].drive_id,origin:p.sources[0].origin,versions:p.questions[0].versions.length,assets:p.questions[0].assets.length}));'
            result = subprocess.run(['node','--input-type=module','-e',script,str(root/'import-manifest.json'),
                                     str(root/'import-questions.json')],check=True,capture_output=True,text=True,
                                     encoding='utf8',timeout=30)
            stored = json.loads(result.stdout)
            self.assertIsNone(stored['drive'])
            self.assertEqual(stored['origin'],origin)
            self.assertEqual((stored['versions'],stored['assets']),(2,1))


if __name__ == '__main__':
    unittest.main()
