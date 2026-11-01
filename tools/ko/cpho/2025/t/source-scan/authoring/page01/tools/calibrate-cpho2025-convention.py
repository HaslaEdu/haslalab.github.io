from pathlib import Path
source=Path('D:/CodexBuilds/calibrate-cpho2025-header-hint.py').read_text('utf8')
start=source.index('fields=');end=source.index('\nresult={}',start)
source=source[:start]+"fields=[('convention','轴正方向传播的一维简谐横波',[177,492,309,510],9.6,10.8),('convention_def','和介质参量表示',[317,526,391,546],9.6,10.8),('convention_amplitude','处的复振幅',[96,544,148,563],9.6,10.8)]"+source[end:]
exec(compile(source,__file__,'exec'))
