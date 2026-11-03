from izho2017_authoring import begin,around,finish
p=begin(1)
for at,text in {
 '1,0,0':'이론시험 문제',
 '2,0,0':'해설',
 '2,1,0':'주의. 채점 기준의 배점은 나누어 부여하지 않는다!',
 '3,2,0':'시간 간격 ',
 '3,4,1':' 동안 모래 상자에 맞는 탄환 수를 ',
 '3,7,0':'이라 하자. ',
 '3,8,0':'그러면 모래 상자에 전달되는 운동량은 ',
 '3,12,0':'이며, 이는 다음 ',
 '3,13,0':'수평력이 작용하는 것과 같다 ',
 '4,0,0':'편향각이 ',
 '4,0,2':'일 때 수평력 ',
 '4,0,4':'가 하는 일은 ',
 '4,9,0':'여기서 ',
 '4,9,2':'은 매단 점에서 질량 중심까지의 거리이다. ',
 '4,10,0':'이 일이 모두 다음과 같은 표적의 퍼텐셜 에너지로 바뀔 때 ',
 '4,11,0':'편향각이 최대가 된다 ',
 '4,21,0':'에너지 보존 법칙 ',
 '4,24,0':'에서 최종 답을 얻는다 ',
 '7,1,0':'평가 항목 ',
 '7,2,0':'배점 ',
 '12,0,0':'수치 ',
 '12,9,0':'합계 ',
 '13,1,0':'표면 전하의 반발로 비눗방울의 크기가 증가한다. 관성 때문에 비눗방울은 ',
 '13,2,0':'평형 위치를 지나 진동한다. 기체의 내부 마찰로 진동이 사라지면서 ',
 '13,3,0':'비눗방울은 새로운 평형 상태에 이른다. 이 과정에서 비누막의 운동 에너지는 ',
 '13,4,0':'기체의 내부 에너지로 전달된다. 따라서 이 상황에서는 기체에 ',
 '13,5,0':'단열 과정의 관계식을 적용할 수 없다. ',
 '13,6,0':'비누막과 기체로 이루어진 계에 에너지 보존 법칙을 적용하면 ',
 '15,0,0':'표면 장력을 고려하면 비눗방울 내부 기체의 초기 압력은 다음과 같다 ',
 '19,0,0':'정전기적 반발력을 고려한 최종 압력은 다음과 같다. ',
 '19,1,0':'대전된 구를 찢으려는 힘에 관한 잘 알려진 문제를 떠올리면 된다 ',
}.items():p.add(at,text)
for at,label in [('3,0,0','1 (10.0 '),('3,1,0','1A (3.0 '),('13,0,0','1В (4.0 ')]:around(p,at,['문제 ','점',' '],[label,')'])
for at,n in [('8,0,0',1),('9,0,0',2),('9,8,0',3),('10,0,0',4)]:around(p,at,['식 ',' '],[f'({n})'])
for slot in p.slots:
 if slot['at']in[[7,1,0],[7,2,0]]:slot['align']='center'
finish(p,[[1,0],[2,0],[2,1],[3,0],[3,1],[13,0]],'Full original2017 page1 visually read at144dpi. Original16.08pt bold-italic two-line main title,13.92pt subsection titles,12pt serif prose,10.08pt bold Arial header retained. All formulas remain exact original mathematical native fonts/fractional points/Forms and complete fraction rules. Formula(n) labels and adjacent same-cell mathematics pack naturally together; scoring numbers at x502.75 and all stationary displayed-equation labels remain fixed. Preserve source Cyrillic В and decimal conventions. No formula regeneration or font fitting.')
