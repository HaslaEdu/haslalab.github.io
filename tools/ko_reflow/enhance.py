# -*- coding: utf-8 -*-
"""Make a sharper working copy of an original whose pages (or figures) are low-resolution scans.

usage: python -I enhance.py ORIGINAL.pdf OUT.pdf [MAX_DPI=200]

Every raster image drawn at less than MAX_DPI is replaced in the copy by a cleaned version:
upscaled (Lanczos) to about 3x / up to 330 dpi, paper tone flattened to white, mildly sharpened and levelled.
Near-grey images are stored as grey JPEG, colour ones (photos, red headers) keep their colour. Vector content,
text layer, page geometry and image placement are untouched, so build.py can stamp from the copy with the
same clip coordinates as from the original.
"""
import sys
import numpy as np, cv2, pymupdf


def placed_dpis(doc):
    best = {}
    for page in doc:
        for info in page.get_image_info(xrefs=True):
            r = pymupdf.Rect(info['bbox'])
            if info['xref'] and r.width > 2:
                d = info['width'] / (r.width / 72)
                best[info['xref']] = min(best.get(info['xref'], d), d)
    return best


def clean(arr, grey, scale):
    def one(ch):
        up = cv2.resize(ch, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
        small = cv2.resize(ch, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
        bg = cv2.resize(cv2.medianBlur(small, 9), (up.shape[1], up.shape[0]), interpolation=cv2.INTER_LINEAR)
        norm = cv2.divide(up, np.maximum(bg, 1), scale=255)
        bl = cv2.GaussianBlur(norm, (0, 0), 0.9 * scale / 3 + 0.4)
        sh = cv2.addWeighted(norm, 1.6, bl, -0.6, 0)
        lut = np.clip((np.arange(256) - 70) * 255 / (240 - 70), 0, 255).astype(np.uint8)
        return cv2.LUT(sh, lut)
    if grey:
        return one(arr)
    up = cv2.resize(arr, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
    bl = cv2.GaussianBlur(up, (0, 0), 1.0)
    return cv2.addWeighted(up, 1.5, bl, -0.5, 0)


def main(src, out, max_dpi=200):
    max_dpi = float(max_dpi)
    doc = pymupdf.open(src)
    done = set(); n = 0
    dpis = placed_dpis(doc)
    for page in doc:
        for img in page.get_images(full=True):
            xref, smask = img[0], img[1]
            if xref in done or smask:
                continue
            done.add(xref)
            dpi = dpis.get(xref)
            if not dpi or dpi >= max_dpi:
                continue
            pix = pymupdf.Pixmap(doc, xref)
            if pix.w < 64 or pix.h < 64:
                continue
            if pix.colorspace is None or pix.n - pix.alpha not in (1, 3):
                pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            if pix.alpha:
                pix = pymupdf.Pixmap(pix, 0)
            a = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)
            if pix.n == 1:
                g, grey = a[:, :, 0], True
            else:
                spread = (a.max(axis=2).astype(int) - a.min(axis=2)).mean()
                grey = spread < 12
                g = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY) if grey else a
            scale = max(1.0, min(3.0, 330 / dpi))
            e = clean(np.ascontiguousarray(g), grey, scale)
            ok, buf = cv2.imencode('.jpg', e if grey else cv2.cvtColor(e, cv2.COLOR_RGB2BGR),
                                   [cv2.IMWRITE_JPEG_QUALITY, 88])
            page.replace_image(xref, stream=buf.tobytes())
            n += 1
    doc.save(out, garbage=4, deflate=True)
    print(out, n, 'images enhanced')


if __name__ == '__main__':
    main(*sys.argv[1:])
