"""DRAFT additive full-Tm/CTM report contract; does not replace validate_page.

Pure JSON/numeric checks only. Runtime/profile/ROOT-GO binding belongs to the
publication coordinator. The existing master-geometry audit anchors absolute
origins; the canonical PDF-to-page y flip is checked using frozen body rows.
"""
from collections import Counter
import json
import hashlib
import math
import re

STATUS='DRAFT_ADDITIVE_REPORT_CONTRACT_NOT_PRODUCTION_AUTHORIZATION'


def number(v):
    assert type(v)in(int,float)and math.isfinite(v)
    return v


def integer(v,minimum=0):
    number(v);assert v==int(v)and v>=minimum
    return int(v)


def vector(v,n):
    assert isinstance(v,list)and len(v)==n
    return[number(x)for x in v]


def near(a,b,tolerance):
    assert len(a)==len(b)and max((abs(number(x)-number(y))for x,y in zip(a,b)),default=0)<=tolerance


def multiply(a,b):
    a,b=vector(a,6),vector(b,6)
    return[a[0]*b[0]+a[1]*b[2],a[0]*b[1]+a[1]*b[3],
        a[2]*b[0]+a[3]*b[2],a[2]*b[1]+a[3]*b[3],
        a[4]*b[0]+a[5]*b[2]+b[4],a[4]*b[1]+a[5]*b[3]+b[5]]


def rotation(angle):
    return{0:[1,0,0,1,0,0],90:[0,1,-1,0,0,0],180:[-1,0,0,-1,0,0],270:[0,-1,1,0,0,0]}[angle]


def geometry(g,count):
    assert g['passed']is True
    assert g['planned_glyphs']==g['actual_glyphs']==g['original_full_font_gids_verified']==count
    assert g['geometry_errors']==g['original_full_font_gid_errors']==[]
    assert 0<number(g['position_tolerance_pt'])<=.001
    assert 0<=number(g['max_position_error_pt'])<=.001


