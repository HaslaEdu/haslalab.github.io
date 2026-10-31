import { getMonthlyAnswerSheet } from '../monthly-problems.mjs?v=498c8dab65d4';

const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const copy = {
  ko: {name:'월별 문제 답안지',part:'소문항',answer:'결과 · 단위',working:'풀이 · 유도 · 계산',nickname:'참가자 / 닉네임',date:'작성일',page:'쪽',points:'점',back:'← 문제로 돌아가기',print:'답안지 인쇄',
    help:'소문항별로 최종 답과 풀이를 함께 작성하세요. 여러 장이면 모든 장에 문제·소문항 번호를 적으세요.',
    note:'이 양식에 작성한 답안 사진 또는 웹의 소문항별 입력란으로 제출합니다. 임시저장·사진 인식은 제출 횟수에 포함되지 않습니다.',
    footer:'추가 용지에는 문제 번호와 소문항 번호를 표시하세요.',failed:'답안지를 불러오지 못했습니다. 문제 화면에서 다시 열어 주세요.'},
  en: {name:'Monthly problem answer sheet',part:'Part',answer:'Results · units',working:'Working · derivation · calculation',nickname:'Participant / nickname',date:'Date',page:'Page',points:'pts',back:'← Back to the problem',print:'Print answer sheet',
    help:'Write both the final answer and the working for each part. Label every additional page with the problem and part numbers.',
    note:'Submit photographs of this form or use the matching web fields. Saving a draft and reading a photo do not use submission attempts.',
    footer:'Label any extra paper with the problem and part numbers.',failed:'The answer sheet could not be loaded. Open it again from the problem page.'},
};

const localized=(value,lang,fallback='')=>value?.['label_'+lang]||value?.label_ko||value?.label_en||fallback;
const titleOf=(value,lang)=>value?.['title_'+lang]||value?.title_ko||value?.title_en||'';

