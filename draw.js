/* The Workshop's figure and simulation editor (#/workshop/draw, draw.html in a frame). A figure is a scene
   (draw-scene.mjs): objects with values in SI units, drawn as an exam figure (draw-render.mjs) and run by the solver
   (draw-physics.mjs). Objects come from the palette or a template, are dragged on a grid and edited by value in the side
   panel. The figure goes out as SVG or PNG, onto the test paper of the problem maker (teach.js reads the paper from
   localStorage 'hlTeachPaper'; the figure is an SVG data URL with its scene), into the member's storage
   (/api/workshop/storage) or into this browser. "Start from a photo" sends one photo to /api/workshop/scene-from-image
   (community/src/workshop-scene.js) and opens what comes back for checking. */
import {validateScene, defaults, template, TEMPLATE_KEYS, TEMPLATE_NAMES, TEMPLATE_DOMAIN, FIELDS, DOMAINS, STYLE_KEYS, isBody, isRound, bodyPose, surfaceFrame, sceneBounds, vec, blankScene, MAX_OBJECTS, createHistory, rotCentre, ROTATABLE} from './draw-scene.mjs?v=89d7475e50e7';
import {buildSim, solveCircuit, computedInfo} from './draw-physics.mjs?v=38361b6fa4aa';
import {renderSVG, texSVG, STYLES, STYLE_TABLE, objectBox, printScale} from './draw-render.mjs?v=de4ee6724ac8';

const $ = id => document.getElementById(id), params = new URL(location.href).searchParams;
const embedded = params.get('embed') === '1' && window.parent !== window;
const lang = params.get('lang') === 'en' ? 'en' : 'ko', ko = lang === 'ko', dark = params.get('theme') === 'dark';
document.documentElement.lang = lang; document.documentElement.dataset.theme = dark ? 'dark' : 'light'; document.documentElement.classList.toggle('embedded', embedded);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const T = ko ? {
  title: '물리 그림·시뮬레이션', lede: '역학 문제 그림을 값으로 그립니다. 같은 그림을 시험지에 넣거나 시뮬레이션으로 돌려 볼 수 있습니다.',
  template: '템플릿', blank: '빈 그림', photo: '문제 사진으로 시작', undo: '되돌리기', redo: '다시 하기', dup: '복제', del: '삭제', grid: '격자', snap: '격자에 맞춤', fit: '화면에 맞추기',
  groups: {bodies: '물체', surfaces: '면 · 고정', links: '연결', marks: '표시'},
  types: {block: '상자', ball: '공', floor: '바닥', ceiling: '천장', wall: '벽', incline: '빗면', pulley: '도르래', pivot: '고정점', string: '줄', rod: '막대', spring: '용수철', force: '힘', label: '글자', dim: '치수선', arc: '각도 표시', axes: '좌표축', line: '보조선'},
  connect: {string: '줄: 한쪽 끝(물체나 고정점)을 누르고, 지나갈 도르래를 차례로 누른 뒤 다른 끝을 누르세요.', rod: '막대: 고정점을 누른 뒤 물체를 누르세요.', spring: '용수철: 두 끝(물체, 벽, 천장, 바닥, 고정점)을 차례로 누르세요.', force: '힘: 힘을 받을 물체를 누르세요.', esc: 'Esc로 취소'},
  play: '재생', pause: '일시정지', reset: '처음으로', speed: '속도', fbd: '힘 그림(자유물체도)', readouts: '측정값', time: '시간',
  stopped: '멈춤', events: {landed: id => `${id}이(가) 면에 닿았습니다`, reached_pulley: id => `${id}이(가) 도르래에 닿았습니다`, end_of_surface: id => `${id}이(가) 면 끝에 이르렀습니다`, lift_off: id => `${id}이(가) 면에서 떨어집니다`, slack: id => `줄 ${id}이(가) 느슨해졌습니다`, touched: id => `${id}이(가) 다른 물체에 닿았습니다`},
  unsupported: {hanging_not_vertical: '매달린 물체가 도르래 바로 아래에 있지 않습니다', tied_not_on_surface: '도르래 없이 이은 두 물체는 면 위에 있어야 합니다', spring_between_systems: '서로 다른 종류의 운동을 하는 물체를 용수철로 이었습니다', pivot_over_pulley: '고정점에서 도르래를 거치는 줄은 아직 계산하지 못합니다', pendulum_on_surface: '진자의 추가 면 위에 있습니다', pendulum_with_spring: '진자에 용수철이 달려 있습니다', zero_length: '줄의 길이가 0입니다', conical_angle: '원뿔 진자의 각도는 0°와 88° 사이여야 합니다', spring_surface_and_air: '면 위의 물체와 공중의 물체를 용수철로 이었습니다'},
  notSim: '이 부분은 계산하지 않습니다', nothing: '움직일 물체가 없습니다.',
  scene: '그림', sceneTitle: '그림 이름', g: '중력 가속도 g (m/s²)', gridSize: '격자 간격 (m)', objects: '그림에 있는 것', noSel: '그림에서 물체를 누르면 값을 고칠 수 있습니다.',
  fields: {x: 'x (m)', y: 'y (m)', w: '너비 (m)', h: '높이 (m)', r: '반지름 (m)', mass: '질량 (kg)', label: '이름표', on: '놓인 면', at: '면 위 위치 (m)', vx: '처음 속도 vx (m/s)', vy: '처음 속도 vy (m/s)', showV: '속도 화살표', vLabel: '속도 이름표', trail: '지나간 길 표시',
    mu: '마찰 계수 μ', hatch: '빗금', side: '단단한 쪽', angle: '각도 (°)', length: '빗면 길이 (m)', flip: '왼쪽으로 오르게', angleLabel: '각 이름표', mount: '붙은 곳', a: '한쪽 끝', b: '다른 끝', over: '지나는 도르래', mode: '운동', k: '용수철 상수 k (N/m)', L0: '자연 길이 (m)', coils: '감은 수',
    F: '힘의 크기 (N)', len: '화살표 길이 (m)', text: '글', size: '글자 크기', x1: 'x₁', y1: 'y₁', x2: 'x₂', y2: 'y₂', offset: '띄우기 (m)', from: '시작 각 (°)', to: '끝 각 (°)', lx: 'x축 길이', ly: 'y축 길이', xlabel: 'x축 이름', ylabel: 'y축 이름', dash: '점선'},
  enums: {left: '왼쪽', right: '오른쪽', normal: '보통', conical: '원뿔 진자'}, none: '(없음)',
  texHint: 'm_1, v_0^2, \\theta, \\vec{F}, \\dot{x}, \\frac{a}{b}, \\hbar 처럼 TeX로 쓰거나 Ω 단추로 기호를 넣으세요. 아래 미리보기가 그림에 들어가는 모양입니다.',
  out: '내보내기', svg: 'SVG 내려받기', png: 'PNG 내려받기 (2배)', toPaper: '시험지에 넣기', replacePaper: '시험지 그림 바꾸기', paperQ: '문제 글 (선택, 수식은 $...$)', inPaper: '시험지에 넣었습니다.', openPaper: '시험지 열기',
  store: '보관함에 저장', stored: n => `보관함 ‘${n}’ 폴더에 JSON과 SVG를 저장했습니다.`, storeLogin: '로그인하면 보관함에 저장할 수 있습니다. 지금은 이 브라우저에 저장하거나 파일로 내려받으세요.', login: '로그인', folder: '그림',
  local: '이 브라우저에 저장', localSaved: '이 브라우저에 저장했습니다.', open: '열기', json: 'JSON 내려받기', load: 'JSON 불러오기', loadBad: '이 파일은 그림 파일이 아니거나 값이 맞지 않습니다.', saves: '이 브라우저에 저장한 그림',
  reading: '사진을 읽는 중입니다. 30초쯤 걸립니다.', photoLogin: '사진으로 시작하려면 로그인하세요. AI는 하루 20번까지 씁니다.',
  aiNote: '사진에서 읽은 그림입니다. AI 인식은 틀릴 수 있으니 물체, 연결, 값을 하나씩 확인하고 고치세요.', aiUnsure: '확실하지 않은 것', left: n => `오늘 ${n}번 더 쓸 수 있습니다.`,
  unsure: {object: '빠졌거나 잘못 읽은 물체가 있을 수 있음', position: '위치', mass: '질량', angle: '각도', mu: '마찰 계수', k: '용수철 상수', length: '길이', connection: '연결', velocity: '속도', force: '힘', label: '이름표', value: '값'},
  err: {scene_limit: '오늘 사진으로 시작할 수 있는 횟수(20번)를 다 썼습니다.', not_mechanics: '역학 문제 그림을 찾지 못했습니다. 그림이 잘 보이게 다시 찍어 주세요.', no_figure: '사진에서 그림을 읽지 못했습니다.', image_too_large: '사진이 너무 큽니다.', bad_image: 'JPEG, PNG, WebP 사진만 됩니다.',
    ai_unavailable: 'AI를 지금 쓸 수 없습니다.', scene_failed: '사진을 읽지 못했습니다. 다시 시도해 주세요.', rate_limited: '잠시 뒤에 다시 시도해 주세요.', login_required: '로그인하세요.', network: '연결에 실패했습니다.', quota_exceeded: '보관함 용량이 모자랍니다.', other: '처리하지 못했습니다.'},
  invalid: '값이 범위를 벗어났습니다', tooMany: `물체는 ${MAX_OBJECTS}개까지 넣을 수 있습니다.`,
  rd: {body: '물체', x: 'x (m)', y: 'y (m)', v: '속력 (m/s)', a: '가속도 (m/s²)', tension: '장력', K: '운동 에너지', U: '위치 에너지', E: '역학적 에너지', heat: '마찰로 잃은 에너지', graph: '그래프', speedOf: id => `${id}의 속력`, yOf: id => `${id}의 높이`, xOf: id => `${id}의 x`, energy: '에너지', tensionOf: id => `장력 ${id}`}
} : {
  title: 'Physics figures and simulations', lede: 'Draw a mechanics figure by value. Put it on a test paper, or run the same figure as a simulation.',
  template: 'Template', blank: 'Blank figure', photo: 'Start from a photo', undo: 'Undo', redo: 'Redo', dup: 'Duplicate', del: 'Delete', grid: 'Grid', snap: 'Snap to grid', fit: 'Fit to view',
  groups: {bodies: 'Bodies', surfaces: 'Surfaces', links: 'Links', marks: 'Marks'},
  types: {block: 'Block', ball: 'Ball', floor: 'Floor', ceiling: 'Ceiling', wall: 'Wall', incline: 'Incline', pulley: 'Pulley', pivot: 'Pivot', string: 'String', rod: 'Rod', spring: 'Spring', force: 'Force', label: 'Text', dim: 'Dimension', arc: 'Angle mark', axes: 'Axes', line: 'Guide line'},
  connect: {string: 'String: click one end (a body or a pivot), then each pulley it goes over, then the other end.', rod: 'Rod: click the pivot, then the body.', spring: 'Spring: click its two ends (bodies, walls, ceilings, floors or pivots).', force: 'Force: click the body it acts on.', esc: 'Esc cancels'},
  play: 'Play', pause: 'Pause', reset: 'Reset', speed: 'Speed', fbd: 'Forces (free-body diagram)', readouts: 'Readouts', time: 'Time',
  stopped: 'Stopped', events: {landed: id => `${id} hit a surface`, reached_pulley: id => `${id} reached the pulley`, end_of_surface: id => `${id} reached the end of its surface`, lift_off: id => `${id} leaves its surface`, slack: id => `string ${id} went slack`, touched: id => `${id} touched another body`},
  unsupported: {hanging_not_vertical: 'a hanging body is not straight below its pulley', tied_not_on_surface: 'two bodies tied without a pulley must rest on surfaces', spring_between_systems: 'a spring joins bodies that move in different kinds of systems', pivot_over_pulley: 'a string from a pivot over pulleys is not computed yet', pendulum_on_surface: 'the pendulum bob rests on a surface', pendulum_with_spring: 'the pendulum has a spring', zero_length: 'the string has no length', conical_angle: 'a conical pendulum needs an angle between 0° and 88°', spring_surface_and_air: 'a spring joins a body on a surface and one in the air'},
  notSim: 'not computed', nothing: 'Nothing here can move.',
  scene: 'Figure', sceneTitle: 'Name', g: 'Gravity g (m/s²)', gridSize: 'Grid step (m)', objects: 'In the figure', noSel: 'Click an object in the figure to edit its values.',
  fields: {x: 'x (m)', y: 'y (m)', w: 'Width (m)', h: 'Height (m)', r: 'Radius (m)', mass: 'Mass (kg)', label: 'Label', on: 'Rests on', at: 'Position on it (m)', vx: 'Initial vx (m/s)', vy: 'Initial vy (m/s)', showV: 'Velocity arrow', vLabel: 'Velocity label', trail: 'Show its path',
    mu: 'Friction μ', hatch: 'Hatching', side: 'Solid side', angle: 'Angle (°)', length: 'Slope length (m)', flip: 'Rises to the left', angleLabel: 'Angle label', mount: 'Fixed to', a: 'One end', b: 'Other end', over: 'Over pulleys', mode: 'Motion', k: 'Spring constant k (N/m)', L0: 'Natural length (m)', coils: 'Coils',
    F: 'Magnitude (N)', len: 'Arrow length (m)', text: 'Text', size: 'Size', x1: 'x₁', y1: 'y₁', x2: 'x₂', y2: 'y₂', offset: 'Offset (m)', from: 'From (°)', to: 'To (°)', lx: 'x-axis length', ly: 'y-axis length', xlabel: 'x label', ylabel: 'y label', dash: 'Dashed'},
  enums: {left: 'Left', right: 'Right', normal: 'Normal', conical: 'Conical pendulum'}, none: '(none)',
  texHint: 'Write TeX such as m_1, v_0^2, \\theta, \\vec{F}, \\dot{x}, \\frac{a}{b}, \\hbar, or insert symbols with the Ω button. The preview is how the figure will show it.',
  out: 'Export', svg: 'Download SVG', png: 'Download PNG (2×)', toPaper: 'Put on the test paper', replacePaper: 'Replace the figure on the paper', paperQ: 'Problem text (optional, $...$ for maths)', inPaper: 'Added to the paper.', openPaper: 'Open the paper',
  store: 'Save to Storage', stored: n => `Saved the JSON and SVG in the “${n}” folder of your storage.`, storeLogin: 'Log in to save to your storage. For now, save in this browser or download the file.', login: 'Log in', folder: 'Figures',
  local: 'Save in this browser', localSaved: 'Saved in this browser.', open: 'Open', json: 'Download JSON', load: 'Open JSON', loadBad: 'This file is not a figure, or its values are out of range.', saves: 'Figures saved in this browser',
  reading: 'Reading the photo. This takes about 30 seconds.', photoLogin: 'Log in to start from a photo. The AI can be used 20 times a day.',
  aiNote: 'This figure was read from your photo. The AI can get things wrong: check each object, connection and value, and fix what is off.', aiUnsure: 'Not sure about', left: n => `${n} more today.`,
  unsure: {object: 'an object may be missing or misread', position: 'position', mass: 'mass', angle: 'angle', mu: 'friction coefficient', k: 'spring constant', length: 'length', connection: 'connection', velocity: 'velocity', force: 'force', label: 'label', value: 'value'},
  err: {scene_limit: 'You have used today\'s 20 photo starts.', not_mechanics: 'No mechanics figure was found. Take the photo again with the figure clearly visible.', no_figure: 'No figure could be read from the photo.', image_too_large: 'The photo is too large.', bad_image: 'Only JPEG, PNG and WebP photos.',
    ai_unavailable: 'The AI is not available right now.', scene_failed: 'The photo could not be read. Try again.', rate_limited: 'Try again in a moment.', login_required: 'Log in first.', network: 'Could not connect.', quota_exceeded: 'Your storage is full.', other: 'Something went wrong.'},
  invalid: 'value out of range', tooMany: `A figure can have up to ${MAX_OBJECTS} objects.`,
  rd: {body: 'Body', x: 'x (m)', y: 'y (m)', v: 'Speed (m/s)', a: 'Accel. (m/s²)', tension: 'Tension', K: 'Kinetic energy', U: 'Potential energy', E: 'Mechanical energy', heat: 'Lost to friction', graph: 'Graph', speedOf: id => `speed of ${id}`, yOf: id => `height of ${id}`, xOf: id => `x of ${id}`, energy: 'energy', tensionOf: id => `tension ${id}`}
};

