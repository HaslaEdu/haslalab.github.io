"""Font-table-only fixed-point authoring check; opens/renders no PDF."""
from pathlib import Path
import sys,json,re
from fontTools.ttLib import TTFont
B=Path(__file__).resolve().parents[1];sys.path.insert(0,str(B/'engine'));from cpho2008_native_compose import font_path
metrics={}
def textwidth(lang,face,text,point):
 key=(lang,face)
 if key not in metrics:
  f=TTFont(font_path(lang,face),fontNumber=0,recalcTimestamp=False);metrics[key]=(f.getBestCmap(),f['hmtx'].metrics,f['head'].unitsPerEm)
  f.close()
 cmap,adv,em=metrics[key];return sum(point/4 if c==' 'else adv[cmap[ord(c)]][0]/em*point for c in text)
for n in map(int,sys.argv[1:]):
 q=json.loads((B/f'authoring/page{n:02}-native-language.json').read_text('utf8'))
 for row in q['rows']:
  for lang in('ko','en'):
   total=0
   for part in re.split(r'(\[\[\d+\]\])',row[lang]):
    if not part:continue
    if part.startswith('[['):a=row['native_atoms'][int(part[2:-2])];total+=a['rect'][2]-a['rect'][0]
    else:total+=textwidth(lang,row['source_prose_face'],part,row['size'])
   x=row['original_center']-total/2 if row.get('align')=='center'else row['left'];lo,hi=row['allowed_horizontal']
   if x<lo-.001 or x+total>hi+.001:print('OVERFLOW',n,row['id'],lang,round(x,3),round(x+total,3),[lo,hi],row[lang])
 print('DONOR_FONT_TABLE_PREFLIGHT_FINISHED',n)
