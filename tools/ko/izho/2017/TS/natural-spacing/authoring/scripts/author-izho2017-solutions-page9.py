from izho2017_authoring import begin,around,finish
p=begin(9)
for at,text in {
 '1,0,0':'따라서 ',
 '2,0,2':'힌트를 이용하여 ',
 '2,5,0':'를 점화식에 대입하면 다음 ',
 '2,6,0':'미지수 ',
 '2,6,2':'에 관한 방정식을 얻는다 ',
 '2,24,0':'정리하면 다음 이차방정식이 된다 ',
 '2,36,0':'그 두 해는 다음과 같다 ',
 '2,66,0':'여기서 ',
 '2,70,0':'는 다음 경계 조건으로 정해지는 임의의 상수이다 ',
 '8,0,0':'이 연립 일차방정식을 풀면 ',
 '39,0,0':'마지막 관계를 유도할 때는 비에타 정리에서 얻는 다음 관계를 이용하였다 ',
 '40,0,2':'위에서 구한 ',
 '41,2,0':'의 식을 이용하면 ',
 '41,45,0':'따라서 최종적으로 ',
 '51,4,2':'정육면체에서 전위가 같은 꼭짓점들을 연결하면 ',
 '51,5,0':'다음 등가 회로를 얻는다 ',
}.items():p.add(at,text)
for at,n in [('2,0,1','1.0'),('40,0,1','0.5'),('51,4,1','0.8')]:around(p,at,['','점',' '],[f'[{n} ',']'])
around(p,'2,47,0',['따라서 점화식 ','의 일반해는 다음과 같이 나타난다 '],['(3)'])
around(p,'23,0,0',['이 해를 식 ','에 대입하면 다음과 같은 대칭적인 형태로 정리할 수 있다 '],['(11)'])
around(p,'51,3,0',['','. 각기둥 모양의 철사틀 (','점',' '],['2','7.0 ',')'])
finish(p,[[51,3]],'Full original2017 page9 visually read at144dpi. Original12pt serif ordinary prose and12pt bold centered subsection are retained. All native lambda/C1/C2/AN mathematical objects, source subscript x0 convention, original12pt counter labels7–16, roots and complete fraction rules remain unchanged. The original prism/circuit images and arrow vector retain exact native resources, color and geometry. Normal Korean prose spacing; no regenerated equations or type-size fitting.')
