from pathlib import Path
import sys
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2010-complete-solutions');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2010,4);p.header()
p.add('1,0,0','점','балла',align='center');p.protect_fragment('1,0,0','С','Original problem-part 1С label.')
for at,text in {
 '1,2,0':'문제의 그림자 모양은 본그림자와 반그림자가 생기기 때문이다. ',
 '1,3,0':'본그림자는 어두운 직사각형, 반그림자는 바깥의 더 밝은 직사각형이다. ',
 '1,4,0':'그림 1은 본그림자 ',
 '3,0,0':'와 반그림자( ',
 '5,0,0':'와 ',
 '7,0,0':')를 만드는 경계 광선을 ',
 '7,1,0':'광원의 한 변에 수직인 단면에서 보였다. 본그림자의 폭 ',
 '9,0,0':'은 ',
 '11,0,0':', ',
 '11,1,0':'반그림자의 폭 ',
 '13,0,0':'은 ',
 '15,0,0':'로 두자. 이 값들은 기하학적 ',
 '15,1,0':'관계로부터 광원과 평판의 크기로 표현된다. ',
 '16,0,0':'삼각형 ',
 '18,0,0':'와 ',
 '20,0,0':'의 닮음에서 ',
 '23,0,0':'삼각형의 닮음: ',
 '25,0,0':'와 ',
 '29,2,0':'그림자 그림에서 필요한 ',
 '29,3,0':'크기를 구하면: ',
 '31,1,0':'식 (1)로부터 ',
 '34,0,0':'따라서 ',
 '36,0,0':'를 얻는다. 식 ',
 '36,2,0':'로 광원의 ',
 '36,3,0':'한 ',
 '36,4,0':'변의 ',
 '36,5,0':'',
 '36,6,0':'길이 ',
 '38,0,0':'를 구한다. ',
 '38,1,0':'수직 단면에서 같은 계산을 하면 ',
 '38,2,0':'다음과 같다: ',
 '40,1,0':'따라서 ',
 '42,1,0':'이 결과에서 광원의 긴 변이 수평으로 놓여 있음을 알 수 있다. ',
 '42,2,0':'(문제의 그림 2를 기준으로 한다.) ',
 '43,1,0':'채점 기준 ',
 '44,0,0':'번 ',
 '44,1,0':'항목 ',
 '44,2,0':'배점 ',
 '44,4,0':'본그림자와 반그림자의 형성을 설명하는 광선 경로도 ',
 '44,7,0':'광원의 크기, 평판의 위치와 크기, 그림자 크기 사이의 ',
 '44,8,0':'기하학적 관계식 (1)~(2) ',
 '46,1,0':'바닥에서 평판까지의 높이 계산(수치 포함) ',
 '46,4,0':'광원 크기 계산(수치 포함) ',
 '46,7,0':'그림자에 대한 광원의 방향 ',
 '46,13,0':'톨먼–스튜어트 실험 ',
 '47,0,2':' 전체 관성 모멘트는 코일 자체의 관성 모멘트와 ',
 '47,1,0':'코일에 감긴 도선의 관성 모멘트를 더한 값이다: ',
 '48,13,2':' 코일을 강체로 보았을 때의 회전 운동 방정식은 ',
}.items():p.add(at,text,align='center'if at in ['43,1,0','44,0,0','44,1,0','44,2,0','46,13,0']else None)
p.add('46,12,0','문제 ','Задача ',align='center');p.add('46,12,0','점','баллов',align='center')
for at in ['47,0,1','48,13,1']:p.add(at,'점','балл')
for at in ['45,0,0','46,5,0']:p.protect(at,'Original numerical grading expression and multiplication character retain their source glyphs.')
for at,run in p.runs.items():
 if 'Italic'in run['font']or run['font'].startswith('BookmanOldStyle'):p.protect(at,'Original physical formula glyphs, preserving the source font, point, offsets and native geometry.')
print(p.save())
