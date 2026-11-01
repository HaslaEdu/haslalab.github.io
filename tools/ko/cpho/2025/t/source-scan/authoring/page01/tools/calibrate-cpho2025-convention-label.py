from pathlib import Path
s=Path('D:/CodexBuilds/calibrate-cpho2025-header-hint.py').read_text('utf8')
a=s.index('fields=');b=s.index('\nresult={}',a)
s=s[:a]+"fields=[('convention_label','约定',[126,492,147,510],9.6,10.8),('convention_score','分',[101.5,492.5,113,509],9.6,10.8)]"+s[b:]
exec(compile(s,__file__,'exec'))
