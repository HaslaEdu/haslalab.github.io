import sys
sys.path.insert(0,'C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions')
from izho2019_ts_authoring import begin,around,finish
p=begin(4)
for at,text in{
 '1,0,0':'상호작용 에너지이다. ',
 '1,0,3':'는 점전하 ','1,0,5':'와 유도 전하의 상호작용 에너지로서, ',
 '1,1,0':'다음과 같이 쉽게 구한다 ',
 '5,0,0':'전하를 무한대로 옮길 때 에너지 보존 법칙이 성립해야 하며, ',
 '5,1,0':'이 경우 다음과 같다 ',
 '10,0,0':'균일한 전기장 속의 도체 구 ',
 '10,1,1':'부피 전체에 전하가 균일하게 분포한 구 내부의 전기장을 구하자. ',
 '10,2,0':'반지름이 ',
 '10,2,2':'인 구형 영역에 가우스 법칙을 적용하면, 그 안의 전하량은 ',
 '13,9,0':'전기장 선속은 다음과 같다 ',
 '14,9,0':'가우스 법칙에 따라 ',
 '18,0,0':'최종적으로 ',
 '22,0,0':'마지막 식에서는 전기장 벡터가 위치 벡터 ',
 '22,1,1':'와 나란함을 고려하였다. ',
 '22,2,1':'이제 부피 전하 밀도의 부호가 반대인 두 가상의 구를 생각하고, ',
 '22,3,0':'두 구가 겹치는 영역의 전기장을 구하자. 이 영역 안의 임의의 점을 택하고, ',
 '22,4,0':'각 구의 중심에서 그 점까지 향하는 위치 벡터를 각각 ',
 '22,4,4':'와 ', '22,4,8':'라 하자. ',
 '29,0,0':'중첩 원리를 이용하면 전체 전기장은 다음과 같다 ',
 '34,0,0':'여기서 ','34,0,2':'는 음전하를 띤 구의 중심에서 ',
 '34,1,0':'양전하를 띤 구의 중심으로 향하는 벡터이다. ',
 '34,2,1':'도체 구 내부의 전기장은 영이어야 한다. 유도 전하가 만드는 전기장은 ',
 '34,4,0':'완전히 상쇄해야 하므로 ',
 '35,9,0':'가상의 두 구에 있는 전하는 표면 근처의 얇은 층을 제외하면 서로 완전히 상쇄된다. ',
 '35,10,0':'이 층은 표면 전하로 볼 수 있다. 층의 두께 ','35,10,2':'는 ',
 '35,11,0':'각 ','35,11,2':'에 따라 달라지며, ','35,11,4':'가 작으므로 다음과 같다 ',
 '36,9,0':'따라서 각 ','36,9,2':'근처의 표면 전하 밀도는 다음과 같다 ',
 '42,9,1':'도체 표면 근처의 얇은 원기둥을 생각하고, 여기에 가우스 법칙을 적용하자. ',
 '42,10,0':'도체 내부에는 전기장이 없고 표면 바로 밖에서는 전기장이 표면에 수직이므로, ',
 '42,11,0':'가우스 법칙에 따라 ',
}.items():p.add(at,text)
around(p,'6,7,0',['식 ','을 연립하면 최종적으로 다음을 얻는다 '],['(16)-(18)'])
around(p,'22,5,0',['그러면 각 구에 식 ','을 적용하여 '],['(23)'])
around(p,'34,3,0',['식 ','에 따라 균일하며, 외부 전기장을 '],['(26)'])
around(p,'41,8,0',['식 ','에서 곧바로 다음을 얻는다 '],['(27)-(29)'])
finish(p,[[10,0]],'Full original2019 sourcepage4 read at144dpi. Continuation WQ/WQq/q definitions, all energy-conservation/Gauss-law/superposition/surface-charge prose and bold enumerators2.6–2.9 translated. Preserve source display equations17–30 and CyrillicФ electric-flux glyphs exactly, all CambriaMath12/8.52/6.96pt formulas, radicals/fraction vectors and native vector-arrow accents with their actual source baselines. Inline WQq,q,r<R,rplus/rminus,a-vector,delta,theta and scalar a move only in complete original CID/Form/clip groups, including every accent. Source final conducting-surface cylinder argument continues into page5. Retain original12pt subsection heading center and all original script relationships; no formula correction/retyping/rasterization/point fitting.')
