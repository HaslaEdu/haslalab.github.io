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
sys.path.insert(0,str(BASE.parent/'common'))
from r4_runtime import (source_style_angle,post_layout,precise_prose_text,capture_width_lineage,fix_widths,finalize_widths)
from r4_guard import (rules as r4_rules,validate_write as r4_validate_write,validate_plan as r4_validate_plan,output_directory as r4_output_directory,sha as r4_sha)
from ortvay2023_write_guard import PROOF_ROOT, CACHE_ROOT, assert_protected_editions, validate_paths
sys.path.insert(0,str(BASE/'composer'/'ortvay2023-frozen-engine'))
import latex_native_motion as motion
import pdf_latex_text_ops as ops
import native_ink_bounds as ink
OLD_ENGINE=Path('D:/CodexBuilds/Hasla-plancks-ortvay-icho-20261102/engine')
sys.path.append(str(OLD_ENGINE))
import native_proof as original_helpers

FONT_DIR=Path('D:/CodexBuilds/Hasla-publish-20261031/tools/ko/fonts')
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
    # Load only the exact font faces actually used on this source page.
    # Every face is still measured by the same unchanged font_metric code.
    def __init__(self,paths):super().__init__();self.paths=paths
    def __missing__(self,role):
        metric=font_metric(self.paths[role]);self[role]=metric;return metric

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
    plan=json.loads(Path(plan_path).read_text('utf-8'));source=Path(plan['source'])
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
    for name in ['ortvay2023-scope.json']:
        path=BASE/'source-review'/name
        if not path.exists():continue
        cfg=json.loads(path.read_text('utf-8'));entry={}
        if cfg.get('source')!=source.name or cfg.get('source_sha256')!=sha(source):raise ValueError('2023 scope source identity mismatch')
        if source.name==cfg.get('source'):entry=cfg.get('pages',{}).get(str(plan['page']),{})
        entry=dict(entry,**cfg.get('additional_historical_scope',{}).get(source.name+':'+str(plan['page']),{}))
        if entry:scopes.update(entry);scope_journal.append({'path':str(path),'sha256':sha(path),'entry':entry})
    scopes.update({k:plan[k]for k in ['excluded_figure_rects','fixed_native_rects','mode','prose_column_rects']if k in plan})
    scopes.update(plan.get('layout_scope',{}));scopes.update((overrides or{}).get('__layout_scope__',{}))
    doc=fitz.open(source);page=doc[plan['page']-1];blocks=page.get_text('rawdict')['blocks']
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
    anchors={};selected_raw=[];locked_raw=[];effective_slots=[]
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
        style_first=first;style_reference=slot.get('source_prose_style_reference')
        if style_reference:
            # An unpainted math-font space can anchor a necessary Korean
            # particle. Its visible style must come from actual adjacent
            # source prose, never from the italic math space's font angle.
            if slot['source'].strip():raise ValueError('Prose style reference requires an original whitespace-only anchor')
            reference=dict(style_reference,id=slot['id']+':style-reference')
            reference_chars=_plain_source(reference,blocks)
            style_first=next(c for c in reference_chars if c['c'].strip())
            if abs(style_first['origin'][1]-first['origin'][1])>.001 or abs(style_first['size']-first['size'])>.001:
                raise ValueError('Referenced prose must have the same original baseline and point size')
            if re.search('CM(?:MI|SY|EX)|Math|Symbol',style_first['font']):raise ValueError('Style reference must be actual source prose')
        role=slot.get('font_role',_role(style_first['font']));text=clean((overrides or{}).get(slot['id'],slot['text']))
        if batang and role=='serif'and (fontinfo(style_first['font'])['angle']or re.search('Ital|SFTI|CMTI|CMSL',style_first['font'])):role='serif-italic'
        width=text_width(metrics[role],text,first['size'])
        line['prose'].append({'kind':'prose','id':slot['id'],'text':text,'old_x':first['origin'][0],
                              'source_text':slot['source'],
                              'source_right':max(c['bbox'][2]for c in chars),'width':width,'size':first['size'],
                              'baseline':y,'font_role':role,'source_font':style_first['font'],
                              'source_anchor_font':first['font'],'source_prose_style_reference':style_reference,
                              'join_left':slot.get('join_left',False),'join_right':slot.get('join_right',False),
                              'optical_gap_left_pt':slot.get('optical_gap_left_pt'),
                              'angle':source_style_angle(BASE,plan,slot,style_first,first,role,text,fontinfo(style_first['font'])['angle']),'color':first['color']})
        selected_raw.extend(chars)
    selected=original_helpers.canonical_selected(page,selected_raw)
    locked=original_helpers.canonical_selected(page,locked_raw)if locked_raw else[]
    erased=Counter(ops.glyph_key(g)for g in selected);lock={ops.glyph_key(g)for g in locked}
    native=[]
    for g in _glyphs(page):
        k=ops.glyph_key(g)
        if erased[k]:erased[k]-=1;continue
        if not g['c'].strip()or k in lock:continue
        native.append(g)
    if any(erased.values()):raise ValueError('Selected source glyph missing')
    images=[fitz.Rect(v['bbox'])for v in page.get_image_info()]
    exclusions=images+[fitz.Rect(r)for r in scopes.get('excluded_figure_rects',[])]+[fitz.Rect(r)for r in scopes.get('fixed_native_rects',[])]
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
        if not any((box&rect).get_area()>=box.get_area()*.8 for rect in exclusions):continue
        protected_forms.append({'path':form['path'],'native_page_bbox':list(box),'glyph_count':len(form['glyphs'])})
        protected_form_keys.update(ops.glyph_key(g)for g in form['glyphs'])
    if protected_form_keys&{ops.glyph_key(g)for g in selected}:
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
    eligible=[g for g in native if ops.glyph_key(g)not in protected_form_keys and not any(rect.intersects(fitz.Rect(g['bbox']))for rect in exclusions)]
    if scopes.get('mode')in['fixed-cover','fixed-toc-grid']:eligible=[]
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
                 and any(inside_line(g,line)for line in anchors.values())]
    if orphan_math:
        raise ValueError('Unassigned native math inside an authored prose line: '+str([(g['c'],g['font'],g['origin'])for g in orphan_math[:8]]))
    for i,key in assigned.items():anchors[key]['native'].append(eligible[i])
    paths=inventory.get('vector_paths',[]);claimed_paths=set();shifts=[];placements=[];line_reports=[]
    optical_adjustments=plan.get('native_gap_adjustments',[])+list((overrides or{}).get('__native_gap_adjustments__',[]));optical_used=Counter()
    line_offsets=plan.get('line_optical_offsets',[])+list((overrides or{}).get('__line_optical_offsets__',[]));line_offsets_used=Counter()
    title_centers=list((overrides or{}).get('__source_title_centers__',[]));title_centers_used=Counter()
    if title_centers:
        if source.name!='Ortvay_2023_T_EN.pdf' or plan['page']!=1 or sha(source)!='c0a5117145c67edc2dfe8953dcc7865438f65e099fe6e73b2ec19616ab27b5f7':
            raise ValueError('Title alignment is restricted to the reviewed2023 first page')
        if len(title_centers)!=4 or len({v['baseline']for v in title_centers})!=4:
            raise ValueError('Exactly four original source title rows are required')
        source_title_glyphs=_glyphs(page)
        for spec in title_centers:
            glyphs=[v for v in source_title_glyphs if v['c'].strip()and abs(v['origin'][1]-spec['baseline'])<.001]
            if not glyphs or ''.join(v['c']for v in glyphs)!=spec['source_text_no_spaces']:
                raise ValueError('Original source title glyph sequence changed')
            if any(v['font']!=spec['source_font']or abs(v['size']-spec['source_size_pt'])>.001 for v in glyphs):
                raise ValueError('Original source title font/point size changed')
            if any(ops.glyph_key(v)not in {ops.glyph_key(g)for g in selected}for v in glyphs):
                raise ValueError('Title centering must include every selected source title glyph')
            center=(min(v['bbox'][0]for v in glyphs)+max(v['bbox'][2]for v in glyphs))/2
            if abs(center-spec['source_center_pt'])>1e-6:
                raise ValueError('Measured original source title center changed')
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
            if token['vector_paths']:
                left=min([box[0]]+[p['rect'][0]for p in token['vector_paths']])
                right=max([box[2]]+[p['rect'][2]for p in token['vector_paths']])
                token['old_x']=left;token['width']=right-left;token['bbox']=[left,box[1],right,box[3]]
            tokens.append(token)
        tokens+=prose;tokens.sort(key=lambda t:t['old_x']);line['tokens']=tokens
    original_prose={t['id']:t['text']for line in anchors.values()for t in line['prose']}
    paragraph_flow=[]
    def pack(nonempty,start,size,fixed_cells):
        cursor=start;gaps=[];prepared=[]
        for i,t in enumerate(nonempty):
            gap=_boundary(nonempty[i-1],t,size,metrics['serif'])if i else 0.
            if fixed_cells:cursor=t['old_x'];gap=cursor-(prepared[-1][1]+prepared[-1][0]['width'])if prepared else 0.
            else:cursor+=gap
            prepared.append((t,cursor));cursor+=t['width']
            if i:gaps.append({'left':nonempty[i-1]['text'],'right':t['text'],
                               'old_gap':t['old_x']-(nonempty[i-1]['old_x']+nonempty[i-1].get('width',0)),
                               'new_gap':gap,'ordinary_space':word_space(metrics['serif'],size)})
        return cursor,gaps,prepared
    ordered_lines=sorted(anchors.values(),key=lambda l:l['baseline'])
    for li,line in enumerate(ordered_lines):
        tokens=line.get('carried_prose',[])+line['tokens']
        size=max(p['size']for p in line['prose'])
        nonempty=[t for t in tokens if t['kind']=='native'or t['text']]
        if not nonempty:continue
        start=min(t['old_x']for t in line['tokens'])
        fixed_cells=((scopes.get('mode')in['fixed-cover','fixed-toc-grid']and not line['is_running_header'])
                     or any(r[1]<=line['baseline']<=r[3]and line['source_bounds'][0]>=r[0]and line['source_bounds'][2]<=r[2]for r in scopes.get('fixed_native_rects',[]))
                     or any(abs(y-line['baseline'])<.01 for y in scopes.get('fixed_prose_baselines',[])))
        cursor,gaps,prepared=pack(nonempty,start,size,fixed_cells)
        right=line['output_right'];adjust=line['header_title_center']-(start+cursor)/2 if line['is_running_header']else 0.
        for ti,spec in enumerate(title_centers):
            if abs(spec['baseline']-line['baseline'])<.0002:
                if fixed_cells or line['is_running_header']or any(t['kind']!='prose'for t in nonempty):
                    raise ValueError('Reviewed2023 title must move as its complete prose row')
                adjust=spec['source_center_pt']-(start+cursor)/2;title_centers_used[ti]+=1
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
                cursor,gaps,prepared=pack(nonempty,start,size,False)
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
                    trial=pack(nonempty+[pulled],start,size,False)
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
    if any(title_centers_used[i]!=1 for i in range(len(title_centers))):raise ValueError('Source title-centering journal did not match exactly once')
    for id,text in original_prose.items():
        cursor=0
        for p in sorted((p for p in placements if p['id']==id),key=lambda p:p.get('target_char_start',0)):
            start=p.get('target_char_start',0);end=p.get('target_char_end',len(text))
            if start<cursor or text[cursor:start].strip()or text[start:end]!=p['text']:
                raise ValueError('Korean paragraph reflow changed text '+id)
            cursor=end
        if text[cursor:].strip():raise ValueError('Korean paragraph reflow omitted text '+id)
    decoration_specs=plan.get('prose_vector_decorations',[])+list((overrides or{}).get('__prose_vector_decorations__',[]))
    decoration_journal=[]
    for spec in decoration_specs:
        targets=[p for p in placements if p['id']==spec['slot_id']and spec['target_text']in p['text']]
        if len(targets)!=1 or targets[0]['text'].count(spec['target_text'])!=1:
            raise ValueError('Ambiguous Korean target for an original prose decoration')
        p=targets[0]
        if abs(p['baseline']-spec['source_baseline'])>.001:raise ValueError('Decorated prose moved to a different source baseline')
        matches=[v for v in paths if v['operator_indices']==spec['operator_indices']]
        if len(matches)!=1:raise ValueError('Original prose-decoration path is missing or ambiguous')
        path=matches[0];key=tuple(path['operator_indices'])
        if key in claimed_paths or path['paint_operator']!=spec['paint_operator']or max(abs(a-b)for a,b in zip(path['rect'],spec['source_rect']))>1e-7:
            raise ValueError('Original prose-decoration path guard failed')
        metric=metrics[p['font_role']];prefix=p['text'].split(spec['target_text'])[0]
        center=p['point'][0]+text_width(metric,prefix,p['size'])+text_width(metric,spec['target_text'],p['size'])/2
        dx=center-(path['rect'][0]+path['rect'][2])/2
        shifts.append({'glyphs':[],'dx':dx,'vector_paths':[path],'purpose':'original-prose-decoration','decoration_id':spec['id']})
        claimed_paths.add(key);decoration_journal.append(dict(spec,dx=dx,target_center_x=center,source_path_index=paths.index(path)))
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
    stationary_figure=[g for g in native if ops.glyph_key(g)in protected_form_keys or any(rect.intersects(fitz.Rect(g['bbox']))for rect in exclusions)]
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
         'prose_vector_decorations':decoration_journal,
         'reviewed_raster_caption_overlaps':caption_overlaps,
         'reviewed_stationary_vector_paths':scopes.get('reviewed_stationary_vector_paths',[]),
         'raster_labels':raster_labels,'reviewed_raster_label_manifest':raster_manifest,'no_reserved_english_widths':True,'no_font_shrink':True,
         'new_font_paths':{r:str(p)for r,p in font_paths.items()},'new_font_file_sha256':{r:sha(p)for r,p in font_paths.items()},
         'font_policy':'Ortvay upright regular serif: Windows Batang TTC face0; bold/sans/italic unchanged'if batang else'PLANCKS existing Noto CJK serif/sans source-style mapping unchanged',
         '_effective_plan':dict(plan,slots=effective_slots,native_gap_adjustments=optical_adjustments,line_optical_offsets=line_offsets,layout_scope=scopes,prose_vector_decorations=decoration_specs,raster_labels=raster_labels,reviewed_raster_label_manifest=raster_manifest),
         'reviewed_native_optical_gaps':optical_adjustments,
         'reviewed_line_optical_offsets':line_offsets,
         'reviewed_source_title_centers':title_centers,
         'excluded_figure_rects':[list(r)for r in exclusions],
         'fixed_running_header_page_columns':fixed_header_columns,
         'protected_native_figure_forms':protected_forms,
         'reviewed_source_scope':scope_journal,'design_mode':scopes.get('mode','natural-prose'),
         'stationary_figure_glyphs':stationary_figure,'stationary_display_glyphs':stationary_display,
         'source_glyph_moves_restricted_to_authored_prose_line_bounds':True,
         'stationary_display_equations_and_figures':True}
    doc.close();return out

