"""A real Poppler-rendered formula must detect overpainted bars and glyphs."""
from pathlib import Path
import subprocess,tempfile,unittest
import numpy as np
import pymupdf as fitz
from PIL import Image
from cpho_2023_original_poppler import native_ink_changes

class NativeInk(unittest.TestCase):
    def test_fraction_and_glyph_overpainting_cannot_pass(self):
        with tempfile.TemporaryDirectory(prefix='cpho-poppler-',dir='D:/CodexBuilds/Hasla-original-style-20261031')as temp:
            folder=Path(temp);original=folder/'original.pdf'
            with fitz.open()as doc:
                page=doc.new_page(width=180,height=140)
                page.insert_text((70,60),'x',fontsize=16,fontname='tiit')
                page.draw_line((62,65),(88,65),width=.75)
                page.insert_text((70,83),'2',fontsize=16,fontname='tiro')
                doc.save(original)
            def render(path):
                stem=path.with_suffix('')
                subprocess.run(['pdftoppm','-singlefile','-r','110','-png',str(path),str(stem)],capture_output=True,check=True)
                with Image.open(stem.with_suffix('.png'))as image:return np.asarray(image.convert('RGB'))
            source=render(original);exceptions=np.zeros(source.shape[:2],np.uint8)
            self.assertFalse(native_ink_changes(source,source,exceptions)[0].any())
            for label,box in [('fraction-bar',(65,64,86,66)),('native-glyph',(68,48,81,61))]:
                bad=folder/(label+'.pdf')
                with fitz.open(original)as doc:
                    doc[0].draw_rect(fitz.Rect(box),color=None,fill=(1,1,1));doc.save(bad)
                self.assertGreater(int(native_ink_changes(source,render(bad),exceptions)[0].sum()),0,label)

if __name__=='__main__':unittest.main()
