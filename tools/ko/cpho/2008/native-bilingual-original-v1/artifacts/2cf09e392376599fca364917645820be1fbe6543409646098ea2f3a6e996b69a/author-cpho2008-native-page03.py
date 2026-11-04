import sys as _atomic_sys
from pathlib import Path as _AtomicPath
_atomic_sys.path.insert(0,str(_AtomicPath(__file__).resolve().parents[1]/'engine'))
from cpho2008_atomic_authoring import atomic_text
"""Source-read refrigerator/heat pump and single-electron-junction introduction."""
from pathlib import Path
import json,re
B=Path(__file__).resolve().parents[1];A=B/'authoring';q=json.loads((A/'page03-native-row-proposals.json').read_text('utf8'))
T=[
('열량이 [[0]], 외부가 냉동기에 한 일이 [[1]]이면 다음이 성립한다.','If the extracted heat is [[0]] and external work is [[1]], then'),
('[[0]]는 이론적인 이상적 경우이다. 겨울에 이 냉동기를 난방용 열펌프로 쓴다.','The sign “[[0]]” is the ideal limit. In winter, use the refrigerator as a heat pump.'),
('실외 온도가 [[0]]일 때 실내를 [[1]]로 유지한다. 실내가 실외보다 따뜻하므로','At outdoor temperature [[0]], it keeps a room at [[1]]. The warmer room'),
('열이 실내에서 실외로 흐른다. 여기서는 열전도만 고려한다. 그 법칙은 다음과 같다.','loses heat outdoors. Consider only conduction, governed by the following law.'),
('전도층의 두께가 [[0]], 면적이 [[1]], 두 면의 온도차 크기가 [[2]]이면 단위 시간에','For a conducting layer of thickness [[0]], area [[1]], temperature difference [[2]], the heat'),
('전도층을 통해 고온부에서 저온부로 전달되는 열량은 다음과 같다.','conducted through it per unit time from the hot side to the cold side is'),
('여기서 [[0]]는 열전도율로, 전도층 물질의 성질에 따라 정해진다.','Here [[0]] is the thermal conductivity, determined by the layer material.'),
('[[0]]. 실외를 향한 면적 [[1]], 두께 [[2]]인 유리판으로 열이 빠져나간다고','[[0]]. Heat loss is through a pane facing out: [[1]] in area, [[2]] thick.'),
('하자. 유리의 열전도율은 [[0]], 전기요금은 kWh당 [[1]]위안이다. 이상적인','Glass conductivity [[0]]; tariff [[1]] yuan/kWh. In the ideal case,'),
('조건에서 이 열펌프를 [[0]] 가동할 때 전기요금을 구하라.','find the electricity cost of operating the heat pump for [[0]].'),
('[[0]]. 이중창으로 바꾸어, 두 유리의 두께를 각각 [[1]]로 한다. 사이에는','[[0]]. Replace it by double glazing: both panes [[1]] thick, separated by'),
('두께 [[0]]인 공기층이다. 열전도율은 [[1]], 전기요금은 여전히','an air gap [[0]] thick; conductivity [[1]]. The tariff remains'),
('kWh당 [[0]]위안이다. [[1]] 가동할 때 단일창보다 절약하는 전기요금을 구하라.','[[0]] yuan/kWh. For [[1]] operation, how much is saved versus single glazing?'),
('4.','4.'),
('그림 [[0]]의 소자는 금속층 [[1]]과 얇은 절연층,','Fig. [[0]] has metal [[1]], thin insulator'),
('[[0]], 금속층 [[1]]이 밀착해 있다. 고전적으로 [[2]]층이','[[0]] and metal [[1]], in close contact. Classically, if [[2]]'),
('이상적인 절연체이면, 전자는 절연층을 통과해 다른','is a perfect insulator, electrons cannot pass to'),
('그림 [[0]]','Fig. [[0]]'),
('금속층으로 갈 수 없다. 그러나 양자역학에서는','another metal layer. Yet quantum physics allows'),
('일정 조건에서 가능하다. 이를 터널링이라 하며, 전자의 파동성 때문이다. 터널링은','this under certain conditions. Tunnelling follows from electron wave nature. Each'),
('한 전자의 이산적 사건이다. 절연층을 통과한 전하량은 전자 전하 [[0]]','event transfers one electron. The discrete charge is a multiple of [[0]]'),
('[[0]]의 정수배이다. 단전자 터널링이라 하며, [[1]] 소자는 터널 접합 또는','[[0]], so single-electron tunnelling. [[1]] is a tunnelling junction, also called a'),
('단전자 터널 접합이다. 이를 제어하는 쿨롱 봉쇄를 다룬다. 이 원리로 극소형','single-electron tunnelling junction. Coulomb blockade controls it, allowing tiny'),
('단전자 소자를 만들 수 있어, 활발히 연구되며 응용이 기대되는 분야이다.','single-electron devices. This active research field has promising applications.'),
('[[0]]. 쿨롱 봉쇄의 가장 간단한 모형으로 그림 [[1]] 소자를 정전용량 [[2]]의 축전기로 보자.','[[0]]. Simplest model: Fig. [[1]] is a capacitor [[2]], with continuous plate charge, as in'),
('그림 [[0]]과 같다. 판의 전하는 양전하 배경에 대한 전도 전자구름의 미세한 이동으로','Fig. [[0]]: the conduction-electron cloud shifts slightly against positive background.'),
('생겨 연속으로 변한다. 절연층을 터널링하는 전하는','Tunnelling through the insulator transfers only'),
('그림 [[0]]','Fig. [[0]]'),
]
assert len(T)==len(q['rows'])
for r,(ko,en)in zip(q['rows'],T):
 en=en.replace('’',"'")
 r.update(ko=ko,en=en,reviewed=True,align='center'if r['id']in('r17','r27')else'left',allowed_horizontal=[89,506])
 if r['id']in('r14','r15','r16','r18'):r['allowed_horizontal']=[89,377]
 if r['id']=='r26':r['allowed_horizontal']=[89,355]
 for a in r['native_atoms']:
  assert not a['proposed_vector_paths'],(r['id'],a['id'],a['proposed_vector_paths']);a.update(vector_paths=[],reviewed=True,source_review_reason='Source-read complete inline original tokens only. Original displayed refrigerator/conduction fractions, all MIM/capacitor figure paths/labels and source footer remain stationary; the original colored caption numbers move only with the centered caption.')
 for lang in('ko','en'):assert sorted(map(int,re.findall(r'\[\[(\d+)\]\]',r[lang])))==list(range(len(r['native_atoms']))),(r['id'],lang)
q.update(source_only_proposal=False,all_source_language_and_native_expressions_manually_reviewed=True,source_display_fraction_and_diagram_paths_all_stationary=True,publication_ready=False)
atomic_text(A/'page03-native-language.json', json.dumps(q,ensure_ascii=False,indent=2)+'\n', 'utf8');print('C08_PAGE03_ALL_SOURCE_PROSE_MANUALLY_AUTHORED',len(T))
