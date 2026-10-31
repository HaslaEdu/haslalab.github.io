import unittest
import pymupdf as fitz
from pdf_text_motion_ink import _origin_selector,ink_envelope
class ExactOriginSelection(unittest.TestCase):
    def test_half_even_boundary_same_origin(self):
        selected=_origin_selector([(80.42500305175781,406.73016357421875)])
        self.assertTrue(selected(80.425,406.73017))
        self.assertFalse(selected(80.435,406.73017))
        self.assertFalse(selected(80.425,406.73217))
    def test_spatial_bucket_negative_and_boundary(self):
        selected=_origin_selector([(-.00001,1.00001),(10.99999,-.00001)])
        self.assertTrue(selected(.00001,.99999))
        self.assertTrue(selected(11.00001,.00001))
        self.assertFalse(selected(11.002,-.00001))
    def test_real_pdf_svg_rounding_selects_only_original_glyph(self):
        with fitz.open()as doc:
            p=doc.new_page(width=300,height=200)
            p.insert_text((80.42500305175781,100.73016357421875),'A',fontsize=12)
            p.insert_text((180.42500305175781,100.73016357421875),'B',fontsize=12)
            g=p.get_texttrace()[0]['chars'][0]
            mask,count=ink_envelope(p,[g[2]],4)
            self.assertEqual(count,1)
            self.assertTrue(mask[350:420,310:390].any())
            self.assertFalse(mask[:,600:].any())
if __name__=='__main__':unittest.main()
