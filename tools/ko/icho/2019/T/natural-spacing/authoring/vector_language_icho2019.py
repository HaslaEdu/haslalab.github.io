"""Suppress only reviewed pure-English paths; retain every source path byte.

Every review pins a source Form and exact path. Fully contained pure-English
paths receive zero opacity. Explicit native prefixes and paths wholly outside
the English area receive only their reviewed x translation. A compound path
that also contains native material keeps the exact source-bound English clip.
All original construction/paint bytes remain inside these narrow wrappers;
the original Form stays reachable as /NativeInlineOriginal. No white mask or
whole-Form removal is used.
"""
from pathlib import Path
from io import BytesIO
import hashlib,json,math,re,sys
import numpy as np,pikepdf,pymupdf as f
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B/'engine'))
import latex_native_motion as m
import icho2019_write_guard as g
sha=lambda b:hashlib.sha256(b).hexdigest()

def form_object(pdf,path):
    obj=pdf.pages[0]
    for i in path:
        ins=pikepdf.parse_content_stream(obj)[i]
        if str(ins.operator)!='Do':raise ValueError('Reviewed Form invocation is not Do')
        obj=obj.Resources.XObject[ins.operands[0]]
    return obj

def inverse(matrix,x,y):
    a,b,c,d,e,z=matrix;det=a*d-b*c
    if abs(det)<1e-12:raise ValueError('Singular label transform')
    return((d*(x-e)-c*(y-z))/det,(-b*(x-e)+a*(y-z))/det)

