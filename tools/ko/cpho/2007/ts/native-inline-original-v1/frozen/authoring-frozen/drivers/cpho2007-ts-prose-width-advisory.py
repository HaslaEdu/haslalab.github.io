"""Authoring-only length advisory from JSON and original font advances.

This does not read/render a PDF, edit a proof, or assert any delivery QA pass.
The real composer and its strict native/ink audits remain authoritative.
"""
from pathlib import Path
import sys,json,re
import pymupdf as f
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2007/TS');sys.path.insert(0,str(B/'engine'))
from cpho2007_ts_initial_native_baseline import translated_text
from izho_natural_spacing import boundary_gap
D=B.parents[1];PD=Path('D:/CodexBuilds/Hasla-publish-20261031')
faces={'en':{'serif':D/'english-face-repair/font-faces/SimSun-5.24.ttf','sans':D/'official-hans-fonts/faces/simhei.ttf'},'ko':{'serif':PD/'tools/ko/fonts/NotoSerifCJKkr-Regular.otf','sans':PD/'tools/ko/fonts/NotoSansCJKkr-Regular.otf'}}
metrics={lang:{fam:f.Font(fontfile=str(path))for fam,path in fs.items()}for lang,fs in faces.items()}
atoms=json.loads((B/'authoring/complete-inline-expressions-evidence.json').read_text('utf8'));plans=json.loads((B/'inputs/original-all20-source-slots.json').read_text('utf8'))['pages'];result=[]
for n in range(5,20):
 plan=next(p for p in plans if p['source_page']==n);auth=json.loads((B/f'authoring/page{n:02}-bilingual-prose.json').read_text('utf8'))['prose']
 for lang in ['ko','en']:
  for row in plan['rows']:
   items=[];rowid=row['row'];y=row['baseline']
   slots=[s for s in plan['slots']if s['row']==rowid]
   if not any(not s.get('retain_native')for s in slots):continue
   if n==14 and rowid==14:continue
   for a in atoms:
    if a['page']!=n or a['row']!=rowid:continue
    # Captions sharing a narrative baseline have their own original anchor.
    if n==7 and rowid==10 and a['rect'][0]>303.12:continue
    gs=a['physical_glyphs'];paths=a['vector_rects'];x0=min([g['origin'][0]for g in gs]+[r[0]for r in paths]);x1=max([g['bbox'][2]for g in gs]+[r[2]+.24 for r in paths])
    items.append(dict(text=a['text'],kind='native',x0=x0,x1=x1,size=max(g['size']for g in gs),width=x1-x0))
   for s in slots:
    if s['source'].strip()in['图','表']and s.get('align')in['center','right']:continue
    text=translated_text(s,auth[s['id']][lang]);size=s['size'];metric=metrics[lang][s['family']]
    if not text:continue
    x=s['origin'][0]
    if not s.get('align')and not s.get('native_prefix')and s['source'].startswith(('（','）')):
     marker='('if s['source'].startswith('（')else')';x+=(size-metric.text_length(marker,fontsize=size))/2 if text.startswith(marker)else 2
    # Exact full-em Hangul advances; new non-Hangul glyphs retain the staging
    # Noto face. Every ordinary space is the compositor's quarter-em.
    width=sum(size/4 if c==' 'else size if lang=='ko'and'가'<=c<='힣'else metric.text_length(c,fontsize=size)for c in text.strip())
    items.append(dict(text=text,kind='korean',x0=x,x1=x+width,size=size,width=width,id=s['id']))
   items.sort(key=lambda t:t['x0'])
   if not items:continue
   right=508.;caps={5:(range(3,10),296.4),7:(range(3,11),303.12),12:(range(6,12),355.68)}
   if n in caps and rowid in caps[n][0]:right=caps[n][1]
   cursor=items[0]['x0']
   for i,t in enumerate(items):
    if i:cursor+=boundary_gap(items[i-1],t)
    cursor+=t['width']
   if cursor>right+.1 and not any(s.get('align')=='center'and s['size']>=12 for s in slots):
    result.append(dict(page=n,language=lang,row=rowid,baseline=y,overflow_pt=round(cursor-right,3),prose=[dict(id=t['id'],text=t['text'])for t in items if'id'in t],sequence=' / '.join(t['text']for t in items)))
path=B/'authoring/current-width-advisory-not-delivery-QA.json';path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
for r in result:print(r['page'],r['language'],r['row'],r['overflow_pt'],r['sequence'],flush=True)
