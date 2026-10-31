"""Real source bitmap: old prose witness never permits new mathematical damage."""
from pathlib import Path
import tempfile,unittest
import pikepdf
import pymupdf as fitz
import cpho_2013_original_raster as raster
import cpho_2013_original_raster_guard as guard
from cpho_2013_original_extract import SOURCE

ROOT=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/regressions')

class CircleJunctionTests(unittest.TestCase):
    def test_prose_only_witness_and_new_ink_rejection(self):
        ROOT.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT)as folder:
            directory=Path(folder);self.assertTrue(directory.resolve().is_relative_to(ROOT.resolve()))
            base=directory/'base.pdf';proof=directory/'proof.pdf'
            with pikepdf.open(SOURCE)as src,pikepdf.new()as out:
                out.pages.append(src.pages[2]);out.save(base,compress_streams=False)
            qa=raster.overlay(3,'ko',base,proof)
            witness=qa['document_specific_old_prose_guard_witness']
            self.assertFalse(qa['passed'])
            self.assertTrue(witness['passed'])
            self.assertEqual(len(witness['source_to_proof_coarse_guard_pixels_xy']),9)
            self.assertEqual(witness['new_language_expanded_guard_changed'],0)
            control=proof.with_suffix('.scan-erasure-control.pdf');regions=raster.plans(3,'ko')
            # A letter crossing the original circle is still rejected.
            changed=directory/'new-letter-over-circle.pdf'
            with fitz.open(proof)as doc:
                doc[0].insert_text((158,172),'X',fontsize=14);doc.save(changed,garbage=0,deflate=False)
            bad=guard.audit(base,control,changed,regions)
            self.assertFalse(bad['passed']);self.assertGreater(bad['new_language_actual_native_ink_changed'],0)
            # Even a new quarter-point dot only in the old-prose expanded
            # guard is rejected; actual-ink protection is not the sole check.
            changed=directory/'new-dot-in-old-prose-guard.pdf'
            with fitz.open(proof)as doc:
                doc[0].draw_rect(fitz.Rect(166.75,172.25,167,172.5),color=None,fill=(0,0,0))
                doc.save(changed,garbage=0,deflate=False)
            bad=guard.audit(base,control,changed,regions)
            self.assertFalse(bad['passed']);self.assertGreater(bad['new_language_expanded_guard_changed'],0)

if __name__=='__main__':unittest.main()