/* ── the other domains: names, palette, symbol picker ── */
const X2 = ko ? {
  lede: '역학·전자기·열·광학·파동·현대물리 문제 그림을 값으로 그립니다. 그리스 문자와 물리 기호를 넣을 수 있고, 같은 그림을 시험지에 넣거나 시뮬레이션·계산으로 확인할 수 있습니다.',
  domains: {mech: '역학', em: '전자기', thermo: '열', optics: '광학', waves: '파동', modern: '현대물리', general: '일반'},
  search: '찾기 (예: 저항, lens, 우물)', style: '그림체', symbols: 'Ω 기호', symTitle: '그리스 문자 · 물리 기호', symHint: '누르면 선택한 글자 칸(없으면 새 글자)에 넣습니다. TeX로 직접 써도 됩니다.',
  solve: '회로 풀기 (전류·전압)', info: '계산값', circuit: '회로', noCircuit: {empty: '회로 소자가 없습니다.', ac: '교류 전원이 있는 회로는 풀지 않습니다.', short: '이상적인 전원이 단락되었거나 전압원 고리가 있어 풀 수 없습니다.'},
  tau: '시간 상수 τ', vFinal: '나중 전압', iFinal: '나중 전류', rth: '테브난 저항', charging: id => `${id} 충전 곡선 V(t)`, current: '전류', drop: '전압', element: '소자',
  infoT: {rails: c => `유도 기전력 ε = BLv = ${c.emf} V, 전류 I = ${c.I} A, 자기력 F = BIL = ${c.F} N`, buoyancy: c => `부력 ${c.B} N, 무게 ${c.W} N${c.floats < 1 ? `, 뜬다면 잠기는 비율 ${c.floats}` : ', 가라앉음'}`, bridge: c => `접점 위치 l = ${c.l} cm (평형: R/S = l/(100 − l))`,
    cycle: (c) => `W = ${c.W}, Q_in = ${c.Qin}, η = ${c.eta} (카르노 한계 ${c.carnot})`, oarrow: c => `상 위치 x = ${c.x} m, 배율 m = ${c.m} (${c.real ? '실상' : '허상'})`, slits: c => `무늬 간격 Δy = λL/d = ${c.dy}`, well: c => `E = ${c.E}${c.T !== undefined ? `, 투과율 T = ${c.T}` : ''}`, levels: c => c.trans, spacetime: c => `γ = ${c.gamma}`, curve: c => `일 W = ∫P dV = ${c.W}`},
  types: {element: '회로 소자', ground: '접지', charge: '점전하', plate: '대전판', fieldlines: '전기력선', field: '균일한 장', cwire: '전류 도선', current: '지면 수직 전류', solenoid: '솔레노이드', loop: '원형 전류 고리', magnet: '막대자석',
    cylinder: '실린더·피스톤', reservoir: '열원', engine: '열기관 도식', graph: '그래프 틀', curve: '곡선', cycle: '순환 과정', lens: '렌즈', mirror: '거울', prism: '프리즘', slab: '유리판', oarrow: '물체 (광학)', ray: '광선', slits: '슬릿·스크린', wavefront: '파면',
    wave: '파동', well: '퍼텐셜 우물', levels: '에너지 준위', phototube: '광전 효과 장치', spacetime: '민코프스키 도표', worldline: '세계선', frames: '관성계 S, S′', vector: '벡터', region: '영역', point: '점'},
  kinds: {wire: '도선', resistor: '저항', battery: '전지 (여러 칸)', cell: '전지', dc: '직류 전원', ac: '교류 전원', capacitor: '축전기', inductor: '코일 (인덕터)', switch: '스위치', diode: '다이오드', led: '발광 다이오드', bulb: '전구', ammeter: '전류계', voltmeter: '전압계', galvanometer: '검류계'},
  fields: {kind: '종류', value: '값', r: '반지름 / 내부 저항', closed: '닫힘', look: '모양', route: '꺾는 방향', q: '전하 (μC)', n: '개수', levels: '등전위선 수 / 준위 수', equip: '등전위선', arrows: '화살표', dir: '방향', mag: '세기 (T 또는 V/m)', spacing: '간격', pattern: '선 모양',
    I: '전류 (A)', rings: '자기장 고리', turns: '감은 수', core: '철심', showB: '자기장 표시', ccw: '반시계 방향', tilt: '기울기', piston: '피스톤 높이 (0–1)', gas: '기체 알갱이', weight: '추', heat: '열', hot: '고온', th: '고온 이름', tc: '저온 이름', qh: 'Q_H 이름', qc: 'Q_C 이름', wl: 'W 이름',
    xmin: 'x 최솟값', xmax: 'x 최댓값', ymin: 'y 최솟값', ymax: 'y 최댓값', auto: '범위 자동', ticks: '눈금', grid: '격자', origin: '원점 이름', graph: '그래프', expr: '식 y = f(x)', gamma: '비열비 γ', heads: '화살표', v1: 'V₁', v2: 'V₂', t1: '고온 T_H', t2: '저온 T_C', labels: '이름 표시', shade: '넓이 칠하기',
    f: '초점 거리 f (m)', face: '빛이 오는 쪽', showF: '초점 표시', apex: '꼭지각 (°)', rays: '주광선', image: '상', imageLabel: '상 이름', d: '슬릿 간격 d (mm)', L: 'L (m / nm)', lambda: '파장 λ (nm)', screen: '스크린까지 (그림)', waves: '입사파 표시',
    A: '진폭 A', phase: '위상 (°)', ends: '양 끝', showLambda: 'λ 표시', showA: 'A 표시', envelope: '포락선', axis: '축', arrow: '화살표', V0: 'V₀ (eV) / ħω', E: '입사 에너지 E (eV)', psi: '파동 함수', values: '준위 (eV, 쉼표)', trans: '전이 (예: 3-2)',
    units: '눈금 수', beta: 'β = v/c', primed: 'S′ 축', cone: '빛 원뿔', hyperbola: '불변 쌍곡선', diagram: '도표', x0: '시작 x', tau: '고유 시간 간격', gap: 'S′까지 거리', width: '굵기', head: '화살촉', shape: '모양', fill: '채우기', filled: '채움', box: '테두리', flip: '뒤집기', size: '크기', marks: '부호 표시'},
  enums: {B: '자기장 B', E: '전기장 E', in: '지면으로 들어감 ⊗', out: '지면에서 나옴 ⊙', arrow: '화살표', solid: '실선', dashed: '점선', dotted: '점점선', dashdot: '일점쇄선', none: '없음', auto: '그림체 따름', zigzag: '지그재그', box: '상자 (IEC)', straight: '곧게', hv: '가로 먼저', vh: '세로 먼저',
    func: '함수', isotherm: '등온', adiabat: '단열', isobar: '등압', isochore: '등적', mid: '가운데', end: '끝', start: '처음', both: '양쪽', carnot: '카르노', otto: '오토', stirling: '스털링', engine: '열기관', fridge: '냉동기',
    plane: '평면파', circular: '원형파', travel: '진행파', standing: '정상파', fixed: '고정', infinite: '무한 우물', finite: '유한 우물', harmonic: '조화 진동자', barrier: '장벽', step: '계단', psi: 'ψ', prob: '|ψ|²', hydrogen: '수소', custom: '직접 입력',
    rect: '사각형', ellipse: '타원', gray: '회색', hatch: '빗금', dots: '점', filled: '채운 삼각형', open: '열린 화살촉', stealth: '날렵한 화살촉'},
  units: {resistor: 'Ω', bulb: 'Ω', galvanometer: 'Ω', battery: 'V', cell: 'V', dc: 'V', ac: 'V', diode: 'V', led: 'V', capacitor: 'μF', inductor: 'H'}
} : {
  lede: 'Draw mechanics, electromagnetism, thermodynamics, optics, waves and modern-physics figures by value, with Greek letters and physics symbols. Put a figure on a test paper, or check it with a simulation or a calculation.',
  domains: {mech: 'Mechanics', em: 'E&M', thermo: 'Thermal', optics: 'Optics', waves: 'Waves', modern: 'Modern', general: 'General'},
  search: 'Search (e.g. resistor, lens, well)', style: 'Style', symbols: 'Ω Symbols', symTitle: 'Greek letters and physics symbols', symHint: 'Click to insert into the selected text field (or a new label). TeX can be typed too.',
  solve: 'Solve the circuit (currents, voltages)', info: 'Computed', circuit: 'Circuit', noCircuit: {empty: 'No circuit elements.', ac: 'Circuits with an AC source are not solved.', short: 'An ideal source is shorted or a loop of voltage sources makes it unsolvable.'},
  tau: 'Time constant τ', vFinal: 'Final voltage', iFinal: 'Final current', rth: 'Thevenin resistance', charging: id => `charging of ${id}, V(t)`, current: 'Current', drop: 'Voltage', element: 'Element',
  infoT: {rails: c => `motional EMF ε = BLv = ${c.emf} V, current I = ${c.I} A, force F = BIL = ${c.F} N`, buoyancy: c => `buoyancy ${c.B} N, weight ${c.W} N${c.floats < 1 ? `, would float with ${c.floats} submerged` : ', sinks'}`, bridge: c => `jockey at l = ${c.l} cm (balance: R/S = l/(100 − l))`,
    cycle: c => `W = ${c.W}, Q_in = ${c.Qin}, η = ${c.eta} (Carnot limit ${c.carnot})`, oarrow: c => `image at x = ${c.x} m, magnification m = ${c.m} (${c.real ? 'real' : 'virtual'})`, slits: c => `fringe spacing Δy = λL/d = ${c.dy}`, well: c => `E = ${c.E}${c.T !== undefined ? `, transmission T = ${c.T}` : ''}`, levels: c => c.trans, spacetime: c => `γ = ${c.gamma}`, curve: c => `work W = ∫P dV = ${c.W}`},
  types: {element: 'Circuit element', ground: 'Ground', charge: 'Point charge', plate: 'Charged plate', fieldlines: 'Field lines', field: 'Uniform field', cwire: 'Current wire', current: 'Current through the page', solenoid: 'Solenoid', loop: 'Current loop', magnet: 'Bar magnet',
    cylinder: 'Cylinder and piston', reservoir: 'Reservoir', engine: 'Heat engine diagram', graph: 'Graph frame', curve: 'Curve', cycle: 'Cycle', lens: 'Lens', mirror: 'Mirror', prism: 'Prism', slab: 'Slab', oarrow: 'Object (optics)', ray: 'Ray', slits: 'Slits and screen', wavefront: 'Wavefronts',
    wave: 'Wave', well: 'Potential well', levels: 'Energy levels', phototube: 'Photoelectric setup', spacetime: 'Minkowski diagram', worldline: 'Worldline', frames: 'Frames S, S′', vector: 'Vector', region: 'Region', point: 'Point'},
  kinds: {wire: 'Wire', resistor: 'Resistor', battery: 'Battery', cell: 'Cell', dc: 'DC source', ac: 'AC source', capacitor: 'Capacitor', inductor: 'Inductor', switch: 'Switch', diode: 'Diode', led: 'LED', bulb: 'Bulb', ammeter: 'Ammeter', voltmeter: 'Voltmeter', galvanometer: 'Galvanometer'},
  fields: {kind: 'Kind', value: 'Value', r: 'Radius / internal resistance', closed: 'Closed', look: 'Look', route: 'Route', q: 'Charge (μC)', n: 'Number', levels: 'Equipotentials / levels', equip: 'Equipotentials', arrows: 'Arrows', dir: 'Direction', mag: 'Strength (T or V/m)', spacing: 'Spacing', pattern: 'Line',
    I: 'Current (A)', rings: 'Field rings', turns: 'Turns', core: 'Iron core', showB: 'Show B', ccw: 'Anticlockwise', tilt: 'Tilt', piston: 'Piston height (0–1)', gas: 'Gas particles', weight: 'Weight', heat: 'Heat', hot: 'Hot', th: 'Hot label', tc: 'Cold label', qh: 'Q_H label', qc: 'Q_C label', wl: 'W label',
    xmin: 'x min', xmax: 'x max', ymin: 'y min', ymax: 'y max', auto: 'Auto range', ticks: 'Ticks', grid: 'Grid', origin: 'Origin label', graph: 'Graph', expr: 'Formula y = f(x)', gamma: 'Heat capacity ratio γ', heads: 'Arrows', v1: 'V₁', v2: 'V₂', t1: 'Hot T_H', t2: 'Cold T_C', labels: 'Labels', shade: 'Shade the area',
    f: 'Focal length f (m)', face: 'Light comes from', showF: 'Mark focal points', apex: 'Apex angle (°)', rays: 'Principal rays', image: 'Image', imageLabel: 'Image label', d: 'Slit spacing d (mm)', L: 'L (m / nm)', lambda: 'Wavelength λ (nm)', screen: 'To the screen (figure)', waves: 'Incident waves',
    A: 'Amplitude A', phase: 'Phase (°)', ends: 'Ends', showLambda: 'Mark λ', showA: 'Mark A', envelope: 'Envelope', axis: 'Axis', arrow: 'Arrow', V0: 'V₀ (eV) / ħω', E: 'Energy E (eV)', psi: 'Wave function', values: 'Levels (eV, commas)', trans: 'Transitions (e.g. 3-2)',
    units: 'Units', beta: 'β = v/c', primed: 'S′ axes', cone: 'Light cone', hyperbola: 'Invariant hyperbolas', diagram: 'Diagram', x0: 'Start x', tau: 'Proper-time step', gap: 'Distance to S′', width: 'Width', head: 'Arrowhead', shape: 'Shape', fill: 'Fill', filled: 'Filled', box: 'Box', flip: 'Flip', size: 'Size', marks: 'Signs'},
  enums: {B: 'Magnetic B', E: 'Electric E', in: 'Into the page ⊗', out: 'Out of the page ⊙', arrow: 'Arrows', solid: 'Solid', dashed: 'Dashed', dotted: 'Dotted', dashdot: 'Dash-dot', none: 'None', auto: 'From the style', zigzag: 'Zigzag', box: 'Box (IEC)', straight: 'Straight', hv: 'Horizontal first', vh: 'Vertical first',
    func: 'Function', isotherm: 'Isotherm', adiabat: 'Adiabat', isobar: 'Isobar', isochore: 'Isochore', mid: 'Middle', end: 'End', start: 'Start', both: 'Both', carnot: 'Carnot', otto: 'Otto', stirling: 'Stirling', engine: 'Engine', fridge: 'Refrigerator',
    plane: 'Plane', circular: 'Circular', travel: 'Travelling', standing: 'Standing', fixed: 'Fixed', infinite: 'Infinite well', finite: 'Finite well', harmonic: 'Harmonic oscillator', barrier: 'Barrier', step: 'Step', psi: 'ψ', prob: '|ψ|²', hydrogen: 'Hydrogen', custom: 'Custom',
    rect: 'Rectangle', ellipse: 'Ellipse', gray: 'Gray', hatch: 'Hatching', dots: 'Dots', filled: 'Filled', open: 'Open', stealth: 'Stealth'},
  units: {resistor: 'Ω', bulb: 'Ω', galvanometer: 'Ω', battery: 'V', cell: 'V', dc: 'V', ac: 'V', diode: 'V', led: 'V', capacitor: 'μF', inductor: 'H'}
};
/* the added elements, fields and editor tools */
const X3 = ko ? {
  types: {wheel: '바퀴 · 원통 · 고리', plank: '막대 · 판 (지레, 시소)', track: '곡면 궤도', bridge: '미터 브리지 · 전위차계', transformer: '변압기', rails: '레일과 움직이는 막대', container: '액체 그릇', utube: 'U자관', thermometer: '온도계', heater: '가열 장치',
    gasbox: '기체 분자 상자', screen: '스크린', eye: '눈', source: '광원', fiber: '광섬유', pulse: '펄스', interference: '두 파원 간섭', nucleus: '원자핵', particle: '입자 · 광자', panel: '그림 칸 (가)(나)', brace: '묶음 괄호', callout: '지시선', parrows: '나란한 화살표 (압력)'},
  kinds: {rheostat: '가변 저항', dielectric: '유전체 축전기'},
  fields: {rot: '회전 (°)', lw: '선 굵기 (배)', ls: '글자 크기 (배)', lock: '잠금 (끌지 않음)', look: '모양', omega: '회전 방향 ω', spokes: '바퀴살', len: '길이 (m)', thick: '두께 (m)', support: '받침', at: '위치 (0–1 / m)', R: '저항 (Ω) / R', scale: '눈금자', np: '1차 감은 수', ns: '2차 감은 수',
    v: '속도 v (m/s)', B: '자기장 B (T)', field: '자기장', level: '수면 높이 (0–1)', rho: '밀도 ρ (kg/m³)', open: '위가 열림', tube: '관 폭', left: '왼쪽 수면', right: '오른쪽 수면', seed: '배치 번호', xt: 'x 눈금 (값:이름, …)', yt: 'y 눈금 (값:이름, …)', data: '점 (x,y x,y …)', half: '반투명 (빔 분할기)',
    width: '폭 / 굵기', pos: '위치 (0–1)', shape: '모양', nodal: '마디선', nn: '중성자 수', caption: '칸 이름', frame: '테두리', end: '끝 모양'},
  enums: {cart: '수레', car: '자동차', disk: '원판 · 원통', ring: '고리', wheel: '바퀴', sphere: '구', shell: '구 껍질', ccw: '반시계', cw: '시계', fulcrum: '받침점 (삼각형)', pivot: '회전축', hinge: '경첩', wall: '벽 경첩', meter: '미터 브리지', pot: '전위차계', lines: '가로줄', cross: '격자 빗금', dark: '진한 회색',
    flame: '불꽃', coil: '전열선', plate: '전열판', bulb: '전구', laser: '레이저', point: '점광원', sun: '태양', gauss: '종 모양', tri: '삼각형', square: '사각형', right: '오른쪽', left: '왼쪽', electron: '전자', positron: '양전자', proton: '양성자', neutron: '중성자', alpha: '알파 입자', photon: '광자', neutrino: '중성미자', bracket: '꺾쇠', brace: '중괄호', dot: '점', points: '점 잇기'},
  tools: {back: '↶ 뒤로', fwd: '↷ 앞으로', backT: '되돌리기 (Ctrl+Z)', fwdT: '다시 하기 (Ctrl+Shift+Z, Ctrl+Y)', clear: '모두 지우기', cleared: '모두 지웠습니다. ‘↶ 뒤로’로 되돌릴 수 있습니다.', example: '처음에 예시 보여 주기', values: '값 표시',
    zoomIn: '확대', zoomOut: '축소', zoomFit: '전체 보기', zoomHint: 'Ctrl+휠·두 손가락으로 확대, 빈 곳을 끌면 여러 개 선택, Space+끌기로 이동', copy: '복사', paste: '붙여넣기', front: '맨 위로', backZ: '맨 아래로', lockAll: '잠금', unlockAll: '잠금 풀기',
    multi: n => `${n}개 선택됨`, align: '정렬', distribute: '고르게 놓기', aL: '왼쪽', aC: '가운데', aR: '오른쪽', aT: '위', aM: '가운데(세로)', aB: '아래', dH: '가로로', dV: '세로로', printW: '인쇄 폭 (mm, 0: 그림체 기본)', styleSrc: '그림체 근거', sliders: '값 조절', frameMark: '그림 범위', setFrame: '보이는 곳을 그림 범위로'}
} : {
  types: {wheel: 'Wheel, cylinder, ring', plank: 'Plank (lever, seesaw)', track: 'Curved track', bridge: 'Meter bridge, potentiometer', transformer: 'Transformer', rails: 'Rails and sliding rod', container: 'Liquid container', utube: 'U-tube', thermometer: 'Thermometer', heater: 'Heater',
    gasbox: 'Gas molecules box', screen: 'Screen', eye: 'Eye', source: 'Light source', fiber: 'Optical fibre', pulse: 'Pulse', interference: 'Two-source interference', nucleus: 'Nucleus', particle: 'Particle, photon', panel: 'Panel (a)(b)', brace: 'Brace', callout: 'Callout', parrows: 'Parallel arrows (pressure)'},
  kinds: {rheostat: 'Rheostat', dielectric: 'Capacitor with dielectric'},
  fields: {rot: 'Rotation (°)', lw: 'Line weight (×)', ls: 'Label size (×)', lock: 'Locked (no dragging)', look: 'Look', omega: 'Spin ω', spokes: 'Spokes', len: 'Length (m)', thick: 'Thickness (m)', support: 'Support', at: 'Position (0–1 / m)', R: 'Resistance (Ω) / R', scale: 'Scale', np: 'Primary turns', ns: 'Secondary turns',
    v: 'Velocity v (m/s)', B: 'Field B (T)', field: 'Field', level: 'Liquid level (0–1)', rho: 'Density ρ (kg/m³)', open: 'Open top', tube: 'Tube width', left: 'Left level', right: 'Right level', seed: 'Layout seed', xt: 'x ticks (value:label, …)', yt: 'y ticks (value:label, …)', data: 'Points (x,y x,y …)', half: 'Half-silvered (beam splitter)',
    width: 'Width', pos: 'Position (0–1)', shape: 'Shape', nodal: 'Nodal lines', nn: 'Neutrons', caption: 'Caption', frame: 'Frame', end: 'End'},
  enums: {cart: 'Cart', car: 'Car', disk: 'Disk, cylinder', ring: 'Ring', wheel: 'Wheel', sphere: 'Sphere', shell: 'Spherical shell', ccw: 'Anticlockwise', cw: 'Clockwise', fulcrum: 'Fulcrum', pivot: 'Pivot', hinge: 'Hinge', wall: 'Wall hinge', meter: 'Meter bridge', pot: 'Potentiometer', lines: 'Lines', cross: 'Cross-hatch', dark: 'Dark gray',
    flame: 'Flame', coil: 'Coil', plate: 'Hot plate', bulb: 'Bulb', laser: 'Laser', point: 'Point source', sun: 'Sun', gauss: 'Bell', tri: 'Triangle', square: 'Square', right: 'Right', left: 'Left', electron: 'Electron', positron: 'Positron', proton: 'Proton', neutron: 'Neutron', alpha: 'Alpha', photon: 'Photon', neutrino: 'Neutrino', bracket: 'Bracket', brace: 'Brace', dot: 'Dot', points: 'Data points'},
  tools: {back: '↶ Back', fwd: '↷ Forward', backT: 'Undo (Ctrl+Z)', fwdT: 'Redo (Ctrl+Shift+Z, Ctrl+Y)', clear: 'Clear all', cleared: 'Cleared. ‘↶ Back’ brings it back.', example: 'Show an example at first', values: 'Show values',
    zoomIn: 'Zoom in', zoomOut: 'Zoom out', zoomFit: 'Show all', zoomHint: 'Ctrl+wheel or two fingers to zoom, drag on empty space to select several, Space+drag to pan', copy: 'Copy', paste: 'Paste', front: 'To front', backZ: 'To back', lockAll: 'Lock', unlockAll: 'Unlock',
    multi: n => `${n} selected`, align: 'Align', distribute: 'Distribute', aL: 'Left', aC: 'Centre', aR: 'Right', aT: 'Top', aM: 'Middle', aB: 'Bottom', dH: 'Horizontally', dV: 'Vertically', printW: 'Print width (mm, 0: the style\'s)', styleSrc: 'What the style is based on', sliders: 'Adjust', frameMark: 'Figure frame', setFrame: 'Make the visible part the frame'}
};
Object.assign(X2.types, X3.types); Object.assign(X2.kinds, X3.kinds); Object.assign(X2.fields, X3.fields); Object.assign(X2.enums, X3.enums); Object.assign(X2.units, {rheostat: 'Ω', dielectric: 'μF'});
T.lede = X2.lede; Object.assign(T.types, X2.types); Object.assign(T.fields, X2.fields); Object.assign(T.enums, X2.enums);
T.err.not_mechanics = ko ? '물리 문제 그림을 찾지 못했습니다. 그림이 잘 보이게 다시 찍어 주세요.' : 'No physics figure was found. Take the photo again with the figure clearly visible.';
T.unsure = {...T.unsure, ...(ko ? {charge: '전하', kind: '종류', focal: '초점 거리'} : {charge: 'charge', kind: 'kind', focal: 'focal length'})};
/* the palette: [type, preset, name] by domain */
const K = X2.kinds, N2 = (k, e) => ko ? k : e;
const PALETTE = {
  mech: [...['block', 'ball', 'floor', 'incline', 'wall', 'ceiling', 'pulley', 'pivot', 'string', 'rod', 'spring', 'force'].map(t => [t, {}, T.types[t]]),
    ['block', {look: 'cart'}, N2('수레', 'Cart')], ['block', {look: 'car'}, N2('자동차', 'Car')], ['wheel', {kind: 'disk', omega: 'ccw'}, N2('원판 · 원통 (ω)', 'Disk, cylinder (ω)')], ['wheel', {kind: 'ring'}, N2('고리', 'Ring')], ['wheel', {kind: 'wheel', spokes: 6}, N2('바퀴', 'Wheel')],
    ['plank', {support: 'fulcrum'}, N2('시소 · 지레', 'Seesaw, lever')], ['plank', {support: 'hinge', at: 0}, N2('경첩 막대', 'Hinged rod')], ['plank', {support: 'none'}, N2('판 · 막대', 'Plank')], ['track', {from: 180, to: 270}, N2('곡면 경사로', 'Curved ramp')], ['track', {from: -90, to: 270}, N2('원형 궤도 (루프)', 'Loop')]],
  em: [...['wire', 'resistor', 'rheostat', 'battery', 'cell', 'dc', 'ac', 'capacitor', 'dielectric', 'inductor', 'switch', 'diode', 'led', 'bulb', 'ammeter', 'voltmeter', 'galvanometer'].map(k => ['element', {kind: k}, K[k]]),
    ['bridge', {kind: 'meter'}, N2('미터 브리지', 'Meter bridge')], ['bridge', {kind: 'pot'}, N2('전위차계 (접점)', 'Potentiometer (jockey)')], ['transformer', {}, T.types.transformer], ['rails', {}, T.types.rails],
    ['ground', {}, T.types.ground], ['charge', {q: 1}, N2('양전하 +q', 'Charge +q')], ['charge', {q: -1}, N2('음전하 −q', 'Charge −q')], ['plate', {}, T.types.plate], ['fieldlines', {}, T.types.fieldlines],
    ['field', {kind: 'B', dir: 'in'}, N2('자기장 ⊗', 'B field ⊗')], ['field', {kind: 'B', dir: 'out'}, N2('자기장 ⊙', 'B field ⊙')], ['field', {kind: 'E', dir: 'arrow', angle: -90, label: '\\vec{E}'}, N2('균일한 전기장', 'Uniform E field')],
    ['cwire', {}, T.types.cwire], ['current', {}, T.types.current], ['solenoid', {}, T.types.solenoid], ['loop', {}, T.types.loop], ['magnet', {}, T.types.magnet]],
  thermo: [['cylinder', {}, T.types.cylinder], ['container', {}, T.types.container], ['utube', {}, T.types.utube], ['thermometer', {}, T.types.thermometer], ['heater', {kind: 'flame'}, N2('가열 장치 (불꽃)', 'Burner')], ['heater', {kind: 'coil'}, N2('전열선', 'Heating coil')], ['gasbox', {}, T.types.gasbox], ['parrows', {dir: 'in', label: 'P'}, N2('압력 화살표', 'Pressure arrows')], ['reservoir', {}, T.types.reservoir], ['engine', {}, T.types.engine], ['graph', {xlabel: 'V', ylabel: 'P'}, N2('P–V 그래프', 'P–V graph')],
    ...['isotherm', 'adiabat', 'isobar', 'isochore'].map(k => ['curve', {kind: k}, T.enums[k]]), ['cycle', {kind: 'carnot'}, N2('카르노 순환', 'Carnot cycle')], ['cycle', {kind: 'otto'}, N2('오토 순환', 'Otto cycle')], ['cycle', {kind: 'stirling'}, N2('스털링 순환', 'Stirling cycle')]],
  optics: [['line', {pattern: 'dashdot'}, N2('광축', 'Optical axis')], ['lens', {f: 1}, N2('볼록 렌즈', 'Converging lens')], ['lens', {f: -1}, N2('오목 렌즈', 'Diverging lens')], ['mirror', {f: 0}, N2('평면 거울', 'Plane mirror')], ['mirror', {f: 1}, N2('오목 거울', 'Concave mirror')], ['mirror', {f: -1}, N2('볼록 거울', 'Convex mirror')],
    ['prism', {}, T.types.prism], ['slab', {}, T.types.slab], ['oarrow', {}, T.types.oarrow], ['ray', {}, T.types.ray], ['slits', {n: 1}, N2('단일 슬릿', 'Single slit')], ['slits', {n: 2}, N2('이중 슬릿', 'Double slit')], ['slits', {n: 6, d: 0.1, a: 0.02}, N2('회절격자', 'Grating')],
    ['wavefront', {kind: 'plane'}, N2('평면 파면', 'Plane wavefronts')], ['wavefront', {kind: 'circular'}, N2('원형 파면', 'Circular wavefronts')],
    ['mirror', {f: 0, half: true, rot: -45, showF: false}, N2('반투명 거울 (빔 분할기)', 'Half-silvered mirror (beam splitter)')], ['screen', {}, T.types.screen], ['eye', {}, T.types.eye], ['source', {kind: 'bulb'}, N2('광원 (전구)', 'Light source (bulb)')], ['source', {kind: 'laser'}, N2('레이저', 'Laser')], ['source', {kind: 'point'}, N2('점광원', 'Point source')], ['fiber', {}, T.types.fiber]],
  waves: [['wave', {kind: 'travel'}, N2('진행파', 'Travelling wave')], ['wave', {kind: 'standing', ends: 'fixed'}, N2('정상파 (고정단)', 'Standing wave (fixed ends)')], ['pulse', {}, T.types.pulse], ['interference', {}, T.types.interference], ['wavefront', {kind: 'circular'}, N2('원형 파면', 'Circular wavefronts')], ['wavefront', {kind: 'plane'}, N2('평면 파면', 'Plane wavefronts')]],
  modern: [['well', {kind: 'infinite'}, N2('무한 우물', 'Infinite well')], ['well', {kind: 'finite'}, N2('유한 우물', 'Finite well')], ['well', {kind: 'harmonic', V0: 0.5, levels: 4}, N2('조화 진동자', 'Harmonic oscillator')], ['well', {kind: 'barrier', L: 0.4, V0: 4, E: 2.5}, N2('퍼텐셜 장벽', 'Barrier')], ['well', {kind: 'step', V0: 3, E: 2}, N2('퍼텐셜 계단', 'Step')],
    ['levels', {}, T.types.levels], ['phototube', {}, T.types.phototube], ['spacetime', {}, T.types.spacetime], ['worldline', {}, T.types.worldline], ['frames', {}, T.types.frames],
    ['nucleus', {}, T.types.nucleus], ['particle', {kind: 'electron'}, N2('전자', 'Electron')], ['particle', {kind: 'photon'}, N2('광자 (물결 화살표)', 'Photon (wiggle)')], ['particle', {kind: 'alpha'}, N2('알파 입자', 'Alpha particle')], ['particle', {kind: 'proton'}, N2('양성자', 'Proton')], ['particle', {kind: 'neutron'}, N2('중성자', 'Neutron')]],
  general: [['label', {}, T.types.label], ['label', {box: true, text: '\\text{box}'}, N2('글 상자', 'Text box')], ['vector', {}, T.types.vector], ['dim', {}, T.types.dim], ['arc', {}, T.types.arc], ['axes', {}, T.types.axes],
    ['line', {pattern: 'dashed'}, N2('점선', 'Dashed line')], ['line', {pattern: 'dotted'}, N2('점점선', 'Dotted line')], ['line', {pattern: 'solid', heads: 'end'}, N2('화살표 선', 'Arrow line')], ['region', {}, T.types.region], ['region', {fill: 'hatch'}, N2('빗금 영역', 'Hatched region')], ['point', {}, T.types.point], ['graph', {}, N2('함수 그래프', 'Function graph')], ['curve', {kind: 'func'}, N2('함수 곡선', 'Function curve')],
    ['graph', {xlabel: 't', ylabel: 'v', grid: true, origin: '0'}, N2('v–t 그래프 (격자)', 'v–t graph (grid)')], ['curve', {kind: 'points', shade: true}, N2('꺾은선 (넓이 칠하기)', 'Polyline (shaded area)')], ['panel', {caption: '(가)'}, N2('그림 칸 (가)', 'Panel (a)')], ['panel', {caption: '(나)'}, N2('그림 칸 (나)', 'Panel (b)')],
    ['brace', {}, T.types.brace], ['callout', {}, T.types.callout], ['parrows', {}, T.types.parrows]]
};
const PAL_EN = {mech: 'block ball floor incline wall ceiling pulley pivot string rod spring force cart car wheel disk cylinder ring plank lever seesaw hinge track loop ramp', em: 'wire resistor rheostat battery cell dc ac capacitor dielectric inductor switch diode led bulb ammeter voltmeter galvanometer meter bridge potentiometer jockey transformer rails rod emf ground charge plate field lines B E current solenoid loop magnet', thermo: 'cylinder piston container liquid water buoyancy utube thermometer heater burner coil gas molecules pressure reservoir engine graph isotherm adiabat isobar isochore carnot otto stirling', optics: 'axis lens mirror prism slab object ray slit grating wavefront beam splitter half screen eye source laser bulb fiber', waves: 'wave standing travelling wavefront pulse interference', modern: 'well barrier step harmonic levels hydrogen photoelectric minkowski spacetime worldline frames nucleus particle electron photon alpha proton neutron', general: 'label text box vector dimension arc axes line dashed dotted arrow region hatch point graph function curve panel caption brace callout arrows'};
/* the symbol picker: [group, [[tex, shown-as], …]] */
const SYMBOLS = [
  [N2('그리스 소문자', 'Greek lower case'), 'alpha beta gamma delta epsilon varepsilon zeta eta theta vartheta iota kappa lambda mu nu xi pi varpi rho varrho sigma varsigma tau upsilon phi varphi chi psi omega'.split(' ').map(n => ['\\' + n])],
  [N2('그리스 대문자', 'Greek capitals'), 'Gamma Delta Theta Lambda Xi Pi Sigma Upsilon Phi Psi Omega'.split(' ').map(n => ['\\' + n])],
  [N2('벡터 · 미분 표기', 'Vectors and derivatives'), [['\\vec{F}'], ['\\hat{x}'], ['\\hat{n}'], ['\\dot{x}'], ['\\ddot{x}'], ['\\bar{v}'], ['\\tilde{x}'], ["x'"], ["x''"], ['\\overrightarrow{AB}'], ['\\mathbf{F}'], ['x_{1}'], ['x^{2}'], ['v_0^2'], ['\\frac{a}{b}'], ['\\sqrt{x}'], ['\\sqrt[3]{x}'], ['|\\vec{r}|']]],
  [N2('미적분 · 연산', 'Calculus and operators'), [['\\nabla'], ['\\partial'], ['\\int'], ['\\oint'], ['\\iint'], ['\\sum'], ['\\prod'], ['\\infty'], ['\\pm'], ['\\mp'], ['\\times'], ['\\cdot'], ['\\circ'], ['\\nabla\\times\\vec{B}'], ['\\nabla\\cdot\\vec{E}'], ['\\frac{dv}{dt}'], ['\\frac{\\partial f}{\\partial x}'], ['\\Delta x']]],
  [N2('관계', 'Relations'), [['\\approx'], ['\\neq'], ['\\le'], ['\\ge'], ['\\propto'], ['\\sim'], ['\\equiv'], ['\\ll'], ['\\gg'], ['\\simeq']]],
  [N2('양자 · 상대론', 'Quantum and relativity'), [['\\hbar'], ['\\ket{\\psi}'], ['\\bra{\\phi}'], ['\\braket{\\phi|\\psi}'], ['\\langle x \\rangle'], ['|\\psi|^2'], ['\\hat{H}'], ['\\mathcal{H}'], ['\\mathcal{L}'], ['\\gamma'], ['ct'], ["x'"], ["S'"], ['\\beta = v/c'], ['E = mc^2'], ['h\\nu'], ['e^-'], ['\\lambda_{dB}']]],
  [N2('기하 · 방향', 'Geometry and direction'), [['\\odot'], ['\\otimes'], ['\\perp'], ['\\parallel'], ['\\angle'], ['\\triangle'], ['\\to'], ['\\Rightarrow'], ['\\leftrightarrow'], ['\\rightleftharpoons'], ['\\uparrow'], ['\\downarrow'], ['\\circlearrowleft'], ['\\circlearrowright']]],
  [N2('전자기 · 단위', 'E&M and units'), [['\\mathcal{E}'], ['\\varepsilon_0'], ['\\mu_0'], ['\\Phi_B'], ['\\mathrm{\\Omega}'], ['\\mathrm{k\\Omega}'], ['\\mathrm{\\mu F}'], ['\\mathrm{mH}'], ['\\mathrm{\\mu C}'], ['\\mathrm{\\AA}'], ['30^\\circ'], ['\\mathrm{m/s^2}'], ['\\mathrm{N\\,m}'], ['\\mathrm{eV}'], ['\\mathrm{nm}'], ['\\mathrm{K}'], ['T_H'], ['T_C'], ['Q_H']]]
];

