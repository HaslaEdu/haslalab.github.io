// Validate the hand-built November 2026 rubrics against the live answer-sheet
// definitions and the Worker's own per-part evidence guard.
//   node community/weekly/rubrics-2026-11/validate.mjs
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { getMonthlyAnswerSheet } from '../../../monthly-problems.mjs';
import { guardMonthlyGrade } from '../../src/monthly-answers.js';

const here = dirname(fileURLToPath(import.meta.url));
// Stored identities that getMonthlyAnswerSheet resolves (7 and 8 are matched by
// period/number/title, not by database id).
const problems = {
  4: { id: 4, week: '2026-11', no: 1, points: 100, title_ko: '양성자 사슬의 진동과 에너지' },
  5: { id: 5, week: '2026-11', no: 2, points: 100, title_ko: '연속 벽과 자유 표적의 충돌' },
  6: { id: 6, week: '2026-11', no: 3, points: 100, title_ko: '굴절률장에서의 러더퍼드 산란' },
  7: { id: 7, week: '2026-11', no: 4, points: 100, title_ko: '원판 모형의 복사 평형과 세차' },
  8: { id: 8, week: '2026-11', no: 5, points: 100, title_ko: '압력파를 이용한 관의 내부 지름 측정' },
};
// The part each criterion is meant for, declared independently of the Worker code.
const intended = {
  4: id => id.split('.')[0],
  5: id => id[0],
  6: id => id.slice(0, 3),
  7: id => id.split('.')[0],
  8: id => id.slice(0, 3),
};

let failures = 0;
const fail = (pid, msg) => { failures++; console.log(`  FAIL [${pid}] ${msg}`); };

for (const pid of Object.keys(problems)) {
  const file = join(here, `${pid}.json`);
  let rubric;
  try { rubric = JSON.parse(readFileSync(file, 'utf8')); }
  catch (e) { fail(pid, `invalid JSON: ${e.message}`); continue; }
  const problem = problems[pid];
  const sheet = getMonthlyAnswerSheet(problem);
  if (!sheet) { fail(pid, 'no answer sheet resolved'); continue; }
  console.log(`Problem ${pid}: ${rubric.length} criteria, sheet ${sheet.key || '(no key)'} with ${sheet.parts.length} parts`);

  if (!Array.isArray(rubric) || !rubric.length) { fail(pid, 'rubric is not a non-empty array'); continue; }
  const ids = new Set();
  for (const c of rubric) {
    const keys = Object.keys(c).sort().join(',');
    if (keys !== 'id,max,name,partial,requirement') fail(pid, `${c.id}: keys ${keys}`);
    for (const k of ['id', 'name', 'requirement', 'partial']) if (typeof c[k] !== 'string' || !c[k].trim()) fail(pid, `${c.id}: empty ${k}`);
    if (ids.has(c.id)) fail(pid, `duplicate id ${c.id}`); ids.add(c.id);
    if (!Number.isInteger(c.max) || c.max <= 0) fail(pid, `${c.id}: max ${c.max} is not a positive integer`);
    const halves = c.name.split(' / ');
    if (halves.length !== 2 || !/[가-힣]/.test(halves[0]) || !/^[A-Za-z]/.test(halves[1]) || /[가-힣]/.test(halves[1]))
      fail(pid, `${c.id}: name not "한국어 / English": ${c.name}`);
    if (c.requirement.length > 600) fail(pid, `${c.id}: requirement ${c.requirement.length} chars > 600`);
  }
  const total = rubric.reduce((s, c) => s + c.max, 0);
  if (total !== 100 || total !== problem.points) fail(pid, `total ${total}`);
  const sheetTotal = sheet.parts.reduce((s, p) => s + p.points, 0);
  if (sheetTotal !== 100) fail(pid, `sheet parts total ${sheetTotal}`);

  // Per-part sums against the public answer sheet.
  const byPart = new Map(sheet.parts.map(p => [p.id, 0]));
  for (const c of rubric) {
    const part = intended[pid](c.id);
    if (!byPart.has(part)) { fail(pid, `${c.id}: intended part ${part} is not on the sheet`); continue; }
    byPart.set(part, byPart.get(part) + c.max);
  }
  for (const p of sheet.parts) if (byPart.get(p.id) !== p.points) fail(pid, `part ${p.id}: criteria sum ${byPart.get(p.id)} != sheet ${p.points}`);
  console.log('  parts: ' + sheet.parts.map(p => `${p.id}=${byPart.get(p.id)}/${p.points}`).join(' '));

  // Prefix rule, using the Worker's guard. Each criterion's evidence marker is
  // written in exactly one part's working; the guard must keep the points only
  // when that part is the criterion's own part.
  const runGuard = place => {
    const text = new Map(sheet.parts.map(p => [p.id, []]));
    for (const c of rubric) text.get(place(c)).push(`EVIDENCE<${c.id}>`);
    const normalized = { sheet: { parts: sheet.parts.map(p => ({ id: p.id, answer: `answer ${p.id}`, working: text.get(p.id).join('\n') || 'blank' })) } };
    const grade = { score: 100, detail: { evidenceIssue: false, feedback: [],
      scores: rubric.map(c => ({ id: c.id, name: c.name, max: c.max, got: c.max, decision: 'met', note: '', evidence: [`EVIDENCE<${c.id}>`] })) } };
    return guardMonthlyGrade(grade, problem, normalized, 'en');
  };
  const own = runGuard(c => intended[pid](c.id));
  for (const s of own.detail.scores) if (s.got !== s.max) fail(pid, `${s.id}: own-part evidence rejected by guard`);
  if (own.score !== 100) fail(pid, `guard score with own-part evidence ${own.score}`);
  const order = sheet.parts.map(p => p.id);
  for (let shift = 1; shift < order.length; shift++) {
    const other = runGuard(c => order[(order.indexOf(intended[pid](c.id)) + shift) % order.length]);
    for (const s of other.detail.scores) if (s.got !== 0) fail(pid, `${s.id}: guard accepted evidence from another part (shift ${shift})`);
  }
  console.log(`  guard: own-part score ${own.score}; cross-part evidence rejected for all ${order.length - 1} shifts`);
}
console.log(failures ? `\n${failures} failure(s)` : '\nAll checks passed.');
process.exit(failures ? 1 : 0);
