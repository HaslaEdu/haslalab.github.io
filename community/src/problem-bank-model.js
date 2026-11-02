// Initial estimates are deliberately separate from reviewed ratings and outcomes.
// Source/statement identities stay in the canonical ingestion tables.
export const BANK_METHOD='rubric-v1';
export const BANK_SUBJECTS=['classical_mechanics','electromagnetism','thermodynamics','optics','quantum_mechanics','relativity','special_relativity','general_relativity','statistical_mechanics','oscillations_waves','mathematical_methods','astronomy_astrophysics','mixed'];
export const BANK_REGISTRY_SCHEMA=`
CREATE TABLE IF NOT EXISTS bank_source_presentations(
 source_id TEXT PRIMARY KEY,title_en TEXT NOT NULL,title_ko TEXT NOT NULL,display_title TEXT NOT NULL,
 primary_author TEXT NOT NULL DEFAULT '',credit_role TEXT NOT NULL DEFAULT '',edition_label TEXT,
 collection TEXT NOT NULL CHECK(collection IN ('physics','astronomy')),source_sha256 TEXT NOT NULL,
 proof_json TEXT NOT NULL CHECK(json_valid(proof_json)),updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS bank_asset_display_policy(
 asset_id TEXT PRIMARY KEY,question_id TEXT NOT NULL,sha256 TEXT NOT NULL,
 placement TEXT NOT NULL CHECK(placement IN ('inline','reference','blocked')),
 review_status TEXT NOT NULL,proof_json TEXT NOT NULL CHECK(json_valid(proof_json)),updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS bank_asset_display_question ON bank_asset_display_policy(question_id);
CREATE TABLE IF NOT EXISTS bank_figure_variants(
 id TEXT PRIMARY KEY,question_id TEXT NOT NULL,source_id TEXT NOT NULL,source_sha256 TEXT NOT NULL,
 parent_asset_id TEXT NOT NULL,parent_asset_sha256 TEXT NOT NULL,spans_json TEXT NOT NULL CHECK(json_valid(spans_json)),
 object_key TEXT NOT NULL,mime_type TEXT NOT NULL CHECK(mime_type IN ('image/png','image/svg+xml')),
 sha256 TEXT NOT NULL,byte_length INTEGER NOT NULL,width INTEGER NOT NULL,height INTEGER NOT NULL,
 verified_givens_only INTEGER NOT NULL CHECK(verified_givens_only=1),
 proof_json TEXT NOT NULL CHECK(json_valid(proof_json)),updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS bank_figure_variant_question ON bank_figure_variants(question_id);
CREATE TABLE IF NOT EXISTS bank_question_feedback(
 question_id TEXT NOT NULL,user_id INTEGER NOT NULL,stars INTEGER NOT NULL CHECK(stars BETWEEN 1 AND 5),
 outcome TEXT NOT NULL CHECK(outcome IN ('not_attempted','solved','partial','unsolved')),
 minutes INTEGER CHECK(minutes BETWEEN 1 AND 1440),evidence TEXT NOT NULL CHECK(evidence='self_report'),
 updated_at TEXT NOT NULL,PRIMARY KEY(question_id,user_id));
CREATE TABLE IF NOT EXISTS bank_feedback_limits(
 user_id INTEGER NOT NULL,day TEXT NOT NULL,n INTEGER NOT NULL,PRIMARY KEY(user_id,day));
CREATE TABLE IF NOT EXISTS bank_difficulty_reviews(
 question_id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,stars INTEGER NOT NULL CHECK(stars BETWEEN 1 AND 5),
 rubric_json TEXT NOT NULL CHECK(json_valid(rubric_json)),basis_text_sha256 TEXT NOT NULL,
 method_version TEXT NOT NULL,updated_at TEXT NOT NULL);
`;
export const BANK_FACETS_SCHEMA=`
CREATE TABLE IF NOT EXISTS bank_question_facets(
 question_id TEXT PRIMARY KEY,source_id TEXT NOT NULL,collection TEXT NOT NULL CHECK(collection IN ('physics','astronomy')),
 subjects_json TEXT NOT NULL CHECK(json_valid(subjects_json)),stars INTEGER NOT NULL CHECK(stars BETWEEN 1 AND 5),
 difficulty_status TEXT NOT NULL CHECK(difficulty_status IN ('provisional','reviewed','community_calibrated')),
 confidence TEXT NOT NULL CHECK(confidence IN ('low','medium','high')),reason_codes_json TEXT NOT NULL CHECK(json_valid(reason_codes_json)),
 rubric_json TEXT NOT NULL CHECK(json_valid(rubric_json)),basis_text_sha256 TEXT NOT NULL,method_version TEXT NOT NULL,
 classification_proof_json TEXT NOT NULL CHECK(json_valid(classification_proof_json)),updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS bank_facets_filters ON bank_question_facets(collection,stars,question_id);
`;

