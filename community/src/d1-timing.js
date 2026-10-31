export const createD1Metrics = () => ({ n: 0, ms: 0, sqlMs: 0, sqlSamples: 0, rows: 0, regions: new Set(), colos: new Set(), locations: new Set(), hits: 0, misses: 0 });
export function timedDB(db, q) {
  const record = result => {
    for (const item of Array.isArray(result) ? result : [result]) {
      const meta = item?.meta;
      if (!meta) continue;
      if (Number.isFinite(meta.timings?.sql_duration_ms)) { q.sqlMs += meta.timings.sql_duration_ms; q.sqlSamples++; }
      if (Number.isFinite(meta.rows_read)) q.rows += meta.rows_read;
      if (meta.served_by_region) q.regions.add(String(meta.served_by_region).replace(/[^A-Za-z0-9_-]/g, '').slice(0, 24));
      if (/^[A-Z]{3}$/.test(meta.served_by_colo || '')) q.colos.add(meta.served_by_colo);
      if (typeof meta.served_by_primary === 'boolean') q.locations.add(meta.served_by_primary ? 'primary' : 'replica');
    }
    return result;
  };
  const time = async run => { const at = Date.now(); try { return record(await run()); } finally { q.n++; q.ms += Date.now() - at; } };
  const wrap = statement => new Proxy(statement, { get(target, key) {
    if (key === 'bind') return (...args) => wrap(target.bind(...args));
    if (key === 'first') return async column => {
      const result = await time(() => target.all()), row = result.results?.[0] || null;
      if (!row || column === undefined) return row;
      if (!Object.hasOwn(row, column)) throw new Error('D1_ERROR: column not found');
      return row[column];
    };
    if (['all', 'run', 'raw'].includes(key)) return (...args) => time(() => target[key](...args));
    const value = target[key]; return typeof value === 'function' ? value.bind(target) : value;
  } });
  return new Proxy(db, { get(target, key) {
    if (key === 'prepare') return sql => wrap(target.prepare(sql));
    if (key === 'batch') return statements => time(() => target.batch(statements));
    const value = target[key]; return typeof value === 'function' ? value.bind(target) : value;
  } });
}
export function d1Timing(q, elapsed) {
  const sql = q.sqlSamples ? `, sql;desc="${q.sqlSamples} statements";dur=${q.sqlMs.toFixed(3)}, d1_read;desc="${q.rows} rows"` : '';
  const region = q.regions.size ? `, d1_region;desc="${[...q.regions, ...q.locations].join(' ')}"` : '';
  const colo = q.colos.size ? `, d1_colo;desc="${[...q.colos].join(' ')}"` : '';
  return `db;desc="${q.n} queries";dur=${q.ms}, total;dur=${elapsed}${sql}${region}${colo}, public_cache;desc="${q.hits} hits ${q.misses} misses"`;
}
