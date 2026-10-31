"""Rebuild reviewed 2010--2017 Korean IZhO PDFs, including the missing 2010 T3.

The English 2010 solution is only seven pages.  Its official Russian companion
contains T3 on pages 7--11.  Rebuild that translated appendix independently, then
append it to the seven translated English-source pages without rescaling either.
"""
from pathlib import Path
import argparse,hashlib,json,urllib.request
import pymupdf as fitz
from izho_translate import ROOT,build
from izho_early_layout import prepare

def ensure_source(folder):
    raw=folder/'translation.raw.json'
    data=json.loads((raw if raw.exists() else folder/'translation.json').read_text(encoding='utf8'))
    source=ROOT/data['source']
    if not source.exists() and data.get('provenance',{}).get('source_url'):
        url=data['provenance']['source_url']
        request=urllib.request.Request(url,headers={'User-Agent':'HaslaLab verified IZhO rebuild'})
        payload=urllib.request.urlopen(request,timeout=120).read()
        if not payload.startswith(b'%PDF-') or hashlib.sha256(payload).hexdigest()!=data['source_sha256']:
            raise ValueError('Official source differs from reviewed original: '+url)
        source.parent.mkdir(parents=True,exist_ok=True);source.write_bytes(payload)

def rebuild(years,keep_going=False,kinds=None):
    output=ROOT/'pdfx/izho';output.mkdir(parents=True,exist_ok=True)
    staging=ROOT/'tmp/izho-early/build';staging.mkdir(parents=True,exist_ok=True)
    report=[];failures=[]
    for year in years:
        for kind in kinds or ['T','TS']:
            folder=ROOT/f'tools/ko/izho/{year}/{kind}'
            final=output/f'IZhO_{year}_{kind}_KO.pdf'
            target=staging/'IZhO_2010_T12_KO.pdf' if (year,kind)==(2010,'TS') else final
            try:
                ensure_source(folder);prepare(year,kind);build(folder,target)
                parts=[str(target.relative_to(ROOT))]
                if (year,kind)==(2010,'TS'):
                    appendix_folder=ROOT/'tools/ko/izho/2010/T3S'
                    ensure_source(appendix_folder);prepare(2010,'T3S')
                    appendix=output/'IZhO_2010_T3_S_KO.pdf';build(appendix_folder,appendix)
                    combined=fitz.open(target);extra=fitz.open(appendix);first=len(combined)
                    combined.insert_pdf(extra)
                    combined.set_toc([[1,'문제 1–2 해설 — 영문 원본 번역',1],
                                      [1,'문제 3 해설 — 공식 러시아어판에서 보완',first+1]])
                    combined.set_metadata({'title':'IZhO 2010 이론시험 전체 해설 — 한국어',
                                           'subject':'English-source T1/T2 + official Russian-source T3',
                                           'author':'HaslaLab'})
                    temporary=staging/'IZhO_2010_TS_complete.pdf'
                    combined.save(temporary,garbage=4,deflate=True);combined.close();extra.close()
                    temporary.replace(final);parts.append(str(appendix.relative_to(ROOT)))
                doc=fitz.open(final)
                item={'year':year,'kind':kind,'file':str(final.relative_to(ROOT)),
                      'pages':len(doc),'bytes':final.stat().st_size,
                      'sha256':hashlib.sha256(final.read_bytes()).hexdigest(),
                      'components':parts}
                doc.close();report.append(item);print('READY',json.dumps(item,ensure_ascii=False),flush=True)
            except Exception as exc:
                failures.append({'year':year,'kind':kind,'error':str(exc)})
                print('FAILED',year,kind,str(exc),flush=True)
                if not keep_going:raise
    path=ROOT/'tools/izho_early_build_report.json'
    prior=json.loads(path.read_text(encoding='utf8')) if path.exists() else {'files':[]}
    selected={(r['year'],r['kind']) for r in report}
    report=[r for r in prior['files'] if (r['year'],r['kind']) not in selected]+report
    path.write_text(json.dumps({'files':sorted(report,key=lambda r:(r['year'],r['kind'])),
                               'failures':failures},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    if failures:raise SystemExit(1)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('years',type=int,nargs='+')
    parser.add_argument('--keep-going',action='store_true')
    parser.add_argument('--kind',choices=['T','TS'],help='Rebuild one published document kind; default is both.')
    args=parser.parse_args();rebuild(args.years,args.keep_going,[args.kind] if args.kind else None)
