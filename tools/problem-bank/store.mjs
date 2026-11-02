// Private import preparation only: no network, paid providers, or production bindings.
import {createHash,randomUUID} from 'node:crypto';
import {readFile,open,rename,unlink,mkdir,realpath,lstat} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';

export const SUBJECTS=['classical_mechanics','electromagnetism','thermodynamics','optics','quantum_mechanics','relativity','statistical_mechanics','oscillations_waves','mathematical_methods','astronomy_astrophysics','mixed'];
export const LEVELS=['high_school','olympiad','undergraduate','graduate','mixed'];
export const SCHEMA_PATH=fileURLToPath(new URL('./schema.sql',import.meta.url));
const PUBLIC_ROOT=fileURLToPath(new URL('../../',import.meta.url));
const sha=value=>createHash('sha256').update(value).digest('hex');
const fail=message=>{throw new Error(message);};
const object=(value,label)=>value&&typeof value==='object'&&!Array.isArray(value)?value:fail(`${label}: expected object`);
function text(value,label,max=1000){if(typeof value!=='string'||!value.trim()||value.length>max||value.includes('\0'))fail(`${label}: invalid text`);return value;}
function choice(value,allowed,label){if(!allowed.includes(value))fail(`${label}: unsupported value`);return value;}
function hash(value,label){if(typeof value!=='string'||!/^[a-f\d]{64}$/i.test(value))fail(`${label}: expected SHA-256`);return value.toLowerCase();}
function language(value,label){if(typeof value!=='string'||!/^[a-z]{2}$/.test(value))fail(`${label}: expected lower-case ISO language code`);return value;}
function subjects(value,label){if(!Array.isArray(value)||!value.length)fail(`${label}: required`);return [...new Set(value.map(v=>choice(v,SUBJECTS,label)))].sort();}
function positive(value,label){if(!Number.isSafeInteger(value)||value<1)fail(`${label}: expected positive integer`);return value;}
function privateKey(value,label){text(value,label,1800);if(/^[a-z][a-z\d+.-]*:|[\\\x00-\x1f]/i.test(value)||value.startsWith('/')||value.split('/').some(v=>!v||v==='.'||v==='..'))fail(`${label}: expected a private object key, not a URL or path traversal`);return value;}
function review(value){return choice(value??'pending',['pending','verified','rejected'],'review_status');}
function inlinePayload(value,expectedHash,expectedLength){
  if(value==null)return null;
  if(typeof value!=='string'||value.length>5600000||!value.length||!/^([A-Za-z\d+/]{4})*([A-Za-z\d+/]{2}==|[A-Za-z\d+/]{3}=)?$/.test(value))fail('asset.inline_base64: invalid or oversized base64');
  const bytes=Buffer.from(value,'base64');if(bytes.length>4*1024*1024||sha(bytes)!==expectedHash)fail('asset.inline_base64: content hash mismatch or over 4 MiB');
  if(expectedLength!=null&&expectedLength!==bytes.length)fail('asset.byte_length: mismatch');
  const chunks=[];for(let offset=0;offset<bytes.length;offset+=32768){const chunk=bytes.subarray(offset,offset+32768);chunks.push({bytes:chunk,sha256:sha(chunk)});}
  return {byte_length:bytes.length,sha256:expectedHash,chunks};
}
function spans(value,source,label){
  if(!Array.isArray(value)||!value.length||value.length>100)fail(`${label}: explicit source pages and boxes required`);
  return value.map((span,index)=>{object(span,label);positive(span.page,label);if(span.page>source.page_count)fail(`${label}: page exceeds source`);
    const b=span.bbox;if(!Array.isArray(b)||b.length!==4||!b.every(v=>Number.isFinite(v)&&v>=0&&v<=1)||b[0]>=b[2]||b[1]>=b[3])fail(`${label}[${index}]: bbox must be [x0,y0,x1,y1] in normalized 0..1 coordinates`);
    return {page:span.page,bbox:[...b]};});
}
function sourceUrl(value){
  const input=text(value,'origin.url',3000);let url;try{url=new URL(input);}catch{fail('origin.url: expected an absolute HTTPS URL');}
  if(url.protocol!=='https:'||url.username||url.password||url.search||url.port)fail('origin.url: expected HTTPS URL without credentials, query or custom port');
  url.hash='';return url.href;
}
function urlOrigin(raw){
  object(raw,'source.origin');choice(raw.kind,['url'],'source.origin.kind');
  const origin={kind:'url',url:sourceUrl(raw.url),attribution:text(raw.attribution,'origin.attribution',2000),
    license_identifier:text(raw.license_identifier,'origin.license_identifier',240),license_url:sourceUrl(raw.license_url)};
  if(raw.terms_url!=null)origin.terms_url=sourceUrl(raw.terms_url);
  if(raw.archive_member!=null){
    const member=object(raw.archive_member,'origin.archive_member');
    origin.archive_member={container_sha256:hash(member.container_sha256,'archive.container_sha256'),
      member_path:privateKey(member.member_path,'archive.member_path'),member_sha256:hash(member.member_sha256,'archive.member_sha256')};
  }
  return origin;
}
export function sourceId(source){
  const revision=text(source.revision,'revision',240);
  if(source.origin!=null){
    if(source.drive_id!=null)fail('Source identity cannot combine Drive and URL origins');
    object(source.origin,'source.origin');choice(source.origin.kind,['url'],'source.origin.kind');
    return 'src_'+sha('url\0'+sourceUrl(source.origin.url)+'\0'+revision);
  }
  return 'src_'+sha(text(source.drive_id,'drive_id',240)+'\0'+revision);
}
export function questionId(source,locator){return 'q_'+sha((typeof source==='string'?source:sourceId(source))+'\0'+text(locator,'locator',1000));}

