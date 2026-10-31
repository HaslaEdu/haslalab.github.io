"""python3 tools/ko/usapho2026_p6_fix.py <USAPhO_2026_T_KO.pdf> <out.pdf>"""
# USAPhO 2026 T KO p6: the page holds the overflow of Problem A3 (fzFrm2), but four reference-sheet labels with their
# white boxes («참고 자료», «기본 상수», «유용한 근사식», «이 자료는 시험의 두 부분 모두에서 사용할 수 있습니다.») were laid on
# it as if it were the reference sheet (EN p6) - they cover and overprint lines of A3 (a)/(b). Those 8 content streams
# are taken out of p6's /Contents; nothing else on the page changes.
import pymupdf,sys,re
d=pymupdf.open(sys.argv[1]); p=d[5]
n=0
keep=[]
for c in p.get_contents():
    s=d.xref_stream(c)
    if re.fullmatch(rb'\s*q\s*[-\d. ]+ re\s*h\s*1 1 1 rg f\s*Q\s*',s) or re.fullmatch(rb'\s*q\s*BT\s*1 0 0 1 [-\d. ]+ Tm /NotoKR [\d.]+ Tf \[<[0-9a-f]+>\]TJ\s*ET\s*Q\s*',s):
        n+=1; continue
    keep.append(c)
assert n==8, n
# the same streams also draw these labels on p1 (the real reference sheet), so they are dropped from p6's /Contents only
d.xref_set_key(p.xref,'Contents','[%s]'%' '.join('%d 0 R'%c for c in keep))
d.save(sys.argv[2],garbage=3,deflate=True)
