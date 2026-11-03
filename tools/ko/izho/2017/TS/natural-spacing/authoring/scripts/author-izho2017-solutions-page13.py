from izho2017_authoring import begin,around,finish
p=begin(13)
for at,n in [('2,0,0',10),('4,0,0',11),('5,0,0',12),('25,0,0',14),('32,1,0',16),('39,0,0',17),('40,1,0',18),('40,11,0',19),('41,1,0',20),('49,11,0',21),('50,1,0',22),('50,10,0',23),('51,1,0',24),('60,0,0',25),('63,5,0',26),('68,0,0',27),('68,9,0',28)]:around(p,at,['식 ',' '],[f'({n})'])
around(p,'12,0,0',['해 ',' '],['(13)'])
p.add('37,0,0','등가 회로 ')
around(p,'74,0,0',['표 ','의 올바른 수치 '],['2'])
around(p,'75,0,0',['표 ','. 각기둥의 저항 '],['2'])
finish(p,[[75,0]],'Full original2017 page13 scoring-table continuation read at144dpi. Original12pt Times prose roles retained. Complete original native two-line systems, tall original braces/Forms, fractions/rules, scripts and source numeric nested table remain unchanged. Same-cell translated labels pack next to whole expressions, including multi-line13, with one dx. Keep all true left section, right grade/subtotal columns and native circuit/arrow diagram positions fixed. Nested Table2 caption remains source-centered. No English-width spacing, point scaling or recreated math.')
