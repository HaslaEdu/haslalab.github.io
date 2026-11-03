// Typed archive metadata is separate from scientific difficulty and source identity.
export const BANK_DISCIPLINES=['physics','astronomy','mathematics','chemistry','biology','earth_science','informatics'];
export const BANK_SOURCE_KINDS=['contest','book','course'];
export const BANK_PAPER_TYPES=['theory','experiment'];
export const BANK_CATALOGUE_SCHEMA=`
CREATE TABLE IF NOT EXISTS bank_question_catalogue(
 question_id TEXT PRIMARY KEY,source_id TEXT NOT NULL,source_kind TEXT NOT NULL CHECK(source_kind IN ('contest','book','course')),
 competition TEXT,year INTEGER,round TEXT,problem_type TEXT CHECK(problem_type IN ('theory','experiment')),
 problem_code TEXT,title_en TEXT,title_ko TEXT,discipline TEXT NOT NULL,sort_key TEXT NOT NULL,
 basis_text_sha256 TEXT NOT NULL,metadata_sha256 TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS bank_catalogue_browse ON bank_question_catalogue(source_kind,competition,year,problem_type,question_id);
`;
const fail=label=>{throw Error('Invalid bank catalogue '+label);};
const label=(v,key,max=500)=>typeof v==='string'&&v.trim()&&v.length<=max&&!/[\u0000-\u001f]/.test(v)&&!/(?:[a-z]:[\\/]|file:\/\/|https?:\/\/|bearer\s|api[_ -]?key)/i.test(v)?v:fail(key);
export function normalizeBankCatalogue(input,{source=false}={}){
 if(!input||typeof input!=='object'||Array.isArray(input))fail('object');
 const allowed=new Set(['kind','competition','year','round','problem_type','problem_code','title_en','title_ko','discipline']);
 if(Object.keys(input).some(k=>!allowed.has(k)))fail('field');
 const out={};
 if(input.kind!=null){if(!BANK_SOURCE_KINDS.includes(input.kind))fail('kind');out.kind=input.kind;}
 if(source&&!out.kind)fail('source kind');
 if(input.competition!=null){if(typeof input.competition!=='string'||!/^[a-z][a-z0-9_-]{1,49}$/.test(input.competition))fail('competition');out.competition=input.competition;}
 if(input.year!=null){if(!Number.isSafeInteger(input.year)||input.year<1800||input.year>2199)fail('year');out.year=input.year;}
 if(input.round!=null)out.round=label(input.round,'round',120);
 if(input.problem_type!=null){if(!BANK_PAPER_TYPES.includes(input.problem_type))fail('problem_type');out.problem_type=input.problem_type;}
 if(input.problem_code!=null)out.problem_code=label(input.problem_code,'problem_code',120);
 for(const k of ['title_en','title_ko'])if(input[k]!=null)out[k]=label(input[k],k,1000);
 if(input.discipline!=null){if(!BANK_DISCIPLINES.includes(input.discipline))fail('discipline');out.discipline=input.discipline;}
 if(out.kind==='contest'&&!out.competition)fail('contest competition');
 return out;
}
export function safeBankCatalogue(input,options){try{return normalizeBankCatalogue(input,options);}catch{return {};}}
export function sourceKind(source){return safeBankCatalogue(source?.catalogue).kind??(source?.origin?.kind==='url'?'course':'book');}
export function catalogueFields(input,{kind=null}={}){
 const c=safeBankCatalogue(input);
 return {source_kind:c.kind??kind,competition:c.competition??null,year:c.year??null,round:c.round??null,problem_type:c.problem_type??null,problem_code:c.problem_code??null,title_en:c.title_en??null,title_ko:c.title_ko??null,discipline:c.discipline??null};
}

export function naturalProblemKey(value){return String(value??'').normalize('NFKC').toLowerCase().replace(/\d+/g,n=>n.replace(/^0+(?=\d)/,'').padStart(12,'0')).slice(0,500);}
export function catalogueSortKey({source_id,catalogue,original_number}){
 const c=safeBankCatalogue(catalogue);
 return (c.kind==='contest'?[c.competition??'',String(c.year??''),c.round??'',c.problem_type==='experiment'?'1':'0',naturalProblemKey(c.problem_code??original_number)]:[source_id,naturalProblemKey(original_number)]).join('/');
}
export function encodeSourceCursor(key,id){return 'sc_'+btoa(String.fromCharCode(...new TextEncoder().encode(JSON.stringify({key,id})))).replaceAll('+','-').replaceAll('/','_').replace(/=+$/,'');}
export function decodeSourceCursor(value){
 if(typeof value!=='string'||value.length>2800||!/^sc_[A-Za-z0-9_-]+$/.test(value))throw Error('invalid_source_cursor');
 const encoded=value.slice(3).replaceAll('-','+').replaceAll('_','/');let x;
 try{x=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(Uint8Array.from(atob(encoded),c=>c.charCodeAt(0))));}catch{throw Error('invalid_source_cursor');}
 if(!x||typeof x!=='object'||Object.keys(x).sort().join(',')!=='id,key'||typeof x.key!=='string'||x.key.length>1500||/[\u0000-\u001f]/.test(x.key)||!/^q_[a-f0-9]{64}$/.test(x.id))throw Error('invalid_source_cursor');return x;
}
