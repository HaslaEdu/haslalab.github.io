import sys
sys.path.insert(0,'C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2019-complete-solutions')
from izho2019_ts_authoring import begin,around,finish
p=begin(11)
for at,text in{'1,3,0':'문항 ','1,4,0':'평가 항목 ','1,5,0':'배점 ','9,1,0':'답: «불가능» ','38,0,0':'수치: ','42,0,0':'수치: ','47,0,0':'도함수가 양수임을 보임; ','50,0,0':'수치: ','51,1,0':'레이저 광속의 세기: '}.items():p.add(at,text)
for at,num in [('2,1,0',1),('4,0,0',2),('6,12,0',3),('10,1,0',4),('12,0,0',5),('21,0,0',6),('28,1,0',8),('33,0,0',10),('34,1,0',11),('36,0,0',15),('40,0,0',16),('41,1,0',18),('43,1,0',19),('44,12,0',20),('48,1,0',21)]:around(p,at,['식 ',' '],[f'({num})'])
for at,num in [('25,1,0',7),('31,0,0',9)]:around(p,at,['부등식 ',' '],[f'({num})'])
around(p,'27,0,0',['식 ','를 다시 사용함 '],['(5)'])
for s in p.slots:
 if s['at']in[[1,3,0],[1,4,0],[1,5,0]]:s['align']='center'
finish(p,[],'Full original2019 sourcepage11 read at144dpi. Every grading criterion, Equation/Formula1–21 and Inequality7/9 and repeated Formula5 labels translated; keep exact original native references, complete original outer Word row clips/MathType Forms with all encoded fonts/GIDs/points/paint/Y, roots/fractions/rules/overbar/scripts. Same source cell run-in math packs with Korean labels while real distinct Part/Content/score/boldsubtotal columns, merged cells, all grid and original numeric decimal commas stay fixed. Preserve original V header9.96pt Arial bold, original score12pt TNR and title role/centers. Native reference and formula must share commonDX including every rule; no math retyping, fitting or threshold changes.')
