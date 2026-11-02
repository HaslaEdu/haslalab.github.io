"""Actual ink masks for explicitly translated native-text figure labels."""
import pymupdf as fitz
import numpy as np
from pdf_text_motion_ink import ink_envelope
from izho_initial_fixed_style import runs_of,characters
from initial_prose_reading_order import journal
from pdf_korean_natural_composer import normalize_placements
from pdf_original_text_ops import glyph_key

def masks(plan,proof,composition,scale=4):
    labels=plan.get('reviewed_native_figure_language_labels',[])
    with fitz.open(plan['original_english_source'])as src,fitz.open(plan['source_base'])as base,fitz.open(proof)as dst:
        original=src[plan['source_page']-1];page=dst[0];h=int(round(page.rect.height*scale+.5));w=int(round(page.rect.width*scale+.5))
        if not labels:return np.zeros((h,w),bool),np.zeros((h,w),bool),None
        runs=runs_of(original);old_origins=[];new_origins=[];rows=[]
        authored=journal(base[plan['page']-1],normalize_placements(base[plan['page']-1],plan['prose_placements']))
        shifts={glyph_key(g):s['dx']for s in composition['native_shifts']for g in s['glyphs']}
        traces=[dict(c=chr(cp),gid=gid,font=t['font'],size=t['size'],origin=point,paint=t['type'])for t in page.get_texttrace()for cp,gid,point,bbox in t['chars']if not chr(cp).isspace()]
        for label in labels:
            if not label.get('reviewed')or label['source_sha256']!=plan['original_english_source_sha256']:raise ValueError('Unreviewed native picture label')
            run=runs[tuple(label['at'])];old=[g for g in characters(run)if g['c'].strip()];old_origins.extend(g['origin']for g in old)
            hits=[p for p in composition['new_batang_placements']if p['text']==label['text']and abs(p['point'][1]-old[0]['origin'][1])<.01]
            if not hits:
                # Bold/italic translated labels intentionally retain their
                # original-role fallback outlines instead of becoming Batang.
                # Locate each by the exact initial authored-tail journal and
                # follow its recorded CID/GID x-only motion into the proof.
                entries=[j for j in authored if j['placement'].get('source_slot',j['placement'].get('at'))==label['at']]
                if len(entries)!=1 or entries[0]['placement']['text'].strip()!=label['text']:raise ValueError('Exact original figure-language slot missing')
                expected=entries[0]['glyphs'];actual=[]
                for g in expected:
                    if not g['c'].strip():continue
                    dx=shifts.get(glyph_key(g),0.)
                    matches=[a for a in traces if a['c']==g['c']and a['gid']==g['gid']and a['font']==g['font']and a['paint']==g['paint']and abs(a['size']-run['size'])<.001 and abs(a['origin'][1]-g['origin'][1])<.001 and abs(a['origin'][0]-g['origin'][0]-dx)<.001]
                    if len(matches)!=1:raise ValueError('Figure label actual font/GID/point/paint/x-only motion mismatch')
                    actual.append(matches[0])
                if ''.join(a['c']for a in actual)!=label['text']:raise ValueError('Retained-role figure language sequence changed')
                new_origins.extend(a['origin']for a in actual)
                rows.append(dict(at=label['at'],source_text=run['text'],translated_text=label['text'],source_font=run['font'],source_point_size=run['size'],target_point_size=actual[0]['size'],source_baseline=old[0]['origin'][1],target_baseline=actual[0]['origin'][1],target_font=actual[0]['font'],source_font_metadata_available=True,actual_initial_authored_GID_and_point_and_paint_retained=True))
                continue
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