export function starsFromRubric(rubric){
  if(!rubric||Object.keys(rubric).sort().join(',')!=='integration,mathematics,prerequisites,reasoning')throw Error('invalid_rubric');
  for(const v of Object.values(rubric))if(typeof v!=='number'||!Number.isFinite(v)||v<0||v>4)throw Error('invalid_rubric');
  const score=.3*rubric.prerequisites+.2*rubric.integration+.2*rubric.mathematics+.3*rubric.reasoning;
  return {stars:1+[.65,1.35,2.1,2.85].filter(cut=>score>=cut).length,score:Number(score.toFixed(3))};
}

const ADVANCED=/green'?s? function|spherical harmonics?|bessel|legendre|sturm.?liouville|hamilton.?jacobi|tensor|christoffel|riemann|schwarzschild|geodesic|dirac equation|renormal|path integral|wkb|degenerate perturbation/i;
const ODE=/differential equation|laplace'?s? equation|poisson'?s? equation|schr[oö]dinger|wave equation|fourier|normal modes?|eigenvalue|eigenfunction/i;
const ALGEBRA=/matrix|matrices|eigenvector|determinant|commutator|operator|hilbert/i;
const CALCULUS=/integr(?:al|at)|derivativ|gradient|divergence|curl|\\(?:int|partial|nabla)\b/i;
const APPROX=/approximation|perturb|asymptot|lineariz|linearisation|small.oscillation|leading.order|limit of|limiting case/i;
const REASONING=/self.consistent|stability|stationary action|variational|optimi[sz]|extrem|prove.*(?:unique|necessary|sufficient)|inverse problem|reconstruct|without assuming/i;
const GROUPS=[/force|momentum|newton|lagrang|hamilton/i,/electri|magnetic|charge|current|gauss/i,/heat|entropy|temperature|thermodynamic/i,/quantum|wavefunction|schr[oö]dinger|pauli/i,/\brays?\b|refract|diffraction|interference|optic/i,/lorentz|relativ|spacetime|four.vector/i,/\bstars?\b|stellar|galax|luminosity|cosmolog|astronom/i];

export function estimateDifficulty({text='',chapter='',level='mixed',subjects=[],unresolved_source=false}){
  // Length, printed problem number, OCR quality and language are not difficulty.
  const prompt=String(chapter)+'\n'+String(text),reasons=['source_level'];
  let prerequisite={high_school:.1,olympiad:.8,undergraduate:.8,graduate:1.5,mixed:.8}[level]??.8;
  let mathematics=.2;
  if(CALCULUS.test(prompt)){mathematics=1.2;prerequisite=Math.max(prerequisite,1.5);reasons.push('calculus');}
  if(ALGEBRA.test(prompt)){mathematics=Math.max(mathematics,2);prerequisite=Math.max(prerequisite,2);reasons.push('linear_algebra');}
  if(ODE.test(prompt)){mathematics=Math.max(mathematics,2.8);prerequisite=Math.max(prerequisite,2.3);reasons.push('differential_equations');}
  if(ADVANCED.test(prompt)){mathematics=4;prerequisite=Math.max(prerequisite,3.6);reasons.push('advanced_mathematics');}
  const groups=GROUPS.filter(re=>re.test(prompt)).length;
  // Coarse source tags and overlapping SR/GR labels are not independent concepts.
  const integration=Math.min(3,Math.max(0,groups-1));
  if(integration>0)reasons.push('concept_integration');
  let reasoning=level==='high_school'?.2:level==='olympiad'?.8:level==='graduate'?1:.5;
  if(APPROX.test(prompt)){reasoning+=.8;reasons.push('approximation');}
  if(REASONING.test(prompt)){reasoning+=1.4;reasons.push('nontrivial_reasoning');}
  if(ADVANCED.test(prompt))reasoning+=.9;
  if(unresolved_source)reasons.push('reference_context_pending');
  const rubric={prerequisites:prerequisite,integration,mathematics,reasoning:Math.min(4,reasoning)};
  return {...starsFromRubric(rubric),status:'provisional',confidence:'low',reason_codes:[...new Set(reasons)],rubric,method_version:BANK_METHOD};
}

