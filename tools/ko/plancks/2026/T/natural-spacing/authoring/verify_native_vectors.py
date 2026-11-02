"""Verify actual native vector coordinates, including stationary diagrams."""
from pathlib import Path
import argparse,json,sys
BASE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BASE/'engine'))
import latex_native_motion as motion
def verify(path):
    path=Path(path);report=json.loads(path.with_suffix('.layout.json').read_text('utf-8'))
    source=motion.inspect_inline_groups(Path(report['source']),report['page'])
    final=motion.inspect_inline_groups(path,1)
    old=source['vector_paths'];new=final['vector_paths']
    offsets={tuple(p['operator_indices']):s['dx']for s in report['native_shifts']for p in s.get('vector_paths',[])}
    errors=[];moved=0;stationary=0
    if len(new)<len(old):errors.append({'kind':'missing_native_paths','before':len(old),'after':len(new)})
    for i,(a,b)in enumerate(zip(old,new)):
        dx=offsets.get(tuple(a['operator_indices']),0);want=[a['rect'][0]+dx,a['rect'][1],a['rect'][2]+dx,a['rect'][3]]
        delta=max(abs(x-y)for x,y in zip(want,b['rect']))
        if a['paint_operator']!=b['paint_operator']or delta>1e-7:errors.append({'path_index':i,'expected':want,'actual':b['rect'],'max_delta':delta})
        moved+=bool(dx);stationary+=not bool(dx)
    result={'native_vector_paths_verified':len(old),'moved_whole_expression_paths_verified':moved,
            'stationary_paths_including_vector_figures_verified':stationary,'coordinate_errors':errors,
            'max_coordinate_tolerance_pt':1e-7,'added_raster_language_mask_paths':len(new)-len(old)}
    report['actual_native_vector_coordinate_audit']=result
    path.with_suffix('.layout.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    if errors:raise ValueError(json.dumps(result,ensure_ascii=False))
    print(path.name,'vectors',len(old),'moved',moved,'stationary',stationary,'PASS',flush=True)
    return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('pdfs',nargs='+',type=Path);a=p.parse_args()
 for path in a.pdfs:
  if path.is_dir():
   for pdf in sorted(path.glob('page[0-9][0-9].pdf')):verify(pdf)
  else:verify(path)