/* ── the member's session, as the other Workshop pages read it ── */
const API = (() => { let o = ''; try { o = localStorage.getItem('hlCmApi') || ''; } catch (e) {} return (/^https:\/\/[a-z0-9-]+\.haslalab\.workers\.dev\/?$/.test(o) ? o : 'https://haslalab-community-edge.haslalab.workers.dev').replace(/\/+$/, ''); })();
const token = () => { try { const v = localStorage.getItem('hlCmTok') || ''; return /^[A-Za-z0-9_-]{20,4096}$/.test(v) ? v : ''; } catch (e) { return ''; } };
async function api(path, method = 'GET', body, form) {
  let r;
  try { r = await fetch(API + path, {method, headers: {...(token() ? {Authorization: 'Bearer ' + token()} : {}), ...(body && !form ? {'content-type': 'application/json'} : {})}, body: form ? body : body ? JSON.stringify(body) : undefined}); }
  catch (e) { throw Object.assign(new Error('network'), {code: 'network'}); }
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw Object.assign(new Error(j.error || 'api ' + r.status), {code: j.error || 'other', status: r.status});
  return j;
}
const errText = e => T.err[e?.code] || T.err.other;
const store = {get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); return true; } catch (e) { return false; } }, del(k) { try { localStorage.removeItem(k); } catch (e) {} }};

/* ── state ── */
const SCENE_KEY = 'hlDrawScene', SAVES_KEY = 'hlDrawSaves', PAPER_KEY = 'hlTeachPaper', EDIT_KEY = 'hlDrawEdit', PREFS_KEY = 'hlDrawPrefs';
/* sel: the object whose values the panel shows; selection: every selected id (shift-click, a box drawn on empty space) */
const st = {scene: null, sel: '', selection: new Set(), hist: createHistory(250), connect: null, grid: true, snap: true, fbd: false, readouts: true, solve: false, circuit: null, dom: 'mech', q: '', lastText: null,
  sim: null, playing: false, speed: 1, last: 0, trails: new Map(), samples: [], graph: '', ai: null, msg: '', paperEdit: null, drag: null, zoom: null, clip: null, gesture: null, marquee: null, space: false};
