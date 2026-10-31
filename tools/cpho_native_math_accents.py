"""Preserve native Word PDF raster accents in tokenized mathematical fields.

Word stores some dots, phasor tildes and h-bars as images with soft masks.
SVG conversion can lose those masks; native PDF rendering retains them.
The image-only source background is built once per page, then composited
under the selected mathematical glyph/rule sprites at source coordinates.
"""
from pathlib import Path
import copy,statistics
import pymupdf as fitz
from PIL import Image,ImageChops

class NativeAccents:
    def __init__(self,source,scale=4):self.source=source;self.scale=scale;self.pages={};self.images={}
    def background(self,pi):
        if pi not in self.pages:
            doc=fitz.open();doc.insert_pdf(self.source,from_page=pi,to_page=pi)
            page=doc[0];page.add_redact_annot(page.rect,fill=None)
            page.apply_redactions(images=0,graphics=2)
            # Full-size source figures are redrawn separately and must not
            # leak into a nearby caption's expanded mathematical crop.
            for item in page.get_images(full=True):
                if item[2]>2 or item[3]>2:page.delete_image(item[0])
            self.pages[pi]=doc
        return self.pages[pi][0]
    def field(self,pi,math,folder,target):
        m=copy.deepcopy(math);r=fitz.Rect(m['source_rect']);region=r+(-1,-8,1,8)
        if pi not in self.images:self.images[pi]=[i for i in self.source[pi].get_image_info()if i['width']<=2 and i['height']<=2]
        baseline=statistics.median([p[1]for p in m.get('glyph_origins',[])]) if m.get('glyph_origins')else(r.y0+r.y1)/2
        eligible=[fitz.Rect(i['bbox'])for i in self.images[pi]if fitz.Rect(i['bbox']).intersects(region)
                  and abs((i['bbox'][1]+i['bbox'][3])/2-baseline)<=10.5]
        if not eligible:return m
        pix=self.background(pi).get_pixmap(matrix=fitz.Matrix(self.scale,self.scale),clip=region,alpha=True)
        canvas=Image.frombytes('RGBA',[pix.width,pix.height],pix.samples)
        origin=(pix.x/self.scale,pix.y/self.scale)
        # A following prose line can have an overdot/tilde at the very bottom
        # of a generous crop. Those small accents belong above their base
        # glyph, not below every selected glyph of this field. Keep descenders
        # such as a denominator h-bar, which are taller connected components.
        last_baseline=max((p[1]for p in m.get('glyph_origins',[])),default=r.y1)
        mask=ImageChops.multiply(canvas.convert('RGB').convert('L').point(lambda z:255 if z<170 else 0),canvas.getchannel('A').point(lambda z:255 if z>60 else 0))
        points={(x,y)for y in range(mask.height)for x in range(mask.width)if mask.getpixel((x,y))}
        native_pixels=len(points)
        remove=[];retained=[]
        while points:
            first=points.pop();component=[first];todo=[first]
            while todo:
                x,y=todo.pop()
                for dx in [-1,0,1]:
                    for dy in [-1,0,1]:
                        q=(x+dx,y+dy)
                        if q in points:points.remove(q);component.append(q);todo.append(q)
            ys=[q[1]for q in component]
            xs=[q[0]for q in component]
            center=fitz.Point(origin[0]+(min(xs)+max(xs))/2/self.scale,origin[1]+(min(ys)+max(ys))/2/self.scale)
            if not any(box.contains(center)for box in eligible) or (max(ys)-min(ys)+1<=self.scale*2.5 and center.y>last_baseline+3):
                remove.extend(component)
            else:retained.extend(component)
        if remove:
            for x,y in remove:canvas.putpixel((x,y),(0,0,0,0))
        if native_pixels==len(remove):return m
        touches=any(x in [0,canvas.width-1]or y in [0,canvas.height-1]for x,y in retained)
        sprite=Image.open(Path(folder)/m['file']).convert('RGBA')
        position=(round((r.x0-origin[0])*self.scale),round((r.y0-origin[1])*self.scale))
        canvas.alpha_composite(sprite,position)
        visible=canvas.convert('RGB').convert('L').point(lambda z:255 if z<170 else 0)
        visible=ImageChops.multiply(visible,canvas.getchannel('A').point(lambda z:255 if z>60 else 0))
        ink=visible.getbbox()
        if not ink:raise ValueError('No native mathematical ink '+str(target))
        box=(max(0,ink[0]-2),max(0,ink[1]-2),min(canvas.width,ink[2]+2),min(canvas.height,ink[3]+2))
        canvas=canvas.crop(box);canvas.save(target)
        m.update(file=Path(target).name,width=canvas.width/self.scale,height=canvas.height/self.scale,
                 source_rect=[origin[0]+box[0]/self.scale,origin[1]+box[1]/self.scale,
                              origin[0]+box[2]/self.scale,origin[1]+box[3]/self.scale],
                 native_raster_math_accents=True,native_raster_ink_pixels=native_pixels-len(remove))
        if remove:m['unrelated_following_line_accent_pixels_excluded']=len(remove)
        if touches:m['native_accent_crop_edge_review_required']=True
        return m
    def close(self):
        for doc in self.pages.values():doc.close()

def restore(data,source,folder):
    helper=NativeAccents(source)
    for e in data['entries']:
        for i,m in enumerate(e['math']):
            if i in e.get('preserved_math',[]):continue
            e['math'][i]=helper.field(e['page'],m,folder,Path(folder)/(e['id']+f'-native-m{i}.png'))
    helper.close()