export function difficultyInfo(row){
  if(!row||!Number.isInteger(row.stars)||row.stars<1||row.stars>5)return null;
  let reasons=[];try{reasons=JSON.parse(row.reason_codes_json||'[]');}catch{}
  const allowed=new Set(['source_level','calculus','linear_algebra','differential_equations','advanced_mathematics','approximation','concept_integration','nontrivial_reasoning','reference_context_pending']);
  return {stars:row.stars,status:['provisional','reviewed','community_calibrated'].includes(row.difficulty_status)?row.difficulty_status:'provisional',confidence:['low','medium','high'].includes(row.confidence)?row.confidence:'low',reason_codes:reasons.filter(x=>allowed.has(x)),method_version:BANK_METHOD};
}

export function solveProbability(ability,difficulty){
  if(!Number.isFinite(ability)||!Number.isFinite(difficulty))throw Error('invalid_rating');
  return 1/(1+Math.exp(Math.max(-30,Math.min(30,difficulty-ability))));
}
export function eloUpdate({ability,difficulty,correct,evidence,studentCount=0,itemCount=0}){
  if(evidence!=='verified_grade')throw Error('verified_grade_required');
  if(![0,1].includes(correct)||![studentCount,itemCount].every(x=>Number.isSafeInteger(x)&&x>=0))throw Error('invalid_outcome');
  const expected=solveProbability(ability,difficulty),error=correct-expected;
  return {ability:ability+.3/Math.sqrt(1+studentCount/20)*error,difficulty:difficulty-.15/Math.sqrt(1+itemCount/30)*error,expected};
}

export function recommendProblems(items,{targetStars=3,limit=12,seen=[],preferredSubjects=[],previousSource=null}={}){
  if(!Number.isInteger(targetStars)||targetStars<1||targetStars>5||!Number.isInteger(limit)||limit<1||limit>30)throw Error('invalid_recommendation_options');
  const skipped=new Set(seen),preferred=new Set(preferredSubjects),bySource=new Map(),bodyHashes=new Set();
  const ranked=items.filter(x=>x&&typeof x.id==='string'&&!skipped.has(x.id)&&Number.isInteger(x.stars)&&x.stars>=1&&x.stars<=5).map(item=>{
    const p=solveProbability(targetStars-3,(item.stars-3)*.9),affinity=(item.subjects||[]).some(s=>preferred.has(s));
    const score=2*(1-Math.abs(p-.65))+(affinity?.45:0)+(item.source_id!==previousSource?.1:0)+(item.difficulty?.status==='reviewed'?.1:0);
    return {...item,recommendation_score:Number(score.toFixed(6)),recommendation_reason:affinity?'preferred_subject_and_target_difficulty':'target_difficulty_and_diversity'};
  }).sort((a,b)=>b.recommendation_score-a.recommendation_score||a.id.localeCompare(b.id));
  const result=[];
  for(const item of ranked){const work=item.source_title?.trim().toLowerCase()||item.source_id;if((bySource.get(work)||0)>=3||item.text_sha256&&bodyHashes.has(item.text_sha256))continue;result.push(item);bySource.set(work,(bySource.get(work)||0)+1);if(item.text_sha256)bodyHashes.add(item.text_sha256);if(result.length>=limit)break;}
  // Fewer eligible questions is preferable to repeating a source or exact copy.
  return result;
}
