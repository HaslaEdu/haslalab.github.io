const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
function config(file,name){const code=fs.readFileSync(path.join(root,file),'utf8').replace(/^export /gm,'');return vm.runInNewContext(code+'\n'+name);}
function asset(url){
  assert.match(url,/^archive-media\/(books|schools)\/[a-z0-9_.-]+\.(webp|png|jpe?g|svg|gif)(?:\?v=[a-f0-9]+)?$/);
  const filename=path.resolve(root,url.split('?')[0]);assert(filename.startsWith(root+path.sep));
  const data=fs.readFileSync(filename);assert(data.length>100&&data.length<512*1024,'thumbnail/mark must be a bounded real asset');
  const ext=path.extname(filename);
  if(ext==='.svg'){
    const text=data.toString('utf8');assert.match(text,/<svg\b/);assert.doesNotMatch(text,/<script\b|\bon\w+\s*=|<!DOCTYPE|<foreignObject|(?:href|src)\s*=\s*["'](?:https?:|javascript:|data:text)/i);
  }else if(ext==='.webp'){assert.equal(data.toString('ascii',0,4),'RIFF');assert.equal(data.toString('ascii',8,12),'WEBP');}
  else if(ext==='.png')assert.equal(data.subarray(0,8).toString('hex'),'89504e470d0a1a0a');
  else if(ext==='.gif')assert.match(data.toString('ascii',0,6),/^GIF8[79]a$/);
  else assert.equal(data.subarray(0,2).toString('hex'),'ffd8');
}
test('every current textbook has a real bounded cover or source title image, without private origins',()=>{
  const media=config('archive-book-media.js','ARCHIVE_BOOK_MEDIA');assert.equal(Object.keys(media).length,22);
  for(const [id,item]of Object.entries(media)){
    assert.match(id,/^src_[a-f0-9]{64}$/);asset(item.image_url);assert(item.alt&&item.title&&item.provenanceKind);
    if(item.sourceUrl)assert.equal(new URL(item.sourceUrl).protocol,'https:');
    assert.doesNotMatch(JSON.stringify(item),/drive\.google\.com|(?:^|["'\s])[A-Z]:[\\/]|file:\/\/|sources\/[a-f0-9]{64}\.pdf|\.codex-remote-attachments|OneDrive/i);
  }
});
test('schools group all verified course papers once and add SNU/KAIST official physics and math materials',()=>{
  const {institutions}=config('archive-school-media.js','ARCHIVE_SCHOOL_MEDIA'),ids=new Set(),sources=new Set();
  for(const school of institutions){
    assert.match(school.id,/^[a-z][a-z0-9-]{0,63}$/);assert(!ids.has(school.id));ids.add(school.id);
    assert(school.name.ko&&school.name.en);asset(school.logo_url);if(school.dark_logo_url)asset(school.dark_logo_url);
    for(const id of school.source_ids){assert.match(id,/^src_[a-f0-9]{64}$/);assert(!sources.has(id),'one paper cannot appear in two schools');sources.add(id);}
    for(const links of Object.values(school.materials||{}))for(const link of links){const url=new URL(link.url);assert.equal(url.protocol,'https:');assert(link.label.ko&&link.label.en);}
  }
  assert.equal(sources.size,115);
  for(const id of ['mit','princeton','yale','snu','kaist'])assert(ids.has(id));
  for(const id of ['snu','kaist']){
    const school=institutions.find(s=>s.id===id);assert.equal(school.source_ids.length,0,'official external materials must not invent canonical questions');
    for(const subject of ['physics','mathematics']){
      assert(school.materials[subject].length>0);
      for(const link of school.materials[subject])assert(new URL(link.url).hostname.endsWith(id==='snu'?'.snu.ac.kr':'.kaist.ac.kr'));
    }
  }
});
test('stored chapter titles cover four source-profile books in Korean and English without repeated chapter numbers',()=>{
  const media=config('archive-book-media.js','ARCHIVE_BOOK_MEDIA');
  for(const [file,count,example]of [['zangwill-modern-electrodynamics-2013.webp',24,'Mathematical Preliminaries'],['jackson-classical-electrodynamics-3.webp',16,'Introduction to Electrostatics'],['purcell-morin-electricity-magnetism-3.webp',14,'Electrostatics: charges and fields'],['carroll-ostlie-modern-astrophysics-2.webp',30,'The Celestial Sphere']]){
    const item=Object.values(media).find(x=>x.image_url.endsWith('/'+file));assert(item);assert.equal(Object.keys(item.chapter_titles).length,count);assert.equal(item.chapter_titles['1'].en,example);
    for(const [chapter,title]of Object.entries(item.chapter_titles)){assert(title.ko&&title.en);assert.doesNotMatch(title.en,new RegExp('^'+chapter+'\\s+'));assert.doesNotMatch(title.ko,/^제\d+장/);}
  }
  const old=Object.values(media).find(x=>x.image_url.endsWith('/zangwill-modern-electrodynamics-2012.webp')),current=Object.values(media).find(x=>x.image_url.endsWith('/zangwill-modern-electrodynamics-2013.webp'));assert.deepEqual(old.chapter_titles,current.chapter_titles);
});
