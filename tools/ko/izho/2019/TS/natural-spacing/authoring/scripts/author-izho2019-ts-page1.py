import sys
sys.path.insert(0,'C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions')
from izho2019_ts_authoring import begin,around,finish
p=begin(1)
for at,text in{
 '1,0,0':'이론시험 문제 ', '2,0,0':'해설 ',
 '2,1,0':'주의: 채점표의 배점은 나눌 수 없음! ',
 '4,1,0':'실은 늘어나지 않고 팽팽하므로, 원반의 속도는 항상 ',
 '4,2,0':'실에 수직이다. 따라서 실의 장력은 원반에 일을 하지 않으며, ',
 '4,3,0':'속력은 일정하게 유지된다 ',
 '5,11,0':'원반 궤적의 곡률 반지름은 풀려 있는 실의 길이 ',
 '5,11,2':'과 같다. ',
 '5,12,0':'따라서 실이 끊어지는 조건은 뉴턴의 운동 제2법칙으로 ',
 '5,13,0':'다음과 같이 구한다 ',
 '8,11,0':'실이 원기둥에 감기면서 그 길이는 다음과 같이 변한다 ',
 '9,10,0':'여기서 ',
 '10,11,0':'실이 회전하는 각속도는 다음과 같다 ',
 '14,10,0':'이를 적분하면 ',
 '24,0,0':'평가 항목 ','24,1,0':'배점 ',
 '24,2,0':'원반의 속력은 변하지 않음 ',
 '32,0,0':'합계 ',
 '32,4,0':'가능한 풀이. ',
 '32,4,1':'물체에서 공기로 전달되는 열의 일률은 ',
 '32,5,0':'물체의 온도 ','32,5,2':'와 공기 온도 ',
 '32,6,2':'의 차이에 비례하며, 비례계수는 ','32,6,4':'이다. 즉, ',
 '32,26,0':'이에 따라 열용량이 ','32,26,2':'인 물체가 온도 ',
 '32,26,4':'만큼 냉각되는 시간은 ',
 '33,0,1':'이며, 열수지 방정식은 다음과 같다 ',
 '34,18,0':'을 적용하면 해는 다음과 같다 ',
 '35,24,0':'여기서 ','35,29,0':'는 상수이다. ',
}.items():p.add(at,text)
around(p,'3,0,0',['문제 ','점',' '],['1 (10.0 ',')'])
around(p,'4,0,0',['문제 ','점',' '],['1A (4.0 ',')'])
around(p,'13,11,0',['식 ','에서 '],['(3)-(5)'])
around(p,'16,10,0',['식 ','을 식 ','에 대입하면, 구하는 시간은 다음과 같다 '],['(1)','(7)'])
around(p,'32,3,0',['문제 ','점',' '],['1В (3.0 ',')'])
around(p,'34,13,0',['식 ','과 ','에 초기 조건 '],['(1)','(2)'])
for s in p.slots:
 if s['at']in[[24,0,0],[24,1,0]]:s['align']='center'
finish(p,[[1,0],[2,0],[2,1],[3,0],[4,0],[32,3]],'Full original2019 source page1 visually read at144dpi. Retain source header RomanV exactly, original9.96pt Arial-BoldMT header and source12pt page1/12 numerals, original15.96pt two-line TimesNewRomanPS-BoldItalicMT main title and14.04pt attention/problem heading; source12pt problem1A/1B headings and italic Possible solution role preserved. Entire puck/string and cooling prose plus all grading prose translated. Pure rubric equations remain centered/stationary with original grid/score positions, native CambriaMath12/8.52/6.96pt and all original fraction/radical programs untouched. Original cooling MathType inline T,Tx,alpha,C,dT,dt,T=T0,beta=alpha/C retain complete original Form/clip and fractional Tf/Tm/points/Y/paint; logical prose baseline never normalizes their physical nativeY. Display counters1–8 then1–3 are source originals. Native CyrillicВ andС remain literal. No math retyping, rasterization, fitting or English-width word gaps.')
