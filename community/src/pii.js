// Personal details taken out of answer-sheet text before it is used for training or evaluation (HaslaEdu/hasla-ai, rule
// L6: answers only). The upload page asks candidates not to write them; this catches what was written anyway: e-mail
// addresses, phone numbers, resident registration numbers, and the value of a labelled header line (name, school,
// student or candidate code, contact). Physics is left alone: a bare number, a formula or «n: 3» is never touched.
const LABELS = [
  '이름', '성명', '학교', '학교명', '학년', '수험번호', '학번', '생년월일', '연락처', '전화', '전화번호', '휴대폰', '주소', '이메일', '응시번호', '참가번호',
  'name', 'full name', 'student name', 'school', 'student id', 'student code', 'student number', 'candidate no', 'candidate number',
  'candidate code', 'contestant no', 'contestant number', 'contestant code', 'country code', 'e-mail', 'email', 'phone', 'address',
];
const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/ /g, '\\s*');
const LABELLED = new RegExp(`^(\\s*(?:${LABELS.map(esc).join('|')})\\.?\\s*[:：]\\s*)(\\S.*)$`, 'gim');
const EMAIL = /[\w.+-]+@[\w-]+(?:\.[\w-]+)+/g;
const PHONE = /(?:\+\d{1,3}[\s.-]?)?\b0\d{1,2}[\s.-]?\d{3,4}[\s.-]?\d{4}\b|\+\d{1,3}[\s.-]?\d{2,4}[\s.-]?\d{3,4}[\s.-]?\d{3,4}\b/g;
const RRN = /\b\d{6}\s?-\s?[1-8]\d{6}\b/g;

export const REMOVED = '[삭제됨]';
/** the text with personal details replaced by [삭제됨] */
export function scrubPersonal(text) {
  return String(text ?? '')
    .replace(EMAIL, REMOVED)
    .replace(RRN, REMOVED)
    .replace(PHONE, REMOVED)
    .replace(LABELLED, (m, label) => label + REMOVED);
}
