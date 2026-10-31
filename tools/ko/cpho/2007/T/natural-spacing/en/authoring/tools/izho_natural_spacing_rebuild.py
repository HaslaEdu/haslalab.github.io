"""Reviewed source-line scopes for natural-spacing IZhO rebuilds on D:."""
from __future__ import annotations
import argparse,hashlib,json,re
from collections import Counter
from pathlib import Path
import pymupdf as fitz
import pdf_korean_natural_composer as composer
from izho_natural_spacing import ROOT,BUILD
from pdf_korean_natural_composer import compose_page
from pdf_memory_gate import page_worker

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def inventory():return json.loads((ROOT/'tools/ko/izho/qa-original-style-new-prose-outlines.json').read_text('utf8'))['edition_audits']

def coverage(plan,composition):
    """Every regular serif Hangul body glyph must enter the replacement set."""
    from izho_natural_spacing import records,token,annotate_placements,visible
    from pdf_original_text_ops import glyph_key
    doc=fitz.open(plan['source_base']);page=doc[plan['page']-1]
    placements=composer.normalize_placements(page,plan['prose_placements']);traces={}
    for row in records(page):traces.setdefault(row['trace'],[]).append(row)
    erased={glyph_key(r)for r in composition['erased_hangul_glyphs']};eligible=[];omitted=[];italic=[]
    for rows in traces.values():
        if not any(composer._hangul(r['c'])and 'NotoSerif'in r['font']and 'Regular'in r['font']for r in rows):continue
        item=token(rows,'korean');annotate_placements([item],placements)
        p=placements[item['placement']]if 'placement'in item else None
        for row in visible(rows):
            if not composer._hangul(row['c'])or 'NotoSerif'not in row['font']or 'Regular'not in row['font']:continue
            if p is None and any(fitz.Rect(r).contains(fitz.Point(row['origin']))for r in plan['excluded_figure_rects']):continue
            if not composer._replace(row,p):italic.append(row);continue
            eligible.append(row)
            if glyph_key(row)not in erased:omitted.append(row)
    doc.close()
    result=dict(eligible_original_regular_serif_hangul=len(eligible),replaced=len(erased),
                intentionally_retained_italic_hangul=len(italic),unreplaced_regular_body_hangul=len(omitted),omitted=omitted)
    if omitted:raise ValueError(('Regular body Hangul silently outside selected line scope',result))
    return result

def _chunks(line):
    chars=[c for s in line['spans']for c in s['chars']];groups=[];current=[];spaces=[]
    for c in chars:
        if c['c'].isspace():spaces.append(c);continue
        if len(spaces)>=2 and current:groups.append(current);current=[]
        elif current:current.extend(spaces)
        spaces=[];current.append(c)
    if current:groups.append(current)
    return groups

def table_cell_bounds(drawings,x,y,full=False):
    """Recognize a cell from actual enclosing grid rules, never text spacing."""
    vertical=[];horizontal=[]
    for drawing in drawings:
        r=fitz.Rect(drawing['rect'])
        if r.width<=1.6 and r.height>=5 and r.y0<=y<=r.y1:
            vertical.append((r.x0+r.x1)/2)
        if r.height<=1.6 and r.width>=3:
            horizontal.append(((r.y0+r.y1)/2,r.x0,r.x1))
        # A grid may be one compound stroked path instead of filled rectangles.
        for item in drawing['items']:
            if item[0]!='l':continue
            a,b=item[1:3]
            if abs(a.x-b.x)<.02 and abs(a.y-b.y)>=5 and min(a.y,b.y)<=y<=max(a.y,b.y):vertical.append((a.x+b.x)/2)
            if abs(a.y-b.y)<.02 and abs(a.x-b.x)>=3:horizontal.append(((a.y+b.y)/2,min(a.x,b.x),max(a.x,b.x)))
    # Merged headings can span several smaller score cells. Their common
    # bottom rule is emitted as adjacent rectangles interrupted by separators.
    merged=[]
    for yy,a,b in sorted(horizontal):
        match=next((v for v in merged if abs(v[0]-yy)<.1 and a<=v[2]+2.1 and b>=v[1]-2.1),None)
        if match is None:merged.append([yy,a,b])
        else:match[1]=min(match[1],a);match[2]=max(match[2],b)
    horizontal=merged
    columns=[]
    for value in sorted(vertical):
        if columns and value-columns[-1]<2:continue
        columns.append(value)
    if len(columns)<3:return None
    left=max((v for v in columns if v<x-2),default=None);right=min((v for v in columns if v>x+2),default=None)
    if left is None or right is None:return None
    rules=[yy for yy,a,b in horizontal if a<=left+2 and b>=right-2 and abs(yy-y)<65]
    if not any(yy<y for yy in rules)or not any(yy>y for yy in rules):return None
    if full:return[left+.35,max(yy for yy in rules if yy<y)+.6,right-.35,min(yy for yy in rules if yy>y)-.6]
    return left+.35,right-.35

