"""Conservative source-native equation frames from actual vector outlines.

Unlike text metric boxes these also include italic overhang. Nested SVG
transforms and source strokes are composed before measuring. This is a
read-only inventory; the SVG is never used as PDF mathematical artwork.
"""
from pathlib import Path
from collections import defaultdict
from fontTools.svgLib.path import parse_path
from fontTools.pens.boundsPen import BoundsPen
import xml.etree.ElementTree as ET
import json,hashlib,time
import pymupdf as fitz
from pdf_moved_native_ink import _transform
from pdf_native_inline_reposition import _multiply,_point,IDENTITY
from cpho2024_events import BASE,key

def measure(page,selected):
    raw=page.get_svg_image(text_as_path=True);root=ET.fromstring(raw)
    paths={};by_char=defaultdict(list);boxes={};matched=set()
    for g in selected:by_char[g['c']].append(g)
    for e in root.iter():
        if e.tag.rsplit('}',1)[-1]=='path'and e.get('id'):
            pen=BoundsPen(None);parse_path(e.get('d',''),pen);paths[e.get('id')]=pen.bounds
    def walk(e,parent=IDENTITY,style=None):
        tag=e.tag.rsplit('}',1)[-1]
        if tag=='defs':return
        m=_multiply(_transform(e.get('transform')),parent);st=dict(style or{})
        st.update(dict(v.split(':',1)for v in e.get('style','').split(';')if':'in v))
        for name in ['stroke','stroke-width']:
            if e.get(name)is not None:st[name]=e.get(name)
        if tag=='use'and e.get('data-text')in by_char:
            x,y=float(e.get('x',0)),float(e.get('y',0));o=_point(m,x,y)
            gs=[g for g in by_char[e.get('data-text')]if max(abs(g['origin'][i]-o[i])for i in [0,1])<.003]
            if gs:
                ref=e.get('{http://www.w3.org/1999/xlink}href',e.get('href','')).lstrip('#')
                if ref not in paths:raise ValueError('Source mathematical glyph has no outline definition: '+ref)
                b=paths[ref]
                if b is not None:
                    pts=[_point(m,xx+x,yy+y)for xx in[b[0],b[2]]for yy in[b[1],b[3]]]
                    border=0.
                    if st.get('stroke','none')!='none':
                        border=float(st.get('stroke-width',1))*max((m[0]**2+m[1]**2)**.5,(m[2]**2+m[3]**2)**.5)/2
                    q=[min(v[0]for v in pts)-border,min(v[1]for v in pts)-border,max(v[0]for v in pts)+border,max(v[1]for v in pts)+border]
                    for g in gs:
                        k=str(key(g));old=boxes.get(k,q);boxes[k]=[min(old[0],q[0]),min(old[1],q[1]),max(old[2],q[2]),max(old[3],q[3])]
                for g in gs:matched.add(str(key(g)))
        for c in e:walk(c,m,st)
    walk(root)
    missing=[g for g in selected if str(key(g))not in matched]
    if missing:raise ValueError('Unmatched source-native outline signatures: '+repr(missing[:3]))
    return dict(svg_sha256=hashlib.sha256(raw.encode()).hexdigest(),glyph_count=len(selected),matched_glyph_keys=len(matched),boxes=boxes,
                source_outlines_only_for_measurement=True,no_math_artwork_replacement=True)

if __name__=='__main__':
    from pdf_memory_gate import page_worker
    source=BASE/'source/CPhO_2024_Chinese_original.pdf'
    for n in range(1,6):
        d=json.loads((BASE/f'authoring/T/page{n:02}.events.json').read_text('utf8'))
        gs=[g for p in d['native_parts']for g in p['glyphs']]
        with page_worker():
            with fitz.open(source)as doc:report=measure(doc[n-1],gs)
        (BASE/f'inspection/page{n:02}-native-ink-bounds.json').write_text(json.dumps(report,ensure_ascii=False,indent=1),'utf8')
        print(n,report['glyph_count'],report['matched_glyph_keys'],flush=True);time.sleep(.6)
