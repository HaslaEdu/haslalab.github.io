"""Real PDF tests: whole scanned fraction, masks, original clip and figures."""
from pathlib import Path
import unittest
import pikepdf
import pymupdf as fitz
import numpy as np
from PIL import Image,ImageDraw
from pdf_original_raster_math import replay,program_sha

BASE=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/raster-math-regressions')

class RasterMathTests(unittest.TestCase):
    def source(self,name,extra_vector=False):
        path=BASE/(name+'.pdf');im=Image.new('RGB',(400,240),'white');draw=ImageDraw.Draw(im)
        for box in[(53,66,59,81),(69,66,75,81),(84,74,95,76),(103,66,109,81),(62,96,68,111),(76,96,82,111)]:draw.rectangle(box,fill='black')
        draw.line([(48,88),(127,88)],fill='black',width=2)
        draw.rectangle([330,140,380,200],outline='black',width=2)
        with pikepdf.Pdf.new()as pdf:
            page=pdf.add_blank_page(page_size=(400,240));image=pdf.make_stream(im.tobytes())
            for k,v in dict(Type=pikepdf.Name.XObject,Subtype=pikepdf.Name.Image,Width=400,Height=240,ColorSpace=pikepdf.Name.DeviceRGB,BitsPerComponent=8).items():image['/'+k]=v
            mask=pdf.make_stream(bytes([255])*(400*240))
            for k,v in dict(Type=pikepdf.Name.XObject,Subtype=pikepdf.Name.Image,Width=400,Height=240,ColorSpace=pikepdf.Name.DeviceGray,BitsPerComponent=8).items():mask['/'+k]=v
            image.SMask=mask;page.Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(Scan=image))
            page.obj.Group=pikepdf.Dictionary(S=pikepdf.Name.Transparency,CS=pikepdf.Name.DeviceRGB)
            raw=b'q 0 0 400 240 re W n 400 0 0 240 0 0 cm /Scan Do Q\n'
            if extra_vector:raw+=b'q 0 g 90 143 20 3 re f Q\n'
            page.Contents=pdf.make_stream(raw);pdf.save(path,compress_streams=False)
        return path

    def base(self,source,name,tamper=False):
        target=BASE/(name+'.pdf')
        with pikepdf.open(source)as pdf:
            page=pdf.pages[0];page.Contents=pikepdf.Array([page.Contents,pdf.make_stream(b'q 1 g 40 120 100 60 re f Q\n')])
            if tamper:page.Resources.XObject.Scan.SMask.write(bytes([0])*(400*240))
            pdf.save(target,compress_streams=False)
        return target

    def atom(self,**extra):
        return dict(id='whole-fraction',image_path=[5],rect=[40,60,140,120],dx=160,reviewed=True,reason='Entire original numerator/denominator/subscripts/fraction rule, one exact bitmap atom.',**extra)

    def pixels(self,path):
        with fitz.open(path)as d:
            p=d[0].get_pixmap(matrix=fitz.Matrix(4,4),alpha=False,colorspace=fitz.csRGB)
            return np.frombuffer(p.samples,dtype=np.uint8).reshape(p.height,p.width,3).copy()

    def test_whole_fraction_moves_exactly_and_other_figure_is_unchanged(self):
        s=self.source('whole');base=self.base(s,'whole-base');raw,qa=replay(s,1,base,[self.atom()]);out=BASE/'whole-moved.pdf';out.write_bytes(raw)
        before=self.pixels(s);expected=before.copy();expected[240:480,160:560]=255;expected[240:480,800:1200]=before[240:480,160:560]
        self.assertEqual(int(np.any(expected!=self.pixels(out),axis=2).sum()),0)
        self.assertEqual(qa['atoms'][0]['source_recipe_roundtrip']['changed_pixels'],0)
        self.assertTrue(qa['original_encoded_image_mask_palette_icc_programs_unchanged'])
        with pikepdf.open(s)as original,pikepdf.open(out)as final:
            source_program=program_sha(original.pages[0].Resources.XObject.Scan)
            copied=final.pages[0].Resources.XObject.OriginalRasterMath1.Resources.XObject.Scan
            self.assertEqual(source_program,program_sha(copied))

    def test_original_mask_tamper_in_base_is_rejected(self):
        s=self.source('mask');base=self.base(s,'mask-base',tamper=True)
        with self.assertRaisesRegex(ValueError,'Base changed'):replay(s,1,base,[self.atom()])

    def test_actual_source_vector_over_math_rejects_bitmap_only_replay(self):
        s=self.source('vector',extra_vector=True);base=self.base(s,'vector-base')
        with self.assertRaisesRegex(ValueError,'differs from actual source'):replay(s,1,base,[self.atom()])

    def test_original_clip_escape_is_rejected(self):
        s=self.source('escape');base=self.base(s,'escape-base');atom=self.atom();atom['rect']=[-1,60,140,120]
        with self.assertRaisesRegex(ValueError,'escapes original image/clip'):replay(s,1,base,[atom])

if __name__=='__main__':
    BASE.mkdir(parents=True,exist_ok=True)
    from pdf_memory_gate import page_worker
    with page_worker():unittest.main()
