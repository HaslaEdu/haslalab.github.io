from izho2016_authoring import begin,around,score,finish
p=begin(7)
for at,text in{
 '1,14,0':'다음과 같이 다시 쓴다 ',
 '10,6,0':'여기서 유효 전기용량은 다음과 같다 ',
 '12,8,0':'잘 알려진 바와 같이, 축전기의 리액턴스는 다음과 같다 ',
 '15,0,0':'직렬로 연결된 저항과 축전기에 흐르는 전류를 구하기 위해 ',
 '15,1,0':'아래 그림의 벡터도를 이용하자. ',
 '16,1,0':'이 벡터도에서 전류의 진폭은 다음과 같이 쉽게 구한다 ',
 '21,0,0':'전류와 전압 사이의 위상차 ','21,0,2':'는 다음과 같다 ',
 '25,0,0':'최종적으로 전류의 시간 의존성은 다음과 같다 ',
 '25,9,2':'축전기 양단 전압 진동의 진폭은 벡터도에서 ',
 '25,10,0':'다음과 같이 구한다 ',
 '25,23,0':'마지막으로 축전기에 걸리는 전압의 직류 성분을 고려하면 ',
 '25,24,0':'다음과 같다 ',
 '28,0,0':'채점 기준 ','28,2,0':'평가 항목 ','28,3,0':'배점 ',
 '38,0,1':' 여기서 함수는 ',
}.items():p.add(at,text)
around(p,'1,13,0',['이 경우 전기용량은 전압에 의존하므로, 식 ','을 '],['(16)'])
for at,ref in [('28,6,0','(1)'),('28,10,0','(2)'),('28,12,0','(3)'),('28,15,0','(4)'),('28,19,0','(5)'),('31,0,0','(6)'),('34,0,0','(7)')]:around(p,at,['식 ',' '],[ref])
score(p,'25,9,1')
for slot in p.slots:
 if slot['at']in[[28,2,0],[28,3,0]]:slot['align']='center'
finish(p,[[28,0]],'Full original2016 page7 read at144dpi. Preserve source native vector diagram, arrow strokes, dotted construction, alpha and voltage/current labels exactly. All display equations19–27 retain their original Cambria Math fonts/GIDs/points, arbitrary source fractional vertical offsets, effective-capacitance scripts and complete nested rules. Preserve genuine content, score and bold subtotal columns of lower rubric. Every same-row native formula following translated Equation labels1–7 must pack with the label as a complete original expression; source Russian Уравнение4 is prose and translated too. The final rubric row continues on page8; original f(q)= expression on this line and its continuation below must remain source-faithful.')
