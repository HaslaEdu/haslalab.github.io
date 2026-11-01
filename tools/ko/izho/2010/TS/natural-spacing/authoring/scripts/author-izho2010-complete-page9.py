from pathlib import Path
import sys
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2010-complete-solutions');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2010,9);p.header()
for at,text in {
 '5,0,0':'여기서는 ',
 '8,0,0':'식 (13)에서 ',
 '11,0,0':'따라서 ',
 '16,0,0':'여기서는 다음 조건을 이용하였다: ',
 '18,1,0':'최종적으로 정면충돌의 문턱 운동량은 식 (14)~(17), (8)에서 ',
 '22,1,0':'따라서 우주선의 최대 에너지는 ',
 '25,0,0':'실험에 따르면 우주선에는 이보다 에너지가 높은 양성자가 ',
 '27,1,0':'거의 존재하지 않는다. ',
 '29,0,0':'는 식 (11)을 다음과 같이 바꾸어 구할 수도 있다: ',
 '33,1,0':'이 식은 식 (13), (16)과 일치한다. ',
 '34,0,1':'. 로런츠 변환 없이도 문턱 에너지를 구할 수 있다. ',
 '34,2,0':'가 관성계에 무관함을 이용한다. 은하계에서 식 (6)을 적용하면, ',
 '34,3,0':'초기 운동량이 반대 방향인 반응 (2)의 문턱에서는( ',
 '38,1,0':'이 식으로부터 ',
 '43,0,0':'배경 복사에는 다음 관계가 성립하므로 ',
 '45,0,0':'',
 '45,1,0':'식 (23)은 식 (18)로 정리된다. ',
 '47,1,0':'여기서 ',
 '49,0,0':'는 파이 중간자의 정지 질량이다. 이 식을 두 번 제곱하면 ',
}.items():p.add(at,text)
def split(at,literal,left,right):
 a,b=p.runs[at]['text'].split(literal)
 if a:p.add(at,left,a)
 if b.strip():p.add(at,right,b)
 elif right:raise ValueError((at,right))
 p.protect_fragment(at,literal,'Original physical variable or mathematical expression within source prose.')
split('7,0,0','G','. 로런츠 변환의 ',' 인자만 구하면 된다. ')
split('13,1,0','G','따라서 ',' 인자는 ')
split('27,2,1','x=',' 질량중심 속도의 비 ','')
split('31,1,0','x=1','두 근 중 비물리적인 근은 ','이고, 물리적인 근은 ')
split('34,1,0','M','물리계의 전체 내부 에너지(정지 질량) ','')
split('45,3,0','π+N','4. 반응의 질량중심계에서 최종 상태 ','에 대해 ')
for at,word in [('27,2,0','Вариант '),('34,0,0','Вариант ')]:p.add(at,'풀이 ',word)
for at,run in p.runs.items():
 if 'Italic'in run['font']or run['font'].startswith('BookmanOldStyle'):p.protect(at,'Original formula or subscript retains its source encoded font and geometry.')
print(p.save())
