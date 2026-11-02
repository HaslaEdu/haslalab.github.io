"""Direct-source Korean line composition with whole native expression movement.

Source English span widths are used only for identifying source glyphs. They
never reserve output space. Korean and native atoms are packed by their actual
advances, with ordinary word spaces, at the source physical line baselines.
"""
from pathlib import Path
from collections import Counter,defaultdict
from io import BytesIO
import argparse,hashlib,json,math,re,sys
import pymupdf as fitz
import numpy as np
from fontTools import subset
from fontTools.ttLib import TTFont

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'composer'/'ortvay2026-frozen-engine'))
import latex_native_motion as motion
import pdf_latex_text_ops as ops
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
    if right['kind']=='prose'and re.match(r'^(?:점|개|가지|년|월|일|배|차|회)(?=\s|$|[,.!?;:)\]}])',b):return 0.
    if a[-1]in',.;:':return word_space(metric,size)
    if right['kind']=='prose'and JOSA.match(b):return 0.
    if right['kind']=='native'and right.get('size',size)<size*.82 and right['baseline']<left['baseline']-size*.15:return 0.
    return word_space(metric,size)

def _token_bbox(glyphs):
    ink=[g for g in glyphs if g['gid']>=0 and g['c'].strip()]
    return [min(g['bbox'][0]for g in ink),min(g['bbox'][1]for g in ink),
            max(g['bbox'][2]for g in ink),max(g['bbox'][3]for g in ink)]

