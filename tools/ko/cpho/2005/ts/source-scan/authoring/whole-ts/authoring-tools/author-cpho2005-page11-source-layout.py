"""Explicit source-native annular-disk resistance and power solution page."""
from cpho2005_manual_seed_tools import generate
rows=[];samples=[];geometry={}
def row(id,hint,ko,en,sample,window,left,erase):
 rows.append(dict(id=id,source_ocr_hint=hint,ko=ko,en=en));geometry[id]=(left,erase)
 samples.append(dict(id=id,source_region='left'if window[0]<420 else'right',source_text=sample,source_measurement_window=window))
row('resistance-heading',1,'[[roman-ii]] 고리 원판의 저항 계산','[[roman-ii]] Resistance of the annular disk','环形圆盘',[118,59,170,76],92,[90,58,232,76])
row('radial-current',3,'반지름 방향 전류이므로 원판을 좁은 고리들로 나누자.','Radial current: divide the disk into many narrow rings.','因环形圆',[91,77,142,94],92,[89,76.5,404,94])
row('ring-radii',6,'반지름은 [[radii]]이며 [[ring-j]]번째','Radii: [[radii]]. Ring [[ring-j]] has','不同半径',[65,95,116,114],66,[63,94,405,114])
row('ring-width',7,'폭은 [[delta-r]]이며 저항은','width [[delta-r]], and resistance','其电阻为',[215,114,269,133],65,[62,111.5,271,133])
row('series-resistance',14,'전체 저항 [[disk-R]]은 각 고리 저항의 직렬 합이다. 즉','Rings are in series; disk resistance [[disk-R]] is','整个圆盘',[65,166,117,184],66,[64,165,338,184])
row('no-load-heading',23,'[[roman-iii]] 무부하 정상 각속도','[[roman-iii]] No-load steady angular velocity','空载达到',[118,217,170,234],91,[89,215.5,258,234])
row('no-load-first',25,'무부하 정상 상태에서 원판 전류는 [[i-zero]]이고,','No-load steady state: disk current [[i-zero]],','当电动机',[91,236,143,253],92,[89,234.5,403,253])
row('no-load-second',26,'각속도는 [[omega0]]이다. 식 [[no-load-eq2]]에서 원판의 유도 기전력은','angular velocity [[omega0]]. By [[no-load-eq2]], the disk’s induced emf is','盘的转动',[64,253,117,272],65,[63,252,360,272])
row('shunt-current',33,'정전류원 전류 [[I-source]]는 모두 [[R0]]로 흐르므로 식 [[shunt-eq1]]에서','All source current [[I-source]] flows in [[R0]]; [[shunt-eq1]] gives','而恒流源',[65,300,117,318],66,[64,298,320,318])
row('no-load-result',39,'식 [[eq4-5]]에서 무부하 정상 각속도는','From [[eq4-5]], the no-load steady angular velocity is','电动机在',[148,347,201,365],65,[62,345.5,342,365])
row('maximum-power-heading',45,'[[roman-iv]] 최대 기계적 출력 계산','[[roman-iv]] Maximum mechanical output power','输出最大',[117,403,170,420],90,[88,401,273,420])
row('loaded-first',47,'부하가 있을 때 각속도를 [[omega-loaded]], 원판 전류를','Mechanical load: angular velocity [[omega-loaded]], disk current','当有机械',[90,421,143,438],91,[88,419.5,409,439])
row('loaded-second',48,'[[current-i]]라 하면 식 [[loaded-eq1]], [[loaded-eq2]]에서','[[current-i]]. By [[loaded-eq1]] and [[loaded-eq2]],','式可得',[198,440,238,458],65,[62,439,240,458])
row('ring-power',58,'[[j-power]]번째 고리에 작용하는 자기력의 일률은','Magnetic power on ring [[j-power]] is','小圆环所',[124,496,178,512],90,[87,494,272,513])
row('total-power',2,'원판 전체에 작용하는 자기력의 일률은','Total magnetic power on the disk is','整个圆环',[439,64,491,81],440,[438,63,580,81])
row('steady-first',8,'정상 회전 상태에서 기계적 출력은 자기력의 일률이다.','Steady rotation: mechanical output equals','当电动机',[467,113,518,131],468,[466,111,784,131])
row('steady-second',10,'식 [[steady-eq7]]을 [[steady-eq9]]에 대입하면','magnetic power. Substitute [[steady-eq7]] into [[steady-eq9]]:','是磁力的',[438,134,491,151],439,[437,131.5,650,151])
row('coefficients',15,'여기서','where','其中',[438,172,466,190],439,[435,169,468,190])
row('eq10',24,'식 [[eq10]]을 다시 쓰면','Rewrite [[eq10]] as','式可改写',[464,227,517,244],440,[438,226,533,244])
row('maximum-condition',None,'다음 조건에서','When','当',[439,290,453,307],440,[438,289,455,308])
row('maximum-result',37,'기계적 출력 [[power-P]]가 최대이다. 식 [[power-eq11]], [[power-eq6]]에서','The output [[power-P]] is maximal. [[power-eq11]], [[power-eq6]] give','输出的机',[458,315,512,333],440,[438,313,715,333])
row('maximum-current-first',42,'[[part-two]] 최대 기계적 출력에서 원판의 각속도는','[[part-two]] At maximum output, disk angular velocity is','当电动机',[476,365,529,382],465,[462,363,784,379.12])
row('maximum-current-second',None,'[[omega-half]]이다. 원판 전류를 [[i-prime]]라 하면 식 [[current-eq1]], [[current-eq2]],','[[omega-half]]. Let disk current be [[i-prime]]. By [[current-eq1]], [[current-eq2]],','环形圆盘',[553,397,608,416],440,[438,389,784,415])
row('maximum-current-third',46,'[[current-eq6]]에서','[[current-eq6]],','式得',[459,416,488,435],440,[437,415,490,435])
row('joule-heating',55,'원판 저항에서 소모되는 열 일률은','The disk’s resistive heating power is','圆盘的电',[439,469,491,486],440,[437,466,582,486])
protected=[[128,133.5,336,165],[89,185,405,215],[150,273,404,297.5],[189,319,405,334.35],[176,366,405,400],[153,459,409,493],[164,513,409,534.146],[437,82,783,111],[550,151.5,783,170],[461,190.5,783,224],[526,244.5,783,278.5],[565,279.5,783,313],[566,333.5,783,363],[565,436,783,465.5],[538,486.5,783,520.121]]
specs=[]
def atom(id,rect,path):specs.append(dict(id=id,search_rect=rect,image_path=[path],center_hint=None))
for id,rect in {'roman-ii':[90,57,116,77],'radii':[117,93,299,115],'ring-j':[366,94,377,115],'delta-r':[128,111,212,134],'disk-R':[155,164,170,185],'roman-iii':[89,215,116,235],'i-zero':[325,233,359,254],'omega0':[165,251,184,273],'no-load-eq2':[200,251,220,273],'I-source':[153,297,165,319],'R0':[239,297,257,319],'shunt-eq1':[272,297,293,319]}.items():atom(id,rect,273)
for id,rect in {'eq4-5':[74,344,120,366],'roman-iv':[87,400,115,421],'omega-loaded':[286,418,301,440],'current-i':[90,438,101,459],'loaded-eq1':[127,438,151,459],'loaded-eq2':[175,438,197,459],'j-power':[102,493,115,514]}.items():atom(id,rect,282)
for id,rect in {'steady-eq7':[534,131,557,153],'steady-eq9':[594,131,617,153],'eq10':[437,225,465,245],'power-P':[548,312,563,334],'power-eq11':[609,312,639,334],'power-eq6':[663,312,686,334],'part-two':[462,362,477,382]}.items():atom(id,rect,291)
for id,rect in {'omega-half':[438,389,487,417],'i-prime':[658,391,673,417],'current-eq1':[691,391,716,417],'current-eq2':[735,391,758,417],'current-eq6':[437,414,462,436]}.items():atom(id,rect,300)
refinements={'delta-r':[128,116.125,209.5,133],'disk-R':[155,164,166.5,185],
 'i-zero':[325,233,357,254],'omega0':[165,251,182,273],
 'R0':[239,297,255,319],'current-i':[90,438,98.5,459],
 'loaded-eq1':[129.5,438,151,459],'loaded-eq2':[177.5,438,197,459],
 'j-power':[102,493,112,514],'steady-eq7':[533,131,553,153],
 'steady-eq9':[593,131,612.5,153],'omega-half':[438,389,483,417],
 'current-eq1':[691,391,711,417],'current-eq2':[733.5,391,753,417],
 'current-eq6':[437,414,459,436]}
for spec in specs:
 if spec['id']in refinements:spec['search_rect']=refinements[spec['id']]
gaps={}
for r in rows:
 ids=__import__('re').findall(r'\[\[([^\]]+)\]\]',r['ko'])
 if ids:gaps[r['id']]={id:.75 for id in ids}
generate(11,rows,samples,geometry,protected,specs,ko_math_gaps=gaps)
