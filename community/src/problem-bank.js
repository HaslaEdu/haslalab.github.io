// Public digital statements; original PDFs/crops and paid OCR retain role gates.
// existing adapter; this module has no provider credentials or model implementation.
// The dedicated search database contains canonical statement drafts, not solutions.
import {BANK_SUBJECTS,BANK_FACETS_SCHEMA,difficultyInfo,starsFromRubric,recommendProblems,BANK_METHOD} from './problem-bank-model.js';
export const PROBLEM_BANK_SEARCH_SCHEMA = `
CREATE TABLE IF NOT EXISTS bank_search_documents(
 id INTEGER PRIMARY KEY,question_id TEXT NOT NULL,source_id TEXT NOT NULL,
 language TEXT NOT NULL CHECK(language IN ('en','ko')),text TEXT NOT NULL,
 search_text TEXT NOT NULL,text_sha256 TEXT NOT NULL,subjects_json TEXT NOT NULL CHECK(json_valid(subjects_json)),
 locator TEXT NOT NULL,original_number TEXT NOT NULL,chapter TEXT,level TEXT NOT NULL,source_title TEXT NOT NULL,
 review_status TEXT NOT NULL DEFAULT 'pending',unresolved_source INTEGER NOT NULL DEFAULT 0 CHECK(unresolved_source IN (0,1)),
 UNIQUE(question_id,language));
CREATE INDEX IF NOT EXISTS bank_search_source ON bank_search_documents(source_id,language,question_id);
CREATE VIRTUAL TABLE IF NOT EXISTS bank_search_fts USING fts5(search_text,content='bank_search_documents',content_rowid='id',tokenize='unicode61 remove_diacritics 2');
CREATE TRIGGER IF NOT EXISTS bank_search_ai AFTER INSERT ON bank_search_documents BEGIN
 INSERT INTO bank_search_fts(rowid,search_text) VALUES(new.id,new.search_text); END;
CREATE TRIGGER IF NOT EXISTS bank_search_ad AFTER DELETE ON bank_search_documents BEGIN
 INSERT INTO bank_search_fts(bank_search_fts,rowid,search_text) VALUES('delete',old.id,old.search_text); END;
CREATE TRIGGER IF NOT EXISTS bank_search_au AFTER UPDATE ON bank_search_documents BEGIN
 INSERT INTO bank_search_fts(bank_search_fts,rowid,search_text) VALUES('delete',old.id,old.search_text);
 INSERT INTO bank_search_fts(rowid,search_text) VALUES(new.id,new.search_text); END;
${BANK_FACETS_SCHEMA}`;

const PREFIX = '/api/problem-bank';
const HEX = '[a-f0-9]{64}', QID = new RegExp('^q_' + HEX + '$'), SID = new RegExp('^src_' + HEX + '$');
const AID = new RegExp('^(?:a_|sa_)' + HEX + '$'), HASH = /^[a-f0-9]{64}$/;
const SUBJECTS = new Set(BANK_SUBJECTS);
const DATABASES = {'haslalab-problem-bank':'BANK_REGISTRY','haslalab-problem-bank-02':'BANK2','haslalab-problem-bank-03':'BANK3'};
const PRIVATE = {visibility:'public',publication_ready:false,independent_scientific_review:'pending'};
const REQUEST_CACHE=Symbol('bankRequestCache');
const JSON_HEADERS = {'Content-Type':'application/json; charset=utf-8','Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'};
const MAX_ASSET = 4 * 1024 * 1024, MAX_BODY = 20000, MAX_SCAN = 8 * 1024 * 1024;
const CONTEXT_DEPTH = 2, CONTEXT_NODES = 8;
const CONTEXT_RELATION = /^[a-z][a-z0-9_]{0,79}$/;
const STOP = new Set('a an the of to in on for is are be and or not with from by as at this that it its find show calculate determine derive using use let given left right frac dfrac sqrt mathrm mathbf text begin end tag cdot times quad qquad'.split(' '));
const GREEK = {'α':'alpha','β':'beta','γ':'gamma','δ':'delta','ε':'epsilon','θ':'theta','λ':'lambda','μ':'mu','ν':'nu','π':'pi','ρ':'rho','σ':'sigma','τ':'tau','φ':'phi','χ':'chi','ψ':'psi','ω':'omega','Δ':'delta','Γ':'gamma','Ω':'omega','Σ':'sigma','Φ':'phi','Ψ':'psi'};
class BankError extends Error { constructor(status, code) { super(code); this.status=status; this.code=code; } }
const fail = (status, code) => { throw new BankError(status, code); };
const json = (body,status=200) => new Response(JSON.stringify(body),{status,headers:JSON_HEADERS});
const parse = (value,fallback={}) => { try { return typeof value==='string'?JSON.parse(value):value??fallback; } catch { return fallback; } };
const array = value => { const x=parse(value,[]); return Array.isArray(x)?x:[]; };
const rows = async (db,sql,args=[]) => (await db.prepare(sql).bind(...args).all()).results ?? [];
const first = async (db,sql,args=[]) => db.prepare(sql).bind(...args).first();
const binding = (env,key) => env[key]?.prepare ? env[key] : fail(503,'problem_bank_unavailable');
const routeDb = (env,name) => DATABASES[name] ? binding(env,DATABASES[name]) : fail(503,'problem_bank_route_unavailable');
const validId = (id,pattern,code='invalid_id') => pattern.test(id??'') ? id : fail(400,code);
const digest = async value => [...new Uint8Array(await crypto.subtle.digest('SHA-256',typeof value==='string'?new TextEncoder().encode(value):value))].map(x=>x.toString(16).padStart(2,'0')).join('');
async function optionalTable(env,key,table){
  const cache=env[REQUEST_CACHE]??new Map(),id=key+':'+table;
  if(!cache.has(id))cache.set(id,first(binding(env,key),"SELECT name FROM sqlite_master WHERE type='table' AND name=?",[table]).then(Boolean));
  return cache.get(id);
}
async function presentationJoin(env){return await optionalTable(env,'BANK_REGISTRY','bank_source_presentations')?' LEFT JOIN bank_source_presentations p ON p.source_id=r.source_id ':'';}
const presentationFields=join=>join?',p.display_title,p.title_en AS published_title_en,p.title_ko AS published_title_ko,p.primary_author,p.edition_label,p.collection AS library_collection':'';
async function facet(env,id){return await optionalTable(env,'BANK_SEARCH','bank_question_facets')?await first(binding(env,'BANK_SEARCH'),'SELECT * FROM bank_question_facets WHERE question_id=?',[id]):null;}
function facetInfo(row,fallbackCollection='physics'){
  const difficulty=difficultyInfo(row);
  return {stars:difficulty?.stars??null,difficulty,collection:row?.collection||fallbackCollection,...(row?.subjects_json?{subjects:array(row.subjects_json).filter(x=>SUBJECTS.has(x))}:{})};
}
async function scopedAssets(env,data,user,questionId){
  if(!data.length)return [];
  const admitted=[];
  if(await optionalTable(env,'BANK_REGISTRY','bank_asset_display_policy'))for(let start=0;start<data.length;start+=80){const batch=data.slice(start,start+80);admitted.push(...await rows(binding(env,'BANK_REGISTRY'),`SELECT asset_id,question_id,sha256,placement,review_status FROM bank_asset_display_policy WHERE asset_id IN (${batch.map(()=>'?').join(',')})`,batch.map(a=>a.id)));}
  const policies=new Map(admitted.filter(a=>a.question_id===questionId).map(a=>[a.asset_id,a]));
  if(user?.role==='admin')return data.map(a=>{const p=policies.get(a.id);return {...assetInfo(a),placement:p?.sha256===a.sha256&&p.placement==='inline'?'inline':p?.placement==='blocked'?'source_only':'reference',figure_review_status:p?.review_status||'pending'};});
  return data.filter(a=>{const p=policies.get(a.id);return a.role==='figure'&&p?.sha256===a.sha256&&['inline','reference'].includes(p.placement);}).map(a=>({...assetInfo(a),placement:policies.get(a.id).placement,figure_review_status:policies.get(a.id).review_status}));
}
async function figureVariants(env,questionId){
  if(!await optionalTable(env,'BANK_REGISTRY','bank_figure_variants'))return [];
  const data=await rows(binding(env,'BANK_REGISTRY'),"SELECT id,parent_asset_id,mime_type,sha256,width,height,spans_json,json_extract(proof_json,'$.figure_label') AS figure_label,json_extract(proof_json,'$.partial_source_figure') AS partial_source_figure FROM bank_figure_variants WHERE question_id=? AND verified_givens_only=1 ORDER BY id LIMIT 100",[questionId]);
  return data.filter(a=>/^f_[a-f0-9]{64}$/.test(a.id)&&HASH.test(a.sha256)).map(a=>({id:a.id,parent_asset_id:a.parent_asset_id,mime_type:a.mime_type,sha256:a.sha256,width:a.width,height:a.height,spans:array(a.spans_json),figure_label:safeString(a.figure_label,240),partial_source_figure:a.partial_source_figure===1,role:'figure',placement:'inline',figure_review_status:'source_verified',url:PREFIX+'/figures/'+a.id}));
}

