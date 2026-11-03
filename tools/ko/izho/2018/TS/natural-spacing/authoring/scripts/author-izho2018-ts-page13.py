import sys
sys.path.insert(0,'C:/Users/andre/CodexWork/HaslaLab/translation-builds/izho2018-complete-solutions/engine')
from izho2018_ts_authoring import *
p=begin(13);point_labels(p)
p.add('3,0,0','따라서 간섭무늬가 이동한 무늬의 수는 다음과 같다 ')
around(p,'6,0,2',[' 식 ','을 이용하면 물의 굴절률은 다음과 같다 '],['(53)'])
for at,text in{'9,0,0':'구분','9,1,0':'평가 항목','9,2,0':'배점','72,0,0':'수치 '}.items():p.add(at,text)
for at in['11,0,0','20,1,0','21,0,0','22,0,0','31,0,0','37,1,0','44,0,0','46,0,0','48,0,0','48,5,0','48,13,0','49,0,0','58,0,0','59,1,0','63,0,0','66,0,0','67,0,0','68,0,0']:formula(p,at)
finish(p,[[9,0,0],[9,1,0],[9,2,0]],'Full original page13 read: original path/fringe-shift and refractive-index equations52–54; all four-vector/Doppler/aberration grading rows1.1–2.3 including native formulas1–18 and declination value. All original complete MathType rational/root functions and exact original scores are preserved; only English prose labels translated.')
