"""Real PDF regressions: image bytes, native ink, guards, and outside changes."""
from pathlib import Path
from io import BytesIO
import tempfile,unittest
import hashlib
import pymupdf as fitz
from PIL import Image,ImageDraw
import pdf_white_raster_original_style as raster


class RasterOverlayTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.root=Path(self.temporary.name);self.font=Path('C:/Windows/Fonts/times.ttf')
        image=Image.new('RGB',(200,120),'white');draw=ImageDraw.Draw(image)
        # Known old-language ink, separate native fraction and a thin rule.
        draw.rectangle((20,25,25,42),fill='black');draw.rectangle((30,25,35,42),fill='black')
        draw.line((140,40,180,40),fill='black',width=1)
        draw.rectangle((153,30,158,35),fill='black');draw.rectangle((153,45,158,50),fill='black')
        draw.point((91,39),fill=(96,96,96));draw.point((103,47),fill=(128,128,128))
        buf=BytesIO();image.save(buf,format='PNG')
        source=fitz.open();page=source.new_page(width=200,height=120)
        page.insert_image(page.rect,stream=buf.getvalue());page.insert_text((10,12),'native X=1',fontsize=8)
        self.source=self.root/'source.pdf';source.save(self.source,deflate=False);source.close()

    def tearDown(self):self.temporary.cleanup()

    def region(self,**changes):
        region=dict(id='language',source_text='fixture language strokes',erase_rects=[[18,23,38,45]],
            point=[19,42],right=100,text='Text',size=10,font_path=str(self.font),reviewed=True)
        region.update(changes);return region

    def test_original_image_and_native_text_unchanged(self):
        proof=self.root/'translated.pdf'
        qa=raster.apply(self.source,1,self.source,proof,[self.region()],self.root/'fonts')
        self.assertTrue(qa['passed']);self.assertEqual(qa['source_native_image_paint_count'],1)
        self.assertTrue(qa['checks']['original_image_programs_and_raw_bytes_and_filters_and_smask_and_ctm_unchanged'])
        self.assertEqual(qa['checks']['base_native_text_glyphs_changed'],0)

    def test_math_inside_language_rectangle_is_explicitly_preserved(self):
        proof=self.root/'guarded.pdf'
        item=self.region(erase_rects=[[18,23,184,54]],protected_rects=[[139,28,182,52]])
        qa=raster.apply(self.source,1,self.source,proof,[item],self.root/'fonts')
        self.assertTrue(qa['passed']);self.assertEqual(qa['checks']['changed_pixels_in_explicit_math_protection'],0)

    def test_new_prose_touching_native_fraction_fails(self):
        proof=self.root/'collision.pdf'
        item=self.region(point=[143,49],right=195,text='MMMM',size=12)
        with self.assertRaisesRegex(ValueError,'changed native ink'):
            raster.apply(self.source,1,self.source,proof,[item],self.root/'fonts')
        import json
        qa=json.loads(proof.with_suffix('.raster-qa.json').read_text('utf8'))
        self.assertFalse(qa['passed']);self.assertGreater(qa['checks']['changed_original_nonlanguage_guard_pixels'],0)

    def test_changes_on_unpainted_background_outside_prose_fail(self):
        proof=self.root/'translated.pdf';regions=[self.region()]
        qa=raster.apply(self.source,1,self.source,proof,regions,self.root/'fonts')
        changed=self.root/'outside.pdf'
        with fitz.open(proof)as doc:
            doc[0].draw_rect(fitz.Rect(110,90,125,100),color=None,fill=(0,0,0));doc.save(changed,deflate=False)
        bad=raster.audit(self.source,1,self.source,changed,regions,qa['placements'])
        self.assertFalse(bad['passed']);self.assertGreater(bad['checks']['changed_pixels_outside_old_and_new_language'],0)

    def background(self,rect,ink):
        return dict(rect=rect,reviewed=True,reason='Scan dust in manually reviewed blank prose background',
            source_sha256=hashlib.sha256(self.source.read_bytes()).hexdigest(),source_ink_bbox=ink,
            evidence='Synthetic source bitmap: explicit gray-pixel locations in this regression')

    def test_unreviewed_scan_dust_remains_protected(self):
        item=self.region(point=[90,45],right=110,text='M',size=12)
        with self.assertRaisesRegex(ValueError,'changed native ink'):
            raster.apply(self.source,1,self.source,self.root/'dust-fails.pdf',[item],self.root/'fonts')

    def test_explicit_blank_background_allows_dust_without_white_fill(self):
        item=self.region(point=[90,45],right=110,text='M',size=12,
            reviewed_blank_background_rects=[self.background([88,32,106,50],[91,39,104,48])])
        proof=self.root/'dust-reviewed.pdf'
        qa=raster.apply(self.source,1,self.source,proof,[item],self.root/'fonts')
        self.assertTrue(qa['passed']);self.assertFalse(qa['reviewed_blank_backgrounds_painted_white'])
        with fitz.open(self.source)as a,fitz.open(proof)as b:
            aa=raster._rgb(a[0],4);bb=raster._rgb(b[0],4)
            self.assertTrue((aa[47*4:48*4,103*4:104*4]==bb[47*4:48*4,103*4:104*4]).all())

    def test_explicit_math_is_protected_inside_reviewed_background(self):
        item=self.region(point=[143,49],right=195,text='MMMM',size=12,
            reviewed_blank_background_rects=[self.background([138,28,184,54],[140,30,181,51])],
            protected_rects=[[139,28,182,52]])
        with self.assertRaisesRegex(ValueError,'changed native ink'):
            raster.apply(self.source,1,self.source,self.root/'background-math-fails.pdf',[item],self.root/'fonts')

    def test_reviewed_fill_stroke_keeps_original_size_baseline_and_native_ink(self):
        proof=self.root/'stroke.pdf'
        item=self.region(render_mode=2,line_width=.6,style_evidence='Known synthetic source style:0.6pt fill and stroke')
        qa=raster.apply(self.source,1,self.source,proof,[item],self.root/'fonts')
        self.assertTrue(qa['passed']);row=qa['placements'][0]
        self.assertEqual(row['point'],item['point']);self.assertEqual(row['size'],item['size'])
        with fitz.open(proof)as doc:
            new=[t for t in doc[0].get_texttrace()if t['font']=='TimesNewRomanPSMT']
            self.assertEqual({t['type']for t in new},{0,1})
            self.assertTrue(all(abs(t['size']-10)<1e-6 for t in new))
            self.assertTrue(all(abs(c[2][1]-42)<1e-6 for t in new for c in t['chars']))
            self.assertTrue(all(abs(t['linewidth']-.6)<1e-6 for t in new if t['type']==1))

    def test_stroke_collision_is_not_excluded_by_new_prose_bounds(self):
        fill=self.region(point=[136.5,42],right=150,text='I',size=12)
        raster.apply(self.source,1,self.source,self.root/'fill.pdf',[fill],self.root/'fonts')
        stroke=dict(fill,render_mode=2,line_width=4,
            style_evidence='Synthetic exaggerated source stroke tests a math collision invisible to fill-only checking')
        with self.assertRaisesRegex(ValueError,'changed native ink'):
            raster.apply(self.source,1,self.source,self.root/'stroke-collision.pdf',[stroke],self.root/'fonts')

    def test_unreviewed_stroke_or_unsupported_mode_is_rejected(self):
        for change in [dict(render_mode=2,line_width=.6),dict(render_mode=2,line_width=0,style_evidence='source'),
                       dict(render_mode=0,line_width=.6),dict(render_mode=1,line_width=.6,style_evidence='source')]:
            with self.subTest(change=change),self.assertRaises(ValueError):
                raster.preflight([self.region(**change)],fitz.Rect(0,0,200,120))


if __name__=='__main__':unittest.main()
