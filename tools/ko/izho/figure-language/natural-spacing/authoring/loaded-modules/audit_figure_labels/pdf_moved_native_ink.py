"""Independent actual-ink check for horizontally moved original PDF glyphs.

Reference outlines come from the INPUT page, not the possibly clipped output.
Nested SVG transforms are composed before selecting source glyph signatures.
Original font/GID/size/paint identity is also checked against the final page.
"""
from collections import Counter,defaultdict
from copy import deepcopy
from pathlib import Path
import hashlib,math,re,xml.etree.ElementTree as ET
import numpy as np
import pymupdf as fitz
from pdf_native_inline_reposition import _traces,_multiply,IDENTITY,_point
from pdf_original_text_ops import glyph_key,family_name

SVG='http://www.w3.org/2000/svg'
XLINK='http://www.w3.org/1999/xlink'
ET.register_namespace('',SVG);ET.register_namespace('xlink',XLINK)


def _transform(text):
    result=IDENTITY
    for op,body in re.findall(r'([A-Za-z]+)\s*\(([^)]*)\)',text or ''):
        v=[float(s) for s in re.findall(r'[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?',body)]
        if op=='matrix' and len(v)==6:m=tuple(v)
        elif op=='translate' and len(v) in(1,2):m=(1,0,0,1,v[0],v[1] if len(v)>1 else 0)
        elif op=='scale' and len(v) in(1,2):m=(v[0],0,0,v[-1],0,0)
        elif op=='rotate' and len(v) in(1,3):
            a=math.radians(v[0]);m=(math.cos(a),math.sin(a),-math.sin(a),math.cos(a),0,0)
            if len(v)==3:m=_multiply(_multiply((1,0,0,1,-v[1],-v[2]),m),(1,0,0,1,v[1],v[2]))
        elif op in('skewX','skewY') and len(v)==1:
            t=math.tan(math.radians(v[0]));m=(1,0,t,1,0,0) if op=='skewX' else(1,t,0,1,0,0)
        else:raise ValueError('Unsupported source SVG transformation: '+op)
        result=_multiply(m,result)
    return result


def _key(g):
    return glyph_key(dict(g,font=family_name(g['font'])))


def _sig(g):return(g['c'],round(g['origin'][0],3),round(g['origin'][1],3))


def source_outline_reference(page,glyphs,offsets=None,scale=4):
    """Return (dark reference mask, source signature/transform audit).

    Source glyphs must be exact input c/font/size/origin dictionaries. Each
    expected physical glyph signature must match an input SVG use; missing
    or fully clipped uses explicitly fail. Source Tr2 can emit two uses for
    one glyph; both preserve their own original fill/stroke geometry.
    """
    if page.rotation:raise ValueError('Rotated page coordinates need an explicit native-ink profile')
    glyphs=[g for g in glyphs if g['c'].strip() and g.get('trace_gid',g.get('gid',0))>=0]
    required=Counter(_sig(g) for g in glyphs);by_char=defaultdict(list)
    for g in glyphs:by_char[g['c']].append(g)
    offsets=offsets or {};root=ET.fromstring(page.get_svg_image(text_as_path=True))
    definitions=next((e for e in root if e.tag.rsplit('}',1)[-1]=='defs'),None)
    refs=ET.Element('{'+SVG+'}svg',dict(width=str(page.rect.width),height=str(page.rect.height),viewBox=f'0 0 {page.rect.width} {page.rect.height}'))
    if definitions is not None:refs.append(deepcopy(definitions))
    matched=Counter();uses=0
    style_keys=['fill','stroke','stroke-width','stroke-linecap','stroke-linejoin','stroke-miterlimit',
                'fill-rule','fill-opacity','stroke-opacity','stroke-dasharray','stroke-dashoffset']
    def visit(element,parent=IDENTITY,inherited=None,opacity=1.,in_defs=False):
        nonlocal uses
        tag=element.tag.rsplit('}',1)[-1]
        if in_defs or tag=='defs':return
        transform=_multiply(_transform(element.get('transform')),parent)
        style=dict(inherited or {'fill':'black','stroke':'none'})
        declarations=dict(pair.split(':',1) for pair in element.get('style','').split(';') if ':' in pair)
        declarations={k.strip():v.strip() for k,v in declarations.items()}
        for key in style_keys:
            if element.get(key) is not None:style[key]=element.get(key)
            if key in declarations:style[key]=declarations[key]
        opacity*=float(declarations.get('opacity',element.get('opacity','1')))
        if tag=='use' and element.get('data-text') is not None:
            c=element.get('data-text');x,y=_point(transform,float(element.get('x','0')),float(element.get('y','0')))
            candidates=[g for g in by_char[c] if abs(g['origin'][0]-x)<.002 and abs(g['origin'][1]-y)<.002]
            if candidates:
                shifts={offsets.get(_key(g),0.) for g in candidates}
                if len(shifts)!=1:raise ValueError('Coincident source SVG uses request different dx')
                clone=deepcopy(element)
                for attr in ['transform','x','y','style','clip-path','mask','filter','opacity',*style_keys]:clone.attrib.pop(attr,None)
                a,b,c0,d,e,f=transform;e+=shifts.pop()
                clone.set('transform','matrix('+','.join('%.12g'%n for n in(a,b,c0,d,e,f))+')')
                for key,value in style.items():
                    if key in('fill','stroke') and value!='none':value='black'
                    clone.set(key,value)
                clone.set('opacity',str(opacity));refs.append(clone);uses+=1
                for signature in {_sig(g) for g in candidates}:matched[signature]+=1
        for child in element:visit(child,transform,style,opacity)
    visit(root)
    missing=required-matched
    report=dict(protected_physical_glyphs=len(glyphs),expected_signature_count=sum(required.values()),
                matched_outline_uses=uses,missing_source_outline_signatures=[dict(c=k[0],origin=[k[1],k[2]],count=n) for k,n in missing.items()],
                ancestor_transforms_flattened=True)
    if missing:return None,dict(report,passed=False)
    vector=fitz.open(stream=ET.tostring(refs,encoding='utf-8'),filetype='svg')
    expected=fitz.open(stream=vector.convert_to_pdf(),filetype='pdf')
    p=expected[0].get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csGRAY,alpha=False)
    mask=np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width).copy()<32
    expected.close();vector.close();return mask,dict(report,passed=True)


