"""Slim a typeset Korean ISPhO paper in place: subset the stamped fonts (ispho_stamp.py embeds them whole) and
store large photographs as JPEG — a 4-page paper drops from ~6 MB to well under 1 MB.

    python3 tools/ko/ispho_slim.py pdfx/ispho/ISPhO_2023_T2_KO.pdf …"""
import io, os, sys

import pymupdf
from PIL import Image


def slim(path):
    d = pymupdf.open(path)
    d.subset_fonts()
    for x in range(1, d.xref_length()):
        if d.xref_get_key(x, 'Subtype')[1] != '/Image' or len(d.xref_stream_raw(x) or b'') < 300_000:
            continue
        if d.xref_get_key(x, 'SMask')[0] != 'null':
            continue                      # a picture with transparency stays lossless
        pix = pymupdf.Pixmap(d, x)
        if pix.n - pix.alpha >= 3 and pix.colorspace and pix.colorspace.n == 3:
            img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
        else:
            continue
        buf = io.BytesIO()
        img.save(buf, 'JPEG', quality=85, optimize=True)
        d.update_stream(x, buf.getvalue(), compress=False)
        for k, v in (('Filter', '/DCTDecode'), ('ColorSpace', '/DeviceRGB'), ('BitsPerComponent', '8'),
                     ('DecodeParms', 'null')):
            d.xref_set_key(x, k, v)
    tmp = path + '.tmp'
    d.save(tmp, garbage=4, deflate=True, clean=True)
    d.close()
    os.replace(tmp, path)


if __name__ == '__main__':
    for p in sys.argv[1:]:
        a = os.path.getsize(p)
        slim(p)
        print('%s: %.1f → %.1f MB' % (p, a / 1e6, os.path.getsize(p) / 1e6))
