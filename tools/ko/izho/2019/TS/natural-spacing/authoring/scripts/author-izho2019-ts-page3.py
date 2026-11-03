import sys
sys.path.insert(0,'C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions')
from izho2019_ts_authoring import begin,around,finish
p=begin(3)
for at,text in{
 '1,0,0':'근거를 제시하지 않음 ',
 '1,2,0':'코일의 인덕턴스 ', '3,2,0':'올바른 수치 ',
 '3,4,0':'최대 전력의 조건 ', '4,0,0':'최대 전력의 식 ',
 '7,0,0':'올바른 수치 ', '7,2,0':'합계 ',
 '9,0,0':'도체 구와 점전하 ',
 '9,1,1':'점전하 ','9,1,3':'가 만드는 전위는 다음과 같다 ',
 '12,0,0':'가상의 점전하 ','12,0,2':'가 만드는 전위는 다음과 같다 ',
 '21,0,1':'구의 표면을 나타내는 원의 방정식은 다음과 같다 ',
 '21,10,0':'변수 ',
 '26,0,1':'구는 접지되어 있으므로 전위가 영이다. 즉, ',
 '32,5,2':'에서 성립해야 한다. 따라서 ',
 '32,6,0':'일차항 ','32,6,2':'의 계수와 상수항은 각각 영이어야 한다. 즉, ',
 '45,10,1':'점전하에 작용하는 힘은 다음과 같다 ',
 '49,0,0':'따라서 구하는 일은 다음 적분으로 얻는다 ',
 '53,0,1':'점전하를 처음 위치에서 무한대까지 천천히 옮기자. 이때 구에 흐르는 전류는 ',
 '53,1,0':'무시할 만큼 작아, 줄 열의 방출은 고려하지 않아도 된다고 하자. ',
 '53,2,0':'에너지 ','53,2,3':'는 점전하 ','53,2,5':'의 에너지, ',
 '53,2,8':'는 유도 전하의 ',
}.items():p.add(at,text)
around(p,'8,0,0',['문제 ',' 전기장 속의 도체 ','점',' '],['2.','(10,0 ',')'])
around(p,'16,0,0',['중첩 원리에 따라 전체 전위는 식 ','과 ','의 합이다 '],['(1)','(2)'])
around(p,'21,10,2',['를 식 ','로 소거한 뒤 식 ','에 대입하면 '],['(4)','(3)'])
around(p,'26,11,0',['식 ','를 영과 같게 놓으면 다음과 같이 쓸 수 있다 '],['(5)'])
around(p,'31,0,0',['식 ','을 제곱하면 다음 방정식을 얻는다 '],['(7)'])
around(p,'32,5,0',['식 ','은 모든 '],['(8)'])
around(p,'33,16,0',['식 ','와 ','을 연립하여 풀면 두 해를 얻는다 '],['(9)','(10)'])
around(p,'39,9,0',['자명하지 않은 해는 식 ','이므로, 최종적으로 '],['(12)'])
finish(p,[[1,0],[8,0],[9,0]],'Full original2019 sourcepage3 read at144dpi. Preserve continuation grading table, original italic Without justification centered in its content cell, every original grade including parenthesized0,5 and source3,0 subtotal; complete native L=1/(omega2 C), L=10^-2 Hn,R=r,Pmax=U2/(8r),Pmax=14mW run-ins pack with labels with all rules/fonts/points unchanged. Preserve14.04pt Problem2 title and12pt subsection center. All sixteen displayed electrostatic equations1–16, original variable definitions, native arrow/script conventions, signs and integral/radical/fraction primitives stay native and stationary. Source prose physical rows and original bold enumerators2.1–2.5 retained. Page ends in definition of WQ continuing onto originalpage4; original Wq/WQ/q scripts must pack as complete CID expressions without English-word-width gaps. Native source math is never retyped or fitted.')
