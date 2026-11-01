from pathlib import Path
import sys,json,copy,unittest
import pikepdf,pymupdf as fitz
B=Path(__file__).resolve().parents[1];sys.path[:0]=[str(B/'engine'),str(Path.cwd()/'tools')]
from initial_bitmap_language_labels import apply,masks
from izho_natural_spacing_qa import fresh_render
from izho_initial_fixed_style import native_image_programs,native_font_programs
from pdf_memory_gate import page_worker

class BitmapLabels(unittest.TestCase):
 def test_real_piston_words_only_and_programs_retained(self):
  with page_worker():
   d=json.loads((B/'natural/2012/T/plans/page03.json').read_text('utf8'));f=B/'bitmap-label-tests';f.mkdir(exist_ok=True);p=f/'real-source-page.pdf'
   with pikepdf.open(d['original_english_source'])as src,pikepdf.Pdf.new()as dst:dst.pages.append(src.pages[2]);dst.save(p,compress_streams=False)
   old_images=native_image_programs(p,1);old_fonts=native_font_programs(p,1);rgb=fresh_render(p,1,f/'source.png');report=apply(d,p);a,b,q=masks(d,p,rgb)
   self.assertEqual(q['new_label_over_original_nonlanguage_foreground_pixels'],0)
   self.assertEqual(old_images,native_image_programs(p,1));self.assertTrue(all(font in native_font_programs(p,1)for font in old_fonts))
   new=fresh_render(p,1,f/'translated.png');import numpy as np
   self.assertEqual(int((np.any(rgb!=new,axis=2)&~(a|b)).sum()),0)
   self.assertEqual(q['labels'],3)
 def test_overshoot_into_actual_nonlanguage_drawing_is_rejected(self):
  with page_worker():
   d=json.loads((B/'natural/2012/T/plans/page03.json').read_text('utf8'));d=copy.deepcopy(d);d['reviewed_bitmap_language_labels'][0]['measured_source_baseline_pt']=144
   f=B/'bitmap-label-tests';f.mkdir(exist_ok=True);p=f/'negative-crossing-piston.pdf'
   with pikepdf.open(d['original_english_source'])as src,pikepdf.Pdf.new()as dst:dst.pages.append(src.pages[2]);dst.save(p,compress_streams=False)
   rgb=fresh_render(p,1,f/'negative-source.png');apply(d,p)
   with self.assertRaisesRegex(ValueError,'nonlanguage picture ink'):masks(d,p,rgb)
if __name__=='__main__':unittest.main()
