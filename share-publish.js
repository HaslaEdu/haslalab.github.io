/* window.HL_SHARE: publishing to the Workshop's sharing place, 작품 공유 (#/workshop/share; server:
   community/src/workshop-share.js). Any Workshop page can load this file (index.html, create.html, draw.html,
   teach.html) and call, with the member signed in on HaslaLab:

     HL_SHARE.publish({type, title, description, howto, notes, tags, topic, payload, thumbnail, creation_id})
       → Promise<{id, url}>          url is '#/workshop/share/<id>' (open it with HL_SHARE.open(id))
     HL_SHARE.update(id, {...the same fields, any subset})   → Promise<{ok}>   (the owner only)
     HL_SHARE.unpublish(id)                                   → Promise<{ok}>   (the owner; staff hide)
     HL_SHARE.get(id)        → Promise<{project, liked, faved, original, remixList}>   (a remix's draft too, for its owner)
     HL_SHARE.remix(id)      → Promise<{id, edit, remix_of}>  edit is the maker's address for the new draft
     HL_SHARE.open(id)       opens the project page in the site (the top window when embedded)
     HL_SHARE.check(input)   the same checks as the server, in the browser: [] or a list of error codes

   type        'sim' | 'python' | 'figure' | 'set'
   payload     sim:    {code, question?, answer?, answerUnit?}      code ≤ 60 000 characters
               python: {statement, starter?, grader}                statement ≤ 8 000, starter ≤ 20 000, grader ≤ 30 000 with def grade(
               figure: {scene}                                      a draw-scene.mjs scene, JSON ≤ 120 000 characters
               set:    {title?, info?, minutes?, items:[{key, pts?, own?:{q, answer?, unit?, sol?, choices?, correct?, fig?}}]}
                                                                    teach.js's paper, 1–100 items, JSON ≤ 400 000 characters
   title ≤ 80, description and howto ≤ 3 000, notes ≤ 2 000 (plain text: HTML tags are removed; **bold**, `code`, lines
   starting "- " and https links are drawn), tags: up to 8 words of ≤ 20 characters, topic one of TOPICS.
   thumbnail   a data URL ≤ 200 KB: image/png, image/jpeg, image/webp, or image/svg+xml with no script, event handler,
               link, style sheet, foreign object or external reference (HL_SHARE.svgThumb(svgText) makes one).
   creation_id publish a creation or a remix draft of one's own instead of making a new one (its type must match).
   Errors reject with {code, status}: login_required, bad_type, bad_title, bad_payload, payload_too_large, bad_thumbnail,
   bad_tags, bad_topic, hidden_by_staff, rate_limited, not_owner, not_found, network. Twenty new projects a day. */
