from pathlib import Path
import sys
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/izho2018-theory-original');sys.path.insert(0,str(B/'engine'))
from source_slot_authoring import PagePlan
p=PagePlan(2018,2);p.header()
for at in ['1,0,0','2,0,0','5,0,0','5,12,0']:
 p.add(at,'문제 ','Problem ',align='center');p.add(at,'점','points',align='center')
for at,label,text in [
 ('2,1,0','A1',' 질량 중심이 치우친 가느다란 원통형 시험관이 '),
 ('3,0,0','A2',' 같은 시험관을 물이 담긴 '),
 ('3,3,0','A2.1',' 시험관이 작은 거리 '),
 ('3,12,0','A2.2',' 평형 위치 부근에서 시험관의 속력은 '),
 ('4,7,0','A2.3',' 좁은 용기 속 시험관의 작은 진동의 '),
 ('5,8,0','1.',' 스위치를 닫은 직후 다이오드에 흐르는 '),
 ('5,10,0','2.',' 다이오드를 통과한 총전하량을 구하시오. '),
]:
 source=p.runs[at]['text'];assert source.startswith(label)
 p.protect_fragment(at,label,'Original native problem/subquestion label or enumerator in exact original font/point/baseline.')
 p.add(at,text,source[len(label):])
for at,text in {
 '1,1,0':'이 문제는 서로 독립인 세 부분으로 이루어져 있다. ',
 '2,2,0':'매우 넓은 용기의 물에 수직으로 떠 있다. 평형 상태에서 잠긴 ',
 '2,3,0':'깊이는 ',
 '2,4,2':'이고, 시험관의 단면적은 ',
 '2,6,1':'이다. 작은 수직 진동의 ',
 '2,7,0':'주기를 구하시오. ',
 '3,1,0':'단면적이 ',
 '3,1,2':'인 좁은 원통형 용기에 넣는다. ',
 '3,2,0':'시험관은 용기 축을 따라 작은 진동을 한다. ',
 '3,3,2':'만큼 내려간다. ',
 '3,4,0':'계의 퍼텐셜 에너지 변화를 ',
 '3,4,2':', ',
 '3,5,0':'초기 잠긴 깊이 ',
 '3,6,2':', 단면적 ',
 '3,10,0':', 물의 ',
 '3,11,0':'밀도 ',
 '3,11,2':'와 중력 가속도 ',
 '3,11,4':'로 나타내시오. ',
 '3,13,2':'이다. 계의 ',
 '3,14,0':'운동 에너지를 다음 값들로 나타내시오: ',
 '3,15,0':'속력 ',
 '3,16,2':', 잠긴 깊이 ',
 '3,17,2':', ',
 '4,0,0':'단면적 ',
 '4,4,0':', 물의 밀도 ',
 '4,4,2':'를 사용한다. 시험관과 ',
 '4,5,0':'용기 벽 사이의 틈에서는 모든 물이 ',
 '4,6,0':'같은 속력 ',
 '4,6,2':'로 움직인다. ',
 '4,8,0':'주기를 구하시오. ',
 '5,1,0':'왼쪽 회로의 소자: 이상적인 다이오드, ',
 '5,2,0':'전기 용량 ',
 '5,3,0':'전압 ',
 '5,4,0':'각 저항은 ',
 '5,5,0':'축전기는 충전되지 않았고 스위치는 열려 있다. ',
 '5,6,0':'스위치를 닫으면 다이오드에 전류가 흐른다. ',
 '5,9,0':'전류를 구하시오. ',
 '5,13,0':'정17각형의 꼭짓점 17곳에 ',
 '5,14,0':'동일한 렌즈가 하나씩 있다. 렌즈의 광학 중심은 ',
 '5,15,0':'꼭짓점과 정확히 일치한다. 각 렌즈의 면은 ',
 '5,16,0':'그 렌즈에 인접한 한 변에 수직이다. ',
 '5,17,0':'모든 렌즈의 초점 거리는 ',
 '5,18,1':'이고, 이는 ',
 '5,19,0':'정17각형의 한 변의 길이와 같다. 한 렌즈에 ',
 '5,20,0':'광축을 따라 평행 광선을 입사시키면, ',
 '5,21,0':'광선 하나가 닫힌 경로를 따른다. 이 경로에 ',
 '5,22,0':'내접하는 원의 반지름을 구하시오. 모든 렌즈가 ',
 '5,23,0':'수렴 렌즈인 경우와 발산 렌즈인 경우를 각각 ',
 '5,24,0':'고려하시오.',
 '5,24,1':' 모든 각이 작아서 ',
 '5,25,1':'가 성립한다고 하시오. ',
}.items():p.add(at,text,align='center'if at=='1,1,0'else None)
for at,native,after,text in [
 ('5,2,2',' = 100 μF',', an ideal diode, a ','인 축전기, '),
 ('5,3,2',' = 10.0 V',', three identical resistors ','인 정전압원, 동일한 저항 세 개, '),
 ('5,4,2',' = 10.0 kΩ',' and a switch. At the initial ','이며 스위치가 있다. 처음에 '),
]:
 assert p.runs[at]['text']==native+after,(at,p.runs[at]['text'])
 p.protect_fragment(at,native,'Original complete numerical electrical value and unit; exact original font/point/baseline and all encoded mathematical glyphs retained.')
 p.add(at,text,after)
at='5,7,0';source=p.runs[at]['text'];native='τ = 462 ms';assert source.count(native)==1
before,after=source.split(native)
p.add(at,'흐르는 시간은 ',before);p.protect_fragment(at,native,'Original complete diode-current duration including Greek tau, equality, digits and unit in native source font.');p.add(at,'이며, 이후 멈춘다. ',after)
# Explicit physical variables/subscripts in the original TNR/Italic math
# fragments are deliberately never selected as translated prose. Cambria Math
# and Symbol glyphs are independently protected by the shared native builder.
for at in ['2,4,0','2,4,1','2,5,0','2,6,0','3,1,1','3,3,1','3,4,1','3,6,0','3,6,1','3,7,0','3,8,0','3,8,1','3,9,0','3,13,0','3,13,1','3,16,0','3,16,1','3,17,0','3,17,1','4,1,0','4,2,0','4,2,1','4,3,0','4,6,1','5,2,1','5,3,1','5,4,1']:
 p.protect(at,'Original physical mathematical variable, subscript or mathematical comma; exact original encoded font/glyph/point/baseline retained, no equation transcription.')
print(p.save())
