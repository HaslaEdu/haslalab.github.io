/* The Workshop's figure and simulation editor (#/workshop/draw, draw.html in a frame). A figure is a scene
   (draw-scene.mjs): objects with values in SI units, drawn as an exam figure (draw-render.mjs) and run by the solver
   (draw-physics.mjs). Objects come from the palette or a template, are dragged on a grid and edited by value in the side
   panel. The figure goes out as SVG or PNG, onto the test paper of the problem maker (teach.js reads the paper from
   localStorage 'hlTeachPaper'; the figure is an SVG data URL with its scene), into the member's storage
   (/api/workshop/storage) or into this browser. "Start from a photo" sends one photo to /api/workshop/scene-from-image
   (community/src/workshop-scene.js) and opens what comes back for checking. */
import {geoIntersect, validateScene, defaults, template, TEMPLATE_KEYS, TEMPLATE_NAMES, TEMPLATE_DOMAIN, FIELDS, DOMAINS, STYLE_KEYS, isBody, isRound, bodyPose, vectorPoints, vectorTransform, surfaceFrame, sceneBounds, vec, blankScene, MAX_OBJECTS, createHistory, rotCentre, ROTATABLE, COLORS, FILLS, parseParams, paramsText, simplifyPath,
  GEO_TYPES, PHYS_SHAPES, PHYS_FIELDS, computeGeometry, isPhysShape} from './draw-scene.mjs?v=7959e10d8eeb';
import {buildSim, solveCircuit, computedInfo} from './draw-physics.mjs?v=f6b4ee63f834';
import {renderSVG, texSVG, PLACEHOLDER, STYLES, STYLE_TABLE, objectBox, printScale, COLOR_HEX, labelScaleFor} from './draw-render.mjs?v=f74e161993eb';

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
  unsupported: {held_by_figure: '계산하지 않는 부분(판·궤도·선·도형·액체)에 놓이거나 매달려 있어 그대로 둡니다', hanging_not_vertical: '매달린 물체가 도르래 바로 아래에 있지 않습니다', tied_not_on_surface: '도르래 없이 이은 두 물체는 면 위에 있어야 합니다', spring_between_systems: '서로 다른 종류의 운동을 하는 물체를 용수철로 이었습니다', pivot_over_pulley: '고정점에서 도르래를 거치는 줄은 아직 계산하지 못합니다', pendulum_on_surface: '진자의 추가 면 위에 있습니다', pendulum_with_spring: '진자에 용수철이 달려 있습니다', zero_length: '줄의 길이가 0입니다', conical_angle: '원뿔 진자의 각도는 0°와 88° 사이여야 합니다', spring_surface_and_air: '면 위의 물체와 공중의 물체를 용수철로 이었습니다'},
  notSim: '이 부분은 계산하지 않습니다', nothing: '움직일 물체가 없습니다.',
  scene: '그림', sceneTitle: '그림 이름', g: '중력 가속도 g (m/s²)', gridSize: '격자 간격 (m)', objects: '그림에 있는 것', noSel: '그림에서 물체를 누르면 값을 고칠 수 있습니다.',
  fields: {x: 'x (m)', y: 'y (m)', w: '너비 (m)', h: '높이 (m)', r: '반지름 (m)', mass: '질량 (kg)', label: '이름표', on: '놓인 면', at: '면 위 위치 (m)', vx: '처음 속도 vx (m/s)', vy: '처음 속도 vy (m/s)', showV: '속도 화살표', vLabel: '속도 이름표', trail: '지나간 길 표시',
    mu: '마찰 계수 μ', hatch: '빗금', side: '단단한 쪽', angle: '각도 (°)', length: '빗면 길이 (m)', flip: '왼쪽으로 오르게', angleLabel: '각 이름표', mount: '붙은 곳', a: '한쪽 끝', b: '다른 끝', over: '지나는 도르래', mode: '운동', k: '용수철 상수 k (N/m)', L0: '자연 길이 (m)', coils: '감은 수',
    F: '힘의 크기 (N)', len: '화살표 길이 (m)', text: '글', size: '글자 크기', x1: 'x₁', y1: 'y₁', x2: 'x₂', y2: 'y₂', offset: '띄우기 (m)', from: '시작 각 (°)', to: '끝 각 (°)', lx: 'x축 길이', ly: 'y축 길이', xlabel: 'x축 이름', ylabel: 'y축 이름', dash: '점선'},
  enums: {left: '왼쪽', right: '오른쪽', normal: '보통', conical: '원뿔 진자'}, none: '(없음)',
  texHint: 'm_1, v_0^2, \\theta, \\vec{F}, \\dot{x}, \\frac{a}{b}, \\hbar 처럼 TeX로 쓰거나 Ω 단추로 기호를 넣으세요. 아래 미리보기가 그림에 들어가는 모양입니다.',
  out: '내보내기', svg: 'SVG 내려받기', png: 'PNG 내려받기 (2배)',
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
  unsupported: {held_by_figure: 'it rests on or hangs from a part that is not computed (a plank, a track, a line, a shape, a liquid), so it stays put', hanging_not_vertical: 'a hanging body is not straight below its pulley', tied_not_on_surface: 'two bodies tied without a pulley must rest on surfaces', spring_between_systems: 'a spring joins bodies that move in different kinds of systems', pivot_over_pulley: 'a string from a pivot over pulleys is not computed yet', pendulum_on_surface: 'the pendulum bob rests on a surface', pendulum_with_spring: 'the pendulum has a spring', zero_length: 'the string has no length', conical_angle: 'a conical pendulum needs an angle between 0° and 88°', spring_surface_and_air: 'a spring joins a body on a surface and one in the air'},
  notSim: 'not computed', nothing: 'Nothing here can move.',
  scene: 'Figure', sceneTitle: 'Name', g: 'Gravity g (m/s²)', gridSize: 'Grid step (m)', objects: 'In the figure', noSel: 'Click an object in the figure to edit its values.',
  fields: {x: 'x (m)', y: 'y (m)', w: 'Width (m)', h: 'Height (m)', r: 'Radius (m)', mass: 'Mass (kg)', label: 'Label', on: 'Rests on', at: 'Position on it (m)', vx: 'Initial vx (m/s)', vy: 'Initial vy (m/s)', showV: 'Velocity arrow', vLabel: 'Velocity label', trail: 'Show its path',
    mu: 'Friction μ', hatch: 'Hatching', side: 'Solid side', angle: 'Angle (°)', length: 'Slope length (m)', flip: 'Rises to the left', angleLabel: 'Angle label', mount: 'Fixed to', a: 'One end', b: 'Other end', over: 'Over pulleys', mode: 'Motion', k: 'Spring constant k (N/m)', L0: 'Natural length (m)', coils: 'Coils',
    F: 'Magnitude (N)', len: 'Arrow length (m)', text: 'Text', size: 'Size', x1: 'x₁', y1: 'y₁', x2: 'x₂', y2: 'y₂', offset: 'Offset (m)', from: 'From (°)', to: 'To (°)', lx: 'x-axis length', ly: 'y-axis length', xlabel: 'x label', ylabel: 'y label', dash: 'Dashed'},
  enums: {left: 'Left', right: 'Right', normal: 'Normal', conical: 'Conical pendulum'}, none: '(none)',
  texHint: 'Write TeX such as m_1, v_0^2, \\theta, \\vec{F}, \\dot{x}, \\frac{a}{b}, \\hbar, or insert symbols with the Ω button. The preview is how the figure will show it.',
  out: 'Export', svg: 'Download SVG', png: 'Download PNG (2×)',
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
  domains: {mech: '역학', em: '전자기', thermo: '열', optics: '광학', waves: '파동', modern: '현대물리', general: '일반', geo: '작도'},
  search: '찾기 (예: 저항, lens, 우물)', style: '그림체', symbols: 'Ω 기호', symTitle: '그리스 문자 · 물리 기호', symHint: '누르면 선택한 글자 칸(없으면 새 글자)에 넣습니다. TeX로 직접 써도 됩니다.',
  solve: '회로 풀기 (전류·전압)', info: '계산값', circuit: '회로', noCircuit: {empty: '회로 소자가 없습니다.', ac: '교류 전원이 있는 회로는 풀지 않습니다.', short: '이상적인 전원이 단락되었거나 전압원 고리가 있어 풀 수 없습니다.'},
  tau: '시간 상수 τ', vFinal: '나중 전압', iFinal: '나중 전류', rth: '테브난 저항', charging: id => `${id} 충전 곡선 V(t)`, current: '전류', drop: '전압', element: '소자',
  infoT: {rails: c => `유도 기전력 ε = BLv = ${c.emf} V, 전류 I = ${c.I} A, 자기력 F = BIL = ${c.F} N`, buoyancy: c => `부력 ${c.B} N, 무게 ${c.W} N${c.floats < 1 ? `, 뜬다면 잠기는 비율 ${c.floats}` : ', 가라앉음'}`, bridge: c => `접점 위치 l = ${c.l} cm (평형: R/S = l/(100 − l))`,
    cycle: (c) => `W = ${c.W}, Q_in = ${c.Qin}, η = ${c.eta} (카르노 한계 ${c.carnot})`, oarrow: c => `상 위치 x = ${c.x} m, 배율 m = ${c.m} (${c.real ? '실상' : '허상'})`, slits: c => `무늬 간격 Δy = λL/d = ${c.dy}`, well: c => `E = ${c.E}${c.T !== undefined ? `, 투과율 T = ${c.T}` : ''}`, qpot: c => `속박 준위 E = ${c.E || '없음'}${c.T !== undefined ? `, 투과율 T = ${c.T}` : ''}`, levels: c => c.trans, spacetime: c => `γ = ${c.gamma}`, curve: c => `일 W = ∫P dV = ${c.W}`},
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
  domains: {mech: 'Mechanics', em: 'E&M', thermo: 'Thermal', optics: 'Optics', waves: 'Waves', modern: 'Modern', general: 'General', geo: 'Construct'},
  search: 'Search (e.g. resistor, lens, well)', style: 'Style', symbols: 'Ω Symbols', symTitle: 'Greek letters and physics symbols', symHint: 'Click to insert into the selected text field (or a new label). TeX can be typed too.',
  solve: 'Solve the circuit (currents, voltages)', info: 'Computed', circuit: 'Circuit', noCircuit: {empty: 'No circuit elements.', ac: 'Circuits with an AC source are not solved.', short: 'An ideal source is shorted or a loop of voltage sources makes it unsolvable.'},
  tau: 'Time constant τ', vFinal: 'Final voltage', iFinal: 'Final current', rth: 'Thevenin resistance', charging: id => `charging of ${id}, V(t)`, current: 'Current', drop: 'Voltage', element: 'Element',
  infoT: {rails: c => `motional EMF ε = BLv = ${c.emf} V, current I = ${c.I} A, force F = BIL = ${c.F} N`, buoyancy: c => `buoyancy ${c.B} N, weight ${c.W} N${c.floats < 1 ? `, would float with ${c.floats} submerged` : ', sinks'}`, bridge: c => `jockey at l = ${c.l} cm (balance: R/S = l/(100 − l))`,
    cycle: c => `W = ${c.W}, Q_in = ${c.Qin}, η = ${c.eta} (Carnot limit ${c.carnot})`, oarrow: c => `image at x = ${c.x} m, magnification m = ${c.m} (${c.real ? 'real' : 'virtual'})`, slits: c => `fringe spacing Δy = λL/d = ${c.dy}`, well: c => `E = ${c.E}${c.T !== undefined ? `, transmission T = ${c.T}` : ''}`, qpot: c => `bound levels E = ${c.E || 'none'}${c.T !== undefined ? `, transmission T = ${c.T}` : ''}`, levels: c => c.trans, spacetime: c => `γ = ${c.gamma}`, curve: c => `work W = ∫P dV = ${c.W}`},
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
/* the drawing tools, the plain shapes, the typed potential, the start hint */
const X4 = ko ? {
  types: {rect: '사각형', ellipse: '원 · 타원', poly: '꺾은선 · 다각형 · 펜', bezier: '곡선 (베지어)', qpot: '퍼텐셜 직접 입력 V(x)'},
  fields: {color: '선 색', fill: '채우기', closed: '닫힌 도형', smooth: '부드럽게', pts: '점', cx1: '조절점 1 x', cy1: '조절점 1 y', cx2: '조절점 2 x', cy2: '조절점 2 y', params: '매개변수 (이름=값 [최소, 최대], …)', V: '퍼텐셜 V(x) (eV, x는 nm)',
    xmin: 'x 시작 (nm)', xmax: 'x 끝 (nm)', showV: 'V(x) 그리기', tplot: '투과율 T(E) 그래프', Emax: '에너지 축 위 끝 (eV, 0: 자동)', psiQ: '그릴 것', levelsQ: '속박 상태 수', EQ: '산란 에너지 E (eV, 0: 없음)', speedArrow: '속도 화살표', mass: '질량 (전자 질량 배)'},
  enums: {black: '검정', gray: '회색', lightgray: '연회색', blue: '파랑', red: '빨강', green: '초록', orange: '주황', white: '흰색', tint: '선 색 옅게'},
  tools: {select: '선택·이동 (V)', line: '선 (L)', arrow: '화살표 (A)', poly: '꺾은선: 누를 때마다 점, 두 번 누르거나 Enter로 끝 (Y)', curve: '곡선: 끌어서 그린 뒤 조절점을 옮기세요 (C)', rect: '사각형 (R)', rrect: '둥근 사각형', ellipse: '원·타원, Shift: 정원 (O)', arc: '호: 중심, 시작점, 끝점을 차례로', polygon: '다각형: 점을 찍고 첫 점을 누르거나 Enter (G)',
    pen: '펜: 손으로 그리기 (P)', text: '글자 (T)', dim: '치수선 (D)', angle: '각도 표시: 꼭짓점, 한쪽 변, 다른 변을 차례로', fill: '채우기: 도형을 누르세요 (F)', eraser: '지우개: 누르거나 끌어서 지우기 (E)'},
  style: {color: '색', width: '굵기', dash: '선 모양', fill: '채우기', heads: '화살촉', start: '시작', end: '끝'},
  parts: '물리 부품', partsHint: '상자, 도르래, 회로 소자, 렌즈… 값으로 움직이는 부품', templates: '템플릿 (완성된 그림)', drawing: '그리기 도구',
  hint: ['그리기 도구로 시작: 선, 화살표, 도형, 펜으로 그리세요.', '물리 부품 추가: ‘물리 부품’ 칸에서 상자·도르래·회로·렌즈 등을 넣으세요.', '값 조절 · 내보내기: 오른쪽에서 값과 슬라이더로 고치고 SVG·PNG·시험지로 보내세요.'], hintClose: '알겠어요', hintTitle: '처음이라면',
  draftHint: {poly: '점을 찍으세요. 두 번 누르거나 Enter로 끝, Esc로 취소', polygon: '점을 찍으세요. 첫 점을 누르거나 Enter로 닫기', arc: '중심 → 시작점 → 끝점', angle: '꼭짓점 → 한쪽 변 위의 점 → 다른 변 위의 점'},
  lede: '선·화살표·도형·펜으로 간단히 그리고, 필요하면 물리 부품과 템플릿을 더합니다. 같은 그림을 시험지에 넣거나 시뮬레이션·계산으로 확인할 수 있습니다.'
} : {
  types: {rect: 'Rectangle', ellipse: 'Circle, ellipse', poly: 'Polyline, polygon, pen', bezier: 'Curve (Bézier)', qpot: 'Typed potential V(x)'},
  fields: {color: 'Line colour', fill: 'Fill', closed: 'Closed', smooth: 'Smooth', pts: 'Points', cx1: 'Control 1 x', cy1: 'Control 1 y', cx2: 'Control 2 x', cy2: 'Control 2 y', params: 'Parameters (name=value [min, max], …)', V: 'Potential V(x) (eV, x in nm)',
    xmin: 'x from (nm)', xmax: 'x to (nm)', showV: 'Draw V(x)', tplot: 'Transmission T(E) plot', Emax: 'Top of the energy axis (eV, 0: auto)', psiQ: 'Draw', levelsQ: 'Bound states', EQ: 'Scattering energy E (eV, 0: none)', speedArrow: 'Velocity arrow', mass: 'Mass (electron masses)'},
  enums: {black: 'Black', gray: 'Gray', lightgray: 'Light gray', blue: 'Blue', red: 'Red', green: 'Green', orange: 'Orange', white: 'White', tint: 'Light line colour'},
  tools: {select: 'Select and move (V)', line: 'Line (L)', arrow: 'Arrow (A)', poly: 'Polyline: click for each point, double-click or Enter ends (Y)', curve: 'Curve: drag, then move its handles (C)', rect: 'Rectangle (R)', rrect: 'Rounded rectangle', ellipse: 'Circle, ellipse; Shift: circle (O)', arc: 'Arc: centre, start, end', polygon: 'Polygon: click the points, then the first one or Enter (G)',
    pen: 'Pen: freehand (P)', text: 'Text (T)', dim: 'Dimension (D)', angle: 'Angle mark: vertex, a point on each side', fill: 'Fill: click a shape (F)', eraser: 'Eraser: click or drag over (E)'},
  style: {color: 'Colour', width: 'Width', dash: 'Line', fill: 'Fill', heads: 'Arrowheads', start: 'Start', end: 'End'},
  parts: 'Physics parts', partsHint: 'Blocks, pulleys, circuit elements, lenses… parts that move by value', templates: 'Templates (finished figures)', drawing: 'Drawing tools',
  hint: ['Start with the drawing tools: lines, arrows, shapes, the pen.', 'Add physics parts: blocks, pulleys, circuits, lenses from the “Physics parts” panel.', 'Adjust and export: change values and sliders on the right, then SVG, PNG or the test paper.'], hintClose: 'Got it', hintTitle: 'New here?',
  draftHint: {poly: 'Click points. Double-click or Enter ends, Esc cancels', polygon: 'Click points. Click the first point or press Enter to close', arc: 'Centre → start → end', angle: 'Vertex → a point on one side → a point on the other'},
  lede: 'Draw simply with lines, arrows, shapes and the pen, then add physics parts and templates when you need them. Put a figure on a test paper, or check it with a simulation or a calculation.'
};
/* ── construction, physics for drawn shapes, per-object style, the reorganised symbol picker ── */
const X5 = ko ? {
  types: {gpoint: '점 (작도)', gline: '선분 · 직선 · 반직선', gcircle: '원 (작도)', gpoly: '다각형 (작도)', gangle: '각 (작도)', joint: '연결 (용수철 · 줄 · 막대)'},
  geoFields: {kind: '종류', a: '대상 1', b: '대상 2', c: '중심', p: '원 위의 점', n: '교점 번호 (0, 1)', pts: '꼭짓점'},
  fields: {base: '기준 직선', show: '점 보이기', measure: '값 표시 (길이 · 넓이 · 각)',
    expr2: '식 y(t)', rel: '부등호', tangent: '접선', tx: '접점 x', area: '넓이 (적분)', a1: '구간 시작 a', a2: '구간 끝 b', roots: '근 표시', extrema: '극값 표시', xstep: 'x 눈금 간격 (0: 자동)', ystep: 'y 눈금 간격 (0: 자동)',
    phys: '물리', pmass: '질량 (kg)', pvx: '처음 속도 vx (m/s)', pvy: '처음 속도 vy (m/s)', pw: '처음 각속도 ω (rad/s)', pmu: '마찰 계수 μ', pe: '반발 계수 e', pfx: '가한 힘 Fx (N)', pfy: '가한 힘 Fy (N)',
    ax: '연결점 x (도형 중심에서)', ay: '연결점 y (도형 중심에서)', bx: '다른 끝 x', by: '다른 끝 y', damp: '감쇠 (N·s/m)', style: '그림체 (이 개체만)'},
  enums: {free: '자유로운 점', on: '대상 위의 점', mid: '중점', inter: '교점', segment: '선분', line: '직선', ray: '반직선', perp: '수선', par: '평행선', param: '매개변수 곡선 (x(t), y(t))', polar: '극좌표 r(θ)', ineq: '부등식 영역',
    lt: 'y < f(x)', le: 'y ≤ f(x)', gt: 'y > f(x)', ge: 'y ≥ f(x)', dynamic: '움직임 (동역학)', static: '고정 (바닥 · 벽 · 경사면)', spring: '용수철', string: '줄', rod: '막대'},
  styleInherit: s => `그림 전체 따름 (${s})`,
  geoTools: {gpoint: '점: 빈 곳을 누르면 자유로운 점, 선이나 원을 누르면 그 위의 점', gseg: '선분: 두 점', gline: '직선: 두 점', gray: '반직선: 시작점, 지나는 점', gcircle: '원: 중심, 원 위의 점', gcircleR: '원: 중심 (반지름은 값으로)', gpoly: '다각형: 꼭짓점들, 첫 점을 누르면 닫힘',
    gperp: '수선: 직선, 지나는 점', gpar: '평행선: 직선, 지나는 점', gmid: '중점: 두 점 또는 선분', ginter: '교점: 두 선 · 원', gangle: '각: 점, 꼭짓점, 점', gdist: '거리: 두 점 (길이 표시)'},
  geoGroup: '작도', geoHint: '작도 도구: 점을 누르거나 빈 곳을 눌러 새 점을 만듭니다. 자유로운 점(파란 테두리)을 끌면 그 점에 기대는 것이 모두 따라 움직입니다.',
  geoStep: {gseg: ['첫 점', '둘째 점'], gline: ['첫 점', '둘째 점'], gray: ['시작점', '지나는 점'], gdist: ['첫 점', '둘째 점'], gcircle: ['중심', '원 위의 점'], gperp: ['기준 직선', '지나는 점'], gpar: ['기준 직선', '지나는 점'], gmid: ['첫 점 (또는 선분)', '둘째 점'], ginter: ['첫 선 · 원', '둘째 선 · 원'], gangle: ['첫 점', '꼭짓점', '셋째 점'], gpoly: ['꼭짓점 (첫 점을 누르거나 Enter로 닫기)']},
  geoNeedLine: '직선(선분)을 먼저 누르세요', geoNeedPath: '선이나 원을 누르세요', geoNoCross: '두 대상이 만나지 않습니다',
  physTitle: '물리 적용', physHint: '그린 도형에 물리를 줍니다. ‘움직임’은 질량을 가지고 떨어지고 부딪히며, ‘고정’은 바닥 · 벽 · 경사면이 됩니다. ▶ 재생을 누르면 움직입니다.',
  physScene: '그린 도형의 물리', gravityOn: '중력 켜기', drag: '공기 저항 (1/s)', join: '연결하기', joinSpring: '용수철로 잇기', joinString: '줄로 잇기', joinRod: '막대로 잇기',
  joinHint: '다른 도형(물리 적용)을 누르거나, 빈 곳을 눌러 고정점에 잇습니다', trails: '궤적 · 속도 화살표', physNone: '물리 없음', physShapes: '물리 도형',
  sym: {title: '수식 기호', search: '찾기 (예: nabla, hbar, 플랑크, 아래첨자)', recent: '최근', tabs: {lower: '그리스 소문자', upper: '그리스 대문자', accent: '꾸밈', ops: '벡터 · 미분 연산자', rel: '관계 · 기호', const: '물리 상수', struct: '구조', chem: '화학식'},
    base: '기본 글자', accentHint: '글자를 고르고(또는 입력하고) 꾸밈을 누르세요', withValue: '값과 단위도 넣기', structHint: '구조를 넣으면 파란 빈칸이 선택됩니다. 글자를 쳐서 채우고 Tab으로 다음 빈칸으로 갑니다. 글자 바로 뒤에서 첨자를 누르면 그 글자에 붙습니다.',
    chemHint: '\\ce{…} 안에서는 원소 뒤 숫자가 아래첨자, ^2- 나 끝의 + − 가 전하가 됩니다', none: '찾은 기호가 없습니다', tooLong: '이 칸에는 너무 깁니다. 글자 개체로 넣었습니다.'}
} : {
  types: {gpoint: 'Point (construction)', gline: 'Segment, line, ray', gcircle: 'Circle (construction)', gpoly: 'Polygon (construction)', gangle: 'Angle (construction)', joint: 'Joint (spring, string, rod)'},
  geoFields: {kind: 'Kind', a: 'Object 1', b: 'Object 2', c: 'Centre', p: 'Point on it', n: 'Intersection (0, 1)', pts: 'Vertices'},
  fields: {base: 'Reference line', show: 'Show the point', measure: 'Show the value (length, area, angle)',
    expr2: 'y(t)', rel: 'Inequality', tangent: 'Tangent', tx: 'Tangent at x', area: 'Area (integral)', a1: 'From a', a2: 'To b', roots: 'Mark roots', extrema: 'Mark extrema', xstep: 'x tick step (0: auto)', ystep: 'y tick step (0: auto)',
    phys: 'Physics', pmass: 'Mass (kg)', pvx: 'Start velocity vx (m/s)', pvy: 'Start velocity vy (m/s)', pw: 'Start angular velocity ω (rad/s)', pmu: 'Friction μ', pe: 'Restitution e', pfx: 'Applied force Fx (N)', pfy: 'Applied force Fy (N)',
    ax: 'Attach x (from the centre)', ay: 'Attach y (from the centre)', bx: 'Other end x', by: 'Other end y', damp: 'Damping (N·s/m)', style: 'Style (this object only)'},
  enums: {free: 'Free point', on: 'Point on object', mid: 'Midpoint', inter: 'Intersection', segment: 'Segment', line: 'Line', ray: 'Ray', perp: 'Perpendicular', par: 'Parallel', param: 'Parametric (x(t), y(t))', polar: 'Polar r(θ)', ineq: 'Inequality region',
    lt: 'y < f(x)', le: 'y ≤ f(x)', gt: 'y > f(x)', ge: 'y ≥ f(x)', dynamic: 'Moves (dynamic)', static: 'Fixed (floor, wall, ramp)', spring: 'Spring', string: 'String', rod: 'Rod'},
  styleInherit: s => `Follow the figure (${s})`,
  geoTools: {gpoint: 'Point: on empty space a free point, on a line or circle a point on it', gseg: 'Segment: two points', gline: 'Line: two points', gray: 'Ray: start, a point it passes', gcircle: 'Circle: centre, a point on it', gcircleR: 'Circle: centre (radius as a value)', gpoly: 'Polygon: vertices, click the first to close',
    gperp: 'Perpendicular: a line, a point', gpar: 'Parallel: a line, a point', gmid: 'Midpoint: two points or a segment', ginter: 'Intersection: two lines or circles', gangle: 'Angle: point, vertex, point', gdist: 'Distance: two points (length shown)'},
  geoGroup: 'Construct', geoHint: 'Construction tools: click a point, or empty space for a new one. Drag a free point (blue ring) and everything built on it follows.',
  geoStep: {gseg: ['first point', 'second point'], gline: ['first point', 'second point'], gray: ['start', 'a point it passes'], gdist: ['first point', 'second point'], gcircle: ['centre', 'a point on it'], gperp: ['a line', 'a point'], gpar: ['a line', 'a point'], gmid: ['first point (or a segment)', 'second point'], ginter: ['first line or circle', 'second line or circle'], gangle: ['first point', 'vertex', 'third point'], gpoly: ['vertices (click the first or press Enter to close)']},
  geoNeedLine: 'Click a line (segment) first', geoNeedPath: 'Click a line or a circle', geoNoCross: 'The two do not meet',
  physTitle: 'Physics', physHint: 'Give a drawn shape physics. ‘Moves’ has a mass, falls and collides; ‘Fixed’ becomes a floor, wall or ramp. Press ▶ Play.',
  physScene: 'Physics of the drawn shapes', gravityOn: 'Gravity on', drag: 'Air drag (1/s)', join: 'Join', joinSpring: 'Join with a spring', joinString: 'Join with a string', joinRod: 'Join with a rod',
  joinHint: 'Click another shape with physics, or empty space for a fixed point', trails: 'Trails and velocity arrows', physNone: 'No physics', physShapes: 'Physics shapes',
  sym: {title: 'Maths symbols', search: 'Search (e.g. nabla, hbar, planck, subscript)', recent: 'Recent', tabs: {lower: 'Greek lower case', upper: 'Greek capitals', accent: 'Accents', ops: 'Vector & calculus', rel: 'Relations & signs', const: 'Constants', struct: 'Structures', chem: 'Chemistry'},
    base: 'Base letter', accentHint: 'Pick (or type) a letter, then an accent', withValue: 'Insert the value and unit too', structHint: 'A structure comes with its first blue box selected: type to fill it, Tab goes to the next box. Right after a letter, a script attaches to it.',
    chemHint: 'Inside \\ce{…} a number after an element is a subscript, ^2- or a closing + − is the charge', none: 'No symbol found', tooLong: 'Too long for this field: added as a label.'}
};
Object.assign(X4.types, X5.types); Object.assign(X4.fields, X5.fields); Object.assign(X4.enums, X5.enums);
T.connect.joint = X5.joinHint;
Object.assign(X4.types, ko ? {nnet: '신경망 (인공지능 가중치 네트워크)', fbox: '블록 (블록 선도)', farrow: '블록 화살표'} : {nnet: 'Neural network', fbox: 'Block (block diagram)', farrow: 'Block arrow'});
Object.assign(X4.fields, ko ? {layers: '층마다 노드 수 (예: 2,3,1)', inLabels: '입력 이름 (쉼표로)', outLabels: '출력 이름 (쉼표로)', act: '활성화 함수 표시', bias: '편향 노드 (+1)', weights: '가중치 행렬 (행은 /, 층 사이는 ;)', wstyle: '가중치 표시', wlabels: '가중치 글자 (w_ij)', nodeR: '노드 반지름 (m)', shape: '모양', route: '꺾는 방향', sign: '부호 (+, −)'}
  : {layers: 'Nodes per layer (e.g. 2,3,1)', inLabels: 'Input names (comma separated)', outLabels: 'Output names (comma separated)', act: 'Activation label', bias: 'Bias nodes (+1)', weights: 'Weight matrices (rows by /, layers by ;)', wstyle: 'Show weights as', wlabels: 'Weight labels (w_ij)', nodeR: 'Node radius (m)', shape: 'Shape', route: 'Route', sign: 'Sign (+, −)'});
