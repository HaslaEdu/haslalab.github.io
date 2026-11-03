"""Human-authored ring-potential prose; both original graphs remain native."""
from pathlib import Path
import json,re
from cpho2005_manual_seed_tools import generate
rows=[];samples=[];geometry={}
def row(id,hint,ko,en,sample,window,left,erase):
 rows.append(dict(id=id,source_ocr_hint=hint,ko=ko,en=en));geometry[id]=(left,erase)
 samples.append(dict(id=id,source_region='left'if window[0]<420 else'right',source_text=sample,source_measurement_window=window))
row('motor-result',1,'식 [[eq3]]을 [[eq16]]에 대입하면','Substitute [[eq3]] into [[eq16]]:','式代入',[96,58,136,75],64,[62,56.5,189,75])
row('section-seven',7,'7.','7.','七、',[87,109,109,127],88,[85,108,110,128])
samples[-1]['source_size_range']=[9,14.751,.025]
row('particle-first',9,'[[part-one]] 정전기력만 받는 대전 입자의 역학적 에너지는 보존된다.','[[part-one]] Electrostatic force alone acts; energy is conserved.','带电粒子',[101,131,151,148],88,[85,128,399,148])
row('particle-second',11,'운동·위치 에너지의 합은 일정하다. 정전기적 위치 에너지는','Kinetic and electric potential energies have a constant sum.','的动能与',[63,149,114,167],64,[61,146.5,399,167])
row('particle-third',13,'그 지점의 전위에 달려 있다. 먼저 대전 고리의 전위를 구하자.','Local potential sets potential energy. Find ring potential.','子所在处',[62,167,114,185],64,[61,165,397,185])
row('axial-first',15,'축대칭이므로 초기 속도가 [[axis-z1]]축 방향인 입자는 [[axis-z2]]축','Axial symmetry: initial motion along [[axis-z1]] stays on [[axis-z2]].','由于电场',[62,185,114,204],63,[60,182.5,399,204])
row('axial-second',17,'위에서만 움직인다. 따라서 [[axis-z3]]축 전위만 구하면 된다. 두 고리의','Thus only the potential on [[axis-z3]] is needed. For the two rings,','上运动',[62,204,99,221],63,[60,201.5,398,221])
row('axial-third',18,'전기장이 각각 만드는 [[axis-z4]]축 전위는','their individual potentials on [[axis-z4]] are','生的电场',[61,221,113,238],63,[60,219,237,238])
row('individual-first',23,'[[V1a]], [[V2a]]는 그림 [[fig1]]과 같다. [[V1b]]는 [[zD]]에서 극대,','[[V1a]], [[V2a]]: Fig. [[fig1]]. [[V1b]] peaks at [[zD]];','的图线如',[134,316,186,335],64,[62,313,402,335])
row('individual-second',24,'[[V2b]]는 [[zminusD]]에서 극대이다. 두 고리가 만드는 [[left-z]]의','[[V2b]] peaks at [[zminusD]]. Total potential at [[left-z]]','处有极大',[158,335,212,354],64,[62,332.5,403,354])
row('individual-third',25,'전위는','is','处的电势',[62,355,113,370],63,[60,352.5,114,371])
row('superposition',2,'전위 [[Vz1]]의 [[z-var]]에 따른 곡선은 [[V1-right]]와 [[V2-right]]를','Potential [[Vz1]] versus [[z-var]]: add [[V1-right]] and [[V2-right]],','的变化的',[523,63,575,80],445,[443,61.5,782,80])
row('large-separation',4,'더한 것이다. [[D-large]]가 커 두 고리가 멀면 [[Vz-large]]는','their curves. For large ring separation [[D-large]], [[Vz-large]] is','即两个圆',[550,82,602,99],445,[443,79.5,783,99])
row('two-extrema',6,'그림 [[fig2a]]의 곡선 [[curve-I]]처럼 극댓값 둘과 극솟값 하나를 갖는다.','Fig. [[fig2a]], curve [[curve-I]]: two maxima (peaks), one minimum (valley).','它有两个',[563,100,614,117],445,[443,98,783,117])
row('peak-symmetry',8,'봉우리는 원점 양쪽에 대칭이고, 한 골짜기는 [[zero-valley]]이다.','Peaks symmetric about the origin; valley at [[zero-valley]].','峰对称地',[500,119,552,137],445,[443,115.5,782,137])
row('smaller-separation',10,'[[D-small1]]가 줄면 두 봉우리가 가까워지고 골짜기는 높아진다.','As [[D-small1]] shrinks, peaks approach and the valley rises.','随着两个',[445,137,496,154],446,[444,135.5,783,154])
row('critical-separation',12,'특정 [[D-small2]]에서 두 봉우리가 사라져 골이 봉우리가 된다. [[D-small3]]가 더','At critical [[D-small2]], the two peaks vanish. When [[D-small3]] gets smaller,','小到某一',[508,156,559,173],446,[444,154,784,173])
row('single-peak',14,'작아져도 봉우리는 [[zero-peak]]에 하나이며 그림 [[fig2b]]의 곡선 [[curve-II]]와','only one peak at [[zero-peak]] remains, as in Fig. [[fig2b]], curve [[curve-II]].','曲线仍只',[488,175,540,192],445,[443,172.5,783,192])
row('graph-description-end',16,'같다.','The valley has risen to become this peak.','示',[444,193,457,210],445,[442,191,466,210])
row('figure-caption',26,'그림 [[caption2]]','Figure [[caption2]]','图',[599,351,609.5,363.5],600,[589,350,628,364.5])
samples[-1]['source_size_range']=[8,12.751,.025]
row('near-origin-first',28,'[[near-zero1]]이 봉우리인지 골인지 보려면 [[near-Vz]]의 [[near-zero2]] 부근만','[[near-zero1]] peak or valley? Inspect [[near-Vz]] near [[near-zero2]],','处是峰还',[500,374,552,391],473,[471,371.75,783,391])
row('near-origin-second',29,'조사하면 된다. 식 [[near-eq1]]에서 [[near-zero3]]의 전위는','from [[near-eq1]], the potential at [[near-zero3]] is','可确定',[446,392,485,408],447,[445,391,631,408])
row('small-z',33,'[[small-z]]가 아주 작으면','For very small [[small-z]],','注意到当',[439,450,489,465],440,[438,448,552,466])
sample_refinements={'particle-first':[98.5,129,153,148],
 'particle-second':[60,146,117,168],'particle-third':[59,163,117,187],
 'axial-first':[59,182.5,117,206],'axial-second':[59,202,103,222],
 'axial-third':[58.5,218.5,116,240.5],'individual-second':[155,333,216,355],
 'individual-third':[59,352.5,116,372],'small-z':[436,447,492,468]}
