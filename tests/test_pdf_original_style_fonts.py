"""Real-font regressions for Hangul subsetting and unsupported whitespace."""
from pathlib import Path
import hashlib,sys,tempfile,unittest
from fontTools.ttLib import TTFont
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from pdf_original_style_fonts import FONTS,subset_font

class OriginalStyleFontTests(unittest.TestCase):
    def test_unsupported_thin_space_fails_instead_of_rendering_notdef(self):
        source=FONTS['serif']
        with TTFont(source)as font:self.assertNotIn(0x2006,font.getBestCmap())
        with tempfile.TemporaryDirectory()as folder:
            with self.assertRaisesRegex(ValueError,'unsupported characters'):
                subset_font(source,'한\u2006글',Path(folder))

    def test_hangul_gids_are_retained_and_subsets_are_reproducible(self):
        source=FONTS['serif'];text='한 글과 수식'
        with tempfile.TemporaryDirectory()as folder:
            a=subset_font(source,text,Path(folder)/'a')
            b=subset_font(source,text,Path(folder)/'b')
            self.assertEqual(hashlib.sha256(a.read_bytes()).digest(),hashlib.sha256(b.read_bytes()).digest())
            with TTFont(source)as old,TTFont(a)as new:
                for char in text:
                    old_name=old.getBestCmap()[ord(char)];new_name=new.getBestCmap()[ord(char)]
                    self.assertEqual(old.getGlyphID(old_name),new.getGlyphID(new_name),char)

if __name__=='__main__':unittest.main()
