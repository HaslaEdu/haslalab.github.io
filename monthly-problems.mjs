// Public answer-sheet structure, shared by the website, printable form and grader.
// No model answers or private marking requirements belong in this module.
export const MONTHLY_ANSWER_LIMIT = 3;
export const MONTHLY_SHEET_VERSION = '2026-11-v1';

const part = (id, label_ko, label_en, points, workingLines = 8) => ({id, label_ko, label_en, points, workingLines});
const sheets = {
  4: {
    parts: [
      part('a', '정확한 운동방정식과 선형화', 'Exact equation of motion and linearization', 10),
      part('b', '분산관계', 'Dispersion relation', 13),
      part('c', '허용 파수와 최대 각진동수', 'Allowed wave numbers and maximum frequency', 10),
      part('d', '감쇠 구동의 복소진폭', 'Complex amplitude of the damped driven motion', 17),
      part('e', '평균 흡수 일률과 공명', 'Mean absorbed power and resonance', 10),
      part('f', '균일 전기장의 흡수 공명 판정', 'Absorption resonance for a uniform field', 7),
      part('g', '한 모드의 평균 에너지', 'Mean energy of one mode', 10),
      part('h', '파수 구간의 모드 수', 'Number of modes in a wave-number interval', 6),
      part('i', '모드 밀도와 전체 진동 에너지', 'Density of modes and total vibrational energy', 7),
      part('j', '고온 몰열용량과 가열 시간', 'High-temperature molar heat capacity and heating time', 10),
    ],
    pages: [['a','b','c'], ['d','e','f'], ['g','h','i'], ['j']],
  },
  5: {
    parts: [
      part('a', '고정 반원 벽의 출구 속력과 임계마찰', 'Exit speed and critical friction for the fixed wall', 15, 28),
      part('b', '마찰 없는 단일 충돌의 출사 속력과 편향각', 'Outgoing speed and deflection in one frictionless collision', 10, 28),
      part('c', '대칭 충돌열의 입사각·최종 상태·극한', 'Incidence angle, final state and limits of the symmetric collision sequence', 20, 28),
      part('d', '마찰·자전을 포함한 단일 충돌', 'One collision with friction and initial spin', 20, 28),
      part('e', '실제 배열에서의 점화식·최종 상태·임계값', 'Recurrence, final state and critical friction in the actual geometry', 35, 28),
    ],
    pages: [['a'], ['b'], ['c'], ['d'], ['e']],
  },
  6: {
    parts: [
      part('A.1', '페르마 원리와 광선 방정식', "Fermat's principle and the ray equation", 15),
      part('A.2', '매개변수 치환과 속도 정규화', 'Reparametrization and speed normalization', 15),
      part('A.3', '극좌표 방정식과 각운동량 보존', 'Polar equations and conservation of angular momentum', 15),
      part('B.1', '입사 광선의 각운동량', 'Angular momentum of the incoming ray', 10, 10),
      part('B.2', '비네 방정식', 'Binet equation', 15, 10),
      part('B.3', '약한 산란각과 미분 단면적', 'Weak deflection and differential cross-section', 20, 12),
      part('B.4', '역학·광학 대응과 전체 단면적', 'Mechanical–optical correspondence and total cross-section', 10, 12),
    ],
    pages: [['A.1','A.2','A.3'], ['B.1','B.2'], ['B.3','B.4']],
  },
  7: {
    parts: [
      part('16','현재 원판·구형의 복사 평형','Present radiative equilibrium of disk and sphere',14,12),
      part('17','천정거리와 세차 온도','Zenith angle and precessing temperature',16,12),
      part('18','최초 1 K 냉각 시각','First one-kelvin fall',19,20),
      part('19','세차 주기의 최저 온도','Minimum over a precession cycle',11,12),
      part('20a','원판의 두 대기층','Two atmospheric layers on a disk',7,14),
      part('20b','구형 모형의 대기층','Atmospheric layer on a sphere',7,14),
      part('20c','투과율에 대한 온도 민감도','Temperature sensitivity to transmission',7,10),
      part('21a','온도 개략도의 수치 읽기','Quantitative reading of the temperature schematic',5,10),
      part('21b','원판 모형과 기록의 정량 비교','Quantitative disk and record comparison',7,12),
      part('21c','전지구 흡수 일률과 세차 평균','Global absorbed flux and precession average',7,14),
    ],
    pages:[['16','17'],['18','19'],['20a','20b'],['20c','21a'],['21b','21c']],
  },
};

