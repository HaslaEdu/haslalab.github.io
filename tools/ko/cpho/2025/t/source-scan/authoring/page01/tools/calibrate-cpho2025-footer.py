from pathlib import Path
source=Path('D:/CodexBuilds/calibrate-cpho2025-header-hint.py').read_text('utf8')
start=source.index('fields=');end=source.index('\nresult={}',start)
source=source[:start]+"fields=[('footer_last','页',[324,778,337,793],8.4,10.0),('footer_first','第',[263,779,276.8,793],8.4,10.0)]"+source[end:]
exec(compile(source,__file__,'exec'))
