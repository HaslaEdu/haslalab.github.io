# -*- coding: utf-8 -*-
"""Typeset a Korean edition (sources in tools/ko_reflow/<comp>/<year>.html) on the original's page geometry, then stamp the
original's own vector figures/logo into the placeholders.

usage: python -I build.py SRC.html ORIGINAL.pdf OUT.pdf
SRC.html: <meta name="page" content="W,H"> (pt) and page divs; figures are
  <span class="fig" data-page="1" data-clip="x0,y0,x1,y1" [data-scale="1"]></span>
Elements with class "ov" (e.g. a Korean label on a white box) are drawn on top of the stamped figures.
"""
import os, re, subprocess, sys, tempfile, pathlib
import pymupdf
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import slant

KIT = pathlib.Path(__file__).resolve().parent
VENDOR = KIT.parents[1] / "vendor"   # repo vendor/katex
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

CSS = """
@font-face{font-family:CM;src:url(KITURL/katex/fonts/KaTeX_Main-Regular.woff2)}
@font-face{font-family:CM;font-weight:bold;src:url(KITURL/katex/fonts/KaTeX_Main-Bold.woff2)}
@font-face{font-family:CM;font-style:italic;src:url(KITURL/katex/fonts/KaTeX_Main-Italic.woff2)}
@font-face{font-family:CM;font-style:italic;font-weight:bold;src:url(KITURL/katex/fonts/KaTeX_Main-BoldItalic.woff2)}
@font-face{font-family:KB;src:url(file:///C:/Windows/Fonts/HANBatang.ttf);size-adjust:94%}
@font-face{font-family:KB;font-weight:bold;src:url(file:///C:/Windows/Fonts/HANBatangB.ttf);size-adjust:94%}
@font-face{font-family:KG;src:url(file:///C:/Windows/Fonts/malgun.ttf)}
@font-face{font-family:KG;font-weight:bold;src:url(file:///C:/Windows/Fonts/malgunbd.ttf)}
@font-face{font-family:KB;font-style:italic;src:url(SLANT_HANBatang);size-adjust:94%}
@font-face{font-family:KB;font-style:italic;font-weight:bold;src:url(SLANT_HANBatangB);size-adjust:94%}
@font-face{font-family:KG;font-style:italic;src:url(SLANT_malgun)}
@font-face{font-family:KG;font-style:italic;font-weight:bold;src:url(SLANT_malgunbd)}
@page{size:PWpt PHpt;margin:0}
*{box-sizing:border-box}
html,body{margin:0;padding:0;-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{font-family:CM,KB,serif;font-size:10.1pt;line-height:12.7pt;color:#000;word-break:normal;line-break:strict;
     text-rendering:geometricPrecision;font-kerning:normal}
.page{width:PWpt;height:PHpt;position:relative;overflow:hidden;page-break-after:always;break-after:page}
.page:last-child{page-break-after:auto;break-after:auto}
p{margin:0;text-align:justify;text-indent:12pt}
p.ni{text-indent:0}
.fig{display:inline-block;vertical-align:top}
.katex{font-size:1em!important}
b,strong{font-weight:bold}
sup{font-size:70%;line-height:0;vertical-align:0.45em}
sub{font-size:70%;line-height:0;vertical-align:-0.2em}
"""


def prepare(src, orig):
    html = pathlib.Path(src).read_text(encoding='utf-8')
    od = pymupdf.open(orig)
    for _p in od:  # clip coordinates are the visible (rotated) page's
        if _p.rotation:
            _p.remove_rotation()
    m = re.search(r'<meta name="page" content="([\d.]+),([\d.]+)"', html)
    pw, ph = (m.group(1), m.group(2)) if m else (str(od[0].rect.width), str(od[0].rect.height))
    figs = []

    def fig(mo):
        attrs = dict(re.findall(r'data-(\w+)="([^"]*)"', mo.group(0)))
        x0, y0, x1, y1 = map(float, attrs['clip'].split(','))
        sc = float(attrs.get('scale', 1))
        i = len(figs)
        figs.append((int(attrs.get('page', 1)) - 1, pymupdf.Rect(x0, y0, x1, y1), sc, attrs.get('srcpage')))
        extra = mo.group(1) or ''
        return (f'<span class="fig{extra}" style="width:{(x1-x0)*sc:.2f}pt;height:{(y1-y0)*sc:.2f}pt;'
                f'background:rgb(254,{i % 250 + 1},{40 + i // 250})"></span>')

    html = re.sub(r'<span class="fig([^"]*)"[^>]*></span>', fig, html)
    kiturl = VENDOR.as_uri()
    html = html.replace('KITURL', kiturl)
    css = CSS.replace('KITURL', kiturl).replace('PW', pw).replace('PH', ph)
    for face in ('HANBatangB', 'HANBatang', 'malgunbd', 'malgun'):   # Hangul italics: a gentle slant, not Chrome's shear
        css = css.replace(f'SLANT_{face})', slant.slanted(f'C:/Windows/Fonts/{face}.ttf').as_uri() + ')')
    head = (f'<meta charset="utf-8"><link rel="stylesheet" href="{kiturl}/katex/katex.min.css">'
            f'<style>{css}</style>')
    tail = (f'<script src="{kiturl}/katex/katex.min.js"></script>'
            f'<script src="{kiturl}/katex/contrib/auto-render.min.js"></script>'
            '<script>renderMathInElement(document.body,{delimiters:[{left:"$",right:"$",display:false},'
            '{left:"\\\\[",right:"\\\\]",display:true}],throwOnError:true});</script>')
    html = html.replace('<head>', '<head>' + head, 1).replace('</body>', tail + '</body>', 1)
    return html, od, figs


