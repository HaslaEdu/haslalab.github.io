from izho2014_authoring import begin,around,finish
p=begin(8)
for at,text in{
 '5,0,0':'따라서 ',
 '7,0,0':'원기둥 내부에서 단위 시간에 발생하는 열은 줄의 법칙을 미분형으로 써서 ',
 '7,1,0':'구할 수 있다 ',
 '13,0,0':'원기둥 내부에서 발생한 열은 원기둥의 표면을 통해 ',
 '13,1,0':'모두 빠져나가야 하므로 ',
 '17,17,0':'다음과 같은 해를 얻는다 ',
 '21,0,0':'따라서 도선 중심에서의 온도는 ',
 '25,1,0':'다음과 같이 나타낼 수 있다 ',
 '33,1,0':'이 경우에 적용하면 ',
 '44,0,0':'따라서 도선 내부에 저장된 자기장 에너지는 ',
 '51,0,2':'이고 길이가 ',
 '51,0,4':'인 도선의 얇은 층을 생각하자. ',
 '51,1,0':'이 층이 놓인 반지름 구간은 ',
 '51,4,0':'. 이 층에 작용하는 전체 앙페르 힘은 ',
 '51,21,0':'따라서 압력 차는 다음과 같다 ',
}.items():p.add(at,text)
around(p,'16,0,0',['미분방정식 ','에 식 ','과 다음 초기 조건을 적용하면 '],['(11)','(10)'])
around(p,'25,0,0',['',' 도선 반지름의 변화는 고체의 열팽창 법칙에 따라 '],['4.'])
around(p,'33,0,0',['',' 자기장 세기는 앙페르의 순환 법칙으로 정해진다. 이를 '],['5.'])
around(p,'36,0,0',['식 ','를 이용하면 최종적으로 '],['(9)'])
around(p,'39,0,0',['',' 자기장의 에너지 밀도는 '],['6.'])
around(p,'51,0,0',['',' 평형 조건을 구하기 위해, 폭이 '],['7.'])
finish(p,[],'Full original2014 page8 read at144dpi: radial heat generation/conduction, temperature profile, thermal expansion, magnetic field energy and pressure balance. Keep all original radial integrals and limits, script/fraction/radical typography, original fractional point sizes, source(11)/(10) reference order, exact numeric299 K,5.70e-9 m,8.33e-10 J, original source signs and all display counters(8)-(21). Width l and length L, all native mu/rho/sigma/kappa/gamma/alpha/beta symbols and scripts remain original encoded glyphs. No mathematical correction, retyping or point fitting.')
