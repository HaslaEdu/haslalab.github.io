/* Turns the per-problem transcriptions of competition PDFs into the Learn section's structured problems.
   Inputs: TRANSCRIPTS_DIR/<pdf id>.json ({problems:[{key,title,blocks:[{t}|{fig}]}]}) and PAGES_DIR (from
   prepare-contest-pages.py: manifest.json and the cropped figures). Only figures a transcript places are copied.
   Writes practice/contest/<competition>.json and practice/contest/fig/*.webp, and marks practice/contests.json.
   usage: node tools/practice/build-contest-items.mjs TRANSCRIPTS_DIR PAGES_DIR */
import fs from 'node:fs';
import path from 'node:path';
const [tDir,pDir]=process.argv.slice(2);
const root=path.resolve(path.dirname(new URL(import.meta.url).pathname),'../..');
const out=path.join(root,'practice/contest');
fs.rmSync(out,{recursive:true,force:true});fs.mkdirSync(path.join(out,'fig'),{recursive:true});
const manifest=JSON.parse(fs.readFileSync(path.join(pDir,'manifest.json'),'utf8'));
const listPath=path.join(root,'practice/contests.json'),list=JSON.parse(fs.readFileSync(listPath,'utf8'));
const MAX_TEXT=20000,problems={},issues=[];
for(const c of list.contests){
  const items=[];
  for(const p of c.problems){
    const file=path.join(tDir,p.id+'.json');
    p.n=0;
    /* a combined paper ("T") repeats the separate T1, T2… of the same year: keep the separate ones */
    if(p.key==='T'&&c.problems.some(o=>o.year===p.year&&/^T\d+$/.test(o.key))){issues.push([p.id,'combined paper skipped (separate problems exist)']);continue;}
    if(!fs.existsSync(file)){issues.push([p.id,'no transcript']);continue;}
    let doc;try{doc=JSON.parse(fs.readFileSync(file,'utf8'));}catch(e){issues.push([p.id,'bad json']);continue;}
    const figs=new Map((manifest[p.id]?.figures||[]).map(f=>[f.id,f]));
    const keys=new Set();
    for(const q of doc.problems||[]){
      const key=String(q.key??'').trim().slice(0,12)||String(keys.size+1);
      if(keys.has(key)){issues.push([p.id,'duplicate key '+key]);continue;}
      const blocks=[];let chars=0;
      for(const b of q.blocks||[]){
        if(typeof b.t==='string'&&b.t.trim()){const t=b.t.trim();chars+=t.length;blocks.push({t});}
        else if(typeof b.fig==='string'){
          const f=figs.get(b.fig);if(!f){issues.push([p.id,'unknown figure '+b.fig]);continue;}
          const name=`${p.id}-${f.id}.webp`;
          fs.copyFileSync(path.join(pDir,p.id,f.id+'.webp'),path.join(out,'fig',name));
          blocks.push({f:name,w:f.w,h:f.h});
        }
      }
      if(!blocks.some(b=>b.t)||chars>MAX_TEXT){issues.push([p.id,'problem '+key+(chars>MAX_TEXT?' too long':' has no text')]);continue;}
      keys.add(key);
      items.push({id:`${p.id}~${key}`.replace(/[^\w~.-]/g,'_'),pdf:p.id,year:p.year,key,title:String(q.title||'').slice(0,120),b:blocks});
    }
    p.n=keys.size;
  }
  problems[c.key]=items.length;
  c.structured=items.length;
  fs.writeFileSync(path.join(out,c.key+'.json'),JSON.stringify({version:1,contest:c.key,items}));
}
fs.writeFileSync(listPath,JSON.stringify(list));
console.log('problems',problems,'total',Object.values(problems).reduce((a,b)=>a+b,0),'figures',fs.readdirSync(path.join(out,'fig')).length,'issues',issues.length);
for(const i of issues.slice(0,25))console.log('  ',...i);