// These are blank response prompts, not a marking scheme. They specify what
// belongs in each result box while the canonical part IDs and page order stay fixed.
const result=(label_ko,label_en,unit='')=>({label_ko,label_en,...(unit?{unit}:{})});
const table=(title_ko,title_en,columns,rows)=>({title_ko,title_en,columns:columns.map(([label_ko,label_en])=>({label_ko,label_en})),rows});
const responseForms={
  4:{
    a:{results:[result('정확한 운동방정식','Exact equation of motion'),result('선형 운동방정식','Linearized equation of motion')]},
    b:{results:[result('분산관계 ω(q)','Dispersion relation ω(q)')]},
    c:{results:[result('허용 파수 q_s','Allowed q_s'),result('ω(0)','ω(0)','s⁻¹'),result('ω_max','ω_max','s⁻¹'),result('이웃 간 위상차','Phase between neighbours','rad')]},
    d:{results:[result('복소진폭 χ̃(q,ν)','Complex amplitude χ̃(q,ν)')]},
    e:{results:[result('입자 한 개의 평균 흡수 일률','Mean absorbed power per particle','W'),result('공명 구동 각진동수 ν','Resonant driving frequency ν','s⁻¹')]},
    f:{results:[result('유한한 양의 흡수 공명 유무','Finite positive absorption resonance'),result('판정에 사용한 식','Expression used for the decision')]},
    g:{results:[result('한 모드의 평균 에너지 E(ω,T)','Mean energy E(ω,T)','J')]},
    h:{results:[result('양·음의 파수 구간을 합한 모드 수','Mode count including positive and negative q')]},
    i:{results:[result('한 셀의 모드 밀도 g(ω)','Density of modes g(ω) per cell'),result('전체 진동 에너지의 적분 E_T(T)','Integral for total vibrational energy E_T(T)','J')]},
    j:{results:[result('고온 몰열용량 C_V','High-temperature molar heat capacity C_V','J mol⁻¹ K⁻¹'),result('가열 시간 t_12','Heating time t_12','s')]},
  },
  5:{
    a:{results:[result('출구 속력 v_e','Exit speed v_e','m s⁻¹'),result('임계 마찰계수 μ_c','Critical friction coefficient μ_c')]},
    b:{results:[result('출사 속력 v′','Outgoing speed v′','m s⁻¹'),result('편향각 δ (시계방향 +)','Deflection δ (clockwise positive)','rad')]},
    c:{results:[result('큰 입사각 θ','Larger incidence angle θ','rad'),result('최종 속력 v_f(N)','Final speed v_f(N)','m s⁻¹'),result('총편향각 δ_f(N)','Total deflection δ_f(N)','rad'),result('θ의 N → ∞ 극한','Limit of θ as N → ∞','rad'),result('v_f의 N → ∞ 극한','Limit of v_f as N → ∞','m s⁻¹'),result('δ_f의 N → ∞ 극한','Limit of δ_f as N → ∞','rad')]},
    d:{results:[result('출사 속력 v′','Outgoing speed v′','m s⁻¹'),result('출사 각속도 ω′ (반시계방향 +)','Outgoing spin ω′ (counterclockwise positive)','s⁻¹'),result('편향각 δ (시계방향 +)','Deflection δ (clockwise positive)','rad')]},
    e:{results:[result('최종 속도 벡터 v_f(N)','Final velocity vector v_f(N)','m s⁻¹'),result('총편향각 δ_f(N)','Total deflection δ_f(N)','rad'),result('임계 마찰계수 μ_c(N)','Critical friction coefficient μ_c(N)'),result('속도 벡터의 N → ∞ 극한','Velocity-vector limit as N → ∞','m s⁻¹'),result('δ_f의 N → ∞ 극한','Limit of δ_f as N → ∞','rad'),result('μ_c의 N → ∞ 극한','Limit of μ_c as N → ∞')]},
  },
  6:{
    'A.1':{results:[result('광선 방정식','Ray equation'),result('dl 매개변수의 정규화','Normalization for parameter dl')]},
    'A.2':{results:[result('s에 대한 운동방정식','Equation in parameter s'),result('|dr/ds|','|dr/ds|')]},
    'A.3':{results:[result('반지름 방향 방정식','Radial equation'),result('각도 방향 방정식','Angular equation'),result('보존량 L_z','Conserved L_z')]},
    'B.1':{results:[result('입사 광선의 |L_z|','Incoming ray |L_z|')]},
    'B.2':{results:[result('u(φ)의 비네 방정식','Binet equation for u(φ)')]},
    'B.3':{results:[result('산란각의 크기 θ','Scattering-angle magnitude θ','rad'),result('미분 단면적 dσ/dΩ','Differential cross-section dσ/dΩ'),result('근사 적용 범위','Approximation range')]},
    'B.4':{results:[result('사용한 정의·가정','Definitions and assumptions')],tables:[table('역학·광학 대응표','Mechanical–optical correspondence',[['물리량','Quantity'],['러더퍼드 산란','Rutherford scattering'],['굴절률장','Index field']],[
      {label_ko:'속도 (실제/매개변수)',label_en:'Speed (physical/parameter)'},{label_ko:'중심력 퍼텐셜',label_en:'Central potential'},{label_ko:'각운동량',label_en:'Angular momentum'},{label_ko:'전체 에너지',label_en:'Total energy'},{label_ko:'최소 접근거리',label_en:'Closest approach'},{label_ko:'산란각',label_en:'Scattering angle'},{label_ko:'전체 산란 단면적',label_en:'Total cross-section'},{label_ko:'미분 산란 단면적',label_en:'Differential cross-section'},
    ])]},
  },
  7:{
    '16':{results:[result('T₀의 식·수치','Expression and value of T₀','K'),result('T_g0의 식·수치','Expression and value of T_g0','K'),result('기하 인자 G_geom','Geometrical factor G_geom'),result('알베도 인자 G_alb','Albedo factor G_alb'),result('G_geom G_alb','G_geom G_alb'),result('온도 비 T₀/T_g0','Temperature ratio T₀/T_g0')]},
    '17':{results:[result('천정거리 z(ε_p,φ)','Zenith angle z(ε_p,φ)'),result('온도 T(T₀,ε_p,φ)','Temperature T(T₀,ε_p,φ)'),result('z의 최솟값·최댓값','Minimum and maximum of z','rad 또는 ° / rad or °')]},
    '18':{results:[result('최초 냉각 시간 Δt의 식','Expression for first cooling time Δt'),result('Δt의 수치','Numerical Δt','yr')]},
    '19':{results:[result('최저 온도 T_min','Minimum temperature T_min','K'),result('최대 온도 강하 T₀-T_min','Maximum fall T₀-T_min','K'),result('최저 온도의 최초 시각','First minimum time','yr')]},
    '20a':{results:[result('앞·뒷면 대기층 및 원판의 수지식','Budgets for both layers and the disk'),result('T_E(flat)의 식·수치','Expression and value of T_E(flat)','K')]},
    '20b':{results:[result('대기층·지표의 수지식','Budgets for the atmosphere and surface'),result('T_E(sph)의 식·수치','Expression and value of T_E(sph)','K')]},
    '20c':{results:[result('대기 인자 H_atm와 온도 비 R','Atmospheric factor H_atm and ratio R'),result('∂ln T / ∂t_sw','∂ln T / ∂t_sw'),result('∂ln T / ∂t_lw','∂ln T / ∂t_lw'),result('t_sw만 0.010 증가할 때 ΔT','ΔT when only t_sw increases by 0.010','K'),result('t_lw만 0.010 증가할 때 ΔT','ΔT when only t_lw increases by 0.010','K')]},
    '21a':{results:[result('그림에서 읽은 범위·근거','Intervals read from the figure')],tables:[table('온도 기록의 수치 읽기','Reading the temperature record',[['물리량','Quantity'],['읽은 값','Read value'],['단위','Unit']],[{label_ko:'대표 반복 간격 P_rec',label_en:'Repeat interval P_rec'},{label_ko:'온도 변동 폭 A_rec',label_en:'Temperature range A_rec'},{label_ko:'P_rec / (23 kyr)',label_en:'P_rec / (23 kyr)'}])]},
    '21b':{results:[result('두 통과 시각의 관계','Relation between the two crossing times')],tables:[table('원판 모형과 기록 비교','Disk model and record comparison',[['물리량','Quantity'],['계산값','Calculated value'],['단위','Unit']],[{label_ko:'기본 주기 P_disk',label_en:'Fundamental period P_disk'},{label_ko:'온도 변동 폭 A_disk',label_en:'Temperature range A_disk'},{label_ko:'t_c + t_w',label_en:'t_c + t_w'},{label_ko:'P_disk / P_rec',label_en:'P_disk / P_rec'},{label_ko:'A_disk / A_rec',label_en:'A_disk / A_rec'}])]},
    '21c':{results:[result('흡수 복사 플럭스 F_sph(φ)','Absorbed flux F_sph(φ)','W m⁻²'),result('흡수 복사 플럭스 F_disk(φ)','Absorbed flux F_disk(φ)','W m⁻²'),result('구·원판의 상대 변동 폭 m','Fractional ranges m for sphere and disk'),result('원판의 위상 평균','Disk phase average','W m⁻²'),result('위상 평균 / F_sph','Phase average / F_sph')]},
  },
};

