"""Synthetic tests for column continuations and source OCR identity."""
import copy
import importlib.util
from pathlib import Path
import unittest

SPEC=importlib.util.spec_from_file_location('columns',Path(__file__).with_name('extract-column-questions.py'))
MODULE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ColumnTests(unittest.TestCase):
    def test_continuation_uses_section_top_on_first_page_and_body_top_afterwards(self):
        profile={'body_top':80,'body_bottom':750,'page_statement_columns':
                 {'1':[[20,270],[300,550]],'2':[[20,270],[300,550]]}}
        section={'first_page':1,'first_body_top':400}
        start={'page':1,'column':0,'bbox':[25,700,40,710]}
        stop={'page':2,'column':0,'y':110}
        result=MODULE.regions(start,stop,section,profile)
        self.assertEqual([(r['page'],r['column']) for r in result],[(1,0),(1,1),(2,0)])
        self.assertEqual([r['bbox_points'][1:] for r in result],
                         [[696,270,750],[400,550,750],[80,270,110]])

    def test_header_end_in_right_column_never_reads_following_column_content(self):
        profile={'body_top':80,'body_bottom':750,'page_statement_columns':{'1':[[20,270],[300,550]]}}
        result=MODULE.regions({'page':1,'column':1,'bbox':[305,500,320,510]},
                              {'page':1,'column':1,'y':600},
                              {'first_page':1,'first_body_top':400},profile)
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['bbox_points'],[300,496,550,600])

    def test_unrelated_lecture_footer_is_outside_both_question_columns(self):
        profile={'body_top':80,'body_bottom':750,'page_body_bottom':{'1':710},
                 'page_statement_columns':{'1':[[20,270],[300,550]],'2':[[20,270],[300,550]]}}
        result=MODULE.regions({'page':1,'column':0,'bbox':[25,650,40,660]},
                              {'page':2,'column':0,'y':110},
                              {'first_page':1,'first_body_top':646},profile)
        self.assertEqual([r['bbox_points'][3] for r in result[:2]],[710,710])

    def test_original_ocr_language_and_geometry_cannot_be_substituted(self):
        record={'source_sha256':'0'*64,'page':1,'engine':'tesseract-local','language':'kor',
                'page_size_pt':[100,200],'render_size_px':[1000,2000],
                'tsv':'5\t1\t1\t1\t1\t1\t100\t200\t200\t100\t99\t합성문항\n'}
        words=MODULE.words(record,'0'*64,1,[100,200],'kor')
        self.assertEqual(MODULE.text_in([0,0,50,50],words),'합성문항')
        self.assertEqual(MODULE.text_in([60,0,100,50],words),'')
        with self.assertRaisesRegex(ValueError,'identity/language'):
            MODULE.words(record,'0'*64,1,[100,200],'eng')
        bad=copy.deepcopy(record)
        bad['page_size_pt']=[]
        with self.assertRaisesRegex(ValueError,'page geometry'):
            MODULE.words(bad,'0'*64,1,[100,200],'kor')


if __name__=='__main__':
    unittest.main()
