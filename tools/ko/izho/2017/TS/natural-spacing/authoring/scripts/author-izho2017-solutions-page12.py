from izho2017_authoring import begin,around,finish
p=begin(12)
for at,text in {
 '14,0,2':'수치로 계산하면 ',
 '19,0,0':'이제 앞의 표에 제시한 여러 경우에 대해 근삿값의 상대 오차를 계산한다. ',
 '19,1,0':'다음 매개변수 ',
 '31,1,0':'이미 ',
 '31,6,0':'무한과 같다! ',
 '31,19,0':'평가 항목 ',
 '31,20,0':'배점 ',
 '60,0,0':'올바른 초기값 ',
}.items():p.add(at,text)
around(p,'14,0,1',['','점',' '],['[1.5 ',']'])
around(p,'19,1,2',['의 값은 표 ','에 제시되어 있다. '],['2'])
around(p,'20,0,0',['표 ',' '],['3.'])
around(p,'31,5,0',['일 때 상대 오차는 ','이다. 따라서 이 문제에서는 넷이 '],['1%'])
for at,n in [('31,23,0',1),('34,0,0',3),('46,1,0',5),('66,1,0',7)]:around(p,at,['식 ',' '],[f'({n})'])
around(p,'62,0,0',['표 ','의 올바른 수치 '],['1'])
around(p,'63,0,0',['표 ',' '],['1.'])
for slot in p.slots:
 if slot['at']in[[31,19,0],[31,20,0]]:slot['align']='center'
finish(p,[[20,0],[63,0]],'Full original2017 page12 visually read at144dpi. Retain source12pt serif ordinary/bold roles and centered Table3/Table1 captions. Both numeric tables, error signs, original limit/ratio expressions and display labels30–32 remain native. In the scoring table, original1.1/1.2/1.3/1.4 merged cells, right scores/subtotals and nested numeric table remain fixed. Complete two-line recurrence formula groups must move rigidly only with their same-cell translated labels; no detached scripts/rules, retyped mathematics or resized points.')
