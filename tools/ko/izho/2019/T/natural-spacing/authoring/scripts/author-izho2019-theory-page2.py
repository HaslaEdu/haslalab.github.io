from pathlib import Path
import sys
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2019-theory-original');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2019,2);p.header()
for at in ['1,0,0','2,0,0','3,0,0','4,1,0']:
 p.add(at,'문제 ','Problem ',align='center');p.add(at,'점','points',align='center')
for at,text in {
'1,1,0':'이 문제는 서로 독립인 세 부분으로 이루어져 있다. ',
'2,1,0':'반지름이 ',
'2,1,2':'인 수직 원기둥을 마찰 없는 수평면에 ',
'2,2,0':'고정했다. 원기둥에 실을 팽팽하게 감았다. 풀린 실의 ',
'2,3,0':'길이는 ',
'2,3,3':'이며, 끝에 질량이 ',
'2,3,5':'인 작은 원판을 단다. ',
'2,4,0':'처음 원판에 수평 속도 ',
'2,4,2':'를 실과 수직으로 준다. ',
'2,5,0':'실이 끊어질 때까지 걸리는 시간을 구하시오(그림 참조). ',
'2,6,0':'실이 견딜 수 있는 최대 장력은 ',
'2,6,2':'이다.',
'3,1,0':'공기 중에서 물체가 식는다. 열전달률은 물체와 공기의 온도 차에 ',
'3,2,0':'비례한다. 아래 그래프는 물체의 온도와 시간의 관계를 나타낸다. ',
'3,3,0':'공기의 온도를 구하시오. ',
'4,2,0':'실제 교류 전압원의 등가회로를 생각하자. ',
'4,3,0':'각진동수는 ',
'4,3,7':'이며, 이상적인 전압원의 ',
'4,4,0':'전압 진폭은 ',
'4,5,0':'전기용량이 ',
'4,6,0':'축전기와 코일을 다양하게 연결한 회로를 부하로 연결할 수 있다. ',
'4,7,0':'부하 자체의 발열률이 최대가 되는 부하 회로를 제안하시오. ',
'4,8,0':'회로를 개략적으로 그리고 각 소자의 값을 구하시오. ',
'4,9,0':'해가 여러 개라면 가장 간단한 것을 제시하시오. 부하에 발생할 수 있는 ',
'4,10,0':'최대 전력도 구하시오. ',
}.items():p.add(at,text,align='center'if at=='1,1,0'else None)
for at in ['2,3,1','2,3,2','2,4,1','4,3,1','4,3,3','4,3,4','4,3,5','4,3,6','4,4,1','4,4,2','4,4,4','4,4,5','4,5,1','4,5,2']:
 p.protect(at,'Original native mixed-font mathematical variable, numeral, exponent or physical unit; preserve exact source font/GID/point/baseline and internal geometry, with no mathematical retyping.')
for at,unit,remainder,text in [
 ('4,4,3','V',', of a resistor with the resistance ','이다. 회로는 저항이 '),
 ('4,4,6','Ohm',' and of ','인 저항기와 '),
 ('4,5,3','μF','. Different circuits of resistors, ','인 축전기를 포함한다. 저항기, '),
]:
 assert p.runs[at]['text']==unit+remainder
 p.protect_fragment(at,unit,'Original printed native physical unit beside its original numerical value; preserve source glyphs and face rather than substitute a retyped unit.');p.add(at,text,remainder)
print(p.save())
