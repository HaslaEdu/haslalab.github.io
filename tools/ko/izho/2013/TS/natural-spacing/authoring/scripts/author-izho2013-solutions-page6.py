from izho2013_authoring import begin,around,finish
p=begin(6)
for at,text in{
 '3,0,0':'인 진동이다. 진동 중심인 새 평형점의 좌표는 다음과 같다: ',
 '5,0,0':'분명히 힘 ',
 '5,0,2':'가 최소가 되는 조건은 ',
 '6,17,0':'이며, 이로부터 ',
 '9,1,0':'도달하므로 다음을 얻는다: ',
 '11,7,0':'에서의 해는 다음과 같다: ',
 '17,0,0':'이에 해당하는 그래프는 다음과 같다: ',
 '28,0,0':'또한 운동 방정식은 다음과 같다: ',
 '32,16,0':'여기서 ',
 '32,16,2':'는 회로를 통과한 전하이다. ',
}.items():p.add(at,text)
around(p,'9,0,0',['',' 앞의 물음 ','에서 고리는 진동의 반 주기 만에 자석 가장자리에 '],['7.','6'])
around(p,'11,0,0',['',' 식 ','에 대한 초기 조건 '],['8.','(17)'])
around(p,'14,0,0',['식 ','에 따르면 고리의 전류는 다음과 같이 변한다: '],['(15)'])
around(p,'26,1,0',['',' 고리에 대한 옴의 법칙은 다음과 같다: '],['9.'])
around(p,'30,0,0',['식 ','와 ','을 유한 차분으로 쓰면 다음과 같다: '],['(25)','(26)'])
around(p,'32,17,0',['식 ','과 ','을 연립하면 다음을 얻는다: '],['(27)','(28)'])
finish(p,[],'Complete original2013 page6 viewed at144dpi. Preserve full original oscillatory-current plot/axes/labels/curves, native italic F and q in prose, original x(0)=0 and derivative initial condition with all native primes, source enumerators7/6/8/9 and exact references(17)/(15)/(25)/(26)/(27)/(28), all display counters(18)-(29), fractions/roots/trigonometric/script math and original CyrillicН/с units. Original F_min subscript is a mathematical index, not translated. All source prose points, styles and baselines retained without fitting.')
