"""Manual bilingual reading/ROIs of actual CPhO2003 solution physical page4."""
from pathlib import Path
import json,re
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');T=B/'TS'
SHA='52f8a891d6129becf4d21ccb60f46997cedf9aa50123ffd147294cedcb121b63'
images={1:([54,176.27000732421874,336,466.52000732421874],783,806,271),2:([54,471.67400732421873,336,497.92400732421873],783,72,280),3:([431.6,111.27000732421874,713.6,359.52000732421874],783,689,289),4:([431.6,365.32400732421877,712.85,501.07400732421877],781,377,298)}
def rect(i,v):
 b,w,h,path=images[i];x,y,r,z=v
 return[b[0]+x*(b[2]-b[0])/w,b[1]+y*(b[3]-b[1])/h,b[0]+r*(b[2]-b[0])/w,b[1]+z*(b[3]-b[1])/h]
rows=[]
def row(id,i,box,source,ko,en,atoms=(),size=10.5,left=None,right=None,baseline=None,face='SimSun'):
 boxpt=rect(i,box);r=dict(id=id,reviewed=True,source=source,ko=ko,en=en,size=size,source_prose_face=face,render_mode=0,baseline=baseline if baseline is not None else rect(i,[0,box[1]+25.5,1,box[1]+26.5])[1],left=boxpt[0]if left is None else left,right=boxpt[2]if right is None else right,erase_rects=[boxpt],source_atom_ids=[a[0]for a in atoms],atoms=[dict(id=a[0],rect=rect(i,a[1]),image_path=[images[i][3]],reason='Manually read complete original inline expression/number; original image program, point-scale, baseline and vertical relation retained.')for a in atoms])
 assert set(re.findall(r'\[\[([^\]]+)\]\]',ko))==set(r['source_atom_ids']),id
 assert set(re.findall(r'\[\[([^\]]+)\]\]',en))==set(r['source_atom_ids']),id
 rows.append(r)
