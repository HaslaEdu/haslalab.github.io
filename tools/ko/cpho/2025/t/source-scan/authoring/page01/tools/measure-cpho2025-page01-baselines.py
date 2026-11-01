from pathlib import Path
import sys,json,hashlib
B=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2025');PUB=Path('D:/CodexBuilds/Hasla-publish-20261031')
sys.path[:0]=['D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS/tools',str(PUB/'tools')]
import pymupdf as fitz
from cpho_2013_ts_manual_page04 import source_baseline
from pdf_memory_gate import page_worker
hints={r['id']:r for r in json.loads((B/'page1-ocr-hints.json').read_text('utf8'))['rows']}
mapping={'p1-intro-a':2,'p1-intro-b':5,'p1-intro-c':8,'p1-intro-d':9,'p1-intro-e':11,'p1-fixed-dipole':15,'p1-direction':17,'p1-angle-guide':18,'p1-axle':19,'p1-mass':20,'p1-question-1':22,'p1-question-2':23,'p1-question-2-end':24,'p1-question-3':25,'p1-question-3-end':26,'p1-question-4':27,'p2-convention':28,'p2-wave-symbols':30,'p2-complex-amplitude':31,'p2-phononic-crystal':32,'p2-small-wave':35,'p2-question-1':38,'p2-question-1-b':40,'p2-question-1-c':41,'p2-question-1-d':42,'p2-question-2':43,'p2-question-2-b':44,'figure-1-caption':16,'figure-2-caption':39}
short_runs={'p1-angle-guide':'质心位于','p1-axle':'光滑绝缘轴','p1-inertia':'单位矢量','p1-question-1':'电场强度','p1-question-2':'电场力沿','p1-question-3':'平衡位置','p1-question-4':'静止释放','p2-question-1-c':'原长弦线','p2-question-2':'正方向和负','p2-matrix-caption':'矩阵表示'}
source=B/'CPhO_2025_T_original-explicit-page-clip.pdf';rows=[]
plan=json.loads((B/'authoring/page01-draft-layout.json').read_text('utf8'))
with page_worker(),fitz.open(source)as doc:
 for row in plan['rows']:
    if row['id']in mapping:
        h=hints['1-'+str(mapping[row['id']])];rect=[min(p[0]for p in h['polygon']),min(p[1]for p in h['polygon']),max(p[0]for p in h['polygon']),max(p[1]for p in h['polygon'])];text=h['text'];size=row['size']
    elif row['id']=='p1-inertia':rect=[226,349,347,369];text='轴方向的单位矢量分别记为';size=10.24
    elif row['id']=='p2-matrix-caption':rect=[469,692,538,713];text='其矩阵表示为';size=10.24
    elif row['id']=='footer':rect=[324,778,337,793];text='页';size=8.5
    else:raise ValueError(row['id'])
    if row['id']in short_runs:text=short_runs[row['id']]
    baseline,evidence=source_baseline(doc[0],rect,text,size)
    r=dict(id=row['id'],old_baseline=row['baseline'],measured_baseline=baseline,delta=baseline-row['baseline'],fixed_source_font_size=size,source_font='SimSun',evidence=evidence)
    rows.append(r);print(json.dumps(r,ensure_ascii=False),flush=True)
q=dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),status='READ_ONLY_SOURCE_BASELINE_MEASUREMENTS_REQUIRES_REVIEW',rows=rows,point_size_adjusted_to_fit_translation=False)
(B/'authoring/page01-source-baselines.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n','utf8')
