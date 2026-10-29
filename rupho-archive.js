/* One public RuPhO archive; source keys remain stable for papers and timed exams. */
(function(root){
  "use strict";
  const stages=[
    {id:"final",key:"rupho",label:{ko:"결선 · 9·10·11학년",en:"Final · grades 9, 10, 11"}},
    {id:"w",key:"ruphow",label:{ko:"W · 선발 예비 과정",en:"W · preliminary selection"}},
    {id:"x",key:"ruphox",label:{ko:"X · 대표 선발 1차",en:"X · first selection"}},
    {id:"y",key:"ruphoy",label:{ko:"Y · 대표 선발 2차",en:"Y · second selection"}}
  ];
  let catalogues={};
  const byKey=key=>stages.find(s=>s.key===key);
  const byId=id=>stages.find(s=>s.id===String(id||"").toLowerCase())||stages[0];
  function initialize(data,theory){
    catalogues={};
    for(const stage of stages){
      if(!data[stage.key])continue;
      catalogues[stage.key]={...data[stage.key],abbr:"RuPhO",stage:stage.id};
      if(stage.id!=="final")delete data[stage.key];
    }
    if(!catalogues.rupho)return;
    const years=new Map();
    for(const stage of stages)for(const year of catalogues[stage.key]?.years||[]){
      const id=String(year.y);
      if(!years.has(id))years.set(id,{...year,problems:[]});
      years.get(id).problems.push(...year.problems);
    }
    data.rupho={...catalogues.rupho,plain:true,
      full:{ko:"전러시아 물리 올림피아드 · 대표 선발",en:"All-Russian Physics Olympiad · team selection"},
      years:[...years.values()].sort((a,b)=>Number(b.y)-Number(a.y)),
      stages:stages.filter(s=>catalogues[s.key]).map(s=>({id:s.id,key:s.key,label:s.label})),
      theoryCount:stages.reduce((n,s)=>n+Object.values(theory[s.key]||{}).reduce((a,t)=>a+(t.p?.length||Object.keys(t.f||{}).length),0),0)
    };
  }
  function route(hash){
    const [path,query=""]=String(hash||"").replace(/^#\/?/,"").split("?");
    const parts=path.split("/").filter(Boolean),legacy=byKey(parts[0]);
    const stage=parts[0]!=="rupho"&&legacy?legacy:byId(new URLSearchParams(query).get("stage"));
    return {stage:stage.id,key:stage.key,year:parts[1]||"",legacy:!!legacy&&parts[0]!=="rupho"};
  }
  function href(key,year=""){
    const stage=byKey(key)||byId(key);
    return "#/rupho"+(year?"/"+encodeURIComponent(year):"")+"?stage="+stage.id;
  }
  function canonical(hash){
    const r=route(hash);return r.legacy?href(r.key,r.year):null;
  }
  function availableYear(key,year){
    return (catalogues[key]?.years||[]).some(y=>String(y.y)===String(year));
  }
  function selector(key,year,lang){
    const active=byKey(key);if(!active)return "";
    const label=lang==="ko"?"RuPhO 단계 선택":"RuPhO stage";
    return `<nav class="rupho-stages" aria-label="${label}">${stages.filter(s=>catalogues[s.key]).map(s=>{
      const target=year==="exam"||availableYear(s.key,year)?year:"";
      return `<a href="${href(s.key,target)}"${s===active?' aria-current="page"':""}>${s.label[lang]}</a>`;
    }).join("")}</nav>`;
  }
  function decorate(key,html,year,lang){
    if(!byKey(key))return html;
    const nav=selector(key,year,lang);
    return html.replace('<div class="phead">',nav+'<div class="phead">')
      .replace(/href="#\/(rupho(?:w|x|y)?)(?:\/([^"?]*))?"/g,(_,source,part)=>`href="${href(source,part||"")}"`);
  }
  root.RUPHO_ARCHIVE={stages,initialize,route,href,canonical,selector,decorate,
    catalogue:key=>catalogues[key]||null,isStage:key=>!!byKey(key),
    sourceKeys:()=>stages.filter(s=>catalogues[s.key]).map(s=>s.key)};
})(typeof window!=="undefined"?window:globalThis);
