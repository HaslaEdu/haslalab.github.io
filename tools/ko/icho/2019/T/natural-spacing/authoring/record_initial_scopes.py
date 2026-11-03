from pathlib import Path
import json
BASE=Path(__file__).resolve().parent
for n in range(1,61):
    p=BASE/f'page{n:02}.overrides.json'
    if p.exists():raise ValueError('Preserving existing year2019 override '+str(p))
    scope=dict(fixed_native_rects=[[493.5,33,533,51],[503,778,538,805]],review_basis='Original fixed candidate-code and footer-page-number columns remain at exact source coordinates, font and size. Body expressions continue to use natural Korean advances.')
    data={'__layout_scope__':scope}
    if n==1:
        data['__slot_edits__']={'p1:b2:l0:s1-1':dict(join_left=True),'p1:b3:l0:s1-1:dropcap':dict(join_left=True)}
        scope['source_caption_centering']=[dict(source_line=[2,0],reason='Original centered cover title; original drop-cap physical sizes and baseline are preserved.'),dict(source_line=[3,0],reason='Original centered cover exam title; original drop-cap physical sizes and baseline are preserved.'),dict(source_line=[5,1],reason='Original centered cover slogan.')]
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf8')
print('60year2019 header/footer guards and source-centered cover slots written')
