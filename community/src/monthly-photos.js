import { getMonthlyAnswerSheet } from '../../monthly-problems.mjs';
import { MonthlyAnswerError } from './monthly-answers.js';

const MAX_IMAGE = 4 * 1024 * 1024, CHUNK = 512 * 1024;
const MAX_PHOTOS = 40, MAX_STORED = 96 * 1024 * 1024;
export const MONTHLY_MAX_OCR_BYTES = 256 * 1024;
const ID = /^[a-f0-9-]{36}$/;
const ready = new WeakMap();
const fail = (code, status = 400) => { throw new MonthlyAnswerError(code, status); };

// Monthly submissions deliberately do not use the timed IPhO photo purge.
// Chunking keeps each D1 row below its individual row-size limit.
export function ensureMonthlyPhotoSchema(db, key = db) {
  let promise = ready.get(key);
  if (!promise) {
    promise = db.batch([
      db.prepare(`CREATE TABLE IF NOT EXISTS monthly_answer_photos (
        id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, problem_id INTEGER NOT NULL,
        part_id TEXT NOT NULL, mime TEXT NOT NULL, bytes INTEGER NOT NULL,
        ocr_text TEXT NOT NULL, created_at INTEGER NOT NULL
      )`),
      db.prepare(`CREATE TABLE IF NOT EXISTS monthly_answer_photo_chunks (
        photo_id TEXT NOT NULL, no INTEGER NOT NULL, data BLOB NOT NULL,
        PRIMARY KEY(photo_id,no)
      )`),
    ]).then(() => db.prepare('CREATE INDEX IF NOT EXISTS monthly_photos_owner ON monthly_answer_photos(user_id,problem_id)').run()).then(() => true);
    ready.set(key, promise);
    promise.catch(() => { if (ready.get(key) === promise) ready.delete(key); });
  }
  return promise;
}

// Capture uploads may supply a trusted server-only SQL guard and follow-up statements.
// Original bytes, page association, revision and idempotent receipt then commit together.
export async function storePhoto(db, { userId, problemId, partId, mime, data, transcript, timestamp, authorization, afterInsert }) {
  const id = crypto.randomUUID(), statements = [db.prepare(`INSERT INTO monthly_answer_photos
    (id,user_id,problem_id,part_id,mime,bytes,ocr_text,created_at)
    SELECT ?,?,?,?,?,?,?,? WHERE EXISTS(SELECT 1 FROM users WHERE id=? AND deleted=0)
      AND (SELECT COUNT(*) FROM monthly_answer_photos WHERE user_id=? AND problem_id=?)<?
      AND (SELECT COALESCE(SUM(bytes),0) FROM monthly_answer_photos WHERE user_id=? AND problem_id=?)+?<=?
      ${authorization ? `AND (${authorization.sql})` : ''}`)
    .bind(id,userId,problemId,partId,mime,data.byteLength,transcript,timestamp,
      userId,userId,problemId,MAX_PHOTOS,userId,problemId,data.byteLength,MAX_STORED,...(authorization?.args || []))];
  for (let offset = 0, no = 0; offset < data.byteLength; offset += CHUNK, no++) {
    statements.push(db.prepare(`INSERT INTO monthly_answer_photo_chunks(photo_id,no,data)
      SELECT ?,?,? WHERE EXISTS(SELECT 1 FROM monthly_answer_photos WHERE id=?)`)
      .bind(id,no,data.slice(offset,offset+CHUNK).buffer,id));
  }
  if (afterInsert) statements.push(...afterInsert(id));
  const result = await db.batch(statements);
  if (!result[0].meta?.changes) {
    const owner = await db.prepare('SELECT deleted FROM users WHERE id=?').bind(userId).first();
    if (!owner || owner.deleted) fail('login_required',401);
    if (authorization && !await db.prepare(`SELECT 1 AS authorized WHERE ${authorization.sql}`).bind(...authorization.args).first()) fail('scan_over',409);
    fail('monthly_photo_storage_full', 413);
  }
  return { id, part_id: partId, mime, bytes: data.byteLength };
}

function photoIds(value) {
  if (value === undefined) return [];
  if (!Array.isArray(value) || value.length > MAX_PHOTOS || value.some(id => typeof id !== 'string' || !ID.test(id))) fail('bad_photo_ids');
  return [...new Set(value)].sort();
}

