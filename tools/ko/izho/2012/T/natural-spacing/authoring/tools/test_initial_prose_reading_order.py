import unittest,json,copy
from pathlib import Path
import pymupdf as fitz
from izho_natural_spacing import baseline_lines,visible
from pdf_korean_natural_composer import normalize_placements
from initial_prose_reading_order import journal,rewrite
B=Path(__file__).resolve().parents[1]
class ActualInitialSourceOrder(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.plan=json.loads((B/'natural/2014/T/plans/page03.json').read_text('utf8'))
  cls.doc=fitz.open(cls.plan['source_base']);cls.page=cls.doc[2]
  cls.placements=normalize_placements(cls.page,cls.plan['prose_placements']);cls.journal=journal(cls.page,cls.placements)
  cls.rect=next(r for r in cls.plan['allowed_line_rects']if r[1]<328.44<r[3])
  cls.lines=baseline_lines(cls.page,allowed_line_rects=[cls.rect],prose_placements=cls.placements,baseline_tolerance_pt=.75)
 @classmethod
 def tearDownClass(cls):cls.doc.close()
 def corrected(self):return rewrite(self.lines,self.page,self.rect,self.placements,self.journal,.75)[0]
 def test_actual_overlapping_prose_stays_before_native_mu(self):
  old=self.lines[0]['tokens'];old_mu=next(i for i,t in enumerate(old)if any(g['c']in['µ','μ']for g in t['glyphs']))
  self.assertTrue(any('소모율'in t['text']for t in old[old_mu+1:]))
  new=self.corrected()[0]['tokens'];mu=next(i for i,t in enumerate(new)if any(g['c']in['µ','μ']for g in t['glyphs']))
  self.assertIn('연료 소모율',new[mu-1]['text']);self.assertTrue(new[mu-1]['source_slot_reading_order'])
 def test_native_glyphs_are_not_rewritten_or_omitted(self):
  authored=set().union(*(r['trace_keys']for r in self.journal))
  key=lambda g:(g['trace'],g['index'])
  def native(lines):return{key(g):(g['c'],g['font'],g['gid'],g['size'],tuple(g['origin']))for line in lines for t in line['tokens']for g in visible(t['glyphs'])if key(g)not in authored}
  self.assertEqual(native(self.lines),native(self.corrected()))
 def test_stale_authored_text_is_rejected(self):
  altered=copy.deepcopy(self.placements);altered[0]['text']='X'+altered[0]['text']
  with self.assertRaises(ValueError):journal(self.page,altered)
 def test_duplicate_logical_row_is_rejected(self):
  with self.assertRaises(ValueError):rewrite(self.lines+self.lines,self.page,self.rect,self.placements,self.journal,.75)
if __name__=='__main__':unittest.main()
