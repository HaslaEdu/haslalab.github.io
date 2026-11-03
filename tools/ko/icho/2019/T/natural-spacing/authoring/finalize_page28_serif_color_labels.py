from pathlib import Path
import json,hashlib
import author_outlined_vector_labels as a
B=Path(__file__).resolve().parent;R=B/'graphic-language-audit-01-56-20261103';data=json.loads((R/'graphic-language-audit-report.json').read_text('utf8'));profile=json.loads((R/'page28-source-vector-profile.json').read_text('utf8'));a.form=lambda n:profile['forms'][0]
for v in data['ordinary_uncovered_vector_labels']:
 if v['page']!=28:continue
 starts=[p['operator_indices'][0]for p in v['source_paths']];word=v['source_text'];ko=v['suggested_Korean'];kw=dict(reference_face='times.ttf',korean_role='serif')
 if word=='Dark Blue':a.add(28,v['id']+'-1','Dark','짙은',starts[:1],**kw);a.add(28,v['id']+'-2','Blue','청색',starts[1:],**kw)
 elif word=='Yello- / wish':a.add(28,v['id']+'-1','Yello-','노란',starts[:1],**kw);a.add(28,v['id']+'-2','wish','기운',starts[1:],**kw)
 elif word in['purple','Purple']:
  prefix=1938 if word=='purple'else 850
  a.add(28,v['id'],word,'보라',[prefix]+starts,english_start=v['label_ink_bbox_page_pt'][0],native_prefix_edge=prefix,clip=[v['label_ink_bbox_page_pt'][0]-.3,v['label_ink_bbox_page_pt'][1]-.3,v['label_ink_bbox_page_pt'][2]+.3,v['label_ink_bbox_page_pt'][3]+.3],**kw)
 else:a.add(28,v['id'],word,'분홍'if word=='Pink'else'노란빛'if word=='Yellowish'else ko,starts,left_anchor=word in['colourless','dark'],**kw)
labels=a.rows[28]
for label in labels:
 label['source_role_visual_review']='Original page28 read independently by main and the read-only graphic reviewer: contrast/terminal serifs in Blue/Pink/Brown are Times-like; page27 flow labels remain sans. Several Times outline word aspect fits share the same approximately3% original Form anisotropy, while Arial fits vary by word. Font/point metadata remains unavailable; selected serif role and physical vertical-em inference are explicit.'
 if label['id']in['p28-graphic-language-02','p28-graphic-language-12']:
  label['source_graphic_row_optical_clearance_y_pt']=.5;label['point'][1]+=.5;label['expected_new_korean_ink_bounds'][1]+=.5;label['expected_new_korean_ink_bounds'][3]+=.5
  label['source_font_size_basis']+=' The inferred Latin reference baseline is not original font metadata. New Korean label alone receives0.5pt downward optical clearance inside its original beaker phase after actual serif ink touched the fixed liquid-level line at2x; font point size and all original scientific/diagram y coordinates remain unchanged.'
p=B/'page28.overrides.json';q=json.loads(p.read_text('utf8'));q['__outlined_vector_labels__']=labels;p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8');(B/'page28-serif-color-label-review.json').write_text(json.dumps(dict(labels=labels,source_font_role_evidence_sha256=hashlib.sha256((B/'graphic-source-font-role-inference.json').read_bytes()).hexdigest(),same_semantic_compact_color_names={'purple':'보라','Pink':'분홍','Yellowish':'노란빛'},original_Dk_code_paths_horizontally_moved_only_inside_their_original_full_caption_center=True,source_family_and_point_metadata_inferred_not_direct=True),ensure_ascii=False,indent=2)+'\n','utf8');print(len(labels),flush=True)
