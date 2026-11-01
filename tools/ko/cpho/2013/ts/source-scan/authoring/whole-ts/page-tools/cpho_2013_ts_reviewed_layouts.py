"""Apply explicit source-contact-sheet reviews, not automatic OCR approval."""
from pathlib import Path
import argparse,json
import pymupdf as fitz
from cpho_2013_ts_manual_page04 import source_baseline
BASE=Path('D:/CodexBuilds/Hasla-original-style-20261031/cpho2013/TS')
PATCHES={
 5:{
  'normal-T':dict(x1=248.5),'eq6-sub':dict(x1=249.0),
  'omega-definition':dict(x0=98.0),'ball2-velocity':dict(x0=238.0),
  'theta-increasing':dict(x0=211.0),'omega-positive':dict(x1=295.0),
  'sin-zero':dict(x1=208.0),'theta-zero':dict(x1=248.0),'other-root':dict(x1=512.0),
  'mark1':dict(x0=168.0),
 },
 6:{'part2':dict(y1=321.8),'r0-definition':dict(y0=327.0),'W-L':dict(x1=270.5)},
 7:{'part4':dict(y1=428.5),'dl-segment':dict(y0=456.5),'dm-definition':dict(x1=313.5,y0=456.5),'Fbase-second':dict(x0=449.0),'zero-work-sum':dict(x1=208.5,y0=639.0)},
 8:{
  'Fbase-negative-top':dict(x1=122.5),'L-at':dict(x0=183.5,x1=213.5),
  'alpha-pm':dict(x0=105.5),'alpha-zero':dict(x0=182.5),
  'case-L-above':dict(x1=148.0),'case-alpha-above':dict(x1=205.0),
  'case-L-at':dict(x0=75.5,x1=108.5),'case-alpha-at':dict(x0=136.0,x1=165.5),
  'case-L-between':dict(x1=154.5),'case-alpha-between':dict(x1=234.5),
  'Fbase-negative-up':dict(x0=299.0,x1=332.0),'Qi':dict(x1=159.0),'minus-Qi':dict(x0=315.0,x1=332.5),
  'g3':dict(x1=129.0),'g20':dict(x1=309.0),
 },
 9:{
  't-zero':dict(x0=369.0),'z-zero':dict(x0=409.5,x1=430.0),'rest-zero':dict(x0=440.5,x1=463.0),
  'I-initial':dict(x0=474.5,x1=498.5),'gravity-expression':dict(x0=232.0,x1=286.0),
  'force-zero':dict(x0=161.5,x1=201.5),
 },
 14:{},
}
PROTECTED={
 5:[[139,106.5,222,119],[284,107,298,120],[139,133,223,147],[284,134,299,147],
    [216,174,384,199],[448,181,466,195],[219,216.6,380,245],[448,223,466,236],
    [138,261,410,286],[447,268,466,282],[216,302,273,314.8],[443,302,466,316],
    [218,330,249,345],[444,331,466,345],[110,342,259,369],[279,348,298,363],
    [105,396,258,419],[281,396,298,411],[105,435,395,460],[438,439,465,451],
    [221,473,310,502],[438,484,457,498],[216,530,332,554],[438,538,458,550],
    [216,570,309,596],[438,576,458,589],[202,611,296,636],[438,618,458,631],
    [202,679,263,701],[433,686,454,698],[420,340,517,406],[426,128,436,163]],
 6:[[129,133,250,157],[439,141,458,156],[126,185,410,211],[439,193,459,207],
    [156,226,420,254],[439,236,459,250],[115,283.5,435,309],[439,289,459,304],
    [219,352,291,378],[255,392,320,423.5],[439,405,459,420],
    [132,440,410,472],[437,449,458,464],[130,485,408,508],[437,492,458,507],
    [132,524,395,557]],
 7:[[155,72,302,108],[174,124,367,153.5],[452,133,472,147],[217,179,380,208],
    [221,222,346,252],[443,234,466,249],[223,269,359,303],[442,280,468,295],
    [216,320,365,356],[430,333,453,348],[206,373,366,409],[430,384,453,398],
    [157,503,397,527.5],[435,510,458,525],[140,545,421,571],[435,553,458,566],
    [143,587,431,608],[435,590,458,604],[192,625,285,638],[428,626,452,640],
    [191,653,452,684],[192,694,354,725],[432,703,455,718]],
 8:[[104,104,398,162],[427,129,449,143],[202,207,283,220],[425,210,449,221],
    [203,249,354,279],[422,257,449,271],[175,493,266,523],[434,499,451,514],
    [177,536.5,257,565.5],[434,543,451,558],[177,581,269,609],[435,587,452,602],
    [177,626,224,653],[437,631,455,646],[181,670,236,696],[437,672,455,686]],
 9:[[187,72,300,100],[441,82,460,95],[184,115,413,143.5],[443,122,464,136],
    [185,160,303,194],[443,168,465,182],[205,279,270,292.5],[438,280,455,294],
    [197,307,309,324],[438,313,456,326],[196,340,275,355],[438,341,456,355],
    [196,369,309,393],[438,375,456,391],[192,419,346,478],[437,441,457,458],
    [203,492.5,280,536],[438,507,458,523],[206,553,375,571],[437,555,458,569],
    [205,585,379,616],[438,593,458,608],[205,632,303,660],[453,640,475,653],
    [205,675.5,319,690],[452,677,475,691],[195,705,344,737],[452,715,475,729]],
 14:[[182,86,312,115.5],[445,95,466,109],[110,134,275,162],[439,143,466,156],
     [110,165,345,194],[439,173,466,186],[110,195,365,225],[439,204,466,217],
     [180,226,190,239],[110,240,420,268],[439,249,466,262],[186,282.5,273,299],[439,282,466,296]],
}

