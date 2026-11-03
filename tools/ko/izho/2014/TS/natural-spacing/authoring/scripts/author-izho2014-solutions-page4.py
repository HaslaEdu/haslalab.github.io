from izho2014_authoring import begin,around,finish
p=begin(4)
for at,text in{
 '2,7,0':'서로 다른 물체 위치에서 같은 크기의 상을 만들 수 없다. 따라서 이 렌즈는 볼록 렌즈이다. ',
 '4,3,0':'세 배 큰 물체가 같은 크기의 상을 만들 위치이다. 따라서 원래 물체의 상은 ',
 '5,0,0':'채점 기준 ',
 '5,2,0':'평가 항목 ',
 '5,3,0':'배점 ',
 '5,5,0':'올바른 답 ',
 '5,8,0':'올바른 답을 뒷받침하는 타당한 근거 ',
 '5,11,0':'렌즈 공식 적용에 오류가 있음 ',
 '5,13,0':'합계 ',
 '6,2,0':'실험실 기준계에 대해 로켓과 같은 속도로 움직이는 관성 기준계이다. ',
 '6,3,0':'고유 기준계에서 로켓은 고려하는 순간 정지해 있다. 로켓의 질량이 ',
 '6,3,2':'이고 ',
 '6,4,0':'시각 ',
 '6,4,2':'에 질량 ',
 '6,4,4':'의 연료를 속도 ',
 '6,4,6':'로 방출하면, 로켓의 ',
 '6,5,0':'속도 변화는 ',
 '6,6,1':'이며, 운동량 보존 법칙은 다음과 같다 ',
 '6,24,0':'고전역학에서는 갈릴레이 변환에 따라 실험실 기준계에서 로켓의 속도 변화가 ',
 '6,25,0':'고유 기준계에서의 속도 변화와 같아야 한다. ',
 '6,31,0':'일 때 ',
 '6,35,0':'치올콥스키의 이름을 딴 다음 공식을 얻는다 ',
}.items():p.add(at,text)
for at,literal in [('2,0,0','1'),('2,4,0','2'),('3,0,0','3')]:around(p,at,['그림 ',' '],[literal])
around(p,'2,6,0',['그림 ','에서 알 수 있듯이, 오목 렌즈에서는 '],['2'])
around(p,'4,0,0',['렌즈의 초점에 대해 대칭인 물체 위치 ','와 ','에서는 '],['A','B'])
around(p,'4,1,0',['같은 크기의 상을 얻는다(그림 ',' 참조). 물체를 '],['3'])
around(p,'4,2,0',['추가로 ','만큼 멀리 옮기면 위치 ','에 놓이게 되며, 이는 '],['5 cm','C'])
around(p,'4,4,0',['세 배 작아진다. 답: ',' '],['1/3 cm.'])
around(p,'6,0,0',['문제 ',' 제트 추진','점',' '],['2',' (10 ',')'])
around(p,'6,1,0',['',' 로켓의 운동을 고유 기준계에서 살펴보자. 여기서 고유 기준계란 '],['1.'])
around(p,'6,26,0',['따라서 초기 조건을 적용하여 식 ','을 풀면 '],['(1)'])
for slot in p.slots:
 if slot['at']in[[5,2,0],[5,3,0]]:slot['align']='center'
finish(p,[[2,0],[2,4],[3,0],[5,0],[6,0]],'Full original2014 page4 read at144dpi. Retain all three optical ray diagrams, original Cyrillicсм labels inside the figure, A/B/C/F native variables, original5 cm and1/3 cm numeric text, all grade values, original14.04pt centered jet-propulsion title, and every exact native rocket variable/script/velocity glyph at its fractional point. Source equation(1) and initial conditions m=m0,v=0 remain encoded source mathematics; nothing is retyped. Caption centers and physical baselines follow the source. Only English prose is translated.')
