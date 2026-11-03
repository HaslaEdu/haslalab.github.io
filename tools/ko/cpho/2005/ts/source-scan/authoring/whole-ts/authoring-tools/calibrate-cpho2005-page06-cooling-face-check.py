from pathlib import Path
s=Path('D:/CodexBuilds/calibrate-cpho2005-page05-distinct-typefaces.py').read_text('utf8').replace('page05','page06-cooling-check').replace('original[4]','original[5]').replace('page=5','page=6')
start=s.index('fields=[');end=s.index('\nresults=',start)
s=s[:start]+"fields=[('cooling-full','当温度缓慢下降',[96,313,184,333]),('conditions','根据题给的条件',[202,313,291,333]),('conclusion','可以判定',[296,313,348,333])]"+s[end:]
start=s.index('fonts=[');end=s.index('\nfields=',start)
s=s[:start]+"fonts=[('SimSun','C:/Windows/Fonts/simsun.ttc'),('SimHei',str(fontroot/'simhei.ttf'))]"+s[end:]
exec(compile(s,'page06-cooling-family-independent-samples','exec'))
