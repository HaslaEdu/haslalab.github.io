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
};

export function getMonthlyAnswerSheet(problem) {
  const id = Number(typeof problem === 'object' && problem !== null ? problem.id : problem);
  const value = sheets[id];
  if (!value) return null;
  return {
    version: MONTHLY_SHEET_VERSION,
    limit: MONTHLY_ANSWER_LIMIT,
    parts: value.parts.map(p => ({...p})),
    pages: value.pages.map(page => [...page]),
  };
}
