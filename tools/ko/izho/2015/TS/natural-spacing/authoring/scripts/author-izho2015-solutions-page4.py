from izho2015_authoring import begin,around,finish
p=begin(4)
for at,text in{
 '2,3,0':'합계 ',
 '3,2,0':'관이 물로 가득 차는 순간 용기 안 공기의 압력은 다음과 같다 ',
 '3,14,0':'용기 벽의 열전도율이 매우 크므로, 내부 공기의 온도는 ',
 '3,15,0':'변하지 않는다. 따라서 상태 방정식은 ',
 '3,39,0':'여기서 ',
 '3,39,2':'는 용기의 단면적이고, ',
 '3,39,4':'는 용기 안 공기의 몰수이다. ',
 '5,6,0':'이 방정식의 해는 다음과 같다 ',
 '11,1,0':'만족해야 한다. 조건 ',
 '11,1,4':'일 때 ',
 '11,1,8':'이거나, ',
 '11,1,12':'일 때 ',
 '11,1,14':'이어야 하므로, ',
 '17,0,0':'수치를 대입하면 ',
 '17,13,0':'의 함수로 다음과 같이 주어진다 ',
 '17,25,2':'에 대한 이상 기체의 상태 방정식은 ',
 '22,1,0':'조건 ',
 '25,0,0':'그 수치를 구하면 ',
 '28,8,0':'공기가 물을 밀어내면서 한 일은 다음과 같이 구한다 ',
 '48,0,0':'열역학 제1법칙에 따라 공기에 전달된 열은 ',
}.items():p.add(at,text)
for at,num in [('1,0,0','2'),('1,1,0','3')]:around(p,at,['- 동그라미 ',' 안에 표시; '],[num])
around(p,'3,0,0',['문제 ',' 물이 든 용기','점',' '],['2.',' (7 ',')'])
around(p,'3,1,0',['',' 용기에 물을 붓는 동안 공기가 압축되어 그 압력이 증가한다. '],['1.'])
around(p,'4,0,0',['식 ','에서 다음 이차방정식을 얻는다: '],['(1) - (3)'])
around(p,'11,0,0',['식 ','의 두 해 중 작은 값을 택해야 한다. 그 이유는 다음 조건을 '],['(5)'])
around(p,'17,12,0',['',' 물이 평형 상태에 있으므로, 용기 안 공기의 압력은 '],['2.'])
around(p,'17,25,0',['',' 임의의 '],['3.'])
around(p,'17,37,0',['이를 식 ','과 결합하면 '],['(1)'])
around(p,'22,0,0',['',' 공기가 용기 밖으로 물을 모두 밀어내는 온도는 '],['4.'])
around(p,'22,1,2',['으로 정해진다. 식 ','에 따라 '],['(10)'])
around(p,'25,13,0',['',' 공기의 내부 에너지 변화는 '],['5.'])
around(p,'48,13,0',['이를 식 ','와 ','에 대입하면 '],['(13)','(14)'])
finish(p,[[3,0]],'Full original2015 page4 read at144dpi. Preserve complete original Cambria Math native ideal-gas/hydrostatic/quadratic/fraction/radical/integral expressions and counters(1)-(16), all exact native x0/p0/T0/v/S/L/h definitions and conditions, their source8.4/12pt scripts and2.4pt source offsets, and unchanged numerical7.86e-2m/350K. Source variable v is the original encoded symbol for amount of gas and is never replaced with another Greek/Latin glyph. All formulas, source literal references and original table continuation remain native. Only prose is translated at original source points/baselines; no mathematics fitting or regeneration.')
