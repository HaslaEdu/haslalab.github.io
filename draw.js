/* The Workshop's figure and simulation editor (#/workshop/draw, draw.html in a frame). A figure is a scene
   (draw-scene.mjs): objects with values in SI units, drawn as an exam figure (draw-render.mjs) and run by the solver
   (draw-physics.mjs). Objects come from the palette or a template, are dragged on a grid and edited by value in the side
   panel. The figure goes out as SVG or PNG, onto the test paper of the problem maker (teach.js reads the paper from
   localStorage 'hlTeachPaper'; the figure is an SVG data URL with its scene), into the member's storage
   (/api/workshop/storage) or into this browser. "Start from a photo" sends one photo to /api/workshop/scene-from-image
   (community/src/workshop-scene.js) and opens what comes back for checking. */
import {validateScene, defaults, template, TEMPLATE_KEYS, TEMPLATE_NAMES, FIELDS, isBody, bodyPose, surfaceFrame, sceneBounds, vec, blankScene, MAX_OBJECTS} from './draw-scene.mjs?v=821b2b258cf0';
import {buildSim} from './draw-physics.mjs?v=e409d69aebc7';
import {renderSVG} from './draw-render.mjs?v=3f0095a65808';

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
  texHint: 'm_1, v_0, \\theta, \\mu 처럼 쓰면 아래 첨자와 그리스 문자가 됩니다.',
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
  texHint: 'Write m_1, v_0, \\theta, \\mu for subscripts and Greek letters.',
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
const SCENE_KEY = 'hlDrawScene', SAVES_KEY = 'hlDrawSaves', PAPER_KEY = 'hlTeachPaper', EDIT_KEY = 'hlDrawEdit';
const st = {scene: null, sel: '', undo: [], redo: [], connect: null, grid: true, snap: true, fbd: false, readouts: true,
  sim: null, playing: false, speed: 1, last: 0, trails: new Map(), samples: [], graph: '', ai: null, msg: '', paperEdit: null, drag: null};
const clone = o => JSON.parse(JSON.stringify(o));
function startScene() {
  const t = params.get('t');
  if (t && TEMPLATE_KEYS.includes(t)) return validateScene(template(t, lang)).scene;
  /* a figure sent from the paper to be changed (teach.js "그림 고치기") */
  try { const e = JSON.parse(store.get(EDIT_KEY) || 'null'); if (e && typeof e.key === 'string' && e.scene) { const r = validateScene(e.scene); if (r.ok) { st.paperEdit = e.key; store.del(EDIT_KEY); return r.scene; } } } catch (e) {}
  try { const r = validateScene(JSON.parse(store.get(SCENE_KEY) || 'null')); if (r.ok && r.scene.objects.length) return r.scene; } catch (e) {}
  return validateScene(template('incline_pulley', lang)).scene;
}
const byId = id => st.scene.objects.find(o => o.id === id);
const view = () => st.scene.view || (st.scene.view = sceneBounds(st.scene));
/* every change goes through here: checked, kept for undo, saved in this browser */
function commit(next, {keepSel = false} = {}) {
  const r = validateScene(next);
  if (!r.ok) { flash(`<span class="bad">${T.invalid}: ${esc(r.errors.map(e => (e.id ? e.id + '.' : '') + (e.field || e.code)).slice(0, 3).join(', '))}</span>`); return false; }
  st.undo.push(JSON.stringify(st.scene)); if (st.undo.length > 120) st.undo.shift(); st.redo = [];
  st.scene = r.scene; if (!keepSel && st.sel && !byId(st.sel)) st.sel = '';
  stopSim(); save(); paint(); return true;
}
const save = () => store.set(SCENE_KEY, JSON.stringify(st.scene));
function undo() { if (!st.undo.length) return; st.redo.push(JSON.stringify(st.scene)); st.scene = JSON.parse(st.undo.pop()); if (st.sel && !byId(st.sel)) st.sel = ''; stopSim(); save(); paint(); }
function redo() { if (!st.redo.length) return; st.undo.push(JSON.stringify(st.scene)); st.scene = JSON.parse(st.redo.pop()); stopSim(); save(); paint(); }
let flashTimer;
function flash(html) { st.msg = html; const el = $('status'); if (el) el.innerHTML = html; clearTimeout(flashTimer); flashTimer = setTimeout(() => { st.msg = ''; status(); }, 6000); }