def stationary_table_math(page,scopes,drawings):
    """Original formula positions are part of the grading-table column design."""
    result=[];seen=set();traces=page.get_texttrace()
    for scope in scopes:
        cell=scope.get('original_grid_cell_rect')
        if not cell:continue
        key=tuple(round(v,3)for v in cell)
        if key in seen:continue
        seen.add(key);box=fitz.Rect(cell);bounds=fitz.Rect();count=0;native=[]
        for trace in traces:
            if not re.fullmatch(r'Cambria ?Math',trace['font']):continue
            for cp,gid,origin,bbox in trace['chars']:
                if chr(cp).isspace()or not box.contains(fitz.Point(origin)):continue
                native.append(dict(c=chr(cp),font=trace['font'],size=trace['size'],origin=list(origin)))
                if gid<0:continue
                bounds|=fitz.Rect(bbox);count+=1
        if not count:continue
        for drawing in drawings:
            r=fitz.Rect(drawing['rect'])
            if box.contains(r)and r.height<2 and r.width<box.width*.8:bounds|=r
        maximum=max(g['size']for g in native);baselines=Counter(round(g['origin'][1],3)for g in native if abs(g['size']-maximum)<.01)
        baseline=baselines.most_common(1)[0][0]
        result.append(dict(source_at=scope['source_at'],cell=cell,rect=list(bounds),glyphs=count,native_glyphs=native,baseline=baseline,
            policy='Original native score-table mathematics and fraction rules remain at exact source coordinates; prose is packed independently in adjacent gaps.'))
    return result

def split_scopes_around_math(rects,math_regions):
    result=[]
    for rect in rects:
        baseline=rect[1]+(rect[3]-rect[1])*.85/1.33
        pieces=[list(rect)]
        for region in math_regions:
            if abs(region['baseline']-baseline)>.9:continue
            box=fitz.Rect(region['rect']);next_pieces=[]
            for piece in pieces:
                if not fitz.Rect(piece).intersects(box):next_pieces.append(piece);continue
                if box.x0-.1>piece[0]+.5:next_pieces.append([piece[0],piece[1],min(piece[2],box.x0-.1),piece[3]])
                if box.x1+.1<piece[2]-.5:next_pieces.append([max(piece[0],box.x1+.1),piece[1],piece[2],piece[3]])
            pieces=next_pieces
        result.extend(pieces)
    return result

