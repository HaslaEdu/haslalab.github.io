from pathlib import Path
import json,sys
import pymupdf as f
from fontTools.ttLib import TTFont
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS')
sys.path[:0]=[str(B/'tools'),'D:/CodexBuilds/Hasla-publish-20261031/tools','D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools']
from cpho_2005_ts_compose import new_font,font_path,width
q=json.loads((B/'proofs/en/page04.composition.json').read_text('utf8'))
r=next(r for r in q['body_placements']if r['id']=='sin-greater')
print('PLACEMENT',json.dumps(r['tokens']),flush=True)
with f.open(B/'proofs/en/page04.pdf') as d:
 for t in d[0].get_texttrace():
  if t['chars']and abs(t['chars'][0][2][1]-171.25)<.1:
   print(t['font'],t['size'],'chars',[(chr(c[0]),c[1],tuple(round(z,3)for z in c[2]),tuple(round(z,3)for z in c[3]))for c in t['chars']],flush=True)
with TTFont(q['body_fonts']['SimSun']['subset'])as tf:
 cm=tf.getBestCmap();print('TTF',tf['head'].unitsPerEm,{c:tf['hmtx'][cm[ord(c)]]for c in 'Thenlight'})
font=f.Font(fontfile=q['body_fonts']['SimSun']['subset'])
print('METRICS',{c:font.glyph_advance(ord(c))*12.475 for c in 'Thenlight'},flush=True)