const clone = o => JSON.parse(JSON.stringify(o));
/* the member's choice: open with an example figure or an empty one (an empty canvas once the example was cleared) */
const prefs = () => { try { const p = JSON.parse(store.get(PREFS_KEY) || '{}'); return p && typeof p === 'object' ? p : {}; } catch (e) { return {}; } };
const setPref = (k, v) => store.set(PREFS_KEY, JSON.stringify({...prefs(), [k]: v}));
const EXAMPLE = 'incline_pulley';
function startScene() {
  const t = params.get('t');
  if (t && TEMPLATE_KEYS.includes(t)) { st.dom = TEMPLATE_DOMAIN[t] || 'mech'; return validateScene(template(t, lang)).scene; }
  /* a figure sent from the paper to be changed (teach.js "그림 고치기") */
  try { const e = JSON.parse(store.get(EDIT_KEY) || 'null'); if (e && typeof e.key === 'string' && e.scene) { const r = validateScene(e.scene); if (r.ok) { st.paperEdit = e.key; store.del(EDIT_KEY); return r.scene; } } } catch (e) {}
  let saved = null;
  try { const r = validateScene(JSON.parse(store.get(SCENE_KEY) || 'null')); if (r.ok) saved = r.scene; } catch (e) {}
  if (saved && saved.objects.length) return saved;
  if (prefs().example === false) return saved || {...blankScene(), view: {x: -0.5, y: -0.5, w: 4, h: 3}};
  return validateScene(template(EXAMPLE, lang)).scene;
}
const byId = id => st.scene.objects.find(o => o.id === id);
const view = () => st.scene.view || (st.scene.view = sceneBounds(st.scene));
/* the part of the world the canvas shows: the figure's frame, or the zoomed part of it */
const dview = () => st.zoom || view();
const selIds = () => [...st.selection].filter(id => byId(id));
function setSel(ids, primary) { st.selection = new Set(ids.filter(Boolean)); st.sel = primary && st.selection.has(primary) ? primary : st.selection.size === 1 ? [...st.selection][0] : st.selection.size ? (st.selection.has(st.sel) ? st.sel : [...st.selection].pop()) : ''; }
/* every change goes through here: checked, kept for undo (one step), saved in this browser */
function commit(next, {keepSel = false, before = null} = {}) {
  const r = validateScene(next);
  if (!r.ok) { flash(`<span class="bad">${T.invalid}: ${esc(r.errors.map(e => (e.id ? e.id + '.' : '') + (e.field || e.code)).slice(0, 3).join(', '))}</span>`); return false; }
  st.hist.record(before || JSON.stringify(st.scene));
  st.scene = r.scene; if (!keepSel) setSel(selIds(), st.sel);
  if (!st.scene.objects.length && prefs().example !== false) setPref('example', false);
  stopSim(); save(); paint(); return true;
}
const save = () => store.set(SCENE_KEY, JSON.stringify(st.scene));
function restore(text) { st.scene = JSON.parse(text); setSel(selIds(), st.sel); stopSim(); save(); paint(); }
function undo() { const t = st.hist.undo(JSON.stringify(st.scene)); if (t) restore(t); }
function redo() { const t = st.hist.redo(JSON.stringify(st.scene)); if (t) restore(t); }
/* 모두 지우기: an empty figure in the same style and frame (one undo step); from then on the editor opens empty */
function clearAll() {
  const next = {...blankScene(), style: st.scene.style, view: st.scene.view, ...(st.scene.printW ? {printW: st.scene.printW} : {})};
  setSel([]); st.ai = null;
  if (commit(next)) { setPref('example', false); flash(esc(X3.tools.cleared)); }
}
let flashTimer;
function flash(html) { st.msg = html; const el = $('status'); if (el) el.innerHTML = html; clearTimeout(flashTimer); flashTimer = setTimeout(() => { st.msg = ''; status(); }, 6000); }

/* ids: the type's letter and the first free number */
const PREFIX = {wheel: 'wh', plank: 'pl', track: 'tr', bridge: 'BR', transformer: 'TR', rails: 'RL', container: 'ct', utube: 'ut', thermometer: 'th', heater: 'ht', gasbox: 'gb', screen: 'sc', eye: 'eye', source: 'src', fiber: 'fb', pulse: 'pu', interference: 'IF', nucleus: 'nu', particle: 'pa', panel: 'pn', brace: 'br', callout: 'co', parrows: 'ar',
  block: 'm', ball: 'b', floor: 'f', ceiling: 'c', wall: 'w', incline: 'i', pulley: 'p', pivot: 'o', string: 's', rod: 'r', spring: 'k', force: 'F', label: 'l', dim: 'd', arc: 'a', axes: 'x', line: 'n',
  element: 'e', ground: 'gnd', charge: 'q', plate: 'P', fieldlines: 'FL', field: 'B', cwire: 'I', current: 'J', solenoid: 'sol', loop: 'loop', magnet: 'mag', cylinder: 'cyl', reservoir: 'res', engine: 'eng', graph: 'G', curve: 'c', cycle: 'cyc',
  lens: 'L', mirror: 'M', prism: 'pr', slab: 'sl', oarrow: 'O', ray: 'ray', slits: 'S', wavefront: 'wf', wave: 'wave', well: 'W', levels: 'lv', phototube: 'pt', spacetime: 'st', worldline: 'wl', frames: 'fr', vector: 'v', region: 'rg', point: 'pt'};
const KIND_PREFIX = {rheostat: 'R', dielectric: 'C', wire: 'W', resistor: 'R', battery: 'E', cell: 'E', dc: 'E', ac: 'E', capacitor: 'C', inductor: 'L', switch: 'S', diode: 'D', led: 'D', bulb: 'B', ammeter: 'A', voltmeter: 'V', galvanometer: 'G'};
const freeId = (type, kind) => { const p = type === 'element' && KIND_PREFIX[kind] ? KIND_PREFIX[kind] : PREFIX[type] || 'o'; let n = 1; while (byId(p + n)) n++; return p + n; };
const snapV = v => st.snap ? Math.round(v / st.scene.grid) * st.scene.grid : v;
const r4 = v => Math.round(v * 1e4) / 1e4;

/* where a new object goes and how large it is: from the view, so it shows wherever the figure is */
function placeNew(type, preset, v, next) {
  const cx = snapV(v.x + v.w / 2), cy = snapV(v.y + v.h / 2), m = Math.min(v.w, v.h), o = {};
  const box = (fw, fh) => { const w = r4(snapV(v.w * fw)) || st.scene.grid, h = r4(snapV(v.h * fh)) || st.scene.grid; Object.assign(o, {x: r4(snapV(cx - w / 2)), y: r4(snapV(cy - h / 2)), w, h}); };
  const seg = frac => { const L = Math.max(st.scene.grid, r4(snapV(v.w * frac))); Object.assign(o, {x1: r4(snapV(cx - L / 2)), y1: cy, x2: r4(snapV(cx - L / 2) + L), y2: cy}); };
  if (type === 'floor' || type === 'ceiling') Object.assign(o, {x: snapV(v.x + v.w * 0.1), y: type === 'floor' ? snapV(v.y + v.h * 0.15) : snapV(v.y + v.h * 0.9), w: r4(snapV(v.w * 0.8))});
  else if (type === 'wall') Object.assign(o, {x: snapV(v.x + v.w * 0.1), y: snapV(v.y + v.h * 0.15), h: r4(snapV(v.h * 0.6))});
  else if (type === 'incline') Object.assign(o, {x: snapV(v.x + v.w * 0.15), y: snapV(v.y + v.h * 0.15), length: r4(snapV(Math.min(v.w * 0.6, v.h * 1.2)))});
  else if (type === 'dim' || type === 'line' || type === 'brace' || type === 'parrows') { seg(0.25); if (type === 'parrows') o.len = r4(m * 0.1); }
  else if (type === 'bridge' || type === 'fiber') { seg(type === 'bridge' ? 0.55 : 0.6); if (type === 'fiber') o.r = r4(m * 0.04); }
  else if (type === 'wheel') Object.assign(o, {x: cx, y: cy, r: r4(Math.max(0.02, m * 0.08))});
  else if (type === 'plank') Object.assign(o, {x: cx, y: cy, len: r4(snapV(v.w * 0.5)) || 1, thick: r4(Math.max(0.01, m * 0.025))});
  else if (type === 'track') Object.assign(o, {x: cx, y: cy, r: r4(m * 0.3)});
  else if (type === 'transformer') Object.assign(o, {x: cx, y: cy, h: r4(v.h * 0.4)});
  else if (type === 'rails') Object.assign(o, {x: r4(snapV(v.x + v.w * 0.15)), y: r4(snapV(cy - v.h * 0.18)), w: r4(snapV(v.w * 0.6)), h: r4(snapV(v.h * 0.35)) || 0.1, at: r4(snapV(v.w * 0.35))});
  else if (['container', 'utube', 'gasbox'].includes(type)) box(0.4, 0.45);
  else if (type === 'panel') box(0.45, 0.45);
  else if (type === 'thermometer') Object.assign(o, {x: cx, y: r4(snapV(cy - v.h * 0.2)), h: r4(v.h * 0.4)});
  else if (type === 'heater') Object.assign(o, {x: cx, y: cy, w: r4(m * 0.2)});
  else if (type === 'screen') Object.assign(o, {x: cx, y: cy, h: r4(v.h * 0.5)});
  else if (type === 'eye' || type === 'source') Object.assign(o, {x: cx, y: cy, size: r4(m * (type === 'eye' ? 0.12 : 0.1))});
  else if (type === 'pulse') Object.assign(o, {x: r4(snapV(v.x + v.w * 0.1)), y: cy, len: r4(snapV(v.w * 0.8)), A: r4(v.h * 0.12), width: r4(v.w * 0.12)});
  else if (type === 'interference') Object.assign(o, {x: cx, y: cy, d: r4(m * 0.25), lambda: r4(m * 0.08)});
  else if (type === 'nucleus') Object.assign(o, {x: cx, y: cy, r: r4(m * 0.08)});
  else if (type === 'particle') Object.assign(o, {x: cx, y: cy, len: r4(m * 0.2)});
  else if (type === 'callout') Object.assign(o, {x: cx, y: cy, x2: r4(snapV(cx + v.w * 0.15)), y2: r4(snapV(cy + v.h * 0.15)), text: 'A'});
  else if (type === 'element' || type === 'plate' || type === 'cwire' || type === 'vector') seg(type === 'element' ? 0.2 : 0.3);
  else if (['field', 'solenoid', 'cylinder', 'slab', 'region', 'phototube'].includes(type)) box(0.4, 0.4);
  else if (type === 'magnet') box(0.35, 0.1);
  else if (type === 'reservoir') box(0.4, 0.12);
  else if (type === 'graph' || type === 'well' || type === 'levels') box(0.6, 0.65);
  else if (type === 'engine') Object.assign(o, {x: cx, y: cy, size: r4(m * 0.22)});
  else if (type === 'spacetime') Object.assign(o, {x: cx, y: r4(snapV(v.y + v.h * 0.12)), size: r4(snapV(v.h * 0.7))});
  else if (type === 'frames') Object.assign(o, {x: r4(snapV(v.x + v.w * 0.15)), y: r4(snapV(v.y + v.h * 0.25)), size: r4(snapV(m * 0.35)), gap: r4(snapV(v.w * 0.4))});
  else if (type === 'lens' || type === 'mirror') Object.assign(o, {x: cx, y: cy, h: r4(v.h * 0.5), f: preset.f !== undefined ? r4(preset.f * v.w * 0.15) : r4(v.w * 0.15)});
  else if (type === 'oarrow') Object.assign(o, {x: r4(snapV(v.x + v.w * 0.15)), y: cy, h: r4(v.h * 0.15)});
  else if (type === 'ray') Object.assign(o, {x: r4(snapV(v.x + v.w * 0.08)), y: cy, len: r4(v.w * 1.2)});
  else if (type === 'slits') Object.assign(o, {x: r4(snapV(v.x + v.w * 0.25)), y: cy, h: r4(v.h * 0.6), screen: r4(v.w * 0.45)});
  else if (type === 'wave') Object.assign(o, {x: r4(snapV(v.x + v.w * 0.15)), y: cy, len: r4(snapV(v.w * 0.65)), A: r4(v.h * 0.12), lambda: r4(v.w * 0.22)});
  else if (type === 'wavefront') Object.assign(o, {x: cx, y: cy, spacing: r4(m * 0.06), h: r4(v.h * 0.5)});
  else if (type === 'charge') Object.assign(o, {x: cx, y: cy, r: r4(Math.max(0.02, m * 0.03))});
  else if (type === 'current') Object.assign(o, {x: cx, y: cy, r: r4(Math.max(0.02, m * 0.02))});
  else if (type === 'loop') Object.assign(o, {x: cx, y: cy, r: r4(m * 0.2)});
  else if (type === 'prism') Object.assign(o, {x: cx, y: r4(snapV(cy - m * 0.2)), size: r4(m * 0.45)});
  else if (type === 'arc') Object.assign(o, {x: cx, y: cy, r: r4(m * 0.1)});
  else if (type === 'axes') Object.assign(o, {x: cx, y: cy, lx: r4(m * 0.3), ly: r4(m * 0.3)});
  else if (type === 'curve' || type === 'cycle') {
    let g = next.objects.find(x => x.type === 'graph');
    if (!g) { g = {...defaults('graph'), id: freeId('graph'), ...(type === 'cycle' || preset.kind !== 'func' ? {xlabel: 'V', ylabel: 'P'} : {})}; Object.assign(g, placeNew('graph', {}, v, next)); next.objects.push(g); }
    o.graph = g.id;
    if (type === 'curve') Object.assign(o, preset.kind === 'func' || !preset.kind ? {x1: 0, x2: 6.2832} : {x1: 1, x2: 3, y1: 3, y2: 1});
  } else if (type === 'worldline') {
    let d = next.objects.find(x => x.type === 'spacetime');
    if (!d) { d = {...defaults('spacetime'), id: freeId('spacetime')}; Object.assign(d, placeNew('spacetime', {}, v, next)); next.objects.push(d); }
    o.diagram = d.id;
  } else if ('x' in FIELDS[type]) Object.assign(o, {x: cx, y: cy});
  return o;
}
function addObject(type, preset = {}) {
  if (st.scene.objects.length >= MAX_OBJECTS) { flash(`<span class="bad">${T.tooMany}</span>`); return; }
  if (['string', 'rod', 'spring', 'force'].includes(type)) {
    const sel = byId(st.sel);
    if (type === 'force' && isBody(sel)) { finishConnect({type: 'force', a: sel.id}); return; }
    st.connect = {type, a: null, over: []}; setSel([]); paint(); return;
  }
  const next = clone(st.scene), o = {...defaults(type), id: freeId(type, preset.kind)};
  Object.assign(o, placeNew(type, preset, dview(), next), Object.fromEntries(Object.entries(preset).filter(([k]) => !(k === 'f' && (type === 'lens' || type === 'mirror')))));
  if (type === 'mirror' && preset.f === 0) o.f = 0;
  if (type === 'block') o.label = `m_${o.id.slice(1)}`;
  if (type === 'label' && !o.text) o.text = 'A';
  if (type === 'element' && !o.label) o.label = {resistor: 'R', capacitor: 'C', inductor: 'L', battery: '\\mathcal{E}', cell: '\\mathcal{E}', dc: '\\mathcal{E}', ac: '\\mathcal{E}', bulb: '', switch: 'S'}[o.kind] || '';
  if (type === 'element') o.value = {battery: 12, cell: 1.5, dc: 6, ac: 10, capacitor: 100, inductor: 0.1, diode: 0.7, led: 2, resistor: 100, bulb: 10, galvanometer: 0}[o.kind] ?? o.value;
  next.objects.push(o);
  if (commit(next)) { setSel([o.id]); paint(); }
}
/* a click while a string, rod, spring or force is being joined */
function connectClick(o) {
  const c = st.connect;
  if (!o) return;
  if (c.type === 'force') { if (isBody(o)) finishConnect({type: 'force', a: o.id}); return; }
  const endOk = c.type === 'rod' ? (c.a ? isBody(o) : o.type === 'pivot') : c.type === 'string' ? isBody(o) || o.type === 'pivot' : isBody(o) || ['pivot', 'wall', 'ceiling', 'floor'].includes(o.type);
  if (!c.a) { if (endOk) c.a = o.id; }
  else if (c.type === 'string' && o.type === 'pulley') { if (!c.over.includes(o.id)) c.over.push(o.id); }
  else if (endOk && o.id !== c.a) { finishConnect({...c, b: o.id}); return; }
  status(); paintCanvas();
}
function finishConnect(c) {
  st.connect = null;
  const next = clone(st.scene), id = freeId(c.type), o = {...defaults(c.type), id};
  if (c.type === 'force') Object.assign(o, {on: c.a});
  else Object.assign(o, {a: c.a, b: c.b, ...(c.type === 'string' ? {over: c.over} : {})});
  if (c.type === 'spring') { const A = next.objects.find(x => x.id === c.a), B = next.objects.find(x => x.id === c.b), pa = isBody(A) ? bodyPose(next, A) : A, pb = isBody(B) ? bodyPose(next, B) : B; if (pa && pb && Number.isFinite(pa.x) && Number.isFinite(pb.x)) o.L0 = r4(Math.max(0.05, Math.hypot(pa.x - pb.x, pa.y - pb.y) * 0.8)); }
  next.objects.push(o);
  if (c.type === 'string') alignHanging(next, o);
  if (commit(next)) { setSel([id]); paint(); }
}
/* a body hanging from a pulley goes straight under the pulley's edge on its side */
function alignHanging(scene, s) {
  const ends = [[s.a, s.over[0]], [s.b, s.over[s.over.length - 1]]];
  ends.forEach(([bid, pid], i) => {
    const b = scene.objects.find(o => o.id === bid), p = scene.objects.find(o => o.id === pid);
    if (!isBody(b) || b.on || !p) return;
    const side = Math.sign(b.x - p.x) || (i === 0 ? -1 : 1);
    if (b.y < p.y) b.x = r4(p.x + side * p.r);
  });
}
function removeIds(scene, ids) {
  const gone = new Set(ids);
  for (let pass = 0; pass < 3; pass++) {
    scene.objects = scene.objects.filter(o => !gone.has(o.id));
    for (const o of scene.objects) {
      if (o.type === 'string') o.over = o.over.filter(p => !gone.has(p));
      if (['string', 'rod', 'spring'].includes(o.type) && (gone.has(o.a) || gone.has(o.b))) gone.add(o.id);
      if (o.type === 'force' && gone.has(o.on)) gone.add(o.id);
      if (isBody(o) && o.on && gone.has(o.on)) { const p = bodyPose({...scene, objects: [...scene.objects, ...st.scene.objects.filter(x => x.id === o.on)]}, o); o.on = ''; o.x = r4(p.x); o.y = r4(p.y); }
      if (o.type === 'pulley' && gone.has(o.mount)) o.mount = '';
      if ((o.type === 'curve' || o.type === 'cycle') && gone.has(o.graph)) gone.add(o.id);
      if (o.type === 'worldline' && gone.has(o.diagram)) gone.add(o.id);
    }
  }
}
function del() { const ids = selIds(); if (!ids.length) return; const next = clone(st.scene); removeIds(next, ids); setSel([]); commit(next); }
/* copy and paste: the selected objects, and the strings, springs, forces and curves among them; pasted a few grid
   steps away with fresh ids (references inside the copy follow it, a body keeps the surface it rests on) */
