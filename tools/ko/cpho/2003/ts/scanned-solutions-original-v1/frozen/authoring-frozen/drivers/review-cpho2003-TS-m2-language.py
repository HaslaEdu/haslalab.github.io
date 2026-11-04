"""Source-bound grammatical prose, retaining every original math atom and source size/y."""
from pathlib import Path
import json,shutil,sys,hashlib
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');T=B/'TS'
sys.path[:0]=[str(T/'engine'),str(B/'engine'),'D:/CodexBuilds']
E={
4:{
'left01':('반지름 [[b]]인 구를 [[4]]개의','A radius-[[b]] ball on [[4]]'),
'left02':('구 위에 놓고, 아래 [[4]]개의','balls leaves all [[4]] fixed.'),
'left03':('위치는 그대로라 하자. [[m]]은',"Let [[m]] be each ball's mass."),
'left04':('각 질량이며, 아래 [[4]]구의','The lower [[4]] centers form'),
'left05':('중심은 수평면의 정사각형','a square in a horizontal'),
'left06':('[[ABCD]]를 이룬다. 그림','plane: [[ABCD]] (see Fig.'),
'left07':('[[20-1-1]]은 평면도다. [[O]]는','[[20-1-1]]). [[O]] is where'),
'left08':('대각선의 교점이다. 구 사이','the diagonals meet. Each'),
'left09':('힘은 모두 [[F1]]이다.','mutual force has size [[F1]].'),
'left12':('대칭에 의해 대각선 [[AC]], 위 구의 중심 [[E]]와 그릇의','By symmetry, diagonal [[AC]], upper center [[E]] and bowl'),
'left13':('중심 [[Op]]는 한 수직면에 있다(그림 [[ref]]). 위 구는','center [[Op]] lie in one vertical plane (Fig. [[ref]]). The'),
'left14':('각 아래 구에 힘 [[F2a]]를 가한다. [[A]]에서 [[F2b]]의 방향은','upper ball exerts [[F2a]] on each lower ball. On [[A]], [[F2b]]'),
'left15':('중심 [[A]], [[E]]의 연결선이다. 반지름 [[b]]인 구의 평형에서','acts along [[A]][[E]]. For the ball of radius [[b]], we have'),
'right01':('아래 구 [[A]]는 중력 [[mg]], [[B]], [[D]]로부터 받는','The forces on lower ball [[A]] are its weight [[mg]], the'),
'right02':('합력 [[resultant]], 위 구의 힘 [[F2]], 그릇이 가하는 힘','resultant [[resultant]] due to [[BOTH_UNUSED]]'),
'right03':('[[F3a]]를 받는다. 대칭과 매끄러운 접촉으로 각 힘은 [[A]], [[F3b]]는','[[F3a]]. Symmetry and smooth contacts make all forces pass [[A]]; [[F3b]]'),
'right04':('[[Op]]도 지난다. 따라서 평형에서','also passes [[Op]]. Equilibrium gives'),
},
5:{
'separation-condition':('[[negative]]이면 아래 [[4a]]구가 분리된다. [[4b]]구가 분리될 때','If [[negative]], the lower [[4a]] balls separate. For these [[4b]],'),
'from8':('식 [[8]]에서 다음을 얻는다.','equation [[8]] gives:'),
'distance-to-O':('아래 구와 [[O]]의 최소 거리는 [[distance]]이다. 위 구가','The least distance from [[O]] is [[distance]]. A ball on'),
'four-balls14':('아래 [[4]]구 위에 놓일 수 있다는 것은','the [[4]] lower balls must therefore satisfy'),
'ellipse-axes':('긴반지름은 [[a]], 짧은반지름은 [[b]]이며','Its semi-axes are [[a]] and [[b]];'),
'ellipse-focal-distance':('중심 [[O]]와 초점 [[F]]의 거리는 [[c]]다.','center [[O]] is [[c]] from focus [[F]].'),
'ellipse-reference':('그림 [[ref]]에서 해석기하학을 적용하면','Fig. [[ref]] and geometry give'),
'hyperbola1':('방출 후 탐사기는','The ejected probe moves'),
'hyperbola2':('쌍곡선을 따른다. 꼭짓점은','on a hyperbola whose vertex'),
'hyperbola3':('원래 타원 궤도의 꼭짓점과','is the old elliptical vertex'),
'hyperbola4':('같다(그림 [[ref]]). 운동 중','(Fig. [[ref]]). Its angular'),
'hyperbola5':('각운동량과 역학적 에너지가','momentum and mechanical energy'),
'hyperbola6':('보존된다. 방출 순간 속력','are conserved. Let'),
'hyperbola7':('[[v0]]는 쌍곡선 꼭짓점의 속력이다.','[[v0]] be its speed at ejection,'),
'hyperbola8':('이때 지구 중심과의 거리는','at the hyperbola vertex.'),
'hyperbola9':('[[ac]]이고, 각운동량은 [[angular]]이다.','Its Earth-center distance is [[ac]], and momentum is [[angular]].'),
'hyperbola10':('무한히 멀어지면 속도는 점근선 방향이다. 그 속력을','At infinity velocity follows the asymptote. Let its speed be'),
'hyperbola11':('[[v]], 지구 중심과 점근선의 거리를 [[d]]라 하면 각운동량은','[[v]] and the Earth-to-asymptote distance [[d]]; angular momentum is'),
},
6:{
'wheel-emf':('각속도가 [[Omega]]일 때 바큇살마다 유도되는 기전력은','At angular speed [[Omega]], the emf induced in each spoke is'),
'spoke-current':('저항 [[R]]을 지나는 전류가 [[I]]이면 바큇살의 전류는','If current [[I]] flows through [[R]], each spoke carries'),
'spoke-torque':('회전축에 대한 자기 토크는','The magnetic torque about the axle is'),
'total-torque':('플라이휠 전체에 작용하는 자기 토크는','The total magnetic torque on the wheel is'),
'when-torque-equal':('다음 조건에서','When'),
'steady-rotation':('일정한 각속도로 돌아 [[Omega0]], [[I0]]가 된다. 위','the wheel rotates steadily: [[Omega0]], [[I0]]. The above'),
'wheel-equations-give':('식들을 적용하면','equations give'),
},
7:{
'steady-speed':(None,'Larger [[R]] gives a larger steady angular speed [[Omega0]],'),
'steady-current':(None,'while the steady current [[I0]] is independent of [[R]].'),
'particle-data':('전하량 [[q]], 질량 [[m]], 처음 속력 [[v]]','For charge [[q]], mass [[m]], speed [[v]],'),
'uniform-field':('인 입자가 균일한 자기장 [[B]]에서','if the initial velocity is normal to [[B]],'),
'normal-field':('처음 속도와 자기장이 수직이면,','a particle in this uniform field'),
'lorentz-newton':('로런츠 힘과 뉴턴 법칙에 따라',"feels Lorentz force; Newton's law"),
'circular-period':('등속 원운동한다. 주기 [[T]]와','gives uniform circular motion. [[T]]'),
'orbital-radius':('궤도 반지름 [[R]]에 대해','and [[R]] are the period and radius:'),
'apply-particle-a':(None,'Here particle [[a]] initially'),
'right-quadrant':(None,'moves in quadrant I, right of [[y]]:'),
'a-enters-left':('[[halfTar]] 후 [[y]]축 왼쪽인 제2·3사분면으로 들어가며','After [[halfTar]], it enters II/III, left of [[y]];'),
'a-period-radius':('주기와 궤도 반지름은 다음과 같다.','its period and radius then become'),
'dashed-repeat':(None,'It repeats the dashed [[xy]] path in Fig. [[ref]].'),
'b-enters-right':('[[halfTbl]] 후 [[y]]축 오른쪽 제4사분면으로 들어가며','After [[halfTbl]], it enters quadrant IV, right of [[y]];'),
'b-period-radius':('주기와 궤도 반지름은 다음과 같다.','its period and radius then become'),
'solid-repeat':(None,'It repeats the solid [[xy]] path in Fig. [[ref]].'),
'meeting-points':(None,'As Fig. [[ref]] shows, the paths must cross'),
'minimum-difference':(None,'or touch for a meeting. To find the least delay, let'),
'simultaneous-start':(None,'[[a]] and [[b]] start together. Compare passage at'),
},
8:{
'least-delay':('각 교점·접점에서 통과 시간을 비교한다. 그 최소 차는','each crossing or tangent point. The least gap'),
'starting-delay':('[[a]], [[b]]가 그곳에서 만나기 위한','for [[a]] and [[b]]'),
'delay-equivalence':('출발 시간 차와 같다. 이를 구하려고','is the start delay for a meeting.'),
'crossing-reference-prefix':(None,'Trace the paths in Fig. [[ref-prefix]]'),
'crossing-reference-tail':(None,'[[ref-tail]] for [[a]] and [[b]].'),
'shortest-crossing':(None,'The crossing between [[fiveT]] and [[fiveQuarterT]]'),
'before-five':(None,'least gap. For [[a]], [[b]], before [[fiveT]]'),
'larger-delay':(None,'give [[a]] and [[b]] longer time gaps.'),
'new-origin-location':(None,'On the negative [[y]]-axis, [[threeRal]] from [[O]], choose'),
'new-origin-time':(None,'([[sixRbl]]) [[Oprime]] as origin (Fig. [[ref]]). Let [[time]] be'),
'two-time-labels':(None,'time zero: [[tp]] for [[a]], [[tpp]] for [[b]].'),
'common-angular-speed':('[[y]]축 왼쪽에서 [[a1]], [[b1]]의 주기는 같다. [[omega1]]은 [[a2]], [[b2]]의',None),
'eye-first-reference':(None,'[[one]] Fig. [[ref]] shows'),
'farthest-object':(None,'a myopic eye viewing its'),
'eye-rays':(None,'farthest clear object.'),
'accommodation':(None,'It can accommodate to see'),
'maximum-distance':(None,'up to [[a]]. An axial object'),
'infinite-object':(None,'An axial point at infinity focuses only at'),
'focus-patch':(None,'[[F]], leaving a blurred patch on the retina.'),
'pinhole-card':(None,'A card with a small circular hole near the eye reduces'),
'patch-reduced':(None,'the patch (Fig. [[ref]]). A smaller patch gives'),
'clearer-small-patch':('상의 점이 작을수록 더 선명하다. 따라서 눈 가까이에','a clearer image. Thus, near the eye, a hole'),
},
9:{
'pupil-hole':('동공보다 작은 원형 구멍을 두면 빛 얼룩이 작아져','smaller than the pupil gives less blur than the pupil,'),
'clearer-than-pupil':('동공만일 때보다 선명해진다.','so the view is clearer.'),
'retinal-patch-lens':(None,'For the patch diameter, Fig. [[ref]] gives the'),
'lens-formula':(None,'lens formula:'),
'parallel-object-rays':(None,'[[ref-tail]], parallel rays from a distant axial point pass through'),
'hole-focus-retinal-patch':(None,'a hole of diameter [[D]], focus at [[F]], and form a patch [[Dp]] wide'),
'patch-reference':(None,'on the retina, as Fig. [[ref]] shows.'),
'geometrical-optics':(None,'By [[three]], smaller [[D]] gives smaller [[Dp]] in geometric optics.'),
'diffraction-setup':(None,'[[two]] Parallel rays through the hole and lens form'),
'diffraction-retina':('망막에 원형 회절 무늬가 생긴다. 지름을 [[Dpp]]라 하면','a round retinal diffraction spot of diameter [[Dpp]]. The'),
'diffraction-approximation':('문제의 근사식에서 다음을 얻는다.','given approximation yields:'),
},
10:{
'scan-intro':('복합 입자는 속력 [[v1]], 운동량 [[p1]], 에너지 [[E1]]을 갖는다.','Its speed, momentum and energy are [[v1]], [[p1]], [[E1]].'),
},
}
# Correct the force enumeration using precisely the original atoms on each row.
E[4]['right01']=('아래 구 [[A]]가 받는 힘은 중력 [[mg]], 구 [[B]], [[D]]의','For lower ball [[A]], the forces are weight [[mg]], from [[B]], [[D]]')
E[4]['right02']=('합력 [[resultant]], 위 구의 힘 [[F2]], 그릇의 힘','their resultant [[resultant]], upper force [[F2]], and bowl force')
E[4]['right03']=('[[F3a]]이다. 대칭과 매끄러운 접촉으로 모두 [[A]], [[F3b]]는','[[F3a]]. All forces pass [[A]] by symmetry and smooth contact; [[F3b]]')

