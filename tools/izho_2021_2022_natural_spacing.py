"""Horizontal line repair for the reviewed 2021/2022 IZhO editions.

Original-style plans remain immutable. New plans use their source baseline
and physical paragraph boundaries, then operate on the reviewed Korean PDF.
Display equations, separate columns and figures are not combined into prose.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import pymupdf as fitz
import izho_early_fixed_style as legacy
from izho_natural_spacing import plan_page
from pdf_native_inline_reposition import reposition_inline
from pdf_original_text_ops import glyph_key
from pdf_original_style_audit import native_ink_neighborhood

ROOT=legacy.ROOT
OUT=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho-natural-spacing/2021-2022')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def policy(year,kind,number):
    plan=ROOT/f'tools/ko/izho/{year}/{kind}/original_style/page{number}.json'
    data=json.loads(plan.read_text('utf8'));source=ROOT/data['source']
    with fitz.open(source)as doc:
        page=doc[data['page']];fitz.TOOLS.set_small_glyph_heights(True);runs=legacy.runs_of(page)
        work=[];selected=set()
        for slot in data['slots']:
            anchor,chars,rect,point=legacy.slot_source(slot,runs)
            work.append(dict(slot=slot,rect=list(rect),baseline=point[1],size=anchor['size']))
            selected.update(glyph_key(c)for c in chars)
        native=[c for run in runs.values()for c in legacy.characters(run)if c['c'].strip()and glyph_key(c)not in selected]
        baselines=[];baseline_tolerance=.75 if kind=='TS'else.1
        # The source's prose word following beta on 2022TS4 is printed
        # 5.04pt below the other words of its physical sentence. Treat this as
        # one logical row without changing that word's real original y.
        if(year,kind,number)==(2022,'TS',4):baseline_tolerance=5.1
        for item in work:
            if not any(abs(item['baseline']-y)<baseline_tolerance for y in baselines):baselines.append(item['baseline'])
        images=[list(info['bbox'])for i,info in enumerate(page.get_image_info())if i not in data.get('inline_math_images',[])]
        # Large actual vector illustrations/table frames are explicit blocked
        # regions. Fraction/radical primitives remain the move helper's strict
        # vector-overlap responsibility.
        figures=[list(d['rect'])for d in page.get_drawings()if d['rect'].width>25 and d['rect'].height>25]
        native_inventory=None;math_bounds=[]
        if kind=='TS':
            # MathType can paint a whole compound fraction as one large
            # graphical path. Its physical extent is not a figure/table.
            from izho_native_atomic_tokens import _inventory
            proof=ROOT/f'tmp/original-style-repair/{year}/{kind}/page{number}.pdf'
            stat=proof.stat();native_inventory=_inventory(str(proof.resolve()),1,stat.st_mtime_ns,stat.st_size)
            for group in native_inventory['forms']:
                box=fitz.Rect()
                for glyph in group['glyphs']:
                    if glyph['c'].strip():box|=fitz.Rect(glyph['bbox'])
                physical=fitz.Rect(group.get('native_page_bbox',box))
                if physical.width<320 and physical.height<70:math_bounds.append(physical+(-.1,-.1,.1,.1))
            figures=[r for r in figures if not any(box.contains(fitz.Rect(r))for box in math_bounds)]
        separators=[]
        if kind=='TS':
            for drawing in page.get_drawings():
                # Word often paints an entire grading table as one compound
                # path. Its overall bbox hides each vertical cell boundary.
                # Inspect the real line/rectangle primitives, not that bbox.
                segments=[fitz.Rect(drawing['rect'])]
                for primitive in drawing['items']:
                    if primitive[0]=='l':
                        a,b=primitive[1:3];segments.append(fitz.Rect(min(a.x,b.x),min(a.y,b.y),max(a.x,b.x),max(a.y,b.y)))
                    elif primitive[0]=='re':
                        r=fitz.Rect(primitive[1]);segments.extend([fitz.Rect(r.x0,r.y0,r.x0,r.y1),fitz.Rect(r.x1,r.y0,r.x1,r.y1)])
                for r in segments:
                    # Single-line grading rows can be only 15–20pt high;
                    # their short original cell borders still divide columns.
                    if r.width<.5 and r.height>10 and not any(box.contains(r)for box in math_bounds):
                        candidate=[r.x0,r.y0,r.y1]
                        if candidate not in separators:separators.append(candidate)
        content_right=max(v['rect'][2]for v in work if v['baseline']>60)
        regions=[];deferred=[]
        for y in sorted(baselines):
            items=[v for v in work if abs(v['baseline']-y)<baseline_tolerance]
            if y<60:
                deferred.append(dict(baseline=y,reason='Header underline needs an independent actual-ink overlap review before horizontal movement.'))
                continue
            size=max(v['size']for v in items);intervals=[]
            for v in items:intervals.append(dict(x0=v['rect'][0],x1=v['rect'][2],slots=[v]))
            for c in native:
                dy=abs(c['origin'][1]-y)
                if dy<(.55*size if c['size']<.85*size else .15*size):
                    intervals.append(dict(x0=c['bbox'][0],x1=c['bbox'][2],slots=[]))
            if native_inventory:
                for group in native_inventory['forms']:
                    glyphs=[g for g in group['glyphs']if g['c'].strip()]
                    if not glyphs:continue
                    box=fitz.Rect(group.get('native_page_bbox',glyphs[0]['bbox']))
                    anchored=any(.7*size<=g['size']<=1.45*size and abs(g['origin'][1]-y)<.35*size for g in glyphs)
                    if anchored and box.width<320 and box.height<70:
                        # The whole native fraction/root expression is one
                        # interval even if its internal font advances are wide.
                        intervals.append(dict(x0=box.x0,x1=box.x1,slots=[]))
            intervals.sort(key=lambda r:r['x0']);groups=[]
            for interval in intervals:
                if groups and interval['x0']-groups[-1]['x1']<=.9*size:
                    groups[-1]['x1']=max(groups[-1]['x1'],interval['x1']);groups[-1]['slots'].extend(interval['slots'])
                else:groups.append(dict(interval))
            for gi,group in enumerate(groups):
                if not group['slots']:continue
                slots=group['slots'];rect=[group['x0']-1,y-.65*size,group['x1']+1,y+.43*size]
                # Unused original paragraph background is available for a
                # faithful fixed-size translation. A separate native equation,
                # column or figure still sets a hard boundary.
                limits=[content_right]
                if gi+1<len(groups):limits.append(groups[gi+1]['x0']-.25*size)
                for sx,sy0,sy1 in separators:
                    if sy0-.5<=y<=sy1+.5 and max(v['rect'][2]for v in slots)<sx-.1:
                        limits.append(sx-2)
                for obstacle in images+figures:
                    r=fitz.Rect(obstacle)
                    if r.y0<rect[3]and r.y1>rect[1]and r.x0>group['x1']:
                        limits.append(r.x0-.25*size)
                original_right=rect[2];rect[2]=max(original_right,min(limits))
                # These are source display identities with trailing prose
                # conditions, not inline paragraphs. Keep both fraction bars
                # and every mathematical glyph in their original positions.
                if(year,kind,number)==(2021,'T',6):
                    if abs(y-177)<.1:rect[0]=284.2799987792969-.05
                    elif abs(y-198)<.1:rect[0]=318.9599914550781-.05
                if(year,kind,number)==(2022,'T',7):
                    for formula_y,comment_x in[(324.84,214.2),(345.24,274.32),(364.92,308.4),(381.24,324.6)]:
                        if abs(y-formula_y)<.1:rect[0]=comment_x-.05
                # Header and grading columns stay separate even when y agrees.
                centered=[s for s in slots if s['slot'].get('align')=='center']
                centers=[]
                if y>60 and len(centered)==1 and len(slots)==1:
                    r=centered[0]['rect'];centers=[dict(baseline=round(y,3),center=(r[0]+r[2])/2)]
                regions.append(dict(rect=rect,baseline=y,centered_lines=centers,
                    original_source_ink_right=original_right,reviewed_blank_paragraph_right=rect[2],
                    source_slots=[s['slot']['at']for s in slots],
                    source_texts=[s['slot'].get('source_text',s['slot'].get('substring'))for s in slots]))
        locked_display=[[204,160,284,187],[167,185,318.5,208.5]]if(year,kind,number)==(2021,'T',6)else[]
        if(year,kind,number)==(2022,'T',7):
            locked_display=[[99,308,214.1,334],[155,331,274.2,354],[160,350,308.3,374.5],[233.5,371,324.5,385.5]]
        return dict(year=year,kind=kind,page=number,source=str(source),source_sha256=sha(source),
            original_plan=str(plan),original_plan_sha256=sha(plan),regions=regions,deferred_lines=deferred,excluded_figure_rects=images+figures,
            locked_display_equation_rects=locked_display,
            stationary_table_column_boundaries=separators,
            logical_baseline_tolerance_pt=5.1 if(year,kind,number)==(2022,'TS',4)else(.75 if kind=='TS'else.12),
            policy='Only x positions change. Exact original glyphs/font programs/point sizes/baselines and display-equation/figure positions are retained.')

def prepare(year,kind,number):
    spec=policy(year,kind,number)
    old=ROOT/f'tmp/original-style-repair/{year}/{kind}/page{number}.pdf'
    authored=json.loads(old.with_suffix('.qa.json').read_text('utf8'))['placements']
    with fitz.open(old)as doc:
        page=doc[0];lines=[];shifts=[];seen=set()
        for region in spec['regions']:
            result=plan_page(page,allowed_line_rects=[region['rect']],excluded_figure_rects=spec['excluded_figure_rects'],centered_lines=region['centered_lines'],prose_placements=authored)
            for line in result['lines']:
                for shift in line['shifts']:
                    keys={glyph_key(c)for c in shift['glyphs']}
                    if seen&keys:raise ValueError('A source glyph belongs to overlapping line regions')
                    seen.update(keys)
                lines.append(line)
            shifts.extend(result['shifts'])
    spec.update(input=str(old),input_sha256=sha(old),lines=lines,shifts=shifts)
    return spec

def build(year,kind,number):
    spec=prepare(year,kind,number);folder=OUT/str(year)/kind;folder.mkdir(parents=True,exist_ok=True)
    target=folder/f'page{number}.pdf'
    target.with_suffix('.plan.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),'utf8')
    raw,qa=reposition_inline(spec['input'],1,shifts=spec['shifts'],allow_white_background_panels=year==2022)
    target.write_bytes(raw)
    with fitz.open(spec['input'])as original,fitz.open(stream=raw,filetype='pdf')as final:
        def pixels(page):
            p=page.get_pixmap(matrix=fitz.Matrix(4,4),colorspace=fitz.csRGB,alpha=False)
            return np.frombuffer(p.samples,np.uint8).reshape(p.height,p.width,3)
        changed=np.any(pixels(original[0])!=pixels(final[0]),axis=2);allowed=np.zeros(changed.shape,bool)
        traced={}
        for tr in original[0].get_texttrace():
            for cp,gid,origin,bbox in tr['chars']:
                traced.setdefault((chr(cp),round(origin[0],4),round(origin[1],4)),[]).append(bbox)
        for shift in spec['shifts']:
            dx=shift['dx']
            # Physical trace bbox plus overhang covers both native and new
            # Korean glyph ink. Coordinates are not an erasure permission.
            for c in shift['glyphs']:
                for bbox in traced[(c['c'],round(c['origin'][0],4),round(c['origin'][1],4))]:
                    r=fitz.Rect(bbox)+(-1,-1,1,1);r|=r+(dx,0,dx,0)
                    x0,y0,x1,y1=map(int,[np.floor(r.x0*4),np.floor(r.y0*4),np.ceil(r.x1*4),np.ceil(r.y1*4)])
                    allowed[max(0,y0):max(0,y1),max(0,x0):max(0,x1)]=True
        old_origins=[c['origin']for s in spec['shifts']for c in s['glyphs']]
        new_origins=[[c['origin'][0]+s['dx'],c['origin'][1]]for s in spec['shifts']for c in s['glyphs']]
        old_actual,old_uses=native_ink_neighborhood(original[0],old_origins,4)
        new_actual,new_uses=native_ink_neighborhood(final[0],new_origins,4)
        qa['source_and_moved_actual_outline_uses_checked']=[old_uses,new_uses]
        qa['changed_actual_glyph_overhang_pixels_outside_metric_boxes']=int((changed&~allowed&(old_actual|new_actual)).sum())
        allowed|=old_actual|new_actual
        qa['changed_pixels_outside_old_and_new_glyph_envelopes']=int((changed&~allowed).sum())
        qa['unchanged_figures']=[]
        for box in spec['excluded_figure_rects']:
            r=fitz.Rect(box);x0,y0,x1,y1=map(int,[r.x0*4,r.y0*4,r.x1*4,r.y1*4])
            diff=int(changed[max(0,y0):max(0,y1),max(0,x0):max(0,x1)].sum())
            qa['unchanged_figures'].append(dict(rect=box,changed_pixels=diff))
        qa['policy']=spec['policy'];qa['input_sha256']=spec['input_sha256']
        qa['deferred_lines']=spec.get('deferred_lines',[])
        qa['visual_review_required']=True
        qa['publication_ready']=False
        qa['plan_sha256']=sha(target.with_suffix('.plan.json'))
        qa['helper_sha256']=sha(ROOT/'tools/pdf_native_inline_reposition.py')
        qa['packer_sha256']=sha(ROOT/'tools/izho_natural_spacing.py')
        final[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(target.with_suffix('.png'))
    qa['passed']=qa['passed']and qa['changed_pixels_outside_old_and_new_glyph_envelopes']==0 and not any(r['changed_pixels']for r in qa['unchanged_figures'])
    target.with_suffix('.qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),'utf8')
    if not qa['passed']:raise ValueError('Independent horizontal-spacing audit failed')
    print(json.dumps(dict(output=str(target),sha256=sha(target),lines=len(spec['lines']),shifted_groups=len(spec['shifts']),qa=qa),ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('year',type=int,choices=[2021,2022]);p.add_argument('kind',choices=['T','TS']);p.add_argument('page',type=int);p.add_argument('--plan-only',action='store_true');a=p.parse_args()
    if a.plan_only:
        folder=OUT/str(a.year)/a.kind;folder.mkdir(parents=True,exist_ok=True)
        target=folder/f'page{a.page}.plan.json';target.write_text(json.dumps(prepare(a.year,a.kind,a.page),ensure_ascii=False,indent=2),'utf8');print(target)
    else:build(a.year,a.kind,a.page)
