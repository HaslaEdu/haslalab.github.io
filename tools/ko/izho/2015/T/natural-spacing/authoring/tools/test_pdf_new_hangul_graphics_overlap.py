"""Independent rendered-ink collisions, including native bitmap math tails."""
from pathlib import Path
import unittest
import pymupdf as fitz
from pdf_native_inline_reposition import _traces
from pdf_new_hangul_graphics_overlap import audit

OUT=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-natural-spacing/overlap-fixtures')

class NewProseGraphicsOverlap(unittest.TestCase):
    def fixture(self,name,kind):
        OUT.mkdir(parents=True,exist_ok=True)
        doc=fitz.open();page=doc.new_page(width=200,height=160)
        if kind=='bitmap':
            image=fitz.Pixmap(fitz.csGRAY,fitz.IRect(0,0,2,2),False)
            image.clear_with(0)
            page.insert_image(fitz.Rect(95,80,120,105),pixmap=image)
        else:
            area=fitz.Rect(95,80,120,105)if kind!='adjacent'else fitz.Rect(135,80,160,105)
            value=.9 if kind=='pale'else 0
            page.draw_rect(area,color=None,fill=(value,value,value))
        # The helper accepts exact explicit glyph journals, so this fixture
        # needs no proprietary full Batang font while exercising its actual
        # source-outline/native-graphics logic unchanged.
        page.insert_text((100,100),'W',fontname='helv',fontsize=18)
        target=OUT/name;doc.save(target);doc.close()
        with fitz.open(target)as saved: glyphs=_traces(saved[0])
        return audit(target,new_glyphs=glyphs)

    def test_native_vector_behind_new_prose_is_rejected(self):
        qa=self.fixture('vector-overlap.pdf','vector')
        self.assertFalse(qa['passed'])
        self.assertGreater(qa['new_hangul_dark_pixels_over_native_foreground'],0)

    def test_native_bitmap_tail_behind_new_prose_is_rejected(self):
        qa=self.fixture('bitmap-overlap.pdf','bitmap')
        self.assertFalse(qa['passed'])
        self.assertGreater(qa['new_hangul_dark_pixels_over_native_foreground'],0)

    def test_adjacent_native_math_has_no_collision(self):
        self.assertTrue(self.fixture('adjacent.pdf','adjacent')['passed'])

    def test_pale_table_fill_is_not_native_foreground(self):
        self.assertTrue(self.fixture('pale-table.pdf','pale')['passed'])

if __name__=='__main__':unittest.main()
