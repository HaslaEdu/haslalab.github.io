from pathlib import Path
import sys
path=Path('D:/CodexBuilds/build-izho2013-natural-pages-and-checks.py');text=path.read_text('utf8');assert text.count("'natural/2013-private-page-progress.json'")==1
text=text.replace("'natural/2013-private-page-progress.json'","'natural/2013-reviewed-refinement-progress.json'")
exec(compile(text,str(path)+'#separate-refinement-record','exec'),{'__name__':'__main__'})
