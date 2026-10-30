// Validate reviewed source before deploying the Worker that bundles it.
// Usage: node weekly/build-seed.mjs --check
// Values are bound through D1 batch(), rather than embedded in a SQL file:
// this keeps long bilingual solutions below the SQL-statement length limit.
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { validateContent } from '../src/weekly-content.js';

export { validateContent } from '../src/weekly-content.js';

export function validateReviewedSources() {
  const load = name => validateContent(JSON.parse(readFileSync(new URL(name,import.meta.url),'utf8')));
  return {
    publications: ['./2026-W44.json','./2026-11-greenhouse-part-d.json'].map(load),
    revisions: ['./2026-11-astronomy-revision.json'].map(load),
  };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);
  if (args.some(arg => arg !== '--check')) throw new Error('Usage: node weekly/build-seed.mjs --check');
  const {publications,revisions} = validateReviewedSources();
  console.log(`Reviewed content verified: ${publications.reduce((sum,content)=>sum+content.problems.length,0)} problems in ${publications.length} independent publications; ${revisions.length} editorial revision; atomic D1 binding publication`);
}
