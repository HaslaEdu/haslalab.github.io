"""Faithful display-vector restoration of the existing WoPhO mark.

The five letter faces are traced from the published raster; no font is used.
This is a derived display asset, not an official vector master. The input PNG
is read only. Color ramps are sampled from its original colored faces.
"""
from pathlib import Path
from collections import deque, defaultdict
import argparse
import hashlib
import json
import math
import numpy as np
from PIL import Image

SMOOTH = False


def components(mask):
    seen = np.zeros(mask.shape, bool)
    found = []
    h, w = mask.shape
    for sy, sx in zip(*np.nonzero(mask)):
        if seen[sy, sx]:
            continue
        q = deque([(int(sx), int(sy))])
        seen[sy, sx] = True
        points = []
        while q:
            x, y = q.popleft()
            points.append((x, y))
            for xx, yy in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if 0 <= xx < w and 0 <= yy < h and mask[yy,xx] and not seen[yy,xx]:
                    seen[yy,xx] = True
                    q.append((xx,yy))
        if len(points) > 1000:
            m = np.zeros(mask.shape, bool)
            xx, yy = zip(*points)
            m[yy,xx] = True
            found.append(m)
    return sorted(found, key=lambda m: int(np.nonzero(m)[1].min()))


def close(mask):
    def morph(m, dilate):
        p = np.pad(m, 1)
        shifted = [p[1+dy:1+dy+m.shape[0],1+dx:1+dx+m.shape[1]]
                   for dy in (-1,0,1) for dx in (-1,0,1)]
        return np.logical_or.reduce(shifted) if dilate else np.logical_and.reduce(shifted)
    return morph(morph(mask, True), False)


def smooth_mask(mask):
    """Denoise one-pixel contour nicks before vector fitting, not a raster upscale."""
    values = mask.astype(float)
    kernel = (1,4,6,4,1)
    for axis in (0,1):
        pad = [(0,0),(0,0)]
        pad[axis] = (2,2)
        extended = np.pad(values,pad)
        result = np.zeros_like(values)
        for offset,weight in enumerate(kernel):
            slices = [slice(None),slice(None)]
            slices[axis] = slice(offset,offset+values.shape[axis])
            result += extended[tuple(slices)]*weight/16
        values = result
    return values >= .5


def area(points):
    return sum(x*y2-x2*y for (x,y),(x2,y2) in zip(points, points[1:]+points[:1]))/2


def contours(mask):
    h,w = mask.shape
    edges = set()
    for y,x in zip(*np.nonzero(mask)):
        x,y = int(x),int(y)
        if y == 0 or not mask[y-1,x]: edges.add(((x,y),(x+1,y)))
        if x == w-1 or not mask[y,x+1]: edges.add(((x+1,y),(x+1,y+1)))
        if y == h-1 or not mask[y+1,x]: edges.add(((x+1,y+1),(x,y+1)))
        if x == 0 or not mask[y,x-1]: edges.add(((x,y+1),(x,y)))
    starts = defaultdict(set)
    for a,b in edges: starts[a].add(b)
    direction = {(1,0):0,(0,1):1,(-1,0):2,(0,-1):3}
    result = []
    while edges:
        a,b = min(edges)
        start = a
        pts = [a]
        while True:
            edges.remove((a,b))
            starts[a].remove(b)
            pts.append(b)
            if b == start:
                break
            prev = direction[(b[0]-a[0],b[1]-a[1])]
            choices = starts[b]
            if not choices:
                raise ValueError("Open contour")
            priority = {1:0,0:1,3:2,2:3}
            c = min(choices, key=lambda v: priority[(direction[(v[0]-b[0],v[1]-b[1])]-prev)%4])
            a,b = b,c
        pts.pop()
        if abs(area(pts)) > 20:
            result.append(pts)
    return sorted(result,key=lambda p:-abs(area(p)))


def rdp(points, epsilon):
    if len(points) <= 2: return points
    p = np.array(points, float)
    v = p[-1]-p[0]
    norm = np.linalg.norm(v)
    dist = np.linalg.norm(p-p[0],axis=1) if not norm else np.abs(v[0]*(p[:,1]-p[0,1])-v[1]*(p[:,0]-p[0,0]))/norm
    i = int(np.argmax(dist))
    if dist[i] <= epsilon: return [points[0],points[-1]]
    return rdp(points[:i+1],epsilon)[:-1]+rdp(points[i:],epsilon)


def simplify_closed(points):
    p0 = np.array(points[0])
    j = int(np.argmax([np.linalg.norm(np.array(p)-p0) for p in points]))
    tolerance = 1.7 if SMOOTH else .85
    a = rdp(points[:j+1], tolerance)
    b = rdp(points[j:]+[points[0]], tolerance)
    return a[:-1]+b[:-1]


def fmt(v): return f"{v:.3f}".rstrip("0").rstrip(".")


def rounded_path(points):
    p = np.array(simplify_closed(points),float)
    incoming, outgoing = [],[]
    for i,v in enumerate(p):
        u = p[i-1]-v
        w = p[(i+1)%len(p)]-v
        radius = min(1.75 if SMOOTH else 1.25,np.linalg.norm(u)*.22,np.linalg.norm(w)*.22)
        incoming.append(v+u/np.linalg.norm(u)*radius)
        outgoing.append(v+w/np.linalg.norm(w)*radius)
    xy = lambda v: fmt(v[0])+" "+fmt(v[1])
    d = ["M"+xy(outgoing[-1])]
    for i,v in enumerate(p):
        d.extend(["L"+xy(incoming[i]),"Q"+xy(v)+" "+xy(outgoing[i])])
    return " ".join(d)+"Z"


