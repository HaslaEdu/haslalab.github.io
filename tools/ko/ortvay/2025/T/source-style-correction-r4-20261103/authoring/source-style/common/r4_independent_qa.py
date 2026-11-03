"""Independent full-master origins, exact native data and P0/P1 exception audit."""
from pathlib import Path
from collections import defaultdict
import hashlib,io,json,math,re,copy
import numpy as np
import pymupdf as f
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from r4_actual_paint import glyphs,normalize_face,streams,actual_row_ink,actual_native_contact
from r4_runtime import contact_row_rule

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def expected_glyphs(e,q,year):
    result=[];metrics={};fontpaths={}
    def add(p,role,path,label=False):
        key=str(path)
        if key not in metrics:metrics[key]=e.font_metric(Path(path))
        metric=metrics[key];x,y=p['point'];size=p['size'];rotation=p.get('rotate',0) if label and year!=2026 else 0
        dx,dy={0:(1,0),90:(0,-1),180:(-1,0),270:(0,1)}[rotation]
        if label and p.get('align')=='right':
            width=metric.text_length(p['text'],fontsize=size);x-=dx*width;y-=dy*width
        for ch in p['text']:
            if not ch.isspace():
                gid=metric.has_glyph(ord(ch));assert gid>0
                result.append(dict(cp=ord(ch),gid=gid,font=normalize_face(metric.name),size=size,origin=[x,y],
                    role=role,master_path=str(path),placement=p,label=label,rotation=rotation,angle=p.get('angle',0) if not label else 0))
            advance=e.word_space(metric,size) if ch==' ' and not label else metric.text_length(ch,fontsize=size)
            x+=dx*advance;y+=dy*advance
    for p in q['placements']:add(p,p['font_role'],q['new_font_paths'][p['font_role']])
    for p in q.get('raster_labels',[]):
        role='sans' if year==2026 else p.get('font_role','sans');add(p,role,e.FONTS[role],True)
    return result

def match_expected(expected,page):
    actual=glyphs(page,True);groups=defaultdict(list)
    for index,g in enumerate(actual):groups[(g['cp'],normalize_face(g['font']),round(g['size'],4))].append((index,g))
    result=[];errors=[];maximum=0.;gid_errors=[]
    for want in expected:
        key=(want['cp'],want['font'],round(want['size'],4));options=groups[key]
        if not options:errors.append(dict(reason='Missing glyph',expected=key,point=want['origin']));continue
        j=min(range(len(options)),key=lambda i:max(abs(a-b) for a,b in zip(want['origin'],options[i][1]['origin'])))
        index,got=options.pop(j);error=max(abs(a-b) for a,b in zip(want['origin'],got['origin']));maximum=max(maximum,error)
        if error>.001:errors.append(dict(identity=key,expected=want['origin'],actual=got['origin'],delta=error))
        if got['gid']<=0 or got['cp']==65533 or got['gid']!=want['gid']:gid_errors.append(dict(expected_gid=want['gid'],actual=got))
        result.append(dict(expected=want,actual=got,index=index))
    extras=[v for values in groups.values() for _,v in values]
    assert not errors and not gid_errors and not extras,dict(geometry_errors=errors[:10],gid_errors=gid_errors[:10],extra=extras[:10],maximum=maximum)
    return result,dict(passed=True,planned_glyphs=len(expected),actual_glyphs=len(actual),max_position_error_pt=maximum,
        position_tolerance_pt=.001,geometry_errors=[],original_full_font_gids_verified=len(actual),original_full_font_gid_errors=[])

def _allowed(pair,cfg,page,lineage,contact):
    g=pair['expected'];p=g['placement'];reasons=[]
    is_contact=contact and abs(g['origin'][1]-contact['baseline'])<.001
    if is_contact:
        assert p['id']==contact['precontact_logical_placement']['id'] and g['font']=='batang'
        reasons.append('approved_one_KO_row_preexisting_AA_contact_dx')
    if lineage=='P2_precise_Tm_precontact_failed_AA_control':return reasons
    if page==1 and cfg['year']!=2023 and any(abs(g['origin'][1]-v['baseline'])<.001 for v in cfg['title_rows']):reasons.append('source_four_title_centers')
    row=cfg.get('approved_row')
    if row and page==row['page'] and abs(g['origin'][1]-row['baseline'])<.001:reasons.append('approved_origin_row_0.75pt')
    if not g['label'] and p['angle']:
        entry=[v for v in cfg['source_style_entries'] if v['source_slot_id']==p['id'] and v['target_text']==p['text'] and abs(v['baseline_pt']-p['baseline'])<.001]
        assert len(entry)==1 and p['angle']==entry[0]['desired_pdf_glyph_space_shear_angle']
        reasons.append('source_slot_bound_new_prose_shear')
    if cfg['year']==2026 and not g['label'] and g['font']=='batang':reasons.append('new_Batang_master_hmtx_W_precision')
    return reasons

