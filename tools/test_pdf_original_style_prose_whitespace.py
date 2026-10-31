"""Only reviewed actual prose spaces may change; all native ink stays locked."""
from pathlib import Path
import unittest
import pymupdf as fitz
from pdf_original_style_audit import audit,glyphs

WORK=Path(__file__).resolve().parents[1]/'tmp/native-prose-whitespace-regressions'

def fixture(name,selected_x=85,unselected_x=180,visible_x=100):
    WORK.mkdir(parents=True,exist_ok=True)
    doc=fitz.open();page=doc.new_page();page.insert_font(fontname='helv')
    xref=doc.get_new_xref();doc.update_object(xref,'<<>>')
    doc.update_stream(xref,(f'BT /helv 12 Tf 1 0 0 1 72 700 Tm (A) Tj '
        f'1 0 0 1 {selected_x} 700 Tm ( ) Tj '
        f'1 0 0 1 {visible_x} 700 Tm (B) Tj '
        f'1 0 0 1 {unselected_x} 700 Tm ( ) Tj ET').encode())
    page.set_contents(xref);path=WORK/(name+'.pdf');doc.save(path,garbage=0,deflate=False);doc.close();return path

def source_spec(source):
    doc=fitz.open(source);g=next(g for g in glyphs(doc[0])if g['c']==' 'and g['origin'][0]==85)
    entry={k:g[k]for k in ['c','font','size','origin']};doc.close()
    return dict(source_page=1,allowed_rects=[[80,125,96,150]],mutable_prose_whitespace_glyphs=[entry])

class ProseWhitespaceAuditTests(unittest.TestCase):
    def test_only_selected_actual_prose_space_is_mutable(self):
        source=fixture('source');target=fixture('selected-space-moved',selected_x=85.1)
        spec=source_spec(source);strict=audit(source,target,dict(source_page=1,allowed_rects=spec['allowed_rects']))
        self.assertEqual(len(strict['native_glyphs_changed']),1)
        result=audit(source,target,spec)
        self.assertEqual(result['selected_prose_actual_whitespace_glyphs_checked'],1)
        self.assertEqual(result['native_glyphs_changed'],[])
        self.assertEqual(result['changed_pixels_in_native_glyph_neighborhood'],0)
        self.assertEqual(result['changed_pixels_outside_prose'],0)

    def test_unselected_spaces_and_visible_glyphs_remain_native(self):
        source=fixture('source');spec=source_spec(source)
        moved_space=fixture('native-space-moved',unselected_x=180.1)
        result=audit(source,moved_space,spec)
        self.assertTrue(result['native_glyphs_changed'])
        self.assertEqual(result['native_glyphs_changed'][0]['c'],' ')
        moved_visible=fixture('visible-glyph-moved',visible_x=101)
        result=audit(source,moved_visible,spec)
        self.assertTrue(any(g['c']=='B'for g in result['native_glyphs_changed']))
        self.assertGreater(result['changed_pixels_in_native_glyph_neighborhood'],0)

    def test_protected_or_synthetic_space_journals_fail_closed(self):
        source=fixture('source');spec=source_spec(source);entry=spec['mutable_prose_whitespace_glyphs'][0]
        for extra in [dict(protected_glyph_origins=[entry['origin']]),dict(protected_whitespace_glyphs=[entry])]:
            with self.assertRaisesRegex(ValueError,'protected native math/Form whitespace'):audit(source,source,{**spec,**extra})
        synthetic={**entry,'origin':[85.05,entry['origin'][1]]}
        with self.assertRaisesRegex(ValueError,'actual source-trace whitespace'):audit(source,source,{**spec,'mutable_prose_whitespace_glyphs':[synthetic]})
        with self.assertRaisesRegex(ValueError,'actual source-trace whitespace'):audit(source,source,{**spec,'mutable_prose_whitespace_glyphs':[{**entry,'c':'A'}]})
        doc=fitz.open(source);unselected=next(g for g in glyphs(doc[0])if g['c']==' 'and g['origin'][0]==180);doc.close()
        with self.assertRaisesRegex(ValueError,'outside the explicit prose frames'):audit(source,source,{**spec,'mutable_prose_whitespace_glyphs':[{k:unselected[k]for k in ['c','font','size','origin']}]})

if __name__=='__main__':unittest.main()
