"""Direct-source Korean line composition with whole native expression movement.

Source English span widths are used only for identifying source glyphs. They
never reserve output space. Korean and native atoms are packed by their actual
advances, with ordinary word spaces, at the source physical line baselines.
"""
from pathlib import Path
from collections import Counter,defaultdict
from io import BytesIO
import argparse,hashlib,json,math,re,sys,zlib
import pymupdf as fitz
import pikepdf
import numpy as np
from fontTools import subset
from fontTools.ttLib import TTFont

BASE=Path(__file__).resolve().parents[1]
STYLE_ROOT=Path('D:/CodexBuilds/Hasla-poi-natural-20261102/style-corrections/icho2024-20261103')
sys.dont_write_bytecode=True
sys.path.insert(0,str(BASE/'style-engine'))
import latex_native_motion as motion
import pdf_latex_text_ops as ops
import native_ink_bounds as ink
OLD_ENGINE=BASE/'style-engine'
sys.path.append(str(OLD_ENGINE))
import native_proof as original_helpers
import prose_style_rules_icho2024 as style_rules
import prose_underline_affine_icho2024 as underline_affine
import prose_outline_geometry_icho2024_style as outline_geometry

FONT_DIR=STYLE_ROOT/'frozen/full-fonts'
FONTS={'serif':FONT_DIR/'NotoSerifCJKkr-Regular.otf','serif-bold':FONT_DIR/'NotoSerifCJKkr-Bold.otf',
       'sans':FONT_DIR/'NotoSansCJKkr-Regular.otf','sans-bold':FONT_DIR/'NotoSansCJKkr-Bold.otf'}
JOSA=re.compile(r'^(?:(?:[은는이가을를의와과도에로면며인])(?=\s|$|[,.!?;:)\]}])|(?:으로|이고|이며|이다|이면|이라|이므로|에서|에는|까지|부터|보다|처럼|만큼)|[,.!?;:)\]}])')
ACCENTS=set('ˆ^˙¨¯ˇ˘˜⃗⃖̀́̂̃̄̇̈')
ELEVATED_MATH=ACCENTS|{'√'}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def clean(text):return re.sub(r'\s+',' ',text).strip()

def font_metric(path):
    if path.suffix.lower()!='.ttc':return fitz.Font(fontfile=str(path))
    font=TTFont(path,fontNumber=0,recalcTimestamp=False);buf=BytesIO();font.save(buf);font.close()
    return fitz.Font(fontbuffer=buf.getvalue())

class FontMetrics(dict):
    """Load the identical source-matched Korean face only when requested."""
    def __init__(self,paths):super().__init__();self.paths=paths
    def __missing__(self,role):
        value=font_metric(self.paths[role]);self[role]=value;return value

def word_space(metric,size):return size/4 if metric.name.startswith('Batang')else metric.text_length(' ',fontsize=size)

def text_width(metric,text,size):
    if not metric.name.startswith('Batang'):return metric.text_length(text,fontsize=size)
    return sum(word_space(metric,size)*len(p)if p.isspace()else metric.text_length(p,fontsize=size)for p in re.split('( +)',text)if p)

def _role(name):
    sans=bool(re.search('Arial|Helvetica|CMSS|Sans',name,re.I))
    bold=bool(re.search('Bold|CMBX|CMSSBX|SFBX',name,re.I))
    return ('sans'if sans else'serif')+('-bold'if bold else'')

def _plain_source(slot,blocks):
    b,l,a,z=slot['at'];spans=blocks[b]['lines'][l]['spans'][a:z+1]
    flat=[dict(c,font=s['font'],size=s['size'],color=s['color'])for s in spans for c in s['chars']]
    chars=flat[slot.get('char_start',0):slot.get('char_end')]
    if ''.join(c['c']for c in chars)!=slot['source']:raise ValueError('Source guard '+slot['id'])
    return chars

def _glyphs(page):
    return [dict(c=chr(cp),gid=gid,font=t['font'],size=t['size'],origin=list(origin),bbox=list(bbox),paint=t['type'])
            for t in page.get_texttrace()if t['type']!=3 for cp,gid,origin,bbox in t['chars']]

def _boundary(left,right,size,metric):
    a=left.get('text','').rstrip();b=right.get('text','').lstrip()
    if not a or not b:return 0.
    if right.get('optical_gap_left_pt')is not None:return float(right['optical_gap_left_pt'])
    if right.get('join_left')or left.get('join_right'):return 0.
    if a[-1] in '([{‘“' or b[0]in',.;:!?)]}’”':return 0.
    if right['kind']=='prose'and re.match(r'^(?:점|개|가지|년|월|일|배|차|회)(?=\s|$|[은는이가을를의,.!?;:)\]}])',b):return 0.
    if a[-1]in',.;:':return word_space(metric,size)
    if right['kind']=='prose'and JOSA.match(b):return 0.
    if right['kind']=='native'and right.get('size',size)<size*.82 and right['baseline']<left['baseline']-size*.15:return 0.
    return word_space(metric,size)

def _token_bbox(glyphs):
    ink=[g for g in glyphs if g['gid']>=0 and g['c'].strip()]
    return [min(min(g['bbox'][0],g.get('native_ink_bbox',g['bbox'])[0])for g in ink),min(g['bbox'][1]for g in ink),
            max(max(g['bbox'][2],g.get('native_ink_bbox',g['bbox'])[2])for g in ink),max(g['bbox'][3]for g in ink)]

