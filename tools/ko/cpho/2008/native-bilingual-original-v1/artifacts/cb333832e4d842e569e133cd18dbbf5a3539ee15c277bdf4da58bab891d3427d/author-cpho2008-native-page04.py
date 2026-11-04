import sys as _atomic_sys
from pathlib import Path as _AtomicPath
_atomic_sys.path.insert(0,str(_AtomicPath(__file__).resolve().parents[1]/'engine'))
from cpho2008_atomic_authoring import atomic_text
"""Source-read Coulomb blockade page; original diagram/plot labels stationary."""
from pathlib import Path
from copy import deepcopy
import json,re,hashlib
B=Path(__file__).resolve().parents[1];A=B/'authoring';q=json.loads((A/'page04-native-row-proposals.json').read_text('utf8'))
T=[
('한 전자의 이산적 전하이다. 터널링이 계의 정전 에너지를 높이면 일어날 수 없다.','discrete electron charge. Tunnelling cannot raise the electrostatic energy.'),
('이를 쿨롱 봉쇄라 한다. 축전기 판 사이 전위차 [[0]]가 어떤','This is Coulomb blockade. For plate potential difference [[0]], find'),
('범위일 때 단전자 터널링이 금지되는지, 쿨롱 봉쇄 조건을 구하라.','for which single-electron tunnelling is forbidden, that is, the blockade condition.'),
('[[0]]. [[1]]가 터널링이 막 가능해지는 전압일 때, 정전용량 [[2]]를 추정하라.','[[0]]. If [[1]] just permits tunnelling, estimate the capacitance [[2]].'),
('[[0]]. 그림 [[1]] 소자를 전압 [[2]]의 정전압원에 연결할 때, 보통 그림 [[3]]의 이중 접합으로','[[0]]. When connecting Fig. [[1]] to a constant source [[2]], the double junction in Fig. [[3]]'),
('단전자 터널링을 관측해 표유 정전용량의 영향을 피한다. 가운데 금속층은 단전자섬이다.','avoids stray capacitance in observing tunnelling. The middle metal layer is'),
('좌우 금속 전극을 [[0]]라 하자. 섬의 순전하가 [[1]]이면 순전자수 [[2]]은 양의 정수,','the single-electron island; electrodes [[0]]. Its charge [[1]] has integer [[2]],'),
('음의 정수, 또는 0이다. [[0]]는 전자 전하의 크기이다. 두 [[1]] 접합의 정전용량을 [[2]], [[3]]라','positive, negative or zero. [[0]] is charge magnitude; [[1]] capacitances [[2]], [[3]].'),
('할 때, 섬의 순전하와 관련된 정전 에너지(단전자섬의 정전 에너지)가 다음임을 보여라.','Show that the charge-dependent (island) electrostatic energy is'),
('[[0]]. 그림 [[1]]의 소스 [[2]], 드레인 [[3]] 이중 접합에, 섬과 연결된 정전용량 [[4]]를 통해','[[0]]. In Fig. [[1]], add a gate to the source [[2]], drain [[3]] pair via capacitor [[4]].'),
('게이트 전극 [[0]]를 더하면 그림 [[1]]의 단전자 트랜지스터가 된다. 게이트와 섬 사이에는','The gate [[0]] forms the single-electron transistor of Fig. [[1]]. No single electron'),
('그림 [[0]]','Fig. [[0]]'),
('단전자 터널링이 없다. [[0]]가 작고 일정할 때 [[1]]로 순전자수 [[2]]을 조절한다. [[3]]가','tunnels between gate and island. At small fixed [[0]], [[1]] controls [[2]]. How does [[3]]'),
('[[0]]을 조절하는 간단한 모형에서, [[1]]는 섬에 등가 전하 [[2]]를 더하는 것으로 본다.','control [[0]]? Model [[1]] as adding the equivalent island charge [[2]].'),
('에너지는 약 [[0]], [[1]]이다. 모눈(그림','Energy is about [[0]]; [[1]]. Grid (Fig.'),
('[[0]])에서 쿨롱 봉쇄를','[[0]]). With Coulomb blockade,'),
('고려하라. 처음 [[0]]이고,','Initially [[0]]. As'),
('[[0]]가 [[1]]에서 [[2]]으로','[[0]] rises from [[1]] to [[2]],'),
('증가할 때 섬의 정전 에너지','draw the island energy'),
('[[0]] 대 [[1]]를 굵게 그려라.','[[0]] against [[1]] in bold.'),
('세로축 [[0]], [[1]]의 단위는','Vertical: [[0]]; units for [[1]]:'),
('그림 [[0]]','Fig. [[0]]'),
]
# The last native token in rows16/17 is the fixed graph ordinate, not prose.
# Its complete original CID/rule/clip program stays at the original position.
for rid in ['r16','r17']:
 r=next(v for v in q['rows']if v['id']==rid)
 for a in r['native_atoms']:
  fixed=[g for g in a['glyphs']if g['origin'][0]>=235]
  a['source_graph_glyphs_excluded_from_inline_motion']=fixed
  a['glyphs']=[g for g in a['glyphs']if g['origin'][0]<235]
  assert a['glyphs'];boxes=[g['bbox']for g in a['glyphs']];a['rect']=[min(x[0]for x in boxes),min(x[1]for x in boxes),max(x[2]for x in boxes),max(x[3]for x in boxes)]
