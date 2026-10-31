"""Explicit native-picture feature masks for reviewed bitmap label overlays."""
from __future__ import annotations
import numpy as np


def feature_masks(pixels,profile,language_boxes):
    height,width=pixels.shape[:2];yy,xx=np.mgrid[:height,:width]
    rgb=pixels.astype(np.int16);r,g,b=[rgb[:,:,i]for i in range(3)]
    planets=np.zeros((height,width),bool)
    for item in profile.get('planet_surfaces',[]):
        if 'rect_px'in item:
            x0,y0,x1,y1=item['rect_px'];planets[max(0,int(y0)):min(height,int(y1)),max(0,int(x0)):min(width,int(x1))]=True
            continue
        cx,cy=item['center_px'];rx,ry=item['radii_px']
        planets|=((xx+.5-cx)/rx)**2+((yy+.5-cy)/ry)**2<=1
    prose=np.zeros((height,width),bool)
    for x0,y0,x1,y1 in language_boxes:
        prose[max(0,int(y0)-1):min(height,int(y1)+1),max(0,int(x0)-1):min(width,int(x1)+1)]=True
    dots=np.zeros((height,width),bool)
    if profile.get('gray_white_asteroid_points'):
        dots=(r>100)&(g>100)&(np.abs(r-g)<35)&(rgb.max(2)-rgb.min(2)<100)&~planets&~prose
    orbits=np.zeros((height,width),bool)
    if profile.get('colored_orbits'):
        orbits=(g>120)&(b>80)&(r<100)&(g-r>40)&~planets
    return dict(planet_surfaces=planets,gray_white_asteroid_points=dots,colored_orbits=orbits)