async function ownedPhotos(db, userId, problemId, ids) {
  if (!ids.length) return [];
  const rows = (await db.prepare(`SELECT id,part_id,mime,bytes,ocr_text FROM monthly_answer_photos
    WHERE user_id=? AND problem_id=? AND id IN (${ids.map(() => '?').join(',')})`)
    .bind(userId,problemId,...ids).all()).results;
  if (rows.length !== ids.length) fail('bad_photo_ids');
  return rows;
}

// Whitespace and common LaTeX delimiters may change during the OCR correction UI.
// Any other typed addition remains eligible for the authorship screen. A photograph
// itself is not proof of human authorship, and a client via_ocr flag is never trusted.
const comparable = text => String(text || '').normalize('NFKC').replace(/\\[()[\]]|\$|\s/g, '');
export async function prepareMonthlyPhotoSubmission(db, userId, problem, normalized, value) {
  normalized.viaOcr = 0;
  normalized.photographedPartIds = [];
  const ids = photoIds(value);
  if (ids.length) {
    await ensureMonthlyPhotoSchema(db);
    const photos = await ownedPhotos(db,userId,problem.id,ids);
    const parts = new Set(normalized.sheet.parts.map(part => part.id));
    if (photos.some(photo => !parts.has(photo.part_id))) fail('bad_photo_ids');
    normalized.viaOcr = 1;
    normalized.photographedPartIds = normalized.sheet.parts.filter(part => {
      const transcript = comparable(photos.filter(photo => photo.part_id === part.id).map(photo => photo.ocr_text).join('\n'));
      const answer = comparable(part.answer), working = comparable(part.working);
      return answer && working && transcript.includes(answer) && transcript.includes(working);
    }).map(part => part.id);
  }
  // Omit empty attachments for compatibility with previously accepted request IDs.
  if (ids.length) normalized.sheet.photo_ids = ids;
  normalized.serialized = JSON.stringify(normalized.sheet);
}

export async function monthlyPhotoAttachments(db, userId, problemId, value) {
  const ids = photoIds(value);
  if (!ids.length) return [];
  await ensureMonthlyPhotoSchema(db);
  return (await ownedPhotos(db,userId,problemId,ids)).map(({ id,part_id,mime,bytes }) => ({ id,part_id,mime,bytes }));
}

export async function deleteMonthlyPhotos(db, userId, key = db) {
  await ensureMonthlyPhotoSchema(db,key);
  await db.batch(monthlyPhotoDeletion(db,userId));
}
export function monthlyPhotoDeletion(db,userId) {
  return [
    db.prepare('DELETE FROM monthly_answer_photo_chunks WHERE photo_id IN (SELECT id FROM monthly_answer_photos WHERE user_id=?)').bind(userId),
    db.prepare('DELETE FROM monthly_answer_photos WHERE user_id=?').bind(userId),
  ];
}

export async function boundedForm(req, HttpError) {
  if (!/^multipart\/form-data\s*;/i.test(req.headers.get('Content-Type') || '')) throw new HttpError(400,'bad_image');
  const maximum = 2*MAX_IMAGE+16384;
  if (Number(req.headers.get('Content-Length')) > maximum) throw new HttpError(413,'image_too_big');
  const reader = req.body?.getReader();
  if (!reader) throw new HttpError(400,'bad_image');
  const chunks = []; let length = 0;
  for (;;) {
    const {value,done} = await reader.read(); if (done) break;
    length += value.byteLength;
    if (length > maximum) { await reader.cancel(); throw new HttpError(413,'image_too_big'); }
    chunks.push(value);
  }
  const data = new Uint8Array(length); let offset = 0;
  for (const chunk of chunks) { data.set(chunk,offset); offset += chunk.length; }
  try { return await new Response(data,{headers:{'Content-Type':req.headers.get('Content-Type') || ''}}).formData(); }
  catch { throw new HttpError(400,'bad_image'); }
}

