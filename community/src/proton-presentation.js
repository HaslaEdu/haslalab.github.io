// Public labels only. The stored a-j keys, rubric and submission history remain
// unchanged; callers apply this to the identified proton-chain problem.
export const PROTON_PART_LABELS = Object.freeze(['A.1','A.2','A.3','A.4','A.5','B.1','B.2','B.3','B.4','B.5']);
const parts = Object.freeze([
  ['정확한 운동방정식과 선형화','Exact equation of motion and linearization',10],
  ['분산관계','Dispersion relation',13],
  ['허용 파수와 최대 각진동수','Allowed wave numbers and maximum frequency',10],
  ['감쇠 구동의 복소진폭','Complex amplitude of the damped driven motion',17],
  ['평균 흡수 일률과 공명','Mean absorbed power and resonance',10],
  ['균일 전기장의 흡수 공명 판정','Absorption resonance for a uniform field',7],
  ['한 모드의 평균 에너지','Mean energy of one mode',10],
  ['파수 구간의 모드 수','Mode count in a wave-number interval',6],
  ['모드 밀도와 전체 진동 에너지','Density of modes and total vibrational energy',7],
  ['고온 몰열용량과 가열 시간','High-temperature molar heat capacity and heating time',10],
]);
const groups = {
  ko:['사슬의 진동과 감쇠 구동','균일 구동과 진동 에너지'],
  en:['Chain oscillations and damped driving','Uniform driving and vibrational energy'],
};
const scoreIntro = /^(?:원문 총 15점 → 웹 채점 100점 기준으로 환산합니다\. 소문항 옆 점수는 원문 배점입니다\.|Original total: 15 points\. Web grading uses a 100-point rubric; the allocations beside the subquestions are the original ones\.)\r?\n\r?\n/u;
const sigma = String.raw`\displaystyle\sum_{k=1}^{\infty}(\cdots)`;

export function presentProtonText(value, field = 'body_ko') {
  if (typeof value !== 'string' || !/^(?:body|model)_(?:ko|en)$/.test(field)) return value;
  const en = field.endsWith('_en'), body = field.startsWith('body_');
  // A maintained or already-formatted statement without legacy headings is
  // left intact. This also makes repeated public projections idempotent.
  if (!/^#{2,3}\s+\([a-j]\)\s+/m.test(value)) return value;
  let text = body ? value.replace(scoreIntro, '') : value;
  if (body) {
    text = text.replace(String.raw`이웃 합은 $\sum_{k=1}^{\infty}(\cdots)$로 표시하여라.`,
      () => `이웃에 대한 합은 다음 형식으로 표시하라.\n$$${sigma}$$`);
    text = text.replace(String.raw`Leave the neighbour sum in the form $\sum_{k=1}^{\infty}(\cdots)$.`,
      () => `Express the neighbour sum in the following form:\n$$${sigma}$$`);
  }
  // Do not rewrite expressions such as f(a), x(d), or parenthesized LaTeX
  // symbols. Only prose references and legacy section headings change.
  return text.split(/(\$\$[\s\S]*?\$\$|\$[^$\n]+\$)/g).map(block => {
    if (block.startsWith('$') && block.endsWith('$')) return block;
    return block.replace(/^#{2,3}\s+\(([a-j])\)\s+[^\r\n]+/gm, (_, old) => {
      const index = old.charCodeAt(0)-97, label = PROTON_PART_LABELS[index];
      let heading = `### ${label} ${parts[index][en ? 1 : 0]}`;
      if (body) heading += en ? ` (${parts[index][2]} points)` : ` (${parts[index][2]}점)`;
      if (index === 0 || index === 5) {
        const group = index === 0 ? 0 : 1;
        const points = group === 0 ? 60 : 40;
        heading = `## Part ${group === 0 ? 'A' : 'B'}. ${groups[en ? 'en' : 'ko'][group]}` +
          (body ? en ? ` (${points} points)` : ` (${points}점)` : '') + '\n\n' + heading;
      }
      return heading;
    }).replace(/(?<![\p{L}\p{N}_])\(([a-j])\)/gu, (_, old) => PROTON_PART_LABELS[old.charCodeAt(0)-97])
      .replace(/\b([AB]\.[13])를/g, '$1을');
  }).join('');
}
