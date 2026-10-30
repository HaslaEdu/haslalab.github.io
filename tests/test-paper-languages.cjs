const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const PaperLanguages = require('../paper-languages.js');
const root = path.resolve(__dirname, '..');
const window = {};
vm.runInNewContext(fs.readFileSync(path.join(root, 'theory.js'), 'utf8'), {window});
const catalogue = window.THEORY;

// An English layout edition must retain its original Chinese source.
const cpho = catalogue.cpho['2023'].f.T;
assert.match(cpho.papers.zh, /CPhO_2023_T_ZH\.pdf$/);
assert.equal(cpho.papers.en, cpho.paper);
assert.equal(PaperLanguages.files(cpho).ko, cpho.ko.paper);
const ru = catalogue.rupho['2026'].f.T1;
assert.equal(PaperLanguages.files(ru).ru, 'RuPhO_2026_T1_RU.pdf');
const hu = catalogue.eotvos['2026'].f.T;
assert.equal(PaperLanguages.files(hu).hu, 'https://eik.bme.hu/~vanko/fizika/eotvos/Eotvos_2026.pdf');
assert.equal(PaperLanguages.label('ru','en'), 'Русский');
assert.equal(PaperLanguages.label('zh','en'), '中文');
assert.equal(PaperLanguages.label('hu','en'), 'Magyar');
// Do not offer an unavailable native paper as if it were translated.
assert.ok(!PaperLanguages.files(catalogue.cpho['2024'].f.T).zh);

const bundle = PaperLanguages.bundle([cpho], 'en');
assert.equal(bundle.language, 'en');
assert.equal(bundle.papers.zh[0], cpho.papers.zh);
assert.equal(PaperLanguages.bundle([cpho], 'ko').language, 'ko');
assert.equal(PaperLanguages.bundle([ru], 'en').language, 'ru');
assert.equal(PaperLanguages.bundle([hu], 'en').language, 'hu');
const oneLanguage = {paper:'Other_2023_T_EN.pdf',paperLang:'en',papers:{en:'Other_2023_T_EN.pdf'}};
assert.deepEqual(Object.keys(PaperLanguages.bundle([cpho,oneLanguage], 'en').papers), ['en']);
assert.deepEqual(PaperLanguages.normalize({ru:['javascript:alert(1)'], en:['../secrets.pdf'],zh:['CPhO_2023_T_ZH.pdf','extra.pdf']},1), {});
assert.deepEqual(PaperLanguages.normalize({ru:['RuPhO_2026_T1_RU.pdf']},1), {ru:['RuPhO_2026_T1_RU.pdf']});

// The actual competition links keep interface and paper language independent.
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const hrefStart = html.indexOf('function theoryHref(');
const hrefEnd = html.indexOf('/* a problem card', hrefStart);
const context = {PaperLanguages,URLSearchParams,lang:'en',THY_WHOLE:new Set(['ispho']),
  thyOf:(key,year)=>catalogue[key][year],compOf:()=>({abbr:'Test'}),yearPair:()=>false};
vm.createContext(context);
vm.runInContext(html.slice(hrefStart,hrefEnd), context);
const link = (key,year,parts) => new URL(context.theoryHref(key,{y:year},parts), 'https://haslalab.org/');
const enLink = link('cpho',2023,['T']);
assert.equal(enLink.searchParams.get('lang'), 'en');
assert.equal(enLink.searchParams.get('pl'), 'en');
assert.equal(JSON.parse(enLink.searchParams.get('papers')).zh[0], cpho.papers.zh);
const ruLink = link('rupho',2026,['T1','T2','T3']);
assert.equal(ruLink.searchParams.get('pl'), 'ru');
assert.equal(JSON.parse(ruLink.searchParams.get('papers')).ru.length,3);

const cardStart = html.indexOf('function theoryHtml(');
const cardEnd = html.indexOf('/* the general instructions',cardStart);
Object.assign(context, {UI:{en:{thyPaper:'Problem paper',thySol:'Solutions',thyOrigChip:'Original'}},
  THY_YEARLY:new Set(),esc:String,thyUrl:x=>x,simThy:()=>new Set(),probCard:card=>JSON.stringify(card),
  contestEntries:()=>[],theoryGroups:()=>[],reviewTheoryGroups:()=>[],examGroups:()=>[],TL:()=>'',thyCount:()=>1});
vm.runInContext(html.slice(cardStart,cardEnd),context);
const cards = context.theoryHtml('cpho',{y:2023});
assert.ok(cards.includes('Problem paper · 中文'));
assert.ok(cards.includes(cpho.papers.zh));
assert.ok(cards.includes('Problem paper · 한국어'));
const nativeCard = context.theoryHtml('eotvos',{y:2026});
assert.ok(nativeCard.includes('Magyar'));
console.log('Paper language catalogue, practice links, exam URLs and input validation passed.');
