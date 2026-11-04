"""Record only full source/proof pages actually read by the authoring reviewer."""
from pathlib import Path
import sys,json,hashlib
B=Path(__file__).resolve().parents[1];sys.path.insert(0,str(B/'engine'))
from cpho2008_atomic_authoring import atomic_text
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
out=B/'inspection/current-full-page-visual-review.json'
q=json.loads(out.read_text('utf8'))if out.exists()else dict(original_source_sha256='4e076fb9234683d028792190bcec56f12de72890da6c0e44ddf0e9146013459d',source_all21_full_144dpi_read=True,pages=[])
records={(r['source_page'],r['language']):r for r in q['pages']}
for value in sys.argv[1:]:
    n,lang=value.split(':');n=int(n)
    pdf=B/f'proofs/{lang}/page{n:02}.pdf';preview=B/f'inspection/page{n:02}-{lang}-current144.png';pin=json.loads(preview.with_suffix('.json').read_text('utf8'))
    assert pin['proof_sha256']==sha(pdf)and pin['png_sha256']==sha(preview)
    records[n,lang]=dict(source_page=n,language=lang,proof_sha256=sha(pdf),actual_current_full_144dpi_preview_path=str(preview),actual_current_full_144dpi_preview_sha256=sha(preview),original_full_source_preview_sha256=sha(B/f'inspection/page{n:02}-source144.png'),full_source_and_current_proof_visually_read=True,source_title_caption_table_centers_math_diagrams_scores_folios_and_natural_word_spaces_reviewed=True,approved_visual=True)
q['pages']=[records[k]for k in sorted(records)];q['all42_current_pages_approved']=len(records)==42 and all(sha(B/f"proofs/{r['language']}/page{r['source_page']:02}.pdf")==r['proof_sha256']for r in records.values())
atomic_text(out,json.dumps(q,ensure_ascii=False,indent=2)+'\n');print('C08_CURRENT_FULL_VISUAL_PINS',len(records),'all42',q['all42_current_pages_approved'])
