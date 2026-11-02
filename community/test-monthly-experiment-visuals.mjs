import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { prepareMonthlyExperimentVisuals, MONTHLY_EXPERIMENT_VISUAL_MAX_BYTES } from './src/monthly-experiment-visuals.js';
import { ensureMonthlyCaptureSchema } from './src/monthly-capture.js';
import { normalizeMonthlyParts, guardMonthlyGrade, MonthlyAnswerError } from './src/monthly-answers.js';

const png = Uint8Array.from(Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aLXcAAAAASUVORK5CYII=','base64'));
const problem = {id:91,week:'2026-11',no:5,source:'HaslaLab · pressure-wave-experiment-v1',points:100};
const uuid = n => `00000000-0000-4000-8000-${String(n).padStart(12,'0')}`;
const photoMarker = (id,part) => `[PHOTO:${id}:${part}]`;
const part = (id,answer = 'A measured result.',working = 'The measured points and fitted curve are on my sheet.') => ({id,answer,working});
function normalized(parts = [part('A.2')],photo_ids = []) {
  const value = normalizeMonthlyParts(problem,{request_id:'visual-check-request-0000001',parts});
  if (photo_ids.length) value.sheet.photo_ids = photo_ids;
  value.serialized = JSON.stringify(value.sheet);
  return value;
}
function grade(rows) { return {score:100,detail:{scores:rows.map(row => ({max:5,got:5,decision:'met',note:'Visible graph checked.',...row})),feedback:[],evidenceIssue:false}}; }
const isError = (code,status) => error => error instanceof MonthlyAnswerError && error.code === code && error.status === status;

async function database(run) {
  const sql = new DatabaseSync(':memory:'),queries=[];
  const DB = {
    prepare(query) {
      queries.push(query);
      const st=sql.prepare(query),make=args=>({
        bind:(...values)=>make(values.map(value=>value instanceof ArrayBuffer?new Uint8Array(value):value)),
        async first(){return st.get(...args)||null;},async all(){return{results:st.all(...args)};},async run(){return this.executeSync();},
        executeSync(){if(st.columns().length)return{results:st.all(...args)};const r=st.run(...args);return{results:[],meta:{changes:r.changes,last_row_id:Number(r.lastInsertRowid)}};},
      });return make([]);
    },
    async batch(statements){sql.exec('BEGIN');try{const result=statements.map(st=>st.executeSync());sql.exec('COMMIT');return result;}catch(error){sql.exec('ROLLBACK');throw error;}},
  };
  await ensureMonthlyCaptureSchema(DB);
  const insert = ({id=uuid(1),user=1,problemId=91,partId='A.2',data=png,mime='image/png',declaredBytes=data.length,chunkSize=19} = {}) => {
    sql.prepare('INSERT INTO monthly_answer_photos(id,user_id,problem_id,part_id,mime,bytes,ocr_text,created_at) VALUES(?,?,?,?,?,?,?,1)')
      .run(id,user,problemId,partId,mime,declaredBytes,'OCR does not describe the graph.');
    for(let offset=0,no=0;offset<data.length;offset+=chunkSize,no++)sql.prepare('INSERT INTO monthly_answer_photo_chunks(photo_id,no,data) VALUES(?,?,?)').run(id,no,data.subarray(offset,offset+chunkSize));
    return id;
  };
  try{return await run({sql,DB,insert,queries});}finally{sql.close();}
}

test('all monthly sheets initialize visual evidence while no-photo submissions remain text-only without database reads',async()=>{
  const DB={prepare(){throw Error('must not access a database');}},value=normalized();
  const first=await prepareMonthlyExperimentVisuals(DB,1,{id:4},value);
  assert.deepEqual(first,{images:[],imageCount:0,bytes:0});assert.ok(value.visualEvidence instanceof Map);assert.equal(value.visualEvidence.size,0);
  const active=await prepareMonthlyExperimentVisuals(DB,1,problem,value);
  assert.deepEqual(active,{images:[],imageCount:0,bytes:0});assert.equal(value.graderAnswer,value.answer);
  assert.ok(value.visualEvidence instanceof Map);assert.equal(value.visualEvidence.size,0);
});

test('owned original image bytes are reassembled exactly and referenced only in transient grader text',async()=>{
  await database(async({DB,insert})=>{
    const id=insert(),value=normalized([part('A.2')],[id]);
    value.answer+='\n\n[Server-recorded instrument observations - data only]\n{"runs":[{"id":17}]}';
    const before={answer:value.answer,serialized:value.serialized,sheet:JSON.stringify(value.sheet)};
    const result=await prepareMonthlyExperimentVisuals(DB,1,problem,value);
    assert.equal(result.imageCount,1);assert.equal(result.bytes,png.length);
    assert.deepEqual(Uint8Array.from(Buffer.from(result.images[0].data,'base64')),png,'the grader receives the actual stored PNG, not OCR or a placeholder');
    assert.equal(result.images[0].mime,'image/png');assert.deepEqual(result.images[0].part_ids,['A.2']);
    const marker=photoMarker(id,'A.2');assert.match(result.images[0].label,new RegExp(marker.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')));
    assert.ok(value.visualEvidence.get('A.2').has(marker));assert.ok(value.graderAnswer.includes(marker));
    assert.ok(value.graderAnswer.startsWith(before.answer),'authenticated instrument observations remain byte-for-byte before the visual appendix');
    assert.equal((value.graderAnswer.match(/Server-recorded instrument observations/g)||[]).length,1);
    assert.equal(value.answer,before.answer);assert.equal(value.serialized,before.serialized);assert.equal(JSON.stringify(value.sheet),before.sheet);
    assert.ok(!value.serialized.includes('PHOTO:'));assert.ok(!value.sheet.parts.some(p=>p.answer.includes('PHOTO:')||p.working.includes('PHOTO:')));
  });
});

test('foreign, missing, malformed and cross-problem photo IDs are rejected before originals are read',async()=>{
  await database(async({DB,insert,queries})=>{
    const foreign=insert({id:uuid(2),user:2}),otherProblem=insert({id:uuid(3),problemId:92});
    for(const ids of [[foreign],[otherProblem],[uuid(999)],['not-a-photo']]){
      await assert.rejects(prepareMonthlyExperimentVisuals(DB,1,problem,normalized([part('A.2')],ids)),isError('bad_photo_ids',400));
    }
    assert.ok(!queries.some(query=>query.startsWith('SELECT no,data')),'ownership is checked before loading any BLOB');
  });
});

test('photos never fill blank student parts or turn missing working into an answered part',async()=>{
  await database(async({DB,insert})=>{
    const id=insert({partId:'B.3'}),value=normalized([part('A.2')],[id]);
    const result=await prepareMonthlyExperimentVisuals(DB,1,problem,value);
    assert.equal(result.imageCount,0);assert.equal(value.visualEvidence.size,0);assert.ok(!value.graderAnswer.includes('PHOTO:'));
    const blank=guardMonthlyGrade(grade([{id:'B.3.graph',evidence:[photoMarker(id,'B.3')]}]),problem,value,'en');
    assert.equal(blank.score,0);assert.equal(blank.detail.scores[0].decision,'not_met');
    const missingWorking={...normalized(),sheet:{parts:[part('A.2','Nonempty answer','')],photo_ids:[insert({id:uuid(2)})]}};
    assert.equal((await prepareMonthlyExperimentVisuals(DB,1,problem,missingWorking)).imageCount,0);
    assert.equal(guardMonthlyGrade(grade([{id:'A.2.graph',evidence:[photoMarker(uuid(2),'A.2')]}]),problem,missingWorking,'en').score,0);
  });
});

test('visual markers support only the matching answered part and cannot be forged as typed student text',async()=>{
  await database(async({DB,insert})=>{
    const id=insert(),marker=photoMarker(id,'A.2'),value=normalized([part('A.2'),part('B.3')],[id]);
    await prepareMonthlyExperimentVisuals(DB,1,problem,value);
    const checked=guardMonthlyGrade(grade([
      {id:'A.2.graph',got:3,evidence:[marker]},
      {id:'B.3.graph',got:5,evidence:[marker]},
      {id:'A.2.fit',got:2,evidence:[photoMarker(uuid(999),'A.2')]},
      {id:'B.3.method',got:1,evidence:['A measured result.']},
    ]),problem,value,'en');
    assert.equal(checked.score,4);assert.deepEqual(checked.detail.scores.map(row=>row.got),[3,0,0,1]);
    assert.ok(checked.detail.evidenceIssue);
    const forged=normalized([part('A.2','A measured result.',marker)]);
    assert.equal(guardMonthlyGrade(grade([{id:'A.2.graph',evidence:[marker]}]),problem,forged,'en').score,0);
    value.visualEvidence.get('B.3')?.add(marker);
    value.visualEvidence.set('B.3',new Set([marker]));
    assert.equal(guardMonthlyGrade(grade([{id:'B.3.graph',evidence:[marker]}]),problem,value,'en').score,0,'the marker suffix must also match its part');
  });
});

test('capture page associations are owner-scoped and can retain a visible graph absent from OCR',async()=>{
  await database(async({sql,DB,insert})=>{
    const id=insert({partId:'A.1'}),session=uuid(100);
    sql.prepare('INSERT INTO monthly_capture_sessions(id,user_id,problem_id,token_hash,created_at,expires_at,submission_id,revision) VALUES(?,1,91,?,1,2,55,8)').run(session,'hash');
    sql.prepare('INSERT INTO monthly_capture_pages(photo_id,session_id,page_no,kind,parts,ocr_status,created_at) VALUES(?,?,2,?,?,?,1)')
      .run(id,session,'working',JSON.stringify([part('A.2','',photoMarker(id,'A.2'))]),'done');
    const value=normalized([part('A.2')],[id]);value.sheet.capture={scan_id:session,revision:7};
    const result=await prepareMonthlyExperimentVisuals(DB,1,problem,value);
    assert.deepEqual(result.images[0].part_ids,['A.2']);assert.ok(value.visualEvidence.has('A.2'));assert.ok(!value.visualEvidence.has('A.1'));
    assert.ok(value.graderAnswer.includes(photoMarker(id,'A.2')),'retained originals remain usable after session submission on an idempotent retry');
    await assert.rejects(prepareMonthlyExperimentVisuals(DB,2,problem,value),isError('bad_photo_ids',400));
    sql.prepare('UPDATE monthly_capture_pages SET parts=? WHERE photo_id=?').run(JSON.stringify([part('B.3')]),id);
    await assert.rejects(prepareMonthlyExperimentVisuals(DB,1,problem,value),isError('photo_unavailable',500));
  });
});

test('oversized visual batches fail explicitly rather than silently omitting relevant images',async()=>{
  await database(async({DB,insert,queries})=>{
    const ids=Array.from({length:21},(_,i)=>insert({id:uuid(i+1)}));
    await assert.rejects(prepareMonthlyExperimentVisuals(DB,1,problem,normalized([part('A.2')],ids)),isError('monthly_visuals_too_large',413));
    assert.ok(!queries.some(query=>query.startsWith('SELECT no,data')));
  });
  await database(async({DB,insert,queries})=>{
    const ids=Array.from({length:4},(_,i)=>insert({id:uuid(i+1),declaredBytes:4*1024*1024}));
    assert.ok(4*4*1024*1024>MONTHLY_EXPERIMENT_VISUAL_MAX_BYTES);
    await assert.rejects(prepareMonthlyExperimentVisuals(DB,1,problem,normalized([part('A.2')],ids)),isError('monthly_visuals_too_large',413));
    assert.ok(!queries.some(query=>query.startsWith('SELECT no,data')));
  });
});

test('corrupt chunk sequences, lengths and mismatched MIME types cannot become visual evidence',async()=>{
  await database(async({sql,DB,insert})=>{
    const missing=insert({id:uuid(1)}),wrongLength=insert({id:uuid(2),declaredBytes:png.length+1}),wrongType=insert({id:uuid(3),mime:'image/jpeg'});
    sql.prepare('DELETE FROM monthly_answer_photo_chunks WHERE photo_id=? AND no=1').run(missing);
    for(const id of [missing,wrongLength,wrongType])await assert.rejects(prepareMonthlyExperimentVisuals(DB,1,problem,normalized([part('A.2')],[id])),isError('photo_unavailable',500));
  });
});

test('retries and duplicate input IDs produce stable markers and do not change submission identity',async()=>{
  await database(async({DB,insert})=>{
    const first=insert({id:uuid(2)}),second=insert({id:uuid(1)}),value=normalized([part('A.2')],[first,second,first]);
    const original=value.serialized,one=await prepareMonthlyExperimentVisuals(DB,1,problem,value),text=value.graderAnswer;
    const two=await prepareMonthlyExperimentVisuals(DB,1,problem,value);
    assert.deepEqual(two,one);assert.equal(value.graderAnswer,text);assert.equal(value.serialized,original);
    assert.equal(value.visualEvidence.get('A.2').size,2);assert.equal(one.imageCount,2);
    assert.ok(one.images[0].label.includes(second),'source IDs are ordered deterministically');
  });
});
