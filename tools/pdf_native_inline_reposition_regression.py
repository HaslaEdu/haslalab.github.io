"""Independent source/control/moved raster regressions for native inline dx.

Writes only to the authorized D: build directory. No published PDF is changed.
"""
from io import BytesIO
from pathlib import Path
import json
import os

os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('OMP_NUM_THREADS','1')
import numpy as np
import pikepdf
import pymupdf as fitz
from fontTools.ttLib import TTFont

from pdf_native_inline_reposition import reposition_inline, inspect_inline_groups, _traces

OUT=Path('D:/CodexBuilds/Hasla-original-style-20261031/native-inline-prototype')
FONT=Path('C:/Windows/Fonts/times.ttf')


def fixture():
    d=fitz.open();p=d.new_page(width=600,height=500)
    p.insert_text((30,40),'ABCD x+y 12',fontfile=str(FONT),fontname='F')
    pdf=pikepdf.Pdf.open(BytesIO(d.tobytes()));page=pdf.pages[0];font=page.Resources.Font.F
    tt=TTFont(FONT);cm=tt.getBestCmap();order=tt.getGlyphOrder();upem=tt['head'].unitsPerEm
    def cid(text):return ''.join('%04x'%order.index(cm[ord(c)]) for c in text)
    widths=[]
    for code in range(256):
        try:char=bytes([code]).decode('cp1252')
        except UnicodeDecodeError:char='?'
        widths.append(tt['hmtx'].metrics[cm.get(ord(char),'.notdef')][0]*1000/upem)
    win=pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.Font,Subtype=pikepdf.Name.TrueType,
        BaseFont=pikepdf.Name('/TimesNewRomanPSMT'),Encoding=pikepdf.Name.WinAnsiEncoding,
        FirstChar=0,LastChar=255,Widths=pikepdf.Array(widths),
        FontDescriptor=font.DescendantFonts[0].FontDescriptor))
    page.Resources.Font.Win=win
    fraction=pdf.make_stream((
        'q 0 0 0 RG .5 w 0 0 m 18 0 l S '
        'BT /F 12 Tf 1 0 0 1 5 4 Tm <'+cid('x')+'> Tj '
        '1 0 0 1 5 -13 Tm <'+cid('y')+'> Tj ET Q').encode('ascii'))
    fraction.Type=pikepdf.Name.XObject;fraction.Subtype=pikepdf.Name.Form
    fraction.BBox=pikepdf.Array([-2,-18,24,20]);fraction.Resources=pikepdf.Dictionary(Font=page.Resources.Font)
    parent=pdf.make_stream(('q 1.1 0 0 1.2 0 0 cm /Frac Do Q '
                            'BT /F 12 Tf 1 0 0 1 70 0 Tm <'+cid('D')+'> Tj ET').encode('ascii'))
    parent.Type=pikepdf.Name.XObject;parent.Subtype=pikepdf.Name.Form
    parent.BBox=pikepdf.Array([-3,-24,100,30])
    parent.Resources=pikepdf.Dictionary(Font=page.Resources.Font,XObject=pikepdf.Dictionary(Frac=fraction))
    page.Resources.XObject=pikepdf.Dictionary(Parent=parent)
    contents=(
        'q 1.25 0 0 .9 8 5 cm BT /F 1 Tf .08 Tc 2 Tw 82 Tz '
        '12 0 0 12 20 440 Tm <'+cid('ABCD')+'> Tj ET Q\n'
        'q BT /Win 13 Tf .7 Tc 2.3 Tw 75 Tz 1.2 0 0 1 40 340 Tm (A BCD) Tj ET Q\n'
        'q 0 0 1 rg 1 0 0 RG .25 w BT /F 12 Tf 2 Tr 1 0 0 1 40 270 Tm <'+cid('ABCD')+'> Tj ET Q\n'
        'q 1 0 0 1 60 190 cm /Parent Do Q\n'
        'q 1 0 0 1 300 190 cm /Parent Do Q\n'
        'q 0 0 0 RG .5 w 40 85 m 70 85 l S '
        'BT /F 12 Tf 1 0 0 1 50 90 Tm <'+cid('x')+'> Tj '
        '1 0 0 1 50 70 Tm <'+cid('y')+'> Tj ET Q\n'
        'q 100 44 30 25 re W n BT /Win 12 Tf 1 0 0 1 105 50 Tm (B) Tj ET Q\n'
        'q 0 0 600 500 re W* n BT /Win 12 Tf 1 0 0 1 300 50 Tm (AB) Tj ET Q\n'
        'q 190 45 50 25 re W n BT /Win 12 Tf 1 0 0 1 200 50 Tm (AB) Tj ET Q\n'
        'q 1 1 1 rg 35 115 530 30 re f Q '
        'BT /F 12 Tf 1 0 0 1 400 130 Tm <'+cid('B')+'> Tj ET\n'
    )
    page.Contents=pdf.make_stream(contents.encode('ascii'))
    out=BytesIO();pdf.save(out,compress_streams=False);return out.getvalue()


