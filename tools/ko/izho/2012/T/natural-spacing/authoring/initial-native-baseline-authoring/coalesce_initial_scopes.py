"""Union source fragments of the same printed row, retaining actual glyph y."""
def coalesce(plan,tolerance=.75):
    rows=[list(r)for r in plan['allowed_line_rects']]
    def baseline(r):return r[1]+(r[3]-r[1])*.85/1.33
    changed=True
    while changed:
        changed=False
        for i,a in enumerate(rows):
            j=next((j for j,b in enumerate(rows)if j>i and abs(baseline(a)-baseline(b))<=tolerance and min(a[2],b[2])-max(a[0],b[0])>.02),None)
            if j is None:continue
            b=rows.pop(j);old_a=list(a);a[:]=[min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3])]
            for item in plan['centered_lines']+plan['right_aligned_lines']:
                if item.get('rect')in[old_a,b]:item['rect']=list(a)
            changed=True;break
    plan['allowed_line_rects']=rows
    return plan
if __name__=='__main__':
    from pathlib import Path
    import sys,json
    folder=Path(__file__).resolve().parent/f'natural/{sys.argv[1]}/T/plans'
    for p in folder.glob('page*.json'):
        d=json.loads(p.read_text('utf8'));coalesce(d);p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
