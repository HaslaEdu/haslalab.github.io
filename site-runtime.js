/* Small routing and request helpers. Large archive datasets are loaded only when needed. */
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.HL_RUNTIME=api;
})(typeof globalThis==='object'?globalThis:this,function(){
  'use strict';
  const publicPaths=new Set(['/health','/boards','/posts','/lab/stats','/lab/contest/catalog','/pay/config']);
  function requestPolicy(method,path){
    if(String(method).toUpperCase()!=='GET')return{safe:false,public:false,ttl:0};
    const u=new URL(path,'https://api.invalid');
    if(u.searchParams.has('view'))return{safe:false,public:false,ttl:0};
    const publicRead=publicPaths.has(u.pathname);
    const safe=publicRead||/^\/(?:me|users|nick-check|weekly|rank|ranking|problems(?:\/\d+)?|submissions(?:\/\d+)?|lab\/(?:bootstrap|active|tokens|sessions(?:\/\d+)?))$/.test(u.pathname);
    const ttl=publicRead?u.pathname==='/health'||u.pathname==='/pay/config'||u.pathname==='/lab/contest/catalog'?300000:u.pathname==='/boards'?30000:u.pathname==='/lab/stats'?15000:5000:0;
    return{safe,public:publicRead,ttl};
  }
  function canonicalPath(path){const u=new URL(path,'https://api.invalid');u.searchParams.sort();return u.pathname+u.search;}
  const clone=value=>value===undefined?value:typeof structuredClone==='function'?structuredClone(value):JSON.parse(JSON.stringify(value));
  function createRequestCache({now=Date.now,maxEntries=100}={}){
    const values=new Map(),pending=new Map();let generation=0,scope='',freshUntil=0;
    function invalidate(fresh=false){generation++;values.clear();pending.clear();if(fresh)freshUntil=now()+30000;}
    function run({method='GET',path,base='',token='',lang=''},send){
      method=String(method).toUpperCase();
      const next=JSON.stringify([base,token,lang]);
      if(scope!==next){scope=next;invalidate();}
      const policy=requestPolicy(method,path);
      if(method!=='GET'){invalidate(true);return Promise.resolve().then(send).finally(()=>invalidate(true));}
      if(!policy.safe)return Promise.resolve().then(send);
      const key=next+' '+canonicalPath(path),cached=values.get(key);
      if(cached&&cached.until>now())return Promise.resolve(clone(cached.value));
      if(cached)values.delete(key);
      let p=pending.get(key);
      if(!p){
        const at=generation;
        p=Promise.resolve().then(()=>send({bypassCache:policy.public&&now()<freshUntil})).then(value=>{
          if(at===generation&&policy.ttl>0){
            values.delete(key);values.set(key,{until:now()+policy.ttl,value:clone(value)});
            while(values.size>maxEntries)values.delete(values.keys().next().value);
          }
          return value;
        }).finally(()=>{if(pending.get(key)===p)pending.delete(key);});
        pending.set(key,p);
      }
      return p.then(clone);
    }
    return{run,invalidate};
  }
  function routeNeeds(hash,{known=[],theory=[],versions={}}={}){
    const [first,second]=String(hash||'').replace(/^#\/?/,'').split('?')[0].split('/').filter(Boolean);
    if(['weekly','rank','me','login','signup','oauth','lab'].includes(first)||first==='community'&&['login','signup'].includes(second))return['arena'];
    if(first==='iypt')return['iypt'];
    if(first==='usaco')return['usaco'];
    const russian=['rupho','ruphow','ruphox','ruphoy'].includes(first);
    if(russian)return['theory:rupho','theory:ruphow','theory:ruphox','theory:ruphoy','rupho'];
    if(!known.includes(first))return[];
    const list=theory.includes(first)?['theory:'+first]:[];
    if(first==='kmo'||first==='kmchc')list.push('contest:'+first);
    return list.filter(key=>versions[key]);
  }
  function createDataLoader({versions={},loadScript,onLoad=()=>{}}){
    const pending=new Map(),loaded=new Set();
    function load(key){
      if(loaded.has(key))return Promise.resolve();
      if(pending.has(key))return pending.get(key);
      if(!versions[key])return Promise.reject(new Error('Unknown module '+key));
      const p=Promise.resolve().then(()=>loadScript(versions[key],key)).then(()=>{onLoad(key);loaded.add(key);}).finally(()=>pending.delete(key));
      pending.set(key,p);return p;
    }
    return{load,ensure:keys=>Promise.all(keys.map(load)),has:key=>loaded.has(key),ready:keys=>keys.every(key=>loaded.has(key))};
  }
  return{requestPolicy,canonicalPath,createRequestCache,routeNeeds,createDataLoader};
});