/* ids: the type's letter and the first free number */
const PREFIX = {block: 'm', ball: 'b', floor: 'f', ceiling: 'c', wall: 'w', incline: 'i', pulley: 'p', pivot: 'o', string: 's', rod: 'r', spring: 'k', force: 'F', label: 'l', dim: 'd', arc: 'a', axes: 'x', line: 'n'};
const freeId = type => { let n = 1; while (byId(PREFIX[type] + n)) n++; return PREFIX[type] + n; };
const snapV = v => st.snap ? Math.round(v / st.scene.grid) * st.scene.grid : v;
const r4 = v => Math.round(v * 1e4) / 1e4;

function addObject(type) {
  if (st.scene.objects.length >= MAX_OBJECTS) { flash(`<span class="bad">${T.tooMany}</span>`); return; }
  if (['string', 'rod', 'spring', 'force'].includes(type)) {
    const sel = byId(st.sel);
    if (type === 'force' && isBody(sel)) { finishConnect({type: 'force', a: sel.id}); return; }
    st.connect = {type, a: null, over: []}; st.sel = ''; paint(); return;
  }
  const v = view(), cx = snapV(v.x + v.w / 2), cy = snapV(v.y + v.h / 2), o = {...defaults(type), id: freeId(type)};
  if (type === 'floor' || type === 'ceiling') Object.assign(o, {x: snapV(v.x + v.w * 0.1), y: type === 'floor' ? snapV(v.y + v.h * 0.15) : snapV(v.y + v.h * 0.9), w: r4(snapV(v.w * 0.8))});
  else if (type === 'wall') Object.assign(o, {x: snapV(v.x + v.w * 0.1), y: snapV(v.y + v.h * 0.15), h: r4(snapV(v.h * 0.6))});
  else if (type === 'incline') Object.assign(o, {x: snapV(v.x + v.w * 0.15), y: snapV(v.y + v.h * 0.15), length: r4(snapV(Math.min(v.w * 0.6, v.h * 1.2)))});
  else if (type === 'dim' || type === 'line') Object.assign(o, {x1: cx - 0.5, y1: cy, x2: cx + 0.5, y2: cy});
  else Object.assign(o, {x: cx, y: cy});
  if (type === 'block') o.label = `m_${o.id.slice(1)}`;
  if (type === 'label') o.text = 'A';
  const next = clone(st.scene); next.objects.push(o);
  if (commit(next)) { st.sel = o.id; paint(); }
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
  if (commit(next)) { st.sel = id; paint(); }
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
    }
  }
}
function del() { if (!st.sel) return; const next = clone(st.scene); removeIds(next, [st.sel]); st.sel = ''; commit(next); }
function dup() {
  const o = byId(st.sel); if (!o || ['string', 'rod', 'spring', 'force'].includes(o.type)) return;
  if (st.scene.objects.length >= MAX_OBJECTS) { flash(`<span class="bad">${T.tooMany}</span>`); return; }
  const c = {...clone(o), id: freeId(o.type)}, d = st.scene.grid * 3;
  if (isBody(c) && c.on) c.at = r4(c.at + (c.type === 'ball' ? 2 * c.r : c.w) + st.scene.grid);
  else if ('x1' in c) { c.x1 += d; c.x2 += d; c.y1 -= d; c.y2 -= d; }
  else { c.x = r4(c.x + d); c.y = r4(c.y - d); }
  if (c.type === 'block' && /^m_\d+$/.test(o.label)) c.label = 'm_' + c.id.slice(1);
  const next = clone(st.scene); next.objects.push(c);
  if (commit(next)) { st.sel = c.id; paint(); }
}

