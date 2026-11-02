// Private EN/KO solutions. No provider calls, production routes, or question writes.
import {createHash,randomUUID} from 'node:crypto';
import {readFile,open,rename,unlink} from 'node:fs/promises';
import {normalizeImport,sourceId,questionId,sqlLiteral,privateOutput} from './store.mjs';

const sha=value=>createHash('sha256').update(value).digest('hex');
const fail=message=>{throw new Error(message);};
const text=(value,label,max=200000)=>typeof value==='string'&&value.trim()&&value.length<=max&&!value.includes('\0')?value:fail(label+': invalid text');
const hash=(value,label)=>typeof value==='string'&&/^[a-f\d]{64}$/.test(value)?value:fail(label+': invalid SHA-256');
const choose=(value,values,label)=>values.includes(value)?value:fail(label+': unsupported value');
const schema=()=>readFile(new URL('./solutions-schema.sql',import.meta.url),'utf8');
function spans(input,source,required=true){
  if(!Array.isArray(input)||required&&!input.length||input.length>100)fail('Explicit solution source spans required');
  return input.map(span=>{
    const box=span.bbox;
    if(!Number.isSafeInteger(span.page)||span.page<1||span.page>source.page_count||!Array.isArray(box)||box.length!==4||box.some(v=>!Number.isFinite(v)||v<0||v>1)||box[0]>=box[2]||box[1]>=box[3])fail('Invalid solution source page or bbox');
    return {page:span.page,bbox:[...box]};
  });
}
const reference=source=>({...((source.origin)?{origin:source.origin}:{drive_id:source.drive_id}),revision:source.revision,sha256:source.sha256});

