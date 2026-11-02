from pathlib import Path
import sys
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2010-complete-solutions');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2010,7);p.header()
for at,text in {
 '1,0,0':'채점 기준 ',
 '2,2,0':'항목 ',
 '2,3,0':'배점 ',
 '2,5,0':'전체 관성 모멘트 (1) ',
 '2,8,0':'운동 방정식 (2) ',
 '2,11,0':'정지 시각 (3) ',
 '2,14,0':'시간에 따른 각속도 (4) ',
 '2,17,0':'유효 전기장 방정식 (5) 또는 (6) ',
 '2,20,0':'옴의 법칙 (7) ',
 '2,23,0':'시간에 따른 전류 (8) ',
 '2,26,0':'검류계를 통과한 전하량 (9) ',
 '2,29,0':'전자의 전하량과 질량의 비 (10) ',
 '2,32,0':'전류 방정식 (11) ',
 '2,35,0':'최대 전류 (12) ',
 '2,38,0':'시간에 따른 전류의 개략적 그래프 ',
 '2,41,0':'최대 에너지 (13) ',
 '2,44,0':'자기장 (14) ',
 '2,47,0':'전자기 유도 법칙 (15) ',
 '2,50,0':'소용돌이 전기장 (16) ',
 '2,53,0':'포인팅 벡터 (17) ',
 '2,56,0':'전자기 에너지 (18) ',
 '2,59,0':'전자기 에너지 (19) ',
 '2,64,0':'우주 배경 복사와 우주선',
 '3,1,0':'온도 ',
 '3,1,2':'에서 광자 에너지의 최빈값은 ',
 '5,0,0':', 이에 대응하는 운동량은 ',
 '7,0,0':'이다. ',
 '7,1,0':'수치를 대입하면 ',
 '14,1,0':'두 입자의 전체 질량중심계에서 구한 에너지의 합이다: ',
 '19,0,0':'여기서 ',
 '21,0,0':'는 전체 에너지, ',
 '23,0,0':'는 두 입자의 운동량이며, 모두 같은 관성계에서 ',
 '23,1,0':'구한 값이다. ',
 '26,0,0':'를, 배경 복사 광자와 충돌하여 ',
 '26,2,0':'이 문턱 에너지 ',
 '28,0,0':'이상이면 반응 (2)가 높은 확률로 일어나며 양성자는 ',
 '28,1,0':'파이 중간자의 생성에 에너지를 잃는다. 반응 (2)에서 생긴 이차 양성자도 ',
 '28,2,0':'에너지가 ',
 '30,0,0':'미만이 될 때까지 이 과정을 반복한다. ',
 '32,0,0':'이면 ',
 '32,1,0':'이 주요 반응 경로에 의한 에너지 손실은 없다. ',
 '34,0,0':'가 우주선 양성자의 ',
 '34,1,0':'최대 에너지이어야 한다. ',
}.items():p.add(at,text,align='center'if at in ['1,0,0','2,2,0','2,3,0','2,64,0']else None)
p.add('24,0,0','양성자의 에너지 ','Пусть ')
p.add('2,63,0','문제 ','Задача ',align='center');p.add('2,63,0','점','баллов',align='center')
for at,text in [('3,0,0','흑체 스펙트럼에서 '),('12,0,0','상호 작용하지 않는 두 입자 계의 전체 내부 에너지는 ')]:p.add(at,text,p.runs[at]['text'].split('. ',1)[1])
source=p.runs['16,0,0']['text'];before,after=source.split('q');p.add('16,0,0',', 여기서 ',before);p.add('16,0,0','는 질량중심계에서 두 입자의 운동량이다. 주어진 ',after);p.protect_fragment('16,0,0','q','Original momentum variable in its source font.')
source=p.runs['16,1,1']['text'];before,after=source.split('S');p.add('16,1,1','에 대한 다음 식은 모든 관성계에서 성립한다. 관성계: ',before);p.protect_fragment('16,1,1','S','Original reference-frame name.')
source=p.runs['26,1,0']['text'];a,b=source.split('Δ');c,d=b.split('Е');p.add('26,1,0','생성되는 입자가 ',a);p.add('26,1,0','일 때의 문턱 에너지라 하자. 에너지 ',c);p.protect_fragment('26,1,0','Δ','Original Delta-particle symbol.');p.protect_fragment('26,1,0','Е','Original energy variable Е.');p.add('26,1,0','',d)
source=p.runs['32,2,0']['text'];a,b=source.split('Δ');p.add('32,2,0','들뜬 상태 중 가장 가벼운 입자가 ',a);p.add('32,2,0',' 입자이므로, 에너지 ',b);p.protect_fragment('32,2,0','Δ','Original Delta-particle symbol.')
for at,run in p.runs.items():
 if 'Italic'in run['font']or run['font'].startswith('BookmanOldStyle'):p.protect(at,'Original mathematical variable, subscript or vector retains its source font and offsets.')
print(p.save())
