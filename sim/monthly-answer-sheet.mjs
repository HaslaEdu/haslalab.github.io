import { getMonthlyAnswerSheet } from '../monthly-problems.mjs?v=4dc2db565898';

const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const copy = {
  ko: {name:'월별 문제 답안지',part:'소문항',answer:'최종 답',working:'풀이 · 유도 · 근거',nickname:'닉네임',date:'작성일',page:'쪽',points:'점',back:'← 문제로 돌아가기',print:'답안지 인쇄',
    help:'소문항별로 최종 답과 풀이를 함께 작성하세요. 여러 장이면 모든 장에 문제·소문항 번호를 적으세요.',
    note:'이 양식에 작성한 답안 사진 또는 웹의 소문항별 입력란으로 제출합니다. 임시저장·사진 인식은 제출 횟수에 포함되지 않습니다.',
    footer:'추가 용지에는 문제 번호와 소문항 번호를 표시하세요.',failed:'답안지를 불러오지 못했습니다. 문제 화면에서 다시 열어 주세요.'},
  en: {name:'Monthly problem answer sheet',part:'Part',answer:'Final answer',working:'Working · derivation · reasoning',nickname:'Nickname',date:'Date',page:'Page',points:'pts',back:'← Back to the problem',print:'Print answer sheet',
    help:'Write both the final answer and the working for each part. Label every additional page with the problem and part numbers.',
    note:'Submit photographs of this form or use the matching web fields. Saving a draft and reading a photo do not use submission attempts.',
    footer:'Label any extra paper with the problem and part numbers.',failed:'The answer sheet could not be loaded. Open it again from the problem page.'},
};

export function buildAnswerPages(problem, sheet, lang='ko') {
  const t=copy[lang]||copy.ko, title=problem.title||problem['title_'+lang]||'', number=problem.no, period=problem.month||problem.period||problem.week||'2026-11';
  const byId=new Map(sheet.parts.map(p=>[p.id,p]));
  return sheet.pages.map((ids,index)=>`<section class="paper" aria-label="${esc(t.page)} ${index+1}">
    <header><div class="brand">HaslaLab · ${esc(t.name)} · ${esc(period)}</div><h1>${esc(number)}. ${esc(title)}</h1>
      <div class="meta"><span>${esc(t.nickname)}: ____________________</span><span>${esc(t.date)}: ____________________</span><span>${esc(t.page)} ${index+1} / ${sheet.pages.length}</span></div>
      <p class="instructions">${esc(t.note)}</p></header>
    <div class="parts" style="--part-count:${ids.length}">${ids.map(id=>{
      const p=byId.get(id);if(!p)throw Error('Unknown answer-sheet part');
      return `<section class="part" data-part="${esc(id)}"><h2>${esc(t.part)} ${esc(id)} · ${esc(p['label_'+lang]||p.label_ko)} · ${p.points}${esc(t.points)}</h2>
        <div class="label">${esc(t.answer)}</div><div class="answer"></div><div class="label">${esc(t.working)}</div><div class="working"></div></section>`;
    }).join('')}</div><footer><span>${esc(t.footer)}</span><span>HL-MONTHLY-${esc(problem.id)} · ${esc(sheet.version)} · ${index+1}/${sheet.pages.length}</span></footer></section>`).join('');
}

async function mount() {
  const q=new URLSearchParams(location.search),id=Number(q.get('id')),lang=q.get('lang')==='en'?'en':'ko',t=copy[lang],sheet=getMonthlyAnswerSheet(id);
  document.documentElement.lang=lang;
  const back=document.getElementById('back'),button=document.getElementById('print'),message=document.getElementById('message');
  back.textContent=t.back;back.href='../?lang='+lang+'#/monthly/p/'+id;button.textContent=t.print;document.getElementById('help').textContent=t.help;
  try {
    if(!sheet)throw Error('Unknown problem');
    const response=await fetch('https://haslalab-community-edge.haslalab.workers.dev/api/problems/'+id+'?lang='+lang,{cache:'no-store'});
    if(!response.ok)throw Error('Problem unavailable');
    const {problem}=await response.json();
    document.title=problem.title+' · '+t.name+' · HaslaLab';
    document.getElementById('sheets').innerHTML=buildAnswerPages(problem,sheet,lang);
    message.hidden=true;button.disabled=false;button.addEventListener('click',()=>window.print());
  } catch { message.textContent=t.failed; }
}
if(typeof document!=='undefined')mount();