def prepare(year,kind):
    edition=next(d for d in inventory()if d['year']==year and d['kind']==kind);base=ROOT/edition['pdf']
    if sha(base)!=edition['sha256']:raise ValueError('Published base PDF SHA changed')
    old=ROOT/f'tools/ko/izho/{year}/{kind}/original_style';out=BUILD/str(year)/kind/'plans';out.mkdir(parents=True,exist_ok=True)
    override_path=old.parent/'natural_spacing-overrides.json';overrides=json.loads(override_path.read_text('utf8'))if override_path.exists()else{}
    plans=sorted(old.glob('page*.json'),key=lambda p:int(p.stem[4:]));made=[]
    for final_page,original_plan in enumerate(plans,1):
        d=json.loads(original_plan.read_text('utf8'));source=ROOT/d['source'];doc=fitz.open(source);page=doc[d['page']]
        fitz.TOOLS.set_small_glyph_heights(d.get('small_glyph_heights',True));raw=page.get_text('rawdict')
        qa_candidates=[ROOT/f'tmp/original-style-repair/{year}/{kind}/{original_plan.stem}.qa.json',ROOT/f'tmp/izho-original-style/{year}/{kind}/{original_plan.stem}.qa.json']
        oldqa=next((p for p in qa_candidates if p.exists()),None)
        if oldqa is None:raise ValueError(('Missing original placement journal',original_plan))
        q=json.loads(oldqa.read_text('utf8'));placements=q['placements']
        selected={tuple(s['at'][:2])for s in d['slots']};selected|={tuple(s['at'][:2])for s in d.get('rich_slots',[])}
        centered={tuple(s['at'][:2])for s in d['slots']if s.get('align')=='center'}
        page_override=overrides.get(str(final_page),{});centered|={tuple(v)for v in page_override.get('extra_centered_source_lines',[])}
        centered|={tuple(v[:2])for v in d.get('centered',[])};selected|=centered
        body=[(i,j,b,line)for i,b in enumerate(raw['blocks'])if not b['type']for j,line in enumerate(b['lines'])if(i,j)in selected]
        global_left=min(line['bbox'][0]for i,j,b,line in body);global_right=max(line['bbox'][2]for i,j,b,line in body)
        rects=[];centers=[];rights=[];scopes=[];display_rects=[];drawings=page.get_drawings()
        for bi,li,block,line in body:
            nonspace=[c for s in line['spans']for c in s['chars']if c['c'].strip()]
            if not nonspace:continue
            indexed=[s for s in line['spans']if ''.join(c['c']for c in s['chars']).strip()]
            indices=[s['at'][2]for s in d['slots']+d.get('rich_slots',[])if tuple(s['at'][:2])==(bi,li)]
            selected_spans=[indexed[i]for i in indices if i<len(indexed)]or indexed
            span=max(selected_spans,key=lambda s:s['size']);y=span['origin'][1];size=span['size'];text=''.join(c['c']for s in line['spans']for c in s['chars'])
            first=min(indices)if indices else 0
            lead=''.join(c['c']for c in indexed[first]['chars']).strip()if first<len(indexed)else''
            prefix=[c for s in indexed[:first]for c in s['chars']if c['c'].strip()]
            if prefix and re.match(r'^(where|here|with|for|if)\b',lead,re.I):
                box=fitz.Rect()
                for c in prefix:box|=fitz.Rect(c['bbox'])
                if box.width>=45:
                    frozen=box+(-.1,-.1,.1,.1)
                    starts=[p.get('point',p.get('origin'))[0]for p in placements if tuple((p.get('source_slot')or p.get('at')or[-1,-1])[:2])==(bi,li)and p.get('point',p.get('origin'))]
                    if starts:frozen.x1=min(frozen.x1,min(starts)-.25)
                    display_rects.append(list(frozen))
            caption_line=bool(re.match(r'^\s*(?:Figure|Fig\.?)\s*\d',text,re.I))
            groups=_chunks(line)if y<60 or caption_line else[nonspace]
            for group in groups:
                x0=min(c['bbox'][0]for c in group);x1=max(c['bbox'][2]for c in group)
                group_text=''.join(c['c']for c in group)
                is_caption=bool(re.fullmatch(r'\s*(?:Figure|Fig\.?)\s*\d+(?:[.\-]\d+)*[.)]?\s*',group_text,re.I))
                is_center=((bi,li)in centered or is_caption)and y>=60
                left=global_left if is_center else min(x0,block['bbox'][0])if y>=60 else x0
                right=global_right if is_center else max(x1,block['bbox'][2])if y>=60 else x1
                row_journal=[p for p in placements if tuple((p.get('source_slot')or p.get('at')or[-1,-1])[:2])==(bi,li)]
                if is_caption:
                    left=x0;right=x1
                    row_journal=[p for p in row_journal if x0-1<=p.get('point',p.get('origin'))[0]<=x1+1]
                if y>=60:
                    # A reviewed legacy translation may legitimately extend a
                    # ragged English line into the same column's blank space.
                    # Include its actual existing prose extent so no following
                    # Korean clause is silently omitted from the new packing.
                    for record in row_journal:
                        point=record.get('point',record.get('origin'));width=record.get('advance',record.get('width'))
                        if point is not None and width is not None:
                            left=min(left,point[0]);right=max(right,point[0]+width)
                        if record.get('frame'):
                            left=min(left,record['frame'][0]);right=max(right,record['frame'][2])
                cell=table_cell_bounds(drawings,(x0+x1)/2 if is_center else x0,y)if y>=60 else None
                if cell is not None:
                    left=max(left,cell[0]);right=min(right,cell[1])
                rect=[left-.25,y-size*.85,right+.25,y+size*.48]
                if rect in rects:continue
                cell_rect=table_cell_bounds(drawings,(x0+x1)/2 if is_center else x0,y,full=True)if cell else None
                rects.append(rect);scopes.append(dict(source_at=[bi,li],source_text=group_text,rect=rect,baseline=y,
                    original_grid_cell_bounds=cell,original_grid_cell_rect=cell_rect))
                if is_center:centers.append(dict(baseline=y,center=(x0+x1)/2 if is_caption else(line['bbox'][0]+line['bbox'][2])/2,rect=rect))
                if y<60 and re.search(r'Page\s*\d',group_text,re.I):rights.append(dict(baseline=y,right=x1,rect=rect))
        # Word can emit the last phrase of one visible line as a second block.
        # Coalesce only overlapping horizontal scopes on the same baseline;
        # disjoint columns retain their separate source anchors.
        merged=[]
        for rect in rects:
            matching=next((r for r in merged if abs((r[1]+r[3])/2-(rect[1]+rect[3])/2)<.12 and min(r[2],rect[2])>max(r[0],rect[0])),None)
            if matching is None:merged.append(list(rect));continue
            oldrect=list(matching);matching[:]=[min(matching[0],rect[0]),min(matching[1],rect[1]),max(matching[2],rect[2]),max(matching[3],rect[3])]
            for values in(centers,rights):
                for value in values:
                    if value.get('rect')in(oldrect,rect):value['rect']=list(matching)
        # A final broad source fragment can bridge several prior fragments.
        # Finish the transitive union rather than leaving overlapping claims.
        changed=True
        while changed:
            changed=False
            for i,a in enumerate(merged):
                match=next((j for j in range(i+1,len(merged))if abs((a[1]+a[3])/2-(merged[j][1]+merged[j][3])/2)<.12 and min(a[2],merged[j][2])>max(a[0],merged[j][0])),None)
                if match is None:continue
                b=merged.pop(match);old_a=list(a);a[:]=[min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3])]
                for values in(centers,rights):
                    for value in values:
                        if value.get('rect')in(old_a,b):value['rect']=list(a)
                changed=True;break
        rects=merged
        table_math=stationary_table_math(page,scopes,drawings)
        rects=split_scopes_around_math(rects,table_math)
        display_rects.extend(page_override.get('frozen_display_math_rects',[]))
        images=[list(info['bbox'])for info in page.get_image_info()if fitz.Rect(info['bbox']).width>30 and fitz.Rect(info['bbox']).height>25]
        # Mathematical inline images are deliberately not classified as figures
        # here; complete native Forms are handled by the atomic helper.
        reviewed_figures=images+display_rects
        plan=dict(year=year,kind=kind,source_base=str(base),source_base_sha256=edition['sha256'],page=final_page,
            original_english_source=str(source),original_english_source_sha256=sha(source),source_page=d['page']+1,
            source_line_scopes=scopes,allowed_line_rects=rects,centered_lines=centers,right_aligned_lines=rights,
            excluded_figure_rects=reviewed_figures,prose_placements=placements,
            frozen_display_math_rects=display_rects,
            stationary_table_math=table_math,
            policy='Batang regular Hangul at original point size; source Latin/math/CIDs and display equations remain native; natural quarter-em word spaces',
            visual_review_required=True)
        plan.update(page_override);plan['frozen_display_math_rects']=display_rects
        path=out/f'page{final_page:02d}.json';path.write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8');made.append(path);doc.close()
    print(f'Prepared {year} {kind}: {len(made)} pages',flush=True);return made

