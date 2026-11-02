"""Manual source-component evidence: remove only empty bitmap padding overlap."""
from pathlib import Path
import json,shutil
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS');E=B/'math-union-contact-review';E.mkdir(exist_ok=True)
fixes={
 5:{'roots-original-reference13':{'eq13-root-a':dict(x0=96)}},
 7:{'tube-force-e':{'radius-local':dict(y0=478.5)}},
 8:{'above-critical-length':{'case-L-above':dict(y1=192.5),'eq19-down':dict(y0=181.5)},'marking-part3':{'part3-grade':dict(y0=353.75),'score4':dict(y0=354)}},
 10:{'marking-part2':{'part2-grade':dict(y0=360.5),'score2':dict(y0=360.5)},'marking-part2-detail':{'g14':dict(y0=373,y1=384),'p2-14':dict(y0=373)}},
 13:{'frame-origins':{'zero-both-times':dict(y0=446.5),'x-prime-axis':dict(y0=447)}},
 14:{'marking-part2-details':{'g6':dict(y0=352),'p1-36':dict(y0=352)}},
}
for n,rows in fixes.items():
 P=B/f'authoring/page{n:02d}-layout.json';snap=E/f'page{n:02d}-before-padding-revision.json'
 if not snap.exists():shutil.copyfile(P,snap)
 p=json.loads(snap.read_text('utf8'));found=[]
 for row in p['rows']:
  for atom in row['atoms']:
   patch=rows.get(row['id'],{}).get(atom['id'])
   if not patch:continue
   old=atom['rect'].copy()
   for key,value in patch.items():atom['rect'][['x0','y0','x1','y1'].index(key)]=value
   found.append(dict(row=row['id'],atom=atom['id'],old=old,new=atom['rect']))
   atom['reason']='Whole original mathematics manually checked using original-source 8x connected-component bounds and source/Multiply-union/Normal-control/final contacts. Remove only prior/next-line CJK or empty bitmap padding; every full mathematical digit, script, parenthesis, bar and original internal geometry is retained at 1x. No source image or formula is regenerated.'
  if n==5 and row['id']=='roots-original-reference13':
   row['ko']='식 '+row['ko'];row['ko']=row['ko'].replace('[[eq13-root-b]]의','식 [[eq13-root-b]]의')
 if len(found)!=sum(len(a)for a in rows.values()):raise ValueError(('Some reviewed atoms not found',n,found))
 p['independent_math_union_padding_revision']=dict(changes=found,reviewed=True,evidence='math-union-contact-review/components.json and per-page source/reference/control/final contacts; original-source component bounds: radius r480.25–485.75, eq19 parentheses183–192, L>L0 complete180.75–190.25, part3 numeral354.5–362, score4 numeral355–361.5, score2 numeral361.875–368.875, eq14 parentheses374.5–383.25, tprime/tzero448–455.625, xprime448.875–456.125.',method='Only explicit mathematical source clip padding narrowed where its opaque white paper covered another mathematical object. Mathematical encoded raster/scale/y and all within-formula relative geometry retained; independent union must show zero lost mathematical ink.')
 P.write_text(json.dumps(p,ensure_ascii=False,indent=2),'utf8');print(n,found)
