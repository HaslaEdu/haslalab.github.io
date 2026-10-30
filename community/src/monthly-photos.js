import { getMonthlyAnswerSheet } from '../../monthly-problems.mjs';
import { MonthlyAnswerError } from './monthly-answers.js';

const MAX_IMAGE = 4 * 1024 * 1024, CHUNK = 512 * 1024;
const MAX_PHOTOS = 40, MAX_STORED = 96 * 1024 * 1024;
const SCAN_SECONDS = 20 * 60, SCAN_PAGE = 10;
const SCAN_UPLOAD_STALE = 5 * 60, MAX_SCAN_REQUESTS = 80;
const MAX_OCR_BYTES = 256 * 1024;
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
      db.prepare(`CREATE TABLE IF NOT EXISTS monthly_scan_sessions (
        id TEXT PRIMARY KEY, token_hash TEXT NOT NULL UNIQUE, user_id INTEGER NOT NULL,
        problem_id INTEGER NOT NULL, part_id TEXT NOT NULL, attempts_used INTEGER NOT NULL,
        created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL, revoked_at INTEGER
      )`),
      db.prepare(`CREATE TABLE IF NOT EXISTS monthly_scan_photos (
        seq INTEGER PRIMARY KEY AUTOINCREMENT, scan_id TEXT NOT NULL, photo_id TEXT NOT NULL UNIQUE
      )`),
      db.prepare(`CREATE TABLE IF NOT EXISTS monthly_scan_uploads (
        scan_id TEXT NOT NULL, request_id TEXT NOT NULL, payload_hash TEXT NOT NULL,
        claim TEXT NOT NULL, photo_id TEXT, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
        PRIMARY KEY(scan_id,request_id)
      )`),
    ]).then(() => db.batch([
      db.prepare('CREATE INDEX IF NOT EXISTS monthly_photos_owner ON monthly_answer_photos(user_id,problem_id)'),
      db.prepare('CREATE INDEX IF NOT EXISTS monthly_scans_owner ON monthly_scan_sessions(user_id,problem_id)'),
      db.prepare('CREATE INDEX IF NOT EXISTS monthly_scan_photos_session ON monthly_scan_photos(scan_id,seq)'),
    ])).then(() => true);
    ready.set(key, promise);
    promise.catch(() => { if (ready.get(key) === promise) ready.delete(key); });
  }
  return promise;
}

const scanGuard = alias => `${alias}.revoked_at IS NULL AND ${alias}.expires_at>?
  AND EXISTS(SELECT 1 FROM users u WHERE u.id=${alias}.user_id AND u.deleted=0)
  AND EXISTS(SELECT 1 FROM problems p WHERE p.id=${alias}.problem_id AND p.opens_at<=?
    AND NOT EXISTS(SELECT 1 FROM monthly_problem_retirements mr WHERE mr.problem_id=p.id))
  AND (SELECT COUNT(*) FROM submissions s WHERE s.user_id=${alias}.user_id AND s.problem_id=${alias}.problem_id)=${alias}.attempts_used`;

