from pathlib import Path
import sys
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2010-complete-solutions');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2010,11);p.header()
for at,text in {
 '1,0,0':'운동량은 ',
 '3,0,0':'이다. 따라서 최종 광자의 ',
 '3,1,0':'운동량은 입사 양성자의 운동량과 크기 차수가 같다. ',
 '3,5,0':'앞의 ',
 '5,0,0':'의 부호를 바꾼다. 최종 운동량 ',
 '7,0,0':'은 식 (9)의 초기 광자 ',
 '8,0,0':'운동량 ',
 '10,0,0':'과 크기가 같아, 광자와 양성자의 운동량이 변하지 않는다. ',
 '13,0,0':'에서, ',
 '13,1,0':'반응은 광자가 양성자의 뒤에서 따라잡을 때에만 가능하다. ',
 '13,2,0':'(양성자가 광자의 뒤에서 움직이면 광자를 따라잡을 수 없다.) ',
 '15,0,0':'에서 광자 에너지는 양성자가 정지할 때 최소이며, 다음 조건으로 구한다: ',
 '17,1,0':'따라서 ',
 '21,0,0':'이는 배경 복사 광자의 에너지보다 훨씬 크다. ',
 '22,1,0':'채점 기준 ',
 '22,3,0':'항목 ',
 '22,4,0':'배점 ',
 '22,6,0':'해석적 표현식 (1) ',
 '22,8,0':'식 (1)의 수치 계산 ',
 '22,11,0':'식 (5) ',
 '22,13,0':'식 (5)가 불변임을 명시 ',
 '23,0,0':'식 (6)으로부터 두 운동량이 반대 방향일 때 ',
 '23,1,0':'문턱 에너지가 최소임을 설명 ',
 '25,0,0':'식 (8)의 유도 ',
 '25,2,0':'관계식 (10)의 유도 ',
 '25,4,0':'식 (13), (16) 또는 (21)의 유도 ',
 '25,8,0':'식 (19)의 유도 ',
 '25,11,0':'식 (25), (26)의 유도 ',
 '25,13,0':'식 (27)의 유도 ',
 '25,16,0':'에너지·운동량 보존으로부터 (28)~(30) 유도 ',
 '25,21,0':'식 (33)의 유도 ',
}.items():p.add(at,text,align='center'if at in ['22,1,0','22,3,0','22,4,0']else None)
def fragments(at,literals,texts):
 rest=p.runs[at]['text']
 for literal,text in zip(literals,texts):
  a,rest=rest.split(literal,1)
  if a:p.add(at,text,a)
  elif text:raise ValueError((at,text))
  p.protect_fragment(at,literal,'Original mathematical symbol, coordinate or subpart label.')
 if rest.strip():p.add(at,texts[-1],rest)
 elif texts[-1]:raise ValueError((at,texts[-1]))
fragments('3,3,0',['В)'],['',' 최종 광자가 은하계에서 뒤로 나아가면 질량중심계에서도 '])
fragments('3,4,0',['OZ'],['음의 ',' 방향으로 움직인다. 이 경우 식 (9)에서 '])
p.add('11,1,0','초기 운동량이 같은 방향으로 나란한 경우 ',p.runs['11,1,0']['text'].split('6. ',1)[1])
fragments('13,3,0',['Δ'],['따라잡는 광자는 ',' 입자를 들뜨게 할 만큼 큰 에너지가 필요하다. '])
fragments('25,6,0',['G'],['로런츠 인자 ',' (17)의 유도 '])
fragments('25,18,0',['A','B'],['로런츠 변환으로 식 (31) 유도: ','와 ',''])
for at,run in p.runs.items():
 if 'Italic'in run['font']or run['font'].startswith('BookmanOldStyle'):p.protect(at,'Original mathematical expression or particle label retains all encoded source glyphs and relative geometry.')
print(p.save())
