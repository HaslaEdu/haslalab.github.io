"""Actual ink masks for explicitly translated native-text figure labels."""
import pymupdf as fitz
import numpy as np
from pdf_text_motion_ink import ink_envelope
from izho_initial_fixed_style import runs_of,characters

def masks(plan,proof,composition,scale=4):
    labels=plan.get('reviewed_native_figure_language_labels',[])
    with fitz.open(plan['original_english_source'])as src,fitz.open(proof)as dst:
        original=src[plan['source_page']-1];page=dst[0];h=int(round(page.rect.height*scale+.5));w=int(round(page.rect.width*scale+.5))
        if not labels:return np.zeros((h,w),bool),np.zeros((h,w),bool),None
        runs=runs_of(original);old_origins=[];new_origins=[];rows=[]
        for label in labels:
            if not label.get('reviewed')or label['source_sha256']!=plan['original_english_source_sha256']:raise ValueError('Unreviewed native picture label')
            run=runs[tuple(label['at'])];old=[g for g in characters(run)if g['c'].strip()];old_origins.extend(g['origin']for g in old)
            hits=[p for p in composition['new_batang_placements']if p['text']==label['text']and abs(p['point'][1]-old[0]['origin'][1])<.01]
            if len(hits)!=1:raise ValueError(('Figure label translation cannot be identified exactly',label,hits))
            p=hits[0];glyphs=[]
            for trace in page.get_texttrace():
                if trace['font']!='Batang'or abs(trace['size']-run['size'])>.001:continue
                glyphs.extend((chr(c),point)for c,gid,point,bbox in trace['chars']if abs(point[1]-p['point'][1])<.01 and p['point'][0]-.01<=point[0]<p['point'][0]+len(label['text'])*run['size']-.01)
            if ''.join(c for c,_ in glyphs)!=label['text']:raise ValueError('A native figure label lost translated glyphs')
            new_origins.extend(point for _,point in glyphs)
            rows.append(dict(at=label['at'],source_text=run['text'],translated_text=label['text'],source_font=run['font'],source_point_size=run['size'],target_point_size=p['style']['size'],source_baseline=old[0]['origin'][1],target_baseline=p['point'][1],source_font_metadata_available=True))
        old_mask,_=ink_envelope(original,old_origins,scale);new_mask,_=ink_envelope(page,new_origins,scale)
        return old_mask,new_mask,dict(labels=rows,actual_source_and_translated_language_glyph_ink_only=True,nonlanguage_picture_geometry_and_variables_protected=True)
