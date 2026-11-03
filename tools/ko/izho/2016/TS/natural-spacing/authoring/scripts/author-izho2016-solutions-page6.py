from izho2016_authoring import begin,around,score,finish
p=begin(6)
for at,text in{
 '1,1,0':'일차함수의 식은 다음과 같다 ',
 '7,0,0':'축전기의 전하량이 ','7,1,0':'과 식 ',
 '10,9,2':'시간 간격 ','10,9,4':'는 전하량이 ',
 '10,10,0':'에서 ',
 '10,10,2':'까지 증가하는 데 걸리는 시간으로, 다음과 같다 ',
 '17,11,0':'처음에는 ','17,11,2':'이므로, ',
 '20,10,2':'보통의 축전기는 전하량이 양단 전압에 비례한다. 즉, ',
 '20,24,0':'회로에 흐르는 전류는 다음과 같다 ',
 '26,9,0':'축전기와 저항은 직렬로 연결되어 있어 같은 전류가 흐른다. 따라서 저항 양단의 ',
 '26,10,0':'전압 진동은 전류 진동과 위상이 같다. ',
 '27,0,0':'여기에 ','27,0,2':'를 대입하면 ',
 '29,1,0':'즉, 축전기 양단 전압과 저항 양단 전압의 진동 사이 위상차는 ',
 '29,2,0':'다음과 같다 ',
 '31,2,0':'그대로 유지된다. 전압의 진동 폭이 전원에서 공급되는 일정한 전압에 비해 ',
 '31,3,0':'작기 때문이다. 즉, ',
 '33,11,2':'전압은 직류 성분과 교류 성분을 갖는다. 오랜 시간이 지나면 ',
 '33,12,0':'직류 전압은 축전기에만 걸린다. 즉, ',
 '33,25,0':'저항 양단 전압의 직류 성분은 영이 된다. 즉, ',
}.items():p.add(at,text)
around(p,'7,0,2',['가 될 때까지 걸리는 시간은 식 ',''],['(7)'])
around(p,'7,1,0',['과 식 ','에서 다음과 같이 얻는다 '],['(8)']) if False else None
# The reference(8) belongs to this same source run; preserve its encoded glyphs.
p.slots=[s for s in p.slots if s['at']!=[7,1,0]]
around(p,'7,1,0',['과 식 ','에서 다음과 같이 얻는다 '],['(8)'])
around(p,'14,0,2',['식 ','을 풀면 '],['(11)'])
around(p,'17,12,0',['식 ','에서 양의 부호를 택해야 한다. 최종적으로 '],['(13)'])
around(p,'31,1,0',['회로에는 비선형 축전기가 있지만 식 ','의 비례 관계는 '],['(16)'])
for at in ['10,9,1','14,0,1','20,10,1','33,11,1']:score(p,at)
finish(p,[],'Full original2016 page6 read at144dpi. Keep the entire original f(q) graph and its axis text/units, source graph grid and native raster/vector geometry. Display labels8–18 are exact native original12pt TNR glyphs. Keep original Cambria Math functions/units including Cyrillic microcoulomb text in q=4 source, source decimal punctuation, every source root/fraction and script. Inline q=4, q0=4, q=8 and q(0)=0 should pack naturally with prose; original Delta t must remain in the translated time-interval statement. Source inline phase expressions including both pi/2 fraction bars must move as complete original native groups; source sign and trigonometric notation preserved verbatim. No math retyping or changed point size.')
