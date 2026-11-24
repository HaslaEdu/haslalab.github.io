const SQL = `CREATE TABLE IF NOT EXISTS account_signup_sources (
  user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  source TEXT NOT NULL CHECK (source IN ('lab', 'nonsul', 'unknown'))
);`;
const schema = new WeakMap();

export function ensureSignupSources(db) {
  let pending = schema.get(db);
  if (!pending) {
    pending = db.prepare(SQL).run().catch(error => { schema.delete(db); throw error; });
    schema.set(db, pending);
  }
  return pending;
}

export function signupSource(value) {
  let url;
  try { url = new URL(value); } catch { return 'unknown'; }
  if (url.protocol !== 'https:' || url.port || url.username || url.password) return 'unknown';
  const name = url.hostname;
  if (['haslalab.org', 'www.haslalab.org', 'haslaedu.github.io'].includes(name)) return 'lab';
  if (['haslaedu.kr', 'www.haslaedu.kr', 'physleague.kr', 'www.physleague.kr', 'haslaedu.haslalab.workers.dev'].includes(name)) return 'nonsul';
  return 'unknown';
}
