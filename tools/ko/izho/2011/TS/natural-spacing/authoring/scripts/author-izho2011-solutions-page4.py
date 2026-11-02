from pathlib import Path
import sys
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2011-complete-solutions');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2011,4);p.header()
p.add('1,0,0','문제 ','Theoretical Question ',align='center');p.add('1,0,0','점','points');p.protect_fragment('1,0,0','2 (10 ','Original native problem number/grade and source punctuation at14.04pt.')
for at,text in{
'2,0,0':'금속의 전기 전도도 ',
'3,0,0':'옴의 법칙 ',
'3,3,0':'줄–렌츠 법칙에 따라 도체에서 발생하는 열의 일률은 ',
'5,0,0':'따라서 단위 부피당 발열 일률 ',
'5,1,2':'는 다음과 같다: ',
'9,0,0':'다음 관계들을 이용하면 ',
'10,10,0':'와 ',
'11,0,0':'다음을 얻는다: ',
'13,0,0':'드루드 모형 ',
'13,3,0':'일정한 전기장 속에서 전자의 운동에 뉴턴 제2법칙을 적용하면 ',
'14,16,2':'동안 전자가 이동한 거리는 ',
'17,0,0':'따라서 전자의 평균 속력은 ',
'19,0,0':'벡터로 쓰면 ',
'22,2,0':'전류 밀도는 전자의 수밀도, 전하와 평균 속도로 ',
'22,3,0':'다음과 같이 나타낸다: ',
'26,0,0':'이는 옴의 법칙이며, 전기 전도도는 ',
'31,2,0':'각 전자는 가속이 끝날 때, 즉 이온과 충돌하는 순간에 ',
'31,3,0':'자신의 운동 에너지를 전달한다: ',
}.items():p.add(at,text,align='center'if at in['2,0,0','3,0,0','13,0,0']else None)
for at in['3,2,0','13,2,0','22,1,0','31,1,0']:p.add(at,'점','point')
p.add('14,16,0','식 (','It follows from Eq.(');p.protect_fragment('14,16,0','5','Original source equation-reference numeral5 at the source12pt face and baseline.');p.add('14,16,0',')에 따르면, 시간 간격 ',')  that for the time interval ')
translated={tuple(s['at'])for s in p.slots};fragments={tuple(s['at'])for s in p.fragments}
for at in p.runs:
 if tuple(map(int,at.split(',')))not in translated|fragments:p.protect(at,'Reviewed original native equation, complete fraction, physical variable/unit/script, source bold vector, numeral or equation marker. Preserve all source font programs/GIDs/fractional points/y and native rules/Forms.')
print(p.save())
