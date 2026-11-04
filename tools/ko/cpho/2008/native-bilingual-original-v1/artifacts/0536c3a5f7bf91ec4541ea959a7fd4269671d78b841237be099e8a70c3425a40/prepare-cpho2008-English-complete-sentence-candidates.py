"""Explicit source-faithful prose review; fixed points, zero fitting or tracking."""
from pathlib import Path
import sys,json,hashlib,re
from fontTools.ttLib import TTFont
B=Path(__file__).resolve().parents[1];sys.path.insert(0,str(B/'engine'))
from cpho2008_atomic_authoring import atomic_text
from cpho2008_native_compose import font_path
UPDATES={
1:{'r06':'uniformly on grass. A defender is at [[0]]. Let [[1]] denote the [[2]] distance and [[3]] the [[4]]–[[5]] angle.'},
3:{'r08':'The glass has conductivity [[0]]; electricity costs [[1]] yuan/kWh. Ideally,','r21':'[[0]], hence the name single-electron tunnelling. An [[1]] device is a tunnelling junction or','r24':'[[0]]. Model the device in Fig. [[1]] as a capacitor of capacitance [[2]]. Its charge is continuous,','r25':'as Fig. [[0]] shows: the electron cloud shifts slightly relative to the positive background.'},
4:{'r06':'the single-electron island. The electrodes are [[0]]. Its net charge [[1]] has integer [[2]],','r07':'positive, negative or zero. Here [[0]] is unit charge; the [[1]] junction capacitances are [[2]] and [[3]].','r14':'The island energy is about [[0]], where [[1]]. Use the grid (Fig.','r15':'[[0]]) and include Coulomb blockade.','r16':'Start with [[0]]. As','r18':"draw the island's energy",'r20':'Plot [[0]] vertically; measure [[1]] in'},
5:{'r00':'[[0]], and use [[1]] horizontally, with [[2]] in units of [[3]]. Mark key points. For [[4]][[5]]','r21':'[[0]] is the gravitational constant, [[1]] the stellar mass and [[2]] light speed; [[3]] is much smaller than [[4]] in'},
6:{'r09':'Electron mass is [[0]][[1]] [[2]] is light speed; [[3]]','r10':'[[0]][[1]] [[2]][[3]] [[4]] is the Coulomb constant and [[5]] the elementary charge.','r14':'[[0]]. The track radius below is [[1]],','r15':'and above is [[0]]. In the plate, the track makes','r16':'[[0]] with its normal. The plate is [[1]] thick;','r17':'the field is [[0]] and the mass is [[1]]'},
9:{'r16':"[[0]]. Choose a frame. Let the object's coordinates be [[1]] and its time [[2]]. Satellite [[3]]"},
10:{'r04':"[[0]] is the gravitational constant, [[1]] Earth's mass and [[2]] the orbit radius. From [[3]],",'r05':"Here [[0]] is Earth's radius, [[1]] the altitude and [[2]] ground gravity. Substitution",'r08':'[[0]] The satellite reading [[1]] minus the inertial-clock reading [[2]] at infinity is','r11':'Numerically, [[0]] is very small, so equation [[1]] becomes'},
11:{'r01':'Numerically, [[0]] is very small. As above, [[1]] is approximately'},
14:{'r00':'[[0]]. In Fig. [[1]], the left [[2]] capacitance is','r01':'[[0]], and the right [[1]] capacitance is [[2]]. The pair','r02':'in Fig. [[0]] has charges [[1]] on capacitors [[2]][[3]]','r03':'[[0]]. Thus the net island charge is','r10':'[[0]][[1]] The plot of [[2]] against [[3]] is Fig. [[4]][[5]] Table [[7]] gives the [[6]] ranges[[8]]'},
15:{'r01':'[[0]]. In Fig. [[1]], [[2]] is normal to [[3]]. Two parallel rays','r21':'[[0]] is the [[1]]–[[2]] angle. At total reflection,'},
16:{'r03':'is even in [[0]], so the ray is symmetric about the polar axis. Rays left of the','r04':'origin have [[0]], and rays on the right have [[1]]. The figure shows [[2]],','r05':'with polar axis [[0]] and the dwarf at [[1]]. In [[2]], insert the periapsis','r09':'Method 1: let [[0]] be the dwarf–Earth distance. Approximately,'},
17:{'r14':"[[0]] is the radius and [[1]] the speed. Bohr's ground-state quantization ([[2]]) gives"},
19:{'r08':'Here [[0]] is the charge, [[1]] the speed and [[2]] the momentum; [[3]] is the angle turned in time [[4]],','r09':'and [[0]] is the curvature radius. Hence','r16a':'The mean speed in the lead plate is','r16b':'[[0]] is the transit'},
20:{'r04':'far shorter than pulse period [[0]]. The mean force on the plate during'}
}
F=B/'authoring/English-complete-sentence-review';F.mkdir(exist_ok=True);metrics={};failed=[];summary=[]
UPDATES[1].update(r05='In football, a player at [[0]] passes along [[1]]; the ball rolls on grass at speed [[2]]',r06='uniformly. A defender is at [[0]]. Let [[1]] be the [[2]] distance and [[3]] the [[4]]–[[5]] angle.')
UPDATES[3].update(r08='The conductivity is [[0]]; electricity costs [[1]] yuan/kWh. Ideally,',r21='[[0]], hence the name single-electron tunnelling. [[1]] is a tunnelling junction or',r24='[[0]]. Treat Fig. [[1]] as a capacitor of capacitance [[2]], whose plate charge is continuous,',r25='as Fig. [[0]] shows: the electron cloud shifts slightly against the positive background.')
UPDATES[4].update(r06='the single-electron island. The electrodes are [[0]]. Its charge [[1]] has integer [[2]],',r07='positive, negative or zero. [[0]] is unit charge; [[1]] capacitances are [[2]] and [[3]].',r14='Its energy is about [[0]], with [[1]]. On the grid (Fig.',r15='[[0]]), allow for blockade.',r20='Plot [[0]] vertically; [[1]] is in')
UPDATES[5].update(r00='[[0]]; use [[1]] horizontally, with [[2]] in units of [[3]]. Mark key points. For [[4]][[5]]',r21='[[0]] is the gravitational constant, [[1]] mass and [[2]] light speed; [[3]] is far below [[4]] in')
UPDATES[6].update(r09='The mass is [[0]][[1]] [[2]] is light speed; [[3]]',r10="[[0]][[1]] [[2]][[3]] [[4]] is Coulomb's constant and [[5]] is unit charge.",r15='and above is [[0]]. In it, the track makes',r16='[[0]] to its normal; it is [[1]] thick;',r17='use [[0]] and [[1]]')
UPDATES[9].update(r16='[[0]]. In a chosen frame, let position be [[1]] and time [[2]]. Satellite [[3]]')
UPDATES[10].update(r01='[[0]][[1]][[2]] The satellite clock slows by [[3]]. The ground reading [[4]] minus',r04="[[0]] is the gravitational constant, [[1]] Earth's mass, [[2]] orbit radius. From [[3]],",r05="Here [[0]] is Earth's radius, [[1]] altitude and [[2]] ground gravity. Substitution")
UPDATES[14].update(r01='[[0]]; the right [[1]] has capacitance [[2]].',r02='In Fig. [[0]], [[1]] are charges on [[2]][[3]]')
UPDATES[16].update(r03='is even in [[0]]; the ray is symmetric about the polar axis. Left of the',r04='origin, [[0]]; on the right, [[1]]. The figure shows [[2]],',r05='with axis [[0]] and dwarf at [[1]]. In [[2]], insert the periapsis')
UPDATES[19].update(r08='Here [[0]] is charge, [[1]] speed and [[2]] momentum; [[3]] is the angle turned in time [[4]],',r16a='The mean speed through lead is')
UPDATES[3]['r24']='[[0]]. Treat Fig. [[1]] as a capacitor of capacitance [[2]], with continuous plate charge,'
UPDATES[6].update(r15='and above is [[0]]. In lead, the track makes',r16='[[0]] to the normal; the lead is [[1]] thick;')
UPDATES[4].update(r04='[[0]]. For Fig. [[1]] at fixed voltage [[2]], use the double junction in Fig. [[3]]',r05='to avoid stray capacitance when observing tunnelling. The middle metal layer is')
UPDATES[4]['r01']='This is Coulomb blockade. Find the range of plate voltage [[0]]'
UPDATES[15]['r16']='the critical angle [[0]], so cannot exit. [[1]] increases with [[2]]. From [[3]],'
UPDATES[5]['r21']='[[0]] is the gravitational constant, [[1]] stellar mass, [[2]] light speed; [[3]] is far below [[4]] in'
UPDATES[4].update(r06='the single-electron island. The electrodes are [[0]]. Its charge is [[1]], where [[2]] is',r07='any integer. [[0]] is unit charge; [[1]] capacitances are [[2]] and [[3]].')
def width(face,text,point):
    if face not in metrics:
        with TTFont(font_path('en',face),fontNumber=0,recalcTimestamp=False)as tt:metrics[face]=(tt.getBestCmap(),dict(tt['hmtx'].metrics),tt['head'].unitsPerEm)
    cmap,advance,em=metrics[face]
    return sum(point/4 if ch==' 'else advance[cmap[ord(ch)]][0]*point/em for ch in text)
