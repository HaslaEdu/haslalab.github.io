/* Build developer selections from the same authoritative papers and experiment
 * groups as the archive. No URLs or scoring criteria come from browser input. */
const {isIP} = require('node:net');
const PDF_BASE = 'https://haslalab-pdf.haslalab.workers.dev/pdf/';
const SITE_BASE = 'https://haslalab.org/';
const taskPattern = /^(?:[A-Z][A-Za-z0-9]{0,3})$/;
const filename = /^[A-Za-z][A-Za-z0-9_.-]{1,140}\.pdf$/;
function source(value) {
  if (typeof value !== 'string') return null;
  let text = value.trim();
  if (text.startsWith(PDF_BASE)) text = text.slice(PDF_BASE.length);
  if (text.startsWith(SITE_BASE + 'pdfx/')) text = text.slice(SITE_BASE.length);
  if (filename.test(text) && !text.includes('..')) return text;
  if (/^pdfx\/[a-z0-9-]+\/[A-Za-z][A-Za-z0-9_.-]{1,140}\.pdf$/.test(text) && !text.includes('..')) return text;
  try {
    const url = new URL(text), host = url.hostname.toLowerCase();
    if (url.protocol !== 'https:' || url.username || url.password || url.port || url.hash ||
        !host.includes('.') || isIP(host.replace(/^\[|\]$/g, '')) || /(?:^|\.)(?:localhost|local|internal|invalid|test|onion)$/.test(host) || text.length > 2048) return null;
    return url.href;
  } catch { return null; }
}
function pick(value) {
  return typeof value === 'string' ? value : value && (value.en || value.ko || Object.values(value).find(x => typeof x === 'string'));
}
const label = (value, fallback = '') => ({
  ko: String(typeof value === 'string' ? value : value?.ko || value?.en || fallback).slice(0, 500),
  en: String(typeof value === 'string' ? value : value?.en || value?.ko || fallback).slice(0, 500),
});
const yearOK = year => /^(?:19|20)\d{2}(?:-\d{1,2})?$/.test(String(year));
function buildModelTestCatalogue(data, {thyOf, theoryGroups, examGroups, examTask, contests = {entries:[]}}) {
  const records = new Map();
  const add = record => {
    if (!record.paper || !yearOK(record.year) || !taskPattern.test(record.task)) return;
    if (!/^[a-z0-9][a-z0-9-]{1,139}$/i.test(record.id || '')) throw new Error('Invalid developer paper ID');
    const previous = records.get(record.id);
    if (previous && JSON.stringify(previous) !== JSON.stringify(record)) throw new Error('Ambiguous developer paper: ' + record.id);
    records.set(record.id, record);
  };
  const common = (comp, competition, year, task, kind) => ({
    id: `${comp}-${year}-${task}`, comp, year, task, kind,
    competition: label(competition.full, competition.abbr || comp.toUpperCase()),
    problemNo: null, skip: [], wholePaper: !!competition.rounds || !!competition.omr || /^(?:T|MC|E)[a-z]?$/.test(task), answerSheets: [],
  });
  const contestComps = new Set((contests.entries || []).map(entry => entry.comp));
  for (const [comp, competition] of Object.entries(data)) {
    if (comp === 'ioi' || contestComps.has(comp)) continue;
    for (const year of competition.years || []) {
      if (!yearOK(year.y)) continue;
      const theory = thyOf(comp, year.y), files = theory?.f || {};
      // Preserve the portal's task choices first. Also expose published papers
      // with no solution for explicitly unscored developer feedback.
      const portal = new Set((theoryGroups(comp, year) || []).flat());
      for (const task of Object.keys(files)) if (/^(?:T|MC)\d*[a-z]?$/.test(task) && !files[task].kx) portal.add(task);
      for (const task of portal) {
        const file = files[task]; if (!file || file.kx) continue;
        const paper = source(pick(file.paper)); if (!paper) continue;
        const solution = source(pick(file.sol)), mark = source(pick(file.mark || file.key));
        const english = (theory.p || []).find(row => row[0] === task)?.[1] || '';
        const korean = (theory.pk || []).find(row => row[0] === task)?.[1] || english;
        const title = label({ko:korean || task, en:english || task});
        const paperKo = source(file.ko?.paper || file.papers?.ko);
        add({...common(comp, competition, year.y, task, 'theory'), title, paper,
          ...(paperKo && paperKo !== paper ? {paperKo} : {}), solution, mark,
          ...(Number.isInteger(file.paperPage) && file.paperPage > 0 ? {paperPage:file.paperPage} : {}),
          ...(Number.isInteger(file.paperLastPage) && file.paperLastPage > 0 ? {paperLastPage:file.paperLastPage} : {}),
          skip: comp === 'nbpho' && task === 'T' ? (theory.x || []).map(String) : [],
          answerSheets: [...new Set([source(file.ko?.answer), source(pick(file.answer))].filter(Boolean))],
          referenceStatus: comp === 'kphe' && solution ? 'independent' : solution || mark ? 'published' : 'problem-only'});
      }
      for (const group of examGroups(comp, year) || []) for (const problem of group) {
        const task = examTask(problem);
        // The theory member of a mixed NBPhO sitting is already represented above.
        if (problem.thy) continue;
        const paper = source(pick(problem.files?.pdf)); if (!paper) continue;
        const solution = source(pick(problem.files?.sol));
        const record = {...common(comp, competition, year.y, task, problem.theory ? 'theory' : 'experiment'),
          title: label(problem.title, task), paper, solution, mark:null,
          problemNo: Number.isInteger(problem.no) ? problem.no : null,
          referenceStatus: solution ? 'published' : 'problem-only'};
        const paperKo = source(problem.files?.pdf?.ko);
        if (paperKo && paperKo !== paper) record.paperKo = paperKo;
        // A simulator-backed theory task can have additional paper metadata.
        const previous = records.get(record.id);
        if (!previous) add(record);
        else if (previous.paper !== record.paper) throw new Error('Different papers for developer task: ' + record.id);
      }
    }
  }
  for (const entry of contests.entries || []) {
    const competition = data[entry.comp];
    if (!competition || entry.practice === false || !taskPattern.test(entry.part || '')) continue;
    const paper = source(entry.paper); if (!paper) continue;
    const solution = source(entry.solution);
    const record = {...common(entry.comp, competition, entry.year, entry.part, 'theory'),
      id:entry.id,
      title:label(entry.title, entry.part), paper, solution, mark:null, wholePaper:true,
      questions:entry.questions || null, questionOffset:entry.questionOffset || 0,
      questionNumbers:Number.isInteger(entry.questions) ? Array.from({length:entry.questions}, (_,i) => (entry.questionOffset || 0) + i + 1) : [],
      ...(Number.isInteger(entry.paperPage) && entry.paperPage > 0 ? {paperPage:entry.paperPage} : {}),
      ...(Number.isInteger(entry.paperLastPage) && entry.paperLastPage > 0 ? {paperLastPage:entry.paperLastPage} : {}),
      referenceStatus: solution ? 'published' : 'problem-only'};
    // Exact, reviewed objective keys are public source data, never inferred equal weights.
    if (entry.answersVerified === true && entry.scoringVerified === true && Array.isArray(entry.answers) && entry.answers.length === entry.questions) {
      record.verifiedScoring = {kind:entry.kind, questions:entry.questions, questionOffset:entry.questionOffset || 0,
        answers:entry.answers, ...(Array.isArray(entry.points) ? {points:entry.points} : {point:entry.point}),
        penalty:entry.penalty || 0, excluded:entry.excluded || [], fullCredit:entry.fullCredit || []};
      record.referenceStatus = 'published';
    }
    add(record);
  }
  return [...records.values()].sort((a,b) => a.comp.localeCompare(b.comp) || String(b.year).localeCompare(String(a.year),'en',{numeric:true}) || a.task.localeCompare(b.task,'en',{numeric:true}));
}
module.exports = {buildModelTestCatalogue, source};
