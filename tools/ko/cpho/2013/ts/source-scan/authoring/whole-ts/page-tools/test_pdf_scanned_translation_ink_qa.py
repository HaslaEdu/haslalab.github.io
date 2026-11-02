"""Small real-PDF regressions for scan math/prose paint ordering and ink QA."""
from pathlib import Path
from io import BytesIO
import json,unittest
from PIL import Image,ImageDraw
import pymupdf as fitz
from pdf_scanned_translation_ink_qa import audit_scan_page
BASE=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/generic-scan-qa-regressions')
class ScanQa(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  BASE.mkdir(exist_ok=True);im=Image.new('RGB',(200,40),'white');d=ImageDraw.Draw(im);d.rectangle((4,15,30,20),fill='black');d.rectangle((16,4,20,32),fill='black');raw=BytesIO();im.save(raw,format='PNG');cls.img=raw.getvalue()
  doc=fitz.open();p=doc.new_page(width=180,height=120);p.insert_image(fitz.Rect(30,40,130,60),stream=cls.img);doc.save(BASE/'source.pdf');doc.close()
 def case(self,name,*,before=False,x=90,damage=False):
  ref=fitz.open();p=ref.new_page(width=180,height=120);p.insert_text((x,55),'K',fontsize=12);ref.save(BASE/(name+'-prose.pdf'));ref.close()
  final=fitz.open();p=final.new_page(width=180,height=120)
  if before:p.insert_text((x,55),'K',fontsize=12)
  p.insert_image(fitz.Rect(30,40,130,60),stream=self.img)
  if not before:p.insert_text((x,55),'K',fontsize=12)
  if damage:p.draw_rect(fitz.Rect(30,40,47,60),color=None,fill=(1,1,1),overlay=True)
  final.save(BASE/(name+'.pdf'));final.close()
  result=audit_scan_page(BASE/'source.pdf',1,BASE/(name+'.pdf'),BASE/'source.pdf',BASE/(name+'-prose.pdf'),language_erase_rects=[],new_prose_rects=[[x-2,40,x+14,60]],protected_source_rects=[[30,40,47,60]])
  (BASE/(name+'.json')).write_text(json.dumps(result,indent=2),'utf8');return result
 def test_math_first_prose_last_pass(self):self.assertTrue(self.case('math-first')['passed'])
 def test_later_bitmap_white_padding_hiding_prose_fails(self):
  q=self.case('padding-after-prose',before=True);self.assertFalse(q['passed']);self.assertGreater(q['new_prose_expected_dark_pixels_missing']['pixels'],0);self.assertEqual(q['new_prose_overlap_original_or_replayed_nonlanguage_ink']['pixels'],0)
 def test_black_prose_over_math_is_independently_rejected(self):
  q=self.case('black-overprint',x=34);self.assertFalse(q['passed']);self.assertGreater(q['new_prose_overlap_original_or_replayed_nonlanguage_ink']['pixels'],0)
 def test_original_math_whiteout_is_rejected(self):
  q=self.case('math-damage',damage=True);self.assertFalse(q['passed']);self.assertGreater(q['independent_protected_source_ink_lost']['pixels'],0)
if __name__=='__main__':unittest.main()