/* ── the canvas ── */
const W = 800;
let shownScene = null, shownPoses = null;
function paintCanvas() {
  const box = $('canvas'); if (!box) return;
  const v = view(), simOn = !!st.sim;
  const sc = simOn ? st.sim.applyTo(st.scene) : st.scene;
  let forces = null;
  if (st.fbd) { try { forces = (simOn ? st.sim : buildSim(st.scene)).forces(); } catch (e) { forces = null; } }
  shownScene = sc; shownPoses = simOn ? st.sim.poses() : null;
  box.innerHTML = renderSVG(sc, {width: W, view: v, edit: true, grid: st.grid && !simOn, selected: simOn ? '' : st.sel, forces, poses: shownPoses,
    velocities: simOn ? st.sim.velocities() : null, anchors: simOn ? st.sim.anchors : null, trails: simOn ? [...st.trails].filter(([id]) => byId(id)?.trail) : null,
    conical: (simOn ? st.sim : null)?.systems.filter(s => s.kind === 'conical').map(s => ({centre: s.centre, radius: s.radius})) || st.scene.objects.filter(o => (o.type === 'string' || o.type === 'rod') && o.mode === 'conical').map(o => conicalOrbit(o)).filter(Boolean)});
  box.classList.toggle('connecting', !!st.connect);
}
function conicalOrbit(s) {
  const P = [byId(s.a), byId(s.b)].find(o => o?.type === 'pivot'), b = [byId(s.a), byId(s.b)].find(isBody);
  if (!P || !b) return null; const p = bodyPose(st.scene, b);
  return {centre: {x: P.x, y: p.y}, radius: Math.abs(p.x - P.x)};
}
function worldAt(ev) {
  const svg = $('canvas').querySelector('svg'), r = svg.getBoundingClientRect(), v = view(), H = svg.viewBox.baseVal.height;
  const px = (ev.clientX - r.left) * W / r.width, py = (ev.clientY - r.top) * H / r.height, S = W / v.w;
  return {x: v.x + px / S, y: v.y + v.h - py / S};
}
function pickAt(ev) { const g = ev.target.closest?.('[data-id]'); return g ? byId(g.dataset.id) : null; }
function bindCanvas() {
  const box = $('canvas');
  box.addEventListener('pointerdown', ev => {
    if (ev.button !== 0) return;
    const o = pickAt(ev);
    if (st.connect) { connectClick(o); return; }
    if (st.sim) { stopSim(); paint(); }
    st.sel = o ? o.id : ''; paintCanvas(); paintSide(); status();
    if (!o || ['string', 'rod', 'spring', 'force'].includes(o.type)) return;
    st.drag = {id: o.id, start: worldAt(ev), orig: clone(o), before: JSON.stringify(st.scene), moved: false};
    box.setPointerCapture?.(ev.pointerId);
  });
  box.addEventListener('pointermove', ev => {
    const d = st.drag; if (!d) return;
    const p = worldAt(ev), dx = p.x - d.start.x, dy = p.y - d.start.y;
    if (!d.moved && Math.hypot(dx, dy) * W / view().w < 3) return;
    d.moved = true; dragTo(d, p, dx, dy); paintCanvas();
  });
  const end = () => {
    const d = st.drag; st.drag = null; if (!d || !d.moved) return;
    const r = validateScene(st.scene);
    if (!r.ok) { st.scene = JSON.parse(d.before); paint(); return; }
    st.undo.push(d.before); st.redo = []; st.scene = r.scene; save(); paint();
  };
  box.addEventListener('pointerup', end); box.addEventListener('pointercancel', end);
}
/* where a dragged object goes: a body slides along the surface it rests on, drops onto one it is put near, or leaves it
   when pulled away; a body hanging from a pulley moves up and down only */