def subset_buffer(path,text):
    # Boundary spaces are emitted even for a single-word title or score.
    if ' 'not in text:text=' '+text
    digest_builder=hashlib.sha256()
    with path.open('rb')as original_font:
        for chunk in iter(lambda:original_font.read(1024*1024),b''):digest_builder.update(chunk)
    digest_builder.update(text.encode('utf-8'));digest=digest_builder.hexdigest()[:20]
    target=CACHE_ROOT/(path.stem+'-'+digest+('.ttf'if path.suffix.lower()=='.ttc'else path.suffix))
    if target.exists():return target.read_bytes()
    font=TTFont(path,fontNumber=0 if path.suffix.lower()=='.ttc'else -1,recalcTimestamp=False);opt=subset.Options();opt.retain_gids=True;opt.name_IDs=['*'];opt.name_languages=['*']
    worker=subset.Subsetter(options=opt);worker.populate(text=text);worker.subset(font);buf=BytesIO();font.save(buf);font.close()
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(buf.getvalue());return buf.getvalue()

def verify_korean_geometry(layout,page,metrics):
    expected=defaultdict(list);actual=defaultdict(list);missing_glyphs=[]
    def face(name):
        value=re.sub('[^a-z0-9]','',name.lower())
        # FreeType reports the Batang TTC metric as Batang Regular; the
        # exact retained-GID subset preserves its PostScript name Batang.
        return 'batang' if value=='batangregular' else value
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
    page.parent.update_stream(xref,data)

