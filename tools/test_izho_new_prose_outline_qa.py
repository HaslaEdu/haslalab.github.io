"""An actual positive-width, nonzero-GID empty-glyph regression fixture."""
from pathlib import Path
from collections import Counter
import json,tempfile,unittest
import pikepdf
import pymupdf as fitz
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
import izho_new_prose_outline_qa as qa


def make_font(path,empty_a):
    fb=FontBuilder(1000,isTTF=True);fb.setupGlyphOrder(['.notdef','A','B','space'])
    outlines={}
    for name in ['.notdef','A','B','space']:
        pen=TTGlyphPen(None)
        if name!='space'and not(name=='A'and empty_a):
            pen.moveTo((50,0));pen.lineTo((550,0));pen.lineTo((550,700));pen.lineTo((50,700));pen.closePath()
        outlines[name]=pen.glyph()
    fb.setupCharacterMap({32:'space',65:'A',66:'B'});fb.setupGlyf(outlines)
    fb.setupHorizontalMetrics({name:(600,0)for name in outlines});fb.setupHorizontalHeader(ascent=800,descent=-200)
    fb.setupNameTable(dict(familyName='IZhOOutlineInkFixture',styleName='Regular',uniqueFontIdentifier='IZhOOutlineInkFixture',fullName='IZhOOutlineInkFixture',psName='IZhOOutlineInkFixture',version='Version 1.0'))
    fb.setupOS2(sTypoAscender=800,sTypoDescender=-200,usWinAscent=800,usWinDescent=200);fb.setupPost();fb.setupMaxp();fb.save(path)


class ActualOutlineTests(unittest.TestCase):
    def test_actual_resource_not_name_and_original_empty_excluded(self):
        with tempfile.TemporaryDirectory(prefix='outline-regression-',dir=qa.ROOT/'tmp')as temp:
            root=Path(temp).resolve();self.assertTrue(root.is_relative_to((qa.ROOT/'tmp').resolve()))
            empty=root/'empty.ttf';valid=root/'valid.ttf';make_font(empty,True);make_font(valid,False)
            source=root/'source.pdf'
            with fitz.open()as doc:
                p=doc.new_page(width=100,height=100);p.insert_font(fontname='EmptyFace',fontfile=str(empty));p.insert_font(fontname='ValidFace',fontfile=str(valid))
                # The original already has an empty nonspace A. It must not
                # be misreported as a newly introduced translation defect.
                p.insert_text((10,20),'A',fontname='EmptyFace',fontsize=10)
                p.insert_text((10,35),'B',fontname='ValidFace',fontsize=10);doc.save(source)
            final=root/'outline-fixture.pdf'
            with fitz.open(source)as doc:
                doc[0].insert_text((10,60),'A',fontname='EmptyFace',fontsize=10)
                doc[0].insert_text((35,60),'A',fontname='ValidFace',fontsize=10)
                doc[0].insert_text((60,60),' ',fontname='EmptyFace',fontsize=10);doc.save(final)
            plan=root/'page1.json';plan.write_text(json.dumps(dict(source=str(source.relative_to(qa.ROOT)),page=0)),encoding='utf8')
            with pikepdf.open(final)as pdf:
                font=pdf.pages[0].Resources.Font['/EmptyFace'];values,default=__import__('pdf_original_text_ops').widths(font)
                code=next(code for code,value in qa.cmap(font).items()if value=='A')
                self.assertGreater(values.get(code,default),0)
            report=qa.edition(0,'fixture',final,[plan],{})
            self.assertEqual(report['new_nonspace_glyphs_checked'],2)
            self.assertEqual(report['empty_outline_count'],1)
            missing=report['empty_outlines'][0]
            self.assertEqual(missing['font_alias'],'/EmptyFace');self.assertEqual(missing['gid'],1)
            self.assertEqual(missing['origin'],[10.0,60.0]);self.assertEqual(missing['c'],'A')


if __name__=='__main__':unittest.main()
