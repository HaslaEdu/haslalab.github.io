import revised from '../weekly/2026-11-astronomy-revision.json' with {type:'json'};

export const ASTRONOMY_REVISION_ID='monthly-2026-11-astronomy-quantitative-v1';
export const ASTRONOMY_REVISION_CONTENT=revised;
const problem=revised.problems[0];
const ready=new WeakMap();

// A new editorial revision updates the already-published problem exactly once.
// Submitted answers, old rubric IDs, images, attempts and frozen results remain intact.
async function applyRevision(db){
  await db.prepare(`CREATE TABLE IF NOT EXISTS weekly_publications (
    id TEXT PRIMARY KEY,problems INTEGER NOT NULL,created_at INTEGER NOT NULL
  )`).run();
  if(await db.prepare('SELECT id FROM weekly_publications WHERE id=?').bind(ASTRONOMY_REVISION_ID).first())return{ready:true,applied:false,changed:0};
  const target=await db.prepare(`SELECT id FROM problems WHERE week=? AND no=? AND kind='essay'
    AND (source=? OR title_ko=? OR title_en=?)`).bind(problem.week,problem.no,problem.source,problem.title_ko,problem.title_en).first();
  if(!target)return{ready:false,applied:false,changed:0};
  const result=await db.batch([
    db.prepare(`UPDATE problems SET subject=?,body_ko=?,body_en=?,model_ko=?,model_en=?,rubric=?
      WHERE id=? AND week=? AND no=? AND (source=? OR title_ko=? OR title_en=?)
      AND NOT EXISTS(SELECT 1 FROM weekly_publications WHERE id=?)`)
      .bind(problem.subject,problem.body_ko,problem.body_en,problem.model_ko,problem.model_en,JSON.stringify(problem.rubric),
        target.id,problem.week,problem.no,problem.source,problem.title_ko,problem.title_en,ASTRONOMY_REVISION_ID),
    db.prepare(`INSERT INTO weekly_publications(id,problems,created_at)
      SELECT ?,1,? WHERE EXISTS(SELECT 1 FROM problems WHERE id=? AND subject=? AND body_ko=?)
      AND NOT EXISTS(SELECT 1 FROM weekly_publications WHERE id=?) ON CONFLICT(id) DO NOTHING`)
      .bind(ASTRONOMY_REVISION_ID,Math.floor(Date.now()/1000),target.id,problem.subject,problem.body_ko,ASTRONOMY_REVISION_ID),
  ]);
  const applied=!!result[1].meta?.changes;
  return{ready:applied||!!await db.prepare('SELECT id FROM weekly_publications WHERE id=?').bind(ASTRONOMY_REVISION_ID).first(),applied,changed:Number(result[0].meta?.changes||0)};
}

export function ensureAstronomyRevision(db,key=db){
  let promise=ready.get(key);
  if(!promise){
    promise=applyRevision(db).then(result=>{if(!result.ready&&ready.get(key)===promise)ready.delete(key);return result;});
    ready.set(key,promise);
    promise.catch(()=>{if(ready.get(key)===promise)ready.delete(key);});
  }
  return promise;
}