def apply(raw,page,labels):
    if not labels:return raw,[]
    if sha(g.SOURCE.read_bytes())!=g.SOURCE_SHA:raise ValueError('Outlined-label original source hash changed')
    before=f.open(stream=raw,filetype='pdf');source_inv=m.inspect_inline_groups(g.SOURCE,page);inv=m.inspect_inline_groups(raw,1)
    pdf=pikepdf.Pdf.open(BytesIO(raw));audit=[]
    groups={}
    for label in labels:groups.setdefault(label['source_form_raw_sha256'],[]).append(label)
    for source_hash,rows in groups.items():
        originals=[v for v in source_inv['forms']if v['original_raw_sha256']==source_hash]
        current=[v for v in inv['forms']if v['original_raw_sha256']==source_hash]
        if len(originals)!=1 or len(current)!=1:raise ValueError('Outlined label needs one exact original/current Form invocation')
        original=originals[0];info=current[0];obj=form_object(pdf,info['path'])
        if original['glyphs']or info['glyphs']:raise ValueError('Outlined-label profile must contain no selectable source font glyphs')
        data,regions=m._raw_regions(obj);instructions=pikepdf.parse_content_stream(obj)
        if sha(obj.read_raw_bytes())!=source_hash:raise ValueError('Outlined label original Form raw SHA guard failed')
        # Get the complete original CTM at each pure path start, without
        # normalizing any high-precision original path/colour operators.
        state=tuple(info['entry_ctm']);stack=[];matrices={}
        for i,ins in enumerate(instructions):
            matrices[i]=m._multiply(state,info['page_matrix']);op=str(ins.operator)
            if op=='q':stack.append(state)
            elif op=='Q':state=stack.pop()
            elif op=='cm':state=m._multiply(tuple(map(float,ins.operands)),state)
        replacements=[];claimed=set();record=[]
        for label in rows:
            if label['source_sha256']!=g.SOURCE_SHA:raise ValueError('Outlined label source SHA mismatch')
            for ref in label['source_paths']:
                found=[v for v in original['own_vector_paths']if v==ref]
                if len(found)!=1:raise ValueError('Outlined label exact original path/paint/bounds guard failed')
                indices=ref['operator_indices'];a,z=regions[indices[0]][0],regions[indices[-1]][1]
                if claimed.intersection(indices):raise ValueError('Outlined language paths overlap')
                claimed.update(indices);fragment=data[a:z];matrix=matrices[indices[0]]
                r=label['english_clip_rect'];native=indices in label.get('preserved_native_caption_edge_paths',[]);area=f.Rect(r);bounds=f.Rect(ref['rect'])
                if native and f.Rect(r).intersects(f.Rect(ref['rect'])):raise ValueError('English review scope overlaps a declared scientific caption prefix')
                mode='native-prefix-x-translation-only'if native else('outside-English-scope-x-translation-only'if not area.intersects(bounds)else'pure-English-path-zero-opacity'if area.contains(bounds)else'mixed-path-exact-English-clip')
                numbers=lambda p:' '.join(f'{v:.14f}'for v in p)
                dx=float(label.get('native_caption_path_dx_pt',0.));tx,ty=m._inverse_vector(matrix,dx)
                points=None;extra='/KO_Reviewed_English_ZeroOpacity gs 'if mode=='pure-English-path-zero-opacity'else''
                if mode=='mixed-path-exact-English-clip':
                    points=[inverse(matrix,x,y)for x,y in[(r[0],r[1]),(r[2],r[1]),(r[2],r[3]),(r[0],r[3])]]
                    extra='-1000000 -1000000 2000000 2000000 re '+numbers(points[0])+' m '+' '.join(numbers(p)+' l'for p in points[1:])+' h W* n '
                prefix=('q 1 0 0 1 '+numbers((tx,ty))+' cm '+extra).encode('ascii')
                replacements.append((a,z,prefix+fragment+b' Q'))
                record.append(dict(id=label['id'],source_text=label['source_text'],source_path=ref,original_construction_and_paint_fragment_sha256=sha(fragment),original_construction_and_paint_bytes_retained=True,reviewed_English_area_rect=r,suppression_mode=mode,local_clip_polygon=points,native_caption_path_dx_pt=dx,local_translation_matrix=[1,0,0,1,tx,ty]))
        pieces=[];at=0
        for a,z,value in sorted(replacements):pieces.extend([data[at:a],b'\n',value,b'\n']);at=z
        pieces.append(data[at:]);changed=b''.join(pieces)
        clone=pdf.make_stream(changed)
        for key,value in obj.items():
            if str(key)not in['/Length','/Filter','/DecodeParms']:clone[key]=value
        resources=pikepdf.Dictionary(obj.get('/Resources',pikepdf.Dictionary()));states=pikepdf.Dictionary(resources.get('/ExtGState',pikepdf.Dictionary()))
        if '/KO_Reviewed_English_ZeroOpacity'in states:raise ValueError('Source already defines the private English suppression state')
        states['/KO_Reviewed_English_ZeroOpacity']=pikepdf.Dictionary(Type=pikepdf.Name('/ExtGState'),ca=0,CA=0);resources.ExtGState=states;clone.Resources=resources
        clone['/NativeInlineOriginal']=obj
        # Form path ancestors are private output objects. Preserve the old
        # object and resource, then replace only the actual Do resource entry.
        parent=pdf.pages[0]
        for idx in info['path'][:-1]:parent=parent.Resources.XObject[pikepdf.parse_content_stream(parent)[idx].operands[0]]
        ins=pikepdf.parse_content_stream(parent)[info['path'][-1]];name=ins.operands[0]
        resources=pikepdf.Dictionary(parent.Resources);xobjects=pikepdf.Dictionary(resources.XObject)
        backup=pikepdf.Name('/OriginalOutlinedLanguage_'+source_hash[:12]);xobjects[backup]=obj;xobjects[name]=clone;resources.XObject=xobjects;parent.Resources=resources
        if any(data[a:z]not in changed for a,z,_ in replacements):raise ValueError('Original outlined label path bytes were lost')
        audit.append(dict(source_form_path=original['path'],source_raw_stream_sha256=source_hash,translated_raw_stream_sha256=sha(clone.read_raw_bytes()),source_native_page_bbox=original['native_page_bbox'],only_reviewed_English_path_opacity_or_exact_clip_and_caption_x_translations_added=True,all_original_construction_paint_and_other_bytes_retained=True,original_Form_reference_retained=True,original_form_glyph_count=0,source_font_and_point_metadata_available=False,paths=record,source_form_own_vector_paths=original['own_vector_paths']))
    buffer=BytesIO();pdf.save(buffer,compress_streams=False);pdf.close();result=buffer.getvalue();after=f.open(stream=result,filetype='pdf')
    a=before[0].get_pixmap(matrix=f.Matrix(4,4),alpha=False,colorspace=f.csGRAY);b=after[0].get_pixmap(matrix=f.Matrix(4,4),alpha=False,colorspace=f.csGRAY)
    aa=np.frombuffer(a.samples,np.uint8).reshape(a.height,a.width);bb=np.frombuffer(b.samples,np.uint8).reshape(b.height,b.width);diff=aa!=bb;allowed=np.zeros(diff.shape,bool)
    for label in labels:
        r=label.get('source_caption_rect',label['english_clip_rect']);dx=label.get('native_caption_path_dx_pt',0.);r=[min(r[0],r[0]+dx),r[1],max(r[2],r[2]+dx),r[3]]
        allowed[max(0,math.floor(r[1]*4)-1):math.ceil(r[3]*4)+1,max(0,math.floor(r[0]*4)-1):math.ceil(r[2]*4)+1]=True
    outside=int((diff&~allowed).sum())
    if outside:raise ValueError('Outlined English suppression changed source pixels outside the reviewed language area: '+str(outside))
    if not int(diff.sum()):raise ValueError('Outlined English label suppression changed no source ink')
    for item in audit:item.update(pixel_verification_scale=4,changed_pixels_total=int(diff.sum()),changed_pixels_outside_reviewed_label_scopes=outside,all_other_native_paths_coordinates_and_paint_preserved=True)
    before.close();after.close();return result,audit
