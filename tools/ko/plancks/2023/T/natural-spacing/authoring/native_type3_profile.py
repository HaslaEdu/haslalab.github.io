"""Exact original F56 bitmap-font reader for the 2023 native N atom.

The complete source Encoding/Widths/FontMatrix/CharProc signature is pinned.
No font, glyph, cmap or bitmap is created, replaced or written. Only the
already verified source code78/trace Unicode78/GID78 may be associated.
"""
import hashlib,json,re
import pikepdf

EXPECTED='03c6ad173286b8ced37bd2c2ed8087f945e84b7785c88869eb822273316420c1'
sha=lambda value:hashlib.sha256(value).hexdigest()

def signature(font):
    if str(font.get('/Subtype'))!='/Type3':raise ValueError('Expected original Type3 font')
    required={'/Widths','/FontMatrix','/Name','/CharProcs','/FontBBox','/FirstChar','/LastChar','/Resources','/Type','/Subtype','/Encoding'}
    if set(map(str,font.keys()))!=required:raise ValueError('Original Type3 dictionary keys changed')
    if str(font.Type)!='/Font'or str(font.Encoding.Type)!='/Encoding':raise ValueError('Original Type3 dictionary type changed')
    if set(map(str,font.Resources.keys()))!={'/ProcSet'}or set(map(str,font.Encoding.keys()))!={'/Type','/Differences'}:
        raise ValueError('Original Type3 resources or explicit Encoding changed')
    return {'name':str(font.Name),'matrix':list(map(float,font.FontMatrix)),'bbox':list(map(float,font.FontBBox)),
        'widths':list(map(float,font.Widths)),'first':int(font.FirstChar),'last':int(font.LastChar),
        'differences':[v if isinstance(v,int)else str(v)for v in font.Encoding.Differences],
        'procset':[str(v)for v in font.Resources.ProcSet],
        'charprocs':{str(name):{'raw_sha256':sha(proc.read_raw_bytes()),'decoded_sha256':sha(proc.read_bytes()),'filter':str(proc.get('/Filter'))}
            for name,proc in font.CharProcs.items()}}

def profile(font):
    if str(font.get('/Subtype'))!='/Type3'or str(font.get('/Name'))!='/F56':return None
    sig=signature(font);digest=sha(json.dumps(sig,sort_keys=True,separators=(',',':')).encode())
    if digest!=EXPECTED:raise ValueError('Original F56 Type3 CharProc/Matrix/Widths/Encoding signature changed')
    return {'font':'F56','signature_sha256':digest,'encoded_mapping':{78:'N'},
        'verified_source_unicode_gid':{'code':78,'unicode':78,'gid':78},'font_signature':sig,
        'program_policy':'Exact original self-contained CharProcs and font dictionary preserved; only source text-show CTM may move horizontally.'}

def font_name(font):
    if font.get('/BaseFont')is not None:return str(font.BaseFont)
    if profile(font)is not None:return str(font.Name)
    raise ValueError('Missing original BaseFont without a verified Type3 Name/program profile')

def verify_cluster(font,code,cluster):
    proof=profile(font)
    if proof is None or code!=78 or len(cluster)!=1:raise ValueError('Unverified Type3 source code/cluster')
    g=cluster[0]
    if g['c']!='N'or g.get('trace_gid',g.get('gid'))!=78 or g['font']!='F56':
        raise ValueError('Original Type3 code/Unicode/GID trace mismatch')
    return proof

def glyph_bounds(font,code,cluster):
    """Read the true original painted bit rectangle in source glyph units."""
    verify_cluster(font,code,cluster);proc=font.CharProcs['/a78'];raw=proc.read_bytes()
    ins=list(pikepdf.parse_content_stream(proc))
    operators=[str(v.operator)if isinstance(v,pikepdf.ContentStreamInstruction)else'BI'for v in ins]
    if operators!=['d1','q','cm','BI','Q']:raise ValueError('Unexpected original Type3 program operators')
    meta=ins[3].iimage.obj
    if set(map(str,meta.keys()))!={'/Width','/Height','/ImageMask','/BitsPerComponent','/Decode'}or not bool(meta.ImageMask)or int(meta.BitsPerComponent)!=1 or list(meta.Decode)!=[1,0]:
        raise ValueError('Unsupported original Type3 inline image-mask profile')
    w,h=int(meta.Width),int(meta.Height);row=(w+7)//8
    marker=re.search(rb'\bID[ \r\n]',raw)
    if marker is None:raise ValueError('Missing original Type3 inline bitmap marker')
    start=marker.end()
    if raw[start-1:start]==b'\r'and raw[start:start+1]==b'\n':start+=1
    tail=raw[start:];bitmap=tail[:row*h]
    if len(bitmap)!=row*h or not re.fullmatch(rb'EI\s+Q',tail[row*h:].strip()):raise ValueError('Original Type3 bitmap row bytes/trailing program changed')
    points=[(x,y)for y in range(h)for x in range(w)if bitmap[y*row+x//8]&(0x80>>(x%8))]
    if not points:raise ValueError('Original Type3 glyph has no painted bits')
    # PDF ImageMask Decode[1,0] paints source sample1. Image row0 is the top
    # row, whereas the original inline cm maps a bottom-left unit rectangle.
    x0=min(x for x,y in points)/w;x1=(max(x for x,y in points)+1)/w
    y0=1-(max(y for x,y in points)+1)/h;y1=1-min(y for x,y in points)/h
    a,b,c,d,e,f=map(float,ins[2].operands)
    corners=[(a*x+c*y+e,b*x+d*y+f)for x,y in[(x0,y0),(x0,y1),(x1,y0),(x1,y1)]]
    bounds=[min(x for x,y in corners),min(y for x,y in corners),max(x for x,y in corners),max(y for x,y in corners)]
    return bounds,tuple(map(float,font.FontMatrix))
