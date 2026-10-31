"""Native replay must distinguish preserved ink from real later occlusion."""
from pathlib import Path
import unittest
import pymupdf as fitz
from test_izho_native_atomic_tokens import AtomicMathTokens
from pdf_native_inline_reposition import inspect_inline_groups,reposition_inline
from pdf_native_form_raster_witness import audit

OUT=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-natural-spacing/native-replay-fixtures')

class OriginalFormRasterWitness(unittest.TestCase):
    def test_exact_original_native_replay_passes_but_white_overlay_fails(self):
        OUT.mkdir(parents=True,exist_ok=True)
        source=OUT/'source.pdf';source.write_bytes(AtomicMathTokens().bitmap_form())
        group=inspect_inline_groups(source,1)['forms'][0]
        raw,qa=reposition_inline(source,1,shifts=[dict(glyphs=group['glyphs'],dx=10,form_path=group['path'])])
        self.assertTrue(qa['passed'])
        good=OUT/'native-shift.pdf';good.write_bytes(raw)
        _,passed=audit(source,1,group['path'],10,good)
        self.assertTrue(passed['passed'])
        with fitz.open(good)as doc:
            bounds=fitz.Rect(group['native_page_bbox'])+(10,0,10,0)
            doc[0].draw_rect(bounds,color=None,fill=(1,1,1),overlay=True)
            bad=OUT/'native-ink-hidden.pdf';doc.save(bad)
        _,failed=audit(source,1,group['path'],10,bad)
        self.assertFalse(failed['passed'])
        self.assertGreater(failed['actual_original_native_replay_missing_dark_pixels'],0)

if __name__=='__main__':unittest.main()
