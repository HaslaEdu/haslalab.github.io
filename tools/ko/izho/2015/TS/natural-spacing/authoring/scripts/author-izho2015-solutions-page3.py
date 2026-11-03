from izho2015_authoring import begin,around,finish
p=begin(3)
for at,text in{
 '1,0,0':'채점 기준 ',
 '1,2,0':'직선들이 등온선임을 ',
 '1,3,0':'밝힘 ',
 '3,1,0':'카르노 순환을 선택함 ',
 '3,4,0':'단열 과정의 방정식을 씀 ',
 '3,5,0':'그 방정식을 로그 눈금으로도 ',
 '3,6,0':'나타냄 ',
 '5,1,0':'직선을 올바르게 ',
 '5,2,0':'그림 ',
 '7,1,0':'효율을 구함 ',
 '7,4,0':'합계 ',
 '8,3,1':'을 광축과 만날 때까지 연장한다. 이 교점이 렌즈의 ',
 '8,4,0':'광학적 중심이다. ',
 '8,6,0':'그 광선이 렌즈면과 만나는 점을 지나는 직선을 긋는다. ',
 '8,7,0':'이어서 상을 지나는 직선을 그어 주광축과의 교점을 구하면, ',
 '8,8,0':'그 점이 렌즈의 후초점이다. 같은 방법으로 전초점도 구한다. 초점들이 정해지면 ',
 '8,9,0':'통상적인 광선 작도법으로 두 번째 광원의 상을 구할 수 있다. ',
 '10,0,0':'채점 기준 ',
 '10,2,0':'렌즈의 광학적 중심을 ',
 '10,3,0':'구함 ',
 '11,6,0':'렌즈의 초점들을 구하고 ',
 '11,7,0':'표시함 ',
 '12,6,0':'두 번째 광원의 상을 구하고 ',
 '12,7,0':'표시함 ',
}.items():p.add(at,text)
around(p,'8,0,0',['문제 ',' '],['1.3'])
around(p,'8,1,0',['',' 직선 '],['1.'])
around(p,'8,5,0',['',' 초점의 위치를 구하려면 점광원을 지나 광축과 평행한 광선을 그리고, '],['2.'])
for at,num in [('10,4,0','1'),('10,5,0','2'),('10,6,0','3'),('11,8,0','1'),('11,9,0','2'),('11,10,0','3'),('12,8,0','1')]:around(p,at,['- 동그라미 ',' 안에 표시; '],[num])
finish(p,[[1,0],[8,0],[10,0]],'Full original2015 page3 read at144dpi, including both grading tables and complete lens ray diagram. Preserve all source diagram lines, concentric-circle score targets, native A/B/C/F1/F2/S-prime source labels, original SS-prime mathematical glyphs and every source grading value/decimal comma. Optical center and front/back focal-point construction is translated into Korean physical terminology without changing source diagram or equations. All original12pt heading/body roles, physical baselines and caption/title centers are retained. No type-size fitting.')
