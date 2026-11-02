from pathlib import Path
import sys
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2011-complete-solutions');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2011,9);p.header()
for at,text in{
'14,0,0':'두 극한에서의 근사식은 ',
'14,1,0':'앞서 구한 전개식으로 쉽게 구한다( ',
'21,0,0':'즉, 몰열용량은 일정하다. 여기서 ',
'21,2,1':'는 ',
'21,3,0':'아보가드로 상수이고, ',
'21,9,0':'는 보편 ',
'21,10,0':'기체 상수이다. ',
'21,11,0':'낮은 온도에서는 ',
'37,1,0':'온도가 영으로 갈 때 몰열용량도 영으로 간다. 개략적인 그래프는 ',
'37,4,1':'기체의 압력은 여러 방법으로 계산할 수 있다. 예를 들어, ',
'37,5,0':'원자 하나가 벽에 가하는 평균 힘은 전달한 운동량을 ',
'37,6,0':'연속한 두 충돌 사이의 시간 간격으로 나눈 값이다: ',
'42,0,0':'압력을 구하려면 이 힘들을 모두 더해야 한다: ',
'59,0,0':'두 극한에서는 앞서 구한 내부 에너지의 근사식을 ',
'59,1,0':'사용한다. ',
'60,0,0':'다음 극한에서는 ',
'62,0,0':'즉, 압력은 절대 온도에 비례한다. ',
'63,0,0':'낮은 온도에서는 ',
}.items():p.add(at,text)
p.add('37,4,0','점','points')
for at,parts in{
'14,2,0':['소문항 ','). 높은 온도 극한에서는 '],
'37,2,0':['그림 ','에 나타냈다. '],
'51,0,0':['기체의 내부 에너지에 대한 식 (',')을 대입하면 '],
}.items():p.references(at,parts)
p.add('65,0,0','그림 ','Fig.');p.protect_fragment('65,0,0','1','Original source caption numeral/font/GID/point/baseline; whole caption original center retained.')
translated={tuple(s['at'])for s in p.slots};fragments={tuple(s['at'])for s in p.fragments}
for at in p.runs:
 if tuple(map(int,at.split(',')))not in translated|fragments:p.protect(at,'Reviewed complete original thermal/statistical sum, integral/fraction/exponential, Avogadro/Boltzmann/gas constant, physical variable/unit/script, original plot variable or equation counter. Preserve exact encoded source fonts/GIDs/fractional points/baselines and native Forms/rules.')
print(p.save())
