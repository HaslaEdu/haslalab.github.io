// Public, blank answer-sheet metadata. Keep model answers and marking rules private.
export const PRESSURE_WAVE_SHEET_KEY = 'pressure-wave-experiment-v1';
export const PRESSURE_WAVE_SHEET_VERSION = '2026-11-pressure-wave-v1';
export const PRESSURE_WAVE_EXPERIMENT_URL = '/sim/monthly-pressure-wave/index.html';

export function isMonthlyPressureWaveProblem(problem) {
  if (!problem || typeof problem !== 'object' ||
      (problem.week || problem.period || problem.month) !== '2026-11' || Number(problem.no) !== 5) return false;
  return problem.answerSheet?.key === PRESSURE_WAVE_SHEET_KEY ||
    problem.source === 'HaslaLab · pressure-wave-experiment-v1' ||
    [problem.title_ko, problem.title_en, problem.title].some(title =>
      title === '압력파를 이용한 관의 내부 지름 측정' ||
      title === 'Measuring the internal diameter of a pipe with pressure waves');
}

const result = (label_ko, label_en, unit = '') => ({label_ko,label_en,...(unit ? {unit} : {})});
const column = (label_ko, label_en = label_ko) => ({label_ko,label_en});
const table = (title_ko,title_en,columns,rows) => ({title_ko,title_en,columns,rows});
const graph = (title_ko,title_en,x,y,heightMm = 70) => ({title_ko,title_en,x_label_ko:x,x_label_en:x,y_label_ko:y,y_label_en:y,columns:80,rows:Math.round(heightMm/2),heightMm});
const sensor = i => `$S_${i}$`;
const sensors = Array.from({length:8},(_,i) => sensor(i));
// These rows are available writing space, never a prescribed acquisition count.
const records = (title_ko,title_en,kind = 'RUN',includeFlow = false) => table(title_ko,title_en,
  [column(`${kind} ID`),...(includeFlow ? [column('$Q_0\\ (\\mathrm{L\\,s^{-1}})$')] : []),...sensors.map(s => column(s))],
  Array.from({length:5},() => []));

