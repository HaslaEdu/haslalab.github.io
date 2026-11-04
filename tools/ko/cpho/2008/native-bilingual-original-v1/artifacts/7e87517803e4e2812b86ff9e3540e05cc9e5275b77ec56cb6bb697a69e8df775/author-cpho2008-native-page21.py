import sys as _atomic_sys
from pathlib import Path as _AtomicPath
_atomic_sys.path.insert(0,str(_AtomicPath(__file__).resolve().parents[1]/'engine'))
from cpho2008_atomic_authoring import atomic_text
"""Literal existing nonblank source tail; no invented missing statement/title."""
from pathlib import Path
import json,re
B=Path(__file__).resolve().parents[1];A=B/'authoring';q=json.loads((A/'page21-native-row-proposals.json').read_text('utf8'))
T=[('두 식을 연립하면 다음을 얻는다.','Combining the two equations gives'),('채점 기준: 광선 경로도를 정확히 그리면 [[0]]점, 식 [[1]]에 [[2]]점.','Scoring: correct ray diagram, [[0]] points; equation [[1]], [[2]] points.')]
assert len(T)==len(q['rows'])==2
for r,(ko,en)in zip(q['rows'],T):
 r.update(ko=ko,en=en,reviewed=True,align='left',allowed_horizontal=[89,506])
 for a in r['native_atoms']:
  assert not a['proposed_vector_paths'];a.update(vector_paths=[],reviewed=True,source_review_reason='Complete original grading numeral/reference only. All actual original optical formulas2/3, fractional physical points, fraction rules, clips and folio21 remain stationary, native and literal.')
 for lang in('ko','en'):assert sorted(map(int,re.findall(r'\[\[(\d+)\]\]',r[lang])))==list(range(len(r['native_atoms']))),(r['id'],lang)
q.update(source_only_proposal=False,all_source_language_and_native_expressions_manually_reviewed=True,literal_original_nonblank_residual_source_page_preserved=True,no_missing_statement_or_editorial_heading_invented=True,publication_ready=False)
atomic_text(A/'page21-native-language.json', json.dumps(q,ensure_ascii=False,indent=2)+'\n', 'utf8');print('C08_PAGE21_LITERAL_SOURCE_TAIL_AUTHORED',len(T))
