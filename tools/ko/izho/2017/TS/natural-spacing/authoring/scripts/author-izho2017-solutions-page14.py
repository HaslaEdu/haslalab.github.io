from izho2017_authoring import begin,around,finish
p=begin(14)
p.add('6,0,0','등가 회로: ')
p.add('9,1,0','등가 회로: ')
for at,n in [('12,0,0',29),('13,9,0',30),('15,0,0',31),('33,0,0',32)]:around(p,at,['식 ',' '],[f'({n})'])
around(p,'20,0,0',['표 ','의 올바른 수치 '],['3'])
around(p,'21,0,0',['표 ',' '],['3.'])
p.add('33,6,0','합계 ')
finish(p,[[21,0]],'Full original2017 page14 scoring-table continuation read at144dpi. Original serif12pt roles retained. Both original N=1/N=2 circuit diagrams, all nested numeric tables, section/grade/subtotal columns, double border and original total stay fixed. The full native infinity/sqrt3, resistance ratio, original negative numerical errors and source infinity≈4 convention remain literal original glyphs at original mathematical fractional points. Complete same-cell inline objects move rigidly only with translated labels. No formula rasterization, font shrink or new explanatory notes.')
