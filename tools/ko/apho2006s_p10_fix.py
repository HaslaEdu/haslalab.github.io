"""python3 tools/ko/apho2006s_p10_fix.py <APhO_2006_S_KO.pdf> <out.pdf>"""
# APhO 2006 S KO p10: the white box over the English 2nd line («30%, 1.0points. If within 50%, 0.5 points.») is painted
# after the Korean line «가 정답의 20% 안. …» and cuts its glyph bottoms. Box 644 (painted before the Korean) already
# covers that English line from x=317.9 on, so box 646 is narrowed to end at x=319.5, short of the Korean (x>=319.8).
import pymupdf,sys
d=pymupdf.open(sys.argv[1]); p=d[9]
xs=[x for x,name,inv,bb in p.get_xobjects() if name=='fullpage']
done=0
for x in set(xs):
    s=d.xref_stream(x)
    old=b'267.2 345.4 242.7 16.5 re\nh\n1 1 1 rg f'
    if s.count(old)==1:
        d.update_stream(x,s.replace(old,b'267.2 345.4 52.3 16.5 re\nh\n1 1 1 rg f')); done+=1
assert done==1
d.save(sys.argv[2],garbage=3,deflate=True)
