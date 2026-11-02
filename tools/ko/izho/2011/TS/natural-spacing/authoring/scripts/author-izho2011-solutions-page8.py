from pathlib import Path
import sys
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2011-complete-solutions');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2011,8);p.header();p.add('1,0,0','문제 ','Theoretical Question ',align='center');p.protect_fragment('1,0,0','3','Original native problem number at source14.04pt font/GID/baseline.')
for at,text in{
'2,0,1':'상수 ',
'2,0,3':'는 전체 입자 수가 ',
'2,1,1':'이라는 조건으로 구한다: ',
'8,0,0':'볼츠만 분포 함수를 대입하고 합을 계산하면 다음을 ',
'8,1,0':'얻는다: ',
'31,1,1':'기체의 내부 에너지는 모든 원자의 운동 에너지의 합이다: ',
'53,0,0':'고전적 극한 ',
'53,5,0':'에서는 지수의 인수가 작으므로 다음 ',
'54,0,0':'근사식을 사용할 수 있다: ',
'56,0,0':'. 이때 다음을 얻는다: ',
'58,0,0':'낮은 온도에서는 지수함수의 값 자체가 작다: ',
'61,0,0':'. 따라서 ',
'68,1,1':'정적 몰열용량은 ',
'71,0,0':'가장 일반적인 경우에는 다음을 얻는다: ',
}.items():p.add(at,text)
for at,word in[('2,0,0','point'),('31,1,0','points'),('68,1,0','points')]:p.add(at,'점',word)
translated={tuple(s['at'])for s in p.slots};fragments={tuple(s['at'])for s in p.fragments}
for at in p.runs:
 if tuple(map(int,at.split(',')))not in translated|fragments:p.protect(at,'Reviewed complete original mathematical sum, exponential/logarithmic function, derivative/fraction, physical constant or particle index, native vector/thermal variable, script or equation marker. Preserve exact source fonts/GIDs/fractional points/y and complete native Forms/rules.')
print(p.save())
