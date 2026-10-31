"""Trace the supplied 2023 scan diagrams into transparent, scale-free paths.

This is geometric tracing of the source ink, not a generated replacement of a
physics diagram. Paper-grey is normalized from the dominant bright paper tone;
the source's darker object fills, letters, arrows and punctuation are retained.
Rebuilding uses PyMuPDF, OpenCV, NumPy and Pillow. The PDF renderer can call
vector_path(source_name, page, rect) using only the Python standard library.
"""
from functools import lru_cache
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'tools/kphe_figures'
SOURCES = ROOT / 'tmp/kphe_archive/originals'
QA = ROOT / 'tmp/kphe_figure_qa'
VERSION = 4
VISUAL_NATIVE_FALLBACKS = {
    '473a149ba2660e62': 'T1b Q7: colored graph boundary developed light gaps after separate-color curve fitting.',
    '41c94783e19a37e2': 'T1b Q11: dark m1/m2 labels inside green blocks lost their original contrast polarity.',
    '03e979a1fb799a38': 'T1b Q12: the filled blue projectile developed pale gaps around its original marking.',
    '2f271e8411a9b898': 'T2b Q5: thin red graph segments became materially lighter and discontinuous.',
    '602f0007b1cf01f2': 'T2b Q16: water/container boundaries developed pale gaps against the black outlines.',
    '4af79247bdadd1ac': 'T2b Q17: the colored support boundary developed light gaps at its original corners.',
}


def crop_key(source, page, rect):
    value = [Path(str(source)).name, int(page), [round(float(x), 4) for x in rect]]
    return hashlib.sha256(json.dumps(value, separators=(',', ':')).encode()).hexdigest()[:16]


@lru_cache(maxsize=1)
def _index():
    return json.loads((ASSETS / 'index.json').read_text(encoding='utf-8'))


def vector_path(source, page, rect):
    """Return the checked transparent SVGZ, or None for non-2023 documents.

    Read with gzip.decompress(path.read_bytes()) before passing its SVG bytes
    to a renderer. Compression is lossless and deterministic (gzip mtime=0).
    """
    source = Path(str(source)).name
    if not source.startswith('KPhE_2023_'):
        return None
    key = crop_key(source, page, rect)
    item = _index()['figures'].get(key)
    if item is None or item['status'] != 'verified':
        raise ValueError(f'Unverified 2023 diagram: {source} page {page} {list(rect)}')
    return ASSETS / item['svg']


def collect():
    result = {}
    for path in sorted((ROOT / 'tools/kphe_solutions').glob('2023-*.json')):
        for part, rows in json.loads(path.read_text(encoding='utf-8')).items():
            if not isinstance(rows, list):
                continue
            for row in rows:
                for where, figure in [('explanation', row.get('figure')), ('problem', row.get('problem', {}).get('figure'))]:
                    if not figure:
                        continue
                    if not figure['source'].startswith('KPhE_2023_'):
                        continue
                    key = crop_key(figure['source'], figure['page'], figure['rect'])
                    item = result.setdefault(key, {**figure, 'uses': []})
                    item['uses'].append({'json': path.name, 'part': part, 'number': row['number'], 'where': where})
    return result


