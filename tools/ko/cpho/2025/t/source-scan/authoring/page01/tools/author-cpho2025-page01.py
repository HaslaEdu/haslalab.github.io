from pathlib import Path
import json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2025')
OUT=B/'authoring';OUT.mkdir(exist_ok=True)
rows=[]
def row(id,y,left,right,ko,en,erase,atoms=(),size=10.24,role='serif'):
    rows.append(dict(id=id,baseline=y,left=left,right=right,size=size,role=role,ko=ko,en=en,erase_rects=erase,
                     atoms=[dict(id=a[0],rect=a[1],image_path=[10],reason='Manually selected original source-image notation; original scale, baseline, shape and encoded image retained.')for a in atoms],
                     source_atom_ids=[a[0]for a in atoms],reviewed=True,
                     printed_stroke_by_language={'ko':{'regular':.30,'bold':.40},'en':{'regular':.50,'bold':.60}}))
# These are manually read source-image ROIs. OCR peak hints were used only to
# locate the lines; they do not generate masks or mathematical content.
row('p1-intro-a',188.35,65.5,401.5,'1. ([[score]]점) 여러 생체 분자의 자기 조립에서 극성 분자 사이의',
    '1. ([[score]] marks) In biomolecular self-assembly, electric dipole',[[63,176,402,192]], [('score',[87,179,102,190.8])])
row('p1-intro-b',204.57434876,64.2,401.5,'쌍극자 상호작용은 분자 배열에 중요하다. 단백질 조각에서는',
    'interactions help determine molecular arrangements. In protein',[[63,193,402,208]])
row('p1-intro-c',221.0,64.2,401.5,'일부 극성 분자가 막이나 지지대에 고정되고, 다른 분자는',
    'fragments, some polar molecules are fixed to a membrane or',[[62.5,209,402,225]])
row('p1-intro-d',237.4,64.2,401.5,'궤도에서 이동·회전한다. 공간 제약과 쌍극자 작용의',
    'support; others slide or rotate on a track. Dipoles and constraints',[[62.5,225.3,402,241]])
row('p1-intro-e',253.85,64.2,401.5,'결합이 방향성이 강한 퍼텐셜을 만들고 안정 구조를 정한다. 그림 [[figure]]의 [[xy]]',
    "couple: a very anisotropic potential sets stable forms. Fig. [[figure]]'s [[xy]]",[[62.5,241.4,402,257.5]],
    [('figure',[251.1,243.4,261.3,255.8]),('xy',[282.5,244,298.5,257])])
row('p1-fixed-dipole',270.25,64.2,401.5,'평면에 모형화한다. 원점 [[O]]에 고정된 분자 [[A]]의 영구 모멘트는 [[p1]], 크기는',
    'plane models this. Molecule [[A]], centred at [[O]], has permanent dipole [[p1]],',[[62.0,257.6,402,275.0]],
    [('O',[181,259,190,272]),('A',[255,259,264,272]),('p1',[348.5,257.6,360.7,273.2])])
row('p1-direction',288.0,63.5,401.5,'[[p]]이고 [[y]]축 양의 방향이다. 분자 [[B]]의 영구 모멘트 [[p2]]도 크기가 [[p2mag]]이며,',
    'of magnitude [[p]] in positive [[y]]. For [[B]], dipole [[p2]] has magnitude [[p2mag]],',[[62,276,402,293.6]],
    [('p',[62.7,277.1,70.9,291.8]),('y',[111.1,277,120.5,291.7]),('B',[213.1,277.1,222.9,291.8]),('p2',[308.0,276.8,322.8,293.5]),('p2mag',[372.3,277,380.5,292])])
row('p1-angle-guide',306.0,63.8,538,'[[y]]축과 [[theta]] [[range]]의 각을 이룬다. 질량 중심은 [[xyb]]에 있고 [[positive]], [[x]]는 변한다. [[yb]]에는',
    'at angle [[theta]] [[range]] to [[y]]. Its centre is at [[xyb]], with [[positive]] and variable [[x]]. Through [[yb]],',[[62.3,293.6,538,311]],
    [('y',[87,295,96,310]),('theta',[145,295,156,310]),('range',[157.2,294.5,218.5,311]),('xyb',[269.5,294.8,312,311]),('positive',[349,295,371,310]),('x',[382,295,390,310]),('yb',[443,295,466.5,310])])