def encode_only_new_korean_font_streams(raw):
    pdf=pikepdf.Pdf.open(BytesIO(raw));seen=set();before=[];changed=[]
    def original_font_streams(resources,visited=None):
        visited=set()if visited is None else visited;result=[]
        for name,font in resources.get('/Font',{}).items():
            if str(name).startswith('/KO_Natural_'):continue
            descriptor=font.get('/DescendantFonts',[font])[0].get('/FontDescriptor',{})
            for key in ['/FontFile','/FontFile2','/FontFile3']:
                stream=descriptor.get(key)
                if stream is not None:result.append((str(font.get('/BaseFont')),key,hashlib.sha256(stream.read_raw_bytes()).hexdigest(),str(stream.get('/Filter')),str(stream.get('/DecodeParms'))))
        for obj in resources.get('/XObject',{}).values():
            if obj.objgen in visited:continue
            visited.add(obj.objgen)
            if str(obj.get('/Subtype'))=='/Form':result+=original_font_streams(obj.get('/Resources',resources),visited)
        return sorted(result)
    before=original_font_streams(pdf.pages[0].Resources)
    for name,font in pdf.pages[0].Resources.get('/Font',{}).items():
        if not str(name).startswith('/KO_Natural_'):continue
        descriptor=font.get('/DescendantFonts',[font])[0].get('/FontDescriptor',{})
        for key in ['/FontFile','/FontFile2','/FontFile3']:
            stream=descriptor.get(key)
            if stream is None or stream.objgen in seen:continue
            seen.add(stream.objgen);data=stream.read_bytes();old=len(stream.read_raw_bytes())
            stream.write(zlib.compress(data,9),filter=pikepdf.Name('/FlateDecode'))
            if stream.read_bytes()!=data:raise ValueError('New font decoded bytes changed')
            changed.append({'resource':str(name),'font_file_key':key,'decoded_sha256':hashlib.sha256(data).hexdigest(),'before_encoded_bytes':old,'after_encoded_bytes':len(stream.read_raw_bytes())})
    if not changed or original_font_streams(pdf.pages[0].Resources)!=before:raise ValueError('Font stream ownership/preservation check failed')
    output=BytesIO();pdf.save(output,compress_streams=False);pdf.close();data=output.getvalue()
    with pikepdf.Pdf.open(BytesIO(data))as check:
        if original_font_streams(check.pages[0].Resources)!=before:raise ValueError('Original encoded font stream changed while saving')
    return data,{'passed':True,'only_new_KO_Natural_font_files_changed':True,'original_font_encoded_bytes_and_filters_unchanged':True,'decoded_new_font_bytes_unchanged':True,'streams':changed}

