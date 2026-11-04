from izho2017_authoring import begin,around,finish
p=begin(4)
for at,text in {
 '1,0,0':'얇은 층 하나가 만드는 자유 낙하 가속도는 다음과 같다 ',
 '5,3,0':'각뿔의 모든 층에 대해 합하면 ',
 '7,2,2':'우주선이 각뿔 행성의 꼭짓점에서 이륙할 때 행성과의 상호작용 에너지를 ',
 '7,3,0':'다음과 같이 두자 ',
 '7,3,3':', 이때 속력을 ',
 '7,3,6':'이라 하자. 에너지 보존 법칙에서 ',
 '7,4,0':'탈출 속도에 대한 다음 관계를 얻는다 ',
 '9,0,0':'마찬가지로 정육면체 행성에서 출발하는 우주선에 에너지 보존 법칙을 적용하면 ',
 '9,1,0':'다음과 같다 ',
 '11,0,0':'여기서 ',
 '11,0,3':'는 정육면체 행성과의 상호작용 에너지이다. ',
 '11,1,0':'다음 두 에너지 사이의 간단한 관계를 구하자: ',
 '11,1,3':'와 ',
 '11,1,6':'. 이를 위해 ',
 '11,2,0':'정육면체 행성의 중심에 놓인 우주선을 생각한다. 먼저 중심의 위치는 ',
 '11,3,0':'여섯 각뿔의 꼭짓점에 우주선을 놓은 것과 같다. 물질의 밀도 변화를 ',
 '11,4,0':'고려하면 정육면체 중심에 있는 우주선의 퍼텐셜 에너지는 ',
 '11,5,0':'다음과 같다 ',
 '12,4,0':'한편, 정육면체 중심은 서로 붙어 있는 동일한 여덟 정육면체의 꼭짓점이다. ',
 '12,5,0':'각 정육면체의 한 변의 길이는 ',
 '14,0,1':'이다. 일반적으로 정육면체 행성의 장에서 ',
 '14,1,0':'우주선의 퍼텐셜 에너지는 다음 식에 따라 행성 크기의 제곱에 비례한다 ',
 '16,1,0':'따라서 정육면체 중심의 우주선의 퍼텐셜 에너지는 ',
 '22,1,2':'이 문제에서는 아래 그림과 같이 극좌표계와 직교좌표계를 ',
 '22,2,0':'함께 사용한다. ',
 '23,0,0':'에너지 보존 법칙은 다음과 같다 ',
 '30,1,0':'여기서 ',
 '32,0,5':'은 구름의 전체 질량이다. ',
}.items():p.add(at,text)
around(p,'7,2,1',['','점',' '],['[2.0 ',']'])
around(p,'16,0,0',['크기가 절반인 정육면체에서는 상호작용 에너지가 ','분의 일로 줄어든다. '],['4'])
around(p,'18,3,0',['식 ','와 ','를 같게 놓으면 '],['(12)','(14)'])
around(p,'19,3,0',['식 ',', ', '와 ','를 연립하면 최종적으로 '],['(10)','(11)','(15)'])
around(p,'22,0,0',['','. 먼지 구름 (','점',' '],['2','6.0 ',')'])
around(p,'22,1,1',['','점',' '],['[2.5 ',']'])
finish(p,[[22,0]],'Full original2017 page4 read at144dpi. Keep source ordinary Times12pt,12pt bold subsection center and all Cambria mathematics at precise original fractional points and baselines. Original spaceship/cloud trajectory figure and vector arrows remain unchanged. Complete original a/2 and M=(4/3)piR^3rho4 inline formulas include all rules/scripts/Forms with one dx; every original display label8–17 stays fixed. No invented mathematical variables, font fitting or editorial insertions.')
