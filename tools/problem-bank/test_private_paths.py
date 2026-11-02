import json
from pathlib import Path
import tempfile
import unittest
from private_paths import source_path


class RuntimeInputMappingTest(unittest.TestCase):
    def test_reads_moved_inputs_without_changing_historical_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);moved=root/'moved';moved.mkdir();pdf=moved/'book.pdf';pdf.write_bytes(b'original PDF bytes')
            historical=str(root/'old-one-drive'/'book.pdf');manifest={'local_path':historical};mapping=root/'mapping.json'
            mapping.write_text(json.dumps({'version':1,'prefixes':[{'from':str(root/'old-one-drive'),'to':str(moved)}]}))
            self.assertEqual(source_path(manifest['local_path'],mapping).read_bytes(),b'original PDF bytes')
            self.assertEqual(manifest['local_path'],historical)
            self.assertFalse((root/'old-one-drive').exists())

    def test_prefix_boundaries_and_unmapped_current_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);mapping=root/'mapping.json';mapping.write_text(json.dumps({'version':1,'prefixes':[{'from':str(root/'old'),'to':str(root/'new')}]}))
            untouched=root/'older'/'x.pdf';self.assertEqual(source_path(untouched,mapping),untouched)
            self.assertEqual(source_path(root/'new'/'x.pdf',mapping),root/'new'/'x.pdf')

    def test_mapping_cannot_escape_its_new_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);mapping=root/'mapping.json';mapping.write_text(json.dumps({'version':1,'prefixes':[{'from':str(root/'old'),'to':str(root/'new')}]}))
            with self.assertRaises(ValueError):source_path(str(root/'old')+'/../outside.pdf',mapping)


if __name__=='__main__':unittest.main()
