from pathlib import Path
p=Path('D:/CodexBuilds/check-izho2013-existing-current-proof.py');text=p.read_text('utf8').replace('2013','2014').replace('ORIGINAL_PROSE_OVERLAP','EXACT_ORIGINAL_CID_TF_TM').replace('audit-before-original-prose-reference','audit-before-original-CID-Tf-Tm-phase-reference')
exec(compile(text,str(p)+'#2014-exact-CID-reference','exec'),{'__name__':'__main__'})
