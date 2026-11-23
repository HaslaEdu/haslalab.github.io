import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {MONTHLY_RUBRICS, monthlyRubric} from './src/monthly-rubrics.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const weekly = path.join(here, 'weekly');

test('every hand-built monthly rubric is bundled into the Worker', () => {
  for (const dir of fs.readdirSync(weekly).filter(d => /^rubrics-\d{4}-\d{2}$/.test(d))) {
    const week = dir.slice('rubrics-'.length);
    for (const f of fs.readdirSync(path.join(weekly, dir)).filter(f => /^\d+\.json$/.test(f))) {
      const id = Number(f.slice(0, -5));
      assert.deepEqual(monthlyRubric(week, id), JSON.parse(fs.readFileSync(path.join(weekly, dir, f), 'utf8')), `${dir}/${f}`);
    }
  }
  assert.equal(monthlyRubric('2026-11', 999), null);
});

test('the site build does not publish community/ (private rubrics and solutions)', () => {
  const pages = fs.readFileSync(path.join(here, '../.github/workflows/pages.yml'), 'utf8');
  assert.doesNotMatch(pages, /--include '\/community\/weekly/);
  assert.match(pages, /--exclude \/community\//);
  assert.ok(Object.keys(MONTHLY_RUBRICS).length > 0);
});
