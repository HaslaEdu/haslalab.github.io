from izho2012_authoring import begin,around,finish
p=begin(8)
around(p,'3,0,0',['채점 기준: 문제 ',' '],['2'])
p.add('4,2,0','배점 ',align='center')
formula_refs={
 '4,5,0':'(1)','5,1,0':'(2)','5,7,0':'(3)','5,10,0':'(4)','5,16,0':'(7)',
 '6,1,0':'(8)','8,1,0':'(9)','10,1,0':'(10)','12,1,0':'(11)',
 '14,1,0':'(12)','14,7,0':'(13)','14,10,0':'(14)','14,13,0':'(15)','14,16,0':'(16)','14,32,0':'(17)',
 '15,1,0':'(19)','16,1,0':'(20)','16,4,0':'(21)','17,1,0':'(22)','17,16,0':'(24)'}
for at,ref in formula_refs.items():around(p,at,['식 ',' '],[ref])
around(p,'5,13,0',['식 ',' 및 ',' '],['(5)','(6)'])
for at,ref in{'14,22,0':'(18)','14,27,0':'(18)','16,7,0':'(23)','16,10,0':'(23)','17,7,0':'(25)','17,12,0':'(25)'}.items():around(p,at,['식 ','의 '],[ref])
for at in['4,9,0','5,19,0','7,1,0','9,1,0','11,1,0','13,1,0','14,19,0','14,35,0','17,4,0','17,19,0']:p.add(at,'수치 ')
p.add('17,22,0','합계 ')
finish(p,[[3,0]],'Full original page8 viewed at144dpi. Preserve the complete original centered narrow grading table, merged cells, all11.04pt body rows,14.04pt centered heading, exact decimal-comma score values, native source equation25 and all table variable/subscript/Greek glyphs. Only the exact English Formula/for/and/Numerical value/Total/points text is translated; complete original reference parentheses/numerals pack with the Korean labels using unchanged encoded source fonts/points/baselines. The original final u label is retained exactly. No font fitting.')