function baseText(text) {
  return String(text).normalize('NFKC').replaceAll('−','-').replace(/[αβγδεθλμνπρστφχψωΔΓΩΣΦΨ]/g,c=>' '+GREEK[c]+' ').toLowerCase();
}
function numbers(text) {
  return [...new Set((baseText(text).match(/[+-]?(?:\d+\.\d+|\d+)(?:e[+-]?\d+)?/g)??[]).map(x=> {
    const m=x.match(/^([+-]?)(\d+)(?:\.(\d+))?(?:e([+-]?\d+))?$/);
    let digits=(m[2]+(m[3]??'')).replace(/^0+/,''),power=BigInt(m[4]??0)-BigInt((m[3]??'').length);
    if(!digits)return '0';
    while(digits.endsWith('0')){digits=digits.slice(0,-1);power++;}
    return (m[1]==='-'?'-':'')+digits+'e'+power;
  }))].slice(0,80);
}
const numberToken = n => 'zznum'+n.replaceAll('-','m').replaceAll('+','p').replaceAll('.','d');
function words(text) {
  const withoutNumbers=baseText(text).replace(/[+-]?(?:\d+\.\d+|\d+)(?:e[+-]?\d+)?/g,' ');
  return (withoutNumbers.match(/[\p{L}\p{N}]+/gu)??[]).filter(x=>!STOP.has(x)&&x.length<=80);
}
// Share this exact helper with the importer so numeric factors and Greek symbols match.
export function problemBankIndexText(text) { return [...words(text),...numbers(text).map(numberToken)].join(' '); }
function features(text) {
  const numeric=numbers(text), terms=[...new Set([...numeric.map(numberToken),...words(text)])].slice(0,24);
  return {numeric,words:[...new Set(words(text))].slice(0,80),terms};
}
const hangulPrefix = term => /[가-힣]{2}/.test(term);
function ftsQuery(text) { return features(text).terms.map(x=>'"'+x.replaceAll('"','""')+'"'+(hangulPrefix(x)?'*':'')).join(' OR '); }
function integer(value,fallback,max) {
  if(value==null||value==='') return fallback;
  if(!/^\d{1,6}$/.test(String(value))) fail(400,'invalid_pagination');
  const n=Number(value); if(n>max||n<0) fail(400,'invalid_pagination'); return n;
}
function options(params) {
  const lang=params.get('lang')??'ko'; if(!['ko','en'].includes(lang)) fail(400,'invalid_language');
  const source=params.get('source')||null; if(source) validId(source,SID,'invalid_source');
  const subject=params.get('subject')||null; if(subject&&!SUBJECTS.has(subject)) fail(400,'invalid_subject');
  const limit=integer(params.get('limit'),20,30); if(!limit) fail(400,'invalid_pagination');
  const collection=params.get('collection')||null;if(collection&&!['physics','astronomy'].includes(collection))fail(400,'invalid_collection');
  const stars=params.get('stars')?integer(params.get('stars'),null,5):null;if(stars===0)fail(400,'invalid_stars');
  const cursor=params.get('cursor')||null;if(cursor)validId(cursor,QID,'invalid_cursor');
  return {lang,source,subject,collection,stars,cursor,limit,offset:integer(params.get('offset'),0,300)};
}
function safeString(value,max=2000) {
  if(typeof value!=='string'||value.length>max||/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(value)) return null;
  // Metadata is a strict allowlist; notes with private paths, origins or secrets are omitted.
  if(/(?:[a-z]:[\\/]|\\\\|file:\/\/|\/(?:Users|home|tmp|mnt|root|workspace|var|opt|etc|data|srv)\/|https?:\/\/|(?:api[_ -]?key|bearer\s|sk-proj-|token\s*[:=]))/i.test(value)) return null;
  return value;
}
function safeContext(raw) {
  const input=parse(raw),out={};
  for(const key of ['unresolved_source','source_image_checked','reference_context_digitized']) if(typeof input[key]==='boolean') out[key]=input[key];
  for(const key of ['source_author','institution','course','term','instructor','source_coverage','source_role','generated_by','authorship','source_contributor']) {
    const v=safeString(input[key]); if(v!==null) out[key]=v;
  }
  for(const key of ['topics','review_notes','scientific_review_notes','answered_subparts','missing_subparts','coverage_notes','adaptation_changes']) {
    if(Array.isArray(input[key])) out[key]=input[key].slice(0,30).map(v=>safeString(v)).filter(v=>v!==null);
    else { const v=safeString(input[key]); if(v!==null) out[key]=v; }
  }
  return out;
}
function sourceInfo(route) {
  const s=parse(route.source_json); const id=route.source_id;
  return {id,title:safeString(route.display_title)??safeString(s.title)??'Source',published_title_en:safeString(route.published_title_en),published_title_ko:safeString(route.published_title_ko),primary_author:safeString(route.primary_author),edition_label:safeString(route.edition_label),collection:route.library_collection||'physics',page_count:s.page_count,subjects:array(s.subjects??s.subjects_json).filter(x=>SUBJECTS.has(x)),level:s.level,
    source_language:s.source_language,expected_question_count:s.expected_question_count??null,extraction_complete:s.extraction_complete===true,
    license_identifier:safeString(s.origin?.license_identifier,240),...PRIVATE};
}
async function sourceRoute(env,sourceId) {
  const join=await presentationJoin(env);
  const route=await first(binding(env,'BANK_REGISTRY'),`SELECT r.source_id,r.source_json,r.database_name${presentationFields(join)} FROM bank_source_routes r ${join} WHERE r.source_id=?`,[sourceId]);
  if(!route) fail(404,'source_not_found');
  return {route,db:routeDb(env,route.database_name)};
}
async function locateQuestion(env,id) {
  validId(id,QID);
  const matches=await rows(binding(env,'BANK_SEARCH'),'SELECT DISTINCT source_id FROM bank_search_documents WHERE question_id=? LIMIT 2',[id]);
  if(!matches.length) fail(404,'question_not_found');
  if(matches.length!==1||!SID.test(matches[0].source_id)) fail(503,'problem_bank_integrity_error');
  const {route,db}=await sourceRoute(env,matches[0].source_id);
  const q=await first(db,`SELECT q.*,c.source_language,c.context_json FROM bank_questions q LEFT JOIN bank_question_context c ON c.question_id=q.id WHERE q.id=? AND q.source_id=?`,[id,route.source_id]);
  if(!q) fail(404,'question_not_found');
  if(q.id!=='q_'+await digest(q.source_id+'\0'+q.locator)) fail(503,'problem_bank_integrity_error');
  return {q,route,db};
}
async function versions(db,table,key,id) {
  const tableName=table==='solution'?'bank_solution_versions':'bank_question_versions';
  const keyName=key==='solution'?'solution_id':'question_id';
  const data=await rows(db,`SELECT id,language,role,text,text_sha256,review_status FROM ${tableName} WHERE ${keyName}=? AND active=1 ORDER BY language,id LIMIT 8`,[id]);
  const seen=new Set();
  for(const v of data) {
    if(seen.has(v.language)||typeof v.text!=='string'||v.text.length>200000||!v.text.length||!HASH.test(v.text_sha256)||await digest(v.text)!==v.text_sha256) fail(503,'problem_bank_integrity_error');
    seen.add(v.language);
  }
  return data.map(v=>({...v,...PRIVATE}));
}
function assetInfo(a) { return {id:a.id,role:a.role,mime_type:a.mime_type,sha256:a.sha256,spans:array(a.spans_json),url:PREFIX+'/assets/'+a.id}; }
function questionInfo(q) { return {id:q.id,source_id:q.source_id,locator:q.locator,original_number:q.original_number,chapter:q.chapter,kind:q.kind,subjects:array(q.subjects_json),level:q.level,source_language:q.source_language,review_status:q.review_status,context:safeContext(q.context_json),...PRIVATE}; }