function dragTo(d, p, dx, dy) {
  const o = byId(d.id), g = d.orig; if (!o) return;
  if (isBody(o)) {
    const hanging = st.scene.objects.some(s => s.type === 'string' && s.over.length && (s.a === o.id || s.b === o.id)) && !g.on;
    if (g.on) {
      const fr = surfaceFrame(byId(g.on)), rel = vec.sub(p, fr.p0), off = vec.dot(rel, fr.n);
      if (off > -0.2 && off < 0.6 + (o.h || o.r || 0)) { o.on = g.on; o.at = r4(snapV(vec.dot(rel, fr.u))); placeOnFrame(o, fr); return; }
      o.on = ''; o.x = r4(snapV(p.x)); o.y = r4(snapV(p.y)); return;
    }
    if (hanging) { o.y = r4(snapV(g.y + dy)); return; }
    o.x = r4(snapV(g.x + dx)); o.y = r4(snapV(g.y + dy));
    const half = o.type === 'ball' ? o.r : o.h / 2;
    for (const s of st.scene.objects.filter(x => x.type === 'floor' || x.type === 'incline')) {
      const fr = surfaceFrame(s), rel = vec.sub(o, fr.p0), along = vec.dot(rel, fr.u), off = vec.dot(rel, fr.n) - half;
      if (Math.abs(off) < 0.12 && along >= 0 && along <= fr.length) { o.on = s.id; o.at = r4(snapV(along)); placeOnFrame(o, fr); return; }
    }
    return;
  }
  if ('x1' in g) { o.x1 = r4(snapV(g.x1 + dx)); o.y1 = r4(snapV(g.y1 + dy)); o.x2 = r4(g.x2 + (o.x1 - g.x1)); o.y2 = r4(g.y2 + (o.y1 - g.y1)); return; }
  if ('x' in g) { o.x = r4(snapV(g.x + dx)); o.y = r4(snapV(g.y + dy)); }
}
function placeOnFrame(o, fr) { const h = o.type === 'ball' ? o.r : o.h / 2, c = vec.add(vec.add(fr.p0, vec.mul(fr.u, o.at)), vec.mul(fr.n, h)); o.x = r4(c.x); o.y = r4(c.y); }

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
const NUM_STEP = {mass: 0.1, angle: 1, mu: 0.05, k: 1, F: 1, size: 1, coils: 1, from: 5, to: 5};
function paintSide() {
  const box = $('props'); if (!box) return;
  const o = byId(st.sel);
  if (!o) {
    box.innerHTML = `<h2>${T.scene}</h2><div class="props"><label class="wide">${T.sceneTitle}<input data-scene="title" maxlength="80" value="${esc(st.scene.title)}"></label>
      <label>${T.g}<input data-scene="g" type="number" step="0.1" value="${st.scene.g}"></label><label>${T.gridSize}<input data-scene="grid" type="number" step="0.05" value="${st.scene.grid}"></label></div>
      <p class="note">${T.noSel}</p><div class="note">${T.objects}</div><div class="olist">${st.scene.objects.map(x => `<button type="button" data-pick="${esc(x.id)}">${esc(x.id)} · ${T.types[x.type]}</button>`).join('')}</div>`;
    box.querySelectorAll('[data-scene]').forEach(el => el.onchange = () => { const next = clone(st.scene), k = el.dataset.scene; next[k] = k === 'title' ? el.value : parseFloat(el.value); commit(next); });
    box.querySelectorAll('[data-pick]').forEach(b => b.onclick = () => { st.sel = b.dataset.pick; paint(); });
    return;
  }
  const F = FIELDS[o.type], fields = Object.entries(F).filter(([k]) => !(isBody(o) && o.on && (k === 'x' || k === 'y')) && !(isBody(o) && !o.on && k === 'at'));
  const opts = (types, cur, optional) => (optional ? `<option value="">${T.none}</option>` : '') + st.scene.objects.filter(x => types.includes(x.type) && x.id !== o.id).map(x => `<option value="${esc(x.id)}"${x.id === cur ? ' selected' : ''}>${esc(x.id)} · ${T.types[x.type]}</option>`).join('');
  const optional = k => !(['string', 'rod', 'spring'].includes(o.type) && (k === 'a' || k === 'b')) && !(o.type === 'force' && k === 'on');
  const field = ([k, f]) => {
    const L = T.fields[k] || k;
    if (f.k === 'num') return `<label>${L}<input data-f="${k}" type="number" step="${NUM_STEP[k] || 0.05}" min="${f.min}" max="${f.max}" value="${r4(o[k])}"></label>`;
    if (f.k === 'bool') return `<label class="chk wide"><input data-f="${k}" type="checkbox"${o[k] ? ' checked' : ''}>${L}</label>`;
    if (f.k === 'enum') return `<label>${L}<select data-f="${k}">${f.list.map(v => `<option value="${v}"${v === o[k] ? ' selected' : ''}>${T.enums[v] || v}</option>`).join('')}</select></label>`;
    if (f.k === 'ref') return `<label>${L}<select data-f="${k}">${opts(f.types, o[k], optional(k))}</select></label>`;
    if (f.k === 'refs') { const ps = st.scene.objects.filter(x => x.type === 'pulley'); return ps.length ? `<div class="wide"><span class="note">${L}</span><div class="over">${ps.map(p => `<label><input type="checkbox" data-over="${esc(p.id)}"${o.over.includes(p.id) ? ' checked' : ''}>${esc(p.id)}</label>`).join('')}</div></div>` : ''; }
    return `<label class="wide">${L}<input data-f="${k}" maxlength="${f.max}" value="${esc(o[k])}"><span class="tex" data-tex="${k}"></span></label>`;
  };
  box.innerHTML = `<h2>${T.types[o.type]} <span class="note">${esc(o.id)}</span></h2><div class="props">${fields.map(field).join('')}</div>
    ${fields.some(([, f]) => f.k === 'txt') ? `<p class="note">${esc(T.texHint)}</p>` : ''}
    <div class="row">${['string', 'rod', 'spring', 'force'].includes(o.type) ? '' : `<button type="button" data-act="dup">${T.dup}</button>`}<button type="button" data-act="del">${T.del}</button></div>`;
  box.querySelectorAll('[data-f]').forEach(el => {
    const k = el.dataset.f, f = F[k];
    const apply = () => {
      const next = clone(st.scene), x = next.objects.find(y => y.id === o.id);
      if (f.k === 'num') { const v = parseFloat(el.value); if (!Number.isFinite(v)) { paintSide(); return; } x[k] = v; }
      else if (f.k === 'bool') x[k] = el.checked;
      else x[k] = el.value;
      if (k === 'on') {
        if (x.on) { const fr = surfaceFrame(next.objects.find(y => y.id === x.on)); x.at = r4(Math.max(0, Math.min(fr.length, vec.dot(vec.sub(bodyPose(st.scene, o), fr.p0), fr.u)))); }
        else { const p = bodyPose(st.scene, o); x.x = r4(p.x); x.y = r4(p.y); }
      }
      if (!commit(next, {keepSel: true})) paintSide();
    };
    el.onchange = apply;
    if (f.k === 'txt') el.oninput = () => texPreview(k, el.value);
    if (f.k === 'txt') texPreview(k, el.value);
  });
  box.querySelectorAll('[data-over]').forEach(el => el.onchange = () => {
    const next = clone(st.scene), x = next.objects.find(y => y.id === o.id), ids = [...box.querySelectorAll('[data-over]')].filter(c => c.checked).map(c => c.dataset.over);
    x.over = [...x.over.filter(id => ids.includes(id)), ...ids.filter(id => !x.over.includes(id))];
    alignHanging(next, x); commit(next, {keepSel: true});
  });
  box.querySelector('[data-act="dup"]')?.addEventListener('click', dup);
  box.querySelector('[data-act="del"]').onclick = del;
}
/* the label as KaTeX shows it, when KaTeX has loaded */
function texPreview(k, v) {
  const el = document.querySelector(`[data-tex="${k}"]`); if (!el) return;
  if (!window.katex || !v) { el.textContent = ''; return; }
  const tex = v.includes('$') ? v.replace(/\$/g, ' ') : /[가-힣]/.test(v) ? `\\text{${v.replace(/[{}\\]/g, '')}}` : v;
  try { window.katex.render(tex, el, {throwOnError: false}); } catch (e) { el.textContent = ''; }
}

