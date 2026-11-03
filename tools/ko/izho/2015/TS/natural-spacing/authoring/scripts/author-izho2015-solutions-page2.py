from izho2015_authoring import begin,around,finish
p=begin(2)
for at,text in{
 '2,3,0':'합계 ',
 '3,1,2':'. 따라서 ',
 '3,2,0':'이 직선들의 방정식은 다음과 같다 ',
 '4,12,0':'효율이 최대인 순환을 얻으려면 두 극점을 지나는 단열선 두 개를 그려 ',
 '4,13,0':'카르노 순환을 만들어야 한다. 단열 과정의 방정식은 ',
 '5,0,0':'여기서 ',
 '10,0,0':'는 이원자 분자 기체의 단열 지수이다. ',
 '11,0,0':'로그 눈금에서 이 방정식은 다음과 같다 ',
 '11,21,0':'이 함수들의 그래프는 기울기가 ',
 '11,21,2':'인 직선이다. ',
 '11,24,0':'순환의 효율은 다음과 같다 ',
}.items():p.add(at,text)
for at,num in [('1,0,0','2'),('1,1,0','3')]:around(p,at,['- 동그라미 ',' 안에 표시; '],[num])
around(p,'3,0,0',['문제 ',' '],['1.2'])
around(p,'3,1,0',['그림 ','의 직선은 기울기가 '],['1.2'])
around(p,'11,22,0',['식 ','의 상수는 절대 온도에 비례한다. 그림으로부터 '],['(1)'])
around(p,'11,23,0',['최고 온도가 최저 온도의 ','배임을 알 수 있으므로, '],['2'])
finish(p,[[3,0]],'Full original2015 page2 read at144dpi. Preserve the complete large logarithmic P/V graph, all native log2/const/gamma/Cp/CV/eta/T1/T2 expressions and original fraction/radical/vector rules at actual fractional source points. All four source display labels and literal50% are native unchanged. The original source introductory slope minus1 and minus1.4 are retained as native symbols. Continued grading rows and all scores keep the exact original grid and point values. Only prose is translated, without font fitting.')
