from pathlib import Path
script=Path('D:/CodexBuilds/propose-cpho2005-page06-native-math.py').read_text('utf8')
start=script.index('specs=[]');end=script.index('S=8;out=[]',start)
spec='''specs=[]
def add(id,rect,path,center=None):specs.append(dict(id=id,search_rect=rect,image_path=[path],center_hint=center))
for id,rect,c in [('A-final',[106,100,120,120],113),('B-final',[121,100,136,120],128),('B-state',[275,100,291,120],283),('P-plate',[185,302,200,322],193),('F-external',[247,302,263,322],255),('C-right',[326,302,342,322],335),('D-right',[342,302,358,322],350),('A-spring',[132,322,147,342],140),('B-spring',[155,322,171,342],163),('C-figure',[264,322,280,342],273),('A-contact',[259,339,274,360],267),('P-contact',[276,339,291,360],284),('Q-contact',[290,339,305,360],297),('N-contact',[302,339,318,360],310),('C-contact',[328,339,344,360],336),('N-friction',[187,358,202,377.25],195),('P-friction',[202,358,218,377.25],210),('Q-friction',[226,358,242,377.25],234),('C-friction',[276,358,292,377.25],284)]:add(id,rect,287,c)
for id,rect in {'eq7-12':[80,171,144,190],'eq6':[81,233,100,252],'eq13':[106,233,131,252],'eq1':[170,233,190,252],'fig1a':[363,322,391,342],'FA':[116,339,136,360],'FP':[138,339,158,360],'FQ':[160,339,180,360],'FN':[191,339,211,360],'fN':[88,358,106,377.25],'fP':[105,358,123,377.25],'fQ':[122,358,141,377.25]}.items():add(id,rect,287)
for id,rect in {'dx1':[179,388,205,409],'dx2':[215,388,242,409]}.items():add(id,rect,296)
for id,rect,c in [('A-extra',[365,388,381,409],373),('B-extra',[390,388,407,409],399)]:add(id,rect,296,c)
add('figure-one',[615,219,626,238],305)
for id,rect,c in [('P-mass',[527,237,542,256],535),('Q-mass',[541,237,556,256],549),('C-mass',[555,237,570,256],563),('D-mass',[570,237,585,256],577),('A-mass',[585,237,600,256],593),('B-mass',[600,237,615,256],608),('C-zero',[635,257,651,276],643)]:add(id,rect,305,c)
add('seven',[661,257,676,276],305)
add('fig1b',[569,458,598,478],323)
'''
script=script[:start]+spec+script[end:]
start=script.index('for spec in specs:\n if spec');end=script.index('boxes=',start)
script=script[:start]+script[end:]
script=script.replace('page06','page07').replace('original.pdf\',6)','original.pdf\',7)').replace('page=d[5]','page=d[6]').replace('page=6','page=7')
out=Path('D:/CodexBuilds/propose-cpho2005-page07-native-math.py');out.write_text(script,'utf8');print('CREATED_EXPLICIT_SOURCE_MATH_WINDOW_PROPOSER',out)