/* ── readouts and the graph ── */
const fmt = v => Number.isFinite(v) ? (Math.abs(v) >= 1000 ? v.toFixed(0) : Math.abs(v) >= 100 ? v.toFixed(1) : v.toFixed(2)) : '—';
function paintReadouts() {
  const box = $('readouts'); if (!box) return;
  if (!st.readouts || !st.sim) { box.innerHTML = ''; return; }
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
function exportSvg() {
  const sc = st.sim ? st.sim.applyTo(st.scene) : st.scene;
  let forces = null; if (st.fbd) { try { forces = (st.sim || buildSim(st.scene)).forces(); } catch (e) {} }
  return renderSVG(sc, {width: W, view: view(), forces, poses: st.sim ? st.sim.poses() : null, velocities: st.sim ? st.sim.velocities() : null, anchors: st.sim?.anchors, title: st.scene.title || T.title,
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
  const svg = exportSvg(), src = svgDataUrl(svg), m = /viewBox="0 0 (\d+) (\d+)"/.exec(svg);
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
  st.sel = ''; st.ai = null; commit(r.scene);
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
    st.ai = {unsure: Array.isArray(r.unsure) ? r.unsure : [], left: r.left}; st.sel = '';
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
  box.querySelectorAll('[data-pick]').forEach(b => b.onclick = () => { st.sel = b.dataset.pick; paint(); });
}

/* ── the page ── */
const PALETTE = [['bodies', ['block', 'ball']], ['surfaces', ['floor', 'incline', 'wall', 'ceiling', 'pulley', 'pivot']], ['links', ['string', 'rod', 'spring', 'force']], ['marks', ['label', 'dim', 'arc', 'axes', 'line']]];
function shell() {
  $('app').innerHTML = `<div class="head"><div><h1>${T.title}</h1><p class="lede">${T.lede}</p></div></div>
    <div class="dbar"><select id="tpl" aria-label="${T.template}"><option value="">${T.template}…</option>${TEMPLATE_KEYS.map(k => `<option value="${k}">${esc(TEMPLATE_NAMES[k][lang])}</option>`).join('')}<option value="blank">${T.blank}</option></select>
      <label class="btn filebtn">📷 ${T.photo}<input type="file" id="photo" accept="image/jpeg,image/png,image/webp,image/*"></label><span class="sep"></span>
      <button type="button" id="bUndo" title="Ctrl+Z">↶ ${T.undo}</button><button type="button" id="bRedo" title="Ctrl+Y">↷ ${T.redo}</button><button type="button" id="bDup" title="Ctrl+D">${T.dup}</button><button type="button" id="bDel" title="Delete">${T.del}</button><span class="sep"></span>
      <label class="btn"><input type="checkbox" id="cGrid" checked style="width:auto"> ${T.grid}</label><label class="btn"><input type="checkbox" id="cSnap" checked style="width:auto"> ${T.snap}</label><button type="button" id="bFit">${T.fit}</button></div>
    <div id="aiNote" class="ainote" hidden></div>
    <div class="work"><nav class="palette" aria-label="${T.groups.bodies}">${PALETTE.map(([g, types]) => `<div class="grp"><h3>${T.groups[g]}</h3>${types.map(t => `<button type="button" data-add="${t}">${T.types[t]}</button>`).join('')}</div>`).join('')}</nav>
      <section class="stage"><div id="canvas" class="canvas"></div><p id="status" class="status" role="status"></p>
        <div class="simbar"><button type="button" class="primary" id="playBtn"></button><button type="button" id="resetBtn">⟲ ${T.reset}</button>
          <label>${T.speed}<select id="speed">${[0.1, 0.25, 0.5, 1, 2].map(v => `<option value="${v}"${v === st.speed ? ' selected' : ''}>${v}×</option>`).join('')}</select></label>
          <label><input type="checkbox" id="cFbd"${st.fbd ? ' checked' : ''}>${T.fbd}</label><label><input type="checkbox" id="cRead"${st.readouts ? ' checked' : ''}>${T.readouts}</label><span class="clock" id="clock"></span></div>
        <div id="readouts" class="readouts"></div></section>
      <div class="side"><section class="panel" id="props"></section><section class="panel" id="out"></section></div></div>`;
  $('tpl').onchange = e => { const k = e.target.value; e.target.value = ''; if (!k) return; st.ai = null; st.sel = ''; commit(k === 'blank' ? {...blankScene(), view: {x: -0.5, y: -0.5, w: 4, h: 3}} : validateScene(template(k, lang)).scene); };
  $('photo').onchange = e => { const f = e.target.files[0]; e.target.value = ''; photoFile(f); };
  $('bUndo').onclick = undo; $('bRedo').onclick = redo; $('bDup').onclick = dup; $('bDel').onclick = del;
  $('cGrid').onchange = e => { st.grid = e.target.checked; paintCanvas(); }; $('cSnap').onchange = e => { st.snap = e.target.checked; };
  $('bFit').onclick = () => { const next = clone(st.scene); next.view = sceneBounds(next); commit(next, {keepSel: true}); };
  document.querySelectorAll('[data-add]').forEach(b => b.onclick = () => addObject(b.dataset.add));
  $('playBtn').onclick = () => st.playing ? pause() : play();
  $('resetBtn').onclick = () => { stopSim(); paint(); };
  $('speed').onchange = e => { st.speed = +e.target.value; };
  $('cFbd').onchange = e => { st.fbd = e.target.checked; paintCanvas(); };
  $('cRead').onchange = e => { st.readouts = e.target.checked; paintReadouts(); };
  bindCanvas(); paint(); paintOut();
}
function paint() {
  paintCanvas(); paintSide(); paintReadouts(); paintSimBar(); status(); paintAi();
  document.querySelectorAll('[data-add]').forEach(b => b.classList.toggle('on', st.connect?.type === b.dataset.add));
  if ($('bUndo')) { $('bUndo').disabled = !st.undo.length; $('bRedo').disabled = !st.redo.length; $('bDel').disabled = !st.sel; $('bDup').disabled = !st.sel; }
  height();
}
function height() { if (embedded) requestAnimationFrame(() => window.parent.postMessage({type: 'hl-draw-height', height: Math.ceil(document.querySelector('main').getBoundingClientRect().bottom + scrollY + 16)}, location.origin)); }
if (typeof ResizeObserver === 'function') new ResizeObserver(height).observe(document.body);
addEventListener('keydown', e => {
  if (e.target.closest?.('input,textarea,select')) return;
  const mod = e.ctrlKey || e.metaKey;
  if (e.key === 'Escape') { st.connect = null; st.sel = ''; paint(); }
  else if (mod && e.key.toLowerCase() === 'z') { e.preventDefault(); e.shiftKey ? redo() : undo(); }
  else if (mod && e.key.toLowerCase() === 'y') { e.preventDefault(); redo(); }
  else if (mod && e.key.toLowerCase() === 'd') { e.preventDefault(); dup(); }
  else if ((e.key === 'Delete' || e.key === 'Backspace') && st.sel) { e.preventDefault(); del(); }
  else if (st.sel && e.key.startsWith('Arrow')) {
    const o = byId(st.sel); if (!o) return; e.preventDefault();
    const d = st.scene.grid, dx = e.key === 'ArrowLeft' ? -d : e.key === 'ArrowRight' ? d : 0, dy = e.key === 'ArrowDown' ? -d : e.key === 'ArrowUp' ? d : 0;
    const next = clone(st.scene), x = next.objects.find(y => y.id === o.id);
    if (isBody(x) && x.on) x.at = r4(x.at + (dx || dy)); else if ('x1' in x) { x.x1 += dx; x.x2 += dx; x.y1 += dy; x.y2 += dy; } else if ('x' in x) { x.x = r4(x.x + dx); x.y = r4(x.y + dy); } else return;
    commit(next, {keepSel: true});
  }
});
st.scene = startScene();
if (!st.scene.view) st.scene.view = sceneBounds(st.scene);
if (document.readyState === 'loading') addEventListener('DOMContentLoaded', shell); else shell();
