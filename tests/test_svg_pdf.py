"""Check the rendered PDF ink, including dash continuity around a corner."""
from pathlib import Path
import sys,unittest
import pymupdf as fitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from svg_pdf import explicit_strokes

def render(body,normalise=True):
    source='<svg xmlns="http://www.w3.org/2000/svg" width="120" height="110">'+body+'</svg>'
    if normalise:source=explicit_strokes(source)
    image=fitz.open(stream=source.encode(),filetype='svg')
    pdf=fitz.open(stream=image.convert_to_pdf(),filetype='pdf')
    return pdf[0].get_pixmap(colorspace=fitz.csGRAY,alpha=False)

class DashedPDFInk(unittest.TestCase):
    def test_dash_gaps_are_white_in_pdf(self):
        pix=render('<path d="M10 20 L110 20" fill="none" stroke="black" stroke-width="2" stroke-dasharray="10 5"/>')
        for x in [15,30,45,60]:self.assertLess(pix.pixel(x,20)[0],50)
        for x in [22,37,52,67]:self.assertGreater(pix.pixel(x,20)[0],240)

    def test_phase_continues_around_polyline_corner(self):
        pix=render('<polyline points="10,20 50,20 50,90" fill="none" stroke="black" stroke-width="2" stroke-dasharray="10 5"/>')
        self.assertGreater(pix.pixel(50,22)[0],240)
        self.assertLess(pix.pixel(50,27)[0],50)

    def test_solid_curve_ink_is_unchanged(self):
        body='<path d="M10 70 C30 10 80 10 110 70" fill="none" stroke="black" stroke-width="2"/>'
        self.assertEqual(render(body).samples,render(body,False).samples)

if __name__=='__main__':unittest.main()
