"""Real PDF regression: regular Hangul Tr2 survives natural Batang replacement."""
from io import BytesIO
from pathlib import Path
import tempfile,unittest
import pymupdf as fitz
from fontTools import subset
from fontTools.ttLib import TTFont
from pdf_korean_natural_composer import compose_page
from izho_natural_spacing import ROOT,BUILD,records

class ComposerPDFRegression(unittest.TestCase):
    def test_fill_stroke_color_width_and_native_math_face(self):
        BUILD.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=BUILD,ignore_cleanup_errors=True)as temp:
            source=Path(temp)/'source.pdf';font=TTFont(ROOT/'tools/ko/fonts/NotoSerifCJKkr-Regular.otf',recalcTimestamp=False)
            options=subset.Options();options.retain_gids=True;worker=subset.Subsetter(options=options);worker.populate(text='질량인 강체구');worker.subset(font)
            buf=BytesIO();font.save(buf);doc=fitz.open();page=doc.new_page(width=400,height=160)
            page.insert_font(fontname='OldKorean',fontbuffer=buf.getvalue())
            times=Path('C:/Windows/Fonts/times.ttf');page.insert_font(fontname='OriginalTimes',fontfile=str(times))
            page.insert_text((20,60),'질량',fontname='OldKorean',fontsize=12,render_mode=2,border_width=.3/12,
                color=(1,0,0),fill=(0,0,1),miter_limit=10)
            page.insert_text((160,60),'m',fontname='OriginalTimes',fontsize=12)
            page.insert_text((190,60),'인 강체구',fontname='OldKorean',fontsize=12)
            doc.save(source,garbage=0,deflate=False);doc.close()
            result,qa=compose_page(source,1,allowed_line_rects=[[19,40,300,80]],
                prose_placements=[dict(point=[20,60],width=23.184,text='질량',border_width=.3),
                                  dict(point=[190,60],width=70,text='인 강체구')])
            final=fitz.open(stream=result,filetype='pdf');rows=records(final[0]);new=[r for r in rows if r['font']=='Batang']
            stroked=[r for r in new if r['paint']==2]
            self.assertEqual(''.join(r['c']for r in stroked),'질량')
            self.assertTrue(all(abs(r['linewidth']-.3)<1e-5 for r in stroked))
            self.assertTrue(all(tuple(r['color'])==(0,0,1)and tuple(r['stroke_color'])==(1,0,0)for r in stroked))
            self.assertTrue(all(r['size']==12 and r['origin'][1]==60 for r in new))
            native=[r for r in rows if r['c']=='m'];self.assertEqual(len(native),1)
            self.assertIn('TimesNewRoman',native[0]['font']);self.assertEqual(native[0]['size'],12)
            self.assertEqual(qa['new_non_hangul_font_replacements'],0)
            self.assertEqual(qa['retained_native_style_or_geometry_mismatches_after_insertion'],0)
            final.close()

if __name__=='__main__':unittest.main()
