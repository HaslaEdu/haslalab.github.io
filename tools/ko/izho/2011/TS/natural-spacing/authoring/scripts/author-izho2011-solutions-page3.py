from pathlib import Path
import sys,re
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2011-complete-solutions');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2011,3);p.header();p.add('1,0,0','점','points',align='center');p.protect_fragment('1,0,0','1C (2.5 ','Original source problem label, grade and punctuation at14.04pt source face and baseline.')
pattern=re.compile(r"(?<![A-Za-z])(?:A'B'|AA'|BB'|A'|B'|AB|BD|A|B|O|C|F)(?![A-Za-z])")
def prose_and_native(at,parts):
 source=p.runs[at]['text'];matches=list(pattern.finditer(source));assert len(parts)==len(matches)+1,(at,source,matches,parts);cursor=0
 for i,m in enumerate(matches):
  if cursor<m.start():p.prose_range(at,cursor,m.start(),parts[i])
  else:assert not parts[i]
  p.protect_range(at,m.start(),m.end(),'Original optical point, ray or line identifier in the exact source TimesNewRoman font/GID/12pt/baseline. Preserve literal apostrophes and joint point-name geometry.');cursor=m.end()
 if cursor<len(source):p.prose_range(at,cursor,len(source),parts[-1])
 else:assert not parts[-1]
for at,parts in{
'3,1,0':['점 ','에서 나온 모든 광선은 렌즈를 지난 뒤 점 ','를 지나야 한다. '],
'3,2,0':['점 ','에서 나온 모든 광선도 렌즈를 지난 뒤 점 ','를 지나야 한다. '],
'3,4,0':['직선 ','과 ','의 교점이 렌즈의 광학 중심 ','이다. 한 광선이 '],
'3,5,0':['점 ','와 ','를 모두 지나면, 반드시 다음 두 '],
'3,5,2':[' ','와 ','를 지나야 한다. 따라서 '],
'3,6,0':['직선 ','와 ','의 교점은 렌즈면 위에 있다. 따라서 렌즈면은 '],
'3,7,0':['점 ','와 ','를 지난다. 렌즈의 주광축은 광학 중심을 지나며 '],
'3,9,0':['광선 ','를 점 ','에서 주광축에 평행하게 그린다. 렌즈를 지난 '],
'3,10,0':['광선(또는 연장선)은 ','를 지나야 한다. 이 광선과 주광축의 교점이 '],
'3,11,0':['첫째 초점 ',''],
'3,11,2':['이다. 같은 방법으로 둘째 초점 ',''],
}.items():prose_and_native(at,parts)
for at,text in{
'3,3,0':'렌즈의 광학 중심을 지나는 광선은 방향이 바뀌지 않는다. 따라서 ',
'3,5,1':'점',
'3,8,0':'렌즈면에 수직이다. 이후에는 일반적인 작도를 한다. ',
'3,12,0':'윗그림에서 렌즈는 오목렌즈(발산렌즈)임을 알 수 있다. ',
}.items():p.add(at,text)
translated={tuple(s['at'])for s in p.slots};fragments={tuple(s['at'])for s in p.fragments}
for at in p.runs:
 if tuple(map(int,at.split(',')))not in translated|fragments:p.protect(at,'Original folio, focus subscript or mathematical punctuation; retain original font/GID/size and physical baseline.')
print(p.save())