function contextOptions(params) {
  const depth=integer(params.get('depth'),CONTEXT_DEPTH,CONTEXT_DEPTH);
  const limit=integer(params.get('limit'),CONTEXT_NODES,CONTEXT_NODES);
  if(!depth||!limit)fail(400,'invalid_pagination');
  return {depth,limit};
}
async function contextGraph(env,parent,limit=CONTEXT_NODES) {
  const db=binding(env,'BANK_REGISTRY');
  // Imports own this additive table. Older registries remain readable without
  // creating schema or changing canonical question/context metadata at runtime.
  const exists=!!await first(db,"SELECT name FROM sqlite_master WHERE type='table' AND name='bank_context_graph_edges'");
  const admitted=new Map([[parent.q.id,parent]]),edgeCache=new Map();
  let lookups=0,truncated=false,unavailable=0;
  return {
    get truncated(){return truncated;},
    get unavailable(){return unavailable;},
    truncate(){truncated=true;},
    async edges(id){
      if(!exists)return [];
      if(edgeCache.has(id))return edgeCache.get(id);
      const data=await rows(db,`SELECT target_question_id,relation,substr(metadata_json,1,4096) AS metadata_json FROM bank_context_graph_edges WHERE question_id=? ORDER BY target_question_id,relation LIMIT ?`,[id,CONTEXT_NODES+1]);
      if(data.length>CONTEXT_NODES)truncated=true;
      const edges=[];
      for(const row of data.slice(0,CONTEXT_NODES)){
        if(!QID.test(row.target_question_id??'')||!CONTEXT_RELATION.test(row.relation??'')){unavailable++;continue;}
        const metadata=parse(row.metadata_json),label=safeString(metadata?.label,240);
        edges.push({question_id:row.target_question_id,relation:row.relation,...(label===null?{}:{label})});
      }
      edgeCache.set(id,edges);return edges;
    },
    async admit(id){
      if(admitted.has(id))return admitted.get(id);
      // Invalid/stale references also consume this bounded lookup budget.
      if(lookups>=limit){truncated=true;return null;}
      lookups++;
      try{const found=await locateQuestion(env,id);admitted.set(id,found);return found;}
      catch(error){
        if(error instanceof BankError&&error.status===404){admitted.set(id,null);unavailable++;return null;}
        throw error;
      }
    }
  };
}
async function directContextLinks(graph,id) {
  const links=[];
  for(const edge of await graph.edges(id))if(await graph.admit(edge.question_id))links.push(edge);
  return links;
}
function contextCycles(adjacency) {
  const color=new Map(),cycles=[],seen=new Set();
  function visit(id){
    color.set(id,1);
    for(const edge of adjacency.get(id)??[]){
      const target=edge.question_id;
      if(color.get(target)===1){
        const key=id+'\0'+target;
        if(!seen.has(key)){seen.add(key);cycles.push({from_question_id:id,to_question_id:target});}
      }else if(!color.has(target))visit(target);
    }
    color.set(id,2);
  }
  for(const id of adjacency.keys())if(!color.has(id))visit(id);
  return cycles;
}
async function questionContext(env,id,lang,{depth,limit},user) {
  const parent=await locateQuestion(env,id);
  await versions(parent.db,'question','question',id);
  const graph=await contextGraph(env,parent,limit),visited=new Set([id]);
  const queue=[{id,depth:0}],contexts=[],byId=new Map(),adjacency=new Map();
  for(let cursor=0;cursor<queue.length;cursor++){
    const current=queue[cursor],links=[];
    for(const edge of await graph.edges(current.id)){
      const target=edge.question_id;
      if(visited.has(target)){links.push(edge);continue;}
      if(current.depth>=depth||contexts.length>=limit){graph.truncate();continue;}
      const found=await graph.admit(target);if(!found)continue;
      const vs=await versions(found.db,'question','question',target);
      const assets=await rows(found.db,'SELECT id,role,mime_type,sha256,spans_json FROM bank_assets WHERE question_id=? ORDER BY asset_id LIMIT 150',[target]);
      const item={id:target,original_number:safeString(found.q.original_number,240),source:{title:sourceInfo(found.route).title},
        selected_version:vs.find(v=>v.language===lang)??null,context_links:[],assets:await scopedAssets(env,assets,user,target),figures:await figureVariants(env,target),depth:current.depth+1,...PRIVATE};
      contexts.push(item);byId.set(target,item);visited.add(target);queue.push({id:target,depth:current.depth+1});links.push(edge);
    }
    adjacency.set(current.id,links);
    if(byId.has(current.id))byId.get(current.id).context_links=links;
  }
  return {question_id:id,contexts,context_links:adjacency.get(id)??[],cycles:contextCycles(adjacency),truncated:graph.truncated,
    unavailable_links:graph.unavailable,depth_limit:depth,context_limit:limit,...PRIVATE};
}