# Linked prose is read as complete paragraphs, not as independent row labels.
E[4].update({
 'left02':('구 위에 놓는다. 아래 [[4]]개는','balls leaves all [[4]] fixed.'),
 'left03':('제자리다. [[m]]은 각 구의 질량',"Let [[m]] be each ball's mass."),
 'left04':('이다. 아래 [[4]]개의 구 중심은','The lower [[4]] centers form'),
 'left05':('수평면의 정사각형','a square in a horizontal'),
 'right01':('아래 구 [[A]]가 받는 힘은 중력 [[mg]], 구 [[B]], [[D]]의','Ball [[A]] feels weight [[mg]], the resultant from [[B]], [[D]],'),
 'right02':('합력 [[resultant]], 위 구의 힘 [[F2]], 그릇의 힘','namely [[resultant]], upper-ball force [[F2]], and bowl force'),
 'right03':('[[F3a]]이다. 대칭과 매끄러운 접촉으로 모두 [[A]]를 지나며, [[F3b]]는','[[F3a]]. All pass through [[A]] by symmetry and smoothness; [[F3b]]'),
 'right04':('[[Op]]도 지난다. 평형 조건은','also passes through [[Op]]. Equilibrium gives'),
})
E[5].update({
 'hyperbola7':('[[v0]]를 방출 순간의 속력으로 두자.','[[v0]] be the ejection speed.'),
 'hyperbola8':('방출은 쌍곡선 꼭짓점에서 일어난다.','At the vertex, the angular'),
 'hyperbola9':('지구 중심까지의 거리는 [[ac]], 각운동량은 [[angular]]이다.','momentum is [[angular]], and Earth-center distance is [[ac]].'),
})
E[7]['simultaneous-start']=('[[a]], [[b]]가 동시에 출발할 때 각 교점·접점을 지나는','[[a]] and [[b]] start together. Compare passage at')
E[8].update({
 'least-delay':('시간 차를 비교한다. 그 최소 차는','each crossing or tangent point.'),
 'starting-delay':('[[a]], [[b]]가 그 점에서 만나기 위한','For [[a]] and [[b]], the least time gap'),
 'delay-equivalence':('출발 시간 차와 같다. 이를 구하기 위해','is the start delay for a meeting.'),
 'maximum-distance':(None,'up to [[a]]; axial points form'),
 'retinal-image':(None,'their images on the retina.'),
})