export function createMonthlyPhotoRouter({ HttpError, needUser, ensureContent, visibleSql, attempts, limit, ocr, imageType, scope }) {
  return async function monthlyPhotoRoute(path, method, me, req, env, url) {
    let match;
    if ((match = /^\/api\/monthly\/photos\/([a-f0-9-]{36})$/.exec(path)) && method === 'GET') {
      needUser(me);
      await ensureMonthlyPhotoSchema(env.DB,scope(env));
      const row = await env.DB.prepare('SELECT user_id,mime,bytes FROM monthly_answer_photos WHERE id=?').bind(match[1]).first();
      if (!row || row.user_id !== me.id && me.role !== 'admin') throw new HttpError(404,'not_found');
      const chunks = (await env.DB.prepare('SELECT data FROM monthly_answer_photo_chunks WHERE photo_id=? ORDER BY no').bind(match[1]).all()).results;
      const data = new Uint8Array(row.bytes); let offset = 0;
      for (const chunk of chunks) { const bytes = new Uint8Array(chunk.data); data.set(bytes,offset); offset += bytes.length; }
      if (offset !== row.bytes) throw new HttpError(500,'photo_unavailable');
      return new Response(data, { headers: { 'Content-Type':row.mime, 'Content-Length':String(row.bytes),
        'Cache-Control':'private, no-store', 'X-Content-Type-Options':'nosniff',
        'Content-Security-Policy':"default-src 'none'", 'Referrer-Policy':'no-referrer' } });
    }
    if (!(match = /^\/api\/monthly\/problems\/(\d+)\/photos$/.exec(path)) || method !== 'POST') return undefined;
    needUser(me);
    await ensureContent(env.DB,scope(env));
    const problem = await env.DB.prepare(`SELECT p.* FROM problems p WHERE p.id=? AND ${visibleSql('p')}`).bind(+match[1]).first();
    const sheet = problem && getMonthlyAnswerSheet(problem);
    if (!sheet || problem.opens_at > Math.floor(Date.now()/1000)) throw new HttpError(404,'not_found');
    const remaining = await attempts(env.DB,problem.id,me.id);
    if (!remaining.remaining) throw new HttpError(409,'attempts_exhausted',{attempts:remaining});
    if (!env.UPSTAGE_API_KEY) throw new HttpError(503,'ocr_off');
    // A bounded multipart payload includes both the scanner result and its original.
    const form = await boundedForm(req,HttpError);
    const image = form.get('image'), original = form.get('original_image') || image, partId = form.get('part_id');
    if (!sheet.parts.some(part => part.id === partId)) throw new HttpError(400,'bad_answer_sheet');
    for (const file of [image,original]) {
      if (!file || typeof file === 'string' || !file.size) throw new HttpError(400,'bad_image');
      if (file.size > MAX_IMAGE) throw new HttpError(413,'image_too_big');
      if (!imageType(new Uint8Array(await file.slice(0,16).arrayBuffer()))) throw new HttpError(415,'bad_image');
    }
    await ensureMonthlyPhotoSchema(env.DB,scope(env));
    const usage = await env.DB.prepare('SELECT COUNT(*) n,COALESCE(SUM(bytes),0) bytes FROM monthly_answer_photos WHERE user_id=? AND problem_id=?').bind(me.id,problem.id).first();
    if (usage.n >= MAX_PHOTOS || usage.bytes + original.size > MAX_STORED) throw new HttpError(413,'monthly_photo_storage_full');
    await limit(env,'ocr:'+me.id,30,86400);
    const result = await ocr(env,image,url.searchParams.get('mode') === 'math' ? 'math' : 'text');
    if (typeof result.text !== 'string' || !result.text.trim()) throw new HttpError(422,'ocr_empty');
    if (new TextEncoder().encode(result.text).byteLength > MONTHLY_MAX_OCR_BYTES) throw new HttpError(413,'ocr_too_big');
    const data = new Uint8Array(await original.arrayBuffer()), mime = imageType(data);
    try {
      const saved = await storePhoto(env.DB,{userId:me.id,problemId:problem.id,partId,mime,data,
        transcript:result.text,timestamp:Math.floor(Date.now()/1000)});
      return {...result,photo_id:saved.id,part_id:saved.part_id,mime:saved.mime,bytes:saved.bytes};
    } catch (error) {
      if (error instanceof MonthlyAnswerError) throw new HttpError(error.status,error.code);
      throw error;
    }
  };
}