def print_pdf(html):
    tmpdir = pathlib.Path(tempfile.mkdtemp(dir=KIT / 'tmp' if (KIT / 'tmp').exists() else None))
    hp = tmpdir / 'page.html'
    hp.write_text(html, encoding='utf-8')
    raw = tmpdir / 'raw.pdf'
    try:
        subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-pdf-header-footer',
                        '--allow-file-access-from-files', '--virtual-time-budget=8000',
                        '--disk-cache-size=1', '--disable-extensions', '--no-first-run',
                        f'--user-data-dir={tmpdir / "profile"}',
                        f'--print-to-pdf={raw}', hp.as_uri()], check=True, capture_output=True, timeout=180, env=dict(os.environ, TEMP=str(tmpdir), TMP=str(tmpdir)))
        return pymupdf.open(stream=raw.read_bytes(), filetype='pdf')
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def main(src, orig, out):
    html, od, figs = prepare(src, orig)
    doc = print_pdf(html)
    over = None
    if re.search(r'class="[^"]*\bov\b', html):
        # labels that must sit ON a stamp (covering the source's own label): printed alone, laid over the stamps
        over = print_pdf(html.replace('</head>', '<style>body *{visibility:hidden!important}'
                                      '.ov,.ov *{visibility:visible!important}</style></head>', 1))
        doc = print_pdf(html.replace('</head>', '<style>.ov{visibility:hidden!important}</style></head>', 1))
    want = len(re.findall(r'class="page"', html))
    if len(doc) != want:
        sys.exit(f'page overflow: printed {len(doc)} pages, expected {want}')
    # locate placeholders by their fill colour
    found = {}
    for pn, pg in enumerate(doc):
        for d in pg.get_drawings():
            f = d.get('fill')
            if f and abs(f[0] - 254 / 255) < 0.003 and f[2] > 39.5 / 255 and f[1] > 0.5 / 255:
                idx = (round(f[2] * 255) - 40) * 250 + round(f[1] * 255) - 1
                found[idx] = (pn, pymupdf.Rect(d['rect']))
    for i, (opn, clip, sc, srcpage) in enumerate(figs):
        if i not in found:
            sys.exit(f'figure {i} placeholder not found')
        pn, r = found[i]
        # Chrome snaps the placeholder to whole device pixels; keep its position but the stamp's exact size
        r = pymupdf.Rect(r.x0, r.y0, r.x0 + clip.width * sc, r.y0 + clip.height * sc)
        pg = doc[pn]
        pg.draw_rect(r + (-0.8, -0.8, 0.8, 0.8), color=None, fill=(1, 1, 1), overlay=True)
        pg.show_pdf_page(r, od, int(srcpage) - 1 if srcpage else opn, clip=clip, overlay=True)
    if over is not None:
        if len(over) != len(doc):
            sys.exit('overlay pass printed a different page count')
        for pn, pg in enumerate(doc):
            if over[pn].get_text('text').strip() or over[pn].get_drawings():
                pg.show_pdf_page(pg.rect, over, pn, overlay=True)
    doc.set_metadata({'title': pathlib.Path(out).stem, 'producer': 'HaslaLab', 'creator': 'HaslaLab'})
    doc.save(out, garbage=4, deflate=True)
    print(out, len(doc), 'pages', len(figs), 'figures')


if __name__ == '__main__':
    main(*sys.argv[1:4])
