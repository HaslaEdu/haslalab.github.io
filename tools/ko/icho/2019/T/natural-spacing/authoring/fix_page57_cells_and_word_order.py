from pathlib import Path
import json
import pymupdf as f
import icho2019_write_guard as g
B=Path(__file__).resolve().parent;path=B/'page57.overrides.json';q=json.loads(path.read_text('utf8'));edits=q.setdefault('__slot_edits__',{});sc=q['__layout_scope__'];doc=f.open(g.SOURCE);p=doc[56];bs=p.get_text('rawdict')['blocks'];plan=json.loads((g.PLANS/'page57.ko.json').read_text('utf8'));slots={s['id']:s for s in plan['slots']+q.get('__extra_slots__',[])}
changes={'p57:b10:l1:s2-2':'지정하라.','p57:b10:l1:s3-3':'그리고 답의','p57:b10:l1:s5-5':'-라이신 염산염의 입체중심 절대 배치를','p57:b10:l1:s6-6':'근거를 제시하라.','p57:b10:l2:s0-0':'치환기를 우선순위대로 나열하여 설명하라.','p57:b14:l0:s0-0:c0-9':'순위'}
for id,text in changes.items():assert id in slots;edits.setdefault(id,{})['text']=text
edits['p57:b14:l0:s0-0:c0-9']['source_word_right_aligned_label']=True
moves=[('p57:b10:l1:s2-2','p57:b10:l1:s5-5'),('p57:b10:l1:s3-3','p57:b10:l1:s2-2')]
sc['reviewed_prose_line_token_moves']=[dict(id='p57-Q1-natural-Korean-predicates',source_sha256=g.SOURCE_SHA,source_line=[10,1],source_baseline=317.80999755859375,moves=[dict(slot_id=a,after_slot_id=b,source_guards=dict(slot_id=slots[a]['source'],after_slot_id=slots[b]['source']))for a,b in moves],review='Original Assign/justify emphasis remains at its original row/point/font role; move only source-bound Korean command tokens after their objects within the same row. Native L atom keeps its exact source glyph/font/size/baseline; all atoms appear once.')]
existing=sc.get('fixed_grid_inline_source_lines',[]);sc['fixed_grid_inline_source_lines']=[list(v)for v in sorted({tuple(v)for v in existing+[[11,0],[14,0]]})]
sc['fixed_prose_baselines']=sorted(set(sc.get('fixed_prose_baselines',[])+[353.4499816894531]))
sc['fixed_inline_group_column_bounds']=[dict(source_line=[b,l],right=176.89999389648438 if b==11 else 524.25,source_rect=list(bs[b]['lines'][l]['bbox']))for b,l in[[11,0],[14,0]]]
chars=bs[14]['lines'][0]['spans'][0]['chars'];assert ''.join(c['c']for c in chars)=='Priority 1 > 2 > 3 > 4: '
sc['native_only_stationary_rects']=sc.get('native_only_stationary_rects',[])+[[chars[9]['origin'][0]-.1,343.37,282.1,356.]]
sc['source_answer_header_cell_review']=dict(source_vertical_border=[176.89999389648438,343.3699951171875,177.37998962402344,416.3299865722656],source_left_header_line=[11,0],source_right_header_line=[14,0],right_label_translation='순위',native_priority_digits_inequalities_and_punctuation_stationary_rect=sc['native_only_stationary_rects'][-1],review='Actual source black vertical border divides Configuration from Priority. Independent source header groups preserve that boundary; compact Korean 순위 retains Priority meaning and is aligned to the original nonspace word right edge. Original numeric priority chain keeps exact source coordinates/fonts/sizes/baseline.')
for s in q['__prose_vector_decorations__']:
    if s.get('slot_id')=='p57:b10:l1:s2-2':s['target_text']='지정하라'
path.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