async function search(env,text,opts,{exclude=null}={}) {
  const db=binding(env,'BANK_SEARCH'),query=ftsQuery(text),args=[],where=['d.language=?']; args.push(opts.lang);
  if(query&&opts.cursor)fail(400,'invalid_cursor');
  if(opts.cursor&&opts.offset)fail(400,'invalid_pagination');
  const facets=await optionalTable(env,'BANK_SEARCH','bank_question_facets'),join=facets?' LEFT JOIN bank_question_facets f ON f.question_id=d.question_id ':'';
  if(opts.source){where.push('d.source_id=?');args.push(opts.source);}
  if(opts.subject){where.push(`EXISTS(SELECT 1 FROM json_each(${facets?'COALESCE(f.subjects_json,d.subjects_json)':'d.subjects_json'}) sj WHERE sj.value=?)`);args.push(opts.subject);}
  if(opts.collection||opts.stars){if(!facets)fail(503,'problem_bank_classification_unavailable');if(opts.collection){where.push('f.collection=?');args.push(opts.collection);}if(opts.stars){where.push('f.stars=?');args.push(opts.stars);}}
  if(opts.cursor){where.push('d.question_id>?');args.push(opts.cursor);}
  if(exclude){where.push('d.question_id!=?');args.push(exclude);}
  const cap=query?Math.min(430,opts.offset+opts.limit+100):opts.offset+opts.limit+1;
  let sql=`SELECT d.question_id,d.source_id,d.locator,d.original_number,d.chapter,${facets?'COALESCE(f.subjects_json,d.subjects_json)':'d.subjects_json'} AS subjects_json,d.level,d.language,d.source_title,d.review_status,d.unresolved_source,d.text_sha256,substr(d.text,1,12000) AS text${facets?',f.stars,f.difficulty_status,f.confidence,f.reason_codes_json,f.collection':''}`;
  if(query){sql+=`,bm25(bank_search_fts) AS fts_rank FROM bank_search_fts JOIN bank_search_documents d ON d.id=bank_search_fts.rowid ${join} WHERE bank_search_fts MATCH ? AND `;args.unshift(query);}
  else sql+=`,0 AS fts_rank FROM bank_search_documents d ${join} WHERE `;
  sql+=where.join(' AND ')+(query?' ORDER BY fts_rank,d.question_id':' ORDER BY d.question_id')+' LIMIT ?';args.push(cap);
  const candidates=await rows(db,sql,args),f=features(text);
  const scored=candidates.map(x=>{
    const w=new Set(words(x.text)),n=new Set(numbers(x.text));
    const nm=f.numeric.filter(t=>n.has(t)).length,wm=f.words.filter(t=>w.has(t)||(hangulPrefix(t)&&[...w].some(word=>word.startsWith(t)))).length;
    const score=query?Number((12*(f.numeric.length?nm/f.numeric.length:0)+nm+5*(f.words.length?wm/f.words.length:0)+Math.min(1,Math.max(0,-Number(x.fts_rank||0)))).toFixed(6)):0;
    return {id:x.question_id,source_id:x.source_id,source_title:x.source_title,locator:x.locator,original_number:x.original_number,chapter:x.chapter,subjects:array(x.subjects_json),level:x.level,language:x.language,snippet:x.text.slice(0,360),score,matched_numeric_factors:nm,review_status:x.review_status,unresolved_source:!!x.unresolved_source,text_sha256:x.text_sha256,...facetInfo(x),...PRIVATE};
  }).sort((a,b)=>b.score-a.score||a.id.localeCompare(b.id));
  // Search rows are derived data. Only current registry routes admit results.
  const sources=[...new Set(scored.map(x=>x.source_id))];
  const admitted=new Set();
  for(let start=0;start<sources.length;start+=80){
    const ids=sources.slice(start,start+80);
    const found=await rows(binding(env,'BANK_REGISTRY'),`SELECT source_id,database_name FROM bank_source_routes WHERE source_id IN (${ids.map(()=>'?').join(',')})`,ids);
    for(const row of found) if(DATABASES[row.database_name]) admitted.add(row.source_id);
  }
  const valid=scored.filter(x=>admitted.has(x.source_id));
  const items=valid.slice(opts.offset,opts.offset+opts.limit),has_more=valid.length>opts.offset+opts.limit;
  return {items,limit:opts.limit,offset:opts.offset,has_more,next_cursor:!query&&has_more&&items.length?items.at(-1).id:null,limited_results:!!query&&candidates.length===cap,method:query?'bounded_text_similarity':'canonical_cursor_browse',...PRIVATE};
}