row('solutions',1,[56,0,222,31],'·参考解答·','· 참고 해설 ·','· Solutions ·',size=11,face='SimHei',baseline=184.0)
row('problem1',1,[55,47,104,72],'一、','1.','1.',baseline=201.6)
row('left01',1,[55,83,354,117],'设半径为b的球放在4','반지름 [[b]]인 구를 [[4]]구','Radius-[[b]] ball on [[4]];', [('b',[184,86,203,115]),('4',[333,86,353,115])])
row('left02',1,[0,127,354,161],'个球上后，下面4个球的位','위에 놓아도 아래 [[4]]구의','lower [[4]] stay fixed.', [('4',[202,130,222,157])])
row('left03',1,[0,170,354,204],'置未变。以m表示每个球的','위치는 같다. 각 질량은 [[m]],','Each mass [[m]]; their', [('m',[139,175,164,201])])
row('left04',1,[0,214,354,248],'质量，下面4个球的球心形','아래 [[4]]구의 중심은','lower [[4]] centers form', [('4',[140,217,162,245])])
row('left05',1,[0,257,354,291],'成一个位于水平面内的正方','수평면의 정사각형','a horizontal square')
row('left06',1,[0,300,354,335],'形ABCD，俯视图如图决解','[[ABCD]]를 이룬다. 평면도는','[[ABCD]], top view Fig.', [('ABCD',[36,303,113,332])])
row('left07',1,[0,344,354,378],'20-1-1所示。O为正方形对','[[20-1-1]]이다. [[O]]는','[[20-1-1]]. [[O]] is the', [('20-1-1',[0,346,85,376]),('O',[178,346,202,375])])
row('left08',1,[0,387,354,421],'角线的交点，各球之间的相','대각선의 교점이다.','diagonal crossing;')
row('left09',1,[0,431,354,465],'互作用力大小均为F1。根据','상호작용 힘은 모두 [[F1]].','mutual force [[F1]].', [('F1',[245,434,278,464])])
row('left10',1,[0,474,783,508],'对称性，并注意到接触面都是光滑的，可知每个球受到相邻两球','접촉면이 모두 매끄럽고 대칭이므로, 이웃한 두 구가 각 구에','All contacts are smooth. By symmetry, each ball feels')
row('left11',1,[0,515,490,552],'作用力的合力都为sqrt2F1，方向沿对角线。','가하는 합력은 [[resultant]]이며 대각선 방향이다.','a resultant [[resultant]] along its diagonal.', [('resultant',[229,515,296,551])],right=336)
row('left12',1,[55,559,783,595],'由几何对称性分析，可知对角线AC、上面球的球心E和碗','대칭에 의해 대각선 [[AC]], 위 구의 중심 [[E]]와 그릇의','By symmetry, diagonal [[AC]], upper center [[E]] and bowl', [('AC',[459,560,501,591]),('E',[699,560,725,591])])
row('left13',1,[0,602,783,639],'的球心O′应在同一竖直平面内，如图决解20-1-2所示。设上面','중심 [[Op]]는 한 수직면에 있다(그림 [[ref]]). 위 구가','center [[Op]] lie in one vertical plane (Fig. [[ref]]).', [('Op',[89,604,122,637]),('ref',[523,604,628,636])])
row('left14',1,[0,646,783,682],'球与下面每个球的相互作用力的大小均为F2，对A球，F2的方','각 아래 구에 가하는 힘은 [[F2a]]이다. 구 [[A]]에 대한 [[F2b]]는','Each upper/lower force is [[F2a]]. On [[A]], [[F2b]] acts', [('F2a',[536,648,571,681]),('A',[621,648,643,679]),('F2b',[690,648,726,682])])
row('left15',1,[0,689,591,725],'向沿球心A、E连线。平衡时对半径为b的球有','중심 [[A]], [[E]]를 잇는 방향. 반지름 [[b]]인 구의 평형은','along centers [[A]], [[E]]. For radius [[b]] in equilibrium:', [('A',[123,692,146,723]),('E',[160,691,186,723]),('b',[475,691,495,723])],right=336)
row('left17',1,[0,775,643,806],'式中α是球心连线AE与水平线AC之间的夹角，有','여기서 [[alpha]]는 [[AE]]와 수평선 [[AC]] 사이의 각이며','Here [[alpha]] is the angle of [[AE]] to horizontal [[AC]]; thus', [('alpha',[66,778,86,806]),('AE',[239,778,281,806]),('AC',[403,778,446,806])],right=336)
row('left-caption',1,[489,419,652,449],'图决解20-1-1','그림 [[number]]','Fig. [[number]]', [('number',[562,421,649,447])],size=8,baseline=rect(1,[0,444,1,445])[1],left=231.5,right=291)
row('right-caption',3,[320,259,458,291],'图决20-1-2','그림 [[number]]','Fig. [[number]]', [('number',[370,260,457,288])],size=8,baseline=rect(3,[0,283,1,284])[1],left=548,right=597)
row('right01',3,[52,300,783,339],'对于下面每个球，如球A，受到的作用力有重力mg，B、D两','아래 구 [[A]]에 작용하는 힘은 중력 [[mg]], 구 [[B]], [[D]]의','For lower ball [[A]]: weight [[mg]], force due to [[B]], [[D]],', [('A',[332,304,355,336]),('mg',[642,301,681,338]),('B',[691,300,713,335]),('D',[729,300,752,335])],right=713.6)
row('right02',3,[0,343,783,383],'球对它的作用的合力sqrt2F1，上面球的作用力F2和碗面的作用力','합력 [[resultant]], 위 구의 힘 [[F2]]와 그릇의 힘','resultant [[resultant]], upper-ball force [[F2]], and bowl force', [('resultant',[249,345,319,380]),('F2',[543,344,580,381])])
row('right03',3,[0,387,783,427],'F3。由于体系对称且接触面光滑，各力均通过球心A，F3还通过','[[F3a]]. 대칭과 매끄러운 면에 의해 각 힘은 중심 [[A]], [[F3b]]는','[[F3a]]. Symmetry and smooth contacts put all forces through [[A]], [[F3b]]', [('F3a',[0,390,35,425]),('A',[621,386,646,421]),('F3b',[658,386,691,422])])
row('right04',3,[0,431,169,472],'O′，平衡时有','[[Op]]도 지난다. 평형에서','also through [[Op]]. In equilibrium,', [('Op',[0,433,34,470])],right=713.6)
row('right07',3,[0,580,477,622],'式中β是F3方向与竖直线的夹角，有','여기서 [[beta]]는 [[F3]]와 수직선의 각이며','Here [[beta]] is the angle of [[F3]] to the vertical; thus', [('beta',[68,581,89,622]),('F3',[122,581,156,620])],right=713.6)
row('right09',4,[0,0,166,36],'由式(1)可得','식 [[1]]에서','From [[1]],', [('1',[58,0,98,33])],baseline=377.5,right=713.6)
row('right11',4,[0,114,259,154],'由式(4)和(6)可得','식 [[4]], [[6]]에서','From [[4]] and [[6]],', [('4',[58,114,101,151]),('6',[139,114,177,151])],baseline=419.0,right=713.6)
row('right13',4,[0,225,313,266],'由式(3)、(6)和(7)可得','식 [[3]], [[6]], [[7]]에서','From [[3]], [[6]], and [[7]],', [('3',[58,225,99,263]),('6',[114,225,156,263]),('7',[194,225,235,263])],baseline=459.5,right=713.6)
row('right15',4,[0,338,781,377],'如果F1≥0，表示下面的4个球相互接触，4个球在原来的位置；','[[condition]]이면 아래 [[4a]]구는 서로 접촉하며 [[4b]]구 모두 원래 위치에 있다.','If [[condition]], the [[4a]] lower balls touch; all [[4b]] stay in place;', [('condition',[61,339,160,377]),('4a',[347,339,371,377]),('4b',[549,339,572,377])],baseline=498.8)
plan=dict(source_page=4,source_sha256=SHA,manual_rois_reviewed=True,publication_ready=False,original_math_retyped=False,original_bitmap_scale_unchanged=True,source_point_calibration=dict(method='Manual original Chinese glyph boxes, eight known glyphs 由几何对称性分析, SimSun outline-sidebearing corrected full-width pitch least-squares, never translation fitting.',estimated_point=10.49698133,fixed_body_point=10.5,residual_RMS_pt=.390340293,source_baseline_estimate_387_84725297=True,all_original_raster_math_unchanged=True),rows=rows,protected_source_display_and_figure_rects=[[195,209,318,326],[484,113,642,205],[145,440.5,335.5,458],[143,473,335.5,494],[493,285,713,320],[511,339,713,359],[532,382,713,402],[531,422,713,444],[522,461,713,484]],reviewed_blank_background_rects=[])
p=T/'authoring/page04-layout.json';assert not p.exists(),p;p.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n','utf8')
print('page04 manually authored',len(rows),'rows',sum(len(r['atoms'])for r in rows),'complete original image atoms')