def normalize_paper(rgb):
    """Remove paper luminance while retaining relative ink/shading contrast."""
    import cv2
    import numpy as np
    # Sample the outside margin. A large light-grey cylinder may occupy more
    # of a tight crop than its white paper and must never become the reference.
    border = np.concatenate((rgb[:3].reshape(-1,3),rgb[-3:].reshape(-1,3),
        rgb[:,:3].reshape(-1,3),rgb[:,-3:].reshape(-1,3)))
    luminance = np.mean(border.astype(float), axis=1)
    neutral = np.max(border,axis=1).astype(float)-np.min(border,axis=1) < 12
    bright = luminance[(luminance >= 180) & neutral]
    if not len(bright):
        raise ValueError('No bright paper reference in this crop')
    hist = np.bincount(np.rint(bright).astype('uint8'), minlength=256)
    # Uniform grey photographic backgrounds and plain white diagrams are both
    # common. Use the dominant neutral bright perimeter tone, not an object fill.
    paper = int(np.argmax(hist[180:]) + 180)
    # Remove only the almost-paper tone. Keep the original foreground colours:
    # scaling every RGB channel to white would overexpose a blue/orange field.
    alpha = np.where(np.min(rgb.astype(float),axis=2) >= paper*251/255,0,255).astype('uint8')
    reference = np.dstack((rgb.copy(),alpha))
    normalized = rgb.copy()
    gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY).astype(float)
    gradient=np.hypot(cv2.Sobel(gray,cv2.CV_64F,1,0),cv2.Sobel(gray,cv2.CV_64F,0,1))
    protected=cv2.dilate((gradient>25).astype('uint8'),np.ones((3,3),dtype='uint8'))>0
    free=(~protected)&(alpha>0)
    count,labels,stats,_=cv2.connectedComponentsWithStats(free.astype('uint8'),8)
    for component in range(1,count):
        if stats[component,cv2.CC_STAT_AREA]<12:
            continue
        mask=labels==component;pixels=rgb[mask]
        # Only flat, edge-free interior patches are denoised. Letter strokes,
        # numbers, arrows, boundaries and real multi-tone object shading stay
        # protected, unlike a destructive whole-colour-component fill.
        if np.max(np.percentile(pixels,75,axis=0)-np.percentile(pixels,25,axis=0))<=8:
            normalized[mask]=np.median(pixels,axis=0).astype('uint8')
    normalized = np.clip(np.rint(normalized.astype(float) / 8) * 8, 0, 255).astype('uint8')
    rgba = np.dstack((normalized, alpha))
    return rgba, paper, reference


def trace_native(rgba, stroke_width=.8, gray_step=8):
    """Deterministic nested ink contours, retaining even tiny punctuation.

    Colour clustering can erase a faint stroke in a scan. Nested masks retain
    each grey level and original connected component instead. Coordinates are
    bounded polygonal paths, not an embedded/resampled image.
    """
    import cv2
    import numpy as np
    from PIL import Image
    height, width = rgba.shape[:2]
    rgb = rgba[:, :, :3]
    opaque = rgba[:, :, 3] > 0
    chromatic = (np.max(rgb,axis=2).astype(int)-np.min(rgb,axis=2).astype(int) > 12) & opaque
    grey = np.mean(rgb.astype(float),axis=2)
    paths = []
    def contour_path(mask, colour, external=False, offset=(0,0)):
        contours,_ = cv2.findContours(mask.astype('uint8'),cv2.RETR_EXTERNAL if external else cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
        commands=[]
        for contour in contours:
            if offset != (0,0):
                contour=contour+np.array([[[offset[0],offset[1]]]],dtype=contour.dtype)
            points=cv2.approxPolyDP(contour,.28,True).reshape(-1,2)
            if len(points)<3:
                x,y,w,h=cv2.boundingRect(contour)
                commands.append(f'M{x-.4:.2f} {y-.4:.2f}h{max(.8,w-.2):.2f}v{max(.8,h-.2):.2f}h{-max(.8,w-.2):.2f}Z')
            else:
                commands.append('M'+' '.join(f'{int(x)} {int(y)}' for x,y in points)+'Z')
        if commands:
            paths.append('<path fill="'+colour+'" stroke="'+colour+'" stroke-width="'+str(stroke_width)+'" stroke-linejoin="round" fill-rule="evenodd" d="'+' '.join(commands)+'"/>')
    if np.any(chromatic):
        # Do not flatten a coloured component or fill its holes: the small
        # internal marks can be N/S, an energy value, or white printed text.
        # Preserve every measured (8-level quantized) colour and paint darker
        # contour sets last, rather than clustering small text into its field.
        palette,labels=np.unique(rgb[chromatic],axis=0,return_inverse=True)
        ys,xs=np.where(chromatic)
        order=np.argsort(labels,kind='stable')
        bounds=np.searchsorted(labels[order],np.arange(len(palette)+1))
        for index in np.argsort(-np.mean(palette.astype(float),axis=1)):
            pixels=order[bounds[index]:bounds[index+1]]
            xx,yy=xs[pixels],ys[pixels]
            x0,y0,x1,y1=int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())
            mask=np.zeros((y1-y0+1,x1-x0+1),dtype=bool)
            mask[yy-y0,xx-x0]=True
            color='#'+''.join(f'{int(c):02x}' for c in palette[index])
            contour_path(mask,color,offset=(x0,y0))
    for level in range(255 if gray_step == 1 else 248,-1,-gray_step):
        mask=(grey<=level) & opaque & ~chromatic
        contour_path(mask,'#'+f'{level:02x}'*3)
    return '<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="'+str(width)+'" height="'+str(height)+'" viewBox="0 0 '+str(width)+' '+str(height)+'">\n<g transform="translate(0.5 0.5)">\n'+'\n'.join(paths)+'\n</g>\n</svg>\n'


