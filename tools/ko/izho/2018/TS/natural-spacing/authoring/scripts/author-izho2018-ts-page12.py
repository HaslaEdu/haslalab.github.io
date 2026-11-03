import sys
sys.path.insert(0,'C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions/engine')
from izho2018_ts_authoring import *
p=begin(12);point_labels(p)
for at,text in{'3,11,0':'또는 ','6,0,0':'물의 흐름과 함께 움직이는 기준계에서는 굴절 법칙이 통상적인 형태로 주어진다 ','7,17,0':'빛의 전파 속력은 ','28,0,0':'따라서 ','37,0,0':'따라서 ','41,0,2':' 빛이 물의 흐름과 같은 방향으로 진행할 때, 각 ','41,0,4':'는 식 ','41,1,2':'로 놓아야 하며, 이에 대응하는 속력은 ','44,0,0':'빛이 물의 흐름과 반대 방향으로 진행할 때의 속력은 ','44,1,0':'다음과 같다 ','48,0,0':'두 광선이 물속에서 이동하는 전체 거리는 ','48,0,2':'이므로, 두 광선의 ','48,1,0':'전파 시간 차 ','48,1,2':'는 다음과 같다 ','52,0,0':'이에 대응하는 광로차는 다음과 같다 '}.items():p.add(at,text)
around(p,'10,0,0',['식 ','과 ','을 이용해 실험실 기준계로 돌아오면 '],['(36)','(37)'])
around(p,'26,0,0',['식 ','로부터 최종적으로 '],['(38)-(42)'])
around(p,'33,0,2',[' 다시 식 ','를 이용하면 '],['(38)-(42)'])
around(p,'41,1,0',['','에서 '],['(48)'])
path=finish(p,[],'Full original page12 read: moving-medium refraction/velocity and complete coefficientsA1/B1/A2/B2, opposite water-flow directions and transit-time difference through51. Original two display alternatives38 remain stationary; only standalone English or becomes또는. All MathType sin/cos, angles/primes, source fractional point sizes and complete root/fraction/rule programs remain native.')
d=json.loads(path.read_text('utf8'));d['frozen_display_math_rects']=[[177.5,72,443,140.5]];path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf8')
