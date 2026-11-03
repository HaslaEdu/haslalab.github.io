from pathlib import Path
p=Path('D:/CodexBuilds/calibrate-cpho2005-page05-distinct-typefaces.py')
s=p.read_text('utf8').replace('page05','page06').replace('original[4]','original[5]').replace('page=5','page=6')
start=s.index('fields=[');end=s.index('\nresults=',start)
s=s[:start]+"fields=[('comparison','可见',[65,65,93,81]),('body','温度缓慢',[110,314,160,333])]"+s[end:]
# Run the same independent source-only four-family comparison, no target text.
exec(compile(s,'page06-independent-source-faces','exec'))