export function normalizeImport(manifest,questionFile={version:1,questions:[]}){
  object(manifest,'manifest');object(questionFile,'questions');if(manifest.version!==1||questionFile.version!==1)fail('Only import format version 1 is supported');
  if(!Array.isArray(manifest.sources)||!manifest.sources.length)fail('sources: at least one source required');
  if(!Array.isArray(questionFile.questions))fail('questions: expected array');
  const sourceMap=new Map();
  for(const raw of manifest.sources){object(raw,'source');const id=sourceId(raw);
    if(raw.origin==null&&!/^[A-Za-z\d_-]{5,240}$/.test(raw.drive_id))fail('drive_id: invalid stable Drive ID');
    const source={id,drive_id:raw.origin==null?raw.drive_id:null,revision:raw.revision,title:text(raw.title,'title',2000),mime_type:choice(raw.mime_type??'application/pdf',['application/pdf'],'mime_type'),
      sha256:hash(raw.sha256,'source.sha256'),page_count:positive(raw.page_count,'page_count'),subjects:subjects(raw.subjects,'source.subjects'),level:choice(raw.level,LEVELS,'source.level'),
      source_language:language(raw.source_language,'source_language'),private_object_key:raw.private_object_key==null?null:privateKey(raw.private_object_key,'source.private_object_key'),
      local_path:raw.local_path==null?null:text(raw.local_path,'local_path',3000),expected_question_count:raw.expected_question_count==null?null:positive(raw.expected_question_count,'expected_question_count'),extraction_complete:raw.extraction_complete===true};
    if(raw.origin!=null){
      source.origin=urlOrigin(raw.origin);
      if(source.revision!=='sha256:'+source.sha256)fail('URL source revision must identify the actual PDF SHA-256');
      if(source.origin.archive_member&&source.origin.archive_member.member_sha256!==source.sha256)fail('Archive member SHA-256 must identify the actual source PDF');
    }
    if(raw.extraction_complete!=null&&typeof raw.extraction_complete!=='boolean')fail('extraction_complete: expected boolean');
    if(source.extraction_complete&&source.expected_question_count==null)fail('Complete extraction requires expected_question_count');
    if(sourceMap.has(id)&&JSON.stringify(sourceMap.get(id))!==JSON.stringify(source))fail('Conflicting duplicate source revision');sourceMap.set(id,source);
  }
  const questionMap=new Map();
  for(const raw of questionFile.questions){object(raw,'question');object(raw.source,'question.source');const source=sourceMap.get(sourceId(raw.source));if(!source)fail('Question references an unregistered source revision');
    const locator=text(raw.locator,'locator',1000),id=questionId(source.id,locator),q={id,source_id:source.id,locator,original_number:text(raw.original_number,'original_number',200),
      chapter:raw.chapter==null?null:text(raw.chapter,'chapter',1000),kind:choice(raw.kind??'problem',['problem','exercise','example'],'kind'),subjects:subjects(raw.subjects??source.subjects,'question.subjects'),
      level:choice(raw.level??source.level,LEVELS,'question.level'),spans:spans(raw.spans,source,'question.spans'),review_status:review(raw.review_status)};
    q.source_language=language(raw.source_language??source.source_language,'question.source_language');
    q.context=object(raw.context??{},'question.context');
    if(JSON.stringify(q.context).length>20000)fail('Question context exceeds storage limit');
    if(q.context.unresolved_source!=null&&typeof q.context.unresolved_source!=='boolean')fail('unresolved_source must be boolean');
    const {review_status,...metadata}=q;q.metadata_hash=sha(JSON.stringify(metadata));q.versions=[];q.assets=[];
    if(raw.assets_complete!=null&&typeof raw.assets_complete!=='boolean')fail('assets_complete must be boolean');
    q.assets_complete=raw.assets_complete===true;
    if(!Array.isArray(raw.versions??[])||!Array.isArray(raw.assets??[]))fail('Question versions/assets must be arrays');
    const languages=new Set();for(const version of raw.versions??[]){object(version,'version');const lang=language(version.language,'version.language');if(languages.has(lang))fail('One supplied version per language per import');languages.add(lang);
      const role=choice(version.role,['original','translation'],'version.role');if((role==='original')!==(lang===q.source_language))fail('Original/translation role must match question source_language');
      const body=text(version.text,'version.text',200000),digest=sha(body);q.versions.push({id:'v_'+sha(id+'\0'+lang+'\0'+digest),language:lang,role,text:body,text_sha256:digest,review_status:review(version.review_status)});
    }
    const assetIds=new Set();for(const asset of raw.assets??[]){object(asset,'asset');const assetId=text(asset.asset_id,'asset_id',500);if(assetIds.has(assetId))fail('Duplicate asset_id in question');assetIds.add(assetId);
      const assetHash=hash(asset.sha256,'asset.sha256'),inline=inlinePayload(asset.inline_base64,assetHash,asset.byte_length),storageId='a_'+sha(id+'\0'+assetId);
      q.assets.push({id:storageId,asset_id:assetId,role:choice(asset.role,['figure','question_crop'],'asset.role'),private_object_key:privateKey(asset.private_object_key??(inline?'d1-inline/'+storageId:undefined),'asset.private_object_key'),
        mime_type:choice(asset.mime_type,['image/png','image/jpeg','image/webp','image/svg+xml','application/pdf'],'asset.mime_type'),sha256:assetHash,spans:spans(asset.spans,source,'asset.spans'),inline});
    }
    if(questionMap.has(id)&&JSON.stringify(questionMap.get(id))!==JSON.stringify(q))fail('Conflicting duplicate question locator');questionMap.set(id,q);
  }
  return {version:1,sources:[...sourceMap.values()].sort((a,b)=>a.page_count-b.page_count||a.id.localeCompare(b.id)),questions:[...questionMap.values()]};
}

