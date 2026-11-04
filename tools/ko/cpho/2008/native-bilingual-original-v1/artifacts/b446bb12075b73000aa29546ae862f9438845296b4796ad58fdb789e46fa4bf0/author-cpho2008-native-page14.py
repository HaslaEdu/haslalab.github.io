import sys as _atomic_sys
from pathlib import Path as _AtomicPath
_atomic_sys.path.insert(0,str(_AtomicPath(__file__).resolve().parents[1]/'engine'))
from cpho2008_atomic_authoring import atomic_text
"""Source-read double-junction derivation, fixed physical table columns."""
from pathlib import Path
import json,re,hashlib
B=Path(__file__).resolve().parents[1];A=B/'authoring';q=json.loads((A/'page14-native-row-proposals.json').read_text('utf8'))
T=[
('[[0]]. 문제 그림 [[1]] 왼쪽 [[2]] 접합의 정전용량은','[[0]]. Fig. [[1]]: left [[2]] capacitance'),
('[[0]], 오른쪽 [[1]] 접합은 [[2]]이다. 이중 접합을','[[0]]; right [[1]] capacitance [[2]]. The pair'),
('그림 [[0]]로 나타내자. [[1]]는 [[2]][[3]]','Fig. [[0]]: charges [[1]] on [[2]][[3]]'),
('[[0]]의 전하이다. 가운데 단전자섬의','[[0]]. The net island charge is'),
('그림 [[0]]','Fig. [[0]]'),
('순전하량은 다음과 같다.','given by'),
('계의 정전 에너지는 [[0]]와 [[1]]에 저장된 에너지의 합이다. 즉','The electrostatic energy is the sum of that in [[0]] and [[1]]:'),
('전압은 다음과 같다.','The voltage is'),
('식 [[0]][[1]][[2]]을 풀면 다음과 같다.','Solving [[0]][[1]][[2]] gives'),
('[[0]]가 일정하므로 식 [[1]]에서 섬의 순전하에 따른 계의 정전 에너지 성분은','With constant [[0]], [[1]] gives the energy due only to net island charge:'),
('[[0]][[1]] [[2]] 대 [[3]]의 그래프는 그림 [[4]][[5]] [[6]] 범위는 표 [[7]]과 같다[[8]]','[[0]][[1]] [[2]] versus [[3]]: Fig. [[4]][[5]] [[6]] ranges: Table [[7]][[8]]'),
('표 [[0]]','Table [[0]]'),
('[[0]]의 범위','[[0]] range'),
('그림 [[0]]','Fig. [[0]]'),
]
assert len(T)==len(q['rows'])
for r,(ko,en)in zip(q['rows'],T):
 if r['id']=='r09':r['complete_original_two_line_island_energy_stationary']=r['native_atoms'][2:];r['native_atoms']=r['native_atoms'][:2]
 if r['id']=='r12':
  r['distinct_original_four_table_value_columns_stationary']=r['native_atoms'][1:];r['native_atoms']=r['native_atoms'][:1];r['original_center']=(r['native_atoms'][0]['rect'][0]+max(g['bbox'][2]for g in r['erase_glyphs']))/2
 if r['id']in['r02','r10']:
  colored=[g for g in r['erase_glyphs']if g['color']==[1.,0.,1.]];assert len(colored)==1 and colored[0]['c']=='图'
  r['source_prose_color_literals']=[dict(source_glyph=colored[0],ko='그림',en='Fig.')]
 bounds=[89,315]if r['id']in['r00','r01','r02','r03','r05']else[89,465.84]if r['id']=='r09'else[106,233]if r['id']=='r12'else[89,506]
 r.update(ko=ko,en=en,reviewed=True,align='center'if r['id']in['r04','r11','r12','r13']else'left',allowed_horizontal=bounds)
 for a in r['native_atoms']:
  assert not a['proposed_vector_paths'];a.update(vector_paths=[],reviewed=True,source_review_reason='Exact complete native inline expression/reference. Full original two-line island-energy program stays fixed; genuine four separate table value columns, table grids/displays, original diagram/plot/images and all equation counters remain stationary. Magenta in-prose figure tags have source-CID-bound translated color literals.')
 for lang in ['ko','en']:assert sorted(map(int,re.findall(r'\[\[(\d+)\]\]',r[lang])))==list(range(len(r['native_atoms']))),(r['id'],lang)
ink_path=B/'inspection/page14-authored-original-native-outline-bounds.json'
ink=json.loads(ink_path.read_text('utf8'));assert ink['source_sha256']==q['source_sha256'];outlines={v['id']:v for v in ink['atoms']}
for row in q['rows']:
 for atom in row['native_atoms']:
  evidence=outlines[atom['id']];assert atom['rect']==evidence['source_metric_rect'];original=atom['rect'];actual=evidence['actual_original_ink_rect']
  atom['source_metric_rect']=original[:];atom['rect']=[min(original[0],actual[0]),original[1],max(original[2],actual[2]),original[3]]
  atom['actual_original_outline_envelope_evidence']=dict(path=str(ink_path),sha256=hashlib.sha256(ink_path.read_bytes()).hexdigest(),atom_id=atom['id'])
q.update(source_only_proposal=False,all_source_language_and_native_expressions_manually_reviewed=True,source_inline_magenta_figure_tag_translation_requires_native_color_binding=True,publication_ready=False)
atomic_text(A/'page14-native-language.json', json.dumps(q,ensure_ascii=False,indent=2)+'\n', 'utf8');print('C08_PAGE14_ALL_SOURCE_PROSE_MANUALLY_AUTHORED',len(T))