async function storePhoto(db, { userId, problemId, partId, mime, data, transcript, timestamp, scan }) {
  const id = crypto.randomUUID(), statements = [db.prepare(`INSERT INTO monthly_answer_photos
    (id,user_id,problem_id,part_id,mime,bytes,ocr_text,created_at)
    SELECT ?,?,?,?,?,?,?,? WHERE EXISTS(SELECT 1 FROM users WHERE id=? AND deleted=0)
      AND (SELECT COUNT(*) FROM monthly_answer_photos WHERE user_id=? AND problem_id=?)<?
      AND (SELECT COALESCE(SUM(bytes),0) FROM monthly_answer_photos WHERE user_id=? AND problem_id=?)+?<=?
      ${scan ? `AND EXISTS(SELECT 1 FROM monthly_scan_sessions q WHERE q.id=? AND q.user_id=? AND q.problem_id=? AND ${scanGuard('q')})
        AND EXISTS(SELECT 1 FROM monthly_scan_uploads up WHERE up.scan_id=? AND up.request_id=? AND up.claim=? AND up.photo_id IS NULL)` : ''}`)
    .bind(id,userId,problemId,partId,mime,data.byteLength,transcript,timestamp,
      userId,userId,problemId,MAX_PHOTOS,userId,problemId,data.byteLength,MAX_STORED,
      ...(scan ? [scan.id,userId,problemId,timestamp,timestamp,scan.id,scan.requestId,scan.claim] : []))];
  if (scan) statements.push(db.prepare(`INSERT INTO monthly_scan_photos(scan_id,photo_id)
    SELECT ?,? WHERE EXISTS(SELECT 1 FROM monthly_answer_photos WHERE id=?)`).bind(scan.id,id,id));
  for (let offset = 0, no = 0; offset < data.byteLength; offset += CHUNK, no++) {
    statements.push(db.prepare(`INSERT INTO monthly_answer_photo_chunks(photo_id,no,data)
      SELECT ?,?,? WHERE EXISTS(SELECT 1 FROM monthly_answer_photos WHERE id=?)`)
      .bind(id,no,data.slice(offset,offset+CHUNK).buffer,id));
  }
  if (scan) statements.push(db.prepare(`UPDATE monthly_scan_uploads SET photo_id=?,updated_at=?
    WHERE scan_id=? AND request_id=? AND claim=? AND photo_id IS NULL
      AND EXISTS(SELECT 1 FROM monthly_answer_photos WHERE id=?)`).bind(id,timestamp,scan.id,scan.requestId,scan.claim,id));
  const result = await db.batch(statements);
  if (!result[0].meta?.changes) {
    const owner = await db.prepare('SELECT deleted FROM users WHERE id=?').bind(userId).first();
    if (!owner || owner.deleted) fail(scan ? 'scan_closed' : 'login_required',scan ? 410 : 401);
    if (scan && !await db.prepare(`SELECT id FROM monthly_scan_sessions q WHERE q.id=? AND ${scanGuard('q')}`)
      .bind(scan.id,timestamp,timestamp).first()) fail('scan_closed',410);
    if (scan && !await db.prepare('SELECT request_id FROM monthly_scan_uploads WHERE scan_id=? AND request_id=? AND claim=? AND photo_id IS NULL')
      .bind(scan.id,scan.requestId,scan.claim).first()) fail('upload_processing',409);
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
    db.prepare('DELETE FROM monthly_scan_uploads WHERE scan_id IN (SELECT id FROM monthly_scan_sessions WHERE user_id=?)').bind(userId),
    db.prepare('DELETE FROM monthly_scan_photos WHERE scan_id IN (SELECT id FROM monthly_scan_sessions WHERE user_id=?)').bind(userId),
    db.prepare('DELETE FROM monthly_scan_sessions WHERE user_id=?').bind(userId),
    db.prepare('DELETE FROM monthly_answer_photo_chunks WHERE photo_id IN (SELECT id FROM monthly_answer_photos WHERE user_id=?)').bind(userId),
    db.prepare('DELETE FROM monthly_answer_photos WHERE user_id=?').bind(userId),
  ];
}

const scanNow = () => Math.floor(Date.now()/1000);
const scanToken = () => btoa(String.fromCharCode(...crypto.getRandomValues(new Uint8Array(32)))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
const scanHash = async token => btoa(String.fromCharCode(...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(token))))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
const photoHash = async data => [...new Uint8Array(await crypto.subtle.digest('SHA-256',data))].map(n=>n.toString(16).padStart(2,'0')).join('');
const scanView = (session, reason = null) => ({id:session.id,problem_id:session.problem_id,part_id:session.part_id,
  created_at:session.created_at,expires_at:session.expires_at,open:!reason,closed_reason:reason});

async function scanState(db, session, visibleSql, attempts) {
  const timestamp = scanNow();
  const owner = await db.prepare('SELECT deleted FROM users WHERE id=?').bind(session.user_id).first();
  if (!owner || owner.deleted) return {reason:'closed'};
  if (session.revoked_at !== null) return {reason:'revoked'};
  if (timestamp >= session.expires_at) return {reason:'expired'};
  const problem = await db.prepare(`SELECT p.* FROM problems p WHERE p.id=? AND ${visibleSql('p')}`).bind(session.problem_id).first();
  const sheet = problem && getMonthlyAnswerSheet(problem);
  if (!sheet || problem.opens_at > timestamp) return {reason:'not_found'};
  const used = await attempts(db,problem.id,session.user_id);
  if (!used.remaining) return {reason:'attempts_exhausted'};
  if (used.used !== session.attempts_used) return {reason:'submitted'};
  return {reason:null,problem,sheet};
}

