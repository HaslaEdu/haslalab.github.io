"""Native-layout regressions for PDF prose suppression, without network data."""
from pathlib import Path
import unittest
import pikepdf
import pymupdf as fitz
from pdf_original_text_ops import cmap,suppress_prose,native_form_glyphs
from pdf_original_style_audit import audit

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'tmp/native-prose-regressions'

def fixture():
    WORK.mkdir(parents=True,exist_ok=True)
    path=WORK/'source.pdf';doc=fitz.open();page=doc.new_page(width=595,height=842)
    xref=page.insert_font(fontname='helv');metric=fitz.Font('helv');values=[]
    for code in range(256):
        try:char=bytes([code]).decode('cp1252')
        except UnicodeDecodeError:char='?'
        values.append(str(round(metric.glyph_advance(ord(char))*1000)))
    doc.xref_set_key(xref,'FirstChar','0');doc.xref_set_key(xref,'LastChar','255')
    doc.xref_set_key(xref,'Widths','['+' '.join(values)+']')
    stream=doc.get_new_xref();doc.update_object(stream,'<<>>')
    doc.update_stream(stream,b'q 1.000000003 0 0 1 0.123456789 0 cm BT /helv 12 Tf 0.4 Tc 1.5 Tw 2 Tr 0.28 w 1 0 0 1 72 700 Tm (Explain ) Tj 0 Tr (x) Tj ET /Math Do 0.5 w 72.123456789 600 m 210.987654321 600 l S Q')
    page.set_contents(stream)
    temporary=WORK/'base.pdf';doc.save(temporary);doc.close()
    with pikepdf.Pdf.open(temporary)as pdf:
        p=pdf.pages[0];form=pdf.make_stream(b'q BT /helv 12 Tf 0 Tc 0 Tw 0 Tr 1 0 0 1 220 650 Tm (y) Tj ET Q')
        form.Type=pikepdf.Name.XObject;form.Subtype=pikepdf.Name.Form
        form.BBox=pikepdf.Array([0,0,595,842]);form.Resources=pikepdf.Dictionary(Font=p.Resources.Font)
        p.Resources.XObject=pikepdf.Dictionary(Math=form);pdf.save(path)
    return path

class NativeTextOpsTests(unittest.TestCase):
    def test_utf16_surrogates_and_range_arrays(self):
        with pikepdf.Pdf.new()as pdf:
            source=b'1 beginbfrange\n<0001> <0002> <D835DC34>\nendbfrange\n1 beginbfrange\n<0003> <0004> [<003D> <03B1>]\nendbfrange'
            font=pikepdf.Dictionary(Encoding=pikepdf.Name('/Identity-H'),ToUnicode=pdf.make_stream(source))
            self.assertEqual(cmap(font),{1:'\U0001d434',2:'\U0001d435',3:'=',4:'α'})

    def test_stroked_prose_advance_and_native_form_pixels(self):
        source=fixture();doc=fitz.open(source);page=doc[0]
        stroke=next(t for t in page.get_texttrace()if t['type']==1)
        selected=[dict(c=chr(cp),font=stroke['font'],size=stroke['size'],origin=origin,bbox=bbox)
                  for cp,gid,origin,bbox in stroke['chars']if not chr(cp).isspace()]
        payload,count=suppress_prose(source,1,selected)
        self.assertEqual(count,len('Explain'))
        target=WORK/'suppressed.pdf';target.write_bytes(payload)
        spec=dict(source_page=1,erased_glyph_origins=[c['origin']for c in selected],
                  allowed_rects=[[c['bbox'][0]-2,c['bbox'][1]-2,c['bbox'][2]+2,c['bbox'][3]+2]for c in selected])
        result=audit(source,target,spec)
        self.assertEqual(result['native_glyphs_changed'],[])
        self.assertEqual(result['changed_pixels_in_native_glyph_neighborhood'],0)
        self.assertEqual(result['changed_pixels_outside_prose'],0)
        with fitz.open(target)as output:self.assertNotIn('Explain',output[0].get_text())
        doc.close()

    def test_math_form_is_read_only(self):
        source=fixture();protected=native_form_glyphs(source,1)
        self.assertEqual([c['c']for c in protected],['y'])
        with self.assertRaisesRegex(ValueError,'preserved native Form'):
            suppress_prose(source,1,protected)

    def test_unused_zero_width_digits_are_not_native_coverage(self):
        from izho_early_fixed_style import font_catalog,latin_profile
        source=fixture();target=WORK/'unused-digit.pdf'
        with pikepdf.Pdf.open(source)as pdf:
            font=pdf.pages[0].Resources.Font['/helv'];font.Widths[ord('1')]=0;pdf.save(target)
        catalog=font_catalog(target,1,{'Helvetica'})
        with self.assertRaisesRegex(ValueError,'No source-native encoding'):
            latin_profile(catalog,'Helvetica','11')
        self.assertEqual(latin_profile(catalog,'Helvetica','XX')['alias'],'helv')

if __name__=='__main__':unittest.main()