async function boundedJson(req) {
  if(!/^application\/json(?:\s*;|\s*$)/i.test(req.headers.get('content-type')??'')) fail(415,'json_required');
  const declared=req.headers.get('content-length'); if(declared&&(!/^\d+$/.test(declared)||Number(declared)>MAX_BODY)) fail(413,'request_too_large');
  const reader=req.body?.getReader();if(!reader) fail(400,'invalid_json');
  const pieces=[];let length=0;
  try {
    for(;;){const {done,value}=await reader.read();if(done)break;length+=value.byteLength;if(length>MAX_BODY){await reader.cancel();fail(413,'request_too_large');}pieces.push(value);}
    const bytes=new Uint8Array(length);let offset=0;for(const p of pieces){bytes.set(p,offset);offset+=p.byteLength;}
    const body=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
    if(!body||typeof body!=='object'||Array.isArray(body)) fail(400,'invalid_json');return body;
  } catch(e){if(e instanceof BankError)throw e;fail(400,'invalid_json');}finally{reader.releaseLock();}
}

async function identifyInput(req,ocr) {
  const type=req.headers.get('content-type')??'';
  if(/^application\/json(?:\s*;|\s*$)/i.test(type)) {
    const body=await boundedJson(req);
    if(Object.keys(body).some(k=>!['text','lang','subject','source','collection','stars','limit'].includes(k)))fail(400,'text_identification_only');
    if(typeof body.text!=='string'||body.text.trim().length<5||body.text.length>12000||body.text.includes('\0'))fail(400,'invalid_identification_text');
    return {body,text:body.text,ocr_used:false};
  }
  if(!/^multipart\/form-data\s*;/i.test(type))fail(415,'json_or_scan_required');
  if(typeof ocr!=='function')fail(503,'ocr_unavailable');
  const declared=req.headers.get('content-length');
  if(declared&&(!/^\d+$/.test(declared)||Number(declared)>MAX_SCAN+65536))fail(413,'request_too_large');
  const reader=req.body?.getReader();if(!reader)fail(400,'invalid_scan');
  const parts=[];let total=0;
  try {
    for(;;){const {done,value}=await reader.read();if(done)break;total+=value.byteLength;if(total>MAX_SCAN+65536){await reader.cancel();fail(413,'request_too_large');}parts.push(value);}
  }finally{reader.releaseLock();}
  const bytes=new Uint8Array(total);let offset=0;for(const part of parts){bytes.set(part,offset);offset+=part.length;}
  let form;try{form=await new Response(bytes,{headers:{'Content-Type':type}}).formData();}catch{fail(400,'invalid_scan');}
  const allowed=new Set(['image','lang','subject','source','collection','stars','limit']);
  for(const [key] of form)if(!allowed.has(key)||form.getAll(key).length!==1)fail(400,'invalid_scan');
  const image=form.get('image');
  if(!image||typeof image.arrayBuffer!=='function'||image.size<1||image.size>MAX_SCAN)fail(400,'invalid_scan');
  if(!['image/png','image/jpeg','image/webp'].includes(image.type))fail(415,'unsupported_scan_type');
  const imageBytes=new Uint8Array(await image.arrayBuffer());if(!rasterSignature(imageBytes,image.type))fail(400,'invalid_scan');
  const body={};for(const key of ['lang','subject','source','collection','stars','limit'])if(form.has(key)){if(typeof form.get(key)!=='string')fail(400,'invalid_scan');body[key]=form.get(key);}
  // Validate filters before spending the caller-authorized OCR request.
  const params=new URLSearchParams(body);options(params);
  let result;
  try {result=await ocr(image,req);}catch(e){if(e?.status===429)fail(429,'ocr_rate_limited');if(e?.status===413)fail(413,'scan_too_large');fail(502,'ocr_failed');}
  const text=typeof result==='string'?result:result?.text;
  if(typeof text!=='string'||text.trim().length<5||text.length>12000||text.includes('\0'))fail(422,'ocr_text_unusable');
  return {body,text,ocr_used:true,ocr_confidence:typeof result?.confidence==='number'&&Number.isFinite(result.confidence)?result.confidence:null};
}