def prepare_layout(plan_path,overrides=None):
    plan=json.loads(Path(plan_path).read_text('utf-8'));source=STYLE_ROOT/'frozen/source/IChO_2024_T_EN.pdf'
    if plan['page']not in range(1,63):raise ValueError('Only root-approved IChO2024 final62 pages may run')
    plan=dict(plan,source=str(source))
    if plan.get('source_sha256')and sha(source)!=plan['source_sha256']:raise ValueError('Source hash changed')
    raster_labels=list(plan.get('raster_labels',[]));raster_manifest=None
    raster_path=Path(plan_path).parent/'raster-labels-reviewed.json'
    if raster_path.exists():
        external=json.loads(raster_path.read_text('utf-8')).get(str(plan['page']),[])
        for item in external:
            if not any(v.get('source_text')==item.get('source_text')and v.get('rect')==item.get('rect')for v in raster_labels):
                raster_labels.append(dict(item,source_font_size_basis=item.get('source_font_size_basis','Raster-only source label: font face/style and physical point size inferred from the reviewed original bitmap; exact source font metadata is unavailable.')))
        raster_manifest={'path':str(raster_path.resolve()),'sha256':sha(raster_path)}
    scopes={};scope_journal=[]
    for name in ['figure-scope-2026.json','ortvay-figure-scope-2026.json','plancks2024-panel-scope.json']:
        path=BASE/'source-review'/name
        if not path.exists():continue
        cfg=json.loads(path.read_text('utf-8'));entry={}
        if source.name==cfg.get('source'):entry=cfg.get('pages',{}).get(str(plan['page']),{})
        entry=dict(entry,**cfg.get('additional_historical_scope',{}).get(source.name+':'+str(plan['page']),{}))
        if entry:scopes.update(entry);scope_journal.append({'path':str(path),'sha256':sha(path),'entry':entry})
    scopes.update({k:plan[k]for k in ['excluded_figure_rects','fixed_native_rects','mode','prose_column_rects']if k in plan})
    scopes.update(plan.get('layout_scope',{}));scopes.update((overrides or{}).get('__layout_scope__',{}))
    doc=fitz.open(source);page=doc[plan['page']-1];blocks=page.get_text('rawdict')['blocks']
    fixed_inline_groups={}
    for b,l in scopes.get('fixed_grid_inline_source_lines',[]):
        chars=[dict(c,font=s['font'],size=s['size'],color=s['color'])for s in blocks[b]['lines'][l]['spans']for c in s['chars']]
        fixed_inline_groups[(b,l)]={ops.glyph_key(c)for c in original_helpers.canonical_selected(page,chars)}
    font_paths=dict(FONTS)
    batang=source.name.lower().startswith('ortvay_')
    if batang:
        font_paths['serif']=Path('C:/Windows/Fonts/batang.ttc')
        font_paths['serif-italic']=FONTS['serif']
    metrics=FontMetrics(font_paths)
    meta=original_helpers.font_metadata(source,plan['page']-1)
    def fontinfo(font):
        name=ops.family_name(font)
        if name in meta:return meta[name]
        # MuPDF omits TeX's numeric synthetic-slant suffix from the trace
        # family. Resolve only a unique explicit resource-name extension.
        matches=[v for k,v in meta.items()if k.startswith(name+'_')]
        if len(matches)!=1:raise ValueError('Missing or ambiguous source font metadata '+name)
        return matches[0]
    anchors={};selected_raw=[];locked_raw=[];effective_slots=[];reviewed_form_raw=[]
    reviewed_form_ids=set((overrides or{}).get('__reviewed_form_prose_slot_ids__',[]))
    slots=plan['slots']+list((overrides or{}).get('__extra_slots__',[]))
    for raw_slot in slots:
        slot=dict(raw_slot,**(overrides or{}).get('__slot_edits__',{}).get(raw_slot['id'],{}))
        if not slot.get('skip')and slot.get('text')is not None:slot['text']=clean((overrides or{}).get(slot['id'],slot['text']))
        effective_slots.append(slot)
        chars=_plain_source(slot,blocks)
        if not chars:continue
        if slot.get('skip'):
            # Authors/references and the left event masthead are not prose.
            if slot['source']=='PLANCKS 2026'or(slot['at'][0:2]==[1,2]and len(re.findall('[A-Za-z]{2,}',slot['source']))>1):locked_raw.extend(chars)
            continue
        if slot.get('text')is None:raise ValueError('Untranslated prose '+slot['id'])
        first=next((c for c in chars if c['c'].strip()),chars[0]);y=first['origin'][1]
        key=round(y,3)
        existing=next((k for k in anchors if abs(k-key)<.06),None)
        key=existing if existing is not None else key
        line=anchors.setdefault(key,{'baseline':y,'prose':[],'native':[],'source_rects':[],'source_lines':[]})
        b,l,_,_=slot['at'];line['source_rects'].append(list(blocks[b]['lines'][l]['bbox']));line['source_lines'].append([b,l])
        role=slot.get('font_role',_role(first['font']));text=clean((overrides or{}).get(slot['id'],slot['text']))
        if batang and role=='serif'and (fontinfo(first['font'])['angle']or re.search('Ital|SFTI|CMTI|CMSL',first['font'])):role='serif-italic'
        width=text_width(metrics[role],text,first['size'])
        line['prose'].append({'kind':'prose','id':slot['id'],'text':text,'old_x':first['origin'][0],
                              'source_text':slot['source'],
                              'source_right':max(c['bbox'][2]for c in chars),'width':width,'size':first['size'],
                              'baseline':y,'font_role':role,'source_font':first['font'],
                              'join_left':slot.get('join_left',False),'join_right':slot.get('join_right',False),
                              'optical_gap_left_pt':slot.get('optical_gap_left_pt'),
                              'angle':fontinfo(first['font'])['angle'],'color':first['color']})
        if source.name=='IChO_2024_T_EN.pdf'and slot['source']=='English (Official)'and first['origin'][0]>450:
            line['prose'][-1]['source_right_aligned_label']=True
        selected_raw.extend(chars)
        if slot['id']in reviewed_form_ids:reviewed_form_raw.extend(chars)
    style_journal=style_rules.apply(anchors,effective_slots,blocks,metrics,fontinfo,_plain_source,text_width,clean)
    selected=original_helpers.canonical_selected(page,selected_raw)
    selected_key_by_raw={}
    raw_nonspace=[c for c in selected_raw if not c['c'].isspace()]
    if len(raw_nonspace)!=len(selected):raise ValueError('Canonical selected source count mismatch')
    for raw,canonical in zip(raw_nonspace,selected):
        key=ops.glyph_key(raw);value=ops.glyph_key(canonical)
        if key in selected_key_by_raw and selected_key_by_raw[key]!=value:raise ValueError('Ambiguous repeated source key in reviewed cell membership')
        selected_key_by_raw[key]=value
    reviewed_form_prose=original_helpers.canonical_selected(page,reviewed_form_raw)if reviewed_form_raw else[]
    if reviewed_form_ids-{s['id']for s in effective_slots if not s.get('skip')and s.get('text')is not None}:
        raise ValueError('Reviewed Form prose slot is not an active source-bound translation')
    locked=original_helpers.canonical_selected(page,locked_raw)if locked_raw else[]
    erased=Counter(ops.glyph_key(g)for g in selected);lock={ops.glyph_key(g)for g in locked}
    selected_keys=set(erased)
    source_glyphs=_glyphs(page)
    for i,cell in enumerate(scopes.get('fixed_table_cells',[])):
        r=fitz.Rect(cell);keys={ops.glyph_key(g)for g in source_glyphs if g['c'].strip()and r.x0-.05<=g['origin'][0]<r.x1-.05 and r.y0-.05<=g['origin'][1]<=r.y1+.05}
        if keys&selected_keys:fixed_inline_groups[('table-cell',i)]=keys
    native=[]
    for g in _glyphs(page):
        k=ops.glyph_key(g)
        if erased[k]:erased[k]-=1;continue
        if not g['c'].strip()or k in lock:continue
        native.append(g)
    if any(erased.values()):raise ValueError('Selected source glyph missing')
    images=[fitz.Rect(v['bbox'])for v in page.get_image_info()]
    protected_figures=images+[fitz.Rect(r)for r in scopes.get('excluded_figure_rects',[])]+[fitz.Rect(r)for r in scopes.get('fixed_native_rects',[])]
    exclusions=protected_figures+[fitz.Rect(r)for r in scopes.get('fixed_table_rects',[])]
    fixed_header_columns=[]
    if source.name.upper().startswith('PLANCKS_')and any(l['baseline']<60 for l in anchors.values()):
        # Source running heads contain a separate right page-number column.
        # It remains fixed even when the translated middle title gets shorter.
        fixed_header_columns=[[page.rect.width-70,0,page.rect.width,60]]
        exclusions.extend(fitz.Rect(r)for r in fixed_header_columns)
    inventory=motion.inspect_inline_groups(source,plan['page'],include_text_shows=True)
    # A figure Form can contain text outside its own clipping BBox. MuPDF
    # reports that invisible text in texttrace, so geometric exclusion of only
    # visible figure labels would accidentally treat it as nearby body math.
    # Protect the complete original invocation, including clipped members.
    protected_forms=[];protected_form_keys=set()
    for form in inventory.get('forms',[]):
        box=fitz.Rect(form['native_page_bbox'])
        if box.is_empty:continue
        explicit=form['path']in scopes.get('protected_form_paths',[])
        if not explicit and not any((box&rect).get_area()>=box.get_area()*.8 for rect in exclusions):continue
        protected_forms.append({'path':form['path'],'native_page_bbox':list(box),'glyph_count':len(form['glyphs'])})
        protected_form_keys.update(ops.glyph_key(g)for g in form['glyphs'])
    if (protected_form_keys&{ops.glyph_key(g)for g in selected})-{ops.glyph_key(g)for g in reviewed_form_prose}:
        raise ValueError('Selected prose belongs to a protected native figure Form')
    for line in anchors.values():line['is_running_header']=source.name.upper().startswith('PLANCKS_')and line['baseline']<60
    body_right=max((r[2]for line in anchors.values()if not line['is_running_header']and max(p['size']for p in line['prose'])<=13 for r in line['source_rects']),default=page.rect.width-36)
    header_right=max((r[2]for line in anchors.values()if line['is_running_header']for r in line['source_rects']),default=body_right)
    for line in anchors.values():
        rr=line['source_rects'];bounds=[min(r[0]for r in rr),min(r[1]for r in rr),max(r[2]for r in rr),max(r[3]for r in rr)]
        if line['is_running_header']:line['header_title_center']=(bounds[0]+bounds[2])/2
        explicit=[r for r in plan.get('allowed_prose_line_rects',[])if abs(r['baseline']-line['baseline'])<.06]
        if explicit:
            if len(explicit)!=1:raise ValueError('Ambiguous authored line-column bounds')
            bounds=list(explicit[0]['rect'])
        line['source_bounds']=bounds;line['output_right']=body_right
        if line['is_running_header']:line['output_right']=page.rect.width-70
        line['source_english_bounds']=list(bounds)
        if not line['is_running_header']and not explicit:line['source_bounds'][2]=line['output_right']
        for rect in scopes.get('prose_column_rects',[]):
            if rect[1]<=line['baseline']<=rect[3]and bounds[0]>=rect[0]-.5 and bounds[0]<rect[2]:
                line['output_right']=rect[2];line['source_bounds']=[max(bounds[0],rect[0]),bounds[1],min(bounds[2],rect[2]),bounds[3]]
    def inside_line(g,line):
        r=line['source_bounds'];x,y=g['origin']
        script_pad=max(p['size']for p in line['prose'])*.4
        if re.search('CMEX',g['font'])and g.get('native_ink_bbox'):
            inkbox=g['native_ink_bbox']
            return r[0]-.7<=x<=r[2]+.7 and inkbox[1]<=r[3]+script_pad and inkbox[3]>=r[1]-script_pad
        return r[0]-.7<=x<=r[2]+.7 and r[1]-script_pad<=y<=r[3]+script_pad
    # Seed exact full-size baselines, then grow scripts through nearby native
    # glyphs. A global connected component can incorrectly bridge adjacent
    # lines through one subscript and the next line's superscript.
    reviewed_inline_keys=set().union(*fixed_inline_groups.values())if fixed_inline_groups else set()
    eligible=[g for g in native if ops.glyph_key(g)not in protected_form_keys and (ops.glyph_key(g)in reviewed_inline_keys or not any(rect.intersects(fitz.Rect(g['bbox']))for rect in exclusions))]
    if scopes.get('mode')in['fixed-cover','fixed-toc-grid']:
        eligible=[g for g in eligible if ops.glyph_key(g)in reviewed_inline_keys]
    outline_candidates=[g for g in eligible if re.search('CMEX',g['font'])or any(inside_line(g,l)for l in anchors.values())]
    native_ink=ink.measure_native_ink_bounds(source,plan['page'],outline_candidates,inventory=inventory)
    for g in outline_candidates:g['native_ink_bbox']=native_ink[ops.glyph_key(g)]
    assigned={}
    for i,g in enumerate(eligible):
        choices=[]
        for key,line in anchors.items():
            size=max(p['size']for p in line['prose']);dy=abs(g['origin'][1]-line['baseline'])
            if not inside_line(g,line):continue
            if re.search('CMEX',g['font']):
                ib=g.get('native_ink_bbox',g['bbox'])
                if not ib[1]<=line['baseline']<=ib[3]:continue
            if g['c']in ELEVATED_MATH or g['size']<size*.90 or dy>size*.14:continue
            if line['is_running_header']and g['origin'][0]<line['source_bounds'][0]-.7:continue
            if size>13 and g['origin'][0]<min(p['old_x']for p in line['prose'])-1:continue
            choices.append((dy,key))
        if choices:assigned[i]=min(choices)[1]
    while True:
        choices=[]
        for i,g in enumerate(eligible):
            if i in assigned:continue
            for j,key in assigned.items():
                other=eligible[j];line=anchors[key];size=max(p['size']for p in line['prose'])
                if not inside_line(g,line):continue
                native_script=(re.search(r'CM(?:MI|SY|R)|Math|Symbol',g['font'])and abs(g['origin'][1]-line['baseline'])<=size*.7)
                if g['size']>=size*.90 and not re.search('CMEX',g['font'])and g['c']not in ELEVATED_MATH and not native_script:continue
                gb=g.get('native_ink_bbox',g['bbox']);ob=other.get('native_ink_bbox',other['bbox'])
                gap=max(gb[0]-ob[2],ob[0]-gb[2],0)
                dy=abs(g['origin'][1]-other['origin'][1])
                if re.search('CMEX',g['font']+' '+other['font']):dy=max(gb[1]-ob[3],ob[1]-gb[3],0)
                horizontal_pad=size*1.25 if re.search(r'CM(?:MI|SY|EX|R)|Math|Symbol',g['font'])else size*.66
                if gap<=horizontal_pad and dy<=size*.98:
                    choices.append((gap+dy*2,i,key))
        if not choices:break
        _,i,key=min(choices);assigned[i]=key
    for i,g in enumerate(eligible):
        if i in assigned:continue
        choices=[]
        for key,line in anchors.items():
            size=max(p['size']for p in line['prose']);dy=abs(g['origin'][1]-line['baseline'])
            if not inside_line(g,line):continue
            if g['size']<size*.90 and dy<=size*.66:choices.append((dy,key))
        if choices:assigned[i]=min(choices)[1]
    orphan_math=[g for i,g in enumerate(eligible)if i not in assigned
                 and re.search(r'CM(?:MI|SY|EX|R)|Math|Symbol',g['font'])
                 and not any(fitz.Rect(cell).contains(fitz.Point(g['origin']))for cell in scopes.get('fixed_table_cells',[]))
                 and any(inside_line(g,line)for line in anchors.values())]
    if orphan_math:
        raise ValueError('Unassigned native math inside an authored prose line: '+str([(g['c'],g['font'],g['origin'])for g in orphan_math[:8]]))
    for i,key in assigned.items():anchors[key]['native'].append(eligible[i])
    paths=inventory.get('vector_paths',[]);claimed_paths={tuple(v['source_prose_decoration_program']['source_operator_indices'])for v in style_rules.mapping_rows(plan['page'])};shifts=[];placements=[];line_reports=[]
    optical_adjustments=plan.get('native_gap_adjustments',[])+list((overrides or{}).get('__native_gap_adjustments__',[]));optical_used=Counter()
    line_offsets=plan.get('line_optical_offsets',[])+list((overrides or{}).get('__line_optical_offsets__',[]));line_offsets_used=Counter()
    for line in sorted(anchors.values(),key=lambda l:l['baseline']):
        size=max(p['size']for p in line['prose']);prose=line['prose'];rows=sorted(line['native'],key=lambda g:(g['bbox'][0],g['origin'][1]))
        chunks=[]
        for g in rows:
            x0=g['bbox'][0];x1=g['bbox'][2]
            # Prose runs divide native atoms even when their translated text is empty.
            structural_prefix=bool(chunks and chunks[-1]['glyphs'][-1]['c']=='.'and g['c']=='['and abs(chunks[-1]['glyphs'][-1]['origin'][1]-g['origin'][1])<.1)
            intervening=bool(chunks and any(chunks[-1]['last_origin_x']<p['old_x']<g['origin'][0]-.01 for p in prose))or structural_prefix
            if chunks and not intervening:
                chunks[-1]['glyphs'].append(g);chunks[-1]['right']=max(chunks[-1]['right'],x1);chunks[-1]['last_origin_x']=max(chunks[-1]['last_origin_x'],g['origin'][0])
            else:chunks.append({'glyphs':[g],'right':x1,'last_origin_x':g['origin'][0]})
        tokens=[]
        for ch in chunks:
            origins=[g['origin'][0]for g in ch['glyphs']]
            if any(min(origins)+.01<p['old_x']<max(origins)-.01 for p in prose):
                raise ValueError('A native expression encloses an authored source-prose seam')
            box=_token_bbox(ch['glyphs']);original_order=sorted(ch['glyphs'],key=lambda g:next(i for i,v in enumerate(native)if v is g))
            token={'kind':'native','glyphs':original_order,'text':''.join(g['c']for g in original_order),
                   'bbox':box,'old_x':box[0],'width':box[2]-box[0],
                   'baseline':min(ch['glyphs'],key=lambda g:-g['size'])['origin'][1],
                   'size':max(g['size']for g in ch['glyphs']),'vector_paths':[]}
            for oi,adjustment in enumerate(optical_adjustments):
                if any(g['c']==adjustment['c']and max(abs(a-b)for a,b in zip(g['origin'],adjustment['origin']))<.0002 for g in original_order):
                    if not 0<=adjustment['gap']<=word_space(metrics['serif'],size):raise ValueError('Optical gap exceeds an ordinary word space')
                    token['optical_gap_left_pt']=adjustment['gap'];token['optical_gap_review']=adjustment;optical_used[oi]+=1
            # A fraction/radical path must be wholly in this exact expression.
            for path in paths:
                k=tuple(path['operator_indices']);r=path['rect']
                if k in claimed_paths:continue
                if any(ex.intersects(fitz.Rect(r)+(-.1,-.1,.1,.1))for ex in exclusions):continue
                rule_pad=max(.7,size*.15)if r[3]-r[1]<=size*.1 and r[2]-r[0]>=size*.6 else .7
                if box[0]-rule_pad<=r[0] and r[2]<=box[2]+rule_pad and box[1]-.7<=r[1] and r[3]<=box[3]+.7:
                    token['vector_paths'].append(path);claimed_paths.add(k)
            style_rules.attach_reviewed_inline_atom(plan['page'],token,paths,claimed_paths)
            if token['vector_paths']:
                left=min([box[0]]+[p['rect'][0]for p in token['vector_paths']])
                right=max([box[2]]+[p['rect'][2]for p in token['vector_paths']])
                token['old_x']=left;token['width']=right-left;token['bbox']=[left,box[1],right,box[3]]
            tokens.append(token)
        tokens+=prose;tokens.sort(key=lambda t:t['old_x'])
        tokens=style_rules.permute_line(plan['page'],line,tokens)
        for token in tokens if fixed_inline_groups else[]:
            if token['kind']=='native':
                keys={ops.glyph_key(g)for g in token['glyphs']}
                groups=[group for group,allowed in fixed_inline_groups.items()if keys<=allowed]
            else:
                slot=next(s for s in effective_slots if s['id']==token.get('original_source_slot_id',token['id']))
                keys={selected_key_by_raw[ops.glyph_key(c)]for c in _plain_source(slot,blocks)if c['c'].strip()}
                groups=[group for group,allowed in fixed_inline_groups.items()if keys and keys<=allowed]
            if len(groups)>1:raise ValueError('Ambiguous reviewed fixed-cell inline group')
            if groups:token['fixed_cell_inline_group']=list(groups[0])
        line['tokens']=tokens
    original_prose={t['id']:t['text']for line in anchors.values()for t in line['prose']}
    paragraph_flow=[]
    def pack(nonempty,start,size,fixed_cells,line_metric):
        cursor=start;gaps=[];prepared=[]
        for i,t in enumerate(nonempty):
            gap=_boundary(nonempty[i-1],t,size,line_metric)if i else 0.
            joined_cell=(i and t.get('fixed_cell_inline_group')is not None and t.get('fixed_cell_inline_group')==nonempty[i-1].get('fixed_cell_inline_group'))
            if t.get('source_right_aligned_label'):
                if i or len(nonempty)!=1:raise ValueError('Source language masthead must be one independent label')
                cursor=t['source_right']-t['width'];gap=0.
            elif fixed_cells and not joined_cell:cursor=t['old_x'];gap=cursor-(prepared[-1][1]+prepared[-1][0]['width'])if prepared else 0.
            else:cursor+=gap
            prepared.append((t,cursor));cursor+=t['width']
            if i:gaps.append({'left':nonempty[i-1]['text'],'right':t['text'],
                               'old_gap':t['old_x']-(nonempty[i-1]['old_x']+nonempty[i-1].get('width',0)),
                               'new_gap':gap,'ordinary_space':word_space(line_metric,size)})
        return cursor,gaps,prepared
    ordered_lines=sorted(anchors.values(),key=lambda l:l['baseline'])
    for li,line in enumerate(ordered_lines):
        tokens=line.get('carried_prose',[])+line['tokens']
        size=max(p['size']for p in line['prose'])
        nonempty=[t for t in tokens if t['kind']=='native'or t['text']]
        if not nonempty:continue
        start=min(t['old_x']for t in line['tokens'])
        fixed_cells=((scopes.get('mode')in['fixed-cover','fixed-toc-grid']and not line['is_running_header'])
                     or any(t.get('fixed_cell_inline_group',[None])[0]=='table-cell'for t in nonempty)
                     or any(r[1]<=line['baseline']<=r[3]and line['source_bounds'][0]>=r[0]and line['source_bounds'][2]<=r[2]for r in scopes.get('fixed_native_rects',[]))
                     or any(abs(y-line['baseline'])<.01 for y in scopes.get('fixed_prose_baselines',[])))
        boundary_role=max(line['prose'],key=lambda p:len(p['text']))['font_role']
        cursor,gaps,prepared=pack(nonempty,start,size,fixed_cells,metrics[boundary_role])
        right=line['output_right'];adjust=line['header_title_center']-(start+cursor)/2 if line['is_running_header']else 0.
        source_centered={tuple(v)for v in scopes.get('centered_source_lines',[])}
        matched=source_centered&{tuple(v)for v in line['source_lines']}
        if matched:
            if len(matched)!=1 or {tuple(v)for v in line['source_lines']}!=matched:raise ValueError('Centered caption scope crosses independent source lines')
            b,l=next(iter(matched));r=blocks[b]['lines'][l]['bbox']
            left=min(x for t,x in prepared);finish=max(x+t['width']for t,x in prepared)
            adjust+=(r[0]+r[2]-left-finish)/2
            line['source_caption_centering']={'source_line':[b,l],'source_rect':list(r),'source_center_x':(r[0]+r[2])/2,'translated_group_center_before_alignment':(left+finish)/2,'dx':adjust}
        for oi,entry in enumerate(line_offsets):
            if abs(entry['baseline']-line['baseline'])<.0002:
                if abs(entry['dx'])>size*.4:raise ValueError('Optical row adjustment exceeds 0.4em')
                adjust+=entry['dx'];line_offsets_used[oi]+=1
        if cursor+adjust>right+.05 and not fixed_cells and not line['is_running_header']and li+1<len(ordered_lines):
            following=ordered_lines[li+1];tail=nonempty[-1]
            same_paragraph=any([b,l+1]in following['source_lines']for b,l in line['source_lines'])
            # MuPDF can split one source paragraph into blocks at an inline
            # style change. A lower-case English continuation at the normal
            # source leading is still the same paragraph; a new numbered
            # question/heading or paragraph gap cannot receive carried text.
            last_source=max(line['prose'],key=lambda t:t['old_x'])['source_text'].rstrip()
            first_source=min(following['prose'],key=lambda t:t['old_x'])['source_text'].lstrip()
            if (following['baseline']-line['baseline']<=size*1.65 and last_source and last_source[-1].isalnum()
                    and re.match('[a-z]',first_source)):
                same_paragraph=True
            compatible=(same_paragraph and 0<following['baseline']-line['baseline']<=size*2.2
                        and abs(following['output_right']-right)<.01 and not following['is_running_header']
                        and max(p['size']for p in following['prose'])==size)
            if compatible and tail['kind']=='prose':
                # Korean permits line breaks between syllables. Keep Latin
                # words intact and avoid stranding punctuation. All native
                # glyphs/paths retain their original physical baseline.
                full=tail['text'];prefix='';suffix=full;cut=0
                metric=metrics[tail['font_role']];available=right-adjust-prepared[-1][1]
                for n in range(1,len(full)):
                    legal=(full[n-1].isspace()or full[n].isspace()or
                           ('가'<=full[n-1]<='힣'and '가'<=full[n]<='힣'))
                    if not legal or full[n-1]in'([{‘“'or full[n]in',.;:!?)]}’”':continue
                    candidate=full[:n].rstrip()
                    if text_width(metric,candidate,tail['size'])<=available+.0001:
                        prefix=candidate;suffix=full[n:].lstrip();cut=n
                original_start=tail.get('target_char_start',0)
                carried=dict(tail,text=suffix,width=text_width(metric,suffix,tail['size']),
                             source_baseline=tail.get('source_baseline',tail['baseline']),baseline=following['baseline'],
                             target_char_start=original_start+cut+len(full[cut:])-len(full[cut:].lstrip()),
                             target_char_end=tail.get('target_char_end',original_start+len(full)))
                following.setdefault('carried_prose',[]).insert(0,carried)
                paragraph_flow.append({'slot_id':tail['id'],'from_baseline':line['baseline'],
                                       'to_baseline':following['baseline'],'text':suffix,'point_size':tail['size']})
                if prefix:
                    tail=dict(tail,text=prefix,width=text_width(metric,prefix,tail['size']),target_char_start=original_start,
                              target_char_end=original_start+len(prefix));nonempty[-1]=tail
                else:nonempty.pop()
                cursor,gaps,prepared=pack(nonempty,start,size,False,metrics[boundary_role])
        if cursor+adjust>right+.05:raise ValueError(f"Full natural line overflow at {line['baseline']}: {cursor+adjust:.2f} > {right:.2f}; paragraph prose needs line-level authoring, never shrink")
        # A Korean particle/suffix from the next source row can complete the
        # native expression on this row. Pull only prose, never a native atom;
        # every painted baseline is still an original source paragraph row.
        if nonempty and nonempty[-1]['kind']=='native'and not fixed_cells and not line['is_running_header']and li+1<len(ordered_lines):
            following=ordered_lines[li+1]
            same=any([b,l+1]in following['source_lines']for b,l in line['source_lines'])
            next_tokens=following.get('carried_prose',[])+following['tokens']
            head=next((t for t in next_tokens if t['kind']=='native'or t['text']),None)
            compatible=(same and 0<following['baseline']-line['baseline']<=size*1.65
                        and not following['is_running_header']and abs(following['output_right']-right)<.01
                        and max(p['size']for p in following['prose'])==size)
            if compatible and head and head['kind']=='prose'and (head.get('join_left')or JOSA.match(head['text'])or re.match(r'^(?:개|점|년|차|회)[은는이가을를의]',head['text'])):
                full=head['text'];metric=metrics[head['font_role']];chosen=None
                original_start=head.get('target_char_start',0)
                for n in range(1,len(full)+1):
                    legal=(n==len(full)or full[n-1].isspace()or full[n].isspace()or ('가'<=full[n-1]<='힣'and '가'<=full[n]<='힣'))
                    if not legal or full[n-1]in'([{‘“'or(n<len(full)and full[n]in',.;:!?)]}’”'):continue
                    prefix=full[:n].rstrip()
                    pulled=dict(head,text=prefix,width=text_width(metric,prefix,head['size']),baseline=line['baseline'],
                                source_baseline=head.get('source_baseline',head['baseline']),target_char_start=original_start,target_char_end=original_start+len(prefix))
                    trial=pack(nonempty+[pulled],start,size,False,metrics[boundary_role])
                    if trial[0]+adjust<=right+.0001:chosen=(n,pulled,trial)
                if chosen:
                    n,pulled,(cursor,gaps,prepared)=chosen;nonempty.append(pulled)
                    suffix=full[n:].lstrip();head['text']=suffix;head['width']=text_width(metric,suffix,head['size'])
                    head['target_char_start']=original_start+n+len(full[n:])-len(suffix)
                    head.setdefault('target_char_end',original_start+len(full))
                    paragraph_flow.append({'kind':'native-suffix-backfill','slot_id':head['id'],
                                           'from_baseline':following['baseline'],'to_baseline':line['baseline'],
                                           'text':pulled['text'],'point_size':head['size']})
        for index,(t,x)in enumerate(prepared):
            x+=adjust
            if t['kind']=='prose':
                entry=dict(t,point=[x,t['baseline']],advance=t['width'])
                # Emit actual ordinary spaces in the text layer as well as
                # reserving their metric advance in the visual line.
                if index and gaps[index-1]['new_gap']>.9*gaps[index-1]['ordinary_space']and not fixed_cells:
                    sw=word_space(metrics[t['font_role']],t['size']);entry['draw_text']=' '+t['text'];entry['draw_point']=[x-sw,t['baseline']]
                placements.append(entry)
            else:
                dx=x-t['old_x']
                if abs(dx)>.0001:shifts.append({'glyphs':t['glyphs'],'dx':dx,'vector_paths':t['vector_paths']})
        line_reports.append({'baseline':line['baseline'],'size':size,'left':start+adjust,'right':cursor+adjust,'source_bounds':line['source_bounds'],'fixed_design_cells':fixed_cells,
                             'source_line_right':max(t.get('source_right',t['old_x']+t['width'])for t in tokens),
                             'gaps':gaps,'tokens':[{'kind':t['kind'],'text':t['text'],'old_x':t['old_x'],'new_x':x+adjust,'width':t['width']}for t,x in prepared]})
    if any(optical_used[i]!=1 for i in range(len(optical_adjustments))):raise ValueError('Optical source-glyph journal did not match exactly once')
    if any(line_offsets_used[i]!=1 for i in range(len(line_offsets))):raise ValueError('Optical source-baseline journal did not match exactly once')
    for id,text in original_prose.items():
        cursor=0
        for p in sorted((p for p in placements if p['id']==id),key=lambda p:p.get('target_char_start',0)):
            start=p.get('target_char_start',0);end=p.get('target_char_end',len(text))
            if start<cursor or text[cursor:start].strip()or text[start:end]!=p['text']:
                raise ValueError('Korean paragraph reflow changed text '+id)
            cursor=end
        if text[cursor:].strip():raise ValueError('Korean paragraph reflow omitted text '+id)
    style_rules.guard_approved_reflow(paragraph_flow)
    decoration_specs=style_rules.mapping_rows(plan['page'])
    decoration_journal=[]
    for spec in decoration_specs:
        source_ref=spec['source_prose_decoration_program'];matches=[v for v in paths if v['operator_indices']==source_ref['source_operator_indices']]
        if len(matches)!=1:raise ValueError('Named original underline missing/ambiguous')
        path=matches[0]
        if path['paint_operator']!='S'or path['rect']!=source_ref['source_exact_path_rect']:raise ValueError('Exact source underline guard failed')
        targets=[p for p in placements if p.get('original_source_slot_id',p['id'])==spec['target_slot_id']and p.get('semantic_binding_index')==spec['inventory_index']]
        if len(targets)!=1 or targets[0]['text']!=spec['target_literal']:raise ValueError('Exact Korean emphasis fragment missing/ambiguous')
        p=targets[0]
        if p['baseline']!=spec['target_existing_baseline']or p['size']!=spec['target_existing_pointsize']:raise ValueError('Semantic emphasis baseline/size changed')
        metric=metrics[p['font_role']];bounds=outline_geometry.text_bounds(font_paths[p['font_role']],p['text'],p['size'],p['angle'],metric,word_space(metric,p['size']))
        tx0=p['point'][0]+bounds[0];tx1=p['point'][0]+bounds[2];r=path['rect']
        decoration_journal.append(dict(id='icho2024-semantic-underline-'+str(spec['inventory_index']),slot_id=p['id'],original_source_slot_id=spec['source_slot_id'],target_text=p['text'],source_baseline=spec['source_guard']['source_prose_baseline'],operator_indices=path['operator_indices'],paint_operator='S',source_rect=r,source_path_index=paths.index(path),target_rect=[tx0,r[1],tx1,r[3]],dx=(tx0+tx1-r[0]-r[2])/2,x_scale=(tx1-tx0)/(r[2]-r[0]),semantic_mapping_index=spec['inventory_index'],source_program=source_ref,target_font_role=p['font_role'],target_pointsize=p['size'],target_baseline=p['baseline'],target_full_font_path=str(font_paths[p['font_role']]),target_full_font_sha256=sha(font_paths[p['font_role']]),target_full_font_curve_relative_bounds=bounds,source_construction_and_paint_bytes_preserved=True))
    caption_overlaps=[]
    for spec in scopes.get('allowed_raster_caption_slots',[]):
        rect=fitz.Rect(spec['source_image_rect'])
        if not any(max(abs(a-b)for a,b in zip(rect,r))<.001 for r in images):raise ValueError('Reviewed caption source-image guard failed')
        matches=[s for s in effective_slots if s['id']==spec['slot_id']]
        ps=[p for p in placements if p['id']==spec['slot_id']]
        if len(matches)!=1 or not ps or any(abs(p['baseline']-spec['source_baseline'])>.001 for p in ps):raise ValueError('Reviewed caption source-baseline guard failed')
        original=original_helpers.canonical_selected(page,_plain_source(matches[0],blocks))
        bounds=ink.measure_native_ink_bounds(source,plan['page'],[g for g in original if g['c'].strip()])
        if not any(fitz.Rect(r).intersects(rect)for r in bounds.values()):raise ValueError('Source caption did not actually overlap its raster canvas')
        caption_overlaps.append(dict(spec,original_caption_outline_overlap_verified=True))
    moving={ops.glyph_key(g)for s in shifts for g in s['glyphs']}
    stationary_figure=[g for g in native if ops.glyph_key(g)in protected_form_keys or any(rect.intersects(fitz.Rect(g['bbox']))for rect in protected_figures)
                       or(ops.glyph_key(g)not in reviewed_inline_keys and any(fitz.Rect(r).intersects(fitz.Rect(g['bbox']))for r in scopes.get('fixed_table_rects',[])))]
    stationary_display=[g for g in native if re.search(r'CM(?:MI|SY|EX)|MS[AB]M|Math|Symbol',g['font'])and not any(inside_line(g,l)for l in anchors.values())and g not in stationary_figure]
    if moving&{ops.glyph_key(g)for g in stationary_figure+stationary_display}:raise ValueError('A diagram/display glyph was requested to move')
    out={'schema':'natural-source-native-v1','source':str(source),'source_sha256':sha(source),'page':plan['page'],'plan_path':str(Path(plan_path).resolve()),'plan_sha256':sha(plan_path),
         'selected_glyphs':selected,'native_shifts':shifts,'placements':placements,'line_reports':line_reports,
         'paragraph_word_reflow':paragraph_flow,'paragraph_text_conservation_verified':True,
         'inline_native_math_assignment_complete':True,
         'native_atom_source_prose_seams_clear':True,
         'native_outline_horizontal_bounds_verified':len(native_ink),
         'native_ink_bounds_engine_sha256':sha(Path(ink.__file__)),
         'native_proof_helper_sha256':sha(Path(original_helpers.__file__)),
         'new_korean_font_subsets_retain_original_gids':True,
         'new_korean_baselines_from_original_paragraph_pool':all(any(abs(p['baseline']-g['origin'][1])<1e-6 for g in selected_raw)for p in placements),
         'prose_vector_decorations':decoration_journal,'source_semantic_style_journal':style_journal,'reviewed_inline_native_atom_path':str(style_rules.ATOM_FILE)if plan['page']==39 else None,'reviewed_inline_native_atom_sha256':style_rules.ATOM_SHA if plan['page']==39 else None,'source_semantic_mapping_sha256':style_rules.mapping_sha(),'approved_source_clause_manifest_path':str(style_rules.APP),'approved_source_clause_manifest_sha256':style_rules.APP_SHA,
         'reviewed_raster_caption_overlaps':caption_overlaps,
         'reviewed_stationary_vector_paths':scopes.get('reviewed_stationary_vector_paths',[]),
         'raster_labels':raster_labels,'reviewed_raster_label_manifest':raster_manifest,'no_reserved_english_widths':True,'no_font_shrink':True,
         'new_font_paths':{r:str(p)for r,p in font_paths.items()},'new_font_file_sha256':{r:sha(p)for r,p in font_paths.items()},
         'font_policy':'Ortvay upright regular serif: Windows Batang TTC face0; bold/sans/italic unchanged'if batang else'PLANCKS existing Noto CJK serif/sans source-style mapping unchanged',
         '_effective_plan':dict(plan,slots=effective_slots,native_gap_adjustments=optical_adjustments,line_optical_offsets=line_offsets,layout_scope=scopes,prose_vector_decorations=decoration_specs,raster_labels=raster_labels,reviewed_raster_label_manifest=raster_manifest),
         'reviewed_native_optical_gaps':optical_adjustments,
         'reviewed_line_optical_offsets':line_offsets,
         'excluded_figure_rects':[list(r)for r in protected_figures],
         'fixed_running_header_page_columns':fixed_header_columns,
         'protected_native_figure_forms':protected_forms,
         'reviewed_source_scope':scope_journal,'design_mode':scopes.get('mode','natural-prose'),
         'stationary_figure_glyphs':stationary_figure,'stationary_display_glyphs':stationary_display,
         'reviewed_form_prose_slot_ids':sorted(reviewed_form_ids),'reviewed_form_prose_glyphs':reviewed_form_prose,
         'source_form_invocations':[{'path':f['path'],'original_raw_sha256':f['original_raw_sha256'],'native_page_bbox':f['native_page_bbox']}for f in inventory.get('forms',[])],
         'source_glyph_moves_restricted_to_authored_prose_line_bounds':True,
         'stationary_display_equations_and_figures':True}
    doc.close();return out

