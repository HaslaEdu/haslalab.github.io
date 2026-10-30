"""Regression: unchanged image bytes do not prove that math ink stays visible."""
from pathlib import Path
import tempfile,unittest
import pikepdf
import pymupdf as fitz
from pdf_original_graphics_ink import audit

ROOT=Path(__file__).resolve().parents[1]

def fixture(folder):
    seed=folder/'seed.pdf'
    pdf=pikepdf.Pdf.new();page=pdf.add_blank_page(page_size=(300,200))
    alpha=bytearray(128*128)
    for y in range(50,70):
        for x in range(80,90):alpha[y*128+x]=255
    soft=pdf.make_stream(bytes(alpha))
    soft.Type=pikepdf.Name.XObject;soft.Subtype=pikepdf.Name.Image
    soft.Width=128;soft.Height=128;soft.BitsPerComponent=8;soft.ColorSpace=pikepdf.Name.DeviceGray
    colour=pdf.make_stream(bytes(2*2*3))
    colour.Type=pikepdf.Name.XObject;colour.Subtype=pikepdf.Name.Image
    colour.Width=2;colour.Height=2;colour.BitsPerComponent=8;colour.ColorSpace=pikepdf.Name.DeviceRGB;colour.SMask=soft
    empty=pdf.make_stream(bytes(128*128));empty.Type=pikepdf.Name.XObject;empty.Subtype=pikepdf.Name.Image
    empty.Width=128;empty.Height=128;empty.BitsPerComponent=8;empty.ColorSpace=pikepdf.Name.DeviceGray;empty.Matte=pikepdf.Array([0,0,0])
    invisible=pdf.make_stream(bytes(2*2*3));invisible.Type=pikepdf.Name.XObject;invisible.Subtype=pikepdf.Name.Image
    invisible.Width=2;invisible.Height=2;invisible.BitsPerComponent=8;invisible.ColorSpace=pikepdf.Name.DeviceRGB;invisible.SMask=empty
    font=pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.Font,Subtype=pikepdf.Name.Type1,BaseFont=pikepdf.Name.Helvetica))
    inner=pdf.make_stream(b'BT /F0 10 Tf 1 0 0 1 2 12 Tm (FORM) Tj ET 0.7 w 0 0 m 20 10 l S')
    inner.Type=pikepdf.Name.XObject;inner.Subtype=pikepdf.Name.Form;inner.BBox=pikepdf.Array([0,0,40,25]);inner.Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(F0=font))
    outer=pdf.make_stream(b'q /Inner Do Q');outer.Type=pikepdf.Name.XObject;outer.Subtype=pikepdf.Name.Form;outer.BBox=pikepdf.Array([0,0,40,25]);outer.Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(Inner=inner))
    page.Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(Bitmap=colour,TransparentCaption=invisible,Outer=outer))
    page.Contents=pdf.make_stream(b'q 120 0 0 80 20 40 cm /Bitmap Do Q q 80 0 0 20 20 165 cm /TransparentCaption Do Q q 20 165 25 20 re W n 80 0 0 20 20 165 cm /Bitmap Do Q q 1 0 0 1 210 20 cm /Outer Do Q')
    pdf.save(seed);pdf.close()
    with fitz.open(seed)as doc:
        doc[0].insert_text((25,30),'Old prose',fontsize=10)
        doc[0].draw_line((180,100),(240,130),color=(0,0,0),width=.7)
        source=folder/'source.pdf';doc.save(source,garbage=4)
    return source

class GraphicsInkTests(unittest.TestCase):
    def test_clipped_raw_mask_ink_does_not_protect_phantom_pixels(self):
        scratch=ROOT/'tmp';scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='graphics-test-',dir=scratch)as name:
            folder=Path(name).resolve();self.assertEqual(folder.parent,scratch.resolve())
            source=fixture(folder);target=folder/'caption.pdf'
            with fitz.open(source)as doc:
                doc[0].draw_rect((20,15,140,35),color=None,fill=(1,1,1))
                doc[0].insert_text((25,30),'New caption here',fontsize=10);doc.save(target,garbage=0)
            result=audit(source,target,1)
            self.assertEqual(result['original_graphics_ink_changed_pixels'],0)
            self.assertTrue(result['original_image_and_smask_programs_and_positions_identical'])

    def test_prose_changes_do_not_trigger_graphics_mask(self):
        scratch=ROOT/'tmp';scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='graphics-test-',dir=scratch)as name:
            folder=Path(name).resolve();self.assertEqual(folder.parent,scratch.resolve())
            source=fixture(folder);target=folder/'translated.pdf'
            with fitz.open(source)as doc:
                doc[0].draw_rect((20,15,100,35),color=None,fill=(1,1,1))
                doc[0].insert_text((25,30),'New prose',fontsize=10)
                doc.save(target,garbage=4)
            result=audit(source,target,1)
            self.assertEqual(result['original_graphics_ink_changed_pixels'],0)
            self.assertTrue(result['original_image_and_smask_programs_and_positions_identical'])

    def test_overpainted_bitmap_and_vector_are_detected(self):
        scratch=ROOT/'tmp';scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='graphics-test-',dir=scratch)as name:
            folder=Path(name).resolve();self.assertEqual(folder.parent,scratch.resolve())
            source=fixture(folder)
            for label,box in [('bitmap',(94,110,108,126)),('vector',(195,104,220,124)),('nested-form-vector',(214,171,227,178))]:
                target=folder/(label+'.pdf')
                with fitz.open(source)as doc:
                    doc[0].draw_rect(box,color=None,fill=(1,1,1));doc.save(target,garbage=4)
                result=audit(source,target,1)
                self.assertGreater(result['original_graphics_ink_changed_pixels'],0,label)
                self.assertTrue(result['original_image_and_smask_programs_and_positions_identical'])

if __name__=='__main__':unittest.main()
