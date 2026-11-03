from izho2014_authoring import begin,around,finish
p=begin(1)
for at,text in{
 '1,0,0':'이론시험 문제 ',
 '2,0,0':'해설 ',
 '2,3,0':'제1단계에서는 일정한 압력에서 ',
 '2,4,0':'끓으므로 온도도 일정하다. ',
 '2,5,0':'마찬가지로 제3단계에서는 ',
 '2,6,0':'압력과 온도가 일정한 상태에서 응축된다. ',
 '2,7,0':'제2·4단계는 단열 과정으로 본다. ',
 '2,8,0':'증기 기관의 (',
 '2,8,2':') 순환 과정은 ',
 '2,9,0':'오른쪽 그림과 같이 나타난다. ',
 '2,10,0':'두 등온 과정과 두 단열 과정으로 ',
 '2,11,0':'이루어지므로, 이는 카르노 순환이다. ',
 '2,12,0':'따라서 그 효율은 다음과 같다 ',
 '6,0,0':'여기서 ',
 '6,1,2':'은 순환의 제1단계에서의 ',
 '6,2,0':'끓는점이고, ',
 '6,4,1':'는 순환의 제3단계에서의 응축 온도이다. ',
 '6,5,0':'각 온도는 문제에 주어진 포화 증기압의 근사식을 이용하여 ',
 '6,6,0':'구할 수 있다. ',
 '6,7,0':'순환의 제1단계에서 압력은 다음 값으로 일정하다 ',
 '8,0,0':'증기의 온도는 물의 끓는점과 같으며, 그 값은 다음과 같다 ',
 '15,0,0':'따라서 증기 기관의 효율은 ',
 '19,0,0':'채점 기준 ',
 '19,2,0':'평가 항목 ',
 '19,3,0':'배점 ',
 '19,11,0':'순환이 카르노 순환임을 알아냄 ',
 '19,14,0':'올바른 순환 과정 그래프 ',
 '19,23,0':'효율의 올바른 수치 ',
 '19,25,0':'합계 ',
}.items():p.add(at,text)
around(p,'2,1,0',['문제 ','점',' '],['1 (10 ',')'])
around(p,'2,2,0',['문제 ','점',' '],['1A (3 ',')'])
around(p,'12,0,0',['식 ','의 온도 차는 다음과 같이 구하면 편리하다 '],['(1)'])
around(p,'19,5,0',['','단계와 ','단계는 등압·등온 과정 '],['1','3'])
around(p,'19,8,0',['','단계와 ','단계는 단열 과정 '],['2','4'])
around(p,'19,17,0',['카르노 순환 효율을 나타내는 식 ',' '],['(1)'])
around(p,'19,20,0',['식 ','와 ',' '],['(2)','(4)'])
for slot in p.slots:
 if slot['at']in[[19,2,0],[19,3,0]]:slot['align']='center'
finish(p,[[1,0],[2,0],[2,1],[2,2],[19,0]],'Full original2014 page1 read at144dpi. Preserve original15.96pt bold italic two-line title,14.04pt subsection centers,12pt Times prose and9.96pt Arial header. The upper body stays in its original column beside the unchanged P-V cycle graph. All Carnot, vapor-pressure and efficiency formulae remain original native MathType glyphs at their precise fractional points; all fraction bars and scripts move only as complete native expressions. Keep original Cyrillic temperature units, four display counters(1)-(4), table scores and original grading grid. Only prose is translated; no point fitting or vector redraw.')