const parts = [
  {id:'A.1',label_ko:'압력 센서 보정',label_en:'Pressure-sensor calibration',points:10,workingLines:3,
    results:[result('$\\Delta r_i$에서 $P_i$를 구하는 식','Conversion from $\\Delta r_i$ to $P_i$')],
    tables:[
      records('기준압 $0.0\\,\\mathrm{kPa}$ · 표시값 $r_i$ ($\\mathrm{kPa}$)','Reference pressure $0.0\\,\\mathrm{kPa}$ · reading $r_i$ ($\\mathrm{kPa}$)','CAL'),
      records('기준압 $200.0\\,\\mathrm{kPa}$ · 표시값 $r_i$ ($\\mathrm{kPa}$)','Reference pressure $200.0\\,\\mathrm{kPa}$ · reading $r_i$ ($\\mathrm{kPa}$)','CAL'),
      table('센서 보정 계수와 표시값의 불확도','Calibration coefficients and reading uncertainties',
        [column('센서','Sensor'),column('$g_i$'),column('$b_i\\ (\\mathrm{kPa})$'),column('$u[r_i(0)]\\ (\\mathrm{kPa})$'),column('$u[r_i(200)]\\ (\\mathrm{kPa})$')],sensors.map(s => [s]))]},
  {id:'A.2',label_ko:'압력파의 속도',label_en:'Pressure-wave speed',points:15,workingLines:5,
    results:[result('$c$','$c$','$\\mathrm{m\\,s^{-1}}$'),result('$K$','$K$','$\\mathrm{Pa}$'),result('$t_{\\mathrm{off}}$','$t_{\\mathrm{off}}$','$\\mathrm{ms}$')],
    tables:[records('폐쇄 시간 $2\\,\\mathrm{ms}$ · 도달 시각 $t_i$ ($\\mathrm{ms}$)','Closure time $2\\,\\mathrm{ms}$ · arrival time $t_i$ ($\\mathrm{ms}$)','RUN',true)],
    graphs:[graph('도달 시각의 직선 맞춤 · 눈금과 단위 표시','Arrival-time fit · label scales and units','$x\\ (\\mathrm{m})$','$t\\ (\\mathrm{ms})$',70)]},
  {id:'B.1',label_ko:'직접파의 측정 구간',label_en:'Direct-wave measurement window',points:10,workingLines:4,
    results:[result('도달 시각 차 $\\Delta t(x)$','Arrival-time difference $\\Delta t(x)$'),result('$S_7$의 $\\Delta t$와 $\\tau$의 상한','$\\Delta t$ at $S_7$ and upper bound on $\\tau$','$\\mathrm{ms}$'),result('선택한 읽기 구간 / RUN ID','Selected reading window / RUN ID')],
    tables:[records('표시값 증가 $\\Delta r_i$ ($\\mathrm{kPa}$) · 사용한 RUN ID','Reading increase $\\Delta r_i$ ($\\mathrm{kPa}$) · source RUN ID'),
      table('보정된 압력 진폭','Corrected pressure amplitude',[column('센서','Sensor'),column('$P_i\\ (\\mathrm{kPa})$'),column('$u(P_i)\\ (\\mathrm{kPa})$'),column('불확도 평가 근거','Basis of uncertainty')],sensors.map(s => [s]))],
    graphs:[graph('$S_7$의 압력 기록 · 읽기 구간과 첫 반사파 도달 표시','$S_7$ pressure record · mark reading window and first reflection','$t\\ (\\mathrm{ms})$','$r\\ (\\mathrm{kPa})$',35)]},
  {id:'B.2',label_ko:'센서 위치의 내부 지름',label_en:'Internal diameter at sensor positions',points:20,workingLines:14,
    results:[result('$D_0$의 식','Expression for $D_0$'),result('$D_0$','$D_0$','$\\mathrm{mm}$'),result('$P(x)$와 $D(x)$의 관계','Relation between $P(x)$ and $D(x)$')],
    tables:[table('측정 지름','Measured diameter',[column('센서','Sensor'),column('$x\\ (\\mathrm{m})$'),column('$P_i\\ (\\mathrm{kPa})$'),column('$D_i\\ (\\mathrm{mm})$')],sensors.map((s,i) => [s,String(15*i)]))]},
  {id:'B.3',label_ko:'지름 함수의 결정',label_en:'Determining the diameter function',points:20,workingLines:8,
    results:[result('$D_0$','$D_0$','$\\mathrm{mm}$'),result('$a$','$a$'),result('$b$','$b$'),result('최종 $D(x)$ · 단위와 정의역','Final $D(x)$ · units and domain')],
    tables:[table('맞춤에 사용한 센서','Sensors used for the fit',[column('센서','Sensor'),column('$x\\ (\\mathrm{m})$'),column('측정 $D_i\\ (\\mathrm{mm})$','Measured $D_i\\ (\\mathrm{mm})$'),column('$D_{\\mathrm{fit}}\\ (\\mathrm{mm})$'),column('차이 ($\\mathrm{mm}$)','Difference ($\\mathrm{mm}$)')],[0,2,4,6].map(i => [sensor(i),String(15*i)]))],
    graphs:[graph('내부 지름 · 측정점과 맞춘 곡선을 구분','Internal diameter · distinguish measured points and fitted curve','$x\\ (\\mathrm{m})$','$D\\ (\\mathrm{mm})$',90)]},
  {id:'C.1',label_ko:'독립 센서로 검증',label_en:'Validation with held-out sensors',points:10,workingLines:13,
    results:[result('검증 RMS $\\eta$','Validation RMS $\\eta$'),result('$D(60.0\\,\\mathrm{m})$','$D(60.0\\,\\mathrm{m})$','$\\mathrm{mm}$'),result('$D(120.0\\,\\mathrm{m})$','$D(120.0\\,\\mathrm{m})$','$\\mathrm{mm}$')],
    tables:[table('맞춤에 사용하지 않은 센서','Sensors not used for the fit',[column('센서','Sensor'),column('$x\\ (\\mathrm{m})$'),column('측정 $D_i\\ (\\mathrm{mm})$','Measured $D_i\\ (\\mathrm{mm})$'),column('예측 $D_{\\mathrm{fit}}\\ (\\mathrm{mm})$','Predicted $D_{\\mathrm{fit}}\\ (\\mathrm{mm})$'),column('상대 차이','Relative difference')],[1,3,5,7].map(i => [sensor(i),String(15*i)]))],
    graphs:[graph('독립 센서의 상대 차이','Relative differences at held-out sensors','$x\\ (\\mathrm{m})$','$(D_{\\mathrm{fit}}-D_i)/D_i$',60)]},
  {id:'C.2',label_ko:'폐쇄 시간의 선택',label_en:'Choosing the closure time',points:15,workingLines:3,
    results:[result('$\\max|\\mathrm{d}\\ln A/\\mathrm{d}x|$','$\\max|\\mathrm{d}\\ln A/\\mathrm{d}x|$','$\\mathrm{m^{-1}}$'),result('$\\tau$의 허용 범위 / 선택한 $\\tau$','Allowed range / selected $\\tau$','$\\mathrm{ms}$'),result('검증 자료의 $D_0$, $a$, $b$','$D_0$, $a$, $b$ from validation data')],
    tables:[table('후보 조건 검토','Candidate closure conditions',[column('$\\tau\\ (\\mathrm{ms})$'),column('$\\varepsilon$'),column('반사파 조건','Reflection condition'),column('사용 가능','Usable')],[2,5,10,20,50].map(t => [String(t)])),
      records('검증 자료 · 새 RUN ID · $\\Delta r_i$ ($\\mathrm{kPa}$)','Validation data · fresh RUN ID · $\\Delta r_i$ ($\\mathrm{kPa}$)')],
    graphs:[graph('초기 함수와 검증 함수를 구분','Distinguish initial and validation functions','$x\\ (\\mathrm{m})$','$D\\ (\\mathrm{mm})$',50)]},
];

export function getPressureWaveAnswerSheet() {
  return JSON.parse(JSON.stringify({version:PRESSURE_WAVE_SHEET_VERSION,key:PRESSURE_WAVE_SHEET_KEY,limit:3,round:'experiment',experimentUrl:PRESSURE_WAVE_EXPERIMENT_URL,
    instructions_ko:'사용한 기록 ID와 측정 조건, 결과·불확도·분석 과정을 표와 그래프에 기록하세요. 표의 빈칸은 측정 횟수를 뜻하지 않습니다. 추가 용지에는 문제·소문항·쪽 번호를 표시하세요. CSV 내보내기는 자료 정리를 위한 선택 기능입니다.',
    instructions_en:'Record source IDs, conditions, results, uncertainties and analysis in the tables and plots. Blank rows do not prescribe the number of measurements. Label extra sheets with the problem, part and page number. CSV export is an optional data-management tool.',
    parts,pages:parts.map(p => [p.id])}));
}
