import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {mkdtemp,writeFile,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {gunzipSync} from 'node:zlib';
import {DatabaseSync} from 'node:sqlite';
import {indexDocument,buildSearchIndex} from './build-search-index.mjs';
const sha=s=>createHash('sha256').update(s).digest('hex');
const source='src_'+sha('synthetic'),locator='part-1/problem-3014',qid='q_'+sha(source+'\0'+locator);
const row={question_id:qid,source_id:source,language:'ko',text:'공기 저항을 무시한다.\n$$V=100\\,\\mathrm V$$',text_sha256:'',subjects_json:'["electromagnetism"]',locator,original_number:'3014',chapter:'1',level:'undergraduate',source_title:'Synthetic book',review_status:'pending',unresolved_source:0};row.text_sha256=sha(row.text);
test('search export preserves UTF-8/LaTeX bytes and indexes book/number metadata',()=>{
  const data=indexDocument(row);assert.equal(data[3],row.text);assert.equal(data[5],sha(data[3]));assert.match(data[4],/synthetic/);assert.match(data[4],/zznum3014e0/);
  assert.throws(()=>indexDocument({...row,text:row.text+'x'}),/Invalid/);assert.throws(()=>indexDocument({...row,question_id:'q_'+sha('wrong')}),/Wrong canonical/);
});
test('compressed private SQL round-trips all text and updates its FTS rows',async()=>{
  const dir=await mkdtemp(path.join(tmpdir(),'bank-index-'));try{
    const input=path.join(dir,'input.jsonl'),output=path.join(dir,'output');await writeFile(input,JSON.stringify(row)+'\n');
    const report=await buildSearchIndex(input,output);assert.deepEqual(report.language_counts,{en:0,ko:1});
    const expected=JSON.parse(await readFile(path.join(output,'expected.json'))),file=expected.files[0],compressed=await readFile(path.join(output,file.filename));
    assert.equal(sha(compressed),file.compressed_sha256);const sql=gunzipSync(compressed).toString('utf8');assert.equal(sha(sql),file.sha256);
    const db=new DatabaseSync(':memory:');try{db.exec(await readFile(path.join(output,'schema.sql'),'utf8'));db.exec(sql);const stored=db.prepare('SELECT text,text_sha256 FROM bank_search_documents').get();assert.equal(stored.text,row.text);assert.equal(sha(stored.text),stored.text_sha256);assert.equal(db.prepare("SELECT count(*) n FROM bank_search_fts WHERE bank_search_fts MATCH 'zznum3014e0'").get().n,1);}finally{db.close();}
  }finally{if(path.dirname(path.resolve(dir))!==path.resolve(tmpdir())||!path.basename(dir).startsWith('bank-index-'))throw Error('Unexpected temporary cleanup path');await rm(dir,{recursive:true,force:true});}
});
