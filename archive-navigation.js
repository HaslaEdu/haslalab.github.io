(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  if(root)root.HL_ARCHIVE=api;
})(typeof window==='object'?window:null,function(){
  'use strict';
  const subjects={phys:'physics',astro:'astronomy',math:'mathematics',chem:'chemistry',bio:'biology',earth:'earth_science',info:'informatics'};
  const aliases={physics:'phys',astronomy:'astro',mathematics:'math',chemistry:'chem',biology:'bio',earth_science:'earth',informatics:'info',cs:'info'};
  const categories={contests:'contest',books:'book',schools:'course'};
  const topics=new Set(['classical_mechanics','electromagnetism','thermodynamics','optics','quantum_mechanics','relativity','special_relativity','general_relativity','statistical_mechanics','oscillations_waves','mathematical_methods','astronomy_astrophysics','mixed','mathematics','chemistry','biology','earth_science','informatics']);
  const slug=value=>Object.hasOwn(subjects,value)||value==='sci'?value:aliases[value]||'';
  function clean(input,{legacy=false}={}){
    const src=input instanceof URLSearchParams?input:new URLSearchParams(input||''),out=new URLSearchParams();
    const one=key=>src.getAll(key).length===1?src.get(key):null;
    for(const [key,pattern] of [['source',/^src_[a-f0-9]{64}$/],['problem',/^q_[a-f0-9]{64}$/],['stars',/^[1-5]$/],['competition',/^[a-z][a-z0-9_-]{1,49}$/],['type',/^(theory|experiment)$/]]){const v=one(key);if(v&&pattern.test(v))out.set(key,v);}
    const q=one('q');if(q&&q.length<=600&&!/[\u0000-\u001f\u007f]/.test(q))out.set('q',q);
    const year=one('year');if(/^\d{4}$/.test(year||'')&&Number(year)>=1800&&Number(year)<=2199)out.set('year',year);
    const topic=one('topic')||one('subject');if(topics.has(topic))out.set('topic',topic);
    const school=one('school');if(school&&/^[a-z0-9][a-z0-9-]{0,63}$/.test(school))out.set('school',school);
    const cursor=one('cursor');if(cursor&&cursor.length<=2800&&/^(?:q_[a-f0-9]{64}|sc_[A-Za-z0-9_-]+|o_(?:0|[1-9]\d{0,2}))$/.test(cursor))out.set('cursor',cursor);
    if(one('view')==='web')out.set('view','web');
    if(legacy){
      const collection=one('collection');if(Object.values(subjects).includes(collection))out.set('collection',collection);
      const kind=one('kind');if(Object.values(categories).includes(kind))out.set('kind',kind);
      const lang=one('lang');if(['ko','en'].includes(lang))out.set('lang',lang);
    }
    return out;
  }
  function href(category='contests',subject='',params=''){
    if(!Object.hasOwn(categories,category))category='contests';
    const sub=slug(subject)|| (category==='contests'?'':'phys');
    const tail=clean(params).toString();
    return '#/archive/'+category+(sub?'/'+sub:'')+(tail?'?'+tail:'');
  }
  function parse(hash){
    const text=String(hash||''),[path,query='']=text.split('?'),parts=path.replace(/^#\/?/,'').split('/').filter(Boolean);
    if(parts[0]!=='archive')return null;
    if(parts[1]==='open')return {category:'books',kind:'book',sub:'phys',collection:'physics',params:clean(query,{legacy:true}),baseHash:'#/archive/open',resolveLegacy:true};
    const category=Object.hasOwn(categories,parts[1])?parts[1]:'contests';
    const sub=slug(Object.hasOwn(categories,parts[1])?parts[2]:parts[1])||(category==='contests'?'':'phys');
    const params=clean(query),baseHash=href(category,sub);
    return {category,kind:categories[category],sub,collection:subjects[sub]||'physics',params,baseHash,resolveLegacy:false};
  }
  function legacy(hash){
    const text=String(hash||''),[path,query='']=text.split('?'),parts=path.replace(/^#\/?/,'').split('/').filter(Boolean);
    if(parts[0]==='comps'){
      const category=Object.hasOwn(categories,parts[1])?parts[1]:'contests';
      return href(category,Object.hasOwn(categories,parts[1])?parts[2]:parts[1],query);
    }
    if(parts[0]==='learn'&&['physics','astronomy'].includes(parts[1])&&parts[2]==='library'){
      const params=clean(query,{legacy:true});params.set('collection',parts[1]);
      return params.has('problem')||params.has('source')?'#/archive/open?'+params:href('books',parts[1],params);
    }
    if(parts[0]==='archive'&&parts[1]!=='open'){
      const route=parse(text),canonical=href(route.category,route.sub,route.params);
      return canonical===text?null:canonical;
    }
    return null;
  }
  return {subjects,categories,slug,clean,href,parse,legacy};
});
