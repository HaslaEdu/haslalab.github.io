from pathlib import Path
import sys
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2018-theory-original');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2018,3);p.header()
p.add('1,0,0','문제 ','Problem ',align='center');p.add('1,0,0','점','points',align='center')
for at,text in {
'1,1,0':'산에서의 물리 ',
'1,2,0':'지구와 같은 실제 행성의 ',
'1,3,0':'대기는 형성에 관여하는 다양한 ',
'1,4,0':'과정과 현상 때문에 구조가 복잡하다. ',
'1,5,0':'이 문제에서는 지구 대기의 ',
'1,6,0':'하층의 두 단순한 모형을 다룬다. ',
'1,7,0':'이 층은 대류권이며, ',
'1,9,0':'뻗어 있다. 일부 현상을 설명할 때 ',
'1,10,0':'지구 대기를 몰 질량이 ',
'1,11,0':'다음과 같은 단일 성분의 ',
'1,12,0':'이원자 기체로 보아도 충분하다: ',
'2,0,0':'제1부. 등온 대기 ',
'2,1,0':'대기의 맨 아래, 지표면에 가까운 층은 지표면에 의해 가열되므로 ',
'2,2,0':'온도가 거의 일정하다. 따라서 이 부분에서는 대기의 온도가 ',
'2,3,0':'모든 높이에서 일정하다고 가정한다. 온도는 ',
'2,4,0':'기압은 ',
'2,4,6':'이다. 중력 가속도 ',
'2,5,2':'는 높이에 무관하다고 하시오. 대기의 전체 높이는 ',
'2,6,0':'지구 반지름 ',
'2,6,4':'보다 훨씬 작다. 보편 기체 상수는 ',
'3,0,2':'을 구하고 수치로 계산하시오. ',
'3,1,3':'는 지표면 위 높이 ',
'3,1,5':'에서의 값이다. ',
'3,2,0':'구하고 수치로 계산하시오. ',
'4,0,0':'낮과 밤이 바뀔 때 대기가 얼마나 빨리 데워지는지는 물리적으로 ',
'4,1,0':'흥미로운 질문이다. 우주 관측으로 알려진 태양 ',
'4,2,0':'상수 ',
'4,2,3':'는 지구 궤도 부근에서 복사에 수직인 ',
'4,3,0':'단위 면적을 통과하는 태양 복사의 총출력이다. ',
'5,0,2':'를 어림하시오. 온도 변화는 ',
'5,1,2':'를 구하고 수치로 계산하시오. 태양이 지구에 줄 ',
'5,2,0':'열량은 ',
'6,0,0':'제2부. 단열 대기 ',
'6,1,0':'실제 대류권은 등온과 거리가 멀며, 높이 올라갈수록 기온이 낮아진다. ',
'6,2,0':'끊임없이 일어나는 대류 때문에 대류권을 사실상 단열로 볼 수 있다. ',
'6,3,0':'지표면의 기온과 기압을 각각 ',
'6,4,0':'와 ',
'6,4,6':'로 놓는다. 중력 가속도 ',
'6,4,9':'는 ',
'6,5,0':'앞과 같이 지표면 위 높이에 무관하다고 하시오. ',
'7,0,3':'는 지표면 위 높이 ',
'7,0,5':'에서의 값이다. ',
'7,1,0':'구하고 수치로 계산하시오. ',
'7,2,3':'는 지표면 위 높이 ',
'7,2,5':'에서의 값이다. ',
'7,3,0':'구하고 수치로 계산하시오. ',
'8,1,0':'이 모형에서 대류권의 높이는 다른 물리 과정들이 중요한 역할을 ',
'8,2,0':'하기 시작하는 임계 온도에 도달하는 높이로 정해진다. ',
'9,0,3':'를 어림하시오. 이 시간 동안 ',
'9,1,0':'지표면 온도는 다음만큼 변한다: ',
}.items():p.add(at,text,align='center'if at in ['1,1,0','2,0,0','6,0,0']else None)
for at,label,text in [('3,0,0','1.1',' 지구 대기의 질량 '),('3,1,0','1.2',' 기압 '),('5,0,0','1.3',' 대기를 가열할 때 필요한 열량 '),('5,1,0','1.4',' 다음 열량을 공급하는 데 걸리는 시간 '),('7,0,0','2.1',' 기온 '),('7,2,0','2.2',' 기압 '),('9,0,0','2.3',' 낮과 밤의 대류권 높이 차이 ')]:
 s=p.runs[at]['text'];assert s.startswith(label)
 p.protect_fragment(at,label,'Original native subquestion enumerator in exact original font/point/baseline.');p.add(at,text,s[len(label):])
at='1,8,0';s=p.runs[at]['text'];v='10-15 km';a,b=s.split(v)
p.protect_fragment(at,v,'Original complete tropospheric altitude interval and km unit in native TNR12; no numeral/unit retyping.');p.add(at,'지표면 위로 ',a);p.add(at,'까지 ',b)
at='2,3,4';s=p.runs[at]['text'];assert s.startswith('К')
p.protect_fragment(at,'К','Original source uses Cyrillic capitalKa for the Kelvin unit. Retain original encoded source glyph/font/point, no Latin substitution.');p.add(at,', 지표면의 ',s[1:])
for at in ['5,0,4','6,3,4','9,1,4']:
 p.protect(at,'Original source Kelvin unit encoded as CyrillicKa and adjacent original punctuation; retain exact original native glyph/font/point.')
print(p.save())