Object.assign(X4.enums, ko ? {width: '선 굵기', color: '색 (+ 파랑, − 빨강)', round: '둥근 상자', circle: '원', diamond: '마름모', sum: '합산점', hv: '가로 먼저', vh: '세로 먼저', straight: '곧게'} : {width: 'Line width', color: 'Colour (+ blue, − red)', round: 'Rounded', circle: 'Circle', diamond: 'Diamond', sum: 'Summing junction', hv: 'Horizontal first', vh: 'Vertical first', straight: 'Straight'});
T.connect.farrow = ko ? '블록 화살표: 시작 블록을 누른 뒤 끝 블록을 누르세요.' : 'Block arrow: click the block it starts from, then the one it goes to.';
/* the symbol picker, like an equation editor: [tex, names (Korean and English, for the search)] by tab */
const GK = ['alpha 알파', 'beta 베타', 'gamma 감마', 'delta 델타', 'epsilon 엡실론', 'varepsilon 엡실론', 'zeta 제타', 'eta 에타', 'theta 세타', 'vartheta 세타', 'iota 요타', 'kappa 카파', 'lambda 람다', 'mu 뮤', 'nu 뉴', 'xi 크사이', 'pi 파이', 'varpi 파이', 'rho 로', 'varrho 로', 'sigma 시그마', 'varsigma 시그마', 'tau 타우', 'upsilon 입실론', 'phi 파이', 'varphi 파이', 'chi 카이', 'psi 프사이', 'omega 오메가'];
const GKU = ['Gamma 감마', 'Delta 델타', 'Theta 세타', 'Lambda 람다', 'Xi 크사이', 'Pi 파이', 'Sigma 시그마', 'Upsilon 입실론', 'Phi 파이', 'Psi 프사이', 'Omega 오메가'];
const ACCENTS = [['\\vec{#}', 'vector arrow 벡터 화살표'], ['\\mathbf{#}', 'bold vector 굵은 벡터'], ['\\boldsymbol{#}', 'bold italic 굵은 기울임'], ['\\hat{#}', 'hat unit vector 단위 벡터 모자'], ['\\dot{#}', 'dot time derivative 점 시간 미분'], ['\\ddot{#}', 'double dot 점 두 개 이계 미분'],
  ['\\bar{#}', 'bar mean 바 평균'], ['\\tilde{#}', 'tilde 물결'], ["#'", 'prime 프라임 미분'], ["#''", 'double prime 이계 프라임'], ['#^\\dagger', 'dagger 대거 수반'], ['\\overrightarrow{#}', 'overrightarrow 긴 화살표'], ['\\overline{#}', 'overline 윗줄'], ['\\underline{#}', 'underline 밑줄'], ['\\check{#}', 'check 체크']];
const ACC_BASES = ['x', 'y', 'z', 'r', 'v', 'a', 'p', 'F', 'E', 'B', 'A', 'L', 'J', 'n', 'k', 'u', 'R', 'H', '\\omega', '\\theta', '\\phi', '\\psi', '\\mu', '\\sigma', '\\tau', '\\rho'];
const SYMTAB = {
  lower: GK.map(s => { const [n, k] = s.split(' '); return ['\\' + n, n + ' ' + k]; }),
  upper: GKU.map(s => { const [n, k] = s.split(' '); return ['\\' + n, n + ' 대문자 ' + k]; }),
  ops: [['\\nabla', 'nabla del gradient 나블라 기울기'], ['\\nabla\\cdot', 'divergence 발산'], ['\\nabla\\times', 'curl 회전'], ['\\nabla^2', 'laplacian 라플라시안'], ['\\partial', 'partial 편미분'], ['\\partial_t', 'partial t 시간 편미분'],
    ['\\frac{\\partial}{\\partial t}', 'partial derivative d/dt 편미분'], ['\\frac{d}{dt}', 'derivative d/dt 미분'], ['\\mathrm{d}', 'differential d 미분'], ['\\int', 'integral 적분'], ['\\oint', 'contour integral 선적분 폐곡선'], ['\\iint', 'double integral 이중적분'], ['\\iiint', 'triple integral 삼중적분'],
    ['\\sum', 'sum 합 시그마'], ['\\prod', 'product 곱'], ['\\lim', 'limit 극한'], ['\\Delta', 'delta change 변화량'], ['\\langle \u2B1A \\rangle', 'expectation bracket 기댓값 꺾쇠'], ['\\ket{\u2B1A}', 'ket 켓'], ['\\bra{\u2B1A}', 'bra 브라'], ['\\braket{\u2B1A|\u2B1A}', 'braket 브라켓 내적'],
    ['\\hat{H}', 'hamiltonian operator 해밀토니안 연산자'], ['\\nabla\\times\\vec{B}', 'curl B 회전'], ['\\nabla\\cdot\\vec{E}', 'divergence E 발산'], ['\\oint \\vec{B}\\cdot d\\vec{l}', 'ampere 앙페르 선적분']],
  rel: [['\\approx', 'approx 근사'], ['\\neq', 'not equal 같지 않음'], ['\\le', 'less equal 작거나 같음'], ['\\ge', 'greater equal 크거나 같음'], ['\\ll', 'much less 훨씬 작음'], ['\\gg', 'much greater 훨씬 큼'], ['\\propto', 'proportional 비례'], ['\\sim', 'similar order 대략'],
    ['\\simeq', 'simeq 거의 같음'], ['\\equiv', 'equiv 정의 항등'], ['\\pm', 'plus minus 플러스 마이너스'], ['\\mp', 'minus plus'], ['\\times', 'times cross 곱하기 외적'], ['\\cdot', 'cdot dot 점곱 내적'], ['\\div', 'divide 나누기'], ['\\infty', 'infinity 무한대'], ['^\\circ', 'degree 도'],
    ["'", 'prime 프라임'], ['\\to', 'arrow to 화살표'], ['\\leftarrow', 'left arrow 왼쪽 화살표'], ['\\leftrightarrow', 'both arrow 양쪽 화살표'], ['\\Rightarrow', 'implies 이면'], ['\\Leftrightarrow', 'iff 동치'], ['\\uparrow', 'up 위'], ['\\downarrow', 'down 아래'],
    ['\\perp', 'perpendicular 수직'], ['\\parallel', 'parallel 평행'], ['\\angle', 'angle 각'], ['\\triangle', 'triangle 삼각형'], ['\\odot', 'out of page 나오는 방향'], ['\\otimes', 'into page 들어가는 방향'], ['\\in', 'in element 원소'], ['\\forall', 'for all 모든'], ['\\exists', 'exists 존재'], ['\\ldots', 'dots 점점점'], ['\\hbar', 'hbar 디랙 상수']],
  const: [['c', 'speed of light 빛의 속력', '2.998\\times10^{8}', 'm/s'], ['h', 'planck 플랑크 상수', '6.626\\times10^{-34}', 'J\\,s'], ['\\hbar', 'hbar reduced planck 환산 플랑크 상수 디랙', '1.055\\times10^{-34}', 'J\\,s'],
    ['e', 'elementary charge 기본 전하 전자 전하량', '1.602\\times10^{-19}', 'C'], ['m_e', 'electron mass 전자 질량', '9.109\\times10^{-31}', 'kg'], ['m_p', 'proton mass 양성자 질량', '1.673\\times10^{-27}', 'kg'], ['m_n', 'neutron mass 중성자 질량', '1.675\\times10^{-27}', 'kg'],
    ['\\varepsilon_0', 'permittivity epsilon0 진공 유전율', '8.854\\times10^{-12}', 'F/m'], ['\\mu_0', 'permeability mu0 진공 투자율', '1.257\\times10^{-6}', 'N/A^2'], ['k_B', 'boltzmann 볼츠만 상수', '1.381\\times10^{-23}', 'J/K'],
    ['k_e', 'coulomb constant 쿨롱 상수', '8.988\\times10^{9}', 'N\\,m^2/C^2'], ['G', 'gravitational constant 중력 상수 만유인력', '6.674\\times10^{-11}', 'N\\,m^2/kg^2'], ['N_A', 'avogadro 아보가드로 수', '6.022\\times10^{23}', 'mol^{-1}'],
    ['R', 'gas constant 기체 상수', '8.314', 'J/(mol\\,K)'], ['\\sigma', 'stefan boltzmann 슈테판 볼츠만 상수', '5.670\\times10^{-8}', 'W/(m^2\\,K^4)'], ['a_0', 'bohr radius 보어 반지름', '5.292\\times10^{-11}', 'm'],
    ['g', 'gravity 중력 가속도', '9.8', 'm/s^2'], ['\\mathrm{u}', 'atomic mass unit 원자 질량 단위', '1.661\\times10^{-27}', 'kg'], ['R_\\infty', 'rydberg 뤼드베리 상수', '1.097\\times10^{7}', 'm^{-1}'], ['\\alpha', 'fine structure 미세 구조 상수', '1/137.04', ''],
    ['\\lambda_C', 'compton wavelength 콤프턴 파장', '2.426\\times10^{-12}', 'm'], ['\\mathrm{eV}', 'electron volt 전자볼트', '1.602\\times10^{-19}', 'J']],
  struct: [['\u2B1A_{\u2B1A}', 'subscript 아래첨자'], ['\u2B1A^{\u2B1A}', 'superscript power 위첨자 거듭제곱'], ['\u2B1A_{\u2B1A}^{\u2B1A}', 'sub and superscript 위아래첨자'], ['\\frac{\u2B1A}{\u2B1A}', 'fraction 분수'], ['\\sqrt{\u2B1A}', 'square root 제곱근 루트'], ['\\sqrt[\u2B1A]{\u2B1A}', 'nth root 거듭제곱근'],
    ['\\overline{\u2B1A}', 'overline 윗줄'], ['\\vec{\u2B1A}', 'vector box 벡터'], ['\\hat{\u2B1A}', 'hat box 모자'], ['\\frac{d\u2B1A}{d\u2B1A}', 'derivative 미분'], ['\\frac{d^2\u2B1A}{d\u2B1A^2}', 'second derivative 이계 미분'], ['\\frac{\\partial \u2B1A}{\\partial \u2B1A}', 'partial derivative 편미분'],
    ['\\int_{\u2B1A}^{\u2B1A} \u2B1A\\,d\u2B1A', 'integral limits 정적분'], ['\\oint \u2B1A\\,d\u2B1A', 'closed integral 폐곡선 적분'], ['\\sum_{\u2B1A}^{\u2B1A} \u2B1A', 'sum limits 합 시그마'], ['\\prod_{\u2B1A}^{\u2B1A} \u2B1A', 'product limits 곱'], ['\\lim_{\u2B1A \\to \u2B1A} \u2B1A', 'limit 극한'],
    ['|\u2B1A|', 'absolute value 절댓값'], ['\\langle \u2B1A \\rangle', 'average 평균'], ['\\pmatrix{\u2B1A & \u2B1A \\\\ \u2B1A & \u2B1A}', 'matrix 2x2 행렬'], ['\\vmatrix{\u2B1A & \u2B1A \\\\ \u2B1A & \u2B1A}', 'determinant 행렬식'], ['\\cases{\u2B1A & \u2B1A \\\\ \u2B1A & \u2B1A}', 'cases piecewise 경우 조각'],
    ['\u2B1A \\times 10^{\u2B1A}', 'scientific notation 과학적 표기'], ['\\mathrm{\u2B1A}', 'upright text 단위 정자체'], ['{}^{\u2B1A}_{\u2B1A}\\mathrm{\u2B1A}', 'nuclide 핵종 원자번호 질량수']],
  chem: [['\\ce{\u2B1A}', 'formula box 화학식 입력'], ['\\ce{H2O}', 'water 물'], ['\\ce{CO2}', 'carbon dioxide 이산화탄소'], ['\\ce{O2}', 'oxygen 산소'], ['\\ce{H2SO4}', 'sulfuric acid 황산'], ['\\ce{NaCl}', 'salt 염화나트륨'], ['\\ce{CaCO3}', 'calcium carbonate 탄산칼슘'],
    ['\\ce{SO4^2-}', 'sulfate ion 황산 이온'], ['\\ce{NH4+}', 'ammonium 암모늄 이온'], ['\\ce{OH-}', 'hydroxide 수산화 이온'], ['\\ce{H3O+}', 'hydronium 하이드로늄'], ['\\ce{Fe^3+}', 'iron ion 철 이온'], ['\\ce{Cu^2+}', 'copper ion 구리 이온'], ['\\ce{e-}', 'electron 전자'],
    ['\\ce{->}', 'reaction arrow 반응 화살표'], ['\\ce{<=>}', 'equilibrium 평형 화살표'], ['\\ce{(aq)}', 'aqueous 수용액'], ['\\ce{(s)}', 'solid 고체'], ['\\ce{(l)}', 'liquid 액체'], ['\\ce{(g)}', 'gas 기체'], ['\\ce{2H2 + O2 -> 2H2O}', 'reaction 반응식'],
    ['\\ce{N2 + 3H2 <=> 2NH3}', 'haber 하버 평형'], ['{}^{235}_{92}\\mathrm{U}', 'uranium nuclide 우라늄 핵종'], ['{}^{4}_{2}\\mathrm{He}', 'alpha helium 헬륨 알파']]
};
const SYM_RECENT = 'hlDrawSymRecent';
Object.assign(X3.types, X4.types); Object.assign(X3.fields, X4.fields); Object.assign(X3.enums, X4.enums);
Object.assign(X2.types, X3.types); Object.assign(X2.kinds, X3.kinds); Object.assign(X2.fields, X3.fields); Object.assign(X2.enums, X3.enums); Object.assign(X2.units, {rheostat: 'Ω', dielectric: 'μF'});
T.lede = X4.lede; Object.assign(T.types, X2.types); Object.assign(T.fields, X2.fields); Object.assign(T.enums, X2.enums);
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
    ['qpot', {}, N2('퍼텐셜 직접 입력: 유한 우물', 'Typed potential: finite well')], ['qpot', {V: 'x < 0 ? 0 : (x < a ? V0 : 0)', params: 'a=0.4 [0.05, 1.5], V0=4 [0, 10]', xmin: -1.2, xmax: 1.6, levels: 0, E: 2.5, tplot: true}, N2('퍼텐셜 직접 입력: 장벽 투과', 'Typed potential: barrier')],
    ['qpot', {V: '0.5 k x^2', params: 'k=2 [0.2, 10]', xmin: -2.5, xmax: 2.5, levels: 4}, N2('퍼텐셜 직접 입력: 조화 진동자', 'Typed potential: harmonic')], ['qpot', {V: 'abs(x) > a + b/2 ? V0 : (abs(x) < b/2 ? Vb : 0)', params: 'a=0.5 [0.2, 1.5], b=0.12 [0, 0.8], V0=6 [0, 12], Vb=1.2 [0, 8]', xmin: -1.3, xmax: 1.3, levels: 3}, N2('퍼텐셜 직접 입력: 이중 우물', 'Typed potential: double well')],
    ['nucleus', {}, T.types.nucleus], ['particle', {kind: 'electron'}, N2('전자', 'Electron')], ['particle', {kind: 'photon'}, N2('광자 (물결 화살표)', 'Photon (wiggle)')], ['particle', {kind: 'alpha'}, N2('알파 입자', 'Alpha particle')], ['particle', {kind: 'proton'}, N2('양성자', 'Proton')], ['particle', {kind: 'neutron'}, N2('중성자', 'Neutron')], ['particle', {kind: 'positron'}, N2('양전자', 'Positron')], ['particle', {kind: 'neutrino'}, N2('중성미자', 'Neutrino')]],
  general: [['label', {}, T.types.label], ['label', {box: true, text: '\\text{box}'}, N2('글 상자', 'Text box')], ['vector', {}, T.types.vector], ['dim', {}, T.types.dim], ['arc', {}, T.types.arc], ['axes', {}, T.types.axes],
    ['line', {pattern: 'dashed'}, N2('점선', 'Dashed line')], ['line', {pattern: 'dotted'}, N2('점점선', 'Dotted line')], ['line', {pattern: 'solid', heads: 'end'}, N2('화살표 선', 'Arrow line')], ['region', {}, T.types.region], ['region', {fill: 'hatch'}, N2('빗금 영역', 'Hatched region')], ['point', {}, T.types.point], ['graph', {}, N2('함수 그래프', 'Function graph')], ['curve', {kind: 'func'}, N2('함수 곡선', 'Function curve')], ['curve', {kind: 'func', params: 'A=1 [0, 2], k=1 [0.1, 5]', expr: 'A sin(k x)'}, N2('매개변수 함수 (슬라이더)', 'Function with parameters (sliders)')],
    ['graph', {xlabel: 't', ylabel: 'v', grid: true, origin: '0'}, N2('v–t 그래프 (격자)', 'v–t graph (grid)')], ['curve', {kind: 'points', shade: true}, N2('꺾은선 (넓이 칠하기)', 'Polyline (shaded area)')], ['panel', {caption: '(가)'}, N2('그림 칸 (가)', 'Panel (a)')], ['panel', {caption: '(나)'}, N2('그림 칸 (나)', 'Panel (b)')],
    ['brace', {}, T.types.brace], ['callout', {}, T.types.callout], ['parrows', {}, T.types.parrows],
    ['curve', {kind: 'param', expr: 'cos(t)', expr2: 'sin(2t)', x1: 0, x2: 6.2832}, N2('매개변수 곡선 x(t), y(t)', 'Parametric curve x(t), y(t)')], ['curve', {kind: 'polar', expr: '1 + cos(t)', x1: 0, x2: 6.2832}, N2('극좌표 곡선 r(θ)', 'Polar curve r(θ)')],
    ['curve', {kind: 'ineq', expr: '0.5 x', rel: 'lt'}, N2('부등식 영역 y < f(x)', 'Inequality region y < f(x)')], ['curve', {kind: 'func', expr: 'x^2 - 1', x1: -2, x2: 2, tangent: true, tx: 1, area: true, a1: -1, a2: 1, roots: true, extrema: true}, N2('함수 분석 (접선·넓이·근·극값)', 'Function analysis (tangent, area, roots, extrema)')]],
  geo: [['gpoint', {}, N2('자유로운 점', 'Free point')], ['rect', {phys: 'dynamic', fill: 'lightgray'}, N2('물리 상자 (움직임)', 'Physics box (dynamic)')], ['ellipse', {phys: 'dynamic', fill: 'tint', color: 'red'}, N2('물리 공 (움직임)', 'Physics ball (dynamic)')],
    ['line', {phys: 'static', pattern: 'solid'}, N2('고정된 바닥 · 경사면 선', 'Fixed floor or ramp line')],
    ['nnet', {}, N2('신경망 (층 · 노드 · 가중치)', 'Neural network (layers, nodes, weights)')], ['nnet', {layers: '3,4,4,2', inLabels: 'x_1,x_2,x_3', outLabels: 'y_1,y_2', bias: true}, N2('심층 신경망 (편향 포함)', 'Deep network (with bias)')],
    ['fbox', {text: '$G(s)$'}, N2('블록 (상자)', 'Block (box)')], ['fbox', {shape: 'sum', w: 0.36, h: 0.36}, N2('합산점 ⊗', 'Summing junction')], ['fbox', {shape: 'diamond', w: 1.2, h: 0.7, text: '?'}, N2('판단 (마름모)', 'Decision (diamond)')], ['fbox', {shape: 'round', text: '시작'}, N2('시작 · 끝 (둥근 상자)', 'Start or end (rounded)')],
    ['farrow', {}, N2('블록 화살표 (두 블록 잇기)', 'Block arrow (join two blocks)')]]
};
const PAL_EN = {mech: 'block ball floor incline wall ceiling pulley pivot string rod spring force cart car wheel disk cylinder ring plank lever seesaw hinge track loop ramp', em: 'wire resistor rheostat battery cell dc ac capacitor dielectric inductor switch diode led bulb ammeter voltmeter galvanometer meter bridge potentiometer jockey transformer rails rod emf ground charge plate field lines B E current solenoid loop magnet', thermo: 'cylinder piston container liquid water buoyancy utube thermometer heater burner coil gas molecules pressure reservoir engine graph isotherm adiabat isobar isochore carnot otto stirling', optics: 'axis lens mirror prism slab object ray slit grating wavefront beam splitter half screen eye source laser bulb fiber', waves: 'wave standing travelling wavefront pulse interference', modern: 'well barrier step harmonic levels hydrogen photoelectric minkowski spacetime worldline frames nucleus particle electron photon alpha proton neutron', geo: 'point construction geometry segment line circle physics rigid box ball ramp', general: 'parametric polar inequality tangent area root extremum label text box vector dimension arc axes line dashed dotted arrow region hatch point graph function curve panel caption brace callout arrows'};

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
const SCENE_KEY = 'hlDrawScene', SAVES_KEY = 'hlDrawSaves', PREFS_KEY = 'hlDrawPrefs';
/* sel: the object whose values the panel shows; selection: every selected id (shift-click, a box drawn on empty space) */
const st = {scene: null, sel: '', selection: new Set(), hist: createHistory(250), connect: null, grid: true, snap: true, fbd: false, readouts: true, solve: false, circuit: null, dom: 'mech', q: '', lastText: null,
  sim: null, playing: false, animationFrame: 0, speed: 1, last: 0, trails: new Map(), samples: [], graph: '', ai: null, msg: '', drag: null, zoom: null, clip: null, gesture: null, marquee: null, space: false,
  tool: 'select', draft: null, dstyle: {color: 'black', lw: 1, pattern: 'solid', fill: 'none', hs: false, he: false}, rtrail: false, symTab: 'struct', symBase: 'x', symValue: false};
