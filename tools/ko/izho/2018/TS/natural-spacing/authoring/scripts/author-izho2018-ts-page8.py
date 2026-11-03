import sys
sys.path.insert(0,'C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions/engine')
from izho2018_ts_authoring import *
p=begin(8);point_labels(p)
for at in['2,0,0','6,0,0','8,0,0','13,0,0','17,1,0','22,0,0','24,1,0','27,1,0','31,0,0','32,1,0','36,1,0','40,0,0','42,0,0','44,3,0','45,0,0','51,0,0','54,0,0','63,0,0','64,1,0']:formula(p,at)
for at in['16,0,0','20,4,0','26,0,0','29,3,0','35,0,0','38,3,0','61,0,0','70,0,0']:p.add(at,'올바른 수치 ')
p.add('70,2,0','합계')
around(p,'70,7,0',['문제 ',' 움직이는 매질의 광학 (','점',''],['3.','10.0',')'])
around(p,'71,0,0',['제','부. ','차원 벡터 (','점',''],['1','4','1,4',')'])
p.add('71,1,2','운동량과 에너지의 단위를 같게 하려면 에너지를 빛의 속력으로 나누거나 ')
p.add('71,2,0','운동량에 빛의 속력을 곱하면 된다. 또한 상대성 원리에 따라 ')
p.add('71,3,0','다음 치환을 해야 한다 ');p.add('71,3,2','. 따라서 ')
finish(p,[[70,7,0],[71,0,0]],'Full original page8 read: every adiabatic grading-table row2.1–2.8, native source formulas12–35 and all numerical/total grades. Source table uses phi_max while body previously used phi_min; original mathematical notation is retained literally. Problem3 moving-media optics title and complete start of four-vector1.1 translated, original V->-V and first Lorentz formula preserved.')
