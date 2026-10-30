// Token arithmetic uses integer tenths. Existing SQLite INTEGER-affinity columns
// accept a fractional token balance; no schema conversion or remote migration is needed.
// A legacy exam_half is added exactly once when a balance is next changed.
export const TOKEN_SCALE = 10;
export function tokenUnits(value) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return null;
  const units = Math.round(value * TOKEN_SCALE);
  return Number.isSafeInteger(units) && Math.abs(value * TOKEN_SCALE - units) < 1e-7 ? units : null;
}
export function tokenBalance(row) {
  const units = Math.round((Number(row?.exam_tokens) || 0) * TOKEN_SCALE) + (row?.exam_half ? 5 : 0);
  return Math.max(0, units) / TOKEN_SCALE;
}
export const tokenSql = (half, prefix = '') => `(CAST(ROUND(COALESCE(${prefix}exam_tokens,0)*10) AS INTEGER)${half ? `+CASE WHEN ${prefix}exam_half<>0 THEN 5 ELSE 0 END` : ''})`;
export const tokenSet = (units, half) => `exam_tokens=(${units})/10.0${half ? ',exam_half=0' : ''}`;