export function normalizeSolutions(input,index){
  if(input?.version!==1||index?.version!==1||!Array.isArray(input.solutions)||!Array.isArray(index.questions))fail('Invalid solution import/index format');
  const sources=normalizeImport({version:1,sources:input.sources}).sources;
  const solutionSources=new Map(sources.map(s=>[s.id,s]));
  const questionSources=new Map(normalizeImport({version:1,sources:index.sources}).sources.map(s=>[s.id,s]));
  const questions=new Map();
  for(const q of index.questions){
    const source=questionSources.get(sourceId(q.source));if(!source)fail('Unregistered canonical question source');
    const locator=text(q.locator,'question locator',1000),id=questionId(source,locator);
    if(questions.has(id))fail('Duplicate canonical question locator');
    questions.set(id,{source,locator,original_number:text(q.original_number,'original number',200)});
  }
  const results=new Map();
  for(const raw of input.solutions){
    const questionSourceId=sourceId(raw.question?.source??{}),locator=text(raw.question?.locator,'question locator',1000),qid=questionId(questionSourceId,locator),q=questions.get(qid);
    if(!q||q.source.id!==questionSourceId||raw.question.source_sha256!==q.source.sha256)fail('Solution must match an exact canonical question revision and PDF hash');
    if(raw.question.original_number!=null&&raw.question.original_number!==q.original_number)fail('Solution question number does not match its locator');
    const source=solutionSources.get(sourceId(raw.source));if(!source)fail('Unregistered solution source');
    const authorship=choose(raw.authorship,['source_transcription','haslalab_original_draft'],'authorship');
    // A source answer and a newly authored worked solution may use the same
    // problem-input PDF and printed locator. They must remain distinct records.
    const solutionLocator=text(raw.locator,'solution locator',1000),id='sol_'+sha(qid+'\0'+source.id+'\0'+authorship+'\0'+solutionLocator);
    const kind=choose(raw.kind,['worked_solution','answer_only','hint'],'kind');
    if(raw.review_status!=null&&raw.review_status!=='pending'||raw.publication_ready===true)fail('Authored solution imports must remain pending independent review and private');
    if(raw.source_image_checked!==true)fail('Original solution/input images must be checked');
    if(authorship==='haslalab_original_draft'&&raw.context?.generated_by!=='Codex')fail('Original drafts must identify their authorship');
    const rawContext=raw.context??{};if(!rawContext||Array.isArray(rawContext)||typeof rawContext!=='object'||JSON.stringify(rawContext).length>20000)fail('Invalid solution context');
    const solutionLanguage=raw.source_language??(authorship==='haslalab_original_draft'?'ko':source.source_language);
    if(!/^[a-z]{2}$/.test(solutionLanguage))fail('Invalid original solution language');
    const context={...rawContext,solution_source_language:solutionLanguage};
    if(authorship==='haslalab_original_draft'&&context.source_role!=='problem_input_for_original_draft')fail('Original drafts must identify their source as problem input');
    const item={id,question_id:qid,question_source:reference(q.source),question_locator:locator,source_id:source.id,locator:solutionLocator,kind,authorship,spans:spans(raw.spans,source),context,review_status:'pending',publication_ready:false,versions:[],assets:[]};
    const languages=new Set();
    for(const version of raw.versions??[]){
      const language=version.language;if(!/^[a-z]{2}$/.test(language))fail('Invalid solution language');if(languages.has(language))fail('Duplicate solution language');languages.add(language);
      const role=language===solutionLanguage?'original':'translation';
      if(version.role!==role)fail('Incorrect solution original/translation role');
      const body=text(version.text,'solution text'),digest=sha(body);
      item.versions.push({id:'sv_'+sha(id+'\0'+language+'\0'+role+'\0'+digest),language,role,text:body,text_sha256:digest,review_status:'pending'});
    }
    if(!['en','ko',solutionLanguage].every(language=>languages.has(language)))fail('Both English and Korean bodies and the original solution language are required');
    const keys=new Set();
    for(const asset of raw.assets??[]){
      const key=text(asset.asset_key,'solution asset key',500);if(keys.has(key))fail('Duplicate solution asset key');keys.add(key);
      if(authorship==='haslalab_original_draft'&&asset.role==='solution_crop')fail('Original draft input crops must be marked source_context or figure');
      const digest=hash(asset.sha256,'asset hash');
      if(typeof asset.inline_base64!=='string'||!asset.inline_base64.length||asset.inline_base64.length>5600000||!/^([A-Za-z\d+/]{4})*([A-Za-z\d+/]{2}==|[A-Za-z\d+/]{3}=)?$/.test(asset.inline_base64))fail('Invalid solution asset base64');
      const bytes=Buffer.from(asset.inline_base64,'base64');if(!bytes.length||bytes.length>4*1024*1024||sha(bytes)!==digest||asset.byte_length!==bytes.length)fail('Solution asset content hash/length mismatch');
      const chunks=[];for(let offset=0;offset<bytes.length;offset+=32768){const payload=bytes.subarray(offset,offset+32768);chunks.push({payload,sha256:sha(payload)});}
      item.assets.push({id:'sa_'+sha(id+'\0'+key),asset_key:key,role:choose(asset.role,['solution_crop','figure','source_context'],'solution asset role'),mime_type:choose(asset.mime_type,['image/png','image/jpeg','image/webp','image/svg+xml'],'solution asset MIME'),sha256:digest,byte_length:bytes.length,spans:spans(asset.spans,source),chunks});
    }
    if(!item.assets.length)fail('Source solution or original-draft input crops are required');
    const {versions,assets,...metadata}=item;item.metadata_sha256=sha(JSON.stringify(metadata));
    if(results.has(id))fail('Duplicate solution source locator for a question');results.set(id,item);
  }
  return {version:1,sources,solutions:[...results.values()]};
}

