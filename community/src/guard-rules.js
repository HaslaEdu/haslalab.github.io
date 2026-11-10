// The answer-injection rules the Worker uses in production are private (HaslaEdu/haslalab-server, guard/guard-rules.js):
// the deploy (.github/workflows/deploy-worker.yml) copies them over this file before testing and deploying. What is here
// is an older public set, enough for local development and the public tests. Keep the exports identical.
export const PRIVATE = false;
export const GUARD_VERSION = 'public-stub';
/** the text the rules read */
export function normalize(text) { return String(text ?? '').normalize('NFKC'); }
/* [rule, pattern] */
export const RULES = [
  // the prompts' own fences and headers, written into an answer
  ['fence', /<<\s*(?:END|ANSWER|SCHEME|OCR|PDF_TEXT|ANALYSIS|TRANSCRIPT|STEPS|PAGES|SECOND TRANSCRIPT|END SECOND TRANSCRIPT)\b[^>\n]{0,40}>>/i],
  ['header', /^[ \t]*\[(?:TASK:\s*(?:grade|build marking scheme|review)|End of fixed rules|Rubric|Marking scheme[^\]\n]{0,40}|Private session reference[^\]\n]{0,40})\][ \t]*$/im],
  ['role', /<\|(?:im_start|im_end|system|start_header_id|end_header_id)\|>|^[ \t]*(?:system|assistant|developer)\s*:\s*(?:you|ignore|grade|award|give)\b/im],
  // instructions to the grader
  ['instruction', /\b(?:ignore|disregard|forget|override)\s+(?:all\s+|any\s+|the\s+|your\s+)?(?:previous|prior|above|earlier|preceding|grading|marking|system)\s+(?:instructions?|rules?|prompts?|rubric|scheme|criteria)\b/i],
  ['instruction', /\b(?:give|award|assign|grant)\s+(?:me\s+|this\s+(?:answer|solution|student)\s+|the\s+student\s+)?(?:full|maximum|max|all(?:\s+the)?|perfect|100\s*%)\s+(?:marks?|points?|score|credit)\b/i],
  ['instruction', /\byou\s+(?:are|must|will|should)\s+(?:now\s+)?(?:give|award|grade\s+this\s+as|mark\s+this\s+as|output|return)\b[^.\n]{0,40}\b(?:full|maximum|correct|10\s*\/\s*10|100\s*%)/i],
  ['instruction', /(?:이전|앞의|위의|기존|모든)\s*(?:지시|지침|명령|규칙|채점\s*기준|프롬프트)\S{0,3}\s*(?:무시|잊어|따르지\s*마)/],
  ['instruction', /(?:채점\s*(?:기준|규칙|지침)\S{0,3}\s*무시|만점\s*(?:을|으로)?\s*(?:줘|주세요|주시오|처리|부여|매겨)|점수\s*를?\s*(?:만점|최고점|10\s*점)\s*(?:으로|을)?\s*(?:줘|주세요|처리|부여|매겨))/],
];