def prepare_layout(plan_path,overrides=None):
    plan=json.loads(Path(plan_path).read_text('utf-8'));source=Path(plan['source'])
    if plan.get('source_sha256')and sha(source)!=plan['source_sha256']:raise ValueError('Source hash changed')
    scopes={};scope_journal=[]
    for name in ['figure-scope-2026.json','ortvay-figure-scope-2026.json']:
        path=BASE/'source-review'/name
        if not path.exists():continue
        cfg=json.loads(path.read_text('utf-8'));entry={}
        if source.name==cfg.get('source'):entry=cfg.get('pages',{}).get(str(plan['page']),{})
        entry=dict(entry,**cfg.get('additional_historical_scope',{}).get(source.name+':'+str(plan['page']),{}))
        if entry:scopes.update(entry);scope_journal.append({'path':str(path),'sha256':sha(path),'entry':entry})
    scopes.update({k:plan[k]for k in ['excluded_figure_rects','fixed_native_rects','mode','prose_column_rects']if k in plan})
    doc=fitz.open(source);page=doc[plan['page']-1];blocks=page.get_text('rawdict')['blocks']
    font_paths=dict(FONTS)
    batang=source.name.lower().startswith('ortvay_')
    if batang:
        font_paths['serif']=Path('C:/Windows/Fonts/batang.ttc')
        font_paths['serif-italic']=FONTS['serif']
    metrics={r:font_metric(p)for r,p in font_paths.items()}
    meta=original_helpers.font_metadata(source,plan['page']-1)
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
        line=anchors.setdefault(key,{'baseline':y,'prose':[],'native':[],'source_rects':[]})
        b,l,_,_=slot['at'];line['source_rects'].append(list(blocks[b]['lines'][l]['bbox']))
        role=slot.get('font_role',_role(first['font']));text=clean((overrides or{}).get(slot['id'],slot['text']))
        if batang and role=='serif'and (meta[ops.family_name(first['font'])]['angle']or re.search('Ital|SFTI|CMTI|CMSL',first['font'])):role='serif-italic'
        width=text_width(metrics[role],text,first['size'])
        line['prose'].append({'kind':'prose','id':slot['id'],'text':text,'old_x':first['origin'][0],
                              'source_right':max(c['bbox'][2]for c in chars),'width':width,'size':first['size'],
                              'baseline':y,'font_role':role,'source_font':first['font'],
                              'join_left':slot.get('join_left',False),'join_right':slot.get('join_right',False),
                              'optical_gap_left_pt':slot.get('optical_gap_left_pt'),
                              'angle':meta[ops.family_name(first['font'])]['angle'],'color':first['color']})
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
        if line['is_running_header']:bounds[0]=page.rect.width*.45;bounds[2]=page.rect.width-36
        explicit=[r for r in plan.get('allowed_prose_line_rects',[])if abs(r['baseline']-line['baseline'])<.06]
        if explicit:
            if len(explicit)!=1:raise ValueError('Ambiguous authored line-column bounds')
            bounds=list(explicit[0]['rect'])
        line['source_bounds']=bounds;line['output_right']=body_right
        if line['is_running_header']:line['output_right']=header_right
        for rect in scopes.get('prose_column_rects',[]):
            if rect[1]<=line['baseline']<=rect[3]and bounds[0]>=rect[0]-.5 and bounds[0]<rect[2]:
                line['output_right']=rect[2];line['source_bounds']=[max(bounds[0],rect[0]),bounds[1],min(bounds[2],rect[2]),bounds[3]]
    def inside_line(g,line):
        r=line['source_bounds'];x,y=g['origin']
        script_pad=max(p['size']for p in line['prose'])*.4
        return r[0]-.7<=x<=r[2]+.7 and r[1]-script_pad<=y<=r[3]+script_pad
    # Seed exact full-size baselines, then grow scripts through nearby native
    # glyphs. A global connected component can incorrectly bridge adjacent
    # lines through one subscript and the next line's superscript.
    eligible=[g for g in native if ops.glyph_key(g)not in protected_form_keys and not any(rect.intersects(fitz.Rect(g['bbox']))for rect in exclusions)]
    if scopes.get('mode')in['fixed-cover','fixed-toc-grid']:eligible=[]
    assigned={}
    for i,g in enumerate(eligible):
        choices=[]
        for key,line in anchors.items():
            size=max(p['size']for p in line['prose']);dy=abs(g['origin'][1]-line['baseline'])
            if not inside_line(g,line):continue
            if g['c']in ELEVATED_MATH or g['size']<size*.90 or dy>size*.14:continue
            if line['is_running_header']and g['origin'][0]<page.rect.width*.45:continue
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
                if g['size']>=size*.90 and not re.search('CMEX',g['font'])and g['c']not in ELEVATED_MATH:continue
                gap=max(g['bbox'][0]-other['bbox'][2],other['bbox'][0]-g['bbox'][2],0)
                dy=abs(g['origin'][1]-other['origin'][1])
                if gap<=size*.66 and dy<=size*.98:
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
    for i,key in assigned.items():anchors[key]['native'].append(eligible[i])
    paths=inventory.get('vector_paths',[]);claimed_paths=set();shifts=[];placements=[];line_reports=[]
    optical_adjustments=plan.get('native_gap_adjustments',[])+list((overrides or{}).get('__native_gap_adjustments__',[]));optical_used=Counter()
    line_offsets=plan.get('line_optical_offsets',[])+list((overrides or{}).get('__line_optical_offsets__',[]));line_offsets_used=Counter()
    for line in sorted(anchors.values(),key=lambda l:l['baseline']):
        size=max(p['size']for p in line['prose']);prose=line['prose'];rows=sorted(line['native'],key=lambda g:(g['bbox'][0],g['origin'][1]))
        chunks=[]
        for g in rows:
            x0=g['bbox'][0];x1=g['bbox'][2]
            # Prose runs divide native atoms even when their translated text is empty.
            structural_prefix=bool(chunks and chunks[-1]['glyphs'][-1]['c']=='.'and g['c']=='['and abs(chunks[-1]['glyphs'][-1]['origin'][1]-g['origin'][1])<.1)
            intervening=bool(chunks and any(chunks[-1]['right']<=p['old_x']<x0-.01 for p in prose))or structural_prefix
            if chunks and x0-chunks[-1]['right']<=size*.62 and not intervening:
                chunks[-1]['glyphs'].append(g);chunks[-1]['right']=max(chunks[-1]['right'],x1)
            else:chunks.append({'glyphs':[g],'right':x1})
        tokens=[]
        for ch in chunks:
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
                if box[0]-.7<=r[0] and r[2]<=box[2]+.7 and box[1]-.7<=r[1] and r[3]<=box[3]+.7:
                    token['vector_paths'].append(path);claimed_paths.add(k)
            tokens.append(token)
        tokens+=prose;tokens.sort(key=lambda t:t['old_x'])
        nonempty=[t for t in tokens if t['kind']=='native'or t['text']]
        if not nonempty:continue
        start=min(t['old_x']for t in tokens);cursor=start;gaps=[];prepared=[]
        fixed_cells=(scopes.get('mode')in['fixed-cover','fixed-toc-grid']and not line['is_running_header'])or any(r[1]<=line['baseline']<=r[3]and line['source_bounds'][0]>=r[0]and line['source_bounds'][2]<=r[2]for r in scopes.get('fixed_native_rects',[]))
        for i,t in enumerate(nonempty):
            gap=_boundary(nonempty[i-1],t,size,metrics['serif'])if i else 0.
            if fixed_cells:cursor=t['old_x'];gap=cursor-(prepared[-1][1]+prepared[-1][0]['width'])if prepared else 0.
            else:cursor+=gap
            prepared.append((t,cursor));cursor+=t['width']
            if i:gaps.append({'left':nonempty[i-1]['text'],'right':t['text'],
                               'old_gap':t['old_x']-(nonempty[i-1]['old_x']+nonempty[i-1].get('width',0)),
                               'new_gap':gap,'ordinary_space':word_space(metrics['serif'],size)})
        right=line['output_right'];adjust=right-cursor if line['is_running_header']else 0.
        for oi,entry in enumerate(line_offsets):
            if abs(entry['baseline']-line['baseline'])<.0002:
                if abs(entry['dx'])>size*.4:raise ValueError('Optical row adjustment exceeds 0.4em')
                adjust+=entry['dx'];line_offsets_used[oi]+=1
        if cursor+adjust>right+.05:raise ValueError(f"Full natural line overflow at {line['baseline']}: {cursor+adjust:.2f} > {right:.2f}; paragraph prose needs line-level authoring, never shrink")
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
    moving={ops.glyph_key(g)for s in shifts for g in s['glyphs']}
    stationary_figure=[g for g in native if ops.glyph_key(g)in protected_form_keys or any(rect.intersects(fitz.Rect(g['bbox']))for rect in exclusions)]
    stationary_display=[g for g in native if re.search(r'CM(?:MI|SY|EX)|MS[AB]M|Math|Symbol',g['font'])and not any(inside_line(g,l)for l in anchors.values())and g not in stationary_figure]
    if moving&{ops.glyph_key(g)for g in stationary_figure+stationary_display}:raise ValueError('A diagram/display glyph was requested to move')
    out={'schema':'natural-source-native-v1','source':str(source),'source_sha256':sha(source),'page':plan['page'],'plan_path':str(Path(plan_path).resolve()),'plan_sha256':sha(plan_path),
         'selected_glyphs':selected,'native_shifts':shifts,'placements':placements,'line_reports':line_reports,
         'raster_labels':plan.get('raster_labels',[]),'no_reserved_english_widths':True,'no_font_shrink':True,
         'new_font_paths':{r:str(p)for r,p in font_paths.items()},'new_font_file_sha256':{r:sha(p)for r,p in font_paths.items()},
         'font_policy':'Ortvay upright regular serif: Windows Batang TTC face0; bold/sans/italic unchanged'if batang else'PLANCKS existing Noto CJK serif/sans source-style mapping unchanged',
         '_effective_plan':dict(plan,slots=effective_slots,native_gap_adjustments=optical_adjustments,line_optical_offsets=line_offsets),
         'reviewed_native_optical_gaps':optical_adjustments,
         'reviewed_line_optical_offsets':line_offsets,
         'excluded_figure_rects':[list(r)for r in exclusions],
         'protected_native_figure_forms':protected_forms,
         'reviewed_source_scope':scope_journal,'design_mode':scopes.get('mode','natural-prose'),
         'stationary_figure_glyphs':stationary_figure,'stationary_display_glyphs':stationary_display,
         'source_glyph_moves_restricted_to_authored_prose_line_bounds':True,
         'stationary_display_equations_and_figures':True}
    doc.close();return out