def rgbhex(rgb): return "#"+"".join(f"{int(v):02x}" for v in rgb)


def source_relative_label(file):
    """Record repository-relative provenance without committing machine paths."""
    absolute = file.resolve()
    for parent in absolute.parents:
        if (parent/".git").exists():
            return absolute.relative_to(parent).as_posix()
    return file.name


def main():
    global SMOOTH
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sourcePath", type=Path, help="Original WoPhO PNG, read only")
    parser.add_argument("outputDirectory", type=Path, help="Created along with any missing parent directories")
    parser.add_argument("--smooth", action="store_true", help="Remove one-pixel contour noise before vector fitting")
    parser.add_argument("--name", help="Output filename stem (without an extension)")
    args = parser.parse_args()
    source, out = args.sourcePath, args.outputDirectory
    SMOOTH = args.smooth
    name = args.name or ("wopho-display-vector-smooth" if SMOOTH else "wopho-display-vector")
    if not name or Path(name).name != name or name in (".", "..") or any(c in name for c in "\\/:"):
        parser.error("--name must be a filename stem, without a directory")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    a = np.array(Image.open(source).convert("RGBA"))
    rgb = a[:,:,:3].astype(int)
    mask = (np.ptp(rgb,axis=2)>45)&(rgb.max(axis=2)>75)&(a[:,:,3]>100)
    faces = components(mask)
    assert len(faces)==5
    defs = ['<filter id="shadow" x="-10%" y="-20%" width="120%" height="160%"><feGaussianBlur stdDeviation=".65"/></filter>']
    geometry = []
    metadata = []
    for i,m in enumerate(faces):
        cleaned = close(m)
        if SMOOTH:
            cleaned = smooth_mask(cleaned)
        loops = contours(cleaned)
        d = " ".join(rounded_path(c) for c in loops)
        yy,xx = np.nonzero(m)
        xmin,xmax = int(xx.min()),int(xx.max())
        stops = []
        samples = []
        for j in range(7):
            target = xmin+(xmax-xmin)*j/6
            selected = m & (np.abs(np.indices(m.shape)[1]-target) <= max(3,(xmax-xmin)/15))
            pixels = rgb[selected]
            value = np.median(pixels,axis=0).round().astype(int)
            stops.append(f'<stop offset="{j/6:.5f}" stop-color="{rgbhex(value)}"/>')
            samples.append(value.tolist())
        defs.append(f'<linearGradient id="face{i}" x1="{xmin}" y1="0" x2="{xmax}" y2="0" gradientUnits="userSpaceOnUse">'+"".join(stops)+'</linearGradient>')
        defs.append(f'<clipPath id="clip{i}"><path d="{d}" fill-rule="evenodd"/></clipPath>')
        geometry.append((i,d))
        metadata.append({"letter":"WoPhO"[i],"sourceBox":[xmin,int(yy.min()),xmax+1,int(yy.max())+1],"sourceFacePixels":int(m.sum()),"contours":len(loops),"outlineVertices":[len(simplify_closed(c)) for c in loops],"maskIoU":float(np.count_nonzero(m&cleaned)/np.count_nonzero(m|cleaned)),"gradientRGB":samples})
    defs.append('<linearGradient id="vertical" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#fff" stop-opacity=".11"/><stop offset=".36" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#181326" stop-opacity=".16"/></linearGradient>')
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="500" height="132" viewBox="0 0 500 132">',
             '<title>WoPhO — source-traced display vector</title>',
             '<desc>Derived display restoration traced from the original World Physics Olympiad raster. Letter geometry and sampled rainbow palette preserved; no font substitution. Not an official vector master.</desc>',
             '<defs>'+"".join(defs)+'</defs>']
    for i,d in geometry:
        parts.append(f'<path d="{d}" fill="#090811" fill-rule="evenodd" opacity=".5" transform="translate(1.5 7)" filter="url(#shadow)"/>')
    for i,d in geometry:
        parts.append(f'<path d="{d}" fill="#66636e" stroke="#514e59" stroke-width="3.8" stroke-linejoin="round" fill-rule="evenodd" transform="translate(.6 5.5)"/>')
    for i,d in geometry:
        parts.append(f'<path d="{d}" fill="url(#face{i})" stroke="#777680" stroke-width="2.3" stroke-linejoin="round" fill-rule="evenodd"/>')
        parts.append(f'<path d="{d}" fill="url(#vertical)" fill-rule="evenodd"/>')
        parts.append(f'<g clip-path="url(#clip{i})"><path d="{d}" fill="none" stroke="#f2f1f7" stroke-width="2.4" opacity=".48" transform="translate(-.8 -.8)"/><path d="{d}" fill="none" stroke="#201c31" stroke-width="2" opacity=".28" transform="translate(.8 .8)"/></g>')
    parts.append('</svg>')
    out.mkdir(parents=True, exist_ok=True)
    target = out/(name+".svg")
    target.write_text("".join(parts)+"\n",encoding="utf8")
    (out/(name+"-provenance.json")).write_text(json.dumps({"kind":"derived-display-vector","source":source_relative_label(source),"sourceSha256":digest,"output":source_relative_label(target),"method":"Five saturated original letter faces traced by pixel-edge contours; small contour-noise smoothing only in --smooth mode; <=1.7px polygon simplification; <=1.75px rounded corners; source-sampled seven-stop rainbow gradients and restrained vector bevel/extrusion. No font substitution or raster upscale.","faces":metadata},indent=2)+"\n")
    assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
    print(json.dumps({"svg":str(target),"bytes":target.stat().st_size,"faces":metadata,"sourceUnchanged":True}))


if __name__ == "__main__": main()
