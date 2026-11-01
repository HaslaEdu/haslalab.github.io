from pathlib import Path
import sys
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2010-complete-solutions');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2010,5);p.header()
for at,text in {
 '1,0,0':'여기서 ',
 '1,0,2':'은 코일의 각가속도이다. ',
 '1,1,0':'식 (2)에서 코일이 정지하는 시각은 ',
 '3,0,0':'따라서 코일의 각속도는 시간에 따라 다음과 같이 변한다: ',
 '13,0,2':' 코일을 급하게 제동하면 도선의 전자는 관성에 의해 계속 움직이므로 ',
 '13,1,0':'검류계에 전류가 검출된다. 코일 테두리 위 점의 선가속도를 ',
 '14,4,0':'로 두자. 가는 도선을 촘촘히 감았다면 ',
 '14,5,0':'이 가속도는 도선을 따라 작용한다고 볼 수 있다. 코일을 제동하면 ',
 '14,6,0':'각 자유 전자에는 가속도와 반대 방향의 관성력 ',
 '14,10,0':'이 ',
 '14,11,0':'작용한다. 이 힘을 받는 전자는 금속 안에서 다음의 유효 전기장이 ',
 '14,12,0':'작용하는 것처럼 움직인다: ',
 '17,0,0':'따라서 자유 전자의 관성으로 코일에 생기는 유효 기전력은 ',
 '17,1,0':'다음과 같다: ',
 '20,0,0':'그러므로 닫힌 전기 회로에 옴의 법칙을 적용하면 ',
 '22,0,0':'앞의 2번 풀이를 이용하면 최종적으로 ',
 '32,0,2':' 검류계를 통과한 전하량은 식 (8)에서 ',
 '35,0,0':'따라서 전자의 전하량과 질량의 비는 ',
 '39,0,2':' 이 경우 식 (7)은 다음과 같이 바뀐다: ',
 '41,0,0':'여기서 ',
 '41,11,0':'는 코일의 인덕턴스이다. ',
 '41,13,0':'식 (11)에서 코일의 최대 전류는 ',
 '44,0,0':'시간에 따른 전류의 개략적인 그래프를 아래에 나타냈다. ',
}.items():p.add(at,text)
for at,word in [('13,0,1','балл'),('32,0,1','балла'),('39,0,1','балл')]:p.add(at,'점',word)
for at,run in p.runs.items():
 if 'Italic'in run['font']or run['font'].startswith('BookmanOldStyle')or run['text'].strip()in ['Emf','max']:p.protect(at,'Original physical equation or original mathematical descriptor, with its original font and offsets.')
print(p.save())
