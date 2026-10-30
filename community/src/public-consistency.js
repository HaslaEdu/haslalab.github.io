export const BOOKMARK_QUERY = '__hl_bm';
export const BOOKMARK_HEADER = 'X-D1-Bookmark';
export function publicReadEligible(request, url = new URL(request.url)) {
  if (request.method !== 'GET' || request.headers.get('X-Monthly-Scan')) return false;
  if (/^\/api\/(?:boards|posts)$/.test(url.pathname)) return !url.searchParams.has('view');
  return /^\/api\/(?:monthly|weekly|rank)$/.test(url.pathname)
    && !request.headers.get('Authorization') && !request.headers.get('Cookie') && !request.headers.get('X-Lab-Token');
}
export function primaryCheckpointRequest(request, url = new URL(request.url)) {
  if (request.method === 'GET') return /^\/api\/(?:boards|posts|monthly|weekly|rank)$/.test(url.pathname);
  if (['HEAD', 'OPTIONS'].includes(request.method)) return false;
  // Monthly attempts, grading, financial and exam writes keep the original primary binding.
  return /^\/api\/(?:posts|comments|me)(?:\/|$)/.test(url.pathname);
}
export function requestBookmark(url) {
  const value = url.searchParams.get(BOOKMARK_QUERY);
  if (value === null) return null;
  if (!/^[\x21-\x7e]{1,2048}$/.test(value)) throw new Error('invalid public bookmark');
  return value;
}
export function selectOnly(db) {
  return {
    prepare(sql) {
      if (!/^\s*SELECT\b/i.test(sql) || sql.includes(';')) throw new Error('public read lane permits SELECT only');
      return db.prepare(sql);
    },
    batch(statements) { return db.batch(statements); },
  };
}