def subset_buffer(path,text):
    # Subsetter.populate stores Unicode values in a set. Canonicalize that
    # same set so line breaks, word order and repetition reuse identical
    # font programs instead of recomputing the same subset. Keep space.
    text=''.join(sorted(set(text+' ')))
    digest=hashlib.sha256(path.read_bytes()+text.encode('utf-8')).hexdigest()[:20]
    target=BASE/'composer/font-cache'/(path.stem+'-'+digest+('.ttf'if path.suffix.lower()=='.ttc'else path.suffix))
    if target.exists():return target.read_bytes()
    font=TTFont(path,fontNumber=0 if path.suffix.lower()=='.ttc'else -1,recalcTimestamp=False);opt=subset.Options();opt.retain_gids=True;opt.name_IDs=['*'];opt.name_languages=['*']
    worker=subset.Subsetter(options=opt);worker.populate(text=text);worker.subset(font);buf=BytesIO();font.save(buf);font.close()
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(buf.getvalue());return buf.getvalue()

def compress_new_korean_font_streams(path):
    """Flate only authored Korean fonts; source streams stay byte-identical."""
    journal=[]
    with pikepdf.Pdf.open(path)as pdf:
        fonts=pdf.pages[0].Resources.get('/Font',{});seen=set()
        for resource,font in fonts.items():
            if not str(resource).startswith('/KO_Natural_'):continue
            face=font.get('/DescendantFonts',[font])[0];descriptor=face.get('/FontDescriptor',{})
            for key in['/FontFile2','/FontFile3']:
                if key not in descriptor:continue
                stream=descriptor[key]
                if stream.objgen in seen:continue
                seen.add(stream.objgen);decoded=stream.read_bytes();before=stream.read_raw_bytes();digest=hashlib.sha256(decoded).hexdigest()
                if stream.get('/Filter')is None:stream.write(zlib.compress(decoded),filter=pikepdf.Name('/FlateDecode'))
                if stream.read_bytes()!=decoded:raise ValueError('Authored font compression changed its decoded program')
                journal.append({'resource':str(resource),'key':key,'decoded_font_program_sha256':digest,'decoded_font_program_bytes_identical':True,'before_encoded_bytes':len(before),'after_encoded_bytes':len(stream.read_raw_bytes()),'scope':'Only new KO_Natural font resources; original source font/image/content streams untouched.'})
        buffer=BytesIO();pdf.save(buffer,compress_streams=False)
    Path(path).write_bytes(buffer.getvalue())
    return journal

