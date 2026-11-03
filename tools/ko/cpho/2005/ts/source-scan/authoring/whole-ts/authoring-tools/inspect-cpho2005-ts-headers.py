from pathlib import Path
import json,re
from collections import Counter
p=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2005/TS/inputs/native-slots.json');q=json.loads(p.read_text('utf8'))
for page in q['pages'][3:5]:
 for s in page['slots']:
  print(page['source_page'],s['source'],Counter(c['font']for c in s['source_characters']if re.search('[\u3400-\u9fff]',c['c'])),s['size'],s.get('original_horizontal_center'))
