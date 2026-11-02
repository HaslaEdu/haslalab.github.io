from pathlib import Path
import sys
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2010-complete-solutions');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2010,3);p.header()
line=p.runs['1,0,0']['text'];before,after=line.split('А')
p.add('1,0,0','점 ',before);p.add('1,0,0','는 불안정하다. 이 점에서 아래로 벗어나면 시험관은 ',after);p.protect_fragment('1,0,0','А','Original intersection-pointА label in its original encoded font.')
p.add('1,1,0','가라앉고, 위로 벗어나면 ')
line=p.runs['1,1,2']['text'];before,after=line.split('В')
p.add('1,1,2','떠오른다. 점 ',before);p.add('1,1,2','는 언뜻 안정적으로 보인다. ',after);p.protect_fragment('1,1,2','В','Original intersection-pointВ label in its original encoded font.')
for at in ['3,1,0','5,1,0','7,1,0','9,1,0']:p.add(at,'그림 ','Рис.',align='center')
p.add('9,2,0','다음 조건이 성립하면 ')
line=p.runs['13,0,0']['text'];before,after=line.split('В')
p.add('13,0,0','교점은 ',before);p.add('13,0,0',' 하나만 남는다(그림 3). 다만 안정성 분석에서는 ',after);p.protect_fragment('13,0,0','В','Original intersection-pointВ label, not narrative language.')
for at,text in {
 '13,1,0':'곡선 2의 수평 부분에서 오른쪽으로 이동하는 동안 기체가 ',
 '13,2,0':'계속 빠져나오는 점을 고려해야 한다. 따라서 왼쪽으로 이동할 때에는 ',
 '13,3,0':'식 (6)의 윗줄과 같은 포물선을 따르지만, 더 큰 새 값 ',
 '13,5,1':'을 쓴다. 이는 ',
 '13,6,0':'시험관에 남아 있는 기체의 양에 해당한다. ',
 '14,0,0':'채점 기준',
 '15,1,0':'항목 ',
 '15,2,0':'배점 ',
 '15,4,0':'용기 높이에 따른 압력 분포 ',
 '15,7,0':'시험관 속 기체의 평균 밀도와 높이의 관계: ',
 '15,8,0':'가) 기체 유출 고려(완전한 답) ',
 '15,9,0':'나) 기체 유출 무시(불완전한 답) ',
 '16,4,0':'액체와 기체의 밀도가 높이에 따라 변하는 양상을 ',
 '16,5,0':'비교: ',
 '16,6,0':'가) 세 경우 모두(완전한 답) ',
 '16,7,0':'나) 두 경우(불완전한 답) ',
 '16,8,0':'다) 한 경우(불완전한 답) ',
 '17,6,0':'교점에 해당하는 높이 결정: ',
 '17,7,0':'가) 두 교점(완전한 답) ',
 '17,8,0':'나) 한 교점(불완전한 답) ',
}.items():p.add(at,text,align='center'if at in['14,0,0','15,1,0','15,2,0']else None)
p.add('15,0,0','번호 ',align='center')
for at,label in [('18,4,0','А'),('18,7,0','В')]:
 source=p.runs[at]['text'];before,after=source.split(label);p.add(at,'안정성 조사: 점 ',before);p.protect_fragment(at,label,'Original named intersection point in the marking-scheme rubric.')
for at,run in p.runs.items():
 if run['font'].startswith('BookmanOldStyle'):p.protect(at,'Original MathType formula or subscript; retain all original encoded glyphs and geometry.')
print(p.save())