export function getMonthlyAnswerSheet(problem) {
  const object = typeof problem === 'object' && problem !== null;
  const id = Number(object ? problem.id : problem);
  const greenhouse = object && (problem.week || problem.period || problem.month) === '2026-11' && Number(problem.no) === 4 &&
    (problem.answerSheet?.key === 'greenhouse-part-d-v1' || problem.source === '제공 자료 · Part D' ||
      [problem.title_ko,problem.title_en,problem.title].some(title => title === '원판 모형의 복사 평형과 세차' || title === 'Radiative equilibrium and precession of a disk'));
  if (object && id === 7 && !greenhouse) return null;
  const value = sheets[greenhouse ? 7 : id];
  if (!value) return null;
  return {
    version: MONTHLY_SHEET_VERSION,
    ...((greenhouse || !object && id === 7) ? {key:'greenhouse-part-d-v1'} : {}),
    limit: MONTHLY_ANSWER_LIMIT,
    round: value.round || 'theory',
    parts: value.parts.map((p,index) => ({...p,...JSON.parse(JSON.stringify(responseForms[greenhouse?7:id]?.[p.id]||{})),...(greenhouse || !object && id === 7 ? {displayId:String.fromCharCode(97+index)} : {})})),
    pages: value.pages.map(page => [...page]),
  };
}

// Round describes the problem; kind continues to select its grading method.
export function getMonthlyProblemRound(problem) {
  const defined=problem?.round || problem?.answerSheet?.round || getMonthlyAnswerSheet(problem)?.round;
  return defined === 'experiment' ? 'experiment' : 'theory';
}