async function boundedForm(req, HttpError) {
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
  const closed = reason => { throw new HttpError(410,reason === 'attempts_exhausted' ? reason : ['expired','revoked','submitted'].includes(reason) ? 'scan_'+reason : 'scan_closed'); };
  const initialize = async env => {
    await ensureContent(env.DB,scope(env));
    await ensureMonthlyPhotoSchema(env.DB,scope(env));
  };
  const lookup = async (req,env) => {
    const token = req.headers.get('X-Monthly-Scan') || '';
    if (!/^[A-Za-z0-9_-]{43}$/.test(token)) throw new HttpError(403,'bad_scan_token');
    await limit(env,'monthly-scan-lookup:'+(req.headers.get('CF-Connecting-IP') || 'unknown').slice(0,128),120,60);
    await initialize(env);
    const session = await env.DB.prepare('SELECT * FROM monthly_scan_sessions WHERE token_hash=?').bind(await scanHash(token)).first();
    if (!session) throw new HttpError(403,'bad_scan_token');
    const state = await scanState(env.DB,session,visibleSql,attempts);
    if (state.reason) closed(state.reason);
    return {session,...state};
  };
  const reserveUpload = async (env,scan,requestId,payloadHash) => {
    const timestamp=scanNow(),claim=crypto.randomUUID();
    const live=await env.DB.prepare(`SELECT id FROM monthly_scan_sessions q WHERE q.id=? AND ${scanGuard('q')}`)
      .bind(scan.id,timestamp,timestamp).first();
    if(!live)closed('closed');
    await env.DB.prepare(`INSERT OR IGNORE INTO monthly_scan_uploads(scan_id,request_id,payload_hash,claim,created_at,updated_at)
      SELECT ?,?,?,?,?,? WHERE EXISTS(SELECT 1 FROM monthly_scan_sessions q WHERE q.id=? AND ${scanGuard('q')})
        AND (SELECT COUNT(*) FROM monthly_scan_uploads WHERE scan_id=?)<?`)
      .bind(scan.id,requestId,payloadHash,claim,timestamp,timestamp,scan.id,timestamp,timestamp,scan.id,MAX_SCAN_REQUESTS).run();
    const row=await env.DB.prepare('SELECT * FROM monthly_scan_uploads WHERE scan_id=? AND request_id=?').bind(scan.id,requestId).first();
    if(!row)throw new HttpError(429,'monthly_scan_upload_limit');
    if(row.payload_hash!==payloadHash)throw new HttpError(409,'upload_conflict');
    if(row.photo_id){
      const photo=await env.DB.prepare(`SELECT p.id AS photo_id,p.part_id,p.ocr_text AS text,p.mime,p.bytes
        FROM monthly_answer_photos p WHERE p.id=? AND p.user_id=? AND p.problem_id=?
          AND EXISTS(SELECT 1 FROM monthly_scan_sessions q WHERE q.id=? AND ${scanGuard('q')})`)
        .bind(row.photo_id,scan.user_id,scan.problem_id,scan.id,timestamp,timestamp).first();
      if(!photo)closed('closed');
      return {replay:{...photo,replayed:true}};
    }
    if(row.claim!==claim){
      const renewed=await env.DB.prepare(`UPDATE monthly_scan_uploads SET claim=?,updated_at=?
        WHERE scan_id=? AND request_id=? AND payload_hash=? AND photo_id IS NULL AND (claim='' OR updated_at<?)
          AND EXISTS(SELECT 1 FROM monthly_scan_sessions q WHERE q.id=? AND ${scanGuard('q')})`)
        .bind(claim,timestamp,scan.id,requestId,payloadHash,timestamp-SCAN_UPLOAD_STALE,scan.id,timestamp,timestamp).run();
      if(!renewed.meta?.changes)throw new HttpError(409,'upload_processing',{retry_after:2});
    }
    return {scan:{...scan,requestId,claim}};
  };
  const upload = async (req,env,url,problem,sheet,userId,scan) => {
    if (!env.UPSTAGE_API_KEY && !scan) throw new HttpError(503,'ocr_off');
    if (scan) await limit(env,'monthly-scan-upload:'+userId,60,3600);
    if (!/^multipart\/form-data\s*;/i.test(req.headers.get('Content-Type') || '')) throw new HttpError(400,'bad_image');
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
    let data;
    if(scan){
      const requestId=form.get('request_id');
      if(typeof requestId!=='string'||!/^[A-Za-z0-9_-]{16,100}$/.test(requestId))throw new HttpError(400,'bad_upload_request');
      data=new Uint8Array(await original.arrayBuffer());
      const hashes=await Promise.all([photoHash(await image.arrayBuffer()),photoHash(data)]);
      const reservation=await reserveUpload(env,scan,requestId,[partId,url.searchParams.get('mode')==='math'?'math':'text',...hashes].join(':'));
      if(reservation.replay)return reservation.replay;
      scan=reservation.scan;
    }
    try {
      const usage = await env.DB.prepare('SELECT COUNT(*) n,COALESCE(SUM(bytes),0) bytes FROM monthly_answer_photos WHERE user_id=? AND problem_id=?').bind(userId,problem.id).first();
      if (usage.n >= MAX_PHOTOS || usage.bytes + original.size > MAX_STORED) throw new HttpError(413,'monthly_photo_storage_full');
      if (!env.UPSTAGE_API_KEY) throw new HttpError(503,'ocr_off');
      await limit(env,'ocr:'+userId,30,86400);
      const result = await ocr(env,image,url.searchParams.get('mode') === 'math' ? 'math' : 'text');
      if (typeof result.text !== 'string' || !result.text.trim()) throw new HttpError(422,'ocr_empty');
      if (new TextEncoder().encode(result.text).byteLength > MAX_OCR_BYTES) throw new HttpError(413,'ocr_too_big');
      data ||= new Uint8Array(await original.arrayBuffer());
      const mime = imageType(data);
      const saved = await storePhoto(env.DB,{userId,problemId:problem.id,partId,mime,data,scan,
        transcript:result.text,timestamp:scanNow()});
      return {...result,photo_id:saved.id,part_id:saved.part_id,mime:saved.mime,bytes:saved.bytes};
    } catch (error) {
      if(scan?.claim)await env.DB.prepare(`UPDATE monthly_scan_uploads SET claim='',updated_at=0
        WHERE scan_id=? AND request_id=? AND claim=? AND photo_id IS NULL`).bind(scan.id,scan.requestId,scan.claim).run().catch(()=>{});
      if (error instanceof MonthlyAnswerError) throw new HttpError(error.status,error.code);
      throw error;
    }
  };
  return async function monthlyPhotoRoute(path, method, me, req, env, url, body = {}) {
    let match;
    if (path === '/api/monthly/scan' && method === 'GET') {
      const {session,problem,sheet} = await lookup(req,env);
      return {session:scanView(session),problem:{id:problem.id,title:problem.title_ko,title_ko:problem.title_ko,title_en:problem.title_en},
        parts:sheet.parts.map(({id,label_ko,label_en,points}) => ({id,label:label_ko,label_ko,label_en,points})),
        limits:{max_image_bytes:MAX_IMAGE,max_photos:MAX_PHOTOS},now:scanNow()};
    }
    if (path === '/api/monthly/scan/photos' && method === 'POST') {
      const {session,problem,sheet} = await lookup(req,env);
      return upload(req,env,url,problem,sheet,session.user_id,session);
    }
    if ((match = /^\/api\/monthly\/problems\/(\d+)\/scan(?:\/([a-f0-9-]{36}))?$/.exec(path))) {
      needUser(me);
      await initialize(env);
      const problemId = +match[1], id = match[2];
      if (!id && method === 'POST') {
        const problem = await env.DB.prepare(`SELECT p.* FROM problems p WHERE p.id=? AND ${visibleSql('p')}`).bind(problemId).first();
        const sheet = problem && getMonthlyAnswerSheet(problem);
        if (!sheet || problem.opens_at > scanNow()) throw new HttpError(404,'not_found');
        const initial = body.part_id === undefined ? sheet.parts[0].id : body.part_id;
        if (!sheet.parts.some(part => part.id === initial)) throw new HttpError(400,'bad_answer_sheet');
        const remaining = await attempts(env.DB,problem.id,me.id);
        if (!remaining.remaining) throw new HttpError(409,'attempts_exhausted',{attempts:remaining});
        await limit(env,'monthly-scan-create:'+me.id,30,3600);
        const timestamp = scanNow(), token = scanToken(), session = {id:crypto.randomUUID(),problem_id:problem.id,part_id:initial,created_at:timestamp,expires_at:timestamp+SCAN_SECONDS};
        // Old capabilities expire, while the photographed originals remain in their independent archive.
        const old = 'SELECT id FROM monthly_scan_sessions WHERE user_id=? AND expires_at<? ORDER BY id LIMIT 100';
        const result = await env.DB.batch([
          env.DB.prepare(`DELETE FROM monthly_scan_uploads WHERE scan_id IN (${old})`).bind(me.id,timestamp-86400),
          env.DB.prepare(`DELETE FROM monthly_scan_photos WHERE scan_id IN (${old})`).bind(me.id,timestamp-86400),
          env.DB.prepare(`DELETE FROM monthly_scan_sessions WHERE id IN (${old})`).bind(me.id,timestamp-86400),
          env.DB.prepare('UPDATE monthly_scan_sessions SET revoked_at=? WHERE user_id=? AND problem_id=? AND revoked_at IS NULL').bind(timestamp,me.id,problem.id),
          env.DB.prepare(`INSERT INTO monthly_scan_sessions(id,token_hash,user_id,problem_id,part_id,attempts_used,created_at,expires_at)
            SELECT ?,?,?,?,?,?,?,? WHERE EXISTS(SELECT 1 FROM users WHERE id=? AND deleted=0)
              AND (SELECT COUNT(*) FROM submissions WHERE user_id=? AND problem_id=?)=?
              AND EXISTS(SELECT 1 FROM problems p WHERE p.id=? AND p.opens_at<=? AND ${visibleSql('p')})`)
            .bind(session.id,await scanHash(token),me.id,problem.id,initial,remaining.used,timestamp,session.expires_at,
              me.id,me.id,problem.id,remaining.used,problem.id,timestamp),
        ]);
        if (!result.at(-1).meta?.changes) throw new HttpError(409,'scan_closed');
        return {session:scanView(session),token,now:timestamp};
      }
      if (id && ['GET','DELETE'].includes(method)) {
        const session = await env.DB.prepare('SELECT * FROM monthly_scan_sessions WHERE id=? AND user_id=? AND problem_id=?').bind(id,me.id,problemId).first();
        if (!session) throw new HttpError(404,'not_found');
        if (method === 'DELETE') {
          await env.DB.prepare('UPDATE monthly_scan_sessions SET revoked_at=? WHERE id=? AND user_id=? AND revoked_at IS NULL').bind(scanNow(),id,me.id).run();
          return {ok:true};
        }
        await limit(env,'monthly-scan-poll:'+me.id,90,60);
        const after = Number(url.searchParams.get('after') || '0');
        if (!Number.isSafeInteger(after) || after < 0) throw new HttpError(400,'bad_cursor');
        const state = await scanState(env.DB,session,visibleSql,attempts);
        const rows = (await env.DB.prepare(`SELECT q.seq,p.id AS photo_id,p.part_id,p.ocr_text AS text,p.mime,p.bytes,p.created_at
          FROM monthly_scan_photos q JOIN monthly_answer_photos p ON p.id=q.photo_id
          WHERE q.scan_id=? AND q.seq>? AND p.user_id=? AND p.problem_id=? ORDER BY q.seq LIMIT ?`)
          .bind(id,after,me.id,problemId,SCAN_PAGE+1).all()).results;
        const photos = rows.slice(0,SCAN_PAGE);
        return {session:scanView(session,state.reason),photos,cursor:photos.at(-1)?.seq || after,has_more:rows.length>SCAN_PAGE,now:scanNow()};
      }
      return undefined;
    }
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
    return upload(req,env,url,problem,sheet,me.id);
  };
}