export function* solutionStatements(normalized,{timestamp=new Date().toISOString()}={}){
  if(!Number.isFinite(Date.parse(timestamp)))fail('Invalid solution timestamp');
  const statement=(sql,params)=>({sql,params});
  for(const s of normalized.sources){const body=JSON.stringify(s);yield statement('INSERT INTO bank_solution_sources VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET source_sha256=CASE WHEN bank_solution_sources.source_sha256=excluded.source_sha256 THEN bank_solution_sources.source_sha256 ELSE NULL END,source_json=excluded.source_json,source_metadata_sha256=excluded.source_metadata_sha256,updated_at=excluded.updated_at',[s.id,body,s.sha256,sha(body),timestamp,timestamp]);}
  for(const s of normalized.solutions){
    yield statement(`INSERT INTO bank_solutions VALUES(?,?,?,?,?,?,?,?,?,?,?,'pending',0,?,?) ON CONFLICT(id) DO UPDATE SET question_source_json=excluded.question_source_json,kind=excluded.kind,authorship=CASE WHEN bank_solutions.authorship=excluded.authorship THEN bank_solutions.authorship ELSE NULL END,spans_json=excluded.spans_json,context_json=excluded.context_json,metadata_sha256=excluded.metadata_sha256,review_status='pending',publication_ready=0,updated_at=excluded.updated_at`,[s.id,s.question_id,JSON.stringify(s.question_source),s.question_locator,s.source_id,s.locator,s.kind,s.authorship,JSON.stringify(s.spans),JSON.stringify(s.context),s.metadata_sha256,timestamp,timestamp]);
    // Each import supplies the complete current language snapshot (EN, KO and
    // the actual original). Preserve all older bodies/roles as inactive history.
    yield statement('UPDATE bank_solution_versions SET active=0 WHERE solution_id=?',[s.id]);
    for(const v of s.versions){yield statement(`INSERT INTO bank_solution_versions VALUES(?,?,?,?,?,?,'pending',1,?,?) ON CONFLICT(id) DO UPDATE SET active=1,review_status='pending',updated_at=excluded.updated_at`,[v.id,s.id,v.language,v.role,v.text,v.text_sha256,timestamp,timestamp]);}
    const obsolete=s.assets.length?' AND id NOT IN ('+s.assets.map(()=>'?').join(',')+')':'';
    yield statement('DELETE FROM bank_solution_asset_chunks WHERE asset_id IN (SELECT id FROM bank_solution_assets WHERE solution_id=?'+obsolete+')',[s.id,...s.assets.map(a=>a.id)]);
    yield statement('DELETE FROM bank_solution_assets WHERE solution_id=?'+obsolete,[s.id,...s.assets.map(a=>a.id)]);
    for(const a of s.assets){
      yield statement('INSERT INTO bank_solution_assets VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET role=excluded.role,mime_type=excluded.mime_type,sha256=excluded.sha256,byte_length=excluded.byte_length,chunk_count=excluded.chunk_count,spans_json=excluded.spans_json,updated_at=excluded.updated_at',[a.id,s.id,a.asset_key,a.role,a.mime_type,a.sha256,a.byte_length,a.chunks.length,JSON.stringify(a.spans),timestamp,timestamp]);
      yield statement('DELETE FROM bank_solution_asset_chunks WHERE asset_id=?',[a.id]);
      for(const [i,chunk] of a.chunks.entries())yield statement('INSERT INTO bank_solution_asset_chunks VALUES(?,?,?,?,?)',[a.id,i,chunk.payload.length,chunk.sha256,chunk.payload]);
    }
  }
}
function bind({sql,params}){let i=0;const result=sql.replace(/\?/g,()=>sqlLiteral(params[i++]));if(i!==params.length)fail('Solution SQL parameter mismatch');return result+';';}
export async function applySolutions(db,normalized,options){
  db.exec(await schema());db.exec('BEGIN IMMEDIATE');
  try{for(const {sql,params} of solutionStatements(normalized,options))db.prepare(sql).run(...params);db.exec('COMMIT');}catch(error){db.exec('ROLLBACK');throw error;}
}
export async function writeSolutionSql(normalized,target,options){
  const destination=await privateOutput(target),temporary=destination+'.'+randomUUID()+'.tmp';const file=await open(temporary,'wx',0o600);
  try{await file.writeFile('-- PRIVATE SOLUTION IMPORT. DO NOT COMMIT.\n'+await schema()+'\n');let buffer='';for(const statement of solutionStatements(normalized,options)){buffer+=bind(statement)+'\n';if(buffer.length>=1024*1024){await file.writeFile(buffer);buffer='';}}if(buffer)await file.writeFile(buffer);await file.sync();await file.close();await rename(temporary,destination);}catch(error){await file.close().catch(()=>{});await unlink(temporary).catch(()=>{});throw error;}return destination;
}
export function readSolutionAsset(db,id){
  const row=db.prepare('SELECT * FROM bank_solution_assets WHERE id=?').get(id);if(!row)return null;
  const chunks=db.prepare('SELECT * FROM bank_solution_asset_chunks WHERE asset_id=? ORDER BY chunk_index').all(id);if(chunks.length!==row.chunk_count)fail('Solution chunk count mismatch');
  for(const [i,c] of chunks.entries())if(c.chunk_index!==i||c.byte_length!==c.payload.length||sha(c.payload)!==c.sha256)fail('Solution chunk integrity failure');
  const bytes=Buffer.concat(chunks.map(c=>Buffer.from(c.payload)));if(bytes.length!==row.byte_length||sha(bytes)!==row.sha256)fail('Solution asset integrity failure');return bytes;
}
