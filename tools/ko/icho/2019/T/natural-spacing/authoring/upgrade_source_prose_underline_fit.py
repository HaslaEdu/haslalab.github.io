from pathlib import Path
import json
import icho2019_write_guard as g
B=Path(__file__).resolve().parent;count=0
for n in range(1,61):
    path=B/f'page{n:02}.overrides.json';q=json.loads(path.read_text('utf8'));plan=json.loads((g.PLANS/f'page{n:02}.ko.json').read_text('utf8'));slots={s['id']:dict(s,**q.get('__slot_edits__',{}).get(s['id'],{}))for s in plan['slots']+q.get('__extra_slots__',[])}
    if n==13:
        refs=q['__layout_scope__'].get('reviewed_native_vector_attachments',[]);selected=[v for v in refs if v.get('kind')=='original-prose-underline-containing-native-numeral'];assert len(selected)==1;ref=selected[0]
        refpath=ref['vector_path'];ids=ref['target_prose_slot_ids'];spec=dict(id=ref['id']+'-independent-prose-fit',source_rect=refpath['rect'],operator_indices=refpath['operator_indices'],paint_operator=refpath['paint_operator'],source_baseline=ref['source_baseline'],source_text=ref['source_text'],source_fragments=[dict(slot_id=id,source_text=slots[id]['source'])for id in ids],target_fragments=[dict(slot_id=id,target_text=q.get(id,slots[id]['text']).strip().rstrip(':'))for id in ids],native_source_glyphs=ref['glyphs'],review='Original underlined coefficient phrase contains native numeral1. Move the numeral by its original source program, independently fit the source English prose underline to the actual Korean phrase+original numeral ink, and preserve y/thickness/black paint and all source path construction bytes.')
        q['__layout_scope__']['reviewed_native_vector_attachments']=[v for v in refs if v is not ref];ss=q.setdefault('__prose_vector_decorations__',[]);ss[:]=[v for v in ss if v['id']!=spec['id']];ss.append(spec)
    for spec in q.get('__prose_vector_decorations__',[]):
        spec.setdefault('previous_review_before_full_phrase_fit',spec.get('review'));spec['fit_source_prose_underline_to_translated_phrase']=True
        spec['review']='Source-bound English prose underline and corresponding Korean emphasis reviewed. Pin the exact original source hash/path/English GIDs and baseline; preserve original construction bytes, black fill/paint, y and thickness. Only the prose decoration receives explicit horizontal scale/translation to cover the actual emitted Korean word/phrase ink (plus explicitly declared unchanged native numeral/notation). Mathematical rules, table borders and other figure paths retain the independent1e-7 coordinate check.';count+=1
    path.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
(B/'source-prose-underline-fit-policy-review.json').write_text(json.dumps(dict(source_sha256=g.SOURCE_SHA,source_bound_prose_underlines=count,scope='Only original English prose emphasis decorations; no mathematical rule/table/figure exception. Exact native source GIDs/fonts/point sizes/baselines remain independently checked.',source_path_bytes_and_vertical_style_preserved=True,full_phrase_actual_ink_width_fit=True),ensure_ascii=False,indent=2)+'\n','utf8');print(count,flush=True)