def _page_build(plan,body_only=False):
    d=json.loads(Path(plan).read_text('utf8'));source=Path(d['source_base'])
    if sha(source)!=d['source_base_sha256']:raise ValueError('Reviewed base changed')
    if body_only:d['allowed_line_rects']=[r for r in d['allowed_line_rects']if r[1]>60]
    revisions=d.get('hangul_word_revisions',[]);original_units=composer._units;applied=[]
    def reviewed_units(item,placements,metric):
        units=original_units(item,placements,metric)
        if 'placement'not in item:return units
        placement=placements[item['placement']];at=placement.get('source_slot',placement.get('at'))
        for rule in revisions:
            if at!=rule['source_at']:continue
            for unit in units:
                if unit['kind']=='batang'and unit['text']==rule['old']:
                    unit['text']=rule['new'];size=unit['style']['size'];unit['width']=sum(size/4 if c==' 'else metric.text_length(c,fontsize=size)for c in unit['text']);applied.append(rule)
        return units
    out=Path(plan).parents[1]/f'page{d["page"]:02d}{"-body"if body_only else""}.pdf'
    move_options=dict(d.get('native_move_options',{}))
    explicit=[]
    atom_rules=list(d.get('explicit_native_math_atoms',[]))
    if atom_rules:
        from pdf_native_inline_reposition import _traces
        from izho_native_atomic_tokens import _inventory
        stat=source.stat();inv=_inventory(str(source.resolve()),d['page'],stat.st_mtime_ns,stat.st_size)
        with fitz.open(source)as doc:
            rows=_traces(doc[d['page']-1])
        for rule in atom_rules:
            if rule.get('reviewed')is not True:raise ValueError('A manual mathematical atom requires review')
            box=fitz.Rect(rule['rect']);glyphs=[dict(g,gid=g['trace_gid'])for g in rows if g['c'].strip()and box.contains(fitz.Point(g['origin']))and re.search(rule['font_regex'],g['font'])]
            paths=[v for v in inv['vector_paths']if box.contains(fitz.Rect(v['rect']))and
                (not rule.get('source_grid_table_math')or(fitz.Rect(v['rect']).height<2 and fitz.Rect(v['rect']).width<box.width*.8))]
            if not glyphs:
                if rule.get('source_grid_table_math'):continue
                raise ValueError('The reviewed native atom has no original glyphs')
            bounds=fitz.Rect()
            for g in glyphs:
                if g['gid']>=0:bounds|=fitz.Rect(g['bbox'])
            for path in paths:bounds|=fitz.Rect(path['rect'])
            explicit.append(dict(kind='native',text=''.join(g['c']for g in sorted(glyphs,key=lambda g:(g['origin'][0],g['origin'][1]))),
                glyphs=glyphs,x0=bounds.x0,x1=bounds.x1,y=rule['baseline'],size=12.,fonts=sorted({g['font']for g in glyphs}),
                bbox=list(bounds),shift_kwargs=dict(vector_paths=paths),reviewed_reason=rule['reason']))
    if not body_only:
        from izho_native_atomic_tokens import _inventory
        stat=source.stat();inv=_inventory(str(source.resolve()),d['page'],stat.st_mtime_ns,stat.st_size)
        underline=[v for v in inv['vector_paths']if v['rect'][1]<60 and v['rect'][2]-v['rect'][0]>400 and v['rect'][3]-v['rect'][1]<2]
        if underline:move_options['reviewed_stationary_vector_paths']=underline
    composer._units=reviewed_units
    locked=[g for region in d.get('stationary_table_math',[])for g in region['native_glyphs']]
    try:raw,qa=compose_page(source,d['page'],native_control_output=out.with_suffix('.native-control.pdf'),native_move_options=move_options,native_atomic_tokens=explicit or None,stationary_native_glyphs=locked,include_image_only_native_math=d.get('include_image_only_native_math',False),**{k:d[k]for k in['allowed_line_rects','prose_placements','excluded_figure_rects','centered_lines','right_aligned_lines']})
    finally:composer._units=original_units
    if len(applied)!=len(revisions):raise ValueError(('Reviewed word revision was not applied exactly once',revisions,applied))
    qa['reviewed_hangul_word_revisions']=applied
    qa['native_move_options']=move_options
    qa['reviewed_explicit_native_math_atoms']=explicit
    qa['body_font_coverage']=coverage(d,qa)
    out.write_bytes(raw)
    qa['source_line_scopes']=d['source_line_scopes'];out.with_suffix('.qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf8')
    doc=fitz.open(out);doc[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(out.with_suffix('.png'));doc.close();print(out,qa['replaced_hangul_glyphs'],qa['output_sha256'],flush=True)

def page_build(plan,body_only=False):
    with page_worker():return _page_build(plan,body_only)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('year',type=int);p.add_argument('kind',choices=['T','TS']);p.add_argument('--page',type=int);p.add_argument('--prepare-only',action='store_true');p.add_argument('--body-only',action='store_true');a=p.parse_args()
    paths=prepare(a.year,a.kind)
    if not a.prepare_only:
        for path in paths:
            if a.page is None or int(path.stem[4:])==a.page:page_build(path,a.body_only)
