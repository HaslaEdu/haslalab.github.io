"""Scientific exponents and indices must survive the embedded Hangul font."""
from pathlib import Path
import sys,unittest
import pymupdf as fitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from pdf_layout_translate import script_markup,FONT

class ScriptGlyphs(unittest.TestCase):
    def test_rendered_scripts_have_no_missing_glyphs(self):
        doc=fitz.open();page=doc.new_page(width=420,height=90)
        archive=fitz.Archive(str(FONT.parent))
        css='@font-face{font-family:Korean;src:url(NotoSansKR-Regular.ttf);}*{font-family:Korean;}'
        text='정오: 1.232 × 10⁹ eV/c², 10⁶, x₁₀, Δxₘ, ᵃ'
        spare,_=page.insert_htmlbox(page.rect,script_markup(text),css=css,archive=archive)
        self.assertGreaterEqual(spare,0)
        self.assertNotIn('\x00',page.get_text())
        self.assertNotIn('�',page.get_text())

if __name__=='__main__':unittest.main()
