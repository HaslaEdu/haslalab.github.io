"""Check original vector paths and explicitly reviewed prose-only Form edits."""
from pathlib import Path
import argparse,hashlib,json,sys,pikepdf,pymupdf as f
BASE=Path(__file__).resolve().parent;sys.path.insert(0,str(BASE/'engine'))
import latex_native_motion as motion
import icho2019_write_guard as year_guard

def verify_exact_English_path_wrappers(path,report,edit,source_info):
    """Reconstruct the entire actual Form from original bytes and narrow scopes."""
    with pikepdf.Pdf.open(report['source'])as source,pikepdf.Pdf.open(path)as final:
        original=source.pages[report['page']-1]
        for i in edit['source_form_path']:
            ins=pikepdf.parse_content_stream(original)[i];assert str(ins.operator)=='Do';original=original.Resources.XObject[ins.operands[0]]
        sha=lambda b:hashlib.sha256(b).hexdigest()
        assert sha(original.read_raw_bytes())==edit['source_raw_stream_sha256']
        candidates=[obj for obj in final.objects if isinstance(obj,pikepdf.Stream)and sha(obj.read_raw_bytes())==edit['translated_raw_stream_sha256']];assert len(candidates)==1;current=candidates[0]
        state=current.Resources.ExtGState['/KO_Reviewed_English_ZeroOpacity'];assert str(state.Type)=='/ExtGState'and float(state.ca)==float(state.CA)==0
        data,regions=motion._raw_regions(original);pieces=[];changes=[];seen=set();labels={v['id']:v for v in report['outlined_vector_labels']if v['source_form_raw_sha256']==edit['source_raw_stream_sha256']}
        matrices={};state0=tuple(source_info['entry_ctm']);stack=[]
        for i,ins in enumerate(pikepdf.parse_content_stream(original)):
            matrices[i]=motion._multiply(state0,source_info['page_matrix']);op=str(ins.operator)
            if op=='q':stack.append(state0)
            elif op=='Q':state0=stack.pop()
            elif op=='cm':state0=motion._multiply(tuple(map(float,ins.operands)),state0)
        declared={(v['id'],tuple(p['operator_indices']))for v in labels.values()for p in v['source_paths']}
        for item in edit['paths']:
            label=labels[item['id']];ref=item['source_path'];indices=ref['operator_indices'];key=(item['id'],tuple(indices));assert key in declared and key not in seen;seen.add(key)
            assert ref in label['source_paths'];native=indices in label.get('preserved_native_caption_edge_paths',[])
            area=f.Rect(label['english_clip_rect']);bounds=f.Rect(ref['rect']);mode='native-prefix-x-translation-only'if native else('outside-English-scope-x-translation-only'if not area.intersects(bounds)else'pure-English-path-zero-opacity'if area.contains(bounds)else'mixed-path-exact-English-clip')
            assert item['suppression_mode']==mode and item['reviewed_English_area_rect']==list(area)
            assert item['native_caption_path_dx_pt']==label.get('native_caption_path_dx_pt',0.)
            a,z=regions[indices[0]][0],regions[indices[-1]][1];fragment=data[a:z];assert sha(fragment)==item['original_construction_and_paint_fragment_sha256']
            matrix=item['local_translation_matrix'];assert matrix[:4]==[1,0,0,1]
            numbers=lambda p:' '.join(f'{v:.14f}'for v in p)
            extra='/KO_Reviewed_English_ZeroOpacity gs 'if mode=='pure-English-path-zero-opacity'else''
            if mode=='mixed-path-exact-English-clip':
                aa,bb,cc,dd,ee,ff=matrices[indices[0]];det=aa*dd-bb*cc
                points=[((dd*(x-ee)-cc*(y-ff))/det,(-bb*(x-ee)+aa*(y-ff))/det)for x,y in[(area.x0,area.y0),(area.x1,area.y0),(area.x1,area.y1),(area.x0,area.y1)]]
                assert points==[tuple(v)for v in item['local_clip_polygon']]
                extra='-1000000 -1000000 2000000 2000000 re '+numbers(points[0])+' m '+' '.join(numbers(p)+' l'for p in points[1:])+' h W* n '
            else:assert item['local_clip_polygon']is None
            prefix=('q 1 0 0 1 '+numbers(matrix[4:])+' cm '+extra).encode('ascii')
            changes.append((a,z,prefix+fragment+b' Q'))
        assert seen==declared
        at=0
        for a,z,replacement in sorted(changes):pieces.extend([data[at:a],b'\n',replacement,b'\n']);at=z
        pieces.append(data[at:]);assert current.read_bytes()==b''.join(pieces),'Actual Form has edits outside the exact source-English opacity/native-prefix x wrappers'
        assert sha(current.NativeInlineOriginal.read_raw_bytes())==edit['source_raw_stream_sha256']
    return True