const LINKS = ['string', 'rod', 'spring', 'force', 'curve', 'cycle', 'worldline'];
function copySel() {
  const ids = new Set(selIds()); if (!ids.size) return false;
  for (const o of st.scene.objects) if (LINKS.includes(o.type) && !ids.has(o.id)) { const refs = refsOf(o); if (refs.length && refs.every(r => ids.has(r))) ids.add(o.id); }
  st.clip = st.scene.objects.filter(o => ids.has(o.id)).map(clone);
  try { sessionStorage.setItem('hlDrawClip', JSON.stringify(st.clip)); } catch (e) {}
  return true;
}
const refsOf = o => Object.entries(FIELDS[o.type]).flatMap(([k, f]) => f.k === 'ref' ? (o[k] ? [o[k]] : []) : f.k === 'refs' ? o[k] : []);
function pasteClip(offset = 3) {
  let clip = st.clip; if (!clip) { try { clip = JSON.parse(sessionStorage.getItem('hlDrawClip') || 'null'); } catch (e) { clip = null; } }
  if (!Array.isArray(clip) || !clip.length) return;
  if (st.scene.objects.length + clip.length > MAX_OBJECTS) { flash(`<span class="bad">${T.tooMany}</span>`); return; }
  const next = clone(st.scene), map = new Map(), d = st.scene.grid * offset, made = [];
  const taken = new Set(next.objects.map(o => o.id)), fresh = (type, kind) => { const p = type === 'element' && KIND_PREFIX[kind] ? KIND_PREFIX[kind] : PREFIX[type] || 'o'; let n = 1; while (taken.has(p + n)) n++; taken.add(p + n); return p + n; };
  for (const o of clip) map.set(o.id, fresh(o.type, o.kind));
  for (const o0 of clip) {
    const o = {...clone(o0), id: map.get(o0.id)};
    let ok = true;
    for (const [k, f] of Object.entries(FIELDS[o.type] || {})) {
      if (f.k === 'ref' && o[k]) { if (map.has(o[k])) o[k] = map.get(o[k]); else if (!byId(o[k]) || LINKS.includes(o.type)) { if (LINKS.includes(o.type)) ok = false; else o[k] = ''; } }
      if (f.k === 'refs') { if (o[k].some(x => !map.has(x) && !byId(x))) ok = false; o[k] = o[k].map(x => map.get(x) || x); }
    }
    if (!ok) continue;
    if (!LINKS.includes(o.type)) moveObj(o, d, -d, o0, map.has(o0.on));
    if (o.type === 'block' && /^m_\d+$/.test(o.label)) o.label = 'm_' + o.id.slice(1);
    next.objects.push(o); made.push(o.id);
  }
  if (commit(next)) { setSel(made); paint(); }
}
function dup() { if (copySel()) pasteClip(); }
/* move one object by (dx, dy) from its state `g`: a body on a surface slides along it (or keeps its place on a pasted
   surface), a segment moves both ends */
function moveObj(o, dx, dy, g = o, keepAt = false) {
  if (isBody(o) && g.on) { if (keepAt) return; const s = st.scene.objects.find(x => x.id === g.on); if (s) { const fr = surfaceFrame(s, st.scene); o.at = r4(g.at + vec.dot({x: dx, y: dy}, fr.u)); return; } }
  if ('x1' in g && 'x2' in g && !('x' in g)) { o.x1 = r4(g.x1 + dx); o.y1 = r4(g.y1 + dy); o.x2 = r4(g.x2 + dx); o.y2 = r4(g.y2 + dy); return; }
  if (o.type === 'callout') { o.x2 = r4(g.x2 + dx); o.y2 = r4(g.y2 + dy); }
  if ('x' in g) { o.x = r4(g.x + dx); o.y = r4(g.y + dy); }
}
/* align and distribute the selection by the boxes the figure draws them in */
function alignSel(how) {
  const ids = selIds().filter(id => !LINKS.includes(byId(id).type)); if (ids.length < 2) return;
  const next = clone(st.scene), boxes = ids.map(id => ({id, b: objectBox(st.scene, byId(id))})).filter(x => x.b);
  const L = Math.min(...boxes.map(x => x.b.x)), R = Math.max(...boxes.map(x => x.b.x + x.b.w)), B = Math.min(...boxes.map(x => x.b.y)), Tp = Math.max(...boxes.map(x => x.b.y + x.b.h));
  const mv = (id, dx, dy) => { const o = next.objects.find(x => x.id === id); moveObj(o, dx, dy, clone(o)); };
  if (how === 'dH' || how === 'dV') {
    const h = how === 'dH', list = [...boxes].sort((a, b) => h ? a.b.x + a.b.w / 2 - b.b.x - b.b.w / 2 : a.b.y + a.b.h / 2 - b.b.y - b.b.h / 2);
    if (list.length < 3) return;
    const c0 = h ? list[0].b.x + list[0].b.w / 2 : list[0].b.y + list[0].b.h / 2, c1 = h ? list.at(-1).b.x + list.at(-1).b.w / 2 : list.at(-1).b.y + list.at(-1).b.h / 2;
    list.forEach((x, i) => { const want = c0 + (c1 - c0) * i / (list.length - 1), now = h ? x.b.x + x.b.w / 2 : x.b.y + x.b.h / 2; mv(x.id, h ? want - now : 0, h ? 0 : want - now); });
  } else for (const {id, b} of boxes) {
    const dx = how === 'aL' ? L - b.x : how === 'aR' ? R - b.x - b.w : how === 'aC' ? (L + R) / 2 - b.x - b.w / 2 : 0;
    const dy = how === 'aB' ? B - b.y : how === 'aT' ? Tp - b.y - b.h : how === 'aM' ? (B + Tp) / 2 - b.y - b.h / 2 : 0;
    mv(id, dx, dy);
  }
  commit(next, {keepSel: true});
}
/* the order objects are drawn in (within their layer): to the end of the list is on top */
function zOrder(front) {
  const ids = new Set(selIds()); if (!ids.size) return;
  const next = clone(st.scene), picked = next.objects.filter(o => ids.has(o.id)), rest = next.objects.filter(o => !ids.has(o.id));
  next.objects = front ? [...rest, ...picked] : [...picked, ...rest]; commit(next, {keepSel: true});
}
function setAll(k, v) { const ids = new Set(selIds()); if (!ids.size) return; const next = clone(st.scene); for (const o of next.objects) if (ids.has(o.id) && k in FIELDS[o.type]) o[k] = v; commit(next, {keepSel: true}); }

/* ── the canvas ── */
const W = 800;
let shownScene = null, shownPoses = null;
function paintCanvas() {
  const box = $('canvas'); if (!box) return;
  const v = dview(), simOn = !!st.sim;
  const sc = simOn ? st.sim.applyTo(st.scene) : st.scene;
  let forces = null;
  if (st.fbd) { try { forces = (simOn ? st.sim : buildSim(st.scene)).forces(); } catch (e) { forces = null; } }
  shownScene = sc; shownPoses = simOn ? st.sim.poses() : null;
  st.circuit = st.solve && hasCircuit() ? solveCircuit(st.scene) : null;
  let svg = renderSVG(sc, {width: W, view: v, edit: true, grid: st.grid && !simOn, selected: simOn ? [] : selIds(), forces, poses: shownPoses, labelScale: screenLabelScale(box), circuit: st.circuit, marquee: st.marquee,
    velocities: simOn ? st.sim.velocities() : null, anchors: simOn ? st.sim.anchors : null, trails: simOn ? [...st.trails].filter(([id]) => byId(id)?.trail) : null,
    conical: (simOn ? st.sim : null)?.systems.filter(s => s.kind === 'conical').map(s => ({centre: s.centre, radius: s.radius})) || st.scene.objects.filter(o => (o.type === 'string' || o.type === 'rod') && o.mode === 'conical').map(o => conicalOrbit(o)).filter(Boolean)});
  /* zoomed: the figure's frame (what is exported) as a thin dashed box */
  if (st.zoom) { const f = view(), S = W / v.w, x = (f.x - v.x) * S, y = (v.y + v.h - f.y - f.h) * S; svg = svg.replace(/<\/svg>$/, `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${(f.w * S).toFixed(1)}" height="${(f.h * S).toFixed(1)}" fill="none" stroke="#d97706" stroke-width="1.2" stroke-dasharray="7 4" pointer-events="none" class="frame"/></svg>`); }
  box.innerHTML = svg;
  box.classList.toggle('connecting', !!st.connect); box.classList.toggle('panning', st.space);
  const z = $('zoomPct'); if (z) z.textContent = `${Math.round(100 * view().w / v.w)}%`;
}
/* labels on a narrow screen: the 800-px drawing is shown smaller, so its labels are drawn larger to stay readable */
function screenLabelScale(box) { const w = box.clientWidth || W; return Math.max(1, Math.min(2.4, 0.75 * W / Math.max(200, w - 14))); }
function conicalOrbit(s) {
  const P = [byId(s.a), byId(s.b)].find(o => o?.type === 'pivot'), b = [byId(s.a), byId(s.b)].find(isBody);
  if (!P || !b) return null; const p = bodyPose(st.scene, b);
  return {centre: {x: P.x, y: p.y}, radius: Math.abs(p.x - P.x)};
}
function worldAt(ev) {
  const svg = $('canvas').querySelector('svg'), r = svg.getBoundingClientRect(), v = dview(), H = svg.viewBox.baseVal.height;
  const px = (ev.clientX - r.left) * W / r.width, py = (ev.clientY - r.top) * H / r.height, S = W / v.w;
  return {x: v.x + px / S, y: v.y + v.h - py / S};
}
/* zoom by k about a world point (the frame's aspect kept, so the canvas does not change height) */
function zoomBy(k, at) {
  const v = dview(), f = view(), c = at || {x: v.x + v.w / 2, y: v.y + v.h / 2};
  let w = Math.max(f.w / 20, Math.min(f.w * 4, v.w / k)); const h = w * f.h / f.w;
  if (Math.abs(w - f.w) < f.w * 0.02 && Math.abs(c.x - (f.x + f.w / 2)) < f.w * 0.02 && !at) { st.zoom = null; paintCanvas(); return; }
  const rx = (c.x - v.x) / v.w, ry = (c.y - v.y) / v.h;
  st.zoom = {x: c.x - rx * w, y: c.y - ry * h, w, h}; paintCanvas();
}
function panBy(dx, dy) { const v = dview(); st.zoom = {x: v.x - dx, y: v.y - dy, w: v.w, h: v.h}; paintCanvas(); }
function pickAt(ev) { const g = ev.target.closest?.('[data-id]'); return g ? byId(g.dataset.id) : null; }
const NO_DRAG = ['string', 'rod', 'spring', 'force', 'curve', 'cycle', 'worldline', 'fieldlines'];
function bindCanvas() {
  const box = $('canvas'), pts = new Map();
  box.addEventListener('pointerdown', ev => {
    pts.set(ev.pointerId, {x: ev.clientX, y: ev.clientY});
    if (pts.size === 2) { const [a, b] = [...pts.values()]; st.drag = {pinch: true, d0: Math.hypot(a.x - b.x, a.y - b.y), v0: {...dview()}, mid: worldAt({clientX: (a.x + b.x) / 2, clientY: (a.y + b.y) / 2})}; st.marquee = null; return; }
    if (ev.button === 1 || (ev.button === 0 && st.space)) { st.drag = {pan: true, last: {x: ev.clientX, y: ev.clientY}}; box.setPointerCapture?.(ev.pointerId); ev.preventDefault(); return; }
    if (ev.button !== 0) return;
    const before = JSON.stringify(st.scene);
    const hd = ev.target.closest?.('[data-handle]'), hs = hd && byId(st.sel);
    if (hs && !st.connect && !hs.lock) { if (st.sim) stopSim(); st.drag = {id: hs.id, handle: +hd.dataset.handle, start: worldAt(ev), orig: clone(hs), before, moved: false}; box.setPointerCapture?.(ev.pointerId); return; }
    const rh = ev.target.closest?.('[data-rot]'), rs = rh && byId(st.sel);
    if (rs && !st.connect) { if (st.sim) stopSim(); const c = isBody(rs) ? bodyPose(st.scene, rs) : rotCentre(rs); st.drag = {id: rs.id, rot: true, c, before, moved: false}; box.setPointerCapture?.(ev.pointerId); return; }
    const o = pickAt(ev);
    if (st.connect) { connectClick(o); return; }
    if (st.sim) { stopSim(); paint(); }
    const add = ev.shiftKey || ev.ctrlKey || ev.metaKey;
    if (!o) {
      /* a box drawn on empty space selects what it touches */
      if (!add) setSel([]);
      st.drag = {marquee: true, start: worldAt(ev), keep: new Set(selIds()), moved: false}; box.setPointerCapture?.(ev.pointerId); paintCanvas(); paintSide(); status(); return;
    }
    if (add) { const ids = new Set(selIds()); ids.has(o.id) ? ids.delete(o.id) : ids.add(o.id); setSel([...ids], o.id); paint(); return; }
    if (!st.selection.has(o.id)) setSel([o.id]); else st.sel = o.id;
    paintCanvas(); paintSide(); status(); paintBar();
    const ids = selIds().filter(id => !NO_DRAG.includes(byId(id).type) && !byId(id).lock);
    if (!ids.length || (byId(o.id).lock && ids.length <= 1)) return;
    st.drag = ids.length > 1 ? {group: ids, origs: new Map(ids.map(id => [id, clone(byId(id))])), start: worldAt(ev), before, moved: false} : {id: o.id, start: worldAt(ev), orig: clone(o), before, moved: false};
    box.setPointerCapture?.(ev.pointerId);
  });
  box.addEventListener('pointermove', ev => {
    if (pts.has(ev.pointerId)) pts.set(ev.pointerId, {x: ev.clientX, y: ev.clientY});
    const d = st.drag; if (!d) return;
    if (d.pinch) { if (pts.size < 2) return; const [a, b] = [...pts.values()], dd = Math.hypot(a.x - b.x, a.y - b.y); if (dd > 10) { st.zoom = {...d.v0}; zoomBy(dd / d.d0, d.mid); } return; }
    if (d.pan) { const svg = box.querySelector('svg'), r = svg.getBoundingClientRect(), k = dview().w / r.width; panBy((ev.clientX - d.last.x) * k, -(ev.clientY - d.last.y) * k); d.last = {x: ev.clientX, y: ev.clientY}; return; }
    const p = worldAt(ev);
    if (d.marquee) {
      d.moved = true; st.marquee = {x0: d.start.x, y0: d.start.y, x1: p.x, y1: p.y};
      const x0 = Math.min(d.start.x, p.x), x1 = Math.max(d.start.x, p.x), y0 = Math.min(d.start.y, p.y), y1 = Math.max(d.start.y, p.y);
      const hits = st.scene.objects.filter(o => { const b = objectBox(st.scene, o); return b && b.x <= x1 && b.x + b.w >= x0 && b.y <= y1 && b.y + b.h >= y0 && !(b.x < x0 && b.x + b.w > x1 && b.y < y0 && b.y + b.h > y1); }).map(o => o.id);
      setSel([...d.keep, ...hits]); paintCanvas(); return;
    }
    if (d.rot) { const o = byId(d.id); if (!o) return; let a = Math.atan2(p.y - d.c.y, p.x - d.c.x) * 180 / Math.PI - 90; if (!ev.shiftKey) a = Math.round(a / 15) * 15; o.rot = r4(((a + 540) % 360) - 180); d.moved = true; paintCanvas(); return; }
    const dx = p.x - d.start.x, dy = p.y - d.start.y;
    if (!d.moved && Math.hypot(dx, dy) * W / dview().w < 3) return;
    d.moved = true;
    if (d.group) { const sx = st.snap ? snapV(dx) : dx, sy = st.snap ? snapV(dy) : dy; for (const id of d.group) { const o = byId(id); if (o) moveObj(o, sx, sy, d.origs.get(id)); } }
    else dragTo(d, p, dx, dy);
    paintCanvas();
  });
  const end = ev => {
    pts.delete(ev.pointerId);
    const d = st.drag; st.drag = null; if (!d) return;
    if (d.marquee) { st.marquee = null; paint(); return; }
    if (d.pan || d.pinch || !d.moved) return;
    const r = validateScene(st.scene);
    if (!r.ok) { st.scene = JSON.parse(d.before); paint(); return; }
    /* one step of history a drag */
    st.hist.record(d.before); st.scene = r.scene; save(); paint();
  };
  box.addEventListener('pointerup', end); box.addEventListener('pointercancel', end);
  box.addEventListener('wheel', ev => {
    if (ev.ctrlKey || ev.metaKey) { ev.preventDefault(); zoomBy(Math.exp(-ev.deltaY * 0.0022), worldAt(ev)); }
    else if (st.zoom) { ev.preventDefault(); const k = dview().w / (box.clientWidth || W); panBy((ev.shiftKey ? ev.deltaY : ev.deltaX) * k, (ev.shiftKey ? 0 : -ev.deltaY) * k); }
  }, {passive: false});
}
/* where a dragged object goes: a body slides along the surface it rests on, drops onto one it is put near, or leaves it
   when pulled away; a body hanging from a pulley moves up and down only */
function dragTo(d, p, dx, dy) {
  const o = byId(d.id), g = d.orig; if (!o) return;
  if (d.handle) {
    /* one end of a wire, an element, a line…: on the grid, or onto a terminal near it */
    let q = {x: r4(snapV(p.x)), y: r4(snapV(p.y))};
    const near = st.scene.objects.filter(x => x.id !== o.id && 'x1' in x && 'y2' in x).flatMap(x => [{x: x.x1, y: x.y1}, {x: x.x2, y: x.y2}]).find(t => Math.hypot(t.x - p.x, t.y - p.y) < Math.max(st.scene.grid * 0.6, 12 * dview().w / W));
    if (near) q = near;
    if (o.type === 'callout') { if (d.handle === 1) { o.x = q.x; o.y = q.y; } else { o.x2 = q.x; o.y2 = q.y; } return; }
    o['x' + d.handle] = q.x; o['y' + d.handle] = q.y; return;
  }
  if (isBody(o)) {
    const hanging = st.scene.objects.some(s => s.type === 'string' && s.over.length && (s.a === o.id || s.b === o.id)) && !g.on;
    if (g.on) {
      const fr = surfaceFrame(byId(g.on), st.scene), rel = vec.sub(p, fr.p0), off = vec.dot(rel, fr.n);
      if (off > -0.2 && off < 0.6 + (o.h || o.r || 0)) { o.on = g.on; o.at = r4(snapV(vec.dot(rel, fr.u))); placeOnFrame(o, fr); return; }
      o.on = ''; o.x = r4(snapV(p.x)); o.y = r4(snapV(p.y)); return;
    }
    if (hanging) { o.y = r4(snapV(g.y + dy)); return; }
    o.x = r4(snapV(g.x + dx)); o.y = r4(snapV(g.y + dy));
    const half = isRound(o) ? o.r : o.h / 2;
    /* resting places: floors, inclines and the tops of blocks (not its own, not one above it) */
    const above = id => { let b = byId(id); for (let k = 0; b && k < 8; k++) { if (b.id === o.id) return true; b = byId(b.on); } return false; };
    for (const s of st.scene.objects.filter(x => x.type === 'floor' || x.type === 'incline' || (x.type === 'block' && x.id !== o.id && !above(x.id)))) {
      const fr = surfaceFrame(s, st.scene), rel = vec.sub(o, fr.p0), along = vec.dot(rel, fr.u), off = vec.dot(rel, fr.n) - half;
      if (Math.abs(off) < 0.12 && along >= 0 && along <= fr.length) { o.on = s.id; o.at = r4(snapV(along)); o.rot = 0; placeOnFrame(o, fr); return; }
    }
    return;
  }
  if ('x1' in g && !('x' in g)) { o.x1 = r4(snapV(g.x1 + dx)); o.y1 = r4(snapV(g.y1 + dy)); o.x2 = r4(g.x2 + (o.x1 - g.x1)); o.y2 = r4(g.y2 + (o.y1 - g.y1)); return; }
  if ('x' in g) { o.x = r4(snapV(g.x + dx)); o.y = r4(snapV(g.y + dy)); if (o.type === 'callout') { o.x2 = r4(g.x2 + (o.x - g.x)); o.y2 = r4(g.y2 + (o.y - g.y)); } }
}
function placeOnFrame(o, fr) { const h = isRound(o) ? o.r : o.h / 2, c = vec.add(vec.add(fr.p0, vec.mul(fr.u, o.at)), vec.mul(fr.n, h)); o.x = r4(c.x); o.y = r4(c.y); }

