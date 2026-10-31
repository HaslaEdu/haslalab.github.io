import { getMonthlyAnswerSheet } from '../../monthly-problems.mjs';
import { MonthlyAnswerError } from './monthly-answers.js';
import { ensureMonthlyPhotoSchema } from './monthly-photos.js';
import { ensureMonthlyCaptureSchema } from './monthly-capture.js';

export const MONTHLY_EXPERIMENT_VISUAL_MAX_IMAGES = 20;
// Base64 plus prompts/schema must fit the selected visual provider's JSON budget.
// Enforce this before a monthly attempt is reserved, with room below its 14 MiB image cap.
export const MONTHLY_EXPERIMENT_VISUAL_MAX_BYTES = 12 * 1024 * 1024;
const MAX_STORED_PHOTOS = 40, MAX_PHOTO_BYTES = 4 * 1024 * 1024;
const UUID = /^[a-f0-9-]{36}$/;
const fail = (code,status = 400) => { throw new MonthlyAnswerError(code,status); };

function photoIds(value) {
  if (value === undefined) return [];
  if (!Array.isArray(value) || value.length > MAX_STORED_PHOTOS ||
      value.some(id => typeof id !== 'string' || !UUID.test(id))) fail('bad_photo_ids');
  return [...new Set(value)].sort();
}
function bytesOf(value) {
  if (value instanceof ArrayBuffer) return new Uint8Array(value);
  if (ArrayBuffer.isView(value)) return new Uint8Array(value.buffer,value.byteOffset,value.byteLength);
  if (Array.isArray(value) && value.every(n => Number.isInteger(n) && n >= 0 && n <= 255)) return Uint8Array.from(value);
  fail('photo_unavailable',500);
}
function imageType(bytes) {
  if (bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return 'image/jpeg';
  if (bytes.length >= 8 && [137,80,78,71,13,10,26,10].every((n,i) => bytes[i] === n)) return 'image/png';
  if (bytes.length >= 12 && String.fromCharCode(...bytes.subarray(0,4)) === 'RIFF' &&
      String.fromCharCode(...bytes.subarray(8,12)) === 'WEBP') return 'image/webp';
  return null;
}
function base64(bytes) {
  const chunks = [], block = 3 * 8192;
  // All intermediate blocks are divisible by three, so joined base64 stays valid.
  for (let offset = 0; offset < bytes.length; offset += block) {
    chunks.push(btoa(String.fromCharCode(...bytes.subarray(offset,offset+block))));
  }
  return chunks.join('');
}
function marker(photoId,partId) { return `[PHOTO:${photoId}:${partId}]`; }
function graderText(answer,parts,evidence) {
  const associations = parts.filter(part => part.answer && part.working && evidence.has(part.id))
    .map(part => `[${part.id}]\n${[...evidence.get(part.id)].join('\n')}`).join('\n\n');
  // Preserve the frozen authenticated instrument appendix already in answer.
  // Photo associations are server labels, never replacement student content.
  return answer+'\n\n[Server-associated student photographs]\n'+associations;
}

// Only server-owned originals are sent to the grader. Student text, serialized
// submissions and idempotency keys remain unchanged; image references are transient.
export async function prepareMonthlyExperimentVisuals(db,userId,problem,normalized,key = db) {
  const sheet = getMonthlyAnswerSheet(problem);
  if (!sheet) return {images:[],imageCount:0,bytes:0};
  const evidence = new Map();
  normalized.visualEvidence = evidence;
  normalized.graderAnswer = normalized.answer;
  const ids = photoIds(normalized.sheet?.photo_ids);
  if (!ids.length) return {images:[],imageCount:0,bytes:0};
  await ensureMonthlyPhotoSchema(db,key);
  const rows = (await db.prepare(`SELECT id,part_id,mime,bytes,provider FROM monthly_answer_photos
    WHERE user_id=? AND problem_id=? AND id IN (${ids.map(() => '?').join(',')})`)
    .bind(userId,problem.id,...ids).all()).results;
  const byId = new Map(rows.map(row => [row.id,row]));
  if (rows.length !== ids.length || ids.some(id => !byId.has(id))) fail('bad_photo_ids');
  const provider=normalized.provider||normalized.sheet.provider;
  if(rows.some(row=>row.provider&&row.provider!==provider))fail('provider_locked',409);
  const known = new Set(sheet.parts.map(part => part.id));
  const answered = new Set(normalized.sheet.parts.filter(part => known.has(part.id) && part.answer && part.working).map(part => part.id));
  const associations = new Map();
  const capture = normalized.sheet.capture;
  if (capture) {
    if (typeof capture.scan_id !== 'string' || !UUID.test(capture.scan_id)) fail('bad_photo_ids');
    await ensureMonthlyCaptureSchema(db,key);
    const session = await db.prepare('SELECT id,provider FROM monthly_capture_sessions WHERE id=? AND user_id=? AND problem_id=?')
      .bind(capture.scan_id,userId,problem.id).first();
    if (!session) fail('bad_photo_ids');
    if(session.provider&&session.provider!==provider)fail('provider_locked',409);
    const pages = (await db.prepare(`SELECT photo_id,page_no,kind,parts,ocr_status FROM monthly_capture_pages
      WHERE session_id=? AND active=1 AND photo_id IN (${ids.map(() => '?').join(',')})`)
      .bind(capture.scan_id,...ids).all()).results;
    if (pages.length !== ids.length) fail('bad_photo_ids');
    for (const page of pages) {
      const allowed = Number.isInteger(page.page_no) && sheet.pages[page.page_no-1];
      let extracted;
      try { extracted = JSON.parse(page.parts); } catch { fail('photo_unavailable',500); }
      if (!allowed || !['answer','working'].includes(page.kind) || page.ocr_status !== 'done' ||
          !Array.isArray(extracted) || extracted.some(part => !part || !allowed.includes(part.id))) fail('photo_unavailable',500);
      // A graph can be visible even when OCR did not extract any text from it.
      const visible=new Set(extracted.filter(part=>part.answer||part.working).map(part=>part.id));
      associations.set(page.photo_id,allowed.filter(id => answered.has(id)&&visible.has(id)));
    }
  } else {
    for (const row of rows) {
      if (!known.has(row.part_id)) fail('bad_photo_ids');
      associations.set(row.id,answered.has(row.part_id) ? [row.part_id] : []);
    }
  }
  const selected = ids.filter(id => associations.get(id)?.length);
  const total = selected.reduce((sum,id) => {
    const size = byId.get(id).bytes;
    if (!Number.isInteger(size) || size < 1 || size > MAX_PHOTO_BYTES) fail('photo_unavailable',500);
    return sum+size;
  },0);
  if (selected.length > MONTHLY_EXPERIMENT_VISUAL_MAX_IMAGES || total > MONTHLY_EXPERIMENT_VISUAL_MAX_BYTES) fail('monthly_visuals_too_large',413);
  const images = [];
  for (const id of selected) {
    const row = byId.get(id), partIds = associations.get(id);
    const chunks = (await db.prepare('SELECT no,data FROM monthly_answer_photo_chunks WHERE photo_id=? ORDER BY no').bind(id).all()).results;
    const data = new Uint8Array(row.bytes); let offset = 0;
    for (const [index,chunk] of chunks.entries()) {
      const bytes = bytesOf(chunk.data);
      if (chunk.no !== index || !bytes.length || offset+bytes.length > data.length) fail('photo_unavailable',500);
      data.set(bytes,offset); offset += bytes.length;
    }
    if (offset !== data.length || imageType(data) !== row.mime) fail('photo_unavailable',500);
    const markers = partIds.map(partId => marker(id,partId));
    images.push({mime:row.mime,data:base64(data),label:`Student photograph ${id}; associated parts: ${markers.join(' ')}`,part_ids:[...partIds]});
    for (const [index,partId] of partIds.entries()) {
      if (!evidence.has(partId)) evidence.set(partId,new Set());
      evidence.get(partId).add(markers[index]);
    }
  }
  normalized.graderAnswer = images.length ? graderText(normalized.answer,normalized.sheet.parts,evidence) : normalized.answer;
  return {images,imageCount:images.length,bytes:total};
}