row('p1-axle',323.4,64.0,538,'[[x]]축과 나란한 매끄러운 가는 레일이 있다. 분자 [[B]]의 질량 중심은 질량·길이를 무시하는 [[xy]] 평면에',
    'a thin smooth track parallels [[x]]; a smooth insulating axle through [[B]] is normal to [[xy]],',[[62.5,311.2,538,328]],
    [('x',[65,313,73.5,328]),('B',[176.8,313,185.7,328]),('xy',[459.5,313,476.1,328])])
row('p1-mass',340.0,64.0,538,'수직인 매끄러운 절연 축으로 레일과 연결되어 움직인다. 분자 [[B]]의 질량은 [[m]], 질량 중심은 축에 있다.',
    'of negligible mass and length, sliding on the track. For [[B]], mass [[m]], its mass centre is on the axle.',[[62.5,328.2,538,345]],
    [('B',[231.5,329,241,344]),('m',[284.5,329,297,344])])
row('p1-inertia',363.0,64.0,538,'편의상 축 관성 모멘트는 [[inertia]], [[x]], [[y]] 방향 단위벡터는 [[ex]], [[ey]], 진공 유전율은 [[eps]]이다.',
    'Use [[inertia]]. Unit vectors along [[x]], [[y]]: [[ex]], [[ey]]; vacuum permittivity: [[eps]]. Ignore gravity.',[[62.5,345.2,538,374]],
    [('inertia',[119.5,346.2,162.5,372.7]),('x',[167.0,351.4,176.0,367]),('y',[218.5,351.4,227.2,367]),('ex',[343,351,358,368.5]),('ey',[376,351,391.1,368.5]),('eps',[465,351,480,368.5])])
row('p1-question-1',388.0,69,538,'중력은 무시한다. (1) 분자 [[A]]가 분자 [[B]]의 위치에 만드는 전기장 [[E]]을 구하여라.',
    '(1) Find the electric field [[E]] produced by molecule [[A]] at molecule [[B]].',[[67,374.5,318,391.5]],
    [('A',[145,376,154,391]),('B',[207,376,216.5,391]),('E',[298.3,376,312.8,392])])
row('p1-question-2',405.5,69,538,'(2) 분자 [[B]]가 받는 전기력의 [[x]] 성분 [[F]]와 절연 축에 대한 토크 [[M]]을 구하고, 정지 조건을 유도하여라.',
    '(2) Find force component [[F]] along [[x]] and torque [[M]] on [[B]] about its axle. Derive conditions',[[67,392,538,409.5]],
    [('B',[144,394,153,409]),('x',[228,394,237,409]),('F',[287,394,301,410]),('M',[430,394,443,409])])
row('p1-question-2-end',423.0,64.5,538,'', 'for it to remain at rest.',[[63,409.8,94,427]])
row('p1-question-3',439.0,69,538,'(3) [[theta]]가 작은 평형에서 분자 [[B]]의 안정성을 분석하여라. 분자 [[B]]의 평형 이탈이 작을 때',
    '(3) Study [[B]] near the equilibrium of smaller [[theta]]. For small deviations of [[B]],',[[67,427,538,442.5]],
    [('B',[153.5,429,163,443]),('theta',[304.5,428,314.0,443]),('B2',[526.5,428,536.5,443])])
rows[-1]['ko']=rows[-1]['ko'].replace('분자 [[B]]의 평형','분자 [[B2]]의 평형')
rows[-1]['en']=rows[-1]['en'].replace('deviations of [[B]]','deviations of [[B2]]')
row('p1-question-3-end',455.5,64.5,538,'[[xt]]와 [[thetat]]의 일반식을 구하여라. 초기 조건은 주어지지 않았으므로 미정의 적분 상수를 포함해도 된다.',
    'find general [[xt]], [[thetat]], with arbitrary integration constants (no initial conditions yet).',[[63,443,532,459.5]],
    [('xt',[168,444,187.7,460]),('thetat',[197.5,444,217.7,460])])
row('p1-question-4',473.0,69,538,'(4) [[xa]], [[small]], [[zero]]에서 분자 [[B]]를 정지 상태로 놓는다. 시각 [[t]]의 [[xt]], [[thetat]]를 구하여라.',
    '(4) Release [[B]] from rest at [[xa]], [[small]], [[zero]]. Find explicit [[xt]] and [[thetat]] at time [[t]].',[[67,460,532,477]],
    [('B',[140.5,462,150,477]),('xa',[201.6,461.7,226,477]),('small',[227,461.7,283.0,477]),('zero',[287,462,313.5,477]),('t',[387,462,396,477]),('xt',[414,461.7,433,477]),('thetat',[442.0,461.7,465,477])])