@lru_cache(maxsize=1)
def potrace_info():
    """Resolve the build-only native Potrace binary; never download it silently."""
    command = os.environ.get('KPHE_POTRACE_BIN') or shutil.which('potrace')
    if not command:
        raise FileNotFoundError('Set KPHE_POTRACE_BIN to Potrace 1.16; see kphe_figure_provenance.md')
    path = Path(command).resolve()
    output = subprocess.run([str(path),'--version'],capture_output=True,text=True,check=True).stdout
    version = output.splitlines()[0]
    if 'potrace 1.16' not in version.lower():
        raise ValueError(f'Expected the verified Potrace 1.16, found {version}')
    return {'version':version,'binarySha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'binary':str(path),'turdsize':0,'alphamax':1,'opticurve':True,'opttolerance':.2,'unit':100,
        'native_small_island_bbox_area_max_pixels':80}


def trace_potrace(rgba, gray_step=8):
    """Curve-fit the same separate ink masks, retaining all colors and specks.

    No color clustering, morphology, threshold changes or component filtering
    takes place here. Potrace's turdsize=0 preserves small connected components.
    A batch invocation traces each PBM independently and preserves all holes.
    """
    import numpy as np
    import cv2
    import xml.etree.ElementTree as ET
    from PIL import Image
    info = potrace_info()
    height,width = rgba.shape[:2]
    rgb,opaque = rgba[:,:,:3],rgba[:,:,3]>0
    chromatic = (np.max(rgb,axis=2).astype(int)-np.min(rgb,axis=2).astype(int)>12)&opaque
    gray = np.mean(rgb.astype(float),axis=2)
    workspace=QA/'potrace-work';workspace.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='trace-',dir=workspace) as temporary:
        directory=Path(temporary).resolve()
        assert directory.is_relative_to(workspace.resolve())
        jobs=[]
        def enqueue(mask,color,offset=(0,0)):
            if not np.any(mask): return
            path=directory/f'ink-{len(jobs):05d}.pbm'
            Image.fromarray(np.where(mask,0,255).astype('uint8')).convert('1').save(path)
            # A 1-pixel gray dot can become lighter after Bezier antialiasing
            # despite turdsize=0. Preserve tiny islands using the preceding
            # native contour geometry, while fitting their larger neighbors.
            contours,hierarchy=cv2.findContours(mask.astype('uint8'),cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE)
            commands=[]
            if hierarchy is not None:
                hierarchy=hierarchy[0]
                for i,contour in enumerate(contours):
                    if hierarchy[i,3]!=-1: continue
                    x,y,w,h=cv2.boundingRect(contour)
                    if w*h>80: continue
                    include=[i];child=hierarchy[i,2]
                    while child!=-1:
                        include.append(child);child=hierarchy[child,0]
                    for j in include:
                        points=cv2.approxPolyDP(contours[j],.28,True).reshape(-1,2)
                        if len(points)<3:
                            x,y,w,h=cv2.boundingRect(contours[j])
                            commands.append(f'M{x-.4:.2f} {y-.4:.2f}h{max(.8,w-.2):.2f}v{max(.8,h-.2):.2f}h{-max(.8,w-.2):.2f}Z')
                        else:
                            commands.append('M'+' '.join(f'{int(x)} {int(y)}' for x,y in points)+'Z')
            jobs.append((path,color,offset,' '.join(commands)))
        if np.any(chromatic):
            palette,labels=np.unique(rgb[chromatic],axis=0,return_inverse=True)
            ys,xs=np.where(chromatic)
            order=np.argsort(labels,kind='stable')
            bounds=np.searchsorted(labels[order],np.arange(len(palette)+1))
            for index in np.argsort(-np.mean(palette.astype(float),axis=1)):
                pixels=order[bounds[index]:bounds[index+1]]
                xx,yy=xs[pixels],ys[pixels]
                x0,y0,x1,y1=int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())
                mask=np.zeros((y1-y0+1,x1-x0+1),dtype=bool)
                mask[yy-y0,xx-x0]=True
                enqueue(mask,'#'+''.join(f'{int(c):02x}' for c in palette[index]),(x0,y0))
        for level in range(255 if gray_step==1 else 248,-1,-gray_step):
            enqueue((gray<=level)&opaque&~chromatic,'#'+f'{level:02x}'*3)
        for start in range(0,len(jobs),48):
            subprocess.run([info['binary'],'--svg','--flat','--turdsize','0','--alphamax','1',
                '--opttolerance','0.2','--unit','100',*[str(job[0]) for job in jobs[start:start+48]]],
                capture_output=True,check=True)
        groups=[]
        namespace='{http://www.w3.org/2000/svg}'
        for path,color,(x,y),islands in jobs:
            root=ET.parse(path.with_suffix('.svg')).getroot()
            group=root.find(namespace+'g')
            if group is None: continue
            paths=[element.attrib['d'] for element in group.iter(namespace+'path')]
            protected=(f'<g transform="translate(0.5 0.5)"><path fill="{color}" stroke="{color}" stroke-width="0.8" stroke-linejoin="round" fill-rule="evenodd" d="{islands}"/></g>') if islands else ''
            groups.append(f'<g transform="translate({x} {y})"><g transform="{group.attrib["transform"]}" fill="{color}" stroke="none" fill-rule="evenodd">'+
                ''.join('<path d="'+value+'"/>' for value in paths)+'</g>'+protected+'</g>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'+''.join(groups)+'</svg>'


def ink_mask(rgb):
    """Measure dark strokes and coloured shapes, including pale coloured fills."""
    import numpy as np
    data=rgb[:,:,:3].astype(float)
    return (np.mean(data,axis=2)<220) | (np.max(data,axis=2)-np.min(data,axis=2)>12)


def minify_svg(svg):
    """Compact numeric syntax without changing any SVG coordinates."""
    # Keep explicit commands: an L following a cubic C cannot be omitted.
    svg = re.sub(r'(?<![\d.])(-?\d+)\.00(?!\d)',r'\1',svg)
    return re.sub(r'(\.\d*[1-9])0+(?!\d)',r'\1',svg)


def build_one(key, item, exact_gray=False, engine='potrace', previous=None):
    import cv2
    import numpy as np
    from PIL import Image
    import pymupdf as fitz
    if engine=='potrace' and key in VISUAL_NATIVE_FALLBACKS:
        # These source-specific cases were rejected in the full visual review.
        # Reuse only a checked native source match, otherwise rebuild native ink.
        native_previous=previous and previous.get('tracing_method','native').startswith('native')
        same_source=previous and previous.get('sourceSha256')==hashlib.sha256((SOURCES/item['source']).read_bytes()).hexdigest()
        if native_previous and same_source and previous.get('status')=='verified':
            path=ASSETS/previous['svg']
            if hashlib.sha256(path.read_bytes()).hexdigest()!=previous['svgSha256']:
                raise ValueError(f'Changed visual-review fallback asset: {path}')
            result={**previous,**item}
            if not all((QA/f'{key}-{suffix}.png').exists() for suffix in ('source','vector','reference','normalized')):
                source=fitz.open(SOURCES/item['source'])
                pix=source[item['page']-1].get_pixmap(matrix=fitz.Matrix(3,3),clip=fitz.Rect(item['rect']),colorspace=fitz.csRGB,alpha=False)
                rgb=np.frombuffer(pix.samples,dtype='uint8').reshape(pix.height,pix.width,3).copy()
                rgba,_,reference=normalize_paper(rgb)
                for suffix,pixels in [('source',rgb),('reference',reference),('normalized',rgba)]:
                    Image.fromarray(pixels).save(QA/f'{key}-{suffix}.png')
                vector=fitz.open(stream=gzip.decompress(path.read_bytes()),filetype='svg')
                vp=vector[0].get_pixmap(matrix=fitz.Matrix(pix.width/vector[0].rect.width,pix.height/vector[0].rect.height),colorspace=fitz.csRGB,alpha=True)
                a=np.frombuffer(vp.samples,dtype='uint8').reshape(vp.height,vp.width,4)
                white=np.clip(a[:,:,:3].astype(float)+255-a[:,:,3:4].astype(float),0,255).astype('uint8')
                Image.fromarray(white).save(QA/f'{key}-vector.png')
        else:
            result=build_one(key,item,engine='native')
        result.update(tracing_method='native-contours-fallback',generator_version=VERSION,tracing_revision=2,
            visual_rejection=VISUAL_NATIVE_FALLBACKS[key],fallback_reason='Full source/vector visual comparison rejected the curve candidate; retain the verified native source contours.')
        (QA/f'{key}-result-v{VERSION}.json').write_text(json.dumps(result,ensure_ascii=False,indent=1)+'\n',encoding='utf8')
        return result
    doc = fitz.open(SOURCES / item['source'])
    page = doc[item['page'] - 1]
    clip = fitz.Rect(item['rect'])
    # The source scans are about 2 px/pt. Sampling at 3 px/pt retains every
    # scanned stroke before tracing; the final SVG contains no raster image.
    pix = page.get_pixmap(matrix=fitz.Matrix(3, 3), clip=clip, colorspace=fitz.csRGB, alpha=False)
    rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3).copy()
    rgba, paper, reference_rgba = normalize_paper(rgb)
    if exact_gray:
        # Faint conductors and plate edges can have a source contrast just
        # above a quantization boundary. Retain all 256 original gray levels
        # when the raw local-contrast comparison identifies such a case.
        rgba = reference_rgba.copy()
    source_png = QA / f'{key}-source.png'
    Image.fromarray(rgb).save(source_png)
    normalized_png = QA / f'{key}-normalized.png'
    Image.fromarray(rgba).save(normalized_png)
    Image.fromarray(reference_rgba).save(QA / f'{key}-reference.png')
    target = ASSETS / f'{Path(item["source"]).stem}-p{item["page"]}-{key}.svgz'
    tracer = trace_potrace if engine == 'potrace' else trace_native
    svg = minify_svg(tracer(rgba, gray_step=1 if exact_gray else 8))
    svg_bytes = svg.encode('utf-8')
    compressed = gzip.compress(svg_bytes, compresslevel=9, mtime=0)
    if '<image' in svg or 'base64' in svg:
        raise ValueError('A traced figure must not contain an embedded bitmap')
    vector = fitz.open(stream=svg.encode(), filetype='svg')
    vp = vector[0].get_pixmap(matrix=fitz.Matrix(pix.width/vector[0].rect.width, pix.height/vector[0].rect.height),
        colorspace=fitz.csRGB, alpha=True)
    va = np.frombuffer(vp.samples, dtype=np.uint8).reshape(vp.height, vp.width, 4)
    # Render comparisons on white, matching the white exam page. Alpha is
    # independently inspected so a hidden white/grey page-sized path fails.
    white = va[:, :, :3].astype(float) + (255-va[:, :, 3:4].astype(float))
    white = np.clip(white, 0, 255).astype('uint8')
    if white.shape[:2] != rgb.shape[:2]:
        white = cv2.resize(white, (rgb.shape[1], rgb.shape[0]))
    cleaned = reference_rgba[:, :, :3].copy(); cleaned[reference_rgba[:, :, 3] == 0] = 255
    ref_ink = ink_mask(cleaned)
    vec_ink = ink_mask(white)
    if not np.any(ref_ink) or not np.any(vec_ink):
        raise ValueError('No foreground ink after tracing')
    distance = cv2.distanceTransform((~vec_ink).astype('uint8'), cv2.DIST_L2, 3)
    recall = float(np.mean(distance[ref_ink] <= 1.5))
    reverse_distance = cv2.distanceTransform((~ref_ink).astype('uint8'), cv2.DIST_L2, 3)
    precision = float(np.mean(reverse_distance[vec_ink] <= 1.5))
    precision2 = float(np.mean(reverse_distance[vec_ink] <= 2.0))
    intersection = int(np.sum(ref_ink & vec_ink)); union = int(np.sum(ref_ink | vec_ink))
    iou = intersection / max(1, union)
    alpha_corner = [int(va[y,x,3]) for y,x in [(0,0),(0,-1),(-1,0),(-1,-1)]]
    transparent_fraction = float(np.mean(va[:, :, 3] == 0))
    ref_gray = cv2.cvtColor(cleaned,cv2.COLOR_RGB2GRAY).astype(float)
    vec_gray = cv2.cvtColor(white,cv2.COLOR_RGB2GRAY).astype(float)
    ref_edge = np.hypot(cv2.Sobel(ref_gray,cv2.CV_64F,1,0),cv2.Sobel(ref_gray,cv2.CV_64F,0,1)) > 65
    vec_edge = np.hypot(cv2.Sobel(vec_gray,cv2.CV_64F,1,0),cv2.Sobel(vec_gray,cv2.CV_64F,0,1)) > 65
    edge_distance=cv2.distanceTransform((~vec_edge).astype('uint8'),cv2.DIST_L2,3)
    edge_recall=float(np.mean(edge_distance[ref_edge]<=2.0)) if np.any(ref_edge) else 1.0
    # Test every small isolated source mark individually. Global recall alone
    # can hide a missing dot, punctuation mark or short arrow beside a block.
    component_count,component_labels,component_stats,_=cv2.connectedComponentsWithStats(ref_ink.astype('uint8'),8)
    small_ids=np.where((component_stats[:,cv2.CC_STAT_AREA]<=80)&(np.arange(component_count)>0))[0]
    near_counts=np.bincount(component_labels[ref_ink&(distance<=1.5)],minlength=component_count)
    missing_small=[int(i) for i in small_ids if near_counts[i]==0]
    chromatic_fraction = float(np.mean(np.max(rgb,axis=2).astype(int)-np.min(rgb,axis=2).astype(int)>12))
    if not exact_gray and edge_recall < .97 and chromatic_fraction < .002:
        return build_one(key,item,exact_gray=True,engine=engine,previous=previous)
    status = 'verified' if recall >= .97 and precision2 >= .97 and edge_recall >= .97 and iou >= .70 and transparent_fraction > .03 and not missing_small else 'needs_review'
    result = {**item, 'svg': target.name, 'sourceSha256': hashlib.sha256((SOURCES/item['source']).read_bytes()).hexdigest(),
        'svgSha256': hashlib.sha256(compressed).hexdigest(), 'svgBytes': len(compressed),
        'uncompressedSvgSha256': hashlib.sha256(svg_bytes).hexdigest(), 'uncompressedSvgBytes': len(svg_bytes),
        'compression': 'gzip, level 9, mtime 0',
        'paper_luminance': paper, 'source_pixels': [pix.width,pix.height],
        'grayscale_levels': 256 if exact_gray else 32,
        'paths': svg.count('<path'), 'ink_recall_within_1_5_pixels': round(recall, 6),
        'ink_precision_within_1_5_pixels': round(precision, 6),
        'ink_precision_within_2_pixels': round(precision2, 6),
        'local_contrast_edge_recall_within_2_pixels': round(edge_recall, 6),
        'ink_iou': round(iou, 6), 'transparent_fraction': round(transparent_fraction, 6),
        'corner_alpha': alpha_corner, 'status': status,'generator_version':VERSION,'tracing_revision':2,
        'tracing_method':'potrace-bezier' if engine=='potrace' else 'native-contours',
        'small_source_components_up_to_80_pixels':len(small_ids),
        'small_source_components_without_nearby_vector_ink':len(missing_small)}
    if engine == 'potrace':
        result['potrace']={key:value for key,value in potrace_info().items() if key!='binary'}
        Image.fromarray(white).save(QA/f'{key}-potrace-candidate.png')
    if engine == 'potrace' and status != 'verified':
        candidate={key:value for key,value in result.items() if key.startswith(('ink_','local_','small_'))}
        if previous and previous.get('status')=='verified':
            existing=ASSETS/previous['svg']
            data=existing.read_bytes()
            if hashlib.sha256(data).hexdigest()!=previous['svgSha256']:
                raise ValueError(f'Cannot retain a changed fallback asset: {existing}')
            original=fitz.open(stream=gzip.decompress(data),filetype='svg')
            fallback=original[0].get_pixmap(matrix=fitz.Matrix(pix.width/original[0].rect.width,pix.height/original[0].rect.height),colorspace=fitz.csRGB,alpha=True)
            pixels=np.frombuffer(fallback.samples,dtype='uint8').reshape(fallback.height,fallback.width,4)
            white=np.clip(pixels[:,:,:3].astype(float)+255-pixels[:,:,3:4].astype(float),0,255).astype('uint8')
            result={**previous,**item,'generator_version':VERSION,'tracing_method':'native-contours-fallback',
                'tracing_revision':2,
                'potrace_candidate':candidate,'fallback_reason':'Potrace candidate failed unchanged source-ink, local-edge, transparency or isolated-mark checks; previous verified contour asset retained byte-for-byte.'}
        else:
            result=build_one(key,item,engine='native')
            result.update(tracing_method='native-contours-fallback',potrace_candidate=candidate,
                fallback_reason='Potrace candidate failed source comparisons; native contour fallback regenerated and checked.')
            white=np.array(Image.open(QA/f'{key}-vector.png').convert('RGB'))
    else:
        temporary=target.with_suffix('.svgz.tmp')
        temporary.write_bytes(compressed)
        temporary.replace(target)
    Image.fromarray(white).save(QA/f'{key}-vector.png')
    (QA/f'{key}-result-v{VERSION}.json').write_text(json.dumps(result,ensure_ascii=False,indent=1)+'\n',encoding='utf8')
    return result


