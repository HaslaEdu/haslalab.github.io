"""Source-bound full-matrix physical style check; rotated labels are not skipped."""
from pathlib import Path
from collections import defaultdict
import hashlib,json,math
import pikepdf
import pymupdf as f
from amended_actual_paint import streams
from r4_font_widths import decimals,to_unicode

def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _alias(want,year):
    if want['label']:
        return 'KO_Natural_Raster' if year==2026 else 'KO_Natural_Raster_'+want['role'].replace('-','_')
    return 'KO_Natural_'+want['role'].replace('-','_')

def verify_physical_streams(target,q,cfg,matched_all):
    """Every CID, including spaces, consumes one exact planned/actual glyph.

    Only source-declared label rotation is removed. The resulting complete
    linear map must be identity or the source-bound +14 degree body shear.
    Scale, a reversed rotation, hidden shear, or an unplanned rotation fail.
    """
    assert q['source_sha256']==cfg['source_sha256']
    reference=next(v for v in cfg['reference_pages'] if v['page']==q['page'])['P0']
    assert _sha(reference['layout_path'])==reference['layout_sha256']
    oldq=json.loads(Path(reference['layout_path']).read_text('utf8'))
    assert q.get('raster_labels',[])==oldq.get('raster_labels',[]),'Source-bound raster label plan changed'
    resources={}
    with pikepdf.Pdf.open(target) as pdf:
        for name,font in pdf.pages[0].Resources.Font.items():
            alias=str(name).lstrip('/')
            if not alias.startswith('KO_Natural_'):continue
            widths,default=decimals(font.DescendantFonts[0].W,font.DescendantFonts[0].get('/DW',1000))
            resources[alias]=(widths,default,to_unicode(font.ToUnicode.read_bytes()))
    groups=defaultdict(list)
    for index,pair in enumerate(matched_all):
        want=pair['expected'];groups[(want['cp'],_alias(want,cfg['year']),round(want['size'],4))].append((index,pair))
    reports=[];italic=[];used=set();all_spaces=0
    with f.open(target) as doc:
        records=streams(doc[0])
        for record in records:
            widths,default,unicode_map=resources[record['font_alias']]
            matrix=f.Matrix(*record['composed_text_matrix_page']);cursor=0.;bindings=[]
            for token in record['tj_tokens']:
                if isinstance(token,float):
                    cursor-=token*record['size']/1000;continue
                assert len(token)%2==0
                for j in range(0,len(token),2):
                    cid=int.from_bytes(token[j:j+2],'big');text=unicode_map[cid];assert len(text)==1
                    point=f.Point(cursor,0)*matrix
                    options=groups[(ord(text),record['font_alias'],round(record['size'],4))]
                    assert options,('Unbound actual KO CID',record['xref'],cid,text,list(point))
                    k=min(range(len(options)),key=lambda k:max(abs(a-b) for a,b in zip(options[k][1]['actual']['origin'],point)))
                    index,pair=options.pop(k);assert index not in used;used.add(index)
                    delta=max(abs(a-b) for a,b in zip(pair['actual']['origin'],point))
                    assert delta<=.001,('Full CTM/W/TJ replay differs from actual glyph',record['xref'],text,delta)
                    want=pair['expected'];placement=want['placement']
                    if want['label']:
                        assert placement in oldq.get('raster_labels',[])
                        source_id='raster:'+placement['source_text']+':'+json.dumps(placement['rect'])
                        assert want['angle']==0
                    else:
                        source_id=placement['id']
                        if want['angle']:
                            entries=[v for v in cfg['source_style_entries'] if v['source_slot_id']==placement['id'] and v['target_text']==placement['text'] and abs(v['baseline_pt']-placement['baseline'])<.001]
                            assert len(entries)==1
                            assert want['angle']==entries[0]['desired_pdf_glyph_space_shear_angle']==14
                            assert placement['font_role']==entries[0]['font_role']
                    bindings.append((want['rotation'],want['angle'],want['label'],source_id,text,delta))
                    all_spaces+=text.isspace()
                    cursor+=float(widths.get(cid,default))*record['size']/1000
            assert bindings,('KO stream has no source-bound glyph, including spaces',record['xref'])
            planned={(v[0],v[1],v[2]) for v in bindings};assert len(planned)==1
            rotation,angle,label=planned.pop()
            assert rotation in (0,90,180,270) and (label or rotation==0)
            residual=(~f.Matrix(rotation))*f.Matrix(*record['composed_text_matrix_pdf'])
            expected=[1.,0.,math.tan(math.radians(angle)),1.]
            actual=[residual.a,residual.b,residual.c,residual.d]
            error=max(abs(a-b) for a,b in zip(actual,expected))
            assert error<=1e-6,('Source-bound full R^-1(Tm*CTM) physical transform differs',record['xref'],rotation,angle,actual,expected,error)
            row=dict(xref=record['xref'],font_alias=record['font_alias'],source_ids=sorted({v[3] for v in bindings}),
                source_label=label,planned_rotation=rotation,planned_physical_shear_angle=angle,
                baseline=record['actual_baseline'],physical_pdf_cm_c=residual.c,
                actual_text_matrix=record['text_matrix'],actual_CTM_at_paint=record['cm'],
                composed_text_matrix_pdf=record['composed_text_matrix_pdf'],rotation_removed_linear=actual,
                expected_rotation_removed_linear=expected,max_linear_error=error,
                canonical_entry_graphics_state=record['canonical_entry_graphics_state'],
                actual_fill_opacity=record['actual_fill_opacity'],actual_stroke_opacity=record['actual_stroke_opacity'],
                actual_baseline_direction=record['actual_baseline_direction'],horizontal_for_row_pairs=record['horizontal'],
                glyphs_including_spaces=len(bindings),spaces=sum(v[4].isspace() for v in bindings),
                max_actual_replay_origin_error_pt=max(v[5] for v in bindings),raw_stream_sha256=record['raw_sha256'])
            reports.append(row)
            if angle:italic.append(row)
    assert not any(groups.values()),'A planned/actual KO glyph was not consumed by full-stream replay'
    assert len(used)==len(matched_all)
    assert bool(italic)==bool(q['r4_source_style_corrections'])
    return dict(passed=True,method='Parsed q/Q/cm/Tm graphics stack at actual TJ paint, source-declared R removed before full linear-map comparison',
        source_rotation_plan_bound_to_P0_layout=True,all_actual_KO_streams_verified=len(reports),
        all_KO_glyphs_including_spaces_verified=len(used),spaces_verified=all_spaces,
        unaccounted_glyphs=0,unbound_streams=0,linear_matrix_tolerance=1e-6,glyph_origin_tolerance_pt=.001,
        source_bound_italic_streams=italic,source_bound_transform_streams=reports)
