from izho2017_authoring import begin,around,finish
p=begin(2)
for at,text in {
 '5,0,0':'이 문제에서는 ',
 '6,24,0':'평가 항목 ',
 '6,25,0':'배점 ',
 '6,34,0':'단열 과정 대신 에너지 보존 법칙을 적용 ',
 '6,42,0':'구의 부피 공식 ',
 '6,44,0':'올바른 답 ',
 '6,46,0':'합계 ',
 '7,1,0':'파동의 간섭으로 신호를 상쇄할 수 있다. 파원 ',
 '7,3,0':'과 ',
 '7,5,1':'의 파동은 수신기에 같은 위상으로 도달하므로, 제3의 파원에서 온 파동은 ',
 '7,6,0':'수신기에 도달할 때 파원 ',
 '7,7,2':'과 ',
 '7,9,1':'의 파동과 반대 위상이어야 한다. 이를 위해 ',
 '8,0,0':'제3의 파원에서 수신기까지의 거리는 다음만큼 차이가 나야 한다 ',
 '8,6,0':'. 여기서 ',
 '9,8,0':'이다. 이 조건을 만족하는 점을 찾으려면 두 원군을 그린다. ',
 '10,0,0':'하나는 반지름이 ',
 '10,8,0':'이고 중심이 ',
 '10,10,1':'인 원군이며, 다른 하나는 ',
 '11,0,0':'반지름이 ',
 '11,8,0':'이고 중심이 ',
 '11,10,1':'인 원군이다. 두 원군의 교점이 ',
 '12,0,0':'제3의 파원을 놓을 위치이며, 그림에 동그라미로 표시하였다. ',
 '12,2,0':'즉, 파원 ',
 '12,3,2':'과 ',
 '12,6,0':'커야 한다. 즉, ',
}.items():p.add(at,text)
around(p,'6,11,0',['이 조건에서 식 ','의 연립 해는 다음과 같다 '],['(1) - (4)'])
around(p,'7,0,0',['문제 ','점',' '],['1С (3.0 ',')'])
around(p,'12,1,0',['제3의 파원에서 나오는 파동의 진폭은 원래 진폭의 ','배여야 한다. '],['2'])
around(p,'12,5,1',['의 파동에 비해 제3의 파원에서 오는 파동의 세기는 ','배 '],['4'])
for slot in p.slots:
 if slot['at']in[[6,24,0],[6,25,0]]:slot['align']='center'
finish(p,[[7,0]],'Full original2017 page2 visually read at144dpi. Preserve original serif12pt body,13.92pt subsection center, actual native S/A subscripts and all complete inline lambda/2 fraction expressions including original vector rules and scripts. The original diagram, source mathematical descriptors initial/final/surf/electr/gas, scoring numbers and display equation labels3–5 remain native in their original fonts/points/paint. Normal Korean particle attachment replaces English-width gaps; no new math or font resizing.')
