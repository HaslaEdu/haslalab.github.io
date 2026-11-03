from izho2016_authoring import begin,around,score,finish
p=begin(5)
for at,text in{
 '8,5,0':'두 근의 안정성 분석 ','8,8,0':'올바른 결과 ',
 '8,11,0':'실근이 없는 조건 ','11,2,0':'각도의 수치 ',
 '11,8,0':'기본 원리: 퍼텐셜 에너지 변화량이 표면 에너지의 ',
 '11,9,0':'변화량보다 커야 함 ',
 '18,1,0':'반지름의 수치(유효숫자 고려) ','21,0,0':'합계 ',
 '22,1,2':'오랜 시간이 지나면 회로에 흐르는 전류가 영이 되고 축전기가 완전히 ',
 '22,2,0':'충전된다. 즉, ',
 '22,16,0':'따라서 전원의 전압이 축전기에 걸리며, 전압 ',
 '22,17,1':'에서의 전기용량은 그래프에서 다음과 같이 얻는다 ',
 '22,30,0':'그러므로 축전기의 전하량은 다음과 같다 ',
 '22,41,2':'회로에 흐르는 전류는 유한하다. 그러나 축전기를 충전하여 ',
 '22,42,0':'전압을 ',
 '22,42,4':'까지 높이려면 무한한 전하량이 필요하다. 따라서 충전 시간은 ',
 '22,56,2':'축전기의 전하량을 ','22,56,4':', 전기용량을 ',
 '22,57,0':'라 하자. 모든 소자가 직렬로 연결되어 있으므로 ',
 '24,10,0':'여기서 전류는 다음과 같다 ',
 '31,0,0':'여기서 ','33,0,2':'는 축전기 전하량의 함수이다. ',
 '34,0,0':'함수 ','34,0,2':'는 주어진 그래프 ',
 '34,0,4':'에서 쉽게 구할 수 있으며, ',
 '34,1,0':'아래 그림과 같이 일차함수가 된다. ',
}.items():p.add(at,text)
around(p,'1,1,0',['식 ',' '],['(12)'])
around(p,'8,1,0',['식 ','를 풂 '],['(12)'])
around(p,'15,0,0',['부등식 ',' '],['(15)'])
around(p,'22,0,0',['문제 ',' 비선형 축전기 ','점',' '],['3.','(10,0 ',')'])
around(p,'26,11,0',['식 ','을 식 ','에 대입하면 '],['(6)','(5)'])
for at in ['22,1,1','22,41,1','22,56,1']:score(p,at)
finish(p,[[22,0]],'Full original2016 page5 read at144dpi. The upper continuation rubric has genuine separate score and bold subtotal columns; preserve the entire original grid and fixed scores. Same-cell labels Equation12, root-absence condition, angle value and Inequality15 must pack with entire original native expressions including root/fraction rules; keep separate-line numerical radius display fixed. Preserve Problem3 original decimal-comma title score, body Cambria Math12pt and scripts8.52/6.96pt, every original unit and source Cl spelling, original U0=5V split across lines, all seven display labels. Inline f(q)=R/(U0-q/C(q)) must move as one original CID+all nested fraction bars unit, with no retyping or sizing changes.')
