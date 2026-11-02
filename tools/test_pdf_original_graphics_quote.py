"""Quote text-state survives analysis-only removal; graphics/clip pixels do too."""
from pathlib import Path
from io import BytesIO
import hashlib,subprocess,sys,tempfile,unittest
import numpy as np
import pikepdf
import pymupdf as fitz
from PIL import Image
from pdf_original_graphics_ink import graphics_control

BUILD=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-natural-spacing')
GRAPHICS=b'''q 1 0 0 1 0.123456789123 0.234567891234 cm
0.8 0.8 0.8 rg 10 10 130 90 re f Q
q 30 30 20 25 re W n 60 0 0 60 20 20 cm /Im0 Do Q
q 0 0 0 RG 0.7 w 5 5 m 160 140 l S Q
'''
TEXT=b'''BT /F1 12 Tf 16 TL 1 0 0 1 15 130 Tm
(A) Tj (B) ' 2.2 0.3 (C) " (D) Tj ET
'''

def make(path,text=b''):
    with pikepdf.Pdf.new()as pdf:
        p=pdf.add_blank_page(page_size=(180,160))
        p.Resources.Font=pikepdf.Dictionary(F1=pikepdf.Dictionary(Type=pikepdf.Name.Font,Subtype=pikepdf.Name.Type1,BaseFont=pikepdf.Name.Helvetica))
        rgb=np.zeros((16,16,3),dtype=np.uint8);rgb[:,:,0]=255;rgb[::2,:,1]=170
        image=pdf.make_stream(rgb.tobytes());image.update(pikepdf.Dictionary(Type=pikepdf.Name.XObject,Subtype=pikepdf.Name.Image,Width=16,Height=16,ColorSpace=pikepdf.Name.DeviceRGB,BitsPerComponent=8))
        p.Resources.XObject=pikepdf.Dictionary(Im0=image)
        p.Group=pikepdf.Dictionary(S=pikepdf.Name.Transparency,CS=pikepdf.Name.DeviceRGB,I=True)
        p.Contents=pdf.make_stream(GRAPHICS+text);pdf.save(path,compress_streams=False)

def pixels(path,out):
    code='import sys,pymupdf as f;d=f.open(sys.argv[1]);d[0].get_pixmap(matrix=f.Matrix(4,4),colorspace=f.csRGB,alpha=False).save(sys.argv[2])'
    subprocess.run([sys.executable,'-c',code,str(path),str(out)],check=True)
    with Image.open(out)as image:return np.array(image.convert('RGB'))

class QuoteGraphicsControl(unittest.TestCase):
    def test_quote_state_and_original_graphics_pixels(self):
        BUILD.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=BUILD)as temp:
            folder=Path(temp);source=folder/'source.pdf';background=folder/'background.pdf';control=folder/'control.pdf'
            make(source,TEXT);make(background);before=hashlib.sha256(source.read_bytes()).hexdigest()
            with fitz.open(source)as doc:control.write_bytes(graphics_control(doc,doc[0]))
            self.assertEqual(before,hashlib.sha256(source.read_bytes()).hexdigest())
            with pikepdf.open(control)as pdf:
                raw=pdf.pages[0].Contents.read_bytes();self.assertIn(b'0.123456789123 0.234567891234 cm',raw)
                quote=[i for i in pikepdf.parse_content_stream(pdf.pages[0])if str(i.operator)in["'",'"']]
                self.assertEqual(len(quote),2)
                self.assertTrue(all(bytes(i.operands[-1])==b''for i in quote))
                self.assertEqual([float(v)for v in quote[1].operands[:2]],[2.2,.3])
                self.assertTrue(pdf.pages[0].Group.I)
            self.assertTrue(np.array_equal(pixels(background,folder/'expected.png'),pixels(control,folder/'actual.png')))

    def test_text_clip_remains_rejected(self):
        with tempfile.TemporaryDirectory(dir=BUILD)as temp:
            source=Path(temp)/'clip.pdf';make(source,TEXT.replace(b'BT ',b'BT 4 Tr ',1))
            with fitz.open(source)as doc:
                with self.assertRaisesRegex(ValueError,'Text clipping'):graphics_control(doc,doc[0])

if __name__=='__main__':unittest.main()
