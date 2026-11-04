// An answer that tries to instruct the grader is not an answer: it is an attempt on the grading, and the account that
// sends one is suspended (the owner's rule, 2026-11-04). The grader already treats answer text as data, never instructions,
// and points need a quote the student actually wrote, so an attempt cannot raise a score; this takes the account out.
//
// Only unambiguous signals count. A physics answer writes «<<» for «much less than» and brackets for references, so a
// bare «<<» or «[1]» is never a signal; what is matched is our own prompt machinery (the fence names and section headers
// the prompts use) and plain instructions to the grader in English or Korean. Each match is kept with its passage, so an
// administrator can see why and lift the suspension (DELETE or lifted_at).
export const SUSPENSION_SCHEMA = [
  `CREATE TABLE IF NOT EXISTS account_suspensions (
    user_id INTEGER PRIMARY KEY,
    reason TEXT NOT NULL,
    source TEXT NOT NULL,
    evidence TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    lifted_at INTEGER
  )`,
];
const ready = new WeakMap();
export function ensureSuspensionSchema(db, scope = db) {
  if (!ready.has(scope)) ready.set(scope, (async () => { for (const sql of SUSPENSION_SCHEMA) await db.prepare(sql).run(); })().catch(error => { ready.delete(scope); throw error; }));
  return ready.get(scope);
}

const RULES = [
  // the prompts' own fences and headers, written into an answer
  ['fence', /<<\s*(?:END|ANSWER|SCHEME|OCR|PDF_TEXT|ANALYSIS|TRANSCRIPT|STEPS|PAGES|SECOND TRANSCRIPT|END SECOND TRANSCRIPT)\b[^>\n]{0,40}>>/i],
  ['header', /^[ \t]*\[(?:TASK:\s*(?:grade|build marking scheme|review)|End of fixed rules|Rubric|Marking scheme[^\]\n]{0,40}|Private session reference[^\]\n]{0,40})\][ \t]*$/im],
  ['role', /<\|(?:im_start|im_end|system|start_header_id|end_header_id)\|>|^[ \t]*(?:system|assistant|developer)\s*:\s*(?:you|ignore|grade|award|give)\b/im],
  // instructions to the grader
  ['instruction', /\b(?:ignore|disregard|forget|override)\s+(?:all\s+|any\s+|the\s+|your\s+)?(?:previous|prior|above|earlier|preceding|grading|marking|system)\s+(?:instructions?|rules?|prompts?|rubric|scheme|criteria)\b/i],
  ['instruction', /\b(?:give|award|assign|grant)\s+(?:me\s+|this\s+(?:answer|solution|student)\s+|the\s+student\s+)?(?:full|maximum|max|all(?:\s+the)?|perfect|100\s*%)\s+(?:marks?|points?|score|credit)\b/i],
  ['instruction', /\byou\s+(?:are|must|will|should)\s+(?:now\s+)?(?:give|award|grade\s+this\s+as|mark\s+this\s+as|output|return)\b[^.\n]{0,40}\b(?:full|maximum|correct|10\s*\/\s*10|100\s*%)/i],
  ['instruction', /(?:이전|앞의|위의|기존|모든)\s*(?:지시|지침|명령|규칙|채점\s*기준|프롬프트)\S{0,3}\s*(?:무시|잊어|따르지\s*마)/],
  ['instruction', /(?:채점\s*(?:기준|규칙|지침)\S{0,3}\s*무시|만점\s*(?:을|으로)?\s*(?:줘|주세요|주시오|처리|부여|매겨)|점수\s*를?\s*(?:만점|최고점|10\s*점)\s*(?:으로|을)?\s*(?:줘|주세요|처리|부여|매겨))/],
];

/** the injection signals in student-controlled text: [{rule, passage}], empty when there are none */
export function injectionSignals(text) {
  const s = String(text ?? '');
  if (!s) return [];
  const out = [];
  for (const [rule, re] of RULES) {
    const m = re.exec(s);
    if (m && !out.some(x => x.passage === m[0])) {
      const at = m.index;
      out.push({ rule, passage: s.slice(Math.max(0, at - 40), at + m[0].length + 40).replace(/\s+/g, ' ').trim().slice(0, 240) });
    }
  }
  return out;
}

/** suspends the account for an injection attempt: users.deleted = 2 (every route already treats a non-zero «deleted» as
    no account, so sessions, rankings and rewards drop it with no extra query), the evidence row, and every session
    ended. Returns true when it was newly suspended. An administrator's account is never suspended by this (logged). */
export const SUSPENDED = 2;
export async function suspendForInjection(env, userId, source, signals, scope = env.DB) {
  if (!userId || !signals?.length) return false;
  await ensureSuspensionSchema(env.DB, scope);
  const u = await env.DB.prepare('SELECT role,deleted FROM users WHERE id=?').bind(userId).first();
  if (!u || u.deleted) return false;
  if (u.role === 'admin') { console.error('injection_signal_admin', source, signals.map(x => x.rule).join(',')); return false; }
  const now = Math.floor(Date.now() / 1000);
  const res = await env.DB.batch([
    env.DB.prepare(`UPDATE users SET deleted=${SUSPENDED} WHERE id=? AND deleted=0 AND role<>'admin'`).bind(userId),
    env.DB.prepare(`INSERT INTO account_suspensions(user_id,reason,source,evidence,created_at) VALUES(?,?,?,?,?)
      ON CONFLICT(user_id) DO UPDATE SET reason=excluded.reason,source=excluded.source,evidence=excluded.evidence,created_at=excluded.created_at,lifted_at=NULL`)
      .bind(userId, 'prompt_injection', String(source).slice(0, 80), JSON.stringify(signals.slice(0, 5)), now),
    env.DB.prepare('DELETE FROM sessions WHERE user_id=?').bind(userId),
  ]);
  console.error('account_suspended_prompt_injection', userId, source, signals.map(x => x.rule).join(','));
  return !!res[0]?.meta?.changes;
}
/** lifts a suspension: the account comes back as it was */
export async function liftSuspension(env, userId, scope = env.DB) {
  await ensureSuspensionSchema(env.DB, scope);
  const now = Math.floor(Date.now() / 1000);
  const res = await env.DB.batch([
    env.DB.prepare(`UPDATE users SET deleted=0 WHERE id=? AND deleted=${SUSPENDED}`).bind(userId),
    env.DB.prepare('UPDATE account_suspensions SET lifted_at=? WHERE user_id=? AND lifted_at IS NULL').bind(now, userId),
  ]);
  return !!res[0]?.meta?.changes;
}
