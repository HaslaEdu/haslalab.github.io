import { getMonthlyAnswerSheet } from '../../monthly-problems.mjs';

// Keep the supplied source records intact for grading and administration. Only
// the public presentation of these monthly answer-sheet problems omits credits.
const creditFooter = /\r?\n\r?\n(?:출처: 제공된 xPhO 2026 주 1 문제 사진,[^\r\n]*|Source: supplied photographs of xPhO 2026 Week 1,[^\r\n]*)\s*$/u;
const textFields = ['body_ko', 'body_en', 'model_ko', 'model_en'];

export function monthlyPublicPresentation(problem) {
  if (!getMonthlyAnswerSheet(problem)) return problem;
  const publicProblem = { ...problem, source: null };
  for (const field of textFields) {
    if (typeof problem[field] === 'string') publicProblem[field] = problem[field].replace(creditFooter, '');
  }
  return publicProblem;
}
