from pathlib import Path
import json,hashlib
BASE=Path(__file__).resolve().parent
p=BASE/'source-format-and-review-status.json';q=json.loads(p.read_text('utf8'))
q['source_pages_visually_read']=list(range(1,61));q['output_hold']=False
q['final_output_dir']='D:/CodexBuilds/Hasla-poi-natural-20261102/proofs/icho/2019-final'
q['minimum_output_cache_and_metadata_free_bytes']=256*1024*1024
q['source_visual_review_tail']=[
dict(pages=[53,54],notes='NMR graph native numeric/letter axes; chair framework and carbon a remain original. Question 5 source has three separately underlined verbs. Synthesis route 1 through 9/2 and native reagent abbreviations remain chemical notation; independent enantiomer/epimer/diastereomer/atropisomer checkbox rows are prose.'),
dict(pages=[55,56],notes='Separate answer-grid chemical labels and both native column positions remain fixed. Question 8 native 4/5 must receive Korean particles in actual reading order. Native 5→6 and 6-prime remain math. Question 14 source says same stoichiometric equivalents and unchanged stereoselectivity: preserve both clauses. Source native arrow choices 1→4 through 9→2 remain original.'),
dict(pages=[57,58],notes='T9 grading grid fixed. Native R/S and priority structures/cells untouched. Translate relative-configuration and L-amino-acid checkbox prose fully. Levobupivacaine route includes vector/Form English prose annotations and independent reagent-structure captions: selective reviewed prose suppression only, chemical programs unchanged. Question 5 enantioselective/enantiospecific/regioselective three choices remain distinct.'),
dict(pages=[59,60],notes='B-F formula labels and answer-grid columns fixed; DCC/TsCl native abbreviations receive natural Korean predicates. Question 9 two reagent checkbox columns stay independent. Part II explicitly derivatizes alpha-amino group only, original (S)-Mosher chemical drawing/formula retained; distinguish diastereomer/enantiomer counts in all four choices. Methods NMR/liquid chromatography/mass spectroscopy/UV-vis remain four complete translated choices.')]
q['reviewed_source_panels']=[dict(path=str((BASE/'source-review'/f'panel{i:02}.png').resolve()),sha256=hashlib.sha256((BASE/'source-review'/f'panel{i:02}.png').read_bytes()).hexdigest())for i in range(1,31)]
p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
print('Original source all60 pages visually read; official theory/blank-answer scope retained, no solutions.')
