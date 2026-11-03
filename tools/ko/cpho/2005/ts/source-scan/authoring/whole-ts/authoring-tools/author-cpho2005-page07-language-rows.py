from pathlib import Path
import json
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS');rows=[];samples=[]
def row(id,hint,ko,en,sample,window):
 rows.append(dict(id=id,source_ocr_hint=hint,ko=ko,en=en))
 samples.append(dict(id=id,source_region='left'if window[0]<420 else'right',source_text=sample,source_measurement_window=window))
row('same-moles',3,'같으므로','are equal, so','数又相等',[66,66,118,84])
row('B-final',9,'[[A-final]], [[B-final]]의 최종 온도도 같다. [[B-state]]의 최종 상태','[[A-final]], [[B-final]]: same final temperature. For [[B-state]],','气体末态',[145,102,198,120])
row('state-equation',None,'방정식은','the final state equation is','程',[67,121,82,138])
row('equation-range',14,'식 [[eq7-12]]에서','From [[eq7-12]],','式得',[143,171,171,190])
row('substitution',24,'식 [[eq6]], [[eq13]]을 [[eq1]]에 대입하면','Substitute [[eq6]], [[eq13]] into [[eq1]]:','式代入',[131,234,172,252])
row('section-four',34,'4.','4.','四、',[93,286,117,305])
row('compression-first',37,'압축 중 판 [[P-plate]]에 외력 [[F-external]]가 가해져 쐐기 [[C-right]], [[D-right]]가 우측 이동해','During compression, force [[F-external]] on [[P-plate]] moves [[C-right]], [[D-right]] right,','在压缩阶',[92,302,145,322])
row('compression-second',39,'용수철 [[A-spring]], [[B-spring]]를 압축한다. 어느 순간 [[C-figure]]의 힘은 그림 [[fig1a]]와','compressing [[A-spring]], [[B-spring]]. Forces on [[C-figure]] at one instant: Fig. [[fig1a]]','在某一时',[169,322,222,341])
row('contact-forces',41,'같다. [[FA]], [[FP]], [[FQ]], [[FN]]은 각각 [[A-contact]], [[P-contact]], [[Q-contact]], [[N-contact]]이 [[C-contact]]에 가하는 힘의','[[FA]], [[FP]], [[FQ]], [[FN]]: contact forces on [[C-contact]] from [[A-contact]], [[P-contact]], [[Q-contact]], [[N-contact]].','分别表示',[209,339.5,262,360.5])
row('friction-forces',42,'크기이다. [[fN]][[fP]][[fQ]]는 각각 [[N-friction]], [[P-friction]], [[Q-friction]]가 [[C-friction]]에 가하는 운동 마찰력의','[[fN]][[fP]][[fQ]]: kinetic friction magnitudes on [[C-friction]] from [[N-friction]], [[P-friction]], [[Q-friction]],','分别表示',[138,359,191,378])
row('extra-compression',46,'크기이며 방향은 그림과 같다. [[dx1]], [[dx2]]는 용수철 [[A-extra]], [[B-extra]]의','Directions as shown. Extra compression of [[A-extra]], [[B-extra]]: [[dx1]], [[dx2]],','方向如图',[81,388,136,409])
row('before-impact',49,'충격 전보다 추가로 압축된 길이이다. 따라서','relative to values before impact. Then','未冲击时',[77,407,130,426])
row('caption',23,'그림 [[figure-one]]','Figure [[figure-one]]','图',[598,218,617,240])
row('massless',25,'문제에서 [[P-mass]], [[Q-mass]], [[C-mass]], [[D-mass]], [[A-mass]], [[B-mass]]의 질량은 영으로 보며, 가속도는','[[P-mass]], [[Q-mass]], [[C-mass]], [[D-mass]], [[A-mass]], [[B-mass]]: masses zero; finite acceleration.','质量均可',[622,237,676,257])
row('resultant',29,'무한할 수 없으므로 [[C-zero]]에 작용하는 [[seven]]개 힘의 합력은 영이다.','The resultant of the [[seven]] forces on [[C-zero]] must vanish.','不可能为',[438,257,491,275])
row('components',33,'수평·수직 방향으로 각각','Horizontally and vertically,','水平和竖',[451,275,504,293])
row('combine',40,'위 식들을 결합하면','Combining the equations gives','以上各式',[450,336,504,353])
row('recovery-first',53,'복원 중 쐐기는 왼쪽으로 움직이며 마찰력 방향은 압축','In recovery, wedges move left; friction is opposite','在恢复阶',[460,439,513,458])
row('recovery-second',56,'단계와 반대이다. 그림 [[fig1b]]의 힘으로부터','to that in compression. Forces in Fig. [[fig1b]] give','其受力情',[479,459,535,478])
for name,data in [('authoring/page07-language-row-proposals.json',dict(rows=rows,reviewed=False,scope='Manual bilingual source-line proposals. All original variables/counters/grade/figure numbers require native bitmap objects.')),
 ('page07-row-baseline-proposals.json',dict(rows=samples,scope='Explicit human-read CJK source measurement windows only, never erase regions.'))]:
 (B/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf8')
for old,new in [('calibrate-cpho2005-page06-per-row-type.py','calibrate-cpho2005-page07-per-row-type.py'),('calibrate-cpho2005-page06-row-weights.py','calibrate-cpho2005-page07-row-weights.py')]:
 if Path('D:/CodexBuilds',new).exists():continue
 s=Path('D:/CodexBuilds',old).read_text('utf8').replace('page06','page07').replace('source[5]','source[6]').replace('original[5]','original[6]').replace('page=6','page=7').replace("'section-three'","'section-four'").replace("'cooling-B'","'compression-first'")
 Path('D:/CodexBuilds',new).write_text(s,'utf8')
print('PAGE07_UNREVIEWED_LANGUAGE_AND_CJK_SAMPLES',len(rows),flush=True)