(function(){
  'use strict';
  const TYPES=['sim','python','figure','set'],TOPICS=['mechanics','em','thermal','optics','waves','modern','other'];
  const LIMITS={title:80,description:3000,howto:3000,notes:2000,tags:8,tag:20,thumbBytes:200*1024,code:60000,statement:8000,starter:20000,grader:30000,figureJson:120000,setJson:400000,setItems:100};
  const base=()=>{let o='';try{o=localStorage.getItem('hlCmApi')||'';}catch(e){}
    if(!/^(?:https?:\/\/(?:localhost|127\.0\.0\.1)(?::\d+)?|https:\/\/[a-z0-9-]+\.haslalab\.workers\.dev)\/?$/.test(o))o='';
    const b=(o||'https://haslalab-community-edge.haslalab.workers.dev').replace(/\/+$/,'');
    return b==='https://haslalab-community.haslalab.workers.dev'?'https://haslalab-community-edge.haslalab.workers.dev':b;};
  const token=()=>{try{const v=localStorage.getItem('hlCmTok')||'';return /^[A-Za-z0-9_-]{20,4096}$/.test(v)?v:'';}catch(e){return '';}};
  async function api(method,path,body){
    const h={};if(token())h.Authorization='Bearer '+token();if(body)h['Content-Type']='application/json';
    let r;try{r=await fetch(base()+'/api'+path,{method,headers:h,body:body?JSON.stringify(body):undefined});}catch(e){throw{code:'network'};}
    const j=await r.json().catch(()=>({error:'server_error'}));
    if(!r.ok)throw{code:j.error||'server_error',status:r.status};
    return j;
  }
  const bytes=s=>new TextEncoder().encode(s).length;
  /** the server's checks, run first so a maker can say what is wrong before sending */
  function check(o,partial=false){
    const e=[],has=k=>!partial||(o&&k in o);
    if(!o||typeof o!=='object')return['bad_request'];
    if(!partial&&!TYPES.includes(o.type))e.push('bad_type');
    if(has('title')&&(typeof o.title!=='string'||!o.title.trim()||o.title.trim().length>LIMITS.title))e.push('bad_title');
    for(const k of ['description','howto','notes'])if(o[k]!=null&&(typeof o[k]!=='string'||o[k].length>LIMITS[k]))e.push('bad_'+k);
    if(o.tags!=null){const t=Array.isArray(o.tags)?o.tags:String(o.tags).split(',');if(t.filter(x=>String(x).trim()).length>LIMITS.tags||t.some(x=>[...String(x).trim()].length>LIMITS.tag))e.push('bad_tags');}
    if(o.topic!=null&&o.topic!==''&&!TOPICS.includes(o.topic))e.push('bad_topic');
    if(o.thumbnail){const s=String(o.thumbnail);if(!/^data:image\/(?:png|jpeg|webp|svg\+xml)[;,]/.test(s)||s.length>LIMITS.thumbBytes*1.4+100)e.push('bad_thumbnail');}
    const p=o.payload;
    if(p!=null||(!partial&&!o.creation_id)){
      if(!p||typeof p!=='object')e.push('bad_payload');
      else if(o.type==='sim'&&(typeof p.code!=='string'||!p.code.trim()||p.code.length>LIMITS.code))e.push('bad_payload');
      else if(o.type==='python'&&(typeof p.statement!=='string'||!p.statement.trim()||typeof p.grader!=='string'||!/def\s+grade\s*\(/.test(p.grader)))e.push('bad_payload');
      else if(o.type==='figure'&&JSON.stringify(p.scene||p).length>LIMITS.figureJson)e.push('payload_too_large');
      else if(o.type==='set'&&(!Array.isArray(p.items)||!p.items.length||p.items.length>LIMITS.setItems))e.push('bad_payload');
      else if(o.type==='set'&&JSON.stringify(p).length>LIMITS.setJson)e.push('payload_too_large');
    }
    return e;
  }
  /** an SVG text as a thumbnail data URL (the server still checks it), or '' when it is too large */
  function svgThumb(svg){const s=String(svg||'');if(bytes(s)>LIMITS.thumbBytes)return '';return 'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(s);}
  const pick=(o,keys)=>{const out={};for(const k of keys)if(o&&o[k]!==undefined)out[k]=o[k];return out;};
  const FIELDS=['type','title','description','howto','notes','tags','topic','payload','thumbnail','creation_id','remix_of'];
  function publish(o){const e=check(o);if(e.length)return Promise.reject({code:e[0],codes:e});return api('POST','/share',pick(o,FIELDS));}
  function update(id,o){const e=check(o,true);if(e.length)return Promise.reject({code:e[0],codes:e});return api('PATCH','/share/'+(+id),pick(o,FIELDS.filter(k=>k!=='type'&&k!=='creation_id')));}
  const unpublish=id=>api('DELETE','/share/'+(+id));
  const get=id=>api('GET','/share/'+(+id));
  const remix=id=>api('POST','/share/'+(+id)+'/remix',{});
  function open(id){const to='/#/workshop/share/'+(+id);try{if(window.top!==window){window.top.location.assign(to);return;}}catch(e){}location.assign(to);}
  window.HL_SHARE={publish,update,unpublish,get,remix,open,check,svgThumb,api,TYPES,TOPICS,LIMITS};
})();
