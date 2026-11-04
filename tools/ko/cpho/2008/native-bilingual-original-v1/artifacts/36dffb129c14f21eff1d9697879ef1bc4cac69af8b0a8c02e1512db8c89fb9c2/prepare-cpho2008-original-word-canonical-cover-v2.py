"""Only source-word cover edges change; original measured typography stays fixed."""
from pathlib import Path
import sys,json,hashlib,math
B=Path(__file__).resolve().parents[1];sys.path.insert(0,str(B/'engine'))
from cpho2008_atomic_authoring import atomic_text
p=B/'authoring/page04-original-island-language-policy.json';raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()=='13aa68df7264cad0c962588756728b09ebcfe5fed820883024494120da1bf6e3';q=json.loads(raw)
for row,expected in zip(q['labels'],[[193.,398.25,229.75,408.],[378.,423.25,415.75,433.]]):
    prior=row['erase_rect_pt'];aligned=[math.floor((prior[0]+.00001)*4)/4,math.floor((prior[1]+.00001)*4)/4,math.ceil((prior[2]-.00001)*4)/4,math.ceil((prior[3]-.00001)*4)/4];assert aligned==expected
    row['raw_source_word_cover_before_canonical_pixel_alignment']=prior;row['erase_rect_pt']=aligned
q['source_only_cover_edge_alignment_pt']=.25;q['prior_source_only_policy_sha256']=hashlib.sha256(raw).hexdigest();q['cover_edge_alignment_changes_no_font_size_baseline_center_image_payload_CTM_math_or_nonlanguage_ink']=True
out=B/'authoring/page04-original-island-language-policy-canonical-cover-v2.json';assert not out.exists();atomic_text(out,json.dumps(q,ensure_ascii=False,indent=2)+'\n');print('C08_SOURCE_WORD_CANONICAL_COVER_V2',hashlib.sha256(out.read_bytes()).hexdigest())