def _build_task(task):
    key,item,engine,previous=task
    return key,build_one(key,item,engine=engine,previous=previous)


def contact_sheets(figures, prefix='contact'):
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 14)
    keys = list(figures)
    for start in range(0, len(keys), 12):
        group = keys[start:start+12]
        sheet = Image.new('RGB', (1200, len(group)*190), 'white')
        draw = ImageDraw.Draw(sheet)
        for i,key in enumerate(group):
            row = figures[key]
            use = row['uses'][0]
            label = f'{start+i+1}. {use["json"]} {use["part"]} Q{use["number"]} | recall {row["ink_recall_within_1_5_pixels"]:.3f} | {row.get("tracing_method","native")}'
            draw.text((5,i*190+3), label, fill='black', font=font)
            for col, suffix in enumerate(('source','vector')):
                image = Image.open(QA/f'{key}-{suffix}.png')
                image.thumbnail((580,158))
                sheet.paste(image,(col*600+10,i*190+24))
            draw.line((0,(i+1)*190-1,1200,(i+1)*190-1), fill='#888888')
        sheet.save(QA/f'{prefix}-{start//12+1:02d}.png')


def main():
    from concurrent.futures import ProcessPoolExecutor,as_completed
    ASSETS.mkdir(exist_ok=True);QA.mkdir(exist_ok=True)
    command=next((arg.split('=',1)[1] for arg in sys.argv if arg.startswith('--potrace=')),None)
    if command: os.environ['KPHE_POTRACE_BIN']=command
    engine=next((arg.split('=',1)[1] for arg in sys.argv if arg.startswith('--engine=')),'potrace')
    if engine not in ('potrace','native'): raise ValueError('Engine must be potrace or native')
    if engine=='potrace': potrace_info()
    workers=int(next((arg.split('=',1)[1] for arg in sys.argv if arg.startswith('--jobs=')),'1'))
    items = collect()
    if '--sample' in sys.argv:
        items = dict(list(items.items())[:4])
    selected = [arg.split('=',1)[1] for arg in sys.argv if arg.startswith('--only=')]
    previous_index=json.loads((ASSETS/'index.json').read_text(encoding='utf-8')) if (ASSETS/'index.json').exists() else {}
    figures=dict(previous_index.get('figures',{}))
    if selected:
        items = {key:item for key,item in items.items() if key in selected}
    tasks=[];completed=0
    for key,item in items.items():
        journal=QA/f'{key}-result-v{VERSION}.json'
        if '--resume' in sys.argv and journal.exists():
            row=json.loads(journal.read_text(encoding='utf8'))
            asset=ASSETS/row['svg']
            visual_ok=key not in VISUAL_NATIVE_FALLBACKS or row.get('tracing_method')=='native-contours-fallback'
            if visual_ok and row.get('status')=='verified' and (row.get('tracing_revision')==2 or row.get('tracing_method')=='potrace-bezier') and asset.exists() and hashlib.sha256(asset.read_bytes()).hexdigest()==row['svgSha256']:
                figures[key]={**row,**item};completed+=1
                print(f'{completed}/{len(items)} resumed {row.get("tracing_method")} {row["svg"]}',flush=True)
                continue
        tasks.append((key,item,engine,figures.get(key)))
    if workers==1:
        for task in tasks:
            key,row=_build_task(task);figures[key]=row;completed+=1
            print(f'{completed}/{len(items)} {row["status"]} {row["tracing_method"]} {row["svg"]}',flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures=[pool.submit(_build_task,task) for task in tasks]
            for future in as_completed(futures):
                key,row=future.result();figures[key]=row;completed+=1
                print(f'{completed}/{len(items)} {row["status"]} {row["tracing_method"]} {row["svg"]}',flush=True)
    contact_sheets(figures)
    out = {'version':VERSION,'method':'Separate original chromatic-color and grayscale ink masks are fitted by Potrace 1.16 Bezier curves, turdsize 0, alphamax 1, opticurve on, opttolerance .2, coordinate unit 100. Perimeter paper detection, color/shade masks and tiny components remain unchanged. Candidates must pass original source-ink, local-edge, transparency and individual isolated-mark checks. A failing candidate retains the preceding verified native contour asset byte-for-byte. No generated content or embedded bitmap.',
        'potrace':{key:value for key,value in potrace_info().items() if key!='binary'} if engine=='potrace' else None,
        'compression':{'format':'SVGZ (gzip)','level':9,'mtime':0,'lossless':True,
            'uncompressed_bytes':sum(row['uncompressedSvgBytes'] for row in figures.values()),
            'compressed_bytes':sum(row['svgBytes'] for row in figures.values())},
        'visual_review':{'status':'pending','unique_crops':len(figures),'source_comparison_contact_sheets':7},
        'figures':figures,'failures':[key for key,row in figures.items() if row['status']!='verified'],
        'potrace_fallbacks':[key for key,row in figures.items() if row.get('tracing_method')=='native-contours-fallback']}
    index_temporary=ASSETS/'index.new.json'
    index_temporary.write_text(json.dumps(out,ensure_ascii=False,indent=1)+'\n',encoding='utf-8')
    index_temporary.replace(ASSETS/'index.json')
    print(f'Traced {len(figures)} unique crops; failures {len(out["failures"])}')
    if out['failures']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
