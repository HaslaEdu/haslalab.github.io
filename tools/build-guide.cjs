#!/usr/bin/env node
/* Builds guide/index.json from the chapters in guide/<area>/<unit>/<chapter>.<ko|en>.md (see guide/README.md) and puts
   the digests of guide.js and guide.css on their tags in index.html.
     node tools/build-guide.cjs          write guide/index.json and index.html
     node tools/build-guide.cjs --check  fail if either is out of date or a chapter is broken */
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const ROOT=path.join(__dirname,'..'),G=require(path.join(ROOT,'guide.js')),P=require(path.join(ROOT,'learn-path.js'));
const read=f=>fs.readFileSync(path.join(ROOT,f),'utf8');
const digest=s=>crypto.createHash('sha256').update(s).digest('hex').slice(0,12);
const LANGS=['ko','en'],TEXT_MAX=6000;

function walk(dir){
  const out=[];
  for(const e of fs.readdirSync(path.join(ROOT,dir),{withFileTypes:true})){
    const rel=dir+'/'+e.name;
    if(e.isDirectory()){if(e.name!=='fig')out.push(...walk(rel));}
    else if(/\.(ko|en)\.md$/.test(e.name))out.push(rel);
  }
  return out;
}

/* the concept simulations by unit (concepts.js), for the chapter's "concept simulation" link */
function sims(){
  const out={};
  for(const m of read('concepts.js').matchAll(/\{id:'([a-z0-9-]+)',unit:'([a-z_]+\/[a-z_]+)',title:L\('([^']+)','([^']+)'\)/g))
    if(!out[m[2]])out[m[2]]={id:m[1],title:{ko:m[3],en:m[4]}};
  return out;
}

function build(){
  const errors=[],byChapter=new Map();
  for(const file of walk('guide')){
    const m=/^guide\/([a-z]+\/[a-z_]+)\/([a-z0-9-]+)\.(ko|en)\.md$/.exec(file);
    if(!m){errors.push(file+': the path must be guide/<area>/<unit>/<chapter>.<ko|en>.md with a lower-case chapter name');continue;}
    const [,unit,slug,lang]=m,src=read(file),key=unit+'/'+slug;
    const doc=G.renderMarkdown(src,lang),meta=doc.meta;
    for(const e of doc.errors)errors.push(file+': '+e);
    if(!P.SUBTOPICS.has(unit))errors.push(file+': '+unit+' is not a unit of learn-path.js');
    if(meta.unit!==unit)errors.push(file+': front matter unit '+meta.unit+' does not match the folder '+unit);
    if(!Number.isInteger(meta.level)||meta.level<1||meta.level>10)errors.push(file+': level must be a step from 1 to 10');
    if(!Number.isInteger(meta.order))errors.push(file+': order must be a whole number');
    if(!meta.title_ko||!meta.title_en)errors.push(file+': title_ko and title_en are both needed');
    if(/—/.test(src))errors.push(file+': use a colon, comma or full stop instead of an em dash');
    for(const f of doc.figures)if(!fs.existsSync(path.join(ROOT,'guide',f)))errors.push(file+': missing figure guide/'+f);
    const c=byChapter.get(key)||{unit,slug,files:{}};c.files[lang]={src,doc,meta};byChapter.set(key,c);
  }
  const chapters=[];
  for(const [key,c] of byChapter){
    for(const l of LANGS)if(!c.files[l])errors.push('guide/'+key+'.'+l+'.md is missing: every chapter has a Korean and an English file');
    if(errors.length)continue;
    const ko=c.files.ko.meta,en=c.files.en.meta;
    for(const k of ['title_ko','title_en','level','order'])if(ko[k]!==en[k])errors.push('guide/'+key+': '+k+' differs between the Korean and English files');
    if(c.files.ko.doc.equations!==c.files.en.doc.equations||c.files.ko.doc.tries!==c.files.en.doc.tries)errors.push('guide/'+key+': the Korean and English files have different numbers of equations or exercises');
    chapters.push({unit:c.unit,slug:c.slug,order:ko.order,level:ko.level,title:{ko:ko.title_ko,en:ko.title_en},
      summary:{ko:ko.summary||'',en:en.summary||''},v:digest(c.files.ko.src+'\n'+c.files.en.src),
      sections:Object.fromEntries(LANGS.map(l=>[l,c.files[l].doc.toc.map(s=>s.title)])),
      text:Object.fromEntries(LANGS.map(l=>[l,G.plainText(c.files[l].src).slice(0,TEXT_MAX)]))});
  }
  const keys=[...P.SUBTOPICS.keys()];
  chapters.sort((a,b)=>keys.indexOf(a.unit)-keys.indexOf(b.unit)||a.order-b.order||a.slug.localeCompare(b.slug));
  const index=JSON.stringify({version:1,chapters,sims:sims()},null,1)+'\n';
  let html=read('index.html');
  html=html.replace(/<script src="guide\.js(?:\?[^"\n]*)?"><\/script>/,'<script src="guide.js?v='+digest(read('guide.js'))+'"></script>')
    .replace(/<link rel="stylesheet" href="guide\.css(?:\?[^"\n]*)?">/,'<link rel="stylesheet" href="guide.css?v='+digest(read('guide.css'))+'">');
  return{errors,index,html,chapters};
}

if(require.main===module){
  const {errors,index,html,chapters}=build(),check=process.argv.includes('--check');
  if(errors.length){console.error(errors.join('\n'));process.exit(1);}
  const stale=[];
  if(!fs.existsSync(path.join(ROOT,'guide/index.json'))||read('guide/index.json')!==index)stale.push('guide/index.json');
  if(read('index.html')!==html)stale.push('index.html');
  if(check){if(stale.length){console.error('out of date: '+stale.join(', ')+' (run node tools/build-guide.cjs)');process.exit(1);}console.log('guide: '+chapters.length+' chapters, up to date');}
  else{fs.writeFileSync(path.join(ROOT,'guide/index.json'),index);fs.writeFileSync(path.join(ROOT,'index.html'),html);console.log('guide: '+chapters.length+' chapters'+(stale.length?', wrote '+stale.join(', '):', nothing changed'));}
}
module.exports={build};
