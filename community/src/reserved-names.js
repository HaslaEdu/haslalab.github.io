// Names that pass for the site's own staff, and mailboxes made to be thrown away, are refused when an account is made
// or renamed (the owner's rule, 2026-11-04: an account named «admin» on a throwaway address had tried «admin» logins
// first). Neither check is a security boundary — roles are a column, never a name — they keep an account from
// looking official to other users and keep the free sign-up tokens off single-use mailboxes.

/* the name as a reader sees it: compatibility forms folded (NFKC), lower case, the usual digit-for-letter swaps
   undone («4dm1n» is «admin»), then everything but letters dropped («ad_min», «a.d.m.i.n», «admin2026») */
const LEET = { 0: 'o', 1: 'i', 3: 'e', 4: 'a', 5: 's', 7: 't', '@': 'a', '$': 's', '!': 'i', '|': 'i' };
export function nameKey(value) {
  return String(value ?? '').normalize('NFKC').toLowerCase().replace(/[013457@$!|]/g, c => LEET[c]).replace(/[^\p{L}]/gu, '');
}
// anywhere in the name
const CONTAINS = ['administrator', 'haslalab', 'haslaedu', '하슬라랩', '하슬라에듀', '관리자', '운영자', '운영진', '운영팀', '공식계정', 'moderator'];
// at the start or the end (inside a word it is someone's own: «badminton»)
const EDGE = ['admin', '어드민'];
// the whole name
const WHOLE = new Set(['root', 'system', 'sysop', 'staff', 'support', 'official', 'owner', 'mod', 'hasla', '하슬라', '공식', '운영', '관리', 'webmaster', 'superuser']);
/** true when a username or nickname would pass for the site's own staff */
export function reservedName(value) {
  const k = nameKey(value);
  if (!k) return false;
  return WHOLE.has(k) || CONTAINS.some(w => k.includes(w)) || EDGE.some(w => k.startsWith(w) || k.endsWith(w));
}

// throwaway-mailbox services; a subdomain of one is the same service
const DISPOSABLE = new Set([
  'drtall.com', 'mailinator.com', 'mailinator.net', 'mailinator2.com', 'yopmail.com', 'yopmail.net', 'yopmail.fr',
  'guerrillamail.com', 'guerrillamail.net', 'guerrillamail.org', 'guerrillamail.biz', 'guerrillamail.de', 'guerrillamailblock.com',
  'sharklasers.com', 'grr.la', 'pokemail.net', 'spam4.me', '10minutemail.com', '10minutemail.net', '10minutemail.co.uk',
  'temp-mail.org', 'temp-mail.io', 'tempmail.com', 'tempmail.net', 'tempmail.dev', 'tempmailo.com', 'tempmail.plus', 'temp-mail.us',
  'maildrop.cc', 'getnada.com', 'nada.email', 'dispostable.com', 'trashmail.com', 'trashmail.net', 'trashmail.de', 'trashmail.me',
  '1secmail.com', '1secmail.net', '1secmail.org', 'mail.tm', 'mailto.plus', 'emailondeck.com', 'mohmal.com', 'fakeinbox.com',
  'throwawaymail.com', 'mintemail.com', 'mytemp.email', 'tempinbox.com', 'mailnesia.com', 'mailcatch.com', 'spamgourmet.com',
  'getairmail.com', 'moakt.com', 'tmail.ws', 'tmpmail.org', 'tmpmail.net', 'emailfake.com', 'fakemail.net', 'burnermail.io',
  'inboxkitten.com', 'mailpoof.com', 'linshiyouxiang.net', 'byom.de', 'discard.email', 'harakirimail.com', 'spambox.us',
  'mailsac.com', 'tempr.email', 'dropmail.me', 'emltmp.com', 'minuteinbox.com', 'cs.email', 'tmails.net', 'mail7.io',
]);
/** true when the address is at a throwaway-mailbox service (DISPOSABLE_EMAIL_DOMAINS in the environment adds more, comma-separated) */
export function disposableEmail(email, env = {}) {
  const at = String(email ?? '').lastIndexOf('@');
  if (at < 0) return false;
  const domain = String(email).slice(at + 1).trim().toLowerCase().replace(/\.$/, '');
  const extra = String(env?.DISPOSABLE_EMAIL_DOMAINS || '').toLowerCase().split(',').map(s => s.trim()).filter(Boolean);
  const parts = domain.split('.');
  for (let i = 0; i < parts.length - 1; i++) {
    const d = parts.slice(i).join('.');
    if (DISPOSABLE.has(d) || extra.includes(d)) return true;
  }
  return false;
}