def _rgb(page,scale):
    p=page.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csRGB,alpha=False)
    return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3).copy()


def _identity(g):
    return(g['c'],g['font'],g['trace_gid'],round(g['size'],5),g['render_mode'],str(g['color']),
           g['opacity'],g['linewidth'],str(g['stroke_color']),g['stroke_opacity'])


def audit_moved_native_ink(source_path,source_page,final_path,final_page=1,*,shifts=(),
                           erased_glyphs=(),protected_glyphs=None,scale=4,position_tolerance_pt=.001):
    """Read-only actual-ink audit, usable by CPhO and IZhO wrappers.

    Pass the existing translated PDF as source and the composer's erasure and
    shift journals. By default all nonerased source glyphs are protected. An
    explicit protected_glyphs list can restrict this to original mathematics.
    Source/final pages are one-based. Missing expected native metadata or an
    unmatched source SVG use returns passed=False, never an empty-mask pass.
    """
    offsets={_key(g):float(s['dx']) for s in shifts for g in s['glyphs']}
    erased={_key(g) for g in erased_glyphs}
    wanted=None if protected_glyphs is None else {_key(g) for g in protected_glyphs
        if g['c'].strip() and g.get('trace_gid',g.get('gid',0))>=0 and g.get('render_mode')!=3}
    with fitz.open(source_path) as source,fitz.open(final_path) as final:
        a=source[source_page-1];b=final[final_page-1]
        if a.rect!=b.rect:raise ValueError('Native-ink page dimensions changed')
        native=[];found=set()
        for g in _traces(a):
            if not g['c'].strip() or g['trace_gid']<0 or g['render_mode']==3 or _key(g) in erased:continue
            if wanted is not None:
                if _key(g) not in wanted:continue
                found.add(_key(g))
            native.append(g)
        missing_requested=[] if wanted is None else[str(k) for k in wanted-found]
        buckets=defaultdict(list)
        for g in _traces(b):buckets[_identity(g)].append(g)
        missing_final=[]
        for g in native:
            x=g['origin'][0]+offsets.get(_key(g),0);y=g['origin'][1];rows=buckets[_identity(g)]
            candidates=[(i,h) for i,h in enumerate(rows) if abs(h['origin'][0]-x)<=position_tolerance_pt and abs(h['origin'][1]-y)<=position_tolerance_pt]
            if candidates:rows.pop(candidates[0][0])
            else:missing_final.append(dict(c=g['c'],font=g['font'],gid=g['trace_gid'],expected_origin=[x,y]))
        reference,outline_qa=source_outline_reference(a,native,offsets,scale)
        report=dict(source=str(source_path),source_page=source_page,final=str(final_path),final_page=final_page,
                    source_sha256=hashlib.sha256(Path(source_path).read_bytes()).hexdigest(),
                    output_sha256=hashlib.sha256(Path(final_path).read_bytes()).hexdigest(),scale=scale,
                    position_tolerance_pt=position_tolerance_pt,protected_native_glyphs=len(native),
                    missing_requested_source_glyphs=missing_requested,missing_final_native_glyphs=missing_final,
                    source_outline_audit=outline_qa,
                    method='Original input glyph outlines with composed SVG ancestor transforms, shifted independently and rendered without text clips; reference<32 versus actual minRGB<220.')
        if missing_requested or missing_final or not outline_qa['passed']:return dict(report,passed=False)
        stationary=[g for g in native if not offsets.get(_key(g),0)]
        old_reference,inherited_qa=source_outline_reference(a,stationary,scale=scale)
        if not inherited_qa['passed']:return dict(report,passed=False,stationary_outline_audit=inherited_qa)
        before=_rgb(a,scale);after=_rgb(b,scale)
        inherited=old_reference&(before.min(axis=2)>=220)
        missing=reference&(after.min(axis=2)>=220)&~inherited
        report.update(expected_native_dark_pixels=int(reference.sum()),
                      inherited_stationary_source_occluded_pixels=int(inherited.sum()),
                      newly_missing_native_ink_pixels=int(missing.sum()),passed=not bool(missing.any()))
        if missing.any():
            ys,xs=np.nonzero(missing);report['missing_bbox']=[float(xs.min()/scale),float(ys.min()/scale),float((xs.max()+1)/scale),float((ys.max()+1)/scale)]
        return report
