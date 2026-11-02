"""Independent native ink, geometry, and collision checks for CPhO2023."""
from pathlib import Path
import argparse,json,math,re
import numpy as np
import pymupdf as fitz
from cpho_2023_natural_spacing import OUT,ROOT
from pdf_memory_gate import page_worker
from pdf_moved_native_ink import audit_moved_native_ink,source_outline_reference,_key
from pdf_native_inline_reposition import _traces
from pdf_original_text_ops import glyph_key
from pdf_native_geometry_motion import audit as geometry_motion
from natural_spacing_form_groups import atomic_shifts
from pdf_original_graphics_ink import graphics_control

def rgb(page,scale=4,clip=None):
    p=page.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csRGB,alpha=False,clip=clip)
    return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3).copy()

def audit(number,language='ko'):
    path=OUT/f'CPhO_2023_p{number}_{language.upper()}_natural.pdf'
    q=json.loads(path.with_suffix('.qa.json').read_text('utf8'));source=Path(q['source'])
    def physical(g):return(g['c'],g['font'],g['trace_gid'],round(g['size'],5),round(g['origin'][0],3),round(g['origin'][1],3))
    labels=json.loads((ROOT/'tools/ko/cpho/2023/original-labels/label-plan.json').read_text('utf8'))['labels']
    language_keys={glyph_key(g)for label in labels if label['page']==number and label['kind']=='native-form-language'for g in label['source_glyphs']}
    with fitz.open(ROOT/'tmp/source-audit/CPhO_2023_T_ZH.pdf')as original,fitz.open(source)as old:
        original_keys={physical(g)for g in _traces(original[number-1])if glyph_key(g)not in language_keys}
        physical_math=[g for g in _traces(old[0])if physical(g)in original_keys]
    ink=audit_moved_native_ink(source,1,path,shifts=q['native_shifts'],erased_glyphs=q['erased_hangul_glyphs'],protected_glyphs=physical_math,scale=4)
    groups=atomic_shifts(source,1,q['native_shifts'])
    motion,geometry=geometry_motion(source,path,groups,scale=4)
    figure_source=ROOT/f'tmp/original-style-repair/2023/CPhO_2023_p{number}_{language.upper()}_proof.pdf'
    if language=='ko':figure_source=Path(f'D:/CodexBuilds/Hasla-original-style-20261031/cpho2023/immutable-slot-baselines/CPhO_2023_p{number}_KO_proof.pdf')
    else:figure_source=Path(f'D:/CodexBuilds/Hasla-original-style-20261031/cpho2023/strict-en/proofs/CPhO_2023_p{number}_EN_proof.pdf')
    with fitz.open(source)as a,fitz.open(path)as b,fitz.open(figure_source)as original_figures:
        figures=[]
        for rect in q['reviewed_line_profile']['excluded_figure_rects']:
            # Display formula locks are also checked exactly like figures.
            old=rgb(original_figures[0],clip=fitz.Rect(rect));new=rgb(b[0],clip=fitz.Rect(rect))
            changed=int(np.any(old!=new,axis=2).sum())
            figures.append(dict(rect=rect,changed_pixels=changed))
        new_glyphs=[g for g in _traces(b[0])if g['font']=='Batang'and g['c'].strip()and g['trace_gid']>=0]
        offsets={_key(g):s['dx']for s in q['native_shifts']for g in s['glyphs']}
        if language=='en':
            physical_keys={glyph_key(g)for g in physical_math}
            # Protected figure/locked-display regions already have exact RGB
            # equality checks above. Their unchanged white figure labels are
            # not newly packed black body prose.
            protected_regions=[fitz.Rect(r)for r in q['reviewed_line_profile']['excluded_figure_rects']]
            new_glyphs=[g for g in _traces(a[0])if glyph_key(g)not in physical_keys and not re.search('[\u3400-\u9fff]',g['c'])
                and g['c'].strip()and g['trace_gid']>=0 and not any(fitz.Rect(g['bbox']).intersects(r)for r in protected_regions)]
            fresh,fresh_qa=source_outline_reference(a[0],new_glyphs,offsets,scale=4)
        else:fresh,fresh_qa=source_outline_reference(b[0],new_glyphs,scale=4)
        erased={glyph_key(g)for g in q['erased_hangul_glyphs']}
        native=physical_math if language=='en'else[g for g in _traces(a[0])if glyph_key(g)not in erased and g['trace_gid']>=0 and g['c'].strip()]
        protected,protected_qa=source_outline_reference(a[0],native,offsets,scale=4)
        collision=None;hangul_missing=None;bbox=None;graphics_overlap=None;graphics_bbox=None;missing_bbox=None;missing_bands=[]
        if fresh is not None and protected is not None:
            overlap=fresh&protected;collision=int(overlap.sum())
            actual=rgb(b[0]);missing=fresh&(actual.min(axis=2)>=220);hangul_missing=int(missing.sum())
            if hangul_missing:
                ys,xs=np.nonzero(missing)
                missing_bbox=[float(xs.min()/4),float(ys.min()/4),float((xs.max()+1)/4),float((ys.max()+1)/4)]
                bands,counts=np.unique(ys//64,return_counts=True)
                missing_bands=[dict(y0=int(band*16),y1=int((band+1)*16),pixels=int(count))for band,count in zip(bands,counts)]
            if collision:
                ys,xs=np.nonzero(overlap);bbox=[float(xs.min()/4),float(ys.min()/4),float((xs.max()+1)/4),float((ys.max()+1)/4)]
            with fitz.open(stream=graphics_control(b,b[0]),filetype='pdf')as nontext:
                dark=rgb(nontext[0]).min(axis=2)<80
            overlap_graphics=fresh&dark;graphics_overlap=int(overlap_graphics.sum())
            if graphics_overlap:
                ys,xs=np.nonzero(overlap_graphics);graphics_bbox=[float(xs.min()/4),float(ys.min()/4),float((xs.max()+1)/4),float((ys.max()+1)/4)]
        b[0].get_pixmap(matrix=fitz.Matrix(1.25,1.25)).save(path.with_suffix('.png'))
    r=dict(document_page=number,language=language,output_sha256=q['output_sha256'],native_ink=ink,native_geometry=geometry,
           figure_reference_source=str(figure_source),figure_reference_is_immutable_before_heading_or_prose_edits=True,
           unchanged_figure_and_stationary_display_regions=figures,new_hangul_outline_reference=fresh_qa,
           native_outline_reference=protected_qa,new_hangul_missing_dark_pixels=hangul_missing,
           new_prose_missing_dark_ink_bbox=missing_bbox,new_prose_missing_dark_ink_bands=missing_bands,
           new_hangul_and_retained_native_dark_ink_overlap_pixels=collision,overlap_bbox=bbox,
           new_prose_and_native_graphics_dark_ink_overlap_pixels=graphics_overlap,graphics_overlap_bbox=graphics_bbox,
           passed=bool(ink['passed']and geometry['changed_nonselected_native_graphical_pixels']==0
                       and not any(f['changed_pixels']for f in figures)and fresh_qa['passed']and protected_qa['passed']
                       and collision==0 and graphics_overlap==0 and hangul_missing==0))
    path.with_suffix('.independent.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps(dict(page=number,passed=r['passed'],math=ink.get('newly_missing_native_ink_pixels'),graphics=geometry['changed_nonselected_native_graphical_pixels'],figures=sum(f['changed_pixels']for f in figures),overlap=collision,graphic_overlap=graphics_overlap,hangul_missing=hangul_missing,bbox=bbox,graphic_bbox=graphics_bbox)),flush=True)
    return r

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--page',type=int,required=True);p.add_argument('--language',choices=['ko','en'],default='ko');a=p.parse_args()
    with page_worker():r=audit(a.page,a.language)
    raise SystemExit(not r['passed'])