def verify_korean_geometry(layout,page,metrics):
    expected=defaultdict(list);actual=defaultdict(list);missing_glyphs=[]
    face=lambda name:re.sub('[^a-z0-9]','',name.lower())
    for p in layout['placements']:
        metric=metrics[p['font_role']];x,y=p['point']
        for ch in p['text']:
            if not ch.isspace():expected[(ord(ch),face(metric.name),round(p['size'],4))].append((x,y))
            x+=word_space(metric,p['size'])if ch==' 'else metric.text_length(ch,fontsize=p['size'])
    for p in layout['raster_labels']:
        metric=fitz.Font(fontfile=str(FONTS[p.get('font_role','sans')]));width=metric.text_length(p['text'],fontsize=p['size'])
        x,y=p['point'];dx,dy={0:(1,0),90:(0,-1),180:(-1,0),270:(0,1)}[p.get('rotate',0)]
        if p.get('align')=='right':x-=dx*width;y-=dy*width
        for ch in p['text']:
            if not ch.isspace():expected[(ord(ch),face(metric.name),round(p['size'],4))].append((x,y))
            advance=metric.text_length(ch,fontsize=p['size']);x+=dx*advance;y+=dy*advance
    for t in page.get_texttrace():
        if not t['font'].startswith(('NotoSerifCJK','NotoSansCJK','Batang'))or t['type']==3:continue
        for cp,gid,origin,_ in t['chars']:
            if gid<=0 or cp==65533:missing_glyphs.append({'unicode':cp,'gid':gid,'font':t['font'],'origin':origin})
            if not chr(cp).isspace():actual[(cp,face(t['font']),round(t['size'],4))].append(tuple(origin))
    errors=[];maximum=0.
    for key in expected.keys()|actual.keys():
        a=expected[key];b=list(actual[key])
        if len(a)!=len(b):errors.append({'identity':key,'expected_count':len(a),'actual_count':len(b)});continue
        for want in a:
            j=min(range(len(b)),key=lambda j:max(abs(v-w)for v,w in zip(want,b[j])))
            got=b.pop(j)
            delta=max(abs(v-w)for v,w in zip(want,got));maximum=max(maximum,delta)
            if delta>.001:errors.append({'identity':key,'expected':want,'actual':got,'delta':delta})
    return {'planned_glyphs':sum(map(len,expected.values())),'actual_glyphs':sum(map(len,actual.values())),
            'missing_or_notdef_glyphs':missing_glyphs,'geometry_errors':errors,'max_position_error_pt':maximum,
            'position_tolerance_pt':.001,'passed':not errors and not missing_glyphs}

