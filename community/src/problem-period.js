// The storage column remains `week` so existing problems and submissions keep their ids.
export const CURRENT_MONTHLY_PERIOD = '2026-11';
export const LEGACY_MONTHLY_PERIOD = '2026-W44';
// Exclusive cutoff: 2026-12-01 00:00:00 Asia/Seoul (November 30 remains open in full).
export const MONTHLY_CLOSES_AT = Date.parse('2026-12-01T00:00:00+09:00') / 1000;
export const isMonthPeriod = value => /^\d{4}-(?:0[1-9]|1[0-2])$/.test(value || '');
export const isProblemPeriod = value => isMonthPeriod(value) || /^\d{4}-W(?:0[1-9]|[1-4]\d|5[0-3])$/.test(value || '');
export const canonicalProblemPeriod = value => value === LEGACY_MONTHLY_PERIOD ? CURRENT_MONTHLY_PERIOD : value;
export function isoMonth(t) {
  const date = new Date((t + 9 * 3600) * 1000);
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}`;
}
