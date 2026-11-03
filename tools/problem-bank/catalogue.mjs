// Private derived catalogue exports. No network or paid providers.
import {createHash} from 'node:crypto';import {readFile,writeFile,mkdir} from 'node:fs/promises';import path from 'node:path';import {pathToFileURL} from 'node:url';
import {questionId,sourceId,sqlLiteral,privateOutput} from './store.mjs';
import {BANK_CATALOGUE_SCHEMA,normalizeBankCatalogue,sourceKind,catalogueSortKey} from '../../community/src/problem-bank-catalogue.js';
const sha=x=>createHash('sha256').update(x).digest('hex');
export function catalogueRecords(normalized,{timestamp=new Date().toISOString()}={}){
 if(!normalized||!Array.isArray(normalized.sources)||!Array.isArray(normalized.questions)||!Number.isFinite(Date.parse(timestamp)))throw Error('Invalid catalogue input');
 const sources=new Map();for(const s of normalized.sources){const id=s.id??sourceId(s);if(id!==sourceId(s)||sources.has(id))throw Error('Conflicting catalogue source');sources.set(id,s);}
 const seen=new Set();return normalized.questions.map(q=>{
  const s=sources.get(q.source_id);if(!s||q.id!==questionId(q.source_id,q.locator)||seen.has(q.id))throw Error('Invalid catalogue question identity');seen.add(q.id);
  const parent=s.catalogue?normalizeBankCatalogue(s.catalogue,{source:true}):{kind:sourceKind(s)};
  const child=q.context?.catalogue?normalizeBankCatalogue(q.context.catalogue):{};
  const c={...parent,...child};if(!c.discipline)c.discipline=s.collection??(s.subjects?.includes('astronomy_astrophysics')?'astronomy':'physics');
  normalizeBankCatalogue(c,{source:true});const basis=q.versions?.find(v=>v.language==='en');if(!basis||!/^[a-f0-9]{64}$/.test(basis.text_sha256)||basis.text!=null&&sha(basis.text)!==basis.text_sha256)throw Error('Catalogue requires exact English body basis');
  const row={question_id:q.id,source_id:q.source_id,source_kind:c.kind,competition:c.competition??null,year:c.year??null,round:c.round??null,problem_type:c.problem_type??null,problem_code:c.problem_code??null,title_en:child.title_en??null,title_ko:child.title_ko??null,discipline:c.discipline,sort_key:catalogueSortKey({source_id:q.source_id,catalogue:c,original_number:c.kind==='contest'?q.original_number:q.locator}),basis_text_sha256:basis.text_sha256};
  return {...row,metadata_sha256:sha(JSON.stringify(row)),updated_at:timestamp};
 });
}
export function catalogueSql(records,{insertOnly=true}={}){
 const ids=new Set();return records.map(row=>{if(ids.has(row.question_id)||!/^[a-f0-9]{64}$/.test(row.metadata_sha256))throw Error('Invalid catalogue record');ids.add(row.question_id);const keys=Object.keys(row);return 'INSERT INTO bank_question_catalogue('+keys.join(',')+') VALUES('+keys.map(k=>sqlLiteral(row[k])).join(',')+')'+(insertOnly?'':' ON CONFLICT(question_id) DO UPDATE SET '+keys.filter(k=>k!=='question_id').map(k=>k+'=excluded.'+k).join(','))+';';}).join('\n')+'\n';
}
if(process.argv[1]&&pathToFileURL(path.resolve(process.argv[1])).href===import.meta.url){
 const [input,folder]=process.argv.slice(2);if(!folder)throw Error('Expected private normalized input and output folder');
 const data=JSON.parse(await readFile(input,'utf8')),records=catalogueRecords(data),out=await privateOutput(path.join(folder,'catalogue.json'));await mkdir(path.dirname(out),{recursive:true});await writeFile(out,JSON.stringify(records));await writeFile(path.join(folder,'catalogue.sql'),catalogueSql(records));await writeFile(path.join(folder,'catalogue-schema.sql'),BANK_CATALOGUE_SCHEMA+'\n');console.log(JSON.stringify({questions:records.length,output:out,server_mutations:false}));
}