def assert_2023_write_namespace(plan_path,target,overrides_path=None,layout_only=False):
    assert_protected_editions()
    plan_path=Path(plan_path).resolve();target=Path(target).resolve()
    expected_plans=(BASE/'historical/ortvay/2023').resolve()
    expected_output=(BASE/'source-review/ortvay2023' if layout_only else PROOF_ROOT).resolve()
    if plan_path.parent!=expected_plans or target.parent!=expected_output:
        raise ValueError('2023 namespace guard rejected plan/output path before any write')
    data=json.loads(plan_path.read_text('utf8'))
    if data.get('year')!=2023 or data.get('competition')!='ortvay' or Path(data['source']).name!='Ortvay_2023_T_EN.pdf':
        raise ValueError('2023 namespace guard rejected source/year')
    if data['source_sha256']!='c0a5117145c67edc2dfe8953dcc7865438f65e099fe6e73b2ec19616ab27b5f7':
        raise ValueError('2023 namespace guard rejected source hash')
    if overrides_path and Path(overrides_path).resolve()!=(BASE/'composer'/f"ortvay2023-page{data['page']:02}.overrides.json").resolve():
        raise ValueError('2023 namespace guard rejected override path')
    validate_paths(data['page'],plan_path,target,Path(__file__),overrides_path,layout_only)
    return True