def assert_natural_gaps(layout):
    count=0
    for line in layout['line_reports']:
        if line.get('fixed_design_cells'):continue
        tokens=line['tokens']
        for left,right,gap in zip(tokens,tokens[1:],line['gaps']):
            actual=right['new_x']-(left['new_x']+left['width'])
            if abs(actual-gap['new_gap'])>.00001:raise ValueError('Placement does not match authored natural gap')
            if actual<-.00001 or actual>gap['ordinary_space']+.00001:
                raise ValueError('Source English width reserved between natural tokens')
            count+=1
    return count

def insert_prose_text(page,point,text,fontname,size,color,angle=0):
    """Keep the new text matrix precise, including a shear about its baseline.

    MuPDF's default five-decimal shear serialization can introduce a visible
    origin offset when it cancels a translation hundreds of points away.
    Only this newly inserted stream is replaced; source streams are untouched.
    """
    shear=math.tan(math.radians(angle))
    morph=(point,fitz.Matrix(1,0,shear,1,0,0))if angle else None
    previous=page.get_contents()
    page.insert_text(point,text,fontname=fontname,fontsize=size,color=color,morph=morph)
    created=[v for v in page.get_contents()if v not in previous and b'/'+fontname.encode('ascii')+b' 'in page.parent.xref_stream(v)]
    if len(created)!=1:raise ValueError('New prose stream ownership is ambiguous')
    xref=created[0];data=page.parent.xref_stream(xref)
    pdf_point=point*~page.transformation_matrix
    number=rb'[-+]?(?:\d+(?:\.\d*)?|\.\d+)'
    if angle:
        pattern=rb'1 0 '+number+rb' 1 '+number+rb' '+number+rb' cm'
        value=f'1 0 {shear:.12f} 1 {-shear*pdf_point.y:.12f} 0 cm'.encode('ascii')
        data,count=re.subn(pattern,value,data)
        if count!=1:raise ValueError('New prose shear matrix is ambiguous')
    value=f'1 0 0 1 {pdf_point.x:.12f} {pdf_point.y:.12f} Tm'.encode('ascii')
    data,count=re.subn(rb'1 0 0 1 '+number+rb' '+number+rb' Tm',value,data)
    if count!=1:raise ValueError('New prose text matrix is ambiguous')
    font_token=b'/'+fontname.encode('ascii')
    data,count=re.subn(re.escape(font_token)+rb' '+number+rb' Tf',font_token+f' {size:.12f} Tf'.encode('ascii'),data)
    if count!=1:raise ValueError('New prose physical font size ownership is ambiguous')
    page.parent.update_stream(xref,data)

