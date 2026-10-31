"""Regression for original bitmap equations absent from every text trace."""
from pathlib import Path
from io import BytesIO
import unittest
import pikepdf
import pymupdf as fitz
import test_izho_native_atomic_tokens as fixtures
from izho_native_atomic_tokens import atomic_tokens
from pdf_native_inline_reposition import inspect_inline_groups,reposition_inline
from pdf_native_geometry_motion import audit as geometry_audit

OUT=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-natural-spacing/atomic-image-fixtures')

class ImageOnlyMathematicalAtoms(unittest.TestCase):
    def source(self,name,form=False,transparent=False):
        with pikepdf.open(BytesIO(fixtures.fixture(b'')))as pdf:
            image=pdf.make_stream(bytes(4));image.Type=pikepdf.Name.XObject;image.Subtype=pikepdf.Name.Image
            image.Width=2;image.Height=2;image.BitsPerComponent=8;image.ColorSpace=pikepdf.Name.DeviceGray
            if transparent:
                mask=pdf.make_stream(bytes(4));mask.Type=pikepdf.Name.XObject;mask.Subtype=pikepdf.Name.Image
                mask.Width=2;mask.Height=2;mask.BitsPerComponent=8;mask.ColorSpace=pikepdf.Name.DeviceGray;image.SMask=mask
            page=pdf.pages[0]
            if form:
                widget=pdf.make_stream(b'q 8 0 0 8 2 4 cm /Bitmap Do Q');widget.Type=pikepdf.Name.XObject
                widget.Subtype=pikepdf.Name.Form;widget.BBox=pikepdf.Array([0,0,12,20])
                widget.Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(Bitmap=image))
                page.Resources.XObject=pikepdf.Dictionary(Math=widget)
                page.Contents=pdf.make_stream(b'q 1 0 0 1 60 680 cm /Math Do Q')
            else:
                page.Resources.XObject=pikepdf.Dictionary(Bitmap=image)
                page.Contents=pdf.make_stream(b'q 8 0 0 8 60 680 cm /Bitmap Do Q')
            OUT.mkdir(parents=True,exist_ok=True);target=OUT/name;pdf.save(target,compress_streams=False);return target

    def atoms(self,path,**kwargs):
        return atomic_tokens(path,1,[35,148,180,166],[dict(baseline=158,size=12)],**kwargs)

    def test_original_image_without_text_is_opt_in_and_has_exact_operator_path(self):
        path=self.source('direct.pdf')
        self.assertEqual(self.atoms(path),[])
        atoms=self.atoms(path,include_image_only=True)
        self.assertEqual(len(atoms),1);self.assertEqual(atoms[0]['glyphs'],[])
        self.assertEqual(atoms[0]['atomic_native_group'],'image')
        self.assertEqual(len(atoms[0]['shift_kwargs']['image_path']),1)
        self.assertEqual((atoms[0]['x0'],atoms[0]['x1']),(60,68))

    def test_nested_bitmap_selects_complete_original_glyphless_form(self):
        atoms=self.atoms(self.source('form.pdf',form=True),include_image_only=True)
        self.assertEqual(len(atoms),1);self.assertEqual(atoms[0]['atomic_native_group'],'image-form')
        self.assertIn('form_path',atoms[0]['shift_kwargs']);self.assertNotIn('image_path',atoms[0]['shift_kwargs'])

    def test_fully_transparent_image_and_excluded_figure_are_not_math_tokens(self):
        path=self.source('transparent.pdf',transparent=True)
        self.assertEqual(self.atoms(path,include_image_only=True),[])
        path=self.source('figure.pdf')
        self.assertEqual(self.atoms(path,include_image_only=True,excluded_rects=[[55,140,80,166]]),[])

    def test_native_image_motion_preserves_other_actual_graphics(self):
        initial=self.source('geometry-initial.pdf')
        with fitz.open(initial)as doc:
            doc[0].draw_rect(fitz.Rect(200,200,220,220),color=None,fill=(0,0,0))
            source=OUT/'geometry-source.pdf';doc.save(source)
        image=inspect_inline_groups(source,1)['images'][0]
        shifts=[dict(glyphs=[],image_path=image['path'],dx=8)]
        payload,qa=reposition_inline(source,1,shifts=shifts);self.assertTrue(qa['passed'])
        target=OUT/'geometry-moved.pdf';target.write_bytes(payload)
        _,good=geometry_audit(source,target,shifts)
        self.assertEqual(good['changed_nonselected_native_graphical_pixels'],0)
        self.assertGreater(good['original_native_math_actual_graphics_pixels'],0)
        with fitz.open(target)as doc:
            doc[0].draw_rect(fitz.Rect(199,199,221,221),color=None,fill=(1,1,1))
            damaged=OUT/'geometry-damaged-static-figure.pdf';doc.save(damaged)
        _,bad=geometry_audit(source,damaged,shifts)
        self.assertGreater(bad['changed_nonselected_native_graphical_pixels'],0)

    def test_inline_bitmap_is_not_collected_by_the_adjacent_prose_row(self):
        initial=self.source('adjacent-initial.pdf')
        with pikepdf.open(initial)as pdf:
            pdf.pages[0].Contents=pdf.make_stream(
                b'q 10.6 0 0 14.25 336.1 690.45 cm /Bitmap Do Q '
                b'q 4.55 0 0 14.3 119.75 676.15 cm /Bitmap Do Q')
            source=OUT/'adjacent-original-Word-lineboxes.pdf';pdf.save(source,compress_streams=False)
        first=atomic_tokens(source,1,[84,138.36,370,154.32],[dict(baseline=148.56,size=12)],include_image_only=True)
        second=atomic_tokens(source,1,[84,152.64,370,168.60],[dict(baseline=162.84,size=12)],include_image_only=True)
        self.assertEqual(len(first),1);self.assertEqual(len(second),1)
        self.assertAlmostEqual(first[0]['x0'],336.1,places=3)
        self.assertAlmostEqual(second[0]['x0'],119.75,places=3)

if __name__=='__main__':unittest.main()
