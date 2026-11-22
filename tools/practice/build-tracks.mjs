/* Builds the Learn section's exam tracks from tools/practice/tracks/<key>.json (original problems written for HaslaLab in
   each exam's style, each checked by a second, independent solver): practice/tracks.json (the list) and
   practice/track/<key>.json (the problems). Fails on any item that does not validate.
   usage: node tools/practice/build-tracks.mjs [--check] */
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../..');
const P = createRequire(import.meta.url)(path.join(root, 'learn-path.js'));
const check = process.argv.includes('--check');

export const TRACKS = [
  {key: 'ap1', name: {en: 'AP Physics 1', ko: 'AP Physics 1'}, exam: 'AP',
    blurb: {en: 'Algebra-based mechanics, rotation, oscillations and fluids. Exam in May.', ko: '대수 기반 역학 · 회전 · 진동 · 유체. 5월 시험.'},
    syl: [['u1', 'Kinematics', '운동학'], ['u2', 'Force and Translational Dynamics', '힘과 병진 운동'], ['u3', 'Work, Energy, and Power', '일 · 에너지 · 일률'],
      ['u4', 'Linear Momentum', '선운동량'], ['u5', 'Torque and Rotational Dynamics', '토크와 회전 운동'], ['u6', 'Energy and Momentum of Rotating Systems', '회전계의 에너지와 각운동량'],
      ['u7', 'Oscillations', '진동'], ['u8', 'Fluids', '유체']]},
  {key: 'ap2', name: {en: 'AP Physics 2', ko: 'AP Physics 2'}, exam: 'AP',
    blurb: {en: 'Algebra-based thermodynamics, electricity, magnetism, optics and modern physics. Exam in May.', ko: '대수 기반 열역학 · 전기 · 자기 · 광학 · 현대물리. 5월 시험.'},
    syl: [['u9', 'Thermodynamics', '열역학'], ['u10', 'Electric Force, Field, and Potential', '전기력 · 전기장 · 전위'], ['u11', 'Electric Circuits', '전기 회로'],
      ['u12', 'Magnetism and Electromagnetism', '자기와 전자기'], ['u13', 'Geometric Optics', '기하 광학'], ['u14', 'Waves, Sound, and Physical Optics', '파동 · 소리 · 물리 광학'],
      ['u15', 'Modern Physics', '현대물리']]},
  {key: 'apcm', name: {en: 'AP Physics C: Mechanics', ko: 'AP Physics C: 역학'}, exam: 'AP',
    blurb: {en: 'Calculus-based mechanics: variable forces, drag, rotation by integration. Exam in May.', ko: '미적분 기반 역학: 변하는 힘, 저항, 적분으로 구하는 회전. 5월 시험.'},
    syl: [['u1', 'Kinematics', '운동학'], ['u2', 'Force and Translational Dynamics', '힘과 병진 운동'], ['u3', 'Work, Energy, and Power', '일 · 에너지 · 일률'],
      ['u4', 'Linear Momentum', '선운동량'], ['u5', 'Torque and Rotational Dynamics', '토크와 회전 운동'], ['u6', 'Energy and Momentum of Rotating Systems', '회전계의 에너지와 각운동량'],
      ['u7', 'Oscillations', '진동']]},
  {key: 'jeem', name: {en: 'JEE Main', ko: 'JEE Main (인도)'}, exam: 'JEE',
    blurb: {en: 'India’s engineering entrance: single-correct questions and integer answers. Sessions in January and April.', ko: '인도 공대 입시: 단일 정답 객관식과 정수 답. 1월 · 4월 시험.'},
    syl: [['u1', 'Units and Measurements', '단위와 측정'], ['u2', 'Kinematics', '운동학'], ['u3', 'Laws of Motion', '운동 법칙'], ['u4', 'Work, Energy and Power', '일 · 에너지 · 일률'],
      ['u5', 'Rotational Motion', '회전 운동'], ['u6', 'Gravitation', '중력'], ['u7', 'Properties of Solids and Liquids', '고체와 액체의 성질'], ['u8', 'Thermodynamics', '열역학'],
      ['u9', 'Kinetic Theory of Gases', '기체 분자 운동론'], ['u10', 'Oscillations and Waves', '진동과 파동'], ['u11', 'Electrostatics', '정전기'], ['u12', 'Current Electricity', '전류'],
      ['u13', 'Magnetic Effects of Current and Magnetism', '전류의 자기 작용과 자성'], ['u14', 'Electromagnetic Induction and AC', '전자기 유도와 교류'], ['u15', 'Electromagnetic Waves', '전자기파'],
      ['u16', 'Optics', '광학'], ['u17', 'Dual Nature of Matter and Radiation', '물질과 빛의 이중성'], ['u18', 'Atoms and Nuclei', '원자와 핵'], ['u19', 'Electronic Devices', '전자 소자'],
      ['u20', 'Experimental Skills', '실험']]},
  {key: 'fma', name: {en: 'F=ma', ko: 'F=ma (미국 올림피아드 1차)'}, exam: 'USAPhO', choices: 5,
    blurb: {en: 'The first round of the US Physics Olympiad: mechanics only, five options, clever reasoning. Held in late January.', ko: '미국 물리올림피아드 1차: 역학만, 5지선다, 발상이 중요합니다. 1월 말 시험.'},
    syl: [['u1', 'Kinematics', '운동학'], ['u2', 'Dynamics and Friction', '동역학과 마찰'], ['u3', 'Energy and Work', '에너지와 일'], ['u4', 'Momentum and Collisions', '운동량과 충돌'],
      ['u5', 'Rotation and Angular Momentum', '회전과 각운동량'], ['u6', 'Gravitation and Orbits', '중력과 궤도'], ['u7', 'Oscillations', '진동'], ['u8', 'Statics, Fluids and Estimation', '정역학 · 유체 · 어림']]},
  {key: 'usapho', name: {en: 'USAPhO', ko: 'USAPhO (미국 올림피아드 준결선)'}, exam: 'USAPhO',
    blurb: {en: 'The US Physics Olympiad semifinal: long problems across all of physics, here ending in one gradeable result. Held in April.', ko: '미국 물리올림피아드 준결선: 물리 전 범위의 긴 문제를 하나의 답으로 채점하게 바꿨습니다. 4월 시험.'},
    syl: [['u1', 'Mechanics', '역학'], ['u2', 'Rotation and Oscillations', '회전과 진동'], ['u3', 'Thermodynamics and Statistical Physics', '열 · 통계물리'],
      ['u4', 'Electricity and Magnetism', '전자기'], ['u5', 'Waves and Optics', '파동과 광학'], ['u6', 'Modern Physics', '현대물리']]},
];