def render(blob):
    d=fitz.open(stream=blob,filetype='pdf');p=d[0].get_pixmap(matrix=fitz.Matrix(4,4),alpha=False)
    a=np.frombuffer(p.samples,dtype=np.uint8).reshape(p.height,p.width,p.n).copy();d.close();return a


def changed_outside(a,b,rects):
    changed=np.any(a!=b,axis=2)
    for r in rects:
        x0,y0,x1,y1=r;changed[max(0,int(y0*4)):int(y1*4+1),max(0,int(x0*4)):int(x1*4+1)]=False
    return int(changed.sum())


def main():
    OUT.mkdir(parents=True,exist_ok=True);source=fixture();(OUT/'synthetic-source.pdf').write_bytes(source)
    doc=fitz.open(stream=source,filetype='pdf');trace=_traces(doc[0]);report=[]
    control,q=reposition_inline(source,1)
    q['raster_changed_pixels']=int(np.any(render(source)!=render(control),axis=2).sum())
    assert q['passed'] and q['raster_changed_pixels']==0
    report.append(dict(case='no-op control: exact source pixels',qa=q))
    # Tf=1 + Tm=12 + nonunit CTM/Tz/Tc; WinAnsi additionally exercises Tw.
    selections=[('CID Tf1 Tm12 CTM Tz Tc',trace[1],5.),
                ('WinAnsi Tc Tw Tz',next(c for c in trace if c['c']=='B' and 150<c['origin'][1]<170),-4.),
                ('Tr2 original fill and stroke',next(c for c in trace if c['c']=='C' and 220<c['origin'][1]<240),6.)]
    for name,g,dx in selections:
        output,q=reposition_inline(source,1,shifts=[dict(glyphs=[g],dx=dx)])
        r=fitz.Rect(g['bbox']);r|=fitz.Rect(r.x0+dx,r.y0,r.x1+dx,r.y1);r+=(-2,-2,2,2)
        q['changed_pixels_outside_moved_glyph']=changed_outside(render(source),render(output),[r])
        assert q['passed'] and q['changed_pixels_outside_moved_glyph']==0
        report.append(dict(case=name,qa=q));(OUT/(name.split()[0]+'-moved.pdf')).write_bytes(output)
        output,q=reposition_inline(source,1,shifts=[dict(glyphs=[g],dx=dx)],text_shift_mode='ctm')
        q['changed_pixels_outside_moved_glyph']=changed_outside(render(source),render(output),[r])
        assert q['passed'] and q['changed_pixels_outside_moved_glyph']==0
        report.append(dict(case=name+' using native graphics translation',qa=q))
    groups=inspect_inline_groups(source,1)['forms']
    target=next(g for g in groups if len(g['path'])==2 and min(c['origin'][0] for c in g['glyphs'])<100)
    moved,q=reposition_inline(source,1,shifts=[dict(glyphs=target['glyphs'],form_path=target['path'],dx=8)])
    a,b=render(source),render(moved)
    q['changed_pixels_outside_first_fraction']=changed_outside(a,b,[[55,283,100,335]])
    # The whole 1.1x/1.2y native fraction, bar included, must be an exact
    # 32-pixel translate. The second use of its shared ancestor stays intact.
    q['translated_fraction_crop_pixel_differences']=int(np.any(a[1140:1320,220:320]!=b[1140:1320,252:352],axis=2).sum())
    assert q['passed'] and q['private_form_ancestor_copies']==1
    assert q['changed_pixels_outside_first_fraction']==0 and q['translated_fraction_crop_pixel_differences']==0
    report.append(dict(case='nested shared Form: fraction glyphs and bar',qa=q));(OUT/'nested-form-moved.pdf').write_bytes(moved)
    erased=[trace[0]];moved,q=reposition_inline(source,1,erased_glyphs=erased,
        shifts=[dict(glyphs=[trace[2]],dx=3)])
    assert q['passed'] and q['erased_glyphs']==1
    report.append(dict(case='simultaneous prose CID suppression and native shift',qa=q))
    # A bare fraction bar and its glyph may never be split by this API.
    unsafe=[c for c in trace if c['origin'][1]>400 and c['origin'][0]<80]
    try:reposition_inline(source,1,shifts=[dict(glyphs=unsafe,dx=4)])
    except ValueError as e:
        # The line lies below the numerator ink but inside its text bbox.
        assert 'vector' in str(e);report.append(dict(case='bare vector fraction rejected',passed=True,error=str(e)))
    else:raise AssertionError('Bare vector fraction was silently split')
    vector=next(v for v in inspect_inline_groups(source,1)['vector_paths'] if abs(v['rect'][1]-415)<.01)
    output,q=reposition_inline(source,1,shifts=[dict(glyphs=unsafe,dx=8,vector_paths=[vector])])
    a,b=render(source),render(output)
    q['translated_bare_fraction_crop_pixel_differences']=int(np.any(a[1580:1750,140:300]!=b[1580:1750,172:332],axis=2).sum())
    assert q['passed'] and q['shifted_reviewed_vector_paths']==1
    assert q['translated_bare_fraction_crop_pixel_differences']==0
    report.append(dict(case='reviewed bare fraction path: exact native bytes and translated ink',qa=q))
    g=next(c for c in trace if c['c']=='B' and 100<c['origin'][0]<110)
    output,q=reposition_inline(source,1,shifts=[dict(glyphs=[g],dx=40)])
    a,b=render(source),render(output)
    q['translated_clipped_glyph_crop_pixel_differences']=int(np.any(a[1720:1850,390:550]!=b[1720:1850,550:710],axis=2).sum())
    assert q['passed'] and q['shifted_atomic_clip_groups']==1
    assert q['translated_clipped_glyph_crop_pixel_differences']==0
    report.append(dict(case='tight clipped native text moves clip and actual ink atomically',qa=q))
    (OUT/'atomic-clip-moved.pdf').write_bytes(output)
    g=next(c for c in trace if c['c']=='B' and 300<c['origin'][0]<320)
    output,q=reposition_inline(source,1,shifts=[dict(glyphs=[g],dx=4)])
    assert q['passed'] and q['shifted_atomic_clip_groups']==0
    report.append(dict(case='partial text move remains inside full-page rectangular clip',qa=q))
    g=next(c for c in trace if c['c']=='B' and 200<c['origin'][0]<220)
    try:reposition_inline(source,1,shifts=[dict(glyphs=[g],dx=100)])
    except ValueError as e:
        assert 'clip' in str(e);report.append(dict(case='partial tight-clip escape rejected',passed=True,error=str(e)))
    else:raise AssertionError('A moved glyph escaped its unmoved clip')
    g=next(c for c in trace if c['c']=='B' and c['origin'][0]>390)
    try:reposition_inline(source,1,shifts=[dict(glyphs=[g],dx=4)])
    except ValueError as e:assert 'vector' in str(e)
    else:raise AssertionError('Unreviewed white geometry was silently ignored')
    output,q=reposition_inline(source,1,shifts=[dict(glyphs=[g],dx=4)],allow_white_background_panels=True)
    assert q['passed'] and q['unchanged_white_background_panels_ignored']==1
    report.append(dict(case='explicit opaque wide white background profile; black bars still protected',qa=q))
    # A later translated prose space may share the exact same native key as
    # an older space inside a moved tight clip. Only the source occurrence
    # belonging to that original q/clip may acquire the group's dx.
    with pikepdf.open(BytesIO(source)) as duplicate:
        p=duplicate.pages[0]
        first=b'q 190 120 60 30 re W n BT /Win 12 Tf 1 0 0 1 200 130 Tm (A B) Tj ET Q '
        p.Contents=duplicate.make_stream(first)
        stream=BytesIO();duplicate.save(stream,compress_streams=False)
        with fitz.open(stream=stream.getvalue(),filetype='pdf') as d:
            space_x=next(g['origin'][0] for g in _traces(d[0]) if g['c']==' ')
        p.Contents=duplicate.make_stream(first+('BT /Win 12 Tf 1 0 0 1 %.12g 130 Tm ( ) Tj ET'%space_x).encode('ascii'))
        stream=BytesIO();duplicate.save(stream,compress_streams=False);duplicate_raw=stream.getvalue()
    with fitz.open(stream=duplicate_raw,filetype='pdf') as d:
        selected=[g for g in _traces(d[0]) if g['c'].strip()]
    output,q=reposition_inline(duplicate_raw,1,shifts=[dict(glyphs=selected,dx=8)])
    assert q['passed'] and q['shifted_atomic_clip_groups']==1
    assert len(q['atomic_nonpainting_space_occurrence_shifts'])==1
    with fitz.open(stream=output,filetype='pdf') as d:
        spaces=[g['origin'][0] for g in _traces(d[0]) if g['c']==' ']
    assert len(spaces)==2 and abs((max(spaces)-min(spaces))-8)<.001,spaces
    report.append(dict(case='exact duplicate-space keys use original clip occurrence membership',qa=q))
    with pikepdf.open(BytesIO(source))as nested:
        p=nested.pages[0]
        p.Contents=nested.make_stream(b'q 190 130 60 8 re W n q 190 130 60 8 re W n BT /Win 12 Tf 1 0 0 1 200 130 Tm (g) Tj ET Q BT /Win 12 Tf 1 0 0 1 235 130 Tm (C) Tj ET Q')
        stream=BytesIO();nested.save(stream,compress_streams=False);clipped=stream.getvalue()
    with fitz.open(stream=clipped,filetype='pdf')as d:
        g=next(c for c in _traces(d[0])if c['c']=='g')
    moved,q=reposition_inline(clipped,1,shifts=[dict(glyphs=[g],dx=8)])
    a,b=render(clipped),render(moved)
    delta=int(np.any(a[1430:1510,780:860]!=b[1430:1510,812:892],axis=2).sum())
    assert q['passed']and q['shifted_atomic_clip_groups']==1 and delta==0
    assert changed_outside(a,b,[[195,355,230,380]])==0
    report.append(dict(case='native own-row clip preserves inherited vertical crop inside stationary ancestor',qa=q,translated_actual_crop_pixel_differences=delta))
    (OUT/'regression.json').write_text(json.dumps(dict(passed=True,cases=report),indent=2),encoding='utf8')
    print(json.dumps(dict(passed=True,cases=len(report),report=str(OUT/'regression.json'))))


if __name__=='__main__':main()
