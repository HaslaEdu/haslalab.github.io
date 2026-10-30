// Runtime bootstrap uses the existing writable D1 binding. Public read replicas
// only SELECT and can still serve notices before this additive table exists.
const pending = new WeakMap();
export const NOTICE_PINS_SCHEMA = `CREATE TABLE IF NOT EXISTS notice_pins (
  post_id INTEGER PRIMARY KEY REFERENCES posts(id) ON DELETE CASCADE,
  pinned_at INTEGER NOT NULL
)`;

export function missingNoticePins(error) {
  for (let current = error, depth = 0; current && depth < 5; current = current.cause, depth++) {
    if (/\bno such table:\s*(?:main\.)?notice_pins\b/i.test(String(current.message || current))) return true;
  }
  return false;
}

export function ensureNoticePins(db, scope = db) {
  let ready = pending.get(scope);
  if (!ready) {
    ready = Promise.resolve().then(() => db.prepare(NOTICE_PINS_SCHEMA).run()).catch(error => {
      if (pending.get(scope) === ready) pending.delete(scope);
      throw error;
    });
    pending.set(scope, ready);
  }
  return ready;
}

export async function noticeIsPinned(db, id) {
  try { return !!await db.prepare('SELECT post_id FROM notice_pins WHERE post_id=?').bind(id).first(); }
  catch (error) { if (missingNoticePins(error)) return false; throw error; }
}

export async function removeNoticePin(db, id) {
  try { await db.prepare('DELETE FROM notice_pins WHERE post_id=?').bind(id).run(); }
  catch (error) { if (!missingNoticePins(error)) throw error; }
}
