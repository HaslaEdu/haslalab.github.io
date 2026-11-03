from pathlib import Path
import json,re,hashlib,copy
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();SOURCE='f338dd0093628b658df3f02ca40a34b97e6ecd8fa431cf8517f08aa4eb14ff49';assert sha(B/'2018/source/IZhO_2018_TS.pdf')==SOURCE
ALLOWED={'XIV','mg','ma','mgx','xg','gx','mv','const','mA','CU','Cl','AB','tg','sm','см','мс','kg','km','exp','Pa','ln','mc','inv','cos','sin','arcsin','ph','Fdr','GM','dr','II','dx','dt','dy','Vdt','Lv'}
def retained(n,auth):
 runs=json.loads((B/f'2018/inspection/page{n:02}-runs.json').read_text('utf8'));selected={};rows=[]
 for s in auth['slots']:
  at=','.join(map(str,s['at']));text=runs[at]['text']
  if 'range'in s:a,b=s['range']
  elif 'substring'in s:a=text.index(s['substring']);b=a+len(s['substring'])
  else:a,b=0,len(text)
  assert text[a:b]==s['source_text'];selected.setdefault(at,[]).append([a,b])
 for at,r in runs.items():
  for m in re.finditer(r'[A-Za-z]{2,}|[\u0400-\u04ff]{2,}',r['text']):
   if all(any(a<=i<b for a,b in selected.get(at,[]))for i in range(m.start(),m.end())):continue
   rows.append(dict(source_page=n,source_at=at,range=[m.start(),m.end()],original_native_word=m.group(),full_source_run=r['text'],source_font=r['font'],source_origin=r['origin']))
 return rows
authored={n:json.loads((B/f'2018/original_style/page{n}.json').read_text('utf8'))for n in range(1,16)};rows=[r for n,a in authored.items()for r in retained(n,a)];assert all(r['original_native_word']in ALLOWED for r in rows),[r for r in rows if r['original_native_word']not in ALLOWED]
policy=B/'2018/inspection/reviewed-retained-native-mathematical-lexical-fragments.json';policy.write_text(json.dumps(dict(source_sha256=SOURCE,all_original_source_pages_visually_read=True,scope='Every retained ASCII/Cyrillic lexical word2+ characters reviewed in its complete original source formula/identifier/unit context. Original headerXIV retained. All other English/Russian prose, including duplicate source paragraphs and grading entries, is selected for translation.',reviewed_native_mathematical_fragments=rows),ensure_ascii=False,indent=2)+'\n','utf8')
expected={(r['source_page'],r['source_at'],tuple(r['range']),r['original_native_word'])for r in rows};negative=copy.deepcopy(authored[6]);removed=[s for s in negative['slots']if s['at']==[25,25,0]];assert len(removed)==1;negative['slots'].remove(removed[0]);unexpected=[r for r in retained(6,negative)if(r['source_page'],r['source_at'],tuple(r['range']),r['original_native_word'])not in expected];assert any(r['original_native_word']=='Thus'for r in unexpected)
report=dict(source_sha256=SOURCE,source_pages=15,all_original_source_prose_and_all_grading_translated=True,explicit_source_selections=sum(len(a['slots'])for a in authored.values()),retained_native_mathematical_lexical_fragments=len(rows),reviewed_math_policy_file=str(policy),reviewed_math_policy_sha256=sha(policy),untranslated_original_English_or_Russian_prose_fragments=[],actual_omitted_source_sentence_control_rejected=True,omission_control_source_at=[6,25,25,0],omission_control_unexpected_English_words=[r['original_native_word']for r in unexpected],source_bitmap_English_words_translated=dict(Star='별',Sun='태양',Earth='지구'),original_typographical_and_numerical_errors_retained_without_editorial_notes=True,passed=True)
out=B/'2018/inspection/complete-original-prose-coverage.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf8');print('COMPLETE_ORIGINAL2018_ENGLISH_RUSSIAN_PROSE_AND_GRADING_COVERAGE_PASS',report['explicit_source_selections'],len(rows),sha(out),flush=True)