export function buildResponseTable(table,lang='ko') {
  const columns=table.columns||[],rows=table.rows||[];
  if(!columns.length)return'';
  return `<table class="response-table"><caption>${esc(titleOf(table,lang))}</caption><thead><tr>${columns.map(c=>`<th scope="col">${esc(typeof c==='string'?c:localized(c,lang))}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>{
    const cells=Array.isArray(row)?row:row.cells||[localized(row,lang)];
    return `<tr>${columns.map((_,i)=>`<${i===0?'th scope="row"':'td'}>${esc(cells[i]??'')}${cells[i]?'':'&nbsp;'}</${i===0?'th':'td'}>`).join('')}</tr>`;
  }).join('')}</tbody></table>`;
}

export function buildResponseGraph(graph,lang='ko') {
  const count=(value,fallback,max)=>Number.isFinite(Number(value))?Math.max(2,Math.min(max,Math.floor(Number(value)))):fallback;
  const columns=count(graph.columns,20,100),rows=count(graph.rows,12,100),height=Math.max(25,Math.min(150,Number(graph.heightMm)||55));
  const left=15,top=4,width=180,bottom=top+height,lines=[];
  for(let i=0;i<=columns;i++){const x=left+i*width/columns;lines.push(`<line x1="${x}" y1="${top}" x2="${x}" y2="${bottom}" stroke="${i%5===0?'#8996a7':'#cbd3dd'}" stroke-width="${i%5===0?'.35':'.15'}"/>`);}
  for(let i=0;i<=rows;i++){const y=top+i*height/rows;lines.push(`<line x1="${left}" y1="${y}" x2="${left+width}" y2="${y}" stroke="${i%5===0?'#8996a7':'#cbd3dd'}" stroke-width="${i%5===0?'.35':'.15'}"/>`);}
  const title=titleOf(graph,lang),xLabel=graph['x_label_'+lang]||graph.x_label_ko||graph.x_label_en||'',yLabel=graph['y_label_'+lang]||graph.y_label_ko||graph.y_label_en||'';
  const mathAxes=xLabel.includes('$')||yLabel.includes('$');
  const labels=mathAxes?'':`<text x="${left+width/2}" y="${bottom+11}" text-anchor="middle" font-size="4" fill="#202735">${esc(xLabel)}</text><text x="4" y="${top+height/2}" transform="rotate(-90 4 ${top+height/2})" text-anchor="middle" font-size="4" fill="#202735">${esc(yLabel)}</text>`;
  const grid=`<svg role="img" aria-label="${esc(title)}" viewBox="0 0 200 ${height+19}" xmlns="http://www.w3.org/2000/svg">${lines.join('')}<path d="M${left},${top}V${bottom}H${left+width}" fill="none" stroke="#202735" stroke-width=".6"/>${labels}</svg>`;
  // KaTeX auto-render works in HTML, so mathematical axes sit over the vector grid.
  const plotted=mathAxes?`<div class="graph-math-plane">${grid}<div class="graph-x-label">${esc(xLabel)}</div><div class="graph-y-label" style="top:${100*(top+height/2)/(height+19)}%">${esc(yLabel)}</div></div>`:grid;
  return `<figure class="response-graph"><figcaption>${esc(title)}</figcaption>${plotted}</figure>`;
}

export function renderAnswerSheetMath(root) {
  if (typeof globalThis.renderMathInElement !== 'function') return;
  globalThis.renderMathInElement(root,{delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false},{left:'\\(',right:'\\)',display:false},{left:'\\[',right:'\\]',display:true}],throwOnError:false,trust:false});
}

function resultBoxes(part,lang){
  if(!part.results?.length)return'';
  return `<div class="result-grid">${part.results.map(r=>`<div class="result-field"><div class="result-heading"><span>${esc(localized(r,lang))}</span>${r.unit?`<span class="unit">[${esc(r.unit)}]</span>`:''}</div><div class="result-space" aria-hidden="true"></div></div>`).join('')}</div>`;
}

export function buildAnswerPages(problem, sheet, lang='ko') {
  const t=copy[lang]||copy.ko, title=problem.title||problem['title_'+lang]||'', number=problem.no, period=problem.month||problem.period||problem.week||'2026-11';
  const byId=new Map(sheet.parts.map(p=>[p.id,p]));
  // SVG ink remains printable when a browser omits CSS background graphics.
  const scanCorners=['tl','tr','bl','br'].map(corner=>`<span class="scan-mark" data-scan-corner="${corner}" aria-hidden="true"><svg width="10" height="10" viewBox="0 0 10 10" focusable="false" shape-rendering="crispEdges"><rect width="10" height="10" fill="#fff"/><rect x="2" y="2" width="6" height="6" fill="#000"/></svg></span>`).join('');
  return sheet.pages.map((ids,index)=>`<section class="paper" aria-label="${esc(t.page)} ${index+1}">
    ${scanCorners}
    <header><div class="brand">HaslaLab · ${esc(t.name)} · ${esc(period)}</div><h1>${esc(number)}. ${esc(title)}</h1>
      <div class="meta"><span>${esc(t.nickname)}: ____________________</span><span>${esc(t.date)}: ____________________</span><span>${esc(t.page)} ${index+1} / ${sheet.pages.length}</span></div>
      <p class="instructions">${esc(sheet['instructions_'+lang]||t.note)}</p></header>
    <div class="parts" style="--part-count:${ids.length}">${ids.map(id=>{
      const p=byId.get(id);if(!p)throw Error('Unknown answer-sheet part');
      const display=p.displayId?(String(p.displayId).includes('.')?String(p.displayId):`(${p.displayId})`):id;
      return `<section class="part" data-part="${esc(id)}" data-display-part="${esc(display)}"><h2>${esc(t.part)} ${esc(display)} · ${esc(p['label_'+lang]||p.label_ko)} · ${p.points}${esc(t.points)}</h2>
        <div class="label">${esc(t.answer)}</div><div class="answer">${resultBoxes(p,lang)}</div>${(p.tables||[]).map(table=>buildResponseTable(table,lang)).join('')}${(p.graphs||[]).map(graph=>buildResponseGraph(graph,lang)).join('')}<div class="label">${esc(t.working)}</div><div class="working"></div></section>`;
    }).join('')}</div><footer><span>${esc(t.footer)}</span><span>HL-MONTHLY-${esc(problem.id)} · ${esc(sheet.version)} · ${index+1}/${sheet.pages.length}</span></footer></section>`).join('');
}

async function mount() {
  const q=new URLSearchParams(location.search),id=Number(q.get('id')),lang=q.get('lang')==='en'?'en':'ko',t=copy[lang];
  document.documentElement.lang=lang;
  const back=document.getElementById('back'),button=document.getElementById('print'),message=document.getElementById('message');
  back.textContent=t.back;back.href='../?lang='+lang+'#/monthly/p/'+id;button.textContent=t.print;document.getElementById('help').textContent=t.help;
  try {
    if(!Number.isInteger(id)||id<1)throw Error('Unknown problem');
    const response=await fetch('https://haslalab-community-edge.haslalab.workers.dev/api/problems/'+id+'?lang='+lang,{cache:'no-store'});
    if(!response.ok)throw Error('Problem unavailable');
    const {problem}=await response.json();
    const sheet=getMonthlyAnswerSheet(problem);
    if(!sheet)throw Error('Unknown answer sheet');
    document.title=problem.title+' · '+t.name+' · HaslaLab';
    const sheets=document.getElementById('sheets');
    sheets.innerHTML=buildAnswerPages(problem,sheet,lang);
    renderAnswerSheetMath(sheets);
    message.hidden=true;button.disabled=false;button.addEventListener('click',()=>window.print());
  } catch { message.textContent=t.failed; }
}
if(typeof document!=='undefined')mount();
