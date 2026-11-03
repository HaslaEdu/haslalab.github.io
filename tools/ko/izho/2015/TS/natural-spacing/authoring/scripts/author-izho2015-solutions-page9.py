from izho2015_authoring import begin,around,finish
p=begin(9)
for at,text in{
 '6,0,0':'첫 번째 항은 평형 위치를 추가로 이동시킨다. 사용한 근사 아래에서 ',
 '6,1,0':'그 이동량은 다음과 같다 ',
 '23,0,0':'따라서 각진동수의 상대 변화는 ',
 '29,1,0':'이 전류는 원판 안의 전기장으로 정해진다(',
 '29,1,2':'). 원판 안의 전기장은 ',
 '29,2,0':'구가 만드는 다음 전기장과 ',
 '32,0,0':'유도 전하가 만드는 반대 방향의 다음 전기장에 의해 정해진다 ',
 '36,0,0':'따라서 옴의 법칙 ',
 '36,0,6':'는 다음과 같이 쓸 수 있다 ',
 '40,0,0':'관계식 ',
 '40,0,2':'과 ',
 '40,0,6':'를 이용하면 ',
 '40,1,0':'최종적으로 다음 방정식을 얻는다 ',
 '49,0,4':' 또는 ',
 '49,2,6':'의 비는 ',
 '49,3,3':'로, 매우 작다. 따라서 다음 방정식의 영차 근사에서는 ',
 '52,0,0':'첫 번째 항을 무시할 수 있으므로 ',
 '56,0,0':'다음 차수의 근사는 ',
 '61,0,0':'벡터도를 이용해서도 이 문제를 풀 수 있다. ',
 '67,0,0':'따라서 구의 운동 방정식은 다음과 같다 ',
}.items():p.add(at,text)
around(p,'12,0,0',['',' 식 ','의 두 번째 항은 진동의 각진동수 변화를 정한다 '],['2.2.2','(24)'])
around(p,'29,0,0',['',' 원판 표면의 전하 밀도 ','는 원판 내부의 전류에 의해 변한다. '],['2.2.3','σ'])
around(p,'49,2,0',['',' 조화 진동에서 '],['2.2.6'])
around(p,'49,2,4',['','의 진폭과 '],['̇'])
around(p,'54,1,1',['',' 및 ',''],[')','𝑝̇'])
around(p,'56,0,2',['','를 원래 방정식에 대입하여 구한다 '],['̇'])
around(p,'61,1,0',['',' 원판이 구에 가하는 힘은 '],['2.2.7'])
finish(p,[],'Full original2015 page9 read at144dpi: equilibrium/frequency shift, finite conductivity/charge relaxation and higher-order polarization response. Preserve exact original source reference(24), original subsection labels2.2.2-2.2.7, all native Cambria Math and fractional Times math CIDs, complete source integrals/radicals/fraction bars, derivative dots including the source extra Times combining-dot glyphs beside p-dot, and equation labels(25)-(28). Only literal English conjunction and embedded in Cambria Math between closing parenthesis and p-dot is explicitly prose; every adjacent symbol remains native under a source-pinned literal policy. No mathematics, font points or source signs are corrected or regenerated.')
