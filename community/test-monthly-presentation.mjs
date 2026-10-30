import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { monthlyPublicPresentation } from './src/monthly-presentation.js';

const content = JSON.parse(readFileSync(new URL('./weekly/2026-W44.json', import.meta.url), 'utf8'));
const rows = content.problems.map(problem => ({ ...problem, id: problem.no }));
const koCredit = '출처: 제공된 xPhO 2026 주 1 문제 사진, 문항 1 (Carina). 한국어 번역·웹 편집 및 채점 기준: HaslaLab. 원문 사진의 정규화 조건을 위와 같이 정정하였다.';
const enCredit = 'Source: supplied photographs of xPhO 2026 Week 1, problem 1, by Carina. Translation, web editing and marking scheme: HaslaLab. The normalization typo is corrected above.';

test('public monthly credits are removed without altering supplied problem records or mathematical corrections', () => {
  for (const row of rows) {
    const original = structuredClone(row), published = monthlyPublicPresentation(row);
    assert.equal(published.source, null);
    assert.deepEqual(row, original, 'stored provenance and original content remain intact');
    assert.equal(published.title_ko, row.title_ko);
    assert.equal(published.title_en, row.title_en);
    assert.equal(published.rubric, row.rubric, 'the private rubric is not rewritten');
    if (row.id === 4) {
      for (const field of ['body_ko', 'body_en']) {
        assert.equal(published[field], row[field].slice(row[field].indexOf('\n\n') + 2), 'only the introductory score-conversion paragraph is omitted');
        assert.doesNotMatch(published[field], /원문 총 15점|Original total: 15 points/);
      }
      for (const field of ['model_ko', 'model_en']) assert.equal(published[field], row[field]);
      assert.equal(published.points, 100);
      assert.equal(published.rubric.reduce((sum, criterion) => sum + criterion.max, 0), 100);
      continue;
    }
    if (row.id !== 6) {
      for (const field of ['body_ko', 'body_en', 'model_ko', 'model_en']) assert.equal(published[field], row[field]);
      continue;
    }
    assert.equal(published.body_ko, row.body_ko.replace('\n\n' + koCredit, ''));
    assert.equal(published.body_en, row.body_en.replace('\n\n' + enCredit, ''));
    assert.ok(published.body_ko.includes('표기 정정: 제공된 사진의 식 (2)'));
    assert.ok(published.body_en.includes('Correction: the supplied photograph states'));
    assert.ok(published.body_ko.includes('B.4 (10점)'));
    assert.ok(published.body_en.includes('B.4 (10 points)'));
    assert.equal(published.model_ko, row.model_ko);
    assert.equal(published.model_en, row.model_en);
  }
});

test('proton introduction removal handles already-published rows without trimming maintained text or mathematical content', () => {
  const proton = rows[0], preserved = proton.body_en.slice(proton.body_en.indexOf('\n\n') + 2);
  assert.equal(monthlyPublicPresentation(proton).body_en, preserved);
  const crlf = { ...proton, body_en: proton.body_en.replaceAll('\n', '\r\n') };
  assert.equal(monthlyPublicPresentation(crlf).body_en, preserved.replaceAll('\n', '\r\n'));
  const maintained = 'A separately maintained introduction.\n\n' + proton.body_en;
  assert.equal(monthlyPublicPresentation({ ...proton, body_en: maintained }).body_en, maintained, 'an internal discussion is not removed');
  for (const id of [1, 7, 99]) {
    const unrelated = { ...proton, id };
    assert.equal(monthlyPublicPresentation(unrelated), unrelated);
  }
});

test('the same trailing credit is omitted from released solutions while other source discussions remain', () => {
  const row = { ...rows[2], model_ko: '정규화 조건과 정답은 보존한다.\n\n' + koCredit,
    model_en: 'Preserve the normalization condition and answer.\n\n' + enCredit + '\n' };
  const published = monthlyPublicPresentation(row);
  assert.equal(published.model_ko, '정규화 조건과 정답은 보존한다.');
  assert.equal(published.model_en, 'Preserve the normalization condition and answer.');
  const discussion = 'Discuss the source example here.\n\n' + enCredit + '\n\nA further mathematical condition follows.';
  assert.equal(monthlyPublicPresentation({ ...row, body_en: discussion }).body_en, discussion,
    'a source mention inside the actual problem text is not an expendable footer');
  const maintained = '## Reference\nSource: a separately maintained mathematical source.';
  assert.equal(monthlyPublicPresentation({ ...row, model_en: maintained }).model_en, maintained);
});

test('unrelated and historical problems retain their original source metadata and content', () => {
  for (const id of [1, 2, 3, 7, 99]) {
    const row = { ...rows[2], id, source: 'Independent source attribution' };
    assert.equal(monthlyPublicPresentation(row), row);
    assert.ok(row.body_en.endsWith(enCredit));
  }
});
