from pathlib import Path
import sys
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2010-complete-solutions');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2010,2);p.header();p.add('2,0,0','점','балла',align='center');p.protect_fragment('2,0,0','В','Original theoretical-part1В label, not narrative language.')
for at,text in {
 '3,0,0':'먼저 용기 안의 높이에 따른 액체의 밀도와 압력 변화를 구한다: ',
 '13,0,0':'용기 윗부분에서는 압력이 0에 가까워진다. 따라서 이 영역에서는 ',
 '13,1,0':'기체의 부피가 시험관 부피를 넘어 기포가 밖으로 나온다. 기체가 ',
 '13,2,0':'시험관에서 나오기 전까지는 등온 팽창하므로 ',
 '15,0,0':'식 (2)를 쓰면 ',
 '22,0,0':'식 (4)의 적용 조건은 ',
 '22,6,0':', 즉 ',
 '27,0,0':'식 (4), (5)를 이용하여 시험관 벽의 질량을 포함한 기체의 평균 ',
 '27,1,0':'밀도를 다음과 같이 쓸 수 있다: ',
 '37,0,0':'여기서 ',
 '37,7,0':'여러 경우에 대한 ',
 '37,10,0':'의 ',
 '37,10,3':'에 따른 변화를 그림 1~3에 나타냈다. 곡선 1은 ',
 '37,11,0':'액체의 밀도이고, 곡선 2 ',
 '37,11,2':'시험관 벽의 질량을 포함한 기체의 평균 ',
 '37,12,0':'밀도이다. ',
 '38,0,0':'두 곡선이 만나지 않으려면(그림 1), ',
 '41,0,0':'에서 ',
 '46,0,0':'이 경우 시험관은 항상 가라앉는다. 다음 두 조건이 동시에 성립하면 ',
 '50,0,0':'두 곡선은 두 점에서 만난다(그림 2): ',
}.items():p.add(at,text)
for at in ['52,1,0','54,1,0']:p.add(at,'점 ','точка ')
p.protect_fragment('52,1,0','А','Original intersection-pointА label in its original encoded font.')
for at,run in p.runs.items():
 if run['font'].startswith('BookmanOldStyle'):p.protect(at,'Original MathType equation and its original gas/liquid descriptive subscripts; all original CID outlines and point sizes remain native.')
# This abbreviation is narrative even though each Cyrillic letter is separated
# by punctuation. Single-letter source-language coverage must not miss it.
for at,run in p.runs.items():
 if 'т.е.'in run['text']and not any(s['at']==list(map(int,at.split(',')))for s in p.slots):p.add(at,', 즉 ',run['text'])
print(p.save())
