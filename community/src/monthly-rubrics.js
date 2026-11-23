/* The hand-built monthly rubrics, bundled into the Worker. They used to be read back from the public site
   (community/weekly/rubrics-<month>/<id>.json); they are private marking schemes, so the site no longer publishes
   community/weekly/ at all. Add each new month's files here (test-monthly-rubrics.mjs checks that none is missing). */
import r2026_11_4 from '../weekly/rubrics-2026-11/4.json' with { type: 'json' };
import r2026_11_5 from '../weekly/rubrics-2026-11/5.json' with { type: 'json' };
import r2026_11_6 from '../weekly/rubrics-2026-11/6.json' with { type: 'json' };
import r2026_11_7 from '../weekly/rubrics-2026-11/7.json' with { type: 'json' };
import r2026_11_8 from '../weekly/rubrics-2026-11/8.json' with { type: 'json' };
export const MONTHLY_RUBRICS = {
  '2026-11': {4: r2026_11_4, 5: r2026_11_5, 6: r2026_11_6, 7: r2026_11_7, 8: r2026_11_8},
};
export const monthlyRubric = (week, id) => MONTHLY_RUBRICS[week]?.[id] ?? null;