async function solutions(env,id,lang,user) {
  const parent=await locateQuestion(env,id);
  const routes=await rows(binding(env,'BANK_REGISTRY'),'SELECT solution_id,question_id,database_name FROM bank_solution_routes WHERE question_id=? ORDER BY solution_id LIMIT 101',[id]);
  if(routes.length>100) fail(503,'problem_bank_integrity_error');
  const items=[];
  for(const route of routes){
    const db=routeDb(env,route.database_name);
    const s=await first(db,'SELECT * FROM bank_solutions WHERE id=? AND question_id=?',[route.solution_id,id]);
    if(!s) fail(503,'problem_bank_integrity_error');
    const vs=await versions(db,'solution','solution',s.id),assets=await rows(db,'SELECT id,role,mime_type,sha256,spans_json FROM bank_solution_assets WHERE solution_id=? ORDER BY id LIMIT 150',[s.id]);
    items.push({id:s.id,question_id:id,kind:s.kind,authorship:s.authorship,source_id:s.source_id,solution_locator:s.solution_locator,review_status:s.review_status,context:safeContext(s.context_json),versions:vs,selected_version:vs.find(v=>v.language===lang)??null,assets:assets.filter(a=>user?.role==='admin'||a.role==='figure').map(assetInfo),...PRIVATE});
  }
  return {question_id:id,question_source:sourceInfo(parent.route),solutions:items,...PRIVATE};
}
function payloadBytes(value) {
  if(value instanceof ArrayBuffer)return new Uint8Array(value);
  if(ArrayBuffer.isView(value))return new Uint8Array(value.buffer,value.byteOffset,value.byteLength);
  if(Array.isArray(value)&&value.every(n=>Number.isInteger(n)&&n>=0&&n<=255))return new Uint8Array(value);
  fail(503,'asset_integrity_error');
}
function rasterSignature(bytes,mime) {
  if(mime==='image/png')return bytes.length>=8&&[137,80,78,71,13,10,26,10].every((v,i)=>bytes[i]===v);
  if(mime==='image/jpeg')return bytes.length>=3&&bytes[0]===255&&bytes[1]===216&&bytes[2]===255;
  if(mime==='image/webp')return bytes.length>=12&&String.fromCharCode(...bytes.slice(0,4))==='RIFF'&&String.fromCharCode(...bytes.slice(8,12))==='WEBP';
  return false;
}
async function asset(env,id,user) {
  validId(id,AID);
  let metadata,db,table;
  if(id.startsWith('sa_')) {
    // Discover at most the three configured databases, and only query solution
    // tables after sqlite_master confirms that schema exists on that shard.
    for(const name of Object.keys(DATABASES)){
      const candidate=routeDb(env,name);
      if(!await first(candidate,"SELECT name FROM sqlite_master WHERE type='table' AND name='bank_solution_assets'"))continue;
      const a=await first(candidate,'SELECT a.*,s.question_id FROM bank_solution_assets a JOIN bank_solutions s ON s.id=a.solution_id WHERE a.id=?',[id]);
      if(!a)continue;
      const route=await first(binding(env,'BANK_REGISTRY'),'SELECT solution_id,question_id,database_name FROM bank_solution_routes WHERE solution_id=?',[a.solution_id]);
      if(route?.database_name===name&&route.question_id===a.question_id){await locateQuestion(env,a.question_id);if(user?.role!=='admin'&&a.role!=='figure')fail(403,'source_asset_admin_required');metadata=a;db=candidate;table='bank_solution_asset_chunks';break;}
    }
  } else {
    const candidates=await Promise.all(Object.keys(DATABASES).map(async name=>({name,db:routeDb(env,name),a:await first(routeDb(env,name),'SELECT a.*,q.source_id FROM bank_assets a JOIN bank_questions q ON q.id=a.question_id WHERE a.id=?',[id])})));
    for(const entry of candidates){
      if(!entry.a)continue;
      const {route}=await sourceRoute(env,entry.a.source_id);
      if(route.database_name!==entry.name)continue;
      await locateQuestion(env,entry.a.question_id);
      if(user?.role!=='admin'){
        const policy=await optionalTable(env,'BANK_REGISTRY','bank_asset_display_policy')?await first(binding(env,'BANK_REGISTRY'),'SELECT question_id,sha256,placement FROM bank_asset_display_policy WHERE asset_id=?',[id]):null;
        if(entry.a.role!=='figure'||!policy||policy.question_id!==entry.a.question_id||policy.sha256!==entry.a.sha256||policy.placement==='blocked')fail(403,'source_asset_admin_required');
      }
      const p=await first(entry.db,'SELECT byte_length,sha256,chunk_count FROM bank_asset_payloads WHERE asset_id=?',[id]);
      if(!p)fail(404,'asset_not_found');
      if(p.sha256!==entry.a.sha256)fail(503,'asset_integrity_error');
      metadata={...entry.a,...p};db=entry.db;table='bank_asset_chunks';break;
    }
  }
  if(!metadata)fail(404,'asset_not_found');
  if(!['image/png','image/jpeg','image/webp'].includes(metadata.mime_type))fail(415,'unsupported_asset_type');
  if(!Number.isSafeInteger(metadata.byte_length)||metadata.byte_length<1||metadata.byte_length>MAX_ASSET||!Number.isSafeInteger(metadata.chunk_count)||metadata.chunk_count<1||metadata.chunk_count>128||!HASH.test(metadata.sha256))fail(503,'asset_integrity_error');
  const totals=await first(db,`SELECT count(*) AS count,COALESCE(sum(byte_length),0) AS bytes FROM ${table} WHERE asset_id=?`,[id]);
  if(totals.count!==metadata.chunk_count||totals.bytes!==metadata.byte_length)fail(503,'asset_integrity_error');
  const chunks=await rows(db,`SELECT chunk_index,byte_length,sha256,CASE WHEN byte_length BETWEEN 1 AND 262144 AND length(payload)=byte_length THEN payload ELSE NULL END AS payload FROM ${table} WHERE asset_id=? ORDER BY chunk_index LIMIT 129`,[id]);
  if(chunks.length!==metadata.chunk_count)fail(503,'asset_integrity_error');
  const bytes=new Uint8Array(metadata.byte_length);let offset=0;
  for(let i=0;i<chunks.length;i++){
    const c=chunks[i],part=payloadBytes(c.payload);
    if(c.chunk_index!==i||c.byte_length!==part.byteLength||part.byteLength<1||part.byteLength>262144||offset+part.byteLength>bytes.length||await digest(part)!==c.sha256)fail(503,'asset_integrity_error');
    bytes.set(part,offset);offset+=part.length;
  }
  if(offset!==bytes.length||await digest(bytes)!==metadata.sha256||!rasterSignature(bytes,metadata.mime_type))fail(503,'asset_integrity_error');
  return new Response(bytes,{headers:{'Content-Type':metadata.mime_type,'Content-Length':String(bytes.length),'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'none'; sandbox",'ETag':'"'+metadata.sha256+'"'}});
}

async function feedback(env,id,user){
  await locateQuestion(env,id);
  if(!await optionalTable(env,'BANK_REGISTRY','bank_question_feedback'))return {question_id:id,count:0,mean_stars:null,own:null,evidence:'self_report'};
  const db=binding(env,'BANK_REGISTRY'),summary=await first(db,'SELECT count(*) AS count,avg(stars) AS mean_stars FROM bank_question_feedback WHERE question_id=?',[id]);
  const own=user?await first(db,'SELECT stars,outcome,minutes FROM bank_question_feedback WHERE question_id=? AND user_id=?',[id,user.id]):null;
  return {question_id:id,...summary,own,evidence:'self_report'};
}
async function writeFeedback(req,env,id,user){
  if(!user)fail(401,'login_required');
  const body=await requestJson(req,2048);
  if(!body||Object.keys(body).some(k=>!['stars','outcome','minutes'].includes(k))||!Number.isInteger(body.stars)||body.stars<1||body.stars>5||!['not_attempted','solved','partial','unsolved'].includes(body.outcome)||body.minutes!=null&&(!Number.isInteger(body.minutes)||body.minutes<1||body.minutes>1440))fail(400,'invalid_feedback');
  await locateQuestion(env,id);
  if(!await optionalTable(env,'BANK_REGISTRY','bank_question_feedback')||!await optionalTable(env,'BANK_REGISTRY','bank_feedback_limits'))fail(503,'feedback_unavailable');
  const db=binding(env,'BANK_REGISTRY'),day=new Date().toISOString().slice(0,10),now=new Date().toISOString();
  const admitted=await first(db,'INSERT INTO bank_feedback_limits(user_id,day,n) VALUES(?,?,1) ON CONFLICT(user_id,day) DO UPDATE SET n=n+1 WHERE n<100 RETURNING n',[user.id,day]);
  if(!admitted)fail(429,'feedback_rate_limited');
  await db.prepare("INSERT INTO bank_question_feedback(question_id,user_id,stars,outcome,minutes,evidence,updated_at) VALUES(?,?,?,?,?,'self_report',?) ON CONFLICT(question_id,user_id) DO UPDATE SET stars=excluded.stars,outcome=excluded.outcome,minutes=excluded.minutes,updated_at=excluded.updated_at").bind(id,user.id,body.stars,body.outcome,body.minutes??null,now).run();
  return feedback(env,id,user);
}
async function requestJson(req,max){
  if(!/^application\/json(?:;|$)/i.test(req.headers.get('Content-Type')||''))fail(415,'json_required');
  const reader=req.body?.getReader();if(!reader)fail(400,'invalid_json');let size=0;const chunks=[];
  try{for(;;){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>max){await reader.cancel();fail(413,'request_too_large');}chunks.push(value);}}finally{reader.releaseLock();}
  const bytes=new Uint8Array(size);let offset=0;for(const c of chunks){bytes.set(c,offset);offset+=c.length;}try{const body=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));if(!body||typeof body!=='object'||Array.isArray(body))fail(400,'invalid_json');return body;}catch(e){if(e instanceof BankError)throw e;fail(400,'invalid_json');}
}
async function reviewDifficulty(req,env,id,user){
  if(!user)fail(401,'login_required');if(user.role!=='admin')fail(403,'admin_required');
  const body=await requestJson(req,4096);
  if(Object.keys(body).some(k=>!['rubric','basis_text_sha256','all_required_context_read'].includes(k))||body.all_required_context_read!==true||!HASH.test(body.basis_text_sha256||''))fail(400,'invalid_difficulty_review');
  let rated;try{rated=starsFromRubric(body.rubric);}catch{fail(400,'invalid_difficulty_review');}
  const found=await locateQuestion(env,id),vs=await versions(found.db,'question','question',id),basis=vs.find(v=>v.language==='en');
  if(!basis||basis.text_sha256!==body.basis_text_sha256)fail(409,'difficulty_basis_changed');
  if(!await facet(env,id)||!await optionalTable(env,'BANK_REGISTRY','bank_difficulty_reviews'))fail(503,'difficulty_review_unavailable');
  const now=new Date().toISOString(),rubric=JSON.stringify(body.rubric);
  await binding(env,'BANK_REGISTRY').prepare('INSERT INTO bank_difficulty_reviews(question_id,user_id,stars,rubric_json,basis_text_sha256,method_version,updated_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(question_id) DO UPDATE SET user_id=excluded.user_id,stars=excluded.stars,rubric_json=excluded.rubric_json,basis_text_sha256=excluded.basis_text_sha256,method_version=excluded.method_version,updated_at=excluded.updated_at').bind(id,user.id,rated.stars,rubric,basis.text_sha256,BANK_METHOD,now).run();
  await binding(env,'BANK_SEARCH').prepare("UPDATE bank_question_facets SET stars=?,difficulty_status='reviewed',confidence='high',rubric_json=?,basis_text_sha256=?,method_version=?,updated_at=? WHERE question_id=?").bind(rated.stars,rubric,basis.text_sha256,BANK_METHOD,now,id).run();
  return {question_id:id,...facetInfo(await facet(env,id))};
}

