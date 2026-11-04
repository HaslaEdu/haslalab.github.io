"""Non-delivery authoring advisory from original coordinates and real advances."""
from pathlib import Path
import sys,json
import pymupdf as f
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native');sys.path.insert(0,str(B/'engine'))
from cpho2003_initial_native_baseline import translated_text
from izho_natural_spacing import boundary_gap
D=Path('D:/CodexBuilds/Hasla-original-style-20261031');PD=Path('D:/CodexBuilds/Hasla-publish-20261031')
faces={'en':{'serif':D/'english-face-repair/font-faces/SimSun-5.24.ttf','sans':D/'official-hans-fonts/faces/simhei.ttf'},'ko':{'serif':PD/'tools/ko/fonts/NotoSerifCJKkr-Regular.otf','sans':PD/'tools/ko/fonts/NotoSansCJKkr-Regular.otf'}}
metrics={lang:{fam:f.Font(fontfile=str(path))for fam,path in fs.items()}for lang,fs in faces.items()}
atoms=json.loads((B/'authoring/native/complete-inline-expressions-evidence.json').read_text('utf8'));plans=json.loads((B/'inputs/original-all10-source-slots.json').read_text('utf8'))['pages'];results=[]
for n in [1,2,3]:
 plan=plans[n-1];auth={r['source_slot']:r['translations']for r in json.loads((B/f'authoring/native/page{n:02}-bilingual-prose.json').read_text('utf8'))['records']}
 for lang in ['ko','en']:
  for row in plan['rows']:
   items=[];ri=row['row'];slots=[s for s in plan['slots']if s['row']==ri]
   for a in atoms:
    if a['page']!=n or a['row']!=ri:continue
    gs=a['physical_glyphs'];x0=min(g['origin'][0]for g in gs);x1=max(g['bbox'][2]for g in gs)
    items.append(dict(text=a['text'],kind='native',x0=x0,x1=x1,size=max(g['size']for g in gs),width=x1-x0))
   for s in slots:
    text=translated_text(s,auth[s['id']][lang]);size=s['size'];metric=metrics[lang][s['family']]
    if not text:continue
    x=s['origin'][0];width=sum(size/4 if c==' 'else size if lang=='ko'and s['family']=='serif'and'가'<=c<='힣'else metric.text_length(c,fontsize=size)for c in text.strip())
    items.append(dict(text=text,kind='korean',x0=x,x1=x+width,size=size,width=width,id=s['id']))
   items.sort(key=lambda t:t['x0'])
   if not items:continue
   right=413.85 if n==2 and ri<=5 else 524.3
   if any(s['size']>=14 for s in slots):continue
   cursor=items[0]['x0']
   for i,t in enumerate(items):
    if i:cursor+=boundary_gap(items[i-1],t)
    cursor+=t['width']
   if cursor>right+.1:results.append(dict(page=n,language=lang,row=ri,overflow_pt=round(cursor-right,3),sequence=' / '.join(t['text']for t in items)))
p=B/'authoring/native/current-width-advisory-not-delivery-QA.json';p.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n','utf8')
for r in results:print(r['page'],r['language'],r['row'],r['overflow_pt'],r['sequence'],flush=True)
