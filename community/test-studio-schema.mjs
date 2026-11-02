import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { ensureStudioSchema } from './src/studio-schema.js';

const normalize = sql => sql.replace(/--[^\n]*/g, '').split(';')
  .map(statement => statement.replace(/\s+/g, ' ').trim()).filter(Boolean);

function binding(batch = statements => statements.map(() => ({ success: true }))) {
  const prepared = [];
  const batches = [];
  const DB = {
    prepare(sql) { prepared.push(sql); return { sql }; },
    batch(statements) { batches.push(statements); return Promise.resolve(batch(statements)); },
  };
  return { DB, prepared, batches };
}

test('runtime schema exactly matches the additive migration after SQL normalization', async () => {
  const migration = await readFile(new URL('./migrations/0015_studio.sql', import.meta.url), 'utf8');
  const mock = binding();
  await ensureStudioSchema(mock.DB);
  assert.deepEqual(normalize(mock.prepared.join(';')), normalize(migration));
  assert.equal(mock.batches.length, 1);
  assert.equal(mock.prepared.length, 5);
  for (const sql of mock.prepared) assert.match(sql, /^CREATE (?:TABLE|INDEX) IF NOT EXISTS /);
});

test('concurrent and later calls share one successful initialization per D1 binding', async () => {
  let finish;
  const gate = new Promise(resolve => { finish = resolve; });
  const mock = binding(() => gate);
  const first = ensureStudioSchema(mock.DB);
  const second = ensureStudioSchema(mock.DB);
  assert.equal(first, second);
  await Promise.resolve();
  assert.equal(mock.batches.length, 1);
  assert.equal(ensureStudioSchema(mock.DB), first);
  finish(mock.prepared.map(() => ({ success: true })));
  await Promise.all([first, second]);
  assert.equal(ensureStudioSchema(mock.DB), first);
  await ensureStudioSchema(mock.DB);
  assert.equal(mock.batches.length, 1);
  assert.equal(mock.prepared.length, 5);
});

test('different D1 bindings initialize independently', async () => {
  const first = binding();
  const second = binding();
  await Promise.all([ensureStudioSchema(first.DB), ensureStudioSchema(second.DB)]);
  assert.equal(first.batches.length, 1);
  assert.equal(second.batches.length, 1);
});

test('a rejected batch is shared by concurrent callers and retries on the next call', async () => {
  let attempts = 0;
  const mock = binding(statements => {
    if (++attempts === 1) return Promise.reject(new Error('D1 temporarily unavailable'));
    return statements.map(() => ({ success: true }));
  });
  const first = ensureStudioSchema(mock.DB);
  const second = ensureStudioSchema(mock.DB);
  assert.equal(first, second);
  await assert.rejects(Promise.all([first, second]), /D1 temporarily unavailable/);
  const retry = ensureStudioSchema(mock.DB);
  assert.notEqual(retry, first);
  await retry;
  await ensureStudioSchema(mock.DB);
  assert.equal(attempts, 2);
});

test('synchronous statement preparation failure also clears the cached promise', async () => {
  const mock = binding();
  const prepare = mock.DB.prepare;
  let fail = true;
  mock.DB.prepare = sql => {
    if (fail) { fail = false; throw new Error('prepare failed'); }
    return prepare(sql);
  };
  await assert.rejects(ensureStudioSchema(mock.DB), /prepare failed/);
  await ensureStudioSchema(mock.DB);
  assert.equal(mock.batches.length, 1);
});

test('an unsuccessful batch result is not cached as a successful schema', async () => {
  let attempts = 0;
  const mock = binding(statements => {
    const result = statements.map(() => ({ success: true }));
    if (++attempts === 1) result[0] = { success: false };
    return result;
  });
  await assert.rejects(ensureStudioSchema(mock.DB), /schema initialization failed/);
  await ensureStudioSchema(mock.DB);
  assert.equal(attempts, 2);
});