export async function problemBankRoute(req,env,url,{user,ocr}={}) {
  if(!(url.pathname===PREFIX||url.pathname.startsWith(PREFIX+'/')))return null;
  try {
    env={...env,[REQUEST_CACHE]:new Map()};
    const suffix=url.pathname.slice(PREFIX.length),opts=options(url.searchParams);
    if(req.method==='POST'&&suffix==='/identify'){
      if(!/^application\/json(?:;|$)/i.test(req.headers.get('Content-Type')||'')){if(!user)fail(401,'login_required');if(user.role!=='admin')fail(403,'admin_required');}
      const input=await identifyInput(req,ocr),{body}=input;
      const params=new URLSearchParams();for(const k of ['lang','subject','source','collection','stars','limit'])if(body[k]!=null)params.set(k,String(body[k]));
      const preferred=options(params),other=preferred.lang==='ko'?'en':'ko';
      const results=await Promise.all([search(env,input.text,preferred),search(env,input.text,{...preferred,lang:other})]);
      const combined=new Map();
      for(const result of results)for(const item of result.items){
        const old=combined.get(item.id);
        if(!old||item.score>old.score||(item.score===old.score&&item.language===preferred.lang))combined.set(item.id,item);
      }
      const all=[...combined.values()].sort((a,b)=>b.score-a.score||a.id.localeCompare(b.id)),items=all.slice(0,preferred.limit);
      return json({...results[0],items,candidates:items,recognized_text:input.text,requested_language:preferred.lang,searched_languages:[preferred.lang,other],has_more:all.length>preferred.limit||results.some(r=>r.has_more),ocr_used:input.ocr_used,ocr_confidence:input.ocr_confidence??null,identification_status:'candidates_only',automatic_match_confirmed:false});
    }
    const write=suffix.match(/^\/questions\/([^/]+)\/(feedback|difficulty-review)$/);
    if(req.method==='POST'&&write){validId(write[1],QID);return json(await (write[2]==='feedback'?writeFeedback(req,env,write[1],user):reviewDifficulty(req,env,write[1],user)));}
    if(req.method!=='GET')fail(405,'method_not_allowed');
    if(suffix==='/status'){
      const counts=await first(binding(env,'BANK_SEARCH'),`SELECT count(DISTINCT question_id) AS questions,count(*) AS language_bodies,count(DISTINCT source_id) AS sources_with_documents,count(DISTINCT CASE WHEN unresolved_source=1 THEN question_id END) AS unresolved_questions FROM bank_search_documents`);
      const registered=await first(binding(env,'BANK_REGISTRY'),'SELECT count(*) AS sources_registered FROM bank_source_routes');
      const enabled=user?.role==='admin'&&typeof ocr==='function';
      return json({...counts,...registered,user:user?{id:user.id,role:user.role,nickname:user.nickname??''}:null,access:'public',review_status:'pending',ocr_available:enabled,identification:enabled?'text_or_scan':'supplied_text_only',...PRIVATE});
    }
    if(suffix==='/sources'){
      const join=await presentationJoin(env),data=await rows(binding(env,'BANK_REGISTRY'),`SELECT r.source_id,r.source_json,r.database_name${presentationFields(join)} FROM bank_source_routes r ${join} ORDER BY r.source_id LIMIT 500`);
      return json({sources:data.filter(r=>DATABASES[r.database_name]).map(sourceInfo),...PRIVATE});
    }
    if(suffix==='/search'){
      const q=url.searchParams.get('q')??'';if(q.length>600||q.includes('\0'))fail(400,'invalid_search_query');
      return json(await search(env,q,opts));
    }
    if(suffix==='/recommendations'){
      const target=opts.stars??3,pool=await search(env,'',{...opts,stars:null,limit:30,offset:0,cursor:null});
      return json({items:recommendProblems(pool.items,{targetStars:target,limit:opts.limit,preferredSubjects:opts.subject?[opts.subject]:[]}),target_stars:target,method:'target_difficulty_and_source_diversity',...PRIVATE});
    }
    const a=suffix.match(/^\/assets\/([^/]+)$/);if(a)return await asset(env,a[1],user);
    const q=suffix.match(/^\/questions\/([^/]+)(?:\/(solutions|recommendations|context|feedback))?$/);
    if(q){
      validId(q[1],QID);
      if(q[2]==='solutions')return json(await solutions(env,q[1],opts.lang,user));
      if(q[2]==='context')return json(await questionContext(env,q[1],opts.lang,contextOptions(url.searchParams),user));
      if(q[2]==='feedback')return json(await feedback(env,q[1],user));
      const found=await locateQuestion(env,q[1]),vs=await versions(found.db,'question','question',q[1]);
      if(q[2]==='recommendations'){
        const current=await facet(env,q[1]),subjects=current?array(current.subjects_json):array(found.q.subjects_json),subject=opts.subject??subjects.find(x=>SUBJECTS.has(x))??null;
        const [related,nearby]=await Promise.all([search(env,(vs.find(v=>v.language===opts.lang)?.text??'').slice(0,600),{...opts,stars:null,cursor:null,offset:0,limit:30,subject},{exclude:q[1]}),search(env,'',{...opts,stars:null,cursor:null,offset:0,limit:30,subject,collection:opts.collection??current?.collection??null},{exclude:q[1]})]);
        const pool=[...new Map([...related.items,...nearby.items].filter(i=>!i.unresolved_source).map(i=>[i.id,i])).values()];
        const seen=user&&await optionalTable(env,'BANK_REGISTRY','bank_question_feedback')?(await rows(binding(env,'BANK_REGISTRY'),"SELECT question_id FROM bank_question_feedback WHERE user_id=? AND outcome='solved' ORDER BY updated_at DESC LIMIT 200",[user.id])).map(r=>r.question_id):[];
        return json({question_id:q[1],items:recommendProblems(pool,{targetStars:opts.stars??current?.stars??3,limit:opts.limit,seen:[q[1],...seen],preferredSubjects:subjects,previousSource:found.q.source_id}),method:'subject_difficulty_novelty_diversity',...PRIVATE});
      }
      const assets=await rows(found.db,'SELECT id,role,mime_type,sha256,spans_json FROM bank_assets WHERE question_id=? ORDER BY asset_id LIMIT 150',[q[1]]);
      const context_links=await directContextLinks(await contextGraph(env,found),q[1]);
      return json({question:{...questionInfo(found.q),...facetInfo(await facet(env,q[1]),sourceInfo(found.route).collection),source:sourceInfo(found.route),versions:vs,selected_version:vs.find(v=>v.language===opts.lang)??null,assets:await scopedAssets(env,assets,user,q[1]),figures:await figureVariants(env,q[1]),can_view_source:user?.role==='admin',context_links},...PRIVATE});
    }
    fail(404,'problem_bank_route_not_found');
  } catch(error) {
    if(error instanceof BankError)return json({error:error.code,...PRIVATE},error.status);
    // Never expose SQL, private filesystem paths, provider messages or credentials.
    return json({error:'problem_bank_unavailable',...PRIVATE},503);
  }
}