def subset_buffer(path,text):
    digest=hashlib.sha256(path.read_bytes()+text.encode('utf-8')).hexdigest()[:20]
    target=BASE/'composer/font-cache'/(path.stem+'-'+digest+('.ttf'if path.suffix.lower()=='.ttc'else path.suffix))
    if target.exists():return target.read_bytes()
    font=TTFont(path,fontNumber=0 if path.suffix.lower()=='.ttc'else -1,recalcTimestamp=False);opt=subset.Options();opt.retain_gids=True;opt.name_IDs=['*'];opt.name_languages=['*']
    worker=subset.Subsetter(options=opt);worker.populate(text=text);worker.subset(font);buf=BytesIO();font.save(buf);font.close()
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(buf.getvalue());return buf.getvalue()

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

def build(plan_path,target,overrides=None,overrides_path=None):
    layout=prepare_layout(plan_path,overrides);target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    effective_path=target.with_suffix('.effective-plan.json');effective_path.write_text(json.dumps(layout.pop('_effective_plan'),ensure_ascii=False,indent=2),'utf-8')
    layout['effective_plan_path']=str(effective_path.resolve());layout['effective_plan_sha256']=sha(effective_path)
    layout['overrides_path']=str(Path(overrides_path).resolve())if overrides_path else None
    layout['overrides_sha256']=sha(overrides_path)if overrides_path else None
    layout['composer_path']=str(Path(__file__).resolve());layout['composer_sha256']=sha(Path(__file__));layout['native_motion_engine_sha256']=sha(Path(motion.__file__))
    layout['ordinary_gap_boundaries_verified']=assert_natural_gaps(layout)
    moved,motion_qa=motion.reposition_inline(Path(layout['source']),layout['page'],erased_glyphs=[],shifts=layout['native_shifts'],text_shift_mode='ctm')
    moved_path=target.with_suffix('.moved.pdf');moved_path.write_bytes(moved)
    hidden,removed=ops.suppress_prose(moved_path,1,layout['selected_glyphs'])
    doc=fitz.open(stream=hidden,filetype='pdf');page=doc[0]
    control=fitz.open(stream=hidden,filetype='pdf')
    korean=fitz.open();kp=korean.new_page(width=page.rect.width,height=page.rect.height)
    font_paths={r:Path(p)for r,p in layout['new_font_paths'].items()};metrics={r:font_metric(p)for r,p in font_paths.items()}
    for role in sorted({p['font_role']for p in layout['placements']}):
        text=''.join(p['text']for p in layout['placements']if p['font_role']==role)
        for pg in(page,kp):pg.insert_font(fontname='KO_Natural_'+role.replace('-','_'),fontbuffer=subset_buffer(font_paths[role],text))
    for p in layout['placements']:
        point=fitz.Point(p.get('draw_point',p['point']));color=tuple(((p['color']>>n)&255)/255 for n in(16,8,0))
        morph=(point,fitz.Matrix(1,0,math.tan(math.radians(p['angle'])),1,0,0))if p['angle']else None
        text=p.get('draw_text',p['text']);metric=metrics[p['font_role']]
        if metric.name.startswith('Batang'):
            xx,yy=point
            parts=re.split('( +)',text)
            for ii,part in enumerate(parts):
                if not part:continue
                if part.isspace():xx+=word_space(metric,p['size'])*len(part);continue
                pp=fitz.Point(xx,yy);mm=(pp,fitz.Matrix(1,0,math.tan(math.radians(p['angle'])),1,0,0))if p['angle']else None
                emitted=part+(' 'if ii+1<len(parts)and parts[ii+1].isspace()else'')
                for pg in(page,kp):pg.insert_text(pp,emitted,fontname='KO_Natural_'+p['font_role'].replace('-','_'),fontsize=p['size'],color=color,morph=mm)
                xx+=metric.text_length(part,fontsize=p['size'])
        else:
            for pg in(page,kp):pg.insert_text(point,text,fontname='KO_Natural_'+p['font_role'].replace('-','_'),fontsize=p['size'],color=color,morph=morph)
    # Use the separately measured raster-only language overlay, preserving source image streams.
    if layout['raster_labels']:
        role='sans';text=''.join(p['text']for p in layout['raster_labels']);name='KO_Natural_Raster'
        for pg in(page,kp):pg.insert_font(fontname=name,fontbuffer=subset_buffer(FONTS[role],text))
        metric=fitz.Font(fontfile=str(FONTS[role]))
        for label in layout['raster_labels']:
            rect=label.get('rect',label.get('mask_pdf_rect'))
            for pg in(page,control[0]):pg.draw_rect(rect,color=None,fill=(1,1,1),overlay=True)
            x,y=label['point'];width=metric.text_length(label['text'],fontsize=label['size'])
            if label.get('align')=='right':x-=width
            for pg in(page,kp):pg.insert_text((x,y),label['text'],fontname=name,fontsize=label['size'],color=(0,0,0))
    def gray(pg):
        pix=pg.get_pixmap(matrix=fitz.Matrix(2,2),colorspace=fitz.csGRAY,alpha=False)
        return np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width)
    ng,kg=gray(control[0]),gray(kp);hits=(ng<180)&(kg<220);collision=int(hits.sum())
    figure_ink=kg<220
    for label in layout['raster_labels']:
        x,y=label['point'];width=fitz.Font(fontfile=str(FONTS['sans'])).text_length(label['text'],fontsize=label['size'])
        if label.get('align')=='right':x-=width
        size=label['size'];x0=max(0,int((x-size*.2)*2));x1=min(figure_ink.shape[1],math.ceil((x+width+size*.2)*2))
        y0=max(0,int((y-size*1.2)*2));y1=min(figure_ink.shape[0],math.ceil((y+size*.4)*2));figure_ink[y0:y1,x0:x1]=False
    diagram_intrusion=0
    for r in layout['excluded_figure_rects']:
        x0=max(0,math.floor(r[0]*2));x1=min(figure_ink.shape[1],math.ceil(r[2]*2));y0=max(0,math.floor(r[1]*2));y1=min(figure_ink.shape[0],math.ceil(r[3]*2))
        diagram_intrusion+=int(figure_ink[y0:y1,x0:x1].sum())
    collision_box=None;collision_samples=[]
    if collision:
        ys,xs=np.nonzero(hits);collision_box=[float(xs.min()/2),float(ys.min()/2),float((xs.max()+1)/2),float((ys.max()+1)/2)]
        collision_samples=[[float(x/2),float(y/2)]for x,y in zip(xs[:30],ys[:30])]
    doc.save(target,garbage=0,deflate=False);doc.close();korean.close();control.close()
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
    final_doc.close();source_doc.close()
    layout['output_sha256']=sha(target);layout['motion_qa']=motion_qa;layout['hidden_original_prose_glyphs']=removed
    layout['new_korean_intrusion_on_native_ink_pixels']=collision;layout['collision_box_pdf_pt']=collision_box
    layout['collision_pixels_pdf_pt']=collision_samples
    layout['new_body_korean_ink_inside_protected_figure_pixels']=diagram_intrusion
    layout['original_font_sizes_and_baselines_identical']=all(abs(p['point'][1]-p['baseline'])<.000001 for p in layout['placements'])
    layout['native_horizontal_moves_only']=True
    layout['stationary_display_glyph_count']=len(layout['stationary_display_glyphs']);layout['stationary_figure_glyph_count']=len(layout['stationary_figure_glyphs'])
    target.with_suffix('.layout.json').write_text(json.dumps(layout,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps({'output':str(target),'page':layout['page'],'native_atoms_moved':len(layout['native_shifts']),
                      'natural_lines':len(layout['line_reports']),'motion_passed':motion_qa['passed'],'no_reserved_english_widths':True,'collision':collision}))
    if collision:raise ValueError('Korean/native ink collision '+str(collision_box))
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