/* ── the simulation ── */
function stopSim() { st.sim = null; st.playing = false; st.trails = new Map(); st.samples = []; }
function ensureSim() {
  if (st.sim) return st.sim;
  st.sim = buildSim(st.scene); st.trails = new Map(); st.samples = []; sample();
  return st.sim;
}
function play() {
  const sim = ensureSim();
  if (!sim.systems.length) { st.sim = null; flash(`<span class="bad">${T.nothing}</span>${sim.unsupported.length ? ' ' + esc(unsupportedText(sim)) : ''}`); return; }
  if (sim.done) { stopSim(); ensureSim(); }
  st.playing = true; st.last = performance.now(); requestAnimationFrame(frame); paintSimBar();
}
function pause() { st.playing = false; paintSimBar(); }
function frame(now) {
  if (!st.playing || !st.sim) return;
  const dt = Math.min(0.05, (now - st.last) / 1000) * st.speed; st.last = now;
  st.sim.run(dt); sample();
  if (st.sim.done) st.playing = false;
  paintCanvas(); paintReadouts(); paintSimBar(); status();
  if (st.playing) requestAnimationFrame(frame);
}
function sample() {
  const sim = st.sim; if (!sim) return;
  for (const [id, p] of sim.poses()) { if (!st.trails.has(id)) st.trails.set(id, []); const tr = st.trails.get(id), last = tr[tr.length - 1]; if (!last || Math.hypot(p.x - last.x, p.y - last.y) > 0.02) tr.push({x: p.x, y: p.y}); if (tr.length > 2000) tr.shift(); }
  const last = st.samples[st.samples.length - 1];
  if (!last || sim.t - last.t >= 0.02) { st.samples.push({t: sim.t, ...readNow()}); if (st.samples.length > 1500) st.samples.shift(); }
}
function readNow() {
  const sim = st.sim, poses = sim.poses(), vel = sim.velocities(), e = sim.energy(), out = {E: e.E, K: e.K, U: e.Ug + e.Us, tension: sim.tensions()};
  for (const [id, p] of poses) { const v = vel.get(id); out['x:' + id] = p.x; out['y:' + id] = p.y; out['v:' + id] = Math.hypot(v.x, v.y, v.z || 0); }
  return out;
}
const unsupportedText = sim => sim.unsupported.map(u => `${u.ids.join(', ')}: ${T.unsupported[u.code] || u.code}`).join(' · ');

/* ── side panel: the selected object's values, or the figure's ── */
const NUM_STEP = {mass: 0.1, angle: 1, mu: 0.05, k: 1, F: 1, size: 1, coils: 1, from: 5, to: 5, n: 1, levels: 1, turns: 1, rings: 1, units: 1, apex: 1, lambda: 10, beta: 0.05, gamma: 0.01, q: 0.5, t1: 10, t2: 10, value: 1, rot: 5, lw: 0.1, ls: 0.1, at: 0.05, level: 0.05, np: 1, ns: 1, spokes: 1, seed: 1, rho: 10, B: 0.05, v: 0.1, R: 1};
/* the main physical values get a slider beside their box: [min, max] in the field's unit (else from its range) */
const SLIDE = {mass: [0.1, 20], angle: [0, 89], mu: [0, 1], k: [1, 500], r: [0.02, 2], F: [0, 100], f: [-5, 5], lambda: [100, 900], q: [-10, 10], A: [0, 2], v: [-10, 10], B: [0, 2], at: [0, 1], level: [0, 1], rho: [100, 3000], V0: [0, 20], E: [0, 20], beta: [-0.95, 0.95], d: [0.01, 2], value: null, rot: [-180, 180], h: [0.1, 5], L: [0.1, 10], len: [0.1, 6], R: [0.1, 100], tilt: [0.05, 1], piston: [0.1, 0.95], gamma: [1.01, 2], apex: [10, 150], n: null};
const slideRange = (o, k, f) => {
  if (o.type === 'element' && k === 'value') return o.kind === 'capacitor' || o.kind === 'dielectric' ? [1, 1000] : ['battery', 'cell', 'dc', 'ac', 'diode', 'led'].includes(o.kind) ? [0, 24] : o.kind === 'inductor' ? [0.01, 2] : [1, 1000];
  if (o.type === 'incline' && k === 'angle') return [1, 89];
  if (o.type === 'slits' && k === 'lambda') return [380, 780];
  if (o.type === 'wave' && k === 'lambda') return [0.2, 5];
  if (o.type === 'interference' && k === 'lambda') return [0.05, 1.5];
  if ((o.type === 'lens' || o.type === 'mirror' || o.type === 'screen') && k === 'h') return [0.2, 4];
  if (k === 'h' || k === 'len' && o.type !== 'plank') return null;
  if (k === 'at') { if (isBody(o)) { const s2 = byId(o.on); return s2 ? [0, r4(surfaceFrame(s2, st.scene).length)] : null; } if (o.type !== 'plank' && o.type !== 'bridge') return null; }
  if (k === 'r' && !['wheel', 'ball', 'pulley', 'track', 'nucleus'].includes(o.type)) return null;
  const r = SLIDE[k]; if (!r) return null;
  return [Math.max(f.min, r[0]), Math.min(f.max, r[1])];
};
/* fields that mean nothing for this object as it is now set (a switch has no value, a function curve no γ …) */
function relevant(o, k) {
  if (o.type === 'element') {
    const K = o.kind;
    if (k === 'value') return !!X2.units[K];
    if (k === 'r') return ['battery', 'cell', 'dc'].includes(K);
    if (k === 'closed') return K === 'switch';
    if (k === 'look') return K === 'resistor';
    if (k === 'route') return K === 'wire';
  }
  if (o.type === 'field' && k === 'angle') return o.dir === 'arrow';
  if (o.type === 'curve') { if (k === 'data') return o.kind === 'points'; if (o.kind === 'points' && ['x1', 'x2', 'y1', 'y2', 'gamma', 'expr'].includes(k)) return false; if (k === 'expr') return o.kind === 'func'; if (k === 'gamma') return o.kind === 'adiabat'; if (k === 'y2') return o.kind === 'isochore'; if (k === 'x2') return o.kind !== 'isochore'; if (k === 'y1') return o.kind !== 'func'; }
  if (o.type === 'plank' && k === 'at') return o.support !== 'none';
  if (o.type === 'wheel' && k === 'spokes') return o.kind === 'wheel' || o.kind === 'disk';
  if (o.type === 'cycle' && k === 'gamma') return true;
  if (o.type === 'graph' && ['xmin', 'xmax', 'ymin', 'ymax'].includes(k)) return !o.auto;
  if (o.type === 'well') { if (k === 'E') return o.kind === 'barrier' || o.kind === 'step'; if (k === 'levels') return !['barrier', 'step'].includes(o.kind); if (k === 'L') return o.kind !== 'harmonic' && o.kind !== 'step'; }
  if (o.type === 'levels') { if (k === 'values') return o.kind === 'custom'; if (k === 'n') return o.kind === 'hydrogen'; }
  if (o.type === 'wave') { if (k === 'n') return o.kind === 'standing'; if (k === 'lambda' || k === 'phase' || k === 'arrow') return o.kind === 'travel'; if (k === 'envelope') return o.kind === 'standing'; }
  if (o.type === 'wavefront' && k === 'angle') return o.kind === 'plane';
  if (o.type === 'charge' && ['mass', 'vx', 'vy', 'showV', 'vLabel', 'trail'].includes(k)) return true;
  return true;
}
const fieldName = (o, k) => o.type === 'block' && k === 'mu' ? (ko ? '마찰 계수 μ (윗면)' : 'Friction μ (top face)') : o.type === 'element' && k === 'value' ? `${T.fields.value} (${X2.units[o.kind]})` : o.type === 'element' && k === 'r' ? (ko ? '내부 저항 (Ω)' : 'Internal resistance (Ω)') : o.type === 'element' && k === 'kind' ? T.fields.kind : T.fields[k] || k;
/* the leads that touch a bridge wire at its jockey move with it */
const jockey = b => ({x: b.x1 + (b.x2 - b.x1) * b.at, y: b.y1 + (b.y2 - b.y1) * b.at});
function followJockey(scene, J0, J1) { for (const e of scene.objects) if (e.type === 'element') for (const k of [1, 2]) if (Math.hypot(e['x' + k] - J0.x, e['y' + k] - J0.y) < 1e-6) { e['x' + k] = r4(J1.x); e['y' + k] = r4(J1.y); } }
/* which simulation and solver controls make sense for this figure */
const hasMech = () => st.scene.objects.some(o => isBody(o) || o.type === 'force' || o.type === 'spring');
const hasCircuit = () => st.scene.objects.some(o => o.type === 'element' || o.type === 'bridge');
function paintSide() {
  const box = $('props'); if (!box) return;
  const ids = selIds(), o = ids.length === 1 ? byId(ids[0]) : null;
  if (ids.length > 1) { paintMulti(box, ids); return; }
  if (!o) {
    const sk = st.scene.style, t = STYLE_TABLE[sk], pr = prefs();
    box.innerHTML = `<h2>${T.scene}</h2><div class="props"><label class="wide">${T.sceneTitle}<input data-scene="title" maxlength="80" value="${esc(st.scene.title)}"></label>
      <label class="wide">${X2.style}<select data-scene="style">${STYLE_KEYS.map(k => `<option value="${k}"${k === sk ? ' selected' : ''}>${esc(STYLES[k].name[lang])}</option>`).join('')}</select></label>
      ${hasMech() ? `<label>${T.g}<input data-scene="g" type="number" step="0.1" value="${st.scene.g}"></label>` : ''}<label>${T.gridSize}<input data-scene="grid" type="number" step="0.05" value="${st.scene.grid}"></label>
      <label class="wide">${X3.tools.printW}<input data-scene="printW" type="number" min="0" max="400" step="5" value="${st.scene.printW || 0}"></label>
      <label class="chk wide"><input type="checkbox" data-scene="values"${st.scene.values ? ' checked' : ''}>${X3.tools.values}</label>
      <label class="chk wide"><input type="checkbox" id="prefExample"${pr.example !== false ? ' checked' : ''}>${X3.tools.example}</label></div>
      <details class="stylesrc"><summary>${X3.tools.styleSrc}</summary><p class="note">${esc(t.source)}${t.n ? ` · n = ${t.n}` : ''} · ${ko ? '그림 폭' : 'figure width'} ${t.widthPt} pt · ${ko ? '글자' : 'labels'} ${t.labelPt} pt · ${ko ? '선' : 'lines'} ${t.thin}/${t.main}/${t.thick} pt${t.gray != null ? ` · ${ko ? '회색' : 'gray'} ${t.gray}` : ''}${t.est.length ? ` · ${ko ? '추정' : 'estimated'}: ${t.est.join(', ')}` : ''}${!t.n ? ` · ${ko ? '실측 자료 없음 (가정)' : 'no measured source (assumed)'}` : ''}</p></details>
      <p class="note">${T.noSel}</p><div class="note">${T.objects}</div><div class="olist">${st.scene.objects.map(x => `<button type="button" data-pick="${esc(x.id)}">${esc(x.id)} · ${esc(x.type === 'element' ? X2.kinds[x.kind] : T.types[x.type])}</button>`).join('')}</div>`;
    box.querySelectorAll('[data-scene]').forEach(el => el.onchange = () => {
      const next = clone(st.scene), k = el.dataset.scene;
      if (k === 'values') next.values = el.checked; else if (k === 'printW') { const v = parseFloat(el.value); if (v > 0) next.printW = Math.max(20, Math.min(400, v)); else delete next.printW; }
      else next[k] = k === 'title' || k === 'style' ? el.value : parseFloat(el.value);
      commit(next);
    });
    $('prefExample').onchange = e => setPref('example', e.target.checked);
    box.querySelectorAll('[data-pick]').forEach(b => b.onclick = () => { setSel([b.dataset.pick]); paint(); });
    return;
  }
  const F = FIELDS[o.type], fields = Object.entries(F).filter(([k]) => !(isBody(o) && o.on && (k === 'x' || k === 'y' || k === 'rot')) && !(isBody(o) && !o.on && k === 'at') && !(o.type === 'block' && k === 'mu' && !st.scene.objects.some(x => x.on === o.id)) && relevant(o, k));
  const opts = (types, cur, optional) => (optional ? `<option value="">${T.none}</option>` : '') + st.scene.objects.filter(x => types.includes(x.type) && x.id !== o.id).map(x => `<option value="${esc(x.id)}"${x.id === cur ? ' selected' : ''}>${esc(x.id)} · ${T.types[x.type]}</option>`).join('');
  const optional = k => !(['string', 'rod', 'spring'].includes(o.type) && (k === 'a' || k === 'b')) && !(o.type === 'force' && k === 'on');
  const field = ([k, f]) => {
    const L = fieldName(o, k);
    if (f.k === 'num') { const sr = slideRange(o, k, f); return `<label class="${sr ? 'wide slide' : ''}">${L}<span class="numrow"><input data-f="${k}" type="number" step="${NUM_STEP[k] || 0.05}" min="${f.min}" max="${f.max}" value="${r4(o[k])}">${sr ? `<input data-s="${k}" type="range" min="${sr[0]}" max="${sr[1]}" step="${(sr[1] - sr[0]) / 200}" value="${Math.max(sr[0], Math.min(sr[1], o[k]))}" aria-label="${esc(L)}">` : ''}</span></label>`; }
    if (f.k === 'bool') return `<label class="chk wide"><input data-f="${k}" type="checkbox"${o[k] ? ' checked' : ''}>${L}</label>`;
    if (f.k === 'enum') return `<label>${L}<select data-f="${k}">${f.list.map(v => `<option value="${v}"${v === o[k] ? ' selected' : ''}>${esc(o.type === 'element' && k === 'kind' ? X2.kinds[v] : o.type === 'block' && v === 'box' ? (ko ? '상자' : 'Box') : T.enums[v] || v)}</option>`).join('')}</select></label>`;
    if (f.k === 'ref') return `<label>${L}<select data-f="${k}">${opts(f.types, o[k], optional(k))}</select></label>`;
    if (f.k === 'refs') { const ps = st.scene.objects.filter(x => x.type === 'pulley'); return ps.length ? `<div class="wide"><span class="note">${L}</span><div class="over">${ps.map(p => `<label><input type="checkbox" data-over="${esc(p.id)}"${o.over.includes(p.id) ? ' checked' : ''}>${esc(p.id)}</label>`).join('')}</div></div>` : ''; }
    if (f.k === 'expr' || k === 'data' || k === 'xt' || k === 'yt') return `<label class="wide">${L}<input data-f="${k}" maxlength="${f.max}" value="${esc(o[k])}" spellcheck="false" autocomplete="off"></label>`;
    return `<label class="wide">${L}<span class="tin"><input data-f="${k}" data-text="1" maxlength="${f.max}" value="${esc(o[k])}" spellcheck="false" autocomplete="off"><button type="button" class="symbtn" data-sym="${k}" title="${esc(X2.symTitle)}">Ω</button></span><span class="tex" data-tex="${k}"></span></label>`;
  };
  /* the object's own values first, its look (line weight, label size, lock) last */
  const main = fields.filter(([k]) => !['lw', 'ls', 'lock'].includes(k)), look = fields.filter(([k]) => ['lw', 'ls', 'lock'].includes(k));
  box.innerHTML = `<h2>${esc(o.type === 'element' ? X2.kinds[o.kind] : T.types[o.type])} <span class="note">${esc(o.id)}</span></h2><div class="props">${main.map(field).join('')}</div>
    ${fields.some(([, f]) => f.k === 'txt') ? `<p class="note">${esc(T.texHint)}</p>` : ''}
    <details class="look"><summary>${ko ? '선 · 글자 · 잠금' : 'Lines, labels, lock'}</summary><div class="props">${look.map(field).join('')}</div></details>
    <div class="row">${['string', 'rod', 'spring', 'force'].includes(o.type) ? '' : `<button type="button" data-act="dup">${T.dup}</button>`}<button type="button" data-act="front">${X3.tools.front}</button><button type="button" data-act="back">${X3.tools.backZ}</button><button type="button" data-act="del">${T.del}</button></div>`;
  box.querySelectorAll('[data-f]').forEach(el => {
    const k = el.dataset.f, f = F[k];
    const apply = () => {
      const next = clone(st.scene), x = next.objects.find(y => y.id === o.id);
      if (f.k === 'num') { const v = parseFloat(el.value); if (!Number.isFinite(v)) { paintSide(); return; } const J0 = x.type === 'bridge' ? jockey(x) : null; x[k] = v; if (J0) followJockey(next, J0, jockey(x)); }
      else if (f.k === 'bool') x[k] = el.checked;
      else x[k] = el.value;
      if (o.type === 'element' && k === 'kind' && X2.units[x.kind] && !X2.units[o.kind]) x.value = defaults('element').value;
      if (k === 'on') {
        if (x.on) { const fr = surfaceFrame(next.objects.find(y => y.id === x.on), next); x.at = r4(Math.max(0, Math.min(fr.length, vec.dot(vec.sub(bodyPose(st.scene, o), fr.p0), fr.u)))); }
        else { const p = bodyPose(st.scene, o); x.x = r4(p.x); x.y = r4(p.y); }
      }
      if (!commit(next, {keepSel: true})) paintSide();
    };
    el.onchange = apply;
    if (f.k === 'txt') { el.oninput = () => texPreview(k, el.value); el.onfocus = () => { st.lastText = {id: o.id, k}; }; texPreview(k, el.value); }
  });
  /* a slider changes the figure live while it moves, and is one step of history when it is let go */
  box.querySelectorAll('[data-s]').forEach(el => {
    const k = el.dataset.s, num = box.querySelector(`[data-f="${k}"]`);
    el.oninput = () => {
      if (!st.gesture) st.gesture = {before: JSON.stringify(st.scene)};
      const x = byId(o.id), v = r4(parseFloat(el.value)); if (!x || !Number.isFinite(v)) return;
      const J0 = x.type === 'bridge' ? jockey(x) : null;
      x[k] = v; if (num) num.value = v;
      if (J0) followJockey(st.scene, J0, jockey(x));
      if (isBody(x) && x.on) for (let i = 0; i < 2; i++) for (const y of st.scene.objects) if (isBody(y) && y.on) { const fr = surfaceFrame(byId(y.on), st.scene); placeOnFrame(y, fr); }
      if (st.sim) stopSim();
      paintCanvas(); paintReadouts();
    };
    el.onchange = () => { const g = st.gesture; st.gesture = null; if (!g) return; const r = validateScene(st.scene); if (!r.ok) { st.scene = JSON.parse(g.before); paint(); return; } st.hist.record(g.before); st.scene = r.scene; save(); paint(); };
  });
  box.querySelectorAll('[data-over]').forEach(el => el.onchange = () => {
    const next = clone(st.scene), x = next.objects.find(y => y.id === o.id), ids2 = [...box.querySelectorAll('[data-over]')].filter(c => c.checked).map(c => c.dataset.over);
    x.over = [...x.over.filter(id => ids2.includes(id)), ...ids2.filter(id => !x.over.includes(id))];
    alignHanging(next, x); commit(next, {keepSel: true});
  });
  box.querySelectorAll('[data-sym]').forEach(b => b.onclick = () => { st.lastText = {id: o.id, k: b.dataset.sym}; openSymbols(); });
  box.querySelector('[data-act="dup"]')?.addEventListener('click', dup);
  box.querySelector('[data-act="front"]').onclick = () => zOrder(true); box.querySelector('[data-act="back"]').onclick = () => zOrder(false);
  box.querySelector('[data-act="del"]').onclick = del;
}
/* several objects: align, distribute, the look of all of them */
function paintMulti(box, ids) {
  const tl = X3.tools, b = (act, t) => `<button type="button" data-al="${act}">${t}</button>`;
  box.innerHTML = `<h2>${esc(tl.multi(ids.length))}</h2>
    <div class="note">${tl.align}</div><div class="row tight">${b('aL', '⇤ ' + tl.aL)}${b('aC', '↔ ' + tl.aC)}${b('aR', tl.aR + ' ⇥')}${b('aT', '⤒ ' + tl.aT)}${b('aM', '↕ ' + tl.aM)}${b('aB', '⤓ ' + tl.aB)}</div>
    <div class="note">${tl.distribute}</div><div class="row tight">${b('dH', '⋯ ' + tl.dH)}${b('dV', '⋮ ' + tl.dV)}</div>
    <div class="props"><label>${T.fields.lw}<input data-all="lw" type="number" step="0.1" min="0.2" max="5" value="${byId(ids[0]).lw}"></label><label>${T.fields.ls}<input data-all="ls" type="number" step="0.1" min="0.3" max="4" value="${byId(ids[0]).ls}"></label></div>
    <div class="row"><button type="button" data-act="dup">${T.dup}</button><button type="button" data-act="lock">${tl.lockAll}</button><button type="button" data-act="unlock">${tl.unlockAll}</button><button type="button" data-act="front">${tl.front}</button><button type="button" data-act="back">${tl.backZ}</button><button type="button" data-act="del">${T.del}</button></div>
    <div class="olist">${ids.map(id => `<button type="button" data-pick="${esc(id)}">${esc(id)}</button>`).join('')}</div>`;
  box.querySelectorAll('[data-al]').forEach(x => x.onclick = () => alignSel(x.dataset.al));
  box.querySelectorAll('[data-all]').forEach(x => x.onchange = () => { const v = parseFloat(x.value); if (Number.isFinite(v)) setAll(x.dataset.all, v); });
  box.querySelector('[data-act="dup"]').onclick = dup; box.querySelector('[data-act="del"]').onclick = del;
  box.querySelector('[data-act="lock"]').onclick = () => setAll('lock', true); box.querySelector('[data-act="unlock"]').onclick = () => setAll('lock', false);
  box.querySelector('[data-act="front"]').onclick = () => zOrder(true); box.querySelector('[data-act="back"]').onclick = () => zOrder(false);
  box.querySelectorAll('[data-pick]').forEach(x => x.onclick = () => { setSel([x.dataset.pick]); paint(); });
}
/* the label as the figure will show it (the same typesetter as the SVG, in the figure's style) */
function texPreview(k, v) {
  const el = document.querySelector(`[data-tex="${k}"]`); if (!el) return;
  el.innerHTML = v ? texSVG(v, 17, st.scene.style) : '';
}

