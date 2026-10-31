"""Collect complete native inline Form/clip expressions before line packing.

An arrow accent may have the same nominal font size as its variable but an
origin ten points above the prose baseline. It must not be filtered as a
separate text line. The original invocation/clip group defines atomicity.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import math,re
import pymupdf as fitz
from pdf_native_inline_reposition import inspect_inline_groups
from pdf_original_text_ops import glyph_key

@lru_cache(maxsize=3)
def _inventory(path,page_number,mtime,size):
    return inspect_inline_groups(path,page_number)

def atomic_tokens(source,page_number,allowed_rect,prose_baselines,excluded_rects=None):
    """Return disjoint native atomic tokens in one reviewed paragraph region.

    ``prose_baselines`` accepts numbers or ``{baseline,size}`` dictionaries.
    Size defaults to12 only for geometric association; actual glyph point
    sizes remain unchanged. Excluded figure rectangles always win.
    """
    source=Path(source).resolve();stat=source.stat()
    inv=_inventory(str(source),page_number,stat.st_mtime_ns,stat.st_size)
    rect=fitz.Rect(allowed_rect);excluded=[fitz.Rect(r)for r in(excluded_rects or[])]
    baselines=[dict(baseline=float(v['baseline']),size=float(v.get('size',12)))if isinstance(v,dict)
               else dict(baseline=float(v),size=12.)for v in prose_baselines]
    candidates=[]
    groups=[dict(g,group_type='clip')for g in inv['clip_groups']]
    groups.extend(dict(g,group_type='form')for g in inv['forms'])
    for group in groups:
        if group['group_type']=='clip':
            clip_rects=group.get('clip_rects',[])
            if not group.get('known_rectangular_clips')or not clip_rects:continue
            max_height=max(45,3*max((b['size']for b in baselines),default=12))
            # A full-page clip around one ordinary glyph does not make that
            # glyph a new atomic mathematical object. Only tight native clips
            # are eligible for this collector.
            if not all(r is not None and fitz.Rect(r).width<=rect.width+2
                       and fitz.Rect(r).height<=max_height for r in clip_rects):continue
        glyphs=[]
        for c in group['glyphs']:
            g=dict(c);g['gid']=g.get('gid',g.get('trace_gid',-1));glyphs.append(g)
        visible=[g for g in glyphs if g['c'].strip()and g['gid']>=0]
        if not visible:continue
        bounds=fitz.Rect()
        for g in visible:bounds|=fitz.Rect(g['bbox'])
        physical_form=None
        if group['group_type']=='form'and group.get('native_page_bbox'):
            physical_form=fitz.Rect(group['native_page_bbox'])
            # Full native containers include original math bitmaps and rules
            # beyond their text glyph metrics. Skip an oversized wrapper so a
            # smaller complete child can be selected instead.
            if physical_form.width>rect.width+2 or physical_form.height>max(70,4*max((b['size']for b in baselines),default=12)):
                continue
            bounds|=physical_form
        # A complete page or multi-line display object is never considered an
        # inline formula merely because one of its glyphs is near prose.
        if bounds.x0<rect.x0-1 or bounds.x1>rect.x1+1:continue
        height_limit=max(70,4*max((b['size']for b in baselines),default=12))if group['group_type']=='form'else max(45,3*max((b['size']for b in baselines),default=12))
        if bounds.height>height_limit:continue
        if any(bounds.intersects(r)for r in excluded):continue
        anchored=[]
        for base in baselines:
            y=base['baseline'];size=base['size']
            body=[g for g in visible if not re.search(r'MT.?Extra',g['font'],re.I)
                  and .7*size<=g['size']<=1.45*size and abs(g['origin'][1]-y)<.35*size]
            if not body:continue
            score=(len(body),-min(abs(g['origin'][1]-y)for g in body))
            anchored.append((score,base))
        if not anchored:continue
        _,base=max(anchored,key=lambda item:item[0]);y=base['baseline']
        if not rect.y0<=y<=rect.y1:continue
        # Preserve existing relative formula positions, including arrowheads,
        # fractions, scripts and the original font metrics.
        x0=min(g['origin'][0]for g in visible);x1=max(g['bbox'][2]for g in visible)
        if physical_form is not None:
            x0=min(x0,physical_form.x0);x1=max(x1,physical_form.x1)
        keys={glyph_key(g)for g in glyphs}
        shift_kwargs=dict(form_path=group['path'])if group['group_type']=='form'else{}
        result=dict(text=''.join(g['c']for g in sorted(visible,key=lambda g:(g['origin'][0],g['origin'][1]))),
            kind='native',glyphs=glyphs,x0=x0,x1=x1,y=y,size=base['size'],
            fonts=sorted({g['font']for g in visible}),shift_kwargs=shift_kwargs,
            atomic_native_group=group['group_type'],bbox=list(bounds))
        if physical_form is not None:result['native_page_bbox']=list(physical_form)
        if group['group_type']=='clip':
            result['source_operator_indices']=group['operator_indices']
            result['source_clip_rects']=group['clip_rects']
            result['source_ancestor_clip_rects']=group.get('ancestor_clip_rects',[])
        else:result['source_form_path']=group['path']
        candidates.append((keys,result))
    # Choose a complete outer native expression rather than overlapping parent
    # and child Forms. Equal-key outer clipping takes priority over a Form so
    # both the invocation and its enclosing clipping move together.
    candidates.sort(key=lambda item:(-len(item[0]),item[1]['atomic_native_group']!='clip',len(item[1].get('source_form_path',[]))))
    result=[];claimed=set()
    for keys,item in candidates:
        if keys&claimed:continue
        claimed.update(keys);result.append(item)
    return sorted(result,key=lambda t:(t['y'],t['x0']))