for sample in samples:
 if sample['id']in sample_refinements:sample['source_measurement_window']=sample_refinements[sample['id']]
protected=[[149,76,399,108],[152,240,319,305.5],[145,372,401,424.57],[137,436.946,300,534.446],[515,215,695,345],[530,408.5,784,443.7],[449,467,745,508.271]]
specs=[]
def atom(id,rect,path):specs.append(dict(id=id,search_rect=rect,image_path=[path],center_hint=None))
for id,rect in {'eq3':[75,56,97,76],'eq16':[131,56,160,76],'part-one':[85,128,100,150],'axis-z1':[255,182,265,205],'axis-z2':[373,182,384,205],'axis-z3':[168,201,178,223],'axis-z4':[126,218,137,240]}.items():atom(id,rect,301)
for id,rect in {'V1a':[62,312,94,336],'V2a':[99,312,133,336],'fig1':[199,312,209,336],'V1b':[241,312,275,336],'zD':[290,312,328,336],'V2b':[62,331,96,356],'zminusD':[109,331,155,356],'left-z':[393,331,404,356]}.items():atom(id,rect,310)
for id,rect in {'Vz1':[469,60,499,82],'z-var':[513,60,522,82],'V1-right':[610,60,642,82],'V2-right':[693,60,730,82],'D-large':[507,79,520,101],'Vz-large':[699,79,730,101],'fig2a':[456,97,466,119],'curve-I':[518,97,530,119],'zero-valley':[726,115,759,139],'D-small1':[613,134,627,156],'D-small2':[496,153,510,175],'D-small3':[741,153,756,175],'zero-peak':[619,171,650,194],'fig2b':[692,171,704,194],'curve-II':[752,171,766,194],'caption2':[610,350,618,365]}.items():atom(id,rect,328)
for id,rect in {'near-zero1':[471,370,502,393],'near-Vz':[631,370,660,393],'near-zero2':[673,370,704,393],'near-eq1':[505,390,526,410],'near-zero3':[544,390,578,410]}.items():atom(id,rect,337)
atom('small-z',[489,447,499,467],346)
refinements={'eq16':[134,56,160,76],'part-one':[85,128,98,145],
 'axis-z1':[255,182,263,200.5],'axis-z2':[375,182,383,202],
 'axis-z3':[168,201,178,218],'axis-z4':[125.75,218,133.5,235.5],
 'V2a':[99,312,133,331],'V2b':[62,331,94.5,350.5],
 'Vz-large':[698.75,79,726,97],'zero-valley':[726,115,759,133.5],
 'D-small2':[496,153,507.5,171.5],'D-small3':[741,153,756,170.5],
 'fig2b':[692,171,702,194],'near-zero1':[471,370,500.25,393],
 'near-zero2':[673,370,706,393]}
for spec in specs:
 if spec['id']in refinements:spec['search_rect']=refinements[spec['id']]
gaps={}
for r in rows:
 ids=re.findall(r'\[\[([^\]]+)\]\]',r['ko'])
 if ids and r['id']!='figure-caption':gaps[r['id']]={id:.75 for id in ids}
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS');center=json.loads((B/'inputs/page12-caption-source-center.json').read_text('utf8'))
generate(12,rows,samples,geometry,protected,specs,ko_math_gaps=gaps,center_slots={'figure-caption':dict(original_source_center=center['original_source_center'],source_evidence='inputs/page12-caption-source-center.json',original_caption_full_deep_ink_bounds=[600.375,352.875,615.625,361.25],reason='Printed original Fig2 only; keep its original baseline and smaller measured source point, retain original numeral2. No caption is added under the uncaptained first graph.')})
p=Path('D:/CodexBuilds/calibrate-cpho2005-page12-row-weights.py');s=p.read_text('utf8').replace("'section-five'","'section-seven'").replace("'excited-energy'","'particle-first'").replace('Chinese ordinal 三','Chinese ordinal 七').replace('ordinal 三','ordinal 七');p.write_text(s,'utf8')