row('p2-convention',505.0,65.5,538,'2. ([[score]]점) [약속: [[x]]축의 양의 방향으로 진행하는 일차원 조화 횡파를 다음과 같이 나타낸다.',
    '2. ([[score]] marks) [Convention: a harmonic transverse wave travelling in positive [[x]] is written as',[[64,492,350,508.5]],
    [('score',[87,495,102,508]),('x',[168.7,495,176.8,508])])
# The full original displayed wave equation is left completely untouched.
row('p2-wave-symbols',540.3,65,538,'[[A]], [[omega]], [[k]], [[phi]]는 진폭, 각진동수, 파수([[omega2]]와 매질 상수로 표현), 초기 위상이며, [[complexA]]는',
    '[[A]], [[omega]], [[k]], [[phi]]: amplitude, angular frequency, wavenumber (via [[omega2]]), initial phase. [[complexA]]:',[[63.5,528,537,545]],
    [('A',[87,530,97,544]),('omega',[104,530,115,544]),('k',[124,530,133,544]),('phi',[145,530,157,546]),('omega2',[306,530,317,544]),('complexA',[446.5,526,515.6,546])])
row('p2-complex-amplitude',557.0,65,538,'위치 [[x]]에서의 복소 진폭이다.]', 'the complex amplitude at [[x]]. Wavenumber depends on frequency and medium parameters.]',[[63.5,545.2,165,562]], [('x',[87,547,96,561])])
row('p2-phononic-crystal',574.0,85.5,385,'공간 주기적인 탄성 매질을 ‘포노닉 결정’이라 한다. 각진동수 [[omega]]인',
    'Periodic elastic media are phononic crystals. Consider, at [[omega]],',[[84,562,385,578]], [('omega',[373.5,564,384,579])])
row('p2-small-wave',590.5,65,385,'일차원 줄의 소진폭 횡파 전파를 살펴보자. 중력은 무시한다.',
    'small transverse waves on a 1D string. Neglect gravity.',[[63.5,578.4,288,594.5]])
row('p2-question-1',606.5,69.5,385,'(1) 선밀도 [[rho]], 장력 [[tau]]인 무한한 균일 줄을 생각하자. [[x]]축은 줄을',
    '(1) Infinite uniform string: line density [[rho]], tension [[tau]], axis [[x]],',[[67.5,593.8,386,610.5]],
    [('rho',[281,595.5,290.5,610]),('tau',[329,595.5,339,610]),('x',[345,595.5,354.5,610])])
row('p2-question-1-b',624.0,65,385,'따른다(그림 [[figure]]). 진폭 [[A]], 초기 위상 [[zero]]인 파동이 [[x]]축 양의 방향으로',
    '(Fig. [[figure]]). A wave of amplitude [[A]], phase [[zero]], travels in positive [[x]].',[[63.5,611,386,628]],
    [('figure',[129,612,141.4,626]),('A',[225,612,234,626]),('zero',[284,612,293,626]),('x',[345,612,354.5,626])])
row('p2-question-1-c',640.0,65,538,'진행한다. 시각 [[t]], 위치 [[x]]의 [[x2]] 방향 원래 단위 길이당 운동 에너지 [[Ek]]와 퍼텐셜 에너지 [[Ep]],',
    'At [[t]], [[x]], find kinetic [[Ek]] and potential [[Ep]] energies per original unit length along [[x2]]',[[63.5,627.8,538,645]],
    [('t',[126.3,629,134,643]),('x',[161.5,629,170.5,643]),('x2',[192,629,201,643]),('Ek',[311,628,342.5,645]),('Ep',[374.8,628,405,645])])
row('p2-question-1-d',660.5,65,538,'순간 에너지 흐름 [[I]]와 평균 [[Ibar]]를 구하여라. 파동이 없을 때의 퍼텐셜 에너지는 0이다.',
    '(zero potential energy without waves), and the instantaneous energy flux [[I]] and mean [[Ibar]].',[[63.5,646.6,256,665]],
    [('I',[163.5,649,190,665]),('Ibar',[240,648.5,250.6,664])])
row('p2-question-2',678.5,69,538,'(2) [[x]]축의 양·음 방향으로 진행하는 조화파가 동시에 있을 때, [[x1]]에서 두 복소 진폭을 각각 [[A1]]과',
    '(2) For harmonic waves travelling both ways along [[x]], take complex amplitudes at [[x1]] as [[A1]] and',[[67,666,532,684]],
    [('x',[169.7,668,178.7,682]),('x1',[397,668,424,684]),('A1',[513,667,527,685])])
