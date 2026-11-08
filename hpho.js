/* HPhO page (#/hpho): what the contest is, the next round in the visitor's own time zone, and registration.
   The server (community/src/hpho.js) holds rounds and entries; index.html's render() calls HL_HPHO.view() and, once the
   page is in the document, HL_HPHO.mount(). */
(() => {
  const L = () => (typeof lang === "string" && lang === "en") ? "en" : "ko";
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const COUNTRIES = "AD AE AF AG AI AL AM AO AR AS AT AU AW AZ BA BB BD BE BF BG BH BI BJ BM BN BO BR BS BT BW BY BZ CA CD CF CG CH CI CK CL CM CN CO CR CU CV CW CY CZ DE DJ DK DM DO DZ EC EE EG ER ES ET FI FJ FM FO FR GA GB GD GE GH GI GL GM GN GQ GR GT GU GW GY HK HN HR HT HU ID IE IL IN IQ IR IS IT JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MG MH MK ML MM MN MO MR MT MU MV MW MX MY MZ NA NC NE NG NI NL NO NP NR NZ OM PA PE PF PG PH PK PL PR PS PT PW PY QA RO RS RU RW SA SB SC SD SE SG SI SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TG TH TJ TL TM TN TO TR TT TV TW TZ UA UG US UY UZ VA VC VE VG VI VN VU WS XK YE ZA ZM ZW".split(" ");
  /* the server's AID_AUTO_COUNTRIES (community/src/hpho.js): the fee is waived there without asking */
  /* fee assistance is on hold (community/src/hpho.js AID_ENABLED): its section and form fields are not shown */
  const AID_ON = false;
  const AID_AUTO = new Set("AF BF BI CF TD CD ER ET GM GW KP LR MG MW ML MZ NE RW SL SO SS SD SY TG UG YE AO BD BJ BT BO KH CM CV KM CG CI DJ EG SZ GH GN HT HN IN KE KI KG LA LB LS MR FM MA MM NP NI NG PK PG PH WS ST SN SB LK TJ TZ TL TN UZ VU VN PS ZM ZW".split(" "));
  const T = {
    ko: {
      tabMonthly: "월별문제", tabHpho: "HPhO", eyebrow: "HaslaLab Physics Olympiad",
      title: "HPhO", lead: "올림피아드를 실제로 겪어보는 연습 대회입니다.",
      note: "HPhO는 입시나 수상 실적을 위한 공인 대회가 아닙니다. 새로운 주제의 문제를 실전처럼 풀어보는 경험을 위해 HaslaEdu가 직접 출제합니다.",
      facts: [["개인전", "혼자 응시합니다"], ["반기 1회", "1년에 두 번 열립니다"], ["이론 + 실험", "실험은 하슬라랩 가상 실험대에서"], ["전 세계 동시", "모든 참가자가 같은 시각에 시작합니다"], ["AI 채점", "채점 후 이의신청 기간이 있습니다"]],
      next: "다음 대회", none: "첫 대회 일정은 곧 공개됩니다.", regOpen: "접수", regClose: "접수 마감", start: "시험 시작", length: "시험 시간", min: "분", fee: "참가비", free: "무료",
      localTz: z => `내 시간대(${z}) 기준`, until: "남음", d: "일", h: "시간", m: "분",
      status: { open: "접수 중", closed: "접수 마감", finished: "종료", soon: "접수 예정" },
      signIn: "접수하려면 로그인하세요.", login: "로그인",
      formTitle: "참가 접수", country: "국가", level: "과정", levels: { middle: "중학생", high: "고등학생", university: "대학생", other: "기타" }, birth: "출생 연도",
      pledge: "대회 규정을 읽었고, 시험 중 다른 사람·AI·인터넷·교재의 도움을 받지 않겠습니다.",
      proctor: "시험은 하슬라에듀 데스크톱 앱으로 응시하며, 웹캠·화면·실행 중인 프로그램이 감독 목적으로 기록되는 데 동의합니다.",
      identity: "답안지에는 수험번호만 적습니다. 이름·학교 등 신원 정보를 적어 생기는 일은 제 책임입니다.",
      guardian: "만 19세 미만이며, 보호자가 참가와 감독 기록에 동의했습니다.",
      submit: "접수하기", update: "접수 내용 수정", withdraw: "접수 취소", withdrawAsk: "접수를 취소할까요?",
      mine: "접수 완료", candidate: "수험번호", candidateNote: "답안지에는 이 수험번호만 적으세요.",
      rulesTitle: "규정 요약",
      rules: [
        "답안지에는 수험번호만 적습니다. 이름·학교 등 신원을 알 수 있는 정보는 적지 마세요. 적어서 생기는 불이익은 본인 책임입니다.",
        "시험 중에는 다른 사람, AI, 인터넷 검색, 교재의 도움을 받을 수 없습니다.",
        "시험은 하슬라에듀 Windows 데스크톱 앱의 감독 모드로 응시합니다. 웹캠과 화면, 창 전환과 실행 중인 프로그램이 기록됩니다.",
        "AI는 의심 장면을 표시만 하며, 실격 여부는 사람이 검토해 결정합니다. 감독 기록은 결과 확정 후 정해진 기간이 지나면 삭제됩니다.",
        "답안은 AI가 채점하고, 결과 공개 후 이의신청 기간이 있습니다. 입상 후보에게는 짧은 화상 확인을 요청할 수 있습니다.",
      ],
      aidTitle: "참가비 지원",
      aidIntro: "비용 때문에 HPhO를 포기하는 학생이 없도록 참가비를 지원합니다.",
      aidRules: ["세계은행 기준 저소득·중저소득 국가에서 응시하면 신청 없이 참가비가 면제됩니다.", "그 밖의 학생은 접수할 때 ‘참가비 지원 신청’을 고르고 사유를 적어 주세요. 증빙 서류는 받지 않습니다.", "HaslaEdu가 접수 마감 전까지 검토해 결과를 이 페이지에 알려드립니다. 지원 여부는 채점이나 결과에 전혀 영향을 주지 않습니다.", "적어 주신 사유는 심사에만 쓰고, 대회가 끝나면 삭제합니다."],
      aidAuto: "이 국가에서는 참가비가 자동으로 면제됩니다.", aidAsk: "참가비 지원을 신청합니다.", aidReason: "사유", aidNote: "간단한 설명 (10~300자)",
      aidReasons: { family_income: "가계 형편이 어려움", public_assistance: "기초생활수급·차상위 등 공공 지원 대상", school_referral: "학교·기관의 추천", other: "기타" },
      feeLabel: "참가비", feeState: { auto: "면제 (자동)", pending: "지원 심사 중", approved: "면제 (지원 승인)", declined: "지원 미승인 · 납부 필요", none: "납부 필요" },
      saved: "접수되었습니다.", err: "처리하지 못했습니다: ",
      errors: { bad_aid_reason: "지원 사유를 고르세요.", aid_note_required: "지원 사유를 10자 이상 적어 주세요.", bad_country: "국가를 고르세요.", bad_level: "과정을 고르세요.", bad_birth_year: "출생 연도를 확인하세요.", pledge_required: "규정 서약에 동의해야 합니다.", proctoring_consent_required: "감독 기록에 동의해야 합니다.", identity_notice_required: "답안지 안내를 확인해야 합니다.", guardian_consent_required: "만 19세 미만은 보호자 동의가 필요합니다.", registration_closed: "접수 기간이 아닙니다.", login_required: "로그인이 필요합니다." },
    },
    en: {
      tabMonthly: "Monthly", tabHpho: "HPhO", eyebrow: "HaslaLab Physics Olympiad",
      title: "HPhO", lead: "A practice olympiad that feels like the real thing.",
      note: "HPhO is not an accredited contest and is not meant for admissions or award records. HaslaEdu writes it so you can meet new topics and sit a paper under real conditions.",
      facts: [["Individual", "You sit it on your own"], ["Twice a year", "One round each half-year"], ["Theory + experiment", "Experiments on the HaslaLab virtual bench"], ["Same time worldwide", "Everyone starts at the same moment"], ["AI-marked", "With a window for appeals"]],
      next: "Next round", none: "The first round's dates will be announced soon.", regOpen: "Registration opens", regClose: "Registration closes", start: "Exam starts", length: "Duration", min: "min", fee: "Fee", free: "Free",
      localTz: z => `in your time zone (${z})`, until: "left", d: "d", h: "h", m: "m",
      status: { open: "Registration open", closed: "Registration closed", finished: "Finished", soon: "Opens soon" },
      signIn: "Sign in to register.", login: "Sign in",
      formTitle: "Register", country: "Country", level: "Level", levels: { middle: "Middle school", high: "High school", university: "University", other: "Other" }, birth: "Year of birth",
      pledge: "I have read the rules and will take no help from people, AI, the internet or books during the exam.",
      proctor: "I will sit the exam in the HaslaEdu desktop app and agree that my webcam, screen and running programs are recorded for proctoring.",
      identity: "I will write only my candidate number on the answer sheets. Anything identifying I write is my own responsibility.",
      guardian: "I am under 19 and a parent or guardian has agreed to my taking part and to the proctoring records.",
      submit: "Register", update: "Update registration", withdraw: "Withdraw", withdrawAsk: "Withdraw your registration?",
      mine: "Registered", candidate: "Candidate number", candidateNote: "Write only this number on your answer sheets.",
      rulesTitle: "Rules in brief",
      rules: [
        "Write only your candidate number on the answer sheets. Do not write your name, school or anything that identifies you; anything you write is your own responsibility.",
        "No help from other people, AI, internet search or books during the exam.",
        "The exam is sat in the proctoring mode of the HaslaEdu Windows desktop app. Your webcam, screen, window switches and running programs are recorded.",
        "AI only flags moments; a person reviews every flag before any disqualification. Proctoring records are deleted a set time after results are final.",
        "Answers are marked by AI, with an appeal window after results. Prize candidates may be asked for a short video check.",
      ],
      aidTitle: "Fee assistance",
      aidIntro: "No student should miss HPhO because of the fee.",
      aidRules: ["Candidates in a low- or lower-middle-income economy (World Bank classification) pay nothing, without asking.", "Anyone else can tick ‘Request fee assistance’ when registering and give a reason. No documents are needed.", "HaslaEdu reviews requests before registration closes and shows the decision on this page. Assistance never affects marking or results.", "Your reason is used only for the review and is deleted after the round."],
      aidAuto: "The fee is waived automatically for this country.", aidAsk: "I request fee assistance.", aidReason: "Reason", aidNote: "A short explanation (10–300 characters)",
      aidReasons: { family_income: "My family cannot easily afford it", public_assistance: "I receive public financial assistance", school_referral: "Referred by my school or an organisation", other: "Other" },
      feeLabel: "Fee", feeState: { auto: "Waived (automatic)", pending: "Assistance under review", approved: "Waived (assistance approved)", declined: "Assistance declined · fee due", none: "Fee due" },
      saved: "You are registered.", err: "Could not complete: ",
      errors: { bad_aid_reason: "Choose a reason for assistance.", aid_note_required: "Please explain in at least 10 characters.", bad_country: "Choose your country.", bad_level: "Choose your level.", bad_birth_year: "Check your year of birth.", pledge_required: "You must accept the pledge.", proctoring_consent_required: "You must agree to proctoring.", identity_notice_required: "Please confirm the answer-sheet notice.", guardian_consent_required: "Under 19: a guardian's consent is required.", registration_closed: "Registration is not open.", login_required: "Please sign in." },
    },
  };
  let state = { data: null, error: null, busy: false };

  const tz = () => { try { return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"; } catch (e) { return "UTC"; } };
  const when = s => new Date(s * 1000).toLocaleString(L() === "en" ? "en-GB" : "ko-KR", { dateStyle: "medium", timeStyle: "short" });
  const countryName = (() => { let dn = null; return c => { try { dn = dn && dn.lang === L() ? dn : Object.assign(new Intl.DisplayNames([L()], { type: "region" }), { lang: L() }); return dn.of(c); } catch (e) { return c; } }; })();
  function left(s, t) {
    const x = T[L()], sec = Math.max(0, s - Math.floor(Date.now() / 1000)), d = Math.floor(sec / 86400), h = Math.floor(sec % 86400 / 3600), m = Math.floor(sec % 3600 / 60);
    return (d ? d + x.d + " " : "") + h + x.h + " " + m + x.m + " " + x.until;
  }
  function roundStatus(r) {
    const t = Math.floor(Date.now() / 1000);
    if (r.status === "finished" || t >= r.start_at + r.duration_min * 60) return "finished";
    if (r.status === "open" && t < r.reg_open) return "soon";
    if (r.status === "open" && t < r.reg_close) return "open";
    return "closed";
  }

  function view() {
    const x = T[L()];
    return `<div class="shell hpho">
      <nav class="hpho-tabs" aria-label="${x.tabHpho}"><a href="#/monthly">${x.tabMonthly}</a><a href="#/hpho" aria-current="page">${x.tabHpho}</a></nav>
      <div class="phead"><p class="eyebrow">${x.eyebrow}</p><h1>${x.title}</h1><div class="sub">${x.lead}</div></div>
      <p class="hpho-note">${x.note}</p>
      <ul class="hpho-facts">${x.facts.map(([a, b]) => `<li><b>${a}</b><span>${b}</span></li>`).join("")}</ul>
      <section class="hpho-round" id="hphoRound" aria-live="polite"><p class="hpho-muted">…</p></section>
      ${AID_ON ? `<section class="hpho-rules"><h2>${x.aidTitle}</h2><p>${x.aidIntro}</p><ul>${x.aidRules.map(r => `<li>${r}</li>`).join("")}</ul></section>` : ""}
      <section class="hpho-rules"><h2>${x.rulesTitle}</h2><ol>${x.rules.map(r => `<li>${r}</li>`).join("")}</ol></section>
    </div>`;
  }

  function roundHtml() {
    const x = T[L()], d = state.data;
    if (state.error) return `<p class="hpho-muted">${esc(x.err + state.error)}</p>`;
    if (!d) return `<p class="hpho-muted">…</p>`;
    const r = d.rounds.find(r => roundStatus(r) !== "finished") || null;
    if (!r) return `<h2>${x.next}</h2><p class="hpho-muted">${x.none}</p>`;
    const st = roundStatus(r), mine = d.entries?.[r.id], me = typeof cm === "object" && cm ? cm.me : null;
    const rows = [[x.regOpen, when(r.reg_open)], [x.regClose, when(r.reg_close)], [x.start, `${when(r.start_at)} <small>(${left(r.start_at)})</small>`], [x.length, r.duration_min + x.min], [x.fee, r.fee_usd ? "$" + r.fee_usd.toFixed(2) : x.free]];
    let action;
    if (mine) action = `<div class="hpho-mine"><p class="hpho-badge">${x.mine}</p><p>${x.candidate}: <b class="hpho-no">${esc(mine.candidate_no)}</b></p><p class="hpho-muted">${x.candidateNote}</p>
      <p><a class="hpho-btn" href="#/hpho/exam">${L() === "en" ? "Technical check · exam room" : "기술 점검 · 시험장 입장"}</a></p>
      ${r.fee_usd ? `<p>${x.feeLabel}: <b>${x.feeState[mine.aid] || x.feeState.none}</b>${mine.fee_due ? ` · $${Number(mine.fee_due).toFixed(2)}` : ""}</p>` : ""}
      ${st === "open" ? `<details><summary>${x.update}</summary>${formHtml(r, mine)}</details><button type="button" class="hpho-link" data-hpho-withdraw="${esc(r.id)}">${x.withdraw}</button>` : ""}</div>`;
    else if (st !== "open") action = "";
    else if (!me) action = `<p>${x.signIn} <a class="hpho-btn" href="#/login">${x.login}</a></p>`;
    else action = formHtml(r, null);
    return `<div class="hpho-round-head"><h2>${x.next} · ${esc(r.title[L()])}</h2><span class="hpho-status is-${st}">${x.status[st]}</span></div>
      <p class="hpho-muted">${x.localTz(esc(tz()))}</p>
      <dl class="hpho-times">${rows.map(([a, b]) => `<div><dt>${a}</dt><dd>${b}</dd></div>`).join("")}</dl>${action}`;
  }

  function formHtml(r, mine) {
    const x = T[L()], y = new Date().getUTCFullYear(), years = [];
    for (let v = y - 9; v >= y - 40; v--) years.push(v);
    const opts = COUNTRIES.map(c => [c, countryName(c)]).sort((a, b) => a[0] === "KR" ? -1 : b[0] === "KR" ? 1 : a[1].localeCompare(b[1]));
    const sel = mine || {};
    return `<form class="hpho-form" data-hpho-round="${esc(r.id)}"><h3>${mine ? x.update : x.formTitle}</h3>
      <label>${x.country}<select name="country" required><option value=""></option>${opts.map(([c, n]) => `<option value="${c}"${sel.country === c ? " selected" : ""}>${esc(n)}</option>`).join("")}</select></label>
      <label>${x.level}<select name="level" required><option value=""></option>${Object.entries(x.levels).map(([k, v]) => `<option value="${k}"${sel.level === k ? " selected" : ""}>${v}</option>`).join("")}</select></label>
      <label>${x.birth}<select name="birth_year" required><option value=""></option>${years.map(v => `<option${+sel.birth_year === v ? " selected" : ""}>${v}</option>`).join("")}</select></label>
      <label class="hpho-check"><input type="checkbox" name="pledge" required> ${x.pledge}</label>
      <label class="hpho-check"><input type="checkbox" name="proctoring" required> ${x.proctor}</label>
      <label class="hpho-check"><input type="checkbox" name="identity_notice" required> ${x.identity}</label>
      ${r.fee_usd && AID_ON ? `<div class="hpho-aid"><p class="hpho-muted" data-hpho-aid-auto hidden>${x.aidAuto}</p>
        <div data-hpho-aid-ask><label class="hpho-check"><input type="checkbox" name="aid_request"${sel.aid && sel.aid !== "none" && sel.aid !== "auto" ? " checked" : ""}> ${x.aidAsk}</label>
        <div data-hpho-aid-fields hidden><label>${x.aidReason}<select name="aid_reason"><option value=""></option>${Object.entries(x.aidReasons).map(([k, v]) => `<option value="${k}"${sel.aid_reason === k ? " selected" : ""}>${v}</option>`).join("")}</select></label>
        <label>${x.aidNote}<textarea name="aid_note" maxlength="300" rows="3">${esc(sel.aid_note || "")}</textarea></label></div></div></div>` : ""}
      <label class="hpho-check" data-hpho-guardian hidden><input type="checkbox" name="guardian_consent"> ${x.guardian}</label>
      <p class="hpho-form-msg" role="status"></p>
      <button type="submit" class="hpho-btn">${mine ? x.update : x.submit}</button></form>`;
  }

  async function load() {
    try { if (typeof cmLoadMe === "function") await cmLoadMe(); state.data = await cmApi("GET", "/hpho"); state.error = null; }
    catch (e) { state.error = e?.code || e?.message || "network"; }
    paint();
  }
  function paint() {
    const box = document.getElementById("hphoRound"); if (!box) return;
    box.innerHTML = roundHtml();
    box.querySelectorAll(".hpho-form").forEach(bindForm);
    box.querySelector("[data-hpho-withdraw]")?.addEventListener("click", async e => {
      if (!confirm(T[L()].withdrawAsk)) return;
      try { await cmApi("DELETE", `/hpho/rounds/${encodeURIComponent(e.currentTarget.dataset.hphoWithdraw)}/entry`); } catch (err) { alert(T[L()].err + (err?.message || "")); }
      load();
    });
  }
  function bindForm(form) {
    const x = T[L()], guard = form.querySelector("[data-hpho-guardian]"), msg = form.querySelector(".hpho-form-msg");
    const sync = () => { const y = +form.birth_year.value, minor = y && new Date().getUTCFullYear() - y < 19; guard.hidden = !minor; guard.querySelector("input").required = !!minor; };
    form.birth_year.addEventListener("change", sync); sync();
    const aidBox = form.querySelector(".hpho-aid");
    const syncAid = () => { if (!aidBox) return; const auto = AID_AUTO.has(form.country.value);
      aidBox.querySelector("[data-hpho-aid-auto]").hidden = !auto; aidBox.querySelector("[data-hpho-aid-ask]").hidden = auto;
      const on = !auto && form.aid_request.checked, fields = aidBox.querySelector("[data-hpho-aid-fields]");
      fields.hidden = !on; form.aid_reason.required = on; form.aid_note.required = on; };
    if (aidBox) { form.country.addEventListener("change", syncAid); form.aid_request.addEventListener("change", syncAid); syncAid(); }
    form.addEventListener("submit", async e => {
      e.preventDefault(); if (state.busy) return; state.busy = true; msg.textContent = "…";
      const body = { country: form.country.value, level: form.level.value, birth_year: +form.birth_year.value,
        pledge: form.pledge.checked, proctoring: form.proctoring.checked, identity_notice: form.identity_notice.checked, guardian_consent: form.guardian_consent.checked,
        ...(form.aid_request && form.aid_request.checked && !AID_AUTO.has(form.country.value) ? { aid_request: true, aid_reason: form.aid_reason.value, aid_note: form.aid_note.value } : {}) };
      try { await cmApi("POST", `/hpho/rounds/${encodeURIComponent(form.dataset.hphoRound)}/entry`, body); msg.textContent = x.saved; await load(); }
      catch (err) { const c = err?.code || err?.message || ""; msg.textContent = x.errors[c] || x.err + c; }
      finally { state.busy = false; }
    });
  }
  let timer = 0;
  function mount() {
    clearInterval(timer); state.data = null; load();
    timer = setInterval(() => { if (!document.getElementById("hphoRound")) return clearInterval(timer); if (!document.querySelector(".hpho-form:focus-within")) paint(); }, 60000);
  }
  window.HL_HPHO = { view, mount, roundStatus };
})();
