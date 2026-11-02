from pathlib import Path
s=Path('D:/CodexBuilds/calibrate-cpho2025-actual-stroke.py').read_text('utf8')
s=s.replace('[62,193,231.7,209]','[177,492,309,510]').replace("text='用在决定分子排布中扮演着重要角色';rows=[];size=10.24","text='轴正方向传播的一维简谐横波';rows=[];size=10.0")
s=s.replace("fontfile='C:/Windows/Fonts/simsun.ttc'","fontfile='D:/CodexBuilds/Hasla-original-style-20261031/official-hans-fonts/faces/simkai.ttf'")
s=s.replace('body-actual-stroke-calibration.json','note-actual-stroke-calibration.json').replace('SimSun','KaiTi')
exec(compile(s,__file__,'exec'))
