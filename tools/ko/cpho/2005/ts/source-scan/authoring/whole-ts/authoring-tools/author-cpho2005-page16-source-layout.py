"""Final original left-column-only solution page, with original period formula."""
from cpho2005_manual_seed_tools import generate
rows=[];samples=[];geometry={};specs=[]
def row(id,hint,ko,en,text,window,left,erase):
 rows.append(dict(id=id,source_ocr_hint=hint,ko=ko,en=en));geometry[id]=(left,erase)
 samples.append(dict(id=id,source_region='left',source_text=text,source_measurement_window=window))
def atom(id,rect,path):specs.append(dict(id=id,search_rect=rect,image_path=[path],center_hint=None))
row('negative-coefficient',5,'[[wide-condition]]이므로 [[negative-term]]는 음수이다. 따라서 위 식은','For [[wide-condition]], [[negative-term]] is negative, so the field becomes','是负的',[199,101,235,121],70,[68.5,99,330,127])
row('electric-force',7,'원점 근처의 입자에 작용하는 전기력은','The electric force on a particle near the origin is','位于原点',[68,166,120,185],71,[69,167,257,185])
row('restoring-first',11,'선형 복원력에 의해 입자는 원점을 중심으로 단진동한다.','The particle moves harmonically about the origin under','它具有弹',[69,220,119,241],72,[70,222,405,241])
row('restoring-second',12,'진동 주기는','this linear restoring force, with period','振动的周',[68,241,120,260],71,[68.5,242,135,257.47])
row('narrow-first',17,'[[case-ii]] [[narrow-condition]]로 두 고리가 가까우면 전위 [[potential-V]]의','[[case-ii]] For closer rings, [[narrow-condition]], potential [[potential-V]] has','即两个圆',[188,309,241,329],90,[87,303,406,334])
row('narrow-second',18,'곡선에는 [[peak-zero1]]에서 봉우리 하나만 있다. 위치 에너지 [[potential-W]]도','one peak at [[peak-zero1]], as does the potential energy [[potential-W]].','的图线只',[59,334,112,354],62,[60,335,406,354])
row('narrow-third',19,'[[peak-zero2]]에서 봉우리 하나만 있다. 그림 [[figure4]]의 [[curve-II1]]과 같다. 입자는 원점에서','It peaks at [[peak-zero2]], as in [[curve-II1]] of Fig. [[figure4]]. At the origin,','亦只有一',[59,353,112,373],62,[59.5,354,406,373])
row('escape-first',20,'위치 에너지가 최대이므로 불안정 평형이다. 처음에 입자가 그곳에','potential energy is maximal, so equilibrium is unstable. Even','时其电势',[59,372,112,392],62,[59.5,374,406,392])
row('escape-second',21,'정지해 있어도 아주 작은 속도를 얻으면 원점에서 멀어져 위치','if initially at rest, any small velocity lets it escape to infinity,','时静止在',[59,391,112,411],62,[59.5,393,405,411])
row('escape-third',22,'에너지가 영인 무한히 먼 곳으로 간다.','where its potential energy is zero.','势能为零',[59,410,112,427],62,[60,412,182,427.42])
for id,rect in {'wide-condition':[82,99,135,128],'negative-term':[140,102,197,120]}.items():atom(id,rect,708)
for id,rect in {'case-ii':[85,309,114,328],'narrow-condition':[130,302,184,335],'potential-V':[375,311,405,329],'peak-zero1':[178,336,209,354],'potential-W':[332,336,364,355],'peak-zero2':[151,355,183,373],'figure4':[239,355,249,373],'curve-II1':[300,355,319,374]}.items():atom(id,rect,717)
protected=[[166,58.72,303,97],[163,130,310,165],[135,177,338,221.5],[149,263.17,406,305.5]]
protected.remove([135,177,338,221.5])
protected.extend([[135,185.5,265,221.5],[265,177,338,221.5]])
gaps={r['id']:{v:.75 for v in __import__('re').findall(r'\[\[([^\]]+)\]\]',r['ko'])}for r in rows}
translations={
 'narrow-third':('[[peak-zero2]]의 봉우리 하나이다. 그림 [[figure4]]의 [[curve-II1]]과 같다. 원점에서',None),
 'escape-first':('위치 에너지가 최대이므로 불안정 평형이다. 처음에 입자가','potential energy is maximal, so equilibrium is unstable.'),
 'escape-second':(None,'Even initially at rest, a tiny velocity makes it leave'),
 'escape-third':(None,'for infinity, where its potential energy is zero.')}
for r in rows:
 if r['id']in translations:
  for lang,value in zip(['ko','en'],translations[r['id']]):
   if value is not None:r[lang]=value
generate(16,rows,samples,geometry,protected,specs,ko_math_gaps=gaps)