def validate(audit,body,year=None,layout_sha256=None,effective_plan=None):
    """Use alongside ortvay_source_style_publication.validate_page."""
    year=audit['year']if year is None else year
    assert year in(2023,2024,2025,2026)and audit['year']==year
    assert audit['passed']is True and audit['page']==body['page']
    assert audit['proof_sha256']==audit['target']['sha256']==body['output_sha256']
    if layout_sha256 is not None:assert audit['layout']['sha256']==layout_sha256
    specs={};body_ids={};labels=[];expected_chars=Counter();expected_total=expected_spaces=0
    def add(p,key,label):
        nonlocal expected_total,expected_spaces
        assert key not in specs and isinstance(p['text'],str)
        role=('sans'if year==2026 else p.get('font_role','sans'))if label else p['font_role']
        alias=('KO_Natural_Raster'if year==2026 else'KO_Natural_Raster_'+role.replace('-','_'))if label else'KO_Natural_'+role.replace('-','_')
        angle=0 if label else number(p.get('angle',0));assert angle in(0,14)
        turn=integer(p.get('rotate',0))if label and year!=2026 else 0
        assert turn in(0,90,180,270)
        count=len(p['text']);spaces=sum(c.isspace()for c in p['text'])
        specs[key]=dict(placement=p,label=label,alias=alias,angle=angle,rotation=turn,count=count,spaces=spaces,size=number(p['size']))
        assert specs[key]['size']>0
        expected_total+=count;expected_spaces+=spaces
        expected_chars.update((alias,c)for c in p['text']if not c.isspace())
    for index,p in enumerate(body['placements']):
        assert isinstance(p['id'],str)
        # A frozen source slot can continue on another authored baseline.
        # Preserve each target range as a separate counted placement.
        key='body:'+str(index)+':'+p['id']+':'+json.dumps([p.get('target_char_start'),p.get('target_char_end'),p['baseline']],separators=(',',':'))
        body_ids.setdefault(p['id'],[]).append(key);add(p,key,False)
    for identifier,keys in body_ids.items():
        if len(keys)>1:
            parts=[specs[key]['placement']for key in keys]
            assert all(p['source_text']==parts[0]['source_text']for p in parts)
            ranges=[]
            for p in parts:
                start=integer(p['target_char_start']);end=integer(p['target_char_end'])
                assert end-start==len(p['text']);ranges.append((start,end))
            ranges.sort();assert ranges[0][0]==0
            if effective_plan is not None:
                # An exact authored U+0020 can be consumed by a line wrap.
                # The raw file bytes, not caller-declared metadata alone, bind
                # the complete authored slot to this certified body layout.
                raw=effective_plan['raw_utf8'];assert isinstance(raw,str)
                assert hashlib.sha256(raw.encode('utf8')).hexdigest()==effective_plan['sha256']==body['effective_plan_sha256']
                plan=json.loads(raw.removeprefix('\ufeff'))
                assert plan==effective_plan['document']
                assert plan['page']==body['page']and plan['source_sha256']==body['source_sha256']
                slots=[p for p in plan['slots']if p['id']==identifier]
                assert len(slots)==1 and slots[0]['source']==parts[0]['source_text']
                full=slots[0]['text'];assert isinstance(full,str)
                ordered=sorted(parts,key=lambda p:p['target_char_start'])
                assert ranges[-1][1]==len(full)
                for p in ordered:
                    start,end=p['target_char_start'],p['target_char_end']
                    assert 0<=start<=end<=len(full)and p['text']==full[start:end]
                for a,b in zip(ordered,ordered[1:]):
                    end,start=a['target_char_end'],b['target_char_start']
                    assert end<=start and (end==start or (start==end+1 and full[end:start]==' '))
                    assert number(b['baseline'])-number(a['baseline'])>.002
            else:
                assert all(a[1]==b[0]for a,b in zip(ranges,ranges[1:]))
            # A baseline alone must uniquely identify a chunk. No guessed
            # origin-based fallback for duplicate IDs on the same baseline.
            baselines=sorted(number(p['baseline'])for p in parts)
            assert all(b-a>.002 for a,b in zip(baselines,baselines[1:]))
    for i,p in enumerate(body.get('raster_labels',[])):
        key='raster:'+str(i);labels.append((key,p));add(p,key,True)
    corrections=body['r4_source_style_corrections'];corrected=set()
    for c in corrections:
        candidates=[key for key in body_ids[c['source_slot_id']]
                    if specs[key]['placement']['text']==c['target_text']
                    and abs(number(specs[key]['placement']['baseline'])-number(c['baseline']))<=.001]
        assert len(candidates)==1
        key=candidates[0];s=specs[key];p=s['placement']
        assert key not in corrected and s['angle']==14 and c['target_text']==p['text']
        assert abs(number(c['baseline'])-number(p['baseline']))<=.001
        assert c['original_descriptor_angle']==-14 and c['physical_target_angle']==14
        assert c['original_point_size_and_logical_origin_unchanged']is True
        assert abs(number(c['physical_pdf_shear_c'])-math.tan(math.radians(14)))<=1e-6
        corrected.add(key)
    assert corrected=={key for key,s in specs.items()if not s['label']and s['angle']==14}
    def resolve(identifier,baseline):
        if identifier in body_ids:
            found=[key for key in body_ids[identifier]
                   if abs(number(specs[key]['placement']['baseline'])-number(baseline))<=.001]
            assert len(found)==1,('Unknown or ambiguous source ID/baseline',identifier,baseline)
            return found[0]
        found=[]
        for key,p in labels:
            prefix='raster:'+p['source_text']+':'
            if identifier.startswith(prefix):
                try:rect=json.loads(identifier[len(prefix):])
                except(ValueError,TypeError):continue
                if rect==p['rect']:found.append(key)
        assert len(found)==1,('Unknown or ambiguous source ID',identifier)
        return found[0]
    physical=audit['actual_full_Tm_CTM_physical_transform_audit']
    assert physical['passed']is True and physical['source_rotation_plan_bound_to_P0_layout']is True
    assert physical['unaccounted_glyphs']==physical['unbound_streams']==0
    mt=number(physical['linear_matrix_tolerance']);gt=number(physical['glyph_origin_tolerance_pt'])
    assert 0<mt<=1e-6 and 0<gt<=.001
    rows=physical['source_bound_transform_streams']
    assert integer(physical['all_actual_KO_streams_verified'])==len(rows)>0
    xrefs=set();counts=Counter();spaces=Counter();italic=[];bound=[]
    for row in rows:
        xref=integer(row['xref'],1);assert xref not in xrefs;xrefs.add(xref)
        assert re.fullmatch('[0-9a-f]{64}',row['raw_stream_sha256'])
        # The current immutable producer paints one source slot per TJ stream.
        assert len(row['source_ids'])==1
        key=resolve(row['source_ids'][0],row['baseline']);s=specs[key]
        assert row['source_label']is s['label']and row['font_alias']==s['alias']
        assert row['planned_rotation']==s['rotation']and row['planned_physical_shear_angle']==s['angle']
        count=integer(row['glyphs_including_spaces'],1);white=integer(row['spaces']);assert white<=count
        counts[key]+=count;spaces[key]+=white
        entry=row['canonical_entry_graphics_state']
        near(vector(entry['ctm'],6),[1,0,0,1,0,0],mt)
        assert number(entry['fill_alpha'])==number(entry['stroke_alpha'])==1
        assert entry['unsafe_styles']=={}and entry['clip']is False
        assert set(entry['text'])=={'Tc','Tw','Ts','Tz','Tr'}
        for k,v in{'Tc':0,'Tw':0,'Ts':0,'Tz':100,'Tr':0}.items():assert number(entry['text'][k])==v
        assert number(row['actual_fill_opacity'])==number(row['actual_stroke_opacity'])==1
        composed=vector(row['composed_text_matrix_pdf'],6)
        replay=multiply(row['actual_text_matrix'],row['actual_CTM_at_paint'])
        near(replay[:4],composed[:4],mt);near(replay[4:],composed[4:],gt)
        residual=multiply(rotation((-s['rotation'])%360),composed)[:4]
        expected=[1,0,math.tan(math.radians(s['angle'])),1]
        near(vector(row['rotation_removed_linear'],4),residual,mt)
        near(vector(row['expected_rotation_removed_linear'],4),expected,mt)
        error=max(abs(a-b)for a,b in zip(residual,expected));assert error<=mt
        assert 0<=number(row['max_linear_error'])<=mt and abs(row['max_linear_error']-error)<=1e-9
        assert abs(number(row['physical_pdf_cm_c'])-residual[2])<=mt
        length=math.hypot(composed[0],composed[1]);assert length>0
        direction=[composed[0]/length,-composed[1]/length]
        near(vector(row['actual_baseline_direction'],2),direction,mt)
        horizontal=abs(direction[1])<=1e-6 and abs(abs(direction[0])-1)<=1e-6
        assert row['horizontal_for_row_pairs']is horizontal
        assert 0<=number(row['max_actual_replay_origin_error_pt'])<=gt
        if not s['label']:assert abs(number(row['baseline'])-number(s['placement']['baseline']))<=gt
        else:number(row['baseline'])
        if s['angle']:italic.append(row)
        bound.append((row,s,composed))
    assert {k for k,v in counts.items()if v}=={k for k,s in specs.items()if s['count']}
    for key,s in specs.items():assert counts[key]==s['count']and spaces[key]==s['spaces'],('Source glyph/space coverage',key)
    assert sum(counts.values())==physical['all_KO_glyphs_including_spaces_verified']==expected_total
    assert sum(spaces.values())==physical['spaces_verified']==expected_spaces
    assert physical['source_bound_italic_streams']==italic==audit['actual_target_physical_shear']
    # This R4 report's page coordinates have the canonical y flip. Infer only
    # its common origin; absolute glyph positions are independently audited.
    offsets=[number(s['placement']['baseline'])+m[5]for row,s,m in bound if not s['label']]
    assert offsets and max(offsets)-min(offsets)<=gt
    for row,s,m in bound:assert abs(number(row['baseline'])-(offsets[0]-m[5]))<=gt
    nonspace=expected_total-expected_spaces
    geometry(audit['original_full_master_geometry'],nonspace)
    geometry(audit['actual_including_space_glyph_geometry'],expected_total)
    assert audit['actual_outline_and_encoded_W_audit_pending']is False
    outline=audit['actual_outline_and_encoded_W_audit']
    assert outline['passed']is True and outline['errors']==[]and outline['master_hmtx_and_gid_exact']is True
    assert outline['actual_CID_TJ_W_glyphs_verified']==outline['actual_master_outline_bounds_verified']==nonspace
    assert 0<number(outline['tolerance_pt'])<=.001
    for field in['actual_W_TJ_replay_max_origin_error_pt','max_transformed_outline_error_pt']:assert 0<=number(outline[field])<=.001
    encoded=outline['encoded_glyph_details'];assert len(encoded)==nonspace
    observed=Counter()
    for glyph in encoded:
        assert isinstance(glyph['character'],str)and len(glyph['character'])==1 and not glyph['character'].isspace()
        observed[(glyph['alias'],glyph['character'])]+=1
        integer(glyph['gid'],1);integer(glyph['cid'],1)
        assert math.isfinite(float(glyph['encoded_W']))and float(glyph['encoded_W'])>0
        near(vector(glyph['actual_origin'],2),vector(glyph['replayed_origin'],2),.001)
        assert re.fullmatch('[0-9a-f]{64}',outline['actual_font_program_sha256'][glyph['alias']])
    assert observed==expected_chars,'Unaccounted encoded CID/W glyph'
    ink=audit['actual_stream_interrow_ink']
    assert ink['passed']is True and ink['all_target_KO_glyphs_accounted_for']is True and ink['each_extracted_row_glyph_trace_matches_target']is True
    assert ink['stream_count']==len(rows)and ink['scale']==2 and ink['threshold']==220
    assert ink['same_row_tolerance_pt']==.001 and ink['close_row_selection_em']==1.1
    orthogonal=[r for r in rows if not r['horizontal_for_row_pairs']]
    excluded=ink['orthogonal_streams_excluded_from_horizontal_pairs']
    assert len(excluded)==len(orthogonal)
    for x,r in zip(excluded,orthogonal):assert x['xref']==r['xref']and x['aliases']==[r['font_alias']]and x['tm']==r['actual_text_matrix']
    grouped=[]
    for row,s,_ in sorted((v for v in bound if v[0]['horizontal_for_row_pairs']),key=lambda v:v[0]['baseline']):
        if not grouped or abs(grouped[-1][0]-row['baseline'])>.001:grouped.append([row['baseline'],s['size']])
        else:grouped[-1][1]=max(grouped[-1][1],s['size'])
    pairs=[(u[0],d[0],d[0]-u[0])for i,u in enumerate(grouped)for d in grouped[i+1:]if d[0]-u[0]<max(u[1],d[1])*1.1]
    assert ink['rows']==len(grouped)and ink['tested_close_row_pairs']==len(ink['pairs'])==len(pairs)
    for actual,wanted in zip(ink['pairs'],pairs):
        near([actual['upper_baseline'],actual['lower_baseline'],actual['gap_pt']],wanted,.001);assert actual['contact_pixels_2x']==0
    for pair in ink['corrected_special_pair_multiscale']:assert pair['contact_pixels_by_scale']=={'2':0,'4':0,'8':0}
    assert ink['failures']==[]
    native=audit['actual_target_language_vs_native_ink']
    assert native['passed']is True and native['actual_KO_vs_original_remaining_ink_contact_pixels_2x']==0
    assert native['original_font_resources_preserved_in_both_controls']is True
    return dict(status=STATUS,page=body['page'],streams=len(rows),glyphs_including_spaces=expected_total,spaces=expected_spaces,
        nonspace_glyphs=nonspace,source_ids=sum(s['count']>0 for s in specs.values()),italic_streams=len(italic))
