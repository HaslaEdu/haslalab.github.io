from pathlib import Path
import sys
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2020-complete-solutions');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2020,9);p.header()
for at in ['1,0,0','4,1,0','7,0,0','9,0,0','10,0,0','19,0,0','21,0,0','25,2,0','26,0,0','31,0,0','38,1,0','42,2,0','44,0,0','46,0,0','52,0,0','58,2,0','59,0,0','62,0,0']:p.add(at,'식','Formula')
for at,text in {
 '3,2,0':'식 (17)의 수치 계산: ', '3,2,2':' 또는 ',
 '5,4,0':'식 (19)의 수치 계산: ', '17,0,0':'식 (23)의 수치 계산: ',
 '29,0,0':'식 (28)의 수치 계산: ', '42,4,0':'식 (31)의 수치 계산: ',
 '58,0,0':'추정: ', '62,2,0':'식 (38)의 수치 계산: ', '62,4,0':'합계 ',
 '63,0,0':'균일하게 대전된 고리 ',
 '63,1,1':'중력에 의해 고리의 질량중심은 속도 ', '63,1,3':'로 수직 아래쪽으로 ',
 '63,2,0':'움직인다. 이때 로런츠 힘 ', '63,2,3':'가 작용하여 고리가 자신의 축을 중심으로 ',
 '63,3,0':'각속도 ', '63,3,2':'로 회전하게 된다. 회전하면 수직 방향의 ',
 '63,4,0':'로런츠 힘 ', '63,4,3':'가 생긴다. 이 힘은 전하의 부호와 무관하게 중력과 반대 방향이다. ',
 '64,0,0':'고리의 질량중심에 대한 운동 방정식은 ',
 '67,10,0':'여기서 로런츠 힘은 ',
 '68,10,0':'이며, 고리 회전의 선속력은 ',
 '69,11,0':'따라서 고리의 질량중심에 대한 운동 방정식을 정리하면 ',
}.items():p.add(at,text)
p.add('62,9,0','문제 ','Problem ',align='center');p.add('62,9,0','자기장 속의 고리','Ring in a magnetic field',align='center');p.add('62,9,0','점','points',align='center')
p.protect_fragment('25,2,0','ln','Original natural logarithm in the exact source equation font and size.')
print(p.save())