# The original folio4 at y790 is unrelated to the magenta Fig5 caption at780.
last=q['rows'][-1];assert ''.join(g['c']for g in last['native_atoms'][0]['glyphs'])=='4'
last['native_atoms']=last['native_atoms'][1:];last['native_atoms'][0]['id']='r21a0';last['source_text']='图[[0]]'
assert len(T)==len(q['rows'])
rows=[]
for r,(ko,en)in zip(q['rows'],T):
 if r['id']=='r11':
  for i in range(2):
   rr=deepcopy(r);g=r['erase_glyphs'][i];a=deepcopy(r['native_atoms'][i]);rr['id']='r11'+chr(97+i);a['id']=rr['id']+'a0'
   rr.update(erase_glyphs=[g],native_atoms=[a],source_text='图[[0]]',source_baselines=[g['origin'][1]],baseline=g['origin'][1],left=g['bbox'][0],source_right=a['rect'][2],original_center=(g['bbox'][0]+a['rect'][2])/2,source_language_rect=g['bbox'])
   rr.update(ko='그림 [[0]]',en='Fig. [[0]]',reviewed=True,align='center',allowed_horizontal=[89,506]);rows.append(rr)
  continue
 r.update(ko=ko,en=en,reviewed=True,align='center'if r['id']=='r21'else'left',allowed_horizontal=[89,232]if r['id']in['r15','r16','r17','r18','r19','r20']else[89,506])
 if r['id']=='r21':
  g=r['erase_glyphs'][0];r['original_center']=(g['bbox'][0]+r['native_atoms'][0]['rect'][2])/2;r['baseline']=g['origin'][1];r['source_baselines']=[r['baseline']]
 rows.append(r)
for r in rows:
 for a in r['native_atoms']:
  assert not a['proposed_vector_paths'];a.update(vector_paths=[],reviewed=True,source_review_reason='Exact source inline expression, including original source mathematical Chinese punctuation. All displayed energy/plot fraction rules, complete diagram labels and footer remain stationary. Separate original captions retain their own centers and baselines.')
 for lang in ['ko','en']:assert sorted(map(int,re.findall(r'\[\[(\d+)\]\]',r[lang])))==list(range(len(r['native_atoms']))),(r['id'],lang,r[lang])
ink_path=B/'inspection/page04-authored-original-native-outline-bounds.json'
ink=json.loads(ink_path.read_text('utf8'));assert ink['source_sha256']==q['source_sha256']
outlines={v['id']:v for v in ink['atoms']}
for row in rows:
 for atom in row['native_atoms']:
  proof=outlines[atom['id']];assert atom['rect']==proof['source_metric_rect'];original=atom['rect'];actual=proof['actual_original_ink_rect']
  atom['source_metric_rect']=original[:];atom['rect']=[min(original[0],actual[0]),original[1],max(original[2],actual[2]),original[3]]
  atom['actual_original_outline_envelope_evidence']=dict(path=str(ink_path),sha256=hashlib.sha256(ink_path.read_bytes()).hexdigest(),atom_id=atom['id'])
label_policy=A/'page04-original-island-language-policy-canonical-cover-v2.json';assert label_policy.exists()
q.update(rows=rows,source_only_proposal=False,all_source_language_and_native_expressions_manually_reviewed=True,source_graph_ordinate_and_original_footer_explicitly_stationary=True,bitmap_chinese_labels_pending_language_only_mask=False,source_bitmap_language_policy_path=str(label_policy),source_bitmap_language_policy_sha256=hashlib.sha256(label_policy.read_bytes()).hexdigest(),publication_ready=False)
atomic_text(A/'page04-native-language.json', json.dumps(q,ensure_ascii=False,indent=2)+'\n', 'utf8');print('C08_PAGE04_SOURCE_PROSE_AND_TWO_ORIGINAL_BITMAP_LABELS_AUTHORED',len(rows))
