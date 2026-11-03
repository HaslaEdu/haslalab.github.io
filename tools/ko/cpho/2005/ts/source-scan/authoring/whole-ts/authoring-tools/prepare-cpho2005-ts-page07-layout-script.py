from pathlib import Path
import json
s=Path('D:/CodexBuilds/author-cpho2005-ts-page06-layout.py').read_text('utf8')
s=s.replace('page06','page07').replace('source[5]','source[6]').replace('source_page=6','source_page=7')
geometry={
'same-moles':(68,[66,64.5,150,83]),'B-final':(68.5,[66.5,100,404,120]),'state-equation':(68,[66,121,83,139]),'equation-range':(69,[67,170,173,190]),'substitution':(70,[68,233.5,216,252]),'section-four':(94,[92,285.5,117,304]),
'compression-first':(94,[92,302.5,407,321.5]),'compression-second':(70,[68,321.5,408,341]),'contact-forces':(70,[68,339.5,408,359.5]),'friction-forces':(70,[68,358.2,408,377.25]),'extra-compression':(64,[62,387.371,407,408]),'before-impact':(64,[62,407,248,426]),
'caption':(601,[599,219,627,238]),'massless':(440,[438,237.5,783,256]),'resultant':(440,[438,257,782,275]),'components':(440,[438,275,582,293]),'combine':(441,[439,335.5,532,353.02]),'recovery-first':(461,[459,438.146,783,458]),'recovery-second':(436,[434,458,674,477])}
start=s.index('geometry={');end=s.index('\nrows=[]',start)
s=s[:start]+'geometry='+repr(geometry)+s[end:]
s=s.replace("  if id=='B-volume':row['math_after_gaps_by_language']['ko']={'alphaVB':.5}\n",'')
s=s.replace("  rows.append(row);used+=ids", "  if id=='friction-forces':\n   for language_key in ['ko','en']:row['math_after_gaps_by_language'].setdefault(language_key,{}).update({'fN':1.125,'fP':.5})\n   row['source_math_list_spacing_evidence']='Native fN crop right101.25; fP crop left102.375 right118.375; fQ crop left118.875. Keep their original1.125pt/0.5pt inter-crop gaps so all3 native objects retain one common source-to-target horizontal translation.'\n  rows.append(row);used+=ids")
s=s.replace("  rows.append(row);used+=ids", "  if id=='compression-first':row['math_after_gaps_by_language'].setdefault('ko',{}).update({'F-external':.5})\n  rows.append(row);used+=ids")
start=s.index(' protected_source_display_and_figure_rects=');end=s.index("\n(B/'authoring",start)
protected=[[210,81,405,100],[153,140,405,170.5],[93,190.2,405,233],[117,252.2,406,285.4],[163,427,405,445],[163,446,405,474],[185,474.5,405,502],[184,502.2,405,521.621],[559,56.77,784,129],[476,145,748,215],[502,294,785,314],[490,315,785,334.5],[478,357.97,784,426.22],[496,477.2,784,495],[482,496,784,517.646]]
s=s[:start]+' protected_source_display_and_figure_rects='+repr(protected)+",\n original_math_list_separators_retained=['fP','fQ'],figure_caption_original_center=612.0)"+s[end:]
s=s.replace("  try:row_layout(row,lang,metric)","  try:\n   if row['id']=='caption':\n    tokens,end=row_layout(row,lang,metric)\n    row.setdefault('left_by_language',{})[lang]=612.0-(end-row['left'])/2\n    row['original_caption_center']=612.0\n   row_layout(row,lang,metric)")
# This page deliberately retains the two native list punctuation marks before
# fP and fQ; translations do not paint duplicate punctuation. All other crops
# have no neighbouring Chinese or unwanted punctuation.
s=s.replace('no neighbouring Chinese/punctuation. Source native','no neighbouring Chinese; original list punctuation before fP/fQ is intentionally retained and not duplicated. Source native')
# Save language-specific centered caption origins in the actual proposal.
s += "\n(B/'authoring/page07-layout-proposal.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\\n','utf8')\n"
out=Path('D:/CodexBuilds/author-cpho2005-ts-page07-layout.py');out.write_text(s,'utf8')
print('PAGE07_LAYOUT_SCRIPT_CREATED',len(geometry))