def verify(path):
    path=Path(path);report=json.loads(path.with_suffix('.layout.json').read_text('utf8'))
    year_guard.assert_output(path,report['page'])
    if Path(report['source']).resolve()!=year_guard.SOURCE or report.get('source_sha256')!=year_guard.SOURCE_SHA:raise ValueError('Cross-year audit rejected')
    year_guard.assert_protected_2024()
    source=motion.inspect_inline_groups(Path(report['source']),report['page']);final=motion.inspect_inline_groups(path,1)
    old=source['vector_paths'];new=final['vector_paths']
    offsets={tuple(p['operator_indices']):s['dx']for s in report['native_shifts']for p in s.get('vector_paths',[])}
    prose_rects={tuple(p['operator_indices']):p['target_rect']for p in report.get('prose_vector_decorations',[])if p.get('prose_decoration_x_scale',1.)!=1.}
    errors=[];moved=0;stationary=0
    if len(new)<len(old):errors.append({'kind':'missing_native_paths','before':len(old),'after':len(new)})
    for i,(a,b)in enumerate(zip(old,new)):
        dx=offsets.get(tuple(a['operator_indices']),0);want=[a['rect'][0]+dx,a['rect'][1],a['rect'][2]+dx,a['rect'][3]]
        want=prose_rects.get(tuple(a['operator_indices']),want)
        delta=max(abs(x-y)for x,y in zip(want,b['rect']))
        if a['paint_operator']!=b['paint_operator']or delta>1e-7:errors.append({'path_index':i,'expected':want,'actual':b['rect'],'max_delta':delta})
        moved+=bool(dx);stationary+=not bool(dx)
    glyph_dx={motion.glyph_key(g):s['dx']for s in report['native_shifts']for g in s['glyphs']}
    remaining=list(final.get('forms',[]));form_paths=0;stationary_forms=0
    reviewed_edits=report.get('reviewed_form_prose_suppression_audit',[]);used_edits=set()
    vector_edits=report.get('reviewed_vector_prose_suppression_audit',[]);used_vector_edits=set()
    for a in source.get('forms',[]):
        deltas={glyph_dx.get(motion.glyph_key(g),0.)for g in a['glyphs']if g['c'].strip()}
        if len(deltas)>1:errors.append({'kind':'partial_form_motion','source_form_path':a['path']});continue
        dx=next(iter(deltas),0.)
        explicit=[s['dx']for s in report['native_shifts']if s.get('form_path')==a['path']]
        if explicit:dx=explicit[0]
        want=[v+(dx if j%2==0 else 0)for j,v in enumerate(a['native_page_bbox'])]
        expected_stream=a['original_raw_sha256']
        edits=[(ei,e)for ei,e in enumerate(reviewed_edits)if e['source_form_path']==a['path']and e['source_raw_stream_sha256']==expected_stream]
        if edits:
            if len(edits)!=1:raise ValueError('Ambiguous reviewed Form prose edit')
            ei,e=edits[0]
            fields=['only_reviewed_Tj_TJ_regions_replaced','all_other_original_content_bytes_identical','original_encoded_prose_codes_and_advances_retained_in_Tr3','form_and_ancestors_each_invoked_once']
            if not all(e.get(k)is True for k in fields):raise ValueError('Incomplete reviewed Form prose proof')
            expected_stream=e['translated_raw_stream_sha256'];used_edits.add(ei)
        v_edits=[(ei,e)for ei,e in enumerate(vector_edits)if e['source_form_path']==a['path']and e['source_raw_stream_sha256']==expected_stream]
        if v_edits:
            if len(v_edits)!=1:raise ValueError('Ambiguous outlined vector language Form edit')
            ei,e=v_edits[0]
            fields=['only_reviewed_English_path_opacity_or_exact_clip_and_caption_x_translations_added','all_original_construction_paint_and_other_bytes_retained','original_Form_reference_retained','all_other_native_paths_coordinates_and_paint_preserved']
            if not all(e.get(k)is True for k in fields)or e.get('changed_pixels_outside_reviewed_label_scopes')!=0 or e.get('original_form_glyph_count')!=0:raise ValueError('Incomplete outlined-vector language suppression proof')
            verify_exact_English_path_wrappers(path,report,e,a)
            expected_stream=e['translated_raw_stream_sha256'];used_vector_edits.add(ei)
        candidates=[b for b in remaining if b['original_raw_sha256']==expected_stream and max(abs(x-y)for x,y in zip(want,b['native_page_bbox']))<=1e-4]
        if not candidates:errors.append({'kind':'form_stream_or_placement_changed','source_form_path':a['path']});continue
        b=candidates[0];remaining.remove(b)
        if not dx:
            stationary_forms+=1
            for field in ['entry_ctm','invocation_ctm','page_matrix']:
                if max(abs(x-y)for x,y in zip(a[field],b[field]))>1e-7:errors.append({'kind':'stationary_form_matrix_changed','source_form_path':a['path'],'field':field})
        if len(a['own_vector_paths'])!=len(b['own_vector_paths']):errors.append({'kind':'form_native_path_count_changed','source_form_path':a['path']});continue
        for j,(av,bv)in enumerate(zip(a['own_vector_paths'],b['own_vector_paths'])):
            pathdx=0.
            if v_edits:
                pathmoves=[p.get('native_caption_path_dx_pt',0.)for p in v_edits[0][1]['paths']if p['source_path']['operator_indices']==av['operator_indices']]
                if len(pathmoves)>1:raise ValueError('Ambiguous original caption path movement')
                pathdx=next(iter(pathmoves),0.)
            want=[v+(dx+pathdx if k%2==0 else 0)for k,v in enumerate(av['rect'])]
            if av['paint_operator']!=bv['paint_operator']or max(abs(x-y)for x,y in zip(want,bv['rect']))>1e-7:errors.append({'kind':'form_native_path_coordinate_changed','source_form_path':a['path'],'path_index':j})
            form_paths+=1
    if used_edits!=set(range(len(reviewed_edits))):errors.append({'kind':'unmatched_reviewed_Form_prose_edit'})
    if used_vector_edits!=set(range(len(vector_edits))):errors.append({'kind':'unmatched_reviewed_vector_language_edit'})
    result={'native_vector_paths_verified':len(old),'moved_whole_expression_paths_verified':moved,'stationary_paths_including_vector_figures_verified':stationary,'coordinate_errors':errors,
            'form_native_vector_paths_verified':form_paths,'stationary_form_invocations_verified':stationary_forms,'reviewed_prose_only_form_stream_edits_verified':len(used_edits),
            'reviewed_outlined_vector_language_Form_edits_verified':len(used_vector_edits),
            'form_bbox_serialization_tolerance_pt':1e-4,'audit_code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'max_coordinate_tolerance_pt':1e-7,'added_raster_language_mask_paths':len(new)-len(old)}
    report['actual_native_vector_coordinate_audit']=result
    path.with_suffix('.layout.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8')
    if errors:raise ValueError(json.dumps(result,ensure_ascii=False))
    print(path.name,'vectors',len(old),'Form paths',form_paths,'prose-only Form edits',len(used_edits),'PASS',flush=True)
    return result
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('pdfs',nargs='+',type=Path);args=parser.parse_args()
    for path in args.pdfs:
        for pdf in sorted(path.glob('page[0-9][0-9].pdf'))if path.is_dir()else[path]:verify(pdf)