/* ── readouts and the graph ── */
const fmt = v => Number.isFinite(v) ? (Math.abs(v) >= 1000 ? v.toFixed(0) : Math.abs(v) >= 100 ? v.toFixed(1) : v.toFixed(2)) : '—';
function paintReadouts() {
  const box = $('readouts'); if (!box) return;
  if (!st.readouts) { box.innerHTML = ''; return; }
  if (!st.sim) { box.innerHTML = staticReadouts(); return; }
  const sim = st.sim, poses = sim.poses(), vel = sim.velocities(), acc = sim.accelerations(), e = sim.energy(), ten = sim.tensions(), R = T.rd;
  const ids = [...poses.keys()];
  const keys = [...ids.map(id => ['v:' + id, R.speedOf(id)]), ...ids.map(id => ['y:' + id, R.yOf(id)]), ...ids.map(id => ['x:' + id, R.xOf(id)]), ['energy', R.energy], ...Object.keys(ten).map(id => ['T:' + id, R.tensionOf(id)])];
  if (!keys.some(([k]) => k === st.graph)) st.graph = keys[0]?.[0] || '';
  box.innerHTML = `<div><table><thead><tr><th>${R.body}</th><th>${R.x}</th><th>${R.y}</th><th>${R.v}</th><th>${R.a}</th></tr></thead><tbody>
      ${ids.map(id => { const p = poses.get(id), v = vel.get(id), a = acc.get(id); return `<tr><td>${esc(id)}</td><td>${fmt(p.x)}</td><td>${fmt(p.y)}</td><td>${fmt(Math.hypot(v.x, v.y, v.z || 0))}</td><td>${fmt(Math.hypot(a.x, a.y))}</td></tr>`; }).join('')}</tbody></table>
      <table><tbody>${Object.entries(ten).map(([id, v]) => `<tr><td>${R.tension} ${esc(id)}</td><td>${fmt(v)} N</td></tr>`).join('')}
      <tr><td>${R.K}</td><td>${fmt(e.K)} J</td></tr><tr><td>${R.U}</td><td>${fmt(e.Ug + e.Us)} J</td></tr><tr><td>${R.E}</td><td>${fmt(e.E)} J</td></tr>${e.heat > 1e-9 ? `<tr><td>${R.heat}</td><td>${fmt(e.heat)} J</td></tr>` : ''}</tbody></table></div>
    <div class="graph"><label class="note">${R.graph} <select id="gSel">${keys.map(([k, n]) => `<option value="${esc(k)}"${k === st.graph ? ' selected' : ''}>${esc(n)}</option>`).join('')}</select></label>${graphSvg()}</div>`;
  $('gSel').onchange = e2 => { st.graph = e2.target.value; paintReadouts(); };
}
/* what the figure computes when nothing moves: the circuit's currents and voltages and its RC (RL) transient, a cycle's
   work and efficiency, an image's place, a fringe spacing, a well's energies… */
const sig = v => typeof v === 'number' ? (Math.abs(v) >= 1e4 || (Math.abs(v) < 1e-3 && v !== 0) ? v.toExponential(2) : +v.toPrecision(4) + '') : v;
const si = (v0, u) => { const v = +(+v0).toPrecision(6), a = Math.abs(v); const [k, p] = a >= 1e6 ? [1e-6, 'M'] : a >= 1e3 ? [1e-3, 'k'] : a >= 1 || a === 0 ? [1, ''] : a >= 1e-3 ? [1e3, 'm'] : a >= 1e-6 ? [1e6, 'μ'] : [1e9, 'n']; return `${+(v * k).toPrecision(4)} ${p}${u}`; };
function staticReadouts() {
  const parts = [];
  if (st.solve && hasCircuit()) {
    const c = st.circuit || solveCircuit(st.scene);
    if (!c.ok) parts.push(`<p class="note bad">${X2.circuit}: ${esc(X2.noCircuit[c.code] || c.code)}</p>`);
    else {
      const rows = [...c.el].filter(([id]) => byId(id) && byId(id).kind !== 'wire').map(([id, r]) => `<tr><td>${esc(id)}</td><td>${esc(X2.kinds[byId(id).kind])}</td><td>${si(Math.abs(r.drop) < 1e-6 ? 0 : r.drop, 'V')}</td><td>${si(Math.abs(r.I) < 1e-9 ? 0 : r.I, 'A')}</td></tr>`).join('');
      parts.push(`<div><table><thead><tr><th>${X2.element}</th><th></th><th>${X2.drop} V₁−V₂</th><th>${X2.current} (1→2)</th></tr></thead><tbody>${rows}</tbody></table></div>`);
      for (const t of c.transients) {
        const N = 120, pts = Array.from({length: N + 1}, (_, i) => { const tt = 5 * t.tau * i / N; return {t: tt, v: t.at(tt)}; }), lo = Math.min(0, ...pts.map(p => p.v)), hi = Math.max(1e-12, ...pts.map(p => p.v));
        const Xg = tt => 34 + tt / (5 * t.tau) * 258, Yg = v => 108 - (v - lo) / ((hi - lo) || 1) * 96;
        parts.push(`<div class="graph"><div class="note">${esc(X2.charging(t.id))} · ${X2.tau} = ${si(t.tau, 's')} · ${X2.rth} = ${si(t.R, 'Ω')} · ${t.kind === 'rc' ? X2.vFinal : X2.iFinal} = ${si(t.final, t.kind === 'rc' ? 'V' : 'A')}</div>
          <svg viewBox="0 0 300 120" role="img"><line x1="34" y1="108" x2="292" y2="108" stroke="currentColor" stroke-opacity=".35"/><line x1="34" y1="10" x2="34" y2="108" stroke="currentColor" stroke-opacity=".35"/>
          <line x1="${Xg(t.tau).toFixed(1)}" y1="10" x2="${Xg(t.tau).toFixed(1)}" y2="108" stroke="currentColor" stroke-opacity=".3" stroke-dasharray="3 3"/><text x="${Xg(t.tau).toFixed(1)}" y="119" font-size="9" text-anchor="middle" fill="currentColor">τ</text>
          <text x="30" y="14" font-size="9" text-anchor="end" fill="currentColor">${sig(hi)}</text><text x="292" y="119" font-size="9" text-anchor="end" fill="currentColor">5τ</text>
          <polyline points="${pts.map(p => `${Xg(p.t).toFixed(1)},${Yg(p.v).toFixed(1)}`).join(' ')}" fill="none" stroke="#3b6fd8" stroke-width="1.6"/></svg></div>`);
      }
    }
  }
  const info = computedInfo(st.scene).map(c => {
    const v = Object.fromEntries(Object.entries(c).map(([k, x]) => [k, Array.isArray(x) ? (c.type === 'levels' ? x.map(t => `${t.from}→${t.to}: ${t.lambda.toFixed(1)} nm`).join(', ') : x.map(e => sig(e) + ' eV').join(', ')) : k === 'dy' ? si(x, 'm') : sig(x)]));
    const line = X2.infoT[c.type]?.(v); return line ? `<li><b>${esc(c.id)}</b> ${esc(line)}</li>` : '';
  }).join('');
  if (info) parts.push(`<div><div class="note">${X2.info}</div><ul class="info">${info}</ul></div>`);
  return parts.join('');
}
function graphSvg() {
  const k = st.graph, data = st.samples.map(s => ({t: s.t, v: k === 'energy' ? s.E : k.startsWith('T:') ? s.tension[k.slice(2)] : s[k]})).filter(d => Number.isFinite(d.v));
  if (data.length < 2) return '<svg viewBox="0 0 300 120"></svg>';
  const t0 = data[0].t, t1 = Math.max(t0 + 0.5, data[data.length - 1].t);
  let lo = Math.min(...data.map(d => d.v)), hi = Math.max(...data.map(d => d.v)); if (hi - lo < 1e-6) { lo -= 1; hi += 1; }
  const X = t => 34 + (t - t0) / (t1 - t0) * 258, Y = v => 108 - (v - lo) / (hi - lo) * 96;
  const pts = data.map(d => `${X(d.t).toFixed(1)},${Y(d.v).toFixed(1)}`).join(' ');
  return `<svg viewBox="0 0 300 120" role="img"><line x1="34" y1="108" x2="292" y2="108" stroke="currentColor" stroke-opacity=".35"/><line x1="34" y1="10" x2="34" y2="108" stroke="currentColor" stroke-opacity=".35"/>
    <text x="30" y="14" font-size="9" text-anchor="end" fill="currentColor">${fmt(hi)}</text><text x="30" y="108" font-size="9" text-anchor="end" fill="currentColor">${fmt(lo)}</text><text x="292" y="119" font-size="9" text-anchor="end" fill="currentColor">${fmt(t1)} s</text>
    <polyline points="${pts}" fill="none" stroke="#3b6fd8" stroke-width="1.6"/></svg>`;
}

/* ── status line and play bar ── */
function status() {
  const el = $('status'); if (!el) return;
  if (st.msg) { el.innerHTML = st.msg; return; }
  if (st.connect) { const c = st.connect; el.innerHTML = `<b>${esc(T.connect[c.type])}</b> ${c.a ? esc([c.a, ...c.over].join(' → ')) + ' → …' : ''} · ${T.connect.esc}`; return; }
  const sim = st.sim;
  if (sim) {
    const ev = sim.events.map(e => `${T.stopped}: ${esc(T.events[e.code]?.(e.id) || e.code)} (t = ${e.t.toFixed(3)} s)`);
    el.innerHTML = [...ev, sim.unsupported.length ? `<span class="bad">${T.notSim}: ${esc(unsupportedText(sim))}</span>` : ''].filter(Boolean).join(' · ');
    return;
  }
  el.innerHTML = '';
}
function paintSimBar() {
  const b = $('playBtn'); if (!b) return;
  b.textContent = st.playing ? '⏸ ' + T.pause : '▶ ' + T.play;
  $('clock').textContent = `${T.time} ${(st.sim ? st.sim.t : 0).toFixed(2)} s`;
}

/* ── export ── */
/* for the paper and the files: the figure drawn at the scale at which, printed at the style's typical width (or the
   figure's own print width), its labels, lines and arrowheads come out at the sizes measured for that style
   (draw-render.mjs STYLE_TABLE, printScale) */
function paperScale() { const p = printScale(st.scene.style, st.scene.printW); return {labelScale: p.labelScale, strokeScale: p.strokeScale}; }
function exportSvg(paper = true) {
  const sc = st.sim ? st.sim.applyTo(st.scene) : st.scene;
  let forces = null; if (st.fbd) { try { forces = (st.sim || buildSim(st.scene)).forces(); } catch (e) {} }
  return renderSVG(sc, {width: W, view: view(), forces, circuit: st.solve && hasCircuit() ? solveCircuit(st.scene) : null, ...(paper ? paperScale() : {}), poses: st.sim ? st.sim.poses() : null, velocities: st.sim ? st.sim.velocities() : null, anchors: st.sim?.anchors, title: st.scene.title || T.title,
    conical: st.scene.objects.filter(o => (o.type === 'string' || o.type === 'rod') && o.mode === 'conical').map(conicalOrbit).filter(Boolean)});
}
const b64 = s => { const bytes = new TextEncoder().encode(s); let bin = ''; for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000)); return btoa(bin); };
const svgDataUrl = svg => 'data:image/svg+xml;base64,' + b64(svg);
const fileName = ext => ((st.scene.title || 'figure').replace(/[\\/:*?"<>|]+/g, ' ').trim().slice(0, 60) || 'figure') + '.' + ext;
function download(blob, name) { const url = URL.createObjectURL(blob), a = document.createElement('a'); a.href = url; a.download = name; document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 30000); }
function pngBlob(svg) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => { const c = document.createElement('canvas'); c.width = img.naturalWidth * 2; c.height = img.naturalHeight * 2; const g = c.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, c.width, c.height); g.drawImage(img, 0, 0, c.width, c.height); c.toBlob(b => b ? resolve(b) : reject(new Error('png')), 'image/png'); };
    img.onerror = reject; img.src = svgDataUrl(svg);
  });
}
function toPaper() {
  const svg = exportSvg(true), src = svgDataUrl(svg), m = /viewBox="0 0 (\d+) (\d+)"/.exec(svg);
  let paper;
  try { paper = JSON.parse(store.get(PAPER_KEY) || 'null'); } catch (e) { paper = null; }
  if (!paper || !Array.isArray(paper.items)) paper = {title: '', school: '', info: '', minutes: '', note: '', two: true, key: true, sol: false, space: false, bp: false, items: []};
  const fig = {src, w: +m[1], h: +m[2], scene: st.scene};
  const item = st.paperEdit && paper.items.find(x => x.key === st.paperEdit && x.own);
  if (item) item.own.fig = fig;
  else paper.items.push({key: 'own:' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6), pts: 3, own: {q: ($('paperQ')?.value || '').trim().slice(0, 4000), answer: '', unit: '', sol: '', fig}});
  if (!store.set(PAPER_KEY, JSON.stringify(paper))) { flash(`<span class="bad">${T.err.other}</span>`); return; }
  st.paperEdit = null;
  $('outMsg').innerHTML = `<span class="ok">${T.inPaper}</span> <a class="btn" href="${embedded ? '/#/workshop/make' : 'teach.html'}" target="_top">${T.openPaper}</a>`;
  paintOut(true);
}
async function toStorage() {
  const msg = $('outMsg');
  if (!token()) { msg.innerHTML = `${T.storeLogin} <a class="btn" href="/#/login" target="_top">${T.login}</a>`; return; }
  msg.textContent = '…';
  try {
    await api('/api/workshop/storage/folders', 'POST', {path: T.folder});
    for (const [ext, body, type] of [['json', JSON.stringify(st.scene, null, 1), 'application/json'], ['svg', exportSvg(), 'image/svg+xml']]) {
      const form = new FormData(); form.append('file', new File([body], fileName(ext), {type})); form.append('folder', T.folder);
      await api('/api/workshop/storage/files', 'POST', form, true);
    }
    msg.innerHTML = `<span class="ok">${esc(T.stored(T.folder))}</span>`;
  } catch (e) { msg.innerHTML = `<span class="bad">${esc(errText(e))}</span>`; }
}
const saves = () => { try { const l = JSON.parse(store.get(SAVES_KEY) || '[]'); return Array.isArray(l) ? l.filter(x => x && typeof x.name === 'string' && x.scene) : []; } catch (e) { return []; } };
function saveLocal() {
  const list = saves().filter(x => x.name !== (st.scene.title || fileName('json')));
  list.unshift({name: st.scene.title || fileName('json'), t: Date.now(), scene: st.scene});
  $('outMsg').innerHTML = store.set(SAVES_KEY, JSON.stringify(list.slice(0, 20))) ? `<span class="ok">${T.localSaved}</span>` : `<span class="bad">${T.err.other}</span>`;
  paintOut(true);
}
function openScene(obj) {
  const r = validateScene(obj);
  if (!r.ok) { $('outMsg').innerHTML = `<span class="bad">${T.loadBad}</span>`; return; }
  if (!r.scene.view) r.scene.view = sceneBounds(r.scene);
  setSel([]); st.ai = null; st.zoom = null; commit(r.scene);
}
function paintOut(keepMsg) {
  const box = $('out'); if (!box) return;
  const old = keepMsg ? $('outMsg')?.innerHTML || '' : '';
  const list = saves();
  box.innerHTML = `<h2>${T.out}</h2>
    <div class="row"><button type="button" id="oSvg">${T.svg}</button><button type="button" id="oPng">${T.png}</button></div>
    ${st.paperEdit ? '' : `<label class="note" for="paperQ">${T.paperQ}</label><textarea id="paperQ" class="q" rows="2"></textarea>`}
    <div class="row"><button type="button" class="primary" id="oPaper">${st.paperEdit ? T.replacePaper : T.toPaper}</button></div>
    <div class="row"><button type="button" id="oStore">${T.store}</button><button type="button" id="oLocal">${T.local}</button></div>
    <div class="row"><button type="button" id="oJson">${T.json}</button><label class="btn filebtn">${T.load}<input type="file" id="oLoad" accept=".json,application/json"></label></div>
    <p class="note" id="outMsg" role="status">${old}</p>
    ${list.length ? `<div class="note">${T.saves}</div><div class="saves">${list.map((x, i) => `<div><span>${esc(x.name)}</span><button type="button" data-open="${i}">${T.open}</button><button type="button" data-drop="${i}" aria-label="${T.del}">✕</button></div>`).join('')}</div>` : ''}`;
  $('oSvg').onclick = () => download(new Blob([exportSvg()], {type: 'image/svg+xml'}), fileName('svg'));
  $('oPng').onclick = () => pngBlob(exportSvg()).then(b => download(b, fileName('png'))).catch(() => { $('outMsg').innerHTML = `<span class="bad">${T.err.other}</span>`; });
  $('oPaper').onclick = toPaper; $('oStore').onclick = toStorage; $('oLocal').onclick = saveLocal;
  $('oJson').onclick = () => download(new Blob([JSON.stringify(st.scene, null, 1)], {type: 'application/json'}), fileName('json'));
  $('oLoad').onchange = async e => { const f = e.target.files[0]; e.target.value = ''; if (!f || f.size > 1e6) return; try { openScene(JSON.parse(await f.text())); } catch (x) { $('outMsg').innerHTML = `<span class="bad">${T.loadBad}</span>`; } };
  box.querySelectorAll('[data-open]').forEach(b => b.onclick = () => openScene(list[+b.dataset.open].scene));
  box.querySelectorAll('[data-drop]').forEach(b => b.onclick = () => { const l = saves(); l.splice(+b.dataset.drop, 1); store.set(SAVES_KEY, JSON.stringify(l)); paintOut(); });
}

