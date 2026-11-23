/* The Learn guide (#/learn/guide): unit-by-unit chapters written in Markdown (guide/<area>/<unit>/<chapter>.<lang>.md,
   listed in guide/index.json by tools/build-guide.cjs) and the owner's PDF handouts (#/learn/guide?tab=handouts,
   community/src/handouts.js).
   Routes: #/learn/guide · #/learn/guide?q=… · #/learn/guide?tab=handouts · #/learn/guide/<area>/<unit>
           · #/learn/guide/<area>/<unit>/<chapter>[?s=<section>]
   window.HL_GUIDE = {view, mount}; in Node the Markdown parts (parseFrontMatter, renderMarkdown, plainText) for the
   build and the tests. */
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.HL_GUIDE=api;
})(typeof globalThis==='object'?globalThis:this,function(){
  'use strict';
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  /* ── authoring format ─────────────────────────────────────────────────────────────────────────── */
  /* front matter: key: value lines between two --- lines */
  function parseFrontMatter(src){
    const text=String(src||'').replace(/^\uFEFF/,'').replace(/\r\n?/g,'\n');
    const m=/^---\n([\s\S]*?)\n---\n?/.exec(text);
    if(!m)return{meta:{},body:text};
    const meta={};
    for(const line of m[1].split('\n')){
      const kv=/^([a-z_]+):\s*(.*)$/.exec(line.trim());if(!kv)continue;
      let v=kv[2].trim();if(/^".*"$/.test(v))v=v.slice(1,-1);
      meta[kv[1]]=/^-?\d+$/.test(v)?Number(v):v;
    }
    return{meta,body:text.slice(m[0].length)};
  }
  const WORDS={
    ko:{remark:'참고',result:'핵심 결과',why:'왜 그럴까?',derivation:'유도',try:'직접 풀어 보기',solution:'풀이 보기',example:'예제',
      show:'펼치기',hide:'접기',figure:'그림',eq:'식'},
    en:{remark:'Remark',result:'Key result',why:'Why?',derivation:'Derivation',try:'Try it yourself',solution:'Show the solution',example:'Worked example',
      show:'Show',hide:'Hide',figure:'Figure',eq:'Eq.'}
  };
  const BOXES=new Set(['remark','result','why','derivation','try','solution','example']);
  const safeHref=u=>/^(?:https:\/\/[^\s"'<>]+|#\/[^\s"'<>]*|[a-z0-9-]+\.html(?:\?[^\s"'<>]*)?)$/i.test(u)?u:'';
  const slugId=s=>String(s).toLowerCase().replace(/[^a-z0-9-]+/g,'-').replace(/^-+|-+$/g,'').slice(0,40);

  /* inline: $math$, `code`, [text](link), [@label] references, **bold**, *italic* */
  function inline(src,state){
    const keep=[];const hold=html=>{keep.push(html);return '\u0000'+(keep.length-1)+'\u0000';};
    let s=String(src).replace(/\\\$/g,()=>hold('$'));
    s=s.replace(/`([^`]+)`/g,(_,c)=>hold(`<code>${esc(c)}</code>`));
    s=s.replace(/\$([^$\n]+?)\$/g,(_,tex)=>hold(`<span class="gm" data-tex="${esc(tex)}">${esc(tex)}</span>`));
    s=s.replace(/\[@([\w-]+)\]/g,(_,label)=>{state.refs.add(label);return hold('\u0002'+label+'\u0002');});
    s=esc(s);
    s=s.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g,(all,text,url)=>{
      const raw=url.replace(/&amp;/g,'&'),h=safeHref(raw);if(!h)return text;
      return `<a href="${esc(h)}"${/^https:/.test(h)?' target="_blank" rel="noopener"':''}>${text}</a>`;
    });
    s=s.replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>').replace(/(^|[^*\w])\*([^*\s][^*]*?)\*(?!\w)/g,'$1<em>$2</em>');
    return s.replace(/\u0000(\d+)\u0000/g,(_,n)=>keep[+n]);
  }

  /* blocks: ## and ### headings, paragraphs, - and 1. lists, $$ display equations $$ {#label} (numbered),
     (numbered in the main text or when labelled; unnumbered steps inside a box), ![caption](fig/x.svg){#label} figures (numbered), and fenced boxes :::remark / :::result / :::why /
     :::derivation Title / :::example Title / :::try Title with :::solution inside, each closed by ::: */
  function renderMarkdown(src,lang='ko',opts={}){
    const W=WORDS[lang]||WORDS.en,{meta,body}=parseFrontMatter(src);
    const state={refs:new Set(),labels:{},eq:0,unnumbered:0,fig:0,sec:0,tries:0,toc:[],errors:[]};
    const stack=[{kind:'root',html:[]}];const out=()=>stack[stack.length-1].html;
    let para=[],list=null;
    const flush=()=>{
      if(para.length){out().push(`<p>${inline(para.join(' '),state)}</p>`);para=[];}
      if(list){out().push(`<${list.type}>${list.items.map(x=>`<li>${inline(x,state)}</li>`).join('')}</${list.type}>`);list=null;}
    };
    const figBase=opts.figBase??'guide/';
    const lines=body.split('\n');
    for(let i=0;i<lines.length;i++){
      const line=lines[i],t=line.trim();
      if(/^:::/.test(t)){
        flush();
        const name=t.slice(3).trim();
        if(!name){
          if(stack.length===1){state.errors.push('a ::: closes nothing (line '+(i+1)+')');continue;}
          const box=stack.pop(),inner=box.html.join('\n'),title=box.title?inline(box.title,state):'';
          const tog=`<span class="gd-tog" data-show="${esc(W.show)}" data-hide="${esc(W.hide)}" aria-hidden="true"></span>`;
          if(box.kind==='derivation')out().push(`<details class="gbox g-deriv"><summary><span class="gbox-h">${W.derivation}</span>${title?` <span class="gbox-t">${title}</span>`:''}${tog}</summary><div class="gbox-b">${inner}</div></details>`);
          else if(box.kind==='solution')out().push(`<details class="g-sol"><summary>${title||W.solution}${tog}</summary><div class="gbox-b">${inner}</div></details>`);
          else if(box.kind==='try'){const n=++state.tries;out().push(`<section class="gbox g-try" id="try-${n}"><p class="gbox-h">${W.try} ${n}${title?` <span class="gbox-t">${title}</span>`:''}</p><div class="gbox-b">${inner}</div></section>`);}
          else if(box.kind==='example')out().push(`<section class="gbox g-example"><p class="gbox-h">${W.example}${title?` <span class="gbox-t">${title}</span>`:''}</p><div class="gbox-b">${inner}</div></section>`);
          else out().push(`<aside class="gbox g-${box.kind}"><p class="gbox-h">${title||W[box.kind]}</p><div class="gbox-b">${inner}</div></aside>`);
          continue;
        }
        const m=/^([a-z]+)\s*(.*)$/.exec(name);
        if(!m||!BOXES.has(m[1])){state.errors.push('unknown box :::'+name+' (line '+(i+1)+')');continue;}
        if(m[1]==='solution'&&stack[stack.length-1].kind!=='try')state.errors.push(':::solution outside :::try (line '+(i+1)+')');
        stack.push({kind:m[1],title:m[2],html:[]});continue;
      }
      if(/^\$\$/.test(t)){
        flush();
        let tex,label='',one=/^\$\$(.+)\$\$\s*(?:\{#([\w-]+)\})?$/.exec(t);
        if(one){tex=one[1];label=one[2]||'';}
        else{
          const buf=[t.slice(2)];let j=i+1;
          for(;j<lines.length;j++){const c=lines[j].trim();const end=/^(.*)\$\$\s*(?:\{#([\w-]+)\})?$/.exec(c);if(end){buf.push(end[1]);label=end[2]||'';break;}buf.push(lines[j]);}
          if(j>=lines.length)state.errors.push('an equation is never closed (line '+(i+1)+')');
          tex=buf.join('\n').trim();i=j;
        }
        /* numbered: an equation of the main text, or a labelled one; the steps inside a box are not */
        const numbered=!!label||stack.length===1,n=numbered?++state.eq:0,id=label?'eq-'+slugId(label):numbered?'eq-'+n:'eq-u'+(++state.unnumbered);
        if(label){if(state.labels[label])state.errors.push('label used twice: '+label);state.labels[label]={n,kind:'eq',id};}
        out().push(`<div class="geq" id="${id}"><div class="geq-m"><span class="gm" data-display="1" data-tex="${esc(tex.trim())}">${esc(tex.trim())}</span></div>${numbered?`<span class="geq-n">(${n})</span>`:''}</div>`);
        continue;
      }
      const h=/^(#{2,3})\s+(.+)$/.exec(t);
      if(h){
        flush();
        if(h[1]==='##'){const n=++state.sec,id='s-'+n;state.toc.push({id,n,title:h[2].trim()});out().push(`<h2 id="${id}"><span class="gd-secn">${n}</span> ${inline(h[2],state)}</h2>`);}
        else out().push(`<h3>${inline(h[2],state)}</h3>`);
        continue;
      }
      const f=/^!\[([^\]]*)\]\((fig\/[\w.-]+\.(?:svg|png))\)\s*(?:\{#([\w-]+)\})?$/.exec(t);
      if(f){
        flush();
        const n=++state.fig,id=f[3]?'fig-'+slugId(f[3]):'fig-'+n;
        if(f[3]){if(state.labels[f[3]])state.errors.push('label used twice: '+f[3]);state.labels[f[3]]={n,kind:'fig',id};}
        (state.figures||(state.figures=[])).push(f[2]);
        out().push(`<figure class="gfig" id="${id}"><img src="${esc(figBase+f[2])}" alt="${esc(f[1])}" loading="lazy"><figcaption><b>${W.figure} ${n}.</b> ${inline(f[1],state)}</figcaption></figure>`);
        continue;
      }
      const li=/^(?:([-*])|(\d+)\.)\s+(.+)$/.exec(t);
      if(li){
        const type=li[1]?'ul':'ol';
        if(para.length){const p=para;para=[];out().push(`<p>${inline(p.join(' '),state)}</p>`);}
        if(list&&list.type!==type)flush();
        if(!list)list={type,items:[]};
        list.items.push(li[3]);continue;
      }
      if(!t){flush();continue;}
      if(list&&/^\s{2,}/.test(line)){list.items[list.items.length-1]+=' '+t;continue;}
      if(list)flush();
      para.push(t);
    }
    flush();
    while(stack.length>1){state.errors.push('a :::'+stack[stack.length-1].kind+' is never closed');const box=stack.pop();out().push(box.html.join('\n'));}
    let html=stack[0].html.join('\n');
    html=html.replace(/\u0002([\w-]+)\u0002/g,(_,label)=>{
      const L=state.labels[label];if(!L){state.errors.push('unknown reference [@'+label+']');return '(?)';}
      return L.kind==='eq'?`<a class="gref" href="#${L.id}" data-gd-jump="${L.id}">(${L.n})</a>`:`<a class="gref" href="#${L.id}" data-gd-jump="${L.id}">${W.figure} ${L.n}</a>`;
    });
    return{meta,html,toc:state.toc,equations:state.eq,figures:state.figures||[],tries:state.tries,errors:state.errors};
  }
  /* the words of a chapter for the search index: no front matter, markup or TeX commands */
  function plainText(src){
    const {body}=parseFrontMatter(src);
    return body.replace(/^:::.*$/gm,' ').replace(/^\$\$[\s\S]*?\$\$.*$/gm,' ').replace(/!\[([^\]]*)\]\([^)]*\)(\{#[^}]*\})?/g,'$1')
      .replace(/\[@[\w-]+\]/g,' ').replace(/\[([^\]]+)\]\([^)]*\)/g,'$1').replace(/\$([^$\n]+)\$/g,(_,m)=>' '+m.replace(/\\[a-zA-Z]+/g,' ').replace(/[{}_^\\]/g,' ')+' ')
      .replace(/^#{1,6}\s+/gm,'').replace(/[*`]/g,'').replace(/\s+/g,' ').trim();
  }

  /* ── the page (browser only) ─────────────────────────────────────────────────────────────────── */
  const B=()=>typeof window==='object'?window:{};
  const ko=()=>typeof lang==='undefined'||lang!=='en';
  const L=()=>ko()?'ko':'en';
  const P=()=>B().HL_LEARN_PATH;
  const T=(k,e)=>ko()?k:(typeof LX==='function'?LX(e):e);
  const READ_KEY='hlGuideRead';
  const readMarks=()=>{try{const v=JSON.parse(localStorage.getItem(READ_KEY)||'{}');return v&&typeof v==='object'?v:{};}catch(e){return{};}};
  const setRead=(id,on)=>{const v=readMarks();if(on)v[id]=Date.now();else delete v[id];try{localStorage.setItem(READ_KEY,JSON.stringify(v));}catch(e){}};
  let indexP=null;
  const getIndex=()=>indexP||(indexP=fetch('guide/index.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error('index');return r.json();}).catch(e=>{indexP=null;throw e;}));
  const mdCache=new Map();
  const getChapter=(c,l)=>{const k=c.unit+'/'+c.slug+'.'+l;if(!mdCache.has(k))mdCache.set(k,fetch(`guide/${c.unit}/${c.slug}.${l}.md?v=${c.v}`).then(r=>{if(!r.ok)throw Error('chapter');return r.text();}).catch(e=>{mdCache.delete(k);throw e;}));return mdCache.get(k);};

  function route(){
    const [path,query]=String(location.hash||'').replace(/^#\/?/,'').split('?');
    const parts=path.split('/').filter(Boolean).slice(2);
    const q=new URLSearchParams(query||'');
    return{area:parts[0]||'',sub:parts[1]||'',chapter:parts[2]||'',q};
  }
  const unitInfo=unit=>{const x=P()?.SUBTOPICS.get(unit);return x?{area:x.area,sub:x.sub,name:x.sub.name[L()],areaName:x.area.name[L()]}:null;};
  const stageText=step=>{const s=P()?.stageOf(step);if(!s)return '';return ko()?`${s.name.ko} · ${step}단계`:`${s.name.en} · step ${step}`;};
  const chapterId=c=>c.unit+'/'+c.slug;
  const chapterHref=c=>'#/learn/guide/'+c.unit+'/'+c.slug;
  const title=c=>c.title?.[L()]||c.title?.ko||c.slug;
  const practiceHref=unit=>'#/learn/practice?mode=custom&unit='+unit;
  const searchHref=unit=>{const [a,s]=unit.split('/'),b=P()?.bankSubjectOf(a,s);return '#/learn/physics/search'+(b?'?subject='+b:'');};
  function head(trail,h1,line){
    const crumbs=[`<a href="#/learn">${T('학습','Learn')}</a>`].concat(trail).join(' / ');
    return `<div class="phead"><p class="eyebrow">${crumbs}</p><h1>${h1}</h1>${line?`<p class="learn-tool-copy">${line}</p>`:''}</div>`;
  }
  const LINE=()=>T('단원마다 읽는 물리 교재입니다. 유도, 풀이 예제, 직접 풀어 보는 문제가 함께 있습니다.','A physics textbook, unit by unit, with derivations, worked examples and problems to try yourself.');
  function tabs(on){
    return `<div role="navigation" class="gd-tabs" aria-label="${T('교재 보기','Guide views')}"><a href="#/learn/guide"${on==='book'?' aria-current="page"':''}>${T('교재','Chapters')}</a><a href="#/learn/guide?tab=handouts"${on==='handouts'?' aria-current="page"':''}>${T('핸드아웃','Handouts')}</a></div>`;
  }

  function view(){
    const r=route(),G=T('교재','Guide'),guideLink=`<a href="#/learn/guide">${G}</a>`;
    if(r.area&&r.sub){
      const u=unitInfo(r.area+'/'+r.sub);
      const name=u?esc(u.name):esc(r.sub);
      return `<div class="shell gd" id="gdRoot" data-gd="${r.chapter?'chapter':'unit'}">${head([guideLink,u?esc(u.areaName):''].filter(Boolean),r.chapter?`<span id="gdTitle">${name}</span>`:name,'')}<div id="gdBody"><p class="note" role="status">${T('불러오는 중…','Loading…')}</p></div></div>`;
    }
    const tab=r.q.get('tab')==='handouts'?'handouts':'book';
    return `<div class="shell gd" id="gdRoot" data-gd="${tab}">${head([G],G,LINE())}${tabs(tab)}<div id="gdBody"><p class="note" role="status">${T('불러오는 중…','Loading…')}</p></div></div>`;
  }

  async function mount(){
    const root=document.getElementById('gdRoot');if(!root)return;
    const box=document.getElementById('gdBody'),r=route(),mode=root.dataset.gd;
    if(mode==='handouts')return mountHandouts(box);
    let idx;
    try{idx=await getIndex();}catch(e){if(box.isConnected)box.innerHTML=`<div class="gd-empty"><p>${T('교재 목록을 불러오지 못했습니다.','Could not load the guide.')}</p><button type="button" class="hm-go gd-btn" id="gdRetry">${T('다시 불러오기','Try again')}</button></div>`;const b=document.getElementById('gdRetry');if(b)b.onclick=()=>mount();return;}
    if(!box.isConnected)return;
    SIMS=idx.sims||{};
    const chapters=ordered(idx.chapters);
    if(mode==='book')return homeView(box,chapters,r);
    const unit=r.area+'/'+r.sub;
    if(mode==='unit')return unitView(box,chapters,unit);
    const c=chapters.find(x=>x.unit===unit&&x.slug===r.chapter);
    if(!c){box.innerHTML=`<div class="gd-empty"><p>${T('이 글을 찾지 못했습니다.','This chapter does not exist.')}</p><a class="hm-go gd-btn" href="#/learn/guide">${T('교재 목록으로','Back to the guide')}</a></div>`;return;}
    return chapterView(box,chapters,c,r);
  }
  /* the units in the learning path's order, then each unit's chapters by order */
  function ordered(list){
    const keys=[...(P()?.SUBTOPICS.keys()||[])],pos=k=>{const i=keys.indexOf(k);return i<0?1e9:i;};
    return [...list].sort((a,b)=>pos(a.unit)-pos(b.unit)||a.order-b.order||a.slug.localeCompare(b.slug));
  }
  const tick=(c,marks)=>marks[chapterId(c)]?`<span class="gd-read" title="${T('읽음','Read')}" aria-label="${T('읽음','Read')}">✓</span>`:'';

  /* the sidebar: areas, their units, each unit's chapters; units without chapters say so */
  function tree(chapters,current){
    const marks=readMarks(),byUnit=new Map();for(const c of chapters)(byUnit.get(c.unit)||byUnit.set(c.unit,[]).get(c.unit)).push(c);
    return (P()?.AREAS||[]).map(a=>{
      const units=a.subtopics.map(s=>{const key=a.key+'/'+s.key,cs=byUnit.get(key)||[];
        const here=current&&current.unit===key;
        return `<li class="${cs.length?'':'gd-soon'}${here?' gd-here':''}"><a href="#/learn/guide/${key}">${esc(s.name[L()])}</a>${cs.length?`<ul>${cs.map(c=>`<li><a href="${chapterHref(c)}"${current&&chapterId(current)===chapterId(c)?' aria-current="page"':''}>${esc(title(c))}</a>${tick(c,marks)}</li>`).join('')}</ul>`:`<span class="gd-soon-t">${T('준비 중','Soon')}</span>`}</li>`;}).join('');
      const open=current?current.unit.startsWith(a.key+'/'):byUnit.size&&[...byUnit.keys()].some(k=>k.startsWith(a.key+'/'));
      return `<details class="gd-area"${open?' open':''}><summary>${esc(a.name[L()])}</summary><ul>${units}</ul></details>`;
    }).join('');
  }

  function homeView(box,chapters,r){
    const marks=readMarks(),next=chapters.find(c=>!marks[chapterId(c)])||chapters[0];
    const started=chapters.some(c=>marks[chapterId(c)]);
    const q=r.q.get('q')||'';
    box.innerHTML=`<div class="gd-start">${next?`<a class="hm-go gd-btn" href="${chapterHref(next)}">${started?T('이어 읽기','Continue reading'):T('첫 글 읽기','Start reading')}: ${esc(title(next))}</a>`:''}
        <form class="gd-search" role="search" id="gdSearch"><label for="gdQ" class="gd-sr">${T('교재 검색','Search the guide')}</label>
          <input id="gdQ" type="search" value="${esc(q)}" placeholder="${T('교재에서 찾기: 예) 가속도, 에너지','Search the guide, e.g. acceleration, energy')}" autocomplete="off"></form></div>
      <div id="gdResults"></div>
      <div id="gdUnits" class="gd-units">${(P()?.AREAS||[]).map(a=>{
        const units=a.subtopics.map(s=>{const key=a.key+'/'+s.key,cs=chapters.filter(c=>c.unit===key);
          return `<li><a href="#/learn/guide/${key}">${esc(s.name[L()])}</a>${cs.length?` <span class="gd-count">${ko()?cs.length+'편':cs.length+(cs.length>1?' chapters':' chapter')}</span>${cs.some(c=>marks[chapterId(c)])?' <span class="gd-read">✓</span>':''}`:` <span class="gd-soon-t">${T('준비 중','Soon')}</span>`}</li>`;}).join('');
        return `<section class="gd-area-card"><h2>${esc(a.name[L()])}</h2><ul>${units}</ul></section>`;}).join('')}</div>
      <p class="note gd-foot">${T('글이 없는 단원은 준비 중입니다. 그동안 단원을 누르면 그 단원의 문제와 시뮬레이션으로 바로 갈 수 있습니다.','Units without chapters are still being written. Open one to go straight to its problems and simulations.')}</p>`;
    const input=document.getElementById('gdQ'),form=document.getElementById('gdSearch');
    const run=()=>{const v=input.value.trim();search(chapters,v);try{history.replaceState(null,'','#/learn/guide'+(v?'?q='+encodeURIComponent(v):''));}catch(e){}};
    input.addEventListener('input',run);form.addEventListener('submit',e=>{e.preventDefault();run();});
    if(q)search(chapters,q);
  }
  function search(chapters,q){
    const out=document.getElementById('gdResults'),units=document.getElementById('gdUnits');if(!out)return;
    const words=q.toLowerCase().split(/\s+/).filter(Boolean);
    if(!words.length){out.innerHTML='';units.hidden=false;return;}
    units.hidden=true;
    const l=L(),hits=[];
    for(const c of chapters){
      const t=(title(c)+' '+(c.sections?.[l]||[]).join(' ')).toLowerCase(),body=String(c.text?.[l]||''),lb=body.toLowerCase();
      if(!words.every(w=>t.includes(w)||lb.includes(w)))continue;
      const at=lb.indexOf(words[0]);
      const from=Math.max(0,at-50),snip=at<0?body.slice(0,120):body.slice(from,from+160);
      hits.push({href:chapterHref(c),name:title(c),meta:unitInfo(c.unit)?.name||'',snip:(from>0?'…':'')+snip+'…',score:words.filter(w=>t.includes(w)).length});
    }
    for(const [key,x] of P()?.SUBTOPICS||[]){const n=(x.sub.name.ko+' '+x.sub.name.en+' '+x.area.name[l]).toLowerCase();if(words.every(w=>n.includes(w)))hits.push({href:'#/learn/guide/'+key,name:x.sub.name[l],meta:T('단원','Unit')+' · '+x.area.name[l],snip:'',score:1});}
    hits.sort((a,b)=>b.score-a.score);
    const mark=s=>{let h=esc(s);for(const w of words)h=h.replace(new RegExp(esc(w).replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'gi'),m=>`<mark>${m}</mark>`);return h;};
    out.innerHTML=hits.length?`<p class="note" role="status">${ko()?`${hits.length}개 찾음`:`${hits.length} found`}</p><ul class="gd-hits">${hits.map(h=>`<li><a href="${h.href}">${esc(h.name)}</a><small>${esc(h.meta)}</small>${h.snip?`<p>${mark(h.snip)}</p>`:''}</li>`).join('')}</ul>`
      :`<div class="gd-empty"><p role="status">${T(`‘${esc(q)}’에 맞는 글이 없습니다. 다른 낱말로 찾거나, 문제 검색에서 찾아보세요.`,`Nothing in the guide matches ‘${esc(q)}’. Try another word, or search the problems.`)}</p><a class="hm-go gd-btn" href="#/learn/physics/search">${T('문제 검색으로','Search problems')}</a></div>`;
  }

  let SIMS={};
  const simOf=unit=>SIMS[unit]||null;
  function unitLinks(unit,{main=true}={}){
    const sim=simOf(unit);
    return `<div class="gd-links">${main?`<a class="hm-go gd-btn" href="${practiceHref(unit)}">${T('이 단원 문제 풀기','Practise this unit')}</a>`:''}
      ${sim?`<a href="#/learn/concepts?sim=${esc(sim.id)}">${T('개념 시뮬레이션','Concept simulation')}: ${esc(sim.title[L()])}</a>`:''}
      <a href="${searchHref(unit)}">${T('이 분야 문제 검색','Search problems in this area')}</a>
      <a href="#/learn/roadmap?view=units">${T('단원 지도에서 보기','See it on the unit map')}</a></div>`;
  }
  function unitView(box,chapters,unit){
    const u=unitInfo(unit);
    if(!u){box.innerHTML=`<div class="gd-empty"><p>${T('이 단원을 찾지 못했습니다.','This unit does not exist.')}</p><a class="hm-go gd-btn" href="#/learn/guide">${T('교재 목록으로','Back to the guide')}</a></div>`;return;}
    const cs=chapters.filter(c=>c.unit===unit),marks=readMarks();
    const stage=stageText(u.sub.from);
    box.innerHTML=`<p class="gd-meta">${T('처음 다루는 단계','First met at')}: ${esc(stage)}</p>
      ${cs.length?`<ol class="gd-chapters">${cs.map(c=>`<li><a href="${chapterHref(c)}">${esc(title(c))}</a>${tick(c,marks)}<small>${esc(stageText(c.level))}</small>${c.summary?.[L()]?`<p>${esc(c.summary[L()])}</p>`:''}</li>`).join('')}</ol>${unitLinks(unit,{main:false})}`
      :`<section class="learn-pending gd-pending"><h2>${T('준비 중','Coming soon')}</h2>
        <p>${T('이 단원의 글은 아직 없습니다. 준비되면 개념 설명, 식의 유도, 풀이 예제, 직접 풀어 보는 문제와 풀이가 여기에 실립니다.','There are no chapters for this unit yet. When they are ready, this page will hold the ideas, the derivations, worked examples, and problems to try with their solutions.')}</p>
        <p>${T('그동안 이 단원의 문제를 풀어 볼 수 있습니다.','Meanwhile you can work through this unit’s problems.')}</p>${unitLinks(unit)}</section>`}`;
  }

  async function chapterView(box,chapters,c,r){
    const l=L();let src;
    try{src=await getChapter(c,l);}catch(e){
      try{src=await getChapter(c,l==='ko'?'en':'ko');}catch(e2){if(box.isConnected)box.innerHTML=`<div class="gd-empty"><p>${T('글을 불러오지 못했습니다.','Could not load this chapter.')}</p><button type="button" class="hm-go gd-btn" id="gdRetry">${T('다시 불러오기','Try again')}</button></div>`;const b=document.getElementById('gdRetry');if(b)b.onclick=()=>mount();return;}
    }
    if(!box.isConnected)return;
    const doc=renderMarkdown(src,l),u=unitInfo(c.unit),i=chapters.indexOf(c),prev=chapters[i-1],next=chapters[i+1];
    const t=document.getElementById('gdTitle');if(t)t.textContent=title(c);
    if(typeof document!=='undefined')document.title=title(c)+' · '+T('교재','Guide')+' · HaslaLab';
    const id=chapterId(c),read=!!readMarks()[id];
    const toc=doc.toc.length?`<ol>${doc.toc.map(s=>`<li><a href="${chapterHref(c)}?s=${s.id}" data-gd-jump="${s.id}">${esc(s.title.replace(/\$[^$]*\$/g,m=>m.slice(1,-1)))}</a></li>`).join('')}</ol>`:'';
    const discuss=`#/community/write/qna?`+new URLSearchParams({title:(ko()?'[교재] ':'[Guide] ')+title(c),body:(ko()?'글: ':'Chapter: ')+location.origin+location.pathname+chapterHref(c)+'\n\n'}).toString();
    box.innerHTML=`<p class="gd-meta">${u?`<a href="#/learn/guide/${c.unit}">${esc(u.name)}</a> · `:''}${esc(stageText(c.level))}${read?` · <span class="gd-read">✓ ${T('읽음','Read')}</span>`:''}</p>
      <div class="gd-bar"><button type="button" class="gd-drawer-btn" id="gdOpenSide" aria-controls="gdSide" aria-expanded="false">${T('단원 목록','All units')}</button>
        ${toc?`<details class="gd-toc-m"><summary>${T('이 글의 차례','In this chapter')}</summary>${toc}</details>`:''}</div>
      <div class="gd-layout">
        <div role="navigation" class="gd-side" id="gdSide" aria-label="${T('단원 목록','All units')}"><div class="gd-side-head"><b>${T('단원 목록','All units')}</b><button type="button" class="gd-close" id="gdCloseSide" aria-label="${T('닫기','Close')}">×</button></div>${tree(chapters,c)}</div>
        <article class="gd-art" lang="${l}">${doc.html}
          <div class="gd-done"><button type="button" class="gd-btn2" id="gdRead" aria-pressed="${read}">${read?'✓ '+T('읽음 표시됨 (취소)','Marked as read (undo)'):T('다 읽었어요','Mark as read')}</button>
            <a href="${esc(discuss)}">${T('질문하기 · 오타 알리기','Ask a question or report a typo')}</a></div>
          <section class="gd-next-steps"><h2>${T('이 단원 연습하기','Practise this unit')}</h2>${unitLinks(c.unit)}</section>
          <div role="navigation" class="gd-pn" aria-label="${T('이전 글, 다음 글','Previous and next')}">${prev?`<a class="gd-prev" href="${chapterHref(prev)}"><small>${T('이전 글','Previous')}</small>${esc(title(prev))}</a>`:'<span></span>'}${next?`<a class="gd-next" href="${chapterHref(next)}"><small>${T('다음 글','Next')}</small>${esc(title(next))}</a>`:'<span></span>'}</div>
        </article>
        ${toc?`<aside class="gd-toc" aria-label="${T('이 글의 차례','In this chapter')}"><b>${T('이 글의 차례','In this chapter')}</b>${toc}</aside>`:''}
      </div><div class="gd-scrim" id="gdScrim" hidden></div>`;
    wireChapter(box,c);
    /* a section link (?s=s-3): scroll there once the math has its final size, and again as figures above it load,
       unless the reader has scrolled in the meantime */
    const s=r.q.get('s'),target=s&&/^[\w-]{1,48}$/.test(s)&&document.getElementById(s);
    let at=-1;const go=()=>{if(!target||!target.isConnected||(at>=0&&Math.abs(scrollY-at)>4))return;target.scrollIntoView({block:'start'});at=scrollY;};
    renderMath(box).then(()=>{go();for(const img of box.querySelectorAll('.gfig img'))if(!img.complete)img.addEventListener('load',go,{once:true});});
  }
  function wireChapter(box,c){
    const side=document.getElementById('gdSide'),scrim=document.getElementById('gdScrim'),open=document.getElementById('gdOpenSide');
    const setSide=on=>{side.classList.toggle('open',on);scrim.hidden=!on;open.setAttribute('aria-expanded',String(on));document.body.classList.toggle('gd-lock',on);if(on)document.getElementById('gdCloseSide')?.focus();};
    open.onclick=()=>setSide(true);document.getElementById('gdCloseSide').onclick=()=>{setSide(false);open.focus();};scrim.onclick=()=>setSide(false);
    side.addEventListener('keydown',e=>{if(e.key==='Escape'){setSide(false);open.focus();}});
    side.addEventListener('click',e=>{if(e.target.closest('a'))setSide(false);});
    box.addEventListener('click',e=>{
      const a=e.target.closest('[data-gd-jump]');if(!a)return;
      const el=document.getElementById(a.dataset.gdJump);if(!el)return;
      e.preventDefault();el.scrollIntoView({behavior:'smooth',block:'start'});
      const d=a.closest('details.gd-toc-m');if(d)d.open=false;
      if(/^s-\d+$/.test(a.dataset.gdJump)){try{history.replaceState(null,'',chapterHref(c)+'?s='+a.dataset.gdJump);}catch(_){}}
    });
    const btn=document.getElementById('gdRead');
    btn.onclick=()=>{const on=btn.getAttribute('aria-pressed')!=='true';setRead(chapterId(c),on);btn.setAttribute('aria-pressed',String(on));btn.textContent=on?'✓ '+T('읽음 표시됨 (취소)','Marked as read (undo)'):T('다 읽었어요','Mark as read');
      const sideLink=side.querySelector(`a[aria-current="page"]`);if(sideLink){sideLink.parentNode.querySelector('.gd-read')?.remove();if(on)sideLink.insertAdjacentHTML('afterend',tick(c,{[chapterId(c)]:1}));}};
  }

  let katexP=null;
  function loadKatex(){
    if(B().katex)return Promise.resolve(B().katex);
    if(katexP)return katexP;
    const base='problem-bank/public/vendor/katex/';
    katexP=new Promise((resolve,reject)=>{
      if(!document.querySelector('link[data-archive-math],link[data-guide-math]')){const css=document.createElement('link');css.rel='stylesheet';css.href=base+'katex.min.css';css.dataset.guideMath='1';document.head.append(css);}
      const s=document.createElement('script');s.src=base+'katex.min.js';s.onload=()=>resolve(B().katex);s.onerror=()=>{s.remove();katexP=null;reject(Error('math'));};document.head.append(s);
    });
    return katexP;
  }
  function renderMath(box){
    const els=[...box.querySelectorAll('.gm')];if(!els.length)return Promise.resolve();
    return loadKatex().then(k=>{for(const el of els){if(!el.isConnected)continue;try{k.render(el.dataset.tex,el,{displayMode:el.dataset.display==='1',throwOnError:false,strict:'ignore',trust:false,maxExpand:1000,maxSize:30});el.classList.add('gm-ok');}catch(e){}}}).catch(()=>{});
  }

  /* ── handouts ─────────────────────────────────────────────────────────────────────────────── */
  const api=(m,p,b)=>typeof cmApi==='function'?cmApi(m,p,b,{forcePrimary:m==='GET'}):Promise.reject({code:'network'});
  const fileUrl=h=>(typeof cmBase==='function'?cmBase():'')+h.file;
  const size=n=>n>=1048576?(n/1048576).toFixed(1)+' MB':Math.max(1,Math.round(n/1024))+' KB';
  const errText=e=>{const c=e?.code||'';return ({pdf_only:T('PDF 파일만 올릴 수 있습니다.','Only PDF files can be uploaded.'),file_too_large:T('25 MB보다 큰 파일은 올릴 수 없습니다.','Files over 25 MB cannot be uploaded.'),
    file_required:T('파일을 고르세요.','Choose a file.'),bad_title:T('제목을 한국어나 영어로 하나 이상 적으세요.','Give a title in Korean or English.'),forbidden:T('관리자만 할 수 있습니다.','Administrators only.'),
    login_required:T('로그인하세요.','Sign in first.'),r2_unavailable:T('파일 저장소가 연결되어 있지 않습니다.','File storage is not connected.'),network:T('서버에 연결하지 못했습니다.','Could not reach the server.')})[c]||T('잘 되지 않았습니다','Something went wrong')+(c?' ('+c+')':'');};
  const unitOptions=sel=>`<option value="">${T('단원 없음','No unit')}</option>`+(P()?.AREAS||[]).map(a=>`<optgroup label="${esc(a.name[L()])}">${a.subtopics.map(s=>{const k=a.key+'/'+s.key;return `<option value="${k}"${sel===k?' selected':''}>${esc(s.name[L()])}</option>`;}).join('')}</optgroup>`).join('');
  const levelOptions=sel=>`<option value="">${T('단계 없음','No step')}</option>`+Array.from({length:10},(_,i)=>i+1).map(n=>`<option value="${n}"${+sel===n?' selected':''}>${esc(stageText(n))}</option>`).join('');
  async function mountHandouts(box){
    const r=route(),fu=r.q.get('unit')||'',fl=r.q.get('level')||'';
    box.innerHTML=`<p class="gd-meta">${T('수업과 특강에서 쓴 자료를 PDF로 모았습니다. 누르면 새 창에서 열립니다.','Notes from classes and lectures, as PDFs. Each opens in a new tab.')}</p>
      <form class="gd-filter" id="hoFilter"><label>${T('단원','Unit')} <select name="unit">${`<option value="">${T('모든 단원','All units')}</option>`+(P()?.AREAS||[]).map(a=>`<optgroup label="${esc(a.name[L()])}"><option value="${a.key}"${fu===a.key?' selected':''}>${esc(a.name[L()])} · ${T('전체','all')}</option>${a.subtopics.map(s=>{const k=a.key+'/'+s.key;return `<option value="${k}"${fu===k?' selected':''}>${esc(s.name[L()])}</option>`;}).join('')}</optgroup>`).join('')}</select></label>
        <label>${T('단계','Step')} <select name="level"><option value="">${T('모든 단계','All steps')}</option>${Array.from({length:10},(_,i)=>i+1).map(n=>`<option value="${n}"${+fl===n?' selected':''}>${esc(stageText(n))}</option>`).join('')}</select></label></form>
      <div id="hoAdmin"></div><div id="hoList"><p class="note" role="status">${T('불러오는 중…','Loading…')}</p></div>`;
    const form=document.getElementById('hoFilter');
    form.addEventListener('change',()=>{const q=new URLSearchParams({tab:'handouts'});if(form.unit.value)q.set('unit',form.unit.value);if(form.level.value)q.set('level',form.level.value);try{history.replaceState(null,'','#/learn/guide?'+q);}catch(e){}load();});
    let me=null;
    try{me=typeof cmLoadMe==='function'?await cmLoadMe():null;}catch(e){}
    const admin=me?.role==='admin';
    if(admin)adminForm(document.getElementById('hoAdmin'),()=>load());
    async function load(){
      const list=document.getElementById('hoList');if(!list)return;
      const q=new URLSearchParams();if(form.unit.value)q.set('unit',form.unit.value);if(form.level.value)q.set('level',form.level.value);if(admin)q.set('all','1');
      let res;try{res=await api('GET','/learn/handouts'+(q.toString()?'?'+q:''));}catch(e){list.innerHTML=`<div class="gd-empty"><p>${T('핸드아웃 목록을 불러오지 못했습니다.','Could not load the handouts.')} ${esc(errText(e))}</p><button type="button" class="hm-go gd-btn" id="hoRetry">${T('다시 불러오기','Try again')}</button></div>`;document.getElementById('hoRetry').onclick=load;return;}
      if(!list.isConnected)return;
      const hs=res.handouts||[];
      if(!hs.length){list.innerHTML=`<div class="gd-empty"><p>${form.unit.value||form.level.value?T('이 단원이나 단계에는 아직 핸드아웃이 없습니다. 필터를 바꾸거나 교재의 글을 읽어 보세요.','No handouts for this unit or step yet. Change the filter, or read the guide’s chapters.'):T('아직 올라온 핸드아웃이 없습니다. 그동안 교재의 글을 읽어 보세요.','No handouts yet. Meanwhile, read the guide’s chapters.')}</p><a class="hm-go gd-btn" href="#/learn/guide">${T('교재 읽기','Read the guide')}</a></div>`;return;}
      list.innerHTML=`<ul class="ho-list">${hs.map(h=>{const name=ko()?(h.title_ko||h.title_en):(h.title_en||h.title_ko),sum=ko()?(h.summary_ko||h.summary_en):(h.summary_en||h.summary_ko),u=h.unit&&unitInfo(h.unit);
        return `<li class="ho-item" data-id="${h.id}"><div class="ho-main"><h3>${esc(name)}${h.status==='hidden'?` <span class="learn-state">${T('숨김','Hidden')}</span>`:''}</h3>
          <p class="ho-meta">${[u?esc(u.name):'',h.level?esc(stageText(h.level)):'','PDF · '+size(h.bytes)].filter(Boolean).join(' · ')}</p>${sum?`<p class="ho-sum">${esc(sum)}</p>`:''}</div>
          <div class="ho-acts">${h.status==='public'?`<a class="hm-go gd-btn" href="${esc(fileUrl(h))}" target="_blank" rel="noopener">${T('열기','Open')}</a>`:`<button type="button" class="hm-go gd-btn" data-ho="open">${T('열기','Open')}</button>`}
          ${admin?`<button type="button" class="gd-btn2" data-ho="edit">${T('고치기','Edit')}</button><button type="button" class="gd-btn2" data-ho="toggle">${h.status==='public'?T('숨기기','Hide'):T('공개하기','Publish')}</button><button type="button" class="gd-btn2 ho-del" data-ho="delete">${T('지우기','Delete')}</button>`:''}</div>
          <div class="ho-edit" hidden></div></li>`;}).join('')}</ul>`;
      list.onclick=async e=>{
        const b=e.target.closest('[data-ho]');if(!b)return;const li=b.closest('.ho-item'),h=hs.find(x=>String(x.id)===li.dataset.id);if(!h)return;
        try{
          if(b.dataset.ho==='open'){const w=window.open('','_blank');const res=await fetch(fileUrl(h),{headers:{Authorization:'Bearer '+(typeof cmTok==='function'?cmTok():'')}});if(!res.ok)throw{code:'not_found'};const url=URL.createObjectURL(await res.blob());if(w)w.location=url;else location.href=url;return;}
          if(b.dataset.ho==='toggle'){await api('PATCH','/learn/handouts/'+h.id,{status:h.status==='public'?'hidden':'public'});return load();}
          if(b.dataset.ho==='delete'){if(!confirm(T('이 핸드아웃과 파일을 지울까요? 되돌릴 수 없습니다.','Delete this handout and its file? This cannot be undone.')))return;await api('DELETE','/learn/handouts/'+h.id);return load();}
          if(b.dataset.ho==='edit'){const ed=li.querySelector('.ho-edit');ed.hidden=!ed.hidden;if(!ed.hidden){ed.innerHTML=fieldsHtml(h)+`<p class="ho-row"><button type="button" class="hm-go gd-btn" data-ho="save">${T('저장','Save')}</button></p><p class="ho-msg" role="status"></p>`;}return;}
          if(b.dataset.ho==='save'){const ed=li.querySelector('.ho-edit'),v=n=>ed.querySelector(`[name="${n}"]`).value;
            await api('PATCH','/learn/handouts/'+h.id,{title_ko:v('title_ko'),title_en:v('title_en'),summary_ko:v('summary_ko'),summary_en:v('summary_en'),unit:v('unit')||null,level:v('level')?+v('level'):null,status:ed.querySelector('[name="status"]:checked').value});return load();}
        }catch(err){const msg=li.querySelector('.ho-msg');if(msg)msg.textContent=errText(err);else alert(errText(err));}
      };
    }
    load();
  }
  function fieldsHtml(h={}){
    const st=h.status||'hidden';
    return `<div class="ho-grid"><label>${T('제목 (한국어)','Title (Korean)')}<input name="title_ko" maxlength="120" value="${esc(h.title_ko||'')}"></label>
      <label>${T('제목 (영어)','Title (English)')}<input name="title_en" maxlength="120" value="${esc(h.title_en||'')}"></label>
      <label>${T('요약 (한국어)','Summary (Korean)')}<textarea name="summary_ko" maxlength="600" rows="2">${esc(h.summary_ko||'')}</textarea></label>
      <label>${T('요약 (영어)','Summary (English)')}<textarea name="summary_en" maxlength="600" rows="2">${esc(h.summary_en||'')}</textarea></label>
      <label>${T('단원','Unit')}<select name="unit">${unitOptions(h.unit||'')}</select></label>
      <label>${T('단계','Step')}<select name="level">${levelOptions(h.level||'')}</select></label></div>
      <fieldset class="ho-status"><legend>${T('공개 여부','Visibility')}</legend><label><input type="radio" name="status" value="public"${st==='public'?' checked':''}> ${T('공개','Public')}</label><label><input type="radio" name="status" value="hidden"${st==='hidden'?' checked':''}> ${T('숨김 (관리자만 봄)','Hidden (administrators only)')}</label></fieldset>`;
  }
  function adminForm(box,done){
    box.innerHTML=`<details class="ho-up"><summary>${T('핸드아웃 올리기 (관리자)','Upload a handout (administrators)')}</summary>
      <form id="hoUp" class="ho-form">${fieldsHtml({status:'public'})}<label class="ho-file">${T('PDF 파일 (25 MB까지)','PDF file (up to 25 MB)')}<input type="file" name="file" accept="application/pdf,.pdf" required></label>
      <p class="ho-row"><button type="submit" class="hm-go gd-btn">${T('올리기','Upload')}</button></p><p class="ho-msg" role="status" id="hoMsg"></p></form></details>`;
    const f=document.getElementById('hoUp'),msg=document.getElementById('hoMsg');
    f.onsubmit=async e=>{
      e.preventDefault();const file=f.file.files[0];
      if(!file){msg.textContent=errText({code:'file_required'});return;}
      if(file.size>25*1024*1024){msg.textContent=errText({code:'file_too_large'});return;}
      const head=new Uint8Array(await file.slice(0,5).arrayBuffer());if(String.fromCharCode(...head)!=='%PDF-'){msg.textContent=errText({code:'pdf_only'});return;}
      const fd=new FormData();for(const k of ['title_ko','title_en','summary_ko','summary_en','unit','level'])fd.set(k,f[k].value);fd.set('status',f.querySelector('[name="status"]:checked').value);fd.set('file',file);
      msg.textContent=T('올리는 중…','Uploading…');f.querySelector('button[type="submit"]').disabled=true;
      try{
        const res=await fetch((typeof cmBase==='function'?cmBase():'')+'/api/learn/handouts',{method:'POST',headers:{Authorization:'Bearer '+(typeof cmTok==='function'?cmTok():'')},body:fd});
        const j=await res.json().catch(()=>({error:'server_error'}));if(!res.ok)throw{code:j.error};
        msg.textContent=T('올렸습니다.','Uploaded.');f.reset();if(typeof cmInvalidate==='function')cmInvalidate();done();
      }catch(err){msg.textContent=errText(err);}finally{f.querySelector('button[type="submit"]').disabled=false;}
    };
  }

  return{parseFrontMatter,renderMarkdown,plainText,WORDS,view,mount};
});
