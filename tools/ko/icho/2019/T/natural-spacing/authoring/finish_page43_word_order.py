from pathlib import Path
import copy,json
import pymupdf as f
import natural_plan_compose_icho2019 as c
import icho2019_write_guard as g
import latex_native_motion as motion
B=Path(__file__).resolve().parent;path=B/'page43.overrides.json';q=json.loads(path.read_text('utf8'));edits=q.setdefault('__slot_edits__',{});extras=q.setdefault('__extra_slots__',[])
plan=json.loads((g.PLANS/'page43.ko.json').read_text('utf8'));slots={s['id']:s for s in plan['slots']+extras}
changes={'p43:b3:l1:s0-0:c12-30':' 크로마토그램:','p43:b3:l1:s6-6:c0-38':'를 용리 부피','p43:b6:l2:s0-0':'몰 질량의 로그값은 용리 부피'}
for id,text in changes.items():
    assert id in slots,id;edits.setdefault(id,{})['text']=text
for id,at,source,text,role in[
('p43-caption-after-native-Ve',[3,1,8,8],'.','의 함수로 나타냈다.','serif'),
('p43-log-after-native-Ve',[6,2,3,3],'. ','의 선형 함수이다.','serif')]:
    extras[:]=[s for s in extras if s['id']!=id];extras.append(dict(id=id,at=at,source=source,text=text,font_role=role,join_left=True))
glyphs=c._glyphs(f.open(g.SOURCE)[42]);native=[v for v in glyphs if v['c']in'Ve'and 399<v['origin'][0]<410 and 505<v['origin'][1]<509]
assert len(native)==2,native
for spec in q['__prose_vector_decorations__']:
    if spec['id']=='p43-missing-prose-underline-954':
        spec['target_fragments']=[dict(slot_id='p43:b6:l2:s0-0',target_text=changes['p43:b6:l2:s0-0'])]
        spec.pop('exclude_native_expression_glyphs_from_prose_underline',None)
        spec['review']+=' The natural Korean predicate follows the native V_e using the source full stop fragment and its separate original punctuation underline. Neither V nor its subscript is redrawn or resized.'
paths=motion.inspect_inline_groups(g.SOURCE,43)['vector_paths'];path2=[v for v in paths if max(abs(a-b)for a,b in zip(v['rect'],[409.989990234375,507.66998291015625,412.75,508.1499938964844]))<.001];assert len(path2)==1;v=path2[0]
id='p43-source-log-punctuation-underline';q['__prose_vector_decorations__'][:]=[s for s in q['__prose_vector_decorations__']if s['id']!=id]
q['__prose_vector_decorations__'].append(dict(id=id,target_fragments=[dict(slot_id='p43-log-after-native-Ve',target_text='의 선형 함수이다.')],source_fragments=[dict(slot_id='p43:b6:l2:s0-0',source_text=slots['p43:b6:l2:s0-0']['source']),dict(slot_id='p43-log-after-native-Ve',source_text='. ')],source_text='Original underlined log sentence including its full stop',source_rect=v['rect'],source_baseline=506.469970703125,operator_indices=v['operator_indices'],paint_operator=v['paint_operator'],fit_source_prose_underline_to_translated_phrase=True,source_prose_punctuation_underline=True,review='The original separate full-stop underline belongs to the same underlined English log sentence. Preserve its construction bytes, y, thickness, colour and paint; explicit horizontal prose-decoration expansion covers the Korean predicate after the native V_e. The source full stop and exact English sentence GIDs independently guard this punctuation path.'))
path.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
