from pathlib import Path
root=Path('D:/CodexBuilds')
p=root/'author-izho2016-solutions-page4.py';s=p.read_text('utf8').replace("'11,5,0':'다음 값을 넘으면: '","'11,5,0':' '").replace("'11,6,2':' 물이 관 전체를 채운다. '","'11,6,2':'를 넘으면 물이 관 전체를 채운다. '");p.write_text(s,'utf8')
p=root/'author-izho2016-solutions-page5.py';s=p.read_text('utf8').replace("'22,41,2':'회로에 흐르는 전류는 유한하며, 축전기를 다음 전압까지 충전하려면 '","'22,41,2':'회로에 흐르는 전류는 유한하다. 축전기를 충전하여 전압을 '").replace("'22,42,0':'전압: '","'22,42,0':' '").replace("'22,42,4':' 무한한 전하량이 필요하므로, 걸리는 시간은 다음과 같다 '","'22,42,4':'까지 높이려면 무한한 전하량이 필요하므로, 걸리는 시간은 다음과 같다 '");p.write_text(s,'utf8')
p=root/'author-izho2016-solutions-page6.py';s=p.read_text('utf8').replace("'10,9,2':'축전기의 전하량이 ','10,9,4':'인 상태에서 '","'10,9,2':'시간 간격 ','10,9,4':'는 전하량이 '").replace("'10,10,0':'다음 값까지 증가하는 데 걸리는 시간: '","'10,10,0':'에서 '").replace("'10,10,2':'은 다음과 같다 '","'10,10,2':'까지 증가하는 데 걸리는 시간으로, 다음과 같다 '");p.write_text(s,'utf8')
