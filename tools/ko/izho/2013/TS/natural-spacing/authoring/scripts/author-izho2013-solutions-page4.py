from izho2013_authoring import begin,around,finish
p=begin(4)
for at,text in{
 '3,0,0':'한편 옴의 법칙은 다음과 같다: ',
 '4,14,0':'따라서 전류와 속도의 관계는 다음과 같다: ',
 '6,0,0':'고리에는 자기장 안으로 다시 끌어당기는 힘이 작용한다. 이 힘은 ',
 '6,1,0':'앙페르 법칙으로 구한다: ',
 '9,0,0':'따라서 운동 방정식은 다음과 같다: ',
 '11,3,0':'에서 구한 해는 다음과 같다: ',
 '21,0,0':'고리가 자기장 밖으로 완전히 나올 때 ',
 '22,17,0':'따라서 다음 시각에 대한 방정식을 얻는다: ',
 '27,0,3':'를 추정하자. 식 ',
 '28,7,0':' 뒤 고리는 종단 속도 ',
 '29,8,2':'까지 고리가 일정한 가속도 ',
 '29,13,0':', 그런 다음 ',
 '29,14,0':'종단 속도 ',
 '29,16,1':'로 움직인다고 가정하면 추정값은 다음과 같다: ',
 '35,4,3':' 이후 고리는 일정한 가속도 ',
 '35,4,5':'로 계속 움직인다. 이때 ',
 '35,5,0':'속도는 시간에 대해 연속이어야 하므로, 속도의 시간 의존성은 다음과 같다: ',
 '46,0,0':'이에 해당하는 그래프는 다음과 같다: ',
}.items():p.add(at,text)
around(p,'11,0,0',['식 ','에 초기 조건 '],['(5)'])
around(p,'16,0,0',['',' 식 ','을 적분하면 다음 관계를 얻는다: '],['3.','(6)'])
around(p,'27,0,0',['식 ','는 초월방정식으로 해석적으로 풀 수 없다. '],['(9)'])
around(p,'28,0,0',['','에서 특성 시간 '],['(6)'])
around(p,'29,8,0',['시간 ','부터 '],['0'])
around(p,'35,0,0',['식 ','의 수치해는 '],['(9)'])
around(p,'35,4,0',['',' 시각 '],['4.'])
finish(p,[],'Complete original2013 page4 viewed at144dpi. Preserve every native differentiation/integration/fraction/exponential/brace glyph and original vector fraction rule, all display counters(1)-(11) at original positions, exact original inline v(0)=0, t0, tau~mR/B2a2, v0=FR/B2a2, w=F/m, source numeral0, original source Cyrillicс unit and numerical10.25/10.5. Source font family/style/points/baselines and italic mathematical typography remain unchanged. Korean prose is authored without fitting, leaving complete native expressions to common-motion packing and independent ink audit.')