def build(plan_path,target,overrides=None,overrides_path=None):
    assert_2023_write_namespace(plan_path,target,overrides_path)
    layout=prepare_layout(plan_path,overrides);target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    effective_path=target.with_suffix('.effective-plan.json');effective_path.write_text(json.dumps(layout.pop('_effective_plan'),ensure_ascii=False,indent=2),'utf-8')
    layout['effective_plan_path']=str(effective_path.resolve());layout['effective_plan_sha256']=sha(effective_path)
    layout['overrides_path']=str(Path(overrides_path).resolve())if overrides_path else None
    layout['overrides_sha256']=sha(overrides_path)if overrides_path else None
    layout['composer_path']=str(Path(__file__).resolve());layout['composer_sha256']=sha(Path(__file__));layout['native_motion_engine_sha256']=sha(Path(motion.__file__))
    layout['ordinary_gap_boundaries_verified']=assert_natural_gaps(layout)
    moved,motion_qa=motion.reposition_inline(Path(layout['source']),layout['page'],erased_glyphs=[],shifts=layout['native_shifts'],text_shift_mode='ctm',reviewed_stationary_vector_paths=layout['reviewed_stationary_vector_paths'])
    moved_path=target.with_suffix('.moved.pdf');moved_path.write_bytes(moved)
    hidden,removed=ops.suppress_prose(moved_path,1,layout['selected_glyphs'])
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
            # Batang's TrueType 2048-em advances are rounded to integer
            # thousandths in the newly embedded PDF /W table. Reset every
            # glyph origin to the full-precision original font metric so a
            # parenthesis cannot shift following Korean glyphs by 0.01 pt.
            # Sizes, baselines and authored ordinary spaces remain unchanged.
            if metric.name.startswith('Batang'):
                gx=xx
                for ch in emitted:
                    for pg in prose_pages:insert_prose_text(pg,fitz.Point(gx,yy),ch,'KO_Natural_'+p['font_role'].replace('-','_'),p['size'],color,p['angle'])
                    gx+=word_space(metric,p['size'])if ch==' 'else metric.text_length(ch,fontsize=p['size'])
            else:
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
            want=[v+(item['dx']if i%2==0 else 0)for i,v in enumerate(item['source_rect'])]
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
                                        'source_path_index':item['source_path_index'],'x_translation_only':True,
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
    encoded,encoding_audit=encode_only_new_korean_font_streams(doc.tobytes(garbage=0,deflate=False));target.write_bytes(encoded);layout['new_korean_font_lossless_stream_encoding_audit']=encoding_audit
    doc.close();korean.close();control.close();raster_layer.close();caption_layer.close()
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


