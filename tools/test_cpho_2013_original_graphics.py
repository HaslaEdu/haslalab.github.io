"""Authoring integration regressions against the exact original/preview pair."""
import unittest
import pymupdf as fitz
import cpho_2013_original_build as b
import cpho_2013_original_graphics as graphics
from cpho_2013_original_qa import selected

AVAILABLE=b.source.SOURCE.exists()and(b.BASE/'ko/page01.pdf').exists()and(b.BASE/'ko/page01.control.pdf').exists()

@unittest.skipUnless(AVAILABLE,'Materialize the pinned original and reviewed2013KO page1 proof')
class OriginalProseGuardTests(unittest.TestCase):
    def test_original_prose_only_guard_is_proven_by_single_glyph_witness(self):
        proof=b.BASE/'ko/page01.pdf';control=proof.with_suffix('.control.pdf')
        result=graphics.audit(b.source.SOURCE,control,proof,selected(b.data()['pages'][0]))
        self.assertTrue(result['passed']);self.assertEqual(result['source_to_proof_guard_pixels_xy'],[[550,675]])
        self.assertEqual(result['source_to_proof_actual_nontext_changed'],0)
        self.assertEqual(result['control_to_proof_guard_changed'],0)

    def test_new_letter_touching_real_fraction_ink_is_rejected(self):
        proof=b.BASE/'ko/page01.pdf';control=proof.with_suffix('.control.pdf')
        bad=b.BASE/'regression-added-letter-over-fraction.pdf'
        with fitz.open(proof)as doc:
            doc[0].insert_text((137,174.5),'X',fontsize=11,fontname='helv',color=(0,0,0))
            doc.save(bad,garbage=0,deflate=False)
        result=graphics.audit(b.source.SOURCE,control,bad,selected(b.data()['pages'][0]))
        self.assertFalse(result['passed'])
        self.assertGreater(result['control_to_proof_actual_nontext_changed'],0)

if __name__=='__main__':unittest.main()
