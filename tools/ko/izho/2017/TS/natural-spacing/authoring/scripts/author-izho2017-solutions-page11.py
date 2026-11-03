from izho2017_authoring import begin,around,finish
p=begin(11)
for at,text in {
 '20,12,2':'문제의 조건에서 ',
 '20,12,3':'회로의 입력 전압은 다음과 같다 ',
 '20,22,0':'따라서 저항은 다음과 같은 간단한 형태로 나타난다 ',
 '32,14,0':'정육면체 각기둥에 해당하는 ',
 '32,18,2':'다음 경우 ',
 '32,22,0':'의 회로는 쉽게 알 수 있다 ',
 '33,0,0':'하지만 ',
 '33,4,0':'일 때는 다음과 같이 각기둥을 추가로 연결해야 한다 ',
 '34,3,0':'나타내자 ',
 '36,0,0':'여기서 ',
 '36,9,0':'그러면 ',
}.items():p.add(at,text)
around(p,'20,0,0',['마지막 단계에서는 식 ','의 관계를 이용하였다 '],['(5)'])
for at,n in [('20,12,1','0.2'),('26,0,1','1.0'),('32,18,1','0.5'),('34,2,1','1.0')]:around(p,at,['','점',' '],[f'[{n} ',']'])
around(p,'26,0,2',['표 ','의 수치를 이용하면 쉽게 계산할 수 있다. '],['1'])
around(p,'27,0,0',['표 ','. 각기둥의 저항 '],['2'])
around(p,'32,17,0',['일 때의 저항은 앞의 ','에서 구한 값과 같다. '],['2.1'])
around(p,'34,1,0',['두 경우 모두 저항은 표 ','의 값과 일치한다. '],['2'])
around(p,'34,2,2',['식 ','의 극한은 여러 방법으로 구할 수 있다. 예를 들어 다음과 같이 '],['(28)'])
finish(p,[[27,0]],'Full original2017 page11 read at144dpi. Source12pt ordinary and bold bracketed score roles retained. The original centered Table2 caption and every original native table glyph/fraction/point/row/column remain fixed; source prism/circuit diagrams are unchanged. Long complete original display equation26 and labels26–29 retain fonts/GIDs/paint/Y. All inline N=4/N=1/N=2 and lambda forms stay original; translated prose packs naturally without English-width gaps or size fitting.')
