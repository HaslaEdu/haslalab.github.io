"""Closed literal source14 magenta figure tags, derived from original CIDs."""
from pathlib import Path
import json
B=Path(__file__).resolve().parents[1]
SOURCE='4e076fb9234683d028792190bcec56f12de72890da6c0e44ddf0e9146013459d'
TAGS={(14,'r02'):56,(14,'r10'):461}
def parts(n,row,lang,text):
 bindings=row.get('source_prose_color_literals',[]);index=TAGS.get((n,row['id']))
 if index is None:
  assert not bindings,'No unbound translated color policy allowed'
  return [(text,row['source_prose_color'])]
 assert len(bindings)==1
 binding=bindings[0];original=json.loads((B/'inspection/page14-original-native-programs.json').read_text('utf8'))['actual_original_glyphs'][index]
 assert binding['source_glyph']['source_trace_index']==index
 assert {k:v for k,v in binding['source_glyph'].items()if k!='source_trace_index'}==original
 assert original['c']=='图'and original['color']==[1.,0.,1.]and original['font']=='ËÎÌå+FPEF'
 assert binding['ko']=='그림'and binding['en']=='Fig.'
 literal=binding[lang];assert row[lang].count(literal)==1
 if literal not in text:return[(text,row['source_prose_color'])]
 before,after=text.split(literal);return[(before,row['source_prose_color']),(literal,original['color']),(after,row['source_prose_color'])]
