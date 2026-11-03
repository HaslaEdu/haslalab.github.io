import sys
sys.path.insert(0,'C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions')
from izho2019_ts_authoring import begin,around,finish
p=begin(7)
ats=['1,0,0','3,0,0','5,0,0','8,0,0','9,0,0','12,0,0','15,0,0','18,0,0','23,0,0','26,0,0','26,2,0','29,0,0','32,0,0','35,0,0','38,0,0','41,1,0']
for number,at in enumerate(ats,32):around(p,at,['식 ',' '],[f'({number})'])
for at,text in{
 '41,6,0':'합계 ',
 '41,12,0':'분포 반전: 2준위계 ',
 '41,13,1':'오른쪽 그림은 가능한 전이와 그 확률을 나타낸다. ',
 '41,14,0':'들뜬 상태의 점유율이 ',
 '41,15,2':'이면, ',
 '42,0,0':'바닥 상태의 점유율은 ',
 '42,5,0':'이다. 분자는 두 상태 중 ',
 '43,0,0':'하나에만 있을 수 있기 때문이다. ',
 '44,0,0':'점유율의 변화를 나타내는 수지 방정식은 그림에서 곧바로 ',
 '44,1,0':'다음과 같이 얻는다 ',
 '46,0,1':'정상 상태에서는 ',
 '46,6,0':'들뜬 상태의 점유율은 다음과 같다 ',
 '50,0,0':'따라서 들뜬 상태와 바닥 상태 사이의 점유율 차이는 다음과 같다 ',
 '54,0,1':'펌프광의 세기를 무한히 크게 하더라도 2준위계에서는 ',
 '54,1,0':'분포 반전을 만들 수 없다. 따라서 이 계에서는 레이저 빛을 ',
 '54,2,0':'증폭할 수 없다. ',
}.items():p.add(at,text)
around(p,'41,4,0',['올바른 답 없이 식 ','을 형식적으로 적분함 '],['(40)'])
around(p,'41,11,0',['문제 ',' 레이저 ','점',' '],['3.','(10.0 ',')'])
around(p,'46,5,0',['이므로, 식 ','에서 '],['(1)'])
finish(p,[[41,11],[41,12]],'Full original2019 sourcepage7 read at144dpi. Original Problem2 continuation rubric Formula32–47 and formal-integral criterion fully translated; native original reference+complete formula row clips preserve all fraction/root/arrow/dot programs and exact grades/columns/subtotal10,0. Keep literal source rubric equation45 as printed, including its difference from the narrative formula; do not correct math. Original14.04pt Problem3 title and12pt two-level subsection center retained. Narrow right-figure prose column beside unchanged original transition diagram, native n1 and(1-n1) inline MathType objects and full stationary dn1/dt=0 bind as complete original programs including scripts and bars. Source diagrams remain original byte/geometry, and all laser displays1–3 retain exact fractional MathType fonts/Tf/Tm/points/Y/paint. Every source population/pumping/amplification paragraph translated with natural Korean gaps; no fitting or math retyping.')
