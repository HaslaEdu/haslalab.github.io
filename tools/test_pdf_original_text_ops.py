"""Native-layout regressions for PDF prose suppression, without network data."""
from pathlib import Path
import unittest
import zlib
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
import pikepdf
import pymupdf as fitz
from pdf_original_text_ops import cmap,suppress_prose,native_form_glyphs,source_code_bytes,widths
from pdf_original_style_audit import audit

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'tmp/native-prose-regressions'

def tiny_font():
    WORK.mkdir(parents=True,exist_ok=True)
    builder=FontBuilder(1000,isTTF=True);order=['.notdef','A','x'];builder.setupGlyphOrder(order)
    builder.setupCharacterMap({65:'A',120:'x'});glyphs={}
    for name in order:
        pen=TTGlyphPen(None);pen.moveTo((40,0));pen.lineTo((300,700));pen.lineTo((560,0));pen.closePath();glyphs[name]=pen.glyph()
    builder.setupGlyf(glyphs);builder.setupHorizontalMetrics({name:(600,0)for name in order})
    builder.setupHorizontalHeader(ascent=800,descent=-200)
    builder.setupNameTable(dict(familyName='NativeCIDFixture',styleName='Regular',uniqueFontIdentifier='NativeCIDFixture',fullName='NativeCIDFixture',psName='NativeCIDFixture'))
    builder.setupOS2(sTypoAscender=800,sTypoDescender=-200,usWinAscent=800,usWinDescent=200);builder.setupPost();builder.setupMaxp()
    fontpath=WORK/'native-cid-fixture.ttf';builder.save(fontpath)
    return fontpath

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

    def test_native_quote_shows_are_read_only_and_spacing_is_inherited(self):
        base=fixture();source=WORK/'quote-shows.pdf'
        with pikepdf.Pdf.open(base)as pdf:
            page=pdf.pages[0]
            extra=b'BT /helv 12 Tf 0 Tc 0 Tw 0 Tr 16 TL 1 0 0 1 300 450 Tm (x) Tj ( ) \' 1.5 0.4 (y) " (tail) Tj (z) Tj ET'
            page.Contents=pikepdf.Array([page.Contents,pdf.make_stream(extra)])
            pdf.save(source,compress_streams=False)
        with fitz.open(source)as doc:
            selected=[];quoted=None
            for trace in doc[0].get_texttrace():
                for cp,gid,origin,bbox in trace['chars']:
                    ch=dict(c=chr(cp),font=trace['font'],size=trace['size'],origin=origin,bbox=bbox)
                    if trace['type']==1 and not ch['c'].isspace()or origin[1]==424 and ch['c']in 'tail':selected.append(ch)
                    if ch['c']=='y'and origin[0]>290:quoted=ch
            self.assertIsNotNone(quoted)
            # The quote glyph itself is native and may never be erased.
            with self.assertRaisesRegex(ValueError,'read-only quote text-show'):
                suppress_prose(source,1,[quoted])
        payload,count=suppress_prose(source,1,selected);self.assertEqual(count,len('Explain')+4)
        target=WORK/'quote-shows-suppressed.pdf';target.write_bytes(payload)
        result=audit(source,target,dict(source_page=1,erased_glyph_origins=[c['origin']for c in selected],allowed_rects=[[c['bbox'][0]-1,c['bbox'][1]-1,c['bbox'][2]+1,c['bbox'][3]+1]for c in selected]))
        self.assertEqual(result['native_glyphs_changed'],[]);self.assertEqual(result['changed_pixels_in_native_glyph_neighborhood'],0);self.assertEqual(result['changed_pixels_outside_prose'],0)
        with pikepdf.Pdf.open(target)as pdf:
            native_stream=pdf.pages[0].Contents.read_bytes()
            self.assertIn(b"( ) '",native_stream);self.assertIn(b'1.5 0.4 (y) "',native_stream)

    def test_multi_unicode_math_cid_remains_native(self):
        source=fixture();cluster_source=WORK/'unicode-cluster.pdf'
        pairs=[]
        for code in range(32,127):
            value='yy'if code==ord('y')else chr(code)
            pairs.append(f'<{code:02X}> <{value.encode("utf-16-be").hex()}>')
        cm=('begincmap\n1 begincodespacerange\n<00> <FF>\nendcodespacerange\n'
            f'{len(pairs)} beginbfchar\n'+'\n'.join(pairs)+'\nendbfchar\nendcmap').encode()
        with pikepdf.Pdf.open(source)as pdf:
            pdf.pages[0].Resources.Font['/helv'].ToUnicode=pdf.make_stream(cm);pdf.save(cluster_source)
        protected=native_form_glyphs(cluster_source,1)
        self.assertEqual([c['c']for c in protected],['y','y'])
        with self.assertRaisesRegex(ValueError,'multi-Unicode CID'):
            suppress_prose(cluster_source,1,protected)
        doc=fitz.open(cluster_source);stroke=next(t for t in doc[0].get_texttrace()if t['type']==1)
        selected=[dict(c=chr(cp),font=stroke['font'],size=stroke['size'],origin=origin,bbox=bbox)
                  for cp,gid,origin,bbox in stroke['chars']if not chr(cp).isspace()]
        payload,count=suppress_prose(cluster_source,1,selected);self.assertEqual(count,len('Explain'))
        target=WORK/'unicode-cluster-suppressed.pdf';target.write_bytes(payload)
        spec=dict(source_page=1,erased_glyph_origins=[c['origin']for c in selected],
                  protected_glyph_origins=[c['origin']for c in protected],
                  allowed_rects=[[c['bbox'][0]-2,c['bbox'][1]-2,c['bbox'][2]+2,c['bbox'][3]+2]for c in selected])
        result=audit(cluster_source,target,spec)
        self.assertEqual(result['native_glyphs_changed'],[])
        self.assertEqual(result['changed_pixels_in_native_glyph_neighborhood'],0)
        self.assertEqual(result['changed_pixels_outside_prose'],0)
        with pikepdf.Pdf.open(cluster_source)as a,pikepdf.Pdf.open(target)as b:
            self.assertEqual(a.pages[0].Resources.XObject.Math.read_bytes(),b.pages[0].Resources.XObject.Math.read_bytes())
            self.assertEqual(a.pages[0].Resources.Font['/helv'].ToUnicode.read_bytes(),b.pages[0].Resources.Font['/helv'].ToUnicode.read_bytes())
        doc.close()

    def test_unused_zero_width_digits_are_not_native_coverage(self):
        from izho_early_fixed_style import font_catalog,latin_profile
        source=fixture();target=WORK/'unused-digit.pdf'
        with pikepdf.Pdf.open(source)as pdf:
            font=pdf.pages[0].Resources.Font['/helv'];font.Widths[ord('1')]=0;pdf.save(target)
        catalog=font_catalog(target,1,{'Helvetica'})
        with self.assertRaisesRegex(ValueError,'No source-native encoding'):
            latin_profile(catalog,'Helvetica','11')
        self.assertEqual(latin_profile(catalog,'Helvetica','XX')['alias'],'helv')

    def test_unmapped_identity_math_cid_is_read_only(self):
        fontpath=tiny_font()
        doc=fitz.open();page=doc.new_page();page.insert_font(fontname='Test',fontfile=str(fontpath));page.insert_text((72,72),'Ax',fontname='Test',fontsize=12)
        initial=WORK/'native-cid-initial.pdf';doc.save(initial);doc.close()
        source=WORK/'unmapped-identity.pdf'
        with pikepdf.Pdf.open(initial)as pdf:
            font=pdf.pages[0].Resources.Font.Test
            font.DescendantFonts[0].CIDToGIDMap=pikepdf.Name.Identity
            # The real glyph for A remains embedded, but the source's CMap
            # deliberately has no Unicode destination for CID1.
            font.ToUnicode=pdf.make_stream(b'begincmap 1 begincodespacerange <0000> <FFFF> endcodespacerange 1 beginbfchar <0002> <0078> endbfchar endcmap')
            pdf.save(source)
        original=fitz.open(source);traces=original[0].get_texttrace();trace=traces[0]
        unknown,nextchar=trace['chars'];self.assertEqual(unknown[:2],(65533,1))
        selected=[dict(c='x',font=trace['font'],size=trace['size'],origin=nextchar[2],bbox=nextchar[3])]
        payload,count=suppress_prose(source,1,selected);self.assertEqual(count,1)
        target=WORK/'unmapped-identity-suppressed.pdf';target.write_bytes(payload)
        result=audit(source,target,dict(source_page=1,erased_glyph_origins=[nextchar[2]],allowed_rects=[[nextchar[3][0]-1,nextchar[3][1]-1,nextchar[3][2]+1,nextchar[3][3]+1]]))
        self.assertEqual(result['native_glyphs_changed'],[]);self.assertEqual(result['changed_pixels_in_native_glyph_neighborhood'],0);self.assertEqual(result['changed_pixels_outside_prose'],0)
        with pikepdf.Pdf.open(source)as a,pikepdf.Pdf.open(target)as b:
            af=a.pages[0].Resources.Font.Test;bf=b.pages[0].Resources.Font.Test
            self.assertEqual(af.ToUnicode.read_bytes(),bf.ToUnicode.read_bytes())
            self.assertEqual(af.DescendantFonts[0].FontDescriptor.FontFile2.read_bytes(),bf.DescendantFonts[0].FontDescriptor.FontFile2.read_bytes())
        # rawdict may expose chr(CID), whereas texttrace exposes FFFD. Both
        # spellings must reject erasure of the unidentified native glyph.
        for char in ['\ufffd','\x01']:
            with self.assertRaisesRegex(ValueError,'unmapped native Identity CID'):
                suppress_prose(source,1,[dict(c=char,font=trace['font'],size=trace['size'],origin=unknown[2],bbox=unknown[3])])
        original.close()

    def test_symbolic_simple_truetype_without_encoding_preserves_native(self):
        fontpath=tiny_font();initial=WORK/'implicit-encoding-initial.pdf'
        doc=fitz.open();page=doc.new_page();page.insert_font(fontname='Test',fontfile=str(fontpath));doc.save(initial);doc.close()
        source=WORK/'implicit-encoding.pdf'
        with pikepdf.Pdf.open(initial)as pdf:
            page=pdf.pages[0];descriptor=page.Resources.Font.Test.DescendantFonts[0].FontDescriptor
            descriptor.Flags=4
            values=[600 if code in [65,120]else 0 for code in range(65,121)]
            font=pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.Font,Subtype=pikepdf.Name.TrueType,
                BaseFont=pikepdf.Name.NativeCIDFixture,FirstChar=65,LastChar=120,Widths=pikepdf.Array(values),
                FontDescriptor=descriptor,ToUnicode=pdf.make_stream(b'begincmap 1 begincodespacerange <00> <ff> endcodespacerange 2 beginbfchar <41> <0041> <78> <0078> endbfchar endcmap')))
            page.Resources.Font=pikepdf.Dictionary(Simple=font)
            page.Contents=pdf.make_stream(b'BT /Simple 12 Tf 1 0 0 1 72 770 Tm (Ax) Tj 1 0 0 1 200 700 Tm (x) Tj ET')
            self.assertEqual(source_code_bytes(font),1);self.assertEqual(widths(font)[0][65],600)
            # Each missing piece must reject this profile rather than guessing
            # a WinAnsi or Mac encoding for the source glyph codes.
            for key in ['/ToUnicode','/Widths']:
                saved=font[key];del font[key]
                with self.assertRaisesRegex(ValueError,'Implicit simple TrueType'):source_code_bytes(font)
                font[key]=saved
            font.FontDescriptor.Flags=32
            with self.assertRaisesRegex(ValueError,'Implicit simple TrueType'):source_code_bytes(font)
            font.FontDescriptor.Flags=4
            saved=font.FontDescriptor.FontFile2;del font.FontDescriptor.FontFile2
            with self.assertRaisesRegex(ValueError,'Implicit simple TrueType'):source_code_bytes(font)
            font.FontDescriptor.FontFile2=saved
            saved=font.ToUnicode;font.ToUnicode=pdf.make_stream(b'begincmap 1 begincodespacerange <0000> <ffff> endcodespacerange 1 beginbfchar <0041> <0041> endbfchar endcmap')
            with self.assertRaisesRegex(ValueError,'single-byte'):source_code_bytes(font)
            font.ToUnicode=saved;font.LastChar=119
            with self.assertRaisesRegex(ValueError,'Widths range'):source_code_bytes(font)
            font.LastChar=120;pdf.save(source,compress_streams=False)
        with fitz.open(source)as original:
            trace=original[0].get_texttrace()[0];char=trace['chars'][0]
            self.assertEqual(char[0],ord('A'))
            selected=[dict(c='A',font=trace['font'],size=trace['size'],origin=char[2],bbox=char[3])]
        payload,count=suppress_prose(source,1,selected);self.assertEqual(count,1)
        target=WORK/'implicit-encoding-suppressed.pdf';target.write_bytes(payload)
        result=audit(source,target,dict(source_page=1,erased_glyph_origins=[char[2]],allowed_rects=[[char[3][0]-1,char[3][1]-1,char[3][2]+1,char[3][3]+1]]))
        self.assertEqual(result['native_glyphs_changed'],[]);self.assertEqual(result['changed_pixels_in_native_glyph_neighborhood'],0);self.assertEqual(result['changed_pixels_outside_prose'],0)
        with pikepdf.Pdf.open(source)as a,pikepdf.Pdf.open(target)as b:
            af=a.pages[0].Resources.Font.Simple;bf=b.pages[0].Resources.Font.Simple
            self.assertNotIn('/Encoding',bf)
            self.assertEqual(list(af.Widths),list(bf.Widths));self.assertEqual(af.ToUnicode.read_bytes(),bf.ToUnicode.read_bytes())
            self.assertEqual(af.FontDescriptor.FontFile2.read_raw_bytes(),bf.FontDescriptor.FontFile2.read_raw_bytes())

    def test_raw_and_flate_image_alpha_streams_are_unchanged(self):
        base=fixture();source=WORK/'image-streams.pdf'
        with pikepdf.Pdf.open(base)as pdf:
            page=pdf.pages[0]
            for name,compressed in [('RawImage',False),('FlateImage',True)]:
                color=b'\x80\x40';alpha=b'\xff\x00\xaa\xff'
                mask=pdf.make_stream(zlib.compress(alpha)if compressed else alpha)
                mask.Type=pikepdf.Name.XObject;mask.Subtype=pikepdf.Name.Image
                mask.Width=2;mask.Height=2;mask.BitsPerComponent=8;mask.ColorSpace=pikepdf.Name.DeviceGray
                image=pdf.make_stream(zlib.compress(color)if compressed else color)
                image.Type=pikepdf.Name.XObject;image.Subtype=pikepdf.Name.Image
                image.Width=2;image.Height=2;image.BitsPerComponent=1;image.ColorSpace=pikepdf.Name.DeviceGray;image.SMask=mask
                if compressed:mask.Filter=pikepdf.Name.FlateDecode;image.Filter=pikepdf.Name.FlateDecode
                page.Resources.XObject['/'+name]=image
            page.Contents=pikepdf.Array([page.Contents,pdf.make_stream(b'q 20 0 0 20 300 400 cm /RawImage Do Q q 20 0 0 20 350 400 cm /FlateImage Do Q')])
            pdf.save(source,compress_streams=False)
        doc=fitz.open(source);stroke=next(t for t in doc[0].get_texttrace()if t['type']==1)
        selected=[dict(c=chr(cp),font=stroke['font'],size=stroke['size'],origin=origin,bbox=bbox)for cp,gid,origin,bbox in stroke['chars']if not chr(cp).isspace()]
        payload,count=suppress_prose(source,1,selected);self.assertEqual(count,len('Explain'))
        target=WORK/'image-streams-suppressed.pdf';target.write_bytes(payload)
        with pikepdf.Pdf.open(source)as a,pikepdf.Pdf.open(target)as b:
            for name in ['/RawImage','/FlateImage']:
                left=a.pages[0].Resources.XObject[name];right=b.pages[0].Resources.XObject[name]
                for before,after in [(left,right),(left.SMask,right.SMask)]:
                    self.assertEqual(before.read_raw_bytes(),after.read_raw_bytes());self.assertEqual(before.read_bytes(),after.read_bytes())
                    self.assertEqual(str(before.get('/Filter')),str(after.get('/Filter')))
            self.assertEqual(len(a.pages[0].Resources.XObject.RawImage.read_raw_bytes()),2)
            self.assertIsNone(a.pages[0].Resources.XObject.RawImage.get('/Filter'))
            self.assertEqual(str(a.pages[0].Resources.XObject.FlateImage.Filter),'/FlateDecode')
        result=audit(source,target,dict(source_page=1,erased_glyph_origins=[c['origin']for c in selected],allowed_rects=[[c['bbox'][0]-2,c['bbox'][1]-2,c['bbox'][2]+2,c['bbox'][3]+2]for c in selected]))
        self.assertEqual(result['native_glyphs_changed'],[]);self.assertEqual(result['changed_pixels_in_native_glyph_neighborhood'],0);self.assertEqual(result['changed_pixels_outside_prose'],0)
        doc.close()

if __name__=='__main__':unittest.main()
