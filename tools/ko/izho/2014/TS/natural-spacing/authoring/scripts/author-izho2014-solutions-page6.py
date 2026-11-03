from izho2014_authoring import begin,around,finish
p=begin(6)
for at,text in{
 '7,0,0':'이에 따라 두 기준계에서 측정한 속도 변화 사이에는 ',
 '7,1,0':'다음 관계가 성립한다 ',
 '18,0,0':'로런츠 변환에 따르면 ',
 '28,0,0':'두 기준계에서의 시간 간격은 다음 관계를 만족한다 ',
 '38,3,0':'으로 두면 최종적으로 ',
 '45,3,0':'인 경우에 적용하면 ',
 '47,0,0':'따라서 다음을 얻는다 ',
 '61,0,0':'채점 기준 ',
 '61,2,0':'평가 항목 ',
 '61,3,0':'배점 ',
}.items():p.add(at,text)
around(p,'38,0,0',['식 ','을 식 ','로 나누고 '],['(17)','(19 )'])
around(p,'42,0,0',['',' 고유 기준계에서는 로켓의 운동이 고전역학을 따르므로, 그 가속도는 '],['8.'])
around(p,'45,0,0',['가속도 변환식 ','과 시간 변환식 ','를 '],['(20)','(19)'])
around(p,'50,0,0',['',' 계산하면 다음과 같다 '],['9.'])
around(p,'55,0,0',['',' 계산하면 다음과 같다 '],['10.'])
for at,literal in [('61,6,0','(1)'),('61,9,0','(2)'),('61,12,0','(3)'),('61,18,0','(5)'),('61,22,0','(6)'),('61,24,0','(7)')]:around(p,at,['식 ',' '],[literal])
around(p,'61,15,0',['식 ','의 올바른 수치 '],['(4)'])
for slot in p.slots:
 if slot['at']in[[61,2,0],[61,3,0]]:slot['align']='center'
finish(p,[[61,0]],'Full original2014 page6 read at144dpi: relativistic velocity, acceleration and time transformations, rocket mass relation, two numerical cases and start of the grading table. Preserve every original radical/fraction/integral-free MathType native program, all physical fractional points and original r/p indices, counters(16)-(25), exponent28630 and1730 kg values. Original printed reference(19 ) includes its space and is deliberately retained as native source text. Table grid and quarter-point scores remain exact. Only complete English prose slots are translated; no formula or point fitting.')
