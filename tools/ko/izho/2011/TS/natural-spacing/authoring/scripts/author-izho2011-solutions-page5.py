from pathlib import Path
import sys,re
B=Path('C:/Users/andre/.codex/tmp/Hasla-original-style-20261102/izho2011-complete-solutions');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2011,5);p.header()
for at,text in{
'5,0,0':'정의에 따라 도체의 세제곱미터당 전자 수는 ',
'5,0,2':'이다. 각 전자는 ',
'5,1,2':'동안 전달한다. 따라서 ',
'5,4,0':'는 전자들이 단위 부피·단위 시간에 결정 격자로 전달하는 에너지이다: ',
'10,1,0':'보였다. ',
'11,0,0':'자기 저항 ',
'11,3,0':'자기장이 있을 때 전자의 운동 방정식은 ',
'13,0,0':'각 좌표축 방향의 성분은 ',
'19,0,2':'평면 위에 있다. 다음 치환을 ',
'28,21,0':'또는 원래 변수로 나타내면 ',
'32,0,0':'여기서 ',
'32,5,0':'초기조건 ',
'32,8,0':'과 ',
'32,12,0':'으로부터 상수 ',
'32,17,0':'와 ',
}.items():p.add(at,text,align='center'if at=='11,0,0'else None)
p.add('11,2,0','점','point')
def references(at,parts):
 source=p.runs[at]['text'];matches=list(re.finditer(r'\d+',source));assert len(parts)==len(matches)+1,(at,source,parts);cursor=0
 for i,m in enumerate(matches):
  if cursor<m.start():p.prose_range(at,cursor,m.start(),parts[i])
  else:assert not parts[i]
  p.protect_range(at,m.start(),m.end(),'Original source equation-reference numerals in exact encoded font/GID/12pt/baseline.');cursor=m.end()
 if cursor<len(source):p.prose_range(at,cursor,len(source),parts[-1])
 else:assert not parts[-1]
for at,parts in{
'5,1,0':['식 (',')의 운동 에너지를 시간 간격 '],
'10,0,0':['이 식은 식 (',')와 같으므로 드루드 모형에서 줄–렌츠 법칙이 성립함을 '],
'19,0,0':['식 (',')에 따르면 전자의 궤적은 '],
'20,9,0':['을 식 (',')–(',')에 대입하면 '],
'26,0,0':['식 (','), (',')의 해는 다음 조화 진동이다: '],
'33,4,0':['를 얻는다. 이를 식 (','), (',')에 대입하면 '],
}.items():references(at,parts)
translated={tuple(s['at'])for s in p.slots};fragments={tuple(s['at'])for s in p.fragments}
for at in p.runs:
 if tuple(map(int,at.split(',')))not in translated|fragments:p.protect(at,'Reviewed original complete mathematical expression, fraction/derivative, physical vector/unit, trigonometric function, script, numerical marker or XY plane label. Preserve exact original font programs/GIDs/fractional points/y and native rules/Forms; no equation retyping.')
print(p.save())