// SQL text has fixed identifiers only; external values are parameters throughout.
export function* importStatementIterator(normalized,{timestamp=new Date().toISOString()}={}){
  if(!Number.isFinite(Date.parse(timestamp)))fail('Invalid import timestamp');const statement=(sql,params)=>({sql,params});
  for(const s of normalized.sources){yield statement(`INSERT INTO book_sources(id,drive_id,revision,title,mime_type,sha256,page_count,subjects_json,level,source_language,private_object_key,local_path,expected_question_count,extraction_complete,created_at,updated_at)
    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,
    sha256=CASE WHEN book_sources.sha256=excluded.sha256 AND book_sources.page_count=excluded.page_count AND book_sources.source_language=excluded.source_language THEN excluded.sha256 ELSE NULL END,
    subjects_json=excluded.subjects_json,level=excluded.level,private_object_key=COALESCE(excluded.private_object_key,book_sources.private_object_key),local_path=COALESCE(excluded.local_path,book_sources.local_path),
    expected_question_count=COALESCE(excluded.expected_question_count,book_sources.expected_question_count),extraction_complete=MAX(book_sources.extraction_complete,excluded.extraction_complete),updated_at=excluded.updated_at`,
    // The legacy SQL column is an opaque identity key. A URL origin stores its
    // actual URL here; it never fabricates a Drive file ID. Public provenance
    // remains explicitly typed in bank_source_origins and normalized sources.
    [s.id,s.drive_id??s.origin?.url,s.revision,s.title,s.mime_type,s.sha256,s.page_count,JSON.stringify(s.subjects),s.level,s.source_language,s.private_object_key,s.local_path,s.expected_question_count,+s.extraction_complete,timestamp,timestamp]);
    if(s.origin)yield statement(`INSERT INTO bank_source_origins(source_id,origin_json,updated_at) VALUES(?,?,?)
      ON CONFLICT(source_id) DO UPDATE SET origin_json=excluded.origin_json,updated_at=excluded.updated_at`,[s.id,JSON.stringify(s.origin),timestamp]);
  }
  for(const q of normalized.questions){
    yield statement(`INSERT INTO bank_questions(id,source_id,locator,original_number,chapter,kind,subjects_json,level,spans_json,review_status,metadata_hash,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
      ON CONFLICT(id) DO UPDATE SET original_number=excluded.original_number,chapter=excluded.chapter,kind=excluded.kind,subjects_json=excluded.subjects_json,level=excluded.level,spans_json=excluded.spans_json,
      review_status=CASE WHEN bank_questions.metadata_hash=excluded.metadata_hash AND bank_questions.review_status='verified' AND excluded.review_status='pending' THEN 'verified' ELSE excluded.review_status END,
      metadata_hash=excluded.metadata_hash,updated_at=excluded.updated_at`,[q.id,q.source_id,q.locator,q.original_number,q.chapter,q.kind,JSON.stringify(q.subjects),q.level,JSON.stringify(q.spans),q.review_status,q.metadata_hash,timestamp,timestamp]);
    yield statement(`INSERT INTO bank_question_context(question_id,source_language,context_json,updated_at) VALUES(?,?,?,?)
      ON CONFLICT(question_id) DO UPDATE SET source_language=excluded.source_language,context_json=excluded.context_json,updated_at=excluded.updated_at`,[q.id,q.source_language,JSON.stringify(q.context),timestamp]);
    for(const v of q.versions){
      yield statement(`UPDATE bank_question_versions SET active=0 WHERE question_id=? AND language=? AND id!=?`,[q.id,v.language,v.id]);
      yield statement(`INSERT INTO bank_question_versions(id,question_id,language,role,text,text_sha256,review_status,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,1,?,?)
        ON CONFLICT(id) DO UPDATE SET active=1,review_status=CASE WHEN bank_question_versions.review_status='verified' AND excluded.review_status='pending' THEN 'verified' ELSE excluded.review_status END,updated_at=excluded.updated_at`,[v.id,q.id,v.language,v.role,v.text,v.text_sha256,v.review_status,timestamp,timestamp]);
    }
    if(q.assets_complete){
      const remaining=q.assets.length?' AND id NOT IN ('+q.assets.map(()=>'?').join(',')+')':'';
      const obsolete=`SELECT id FROM bank_assets WHERE question_id=?${remaining}`,params=[q.id,...q.assets.map(a=>a.id)];
      yield statement(`DELETE FROM bank_asset_chunks WHERE asset_id IN (${obsolete})`,params);
      yield statement(`DELETE FROM bank_asset_payloads WHERE asset_id IN (${obsolete})`,params);
      yield statement(`DELETE FROM bank_assets WHERE id IN (${obsolete})`,params);
    }
    for(const a of q.assets){yield statement(`INSERT INTO bank_assets(id,question_id,asset_id,role,private_object_key,mime_type,sha256,spans_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)
      ON CONFLICT(id) DO UPDATE SET role=excluded.role,private_object_key=excluded.private_object_key,mime_type=excluded.mime_type,sha256=excluded.sha256,spans_json=excluded.spans_json,updated_at=excluded.updated_at`,[a.id,q.id,a.asset_id,a.role,a.private_object_key,a.mime_type,a.sha256,JSON.stringify(a.spans),timestamp,timestamp]);
      yield statement('DELETE FROM bank_asset_chunks WHERE asset_id=?',[a.id]);yield statement('DELETE FROM bank_asset_payloads WHERE asset_id=?',[a.id]);
      if(a.inline){yield statement('INSERT INTO bank_asset_payloads(asset_id,byte_length,sha256,chunk_count) VALUES(?,?,?,?)',[a.id,a.inline.byte_length,a.inline.sha256,a.inline.chunks.length]);
        for(const [index,chunk] of a.inline.chunks.entries())yield statement('INSERT INTO bank_asset_chunks(asset_id,chunk_index,byte_length,sha256,payload) VALUES(?,?,?,?,?)',[a.id,index,chunk.bytes.length,chunk.sha256,chunk.bytes]);}
    }
  }
  const job=(source,question,stage,inputHash,status)=>statement(`INSERT INTO bank_jobs(id,source_id,question_id,stage,status,input_hash,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)
    ON CONFLICT(id) DO UPDATE SET status=CASE WHEN excluded.status='done' THEN 'done' ELSE bank_jobs.status END,updated_at=excluded.updated_at`,['j_'+sha(source+'\0'+(question??'')+'\0'+stage+'\0'+inputHash),source,question,stage,status,inputHash,timestamp,timestamp]);
  for(const s of normalized.sources)yield job(s.id,null,'extract',s.sha256,s.extraction_complete?'done':'pending');
  for(const q of normalized.questions){
    const original=q.versions.find(v=>v.role==='original');
    for(const lang of ['ko','en']){const v=q.versions.find(v=>v.language===lang);if(!v||v.role==='translation')yield job(q.source_id,q.id,'translate_'+lang,sha(q.metadata_hash+(original?.text_sha256??'')),v?'done':'pending');}
    const reviewed=q.review_status==='verified'&&!q.context.unresolved_source&&['ko','en'].every(lang=>q.versions.some(v=>v.language===lang&&v.review_status==='verified'));
    yield job(q.source_id,q.id,'review',sha(q.metadata_hash+q.versions.map(v=>v.text_sha256).join('')),reviewed?'done':'pending');
  }
  // A NULL hash violates the table constraint and rolls back the entire transaction
  // if a purported complete extraction omits or overcounts stored questions.
  for(const s of normalized.sources)yield statement(`UPDATE book_sources SET sha256=CASE WHEN extraction_complete=0 OR expected_question_count=(SELECT COUNT(*) FROM bank_questions WHERE source_id=book_sources.id) THEN sha256 ELSE NULL END WHERE id=?`,[s.id]);
}

