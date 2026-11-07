// Personal details are taken out of answer-sheet and chat text before training or evaluation (HaslaEdu/hasla-ai, L6).
import test from 'node:test';
import assert from 'node:assert/strict';
import { scrubPersonal, REMOVED } from './src/pii.js';
import { gradeTrainInput } from './src/lab-train.js';
import { trainingLine } from './src/ai-eval.js';

test('names, schools, codes and contacts written on a sheet are removed', () => {
  assert.equal(scrubPersonal('이름: 홍길동\n학교 : 서울과학고\n수험번호: 1234'), `이름: ${REMOVED}\n학교 : ${REMOVED}\n수험번호: ${REMOVED}`);
  assert.equal(scrubPersonal('Name: Kim Minsu\nStudent code: KOR-3\nCountry code: KOR'), `Name: ${REMOVED}\nStudent code: ${REMOVED}\nCountry code: ${REMOVED}`);
  assert.equal(scrubPersonal('연락처 010-1234-5678, kim@school.kr'), `연락처 ${REMOVED}, ${REMOVED}`);
  assert.equal(scrubPersonal('950101-1234567'), REMOVED);
  assert.equal(scrubPersonal('call +82 10 1234 5678'), `call ${REMOVED}`);
});

test('physics stays as it is', () => {
  for (const t of ['$E = mc^2$', 't: 3 s\nn: 1.33\n0.0123 kg', 'x = 0.25 m, q = 1.6e-19 C, N_A = 6.02 × 10^23', 'P = 101325 Pa, T = 300 K',
    'A.1: v = \\sqrt{2gh}', '(b) 2.0 × 10^-3 s', 'Final answer (B.2): 0.42 m'])
    assert.equal(scrubPersonal(t), t);
});

test('the grading training input and the chat training line carry no personal details', () => {
  const input = gradeTrainInput({items: [{id: 'A.1', points: 1, what: 'speed'}]}, [{no: 1, kind: 'answer', ocr: '이름: 홍길동\nv = 3 m/s'}], {task: 'T1', exam: 'ipho2016'});
  assert.ok(!input.includes('홍길동') && input.includes('v = 3 m/s'));
  const line = JSON.parse(trainingLine({question: '제 이메일은 a@b.com 이에요. 1+1은?', answer: '2', context: JSON.stringify([{role: 'user', content: '연락처: 010-1111-2222'}])}));
  assert.ok(!JSON.stringify(line).includes('a@b.com') && !JSON.stringify(line).includes('010-1111-2222'));
  assert.equal(line.messages.at(-1).content, '2');
});
