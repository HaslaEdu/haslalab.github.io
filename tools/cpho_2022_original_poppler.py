"""Second-renderer pixel comparison of the complete 2022 problem editions."""
from pathlib import Path
import argparse,hashlib,json,math,subprocess
import numpy as np
import cv2
from PIL import Image,ImageDraw
import cpho_2022_original_build as b
from cpho_2022_original_qa import label_mask
cv2.setNumThreads(1)


def render(path,number,target,dpi=110):
    args=['pdftoppm','-f',str(number),'-l',str(number),'-r',str(dpi),'-singlefile','-png',str(path.relative_to(b.ROOT)),str(target.relative_to(b.ROOT))]
    result=subprocess.run(args,cwd=b.ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
    return target.with_suffix('.png'),result.stderr.decode('utf8',errors='replace')


def audit(paths,dpi=110):
    folder=b.BASE/'qa/poppler';folder.mkdir(parents=True,exist_ok=True);source=[];native=[];warnings=[]
    for number in range(1,5):
        image,warning=render(b.SOURCE,number,folder/f'source-page{number}',dpi);source.append(image)
        if warning:warnings.append({'file':b.SOURCE.name,'page':number,'warning':warning})
        image,warning=render(b.BASE/f'native/page{number:02}.pdf',1,folder/f'native-page{number}',dpi);native.append(image)
    report={'source_sha256':b.SOURCE_SHA,'renderer':'pdftoppm (independent of MuPDF)','dpi':dpi,'files':[],'passed':True,'warnings':warnings,
        'prose_antialias_guard_px':1,'method':'Original and translated prose outline boxes receive one raster-pixel allowance for hinting/antialiasing. Native visible ink is independently compared with the original operators after prose suppression, excluding only original raster-language regions.'}
    scale=dpi/72
    for path in paths:
        row={'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'pages':[],'passed':True};previews=[]
        specs=b.BASE/'qa'/path.stem
        build=json.loads(path.with_suffix('.build.json').read_text(encoding='utf8'))
        for number in range(1,5):
            image,warning=render(path,number,folder/f'{path.stem}-page{number}',dpi)
            with Image.open(source[number-1])as old:a=np.array(old.convert('RGB'))
            with Image.open(image)as new:z=np.array(new.convert('RGB'))
            with Image.open(native[number-1])as unchanged:native_pixels=np.array(unchanged.convert('RGB'))
            if a.shape!=z.shape:raise ValueError('Page dimensions differ')
            spec=json.loads((specs/f'page{number:02}-spec.json').read_text(encoding='utf8'));allowed=np.zeros(a.shape[:2],bool)
            for x0,y0,x1,y1 in spec['allowed_rects']:
                allowed[max(0,math.floor(y0*scale)):min(a.shape[0],math.ceil(y1*scale)),max(0,math.floor(x0*scale)):min(a.shape[1],math.ceil(x1*scale))]=True
            difference=np.any(a!=z,axis=2);raw=difference&~allowed
            distance=cv2.distanceTransform((~allowed).astype(np.uint8),cv2.DIST_C,3)
            padded=cv2.dilate(allowed.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool);outside=difference&~padded
            raster=[label for label in build['raster_label_translation']if label['page']==number]
            native_ink=(native_pixels.min(axis=2)<250)&~label_mask(allowed.shape,scale,raster)
            native_changes=np.any(native_pixels!=z,axis=2)&native_ink
            source_mix=np.any(native_pixels!=a,axis=2)&native_ink
            item={'page':number,'changed_pixels_outside_prose':int(outside.sum()),'outline_bbox_antialias_fringe_pixels':int(raw.sum()),
                'maximum_fringe_distance_px':float(distance[raw].max())if np.any(raw)else 0,
                'changed_pixels_in_native_actual_ink':int(native_changes.sum()),'original_prose_antialias_mix_pixels':int(source_mix.sum()),'image':str(image.relative_to(b.ROOT))}
            if np.any(outside):
                yy,xx=np.nonzero(outside);item['outside_bbox']=[float(xx.min()/scale),float(yy.min()/scale),float((xx.max()+1)/scale),float((yy.max()+1)/scale)]
            if warning:report['warnings'].append({'file':path.name,'page':number,'warning':warning})
            row['pages'].append(item);row['passed']&=not np.any(outside)and not np.any(native_changes);print(path.name,number,'pdftoppm outside',item['changed_pixels_outside_prose'],'native ink',item['changed_pixels_in_native_actual_ink'],flush=True)
            preview=Image.fromarray(z);preview.thumbnail((595,842));previews.append(preview)
        contact=Image.new('RGB',(1220,1740),'#ddd')
        for i,preview in enumerate(previews):contact.paste(preview,((i%2)*610+8,(i//2)*870+20))
        contact_path=specs/'contact-poppler.png';contact.save(contact_path);row['contact']=str(contact_path.relative_to(b.ROOT));report['files'].append(row);report['passed']&=row['passed']
    (b.AUTHOR/'qa-poppler.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('pdfs',nargs='+',type=Path);args=parser.parse_args();result=audit([p.resolve()for p in args.pdfs]);print('PASSED',result['passed']);raise SystemExit(not result['passed'])
