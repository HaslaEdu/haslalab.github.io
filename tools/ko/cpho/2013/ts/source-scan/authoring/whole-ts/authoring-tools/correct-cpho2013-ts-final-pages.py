from pathlib import Path
import json,hashlib,shutil
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS');archive=B/'root-paint-order-completion/preserved-final-page-drafts';archive.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source_sha='612d676f525ddc35ad3b417a8f25141d3467f48309d52dfdbcab7bd222201d68'
for n in[12,13]:
 p=B/f'authoring/page{n}-layout.json';backup=archive/p.name
 if not backup.exists():shutil.copy2(p,backup)
 for lang in['ko','en']:
  dest=archive/lang;dest.mkdir(exist_ok=True)
  for f in(B/'proofs'/lang).glob(f'page{n}*'):
   if not(dest/f.name).exists():shutil.copy2(f,dest/f.name)
 d=json.loads(p.read_text('utf8'));changes=[]
 rect_changes=({(292,85.5,325,100):[293.25,85.5,325,100],(75,493,201,565):[75,493,201,559.5],(116,590,173,608):[116,590,173,606]}if n==12 else{(171,400,339,432):[171,400,339,427.25],(180,483,241,499):[180,484.75,241,499],(180,577,250,594):[180,582,250,595.5]})
 for old,new in rect_changes.items():
  rects=d['protected_source_display_and_figure_rects']
  if list(old)in rects:rects[rects.index(list(old))]=new
  else:assert new in rects,(n,old)
  changes.append(dict(kind='source-display-scope',before=list(old),after=new,reason='Actual original math protected in full; adjacent translated Chinese / intentionally moving next-line inline numerator excluded after exact source contact review.'))
 for row in d['rows']:
  for a in row['atoms']:
   old=list(a['rect'])
   if n==12 and a['id']=='QQplus-expansion':a['rect'][2]=174.0
   if n==13 and a['id']=='screen-distance':a['rect'][2]=132.75
   if n==13 and a['id']=='slit-gap':a['rect'][2]=216.0
   if n==13 and a['id']in['tprime1-T','xprime1-zero']:a['rect'][1]=427.3
   if n==13 and row['id']=='event2-definition-a':a['rect'][1]=596.0
   if n==13 and a['id']=='event1-other':a['rect']=[442.5,598.0,448.5,608.5]
   if a['rect']!=old:changes.append(dict(kind='complete-source-inline-atom',id=a['id'],before=old,after=a['rect'],reason='Complete original shape/prime at1x; source punctuation/CJK and opaque padding outside the notation excluded by reviewed source contact sheet.'))
  if n==13 and row['id']=='event2-definition-a':
   for r in row['erase_rects']:r[1]=596.0
 rect,path=([96.25,564.0,97.0,564.75],[289])if n==12 else([95.5,91.0,96.25,91.75],[313])
 d['source_background_restore_atoms']=[dict(id=f'source-background-speck-page{n}',rect=rect,image_path=path,dx=0,reviewed=True,source_sha256=source_sha,
  reason='Restore the original isolated scan-background pixel at its exact original coordinate after opaque inline bitmap padding; source-only4x contact witness, no prose/math/figure ink in this tiny region. Exact original image/clip program at1x, no generated pixel or erasure waiver.',
  evidence='root-paint-order-completion/loss-review/ and inline-review/reviewed-candidates.png')]
 if rect not in d['protected_source_display_and_figure_rects']:d['protected_source_display_and_figure_rects'].append(rect)
 d['root_source_contact_corrections']=dict(source_sha256=source_sha,source_shape_review='root-paint-order-completion/inline-review/reviewed-candidates.png',source_scope_review='root-paint-order-completion/loss-review',changes=changes,original_y_and_scale_unchanged=True)
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8');print(n,len(changes),'reviewed corrections')