for n,changes in UPDATES.items():
    original=B/f'authoring/page{n:02}-native-language.json';raw=original.read_bytes();q=json.loads(raw);rows={r['id']:r for r in q['rows']}
    for id,text in changes.items():
        r=rows[id];assert sorted(map(int,re.findall(r'\[\[(\d+)\]\]',text)))==list(range(len(r['native_atoms']))),(n,id)
        old=r['en'];r['en']=text;total=0
        for part in re.split(r'(\[\[\d+\]\])',text):
            if not part:continue
            if part.startswith('[['):a=r['native_atoms'][int(part[2:-2])];total+=a['rect'][2]-a['rect'][0]
            else:total+=width(r['source_prose_face'],part,r['size'])
        left=r['original_center']-total/2 if r.get('align')=='center'else r['left'];lo,hi=r['allowed_horizontal'];good=left>=lo-.001 and left+total<=hi+.001
        record=dict(source_page=n,row=id,old_English=old,complete_natural_English=text,source_text=r['source_text'],original_point=r['size'],source_baseline=r['baseline'],actual_donor_hmtx_and_original_native_width_right=left+total,source_allowed_right=hi,fits_at_original_point=good)
        summary.append(record)
        if not good:failed.append(record);print('OVERFLOW',n,id,round(left+total-hi,3),text)
    atomic_text(F/f'page{n:02}-native-language-candidate.json',json.dumps(q,ensure_ascii=False,indent=2)+'\n')
review_path=F/'explicit-source-complete-English-review.json'
if review_path.exists():
    old=review_path.read_bytes();history=F/'previous-reviewed-prose';history.mkdir(exist_ok=True);preserved=history/(hashlib.sha256(old).hexdigest()+'.json')
    if not preserved.exists():atomic_text(preserved,old.decode('utf8'))
atomic_text(review_path,json.dumps(dict(source_sha256='4e076fb9234683d028792190bcec56f12de72890da6c0e44ddf0e9146013459d',changes=summary,no_font_or_point_fitting=True,all_candidates_fit=not failed),ensure_ascii=False,indent=2)+'\n')
print('C08_COMPLETE_SENTENCE_CANDIDATES',len(summary),'pages',len(UPDATES),'overflows',len(failed))
if failed:raise SystemExit(1)
