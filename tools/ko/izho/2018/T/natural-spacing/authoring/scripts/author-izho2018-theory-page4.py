from pathlib import Path
import sys
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2018-theory-original');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2018,4);p.header()
for at,text in {
'1,0,0':'등산가가 상당히 높은 산을 오르기 시작한다. 산기슭의 ',
'1,1,0':'기온과 기압은 각각 ',
'1,1,10':'이다. ',
'1,2,0':'높이 ',
'1,2,2':'에서 물을 끓이려고 쉬다가, 물이 ',
'1,3,0':'평소보다 빨리 끓는 것을 발견한다. 물리 편람을 보니 ',
'1,4,0':'온도 ',
'1,4,12':', ',
'1,5,0':'온도 ',
'1,5,10':'이다. ',
'2,0,2':'에서 물의 끓는점을 구하고 수치로 계산하시오. ',
'3,0,0':'등산가는 다시 오르다가 어느 높이부터 눈이 있음을 확인한다. ',
'3,1,0':'더 오르려면 특수 장비가 필요하다. ',
'4,0,3':'를 구하고 수치로 ',
'4,1,0':'계산하시오. ',
'5,0,0':'등산가는 등반 직전 주민들에게 들은 말을 떠올린다. ',
'5,1,0':'산의 눈이 완전히 사라지는 것은 산기슭의 기온이 ',
'6,0,3':'를 구하고 수치로 계산하시오. ',
'7,0,0':'산비탈을 따라 더 올라가 높이 ',
'7,0,2':'에 이른 등산가는 ',
'7,1,0':'안개를 발견한다. 주변에는 구름도 없고 바람도 불지 않는다. ',
'7,2,0':'물의 몰 질량은 ',
'7,2,8':'이고, ',
'7,3,0':'일기 예보에서 확인한 산기슭의 상대 습도는 ',
'7,4,1':'이다. 물리 편람에 실린 물의 포화 증기압은 ',
'7,5,0':'온도 범위 ',
'7,5,2':'에서 다음 식으로 주어진다. ',
'12,0,0':'여기서 ',
'12,0,3':'은 온도 ',
'12,0,5':'의 포화 증기압이고, ',
'12,0,8':'은 ',
'12,1,0':'온도 ',
'12,1,3':'의 포화 증기압이다. ',
'12,1,6':', ',
'12,1,8':'는 상수이다. ',
'12,2,0':'계산에서는 수증기가 항상 주변 공기와 열역학적 평형을 이룬다고 하시오. ',
'13,0,2':'를 구하고 수치로 계산하시오. ',
'13,1,3':'를 구하고 수치로 계산하시오. ',
'13,2,0':'이때 산비탈 어딘가에서 안개가 여전히 관측되어야 한다. ',
'14,0,0':'수학적 도움말 ',
'14,1,0':'다음 적분을 사용할 수 있다. ',
}.items():p.add(at,text,align='center'if at=='14,0,0'else None)
for at,label,text in [('2,0,0','2.4',' 높이 '),('4,0,0','2.5',' 눈 덮인 부분을 처음 발견한 높이 '),('6,0,0','2.6',' 등산가가 오르는 산의 높이 '),('13,0,0','2.7',' 높이 '),('13,1,0','2.8',' 산기슭의 최소 상대 습도 ')]:
 s=p.runs[at]['text'];assert s.startswith(label)
 p.protect_fragment(at,label,'Original native subquestion enumerator at exact original source font/point/baseline.');p.add(at,text,s[len(label):])
for at,text in [('1,1,4','와 '),('1,4,4','에서 물의 포화 증기압은 '),('1,5,4','에서는 '),('5,2,1','일 때이다. ')]:
 s=p.runs[at]['text'];assert s.startswith('К')
 p.protect_fragment(at,'К','Original source CyrillicKa Kelvin unit; exact original font, encoded glyph and baseline retained, no Latin-letter replacement.')
 p.add(at,text,s[1:])
print(p.save())