row('p2-question-2-b',706.0,66,378.5,'[[B1]], [[x2]]에서 [[A2]], [[B2]]로 두자. [[A2b]], [[B2b]]를 [[A1]], [[B1b]]로 나타내면:',
    '[[B1]], and at [[x2]] be [[A2]], [[B2]]. Express [[A2b]], [[B2b]] via [[A1]], [[B1b]] as shown.',[[64.5,693,377.5,713]],
    [('B1',[66.5,695,77.6,711]),('x2',[97,695,124.2,711]),('A2',[215.6,693.9,230,712]),('B2',[236.0,694,250.7,712]),('A2b',[257,694,272.5,712]),('B2b',[280.5,694,294.4,712]),('A1',[315.5,694,327,712]),('B1b',[335.5,694,349,712])])
row('p2-matrix-caption',706.0,470.0,538,'행렬로는', 'Matrix form:',[[468.5,694,538,713]])
row('figure-1-caption',277.5,455,480,'그림 [[fig]]', 'Fig. [[fig]]',[[452,264.5,481,281]], [('fig',[465.5,267,480,281])])
row('figure-2-caption',606.5,454,480,'그림 [[fig]]', 'Fig. [[fig]]',[[451,593.6,482,611]], [('fig',[465.2,595,481,610])])
row('footer',790.7,265,337,'[[one]] / [[six]]쪽','Page [[one]] of [[six]]',[[263,778.5,339,795]],
    [('one',[280,780,287,794]),('six',[315.3,780,322.5,794])],size=9.0)
# Expanded 4x source contact sheets exposed neighbouring Chinese strokes and
# three wrongly anchored tiny variables. Correct only these reviewed clips;
# the complete original scan program, its CTM and each destination y stay fixed.
corrections={
 'p1-intro-a/score':[90.5,179,102,190.8],
 'p1-direction/p':[62.7,277.1,69.6,291.8],
 'p1-direction/y':[111.1,277,119.6,291.7],
 'p1-direction/p2':[308,276.8,321.0,293.5],
 'p1-direction/p2mag':[372.3,277,379.4,292],
 'p1-angle-guide/y':[87,295,95.2,310],
 'p1-angle-guide/xyb':[269.5,294.8,310.5,311],
 'p1-angle-guide/positive':[349,295,370.5,310],
 'p1-angle-guide/x':[382,295,389.3,310],
 'p1-angle-guide/yb':[443,295,465.7,310],
 'p1-axle/x':[65,313,72.7,328],
 'p1-axle/B':[176.8,313,184.8,328],
 'p1-axle/xy':[459.5,313,475.1,328],
 'p1-mass/m':[284.5,329,293.7,344],
 'p1-inertia/inertia':[118.6,346.2,162,372.7],
 'p1-inertia/x':[167,351.4,174.7,367],
 'p1-inertia/y':[218.5,351.4,226.1,367],
 'p1-inertia/ex':[347.1,356.8,355.1,366.3],
 'p1-inertia/ey':[368.6,356.7,377.4,367.2],
 'p1-inertia/eps':[462.1,355.9,470.9,365.7],
 'p1-question-1/E':[298.3,376,311.3,392],
 'p1-question-2/F':[287,394,299.4,410],
 'p1-question-3/theta':[304.5,428,313.2,443],
 'p1-question-4/t':[389.5,462,393.8,477],
 'p1-question-4/xt':[414,461.7,432.2,477],
 'p1-question-4/thetat':[444,461.7,463.5,477],
 'p2-convention/score':[88.1,495,100.2,508],
 'p2-convention/x':[168.7,495,176.0,508],
 'p2-wave-symbols/A':[87,530,96.3,544],
 'p2-wave-symbols/omega2':[306,530,316.3,544],
 'p2-question-1/tau':[330,595.5,337.8,610],
 'p2-question-1/x':[345,595.5,353.6,610],
 'p2-question-1-b/A':[225,612,233.2,626],
 'p2-question-1-b/x':[345,612,353.6,626],
 'p2-question-1-c/t':[126.3,629,132.2,643],
 'p2-question-1-c/x':[161.5,629,169.5,643],
 'p2-question-1-c/x2':[191.5,629,199.2,643],
 'p2-question-2/x':[169.7,668,177.8,682],
 'p2-question-2/x1':[397,668,423.2,684],
 'p2-question-2/A1':[513,667,525.4,685],
 'p2-question-2-b/x2':[97,695,123.4,711],
 'p2-question-2-b/A2':[215.6,693.9,228.3,712],
 'p2-question-2-b/B2':[236,694,249.2,712],
 'p2-question-2-b/A2b':[257,694,270.8,712],
 'p2-question-2-b/B2b':[280.5,694,293.1,712],
 'p2-question-2-b/A1':[315.5,694,325.2,712],
 'p2-question-2-b/B1b':[335.5,694,346.5,712],
 'footer/one':[279,780,287,794],
}
for r in rows:
    for a in r['atoms']:
        key=r['id']+'/'+a['id']
        if key in corrections:
            a['initial_rect']=a['rect'];a['rect']=corrections[key]
            a['source_crop_review']='atom-review/page01-atoms-01.png through page01-atoms-08.png; explicit manually reviewed corrected ROI.'