# New private R4 wrappers; source kernels and prior revisions remain immutable.
_R4_ORIGINAL_PREPARE=prepare_layout
def prepare_layout(plan_path,overrides=None):
    cfg=r4_rules(BASE);n=json.loads(Path(plan_path).read_text('utf8'))['page']
    expected=cfg['overrides'].get(str(n));path=Path(expected['path']) if expected else None
    r4_validate_plan(BASE,plan_path,path)
    assert overrides==(json.loads(path.read_text('utf8')) if path else None),'Unapproved override dictionary'
    value=_R4_ORIGINAL_PREPARE(plan_path,overrides)
    return post_layout(value,BASE,font_metric,text_width,ops.glyph_key,_glyphs)
_R4_ORIGINAL_BUILD=build
def build(plan_path,target,overrides=None,overrides_path=None):
    r4_validate_write(BASE,plan_path,target,overrides_path)
    value=_R4_ORIGINAL_BUILD(plan_path,target,overrides,overrides_path)
    result=finalize_widths(Path(target),value,BASE)
    if result:value['r4_exact_W_finalization']=result
    value['output_sha256']=r4_sha(target)
    Path(target).with_suffix('.layout.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf8')
    return value

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('plan',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--overrides',type=Path)
    args=parser.parse_args();r4_validate_write(BASE,args.plan,args.output,args.overrides)
    overrides=json.loads(args.overrides.read_text('utf8')) if args.overrides else None
    build(args.plan,args.output,overrides,args.overrides)
