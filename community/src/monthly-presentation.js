import { getMonthlyAnswerSheet } from '../../monthly-problems.mjs';

// Keep the supplied source records intact for grading and administration. Only
// the public presentation omits credits and the proton-chain score-conversion introduction.
const creditFooter = /\r?\n\r?\n(?:출처: 제공된 xPhO 2026 주 1 문제 사진,[^\r\n]*|Source: supplied photographs of xPhO 2026 Week 1,[^\r\n]*)\s*$/u;
const protonScoreIntro = /^(?:원문 총 15점 → 웹 채점 100점 기준으로 환산합니다\. 소문항 옆 점수는 원문 배점입니다\.|Original total: 15 points\. Web grading uses a 100-point rubric; the allocations beside the subquestions are the original ones\.)\r?\n\r?\n/u;
const textFields = ['body_ko', 'body_en', 'model_ko', 'model_en'];

export function monthlyPublicPresentation(problem) {
  if (!getMonthlyAnswerSheet(problem)) return problem;
  const publicProblem = { ...problem, source: null };
  for (const field of textFields) {
    if (typeof problem[field] === 'string') {
      let text = problem[field].replace(creditFooter, '');
      if (Number(problem.id) === 4 && field.startsWith('body_')) text = text.replace(protonScoreIntro, '');
      publicProblem[field] = text;
    }
  }
  return publicProblem;
}
