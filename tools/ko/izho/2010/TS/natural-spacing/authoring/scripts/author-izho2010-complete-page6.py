from pathlib import Path
import sys
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2010-complete-solutions');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2010,6);p.header()
for at,text in {
 '2,1,2':' 코일에 저장되는 최대 에너지는 ',
 '6,0,2':' 정상 상태에서 자기장 ',
 '6,13,0':'은 코일 안에서 일정하며 전기장은 없다. 그러나 전류가 0에서 식 (12)의 ',
 '6,14,0':'최댓값까지 짧은 시간 동안 증가하는 초기에는 그렇지 않다. ',
 '6,15,0':'식 (14)에 따라 시간에 따라 변하는 자기장은 소용돌이 전기장을 만들며, ',
 '6,16,0':'이때 코일의 옆면을 통과하는 전자기 에너지의 흐름이 생긴다. ',
 '6,17,0':'코일 표면 부근에서 소용돌이 전기장의 세기를 ',
 '6,18,0':'패러데이의 전자기 유도 법칙으로 ',
 '6,19,0':'구하면: ',
 '8,0,0':'따라서 전기장의 크기는 ',
 '11,0,0':'벡터 ',
 '13,1,0':'와 ',
 '15,0,0':'의 방향은 아래 그림과 같다. ',
 '17,1,0':'포인팅 벡터에 식 (14), (16)을 대입하고 ',
 '17,2,0':'',
 '17,3,0':'두 벡터 ',
 '19,0,0':'와 ',
 '21,0,0':'가 서로 수직임을 이용하면 ',
 '24,0,0':'따라서 전류가 증가하는 동안 솔레노이드 옆면을 통과하는 전자기 에너지는 ',
 '24,1,0':'식 (17)을 시간에 대해 적분한 값이다: ',
 '30,0,0':'전류가 감소할 때에도 같은 에너지가 코일 옆면을 통해 빠져나간다. ',
 '30,1,0':'따라서 ',
}.items():p.add(at,text)
for at,word in [('2,1,1','балл'),('6,0,1','балла')]:p.add(at,'점',word)
for at,run in p.runs.items():
 if 'Italic'in run['font']or run['font'].startswith('BookmanOldStyle')or run['text'].strip()in ['max','Emf']:p.protect(at,'Original mathematical variable, operator descriptor or subscript retains its encoded source glyphs.')
print(p.save())
