/* Which medal the experiment alone would have earned: the candidate's exam-mode score, scaled to the olympiad's
   experimental marks, ranked among the experimental scores of that year's contestants (labmedals.json, from
   tools/labmedals.py), with that year's numbers of gold, silver, bronze and honourable mentions given out by rank.
   Used by the score report (arena.js) and the receipt (exam.html).
   labMedal.load(url) → data;  labMedal.estimate(data, comp, year, score, points, tasks) → null | {...};
   labMedal.html(est, lang) → a small block. */
(function () {
  "use strict";
  let P = null;
  const load = url => P || (P = fetch(url).then(r => (r.ok ? r.json() : null)).catch(() => null));
  /* the experiments of a year in exam mode: IPhO and APhO have one or two; a sitting of fewer than the year has
     (a year whose other experiment has no simulator) is scaled from the fraction it scored */
  function estimate(data, comp, year, score, points, tasks) {
    const d = data && data[comp] && data[comp][String(year)];
    if (!d || !(points > 0) || !d.exp || !d.exp.length) return null;
    const mine = Math.round((score / points) * d.max * 100) / 100;
    const rank = d.exp.filter(x => x > mine).length + 1;            // ties share the better place
    const g = d.g, s = g + d.s, b = s + d.b, hm = b + d.hm;
    const medal = rank <= g ? "g" : rank <= s ? "s" : rank <= b ? "b" : rank <= hm ? "hm" : "none";
    const cut = k => (d.exp.length >= k && k > 0 ? d.exp[k - 1] : null);
    return { comp, year: +year, mine, max: d.max, rank, of: d.exp.length, medal, complete: d.complete,
      cuts: { g: cut(g), s: cut(s), b: cut(b), hm: cut(hm) }, tasks: tasks || [] };
  }
  const T = {
    ko: { h: "실험만으로 본 메달권", medal: { g: "금메달권", s: "은메달권", b: "동메달권", hm: "장려상권", none: "수상권 밖" },
      line: e => `실험 ${e.mine} / ${e.max}점으로 환산하면, 공개된 ${e.year}년 실험 점수 ${e.of}개 가운데 ${e.rank}등입니다.`,
      cuts: "실험 점수 기준선 (그해 메달 수를 실험 순위로 나눴을 때)", g: "금", s: "은", b: "동", hm: "장려",
      note: e => (e.complete ? "" : "공개된 기록에는 수상자의 점수만 있어, 순위는 실제보다 좋게 나올 수 있습니다. ") +
        "실제 메달은 이론과 실험의 합계로 정해지므로 참고용 추정입니다.", src: "자료: IPhO 비공식 기록(ipho-unofficial.org), APhO 공식 결과" },
    en: { h: "Medal on the experiment alone", medal: { g: "gold", s: "silver", b: "bronze", hm: "honourable mention", none: "no award" },
      line: e => `Scaled to ${e.mine} / ${e.max}, your experiment ranks ${e.rank} among the ${e.of} published experimental scores of ${e.year}.`,
      cuts: "Experimental cut-offs (that year's medal numbers, ranked by the experiment)", g: "gold", s: "silver", b: "bronze", hm: "HM",
      note: e => (e.complete ? "" : "The published records hold the award winners' scores only, so the rank may look better than it was. ") +
        "Real medals go by the total of theory and experiment; this is an estimate.", src: "Data: IPhO unofficial records (ipho-unofficial.org), APhO official results" },
  };
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const COL = { g: "#d4a017", s: "#a8b2bd", b: "#b4703c", hm: "#6c9bd2", none: "#7a828a" };
  function html(e, lang) {
    if (!e) return "";
    const L = T[lang === "en" ? "en" : "ko"];
    const cut = ["g", "s", "b", "hm"].filter(k => e.cuts[k] != null).map(k => `${L[k]} ${e.cuts[k]}`).join(" · ");
    return `<div class="lbmedal" data-medal="${e.medal}" style="margin-top:12px;border:1px solid ${COL[e.medal]};border-radius:10px;padding:10px 12px">
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap"><b style="font-size:13px">${esc(L.h)}</b>
        <span style="background:${COL[e.medal]};color:#111;border-radius:999px;padding:2px 10px;font-weight:700;font-size:13px">${esc(e.comp.toUpperCase())} ${e.year} · ${esc(L.medal[e.medal])}</span></div>
      <div style="font-size:13px;margin-top:6px">${esc(L.line(e))}</div>
      ${cut ? `<div style="font-size:12.5px;margin-top:4px;opacity:.85">${esc(L.cuts)}: ${esc(cut)}</div>` : ""}
      <div style="font-size:11.5px;margin-top:6px;opacity:.7">${esc(L.note(e))} ${esc(L.src)}</div></div>`;
  }
  window.labMedal = { load, estimate, html };
})();
