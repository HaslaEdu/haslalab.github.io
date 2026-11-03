import sys
sys.path.insert(0,'C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions')
from izho2019_ts_authoring import begin,around,finish
p=begin(5)
for at,text in{
 '4,0,0':'따라서 ',
 '5,9,0':'도체 구와 대전된 고리 ',
 '5,10,1':'도체 구는 매우 작으므로, 그 근처에서 고리의 전기장 ',
 '5,10,3':'는 ',
 '5,11,0':'거의 균일하다고 볼 수 있다. 앞 절에서 이 구의 분극은 ',
 '5,12,0':'반대 부호의 전하를 띤 두 가상의 구로 나타낼 수 있음을 보였다. 두 구는 ',
 '5,13,0':'외부 전기장 속에서 다음 모멘트의 쌍극자처럼 거동한다 ',
 '6,10,0':'여기서 ',
 '10,9,0':'구 근처에서 고리가 만드는 전기장 ','10,9,2':'를 중심으로부터의 ',
 '10,10,0':'거리 ','10,10,2':'의 함수로 구하자. 고리의 전기장 방향은 바늘을 따른다. 고리를 ',
 '10,11,0':'작은 부분으로 나누고, 각 부분의 전하량을 ',
 '10,11,3':'라 하자. 그 전기장의 ',
 '10,12,0':'바늘 방향 성분은 다음과 같다 ',
 '14,0,0':'다음 관계를 이용하고 ',
 '18,0,0':'고리의 모든 부분에 대해 합하면 ',
 '22,0,0':'쌍극자에 작용하는 힘은 다음과 같다 ',
 '31,1,0':'각 위치는 다음과 같다 ',
 '39,0,0':'여기서 ',
 '43,0,0':'평형점에서의 변위 ','43,0,2':'가 작을 때, ',
 '43,1,0':'바늘을 따라 움직이는 구의 뉴턴 운동 방정식은 다음과 같다 ',
 '47,0,0':'이는 다음 각진동수를 갖는 조화 진동 방정식이다 ',
 '51,1,0':'분극되지 않는다. 고리와의 거리가 영일 때와 무한대일 때 모두 ',
}.items():p.add(at,text)
around(p,'9,9,0',['식 ','을 식 ','과 ','에 적용하면 '],['(27)','(33)','(34)'])
around(p,'27,5,0',['식 ','와 ','을 식 ','에 대입하면 '],['(35)','(38)','(39)'])
around(p,'31,0,0',['식 ','에서 평형 위치가 세 개임을 알 수 있다. '],['(40)'])
around(p,'34,10,0',['간단히 분석하면 평형 위치 ','은 불안정하며, 대칭인 두 '],['(41)'])
around(p,'34,11,0',['평형 위치 ','는 모두 안정함을 알 수 있다. '],['(42)'])
around(p,'35,0,0',['안정 평형 위치 부근에서 힘에 대한 식 ','은 다음과 같이 단순해진다 '],['(40)'])
around(p,'51,0,1',['식 ','을 적분할 필요는 없다. 처음 위치에서 도체 구는 분극되지 않으며, 마지막에도 '],['(40)'])
finish(p,[[5,9]],'Full original2019 sourcepage5 read at144dpi. All conductive-ball/ring/dipole/equilibrium/oscillation/work prose and bold enumerators2.10/2.11 translated. Preserve original displayed equations31–46, original12pt centered subsection heading, source native p/E vector-arrow accents, charge/index scripts, every cos(alpha), root/fraction/integral/second-derivative glyph and rule at exact native points/Y/paint. Keep original ring/ball radii symbol conventions, source equation signs and both stable-equilibrium branches literal. Inline E,z,Deltaqi,x move only as whole original native expressions with every arrow/script carried. Original regular body12pt and all paragraph physical baselines retained, source work argument continues into page6. No mathematical correction/retyping/rasterization or point fitting.')