export function importStatements(normalized,options){return [...importStatementIterator(normalized,options)];}


export async function schemaSql(){return readFile(SCHEMA_PATH,'utf8');}
export async function applyImport(db,normalized,options){
  db.exec(await schemaSql());db.exec('BEGIN IMMEDIATE');
  try{for(const {sql,params} of importStatementIterator(normalized,options))db.prepare(sql).run(...params);db.exec('COMMIT');}
  catch(error){db.exec('ROLLBACK');throw error;}
  return db.prepare('SELECT * FROM bank_source_readiness ORDER BY page_count,id').all();
}
export async function applyD1Import(db,normalized,options){
  // Initialize schema separately through schema.sql; one batch is atomic on D1.
  return db.batch(importStatements(normalized,options).map(({sql,params})=>db.prepare(sql).bind(...params.map(value=>value instanceof Uint8Array?value.buffer.slice(value.byteOffset,value.byteOffset+value.byteLength):value))));
}
export function sqlLiteral(value){if(value==null)return 'NULL';if(value instanceof Uint8Array)return "X'"+Buffer.from(value).toString('hex')+"'";if(typeof value==='number'){if(!Number.isFinite(value))fail('Nonfinite SQL number');return String(value);}if(typeof value!=='string'||value.includes('\0'))fail('Unsupported SQL literal');return "'"+value.replaceAll("'","''")+"'";}
export function readInlineAsset(db,assetId){
  const metadata=db.prepare('SELECT * FROM bank_asset_payloads WHERE asset_id=?').get(assetId);if(!metadata)return null;
  const chunks=db.prepare('SELECT * FROM bank_asset_chunks WHERE asset_id=? ORDER BY chunk_index').all(assetId);
  if(chunks.length!==metadata.chunk_count)fail('Stored asset chunk count mismatch');
  for(const [index,chunk] of chunks.entries())if(chunk.chunk_index!==index||chunk.payload.length!==chunk.byte_length||sha(chunk.payload)!==chunk.sha256)fail('Stored asset chunk integrity failure');
  const bytes=Buffer.concat(chunks.map(chunk=>Buffer.from(chunk.payload)));if(bytes.length!==metadata.byte_length||sha(bytes)!==metadata.sha256)fail('Stored asset integrity failure');return bytes;
}
function bindSql({sql,params}){let index=0;const bound=sql.replace(/\?/g,()=>sqlLiteral(params[index++]));if(index!==params.length)fail('SQL parameter mismatch');return bound+';';}
export async function exportImportSql(normalized,options){return '-- PRIVATE QUESTION-BANK IMPORT. DO NOT COMMIT THIS FILE.\n-- D1 file import supplies its own transaction; no BEGIN/COMMIT here.\n'+await schemaSql()+'\n'+importStatements(normalized,options).map(bindSql).join('\n')+'\n';}

