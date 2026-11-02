"""Real-source preservation and fail-closed regressions for the isolated fork."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest,re,os
from collections import Counter
import pikepdf
import pymupdf as fitz
import pdf_latex_text_ops as ops
from latex_native_proof import source_records,compare_native,font_programs,native_images,drawings

ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path(os.environ.get('LATEX_NATIVE_PLANCKS_SOURCE',str(ROOT/'tmp/source-audit/PLANCKS_2026_T_EN.pdf')))

def alpha_selection(page):
    return [r for r in source_records(page)if r['font'].startswith(('CMR','CMBX','CMSL','CMTI','CMCSC','SFRM','SFBX','SFTI','SFTT'))and r['c'].isalpha()]

@unittest.skipUnless(SOURCE.is_file(),'Place the official PLANCKS2026 source at tmp/source-audit or set LATEX_NATIVE_PLANCKS_SOURCE')
class LatexNative(unittest.TestCase):
    def test_ortvay10pages_preserve_unselected_native_glyphs(self):
        path=Path(os.environ.get('LATEX_NATIVE_ORTVAY_SOURCE',str(ROOT/'tmp/source-audit/Ortvay_2026_T_EN.pdf')))
        if not path.is_file():self.skipTest('Place the official Ortvay2026 source at tmp/source-audit or set LATEX_NATIVE_ORTVAY_SOURCE')
        doc=fitz.open(path)
        for pi,page in enumerate(doc):
            with self.subTest(page=pi+1):
                selected=alpha_selection(page);counts=Counter(ops.glyph_key(r)for r in selected);remaining=[]
                for r in source_records(page):
                    key=ops.glyph_key(r)
                    if counts[key]:counts[key]-=1
                    else:remaining.append(r)
                raw,n=ops.suppress_prose(path,pi+1,selected);out=fitz.open(stream=raw,filetype='pdf')
                result=compare_native(remaining,source_records(out[0]))
                self.assertEqual(result['missing'],[]);self.assertEqual(result['extra'],0)
                self.assertEqual(n,len(selected));self.assertEqual(font_programs(doc,page),font_programs(out,out[0]))
                self.assertEqual(native_images(page),native_images(out[0]));self.assertEqual(drawings(page),drawings(out[0]))
                out.close()
        doc.close()

    def test_real18pages_preserve_all_unselected_glyphs_and_native_objects(self):
        doc=fitz.open(SOURCE);removed=0
        for pi,page in enumerate(doc):
            with self.subTest(page=pi+1):
                selected=alpha_selection(page);counts=Counter(ops.glyph_key(r)for r in selected)
                remain=[]
                for r in source_records(page):
                    key=ops.glyph_key(r)
                    if counts[key]:counts[key]-=1
                    else:remain.append(r)
                raw,n=ops.suppress_prose(SOURCE,pi+1,selected);out=fitz.open(stream=raw,filetype='pdf')
                result=compare_native(remain,source_records(out[0]))
                self.assertEqual(result['missing'],[]);self.assertEqual(result['extra'],0)
                self.assertEqual(n,len(selected));removed+=n
                self.assertEqual(font_programs(doc,page),font_programs(out,out[0]))
                self.assertEqual(native_images(page),native_images(out[0]))
                self.assertEqual(drawings(page),drawings(out[0]));self.assertEqual(page.rect,out[0].rect)
                out.close()
        self.assertGreater(removed,15000);doc.close()

    def test_partial_fi_ligature_is_rejected(self):
        doc=fitz.open(SOURCE);records=source_records(doc[1])
        continuation=next(r for r in records if r['gid']==-1 and r['c']=='i')
        with self.assertRaisesRegex(ValueError,'only part'):ops.suppress_prose(SOURCE,2,[continuation])
        doc.close()

    def test_whole_ffi_with_repeated_f_identity_is_suppressed_once(self):
        doc=fitz.open(SOURCE);rows=source_records(doc[12])
        i=next(i for i in range(len(rows)-2)if ''.join(r['c']for r in rows[i:i+3])=='ffi'and rows[i+1]['gid']==rows[i+2]['gid']==-1)
        cluster=rows[i:i+3];self.assertEqual(ops.glyph_key(cluster[0]),ops.glyph_key(cluster[1]))
        raw,n=ops.suppress_prose(SOURCE,13,cluster);self.assertEqual(n,3)
        out=fitz.open(stream=raw,filetype='pdf');remain=rows[:i]+rows[i+3:]
        self.assertEqual(compare_native(remain,source_records(out[0]))['missing'],[])
        with self.assertRaisesRegex(ValueError,'only part'):ops.suppress_prose(SOURCE,13,[cluster[0],cluster[2]])
        doc.close();out.close()

    def test_profile_requires_embedded_program_explicit_widths_and_single_byte_map(self):
        with pikepdf.Pdf.open(SOURCE)as q:
            f=next(iter(q.pages[0].Resources.Font.values()))
            self.assertEqual(ops.source_code_bytes(f),1)
            original=f.ToUnicode;del f['/ToUnicode']
            with self.assertRaisesRegex(ValueError,'explicit Widths and ToUnicode'):ops.source_code_bytes(f)
            f.ToUnicode=original;original_widths=f.Widths;f.Widths=pikepdf.Array([1])
            with self.assertRaisesRegex(ValueError,'invalid explicit Widths'):ops.source_code_bytes(f)
            f.Widths=original_widths;program=f.FontDescriptor.FontFile;del f.FontDescriptor['/FontFile']
            with self.assertRaisesRegex(ValueError,'embedded Type1'):ops.source_code_bytes(f)
            f.FontDescriptor.FontFile=program
            f.ToUnicode=q.make_stream(b'1 begincodespacerange <0000> <00FF> endcodespacerange 1 beginbfchar <0050> <0050> endbfchar')
            with self.assertRaisesRegex(ValueError,'single-byte'):ops.source_code_bytes(f)

    def test_source_unicode_vs_trace_mismatch_is_rejected(self):
        with TemporaryDirectory(dir=Path(__file__).parent)as tmp:
            bad=Path(tmp)/'bad-map.pdf'
            with pikepdf.Pdf.open(SOURCE)as q:
                f=next(iter(q.pages[0].Resources.Font.values()))
                original=f.ToUnicode.read_bytes()
                patched,n=re.subn(rb'<50>\s*<0050>',b'<50> <0051>',original)
                if not n:
                    # TeX uses a bfrange covering P; an appended explicit
                    # bfchar overrides it in the helper's authoritative map.
                    patched=original.replace(b'endcmap',b'1 beginbfchar\n<50> <0051>\nendbfchar\nendcmap')
                f.ToUnicode=q.make_stream(patched);q.save(bad)
            # MuPDF also obeys the changed ToUnicode, so select the *reviewed
            # original* P record; the exact selected-geometry guard must fail.
            original_doc=fitz.open(SOURCE);selected=alpha_selection(original_doc[0])
            with self.assertRaises(ValueError):ops.suppress_prose(bad,1,selected)
            original_doc.close()

if __name__=='__main__':unittest.main(verbosity=2)
