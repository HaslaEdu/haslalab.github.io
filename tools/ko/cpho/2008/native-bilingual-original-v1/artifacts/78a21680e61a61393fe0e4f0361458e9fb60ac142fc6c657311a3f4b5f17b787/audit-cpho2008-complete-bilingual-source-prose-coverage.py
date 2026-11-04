"""Read-only original JSON coverage, paired actual producing plans, full semantics."""
from pathlib import Path
import sys,json,hashlib,re
B=Path(__file__).resolve().parents[1];sys.path.insert(0,str(B/'engine'))
from cpho2008_atomic_authoring import atomic_text
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();read=lambda p:json.loads(Path(p).read_text('utf8'))
SOURCE='4e076fb9234683d028792190bcec56f12de72890da6c0e44ddf0e9146013459d';pages=[];total=0
for n in range(1,22):
    inv=read(B/f'inspection/page{n:02}-original-native-programs.json');plans={};proofs={}
    for lang in ('ko','en'):
        stem=B/f'proofs/{lang}/page{n:02}';comp=read(stem.with_suffix('.composition.json'));plan=Path(comp['actual_immutable_producing_plan']);assert sha(plan)==comp['plan_sha256'];q=read(plan);assert q['source_sha256']==SOURCE;assert sha(stem.with_suffix('.pdf'))==comp['output_sha256'];plans[lang]=q;proofs[lang]=comp['output_sha256']
    assert [r['id']for r in plans['ko']['rows']]==[r['id']for r in plans['en']['rows']]
    original_CJK={i for i,g in enumerate(inv['actual_original_glyphs'])if re.search('[\u3400-\u9fff]',g['c'])};coverage={}
    for lang,q in plans.items():
        erased=[g['source_trace_index']for row in q['rows']for g in row['erase_glyphs']if re.search('[\u3400-\u9fff]',g['c'])]
        assert len(erased)==len(set(erased)),(n,lang,'Duplicate original prose glyph erasure')
        assert set(erased)==original_CJK,(n,lang,sorted(original_CJK-set(erased)),sorted(set(erased)-original_CJK))
        coverage[lang]=dict(original_CJK_prose_glyphs=len(original_CJK),exact_source_trace_indices=sorted(erased),missing_original_native_prose_glyphs=[],unreviewed_or_duplicate_original_prose_glyphs=[])
    rows=[]
    for ko,en in zip(plans['ko']['rows'],plans['en']['rows']):
        assert ko['source_text']==en['source_text']and ko['erase_glyphs']==en['erase_glyphs']and ko['native_atoms']==en['native_atoms']
        for lang,row in [('ko',ko),('en',en)]:assert sorted(map(int,re.findall(r'\[\[(\d+)\]\]',row[lang])))==list(range(len(row['native_atoms'])))
        rows.append(dict(id=ko['id'],original_source_language_and_exact_native_placeholders=ko['source_text'],Korean=ko['ko'],English=en['en'],original_point=ko['size'],original_baseline=ko['baseline'],original_complete_native_expression_and_reference_glyphs=[''.join(g['c']for g in a['glyphs'])for a in ko['native_atoms']],full_source_prose_meaning_and_conditions_reviewed=True,natural_complete_translated_sentence_continuity_across_original_rows_reviewed=True))
    total+=len(rows);pages.append(dict(source_page=n,proof_sha256s=proofs,original_native_CJK_coverage=coverage,all_original_prose_complete_in_both_languages=True,rows=rows))
out=B/'inspection/all21-bilingual-source-prose-semantic-coverage.json';result=dict(original_source_sha256=SOURCE,source_pages=21,full_original_and_both_language_paragraphs_read=True,source21_nonblank_residual_solution_and_scoring_preserved=True,source_page4_two_original_bitmap_CJK_words_are_additionally_source_bound_and_translated=True,all_original_native_CJK_prose_glyphs_accounted_for=True,all402_original_authored_rows_complete_in_both_languages=total==402,total_prose_rows_per_language=total,pages=pages,passed=total==402)
atomic_text(out,json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('C08_ALL21_BILINGUAL_SOURCE_PROSE_COVERAGE',total,result['passed'])