def reference_comparison(e,q,target,cfg,matched,label,reference,reference_layout):
    oldq=json.loads(Path(reference_layout).read_text('utf8'));assert q['native_shifts']==oldq['native_shifts']
    contact=contact_row_rule(cfg['year'],q['page'])
    assert len(oldq['placements'])==len(q['placements'])
    title_dx={}
    for previous,current in zip(oldq['placements'],q['placements']):
        expected=copy.deepcopy(previous);y=previous['baseline'];title=q['page']==1 and cfg['year']!=2023 and any(abs(y-v['baseline'])<.0002 for v in cfg['title_rows'])
        row=cfg.get('approved_row');combined=row and q['page']==row['page'] and abs(y-row['baseline'])<.0002
        contact_match=contact and abs(y-contact['baseline'])<.001
        if title:
            dx=current['point'][0]-previous['point'][0]
            if label in ('P1_approved_intermediate','P2_precise_Tm_precontact_failed_AA_control'):assert abs(dx)<=1e-7,'Approved/control title moved again'
            if y in title_dx:assert abs(dx-title_dx[y])<=1e-7
            title_dx[y]=dx
        elif combined:dx=row['dx'] if label=='P0_current_published' else 0
        elif contact_match:dx=contact['dx']
        else:dx=0
        for field in ('point','draw_point'):
            if field in expected:
                expected[field][0]+=dx
                assert max(abs(a-b) for a,b in zip(expected[field],current[field]))<=1e-7,('Unapproved logical origin change',previous,current)
                expected[field]=current[field]
        if previous['angle']:
            entries=[v for v in cfg['source_style_entries'] if v['source_slot_id']==current['id'] and v['target_text']==current['text'] and abs(v['baseline_pt']-y)<.001]
            assert len(entries)==1 and previous['angle']==entries[0]['old_descriptor_angle']
            expected['angle']=entries[0]['desired_pdf_glyph_space_shear_angle']
        assert expected==current,('Unapproved placement field/word/spacing/style change',previous,current)
    assert q.get('raster_labels',[])==oldq.get('raster_labels',[]),'Raster label plan changed'
    with f.open(reference) as old,f.open(target) as new:
        op,np_=old[0],new[0];assert op.rect==np_.rect
        assert glyphs(op,False,True)==glyphs(np_,False,True),'Original native glyphs changed'
        assert e.original_helpers.font_programs(old,op)==e.original_helpers.font_programs(new,np_),'Font program binaries changed'
        assert e.original_helpers.encoded_images(old,op)==e.original_helpers.encoded_images(new,np_),'Image bytes changed'
        assert e.original_helpers.native_images(op)==e.original_helpers.native_images(np_),'Image placements changed'
        groups=defaultdict(list)
        for g in glyphs(op,True):groups[(g['cp'],g['gid'],normalize_face(g['font']),round(g['size'],4),g['color'],g['paint'],g['dir'])].append(g)
        changed=[];untouched=0;title_audits=[];allowed_pairs=[]
        for pair in matched:
            got=pair['actual'];want=pair['expected'];key=(got['cp'],got['gid'],normalize_face(got['font']),round(got['size'],4),got['color'],got['paint'],got['dir'])
            options=groups[key];assert options,('P0/P1 glyph identity changed',key)
            j=min(range(len(options)),key=lambda i:(abs(got['origin'][1]-options[i]['origin'][1]),abs(got['origin'][0]-options[i]['origin'][0])))
            previous=options.pop(j);reasons=_allowed(pair,cfg,q['page'],label,contact)
            assert abs(previous['origin'][1]-got['origin'][1])<=1e-6,('Source baseline changed',previous,got)
            is_style='source_slot_bound_new_prose_shear' in reasons
            is_width='new_Batang_master_hmtx_W_precision' in reasons
            is_title='source_four_title_centers' in reasons
            is_row='approved_origin_row_0.75pt' in reasons
            is_contact='approved_one_KO_row_preexisting_AA_contact_dx' in reasons
            if is_contact and label=='P2_precise_Tm_precontact_failed_AA_control':
                assert abs(previous['origin'][0]+contact['dx']-got['origin'][0])<=.001
            if is_row:
                dx=cfg['approved_row']['dx'] if label=='P0_current_published' else 0
                assert abs(previous['origin'][0]+dx-got['origin'][0])<=.001,('Approved row origin',previous,got,dx)
                assert abs(dx)/cfg['approved_row']['source_size_pt']<=.4
            elif is_title:
                if label=='P1_approved_intermediate':assert max(abs(a-b) for a,b in zip(previous['origin'],got['origin']))<=.001
            elif not is_width and not is_contact:assert max(abs(a-b) for a,b in zip(previous['origin'],got['origin']))<=.001
            # New shear affects bbox geometry, but never identity, size or baseline.
            if not is_style and not is_width and not is_title and not is_row and not is_contact:
                assert previous==got,('Glyph outside correction union changed',previous,got);untouched+=1
            else:allowed_pairs.append((previous,got,reasons,pair))
            if previous!=got:changed.append(dict(character=chr(got['cp']),reasons=reasons,old_origin=previous['origin'],new_origin=got['origin'],old_bbox=previous['bbox'],new_bbox=got['bbox']))
        assert not any(groups.values()),'P0/P1 extra glyphs'
        if q['page']==1:
            for spec in cfg['title_rows']:
                row=[p['actual'] for p in matched if abs(p['actual']['origin'][1]-spec['baseline'])<.001]
                assert row;center=(min(v['bbox'][0] for v in row)+max(v['bbox'][2] for v in row))/2
                assert abs(center-spec['source_center_pt'])<=.001
                title_audits.append(dict(baseline=spec['baseline'],actual_center=center,original_center=spec['source_center_pt'],error=center-spec['source_center_pt']))
        scale=2
        a=op.get_pixmap(matrix=f.Matrix(scale,scale),alpha=False);b=np_.get_pixmap(matrix=f.Matrix(scale,scale),alpha=False)
        aa=np.frombuffer(a.samples,np.uint8).reshape(a.height,a.width,a.n);bb=np.frombuffer(b.samples,np.uint8).reshape(b.height,b.width,b.n)
        difference=np.any(aa!=bb,axis=2);mask=np.zeros(difference.shape,bool)
        for before,after,why,pair in allowed_pairs:
            # Per glyph only; account for its actual oblique outline rather than masking the whole row.
            for g in (before,after):
                bounds=list(g['bbox']);angle=pair['expected']['angle']
                if angle:
                    extent=abs(math.tan(math.radians(angle)))*g['size']
                    bounds[0]-=extent;bounds[2]+=extent
                x0=max(0,math.floor(bounds[0]*scale)-2);x1=min(a.width,math.ceil(bounds[2]*scale)+2)
                y0=max(0,math.floor(bounds[1]*scale)-2);y1=min(a.height,math.ceil(bounds[3]*scale)+2)
                mask[y0:y1,x0:x1]=True
        outside=int((difference&~mask).sum());assert outside==0,('Pixels outside glyph union changed',label,outside)
        return dict(passed=True,lineage=label,reference_path=str(reference),reference_sha256=sha(reference),
            reference_layout_sha256=sha(reference_layout),actual_new_glyphs_compared=len(matched),unmodified_new_glyphs_exact=untouched,
            native_glyphs_exact=True,source_and_new_font_program_binaries_exact=True,encoded_images_and_placements_exact=True,
            native_shifts_exact=True,pixel_scale=2,total_changed_pixels=int(difference.sum()),changed_pixels_outside_explicit_glyph_union=outside,
            planned_words_point_sizes_styles_word_spaces_and_all_other_placement_fields_exact=True,
            title_centers=title_audits,approved_intermediate_titles_preserved=label=='P1_approved_intermediate',changed_glyph_details=changed)

