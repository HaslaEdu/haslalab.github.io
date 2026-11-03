const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),{createHash}=require('node:crypto');
const {JSDOM}=require('../community/node_modules/jsdom');
const root=path.resolve(__dirname,'../archive-media/subjects');
const subjects=['phys','chem','bio','earth','astro','math','info'];
test('book and school subject navigation uses original subject art while contest navigation keeps its logos',()=>{
  const vm=require('node:vm'),index=fs.readFileSync(path.resolve(__dirname,'../index.html'),'utf8');
  const code=index.slice(index.indexOf('function archiveSubjects('),index.indexOf('function viewArchiveDigital('));
  const context={lang:'ko',LOGO_V:'test',SUBJ:[...subjects,'sci'].map(k=>({k,ko:k,en:k,logo:'logo-'+k,comps:['ipho']})),DATA:{ipho:{}},UI:{ko:{subjLabel:'분야',subjN:n=>String(n),subjSoon:'준비중'}},archiveHref:(category,subject)=>'#/archive/'+category+'/'+subject,logoSource:key=>'logo/'+key+'.svg'};
  vm.createContext(context);vm.runInContext(code,context);
  for(const category of ['books','schools','contests']){
    const dom=new JSDOM(context.archiveSubjects(category,'phys'));
    try{
      const nav=dom.window.document.querySelector('nav'),images=[...nav.querySelectorAll('img')];
      if(category==='contests'){
        assert.equal(images.length,8);assert(!nav.classList.contains('archive-library-subjects'));
        assert(images.every(img=>img.hasAttribute('data-logo-key')&&!img.hasAttribute('data-subject-art')));
      }else{
        assert.equal(images.length,7);assert(nav.classList.contains('archive-library-subjects'));
        assert.deepEqual(images.map(img=>img.dataset.subjectArt),subjects);
        for(const img of images){assert.equal(img.getAttribute('src'),'archive-media/subjects/'+img.dataset.subjectArt+'.svg?v=1');assert(!img.hasAttribute('data-logo-key'));assert(!img.hasAttribute('onerror'));assert.equal(img.getAttribute('alt'),'');}
        assert.equal(nav.querySelector('a').getAttribute('aria-current'),'true');
      }
    }finally{dom.window.close();}
  }
});
test('seven subject illustrations are distinct code-native SVGs with transparent page backgrounds',()=>{
  const hashes=new Set();
  for(const subject of subjects){
    const source=fs.readFileSync(path.join(root,subject+'.svg'),'utf8');
    assert(Buffer.byteLength(source)>500&&Buffer.byteLength(source)<8000,'subject art stays small enough for navigation');
    const hash=createHash('sha256').update(source).digest('hex');assert(!hashes.has(hash),'each subject must have its own illustration');hashes.add(hash);
    const dom=new JSDOM(source,{contentType:'image/svg+xml'});
    try{
      const svg=dom.window.document.documentElement;
      assert.equal(svg.tagName,'svg');assert.equal(svg.namespaceURI,'http://www.w3.org/2000/svg');assert.equal(svg.getAttribute('viewBox'),'0 0 112 112');assert.equal(svg.getAttribute('fill'),'none');
      assert(svg.querySelector('title')?.textContent.trim());assert(svg.querySelectorAll('path,circle,ellipse,rect,polygon,line').length>=8);
      assert.equal(svg.querySelector('script,foreignObject,image,use,text,style,filter'),null,'illustrations contain neither executable nor raster/font content');
      for(const node of [svg,...svg.querySelectorAll('*')])for(const attribute of node.attributes){
        if(attribute.name==='xmlns'){assert.equal(attribute.value,'http://www.w3.org/2000/svg');continue;}
        assert(!/^on/i.test(attribute.name));assert(!/(?:href|src)$/i.test(attribute.name));
        assert(!/(?:https?:|javascript:|data:|url\s*\()/i.test(attribute.value));
      }
      for(const rect of svg.querySelectorAll('rect')){
        const width=Number(rect.getAttribute('width')),height=Number(rect.getAttribute('height'));
        assert(width<100||height<100,'an opaque canvas-sized backdrop would break light/dark integration');
      }
      assert.doesNotMatch(source,/<\?xml-stylesheet|<!DOCTYPE|#(?:fff(?:fff)?|000(?:000)?)\b/i);
      assert.match(source,/#9270D1/);assert.match(source,/#318FA9/);
    }finally{dom.window.close();}
  }
  assert.equal(hashes.size,7);
});
