"""Inventory canonical statement assets without promoting figures or reading solutions.

This reads only current extractor roots, never correction-history or solution-bank
assets. IDs mirror prepare-extracted.py + store.mjs. Server readback is separate.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from private_paths import private_directory
from source_identity import source_key


def digest(value):
    return hashlib.sha256(value).hexdigest()


def inventory(root):
    root=Path(root)
    index=json.loads((root/'solution-bank/question-index.json').read_text(encoding='utf-8'))
    registered=json.loads((root/'solution-bank/source-index.json').read_text(encoding='utf-8'))['normalized_sources']
    sources={source_key(source):source for source in registered}
    def identity(reference,locator):
        source=sources[source_key(reference)]
        return source,'q_'+digest((source['id']+'\0'+locator).encode())
    canonical={}
    for question in index['questions']:
        source,qid=identity(question['source'],question['locator'])
        if qid in canonical:raise ValueError('Duplicate canonical question ID')
        canonical[qid]=(source,question)
    found=set();profiles=[];figures=[];unmapped=[]
    paths=sorted(set(root.glob('*/questions.raw.json'))|set(root.glob('*/questions-raw.json'))|
                 set(root.glob('university-bank/*/questions.raw.json')))
    total_raw=Counter();total_normalized=Counter();no_separated_figure=[]
    for path in paths:
        raw=json.loads(path.read_text(encoding='utf-8'));questions=raw.get('questions',[])
        counts=Counter();normalized=Counter();accepted=0;with_figures=0
        for question in questions:
            legacy='source' not in question
            if legacy:
                matches=[s for s in registered if s['sha256']==raw['source_sha256']]
                if len(matches)!=1:raise ValueError('Ambiguous legacy source PDF hash')
                source=matches[0];locator='problem-'+str(question['original_number'])
                qid='q_'+digest((source['id']+'\0'+locator).encode())
                assets=[{'role':'question_crop','sha256':s['image_sha256'],'local_path':str(path.parent/s['image'])}
                        for s in question['statement_segments']]
            else:
                source,qid=identity(question['source'],question['locator']);locator=question['locator'];assets=question.get('assets',[])
            if qid not in canonical:continue
            if qid in found:raise ValueError('Canonical question appears in multiple current raw profiles')
            found.add(qid);accepted+=1;has_figure=False
            for offset,asset in enumerate(assets,1):
                role=asset['role'];mapped='figure' if role in ('figure','source_figure') else 'question_crop' if role in ('question_crop','source_context','source_footnote') else None
                counts[role]+=1
                if mapped is None:unmapped.append({'question_id':qid,'role':role});continue
                normalized[mapped]+=1
                if mapped=='figure':
                    has_figure=True;asset_id='crop-'+str(offset)
                    figures.append({'question_id':qid,'source_id':source['id'],'source_sha256':source['sha256'],
                        'profile':path.parent.name,'locator':locator,'original_number':str(question['original_number']),
                        'expected_canonical_asset_id':'a_'+digest((qid+'\0'+asset_id).encode()),'asset_id':asset_id,
                        'raw_role':role,'expected_canonical_role':mapped,'sha256':asset['sha256'],
                        'mime_type':asset.get('mime_type'),'local_path':asset.get('local_path'),
                        'spans':asset.get('spans',[]),'figure_label':asset.get('figure_label'),
                        'quality_flags':asset.get('quality_flags',[]),'raw_path':str(path),
                        'canonical_server_readback_verified':False,'visual_boundary_review_this_audit':False,
                        'public_admission':'not_admitted_by_inventory'})
            with_figures+=has_figure
            if not has_figure:no_separated_figure.append({'question_id':qid,'profile':path.parent.name,'locator':locator})
        if accepted:
            total_raw.update(counts);total_normalized.update(normalized)
            profiles.append({'profile':path.parent.name,'raw_path':str(path),'raw_sha256':digest(path.read_bytes()),
                'canonical_questions':accepted,'raw_asset_roles':dict(counts),'expected_normalized_roles':dict(normalized),
                'questions_with_separated_figure_assets':with_figures,'questions_without_separated_figure_assets':accepted-with_figures})
    return {'schema':'haslalab.private.canonical-question-figure-inventory.v1','private':True,
        'canonical_question_count':len(canonical),'current_raw_questions_found':len(found),
        'missing_current_raw_question_ids':sorted(canonical.keys()-found),'raw_asset_roles':dict(total_raw),
        'expected_canonical_normalized_roles':dict(total_normalized),'questions_with_separated_figure_assets':len(found)-len(no_separated_figure),
        'questions_without_separated_figure_assets':len(no_separated_figure),'profiles':profiles,
        'separated_figure_candidates':figures,'unmapped_roles':unmapped,
        'no_figure_role_does_not_mean_no_diagram':True,'source_context_and_statement_crops_are_not_public_figures':True,
        'canonical_server_readback_verified':False,'all_figure_boundaries_visually_verified':False,
        'solution_assets_examined_or_admitted':0,'public_admission':'none; a separate verified figure registry is required'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--private-root',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    report=inventory(args.private_root);target=private_directory(args.out.parent)/args.out.name
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({key:report[key] for key in ['canonical_question_count','current_raw_questions_found','raw_asset_roles','expected_canonical_normalized_roles','questions_with_separated_figure_assets','questions_without_separated_figure_assets','missing_current_raw_question_ids','unmapped_roles']},ensure_ascii=False))