// Keep only a bounded SQL buffer; image payloads can make a whole-file string exceed
// V8's maximum string size even when the normalized input fits in available memory.
export async function writeImportSql(normalized,target,options){
  const out=await privateOutput(target),temporary=out+'.'+randomUUID()+'.tmp';
  const handle=await open(temporary,'wx',0o600);
  try{
    await handle.writeFile('-- PRIVATE QUESTION-BANK IMPORT. DO NOT COMMIT THIS FILE.\n-- D1 file import supplies its own transaction; no BEGIN/COMMIT here.\n'+await schemaSql()+'\n','utf8');
    let buffer='';
    for(const statement of importStatementIterator(normalized,options)){
      buffer+=bindSql(statement)+'\n';
      if(buffer.length>=1024*1024){await handle.writeFile(buffer,'utf8');buffer='';}
    }
    if(buffer)await handle.writeFile(buffer,'utf8');
    await handle.sync();await handle.close();await rename(temporary,out);
  }catch(error){await handle.close().catch(()=>{});await unlink(temporary).catch(()=>{});throw error;}
  return out;
}

export async function privateOutput(target){
  const absolute=path.resolve(target),parent=path.dirname(absolute);await mkdir(parent,{recursive:true});
  const actual=path.join(await realpath(parent),path.basename(absolute)),root=await realpath(PUBLIC_ROOT),relative=path.relative(root,actual);
  if(!relative||!relative.startsWith('..'+path.sep)&&relative!=='..'&&!path.isAbsolute(relative))fail('Refusing to write private content inside the public Git checkout');
  try{if((await lstat(actual)).isSymbolicLink())fail('Refusing to follow a private output symlink');}catch(error){if(error.code!=='ENOENT')throw error;}
  return actual;
}
export async function main(argv=process.argv.slice(2)){
  const options={};for(let index=0;index<argv.length;index+=2){if(!['--manifest','--questions','--out'].includes(argv[index])||!argv[index+1]||options[argv[index]])fail('Usage: node store.mjs --manifest PRIVATE/manifest.json [--questions PRIVATE/questions.json] --out PRIVATE/import.sql');options[argv[index]]=argv[index+1];}
  if(!options['--manifest']||!options['--out'])fail('--manifest and --out are required');
  const manifest=JSON.parse(await readFile(options['--manifest'],'utf8'));
  const questionFile=options['--questions']?JSON.parse(await readFile(options['--questions'],'utf8')):undefined;
  const normalized=normalizeImport(manifest,questionFile),out=await writeImportSql(normalized,options['--out']);
  const supplied=normalized.questions.flatMap(q=>q.versions);console.log(JSON.stringify({sources:normalized.sources.length,questions:normalized.questions.length,language_versions:supplied.length,
    verified_language_versions:supplied.filter(v=>v.review_status==='verified').length,output:out,server_imported:false}));
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href)main().catch(error=>{console.error(error.message);process.exitCode=1;});