/* ── photo → figure ── */
async function photoFile(file) {
  if (!file) return;
  if (!token()) { flash(`<span class="bad">${T.photoLogin}</span> <a class="btn" href="/#/login" target="_top">${T.login}</a>`); return; }
  flash(T.reading);
  let image;
  try {
    const bmp = await createImageBitmap(file), k = Math.min(1, 1600 / Math.max(bmp.width, bmp.height)), c = document.createElement('canvas');
    c.width = Math.round(bmp.width * k); c.height = Math.round(bmp.height * k); const g = c.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, c.width, c.height); g.drawImage(bmp, 0, 0, c.width, c.height);
    for (const q of [0.85, 0.7, 0.55]) { image = c.toDataURL('image/jpeg', q); if (image.length < 5.2e6) break; }
  } catch (e) { flash(`<span class="bad">${T.err.bad_image}</span>`); return; }
  try {
    const r = await api('/api/workshop/scene-from-image', 'POST', {image, lang});
    const v = validateScene(r.scene);
    if (!v.ok) throw {code: 'scene_failed'};
    v.scene.view = sceneBounds(v.scene); if (!v.scene.title) v.scene.title = '';
    st.ai = {unsure: Array.isArray(r.unsure) ? r.unsure : [], left: r.left}; setSel([]); st.zoom = null;
    commit(v.scene); flash('');
  } catch (e) { flash(`<span class="bad">${esc(errText(e))}</span>`); }
}
function paintAi() {
  const box = $('aiNote'); if (!box) return;
  if (!st.ai) { box.innerHTML = ''; box.hidden = true; return; }
  box.hidden = false;
  const u = st.ai.unsure.filter(x => T.unsure[x.what]);
  box.innerHTML = `<b>${T.aiNote}</b>${Number.isFinite(st.ai.left) ? ` <span>${T.left(st.ai.left)}</span>` : ''}
    ${u.length ? `<div>${T.aiUnsure}:</div><ul>${u.map(x => `<li>${x.id && byId(x.id) ? `${esc(x.id)}: ` : ''}${T.unsure[x.what]}${x.id && byId(x.id) ? `<button type="button" data-pick="${esc(x.id)}">↗</button>` : ''}</li>`).join('')}</ul>` : ''}`;
  box.querySelectorAll('[data-pick]').forEach(b => b.onclick = () => { setSel([b.dataset.pick]); paint(); });
}

/* ── the page ── */
/* the palette: a tab a domain, or every match of the search */
function paintPalette() {
  const box = $('palette'); if (!box) return;
  const q = st.q.trim().toLowerCase();
  const entries = q ? Object.entries(PALETTE).flatMap(([d, list]) => list.map((e, i) => [d, i, e]).filter(([, , e]) => (e[2] + ' ' + e[0] + ' ' + (e[1].kind || '') + ' ' + PAL_EN[d]).toLowerCase().includes(q) || e[2].toLowerCase().includes(q)))
    : PALETTE[st.dom].map((e, i) => [st.dom, i, e]);
  box.innerHTML = `<div class="tabs" role="tablist">${Object.keys(PALETTE).map(d => `<button type="button" role="tab" data-dom="${d}" aria-selected="${!q && d === st.dom}" class="${!q && d === st.dom ? 'on' : ''}">${X2.domains[d]}</button>`).join('')}</div>
    <div class="items">${entries.map(([d, i, e]) => `<button type="button" data-add="${d}:${i}" class="${st.connect?.type === e[0] ? 'on' : ''}">${esc(e[2])}</button>`).join('') || `<span class="note">—</span>`}</div>`;
  box.querySelectorAll('[data-dom]').forEach(b => b.onclick = () => { st.dom = b.dataset.dom; st.q = ''; const s2 = $('palSearch'); if (s2) s2.value = ''; paintPalette(); height(); });
  box.querySelectorAll('[data-add]').forEach(b => b.onclick = () => { const [d, i] = b.dataset.add.split(':'), e = PALETTE[d][+i]; addObject(e[0], clone(e[1])); });
}
/* the symbol picker: inserts into the text field last used, or adds a label */
function openSymbols() {
  let pop = $('symPop');
  if (pop) { pop.hidden = !pop.hidden; if (!pop.hidden) pop.querySelector('button')?.focus(); return; }
  pop = document.createElement('div'); pop.id = 'symPop'; pop.className = 'sympop'; pop.setAttribute('role', 'dialog'); pop.setAttribute('aria-label', X2.symTitle);
  pop.innerHTML = `<div class="symhead"><b>${X2.symTitle}</b><button type="button" data-close aria-label="✕">✕</button></div><p class="note">${X2.symHint}</p>${SYMBOLS.map(([g, list]) => `<div class="symgrp"><div class="note">${esc(g)}</div><div class="syms">${list.map(([tex]) => `<button type="button" data-tex="${esc(tex)}" title="${esc(tex)}">${texSVG(tex, 17, st.scene.style)}</button>`).join('')}</div></div>`).join('')}`;
  $('stageTop').after(pop);
  pop.querySelector('[data-close]').onclick = () => { pop.hidden = true; };
  pop.querySelectorAll('[data-tex]').forEach(b => b.onclick = () => insertSymbol(b.dataset.tex));
  height();
}
function insertSymbol(tex) {
  const t = st.lastText, o = t && byId(t.id);
  if (o && FIELDS[o.type][t.k]?.k === 'txt') {
    const el = document.querySelector(`[data-f="${t.k}"]`), cur = String(o[t.k] || ''), a = el && document.activeElement === el ? el.selectionStart : (el?._caret ?? cur.length), b = el && document.activeElement === el ? el.selectionEnd : a;
    const val = (cur.slice(0, a) + tex + (/^\\[A-Za-z]+$/.test(tex) && /^[A-Za-z]/.test(cur.slice(b)) ? ' ' : '') + cur.slice(b)).slice(0, FIELDS[o.type][t.k].max);
    const next = clone(st.scene); next.objects.find(x => x.id === o.id)[t.k] = val;
    if (commit(next, {keepSel: true})) { setSel([o.id]); paint(); const el2 = document.querySelector(`[data-f="${t.k}"]`); if (el2) { el2.focus(); const c = Math.min(val.length, a + tex.length); el2.setSelectionRange(c, c); el2._caret = c; } }
    return;
  }
  const v = dview(), next = clone(st.scene), id = freeId('label');
  next.objects.push({...defaults('label'), id, x: r4(snapV(v.x + v.w / 2)), y: r4(snapV(v.y + v.h / 2)), text: tex});
  if (commit(next)) { setSel([id]); st.lastText = {id, k: 'text'}; paint(); }
}
function shell() {
  const tl = X3.tools;
  $('app').innerHTML = `<div class="head"><div><h1>${T.title}</h1><p class="lede">${T.lede}</p></div></div>
    <div class="dbar"><select id="tpl" aria-label="${T.template}"><option value="">${T.template}…</option>${Object.keys(DOMAINS).map(d => `<optgroup label="${esc(X2.domains[d])}">${TEMPLATE_KEYS.filter(k => TEMPLATE_DOMAIN[k] === d).map(k => `<option value="${k}">${esc(TEMPLATE_NAMES[k][lang])}</option>`).join('')}</optgroup>`).join('')}<option value="blank">${T.blank}</option></select>
      <select id="styleSel" aria-label="${X2.style}" title="${X2.style}">${STYLE_KEYS.map(k => `<option value="${k}">${esc(X2.style)}: ${esc(STYLES[k].name[lang])}</option>`).join('')}</select><button type="button" id="bSym">${X2.symbols}</button>
      <label class="btn filebtn">📷 ${T.photo}<input type="file" id="photo" accept="image/jpeg,image/png,image/webp,image/*"></label><span class="sep"></span>
      <button type="button" id="bUndo" class="hist" title="${esc(tl.backT)}" aria-label="${esc(tl.backT)}">${tl.back}</button><button type="button" id="bRedo" class="hist" title="${esc(tl.fwdT)}" aria-label="${esc(tl.fwdT)}">${tl.fwd}</button>
      <button type="button" id="bDup" title="Ctrl+D">${T.dup}</button><button type="button" id="bCopy" title="Ctrl+C">${tl.copy}</button><button type="button" id="bPaste" title="Ctrl+V">${tl.paste}</button><button type="button" id="bDel" title="Delete">${T.del}</button><button type="button" id="bClear" class="danger">${tl.clear}</button><span class="sep"></span>
      <span class="zoom" role="group" aria-label="zoom"><button type="button" id="bZout" title="${esc(tl.zoomOut)} (−)" aria-label="${esc(tl.zoomOut)}">−</button><span id="zoomPct" class="pct">100%</span><button type="button" id="bZin" title="${esc(tl.zoomIn)} (+)" aria-label="${esc(tl.zoomIn)}">+</button><button type="button" id="bZfit" title="${esc(tl.zoomFit)} (0)">${tl.zoomFit}</button></span>
      <label class="btn"><input type="checkbox" id="cGrid" checked style="width:auto"> ${T.grid}</label><label class="btn"><input type="checkbox" id="cSnap" checked style="width:auto"> ${T.snap}</label><label class="btn"><input type="checkbox" id="cVals" style="width:auto"> ${tl.values}</label><button type="button" id="bFit" title="${esc(tl.frameMark)}">${T.fit}</button></div>
    <div id="aiNote" class="ainote" hidden></div>
    <div class="work"><nav class="palwrap" aria-label="${X2.search}"><input type="search" id="palSearch" placeholder="${esc(X2.search)}" aria-label="${esc(X2.search)}"><div id="palette" class="palette"></div></nav>
      <section class="stage"><div id="stageTop"></div><div id="canvas" class="canvas" tabindex="0"></div><p id="status" class="status" role="status"></p><p class="note hint">${esc(tl.zoomHint)}</p>
        <div class="simbar"><span id="mechBar" class="grp"><button type="button" class="primary" id="playBtn"></button><button type="button" id="resetBtn">⟲ ${T.reset}</button>
          <label>${T.speed}<select id="speed">${[0.1, 0.25, 0.5, 1, 2].map(v => `<option value="${v}"${v === st.speed ? ' selected' : ''}>${v}×</option>`).join('')}</select></label>
          <label><input type="checkbox" id="cFbd"${st.fbd ? ' checked' : ''}>${T.fbd}</label></span><label><input type="checkbox" id="cRead"${st.readouts ? ' checked' : ''}>${T.readouts}</label><label id="solveLbl"><input type="checkbox" id="cSolve"${st.solve ? ' checked' : ''}>${X2.solve}</label><span class="clock" id="clock"></span></div>
        <div id="readouts" class="readouts"></div></section>
      <div class="side"><section class="panel" id="props"></section><section class="panel" id="out"></section></div></div>`;
  $('tpl').onchange = e => { const k = e.target.value; e.target.value = ''; if (!k) return; st.ai = null; setSel([]); st.zoom = null; if (TEMPLATE_DOMAIN[k]) st.dom = TEMPLATE_DOMAIN[k]; commit(k === 'blank' ? {...blankScene(), style: st.scene.style, view: {x: -0.5, y: -0.5, w: 4, h: 3}} : validateScene(template(k, lang)).scene); };
  $('photo').onchange = e => { const f = e.target.files[0]; e.target.value = ''; photoFile(f); };
  $('bUndo').onclick = undo; $('bRedo').onclick = redo; $('bDup').onclick = dup; $('bDel').onclick = del; $('bClear').onclick = clearAll;
  $('bCopy').onclick = () => { if (copySel()) paintBar(); }; $('bPaste').onclick = () => pasteClip();
  $('bZin').onclick = () => zoomBy(1.25); $('bZout').onclick = () => zoomBy(0.8); $('bZfit').onclick = () => { st.zoom = null; paintCanvas(); };
  $('cGrid').onchange = e => { st.grid = e.target.checked; paintCanvas(); }; $('cSnap').onchange = e => { st.snap = e.target.checked; };
  $('cVals').onchange = e => { const next = clone(st.scene); next.values = e.target.checked; commit(next, {keepSel: true}); };
  $('bFit').onclick = () => { const next = clone(st.scene); next.view = sceneBounds(next); st.zoom = null; commit(next, {keepSel: true}); };
  $('palSearch').oninput = e => { st.q = e.target.value; paintPalette(); height(); };
  $('styleSel').onchange = e => { const next = clone(st.scene); next.style = e.target.value; commit(next, {keepSel: true}); const pop = $('symPop'); if (pop) { pop.remove(); } };
  $('bSym').onclick = openSymbols;
  $('cSolve').onchange = e => { st.solve = e.target.checked; paintCanvas(); paintReadouts(); };
  $('playBtn').onclick = () => st.playing ? pause() : play();
  $('resetBtn').onclick = () => { stopSim(); paint(); };
  $('speed').onchange = e => { st.speed = +e.target.value; };
  $('cFbd').onchange = e => { st.fbd = e.target.checked; paintCanvas(); };
  $('cRead').onchange = e => { st.readouts = e.target.checked; paintReadouts(); };
  bindCanvas(); paint(); paintOut();
}
/* the toolbar's state: back/forward only when there is something to go to; play only for mechanics; the circuit solver
   only with a circuit */
function paintBar() {
  if (!$('bUndo')) return;
  $('bUndo').disabled = !st.hist.canUndo; $('bRedo').disabled = !st.hist.canRedo;
  const any = selIds().length > 0; $('bDel').disabled = !any; $('bDup').disabled = !any; $('bCopy').disabled = !any;
  $('bPaste').disabled = !st.clip; $('bClear').disabled = !st.scene.objects.length;
  $('cVals').checked = !!st.scene.values;
  const mech = hasMech(), circ = hasCircuit();
  $('mechBar').hidden = !mech; $('clock').hidden = !mech; $('solveLbl').hidden = !circ;
  if (!mech && st.sim) stopSim();
}
function paint() {
  paintCanvas(); paintSide(); paintReadouts(); paintSimBar(); status(); paintAi(); paintPalette(); paintBar();
  if ($('styleSel')) $('styleSel').value = st.scene.style;
  height();
}
function height() { if (embedded) requestAnimationFrame(() => window.parent.postMessage({type: 'hl-draw-height', height: Math.ceil(document.querySelector('main').getBoundingClientRect().bottom + scrollY + 16)}, location.origin)); }
let lastW = 0;
if (typeof ResizeObserver === 'function') new ResizeObserver(() => { height(); const w = $('canvas')?.clientWidth || 0; if (w && Math.abs(w - lastW) > 30) { lastW = w; paintCanvas(); } }).observe(document.body);
addEventListener('keydown', e => {
  if (e.target.closest?.('input,textarea,select')) return;
  const mod = e.ctrlKey || e.metaKey, k = e.key.toLowerCase();
  if (e.key === ' ' && !st.space) { st.space = true; $('canvas')?.classList.add('panning'); e.preventDefault(); return; }
  if (e.key === 'Escape') { st.connect = null; setSel([]); paint(); }
  else if (mod && k === 'z') { e.preventDefault(); e.shiftKey ? redo() : undo(); }
  else if (mod && k === 'y') { e.preventDefault(); redo(); }
  else if (mod && k === 'd') { e.preventDefault(); dup(); }
  else if (mod && k === 'c') { if (copySel()) { e.preventDefault(); paintBar(); } }
  else if (mod && k === 'v') { e.preventDefault(); pasteClip(); }
  else if (mod && k === 'a') { e.preventDefault(); setSel(st.scene.objects.map(o => o.id)); paint(); }
  else if (!mod && (e.key === '+' || e.key === '=')) zoomBy(1.25);
  else if (!mod && (e.key === '-' || e.key === '_')) zoomBy(0.8);
  else if (!mod && e.key === '0') { st.zoom = null; paintCanvas(); }
  else if ((e.key === 'Delete' || e.key === 'Backspace') && selIds().length) { e.preventDefault(); del(); }
  else if (selIds().length && e.key.startsWith('Arrow')) {
    /* a grid step, ten with Shift: one step of history each */
    e.preventDefault();
    const d = st.scene.grid * (e.shiftKey ? 10 : 1), dx = e.key === 'ArrowLeft' ? -d : e.key === 'ArrowRight' ? d : 0, dy = e.key === 'ArrowDown' ? -d : e.key === 'ArrowUp' ? d : 0;
    const next = clone(st.scene), ids = new Set(selIds());
    for (const x of next.objects) if (ids.has(x.id) && !x.lock && !NO_DRAG.includes(x.type)) { const g = clone(x); if (isBody(x) && x.on) x.at = r4(x.at + (dx || dy)); else moveObj(x, dx, dy, g); }
    commit(next, {keepSel: true});
  }
});
addEventListener('keyup', e => { if (e.key === ' ') { st.space = false; $('canvas')?.classList.remove('panning'); } });
st.scene = startScene();
if (!st.scene.view) st.scene.view = sceneBounds(st.scene);
if (document.readyState === 'loading') addEventListener('DOMContentLoaded', shell); else shell();
