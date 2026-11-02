"""Synthetic original-figure safety checks. No real books or network access."""
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
import pymupdf
from PIL import Image

SPEC=importlib.util.spec_from_file_location('extract_figures',Path(__file__).with_name('extract-question-figures.py'))
MODULE=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(MODULE)


class OriginalFigureTests(unittest.TestCase):
    def test_native_svg_physically_removes_other_question_and_solution_text(self):
        with pymupdf.open() as pdf:
            page=pdf.new_page(width=400,height=400)
            page.insert_text((20,30),'OTHER QUESTION / SECRET SOLUTION')
            page.insert_text((135,155),'original label')
            page.draw_rect(pymupdf.Rect(120,120,280,280))
            svg,proof=MODULE.native_svg(page,pymupdf.Rect(100,100,300,300))
            self.assertTrue(proof['available']);self.assertIn('original label',proof['retained_text_for_private_review'])
            self.assertNotIn('SECRET',proof['retained_text_for_private_review']);self.assertNotIn(b'SECRET',svg)
            self.assertIn('SECRET',page.get_text());self.assertNotIn(b'<script',svg)

    def test_full_page_scan_is_never_hidden_as_an_off_crop_svg_image(self):
        with pymupdf.open() as pdf:
            page=pdf.new_page(width=400,height=400)
            stream=io.BytesIO();Image.new('RGB',(400,400),'white').save(stream,format='PNG')
            page.insert_image(page.rect,stream=stream.getvalue())
            svg,proof=MODULE.native_svg(page,pymupdf.Rect(100,100,300,300))
            self.assertIsNone(svg);self.assertEqual(proof['reason'],'intersecting_image_extends_outside_figure')

    def test_crossing_zero_height_vector_is_refused_instead_of_retained_outside_crop(self):
        with pymupdf.open() as pdf:
            page=pdf.new_page(width=400,height=400);page.draw_line((0,200),(400,200))
            svg,proof=MODULE.native_svg(page,pymupdf.Rect(100,100,300,300))
            self.assertIsNone(svg);self.assertEqual(proof['reason'],'intersecting_vector_extends_outside_figure')

    def test_page_box_and_invalid_normalized_coordinates_are_checked(self):
        with pymupdf.open() as pdf:
            page=pdf.new_page(width=400,height=200)
            self.assertEqual(list(MODULE.rectangle(page,[.25,.25,.75,.75])),[100,50,300,150])
            for value in [[0,0,0,1],[0,0,1,2],[False,0,1,1],[0,0,float('nan'),1],[]]:
                with self.assertRaises(ValueError):MODULE.rectangle(page,value)

    def test_extractor_requires_canonical_identity_source_bytes_and_explicit_source_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'solution-bank').mkdir();pdfpath=root/'source.pdf'
            with pymupdf.open() as doc:
                page=doc.new_page(width=400,height=400);page.insert_text((120,140),'input label');doc.save(pdfpath)
            source={'drive_id':'synthetic-source','revision':'v1','id':'src_'+'a'*64,'sha256':MODULE.sha(pdfpath.read_bytes()),'local_path':str(pdfpath)}
            ref={'drive_id':source['drive_id'],'revision':source['revision']}
            (root/'solution-bank/source-index.json').write_text(json.dumps({'normalized_sources':[source]}))
            (root/'solution-bank/question-index.json').write_text(json.dumps({'questions':[{'source':ref,'locator':'problem-1','original_number':'1'}]}))
            item={'source':ref,'locator':'problem-1','source_pdf_sha256':source['sha256'],'page':1,'bbox':[.25,.25,.75,.75],'source_bbox_visually_verified':True,'statement_figure_not_solution':True}
            result=MODULE.extract(root,{'version':1,'figures':[item]},root/'output',100)
            figure=result['figures'][0];self.assertEqual(figure['role'],'figure');self.assertFalse(figure['final_extracted_image_visually_verified'])
            self.assertEqual(MODULE.sha(Path(figure['local_path']).read_bytes()),figure['sha256'])
            self.assertIn('input label',pymupdf.open(pdfpath)[0].get_text())
            for change in [{'statement_figure_not_solution':False},{'source_bbox_visually_verified':False},{'locator':'problem-2'},{'source_pdf_sha256':'b'*64},{'question_id':'q_'+'0'*64}]:
                with self.assertRaises(ValueError):MODULE.extract(root,{'version':1,'figures':[{**item,**change}]},root/'reject',100)
            pdfpath.write_bytes(pdfpath.read_bytes()+b'changed')
            with self.assertRaisesRegex(ValueError,'source PDF bytes changed'):MODULE.extract(root,{'version':1,'figures':[item]},root/'reject',100)


if __name__=='__main__':unittest.main()
