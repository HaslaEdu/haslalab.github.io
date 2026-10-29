"""Validate the GPhO Korean solution publication set, including region coverage."""
import hashlib
import json
import pathlib
import re
import sys
import pymupdf as fitz
import gpho_ko_layout as build

def validate():
    report = {'competition':'gpho', 'years':{}, 'files':[], 'untranslated':[]}
    overlay = json.loads((build.ROOT/'tools/gpho_ko_additions.json').read_text(encoding='utf8'))['gpho']
    for year, spans in build.PARTS.items():
        source = fitz.open(build.SOURCE/f'GPhO_{year}_TS.pdf')
        regions = build.groups(source)
        mapping = json.loads((build.DATA/f'{year}.json').read_text(encoding='utf8'))
        missing = [r['id'] for r in regions if r['id'] not in mapping and build.automatic(r['text']) is None]
        assert not missing, (year, missing)
        report['years'][str(year)] = {'regions':len(regions),
            'source_sha256':hashlib.sha256((build.SOURCE/f'GPhO_{year}_TS.pdf').read_bytes()).hexdigest(),
            'source_url':f'https://github.com/HaslaEdu/haslalab.github.io/releases/download/pdf-gpho/GPhO_{year}_TS.pdf',
            'solution_pages':sum(b-a+1 for a,b in spans)}
        # Ensure no formula/prose block from a neighbouring column is swallowed.
        for r in regions:
            if r['rect'][2]-r['rect'][0] > 300 and int(r['id'].split('.')[0]) > 1:
                assert isinstance(mapping.get(r['id']),dict), (year,r['id'],'wide prose region')
        for part, (start,end) in enumerate(spans,1):
            name = overlay[str(year)][f'T{part}']['sol']
            path = build.OUT/name
            with fitz.open(path) as doc:
                assert len(doc)==end-start+1, (name,'page count')
                text=''.join(p.get_text() for p in doc)
                assert len(re.findall('[가-힣]',text)) > 300, (name,'missing Korean text')
                for p in doc:
                    assert abs(p.rect.width-source[0].rect.width)<.1 and abs(p.rect.height-source[0].rect.height)<.1
                    assert not p.search_for('pts'), (name,'untranslated score label')
                annotations = sum(len(list(p.annots() or [])) for p in doc)
                report['files'].append({'file':name,'pages':len(doc),'bytes':path.stat().st_size,
                    'sha256':hashlib.sha256(path.read_bytes()).hexdigest(), 'translation_notes':annotations})
    assert len(report['files'])==12
    assert sum(f['pages'] for f in report['files'])==29
    target=build.SOURCE/'validation.json'
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'files':12,'pages':29,'regions':sum(y['regions'] for y in report['years'].values()),
                      'translation_notes':sum(f['translation_notes'] for f in report['files']),
                      'report':str(target)},ensure_ascii=False))
    return report

if __name__=='__main__':
    validate()
