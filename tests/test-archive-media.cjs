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
test('PNS volumes keep distinct bilingual subjects prominent while retaining their published titles',()=>{
  const media=config('archive-book-media.js','ARCHIVE_BOOK_MEDIA');
  const volumes=Object.values(media).filter(item=>item.short_title==='PNS');
  assert.equal(volumes.length,5);
  const subjects=new Set();
  for(const item of volumes){
    assert.equal(item.topic_prominent,true);assert(item.topic_label.ko&&item.topic_label.en);
    assert.equal(item.full_title,item.title);assert.match(item.full_title,/^Problems and Solutions on /);
    assert(item.title.includes(item.topic_label.en),'the displayed subject must belong to this volume');
    assert(!subjects.has(item.topic_label.ko));subjects.add(item.topic_label.ko);
  }
  assert.deepEqual([...subjects].sort(),['광학','양자역학','역학','열역학·통계역학','전자기학'].sort());
});
test('GTP and Puzzling shortcuts retain discoverable full titles and only Puzzling bypasses the contents step',()=>{
  const media=config('archive-book-media.js','ARCHIVE_BOOK_MEDIA');
  const abbreviated=Object.values(media).filter(item=>item.short_title);
  assert.equal(abbreviated.length,9);
  for(const item of abbreviated)assert.equal(item.full_title,item.title,'a shortcut must not erase the published title');
  const gtp=abbreviated.filter(item=>/^GTP /.test(item.short_title));
  assert.deepEqual(gtp.map(item=>item.short_title),['GTP 1','GTP 2']);
  assert.equal(gtp[0].topic_label.en,'Mechanics, Relativity, and Electrodynamics');
  assert.equal(gtp[1].topic_label.en,'Thermodynamics, Statistical Physics, and Quantum Mechanics');
  const flat=Object.entries(media).filter(([,item])=>item.browse_mode==='flat');
  assert.deepEqual(flat.map(([,item])=>item.short_title).sort(),['MORE PUZZLING','PUZZLING']);
  assert.deepEqual(flat.map(([id])=>id).sort(),['src_4827842a539dbd74390bdaf67e03ffb4720bfd0e41415009a903f3d261e1bd6c','src_efbf5a08177fd3dfcb26a44ab215d896df275b7905bdd0276ac60b3235d97be0'].sort());
  assert(flat.every(([,item])=>!item.chapter_titles),'flat navigation must not fabricate a table of contents');
});
test('PNS and GTP classifications retain their actual source keys and printed problem order with human bilingual labels',()=>{
  const media=config('archive-book-media.js','ARCHIVE_BOOK_MEDIA');
  const books=Object.values(media).filter(item=>item.short_title==='PNS'||/^GTP /.test(item.short_title||''));
  assert.equal(books.length,7);assert.equal(books.reduce((n,item)=>n+item.chapter_order.length,0),57);
  for(const item of books){
    assert.equal(new Set(item.chapter_order).size,item.chapter_order.length);
    assert.deepEqual([...item.chapter_order].sort(),Object.keys(item.chapter_titles).sort());
    for(const key of item.chapter_order){const title=item.chapter_titles[key];assert(title.ko&&title.en);assert.doesNotMatch(title.ko,/^[a-z]+(?:-[a-z]+)+$/);assert.doesNotMatch(title.en,/^[a-z]+(?:-[a-z]+)+$/);}
  }
  const mechanics=books.find(item=>item.title==='Problems and Solutions on Mechanics');
  assert.deepEqual(Array.from(mechanics.chapter_order),['dynamics-of-a-point-mass','dynamics-of-point-mass-systems','rigid-body-dynamics','deformable-body-dynamics','lagrange-equations','small-oscillations','hamilton-canonical-equations','special-relativity']);
  assert.equal(mechanics.chapter_titles['dynamics-of-a-point-mass'].ko,'질점의 동역학');
  assert.deepEqual(Array.from(books.find(item=>item.short_title==='GTP 1').chapter_order),['Mechanics','Relativity','Electrodynamics']);
  assert.deepEqual(Array.from(books.find(item=>item.short_title==='GTP 2').chapter_order),['Thermodynamics and Statistical Physics','Quantum Mechanics']);
  const gtp=books.find(item=>item.short_title==='GTP 2');
  assert.equal(gtp.chapter_titles['Thermodynamics and Statistical Physics'].ko,'열역학과 통계물리');
  assert.equal(gtp.chapter_titles['Quantum Mechanics'].ko,'양자역학');
});