# All eight proposed contact sheets were visually compared with the complete
# source neighbourhood. Three proposals are rejected: a disconnected y arm,
# the multi-symbol theta=0 identity and the hat on the complex amplitude B_2.
# This is an explicit per-document review, never automatic glyph recognition.
suggestions=json.loads((OUT/'page01-single-symbol-clip-proposals.json').read_text('utf8'))if(OUT/'page01-single-symbol-clip-proposals.json').exists()else[]
rejected={('p1-direction','y'),('p1-question-4','zero'),('p2-question-2-b','B2')}
accepted={(s['row'],s['atom']):s['proposed_rect']for s in suggestions if(s['row'],s['atom'])not in rejected}
accepted[('p1-direction','y')]=[111.5,282.,119.,291.75]
for r in rows:
    for a in r['atoms']:
        if(r['id'],a['id'])in accepted:
            a['previous_rect_before_source_ink_review']=a['rect'];a['rect']=accepted[(r['id'],a['id'])]
            a['source_crop_review']='All8 atom-review-proposed contact sheets manually reviewed. Whole original notation remains inside the clip; neighbouring Chinese ink is excluded. Original image scale/y unchanged.'
# Baselines are measured from original CJK shapes at a fixed source point size.
# The bracketed convention is a distinct actual KaiTi role in the original.
measurements=json.loads((OUT/'page01-source-baselines.json').read_text('utf8'))
by_id={r['id']:r for r in measurements['rows']}
note_fields={'p2-convention':'convention','p2-wave-symbols':'convention_def','p2-complex-amplitude':'convention_amplitude'}
for r in rows:
    measured=by_id[r['id']];r['baseline']=measured['measured_baseline'];r['baseline_evidence']=measured['evidence'];r['source_face']='SimSun';r['font_role']='body'
    if r['id']=='footer':r['size']=8.5;r['baseline']=789.5;r['baseline_evidence']['source_first_last_CJK_midpoint_used']=True
    if r['id']in note_fields:
        field=note_fields[r['id']];qcal=json.loads((B/(field+'-font-calibration.json')).read_text('utf8'));best=qcal['best_by_font']['KaiTi']
        r['size']=best['size_pt'];r['baseline']=best['source_font_origin_point'][1];r['source_face']='KaiTi';r['font_role']='note';r['source_font_evidence']=str(B/(field+'-font-calibration.json'))
        r['printed_stroke_by_language']={'ko':{'regular':.15,'bold':.25},'en':{'regular':.275,'bold':.375}}
    if r['id']=='p2-convention':
        r['prefix_font_role']='body';r['prefix_size']=9.72;r['prefix_baseline']=504.04129091157034
        r['prefix_source_evidence']='convention_score-font-calibration.json: actual SimSun score label; following bracketed note independently KaiTi.'
q=dict(status='DRAFT_MANUAL_MAPPING_IN_PROGRESS_NOT_FOR_PUBLICATION',source_page=1,
       source_sha256='c9562e8f6053b454391083289b179f28ed29f7d9024723a34a2a8b0e663bd306',
       manual_rois_reviewed=False,publication_ready=False,rows=rows,
       note='Complete page semantic/ROI draft for review only. All selected notation must be checked against the coordinate source; point size is calibrated from the source, not fitted to translations. No READY until source scan glyph/paint, full math ink, outside graphics, new prose visibility, native overlap and visual comparison all pass.')
(OUT/'page01-draft-layout.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
print('Saved non-publishable manual semantic/ROI draft',len(rows),'rows')
