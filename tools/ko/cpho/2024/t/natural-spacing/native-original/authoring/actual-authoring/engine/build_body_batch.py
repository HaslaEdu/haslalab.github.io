from pathlib import Path
import json,os,time
from cpho2024_natural import BASE,build,preflight
from pdf_memory_gate import page_worker

if __name__=='__main__':
    print('PID',os.getpid(),flush=True)
    records=[]
    for number in range(1,6):
        for language in ['KO','EN']:
            # Fonts and line lengths are checked without holding the render
            # gate; each actual page is one independent memory-heavy unit.
            preflight(number,language)
            with page_worker():path,report=build(number,language)
            records.append(dict(page=number,language=language,path=str(path),sha256=report['output_sha256']))
            (BASE/'inspection/body-build-status.json').write_text(json.dumps(records,indent=1),'utf8')
            print(number,language,report['output_sha256'],flush=True);time.sleep(.6)
