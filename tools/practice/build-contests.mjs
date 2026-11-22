/* Lists the olympiad problems the Learn section's "competition challenge" draws from: EuPhO, BAUPC, Eötvös,
   Physics Cup, WoPhO and OPhO, read from theory.js. Each entry links the papers and solutions on the PDF Worker
   exactly as the archive does (index.html thyUrl).  usage: node tools/practice/build-contests.mjs */
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
const root=path.resolve(path.dirname(new URL(import.meta.url).pathname),'../..');
const PDF_BASE='https://haslalab-pdf.haslalab.workers.dev/pdf/';
const url=f=>!f?null:/^https?:/.test(f)?f:/^pdfx\//.test(f)?PDF_BASE+f.replace(/^pdfx\/(?:([a-z]+)\/)?/,(m,d)=>'l/'+(d?d+'/':'')):PDF_BASE+f;
const ctx={window:{}};vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(root,'theory.js'),'utf8'),ctx);
const T=ctx.window.THEORY;
/* step on the learning path: an estimate per competition (olympiad 7–8, national team 9–10) */
const CONTESTS=[
  {key:'eotvos',name:{ko:'Eötvös 대회 (헝가리)',en:'Eötvös Competition (Hungary)'},step:7},
  {key:'opho',name:{ko:'OPhO 온라인 물리올림피아드',en:'Online Physics Olympiad (OPhO)'},step:7},
  {key:'wopho',name:{ko:'WoPhO 세계물리올림피아드',en:'World Physics Olympiad (WoPhO)'},step:8},
  {key:'baupc',name:{ko:'BAUPC 버클리 대학생 물리 대회',en:'Berkeley Undergraduate Physics Competition (BAUPC)'},step:8},
  {key:'physcup',name:{ko:'Physics Cup',en:'Physics Cup'},step:9},
  {key:'eupho',name:{ko:'EuPhO 유럽물리올림피아드',en:'European Physics Olympiad (EuPhO)'},step:9}];
const out=[];
for(const c of CONTESTS){
  const problems=[];
  for(const [year,y] of Object.entries(T[c.key]||{})){
    const titles=Object.fromEntries((y.p||[]).map(([k,t])=>[k,t]));
    for(const [key,f] of Object.entries(y.f||{})){
      if(f.component&&f.component!=='theory')continue;
      const papers={};
      for(const [lang,file] of Object.entries(f.papers||{}))papers[lang]=url(file);
      if(f.ko?.paper)papers.ko=url(f.ko.paper);
      if(!Object.keys(papers).length&&f.paper)papers[f.paperLang||'en']=url(f.paper);
      if(!Object.keys(papers).length)continue;
      const sols={};if(f.sol)sols.en=url(f.sol);if(f.ko?.sol)sols.ko=url(f.ko.sol);
      problems.push({id:`${c.key}-${year}-${key}`,year:Number(year),key,title:typeof titles[key]==='string'?titles[key]:'',papers,sols});
    }
  }
  problems.sort((a,b)=>a.year-b.year||a.key.localeCompare(b.key,undefined,{numeric:true}));
  out.push({...c,problems});
}
fs.writeFileSync(path.join(root,'practice/contests.json'),JSON.stringify({version:1,contests:out}));
console.log(out.map(c=>c.key+':'+c.problems.length).join(' '));
