"""Verify actual original fraction-rule geometry carried by complete native clips."""
from pathlib import Path
import json
from collections import defaultdict
import pymupdf as fitz
from pdf_original_text_ops import glyph_key

def audit(proof,composition):
    shifts=defaultdict(list)
    for s in composition['native_shifts']:
        for g in s['glyphs']:shifts[glyph_key(g)].append(s['dx'])
    rows=[]
    with fitz.open(composition['source'])as old,fitz.open(proof)as new:
        original=old[composition['source_page']-1].get_drawings();actual=new[0].get_drawings()
        for atom in composition.get('reviewed_explicit_native_math_atoms',[]):
            paths=atom.get('preserved_vector_paths_in_complete_clip',[])
            if not paths:continue
            dxs=[shifts.get(glyph_key(g),[0.])[0]for g in atom['glyphs']if g['c'].strip()]
            if max(dxs)-min(dxs)>.001:raise ValueError('Complete native clip has split glyph motion')
            dx=dxs[0]
            for path in paths:
                candidates=[d for d in original if max(abs(a-b)for a,b in zip(d['rect'],path['rect']))<.001]
                if len(candidates)!=1:raise ValueError('Original fraction rule cannot be identified uniquely')
                source=candidates[0]
                if source['type']!='s'or not all(i[0]=='l'for i in source['items']):raise ValueError('This reviewed fraction profile requires original stroked straight native rules')
                rect=list(fitz.Rect(source['rect'])+(dx,0,dx,0))
                found=[d for d in actual if max(abs(a-b)for a,b in zip(d['rect'],rect))<.001]
                same=[]
                for d in found:
                    style=all(d.get(k)==source.get(k)for k in ['type','width','color','fill','lineCap','lineJoin','dashes','stroke_opacity','fill_opacity','closePath'])
                    points=len(d['items'])==len(source['items'])and all(a[0]==b[0]and max(abs(a[j][axis]-b[j][axis]-(dx if axis==0 else 0))for j in [1,2]for axis in [0,1])<.001 for a,b in zip(d['items'],source['items']))
                    if style and points:same.append(d)
                rows.append(dict(original_operator_indices=path['operator_indices'],original_rect=list(source['rect']),expected_rect=rect,dx=dx,original_stroke_width=source['width'],matching_actual_native_paths=len(same),passed=len(same)==1,complete_original_clip=atom['complete_original_clip']))
    result=dict(proof=str(proof),paths=rows,passed=all(r['passed']for r in rows),method='Actual final native drawing endpoints, stroke width/style and relative glyph dx matched to each original fraction rule carried by its complete original clip.')
    Path(proof).with_suffix('.complete-clip-bars.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    return result
