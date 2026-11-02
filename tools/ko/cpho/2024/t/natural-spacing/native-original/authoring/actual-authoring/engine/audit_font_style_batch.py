from pathlib import Path
import sys,subprocess,time,json,os
B=Path(__file__).resolve().parents[1];status=[]
for n in range(1,6):
 for lang in ['KO','EN']:
  log=B/f'T/body-qa/page{n:02}-{lang}.font-style.log'
  with log.open('w',encoding='utf8')as out:r=subprocess.run([sys.executable,str(B/'engine/cpho2024_font_style_qa.py'),str(n),lang],stdout=out,stderr=subprocess.STDOUT,env=dict(os.environ))
  row=dict(page=n,language=lang,returncode=r.returncode);status.append(row);(B/'T/body-qa/font-style-status.json').write_text(json.dumps(status,indent=1)+'\n','utf8');print(row,flush=True);time.sleep(.6)