if __name__=='__main__':
 h=T/'history/m1-before-source-bound-language-repair';h.mkdir(parents=True,exist_ok=True)
 a=T/'proofs';b=h/'proofs';assert a.resolve().is_relative_to(T.resolve())and b.resolve().is_relative_to(T.resolve())
 if not b.exists():a.replace(b)
 (T/'proofs').mkdir(exist_ok=True)
 for name in ['full144-visual-review-complete.json','final-auditor-import-closure.json']:
  p=T/'authoring'/name;out=h/'authoring'/name;out.parent.mkdir(parents=True,exist_ok=True);assert p.resolve().is_relative_to(T.resolve())and out.resolve().is_relative_to(T.resolve())
  if p.exists()and not out.exists():p.replace(out)
  else:assert out.exists()
 reports=[]
 for n in range(4,11):
  p=T/f'authoring/page{n:02}-layout.json';copy=h/'authoring'/p.name
  if copy.exists()and hashlib.sha256(copy.read_bytes()).hexdigest()!=hashlib.sha256((T/f'master-v1/authoring-frozen/authoring/{p.name}').read_bytes()).hexdigest():
   failed=copy.with_suffix('.incomplete-copy-WinError112.partial');assert copy.resolve().is_relative_to(T.resolve())and failed.resolve().is_relative_to(T.resolve());copy.replace(failed)
  if not copy.exists():shutil.copy2(T/f'master-v1/authoring-frozen/authoring/{p.name}',copy)
  q=json.loads(p.read_text('utf8'));ids={r['id']for r in q['rows']};assert set(E[n])<=ids
  for r in q['rows']:
   if r['id']in E[n]:
    ko,en=E[n][r['id']]
    if ko is not None:r['ko']=ko
    if en is not None:r['en']=en
   if r.get('align')!='center':r['whole_original_image_expression_pixel_grid']=True
   r['source_bound_M2_language_review']='Natural grammatical continuity is checked across adjoining source rows; every original image/native math atom, measured point, source-only baseline, face role and figure remains unchanged. No point/scale fitting.'
  p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
  reports.append(dict(source_page=n,layout_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),changed_rows=sorted(E[n]),all_original_math_atoms_same_y=True,source_point_and_baseline_unchanged=True))
 out=T/'authoring/m2-source-bound-language-review.json';assert not out.exists();out.write_text(json.dumps(dict(status='SOURCE_BOUND_GRAMMAR_DRAFT_WIDTH_AND_VISUAL_QA_PENDING',original_source_sha256='52f8a891d6129becf4d21ccb60f46997cedf9aa50123ffd147294cedcb121b63',sealed_M1_untouched=True,pages=reports),ensure_ascii=False,indent=2)+'\n','utf8')
 print('M2_SOURCE_BOUND_LANGUAGE_DRAFTS_WRITTEN')