const units = new Set(P.AREAS.flatMap(a => a.subtopics.map(s => a.key + '/' + s.key)));
const fail = (id, why) => { throw new Error(`${id}: ${why}`); };
const dollars = s => (String(s).replace(/\\\$/g, '').match(/\$/g) || []).length % 2 === 0;
export function validate(track, item) {
  const id = item.id;
  if (!new RegExp(`^${track.key}-u\\d{1,2}-\\d{3}$`).test(id || '')) fail(id, 'bad id');
  if (!track.syl.some(([k]) => k === item.syl)) fail(id, 'bad syl ' + item.syl);
  if (!units.has(item.unit)) fail(id, 'bad unit ' + item.unit);
  if (!(Number.isInteger(item.step) && item.step >= 1 && item.step <= 10)) fail(id, 'bad step');
  if (typeof item.q !== 'string' || !item.q.trim() || item.q.length > 1500) fail(id, 'bad q');
  if (!Array.isArray(item.hints) || item.hints.length < 1 || item.hints.length > 4 || item.hints.some(h => typeof h !== 'string' || !h.trim())) fail(id, 'bad hints');
  if (typeof item.sol !== 'string' || !item.sol.trim()) fail(id, 'bad sol');
  if (item.type === 'mc') {
    const n = track.choices || 4;   /* F=ma has five options, the other exams four */
    if (!Array.isArray(item.choices) || item.choices.length !== n || new Set(item.choices).size !== n) fail(id, 'bad choices');
    if (!(Number.isInteger(item.answer) && item.answer >= 0 && item.answer < n)) fail(id, 'bad answer');
  } else if (item.type === 'num') {
    const a = item.answer;
    if (!a || !Number.isFinite(a.value) || !(a.tol >= 0 && a.tol <= 0.1) || typeof a.unit !== 'string') fail(id, 'bad numeric answer');
    if (a.tol === 0 && !Number.isInteger(a.value)) fail(id, 'exact answer must be an integer');
  } else fail(id, 'bad type');
  for (const t of [item.q, item.sol, ...item.hints, ...(item.choices || [])]) {
    if (!dollars(t)) fail(id, 'unbalanced $');
    if (/\\,\^/.test(t)) fail(id, 'a superscript on \\, does not render');
    if (/\\text\{[^}]*·/.test(t)) fail(id, 'a middle dot inside \\text does not render');
  }
}

export function build() {
  const list = [], files = {};
  for (const t of TRACKS) {
    const file = path.join(root, 'tools/practice/tracks', t.key + '.json');
    if (!fs.existsSync(file)) continue;   /* a track whose problems are still being written and checked */
    const src = JSON.parse(fs.readFileSync(file, 'utf8'));
    if (src.track !== t.key) fail(t.key, 'track key');
    const seen = new Set();
    const items = src.items.map(i => {
      validate(t, i);
      if (seen.has(i.id)) fail(i.id, 'duplicate');
      seen.add(i.id);
      const o = {id: i.id, syl: i.syl, unit: i.unit, step: i.step, type: i.type, q: i.q};
      if (i.type === 'mc') o.choices = i.choices;
      return {...o, answer: i.answer, hints: i.hints, sol: i.sol};
    });
    files[t.key] = JSON.stringify({version: 1, track: t.key, items});
    list.push({key: t.key, exam: t.exam, name: t.name, blurb: t.blurb, n: items.length, steps: [...new Set(items.map(i => i.step))].sort((a, b) => a - b),
      syl: t.syl.map(([key, en, ko]) => ({key, name: {en, ko}, n: items.filter(i => i.syl === key).length})).filter(u => u.n)});
  }
  return {list: JSON.stringify({version: 1, tracks: list}), files};
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const {list, files} = build();
  const outs = [['practice/tracks.json', list], ...Object.entries(files).map(([k, v]) => [`practice/track/${k}.json`, v])];
  if (check) {
    const stale = outs.filter(([f, v]) => !fs.existsSync(path.join(root, f)) || fs.readFileSync(path.join(root, f), 'utf8') !== v).map(([f]) => f);
    if (stale.length) { console.error('stale, run node tools/practice/build-tracks.mjs:', stale.join(' ')); process.exit(1); }
    console.log('tracks up to date');
  } else {
    fs.mkdirSync(path.join(root, 'practice/track'), {recursive: true});
    for (const [f, v] of outs) fs.writeFileSync(path.join(root, f), v);
    console.log(JSON.parse(list).tracks.map(t => `${t.key} ${t.n}`).join(', '));
  }
}
