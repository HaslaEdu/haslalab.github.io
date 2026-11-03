from izho2015_authoring import begin,around,finish
p=begin(7)
for at,text in{
 '1,0,0':'원판 전체에서 자석이 만드는 자기장의 축 방향 성분 변화를 ',
 '1,2,0':'따라서 자석의 좌표가 ',
 '1,2,2':'이면, 그 위치의 자기장은 ',
 '11,0,0':'마지막 식에서는 다음 조건을 사용하였다 ',
 '11,4,0':'고리 안의 전류 밀도는 옴의 법칙으로 주어진다 ',
 '13,0,0':'고리에 흐르는 전류가 ',
 '13,3,0':'이므로, 고리의 자기 모멘트는 ',
 '17,0,0':'원판 전체에 대해 적분하면 전체 자기 모멘트는 ',
 '28,0,0':'원판의 영향을 고려한 자석의 운동 방정식은 다음과 같다 ',
 '30,0,0':'여기서 ',
 '32,1,0':'다음과 같다 ',
 '45,0,0':'여기서 ',
 '45,0,2':'이다. 이 식으로부터 각진동수의 상대 변화는 ',
}.items():p.add(at,text)
around(p,'1,1,0',['무시할 수 있다고 가정한다. 이 성분 역시 식 ','로 정해진다. '],['(4)'])
around(p,'6,0,0',['이를 식 ','에 대입하여 미분하면 '],['(10)'])
around(p,'22,0,0',['자석에 작용하는 힘을 구하려면 식 ','을 적용한다. 이때 자기장은 '],['(8)'])
around(p,'22,1,0',['식 ','로 계산한다. 대입하면 다음 식을 얻는다 '],['(4)'])
around(p,'31,13,0',['는 식 ','에서 정한 계수이다. '],['(16)'])
around(p,'32,0,0',['',' 문제에 주어진 감쇠 진동 방정식의 해를 이용하면 '],['1.2.3'])
around(p,'55,0,0',['',' 따라서 특성 감쇠 시간은 '],['1.2.4'])
around(p,'63,0,0',['',' 줄의 법칙에 따라 원판의 순간 열 손실 전력은 '],['1.2.5'])
around(p,'71,0,0',['이는 식 ','의 힘과 자석 속도의 곱과 같다. '],['(16)'])
finish(p,[],'Full original2015 page7 read at144dpi. Preserve all source magnetic-field/current/moment/force equations(11)-(18), actual fractional Times MathType points, Cambria Math beta definition and complete Joule-loss integral, all native alpha/beta/rho/mu/z/R/h/r and p_m scripts, native source signs and approximation powers exactly. The source defines damping coefficient b again; no variable is renamed or mathematical statement corrected. Native x<<z condition and source subsection labels1.2.3-1.2.5 stay encoded original. Only source narrative is translated with normal Korean spacing at original12pt body baselines.')