def build(plan_path,target,overrides=None,overrides_path=None):
    layout=prepare_layout(plan_path,overrides);target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    effective_path=target.with_suffix('.effective-plan.json');effective_path.write_text(json.dumps(layout.pop('_effective_plan'),ensure_ascii=False,indent=2),'utf-8')
    layout['effective_plan_path']=str(effective_path.resolve());layout['effective_plan_sha256']=sha(effective_path)
    layout['overrides_path']=str(Path(overrides_path).resolve())if overrides_path else None
    layout['overrides_sha256']=sha(overrides_path)if overrides_path else None
    layout['composer_path']=str(Path(__file__).resolve());layout['composer_sha256']=sha(Path(__file__));layout['native_motion_engine_sha256']=sha(Path(motion.__file__))
    layout['ordinary_gap_boundaries_verified']=assert_natural_gaps(layout)
    moved,motion_qa=motion.reposition_inline(Path(layout['source']),layout['page'],erased_glyphs=[],shifts=layout['native_shifts'],text_shift_mode='ctm',reviewed_stationary_vector_paths=layout['reviewed_stationary_vector_paths'])
    original_moved_sha=hashlib.sha256(moved).hexdigest()
    moved,affine_audit=underline_affine.apply(moved,Path(layout['source']),layout['page'],layout['prose_vector_decorations'])
    layout['source_prose_underline_affine_audit']=affine_audit
    layout['native_motion_before_prose_underline_affine_sha256']=original_moved_sha
    moved_path=target.with_suffix('.moved.pdf');moved_path.write_bytes(moved)
    form_edits=[]
    hidden,removed=ops.suppress_prose(moved_path,1,layout['selected_glyphs'],allowed_form_prose_glyphs=layout.get('reviewed_form_prose_glyphs',[]),form_edit_audit=form_edits)
    for edit in form_edits:
        matches=[f for f in layout['source_form_invocations']if f['original_raw_sha256']==edit['source_raw_stream_sha256']]
        if len(matches)!=1:raise ValueError('Reviewed Form prose edit lacks one exact original source invocation')
        edit['suppression_input_form_path']=edit['source_form_path'];edit['source_form_path']=matches[0]['path']
        edit['source_native_page_bbox']=matches[0]['native_page_bbox']
    layout['reviewed_form_prose_suppression_audit']=form_edits
    doc=fitz.open(stream=hidden,filetype='pdf');page=doc[0]
    control=fitz.open(stream=hidden,filetype='pdf')
    korean=fitz.open();kp=korean.new_page(width=page.rect.width,height=page.rect.height)
    raster_layer=fitz.open();rp=raster_layer.new_page(width=page.rect.width,height=page.rect.height)
    caption_layer=fitz.open();cp=caption_layer.new_page(width=page.rect.width,height=page.rect.height)
    caption_ids={s['slot_id']for s in layout['reviewed_raster_caption_overlaps']}
    font_paths={r:Path(p)for r,p in layout['new_font_paths'].items()};metrics=FontMetrics(font_paths)
    for role in sorted({p['font_role']for p in layout['placements']}):
        text=''.join(p['text']for p in layout['placements']if p['font_role']==role)
        for pg in(page,kp,cp):pg.insert_font(fontname='KO_Natural_'+role.replace('-','_'),fontbuffer=subset_buffer(font_paths[role],text))
    for p in layout['placements']:
        prose_pages=(page,kp,cp)if p['id']in caption_ids else(page,kp)
        point=fitz.Point(p.get('draw_point',p['point']));color=tuple(((p['color']>>n)&255)/255 for n in(16,8,0))
        morph=(point,fitz.Matrix(1,0,math.tan(math.radians(p['angle'])),1,0,0))if p['angle']else None
        text=p.get('draw_text',p['text']);metric=metrics[p['font_role']]
        # Reset the PDF text origin at each ordinary word. This also avoids
        # accumulating rounded PDF glyph advances across a long paragraph.
        xx,yy=point;parts=re.split('( +)',text)
        for ii,part in enumerate(parts):
            if not part:continue
            if part.isspace():xx+=word_space(metric,p['size'])*len(part);continue
            pp=fitz.Point(xx,yy);mm=(pp,fitz.Matrix(1,0,math.tan(math.radians(p['angle'])),1,0,0))if p['angle']else None
            emitted=part+(' 'if ii+1<len(parts)and parts[ii+1].isspace()else'')
            for pg in prose_pages:insert_prose_text(pg,pp,emitted,'KO_Natural_'+p['font_role'].replace('-','_'),p['size'],color,p['angle'])
            xx+=metric.text_length(part,fontsize=p['size'])
    # Use the separately measured raster-only language overlay, preserving source image streams.
    if layout['raster_labels']:
        label_roles={label.get('font_role','sans')for label in layout['raster_labels']}
        for role in sorted(label_roles):
            if role not in FONTS:raise ValueError('Unsupported raster-label font role '+role)
            text=''.join(label['text']for label in layout['raster_labels']if label.get('font_role','sans')==role)
            for pg in(page,kp,rp):pg.insert_font(fontname='KO_Natural_Raster_'+role.replace('-','_'),fontbuffer=subset_buffer(FONTS[role],text))
        for label in layout['raster_labels']:
            role=label.get('font_role','sans');name='KO_Natural_Raster_'+role.replace('-','_')
            metric=fitz.Font(fontfile=str(FONTS[role]))
            rect=label.get('rect',label.get('mask_pdf_rect'))
            fill=tuple(label.get('fill',(1,1,1)))
            if len(fill)!=3 or any(v<0 or v>1 for v in fill):raise ValueError('Invalid raster-label background fill')
            for pg in(page,control[0]):pg.draw_rect(rect,color=None,fill=fill,overlay=True)
            x,y=label['point'];width=metric.text_length(label['text'],fontsize=label['size'])
            rotate=int(label.get('rotate',0))
            if rotate not in [0,90,180,270]:raise ValueError('Raster-label rotation must match an orthogonal source baseline')
            if label.get('align')=='right':
                if rotate==0:x-=width
                elif rotate==90:y+=width
                elif rotate==180:x+=width
                else:y-=width
            color=label.get('color',0)
            color=tuple(((color>>n)&255)/255 for n in(16,8,0))if isinstance(color,int)else tuple(color)
            for pg in(page,kp,rp):pg.insert_text((x,y),label['text'],fontname=name,fontsize=label['size'],color=color,rotate=rotate)
    def gray(pg):
        pix=pg.get_pixmap(matrix=fitz.Matrix(2,2),colorspace=fitz.csGRAY,alpha=False)
        return np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width)
    ng,kg=gray(control[0]),gray(kp);hits=(ng<180)&(kg<220);raw_collision=int(hits.sum())
    decoration_ink=np.zeros(ng.shape,bool);decoration_contacts=[]
    if layout['prose_vector_decorations']:
        raw=control.tobytes(garbage=0,deflate=False);inv=motion.inspect_inline_groups(raw,1)
        remove=set();regions=[]
        for item in layout['prose_vector_decorations']:
            path=inv['vector_paths'][item['source_path_index']]
            want=item['target_rect']
            if path['paint_operator']!=item['paint_operator']or max(abs(a-b)for a,b in zip(want,path['rect']))>1e-6:
                raise ValueError('Prose decoration final native path guard failed')
            remove.update(path['operator_indices']);regions.append((item,want))
        pdf=pikepdf.Pdf.open(BytesIO(raw));pp=pdf.pages[0]
        instructions=[v for i,v in enumerate(pikepdf.parse_content_stream(pp))if i not in remove]
        pp.Contents=pdf.make_stream(pikepdf.unparse_content_stream(instructions));buffer=BytesIO();pdf.save(buffer);pdf.close()
        without=fitz.open(stream=buffer.getvalue(),filetype='pdf');dg=gray(without[0]);without.close()
        for item,r in regions:
            scope=np.zeros(ng.shape,bool);pad=1.
            x0=max(0,math.floor((r[0]-pad)*2));x1=min(ng.shape[1],math.ceil((r[2]+pad)*2))
            y0=max(0,math.floor((r[1]-pad)*2));y1=min(ng.shape[0],math.ceil((r[3]+pad)*2));scope[y0:y1,x0:x1]=True
            actual=(ng<180)&(dg>=180)&scope;decoration_ink|=actual
            ys,xs=np.nonzero(hits&actual)
            decoration_contacts.append({'id':item['id'],'observed_contact_pixels':len(xs),
                                        'contact_pixels_pdf_pt':[[float(x/2),float(y/2)]for x,y in zip(xs,ys)],
                                        'source_path_index':item['source_path_index'],'x_translation_only':False,'source_bound_prose_x_affine_only':True,
                                        'source_path_bytes_and_paint_and_y_preserved':True})
    hits&=~decoration_ink;collision=int(hits.sum())
    figure_ink=kg<220
    if layout['raster_labels']:figure_ink&=~(gray(rp)<220)
    caption_canvas_pixels=0
    if caption_ids:
        scope=np.zeros(ng.shape,bool)
        for spec in layout['reviewed_raster_caption_overlaps']:
            r=spec['source_image_rect'];x0=max(0,math.floor(r[0]*2));x1=min(ng.shape[1],math.ceil(r[2]*2))
            y0=max(0,math.floor(r[1]*2));y1=min(ng.shape[0],math.ceil(r[3]*2));scope[y0:y1,x0:x1]=True
        intentional=(gray(cp)<220)&scope;caption_canvas_pixels=int(intentional.sum());figure_ink&=~intentional
    diagram_intrusion=0
    for r in layout['excluded_figure_rects']:
        x0=max(0,math.floor(r[0]*2));x1=min(figure_ink.shape[1],math.ceil(r[2]*2));y0=max(0,math.floor(r[1]*2));y1=min(figure_ink.shape[0],math.ceil(r[3]*2))
        diagram_intrusion+=int(figure_ink[y0:y1,x0:x1].sum())
    collision_box=None;collision_samples=[]
    if collision:
        ys,xs=np.nonzero(hits);collision_box=[float(xs.min()/2),float(ys.min()/2),float((xs.max()+1)/2),float((ys.max()+1)/2)]
        collision_samples=[[float(x/2),float(y/2)]for x,y in zip(xs[:30],ys[:30])]
    doc.save(target,garbage=0,deflate=False);doc.close();korean.close();control.close();raster_layer.close();caption_layer.close()
    layout['new_korean_font_stream_compression']=compress_new_korean_font_streams(target)
    source_doc=fitz.open(layout['source']);source_page=source_doc[layout['page']-1]
    hidden_keys=Counter(ops.glyph_key(g)for g in layout['selected_glyphs'])
    dx={ops.glyph_key(g):s['dx']for s in layout['native_shifts']for g in s['glyphs']}
    expected=[]
    for g in _glyphs(source_page):
        if not g['c'].strip():continue
        k=ops.glyph_key(g)
        if hidden_keys[k]:hidden_keys[k]-=1;continue
        row=dict(g);row['origin']=[g['origin'][0]+dx.get(k,0),g['origin'][1]];expected.append(row)
    final_doc=fitz.open(target);final_page=final_doc[0]
    retained=[g for g in _glyphs(final_page)if g['c'].strip()and not g['font'].startswith(('NotoSerifCJK','NotoSansCJK','Batang'))]
    native_geometry=original_helpers.compare_native(expected,retained)
    layout['final_native_geometry']=native_geometry
    layout['source_font_programs_preserved']=original_helpers.font_programs(source_doc,source_page)<=original_helpers.font_programs(final_doc,final_page)
    layout['original_image_encoded_bytes_and_filters_preserved']=original_helpers.encoded_images(source_doc,source_page)==original_helpers.encoded_images(final_doc,final_page)
    layout['source_image_placements_preserved']=original_helpers.native_images(source_page)==original_helpers.native_images(final_page)
    layout['stationary_display_glyphs_missing_or_moved']=original_helpers.compare_native(layout['stationary_display_glyphs'],retained)['missing']
    layout['stationary_figure_glyphs_missing_or_moved']=original_helpers.compare_native(layout['stationary_figure_glyphs'],retained)['missing']
    layout['new_korean_glyph_and_geometry_audit']=verify_korean_geometry(layout,final_page,metrics)
    final_doc.close();source_doc.close()
    layout['output_sha256']=sha(target);layout['motion_qa']=motion_qa;layout['hidden_original_prose_glyphs']=removed
    layout['new_korean_intrusion_on_native_ink_pixels']=collision;layout['collision_box_pdf_pt']=collision_box
    layout['raw_korean_contact_with_all_original_ink_pixels']=raw_collision
    layout['intentional_prose_decoration_contact_pixels']=raw_collision-collision
    layout['intentional_prose_decoration_contacts']=decoration_contacts
    layout['collision_metric_scope']='Protected original math/figures/text ink; the separately verified original prose underline contacts are reported explicitly.'
    layout['collision_pixels_pdf_pt']=collision_samples
    layout['new_body_korean_ink_inside_protected_figure_pixels']=diagram_intrusion
    layout['reviewed_source_caption_raster_canvas_overlap_pixels']=caption_canvas_pixels
    layout['original_font_sizes_and_baselines_identical']=all(abs(p['point'][1]-p['baseline'])<.000001 for p in layout['placements'])
    layout['native_horizontal_moves_only']=True
    layout['stationary_display_glyph_count']=len(layout['stationary_display_glyphs']);layout['stationary_figure_glyph_count']=len(layout['stationary_figure_glyphs'])
    target.with_suffix('.layout.json').write_text(json.dumps(layout,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps({'output':str(target),'page':layout['page'],'native_atoms_moved':len(layout['native_shifts']),
                      'natural_lines':len(layout['line_reports']),'motion_passed':motion_qa['passed'],'no_reserved_english_widths':True,'collision':collision}))
    if collision:raise ValueError('Korean/native ink collision '+str(collision_box))
    if not layout['new_korean_glyph_and_geometry_audit']['passed']:
        q=layout['new_korean_glyph_and_geometry_audit']
        raise ValueError('New Korean glyph/geometry verification failed: '+str(dict(missing=q['missing_or_notdef_glyphs'][:5],errors=q['geometry_errors'][:5],max_error=q['max_position_error_pt'])))
    if diagram_intrusion:raise ValueError('Body Korean entered protected diagram: '+str(diagram_intrusion))
    if native_geometry['missing']or native_geometry['extra']or layout['stationary_display_glyphs_missing_or_moved']or layout['stationary_figure_glyphs_missing_or_moved']or not layout['source_font_programs_preserved']or not layout['original_image_encoded_bytes_and_filters_preserved']or not layout['source_image_placements_preserved']:
        raise ValueError('Final native glyph/font/image preservation failed')
    return layout

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('plan',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--overrides',type=Path);parser.add_argument('--layout-only',action='store_true')
    args=parser.parse_args();overrides=json.loads(args.overrides.read_text('utf-8'))if args.overrides else None
    if args.layout_only:
        out=prepare_layout(args.plan,overrides);args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2),'utf-8');print(len(out['line_reports']))
    else:build(args.plan,args.output,overrides,args.overrides)