def verify(e,q,target,cfg):
    with f.open(target) as doc:
        expected=expected_glyphs(e,q,cfg['year']);matched,geometry=match_expected(expected,doc[0])
        physical=[]
        for stream in streams(doc[0]):
            shear=stream['cm'][2]
            if abs(shear)>1e-10:
                assert shear>0,'New prose still has physical left shear'
                assert abs(shear-math.tan(math.radians(14)))<=1e-6
                physical.append(dict(xref=stream['xref'],physical_pdf_cm_c=shear,baseline=stream['actual_baseline']))
        assert bool(physical)==bool(q['r4_source_style_corrections'])
    row=cfg.get('approved_row');special=[(row['upper_baseline'],row['baseline'])] if row and q['page']==row['page'] else []
    contact_rule=contact_row_rule(cfg['year'],q['page'])
    if contact_rule:
        with f.open(target) as doc:
            assert not [v for v in glyphs(doc[0],False) if abs(v['origin'][1]-contact_rule['baseline'])<.001],'Approved contact row contains an original native glyph'
            actual=sorted([v for v in glyphs(doc[0],True) if abs(v['origin'][1]-contact_rule['baseline'])<.001],key=lambda v:v['origin'][0])
            whitelist=[dict(cp=v['cp'],gid=v['gid'],font=v['font'],size=v['size'],color=list(v['color']) if isinstance(v['color'],tuple) else v['color'],paint=v['paint']) for v in actual]
            assert whitelist==contact_rule['actual_nonspace_glyph_whitelist'],'Approved KO row glyph identity/style whitelist changed'
        special.extend([(contact_rule['upper_baseline'],contact_rule['baseline']),(contact_rule['baseline'],contact_rule['next_lower_baseline'])])
    kk=actual_row_ink(target,q,special);assert kk['passed'],kk
    contact=actual_native_contact(target);assert contact['passed'],contact
    refs=next(v for v in cfg['reference_pages'] if v['page']==q['page'])
    p0=refs['P0']
    assert sha(p0['published_document_path'])==p0['published_document_sha256']
    with f.open(p0['published_document_path']) as publication,f.open(p0['proof_path']) as reference:
        pp,rp=publication[p0['published_page_index']],reference[0]
        assert glyphs(pp,None,True)==glyphs(rp,None,True),'Current published complete document differs from its frozen page proof'
        a,b=pp.get_pixmap(matrix=f.Matrix(2,2),alpha=False),rp.get_pixmap(matrix=f.Matrix(2,2),alpha=False)
        assert (a.width,a.height,a.n,a.samples)==(b.width,b.height,b.n,b.samples),'Current published page pixels differ from frozen page proof'
        published_lineage=dict(passed=True,published_document_path=p0['published_document_path'],
            published_document_sha256=p0['published_document_sha256'],published_page_index=p0['published_page_index'],
            P0_frozen_page_sha256=p0['proof_sha256'],published_page_trace_exact=True,published_page_pixels_2x_exact=True)
    comparisons=[]
    for key,label in [('P0','P0_current_published'),('P1_approved','P1_approved_intermediate')]:
        ref=refs.get(key)
        if ref:comparisons.append(reference_comparison(e,q,target,cfg,matched,label,ref['proof_path'],ref['layout_path']))
    if contact_rule:
        comparisons.append(reference_comparison(e,q,target,cfg,matched,'P2_precise_Tm_precontact_failed_AA_control',contact_rule['precontact_proof']['path'],contact_rule['precontact_layout']['path']))
    return dict(passed=True,page=q['page'],year=cfg['year'],proof_sha256=sha(target),
        original_full_master_geometry=geometry,actual_target_physical_shear=physical,
        actual_stream_interrow_ink=kk,actual_target_language_vs_native_ink=contact,
        current_published_complete_document_lineage=published_lineage,
        direct_reference_comparisons=comparisons,combined_approved_row_bbox_is_not_pure_translation=bool(row and q['page']==row['page']),
        preexisting_AA_contact_KO_row_correction=q.get('r4_existing_AA_contact_KO_row_correction'),
        actual_outline_and_encoded_W_audit_pending=True)
