from pathlib import Path
import sys
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2011-complete-solutions');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2011,6);p.header()
for at,text in{
'4,0,0':'전자가 ',
'4,0,2':'축 방향으로 시간 간격 ',
'4,0,4':'동안 이동한 거리는 ',
'6,0,0':'평균 속력은 ',
'9,0,0':'따라서 전기 전도도의 상대 변화는 ',
'16,0,0':'그러므로 ',
'22,0,0':'홀 효과 ',
'22,3,0':'전자에 작용하는 로런츠 힘은 아래쪽을 향하므로, 음전하는 ',
'22,4,0':'아랫면 근처에 쌓인다. ',
'22,7,0':'막대의 아랫면 근처에 전자가 모이므로, 홀 전기장은 ',
'22,8,0':'',
'22,9,0':'다음과 같이 쓸 수 있다: ',
'28,0,0':'전자의 궤적은 다시 ',
'28,0,2':'평면 위에 있다. 다음 치환을 ',
'38,21,0':'또는 원래 변수로 나타내면 ',
}.items():p.add(at,text,align='center'if at=='22,0,0'else None)
for at in['1,0,0','22,2,0','22,6,0']:p.add(at,'점','points')
for at,parts in{
'1,1,0':['자기장 세기가 작을 때, 식 (',')은 다음과 같다: '],
'22,8,2':['축과 반대 방향이다. 따라서 운동 방정식 (',')을 '],
'29,9,0':['을 식 (','), (',')에 대입하면 '],
'36,0,0':['식 (','), (',')의 해는 다시 다음 조화 진동이다: '],
}.items():p.references(at,parts)
translated={tuple(s['at'])for s in p.slots};fragments={tuple(s['at'])for s in p.fragments}
for at in p.runs:
 if tuple(map(int,at.split(',')))not in translated|fragments:p.protect(at,'Reviewed original complete native mathematics, fraction/derivative, physical OX/OY/XY axis, vector/unit, script or equation counter. Preserve encoded source font/GID/fractional point/baseline and all original Forms/rules; no math retyping.')
print(p.save())
