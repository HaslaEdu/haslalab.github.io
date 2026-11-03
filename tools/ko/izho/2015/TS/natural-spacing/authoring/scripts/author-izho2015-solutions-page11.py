from izho2015_authoring import begin,around,finish
p=begin(11)
for at,text in{
 '1,2,0':'정확한 ',
 '1,7,0':'힘의 상수항을 구함 ',
 '9,1,0':'힘의 다음 성분을 구함 ',
 '25,0,0':'위 식에 음의 부호가 없을 때 ',
 '42,1,0':'원판의 에너지 손실을 구함 ',
 '42,4,0':'마찰력의 일률을 구함 ',
 '42,6,0':'두 값이 같음 ',
 '42,8,0':'합계 ',
}.items():p.add(at,text)
around(p,'1,0,0',['조건 ',''],['z'])
around(p,'1,0,2',['','에서 단순화 '],['R'])
around(p,'1,4,0',['정확한 ',' '],['α'])
finish(p,[],'Full original2015 page11 read at144dpi: complete final grading table. Preserve original page-number11/11 wrapping to the left of the second header line, all original mathematical source programs, source z>>R text even where source physics might suggest another condition, exact fractional Times/Cambria script points, every original vector/fraction/radical/integral stroke, table geometry, subsection numbers, all0.25/0.5/0.75/1/1.5/2 subtotal values and original16 total. Only grading prose is translated; no score, mathematical expression, type-size or diagram redesign.')