EXTRA=json.loads((BASE/'authoring'/'manual-extra-rois.json').read_text('utf8'))
for key,value in EXTRA.get('patches',{}).items():PATCHES[int(key)]=value
for key,value in EXTRA.get('protected',{}).items():PROTECTED[int(key)]=value

def create(page):
    if page not in PATCHES:raise ValueError('Contact sheet not yet manually reviewed')
    data=json.loads((BASE/'row-hints'/f'page{page:02d}-geometry-candidates.json').read_text('utf8'))
    hints={r['id']:r for r in json.loads((BASE/'row-hints'/f'page{page:02d}-ctc.json').read_text('utf8'))['rows']}
    source=Path.cwd()/'tmp/original-style-sources/CPhO_2013_Chinese_original.pdf'
    with fitz.open(source)as doc:
        for row in data['rows']:
            if page==10 and row['source_image_path']==[339]:
                row['size']=10.48
                row['font_size_measurement']='p10-tight-prose.json: ten original known CJK glyphs best fixed-source SimSun10.48pt, IoU.7521 versus KaiTi.451/FangSong.545. Measurement before translation; no fitting.'
            if page==6 and row['source_image_path']==[293]:
                row['size']=9.68
                row['font_size_measurement']='p6-tight-prose.json: fixed-source SimSun size9.68pt, IoU.693479 versus KaiTi.432/FangSong.523; pure source scan baseline angle+.3deg. Not translation fitting.'
            rect=hints[row['id']]['rect'];baseline,evidence=source_baseline(doc[page-1],rect,row['source'],row['size'])
            row.update(baseline=baseline,baseline_evidence=evidence,reviewed=True,location_only=False,
                source_visual_review='Original full page and original bitmap contact sheet; later final whole-page and actual-ink audits remain required.')
            row.update(printed_regular_stroke=round((.5 if page==6 else .45)*row['size']/(9.68 if page==6 else 9.78),4),printed_bold_stroke=round(.6*row['size']/9.78,4),
                scan_weight_evidence='Original known-CJK actual PDF Tr2 raster comparisons: p4-first-ten, p4-speed-clause and p6-tight-prose-actual-stroke.json. Same-print scanned chunks use the physical image scale; no translation or glyph width fitting.')
            row['printed_stroke_by_language']={'en':dict(regular=row['printed_regular_stroke'],bold=row['printed_bold_stroke']),
                'ko':dict(regular=round(.3*row['size']/9.78,4),bold=round(.4*row['size']/9.78,4),evidence='source-vs-Batang-stems.json/.png: actual source primary vertical/horizontal stem medians and contrast, not whole ink density. Regular.30 and modest bold.40 at9.78pt, proportionally scaled for independently measured sourcepointsize; no font width/size fitting.')}
            if row['source'].strip()in['参考解答：','参考解答:']:row['role']='serif-bold'
            for atom in row['atoms']:
                changes=PATCHES[page].get(atom['id'],{})
                for name,value in changes.items():atom['rect'][['x0','y0','x1','y1'].index(name)]=value
                atom.update(reviewed=True,location_only=False,reason='Entire source mathematical object manually checked in the original bitmap contact sheet; neighbouring Chinese/punctuation excluded by explicit coordinate review. Original1x bitmap/q/clip/cm/Do tokens retained.')
                if atom['expected_original'].endswith('.'):
                    for language in ['ko','en']:row[language]=row[language].replace('[['+atom['id']+']].','[['+atom['id']+']]')
            if page==10 and row['id']in['disk-energy-balance','conductivity-and-bottom-loss']:
                top=453.5 if row['id']=='disk-energy-balance' else 593.0
                for rect in row['erase_rects']:rect[1]=max(rect[1],top)
                for atom in row['atoms']:atom['rect'][1]=max(atom['rect'][1],top)
            if page==11 and row['id']=='reflected-ray-angle':
                row['erase_rects'][0][2]=250.0  # Original 为 ink reaches249.25pt; source prose only.
            if page==13 and row['id']=='fringe-spacing':
                row['left']=79.0  # Source leading D-sqrt(2)d/8 was missed by OCR; replay complete original object.
            if page==12 and row['id']=='small-angle-when':
                row['left_by_language']={'ko':326.0,'en':280.0}
                row['ko']='일 때'
            if page==12 and row['id']in['upper-image-label','lower-image-label']:
                row.update(align='right',right=134.0,min_left=72.0)
            if page==12 and row['id']=='alternative2-title':
                row['ko']='[다른 풀이 2:';row['en']='[Alternative solution 2:'
            if page==11 and 247<row['baseline']<410:
                row['right']=350.0  # Source figure column begins355pt and stays stationary.
            if page==9 and row['id']=='magnetic-force-a':
                row['en']="Now consider the ring's magnetic force, nonzero because the field is nonuniform."
            if page==8 and row['id']=='below-critical-length-a':
                # Preserve the descenders of stationary equation tag(20) ending220.75pt.
                for rect in row['erase_rects']:rect[1]=max(rect[1],222.0)
                for atom in row['atoms']:atom['rect'][1]=max(atom['rect'][1],222.0)
            if page==7 and row['id']=='zero-virtual-work':
                # Eq16 base subscripts end at637.75pt; the next prose/math row begins below639pt.
                # Exclude the original stationary Eq16 ink from this language erase/replay ROI.
                for rect in row['erase_rects']:rect[1]=max(rect[1],639.0)
            if page==5 and row['id']=='roots-original-reference13':
                row['ko']='[[eq13-root-a]]의 [[sin-zero]], [[theta-zero]]은 초기위치다. [[eq13-root-b]]의 나머지 해는 [[other-root]]이다.'
            if page==5 and row['id']=='angular-speed-definition':
                row['erase_rects']=[[75.4,373.4,286.8,387.3],[98,367.3,129,395.1]]
                for atom in row['atoms']:
                    if atom['id']=='ball2-velocity':atom['rect'][1:4:2]=[374,387.2]
    data.update(manual_rois_reviewed=True,publication_ready=False,source_page_reviewed=True,source_contact_sheet=str(BASE/'row-hints'/f'page{page:02d}-candidate-contact.png'),source_nonlanguage_and_final_visual_audit_required=True,protected_source_display_and_figure_rects=PROTECTED.get(page,[]))
    from cpho_2013_ts_background_evidence import prepare
    data['reviewed_blank_background_rects']=prepare(data)
    target=BASE/'authoring'/f'page{page:02d}-layout.json';target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf8')
    print(target)
    for row in data['rows']:print(row['id'],row['baseline'],round(row['baseline_evidence']['iou'],3),flush=True)

if __name__=='__main__':
    from pdf_memory_gate import page_worker
    p=argparse.ArgumentParser();p.add_argument('page',type=int);a=p.parse_args()
    with page_worker():create(a.page)
