from izho2012_authoring import begin,around,finish
p=begin(11)
p.add('0,3,0','이로부터 ')
around(p,'4,0,0',['채점 기준: 문제 ',''],['3'])
p.add('5,2,0','배점 ',align='center')
formula_refs={
 '5,5,0':'(1)','5,9,0':'(1)','5,12,0':'(1)','5,15,0':'(1)','5,19,0':'(6)','5,23,0':'(7)',
 '6,5,0':'(8)','6,15,0':'(9)','6,19,0':'(10)','6,22,0':'(11)','6,29,0':'(12)',
 '8,1,0':'(13)','9,2,0':'(15)','9,6,0':'(16)','9,10,0':'(17)',
 '12,1,0':'(18)','12,4,0':'(19)','12,7,0':'(20)','12,10,0':'(21)'}
for at,ref in formula_refs.items():around(p,at,['식 ',' '],[ref])
for at in['5,26,0','6,9,0','6,25,0','12,13,0']:p.add(at,'수치 ')
around(p,'8,4,0',['그래프 ','축 기호 표기 '],['X'])
around(p,'8,7,0',['그래프 ','축 기호 표기 '],['Y'])
around(p,'8,10,0',['그래프 ','의 범위 ','부터','까지 '],['k','0','1'])
p.add('8,13,0','그래프의 올바른 수치 ')
around(p,'8,17,0',['올바른 ','값 '],['k'])
p.add('8,21,0','올바른 값 ')
p.add('13,1,0','합계 ')
finish(p,[[4,0]],'Full original page11 viewed at144dpi. Preserve exact native final equation21, original source crtitcal subscript spelling, full grading grid/merged blank separator rows, all source decimal-point score values, repeated source Formula(1) labels, native X/Y/k/0/1, original source Times mathematical scripts and complete parenthetical references. Gray source fields, exact original14.04pt centered heading and12pt table/Total faux-bold paint remain. Only explicit English language is translated; no mathematical glyph/size is retyped or fitted.')
