import sys
sys.path.insert(0,'C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions')
from izho2019_ts_authoring import begin,around,finish
p=begin(12)
for at,text in{'6,0,0':'수치: ','9,0,0':'수치: ','13,0,0':'도함수가 영이 됨 ','36,0,0':'수치: ','36,15,0':'그래프: 축의 물리량과 눈금을 표시함 ','36,17,0':'그래프: 직선으로 그림 ','36,19,0':'그래프: 직선이 ','41,0,0':'총점 '}.items():
 if at!='36,19,0':p.add(at,text)
around(p,'36,19,0',['그래프: 직선이 ','을 지남 '],['1'])
for at,num in [('1,0,0',22),('7,0,0',23),('8,0,0',24),('15,0,0',25),('16,0,0',26),('25,0,0',27),('27,0,0',28),('34,0,0',30),('38,0,0',31),('39,1,0',32),('40,0,0',34)]:around(p,at,['식 ',' '],[f'({num})'])
finish(p,[],'Full original2019 sourcepage12 read at144dpi. Every final laser grading criterion, Formula22–34, numeric-value labels and three graph criteria translated. Source original graph straight line passes through literal1; preserve native digit and add Korean predicate after it. Preserve every exact original native counter/reference/score12pt TNR, MathType/CambriaMath fraction/overbar/epsilon/sigma/eta/subscript/rule/form/clip at original point/paint/Y. Complete same-cell native reference+formula outer clips move together for natural Korean spacing; merged Part3.13/3.14 rows, genuine score/boldsubtotal columns, all original grid lines and Total centered source role stay fixed. No math retyping, rasterization, fitting or guard changes.')
