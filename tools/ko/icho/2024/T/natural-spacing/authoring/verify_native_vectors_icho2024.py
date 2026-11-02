"""Check original vector paths and explicitly reviewed prose-only Form edits."""
from pathlib import Path
import argparse,hashlib,json,sys
BASE=Path(__file__).resolve().parent;sys.path.insert(0,str(BASE/'engine'))
import latex_native_motion as motion
def verify(path):
    path=Path(path);report=json.loads(path.with_suffix('.layout.json').read_text('utf8'))
    source=motion.inspect_inline_groups(Path(report['source']),report['page']);final=motion.inspect_inline_groups(path,1)
    old=source['vector_paths'];new=final['vector_paths']
    offsets={tuple(p['operator_indices']):s['dx']for s in report['native_shifts']for p in s.get('vector_paths',[])}
    errors=[];moved=0;stationary=0
    if len(new)<len(old):errors.append({'kind':'missing_native_paths','before':len(old),'after':len(new)})
    for i,(a,b)in enumerate(zip(old,new)):
        dx=offsets.get(tuple(a['operator_indices']),0);want=[a['rect'][0]+dx,a['rect'][1],a['rect'][2]+dx,a['rect'][3]]
        delta=max(abs(x-y)for x,y in zip(want,b['rect']))
        if a['paint_operator']!=b['paint_operator']or delta>1e-7:errors.append({'path_index':i,'expected':want,'actual':b['rect'],'max_delta':delta})
        moved+=bool(dx);stationary+=not bool(dx)
    glyph_dx={motion.glyph_key(g):s['dx']for s in report['native_shifts']for g in s['glyphs']}
    remaining=list(final.get('forms',[]));form_paths=0;stationary_forms=0
    reviewed_edits=report.get('reviewed_form_prose_suppression_audit',[]);used_edits=set()
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
        candidates=[b for b in remaining if b['original_raw_sha256']==expected_stream and max(abs(x-y)for x,y in zip(want,b['native_page_bbox']))<=1e-4]
        if not candidates:errors.append({'kind':'form_stream_or_placement_changed','source_form_path':a['path']});continue
        b=candidates[0];remaining.remove(b)
        if not dx:
            stationary_forms+=1
            for field in ['entry_ctm','invocation_ctm','page_matrix']:
                if max(abs(x-y)for x,y in zip(a[field],b[field]))>1e-7:errors.append({'kind':'stationary_form_matrix_changed','source_form_path':a['path'],'field':field})
        if len(a['own_vector_paths'])!=len(b['own_vector_paths']):errors.append({'kind':'form_native_path_count_changed','source_form_path':a['path']});continue
        for j,(av,bv)in enumerate(zip(a['own_vector_paths'],b['own_vector_paths'])):
            want=[v+(dx if k%2==0 else 0)for k,v in enumerate(av['rect'])]
            if av['paint_operator']!=bv['paint_operator']or max(abs(x-y)for x,y in zip(want,bv['rect']))>1e-7:errors.append({'kind':'form_native_path_coordinate_changed','source_form_path':a['path'],'path_index':j})
            form_paths+=1
    if used_edits!=set(range(len(reviewed_edits))):errors.append({'kind':'unmatched_reviewed_Form_prose_edit'})
    result={'native_vector_paths_verified':len(old),'moved_whole_expression_paths_verified':moved,'stationary_paths_including_vector_figures_verified':stationary,'coordinate_errors':errors,
            'form_native_vector_paths_verified':form_paths,'stationary_form_invocations_verified':stationary_forms,'reviewed_prose_only_form_stream_edits_verified':len(used_edits),
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
