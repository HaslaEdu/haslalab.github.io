// Offline private export: no provider or network calls. Never put book text in Git.
import {createHash} from 'node:crypto';
import {createReadStream} from 'node:fs';
import {mkdir,readFile,writeFile,realpath} from 'node:fs/promises';
import {createInterface} from 'node:readline';
import {gzipSync} from 'node:zlib';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {PROBLEM_BANK_SEARCH_SCHEMA,problemBankIndexText} from '../../community/src/problem-bank.js';
const sha=x=>createHash('sha256').update(x).digest('hex');
const quote=x=>x==null?'NULL':typeof x==='number'?String(x):"'"+String(x).replaceAll("'","''")+"'";
export function indexDocument(row){
  if(!/^q_[a-f0-9]{64}$/.test(row.question_id)||!/^src_[a-f0-9]{64}$/.test(row.source_id)||!['en','ko'].includes(row.language)||typeof row.text!=='string'||sha(row.text)!==row.text_sha256)throw Error('Invalid current canonical body');
  if(row.question_id!=='q_'+sha(row.source_id+'\0'+row.locator))throw Error('Wrong canonical identity');
  const subjects=JSON.parse(row.subjects_json);if(!Array.isArray(subjects)||!subjects.length)throw Error('Missing subject metadata');
  return [row.question_id,row.source_id,row.language,row.text,problemBankIndexText([row.source_title,row.original_number,row.locator,row.text].join('\n')),row.text_sha256,row.subjects_json,row.locator,row.original_number,row.chapter??null,row.level,row.source_title,row.review_status,Number(!!row.unresolved_source)];
}
export async function buildSearchIndex(input,output){
  const root=await realpath(fileURLToPath(new URL('../../',import.meta.url))),target=path.resolve(output);
  await mkdir(target,{recursive:true});const actual=await realpath(target);if(actual===root||actual.startsWith(root+path.sep))throw Error('Private corpus export cannot enter public checkout');
  const columns='question_id,source_id,language,text,search_text,text_sha256,subjects_json,locator,original_number,chapter,level,source_title,review_status,unresolved_source';
  const manifest={version:1,private:true,files:[],documents:[],question_ids:new Set(),language_counts:{en:0,ko:0}};
  await writeFile(path.join(actual,'schema.sql'),PROBLEM_BANK_SEARCH_SCHEMA+'\n');let batch=[],batchNumber=0,keys=new Set();
  const flush=async()=>{if(!batch.length)return;const filename=`batch-${String(++batchNumber).padStart(3,'0')}.sql.gz`,sql=batch.join('\n')+'\n',compressed=gzipSync(sql);await writeFile(path.join(actual,filename),compressed);manifest.files.push({filename,sha256:sha(sql),compressed_sha256:sha(compressed),documents:batch.length});batch=[];};
  for await(const line of createInterface({input:createReadStream(input),crlfDelay:Infinity})){
    if(!line.trim())continue;const row=JSON.parse(line),values=indexDocument(row),key=row.question_id+'/'+row.language;if(keys.has(key))throw Error('Duplicate canonical body');keys.add(key);
    batch.push(`INSERT INTO bank_search_documents(${columns}) VALUES(${values.map(quote).join(',')}) ON CONFLICT(question_id,language) DO UPDATE SET ${columns.split(',').filter(x=>!['question_id','language'].includes(x)).map(x=>`${x}=excluded.${x}`).join(',')};`);
    manifest.documents.push({question_id:row.question_id,language:row.language,text_sha256:row.text_sha256,search_text_sha256:sha(values[4]),metadata_sha256:sha(JSON.stringify({source_id:row.source_id,locator:row.locator,original_number:row.original_number,chapter:row.chapter??null,subjects_json:row.subjects_json,level:row.level,source_title:row.source_title,review_status:row.review_status,unresolved_source:Number(!!row.unresolved_source)}))});manifest.question_ids.add(row.question_id);manifest.language_counts[row.language]++;
    if(batch.length>=300)await flush();
  }await flush();manifest.question_count=manifest.question_ids.size;delete manifest.question_ids;await writeFile(path.join(actual,'expected.json'),JSON.stringify(manifest));return {question_count:manifest.question_count,language_counts:manifest.language_counts,batches:manifest.files.length};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const [input,output]=process.argv.slice(2);if(!input||!output)throw Error('Expected private input JSONL and output directory');console.log(JSON.stringify(await buildSearchIndex(input,output)));
}
