from pathlib import Path
import json,shutil,hashlib
D=Path('D:/CodexBuilds/Hasla-original-style-20261031');B=D/'cpho2005/TS';PUB=Path('D:/CodexBuilds/Hasla-publish-20261031');TS=D/'cpho2013/TS/tools'
# Private copy only: the already reviewed2013 producers remain unchanged.
text=(TS/'cpho_2013_ts_compose.py').read_text('utf8')
text=text.replace("ROOT=Path.cwd()","ROOT=Path('C:/Users/andre/OneDrive/문서/ChatGPT/Hasla 노술/haslalab')")
text=text.replace("cpho2013/TS'","cpho2005/TS'").replace("SOURCE=ROOT/'tmp/original-style-sources/CPhO_2013_Chinese_original.pdf'","SOURCE=BASE/'inputs/CPhO_2005_Chinese_original.pdf'").replace('612d676f525ddc35ad3b417a8f25141d3467f48309d52dfdbcab7bd222201d68','9867b5116f1feb921515844332d43ed08a7c790292d5eecd89c70aacdf698b4f')
start=text.index('def font_path(');end=text.index('\n\ndef width(',start)
text=text[:start]+'''def font_path(lang,face='SimSun'):
    if lang=='ko':
        return Path('C:/Windows/Fonts/batang.ttc')if face=='SimSun'else ROOT/'tools/ko/fonts/NotoSansCJKkr-Regular.otf'
    if face=='SimSun':return Path('C:/Windows/Fonts/simsun.ttc')
    if face=='SimHei':return Path('D:/CodexBuilds/Hasla-original-style-20261031/official-hans-fonts/faces/simhei.ttf')
    raise ValueError(('Unknown original Chinese prose face',face))
'''+text[end:]
text=text.replace("(ROOT/'tools/ko/cpho/2013/original/native-slots.json')","(BASE/'inputs/native-slots.json')")
text=text.replace("face=slot['source_font'];role=face","face=next((c['font']for c in slot['source_characters']if re.search('[\\u3400-\\u9fff]',c['c'])),slot['source_font']);role=face")
text=text.replace("if h['source_font']==face","if h['source_prose_face']==face")
text=text.replace('Original2013 scanned solutions','Private2005 scanned solutions')
(B/'tools/cpho_2005_ts_compose.py').write_text(text,'utf8')
print('Private2005 source/header producer fork initialized; mixed body-face extension still pending, no proof READY.')
