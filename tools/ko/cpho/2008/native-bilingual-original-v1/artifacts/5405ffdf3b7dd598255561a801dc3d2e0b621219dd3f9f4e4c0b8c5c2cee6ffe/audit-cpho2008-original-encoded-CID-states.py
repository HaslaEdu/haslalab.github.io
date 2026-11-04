from pathlib import Path
import sys,json,hashlib
B=Path(__file__).resolve().parents[1];sys.path[:0]=[str(B/'engine'),'D:/CodexBuilds/Hasla-publish-20261031/tools']
from pdf_memory_gate import page_worker
from pdf_native_inline_reposition import inspect_inline_groups
from cpho2008_original_CID_states import audit
n=int(sys.argv[1]);lang=sys.argv[2];S=B/'source/CPhO_2008_original_combined_ZH.pdf';P=B/f'proofs/{lang}/page{n:02}.pdf';c=json.loads(P.with_suffix('.composition.json').read_text('utf8'));source=json.loads((B/f'inspection/page{n:02}-original-native-programs.json').read_text('utf8'))
with page_worker():
 actual=inspect_inline_groups(P,1,include_text_shows=True);result=audit(S,n,P,source,actual,c['erased_original_language_glyphs'])
 out=P.with_suffix('.original-encoded-CID-states.json')
 if out.exists():
  H=B/'history/previous-encoded-CID-audits';H.mkdir(parents=True,exist_ok=True);(H/f'{n:02}-{lang}-{hashlib.sha256(out.read_bytes()).hexdigest()}.json').write_bytes(out.read_bytes())
 out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8');print('C08_ORIGINAL_ENCODED_CID_TF_FULL_TM_FONT_GID_POINT_CLIP_PROGRAM',n,lang,'pass',result['passed'],'CIDs',result['actual_original_encoded_CIDs_checked'],'errors',len(result['errors']),flush=True)
