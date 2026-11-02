from pathlib import Path
import sys
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2010-complete-solutions');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2010,8);p.header()
for at,text in {
 '3,0,0':'의 방향으로 잡는다. 배경 복사의 등방성 때문에 ',
 '4,0,0':'배경 복사 광자는 두 방향 ',
 '10,1,0':'운동량의 크기 ',
 '12,0,0':'가 주어졌을 때, 반응 (2)의 문턱 에너지는 ',
 '14,0,0':'광자가 양성자와 반대 방향으로 움직이는 정면충돌에서 ',
 '14,1,0':'최소가 된다. ',
 '14,2,0':'실제로 ',
 '14,3,0':'충돌하는 ',
 '14,4,0':'두 입자의 ',
 '14,5,0':'전체 ',
 '14,6,0':'내부 ',
 '14,7,0':'에너지는 ',
 '14,8,0':'',
 '14,9,0':'초기 에너지가 최소인 반응 문턱에서 ',
 '16,0,0':'이다. 한편 식 (5)에서 ',
 '16,1,0':'',
 '19,0,0':'이 식에서 광자 에너지 ',
 '21,0,0':'가 일정할 때 ',
 '22,0,0':'양성자의 에너지 ',
 '24,0,0':'는 운동량 ',
 '26,0,0':'와 ',
 '28,0,0':'가 반대 방향일 때 최소이다. ',
 '31,0,0':')에서 ',
 '34,0,0':'여기서 ',
 '36,0,0':'는 양성자의 운동량, ',
 '40,0,0':'에서 정지한다. 반응 (2)의 조건은 ',
 '42,1,0':'여기서 ',
 '46,0,0':'는 양성자의 정지 질량이다. 따라서 ',
 '49,0,0':'또는 ',
 '54,0,0':'에서의 광자 운동량(8)과 은하계에서의 ',
 '56,0,0':'사이의 관계는 로런츠 변환으로 주어진다: ',
 '59,0,0':'정면충돌의 경우에는 ',
 '63,1,0':'여기서 ',
 '67,2,0':'식 (10)으로부터 다음 비를 정의한다: ',
 '71,0,0':'수치를 대입하면 ',
 '74,0,0':'이 값 ',
 '74,0,2':'가 작으므로 ',
 '76,0,0':'도 1에 가깝다. 따라서 ',
 '76,1,0':'다음과 같이 쓸 수 있다: ',
 '79,0,0':'여기서 ',
 '83,0,0':'에서 ',
 '83,1,0':'은하계의 ',
 '85,0,0':'으로 변환할 때에도, 정면충돌의 경우 ',
 '87,0,0':'다음과 같다: ',
}.items():p.add(at,text)
def split(at,literal,left,right):
 a,b=p.runs[at]['text'].split(literal);p.add(at,left,a)
 if b.strip():p.add(at,right,b)
 elif right:raise ValueError((at,right))
 p.protect_fragment(at,literal,'Original coordinate, particle or Lorentz-frame mathematical label.')
split('1,1,0','ОZ','축 ','를 운동량 ')
p.protect('6,0,0','Original coordinate-axis label ОZ and comma.')
for at in ['8,0,0','10,0,0']:p.protect(at,'Original OX/OY coordinate-axis label and punctuation.')
p.add('29,0,0','양성자와 배경 복사 광자의 질량중심계( ',p.runs['29,0,0']['text'].split('3а. ',1)[1]);p.protect_fragment('29,0,0','3а.','Original subpart numbering.')
split('38,0,0','Δ(1232)','는 광자의 운동량, ',' 입자는 질량중심계 ')
split('44,0,0','Δ(1232)','는 ',' 입자의 정지 질량, ')
p.add('52,2,1','풀이 ','Вариант ')
split('52,3,0','p+γ','질량중심계 ','')
split('65,0,0','p+γ','는 질량중심계 ','에서의 광자 에너지이다: ')
split('81,2,0','p+γ','양성자의 운동량을 질량중심계 ','')
for at,run in p.runs.items():
 if 'Italic'in run['font']or run['font'].startswith('BookmanOldStyle'):p.protect(at,'Original physical formula, symbol or subscript retains its encoded source glyphs.')
print(p.save())
