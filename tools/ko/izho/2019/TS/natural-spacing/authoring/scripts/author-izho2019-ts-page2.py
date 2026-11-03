import sys
sys.path.insert(0,'C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions')
from izho2019_ts_authoring import begin,around,finish
p=begin(2)
for at,text in{
 '1,0,0':'일정한 시간 동안 물체의 온도가 ','1,1,2':'에서 ',
 '1,2,2':'로 낮아졌다고 하자. ',
 '3,0,0':'여기서 ','3,0,2':'는 상수이다. ',
 '4,0,0':'그다음 같은 시간 구간에서도 온도 변화량에 동일한 계수 ',
 '4,0,2':'가 적용된다 ',
 '12,0,0':'이 식의 해는 다음과 같다 ',
 '17,0,0':'주어진 그래프에서 초기 온도는 ',
 '17,5,0':'다음과 같다: ',
 '18,19,0':'평가 항목 ','18,20,0':'배점 ',
 '18,21,0':'공기 온도를 올바른 방법으로 구함 ',
 '18,23,0':'공기 온도가 다음 범위에 있음: ',
 '18,31,0':'공기 온도가 다음 범위에 있음: ',
 '18,38,0':'공기 온도가 다음 범위에 있음: ',
 '18,46,0':'위의 범위를 벗어남 ', '18,48,0':'합계 ',
 '18,52,0':'부하의 저항 성분(임피던스의 실수부)을 ',
 '18,52,2':', 전체 회로의 리액턴스 성분을 ',
 '18,52,4':'라 하자. ',
 '18,53,0':'후자는 전체 임피던스의 허수부이다. 그러면 전류의 진폭은 ',
 '18,54,0':'다음과 같다 ',
 '22,0,0':'부하에서 소비되는 평균 열적 전력은 다음과 같다 ',
 '27,0,0':'전력은 ','27,1,0':'없어야 한다. 나머지 식은 ',
 '28,0,0':'코일을 축전기에 직렬로 연결하면 위상차를 없앨 수 있다. ',
 '28,1,0':'그 조건은 ',
 '30,0,2':'이므로 ',
 '32,1,0':'따라서 가장 간단한 부하는 ',
 '33,0,0':'최대 전력은 다음과 같다 ',
 '40,0,0':'평가 항목 ','40,1,0':'배점 ',
 '40,2,0':'위상차가 영임 ',
}.items():p.add(at,text)
around(p,'1,3,0',['그러면 식 ','에서 '],['(3)'])
around(p,'6,0,0',['식 ','과 ','에서 다음 관계를 얻는다 '],['(4)','(5)'])
around(p,'17,4,0',['이며, ','분 뒤의 온도는 '],['10'])
around(p,'17,11,0',['이며, ','분 뒤에는 '],['20'])
p.add('17,17,0','가 된다. ')
around(p,'17,18,0',['이 값들을 식 ','에 대입하면 공기 온도는 다음과 같다 '],['(7)'])
around(p,'18,51,0',['문제 ','점',' '],['1С (3.0 ',')'])
around(p,'27,0,2',['','일 때 최대이다. 즉, 회로에 위상차가 '],[' = 0'])
p.add('27,1,4','일 때 최대이다. ')
around(p,'32,2,0',['저항값이 ','옴인 저항과, 인덕턴스가 '],['2019'])
p.add('32,2,4','인 코일로 이루어진다. ')
for s in p.slots:
 if s['at']in[[18,19,0],[18,20,0],[40,0,0],[40,1,0]]:s['align']='center'
finish(p,[[18,51]],'Full original2019 sourcepage2 visually read at144dpi. Preserve all original cooling MathType formulas and T0=373K,T1=337K,T2=319K with their exact fractional native points/scripts, source gamma sign/convention, original displayed equations4–8 and literal equation6 denominator as printed. Entire temperature-range rubric translated; range formulas move as complete original Forms beside labels, with all native degree/C glyphs and grading columns fixed. Native10/20 minute and2019 numeric source prose references retained. Circuit solution I/P/Pmax displays and inline 1/(omega C)=omega L and L=1/(omega2 C)=1e-2 Hn move only as complete original CID/rule/clip groups when embedded in prose; original Hn spelling retained. Source right-hand resistor/coil graphic defines the lower narrow prose column. Source table Content/Points centers, original scores and all native math fonts/GIDs/points/Y/paint remain exact; terminal prose punctuation used for Korean predicate does not retype mathematical units. No fitting, rasterization or source-figure replacement.')
