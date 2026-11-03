import sys
sys.path.insert(0,'C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions/engine')
from izho2018_ts_authoring import *
p=begin(2)
p.add('1,17,0','시험관과 올라가는 물의 전체 운동 에너지는 다음과 같다 ')
around(p,'6,0,0',['',' 이 계의 에너지 보존 법칙은 '],['А2.3'])
p.add('6,1,0','다음과 같이 쓸 수 있다 ');p.add('14,0,0','이 방정식도 주기가 다음과 같은 조화 진동의 방정식이다 ')
for at,text in{'16,1,0':'구분','16,2,0':'평가 항목','16,3,0':'배점'}.items():p.add(at,text)
for at in['18,0,0','20,0,0','21,0,0','24,0,0','26,0,0','28,0,0','32,0,0','32,10,0','41,0,0','47,0,0','53,0,0','57,0,0','57,13,0','80,1,0']:formula(p,at)
finish(p,[[16,1,0],[16,2,0],[16,3,0]],'Full source page2 read: energy conservation, equal oscillation period and every grading-table row1–14. Original source formulas8 and13 sit on separate display lines below their labels and retain those placements; actual run-in label/formula rows pack naturally with complete original MathType programs. Grading columns and all native source part codes/scores remain exact.')
