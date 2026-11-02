"""Real-PDF regression for identical colour images with distinct soft masks."""
from io import BytesIO
import hashlib,unittest
import pikepdf
import pymupdf as fitz
from pdf_original_image_ink import resolved_images,_planes,image_programs

def source(nested=False):
    pdf=pikepdf.Pdf.new();page=pdf.add_blank_page(page_size=(240,180));objects=[]
    for alpha in[b'\xff\x00\x00\x00',b'\x00\x00\x00\xff']:
        mask=pdf.make_stream(alpha);mask.Type=pikepdf.Name.XObject;mask.Subtype=pikepdf.Name.Image
        mask.Width=mask.Height=2;mask.ColorSpace=pikepdf.Name.DeviceGray;mask.BitsPerComponent=8
        image=pdf.make_stream(b'\x00\x00');image.Type=pikepdf.Name.XObject;image.Subtype=pikepdf.Name.Image
        image.Width=image.Height=2;image.BitsPerComponent=1;image.SMask=mask;image.Interpolate=False
        image.ColorSpace=pikepdf.Array([pikepdf.Name.Indexed,pikepdf.Name.DeviceRGB,1,pikepdf.String(b'\x00\x00\x00\xff\xff\xff')]);objects.append(image)
    page.Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(A=objects[0],B=objects[1]))
    if nested:
        form=pdf.make_stream(b'q 80 0 0 80 20 30 cm /A Do Q q 80 0 0 80 130 30 cm /B Do Q')
        form.Type=pikepdf.Name.XObject;form.Subtype=pikepdf.Name.Form;form.BBox=pikepdf.Array([0,0,240,180]);form.Matrix=pikepdf.Array([.8,0,0,.8,5,7]);form.Resources=page.Resources
        page.Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(F=form));page.Contents=pdf.make_stream(b'q 1 0 0 1 3 4 cm /F Do Q')
    else:page.Contents=pdf.make_stream(b'q 80 0 0 80 20 30 cm /A Do Q q 80 0 0 80 130 30 cm /B Do Q')
    out=BytesIO();pdf.save(out,compress_streams=False);pdf.close();return out.getvalue()

class OriginalMaskIdentity(unittest.TestCase):
    def check(self,nested):
        raw=source(nested);before=hashlib.sha256(raw).hexdigest()
        with fitz.open(stream=raw,filetype='pdf')as doc:
            items=resolved_images(doc,doc[0]);self.assertEqual(len(items),2);self.assertNotEqual(items[0]['xref'],items[1]['xref'])
            planes=[_planes(doc,image)for image in items]
            self.assertEqual(planes[0][1].tobytes(),b'\xff\x00\x00\x00');self.assertEqual(planes[1][1].tobytes(),b'\x00\x00\x00\xff')
            self.assertEqual(planes[0][0].tobytes(),planes[1][0].tobytes());self.assertNotEqual(planes[0][2],planes[1][2])
            self.assertTrue(all(i['xref_resolved_from_original_Do']for i in items))
            self.assertEqual(len(image_programs(doc,doc[0])),2)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),before)
    def test_two_equal_colour_streams_keep_distinct_original_masks(self):self.check(False)
    def test_nested_form_matrix_keeps_occurrence_and_mask_identity(self):self.check(True)

if __name__=='__main__':unittest.main()
