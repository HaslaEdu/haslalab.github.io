from izho2017_authoring import begin,around,finish
p=begin(10)
for at,text in {
 '1,0,0':'표준적인 방법으로 다음과 같이 쉽게 계산할 수 있다 ',
 '2,0,0':'따라서 주어진 연결에서 정육면체의 저항은 다음과 같다 ',
 '4,0,2':'회로와 초기 조건의 대칭성에서 다음 관계를 ',
 '4,1,0':'바로 얻는다 ',
 '4,22,2':'한 접점으로 들어오는 전류의 대수적 합은 영이다. 따라서 ',
 '4,23,0':'옴의 법칙으로 다음 접점에 대한 방정식을 얻는다 ',
 '13,0,0':'다음 관계 ',
 '13,7,0':'가 성립하므로 다음 점화식을 얻는다 ',
 '13,26,2':'모든 전위 ',
 '13,27,2':'를 유일하게 정하려면 ',
 '13,28,0':'두 경계 조건이 필요하다. 하나는 초기 전위이며, ',
 '13,28,1':'그 값은 다음과 같다 ',
 '13,37,2':'에 대해 성립한다. 특히 ',
 '13,38,0':'다음 경우 ',
 '13,42,0':'에도 성립한다. 회로에는 번호가 ',
 '13,42,2':'인 접점이 없다는 점에 유의하자 ',
 '21,0,2':'전원 회로의 전류는 다음 접점에서 나오는 전류들의 합이다 ',
 '21,1,0':'즉, ',
 '34,0,0':'여기서는 다음 관계를 이용하였다 ',
 '34,15,0':'. 다음 전위 ',
 '34,20,0':'를 대입하면 ',
}.items():p.add(at,text)
for at,n in [('4,0,1','0.2'),('4,22,1','1.0'),('13,26,1','0.2'),('13,48,1','0.2'),('21,0,1','0.4')]:around(p,at,['','점', ' ' if at!='4,22,1' else ''],[f'[{n} ',']'])
around(p,'13,37,0',['다른 조건은 대칭 조건 ','에서 얻으며, 임의의 '],['(19)'])
around(p,'13,48,2',['점화식 ','은 앞의 수학적 준비에서 다루었다. '],['(21)'])
around(p,'13,49,0',['따라서 구한 해 ','을 다음과 같이 적용할 수 있다 '],['(16)'])
finish(p,[],'Full original2017 page10 read at144dpi. Original source12pt body and bracketed bold score roles retained. Complete source circuit-reduction diagram is unmodified, including every arrow, R0 fraction and native diagram label. Display labels17–25 fixed and all original native multilevel fractions/scripts stay at original Y/points. Inline y/x/k/N relations stay native. Preserve the literal source boundary-condition conventions; ordinary Korean prose spacing only.')