const clone = o => JSON.parse(JSON.stringify(o));
/* the member's choice: open with an example figure or an empty one (an empty canvas once the example was cleared) */
const prefs = () => { try { const p = JSON.parse(store.get(PREFS_KEY) || '{}'); return p && typeof p === 'object' ? p : {}; } catch (e) { return {}; } };
const setPref = (k, v) => store.set(PREFS_KEY, JSON.stringify({...prefs(), [k]: v}));
const EXAMPLE = 'incline_pulley';
const PROJECT_PAGES = 12;
const projectTitle = () => st.project?.title || st.scene?.title || (ko ? '제목 없는 프로젝트' : 'Untitled project');
const blankPage = () => ({...blankScene(), style: st.scene?.style || blankScene().style, view: {x: -0.5, y: -0.5, w: 4, h: 3}});
function decodeProject(raw) {
  const active = validateScene(raw);
  if (!active.ok) return null;
  if (raw.project?.version !== 1) return {title: '', index: 0, pages: [active.scene]};
  const {title, index, otherPages} = raw.project;
  if (!Array.isArray(otherPages) || otherPages.length >= PROJECT_PAGES || !Number.isInteger(index) || index < 0 || index > otherPages.length) return null;
  const pages = otherPages.map(page => validateScene(page));
  if (pages.some(page => !page.ok)) return null;
  const scenes = pages.map(page => page.scene);
  scenes.splice(index, 0, active.scene);
  return {title: typeof title === 'string' ? title.trim().slice(0, 60) : '', index, pages: scenes};
}
function projectData() {
  const {title, index, pages} = st.project;
  return {...st.scene, project: {version: 1, title, index, otherPages: pages.filter((_, i) => i !== index)}};
}
function projectSignature() {
  const {title,index,pages} = st.project;
  return JSON.stringify([title,pages.map((page,i) => {
    const scene = i === index ? st.scene : page;
    return scene.view ? scene : {...scene,view:sceneBounds(scene)};
  })]);
}
function selectProjectPage(index, {bind = true, loaded = false} = {}) {
  const scene = st.project.pages[index];
  if (!scene) return;
  st.project.index = index;
  st.scene = clone(scene);
  if (!st.scene.view) st.scene.view = sceneBounds(st.scene);
  if (loaded) st.savedSignature = projectSignature();
  if (!bind) return;
  st.hist = createHistory(250);
  $('inkProposal').hidden = true;
  $('inkStatus').textContent = '';
  st.ai = null;
  st.zoom = null;
  keepShare(null);
  setSel([]);
  setTool('select');
  stopSim();
  save({changed: false});
  paint();
}
function addProjectPage(scene = blankPage()) {
  if (st.project.pages.length >= PROJECT_PAGES) { flash(ko ? '프로젝트당 그림을 최대 12개 만들 수 있습니다.' : 'A project can have up to 12 figures.'); return; }
  st.projectChanged = true;
  st.project.pages.push(scene);
  selectProjectPage(st.project.pages.length - 1);
}
function replaceProject(project, ids = null) {
  st.project = project;
  st.projectChanged = false;
  keepStoreIds(ids);
  selectProjectPage(project.index,{loaded:true});
}
function canLeaveProject() {
  if (st.storageBusy) return false;
  return !st.projectChanged || confirm(ko ? '현재 프로젝트를 보관함이나 이 브라우저에 저장하지 않고 다른 프로젝트를 열까요?' : 'Open another project without saving this one to storage or this browser?');
}
function paintProject() {
  if (!$('projectPages')) return;
  const {pages, index, title} = st.project;
  pages[index] = st.scene;
  $('projectTitle').value = title;
  $('projectPages').innerHTML = pages.map((page, i) => `<option value="${i}">${i + 1} · ${esc(page.title || (ko ? '그림' : 'Figure'))}</option>`).join('');
  $('projectPages').value = index;
  $('projectRemove').disabled = pages.length < 2;
  $('projectAdd').disabled = pages.length >= PROJECT_PAGES;
  $('saveStatus').textContent = st.projectChanged ? (ko ? '편집 중' : 'Edited') : '';
}
function startScene() {
  const t = params.get('t');
  if (t && TEMPLATE_KEYS.includes(t)) { st.unlinkedStart = true; st.dom = TEMPLATE_DOMAIN[t] || 'mech'; return validateScene(template(t, lang)).scene; }
  let saved = null;
  try { const raw = JSON.parse(store.get(SCENE_KEY) || 'null'), p = decodeProject(raw); if (p) { st.project = p; st.savedProject = raw.project?.version === 1; st.projectChanged = !!raw.project?.dirty; saved = p.pages[p.index]; } } catch (e) {}
  if (saved && (saved.objects.length || st.savedProject || st.project.pages.length > 1 || st.project.title)) return saved;
  if (prefs().example === false) return saved || {...blankScene(), view: {x: -0.5, y: -0.5, w: 4, h: 3}};
  return validateScene(template(EXAMPLE, lang)).scene;
}
const byId = id => st.scene.objects.find(o => o.id === id);
const view = () => st.scene.view || (st.scene.view = sceneBounds(st.scene));
/* the part of the world the canvas shows: the figure's frame, or the zoomed part of it */
const dview = () => st.zoom || view();
const selIds = () => [...st.selection].filter(id => byId(id));
const groupOf = id => st.scene.groups?.find(members => members.includes(id));
function setSel(ids, primary, {expand = true} = {}) { st.selection = new Set(ids.filter(Boolean).flatMap(id => (expand && groupOf(id)) || [id])); st.sel = primary && st.selection.has(primary) ? primary : st.selection.size === 1 ? [...st.selection][0] : st.selection.size ? (st.selection.has(st.sel) ? st.sel : [...st.selection].pop()) : ''; }
function toggleSelection(id) {
  const ids = new Set(selIds()), members = groupOf(id) || [id], remove = members.every(member => ids.has(member));
  members.forEach(member => remove ? ids.delete(member) : ids.add(member));
  setSel([...ids], id);
}
/* every change goes through here: checked, kept for undo (one step), saved in this browser */
function commit(next, {keepSel = false, before = null} = {}) {
  const r = validateScene(next);
  if (!r.ok) { flash(`<span class="bad">${T.invalid}: ${esc(r.errors.map(e => (e.id ? e.id + '.' : '') + (e.field || e.code)).slice(0, 3).join(', '))}</span>`); return false; }
  st.hist.record(before || JSON.stringify(st.scene));
  st.scene = r.scene; if (!keepSel) setSel(selIds(), st.sel);
  if (!st.scene.objects.length && prefs().example !== false) setPref('example', false);
  stopSim(); save(); paint(); return true;
}
function save({changed = true} = {}) {
  st.project.pages[st.project.index] = st.scene;
  if (changed) st.projectChanged = st.savedSignature !== projectSignature();
  const saved = projectData();
  saved.project.dirty = !!st.projectChanged;
  return store.set(SCENE_KEY, JSON.stringify(saved));
}
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
  lens: 'L', mirror: 'M', prism: 'pr', slab: 'sl', oarrow: 'O', ray: 'ray', slits: 'S', wavefront: 'wf', wave: 'wave', well: 'W', levels: 'lv', phototube: 'pt', spacetime: 'st', worldline: 'wl', frames: 'fr', vector: 'v', region: 'rg', point: 'pt', rect: 'rc', ellipse: 'el', poly: 'pg', bezier: 'bz', qpot: 'Q'};
const KIND_PREFIX = {rheostat: 'R', dielectric: 'C', wire: 'W', resistor: 'R', battery: 'E', cell: 'E', dc: 'E', ac: 'E', capacitor: 'C', inductor: 'L', switch: 'S', diode: 'D', led: 'D', bulb: 'B', ammeter: 'A', voltmeter: 'V', galvanometer: 'G'};
Object.assign(PREFIX, {gline: 'g', gcircle: 'ci', gpoly: 'pol', gangle: 'ang', joint: 'j'});
/* a construction point takes the next free capital letter (A, B, C …), as on a blackboard */
const freeId = (type, kind) => { if (type === 'gpoint') { for (const c of 'ABCDEFGHIJKLMNOPQRSTUVWXYZ') if (!byId(c)) return c; } const p = type === 'element' && KIND_PREFIX[kind] ? KIND_PREFIX[kind] : PREFIX[type] || 'o'; let n = 1; while (byId(p + n)) n++; return p + n; };
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
  else if (type === 'graph' || type === 'well' || type === 'levels' || type === 'qpot') box(0.6, 0.65);
  else if (type === 'rect' || type === 'ellipse') box(0.25, 0.2);
  else if (type === 'nnet') box(0.6, 0.55);
  else if (type === 'fbox') Object.assign(o, {x: cx, y: cy, w: r4(snapV(v.w * 0.18)) || 1, h: r4(snapV(v.h * 0.15)) || 0.6});
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
  if (type === 'farrow') { st.connect = {type, a: null, over: []}; setSel([]); paint(); return; }
  if (['string', 'rod', 'spring', 'force'].includes(type)) {
    const sel = byId(st.sel);
    if (type === 'force' && isBody(sel)) { finishConnect({type: 'force', a: sel.id}); return; }
    st.connect = {type, a: null, over: []}; setSel([]); paint(); return;
  }
  const next = clone(st.scene), o = {...defaults(type), id: freeId(type, preset.kind)};
  Object.assign(o, placeNew(type, preset, dview(), next), Object.fromEntries(Object.entries(preset).filter(([k]) => !(k === 'f' && (type === 'lens' || type === 'mirror')))));
  if (type === 'mirror' && preset.f === 0) o.f = 0;
  if (type === 'label' && !o.text) o.text = 'A';
  if (type === 'element' && !o.label) o.label = {resistor: 'R', capacitor: 'C', inductor: 'L', battery: '\\mathcal{E}', cell: '\\mathcal{E}', dc: '\\mathcal{E}', ac: '\\mathcal{E}', bulb: '', switch: 'S'}[o.kind] || '';
  if (type === 'element') o.value = {battery: 12, cell: 1.5, dc: 6, ac: 10, capacitor: 100, inductor: 0.1, diode: 0.7, led: 2, resistor: 100, bulb: 10, galvanometer: 0}[o.kind] ?? o.value;
  next.objects.push(o);
  if (commit(next)) { setSel([o.id]); paint(); }
}
/* a click while a string, rod, spring or force is being joined */
function connectClick(o, at) {
  const c = st.connect;
  /* a joint between drawn shapes with physics: the second end on another one, or on empty space a fixed point */
  if (c.type === 'joint') {
    if (o && isPhysShape(o) && o.id !== c.a) finishConnect({...c, b: o.id});
    else if (!o || !isPhysShape(o)) { const p = snapPt(at); finishConnect({...c, b: '', bx: p.x, by: p.y}); }
    return;
  }
  if (!o) return;
  if (c.type === 'farrow') { if (o.type !== 'fbox') return; if (!c.a) c.a = o.id; else if (o.id !== c.a) { finishConnect({...c, b: o.id}); return; } status(); paintCanvas(); return; }
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
  if (c.type === 'joint') Object.assign(o, {a: c.a, b: c.b, kind: c.kind, bx: c.b ? 0 : r4(c.bx), by: c.b ? 0 : r4(c.by), k: c.kind === 'spring' ? 40 : 50});
  else if (c.type === 'force') Object.assign(o, {on: c.a});
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
      if (o.type === 'vector' && gone.has(o.on)) setVectorAttachment(st.scene, o, '', o.vectorFrame);
      if (isBody(o) && o.on && gone.has(o.on)) { const p = bodyPose({...scene, objects: [...scene.objects, ...st.scene.objects.filter(x => x.id === o.on)]}, o); o.on = ''; o.x = r4(p.x); o.y = r4(p.y); }
      if (o.type === 'pulley' && gone.has(o.mount)) o.mount = '';
      if ((o.type === 'curve' || o.type === 'cycle') && gone.has(o.graph)) gone.add(o.id);
      if (o.type === 'worldline' && gone.has(o.diagram)) gone.add(o.id);
      if (o.type === 'joint' && (gone.has(o.a) || (o.b && gone.has(o.b)))) gone.add(o.id);
      if (o.type === 'farrow' && (gone.has(o.a) || gone.has(o.b))) gone.add(o.id);
      if (GEO_TYPES.includes(o.type) && (['a', 'b', 'c', 'p', 'base'].some(k => o[k] && gone.has(o[k])) || (o.type === 'gpoly' && o.pts.some(k => gone.has(k))))) gone.add(o.id);
    }
  }
}
function setVectorAttachment(scene, o, on, frame) {
  const points = vectorPoints(scene, o);
  o.on = on; o.vectorFrame = frame;
  const {toLocal} = vectorTransform(scene, o);
  points.map(toLocal).forEach((p,i) => { o['x'+(i+1)] = r4(p.x); o['y'+(i+1)] = r4(p.y); });
}
function groupSelection(ungroup = false) {
  const ids = selIds(), selected = new Set(ids);
  if (ids.length < 2) return;
  const next = clone(st.scene);
  next.groups = (next.groups || []).filter(members => !members.some(id => selected.has(id)));
  if (!ungroup) next.groups.push(ids);
  commit(next, {keepSel:true});
}
function del() { const ids = selIds(); if (!ids.length) return; const next = clone(st.scene); removeIds(next, ids); setSel([]); commit(next); }
/* copy and paste: the selected objects, and the strings, springs, forces and curves among them; pasted a few grid
   steps away with fresh ids (references inside the copy follow it, a body keeps the surface it rests on) */
const LINKS = ['string', 'rod', 'spring', 'force', 'curve', 'cycle', 'worldline'];
function copySel() {
  const ids = new Set(selIds()); if (!ids.size) return false;
  for (const o of st.scene.objects) if (LINKS.includes(o.type) && !ids.has(o.id)) { const refs = refsOf(o); if (refs.length && refs.every(r => ids.has(r))) ids.add(o.id); }
  st.clip = {objects:st.scene.objects.filter(o => ids.has(o.id)).map(clone),
    groups:(st.scene.groups || []).filter(members => members.every(id => ids.has(id))).map(clone)};
  try { sessionStorage.setItem('hlDrawClip', JSON.stringify(st.clip)); } catch (e) {}
  return true;
}
const refsOf = o => Object.entries(FIELDS[o.type]).flatMap(([k, f]) => f.k === 'ref' ? (o[k] ? [o[k]] : []) : f.k === 'refs' ? o[k] : []);
function pasteClip(offset = 3) {
  let clip = st.clip; if (!clip) { try { clip = JSON.parse(sessionStorage.getItem('hlDrawClip') || 'null'); } catch (e) { clip = null; } }
  if (Array.isArray(clip)) clip = {objects:clip};
  if (!Array.isArray(clip?.objects) || !clip.objects.length) return;
  const d = st.scene.grid * offset;
  return insertObjects(clip, d, -d);
}
function insertObjects(clip, dx, dy) {
  if (st.scene.objects.length + clip.objects.length > MAX_OBJECTS) { flash(`<span class="bad">${T.tooMany}</span>`); return; }
  const next = clone(st.scene), map = new Map(), made = [];
  const taken = new Set(next.objects.map(o => o.id)), fresh = (type, kind) => { const p = type === 'element' && KIND_PREFIX[kind] ? KIND_PREFIX[kind] : PREFIX[type] || 'o'; let n = 1; while (taken.has(p + n)) n++; taken.add(p + n); return p + n; };
  for (const o of clip.objects) map.set(o.id, fresh(o.type, o.kind));
  for (const o0 of clip.objects) {
    const o = {...clone(o0), id: map.get(o0.id)};
    let ok = true;
    for (const [k, f] of Object.entries(FIELDS[o.type] || {})) {
      if (f.k === 'ref' && o[k]) { if (map.has(o[k])) o[k] = map.get(o[k]); else if (!byId(o[k]) || LINKS.includes(o.type)) { if (LINKS.includes(o.type)) ok = false; else o[k] = ''; } }
      if (f.k === 'refs') { if (o[k].some(x => !map.has(x) && !byId(x))) ok = false; o[k] = o[k].map(x => map.get(x) || x); }
    }
    if (!ok) continue;
    if (!LINKS.includes(o.type)) moveObj(o, dx, dy, o0, map.has(o0.on));
    if (!clip.style && o.type === 'block' && /^m_\d+$/.test(o.label)) o.label = 'm_' + o.id.slice(1);
    next.objects.push(o); made.push(o.id);
  }
  if (clip.groups?.length) next.groups = [...(next.groups || []), ...clip.groups.map(ids => ids.map(id => map.get(id)))];
  if (!commit(next)) return false;
  setSel(made); paint();
  return true;
}
function dup() { if (copySel()) pasteClip(); }
/* move one object by (dx, dy) from its state `g`: a body on a surface slides along it (or keeps its place on a pasted
   surface), a segment moves both ends */
function moveObj(o, dx, dy, g = o, keepAt = false) {
  if (g.on && keepAt && (isBody(o) || o.type === 'vector')) return;
  if (o.type === 'vector' && o.on) {
    const {toWorld, toLocal} = vectorTransform(st.scene, o);
    for (const i of [1,2]) {
      const p = toWorld({x:g['x'+i],y:g['y'+i]}), q = toLocal({x:p.x+dx,y:p.y+dy});
      o['x'+i] = r4(q.x); o['y'+i] = r4(q.y);
    }
    return;
  }
  if (isBody(o) && g.on) { const s = st.scene.objects.find(x => x.id === g.on); if (s) { const fr = surfaceFrame(s, st.scene); o.at = r4(g.at + vec.dot({x: dx, y: dy}, fr.u)); return; } }
  if ('x1' in g && 'x2' in g && !('x' in g)) { o.x1 = r4(g.x1 + dx); o.y1 = r4(g.y1 + dy); o.x2 = r4(g.x2 + dx); o.y2 = r4(g.y2 + dy); if ('cx1' in g) { o.cx1 = r4(g.cx1 + dx); o.cy1 = r4(g.cy1 + dy); o.cx2 = r4(g.cx2 + dx); o.cy2 = r4(g.cy2 + dy); } return; }
  if (g.type === 'poly') { o.pts = g.pts.map(q => [r4(q[0] + dx), r4(q[1] + dy)]); return; }
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
  const drawn = st.draft ? {...sc, objects: [...sc.objects, draftObject()].filter(Boolean)} : sc;
  let svg = renderSVG(drawn, {width: W, view: v, edit: true, grid: st.grid && !simOn, selected: simOn ? [] : selIds(), forces, poses: shownPoses, labelScale: screenLabelScale(box), circuit: st.circuit, marquee: st.marquee,
    velocities: simOn ? st.sim.velocities() : null, anchors: simOn ? st.sim.anchors : null, trails: simOn ? [...st.trails].filter(([id]) => byId(id)?.trail || (st.rtrail && isPhysShape(byId(id)))) : null, ...simDrawOpts(simOn)});
  /* zoomed: the figure's frame (what is exported) as a thin dashed box */
  if (st.zoom) { const f = view(), S = W / v.w, x = (f.x - v.x) * S, y = (v.y + v.h - f.y - f.h) * S; svg = svg.replace(/<\/svg>$/, `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${(f.w * S).toFixed(1)}" height="${(f.h * S).toFixed(1)}" fill="none" stroke="#d97706" stroke-width="1.2" stroke-dasharray="7 4" pointer-events="none" class="frame"/></svg>`); }
  box.innerHTML = svg;
  box.classList.toggle('connecting', !!st.connect); box.classList.toggle('panning', st.space); box.dataset.tool = st.tool;
  const z = $('zoomPct'); if (z) z.textContent = `${Math.round(100 * view().w / v.w)}%`;
}
/* labels on screen: the 800-px drawing is shown at the canvas's width or, for a tall figure, at the height the canvas
   allows (68% of the window, at most 640 px), so its labels are drawn larger by what it is shrunk, to stay about
   12 px or more on screen (draw-render.mjs screenLabelScale) */
