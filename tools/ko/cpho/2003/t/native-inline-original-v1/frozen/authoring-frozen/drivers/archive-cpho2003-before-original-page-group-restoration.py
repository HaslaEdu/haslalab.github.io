from pathlib import Path
import json
B=Path('C:/Users/andre/CodexWork/HaslaLab/translation-builds/cpho2003-original-native').resolve();history=B/'proof-history/before-original-source-page-group-restoration';assert not history.exists();history.mkdir(parents=True)
for rel in ['natural/2003','native-baseline','initial-fixed-slot-staging','proof-renders-144','evidence/actual-style','evidence/source-native-ink','evidence/source-programs-and-advances','evidence/negative-controls','evidence/native-visual-review']:
 source=(B/rel).resolve();target=(history/rel).resolve();assert source.is_relative_to(B)and target.is_relative_to(history)and not target.exists()
 if source.exists():target.parent.mkdir(parents=True,exist_ok=True);source.rename(target)
q=dict(status='ORIGINAL_PAGE_GROUP_RESTORATION_IN_PROGRESS_NOT_READY',source_sha256='52f8a891d6129becf4d21ccb60f46997cedf9aa50123ffd147294cedcb121b63',actual_source_group=dict(Type='/Group',S='/Transparency',CS='/DeviceRGB'),finding='PyMuPDF initial page import omitted this original page group. Original fonts, glyphs, source-point sizes, images and ink already passed; restore the original object in the initial10-page staging baseline and rebuild all6 proofs/derived audits. No thresholds or native guard changed.',earlier_current_proofs_and_actual5_negatives_preserved=str(history),C07_readonly_crosscheck='Original and frozen proof both have no Group and retain the same CS1 ICC graph; no change to C07.')
(B/'evidence/native-T-source-page-group-review.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
