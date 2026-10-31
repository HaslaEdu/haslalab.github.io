/* How long a HaslaLab exam (exam mode) lasts.  The community worker keeps the same table in
   labExamSec (community/src/index.js), and its clock is the one that counts: keep the two alike.

   - IPhO, APhO, EuPhO and the rest: five hours, as the experimental exam on the day.
   - Physics Cup, Ortvay, OPhO and WOPHO use untimed review only. USAPhO 2022: «3 hours allowed».
   - RMPh: 4 h 30 min, the length of a contest day in its regulation.
   - NBPhO: the organisers publish no time for the experiments alone, so the exam gets the year's
     competition time shared out evenly over its problems, times the experiments sat:
     total / problems × experiments.  The competition was one five-hour round in 2003–2005 and online
     in 2020–2021, and two five-hour rounds in the other years (each round ends with its experiment).
   - IZhO: the experimental round's own length on its paper — 3 hours, 4 hours in 2022, 2023 and 2026
     (2021, a computer experiment done by hand, states none: 3 hours).
   - A theory exam (the year's written paper, sat at once): five hours as at IPhO, APhO, IChO, IOAA and most others;
     three hours for USAPhO, IJSO, IBO, IESO and OPhO, whose theory papers are shorter, and for the CPhO final's theory
     and each round of USAAAO, USESO and JESO; nine hours for an IMO paper (its two days of 4 h 30 min); RuPhO's
     final, five hours a grade. IOI is not sat in exam mode (its tasks are programs).
   - NBPhO's combined exam (its experiments and the rest of its booklet, as on the day): the year's whole competition time. */
(function () {
  var NBPHO = { 2003: [300, 8], 2004: [300, 9], 2005: [300, 9], 2006: [600, 8], 2007: [600, 8], 2008: [600, 10],
    2009: [600, 10], 2010: [600, 11], 2011: [600, 9], 2012: [600, 10], 2013: [600, 10], 2014: [600, 10], 2015: [600, 10],
    2016: [600, 10], 2017: [600, 10], 2018: [600, 9], 2019: [600, 8], 2020: [300, 5], 2021: [300, 4], 2022: [600, 9],
    2023: [600, 9], 2024: [600, 10], 2025: [600, 9], 2026: [600, 10] };
  var THEORY = { usapho: 3 * 3600, ijso: 3 * 3600, ibo: 3 * 3600, ieso: 3 * 3600, opho: 3 * 3600,
    cpho: 3 * 3600, imo: 9 * 3600, usaaao: 3 * 3600, useso: 3 * 3600, jeso: 3 * 3600, plancks: 4 * 3600 };
  function sec(comp, year, n, theory) {
    if (['physcup', 'ortvay', 'opho', 'wopho'].indexOf(comp) >= 0) return 0;
    if (comp === 'plancks' && +year === 2021 && theory) return 16 * 3600;
    if (theory === 'mixed') return comp === 'nbpho' && NBPHO[year] ? NBPHO[year][0] * 60 : 5 * 3600;   // NBPhO's whole booklet at once
    if (theory) return THEORY[comp] || 5 * 3600;
    n = Math.max(1, n || 1);
    if (comp === 'usapho' && +year === 2022) return 3 * 3600;
    if (comp === 'rmph') return 4.5 * 3600;
    if (comp === 'nbpho' && NBPHO[year]) return Math.round(NBPHO[year][0] / NBPHO[year][1] * n) * 60;
    if (comp === 'izho') return ([2022, 2023, 2026].indexOf(+year) >= 0 ? 4 : 3) * 3600;
    return 5 * 3600;
  }
  /* «5시간», «2시간 13분» / «5 hours», «2 h 13 min» */
  function text(s, lang) {
    var m = Math.round(s / 60), h = Math.floor(m / 60); m %= 60;
    if (lang === 'en') return h && m ? h + ' h ' + m + ' min' : h ? h + (h === 1 ? ' hour' : ' hours') : m + ' minutes';
    return (h ? h + '시간' : '') + (h && m ? ' ' : '') + (m ? m + '분' : '');
  }
  /* «5:00» */
  function clock(s) { var m = Math.round(s / 60); return Math.floor(m / 60) + ':' + String(m % 60).padStart(2, '0'); }
  window.HLexam = { sec: sec, text: text, clock: clock };
})();
