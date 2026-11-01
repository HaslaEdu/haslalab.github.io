from pathlib import Path
import sys
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2010-complete-solutions');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2010,10);p.header()
p.protect('26,1,0','Original OZ coordinate-axis label and source punctuation.')
for at,text in {
 '3,0,0':'은하계에서 반응 (2)에 따른 양성자의 운동량 손실을 추정하자. ',
 '3,1,0':'반응의 질량중심계에서는 다음 두 경우가 가능하다. ',
 '4,3,0':'아래 로런츠 변환으로 구한다: ',
 '8,0,0':'은 ',
 '8,1,0':'초기 운동량 ',
 '10,0,0':'보다 상당히 작을 수 있다. 초기 양성자 ',
 '10,1,0':'운동량을 우주선의 최댓값 ',
 '12,0,0':'으로 두고, ',
 '14,0,0':'는 ',
 '16,0,0':'는 식 (12)를 이용하면, 식 (27)의 수치는 ',
 '18,4,0':'양성자 운동량 식 (27)에서 ',
 '20,0,0':'앞의 부호를 바꾼다. 초기 운동량이 ',
 '20,1,0':'우주선 ',
 '20,2,0':'양성자의 ',
 '20,3,0':'최댓값 ',
 '22,1,0':'일 때 ',
 '22,2,0':'최종 운동량은 ',
 '22,3,0':'',
 '24,4,1':' 주어진 조건에서 콤프턴 산란 후 광자와 양성자는 ',
 '24,5,0':'반응 ',
 '26,0,0':'에서 모두 양의 방향으로 나아간다. 축: ',
 '30,1,0':'연립 방정식 (28)을 ',
 '32,0,0':'에 대해 풀면 ',
 '35,0,0':'이 값 ',
 '37,0,0':'를 알면 식 (28)에서 ',
 '44,0,0':'따라서 ',
 '46,0,0':', 즉 에너지 변화량( ',
 '46,0,2':')과 ',
 '46,1,0':'운동량 변화량은 크기가 같고 부호가 반대이다. 이는 ',
 '46,2,0':'다음의 경우에만 가능하며, ',
 '48,0,0':', 즉 충돌 전후에 에너지와 ',
 '48,1,0':'운동량이 변하지 않는다. ',
 '48,4,0':'은하계에서 최종 광자의 운동량은 ',
 '51,0,0':'우주선 양성자의 최대 운동량 ',
 '53,0,0':'에서, ',
 '55,0,0':'는 식 (8), ',
 '57,0,0':'는 식 (12)를 이용하면 식 (31)의 수치는 ',
 '59,0,0':'이다. 최종 양성자의 ',
}.items():p.add(at,text)
def fragments(at,literals,texts):
 rest=p.runs[at]['text']
 for literal,text in zip(literals,texts):
  a,rest=rest.split(literal,1)
  if a:p.add(at,text,a)
  elif text:raise ValueError((at,text))
  p.protect_fragment(at,literal,'Original mathematical coordinate, variable or source subpart label.')
 if rest.strip():p.add(at,texts[-1],rest)
 elif texts[-1]:raise ValueError((at,texts[-1]))
fragments('4,1,0',['А)','OZ'],['',' 파이 중간자는 양의 ',' 방향, 양성자는 '])
fragments('4,2,0',['OZ'],['반대의 ',' 방향으로 움직인다. 동반계에서 최종 양성자 운동량은 '])
fragments('6,1,0',['G'],['여기서는 식 (17)의 ',' 인자를 이용하였다. 최종 운동량 '])
fragments('18,2,0',['В)','OZ'],['',' 파이 중간자는 음의 ',' 방향, 양성자는 '])
fragments('18,3,0',['OZ'],['양의 ',' 방향으로 움직인다. 이 경우에는 최종 '])
p.add('24,2,0','콤프턴 산란에 의한 운동량 손실을 구하자. ',p.runs['24,2,0']['text'].split('5. ',1)[1])
for at in ['24,4,0','48,2,0']:p.add(at,'풀이 ','Вариант ')
p.add('26,3,0','은하계에서 에너지와 운동량 보존 법칙을 적용하면: ',p.runs['26,3,0']['text'].split('А) ',1)[1]);p.protect_fragment('26,3,0','А)','Original source subpart label.')
p.add('39,2,0','최종 광자가 은하계에서 뒤로 나아가면 ',p.runs['39,2,0']['text'].split('B) ',1)[1]);p.protect_fragment('39,2,0','B)','Original source subpart label.')
fragments('48,2,1',['OZ'],['. 반응의 질량중심계에서 최종 광자는 양의 ',' 방향, '])
fragments('48,3,0',['OZ'],['최종 양성자는 음의 ',' 방향으로 움직인다. 이 경우의 로런츠 변환으로부터 '])
for at,run in p.runs.items():
 if 'Italic'in run['font']or run['font'].startswith('BookmanOldStyle'):p.protect(at,'Original mathematical expression retains its source font, glyphs, point sizes and geometry.')
print(p.save())