function screenLabelScale(box) {
  const v = dview(), wide = !matchMedia('(max-width:720px)').matches;
  return labelScaleFor((box.clientWidth || W) - 14, wide ? Math.min(innerHeight * 0.68, 640) : Infinity, W * v.h / v.w);
}
function conicalOrbit(s) {
  const P = [byId(s.a), byId(s.b)].find(o => o?.type === 'pivot'), b = [byId(s.a), byId(s.b)].find(isBody);
  if (!P || !b) return null; const p = bodyPose(st.scene, b);
  return {id: s.id, centre: {x: P.x, y: p.y}, radius: Math.abs(p.x - P.x)};
}
/* what the simulation adds to the drawing: the conical orbits, the rigid world's joints, velocities and trails */
function simDrawOpts(simOn) {
  const rig = simOn ? st.sim.systems.find(s => s.kind === 'rigid') : null;
  return {conical: (simOn ? st.sim.systems.filter(s => s.kind === 'conical').map(s => ({id: s.id, centre: s.centre, radius: s.radius})) : null) || st.scene.objects.filter(o => (o.type === 'string' || o.type === 'rod') && o.mode === 'conical').map(conicalOrbit).filter(Boolean),
    jointEnds: rig ? rig.jointWorld() : null, rigidV: rig && st.rtrail ? rig.velocities() : null};
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
const NO_DRAG = ['string', 'rod', 'spring', 'force', 'curve', 'cycle', 'worldline', 'fieldlines', 'gangle', 'joint', 'farrow'];
/* a construction object is dragged by its free points (a segment by both ends, a circle by its centre and point …);
   a point computed from others (a midpoint, an intersection) does not move by itself */
function geoDragIds(o) {
  if (!GEO_TYPES.includes(o.type)) return [o.id];
  if (o.type === 'gpoint') return o.kind === 'free' || o.kind === 'on' ? [o.id] : [];
  const refs = o.type === 'gpoly' ? o.pts : ['a', 'b', 'c', 'p'].map(k => o[k]).filter(Boolean);
  const out = new Set();
  for (const id of refs) { const x = byId(id); if (x) for (const y of geoDragIds(x)) out.add(y); }
  return [...out];
}
/* ── the drawing tools ──
   select (move, box-select), line, arrow, polyline, curve (a Bézier with two handles), rectangle, rounded rectangle,
   circle/ellipse, arc, polygon, pen (freehand, simplified and smoothed), text, dimension, angle mark, fill and eraser.
   A shape takes the current colour, line width, line pattern, fill and arrowheads (st.dstyle). Points snap to the
   points of the figure near them (ends, corners, vertices, terminals) or else to the grid; with Shift a segment turns
   in 15° steps (a rectangle or an ellipse becomes a square or a circle). */
const TOOLS = ['select', 'line', 'arrow', 'poly', 'curve', 'rect', 'rrect', 'ellipse', 'arc', 'polygon', 'pen', 'text', 'dim', 'angle', 'fill', 'eraser'];
const ic = d => `<svg viewBox="0 0 20 20" width="20" height="20" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
const TOOL_ICON = {select: ic('<path d="M5 3l10 7-4.5 1 2.5 5-2 1-2.5-5L5 15z" fill="currentColor" stroke="none"/>'), line: ic('<path d="M4 16L16 4"/>'), arrow: ic('<path d="M4 16L15 5M9 5h6v6"/>'),
  poly: ic('<path d="M3 15l5-9 4 7 5-9"/>'), curve: ic('<path d="M3 15C6 3 13 17 17 5"/><circle cx="3" cy="15" r="1.4" fill="currentColor"/><circle cx="17" cy="5" r="1.4" fill="currentColor"/>'), rect: ic('<rect x="3" y="5" width="14" height="10"/>'),
  rrect: ic('<rect x="3" y="5" width="14" height="10" rx="3.5"/>'), ellipse: ic('<ellipse cx="10" cy="10" rx="7" ry="5.5"/>'), arc: ic('<path d="M4 15A7 7 0 0 1 16 10"/><circle cx="10" cy="15" r="1" fill="currentColor"/>'),
  polygon: ic('<path d="M10 3l7 5-3 8H6L3 8z"/>'), pen: ic('<path d="M3 17c2-1 3-4 5-4s1 3 4 2 3-6 5-8"/>'), text: ic('<path d="M5 5h10M10 5v11"/>'), dim: ic('<path d="M3 7v8M17 7v8M3 11h14M6 9l-3 2 3 2M14 9l3 2-3 2"/>'),
  angle: ic('<path d="M3 16h14M3 16L14 5M8.5 16a5.5 5.5 0 0 0-1.6-3.9"/>'), fill: ic('<rect x="4" y="4" width="12" height="12"/><path d="M4 12l8-8M4 16l12-12M8 16l8-8M12 16l4-4" stroke-width="1"/>'), eraser: ic('<path d="M8 16l-4-4 8-8 5 5-7 7zM8 16h9M7 9l5 5"/>')};
const TOOL_KEY = {v: 'select', l: 'line', a: 'arrow', y: 'poly', c: 'curve', r: 'rect', o: 'ellipse', g: 'polygon', p: 'pen', t: 'text', d: 'dim', f: 'fill', e: 'eraser'};
const DRAG_TOOLS = ['line', 'arrow', 'curve', 'rect', 'rrect', 'ellipse', 'dim', 'pen'], CLICK_TOOLS = {poly: 0, polygon: 0, arc: 3, angle: 3};
const FILLABLE = ['rect', 'ellipse', 'poly', 'region'];
const headsOf = ds => ds.hs && ds.he ? 'both' : ds.he ? 'end' : ds.hs ? 'start' : 'none';
/* ── the construction tools (GeoGebra-like): each click picks a point (an existing one near the pointer, a new point
   on the line or circle under it, or a new free point), and the tool makes its object when it has what it needs ── */
const GEO_TOOLS = ['gpoint', 'gseg', 'gline', 'gray', 'gdist', 'gcircle', 'gcircleR', 'gpoly', 'gperp', 'gpar', 'gmid', 'ginter', 'gangle'];
const gi = d => ic(d);
const GEO_ICON = {gpoint: gi('<circle cx="10" cy="10" r="2.6" fill="currentColor"/>'), gseg: gi('<path d="M4 15L16 5"/><circle cx="4" cy="15" r="1.8" fill="currentColor"/><circle cx="16" cy="5" r="1.8" fill="currentColor"/>'),
  gline: gi('<path d="M1 18L19 2"/><circle cx="6" cy="13.5" r="1.8" fill="currentColor"/><circle cx="14" cy="6.5" r="1.8" fill="currentColor"/>'), gray: gi('<path d="M4 15L19 2"/><circle cx="4" cy="15" r="1.8" fill="currentColor"/><circle cx="12" cy="8" r="1.8" fill="currentColor"/>'),
  gdist: gi('<path d="M3 14L17 6"/><circle cx="3" cy="14" r="1.6" fill="currentColor"/><circle cx="17" cy="6" r="1.6" fill="currentColor"/><path d="M8 7l1.5 2.5" stroke-width="1"/><text x="9" y="18" font-size="6" fill="currentColor" stroke="none">cm</text>'),
  gcircle: gi('<circle cx="10" cy="10" r="7"/><circle cx="10" cy="10" r="1.5" fill="currentColor"/><circle cx="17" cy="10" r="1.5" fill="currentColor"/>'), gcircleR: gi('<circle cx="10" cy="10" r="7"/><circle cx="10" cy="10" r="1.5" fill="currentColor"/><path d="M10 10h7" stroke-dasharray="2 1.5"/>'),
  gpoly: gi('<path d="M4 16L7 4l10 4-2 8z"/><circle cx="4" cy="16" r="1.4" fill="currentColor"/><circle cx="7" cy="4" r="1.4" fill="currentColor"/><circle cx="17" cy="8" r="1.4" fill="currentColor"/>'),
  gperp: gi('<path d="M2 15h16M10 15V2M10 12h3v3"/>'), gpar: gi('<path d="M2 14L16 4M5 18L19 8"/>'), gmid: gi('<path d="M3 15L17 5"/><circle cx="10" cy="10" r="2.2" fill="currentColor"/>'),
  ginter: gi('<path d="M3 17L17 3M3 3l14 14"/><circle cx="10" cy="10" r="2" fill="currentColor"/>'), gangle: gi('<path d="M3 16h14M3 16L13 4M8 16a5 5 0 0 0-1.8-3.8"/>')};
function freeIdIn(scene, type) {
  const has = id => scene.objects.some(o => o.id === id);
  if (type === 'gpoint') for (const c of 'ABCDEFGHIJKLMNOPQRSTUVWXYZ') if (!has(c)) return c;
  const p = PREFIX[type] || 'o'; let n = 1; while (has(p + n)) n++; return p + n;
}
function geoDown(ev) {
  const t = st.tool, raw = worldAt(ev), hit0 = pickAt(ev), geo = computeGeometry(st.scene), tol = 11 * dview().w / W;
  if (st.scene.objects.length >= MAX_OBJECTS - 2) { flash(`<span class="bad">${T.tooMany}</span>`); return; }
  const dr = st.draft && st.draft.tool === t ? st.draft : (st.draft = {tool: t, picks: [], geo: true});
  const next = clone(st.scene);
  const add = o => { const id = freeIdIn(next, o.type); next.objects.push({...defaults(o.type), ...o, id, ...(o.type === 'gpoint' ? {label: o.label ?? id} : {})}); return id; };
  const nearPt = () => { let best = null, bd = tol; for (const x of st.scene.objects) if (x.type === 'gpoint') { const g = geo.get(x.id); if (g) { const d = Math.hypot(g.x - raw.x, g.y - raw.y); if (d < bd) { bd = d; best = x.id; } } } return best; };
  const pathHit = () => hit0 && ['gline', 'gcircle', 'gpoly'].includes(hit0.type) ? hit0 : null;
  const point = () => { const id = nearPt(); if (id) return id; const p = pathHit(); if (p) return add({type: 'gpoint', kind: 'on', a: p.id, x: r4(raw.x), y: r4(raw.y)}); const q = snapPt(raw); return add({type: 'gpoint', x: q.x, y: q.y}); };
  const done = (sel) => { st.draft = t === 'gpoint' || t === 'gcircleR' ? null : {tool: t, picks: [], geo: true}; if (commit(next)) { setSel(sel ? [sel] : []); paint(); } };
  const keep = () => { if (next.objects.length !== st.scene.objects.length) commit(next); setSel(dr.picks.filter(id => next.objects.some(o => o.id === id))); paint(); };
  if (t === 'gpoint') { done(point()); return; }
  if (t === 'gcircleR') { const c = point(); done(add({type: 'gcircle', c, r: Math.max(st.scene.grid * 5, 0.5)})); return; }
  if (t === 'gperp' || t === 'gpar') {
    if (!dr.picks.length) { if (hit0?.type !== 'gline') { flash(esc(X5.geoNeedLine)); return; } dr.picks.push(hit0.id); keep(); return; }
    const a = point(); done(add({type: 'gline', kind: t === 'gperp' ? 'perp' : 'par', a, base: dr.picks[0], pattern: 'dashed'})); return;
  }
  if (t === 'ginter') {
    const p = pathHit(); if (!p) { flash(esc(X5.geoNeedPath)); return; }
    if (!dr.picks.length || dr.picks[0] === p.id) { dr.picks = [p.id]; keep(); return; }
    const n = geoIntersect(geo.get(dr.picks[0]), geo.get(p.id)).length;
    if (!n) { flash(esc(X5.geoNoCross)); st.draft = {tool: t, picks: [], geo: true}; paint(); return; }
    let last = ''; for (let k = 0; k < Math.min(2, n); k++) last = add({type: 'gpoint', kind: 'inter', a: dr.picks[0], b: p.id, n: k});
    done(last); return;
  }
  if (t === 'gmid' && !dr.picks.length && !nearPt() && hit0?.type === 'gline') { done(add({type: 'gpoint', kind: 'mid', a: hit0.id})); return; }
  const id = point();
  if (t === 'gpoly' && dr.picks.length >= 3 && id === dr.picks[0]) { done(add({type: 'gpoly', pts: [...dr.picks]})); return; }
  if (dr.picks[dr.picks.length - 1] !== id) dr.picks.push(id);
  const need = {gseg: 2, gline: 2, gray: 2, gdist: 2, gcircle: 2, gmid: 2, gangle: 3}[t];
  if (need && dr.picks.length >= need) {
    const [a, b, c] = dr.picks;
    if (t === 'gcircle') done(add({type: 'gcircle', c: a, p: b}));
    else if (t === 'gmid') done(add({type: 'gpoint', kind: 'mid', a, b}));
    else if (t === 'gangle') done(add({type: 'gangle', a, b, c}));
    else done(add({type: 'gline', a, b, kind: t === 'gline' ? 'line' : t === 'gray' ? 'ray' : 'segment', measure: t === 'gdist'}));
    return;
  }
  keep();
}
/* Enter closes a polygon being constructed */
function geoFinish() {
  const dr = st.draft; if (!dr?.geo) return false;
  if (dr.tool === 'gpoly' && dr.picks.length >= 3) { const next = clone(st.scene), id = freeIdIn(next, 'gpoly'); next.objects.push({...defaults('gpoly'), id, pts: [...dr.picks]}); st.draft = {tool: 'gpoly', picks: [], geo: true}; if (commit(next)) { setSel([id]); paint(); } }
  else { st.draft = null; paint(); }
  return true;
}
function setTool(t) { st.tool = TOOLS.includes(t) || GEO_TOOLS.includes(t) ? t : 'select'; st.draft = null; st.connect = null; paintTools(); paintCanvas(); status(); }
/* the points a new point snaps to */
function snapTargets(exclude) {
  const out = [];
  for (const o of st.scene.objects) {
    if (o.id === exclude) continue;
    if ('x1' in o && 'y2' in o && typeof o.x1 === 'number') out.push({x: o.x1, y: o.y1}, {x: o.x2, y: o.y2});
    if (o.type === 'poly') o.pts.forEach(q => out.push({x: q[0], y: q[1]}));
    if (o.type === 'rect' || o.type === 'region' || o.type === 'ellipse') { const c = [[0, 0], [1, 0], [0, 1], [1, 1]]; if (o.type === 'ellipse') c.splice(0, 4, [0.5, 0], [0.5, 1], [0, 0.5], [1, 0.5], [0.5, 0.5]); c.forEach(([a, b]) => out.push({x: o.x + a * o.w, y: o.y + b * o.h})); }
    if (['point', 'arc', 'pivot', 'pulley', 'charge'].includes(o.type)) out.push({x: o.x, y: o.y});
    if (o.type === 'floor' || o.type === 'ceiling') out.push({x: o.x, y: o.y}, {x: o.x + o.w, y: o.y});
  }
  if (st.scene.objects.some(o => o.type === 'gpoint')) { const geo = computeGeometry(st.scene); for (const o of st.scene.objects) if (o.type === 'gpoint' && o.id !== exclude) { const g = geo.get(o.id); if (g) out.push({x: g.x, y: g.y}); } }
  return out;
}
function snapPt(p, {from = null, shift = false, exclude = ''} = {}) {
  if (from && shift) {
    const dx = p.x - from.x, dy = p.y - from.y, L = Math.hypot(dx, dy), a = Math.round(Math.atan2(dy, dx) / (Math.PI / 12)) * (Math.PI / 12);
    const L2 = st.snap ? Math.round(L / st.scene.grid) * st.scene.grid || L : L;
    return {x: r4(from.x + L2 * Math.cos(a)), y: r4(from.y + L2 * Math.sin(a))};
  }
  const tol = Math.max(10 * dview().w / W, st.snap ? st.scene.grid * 0.45 : 0);
  let best = null, bd = tol;
  for (const q of snapTargets(exclude)) { const d = Math.hypot(q.x - p.x, q.y - p.y); if (d < bd) { bd = d; best = q; } }
  if (best) return {x: r4(best.x), y: r4(best.y)};
  return {x: r4(snapV(p.x)), y: r4(snapV(p.y))};
}
function smoothInk(points, unit) {
  const first = points[0], last = points.at(-1);
  const dx = last.x - first.x, dy = last.y - first.y, length = Math.hypot(dx, dy);
  if (length >= 28 * unit && points.every(p => {
    const x = p.x - first.x, y = p.y - first.y, along = (x * dx + y * dy) / length;
    return Math.abs(x * dy - y * dx) / length <= 4 * unit && along >= -unit && along <= length + unit;
  })) return [first, last];
  return points.map((p, i) => {
    if (!i || i === points.length - 1) return p;
    const a = points[i - 1], b = points[i + 1];
    const before = {x:p.x-a.x,y:p.y-a.y}, after = {x:b.x-p.x,y:b.y-p.y};
    const turn = before.x * after.x + before.y * after.y;
    if (turn < .5 * Math.hypot(before.x,before.y) * Math.hypot(after.x,after.y)) return p;
    return {x: .2 * a.x + .6 * p.x + .2 * b.x, y: .2 * a.y + .6 * p.y + .2 * b.y};
  });
}
const deg = (c, p) => r4(Math.atan2(p.y - c.y, p.x - c.x) * 180 / Math.PI);
/* the object a draft makes (null while it is too small to be one) */
function shapeOf(dr) {
  const ds = st.dstyle, look = {color: ds.color, lw: ds.lw}, t = dr.tool, a = dr.a, b = dr.b;
  const tiny = 3 * dview().w / W;
  if (t === 'line' || t === 'arrow' || t === 'dim') {
    if (!b || Math.hypot(b.x - a.x, b.y - a.y) < tiny) return null;
    if (t === 'dim') return {type: 'dim', x1: a.x, y1: a.y, x2: b.x, y2: b.y, offset: 0, text: ''};
    return {type: 'line', x1: a.x, y1: a.y, x2: b.x, y2: b.y, pattern: ds.pattern, heads: t === 'arrow' ? (ds.hs ? 'both' : 'end') : headsOf(ds), ...look};
  }
  if (t === 'rect' || t === 'rrect' || t === 'ellipse') {
    if (!b) return null; let w = Math.abs(b.x - a.x), h = Math.abs(b.y - a.y);
    if (dr.shift) w = h = Math.max(w, h);
    if (w < tiny || h < tiny) return null;
    const x = b.x < a.x ? a.x - w : a.x, y = b.y < a.y ? a.y - h : a.y;
    return {type: t === 'ellipse' ? 'ellipse' : 'rect', x: r4(x), y: r4(y), w: r4(w), h: r4(h), ...(t === 'rrect' ? {r: r4(Math.min(w, h) * 0.18)} : {}), fill: ds.fill, pattern: ds.pattern === 'none' ? 'solid' : ds.pattern, ...look};
  }
  if (t === 'curve') {
    if (!b) return null; const dx = b.x - a.x, dy = b.y - a.y, L = Math.hypot(dx, dy); if (L < tiny) return null;
    const n = {x: -dy / L, y: dx / L}, k = 0.3 * L;
    return {type: 'bezier', x1: a.x, y1: a.y, x2: b.x, y2: b.y, cx1: r4(a.x + dx / 3 + n.x * k), cy1: r4(a.y + dy / 3 + n.y * k), cx2: r4(a.x + 2 * dx / 3 + n.x * k), cy2: r4(a.y + 2 * dy / 3 + n.y * k), pattern: ds.pattern, heads: headsOf(ds), ...look};
  }
  if (t === 'pen') {
    if (!dr.raw || dr.raw.length < 2) return null;
    const unit = dview().w / W;
    const raw = dr.smooth && dr.done ? smoothInk(dr.raw, unit) : dr.raw;
    const pts = dr.done ? simplifyPath(raw, (dr.smooth ? 1.2 : 0.6) * unit, 200) : raw;
    if (pts.length < 2) return null;
    return {type: 'poly', pts: pts.map(q => [r4(q.x), r4(q.y)]), smooth: dr.smooth && pts.length > 2, closed: false, fill: 'none', pattern: ds.pattern, heads: headsOf(ds), ...look};
  }
  if (t === 'poly' || t === 'polygon') {
    const pts = [...dr.pts, ...(dr.cur && !dr.done ? [dr.cur] : [])]; if (pts.length < 2) return null;
    const closed = t === 'polygon' && (dr.done || pts.length > 2);
    return {type: 'poly', pts: pts.map(q => [q.x, q.y]), closed, smooth: false, fill: closed ? ds.fill : 'none', pattern: ds.pattern, heads: closed ? 'none' : headsOf(ds), ...look};
  }
  if (t === 'arc' || t === 'angle') {
    const pts = [...dr.pts, ...(dr.cur && !dr.done ? [dr.cur] : [])]; if (pts.length < 2) return null;
    const c = pts[0], p1 = pts[1], p2 = pts[2] || null, R1 = Math.hypot(p1.x - c.x, p1.y - c.y); if (R1 < tiny) return null;
    if (t === 'arc') return {type: 'arc', x: c.x, y: c.y, r: r4(Math.max(0.02, R1)), from: deg(c, p1), to: p2 ? deg(c, p2) : r4(deg(c, p1) + 1), text: '', arrow: ds.he, pattern: ds.pattern, color: ds.color};
    if (!p2) return {type: 'line', x1: c.x, y1: c.y, x2: p1.x, y2: p1.y, pattern: 'dotted', heads: 'none'};
    let from = deg(c, p1), to = deg(c, p2), sweep = ((to - from) % 360 + 360) % 360;
    if (sweep > 180) [from, to] = [to, from];
    const R2 = Math.hypot(p2.x - c.x, p2.y - c.y);
    return {type: 'arc', x: c.x, y: c.y, r: r4(Math.max(0.03, 0.35 * Math.min(R1, R2))), from, to, text: '\\theta', arrow: false, color: ds.color};
  }
  return null;
}
function draftObject() { const o = st.draft && shapeOf(st.draft); return o ? {...defaults(o.type), ...o, id: 'zzDraft'} : null; }
function addShape(o) {
  if (!o) return;
  if (st.scene.objects.length >= MAX_OBJECTS) { flash(`<span class="bad">${T.tooMany}</span>`); return; }
  const next = clone(st.scene), id = freeId(o.type); next.objects.push({...defaults(o.type), ...o, id});
  if (commit(next)) { setSel([id]); paint(); }
  return id;
}
function finishDraft() { const dr = st.draft; if (!dr) return; dr.done = true; if (dr.pts) dr.pts = dr.pts.filter((q, i, a) => !i || Math.hypot(q.x - a[i - 1].x, q.y - a[i - 1].y) > 1e-9); const o = shapeOf(dr); st.draft = null; if (o) addShape(o); else paintCanvas(); status(); }
function toolDown(ev) {
  const t = st.tool, raw = worldAt(ev), shift = ev.shiftKey;
  if (GEO_TOOLS.includes(t)) { geoDown(ev); return; }
  if (t === 'eraser') { st.drag = {erase: new Set()}; const o = pickAt(ev); if (o) st.drag.erase.add(o.id); setSel([...st.drag.erase]); paintCanvas(); return; }
  if (t === 'fill') {
    const o = pickAt(ev); if (!o || !FILLABLE.includes(o.type)) return;
    const next = clone(st.scene), x = next.objects.find(y => y.id === o.id), want = st.dstyle.fill !== 'none' ? st.dstyle.fill : (o.fill === 'none' ? 'lightgray' : 'none');
    if (x.type === 'region') x.fill = {lightgray: 'gray', gray: 'gray', white: 'none', tint: 'gray'}[want] || (FIELDS.region.fill.list.includes(want) ? want : 'gray');
    else { x.fill = want; if (x.type === 'poly') x.closed = true; }
    if (commit(next)) { setSel([o.id]); paint(); }
    return;
  }
  if (t === 'text') {
    const p = snapPt(raw), id = addShape({type: 'label', x: p.x, y: p.y, text: 'A', size: 16, color: st.dstyle.color});
    ev.preventDefault();
    if (id) { st.lastText = {id, k: 'text'}; setTimeout(() => { const el = document.querySelector('[data-f="text"]'); if (el) { el.focus(); el.select(); } }, 0); }
    return;
  }
  if (t in CLICK_TOOLS) {
    const dr = st.draft && st.draft.tool === t ? st.draft : (st.draft = {tool: t, pts: []});
    const last = dr.pts[dr.pts.length - 1], p = snapPt(raw, {from: last, shift: shift && !!last});
    /* a second press on the same spot ends a polyline or a polygon (the canvas is redrawn between the presses, so the
       browser's own dblclick does not come) */
    const now = performance.now(), quick = dr.lastDown && now - dr.lastDown.t < 400 && Math.hypot(ev.clientX - dr.lastDown.x, ev.clientY - dr.lastDown.y) < 6;
    dr.lastDown = {t: now, x: ev.clientX, y: ev.clientY};
    if (quick && !CLICK_TOOLS[t]) { finishDraft(); return; }
    /* a polygon closes on its first point */
    if (t === 'polygon' && dr.pts.length > 2 && Math.hypot(p.x - dr.pts[0].x, p.y - dr.pts[0].y) < 10 * dview().w / W) { finishDraft(); return; }
    dr.pts.push(p); dr.cur = null;
    if (CLICK_TOOLS[t] && dr.pts.length >= CLICK_TOOLS[t]) { finishDraft(); return; }
    paintCanvas(); status(); return;
  }
  if (DRAG_TOOLS.includes(t)) {
    const a = t === 'pen' ? raw : snapPt(raw);
    st.draft = t === 'pen' ? {tool: t, raw: [a], smooth: $('penSmooth').checked} : {tool: t, a, b: null};
    st.drag = {tool: true, penPointer: ev.pointerType === 'pen' ? ev.pointerId : null};
    $('canvas').setPointerCapture?.(ev.pointerId);
  }
}
function toolMove(ev) {
  const dr = st.draft; if (!dr) return;
  const raw = worldAt(ev);
  if (dr.tool === 'pen') {
    const events = ev.getCoalescedEvents?.();
    const threshold = 0.8 * dview().w / W;
    for (const point of events?.length ? events.map(event => worldAt(event)) : [raw]) {
      const q = dr.raw.at(-1);
      if (Math.hypot(point.x - q.x, point.y - q.y) > threshold) dr.raw.push(point);
    }
    if (dr.raw.length > 1600) dr.raw = dr.raw.filter((_, i, all) => i % 2 === 0 || i === all.length - 1);
  }
  else if (dr.a) { dr.shift = ev.shiftKey; dr.b = ['rect', 'rrect', 'ellipse'].includes(dr.tool) ? snapPt(raw) : snapPt(raw, {from: dr.a, shift: ev.shiftKey}); }
  else if (dr.pts) { const last = dr.pts[dr.pts.length - 1]; dr.cur = snapPt(raw, {from: last, shift: ev.shiftKey && !!last}); }
  paintCanvas();
}
/* a mount's pulleys and the bodies hanging from them go along when it is dragged (and a pulley's hanging bodies) */
function followersOf(o) {
  if (!o || isBody(o)) return [];
  const pulleys = o.type === 'pulley' ? [] : st.scene.objects.filter(p => p.type === 'pulley' && p.mount === o.id), out = [...pulleys];
  for (const p of o.type === 'pulley' ? [o, ...pulleys] : pulleys) for (const sg of st.scene.objects) if (sg.type === 'string' && sg.over.length)
    for (const [bid, pid] of [[sg.a, sg.over[0]], [sg.b, sg.over[sg.over.length - 1]]]) { const b = byId(bid); if (pid === p.id && isBody(b) && !b.on && !out.includes(b)) out.push(b); }
  return out.map(clone);
}

function bindCanvas() {
  const box = $('canvas'), pts = new Map();
  box.addEventListener('pointerdown', ev => {
    if (st.drag?.penPointer != null && ev.pointerId !== st.drag.penPointer) return;
    pts.set(ev.pointerId, {x: ev.clientX, y: ev.clientY});
    if (pts.size === 2) { const [a, b] = [...pts.values()]; st.drag = {pinch: true, d0: Math.hypot(a.x - b.x, a.y - b.y), v0: {...dview()}, mid: worldAt({clientX: (a.x + b.x) / 2, clientY: (a.y + b.y) / 2})}; st.marquee = null; return; }
    if (ev.button === 1 || (ev.button === 0 && st.space)) { st.drag = {pan: true, last: {x: ev.clientX, y: ev.clientY}}; box.setPointerCapture?.(ev.pointerId); ev.preventDefault(); return; }
    if (ev.button !== 0) return;
    box.focus({preventScroll: true});
    const before = JSON.stringify(st.scene);
    const hd = ev.target.closest?.('[data-handle]'), hs = hd && byId(st.sel);
    if (hs && !st.connect && !hs.lock) { if (st.sim) stopSim(); st.drag = {id: hs.id, handle: hd.dataset.handle, start: worldAt(ev), orig: clone(hs), before, moved: false}; box.setPointerCapture?.(ev.pointerId); return; }
    const rh = ev.target.closest?.('[data-rot]'), rs = rh && byId(st.sel);
    if (rs && !st.connect) { if (st.sim) stopSim(); const c = isBody(rs) ? bodyPose(st.scene, rs) : rotCentre(rs); st.drag = {id: rs.id, rot: true, c, before, moved: false}; box.setPointerCapture?.(ev.pointerId); return; }
    if (st.tool !== 'select' && !st.connect) { if (st.sim) { stopSim(); paint(); } toolDown(ev); return; }
    const o = pickAt(ev);
    if (st.connect) { connectClick(o, worldAt(ev)); return; }
    if (st.sim) { stopSim(); paint(); }
    const add = ev.shiftKey || ev.ctrlKey || ev.metaKey;
    if (!o) {
      /* a box drawn on empty space selects what it touches */
      if (!add) setSel([]);
      paintObjectPicker();
      st.drag = {marquee: true, start: worldAt(ev), keep: new Set(selIds()), moved: false}; box.setPointerCapture?.(ev.pointerId); paintCanvas(); paintSide(); status(); return;
    }
    if (add || $('selectMore').checked) {
      toggleSelection(o.id); paint(); return;
    }
    if (!st.selection.has(o.id)) setSel([o.id]); else st.sel = o.id;
    paintObjectPicker(); paintCanvas(); paintSide(); status(); paintBar();
    const ids = [...new Set(selIds().filter(id => !NO_DRAG.includes(byId(id).type) && !byId(id).lock).flatMap(id => geoDragIds(byId(id))))].filter(id => byId(id) && !byId(id).lock);
    if (!ids.length || (byId(o.id).lock && ids.length <= 1)) return;
    if (ids.length > 1 || ids[0] !== o.id) { st.drag = {group: ids, origs: new Map(ids.map(id => [id, clone(byId(id))])), start: worldAt(ev), before, moved: false}; box.setPointerCapture?.(ev.pointerId); return; }
    st.drag = {id: o.id, start: worldAt(ev), orig: clone(o), follow: followersOf(o), before, moved: false};
    box.setPointerCapture?.(ev.pointerId);
  });
  box.addEventListener('pointermove', ev => {
    if (st.drag?.penPointer != null && ev.pointerId !== st.drag.penPointer) return;
    if (pts.has(ev.pointerId)) pts.set(ev.pointerId, {x: ev.clientX, y: ev.clientY});
    if (!st.drag && st.draft && st.draft.pts) { toolMove(ev); return; }
    const d = st.drag; if (!d) return;
    if (d.tool) { toolMove(ev); return; }
    if (d.erase) { const o = pickAt(ev) || (() => { const el = document.elementFromPoint(ev.clientX, ev.clientY); const g = el?.closest?.('[data-id]'); return g ? byId(g.dataset.id) : null; })(); if (o && !d.erase.has(o.id)) { d.erase.add(o.id); setSel([...d.erase]); paintCanvas(); } return; }
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
    d.shift = ev.shiftKey;
    const dx = p.x - d.start.x, dy = p.y - d.start.y;
    if (!d.moved && Math.hypot(dx, dy) * W / dview().w < 3) return;
    d.moved = true;
    if (d.group) { const sx = st.snap ? snapV(dx) : dx, sy = st.snap ? snapV(dy) : dy; for (const id of d.group) { const o = byId(id); if (o) moveObj(o, sx, sy, d.origs.get(id), d.origs.has(o.on)); } }
    else dragTo(d, p, dx, dy);
    paintCanvas();
  });
  const end = ev => {
    if (st.drag?.penPointer != null && ev.pointerId !== st.drag.penPointer) return;
    pts.delete(ev.pointerId);
    const d = st.drag; st.drag = null; if (!d) return;
    if (d.tool) {
      if (ev.type === 'pointercancel' && st.draft?.tool === 'pen') { st.draft = null; paintCanvas(); status(); }
      else if (st.draft && DRAG_TOOLS.includes(st.draft.tool)) finishDraft();
      return;
    }
    if (d.erase) { if (d.erase.size) { const next = clone(st.scene); removeIds(next, [...d.erase]); setSel([]); commit(next); } return; }
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
    /* an end of a wire, an element, a line…, a vertex, a control point, a corner: onto a point of the figure near it or
       the grid; with Shift a segment's end turns in 15° steps about the other end */
    const h = String(d.handle);
    if (h === '1' || h === '2') {
      const other = o.type === 'vector' ? vectorPoints(st.scene, o)[h === '1' ? 1 : 0] : o.type === 'callout' ? (h === '1' ? {x: o.x2, y: o.y2} : {x: o.x, y: o.y}) : {x: o['x' + (h === '1' ? 2 : 1)], y: o['y' + (h === '1' ? 2 : 1)]};
      let q = snapPt(p, {from: other, shift: !!d.shift, exclude: o.id});
      if (o.type === 'vector') q = vectorTransform(st.scene, o).toLocal(q);
      if (o.type === 'callout') { if (h === '1') { o.x = q.x; o.y = q.y; } else { o.x2 = q.x; o.y2 = q.y; } return; }
      o['x' + h] = q.x; o['y' + h] = q.y; return;
    }
    if (h[0] === 'p' && o.type === 'poly') { const i = +h.slice(1), prev = o.pts[i - 1] || o.pts[i + 1], q = snapPt(p, {from: prev && {x: prev[0], y: prev[1]}, shift: !!d.shift && !!prev, exclude: o.id}); o.pts[i] = [q.x, q.y]; return; }
    if (h === 'c1' || h === 'c2') { const k = h[1], q = snapPt(p, {from: {x: o['x' + k], y: o['y' + k]}, shift: !!d.shift, exclude: o.id}); o['cx' + k] = q.x; o['cy' + k] = q.y; return; }
    if (h === 'wh') { const q = snapPt(p, {exclude: o.id}), m = Math.max(0.05, st.scene.grid * 0.5); o.w = r4(Math.max(m, q.x - o.x)); o.h = r4(Math.max(m, q.y - o.y)); if (d.shift && (o.type === 'rect' || o.type === 'ellipse')) o.w = o.h = Math.max(o.w, o.h); return; }
    if (h === 'r') { const q = snapPt(p, {exclude: o.id}); o.r = r4(Math.max(0.02, Math.hypot(q.x - o.x, q.y - o.y))); o.to = deg(o, q); return; }
    return;
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
  if (o.type === 'vector' && o.on) { moveObj(o, snapV(dx), snapV(dy), g); return; }
  if ('x1' in g && !('x' in g)) { o.x1 = r4(snapV(g.x1 + dx)); o.y1 = r4(snapV(g.y1 + dy)); const ex = o.x1 - g.x1, ey = o.y1 - g.y1; o.x2 = r4(g.x2 + ex); o.y2 = r4(g.y2 + ey); if ('cx1' in g) { o.cx1 = r4(g.cx1 + ex); o.cy1 = r4(g.cy1 + ey); o.cx2 = r4(g.cx2 + ex); o.cy2 = r4(g.cy2 + ey); } return; }
  if (g.pts) { const ex = r4(snapV(g.pts[0][0] + dx)) - g.pts[0][0], ey = r4(snapV(g.pts[0][1] + dy)) - g.pts[0][1]; o.pts = g.pts.map(q => [r4(q[0] + ex), r4(q[1] + ey)]); return; }
  if ('x' in g) {
    o.x = r4(snapV(g.x + dx)); o.y = r4(snapV(g.y + dy)); if (o.type === 'callout') { o.x2 = r4(g.x2 + (o.x - g.x)); o.y2 = r4(g.y2 + (o.y - g.y)); }
    for (const fw of d.follow || []) { const x = byId(fw.id); if (x) { x.x = r4(fw.x + o.x - g.x); x.y = r4(fw.y + o.y - g.y); } }
  }
}
function placeOnFrame(o, fr) { const h = isRound(o) ? o.r : o.h / 2, c = vec.add(vec.add(fr.p0, vec.mul(fr.u, o.at)), vec.mul(fr.n, h)); o.x = r4(c.x); o.y = r4(c.y); }

/* ── the simulation ── */
function stopSim() { stopPlayback(); st.sim = null; st.trails = new Map(); st.samples = []; }
function ensureSim() {
  if (st.sim) return st.sim;
  st.sim = buildSim(st.scene); st.trails = new Map(); st.samples = []; sample();
  return st.sim;
}
function simForPlayback() {
  st.msg = ''; clearTimeout(flashTimer);
  const sim = ensureSim();
  if (sim.systems.length) return sim;
  stopSim();
  flash(`<span class="bad">${T.nothing}</span>${sim.unsupported.length ? ' ' + esc(unsupportedText(sim)) : ''}`);
  return null;
}
function stopPlayback() {
  cancelAnimationFrame(st.animationFrame);
  st.animationFrame = 0;
  st.playing = false;
}
function play() {
  const sim = simForPlayback();
  if (!sim) return;
  if (sim.done) { stopSim(); ensureSim(); }
  st.playing = true;
  st.last = performance.now();
  st.animationFrame = requestAnimationFrame(frame);
  paintSimBar();
}
function pause() { stopPlayback(); paintSimBar(); }
function advanceSimulation(dt) {
  st.sim.run(dt);
  sample();
  if (st.sim.done) stopPlayback();
  paintCanvas(); paintReadouts(); paintSimBar(); status();
}
function stepSimulation() {
  const sim = simForPlayback();
  if (sim && !sim.done) advanceSimulation(0.05);
}
function frame(now) {
  if (!st.playing || !st.sim) return;
  const dt = Math.min(0.05, (now - st.last) / 1000) * st.speed;
  st.last = now;
  advanceSimulation(dt);
  if (st.playing) st.animationFrame = requestAnimationFrame(frame);
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
  if (o.type === 'vector' && k === 'vectorFrame') return !!o.on;
  if (o.type === 'curve') {
    const K = o.kind;
    if (k === 'expr2') return K === 'param';
    if (k === 'rel') return K === 'ineq';
    if (['tangent', 'area', 'roots', 'extrema'].includes(k)) return K === 'func';
    if (k === 'tx') return K === 'func' && o.tangent;
    if (k === 'a1' || k === 'a2') return K === 'func' && o.area;
    if (k === 'color') return ['func', 'param', 'polar', 'ineq', 'points'].includes(K);
    if (K === 'ineq' && ['x1', 'x2', 'heads', 'shade', 'pattern', 'y1', 'y2', 'gamma', 'data'].includes(k)) return false;
    if ((K === 'param' || K === 'polar') && ['shade', 'y1', 'y2', 'gamma', 'data'].includes(k)) return false;
    if (k === 'expr' && (K === 'param' || K === 'polar' || K === 'ineq')) return true;
  }
  if (o.type === 'gpoint') { if (k === 'x' || k === 'y') return o.kind === 'free' || o.kind === 'on'; if (k === 'a') return o.kind !== 'free'; if (k === 'b') return o.kind === 'mid' || o.kind === 'inter'; if (k === 'n') return o.kind === 'inter'; }
  if (o.type === 'gline') { if (k === 'b') return o.kind !== 'perp' && o.kind !== 'par'; if (k === 'base') return o.kind === 'perp' || o.kind === 'par'; }
  if (o.type === 'gcircle' && k === 'r') return !o.p;
  if (o.type === 'joint' && ['k', 'damp', 'coils'].includes(k)) return o.kind === 'spring';
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
  if (o.type === 'particle' && (k === 'angle' || k === 'len')) return o.arrow || o.kind === 'photon';
  if (isBody(o) && k === 'vLabel') return o.showV;
  if (o.type === 'poly') { if (k === 'fill') return o.closed; if (k === 'heads') return !o.closed; if (k === 'pts') return false; }
  if (o.type === 'qpot' && k === 'Emax') return true;
  return true;
}
const LETTER_OPTIONS = ko
  ? {letterStyle: '글자 스타일', letterFamily: '글꼴', auto: '그림 기본값', regular: '바르게', italic: '기울임 (이탤릭)', bold: '굵게', boldItalic: '굵은 기울임', serif: '명조 계열', sans: '고딕 계열', mono: '고정폭'}
  : {letterStyle: 'Text style', letterFamily: 'Font family', auto: 'Figure default', regular: 'Upright', italic: 'Italic', bold: 'Bold', boldItalic: 'Bold italic', serif: 'Serif', sans: 'Sans serif', mono: 'Monospace'};
const QNAME = {psi: 'psiQ', levels: 'levelsQ', E: 'EQ', mass: 'mass'};
const fieldName = (o, k) => k === 'mass' && !['qpot', 'well'].includes(o.type) ? (o.type === 'charge' ? (ko ? '질량 (mg)' : 'Mass (mg)') : (ko ? '질량 (kg)' : 'Mass (kg)')) : GEO_TYPES.includes(o.type) && X5.geoFields[k] ? X5.geoFields[k] : o.type === 'joint' && (k === 'a' || k === 'b') ? X5.geoFields[k] : o.type === 'curve' && ['param', 'polar'].includes(o.kind) && (k === 'x1' || k === 'x2') ? (k === 'x1' ? (ko ? 't 처음' : 't from') : (ko ? 't 끝' : 't to'))
  : o.type === 'curve' && k === 'expr' && o.kind !== 'func' && ['param', 'polar', 'ineq'].includes(o.kind) ? ({param: 'x(t)', polar: ko ? 'r(t) (t = θ, 라디안)' : 'r(t) (t = θ, radians)', ineq: 'f(x)'})[o.kind] : o.type === 'particle' && k === 'arrow' ? X4.fields.speedArrow : o.type === 'qpot' && QNAME[k] ? X4.fields[QNAME[k]] : o.type === 'block' && k === 'mu' ? (ko ? '마찰 계수 μ (윗면)' : 'Friction μ (top face)') : o.type === 'element' && k === 'value' ? `${T.fields.value} (${X2.units[o.kind]})` : o.type === 'element' && k === 'r' ? (ko ? '내부 저항 (Ω)' : 'Internal resistance (Ω)') : o.type === 'element' && k === 'kind' ? T.fields.kind : T.fields[k] || k;
/* the leads that touch a bridge wire at its jockey move with it */
const jockey = b => ({x: b.x1 + (b.x2 - b.x1) * b.at, y: b.y1 + (b.y2 - b.y1) * b.at});
function followJockey(scene, J0, J1) { for (const e of scene.objects) if (e.type === 'element') for (const k of [1, 2]) if (Math.hypot(e['x' + k] - J0.x, e['y' + k] - J0.y) < 1e-6) { e['x' + k] = r4(J1.x); e['y' + k] = r4(J1.y); } }
/* which simulation and solver controls make sense for this figure */
const hasMech = () => st.scene.objects.some(o => isBody(o) || o.type === 'force' || o.type === 'spring' || (isPhysShape(o) && o.phys === 'dynamic'));
const hasPhys = () => st.scene.objects.some(isPhysShape);
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
      <label class="chk wide"><input type="checkbox" id="prefExample"${pr.example !== false ? ' checked' : ''}>${X3.tools.example}</label>
      ${hasPhys() ? `<div class="wide note">⚙ ${esc(X5.physScene)}</div><label class="chk"><input type="checkbox" data-scene="gravityOn"${st.scene.gravityOn !== false ? ' checked' : ''}>${esc(X5.gravityOn)}</label><label>${esc(X5.drag)}<input data-scene="drag" type="number" min="0" max="50" step="0.05" value="${st.scene.drag || 0}"></label>` : ''}</div>
      <details class="stylesrc"><summary>${X3.tools.styleSrc}</summary><p class="note">${esc(t.source)}${t.n ? ` · n = ${t.n}` : ''} · ${ko ? '그림 폭' : 'figure width'} ${t.widthPt} pt · ${ko ? '글자' : 'labels'} ${t.labelPt} pt · ${ko ? '선' : 'lines'} ${t.thin}/${t.main}/${t.thick} pt${t.gray != null ? ` · ${ko ? '회색' : 'gray'} ${t.gray}` : ''}${t.est.length ? ` · ${ko ? '추정' : 'estimated'}: ${t.est.join(', ')}` : ''}${!t.n ? ` · ${ko ? '실측 자료 없음 (가정)' : 'no measured source (assumed)'}` : ''}</p></details>
      <p class="note">${T.noSel}</p><div class="note">${T.objects}</div><div class="olist">${st.scene.objects.map(x => `<button type="button" data-pick="${esc(x.id)}">${esc(x.id)} · ${esc(x.type === 'element' ? X2.kinds[x.kind] : T.types[x.type])}</button>`).join('')}</div>`;
    box.querySelectorAll('[data-scene]').forEach(el => el.onchange = () => {
      const next = clone(st.scene), k = el.dataset.scene;
      if (k === 'gravityOn') { if (el.checked) delete next.gravityOn; else next.gravityOn = false; }
      else if (k === 'drag') { const v = parseFloat(el.value); if (v > 0) next.drag = Math.min(50, v); else delete next.drag; }
      else if (k === 'values') next.values = el.checked; else if (k === 'printW') { const v = parseFloat(el.value); if (v > 0) next.printW = Math.max(20, Math.min(400, v)); else delete next.printW; }
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
    const lettering = k === 'letterStyle' || k === 'letterFamily';
    const L = lettering ? LETTER_OPTIONS[k] : o.type === 'vector' && k === 'on' ? (ko ? '따라갈 물체' : 'Follow body')
      : k === 'vectorFrame' ? (ko ? '벡터 방향' : 'Vector direction') : fieldName(o, k);
    if (f.k === 'num') { const sr = slideRange(o, k, f); return `<label class="${sr ? 'wide slide' : ''}">${L}<span class="numrow"><input data-f="${k}" type="number" step="${NUM_STEP[k] || 0.05}" min="${f.min}" max="${f.max}" value="${r4(o[k])}">${sr ? `<input data-s="${k}" type="range" min="${sr[0]}" max="${sr[1]}" step="${(sr[1] - sr[0]) / 200}" value="${Math.max(sr[0], Math.min(sr[1], o[k]))}" aria-label="${esc(L)}">` : ''}</span></label>`; }
    if (f.k === 'bool') return `<label class="chk wide"><input data-f="${k}" type="checkbox"${o[k] ? ' checked' : ''}>${L}</label>`;
    if (f.k === 'enum') return `<label>${L}<select data-f="${k}"${lettering ? ` aria-label="${esc(L)}"` : ''}>${f.list.map(v => `<option value="${v}"${v === o[k] ? ' selected' : ''}>${esc(o.type === 'element' && k === 'kind' ? X2.kinds[v] : o.type === 'block' && v === 'box' ? (ko ? '상자' : 'Box') : (k === 'vectorFrame' ? (v === 'body' ? (ko ? '물체와 함께 회전' : 'Rotate with body') : (ko ? '공간 기준 방향 유지' : 'Keep world direction')) : lettering ? LETTER_OPTIONS[v] : T.enums[v]) || v)}</option>`).join('')}</select></label>`;
    if (f.k === 'ref') return `<label>${L}<select data-f="${k}">${opts(f.types, o[k], optional(k))}</select></label>`;
    if (f.k === 'refs' && o.type === 'gpoly') return `<div class="wide note">${esc(L)}: ${esc(o.pts.join(', '))}</div>`;
    if (f.k === 'refs') { const ps = st.scene.objects.filter(x => x.type === 'pulley'); return ps.length ? `<div class="wide"><span class="note">${L}</span><div class="over">${ps.map(p => `<label><input type="checkbox" data-over="${esc(p.id)}"${o.over.includes(p.id) ? ' checked' : ''}>${esc(p.id)}</label>`).join('')}</div></div>` : ''; }
    if (f.k === 'pts') return '';
    if (f.k === 'params') { const list = parseParams(o[k]) || []; return `<label class="wide">${L}<input data-f="${k}" maxlength="${f.max}" value="${esc(o[k])}" spellcheck="false" autocomplete="off"></label>${list.map((q, i) => `<label class="wide slide">${esc(q.name)}<span class="numrow"><input data-pv="${i}" type="number" step="any" value="${+q.value.toPrecision(6)}"><input data-ps="${i}" type="range" min="${q.min}" max="${q.max}" step="${(q.max - q.min) / 200}" value="${q.value}" aria-label="${esc(q.name)}"></span></label>`).join('')}`; }
    if (f.k === 'expr' || k === 'data' || k === 'xt' || k === 'yt' || k === 'weights' || k === 'layers') return `<label class="wide">${L}<input data-f="${k}" maxlength="${f.max}" value="${esc(o[k])}" spellcheck="false" autocomplete="off"></label>`;
    return `<label class="wide">${L}<span class="tin"><input data-f="${k}" data-text="1" maxlength="${f.max}" value="${esc(o[k])}" spellcheck="false" autocomplete="off"><button type="button" class="symbtn" data-sym="${k}" title="${esc(X2.symTitle)}">Ω</button></span><span class="tex" data-tex="${k}"></span></label>`;
  };
  /* the object's own values first, its physics (a drawn shape), its look (line weight, label size, lock) last; its
     style (그림체) on top */
  const PK = Object.keys(PHYS_FIELDS), physRel = k => k === 'phys' || (o.phys === 'dynamic') || (o.phys === 'static' && (k === 'pmu' || k === 'pe'));
  const lettering = fields.filter(([k]) => k === 'letterStyle' || k === 'letterFamily');
  const main = fields.filter(([k]) => !['letterStyle', 'letterFamily', 'lw', 'ls', 'lock', 'style', ...PK].includes(k)), look = fields.filter(([k]) => ['lw', 'ls', 'lock'].includes(k)), phys = fields.filter(([k]) => PK.includes(k) && physRel(k));
  const physBox = PHYS_SHAPES.includes(o.type) ? `<details class="physp"${o.phys !== 'none' ? ' open' : ''}><summary>⚙ ${esc(X5.physTitle)}${o.phys !== 'none' ? ' · ' + esc(T.enums[o.phys]) : ''}</summary><p class="note">${esc(X5.physHint)}</p><div class="props">${phys.map(field).join('')}</div>
    ${o.phys !== 'none' ? `<div class="row tight">${['spring', 'string', 'rod'].map(k2 => `<button type="button" data-join="${k2}">${esc(X5['join' + k2[0].toUpperCase() + k2.slice(1)])}</button>`).join('')}</div>` : ''}</details>` : '';
  box.innerHTML = `<h2>${esc(o.type === 'element' ? X2.kinds[o.kind] : T.types[o.type])} <span class="note">${esc(o.id)}</span></h2>${styleSelect(o.style || '')}<div class="props">${lettering.concat(main).map(field).join('')}</div>${physBox}
    ${fields.some(([, f]) => f.k === 'txt') ? `<p class="note">${esc(T.texHint)}</p>` : ''}
    <details class="look"><summary>${ko ? '선 · 글자 · 잠금' : 'Lines, labels, lock'}</summary><div class="props">${look.map(field).join('')}</div></details>
    <div class="row">${['string', 'rod', 'spring', 'force'].includes(o.type) ? '' : `<button type="button" data-act="dup">${T.dup}</button>`}<button type="button" data-act="front">${X3.tools.front}</button><button type="button" data-act="back">${X3.tools.backZ}</button><button type="button" data-act="del">${T.del}</button></div>`;
  box.querySelectorAll('[data-f]').forEach(el => {
    const k = el.dataset.f, f = F[k];
    const apply = () => {
      const next = clone(st.scene), x = next.objects.find(y => y.id === o.id);
      if (f.k === 'num') { const v = parseFloat(el.value); if (!Number.isFinite(v)) { paintSide(); return; } const J0 = x.type === 'bridge' ? jockey(x) : null; x[k] = v; if (J0) followJockey(next, J0, jockey(x)); }
      else if (f.k === 'bool') x[k] = el.checked;
      else if (o.type === 'vector' && (k === 'on' || k === 'vectorFrame')) setVectorAttachment(next, x, k === 'on' ? el.value : x.on, k === 'vectorFrame' ? el.value : x.vectorFrame);
      else x[k] = el.value;
      if (o.type === 'element' && k === 'kind' && X2.units[x.kind] && !X2.units[o.kind]) x.value = defaults('element').value;
      /* a curve changing between a function of x and one of t takes a formula in the new variable */
      if (o.type === 'curve' && k === 'kind') { const tv = v => v === 'param' || v === 'polar'; if (tv(x.kind) && !tv(o.kind)) Object.assign(x, x.kind === 'polar' ? {expr: '1 + cos(t)'} : {expr: 'cos(t)', expr2: 'sin(t)'}, {x1: 0, x2: 6.2832}); else if (!tv(x.kind) && tv(o.kind)) x.expr = 'sin(x)'; else if (x.kind === 'polar' && o.kind === 'param') x.expr = '1 + cos(t)'; }
      if (k === 'on' && isBody(x)) {
        if (x.on) { const fr = surfaceFrame(next.objects.find(y => y.id === x.on), next); x.at = r4(Math.max(0, Math.min(fr.length, vec.dot(vec.sub(bodyPose(st.scene, o), fr.p0), fr.u)))); }
        else { const p = bodyPose(st.scene, o); x.x = r4(p.x); x.y = r4(p.y); }
      }
      if (!commit(next, {keepSel: true})) paintSide();
      if (k === 'letterStyle' || k === 'letterFamily') box.querySelector(`[data-f="${k}"]`)?.focus({preventScroll: true});
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
  /* a parameter's slider (a function's or a potential's): the figure follows live, one step of history when let go */
  const setParam = (i, v, live) => {
    const x = byId(o.id), list = x && parseParams(x.params); if (!list || !list[i] || !Number.isFinite(v)) return;
    list[i].value = v; if (v < list[i].min) list[i].min = v; if (v > list[i].max) list[i].max = v;
    if (live) { if (!st.gesture) st.gesture = {before: JSON.stringify(st.scene)}; x.params = paramsText(list); const n = box.querySelector(`[data-pv="${i}"]`); if (n) n.value = +v.toPrecision(6); paintCanvas(); paintReadouts(); }
    else { const next = clone(st.scene); next.objects.find(y => y.id === o.id).params = paramsText(list); commit(next, {keepSel: true}); }
  };
  box.querySelectorAll('[data-ps]').forEach(el => {
    el.oninput = () => setParam(+el.dataset.ps, r4(parseFloat(el.value)), true);
    el.onchange = () => { const g = st.gesture; st.gesture = null; if (!g) return; const r = validateScene(st.scene); if (!r.ok) { st.scene = JSON.parse(g.before); paint(); return; } st.hist.record(g.before); st.scene = r.scene; save(); paint(); };
  });
  box.querySelectorAll('[data-pv]').forEach(el => el.onchange = () => setParam(+el.dataset.pv, parseFloat(el.value), false));
  box.querySelectorAll('[data-over]').forEach(el => el.onchange = () => {
    const next = clone(st.scene), x = next.objects.find(y => y.id === o.id), ids2 = [...box.querySelectorAll('[data-over]')].filter(c => c.checked).map(c => c.dataset.over);
    x.over = [...x.over.filter(id => ids2.includes(id)), ...ids2.filter(id => !x.over.includes(id))];
    alignHanging(next, x); commit(next, {keepSel: true});
  });
  box.querySelectorAll('[data-sym]').forEach(b => b.onclick = () => { st.lastText = {id: o.id, k: b.dataset.sym}; openSymbols(); });
  bindStyleSelect(box);
  box.querySelectorAll('[data-join]').forEach(b => b.onclick = () => { st.connect = {type: 'joint', kind: b.dataset.join, a: o.id, over: []}; status(); paintCanvas(); flash(esc(X5.joinHint)); });
  /* a text field: where its caret is (for the symbol picker), and Tab from one placeholder box to the next */
  box.querySelectorAll('[data-text]').forEach(el => bindTextField(el, o.id, el.dataset.f));
  box.querySelector('[data-act="dup"]')?.addEventListener('click', dup);
  box.querySelector('[data-act="front"]').onclick = () => zOrder(true); box.querySelector('[data-act="back"]').onclick = () => zOrder(false);
  box.querySelector('[data-act="del"]').onclick = del;
}
/* several objects: align, distribute, the look of all of them */
function paintMulti(box, ids) {
  const group = groupOf(ids[0]), grouped = group?.length === ids.length && ids.every(id => group.includes(id));
  const tl = X3.tools, b = (act, t) => `<button type="button" data-al="${act}">${t}</button>`;
  box.innerHTML = `<h2>${esc(grouped ? (ko ? `그룹 · ${ids.length}개` : `Group · ${ids.length}`) : tl.multi(ids.length))}</h2>
    <div class="row"><button type="button" data-group>${grouped ? (ko ? '그룹 해제' : 'Ungroup') : (ko ? '그룹으로 묶기' : 'Group objects')}</button><button type="button" data-save-asset>${ko ? '에셋으로 저장' : 'Save as asset'}</button></div>
    <div class="note">${tl.align}</div><div class="row tight">${b('aL', '⇤ ' + tl.aL)}${b('aC', '↔ ' + tl.aC)}${b('aR', tl.aR + ' ⇥')}${b('aT', '⤒ ' + tl.aT)}${b('aM', '↕ ' + tl.aM)}${b('aB', '⤓ ' + tl.aB)}</div>
    <div class="note">${tl.distribute}</div><div class="row tight">${b('dH', '⋯ ' + tl.dH)}${b('dV', '⋮ ' + tl.dV)}</div>
    ${styleSelect(ids.map(id => byId(id).style || '').every((v, i, a) => v === a[0]) ? byId(ids[0]).style || '' : null)}
    <div class="props"><label>${T.fields.lw}<input data-all="lw" type="number" step="0.1" min="0.2" max="5" value="${byId(ids[0]).lw}"></label><label>${T.fields.ls}<input data-all="ls" type="number" step="0.1" min="0.3" max="4" value="${byId(ids[0]).ls}"></label>
      ${ids.some(id => PHYS_SHAPES.includes(byId(id).type)) ? `<label class="wide">⚙ ${esc(X5.physTitle)}<select data-allphys>${FIELDS.rect.phys.list.map(v => `<option value="${v}"${ids.every(id => byId(id).phys === v) ? ' selected' : ''}>${esc(T.enums[v] || X5.physNone)}</option>`).join('')}</select></label>` : ''}</div>
    <div class="row"><button type="button" data-act="dup">${T.dup}</button><button type="button" data-act="lock">${tl.lockAll}</button><button type="button" data-act="unlock">${tl.unlockAll}</button><button type="button" data-act="front">${tl.front}</button><button type="button" data-act="back">${tl.backZ}</button><button type="button" data-act="del">${T.del}</button></div>
    <div class="olist">${ids.map(id => `<button type="button" data-pick="${esc(id)}">${esc(id)}</button>`).join('')}</div>`;
  box.querySelector('[data-group]').onclick = () => groupSelection(grouped);
  box.querySelector('[data-save-asset]').onclick = () => saveGroupAsset(ids);
  box.querySelectorAll('[data-al]').forEach(x => { x.disabled = grouped; x.onclick = () => alignSel(x.dataset.al); });
  bindStyleSelect(box);
  box.querySelector('[data-allphys]')?.addEventListener('change', e => setAll('phys', e.target.value));
  box.querySelectorAll('[data-all]').forEach(x => x.onchange = () => { const v = parseFloat(x.value); if (Number.isFinite(v)) setAll(x.dataset.all, v); });
  box.querySelector('[data-act="dup"]').onclick = dup; box.querySelector('[data-act="del"]').onclick = del;
  box.querySelector('[data-act="lock"]').onclick = () => setAll('lock', true); box.querySelector('[data-act="unlock"]').onclick = () => setAll('lock', false);
  box.querySelector('[data-act="front"]').onclick = () => zOrder(true); box.querySelector('[data-act="back"]').onclick = () => zOrder(false);
  box.querySelectorAll('[data-pick]').forEach(x => x.onclick = () => { setSel([x.dataset.pick], null, {expand:false}); paint(); });
}
/* the label as the figure will show it (the same typesetter as the SVG, in the figure's style) */
function texPreview(k, v) {
  const el = document.querySelector(`[data-tex="${k}"]`); if (!el) return;
  const object = byId(st.sel);
  el.innerHTML = v ? texSVG(v, 17, object?.style || st.scene.style, object) : '';
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
  if (st.draft?.geo) { const steps = X5.geoStep[st.draft.tool]; el.innerHTML = `<b>${esc(X5.geoTools[st.draft.tool].split(':')[0])}</b>${steps ? ' · ' + esc(steps[Math.min(steps.length - 1, st.draft.picks.length)]) : ''}${st.draft.picks.length ? ' (' + esc(st.draft.picks.join(', ')) + ')' : ''} · Esc`; return; }
  if (GEO_TOOLS.includes(st.tool)) { el.innerHTML = `<b>${esc(X5.geoTools[st.tool])}</b>`; return; }
  if (st.draft && X4.draftHint[st.draft.tool]) { el.innerHTML = `<b>${esc(X4.tools[st.draft.tool].split(':')[0])}</b> · ${esc(X4.draftHint[st.draft.tool])}`; return; }
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
  $('stepBtn').disabled = st.playing || !!st.sim?.done;
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
    ...simDrawOpts(!!st.sim)});
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
/* Projects use the member's existing “그림” folder and Workshop quota. */
const FIG_FOLDER = '그림', STORE_IDS_KEY = 'hlDrawStoreIds';
const X6 = ko ? {save: '💾 저장', saveT: '보관함 ‘그림’ 폴더에 저장 (다시 누르면 같은 파일에 덮어씀)', open: '📂 보관함에서 열기', saved: n => `보관함 ‘그림/${n}’에 저장했습니다.`, overwritten: n => `보관함 ‘그림/${n}’을(를) 새 내용으로 바꿨습니다.`,
  changed: '보관함의 파일이 다른 곳에서 바뀌어 새 파일로 저장했습니다.', localOnly: '로그인하지 않아 이 브라우저에 저장했습니다.', list: '보관함 ‘그림’ 폴더의 그림', none: '보관함 ‘그림’ 폴더에 저장한 그림이 없습니다.', opened: n => `보관함에서 ‘${n}’을(를) 열었습니다.`,
  ai: '✨ AI로 그리기', aiHint: '그릴 그림을 말로 적으세요. 예: 30° 빗면 위 2 kg 블록, 마찰계수 0.2, 도르래로 1 kg 추와 연결', aiEdit: '현재 그림 고치기', aiGo: '그리기', aiLeft: n => `오늘 ${n}번 더 쓸 수 있습니다.`,
  aiErr: {login_required: '로그인하면 쓸 수 있습니다.', quota: '오늘 쓸 수 있는 횟수를 다 썼습니다.', not_configured: 'AI가 아직 준비되지 않았습니다.', bad_prompt: '설명을 조금 더 구체적으로 적어 주세요.', ai_failed: 'AI가 그림을 만들지 못했습니다. 다시 시도해 주세요.', empty: 'AI가 돌려준 그림에 쓸 수 있는 것이 없었습니다.'}}
  : {save: '💾 Save', saveT: 'Save to the “그림” folder of your storage (saving again overwrites the same file)', open: '📂 Open from storage', saved: n => `Saved to storage: 그림/${n}.`, overwritten: n => `Updated 그림/${n} in your storage.`,
  changed: 'The stored file was changed elsewhere, so this was saved as a new file.', localOnly: 'Not logged in: saved in this browser.', list: 'Figures in the “그림” folder', none: 'No figures in the “그림” folder yet.', opened: n => `Opened ‘${n}’ from storage.`,
  ai: '✨ Draw with AI', aiHint: 'Describe the figure. E.g. a 2 kg block on a 30° incline, μ = 0.2, tied over a pulley to a 1 kg mass', aiEdit: 'Change the current figure', aiGo: 'Draw', aiLeft: n => `${n} left today.`,
  aiErr: {login_required: 'Log in to use it.', quota: 'You have used today’s quota.', not_configured: 'The AI is not set up yet.', bad_prompt: 'Describe the figure a little more.', ai_failed: 'The AI could not make the figure. Try again.', empty: 'Nothing usable came back.'}};
st.storeIds = (() => { try { const v = JSON.parse(store.get(STORE_IDS_KEY) || 'null'); return v && (typeof v.json === 'string' || (v.provider === 'drive' && typeof v.id === 'string') || (v.provider === 'github' && typeof v.path === 'string')) ? v : null; } catch (e) { return null; } })();
const keepStoreIds = ids => { st.storeIds = ids; if (ids) store.set(STORE_IDS_KEY, JSON.stringify(ids)); else store.del(STORE_IDS_KEY); };
function projectFileName(title) { return (title.replace(/[\\/:*?"<>|]+/g, ' ').trim().slice(0, 60) || 'project') + '.json'; }
function projectUpload(json, name, extra = {}) {
  const form = new FormData();
  form.append('file', new File([json], name, {type: 'application/json'}));
  form.append('kind', 'figure');
  for (const [k, v] of Object.entries(extra)) form.append(k, v);
  return form;
}
async function toStorage() {
  if (st.storageBusy) return;
  if (!token()) {
    if (saveLocal()) $('saveStatus').innerHTML = `${esc(X6.localOnly)} <a href="/#/login" target="_top">${T.login}</a>`;
    return;
  }
  const provider = $('drawProvider').querySelector('select').value;
  const data = JSON.stringify(projectData()), signature = projectSignature(), msg = $('saveStatus');
  const current = st.project, fileName = projectFileName(projectTitle());
  const rename = !!current.title;
  const create = () => api('/api/workshop/storage/files', 'POST', projectUpload(data, fileName, {folder: FIG_FOLDER, ensure_folder: '1'}), true);
  st.storageBusy = true;
  $('bSave').disabled = true;
  msg.textContent = ko ? '저장 중…' : 'Saving…';
  try {
    const ids = st.storeIds;
    if (provider !== 'store') {
      const entry = await drawStorage.saveExternal(provider,'figure',projectTitle(),JSON.parse(data),ids);
      if (st.project === current) {
        keepStoreIds(entry);
        st.savedSignature = signature;
        st.projectChanged = signature !== projectSignature();
        save({changed:false});
        msg.textContent = st.projectChanged ? (ko ? '이전 상태 저장됨 · 새 수정 있음' : 'Earlier revision saved · newer edits pending') : (ko ? '저장했습니다.' : 'Saved.');
      }
      return;
    }
    const local = ids?.json ? ids : null;
    let response, copied = false;
    try {
      response = local ? await api(`/api/workshop/storage/files/${encodeURIComponent(local.json)}/content`, 'PUT', projectUpload(data, fileName, local.base ? {base: String(local.base)} : {}), true) : await create();
    } catch (e) {
      if (!local || ![404, 409].includes(e.status)) throw e;
      response = await create();
      copied = e.status === 409;
    }
    let file = response.file, renameProblem = false;
    if (ids?.json === file.id && rename && file.name !== fileName) {
      try { file = (await api(`/api/workshop/storage/files/${encodeURIComponent(file.id)}`, 'PATCH', {name: fileName})).file; }
      catch { renameProblem = true; }
    }
    if (st.project === current) {
      keepStoreIds({json: file.id, base: file.updated_at, name: file.name});
      st.savedSignature = signature;
      st.projectChanged = signature !== projectSignature();
      save({changed: false});
      msg.textContent = renameProblem ? (ko ? '내용 저장됨 · 보관함 파일 이름 변경 실패' : 'Content saved · storage file name could not be changed') : copied ? X6.changed : st.projectChanged ? (ko ? '이전 상태 저장됨 · 새 수정 있음' : 'Earlier revision saved · newer edits pending') : X6.saved(file.name);
    }
  } catch (e) {
    msg.textContent = window.HL_WORKSHOP_PROJECTS.error(e);
  } finally {
    st.storageBusy = false;
    $('bSave').disabled = false;
  }
}
/* ── sharing (작품 공유, share-publish.js window.HL_SHARE): publish the figure with a title, a description, how to use it,
   tags and a topic; the share id is kept with the figure in this browser, so the dialog offers to update the shared
   version or take it down. Opened as ?share=N: someone else's figure becomes a new draft published as a remix of N;
   one's own unpublished draft N is published as itself (creation_id). ── */
const SHARE_KEY = 'hlDrawShare';
const X7 = ko ? {share: '🔗 공유하기', title: '작품 공유', name: '제목', desc: '설명', howto: '사용 방법', tags: '태그 (쉼표로)', topic: '주제', publish: '공유하기', update: '공유 내용 업데이트', unpublish: '공유 취소', view: '공유 페이지 보기', cancel: '닫기',
  done: '공유했습니다.', updated: '공유 내용을 바꿨습니다.', removed: '공유를 취소했습니다.', remix: n => `공유된 그림 #${n}을(를) 불러왔습니다. 고쳐서 공유하면 리믹스가 됩니다.`, draft: n => `초안 #${n}을(를) 불러왔습니다.`, login: '로그인하면 공유할 수 있습니다.', unavailable: '공유 기능을 불러오지 못했습니다.',
  topics: {mechanics: '역학', em: '전자기', thermal: '열', optics: '광학', waves: '파동', modern: '현대물리', other: '기타'}}
  : {share: '🔗 Share', title: 'Share this figure', name: 'Title', desc: 'Description', howto: 'How to use it', tags: 'Tags (comma separated)', topic: 'Topic', publish: 'Share', update: 'Update the shared version', unpublish: 'Stop sharing', view: 'Open the share page', cancel: 'Close',
  done: 'Shared.', updated: 'The shared version was updated.', removed: 'No longer shared.', remix: n => `Loaded shared figure #${n}. Share your changes and it becomes a remix.`, draft: n => `Loaded draft #${n}.`, login: 'Log in to share.', unavailable: 'Sharing could not be loaded.',
  topics: {mechanics: 'Mechanics', em: 'E&M', thermal: 'Thermal', optics: 'Optics', waves: 'Waves', modern: 'Modern', other: 'Other'}};
st.share = (() => { try { const v = JSON.parse(store.get(SHARE_KEY) || 'null'); return v && typeof v === 'object' ? v : null; } catch (e) { return null; } })();
const keepShare = v => { st.share = v; if (v) store.set(SHARE_KEY, JSON.stringify(v)); else store.del(SHARE_KEY); };
const topicOf = () => { const d = Object.entries(DOMAINS).map(([k, l]) => [k, st.scene.objects.filter(o => l.includes(o.type)).length]).sort((a, b) => b[1] - a[1])[0]?.[0]; return {mech: 'mechanics', em: 'em', thermo: 'thermal', optics: 'optics', waves: 'waves', modern: 'modern'}[d] || 'other'; };
function openShare() {
  const S = window.HL_SHARE; let box = $('shareBox');
  if (!S) { flash(`<span class="bad">${esc(X7.unavailable)}</span>`); return; }
  if (!token()) { flash(`${esc(X7.login)} <a class="btn" href="/#/login" target="_top">${T.login}</a>`); return; }
  if (!box) { box = document.createElement('div'); box.id = 'shareBox'; box.className = 'sharebox'; box.setAttribute('role', 'dialog'); box.setAttribute('aria-label', X7.title); $('stageTop').after(box); }
  const sh = st.share || {}, m = sh.meta || {};
  box.hidden = false;
  box.innerHTML = `<div class="symhead"><b>${esc(X7.title)}</b><button type="button" data-close aria-label="✕">✕</button></div>
    <div class="props"><label class="wide">${esc(X7.name)}<input id="shTitle" maxlength="80" value="${esc(m.title || st.scene.title || '')}"></label>
    <label class="wide">${esc(X7.desc)}<textarea id="shDesc" rows="3" maxlength="3000">${esc(m.description || '')}</textarea></label>
    <label class="wide">${esc(X7.howto)}<textarea id="shHow" rows="2" maxlength="3000">${esc(m.howto || '')}</textarea></label>
    <label>${esc(X7.tags)}<input id="shTags" maxlength="180" value="${esc((m.tags || []).join(', '))}"></label>
    <label>${esc(X7.topic)}<select id="shTopic">${S.TOPICS.map(t => `<option value="${t}"${t === (m.topic || topicOf()) ? ' selected' : ''}>${esc(X7.topics[t] || t)}</option>`).join('')}</select></label></div>
    <div class="row">${sh.id ? `<button type="button" class="primary" id="shUpd">${esc(X7.update)}</button><button type="button" id="shView">${esc(X7.view)}</button><button type="button" class="danger" id="shDel">${esc(X7.unpublish)}</button>` : `<button type="button" class="primary" id="shPub">${esc(X7.publish)}</button>`}</div>
    <p class="note" id="shMsg" role="status"></p>`;
  const msg = t => { $('shMsg').innerHTML = t; };
  const fields = () => ({title: $('shTitle').value.trim() || st.scene.title || T.title, description: $('shDesc').value, howto: $('shHow').value, tags: $('shTags').value.split(',').map(x => x.trim()).filter(Boolean).slice(0, 8), topic: $('shTopic').value});
  const content = () => { const thumb = S.svgThumb(exportSvg(false)); return {payload: {scene: st.scene}, ...(thumb ? {thumbnail: thumb} : {})}; };
  const fail = e => msg(`<span class="bad">${esc(e?.code === 'login_required' ? X7.login : T.err[e?.code] || e?.code || T.err.other)}</span>`);
  box.querySelector('[data-close]').onclick = () => { box.hidden = true; height(); };
  $('shPub')?.addEventListener('click', async () => {
    msg('…'); const f = fields();
    try {
      const r = await S.publish({type: 'figure', ...f, ...content(), ...(sh.draft ? {creation_id: sh.draft} : sh.remixOf ? {remix_of: sh.remixOf} : {})});
      keepShare({id: r.id, meta: f}); openShare(); $('shMsg').innerHTML = `<span class="ok">${esc(X7.done)}</span>`;
    } catch (e) { fail(e); }
  });
  $('shUpd')?.addEventListener('click', async () => { msg('…'); const f = fields(); try { await S.update(sh.id, {...f, ...content()}); keepShare({...sh, meta: f}); msg(`<span class="ok">${esc(X7.updated)}</span>`); } catch (e) { fail(e); } });
  $('shDel')?.addEventListener('click', async () => { msg('…'); try { await S.unpublish(sh.id); keepShare(null); openShare(); $('shMsg').textContent = X7.removed; } catch (e) { fail(e); } });
  $('shView')?.addEventListener('click', () => S.open(sh.id));
  height();
}
/* #/workshop/draw?share=N: the shared figure N opened in the editor */
async function openShared(n) {
  const S = window.HL_SHARE; if (!S || !(n > 0)) return;
  try {
    const before = JSON.stringify(projectData());
    const r = await S.get(n), p = r?.project, sc = p?.payload?.scene || p?.payload;
    const v = validateScene(sc, {lenient: true}); if (!v.scene.objects.length) return;
    if (!v.scene.view) v.scene.view = sceneBounds(v.scene);
    if (st.storageBusy || before !== JSON.stringify(projectData())) return;
    replaceProject({title: p.title || '', index: 0, pages: [v.scene]});
    const mine = !!p.mine, meta = {title: p.title, description: p.description ?? p.descr ?? '', howto: p.howto || '', tags: p.tags || [], topic: p.topic};
    keepShare(mine ? (p.status === 'public' ? {id: n, meta} : {draft: n, meta}) : {remixOf: n, meta: {...meta, title: p.title}});
    flash(esc(mine ? X7.draft(n) : X7.remix(n)));
  } catch (e) { flash(`<span class="bad">${esc(T.err[e?.code] || T.err.other)}</span>`); }
}
/* the models the server offers for drawing with AI (GET /api/workshop/ai/models), asked for once */
async function aiModels() {
  if (st.aiModels || !token()) return;
  try { const r = await api('/api/workshop/ai/models'); st.aiModels = (r.models || []).filter(m => m && m.id && m.configured !== false); const sel = $('aiModel');
    if (sel && st.aiModels.length > 1) { sel.innerHTML = st.aiModels.map(m => `<option value="${esc(m.id)}"${m.id === r.default ? ' selected' : ''}>${esc(m.model || m.id)}</option>`).join(''); sel.hidden = false; syncAiControls(); }
  } catch (e) { st.aiModels = []; }
}
/* Preview a checked proposal in the existing AI panel before replacing the drawing. */
function showAiProposal(scene, base, edit, recognition = null) {
  const panel = $('aiProposal');
  const caption = ko ? 'AI가 제안한 그림' : 'AI-proposed figure';
  panel.innerHTML = `<img src="${svgDataUrl(renderSVG(scene, {width: 480, view: scene.view}))}" alt="${caption}" width="480" style="max-width:100%;height:auto">
    <div class="row"><button type="button" class="primary" id="aiApply">${ko ? '그림에 적용' : 'Apply to figure'}</button><button type="button" id="aiDiscard">${ko ? '제안 닫기' : 'Discard proposal'}</button></div>`;
  panel.hidden = false;
  const close = () => { panel.replaceChildren(); panel.hidden = true; $('aiGo').focus(); height(); };
  $('aiDiscard').onclick = close;
  $('aiApply').onclick = () => {
    if (JSON.stringify(projectData()) !== base) {
      $('aiMsg').textContent = ko ? '요청 후 그림이 바뀌었습니다. 현재 그림으로 다시 요청해 주세요.' : 'The figure changed after this request. Ask again with the current figure.';
      return;
    }
    setSel([]);
    st.zoom = null;
    st.ai = recognition;
    if (commit(scene)) {
      if (!edit) keepShare(null);
      $('aiMsg').textContent = ko ? '그림에 적용했습니다. 실행 취소로 되돌릴 수 있습니다.' : 'Applied to the figure. You can undo this change.';
      close();
    }
  };
  height();
}
const AI_MESSAGES = ko ? {
  region_failed:'그림 영역을 찾지 못했습니다. 다시 찾거나 사진을 잘라서 올려 주세요.',
  illustration_failed:'삽화를 만들지 못했습니다. 요청이나 참고 그림을 확인하고 다시 시도해 주세요.',
  illustration_busy:'오늘의 삽화 생성 한도에 도달했습니다.',
} : {
  region_failed:'Could not find figure regions. Try again or upload a cropped photo.',
  illustration_failed:'Could not generate the illustration. Check the request or reference and try again.',
  illustration_busy:'The daily illustration generation limit has been reached.',
};
function syncAiControls() {
  const attached = !!$('aiPhoto').files.length, raster = $('aiOutput').value === 'illustration';
  $('aiClearPhoto').hidden = $('aiDetect').hidden = !attached;
  $('aiWhole').hidden = !attached || !!st.aiPhoto || !st.aiRegionFailed;
  for (const id of ['aiOutput','aiStyle','aiPhoto','aiRegion','aiClearPhoto','aiWhole']) $(id).disabled = !!st.aiWork;
  $('aiEditLabel').hidden = $('aiEditCur').disabled = attached || raster;
  $('aiModel').hidden = attached || raster || !(st.aiModels?.length > 1);
  $('aiStyleLabel').hidden = $('aiStyle').hidden = !raster;
  $('aiDetect').disabled = !!st.aiWork;
  $('aiGo').disabled = !!st.aiWork || (attached && !st.aiPhoto);
  $('aiGo').textContent = raster ? (ko ? '삽화 만들기' : 'Generate illustration')
    : attached ? (ko ? '도식 복원' : 'Restore editable figure') : X6.aiGo;
}
function resetAiPhoto() {
  st.aiPhoto = null;
  st.aiRegionFailed = false;
  $('aiScan').hidden = true;
  $('aiSource').removeAttribute('src');
  $('aiMsg').textContent = $('aiPhoto').files.length ? (ko ? '그림 영역 찾기를 눌러 주세요.' : 'Find the figure regions first.') : '';
  syncAiControls();
  height();
}
function paintAiOutline() {
  const box = st.aiPhoto?.regions[Number($('aiRegion').value)]?.box;
  const outline = $('aiBoxOutline');
  outline.hidden = !box;
  if (!box) return;
  const [top,left,bottom,right] = box;
  Object.assign(outline.style,{top:top/10+'%',left:left/10+'%',width:(right-left)/10+'%',height:(bottom-top)/10+'%'});
}
async function detectAiRegions({whole = false} = {}) {
  const file = $('aiPhoto').files[0], msg = $('aiMsg');
  if (!file || st.aiWork) return;
  if (!token()) { msg.textContent = X6.aiErr.login_required; return; }
  st.aiWork = true;
  syncAiControls();
  msg.textContent = whole ? (ko ? '사진을 불러오는 중…' : 'Loading photo…') : (ko ? '그림 영역을 찾는 중…' : 'Finding figure regions…');
  try {
    const source = await photoData(file);
    const r = whole ? {regions:[]} : await api('/api/workshop/figure-regions','POST',{image:source, lang});
    if ($('aiPhoto').files[0] !== file) return;
    st.aiRegionFailed = false;
    const regions = r.regions || [], select = $('aiRegion');
    st.aiPhoto = {source,regions};
    select.replaceChildren();
    regions.forEach((region,i) => select.append(new Option((i+1)+' · '+(region.label || (ko ? '그림' : 'Figure')),String(i))));
    select.append(new Option(ko ? '사진 전체' : 'Whole photo','-1'));
    $('aiSource').src = source;
    $('aiScan').hidden = false;
    paintAiOutline();
    msg.textContent = regions.length ? (ko ? '사용할 그림 영역을 골라 주세요.' : 'Choose a figure region.')
      : (ko ? '자동 감지된 영역이 없습니다. 사진 전체를 쓰거나 잘라서 다시 올릴 수 있습니다.' : 'No regions detected. Use the whole photo or upload a crop.');
  } catch (e) {
    if ($('aiPhoto').files[0] === file) {
      st.aiRegionFailed = true;
      msg.textContent = AI_MESSAGES[e.code] || X6.aiErr[e.code] || errText(e);
    }
  } finally { st.aiWork = false; syncAiControls(); height(); }
}
async function decodeAiImage(src) {
  const image = new Image();
  image.src = src;
  await image.decode();
  return image;
}
async function aiCrop(photo, index) {
  const box = photo.regions[index]?.box;
  if (!box) return photo.source;
  const im = await decodeAiImage(photo.source), canvas = document.createElement('canvas');
  const [top,left,bottom,right] = box;
  const x = Math.floor(left * im.width / 1000), y = Math.floor(top * im.height / 1000);
  canvas.width = Math.max(1, Math.ceil(right * im.width / 1000) - x);
  canvas.height = Math.max(1, Math.ceil(bottom * im.height / 1000) - y);
  canvas.getContext('2d').drawImage(im,x,y,canvas.width,canvas.height,0,0,canvas.width,canvas.height);
  return canvas.toDataURL('image/jpeg',.88);
}
async function illustrationAsset(src, title) {
  const image = await decodeAiImage(src), c = document.createElement('canvas');
  for (const scale of [1,.85,.7,.55,.4]) {
    c.width = Math.max(1,Math.round(image.naturalWidth*scale));
    c.height = Math.max(1,Math.round(image.naturalHeight*scale));
    const g = c.getContext('2d');
    g.fillStyle = '#fff'; g.fillRect(0,0,c.width,c.height);
    g.drawImage(image,0,0,c.width,c.height);
    const compressed = c.toDataURL('image/jpeg',.9);
    if (compressed.length < 280000) return {format:'haslalab-illustration',version:1,title,image:compressed,width:c.width,height:c.height};
  }
  throw new Error(ko ? '삽화 파일이 너무 큽니다.' : 'The illustration is too large.');
}
async function showIllustration(src, prompt, left, style) {
  if (typeof src !== 'string' || !/^data:image\/(png|jpeg|webp);base64,[A-Za-z0-9+/]+={0,2}$/.test(src)) throw {code:'illustration_failed'};
  if (style === 'exam') {
    const image = await decodeAiImage(src), canvas = document.createElement('canvas');
    canvas.width = image.naturalWidth; canvas.height = image.naturalHeight;
    const paper = canvas.getContext('2d');
    paper.fillStyle = '#fff'; paper.fillRect(0,0,canvas.width,canvas.height);
    paper.drawImage(image,0,0);
    const pixels = paper.getImageData(0,0,canvas.width,canvas.height);
    for (let i = 0; i < pixels.data.length; i += 4) {
      const gray = 0.2126*pixels.data[i] + 0.7152*pixels.data[i+1] + 0.0722*pixels.data[i+2];
      pixels.data[i] = pixels.data[i+1] = pixels.data[i+2] = gray;
    }
    paper.putImageData(pixels,0,0);
    src = canvas.toDataURL('image/png');
  }
  const host = $('aiIllustration');
  host.hidden = false;
  host.innerHTML = '<img id="aiRasterPreview" alt=""><label for="aiRasterTitle"></label><input id="aiRasterTitle" maxlength="60"><div class="row" id="aiRasterTools"></div><p class="note" id="aiRasterStatus" role="status"></p>';
  const im = $('aiRasterPreview');
  im.src = src; im.alt = ko ? '생성한 시험지 삽화' : 'Generated worksheet illustration';
  const title = $('aiRasterTitle');
  host.querySelector('label').textContent = ko ? '삽화 이름' : 'Illustration name';
  title.value = prompt.slice(0,60) || (ko ? '문제 삽화' : 'Worksheet illustration');
  const tools = $('aiRasterTools'), status = $('aiRasterStatus');
  const provider = window.HL_WORKSHOP_PROJECTS.providerSelect();
  const button = (text, fn) => { const b=document.createElement('button');b.type='button';b.textContent=text;b.onclick=fn;return b; };
  const fileExt = src.slice(11,src.indexOf(';')), getTitle = () => title.value.trim() || (ko ? '문제 삽화' : 'Worksheet illustration');
  tools.append(provider,button(ko ? '삽화 저장' : 'Save illustration', async (event) => {
    const saveButton = event.currentTarget;
    saveButton.disabled = true;
    try {
      const name = getTitle(), selected = provider.value, asset = await illustrationAsset(src,name);
      if (selected === 'store') {
        await api('/api/workshop/storage/files','POST',projectUpload(JSON.stringify(asset),projectFileName(name),{folder:'삽화',ensure_folder:'1'}),true);
      } else await drawStorage.saveExternal(selected,'illustration',name,asset);
      status.textContent = ko ? '저장했습니다. 시험지 제작에서 그림 불러오기로 선택할 수 있습니다.' : 'Saved. Select it under Import figure in the test-paper maker.';
    } catch (e) { status.textContent = window.HL_WORKSHOP_PROJECTS.error(e); }
    finally { saveButton.disabled = false; height(); }
  }),button(ko ? '삽화 내려받기' : 'Download illustration', () => {
    const content = Uint8Array.from(atob(src.slice(src.indexOf(',')+1)),ch=>ch.charCodeAt(0));
    const ext = fileExt === 'jpeg' ? 'jpg' : fileExt;
    download(new Blob([content],{type:'image/'+fileExt}),projectFileName(getTitle()).replace(/\.json$/,'.'+ext));
  }));
  $('aiMsg').textContent = (ko ? '삽화가 생성되었습니다.' : 'Illustration generated.') + (Number.isFinite(left) ? ' '+X6.aiLeft(left) : '');
  height();
}
async function aiDraw() {
  const box = $('aiMsg'), text = $('aiPrompt').value.trim(), file = $('aiPhoto').files[0];
  const photo = st.aiPhoto, cropIndex = Number($('aiRegion').value), raster = $('aiOutput').value === 'illustration';
  const edit = !raster && !file && $('aiEditCur').checked;
  if (st.aiWork || (file && !photo)) return;
  if (!text && !file) { $('aiPrompt').focus(); return; }
  if (!token()) { box.innerHTML = '<span>'+esc(X6.aiErr.login_required)+'</span> <a class="btn" href="/#/login" target="_top">'+T.login+'</a>'; return; }
  const base = JSON.stringify(projectData()), scene = edit ? clone(st.scene) : null;
  const model = !$('aiModel').hidden ? $('aiModel').value : '', style = $('aiStyle').value;
  $('aiProposal').hidden = true;
  $('aiProposal').replaceChildren();
  $('aiIllustration').hidden = true;
  $('aiIllustration').replaceChildren();
  box.textContent = raster ? (ko ? '삽화를 그리는 중…' : 'Generating illustration…') : '…';
  st.aiWork = true;
  syncAiControls();
  try {
    const image = photo ? await aiCrop(photo,cropIndex) : undefined;
    if (raster) {
      const r = await api('/api/workshop/illustration','POST',{prompt:text,style,lang,...(image ? {image} : {})});
      await showIllustration(r.image,text,r.left,style);
      return;
    }
    const r = image
      ? await api('/api/workshop/scene-from-image', 'POST', {image, prompt:text, lang})
      : await api('/api/workshop/ai/scene', 'POST', {prompt:text,...(scene ? {scene} : {}),lang,...(model ? {model} : {})});
    const v = validateScene(r?.scene,{lenient:true});
    if (!v.scene?.objects.length) throw {code:'empty'};
    if (!v.scene.view) v.scene.view = sceneBounds(v.scene);
    const recognition = image ? {unsure:Array.isArray(r.unsure) ? r.unsure : [],left:r.left} : null;
    showAiProposal(v.scene,base,edit,recognition);
    const notes = (Array.isArray(r.notes) ? r.notes : []).filter(n=>typeof n==='string').slice(0,6);
    box.innerHTML = (notes.length ? '<ul>'+notes.map(n=>'<li>'+esc(n.slice(0,200))+'</li>').join('')+'</ul>' : '') +
      (Number.isFinite(r.left) ? '<span class="note">'+esc(X6.aiLeft(r.left))+'</span>' : '');
  } catch (e) { box.textContent = AI_MESSAGES[e.code] || X6.aiErr[e.code] || errText(e); }
  finally { st.aiWork = false; syncAiControls(); height(); }
}
const saves = () => { try { const l = JSON.parse(store.get(SAVES_KEY) || '[]'); return Array.isArray(l) ? l.filter(x => x && typeof x.name === 'string' && x.scene) : []; } catch (e) { return []; } };
function saveLocal() {
  const name = projectTitle(), list = saves().filter(x => x.name !== name);
  list.unshift({name, t: Date.now(), scene: projectData()});
  const ok = store.set(SAVES_KEY, JSON.stringify(list.slice(0, 20)));
  if (ok) { st.savedSignature = projectSignature(); st.projectChanged = false; save({changed: false}); paintProject(); }
  $('outMsg').innerHTML = ok ? `<span class="ok">${T.localSaved}</span>` : `<span class="bad">${T.err.other}</span>`;
  paintOut(true);
  return ok;
}
function openScene(obj) {
  const project = decodeProject(obj);
  if (!project) { $('outMsg').innerHTML = `<span class="bad">${T.loadBad}</span>`; return; }
  if (canLeaveProject()) replaceProject(project);
}
function paintOut(keepMsg) {
  const box = $('out'); if (!box) return;
  const old = keepMsg ? $('outMsg')?.innerHTML || '' : '';
  const list = saves();
  box.innerHTML = `<h2>${T.out}</h2>
    <div class="row"><button type="button" id="oSvg">${T.svg}</button><button type="button" id="oPng">${T.png}</button></div>
    <div class="row"><button type="button" id="oLocal">${T.local}</button></div>
    <div class="row"><button type="button" id="oJson">${T.json}</button><label class="btn filebtn">${T.load}<input type="file" id="oLoad" accept=".json,application/json"></label></div>
    <p class="note" id="outMsg" role="status">${old}</p>
    ${list.length ? `<div class="note">${T.saves}</div><div class="saves">${list.map((x, i) => `<div><span>${esc(x.name)}</span><button type="button" data-open="${i}">${T.open}</button><button type="button" data-drop="${i}" aria-label="${T.del}">✕</button></div>`).join('')}</div>` : ''}`;
  $('oSvg').onclick = () => download(new Blob([exportSvg()], {type: 'image/svg+xml'}), fileName('svg'));
  $('oPng').onclick = () => pngBlob(exportSvg()).then(b => download(b, fileName('png'))).catch(() => { $('outMsg').innerHTML = `<span class="bad">${T.err.other}</span>`; });
  $('oLocal').onclick = saveLocal;
  $('oJson').onclick = () => download(new Blob([JSON.stringify(projectData(), null, 1)], {type: 'application/json'}), fileName('json'));
  $('oLoad').onchange = async e => { const f = e.target.files[0]; e.target.value = ''; if (!f) return; if (f.size > 5e6) { $('outMsg').textContent = T.loadBad; return; } try { openScene(JSON.parse(await f.text())); } catch (x) { $('outMsg').innerHTML = `<span class="bad">${T.loadBad}</span>`; } };
  box.querySelectorAll('[data-open]').forEach(b => b.onclick = () => openScene(list[+b.dataset.open].scene));
  box.querySelectorAll('[data-drop]').forEach(b => b.onclick = () => { const l = saves(); l.splice(+b.dataset.drop, 1); store.set(SAVES_KEY, JSON.stringify(l)); paintOut(); });
}

// Flatten and downsize the photo before sending it to the existing vision service.
async function photoData(file) {
  if (file.size > 24 * 1024 * 1024) throw {code: 'image_too_large'};
  let bitmap;
  try {
    bitmap = await createImageBitmap(file);
    const scale = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', 0.82);
  } catch { throw {code: 'bad_image'}; }
  finally { bitmap?.close(); }
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
/* the style (그림체) of the selected objects only: '' follows the figure's */
function styleSelect(cur) {
  return `<label class="wide stylepick">${esc(X5.fields.style)}<select data-objstyle>${cur === null ? '<option value="" selected>—</option>' : ''}<option value=""${cur === '' ? ' selected' : ''}>${esc(X5.styleInherit(STYLES[st.scene.style].name[lang]))}</option>${STYLE_KEYS.map(k => `<option value="${k}"${cur === k ? ' selected' : ''}>${esc(STYLES[k].name[lang])}</option>`).join('')}</select></label>`;
}
function bindStyleSelect(box) { box.querySelector('[data-objstyle]')?.addEventListener('change', e => setAll('style', e.target.value)); }
/* a label's text field: the caret is kept (the symbol picker inserts there), and Tab goes to the next placeholder box
   (Shift+Tab to the one before) */
function bindTextField(el, id, k) {
  const keep = () => { st.lastText = {id, k, caret: el.selectionStart, caretEnd: el.selectionEnd}; };
  for (const ev of ['keyup', 'click', 'select', 'focus', 'input']) el.addEventListener(ev, keep);
  el.addEventListener('keydown', e => {
    if (e.key !== 'Tab' || !el.value.includes(PLACEHOLDER)) return;
    const v = el.value, from = e.shiftKey ? el.selectionStart - 1 : el.selectionEnd;
    let i = e.shiftKey ? v.lastIndexOf(PLACEHOLDER, from) : v.indexOf(PLACEHOLDER, from);
    if (i < 0) i = e.shiftKey ? v.lastIndexOf(PLACEHOLDER) : v.indexOf(PLACEHOLDER);
    if (i < 0) return;
    e.preventDefault(); el.setSelectionRange(i, i + 1); keep();
  });
}
/* ── the symbol picker, organised like an equation editor: Greek, accents on a letter you choose, vector and calculus
   operators, relations and signs, physical constants (typeset, their value and unit on hover), structures with
   placeholder boxes (Tab moves between them), chemical formulas; the recently used ones on top and a search by name ── */
const symRecent = () => { try { const l = JSON.parse(store.get(SYM_RECENT) || '[]'); return Array.isArray(l) ? l.filter(x => typeof x === 'string').slice(0, 16) : []; } catch (e) { return []; } };
const constTex = c => st.symValue && c[2] ? `${c[0]} = ${c[2]}${c[3] ? `\\,\\mathrm{${c[3]}}` : ''}` : c[0];
function symItems(tab) {
  if (tab === 'accent') return ACCENTS.map(([t, n]) => [t.replace(/#/g, st.symBase.length > 1 && !st.symBase.startsWith('\\') ? `{${st.symBase}}` : st.symBase), n]);
  if (tab === 'const') return SYMTAB.const.map(c => [constTex(c), c[1], `${c[1].split(' ').filter(w => /[가-힣]/.test(w)).join(' ') || c[1]}: ${c[2].replace(/\\times10\^\{(-?\d+)\}/, ' × 10^$1')} ${c[3].replace(/\\,/g, '·')}`]);
  return SYMTAB[tab] || [];
}
function openSymbols() {
  let pop = $('symPop');
  if (pop && !pop.hidden) { pop.hidden = true; return; }
  if (!pop) { pop = document.createElement('div'); pop.id = 'symPop'; pop.className = 'sympop'; pop.setAttribute('role', 'dialog'); pop.setAttribute('aria-label', X5.sym.title); $('stageTop').after(pop); }
  pop.hidden = false; paintSymbols(); height();
}
function paintSymbols() {
  const pop = $('symPop'); if (!pop) return;
  const S5 = X5.sym, q = (st.symQ || '').trim().toLowerCase(), tabs = Object.keys(S5.tabs);
  const btn = (tex, name, tip) => `<button type="button" data-tex="${esc(tex)}" title="${esc(tip || `${name ? name + ' · ' : ''}${tex}`)}">${texSVG(tex, 17, st.scene.style)}</button>`;
  let body;
  if (q) {
    const hits = tabs.flatMap(t => symItems(t).filter(([tex, n]) => (tex + ' ' + (n || '')).toLowerCase().includes(q)).map(([tex, n, tip]) => btn(tex, n, tip)));
    body = hits.length ? `<div class="syms">${[...new Set(hits)].join('')}</div>` : `<p class="note">${esc(S5.none)}</p>`;
  } else {
    const tab = st.symTab, items = symItems(tab);
    const extra = tab === 'accent' ? `<div class="symbase"><label>${esc(S5.base)} <input id="symBase" value="${esc(st.symBase)}" maxlength="12" spellcheck="false"></label><div class="syms small">${ACC_BASES.map(b => `<button type="button" data-base="${esc(b)}" class="${b === st.symBase ? 'on' : ''}">${texSVG(b, 15, st.scene.style)}</button>`).join('')}</div><p class="note">${esc(S5.accentHint)}</p></div>`
      : tab === 'const' ? `<label class="chk"><input type="checkbox" id="symVal"${st.symValue ? ' checked' : ''}> ${esc(S5.withValue)}</label>`
      : tab === 'struct' ? `<p class="note">${esc(S5.structHint)}</p>` : tab === 'chem' ? `<p class="note">${esc(S5.chemHint)}</p>` : '';
    body = `${extra}<div class="syms${tab === 'struct' || tab === 'chem' || tab === 'const' ? ' wide' : ''}">${items.map(([tex, n, tip]) => btn(tex, n, tip)).join('')}</div>`;
  }
  const rec = symRecent();
  pop.innerHTML = `<div class="symhead"><b>${esc(S5.title)}</b><input type="search" id="symQ" placeholder="${esc(S5.search)}" aria-label="${esc(S5.search)}" value="${esc(st.symQ || '')}"><button type="button" data-close aria-label="✕">✕</button></div>
    ${rec.length ? `<div class="symrec"><span class="note">${esc(S5.recent)}</span><div class="syms">${rec.map(t => btn(t)).join('')}</div></div>` : ''}
    <div class="tabs symtabs" role="tablist">${tabs.map(t => `<button type="button" role="tab" data-symtab="${t}" aria-selected="${!q && t === st.symTab}" class="${!q && t === st.symTab ? 'on' : ''}">${esc(S5.tabs[t])}</button>`).join('')}</div>
    <div class="symbody">${body}</div>`;
  pop.querySelector('[data-close]').onclick = () => { pop.hidden = true; height(); };
  pop.querySelectorAll('[data-tex]').forEach(b => { b.onmousedown = e => e.preventDefault(); b.onclick = () => insertSymbol(b.dataset.tex); });
  pop.querySelectorAll('[data-symtab]').forEach(b => b.onclick = () => { st.symTab = b.dataset.symtab; st.symQ = ''; paintSymbols(); height(); });
  pop.querySelectorAll('[data-base]').forEach(b => { b.onmousedown = e => e.preventDefault(); b.onclick = () => { st.symBase = b.dataset.base; paintSymbols(); }; });
  const sb = $('symBase'); if (sb) sb.oninput = () => { st.symBase = sb.value.trim() || 'x'; const pos = sb.selectionStart; paintSymbols(); const s2 = $('symBase'); s2.focus(); s2.setSelectionRange(pos, pos); };
  const sv = $('symVal'); if (sv) sv.onchange = () => { st.symValue = sv.checked; paintSymbols(); };
  const sq = $('symQ'); sq.oninput = () => { st.symQ = sq.value; const pos = sq.selectionStart; paintSymbols(); const s2 = $('symQ'); s2.focus(); s2.setSelectionRange(pos, pos); };
}
/* insert at the caret of the text field last used (else a new label): a structure whose first box is its base (X_□)
   right after a letter takes that letter as its base; the first box of what was put in is selected */
function insertSymbol(tex) {
  store.set(SYM_RECENT, JSON.stringify([tex, ...symRecent().filter(x => x !== tex)].slice(0, 16)));
  const t = st.lastText, o = t && byId(t.id);
  const select = (el, from, to) => { const i = to.indexOf(PLACEHOLDER, from); const c = i >= 0 ? i : Math.min(to.length, from); el.focus(); el.setSelectionRange(c, i >= 0 ? c + 1 : c); st.lastText = {...st.lastText, caret: c, caretEnd: i >= 0 ? c + 1 : c}; };
  if (o && FIELDS[o.type][t.k]?.k === 'txt') {
    const el = document.querySelector(`[data-f="${t.k}"]`), live = el && el.value !== undefined ? el.value : String(o[t.k] || ''), cur = live;
    const a = el && document.activeElement === el ? el.selectionStart : (t.caret ?? cur.length), b = el && document.activeElement === el ? el.selectionEnd : (t.caretEnd ?? a);
    let ins = tex;
    /* a script right after its base: Q then X_□ gives Q_□ */
    if (ins.startsWith(PLACEHOLDER + '_') || ins.startsWith(PLACEHOLDER + '^')) { const before = cur.slice(0, a); if (/([A-Za-z0-9}')|]|\\[A-Za-z]+)$/.test(before) && a === b) ins = ins.slice(1); }
    /* a placeholder that is selected is replaced by what is inserted */
    const val = cur.slice(0, a) + ins + (/^\\[A-Za-z]+$/.test(ins) && /^[A-Za-z]/.test(cur.slice(b)) ? ' ' : '') + cur.slice(b);
    const max = FIELDS[o.type][t.k].max;
    if (val.length > max) { flash(esc(X5.sym.tooLong)); st.lastText = null; return insertSymbol(tex); }
    const next = clone(st.scene); next.objects.find(x => x.id === o.id)[t.k] = val;
    if (commit(next, {keepSel: true})) { setSel([o.id]); paint(); const el2 = document.querySelector(`[data-f="${t.k}"]`); if (el2) select(el2, a, val); }
    return;
  }
  const v = dview(), next = clone(st.scene), id = freeId('label'), text = tex.startsWith(PLACEHOLDER + '_') || tex.startsWith(PLACEHOLDER + '^') ? tex : tex;
  next.objects.push({...defaults('label'), id, x: r4(snapV(v.x + v.w / 2)), y: r4(snapV(v.y + v.h / 2)), text: text.slice(0, FIELDS.label.text.max)});
  if (commit(next)) { setSel([id]); st.lastText = {id, k: 'text'}; paint(); const el2 = document.querySelector('[data-f="text"]'); if (el2) select(el2, 0, el2.value); }
}
const drawStorage = window.HL_WORKSHOP_PROJECTS.client({base:API, token});
async function saveGroupAsset(ids) {
  if (!token()) { $('saveStatus').textContent = X6.aiErr.login_required; return; }
  const name = prompt(ko ? '에셋 이름' : 'Asset name', ko ? '물체 그룹' : 'Object group')?.trim().slice(0,60);
  if (!name) return;
  const selected = new Set(ids), scene = clone(st.scene);
  for (const o of scene.objects) {
    if (!selected.has(o.id) && LINKS.includes(o.type)) {
      const refs = refsOf(o);
      if (refs.length && refs.every(id => selected.has(id))) selected.add(o.id);
    }
  }
  removeIds(scene, scene.objects.filter(o => !selected.has(o.id)).map(o => o.id));
  const clean = validateScene({...scene, title:name, groups:[ids]}, {lenient:true}).scene;
  if (clean.objects.length < 2) { $('saveStatus').textContent = T.loadBad; return; }
  clean.groups = [clean.objects.map(o => o.id)];
  clean.view = sceneBounds(clean);
  const data = {...clean, asset:'group'};
  const status = $('saveStatus'), provider = $('drawProvider').querySelector('select').value;
  status.textContent = ko ? '에셋 저장 중…' : 'Saving asset…';
  try {
    if (provider === 'store') await api('/api/workshop/storage/files','POST',projectUpload(JSON.stringify(data), projectFileName(name), {folder:'에셋',ensure_folder:'1'}), true);
    else await drawStorage.saveExternal(provider,'asset',name,data);
    status.textContent = ko ? '에셋을 저장했습니다.' : 'Asset saved.';
  } catch (e) { status.textContent = window.HL_WORKSHOP_PROJECTS.error(e); }
  height();
}
function openAssetLibrary() {
  const dialog = document.createElement('dialog'), host = document.createElement('div');
  dialog.className = 'stdlg';
  const close = document.createElement('button');
  close.type = 'button'; close.textContent = ko ? '닫기' : 'Close'; close.onclick = () => dialog.close();
  dialog.append(close, host);
  dialog.addEventListener('close', () => { dialog.remove(); $('bInsertAsset').focus(); height(); });
  document.body.append(dialog);
  dialog.showModal();
  const library = window.HL_WORKSHOP_PROJECTS.library(host, drawStorage, {
    kind:'asset', title:ko ? '에셋 불러오기' : 'Insert asset', height,
    initial:$('drawProvider').querySelector('select').value,
    onOpen(raw) {
      const {scene, ok} = validateScene(raw);
      if (!ok || raw.asset !== 'group' || scene.objects.length < 2) throw new Error(T.loadBad);
      const view = dview(), bounds = scene.view || sceneBounds(scene);
      if (scene.style !== st.scene.style) for (const o of scene.objects) if (!o.style) o.style = scene.style;
      const dx = view.x+view.w/2-bounds.x-bounds.w/2, dy = view.y+view.h/2-bounds.y-bounds.h/2;
      if (!insertObjects(scene, dx, dy)) throw new Error(st.scene.objects.length + scene.objects.length > MAX_OBJECTS ? T.tooMany : T.loadBad);
      dialog.close();
    },
  });
  library.heading.id = 'assetLibraryTitle';
  dialog.setAttribute('aria-labelledby', library.heading.id);
  library.heading.focus();
  height();
}
function showDrawEditor() {
  $('drawProjects').hidden = true;
  $('drawEditor').hidden = false;
  $('drawProvider').querySelector('select').value = st.storeIds?.provider || 'store';
  paint();
}
function showDrawProjects() {
  stopSim();
  $('drawEditor').hidden = true;
  const host = $('drawProjects');
  host.hidden = false;
  const library = window.HL_WORKSHOP_PROJECTS.library(host, drawStorage, {
    kind:'figure', unified:true, title:ko ? '그림 프로젝트' : 'Figure projects', height,
    onNew() {
      if (!canLeaveProject()) return;
      replaceProject({title:'', index:0, pages:[blankPage()]});
      showDrawEditor();
      $('projectTitle').focus();
    },
    onResume:showDrawEditor,
    onOpen(raw, entry) {
      const project = decodeProject(raw);
      if (!project) throw new Error(T.loadBad);
      if (!canLeaveProject()) return;
      project.title ||= entry.name.replace(/\.json$/i,'');
      const ids = entry.provider === 'store' ? {json:entry.id, base:entry.updated_at, name:entry.name} : entry;
      replaceProject(project, ids);
      showDrawEditor();
      $('projectTitle').focus();
    },
  });
  library.heading.focus();
  height();
}
function paintTemplates() {
  const box = $('templateCards'), domain = $('templateDomain').value;
  box.innerHTML = TEMPLATE_KEYS.filter(key => TEMPLATE_DOMAIN[key] === domain).map(key => {
    const scene = template(key, lang);
    const src = svgDataUrl(renderSVG(scene, {width: 160, view: scene.view || sceneBounds(scene)}));
    return `<button type="button" data-template="${key}"><img alt="" src="${src}" loading="lazy"><span>${esc(TEMPLATE_NAMES[key][lang])}</span></button>`;
  }).join('');
  box.querySelectorAll('[data-template]').forEach(button => button.onclick = () => {
    const key = button.dataset.template, scene = validateScene(template(key, lang)).scene;
    st.dom = TEMPLATE_DOMAIN[key];
    if (st.scene.objects.length) addProjectPage(scene);
    else { st.projectChanged = true; st.project.pages[st.project.index] = scene; selectProjectPage(st.project.index); }
  });
  height();
}
function shell() {
  const tl = X3.tools, panelControls = window.HL_WORKSHOP_PROJECTS.panelControls;
  $('app').innerHTML = `<section id="drawProjects" hidden></section><div id="drawEditor"><div class="head"><div><h1>${T.title}</h1><p class="lede">${T.lede}</p></div>
      <div class="project-actions"><button type="button" id="bOpenStore">${ko ? '프로젝트 목록' : 'Projects'}</button><span id="drawProvider"></span><button type="button" id="bSave" class="primary">${esc(X6.save)}</button></div></div>
    <div class="project-line"><label class="note" for="projectTitle">${ko ? '프로젝트 이름' : 'Project name'}</label><input id="projectTitle" maxlength="60" placeholder="${ko ? '제목 없는 프로젝트' : 'Untitled project'}"><select id="projectPages" aria-label="${ko ? '프로젝트의 그림' : 'Figures in project'}"></select><button type="button" id="projectAdd">${ko ? '+ 그림 추가' : '+ Add figure'}</button><button type="button" id="projectRemove">${ko ? '현재 그림 삭제' : 'Remove current figure'}</button><span id="saveStatus" class="note" role="status"></span></div>
    <div id="hint3"></div>
    <div class="dbar"><button type="button" id="bTemplates">${esc(X4.templates)}</button>
      <select id="styleSel" aria-label="${X2.style}" title="${X2.style}">${STYLE_KEYS.map(k => `<option value="${k}">${esc(X2.style)}: ${esc(STYLES[k].name[lang])}</option>`).join('')}</select><button type="button" id="bShare">${esc(X7.share)}</button>
      <button type="button" id="bInsertAsset">${ko ? '에셋 불러오기' : 'Insert asset'}</button><label class="btn"><input type="checkbox" id="selectMore" style="width:auto"> ${ko ? '여러 물체 선택' : 'Multi-select'}</label>
      <span class="sep"></span>
      <button type="button" id="bUndo" class="hist" title="${esc(tl.backT)}" aria-label="${esc(tl.backT)}">${tl.back}</button><button type="button" id="bRedo" class="hist" title="${esc(tl.fwdT)}" aria-label="${esc(tl.fwdT)}">${tl.fwd}</button>
      <button type="button" id="bDup" title="Ctrl+D">${T.dup}</button><button type="button" id="bCopy" title="Ctrl+C">${tl.copy}</button><button type="button" id="bPaste" title="Ctrl+V">${tl.paste}</button><button type="button" id="bDel" title="Delete">${T.del}</button><button type="button" id="bClear" class="danger">${tl.clear}</button><span class="sep"></span>
      <span class="zoom" role="group" aria-label="zoom"><button type="button" id="bZout" title="${esc(tl.zoomOut)} (−)" aria-label="${esc(tl.zoomOut)}">−</button><span id="zoomPct" class="pct">100%</span><button type="button" id="bZin" title="${esc(tl.zoomIn)} (+)" aria-label="${esc(tl.zoomIn)}">+</button><button type="button" id="bZfit" title="${esc(tl.zoomFit)} (0)">${tl.zoomFit}</button></span>
      <label class="btn"><input type="checkbox" id="cGrid" checked style="width:auto"> ${T.grid}</label><label class="btn"><input type="checkbox" id="cSnap" checked style="width:auto"> ${T.snap}</label><label class="btn"><input type="checkbox" id="cVals" style="width:auto"> ${tl.values}</label><button type="button" id="bFit" title="${esc(tl.frameMark)}">${T.fit}</button></div>
    <details class="aibox" id="aiBox"><summary>${ko ? '✨ AI 그림 작업' : '✨ AI figure maker'}</summary>
      <p class="note">${ko ? '문제 사진의 그림 영역은 Gemini 3.8 Flash로 찾습니다.' : 'Gemini 3.8 Flash finds figure regions in worksheet photos.'}</p>
      <div class="row"><label for="aiOutput">${ko ? '결과 형식' : 'Output'}</label><select id="aiOutput"><option value="scene">${ko ? '편집 가능한 시뮬레이션 도식' : 'Editable simulation figure'}</option><option value="illustration">${ko ? '시험지 삽화 · Gemini 3 Pro Image' : 'Worksheet illustration · Gemini 3 Pro Image'}</option></select>
      <label for="aiStyle" id="aiStyleLabel" hidden>${ko ? '삽화 그림체' : 'Illustration style'}</label><select id="aiStyle" hidden><option value="exam">${ko ? '시험지 흑백 선화' : 'Exam line art'}</option><option value="textbook">${ko ? '교과서 컬러 삽화' : 'Color textbook'}</option><option value="technical">${ko ? '과학 논문 도식' : 'Technical diagram'}</option></select></div>
      <textarea id="aiPrompt" aria-label="${ko ? '그림 설명 또는 복원 요청' : 'Figure description or tracing instructions'}" rows="2" maxlength="1200" placeholder="${esc(X6.aiHint)}"></textarea>
      <div class="row"><label class="note" for="aiPhoto">${ko ? '문제 사진 첨부' : 'Attach a problem photo'}</label><input type="file" id="aiPhoto" accept="image/jpeg,image/png,image/webp"><button type="button" id="aiClearPhoto" hidden>${ko ? '첨부 지우기' : 'Remove attachment'}</button><button type="button" id="aiDetect" hidden>${ko ? '그림 영역 찾기' : 'Find figure regions'}</button><button type="button" id="aiWhole" hidden>${ko ? '사진 전체 사용' : 'Use whole photo'}</button></div>
      <div id="aiScan" hidden><div class="ai-photo-preview"><img id="aiSource" alt="${ko ? '첨부한 문제 사진' : 'Attached worksheet photo'}"><span id="aiBoxOutline" aria-hidden="true"></span></div>
      <div class="row"><label for="aiRegion">${ko ? '사용할 영역' : 'Region to use'}</label><select id="aiRegion"></select></div></div>
      <div class="row"><label class="chk" id="aiEditLabel"><input type="checkbox" id="aiEditCur"> ${esc(X6.aiEdit)}</label><select id="aiModel" hidden aria-label="model"></select><button type="button" class="primary" id="aiGo">${esc(X6.aiGo)}</button></div><div id="aiMsg" class="note" role="status"></div><div id="aiProposal" hidden></div><div id="aiIllustration" hidden></div></details>
    <div id="aiNote" class="ainote" hidden></div>
    <div class="work" id="drawDock"><div class="draw-library" data-dock><div class="dock-bar"><span>${ko ? '도구와 템플릿' : 'Tools and templates'}</span>${panelControls('drawLibraryBody')}</div><div id="drawLibraryBody" data-dock-body>
      <details class="palwrap parts" id="templateShelf"><summary>${esc(X4.templates)}</summary><label class="note" for="templateDomain">${ko ? '분야' : 'Topic'}</label>
        <select id="templateDomain">${Object.keys(DOMAINS).filter(d => TEMPLATE_KEYS.some(k => TEMPLATE_DOMAIN[k] === d)).map(d => `<option value="${d}">${esc(X2.domains[d])}</option>`).join('')}</select>
        <div id="templateCards" class="template-cards"></div></details>
      <details class="palwrap parts" id="parts"${prefs().parts ? ' open' : ''}><summary title="${esc(X4.partsHint)}">${esc(X4.parts)}</summary><p class="note">${esc(X4.partsHint)}</p><input type="search" id="palSearch" placeholder="${esc(X2.search)}" aria-label="${esc(X2.search)}"><div id="palette" class="palette"></div></details></div></div>
      <section class="stage" data-dock><div class="dock-bar"><span>${ko ? '캔버스' : 'Canvas'}</span>${panelControls('canvas',{collapse:false})}</div><div id="tools" class="tools" role="toolbar" aria-label="${esc(X4.drawing)}"></div><div id="stageTop"><label class="note" id="penSmoothLabel" hidden><input type="checkbox" id="penSmooth" style="width:auto"${prefs().penSmooth !== false ? ' checked' : ''}> ${ko ? '펜 흔들림 보정' : 'Stabilize pen strokes'}</label><select id="objectPicker" aria-label="${ko ? '그림 요소 선택' : 'Select figure object'}"></select>
        <button type="button" id="inkGo" hidden title="${ko ? '선택한 획만 수식 인식 서비스에 전송합니다.' : 'Sends only the selected strokes to the formula recognizer.'}">${ko ? '선택한 획을 수식으로' : 'Recognize selected ink'}</button><span id="inkStatus" class="note" role="status"></span>
        <div id="inkProposal" hidden><label for="inkText" class="note">LaTeX</label><input id="inkText" maxlength="240"><div id="inkPreview"></div><button type="button" id="inkApply">${ko ? '수식 적용' : 'Apply formula'}</button><button type="button" id="inkDiscard">${ko ? '닫기' : 'Close'}</button></div></div><div id="canvas" class="canvas" tabindex="0" role="region" aria-label="${ko ? '그림 편집 캔버스' : 'Figure editing canvas'}"></div><p id="status" class="status" role="status"></p><p class="note hint">${esc(tl.zoomHint)}</p>
        <div class="simbar"><span id="mechBar" class="grp"><button type="button" class="primary" id="playBtn"></button><button type="button" id="resetBtn">⟲ ${T.reset}</button><button type="button" id="stepBtn">${ko ? '0.05초 진행' : 'Step 0.05 s'}</button>
          <label>${T.speed}<select id="speed">${[0.1, 0.25, 0.5, 1, 2].map(v => `<option value="${v}"${v === st.speed ? ' selected' : ''}>${v}×</option>`).join('')}</select></label>
          <label><input type="checkbox" id="cFbd"${st.fbd ? ' checked' : ''}>${T.fbd}</label><label id="rtLbl"><input type="checkbox" id="cRt"${st.rtrail ? ' checked' : ''}>${esc(X5.trails)}</label></span><label><input type="checkbox" id="cRead"${st.readouts ? ' checked' : ''}>${T.readouts}</label><label id="solveLbl"><input type="checkbox" id="cSolve"${st.solve ? ' checked' : ''}>${X2.solve}</label><span class="clock" id="clock"></span></div>
        <div id="readouts" class="readouts"></div></section>
      <div class="side" data-dock><div class="dock-bar"><span>${ko ? '속성과 내보내기' : 'Properties and export'}</span>${panelControls('drawSideBody')}</div><div id="drawSideBody" data-dock-body><section class="panel" id="props"></section><section class="panel" id="out"></section></div></div></div></div>`;
  window.HL_WORKSHOP_PROJECTS.bindPanels($('drawDock'),()=>{ if (!$('drawEditor').hidden) paintCanvas(); height(); });
  $('drawProvider').append(window.HL_WORKSHOP_PROJECTS.providerSelect(st.storeIds?.provider));

  $('projectTitle').onchange = e => { st.project.title = e.target.value.trim(); save(); paintProject(); };
  $('projectPages').onchange = e => selectProjectPage(+e.target.value);
  $('projectAdd').onclick = () => addProjectPage();
  $('projectRemove').onclick = () => {
    const p = st.project;
    if (p.pages.length < 2 || !confirm(ko ? '현재 그림을 프로젝트에서 삭제할까요?' : 'Remove this figure from the project?')) return;
    p.pages.splice(p.index, 1);
    st.projectChanged = true;
    selectProjectPage(Math.min(p.index, p.pages.length - 1));
    $('projectPages').focus();
  };
  $('bTemplates').onclick = () => { const shelf = $('templateShelf'); shelf.open = true; shelf.scrollIntoView({block: 'nearest'}); $('templateDomain').focus({preventScroll: true}); };
  $('templateShelf').ontoggle = e => { if (e.target.open) paintTemplates(); height(); };
  $('templateDomain').onchange = paintTemplates;
  $('aiOutput').onchange = syncAiControls;
  $('aiPhoto').onchange = resetAiPhoto;
  $('aiClearPhoto').onclick = () => { $('aiPhoto').value = ''; resetAiPhoto(); $('aiPhoto').focus(); };
  $('aiDetect').onclick = () => detectAiRegions();
  $('aiWhole').onclick = () => detectAiRegions({whole:true});
  $('aiRegion').onchange = paintAiOutline;
  syncAiControls();
  $('bInsertAsset').onclick = openAssetLibrary;
  $('bSave').onclick = toStorage; $('bOpenStore').onclick = showDrawProjects;
  $('aiGo').onclick = aiDraw; $('aiBox').ontoggle = () => { if ($('aiBox').open) aiModels(); };
  $('bShare').onclick = openShare;
  { const n = +params.get('share'); if (n > 0) { if (window.HL_SHARE) openShared(n); else addEventListener('load', () => openShared(n), {once: true}); } } $('aiPrompt').onkeydown = e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) aiDraw(); };
  $('bUndo').onclick = undo; $('bRedo').onclick = redo; $('bDup').onclick = dup; $('bDel').onclick = del; $('bClear').onclick = clearAll;
  $('bCopy').onclick = () => { if (copySel()) paintBar(); }; $('bPaste').onclick = () => pasteClip();
  $('bZin').onclick = () => zoomBy(1.25); $('bZout').onclick = () => zoomBy(0.8); $('bZfit').onclick = () => { st.zoom = null; paintCanvas(); };
  $('cGrid').onchange = e => { st.grid = e.target.checked; paintCanvas(); }; $('cSnap').onchange = e => { st.snap = e.target.checked; };
  $('cVals').onchange = e => { const next = clone(st.scene); next.values = e.target.checked; commit(next, {keepSel: true}); };
  $('bFit').onclick = () => { const next = clone(st.scene); next.view = sceneBounds(next); st.zoom = null; commit(next, {keepSel: true}); };
  $('palSearch').oninput = e => { st.q = e.target.value; paintPalette(); height(); };
  $('styleSel').onchange = e => { const next = clone(st.scene); next.style = e.target.value; commit(next, {keepSel: true}); const pop = $('symPop'); if (pop) { pop.remove(); } };
  $('cSolve').onchange = e => { st.solve = e.target.checked; paintCanvas(); paintReadouts(); };
  $('playBtn').onclick = () => st.playing ? pause() : play();
  $('resetBtn').onclick = () => { stopSim(); paint(); };
  $('stepBtn').onclick = stepSimulation;
  $('speed').onchange = e => { st.speed = +e.target.value; };
  $('cFbd').onchange = e => { st.fbd = e.target.checked; paintCanvas(); };
  $('cRt').onchange = e => { st.rtrail = e.target.checked; paintCanvas(); };
  $('cRead').onchange = e => { st.readouts = e.target.checked; paintReadouts(); };
  $('parts').ontoggle = e => { setPref('parts', e.target.open); height(); };
  $('objectPicker').onchange = e => {
    const id = e.target.value;
    if (id && st.sim) stopSim();
    if (id && $('selectMore').checked) toggleSelection(id);
    else setSel(id ? [id] : []);
    paint();
  };
  $('inkGo').onclick = recognizeInk;
  $('inkDiscard').onclick = () => { $('inkProposal').hidden = true; $('canvas').focus(); height(); };
  $('penSmooth').onchange = e => setPref('penSmooth', e.target.checked);
  bindCanvas(); paintHint(); paintTools(); paint(); paintOut();
  if (!params.get('t') && !params.get('share')) showDrawProjects();
}
/* the three steps a new member sees once (dismissed for good, in this browser) */
function paintHint() {
  const box = $('hint3'); if (!box) return;
  if (store.get('hlDrawHint') === '1') { box.innerHTML = ''; box.hidden = true; return; }
  box.hidden = false; box.className = 'hint3';
  box.innerHTML = `<b>${esc(X4.hintTitle)}</b><ol>${X4.hint.map(t => `<li>${esc(t)}</li>`).join('')}</ol><button type="button" id="hintClose">${esc(X4.hintClose)}</button>`;
  $('hintClose').onclick = () => { store.set('hlDrawHint', '1'); paintHint(); height(); };
}
/* the drawing toolbar: the tools, then the look of what they draw (also applied to the selected shapes) */
const STYLE_FIELDS = ['color', 'lw', 'pattern', 'fill', 'heads'];
function paintTools() {
  if ($('penSmoothLabel')) $('penSmoothLabel').hidden = st.tool !== 'pen';
  const box = $('tools'); if (!box) return;
  const ds = st.dstyle, sw = c => `<button type="button" class="swatch${ds.color === c ? ' on' : ''}" data-color="${c}" title="${esc(X4.enums[c])}" aria-label="${esc(X4.enums[c])}" style="--c:${COLOR_HEX[c]}"></button>`;
  box.innerHTML = `<div class="tgroup">${TOOLS.map(t => `<button type="button" class="tool${st.tool === t ? ' on' : ''}" data-tool="${t}" title="${esc(X4.tools[t])}" aria-label="${esc(X4.tools[t])}" aria-pressed="${st.tool === t}">${TOOL_ICON[t]}</button>`).join('')}<button type="button" id="bSym" class="tool" aria-label="${esc(X2.symbols)}" title="${esc(X2.symTitle)}">Ω</button></div>
    <div class="tgroup geo" role="group" aria-label="${esc(X5.geoGroup)}"><span class="tlabel">${esc(X5.geoGroup)}</span>${GEO_TOOLS.map(t => `<button type="button" class="tool${st.tool === t ? ' on' : ''}" data-tool="${t}" title="${esc(X5.geoTools[t])}" aria-label="${esc(X5.geoTools[t])}" aria-pressed="${st.tool === t}">${GEO_ICON[t]}</button>`).join('')}</div>
    <div class="tgroup tstyle"><span class="swatches" role="group" aria-label="${esc(X4.style.color)}">${COLORS.map(sw).join('')}</span>
      <label title="${esc(X4.style.width)}">${esc(X4.style.width)}<select data-ds="lw">${[0.5, 0.75, 1, 1.5, 2, 3].map(v => `<option value="${v}"${v === ds.lw ? ' selected' : ''}>${v}×</option>`).join('')}</select></label>
      <label title="${esc(X4.style.dash)}">${esc(X4.style.dash)}<select data-ds="pattern">${['solid', 'dashed', 'dotted', 'dashdot'].map(v => `<option value="${v}"${v === ds.pattern ? ' selected' : ''}>${esc(T.enums[v])}</option>`).join('')}</select></label>
      <label title="${esc(X4.style.fill)}">${esc(X4.style.fill)}<select data-ds="fill">${FILLS.map(v => `<option value="${v}"${v === ds.fill ? ' selected' : ''}>${esc(X4.enums[v] || T.enums[v] || v)}</option>`).join('')}</select></label>
      <span class="heads" title="${esc(X4.style.heads)}">${esc(X4.style.heads)} <label><input type="checkbox" data-dh="hs"${ds.hs ? ' checked' : ''}>${esc(X4.style.start)}</label><label><input type="checkbox" data-dh="he"${ds.he ? ' checked' : ''}>${esc(X4.style.end)}</label></span></div>`;
  box.querySelectorAll('[data-tool]').forEach(b => b.onclick = () => setTool(b.dataset.tool));
  $('bSym').onclick = openSymbols;
  const keep = () => setPref('dstyle', st.dstyle);
  /* the look goes to the selected shapes too (one step of history) */
  const toSel = (k, v) => { const ids = new Set(selIds()); if (!ids.size) return; const next = clone(st.scene); let any = false;
    for (const o of next.objects) if (ids.has(o.id) && k in FIELDS[o.type]) { if (k === 'heads' && !FIELDS[o.type].heads.list.includes(v)) continue; if (k === 'fill' && !FIELDS[o.type].fill.list.includes(v)) continue; if (k === 'color' && !FIELDS[o.type].color.list.includes(v)) continue; o[k] = v; any = true; }
    if (any) commit(next, {keepSel: true}); };
  box.querySelectorAll('[data-color]').forEach(b => b.onclick = () => { ds.color = b.dataset.color; keep(); toSel('color', ds.color); paintTools(); });
  box.querySelectorAll('[data-ds]').forEach(el => el.onchange = () => { const k = el.dataset.ds; ds[k] = k === 'lw' ? +el.value : el.value; keep(); toSel(k, ds[k]); });
  box.querySelectorAll('[data-dh]').forEach(el => el.onchange = () => { ds[el.dataset.dh] = el.checked; keep(); toSel('heads', headsOf(ds)); });
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
  $('mechBar').hidden = !mech; $('clock').hidden = !mech; $('solveLbl').hidden = !circ; $('rtLbl').hidden = !hasPhys();
  if (!mech && st.sim) stopSim();
}
function inkObjects() { return selIds().map(byId).filter(o => o.type === 'poly' && !o.closed && o.pts.length >= 2); }
async function recognizeInk() {
  const items = inkObjects(), box = $('inkStatus'), button = $('inkGo');
  if (!items.length || button.disabled) return;
  if (items.length > 32) { box.textContent = ko ? '수식에 해당하는 획을 32개 이하로 선택해 주세요.' : 'Select no more than 32 strokes for the formula.'; return; }
  if (!token()) { box.textContent = T.storeLogin; return; }
  const base = JSON.stringify(projectData()), ids = new Set(items.map(o => o.id));
  const paths = items.map(o => o.pts), points = paths.flat();
  const x = Math.min(...points.map(p => p[0])), y = Math.max(...points.map(p => p[1]));
  const w = Math.max(...points.map(p => p[0])) - x, h = y - Math.min(...points.map(p => p[1]));
  const scale = 900 / Math.max(0.001, w, h);
  const strokes = paths.map(path => path.map(p => [Math.round(16+(p[0]-x)*scale), Math.round(16+(y-p[1])*scale)]));
  button.disabled = true;
  $('inkProposal').hidden = true;
  box.textContent = ko ? '수식 인식 중…' : 'Recognizing formula…';
  try {
    const {latex} = await api('/api/workshop/ink-formula', 'POST', {strokes});
    if (base !== JSON.stringify(projectData())) {
      box.textContent = ko ? '그림이 바뀌었습니다. 현재 획을 선택해 다시 인식해 주세요.' : 'The figure changed. Select the current strokes and try again.';
      return;
    }
    const field = $('inkText'), render = () => { $('inkPreview').innerHTML = texSVG(field.value, 24, st.scene.style); height(); };
    field.value = latex;
    field.oninput = render;
    $('inkApply').onclick = () => {
      if (base !== JSON.stringify(projectData())) { box.textContent = ko ? '그림이 바뀌었습니다. 다시 인식해 주세요.' : 'The figure changed. Recognize the ink again.'; return; }
      const text = field.value.trim();
      if (!text) return;
      const next = clone(st.scene), id = freeId('label');
      next.objects = next.objects.filter(o => !ids.has(o.id));
      next.objects.push({...defaults('label'), id, x:r4(x+w/2), y:r4(y-h/2), text, color:items[0].color});
      if (commit(next)) {
        setSel([id]); paint();
        $('inkProposal').hidden = true;
        box.textContent = ko ? '수식으로 바꿨습니다. 실행 취소로 되돌릴 수 있습니다.' : 'Converted to a formula. You can undo this change.';
        $('canvas').focus();
      }
      height();
    };
    $('inkProposal').hidden = false;
    box.textContent = ko ? '인식 결과를 확인하고 적용하세요.' : 'Review the recognized formula before applying.';
    render(); field.focus();
  } catch (e) {
    box.textContent = e.code === 'ocr_engine_unavailable' ? (ko ? '수식 인식 서비스가 아직 연결되지 않았습니다.' : 'Formula recognition is not configured.')
      : (ko ? '수식을 읽지 못했습니다. 수식에 해당하는 획만 선택해 다시 시도해 주세요.' : 'Could not read the formula. Select only its strokes and try again.');
  } finally { button.disabled = false; height(); }
}
function paintObjectPicker() {
  $('inkGo').hidden = !inkObjects().length;
  const picker = $('objectPicker');
  const elements = st.scene.objects.map(o => {
    const type = o.type === 'element' ? X2.kinds[o.kind] : T.types[o.type];
    const caption = o.label || (o.type === 'label' ? o.text : '');
    const lock = o.lock ? ' · ' + (ko ? '잠김' : 'Locked') : '';
    return `<option value="${esc(o.id)}">${esc([o.id, type, caption].filter(Boolean).join(' · ') + lock)}</option>`;
  });
  picker.innerHTML = `<option value="">${ko ? '그림 요소 선택…' : 'Select figure object…'}</option>${elements.join('')}`;
  picker.value = selIds().length === 1 ? st.sel : '';
  picker.disabled = !elements.length;
}
function paint() {
  paintProject(); paintObjectPicker(); paintCanvas(); paintSide(); paintReadouts(); paintSimBar(); status(); paintAi(); paintPalette(); paintBar();
  if ($('styleSel')) $('styleSel').value = st.scene.style;
  height();
}
function height() { if (embedded) requestAnimationFrame(() => window.parent.postMessage({type: 'hl-draw-height', height: Math.ceil(document.querySelector('main').getBoundingClientRect().bottom + scrollY + 16)}, location.origin)); }
let lastW = 0;
if (typeof ResizeObserver === 'function') new ResizeObserver(() => { height(); const w = $('canvas')?.clientWidth || 0; if (w && Math.abs(w - lastW) > 30) { lastW = w; paintCanvas(); } }).observe(document.body);
addEventListener('keydown', e => {
  if ($('drawEditor')?.hidden || e.defaultPrevented || e.isComposing || e.target.closest?.('input,textarea,select,[contenteditable]')) return;
  const mod = e.ctrlKey || e.metaKey, k = e.key.toLowerCase();
  // Native controls keep their normal Space and Enter activation.
  if ((e.key === ' ' || e.key === 'Enter') && e.target.closest?.('button,a,label,summary')) return;
  if (e.key === ' ' && $('canvas')?.contains(e.target)) { st.space = true; $('canvas').classList.add('panning'); e.preventDefault(); return; }
  if (e.key === 'Escape' && st.draft) { st.draft = null; paintCanvas(); status(); return; }
  if (e.key === 'Enter' && st.draft) { e.preventDefault(); if (!geoFinish()) finishDraft(); return; }
  if (!mod && !e.altKey && TOOL_KEY[k] && !(selIds().length && e.key.startsWith('Arrow'))) { setTool(TOOL_KEY[k]); return; }
  if (e.key === 'Escape') { st.connect = null; if (st.tool !== 'select') setTool('select'); setSel([]); paint(); }
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
    const moving = new Set(next.objects.filter(x => ids.has(x.id) && !x.lock && !NO_DRAG.includes(x.type)).map(x => x.id));
    for (const x of next.objects) if (moving.has(x.id)) {
      if (isBody(x) && x.on && !moving.has(x.on)) x.at = r4(x.at + (dx || dy));
      else moveObj(x, dx, dy, clone(x), moving.has(x.on));
    }
    commit(next, {keepSel: true});
  }
});
function releasePan() { st.space = false; $('canvas')?.classList.remove('panning'); }
addEventListener('keyup', e => { if (e.key === ' ') releasePan(); });
addEventListener('blur', releasePan);
try { const d = prefs().dstyle; if (d && typeof d === 'object') { const ds = st.dstyle; if (COLORS.includes(d.color)) ds.color = d.color; if ([0.5, 0.75, 1, 1.5, 2, 3].includes(d.lw)) ds.lw = d.lw; if (['solid', 'dashed', 'dotted', 'dashdot'].includes(d.pattern)) ds.pattern = d.pattern; if (FILLS.includes(d.fill)) ds.fill = d.fill; ds.hs = d.hs === true; ds.he = d.he === true; } } catch (e) {}
st.scene = startScene();
st.project ||= {title: '', index: 0, pages: [st.scene]};
if (!st.projectChanged) st.savedSignature = projectSignature();
if (st.unlinkedStart) keepStoreIds(null);
if (!st.scene.view) st.scene.view = sceneBounds(st.scene);
if (document.readyState === 'loading') addEventListener('DOMContentLoaded', shell); else shell();
